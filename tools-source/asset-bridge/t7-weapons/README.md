# T7 weapons bridge: BO3 Wonder Weapons for IW7 Zombies

Goal: port every Black Ops III Wonder Weapon (all maps, DLC and Chronicles) to
IW7 Zombies as ordinary IW7 assets in one mod fastfile that the official
iw7-mod client downloads by itself (`mods/<mod>/mod.ff`, `mod.sabl`,
`mod.sabs`; see the server product's KINO.md). No client-side native change.
Game data, dumps and built fastfiles stay local and are never committed.

## Pipeline

| Step | Tool | Input -> output |
| --- | --- | --- |
| 1. Load a BO3 zone resident | owner-fork ZoneTool in T7 mode: `zonetool.exe -assetlog <log.tsv> -holdzone <zone> <release-file>` next to `BlackOps3_UnrankedDedicatedServer.exe` and the BO3 `zone/` folder | `log.tsv`: type, type name, asset name, header address of every registered asset |
| 2. Scan weapon definitions | `t7_weapon_scan.py --pid <zonetool pid> --assetlog <log.tsv> --out scan.json` | read-only, bounded, annotated memory of each `weapon` asset (asset references, strings, nested blocks) |
| 3. Convert models/anims | ZoneTool `-dumpzoneto iw7 <zone> xmodel,xmodelmesh,xanim` | IW7 ZoneTool sources (`xmodel/`, `xsurface/`, `xanim/`) |
| 3b. Check long animations | `iw7_xanim_layout.py <xanim/*.xab>` | exit 1 when an animation of 256+ frames keeps a 64+ key rotation channel inline (BO3 layout): the IW7 client then reads a null index list and crashes |
| 3c. Check model normals | `iw7_xsurface_check.py <xsurface/*.xsb>` | exit 1 when vertex normals lack the IW7 high bits (BO3 leaves them clear; the model renders black) or are not unit length |
| 3d. Retarget arm animations | `t7_vm_retarget.py --source-hands <BO3 hands .xmb> --target-hands <IW7 hands .xmb> --out <dir> <xanim/*.xab>` | IW7 view-hand animations: arms by two-bone IK onto the BO3 wrists, hands/fingers by bind-relative orientation, gun on `tag_weapon` (IW7 convention); `iw7_xanim_codec.py` decodes/encodes the IW7 animation layout |
| 4. Infer fields | `t7_weapon_fields.py` | per weapon: anim slots, models, FX, sounds, numeric stats |
| 4b. Materials | `t7_material_pack.py <materials.json> --template <stock IW7 weapon material> --texconv <texconv.exe> --out <build> [--max-size 1024]` | BC7 `images/*.dds` + `materials/*.json` |
| 5. Author IW7 weapon | template from a stock IW7 Zombies weapon dump | `weapons/*.json`, `animpkg/`, `sfxpkg/`, `vfxpkg/` |
| 6. Build | ZoneTool IW7 `-buildzone mod` | `mod.ff`, `mod.sabl`, `mod.sabs` |

`-holdzone` keeps the process alive until the release file exists; create it
(or terminate the exact process) when the scan is done. The scan never writes
to the target process and reads at most `--max-blocks` nested blocks per weapon.

## Status

See `STATUS.md` for measured results. Field meanings in BO3's WeaponDef are
not public: `t7_weapon_fields.py` derives them from cross-weapon evidence and
records which offsets were confirmed against which known values.

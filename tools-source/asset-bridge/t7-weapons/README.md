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
| 3e. Grip and aiming | `t7_vm_retarget.py ... --ads-gun x,y,z --ads-idle <idle> --ads-up <ads_up> --ads-down <ads_down>` | hand/finger bones take the BO3 world orientation through a per-arm axis map measured at the wrist binds (the IW7 hand grips the gun as the BO3 hand does). ADS raise/lower animate only `tag_ads`, as stock IW7 does: the whole view model moves about the eye so the hip gun ends on the camera axis at `x,y,z`. Hand animations never list `tag_view`/`tag_ads` (the engine's ADS layer) |
| 3f. Sounds | `t7_weapon_sound.py --bo3-aliases <GrayWolf alias csv> --flac-root <dir> --template <stock IW7 aliases.csv> --out <zone asset root> --bank <bank> --zone <zone> --prefix <dir> --alias <BO3 aliases>` | IW7 sound bank source: each BO3 alias takes the first audible stock row of its role (player/npc fire, foley, projectile loop, impact), keeps its BO3 secondary chain and relative volume, `loaded` mod files, no stock duck references. Add `soundbank,<bank>` to the zone; ZoneTool writes `mod.sabl`/`mod.sabs` |
| 3g. Effects (read) | `t7_fx_read.py --pid <zonetool pid> --assetlog <log.tsv> --out fx.json [--only <effects>] [--follow]` | BO3 FxEffectDef headers and 0x260-byte elements (type, visual material/model/light/effect, linked effects, raw bytes) as JSON; read-only. The IW7 side is `iw7_vfx.py` (step 3h); the BO3 -> IW7 mapping is not written yet |
| 3h. Effects (IW7 read/write) | `iw7_vfx.py --to-json <x.iw7VFX> -o <x.json>`, `--from-json <x.json> -o <x.iw7VFX>`, `--roundtrip <dump dir>`, `--summary <dir> [--match <regex>]` | ZoneTool IW7 particle systems (`particlesystem/*.iw7VFX`) <-> JSON named after `structs.hpp` (system, emitters, states, 3 module groups, modules by type with curves and linked materials/models/lights/sub-systems/sounds). The encoder replays the ZoneTool dumper (its pointer de-duplication included): byte-identical on every stock dump. Edited lists set their counts; edited shared slots get fresh pointers |
| 4. Infer fields | `t7_weapon_fields.py` | per weapon: anim slots, models, FX, sounds, numeric stats |
| 4b. Materials | `t7_material_pack.py <materials.json> --template <stock single-UV IW7 weapon material> --texconv <texconv.exe> --out <build> [--max-size 1024] [--only <materials>]` | stock formats: BC7 `_packed_cs`/`_packed_nog`, BC4 `_packed_a`; `materials/*.json`. Opaque parts: `m2o/weapon_ar57_sight.json` (`..._i0c0s0o0n0p0_vm`); alpha parts: `m2o/weapon_ar57_tint2_camo.json`. Two-UV (`2uvt`) camo templates are refused (they draw BO3 meshes black). `--emissive-template m2o/attachment_thermalhybrid.json` (`..._i0c0s0o0n0e0p0_vm`) for BO3 materials with an emissive map (tint baked, BC7_UNORM `_e`); `--blend-template m2o/weapon_zappers_headcutter_glass.json` (`..._ndw_blend_i0c0s0n0pa0_vm`) for BO3 `blend` materials (glass): an opaque `replace` template draws them solid and hides the lit parts behind them |
| 5. Author IW7 weapon | template from a stock IW7 Zombies weapon dump | `weapons/*.json`, `animpkg/`, `sfxpkg/`, `vfxpkg/` |
| 6. Build | ZoneTool IW7 `-buildzone mod` | `mod.ff`, `mod.sabl`, `mod.sabs` |

`-holdzone` keeps the process alive until the release file exists; create it
(or terminate the exact process) when the scan is done. The scan never writes
to the target process and reads at most `--max-blocks` nested blocks per weapon.

## Status

See `STATUS.md` for measured results. Field meanings in BO3's WeaponDef are
not public: `t7_weapon_fields.py` derives them from cross-weapon evidence and
records which offsets were confirmed against which known values.

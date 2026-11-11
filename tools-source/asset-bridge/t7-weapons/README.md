# T7 weapons bridge: BO3 Wonder Weapons for IW7 Zombies

Goal: port every Black Ops III Wonder Weapon (all maps, DLC and Chronicles) to
IW7 Zombies as ordinary IW7 assets in one mod fastfile that the official
iw7-mod client downloads by itself (`mods/<mod>/mod.ff`, `mod.sabl`,
`mod.sabs`; see the server product's KINO.md). No client-side native change.
Game data, dumps and built fastfiles stay local and are never committed.

## Port a weapon in one command

Once per BO3 zone (zm_levelcommon, a DLC map zone, ...), snapshot every weapon
and every effect it holds; the snapshot folder then serves every port from
that zone (config key `snapshots`):

```
python t7_zone_snapshot.py --zonetool <zt-t7>/zonetool.exe --zone zm_levelcommon --out <snapshots>
python t7_port_weapon.py --config port-config.json --weapon thundergun_zm --out <dir>
```

The snapshot starts ZoneTool with `-holdzone`, runs `t7_weapon_scan.py` and
`t7_fx_read.py` on the holding process as soon as it prints
`ZONETOOL_HOLD <zone> <pid>`, then releases it.

Every stage is data-driven: no weapon name appears in the tools. The spec
(`t7_weapon_spec.py`) reads every role from the BO3 WeaponDef at fixed offsets
(models, flash/impact/trail effects, sound aliases, clip, ammo, fire time,
projectile values, gun/view kick, anim names by suffix). Its `_upgraded_zm`
twin becomes the Pack-a-Punch variant. Then:

| Stage | Does | Tool |
| --- | --- | --- |
| scripts | exports the zone's scripts, decompiles them, keeps those calling `getweapon("<base>")` and the zone scripts they `#using`; reads their tuning (`set_zombie_var`) and the effects they play | GrayWolf, gsc-tool `-g t7`, `t7_weapon_scripts.py` |
| export | view/world models with PNG images, the effects' materials, one alias table per sound zone, then exactly the sound files of the weapon's aliases, their secondaries and its anim notetracks | `graywolf_mcp.py` (GrayWolf over MCP stdio; `assets` is ignored for sounds, `name_filter` matches file base names) |
| materials | IW7 weapon materials, placed where the converted models reference them (`mc/`) | `t7_material_pack.py` |
| models | ZoneTool-converted models, normals checked | `iw7_xsurface_check.py` |
| anims | retarget onto the IW7 hands; ADS aim from the mesh (camera on the sight line from the rear third's top to the front third's top; Ray Gun 5.78 against 5.75 tuned in game) | `t7_vm_retarget.py`, `iw7_xanim_layout.py` |
| sounds | IW7 bank rows, role from the WeaponDef slot naming the alias (notetracks are foley); empty BO3 aliases stay silent | `t7_weapon_sound.py --role` |
| fx | weapon and script effects plus linked effects | `t7_fx_material_pack.py`, `t7_fx_to_iw7.py` |
| author | weapon, anim/vfx/sfx packages, BO3 kick, `_pap1` weapon and its two attachments | `iw7_weapon_author.py` |
| zone | `zone.csv` lines, the module catalog entry and one behaviour line per BO3 behaviour script (`weapon\|namespace\|tuning\|effects\|sounds`) | |

`t7_mod_assemble.py --mod-zone zonetool/<zone> --csv zone_source/<zone>.csv
--bank <zone>.all --zone <zone> --port <dir> [--port ...]` merges ports into
one mod zone: assets, the lines its CSV lacks, and one sound bank listing every
weapon's alias table. It keeps the mod catalog (`<mod zone>/catalog.txt`,
`weapon[:pap weapon:pap1 attachment:pap2 attachment]` per line) and, with
`--gsc <server module>`, rewrites the module's catalog between
`// BEGIN t7_mod_assemble catalog` and `// END t7_mod_assemble catalog`, so a
ported weapon reaches the magic wheel with no hand edit. The `behaviours` block
works the same way: the module implements each BO3 behaviour family once (by
script namespace, e.g. `zm_weap_thundergun`) and every weapon of that family,
base or upgraded, gets its tuning, effects and sounds from the BO3 script data. The author stage references only the effects the fx stage
built and never keeps a template's stock effect (BO3's effect or none).

`port-config.example.json` lists the machine inputs. Behaviour that BO3 keeps
in script (Thundergun blast, DG-2 chain lightning, view-model effects played by
client script) is extracted with its tuning but still needs an IW7 module;
IW7 has no client scripts.

## Pipeline

| Step | Tool | Input -> output |
| --- | --- | --- |
| 1. Load a BO3 zone resident | owner-fork ZoneTool in T7 mode: `zonetool.exe -assetlog <log.tsv> -holdzone <zone> <release-file>` next to `BlackOps3_UnrankedDedicatedServer.exe` and the BO3 `zone/` folder | `log.tsv`: type, type name, asset name, header address of every registered asset |
| 2. Scan weapon definitions | `t7_weapon_scan.py --pid <zonetool pid> --assetlog <log.tsv> --out scan.json` | read-only, bounded, annotated memory of each `weapon` asset (asset references, strings, nested blocks) |
| 3. Convert models/anims | ZoneTool `-dumpzoneto iw7 <zone> xmodel,xmodelmesh,xanim` | IW7 ZoneTool sources (`xmodel/`, `xsurface/`, `xanim/`) |
| 3b. Check long animations | `iw7_xanim_layout.py <xanim/*.xab>` | exit 1 when an animation of 256+ frames keeps a 64+ key rotation channel inline (BO3 layout): the IW7 client then reads a null index list and crashes |
| 3c. Check model normals | `iw7_xsurface_check.py <xsurface/*.xsb>` | exit 1 when vertex normals lack the IW7 high bits (BO3 leaves them clear; the model renders black) or are not unit length |
| 3d. Repair model normals | `iw7_xsurface_normals.py <xsurface/*.xsb> [--out-dir d]` | rebuilds rigid vertex normals from the triangles (area-weighted, smoothed over shared positions, IW7 high bits): for converted models whose normals pass 3c but point anywhere (p7_zm_teddybear: 49..55% outward, stock ~78%); reports outward share and triangle agreement before/after |
| 3e. Check LOD order | `iw7_xmodel_lods.py <xmodel/x.xmb> --xsurface <dir> [--fix]` | lists the XModelSurfs per LOD with triangle counts; IW7 draws LOD0 up close. The T7 conversion writes them lowest detail first (p7_zm_teddybear 68..2042 triangles; also wpn_t7_zmb_raygun_world 103..3105): `--fix` swaps the equal-length names into descending order |
| 3d. Retarget arm animations | `t7_vm_retarget.py --source-hands <BO3 hands .xmb> --target-hands <IW7 hands .xmb> --out <dir> <xanim/*.xab>` | IW7 view-hand animations: arms by two-bone IK onto the BO3 wrists, hands/fingers by bind-relative orientation, gun on `tag_weapon` (IW7 convention); `iw7_xanim_codec.py` decodes/encodes the IW7 animation layout |
| 3e. Grip and aiming | `t7_vm_retarget.py ... --ads-gun x,y,z --ads-idle <idle> --ads-up <ads_up> --ads-down <ads_down>` | hand/finger bones take the BO3 world orientation through a per-arm axis map measured at the wrist binds (the IW7 hand grips the gun as the BO3 hand does). ADS raise/lower animate only `tag_ads`, as stock IW7 does: the whole view model moves about the eye so the hip gun ends on the camera axis at `x,y,z`. Hand animations never list `tag_view`/`tag_ads` (the engine's ADS layer) |
| 3f. Sounds | `t7_weapon_sound.py --bo3-aliases <GrayWolf alias csv> --flac-root <dir> --template <stock IW7 aliases.csv> --out <zone asset root> --bank <bank> --zone <zone> --prefix <dir> --alias <BO3 aliases>` | IW7 sound bank source: each BO3 alias takes the first audible stock row of its role (player/npc fire, foley, projectile loop, impact), keeps its BO3 secondary chain and relative volume, `loaded` mod files, no stock duck references. Add `soundbank,<bank>` to the zone; ZoneTool writes `mod.sabl`/`mod.sabs` |
| 3g. Effects (read) | `t7_fx_read.py --pid <zonetool pid> --assetlog <log.tsv> --out fx.json [--only <effects>] [--follow]` | BO3 FxEffectDef headers and 0x260-byte elements (type, visual material/model/light/effect, linked effects, raw bytes) as JSON; read-only. The IW7 side is `iw7_vfx.py` (step 3i); the BO3 -> IW7 mapping is not written yet |
| 3h. Effect materials | `t7_fx_material_pack.py --materials <GrayWolf FX material export> --effects fx.json --add-template eq/gfx_flare_wtr.json --blend-template eq/vfx_pyro_flash_ark_green_p.json --add-atlas-template eq/vfx_pyro_fire_inferno_burst_short_1_anim_0z.json --blend-atlas-template eq/vfx_pyro_fire_flame_base_smoky.json --texconv <exe> --out <zone root>` | IW7 effect materials (`eq_effectunlit_*_evc`, particle colour from the emitter) with BO3 colour maps (BC7) and atlas layouts from the effects; distortion skipped |
| 3i. Effects (IW7 read/write) | `iw7_vfx.py --to-json <x.iw7VFX> -o <x.json>`, `--from-json <x.json> -o <x.iw7VFX>`, `--roundtrip <dump dir>`, `--summary <dir> [--match <regex>]` | ZoneTool IW7 particle systems (`particlesystem/*.iw7VFX`) <-> JSON named after `structs.hpp` (system, emitters, states, 3 module groups, modules by type with curves and linked materials/models/lights/sub-systems/sounds). The encoder replays the ZoneTool dumper (its pointer de-duplication included): byte-identical on every stock dump. Edited lists set their counts; edited shared slots get fresh pointers |
| 3j. Effects (convert) | `t7_fx_to_iw7.py --effects fx.json --materials <3h report> --template sprite=<stock.iw7VFX>:<emitter> [--template sprite_atlas=... tail=... trail=... light=...] --map <bo3 effect>=<iw7 name> --out <zone root>` | one IW7 emitter per BO3 element, cloned from a stock emitter of its kind and rewritten (life, burst/rate, material, colour and size graphs, spawn box, velocity, atlas); writes `particlesystem/<name>.iw7VFX` via `iw7_vfx.py`. Ray Gun templates: `vfx_zmb_impact_green_ch1` emitters 2/5/3/1 (sprite, atlas sprite, tail, omni light), `vfx_plasma_trail_friendly` emitter 1 (geo trail) |
| 4a. Recoil | `t7_weapon_kick.py --scan scan.json --weapon <bo3 weapon> --iw7 <weapons/*.json>` | BO3 gun kick and view kick (ADS and hip blocks of the WeaponDef, BO2 field order) copied into the IW7 weapon definition |
| 4. Infer fields | `t7_weapon_fields.py` | per weapon: anim slots, models, FX, sounds, numeric stats |
| 4b. Materials | `t7_material_pack.py <materials.json> --template <stock single-UV IW7 weapon material> --texconv <texconv.exe> --out <build> [--max-size 1024] [--only <materials>]` | stock formats: BC7 `_packed_cs`/`_packed_nog`, BC4 `_packed_a`; `materials/*.json`. Opaque parts: `m2o/weapon_ar57_sight.json` (`..._i0c0s0o0n0p0_vm`); alpha parts: `m2o/weapon_ar57_tint2_camo.json`. Two-UV (`2uvt`) camo templates are refused (they draw BO3 meshes black). `--emissive-template m2o/attachment_thermalhybrid.json` (`..._i0c0s0o0n0e0p0_vm`) for BO3 materials with an emissive map (tint baked, BC7_UNORM `_e`); `--blend-template m2o/weapon_zappers_headcutter_glass.json` (`..._ndw_blend_i0c0s0n0pa0_vm`) for BO3 `blend` materials (glass): an opaque `replace` template draws them solid and hides the lit parts behind them |
| 5. Author IW7 weapon | template from a stock IW7 Zombies weapon dump | `weapons/*.json`, `animpkg/`, `sfxpkg/`, `vfxpkg/` |
| 5b. Preflight the assembled tree | `iw7_mod_preflight.py <zonetool/<zone>> --csv <zone_source/<zone>.csv>` | exit 1 on a fault that would cost a build or a launch: see below |
| 6. Build | ZoneTool IW7 `-buildzone mod` | `mod.ff`, `mod.sabl`, `mod.sabs` |

`-holdzone` keeps the process alive until the release file exists; create it
(or terminate the exact process) when the scan is done. The scan never writes
to the target process and reads at most `--max-blocks` nested blocks per weapon.

## Preflight the assembled tree (seconds, no game)

`iw7_mod_preflight.py` reads the whole `zonetool/<zone>` tree and its zone csv before ZoneTool or the game
is started. It is data-driven: it knows asset kinds and fields, never a weapon name.

    python iw7_mod_preflight.py <zonetool/<zone>> --csv <zone_source/<zone>.csv> [--state <file>] [--json <file>]

One pass, about 1.6 s for a 711-file, four-weapon tree:

- every long animation through `iw7_xanim_layout` (the layout that crashes the client) and every model surface
  through `iw7_xsurface_check` (normals that render black), instead of one file at a time by hand;
- every zone csv line has a source file; every name a weapon, attachment, package, material, model or effect
  points at exists in the tree or in the stock lists the csv ignores (`REFERENCE_MISSING`);
- a source file that no csv line builds (`SOURCE_NOT_BUILT`): it will not be in the fastfile;
- sound: every alias list is named by a bank, every bank list exists, every alias has its audio file;
- `catalog.txt` and `behaviours.txt`: each weapon, upgrade, attachment, effect and alias they name is built;
- a model wearing a two-UV (camo) material whose surfaces have no second UV set.

Errors are faults that have cost a build or a launch before; warnings and notes are there to be read once.
A pass is a data check, not a rendering proof.

### Look again only at what changed

With `--state <file>` the preflight hashes, per catalog weapon, everything that weapon reaches (its files,
alias rows, catalog and behaviour lines) and prints which weapons differ from the last accepted state:

    python iw7_mod_preflight.py <zone dir> --csv <csv> --state accepted.json            # what must be looked at
    python iw7_mod_preflight.py <zone dir> --csv <csv> --state accepted.json --accept   # after the in-game pass
    python iw7_mod_preflight.py <zone dir> --csv <csv> --state accepted.json --accept <weapon> [...]

A weapon listed under `unchanged since accepted, no launch needed` reaches byte-identical data. A shared file
(a view model, a texture) puts every weapon that wears it back on the list.

### Measured on the recorded port history (9 Nov 2026)

- Six assembled trees that were built and played: 0 errors (no false alarm), 0.4 to 1.7 s each.
- All 22,734 recorded `.xab`/`.xsb` files replayed: 7 animations carry the crash layout, among them the
  Ray Gun idle of the build that crashed the client on 6 Nov; five belong to content not ported yet.
- The crash animation copied into a clean tree: exit 1 in 1.6 s, and only the weapon that plays it is listed
  for a new in-game pass.
- `iw7_xsurface_check.py` now reads surfaces that carry a second UV set (14 of 43 recorded files were
  unreadable by the count search).

## Is the weapon right, not only loadable

`iw7_weapon_feel_audit.py`, `iw7_weapon_sound_audit.py` and `iw7_weapon_fx_audit.py` compare a weapon with
declared decisions and with the stock population: handling left over from the cloned stock weapon, fire
sounds set up unlike any stock shot, measured loudness, ribbons that are copies of stock ribbons. The compiled
fastfile is then read back through the game's own loader (`../zone-check`). Contract, commands and measured
results: `docs/CONTENT-AUDITS.md`.

## Original weapons from Blender

An original weapon is modelled by a deterministic Blender generator on the skeleton of a stock donor weapon, so
the donor's animations drive it and its hands hold it. One command builds the ZoneTool fragment, the zone rows
and the proofs:

    set IWZ_BLENDER=<blender.exe>  IWZ_TEXCONV=<texconv.exe>  IWZ_TEMPLATE_ROOT=<zonetool/<map> with stock materials and techsets>
    set IWZ_HANDS_XMB=<viewmodel_base_viewhands_iw7.xmb>  IWZ_HANDS_EXPORT=<its XMODEL_EXPORT>  IWZ_DONOR_XANIM=<dump>/xanim
    python -I authored/build_authored_weapon.py authored/exact_change.recipe.json --donor-dump <dump with xmodel/ xsurface/> --out <...>/model/zonetool [--fast]

| Piece | Role |
| --- | --- |
| `authored/<weapon>_gun.py` | the weapon's own generator (Blender Python): parts, bone per part, atlas per part, look materials; EXACT CHANGE: `exact_change_gun.py` |
| `authored/authored_blender.py` | shared Blender helpers: shapes (box, prism, cylinder, tube, curve tube, dome, raised text, booleans, panel grooves, bevels), look-material contract, atlas unwrap, camo UV layer, Cycles bake (albedo, roughness/metalness/mask, tangent normal, AO), copies sharing a UV island, join per (bone, atlas), 3/4 preview |
| `authored/<weapon>.recipe.json` | donor models, bone bindings per model (`bone_map`, `null` drops), world-model offset (`align_bone`), LOD ratios and distances, atlases and their stock template materials per view, image prefix, hand zones for the proof |
| `authored/build_authored_weapon.py` | generic driver: generator, `blender_export.py --all-meshes --uv2 camo`, remap per model, `build_model.py` on the donor skeleton, texture packing, material JSON + techset state/constant buffer copies, `rows.csv`, proofs |
| `authored/authored_weapon_proof.py` | offline proofs, exit code 1 on a failure (below) |

Texture packing (stock formats, `t7_material_pack.py` layouts): `packed_cs` BC7 = sqrt(albedo), alpha 0.04 for
dielectrics or 0.1 + 0.9 metalness; `packed_nog` BC7 = R gloss (from the GGX roughness via the shader's power
2^(20 (1 - sqrt(1 - R))) + 2), G/A octahedral normal with the green flipped (Blender bakes OpenGL, stock is
DirectX), B baked AO; blend (glass) atlases `packed_ng`; `packed_a` BC4 R = camo mask (camo atlases: where a
Pack-a-Punch camo shows) or opacity (blend atlases). Camo atlases get a second UV set = UV1 scaled to the stock
camo density (0.12 UV per inch measured on the stock 1887), so the camo records' basis is the identity; decimated
LODs get their camo UV rebuilt from that scale (the decimator breaks it at seams). A recipe material of `null`
leaves an atlas out of one view (EXACT CHANGE's world model has no hopper glass: the stock world-model glass
technique reads unpacked `_c`/`_sg` images whose layout is not measured yet).

What the proof says, per model: bone names, parents, bind matrices, tag angles/positions and part classes equal
the donor's byte for byte; every vertex of every LOD in blend group 0 (one bone at weight 1) on an existing bone;
per-bone boxes against the donor and the recipe's hand zones (triangles clipped to an x/z window: grip, fore-end,
lever loop, magazine, trigger) within tolerance; every surface on a `_2uvt` material has flag 0x400 and one
24-byte record per vertex (read back with `iw7_xsurface_uv2.parse`); the xmodel and xsurface files read and write
back byte-identical and pass `iw7_xsurface_check`. Preview PNGs: the donor's first-person camera with the hands
and the gun parts posed by the donor's own animations (ours beside the donor), and a 3/4 Cycles render with the
baked maps. They are for information: the look is judged on in-game frames by independent reviewers.

Not proven by these checks: that ZoneTool builds the fragment, that the game draws it, the camo look, the glass
blend, the world-model physics (the donor's `_lod.hkx` is copied as is) and the LOD switch. Tests:
`test_authored_weapon.py` (synthetic data).

## Status

See `STATUS.md` for measured results. Field meanings in BO3's WeaponDef are
not public: `t7_weapon_fields.py` derives them from cross-weapon evidence and
records which offsets were confirmed against which known values.

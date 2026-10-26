# T7 map bridge: Kino der Toten overlay for IW7

Converts a loaded Black Ops III map (Kino der Toten, `zm_theater`) into IW7
rigid models, images and materials packed in one mod fastfile. The server
product (`iw7-paris-server`) places those models above a host Zombies map and
supplies collision/gameplay; this directory only owns extraction and asset
conversion. Game data, dumps, templates and built fastfiles stay local and are
never committed.

## Pipeline

| Step | Tool | Input -> output |
| --- | --- | --- |
| 1. Load the map in BO3 | `boiii.exe -launch`, then `BO3-Console.ps1 -Command "devmap zm_theater"` | owner's legitimate BO3 install |
| 2. World, clip, paths, entities | `t7_map_extract.py --out <export> --expect-map zm_theater` | process memory (read-only) -> `world.json`, vertex/index buffers, `clip.json`, `pathnodes.json`, `mapents.txt` |
| 3. Resident prop meshes | `t7_props_extract.py <export> <export>/props` | static-model LOD0 surfaces resident in memory |
| 4. Materials/images/mesh streaming metadata | `t7_assets_meta.py <export>` | `assets_meta.json` (xpak keys, formats, mesh layouts) |
| 5. Streamed data | `t7_xpak.py` (library) | xpak hash table + LZ4 block groups |
| 6. Compose | `kino_compose.py --one-cell` | KMSH v2 meshes, KIMG images, materials, zone CSV, `layout.json` |
| 7. Serialize | `kino-writer.exe` (`build-writer.ps1 -ZoneToolSource <pinned x64-zt>`) | `xmodel/*.xmb`, `xsurface/*.xsb`, `images/*.iw7Image` |
| 8. Fastfile | `Build-KinoFF.ps1` (`ff-work-profile.json`) | measured community ZoneTool `-buildzone kino` |
| Material template | `make_unlit_template.py <dumpasset output> <dir>` | stock `mopw/zmb_neon_light_blue` -> unlit template |
| Collision | `kino_collision.py --export <export> --out <json>` | clip brushes + triangle soup -> `kino.collision/3` pieces (stock cp_zmb donor, origin, angles) |
| Collision check | `kino_collision_check.py --export <export> --collision <json>` | floor support / body clearance at every BO3 pathnode |
| BO3 sound banks | `t7_sab.py list <bank.sabs> [--min-seconds N]`, `t7_sab.py extract <bank> <index> <out.flac>` | T7 v15 `.sabs` entries (format 8 = whole FLAC files) |
| Mod sound bank | `kino_sound.py --out <zonetool work> --zone mod --template <stock aliases.csv> --music alias=file.flac` | ZoneTool `soundbank/`, `sound/` alias table and `sound_assets/`; the build then writes `mod.sabl`/`mod.sabs` |

`build.sh <name> [compose args]` chains steps 6-8 (environment variables
documented in the script). Steps 1-4 run once per BO3 export; BO3 can be closed
after step 4 because all streamed geometry/pixels are read from the xpak files.
`Build-KinoFF.ps1` copies `soundbank/`, `sound/` and `sound_assets/` from the
build root when present. The bank zone name names the output files, so a mod
uses zone `mod` to ship `mods/<mod>/mod.sabl`/`mod.sabs` beside `mod.ff`; the
Aurora client downloads all three automatically.

The memory layouts were checked against this boiii-launched `BlackOps3.exe`
(asset pool RVA `0x93883F0`; Husky lists `0x94073F0` for another build). The
client `cbrush_t` stride is 112 bytes (the pinned ZoneTool declaration has 104)
and `cmodel_t` is 96 bytes. GfxWorld/material/static-model offsets come from
Husky (Scobalula, GPL-3.0, as maintained in vugi99/C2M); files derived from it
carry that notice.

## IW7 conventions established in-engine

Each item below was isolated with private protected visual witnesses on a test
dedicated (`ops/Test-KinoVisual.ps1` in the server product).

- **Triangle order**: keep BO3 index order. Stock IW7 surfaces store the index
  cross product opposite to the outward normal (measured on a stock candy-box
  model); reversing the order made faces disappear.
- **Normals**: 10:10:10 fields `floor((c + 1) * 1023 / 2 + 0.5)` with the two top
  bits always `11` (61,556 of 61,556 stock vertices). BO3 world normals have top
  bits `00`; without `11` IW7 hides up-facing faces. Tangents keep BO3 words,
  whose top bits carry the bitangent sign.
- **Surfaces per model**: only the first 32 surfaces of a model were drawn
  (floors in surface 38+ vanished). Compose groups geometry by material over
  the whole map (`--one-cell`) with at most 32 surfaces and 30,000 vertices per
  surface.
- **Images**: loaded (non-streamed) images need the full mip chain down to 1x1,
  `NOPICMIP`, and a UNORM DXGI format; sRGB is expressed with
  `IMG_DISK_FLAG_GAMMA_SRGB`. `*_SRGB` formats fail `Create2DTexture` with
  `E_INVALIDARG`. BO3 streamed parts: part 0 holds the low chain (to 4x4), later
  parts only their top mip; 1024+ parts were not needed (images capped at 512).
- **xpak data**: command groups (`count`, decompressed `offset`, 30 commands)
  are followed by `0xCD` padding; the next group header is 128-byte aligned and
  its offset equals the decompressed length.
- **Materials**: names must be flat (`kino_t_<image>`); one material per BO3
  color image keeps the surface count low. The lit `mopw_l_sm_replace` technique
  renders almost black outside the host light grid; the stock unlit technique
  `mopw_unlit_replace_lin_ct_nocast` with a white color tint shows the textures.
- `setsunlight` changes the network sun; vision-set rawfiles and
  `enableouterspacemodellighting` had no visible effect on these models.

## Collision approximation

IW7 cannot load BO3 clip data, so walkable space is rebuilt from clones of
stock `cp_zmb` collision brushmodels (`playerai512x512x8` is 258x258x10,
`playerai128x128x8`, `player64x64x8`, `player64x64x64/128/256`; origin at the
bottom-face center). The generator voxelizes player-blocking brushes and the
triangle soup at 16 units, keeps space reachable from the pathnodes, fits
floor plates to each walkable sheet (slopes and stairs become ramps) and stands
plates/pillars along sheet boundaries up to the obstacle top (at most floor +
96). Brushes with origin-centred bounds (submodel local space) or enclosing a
pathnode are not world blockers and are ignored.

In-engine findings (private witnesses): clones block players and
`playerphysicstrace`, not bullets; `hide()` unlinks them (no collision); about
240 extra visible entities above the Spaceland baseline drop the server
(`sv_running 0`, no message), including deleted entities still pending, so the
server streams a fixed pool of clones near players instead of spawning all
pieces. Current set: 4,451 pieces; 1,362 nodes, 138 without a floor within
reach and 169 with a piece inside the body margin (mostly the theatre centre
and stage props).

## Current limits

Decals, transparent glass, skinned props and images without streamed pixels
(36 materials, gray fallback) are omitted. No lightmap or baked lighting: the
unlit textures look flat. Collision, navigation and gameplay are server work.
Build and visual evidence: `%USERPROFILE%/Documents/IW7-Runtime/kino-*`.

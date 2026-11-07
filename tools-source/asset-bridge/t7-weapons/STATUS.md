# T7 weapons bridge: measured status

Evidence levels: PROVEN_LOCAL (observed on this machine with real BO3 data),
NOT_PROVEN (designed, not yet run end to end), BLOCKED.

## 2026-11-05: extraction and conversion of `zm_levelcommon`

Inputs: owner's BO3 install (`zone/`, 101 GB, DLC and Chronicles), BO3
Unranked Dedicated Server executable build 4500243 (SHA-256 `3df511d7...`),
owner-fork ZoneTool branch `codex/t7-asset-address-log` built locally
(Release and Debug).

| Step | Result | Level |
| --- | --- | --- |
| T7 zone load in ZoneTool | `zm_levelcommon`: 25,982 assets incl. 161 `weapon`, 582 `fx`, 4,599 `xanim`, 1,551 `xmodel` | PROVEN_LOCAL |
| Asset address log + resident hold | `-assetlog` + `-holdzone`: all addresses logged, zone kept resident for read-only scans | PROVEN_LOCAL |
| Weapon definition scan | `ray_gun_zm`: view/world models, 1p/3p muzzle FX, impact FX, projectile trail FX, fire/loop/explosion/reload sound aliases, upgrade link `ray_gun_upgraded_zm`, full anim name table | PROVEN_LOCAL |
| Clip size | WeaponVariantDef `+0x194` (i32): unique offset matching Ray Gun 20, Ray Gun PaP 40, Thundergun 2, Wunderwaffe 3 | PROVEN_LOCAL |
| Max/start ammo | WeaponDef (`variant+0x18`) `+0x8F8` / `+0x8FC`: Ray Gun 160/160, PaP 200/200, Thundergun 12/12, Wunderwaffe 15/15. Ordinary guns store a different quantity there (MR6 4/10, Kuda 7/7); the flag at `+0x8F0` (2 for these Wonder Weapons) is not yet decoded | PROVEN_LOCAL for the listed Wonder Weapons only |
| Anim table | WeaponDef `+0x60` points to an array of anim name strings; slot meaning is taken from the anim names (`idle`, `fire`, `reload`, `pullout`, `first_raise`, `putaway`, `sprint_*`, `ads_up/down`, `crawl_*`, `swim_*`, `wall_run_*`) | PROVEN_LOCAL (names); slot enum indices not decoded |
| T7 -> IW7 anim conversion | 4,599 / 4,599 anims after two converter fixes (below) | PROVEN_LOCAL (files written; engine playback NOT_PROVEN) |
| T7 -> IW7 model conversion | 1,541 models, 6,325 surfaces; Ray Gun and Thundergun view meshes converted | PROVEN_LOCAL (files written; rendering NOT_PROVEN) |
| Streamed meshes | 181 meshes not readable from `zm_levelcommon.xpak`, incl. Apothicon Servant (`wpn_t7_zmb_zod_idg_*`) and Ragnarok DG-4 (`wpn_zmb_dlc1_talon_spikes_view`): their data lives in their own map's xpak; load that map zone to convert them | NOT_PROVEN |

### ZoneTool converter fixes (owner fork)

1. The T7 -> IW7 anim converter wrote converted quaternions into arrays sized
   by the source counts without bounds checks. Animations with more than 255
   frames store `frameCount + 1` inline key frame indices in `dataShort`
   (observed: `vm_raygun_t7_idle`, 300 frames, `6 | 0 1 50 116 222 281 300`);
   the converter copied one index, desynchronised and overran the heap. The
   process later exited with code 127 mid-zone (first after 62 anims). Fixed by
   copying all indices and bounds-checking every write; refused layouts are
   logged instead of corrupting memory.
2. `-verifyzone` never finished because no fastfile name was set for the
   finish hook; it now sets it.

### Material channel mapping (design, from measured stock IW7 textures)

IW7 weapon materials (`m2o_l_sm_replace_..._vm` techsets) bind packed images:
`*_packed_cs` RGB = albedo, A = specular (low values); `*_packed_nog`
R = gloss, G = normal Y, B = occlusion, A = normal X; `*_packed_a` alpha.
GrayWolf exports BO3 bindings per material (albedo, `xy` normal, occlusion R,
roughness = inverted gloss R, specular, emissive). Packing BO3 maps into these
layouts is the planned image step: NOT_PROVEN, needs a rendered comparison.

## Wonder Weapon inventory (from the BO3 data, not memory)

Models found by GrayWolf / weapon assets seen by ZoneTool:

| Weapon | BO3 internal name(s) | Source zone(s) |
| --- | --- | --- |
| Ray Gun | `ray_gun_zm`, `ray_gun_upgraded_zm` | zm_levelcommon |
| Ray Gun Mark II | `wpn_t7_zmb_hd_raygun_mk2_*` | Chronicles maps |
| Ray Gun Mark III | `raygun_mark3_zm`, `raygun_mark3lh_zm` (+ upgraded) | zm_levelcommon, zm_stalingrad |
| Thundergun | `thundergun_zm` (+ upgraded) | zm_levelcommon, zm_genesis, Chronicles |
| Wunderwaffe DG-2 | `tesla_gun_zm` (+ upgraded) | zm_levelcommon, zm_factory, zm_sumpf, zm_asylum |
| Apothicon Servant | `idgun_0..3_zm` (+ upgraded) | zm_zod, zm_genesis |
| Li'l Arnie | `octobomb_zm` (+ upgraded) | zm_zod, zm_genesis |
| Ragnarok DG-4 | `hero_gravityspikes_melee_zm`, model `wpn_zmb_dlc1_talon_spikes_*` | zm_castle |
| Wrath of the Ancients | `wpn_t7_zmb_bow_*` (base, storm, wolf, rune, demon) | zm_castle |
| KT-4 / Masamune | `wpn_t7_zmb_dlc2_mirg_*` | zm_island |
| Gauntlet of Siegfried | `wpn_t7_zmb_dlc3_gauntlet_dragon_*` | zm_stalingrad |
| Apothicon Sword | `wpn_t7_zmb_zod_sword1/2_*` | zm_zod |
| Wave Gun / Zap Guns | `wpn_t7_zm_hd_wavegun_*` | zm_moon |
| 31-79 JGb215 | `wpn_t7_zmb_hd_shrinkray_*` | zm_temple |
| Origins staffs | `wpn_t7_zmb_hd_staff_*` (fire, ice, wind, lightning) | zm_tomb |
| Tacticals | Gersch device, QED, Matryoshka dolls, Cymbal Monkey | zm_cosmodrome, zm_moon, zm_levelcommon |

Weapon-asset names for the map-specific entries are confirmed per zone when
that zone is scanned.

## 2026-11-05: Ray Gun materials packed

`t7_material_pack.py` packed the six Ray Gun view materials (plastic, metal,
power, meter, reticle, glass) against the stock `weapon_zappers_dischord_camo`
template with Microsoft texconv May 2026 (SHA-256 `dcfdec10...`, valid Microsoft
signature): 7.9 MB of BC7 DDS with `--max-size 1024` (16 MB at source size).
Material JSONs bind the packed colour/specular, normal/occlusion/gloss, alpha
and emissive images. Rendering: NOT_PROVEN.

## 2026-11-06: more WeaponDef fields and the first Ray Gun fastfile

Fields located by cross-weapon comparison (Ray Gun, Ray Gun PaP, Thundergun,
Wunderwaffe, MR6, Kuda), PROVEN_LOCAL as memory values; semantic names are
inferences consistent with every compared weapon:

| WeaponDef offset | Ray Gun / PaP / Thundergun / Wunderwaffe / MR6 / Kuda | Meaning |
| --- | --- | --- |
| `+0xA1C` i32 | 330 / 330 / 950 / 1000 / 120 / 83 | fire time ms (Ray Gun ~181 RPM, Kuda ~720 RPM) |
| `+0xFB4` i32 | 1500 / 2000 / 0 / 1 / 0 / - | explosion inner damage |
| `+0xFB8` i32 | 64 / 64 / 0 / 110 / 0 / - | explosion radius |
| `+0xFC0` i32 | 300 / 300 / 0 / 1 / 0 / - | explosion outer damage |
| `+0xFEC` i32 | 3200 / 4200 / 2000 / 2250 / 0 / - | projectile speed |
| `+0x1004` f32 | 10 / 10 / 0.5 / 30 / 0 / - | projectile lifetime s |
| `+0xB14` i32 | 1900 (Ray Gun) | candidate reload add time; the reload anim's `battery_in` notetrack is at 1833 ms |

Converted Ray Gun anims pass the independent IW7 `.xab` envelope check
(`animation/xab_preflight.py`): reload 115 frames / 30 fps (3833 ms) with
`wpn_ray_reload_open`, `..._battery_out`, `..._battery_in`, `..._close`
notetracks; first raise keeps `wpn_ray_1straise`.

`iw7_weapon_author.py` turns a spec (models, anims, clip 20, ammo 160, fire
330 ms, projectile 1500/300 damage, radius 64, speed 3200, 10 s) into an IW7
weapon and anim package from stock templates (`iw7_facemelter_zm`,
`iw7_zapper_mp_package`, projectile fields from `iw7_zapper_grey`); timers
come from the anim durations.

The owner-fork ZoneTool in IW7 mode built `bo3wpn.ff` (6,608,548 bytes) from
these sources, referencing stock assets through `ignore,<csv>` lists of
`cp_zmb` and the techset zones; with `common_cp` and `cp_zmb` loaded, the IW7
engine (in ZoneTool) registered every asset of the zone, including the weapon
`iw7_raygun_zm`, without errors (PROVEN_LOCAL, offline). Not yet established:
loading on a client, rendering, animation playback, firing, sound, the
auto-download, and other maps (stock references are Spaceland-only).

## 2026-11-06: client crash on the Ray Gun idle (long-animation layout)

The first client witness (stock iw7-mod client, mod downloaded automatically)
crashed the moment the player switched to the Ray Gun: access violation
reading `0x200` in `iw7_ship+0xd7b545`, a word read from a null index list at
key 256 of a 273-key channel. `vm_raygun_t7_idle` has 300 frames; BO3 keeps
every key frame index inline in dataShort, but IW7 does so only below 64 keys.
A larger channel keeps a lookup table inline (the key at every 256th position,
then the last key: `((keys - 2) >> 8) + 2` entries) and its index list in
`XAnimParts::indices`, rotation channels first. `iw7_xanim_layout.py` checks
this: 27 of 27 long stock cp_zmb animations pass, the converted idle fails
(12 large channels, no index list). Fix: ZoneTool converter, owner fork.
Short animations (under 256 frames) have the same layout in both games.

## 2026-11-06: black Ray Gun viewmodel (vertex normal high bits)

With the crash fixed, the Ray Gun drew black on the client while the IW7 arms
next to it were lit. Albedo, packing and texture slots were correct (packed
albedo matches the BO3 source in sRGB). The vertex normals decode the same way
in both games and agree with the triangles, but IW7 sets the two high bits of
every model vertex normal (180,445 of 180,445 vertices in 300 stock cp_zmb
surfaces) and BO3 leaves them clear. Fix in the ZoneTool converter (owner fork
PR7); `iw7_xsurface_check.py` checks this: 4531 stock surface files pass, 0
fail (126 special-format files are not parsed); the old Ray Gun fails, the
reconverted Ray Gun and BO3 Dempsey view hands pass.

Placement: BO3 view hands have no clavicle (`tag_torso` -> `j_shoulder_*`);
IW7's have `tag_torso` -> `j_clavicle_*` -> `j_shoulder_*`, so BO3 weapon
animations played on IW7 arms put bones under the wrong parents. The witness
now shows the BO3 hands model with the BO3 weapon (server `setviewmodel`);
retargeting to IW7 arms is a separate option.

## 2026-11-06: animation codec and view-hand retargeting

`iw7_xanim_codec.py` decodes every IW7 animation channel (all frames) and
encodes a valid layout (every animated channel keyed each frame: full
quaternions, unsigned-short translations). On 4029/4029 stock cp_zmb
animations it consumes every data array exactly and every key index sequence
starts at 0 and rises strictly (a channel may stop before the last frame); a
decode/encode/decode round trip stays within 0.004 degrees and 0 units.
dataByte: under 256 frames, rotation index bytes, then per animated
translation channel its bone byte followed by its index bytes, then the static
and untranslated bone groups; at 256+ frames, the animated translation bones
then those two groups. A first version that put the whole order list first
passed the consumption check alone (same total length) but misread short
animations and crashed the client on the retargeted fire animation
(`iw7_ship+0xd7a002`, translation index search); the index-sequence check now
catches it. A few stock character animations list a channel past their names.

Witness findings that drove `t7_vm_retarget.py`: the converted Ray Gun was
drawn at the view origin with IW7 hands and with BO3 hands alike. BO3 frame 0
on the BO3 hands is a normal hip pose relative to `tag_camera` (wrist about
10 units ahead, 5 right, 6 down), as is IW7 stock frame 0 on IW7 hands, but
IW7 animations keep `tag_weapon` equal to `tag_weapon_right` (0.00 degrees,
0 units in stock) while BO3 animations leave it unanimated, and BO3 hands do
not have it. The retargeted Ray Gun animations put both IW7 wrists and the gun
exactly on the BO3 ones (0.001 units, 0.0 degrees; fingers within 0.2) on every
frame of all 11 Ray Gun animations. Client confirmation is pending.

Translation scale: the stored animated-translation size is the step per key
unit (range / 255 or range / 65535; stock medians 0.0074 and 0.0005), and the
value is mins + step * key. A codec version that treated it as the full range
also round-tripped perfectly (symmetric error) but made the engine place
translated bones thousands of units away: the client showed no view model with
re-encoded stock zapper animations. The discriminating check is now the stock
IW7 convention itself: decoded with this codec, tag_weapon equals
tag_weapon_right on every frame of stock view animations (within 0.1 units and
0.2 degrees of quantization).

Image formats: stock weapon material images are BC7_UNORM (`_packed_cs`,
`_packed_nog`; colour stored as sRGB values without an sRGB format) and
BC4_UNORM for `_packed_a` (single red channel), read from the GfxImage headers
of stock images. The first packer wrote `_packed_a` as BC7 with the alpha in A
and red 8/255, and `_packed_cs` as BC7_UNORM_SRGB: the Ray Gun drew black even
with stock animations holding it normally in the IW7 hand. `t7_material_pack.py`
now writes the stock formats with the alpha in red.

Bone list: stock view animations list every hand bone (static values for the
ones that do not move). A retargeted animation that listed only the animated
bones drew the arms collapsed onto the view origin; with every hand bone
listed (bind values for the still ones), the client shows the IW7 arms holding
the Ray Gun in the right hand at the BO3 position, firing and reloading through
client input (private witness 2026-11-06). The gun itself still draws black.

Black gun, resolved: with stock Facemelter images bound to the Ray Gun
materials the gun still drew black, so the images were not the cause. The camo
template's technique (`..._2uvt_...`) reads a second UV set (stock weapon
surfaces with it carry SURF_FLAG_SECONDUV); BO3 weapon meshes have one. With
single-UV templates (`m2o_l_sm_replace_i0c0s0o0n0p0_vm`, alpha parts
`..._i0c0s0o0n0pa0_bsted_vm`) the client draws the Ray Gun textured and lit in
the IW7 hand, with the BO3 hip pose, fire and reload animations (private
witness 2026-11-06). Setting SURF_FLAG_VERTCOL_NONE (which stock surfaces
carry) made no visible difference and is not part of the pipeline.
`t7_material_pack.py` refuses two-UV templates.

## 2026-11-06: grip, sounds and aiming

Grip: mapping each IW7 hand bone through its own bind pose bent the fingers
up to 38 degrees from BO3's. Each arm now takes the BO3 world orientation
through one axis map measured at the wrist binds (right side about 180
degrees around Z, left side none; constant within 4 degrees over the hand).
Client witness: the IW7 hand holds the Ray Gun as BO3 does. PROVEN_LOCAL.

Sounds: `t7_weapon_sound.py` writes the bank for the BO3 Ray Gun aliases
(fire, secondary layers, reload notetracks, projectile loop, impact). Stock
alias rows carry duck references that the mod build cannot resolve (ZoneTool
FATAL), so the duck column is cleared. Built mod.sabl/mod.sabs are
auto-downloaded with mod.ff (byte-identical). Audible playback is NOT_PROVEN:
the witness has no audio capture.

Aiming: stock IW7 ADS raise/lower animations animate one bone, `tag_ads`
(hands root under `tag_view`); stock idle + ads_up end puts the gun on the
camera axis (y = 0.00) for the zapper, G18 and AR57. Earlier attempts that
listed every hand bone in the ADS animations replaced the hip pose with their
values in game (the engine plays them as an absolute override of the listed
bones, also at hip after lowering). `root_ads` writes `tag_ads` only; the base
animations leave `tag_view`/`tag_ads` out as stock does. Client witness with
the ADS key held (scenario hold_start): zoomed view, the Ray Gun's rear sight
on the reticle; hip pose unchanged. PROVEN_LOCAL. The scenario runner's
`press` is a 200 ms tap: earlier ADS captures were taken after the weapon was
lowered, including a stock Facemelter control.

## 2026-11-06: lit Ray Gun (emissive parts and glass)

The converted Ray Gun looked switched off. Its BO3 lit parts (energy tube
`power`, rear gauge `meter`, sight `reticle`) bind emissive maps, and the tube
and gauge sit under `glass`, a BO3 `blend` material. The glass had been built
from an opaque `replace` template: drawn solid and dark, it hid both; emissive
intensity x8 and a fully transparent glass alpha changed nothing (client
probes), a z-buffered projection of the model by material from the hip
camera showed the glass in front of them. Glass now uses the stock
Headcutter glass technique (`m2o_l_sm_ndw_blend_i0c0s0n0pa0_vm`) and the lit
parts the stock emissive weapon technique (`m2o_l_sm_replace_i0c0s0o0n0e0p0_vm`,
`emissivePara` 1), both loaded by cp_zmb. Client witness: blue animated
energy tube, red/yellow/green gauge and red reticle lit. PROVEN_LOCAL. BO3's
scrolling of the tube texture is not reproduced (no scroll in the template).

## 2026-11-06: BO3 effects, reading (step 1 of the converter)

GrayWolf has no FX kind and the BO3 mod tools (with .efx sources) are not
installed, so effects are read from the zone held resident by the ZoneTool
fork. `t7_fx_read.py` reads every FxEffectDef: header 0x90, elements 0x260
(stride confirmed on all 582 effects / 5809 elements of zm_levelcommon:
count * 0x260 <= totalSize for every effect). Element type at +0xc8 matches
the visual it carries: material for types 0-6 (5 = geometry trail), xmodel
7, light description 8 (325/326), effect 14 (234/234). PROVEN_LOCAL.

Ray Gun (base and upgraded): 10 effects (1p/3p muzzle, geotrail, ring
emitter, impact), 100 elements, 13 particle materials (ei/gfx_ring_thin,
ei/gfx_water_splash_em, ei/gfx_light_phosphorous_em, ...) and 3 omni lights.
BO3 tints neutral textures through colour samples, so the colour/size/velocity
samples (pointers at +0xd0..+0xe8, interval counts after the type byte) are
the next step, then BO3 particle materials, then an IW7 ParticleSystemDef
writer (planned as a ZoneTool fork converter, reusing its IW7 particle dump).
NOT_PROVEN in game: the Ray Gun still uses IW7 placeholder effects.

## 2026-11-06: BO3 effect curves decoded (step 2)

Element counts: +0xc9 visuals, +0xca velocity intervals, +0xcd visual-state
intervals (samples = intervals + 1); established by reading 5 velocity
samples where +0xca = 4 and 6 visual samples where +0xcd = 5, with the next
element's data right after. Velocity samples (+0xd0) are BO2's 0x60 layout;
visual-state samples (+0xe0) are 0x50: base and amplitude of colour RGBA
bytes, rotation delta/total, size[2], scale and 4 more dwords. Spawn (looping
interval/count or one-shot count) at dwords 2-3 and lifespan (int ms) at
15-16 match the Ray Gun's behaviour (rings every 50 ms during the 1p muzzle,
150 ms life). Ray Gun: lime green (64,255,0) fading to alpha 0; impact
(128,255,0); smoke cyan-green. PROVEN_LOCAL (decode); arrays at +0xd8/+0xe8
and dwords 7-14 are not named yet.

Atlas: dword 48 bytes 0/1 of a sprite element are log2 columns/rows (Ray
Gun: smoke and bubbles 8x4 on 2048x1024 images, splash 4x4 on 1024x1024,
splash 2x1 on 1024x512, debris 2x2 on 512x512; static 1x1).
Effect materials: all Ray Gun BO3 particle materials are
`effect_lit_emissive_blend` (one `effect_lit_specular_blend`, one
`effect_distortion`). `t7_fx_material_pack.py` maps them to stock IW7
`eq_effectunlit_*_evc` techniques loaded by cp_zmb (additive for glows,
blend for smoke/debris, `zfeather_*_tab` for atlases). 11 of 12 Ray Gun
materials converted; heat distortion skipped. Not yet drawn in game.

## 2026-11-06: IW7 particle systems, read and write (`iw7_vfx.py`)

`iw7_vfx.py` decodes the ZoneTool `.iw7VFX` stream (`vfx::binary` in the
fork's `iw7/assets/particle_system.cpp`) into JSON named after `structs.hpp`
and encodes it back. The writer replays `assetmanager::dumper`, including its
pointer de-duplication (OFFSET tokens are recomputed from the pointer values
kept in the structs, not copied). Bytes that no named field covers are kept
in `_gaps`. This replaces the planned ZoneTool-side writer: the converter can
emit `.iw7VFX` from Python.

| Check | Result | Level |
| --- | --- | --- |
| Round trip, bytes -> model -> JSON text -> model -> bytes, strict (no pointer reassigned) | 1195 / 1195 stock dumps byte-identical (cp_zmb 1164, patch_cp_zmb 31) | PROVEN_LOCAL |
| De-duplication in stock | 2617 OFFSET tokens, all to an earlier asset (shared material, light, sub-system); no string or array offsets; no offset to the root entry | PROVEN_LOCAL |
| JSON edit (material rename in `vfx_muz_ark_green_v_a`) -> `--from-json` -> decode | renamed material read back, other data unchanged | PROVEN_LOCAL (file level; not built into a fastfile, not seen in game) |

Module types seen (instances / files): INIT_SPAWN 6998/1193, INIT_MATERIAL
6046/1047, INIT_ATTRIBUTES 5971/1139, COLOR_GRAPH 5660/934,
INIT_RELATIVE_VELOCITY 5053/1005, SIZE_GRAPH 4326/879, INIT_ATLAS 3685/797,
INIT_SPAWN_SHAPE_BOX 3487/793, INTENSITY_GRAPH 3361/700, INIT_ROTATION
3346/778, INIT_MIRROR_TEXTURE 2417/521, VELOCITY_GRAPH 1832/576, INIT_TAIL
1215/499, INIT_SPAWN_SHAPE_SPHERE 1130/367, SIZE_LERP 958/421,
INIT_ORIENTED_SPRITE 935/254, INIT_SPAWN_SHAPE_CYLINDER 851/252,
ROTATION_GRAPH 694/314, GRAVITY 645/315, INIT_ROTATION_3D 626/237,
INIT_LIGHT_OMNI 523/489, FORCE 522/205, INIT_MODEL 503/203, COLOR_LERP
382/208, INIT_RUNNER 378/248, INIT_SPAWN_SHAPE_ELLIPSOID 128/40,
PHYSICS_RAY_CAST 124/79, INIT_BEAM 116/27, INIT_OCCLUSION_QUERY 115/65,
POSITION_GRAPH 110/27, INIT_CAMERA_OFFSET 105/29, EMISSIVE_GRAPH 104/35,
TEST_IMPACT 93/54, INIT_FLARE 85/46, INIT_GEO_TRAIL 68/48, INIT_DECAL 55/49,
EMISSION_GRAPH 51/26, TEST_DEATH 45/24, PHYSICS_LIGHT 44/26,
ROTATION_GRAPH_3D 36/15, INIT_CLOUD 34/28, INIT_SPAWN_SHAPE_MESH 15/6,
INIT_SOUND 14/14, INIT_PLAYER_FACING 8/8, INIT_LIGHT_SPOT 2/2, TEST_AGE 2/2,
ATTRACTOR 1/1, INIT_PARTICLE_SIM 1/1, TEST_BIRTH 1/1. Never seen:
INIT_VECTOR_FIELD, PARENT_VELOCITY_GRAPH, TEST_GRAVITY, TEST_POS (their
layouts are untested).

Struct layouts that the data contradicts (bytes kept through `_gaps`, field
meaning NOT_PROVEN):

* INIT_ATLAS: 1 or 2 byte flags (0/1) after `m_loopCount`, past ZoneTool's
  20-byte struct (3284 of 3685 modules).
* TEST_AGE: the age is a float at union `+12` (0.2, 0.03), overlapping
  `m_useVelocityOptions` and padding; ZoneTool's `m_age` at `+48` reads 0.
* INIT_SPAWN_SHAPE_MESH: a byte flag at union `+36`, between
  `m_numMeshAssets` and the linked asset list (1 module).

### Ray Gun effect templates (stock cp_zmb, read-only)

Screened with `iw7_vfx.py --summary` (names, Wonder Weapon packages
`vfxpkg/iw7_zmb_wor_*`, the Grey zapper's `projTrailEffect` and
`projExplosionEffect`, colour graph samples). The green mostly comes from the
materials; colour graphs and lerps scale it.

| Role | Particle system | Emitters (element types) | Module types | Materials |
| --- | --- | --- | --- | --- |
| Muzzle flash, view | `vfx/iw7/core/muzflash/ark/vfx_muz_ark_green_v_a` | 4 (3 sprite, 1 omni light) | INIT_SPAWN, INIT_SPAWN_SHAPE_BOX, INIT_ATTRIBUTES, INIT_MATERIAL, INIT_ATLAS, INIT_ROTATION, INIT_RELATIVE_VELOCITY, INIT_LIGHT_OMNI, COLOR_GRAPH, COLOR_LERP, SIZE_GRAPH | `eq/vfx_pyro_flash_ark_green_01`, `eq/vfx_vol_light_glow_blobby_soft_z10_eye20`, `eq/vfx_vol_smk_wispy_swirl_lg`; light `light_fx_default` |
| Muzzle flash, world | `vfx/iw7/core/muzflash/ark/vfx_muz_ark_green_w_a` | 5 (3 sprite, 1 tail, 1 light) | as above + INIT_TAIL | as above + `eq/vfx_pyro_flash_ark_green_p` |
| Muzzle flash, view (Dischord) | `vfx/iw7/core/muzflash/zmb/vfx_muz_zmb_dchord_v_a` | 8 (3 sprite, 4 oriented, 1 light) | as the Ark flash + INIT_ORIENTED_SPRITE, INIT_MIRROR_TEXTURE, INIT_SPAWN_SHAPE_SPHERE, SIZE_LERP | Ark green flash set + `eq/vfx_energy_shockwave_04`, `eq/vfx_dist_ring_fade`, `eq/vfx_energy_elec_ring_loop_int` |
| Trail, minimal | `vfx/iw7/_requests/mp/vfx_plasma_trail_friendly` | 2 (sprite, geo trail) | INIT_SPAWN, INIT_GEO_TRAIL, INIT_ATTRIBUTES, INIT_MATERIAL, INIT_RELATIVE_VELOCITY, COLOR_GRAPH, INTENSITY_GRAPH, SIZE_GRAPH | `eq/vfx_pyro_muzflash_vfx_muzzle_flash_glow`, `ev/vfx_vol_smk_geotrl_wispy_01_ul_ng` |
| Trail, energy | `vfx/iw7/_requests/mp/vfx_sentry_shock_proj_trail` | 3 (2 sprite, geo trail) | INIT_SPAWN, INIT_SPAWN_SHAPE_BOX, INIT_GEO_TRAIL, INIT_ATTRIBUTES, INIT_MATERIAL, INIT_ROTATION, INIT_RELATIVE_VELOCITY, COLOR_GRAPH, SIZE_GRAPH | `ev/vfx_energy_elec_trail_01_gray`, `eq/vfx_vol_light_glow_lensflare_noring_z10` |
| Trail, Grey zapper projectile | `vfx/iw7/core/zombie/ufo/weapon/vfx_ufo_alien_weapon` | 12 (9 sprite, 2 geo trail, 1 tail) | INIT_SPAWN, INIT_SPAWN_SHAPE_SPHERE, INIT_GEO_TRAIL, INIT_TAIL, INIT_ATTRIBUTES, INIT_MATERIAL, INIT_ATLAS, INIT_ROTATION, INIT_MIRROR_TEXTURE, INIT_RELATIVE_VELOCITY, COLOR_GRAPH, INTENSITY_GRAPH, SIZE_GRAPH, SIZE_LERP, VELOCITY_GRAPH, GRAVITY | `eq/vfx_energy_tesla_bolt_stretch_anim`, `eq/vfx_energy_elec_blast_anim`, `eq/vfx_energy_elec_core_exp_anim_16f_01`, `eq/vfx_energy_rim_atlas_01`, `eq/vfx_energy_shockwave_blast_anim_01_z100`, `ev/vfx_vol_smk_geotrl_hot_core_01`, `ev/vfx_vol_smk_geotrl_billow_02`, `eq/vfx_alien_glow_kraken_cone`, 3 glow/smoke |
| Impact, green energy | `vfx/iw7/core/zombie/weapon/impact/vfx_zmb_impact_green_ch1` | 7 (3 sprite, 3 tail, 1 light) | INIT_SPAWN, INIT_SPAWN_SHAPE_BOX/CYLINDER, INIT_TAIL, INIT_ATTRIBUTES, INIT_MATERIAL, INIT_ATLAS, INIT_MIRROR_TEXTURE, INIT_ROTATION, INIT_RELATIVE_VELOCITY, INIT_LIGHT_OMNI, COLOR_GRAPH, INTENSITY_GRAPH, SIZE_GRAPH, VELOCITY_GRAPH, GRAVITY | `eq/vfx_energy_plasma_tendrils`, `eq/vfx_energy_plasma_ball_loop`, `eq/vfx_pyro_flash_energy_plasmic_ds`, `eq/vfx_pyro_flash_ark_blue_p`, `eq/vfx_pyro_spark_single`, `eq/vfx_dist_ripple`, `el/gfx_test01` |
| Impact, green burst | `vfx/iw7/core/zombie/weapon/ark/vfx_zmb_ark_green_s` | 7 (6 sprite, 1 tail) | INIT_SPAWN, INIT_SPAWN_SHAPE_BOX/SPHERE, INIT_TAIL, INIT_ATTRIBUTES, INIT_MATERIAL, INIT_ATLAS, INIT_MIRROR_TEXTURE, INIT_ROTATION, INIT_RELATIVE_VELOCITY, COLOR_GRAPH, INTENSITY_GRAPH, SIZE_GRAPH, VELOCITY_GRAPH | `eq/vfx_energy_plasma_explosion_anim_64f`, `eq/vfx_energy_plasma_ball_loop`, `eq/vfx_zmb_energy_wave`, `eq/vfx_energy_rim_atlas_01`, `eq/vfx_vol_smk_wispy_01_anim_unlit` |
| Impact, Grey zapper | `vfx/iw7/core/zombie/ufo/weapon/vfx_ufo_alien_weapon_impact` | 11 (7 sprite, model, oriented, spark cloud, light) | the impact set above + INIT_CLOUD, INIT_MODEL, INIT_ROTATION_3D, EMISSION_GRAPH, FORCE, ROTATION_GRAPH | `eq/vfx_energy_emp_bolt_02_atl` (+`_z20_int1`), `eq/vfx_alien_cortex_blast_center`, `eq/vfx_alien_mist_a_lp_add_z40_dlc`, `eq/vfx_glow_hard_white_streaks_uncmp_nf_z100`, `el/vfx_spkcld_spark_simple_gray`, 2 smoke; models `vfx_energy_emp_bolt_b_01..06` |
| Impact, small energy (Facemelter, Headcutter) | `vfx/iw7/core/zombie/vfx_zmb_facemelter_imp`, `vfx/iw7/core/zombie/vfx_zmb_headcutter_imp` | 3 sprites | INIT_SPAWN, INIT_SPAWN_SHAPE_SPHERE, INIT_ATTRIBUTES, INIT_MATERIAL, INIT_ATLAS, INIT_MIRROR_TEXTURE, INIT_ROTATION, INIT_RELATIVE_VELOCITY, COLOR_GRAPH, SIZE_GRAPH | `eq/vfx_energy_elec_blast_anim`, `eq/vfx_energy_elec_core_exp_anim_16f_01`, `eq/vfx_dist_fire_flames_01_anim` |

Next: map BO3 FxElemDefs (`t7_fx_read.py`) onto these templates (sprite ->
BILLBOARD_SPRITE with INIT_MATERIAL, COLOR_GRAPH, SIZE_GRAPH; trail ->
GEO_TRAIL; light -> INIT_LIGHT_OMNI), build a candidate into the mod zone and
compare in game. Whether ZoneTool `-buildzone` and the client accept an edited
`.iw7VFX` is NOT_PROVEN.

## 2026-11-06: owner texture cap 512 px

Owner decision: weapon and effect textures capped at 512 px (and no hero
weapons). `t7_fx_material_pack.py --max-size` keeps atlas grids aligned
(the whole sheet scales). Ray Gun at 512: weapon images 9.7 -> 2.9 MB, effect
images 12 -> 2.0 MB (DDS on disk).

## 2026-11-07: BO3 recoil (gun kick, view kick)

Owner: the weapon must kick as in BO3, not with the IW7 template's values.
Two WeaponDef blocks follow BO2's order (reduced-kick bullets/percent, gun
kick pitch/yaw min/max, accel, speed max, speed decay, static decay, view kick
pitch min/max, min magnitude, yaw min/max): ADS at +0x1208, hip at +0x1268.
Evidence: the hip block of every zm_levelcommon Wonder Weapon reads accel
1000 / speed max 1200 / decay 100 / static 2, the values IW7 carries in the
same fields; the Thundergun and Wunderwaffe differ only by a stronger hip view
kick (100-110). Ray Gun: hip gun kick pitch -30..-35, yaw -2..18, view kick
40..45; ADS gun kick -35..-40, accel 825, speed max 2000. `t7_weapon_kick.py`
copies them. PROVEN_LOCAL (decode); in-game feel NOT_PROVEN. View-kick centre
speed and idle/sway blocks are not mapped yet.

## 2026-11-07: Thundergun, first generic port in game

`t7_port_weapon.py` ported the Thundergun end to end (no weapon-specific
code). Client witness (fire, reload, ADS, burst): textured, lit model (orange
grilles, red sight), BO3 muzzle blast and shockwave ring, clip 2/12, reload
and ADS poses correct. PROVEN_LOCAL. Two fixes came out of it:

* Surfaces: converted `.xsb` are named after BO3 surface assets plus a hash,
  not after the model; `model_surfaces()` takes every name the `.xmb` lists
  that has a surface file (the first build drew stretched spikes).
* Idle pose: the hip idle held the gun turned about 40 degrees in the hands.
  A bone listed with no rotation channel is identity in XAnim; the
  retargeter's skeleton pose read it as the bind rotation, and the BO3 hands
  bind `tag_weapon_right` off-axis. The Thundergun idle is the first
  animation seen leaving that bone unkeyed. Fixed in `Skeleton.pose`, test
  added; converted idle now matches fire frame 0. Client recheck pending.

Effects with visual arrays: a BO3 element with several visuals (one picked
per particle) now keeps all of them. Export and material packing take every
array material, and the converter lists one INIT_MATERIAL linked asset per
converted material, as 771 of 5932 stock IW7 material modules do (survey of
the 1164 stock cp_zmb particle systems). Partly converted arrays are reported
(`partial`). Thundergun smoke cloud now builds; knockback ground pending the
re-export.

## 2026-11-07: DG-2, second generic port

`t7_port_weapon.py --weapon tesla_gun_zm` ran every stage with no
DG-2-specific code (62 zone lines, Pack-a-Punch weapon and attachments,
19 effects built). Two generic fixes came out of it:

* Sounds: a weapon may name generic BO3 aliases kept outside the zones the
  port reads (`dryfire_rifle`). An alias found in no exported table is now
  reported (`unresolved`) and left silent instead of stopping the port;
  `core_common.ff` joined the machine's sound zones. The DG-2 dry fire stays
  unresolved, and that is faithful: `dryfire_rifle` is a legacy name that no
  BO3 alias table defines (zm_levelcommon, zm_common, core_common,
  core_patch, core_all, zm_common_all, mp_common all searched by name; BO3
  weapons use `wpn_<weapon>_dryfire_plr`), so BO3 plays nothing for it either.
* Behaviours: BO3 splits a namespace across scripts (server `.gsc`, client
  `.csc`); one line per script let a later line replace an earlier one's
  data in the assembled module (the `lightning_chain` electrocute sound).
  Lines are now merged per namespace.

Not converted yet: heat-distortion materials, a nested effect-array element
(type 13) in the ground shock, and the BO3 client-side view-model effects
(`tesla_viewmodel_rail/tube`, played by the `.csc` on view-model tags).

View-model effects, what BO3 does and what IW7 offers (2026-11-07):

* BO3 `_zm_weap_tesla.csc` plays the rail (`fx_tesla_rail_view_zmb`, a
  one-shot of about 0.8 s) on `tag_flash` every 8 to 12 s (random), while
  the weapon's own notetracks `tesla_play_fx_on/off` allow it, not in ADS
  and with ammo in the clip. The tube effect on `tag_brass` is four endless
  omni lights whose variant follows the clip count, plus a shader tint.
* An IW7 weapon can trigger view effects only from animation notetracks
  (`notetrackFXMapKeys/Values/TagValues`, as stock `iw7_spaceland_wmd`).
  The converted DG-2 anims keep BO3's notetracks, but the idle is a 2-frame
  pose: a notetrack there fires many times a second, not every 8 to 12 s.
* So a faithful rail needs client-side timing that IW7 assets lack. Two
  routes: a generic native client hook (an ambient view-effect table in the
  mod: effect, tag, random period, gate notetracks), or the asset-only
  subset (the rail when the gun switches on: first raise, pullout, end of
  reload). The tube's look is carried by the emissive tube materials; its
  lights and clip-count tint are not.

## 2026-11-07: projectile launch components

The author copied every `proj*`/`iProjectile*` field of the IW7 projectile
template (`iw7_zapper_grey`, an AI lob: `iProjectileSpeedUp` 500) and
overwrote only the speed, explosion and lifetime from BO3. BO3 keeps the
launch components after the speed, in BO2's order: +0xFF0 up, +0xFF4
forward (zm_levelcommon: Cymbal Monkey and Octobomb up 100, Mustang & Sally
up 50, frag forward 120; Ray Gun, DG-2, Thundergun 0). The spec now reads
both and the author writes them. In game the DG-2 projectile had hit no
zombie in its path; the rerun with the fix is the check.

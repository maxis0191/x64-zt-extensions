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

# Station Zero zombie kit - NOTES (updated 2026-11-09 ~21:40, agent stopped on request)

## Where things are
- Code: on the main line of x64-zt-extensions since 2026-11-10, in `tools-source/iwz-zombie-kit` (written on the
  branch `codex/iwz-zombie-kit`, based on codex/iw7-skinned-writer 3283f2a). Overview: `README.md` beside this file.
  - `tools-source/iwz-zombie-kit/fit_zombie.py` (Blender): AI mesh -> 6 normal parts + 5 damaged gibs, loads
    heroes\tools\fit\fit_hero.py functions WITHOUT running its main (hero file untouched).
  - `run_zombie.py` (stdlib): fit -> blender_export -> build_model (base = stock part xmb) -> hero_material pack ->
    hero_material_zone (mo/zmb_iwz_<id>_body|head) -> clone_scriptable.
  - `clone_scriptable.py`: string swap on ZoneTool assetmanager dumps (+ hair options -> zmb_female_head_hair_nodraw).
  - `configs/zombie_M1.json`; `inspect_stock_parts.py`.
  - writer change: `iw7-skinned-writer/hero_material_zone.py --tex SEM=png` (extra texture rebinding).
- Data: heroes\zombies\fit\M1 (full), fit\M1_quick (quick test). Stock parts glb: heroes\stock_zombies\iw\models (26).

## Status M1 (all offline, PROVEN_LOCAL; nothing built into a zone, no game run)
- fit\M1\run.out: RUN_DONE all steps rc 0. Parts tris: torso 16589 + caps, arm_l 2031, arm_r 1960, leg_l 2024,
  leg_r 1830, head 1566; gibs arm ~1.95k, leg ~2.0k, head 1.6k (+caps). kitdump\xmodel,xsurface = 11 models
  zmb_iwz_m1_{normal_torso,normal_arm_l/r,normal_leg_l/r,head,damaged_arm_l/r,damaged_leg_l/r,head_damaged}.
  Build reports: skeleton_check max err 0.00015 in, 0 unknown bones, 0 unweighted.
- Materials: fit\M1\matroot (mo/zmb_iwz_m1_body from mo/zmb_male_body, sem16 packed_a -> white; mo/zmb_iwz_m1_head
  from mo/zmb_male_head_01, sem2 emissive -> black). Caps use stock mo/zmb_dismembered_caps.
- Scriptable: fit\M1\scriptable\zombie_iwz_m1 (13 names swapped, 30 hair options -> nodraw).
- Renders: fit\M1\renders\align_overlay_*.png, sheet_parts.png, sheet_exploded_gibs.png.

## Facts learned
- Damaged parts = GIBS spawned by ChunkDynent events (left_arm_chunk ... at J_Shoulder_LE), rigid on one bone,
  flags 0x82 (rigid). Our writer writes them skinned 0x86 on 1 bone: NOT_PROVEN in a dynent -> if invisible,
  write rigid surfaces (rigidVertLists + collTree) .
- Stock zombie surfaces flags 0x86, no SH-probe stream -> no --transfer-from needed (unlike mopw heroes).
- Part glbs are in root-bone space (arms/head: j_spine4, legs: j_mainroot, gibs: j_shoulder/j_hip/j_spine4).
- Stock leg gibs are modelled bent at the knee (ours are straight; stock map p50 118 mm = the bend, not an error).
- Gib cut = limb axis plane at the median depth of the stock cap verts: arm 144-148 mm, leg 276-288, head 265.
- IMPORTANT (found last): the zombie character is ALSO an xmodel `zombie_male_outfit_1` (bones-only model:
  lod surf zmb_base_normal_torso_bones..., material mo/lambert1, procedural bones, ragdoll_zombie_male) that names
  the scriptable. cp_iwz.csv has `xmodel,zombie_male_outfit_1` rows (line ~2064) and 276 scriptable rows.
  => also clone dump\cp_zmb\xmodel\zombie_male_outfit_1.xmb -> zombie_iwz_m1.xmb (string swap of the scriptable
  name with clone_scriptable.py should work: same dump format) and add `xmodel,zombie_iwz_m1` + `scriptable,zombie_iwz_m1`.
- cp_iwz.gsc (level zonetool copy) line 20 calls cp_zmb::setup_generic_zombie_model_list(); add a call after it
  setting level.generic_zombie_model_list to the new roster (check 3954.gsc:165-178 for the expected list shape).

## Known quality issues (M1)
- Torso caps: 8 seam loops (expected 5: neck, 2 shoulders, 2 hips) -> small leftover label islands; a few coat
  shreds labelled leg. Weight transfer accepted 48 % (coat far from stock surface, inpainted + coat weights).
- 1 LOD only (writer). Backpack/fanny-pack options of the stock scriptable kept.

## Next (in order)
1. Create own work dir: new-work.ps1 -Work heroes\zombies\ztwork (sdk-hero-train\tools-source\iwzmap\new-work.ps1),
   then Stage-OutfitZone -SourceWork level\ztwork (g27dw, csv zone_source\cp_iwz.csv 7:10 PM) -Models <11> -KitDump
   fit\M1\kitdump -MaterialRoots fit\M1\matroot; needs a -NoOutfitTable switch (else it swaps the hero character
   setup) + scriptable/xmodel rows + roster gsc. Build under the zt.ps1 lease.
2. Usermap dir = built cp_iwz.ff + cp_iwz.arena/.sabl/.sabs from level\um_g27dw; fixture spawning zombies
   (roster forced) + capture; FFSHA256 check.
3. Dismember fixture (3954.gsc:949-975 bitmask), then the other 7 configs (F* = gender female; F4 glb present).
4. Reviewers, fixes, report.

## Since 2026-11-10: local inputs come from the environment
`run_zombie.py` reads `IWZ_HEROES`, `IWZ_BLENDER`, `IWZ_DUMP` and `IWZ_TEXCONV` (optional `IWZ_FIT_DIR`, `IWZ_WRITER`)
and stops with the missing names; `fit_zombie.py` needs `IWZ_FIT_DIR`. No machine path remains in the code. The
pipeline was not run again after this change.

# IW7 skinned model writer (heroes/writer) - NOTES

Code: x64-zt-extensions branch `codex/iw7-skinned-writer`, worktree
`C:\Users\ezvalo\Documents\IW7-Products\worktrees\ext-iw7-skinned-writer\tools-source\iw7-skinned-writer`.
Python: `C:\Users\ezvalo\AppData\Local\Programs\Python\Python312\python.exe -I` (pure stdlib, no numpy).

## M1 reader (PROVEN_LOCAL, 2026-11-09)
- `ztdump.py` ZoneTool assetmanager record stream (type byte, existing byte, u32 count/size, OFFSET re-use records).
- `xsurface.py` XModelSurfs/XSurface (0x38/0x100 structs, verts 32 B, faces, rigid lists + collision trees,
  blend stream, lmap, tension, subdiv kept verbatim, SH/"second uv" stream for flags 0x100/0x400).
- `xmodel.py` XModel 0x2E0 header (named fields), bones, parent offsets, tag quats, positions, baseMat, boneInfo,
  invHighMipRadius, materials (OFFSET re-use resolved), 6 LOD infos, physics/procedural refs.
- `m1_proof.py` -> `m1\m1_report.json`, `m1\m1_proof.log`: 16 dumps (jock body xmb + 6 body LOD xsb, head xmb + 6 xsb,
  arms xmb + xsb) re-written byte-exact; lod0 decode == GrayWolf glb (pos*2.54, normals, UVs, faces reversed winding,
  bones + weights exact, partBits formula exact).

### Format facts
- Vertex 32 B: xyz f32 (inches), u32 selfVisibility (or binormalSign/height for flag 8), u32 color RGBA8,
  u32 uv = 2 x half (u low, v high, same v convention as glTF), normal/tangent = 3 x 10-bit unorm
  (q/1023*2-1), normal bits30-31 = 3, tangent bits30-31 = 3 or 0 (bitangent sign).
- Faces u16 x3, winding reversed vs glTF (glb (a,b,c) == xsb (a,c,b)).
- Skinned surface (flags 0x4): every vertex is in blendVerts, ordered by influence count (1-bone verts first).
  Group g (g+1 bones) per vertex: bone0, (bone_i, w_i) x g, 0 ; bones are plain xmodel bone indices,
  w_i u16 /65536, w0 = 1 - sum. blendVertSize = bytes. Stock heroes use groups 0..3 only (max 4 influences).
- Rigid surface (flags without 0x4): rigidVertLists[{boneIndex, vertCount, triOffset, triCount, collTree}].
- partBits int[8]: bone b -> word b>>5, bit 0x80000000>>(b&31); surface = bones it references; LOD/model = union.
- unk (+0xC0, vertexLightingIndex) = running vertex offset over all surfaces dumped from the zone.
- XModel bounds = midPoint[3] + halfSize[3]; parentList = index - parent; tagAngles = quat*32768 shorts.
- Body xmodel jock: 105 bones, 6 LODs, 48 material slots (9 surfs per lod), procedural bones
  `procedurual_male_undershoulder`, characterCollBoundsType 1.

## M2 writer (PROVEN_LOCAL offline, 2026-11-09)
- `blender_export.py` (Blender 4.5 headless) -> JSON; `build_model.py` JSON + stock .xmb skeleton -> .xmb/.xsb.
- Proof `m2\m2_compare.log/json`: unmodified stock jock glb -> Blender -> writer == stock lod0 xsb: same vertex order,
  faces equal, blend group counts equal, pos err <= 0.0006 in, UV exact, normals within 1-2 quant steps,
  tangent sign 99.3-100 %, weights within 0.005 (ties in bone order only), partBits equal, skeleton heads 0.0006 in.
- Limits enforced: vertCount/triCount <= 65535 per surface (auto split), max 4 influences (clamped + renormalised,
  first weight implicit, u16/65536), vertices sorted by influence count, bone names must exist in the base skeleton
  (exit 2 otherwise), faces winding (a,c,b). Writes flags 0x86 (VERTCOL_NONE|SKINNED|SELF_VIS), selfVis = ZoneTool
  default pack(0,0,1,0), no SH/second-uv stream (flag 0x100 dropped), 1 LOD (dist 1e6), bounds/radius recomputed.

## M3 (PARTIAL)
- Modified model: `m3\kitdump` body_zmb_hero_jock_sztest (jacket +1.0 in along normals; `m3\build_sztest_report.json`).
  xmb sha256 32774152CA64D3B2682FB019F77A383413D37C88BF29F71160D90E94CBDC574B ; xsb sha256 86DBADAFF7A4D3D7B2316564E199F7A7478E4CCDF1A5D2AEF8DF2A3C3BF6EBF0
- ZoneTool compile PROVEN_LOCAL: private work dir `ztwork` (new-work.ps1, hardlinked game zones),
  `zone_source\sztest_hero.csv` = require,cp_zmb + xmodel row -> `ztwork\zone\sztest_hero.ff` (sha256 80BF0D697CBE4EB51DCB54BCE2DA6404D9AED72DC3C992B8B678B4C28E253D99), then
  `-dumpzone sztest_hero` -> dumped xmb/xsb equal to writer output (`m3\zt_roundtrip_compare.log`).
  Caveats seen: materials became `default` in this standalone zone (cp_zmb only references them; techsets_cp_zmb
  require -> FATAL missing pixel shader); procedural bones ref `procedurual_male_undershoulder` dropped to null.
- In-engine render/animation: NOT_PROVEN (not run). Next steps:
  1. Build Station Zero with the model added to zonetool/cp_iwz (stock jock materials are already in the cp_iwz csv via
     `xmodel,body_zmb_hero_jock`):
     `build-sz2.ps1 -Src <current src> -UmOut <writer\m3\um> -Work <writer\ztwork2 (new-work.ps1)> -KitModels body_zmb_hero_jock_sztest -KitDumps 'cp_zmb=<writer>\m3\kitdump'`
     (if kit_import refuses the zone, copy the .xmb/.xsb into zonetool\cp_iwz and add `xmodel,body_zmb_hero_jock_sztest`
     before the world rows of zone_source\cp_iwz.csv, then -buildzone). Verify the procedural bones asset is kept.
  2. cp_iwz-local character setup: copy cp_zmb_player_character_setup::init_player_characters and change the jock row
     (index 4) body to body_zmb_hero_jock_sztest; call it from cp_iwz2.gsc instead of the stock init.
  3. Fixture: spawn script_model body_zmb_hero_jock_sztest + head_zmb_hero_jock at a view, scriptmodelplayanim an idle
     (e.g. the hero idle used by the stock lobby/intro), capture_frame at 2-3 times; also a stock body beside it.

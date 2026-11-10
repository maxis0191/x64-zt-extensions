# IW7 skinned model writer (heroes/writer) - NOTES

Code: on the main line of x64-zt-extensions since 2026-11-10, in `tools-source/iw7-skinned-writer` (written on the
branch `codex/iw7-skinned-writer`). Overview and entry commands: `README.md` beside this file.
Python: `python -I` with Python 3.12 (pure stdlib, no numpy).

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

## M3 in-engine (2026-11-09 evening) - PROVEN
- Zone: private copy of the level agent's assembled g27dc zone source (level\ztwork read-only; copy in
  writer\ztwork\zonetool\cp_iwz + zone_source\cp_iwz.csv + their zonetool.exe), rows added:
  rawfile cp_iwz_outfits.gsc, xmodel body_zmb_hero_jock_sztest / _szred; cp_iwz.gsc calls
  cp_iwz_outfits::init_player_characters (stock table + data rows). Build: m3\build_cp_iwz.ps1 (zt.ps1 lease).
  Final FF m3\um\cp_iwz.ff sha256 1800B9758A970B3D1B0ECC16E737D8DE7F898353895FEB464F1C453BC3F7E8D9 (log m3\buildzone_cp_iwz_b2.out.log).
- Runs (Test-IWZMapLocal, private, FFSHA256 checked): runs\o3_300 (hall, -700,3560,0 yaw -90) and runs\o4_400
  (platform A, -2300,2300,-320 yaw 0): InGame, Restored, 16 frames each. Lines: [IWZ outfit] hero=4 body=..._sztest,
  TABLE jock body=body_zmb_hero_jock_sztest outfits=1.
- Root cause found on the way (run o2_200, FF 8378C56B...): writer bodies rendered BLACK (body and attached head) and
  szred did not draw at all. Fixes: (1) 'mopw' hero materials need the per-vertex SH probe simplex stream (flag 0x100,
  8 B/vertex: 4 probe ids u8 + 4 weights u8 summing 255 over 6 character probe points) -> build_model --transfer-from
  copies it + self-visibility from the nearest stock vertex and restores stock flags 0x386; (2) every model a script
  setmodel()s must be precached at level load -> outfit_extra_models() table.
- Torso RGB (m3\torso_rgb.json): o2 sztest [19,17,15] (black) -> o3 [25,38,54] vs stock [29,39,53]; szred [70,28,24].
- Evidence crops: m3\evidence\*.png/jpg.
- Tracked copy of the torso measurement: `evidence-m3-torso_rgb.json` beside this file (evidence, kept as recorded).
- `gsc/iwzmap_head_probe.gsc` and `gsc/iwzmap_head_probe2.gsc`: fixtures of a local private session that asked how
  head models draw on script models (attach tags). Nothing else in the repository refers to them; kept as the record
  of that question.
- Procedural bones: cp_iwz csv carries 'proceduralbones,,procedurual_male_undershoulder' (reference row) and the
  writer xmb keeps the ref (read back): resolved like the stock body. Not separately measured in a frame.
- LOD: writer models have 1 LOD (dist 1e6): drawn at 500/1000/2000 u (o4 far frames), never reduced -> perf risk.

## New material route - PROVEN (frame)
- hero_material.py (Blender headless): decode stock packed_cs/packed_nog PNG <-> authoring maps; pack albedo(sRGB)/
  normal/gloss|roughness/ao/reflectance|metalness -> *_c_packed_cs.png / *_n_packed_nog.png. Re-pack of the decoded
  stock jacket = stock within 1 LSB (mat\repack_check\pack_report.json).
- hero_material_zone.py: texconv BC7_UNORM DDS (images\<stem>.dds, embedded), material JSON clone with semantics
  14/15 rebound, techset state/constantbuffer copies; technique stays the stock runtime one.
- szred: hue 150 jacket, 1024^2, ZoneTool 'Parsing custom image' x2, drawn red/green in o3/o4.

## Commands (new outfit)
blender -b --factory-startup outfit.blend -P blender_export.py -- --out o.json
python -I build_model.py o.json --base-xmodel <cp_zmb>\xmodel\body_zmb_hero_jock.xmb --name <name> --out <kitdump>
   --transfer-from <cp_zmb>\xsurface\body_zmb_hero_jock_lod030v7e1p3_0060.xsb [--material-map map.json]
blender -b --factory-startup -P hero_material.py -- pack --albedo a.png --normal n.png --roughness r.png --ao ao.png --metalness 0 --stem <stem> --out <dir>
python -I hero_material_zone.py --techsets-dump <dump>\techsets_cp_zmb --template mopw/zmb_hero_jock_jacket --name mopw/<new> --cs ... --nog ... --texconv <texconv.exe> --out <matroot>
ops\Stage-OutfitZone.ps1 -SourceWork <good level ztwork> -Work <own ztwork> -Models <names> -KitDump <kitdump> -MaterialRoots <matroot> -Build -ZoneTool <iw7-creator-sdk>\tools-source\iwzmap\zt.ps1
ops\Run-OutfitProof.ps1 -Runner <server>\ops\iwzmap\Test-IWZMapLocal.ps1 -SourcePackage <source package> -GameRoot <bench root> -InjectDll <error journal dll> -UsermapDir <um> -OutputRoot <new run dir> -View "x,y,z,yaw"
Add the outfit row in gsc\cp_iwz_outfits.gsc outfit_rows(): [ index, body, view arms, head, hair ].

## Hero outfits ship (2026-11-09 night) - IN PROGRESS (stopped on request 21:18)
- ship_heroes.py + ship_heroes.example.json: pack (normal green flipped: stock nog = DirectX, fit = OpenGL, hero_material.py
  normcheck), materials (body mopw clone of jock jacket/jeans, hair + VM sleeves mo clone of nerd helmet), body with
  --transfer-from hero stock LOD0, LOD chain 300/1000/10000 (blender_export --decimate 0.35/0.12, build_model --lods),
  hair (valley girl hair skeleton), VM arms, Poindexter cleaned head (helmet/accessories/lenses dropped, 6 LODs).
- v1: heroes_v1 (FF A432C131..., runs h1-h4, probes p1/p2b). Reviewers r1 (review_r1): all DO NOT SHIP 2-4/10.
- Found: script models do NOT draw heads attached with attach(head,"") (any tag) nor attachments of a linked head;
  fixture now spawns head as own script_model linked at body j_spine4 and hair linked at head j_neck (h4: faces ok).
  Real-player third person NOT_PROVEN (second client did not join within 90 s in h4).
- Found: fit textures leave ~55% atlas black; AO missing on ~75% of AJ islands; gloss too high -> packer --pad 1
  (edge padding), unbaked AO -> white, --ao-floor 0.4, --gloss-scale 0.6.
- v2: heroes_v2 (new fit READY exports 20:38-20:59, new packing, new LODs) built: um\cp_iwz.ff sha256 AD47695DEFD5D6ED3D6282129028F1A255F8005C283F24B32342776E35FC35B1 ;
  NOT yet run. Next: Run heroes_v2\run_h5 (see heroes_v1\run_h4.ps1 pattern, fixture heroes_v2\iwzmap_hero_fixture.gsc,
  -Extra '+set paris_iwz_hero_nohud 1 +set paris_iwz_hero_ref body_zmb_hero_jock,head_zmb_hero_jock'), build
  review_r2 like review_r1, ask parent for reviewers.
- Bug fixed: Run-OutfitProof -Extra was silently dropped (PowerShell $Extra/$extra same variable).

## Since 2026-11-10: no machine paths, no retry loop
- `ops/Run-OutfitProof.ps1` takes the runner, the source package, the game root and the diagnostic DLL as mandatory
  parameters, refuses a game root that is not a bench root (`paris-bench-root.json` absent) and runs once: the
  former version tested in the owner's game folder and retried for up to three hours. Not run since this change.
- `ops/Stage-OutfitZone.ps1 -Build` takes `-ZoneTool` and runs the build once.
- `ship_heroes.py` reads `${NAME}` environment variables in the root values of its config and resolves relative
  LOD paths under `lods_root`; the tracked config is `ship_heroes.example.json`.

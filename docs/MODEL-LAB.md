# Original model lab and named Doom content goals

This lab proves an original rigid model from explicit geometry to IW7 serialization,
then FF inventory and protected-client pixels. The original cube is a pipeline
witness. Doom Slayer, the Super Shotgun and an Eternal enemy remain separate open
content goals; no generic model silently replaces them. Source/format compatibility,
file integrity, runtime behavior and owner acceptance are separate gates.

> **Current visual status — 2026-10-13.** Original rigid geometry is visibly
> documented. Case `20261007-010207-340-356f8823` corrected LOD0 distance from
> zero to 1,000,000: the 1040-byte FF `0EC7544D…3685063` rendered the cube at
> both swapped poses and restored fully. See the [STATE checkpoint](STATE.md#original-geometry-renders-after-lod-correction---2026-10-07)
> and [runtime validation](VALIDATION.md#visible-original-cube-and-isolated-native-observer-build---2026-10-07).
> The [12 October UseRejoin Plan B](SELF-CONTAINED-BEACON-RUNTIME.md#userejoin-plan-b-targeted-runtime-pass-2026-10-12)
> reused the 1048-byte Beacon FF `3FA49BCD…F8B71DA8`; review saw the cuboid and
> HUD in five views, while one nearly black frame was unusable. Its recipient
> material is `mopw/character_park_clown_zombie_shoes`, not a custom texture.
> These observations do not prove custom textures, UV/normal/lighting conformity,
> overall pixels or owner acceptance, or the new T7 asset port. The earlier
> invisible-cube result below is retained as history.

## Named content and author evidence

Public author pages were inspected once for this content search on2026-10-06/07.
No purchase, registration, author message or restricted asset download occurred.
These links establish available descriptions, not ownership or permission to
redistribute Bethesda/id Software content in another game.

| Goal/source | Author evidence and practical boundary |
| --- | --- |
| [Doom Eternal Slayer GMod](https://steamcommunity.com/sharedfiles/filedetails/?id=2039547466) | Author **o u t l a w** describes extracted third-person/viewmodel content, original proportions and blade bodygroup, without shoulder gun; credits id Software/Bethesda. A GMod publication is no cross-game export/redistribution license. File compatibility/download remains unverified. |
| [Rigged low-poly Slayer](https://randomthings.artstation.com/store/BWYXK/doom-slayer-lowpoly-rigged) | **Random Things** lists FBX/DAE/OBJ/BLEND, Blender-only rig controls and1024 textures; paid $5 Standard Use with commercial project/sales/view limits. No purchase; animation clips and Doom IP permissions remain unresolved. |
| [Super Shotgun](https://sketchfab.com/3d-models/super-shotgun-doom-eternal-964c0b4839c64e37bdbeefee8a2e242b) | **Meredith Ms** indexed page describes325.9k triangles/153.1k vertices with CC Attribution. Direct page403; downloadable formats, rig/animations and underlying IP authority remain unverified. |
| [Low-poly Doom Shotgun](https://3jup1t3r.itch.io/ps1-style-doom-shotgun) | **3JUP1T3R** describes434 vertices, FBX/BLEND and a meathook, with author project-use permission/credit. The author explicitly identifies a Bethesda media texture and unknown permission for it. No animation/export validation or download. |
| [Eternal Marauder](https://sketchfab.com/3d-models/doom-eternal-marauder-f16a114a09d4475a95c72352feb2151e) | **cadki3334** lists59k triangles/30.5k vertices and CC BY, without a provenance description. Rig, animations, file formats and authority to license extracted IP remain unverified. |

[Bethesda's official PC mods update](https://slayersclub.bethesda.net/en-US/news/doom-eternal-pc-mods-update)
(Joshua Boyle,2025-08-07) describes idStudio/mod asset packs for Doom Eternal.
[Official mod installation help](https://help.bethesda.net/app/answers/detail/a_id/66328/)
does not establish IW7 asset redistribution permission. Extraction for local
experimentation and distributing a pack are distinct decisions.

[VEGA by DTZxPorter/id-daemon](https://dtzxporter.com/tools/vega) describes v2.64
(2026-09-16), models in Cast/OBJ/XNALara/SMD/CoDXModel/Maya/FBX, Cast animations,
and DDS/PNG/TIFF/TGA textures, requiring intact base/patch resources. A CoDXModel
export does not prove our IW7 XMB/XSB compatibility. Related author sources are
[SAMUEL](https://github.com/brongo/SAMUEL),
[EternalResourceExtractor](https://github.com/brunoanc/EternalResourceExtractor),
[extraction format guidance](https://wiki.eternalmods.com/books/eternal-how-to-create-mods/page/extracting-resources),
[legacy SEModel Blender importer](https://github.com/dtzxporter/io_model_semodel)
and [legacy SEAnim importer](https://github.com/SE2Dev/io_anim_seanim).
Current Cast rig/weight/animation import still requires a validated bridge.
Do not download retail PAKs, perform a full20GB extraction or claim that these
sources grant permission for an IW7 redistribution.

Bounded local Steam/Epic inventories found no Doom installation: HKCU SteamPath
pointed to an absent directory, expected Steam library paths and Epic manifests
were absent, and filtered Windows uninstall inventories had no Doom entry. This
is no proof of account ownership/nonownership or absence elsewhere on the PC.
Filename inventories of the retained Doom labs found no named Slayer/shotgun/
Eternal FBX/OBJ/BLEND/SEModel model payload. A compiler .obj is not a3D asset.
The existing DoomFight uses retail IW7 enemies; abandoned negative-texture work
must not be revived as an accepted appearance. No full-PC scan was performed.

## Exact IW7 pipeline

The existing local ZoneTool source is pinned to
`fab935826c898806855376662a8a03317b3ad8f1` at `tools/x64-zt-enemy`.
The shared checkout remains unchanged. Its native importer expects:

| Input | Required information |
| --- | --- |
| `xmodel/<name>.xmb` | XModel736-byte structure, names/tags, bone hierarchy/rest matrices/bounds, material references, up to6 LOD surface references and optional physics/procedural data. |
| `xsurface/<name>.xsb` | XModelSurfs56-byte structure, XSurface256-byte structures, packed vertices/UV/normals/tangents, triangle indices, rigid lists or blend weights and optional subdivision/SH streams. |
| `xanim/<name>.xab` | Compressed tracks, bone IDs, notetracks and delta parts; raw exported clips are not an automatic compatible animation. |
| `weapons/<name>.json` | Weapon definition plus actual view/world models, animation/effect/sound/attachment references and dependency closure. |

No generic direct FBX/OBJ/SEModel importer into this IW7 binary format was found
in the existing tools. Other game-family converters are not a general Doom
importer. The next Cast bridge must explicitly map skeleton/rest pose, weights,
materials and animations; playable Slayer and an enemy additionally need correct
movement/attack/death behavior. A shotgun needs viewmodel hands/rig, clips and
weapon definition; a visible static mesh is not a functioning weapon.

## Original cube and standalone writer

`geometry.py` defines original24 vertices/12 triangles, one rigid `tag_origin`
identity root, one surface and one LOD. Each face has its own outward winding,
flat normal and0/1 UV corners. Bounds are[-8,8] in each axis. No retail mesh is
copied or used as a template. Optional physics, subdivision, animation, reactive
motion and scriptable fields are absent. The source validator rejects nonfinite
vectors, bad indices, inverted faces, wrong weights and false readiness.

`prepare_writer.py` checks the clean pin and hashes ten source interfaces/order
references, then emits source geometry, a generated header, `writer.cpp` and
source provenance in a fresh directory. Linked ancestry/existing output are
refused. With a recipient reference it additionally rechecks the exact retained
snapshot files before binding its name; changed snapshots are refused.

`Build-Writer.ps1` rechecks the pin and prepared input hashes, compiles one
translation unit with installed MSVC x64, and reserves Build RAM2GiB/commit3GiB
for compilation plus a standalone1MiB reader. There is no PCH/full ZoneTool
rebuild, stock/model extraction or game process. The adapter opens only the two
fixed original assets, uses CREATE_NEW, rejects linked ancestry, short I/O,
oversized files and strings, then invokes the actual pinned dumper and reader.
Every original position, packed vertex field, index, rigid list, root/rest pose,
bounds and LOD reference is compared. ASLR pointers embedded in dump records
mean byte reproducibility is not assumed; compare semantic geometry and record
actual output hashes per run. Generated files remain ignored runtime artifacts.

## Actual roundtrip measurements

Root-run `runtime/model-writer-source-20261007` passed compilation without
warnings and pinned-reader comparisons; the lease was released23:32:21Z.
`artifact.measured.json` retains this initial null-material proof:

| Artifact | Actual measurement |
| --- | --- |
| Writer | SHA-256 `26933C24E9520018AF0A714C4865FC01161C1D03F3E6A53FA5F86963021EDDE5` |
| XMB |939B, `B8C731255A81502B887BC58705AAAA37C540300C575AE3190859A751AAC391CE` |
| XSB |1231B, `FB05AF067B0186BE175ED4015DB26A3723BC3438154DB79C58A8B88EFEF324A9` |

The material reference selected for the cube is
`mopw/character_park_clown_zombie_shoes`. A retained selective Spaceland snapshot
has its exact closure row, matching cp_zmb load log and material JSON. These three
files were rechecked by hash/size. `recipient.evidence.json` records dated snapshot
proof, not a live engine success or a redistribution license. Only its name is
bound: no retail material JSON, shader, image or model data is copied into the pack.
This is a recipient material for a cube witness, not a Doom appearance claim.

Pinned experimental H1-to-IW7 `xsurface.cpp` copies normal/tangent/UV packed values
unchanged (lines139–140); the reverse converter copies compatible vertex fields.
The H1-to-IW7 path sets self-visibility flag0x80 and default[0,0,1,0], now followed
by our writer. This supports static format compatibility. Actual IW7 shader
lighting and tangent handedness remain pending. UV0/1 use exact IEEE-half values.
The normal encoder follows the pinned H1 10/10/10/2 formula; its raw roundtrip
proves serialization integrity, not shader correctness.

Root-run `runtime/model-writer-material-verified-20261007` recompiled and passed
material-linked roundtrip. `artifact.material.measured.json` retains:

| Artifact | Actual measurement |
| --- | --- |
| Writer | `4632CD9F8C62131C6831AC9B8EE508A575762757286A62AEEB834E3BCA5FC8CE` |
| XMB |978B, `41EA1DE95B0A0D9800945AAF54FBB255B1639A57F85514F806C9ABA2F974BE57` |
| XSB |1231B, `E317D0DB02E2D938AC382D310C4820828AAE5ADAF82D5A24BC567670B9677FFC` |

Both runs retain ready=false. The old null-material output remains unchanged.

## Minimal FF preparation and next gate

`prepare_ff.py` requires measured material-linked writer provenance and exactly
two XMB/XSB artifacts with matching sizes/hashes before creating fresh staging.
It prepared `runtime/model-ff-source-20261007`: original XMB/XSB, CSVs, a five-asset
expected inventory plan and an original single-entry model NetConstStrings table
(XMODEL type0, COMMON source2 from the pin). Four asset-free tests pass, including
changed-payload, null-material, wrong-pin and existing-output refusals.

The CSV ignore list turns the typed material dependency into a recipient name
reference. Expected compiled rows are custom XModel, custom XModelSurfs,
referenced material, one NetConstStrings asset and generated zone RawFile.
No shader/image/material payload should enter the inventory.

```powershell
python ops/model-lab/prepare_writer.py --source tools/x64-zt-enemy `
  --recipient-evidence ops/model-lab/recipient.evidence.json `
  --stock-root <existing-stock-tool-root> --output <fresh-runtime-source-root>
pwsh -NoProfile -File ops/model-lab/Build-Writer.ps1 `
  -PreparedRoot <fresh-runtime-source-root> -DryRun
python ops/model-lab/prepare_ff.py --writer-run <measured-writer-run> `
  --output <fresh-runtime-ff-source>
```

Already prepared directories must not be reused for preparation. Root coordinates
all actual heavy slots. The next FF **build** can use the known bootstrap tool,
sentinel and PAK1 inputs with `-buildzone paris_model_probe`. Preloading cp_zmb
is unnecessary merely to serialize a named external material reference. Retain
the FF immediately after compilation; verify exact inventory and re-dumped
original model/surface geometry. A bootstrap-only load cannot prove this external
material resolves. That separate gate belongs to cp_zmb loaded in the protected
client/dedicated using existing complete stock, without speculative PAK copies.
The real frame must show original cube geometry/material/lighting, and network
model NetConstStrings binding must be observed for a server spawn witness.
FF build, external material runtime binding, lighting and pixels remain pending.
Then implement Cast import with genuine rig/weights/animation/weapon behavior;
Doom Slayer, Super Shotgun and the Eternal enemy goals remain open.


## Narrow FF wrapper, no launch yet

`Build-ModelFF.ps1` reuses the existing BaseTransaction, resource admission,
NTFS identity and owned tool/diagnostic supervisors without editing HUD/native
code. Its actual dry run passed against the retained stock/tool provenance and
`runtime/model-ff-ready-source-20261007`. It declares the same allowlisted FF
bootstrap set, mutable sentinel copy, engine DLL copies and only PAK1 hardlink.
It reserves Extract8GiB/commit11GiB including45s stall diagnosis. There is no
cp_zmb preload or PAK53 addition.

The wrapper retains compiled `mod.ff` before inventory or dump validation.
Failed external-reference loads retain compiled proof with offline-unresolved
status; no recipient binding is inferred from bootstrap inventory. Optional
`ReaderRun` uses a measured writer with `--verify-existing` mode to compare
FF-re-dumped model/surface geometry. That reader is itself supervised by the
existing exact-owned process helper with a30s timeout under the same reservation.
New reader source is staged in `runtime/model-writer-reader-source-20261007`;
its measured compiler run passed with executable SHA256
`DD28427E8D26D32A0B78426EC1083C18B529262EE67CAE010B8ACCB3A901C2BA`.

Restoration requires owned-work vacancy, source/target NTFS identity, source
size/mtime/attributes, actual transaction restore and source-final verification.
Unconfirmed child cleanup or any refusal retains the reservation and bytes.
Source attributes/file ID and vacancy refusal regression tests use real NTFS
hardlinks and BaseTransaction fixtures; they verify no release/removal on refusal
and release only after confirmed restoration. Inventory tests reject extra,
changed and unresolved-reference rows. Eight asset-free tests pass. FF build/inventory and retained semantic re-read
have now passed as described below; protected pixels remain pending.


## Measured FF and retained-reader correction — 2026-10-07

`runtime/model-ff-build-20261007` produced a 1036-byte FF with SHA256
`BE3A34FF1AB0F95B1850E0BDE0BA60E519706F796F2BF38134C65A42724893CB`.
Build, bootstrap inventory and dump exited zero. Inventory is exactly the external
material reference, original xmodelsurfs, original xmodel, model netconststrings
and zone rawfile. No retail material payload is embedded. The first wrapper
failed before starting the semantic reader because its Memory-Budget import was
missing. Its Failed state and original false geometry flag remain immutable;
Restored/StockPreserved are true and no retained lease remains.

The minimum import was corrected. A separate supervised retained-reader pass
exited zero: `runtime/model-retained-reader-20261007.log`, with unique evidence
`model-recovery-reader-20261006-235045-332-54ebc81551d342dba2cd56293c1dd5e7.stdout.log.evidence.json`
inside the original run. It re-read the actual FF dump and preserved all 24
vertices, 12 triangles, one root, one surface and one LOD. It did not rebuild the
FF or overwrite the failed first result. `artifact.ff.measured.json` records both
facts. Bootstrap reference inventory cannot establish recipient material binding,
shader correctness, normals under lighting or pixels; Ready remains false.

## Protected scene witness API (prepared, not launched)

`Model-Runtime.Core.ps1` has no effects on import. Caller imports the reviewed
Base-Client and ModelFF core. `Read-IW7ModelBuild(RunRoot, ReaderEvidence)` admits
only the measured 1036-byte FF above, restored stock state, exact five inventory
callbacks and the measured retained reader. It re-hashes both dump files and
compares the reader's actual stdout JSON with its evidence before returning
Bytes/SHA256/FsGame/HttpRoute. Evidence is local provenance, not a signed attestation.

`Get-IW7ModelProfilePaths(GameRoot)` admits only `mods/paris_model_probe` with one
mod.ff no larger than 1600 bytes and no subdirectories; unexpected content is
preserved and refused. Agent-Lab owns the snapshot/hash-preflight clear and
restore for both candidate and existing base client. Server fs_game is exactly
`mods/paris_model_probe`, with real FF and engine-computed mod_hash.

The shared `IW7HudHttp` four-argument constructor explicitly accepts
`IW7HudHttp.ModelRoute` (`/mods/paris_model_probe/mod.ff`). Three-argument calls
retain the HUD route. Arbitrary routes, queries and the HUD route on a model
listener are refused. Bytes are cloned/hash-verified, service is loopback-only,
journal is `model-http.jsonl`, and its worker is disposed/joined before any
transaction restoration or reservation release. GET proves exact transport and
time, not the requesting TCP process ID.

`model_fixture.gsc` runs only on a password-protected isolated dedicated Spaceland
case on ports27100–27999, with the model/test dvars and sv_cheats0. It precaches
the original model, then waits up to90s for intro and gesture completion, unfrozen
controls, grounded player and one second of stable position/view. Independent
250ms protection heartbeats continue throughout readiness and the witness. It
places one script_model96units ahead of eye and12units below it, rotated30degrees
to expose faces. It never replaces the player model, changes player angles or
weapons, grants DC perks, or claims a Doom asset. The object is deleted after60s,
on disconnect, game end or protection failure; use one dedicated case per witness.

`Wait-IW7ModelRuntimeEvidence(Session, Build, Http, OutputRoot)` uses Session.Server
and Session.Identity checks, bounded exact-owned logs, ordered unique complete
SCRIPT_MODEL_REQUESTED/READY_MODEL lines, post-launch exact GET journal and fresh
client cache hash/mtime. It emits `model-runtime.local.json`. A setmodel request
is not a pixel or material-resolution witness: RecipientReferenceResolved,
PixelsVerified and Ready remain false. Root's runner captures the native1280x720
frame for independent visual inspection. Shadows, normals, texture binding,
visibility and original geometry appearance require that real frame. Doom Slayer,
shotgun and Eternal enemy remain separate open targets.

Eight lightweight tests cover real NTFS restoration refusals, geometry/staging,
missing-import regression, exact model HTTP routing/worker disposal, foreign cache
preservation, injected owned-session identity, stale GET/duplicate markers and
false pixel/material acceptance. GSC parse passed; no model client/game was
launched in this preparation step.

## Historical invisible cube: isolated shadow sentinel candidate

The protected run `runtime/agent-lab/20261007-000759-331-f456a89f` loaded
the measured 1036-byte FF, requested a script model and captured fresh frames.
Independent inspection did not establish a visible cube. Transport, entity
creation and successful cleanup remain separate from pixel acceptance.

The old original writer set `shadowCutoffLod=255`. The retained converter at
`fab935826c898806855376662a8a03317b3ad8f1`,
`h1/converter/iw7/assets/xmodel.cpp`, explicitly uses `shadowCutoffLod=6` and
records that `0xFF caused models to fade out`. The candidate changes only this
model field to 6; `collLod=255` is a distinct collision sentinel and stays intact.
Preparation records the converter hash, and the standalone reader must prove
both fields after roundtrip. This source evidence motivates the correction;
no new compile, FF or visible result has yet been measured for it.

If the candidate remains invisible, compare a recipient retail model with the
custom model sequentially at the exact same script-model pose. Log player eye,
view angles, entity origin/angles and the selected model. The current placement
uses horizontal yaw at 96 units and eye height minus 12, ignoring view pitch;
it may overlap the weapon. Repeat a pose above that overlap only after the
same-pose control, keeping camera angles untouched. Material resolution, client
model-index/NCS binding and LOD/culling data still need independent evidence.

# BO3 / T7 to IW7: selected static model

Status, 2026-10-12: source reconnaissance and proposed export contract. No BO3
payload was read, exported, converted, built into an FF or rendered here. The
owner stopped H1 work. Its checkpoint is historical and supplies no BO3 proof.

After the owner confirmed download completion, the bounded metadata inventory
found the client and `boiii.exe`, 168 FFs, 203 XPAKs and 110 FDs immediately under
`zone`. The required dedicated executable and `UnrankedServer` directory were
absent at the inspected locations. See `bo3-inventory-20261012.json`; this is not
an installation integrity or build-compatibility check.

Reuse the existing `bigmangeekf/x64-zt` checkout at
`fab935826c898806855376662a8a03317b3ad8f1`. The accompanying source contract pins
the actual T7 converters, IW7 serializers and layouts. It is not an executable
compatibility receipt. Do not copy the game, ZoneTool source tree or SDK tree.

## Existing route and exact gaps

| Stage | Observed source behavior | Remaining work |
| --- | --- | --- |
| Boot | `main.cpp:19,35-74,538` selects T7 when `BlackOps3_UnrankedDedicatedServer.exe` exists. One multigame ZoneTool build selects its mode by local executable names. | Identify the exact compatible server binary; a `BlackOps3.exe` client or T7x download is not equivalent. Hardcoded T7 hooks require build validation. |
| Load/catalogue | T7 `zonetool.cpp` has `loadzone` and `dumpcsv`. Both load a zone through the engine. | Admit one explicitly selected zone and bounded metadata catalogue after the download completes. Neither command is metadata-only disk inspection. |
| Dispatch | Console `dumpzone iw7 <zone> xmodel,xmodelmesh` selects the existing IW7 conversion but exports those types across the zone. CLI `-dumpzone <zone>` and console `dumpasset` force T7; the T7 dump switch is empty. | Recipient worker owns the selective CLI, boot and XPAK confinement. Proposed interface: `-t7-iw7-model <zone> <exact-model-name> <lod>`. It does not exist at the pinned revision. |
| Conversion | `t7/converter/iw7/assets/xmodel.cpp` and `xmodel_mesh.cpp` return real IW7 structures; dump calls the existing IW7 writers. | Preflight, one-LOD nonmutating view and selected model/mesh closure described below. |
| Strings | `game/shared.cpp:84-90` installs T7 `SL_ConvertToString` at `0x1401632C0`; IW7 `xmodel::dump` resolves each copied T7 bone ID through that shared symbol. | Capture a nonempty engine-resolved name, compare it with the XMB string, then separately prove IW7 parse/prepare re-interning. Never substitute `tag_origin` for a failed lookup. |
| Output | `dump/<fastfile>/xmodel/<donor-name>.xmb` and `xsurface/<selected-mesh-name>.xsb`; material and LOD ASSET records contain names. | Preserve donor names and bytes. SDK binding to its probe names is a separately recorded derivation. |

The serialized stream is ZoneTool `assetmanager`, **not** XMODEL_BIN or SEModel.
It has typed records (ARRAY 8, STRING 6, ASSET 7, RAW 10, OFFSET 9), optional
presence bytes, array counts and native-layout records. It has no global format
magic/version. Identify it by source commit plus serializer/layout hashes.
Pinned IW7 layout assertions: XModel 736 bytes, XSurface 256, XModelSurfs 56.
The reader must support the writer's bounded backreferences or reject an actual
export explicitly; the old original-cube reader is not a general BO3 reader.
The SDK reader review also found that its existing skin reader only handles a
narrow name-alias case and has 64 KiB/128-character bounds. The production
writer's ledger is global and untyped: present records create entries, absent
and OFFSET records do not, and `array_index` uses the consuming type's stride.
The future bounded reader must track record kind, stride, count and extent,
reject unproven aliases, and preserve all logical aliases during any binding.
Do not relax historical fixture oracles or use global binary name replacement.

## First real donor profile

Select a small recognizable prop from an admitted catalogue, recording its
exact name, source zone, source LOD index and selected mesh name. No retail name
has yet been observed; choosing one now would be speculation. The first profile
accepts one surface, one root bone, no cosmetic bones, no skinning, no submodels,
no collision surface/tree or physics payload. Reject unsupported data explicitly.

1. Validate model, mesh, shared header, one material slot, rigid list, bone name,
   classification, base matrix and bone bounds before calling the converters.
   A nonnull pointer is not a readable-range proof. The selective engine adapter
   must validate ranges/lifetime while the database is stable.
2. Require `0 <= selected_lod < numLods <= 8`, one surface and one material in
   that LOD, one covering rigid list bound to root bone 0. Validate finite model
   and bone bounds, nonnegative extents/radii, a finite positive selected
   `averageTriArea`, and finite nonnegative `himipInvSqRadii`.
3. Initially accept only resident mesh data: shared `flags & 1 == 0`, a nonnull
   data buffer, positive bounded `dataSize`, and the selected surface using the
   same shared buffer. Reject the streamed surface flag too. No XPAK lookup is
   permitted by this profile.
4. Use checked arithmetic for the ranges below, then validate each triangle
   index against `vertCount`. Reject nonfinite positions/half-float UVs, empty
   geometry, degenerate triangles and inconsistent rigid coverage. Proposed
   per-model caps: 65,535 vertices, 65,535 triangles, 16 MiB resident buffer,
   32 MiB combined export. These are admission limits, not measured costs.

| Stream | Start within shared buffer | Required bytes |
| --- | --- | --- |
| Positions | `posOffset + baseVertOffset * 12` | `vertCount * 12` |
| Vertex attributes | `vertsOffset + baseVertOffset * 16` | `vertCount * 16` |
| Indices | `indicesOffset + baseIndexOffset * 2` | `triCount * 6` |

The existing converter computes a weights pointer even for an unskinned
surface. The pilot requires that start to be within or one-past the buffer,
without requiring skin payload bytes. This avoids constructing an out-of-range
pointer without inventing a skin stream for a rigid model.

Create a stack/owned copy of the T7 model header and one copied mesh-material
entry. Set only the view's `numLods=1`, `meshes[0]=source.meshes[selected_lod]`,
`averageTriArea[0]=source.averageTriArea[selected_lod]`, and `meshMaterials` to
the copied entry. Clear unused mesh slots and reject collision LOD data for this
initial profile. Keep the donor model and mesh names unchanged. Pass the view
to the real model converter and the selected mesh to the real mesh converter.
Never alter the engine-owned model, counts, pointers, materials or resident
buffer. Keep view storage alive through conversion/dump; do not return a copied
wrapper containing a self-referential pointer. Canonicalize the owned view's
unused zero-count parent/angle/position pointers to null.

`t7_iw7_resident_model.hpp` implements this selection interface in source:
`resident_iw7::select(const XModel*, const char*, unsigned int,
utils::memory::allocator&) -> XModel*`. It uses caller-owned allocator storage
and throws a reason on refusal. Its readable-range checks use `VirtualQuery`;
the caller still owns binary compatibility and database lifetime. This source
has not yet been compiled or executed. The constraints define pilot v1, not
permanent SDK limits on future multisurface, skeletal or animated imports.

Independent review found that ASCII alone did not confine the native writers'
paths. The selector now calls the common `asset_name`/`checked_asset_name` rule
on **both** the selected model and mesh. It rejects traversal, rooted/UNC/drive
paths, ADS, empty segments, Windows device aliases (including with extensions),
trailing dots/spaces, control bytes and forbidden Windows filename characters.
Valid donor names retain their spelling and relative subdirectories. The CLI
must also check actual output ancestry/reparse entries; lexical name validation
does not secure a preexisting output tree. `test_t7_asset_name.cpp` prepares
51 boundary checks against the real portable helper; native execution remains
pending admission and is required before any export.

The converter copies packed normals/tangents and UV words. Greyhound's BO3
source independently identifies the two UV fields as half floats and decodes
normals as biased 10-bit components. That supports inspection, not full IW7
frame compatibility. Compare the first real output's geometry, winding, decoded
normals/tangents, orthogonality and UV handedness before rendering acceptance.
Preserve vertex colors. Do not quietly regenerate tangents or replace materials.

## Explicit exclusions and receipts

The existing model converter estimates LOD distance with a stated heuristic;
the first one-LOD port must disclose that distance. It truncates accumulated
material count to an unsigned byte; the one-surface profile avoids that case.
Its material handles are casts used by a name-only dump, not material conversion.
Collmaps create a physics name stub, not converted physics. Cosmetic bones are
marked untested. The animation converter narrows some counts, changes quaternion
streams, maps notify fields and aliases delta data; its presence does not prove
animation compatibility. Skeletons, animation, materials/textures and physics
remain separate future work.

Keep independent evidence for: source pins; exact donor executable/zone inputs;
original job/process closure; selected source counts/ranges/bone string/material
name; real converter invocation; actual XMB/XSB lengths and SHA-256; independent
readback; explicit SDK binding if used; IW7 FF build/verify/dump/read; rendered
appearance. No stage inherits a successful result from an H1 or original-cube
receipt. The SDK's existing V8 probe requires `paris_model_probe`,
`paris_model_probe_lod0` and `ncs_mdl_paris_model_probe`; the SDK worker owns that
derivation and packaging after real output exists.

## Legitimate executable acquisition

Treyarch's [official dedicated-server guide](https://steamcommunity.com/sharedfiles/filedetails/?id=814090509)
identifies the Steam Tools distribution and required executable. Its 2016
instructions do not establish today's depot sizes, account access or binary
compatibility. Valve's [server distribution documentation](https://partner.steamgames.com/doc/sdk/uploading/distributing_gs)
explains that anonymous SteamCMD availability is app/package configuration;
do not infer it merely from being a dedicated server.

Prepare a separately admitted SteamCMD **metadata-only** bootstrap in durable
local tool storage. The official bootstrap URL is
`https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip`; HTTP HEAD on
2026-10-12 reported 774,825 bytes. This is the compressed bootstrap only, not
the updated client's installed size. Download and hash under a total 512 MiB
bootstrap/cache/log ceiling. The 774,825-byte ZIP was downloaded with a 1 MiB
transfer cap; its sole entry was extracted with an 8 MiB limit. The extracted
1,687,464-byte executable has a valid Valve Authenticode signature and version
02.02.95.35. Hashes are in the retained initial `steamcmd-bootstrap.json` receipt.
At that preparation checkpoint neither executable nor self-update had run.
These are initial bootstrap hashes; the subsequent attempt A is recorded below.

Initial candidate query, before the primary AppID confirmation in attempt A:
`steamcmd.exe +login anonymous +app_info_update 1 +app_info_print 545990 +quit`.
This contains no `app_update`, `download_depot`, personal account login or
server launch. The store `appdetails` endpoint returned `success:false`; an
official EULA URL for that ID served a generic agreement without the game name.
Neither result proves the AppID. Verify the application name, public branch,
depot/manifest IDs and sizes from Steam's returned metadata before any download.
Record failed queries as such.

The existing NativeJob retains a read-only file-sharing guard on its root
executable. Launching the old bootstrap as that guarded root may prevent its
expected self-replacement. Prefer the existing pinned Python-phase-under-job
pattern if retaining SteamCMD: the phase validates and launches the bootstrap
as a child, while the original job owns its complete update/process tree. This
requires a reviewed adapter, deadline, private cache/temp/log paths and separate
before/after executable hashes; the executable host is described below. An
uncertain or still-active original job retains/quarantines its reservation.

`steamcmd_metadata_phase.py` is that fixed-command child adapter. It reuses
`sdk/modding/beacon_tool_phase.py::copy_bounded`, limits each output log to 2 MiB,
observes the whole private tool/cache/temp tree against 512 MiB with 1 MiB
reserved for final metadata, and applies a 180-second phase deadline. The disk
limit is sampled, not an OS quota; the outer retained job must stop all children
on failure and confirm closure before lease release. Twelve light Python checks
passed for refusals, disk accounting, the existing bounded-output helper,
thread failures including `SystemExit`, and zero-exit/deferred output completing
at or beyond the deadline. Worker failures set the shared failure event before
returning; the phase rechecks its deadline after child exit and after output
drain. These checks never started SteamCMD. Prepare the outer launch plan with current pins of
Python, this adapter, its imported helper, scheduler and original NativeJob DLL;
do not invoke the adapter directly as an unsupervised process.

`Invoke-SteamMetadata.ps1` now provides that one-attempt executable host. It
verifies a coordinator-reviewed local plan SHA256 and retains the bound source,
interpreter and provider files. Without `-Run` it only checks the plan; it loads
no native type, obtains no lease and creates no attempt directory. With the
separate coordinator GO, the fixed invocation reserves Analysis 2 GiB physical /
3 GiB commit, uses the existing witnessed NativeJob DLL and exact original-handle
registration/closure primitives, and launches only the Python AppInfo phase.
The outer acceptance deadline is 200 seconds; failed-tree cleanup has 5 seconds.
Outer logs have 64 KiB caps, phase logs have 2 MiB caps, and metadata accounting
checks the combined tool/cache/evidence tree against 512 MiB with receipt space.
These are sampled limits, not kernel quotas. Generic helpers stored under
`h1-fixture` are reused without running an H1 stage or compiler policy.

The host never accepts Python exit alone: it checks fresh original root identity,
exit status and zero active job members before closing handles. Failure stops
only that original job, and forced stop remains failure. Ambiguous closure or
lease release keeps the owner/guards in the live host and retains the lease;
the coordinator must preserve that host for recovery. Closed successful process
execution remains pending review of the actual Steam AppInfo response. Bootstrap
file guards are released before SteamCMD self-update; the updated image hash,
version and signature status are captured after closure. No rerun is implicit.

`Test-SteamMetadataHost.ps1` runs pure PowerShell fault injection with fake owners
and snapshots. Its 27 assertions cover output accounting/caps, late observation,
live children after root exit, identity mismatch, commit pressure, fresh forced
closure, failed stop/release and pre-create failure. They load no native provider
and never start SteamCMD. The final machine-specific plan and exact command stay
under ignored `runtime/`; they require review and GO before `-Run`.

### AppInfo attempt A observed on 2026-10-12

The coordinator authorized exactly one invocation at source `2fc9470` and plan
SHA256 `081d703c285d21cba2cf5c9c267fd1b20bd6026d4b0a16a6cb9cbe713fc90e2a`.
The process attempt **failed**: the original SteamCMD parent returned 7 and
Python returned 1 after 16.656 seconds. The retained receipt is not promoted to
passed. Inspected updater logs show two update stages and cleanup warnings marked
as continuing; the later internal console shows anonymous login, query and unload
OK. These logs do not explicitly establish why the parent returned 7.

The actual primary AppInfo response is present in the separate internal
`logs/console_log.txt`, not in the bootstrap's captured stdout. It confirms:

- App **545990**, **Call of Duty: Black Ops III - Unranked Dedicated Server**,
  type Tool, released for Windows, free-to-download flag set.
- Public depot **545991**, manifest **2350066205567669287**, build **4500243**.
- Declared installed size **3,900,040,220 bytes** and download size
  **3,697,813,104 bytes**. These are depot totals, not a selective EXE transfer.
- Launch entry `UnrankedServer\Launch_Server.bat`, working directory
  `UnrankedServer\`. Individual payload paths/sizes still require its file manifest.

The updated SteamCMD executable is 5,462,168 bytes, version 10.95.69.31, validly
signed by Valve Corp., SHA256
`88f791368cdb3a8c82b84d3ea53f25c18c33b425a0560d5a3f851bd709b35580`.
The closed installation occupies 161,068,764 bytes; with the outer receipt/logs,
161,070,418 bytes. The phase observed a peak of 287,918,599 bytes. The original
job was already empty at root failure; a stop request and second fresh empty
snapshot were retained, followed by closure and lease release. A fresh audit
found zero leases, no original root or tool/host remnants, and the same Main
process generation and UDP27016 owner. No app/depot install or T7 execution ran.

[The sanitized observation](steamcmd-appinfo-observation-20261012.json) binds
the small receipts and logs by hash; raw private logs and the failed attempt are
preserved locally. The useful next step is a file-manifest-only retrieval to
select the minimum executable/dependencies. Repeating AppInfo is unnecessary to
confirm fields already observed. Reusing this updated installation requires an
explicit reviewed profile; do not bypass the old fresh-two-files/bootstrap pin.

### File-manifest preparation

No verified documented SteamCMD manifest-only route was found. The selected
tool is [SteamRE DepotDownloader 3.4.0](https://github.com/SteamRE/DepotDownloader/releases/tag/DepotDownloader_3.4.0),
source commit `c553ef4d60c00a4f5fd16c9fe017f569001589ff`, not a Valve-issued binary.
The pinned `Program.cs:87` recognizes `-manifest-only`; `ContentDownloader.cs:865`
dumps the manifest and returns before file selection/chunk download. The text
dump includes sizes, chunk counts, SHA1, flags and original filenames.

The framework ZIP is 2,661,253 bytes but this release targets .NET 9; the observed
system shared runtime is only 8.0.28. The autonomous Windows x64 archive avoids
a separate runtime installation. Official release metadata and HTTP HEAD agree
on 33,474,005 compressed bytes. Its SHA256
`41c9e9f0df54b3ad02e67a11726756e5c73283bd7c2e1b04acfa5ae4c2ed3767`
is published by the [Microsoft WinGet catalog](https://raw.githubusercontent.com/microsoft/winget-pkgs/master/manifests/s/SteamRE/DepotDownloader/3.4.0/SteamRE.DepotDownloader.installer.yaml);
the upstream GitHub release API digest is null. A metadata-only HTTP Range
inspection was refused with 501; no archive body was read in that failed request.

The coordinator subsequently authorized the tool download/extraction alone.
`prepare_depotdownloader.py` obtained and verified that exact archive, inspected
all entries before extraction, and enforced 40 MiB transfer / 128 MiB extraction
caps into a fresh durable directory. Actual contents are just `DepotDownloader.exe`
(78,840,739 bytes, SHA256
`6281279efce8f1e20db9532a58e42382f81afb9e3827a8b965ffcb43fbe4531f`)
and `LICENSE` (18,431 bytes), totaling 78,859,170 extracted bytes. The executable
has no Authenticode signature; the release/archive hash is the provenance check.
[Preparation receipt](depotdownloader-preparation-20261012.json). No tool execution,
system .NET installation or game-payload transfer occurred during preparation.

The existing host now has one additional fixed operation, `depot-file-manifest`,
attempt `manifest-a`. It starts the pinned portable EXE directly in the same
NativeJob, using anonymous login with distinct LoginID 20261012, exact app545990 /
depot545991 / manifest2350066205567669287, `-manifest-only` and one download worker.
There is no arbitrary-command input or fallback to full-depot download. Its fresh
working directory isolates `account.config`; `-dir` and the .NET bundle/temp
location stay under the attempt output. The old AppInfo bootstrap guard is
unchanged; only the exact 78,840,739-byte DepotDownloader pin may exceed the old
64 MiB source-binding cap. Manifest/cache/temp evidence has an explicit 32 MiB
cap, while existing 2/3 GiB admission, 200/5-second deadlines, 64 KiB outer logs,
512 MiB aggregate observation and original-handle closure remain in force.

The host accepts a closed root0/Active0 result only with the expected manifest
ID/header and a zero downloaded-content-chunk counter. Actual file selection and
binary compatibility remain separate. Manifest (16 MiB maximum) and stdout
(64 KiB maximum) are read through retained `FileStream` handles with
`FileShare.Read`, with an actual limit-plus-one read and stable-length check.
Headers, zero-chunk marker and receipt hashes all use those same byte snapshots;
the guards remain held through final measurement and receipt publication.
Forty PowerShell assertions pass, including attempted growth/replacement while
the original file is guarded, oversized snapshot refusal, and the metadata-output
cap while preserving the smaller AppInfo cap. No native provider is loaded.
The fixed command and freshly bound plan were prepared under ignored `runtime/`;
no execution occurred before the separate reviewed GO recorded below.

### File manifest retrieved without game content

The first actual manifest invocation used reviewed plan revision B, SHA256
`75b90a6e5abe32b788a39a22c6579563de6ead0ad2e44447081bff6658362f3e`,
at source `a3bc3e42`. It completed in 4,976.78 ms with original root exit0,
ActiveProcesses0, normal closure and lease release. No forced stop, quarantine
or retry occurred. A fresh post-run audit found zero leases, no owned root/tool
or host remnants, and unchanged Main process generation / UDP27016 ownership.

The 18,752-byte text manifest has SHA256
`4423aa96951c341b32e34e65787b6ef7fda29733c8a11f4f254a6d1531b35eb8`.
All 174 entries were parsed; their sizes total exactly 3,900,040,220 bytes, matching
AppInfo and the manifest header. The header declares 3,845 unique chunks and
3,697,813,104 compressed bytes. The actual content-chunk counter is **zero**.
Tool plus closed attempt occupies 112,532,097 bytes, including the receipt.
[Sanitized manifest observation](depot-manifest-observation-20261012.json).

The real EXE entry is `UnrankedServer\BlackOps3_UnrankedDedicatedServer.exe`,
21,737,352 bytes, 21 chunks, SHA1 `9d5fdd6f44defb8d65f8f5256e4eb83d4547f408`.
The existing owner's `steam_api64.dll` (235,600 bytes) already matches its manifest
SHA1 exactly; a targeted read verified this without copying it. The executable
and other dependencies have **not** been acquired. Select them from the manifest
against the T7 loader/import needs; reuse BO3's installed FF/XPAK in place.
This result proves manifest retrieval, not T7 address or asset compatibility.

Select the minimum legitimate server executable/dependencies only after a
manifest establishes exact paths and sizes. SteamCMD's full app/depot update is
not a per-file filter. Evaluate an existing compatible selective downloader
only if needed, from its official upstream with a pinned release; a manifest
and file allowlist must precede payload transfer. No full server, Mod Tools,
Additional Assets, game clone, map pack or public redistribution is implied.
Total future task growth stays within the coordinator's 10 GB cap excluding
the owner's current BO3 download. Update tools documentation when an actual
installation occurs, with provenance and measured storage rather than estimates.

## Primary format reference

[Greyhound GameBlackOps3.cpp](https://github.com/Scobalula/Greyhound/blob/master/src/WraithXCOD/WraithXCOD/GameBlackOps3.cpp)
was inspected for the stream structs, UV and normal decoding. Greyhound is a
source cross-check only; it was neither installed nor adopted as a parallel
export route. Existing ZoneTool/Creator components remain the implementation
route. Native compile/export and any donor launch require their separate
coordinated resource admission; no such GO is active for this checkpoint.

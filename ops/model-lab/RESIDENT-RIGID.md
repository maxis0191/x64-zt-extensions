# Resident rigid export connection

This source addition connects the existing Model Lab to an already produced
`t7-iw7-resident-static-v1` or explicitly versioned
`t7-iw7-resident-static-v2` XMB/XSB export. It does not launch the T7 exporter,
convert a second mesh, extract textures, or qualify native/exporter provenance.
The original 24-vertex/12-triangle cube route and its measured FF/reader tuples
remain available. Its corrected LOD0 distance of 1000000 is preserved.

The first selected donor is `p7_fre_platform_cap_02`, zone `mp_freerun_04`, LOD0.
This change has been checked with synthetic bytes only. No real donor export,
FF build, resource admission, game run or rendering is part of that validation.

## Inputs and derivation

Future preparation, after an export and its independent receipt review:

```powershell
python -B -S ops/model-lab/prepare_ff.py `
  --export-root $exportRoot --request $requestPath `
  --manifest "$exportRoot/manifest.json" --output $freshSourceRoot `
  --rebind-material mopw/character_park_clown_zombie_shoes
```

The existing independent `tools-source/asset-bridge/t7-iw7/readback.py` validates
the receipt, hashes and serialized static profile: one root/bone/surface/rigid
list/material, 3..65535 vertices and 1..65535 nondegenerate triangles. Request and
native receipt are limited to 4 KiB each, XMB to 1 MiB and XSB to 16 MiB. Model Lab
additionally requires portable CSV/config names (`A-Z a-z 0-9 _ . / -`, safe path
segments). The actual XSB name comes from the verified receipt, never a guessed
suffix. The export root remains untouched; byte-exact raw snapshots are retained
under `evidence/` in the fresh preparation directory.

The required material option changes only the standalone material ASSET string
in the derived XMB. It refers to the existing IW7 recipient material; no BO3 or
IW7 texture/material payload is copied. XSB is byte-identical. All remaining XMB
bytes, including bounds, rig and LOD metadata, are preserved by default.

An additional **explicit** `--lod-distance 1000000` changes only the four bytes
of `lodInfo[0].dist`. `derived-export.json` records both old/new values and both
declared spans. It has its own `iw7.model-derived-export/1` schema; it is never
passed off as the native export receipt. Revalidation reconstructs the declared
derivation from the preserved snapshots and rejects any third change even when
a staged-file hash has been updated.

Zero or a distance below the Model Lab scene's conservative 256-unit margin is
accepted as a source export but blocks this scene's FF preparation gate with an
explicit diagnostic. This guard is not a universal asset-validity rule, a full
culling analysis, or evidence that the donor will be visible. Other sufficient
finite source distances remain unchanged. Dimensions, pivot, camera placement,
LOD behavior and actual pixels still require the future donor run.

## Existing FF and runtime route

`Build-ModelFF.ps1` detects the resident geometry profile in the preparation
plan, checks the derivation before stock staging, and uses the existing resource
lease, stock transaction, debugger, build/verify/dump commands and restoration
guards. The fixed zone is still `paris_model_probe`. Only the two asset input
paths and expected XModel/XModelSurfs inventory names vary. The NCS asset remains
`ncs_mdl_paris_model_probe`, with the actual XModel name in `stringList`.

The resident route uses Python (`-Python` selects an executable) instead of the
cube's native `-ReaderRun`. After the future FF dump, `rigid_export.py verify-dump`
reuses the independent reader and compares parsed model/mesh metadata plus every
packed vertex, triangle and rigid-list byte against the derived source. Opaque
nonzero pointer values may differ between serializations. The bounded receipt
`geometry-roundtrip.json` binds the FF hash/length, source-plan/derivation hashes
and the two retained dump hashes. The FF is limited to 32 MiB. Its false flags
retain the provenance, donor-fidelity, dependency-payload, rendering and runtime
limits of this comparison.

For a subsequent separately authorized runtime witness, `Agent-Lab.ps1` requires
the existing `-ObservationMode model -ModelBuildRun ...` and
`-ModelReaderEvidence geometry-roundtrip.json`, plus an independently reviewed
tuple supplied as `-ModelReviewedBytes`, `-ModelReviewedSHA256` and
`-ModelReviewedEvidenceSHA256`. Do not auto-approve these values from mutable
build metadata. Historical cube admission continues to use its original tuples;
these parameters cannot bypass that allowlist.

The existing protected scene precaches/requests the validated actual XModel
using `paris_model_asset`; it defaults to the cube when unset. Logs identify the
actual model, and runtime observation matches that escaped name. The existing
capture scenario is unchanged. `fs_game` stays `mods/paris_model_probe`, and HTTP
stays `/mods/paris_model_probe/mod.ff`. An existing larger cache is accepted only
if its bytes/hash match the reviewed rigid FF; foreign cache contents are kept
and refused. `SCRIPT_MODEL_REQUESTED`, `READY_MODEL` and a correct download do
not prove visible pixels, correct shading, textures or owner gameplay acceptance.

The shared `HudHttp.cs` has one explicit `CreateRigidModel` factory, fixed to
ModelRoute and at most 32 MiB, called only after the reviewed tuple gate. All
legacy constructors and their existing size/route limits remain unchanged.

## Explicit multisurface v2

V1 keeps its one-surface contract, scalar `--rebind-material`, manifest schema
`iw7.t7-iw7-resident-export/1` and 4 KiB manifest cap. V2 requires the paired
`iw7.t7-iw7-resident-export/2` and `t7-iw7-resident-static-v2` identifiers; neither
surface count nor file size implicitly upgrades a v1 artifact. The selected
profile remains `resident-rigid-one-lod`: one root/bone, one LOD, 1..255 ordered
surfaces, one rigid list per surface, 3..65535 vertices and 1..65535 triangles
per surface. The model totals must equal all surface records. Material slots
stay in surface order, including repeated dependencies.

Before reading geometry, the common contract and independent reader recompute
`geometry_work_bytes_upper_bound = 256 + 384*N + 60*V + 12*T`, capped at 16777216
bytes. `N`, `V`, `T` are surface count and summed vertex/triangle counts. Every
logical occurrence counts in full, including aliases. This accounts for the
source and destination geometry buffers; it is neither a total RAM/CPU estimate
nor a serialized-file cap. The per-surface allowance includes the 96-byte T7
surface; the earlier 368-byte coefficient assumed 80 bytes and is invalid.
Model Lab rejects metadata claiming that old work value. At `N=6`, `V=267000`,
`T=62888`, the corrected total is exactly 16 MiB; `T=62896`, previously at the
boundary, exceeds it by 96 bytes. V2 manifest bytes have a separate 256 KiB cap,
strings remain bounded to 255 portable ASCII characters, XMB remains at 1 MiB and XSB at
16 MiB. Model Lab v2 derived receipts/plans have a separate 1 MiB metadata cap
for up to 255 surface summaries and material mappings; their v1 cap stays 64 KiB.
No resource admission, mutable-space, FF or HTTP limit is increased by v2.

Future v2 preparation uses `--material-rebinds path/to/rebinds.json` in place of
the v1 scalar option. The JSON file (at most 256 KiB) is an explicit ordered list
with one entry per slot. For example, a **synthetic two-surface** export uses:

```json
[
  {"slot": 0, "source": "original/clay", "target": "mopw/character_park_clown_zombie_shoes"},
  {"slot": 1, "source": "original/clay", "target": "mopw/character_park_clown_zombie_shoes"}
]
```

Each source must match the native manifest's material at that slot. Only the
existing proven recipient reference above is allowed in this step. Shared
ASSET aliases must request the same target. The independent reader identifies
their defining string spans; derivation patches each definition once and keeps
alias record bytes and ledger indices intact. It does not collapse surfaces,
merge their geometry, extract textures or copy material payloads. The recipient
CSV/inventory deduplicates recipient references, while the plan preserves all
ordered slots. The model still has exactly two payload files and five source
files. Optional LOD derivation keeps its existing explicit four-byte scope.

V2 uses internal `iw7.model-derived-export/2`, `iw7.model-ff-plan/2` and
`iw7.model-rigid-roundtrip/2` receipts. They retain `surface_records`, ordered
`material_references` and the recomputed work bound where applicable. Readback
checks every surface's packed position, UV, triangle indices/areas and rigid
coverage. Ordered SHA-256 digests cover all packed vertex/triangle/rigid bytes
for the subsequent FF roundtrip comparison; opaque pointer values may differ.
There is no global expanded position/face list for v2.

The existing runtime gate binds the reviewed FF/evidence tuple to the matching
version, aggregate counts, individual ordered counts, slots and work bound.
Only the exact v1/v2 profile allowlist selects the existing bounded HTTP factory
and larger matching-cache path. Unknown or mixed profiles are refused. Runtime,
pixels, donor fidelity and native provenance remain unqualified by these tests.

## Source validation

`python -B -S tests/ops/model_lab_test.py -v` covers original cube regression,
synthetic irregular geometry, exact material-only and optional LOD derivations,
third-change refusal, packed normal/UV/index mutation refusal, actual names/NCS,
explicit FF/evidence admission, cache preservation and runtime claim limits.
Its FF stand-ins are labeled synthetic data and are never engine inputs.
Resource/process functions are mocked where exercised; no game is launched.

Historical v1 source checkpoint (2026-10-13): 19 Model Lab tests, 31 independent resident
readback tests and five existing shared HTTP regression tests passed. The agent
ownership suite passed 41 controls; the mocked capture-evidence suite and the
four changed PowerShell files' AST parse passed. GSC runtime compilation, native
FF build and donor rendering remain unexecuted and unqualified.

V2 source checkpoint (2026-10-13): 26 Model Lab tests and 40 independent reader
tests passed using original synthetic bytes, including 255 surfaces, exact work
cap/overflow before Reader allocation, repeated material and geometry aliases,
late-surface corruptions, truncations, explicit rebind refusal, proof/plan count
crossing, unknown-profile refusal and the actual HTTP dispatch expression.
The 16 common export-contract tests, five shared HTTP regression tests, 41
ownership controls, mocked capture-evidence suite and four PowerShell AST
parses also passed at this checkpoint.
Initial local test failures (reader return-shape unpacking and a test AST selector
that also selected the null initialization) were corrected before this checkpoint.
No native exporter/FF build, actual readback, game, stock payload read/hash or
resource admission was performed. Next: coordinator source review/integration;
native qualification and any real execution require their distinct approved step.

On 2026-10-14, the render-only streamed export/2 schema was added to the
existing large-manifest dispatch in `load_export`. Its export-manifest cap
remains the reader's 256 KiB; derived receipts and FF plans retain their
separate one-MiB cap. The legacy resident export/1 cap remains four KiB.
A synthetic regression first reproduced the erroneous four-KiB
refusal, then passed full staging and staged verification after the correction.
It retains the exact source manifest and mesh, explicit ordered recipient
bindings and only the declared LOD change. Oversized V2 and legacy V1 manifests
remain refused. This source-only correction does not alter the compiled E5
candidate or prove native FF/runtime behavior.
The 13 streamed-contract tests, 28 Model Lab tests in a fresh pinned source
composition and repository boundaries (715 tracked/697 exports/three
dependencies) passed. An initial Model Lab run from the uncomposed checkout
failed nine dependency-based checks because the Native/SDK files were absent;
the full composed run passed without relaxing those checks.

The community-candidate FF path now defers its full `Assert-BeaconCandidate`
EXE/tlog qualification until the existing Extract lease, before copying/loading
or starting the tool. Its candidate `DryRun` reads bounded producer metadata
and retains the original arena's exact e7 restriction. The existing non-arena
CDB digest check also runs under that lease, once, after candidate qualification.
The legacy ToolProvenance/reader path and World original-owner/stock restoration
remain unchanged. A source-only fixture runs the actual metadata and admission
blocks: candidate preview reads no opaque bytes; changed authored fake EXE bytes
are refused after admission; the valid candidate and diagnostic checks each run
once. This fixture launches no engine and reads no retail or qualified tool PE.

The existing selected 72-input stock mapping is also available explicitly to
`t7-iw7-selected-streamed-render-only-v2` with a community candidate. Other
resident profiles and the legacy tool path do not gain this option. This reuses
the existing flat Doom sources, selected main/zone destinations, copied sentinel,
NTFS identity/content guards and transaction restoration. No arena marker,
game-directory copy or separate stock cache is introduced. The selected recipe
retains 71 links and one independent sentinel copy; its historical baseline
modes are metadata, not new runtime qualification. Actual source guards, content
hashing, link creation and final source proof belong to the admitted FF run.
A source-only selector fixture checks this exact profile, missing-candidate,
wrong-profile, changed-plan and hardlinked-sentinel refusals, plus unchanged
World selection. The frozen source stage remains separate from a future FF.

## Authored rigid source seam - 2026-10-15

`geometry.py::validate_authored(data, *, model_name=None,
material_reference=None)` accepts the existing `iw7.original-mesh-source/1`
document independently of the fixed cube. It returns a new document with
float32 positions, normals and UVs, and conservative float32 local bounds.
The supplied bounds must agree with those derived positions. The source and
readiness flags stay false. The input is never modified.

The profile `iw7-authored-rigid-v1` supports one identity `tag_origin` root,
one surface/material and one LOD, 3..192 vertices and 1..96 triangles. These
limits retain the existing native reader's 8192-byte owned-file ceiling.
Positions are finite within +/-32768; normals are unit vectors pointing with
the triangle winding. UVs range from 0 to 1, including fractional coordinates.
Prepared UV words use the existing IEEE binary16 nearest-even, U-low/V-high
convention. Tangents derive from the actual half-precision UVs. Mirrored or
degenerate UV triangles, unused vertices and conflicting tangents are refused.
This profile does not establish the IW7 shader normal/tangent ABI.

Namespace, zone, model and mesh names are portable flat identifiers
`[A-Za-z0-9_]+`, at most 63 characters, excluding Windows device names.
Material names additionally allow slash-separated portable segments, at most
127 characters. Names are data; no per-model hook or allowlist is added.

```python
# Pure source validation; safe to use from Creator Plan.
mesh = geometry.validate_authored(document, model_name=model_name,
                                  material_reference=material_name)

# Existing pinned writer preparation; no compiler, stock or game operation.
manifest = prepare_writer.prepare_authored(
    fresh_output, pinned_tool_source, geometry_source_path,
    namespace=namespace, zone=zone, mesh_name=mesh_name,
    material_reference=material_name)
```

The CLI adds `--geometry-source`, `--namespace`, `--zone`, `--mesh-name` and
`--material-reference` to the existing `prepare_writer.py --output --source`
entry. All five authored options are required together. Retail recipient
options cannot be combined with this route. Tool interface hashes retain
the exact `fab935826c898806855376662a8a03317b3ad8f1` pin.

Preparation writes `geometry.source.json`, `probe_geometry.hpp`, `writer.cpp`,
`writer-source.json`, `zone_source/<zone>.csv` and
`netconststrings/ncs_mdl_<zone>.json`. The model is `document.name`; the mesh
name is explicit. The future owned outputs are `xmodel/<model>.xmb` and
`xsurface/<mesh>.xsb`. Bounds, counts, names and packed UV data adapt the same
native writer AND its existing-dump reader. No stream layout or serializer is
invented. Exact replacement checks refuse a changed serializer seam. The
legacy writer template, original cube preparation and World adapters are kept.

`verify_authored_preparation(prepared)` (CLI `--verify-authored`) reconstructs
that source recipe and rejects changed source even if its declared hash was
updated. `Build-Writer.ps1` accepts this explicit profile only after that check,
then retains its pinned interface, fresh outputs, resource admission and native
roundtrip gates. Its resulting artifact paths and report identities come from
the authored contract. This wrapper change has source validation only; no new
native writer build or XMB/XSB roundtrip has been measured.

`Build-Writer.ps1 -ToolSource <existing-pinned-checkout>` explicitly reuses an
ordinary Native source directory when the composed package has no
`tools/x64-zt-enemy` checkout. Omitting the option keeps that exact legacy
default. The override rejects redirected ancestry and non-directories; the
existing exact Git pin, clean checkout and ten source-interface hashes still
apply before compilation. It does not clone/copy a tool tree or change the
source checkout. The preview/build provenance records `ToolSource`.
`-DryRun` now returns only the validated Source admission preview, with compiler
and arguments null. It does not discover VS/SDK, hash opaque binaries, load
native types, acquire a lease or create a native-run receipt.

Actual execution additionally requires `-NativeJobAssembly` pointing to the
retained H1 original owner (SHA256 `5f613ebb83019dbf4bfa4f6a93c5329098343729b70acc2cfa70aa8b64f195f8`)
and a fresh persistent PS7 `-NoExit` host. The writer obtains **one** existing
Build reservation before any native import, VS discovery, SDK query or compiler
argument preparation. Discovery (`vswhere`), compilation and the writer itself
use the existing H1 owner through `T7Build.Profile.ps1`; no shell compiler or
second reservation is used. Exact compiler/VCTIP policy, original handles,
deadlines, sampled output bounds and ordinary zero-active closure remain H1
checks. Compiler artifacts are retained in `compile/`, with byte-checked copies
at the historical `model-writer.exe` / `writer.obj` locations. The existing
native serializer/reader and its report gate remain unchanged.

The same context, original PSVariable, lease and guard list are retained if
creation/closure or final input validation is unknown. `Complete-H1Stage` has an
optional typed `BeforeReleaseCheck` callback; the default behavior is unchanged.
The writer rechecks bound inputs and closes its guards inside that callback
before releasing the original lease. Callback failure or unknown job closure
retains the original lease and objects in AppDomain quarantine. A native-run
receipt records failure/closure; `writer-provenance.json` is published only after
all jobs, guards and the one lease are confirmed closed. Source/compiled output
bindings are guarded; full SDK/DLL hermeticity is not claimed
(`ToolchainFullyHermetic=false`).

Preparing a Source capsule does not invoke this execution route. CPP, opaque
input inspection and FF still require their separate reviewed GO. Tests here
are Source/mocked lifecycle tests; they do not qualify the real compiler,
discovery executable, NativeJob DLL or native geometry.

The zone CSV declares the authored material as a **local payload dependency**,
not an ignored retail reference. This producer supplies no material/image bytes:
`material_payload_present=false`, `material_closure_required=true`. The separate
surfaces producer must provide that closure before an FF can be prepared.
The historical `prepare_ff.stage` route still requires five inputs, fixed
`paris_model_probe` zone/NCS, and the measured M7 recipient material. Those
legacy gates remain strict. The explicit authored FF connection below joins
the owned material closure in the same ModelFF path.

Source tests cover two distinct geometries/names, fractional positions/UVs,
derived bounds, serializer and reader adaptation, updated-hash tampering,
invalid source/claims and the preserved strict legacy cube contract. No
CPP/FF/Native/PE/stock/lease/game operation is part of this checkpoint. Player
contact/collision, rendered diffuse/orientation/alpha, ABI and owner acceptance
remain unmeasured; `collLod=255` and null physics do not prove collision.

## Authored material connection in existing ModelFF - SOURCE ONLY

`prepare_ff.stage_authored(writer_run, fresh_output, *, material_inputs)` takes
the existing `surfaces/authored_dds_material.py::prepare_material(...)` result
directly. The writer run must contain its reviewed authored source recipe plus
the actual future `Build-Writer` provenance, native roundtrip and two measured
XMB/XSB files. Source tests use explicitly synthetic receipts/bytes instead;
they do not supply native evidence for a creator project.

The same surfaces producer reconstructs the owned DDS/material/sidecar recipe.
Its selected diffuse is local; its techset and remaining images alone become
explicit recipient references. ModelFF joins its CSV with XModel and NCS rows,
keeps the complete writer source/provenance under `evidence/writer`, and emits
`iw7.model-ff-plan/3` with the existing `iw7-authored-rigid-v1` profile. Names,
zone, NCS, selected counts, exact source hashes and expected inventory derive
from that project. The existing content Inspector checks material/state fields
and references; its 8 MiB per-image preflight ceiling also applies to this
connection. No additional compiler, FF builder, image decoder or asset serializer
is introduced. Python callers can use the API; no new SDK orchestration is owned
here.

`verify_authored_stage(source)` (CLI `--verify-authored-stage`) reconstructs
the joined recipe, rechecks the writer evidence/artifact hashes, source flags,
material/DDS metadata, CSV/NCS and complete local payloads. Replacing a payload
and updating only its staged hash cannot qualify the recipe. The source plan
retains `material_closure_verified=false`, `ff_built=false`, `ready=false`.
These DEFAULT source checks do read/hash the bounded, isolated original
DDS/XMB/XSB/sidecar bytes supplied by the author. They do not read retail/stock,
banks, a native FF, executable or symbols, or launch a game/process fixture.

`Build-ModelFF.ps1` dispatches this explicit profile through its existing stock
transaction, shared admission, strict community-candidate qualification, native
process runner, build/verify/dump commands and restoration. It requires both
`-CandidateRoot` with its producer digest and `-ReaderRun` bound to this stage's
writer provenance/hash/geometry. The native reader executable is rehashed under
the existing lease. Zone arguments, mutable FF path, dump path, input count and
inventory vary by project; the old cube/resident/World paths remain separate
strict branches. No per-model binary allowlist or hook is added.

After a future admitted FF dump, the **same** compiled native writer executes
`--verify-existing` against the two dumped geometry files. The existing surfaces
`verify_image` compares the authored DDS's typed format, dimensions, explicit
single mip, semantic and every serialized pixel/block byte. Material JSON fields
and conditional state/CBI sidecars are compared; CBT is required nonempty when
present, with `native_cbt_semantics_verified=false` because pointers/layout are
not proven by equality. `surface-roundtrip.json` binds source-plan and FF hashes.
The authored `geometry-roundtrip.json` retains the native
`iw7.model-roundtrip/1` report and adds `source_plan_sha256`, `ff` and the two
`dumped_artifacts` path/length/SHA256 records after successful native comparison.
The build state records `GeometryReader`, `SurfaceReader`,
`GeometryEvidenceSHA256` and `SurfaceEvidenceSHA256`; there is no separate
`NativeGeometryReader` field. The prior standalone writer proof remains
`writer_run/writer-provenance.json`.
Rendered pixels, recipient resolution, player contact, shader ABI and owner
acceptance remain false/unmeasured even when those offline byte checks succeed.

Validation here consists only of synthetic source/receipt/owned-byte fixtures:
two independent mesh/name/material projects, complete local DDS/state closure,
recipient versus local inventory, tampering and false provenance refusal,
existing PowerShell input/inventory/admission gates, image/material readback
comparisons and unchanged legacy inventory. No actual CPP, FF, PE, stock, lease,
native process or game run has occurred. The source route is connected;
Creator must keep native build/readback/runtime qualification pending.

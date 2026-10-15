# Original arena source and collision seam

Owner: `x64-zt-extensions`. Native shape creation/query integration belongs to
`iw7-mod-components` and is coordinated with the engine worker. Gameplay/lab
installation belongs to the server; creator distribution belongs to the SDK.
This directory does not change those shared implementations.

The separate [platform/contact source jointure](../platform-contact/README.md)
uses one authored 256×256×16 mesh matching the fixed a572 fixture. It does not
resize this seven-box arena, alter writer D or qualify a new runtime cohort.

`arena.py` authors seven original axis-aligned boxes: a 512 × 384 floor, three
closed sides, a south doorway, and an obstacle. Face-local geometry is derived
from the existing original cube authoring function, yielding 168 vertices and
84 outward triangles. The scene also declares a goal volume and a two-segment
route around the obstacle. No retail geometry, complete commercial map or
Havok payload is copied.

`prepare.py` emits fresh original JSON/header files and adapts the existing
`ops/model-lab/writer.cpp` in ignored scratch. It changes only the asset names,
counts, bounds/radius, and report. Assetmanager record ordering, filesystem
ownership, pinned C++ layouts and fresh-output semantics remain that writer's
implementation. Exact replacement seams fail if it changes. No new general
serializer or supervisor is introduced. There is one rigid root and one LOD;
the material is deliberately unbound and physics dependencies remain absent.

`readback.py` imports only the existing bounded typed-record cursor. It checks
the IW7 736-byte model, 56-byte surface group, 256-byte surface, each original
position/UV/normal candidate/index, rigid coverage and matching bounds after
serialization. It is independent of the generator and native writer. Its scope
is this small original rigid profile, not arbitrary XModels, shader decoding,
Havok shapes, complete fastfile validation or runtime acceptance.

## Source checks and preparation

From this product checkout, using Python 3.12:

```powershell
python -B -m unittest discover -s tools-source/asset-bridge/world/original-arena -p test_arena.py
python -B tools-source/asset-bridge/world/original-arena/prepare.py --output "$PWD/runtime/original-arena-source-a"
```

The output must not exist. Operations consuming other products use their new
qualified source package; never edit that generated package. Native compilation
and execution require the global heavy-workload grant and an existing owned
stage runner. Reuse the World `Invoke-WorldStage` → T7 → H1 stages: direct `/c`,
direct Link, fresh writer output, independent Python readback. Do not call the
fixed 24-case World CLI or its stdout validator for this different fixture.

After a coordinated build, the independent check is:

```powershell
python -B tools-source/asset-bridge/world/original-arena/readback.py --artifacts <owned-writer-artifacts> --geometry-source <prepared-geometry.source.json>
```

Current source result: 28 targeted tests pass. Default source preparation produces seven
files, including a 55,918-byte geometry document and about 14 KiB of adapted C++.
No native compile, fastfile, material binding or game result is implied. The
previous World 24-case native receipt is preserved at its original paths and
identities; it qualifies the reused lifecycle, not the relocated/new arena.

## Visible original model through ModelLab

The explicit `iw7-original-arena-rigid-v1` profile reuses the existing ModelLab
FF runner, inventory, stock links and restoration. It is an authored original
model, not a resident T7 export. One combined surface contains all seven default
boxes (168 vertices, 84 triangles), with the existing `paris_model_probe` zone,
NetConstStrings and rawfile names. These names require an exclusive ModelLab
scenario; the XModel/mesh names remain `paris_original_arena` / `_lod0`.

The historical unbound writer Plan remains byte-exact but is retired from execution.
A separate material-bound source variant may still use the retained legacy
fresh material-bound source variant uses the cube's extracted source/recipient
validator, rechecking its three snapshot files and three normal-source hashes:

```powershell
python -B tools-source/asset-bridge/world/original-arena/prepare.py --output <fresh-bound-source> --source <pinned-tool-source> --recipient-evidence ops/model-lab/recipient.evidence.json --stock-root <existing-recipient-snapshot>
```

This emits `arena-writer-source.json` as source metadata, with compiled=false.
After a separately coordinated native build, stage only its bounded XMB/XSB:

```powershell
python -B tools-source/asset-bridge/world/original-arena/model_lab.py stage --artifacts <bound-writer-artifacts> --prepared-source <fresh-bound-source> --output <fresh-ff-source>
python -B tools-source/asset-bridge/world/original-arena/model_lab.py verify-stage --source <fresh-ff-source>
```

`verify-stage` returns the five FF input hashes and all eight relative paths it
consults under staging (`validation_files`, including source metadata and the
plan itself). The creator SDK can capture/recheck those same bytes. The helper
uses the existing CSV/NCS authoring adapter unchanged; it never invents a T7
manifest or copies recipient material payloads.

`Build-ModelFF.ps1` dispatches this profile to the arena's independent Python
reader for source validation and FF re-dump. `verify-dump --source <staging>
--dump <owned-redump> --ff <owned-ff>` checks authored positions, rig/LOD/material,
and byte-identical packed vertex/index/rigid streams, then reports plan/geometry/
FF hashes. Raw pointer relocation is allowed; the named material must match.
The helper does not parse the FF container or independently establish native
producer provenance. Its geometry checks complement the existing tool run and
inventory evidence. Every source/test receipt keeps native provenance, pixels,
runtime and physics unverified. No material-bound native run or FF was performed
for this source change; collision remains a separate native engine task.

## Collision that still needs a native primitive

### 2026-10-14: source contract for the first original box

The optional `prepare.py --first-box obstacle` writes `first-box.source.json`
alongside the existing inputs. It binds the geometry document's SHA-256 and
selects surface0 vertices144–167 / triangles72–83. The combined model remains
168 vertices /84 triangles; this selection does not isolate its rendered mesh.
Default preparation and writer/ModelLab/readback inputs remain byte-identical.
No new FF, native serializer, provider, gameplay fixture or HKX format is added.

For the first obstacle, local min=(16,-32,0), max=(48,32,32), midpoint=(32,0,16)
and half=(16,32,16). Model angles are identity(0,0,0), with X→X/Y→Y/Z→Z axes.
The source mapping is `world = model_origin + uniform_scale * local`.
Default origin=(0,0,0), scale=1 makes these exact local/world bounds coincide.
`--model-origin X Y Z` / `--model-scale S` require a selected box, positive exact
float32 scale/origin, and exact finite noncollapsed float32 endpoint results.
Rounded or collapsed world endpoints are refused before output creation.

Example **source preparation only**, with a fresh output:

```powershell
python -B tools-source/asset-bridge/world/original-arena/prepare.py --output <fresh-source> --first-box obstacle --model-origin 0 0 0 --model-scale 1
```

The same optional arguments can accompany the existing measured M7 material
binding. The sidecar then carries only that named reference; it does not turn
the measured nondefault reference into a rendered material or texture proof.

The current collision provider's source contract accepts absolute IW7 game
min/max on a dedicated `script_model`: call `solid()` before
`collision_createbox(minimum,maximum,1)` for world0 and one observed box. Use a
distinct collision owner; its origin/angles/modelscale do not transform these
arguments. The provider computes float32 midpoint/half, instantiates at that
midpoint with quaternion(0,0,0,1), and internally converts half-extents1/32.
Do not predivide GSC bounds or infer a rotated body from a rotated visible model.

Native collision E qualified a solo zero-client query/removal/counter episode,
not this geometry, seven simultaneous bodies, rendered contact, prediction or
player movement. Existing Rig/BO3 display geometry is a different source and is
not used to infer these bounds. This sidecar is source correspondence only:
actual render transform/bounds, collision, prediction, movement and runtime
remain false. It is not consumed by the writer or gameplay fixture.

Next: measure the actual identity-rotated visible original obstacle and bind
its observed origin/scale to these exact source faces before proposing one
collision episode. The current writer can only produce the combined seven-box
profile. An isolated24/12 model needs a separately reviewed profile change and
FF/build plan; neither is authorized by this source-only preparation.

The reference query expands each authored box by the query half-extents and
intersects a segment using slabs. Query coordinates are **box centers**, not
player feet. It handles start-solid, misses, tangency and motion into a boundary.
For the declared actor box (15, 15, 36), a fall from (0, 0, 80) to (0, 0, 20)
hits the authored floor at center z=36 / fraction 44/60. A point trace from
(0, 0, 32) to (0, 0, -32) hits at fraction 0.5. Side-wall and obstacle collisions,
door clearance and the route are tested. This is an analytical AABB oracle,
not a Havok capsule, convex margin or engine collision result.

The goal uses the existing trigger-record adapter. It remains geometry/type
data only and cannot make the floor solid. In the pinned ZoneTool converter,
`havokWorldShapeData` is empty. No static box builder/registry/serializer ABI has
yet been qualified. Engine source exposes `PhysicsQuery_LegacyTrace` at
0x14055C9E0 in pinned IW7-Mod 77e6d4d, through `fx/engine.hpp` and the bounded
trace allocation in `fx/update.cpp`; that is a query entry, not a shape creator.
Names such as `solid`/`setcontents` are not accepted as proof of body allocation.

The smallest required engine seam is one original static box with explicit
coordinate scale, allocator/lifetime, world/shape identity, contents/filter and
margin. Create/link it only in the owned private scenario; run the floor-hit,
outside-miss and side/swept-box cases; remove it and confirm native closure.
Entity bbox collision and true world Havok collision must be labeled separately.
If this seam succeeds, the same seven source bounds can be associated with the
rendered model and goal. Until then a visible model or trigger readback cannot
be called a navigable original arena.

Next steps: qualify this small model serialization/readback under a short heavy
slot; bind a verified recipient material and reuse FF build/dump; coordinate the
static-box primitive with the engine worker, then prove collision and protected
private navigation. No full stock/game copy or large asset extraction is needed.

## 2026-10-14: measured stock reference and current FF recipe

The previous three-file recipient material snapshot was not recovered. It must
not be reconstructed from a name in an old FF inventory. `Measure-StockReference.ps1`
uses the existing e7 community candidate's `-enemy-reference-check` for exactly
one named material on cp_zmb. Its CSV distinguishes verified, missing and default
assets. This proves a nondefault registered stock reference, not the material
payload, a shader/alias, GPU output or a live client binding. The temporary zeroed
Material in the writer only serializes its named reference; it does not establish
the cause of the Rig display issue.

Run all operations from a freshly composed, verified source package containing
these World exports and native provider `2f9462`. Its resource and memory policy
is TelemetryOnly. SDK `f4e5` is the creator source contract; do not substitute its
older native providers for this runtime package. The immutable legacy Plan3057
contains the old null-material/P2/headroom contract and is NOT GO.

The concrete sequence is below. `$package`, `$toolSource`, `$candidate`, `$jobDll`,
`$stockBinding` and `$stockBindingSHA` are the reviewed local bindings. The latter
is the existing 72-input Rig stock mapping, with only the sentinel copied and the
other selected inputs hardlinked from the suitable existing dedicated. Before
stock preparation, fetch/read the current server RESOURCE, STORAGE and INSTANCE
workflows. Every output below is fresh under `$package/runtime`; source packages,
retired plans, stock, Main27016 and occupied clients remain preserved.

```powershell
$world = Join-Path $package 'tools-source/asset-bridge/world/original-arena'
$reference = Join-Path $package 'runtime/original-arena-reference-c'
$prepared = Join-Path $package 'runtime/original-arena-bound-c'
$native = Join-Path $package 'runtime/original-arena-writer-c'
$staged = Join-Path $package 'runtime/original-arena-ff-source-c'
$ff = Join-Path $package 'runtime/original-arena-ff-c'
$measureArgs = @{
    PackageRoot=$package; RunRoot=$reference; StockBindingPlan=$stockBinding
    StockBindingPlanSHA256=$stockBindingSHA; ToolSource=$toolSource
    CandidateRoot=$candidate; NativeJobAssembly=$jobDll
    CandidateArtifactSHA256='f0d4d7db132d51c789a999e33ab0ce905b2df749db453029f91356b9aa2e2165'
}
& "$world/Measure-StockReference.ps1" @measureArgs
# After source review and the coordinator's Extract slot only:
& "$world/Measure-StockReference.ps1" @measureArgs -PlanSHA256 $measurementPlanSHA -Run
python -I -S -B "$world/prepare.py" --output $prepared --source $toolSource --recipient-evidence "$reference/reference-evidence.json" --stock-root $reference
$writerArgs = @{PackageRoot=$package;PreparedRoot=$prepared;ToolSource=$toolSource;RunRoot=$native;NativeJobAssembly=$jobDll}
& "$world/Build-ArenaWriter.ps1" @writerArgs
# Review its new Plan after actual measurement, then use a separate Build slot:
& "$world/Build-ArenaWriter.ps1" @writerArgs -PlanSHA256 $writerPlanSHA -Run
python -I -S -B "$world/model_lab.py" stage --artifacts "$native/artifacts" --prepared-source $prepared --output $staged
python -I -S -B "$world/model_lab.py" verify-stage --source $staged
# After confirmed native closure/release, a separate Extract slot:
& "$package/ops/model-lab/Build-ModelFF.ps1" -RunRoot $ff -StockToolRoot $stockRoot -SourceRoot $staged -CandidateRoot $candidate -CandidateArtifactSHA256 $measureArgs.CandidateArtifactSHA256 -NativeJobAssembly $jobDll -StockBindingPlan $stockBinding -StockBindingPlanSHA256 $stockBindingSHA
```

Default measurement and writer Plan modes read small sources/receipts and defer
known executable hashes until the Run reservation is held. The original-arena
ModelFF candidate path reads bounded metadata first and qualifies the actual e7
EXE/tlog under its existing Extract reservation. Other ModelFF paths retain
their existing qualification behavior; general DryRun is not a replacement for
the World LIGHT recipe. The measured reference plan/request/native image/identity/full log output
are bound together; an open job, wrong recipe digest, replaced root image, extra
CSV row, wrong output marker or unrestored stock is refused. The reader is also
run before publishing successful reference status.

The writer retains the existing direct World/T7/H1 Compile, Link, writer and
independent Check jobs: shared 90-second Compile/Link allowance, 10-second writer,
5-second check and 120-second group; 2 GiB physical / 3 GiB commit estimates.
It checks all three rigid masks, named material and authored packed streams.
Its compiler environment is explicitly not fully hermetic.

Measurement and FF each request one 8 GiB physical / 11 GiB commit Extract
admission. FF consumes the selected mapping directly, so no intermediate full
game copy or extra stock view is needed. Strict-source build, verify, dump and
the independent 30-second reader use the retained H1 NativeJob owner, separately,
with original root0/Active0 before advancing. The small World caller reuses that
owner, registration, exact-handle cleanup and output accounting; it creates no
new generic supervisor or second reservation. Stream thresholds are sampled
at 2 MiB; generated output has one 256 MiB allowance across the FF phases.
Source proof precedes guard disposal, restoration and release. Unknown creation,
closure or source proof retains the original context/guards/lease in quarantine.

These are source-reviewed routes, not native run receipts. Source mocks test the
delegation, telemetry-only pressure and failure/unknown-owner handling; they do
not qualify a native job. Actual measured reference, writer/FF/readback receipts,
pixels, collision, navigation and owner gameplay remain pending coordinated GO.

## 2026-10-14: writer-only plan after the measured M7 reference

The first writer proposal retains the existing seven-box168/84 profile and one
obstacle sidecar. The seven default preparation files plus material-bound
`arena-writer-source.json` and `first-box.source.json` make nine source files.
The native helper consumes its existing four files (writer, header, geometry,
material manifest); the sidecar is not an engine payload. Source preparation
uses `python -B -S prepare.py`: direct `-I` removes the script directory needed
by `import arena`. The independent reader retains its existing `-I -S -B` route.

Use the immutable M7D evidence/CSV hashes recorded in WORLD-ASSET-BRIDGE.md and
the pinned ZoneTool interface source `fab935826c898806855376662a8a03317b3ad8f1`.
No stock file is needed by this standalone writer. Material binding consults
only its small reference snapshots/request/closed plan and three normal source
proofs; it does not copy material payloads or replay the reference measurement.
The composed package must retain native helper policy
`2f9462db806bbd3ab51f9ecb2f3b25ae54ae10f1` and the exact reviewed assets revision.

The writer's stale Python pin `31073dad…` is corrected to
`4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a`.
This digest comes from the actual closed M7D reference reader: Python3.12,
exit0, root exited, active0 and job closed at14:14:25 UTC. This source correction
is not a fresh binary measurement. The next admitted Build must hold/recheck
the actual selected Python image against that digest before any process starts.
The exact pin fails if PATH resolves another Python; there is no fallback.
MSVC14.44.35207/SDK10.0.26100.0, cl/link/vctip and NativeJob5f pins remain unchanged.

Plan through existing `Build-ArenaWriter.ps1`, then review its newly generated
local recipe hash before a separate GO. Start the approved invocation in one
fresh original PS7 host with `-NoExit` before `-File`/`-Command`, record that
host's image/PID/parent/creation before the helper, and preserve its same live
AppDomain for failure/quarantine inspection. Invoke the helper once. It owns
the sole Build lease, guarded inputs, Compile→Link→Fixture→Check jobs and
closure/source-final/output/release path. No wrapper lease, independent kill,
stock aliases, game launch or replacement supervisor is required.

Expected readback: XModel `paris_original_arena`, XSurface
`paris_original_arena_lod0`, root `tag_origin`, one root/surface/LOD,168/84,
identity bind/model scale1, midpoint(0,0,40), half(272,208,56), named M7 material,
all positions/UVs/normal candidates/white colors/indices/rigid coverage and three
root part masks. Writer self-read compares full packed attributes including
tangents; the independent reader checks the listed semantics and complete
record consumption. It hashes packed streams but does not independently decode
tangents or qualify normal encoding on the GPU. Physics names, collision tree,
blend streams and runtime qualification remain absent/false. Each XMB/XSB is
bounded to8192 bytes; Check stdout is bounded to4KiB with empty stderr.

The existing shared Compile+Link allowance is90 seconds, Fixture10, Check5,
whole group120. Output64MiB is sampled, with2MiB stream threshold and1MiB
metadata reserve. The2GiB/3GiB estimates are telemetry under the pinned policy,
not independent admission thresholds. Known opaque image digests are deferred
until the single Build admission. Unknown closure/source proof retains the
original guard/owner/lease context; no receipt/PID/token recreates those handles.

Future FF naming remains zone/FF/rawfile `paris_model_probe` and NCS
`ncs_mdl_paris_model_probe`, with five payload inputs and three metadata files
in staging. Ops55's Rig consumer uses a different FF/model cohort and must stay
preserved. A future World consumer needs its own admitted model names and a
measured identity actor/transform; Native62 and Ops55 own those changes.
Native25's model_probe diagnostic targets `paris_model_probe` and its mesh;
sharing the zone/NCS names does not admit `paris_original_arena` or its mesh.
Its scene observer is Rig-only. A future opt-in World diagnostic/profile and
separate protected consumer must be reviewed by those owners before render GO.
These filters constrain diagnostic qualification, not general engine loading;
an omitted World witness cannot establish absence of that model in the engine.

**FF coverage gap:** current ModelFF accepts exactly the72-input binding and
declares assetfile1. M7's successful reference used a fixed33-PAK/104-input cohort.
The standalone writer proves neither cohort sufficient for a new FF. Do not
pass the M7 cohort as a72-input plan or claim FF provenance from source tests.
Any finite-cohort FF extension is a separate source follow-up after measured
writer/readback and demonstrated need, with the existing managed transaction.
No FF/Extract/Game authorization is included in this writer-only proposal.

## 2026-10-14: writer B produced records; independent metadata check failed

The unique approved B attempt compiled and linked with exit0, then its writer
exited0 and self-read168 vertices/84 triangles with the named M7 reference.
It produced a984-byte XMB and6274-byte XSB. The independent Python Check exited1
at the seven-byte XModel metadata tuple, so the B native attempt remains Failed.
No FF, stock staging, game or physics stage ran.

The actual bytes8..14 were `(0,1,0,1,255,6,0)`. The old reader/synthetic fixture
expected a final1. Pinned `iw7/structs.hpp` maps byte14 to
`characterCollBoundsType`; the original writer zero-initializes that member.
`hasLods=true` is already byte9. Correct the reader's final expected byte to0
and the synthetic fixture accordingly, keeping the other metadata checks exact.
The causal executes the prior predicate in the actual reader body against the
observed header, then checks the corrected reader and corruptions of hasLods,
collision sentinel, shadow cutoff and character bounds type.

The corrected source reader also passes the complete preserved B XMB/XSB:
positions/UVs/normal candidates/indices/rigid masks/bounds/material and full record
consumption. This is a light source diagnostic over existing generated records,
not a rerun/reclassification of B or a new compiled candidate. B's original
failed receipt, packet, source package, stdout/stderr and artifacts stay intact.

All four original jobs closed. The helper published/accounted934974 bytes and
verified source hashes before confirming its sole lease release. The immutable
run.json is a BEFORE-release snapshot; the same live original host's returned
state reported FinalReceiptVerified=true/LeaseReleased=true/Confirmed/token null.
Failure closure verified the actual original job/process handles closed, guards0,
native quarantine null and fresh global leases empty before clearing the retained
failed caller root. Native Check exit1 remains authoritative for the failure.

The child NoExit shell was instructed `exit1`; the actual external PTY returned0
because Launch did not propagate the child result. Earlier PTY1 claims are
explicitly retracted in a preserved additive exit audit. Fresh observations found
the original host/parent and native identities absent; one transient PID reuse
was distinguished by image/creation and never touched. This is FailedKnownClosed,
not readback/native acceptance. A future C launch must explicitly propagate the
child result to the outer PTY and use a distinct source package/recipe/GO.

Resource policy is now owned by `iw7-mod-components`: fetch/read its current
RESOURCE-WORKFLOW before heavy work. STORAGE/INSTANCE remain server ownership.
Next: source/private Git review and exact-head CI audit, then a new additive C
capsule; no automatic CPP retry or change to the frozen B package is authorized.

## 2026-10-14: C readback process passed; post-read canonical path failed

The distinct approved C used the corrected reader. Compile/link/writer/Check all
exited0 (approximately2.23/3.10/0.23/0.25 seconds). Check's633-byte stdout fully
verified168/84, model984 bytes/mesh6274 bytes and named M7 material; stderr was
empty. The overall native harness still failed after Check: the call site passed
`"$dir/stdout.log"` into Read-H1SmallJson, whose existing Assert-H1Path requires
exact canonical Windows separators. The forward-slash string differs from
Path.GetFullPath, even though Python and ordinary Get-Item accept it.

Only that producer call now uses `(Join-Path $dir 'stdout.log')`. Generic H1 path
and size guards remain unchanged. The causal runs the actual strict JSON reader
and the actual writer assignment against an authored stdout: old slash refused,
new canonical path accepted, relative and oversized inputs still refused. A
light source diagnostic over C's saved Check report confirms the corrected
assignment, without a new process fixture/CPP/lease or reclassification of C.

Original jobs all closed. The helper's source-final and934571-byte publication
were verified before its confirmed lease release. Failed caller recovery used
the same original references, actual closed job/process handles, guards0/null
quarantine and empty fresh registry before FailedKnownClosed/CanExit. C's child
exit1 was separately captured by Launch; actual outer PTY also returned1. Fresh
host/parent/native identities were absent. C remains overall Failed while its
individual Check exit0/readback is separately recorded. B and C inputs/receipts
remain immutable. No stock, FF, Game, renderer, collision or movement claim.

Next: source/private PR/exact-head checks/review and a distinct additive D tuple.
No repeat of C or automatic native build is authorized by this correction.

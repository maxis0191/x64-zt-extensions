# Original arena source and collision seam

Owner: `x64-zt-extensions`. Native shape creation/query integration belongs to
`iw7-mod-components` and is coordinated with the engine worker. Gameplay/lab
installation belongs to the server; creator distribution belongs to the SDK.
This directory does not change those shared implementations.

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

Current source result: 23 targeted tests pass. Default source preparation produces seven
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

The default unbound writer and its queued native Plan remain unchanged. A future
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

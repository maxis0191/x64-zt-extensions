# Original rig chain: recipe and specialized executor

`plan_rig_chain.py` prepares the eight ordered steps from original rig inputs to
native XMB/XSB, FF build/verify/dump and independent readback. It reads and hashes
existing files only. It has no Run option, subprocess, native helper import,
lease, stock enumeration, copy, directory creation or compiler invocation.
The printed plan is review data, not an executable success receipt.
`Build-RigChain.ps1` consumes that exact hash-bound recipe. Its default action
reproduces the full recipe from current sources and inspects toolchain metadata.
Only a separately authorized `-Run` enters admission or invokes native helpers.
One authorized attempt passed all four native phases, then stopped before
ZoneTool because FF logs aliased the compiler artifact directory. The failed
attempt is preserved and restored. The source correction has not been rerun;
see [the run record](RIG-RUN-2026-10-12-A.md).

The planner binds the nine reviewed providers from the successful animation FF,
the existing full ZoneTool candidate and BuildJob, original clip, prepared rig
source/header and eleven actual IW7 interfaces. It rechecks the installed
compiler from the previous clip receipt and requires the existing Windows SDK.
Nothing is downloaded or copied. New pins require a coordinator review rather
than silent acceptance. The proposed run root must be a fresh child of this
worktree's ignored runtime and remains absent after planning.

## Ordered phases and retained data

| Group | Phase | Exact purpose |
| --- | --- | --- |
| Native | compile | Recovered two-bone writer using the real prepared header and SDK types |
| Native | emit-first | Fresh `native/first/xmodel` and `xsurface` outputs |
| Native | emit-second | Fresh `native/second/xmodel` and `xsurface` outputs |
| Native | read-native | Complete independent read of both pairs, then four-key clip/rig CPU oracle |
| FF | build | Distinct `sdk_original_rig_probe` zone using existing full ZoneTool |
| FF | verify | Exact seven-row inventory; refuse unresolved/default/extra/duplicate rows |
| FF | dump | Produce the named model, surface and XAnim redumps |
| FF | read-ff | Read both native pairs and all five redumps, compare decoded rig/clip semantics |

The runner closes the native group and releases its reservation before FF
admission. It does not skip compilation/emission using retained pairs.

The exact proposed CSV includes the existing reference material, both distinct
models and the clip. The native two-bone profiles remain unchanged. Expected
offline inventory is seven assets: material reference, two XModels, two
XModelSurfs, one XAnim, and the zone branding rawfile. No runtime model/animation
registry is included in this offline pack. The reference material's presence in
inventory does not prove map resolution, shaders or pixels.

FF staging proposes the existing 72 bound stock entries, candidate executable,
four actual native model/surface files, original clip and exact CSV: 79 entries.
Stock stays 71 hardlinks plus the independent 77-byte sentinel copy. The plan
does not access those stock files; live source/content/NTFS guard checks remain
mandatory under admission. Retain the four model/surface dumps and one XAB under
`roundtrip/` with 64 KiB per-file caps before restoration. The native writer's
two fresh roots differ intentionally from the flat FF dump root.

## Independent reader and evidence limits

`read_rig_chain.py` imports the existing independent readers, never the writer.
It consumes whole bounded XMB/XSB records, obtains binds and blends from those
actual bytes, then supplies them to the four-key oracle. This prevents a good
source bundle from masking a damaged output. Native and FF data must agree on
decoded poses, topology, weights, names and note time. Pointer values and the
nonzero interned note ID may differ; neither whole-file hash equality nor a
timer notification substitutes for semantic verification.

The old strict XMB/XSB profile is not weakened for hypothetical FF changes. If
a real redump gains an alias, material-name variant or runtime field, the reader
must refuse it until observed bytes/source justify a separately reviewed profile.
Synthetic test dumps only test the FF reader; no actual model FF has run here.
The first authorized native writer outputs passed the complete model/surface read
and CPU oracle. That is native serialization/data evidence, not engine playback.
`native_execution_verified`, `ff_execution_verified`, material resolution,
restoration, runtime and ready flags remain false in data-reader output. The
outer runner binds all output hashes to successful phase receipts and
original-handle exit/job closure before recording an offline data pass.

## Implemented local executor; native GO still pending

No shared runner/provider patch was applied. The local runner reuses the pinned
BuildJob, Resource-Scheduler, Base transaction, ModelFF restoration, StockBinding
and bounded Beacon drain. `rig_phase.py` accepts only eight phase IDs with fixed
timeouts and an exact explicit environment. It launches literal argv within the
outer original job, drains two capped log streams and records a hash-bound phase
receipt. It owns no lease and never kills a PID. Local native wrapper functions
are exercised by mocks; their real implementation calls the pinned BuildJob and
the read-only original-job member observer.

Compiler artifacts stay under `build/`; all eight phase log directories are
fresh children of `logs/`. A bootstrap failure writes a fresh sibling
`<phase>.spec.launch-error.json`, bound to the spec SHA and original Python PID.
If `phase.json` is absent, the runner reports that original error and root exit
instead of replacing them with a file-not-found exception. Unbound error records
are retained but cannot supply accepted failure text; existing evidence is never
overwritten. A launch-error receipt never substitutes for job closure or success.

The compiler uses explicit include/library paths and `/X`; `CL`, `_CL_`,
`PYTHONPATH` and `PYTHONHOME` are absent from the child environment. Python roots
and readers use `-I -B`. Plan reads metadata only for compiler binaries, the
pinned source include tree, prepared headers, VC/SDK includes and x64 libraries.
After native admission, Run hashes and holds read guards on these files, records
NTFS identity/size/time/attributes, checks inventory membership before each native
phase and rechecks hashes before releasing the native reservation. The installed
SDK is neither downloaded nor copied. The observed current inventory has 5,442
files and 1,131,905,184 bytes; these are input bytes, not measured run output.

Compiler closure adapts the reviewed `b08fc1e` Material V2 contract locally; see
[closure-reference.json](closure-reference.json). A successful compile receipt
alone cannot authorize accepted telemetry cleanup. The runner must independently
observe `cl.exe` as a direct child of the exact original Python root, with a
stable creation identity. After the root exits zero, exactly one original-job
member may remain: the pinned `vctip.exe`, parented to that witnessed compiler
with consistent timestamps. Both binaries are rehashed, and only that original
job is stopped. A fresh root-exited/exit-zero/Active-zero sample is still required.
An unknown member, changed generation, missing witness, extra member or failed
hash refuses accepted closure. Failure cleanup still targets the original job.
No Material module is imported and no system-wide telemetry setting is changed.

Every phase captures the original handle identity before Resume, then uses the
existing bounded CIM registration helper. A failed Prepare is closure-unknown
even if no owner object returns. Unknown closure or failed source proof retains
guards, staging and the lease. Confirmed closure and source proof precede guard
disposal; the shared restoration helper checks stock before/after restoration
and releases the FF reservation only on success. A restoration refusal retains
the lease and failure receipt. Final output accounting includes hidden files and
the last serialized receipt, exempting only identity-verified staged hardlinks.
No runtime animation acceptance follows from any of these process checks.

Native proposals stay 4/6 GiB with a 32 MiB output cap; FF stays 8/11 GiB with a
64 MiB output cap, 2 MiB per log stream, 1 MiB FF and 64 KiB per redump. These
are proposed admission bounds, not measured rig-chain maxima or active leases.
No actor/GSC/animtree/game is launched by this adapter. Weight convention,
material binding, animation cadence, notetrack delivery and render stay open.

## Current source verification

The initial source checkpoint had 108 passing Python tests: the previous 93, thirteen phase
adapter tests and two Windows executor tests. The latter invoke four PowerShell
source/mock suites with 187 internal checks, covering compiler/telemetry refusal,
fresh closure sampling, actual phase orchestration, factory/Resume/registration/
budget/receipt failures, source/restoration gates, frozen inventory changes,
physical output-hash bindings and final serialized byte accounting. C# is parsed
with Roslyn only; no native helper assembly is compiled or loaded. The tests use
original synthetic geometry/clip bytes and did not prove native writer execution.
After the real failed attempt, focused correction checks passed: 15 Python phase
tests, 65 mocked phase-orchestration checks and 64 pure runner/parser checks.
The regression executes the real PowerShell phase function with a populated
compiler `build/` directory and a simulated child; logs remain independent.
Missing/bound/unbound bootstrap receipts are covered. Other unchanged suites
were not repeated for this correction.

A real read-only Plan rechecks existing providers, prepared source, compiler and
inputs; it creates no run directory and reads/copies no stock. Historical
plan-only evidence is retained in `chain-validation-2026-10-12.json`; current
source/mock/Plan evidence is in `runner-validation-2026-10-12.json`.
Run the complete light suite with the README command. Generate fresh recipe JSON
with the explicit paths/hashes listed by `plan_rig_chain.py --help`, and save it
outside the proposed run root. Changes to bound source require regeneration.

```powershell
pwsh -NoProfile -File tools-source/asset-bridge/animation/rig/Build-RigChain.ps1 -PlanPath $RecipePath -PlanSHA256 $RecipeHash
```

This command performs the default Plan only. Do not append `-Run` without the
coordinator's distinct execution GO following independent source review.

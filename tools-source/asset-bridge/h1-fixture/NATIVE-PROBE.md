# Prepared production-parser -> production-converter observation

**Compile B and a separately admitted Probe passed, with 111 native checks and
confirmed original-tree closure/lease release. Compile A remains Failed.**
The result covers extracted production methods with the declaration adapter;
it does not validate the full CLI, complete materials, FF, rendering or retail imports.
The existing full ZoneTool EXE has not been launched or changed. The original
H1 XMB/XSB fixture and its light checks are described in [README.md](README.md).

## Concrete route

`prepare_native.py` prepares one small C++ translation unit and includes from
the checked `fab935826c898806855376662a8a03317b3ad8f1` source, plus the exact
reviewed H1 surface correction. It does not change the shared source checkout.
It hashes 21 source files and fails on drift. The patch is applied in memory;
its target, hunk context/counts, patch hash and complete resulting source hash
must match. The local patch is an exact LF copy of the model owner's
`zonetool-fab9358-h1-xsurface.patch`, SHA-256
`e50c7f18b9e3b8904b441ddf10bb32a3315442d22afec7d174bda699f9db26a0`.

The observed native flow is:

1. Open the two original fixture files read-only while denying write/delete
   sharing, reject reparse paths and compare **all bytes** with the positive
   input embedded at preparation. Keep both handles until observation ends.
   Malformed-input Python tests are not fed into the permissive production
   C++ reader. This is not a general untrusted-asset importer.
2. Restrict the production filesystem search paths to the fixture root. Create
   the real `zone_memory` with a 1 MiB pool. Call exact production
   `h1::xmodel::parse` and `h1::xsurface::parse` bodies on the two files.
3. Inspect parsed fields, the material/LOD names and `tag_origin` retained by
   the production string-table methods. Leave its numeric token **zero**.
4. Pass the returned objects directly to the exact production
   `h1::converter::iw7::xmodel::convert` and patched
   `h1::converter::iw7::xsurface::convert`. Use the real allocator methods and
   ordinary-vertex/self-visibility codec, with no reactive-motion shortcut.
5. Check actual ABI offsets, counts, bounds, all 24 vertex field transfers,
   self-visibility against a literal oracle, triangle/rigid aliases, optional
   streams, bone-array aliasing and named references. Print one compact JSON
   result only after all observations succeed. No pointer addresses or machine
   paths are emitted. No dump, FF, material conversion, renderer or engine is
   called; allocator lifetimes encompass every observed alias.

## What is exact, and the one declaration adapter

The generated fragment manifest hashes each selection. Function bodies are
byte-identical to LF-normalized production source, or to the reviewed patched
surface source, including their original error paths:

- `h1::xmodel::{add_script_string,get_script_string,parse}`;
- `h1::parse_subdiv` and `h1::xsurface::parse`;
- both converter bodies, blend validator/packer and converter macros;
- full `filesystem.cpp` namespace body, the two referenced directory helpers,
  allocator methods, half-float and self-visibility codec namespaces.

The real H1/IW7 structs, `assetmanager::reader`, `zone_memory`, filesystem class
and allocator headers are included from the existing checkout. No SDK or
game files are copied. There is no Python-created C++ object standing in for
the production parser and no replacement reader, allocator or converter.

The asset class headers normally include `h1/zonetool.hpp`, which pulls hooks,
engine DB, command/scheduler integration, every asset and virtual interfaces.
The preparation therefore extracts the original fields and parse/string-method
signatures into **declaration-only class envelopes** without `asset_interface`
or the unrelated virtual methods. Their access is public in this envelope to
observe the real string table. The parser bodies are unchanged. This probes
those exact production methods and their real serialization/support routines;
it does not validate the original class vtable, full ZoneTool initialization,
stock DB fallback, command dispatch or whole-application linkage. Logging alone
is adapted to `fprintf(stderr, ...)`. Compile B and Probe below now verify this
bounded method/ABI route, not the omitted whole-application integration.

## String and material limits remain explicit

`tag_origin` is honestly resolved **as the string stored by the parser**, not
as a live engine script-string ID. No guessed ID is assigned. No `prepare`,
`SL_GetString`, `SL_ConvertToString` or IW7 dump call is included. A later dump
requires a separately reviewed real engine/string-table integration; this
probe intentionally cannot emit an IW7 XMB. A successful in-memory conversion
would not close that gap.

H1 `read_asset<Material>()` creates only the named reference. The probe reads
only its name, never uses the stub as a full Material, and does not call the
material converter. XModel conversion creates an IW7 name stub; its null
technique remains an explicit check. The converted LOD also remains a named
reference, not linked geometry. Complete material/technique/shaders, dependency
closure and recipient binding remain with their owners. A passing synthetic
probe would not establish retail-H1 import, FF loading or rendered appearance.

## Preparation and proposed admitted work

The following commands remain source preparation and Python tests only:

```powershell
python -B tools-source/asset-bridge/h1-fixture/test_native_preparation.py `
  --source-repo <existing-pinned-x64-zt-directory>
python -B tools-source/asset-bridge/h1-fixture/prepare_native.py `
  --source-repo <existing-pinned-x64-zt-directory> `
  --output <absolute-fresh-preparation-directory>
```

Generic unittest discovery does not supply `--source-repo`, so it skips only
the preparation class requiring the pinned checkout. The two `raw_bounded`
concurrency/replacement tests remain independent and run during discovery.
Use the explicit test command above to exercise preparation checks; an
explicitly supplied missing, invalid or changed source fails instead of
being skipped. Neither route compiles or executes native code.

Prepared source and receipts must stay below **1 MiB**. Output is create-only
and reparse ancestry is refused. `preparation.local.json` records source,
fragment and output hashes plus proposed compile arguments; it launches no
compiler. Revalidate that receipt, the source headers and original fixture
hashes immediately before a future admitted native run.

Use the same preparation command with `--verify` for a read-only preflight:
it regenerates the expected source in memory, checks every prepared source
byte and fragment/source hash, and still grants no execution authorization.

Review correction: `raw_bounded` no longer performs `stat` followed by an
unlimited `read_bytes`. It opens one unbuffered handle, requests at most
1 MiB + 1 byte, rejects excess length and checks regular-file identity/state
before and after reading against the current pathname. Tests perform a real
concurrent append after `fstat` (both oversized and within the cap), and a real
path replacement before open. An initial check exposed differing Windows
Python 3.12 `ctime` semantics in `lstat` and `fstat`; identity/birth/mtime are
compared across APIs and `ctime` within each API. This remains a cooperative
file guard, not protection against an attacker restoring every metadata field.

Proposed future budget, subject to the parent's plan/GO and live scheduler:

| Group | RAM / commit estimate | Bound |
| --- | --- | --- |
| One MSVC x64 compile + link | 4 GiB / 6 GiB | One compiler, no `/MP`, no PCH, 120 seconds; <=32 MiB new obj/EXE/logs |
| Separate probe execution | 0.25 GiB / 0.25 GiB | 1 MiB parser pool, two files/2,260 bytes, 15 seconds |

These estimates are **not measured peaks or current leases**. The current
reviewed scheduler/owned-job wrapper must own the whole active group, enforce
timeouts/output monitoring, observe closure and release admission. Preserve
all diagnostics if compile/link/assertions fail. Do not reduce estimates to
bypass a refused admission or invoke the planned commands directly. A full
ZoneTool rebuild, engine/game loading or donor extraction is not part of this
route; a coupling failure requires a revised source plan before expanding it.

No private PR is opened by this sub-lot; the coordinating branch owns its
integration, exact-head checks and merge.

## Prepared runner and immutable review plan

`plan_native.py` now produces a local JSON plan from the existing preparation,
fixture, source checkout, installed MSVC/SDK and reviewed provider directory.
It writes only the optional create-only `--output` plan, or prints to stdout.
It never creates the run directory, loads a native provider or acquires a lease.
The initial Plan C had 54 SHA-256/length bindings, including this runner,
its core, all 21 production inputs, all seven prepared files, the two fixture
files and the relevant providers/compiler anchors. System DLLs and the entire
installed SDK are **not** claimed to be a hermetic closure.

The runner reuses `IW7.AnimationProbe.NativeJob` from the existing witnessed
13,312-byte DLL, SHA-256
`5f613ebb83019dbf4bfa4f6a93c5329098343729b70acc2cfa70aa8b64f195f8`.
Its source is pinned to
`ddefa72ff2b98286cd585d1178c13e67dcd646bbcf39d51365660901366c5ca8`.
That initial runner introduced no new C# job or identity implementation. The shared
resource scheduler and its existing memory provider are pinned too; during a
future Run the scheduler can load its existing `ResourceMemory.cs` as usual.
That does not happen in Plan mode or in the light tests.

Review-only invocation (also the default without `-Run`):

```powershell
pwsh -NoProfile -File tools-source/asset-bridge/h1-fixture/Run-H1Native.ps1 `
  -PlanPath <absolute-local-plan.json> -PlanSHA256 <reviewed-sha256> -Stage Compile
```

After a separate coordinator GO, `-Run -Stage Compile` reserves 4/6 GiB for
one compiler/linker group and records closure before releasing that lease.
`-Run -Stage Probe` is a **separate fresh-host invocation**: it requires the
successful compile receipt bound to the same reviewed plan, checks/holds the
compiled executable hash, and requests a new 0.25/0.25 GiB Analysis lease.
There is no automatic transition, admission downgrade or direct unsupervised
fallback. The compiled executable and every reviewed file stay open with
write/delete sharing denied while relevant work runs.

Both stages use the original process/job handles, a BelowNormal process tree,
create-only logs, the original PID/creation/image tuple for scheduler
registration, a fresh monotonic deadline after telemetry, a combined 32 MiB
output cap (including temporary compiler outputs/logs/receipts), a 1 MiB final
metadata reserve and the scheduler's 85% commit high water. These are admission
estimates and monitored limits, not hard kernel memory/output quotas or measured
peaks. A synchronous filesystem/CIM operation may delay a deadline observation;
late completion is rejected. Cleanup allows five additional seconds and proves
original-root exit plus zero active job descendants before lease release.
Unknown ownership/closure or failed release retains the reservation and owner
context; no PID/name-based kill or lease deletion is used. The supervisor's
existing kill-on-close is a fallback, never substituted for observed closure.

Each stage publishes its receipt only after cleanup and a final output-size
check. Compile success is not probe success. A probe receipt may establish only
the extracted production-method observation above; it must keep full CLI,
engine token, complete material/LOD linking, FF/render and retail claims false.

At `f8ac21e`, `Test-H1Native.ps1` exercised 22 assertions with mocked providers:
normal and early closure, unavailable identity, deadline after slow telemetry,
partial Start failure, throwing owner factory, nonzero exit, failed closure,
failed release, guarded file mutation and receipt-size failure. `Test-H1Plan.ps1`
added nine assertions against Plan C, including immutable-plan, core,
provider and same-length source drift, lowered budgets and probe-before-compile
refusals. These are **source/lifecycle checks, not a new real Job witness**.
Those checks did not launch the H1 compiler or probe. The parent must review the
final plan hash and grant each relevant native stage separately. Compile A's GO
was consumed without a retry; Compile B and Probe subsequently received their
own separate explicit authorizations, documented below.

## One admitted compile attempt, 2026-10-12

Source `f8ac21e5ff473417345ad07be7eb6f8bddc068f6`, Plan C SHA-256
`a4564b25a7046568e28b26e6a22b3f84c10780b6478eed319c06bcd6182251f4`.
The coordinator reviewed that exact plan and authorized **one Compile invocation
only** with the complete 4/6 GiB reservation, 120-second deadline, 32 MiB output
budget and five-second cleanup. Current origin resource policy was fetched/read;
the registry and compiler-related process inventory were empty before launch.

The original `cl.exe` PID 32116 was created at `08:09:58.0787715Z`; the owned
stage started `08:09:58.0661405Z`. It registered against the shared Build lease
and generated the EXE/OBJ/PDB. The compiler's original exit code was **0**.
There were two existing production-reader `strcpy` deprecation warnings C4996,
with no compile/link error. While the owned tree remained open, `vctip.exe`
PID 22980 was observed with parent 32116, creation `08:09:59.470631Z` and the
same MSVC installation. Setting `VCTIP=0` did not prevent this observed child.
No claim of natural complete-tree closure or successful stage is made.

At the deadline the runner failed with `Stage deadline exceeded.`, requested
termination through the **original Job owner**, and confirmed its original
root was exited and the job empty. The final receipt at `08:11:58.3423038Z`
records `Status=Failed`, `ExitCode=0`, `TerminationRequested=true`,
`TreeClosureConfirmed=true`, `LeaseReleased=true`, `Quarantined=false`.
A subsequent fresh registry read showed zero leases; CIM showed none of the
original launcher/compiler/observed-child PIDs and no compiler/linker/VCTIP/
PDB-server/ZoneTool process matching the bounded inventory. No process was
stopped by guessed PID or name. All 54 bound input hashes/lengths still matched.

| Preserved output | Bytes | SHA-256 |
| --- | ---: | --- |
| `native_probe.exe` | 1,251,840 | `531787845faabfd20cd4597de10426be3ad710f0b1ffee89b11fcf2cd5a1f30d` |
| `native_probe.obj` | 3,585,662 | `500f9aa398f00bb89f759dd8b7d18c384bbeb4fe7f3f65512bfff1fe9710d7fc` |
| `native_probe.pdb` | 13,160,448 | `e082c8839162629daa9133be5b540f2b5abdad02c8050ebd2618fa30f16f34ad` |
| `stdout.log` | 1,265 | `0c4a6f654fc5df3d19342de044b419428746f68bb03a967e97a53634703d6439` |
| `stderr.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `receipt.json` | 1,005 | `8b3b1fa096358a5ac7b824c3bbfaec1e5e70cdf048e2197f0d1b2db0b77ed009` |

The six stage files total **18,000,220 bytes**, including the receipt. Memory
numbers remain admission estimates, not measured peaks. All outputs, the Plan C
and prepared sources remain local. The supplemental local observer's first
aggregate mistakenly used `Measure-Object` on ordered dictionaries and wrote
zero; observer B explicitly sums the recorded file sizes and preserves this
correction. The native runner receipt and file hashes were unchanged.

The retained local observer records the exact absolute launcher and argument
array for the one invocation (`Run-H1Native.ps1`, Plan C/hash, `-Stage Compile
-Run`), the compiler argument array, original child tuple, native receipt and
post-run checks. No retry, Stage Probe, game, full CLI, FF or render test followed.
The failed Compile receipt deliberately blocks Stage Probe. Its next action was
source review of compiler ancillary-process handling and a new plan/GO; do not
edit this receipt to promote the retained EXE into an accepted compile stage.

## Prepared correction: original compiler plus qualified telemetry closure

This revision was first source-tested after the failed attempt above; its
successful native qualification is recorded below. It does not reclassify the
failed attempt or implicitly grant further runs. It reuses the
MaterialV2/GSC qualified policy: compiler success is necessary, while residual
membership, identity and fresh post-stop closure need their own evidence.

The retained `NativeJob` public API supplies `TreeExited`, `StopAndConfirm` and
`CloseConfirmed`; its snapshot primitives/handles are private, and
`StopAndConfirm` closes them before an independent follow-up snapshot. The
existing MaterialV2 observer requires `BuildJob`/`IntPtr` and rejects this owner.
Consequently `H1Native.JobMembers.cs` adapts only the observer's owner/handle
binding to the pinned `NativeJob`/`SafeFileHandle`. Its bounded member and native
parent query body remains byte-identical to reviewed MaterialV2 source
`c8fce6094104eae70442a081654f403739f5315d531c35385021759b74c2abda`.
Borrowed job handles are protected with `DangerousAddRef`/`DangerousRelease`;
member handles request query-limited access. No launch, termination, assignment,
debug attachment or process-memory primitive is added to the C# observer.

`H1Native.Compiler.ps1` calls the pinned owner's existing private query/stop
methods with protected original handles. This reflection adapter is explicitly
bound to the existing DLL/source hashes and field/method shape; it is not a
general API compatibility claim. The reused MaterialV2 policy and member/time
validators are byte-bound to source
`fc024337fdb18c8a759cd6346ad90fe1fb2086d790e4804ade583c30e69d25d6`.

For Compile only, qualified cleanup requires all of the following:

1. A fresh original-handle root exit **0**, with the original PID/creation/image
   identity captured at launch. Here `cl.exe` itself is the original root;
   no wrapper receipt or guessed parent/compiler identity is substituted.
2. All reviewed inputs still match. EXE, OBJ and PDB are nonempty, within budget,
   hashed, tied to this Plan SHA and held with write/delete sharing denied.
   Both the compiler and sibling `vctip.exe` images are pinned/held too.
3. Two fresh complete native Job-member captures show exactly one identical
   `vctip` generation: expected image/hash, direct parent equal to the original
   compiler PID, plausible native creation time, no query/parent error and
   explicit membership in that original Job. Captures are retained before
   validation, including rejection evidence. Unknown or additional children fail.
4. Only then request the existing native `TerminateJobObject` primitive on the
   owner's protected original Job. No collected PID is a termination target.
   Obtain fresh original root0/Active0 **and** an empty native member capture;
   retain handles and resume normal supervision. The next ordinary poll must
   independently observe root0/Active0 before `CloseConfirmed` and lease release.
5. Recheck artifact hashes after closure. Publish Passed only through the normal
   final receipt gate. Any late/unknown/failed cleanup remains Failed/quarantined
   according to the existing lifecycle, and cannot enable Probe.

Plan schema v2 binds **59 inputs**: the original 54 plus the local compiler policy
adapter/observer, their two reviewed MaterialV2 source providers and `vctip.exe`.
The compiler is pinned to
`fe251ef50a1545b1b0835ee17b1e785459712b38d79e45b5c1d3d28970a36619`;
telemetry to
`d591358c6aee4b673562ca3b3a15c250e612708394fe3b44a7a7eda2470570a5`.
The ineffective `VCTIP=0` assignment is removed; no environment opt-out is used
as closure evidence. The existing budgets are unchanged. The 120-second stage
clock now begins immediately after admission, including observer setup; exhausted
setup time refuses process creation. Qualified cleanup gets at most five seconds
inside that original deadline. Failure cleanup still has its existing separate
five-second allowance and never turns a late result into success.

Pure verification: 69 policy assertions, 24 general lifecycle assertions,
12 read-only Plan assertions, 12 observer/source assertions (zero Roslyn semantic
errors, no Emit) and 12 PowerShell adapter assertions using mocked handles and
method objects. The ordinary wait loop is tested to perform a new zero-active
poll after the accepted stop; private-method calls and cached `Closed` alone
are never accepted as closure evidence. None of these checks loads/emits the
new native observer, acquires a lease, launches a compiler or retries the probe.
Those source checks alone did not prove actual adapter/native behavior. The
separately reviewed Compile B below now exercises the successful closure path;
the mocked fault cases are not reclassified as native fault-injection evidence.

## Compile B and separately admitted Probe: 2026-10-12

Both invocations used clean source `f20b1428d6d43e09e8b42b971a409171b5b0e963`
and Plan F SHA-256
`ce9d6d5805a4aa0b927a59002838d2203c9ef060ea5bb092040d4f8a360d76cf`.
Each had a separate central GO and fresh atomic admission. There was one
Compile B invocation, no retry, then one separately authorized Probe invocation
using its retained EXE. The 59 inputs matched before and after; no shared source
or fixture bytes changed. Both receipts report `Passed`, original exit 0,
`TreeClosureConfirmed=true`, `LeaseReleased=true`, `Quarantined=false`.

Compile B reserved 4/6 GiB and began its stage clock at `08:43:00.5823668Z`.
The original `cl.exe` PID 25332 was created at `08:43:00.6950598Z` and exited 0.
Two native captures at `08:43:03.2666302Z` and `08:43:03.3465747Z` independently
reported one identical member: pinned `vctip.exe` PID 32984, parent 25332,
creation `08:43:02.1503335Z`, `InOriginalJob=true`, no image/parent query error.
After the original-job stop, a fresh root0/Active0 snapshot was captured at
`08:43:03.3552283Z`, an empty member list at `08:43:03.3554510Z`, and the ordinary
supervision loop independently observed root0/Active0 at `08:43:03.3604539Z`.
Artifact acceptance took **2,850.3902 ms** from admission-stage start; cleanup
and receipt preparation finished `08:43:03.6377276Z`. No deadline extension or
PID/name kill was used. The two existing production `strcpy` C4996 warnings
remain in stdout; stderr is empty.

Compile receipt SHA-256:
`91ceb86a85601f65cc2942a4adbe08c3dc99681e9b0bacd29ea0fce8682ffdfa`.
Its EXE is 1,251,840 bytes, SHA-256
`7271eaf3f2069a4f92587e02b6caa1775983dcadcb1dbfb0fda7ee4753ea7e01`.
The six compile-stage files, including receipt, total **18,005,458 bytes**.

Probe used a new 256/256 MiB Analysis reservation with the unchanged 15-second
deadline. Its original PID 28164 was created at `08:46:37.6078022Z` and exited 0.
It completed before CIM registration: that failed registration is preserved as
`Original process differs from scheduler observation.`, and the explicit
`Original job already empty before CIM registration` branch required original
root/job closure. No missing/reused PID was adopted. Measured supervision elapsed
was 272.3284 ms; final observation acceptance was **291.3531 ms**. The stage
finished `08:46:38.0720612Z`, closed and released.

The real native stdout reports **111 successful checks**. Together with the
compiled static assertions, this proves the reviewed synthetic case covers:

- H1 `XModel` 680 bytes, `XModelSurfs` 56, `XSurface` 264, packed vertex 32 and
  rigid-list entry 16; IW7 `XModel` 736 and `XSurface` 256, plus selected offsets.
- Production parsing of the exact 932-byte XMB and 1,328-byte XSB, one bone/root,
  one LOD/surface, 24 vertices, 12 triangles and one rigid root group.
- Actual returned parser objects passed to the production converters; fresh
  model/group/vertex allocations, expected bounds/scale/counts, and observed
  bind-pose/bone-info/topology/rigid-list aliases within allocator lifetimes.
- Position, color, UV, normal and tangent transfer for all 24 vertices, literal
  self-visibility result `0x01FE0100`, expected part bits/counts and absent
  unsupported optional streams.
- Parser-retained string `tag_origin` with numeric token still **zero**; material
  name and LOD named reference observed, but technique and linked LOD geometry
  intentionally still absent. These last checks establish limits, not completeness.

Probe receipt SHA-256:
`40cc0a14320a517c97f12765354522a64d9f471d7f14a713408f05688b6df1c0`.
Stdout is 497 bytes, SHA-256
`97e82008b1f684f016a09c9f5e4bb1364440fddc8cbcb6511a9118b4da35b30b`;
stderr contains only the two parsing messages (101 bytes). Probe files total
2,815 bytes; the full Compile B + Probe run is **18,008,273 bytes**, below 32 MiB.
Memory values are reservations, not measured peaks.

Fresh post-run process/registry observations found no remaining owned probe,
compiler/telemetry/heavy process and no lease. Main retained PID 27784, creation
`2026-10-12T00:52:28.7133740Z` and image SHA-256
`408ecfaef8e3584769736878858ed225c4648249433e91caff3ad8c5c7efb9a7`.
Local observer manifests retain absolute commands, full receipts and hashes;
the sanitized checkpoint is [native-observation-2026-10-12.json](native-observation-2026-10-12.json).

Full CLI/class-vtable integration, engine script-string resolution, complete
material/technique/shaders, linked LOD dependencies, dump/FF, recipient loading,
rendered appearance and retail-H1 compatibility remain unverified. The source-only
contract/validation JSONs remain dated preparation evidence. No existing Failed
receipt or acceptance boundary was rewritten. A next export/integration step
requires a distinct source plan and authorization; this witness grants none.

The separate [DUMP-PROBE.md](DUMP-PROBE.md) now supplies that next
profile and an independent reader. Its fixture-only string bridge leaves token
0 unresolved. The prepared B bytes and receipts are preserved. One separately
authorized Compile and another separately authorized 149-check Probe passed
under the dump Plan. The two actual IW7 dumps passed independent readback with
hashes matched to that Probe receipt. FF/material/engine-token/render boundaries
remain open; the original 111-check B witness above is unchanged.

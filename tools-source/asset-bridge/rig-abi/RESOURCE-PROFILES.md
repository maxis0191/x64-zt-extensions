# Distinct fixture and retail resource estimates

The Python/CDB protocol fixture and a retail ZoneTool observation execute
different workloads. Both remain subject to independent source review and a
separate coordinator GO. Neither estimate is a measured peak or a memory cap.

| Scenario | Physical / commit estimate | Included workload |
| --- | --- | --- |
| `iw7.rig-watch-python-cdb-fixture/1` | **4 / 6 GiB** | PowerShell controller/helpers, Python transport, CDB and its Python fixture |
| Future retail observation | **10 / 14 GiB**, unchanged | Existing rig FF envelope 8/11 plus debugger envelope 2/3 |

The fixture estimate is fixed in its v4 Plan and fixture-only transaction. It
is not a choice between resource presets. The input schema refuses retail mode,
unknown profile identifiers, budget fields, replacement target fields and old
v1/v2 schemas. The concrete transport still constructs only the fixed Python
fixture command and independently rejects retail mode. There is no retail
adapter or compatibility claim for the 4/6 profile.

## Component accounting from the source

The proposed 4/6 envelope is the sum of two conservative estimates:

| Component envelope | Physical / commit | Source basis and contents |
| --- | --- | --- |
| Debugger | 2 / 3 GiB | Reuses the documented debugger allowance in `docs/DEBUGGER.md`: CDB, DbgEng, DbgHelp, runtime libraries, command handling and diagnostic overhead. It is an existing planning allowance, not a CDB benchmark. |
| Controller and synthetic target | 2 / 3 GiB | The PowerShell/.NET host, compilation and loading of the small BuildJob/member/deadline/memory helpers, pinned file hashing and guards, one Python transport and one Python target, their standard libraries, three pipe workers, protocol parsing and retained evidence. |

`Run-WatchFixture.ps1` creates a suspended Python transport in the original
BuildJob. `cdb_transport.py` creates CDB; CDB starts the fixed `debug_fixture.py`
using the same pinned Python executable. Before continuation the original job
must contain exactly root Python, CDB and target Python, with checked identities.
The controller remains outside that job and is included in the estimate.

The target allocates a 256-byte surface, 56-byte model-surfs record and a short
name. These are application records, not an estimate of Python's total memory.
The transport has 64 queued pipe chunks of at most 4096 bytes, four queued
commands of at most 8192 bytes, and a combined 256 KiB raw stream cap. The whole
new output directory is bounded to 1 MiB and 32 files. Parser copies, Python
objects, thread stacks, runtime/JIT/compiler allocations and file-cache effects
remain part of the larger controller envelope; byte caps on records and files
are not process-memory caps.

No ZoneTool executable, retail image, FF, stock transaction, game/client/server,
matched retail PDB, source extraction, native build toolchain or hardware GPU
workload is part of this fixture. CDB receives `-sins`, an initially empty local
symbol directory, `-netsyms:no`, `-noshell` and only the newly created/held Python
target described by the [owned-creation Plan](OWNED-CREATION-PLAN.md). The
transport removes inherited symbol/source/extension path variables. This is the
intended symbol-free recipe, not yet a live qualification of CDB's behavior or
its internal allocations. The admitted helper `Add-Type` compilation is included
in the controller envelope; no ZoneTool/MSBuild build is requested.

## Unknown peaks and future evidence

The 2/3 controller envelope is a conservative planning estimate. Trials A/B
failed before arm and did not measure process/group peaks. The v4 owned-creation
candidate has not run. Startup peaks, debugger/plugin/runtime allocation, .NET/JIT
and Python library costs, working-set residency and transient commit growth are
unmeasured. The Plan and transaction explicitly retain `MeasuredPeaks=false` or
`MeasuredResourcePeaks=false`; success of source simulations cannot change this.

At a future separately approved qualification, retain time-stamped memory
observations covering controller/helper setup, child startup, stopped/armed
state, continuation, capture and closure. Include the controller and all three
identity-checked job members; report their working sets and private bytes plus
system available RAM, committed bytes and commit limit. Preserve observed
high-water values, sampling interval, missed phases and unavailable identities.
Distinguish system pressure from attribution to this group. Sampled observations
can miss transients and do not establish a guaranteed maximum. The present
runner checks global commit pressure but does not collect these per-process peak
series; qualification must explicitly report that measurement gap if no reviewed
observer accompanies the run. It must not call this estimate measured or revise
it from one favorable sample.

## Unchanged admission and closure gates

The fixed complete 4/6 fixture group must be atomically acquired before staging
or helper compilation. Use the current account-wide scheduler, zero RAM reserve,
20% commit reserve with a minimum 4 GiB, and the existing 85% commit-pressure
stop check. No competing heavy group is admitted. Source/tool guards, positive
original-job membership, 240-second overall observation, at most 10 seconds
after stopped confirmation before continuation/capture, at most 30 seconds
cleanup within start+270 seconds, original root exit and Active0, restoration,
and ownership-bound release/quarantine are unchanged.

The older 10/14 fixture Plan and refused preflights remain historical evidence.
Their numbers came from applying the README retail sum (rig FF 8/11 + debugger
2/3) to the smaller synthetic fixture. This correction follows the actual source
workload, not a currently observed resource deficit. The future retail 10/14
estimate is preserved. Old Plans are not rewritten or silently executed with the
new profile. A new source-bound v4 Plan, independent review and separate GO are
required. This source change requests no resource preflight or native execution.

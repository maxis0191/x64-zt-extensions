# Original-job supervision — source preparation

The original `model/BuildJob.cs` remains unmodified, SHA256
`f6be2a4cafddb78b5e07a6802354575ada418cb7643d96a3abd0a4c063bc6387`.
The new `Watchpoint.Core.ps1` keeps a single 240 s monotonic observation budget
from before admission/staging, tightens it to 10 s before authorizing the one
armed continuation, and permits at most 30 s cleanup, bounded by start+270 s.
Time is checked after slow getters, callbacks and persistence, before acceptance.
Forced closure records the original exit code and never claims FF success.

`WatchpointDeadline.cs` borrows that same owner and invokes its `Stop()` from a
dedicated managed thread. It creates no native job, attaches to no PID and uses
no P/Invoke. Arm it before Resume; tighten before sending CDB `g`. It can request
termination while the PowerShell controller is busy. OS scheduling and native
Stop completion are not real-time guarantees: observed timing and failures must
be retained. Root exit plus Active0 and timely cleanup remain required.
Its close method refuses to disarm over a live job or a pending Stop call.

The pure core's hooks are implemented by the concrete runner/transport, not by
untrusted serialized scriptblocks. They acquire the complete 10/14 GiB group,
hold source pins, stage/restore the reviewed files, create the root in BuildJob,
bind its original-handle identity, register it, read nonblocking transport state,
authorize exactly one continuation, seal the bounded witness, save, and release.
Factory ambiguity, incomplete closure, source drift or failed restoration retains
ownership/guards and the lease for recovery. A release that returned successfully
but exceeded time is recorded as released with failed diagnostic acceptance.

The transport contract is `Loading -> ArmedStopped -> Running -> CaptureStopped`.
ArmedStopped requires actual stopped identity and breakpoint confirmation;
CaptureStopped requires a matching nonce and sealed independently parsed log.
EOF, failed drains, output overflow, refusal and unsolicited continuation fail.
Debugger stop recovery uses original-job termination and does not depend on a
responsive stdin, Ctrl+C broadcast, or a guessed descendant PID.

`Test-Watchpoint.ps1` exercises 19 simulated transactions, including slow exit
getters/saves/seals/releases, factory errors, stop failures, EOF and quarantine.
It does not load the new C# type or run CDB, Python fixture, game or Win32 owner.
The deadline thread is source-reviewed only, uncompiled and unqualified here.
Concrete transport is now provided below. Actual fixture qualification remains
required before any retail GO and is not authorized by these source artifacts.

## Concrete qualification recipe

`Run-WatchFixture.ps1` defaults to Plan. It validates the small spec, local paths
and exact pinned provider sources, then returns without loading a native helper,
taking admission, creating the future run root or launching anything. `-Run`
exists for a future explicit coordinator GO. It reserves the complete 10/14 GiB
group, guards source and tool files, loads the existing BuildJob and member
observer plus the new deadline helper, and starts the Python transport as the
suspended original root. It does not create or copy retail stock or a PDB.

The concrete chain is original BuildJob -> Python transport -> CDB -> Python
fixture. The fixture allocates 256/56-byte fake records and the allowlisted name,
writes a bounded manifest containing its exact process creation FILETIME, then
calls DebugBreak. After one approved continuation it performs a single known
eight-byte store of the name address at surface+0x58 and waits for owned closure.
This qualifies neither a retail loader nor the meaning of a GPU field.

`cdb_transport.py` launches CDB with a fixed argument list, no shell, no attach
flags, explicit startup script, local empty symbol path and network symbols
disabled. Separate daemon workers read stdout/stderr and write stdin; bounded
queues make every controller poll and command enqueue nonblocking. A blocked
worker cannot extend the independent owner deadline. EOF, process exit, failed
drain/write, queue overflow or the combined 256 KiB stream cap fails the phase.
The total output root is capped at 1 MiB/32 files. UTF-8 protocol decoding is
strict; an unexpected encoding is a refusal, not silently repaired evidence.

The fixture-only startup sequence verifies an empty breakpoint table, continues
to the deliberate DebugBreak, reads PID/RIP/eight code bytes through CDB, then
generates the same guarded capture fragments using a separate fixture schema.
No fabricated ZoneTool or FF hash is used. ArmedStopped requires `BP_PRESENT`
and a following debugger prompt. The PowerShell controller independently checks
that all three processes are positive members of the original job, with exact
images, matching target creation FILETIME and a distinct target PID. Only then
does it tighten the deadline and publish one atomic `continue-once` request.
The first write plus STOP/prompt is parsed and saved as a bounded sealed witness.
The exact original job is stopped even if CDB is parked at a prompt. Pipe errors
and partial raw output are retained; no attempt is made to attach or kill by name.

All files are new diagnostic outputs. For this fixture, restoration means guarded
sources unchanged and original job closed, followed by releasing the guards;
there is no pre-existing stock/profile mutation to roll back. Evidence remains.
Do not interpret this fixture-specific restoration as a tested retail staging
transaction. A future retail adapter must use the already reviewed rig stock
transaction and its own locator binding, and is currently absent.

## Future GO input and current verification

The private spec schema is `iw7.rig-watch-fixture-plan/1` with fields `Mode`
(`fixture` only), `Nonce` (32 lowercase hex), `RunRoot` (fresh below this checkout's
runtime), `ProviderRoot`, `PythonExe`, `PythonSHA256`, and `CdbExe`. It contains
paths/pins only, never serialized callbacks or arbitrary debugger commands.
The runner takes `-SpecPath` and `-SpecSHA256`; **omit `-Run` for Plan**.
The provider root must include the current source-bound rig member observer.
There is no game, client, Main, locator address, build toolchain or installation
in this qualification recipe. Keep the 10/14 estimate; no admission was measured.

Current verification is 42 Python source tests (20 capture/identity, 22 concrete
protocol/pipe simulations), 19 PowerShell transaction simulations, 12 worker-state
refusals and PowerShell
AST parsing. A real default Plan against the retained sources returned
NativeExecuted=false, NativeTypesLoaded=false, LeaseAcquired=false, Ready=false,
and did not create its future run directory. The first Plan exposed hidden
WindowsApps ancestry needing `Get-Item -Force`; this read-only path check was
corrected and the Plan passed. No CDB, DebugBreak fixture, new C# compilation,
hardware watchpoint, native job or resource measurement was exercised.

Review found that a worker `BaseException`, or an exception whose `__str__`
raises, could previously end a drain without setting the failure signal. Workers
now catch `BaseException`, signal failure before assigning a bounded fixed reason
that never formats the exception, and publish explicit termination in `finally`.
The controller rejects any worker termination, rechecks health around protocol
processing/publication, and exports all three worker states. The PowerShell
consumer independently rejects missing, ended or non-running workers. Regressions
include valid stdout combined with a failed stderr worker, writer failures at
queue/read/write/flush boundaries, hostile formatting, and a failed error handler.
The prior Plan is preserved unchanged pending the complete independent verdict;
its old source bindings do not describe this corrective revision.

Source corrections include the documented `r $t0` destination syntax and the
positive `$bp3` acknowledgement. Actual command quoting, console/pipe behavior,
network-symbol suppression, child job inheritance, the deadline thread and
capture/closure under a debugger stop remain the purpose of the future fixture
GO, not established results. See Microsoft's
[CDB command-line reference](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/cdb-command-line-options)
and [pseudo-register reference](https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/pseudo-register-syntax).

# Original-job supervision — source preparation

Current creation protocol: [owned suspended fixture Plan](OWNED-CREATION-PLAN.md).
Trials A/B remain immutable; B established target nonmembership without proving
its cause. The new v4 source candidate has not run natively.

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
untrusted serialized scriptblocks. They acquire the complete fixed fixture
4/6 GiB group (see [resource profiles](RESOURCE-PROFILES.md)),
hold source pins, stage/restore the reviewed files, create the root in BuildJob,
bind its original-handle identity, register it, read nonblocking transport state,
authorize exactly one continuation, seal the bounded witness, save, and release.
Factory ambiguity, incomplete closure, source drift or failed restoration retains
ownership/guards and the lease for recovery. A release that returned successfully
but exceeded time is recorded as released with failed diagnostic acceptance.

The transport contract is `TargetCreatedStopped -> Loading -> AttachedStopped ->
Loading -> ArmedStopped -> Running -> CaptureStopped`. The first gate proves
two original-job members before attachment; the second proves three before
resuming the retained primary thread and sending fixture startup `g`.
ArmedStopped requires actual stopped identity and breakpoint confirmation;
CaptureStopped requires a matching nonce and sealed independently parsed log.
EOF, failed drains, output overflow, refusal and unsolicited continuation fail.
Debugger stop recovery uses original-job termination and does not depend on a
responsive stdin, Ctrl+C broadcast, or a guessed descendant PID.

`Test-Watchpoint.ps1` exercises 29 simulated transactions, including slow exit
getters/saves/seals/releases, factory errors, stop failures, EOF and quarantine.
Four boundary cases cover a stopped confirmation with five milliseconds left,
confirmation exactly at the global deadline, an expired checkpoint between
tightening and continuation, and a continuation callback returning too late.
The ten-second interval begins after the stopped identity/breakpoint confirmation;
before that, the original 240-second deadline remains in force. Tightening uses
the earlier deadline, and does not add ten seconds to the remaining global budget.
It does not load the new C# type or run CDB, Python fixture, game or Win32 owner.
The deadline helper compiled and requested cleanup Stop in trials A/B. Its
independent timeout behavior during a stalled controller remains unqualified.
Concrete transport is now provided below. Actual fixture qualification remains
required before any retail GO and is not authorized by these source artifacts.

## Concrete qualification recipe

`Run-WatchFixture.ps1` defaults to Plan. It validates the small spec, local paths
and exact pinned provider sources, then returns without loading a native helper,
taking admission, creating the future run root or launching anything. `-Run`
exists for a future explicit coordinator GO. It reserves the complete fixture 4/6 GiB
group, guards source and tool files, loads the existing BuildJob and member
observer plus the new deadline helper, and starts the Python transport as the
suspended original root. It does not create or copy retail stock or a PDB.

The original BuildJob owns Python transport and its two children: a directly
created suspended Python fixture and CDB attaching only to that new held target.
The fixture allocates 256/56-byte fake records and the allowlisted name,
writes a bounded manifest containing its exact process creation FILETIME, then
calls DebugBreak. After one approved continuation it performs a single known
eight-byte store of the name address at surface+0x58 and waits for owned closure.
This qualifies neither a retail loader nor the meaning of a GPU field.

`cdb_transport.py` launches CDB with a fixed argument list, no shell, an attach
PID derived only from its new retained creation handles, an explicit startup
script, local empty symbol path and network symbols disabled. Existing/retail
PIDs are unavailable. Separate daemon workers read stdout/stderr and write stdin; bounded
queues make every controller poll and command enqueue nonblocking. A blocked
worker cannot extend the independent owner deadline. EOF, process exit, failed
drain/write, queue overflow or the combined 256 KiB stream cap fails the phase.
The total output root is capped at 1 MiB/32 files. UTF-8 protocol decoding is
strict; an unexpected encoding is a refusal, not silently repaired evidence.

The fixture-only startup sequence first proves original two/three-member ownership
as detailed in the creation Plan. At the initial attach prompt it removes the
temporary DLL stop filter, verifies an empty breakpoint table, binds the stopped
PID, and awaits owner authorization. It resumes the original primary handle
exactly once, continues to deliberate DebugBreak, reads PID/RIP/eight code bytes through CDB, then
generates the same guarded capture fragments using a separate fixture schema.
No fabricated ZoneTool or FF hash is used. ArmedStopped requires `BP_PRESENT`
and a following debugger prompt. The PowerShell controller independently checks
that all three processes are positive members of the original job, with exact
images, matching target creation FILETIME and a distinct target PID. Only then
does it tighten the deadline and publish one atomic `continue-once` request.
The first write plus STOP/prompt is parsed and saved as a bounded sealed witness.
The exact original job is stopped even if CDB is parked at a prompt. Pipe errors
and partial raw output are retained; no attempt is made to attach or kill by name.
On a transport failure, the directly created target can also be stopped through
its retained creation handle. `OriginalJobClosed` alone does not imply complete
closure: unproven descendant membership retains the lease in quarantine.

All files are new diagnostic outputs. For this fixture, restoration means guarded
sources unchanged and original job closed, followed by releasing the guards;
there is no pre-existing stock/profile mutation to roll back. Evidence remains.
Do not interpret this fixture-specific restoration as a tested retail staging
transaction. A future retail adapter must use the already reviewed rig stock
transaction and its own locator binding, and is currently absent.

## Future GO input and current verification

The private spec schema is `iw7.rig-watch-fixture-plan/4` with fields `Mode`
(`fixture` only), `ResourceProfile` (`iw7.rig-watch-python-cdb-fixture/1` only),
`Nonce` (32 lowercase hex), `RunRoot` (fresh below this checkout's
runtime), `ProviderRoot`, `PythonExe`, `PythonSHA256`, `CdbExe`, and `SourceBindings`. It contains
paths/pins and the fixed fixture identity only, never serialized callbacks,
arbitrary debugger commands, budget values or alternative target paths. Unknown
fields are refused. The Plan returns `iw7.rig-watch-fixture-source-plan/4`.
The runner takes `-SpecPath` and `-SpecSHA256`; **omit `-Run` for Plan**.
The provider root must include the current source-bound rig member observer.
`SourceBindings` binds exactly eight reviewed basename-to-SHA256 pairs:
`Run-WatchFixture.ps1`, `Watchpoint.Core.ps1`, `WatchpointDeadline.cs`, `capture.py`,
`cdb_transport.py`, `debug_fixture.py`, `owned_fixture.py`, and `fixture-providers.json`. The hashes
must come from the reviewed revision and are part of the immutable SpecSHA256.
Plan and Run compare them before any provider import or Add-Type. Run additionally
holds read-only file guards from that comparison through transaction cleanup,
closing the edit window before imports; it never blesses current local hashes as
new approval. The old v1/v2/v3 specs are refused and their Plans are preserved for the
review record, not upgraded or executed automatically.
There is no game, client, Main, locator address, build toolchain or installation
in this qualification recipe. The earlier 10/14 fixture estimate inherited the
retail rig envelope by mistake. The new fixed 4/6 component estimate is separate,
unmeasured and subject to review; retail remains 10/14. Old preflight refusals
remain intact. No new resource preflight or native execution follows this change.

Current verification is 69 Python source tests (20 capture/identity, 28 concrete
protocol/pipe simulations, 11 job/error diagnostic simulations, 10 fake creation-handle
cases), 29 PowerShell transaction simulations, 23 membership refusals plus valid
two/three-member cases, 12 worker-state refusals, four pre-admission mode/budget
refusals and PowerShell AST parsing. Earlier default Plans returned
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
The prior Plan is preserved unchanged in the independent review history;
its old source bindings do not describe this corrective revision.

The second review finding was that the previous runner recalculated its seven
local hashes without comparing them with reviewed input, so an unchanged
SpecSHA256 could accept edits between Plan and Run. Spec v2 fixed that binding;
v3 retained it and distinguished the fixed fixture resource profile. v4 adds the
owned-creation source and preserves the same fixed resource profile.
`Test-WatchSourceBindings.ps1` invokes only extracted pure source/path validators:
each of eight synthetic source mutations is refused with an unchanged spec hash,
incomplete maps fail, all imports follow binding, and held guards reject a later
edit. It also verifies the fixed 4/6 Plan envelope and nine old-schema, retail,
foreign-profile and arbitrary-budget/target refusals. This profile change needs
a new v4 source Plan and independent review before a separate future GO.

Source corrections include the documented `r $t0` destination syntax and the
positive `$bp3` acknowledgement. Actual command quoting, console/pipe behavior,
network-symbol suppression, child job inheritance, the deadline thread and
capture/closure under a debugger stop remain the purpose of the future fixture
GO, not established results. See Microsoft's
[CDB command-line reference](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/cdb-command-line-options)
and [pseudo-register reference](https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/pseudo-register-syntax).

The [first admitted fixture](CDB-FIXTURE-2026-10-12-A.md) subsequently refused at
its ambiguous job guard, then closed/restored and released its lease. It did not
reach arm or capture. The [next diagnostic source Plan](CDB-DIAGNOSTIC-PLAN.md)
keeps the guard, separates API/member/last-error evidence, and preserves the
bound initial failure through the transport and PowerShell state. Four pure
PowerShell envelope checks cover that reporting and reject foreign identities.
No second native attempt accompanies this diagnostic source change.

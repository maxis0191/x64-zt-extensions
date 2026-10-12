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
Concrete transport and fixture qualification remain required before native GO;
the retail mode additionally requires locator/mapping/stopped-identity bindings.

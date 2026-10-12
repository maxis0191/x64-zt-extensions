# Native runner failure-path corrections, 2026-10-12

Independent review of `42b5d27` accepted the historical 281-byte XAB/readback
evidence and identified two defects in the runner. This source correction does
not replace or rewrite `native-validation-2026-10-12.json`, its raw receipts or
the writer/ABI sources. The successful run remains bound to its earlier runner
hash. The corrected native helper has **not been compiled or executed**.

## P1: own and confirm the complete process tree

The earlier `.Kill()` ended only the root process. A surviving `c1xx.exe` or
other descendant could retain redirected pipe writers and block `ReadToEndAsync`.
The shared scheduler's name checks alone could not prove that tree empty.

`Probe-NativeJob.cs` now owns one unnamed, noninheritable Windows Job Object for
each compiler/writer/reader invocation. It requests kill-on-close and BelowNormal
priority, without either breakaway permission. Windows SDK 10.0.26100.0
`WinBase.h` defines `ProcThreadAttributeJobList=13`, used through
`PROC_THREAD_ATTRIBUTE_JOB_LIST` in `STARTUPINFOEX`. Job membership is requested
atomically in `CreateProcessW`; a suspended primary thread permits original
handle/creation/image/priority checks before resuming. Unsupported job assignment
fails closed; there is no ordinary launch fallback. This requires Windows 10+.

The inherited-handle list contains only stdin NUL and the two create-only log
files. The executable is hash-checked through a retained read guard. No async
pipe reader or PID/name-based termination remains. Normal completion requires
both the original root handle signaled and job accounting `ActiveProcesses=0`.
Failure invokes `TerminateJobObject` on that exact owner, then polls the same
conditions for at most five seconds per cleanup attempt. The outer finalizer
can retry once; it retains the reservation if any owner remains unresolved.
Kill-on-close also covers abrupt loss of the launcher, while the Build lease
remains quarantined for later inspection. No lease is deleted or bypassed.

`Close-ProbeReservation` invokes the existing shared `Exit-IW7ResourceLease`
only after every retained owner confirms closure. Thus a missing/failed native
accounting query cannot fall back to the shared process-name scan. Another
chat's processes are never added to, enumerated for killing by, or terminated
through these unnamed job handles.

The API design follows Microsoft's [Job Objects documentation](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects),
[CreateProcessW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw),
[process/thread attributes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute)
and [job accounting](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information),
plus the installed SDK definitions. These references are not execution evidence.

## P2: include final receipts in the 32 MiB cap

The old runner checked before writing `native-receipt.json` and
`resource-after.json`. It now reserves 1 MiB for their combined encoded UTF8
bytes, leaving 31 MiB for native output and logs. After owned tree closure and
lease handling, it serializes both receipts in memory and rejects oversized
metadata before writing either file. Writes use CreateNew.

The native receipt is first written under a `.pending.json` name. Both complete
receipts and every other output file must pass the final 32 MiB count before
renaming that pending receipt to its published name. The rename adds no bytes;
a final recount precedes the success message. An oversized payload, metadata or
late-growing directory cannot pass the publication check. Logs are polled while
the process runs: this is a stop/reject limit, not an OS disk quota preventing
every transient overshoot. An over-budget failed run is preserved for diagnosis
and cannot be described as a successful capped run.

## Validation performed and next admitted witness

```powershell
pwsh -NoProfile -File tools-source/asset-bridge/animation/Test-NativeProbeSource.ps1
python -B -m unittest discover -s tools-source/asset-bridge/animation -v
```

The source test runs only AST-extracted pure PowerShell functions, tiny temporary
files and mocked resource owners. It parses C# with the already-installed Roslyn
syntax parser, without Add-Type, compilation/Emit, native calls or a reservation.
28 checks passed: PS/C# syntax and source constraints, empty/exact/oversized
payloads, both receipts in the final total, UTF8 metadata overflow, late file
growth before publication, normal closure, failed cleanup, cleanup returning
without proof, and recovery which explicitly confirms closure. The 39 existing
Python tests still cover the unchanged clip/preflight paths.

These tests do not establish native job ABI, successful launch or actual process
tree termination. Under a separately authorized heavy slot, first compile the
helper and use a tiny purpose-built parent/child/grandchild fixture to verify:
root exit with a surviving child does not complete the job; timeout kills all
owned descendants; unrelated witness processes survive; suspended-start failure
leaves no executable running; forced launcher exit triggers kill-on-close; and
an unconfirmed native closure preserves its lease. Then validate file-backed
diagnostics and the normal writer path. Preserve original handles/identities,
logs and final directory accounting. No part of that next witness ran here.

The [prepared native witness command](NATIVE-JOB-WITNESS.md) now provides the
normal/root-exit/kill-on-close tree cases, foreign witness and final accounting
without rebuilding the original writer. It remains unexecuted. The lightweight
suite is now 32 checks after adding both fixture scripts' syntax and admission
ordering checks. The helper's hash encoding uses BitConverter for PowerShell
7.0 / .NET Core 3.1 compatibility; this does not expand the native evidence.

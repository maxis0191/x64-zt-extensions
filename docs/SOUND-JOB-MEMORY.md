# Sound phase JobObject commit peaks

This source change adds telemetry to the existing sound supervisor. It does not
change the 8 GiB physical / 11 GiB commit admission, memory margins, deadlines,
candidate C, closed attempts A/B or retained runtime plans. No real peak has yet
been captured with this implementation.

## Counter and capture point

Microsoft documents `JobObjectExtendedLimitInformation` as information class 9
for [QueryInformationJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-queryinformationjobobject).
The existing `BuildJob.ExtendedLimits` layout already contains the corresponding
[`PeakJobMemoryUsed`](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information)
field. Windows tracks this job memory high-water counter continuously; no memory
limit flag needs to be enabled for this read. This is committed job memory, not
working set, output-file size or a single process's private-memory snapshot.

`BuildJob.PeakJobCommitBytes` queries class 9 on the original owned job handle,
requires API success and the exact returned structure length, then preserves the
unsigned byte value. A zero/disposed handle throws before the query: passing NULL
to Windows could select the calling process's job instead. Existing job flags,
process creation and ownership operations are unchanged.

`SoundFF.Core.ps1` reads the counter once before disposing each phase's job. On
success this follows the existing closed-job wait. On error it follows the
existing cleanup/stop attempt, including a stop exception, while the handle is
still available. Values are kept in the transaction state before `Dispose` and
persisted by its existing state/final-state writes. A failed factory that returns
no owner cannot be queried. A disposal failure does not trigger a second query.

## Receipt scope

`state.local.json.JobMemory.Phases` records one row per attempted phase:

- `Phase`, `PeakJobCommitBytes`, `Status`, `JobClosedAtQuery` and `Error`.
- `Captured` means an unsigned counter was returned; zero is preserved as zero.
- `Unavailable` leaves the value null and records a bounded error. It does not
  replace the original phase failure or change its ownership/cleanup decision.
- `NotQueried` means no query occurred, including an unreturned factory owner.
- `JobClosedAtQuery=false` means an observation before confirmed closure, not a
  final peak. Such a value cannot establish completed-phase coverage.

`MaxObservedPhaseJobCommitBytes` is the maximum of captured phase values, never
their sum. Missing phases, failed queries and unconfirmed closure remain visible;
this aggregate is not a claim that all planned phases completed or were measured.

Each job covers its phase worker and attached descendants. The PowerShell
supervisor is outside those jobs, so `SupervisorIncluded=false`,
`SupervisorPeakCommitBytes=null` and `TransactionPeakCovered=false`. No exact
supervisor peak counter is supplied by this change. The existing global commit
pressure snapshot is not a substitute. These records alone cannot establish a
smaller whole-transaction reservation.

## Validation and next use

`test_sound_job_memory.ps1` exercises the actual phase/cleanup functions with
synthetic unsigned counters and mock owners. Cases cover zero, unavailable or
invalid values, original errors, stop/dispose failures, a missing owner, capture
ordering and an exact maximum above the floating-point integer precision limit.
Its `-InteropOnly` mode compiles the C# source as a managed assembly, checks x64
structure sizes/offset and the zero-handle rejection, and calls no kernel query.
These checks are not native workload execution or real memory measurements.

Source validation on 2026-10-12 passed: the 12 mock memory-flow cases and five
managed interop checks above; existing transaction suites (21 StandardMod,
12 DumpOnly and 14 legacy cases); and 11 deadline cases. The six Python helper
source tests and the PowerShell binding check for all 16 text helpers also
passed. Only the `BuildJob.cs` canonical source digest was changed in
`sab_ff_helpers.json`; the other 15 entries and all retained runtime plans remain
unchanged. No native build, Run, admission, new resource preflight or retained
payload read was part of this validation.

A future admitted execution must bind the changed sources in a newly reviewed
plan and retain all phase records plus normal closure evidence. Historical plans
and receipts stay immutable; their old source pins are not silently refreshed.
Budget changes, if ever justified by complete measured scope and margin, require
a separate review. This implementation does not authorize a Run.

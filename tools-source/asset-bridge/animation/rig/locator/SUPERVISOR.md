# Locator supervisor: bounded static analysis

`Run-Locator.ps1 -PlanPath <absolute-json> -PlanSHA256 <digest>` defaults to
Plan. It verifies its source, Python and fixed provider pins, lists runtime and
reference metadata, and prints the exact command. Plan does not load the native
job/file-identity/memory types, enter the scheduler, query CIM, create the run
directory or hash retail reference content. `-Run` requires a separate reviewed
GO. No Run or reference-code scan has happened during this preparation.

That sentence records the original preparation checkpoint. The subsequent
separately authorized [Run B](run-b-validation-2026-10-12.json) completed as
`CandidateRouteNeedsReview`: original root exit zero / job Active=0, final guarded
source proof true, reservation released, and Main unchanged. It established
only a static candidate route. The new targeted phase requires a new reviewed
Plan and its own GO; Run B is not reusable authorization.

## Fixed resource and source contract

The reservation is Analysis, 1 GiB physical / 2 GiB commit. The original Python
process has a 60-second monotonic deadline, starting before suspended Prepare.
The complete original Windows job is owned by unchanged `BuildJob.cs` SHA256
`f6be2a4cafddb78b5e07a6802354575ada418cb7643d96a3abd0a4c063bc6387`.
No new C# implementation was added. The current scheduler, memory helper,
recorder import and file-identity helper are independently hash-pinned.

The three retained inputs total 25,162,848 bytes. The interpreter's four DLLs
and the exact Capstone source/native-library inventory add 42 pins / 15,178,078
bytes. Plan B has 40,534,637 guarded bytes including sources/providers/manifest.
Two guarded hash passes plus the child's input read total 106,232,122 bytes;
small pre-admission source checks remain below the 128 MiB known-input-content
budget. This count excludes ordinary operating-system/interpreter library IO.
No reference is copied. The 359,301,120-byte bound is for linear opcode searches
in an existing RAM buffer; reading each candidate's displacement is additional
fixed-size memory access, not repeated disk IO.

Read-sharing handles deny writes/deletes while inputs are used. After admission,
the existing file-identity helper binds NTFS identities, length, time and
attributes. Final identity/content checks happen while handles and admission are
still retained. Source changes or failed proof prevent normal release.
The source/module/runtime inventory is fixed; interpreter standard-library and
OS components remain the existing installed environment, not a newly frozen
whole-machine image.

The child uses `-I -B` and a fresh, unused pycache prefix. It writes at most
3 MiB for the report through the new `--max-output-bytes` argument; the standalone
tool default remains 4 MiB. The state is capped at 128 KiB, and the supervisor
counts all files including hidden ones against 4 MiB combined. Final counters
include the serialized state. Oversize/unexpected activity refuses success and
preserves evidence; it is not permission to delete or silently truncate a result.

## Ownership and failure handling

Prepare creates the process suspended inside the original kill-on-close job.
The supervisor immediately resumes it before any CIM call. PID, executable,
creation time and BelowNormal priority then come from the original handles.
Scheduler registration compares the CIM tuple with those handles inside the
current admission lock before saving it, so a reused PID cannot be adopted.
A process that finishes before CIM is recorded from its still-retained original
handles; registration absence alone is not a failed process or proof of success.

The monotonic clock is refreshed after Prepare/Resume, identity reads, CIM,
memory/filesystem polling and state writes. A late call cannot turn a stale
exit-zero sample into acceptance. Normal completion requires root exit zero,
zero active original-job processes, a bounded typed report and final source
proof. The report can establish only a candidate static route needing review.

Failures stop only the retained original job. A fresh root-exited / Active=0
sample is required after Stop, with a separate 15-second cleanup deadline.
Unknown factory ownership, failed Stop/closure, source-proof failure or refused
lease release retain the reservation and quarantine the owner/guard references
in the current AppDomain. The serialized state records the admission token and
identity. Quarantine references last only for that host's lifetime; after host
exit the original job's kill-on-close behavior applies and the durable scheduler
lease remains for investigation. Host exit is never relabeled as verified closure.
There is no PID-based kill, process adoption, automatic lease deletion or retry.

## Validation and exact Plan B

The actual PowerShell functions passed **111 synthetic checks**. They cover
Resume-before-registration, fast exit, wrong identity, live registration error,
slow CIM/poll/save, nonzero root, active descendants, output/commit refusal,
failed Stop, cleanup deadline, failed source proof, failed release, PID reuse,
concurrent write denial, hidden output counting and typed report limits.
The static locator's **12 tests** also pass, including the reviewed LOOP/CALL
bypasses, one opcode pass and exact instruction cap. These are source/mock
results; the F6 native job and resource lifecycle have not been exercised by
this new supervisor.

An actual default Plan B was run in a fresh PowerShell host with Add-Type,
admission, CIM, creation/copy and retail hashing trapped. It completed without
triggering those traps; native types stayed absent and the run root stayed
absent. Plan A is preserved as an obsolete preparation snapshot.

Local recipe B SHA256:
`ee98e9a6bb73b231b2658dcce79e86c5e6a064a7dbce3250c98105a3a85cc6b6`.
Default-Plan evidence SHA256:
`6716b61e5b2451bd40ad4d0dee0e60b0287b1cd9f0b283fc9526192fba2492d3`.
The local command file and validation JSON bind the exact source hashes.
The coordinator reviews this supervisor and its Plan before issuing any Run GO.
Main, stock, `rig-abi/`, previous failed rig receipts and other edits are preserved.

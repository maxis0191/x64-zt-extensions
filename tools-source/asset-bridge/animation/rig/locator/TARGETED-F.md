# Locator Plan F: fixed 512-edge preparation

The original checkpoint below contained source, pure tests and an inert Plan
only. A later separate GO authorized one Run F, recorded below. Run E remains
a failed traversal at 64 edges, preserved in its separate
[receipt](run-e-validation-2026-10-12.json), commit `996a686`.

## Run F: authorized traversal completed

The [sanitized receipt](run-f-validation-2026-10-12.json) records one Run at
source `8b650d7` and exact Plan SHA256
`95a02ba6a5a21ec74b4b7aef9f74db481c14b41208d578d49f3e16c206562886`.
It fully decoded and visited all 500 instructions in the same 2,498-byte range,
recording 93 edges: 65 calls not followed and 28 direct branches. There is no
current, pending, refused or unresolved frontier. Status is
`CandidateRouteNeedsReview`, not first-writer or gameplay acceptance.

The original process exited 0 with job Active=0. Guarded inputs remained
unchanged; the job closed without quarantine and its reservation was released.
The independent post-observation found no lease or original process identity,
and Main's image/hash/creation identity was unchanged. Two output files total
108,775 bytes, also the maximum observed size. Analysis took 0.047 seconds;
the supervisor measured 609 ms for its original process lifecycle. No stock
was staged, no restoration was needed and no game or ZoneTool was launched.

An earlier preflight did not launch F: a supplemental observer incorrectly
treated two old Python services as possible heavy work. The coordinator
identified the Main incident recorder and another project's loopback HTTP
preview, then issued a new unique GO. Their exact identities were verified and
preserved; no budget changed. Both preflight receipts remain intact. The raw
post-observation still uses the legacy `ForeignHeavy` label for those two rows,
each with scheduler `Heavy=false`; the sanitized receipt explains that label
without rewriting the original evidence. This was one Run, with no automatic
retry and no subsequent Run authorized.

The one literal +0x58 memory reference remains a read at `0x140a18210`; there
are no explicit overlapping write candidates. [Report E's static address
trace](REPORT-E-LAYOUT.md) still identifies possible earlier by-reference call
boundaries. Completing F's declared traversal does not inspect those callees,
prove their return behavior, establish the complete logical function, or prove
live surface identity and the first writer. All such proof flags remain false.

## Original preparation contract

The coordinator requested a fixed 512-edge contract after E fully decoded the
2,498-byte owner range into 500 instructions but stopped at its 65th edge.
A [report-only review](REPORT-E-LAYOUT.md) counts 93 call/branch sites across
that range, including unvisited rows. The new bound is fixed before execution;
it is neither automatic expansion nor proof that a future traversal will finish.

| Limit | Plan F |
| --- | ---: |
| Selected entry | `0x140a17e70` |
| Maximum fragments | 8 |
| Maximum bytes in one fragment | 16,384 |
| Maximum total decoded bytes | 32,768 |
| Maximum decoded instructions | 8,192 |
| Maximum recorded control edges | **512** |
| Derived maximum refused frontiers: one root + edge bound | **513** |
| Internal checked analysis deadline | 10 seconds |
| Global opcode scans / followed callees | 0 / 0 |

Only the fixed edge cap changes from E. The derived diagnostic cap consequently
changes from 65 to 513. The historical two-entry allowlist still selects one
exact entry per Plan. Entry F is unchanged from E. Traversal, owner/decode
checks and current/pending diagnostics are unchanged. A refused local frontier
still produces overall failure; a hard bound still stops the walk globally.

The original F6 job, full 1 GiB physical / 2 GiB commit admission, BelowNormal,
60-second checked outer deadline, 15-second cleanup deadline, 3 MiB report and
4 MiB combined-output limits remain unchanged. Final guarded input proof and
original-handle closure still precede release. Admission is not an OS memory
cap and checked deadlines are not preemptive. No report is truncated to fit.

The [preparation receipt](targeted-f-validation-2026-10-12.json) records 40 passing
Python tests (12 original, 28 targeted) and 153 PowerShell checks. Synthetic
fixtures accept exactly 512 calls without following callees and refuse call
513 before appending its edge or call record, retaining the current frontier.
A queued sibling is also preserved when a smaller test cap fails. The supervisor
rejects the obsolete 64-edge Plan, a 513-edge Plan and an untyped bound, accepts
a consistent 512-edge report and rejects an otherwise consistent 513-edge report.

The exact default Plan is tested with native loading, lease acquisition, CIM,
creation/copy and snapshot hashing trapped. Preparation does not validate runtime
hashes or obtain fresh full admission. The ignored Plan, command and executor
receipt are immutable and individually pinned in the preparation receipt.

At preparation, the next gate was independent source and exact Plan review,
then a separate explicit GO before one Run. Those gates led to the result above.
Next: coordinator review of that retained report and its call boundaries; no
further Run or callee read without a separately scoped plan and GO.

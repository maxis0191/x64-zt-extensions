# Locator Plan F: fixed 512-edge preparation

This checkpoint contains source, pure tests and an inert Plan only. It authorizes
no Run, snapshot content read, game or ZoneTool launch, attachment or callee walk.
Run E remains a failed traversal at 64 edges, preserved in its separate
[receipt](run-e-validation-2026-10-12.json), commit `996a686`.

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

Next: independent source and exact Plan F review, then a separate explicit GO
before one Run. First-writer proof, live provenance and gameplay acceptance
remain false.

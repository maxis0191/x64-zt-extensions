# Locator Plan E: reassessed fixed owner-range bounds

The original checkpoint below was source, pure tests and inert Plan only. A later
separate GO authorized one Run E, recorded below, without retry or attachment.
The Run D
failure is archived separately and its original receipts remain unchanged.

## Run E: complete range decode, partial traversal

The [sanitized receipt](run-e-validation-2026-10-12.json) records one Run at
source `3ca9df4`. Its owner is `[0x140a17e70, 0x140a18832)`, 2,498 bytes, fully
decoded into 500 instructions. The traversal visited 310 instructions and
recorded 64 control edges before refusing the next edge at `0x140a183c3`.
Six frontiers remain pending; there were no local ownership refusals or global
opcode scans. This is `Failed` / `bounded-refusal`, not a completed route.

The original process exited 2, job Active=0; final guarded input proof passed,
the job closed and its reservation was released. Main was unchanged. The two
output files total 103,728 bytes; maximum 103,732 includes an earlier state.
No callee was followed, no retry occurred and the original receipts are intact.
E's measured range size does not retroactively fill D's missing size evidence.

D refused before decoding because its entry's unique `.pdata` range exceeded
the deliberate 2 KiB limit. The exact range size was not serialized by D and is
still unknown. The coordinator authorized preparation of new fixed limits; this
is a reviewed change of contract, not an adaptive expansion during an attempt.

Plan E keeps the single selected entry **`0x140a17e70`**, the same traversal and
no followed callees or global opcode scans. Its immutable source/Plan limits are:

| Limit | Plan E |
| --- | ---: |
| Selected entries | 1 |
| Maximum fragments | 8 |
| Maximum bytes in one fragment | 16,384 |
| Maximum total decoded bytes | 32,768 |
| Maximum decoded instructions | 8,192 |
| Maximum recorded control edges | 64 |
| Internal checked analysis deadline | 10 seconds |

The old and new bounds cannot be mixed: the supervisor validates the exact Plan
limits, source hashes and matching report. Ownership/decode refusals remain
local diagnostics with independent bounded branch progress and overall exit 2.
Every hard budget/deadline failure still aborts globally. No absent owner is
decoded from a guessed address. The two-entry historical allowlist is unchanged;
E does not select or follow the other seed. Logical-function completeness,
surface-base identity and first-writer proof remain false.

For a future attempt, the current frontier receives `selected_owner` metadata
as soon as a unique owner is identified: start, exclusive end, actual byte count
and unwind RVA. This happens before any range/count/byte/decode gate. Missing
ownership remains null; ambiguous-owner diagnostics include the actual sizes
of their bounded owner list. Successful fragment records already retain actual
start/end/byte counts. This improvement supplies future evidence only; it does
not reconstruct or change D's unknown actual owner size.

The original F6 process/job lifecycle remains unchanged: BelowNormal, full
1 GiB physical / 2 GiB commit admission, 60-second checked process deadline,
3 MiB report / 4 MiB combined output, 15-second cleanup deadline, final guarded
source proof before lease release. Deadlines are not preemptive and admission
is not an OS memory cap. A larger range can still hit another bound, including
report size; no limit is relaxed automatically and no output is truncated to fit.
Plan E binds 40,542,798 guarded bytes; two guard passes plus the child's input
read total 106,248,444 known bytes, before small source prechecks, below 128 MiB.

The [preparation receipt](targeted-e-validation-2026-10-12.json) records 38 passing
Python tests (12 original, 26 targeted) and 148 PowerShell checks. New pure cases
accept a 3,001-byte owner, refuse a 16,385-byte owner before decoding while
retaining its size, stop exactly at 8,192 instructions, and refuse the next
fragment before crossing the 32 KiB total. The supervisor separately refuses a
fragment above 16 KiB even when the total remains within 32 KiB.

Actual default Plan E ran with native loading, lease acquisition, CIM,
creation/copy and snapshot hashing trapped. No trap fired; the native types and
execution root remain absent. Runtime hashes and fresh full admission remain
future Run checks, and the snapshots' capture-time provenance remains unattested.

Plan SHA256:
`b473edbf9f3505b5e97cae45a6a0c81990bbcb9b84b1ea78bd5ffc1052ad783f`.
Default Plan evidence SHA256:
`355c848111f1b6a6cce52218333287efcae60e8856faa9a17f002e89b79d8d4a`.
Next: independent source/Plan review, then a separate explicit GO before any
single Run E. No live engine or gameplay conclusion is available.

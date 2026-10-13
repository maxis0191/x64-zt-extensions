# Locator Plan G: one explicit output-pointer callee

The original checkpoint below was source, synthetic tests and inert Plan
preparation only. A later explicit GO authorized one G Run on 2026-10-13,
recorded below. No further Run is authorized. [Run F](run-f-validation-2026-10-12.json)
is closed and remains unchanged.

## Run G: declared traversal completed, another call boundary found

The [sanitized receipt](run-g-validation-2026-10-13.json) records exactly one
Run on clean HEAD `8a8ccfd`, with source code unchanged from `86d35c6` and the
same pinned Plan. G decoded and statically visited 31 instructions in one
119-byte owner range, with five edges and no remaining or refused frontier.
The original child exited 0, job Active=0; guarded inputs were unchanged,
the job closed and its full 1 GiB/2 GiB reservation was released. The local
postcheck found no lease or original child. Main remained `StoppedConfirmed`,
with no game process or UDP 27016 endpoint, and the known recorder tuple survived.
An independent absence witness passed at `2026-10-13T05:22:18.2210757Z`,
pinned in the sanitized receipt. It verified all four original process tuples
absent, no descendants, lease, heavy work, game or monitored endpoint, and the
recorder tuple unchanged. The real PTY exit was verified separately. Original
job/handle closure facts come from the pinned runner receipts; the witness did
not adopt or inspect the terminated job. Runtime sources were unchanged while
the two documentary files were being edited. This closes the execution review,
without establishing any functional or gameplay acceptance.

The initial G preflight had incorrectly required Main to be running. Its refusal
and original helpers remain intact. After independent confirmation that Main
was stopped, separately reviewed r2 helpers accepted that explicit state only
with no Main/game process and no endpoint. Global endpoint-query errors still
fail; absence after a successful query is valid data. Main is never started to
satisfy this observer. A later fresh preflight and renewed unique GO preceded
the one Run; no native retry occurred.

The PTY capture preserves both actual tool-output chunks, including console
wrapping/escape sequences. Host, parent, Run host and child image/creation tuples
are in the ignored receipts. Two Run files total/max 10,222 bytes: report 8,282
and state 1,940. The original-process lifecycle took 515 ms; analysis took
0.016 seconds. The fixed 16 MiB new-output allocation in the existing 4 GiB
pool did not alter the 3 MiB report or 4 MiB Run-output ceilings. No game,
ZoneTool, stock copy, restoration or cleanup occurred, and no snapshot/binary
was rehashed after release.

The [report-only boundary review](REPORT-G-BOUNDARY.md) traces entry RCX into
RBX and, on the nonzero-source branch, into R9 for the call to `0x1405f04a0`.
No direct store through that pointer appears in this range. A different call
lies on the zero-source branch. All three callees remain unexamined, and the
literal +0x58 reference is a stack restore. First-writer, live provenance and
rig/animation acceptance remain false. The proposed next seed is exactly
`0x1405f04a0`, from the explicit R9 handoff at `0x140dd1fe6`; this is a source
proposal for separate review, without a new Plan, allowlist expansion or Run.

## Original source/Plan preparation

Owner direction, 2026-10-12: the import target is now **BO3/T7x to IW7**;
H1 is abandoned as the new import target. Future model and animation work must
use T7 skeletons, skinning weights and xanim as its starting point, with their
formats and compatibility still to be established. Do not extend the H1 import
route or bulk-read the BO3 files while their download is in progress. G remains
an IW7-side investigation and its exact seed, source pins, Plan and budgets are
unchanged. Existing H1-era helpers and evidence are retained; this direction
does not authorize a new donor read or alter the independent SDK runtime demo.

## Selection from the retained F report

G selects **only `0x140dd1f90`**, the direct target recorded at F's visited
call site `0x140a181bd`. F report SHA256 is
`a9d47a4a6aed8c157f78855efa27c49cd28c7d0824bb3e9bb2f2c74a392a94ee`.
This is an explicit new root selected during review, not automatic callee
expansion from F. The Python reader and supervisor allow exactly this third
canonical entry alongside the two historical entries, one per invocation.

The existing [address trace](REPORT-E-LAYOUT.md), also visible in F, gives:

| Argument at `0x140a181bd` | Static origin |
| --- | --- |
| RCX | `S_1817b + 0x58`, retained in RBX across the earlier call |
| RDX | qword read at `S_181a4 + 0x50` |
| R8D | dword read at `S_181a4 + 0x18` |
| R9 | RIP-relative address; pointed-to content not inspected |

Each S denotes a separate load from global slot G=`0x1453e1800`. Their equality,
the runtime surface identity and ordinary x64 register preservation remain
assumptions. Names such as buffer, size or label are not verified field ABI.
RCX is a concrete output-pointer candidate, which makes this root useful for
finding a store or update boundary without inspecting both helpers at once.

The earlier `0x140a7ca90` call at `0x140a1819f` also receives the +0x58 address,
in RDX with R8D=8. It remains outside G's entry allowlist and is not selected.
Its effects and the earlier whole-record call remain unknown. A store found in
G would not establish that G is the first writer.

## Unchanged reader and supervisor contract

The existing targeted reader starts at the single selected seed, requires unique
`.pdata` ownership and complete instruction-boundary decoding, and traverses
only explicit branches and sequential continuations within fixed bounds. Calls
are recorded without following them. Missing ownership and decode failures keep
their diagnostics and overall failure; hard bounds abort without expansion.

| Fixed limit | G |
| --- | ---: |
| Root entries / fragments | 1 / 8 |
| Per-fragment / total decoded bytes | 16,384 / 32,768 |
| Decoded instructions / recorded control edges | 8,192 / 512 |
| Derived refused-frontier diagnostic cap | 513 |
| Internal checked deadline | 10 seconds |
| Global opcode scans / followed callees | 0 / 0 |
| Full physical / commit admission | 1 GiB / 2 GiB |
| Outer checked deadline / cleanup | 60 / 15 seconds |
| Report / combined output | 3 MiB / 4 MiB |

These are the already tested F ceilings, not measurements of G. The selected
callee's owner, size and content are deliberately unknown until a separately
authorized Run. The same fixed ceilings can refuse it; no budget grows on
failure. The existing reader still hashes the same three retained reference
files under the original source guards and full admission. No reference file is
read during this preparation. The F6 original-handle job, BelowNormal priority,
final input proof and lease-release conditions are unchanged. Checked deadlines
are not preemptive and admission is not an OS memory cap.

## What a future report could establish

Review the complete retained instructions for stores through entry RCX or its
aliases, pointer replacement/clearing, branch conditions and further by-reference
call boundaries. The existing `offset_58_overlap_candidates` list only matches
literal operand displacements; it is not a general alias or output-argument
analysis. For example, a store through `[rcx]` can update the caller's +0x58
field while that list stays empty. A synthetic fixture verifies that the full
instruction remains visible and no first-writer proof is inferred.

Any finding must distinguish a decoded store candidate from execution, branch
coverage, actual S/G stability and provenance. No inner callee or second seed is
opened automatically. `actual_first_writer_established`, live provenance,
breakpoint, logical-function completeness and gameplay acceptance remain false.

The [preparation receipt](targeted-g-validation-2026-10-12.json) pins the exact
Plan, Plan-only command, source and default-Plan evidence. It records 41 Python
tests (12 original, 29 targeted) and 159 PowerShell checks. The new seed binds
exactly through argv and report validation; the other helper, multiple seeds,
noncanonical forms and an F report presented as G are refused. The actual
default Plan runs with native loading, lease acquisition, CIM, creation/copy
and snapshot hashing trapped; G's Run root remains absent.

At preparation, source/Plan review and a separate GO with fresh full admission
were required before one Run. Those gates led to the result above. Next:
coordinator review of the retained receipts and newly identified call boundary,
without an implicit additional Run or callee read.

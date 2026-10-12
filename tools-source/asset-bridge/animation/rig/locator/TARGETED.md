# Targeted candidate continuation, Plan C

This is source and inert Plan preparation only. The coordinator has not given
Run C or attachment permission. Run B's original files, hashes and failure-free
lifecycle receipt remain unchanged. The engine chat received the candidate and
its limitations through the coordinator; this did not grant a live probe GO.

The sole entry is `0x140a17970`, the common callee immediately before the
type-7 wrapper in the two Run B caller fragments. This is a snapshot address,
not an established function name or currently loaded retail address.

## Fixed traversal scope

`locate_targeted.py` starts a worklist at that entry. It decodes the containing
`.pdata` range from its recorded start to establish instruction boundaries,
then follows only instructions reachable from the selected entry. An explicit
direct non-call branch may reference another range. A decoded instruction at
the range end may fall through to the next address; that continuation must
also have unique ownership and a valid decoded boundary. No arbitrary adjacent
range, reverse caller, string, opcode or address-space search is performed.

Calls are recorded, including indirect calls, but their targets are never
followed. Their returning fallthrough is a static assumption, explicitly marked
in the report. Indirect jumps remain unresolved; jump tables are not guessed.
Returns, interrupts and explicit halt/undefined instructions stop that path.
Repeated reachable addresses are deduplicated. Only reachable instructions can
produce overlap candidates or enqueue continuations; the complete small range
is retained for boundary review with each instruction's reachability marked.

| Bound | Fixed maximum |
| --- | ---: |
| Selected entry addresses | 1 |
| `.pdata` fragments | 8 |
| Bytes per fragment | 2,048 |
| Total decoded range bytes | 8,192 |
| Decoded instructions | 2,048 |
| Calls, branches and boundary fallthrough edges | 64 |
| Internal analysis duration | 10 seconds |
| Global opcode scans / called targets followed | 0 / 0 |

The entry count is not a claim that all branch destinations belong to one
logical function. A tail branch can cross a function boundary. The enforced
unit is the `.pdata` fragment; an exact logical-function count, identity and
completeness remain unestablished. Unwind
RVA metadata is retained without interpreting chained unwind information.
Ambiguous or overlapping selected ranges, incomplete decode, missing ownership,
non-instruction branch targets or any limit violation refuse success without
expanding scope.

## Memory-reference evidence

The report keeps explicit reachable memory operands whose displacement and
width overlap offset `0x58`. It lists access metadata and unproved write
candidates separately. The pinned Capstone 5.0.7 synthetic test marked a
`movups [rax+0x50], xmm0` destination as read-only; relying solely on that flag
initially missed the overlapping 16-byte write. The correction supplements
decoder write flags for an explicit MOV-family memory destination and keeps
all overlap references for manual review. The regression now passes.

No displacement establishes an XSurface base. Pointer rebasing, earlier LEA,
implicit bulk copies, unresolved branches and unexamined callees can hide the
actual field access. A missing candidate is never a proof of no write. The
report cannot establish the first writer, logical function completeness, a
valid live breakpoint, field meaning or acceptance of E's nonzero values.

## Original ownership supervisor and new Plan

Plan schema 2 selects only the targeted script, exact seed and fixed inner
limits. Schema 1 remains the original registration locator route. The
supervisor refuses a report from the other mode or widened/ill-typed targeted
counters. It retains the original F6 job, fresh host, BelowNormal priority,
1 GiB physical / 2 GiB commit admission, 60-second original-process deadline,
3 MiB report / 4 MiB total output and 15-second closure deadline. These are
checked deadlines, not a preemptive watchdog; admission is not an OS memory cap.

The child still reads and hashes the same three references once (25,162,848
bytes). This is source identity IO, not a global opcode scan. The supervisor
holds the same source/provider/interpreter, 42 runtime and three reference
guards and verifies their final identities/hashes before release. Plan C binds
40,538,053 guarded bytes; two guard passes and one child input pass total
106,238,954 known content-read bytes, plus small pre-admission source checks,
below 128 MiB. Ordinary interpreter/OS IO is outside that count.

The snapshot capture has no attested capture-time source-binary manifest.
Matching historical hashes preserves the evidence chain, not live compatibility.
Any future retail observation must independently match the selected code-window
hashes against the loaded image and needs a separate live GO.

## Preparation evidence

The [sanitized preparation receipt](targeted-validation-2026-10-12.json) records
28 passing Python tests (12 original, 16 targeted), 134 PowerShell checks and
the exact inert Plan C. Synthetic cases cover cross-fragment branches and
fallthrough, loops, unreachable code, instruction-interior targets, incomplete
and overlapping ranges, indirect jumps, unexamined calls, SIMD overlap and
each hard cap. PowerShell tests cover the targeted seed/bounds, typed output,
cross-mode report refusal and the existing ownership lifecycle.

The actual default Plan C was run with native loading, admission, CIM, creation,
copy and retail-content hashing trapped. No trap fired; native types stayed
absent and the execution directory stayed absent. Its source/provider pins
were checked; runtime content hashes and resource admission remain for a
separately authorized Run. No targeted analysis, new retail scan, resource
measurement, game, ZoneTool or debugger was started during this preparation.

Plan C SHA256:
`f52d2728225ab92670a909ab2c92a336f4b6400519f52c7fc601671d8b86ad3f`.
Default Plan evidence SHA256:
`1e7082d461981f2b86bbf1b4c281de9be63582a7f5c15e5bb8c147f1f4c2b7d5`.
The next action is coordinator source/Plan review, followed by a separate exact
GO and fresh full admission if execution is chosen.

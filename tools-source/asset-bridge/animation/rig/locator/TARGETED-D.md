# Targeted Plan D: one per-record callee, explicit refusal frontiers

This is source, synthetic-test and inert-Plan preparation. No Run D, new snapshot
read, process attachment or live acceptance is authorized by this document.
Run C remains a failed, closed and released attempt at its original source and
Plan. Its original state, report and after-check receipts are unchanged.

## Candidate from the existing report only

C's entry `0x140a17970` branches either to an adjacent body at `0x140a179de`
or a common exit range at `0x140a17a6c`. The exit restores stack/register state
before jumping to `0x1400a1240`, outside all three decoded ranges. That is a
candidate shared external tail; its function identity, leaf status and reason
for absent/ambiguous ownership were not measured by C's generic error.

The adjacent body was fully decoded but only partly visited when C aborted.
The retained instructions describe a count at header offset `0x10`, a count
multiplied by `0x100` before a call, and a loop calling `0x140a17e70` while
advancing a pointer by `0x100`. The coordinator/engine review finds this
consistent with a per-XSurface route, but that name and pointer type remain
inferences. No additional snapshot bytes were read to prepare this candidate.

Plan D therefore selects **only `0x140a17e70`**. It does not revisit C's seed,
follow that seed's other callees, or inspect the unowned exit target. The CLI
and Plan contract allow exactly the historical seed and this new seed, one at
a time. The child report must match the exact entry selected by its Plan.

## Local refusals preserve independent work

Each queued frontier now carries its target address, source instruction,
edge type, source mnemonic, containing source range and whether the target is
inside or outside that range. This is range membership, not function identity.
The report distinguishes `missing-pdata-owner` from `ambiguous-pdata-owner`,
includes the owner count and at most eight owner ranges, and separately records
overlapping ranges, incomplete decoding or invalid instruction boundaries.

A local ownership/decode refusal is recorded and that frontier is not followed.
Other already queued branches continue under the same global limits. A partially
decoded cached range cannot later be adopted through another incoming edge.
Any local refusal still makes the overall CLI exit **2 / bounded-refusal**;
continuing independent work does not convert partial evidence into success.

Hard limits and deadlines remain immediate global aborts, with the current and
pending frontier records preserved. No budget is reset or enlarged. Calls remain
unfollowed and their returning fallthrough remains an explicit assumption.
Indirect jumps remain unresolved. There is no byte-boundary guess for a leaf
without `.pdata`, no global opcode scan and no adaptive selection of callees.

Report schema `iw7.rig-targeted-static/2` replaces the misleading reachability
name with `visited_in_static_walk` / `visited_instructions` and explicitly sets
`unvisited_is_unreachable=false`. It records pending and refused frontiers,
fragment decode completeness and queue exhaustion. The supervisor refuses a
success report with a refused/pending frontier, incomplete fragment, wrong seed
or any completeness/first-writer overclaim. An exhausted queue is not proof of
a complete logical function or of dynamic reachability.

## Unchanged bounds and ownership

One selected entry; at most eight `.pdata` fragments, 2 KiB each and 8 KiB total;
2,048 decoded instructions; 64 recorded control edges; 10 seconds of internal
analysis. At most 65 refused frontiers follows from the one root plus the
control-edge limit and is also enforced explicitly. Zero global scans and zero
called targets followed. Both logical-function completeness flags remain false.

The original F6 job, source/runtime/reference guards, fresh host and 1 GiB
physical / 2 GiB commit reservation remain unchanged. The supervisor retains its
60-second checked process deadline, 3 MiB report / 4 MiB combined output and
15-second cleanup deadline. Neither deadline is a preemptive watchdog; the
reservation is not an OS memory cap. Final guarded input proof precedes release.
Plan D has 40,542,374 guarded bytes and 106,247,596 known guard-plus-child content
read bytes, plus small pre-admission source checks, within the 128 MiB bound.
The same three references must be rehashed under any future admission; historical
hash equality still does not attest capture-time provenance or live compatibility.

## Preparation evidence and next gate

The [sanitized receipt](targeted-d-validation-2026-10-12.json) binds 34 passing
Python tests (12 original, 22 targeted) and 145 PowerShell checks. New regressions
exercise missing versus ambiguous frontiers, independent branch progress after
a refused tail, rejection of a cached incomplete fragment, preservation of a
fatal budget frontier, the exact two-entry allowlist and per-Plan report binding.

The actual default Plan D completed with native loading, admission, CIM,
creation/copy and reference-content hashing trapped. No trap fired, no native
types were loaded, no lease was acquired and the Run D root remains absent.
Plan SHA256:
`6e2158212845ad7642eae0a5a97304fb7e2dec20303f6d0fac2bb0d637113ca2`.
Default Plan evidence SHA256:
`625ebead135ac025958a55dd56d0e3b28c3814d6f3c186d8c80a1eda0582d014`.

Next: coordinator source/Plan review, then a separate exact GO and fresh full
admission if the single targeted Run is selected. No first writer, live
breakpoint, XSurface base, field meaning or gameplay acceptance is established.

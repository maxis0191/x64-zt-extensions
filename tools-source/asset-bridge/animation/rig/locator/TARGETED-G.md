# Locator Plan G: one explicit output-pointer callee

This is source, synthetic tests and inert Plan preparation only. No G Run,
snapshot content read, admission, game, ZoneTool or debugger action is authorized
by this checkpoint. The SDK runtime demonstration keeps priority for the heavy
slot. [Run F](run-f-validation-2026-10-12.json) is closed and remains unchanged.

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

Next: coordinator source/Plan review, then a separate explicit GO and fresh
full admission before one G Run. Until then, no heavy reservation is taken.

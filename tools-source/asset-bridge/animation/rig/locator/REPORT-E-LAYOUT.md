# Report E: static field-address trace

This review reads only the existing E JSON report, SHA256
`9b04cf70904b4d28a5bd12909c23fd9facb6dc6921e8a42dbc248ad06c5eee84`.
It performs no snapshot read, disassembly, callee inspection or live operation.
The original [E receipt](run-e-validation-2026-10-12.json) remains unchanged.

The 500 decoded instructions contain 65 calls, 22 conditional branches, six
unconditional branches and one final return at `0x140a18831`. All 28 explicit
branch targets lie inside the selected range. These are report-wide counts,
including instructions E did not visit; they do not complete E's traversal or
establish a complete logical function. Calls remain unexamined.

## Base of the read at +0x58

RIP-relative address arithmetic identifies the same global slot
`G = 0x1453e1800`. For example, the next address after the load at
`0x140a181f2` is `0x140a181f9`; adding its reported displacement `0x49c9607`
gives G. Let `S_i` mean the pointer loaded from G at a particular load. This is
a static origin trace, not proof that S is a live XSurface or remains identical
across unexamined calls.

| Site | Static argument or memory relationship | Classification |
| --- | --- | --- |
| `0x140a17e8c` | RDX loaded from G; R8D = `0x100` | Unexamined call to `0x140a7ca90`; possible whole-record effect |
| `0x140a1819f` | RDX = `S_1817b + 0x58`; R8D = 8; ECX = 0 | The field address is passed to `0x140a7ca90`; a write is possible, not proved |
| `0x140a181bd` | RCX = `S_1817b + 0x58`; RDX = `[S_181a4 + 0x50]`; R8D = `[S_181a4 + 0x18]` | The field address is passed to `0x140dd1f90`; another possible writer boundary |
| `0x140a181ed` | RDX = `S_181c2 + 0x60`; R8D = 8; ECX = 0 | Analogous address handoff to `0x140a7ca90` |
| `0x140a18210` | RDX changes from `S_181f2` to `[S_181f2 + 0x58]` | Explicit read, not a store |
| `0x140a18214` | RCX = `S_181c2 + 0x60`; RDX = prior +0x58 value; R8 = `[S_181f2 + 0x50]`; R9D = `[S_181f2 + 0x18]` | Values and +0x60 address are passed to `0x140dd2100` |

All six sites above were marked visited in E. The address kept in RBX across
calls assumes the normal x64 callee-preserved register convention. Other
arguments include RIP-relative addresses whose pointed-to strings were not read.
The +0x50/+0x58/+0x60 sequence suggests source data, buffer and view roles, but
these names, field ABI, GPU resource identity and runtime values remain hypotheses.

## Visible stores and the first-writer limit

Explicit record-relative pointer stores appear at +0x48, +0x50, +0x68 and
+0x80 in visited instructions. The +0x88 stores are partly visited and the
+0x90 stores are decoded but unvisited. Stack saves and RIP-relative helper-slot
stores are separate categories. The 500-row report has no literal direct store
to +0x58; its automated visited-overlap candidate list is empty.

That absence does not exclude indirect writes through the three earlier
handoffs above, aliases, bulk writes, or effects inside unexamined callees.
The +0x58 read now has a static global-slot origin, but the locator's raw
`surface_base_traced` flag remains false. No raw report was changed and no
actual first writer or live breakpoint was established.

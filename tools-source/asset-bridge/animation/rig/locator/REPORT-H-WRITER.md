# Report H: an explicit store through the output-pointer candidate

This review uses only H's retained 11,700-byte report, SHA256
`7cf5f8b159a55f066b4bf22ff45fd8c4cff8eabe8333acd595f4c8d87b8211c0`.
No reference snapshot, binary or called function was read after lease release.
The selected `.pdata` owner is `[0x1405f04a0, 0x1405f0573)`, 211 bytes,
window SHA256 `fa73dee8f64663876abb31d57265b7ebdfef94caaed01d4b688e2a153c1324e2`.
All 56 decoded instructions were visited in the static walk, with three direct
branch edges and two calls not followed. No pending/refused/unresolved frontier
remains. This is declared traversal under call-return assumptions, not runtime
coverage or proof of complete logical-function ownership.

Let P be H's entry R9 and T its local slot at the post-prologue `rsp + 0x20`.
The retained F/G caller hypothesis remains `P = S_1817b + 0x58`; actual surface
identity, equality of reloaded globals, field ABI and live provenance are not
established. H provides the following concrete static relationship:

| Site | Visible effect | Limit |
| --- | --- | --- |
| `0x1405f04db` | Entry R9 is copied into RBX, retaining candidate address P | P has not been validated against an actual live surface |
| `0x1405f0552` → `0x140dd26e0` | R8 points at local slot T; RCX points at a local descriptor and RDX selects another descriptor or zero. R9 was replaced at `0x1405f04de` by the caller's fifth argument and no longer holds P | The called body and any writes it performs remain unexamined |
| `0x1405f0557` | RAX reads the qword at T after the call | T is not explicitly initialized in H before the call; a successful callee write, nonzero value or pointer type is not proved |
| `0x1405f055c` | An eight-byte store writes RAX through RBX | With ordinary nonvolatile preservation, destination is P; this is a direct store candidate, not a global first-writer proof |

RBX has no other explicit assignment before that store in the selected range.
The RAX used by the store is defined by the post-call read of T, not directly
by the call's return register; passing T's address does not prove its production.
The store is the only explicit non-stack memory destination decoded in H. It
lies after the unexamined call on the returning path; the reader's traversal
order is not execution evidence. The later call `0x1405f0567` → `0x1412ba0d0`
is also unexamined. Do not infer helper names or semantics from their shape.

The empty literal-offset-58 list is expected: H stores through an argument
already hypothesized to contain the field's address. That list is not alias
analysis and does not contradict the explicit store witness.

This resolves the narrow question of where an explicit store through P is
visible. It does not settle whether any preceding H/F/G call already changed
that field, whether the relevant path executes, whether P still names the same
surface, or what value category T supplies. No GPU-object, allocation, rig,
weight, animation or owner-acceptance claim follows from this result.

For a separately reviewed Engine observation, H entry is a candidate boundary
where R9 carries P and `0x1405f055c` is a concrete expected store site. First
bind the loaded image/code window, establish the actual surface/P relationship
and observe the before-value; no authored-zero state is assumed. A future
watchpoint first hit would cover only its observed interval, leaving earlier
F/G effects unresolved. No executable breakpoint/watchpoint script, further
callee read, next seed or additional Run is authorized by this report.

# Report G: output pointer handed to another call

This review uses only the retained 8,282-byte G report, SHA256
`0edc13f6fc783cfcaa53569b7c0d2638859c98b705c4cc563f5831364d64e84c`.
No snapshot, binary or called function was read after G's lease release.

G decoded the unique selected `.pdata` range `[0x140dd1f90, 0x140dd2007)`,
119 bytes, and statically visited all 31 instructions. Its five edges comprise
three calls not followed, one conditional branch and one direct jump. No
current, pending, refused or unresolved frontier remains. This completes the
declared traversal under call-return assumptions, not live execution or proof
of complete logical-function ownership.

Let P be entry RCX, D entry RDX, N entry R8D and L entry R9. The caller-side
hypothesis from F is `P = S_1817b + 0x58`; actual surface identity, S/G stability
and field ABI remain unproved. G preserves P in RBX at `0x140dd1fad`, D in RDI,
N in EBP and L in RSI. The following static relationships are visible:

| Branch/site | Argument or effect visible in this range | Limit |
| --- | --- | --- |
| D is nonzero: `0x140dd1fb5` → `0x1403bc140` | RCX still contains P when this first call is reached; its returned RAX is retained in a local stack slot | Callee and argument consumption unknown |
| D is nonzero: `0x140dd1fe6` → `0x1405f04a0` | ECX=N, EDX=2, R8=D, R9=P; the fifth argument points to two local qwords containing the earlier RAX and L | Explicit output-address handoff candidate; callee not inspected |
| D is zero: `0x140dd1fed` → `0x14126a090` | RCX still contains P; no previous call lies on this branch | Possible update boundary, not proof of a clear or release operation |

The nonzero-path alias trace assumes normal preservation of RBX/RDI/RBP/RSI
by the earlier unexamined call. Every explicit memory destination in G's
decoded instructions is stack-relative; none directly stores through P or its
visible aliases. That does not exclude writes performed by any of the three
calls, nor effects before G in F's earlier helper `0x140a7ca90`.

The report's one literal +0x58 reference at `0x140dd1ff7` restores RBP from
`[rsp + 0x58]`. It is a stack read, not a surface-field read. The empty literal
offset-58 write-candidate list is therefore not an alias-analysis result.

G establishes another static call boundary worth reviewing. It establishes no
actual first writer, current live provenance, GPU object identity, T7 rig/weight
layout or animation acceptance. No further callee, seed or Run is authorized by
this report; selecting a subsequent experiment remains a coordinator decision.

Proposed next source plan: select only `0x1405f04a0`, the explicit R9=P handoff
at `0x140dd1fe6`. Its owner size and contents are unknown and have not been read.
This target is not yet added to the locator entry allowlist. Even a store there
would leave earlier-call and zero-source effects unresolved; the proposal is
not first-writer evidence and carries no execution authorization.

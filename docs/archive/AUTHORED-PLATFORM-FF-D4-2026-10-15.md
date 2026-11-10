# Original platform: SDK31 stage passed, D4 preflight refused

The admitted D4 attempt on 2026-10-15 successfully ran SDK31's authored input
stage and accepted the actual ModelFF plan/3. It then refused in the preparation
of SourceValidation, before that phase created an owner or started a process.
No FF was built. The same original job, guards, reservation and persistent host
were subsequently closed, with Root independently corroborating the evidence.

[Sanitized measurements](../ops/model-lab/artifact.authored-platform-ff-d4.measured.json)
retain the frozen revisions and local text receipt lengths/hashes. Process
identities, machine paths, runtime receipts, native inputs and logs remain
outside Git. The [D3 refusal](AUTHORED-PLATFORM-FF-D3-2026-10-15.md) and
[B2 CPP qualification](AUTHORED-PLATFORM-CPP-2026-10-15.md) remain separate records.

## Actual SDK stage result

D4 used assets `a5be8bd6204c608f5c17f6a68454f7365c4695ec` (PR185), Stage
SDK31 `24edc27ff7f379613d51ae9d91b3f10054d67b6a` and the existing single-admission
ModelFF/H1 route. The native Source pin remained
`fab935826c898806855376662a8a03317b3ad8f1`, with B2 producer
`8f55ac7819d93f5bcede273aea3e478ae9438a12`. Consumer SDK30
`62cf38834a0cbcd7243a3d52ce6100c1edbd9cdc` and runtime SDK
`6dcfc719e0535509f109c593fa4342ce201b5523` were not repinned or executed.

The caller differed from reviewed D3 only by four finite namespace/revision
rebindings; reversing those replacements recovered D3's exact bytes. The entry
and its 65 causal Source assertions had passed the 49-test ModelLab suite before
this admitted operation. Those Source tests did not themselves qualify a stage.

The sole actual native job was Python `authored-stage`, created at
`2026-10-15T08:22:49.3844118Z`. It exited zero and closed its original job tree
with zero active members, in approximately 346 ms. Its JSON report recorded
`ff_inputs_staged=true`, `opaque_inputs_read=true`, and build/FF/runtime/owner
qualification flags false. These opaque reads occurred under the existing
admission. No standalone CPP rebuild was performed.

SDK31 produced the actual 4936-byte `iw7.model-ff-plan/3` file, SHA256
`02285a22c7a10333dfb1d3593479cc2248c81eddf2eb90405f35a7ae7ddd19a1`.
The original Python job measured that file; the caller accepted and guarded it.
The plan binds B2's existing writer/provenance and normalized geometry, with
`material_payload_copied=true` while material closure, FF, pixels and Ready remain
false. The LF template therefore passed the earlier D3 Source-contract refusal;
this does not establish FF serialization or rendering.

## TargetId refusal before alias creation

The entry next qualified the existing E7 candidate under its admission and
measured 104 stock inputs from 73 providers: 95 planned hardlinks and nine copies.
These were current Source observations, not inherited historical file IDs.
The actual SourceValidation call then failed at
`OriginalArena.Process.ps1:23` with
`PropertyNotFoundStrict,Microsoft.PowerShell.Commands.WhereObjectCommand`:
the budget-exempt predicate read `TargetId` from a pre-alias hardlink record.

At this point those rows had Source identity/content metadata but no TargetId.
All 95 hardlink rows lacked that property because the stock work directory,
transaction and aliases were not yet created. The predicate runs before the
function clears its previous owner or invokes `Invoke-H1OwnedStage` at lines
47/48. The actual ErrorRecord stack, InvocationInfo, original phase list and
state agree: SourceValidation did not create an owner or start a job. It created
only its empty owned log directory. The retained owner was the already closed,
successful SDK job; it was not used to attest a hypothetical new child.

`SourceValidation` stayed null. The stock Work directory was absent and the
transaction remained null. Build/offline/dump and both independent FF readers
were never reached. Restoration was not exercised; the entry's `Restored` and
`StockPreserved` flags remained false. Original stock guards and Source checks
completed in the entry's normal pre-transaction failure path before its lease
release. No Main/client/game operation or bank/config mutation occurred.

## Same-original failed-operation closure

The caller kept its actual AppDomain root, original PSVariables/context/state,
1107 Source guards and the unique native-publication guard in the same physical
`-NoExit` host. The child root remained reachable through those original
PSVariables even though the entry threw before the outer success-path capture.
Its native snapshot's `ReleasePending` field describes publication time; the
later actual context and registry checks establish the current absent lease.

The bounded closure proposal required the exact successful SDK owner/phase,
actual ErrorRecord and failed pre-alias state, rather than reconstructing an owner
from JSON. Two local drafts were refused by the parser and never invoked. The
valid R2 proposal was also not invoked: review identified a possible PowerShell
generic-list array conversion failure in its final observation, outside its try
block. R3 changed only that expression to `Publications.ToArray()` before any
closure invocation; its lifecycle and guard order stayed byte-identical.

R3 rechecked the original references, 1107 held Source streams and the original
native-publication stream. Failure receipts used `CreateNew`, enrolled the actual
stream before writing, called `Flush(true)`, and checked length/hash/JSON through
the same handle. Fresh reference checks preceded guard disposal. Its final
observation confirmed known-failed closure, all three guard lists empty and
CanExit true, while FF/Verified/Ready remained false. No job kill, manual lease
release, stage retry or replacement ownership context was used.

Root personally read both failure publications. The original host rechecked
their unchanged hashes and its original references, then explicitly exited 1.
The true PTY completed with the same aggregate failure exit. The fresh inventory
at `2026-10-15T08:43:50.4874572Z` contained no original host/parent/SDK identities,
game/compiler processes or resource leases. Root corroborated that inventory
before releasing the orchestration slot.

## Required correction and next operation

The existing budget-exempt selection must handle pre-alias inputs without reading
an absent TargetId. Missing identity must never be fabricated or fall back to
SourceId. An existing alias can be exempt only after the existing validator or
provider proves its actual current identity; a declared matching pair alone
must not hide a replaced file from path-based output accounting. Copy, missing,
empty, malformed, mismatched, disappeared and replaced targets must stay counted
or be refused before Start. Full input-guard validation must remain intact.

That helper/test correction is separate Source work. Review and merge it, compose
a fresh immutable package/capsule and obtain a distinct exact-tuple GO before
another FF attempt. Preserve D4, D3, B2 and their failed/reviewed proposals.
No authored FF, independent FF geometry/material/image readback, rendered pixels,
collision/contact or owner gameplay acceptance was established by D4.

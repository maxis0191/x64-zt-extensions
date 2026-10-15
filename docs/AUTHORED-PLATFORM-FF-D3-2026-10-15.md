# Original platform: D3 stage refusal and closed failed attempt

The admitted authored FF attempt on 2026-10-15 stopped in SDK29's first Python
stage with `Authored source contract/template changed`. No FF was built or read
back. The original failed job, reservation, retained guards and persistent host
were subsequently closed and independently checked. This is a closed failed
attempt, not an FF qualification. The earlier
[B2 standalone CPP result](AUTHORED-PLATFORM-CPP-2026-10-15.md) remains separate.

[Sanitized measurements](../ops/model-lab/artifact.authored-platform-ff-d3.measured.json)
bind the exact Source tuple and local text receipts. Logs, runtime receipts,
native inputs, process identities and machine paths remain outside Git.

## Frozen operation and actual boundary

The producer was assets `6c1736ddf3720e9913c5281ce0af1a9a31acac8d`
(PR179). The reviewed D3 caller used the existing `Build-ModelFF.ps1`, one
admission and the original H1 job owner. Stage SDK29 was
`2f9f584549ba7b009b35699a59582f4390102994`; its immutable input package was
not edited. Consumer SDK30 `62cf38834a0cbcd7243a3d52ce6100c1edbd9cdc`
was declared separately and no Bind/Materialize operation ran. Runtime SDK
`6dcfc719e0535509f109c593fa4342ce201b5523` was unchanged. The native Source
pin remained `fab935826c898806855376662a8a03317b3ad8f1`.

The D3 caller had 156 passing Source assertions, including substitutions after
receipt readback and after environment restoration. Those tests did not qualify
the SDK stage. In the actual admitted operation, input guards and project/template
copying preceded the SDK call. Its original Python job started at
`2026-10-15T07:05:03.3763378Z`, exited 1, and closed its original job tree. The
H1 phase recorded `TreeClosureConfirmed=true` and approximately 337 ms elapsed.
The entry reported `Original stage process failed.`; the bounded stderr identified
the more precise SDK refusal above.

Only `authored-stage` ran. No actual plan/3 was accepted: state retained a null
SourcePlan, empty stock inputs, null transaction and null qualified-tool hash.
Candidate qualification, retail aliases, FF build/offline/dump and both independent
readers were not reached. Stock restoration was not exercised; the initial
`Restored` and `StockPreserved` flags remained false. The planned 104 aliases and
73 stock providers are declarations, not observations from this attempt.

## Source cause: template bytes differ only by line endings

The SDK owner diagnosed the failure using bounded Source and JSON only; Root
independently confirmed it. `verify_authored_preparation` reconstructs the source
contract and hashes the bytes of its adjacent template `writer.cpp`. It compares
that hash to the closed B2 writer recipe before accepting downstream staging.

Both Source manifests identify producer `8f55ac7819d93f5bcede273aea3e478ae9438a12`
and Git blob `61a7d3aa9b12ed567634e8bebd2dd0a1577d3052`, but their exported
template bytes differ:

| Template Source | Bytes | Line endings | SHA256 |
| --- | ---: | --- | --- |
| B2 original template | 13833 | LF | `3494bbacda6964c5b6966673698851ffe083341f2dabed3cd48de99559021b38` |
| SDK29 exported template | 13991 | CRLF | `d614f6057422e416c9d12df5bbc37d66c2cbd5e8f05093789aebdbe1fc74c210` |

Converting CRLF to LF in memory yielded the exact B2 template hash. The nine
authored name/count/bounds fields agreed. This concerns the original template,
not B2's generated/adapted `writer.cpp` or its measured PE/XMB/XSB outputs.

The exporter used `git cat-file --filters` in a sparse checkout where physical
attributes were absent and system `core.autocrlf=true` applied. A commit/blob pin
therefore did not alone determine the exported bytes. The required correction is
deterministic export based on the pinned commit's attributes, tracked separately
in the SDK repository.
No generated SDK package, B2 recipe/hash, verification gate or failed D3 package
was patched to accept the mismatch.

## Honest failure closure

The original H1 owner confirmed the failed Python job closed. The entry's normal
pre-transaction failure path closed its input guards and released its reservation.
The outer caller kept its Source guards and the unique original native-publication
guard in the same physical `-NoExit` host. Its success flags and the FF flags stayed
false. The actual child root remained reachable through its original AppDomain
root and PSVariables; no owner was reconstructed from JSON.

The native snapshot's `ReleasePending=true` describes its publication before
release. Later checks of the actual original context and reservation established
closure; that historical JSON field was not treated as current lease state.

A reviewed same-host recovery retained the original references and verified the
known failed first-stage state. Its first invocation refused before publication
or disposal because a manually copied expected native SHA literal contained 65
characters. The actual producer record and the same retained stream agreed at
the correct 64-character hash. The strict corrected resume preserved this refusal,
reused the same rooted objects and loaded publication helper, and did not rerun
the stage or initialize a new owner/context/guard list.

The failure receipts used `CreateNew`, enrolled the actual stream before writing,
called `Flush(true)`, then read back and checked length/hash/JSON through that
same handle. Fresh reference checks preceded closure of the original guards.
The final failure closure confirmed the already closed job, absent lease, no
transaction and all original/publication guards closed. Its `Verified`, `FFBuilt`
and `Ready` flags remained false. No manual lease release or process kill was used.

Root personally read the preexit and closure receipts. The same original host
then passed its final reference checks and explicitly exited 1; the true PTY
also completed with exit 1. The fresh postexit inventory at
`2026-10-15T07:20:51.5526706Z` contained no matching host/parent/native identities,
game/compiler processes or resource leases. Root independently confirmed that
inventory before releasing its orchestration slot.

## Next operation and limits

Review and merge the SDK export correction, prepare a fresh immutable Source
package, then rebind a new FF capsule. Keep the frozen B2/D3 evidence and failed
recovery history. A distinct exact-tuple GO is required before native staging,
candidate or stock observation, FF work or another admission.

No authored FF, serialized material/image readback, recipient/shader/normal ABI,
rendered pixels, collision/contact or owner gameplay acceptance was established.
No game/client run, Bind/Materialize operation or promotion occurred.

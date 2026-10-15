# Original platform: FF built, sidecar readback failed, operation closed

The admitted D5 attempt on 2026-10-15 built a 1904-byte authored FF and passed
its offline inventory check. Native re-dumping exited zero, but the required
material CBI sidecar was absent. The operation failed before either independent
geometry or material/image reader ran. Its original transaction was restored,
then receipt publication independently failed on H1's unchanged 64-entry limit.
The same original reservation, handles and host were subsequently closed, with
Root independently corroborating the failure evidence and process absence.

[Sanitized measurements](../ops/model-lab/artifact.authored-platform-ff-d5.measured.json)
retain revisions and local text-evidence lengths/hashes. Process identities,
machine paths, raw receipts, native inputs and outputs remain outside Git.
[D4](AUTHORED-PLATFORM-FF-D4-2026-10-15.md),
[D3](AUTHORED-PLATFORM-FF-D3-2026-10-15.md) and the
[B2 standalone qualification](AUTHORED-PLATFORM-CPP-2026-10-15.md) remain separate.

## Actual FF result and failure

D5 froze assets `12926a0ab39cd14f0b03868590b0d2c6474c894b`, including PR187's
qualified-alias correction. Its Stage SDK31, Consumer SDK30, runtime SDK,
native Source and B2 writer pins remained unchanged. Reversing exactly three
finite D4-to-D5 namespace/revision substitutions recovered D4's caller bytes.
The admitted package's 54 Source tests had passed; they did not qualify this FF.

Five actual original job phases exited zero and confirmed tree closure:

| Phase | Purpose | Elapsed |
| --- | --- | ---: |
| `authored-stage` | SDK31 authored input stage | 338 ms |
| `authored-source` | Source/material closure check | 242 ms |
| `hud-build` | Native FF construction | 7239 ms |
| `hud-offline` | Offline asset inventory | 6478 ms |
| `hud-roundtrip` | Native re-dump | 6512 ms |

SDK31's accepted 4936-byte plan/3 had SHA256
`02285a22c7a10333dfb1d3593479cc2248c81eddf2eb90405f35a7ae7ddd19a1`.
The existing E7 candidate and 104 inputs from 73 stock providers were qualified
under the original admission: 95 hardlinks and nine copies. The transaction
created and subsequently removed its managed aliases and copied inputs.

The retained FF had SHA256
`6d7d18dd0aba97eb29c9372134996d8eca452191f865b16b263c960a57d00cdb`.
`InventoryVerified` became true. At `Build-ModelFF.ps1:485`, the required
`sdk_author_platform_material.cbi` was missing from the native dump, and
`Copy-Item` raised `PathNotFound,Microsoft.PowerShell.Commands.CopyItemCommand`.
Neither independent reader was started. Native exit zero and inventory success
therefore do not establish FF geometry, material/image bytes, ABI or appearance.

## Distinct publication failure after restoration

The actual transaction and entry both recorded restoration, and Source identity,
size, time and attributes were rechecked. `Restored` and `StockPreserved` were
true. The before-release publication then failed with
`Output entry count exceeded 64.` from `Measure-H1Output`.

That function counts all files and directories below its RunRoot. D5's Source
stage, author project, phase logs, dump, roundtrip, backup and metadata share that
namespace. The generic cap does not exempt these entries. Before recovery
publication, the full namespace contained 128 entries and 1,683,309 bytes,
without reparse points. This was a count violation, despite being below the
original 256 MiB byte limit. No native receipt or publication guard had yet been
created by the refused generic writer.

The original state deliberately remained `Failed`, with the primary CBI failure,
`RestorationStatus=Refused` and `CleanupError=Output entry count exceeded 64.`.
The reservation remained held because the original release tail was not reached.
Calling the entire restore function again would incorrectly require the aliases
that successful restoration had already removed.

## Same-original known-failure closure

The same physical persistent host retained its original AppDomain root,
PSVariables, context, state, five phase records, reservation and actual guards:
84 Source streams, 73 stock streams and 1109 outer Source streams. The outer
success-path root capture remained null because the entry had thrown; it was
not replaced from JSON.

Root and two independent reviewers approved a finite recovery Source helper.
It was invoked once. It rechecked the actual references, closed native owners,
restored paths, held input hashes and unchanged failure state. It captured each
actual guard handle before disposal, accepting a direct `SafeFileHandle` or a
`FileStream`'s actual handle and refusing other types before closing anything.
The actual D5 original guards were all FileStreams. Two separate Source fixture
tests checked mixed handle types and the bounded metadata publisher; neither
test invoked the main helper or touched the original host/reservation.

Three failure publications used `CreateNew`, enrolled their actual streams
before writing, called `Flush(true)`, and checked length/hash/JSON through those
same streams. Full RunRoot metadata accounting surrounded publication. The
4096-entry diagnostic traversal bound did not replace or raise H1's 64-entry
limit: the original violation remained explicit. The 256 MiB global byte limit
and combined one MiB metadata reserve were unchanged. The original 600-second
native group deadline had elapsed while the failed operation awaited review;
its elapsed value was recorded, with no new job, deadline reset or native retry.

After prepublication and final input checks, the helper closed the actual input
handles. It extracted only the exact three release statements from the loaded
original `Complete-ModelFFRestore` AST and executed them with the same state,
state path and original token. It did not replay restoration or call a manual
replacement release. The original state kept its failure and cleanup fields.

The final observation confirmed 1271 actual handles closed: stock 73, Source 84,
outer Source 1109, two material-metadata inputs and three failure publications.
All corresponding guard lists were empty; the actual lease and registry entry
were absent. Only the separate diagnostic root reported known-failed closure
and permission to exit. Original success/Ready flags stayed false.

Root personally read and hashed the publications before authorizing exit. A
dot-sourced exit script returned to the NoExit prompt; this was not counted as
host termination. The subsequent guarded interactive `exit 1` completed the
true PTY with exit code 1. The fresh inventory at
`2026-10-15T09:49:26.3249905Z` contained none of the seven original process
identities, game/compiler/VCTIP processes or resource leases. Root corroborated
closure before releasing its orchestration slot at
`2026-10-15T09:52:03.9648600Z`. Post-exit metadata used its own guarded write and
actual handle-closure check. No job kill, replacement owner/context, new lease,
FF retry or game operation was used.

## Material metadata and next Source corrections

Under the retained original admission, bounded projection read only the owned
Source and dumped material JSON, plus immediate related directory names.
Both JSONs were present with the same two constants, two texture entries and
state flags 57. The normal and authored-color entries retained semantics 15 and
14, sampler state 19 and their type hashes. This is metadata evidence, not an
independent material/image readback. No pixels or binary sidecar were reopened.

Both JSONs declare the literal property `techniqueSet->name`. The projector
looked for `techniqueSet`, so its projected name/type stayed null; it did not
capture or prove the actual property value. The observed constant-buffer and
state directory names matched the expected techset directory.

Source inspection identified a concrete hypothesis: D5's expected CBI and state
paths were 278 and 275 characters, while its material JSON path was 234.
Pinned native Source uses narrow `fopen_s` and can silently skip a sidecar when
opening fails. This is compatible with the observed short JSON, directories,
missing long-path sidecar and native exit zero. No actual errno or Win32 error
was captured, so a MAX_PATH failure remains a hypothesis, not a proven cause.

Separate Source changes must preflight effective native paths and inspect the
literal dumped JSON fields before copying all required sidecars. Required CBI
files must not be omitted or substituted with Source copies. A future short
Source package/RunRoot can retain the existing path-containment rules. The
ModelFF publication fix must bound its complete expected global namespace from
inputs/manifests before running; it must not choose a larger cap from D5's
observed count or weaken generic H1/qualified-alias validation.

Those fixes require their own review/merge, a fresh immutable package and a new
exact-tuple GO. Frozen D5 is not retried. No independent FF geometry/material
readback, rendered pixels, collision/contact or owner gameplay acceptance has
been established by D5.

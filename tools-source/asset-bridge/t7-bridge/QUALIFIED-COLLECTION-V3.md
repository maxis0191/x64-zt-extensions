# QualifiedCollectionV3: explicit larger bootstrap bounds

Source preparation dated 2026-10-12, based on reviewed commit
`22bbaa184c583c7d579b991def9b79c73b2a19e4`. This adds a separate opt-in policy;
it selects no real files and does not alter an existing V1/V2 plan or source pin.
The metadata inventory of available `*core*.ff` files is not an engine dependency
list or load order. No automatic scan, wildcard selection, next-zone expansion,
payload read, native run or resource admission is part of this change.

| Explicit policy | Items | Per-file maximum | Aggregate maximum |
| --- | ---: | ---: | ---: |
| QualifiedCollectionV1 | 1..8 | 32 MiB | 32 MiB |
| QualifiedCollectionV2 | 1..8 | 64 MiB | 128 MiB |
| QualifiedCollectionV3 | 1..32 | 512 MiB | 768 MiB |

Without a policy, the historical absent/single/exact-pair behavior remains.
V3 requires the existing MSG candidate profile and `Bootstraps` array. Every
name is literal, canonical and independently qualified, with distinct source,
alias, file ID, qualification receipt and qualification script. The existing
receipt lifecycle/metadata/hash requirements remain. No missing file is guessed.

## Bounds and publication order

`Get-T7CatalogueBootstraps` checks the entire collection before returning any
item. Each addition is preceded by `item <= totalLimit - currentTotal`, with
integer validation before conversion. Plan output sums also check remaining
int64 range before addition. The exact output budget remains:

```text
106,059,160 + actual candidate bytes + actual declared bootstrap bytes
```

At the V3 aggregate ceiling and the maximum 64 MiB candidate this is
**978,474,392 bytes**, below 1 GiB. For the 21,750,272-byte MSG candidate it is
**933,115,800 bytes**. These are output accounting limits, not RAM estimates or
filesystem quotas. A plan must use its actual sum, not the theoretical maximum.

V3 permits the existing formula `22 + 3 * itemCount` up to 118 bindings. Only
explicit bootstrap binary bindings inherit the 512 MiB per-file limit; other
binaries remain <=64 MiB and text <=1 MiB. Per-item qualification text remains
<=32 KiB. The runner's 128 KiB plan limit and 64-entry output-tree limit remain;
long paths/metadata may therefore constrain a particular plan below 32 items.

The unchanged runner validates plans and all qualification receipts before
execution. Under its existing admission, it guards inputs, checks bootstrap
identities, observes the requested zone and checks all original file IDs before
the first alias directory or alias. A late invalid item, sum, receipt or ID
collision must fail before alias publication. V3 creates no new publication path.

## Two deliberately different read paths

`Read-SteamSnapshot` retains its byte-array result and guarded-file contract.
Limits above 32 MiB require an explicit opt-in; `-Allow64MiB` stops at 64 MiB,
and limits above that require **`-Allow512MiB`**. The upper parameter limit is
512 MiB. Parameter gates precede path access; file metadata is bounded before
open, then length is rechecked under the read/share-read handle before allocation.

The body allocates **one array at the actual guarded file length**, not two
arrays at the requested ceiling. Reads never exceed the remaining array range;
short reads, an extra byte or changed length fail. Hashing and parsing consume
the same array, and the original handle stays retained. This is not constant
memory streaming: a maximum-sized snapshot still requires a 512 MiB array.

The catalogue requires hash guards rather than returned payload arrays. The
shared `Open-H1Pin` still has its original 64 MiB ceiling. After admission,
`Enable-T7CatalogueRuntimeProfile` installs a **V3-only, host-scoped adapter**:
`Open-T7CatalogueV3Pin` recognizes only exact declared bootstrap source paths
and their exact run-local alias paths, verifies the expected size/hash pin,
checks metadata before open and hashes through the retained stream. It allocates
no bootstrap-sized arrays. Unrelated inputs delegate to the unchanged shared
reader; V1/V2 do not install this adapter. The common helper and runner files
are untouched. Native file-ID checks remain in the original runner ordering.

## Memory and validation limits

The existing reservation remains **6 GiB physical / 8 GiB commit** and deadlines
remain 200/120/5 seconds. Neither estimate is reduced. Stream hashing avoids
retaining up to 768 MiB of bootstrap arrays in the catalogue host. Snapshot
qualification callers can still retain large arrays across passes: two retained
passes at the aggregate ceiling would alone represent 1.5 GiB of live arrays,
before PowerShell/GC, engine loading and decompression costs. This arithmetic
does not measure those costs or prove that a future V3 native run fits 6/8 GiB.
An exact future plan still needs the coordinator's GO, fresh admission and
runtime monitoring; this source policy cannot authorize that run.

Pure tests cover default/V1/V2 preservation, V3 item counts through 32, exact
512/768 MiB metadata boundaries and +1-byte failures, invalid integer types and
int64 maxima, exact output ceilings, late duplicate paths/IDs, receipt failure,
and rejection before subsequent runner reads/alias-directory creation. The
reader's maximum opt-in is tested against tiny authored text; no 512 MiB test
allocation occurs. The streaming adapter uses only small original bytes and
ordinary temporary files, with no hardlink, native ID provider, lease or game.

```powershell
pwsh -NoProfile -File tools-source/asset-bridge/t7-bridge/Test-SteamMetadataHost.ps1
pwsh -NoProfile -File tools-source/asset-bridge/t7-bridge/Test-T7CatalogueBootstraps.ps1
pwsh -NoProfile -File tools-source/asset-bridge/t7-bridge/Test-T7CatalogueBootstrap.ps1
pwsh -NoProfile -File tools-source/asset-bridge/t7-bridge/Test-T7Catalogue.ps1
```

On 2026-10-12 these suites passed 97, 443, 177 and 188 checks respectively
(905 total). All used synthetic metadata/original small fixtures; no native
process, real lease, owner-stock read or operational plan was created. These
results validate source behavior, not a large-file or engine run.

Review should focus on preserving the opt-in boundaries, restricting the runtime
adapter to explicit source/alias pins, pre-open/allocation bounds, exact aggregate
arithmetic and the unchanged global validation-before-alias order. Real large
input hashing, timing, engine compatibility and resource use remain untested.

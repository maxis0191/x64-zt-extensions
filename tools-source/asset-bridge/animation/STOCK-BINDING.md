# Shared FF stock observation binding

Use the existing **`iw7.ff-stock-observation/1`** JSON directly. There is no new
receipt format or rewritten restoration history. This observation is descriptive,
not a launch, stock-restoration or current content-verification result.

The common pure helper is
[`../common/StockBinding.Core.ps1`](../common/StockBinding.Core.ps1), shared by
Animation and Material adapters. No frozen provider helper was changed.

## Three immutable input receipts

| Input | SHA256 |
| --- | --- |
| Historical `model-lod1m-ff-build-20261007/state.local.json` | `4cf67ebe1645c6c0761b9a24cb4e4630edee9c5d737742c704d624fe60cb3850` |
| `agent-pair-inventory-20261007-v2/reviewed-stock.local.json` | `9116255ef148a324df15fa914795a7917615f023973111fdc39ae7329a9dcbf4` |
| First descriptive `stock-observation-20261012-0350.local.json` | `473766b743343bebe58a08bb2fdb30d1eb727aa5e7e6961da2ba1152c6f374bc` |

The reviewed-stock file is an array of `RelativePath`, `Length`, `SHA256`,
`Operation=NTFSHardLinkImmutableStock`. The observation binds its own canonical
StockRoot, the two historical hashes and exact 72-entry `Inputs`: `Relative`,
canonical actual `Source`, `Mode`, `Bytes`, `Attributes`, `ModifiedUtc`, `SourceId`,
`SHA256`, `ReviewedStockRelative`, and `ExternalToolDependency`. Its extra
descriptive fields are not accepted as proof in place of those checks.

The historical operations are **63 HardLink and 9 Copy**, not 71/1. All observed
IDs differ from the historical IDs; the rejected initial proposal to require ID
continuity was not run or committed as a valid stock policy. Retail content is
instead bound to the reviewed manifest: 71 entries / 40 unique physical files.
`main/*.ff` and `zone/*.ff` map to the reviewed root `.ff` name;
`zone/assetfile1.pak` maps to reviewed `assetfile1.pak`. Other retail paths remain
exact. The source must be that reviewed relative path under the observed root.

Only `tlsdll.dll` may be external: 113152 bytes, SHA256
`6e00dbe90e4ccb60283fad72a769b36542e587019a0da9fa42cb6a0fcf91207a`.
Its explicit canonical path and current ID remain bound to the observation hash.
No other outside source is accepted. No `Restored`, `StockPreserved`, `Transaction`,
`RetainedLeaseToken` or `TargetId` may be fabricated on this observation.

## Producer and caller contract

The inventory chat produces the observation; do not repeat its inventory, copy
assets or manufacture another receipt. Preserve all historical files unchanged.
After the coordinator-owned move to durable stock, use its new observation/hash;
the root is explicit and never hardcoded in the helper. For a later capture,
record real IDs in the existing NTFS helper representation
(`volume8hex:index16hex`) and real content hashes, times and attributes; write a
fresh observation and pin its SHA256. File ID alone is not content equivalence.

1. Hash and read the historical receipt, reviewed manifest and observation using
   the existing `Assert-BeaconHash` / `Read-BeaconJson` helpers.
2. Call `Get-FFStockBindingInputs baseline observation reviewed StockRoot
   baselineSHA256 reviewedSHA256`. This checks the data contract only, without
   filesystem inventory or content hashing. It returns exact historical `Mode`
   and observed metadata plus `ExpectedSourceId` / `ExpectedSHA256`.
3. For the existing 71-link/one-copy staging policy, preserve each returned `Mode`
   as `BaselineMode`, then set operational `Mode=HardLink` except the 77-byte
   `main/fileSysCheck.cfg`. This avoids copying 56198365 bytes of historical
   EXE/DLL/bootstrap inputs. Budget exclusion uses operational Mode only.
4. Under the complete 8/11 GiB admission, hold every input source guard and read
   actual IDs through the existing NTFS helper. Compare each via
   `Assert-FFStockIdentity entry actualId` **before** assigning `SourceId`. Then
   call `Assert-FFStockContent inputs`; it rehashes real bytes, deduplicated only
   by verified IDs, and rejects conflicting expectations. This is about 453 MB
   of reads over 41 physical sources, not additional stored stock.
5. The existing source metadata/NTFS and transaction helper checks still apply
   before staging and after restoration. A changed path, metadata, ID or content
   refuses the attempt; never overwrite the observed expectation with a new ID.

The sentinel source has ReadOnly attributes 33. Preserve that source. After
creating its own independent 77-byte copy, first prove its target ID differs from
the guarded source ID; only that owned copy may have ReadOnly cleared. Every
hardlink remains write/delete guarded. No stock attribute is changed.

## Animation parameters and evidence boundary

Keep the historical `StockReceipt` / `StockReceiptSHA256`, native XAB receipt,
candidate receipt, BuildJob/Python pins and frozen ProviderRoot. Set `StockRoot`
to the latest observation's root, add `StockBindingReceipt` /
`StockBindingReceiptSHA256` pointing to that observation, and
`ReviewedStockManifest` / `ReviewedStockManifestSHA256`. Concrete paths remain in
ignored local arguments. The common helper and all three receipt files enter
the run's source guards.

Plan mode returns `StockContentAndIdentityRecheckPending=true` and
`StagingCopyBytes=77`; it neither scans/hashes live stock nor loads native code.
The observed 72-entry contract was accepted using only the three small JSON
files. That does not establish that stock content/identity is still current.
Pure synthetic tests cover contract refusal, modes, expected IDs and tiny-file
hash drift. Independent source review and coordinator GO remain required before
the actual admitted recheck/build/verify/dump/read transaction.

This source tranche passed 24 common stock checks and 48 animation PowerShell
checks. The 49 Python checks belonged to the preceding adapter tranche; its
Python sources are unchanged here. No new native/FF result or lease is claimed.

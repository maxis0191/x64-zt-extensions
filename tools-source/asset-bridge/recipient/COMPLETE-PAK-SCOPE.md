# Complete asset-PAK scope proposal after F

This begins with the source and filesystem-metadata investigation archived in
`f57b530`. The preparation checkpoint below supersedes its then-unsupported
runner status; the original proposal JSON remains an unchanged snapshot.
F remains failed on `assetfile101.pak`, with confirmed original-job closure and
restoration of all 80 managed paths. Its GO is exhausted. The existing four/five
profiles and all earlier evidence remain unchanged.

## Recommended next route

Review a new explicit profile covering **all 33 existing, reviewed `assetfile`
PAKs in durable Doom**, retaining the original 72-entry FF/tool baseline. Pak1
is already in that baseline, so this means 32 additional `zone/` hardlinks.
The [fixed proposal](asset-pak-scope-proposal-2026-10-12.json) lists every name,
size and historical reviewed SHA256. That proposal JSON is not a runner receipt.
No wildcard, failure-driven append, new directory clone or payload copy should
become an execution input. A future implementation must accept only the exact
ordered scope and totals, preserve the previous profiles, and require a new
metadata observation bound to the fixed list, manifest and source identities.

This is the most direct way to cover the observed asset-file family without
developing and qualifying a retail FF dependency parser first. It deliberately
covers more than a proven minimal CP subset. It does **not** promise CP closure,
qualified references or absence of another kind of dependency failure.

## Measured inventory

The 2026-10-12 observation enumerated direct Doom-root files and opened them only
for filesystem identity. It read **zero retail payload bytes**, performed no
retail hash, and took 0.4289757 seconds for enumeration, metadata and manifest
comparison. The reviewed manifest has only root-level PAK entries. All 82 files
have a unique matching manifest row and expected length; none is missing or
marked read-only, directory or reparse point. No other root-level `.pak` name
was found. This is coverage of the retained reviewed stock, not proof that a
retail installation or a CP dependency set is complete.

| Family | Files / distinct NTFS IDs | Logical bytes | GiB | Reviewed rows |
| --- | ---: | ---: | ---: | ---: |
| `assetfile` | 33 / 33 | 4705977508 | 4.383 | 33 |
| `imagefile` | 49 / 49 | 43257601456 | 40.287 | 49 |

All per-file IDs, modification times, attributes and manifest comparisons are
retained in the ignored local `pak-inventory.local.json` (32,403 bytes), SHA256
`683C8A39B6BD289A2ACC0A27129A038361D5A217D6EF129D07DA739FEB6F76BF`.
The tracked proposal omits machine paths and NTFS IDs. The manifest SHA256 was
rechecked as `9116255EF148A324DF15FA914795A7917615F023973111FDC39AE7329A9DCBF4`.
Its content hashes remain historical expectations, not fresh retail hashes.

The new fatal's pak101 exists in that scope at 395,509,796 bytes. Its reviewed
expected SHA256 is
`919308F769389718621883149EC9801EAFAB8895E3A9E74AE73E1D702AA30B38`.
Finding it does not retroactively change F's result or qualify current content.

## What the pinned source can establish

Source pin: `fab935826c898806855376662a8a03317b3ad8f1` in the retained x64-zt tree.

- `src/zonetool/zonetool/iw7/zonetool.cpp:1853` loads the two available core
  techset zones, then available techsets/base/patch zones for code_post_gfx,
  global, common, global_mp, global_cp, common_mp, common_cp and cp_zmb,
  synchronously. The current baseline contains 31 distinct FF files; the bound
  explicit loader sequence expects 25 messages. Baseline coverage and zones
  actually loaded must not be conflated.
- `src/zonetool/zonetool/iw7/structs.hpp:12875` describes `XStreamFile` with
  offset, end offset, file index and localized flag. `XZoneMemory` distinguishes
  shared FF data from streamed images. `XFileHeader:12950` describes separate
  shared/image counts and stream tables before the length fields and compressed
  data. Its layout implies a 208-byte prefix and 24-byte records on this x64
  layout. That is source-derived structure, not a validated retail-file parse.
- `src/zonetool/zonetool/iw7/zone.cpp:1167` accounts for both table sizes, and
  writes image records at `offsetof(XFileHeader, fileLen)`. The writer sets
  `shared_ff_count=0`; it therefore does not validate retail shared-table
  interpretation or the native mapping of shared indices to `assetfile` names.
  The writer uses version 1619, signed `IWff0100` or unsigned `IWffu100` magic.
- `src/zonetool/component/iw7/imagefiles.cpp:16` advances native image stream
  records without opening image payloads in its replacement hook.
  `src/zonetool/component/iw7/zonetool.cpp:94` additionally patches an image-path
  opening site. These do not prove all PAK families are unnecessary: real
  assetfile fatals already disprove that interpretation.
- `src/zonetool/zonetool/iw7/assets/gfximage.cpp:553` explicitly opens
  `imagefile%d.pak` for streamed image export. The current reference check does
  not perform that image export. Asset/image file families must remain separate;
  exclusion of image payloads is a bounded proposal, not a verified CP success.

No qualified retained parser or complete CP asset-index list was found in the
searched recipient/model/HUD source and documentation. No FF header, table or
compressed payload was read during this investigation. The mapping from all
retail shared indices to native file requests remains unproved.

Source-file SHA256 pins, in the same order as the relevant files above:

| File | SHA256 |
| --- | --- |
| IW7 `zonetool.cpp` | F1C9FB861B81727DC7E3882F5116231E6DC0D1A0E6F5838953A62232171059BC |
| IW7 `structs.hpp` | ADB62E481A533D27F97829E64D9038B13C5E9CD88E6B4AEE8CAC339B9492921A |
| IW7 `zone.cpp` | A37B1698358D4A3AA9AE69155DC0E659F78E18E79E20DC7CA6A3F4FAE10CA675 |
| component `imagefiles.cpp` | DC6D3C1C5A6BF4072327754E50B42F263DB0B3F32BCA923BADAD44B56241F808 |
| component `zonetool.cpp` | BE37E50690C515FC116F0C6092F8DD361B973AA73F9B56FAF32EE457F3C90ED4 |
| asset `gfximage.cpp` | 71BA077CCA8727D7C79C61797463239C5B47E12D0F86774868737F71A7A003D1 |

## Proposed budget and limits

| Quantity | F's five supplemental PAKs | Proposed complete asset family |
| --- | ---: | ---: |
| Supplemental PAKs beyond baseline pak1 | 5 | 32 |
| Supplemental logical/hash-read bytes | 966557876 | 4695508096 |
| Exact supplemental limit | 966557876 | 4695508096 |
| Distinct total stock files | 46 | 73 |
| Total distinct stock hash-read bytes | 1419496893 | 5148447113 |
| Stock hardlinks + sentinel copies | 76 + 1 | 103 + 1 |
| Managed paths including candidate and requests | 80 | 107 |
| PAK payload copy bytes | 0 | 0 |

The increase is **3,728,950,220 hash-read bytes** over F. The baseline's 41
physical files account for 452,939,017 bytes, including pak1. The 77-byte writable
sentinel copy remains the only stock copy. NTFS metadata allocation is unmeasured
and is not claimed to be zero. Old 600 MiB, approximately 1 GiB, or five-file
limits cannot be reused. Including all image PAKs as well would instead raise
total stock hashing to 48,406,048,569 bytes; that is outside this proposal.

For 5,148,447,113 bytes, arithmetic hash-I/O scenarios are 49.10 seconds at
100 MiB/s, 19.64 seconds at 250 MiB/s or 9.82 seconds at 500 MiB/s. These are
**estimates, not measured throughput or completion promises**. Guard setup,
hash CPU cost, contention and native file reads add time. Native bytes read and
peak memory remain unknown; logical PAK sizes are not resident-memory sizes.

The initial reservation proposal remains 8 GiB RAM / 11 GiB commit, with fresh
complete admission, RAM reserve 0, the current 20% commit reserve policy and
runtime 85% commit-pressure stop. These remain estimates: F failed early and
did not measure peak CP loading. The next plan must explicitly review this
reservation for the larger loading scope and record actual peak memory.

Retain the 240-second native phase, 245-second job observation and 600-second
group active-work deadlines, plus existing 2 MiB log and 256 MiB generated-output
limits, only after review of the increased hash work. Hashing is streaming and
does not intentionally buffer entire PAKs. Existing content hashing and some
Win32 calls are synchronous; a deadline check after them is not a preemptible
I/O timeout. The largest proposed PAK is 944,406,564 bytes. No hard bound on
blocked filesystem calls, Stop or restoration is claimed. Do not silently raise
time limits or perform an automatic retry if the next attempt fails.

## Optional narrower index route

A separate source-only reader could be qualified on synthetic signed/unsigned
headers, exact table bounds, overflow, truncation, localized flags and invalid
indices before reading retained FF metadata. A proposed investigation cap is
1 MiB per each of the 31 baseline FF files, 31 MiB aggregate, with no decompression
or PAK read and a small fixed streaming buffer. This is a proposed cap, not the
actual table size. Files exceeding it must fail closed. Any eventual native
asset mapping inferred from these tables still needs validation against the
observed pak1/17/19/37/53/69/101 requests and complete load scope. No such reader
or retail-header operation is implemented or authorized for execution here.

The complete 33-file profile avoids that prerequisite. Before execution it needs
source review, immutable schema/list/budget checks, old-profile regression and
negative fixtures, Distribution binder agreement, a new exact source/plan/spec
and separately granted GO. Content hashes must then be verified under guards
inside fresh admission before staging. Success still requires the four exact
non-default reference results, original-tree closure, all 107 paths restored,
source preservation and released resources. Script bytes, package qualification
and gameplay remain separate gates. Coordinator owns central docs and GitHub
integration; this investigation launches nothing.

## Source preparation checkpoint

The coordinator subsequently authorized source and Plan preparation only.
`Recipient.Stock.ps1` now supports the distinct
`doom-reviewed-all-asset-paks-20261012` profile with observation schema `/3`, the
exact 32 ordered supplemental names and the exact 4,695,508,096-byte limit.
The earlier `/1` and `/2` profiles remain unchanged. No discovery or automatic
growth runs inside the producer. Budget calculation independently rechecks the
named ordered scope, rejecting substitutions even if total bytes were preserved.

The `/3` observation binds F's fatal SHA256
`67995123AB95D54DE3DDB9FFB0F52015DAA0978F3C782C977A7C9A3A3C9F58F3`
and the independent complete-inventory SHA256 above. The spec supplies
`RecipientCompleteInventoryReceipt` and its SHA256. Plan construction requires
the fixed hash, a bounded receipt of at most 128 KiB, then compares the exact
asset names, bytes, IDs, modification times, attributes and historical hashes.
The baseline pak1 must also match that inventory. The independent inventory is
added to `SourceHashes`, so execution would recheck and hold its normal read
guard. An earlier profile rejects these extra complete-inventory bindings.
Normal admitted live identity/content guards remain unchanged.

All 33 current source identities, lengths, timestamps and attributes still
matched the retained metadata inventory during preparation. No retail contents
were read. New checks pass for malformed/missing/mixed profiles, wrong F or
inventory evidence, missing/duplicate/reordered names, imagefile substitution,
unexpected names, copied PAKs, changed sizes/hashes/attributes/timestamps/IDs,
baseline pak1 disagreement and a changed live identity before staging.
Results: **59 complete-profile, 65 earlier-profile and 65 source/contract checks**.
These are synthetic/source checks, not a real restoration or reference result.

Two fresh PowerShell hosts produced the same references-only Plan: 104 stock
inputs, 107 managed paths, 73 distinct stock files, 5,148,447,113 stock hash-read
bytes, 20 source pins and 12 unchanged provider pins. The run root remains absent,
and `NativeExecuted`, `ClosureComplete` and `Ready` are false. The 8/11 GiB
reservation and 240/245/600-second deadlines are retained estimates requiring
review; no admission, staging, retail hash or native run occurred. Distribution
binder compatibility with this new profile remains an independent review gate.

Run the additional pure checks with:

```powershell
pwsh -NoProfile -File tools-source/asset-bridge/recipient/Test-RecipientCompleteStock.ps1 -StockBindingPath <reviewed-provider>/tools-source/asset-bridge/common/StockBinding.Core.ps1
```

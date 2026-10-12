# Recipient supplemental PAK profile after C

Source-only preparation, 2026-10-12. No new native run, stock copy, download,
game launch, lease or PAK content hash was performed during that preparation.
The separately authorized D execution and its limits are recorded below.

## Evidence and immediate cause

C's identity-verified, untruncated fatal names `assetfile17.pak`. Its 72 stock
entries included only `zone/assetfile1.pak`. Fresh metadata reads found pak17 at
the roots of both durable Doom and the base game: 104,595,492 bytes, modified
`2026-09-29T21:45:47.6718742Z`, attributes 32. Their NTFS IDs differ, respectively
`D088B64A:00140000000731F5` and `D088B64A:00330000000E2F41`. Equal metadata does not
prove equal bytes. The correction sources the durable Doom file; it does not
modify or stage from the occupied owner installation.

The reviewed retail manifest `9116255ef148a324df15fa914795a7917615f023973111fdc39ae7329a9dcbf4`
already contains pak17's expected content hash. The new observation records
current identities/metadata and those **historical expected hashes**. Fresh
content requalification occurs only inside the next admitted guarded run.

## Search route and limits

Retained tool source is `fab935826c898806855376662a8a03317b3ad8f1`:

- `check_enemy_references` calls `load_enemy_source_zones`; its explicit sequence
  includes `global_mp` before `global_cp`, `common_mp`, `common_cp` and `cp_zmb`.
  The same loader serves compiled-script export. The 25 available zone entries
  and native commands remain unchanged.
- `game/iw7/structs.hpp` declares `SF_PAKFILE=4`; `symbols.hpp` binds native
  `Sys_CreateFile` at `0x140CFDF50`. The retained IW7 source does not contain that
  engine routine's implementation or the fatal string, so a complete native
  filename-search trace is not claimed.
- `component/iw7/imagefiles.cpp` invokes the retail image-stream routine at
  `0x1409E7450`. `component/iw7/zonetool.cpp` has existing image-stream patches,
  including a comment about skipping pak opens. C demonstrates that those
  comments do not establish that this command requires no asset PAKs.
- Historical HUD code stages the observed PAKs under `zone/`. The retained
  `hud-build-pak17-only-20261006-224750` receipt proves identical source/target
  identities for `zone/assetfile17.pak`, followed by a real fatal naming pak19.
  This supplies empirical support for the selected alias; no new engine patch,
  pool change, `global_mp` bypass or speculative alternative alias is introduced.

The historical pak17-only receipt hashes to
`EFA6F49458B1E09FAC51E522D1F73342311CCB717AD838780AFD2ECED26D4146` and records failed
verification but confirmed restoration/source preservation. It remains intact.

## Four observed prerequisites, not a complete inventory

The existing [HUD dependency record](../../../ops/hud-lab/bootstrap-dependencies.json)
(path relative to repository root: `ops/hud-lab/bootstrap-dependencies.json`)
hashes to `8CFBAFB748C438A133F972841328CD0B9E1865073FD4583CF9CD09BF35E31850`.
It pins the same tool source and records these successive CP-context fatals:

| PAK | Historical failing run | Bytes | Expected SHA-256 from reviewed stock |
| --- | --- | ---: | --- |
| 17 | `hud-build-generic-inventory-20261006-224500` | 104595492 | `6F5C0D1937B5A707D4E1FB3009F68A827714D9E4A72FF2D6570B57DBF6B0F058` |
| 19 | `hud-build-pak17-only-20261006-224750` | 418201636 | `064B6D23CFCEC2BAEDF1A5589FCD602FB1CFBDBB2040D88D21CB8A8CA7779B0D` |
| 37 | `hud-dependency-retry1-20261006-225100` | 53477412 | `839C1DA30E43B9C5C78CC457D3FA3EF61BD85AE818C81A2D2D0B30FF187FB349` |
| 53 | `hud-dependency-retry2-20261006-225200` | 3817508 | `B0C4AC18F4F9965A396B74CE8FBE2118D6FD6F68D92E7295AD29BC7BC2FBF773` |

Fresh durable metadata matches all four reviewed sizes; their IDs are stored in
the local observation. Only pak17's failure was reproduced by Recipient C. The
historical HUD success subsequently used Bootstrap/pak1 only and explicitly did
not establish CP closure. These four dependencies are evidence-based additions,
not a fresh retail inventory or a guarantee that no further prerequisite exists.

## Binding, preservation and budgets

`Recipient.Stock.ps1` accepts exactly the ordered four-entry
`observed-cp-paks-17-19-37-53` receipt. It requires the pinned reviewed manifest,
canonical sources directly under the configured stock root, exact `zone/` target
names, hardlink mode, expected hashes/sizes, valid observed NTFS IDs/timestamps,
and ordinary non-read-only, non-reparse file attributes. Extra, duplicate, moved
or reordered inputs and metadata receipts claiming acceptance/restoration fail.
No wildcard enumeration or automatic dependency expansion exists.

The shared 72-entry FF profile and all 12 provider pins are unchanged. New entries
flow through the same original transaction, read-sharing guards, identity check,
deduplicated SHA-256 verification and metadata checks **before staging**. Each
staged hardlink must have its source's exact identity. Restoration follows
confirmed original-job closure and checks recorded source/target identities;
unknown closure retains the existing quarantine/lease behavior. No PAK attribute
is changed. Only the existing 77-byte sentinel is copied and made writable.

| Budget | Proposed reference plan |
| --- | ---: |
| Baseline / supplemental stock entries | 72 / 4 |
| Supplemental logical and hash-read bytes | 580092048 (about 553.2 MiB) |
| Supplemental ceiling / copied bytes | 600 MiB / 0 |
| Total distinct stock hash reads | 45 files, 1033031065 bytes |
| Stock hardlinks / sentinel copies | 75 / 1 |
| Total managed paths including E7 and two requests | 79 |
| Admission RAM / commit | 8 GiB / 11 GiB |
| Generated-output stop / each log limit | 256 MiB / 2 MiB |

Hash-read bytes are sequential source reads, not a RAM allocation or generated
output. Verified hardlinks stay exempt from generated-byte accounting. The
additional resident-memory cost and reference-phase peak are unmeasured; the
8/11 admission estimate is not a measured upper bound. Existing fresh memory
checks and the 85% commit stop remain. The plan has no PAK hash or native side
effects; Plan fields explicitly leave content and resident-memory verification
false. A fresh deadline/memory check follows admitted content hashing before
directory creation and staging.

## Review checkpoint

39 new pure fixtures pass, covering path traversal/root escape, exact scope,
duplicate/reordered/missing inputs, read-only/reparse refusal, metadata/content
mismatch, false acceptance fields, alias disagreement and byte accounting.
The 39 source/contract fixtures also pass, including the real pre-staging budget
function with in-memory doubles for directory/memory observation. They do not constitute a
real restoration or reference-resolution test of this new overlay.

The prepared plan is references-only, retains the existing 240/245/600-second
phase/job/group active-work deadlines and requires a fresh run root. It does not
run the utility phase. A separately reviewed GO and fresh shared admission are
required before one native attempt. Subsequent acceptance must include the exact
four non-default reference rows, original tree closure, all 79 staged paths
removed, preserved stock, released lease and unchanged owner/Main identities.
`Ready`, package closure, script-byte validation and gameplay acceptance remain
false. Coordinator owns integration and the GitHub workflow.

## D execution checkpoint

The [D record](native-validation-d-2026-10-12.json) supersedes the pending-execution
status above. One execution of `fde8c49` passed fresh 8/11 admission and the
existing guarded pre-staging SHA-256 gate. All four supplemental source/target
identities matched. Native loading progressed to `global_cp`, then a verified
Fatal Error title prompted immediate original-job stop. The light observer did
not read control text; the new failure cause is unknown. No accepted references
or complete stock closure were established.

Original root exit 122 and zero members, removal of all 79 managed paths,
restoration/source preservation, final source metadata, unchanged owner/Main and
zero remaining owned processes/leases were confirmed. No content rehash outside
admission was performed after restoration. No retry or PAK expansion is allowed
by D's exhausted GO. The next source-only change captures future exact fatal
text in normal reference mode; it cannot reconstruct D's missing body.

## Explicit 4+1 profile after E2

The [E2 failure](native-validation-e2-2026-10-12.json) independently captured
`Could not find asset file assetfile69.pak` with verified original identity and
no text truncation/read error. The native log still ended at `global_cp` and was
byte-identical to D. The pinned `load_enemy_source_zones` includes `global_cp`
in its explicit synchronous sequence after `patch_global_mp` and the available
`techsets_global_cp`. Its source SHA remains
`F1C9FB861B81727DC7E3882F5116231E6DC0D1A0E6F5838953A62232171059BC`.
This links the new request to the observed loading interval; it does not assign
a serialized asset owner or establish a complete native filesystem search trace.
The old HUD record does not name pak69. E2 supplies this dependency's evidence.

After E2's independently confirmed closure and the separate proof commit,
read-only metadata inspection found `assetfile69.pak` directly under both the
durable Doom root and base-game root:

| Property | Durable Doom | Base game |
| --- | --- | --- |
| Bytes | 386465828 | 386465828 |
| NTFS ID | `D088B64A:001000000007343B` | `D088B64A:000B0000000E2FAC` |
| Modified UTC | `2026-09-29T21:46:16.7968839Z` | same |
| Attributes | 32 | 32 |

The pinned reviewed retail manifest already contains pak69, with expected SHA256
`042C8D62A3A24ACD21A5502A5A111E6E426E870505DA3CDD62ADA3C3A23C496F`.
This is a historical expected content hash, not a fresh hash of either file.
Equal metadata and differing identities are not a current content-equality proof.
The proposed source is durable Doom; the base installation is not staged from.

The new metadata receipt is **schema `iw7.recipient-stock-observation/2`**, profile
`observed-cp-paks-17-19-37-53-69`. It requires exactly five ordered `zone/` aliases,
with the same fixed root, reviewed size/hash, identity, attribute and hardlink
checks. `AdditionalDependencyEvidenceSHA256` must bind the original E2 fatal
record `867E858ECD4BFFDE50A04E62488E42B73F528177E0E01B51A081BC030DBBB280`.
Every returned input records its explicit `StockProfileId`; mixed profile IDs
cannot choose a byte budget. The original four-PAK `/1` schema, profile, receipt
and 600 MiB ceiling remain valid for their original scope and are not rewritten.

`Get-RecipientSupplementalProfile` has only these two named cases. It does not
infer a profile from a count, enumerate a directory, append a missing PAK on
failure or accept a caller-supplied ceiling. Unknown profiles, cross-schema
receipts, missing evidence, a sixth entry, changed names/order and mixed budgets
fail before staging. The new local observation reads only the five explicit
files' metadata and historical expected hashes. Actual SHA-256 requalification
remains inside fresh admission and existing read guards before any staging.

| Budget | Original four-PAK profile | New explicit 4+1 profile |
| --- | ---: | ---: |
| Supplemental logical/hash-read bytes | 580092048 | 966557876 |
| Additional pak69 bytes | 0 | 386465828 |
| Supplemental ceiling | 629145600 (600 MiB) | 966557876 (exact observed total) |
| Supplemental payload-copy bytes | 0 | 0 |
| Total distinct stock hash-read bytes | 1033031065 | 1419496893 |
| Distinct stock files | 45 | 46 |
| Stock hardlinks + sentinel copies | 75 + 1 | 76 + 1 |
| Managed paths including E7/requests | 79 | 80 |

The new total is about **921.78 MiB**, so the old 600 MiB ceiling cannot be reused.
Hardlinks add directory entries to existing payloads, not another 386,465,828-byte
copy. NTFS metadata allocation was not measured and is not claimed to be zero.
The single 77-byte mutable sentinel copy is unchanged. Logical/hash-read bytes
are not a measured resident-memory cost: the 8 GiB RAM/11 GiB commit plan remains
an estimate requiring fresh admission, existing pressure checks and future
measurement. No new allocation peak or complete stock sufficiency is proven.

65 pure stock fixtures pass, including old-profile regression, exact five-PAK
budget/zero-copy accounting, schema/profile confusion, missing or incorrect E2
evidence, unsupported sixth inputs, wrong pak69 metadata and mixed budgets.
The 65 source/contract fixtures also pass. Two fresh PowerShell hosts produce an
identical source-only plan with 77 stock inputs and 80 managed paths. That plan,
the new observation and spec are separate ignored artifacts; no PAK was staged,
copied or rehashed and no lease/native run occurred during preparation. Further
review and a separately authorized slot/GO are required. E2 remains failed and
restored, and none of its proofs are amended into a five-PAK success.

## F execution checkpoint

F subsequently executed the five-PAK profile once after its own review/GO and
fresh admission. Its guarded hashes/staging passed, but native loading failed
with the exact captured `Could not find asset file assetfile101.pak`. Stdout
remained at the same `global_cp` boundary as E2. The [F record](native-validation-f-2026-10-12.json)
confirms the original job closed and all 80 paths were restored/removed, sources
and Main preserved and zero owned process/lease remaining. This proves neither
complete CP stock nor accepted references. No sixth entry or retry is introduced.
The next investigation assesses the complete existing asset-PAK scope and its
newly measured read budget before any further profile proposal or admission.

The resulting [complete-scope investigation](COMPLETE-PAK-SCOPE.md) identifies
33 reviewed asset PAKs and 49 separate image PAKs using metadata only. It proposes
an explicit all-asset list with 5,148,447,113 total stock hash-read bytes, without
authorizing a run. The later source-preparation checkpoint in that note records
the distinct `/3` runner profile, independent inventory binding and pure tests.
Its exact Plan still requires review and a separately granted GO.

## H execution checkpoint

The subsequent reviewed Plan H executed once on source `e0654a74`, using schema
`/3` and the complete fixed asset-PAK profile. All 25 expected zones loaded and
the four exact requested references were verified without missing/default rows.
[H's evidence](native-validation-h-2026-10-12.json) confirms original-job closure,
107 paths restored/removed, source preservation, unchanged owner/Main identities
and zero remaining process/lease. The stock profile suffices for this recorded
reference check; its minimal dependency subset, image export, scripts and package
closure are not established. Earlier profiles and failures are unchanged. No
additional native operation follows from H's exhausted single-execution GO.

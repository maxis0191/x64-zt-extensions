# Fixed link/lookup V3 consumer

The V2 native capture exposed `DB_AddXAsset` delegating to the link function
outside its fixed capture window. V3 observes that code band and two lookup
anchors before component post-unpack, then exits before hooks or zones.
It does not establish provider identity, failure cause, ABI compatibility,
catalogue readiness or successful game loading.

The existing `Run-T7PrepatchReferenceV2.ps1` entry accepts exactly two finite
profiles through its reviewed plan: V2 and `t7-prepatch-link-v3`. The shared
H1 lifecycle, corrected physical EXE/managed `pwsh.dll` argument check,
create-only publication ordering and original-host closure remain in place.
There is no second runner or native host framework. V2 source/CPP pins,
captured outputs and closure witnesses remain unchanged.

## V3 observation contract

| Row | Site RVA | Window RVA | Bytes |
| --- | --- | --- | --- |
| DB_LinkXAssetEntry | `0x1D7960` | `0x1D4F00` | `0x4000` |
| DB_FindXAssetHeader | `0x1D5FB0` | `0x1D5FB0` | `256` |
| DB_IsXAssetDefault | `0x1D7260` | `0x1D7260` | `256` |

The first window ends exclusively at `0x1D8F00`. Total code bytes are 16,896.
Region coverage starts at the window RVA; `.pdata` containment uses the site
RVA. Separate lookup rows preserve each anchor's function metadata even though
their code overlaps the large band. Report schema is
`iw7.t7-prepatch-link-observation/3`, with a 4 MiB read bound, 2 MiB `.pdata`
bound and 256 KiB report bound. No address selector, scanner, recursive callee
capture, provider/data dump or zone operation is accepted.

## Source transition

The consumer validates exactly 14 build-profile fields and 10 marker fields.
The V3 helper is 15,827 bytes / `cf839e18a68adb4ed3aae82d683ef110ab595fa8c172584e47ca4d11bb8db48d`;
adapter 2,236 / `66f70ca5a979745288232d76496a339e08d639ddf34560aada6e6b63c5bcffa1`;
prepared main 14,469 / `84cde2924df0a0553dd2cddb0ca173aed54af43d6874b06718c01d1a6cec4989`.
Its base is the immutable **wired** V2 main, 14,524 / `e719365c5a7f407218a7218bd9c7090421934042c34a9f163d9a8e3d42ee1e28`,
under the original V2 recipe `0aca63cb09e8ecfc96dee34e1fdf94f8cb66e400f8a190ffdefd38bec3a2c549`.
Retained C plan/receipt and V2 helper/adapter pins remain literal. Mixed
V2/V3/catalogue/export/parts markers and array/string coercions are refused.

## Initial source-only gate (historical)

At this checkpoint V3 has no qualified CPP receipt, executable tuple or six
original build-closure pins. A V3 plan must contain explicit null values for
`CandidateSource`, `CandidateSHA256`, `BuildReceipt`,
`ExpectedBuildReceiptSHA256` and `BuildClosedPins`, with `CandidateBytes=0`.
The source recipe is a bounded guarded text pin named by the reviewed plan.
DEFAULT checks the source marker/profile, private paths, original input
metadata and stopped Main/bank metadata shape. It returns
`PlanCheckedPendingInstrumentedCandidate`, without native types, binary reads,
lease, candidate alias or attempt/publication output.

`-Run` for V3 fails explicitly before scheduler import or admission. Populating
an arbitrary candidate/receipt/index cannot enable it. After a real producer
CPP and its original-host/actual-exit/independent-absence proofs, a separate
reviewed change must qualify the closed tuple and executable capsule. A Root GO
for the eventual capture is still separate from source validation.

## Source validation

`Test-T7LinkV3Report.ps1` passes 25 fixed-window, region, metadata and schema
controls; `Test-T7LinkV3Consumer.ps1` passes 91 source pin, scalar, exclusive
profile and pending-candidate gate controls. Affected V2 tests pass 168 consumer
controls, 11 causal publication controls and 34 real managed-host controls.
These source tests execute no native candidate, acquire no lease and read no
opaque input. The real managed-host test observes natural PowerShell exit 0
and subsequent process absence; it is not a native V3 test.

The first shared-plan refactor flattened a singleton PowerShell pin row. The
causal publication test refused it; the corrected explicit nested array passes.
No failed native attempt or heavy reservation resulted.

The actual pre-merge DEFAULT uses consumer source `b442fefb9c2a0e33b5685a80edb886d3272392bd`
(code `1b7c839`) composed into the local `plv3a` packet, 919 text files /
8,935,424 bytes. Its producer source recipe is 304,645 bytes /
`ba777867ec8f3516cabf7ee22b64416d85f3066ca1091c9a32f804144191b965`,
from producer head `9338d143033cb652df5003d3bdf7c61f2eccd497`.
Consumer plan `e6718acf843ec12e4b6a5c82150f8a7131973f3909c904969fcac3708c4f161f`
binds 17 text files and 6 opaque metadata rows. Fresh NoProfile parent imports
no project helpers and invokes the actual entry directly without `-Run`.
Child PID 3404, created `2026-10-14T07:34:00.1557426Z`, exits naturally 0;
its original process reports `HasExited=true`, empty stderr and all six
DEFAULT execution/read/write/readiness flags false. Subsequent CIM lookup
confirms that PID absent. Candidate, attempt, host-start, host-postflight and
report paths remain absent. These local bounded JSON witnesses stay ignored;
no game content or native dump is committed. This is pre-merge source evidence,
not a qualified executable capsule.

Next at that source-only checkpoint: close the consumer source PR and fresh
DEFAULT capsule, then qualify the producer's real CPP tuple before proposing
an executable V3 capture capsule.

## Actual closed CPP qualification, 2026-10-14

The later, separate CPP used the new OS-context recipe 305,621 bytes /
`e484cef7415b2697c188b0202f3771af15377ecb56d98a0a85bfc1d2418fe530`.
Its original 17,200-byte receipt is
`0cc0c8b6b46fd75d09c53b3e3c3dc9af40aa4211a786629fcf2f791c52111328`.
Main/link exit 0, original compiler jobs and VCTIP members close, inputs are
reverified and admission releases. Original host 25996 / parent 23872 and
compiler/VCTIP IDs 19408/27020/8216/24704 are subsequently absent, with no
heavy process or lease. Actual PTY 85134 exits 0, chunk `aa25c2`; never poll it.

The EXE tuple observed under that original lease is 21,777,408 bytes /
`d89c4cf326f21038d9fbcc6a18c18db2c17c17f448400a8567ee2e5fdca6a8bb`.
The PDB observation is 136,982,528 /
`d45781dc051dd5ed2fc57c86b093296207c7623b8810df9ecd04f08851a648c3`.
These values are copied from the closed receipt; this consumer qualification
does not read or rehash either file. The six-role index is 2,189 bytes /
`b13107f072b164640a4344d8281df79b5b2f3fc1ee229813764ce7e55159e4c2`,
schema `iw7.t7-prepatch-link-v3-closed-pins/3`. Entry, completion, actual tool
exit, independent inventory, original build receipt and closed bundle have
distinct literal text pins. V2's original tuples and index remain unchanged.

The consumer now accepts only this measured V3 candidate/recipe/receipt/index
cohort, with the original source profile/marker and dated OS proof. Generic
Passed receipts, mixed V2 tuples, running compiler members and incomplete
closure evidence cannot qualify it. Earlier null drafts and old recipes retain
their original source-only status; they are not rewritten or relabelled.

`-SourceOnly` on the existing runner performs actual V3 source/closed-cohort
checks without operational preparation. It requires the future runtime to be
absent, opens only guarded source/closed JSON text and skips opaque metadata
queries for the unprepared aliases. Main/bank metadata is shape-checked only;
live preservation checks remain mandatory in the operational path. It returns
`SourceCohortCheckedPendingPreparationGO`. Combining `-SourceOnly` with `-Run`
fails before any plan guard, scheduler import, type load or admission.
V2 cannot select this new source-only mode.

This separation supports source/default ownership review while the coordinator
has not authorized capture preparation. Later ordinary DEFAULT still requires
fresh private directories, aliases and current metadata. Native execution still
needs the exact original NoProfile/NoExit host and a distinct capture GO; CPP
success supplies no ABI, boot, provider, catalogue or gameplay acceptance.

Affected authored checks pass 39 closed-cohort controls and 91 existing V3
source controls; the unchanged V2 consumer and causal publication controls
pass 168 and 11. These checks use source/synthetic objects only, no native
candidate, real admission or opaque input.

Actual pre-merge source-only entry validation uses code
`d6e5cbc472e6c001734e8bacdd4769b6135af5fc`, composed as local `plv3d`
(959 text files / 9,365,169 bytes). The new active source plan is 36,485 bytes /
`409d2852ac01f982a954de7156d12609ef90318327eebade58c31167617fcd56`,
with 25 guarded text pins and 7 opaque tuples copied from original observations.
Fresh NoProfile parent imports no helpers and directly invokes the entry with
`-SourceOnly`. Original child 12604, created
`2026-10-14T11:44:13.8933384Z`, naturally exits 0 and reports
`SourceCohortCheckedPendingPreparationGO`, candidate bound, no native types,
binary hashes, lease, files created or readiness. Subsequent independent CIM
lookup confirms the child absent and the future runtime still absent. Bank and
retail metadata are not refreshed; operational preparation/capture remain
unauthorized. The earlier d904 null draft and frozen V2/E5 files are intact.

## Merged source and operational preparation, 2026-10-14

PR #100 merged as `3f3cb55283f591f1976f1c4c7caf37a474e00eaa`.
Its fresh source package contains 960 text files / 9,384,002 bytes. The merged
source-only plan is 36,485 bytes /
`c8380f5b40201c2b86857122e4c9394c09b63bbe320b8cea399c71c40539d630`.
The actual `-SourceOnly` child 27548, created
`2026-10-14T12:10:35.8407095Z`, exits naturally 0, returns the source-qualified
pending-preparation status and is independently absent. Its future runtime
remains absent at that checkpoint; no operational preparation is inferred.

A separate authorized Analysis reservation then performs exactly two owned
PowerShell phases: operational plan preparation and ordinary DEFAULT.
Preparation refreshes Main/bank metadata and creates only two engine/Steam
hardlinks; it copies no game bytes, creates no candidate alias and reads/hashes
no opaque content. The existing scoped original-owner helper is reused.
Unconfirmed creation/wait/termination retains the original owner/context/lease
and NoExit host; no process adoption or second host framework is introduced.

Independent source review found that the original local outer required an
Int32 parent PID, while the real JSON round trip returns Int64. That local A
packet remains immutable and unexecuted. The B correction accepts only scalar
Int32/Int64 values in `1..Int32.MaxValue`, without permissive casts; exact live
parent PID, image and UTC creation identity comparisons remain intact.
The causal source fixture reproduces A's refusal and passes B's real JSON
round trip with 14 invalid mutations rejected (17 checks total). The existing
host exit gate passes 7 controls; original-owner cleanup passes 5 cases.
These fixtures do not acquire a real lease or execute preparation.

Actual B preparation records parent 25920 before original NoExit host 5920.
Owned preparation child 6824 and ordinary DEFAULT child 2740 both exit 0 under
one Analysis lease. DEFAULT returns `PlanCheckedPendingGO`, candidate bound,
with typed false values for native types, binary hashing, lease acquisition,
files created and readiness. The real operational plan is 36,491 bytes /
`f9a2e6f0e741ffe5c09212f5cc509cb317eb56394d1ddfdd3d4b3c51721a2b3f`;
the generated capture packet is 2,068 bytes /
`4b5978e34b49a716ce8784f07b1ccc6a939d2b391ee36793df48c30833d85700`.
Neither artifact grants capture authorization. Preparation's original context
closes, its lease releases and the true PTY exits 0 (chunk `b1973e`). Fresh
`2026-10-14T12:44:38.8580316Z` inventory confirms all four original IDs absent,
no heavy process and no lease. Main remains stopped with unknown cause and
68 bank metadata entries unchanged; bank contents are not read or modified.

## Actual fixed-window capture, 2026-10-14

A separate reviewed capture GO consumes that exact operational plan once.
The original parent 25860 is recorded before fresh NoProfile/NoExit host 11456;
the existing runner validates physical `pwsh.exe`, actual managed `pwsh.dll`
entry and all ten arguments. One Extract lease covers input rechecks, candidate
alias creation, the bounded native capture and final input revalidation.
Native 21508, created `2026-10-14T12:52:28.4250853Z`, exits naturally 0 after
2,072.013 ms. It captures the three fixed windows above, totaling 16,896 code
bytes, at the first DPI callback before component post-unpack. Total bounded
reads equal returned bytes at 676,760, including PE metadata and 54,927 `.pdata`
records.

The original report is 38,323 bytes /
`95d489a706885eec2723a4fcbeeb30c2686abc82cc0010151d02c0aa94a7e4e1`;
run receipt 4,868 /
`1554c017e2ce2d2a4bb637177890912850f2d69ded705b7924acfcee2b531e70`.
The report records `capture_complete=true` and `captured_for_offline_review`;
the receipt records `CaptureOutcome=CaptureComplete` and wrapper status
`CaptureCompletePendingReview`. Original job closure is confirmed without
forced termination or quarantine. Inputs are reverified under the original
lease, original input metadata is unchanged and aliases are retained. No
opaque content is read or rehashed after lease release.

The same original host confirms its original Context, State and Guards
references, original owner closed with exit 0, zero wrapper guards and no
lease before exiting. Host postflight is 1,498 bytes /
`4e462074af0638d38eb2a27cdd2e0dad2d03957e560397f48b3564ef0c9728ee`.
True PTY 12108 exits 0, final chunk `b64cc1`; it is closed and must never be
polled again. Fresh `2026-10-14T12:55:08.7021082Z` independent inventory finds
parent 25860, host 11456 and native 21508 absent, with no heavy process or lease.
The 1,942-byte independent witness is
`fc451041fead6297457ad06709f4fb8e9f4d467ff2bb142e78bd76b9e0a30127`.
Main/bank preservation remains confirmed by the original before/after and host
postflight metadata checks; Main's stopped state still has unknown cause.

A later closed-JSON summary command incorrectly used `Measure-Object` on
OrderedDictionary rows and failed before publishing its summary card.
Explicit scalar addition corrected only that summary; no native replay or
new admission resulted. All original capture and closure artifacts remain
unchanged, along with the null drafts, source-only plans and V2/E5 evidence.

This result proves the requested bytes and metadata were captured. It does
not establish Link/Find/IsDefault semantics, image-header validity, provider
identity, ABI/runtime compatibility, boot, catalogue, textures or gameplay.
The native ABI, runtime-compatibility and boot-authorization flags remain typed
false, as do wrapper compatibility/readiness. Reports and machine-specific
operator controls remain ignored; no dump, asset, binary or symbol is committed.

Next: independent bounded review of the closed JSON and its source references.
Any actual disassembly process or other heavy analysis needs a separate reviewed
Analysis GO; no replay, new hook or downstream native operation is authorized
by this capture result.

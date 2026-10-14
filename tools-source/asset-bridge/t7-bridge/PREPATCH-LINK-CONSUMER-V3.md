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

## Source-only gate

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

Next: close the consumer source PR and fresh DEFAULT capsule, then qualify the
producer's real CPP tuple before proposing an executable V3 capture capsule.

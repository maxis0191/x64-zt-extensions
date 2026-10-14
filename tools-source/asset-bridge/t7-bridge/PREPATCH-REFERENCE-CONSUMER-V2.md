# Fixed reference prepatch V2 consumer

`Run-T7PrepatchReferenceV2.ps1` and `T7PrepatchReferenceV2.Profile.ps1` consume
only the separate V2 producer. V1, C1/C2 and RunCatalogue remain unchanged.
The native command is exactly `-t7-prepatch-reference-v2`, with report
`t7-prepatch-reference-v2.local.json` and observation schema
`iw7.t7-prepatch-reference-observation/2`. No zone or address selector exists.
The report must contain DB_AddXAsset RVA 0x1D4600/2048 bytes and
Load_SimpleAsset RVA 0x1DB2B0/256 bytes in that order.

The producer cohort is immutable: source `2f74c974`, recipe SHA256 `0aca63cb`,
closed receipt 16885 bytes/`77e7fecf`, six-closure index 1867 bytes/`cfb6f523`
and executable 21777408 bytes/`f11c683b`. These tuples come from the original
admitted compilation; source preparation never rehashes the executable/PDB.
The consumer requires the original main/link closure, exact twelve-field
build profile, ten-field source marker and six guarded closure JSON records.
Singleton arrays cannot substitute for strings, integers or lifecycle booleans.

The assigned Main baseline is Stopped, with cause Unknown. Before and after
the probe, its original PID/image and UDP 27016 must be absent. PID reuse,
an inaccessible same-name image or a port owner refuses the operation.
Read-only file and bank directory metadata must match the local reviewed
snapshot; bank contents are not read. Machine paths, bank names and snapshots
belong in the ignored operational plan, not this repository.

H1 still owns admission, original creation handles, registration, deadlines,
telemetry, confirmed teardown, quarantine and receipts. The 6/8 GiB estimates
are observations under the existing telemetry-only scheduler, not capacity
minima. The V2 profile retains a 200-second group, 120-second native deadline,
2 MiB .pdata bound, 4 MiB total capture reads and 256 KiB report. It validates
only the two reported ranges and their memory/.pdata metadata; it performs
no disk PE scan, disassembly or callee following.

DEFAULT validates source/text pins and binary metadata without a lease,
provider load, binary hash or native launch. PowerShell 7.5+ JSON decoding
preserves literal UTC strings explicitly. A fresh NoProfile DEFAULT must
qualify the real entrypoint and its final plan before the coordinator's GO.
Run requires the exact fresh NoLogo/NoProfile/NoExit command. Same-host
postflight exposes CanExit only after original tree closure, lease release,
zero wrapper guards, native absence and preserved Main metadata. Actual PTY
exit and a subsequent independent absence witness remain separate obligations.

Source tests cover fixed/scalar selectors, closed build fields, exact argv,
complete/partial/missing reports, window and region bounds, guarded output,
literal UTC JSON and stopped Main/port/bank conflicts. No test starts a
candidate or loads the native provider. Native capture and interpretation
still require a separate GO; ABI, provider ownership, boot and catalogue
compatibility are never inferred from source checks or CaptureComplete.

Source verification on 2026-10-14: 168 targeted controls passed without a
provider/process/lease or opaque input read. Code source `334fd8da` composed
903 text files/8784857 bytes. The actual entrypoint in a separate fresh
NoProfile child naturally exited 0 and reported PlanCheckedPendingGO with
CandidateBound true and all native-type/binary-hash/lease/file-creation/Ready
flags false. Its parent imported no project helper, the child Process was
disposed after exit and subsequent CIM observation confirmed absence.
The 1337-byte DEFAULT witness SHA256 is
`f3270378ade58870400bd62ec782b3068b345ce2c23ebddbfbf31c2d3b1cd8a0`.
The prepared plan used 30 bindings (23 text/seven binary metadata), two
hardlinked engine/Steam aliases, no copied game bytes and the closed producer
cohort above. This is source/metadata qualification, not a native probe GO.

An initial test-fixture expression unwrapped its supposed singleton array;
the fixture was corrected to assign a real array before the passing run.
The preparation helper's first parse refused before creating outputs; its
parenthesis correction preceded the create-only preparation. These failures
did not start a native process or consume a probe attempt.

Peer review of the initial consumer found a deterministic Run-only refusal:
it published its own host-start marker before repeating the create-only
validation. DEFAULT legitimately passed without that marker. The final
validation now occurs after admission and before publication; the exclusive
CreateNew marker and refusal of existing attempts remain intact. Eleven
causal checks execute the actual post-admission prelude on synthetic file
metadata, then reproduce the old-order refusal by moving only that validation.
No lease, provider or native process participates in these checks. The fixture
runs its extracted prelude as a file to retain the real PSCommandPath semantics.
The initial code/package/plan and DEFAULT witness remain historical and do
not qualify the corrected consumer. Prepare a new source/plan and fresh
entry DEFAULT before the final review and any separate probe GO.

Corrected code `06b6046f` composed a new immutable package of 904 text files /
8799440 bytes. Its new 30-binding plan SHA256 is
`7ac228ffe598acfb291aacde17637e9dd96550defebe3b51bca7ab665fba2d92`.
The actual fresh NoProfile entry child naturally exited 0 with CandidateBound
true and all five runtime flags false, then was absent in CIM. The new
1337-byte DEFAULT witness SHA256 is
`da835df6cc80c8739054349baee896eab48dc77374e97a6f3eb0a2115f4ec86a`.
The producer executable and all closure tuples remain unchanged. No probe
has run; the coordinator's separate GO remains required.

The first authorized wrapper invocation refused its managed-host arguments
before admission, native types, host retention or attempt creation. The physical
image was the pinned pwsh.exe, while Environment.GetCommandLineArgs()[0] was
its CLR pwsh.dll. Arguments 1 through 10 matched the exact command. Original
source guards were observed zero; PTY 49316 actually exited 1 (`67ab89`), and
fresh absence confirmed original host 13684 absent, no heavy process or lease,
and the unchanged stopped Main / 68 bank metadata entries. No binary or mapped
window was read, and this launch did not consume a native capture.

The validator now checks the physical host image separately and binds managed
argv[0] to the actual EntryAssembly.Location at the same runtime's pwsh.dll.
Every flag and operand at positions 1 through 10 remains exact. A real fresh
NoProfile/NoExit source-only host passed 34 controls, including changed physical
image, foreign assembly/DLL, singleton arrays and every changed argument.
Its natural exit 0 and subsequent absence were observed. Neither a lease nor
the native provider/engine participated; this is launch-model verification.
The old source/plan/refusal remains frozen. A new source DEFAULT and reviewed
capsule must precede a renewed coordinator probe GO; the CPP cohort is unchanged.

Corrected launch code `fca00698` composed 913 text files/8873153 bytes. Its
actual fresh NoProfile DEFAULT child naturally exited 0 and was subsequently
absent, with CandidateBound true and all five runtime flags false. The new
30-binding plan SHA256 is
`a9f7ea00efeb619366dfe660995ef8e3504cc6ab8800ac93469e72d2b863564c`;
the 1337-byte witness SHA256 is
`0c353409a7e7cfc56c5d15c92aec256e1aca9e09d496dc0615cb39033f8e8b8f`.
This source qualification leaves native capture and interpretation pending.

## Actual V2 capture, 2026-10-14

The renewed coordinator GO consumed one real V2 capture with operator merge
`c70342ff`, frozen plan `7e0b7153` and unchanged producer `2f74c974` /
executable `f11c683b`. Fresh preflight found no heavy process or lease and
preserved the stopped Main, its executable metadata and 68 bank entries.
No bank contents were read, no game bytes were copied and no zone was loaded.

Native 2968, created at `2026-10-14T06:47:21.6594255Z`, naturally exited 0
after 1620.7073 ms. The outcome is `CaptureCompletePendingReview`, separately
from compatibility or catalogue acceptance. The 8504-byte report SHA256 is
`dd0d10a895ec9c42c1d4e7c87e812fab527e8ca4650e1aa67154530c64ee47d7`.
Its phase is first DPI before component post_unpack. Source and mapped base
both equal 0x140000000; 662164 requested bytes were returned completely,
including the bounded .pdata observation of 54927 records and two fixed windows:

| Window | RVA / captured bytes | Observed runtime-function range | Unwind RVA / header |
| --- | --- | --- | --- |
| DB_AddXAsset | 0x1D4600 / 2048 | 0x1D4600–0x1D46F6 | 0xFB5038 / 11180600 |
| Load_SimpleAsset | 0x1DB2B0 / 256 | 0x1DB2B0–0x1DB2CE | 0xFA5904 / 01060200 |

The local report retains all raw hex. These ranges and headers are observations;
unwind-format, ABI, provider ownership, boot and runtime compatibility remain
unproven. The original native result/inputs, aliases and metadata were reverified
under admission. Source/opaque input bytes were not rehashed after release.

Original host 11420, created at `2026-10-14T06:47:18.5186933Z`, completed
same-host postflight with tree closure, lease release and zero wrapper guards.
PTY 86499 actually exited 0 (chunk `ff1969`). Fresh absence at
`2026-10-14T06:49:27.3382826Z` confirmed both original identities absent,
no heavy process or lease and preserved stopped Main/bank metadata, cause Unknown.
The native receipt is 4880 bytes/SHA256
`97546ab8f47bc8daa342eefb95b1e933f31b20bcecb99536be79b09df17de1b3`;
the independent completion proof is 7357 bytes/SHA256
`883f357812068c0ebb6c7eba37ca64fe68abf92f58be4359ea63cb728f499d77`.
The preceding managed-host refusal remains separate and preserved. This consumes
the single native GO; the next action is bounded interpretation of the retained
two windows, not another probe, compiler run or dependency-zone guess.

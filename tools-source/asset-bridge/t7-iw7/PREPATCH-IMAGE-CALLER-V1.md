# One bounded prepatch image-loader caller

This Source mode reuses the existing prepatch reader, first-DPI rendezvous,
exclusive flushed report writer and immediate exit. It observes the single
runtime-function interval containing callsite RVA `0x1B1E5D`, to support a later
review of RCX/a1 provenance and stores before the GfxImage wrapper. It does not
read a GfxImage, call an asset lookup, enable Link, load a zone or follow a callee.

The known call target RVA `0x7DB4C0` is already recorded by
`prepatch-comparison-20261012.json`. It is a concordance check on the E8 rel32
inside the selected caller, never another code window or discovery objective.
The old V2/V3 captures, helpers, wiring, reports and interpretation stay immutable.

## Finite capture contract

The sole flag is `-t7-prepatch-image-caller-v1`, with no address or size selector.
The report is `t7-prepatch-image-caller-v1.local.json`, schema
`iw7.t7-prepatch-image-caller-observation/1`. The existing invocation check binds
fresh output before load_binary; capture happens once at
`first_dpi_before_component_post_unpack`, then exits through the existing hook.

The existing guarded reader validates the named mapped image, PE metadata,
section extents, MEM_IMAGE allocation and readable regions. It reads at most
2 MiB of exception-directory metadata within its 4 MiB cumulative budget. Exactly
one valid, ordered, non-overlapping runtime-function record must cover the fixed
callsite. No nearest-function, guessed prologue or fallback is allowed. The
selected function must be at most 8192 bytes and contain the whole five-byte call;
these checks happen **before any caller code copy**. Missing, ambiguous, invalid
or oversized metadata refuses. The copied function must contain E8 at the exact
site and its signed rel32 must resolve to the already known target RVA. A mismatch
refuses completion. The target function is never read.

Only that complete caller body and its existing four-byte unwind-header prefix
are collected, alongside the existing bounded PE/region metadata. The unwind
format remains unqualified. Report size stays at 256 KiB. The range selector and
call guard are shared with a 25-case authored C++ fixture, including 8192/8193,
missing/ambiguous ranges, malformed metadata, truncated call, opcode/target drift
and signed-displacement cases. No compiled result is claimed by these Source
fixtures or their contract pins.

## Existing build path

`--prepatch-image-caller-v1` requires its paired
`--prepatch-image-caller-v1-base-plan`, the immutable 305621-byte V3 Source plan
`e484cef7415b2697c188b0202f3771af15377ecb56d98a0a85bfc1d2418fe530`.
Only its exact 14469-byte wired main is imported; namespace/include rebinding
produces main 14557/SHA256
`2ff1c104f8dfc99432179b289a0453aa1a81b8a99703803fcede1869fae61133`.
The retained failed C group keeps its failure status and supplies only the same
previously successful CLI/xpak sub-stages. No old runtime qualification is moved
onto a new input path.

The recipe uses the existing runner/H1 host, original-job and VCTIP policies:
caller fixture Compile 120 s, fixture Probe 15 s, main Compile 120 s, link Link 120 s.
The Probe must exit zero with exactly
`IW7_T7_PREPATCH_IMAGE_CALLER_CHECKS=25` plus LF/CRLF and empty stderr before main
can compile. Group 600 s, output 256 MiB and metadata reserve 1 MiB stay unchanged.
The closed profile has 18 fields, including typed Source/response pins; the new
transition has 10 fields. Mixed V2/V3, catalogue, export or provenance selections
refuse. DEFAULT reports Source pending, CPP unqualified, null candidate and false
execution/hash/admission/readiness flags. An eventual real receipt records its
fixture pass separately; it does not rewrite the input plan or Source marker.

The fixture response is capped at 16 KiB and read from the actual held bootstrap
Source stream. Before admission, the existing response tokenizer compares the
whole 18-argument vector with the producer's fixed source, include, flags and
output paths. A response with the right path and a matching updated hash is not
sufficient. Extra or nested responses, changed source/flags/includes/outputs,
malformed quoting and an oversized response refuse before compiler creation.
The producer emits UTF-8 without BOM. Strict UTF-8 decoding never switches
encodings from a BOM; repinned UTF-16LE/BE and UTF-32LE/BE responses refuse.

## Closed CPP25 checkpoint - 2026-10-15

The immutable Source package from [PR #200](https://github.com/maxis0191/x64-zt-extensions/pull/200),
merge `408af1d5f51469cca9b27128bedc895383aeee29`, completed actual preparation,
ordinary DEFAULT without `-Run`, the full pre-admission Source audit and a
separately authorized four-stage C++ build. The prepared plan is 312105 bytes,
SHA256 `8cd3dbdfeb6100e47509abf9621e087109fe522bf94e1bc9e97fbb970ad85fc3`.
Its measured inventory is 1083 Inputs and 87 bindings: 80 Source text, one
historical OS-proof text binding and six opaque metadata bindings. The generated
fixture response is 1193 bytes, SHA256
`5cd1f496bcb97a3c5080c3e68be7213f469097b3cb3482d460150748baae3822`.

The actual fixture compiled and exited zero with exactly
`IW7_T7_PREPATCH_IMAGE_CALLER_CHECKS=25` plus CRLF and empty stderr before main
compiled. Fixture Compile, fixture Probe, main Compile and Link all exited zero;
all three compiler/link telemetry records confirm root exit zero, no active
processes and empty original jobs. Group elapsed time was 21187.291 ms and maximum
observed output was 184309458 bytes, within the existing 600-second/256-MiB budget
and 1-MiB metadata reserve. Inputs were reverified; the before-release and final
receipts were flushed and read back. The same original physical NoExit host,
AppDomain root, PSVariable/context/state/guard references and owners remained
available through closure. Input, publication and caller Source guards closed,
the lease released, then the original PTY actually exited zero. Fresh observations
confirmed both host/parent and all four stage identities absent, with no game,
compiler/link, VCTIP, PDB server or heavy lease remaining.

The following pins are retained evidence, not a request to reopen binary files.
EXE/PDB pins were captured under the build lease and copied from its receipt;
neither binary was reopened or rehashed for post-release handoff or this document.

| Evidence | Bytes | SHA256 |
| --- | ---: | --- |
| Final build receipt | 28426 | `c07888de31c7700875b2acdb44fa01d26dc294e9deb751f93569e81e092f48b6` |
| Before-release receipt | 28385 | `ada38eb88ae718de1c1e228e0dc879e20ae28cac8f3e4f1ea0ea03917d64deda` |
| Original pre-exit proof | 35666 | `76d0506c50802d6fb0d59b3b3ba6beed82a2b9e330055360f7b7d43a571fa80a` |
| Post-exit proof | 29022 | `7bc7283bbdf25a1036824c0ea07992391cf05fa24ac62cb53dc606c833d18790` |
| Actual Source handoff | 31898 | `7d5f0b784ac700d838b36dc9c9e3fd998a185e1f574be422e328e4b789e06529` |
| Candidate `zonetool-t7.exe` | 21780992 | `f2712242fa0c544e77b313d808f3487bce89a2d8578ff079e6e140764fe93e9e` |
| Symbols `zonetool-t7.pdb` | 137023488 | `152c0f94217605b31ac323e715d36beb054cf9506aed74b57898b9ad4638fb7a` |

The real receipt records `ImageCallerFixturePassed=true`, Probe `Checks=25` and
`Status=Passed`. It has no top-level `ImageCallerCPPQualified` field; none is
invented. The immutable plan and Source marker keep their pending/unqualified
values. The candidate has never executed, no caller capture/native report exists,
and consumer adoption plus a separate Root native-capture GO remain required.
Compiled boundary checks do not qualify unwind interpretation, runtime image
reading, a GfxImage ABI, a writer, authentic texture payload or gameplay.

### SourceKnownLimit for this exact plan

The instrumented actual-runner prefix reached its real admission boundary with
78 bounded Source files verified and 1090 metadata queries satisfied in memory.
Provider imports/admission were excluded, with no actual runner entry, lease or
opaque filesystem access. Six mutations were refused by the real pre-admission
validators: OS date, prepared-main pin, same-path repinned `/W4` to `/W3` response,
dispatch option, singleton profile array and duplicate binding. An independent
review confirmed the unchanged baseline and the response/profile/dispatch cases.

The additional `opaque-as-text` diagnostic was blocked by the audit harness's
Source whitelist, **not** by a demonstrated runner classification guard. The
legacy non-multisurface branch returns before the publication family's binary
classification check. This is not a seventh production refusal or a general
classification/filesystem/reparse qualification. Root accepted this explicit
limit only for the immutable plan SHA256 above, whose six known opaque bindings
were independently checked as `IsText=false`; its 81 text bindings are the 80
Source files plus one historical proof. Any changed plan needs a new review.
The CPP capsule, audit and actual handoff retain this limit. No package, plan or
Source guard was silently rewritten to conceal it.

## Interpretation and execution limits

Function bytes can support instruction-level provenance and stores within this
interval. They do not prove live a1 values, allocation lifetime, scratch reuse,
the GfxImage ABI/stride, a default/provider identity or authentic texture payload.
If the writer is outside the function, the result must say so; there is no
automatic interval expansion, scan, lookup or callee following.

The closed CPP checkpoint above supersedes the initial uncompiled status for
that exact tuple only. No native report exists and no decoder was replayed. A
closed successful CPP tuple precedes consumer adoption and a separate
native-capture GO. No additional PE/retail read, lease, game or deployment is
authorized by this document or the Source capsule.

The first Source candidate's negative controls exposed PowerShell's pipeline
enumeration of a singleton profile array before the local object check. The
correction checks the original plan property itself before accepting this mode;
the original failing candidate and correction remain separate commits. No
preparation, compiler or capture ran from that candidate.

Source validation after correction passes 11 targeted Python tests and 169 actual
PowerShell profile/input/fixture-output controls. Retained V3/V2 controls pass
48/100, OS controls 39, input-binding controls 132, deadline controls 3 and the
registration-bindings controls 144. Shared build/registration Python checks ran
43 cases: 35 passed and 8 integrations were skipped because their separate retained
inputs were not supplied. This does not credit a compiled fixture or native test.

Review of the second Source candidate found that a self-repinned response could
change the compiled fixture despite its fixed filename. The correction above
keeps that candidate in history and adds 15 real authored-response mutations.
Each retains correct metadata/path/pins, reproduces acceptance without the new
guard, then requires the actual held-stream/token refusal through both profile
and input validation. A further encoding check found that automatic BOM detection
could override the stated UTF-8 decoder. Four additional encoded responses
reproduce acceptance with only that old detection flag restored, then require
the strict decoder's refusal through both validators. No compiler or capture ran
from either reviewed candidate.

# Caller-v1 adoption through the existing prepatch runner

`Run-T7PrepatchReferenceV2.ps1` now selects the finite
`t7-prepatch-image-caller-v1` protocol alongside unchanged V2/V3 protocols.
It uses the existing H1 owner, host, environment, output and closure machinery.
There is no new host or factory. This route exits at first DPI before zone load;
it does not pass through the Catalogue runner's zone/bootstrap path.

The native invocation has argc2: image plus the sole literal
`-t7-prepatch-image-caller-v1`. There is no address/size selector. The fixed report
is `t7-prepatch-image-caller-v1.local.json`, capped at 256 KiB. Caller mode adds the
existing functions-only Catalogue profile as a guarded Source dependency for its
typed metadata and report helpers. Other modes retain their earlier dependencies.

## Exact actual CPP cohort

Source PR200 merged408af1d and native Sourcefab935 produced a real closed CPP25
tuple; [the producer checkpoint](../t7-iw7/PREPATCH-IMAGE-CALLER-V1.md) retains the
preparation, audit, closure and known-limit evidence. This receiver binds only:

| Text or artifact metadata | Bytes | SHA-256 |
| --- | ---: | --- |
| Actual recipe | 312105 | `8cd3dbdfeb6100e47509abf9621e087109fe522bf94e1bc9e97fbb970ad85fc3` |
| Actual build receipt | 28426 | `c07888de31c7700875b2acdb44fa01d26dc294e9deb751f93569e81e092f48b6` |
| Actual CPP handoff/index | 31898 | `7d5f0b784ac700d838b36dc9c9e3fd998a185e1f574be422e328e4b789e06529` |
| Candidate metadata captured under lease | 21780992 | `f2712242fa0c544e77b313d808f3487bce89a2d8578ff079e6e140764fe93e9e` |

No PE/PDB was opened to author or test this adoption. Source408 and nativefab
remain the compiled revisions even after later receiver changes. Old V2/V3
candidates cannot be relabeled. The four stages are caller fixture Compile,
fixture Probe, main Compile and Link. The real receipt must have
`ImageCallerFixturePassed=true`, Probe25 with EngineInvoked=false, four exit0/
closed jobs and completed compiler/link telemetry. The candidate must match the
actual Link artifact. No top-level `ImageCallerCPPQualified` receipt field is
invented; the immutable Source marker retains its earlier values.

The handoff/index must bind the actual recipe/receipt/candidate and original
closure facts. The inherited Source classification limit is explicit: this
exact recipe's six opaque metadata bindings were reviewed as IsText=false;
the opaque-as-text mutation was denied by an audit harness, not a demonstrated
generic legacy runner guard. Adoption does not turn it into a seventh production
refusal or general filesystem/reparse qualification.

## Bounded observation

The new report decoder requires strict UTF-8, object root, depth<=25, no duplicate
fields and no trailing JSON. It reads bytes through the report's original held
H1 guard and resets its position; it does not open a second unguarded stream.
Existing V2/V3 JSON paths are unchanged.

The closed caller DTO is derived from the pinned producer. It checks the original
PID/generation, mapped module/PE bounds, one full pdata function containing
callsite RVA1B1E5D, length5..8192, unwind prefix4 with format still unqualified,
readable MEM_IMAGE region coverage and exact code hex length. The E8 instruction
inside the copied interval and its signed rel32 must agree with known target
7DB4C0; the target is never read or followed. Partial reports require native exit2;
complete reports require exit0 and return `CallerCapturedForOfflineReview`.
The existing runner's validation/finalization gates use that selected protocol
outcome before `CaptureCompletePendingReview`; V2/V3 retain `CaptureComplete`.

All boot, runtime-compatibility, ABI, writer, GfxImage payload and outside-interval
claims must remain false. A structurally valid report does not establish live
RCX/a1 values, scratch reuse, allocation lifetime, authenticated image identity,
pixel payload or Ready. A writer outside the single interval remains unknown.
The JSON is not claimed tamperproof without the existing H1 process/input proof.

Authored tests cover bounded reports, interval/call/coverage mutations, false
claims, strict JSON and wrong/incomplete/forged CPP metadata. A separate Source
replay validated the three actual recipe/receipt/handoff JSON texts without
creating a runtime plan or opening the candidate. No native report has been read
or captured by this adoption. Fresh receiver Source, a separately reviewed
Analysis preparation/ordinary DEFAULT and a separate Root Native GO remain
required before executing this mode. No zone, lookup, image body, XPAK, DDS,
payload, game or deployment operation is authorized here.

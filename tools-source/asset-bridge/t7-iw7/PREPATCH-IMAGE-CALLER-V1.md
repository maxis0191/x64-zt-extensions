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

## Interpretation and execution limits

Function bytes can support instruction-level provenance and stores within this
interval. They do not prove live a1 values, allocation lifetime, scratch reuse,
the GfxImage ABI/stride, a default/provider identity or authentic texture payload.
If the writer is outside the function, the result must say so; there is no
automatic interval expansion, scan, lookup or callee following.

This is Source authoring only. The C++ fixture and new candidate are uncompiled,
no native report exists and no decoder was replayed. A reviewed immutable Source
package, actual preparation and full pre-admission Source audit precede a distinct
CPP GO. A closed successful CPP tuple then precedes consumer adoption and a
separate native-capture GO. No PE/retail read, lease, game or deployment is
authorized by this document or the Source capsule.

The first Source candidate's negative controls exposed PowerShell's pipeline
enumeration of a singleton profile array before the local object check. The
correction checks the original plan property itself before accepting this mode;
the original failing candidate and correction remain separate commits. No
preparation, compiler or capture ran from that candidate.

Source validation after correction passes 11 targeted Python tests and 150 actual
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
and input validation. No compiler or capture ran from the reviewed candidate.

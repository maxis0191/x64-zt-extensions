# Native source-checksum correction proposal

This is a private source patch and a review proposal, not a rebuilt ZoneTool.
No native compiler, linker, librarian, probe, FFmpeg or ZoneTool was run for this
correction. The failed first SAB/FF attempt remains unchanged. The independent
reader still rejects its checksum. Playback and `Ready` remain false.

The subsequent [Seal C checkpoint](INPUT-SEALING.md) qualifies the retained input
bytes. The [private executable Build Plan B](BUILD-PLAN.md) now has a source-only
launcher and mock verification. It still requires separate review and native GO;
the earlier preparation descriptions below are historical proposal evidence.

## Observed defect and source boundary

The original 34-byte FLAC STREAMINFO contains 18 metadata bytes followed by the
opaque 16-byte PCM MD5 `24fe5af1473ea8f4be33912348210c78`. The retained E7 SABL
instead contains `78000000000000000000000000000000` at offset 110592. This is not
an endian permutation: fifteen nonzero digest bytes have been lost. The separate
compressed seek/frame payload and its checksum already matched before the strict
reader rejected the PCM checksum. See the sibling
`sab-ff-checkpoint-2026-10-12.json` for the failed native run and closure evidence.

At native revision `fab935826c898806855376662a8a03317b3ad8f1`, the IW7 writer calls
`block_buffer.read_buffer(info.md5sum, 128)` at `sound_bank.cpp:2767`, then copies
the sixteen bytes to `source_checksum`. The total of 128 bits is correct. Inside
`common/utils/bit_buffer.hpp:34`, however, every one of the sixteen loop iterations
calls `read_bits<uint8_t>(num_bits)` instead of reading one byte. The first read
advances from bit 144 to bit 272; the remaining fifteen reads are out of range and
return zero. The one-line patch changes that inner width to 8, so sixteen reads
consume exactly 128 bits and preserve the original MD5 byte order.

The unpatched implementation also converts `pow(2, p)` to `size_t` for exponents
outside the 64-bit range. The Python cursor/low-byte model explains the observed
E7 output, but does not emulate this nonportable C++ arithmetic. The native probe
has not yet established its precise behavior under a fresh compiler invocation.
No broader arithmetic change is included in this patch.

`source-contract.json` pins the exact original header, implementation and writer
as both retained raw bytes and Git LF bytes. Their three exact local copies total
123061 bytes under `runtime/content-surfaces/original-sound-checksum-source-a`,
with the original source-relative paths. They were compared to Git at the pinned
revision. They contain no retail stock. The native checkout remains unmodified.
The private patch passes `git apply --check` there; it has not been applied there.

## Regression evidence and pending native probe

`test_native_checksum.py` contains six passing source-model tests: pinned original
STREAMINFO and failed receipt, the old cursor overreads, sixteen correct byte
reads, exclusion of an endian-only explanation, conservation of an original
generated seek/frame payload, and the one-line patch plus strict reader boundary.
The field-conservation test starts a new synthetic fixture with an intentionally
different field and verifies exactly sixteen changed byte offsets. It never
edits a retained native SAB or any original source asset.

`checksum_probe.cpp` is an uncompiled reproduction using the exact upstream
header and implementation together in one translation unit. It parses the same
STREAMINFO metadata fields, calls the actual `read_buffer`, and reports the
returned digest. Its generated in-memory envelope checks the target field and
conservation of every other byte. It does not implement or validate native SAB
serialization; the original seek/frame equality is covered by the Python fixture.

After a separate reviewed GO, compile the probe twice with the same pinned x64
MSVC release settings: once against the archived original source and once against
an isolated patched copy. Each uses its own object, executable and debug output.
The original mode is `--expect-observed-corrupt`; the patched mode is
`--expect-original`. Preserve a differing original result as evidence of the
arithmetic/compiler boundary; do not weaken the test or reader to hide it.
Only the patched mode returning the original sixteen bytes supports the fix.

## Smallest proposed consistent ZoneTool candidate

The shared native checkout, H1's `runtime/zt-full-a`, its E7 EXE/PDB, all 413
objects, PCH, compile PDB and existing dependency libraries are frozen. H1 and
Engine ownership was checked through the coordinator. No shared write is
authorized. The proposed fresh output is `runtime/zt-sound-md5-b` in the sound
worktree; it did not exist at source review. The complete native build and SAB/FF
run both remain NO GO. The coordinator controls the native slot; sound has no
reservation. The latest coordination moved the active GO to Recipient H.

The source include scan finds six direct consumers of `bit_buffer.hpp`:

| Source relative to the native checkout | Candidate output |
| --- | --- |
| `src/zonetool/zonetool/h1/assets/loadedsound.cpp` | `obj/loadedsound.obj` |
| `src/zonetool/zonetool/h2/assets/loadedsound.cpp` | `obj/loadedsound1.obj` |
| `src/zonetool/zonetool/iw6/assets/loadedsound.cpp` | `obj/loadedsound2.obj` |
| `src/zonetool/zonetool/s1/assets/loadedsound.cpp` | `obj/loadedsound3.obj` |
| `src/zonetool/zonetool/iw7/assets/sound_bank.cpp` | `obj/sound_bank.obj` |
| `src/common/utils/bit_buffer.cpp` | `common/bit_buffer.obj` |

The five ZoneTool consumers are original source units, not one of E7's five
patched overlays. Recompile all five, plus the common implementation, against the
new header; do not mix old inline definitions with new ones. Make a new private
`common.lib` from the thirteen object inputs in its retained librarian command:
the new bit-buffer object and twelve unchanged common objects. A bounded archive
metadata read (2702 bytes) identified exactly thirteen distinct members, including
one `bit_buffer.obj`; all retained object files exist with matching lengths.
Their bytes have not been requalified. Before rebuilding, prove each of the twelve
unchanged inputs equals its member in the old archive; afterward prove the new
archive contains those same twelve payloads and the one replacement. Stop on any
mismatch. This avoids relying on ambiguous append/remove semantics and needs no
copy of the old archive or unchanged objects.

Use a tiny source overlay, with the patched header before the original common
include directory. Compile the common implementation from its private copy so
its quoted `bit_buffer.hpp` include resolves to the patched sibling. For the
five other units, retain source locations and all include paths/definitions from
their actual E7 command records, adding only the private common overlay first.
Record compiler include dependencies and reject any use of the original
bit-buffer header. Verify the include graph and recorded dependencies before
accepting 408 objects as unaffected. The source scan did not find this header in
`std_include.hpp` or an additional header consumer; this is source evidence,
not a substitute for compiled dependency evidence.
The similarly named object in `shader-tool.lib` belongs to its separate
`deps/shader-tool/include/shader-tool/utils/bit_buffer.hpp`; its source and
project include paths were checked. It is not a consumer of the patched common
header and is not included in the six-unit rebuild.

Disable PCH use for the six replacement units (`/Y-`) and use new `/Fo` and `/Fd`
paths. This avoids copying or updating the shared 277938176-byte PCH or its
43798528-byte compile PDB. Preserve x64 MSVC 14.44.35207, Windows SDK 10.0.26100.0,
the recorded release language/ABI/CRT/optimization flags, `/MT`, `/O1`, `/Zi`,
`/bigobj`, and one compiler at a time. The common unit uses the common command's
definitions, not the ZoneTool-only `EXPERIMENTAL_IW7` set. This recipe has not
been compiled, so include/self-containment or warning failures must be reported
and reviewed rather than solved by weakening checks.

Link the 408 unaffected E7 objects read-only, the five replacement objects,
unchanged resource input, the new common library and seventeen other unchanged
libraries. Keep E7's five existing source-overlay fixes through their retained
objects. Do not invoke its full MSBuild project, which could rebuild shared
outputs. Preserve the recorded link flags; explicitly isolate EXE, PDB, import
library, temporary files and any incremental state. Use `/INCREMENTAL:NO` for
the candidate. Shared compile PDBs may be read by the linker; they require
read-only guards and before/after identity checks. A missing or changed input
invalidates this reuse plan, rather than authorizing a full rebuild.

The existing full preparation helper describes 413 units and 18 libraries; it
does not validate this incremental recipe. An isolated preparer, exact input
manifest, command review and closure/accounting adapter remain to be completed
before requesting execution. No executable build command is authorized by this
document. `build-proposal.json` records the bounded proposal and these gates.

## Separate commands prepared for review, not execution

The local `runtime/content-surfaces/original-sound-checksum-build-review-a`
contains two small private patched source files, twelve complete response files
and `command-review.local.json`: 102218 bytes total. No candidate output directory
was created. The 12475-byte JSON has SHA-256
`75ad217b9841856a7401785fef53b8281e3b80e26bf5525e37e8250ee2826ce9`.
It records fourteen proposed invocations, with exact executable and response-file
paths, individual response hashes and the four retained command-record hashes.
Its status is `NOT_RUN_NOT_EXECUTION_READY`; it is not a runnable execution plan.

The separate stages are:

1. `cl.exe @probe-original-compile.rsp`, then
   `link.exe @probe-original-link.rsp`, then the original probe with
   `--expect-observed-corrupt`.
2. `cl.exe @probe-patched-compile.rsp`, then
   `link.exe @probe-patched-link.rsp`, then the patched probe with
   `--expect-original`.
3. Six independent compiler invocations using `compile-loadedsound.rsp`,
   `compile-loadedsound1.rsp`, `compile-loadedsound2.rsp`,
   `compile-loadedsound3.rsp`, `compile-sound_bank.rsp` and
   `compile-common-bit-buffer.rsp`, in that order.
4. `lib.exe @archive-common.rsp`, proving the thirteen member payloads afterward.
5. `link.exe @link-candidate.rsp`, using exactly 413 ZoneTool objects, seventeen
   retained libraries and the new common library, with the existing resource.

These are review notation for commands whose full bindings are in the local
JSON, not instructions to launch them from this checkout. The compiler command
records retain all recorded release macros/options, replacing only source
selection where needed, private include precedence, PCH and output paths, and
adding include reporting. Common/probe compilations keep the common macros;
only the five ZoneTool compilations define `EXPERIMENTAL_IW7`. All eight compile
responses retain `/fp:precise`; disabling `/Fp` PCH output must not remove this
distinct floating-point flag. The final link keeps the original `/INCREMENTAL:NO`
and substitutes exactly five object paths, the common library and three output
paths. Windows path comparison normalizes the doubled separators in the retained
link record. These two draft-generation corrections are retained in the JSON.

The future launcher must pin the x64 toolchain `PATH`, `INCLUDE` and `LIB`, clear
`CL`/`_CL_` option injection, isolate `TMP`/`TEMP`, create only the fresh candidate
directories, and wrap every stage with reviewed admission, output limits, job
closure and read-only input guards. No developer environment was launched for
this preparation. Neither the command draft nor the source tests establish those
runtime guarantees or qualify the old objects/libraries for reuse.

## Resource and storage estimate for review

Metadata-only inspection found 413 retained objects totaling 541799648 bytes.
The five to replace total 9881624 bytes; the old common object is 71574 bytes.
The prior common library is 3965610 bytes. Its historical SHA-256 is
`9f689a252c54705f2508ea4cf2d928ac3deb040c94c20a67949610521447314f`;
it has not been freshly hashed or requalified during this source-only review.
The historical E7 identity is pinned separately in the source contract.

Using prior EXE, final PDB and compile-PDB sizes as planning allowances gives
214946392 bytes (about 205 MiB) for six objects, common library and these outputs.
This is a size reference, not a measured future peak. Propose a 512 MiB observed
stop threshold and a 768 MiB planning ceiling for all new candidate files,
including probes, library intermediates, logs and debug output. Neither is a
filesystem quota. An overrun must close the job and retain evidence; it does not
authorize deleting old objects or exceeding admission silently.

For sequential compile, archive and link, propose 4 GiB RAM / 6 GiB commit as a
conservative review estimate, not measured consumption or granted admission.
No duration is claimed. Reuse input hashing and dependency inspection belong
inside the future admitted scenario. The later SAB/FF run is separately gated
and keeps its complete 8 GiB RAM / 11 GiB commit estimate. No game stock clone is
needed for compilation. Any native execution first requires the current resource
workflow, a fresh lease and the existing job closure/restoration guarantees.

The coordinator owns PR153, exact-head CI, merge and common documentation for
this delivery. Local tests establish source-level regression evidence only.

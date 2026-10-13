# Selected resident T7 image to DDS

This is executable **offline pixel serialization**, plus a native copy adapter
qualified against a synthetic fixture. Neither is connected to `native_export.inc`.
The existing `iw7.t7-iw7-resident-export/1` and `/2` model contracts still emit
their two geometry files; v2 adds ordered surface/material records, not material
or image payload completeness.

## Reusable pieces

- `resident_image.py::CopiedImage`, `layout`, `to_dds`: validate a copied scalar
  view and owned immutable bytes, then return a DX10 DDS. No engine calls,
  decompression, color conversion, shader transfer or package lookup.
- `resident_image_copy.hpp::copy`: read the pinned T7 header into a local value,
  validate the metadata, copy at most 16 MiB of pixels, and recheck the relevant
  header/pixel pointer. The caller supplies the existing throwing readability
  check, e.g. `resident_iw7::detail::readable`. There is no new memory-access API.
  Header and complete pixel ranges are checked **before** dereference/copy;
  address overflow/null and changed metadata are refused. The result owns its
  pixel vector and has no exported process pointer, shader or GPU handle.

The native adapter passed standalone x64 MSVC compilation and all 54 synthetic
fixture cases in attempt B below. Attempt A remains a recorded compile failure.
Its five source-contract checks are not runtime tests of pointer readability.
The callback must throw for an unreadable range; a no-op callback is invalid.
The caller must keep the source allocation/database stable through copying.
Sequential header checks cannot prove an atomic pixel snapshot or prevent an
unmap between a readability check and memcpy. No race-free claim is made.

## Engine lifetime: source findings and proposed scope (2026-10-12)

The current [postload exporter](https://github.com/bigmangeekf/iw7-paris-server/blob/894895ec654025b3799595c5272062f3f1829b49/tools-source/asset-bridge/t7-iw7/native_export.inc#L65-L106)
loads synchronously, waits, then selects the model and borrowed mesh/material
pointers. Its "same stable DB scope" comment is a **caller precondition**, not an
implemented retention mechanism. At native pin `fab935826c898806855376662a8a03317b3ad8f1`,
[startup calls the CLI before its Com_Frame loop](https://github.com/bigmangeekf/x64-zt/blob/fab935826c898806855376662a8a03317b3ad8f1/src/zonetool/component/t7/zonetool.cpp#L12-L22),
and [load_zone requests no explicit zone release](https://github.com/bigmangeekf/x64-zt/blob/fab935826c898806855376662a8a03317b3ad8f1/src/zonetool/zonetool/t7/zonetool.cpp#L399-L440).
This bounds caller control flow; it does not establish the runtime thread identity,
exclude DB workers or retain delayed/temporary image allocations.

[wait_for_database only polls readiness](https://github.com/bigmangeekf/x64-zt/blob/fab935826c898806855376662a8a03317b3ad8f1/src/zonetool/zonetool/t7/zonetool.cpp#L94-L106).
The [exposed DB functions](https://github.com/bigmangeekf/x64-zt/blob/fab935826c898806855376662a8a03317b3ad8f1/src/zonetool/zonetool/t7/functions.hpp#L11-L17)
provide no usable retain/release or lock API. Scheduler/capture mutexes protect
their own containers, not engine allocations. Readability checks and repeated
metadata reads neither pin pages nor make pixel copying atomic.

The minimal proposed correction reuses the existing
[DB_Add callback](https://github.com/bigmangeekf/x64-zt/blob/fab935826c898806855376662a8a03317b3ad8f1/src/zonetool/zonetool/t7/zonetool.cpp#L351-L379).
It already dumps assets synchronously before forwarding; IMAGE skips the original
DB_Add entirely, so normal image registration/retention cannot be assumed.
For the one exact XModel, borrow pointers only within this callback: select the
LOD, serialize geometry and copy the single admissible image before returning.
Retain only owned bytes, strings and scalars afterward. Refuse missing/nonresident
dependencies, an unsupported image profile or repeated capture, without a postload
fallback. Add no hook, worker or purported DB mutex, and perform no reentrant load,
wait or waiting DB lookup inside the callback.

This is a concrete placement to test, **not an observed dependency-lifetime
guarantee**: the source does not expose the loader's allocation lifecycle or prove
that every referenced material/image is ready and unchanged there. The finish-load
callback shown in the same source is no substitute for that evidence. Catalogue
bootstrap remains the priority; next observe the selected dependencies in the
existing callback. Do not extend the image capture/publication contract before
that first real observation; the existing geometry `/2` is a separate contract.
No new infrastructure or exhaustive theoretical lifetime proof is required.

## Explicit v1 profile

Single T7 `MAPTYPE_2D=1`, depth 1, width/height 1..4096; output DDS Texture2D=3,
arraySize=1. `width1/height1/levelCount1` must equal `width/height/levelCount`.
That conservative equality is a pilot admission rule, not an assertion about
every possible T7 image. A future real observation may justify a reviewed
extension; this helper never guesses which dimensions describe a resident tail.

`streaming`, `streamedPartCount`, `useFallback`, `fallbackLevel`, `fallbackSize`
must be zero; no fallback pointer and no delayed pixels. Uninterpreted T7 `flags`
must be zero. Nonzero flags are outside this profile, not proof of corrupt assets.
Zero active streamed parts is checked; unused descriptor storage is not interpreted.

Typed formats supported, using SDK DXGI identifiers:

| Storage | Linear / sRGB IDs | Bytes per unit |
|---|---|---|
| RGBA8 UNORM | 28 / 29 | 4 per pixel |
| BGRA8 UNORM | 87 / 91 | 4 per pixel |
| RG8, R8 UNORM | 49, 61 | 2, 1 per pixel |
| BC1 | 71 / 72 | 8 per 4x4 block |
| BC2, BC3 | 74 / 75; 77 / 78 | 16 per 4x4 block |
| BC4 UNORM / SNORM | 80 / 81 | 8 per 4x4 block |
| BC5 UNORM / SNORM | 83 / 84 | 16 per 4x4 block |
| BC7 | 98 / 99 | 16 per 4x4 block |

`format_namespace` must explicitly be `DXGI_FORMAT`; the different T7
`GfxPixelFormat` enum is not accepted as the same namespace. UNKNOWN/TYPELESS,
HDR/BC6, video, depth, arrays, cubes and volumes are outside v1. An explicit
DX10 header preserves signed/UNORM/sRGB distinctions. Pixels/blocks are copied
unchanged; alpha mode remains UNKNOWN, with no guessed premultiplication.

For each declared mip, dimensions halve to at least one. Linear row pitch is
width times pixel size; BC row pitch is ceil(width/4) times block size, with
ceil(height/4) rows. Even a 1x1 BC mip occupies a complete block. `totalSize` and
the copied byte count must equal the exact sum of tight mip sizes, at most16 MiB.
Padding, truncation and trailing bytes fail. One to the maximum possible mip
count is supported; no omitted mip is generated. All **declared** mips must be
present. This does not prove that a future capture describes the donor's highest
quality representation. Source format/layout/residency remain observations to
check when the adapter is first integrated.

## Finite integration into a later selected export

After the callback observation above supports integration, follow only that
model's single material and its explicitly selected image pointers; do not
enumerate the DB, dump a zone or enable XPAK. Within the reviewed callback scope:

```cpp
auto copied = zonetool::t7::resident_image::copy(source_image,
    zonetool::t7::resident_iw7::detail::readable);
```

A future extension can serialize the exact `metadata` scalar names as
`{"schema":"iw7.t7-resident-image-copy/1","format_namespace":"DXGI_FORMAT","image":{...}}`
and publish its owned pixels through the existing bounded writer. Reuse that
writer/runner and explicitly extend the file allowlist, count/byte budgets and
manifest version. Do not change the current model `/1` receipt's two-file promise.
No source asset names are used as filesystem paths by this helper.

Then convert those explicit files after the source process has closed:

```text
python -B -S resident_image.py copied-image.json copied-pixels.bin selected.dds
```

Metadata is capped at16 KiB, pixels at16 MiB. The output is created exclusively;
an existing file is refused. A disk write failure can leave a partial new output;
only successful completion is usable. Library callers may instead use
`to_dds(view, immutable_pixels)` and their existing publication transaction.
Metadata cannot direct the helper to another file. Maximum DDS size is
16 MiB +148 bytes. There is no download, discovery, fallback or automatic retry.

IW7's existing `gfximage.cpp::directxtex::parse` loads DDS with DirectXTex and
builds a non-streamed `GfxImage`; this is the intended consumer. Actual DirectXTex
parse/reload has not run here. The material still needs explicit slots, samplers,
UV/constant mapping and a compatible real IW7 techset. The T7 semantic is retained
as metadata only; this helper does not repack normals/gloss/specular, assign a
placeholder material, or establish rendered quality.

## Selected material decision (2026-10-13)

After export D provides real ordered `material_dependencies`, observe one named
material and one selected image, including the chosen material's aliased slots.
The seam is [native_export.inc](native_export.inc)'s
`selected->meshMaterials[0].materials[i]`, currently reduced to `material->name`.
The callback scope above remains a placement to qualify, not a lifetime guarantee.
Do not add a native hook or image-capture implementation before these observations.

At native pin `fab935826c898806855376662a8a03317b3ad8f1`,
[T7 MaterialTextureDef](https://github.com/bigmangeekf/x64-zt/blob/fab935826c898806855376662a8a03317b3ad8f1/src/zonetool/zonetool/t7/structs.hpp#L731-L772)
contains `image`, `nameHash`, `uvScale`, `texSizeShift[2]`, `uvOffset[3]`, `usage`
and `isMatureContent`. Material supplies `textureCount/textureTable`,
`samplerCount/samplerTable`, `constantCount/constantTable` and `techniqueSet`.
Preserved mesh UVs therefore do not prove preserved texture placement; mapping
these fields, sampler state and packed offsets remains unknown.

The existing [MaterialV2 template](../surfaces/prepare_material_v2.py) uses
IW7 bindings **14 = TS_COLOR_SPECULAR_MAP** and
**15 = TS_NORMAL_OCCLUSSION_GLOSS_MAP**, per the pinned
[IW7 enum](https://github.com/bigmangeekf/x64-zt/blob/fab935826c898806855376662a8a03317b3ad8f1/src/zonetool/zonetool/iw7/structs.hpp#L2729-L2748).
T7 image semantic `DIFFUSE_MAP=2` or `NORMAL_MAP=4` does not supply that channel
mapping. Do not infer compatible alpha, normal/gloss packing, constants or shader
behavior from the image name/semantic. Keep qualified IW7 techset/state data;
blind copying of T7 constant buffers is not a conversion.

The bounded route is one admissible resident image (2D, at most 4096 per dimension
and 16 MiB pixels), the existing copier and DDS serializer, then one derived IW7
material in MaterialV2 and ModelFF. It still requires real capture/lifetime,
DDS-import, channel/UV and selected-format readback evidence. The current
synthetic 32x32 witness cannot establish those facts or BO3 rendering parity.
See the [five-surface decision](../../../docs/CONTENT-SURFACES-BRIDGE.md#t7-five-surface-material-boundary-2026-10-13).

## Source and validation evidence

At retained native pin `fab935826c898806855376662a8a03317b3ad8f1`:
`src/zonetool/zonetool/t7/structs.hpp:918` defines GfxImage (0x108 bytes;
name offset248). `iw7/assets/gfximage.cpp:128-194` implements DDS import and
`:646-723` computes/saves DDS mip pitches. Bundled
`deps/DirectXTex/DirectXTex/DDS.h` defines the 124+20-byte headers;
`DirectXTexDDS.cpp::EncodeDDSHeader` defines their flags. Format IDs were checked
against the installed Windows SDK `dxgiformat.h`. No game bytes were read.

```text
python -B -S -m unittest discover -s tools-source/asset-bridge/t7-iw7 -p "test_resident_image*.py" -v
```

The initial source-only checkpoint passed 22 tests:17 executable Python tests (including independent fixed-offset
DDS parsing, original checkerboard/BC1 red data, all18 typed formats, mip tails,
sRGB preservation and malformed inputs), plus5 C++ source-contract checks.
That checkpoint did not perform a native build, engine import or real-image
capture and did not establish material completeness or visual acceptance.
The separate initial synthetic validation receipt records
the checked sources. Native synthetic qualification below comes before a bounded
selected-image capture/publication extension under its own reviewed native plan.

## Native fixture qualification (2026-10-12)

`resident_image_fixture.cpp` includes the production copy adapter, which includes
the **actual pinned T7 structs** through the native tree's include path. It does
not redeclare `GfxImage`, replace the adapter, or disable the native ABI assertions.
It requires x64, a 264-byte image header and name offset 248. The two assertion
macros have the same semantics as the pinned `std_include.hpp`, without pulling
in that application's unrelated dependencies.

The fixture covers **54 native cases**, all executed successfully by attempt B.
Attempt A below remains a failed compilation:

- Six exact-byte copies cover linear RGBA/R8 rows, odd dimensions, BC1/BC3 block
  rounding, multiple mips and complete sub-block tails. Expected sizes are literal
  independent values. Each case checks metadata, bytes and ownership of the copy.
- Eighteen SDK-named typed formats each copy their independently specified 1x1
  storage size, retaining the UNORM/SNORM/sRGB distinctions.
- Thirty refusals cover streaming/fallback/delay, flags, dimensions/mips,
  cubes/depth, typeless/BC6, short/trailing/over-budget size, unreadable spans,
  invalid/null/overflowing pointers, and a header/pointer change during copying.

Every pixel array is 128 bytes; the largest successful pixel copy is 96 bytes.
The readability callback accepts only the fixture's actual header and bounded
array, throws before an invalid address can be dereferenced, and can simulate a
change before the second header copy. This tests the callback contract, **not**
Win32 page probing, SEH, a real DB scope, or an atomic image snapshot. Future engine
integration still requires a stable DB/allocation scope through both reads and
the pixel copy; double header checks cannot establish that scope themselves.

Success is one exact JSON record, at most 1 KiB of stdout, empty stderr and root
exit 0. `resident_image_fixture_check.py` checks a saved transcript with bounded
reading, exact fields/types/counts, duplicate-key rejection and explicit false
engine/atomic/SEH flags. A matching transcript alone is forgeable and is **not
execution evidence**: the checker reports `native_execution_verified: false`.
The existing owned runner's receipt must prove which binary ran and closed.

### Minimal stage recipe and remaining runner binding

`resident_image_fixture_plan.json` contains the complete four direct-tool argv
lists and budgets as **inert stage data, not a sealed or executable Plan**:

| Stage | Direct tool and intended result |
|---|---|
| Compile | x64 `cl.exe /std:c++20 /EHsc /MD /O1 /W4 /WX /c`, fixture TU to `.obj`, plus `/sourceDependencies` JSON |
| Link | x64 `link.exe`, that object to the fixture `.exe`; MSVC/SDK CRT libraries and `kernel32.lib` |
| Fixture | That exact prior link artifact, no arguments; bounded synthetic JSON |
| Check | Qualified Python `-I -S -B resident_image_fixture_check.py <saved-stdout>` |

These commands are intended as argv passed to the **existing stage owner**, not
as shell commands bypassing its admission or supervision. Bind the installed
MSVC and Windows SDK include/library roots, the pinned native tree and the fixture
source directory. The real T7 header needs SDK `d3d11.h` declarations; no Direct3D
device or D3D import library, Boost, DirectXTex, game executable or game data is
needed by this fixture. Compilation remains the check of that dependency claim.
Retain the compiler dependency report and reject unexpected source provenance.

Reuse `Invoke-WorldStage` in `world/ObserverStages.Profile.ps1`, then
`Invoke-T7OwnedStage` in `t7-iw7/T7Build.Profile.ps1` and `Invoke-H1OwnedStage` in
`h1-fixture/H1Native.Core.ps1`, with the already qualified native Job provider.
The current World CLI fixes its own translation unit, artifacts and transcript
checker; **it cannot consume this proposal unchanged**. The runner owner must
bind this narrow fixture profile and seal its existing transitive sources/tool
receipts. Do not create another launcher, framework, supervisor or native owner.

The proposal retains the qualified stage model: separate Compile and Link jobs,
previous root exit 0 and original job closure before advancing, guarded/pinned
artifacts before launch, bounded deadlines, original-handle cleanup and immutable
closure/release receipt. Reuse the existing quarantine behavior on uncertainty;
no automatic retry. The inherited reservation proposal is 4 GiB physical/6 GiB
commit; Compile+Link share 90 s, Fixture 10 s, Check 5 s, group 120 s, cleanup 5 s.
These are admission limits, not measured fixture peaks. Existing 63 MiB live and
2 MiB per-log guards are sampled thresholds, not strict write caps; final output
acceptance is 64 MiB. Fixture transcript acceptance remains the tighter 1 KiB.

Before any GO, bind the exact fixture/helper/checker/proposal, actual T7 header,
existing profile/provider source closure, qualified compiler/linker/Python and
telemetry/native-owner receipts, plus a fresh private RunRoot and sanitized child
environment. **Catalogue C has priority.** Preparing these source files performs
no binary hash, Plan invocation, resource admission, build, or native execution.
The source bundle stays below 1 MiB.

The same Python discovery command above passed **36 tests**: the previous 22,
eight executable transcript-checker tests and six fixture/proposal source checks.
These Python checks are separate from the 54 native cases; they cannot by
themselves certify compilation or native behavior. B supplies that evidence.

### Native attempt A: compile refusal retained

The one authorized A invocation on 2026-10-12 ran from 14:40:41.669 to
14:40:55.328 UTC. MSVC exited 2 with C2220 under `/WX` and C4702 (unreachable
code) at `resident_image_copy.hpp:109`, immediately after the readability call.
The two null/header-overflow cases instantiated that template with a callback
whose body always threw. Their expected early refusal does not prevent MSVC
from diagnosing the rest of the template instantiation. This source diagnosis
does not turn the failed compile into successful native validation.

The fixture now passes its existing stateful synthetic allowlist to those two
cases and asserts the callback count stays zero after each. If an early refusal
regresses, the same allowlist still throws before the invalid address can be
dereferenced. `/WX`, ABI checks and the production helper are unchanged. No
warning suppression or no-op memory callback was added. The correction was
subsequently qualified by B, under its fresh reviewed Plan and separate GO.

The original compiler job closed after failure cleanup. The immutable receipt
records `Failed`, source hashes unchanged, and closure confirmed **before** lease
release. The retained host subsequently observed an empty registry and no
AppDomain quarantine; postflight preserved stopped Main and the protected Python.
The host exited normally and its absence was confirmed at 14:43:53.183 UTC.
Link, Fixture and Check never ran in A; it supplies no native case results.
`resident_image_fixture_validation-20261012-a.json` preserves the sanitized
failure, evidence hashes and closure boundaries. There was no retry.

### Native attempt B: 54 cases passed, all jobs closed

The separately authorized B invocation used fixture source `f1e0d357` and ran
from 14:51:34.387 to 14:51:44.829 UTC on 2026-10-12. All four stages exited 0:
Compile retained `/WX`, Link produced the guarded 23,552-byte executable, Fixture
executed the 6 copy +18 format +30 expected-refusal cases, and Check accepted its
exact 298-byte JSON. Every stage's stderr was empty. The actual T7 header measured
264 bytes with name offset 248; the largest copied pixel payload was 96 bytes.
Compiler dependency evidence lists 263 includes, all within the guarded set.

Compile and Link used the existing qualified same-job telemetry cleanup, then
confirmed fresh root0/Active0. The very short Fixture and Check processes had
already left their original jobs empty before scheduler CIM registration; the
unchanged owner confirmed closure and exit0 through their retained handles.
This registration observation is retained in the receipt, not hidden as an error.

The immutable receipt was verified before release; returned state then confirmed
`SyntheticHarnessPassed` and `LeaseReleaseState=Confirmed`. Final run output was
463,606 bytes. All four jobs closed, source/input revalidation passed under the
lease, and the retained host found no AppDomain quarantine. Postflight found no
other heavy process or remaining known child, with stopped Main and the protected
Python preserved. The host exited normally; its absence and that of all six known
children were confirmed at 14:53:45.886 UTC. No binary was rehashed after release.

`resident_image_fixture_validation-20261012-b.json` records the sanitized stage
results, guarded artifact hashes and text/JSON evidence hashes. The executable
hash is taken from the original guarded receipt, not recomputed after release.
The standalone checker still correctly reports `native_execution_verified=false`:
the original-job receipt supplies execution evidence that a transcript alone cannot.

This establishes standalone compilation and synthetic copy/validation behavior.
It does not establish a stable engine DB scope, an atomic snapshot, SEH protection,
real T7 image residency, DirectXTex import, material completeness or rendered
quality. After catalogue bootstrap, the next work is the callback dependency
observation described above, before a reviewed selected-image publication
extension. No further native invocation is authorized by this checkpoint.

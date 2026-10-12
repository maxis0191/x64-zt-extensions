# Selected resident T7 image to DDS

This is executable **offline pixel serialization**, plus a source-only native
copy adapter. Neither is connected to `native_export.inc`. The existing
`iw7.t7-iw7-resident-export/1` model contract still emits its two geometry files;
no material/image dependency has silently become complete.

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

The native header has **not passed native compilation**; attempt A below failed
before any fixture execution.
Its five source-contract checks are not runtime tests of pointer readability.
The callback must throw for an unreadable range; a no-op callback is invalid.
The caller must keep the source allocation/database stable through copying.
Sequential header checks cannot prove an atomic pixel snapshot or prevent an
unmap between a readability check and memcpy. No race-free claim is made.

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

After selection, follow only that model's single material and its explicitly
selected image pointers; do not enumerate the DB, dump a zone or enable XPAK.
In the existing stable DB scope call:

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

22 tests pass:17 executable Python tests (including independent fixed-offset
DDS parsing, original checkerboard/BC1 red data, all18 typed formats, mip tails,
sRGB preservation and malformed inputs), plus5 C++ source-contract checks.
No native build, engine import, real-image capture, material completeness or
visual acceptance is claimed. The separate synthetic validation receipt records
the checked sources. Native synthetic qualification below comes before a bounded
selected-image capture/publication extension under its own reviewed native plan.

## Prepared native fixture (source only, 2026-10-12)

`resident_image_fixture.cpp` includes the production copy adapter, which includes
the **actual pinned T7 structs** through the native tree's include path. It does
not redeclare `GfxImage`, replace the adapter, or disable the native ABI assertions.
It requires x64, a 264-byte image header and name offset 248. The two assertion
macros have the same semantics as the pinned `std_include.hpp`, without pulling
in that application's unrelated dependencies.

The fixture prepares **54 native cases**. Attempt A below failed compilation;
no native case has executed yet:

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
These checks are separate from the 54 intended native cases; they cannot certify
compilation or native behavior.

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
warning suppression or no-op memory callback was added. This correction has not
yet been compiled; it requires a fresh reviewed B Plan and a separate GO.

The original compiler job closed after failure cleanup. The immutable receipt
records `Failed`, source hashes unchanged, and closure confirmed **before** lease
release. The retained host subsequently observed an empty registry and no
AppDomain quarantine; postflight preserved stopped Main and the protected Python.
The host exited normally and its absence was confirmed at 14:43:53.183 UTC.
Link, Fixture and Check never ran. The 54 intended cases remain unexecuted.
`resident_image_fixture_validation-20261012-a.json` preserves the sanitized
failure, evidence hashes and closure boundaries. There was no retry.

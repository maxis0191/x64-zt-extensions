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

The existing Python helper can also compare a dumped IW7 image with those same
copied bytes, including every declared mip and unchanged compressed block:

```text
python -B -S resident_image.py copied-image.json copied-pixels.bin --verify-iw7-image selected.iw7Image --image-name community_bo3_color --iw7-semantic 2
```

This readback checks the pinned IW70x70 scalar, typed format, dimensions, mips,
resident byte counts, explicit IW7 semantic, literal name and complete pixel array.
It creates no DDS and reports serialized-byte verification only, not capture
provenance, channel decoding, shader compatibility or rendered quality. On
2026-10-13, 29 tiny synthetic image/readback/source tests passed; no real T7 image
or native DDS import was exercised by that result. The earlier Material C witness
and its exact 32x32 oracle remain unchanged.

## Selected material decision (2026-10-13)

After a real export with the D candidate provides ordered `material_dependencies`,
observe one named material and one selected image, including its aliased slots.
The seam is [native_export.inc](native_export.inc)'s
`selected->meshMaterials[0].materials[i]`, currently reduced to `material->name`.
The callback scope above remains a placement to qualify, not a lifetime guarantee.
Use narrowly bounded metadata instrumentation for these observations before
adding pixel capture; this decision does not require a pixel exporter to exist first.

The separate [metadata helper](selected_material_observation.hpp) accepts the
exact model name, LOD, selected slot and existing throwing readability callback.
It records at most 32 ordered material names, then one material's aliases,
16 texture/sampler entries and 32 constants. UV scales/constants stay raw float
bits; image fields stay typed metadata. Reads are capped at 64 KiB and JSON at
32 KiB. It never reads pixels/streams, writes a file or calls the engine. Header
rechecks do not pin allocations or establish an atomic snapshot. Refusal returns
non-ready JSON, retaining names already collected when they can be serialized.
The native caller must log that diagnostic separately and continue its original
geometry selection, so this observation cannot erase its geometry refusal.
The [tiny fixture](selected_material_observation_fixture.cpp) has synthetic
headers and an unreadable pixel sentinel. Original attempt C passed **32 checks**
and the diagnostic correction passed **50 checks** in D on 2026-10-13, as recorded
below. Neither result qualifies a real material capture.

### Selected-material fixture: 32 checks passed (2026-10-13)

Attempt C compiled the unchanged fixture and production helper from source
package `afdd8062732499698a6a810918b8aae082ba3668`, including the actual T7
structs at native pin `fab935826c898806855376662a8a03317b3ad8f1`. Those input helper
and fixture bytes match the author-preserving cherry-pick merged in
[PR 11](https://github.com/maxis0191/x64-zt-extensions/pull/11), merge
`7fd2016cafc247dca0cd8372deaa383ace99fbff`. PR 9 was closed as superseded.
MSVC 14.44 retained C++20, `/W4 /WX`, `/MD` and `/O1`.

The combined compile/link root exited 0. Two original-job captures then proved
that its sole remaining member was the pinned `vctip.exe` child with the same
identity and the compiler as parent. The existing H1 original-job helpers stopped
only that retained job; fresh observations confirmed root exit 0, zero active
processes and an empty member list before ordinary closure. No global telemetry
setting or external PID stop was used. The separately owned fixture then exited
0 with the actual transcript:

```text
PASS selected material metadata fixture: 32 checks; no pixels or engine calls.
```

The executable measured 178,688 bytes, SHA-256
`d76f9d8c107a092502f18e00eefaf67a2e187ff8e534638cc72a84cc3353a716`.
The original-job receipt records both phase exits, artifact hashes and confirmed
tree closure before resource release. All retained outputs, including that
receipt, total 4,173,578 bytes. Fresh postflight observed zero leases and zero
heavy/game processes; the invoking host exited 0.

Earlier attempt A remains failed: the pinned NativeJob assembly consumed
`ProcessStartInfo.ArgumentList`, while the first driver supplied `Arguments`.
The compiler printed usage and produced no executable. Attempt B used the
correct argument list and produced artifacts, but its naive whole-job wait
expired before the standalone test. Its original compiler exit was not retained;
artifact existence is not a passed compile/test receipt. Both failed jobs were
closed and their leases released, with their separate evidence preserved.
Attempt C reused the existing H1 compiler/member helpers rather than adding
another process supervisor.

This qualifies standalone synthetic metadata/refusal behavior, including the
unreadable pixel sentinel. It does not establish live pointer lifetime, atomic
snapshots, authentic texture bindings/pixels, channel conversion, shader import
or rendered appearance. The subsequent real BO3 metadata sonde did not produce
an image candidate, as recorded below.

### Real selected-material read refusal and diagnostic correction

The E2 engine sonde on 2026-10-13 observed five ordered material names for
`p7_fre_platform_cap_02`, LOD 0. Selected slot 0 named
`mc/t7_metal_trim_safehouse_mobile_09` and aliased only slot 0. Its material
observation then refused with `range is not committed readable memory`;
`headers_rechecked`, `pixels_copied` and `ready` remained false. No texture
name, DXGI format, source semantic or pixel payload was captured. The old
diagnostic cannot distinguish a table, image, technique or recheck failure;
the exact engine-side cause remains unknown.

The corrected source exposes `failure_stage` and, for indexed reads, the original
row `failure_index`. Its `selected_header` records only table counts and pointer
presence booleans, never addresses. Texture rows are now processed before sampler
and constant tables and retained progressively after their own texture recheck.
A later refusal therefore preserves candidate metadata already read. That partial
output still has `refused=true` and `headers_rechecked=false`; it does not qualify
texture binding, lifetime or pixels. Complete header/name rechecks and the existing
64 KiB read/32 KiB JSON bounds still apply before success.

New synthetic cases cover unreadable texture/sampler/constant tables, refusal
stages, partial texture preservation and sparse image bindings. Attempt D compiled
and executed them from source `966c98f9edaef07753421f56189997da0d4531e8` with
MSVC C++20 `/W4 /WX`, passing the actual transcript:

```text
PASS selected material metadata fixture: 50 checks; no pixels or engine calls.
```

Compile/link and the separate fixture each exited 0. Two original-job captures
proved the same pinned `vctip` child after compiler exit 0; only that owned job
was stopped, then fresh root0/active0/members0 preceded ordinary closure and the
test. All jobs closed before lease release; fresh postflight showed zero leases
and heavy/game processes, and the invoking host exited 0. The executable measured
183,808 bytes, SHA-256
`38c1849ee7f89d292954a16b68b80c838ec96c54eb7c7c0206f67e3243f8f1fa`.
All retained outputs total 4,314,643 bytes, within D's 6 MiB bound. The earlier
32-check C result remains attached only to its original input bytes.

A primary-source comparison with Greyhound
[`22c3d17`, BO3 structures](https://github.com/Scobalula/Greyhound/blob/22c3d17f7428573042b56f43af0ed2585989bebd/src/WraithXCOD/WraithXCOD/DBGameAssets.h#L817-L839)
corroborates material texture count at `0x270`, texture table at `0x280`, binding
image/nameHash at `0x00/0x08` and binding stride `0x20`. Its material description
ends at `0x288`, so it is a partial prefix rather than a conflicting complete
size. Its [BO3 reader](https://github.com/Scobalula/Greyhound/blob/22c3d17f7428573042b56f43af0ed2585989bebd/src/WraithXCOD/WraithXCOD/GameBlackOps3.cpp#L582-L620)
uses those entries. It does not corroborate sampler/constant pointers, UV decoding,
the loaded engine version or E2 allocation validity. No ABI mismatch is established.

E2 and the geometry owner's compiled observer remain immutable. A future
diagnostic epoch must explicitly adopt the new helper and requalify the native
CLI; D's synthetic cases do not supply that engine evidence. No diffuse image is
inferred from a material name or an incomplete observation.

### E3 image-header refusal and retained binding scalars

The separate E3 stock sonde observed seven textures, eight samplers and zero
constants in selected material 0. It copied the texture table, then refused at
`image_header`, original binding index 0, with the same committed-readable-range
guard. No image header, image name, source semantic, format or pixels were read.
The stdout text was 1,404 bytes with SHA-256
`433ebb839a9b07408d58e965487c6c856e3782dbb96398728a45eaf8268e1082`.
That failed result and its compiled inputs remain frozen.

The next correction records the scalar rows already owned after the texture-table
copy before any image dereference. `nameHash`, `usage` and UV fields remain raw;
addresses are never published. `image_pointer_present`, `image_header_read` and
`image_read_state` distinguish `absent`, `not_attempted`, `observed` and `refused`.
An image-name refusal may retain its already copied header metadata. A refused
row records its image failure stage; later rows remain explicitly not attempted,
rather than being mistaken for missing or unreadable images. The observer still
stops at that refusal and leaves all completeness/lifetime/pixel claims false.
Header/texture rechecks, maximum counts and read/output limits are unchanged.
Attempt E on 2026-10-14 (Europe/Paris), source
`8b953041b734fd129dd9d19aa61f92d198800a3d`, actually passed the changed fixture:

```text
PASS selected material metadata fixture: 63 checks; no pixels or engine calls.
```

The checker required the exact inventory of D50 plus 13 added/updated checks,
including retained failed-binding scalars, later unvisited bindings, an unreadable
image name after a copied header, and sparse image indices. MSVC C++20 `/W4 /WX`
compile/link and the separately owned fixture both exited 0. The sole pinned
`vctip` child was captured twice through the original compiler job; only that job
was stopped, then fresh root0/active0/members0 preceded ordinary closure and test.
All jobs closed before lease release, fresh postflight showed zero leases and
heavy/game processes, and the invoking host exited 0. Retained outputs total
4,393,223 bytes under the 6 MiB bound. The 187,904-byte executable SHA-256 is
`28aaa52b2f28227a592cebbdfed94b50557f1a2519c52366f887a3785ada4312`.
This qualifies the new synthetic diagnostics, not an engine pointer or authentic
image capture. The earlier D50 and E3 results belong only to their frozen bytes;
a future native CLI must explicitly adopt these new source inputs.

Greyhound
[`22c3d17`, image structures](https://github.com/Scobalula/Greyhound/blob/22c3d17f7428573042b56f43af0ed2585989bebd/src/WraithXCOD/WraithXCOD/DBGameAssets.h#L776-L815)
also describes a `0x108` image header and name pointer at `0xF8`. Its
[BO3 material/image reader](https://github.com/Scobalula/Greyhound/blob/22c3d17f7428573042b56f43af0ed2585989bebd/src/WraithXCOD/WraithXCOD/GameBlackOps3.cpp#L582-L633)
uses `ImagePtr` directly, without a handle lookup, tag mask or second header-pointer
dereference. This does not establish E3 pointer validity. Its pixel-size and format
interpretations differ in field width from the native declarations; no resident
profile is changed based on that source comparison.

The same primary reader classifies binding `SemanticHash` (native `nameHash` at
`0x08`) as DiffuseMap for `0xA0AB1041`, NormalMap for `0x59D30D0F`, SpecularMap for
`0xEC443804`, otherwise Unknown. It does not use the native `usage` field or the
separate T7 `GfxImage::semantic`. These labels can guide a future exact binding
selection; they supply no filename, pixel encoding, texture lifetime or IW7 mapping.

### E4 stock binding observations

The separate E4 sonde on 2026-10-14 (Europe/Paris) observed selected material 0
of `p7_fre_platform_cap_02`, LOD 0, and retained all seven copied binding rows.
Its header reported seven textures, eight samplers and zero constants; texture,
sampler and technique-set pointers were present, while the constant-table pointer
was absent. Every binding reported an image pointer present, but binding 0 refused
at `image_header` before copying a header. Bindings 1 through 6 were explicitly
`not_attempted`, not proven unreadable. All seven `image_header_read` values were
false, and every `image` was null. No image name, format or pixels were captured.

| Binding index | Raw `nameHash` | Raw `usage` | Image read state | Greyhound hash classification only |
| --- | --- | --- | --- | --- |
| 0 | `0x07176BF2` | 16 | `refused` at `image_header` | Unknown |
| 1 | `0x389DD40F` | 0 | `not_attempted` | Unknown |
| 2 | `0x59D30D0F` | 2 | `not_attempted` | NormalMap |
| 3 | `0x6D0A6C98` | 8 | `not_attempted` | Unknown |
| 4 | `0xA0AB1041` | 1 | `not_attempted` | DiffuseMap |
| 5 | `0xEB529B4D` | 0 | `not_attempted` | Unknown |
| 6 | `0xEC443804` | 4 | `not_attempted` | SpecularMap |

The last column is an inference from the pinned primary reader cited above, not
an additional runtime observation or an interpretation of `usage`. Binding 4 is
therefore a precise diffuse-header diagnostic lead; it does not provide a name,
encoding, retained allocation, converted IW7 material or rendered texture. All
rows had `uvScaleBits=[1065353216,1065353216]`, `texSizeShift=[0,0]`,
`uvOffset=[0,0,0]` and `isMatureContent=0`. The copied scalars were not rechecked
after the image refusal; `headers_rechecked`, `allocation_retained`,
`atomic_snapshot_proven`, `pixels_copied` and `ready` remained false.

The completed stdout was 3,282 bytes with SHA-256
`1ffe68788acf748ff9e1a51d48d8f852504aaf31be2c8779a8bd3ed2418b46d4`.
The separate export still failed before the mesh reader: its surface-0 refusal
reported bone/triangle offsets 0, vertices 208 versus expected 208, triangles 200
versus expected 200, and `collisionTreePresent=1`. This is not a successful model
export. The 36,743-byte receipt SHA-256 is
`5c7454181c2e266c81d86ac44814a8ba539f0f2aeb142e95e82355709523c302`,
under plan SHA-256
`59178a77882aa6d69bee474405e78ceff64d91ea621585e1e05ef9a3c2fb9f0f`.
It records status Failed, natural native exit 1, original tree closure confirmed,
lease released, no termination request and Ready false. These qualified binding
diagnostics do not change the frozen D/E3 results or establish image lifetime,
pixel acquisition, geometry conversion or owner gameplay acceptance.

### Explicit single-binding observation API and synthetic G qualification

`observe(model, expected_model, lod, slot, readable)` retains its original five
arguments, schema `/1`, ordered output and default reads. An explicit new entry
`observe_binding(model, expected_model, lod, slot, readable,
image_binding_selection{index, expected_name_hash})` shares the same reader and
budgets, and announces diagnostic schema `iw7.t7-selected-material-observation/2`
with `image_selection={mode:"exact_binding",index,expected_nameHash}`. A future
caller can request binding 4 with expected hash `0xA0AB1041`; no caller or native
CLI/request is activated by this source change. No native profile, payload schema
or existing renderer/input contract is changed.

The new path copies the bounded texture table and publishes the same raw rows,
then requires the requested index to exist, its copied hash to match and its image
pointer to be present before any image header/name read. A refusal here is
`texture_selection`, with no image row falsely labeled as read/refused. Only the
selected image can be attempted; all nonselected image rows remain `not_attempted`
or `absent`. Every copied scalar binding is still rechecked, including those whose
images are not selected. The existing selected-image header/name and all other
model/material/table/name rechecks remain. `headers_rechecked` means the copied
headers/rows were rechecked within this explicitly selected scope; it does not
mean nonselected image headers were read. Allocation retention, atomic snapshot,
pixels and Ready claims remain false.

The fixture source adds ten scenarios: unchanged default refusal at image 0;
exact image 4 behind unreadable nonselected image pointers; index/hash/null-image
selection refusals before image reads; selected image-header/name/name-recheck
refusals; and mutations of selected or nonselected scalar bindings. Pixel data
remain an unreadable sentinel. Attempt G on 2026-10-14 (Europe/Paris), source
`ee985f1f99486a8bf824cfb32aa7b7a6f9a9966f`, compiled and actually passed all
109 checks (the qualified E63 inventory plus 46 added checks, including
per-observation output bounds). The runner required this exact executed inventory:

```text
PASS selected material metadata fixture: 109 checks; no pixels or engine calls.
```

MSVC C++20 `/W4 /WX` compile/link and the separate fixture both exited 0 through
their original owned jobs. The sole pinned `vctip` child was captured twice with
the same creation identity, original compiler parent and original-job membership.
Only that compiler job was stopped after successful compilation and pinned
artifacts; fresh root0/active0/members0 preceded normal closure and fixture launch.
The invoking tool exited 0, and the exact original PowerShell host was absent in
a fresh PID/image/creation-filetime check. Lease release followed job closure;
fresh postflight showed an empty global registry and zero heavy/game/compiler
processes. RAM/commit remained telemetry without a numeric admission floor.

Retained scope outputs including the receipt total 4,817,828 bytes under 6 MiB.
The 193,536-byte executable SHA-256 is
`d2b240483e6eb6a2d27e1f1f7127a0253433ad66915fd87d568d2fe8a03103ee`;
the 9,085-byte receipt SHA-256 is
`13626dc4bc101e4dd60be71265de42f18770528223b10d81b1dfbc66b98a94a0`.
This qualifies the new synthetic API cases. It does not qualify an engine image
pointer, image lifetime, filename, format, pixels or an authentic rendered texture.
The E63/E4 results and E5 geometry's frozen `0ea84735` helper remain independent;
only a future explicit native CLI epoch may adopt and activate the new entry.
No T7 engine, game, stock extraction, image/pixel IO or native caller activation
occurred in G.

### First authentic diffuse: opt-in parts probe source

E5's completed metadata still contains no image name, format, size or stream key.
Its material slot 0 is `mc/t7_metal_trim_safehouse_mobile_09`; diffuse-hash binding
4 (`0xA0AB1041`, raw usage 1) was not attempted. This 32-bit binding hash is not
the 64-bit XPAK object key. The other four source material slots and their existing
IW7 shoe rebindings do not establish an authentic BO3 texture.

The separate [parts adapter](selected_material_parts_observation.hpp) preserves
the exact G2 header `a8848a92` and fixture `b3de6888`. It reuses `observe_binding`
with a guarded callback and collects exactly two owned copies of 264-byte ranges
after the original guard approves them. Any third matching range refuses, rather
than being ignored or classified by a type heuristic. The 64 KiB budget charges
both original reads and the additional 528 copied bytes. Before adding parts, the
adapter requires the exact selected row, G2's header/name rechecks, two copies at
the same address with identical full header bytes, and metadata identical to G2.
Original G2 refusals remain refusals, without publishing stream descriptors.

Only the opt-in entry `selected_material_parts_observation::observe_binding_parts`
announces diagnostic schema `/3`. It publishes the four physical part records
from that owned header: packed count/size word, raw four-bit count and 28-bit size,
dimensions, canonical 64-bit key and three opaque descriptor words. A declared
count above four is flagged outside bounds; it never controls a memory walk.
Native raw 32-bit format and its first byte are both retained because the primary
layout descriptions differ in format field width. No masking, format conversion,
package guess, pointer address, pixel copy or allocation-retention claim is added.
The separate [fixture](selected_material_parts_observation_fixture.cpp) has an
expected 32 focused checks for raw field widths/high-bit keys, negative ranges,
exact selection, count bounds, preserved G2 refusal, third capture and budget.
These changed C++ cases remain **uncompiled/unexecuted** at this source stage.

The coordinated future CLI mode is explicit:
`-t7-iw7-material-parts-v1 mp_freerun_04 p7_fre_platform_cap_02 0`.
It selects material slot 0 / image binding 4 / expected hash `0xA0AB1041`, emits
bounded JSON and stops before geometry, XPAK payload decoding or FF output.
The caller/build transition is owned separately; default render bytes, legacy
factories and frozen E5 inputs are preserved. Native compilation and this one
stock probe require their own coordinator slot and exact source/input plan.

After successful real metadata, reuse the qualified selected-XPAK CLI for one
authentic complete object of at most 262,144 decoded/encoded bytes. The primary
[Greyhound reader](https://github.com/Scobalula/Greyhound/blob/22c3d17f7428573042b56f43af0ed2585989bebd/src/WraithXCOD/WraithXCOD/GameBlackOps3.cpp#L588-L643)
uses the first cumulative size or the difference from the preceding cumulative
size for later parts. Preserve the raw words and refuse underflow, zero or
oversized objects; do not substitute a binding hash or truncate an object to one
mip. Keep sRGB as observed. DDS construction must validate the complete decoded
layout before reusing the existing encoder; resident metadata cannot be forged
to admit a streamed object.

The first textured FF is a distinct stage derived from the preserved E5 geometry:
change only material handle 0 to a private material, keep four shoe handles and
the exact mesh/UV/index data, and embed the one authentic diffuse with measured
IW7 material state. The retained beacon recipe supplies a potential packed-color
template, with recipient normal/specular behavior explicitly borrowed rather
than claimed BO3-faithful. Its opaque state/constant inputs need fresh guarded
admission before copying. The existing shoe-only FF/runtime gates need narrow,
reviewed variant support from their owners; the old `750d25d7` plan and `50ca9124`
FF remain immutable. No image payload, DDS or textured FF exists yet.

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

An existing [H1-to-IW7 mapping](https://github.com/bigmangeekf/x64-zt/blob/fab935826c898806855376662a8a03317b3ad8f1/src/zonetool/zonetool/h1/converter/iw7/assets/material.cpp#L146-L150)
suggests a simpler first candidate: `mo_l_sm_replace_i0c0` for separate colour,
`mo_l_sm_replace_i0c0n0` with normal, or `mo_l_sm_replace_i0c0s0n0` with specular.
These use separate IW7 semantics 2/5/8; their actual recipient availability and
own state/constant-buffer sidecars must be established before use. Renaming the
packed shoes template's techset is insufficient. T7 normal/specular channels,
binding hashes, sampler bits and nontrivial UV transforms remain to be mapped.

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

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

The native header is prepared but **not compiled or executed** in this change.
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
the checked sources. The next implementation is a bounded selected-image
capture/publication extension under its own reviewed native plan, not a new
general exporter.

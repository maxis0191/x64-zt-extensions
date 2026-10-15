# Original IW7 DDS/material source seam

`authored_dds_material.py` supplies owned author input to the existing IW7
image/material/FF path. It performs no file queries, writes, tool calls, leases,
extraction or game operations. A Source check does not authorize an FF build.
Original DDS metadata is independent of retail T7 capture, descriptor lifetime,
XPAK identity and `QualifiedObjectMipCount`. Those retail gates stay unchanged.

## Exact API

```python
rgba8_dds(width, height, pixels, *, srgb=False) -> bytes
read_dds(data) -> (resident_image.CompleteImageObject, pixels: bytes)
prepare_material(*, zone, image_name, material_name, texture_slot, dds, template) -> dict
verify_image(dds, dumped_image, *, image_name, iw7_semantic) -> dict
```

`pixels` is immutable RGBA8 bytes in row order. The optional text-recipe wrapper
uses the existing `object_to_dds` encoder; it generates no file. A project can
instead supply an existing owned DDS unchanged. No DDS or bitmap is generated
on disk by this module or its tests. Synthetic test bytes are not a native run.

The v1 DDS input is deliberately explicit: DX10 header, Texture2D, one array
element, one declared mip, unknown alpha mode, no cube/volume/misc flags, tight
pitch/linear size and exactly the full payload. Dimensions are 1..4096 and pixel
bytes at most 16 MiB. The existing 18 typed DXGI formats and sRGB/signed variants
come from `resident_image.FORMATS`; no new format or layout table is introduced.
Zero/default mip counts, legacy headers, mip chains, typeless formats, padding,
premultiplied-alpha metadata and extra payloads are refused. This is an initial
authoring subset, not a statement that IW7 or DDS cannot support other shapes.
Header fields follow Microsoft's [DDS_HEADER](https://learn.microsoft.com/en-us/windows/win32/direct3ddds/dds-header)
and [DDS_HEADER_DXT10](https://learn.microsoft.com/en-us/windows/win32/direct3ddds/dds-header-dxt10).
The stricter accepted subset is our policy; compliant writers outside it refuse.

`zone` is a flat portable name up to 63 characters. Image/material names are
portable alphanumeric/underscore path segments, up to 128 characters total.
Windows devices, traversal, leading commas, wildcards and CSV metacharacters
refuse. No special asset name is embedded in the API. `texture_slot` is the
explicit integer index in the IW7 material's `textureTable`, distinct from the
model's material slot. Only that row's image name changes. Its IW7 semantic,
sampler/hash fields, technique, constants and all other material fields remain.
Authored and recipient image names cannot alias by Windows case folding. Review
caught that missing refusal in the initial Source candidate; the mixed-case
counterexample is retained alongside the corrective commit.

## External template bytes and recipients

`template` maps roles to already owned immutable bytes, each nonempty and at most
256 KiB. It never points the module at a filesystem path:

| Role | Input and retained use |
| --- | --- |
| `material` | Original IW7 material JSON, not a foreign shader/material layout |
| `statebits` | Exact 152-byte IW7 technique-index array |
| `statebitsmap` | Nonempty JSON state map; state indices must fit it |
| `stateinfo` | JSON state flags; required when material `stateFlags` is absent/null, otherwise optional |
| `cbi`, `cbt` | Both required for a nonempty constant table: 152-byte indices and original nonempty buffer; no native buffer-layout proof is inferred |

No template retail content is embedded here. Existing template files must be
supplied explicitly by the project's admission/ownership layer. The byte-preserved
state/buffer sidecars are renamed under the selected material and its unchanged
technique. Layered submaterials are outside v1. The existing content inspector,
strict source reader and native build/readback remain responsible for full
material/state/buffer/shader closure; this seam is not a replacement validator.

`prepare_material` returns `files`, a mapping of source-relative paths to bytes:
the unchanged DDS, material JSON, renamed sidecars, recipient CSV and zone CSV.
It also returns `material_reference` for the existing single model surface,
`texture_slot`, an `image` metadata object (name, dimensions, typed DXGI,
namespace, explicit mip count, byte count, pixel/DDS hashes and IW7 semantic),
and `recipient_references` with `techset` and the unchanged other `images`.
The CSV references that technique and those images explicitly; it does not
pretend they are original authored shaders/textures. The SDK appends its model
and behavior inputs using existing interfaces. No geometry serializer is added.

`verify_image` delegates to the unchanged `verify_iw7_object`: actual image name,
semantic, format, dimensions/mip count and all pixel/block bytes must agree with
the DDS. Model binding, material state/CBT, rendering, audio and owner acceptance
remain separate. Returned preparation flags `ff_built`, `material_verified`,
`rendered_verified` and `ready` are false. Successful image-byte readback still
reports material/render false.

## Acquired proof and next proof

Material C already demonstrated a real native six-phase FF build/readback of an
original 32x32 diffuse, as recorded in [CONTENT-SURFACES-BRIDGE](../../../../docs/CONTENT-SURFACES-BRIDGE.md#material-c-complete-native-pipeline-and-restoration-confirmed).
Its preserved generator and 32x32 oracle remain frozen. This new pure seam tests
two distinct names, dimensions, formats and original byte patterns through the
same API, but has not built an FF or rendered either project. The next separately
admitted witness must consume the SDK's second project, original serializer and
existing build/runtime lifecycle, then check independent readback and rendering.
It must not inherit Material C's acceptance or weaken retail T7 mip gates.

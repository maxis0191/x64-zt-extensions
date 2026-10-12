# Original H1 parser fixture, source-only checkpoint

This directory can emit a tiny original H1-format cube without a donor game.
The bytes target the actual pinned `h1::xmodel::parse` and
`h1::xsurface::parse` methods. They are not preconverted IW7 bytes. Neither the
production parser nor the production converter has been executed for this
fixture. Python validation is a separate format/geometry check.

The scope is deliberately incomplete: the XModel contains one **explicit named
material reference**, as read by production `read_asset<Material>()`, but no
complete H1 material, technique, shader or texture payload. This is not a
renderable asset package, a closed material test, a fastfile or retail-H1
compatibility evidence. That gap must not be hidden behind a dummy material.

## Source contract and outputs

Source pin: `bigmangeekf/x64-zt` at
`fab935826c898806855376662a8a03317b3ad8f1`. The generator checks HEAD plus
LF-normalized SHA-256 of the exact relevant source files. It reads those files
in place; no SDK/header tree is copied. Source hashes are in
`source-contract.json`; generated assets remain ignored under `generated/`.

| Contract | Pinned source location |
| --- | --- |
| H1 XMB record order | `src/zonetool/zonetool/h1/assets/xmodel.cpp:30-121`; matching dump at `:461` |
| H1 XSB record order | `src/zonetool/zonetool/h1/assets/xsurface.cpp:36-106`; matching dump at `:445` |
| x64 ABI | `h1/structs.hpp:3975` vertex (32 B), `:4037` rigid list (16 B), `:4160` surface (264 B), `:4199` surface group (56 B), `:4333` model (680 B) |
| Typed stream | `zonetool/utils/io/assetmanager.hpp`: ARRAY=8, STRING=6, ASSET=7, RAW=10; one-byte presence; uint32 array count; null-terminated ASCII names |
| H1 frame packing | `src/zonetool/game/shared.cpp:400-408`, `Vec3PackUnitVec_H1`; UVs use exactly representable half-float 0/1 |
| Actual conversion | `h1/converter/iw7/assets/xmodel.cpp:15`, `xsurface.cpp:82`; ordinary vertices and self-visibility path, no reactive-motion shortcut |
| Dispatch boundary | `h1/zonetool.cpp:390-454`, `dump_asset_iw7` receives already loaded H1 XAssets |

Paths in the ABI/conversion rows are relative to `src/zonetool/zonetool/`.
The source structs' field order and explicit `assert_sizeof` values establish
the serialized layout. Native `offsetof`/ABI acceptance is still pending.

The original cube is 16 units wide, centered at the origin: 24 face-local
vertices, 12 outward triangles, 1 surface, 1 LOD, 1 root bone (`tag_origin`),
1 rigid vertex list, white vertex colors, per-face normals/tangents and positive
UV handedness. There is no skinning, collision tree, physics, subdivision,
reactive motion, blend shape, lightmap or optional raw stream.

The model references `paris_h1_original_material` and
`paris_h1_original_cube_lod0` by production ASSET records. Header pointers are
zero: the actual parser replaces them from subsequent records. No process
address is emitted. Both triangle arrays contain original equivalent topology;
the source converter uses the first array. The reader checks the second too.

## Light reproduction

Use Python 3.12, absolute paths and a fresh output directory. These commands do
not execute native code or acquire a heavy-work lease.

```powershell
python -B tools-source/asset-bridge/h1-fixture/test_fixture.py
python -B tools-source/asset-bridge/h1-fixture/generate.py `
  --source-repo <existing-pinned-x64-zt-directory> `
  --output <absolute-fresh-directory>
python -B tools-source/asset-bridge/h1-fixture/inspect_fixture.py `
  <generated-xmodel-path> <generated-xsurface-path>
```

The generator refuses existing output and reparse ancestry. It writes three
files with exclusive creation, verifies the emitted bytes and limits their
combined size to less than 1 MiB. This is a cooperative-file guard, not a
hostile filesystem sandbox. The inspector deliberately accepts only this
fixture profile and rejects OFFSET records and unsupported streams.

Tests include every truncated prefix, wrong record tags/counts, corrupt
references/pointers, nonfinite vertices, bad topology, wrong packed normals,
degenerate UVs, wrong rigid coverage and unexpected optional streams. The frame
oracle derives normals and tangents independently from triangle positions/UVs;
it does not merely decode the generator with its inverse. Golden hashes bind
reproducibility, not native acceptance.

## Precise remaining gaps and next observation

1. **Actual parser-to-converter invocation.** A separately authorized native
   consumer must register the fixture directory in the real file search path,
   call production `h1::xmodel::parse(MODEL, zone_memory)` and
   `h1::xsurface::parse(SURFACE, zone_memory)`, check actual ABI/counts/references,
   then pass those returned objects to the real
   `h1::converter::iw7::{xmodel,xsurface}::convert` functions. Use the reviewed
   surface patch already owned by the model branch. No handwritten reader,
   converted struct constructor or replacement converter can establish this
   witness. The existing command-line dump route instead loads the H1 game
   binary (`main.cpp:180`) and database assets; writing XMB/XSB alone does not
   create a donor-free command-line conversion route.
2. **Bone strings before any IW7 dump.** H1 `xmodel::parse` records `tag_origin`
   in a private string table; its raw numeric bone token is intentionally zero.
   `prepare` normally turns those strings into zone-buffer indices. Direct
   XModel conversion only aliases that array, while `iw7::xmodel::dump` calls
   the engine `SL_ConvertToString`. Calling dump directly on the parsed model
   therefore is not a demonstrated valid path. A native consumer may inspect
   converted fields first, but emission needs a reviewed genuine string
   resolution path, with no invented live engine ID.
3. **Complete material.** `h1/assets/material.cpp:199-340` expects a named
   technique and its statebits. An empty technique leaves zero state entries
   and hits `max_state_index >= stateBitsCount`; an empty JSON is not a valid
   shortcut. The mesh converter only copies a material name. Loading or
   converting that name stub as a full Material would be invalid. The next
   independent material work must establish original shader/technique/statebit
   authoring or an explicit, verified recipient-material binding; the latter
   tests geometry/reference mapping, not H1 material conversion.

No native compilation, binary execution, FF build, extraction, game, download,
retail data read, shared-source modification or Main/voice change occurred.
This source-only sub-lot is handed to the coordinating branch for review and
the project's private integration/CI/merge workflow.

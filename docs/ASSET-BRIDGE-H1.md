# H1 -> IW7 model bridge: bounded source checkpoint, 2026-10-12

The owner-fork converter has a prepared correction for silent blend truncation,
unaligned H1 bone offsets and a subdivision flag read before its count is copied.
The patch is reproducible and applies to the pinned real converter. It has **not
been compiled or executed natively** in this lot. The standalone Python bridge
converts and verifies raw blend records; it is not a complete H1 model importer.

The parent coordinates integration, private PR/CI/merge and the heavy-work GO.
No game, native compilation, extraction, audio capture, native Add-Type, lease,
SDK copy or change to Main/client/bank/config occurred. Existing owner-fork and
historical worktrees were read only. Source preparation stays below 100 MB.

## Delivered code and how to use it

All files are under `tools-source/asset-bridge/model/`:

- `blend_bridge.py`: H1 raw little-endian blend words -> IW7 raw words, independent
  readback, exact source correspondence and create-only output.
- `test_blend_bridge.py`: ten unit tests, including 100 deterministic original
  fixtures, literal golden records for all four supported influence groups,
  malformed/truncated/extra bytes, invalid counts, bone bounds, misaligned offsets,
  padding, changed weights and refused output overwrite.
- `zonetool-fab9358-h1-xsurface.patch`: actual owner-fork converter correction.
- `prepare_zonetool_patch.py`: regenerate that patch from the exact clean pin.
- `verify_zonetool_patch.py`: regenerate/compare, apply and reverse-check the patch
  on a temporary copy of its sole source file. Never patches the shared fork.
- `verify_retained_two_bone.py`: re-read existing October 7 XMB/XSB files using
  their retained independent reader, check exact hashes, compare actual blend
  data with the H1 bridge. It does not rebuild or re-emit them.
- `validation-2026-10-12.json`: sanitized light-test and retained-output evidence.

The raw bridge metadata is intentionally narrow:

```json
{
  "schema": "iw7.asset-bridge.h1-blend/1",
  "blend_vert_counts": [4, 4, 0, 0, 0, 0, 0, 0],
  "vertex_count": 8,
  "bone_count": 2,
  "rigid_vert_list_count": 0
}
```

Pass absolute local paths. Inputs are bounded (metadata 4 KiB, blend 1 MiB).
The output must be a fresh `.u16.bin` in an existing directory. Input/output
links and reparse ancestry are refused; the file is created exclusively. This
is a cooperative local-file guard, not a hostile filesystem race sandbox.

```powershell
python -B tools-source/asset-bridge/model/test_blend_bridge.py
python -B tools-source/asset-bridge/model/blend_bridge.py `
  --metadata <absolute-metadata.json> --h1-blend <absolute-h1.u16.bin> `
  --output <absolute-fresh-iw7.u16.bin>
python -B tools-source/asset-bridge/model/verify_zonetool_patch.py `
  --source-repo <absolute-existing-pinned-owner-fork>
```

The counts must cover every vertex with zero rigid lists, each H1 signed-short
count must be nonnegative, and only groups 1..4 are supported. `bone_count` is
1..255 because pinned H1 `XModel::numBones` is uint8. The bridge checks every
bone ID against that supplied count; it does not independently parse the model
to establish it. Client bones and extended palettes are outside this profile.

Source layout is 1/3/5/7 uint16 words per vertex. Bone positions are 0, then
1/3/5; they contain IDs multiplied by 64. Weight positions 2/4/6 are preserved
verbatim, including values above 255. Output uses 2/4/6/8 words: raw bone IDs,
unchanged weights, final zero. No weight normalization, clamping, ordering
change or inference about which bone receives a weight occurs.

## Real converter correction

Owner fork: `bigmangeekf/x64-zt`, exact source revision
`fab935826c898806855376662a8a03317b3ad8f1`. No official update check was repeated.
The single patched file is:

`src/zonetool/zonetool/h1/converter/iw7/assets/xsurface.cpp`

| Finding in the pinned source | Prepared behavior | Verification boundary |
| --- | --- | --- |
| `convert()` copies eight blend counts; `PackIW7BlendVerts()` writes only groups 1..4 | Reject every nonzero group 5..8 before blend allocation/emission | No guessed higher-influence layout |
| H1 counts are signed; copied counts become unsigned | Reject negative counts and sum above surface vertex count | Native routine can still allow rigid/unblended remainder; raw bridge deliberately requires full coverage |
| Nonzero counts can have a null blend pointer | Reject before dereference | Native struct carries no buffer length; truncated allocation still requires parser-boundary validation |
| Every bone offset is divided by 64 without validation | Scan only bone words and reject nonmultiples before conversion | Native surface alone has no model bone count; raw bridge adds that supplied bound |
| Subdivision flag tests zero-initialized destination count before `COPY_VALUE` | Test `surf->subdivLevelCount` at that point | Does not prove H1/IW7 subdivision payload compatibility or runtime rendering |

The patch retains the existing 1..4 packing loops and all weight words. The
native validator allows a zero-blend static surface; the standalone raw bridge
is a separate, explicitly skinned profile. Errors use the existing C++ exception
path. Nothing is written by `xsurface::dump()` until `convert()` returns.

LF-normalized source hashes:

- Base: `db44ec1166c6f0cbb3af0ad21631154b8e3b00b42aac042b59e79c1ced4d24ce`.
- Patched: `f0910695382533abf9aed8a0c03f2f0da9d9af1ce2baee0efb5e78d252218a15`.
- Patch bytes: `e50c7f18b9e3b8904b441ddf10bb32a3315442d22afec7d174bda699f9db26a0`.

One verifier attempt initially compared Git's CRLF checkout bytes with the
advertised LF hash and failed. The corrected verifier normalizes CRLF only for
that comparison, then checks reverse application. This was a verification
defect, not a native execution failure. The shared fork remains unchanged.

## XModel, references and fastfile boundaries

Source locations below are relative to the pinned ZoneTool checkout. These are
source observations, not claims that arbitrary H1 assets render correctly.

| Area | Existing source behavior | Remaining obligation |
| --- | --- | --- |
| `h1/converter/iw7/assets/xmodel.cpp` | Copies names, roots, parent/tag/bind, boneInfo, bounds and scale; creates named material and LOD-surface references | Validate skeleton hierarchy, finite transforms, LOD count/ranges and required dependency pointers before accepting general input |
| XModel LOD policy | Copies source LOD distances; sets `shadowCutoffLod=6`, `characterCollBoundsType=1`, unknown indices 255 | H1 material/draw/culling acceptance is still required; previous rigid-model witness does not settle arbitrary models |
| Model feature loss | Sets physicsAsset/physicsFXShape null; does not implement a general H1 physics/blend-shape/procedural-bone conversion | Reject or explicitly inventory unsupported features in the future model importer; do not advertise lossless conversion |
| `h1/converter/iw7/assets/xsurface.cpp` | Expands ordinary packed vertex to IW7 with selfVisibility; copies normal/tangent words, triangle/rigid/subdivision/tension references; converts lightmap half UV to float | Validate optional stream layout and closure independently; the new patch does not complete these codecs |
| `iw7/assets/xmodel.cpp` | Writes model data in virtual stream; prepares bone script strings; resolves material and LOD assets through `zone->get_asset_pointer` | Named XMB references do not prove closure in the future FF |
| `iw7/assets/xsurface.cpp` | Writes surfaces in virtual stream; clears GPU views; aligns vertices/triangles to 16 bytes, rigid arrays to 8, blend to 4; writes `blendVertSize & ~1` and clears that pointer for relocation | Raw blend bytes have no FF alignment/relocation. Exercise actual FF writer/loader before accepting them |
| XModel array fixups | Parent alignment 1, tag angles 2, tag positions 4, baseMat 16, boneInfo 4, invHighMipRadius 2, material handles 8 | Values are byte alignments (`align` takes mask); do not confuse XMB dump records with final FF streams |

The standalone bridge emits neither XModel nor XSurface nor XAnim. Material
conversion and animation/AI remain with their owning chats; no SDK manifest was
changed. No existing rigid reader/profile was relaxed to admit skinned records.

## Reuse of the October 7 writer and independent reader

The retained V5 evidence, under historical
`docs/deployments/2026-10-07-doom-two-bone-owned-admission-partial.json`, distinguishes
earlier wrapper failures from its successful compilation/emission/readback. V5's
summary publication itself failed after cleanup; it is not a fully successful
wrapper run. This task did not repeat that compilation.

Fresh October 12 Python reads consume all four existing files and match V5:

| Profile | XMB bytes / SHA-256 | XSB bytes / SHA-256 |
| --- | --- | --- |
| first | 1114 / `c979c54ac158dcc9ad648efe2542831f4250b13805b8232e218866a15ac0d856` | 730 / `aef640e642c7e0eeef0d5cf2a483a8d349a4e5514c4528c8ac77998794ba4fdc` |
| second | 1116 / `67fc685e892dff9f46c10923e0c2c9819ed38f9cec502bdfb6349b3d2ff7a620` | 731 / `118343bf0f75df1fe4bc3be71d93b9d895f4f899fb5301f5dee0f157767574ae` |

Each is 2 bones/1 root, 1 LOD/surface, 8 vertices, 6 triangles, 48 blend bytes,
zero rigid lists. The original H1-layout examples convert to exactly those
48-byte blobs in both profiles. Full independent XMB/XSB reading and the CPU
bind oracle also pass. This is an original synthetic mesh, not an extracted H1
asset or evidence of H1 in-engine compatibility.

The two weight interpretations remain deliberately unresolved. CPU quantization
error is about 0.0042446753 units for the corresponding interpretation; swapping
it produces about 2.1605397253. Neither a matching dump nor `setmodel` proves the
engine convention. PartBits, shader words/handedness, planar bounds/culling,
actual deformation, FF loading and rendered pixels remain pending.

To reproduce the read-only check, supply the retained trusted Python reader,
original input bundle and V5 build directory:

```powershell
python -B tools-source/asset-bridge/model/verify_retained_two_bone.py `
  --reader <absolute-historical-ops/doom-source/read_skin_native.py> `
  --inputs <absolute-two-bone-input-directory> `
  --build-dir <absolute-two-bone-build-reviewed-20261007-v5>
```

Local historical roots are recorded in the coordinating chat, not embedded as
machine-specific settings. Assets, SDK headers, native executables and raw logs
remain ignored and outside this deliverable. Existing stale reader comments
that say no native files were emitted are superseded by the V5 evidence and
this fresh readback; the historical files themselves were preserved.

## Next decisive experiments and budgets

1. After the parent's GO, apply the checked patch in a separately owned source
   checkout of the same owner-fork pin. Build with the reviewed resource helper,
   one compiler node, estimated **4 GiB physical / 6 GiB commit**. Exercise the
   real converter on original 1/2/3/4-influence fixtures and every refused case,
   including zero-blend rigid input and both subdivision-count branches. Compare
   output words with the literal/Python oracle. Gate any H1 asset work on this;
   light Python tests and Git patch application are not native-test evidence.
2. Use the already emitted two-bone XMB/XSB to prepare a distinct minimal FF
   closure; do not rebuild the writer. Require explicit names, matching hashes,
   material binding, FF fixups and no optional streams. Plan **6 GiB physical /
   8 GiB commit** for an admitted minimal tool invocation, then release it before
   gameplay. Target <=100 MiB new candidate output; measure and stop before
   exceeding that per-experiment bound. Never duplicate stock, SDKs or PDBs.
3. Reuse the retained test dedicated and base client sequentially. The parent
   admits the complete full-quality pair (up to **16 GiB physical / 16 GiB
   commit**, estimates subject to the actual scenario), fresh engine protection
   and restoration. First verify visible mesh/LOD/material; only a separately
   owned real pose/deformation witness can choose the two weight conventions.
4. Feed a minimal legitimate H1 mesh into the same declared SDK closure only
   after native conversion passes and unsupported features are inventoried.
   A community beacon or two-player join/cache test is a downstream integration
   witness; success with its original rigid mesh is not an H1 import result.

No reservation is held now. Parent authorization, resource admission and the
aggregate future-data ceiling remain in force; these estimates do not lift the
active heavy-work gate or establish owner gameplay acceptance.

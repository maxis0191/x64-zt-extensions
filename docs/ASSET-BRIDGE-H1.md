# H1 -> IW7 model bridge: converter checkpoint, 2026-10-12

The owner-fork converter has a prepared correction for silent blend truncation,
unaligned H1 bone offsets and a subdivision flag read before its count is copied.
The patch is reproducible and applies to the pinned real converter. Its exact
validator, packer and converter bodies now compile and execute in the bounded
native fixture: **52 assertions pass**. The full ZoneTool application, FF loading
and rendering remain untested by this task. The standalone Python bridge
converts and verifies raw blend records; it is not a complete H1 model importer.

The parent coordinates integration, private PR/CI/merge and the heavy-work GO.
The initial source lot performed no heavy work. A later explicit parent GO
authorized one 4/6 GiB native-fixture group, completed and released below. No
game, extraction, audio capture, SDK copy or change to Main/client/bank/config
occurred. Existing owner-fork and historical worktrees were read only. Source
preparation stays below 100 MB; new native artifacts stay below 10 MiB.

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
- `native-validation-2026-10-12.json`: actual compile/link/fixture result, hashes,
  admission and release evidence, with the preserved compiler warning.

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

1. The minimal real-function native fixture now passes; do not repeat its build
   without changed inputs or a new unresolved concern. After a further parent
   GO, integrate the checked patch in a separately owned source checkout of the
   same owner-fork pin and build the full tool with the reviewed resource helper,
   one compiler node, estimated **4 GiB physical / 6 GiB commit**. Exercise the
   real converter on original 1/2/3/4-influence fixtures and every refused case,
   including zero-blend rigid input and both subdivision-count branches. Compare
   output words with the literal/Python oracle. Gate general H1 asset work on
   this integration; the isolated fixture does not exercise dump/FF emission.
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

## Prepared native fixture of the real converter

`prepare_native_fixture.py` now prepares `native_fixture.cpp` and a generated
`native_production.inc` in a fresh ignored directory. It applies the pinned patch
to one temporary source file, verifies its final hash, and extracts the exact
`ValidateH1BlendVerts`, `PackIW7BlendVerts` and complete `convert` bodies. The
three conversion macros are copied verbatim from the pinned header. Real H1/IW7
struct headers and allocator declarations/templates are hashed and read in place;
no SDK/header tree is copied. The generated source totals 14,941 bytes.

The test plans literal 1..4-influence words, all malformed bone offsets, negative
counts, unsupported groups, count overflow, null data, empty rigid input and both
subdivision-count branches through the actual `convert()` function. It checks
refusal before output allocation. Actual ABI sizes/static assertions are enabled.
Only allocation/free are a bounded fixture adapter. Lightmap/selfVisibility
helpers throw if invoked; the subdivision flag fixture uses a motion vertex to
avoid claiming unrelated codec coverage. No dump, FF, D3D, animation or game is
linked or run. A future passing fixture does not replace the full ZoneTool build.

```powershell
python -B tools-source/asset-bridge/model/prepare_native_fixture.py `
  --source-repo <absolute-existing-pinned-owner-fork> `
  --output <absolute-fresh-native-fixture-directory>
```

The preparation receipt records the exact MSVC C++20 arguments (including both
existing include roots and explicit OBJ/EXE output paths). It never invokes them.
After parent GO, recheck the recorded source/header hashes, use the existing x64
compiler environment and the admitted native-job wrapper, then compile and run
the resulting exact fixture. Budget up to 4/6 GiB physical/commit and <=10 MiB
generated build files. The original preparation proved source consistency and
overwrite refusal. The subsequent native result below supersedes the earlier
no-execution state for this fixture only.

## Actual bounded native run, 2026-10-12 02:03 UTC

The parent lifted the gate for this one fixture group after the two priority
sessions ended. Current private `origin/main=24d5c4f799b295cced57abea845fa1c39c753f09`
was fetched and merged before action; the resource/memory helpers match that
revision. RESOURCE, INSTANCE and STORAGE were refreshed. Atomic admission
reserved **4 GiB physical / 6 GiB commit**, with RAM reserve zero and unchanged
20% commit headroom. No second group was requested or started.

MSVC 14.44.35207 x64 compiled the prepared file with `/c /std:c++20 /EHsc /W4 /MT`,
without `/MP`, followed by a separate synchronous link with `/INCREMENTAL:NO` and
then the fixture. All three processes were observed BelowNormal, exited zero
and had their exits confirmed through their retained original process objects
and handles. The parent priority/PATH were restored. The reservation was released;
the 02:03:03.5125170Z snapshot contains zero leases and no high-water condition.

All **52 runtime assertions** passed. These include allocator-budget assertions,
golden 1..4-influence output/preserved input, 18 malformed-input refusals before
blend allocation, empty rigid input and both subdivision flag branches through
the real `convert()`. Real H1/IW7 headers and their size assertions were compiled.
The checked production LF hash remains
`f0910695382533abf9aed8a0c03f2f0da9d9af1ce2baee0efb5e78d252218a15`.

- EXE: 320,512 bytes, SHA-256
  `a88052927daec4a4c343076368d2946e660771a2c6db802acdf6fd7abcce3d65`.
- OBJ: 374,912 bytes, SHA-256
  `ac9e386db07d8a1bf1e6d96c468e8fe0afc3186509235aa2b5333eda596341d6`.
- First attempt succeeded; no failed candidate or corrective rebuild occurred.
  Compiler warning C4244 at fixture line 144 reports the `{0,1}` int initializer
  conversion to unsigned char. Both values are representable and both branches
  passed. The original source/log is preserved; no warning-free build is claimed.

The execution directory, including logs and before/after receipts, is about
0.71 MB. The EXE/OBJ and raw local diagnostics remain ignored; Git receives only
sanitized evidence. Native allocation/free use the documented test adapter;
optional codecs deliberately throw if reached. This proves the selected real
converter functions under that fixture, not the full tool allocator, arbitrary
dump safety, optional stream compatibility, FF relocation/loading, bone-weight
interpretation, shader correctness, visual deformation or owner acceptance.

## First full ZoneTool candidate: source-only reuse plan

This plan follows the parent's next request; it starts no second heavy group.
The animation chat owns the newly allocated group. The bounded inventory is in
`tools-source/asset-bridge/model/full-build-plan-2026-10-12.json`.

The retained clean `x64-zt-enemy` checkout is still at `fab9358`. Its existing
Release x64 executable is 21,161,472 bytes, SHA-256
`a2cba8b0c34493fcddb5dc82e034e678c948f5c80d5b4454a93792e8e256b1d9`.
`build/x64-zt.sln` and `build/zonetool.vcxproj` exist; the latter contains 413
compile units and 18 dependency-project references. Fourteen submodules are
already present at their recorded pins. The retained build occupies:

| Retained input | Measured logical bytes | Reuse policy |
| --- | ---: | --- |
| All object/intermediate directories | 1,127,437,788 | Preserve, no bulk copy |
| ZoneTool-only intermediates | 875,658,470 | Fresh candidate objects; do not share mutable outputs |
| ZoneTool PCH within that total | 277,938,176 | Fresh candidate PCH: macro configuration changes |
| ZoneTool compiler PDB within that total | 43,020,288 | Do not copy; generate candidate symbols if enabled |
| 20 existing libraries | 256,258,974 | Resolve the 18 referenced dependency libraries read-only; exclude the tool's own import library |
| Existing final ZoneTool PDB | 132,345,856 | Preserve in place; never copy to seed the new build |
| TLS helper DLL embedded by resource.rc | 113,152 | Read the retained file in place |

The material/source patch from commit `992f3f6` has SHA-256
`4d7049216f24474e077ab704dac625c7f335c8264434b7de525e56a96a988d08`.
It changes IW7 `material.cpp`, `techset.cpp`, `gfximage.cpp`; the H1 patch changes
only `h1/converter/iw7/assets/xsurface.cpp`. Both patches were applied sequentially
and reversed on four temporary original files, with exact resulting hashes in
the inventory. No conflict or shared-source modification occurred.

Two source findings prevent blindly reusing the old command:

1. The retained Release project does **not** define `EXPERIMENTAL_IW7`.
   `h1/zonetool.cpp::dump_asset_iw7` and eleven converter translation units are
   conditional on it. A default build could compile the patched filename while
   excluding its actual functions. The candidate must explicitly define the
   macro across its own project/PCH and preserve a compiler-command witness.
2. Current-main `ops/Build-RhinoZoneTool.ps1` still regenerates Rhino overlays from
   `a4cec149f0dd34aa13e37e8f7ab754af11e122ec`. The first guarded file,
   `component/exception.cpp`, differs from both that base and the helper-generated
   inline-headless version; it has no ownership stamp. The helper also copies
   `zonetool_rhino.hpp` before that refusal. Its ancestry check alone passes but
   does not make it compatible. **Do not invoke it on the retained checkout** or
   pretend it builds the requested clean `fab9358` candidate.

The proposed minimal isolation is a reviewed project/source overlay in one new
owned runtime directory, not another SDK/game/toolchain checkout:

- Copy only the generated 110,595-byte ZoneTool project, the four patched C++
  files and small version/resource source files. Input bytes/hashes remain pinned.
  Keep this preparation below 2 MiB; no dependency directories, PDBs or binaries
  are copied. A full fork source checkout would be about 16.33 MB without
  submodules, but is unnecessary for this first candidate build.
- Rewrite project source/header paths to absolute retained inputs, except the
  four owned patched files. Each patched file gets its **own original parent
  include directory**, so H1/IW7 files named `xsurface.hpp` cannot shadow one
  another. Reuse dependency include directories through absolute read-only paths.
- Remove dependency `ProjectReference` entries; link their exact existing Release
  libraries explicitly after input hashes/configuration are checked. Keep the
  retained static-runtime convention. Do not rebuild or write through those
  dependency projects.
- Set private absolute `IntDir`, `OutDir`, compiler PDB/PCH, linker PDB/import-lib,
  resource and tracking-log outputs. Generate fresh objects/PCH for all 413
  translation units with `EXPERIMENTAL_IW7`; do not mix the disabled baseline
  objects with newly enabled H1 code. Preserve the existing C++23, `/W4 /WX`,
  static runtime, optimization and linker conventions.
- Remove pre/post-build events and implicit user property-sheet imports from
  the reviewed overlay. In particular, the original pre-build command runs
  `premake5 generate-buildinfo` in its parent; it must not touch retained sources.
  Supply a small candidate version header with source/patch provenance. Give
  `resource.rc` explicit retained paths for the icon, existing compressed tool
  resource and `tlsdll.dll`; no game/SDK/resource copy is needed.
- Before admission, review/evaluate every final project input/output and reject
  any mutable path outside the candidate root. Record baseline hashes/metadata.
  Compile only after a new parent GO; preserve failure output before correcting.

The reusable part of the current helper is its scheduler/MSBuild tail, not its
old overlay mutation. Once the described candidate project is prepared/reviewed,
the concrete equivalent invocation is:

```powershell
. <current-private-repo>/ops/Resource-Scheduler.Core.ps1
Invoke-IW7ResourceJob -Scope <absolute-candidate-root> -Kind Build `
  -Owner 'Pinned H1 and strict-source ZoneTool candidate' `
  -PhysicalBytes 4GB -CommitBytes 6GB -Body {
    & <existing-VS2022>/MSBuild/Current/Bin/MSBuild.exe `
      <absolute-candidate-root>/zonetool-community.vcxproj `
      /m:1 /nr:false /v:minimal /p:Configuration=Release /p:Platform=x64 `
      /p:MultiProcessorCompilation=false /p:BuildProjectReferences=false
    if ($LASTEXITCODE) { throw 'Full candidate ZoneTool build failed.' }
  }
```

This is a plan, not a generated or executed new builder. Parent admission remains
atomic and authoritative. Keep the identified compiler/MSBuild job, BelowNormal
priority and closure evidence; do not launch any candidate game/extraction/FF as
part of this group. Estimated new outputs are **1.4 GiB**, with a **2 GiB hard
ceiling**, from the measured approximately 1.03 GB old tool intermediates plus
EXE/final PDB and margin. New symbols are generated, not copied. Enabling the
previously disabled converters can expose real compile/link errors or increase
output; stop and report if the ceiling is approached, never borrow more disk or
lower RAM/commit estimates to pass admission. No full-build runtime/FF/visual
result is established by this source inventory and plan.

## Full-build overlay and launch preflight

`prepare_full_build.py` creates a small project/source overlay from the clean
`fab9358` fork and the two pinned patches. `verify_full_overlay.py` verifies 413
compile inputs, four patched inputs, 18 retained libraries, explicit
`EXPERIMENTAL_IW7`, private object/PCH/PDB/resource/link/tracking outputs, and the
absence of dependency projects, user property imports and source-mutating build
events. The first preparation used 409,603 bytes; no dependencies were copied.

`Build-FullZoneTool.ps1` uses the current resource scheduler with 4 GiB physical
and 6 GiB commit admission. Its small `BuildJob.cs` owner creates MSBuild suspended
and BelowNormal, assigns its original handle to a kill-on-close Windows job,
registers the PID with the scheduler, then resumes it. MSBuild is one node,
node reuse is disabled and compiler multiprocessing is disabled. All descendants
remain in the owned job. The runner polls artifact size and commit pressure;
the conservative stop point is 1,600 MiB, preserving 448 MiB of margin below the
2 GiB hard ceiling. This is monitored admission, not a kernel disk quota.

The first admission on 2026-10-12 at 02:20:30Z exercised a `cmd`/`ping` child
containment fixture before starting any MSBuild or compiler. The fixture stopped
its job but found that zero active job processes can briefly precede the root
handle's termination signal. The finalizer subsequently confirmed both conditions,
preserved the failure receipt, verified retained inputs unchanged and released
the lease (`0078def8e24542bfa02589aa722115a5`). No compiler ran. The correction
waits for both job emptiness and the original process signal, including cleanup;
a fresh coordinator allocation is required before its native revalidation.

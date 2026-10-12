# World asset bridge: source preparation

Evidence date: 2026-10-12. This work maps the retained H1-to-IW7 converter and
implements a bounded client-trigger record adapter using original data. It does
not produce a playable custom map, an IW7 fastfile, or a BO3-style map editor.

## Source and ownership

- Project baseline: `178708bde0ee18fc552007aa3b6475477b82aae9`.
- Retained ZoneTool pin: `fab935826c898806855376662a8a03317b3ad8f1`.
- The retained checkout is read-only. No SDK, retail stock or game client was
  copied; no download, extraction, native compilation or game launch occurred.
- This contribution owns only this document and
  `tools-source/asset-bridge/world/`. The parent chat owns integration, resource
  admission, private PR, exact-head CI and merge.
- `source-contract.json` binds eleven inspected source files to the pin with
  SHA-256 hashes after CRLF-to-LF normalization. Line references below refer to
  that pin. Paths in the source table are relative to
  `src/zonetool/zonetool/` in ZoneTool, not this repository.

## Existing routes and their limits

`h1/zonetool.cpp:390-454` dispatches H1 assets to IW7 converters under
`EXPERIMENTAL_IW7`. These are conversions of already compiled H1 asset
structures. Their presence does not establish an original geometry compiler or
an end-to-end working map pipeline.

| Route | Source evidence | What still prevents a readiness claim |
| --- | --- | --- |
| World render: H1 `GfxWorld` to IW7 world, lightmaps and transient zone | `h1/converter/iw7/assets/gfxworld.cpp:615-663` copies vertices, layers, cell bounds and indices into one transient zone; `:1076-1087` dumps the world, lightmaps and transient zone. IW7 readers use `.gfxmap` and `transient_zones/<name>.gfxmap_tr`. | Source contains a lightmap reindex TODO (`:577-578`), generated lightmap/texture placeholders (`:589-607`), and reused H1 Umbra tome data (`:921-934`). The same-size vertex copy is not render or semantic compatibility evidence. No original BSP, visibility, material, lighting or Umbra authoring pipeline was demonstrated. |
| World collision: H1 `clipMap_t` to IW7 `clipMap_t` | `h1/converter/iw7/assets/clipmap.cpp:377-451`; `generate_clip_info` copies only planes (`:377-381`). | `havokWorldShapeDataSize = 0` and data is null (`:441-442`); physics capacities are not populated (`:439`), broadphase limits are constants (`:432-437`), and the top-down map is null (`:447`). No H1 brush/patch-to-IW7 collision cooking is present here. |
| Map entities and client/server triggers | The clipmap converter generates MapEnts (`clipmap.cpp:73`), copies trigger hulls/slabs, expands models (`:84-130`), remaps type flags (`:137-141`), then dumps MapEnts before clipmap (`:459-467`). `iw7/assets/mapents.cpp:154-180` reads native `.ents.data` arrays plus separate entity/spawn/spawner content. | Entity token conversion (`clipmap.cpp:16-50`) is a token-name rewrite, not a full script/API migration. Entity Havok data is empty (`:185-186`); submodel physics assets are null (`:188-197`). Dynent conversion also contains assumptions and reserved entries. The new JSON adapter does not implement this native reader format. |
| Common world / lights | `h1/converter/iw7/assets/comworld.cpp:22-54` maps primary light fields. | It sets forward-plus and bake defaults (`:69-70`), synthesizes one environment per primary light (`:79`), and hardcodes build metadata (`:90-92`). This is not a validated lighting bake. |
| FX world | `h1/converter/iw7/assets/fxworld.cpp` converts glass/FX records and dumps IW7 output. | Glass physics assets are null (`:66`), a mip conversion remains questioned in source (`:76`), and reused runtime arrays (`:82-93`) are not physics validation. |
| Glass world | `h1/converter/iw7/assets/glassworld.cpp:15-24` reinterprets the structure and dumps it. | A cast does not establish semantic or runtime compatibility. |

Render texture/material/model conversion remains a separate dependency; see
[ASSET-BRIDGE-H1.md](ASSET-BRIDGE-H1.md) and the existing model/surface adapter
sources. No retained stock is suitable proof that a newly authored world works.

## First missing block for a small original map

The first concrete missing data block identified in this source audit is
**IW7 world collision shape data**, `havokWorldShapeData`, with its required
physics capacities and consistent world/submodel references. This is a source
dependency finding, not the first observed runtime failure: no map was loaded.

H1 `ClipInfo` contains brush, patch and static-model collision trees/data
(`h1/structs.hpp:6828-6847`). IW7 `ClipInfo` contains only planes
(`iw7/structs.hpp:3756-3760`); the missing collision representation cannot be
replaced by copying those planes or by adding trigger volumes. The converter
deliberately emits zero world Havok bytes and zero entity Havok bytes.

The IW7 clipmap reader uses a `.colmap` plus a Havok sidecar:
`iw7/assets/clipmap.cpp:78-79` calls `havok::binary::parse_havok_data`, and
`:243-247` writes existing Havok bytes. `iw7/common/havok.hpp:14` supplies the
`.hkx` extension. `iw7/common/havok.cpp:9,24-99` expects the packfile/version
header for `hk_2014.2.5-r1`; its reader (`:102` onward) validates header fields
and copies supplied bytes. Its XML namespace is empty (`:17-20`). It is neither
a geometry cooker nor a complete physics-content validator. A header-valid
file alone would not prove collision.

Therefore the next map-enabling investigation is a legitimate, compatible
collision-authoring route for a tiny original floor/wall fixture, including
shape content and capacities. A useful acceptance sequence is: verify the
authoring/cooking route, validate its output structurally, integrate an original
minimal world fixture, then obtain coordinated native/load/render/collision
evidence. Umbra/visibility, lighting, materials, entity behavior and other world
dependencies remain unresolved even if collision succeeds. This contribution
does not fabricate an HKX blob or label trigger geometry as solid geometry.

## Delivered bounded adapter

`tools-source/asset-bridge/world/trigger_bridge.py` converts explicit JSON
records of the H1 **client-trigger geometry/type subset** to named IW7 records.
It uses Python's standard library and requires no SDK or game files.

Input schema: `iw7.asset-bridge.h1-client-triggers/1`.
Output schema: `iw7.asset-bridge.iw7-client-trigger-records/1`.
The output contains `runtime_ready: false`, the source pin, and (for file
conversion) the SHA-256 of the raw input bytes. It is an inspectable intermediate
representation, not `.ents.data`, a serialized native ABI, pointers, MapEnts,
Havok data or a fastfile.

Supported fields are the named H1 `TriggerModel`, `TriggerHull`, `TriggerSlab`
and `MapTriggers` members at `h1/structs.hpp:3017-3047`, with corresponding IW7
members at `iw7/structs.hpp:3829-3881`. Models gain exactly the defaults used by
the existing converter: zero winding counts/indices and flags, null
`physicsAsset`, and `physicsShapeOverrideIdx = 65535`. Winding arrays are empty.
Hull bounds, contents, slab directions, distances and extents are preserved
subject to explicit float32 rounding. Directions are not normalized.

| H1 flag | H1 value | IW7 flag | IW7 value |
| --- | ---: | --- | ---: |
| VISIONSET | 1 | VISIONSET | 1 |
| AUDIO | 4 | AUDIO | 2 |
| BLEND_VISION | 8 | BLEND_VISION | 4 |
| BLEND_AUDIO | 16 | BLEND_AUDIO | 8 |
| NPC | 32 | AUDIO_NPC | 16 |

Zero and combinations of these five bits are supported. H1 LIGHTSET (2), CLUT
(64), CONTEXT (128), WATER (256), negative values and unknown bits are refused.
The enums and existing converter establish this mapping; the adapter does not
claim that audio/vision behavior works without the remaining client-trigger
settings, sound/vision assets and engine integration.

Validation is deliberately narrow and bounded:

- Exact fields are required at every supported object level. Unknown fields
  are refused, including winding/physics fields outside this input subset.
- Counts must match arrays; model-to-hull and hull-to-slab ranges must stay
  inside them. Signed 32-bit contents and unsigned 16-bit spans are checked.
- At most 256 models, 4,096 hulls and 16,384 slabs; one type per model.
- Three-component vectors, finite float32 values, nonnegative extents and
  nonzero directions; booleans, overflow and nonzero values rounded to zero
  are rejected. Geometry validity beyond these record constraints is unproved.
- Input is at most 1 MiB and 16 JSON nesting levels; duplicate keys,
  nonfinite constants and invalid UTF-8 are refused. Output is at most 4 MiB.
- File conversion requires absolute paths, existing directory ancestry,
  regular input and a new `.json` output. Traversal and link/reparse ancestry
  are refused; existing output is never overwritten. This is cooperative
  local tooling, not a hostile-filesystem race sandbox.
  On Windows only ordinary local drive-letter paths are supported. Both paths
  are checked lexically before filesystem I/O: alternate streams (`:` outside
  the drive), reserved device names, device/UNC namespaces, control/invalid
  filename characters and components ending in a dot or space are refused.

`fixtures/original-trigger.json` is handcrafted original data: one axis-aligned
box centered at `(12.5, -4, 8)`, half extents `(16, 8, 4)`, one model/hull and
three axis slabs. H1 type `5` becomes IW7 type `3`.
`fixtures/original-trigger.iw7.json` is its actual CLI output. No retail data or
proprietary dump is included.

From the project root in PowerShell, using an available Python 3 installation:

```powershell
$world = (Resolve-Path tools-source/asset-bridge/world).Path
python -B "$world/test_trigger_bridge.py"
# The destination must not already exist; its parent must exist.
python -B "$world/trigger_bridge.py" --input "$world/fixtures/original-trigger.json" --output "$world/original-trigger-review.json"
```

The example review output is local scratch; do not commit copies of it.

## Prepared native refusal patch

The existing `convert_trigger_type` silently drops H1-only and unknown type
bits. `zonetool-fab9358-trigger-types.patch` prepares a change to the exact
retained converter: include `<stdexcept>`, accept only the five supported bits,
and throw `std::runtime_error` for unsupported types before conversion.
In the inspected flow this happens while generating MapEnts, before its dump.
This makes the unsupported case explicit rather than claiming its behavior was
converted. It does not add missing trigger behavior or undo other assets that
may already have been dumped in a larger conversion operation.

The patch is **uncompiled and unapplied to the retained checkout**. Exception
handling, native build compatibility and caller diagnostics remain native
validation work. There is no claim that the Python test runs execute C++.

`verify_source.py` checks the exact source pin and eleven normalized source
hashes, extracts both enum tables and the existing five mapping calls, checks
the prepared patch against the intended source transformation, then applies
and reverse-applies it in a temporary copy of **only the converter file**. It
compares exact file bytes and checks that the shared source stayed unchanged.

```powershell
python -B "$world/verify_source.py" --source-repo "C:/Users/ezvalo/.codex/worktrees/modular-agent-platform/IW7-Paris-Server/tools/x64-zt-enemy"
```

The absolute path above names the retained source used for this evidence; it
does not install, copy or discover a different SDK. Supply another path only if
it is the same verified pin and content.

## Validation and corrections

On 2026-10-12, Python 3.12 completed 10 unit tests, including all 512
combinations of the nine known H1 bits (32 accepted combinations, 480 refused),
100 deterministic original box geometries, field/range/count/float failures,
empty/shared ranges, strict JSON parsing and create-only file conversion.
The fixture output was read back and compared to the adapter result.

An initial test exposed that Python's JSON parser accepted the deliberately
deep input: relying on a parser recursion error did not enforce a small depth
budget. A quote/escape-aware 16-level prescan was added; the rejection and a
string containing brackets/escaped quotes now pass. The patch was also made
self-contained by adding the explicit `<stdexcept>` include. Neither correction
required native execution.

The source verifier passed with these exact LF-normalized identities:

| Artifact | SHA-256 |
| --- | --- |
| Original converter | `4dd5b2e1b384d6d462e61bd30addee6f879db36175719bba13912292a2de029b` |
| Prepared patched converter | `d7473ca4959490687e3512de98918fda5a06fe82490a491b9e90e16fe856b793` |
| Prepared patch | `2ce5d1aad577b5decb6d5ac88d653422e046ab8fb0d857133cdf8190da4a86f0` |
| Original JSON input bytes | `6914615b4bd983f8fcf13a5abdd8f6644e9ecc089515f1b694047ebc0bf9ebc0` |

No heavy workload reservation was requested. No native build, asset extraction,
HKX cooking, FF assembly, game launch, engine test or owner gameplay acceptance
occurred. The first coordinated native step for this limited patch is compiling
the pinned converter and exercising supported/refused trigger flags after the
parent chat grants native GO. The broader original-map blocker remains world
collision authoring plus the unresolved world dependencies above.

### Independent-review correction: NTFS streams

Review of the first commit (`b9a1f083`) found that exclusive creation (`xb`)
still allowed `existing.bin:review.json`: NTFS can create a named stream on an
existing host file. The original create-only assertion was therefore too broad.
The path guard now rejects ADS and Windows filename/device aliases before any
filesystem I/O, for input and output alike. Twelve tests pass after correction,
including a temporary existing host file whose bytes remain unchanged and whose
named output stream remains absent. Mocked filesystem calls also establish
that all enumerated invalid spellings are rejected before access. No retail or
provider file was involved in the reproduction tests.

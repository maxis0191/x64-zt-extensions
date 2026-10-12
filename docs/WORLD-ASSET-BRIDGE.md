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

## Targeted Havok follow-up: format, available code and next original test

The follow-up remained read-only against retained ZoneTool and existing engine
references. No upstream refresh, download, extraction, heavy analysis, native
build or provider edit occurred. The separate
`world/havok-audit-2026-10-12.json` records source hashes and sanitized observations.
`world/havok_probe.py` reproduces the two bounded observations without loading
native code or writing an asset.

### What the retained data establishes

The previously captured `tools/references/unpacked-rdata.bin` is 3,194,880 bytes,
SHA-256 `28b66189c1f35442d3e32ea5077e785e7cb8fbf45ed420094dc6b2795afd04e5`.
It is a **previously patched runtime snapshot**, not a newly captured or pristine
retail image. Its strings include `hk_2014.2.5-r1`, `hknpPhysicsSystemData`,
`hknpConvexPolytopeShape`, `hknpCompressedMeshShapeData`, `hkGeometry`, and the
IW7-specific `HavokPhysicsAsset` and `HavokPhysicsShapeList` names. These support
an **hknp/Physics 2014** route; an old `hkpBoxShape` tutorial or a generic HKX
extension is not sufficient compatibility evidence. Some `hkp` constraint
classes also coexist in the inspected asset, so this is not an assertion that
every runtime class uses the `hknp` prefix.

A retained, read-only `ragdoll_alien_queen.hkx` from the 2026-10-03 Rhino build
supplies concrete serialized-envelope evidence: 47,152 bytes, SHA-256
`4827c1d86cad3cf7065fd5b24bf1fd09dbec88ea7ff495b008407aaaf0fbb112`.
This is a physics-model reference, not original map data and not a new runtime
acceptance test.

| Item | Observed value |
| --- | --- |
| Magic words | `0x57E0E057`, `0x10C0C010` |
| Packfile format version | 11 |
| Contents version | `hk_2014.2.5-r1` |
| Platform tuple | pointer size 8, little-endian 1, reuse-base-padding 0, empty-base-optimization 1 |
| Header / section-record sizes | 64 / 64 bytes in this observed v11 layout |
| Sections | `__classnames__` at byte 256; empty `__types__` at 640; `__data__` at 640 |
| Data section | 42,320 bytes before local fixups; global fixups at relative 43,104; virtual fixups at 45,072; section ends at 46,512 |
| Root | `HavokPhysicsAsset`, section 2, relative offset 0 |
| Relevant contained names | `hknpPhysicsSystemData`, `hknpCapsuleShape`, `hknpConvexPolytopeShape`, connectivity and mass-properties classes |

The 64-byte header field layout comes from `iw7/common/havok.cpp:26-43`.
The section-record interpretation is corroborated by this retained v11 file;
it is not asserted for other packfile versions. There are no serialized type
definitions in this sample's empty `__types__` section. Class names alone do not
provide class layouts, signatures, finishing callbacks or a replacement runtime
registry.

The runtime also contains `HavokPhysicsShapeList` and nearby names `shapes`,
`shapeIndices`, `shapeNames`, `vertCounts`, `triCounts`, `minMaxes`,
`numWorldGeoShapes`, `shapeTagData`, `shapeContents`, and `convexCounts`.
Nearby shape-tag names include `collisionFilterInfo`, `materialCRC`,
`materialId`, and `userData`. They are a concrete lead for the world container,
**not proof of its member offsets, types or use by the world loader**.
No `.colmap.hkx` was found in the inspected retained runtime/reference roots.
The world loader's required root, class graph and tag/scale rules therefore
remain unverified; the ragdoll root must not be substituted for them.

### Available locally versus still missing

| Component | Current evidence | Classification |
| --- | --- | --- |
| Copy an existing compatible HKX into a zone | `iw7/assets/clipmap.cpp:78-79,243-247` and `physics_asset.cpp:35-38,114-118` read existing bytes and write them aligned to 16 bytes. PhysicsAsset metadata separately stores rigid-body/constraint/event counts (`iw7/structs.hpp:655-668`). | Implemented packaging; not collision generation. |
| H1 brush/patch conversion | The H1 converter emits zero world/entity Havok bytes. | Bridge code is not implemented; merely filling the data pointer cannot solve the format/schema dependency. |
| Havok headers, libraries or standalone cooker | ZoneTool's `.gitmodules`, `deps` build descriptions and bound IW7 symbol/function headers contain no Havok SDK dependency, convex builder or serializer binding. Targeted filename searches found no `hk*.lib`, `hknp*.h` or `hkSerializeUtil.h` in the inspected project tool/runtime roots. | No ready authoring toolchain found **in those roots**. This is not a whole-machine or licensing inventory. A compatible external SDK must not be presumed installed. |
| Runtime geometry and serialization code | The pinned rdata contains `hkGeometry`, convex/mesh classes, `Util\\hkSerializeUtil.cpp`, `Packfile\\hkPackfileWriter.cpp`, and a diagnostic mentioning `hkSerializeUtil::savePackfile`. | A plausible local in-process route worth investigating. String presence does not prove callable addresses, signatures, allocator ownership, enabled save path or safe teardown. No usable wrapper was found. |
| Original hand-written HKX encoder | No local encoder or complete class graph schema was identified. | Substantial format/registry/collision code remains to be established. Writing a v11 header and eight vertices is insufficient. |
| World linkage | Capacities, shape/filter/material/content tags, world root, submodels and unit conversion are not established by this sample. | Engine-specific integration still unimplemented/unverified even with a generic shape cooker. |

The filename search covered the retained modular-agent-platform runtime,
rhino-animclass runtime and primary project tools. It did not scan the entire
machine, fetch a package, infer license rights or recover removed worktrees.
The exact source files checked are hash-bound in the audit receipt.

There is also a native parser boundary to fix before feeding new or malformed
files to ZoneTool: `parse_havok_data` reads arbitrary file bytes and casts their
start to `hkxHeaderData*` without a 64-byte minimum (`havok.cpp:116-121`);
`validate_header` uses `strcmp` on `contentsVersion[16]` without first proving
termination (`:85-87`). It does not validate the file-format version, sections,
fixups or object graph. This source finding is not a native crash reproduction.
The new inspector bounds its own reads and strings; it does **not** patch that
native reader or make untrusted HKX safe for it.

### Smallest useful original-collision test

The next investigation should establish bindings for the existing runtime's
convex builder, serializer/class registry and world loader, including allocator,
scale and tag ownership. If those functions cannot be bound safely from the
retained reference, the alternative is a legitimately available compatible
Havok 2014.2.5 authoring SDK plus IW7's custom container definitions. Neither
route is ready to execute locally today.

Once that prerequisite is met and the parent grants native GO, the smallest
meaningful test is **one original static convex box in a private temporary
physics world**. It avoids needing a general triangle-mesh/BVH cooker as the
first milestone. `fixtures/original-collision-box-plan.json` supplies eight
original corners, bounds `(-64,-64,-8)` to `(64,64,0)`, and three exact geometric
ray expectations: top hit, outside miss, side hit. It is a test specification,
not an input format accepted by ZoneTool and not a cooked asset.

The native fixture must explicitly set/verify scale and convex margin, build
the actual `hknp` shape, attach supported filter/material/content tags and use
the **verified** world container. Serialize using the matched registry, reload
the created bytes, repeat the three queries and check object cleanup. Preserve
the output hash, shape/body counts, hit fractions/normals, rejection diagnostics
and teardown result. Do not guess a function address, class signature or memory
layout from the strings above. Header acceptance or successful zone registration
alone cannot pass this test.

Only after this isolated test should an original `.colmap`/world fixture be
integrated under resource/instance guards. Rendering, visibility/Umbra, lighting,
MapEnts, pathing and owner gameplay remain separate work. No custom-map readiness
is implied by a single original physics box.

### Reproduce the bounded source checks

```powershell
$world = (Resolve-Path tools-source/asset-bridge/world).Path
python -B "$world/test_havok_probe.py"
python -B "$world/havok_probe.py" --rdata "<retained-reference-root>/unpacked-rdata.bin"
python -B "$world/havok_probe.py" --hkx "<retained-physicsasset-root>/ragdoll_alien_queen.hkx"
```

Five new tests pass using only original synthetic envelopes, covering short
headers/tables, file budgets, version/layout mismatches, bad root indices and
ranges, overlapping/nonmonotonic sections, missing string termination and an
unpinned runtime snapshot. The synthetic bytes are deliberately nonfunctional
and are never written as an HKX file. The inspector accepts only the observed
three-section v11 envelope and reports `shape_graph_validated: false`,
`fixups_validated: false`, `runtime_ready: false` even for structurally accepted
input. Rechecking retained metadata confirms the values above; no native test
or collision generation was performed.

### World-consumer chain resolved in the retained snapshot

A subsequent targeted pass advanced the chain from names to actual field
consumption. It followed the source-known DB registration entry and its direct
calls/table entry, reading selected function windows only. It did not scan the
whole executable or invoke any address. The reproducible check is
`world/inspect_world_consumer.py`, using the already installed Capstone 5.0.7.
It reads **2,690 selected text bytes** plus the pinned rdata/pdata metadata,
checks nine exact SHA-256 signatures, decodes every selected byte, and verifies
the call targets, CLIPMAP dispatch entry and two world-buffer field accesses.
The result is stored under `world_consumer` in the existing audit receipt.

All addresses here are preferred-image addresses in the historical patched
snapshot. They are **not approved live bindings**. In particular, the entry at
`0x140A76520` already jumps outside the captured text; the retained body after
that patch remains inspectable. Source `iw7/zonetool.cpp:590-603,2804` supplies
the DB-add hook anchor and its forward-to-original behavior. This is source and
snapshot evidence, not a claim that an unobserved live call executed this chain.

| Step | Verified relation |
| --- | --- |
| DB-add retained body | `0x140A76557` calls `0x140A782B0`. |
| Asset linking | `0x140A783CB` calls `0x1403B7430`, passing the asset pointer and type. |
| Type dispatch | `0x1403B7430` reads the function table at `0x1414672D0`; index 22 (`ASSET_TYPE_CLIPMAP`, pinned `iw7/structs.hpp:147`) contains `0x1403B72F0`. |
| CLIPMAP wrapper/thunk | `0x1403B72F4` calls `0x14054BEB0`, whose five-byte tail jump targets `0x140571D50`. |
| **World consumer** | `0x140571D50` reads the size at asset `+0xF8`; when nonzero, it reads the pointer at `+0x100` and calls `0x140572C30` at `0x140571D79`. These are the two `havokWorldShapeData` fields in the pinned source layout. |
| World shape/tag helper | `0x140572C30` zeroes R8/R9 and calls `0x140F2DA80`, then processes the returned root's array at `+0x68`, count at `+0x70`, stride 24. |
| Packfile load in place | `0x140F2DA80` calls header checker `0x140F2E120`, tests/sets bit 0 at packfile `+0x38`, processes section relocations/finishing callbacks, and returns a pointer into the supplied buffer. |

This gives a concrete answer for **where the world bytes are consumed**. It
does not identify a creation or save function. The generic packfile loader is a
load-in-place path, not a cooker or serializer. Its use of a thread allocator,
global registry and virtual callbacks means that calling it with a hand-written
prototype outside the initialized engine would be unsupported.

The returned world root is stored at global `0x144BDF458`. The consumer accesses
an array of name pointers at root `+0x20`, count at `+0x28`, masks each pointer's
low bit and lowercases nonempty names **in place**. The tag helper compares the
32-bit value at record `+4` against a runtime table, then writes a 16-bit value
to record `+8`. This is consistent with the observed `materialCRC`/`materialId`
names, but the semantic field naming remains an inference until root metadata
is observed. The global table and registry values are outside the retained
rdata/pdata slices. They were not read from a running process.

Consequences for a future original collision are concrete: its backing storage
and name strings must permit the normal loader's mutations, it needs valid
relocations/finishing metadata, and its tags must match initialized runtime
material/filter data. Reusing an already fixed-up live buffer as a portable HKX
is unsafe: this loader rejects the already-set loaded flag. The root accesses
strongly support the `HavokPhysicsShapeList` lead, but **the actual world root
class name is still unobserved**. No Rhino `HavokPhysicsAsset` was substituted.

The initial read also exposed a tooling detail: the CLIPMAP thunk has no pdata
owner, while the generic loader spans five adjacent unwind records. The
reproducer includes the exact five-byte thunk and the full observed loader
range through its return; it does not confuse one unwind-record boundary with
a complete function. No instruction bytes or disassembly are committed.

### Small next observation before attempting original shape generation

The next useful native observation is now narrowly specified. After coordinated
native GO, extend the existing DB-add observer for **one allowlisted CLIPMAP
asset** during one normal offline registration. Place it before the existing
hook forwards to the original routine, so it sees pre-fixup bytes. No full map
dump, repeated manual loader call or geometry extraction is needed.

1. Bind the binary identity and reviewed hook signature; verify the asset type
   is 22 and the name matches the single requested asset. Check pointer/size
   ranges before reading. Observe only; forward the normal call exactly once.
2. Before forwarding, read the 64-byte packfile header, bounded section table
   and at most 128 bytes of the root class name. Require the known platform,
   version, supported section layout, in-bounds offsets and unloaded flag.
   Refuse ambiguous/already-fixed-up data. Limit raw inspection to 2 KiB and
   emitted metadata to 4 KiB for that one asset; emit no geometry or raw bytes.
3. Record the root class string, section count/offsets, declared blob size and
   metadata digest. After normal registration, record the loaded-flag change
   and whether the returned/stored root points at the header-derived contents
   offset, plus only the two observed bounded array counts. The matching root
   relation must be observed, not assumed from a string in rdata.
4. Stop after this one observation. If the root is confirmed as
   `HavokPhysicsShapeList`, the next source target is its finish/constructor
   registration and an actual convex-builder/save call chain. If it differs,
   revise the original-box plan before building anything.

Creation and serialization remain **unbound**, despite the earlier save-related
diagnostic strings. This observation advances the missing world-container
contract; it is not collision generation or gameplay evidence. No observer was
installed or run in this source-only pass.

```powershell
python -B "$world/inspect_world_consumer.py" --reference-root "<absolute-path-to-retained-references>"
```

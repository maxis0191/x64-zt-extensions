# World asset bridge: source preparation

## Future resource regression contract - 2026-10-14

The full product source run at `965188d` failed `test_observer_stages` because
it still required `Commit high water` at 86% after the owner removed percentage
stops. The World runtime profile already forwards the shared H1 `TelemetryOnly`
observer; no runtime policy change is needed here. The corrected source test
requires stage success and fresh observations at 85%, 86%, 99% and 100%, without
pressure allocations. The real scheduler/registration functions are exercised
in a fixture-local registry for competing leases, wrong/unreadable identities,
retention of a live child and recovery only after proven absence. Original-stage
identity failure, unconfirmed closure, deadlines, output limits and native exit
failure remain refusal cases. No native provider, compiler, process child or
account-wide lease is started by these tests.

The failed producer logs, frozen observer plans/capsules and earlier evidence
retain their original bytes. Future source packages adopt the corrected test;
the change does not requalify a historical plan or establish gameplay evidence.

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

## Prepared single-CLIPMAP observer: source candidate only

`world/world_clipmap_observer.hpp` now implements the bounded observation;
`world/zonetool-fab9358-world-observer.patch` includes that new header and the
private ZoneTool integration against the exact retained pin. The shared checkout
was not edited. The patch touches `iw7/zonetool.cpp` and adds
`iw7/common/world_clipmap_observer.hpp` only. No native compilation or execution
has occurred, and the **real world root class remains unknown**.

The source hook remains `db_add_xasset_stub`, installed at `0x140A76520` by the
existing code. Its existing `dump_asset` call stays in place. Immediately after
it, the new `forward` wrapper surrounds the original detour invocation:

1. `before` is `noexcept` and claims the first type-22 callback only after explicit
   arming. Its inspection can succeed or refuse; both paths return to `forward`.
2. `forward` has one unconditional `invoke()` expression. The integration has
   one `db_add_xasset_hook.invoke<XAssetHeader>` call site inside that callback.
3. On normal return, `after` is `noexcept` and receives the returned asset pointer.
   An original C++ exception is recorded and rethrown without retry. Observer
   refusals never skip or repeat the original call. Existing errors outside the
   observer, including the earlier legacy `dump_asset`, are not swallowed.

The observer uses `ReadProcessMemory` on its own process, checked address
addition and fixed storage; it never writes the observed asset/blob. It preserves
`GetLastError` and `errno` around observer work. SHA-256 uses Windows CNG and
`bcrypt.lib` from the already installed Windows SDK; no additional SDK/download
is required. Three exact code signatures and the CLIPMAP dispatch-table entry
must match the audited preferred-address profile before arming. This partial
code guard supplements, and does not replace, the coordinator's binary/build
identity verification. A relocated or changed profile is refused, not guessed.

There is one attempt per process, with no rearm or search over further CLIPMAPs.
The first selected callback must have the exact requested name. A mismatch consumes
the observation and records a refusal while normal registration proceeds. Other
asset types incur no asset reads. An atomic claim excludes nested/concurrent
callbacks from taking a second observation.

### Read and output boundaries

- All guarded inspection reads, including signature guards, share a **2,048-byte
  requested-byte budget**. Failed or partial reads consume their requested
  amount. The present longest accepted path requests at most 1,160 bytes.
- The guard reads 580 code bytes plus an eight-byte dispatch entry. Asset/name
  pointers and the declared payload size are read separately. A declared blob
  above 512 MiB is refused; it is never copied or hashed in full.
- The 64-byte HKX header is checked **before** reading the 192-byte section
  table. Only the observed version/platform/three-section layout is supported.
  All section/root bounds are checked against the declared blob extent. At most
  128 bytes are read for the root class, with bounded NUL termination and a
  restricted ASCII identifier alphabet.
- After normal registration, the returned asset must retain the same blob and
  size. The loaded flag and global root must match the precomputed contents
  pointer. Two scalar array counts are read only if the captured class is exactly
  `HavokPhysicsShapeList`, with an in-data extent check and count bounds. Unknown
  root names are still reported, without assuming their array layout.
- Exactly one `WORLD_CLIPMAP_OBSERVATION` JSON record is attempted, bounded to
  **4,096 bytes including prefix/newline**. A small refusal record replaces an
  oversized result. Short stdout writes are not retried. The digest covers only
  the pre-fixup header, section table and class name; it is not a geometry hash.
  Ordinary pre-existing ZoneTool console messages are outside this observer
  metadata limit.
- No geometry arrays, shape tags, name arrays, Havok object graph or full map
  payload are read. A refused observation does not make malformed data safe for
  the engine: the engine's normal call is deliberately preserved. Malformed
  inputs belong only in the synthetic harness, not in a native map load.

The prepared CLI mode is deliberately exclusive, requiring exactly:

```text
<candidate-zonetool> -headless -world-clipmap-observe <allowlisted-Zombies-map> <exact-clipmap-asset-name>
```

The requested map is checked by the existing five-map allowlist. Dump, CSV dump
and verify modes are disabled; existing synchronous source-zone loading is used.
The process waits for the database, checks the observation outcome and exits.
No new asset-capture/file-write command is added. The exact CLIPMAP name must be
provided from a trusted inventory; an inferred filename is not an accepted match.
This command is a future coordinated test recipe, **not executed evidence**.

### Prepared harness and remaining validation

`world/test_world_clipmap_observer.cpp` exercises the same `forward`, `before`
and `after` code with original synthetic buffers and a tiny newly reserved mapping
owned by its standalone process. It refuses an occupied fixture address. It is
prepared to check successful metadata flow, thread-error restoration, duplicate
and nested callbacks, eleven pre-inspection refusals, three post-identity/count
refusals, missing post-fixup state, propagation of an original exception and an
unrelated asset. A first-name mismatch consumes the attempt even if a later
callback matches. Every refusal still checks one original call and the relevant
result/exception. No retail file is an input.
Fixture seeding bypasses engine signature checks explicitly and leaves
`signature_checked: false`; its records cannot establish an engine observation.
At this initial source checkpoint the harness had not been compiled or run;
the two later native refusals are recorded below. No fixture pass is established.

The harness now captures the real emitter's bytes through a process-owned pipe,
without changing the observer header. Each normal case checks one complete line
and no second emission, then replays the exact bytes for an independent JSON
reader. It directly tests an exact 2,048-byte read, refusal of the next byte and
an oversized request, address overflow, and charging a failed requested read.
Canaries surround a 4,096-byte formatting buffer. Maximum-width fields and a
deliberately impossible oversized diagnostic test normal output and the fallback.
The latter is fixture-only; production refusal tokens remain constant and short.
A broken emitter that blocks is stopped by the outer job deadline.

`world/check_observer_harness.py` reads at most 128 KiB, requires the 24 expected
records and final measured summary, rejects duplicate JSON keys, checks the
actual per-record 4 KiB and requested-read 2 KiB bounds, and preserves the
synthetic evidence labels. Its five Python tests passed on original JSON data,
including 4,096/4,097-byte boundary cases. **That validates the reader only**;
the C++ cases and real transcript remain pending. The compile/run plan and exact
provider bindings are in `world/observer-harness-plan.json` (v2).

`world/verify_observer_patch.py` verifies the exact pin/source/header hashes and
applies/reverses the prepared patch against two temporary source files. This
passed, including exact restored bytes and a single syntactic original-call
site. Its receipt is `observer_source_candidate` in the existing Havok audit.
This source check is not a C++ compiler, a forward-once runtime test, or a memory
safety proof.

```powershell
python -B "$world/verify_observer_patch.py" --source-repo "<absolute-path-to-pinned-zonetool-source>"
# Only after the admitted native run has produced this transcript:
python -B "$world/check_observer_harness.py" "<owned-run-root>/harness.stdout.log"
```

The proposed standalone group uses **one original Windows job for its root,
compiler/linker and subsequent fixture**, and one 4 GiB RAM / 6 GiB commit lease.
It reuses `model/BuildJob.cs`, the `surfaces/MaterialV2.Core.ps1` start/wait/stop
functions, `MaterialV2.JobMembers.cs`, the reviewed compiler-witness/telemetry
policy, and the existing bounded log drain. No replacement job/process manager
is introduced here. `world/Run-ObserverHarness.ps1` now provides the executable
adapter: its default Plan mode verifies installed tools and source/provider pins
without creating output, taking a resource snapshot, loading native helper types,
reserving resources or starting a child. `-Run` is the future coordinated native
entry point; source delivery does not authorize using it.
World-owned PowerShell sources explicitly use LF through the local
`.gitattributes`, preserving their exact hash pins after checkout. All eleven world
source pins were also checked against Git's checkout-filtered committed bytes.

Compile one TU using the existing x64 MSVC/Windows SDK, `/std:c++20 /EHsc /MD /O1
/W4 /D_CRT_SECURE_NO_WARNINGS`, explicit include/lib paths, `/INCREMENTAL:NO`,
and `bcrypt.lib`; no `/MP`, dependency rebuild or SDK copy. Pin compiler, Python,
provider and input hashes under read guards. Keep `CL` and `_CL_` out of the
child's compiler environment. The candidate EXE/object and all logs belong to a
fresh owned runtime directory. Use the fixture's actual compiled EXE hash for
its single launch; its input is entirely compiled-in original synthetic data.

The Python driver launches the compiler once, requires its witnessed exit zero,
then waits for an atomic, token-bound fixture permit from the PowerShell owner.
The owner keeps the compiled EXE open against writes/deletion and binds its hash
in that permit. Before permitting the fixture, the same original job may contain
only the root, at most one exact compiler telemetry child, and at most one exact
System32 console host. The World console policy pins the reviewed Windows image
SHA256 and Microsoft Windows signer subject/thumbprint. Plan only reads/hashes
the image; Run additionally requires a valid Authenticode result under its read
guard before creating the original job. A Windows image/signing update refuses
the pinned policy until reviewed.

The console host must be witnessed while the root is alive, as its direct child
in the same original job, with creation between the root's creation and capture.
Its PID, image and creation generation cannot change. The complete gate rejects
duplicate identities, a second console/telemetry child, unreadable or foreign
members, and unknown paths; it never filters out an arbitrary `conhost.exe`.
After the original root exits successfully, a residual console host must match
that previous witness. World checks the complete residual set and uses the
existing original-job stop helper; telemetry-only closure delegates unchanged
to the existing compiler policy. The reused supervisor still must observe fresh
root0 / Active0 before acceptance. No PID/name-based cleanup, replacement native
owner, automatic retry or relaunch is introduced.
The adapter enforces 90 s for compilation including the permit gate, 10 s from
fixture permission and 120 s from lease acquisition for the group, within the existing supervisor's
240 s supported envelope (245 s including its grace). The poll callback checks
the stricter deadlines before and after its work and after native helper imports;
the driver independently checks
its monotonic deadlines during polling, after exit and after log draining. Keep the existing
2 s drain and 15 s cleanup bounds. A failed/ambiguous job closure retains the
lease and diagnostics. The full group, receipts included, is capped at 64 MiB;
each compiler/fixture log stream is capped at 2 MiB and the accepted fixture
transcript at 128 KiB. These are proposed limits, not measured resource usage.

The driver reuses `beacon_tool_phase.py`'s pinned bounded stream drain. A local
`guarded_drain` wrapper catches `BaseException` and signals failure before a
worker returns; it never formats the thrown exception. This covers non-OS stream
errors and `SystemExit`, which the provider's `OSError` handler does not catch.
The driver has no
job owner, lease API or kill operation. Errors exit the root so the PowerShell
owner stops only its original job. It requires the independent transcript checker
before successful exit; the owner then requires fresh root0/Active0, the exact
fixture receipt and transcript digest. Final byte accounting includes `run.json`
itself. The owner publishes that immutable **before-release snapshot**, checks
its exact bytes/hash and total output size, and holds it against writes/deletion
before calling the scheduler releaser. Publication, accounting or verification
failure prevents any release attempt. The file says `ReceiptStage:
BeforeLeaseRelease`, `LeaseReleased: false`, and `LeaseReleaseState: NotAttempted`;
it does not predict scheduler success. After the call returns, only the returned
result reports `LeaseReleased: true` / `Confirmed`. No later file write is needed
to qualify the frozen evidence. A throwing release is `Unconfirmed`, retaining
the token for registry reconciliation without assuming the lease still exists.
There is no retry of a confirmed or ambiguous release. Failed factory/closure,
changed source or failed finalization keeps guarded objects and the token;
no new attempt is started.

Source validation for this adapter: nine Python tests use fake process objects
and original data; fifty-six PowerShell checks exercise budgets, pins, receipt/member
refusals, the reused supervisor with fake clocks, deadline boundaries and failed
cleanup. The driver tests include twelve stdout/stderr read/write/flush faults
using both ordinary exceptions and `SystemExit` with deliberately broken string
formatting. Forty-five further original-text/mock-scheduler checks cover receipt
publication, pre/post-write accounting, same-size content corruption, the held
receipt guard, release order, ambiguous release and faithful closure/lease flags.
An additional real installed-tool Plan check verified 26 bound inputs,
zero prohibited calls, no output directory and no native helper types. An early
pure test found missing parentheses in a mixed PowerShell `-and`/`-or` type gate;
the grouping was corrected before delivery. Review of `d2d97ca` then identified
two gaps missed by the earlier tests: unguarded non-OS drain exceptions and
release before final receipt publication/accounting. Both corrections and their
fault-injection tests are now source-only; no earlier native pass is implied.
These adapter checks remain **source, mock or inert Plan evidence**. The first
separately authorized native attempt is recorded below; its compilation success
does not qualify the fixture or this subsequent console-policy correction.

### First native attempt and console-policy correction, 2026-10-12

The immutable [failure checkpoint](../tools-source/asset-bridge/world/native-checkpoint-2026-10-12.json)
records source `ae0d85f6`, the exact Plan/receipt/postflight hashes, and the one
authorized invocation. Compilation exited zero, but the pre-fixture gate refused
the observed Python / System32 console-host / compiler-telemetry membership.
No fixture permit was issued: **0/24 observations**, no engine evidence. The
original job was stopped and confirmed root-exited / Active0; external postflight
found no retained lease or known child and confirmed Main unchanged. The frozen
run receipt is explicitly before release and must not be read as the final
scheduler state. Raw local diagnostics remain preserved outside tracked source.

Both the original owner and driver already requested `CREATE_NO_WINDOW`; this
flag was not missing. The source correction described above uses the existing
member capture, supervisor and stop helpers without rebuilding or altering their
native owner. Seventy-six additional pure/mock checks replay the measured
three-member shape with sanitized identifiers, reject spoofed/duplicate/replaced
members and signatures, and cover console-only, telemetry-only and mixed
post-root closure, unknown survivors and failed closure. Together with the
existing 56 adapter and 45 finalization checks, these are **177 pure/mock checks**.
The installed-tool Plan remains inert, now including the console image pin;
signature validation is forbidden in its Plan test. That correction was then
independently reviewed and given one native retry, recorded next. Neither failed
checkpoint is overwritten by later source work.

### Second native refusal and child console roles, 2026-10-12

The [retry checkpoint](../tools-source/asset-bridge/world/native-checkpoint-2026-10-12-retry.json)
retains the reviewed source `78a34b5`, Plan `7bf84ebf`, receipt/postflight hashes,
and both console generations and parent roles. The complete native observation
at `12:02:46.8074986Z` was:

```text
retained PowerShell owner
  Python root                 created 12:02:46.5339115Z
    System32 conhost          created 12:02:46.5546554Z
    cl.exe                    created 12:02:46.6553769Z
      System32 conhost        created 12:02:46.6691788Z
```

All four members were verified in the original job. This was during the live
compilation, before any successful compiler receipt, fixture permit or fixture
launch. The new per-poll console witness counted both console roles against its
single-root-console limit and refused. Compilation was interrupted; this retry
produced **0/24 observations**. The original job closed with root-exited / Active0
at `12:02:46.9650788Z`. External postflight confirmed no retained lease or known
child, no quarantine in the retained PowerShell host, and Main unchanged. Only
then was the original host exited. Its exit status does not qualify the harness.

`BuildJob.Prepare` requests `CREATE_NO_WINDOW` for Python; the World driver's
`run_phase` also requested it separately for `cl.exe` and would do so for the
fixture. Microsoft describes [the console-host startup path](https://github.com/microsoft/terminal/blob/main/doc/specs/%23492%20-%20Default%20Terminal/spec.md):
the inbox console still serves applications that need no window. Thus this flag
does not imply the absence of a console-host process. The observed generations
map to the separate Python and compiler launches, not two generations of the
same root console. The fixture branch had not run, so a fixture console remains
a source-derived possibility, not an observed process.

The minimal source correction changes only the World driver's two pipe-only
child launches to `DETACHED_PROCESS` (`0x8`), with stdin `DEVNULL` and stdout/stderr
still redirected to the existing bounded drains. This [console detachment flag](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags)
is distinct from job breakaway; the original job, BelowNormal inheritance,
hash-bound launches and cleanup remain unchanged. No new native owner is built,
and the policy does not raise its console count or allow compiler/fixture console
hosts. Unknown or extra members remain refused. The fixture uses CRT output and
an internal capture pipe, with no console-allocation/input API dependency in its
source. Actual compiler and fixture behavior under these flags still requires
native validation; it is not inferred from fake-process tests.

One additional driver test exercises both compile and fixture launch contracts,
including redirected handles and refusal of console/new-console/job-breakaway
flag combinations. The driver/reader total is now **15 Python tests**, alongside
the unchanged **177 PowerShell pure/mock checks** and inert installed-tool Plan
test. That source-only correction subsequently received independent review and
one separately authorized third attempt, recorded next.

### Third native refusal: the nested linker console, 2026-10-12

The [third checkpoint](../tools-source/asset-bridge/world/native-checkpoint-2026-10-12-detached.json)
retains source `757e3a1`, exact Plan `b6f79c9f`, driver and evidence hashes.
The first seven polls reached an actual compile/link graph at
`12:18:51.5814777Z`: Python with its console host; direct child `cl.exe`;
compiler children `vctip.exe` and `link.exe`; and a second console host whose
native parent was the linker. All six members were in the original job with
complete parent/image/creation observations. Thus changing the direct compiler
launch did not eliminate the nested linker's console. The per-poll single-console
witness again refused before a compiler success receipt or fixture permit.

An object file was emitted, but compilation/link success is **not established**.
There is no fixture stdout or stderr and **0/24 observations**. Both compiler
streams were empty at interruption. Outer stdout contains only the retained
PowerShell host's banner/prompts; stderr reports the console-generation refusal.
No fourth invocation or speculative source correction followed this result.

Original-job cleanup confirmed root exit `122` / Active0 at
`12:18:51.7199067Z`. Postflight verified unchanged source pins and Main, no known
children, no lease and no quarantine while the original host remained alive.
The host was then exited and the released slot confirmed at
`12:21:20.4989967Z`. No Main/config/bank restoration was required. The immutable
`BeforeLeaseRelease` receipt remains distinct from the later external release
proof; neither host exit nor cleanup turns any of the three attempts into a pass.

The next source review must account for phase boundaries and the observed nested
compiler/linker roles before any new exact Plan and separate GO. Merely increasing
the global console count would not establish the expected role identities.

### Proposed reuse of qualified T7/H1 stages, 2026-10-12

This is a **source/diagnostic proposal only**, not an executable Plan or a fourth
Run. The third failure and release checkpoint above remain authoritative. No
native provider, driver, launch flag, member count or budget was changed for this
proposal, and no heavy reservation is retained for it.

The complete observed third-attempt graph was:

```text
retained PowerShell host
  Python original job root
    conhost (Python parent)
    cl.exe (direct DETACHED_PROCESS request)
      vctip.exe (compiler parent)
      link.exe (implicit child created by cl.exe)
        conhost (linker parent)
```

The direct launch request does not describe how `cl.exe` creates its own linker.
The live graph was refused before either tool had completed. A larger global
console count would still mix live build descendants with post-exit residuals;
it would also leave compiler-owned and linker-owned VCTIP generations in one
continuing Python job. The failure does not establish a toolchain build failure.

The smallest reuse candidate is a World-specific profile around the already
qualified `Invoke-H1OwnedStage` lifecycle and existing
`IW7.AnimationProbe.NativeJob` DLL, with explicit `/c` and a direct link stage.
Reuse the function-scoped linker identity adaptation in
`T7Build.Profile.ps1::Invoke-T7OwnedStage`; do not broaden the shared compiler
policy globally or import the complete T7 runner and its larger budgets.

| Proposed stage | Original process and required boundary |
| --- | --- |
| Compile | Pinned `cl.exe`, `/c`, one World TU, no `/MP`. Require root exit0 and original-job Active0 before using its object/dependency report. |
| Link | Pinned `link.exe`, only the frozen object and required pinned libraries. Require root exit0 and original-job Active0 before accepting the fixture EXE. |
| Fixture | Exact newly hashed EXE, compiled-in synthetic data, no child launch requested. Require exit0 and empty original job; retain both streams. |
| Check | Pinned Python plus the existing `check_observer_harness.py`, reading the frozen fixture transcript. Require exit0, empty original job and the existing exact 24-record contract. |

This explicitly changes ownership from one continuing Python job to four
**sequential original jobs under one lease**, with at most one active job. The
checker is included rather than becoming an unowned process. Keep each original
owner and its identity until closure; update scheduler registration only after
the previous stage is closed. This lifecycle change needs a new reviewed Plan.

For each tool independently, H1 first requires its original root to have exited
successfully. If descendants remain, the only qualified successful cleanup is
one exact pinned VCTIP, parented to that stage's original tool PID, with matching
creation/image/job identity in two captures. Reverify inputs and freeze output
artifacts before stopping that original job, then require fresh root0/Active0
and an empty member capture. Unknown, extra or ambiguous residuals fail the
stage. No global live-console counter or termination by process name is needed;
a console that remains after tool exit is not silently exempted. A failed stage
may recover its owned job, but recovery never qualifies the stage as passed.

Read-only evidence was checked against retained T7 receipts and current provider
bytes. `zt-t7-a` is **Failed overall**, but its three `/c` production TU stages
each record exit0, tree closure and verified compiler-owned VCTIP cleanup; its
helper and 51-case probe also closed successfully. The separate `zt-t7-b` D2
receipt is **Passed** for direct Link, with linker-owned VCTIP observed twice,
root0/Active0, input revalidation and lease release. That candidate was not
executed. None of these results validates the World fixture's 24 cases.

| Retained evidence | SHA-256 |
| --- | --- |
| T7 C receipt (`zt-t7-a/receipt.json`, partial stage evidence only) | `af6beecf7a8892e16266a7641d2799f665f86fa8ad7c40c61561b782534f7897` |
| T7 D2 receipt (`zt-t7-b/receipt.json`) | `c609bc56523654d8bca4b855024a463393185aab8e19ed4eae94c1ff8f6a09c2` |
| D2 installed-tool Plan | `daa7097f872b83a5762b2cb56bf6dd5a235ed2beee8e0ff077276c61622d53fa` |
| Existing qualified `Probe-NativeJob.dll` | `5f613ebb83019dbf4bfa4f6a93c5329098343729b70acc2cfa70aa8b64f195f8` |

The five D2-bound source providers (T7 profile, H1 core/compiler/member observer,
and MaterialV2 compiler policy) and the DLL still matched their D2 bindings at
inspection. A future Plan must bind and read-guard exact bytes again; a provider
name or another chat's successful result alone is insufficient.

Two compatibility differences prevent a blind replacement:

- `Complete-H1Stage` releases its lease before the T7 receipt is published.
  Reuse stage ownership/closure, but retain World's immutable
  `BeforeLeaseRelease` receipt, output accounting, read guard and single release
  attempt. Preserve the retained-host quarantine path on ambiguous closure,
  publication or release. Never overwrite a live owner when advancing stages.
- `NativeJob.OpenLog` gives tools direct create-only file handles; H1 polls total
  output every 100 ms. This does **not** implement World's existing strict
  2 MiB drain cap per stream. Adding a sampled 2 MiB check cannot prove that the
  files never exceeded 2 MiB between polls. There is no verified bounded-log
  parameter in this DLL. Resolve that contract separately in source review
  before an executable Plan: either retain strict bounded capture with an
  explicitly reviewed provider change, or explicitly revise the contract to
  sampled enforcement. Neither change is implemented or authorized here, and
  rebuilding a native owner is not part of this proposal.

Keep World admission at 4 GiB RAM / 6 GiB commit, 64 MiB total output with the
existing metadata reserve, 128 KiB accepted transcript and 120 s total group
deadline. Compile **plus** Link share one 90 s window; do not grant 90 s each.
Fixture keeps 10 s; a proposed Check stage gets at most 5 s within the same group.
Imports, cleanup and finalization remain accounted for. H1's existing original
job cleanup is bounded at 5 s; document that narrower bound if reused instead of
silently inheriting T7's overall timing. The 2 s pipe-drain bound is relevant
only if bounded capture is retained; direct files must not be described as a
verified drain replacement.

Next action is a source-only decision on that log contract and a narrow World
profile review. Do not run the historical command below as a test of this
proposal. BO3 and its witness retain scheduling priority; no fourth World Run is
authorized by this document.

### Bounded-reader compatibility result, 2026-10-12

This checkpoint (`c03e9db`) applies while preserving the old strict stream cap.
The subsequent decision below explicitly changes that contract, so a shared
native-provider change is no longer the proposed next action.

The follow-up source audit found **no compatible World-only connection** between
the existing strict drain and the qualified direct-tool stages. The reader is
usable; the missing capability is at the native launch/handle boundary:

- `sdk/modding/beacon_tool_phase.py::copy_bounded` reads a stream in 4096-byte
  blocks, writes only the remaining allowance and flags excess bytes. World's
  existing `guarded_drain` additionally records arbitrary reader/writer/flush
  exceptions. This strictly limits the persisted destination stream to 2 MiB;
  it does not limit how many bytes a tool tries to emit.
- `Probe-NativeJob.cs::Start` takes output **paths**, calls `OpenLog` with
  `CREATE_NEW`, and places those file handles directly in both `STARTUPINFO`
  and the three-handle inheritance list. It exposes no reader stream, pipe
  handle, drain callback or log-cap parameter. Its use of `CreateProcessW`
  does not inspect `ProcessStartInfo.RedirectStandardOutput` or
  `RedirectStandardError`; setting those properties in a World profile cannot
  attach the Python reader.
- `Invoke-H1OwnedStage` calls precisely that `Start` overload. Wrapping `cl.exe`
  or `link.exe` in the existing Python `Popen` driver would restore the pipes,
  but make Python the original root. The real `Assert-H1CompilerRoot` rejects
  that root for both tool identities. Relabeling Python as the compiler would
  also break the required VCTIP-to-original-tool parent relation. This is not
  reuse of the qualified direct Compile/Link stages.

Reading or truncating a direct log after creation would only bound a later copy;
the original file could already exceed 2 MiB. Polling its size has the same
overshoot gap. Neither is substituted for strict capture. No wrapper, new
supervisor, shared-policy relaxation or partial launch adapter was added.

The inspected native source has SHA-256
`ddefa72ff2b98286cd585d1178c13e67dcd646bbcf39d51365660901366c5ca8`,
matching the source pin in the successful original native-owner witness; that
receipt also pins the same DLL hash recorded above. Thus this conclusion is
about the qualified provider's source, not an unrelated current implementation.

If the strict cap and direct-tool identities are both retained, the minimum
shared capability needed is bounded redirected output in that native owner:
pipe-backed standard handles without changing atomic original-job creation,
retained drain state with byte/error/overflow reporting, and a bounded drain
completion check after descendant closure. H1 must be able to request and check
that capability before accepting a stage; its default T7 behavior need not
change. This requires provider-owner work and a newly qualified DLL, not merely
a World argument change. Its implementation and native fault-injection witness
are outside this World-only change and have not been performed. Reusing the
Python reader unchanged would require exposing its input streams to another
runtime and adding coordination, which is not the smaller route.

Source verification completed: **3 existing bounded-reader tests, 15 existing
World driver/reader tests and 10 existing T7 Link policy cases passed**. Four
additional pure calls to the actual H1 root validator accepted direct `cl.exe`
and `link.exe` identities and rejected the Python-root alternative for each.
They used synthetic identities only: no native type import, native launch or
lease. No new test framework was added. The three World failure checkpoints are
byte-for-byte unchanged in Git, and the result remains **0/24 native World
fixtures**. The concrete next step is to route this bounded-output capability to
the shared provider owner for source review; no fourth Run is authorized.

### Current source candidate: sampled output, existing direct stages

The source-only checkpoint in this section was subsequently exercised once;
the successful native result is recorded in the next section. Its reviewed Plan
and provider pins were not changed before execution.

The coordinated architecture decision permits replacing the old strict 2 MiB
drain cap with an explicitly **sampled threshold**. This removes the need for a
new native owner or pipe infrastructure. `Run-ObserverHarness.ps1` now uses the
qualified H1 controller and existing T7 direct Link adapter in place. A small
World profile supplies artifacts, deadlines and output checks; no provider was
copied or edited. The historical Python launch driver is retained for provenance
and its tests, but is not on the new execution path.

The manifest is `iw7.world-clipmap-harness-plan/3`; the generated execution Plan is
version 2. There are four sequential original jobs under one reservation:
`cl.exe /c`, direct `link.exe`, the exact compiled fixture, then isolated Python
(`-I -S -B`) running the existing independent transcript checker. Each stage must
close before the next starts. Compiler-owned and linker-owned VCTIP remain
subject to the unchanged H1 exact-root/two-capture policy. The existing qualified
DLL is loaded under its read guard, not rebuilt. The member observer retains
its existing source-bound import at execution time.

| Contract field | Current source behavior |
| --- | --- |
| Each stdout/stderr file | Sample its actual size; refuse **above 2 MiB**. Exactly 2 MiB is allowed. This is not a write cap. |
| Polling | H1 sleeps 100 ms between ordinary polls, plus observation/I/O time. Samples occur before launch, in the loop, after job closure and before advancing. There is no guaranteed maximum detection latency or overshoot byte count. |
| Total output | Sample against 63 MiB, retaining 1 MiB for metadata; final accepted accounting stays at most 64 MiB. This is not an OS disk quota. |
| Time | Compile plus Link share one 90 s clock; fixture 10 s; checker 5 s; group 120 s from lease acquisition. Checks are cooperative, including before release. Failure cleanup uses the existing original-job stop with a 5 s confirmation bound. |
| Resource admission | One build reservation, 4 GiB physical / 6 GiB commit, one active original job, existing 85% commit-pressure check. These are admission estimates, not measured peaks. |
| Overflow or timeout | Fail the current stage, stop only its retained original job, require closure, and prevent later stages. A nonzero tool result also fails. Never relabel cleanup as a successful fixture. |
| Unconfirmed closure | Preserve the original owner, guards and lease in the retained host. Never replace an unclosed owner or use a previous closed owner to certify a failed new factory. |
| Finalization | Preserve the immutable `BeforeLeaseRelease` receipt, verification and single release attempt. Check the success deadline before and after release; the stored before-release snapshot never claims a confirmed pass. |

The source-derived maximum for the **passing fixture path** is **98,508 stdout
bytes**: 24 replayed records, each at most 4096 bytes including its framing and
newline, plus the largest 204-byte summary (`largest_record_bytes=4096`). Binary
replay prevents CRLF expansion. The intentional success marker on stderr is
62 bytes with LF or 63 with CRLF, and is checked exactly. The independent reader
retains its 128 KiB transcript input bound; its result must be at most 4 KiB,
report 24 records and match the frozen transcript hash/length. This is a source
calculation, **not a measured native output**. The checker and fixture are still
synthetic observer tests, not proof of a real map load, serialization or collision.

Compiler/linker diagnostics do not have a source-derived maximum: warnings,
tool failures or unexpected output can exceed the 2 MiB threshold between
samples. The actual peak can exceed both stream and total thresholds before
termination. A blocked host/I/O call can also delay deadline detection. No
strict disk or wall-clock guarantee is inferred from the poll sleep. If output
growth defeats the retained final-receipt accounting, the owned job is stopped
but publication/release remains unconfirmed and the host must remain available
for reconciliation; evidence is not truncated/deleted to make it fit. Toolchain
headers/libraries remain installed external inputs (`ToolchainFullyHermetic=false`),
as in the prior World harness; this change does not claim a hermetic SDK build.

Default invocation still only emits an inert Plan and its deterministic SHA-256.
New required parameters identify the reviewed H1 checkout (`StageProviderRoot`),
the existing `T7Build.Profile.ps1` (`LinkProfilePath`), and qualified native DLL
(`NativeJobAssembly`). Installed compiler/SDK/Python paths and a fresh World
runtime directory remain required. `-Run` additionally checks the reviewed
`PlanSHA256` **before admission**. A matching hash is not coordinated permission
to run; no fourth Run or lease was taken for this source candidate.

Pure verification covers the real H1 loop/T7 adapter with fake original owners:
stream and total threshold failures, a flood between the final poll and exit,
nonzero exit, time/commit/stop-request refusal, ambiguous closure, failed factory,
shared Compile/Link deadline and refusal to overwrite an unclosed owner. Fixture
output tests cover exact size/marker boundaries and the transcript read guard.
The finalization tests include a deadline reached after publication but before
release. An installed-tool inert Plan test checks deterministic identity, all
four stages, environment exclusions and absence of native type/process/lease
creation. These are source/mock tests; **native World remains 0/24**, with all
three failed checkpoints intact pending independent review and separate GO.

Current results: 55 World stage checks, 48 finalization checks, 17 Python tests
(including the retained 10 historical driver tests), and the deterministic
installed-tool Plan with 32 bound inputs passed. The 132 historical adapter and
console checks also remain green. The retained third attempt's linker response
file was inspected read-only to confirm the new direct link preserves its
options, object and library search paths. No extra linker-flag experiment was
introduced while separating `/c` and Link.

### Direct-stage native checkpoint: 24/24 synthetic cases passed

The [sanitized fourth-attempt checkpoint](../tools-source/asset-bridge/world/native-checkpoint-2026-10-12-stages.json)
records **one authorized invocation** of source `916d3fdeb19c642c7f29fc8bc6e2885601b6baa3`
and Plan `f3c03139ae349a2678964132eeffb74951426a607d9616e0538c33faa721c646`.
The retained host completed that invocation at `2026-10-12T13:29:34.2707242Z`,
5.817 seconds after its invocation marker. This includes wrapper/Plan/admission
time; it is not a measured native memory peak or a standalone stage duration.

All four original jobs exited successfully and closed. Compile and Link each
qualified their own exact VCTIP child and obtained a fresh original root0/Active0
snapshot plus an empty member capture. Their shared build clock reached
2,370.778 ms after Link (Compile's checkpoint was 1,500.087 ms). Fixture and
independent Check took 277.750 ms and 289.041 ms on their individual stage clocks.
No alternate compiler flags, console-count relaxation or retry was used.

The actual fixture transcript is **18,177 bytes**, with **24 records** and a
largest record of **1,254 bytes**. The independent reader accepted all expected
cases, including two positive observations and 22 deliberate refusals. Fixture
stderr was the expected 63-byte success marker. Compiler stdout was 33 bytes;
compiler stderr and both linker streams were empty. The checker emitted 377
stdout bytes and no stderr. The retained tree contains 11 files / **321,022 bytes**,
including the 27,271-byte immutable receipt. No sampled output threshold was
exceeded; this result does not turn the sampled policy into a strict write cap.

The exact fixture EXE is
`910e2450b052d0a0f868d2cf1550fc56c3ec2a9692b4abaf843925fa557acf7c`;
the transcript is
`b4332b0e0cd1cad3b2eddd87ab46880e2290e68a5775ba4dcea09b8cd07b98a8`.
The stored receipt SHA-256 is
`3286d12f564eb3d4819415950ce5329d44743ac090248f7847f4d29fdcc352f4`.
Its status remains `SyntheticHarnessValidatedLeaseHeld` / `BeforeLeaseRelease`.
The separate returned state, retained-host observation and postflight establish
the subsequent confirmed release and `SyntheticHarnessPassed` outcome; the
immutable receipt was not rewritten to predict that release.

Postflight at `13:29:57.6083995Z` verified all 32 bindings unchanged, zero leases,
no other heavy process, and the same Main process with two clients on `cp_zmb`.
Main's binary, scripts, configurations and bank fingerprints matched preflight;
the owner's unrelated Python process was preserved. The original host remained
alive through the no-quarantine check, then exited normally. At
`13:31:05.8780027Z`, the slot-release proof confirmed host exit, job closure,
zero leases and no other heavy process. All four original stage generations and
both observed VCTIP generations were also verified absent. No restoration was
needed and no Main/client operation was performed.

The previous three checkpoints remain **Failed / 0 of 24** with their original
raw receipt hashes unchanged. This new result validates the synthetic observer
fixture and its independent reader only: `engine_observed=false`; real map
serialization, collision and owner gameplay remain unvalidated. The unique GO
is consumed. Next work is coordinated review/integration of this evidence and
a separately reviewed real-asset plan, not another native invocation here.

The third attempt's exact Plan command is retained below for provenance. Its
runtime directory is now occupied and cannot be reused. This command describes
the historical `757e3a1` interface, not the current stage candidate:

```powershell
$world = Join-Path (Get-Location) 'tools-source/asset-bridge/world'
$planArgs = @{
    RunRoot = Join-Path (Get-Location) 'runtime/world-observer-harness-20261012-detached'
    VCToolsRoot = 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207'
    WindowsSdkRoot = 'C:/Program Files (x86)/Windows Kits/10'
    WindowsSdkVersion = '10.0.26100.0'
    PythonExe = (Get-Command python).Source
}
& "$world/Run-ObserverHarness.ps1" @planArgs
```

New reviewed Plans run from the repository root in a fresh PowerShell7 host. After
review and explicit coordinated GO only, the same command with `-Run` performs
admission and the single native group. An existing output directory is refused;
retain failed output and choose a new reviewed run identity for any later attempt.
The harness executable/transcript are never accepted as a real map observation.
The first attempt's local Plan, command and diagnostics are retained under
`world/.review/observer-harness-20261012-p2/`; its runtime directory is occupied
by the failed attempt and must not be reused. The corrected source's inert Plan
and retry evidence are retained under `world/.review/observer-harness-conhost-source/`.
That second runtime directory is also occupied and must not be reused. These
ignored review directories contain machine paths. The third Plan and failed
attempt are retained under `world/.review/observer-harness-detached-source/`;
its runtime directory is now occupied as well. Saving a review snapshot does not
change the inert Plan command's behavior.

After coordinated native GO, perform the following sequentially, using current
reviewed Resource-Scheduler/stock helpers and preserving occupied owner processes.
The estimates are admission requests, not measured peaks or active reservations.

| Stage | Proposed resource/time budget | Required result before proceeding |
| --- | --- | --- |
| Compile/run the standalone original-data harness | One compiler, `/MP` disabled; standard one-node build reservation **4 GiB RAM / 6 GiB commit**; at most 64 MiB fresh scratch; build deadline 90 s and fixture deadline 10 s | Actual C++ cases pass; every observer record parses and is at most 4 KiB; read counts are at most 2 KiB; outputs retain `signature_checked: false` and are labeled synthetic. |
| Compile/link private ZoneTool candidate | Reuse the pinned checkout's existing dependency artifacts read-only; rebuild the affected TU and link in an owned candidate output; **4 GiB RAM / 6 GiB commit**, one node, at most 1 GiB incremental scratch, deadline 10 min | Compiler/linker success, reviewed final diff and exact binary/patch/header hashes. Do not recompile all dependencies, copy the SDK or modify the shared provider to bypass an error. |
| One offline normal map registration | One headless candidate process, no client/server/gameplay; proposed **8 GiB RAM / 12 GiB commit**, deadline 180 s, at most 16 MiB logs; reuse existing stock | One genuine matching CLIPMAP record, `signature_checked: true`, bounded metadata, actual root name, loaded-flag change and matching root relation. Preserve failure diagnostics; no automatic retry or broader extraction. |

The ordinary engine load is larger than the observer's 2 KiB inspection budget;
the complete process must pass resource admission. Capture only the owned child
identity and use the existing recovery/timeout discipline. No lease, build,
stock copy or native observation was performed for this source correction.
The three failed native attempts remain documented above.
Only a successful real record can advance the root-class finding; collision
creation/serialization and the original-box test remain subsequent work.

## 2026-10-13: authored original arena ModelLab source route

The original seven-box arena now has an explicit material-bound source variant
and `iw7-original-arena-rigid-v1` ModelLab dispatch. It uses one combined surface
(168 vertices / 84 triangles), the existing named cp_zmb recipient material and
the existing FF runner/transaction/inventory/restoration. It does not masquerade
as a resident T7 export. The independent reader rechecks authored geometry and
packed streams after a future owned FF dump; the creator SDK receives all eight
relative staging paths for its own byte snapshots. See
`tools-source/asset-bridge/world/original-arena/README.md` for the source CLI.

Twenty-four source tests pass using authored synthetic records/evidence only.
Review found that the first reader variant omitted the model LOD partBits mask;
the correction checks the model LOD, surface group and surface masks together,
with corrupt first/last mask-byte cases and a failed re-dump case. The original
writer already initializes the LOD mask from the surface; the source fixture was
corrected to match it. The first candidate and review correction remain in Git.
No material-bound native writer, FF, game or collision test was run for this
source change. The queued null-material World Plan remains byte-exact and does
not qualify this separate source variant. Rendering can be validated before
collision; visible geometry still cannot be called a solid or navigable arena.

## 2026-10-14: fresh nondefault reference and original-arena FF execution source

The legacy recipient snapshot's three files were not recovered; a Rig inventory
name cannot replace them. The World route now measures exactly one nondefault
stock reference with the retained e7 candidate and binds CSV, complete success
marker, request, actual recipe digest and original native image/identity. It
refuses incomplete job closure/restoration and preserves material payload,
runtime and GPU claims as false. Review corrections for the receipt bindings
are separate from the initial stock-reference commit.

The specialized measurement caller and fresh material-bound writer recipe reuse
the existing selected 72-input stock profile and World/T7/H1 lifecycle. ModelFF
accepts that explicit stock mapping and the existing qualified community
candidate. Its original-arena candidate path runs strict build/verify/dump and
the independent P2 reader in separate original H1 jobs; root0/Active0 precedes
restoration/release. Native2f9462 TelemetryOnly remains the runtime provider;
SDKf4e5 is the creator source contract, not a replacement native runtime.
The immutable null-material Plan3057 remains NOT GO. See the original-arena
README for the concrete three-admission sequence and deferred evidence.

Twenty-six authored source tests pass, including receipt substitutions, all
three rigid masks, source caller mocks and unknown-owner retention. No stock
payload, native build, FF, process fixture, game or GPU was executed for this
source change. The read-only review used one GPT-6.1 Sol / medium agent under
the then-visible policy; later policy requires Ultra for any new Sol review.

Independent Ultra review found a reused-context factory gap: the previous closed
Owner could survive a throwing next factory and falsely qualify cleanup. The
World caller now clears Owner before invoking H1, matching Invoke-WorldStage.
The authored source mock covers success followed by a failed unknown factory;
the old owner is never stopped/reused and the new context stays unconfirmed.
This correction does not qualify native execution.

The same review also found that the reference checker was executed without its
own source/import hashes in the measurement Plan. ModelLab, the arena reader,
the shared record cursor and eager ModelLab/T7 contract imports are now in the
existing SmallPin/guard set. Checker changes after LIGHT change the Plan digest
or fail its source guard check; they cannot leave SourceHashesUnchanged true.
The 27th authored source test generates LIGHT Plans with nonexistent stock/tool/
owner inputs, mutates each checker/cursor source and verifies that the digest
changes without native types, stock reads, admission or output-root creation.

Architecture review found two additional opaque-read ordering gaps. The World
writer previously validated known executable hashes before Build admission;
the World FF candidate qualified its EXE/tlog before Extract admission. Their
actual validation now occurs under the existing reservation before any owner
load/start, with small source/producer metadata left in LIGHT. The unused CDB
hash check is omitted for the original-owner World path; legacy/non-arena HUD
qualification and diagnostics remain unchanged. The 28th source mock checks
deferred writer pins and World metadata versus admitted candidate validation.
All 28 World source tests pass; this still provides no native execution proof.

## 2026-10-14: stock timestamp guard for the retained arena recipe

The minimum source refresh found all 72 retained stock sizes, UTC timestamps and
attributes unchanged. PowerShell's JSON reader returns timestamp strings as
DateTime values; JSON serialization can also omit trailing fractional zeroes.
The arena measurement's string comparison would reject those identical times.
It now compares exact UTC ticks, matching the existing ModelFF guard. An authored
source test accepts string/trimmed/typed dates and still refuses a one-tick,
size or attribute change. No retail payload, native job, writer, FF or gameplay
was run. The former a49a Plan stays immutable and is retired from execution;
the corrected source requires a fresh reviewed Plan before any heavy slot.

## 2026-10-14: actual original-arena reference attempt M failed closed

Root approved one material-reference measurement only. The corrected source
`372b1a9` (merged by PR58 / `dec599d`) composed 899 files / 8,724,005 bytes with
explicit native2f TelemetryOnly providers. Their resource helper blobs match
current native0d7; that compatibility does not relabel the package as native0d7.
The internal recipe digest was
`f45318b6eac6b71d2885ef676036b2d090b2fbc1dd040d30a86040e239c2c65c`;
the outer plan-file digest was
`17186c04de585270644cfc015c0503a074f5af2b94cde23a56c93c10033c17ef`.
The distinct digests are retained at their original identities.

The fresh bundled PS7 host launched the retained e7 candidate at 05:24:07 UTC.
Actual qualification and stock content/identity checks ran under the helper's
one Extract reservation; no enclosing/nested admission or memory threshold was
added. The 72-entry selection staged 71 same-ID hardlinks plus the independent
77-byte sentinel. No whole game/client copy or game scenario was prepared.

The final log line was `Loading zone "global_mp"...`; stdout retained 1,449 bytes
and stderr was empty. At 05:26:32 UTC, the tool had consumed 148.45 CPU seconds,
with 443,027,456-byte working set and 593,072,128-byte private allocation. These
are one process sample, not measured peaks. At its 240-second deadline, the
original owner stopped/closed the exact job. No selective CSV or stock reference
success marker was produced. This is a load timeout, not a proven crash, missing
material, bad stock or memory-capacity finding.

The borrowed-file transaction restored all 74 managed entries. Stock content,
source hashes and the read-only sentinel were preserved. `state.local.json` was
published before lease release, so its old token and `LeaseReleased=false` are
not current reservation evidence. The original live host subsequently showed
no AppDomain quarantine object, and the authoritative registry had no token or
lease. After that proof, only its own PTY was resumed and exited with actual code
1. Fresh 05:32:44 UTC observations found the owned tool/host/parent and all native
heavy candidates absent, with zero leases. Main27016, banks/configuration and
owner clients were untouched. The before-release snapshot remains immutable;
the separate original-host and final postflight records explain the correction.

Pinned source `load_enemy_source_zones` calls global_mp synchronously before
global_cp/common_cp/cp_zmb. `load_zone` prints that log before DB_LoadXAssets.
The CP material query was never reached; without a native stack the busy-loop
location and root cause remain unknown. Diagnostic authorization arrived after
the tool had exited, so no reused PID was opened for a snapshot. No retry,
material-bound writer, FF, GPU or physics result is implied. Runtime/owner
acceptance remain false, and the M approval is consumed.

Next action: review the smallest CP reference path or a bounded native load
witness using the retained source/stock. A new candidate or repeat measurement
needs a fresh plan and coordinated slot. Do not replace the missing nondefault
reference proof with an E5 FF inventory name. The collision worker retains sole
native shape/runner ownership; eventual integration uses the same seven-box
scene JSON, reviewed transform and clear-before-delete lifecycle.

The E5 owner confirmed its actual build/verify/dump route loads only the produced
paris_model_probe FF, with CPPreload=false. Those handlers do not call the enemy
reference loader, and there is no scoped skip-global_mp switch in the retained
reference-check CLI. Its material inventory remains an external named reference;
it cannot replace the missing independent nondefault cp_zmb measurement.

## Proposed next witness: one bounded original load diagnostic

No supported CP-only reference switch exists in the retained primary CLI. The
opt-in World `-LoadDiagnostic` source route preserves loader order and stages
the same selected stock under one admission, then observes the original live
root. At 45 seconds with global_mp unchanged for 15 seconds, it records five
seconds of CPU/I/O by thread, one light stack minidump and offline CDB output.
Original diagnostic jobs share the existing reservation, with combined unknown
closure quarantining guards/lease even when the original target has closed.

After capture the exact target is stopped/restored, within a 120-second phase;
it reports DiagnosticCaptured, never a material/reference proof. Existing
snapshot flags 0x1820 contain normal stacks, region/thread information and
unloaded modules, without full-memory data. Dump acceptance is 32 MiB and output
thresholds are sampled. The detailed single-experiment contract and its primary
Microsoft source are in `original-arena/LOAD-DIAGNOSTIC.md`. Pure source mocks
cover one-shot/progress gating, original identity, offline-only debugger arguments
and unknown diagnostic retention. Capture, symbols and stack classification
remain unrun pending a separate reviewed Plan and coordinated GO. No T7 consumer,
caller51, loader CPP, stock payload or gameplay was changed or exercised.

# Neutral pair dependency Source foundation — 2026-10-15

This opt-in Source implementation owns two typed pure walkers, one local bounded
collector, a public-parse seam and an in-memory native Source patch renderer.
It does not change the historical CPP Q module or activate a native command.
The sixteen C++ fixtures are authored, **not compiled or executed**. The Python
Source checks do not establish C++ syntax, ABI, runtime or roundtrip acceptance.

The corrected gates are sequential: author and review this Source; obtain a
distinct complete CPP recipe/admission/GO; compile the actual production walkers
and run all sixteen fixtures; require sixteen actual PASS before any FF packet,
runnable qualification or weapon readiness claim. Source merge may precede CPP.
The earlier proposal's requirement to run C++ before CPP is superseded by this
gate correction. It is not a waiver of the future sixteen actual PASS.

## Typed local collection

`native_weapon_dependencies.inc` and `native_attachment_dependencies.inc` derive
from the two existing `load_depending` traversals in owner fork
`maxis0191/x64-zt` at `fab935826c898806855376662a8a03317b3ad8f1`.
`prepare_dependency_visitors.py` verifies the four exact native CPP/HPP hashes,
re-derives the reviewed walkers and returns patched texts in memory. It has no
filesystem output, process launcher, CLI registration or stock/data access.
Future composition must copy the declared production headers explicitly; no
generated Source package or frozen CPP Q input was modified by this milestone.

The templates take parsed `WeaponCompleteDef*` / `WeaponAttachment*` directly.
The small `parse_and_collect_pair` seam invokes each existing public `parse`
with its exact private name and passes the returned pointer, avoiding an unset
private `asset_`. File/hash/schema/input-size validation and lifetime ownership
remain obligations of the separately reviewed runtime caller. Public parse is
not a bounded JSON parser by itself. This Source milestone does not implement
or authorize that runtime caller.

The collector contains no zone or engine callback. It copies only dependency
names through the existing AV-only `player_definition_access::copy` leaf by
default. Fixtures inject an owned-memory copy callback. The native parsed roots,
their owned subblocks/arrays and name-pointer headers must already have passed
the caller's input/lifetime checks; the walkers do not make arbitrary native
pointers safe. They never recurse into a dependency's body.

References deduplicate by type/name and preserve every unique owner/path edge
in discovery order. Owners identify exactly `weapon:sdk_shredder_clone_zm` and
`attachment:sdk_shredder_clone_pap_zm`. Indices are actual native array indices.
Owned private edges are retained separately and cannot become ignore rows.
Both roots must be present in the correct order before freeze. After freeze,
mutation invalidates the collector. `verify_rows` checks exact ordered typed
external rows without allocating or changing `ignore_assets`; file publication,
manifest hash/readback and builder entry remain future caller obligations.

The legacy adapter alone holds a zone pointer and forwards the original
type/name sequence. It preserves unchecked legacy counts/null behavior and the
original invalid FX discriminant's else-as-FX fallback. The collecting adapter
rejects a nonnull unknown discriminant and cannot freeze/publish that graph.
Null FX cells emit nothing. FX/VFX scalar, notetrack array and attachment
projectile/charged paths share the same production helper.

## Closed external policy and its Source proof

Only FX, VFX and RETICLE are admitted as external reference-only candidates in
this initial Source step. This proves a native writer path for empty reference
placeholders, not retail-name resolution, availability or runtime acceptance.
The future builder must apply the frozen ignore rows **before** either full
owned root. `zone.cpp` adds a leading comma for ignored typed names, before
`init → dump_enemy_pack_asset → load_depending → m_assets.push_back`.

At the same pinned fork revision:

| Family | Source proof for reference-only path |
| --- | --- |
| FX | `iw7/assets/fxeffectdef.hpp` detects leading comma. `fxeffectdef.cpp::init` allocates a zeroed struct, sets only name and returns before parse/DB fallback. `prepare` is empty; `load_depending` has zero element counts; `write` writes the struct/name and skips null `elemDefs`. |
| VFX | `iw7/assets/particle_system.hpp` detects leading comma. `particle_system.cpp::init` returns after zeroed allocation/name. `prepare` is empty; `load_depending` skips null `emitterDefs`; `write` skips null emitter/scripted-input blocks. |
| RETICLE | `iw7/assets/reticle.hpp` detects leading comma. `reticle.cpp::init` returns after zeroed allocation/name. `prepare` and `load_depending` are empty; `write` skips null `widgetName`. |

`utils/memory.hpp::manual_allocate` zeroes the requested allocation.
`iw7/zonetool.cpp::dump_enemy_pack_asset` has a closed type set that excludes
FX, VFX and RETICLE, so its intermediate callback does not dump these bodies.
All paths above are relative to `src/zonetool/zonetool/` at the pin, except
`zone.cpp` and `zonetool.cpp`, which are under `iw7/`.

External ATTACHMENT is explicitly unsupported. Its `weaponattachment.cpp::init`
referenced branch has **no return**, continues through public parse/DB fallback,
and its writer writes the full attachment/subblocks. This change preserves that
legacy behavior. The owned private PAP remains a full definition, never an
external reference placeholder.

ANIM_PACKAGE, GESTURE, LASER, MATERIAL, RUMBLE, SFX_PACKAGE, TRACER, VFX_PACKAGE
and XMODEL are recognized and emitted by the pure walkers but refused by the
collector until their entire reference path is separately proven/reviewed.
Unknown types and IMAGE are refused. This initial refusal is a documented step,
not a permanent feature ceiling. No image/body lookup, exporter or hook is added.

## Fixed bounds

The collector allows two exact owned roots, 8,192 nonnull occurrences, 4,096
unique external references, 8,192 unique owner/path edges, 511 UTF-8 name bytes
plus NUL, 256 origin bytes and depth 32. Dynamic arrays are limited to 64 entries,
with 8,192 aggregate visited array elements. Copied names/origins and conservative
serialized JSON estimates each have a 1 MiB cap. Checks precede record allocation.
Names require bounded NUL, canonical UTF-8, no control characters, no reference
prefix and no empty/default sentinel. All failures poison the operation; no
automatic reset or larger budget is offered. Allocation failure also refuses.

The conservative JSON cap can dominate unique-reference/edge/text caps. The
production `Budget::permits` arithmetic is tested independently at each boundary
by the authored C++ fixture, alongside actual duplicate-occurrence exhaustion.
This does not invent a reachable graph at every simultaneous maximum.

## Validation and next action

Six Python Source tests exercise the real patch renderer with owned Source
fixtures, reject pin/statement/reviewed-walker drift, verify API separation,
preserve historical activation and inventory sixteen C++ cases. A separate
Source-only render against the four exact pinned native texts verifies byte
preservation outside the dependency regions and the one header insertion.
No C++ PASS is claimed from any Python check.

The next concrete gate is review of the exact Source PR and a distinct bounded
CPP recipe/GO. That recipe must compile this header/walkers with the exact pinned
native declarations and execute all sixteen cases with production code, then
compile both patched native translation units. Until that succeeds, no new
candidate executable, private readback CLI leaf, FF or runtime roundtrip is
qualified. The proposed `-iw7-neutral-clone-readback` remains unimplemented.

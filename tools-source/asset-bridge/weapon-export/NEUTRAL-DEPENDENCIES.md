# Neutral pair dependency Source foundation — 2026-10-15

The next bounded Source lot is documented in [NEUTRAL-INVENTORY.md](NEUTRAL-INVENTORY.md).
It adds a distinct descriptive inventory and pure identity contract. The current
inactive Source policy is FX/VFX/RETICLE/RUMBLE; the RUMBLE addition below has
not been compiled or run. Actual CPP F at Source `a97bfc9` passed the original
16 cases, 12 new cases and both native TUs, with independently verified closure. The E3 result
below qualifies only its earlier Source; F's exact pins/limits are in that note.

## RUMBLE Source-only extension — 2026-10-18

The only production change is adding RUMBLE to `reference_supported`. Existing
typed walkers, constructors, names, budgets, freeze/row checks, legacy routing
and private-root ownership remain unchanged. No arbitrary owned RUMBLE, builder
staging, CLI, token, activation, serialized manifest or export is added. The
strict Collector can now describe a RUMBLE reference and verify its exact
internal reference-only rows. Those rows do not authorize a builder.

The three new authored strict cases use the actual walkers and Collector:
weapon/attachment fireRumble deduplicate to one key with two owner/path edges;
RUMBLE plus FX checks exact discovery-order rows and missing/extra/reordered or
wrong type/name rows; invalid/default/comma/private-root RUMBLE names refuse.
Poisoned graph pointers test that these walkers inspect only the direct name.
MATERIAL and external ATTACHMENT remain refused. The original budgets and legacy
sequence cases remain in the fixture. Inventory's separate canonical identity
helper tests mixed RUMBLE modes in both orders; this is not Collector coupling.
Such coupling is still required before any generalized builder.

The current fixtures contain **19 strict and 13 inventory cases, AUTHORED and
NOT COMPILED/RUN for this change**. Exact Source review must precede a separately
reviewed CPP recipe and distinct GO/admission: compile/run both complete fixtures
and compile both patched native TUs before merge/adoption. Earlier E3, F and J7
results do not qualify this policy. Python Source checks do not execute C++.

This opt-in Source implementation owns two typed pure walkers, one local bounded
collector, a public-parse seam and an in-memory native Source patch renderer.
It does not change the historical CPP Q module or activate a native command.
Actual CPP E3 at Source head `05c28704ff0af07ab08b5b35681356999d96b26a` passed
**all sixteen cases and both patched native TU compiles**, with complete
dependency guards and inherited-input revalidation. Root independently verified
ordinary closure. This qualifies the bounded compilation/owned-memory checks;
runtime, FF, roundtrip, gameplay, physics and PAP transactions remain unqualified.
Earlier C and D remain failed historical attempts, as recorded below.

The corrected gates are sequential: author and approve this exact Source; review
a dedicated CPP recipe and obtain its distinct admission/GO; compile the actual
production walkers and run all sixteen fixtures, then compile both patched native
translation units. Only after these checks pass may this foundation PR merge.
Require sixteen actual PASS before any FF packet, runnable qualification or
weapon readiness claim. FF/full CLI qualification is a separate later gate.
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

Only FX, VFX, RETICLE and RUMBLE are admitted as external reference-only
candidates by the current Source policy. This proves a native writer path for empty reference
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
| RUMBLE | `iw7/assets/rumble.hpp` detects leading comma. `rumble.cpp::init` allocates zeroed `RumbleInfo`, sets name and returns before parse/DB fallback. `prepare` is empty; `load_depending` and `write` skip the null high/low graph pointers; write emits shell/name. |

RUMBLE's exact primary Git blobs at the native pin above are
`rumble.hpp` = `4a95159064885c3e53286e467d8d382f40e9c53a` and
`rumble.cpp` = `7ddf02027205952e67f2fa6d5292b6faa075d7bf`. This Source proof
does not establish retail-name availability, native/runtime resolution or a
writer/FF execution for this change.

`utils/memory.hpp::manual_allocate` zeroes the requested allocation.
`iw7/zonetool.cpp::dump_enemy_pack_asset` has a closed type set that excludes
FX, VFX, RETICLE and RUMBLE, so its intermediate callback does not dump these bodies.
All paths above are relative to `src/zonetool/zonetool/` at the pin, except
`zone.cpp` and `zonetool.cpp`, which are under `iw7/`.

External ATTACHMENT is explicitly unsupported. Its `weaponattachment.cpp::init`
referenced branch has **no return**, continues through public parse/DB fallback,
and its writer writes the full attachment/subblocks. This change preserves that
legacy behavior. The owned private PAP remains a full definition, never an
external reference placeholder.

ANIM_PACKAGE, GESTURE, LASER, MATERIAL, SFX_PACKAGE, TRACER, VFX_PACKAGE
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
production `Budget::permits` arithmetic is exercised independently at each boundary
by the authored C++ fixture, alongside actual duplicate-occurrence exhaustion.
This does not invent a reachable graph at every simultaneous maximum.

## Validation and next action

Eight Python Source tests exercise the real patch renderer with owned Source
fixtures, reject pin/statement/reviewed-walker drift, verify API separation,
preserve historical activation and inventory sixteen C++ cases. A separate
Source-only render against the four exact pinned native texts verifies byte
preservation outside the dependency regions and the one header insertion.
No C++ PASS is claimed from any Python check.

Eight additional declaration-only Python tests cover compiler input roles,
extensionless headers, tuple preservation, search-root boundaries, malformed
metadata, attached include-option suffixes, trailing-dot/space Win32 aliases
in every component and refusal of implicit roots. They do not open inherited inputs.

The initial reviewed head `6bbb3960c9ca7073d7d981cbb106ae67bf3886dc` wrongly
required the optional fixed-capacity `notetrackFXMapValues` pointer when NULL.
Source review found this before CPP. The renderer now skips a NULL optional
fixed-capacity pointer array and charges its capacity only when present; a
dynamic counted array still refuses a nonzero count without storage. The
authored positive fixtures explicitly retain the NULL pointer, and a negative
fixture covers missing counted storage. No failed C++ run is invented.

Actual distinct CPP C compiled Source head
`126404525068b8b65660a7c4893708dffafc8d41` with the exact native pin. The compiler
and its witnessed VCTIP child closed through existing H1; the fixture process
then printed fifteen PASS and `FAIL legacy_parity: fixture check failed`, exit 1.
The native TUs did not run. Source inspection finds the fixture set
`numComplexModels=2` with only `complexWorldModel` storage, while its recording
sink requires storage for all six counted arrays. The legacy adapter correctly
skips the other NULL arrays. The corrected fixture preserves a sparse legacy
sequence check and supplies five owned arrays of NULL entries for the strict
recording check. Production visitors, collector and legacy adapter are unchanged.

A nonzero shared count with some NULL model arrays is permitted by the original
native parser/traversal. It is an explicitly unsupported subdomain of the initial
strict collecting policy, rather than an intrinsically invalid upstream layout.
The sparse fixture checks the legacy contract; the populated fixture exercises
the stricter recording domain. No such layout is claimed observed in actual
retail bodies. Accepting it in collection can be a separate future Source
capacity change; this initial refusal is not a permanent platform ceiling.

C remains failed and unqualified. Its original context closed, all 828 retained
FileStream/SafeFileHandle references closed, three same-stream publication
readbacks and the last deadline passed, and the original physical terminal exited
1. A fresh snapshot found the four captured identities and leases absent. The
on-disk final snapshot honestly records guards held at publication; the original
in-memory witness subsequently verified their disposal. A new reviewed exact
Source head/capsule and distinct CPP GO are required to rerun the corrected
fixture and compile the two TUs. The local failure cannot use a CI billing
exception or count as sixteen PASS.

Actual CPP D at `d4aaf85d46ac7a7f7ac35e80c68a0351ade31256` recompiled and ran
all sixteen fixtures successfully. The weapon TU compiler exited 0, with its
witnessed VCTIP original job closed, but `Assert-T7Dependencies` then refused
`deps/gsl/include/gsl/gsl` outside the guarded set. The attachment TU never
started and final inherited-input revalidation did not run. All 834 original
FileStream/SafeFileHandle references subsequently closed after the three
same-stream publication readbacks and last deadline. The original terminal
exited 1; Root verified the seven captured identities and leases absent.
D remains failed and unqualified despite the real sixteen fixture PASS.

The local recipe had selected native header declarations by `.h`/`.hpp`, losing
ten extensionless GSL declarations already present in the hash-pinned historical
Q Source plan. `neutral_dependency_inputs.py` replaces this suffix guess with
finite roles from the pinned quoted `/I` roots and sealed INCLUDE/PATH/LIB roots:
`CompilerInclude`, `CompilerRuntime` and `FixtureLinkInput`. Each selected row
preserves its exact inherited path/length/SHA and records its role root and
parent-plan SHA. Unknown roots, malformed tuples and duplicate identities refuse.
Historical build artifacts outside those explicit roots remain excluded.

The declaration-only profile selects 682 tuples: 585 includes, 70 runtime inputs
and 27 fixture-link inputs. Compared with D's 668, this adds ten GSL headers,
three installed MSVC library debug-symbol inputs and one declared Windows runtime
resource. These are inherited metadata declarations, not newly inspected files.
Their actual byte verification remains mandatory under each distinct CPP lease.
They are never `IsText` Source bindings, and DEFAULT does not query them. No
post-compile additions, weakened dependency check, adopted C/D artifact or broader
asset export is permitted. A separately reviewed CPP E packet must repeat all
four phases under its own distinct GO before the merge gate can complete.

Actual CPP E3 completed those four phases on the exact Source head above and
native fork pin `fab935826c898806855376662a8a03317b3ad8f1`. All four processes
exited 0; the fixture printed the exact sixteen case markers and `16/16 PASS`.
Both weapon and attachment TUs compiled with the existing warning/error policy.
All three compiler dependency reports were accepted against the guarded set.
The 682 inherited inputs were reverified under the original lease. Ten parent
Source files, including the scheduler's transitive imports, were held before
imports and rechecked in the final Source loop. Earlier C/D are not retrospectively
credited with this additional transitive Source retention.

The exact E3 plan is 423,333 bytes, SHA256
`aa9d53ece2a4befa37ab09b342e629875647d0c12e019bda29fac0993e4e93dd`.
Three preopened ReadWrite publication streams were written, flushed and read
back through the same handles, retaining Source/opaque/publication guards through
lease release and the last deadline. Their 23,503 bytes fit the unchanged 1 MiB
metadata reserve; native outputs measured under the lease totaled 28,732,664
bytes. The disk final snapshot honestly records released lease/guards held;
the same original context then verified disposal of all 1,542 retained actual
FileStream/SafeFileHandle references before `CanExit`. The physical NoExit host
exited 0 and fresh postflight found all nine captured identities and leases
absent. Root independently corroborated the Source receipt chain, original
preexit witness, real terminal exit and fresh absence before qualification.

The short fixture's CIM registration error remained recorded alongside the
native original-job-already-empty marker and actual root exit 0; no cause is
inferred from its duration. Full kernel creation and CIM microsecond timestamps
remain separate in the original witness. No OBJ/EXE/PDB/SDK input was reopened,
statted or rehashed after release; later checks read Source evidence only.

The compiled Source revision is the exact head above. A later documentation-only
head records this result and must not be described as newly compiled. No full
ZoneTool CLI link/execution, FF, asset roundtrip, stock/clone/T2 body access or
gameplay occurred. The private readback CLI leaf remains unimplemented.

The next concrete gate is review of this documentation-only result and the final
exact PR head before merge. Next Source work can specify the closed private-pair
readback leaf and hash-bound inventory-before-builder transaction; activation,
full CLI build, FF and runtime operations require their own review and distinct
GO. The proposed `-iw7-neutral-clone-readback` remains unimplemented.

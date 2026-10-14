# Finite T7 weapon-name observation: unused source support

No BO3 weapon name has been observed in the retained corpus. The complete F
Freerun catalogue contains eight resolved props and two references. Its success
and the later visible platform model do not establish weapon availability.
The retained F closure has 23 qualified bootstrap files, including
`core_common.ff` and `core_specialists.ff`; qualification proves historical
identity/hash, not that a weapon type was loaded. C2 and prepatch code captures
also contain no weapon-registration evidence. No Freerun weapon probe is selected.

This source support stays **unused**. No command, shared prepare/build marker,
profile, launcher, caller or frozen plan enables it. The closure label is
`historical_f23_startup`, with `weapon_presence=unknown`. A future owner must
qualify the fresh scope, obtain the separate runtime GO and establish the actual
loading route. An enable marker is configuration evidence, not proof of a hook,
weapon, supplied zone, successful load or asset compatibility.

## Existing route and exact boundary

At native pin `fab935826c898806855376662a8a03317b3ad8f1`, T7 types are
Weapon 0x17, WeaponDef 0x18, WeaponVariant 0x19 and WeaponFull 0x1A.
The existing DB-add stub constructs `XAsset` and forwards the original type and
eight-byte header once. The C2 module supplies its existing POD-only SEH leaf
`c2_add_get_name`, using the engine's typed `get_asset_name(XAsset*)`, and its
LastError/errno guard. Weapon support reuses those helpers unchanged. It never
casts a WeaponDef, invents an offset, performs a default lookup, loads a zone,
reads geometry/pixels or installs a hook.

`wire_unused_module(final_c2_cli)` only appends support after the exact unchanged
C2 module. Missing/changed/multiple anchors, CRLF or a repeated addition fail.
It does not call any weapon function or enable C2. This is not a new build profile.
The shared V3 main, producer, source pins and current CLI remain unchanged.

The future existing-caller integration has four named boundaries, requiring its
owner's review before a new source cohort: explicitly enable before the audited
startup scope; call `weapon_names_begin(xasset, original_caller)`; forward the
existing original DB add exactly once outside every SEH/exception boundary and
pass its scalar header to `weapon_names_end`; explicitly finish after a proven
observation boundary. No lock is held across the original call. These calls are
not wired by this change and the caller must not claim an atomic DB snapshot.

## Finite text contract

The module observes at most eight calls of types 23 through 26, before any name
getter is invoked. Each selected name read is at most 96 bytes; a missing NUL,
getter exception or unreadable range is retained as an explicit refusal/prefix.
No engine pointer is retained, dereferenced by the reader or used as an output
filename. Names are hex bytes with unknown encoding; a leading comma is retained
as reference evidence, never stripped into a supposedly available weapon.

`[T7_WEAPON_NAMES]`, schema `iw7.t7-weapon-name-observation/1`, has one enabled
record, up to eight entries and eight correlated returns, at most one overflow,
and one finish: at most 19 lines, 512 bytes per complete line, 8 KiB own text and
16 KiB combined text. Every producer line is submitted once using WriteFile;
short/interrupted publication is incomplete evidence. No extra file is emitted.
Duplicate returns are suppressed and mark failure. The original return value is
preserved by the existing caller; a non-null result alone does not prove nondefault.

The reader strips only its exact markers and preserves other text byte-for-byte.
Unknown fields/types, mismatched thread/type/return, malformed bytes and duplicate
records fail. `Absent`, `Incomplete`, `NamesObserved` and `NoNamesObserved` refer
only to this finite observation. Overflow, name refusal, missing finish/return or
write failure never establish absence. Every result retains availability, zone
ownership, default resolution, role bindings, runtime compatibility and ready false.

## One next measurable step

Under a separate Root GO, produce a finite weapon-name report from the audited
existing startup registration route. Success is at least one actual bounded name
with its type/caller/thread/return evidence. Otherwise retain explicit no-name or
incomplete evidence. Then the asset owner can choose a real candidate and establish
its view/world role from primary Weapon data; this module does not infer roles.
No runtime invocation, compilation, game input read or weapon acceptance belongs
to this source preparation.

Initial source-test attempt: 18 tests ran with one failed negative fixture.
Its literal length replacement did not match the authored name, so the input
was unchanged. This is retained as a test-construction failure, not a reader
refusal failure or native result; the fixture must use its actual name length.

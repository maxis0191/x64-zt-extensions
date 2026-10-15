# Neutral registered player definitions: Source contract

2026-10-15: Source implementation, admitted PREP N and failed CPP N are recorded
separately. CPP N passed name8/argv28/primary36, then its definition fixture
failed compilation with C4702 under `/WX`; its 100 checks did not run. No new
IW7 TU, link, native serializer, extraction or game run executed. Actual M remains
the closed metadata observation described in EXPORT-COHORT.md: base type1,
PAP type0, raw PAP flag1/true, one association. Candidate J does not contain this
new route. Source checks and authored C++ checks are different evidence.

The new `-iw7-player-weapon-pair-definitions` route takes exactly six arguments
including the executable: `-headless`, that flag, `cp_zmb`, the exact 47-byte
two-row request, and `paris_enemy_cp_zmb_raygun_pair_definitions_a`. The export
caller requires the explicit scalar boolean `PairDefinitions=true`. Profile,
neutral definitions and modal selection cannot mix. Ordinary DEFAULT still
loads no native type, reads no opaque input, acquires no lease and creates no
runtime directory. The old native PROJECTILE/profile module/header prefix and
CLI suffix remain byte-identical at their normalized LF hashes.

The purpose is to observe two complete registered native definitions without
changing their values to satisfy the separate PROJECTILE3/3 author. It is not
an authoring mode, weapon grant or mechanics qualification.

## Finite preflight before the public serializers

Preparation verifies the normalized hashes of the two serializers, their two
public headers and structs.hpp at native pin
`fab935826c898806855376662a8a03317b3ad8f1`. Generation must reproduce the checked
readset exactly: 41 typed functions and 1203 macro fields. Unknown source,
macro/count expressions or generation mismatch refuse staging. No bypass CLI
exists for this verification.

The new mode preserves `globals.dump=false` during shared/map load and both
typed calls. It makes the same two exact registration requests and default
checks. Returned entry type/header, typed root/header/name, raw1/0/1 scalars and
the six bounded association arrays are inspected through the guarded reader.
Exactly one PAP pointer occurrence is required. It adds no scan, database
request, dependency-body capture, `load_depending`, dispatcher or dump hook.

Every scalar, pointer, count and string byte reached by the new readset requires
a copy callback. The production callback uses a small POD-only MSVC SEH leaf.
Only access violations are handled; other exceptions continue searching.
There is no unguarded memcpy fallback, broad catch or resume-after-fault path.
The unchanged serializers are invoked only after both complete preflights.

| Source policy | Bound |
| --- | ---: |
| Aggregate charged readable/copied spans | 1 MiB |
| Aggregate array elements | 8192 |
| Each dynamic count | 64 |
| Each string including NUL | 512 bytes |
| Nonzero script-string conversions | 2048 |
| Conservative combined JSON estimate | 2 MiB |
| Finite JSON allocation estimate | 16 MiB |
| Each native JSON file | 2 MiB |
| Neutral manifest | 16 KiB |

The allocation counter is a Source estimate for finite values, keys and
container/string growth, not a measurement or hard cap of the runtime allocator.
The existing owned job/group deadline/output budget remains the process boundary.
Counts/spans include overflow checks. Bools require raw0/1; floats must be finite;
bounded copied strings require NUL and valid UTF-8. Optional null references
follow the pinned serializer's shape. Referenced asset names are validated;
their model/animation/material/FX/audio bodies are not captured.

All three override tables are **inline arrays of 21** native structures. Their
whole spans and every nested element are checked; they are not nullable pointer
fields. Nested notetrack/suit mappings, attachment subblocks, fixed arrays and
accuracy curves are covered separately. Original knots use the native loop's
parent count, with the declared original capacity also required to cover it.

The two camo material tables are also inline: `Material*[16]`. Generation
explicitly dispatches these declarations through the typed inline helper and
visits all sixteen pointer fields/names. Complex-model and attachment variation/
material fields remain true pointer fields. The exact native declarations for
all macro array families were checked before this distinction was corrected.

Native turret STRING_ARR has an existing unusual conversion: four null pointers
produce four empty strings, while four nonnull pointers produce a repeated4x4
matrix. Mixed null/non-null arrays refuse before serializer entry. Nonnull
empty strings remain a matrix. The readset charges sixteen cells and four full
string passes per matrix, and records both resulting shapes. No macro repair
or roundtrip compatibility is implied.

Script-string0 follows the native empty-string bypass. Negative IDs are a
conservative refusal policy, not proof of a native pool range. Positive IDs
retain their full32-bit value, including values above65535. The Source binding
must equal the reviewed `SL_ConvertToString` address0x140C03300 and have an
executable committed page. The bounded converter uses the AV-only POD leaf,
then validates/copies its returned string. No Source pool-membership bound is
known. The unchanged serializers repeat those calls later: readability and
successful preflight do **not** prove ABI, identity, lifetime or a stable pool.
No hook freezes or replaces engine conversion. An AV/partial output must fail
without a completion marker or qualified receipt.

## Output and honest completion

Only the public `weapon_def::dump(WeaponCompleteDef*)` and
`weapon_attachment::dump(WeaponAttachment*)` write the two native files. The
native signatures are non-const, but their reviewed dump bodies only read the
definitions. No name, enum, flag, pointer, weapon field or mechanics is coerced.

The fresh output contains exactly:

- `weapons/iw7_shredder_zm.json`;
- `attachments/shredderpap1.json`;
- `player-definition-pair-manifest.json`.

The closed manifest schema is `iw7.registered-player-definition-pair/1`. Both
readbacks must retain the exact identities, integer1/0 types and literal true PAP
flag. The Source reader rejects duplicate/extra manifest keys, numeric coercion,
over-budget counters, mismatched native array shapes, extra/missing files and
path/size/hash mismatches. Only after both native readbacks and stock confirmation
does the caller set `NeutralCaptureComplete` and `FullDefinitionsObserved`.
Legacy `NativeExportComplete` remains false for this mode.

`templates_exported`/`full_definitions_observed` are observation flags. Author
eligibility, dependency bodies, ABI, lifetime, roundtrip, weapon grant,
projectile damage, physics, retail PAP transaction and gameplay remain false.
Native49 `prepare_weapon.py` is unchanged and rejects this actual1/0 pair; its
valid3/3 route is unchanged. A separate external manifest is not a tamper-proof
origin marker embedded in raw native JSON. No automatic provenance rejection
for a manually forged raw3/3 file is claimed.

## Verification and next gate

The Source suite executes the actual PowerShell closed reader and final readback
statements on small owned files. Hash failure, missing output or stock failure
cannot promote completion. Generator tests cover exact-pin drift, finite set,
unknown operations and before-output refusal. These are Source causals.

Review rejected initial head88370ea for two Source defects before any native
execution: the two inline camo tables were sent to a pointer-field helper, and
script-conversion fixture mutations used `internalName`, which the pinned
serializer comments out. The correction dispatches the actual inline types and
uses the dumped `attachPoint` field, checking the real resolver call count/ID.
The original77 Source tests were not proof of C++ typing or fixture execution.

Review also rejected head3be7ff3's fixture name buffers: the weapon/PAP names
need16/13 bytes including NUL. The corrected owned arrays use `sizeof(literal)`.
Source auto-review found that native `sha256::compute(...,true)` emits uppercase
hex (`dump_hex` uses `%02X`); the neutral producer now applies the existing
`to_lower` utility before writing the manifest's canonical lowercase hashes.
The closed reader and legacy producer remain unchanged. These were Source
corrections before any compilation or extraction of this mode.

`test_definition_readset.cpp` authors100 checks using the real pinned structures
and production `with_pair` gate. It covers unchanged values, missing copy,
integer-copy refusal, unreadable spans, count/overflow/string/UTF8/bool/float
refusals, inline21 arrays, curves, nested mappings/subblocks, all32 turret masks,
script conversion failures/full32-bit IDs, aggregate budgets and the AV-only
leaf. Its first actual compile attempt failed; none of those 100 checks has
executed. The existing name8/argv28/primary36 probes passed at the exact N Source
revision recorded in BUILD-COHORT.md, which does not qualify a later correction.

The build plan's explicit `PairDefinitionsCLI=true` requires both existing
fixture profiles and the fixed ten-stage sequence: name compile/test8, argv
compile/test28, primary compile/test36, definition compile/test100, one IW7 TU,
link. The definition compile must bind the exact native structs header via
`IW7_NATIVE_STRUCTS_HEADER`, all readset sources and compiler dependencies under
the ordinary source guard policy. Incomplete older6/8-stage plans cannot build
the new module. Old modules retain their existing6/8-stage contracts.

The C4702 correction moves the success return into the integer/enum fallback;
bool and floating-point branches retain their validation returns. `/W4 /WX`
remain enabled. Source regression checks reject the earlier shared-return
layout, but cannot establish successful MSVC compilation.

Next: finish exact Source review/CI/private merge, then a new Source package,
PREP sibling and separately admitted CPP capsule. Only its actual closed candidate may feed a
separately admitted neutral extraction. No CPP, Native, Extract, authoring or
game authorization follows from this Source document.

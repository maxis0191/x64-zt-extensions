# Pure native input preflight

`neutral_pair_bodies.validate_private_pair_bodies` consumes the original immutable
report and three payload buffers, plus the trusted external report length/hash.
It reruns PR215's raw binding before decoding either definition. Success returns
`None`. The call opens nothing and creates no native object, arena, route, CLI,
builder row, token or permission. Existing PR215 APIs keep their original scope.

The supported dialect is deliberately strict. A source conversion that would
default, truncate, lose a shape or normalize unsupported data is refused. A
successful synthetic example does not qualify actual captured input.

## Source and coverage

The source revision is `fab935826c898806855376662a8a03317b3ad8f1`.
`generate_native_body_schema.py` checks nine bounded LF-normalized Source text pins before
extraction. It joins the actual parser macros, native declarations and serializer
key sets. It accounts for 41 typed structures and 1,203 macro sites. Counts are
diagnostics: macro-only bodies must contain no unexplained statements, and the
three routines with manual branches have exact reviewed body fingerprints and
explicit ordered handlers. Unknown syntax, macro, type, member, count, packing or
manual routine refuses generation. The checked-in table is constant Source data.

```powershell
python -B generate_native_body_schema.py --native-source-root <pinned-source-root> --output <new-file.py>
python -B -m unittest -v test_native_body_schema
```

Regeneration must match `native_body_schema.py` byte for byte. Source input is
not vendored here. The generator never compiles code or imports a producer.
Native type sizes use pinned `assert_sizeof` declarations when present; other
small allocation types use the finite member-layout grammar. Alignment derives
from members, aliases, unions and active packing under Windows x64 LLP64/default
pack8. Pointer-only external headers retain their actual typed alignment but
allocate eight bytes, rather than a full external body. `unk0.material` instead
allocates a full 280-byte `Material`. These are Source assumptions for later
independent C++ checks; they are not a runtime ABI observation.

## Exact input rules

Objects have exact keys; booleans, integers, ranges and enum domains are checked
without coercion. Floating literals must remain finite and nonzero values cannot
underflow to zero during JSON or float32 conversion. UTF-8 is strict; duplicate
keys, BOM, trailing tokens, nonfinite values, surrogate/NUL strings, missing
consumed fields and unexplained extras refuse.

One explicit conversion-only exception applies to `WeaponDef.chargeType` and
`AttCharged.chargeType`. Their `WeaponChargeType : std::int32_t` declaration is
empty. The pinned JSON gitlink is `484483acad6d562306efc9b3c6d413404f1b1f8a`;
the actual selected single-include header has SHA256
`53855e4a20d7bc92d9624bf0d83fba8e22d0d9de83f9480bd4895651602fa8cc`.
Its enum `from_json` at 5274-5283 uses `underlying_type`, arithmetic conversion
and `static_cast<EnumType>`, reached by default `get_impl`/`adl_serializer`.
The generator also pins the include selection and native std_include macros.
Only an exact int32 integer is accepted, without bool/float/coercion or narrowing.
The descriptor keeps `semantic_domain_unknown=True`, an empty enumerator table
and `storage_domain_only=True`. This proves no charge-mode meaning. A new empty
enum, changed type/converter/macro or use outside these two scalar fields blocks
generation; this exception supplies no index/count or gameplay authority.

The finite bitfield rule preserves the five `GfxDrawSurfFields` widths
16/32/2/14/64 in unsigned64 storage units under MSVC x64/default pack8. The first
four share one unit and the last occupies a second: size16/alignment8, also for
the `GfxDrawSurf` union with `Packed128`. Another type, width sequence, mixed
storage type or packing refuses; this is not a general C++ bitfield parser.
Every other derived struct size must also equal its pinned `assert_sizeof`
when one is present, rather than silently masking a mismatched derivation.

Attachment keys such as `overlay.shader`, `projExplosionEffect.type` and
`projExplosionEffect.u.fx` are literal flat JSON keys. The attachment macros
stringify the complete C++ member expression (weaponattachment.cpp:115-172,
492-566), and its dump does the same. WeaponDef uses an actual nested `overlay`
object and `{type, fx}` FX cells. The native member path and JSON path are
different concepts and are never interchanged.

Every fixed array has its exact cardinality, including flat turret sound arrays
of four, inline material arrays of sixteen, three interleaved override tables of
twenty-one, and location damage arrays of twenty-two. Dynamic count groups use
one explicit null policy and equal positive lengths. This checks both mapping
buffers and all shared model variations before the native `MODVAL` assignments;
release-disabled `assert` is never a guard. Reticle counts target signed int32,
model/material counts target uint32, and the two outer notetrack table lengths
must fit the actual uint16 cast even though their stored counters are uint32.

The two parent accuracy-graph slots are always present. Each is null or a positive
array of exact two-float rows; counts fit uint16. Original graphs follow the
actual conditional dump at weapondef.cpp:2258-2267 and reads at 583-593:

| Parent counts | Original knot key and exact outer shape |
|---|---|
| 0, 0 | Key absent; no original-knot read executes |
| positive, 0 | One-element outer array containing slot0 rows |
| 0, positive | Two-element outer array: null, slot1 rows |
| positive, positive | Two arrays with their respective parent lengths |

Original name and count arrays still require two slots. Names may be empty
strings: that is the dump's explicit representation of a null native name.
Original stored counts must equal parent allocation counts in this conservative
dialect. Extra tails, explicit null replacing the absent whole key, missing
nonzero graphs and mismatches refuse. This is conditional consumption, not an
operator[] default, resize or serializer repair.

Empty weapon scalar strings are preserved. Empty attachment, asset and script
strings are refused where the native conversion would collapse them to null.
Zero-length allocated arrays similarly collapse to null and are refused. This
does not claim every legacy serializer output is admitted. The full private
profile keeps BULLET1/NONE0, true PAP flag, all six attachment keys, exact private
names and exactly one PAP association in the report-named slot.

## Ordered allocation and limits

One fresh arena is modeled from relative offset zero, weapon first and attachment
second. Every real allocation and string duplication advances the same cursor in
the pinned execution order; the three inline override tables are interleaved by
index. Multiplication and addition are checked in the uint64 `size_t` domain.
Before each typed event the current offset must satisfy its Source alignment.
FX memory allocated as `char` must also satisfy the effective typed header view.
Unknown/misaligned storage refuses. Count-zero/null branches advance nothing.

No offset rounding, string padding, reordered allocation, shadow arena or legacy
allocator change is supplied. A sufficient total size cannot establish alignment.
The actual allocator returns `pool + mem_pos` without padding and uses unchecked
arithmetic (utils/memory.hpp:102-128); its MessageBox/exit0 path is not validation.

Caps remain 2 MiB per raw definition, 32,768 decoded nodes and depth64 per body,
8,192 elements per JSON array, plus 8,192 **allocated native array cells across
both roots**. The aggregate counts each allocated scalar, pointer, script-string,
FX, knot or table array cell; inline cells already stored in enclosing structs
and standalone root/subblock/header allocations do not count as array cells.
Arena string storage is separately bounded by the two raw-byte caps plus 65,536
terminators; parser map entries are bounded by the two node caps. Both notetrack
buffers, their strings and distinct bookkeeping entries count independently.
These are logical input caps, not machine RAM minima or process commit estimates.

JSON trees and native parser `script_strings` vector capacity/allocator overhead
are outside the modeled arena. No exact STL heap-byte total is invented. A later
native owner still needs the real arena capacity, an aligned pool base, both
parser/maps and roots, original guards, and exact destruction order.

## Remaining gates

Actual bodies have not been inspected or admitted by this Source lot. Misalignment
can expose a legacy allocator limitation even for well-formed input; document a
future observation separately and pursue a reviewed allocator change if needed.
This conservative gate does not reduce the MAX objective.

Before native use, separately prove actual reopened FILE identity **before its
first read**, exclusive CWD/fastfile/search-path routing and restoration, durable
owners, runtime ABI and actual capacity/base alignment. Inventory remains
descriptive; strict dependency policy remains FX/VFX/RETICLE. No additional
reference family, builder adoption, branding rawfile, FF/readback, weapon grant,
physics, PAP transaction, BO3 authentication or gameplay acceptance is supplied.

## Review corrections

The initial Source candidate `1854dd2` passed its authored tests but discarded
bitfield widths, describing `GfxDrawSurfFields/GfxDrawSurf` as40 bytes. Review
caught this metadata error; `MaterialInfo48` and `Material280` were already
asserted and no current arena under-allocation was demonstrated. The finite
unit rule and shared-unit/crossing refusals above replace that derivation.

Review also found that the original280-versus8 test called the allocation helper
directly while the full handler fixtures kept `unk0.material` null. A new owned
private-pair positive reaches the real `unk_material` handler and requires its
280-byte event, name allocation, following attachment offset and6384-byte total.
Changing that handler to an8-byte shell now loses272 bytes and fails the test.
These are Source regression checks, not observations of any real input or arena.

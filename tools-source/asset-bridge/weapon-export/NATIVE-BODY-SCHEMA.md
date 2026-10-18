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

## Offline C++ constants projection

`native_pair_body_schema.hpp` is inactive Source data projected from the pinned
Python literal: 239 type records, 41 structures, 1,213 ordered operations and 17
operation tags. It does not decode input or construct native objects. Presence
bits distinguish absent, false, zero and empty values; integers retain a sign
and uint64 magnitude, including UINT64_MAX. Enum declaration aliases, shared
count names/types, manual arguments, direct sites and Source provenance remain
separate. Thirty pointer element labels are not expanded into layouts: known
labels require a type-ID tag; only unknown pointer labels use the exact literal
string tag. Unknown array element types refuse.

The adopted bytes are the single reviewed Source emission at generator commit
`cfd291253f8d836bb9e6b1d818272f5568990eef`, generator blob
`cf33622aa09ccb871d92c059d3df4cfe19691a78`, 50,953 LF bytes/SHA256
`35770c090a883e5edc2b28783a92d2954563b4fd1a62ca27949efbee54732939`.
The header is 1,073,140 bytes, SHA256
`dbedd4632d8bb20686c8c1355d4b0200fc2c6149ba141897007f41252f555b75`.
Its four provenance roles preserve the historical extraction generator4717a82a,
the new projection generator, the original SCHEMA and the body validator.
The projection generator was frozen externally before header emission, avoiding
a generator/output self-hash cycle. The transitive executable Source was pinned
before execution; no SCHEMA module was imported.

An independent Source aggregate reader reconstructs every field, required order,
type and presence from the emitted text and compares it to the original literal.
The adoption check also requires the exact raw header pin. These Python checks
supply Source fidelity; the separate constants-only C++ result follows.

On 2026-10-18, J10 compiled `test_native_pair_body_schema.cpp`, freshly linked its
single produced object and ran the fixture, all at exact Source
`1adcece1ae57697156f5e54e44030d881feb6ad2` with explicit provider Source
`efe6761bc6a96581140767bde9f82816af579375` and the pinned `fab9358` native model.
The three original stages exited 0 with confirmed job-tree closure; their measured
stage durations were 1796.3844, 1059.5636 and 192.3097 ms respectively. The four
observed PASS groups were `fixed_width_sign_magnitude`,
`ids_spans_element_canonicality`, `utf8_pool_bytes` and
`ordered_records_aliases_manual_sites`, followed by `IW7_BODY_SCHEMA_CONSTANTS=4`.
Raw stdout was 164 bytes/SHA256
`fecb014d4b92312bc7697fe37dbff63ba97769ad0d9044834319912ca56c6340`.
Its CRLF bytes were read and hashed before explicit CRLF-to-LF ordinal comparison
with the Source literal; all three stderr logs were empty.

Root's observation of the same originals before exit recorded 31 Source records, 498 input
records and 3 publication streams: all 532 saved FileStreams/SafeFileHandles and
all 3 original owners were closed, with the 6 inner/7 external witnesses and their
references preserved, lease null and `CanExit=true`. The 490 selected input
declarations plus 4 opaque parent declarations are metadata counts, not a claim
of 494 unique physical inputs. The maximum measured output was 13,315,956 bytes
under admission; the original clock was never reset. The final disk receipt
described a released lease with guards still held pending postflight; the
later observation established actual disposal. The external caller Source and
host handle stayed retained until the reviewed terminal gate, closing Source
before disposing the same Process object. A separate kernel CloseHandle return
was not measured.

Root issued the distinct terminal GO at 08:32:15.8839269 UTC, then observed true
exit 0 / terminal chunk `c5cec0`. The terminal event's exact UTC and total PTY wall
time were not separately measured. Root's fresh check at 08:32:46.2630292 UTC
found the seven expected processes absent, an empty Version1 lease registry and
the protected Main unchanged. The probe's registration error
`Original process differs from scheduler observation.` remains recorded alongside
`Original job already empty before CIM registration`; no cause is inferred from
its short duration. Earlier Source A's residual JSON-binding refusal and the
Source/harness corrections remain retained; only the corrected B packet ran.
After release, this documentation update read only Source and own JSON/text logs,
without reopening opaque native outputs.

This result qualifies the standalone constants fixture and its compiled table,
not a body decoder/interpreter, real-pair admission, arena or engine ABI,
builder/CLI/FF integration, readiness or gameplay. It does not qualify the future
DOC commit or merge as newly compiled Source.

## Inactive SAME-owned C++ body preflight

`iw7::neutral::player_pair_bodies::validate_owned_pair_bodies(const
player_pair_input::OwnedInput&)` ports the existing Python dialect to the pinned
constants. It calls the real J9 report checker before decoding either body. A
public PRIMARY SAX guard checks floating lexemes and decoded duplicate keys;
ordered DOM decoding then reads the SAME owned role bytes, with independent
32,768-value/container, root-depth64 and 8,192-element array limits in both passes.
Raw BOM/NUL, malformed UTF-8/surrogates, decoded NUL, trailing input and silent
callback discard are refused. Lexer/JSON/STL temporaries use ordinary memory;
this is not allocation-free or an arena-owner guarantee.

The seventeen operation tags and eight manual handlers preserve literal keys,
null/count relationships, named counters and the full Python front door: private
names, BULLET1/NONE0, literal PAP true and one declared association in six slots.
Strings do not resolve an unused pointer target layout; an actual layout request
still refuses an unknown type. Demand/domain checks complete before a second
weapon-then-attachment trace enables Source alignment, without padding or reset.
The trace is ordinary internal diagnostics, not a parse capability or permission.

Boolean, integer and floating variants remain distinct. Signed zeros with a zero mantissa are
allowed for floating targets; a nonzero mantissa underflowing to zero refuses.
IEEE binary32 conversion preserves Python's rounding just above its maximum up
to the exclusive halfway overflow boundary, without an out-of-range C++ cast.
No engine ABI, real-pair input, native core/arena/routing, builder, CLI, FF,
readiness or gameplay is supplied. The new C++ fixture is AUTHORED, NOT COMPILED
or executed: eight groups have the authored marker `IW7_OWNED_BODY_PREFLIGHT=8`.
Its ordinary-memory causal arms the first standard-new failure reached after
entering the decoder; the exact failing allocation is unknown. This does not
prove late-allocation or general unwind behavior. Six Python checks cover static
Source dispatch/order/integration only. J10 qualified only the earlier constants
fixture. New compilation and exact original closure require their own reviewed
recipe and distinct GO.

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

Original name and count arrays still require two slots. Every non-null name,
including an empty string, duplicates its UTF-8 bytes plus NUL. The native
branch tests JSON-value `empty()`, which is false for a string even when it
contains no characters; it is not a string-emptiness check. A null name skips
storage only when both the corresponding parent count and the uncoerced
original count are zero. Nonzero-count null names and other shapes refuse.
An empty string in a dump is therefore not an allocation-free null name on read.
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
Unknown/misaligned storage refuses. A count-zero allocation adds no bytes;
its separate non-null graph-name string still adds its NUL byte. A permitted
null name adds no string storage.

No offset rounding, string padding, reordered allocation, shadow arena or legacy
allocator change is supplied. A sufficient total size cannot establish alignment.
The actual allocator returns `pool + mem_pos` without padding and uses unchecked
arithmetic (utils/memory.hpp:102-128); its MessageBox/exit0 path is not validation.

J5 at `d6525ca` measured one first-refusal boundary: ordinal24, size16/count1,
used6194/cap6208, attachment-entry phase and type alignment1. The compiled root
units312/5144/536 matched the Source assumptions for that fixture. Source
reconstruction identifies the prior model's first omitted request at graph
name0 (one NUL), then graph name1 (one NUL). It predicts the observed final
request and attachment offset5594 modulo align8=2. Earlier rows and that offset
are reconstructed, not individually measured; no general ABI proof follows.
The previous twenty-row projection is incomplete and remains historical.

The corrected owned zero-graph fixture uses two JSON null names and strict new
weapon/report identities. Its demand6208 and attachment offset5592 are unchanged.
J1-J5 inputs/results stay immutable. No allocator, native parser/cut, padding or
capacity change is made. The new Source inputs have not been natively qualified.
See the [JSON empty API](https://json.nlohmann.me/api/basic_json/empty/).

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

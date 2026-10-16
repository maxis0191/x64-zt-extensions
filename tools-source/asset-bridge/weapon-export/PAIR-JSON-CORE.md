# Authored JSON pair through the real native cores

This Source lot isolates the two pinned JSON-to-native implementations and
authors an end-to-end C++ fixture. **J1d compiled both cores at `c9d8332`, then
fixture compilation failed before link or execution.** The current support-list
correction has no CPP qualification. A fresh gate must prove the complete real
link and parse; earlier allocator fixtures and partial core compilation do not
qualify the complete witness.

## Pure Source renderer

`prepare_pair_json_core.render(sources, stage_core=False)` accepts exactly twelve
bounded Source roles. Full LF-normalized SHA-256 checks precede every cut/output.
DEFAULT returns the original strings byte-for-byte, including CRLF, without
filesystem access. Literal `stage_core=True` composes the existing three
unconditionally rejecting FILE/route hooks using an explicit supplied Source
header, then the unchanged PR218 checked-memory overlay.

The native pin is `fab935826c898806855376662a8a03317b3ad8f1`. Exact inclusive LF
cuts and their hashes are constant in the renderer: weapon map 6–16, macros
30–190, helpers 192–1139 and root 1158–1162; attachment map 84–94, macros
108–177, 31 helpers 179–662, dispatch 664–673 and root 694–782. The source is
read by the caller from pinned Git, never copied manually into this repository.
Unknown/missing/duplicate roles, hashes, cuts or staging anchors refuse without
returning a partial output. Generated packages/native checkouts are not edited.

Opt-in returns three additional native Source strings:

- `iw7/assets/weapon_pair_json_core.hpp` declares the mutable-JSON API.
- `iw7/assets/weapon_pair_json_core.cpp` contains the real weapon helpers.
- `iw7/assets/attachment_pair_json_core.cpp` contains the real attachment helpers.

The API is `parse_weapon_json(ordered_json&, zone_memory*, ScriptStrings&)` and
`parse_attachment_json(...)`, in `zonetool::iw7::pair_json`. The maps are two
separate durable `vector<pair<scr_string_t*, const char*>>` instances. Actual
first-pointer-wins registration and zero script indices are preserved. Context
parameters are threaded through the real helpers; explicit void expressions
handle unused parameters without weakening `/W4 /WX`. Per-TU static map helpers
avoid a duplicate link symbol. Weapon parent counts still precede the final
`weapDef` allocation. Pointer-name shells use their actual native allocation
expressions; the manual full `unk0.material` allocation remains unchanged.

Legacy file wrappers retain their exact path, exists/null-missing, logging,
open/size/read/close and JSON construction. Only their allocation/parse/return
tail delegates to the same core with their existing map. Original helpers are
moved once; unique marker comments allow reconstruction against the inactive
Source output. Legacy private map/getters and unrelated operations remain.

The standalone uses the real `structs.hpp`, pinned JSON with
`JSON_DIAGNOSTICS=1`, STL and the PR218 memory header. No `std_include.hpp`,
virtual asset interface, init/prepare/write/dump, fatal enum conversion,
DB/SL/engine/FS stub or full CLI is included. `structs.hpp` itself requires
`d3d11.h`; all actual SDK/STL/toolchain inputs must be explicitly declared and
admitted in the later native recipe. No SDK file is queried by this renderer.

## Complete authored witness

`authored_pair_json_fixtures` reuses the existing owned Source fixture builders.
It creates three complete variants and runs production PR215/216 against the
four immutable original buffers: report, weapon, attachment and CSV. Thirteen
Native60 qualification flags stay false. Technical clone labels are required
schema constants, not evidence that a game definition was captured. Every
variant has demand 6,208 bytes, weapon-definition offset 384 and attachment
offset 5,592 in the unpadded Source trace. Names have fifteen bytes; the initial
sixteen-byte authored names were refused by the alignment check and corrected
in the data, without allocator padding or relaxed validation.

`render_header()` emits the approved bytes and external expected pins in memory
only after all three variants validate. It also emits a literal oracle,
independent of the native walkers: four typed references, four distinct edges
and global `occurrences()==4`. These are the owned PAP attachment, same-name
FX/VFX references and a reticle. There is no count per tuple or edge, and no
reference-family policy change.

`test_authored_pair_json.cpp` consumes that header. It makes one private copy of
all four buffers and rehashes **those copies** against the trusted Source pins
before any JSON decode or arena. It never computes an expected pin from input.
Only the three Source-approved byte sets are qualified by this finite binding;
there is no general C++ schema validator or transferable success token.

The fixture uses the existing `OwnedPair` lifetime storage, one real checked
arena per pair, weapon then attachment with no reset, two map owners, actual
returned roots and the existing `inventory_pair/Inventory`. Its copy callback
accepts only the retained live arena range. Inventory data is copied/frozen
before roots/maps/arena are destroyed; only copied strings and rows escape.
The external PR218 report precedes and outlives the arena. No-op FILE/route
storage indicates that no such operation occurred; it proves no FILE seal.

Eight named C++ groups are authored:

1. Fixture-local SHA256 known vectors, required before pin checks.
2. The real pair plus approved same-length rename and FX/VFX swap variants;
   a prefab golden inventory fails the mutant oracles.
3. The rename bytes against old trusted pins refuse before decode/arena.
4. Invalid UTF-8, duplicate/missing-field raw mutations with old pins refuse
   by pin before decode/arena. Separate Python checks show production PR216
   rejects those invalid inputs even if their raw report/pins are recomputed.
5. Durable distinct maps, zero indices and preseeded first-pointer-wins.
6. Real checked capacity refusal before a second parse or publication.
7. A deliberate non-null string in the boolean `papAttachment` after trusted-byte decoding
   makes the real second core throw; its original JSON exception survives
   explicit free and destruction, with one reported cleanup attempt.
8. Bypassing the real weapon core cannot retain roots or publish inventory.

No VirtualAlloc/VirtualFree redirect or fake parser is supplied. Success would
require the real OS release report; OS failure would fail the witness rather
than be reclassified or retried. This Source text has not proved those results.
Source review corrected an earlier erased-field fault: the real macro skips a
missing/null field, so that mutation could not prove a parser exception. The
authored fault now reaches its actual `get<bool>()` with a non-null string.

## Validation and next native contract

Source checks exercise the actual renderer against owned grammar, pin/bound
ordering, no-I/O DEFAULT, wrapper reconstruction, context propagation and
authored production validation/oracles. A separate pure render of the real
pinned Git sources verifies the actual cuts and core output; this is Source
evidence only. H3b still qualifies its older allocator/three-TU compilation,
not this new core/link/fixture.

Source checkpoint, 2026-10-16: 68 targeted tests passed across
`test_pair_json_core_source`, `test_pair_session_source`,
`test_pair_checked_memory_source` and `test_native_body_schema`. The real pinned
Git render passed DEFAULT identity and exact reconstruction of both inactive
wrappers. The product boundary check passed with 992 tracked files, 974 exports
and three dependencies. No native input, compiler, linker or arena was opened.

The later separately authorized J1d CPP attempt compiled both real cores with
exit zero, then failed fixture compilation with C1083: Inventory's
`native_weapon_dependencies.inc` was absent from the prepared support set.
`native_attachment_dependencies.inc` was omitted as well. No link, fixture
group or legacy TU ran. J1d remains immutable FailedClosed, with
`NativeInputsReverified=false`; original postflight and true terminal exit
completed, and Root independently confirmed closure before releasing the slot.
The authorized diagnostic read covered only fixture stdout (288 bytes, SHA256
`0bbee7c4dbe6be81b5269e786f9eeec75599a339f97a958f60aea829d100d91b`)
and empty stderr. No SDK or native artifact was reopened.

`authored_pair_json_fixtures.FIXTURE_SOURCE_FILES` now declares all six owned
witness/support files, including both transitive Inventory walkers. The next
Source preparer must consume that list and pin each file from the exact product
head, with both generated headers supplied separately. A Source regression
reads actual local includes and exposes the old four-file omission. The authored
case header remains byte-identical (80,847 bytes); parser code, input pins,
oracles, qualification flags and `/W4 /WX` are unchanged. This correction has
not been compiled or linked and does not reuse J1d objects or qualification.

Before merge, review the exact Source head and prepare a fresh minimal native
capsule with both real core TUs, the real inventory support, generated authored
case header and this complete fixture. Compile and **LINK** without invented
engine/FS symbols, run its eight groups and compile the affected native wrapper
TUs. Keep `/W4 /WX`, actual input admission, original owner/job/guard/publication
closure, true terminal exit and independent Root fresh checks. Do not reuse a
consumed H3b plan or infer permission from an empty heavy slot.

FILE/route activation, arbitrary definitions, captured U1/T2/body/stock, full
CLI, FF, engine ABI, game and NativeD remain closed. `Ready`, actual parse
qualification and actual allocator-closure qualification remain false until
their own evidence and decisions exist.

# Inactive pair session Source

This lot implements ordinary lifetime/event models and three **unconditionally
rejecting native Source hooks**. It opens no actual input, constructs no native
arena/parser, seals no real route, and wires no CLI, builder or producer. The
schema-to-native bridge and real Windows FILE inspector do not exist here.

`prepare_pair_checked_parse.render` takes exactly ten pinned Source texts from
native `fab935826c898806855376662a8a03317b3ad8f1` and support merge
`0d56ddb107b51e6741b178d1f8cf7b927226e3b6`. Every pin is checked before staging.
Its default returns the exact input strings, including original newlines.
`stage_inactive=True` selects only an in-memory Source overlay. It is not native
permission. No output package, compiler or child process is invoked.

The overlay adds the authored header, two `parse_checked_inactive` overloads and
a filesystem `pair_route_seal_inactive` constructor. All three call the same
noreturn `reject_native_activation` before any open, size, read, allocation,
native parse, route capture or mutation. Neither mutable request metadata nor
changing the returned diagnostic dictionary can enable them. Original two-arg
parsers, filesystem mutators and memory allocator remain unchanged. Existing
Source preparation/CLI paths do not import or select the overlay.

## Lifetime storage and event contracts

`native_pair_session.hpp` has no Windows/native includes or I/O. Its ordinary
`FileIdentity` and `ReadRequest` are data, not validation tokens. `FirstReadOrder`
copies those values and models guards retained -> one role/stream open -> exact
ordinary-file identity check -> size -> first byte -> close -> guards released.
Wrong role, null/swapped stream, foreign volume/file ID/size, early read/release,
checker read/seek/close and retry/reopen refuse. A stream cookie is never an OS
identity, and model events do not prove any real FILE or original guard exists.

The generic `ScopedRoute` captures/restores an owned fake environment and records
restore failures without throwing from its destructor. A thrown `enter` attempts
restoration before rethrowing. Cleanup success is merely diagnostic. There is no
real CWD/search-path environment, alias exclusion or seal implementation.

`OwnedPair` is noncopyable/nonmovable ordinary storage. Its factory supplies
unique guards, raw-buffer owner, route scope, arena storage and two **separate**
parser/map objects in declaration order. A missing/throwing earlier component
prevents later component callbacks. Returned roots are explicitly retained once;
the interface `pointer()/init/prepare` path is not used. It retains copied
inventory only after roots, without conversion to Collector/builder authority.
The aggregate does not perform schema validation or qualify its factory.

Cleanup drops inventory/borrowed root views, attachment parser/map, weapon
parser/map, arena, route, raw buffers and original guards last. Borrowed const
views must not outlive that owner. No native factory is supplied. Authored
factories use only fakes and their constructor refusals are normal C++ throws.

## Explicit uncovered boundaries

The contracts apply only on normal return/status refusal and exceptions that
actually unwind. Native `zone_memory(size)` at fab935 memory.hpp:34 can fail
`VirtualAlloc`, show MessageBoxA at43 and call `std::exit(0)` at44. That real
fatal branch is **NOT COVERED**; local RAII/route/original-guard closure and a
successful operation do not follow from exit0. Capacity/base checks do not
guarantee OS allocation success. A fake constructor throw does not qualify this
branch. No allocator fix, failure probe or new RAM minimum is introduced.

The following still block actual activation even if every model/fake passes:

- Same-original-owner raw report/byte binding and PR216 validation before arena
  construction, with no bool success flag or fabricated capability substituted.
- Live underlying FILE/OS-handle identity before **any** size/read/seek/JSON
  action, held ordinary-file/no-reparse/write-delete-denying original guards,
  exact absolute rb/use_path=false path and no exists-probe/reopen fallback.
- Real exclusive CWD/effective filesystem.cpp fastfile/ordered search-vector
  seal. Header `static fastfile` is TU-local; `set_fastfile` repopulates ambient
  routes. Mutable `get_search_paths` aliases or another thread cannot be made
  safe by a mutex/snapshot around only this new wrapper. A closed fresh call
  graph/no escaped aliases or a separate writer/alias evolution must be proved.
- Real arena capacity/base alignment and the non-unwinding fatal allocator
  branch, separately reviewed compilation/operation and original-owner closure.

The conservative boundary preserves the MAX objective and leaves these future
evolutions explicit. Inventory policy stays FX/VFX/RETICLE; no dependency family,
asset adoption, CSV/branding, zone/write/readback, FF, grant, runtime ABI,
physics/PAP transaction or gameplay qualification is supplied.

## Verification scope

Python checks execute only Source validation/staging and boundary checks. They
exercise the real renderer, not a duplicate renderer, and inspect inactive hook
bodies/default preservation, guard order, no copy/move, restore failure reporting
and absent integration.

`test_pair_session.cpp` authors twelve future checks using the production header
with owned fake identities/routes/components: ordering and refusal, unwindable
restore/partial construction, both map lifetimes and guard-last destruction.
It is **AUTHORED, NOT COMPILED OR EXECUTED** in this Source lot. Source checks do
not claim those C++ cases passed. A later CPP operation needs separate admission.

```powershell
python -B -m unittest -v test_pair_session_source
```

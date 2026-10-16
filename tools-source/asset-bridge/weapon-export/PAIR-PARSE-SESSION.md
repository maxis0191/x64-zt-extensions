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

`test_pair_session.cpp` authors twelve checks using the production header
with owned fake identities/routes/components: ordering and refusal, unwindable
restore/partial construction, both map lifetimes and guard-last destruction.
Python Source checks do not execute those C++ cases or grant native permission.

```powershell
python -B -m unittest -v test_pair_session_source
```

### Admitted CPP G checkpoint — 2026-10-16

A separately reviewed and admitted five-stage operation compiled Source
`2b48cd810de3c7bd8cb005f2ea07d17bdb0fb27d`, tree
`ae57ab273fa504b4451987a38b61d877f7af2123`, against native Source pin
`fab935826c898806855376662a8a03317b3ad8f1`. Later documentation and merge commits
are not additional compiled heads. No old object or earlier CPP qualification
was inherited. The staged project sources were freshly obtained from that Git
pin; the compiler/SDK declarations remained opaque until admission.

| Stage | Observed result |
| --- | --- |
| Production-header fake fixture compile | Exit 0 |
| Production-header fake fixture run | All 12 checks PASS; exact stdout verified; exit 0 |
| Patched `weapondef.cpp` compile | Exit 0 |
| Patched `weaponattachment.cpp` compile | Exit 0 |
| Patched `filesystem.cpp` compile | Exit 0 |

All five original process/job trees closed. Each compiler's retained `vctip`
member was observed and closed through its original job; final active/listed
counts were zero. The probe recorded `Original process differs from scheduler
observation.` during CIM registration. The pre-existing reviewed fallback
confirmed the captured original job was already empty, the original process
exited 0 and the expected twelve-check stdout matched. This does not establish
why the registration observations differed, and no retry or adoption occurred.

Each of the four compiles verified its 222 bound inputs; actual compiler
dependencies remained inside the guarded set. Inherited inputs were rechecked.
Maximum observed output was 34,976,985 bytes under the fixed 256 MiB bound.
The group/compile/probe deadlines were 600/120/15 seconds; positive 4/6 GiB
planning estimates introduced no RAM or commit admission minimum.

The retained original context confirmed owner closure, lease release, zero
remaining guards, measured/final same-stream readbacks within the deadline, and
all 1,619 original FileStream references plus their 1,619 saved SafeHandles
closed. The three original publications were read back on their original
streams; their pre-disposal snapshots are distinct from the later closure
proof. The bundled physical NoExit/dot host remained open for that proof, then
exited normally with code 0. Root independently verified all eleven tracked
process identities absent and the account lease registry empty before release.

The initial separate receipt helper was rejected in Source review because its
arbitrary absolute JSON destination admitted alternate streams. The preserved
sibling B correction binds one literal owned Source destination, checks ordinary
non-reparse ancestors, and uses bounded CreateNew ReadWrite publication,
Flush(true), same-stream byte/hash/JSON readback and actual stream/SafeHandle
closure before returning metadata. Seventeen Source causal checks passed;
positive publication used an explicitly substituted isolated Source/fake path,
never a false actual preexit receipt. Its caller held and pinned the helper's
original Source stream, dotted those same held bytes, rechecked it and confirmed
the original Source guard closed. The new publication's actual references were
checked inside the writer before return; they were not exported for a later
reference recheck. No native output was reopened, inspected or hashed after
release. The original plan, runner and launch capsule remained unchanged.

Reproducibility bindings retained with the local operational evidence:

| Source evidence | SHA-256 |
| --- | --- |
| Exact G plan | `574905d074b13954864828b7b3ec28a929662b95865735482579cdf4cf72668f` |
| Original-context B preexit receipt | `fc1f76df94e7b3ed29a4bc214b178165846fa894012cc6f7cd56cf8d0dbaa6cc` |
| Independent Root closed postflight | `065ceab54730ac47158aa477eb3db3783831281dca22c4478f6f146ee5dd41ed` |

The same code head also completed 169 Python module tests: 168 passed and one
existing composed-package dependency test skipped. The ten targeted Source
tests passed separately. These are local results; hosted jobs refused before
any runner/step because of the account billing/spending condition are **not CI
passes** and require the existing narrowly scoped workflow exception.

CPP G qualifies compilation of the inactive hooks and the twelve owned fake
cases only. It does not execute native parser bodies or the real allocator,
inspect a live FILE, prove a route seal, create a full CLI, or authorize any
actual pair input, FF, runtime, grant, physics/PAP transaction or gameplay.
Fatal allocator closure and actual activation remain false; Ready remains false.
The next step is a small separately reviewed Source proposal for the original
raw-buffer bridge, live-file admission and fatal allocation boundary.

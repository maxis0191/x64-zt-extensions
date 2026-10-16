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

## Opt-in checked allocator — V9c

`prepare_pair_checked_memory.render` accepts only the exact 3,000-byte UTF-8
memory header at native `fab935826c898806855376662a8a03317b3ad8f1`, SHA-256
`9025b835313ee45ba3418e3322210dec3b6d334e504a1dd3b59e9f38e2898f35`.
It performs no I/O or invocation. DEFAULT returns that same input text without
staging. Literal `stage_checked=True` renders an in-memory overlay only. Removing
the explicit checked additions reconstructs the original Source exactly.
No consumer or existing pair stager imports/selects this overlay.

Source review of initial head `ba299e8` found the character bound was checked
too late. The corrected entry checks exact str type and at most 3,000 characters
before NUL scan, UTF-8 encoding or hashing. A causal trace checks oversized
ordinary, NUL-containing and invalid-Unicode texts refuse before those actions;
the independent exact byte length, strict UTF-8 and Source hash checks remain.

The staged `zone_memory(checked_memory_tag, size, report)` constructor binds an
external original-owner report once. It captures failed VirtualAlloc's error
immediately and throws a fixed-message diagnostic. In checked mode, capacity
exhaustion and multiplication overflow also throw before pointer arithmetic,
zero-fill or position changes. Successful allocation preserves the original
packed offsets and no-padding trace, including zero-count behavior while Live.
H3b exercises these behaviors through fixture-local fake OS calls. Real OS
failure and arena closure remain unqualified.

Both checked public `free()` and the existing destructor use the same private
release state. The attempt is marked before the single VirtualFree call. Success
is terminal/idempotent; repeated free/destruction never calls VirtualFree again
or on NULL. Failure is terminal/sticky and preserves the first return/error and
original pool identity without clearing, retrying, transferring ownership or
reclassifying it as Closed. A primary allocation failure poisons later use but
still allows its one pending cleanup attempt. Allocation (even count zero),
clear, string duplication, statistics and copy from a checked source refuse
before subsequent pool use. The legacy copy behavior remains outside checked
mode; the mutex already implicitly deletes assignment, so no operator= fix is
introduced.

The original report must be constructed before and outlive the arena. It is
noncopyable/nonmovable, exposes read-only diagnostics, and has no reset or
readiness authority. It preserves primary and cleanup errors separately after
arena destruction. Checked release catches unexpected lock/API exceptions,
records a terminal cleanup exception without inventing an OS result, and never
replaces an unwinding primary exception. A report or destructor return is not
proof that the OS released a pool. A failed release remains unqualified.

The mode/report fields change class layout. CPP G compiled the earlier `2b48cd8`
code and does not qualify this overlay, any new header, affected native TUs or a
full CLI. Legacy DEFAULT Source and its two fatal paths remain unchanged. Those
paths are constructor failure at memory.hpp:44 and capacity exhaustion at119;
neither is globally repaired or covered by the opt-in path.

`test_pair_checked_memory.cpp` authors twelve production-header cases using only
test-local redirected allocation/free/message calls and a small static fake
buffer: constructor/capacity/overflow refusals, remaining-capacity checks,
zero-count/packed layout, copy refusal, free-to-destructor success and failure,
repeated free without retry/NULL calls, terminal-use refusal, and durable
primary/cleanup reports. The durable-report case also authors an explicit fake
VirtualFree-throws subcase: one attempt, no retry on later free/destruction,
unavailable OS result, no invented error and the original primary preserved.
Lock-throw handling remains Source-inspected only and is not exercised by the
fixture. **All twelve named cases passed in H3b; allocation/free calls are fake.**

The H2 attempt on 2026-10-16 stopped at its first fixture compilation with
exit code 2: `/W4 /WX` rejected two signed/unsigned comparisons between the
`DWORD` cleanup error and signed ternary constants in the durable-report case.
No fixture case executed, and none of the three affected translation units
compiled. The failed state, including its incomplete stage telemetry and
unverified native inputs, was preserved. Original owner/job, retained streams,
saved handles and three publication readbacks were checked closed; a Source
failure receipt
preceded true terminal exit code 1 and independent process/lease checks.
The correction types both ternary operands as `DWORD`, keeping `/W4 /WX`.
It changes no allocator or report behavior. H3b used fresh Source bindings and
a separate reviewed execution GO; H2 remains failed and is never requalified.

The fifteen targeted Python checks pass real renderer Source causals, exact
default/reversible legacy preservation, state/side-effect order and absent
integration. At Source head `a0abfdf`, the complete Python module suite had
184 tests: 183 passed and one existing composed-package dependency test skipped
(76.222 seconds). That earlier Source checkpoint compiled/executed no C++.
The fifteen targeted checks passed again on `ffc2ea2` in 0.007 seconds. The
unchanged Python suite was not repeated for the two C++ constants or later docs.
Fake tests cannot establish real OS failure or actual arena closure.

### H3b native compilation checkpoint — 2026-10-16

The compiled code head is `ffc2ea25c3c2754291a10f6ab5e3754129663ef6`, tree
`8ad3ccd792122ef77224fabe4898d35a81eb11ff`. Documentation/merge heads are separate
from that compiled revision. Native Source remains pinned to
`fab935826c898806855376662a8a03317b3ad8f1`; the current scheduler providers came
from core `d271f6e680cfdc2d09d2b3dbc23d9e96aa23eeb1` and were byte-identical to
the reviewed provider implementation. The checked memory header is still
10,176 bytes, SHA-256
`47affa362ea7d42131030396af828252b598e751f118f0bb8e747730e9ddefa0`.

All five phases exited zero: fixture compilation, twelve verified fixture
cases, then `weapondef.cpp`, `weaponattachment.cpp` and `filesystem.cpp`.
The three TU compilations and the fixture retained `/W4 /WX`. Every compiler
completed its original-handle verification and telemetry-child closure. The
short-lived fixture exited before CIM registration; the existing guarded
original-job-already-empty path established closure without adopting a new
process. All five original stage closures were confirmed. Compiler dependencies
remained within the guarded set, and all 682 retained inputs were reverified
before release; no postcompile guard was added.

The admitted group kept its original 600-second deadline, 120-second compile
limits, 15-second fixture limit and 256 MiB output/1 MiB metadata bounds. Maximum
recorded output was 34,803,446 bytes. These are bounded compilation results,
not performance or real allocator-failure acceptance.

The measured and before-release publications were read back while the lease was
held. The final publication was written and read back after release through its
same retained original stream, before guard disposal. The preplanned finite
PASS postflight then checked all 1,629 original FileStream
references and 1,629 saved handles closed, along with the same three publication
entries, original owner/job and both held Source-helper streams/handles. Its
separate bounded Source receipt was flushed, reread for byte/hash/strict-JSON
equality and closed inside the writer before return. No OBJ/EXE/PDB or SDK input
was reopened after release. The retained original terminal subsequently exited
zero; the worker's postexit observation found all eleven owned host/launcher/
compiler/fixture/telemetry identities absent and the lease registry empty.
Root independently confirmed the actual terminal result and the same fresh
absence/empty registry at `2026-10-16T04:32:21.8923478Z`. A separately authorized
Root Source-only fixture-log read found twelve PASS lines plus the exact
count marker in 766 stdout bytes and empty stderr; it opened no opaque artifact.

The immutable H3b plan SHA-256 is
`66d2a325b6877746acee403364f2c7fdda93b04b80e8686a9ba52f380299ca1c`.
The separate preexit Source receipt is 31,590 bytes, SHA-256
`8f6002cb52b1c68a7a13cd8852f4b1c35b18d34865fda936b1f412777b3797cf`.
Those receipts qualify this bounded fixture/TU checkpoint only. Earlier H2 and
the first H3 Source DEFAULT refusal retain their failed outcomes. That DEFAULT
refused an old exact-head constant before native effects. H3b's successful
DEFAULT and twenty finite-policy Source fake causals are separate from its
subsequent actual C++ run and do not prove original native closure themselves.

The three PR217 hooks remain unconditionally rejecting. Same-owner raw/schema
binding, live FILE identity, real route/alias exclusion and actual allocator
closure still block activation. H3b supplied no actual raw body, live arena,
full CLI, FF or game operation. Its separately admitted compiler/SDK access
does not authorize integration or another run. Final exact-head CI disposition,
independent review and the merge audit remain separate gates. Ready remains false.

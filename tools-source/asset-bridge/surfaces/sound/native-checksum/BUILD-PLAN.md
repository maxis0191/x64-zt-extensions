# Private checksum build Plan C: review only

The source launcher and its Plan are runnable, but no native build or C++ probe
has been authorized or executed. The coordinator must review this exact Plan and
give a separate GO. The failed SAB/FF run remains preserved; its strict reader
is unchanged. Neither this Plan nor the input seal establishes the native fix,
SAB serialization, playback, deployment or owner acceptance. `Ready` is false.

## Exact local bindings

`runtime/content-surfaces/original-sound-checksum-build-plan-a` contains:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `build-plan-c.local.json` | 28618 | `a0389f94f3ad2488a76b7c30229ec6a5486b145e448cc62e2b8a4d3ce9000a38` |
| `build-command-c.local.ps1` | 615 | `9c2977b50cbf92fc6c694a63c9dcf73b1795c421a81b7f4de55353f681f4fe60` |

The short command starts a fresh PowerShell 7.6.5 host with `-NoProfile`, the exact
Plan path/hash and `-Build`. Its existence is not permission to invoke it. Without
`-Build`, `Build-ChecksumCandidate.ps1` only validates small guarded source/Plan
files and the completed Seal C manifests. It does not request admission, import
the scheduler, compile a native type, inspect processes, hash the reusable
objects/libraries, create the candidate directory or invoke another process.
The Python worker also defaults to Plan, and its execution path requires the
outer run/lease bindings.

Earlier local Plans A and B remain preserved and unexecuted. The
final candidate path, `runtime/zt-sound-md5-b`, was absent after all default-Plan
tests. No shared native or H1 output is changed. The fourteen response-file
commands retain the source proposal's eight compilations, two probe links,
two probe runs, one private archive construction and one candidate link.

`prepare_build_plan.py` reads only the small command review, Seal C manifest,
final sealing state and helper sources. It binds the 1410 existing inputs to
manifest SHA `f52867e7c26d05466ba57d72eef601d42376c1109dfcf61f219a1a028229f388`
and final sealing-state SHA
`fc502fb025a87278c9d9b9854b5186383d94b98add0c230ea39124404247c582`.
It neither rehashes those large inputs nor creates the native candidate.

## Owned execution and proof boundary

After explicit GO, one complete Build admission requests 4 GiB RAM / 6 GiB commit.
It covers fresh input verification, native work, closure and final source/output
proof. Each of the 1410 source, toolchain, object, library and debug inputs is
opened read-only with write/delete sharing denied, metadata-checked and compared
to Seal C before native work. Guards stay held through a second hash/metadata
proof after the original job is confirmed closed. The five final artifacts are
also rehashed after closure. No shared PCH is consumed by the eight compilations.

The entry opens recipe/entry/core/receipt guards before its first hash/parse,
then guards every discovered helper before hash/import. Hashes and JSON reads
use those same retained streams. The small bootstrap guards stay held through
the Plan return or execution lifecycle. There is no hash-then-open gap.

The existing `BuildJob.cs` F6 owner is reused unchanged:
`f6be2a4cafddb78b5e07a6802354575ada418cb7643d96a3abd0a4c063bc6387`.
The supervisor, closure collector, diagnostics and residual predicate are exact
copies from GSC revision `eabe74ab65d8ce2a943b54d24b15a60749a0cf2a`.
The existing `Rig.JobMembers.cs` observer is also unchanged. No replacement job,
process-identity or telemetry-classification framework is introduced.

The root Python process is created suspended, BelowNormal, without a window,
inside the existing non-breakaway kill-on-close job. Identity comes from retained
original handles; Resume precedes bounded scheduler/CIM registration. All
fourteen native commands run sequentially inside that one job through the
unchanged material phase runner and bounded SDK drain. Both pipe-drain calls
must return normally. Nonzero exit, missing EOF, a BaseException, phase timeout
or receipt disagreement fails the run; there is no automatic retry.

The narrow `BuildReceipt.Core.ps1` callback validates sound-specific evidence
inside the unchanged v6 completion collector. It verifies the fresh Plan/run/
lease/root binding, fourteen native phase receipts, the two actual native probe
JSON outputs, three executable hashes, eight compiler-log hashes and the twelve
unchanged common-member digests. The source-bound worker parses the actual
include logs, refuses an unsealed header or the shared old header, and compares
the thirteen archive member payloads before and after reconstruction.

The existing residual rule can only qualify its exact pinned vctip image as one
completely identified member of the original job, with two fresh matching
captures. The configured compiler is a file witness, not proof of ancestry.
The two-second drain deadline is unchanged. The collector checks 30 files at
most in this recipe (including its build receipt, compiler and residual image),
under its unchanged 32-file / 128 MiB bound. Actual duration remains unmeasured.
The large PDB/library and 1.1 GB input recheck happen after positive job closure,
outside that drain interval, while the original admission and file guards remain.

The native environment is explicitly declared. `CL`, `_CL_`, `LINK`, `_LINK_`,
`LIBPATH`, `PYTHONPATH` and `PYTHONHOME` are empty; x64 MSVC 14.44.35207 and SDK
10.0.26100.0 search directories are explicit. Compiler language is English,
processor count is one and TMP/TEMP point inside the candidate. The parent
environment is restored immediately after root creation. These pins cover the
declared tool files and observed include closure; they are not an attestation
of loaded memory, every Windows DLL or filesystem isolation.

All new files, including logs, debug output and supervisor state, count toward
the 512 MiB observed stop threshold; 768 MiB is the planning ceiling, not a quota.
Commit pressure above 85% or `stop.request` fails the run. The global observed
deadline is one hour, including callbacks and final writes; individual native
phases keep 240 seconds or 30 seconds for a probe. Blocking I/O cannot be
preempted. A late read counts returned bytes, then fails. A late final state
write cannot preserve a successful result.

Failure preserves output. Confirmed job closure permits cleanup and release;
unknown factory/closure, an unresolved post-run source proof or refused lease
release retains the reservation explicitly. The original owner, input/artifact
guards, bootstrap guards, reservation and context are strongly rooted together
in `AppDomain.CurrentDomain`, under `IW7.SoundChecksum.Quarantine.<token>`.
They outlive the invoking script scope. An existing key is refused, never
silently overwritten, and production code never automatically clears a root.
The entry verifies that its exact bootstrap is retained before returning.
These host roots do not promise handles survive host termination. No lease
is manually deleted. Input and artifact guard open/dispose counts are recorded.
The final state counts its own serialized bytes. Success requires released
admission, successful closure, before/after input proof and complete artifacts.

## Source and mock verification

No test below invokes a compiler, librarian, linker, C++ probe, ZoneTool or game.

- Seven Python tests cover exact original/patched probe contracts, typed flags,
  duplicate JSON keys, a thirteen-member COFF fixture and one replacement,
  missing/duplicate/truncated members, sealed include closure, actual existing
  drain adapter EOF/BaseException failures, changed images/receipts and incomplete
  sealing lifecycle refusal.
- `test_build_lifecycle.ps1`: thirteen source/mock cases, 72 assertions. They cover
  success, nonzero root, factory/identity/closure/release failure, input drift,
  late blocking read, failed post-run proof, late final receipt and the dynamic
  sound callback dispatch, plus late helper loading, late Prepare and late
  original-identity getters. All three late cases refuse Resume; an already
  prepared root is stopped through its original owner. No actual lease or
  native type is created.
- `test_build_quarantine.ps1`: fourteen assertions on two ordinary child-script
  returns, exact host-root associations, still-held small file guards, refusal
  to overwrite a quarantine and coexistence of separate reservation keys. Only
  these explicitly identified fixture roots are cleared. It performs no GC
  experiment and starts no native process or reservation.
- `test_build_receipt.ps1`: fifteen cases with real small guarded fixture files,
  checking stale identities, untyped values, incomplete/reordered steps, changed
  artifacts, wrong/unsealed header claims, changed common payload digests and
  invalid actual native probe/phase JSON.
- `test_build_entry_guards.ps1`: fourteen real denied write attempts on disposable
  copies at parse/output boundaries; six files become writable after Plan returns.
  Admission, Add-Type, CIM, process creation and reusable input hashing are trapped.
- Both actual PowerShell and Python default Plan C invocations pass. Candidate
  output and the native owner/observer types remain absent.

## Independent source review corrections

Review of `d5b2214` found two P2 gaps before any native GO. Script-scoped variables
did not provide an explicit host lifetime for quarantined owner/guard references.
The local AppDomain policy now follows the pattern reviewed in downloader
`4773bb2`, retaining the whole original context without modifying the shared GSC
provider. A temporary reviewer GC witness was not executed; this finding was
source-based. The ordinary repository tests above verify scope-return rooting
and guard behavior without retrying that experiment.

Review also found missing fresh budgets between helper initialization, suspended
Prepare, original-identity reads and Resume. The local wrapper now checks after
initialization, immediately before Prepare, after Prepare and immediately before
Resume. Budget measurement and pressure callbacks are followed by an unconditional
fresh monotonic check, so a slow callback cannot authorize an expired continuation.
The existing provider's deadlines and implementation remain unchanged.

Plan B and its command retain their original 28618/615-byte identities:
`6f32a843b685165b6d0ed040ad5f60f32f26e334913e90c06e4ae4da9e01350d` and
`701ecfc01babfdcfd0d93d79725e883cd56cc8f153e574d169ae90e6ded3994b`.
They are obsolete review evidence; neither was invoked for a native build.

Next action: independent coordinator review of this source, exact Plan C,
environment, seal and unchanged qualified providers. Only a new explicit GO can
authorize one native build attempt. Any later SAB/FF rerun remains separately gated.

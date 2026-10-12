# Minimal T7 catalogue/export build

This is a source preparation and an executable, default-read-only build entry.
It is not a native result, a coordinator GO, a stock plan or a T7 engine launch.
The coordinator integrates this work and owns the private PR/CI/merge workflow.

`prepare_build.py` renders the current reviewed CLI patch into seven private
files: three translation units, the changed xpak.hpp, the two exact conversion
headers and the 51-case name fixture. It derives four response files from the
retained E7 compiler/link tlogs. It neither modifies the shared ZoneTool checkout
nor copies a source tree, SDK, game or binary. Preparation directories are
create-only; superseded plans remain available and do not authorize a new run.

The build replaces main.obj, zonetool11.obj and xpak.obj. It retains all 410 other
E7 objects in their exact link order, 18 project libraries and one resource.
Original /MT, /O1, /Zi, /W4, /WX, /fp:precise and c++23preview remain. PCH /Yu and
case-sensitive /Fp are replaced with /Y-; original quoted-include directories
are added for the small private overlay. Every TU has private object, PDB and
sourceDependencies outputs. Each /D argument stays on the same response line,
preserving the 12 definitions and avoiding the Sound D8004 failure. Link keeps
the manifest options, resource and /INCREMENTAL:NO with private EXE/PDB/LIB/EXP.

## Exact execution profile

Run-T7Build.ps1 defaults to a source and metadata check. It verifies the supplied
plan SHA, runner/provider/source hashes, fixed stages and limits, fresh private
output and recorded input sizes. This path does not hash binary inputs, load
native providers, obtain a lease or create the candidate root. Only `-Run` after
the coordinator's GO admits the group and enables execution.

The one account-wide Build lease requests 4 GiB physical and 6 GiB commit. The
launcher and children use BelowNormal priority. Six sequential stages are fixed:
name helper compile, helper probe (exactly 51 checks and empty stderr), main,
T7 zonetool, xpak and final link. Compile/link deadlines are 120 seconds each;
the probe gets 15 seconds; the entire admitted group, including input checks,
gets 600 seconds. Output stops at 256 MiB including logs/debug/temp/receipts,
with 1 MiB reserved for the final receipt. These are estimates/limits, not
measurements. The existing H1 64-entry output guard is also retained.

The native supervisor is the existing witnessed NativeJob assembly, SHA256
5f613ebb83019dbf4bfa4f6a93c5329098343729b70acc2cfa70aa8b64f195f8.
H1Native.Core, H1Native.Compiler, H1Native.JobMembers and MaterialV2's compiler
policy are pinned external providers. No process/ownership/stop framework is
added. The T7 profile supplies artifact names and the whole-group deadline.
H1's original handle identities, two exact vctip observations, root exit zero,
fresh empty job proof, failure cleanup and quarantine are unchanged. Unknown
compiler/link residuals are failures; no broader kill or adoption is allowed.
The next job starts only after the prior job is closed. The lease/guards survive
all stages and are released only on confirmed closure; a failed closure stays
quarantined. The generated ZoneTool candidate is never executed by this build.

## Inputs and source-only evidence

Compiler and linker dependency tlogs supply the three TU/PCH include union and
the link/debug closure. Sound Seal C supplies existing expected hashes where
the path matches; it is not relabelled as a T7 seal. A further 27 small source
headers are separately pinned. Five unchanged E7 objects omitted by Sound's
replacement set were explicitly authorized for a targeted light hash on
2026-10-12: loadedsound.obj, loadedsound1.obj, loadedsound2.obj,
loadedsound3.obj and sound_bank.obj, totalling 9,881,624 bytes. Their separate
receipt is accepted only for those five paths. E7 EXE and PDB are explicitly
bound to the retained qualified receipt as preservation anchors.

MSVC is x64 14.44.35207; the SDK is 10.0.26100.0. PATH contains that MSVC bin,
that SDK's x64 bin and System32. rc.exe (55,640 bytes, SHA256
43da1503c262c30894c851589bf0155f8365d77e63a5f7bc13982320e3a6b42d) and
rcdll.dll (264,536 bytes, SHA256
9a11e4759adc48abe1fa9e3082ad7db4b53f4d6d77701c13729f4ffd47ae934c) are
new independent input pins, not members of historical Seal C. Compiler/link
environment overrides are cleared; INCLUDE/LIB are explicit and TEMP is private.
Windows/system DLL closure is not claimed hermetic; mt.exe usage is not proved.

During an admitted run, full expected inputs are guarded and verified before
execution and again after all jobs close. The generated sourceDependencies for
each compilation must be contained in the guarded input/binding set; an extra
include refuses acceptance. The plan is an expected dependency closure until
this actual compiler evidence exists, not a claim that T7 has been compiled.

Plan B remains preserved at `runtime/t7-build-plan-b/build-plan.local.json`,
SHA256 3ae75e8139c60f30b8ac37c55be731cef3297444cec752a8cce8850a173f6352,
but is superseded by the deadline correction below. Plan C is
`runtime/t7-build-plan-c/build-plan.local.json`, SHA256
422e79898fa2b16defc8193182fe146e2db5d73aeb4516c2bd2aaf87c409c4de.
Its default check passed with 1,073 expected input pins, no missing pins,
no native types, no lease and no candidate root. The 32 Python source/command
tests pass against the pinned tlogs; PowerShell parsing also passes. The five
new tests cover ordered 410-object reuse, PCH/precision separation, macro line
integrity and rejection of altered command contracts. The prior 27 source tests
cover catalogue/export rules. No native name-helper/three-TU/link result is
claimed here. The conversion owner confirms no exactly qualified 51-case helper
exists; the helper compile/probe stages therefore remain necessary.

For exact command tests, set both `IW7_T7_SOURCE` to the retained native checkout
and `IW7_T7_E7_BUILD` to its existing E7 build directory. The latter is explicit:
an integration checkout must reuse the original tlogs rather than assume they
exist under its own runtime directory or copy them there. Missing optional paths
skip that test class; supplied invalid paths or changed tlog hashes fail. This is
independent of the three source comparisons controlled by `IW7_T7_SOURCE` alone.

## Review correction: the 600-second boundary

The lifecycle reviewer reproduced two gaps in Plan B: provider loading could
cross 600 seconds before a stage started, and finalization at 599 seconds could
finish at 602 seconds while retaining Passed. The profile now applies the one
original group clock to H1's own stage checks as well as its polling budget.
The runner explicitly checks after LoadFrom/Add-Type and immediately before each
stage, and checks final cleanup, lease release, priority restoration and guard
release before assigning Passed. No second time window is started. Existing
five-second failure cleanup and quarantine are unchanged and still execute
after the group deadline.

A late receipt publication is also rejected: its attempt is retained under
`receipt.deadline-exceeded.json` and the canonical receipt records failure.
`Test-T7BuildDeadline.ps1` executes the real H1 stage function and the actual
runner finally block with an injected clock and fake finalization/receipt
functions. Three regressions pass: no owner creation/start at 600001 ms;
599000-to-602000 finalization still cleans up but cannot publish Passed; and a
late receipt cannot remain a canonical Passed result. These tests start no
native process, load no native provider and acquire no lease. They create only
tiny ignored receipt fixtures. Plan C has new source/provider bindings; neither
Plan A nor Plan B is authorized for execution.

Next: independent source/command/deadline review, then a coordinator GO for this
exact plan. First T7 engine boot/export remains a separate compatibility
experiment after the acquired dedicated EXE, PE/code windows, stock and original
job/restoration plan are bound. An official download hash alone cannot prove
compatibility with the retained fixed T7 addresses.

## Plan C attempt: compilation passes, link closure fails

The coordinator authorized one Plan C invocation on 2026-10-12. It ran in a
persistent PowerShell 7 host after fresh resource admission, using exactly the
4/6 GiB lease and reviewed source 86b49fc. The native name fixture produced the
exact 51-check marker with empty stderr. Helper, main, T7 zonetool and xpak each
finished with original root exit zero and fresh empty-job closure, respectively
in approximately 1.50, 3.54, 5.43 and 3.44 seconds. The three translation units
compiled under /W4 /WX; their actual include sets matched guarded inputs.

The final linker produced a 21,740,032-byte EXE and 136,466,432-byte PDB, but
original-job emptiness was not reached within its 120-second deadline. The
attempt is **Failed**, not a qualified candidate. Its create-only receipt is
`runtime/zt-t7-a/receipt.json`, SHA256
af6beecf7a8892e16266a7641d2799f665f86fa8ad7c40c61561b782534f7897.
The group elapsed approximately 140.077 seconds and output before receipt was
183,749,609 bytes. Final full input revalidation was not reached.

A live CIM observation during the wait showed a single VCTIP process whose
parent PID matched the registered original linker and whose creation followed
that linker. No cl/link process remained in that observation. This supports a
linker telemetry residue as the cause; original-job membership was not captured
by the Link profile and is not retroactively claimed. Source inspection confirms
H1 qualifies telemetry only for Stage=Compile, while Stage=Link waits for ordinary
empty-job closure. NativeJob.TreeExited requires root exit and zero active members.

Failure cleanup stopped only the original owned job and confirmed closure; the
retained original root exit code was zero. The receipt records lease released
and no quarantine. Fresh postflight at 11:43:41 UTC found no lease or build/
telemetry processes and unchanged owner Main process identity. The persistent
host saved its outcome, verified no AppDomain quarantine, then exited normally.
E7 EXE/PDB were guarded against writing throughout the attempt; their observed
size/mtime remained unchanged. No candidate or game was launched; no retry was
performed. The failed receipt and all artifacts remain separate evidence.

The helper EXE (1,032,192 bytes) is now observed at SHA256
c5989b285530d036caa105e9456400daeac859e44b008ad94a5a079e3faab1f6
with those exact 51 source cases. Reuse must bind its source/header/receipt
identity, rather than rerun a source-identical helper unnecessarily. The next
source-only change is a narrow Link telemetry policy adapter reusing H1's strict
identity, artifact, two-capture and original-job closure checks, with no deadline
increase. Any further native invocation requires a separately reviewed new plan
and coordinator GO; Plan C remains Failed.

## Link-only correction and Plan D2 preparation

Invoke-T7OwnedStage is a small adapter around the unchanged H1 controller. For
Link only, it supplies the pinned sibling link.exe identity (SHA256
a364af801a8539e4324d9489313dbf001d959128451fc99a27b24676bbac058f)
to the same strict compiler telemetry policy. The controller's internal Compile
branch is reused; the receipt retains the actual Link phase label even on error.
The policy factory override is function-local and cannot broaden the ordinary
cl.exe factory. VCTIP path/hash, exact root identity/exit zero, bound inputs,
all four linker artifacts, two matching original-job captures, parent/creation
checks and a fresh zero-member proof remain required. Unknown residuals still
fail. There is no new job owner, OS change or timeout increase.

The recovery plan executes only a fresh linker job. It reuses the exact three
compiled objects, their PDBs and dependency reports, plus the already observed
51-case helper proof. The prior Plan C SHA, its Failed-but-closed receipt and
seven byte-identical native source/header/fixture files must agree before reuse
is prepared. A changed native source, incomplete artifact set, nonzero compile
exit, missing closure, wrong probe count or quarantine refuses reuse. Full
expected inputs and reused artifact pins are guarded/rehashed under the new
lease, and actual prior compiler include sets are checked against that guarded
set again before link. No old Link result is promoted or relabelled.

The first D read-only check exposed PowerShell's one-element array unwrapping
in the stage-name count; it stopped before native providers or admission. That
plan remains preserved. The corrected plan is
`runtime/t7-build-plan-d2/build-plan.local.json`, SHA256
daa7097f872b83a5762b2cb56bf6dd5a235ed2beee8e0ff077276c61622d53fa.
Its default check passes with one Link stage, 1,086 expected input pins, zero
missing pins and no native types, lease, binary hashing or candidate root.
The new candidate root is `runtime/zt-t7-b`; the original C artifacts remain
under `runtime/zt-t7-a`. Link stays at 120 seconds, group at 600 seconds,
admission at 4/6 GiB and output at 256 MiB. E7 preservation anchors remain bound.

Validation: 37 Python source/recipe tests pass, including five reuse regressions;
three global-deadline regressions still pass. Ten synthetic Link tests exercise
the actual H1 telemetry functions through the adapter, verifying success only
after artifact/two-capture proof and rejecting root failure, wrong telemetry
path, wrong parent, absent job membership, changed generation, changed inputs,
changed artifacts and unpinned linker identity. The original cl policy remains
unchanged outside the adapter. All three retained dependency reports also pass
the new plan's source-only check. These tests perform no native execution or
reservation. Independent review and a new coordinator GO remain required.

## Plan D2 result: qualified link, candidate not executed

After favorable independent review and an explicit coordinator GO, exactly one
Link-only D2 invocation ran on 2026-10-12 with source
ba365d4ba100128094d7de821da95f1516516c88 and the plan SHA above. Fresh admission
followed the preceding workload's confirmed closure. The linker completed in
2.753 seconds; the complete guarded group took 13.791 seconds. The original
linker exited zero. H1 qualified the exact VCTIP child in two original-job
captures, stopped only that original job, and confirmed root exit zero with
zero active members afterward. No compile or helper fixture was rerun.

The create-only receipt is `runtime/zt-t7-b/receipt.json`, SHA256
c609bc56523654d8bca4b855024a463393185aab8e19ed4eae94c1ff8f6a09c2.
It records Passed, InputsReverified, TreeClosureConfirmed and LeaseReleased,
with Quarantined false. All 1,086 expected inputs, including the E7 preservation
anchors and reused C artifacts, passed final revalidation. Link output before
receipt was 158,225,555 bytes. Qualified outputs under `runtime/zt-t7-b/link`:

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| zonetool-t7.exe | 21,740,032 | 94dd29a9cb538504ddeb3545483e43a5dfea195aaca155db5bf147f1c6334c15 |
| zonetool-t7.pdb | 136,474,624 | b533dd414ebe395885f03dfddb4fb5c43fafdf8f51de33e5ec1b5b3afa1fd5c2 |
| zonetool-t7.lib | 6,744 | f922f8b672d7483ac5d4e056e45f3dcdfbda7db51a4f80451d478fbe512d453d |
| zonetool-t7.exp | 3,901 | b390095aaa172e81ca1cecd15c10b35c27faf08303157a478bb638ab574a9c8f |

Postflight at 12:08:53 UTC found zero leases, no compiler/linker/ZoneTool/telemetry
processes and unchanged owner Main identity. The persistent host verified the
receipt and absence of AppDomain quarantine, saved
`runtime/t7-build-plan-d2/host-outcome.local.json`, then exited normally. Its
absence was verified separately. The failed Plan C and frozen E7 artifacts
remain preserved; C is not relabelled as successful.

This qualifies the build only: CandidateExecuted and Ready remain false.
Neither the candidate nor the dedicated engine was launched. Fixed-address
engine compatibility, catalogue/export execution and owner gameplay remain
unproved. The next authorized work is source-only wiring of a separate bounded
pre-patch rendezvous probe before `component_loader::post_unpack`; any new
native build or runtime experiment requires its own reviewed plan and GO.

## Separate pre-patch diagnostic: source and plan only

`prepare_prepatch.py` is a narrow overlay of the already pinned main source.
It leaves the resident CLI patch and its historical source contract unchanged.
Its separate helper is owned by the executable-inspection workstream, commit
9ec33562964dcd8b3c2bd0bbbc12fe82bb63ceb7: `native_prepatch_probe.inc`, 16,290 bytes,
SHA256 83f7a6e2cbf3551105d2ea698d5e25f21dc3d6343e6ac21a8358fa693145dd67.
The helper is copied only into the tiny private prepared-source overlay;
the shared native tree and D2 artifacts are unchanged.

The explicit `-t7-prepatch-probe` invocation is validated before any engine
selection/load. It requires exactly two arguments including the executable,
the T7 dedicated file, T7 mode, and the helper's fresh bound output. The first
T7 SetProcessDPIAware stub calls capture and immediately passes its result to
the existing exit_hook/pre_destroy path, before post_unpack. The T7 ExitProcess
import instead refuses an engine exit before capture. Loader exceptions report
to stderr and return two before the ordinary modal path. Refused post_start/
post_load and an entrypoint return without capture also return two. Ordinary
engine modes retain their existing behavior; there is no alternate address
patch or fallback into the ordinary T7 boot after a diagnostic refusal.

This is a witness after imports, hooks and post_load have already been able to
act, not a side-effect-free load or an ABI proof. The helper captures metadata
and twelve bounded windows, then exits. Its complete-capture exit zero still
requires offline compatibility review. The separate runtime supervisor must
check the report identity, phase and completeness, not merely the exit code.

The new optional `--prepatch-helper` build mode requires retained compilation
proof. It recompiles only main and then links, reusing C's unchanged zonetool11/
xpak objects, PDBs, dependency reports and exact 51-case helper proof. Every
other native source/header must remain byte-identical; the main must differ.
Both reused dependency reports (637 and 560 includes) are covered by the new
guarded set and will be checked again during an admitted build. D2 is not used
as an instrumented candidate and C's failed group status is preserved.

Plan and native receipt carry BuildProfile `t7-prepatch-probe`, exact option,
argument count and report name, plus Helper/Wiring/PreparedMain pins that must
match guarded text bindings. A main rebuild without that profile, or a profile
without the main rebuild, is refused. The runtime launcher can consequently
reject a non-instrumented D2 receipt instead of guessing from an EXE filename.

The prepared plan is `runtime/t7-prepatch-build-plan-a/build-plan.local.json`,
SHA256 63982a61209d68ae693fb1bbc6b59545618f60875f86b237e404bdb21dfe3074.
Its source/metadata-only check passes: two stages, 1,083 expected inputs, no
missing pins, no native types, no binary input hashing, no lease or candidate
root. The future output is `runtime/zt-t7-prepatch-a/link/zonetool-t7.exe`;
there is currently no EXE or build receipt at that root. Admission remains
4/6 GiB, each stage 120 seconds, group 600 seconds and output 256 MiB.

Validation: 46 Python source/recipe regressions, eleven actual runner profile
validator cases, three deadline cases and ten Link telemetry cases pass without
native execution. IW7_T7_E7_BUILD remains supported for retained-build tests.
The helper's own ten source tests are separate evidence, not a native result.
Next: independent review of this exact source and plan, coordinator admission
and explicit build GO. A future runtime probe remains a separate authorization.

## Diagnostic Plan A attempt: include failure, closed without retry

After favorable independent review, the coordinator authorized exactly one
invocation of the diagnostic plan above, source 4bc568c5f13f582baf80f2285e3f807f798df933
and helper 9ec3356. Fresh admission at 12:27:07 UTC found no concurrent build or
lease, sufficient 4/6 GiB headroom and unchanged Main identity. Main compilation
failed with original compiler exit two: helper line 15 requested
`<nlohmann/json.hpp>`, which the pinned native include paths do not provide
(MSVC fatal C1083). The retained native std_include.hpp instead includes
`<json.hpp>` and already declares nlohmann json/ordered_json aliases.

The Link stage was never reached and no candidate EXE was created. The original
job controller correctly refused telemetry qualification for the nonzero
compiler exit; its surfaced error, "Successful original compiler handle identity
required", is not a replacement for the C1083 compiler diagnostic. Failed-run
cleanup confirmed original-job closure, released the lease and recorded no
quarantine. Full final input revalidation was not reached. The group elapsed
7.513 seconds. Receipt `runtime/zt-t7-prepatch-a/receipt.json` has SHA256
df3384100270520efc24653f97b49891165c43c7cf0c125eba4cc0fb1a81ea66.

Postflight at 12:28:43 UTC found zero leases/build processes and unchanged Main.
The persistent host confirmed the exact failed receipt and absence of AppDomain
quarantine, saved its outcome, then exited; its absence was independently checked.
The plan, prepared source, partial compiler output and failed receipt remain
preserved. No second invocation or candidate execution occurred. The helper
owner was notified for a source-only include correction; a new plan and review/GO
are required before any further build. Qualified D2 remains separate and intact.

## Diagnostic Plan B preparation: one-line include correction

Helper commit d1858afa1b665eee05322bcf3316dae58d969873 changes only the include
to `<json.hpp>`, matching the native tree's existing dependency. Its 16,281-byte
SHA256 is a9f458d2783c845af6958c896bda07fa4b92a5ea23a14c9e5d1201fe234a2018.
No download, include-path expansion or feature change is required.
Plan `runtime/t7-prepatch-build-plan-b/build-plan.local.json`, SHA256
c9e664bb4dbf2b7e3c38c05a9952ef9d809e326cef7ae864209073ecaf61acd6, passes
the default source/metadata check with the same 1,083 expected inputs and
main/Link stages. Its entire expected input array is identical to A; wiring,
prepared main and budgets are also unchanged. The corrected helper and fresh
private paths are rebound in the text bindings. The candidate root
`runtime/zt-t7-prepatch-b` remains absent. A and its failed evidence are preserved.
This is preparation only; targeted review, fresh admission and a new coordinator
GO remain required before the single proposed invocation.

## Diagnostic Plan B result: instrumented build qualified, no runtime probe

Following independent delta review and a new explicit coordinator GO, one B
invocation ran on 2026-10-12. Fresh admission at 12:37:39 UTC found no competing
lease/build and unchanged Main identity. Main compiled under /W4 /WX in 5.001
seconds and Link completed in 2.825 seconds. Each original root exited zero;
the retained H1 policy qualified telemetry, closed its original job and observed
zero active members afterward. Total group time was 20.969 seconds. The reused
two translation units and 51-case name helper were not rebuilt or rerun.

Receipt `runtime/zt-t7-prepatch-b/receipt.json`, SHA256
a72aceb8828fe5afde79f53d8ab0c4beef711674500e5144997039580a2805d4, records
Passed, InputsReverified, TreeClosureConfirmed and LeaseReleased, with no
quarantine. The expected inputs and source bindings passed full postvalidation;
the new actual compiler dependency report passed the guarded-set check. The
receipt carries the reviewed BuildProfile and its exact Helper/Wiring/PreparedMain
pins. Output before receipt was 164,022,183 bytes. Qualified files under
`runtime/zt-t7-prepatch-b/link`:

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| zonetool-t7.exe | 21,776,384 | 6e304990711282a696a4096ed9482d1430ce2783d67f5bc4983235d18e333526 |
| zonetool-t7.pdb | 136,998,912 | 102b027f6ec37e3ea5d2e81bbc6f812c11afad85aea40caae5f08feddbf215c2 |
| zonetool-t7.lib | 6,744 | f922f8b672d7483ac5d4e056e45f3dcdfbda7db51a4f80451d478fbe512d453d |
| zonetool-t7.exp | 3,919 | e30af1a45c774a703ba2713c758ae422a9aae861d7e29da4830a845c59f616df |

Postflight at 12:39:21 UTC found zero leases/build/telemetry processes and
unchanged Main identity. The persistent host verified the exact receipt and
absence of AppDomain quarantine, saved its outcome, then exited; its absence
was verified separately. Failed A/C and qualified D2 remain preserved.

CandidateExecuted and Ready remain false: neither this candidate nor the engine
was launched. The qualified receipt, EXE pin and BuildProfile were handed to the
existing diagnostic-launcher workstream for source/metadata preparation only.
Its separate reviewed launch plan and coordinator GO must precede any runtime
capture. Compilation proves neither reaching SetProcessDPIAware nor fixed-address
compatibility, successful catalogue/export, or owner gameplay acceptance.

## Catalogue trace: observe the ordinary command without changing dispatch

The real catalogue B run used ordinary D2 and naturally returned zero in 2.180
seconds, with only the initial ZoneTool message and no catalogue. That message is
emitted from component post_unpack before the original engine initialization call.
The logger uses printf without fflush, so missing later lines alone cannot locate
the exit. Source review found no argv/define mismatch and no explicit successful
exit in the interval. A missing bootstrap file or wrong patch offset is not proven.
Catalogue A/B failures and the earlier pre-patch experiments remain historical.

The coordinator authorized a minimal observation during the **same** command,
`-t7-iw7-catalog mp_freerun_04`. `prepare_catalog_trace.py` overlays only the
ordinary prepared main. At the first main statement it checks the actual wide
command line for exactly three arguments, the exact catalogue option and a
nonempty zone argument. It does not alter argv, cache flags, add a command mode,
validate the zone differently, or replace any loader, patch or dispatch behavior.
For this invocation it calls setvbuf on stdout and stderr before engine work and
reports whether each call succeeded. It emits flushed stderr observations around
T7 post_unpack, before entry_point, after its return with the original result,
and at exit_hook with the original code, current TID and caller return address
before pre_destroy. _ReturnAddress is captured at the hook itself. Other phases
carry a null address and zero code except entry_point_return, which carries the
original result. The original cleanup and exit/return remain unchanged.

Each of six fixed events has an InterlockedOr bit; repeated calls cannot flood
the trace. No raw command line, asset name or memory contents are logged. Each
line is under 256 bytes; all trace output is under 1,536 bytes. The exact formats
(fprintf LF, possibly translated to CRLF by Windows) are:

```text
[T7_CATALOG_TRACE] schema=iw7.t7-catalog-trace/1 phase=enabled stdout_unbuffered=%d stderr_unbuffered=%d tid=%lu
[T7_CATALOG_TRACE] schema=iw7.t7-catalog-trace/1 phase=%s code=%d tid=%lu return_address=%p
```

The second format allows only before_post_unpack, after_post_unpack,
before_entry_point, entry_point_return and exit_hook. Buffering indicators are
0/1, code is signed int32, TID is unsigned DWORD, and address uses the pinned
MSVC x64 %p representation. Markers prove only that their sites were reached;
they do not establish engine readiness, successful catalogue or export.

The explicit build profile is `t7-catalog-trace`, Option `-t7-iw7-catalog`,
ArgumentCount 3, TraceSchema `iw7.t7-catalog-trace/1`. It binds exactly Wiring,
PreparedMain, BaseBuildPlan and BaseBuildReceipt text pins (Path/Bytes/SHA256),
with no Helper or Report. The base is ordinary D2 plan daa7097f872b83a5762b2cb56bf6dd5a235ed2beee8e0ff077276c61622d53fa
and Passed receipt c609bc56523654d8bca4b855024a463393185aab8e19ed4eae94c1ff8f6a09c2.
Preparation explicitly compares D2's compile-reuse chain with C, all seven
uninstrumented native payloads in both prepared-source bindings, and all retained
helper/object artifact pins. Only then is main overlaid. No binary is read by
this comparison. The old source/receipt identities are not reused for a new EXE.

The existing build runner accepts this named profile and pre-patch as separate
variants. Unknown or mixed profiles are refused. ReuseCompile.RecompiledMain is
true, its exact retained dependency roots are zonetool11 and xpak, and the two
new stages are main Compile then Link. The qualified helper's 51 native checks
remain historical. The common H1 providers, scheduler, telemetry policy and
4/6 GiB, 120-second stage, 600-second group, 256 MiB output limits are unchanged.
The new receipt must copy the exact BuildProfile and report its own plan hash,
both original roots exiting zero and closed, Passed, InputsReverified and
LeaseReleased with no quarantine. Catalogue launcher qualification belongs to
the existing T7 acquisition chat and must bind this new evidence.

Source tests recover the exact original main after removing only observations,
check the order of trace/cleanup/return, enforce the bounded existing command,
and reject changed ordinary source, proof chains, retained artifact pins and
mixed payloads. PowerShell tests execute the runner's actual profile validator
without providers. A plan and independent review precede any native build GO;
no build, engine launch, lease or binary hash is authorized by preparation alone.

Local source validation on 2026-10-12 passes 58 Python tests against the retained
native source and explicit E7 path, plus 37 PowerShell checks (24 profile,
3 deadline, 10 Link telemetry). The deadline/telemetry fixtures use the existing
providers with synthetic native observations: no native types, children or lease.

### Exact catalogue trace build plan A, awaiting review/GO

Source commit 6c9b781d45a24747a66c24a6d803478b77215f6a produced
`runtime/t7-catalog-trace-build-plan-a/build-plan.local.json`, SHA256
0a6af99207b0b35bdf689a7378af3e1760bfd06e2da870fc1e1c9e5164462d31.
Default-check passes with 1,083 expected inputs and no missing pins. Wiring is
5,485 bytes / 247f4ed5f2734ddf0f36dcaf7d9ffe548e4a53c8977440d9306aeb419a039b56;
prepared main is 14,426 bytes / 6d06778290f1d8befb3184cc7ff7de7f82d7acb02ebef9f72e0a91cdf2056bb1.
The D2 base plan/receipt text pins are 296,330/7,136 bytes respectively, with
the unchanged hashes above. Comparing all 413 object references in both Link
response files finds exactly one changed row, line 22: the fresh main.obj.
The other 412 paths are identical. intrin.h, cwchar and cstdio already belong to
the expected input set; this requires no toolchain copy or dependency download.

The future output root `runtime/zt-t7-catalog-trace-a` remains absent. This
preparation loaded no native type, acquired no lease and hashed no binary.
No new EXE, dependencies.json, Passed build receipt or catalogue exists yet.
The coordinator and catalogue launcher owner received this exact plan and its
source pins for independent review and later qualification. A new build receipt
and explicit runtime plan/GO remain separate requirements.

### Catalogue trace build A: Passed, closed, candidate not executed

After favorable independent review and an explicit single-run coordinator GO,
the exact plan above ran once on 2026-10-12. Preflight at 13:57:48 UTC recorded
sufficient 4/6 GiB capacity, zero competing leases/builds and unchanged Main
PID 27784 and Python PID 23352 identities. The retained PowerShell host PID 7980
invoked the existing runner without any new supervisor or provider changes.

Main compiled under /W4 /WX in 3.517 seconds; Link completed in 2.693 seconds.
Original roots cl PID 9196 and link PID 5512 each exited zero. The existing H1
policy qualified each exact telemetry child and its parent relationship, then
closed the retained job; both after-stop observations report zero active members.
Total group elapsed time was 16.974 seconds, with maximum observed output
188,513,840 bytes, within the unchanged 256 MiB limit. Actual main dependencies
passed the guarded-set check; Data.Source identifies the reviewed PreparedMain
(Windows path case normalized to lowercase by MSVC). Both stages' artifacts
passed comparison across telemetry cleanup and final input revalidation.

Receipt `runtime/zt-t7-catalog-trace-a/receipt.json`, SHA256
6a886fd9befa29b35ef220efa4cfb011a45cd0fd30bdcaff8a9b3374d0df73b3,
records Passed, InputsReverified, TreeClosureConfirmed and LeaseReleased, with
no quarantine. It carries the exact catalogue-trace BuildProfile and its four
source/base-proof pins. These are the new artifacts under that run root:

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| main/main.obj | 521,953 | 6423dff9e3ba14d920a8a04b49740b6c313fe815f6e082eb6616f15ecd75d195 |
| main/compile.pdb | 1,724,416 | a5be4ee5c012fbec7663af444e0b74b594509c28e5bcf917426e5d830bfefdad |
| main/dependencies.json | 61,948 | 11e21fcb1430dc6ae4dd08bd4eb1313256b2f399835af114c13391853d441cd4 |
| link/zonetool-t7.exe | 21,741,056 | 1034faa2f198f3edc367e6f5d6c24059bddb6962f9950a347400e6108f3b60b0 |
| link/zonetool-t7.pdb | 136,474,624 | 5ef1dca35b70e2c04093f248bc839e484b395805b1ec9657180e1277d75949a0 |
| link/zonetool-t7.lib | 6,744 | f922f8b672d7483ac5d4e056e45f3dcdfbda7db51a4f80451d478fbe512d453d |
| link/zonetool-t7.exp | 3,929 | 29f525675fc321d1b9bed53ed3f857fca14761bbad3821811bdb9b77578dbd3c |

Postflight at 13:59:33 UTC confirmed zero leases and build/telemetry processes,
plus unchanged Main and Python identities. The retained host verified the exact
Passed receipt and absence of its AppDomain quarantine, saved its outcome and
exited zero. Independent observation at 14:00:08 UTC confirmed PID 7980 absent.
Preflight, postflight, host-outcome and host-exit evidence is retained under
`runtime/t7-catalog-trace-build-plan-a`. The coordinator and catalogue runner
owner received the new pins and closure proof; no D2 receipt is substituted for
this build. All previous failed and successful candidates remain preserved.

CandidateExecuted and Ready remain false. This build did not run the EXE or
engine, observe any trace marker, produce a catalogue, or validate export or
gameplay. The next action belongs to the catalogue runner owner: qualify these
new artifacts, prepare a real catalogue plan and obtain its separate runtime GO.

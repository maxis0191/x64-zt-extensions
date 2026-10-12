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

## Loaded exit context: source preparation after catalogue D

The catalogue owner's D evidence records five /1 markers: buffering enabled and
entry_point/post_unpack entered on TID 31804, post_unpack returned, then exit_hook
received code zero on TID 18184 with return address 0x140AC00C4. There was no
entry_point_return and no catalogue. The original job exited naturally and closed;
the run receipt is f518bf36f08eeb01f9d89ead6f8d0f5b79fe48501864e0cb93801652f7b9e3b4.
This establishes an exit from another thread, not its cause. Source review found
no name for this RVA or matching saved byte window. Console/scheduler sources do
not explicitly request ExitProcess; attributing the exit to anti-tamper, the CRT,
or missing files would be speculation. The packed disk image was not reread.

The coordinator authorized a source-only extension at the existing exit_hook.
`wire_main` and its six /1 markers are preserved exactly; an identity test matches
the previously built 14,426-byte main. `wire_exit_main` adds context without
changing arguments, dispatch, engine patches, exit code or cleanup. The build
selector `--catalog-exit` is mutually exclusive with `--catalog-trace` and the
pre-patch build variant. It is not a new runtime argument or command mode.

The distinct BuildProfile Name is `t7-catalog-exit-context`, retaining Option
`-t7-iw7-catalog`, ArgumentCount 3 and TraceSchema `iw7.t7-catalog-trace/1`, plus
ContextSchema `iw7.t7-catalog-exit-context/1`. Its same four text pins are Wiring,
PreparedMain, BaseBuildPlan and BaseBuildReceipt. The base remains ordinary D2,
with the exact same checked C compilation chain and two retained dependency roots;
main Compile and Link must produce their own new Passed receipt and EXE. The /1
candidate, its receipt and catalogue failures remain separate historical evidence.

A single InterlockedOr selection owns the exit marker **and** its three context
lines. Only the selected invocation calls the generic /1 exit marker, then captures
code/TID/RA locally. Other exit invocations proceed directly to the original
cleanup/exit without waiting for the capture. Concurrent termination can therefore
leave partial output, which must not be treated as a complete observation.

The selected thread attempts these three independently SEH-guarded observations:

- Memory: 256 bytes at RA minus 0x40. The named existing T7 module must have base
  0x140000000, allocation must match, and the entire window must fit one committed
  region without guard/no-access protection. VirtualQuery metadata is recorded;
  ReadProcessMemory uses the current process only. Partial bytes remain labeled.
- Stack: RtlCaptureStackBackTrace requests at most eight addresses from the current
  thread. This is a best-effort runtime stack observation, not validated unwind/ABI.
- Function: RtlLookupFunctionEntry is called only for RA minus one, after checking
  that address's allocation. If present, its image base must match T7 and only the
  accessible 12-byte RUNTIME_FUNCTION is copied. Begin/End must contain RA minus
  one for status ok; UnwindData is recorded as metadata, never dereferenced.

Each observation is serialized and flushed before attempting the next, retaining
the window if stack walking fails or the process exits concurrently. All three
errors are non-fatal to this instrumentation; original pre_destroy/exit follows.
The observer restores the calling thread's saved LastError. Fixed local buffers
are clamped again after guarded calls, before serialization. No file read/write,
process attachment, worker hook, engine offset patch or new supervisor is added.

Context prefix is `[T7_CATALOG_EXIT] schema=iw7.t7-catalog-exit-context/1`.
Each of memory, stack and function occurs at most once, following the /1 exit_hook
marker with matching signed int32 code, DWORD TID and pointer RA. Exact formats
are the three fprintf literals in prepare_catalog_trace.py, shared with the
catalogue parser owner. Integers are decimal except pointer hex16 and function
RVAs hex8; data is uppercase hex (two characters per copied byte), stack addresses
are uppercase hex16 separated by commas, and an empty data/list is `-`.
Each fprintf LF may become CRLF under Windows text mode.

Memory is at most 1,024 bytes per line, stack and function 512 each, and the six
unchanged markers 256 each. The entire stderr contract is at most 4 KiB/nine lines.
Raw captured bytes belong only to ignored runtime stderr/receipts; committed
evidence must retain metadata, states and pins without byte windows.

Memory status ok requires 256 copied bytes, partial 1..255. read_failed has zero
bytes, or a full count if the API anomalously reports failure despite that count.
Exception retains bounded metadata/bytes already obtained. Function partial has
1..11 copied bytes, read_failed zero or 12, and both have zeroed RVA fields.
Function exception also zeroes RVAs; record_invalid can preserve a full record
that fails containment. Early refusals have zero bytes and zero RVAs. Stack ok
has 1..8 frames; empty/invalid_count/exception have none. API/SEH errors are
explicit. Absent or incomplete contexts are not success; even three ok records
prove neither the cause of ExitProcess nor a successful catalogue.

Source tests verify unchanged /1 output/control flow, single-invocation ownership,
per-API SEH guards, allocation/read/array bounds, incremental publication, original
exit/LastError preservation and actual maximum-width fprintf sizes. The runner's
profile tests keep /1 strict and refuse unknown/mixed context schemas. These are
source/synthetic tests only; C++ compilation and actual capture behavior remain
unverified pending independent review and separate build/runtime GO decisions.

Local validation on 2026-10-12 passes 68 Python tests using the pinned retained
native source/E7 command records and 45 PowerShell checks (32 profile, 3 deadline,
10 Link telemetry). The current SDK header confirms the declared lookup API;
no dependency, compiler option or common provider changed. These checks loaded
no native diagnostic type, launched no child and acquired no heavy lease.

### Exact exit-context build plan A, awaiting review/GO

Source commit 55dde1dd60ff925efa9326312deb12b0f6c2e56b produced
`runtime/t7-exit-context-build-plan-a/build-plan.local.json` (298,652 bytes),
SHA256 0cd2c2f3bdc22021a045d53bec19988b912c8d3db095e02eef061ebfa201880b.
Its default source/metadata check passes with 1,083 inputs and no missing pin.
The entire Inputs array equals the trace A array. Its 413-object Link response
differs from trace A on exactly line 22, the newly compiled main.obj; the other
412 references are identical. No dependency or common provider was added.

Wiring is 13,796 bytes / 4f86d6c5189a26978827d97ce86c022a1978437555dcfa579554a3039f5c209b;
prepared main is 22,194 bytes / 5f64c43ca9306cfa0ee561fbe94592a4f0cedcc9382456d11772653695c3fae3.
The two D2 base-proof pins and the retained C compilation chain are unchanged.
The future `runtime/zt-t7-exit-context-a` output root is absent. This preparation
loaded no native diagnostic type, hashed no binary and acquired no lease. It
created neither an EXE nor a Passed build receipt. The coordinator and catalogue
parser owner received this exact source/plan for review; the build still needs
its own GO, and any later real catalogue run requires a separate reviewed plan.

### Exit-context build A: Passed and fully closed, no candidate launch

Independent review accepted source 55dde1d and the exact plan above. After the
image fixture released the shared slot, the coordinator authorized one build.
Fresh preflight at 14:56:52 UTC on 2026-10-12 found sufficient 4/6 GiB capacity,
zero leases/builds, Main still stopped and the exact Python PID 23352 generation
unchanged. The new persistent PowerShell host PID 21776 invoked the existing
runner once; no retry or alternative compiler/link route was used.

Main compiled under /W4 /WX in 3.334 seconds and Link completed in 2.948 seconds.
Original roots cl PID 20668 and link PID 24764 both exited zero. The qualified H1
telemetry policy closed both jobs and recorded zero active members afterward.
Actual source dependencies passed the guarded-set check; Data.Source identifies
the reviewed PreparedMain, with Windows path case normalized by MSVC. Final
source/input revalidation passed. Total group elapsed time was 16.595 seconds;
maximum observed output was 167,935,441 bytes, below the unchanged 256 MiB cap.

Receipt `runtime/zt-t7-exit-context-a/receipt.json` is 14,488 bytes, SHA256
3366373d1cf91e30634bfb3367133bee99771ca2b2cb9c794c7ced784cc9f6b0.
It records Passed, InputsReverified, TreeClosureConfirmed and LeaseReleased,
with no quarantine. Its BuildProfile is exactly equal to the reviewed plan's
profile, including ContextSchema and all four text pins. New artifacts under
`runtime/zt-t7-exit-context-a` are:

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| main/main.obj | 538,558 | 179d7ee84d84fdcc83c00587775aeea0914e34fea141ec673c3c83b279b08f67 |
| main/compile.pdb | 1,732,608 | 05867f326e0e34abac9de0ea1faf5c3ce988283f37554435bf6abd6457e9b67b |
| main/dependencies.json | 61,947 | 82ebe404731828932c65e6752c4365f465365596d44d6685e93309645507f414 |
| link/zonetool-t7.exe | 21,744,640 | f3408671d392b97e3ca09bc3e6e294c761813feccd18d8a1aaa4920874be2847 |
| link/zonetool-t7.pdb | 136,482,816 | cfc51daed1e5ca49379e413949bd88362c36f3239c188868f26847d464729854 |
| link/zonetool-t7.lib | 6,744 | f922f8b672d7483ac5d4e056e45f3dcdfbda7db51a4f80451d478fbe512d453d |
| link/zonetool-t7.exp | 3,927 | 6c93e70042f25bc473a38799d73d0e9740756c76861e24f66ccf81d5696ce9fc |

Postflight at 14:58:26 UTC found zero leases/build/telemetry processes, Main still
stopped and Python's exact identity preserved. The retained host verified the
exact Passed receipt and absence of AppDomain quarantine, saved its outcome and
exited zero. Independent observation at 14:58:52.3190650 UTC confirmed PID 21776
absent. All four pre/postflight and host outcome/exit records remain in
`runtime/t7-exit-context-build-plan-a`. The coordinator and catalogue owner received
these new pins and complete closure proof for the separately reviewed Plan E.

CandidateExecuted and Ready remain false. Compilation validates the new C++/SEH
syntax and linkage, not actual memory/stack capture behavior, the cause of the
engine exit, catalogue generation or gameplay. No candidate or engine was
launched by this build. The separate runtime parser correction does not change
this qualified build; future runtime acceptance must bind its own reviewed plan.

### E caller diagnostic: source-only preparation

Runtime E captured ExitProcess with return address 0x140AC00C4 after post_unpack,
but no catalogue. The subsequent INT3 is not evidence of execution or anti-debug
failure. The retained source has no exact symbol for the three engine callers.
No exit suppression, bootstrap fix, renamed function or offset correction is
justified by this evidence. The coordinator authorized a finite main-only source
diagnostic on 2026-10-12; build and runtime each require a separate GO.

The preparation selector `--catalog-callers` is exclusive with the pre-patch,
trace and exit-context selectors. Runtime argv remains `-t7-iw7-catalog <zone>`.
BuildProfile has exactly ten fields: Name `t7-catalog-callers`, Option,
ArgumentCount 3, TraceSchema `iw7.t7-catalog-trace/1`, ContextSchema
`iw7.t7-catalog-exit-context/1`, CallerSchema `iw7.t7-catalog-callers/1`, plus
Wiring, PreparedMain, BaseBuildPlan and BaseBuildReceipt. The four text pins,
ordinary D2 proof and retained C compilation chain follow the existing profile.
Only main is recompiled; Link reuses the other 412 object references. No provider,
native supervisor, command, stock or shared source tree changes.

The trace /1 and exit-context /1 generators retain their exact previously built
identities. The new overlay adds a cstring include (already in the sealed input
set), a POD-only guarded reader and a finite emitter. The existing bit-64 first
winner, code, TID, exit RA, eight-frame stack and original LastError restoration
are reused. After all three EXIT records, before original cleanup/exit, exactly
three CALLER records are independently captured and immediately flushed:

| Index | Fixed target return address |
| --- | --- |
| 0 | 0x140584FD8 |
| 1 | 0x1401DA015 |
| 2 | 0x140526D02 |

Each target must occur in the already captured current-thread stack. `frame` is
the zero-based first matching index; unavailable stack or absent target emits an
explicit refusal with frame -1 and no lookup/read. The named module must be at
0x140000000. RA-1 must lie in its readable committed allocation. Lookup uses
RA-1, requires the same image base, and copies only the 12-byte RUNTIME_FUNCTION
from a readable region in the same allocation. Begin <= RA-1 < End is mandatory.
UnwindData remains metadata and is never dereferenced.

If the entire function fits in 512 bytes and the RA-1 region contains it, capture
the whole function. Otherwise intersect [RA-448, RA+64), [Begin, End), and the
readable region containing RA-1. The intersection must contain RA-1 and have
length 1..512. `scope=full` means the requested window covers the entire function;
`window` means a bounded subset. Scope alone does not imply that the read passed.
No region is traversed and no image/stack scan or additional stack capture occurs.
The three new records read at most 1,536 code bytes and 36 record bytes in total,
in addition to the unchanged EXIT /1 observations.

The exact wire format is the single fprintf literal in CALLERS_SUPPORT. Fields
in order are schema, code, tid, exit_ra, index, ra, status, frame, module, image,
record, record_read, begin, end, unwind, start, requested, read, scope, allocation,
region, region_size, state, protect, type, error, data. Prefix is
`[T7_CATALOG_CALLER]`; pointers are uppercase hex16, RVAs uppercase hex8, other
numbers decimal, and data uppercase hex2*read or `-`. LF may become CRLF.

Statuses are ok, absent, stack_unavailable, module_missing, module_mismatch,
query_failed, region_invalid, not_found, record_partial, record_read_failed,
record_invalid, partial, read_failed, exception. Zero-initialized metadata can
remain populated up to the failed operation. Before code selection, start,
requested and read are zero and scope is none. Record partial has 1..11 bytes;
record_read_failed has zero or 12; both clear all RVAs. record_invalid can retain
a complete non-containing record. region_invalid after lookup can retain a valid
record. The record's query region is checked internally but is not emitted.

Code ok requires read=requested, partial requires 0<read<requested, and a failed
RPM can report read_failed with zero or requested bytes. Exception zeroes RVAs
while preserving any other bounded metadata/code already obtained. A separate
serialization clamp also protects partial SEH outcomes: requested>512 or
read>requested resets start/requested/read to zero and scope to none, with
read_failed/error=ERROR_INVALID_DATA (13). An overlarge record count is reset to
zero with zero RVAs and record_invalid. Errors in one target do not suppress the
next target. The original cleanup and process exit remain unchanged.

The maximum-width test evaluates the actual fprintf formats, including CRLF,
maximum signed code/DWORD/SIZE_T values, longest states and 512 code bytes per
caller. It bounds each CALLER line at 1,546 bytes and all 12 possible lines
(six TRACE, three EXIT, three CALLER) at 6,911 bytes, within the 8,192-byte stderr
contract. Raw bytes stay in ignored runtime evidence; committed evidence retains
only metadata, statuses and pins. Observed capture never implies a catalogue.

Source validation passes 77 Python tests with the retained source and E7 command
records, plus 53 PowerShell checks (40 profile, 3 deadline, 10 Link telemetry).
The initial test invocations lacked the retained E7 environment/provider
arguments; the complete invocations above passed after those were supplied.
No native diagnostic type, build child or lease was created. These source and
synthetic tests do not establish C++ compilation or actual caller capture.

### Exact caller build plan A, awaiting review and coordinated GO

Source commit 39933eb35f85c0267a75138330ecf9da81a90ed4 produced
`runtime/t7-callers-build-plan-a/build-plan.local.json` (298,615 bytes), SHA256
455b67c2862105ce5670f9cb2fefb26ba8e86f0167481ae7a1d8cc7f1a1e1b20.
The default runner source/metadata check passes with 1,083 inputs and zero
missing pins. The initial invocation supplied forward slashes in PlanPath and
was refused by the existing canonical-path guard; resolving that same path
passed without changing the plan or runner. No native action occurred.

| Text binding | Bytes | SHA256 |
| --- | ---: | --- |
| Wiring | 21,022 | 04f8ef6d2b27ca6168bf4571e5e1495d2ad4c65731597c3f5512c0cf200e7b1e |
| PreparedMain | 28,832 | af47dee318d9390f26c326d2e8ddd734e41bdc6db81b2b240e82c653cf7d2aa4 |
| Ordinary D2 plan | 296,330 | daa7097f872b83a5762b2cb56bf6dd5a235ed2beee8e0ff077276c61622d53fa |
| Ordinary D2 receipt | 7,136 | c609bc56523654d8bca4b855024a463393185aab8e19ed4eae94c1ff8f6a09c2 |

The Inputs array equals exit-context plan A exactly. Of 413 Link object paths,
only the 21st object (main.obj, response-file line 22) changes; 412 references
remain identical. Stages are main and Link, with the retained C helper/T7/xpak
proof. Budgets remain 4/6 GiB, 120 seconds per stage, 600 seconds per group and
256 MiB output. The future `runtime/zt-t7-callers-a` root is absent.

NativeTypesLoaded, BinaryInputsHashed, LeaseAcquired and RunRootCreated are all
false in the default check. Preparation creates no EXE, PDB or Passed build
receipt. No candidate/engine was launched. Source and exact plan were sent to
the coordinator and runtime parser owner; Sound F currently owns the heavy slot.
Review and a separate coordinator build GO are the next actions. A later real
catalogue invocation must bind the actual resulting artifacts in its own plan.

### Caller build A: Passed and fully closed, candidate unexecuted

Independent review accepted source 39933eb and the exact plan above without
P1/P2 findings. After Sound F fully closed, the coordinator authorized one build.
Fresh preflight at 15:34:20.4447517 UTC on 2026-10-12 admitted the unchanged
4/6 GiB estimates, with zero leases/heavy processes, Main stopped and the exact
Python PID 23352 generation preserved. A fresh persistent PowerShell host PID
18716, created at 15:34:26.0478570 UTC, made the single invocation. Its outer
process was PID 29752. Run returned without error at 15:35:13.5393776 UTC.

Main compiled under /W4 /WX in 3.250 seconds, and Link completed in 2.631 seconds.
Original roots cl PID 3484 and link PID 16372 both exited zero. The existing H1
policy verified each root's exit and exact VCTIP residual, then closed each job
with zero active members. Artefact hashes were stable across closure. Native
source dependencies identify the reviewed PreparedMain (case normalized by
MSVC). Final input revalidation passed. The group took 15.931 seconds and
observed at most 160,584,166 output bytes, below the unchanged 256 MiB cap.

Receipt `runtime/zt-t7-callers-a/receipt.json` is 14,453 bytes, SHA256
9f8b8bc235bd52429a915bb1f1d3fc3ca0afd6b852e8897dfc312d566166aa99.
It records Passed, InputsReverified, TreeClosureConfirmed and LeaseReleased,
Quarantined false and the exact reviewed ten-field BuildProfile. New artefacts
under `runtime/zt-t7-callers-a` are:

| Artefact | Bytes | SHA256 |
| --- | ---: | --- |
| main/main.obj | 548,659 | c02b70285028b0a7525b8761487ad5153fb2acefae543c1d930d5380e31ad434 |
| main/compile.pdb | 1,732,608 | 2969e7be44e123245eef655f488603c132c55f04035dbe1803c8141ecdb22dd2 |
| main/dependencies.json | 61,942 | 3222d5ee5df6d6779ab928324151357098741421809e10e148c48984f423ada5 |
| link/zonetool-t7.exe | 21,747,200 | 01aa3310e92a1e458005de044c582c302c12149a81bf7fce23b7cc5ae153bbd4 |
| link/zonetool-t7.pdb | 136,482,816 | e070475db1bd239fb4f7692c63948d8d7c0898a969069157fc96384c783140c9 |
| link/zonetool-t7.lib | 6,744 | f922f8b672d7483ac5d4e056e45f3dcdfbda7db51a4f80451d478fbe512d453d |
| link/zonetool-t7.exp | 3,917 | 937c3f08a1dd29100f63bdf6926e2c370da9a74883ca54a62e2ba834bf3a2d9c |

Postflight at 15:35:50.5608723 UTC found zero leases/build/telemetry processes,
Main still stopped and Python's exact identity unchanged. The retained host
verified the exact receipt and absence of AppDomain quarantine, saved its
outcome and exited zero. Session 15400 closed. Independent observation at
15:36:30.9704126 UTC confirmed host 18716, outer 29752, both tool roots and both
VCTIP residuals absent. All four pre/postflight and host outcome/exit records
remain under `runtime/t7-callers-build-plan-a`.

The coordinator and runtime parser owner received these artefacts and closure
proof. No retry, candidate execution or engine launch occurred. CandidateExecuted
and Ready remain false. Compilation proves C++/SEH syntax and linkage; it does
not prove real caller captures, the cause of ExitProcess, catalogue generation
or gameplay. The next action is a separately reviewed runtime plan using these
actual artefact identities, followed only by its own explicit coordinator GO.

### Message diagnostic: source-only implementation after F

[The F analysis](CALLER-F-ANALYSIS.md) records the verified 644 captured code
bytes, two complete functions, one partial region and the exact observed callsite.
It supplies the concrete ABI, installation/readback/rollback guards, publication
ordering, one-shot and error-count contract for the message observer. F remains
NoCatalogue; no missing dependency or fatal-function name has been established.

The new preparation selector `--catalog-message` is exclusive with the four
earlier selectors. BuildProfile has exactly eleven fields: Name
`t7-catalog-message`, Option `-t7-iw7-catalog`, ArgumentCount 3, the unchanged
TraceSchema/ContextSchema/CallerSchema, MessageSchema
`iw7.t7-catalog-message/1`, and Wiring/PreparedMain/BaseBuildPlan/BaseBuildReceipt.
It still rebuilds only main and Link, reusing the other 412 object references
and the qualified ordinary D2/C proofs. Runtime argv is unchanged.

The three existing wire schemas and generated sources retain their exact built
identities. Only the new profile forwards the already observed five-byte call
through a fixed ABI-preserving wrapper. Forwarding occurs before any diagnostic
API and is never caught. Afterward, at most 384 stack-buffer bytes are read, and
only the prefix before NUL is serialized. Original return value, LastError,
cleanup and exit remain. Installation and buffer observation each publish at
most one new line. Actual maximum-width formats, including CRLF, total at most
7,994 bytes/fourteen lines, within the unchanged 8,192-byte stderr contract.

Source validation passes 94 Python tests with retained source/E7 bindings and
61 PowerShell checks (48 profile, 3 deadline, 10 Link telemetry). The retained
SHA-256 helper's uppercase encoding and SDK stack-bound API were checked in
source; both headers already belong to the qualified input set. No native type,
build child, lease, executable/PDB read or hash was used by this preparation.
No C++ compilation or actual message capture is claimed. The coordinator owns
independent review, integration, and the distinct future build/runtime GO gates.

### Exact message build plan A, awaiting review and GO

Source ff488654f9f7f0a0d7752ca2ffc669839e8deea0 produced
`runtime/t7-message-build-plan-a/build-plan.local.json` (298,664 bytes), SHA256
0b1d6f29cb6b02f81d78e2d11f46bbc3679a635a943cca232b7be72d0643a28a.
Its default source/metadata validation passes with 1,083 inputs and no missing
pin. BuildProfile has exactly the eleven fields specified above.

| Text binding | Bytes | SHA256 |
| --- | ---: | --- |
| Wiring | 31,337 | 25284eabad7d3818c302700234f93f767f8d47c9fd403473a7a82b2670550e46 |
| PreparedMain | 38,500 | a601ef1449eaa4c3ec2c85ea561ed4cc5c1aa75769a4ad1def002d348a971e68 |
| Ordinary D2 plan | 296,330 | daa7097f872b83a5762b2cb56bf6dd5a235ed2beee8e0ff077276c61622d53fa |
| Ordinary D2 receipt | 7,136 | c609bc56523654d8bca4b855024a463393185aab8e19ed4eae94c1ff8f6a09c2 |

Inputs equal callers A exactly. The 413-object Link response changes only its
21st object (main.obj, response-file line 22); 412 objects are reused. Stages
remain main and Link with the existing 4/6 GiB, 120/600-second and 256 MiB limits.
No dependency or common provider was added. The future `runtime/zt-t7-message-a`
root is absent. NativeTypesLoaded, BinaryInputsHashed, LeaseAcquired and
RunRootCreated are false. There is no message candidate or build receipt yet.

The coordinator and runtime parser owner received the exact source, plan and
pins for review. No build, engine execution, new payload read or binary/PDB hash
occurred during preparation. Build and runtime still need distinct GO decisions.

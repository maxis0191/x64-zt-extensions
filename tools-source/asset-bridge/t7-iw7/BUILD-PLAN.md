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

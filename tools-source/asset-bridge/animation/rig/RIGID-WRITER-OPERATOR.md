# Original ribbon rigid writer: protected operator

This is a narrow compiler adapter for the source-only control in
`RIGID-CONTROL.md`. It compiles two copies of the same adapted rigid writer,
each with its fixed first/second header. It never executes either writer, emits
native model assets, builds a FF, installs a mod or starts a game. The old
skinned rig, Doom wrapper, SDK and native observer are unchanged.

`Build-RigidControlWriter.ps1` and the pure `RigidControlWriter.Core.ps1` reuse
the existing `New-RigOwnedJob`, `Wait-RigOwnedPhase`, original-handle identity,
bounded `rig_phase.py`, pinned Beacon drain, `Rig.Compiler` telemetry closure,
ResourceScheduler, input/file identity guards and base transaction. They add no
process owner, native class or resource scheduler.

The closed operator plan binds its own two source hashes, the exact source
package receipt, the eight-file prepared control, FAB native source, compiler,
Python and SDK. It accepts no caller-supplied commands. All argv and child
environment values are reconstructed from the fixed recipe. The supported
source-only plan pins the actual local Python SHA `4d6f5f81...`, not the old
skinned runner's `31073dad...`; that old runner is preserved. The first DEFAULT
refusal from the mistaken old Python pin is retained as failed source evidence.

## Default and explicit execution

Default reads and validates bounded text sources, reports executable paths and
expected SHA values plus the two commands, then returns. Actual executable
hashes are read only under the reservation. Default does not acquire a lease, inventory/hash the
complete SDK, load a native helper, create a work directory or compile.

```powershell
# Source-only DEFAULT. The plan and hashes come from the reviewed capsule.
pwsh -NoLogo -NoProfile -File '<operator>/Build-RigidControlWriter.ps1' `
  -PlanPath '<capsule>/plan.local.json' -PlanSHA256 '<reviewed SHA256>'

# Only after Root's separate writer GO, in the original persistent host:
pwsh -NoExit -NoLogo -NoProfile -File '<operator>/Build-RigidControlWriter.ps1' `
  -PlanPath '<capsule>/plan.local.json' -PlanSHA256 '<reviewed SHA256>' -Run
```

Do not substitute a short-lived child host. `-Run` checks the real host argv
for `-NoExit` before admission. If launching a background helper, preserve that
host's existing control/session route and use a hidden window. No host is
launched by this operator itself.

## Lifecycle and outputs

The plan requires a fresh short `C:\IW7-Work\rcw-YYYYMMDD-suffix` root. One
complete Build lease covers both sequential 120-second compile phases, using
the existing single-translation-unit estimates (2 GiB physical / 3 GiB commit).
The pinned scheduler uses memory telemetry without a numeric free-memory
minimum. The group deadline is 600 seconds; generated output is limited to
128 MiB, with each retained compiler artifact limited to 32 MiB.

The original host's AppDomain context exists before admission and before any
factory call. Source imports are hash-bound under read locks. After admission,
the SDK, compiler support files and native headers are inventoried and guarded.
The prepared text sources are copied into the owned short source directory,
hash-checked and guarded. No stock game data is copied or read.

The two fixed output namespaces are `build/first` and `build/second`. Before
compiler creation, the existing transaction backs up their exact mutable
filenames and the owned first/second/tmp directories. Expected `.exe` and
`.obj` files, plus `.pdb` if emitted, are copied and hash-checked into
`retained/first` and `retained/second` before restoration removes the build
outputs. Those retained writers are not executed; their measured hashes will
be necessary for a separately admitted emission/FF stage.

Each phase captures and persists the original Python handle identity before
Resume, registers it after Resume using the existing CIM retry helper, and
requires the exact compile receipt plus a fresh root-exited/Active0 snapshot.
Only the established, fully witnessed vctip child may use compiler telemetry
closure. A factory exception is not treated as proof of closure.

Restoration runs only after actual owned closure and unchanged source proof.
The transaction checks every target before changing any byte. Lease release
is confirmed against the shared registry before read guards are disposed.
Any ambiguous closure, changed source, failed restoration or unconfirmed
release preserves `IW7.RigidControl.HostContext` in that original host, with
its owner, lease, transaction and guards. Keep the host alive and recover there;
do not delete a lease, dispose unknown handles or relaunch a duplicate job.

`CompilePassedRestored` requires both writers, their successful phase receipts,
source proof, restoration and lease release. All native-emission, FF, GPU,
pixel and readiness fields remain false even after successful compilation.

## Source verification

`test_rigid_control_operator.ps1` uses the existing wait/receipt/transaction
logic with deterministic owner mocks and tiny synthetic temp files. It checks
closed plan refusals, distinct profiles, identity persistence before exposure,
fresh closure samples, failed factory/receipt, restore refusal and retained
guards on lease-release failure. It acquires no real lease and runs no compiler
or native writer. The portable source check is registered in `checks.json`.
Real compiler, original-job and telemetry behaviour still require the admitted
execution and cannot be replaced by these source checks.

Draft DEFAULT A/B hashed cl/vctip/Python before admission. Architecture's P2
moved all three qualifications under the lease. Preserve those earlier logs as
diagnostics; they do not qualify a strictly source-only DEFAULT. A fresh strict
DEFAULT is required for the corrected operator and its exact source pins.

2026-10-14 source evidence: 46 operator controls and 61 existing compiler
closure controls passed. Fresh corrected DEFAULT exited 0; a DEFAULT whose
cl/vctip/Python paths are actually absent also exited 0. Ordinary-host `-Run`
refused before admission for missing `-NoExit`. Both planned native run roots
remained absent. No compiler or native writer was executed and no FF was built.

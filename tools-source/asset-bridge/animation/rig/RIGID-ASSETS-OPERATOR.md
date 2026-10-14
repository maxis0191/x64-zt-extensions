# Original ribbon rigid control: finite consumer operator

`Build-RigidControlAssets.ps1` defaults to a hash-bound source plan. It reads
bounded JSON and pinned provider/prepared text only. Python, writer and candidate
paths need not exist. It creates no directory, type, lease or child process and
does not read/hash stock, FF, game or executable bytes. The exact closed CPP
receipt binds the two immutable writers; it is historical compilation evidence,
not proof of emission or FF acceptance.

The operator imports only reviewed function providers from the immutable
`rigid-control-command-inputs-20261014-a` package. It uses `Rig.Phase`, existing
`New-RigOwnedJob`/BuildJob, original-job Wait, ResourceScheduler, StockBinding and
ModelFF/Base transaction helpers. It adds no native process owner or compiler.
The old two-bone skinned reader, one-model Doom wrappers and SDK/observer
capsules remain independent and unchanged.

## Source review

Use the source plan's exact path and SHA256:

```powershell
& ./tools-source/asset-bridge/animation/rig/Build-RigidControlAssets.ps1 `
  -PlanPath $planPath -PlanSHA256 $planHash
& ./tools-source/asset-bridge/animation/rig/test_rigid_control_assets.ps1 `
  -SourcePackage $sourcePackage -PlanPath $planPath -PlanSHA256 $planHash
```

The tests use mocks and tiny synthetic transaction files. Their only `-Run`
exercise is an ordinary-host refusal before admission. Tests cannot assert native
emission, an actual FF tuple, GPU interpretation or pixels.

## Separately admitted future execution

Execution needs the original bundled `pwsh.exe -NoExit` host, kept alive through
both groups. Start that host only after Root authorizes the next group. Invoke
the commands in that exact host; restarting PowerShell discards original handles
and is not a recovery method. `$planHash` is the source plan's exact hash.

```powershell
& $operator -PlanPath $planPath -PlanSHA256 $planHash -Run -Group Emit `
  -RootGO ('Emit:'+$planHash.ToLowerInvariant())
# Only following a separate Root FF/readback GO and successful Emit restoration:
& $operator -PlanPath $planPath -PlanSHA256 $planHash -Run -Group FF `
  -RootGO ('FF:'+$planHash.ToLowerInvariant())
```

There is one reservation per group. The AppDomain key
`IW7.RigidControlAssets.HostContext` exists before admission/factory and retains
the original source/output guards, state, native owner and any unreleased lease.
`Closed=false` precedes factory; original job identity precedes Resume;
ResourceScheduler registration follows Resume. Exact phase receipts and fresh
original `exit0/Active0` precede successful disposal. Factory, receipt, source,
restoration or registry ambiguity preserves the original context and lease.
Inspect/recover that context in its original host; never delete a lease or guess
closure from absence of a process name.
Successful FF restoration and confirmed release dispose the guards and clear
the context; successful Emit retains them for the separately admitted FF group.
The existing scheduler uses telemetry-only memory policy: the full estimates
are 2/3 GiB physical/commit for Emit and 8/11 GiB for FF, with no minimum
headroom threshold added by this operator.

Emit runs the two fixed writer commands for fresh owned native directories,
requires bounded model/surface pairs and strict original rigid roundtrip JSON.
The pinned C++ source checks all packed geometry, normals/tangents/UV/indices,
rigid lists, zero blends, one root, three root masks, material, binds, bounds and
LOD metadata. The stdout confirms those source assertions through
`geometry_roundtrip_verified`; it does not separately expose numeric blend/flag
fields or assert the engine's shader interpretation.

FF admission qualifies the original stock receipts, live identities/content,
candidate artifact and executable, stages 72 stock entries plus one candidate,
four native files and one CSV (78 total), and backs up owned work before staging.
Only the independently copied 77-byte `fileSysCheck.cfg` may become writable;
immutable inputs use verified hardlinks. The fixed build/verify/dump vectors use
`-headless -unbuffered-io -strict-content-sources` and
`sdk_original_rig_rigid_control`. The inventory must contain exactly the six
typed assets; it includes no xanim or netconststrings.

The FF and four bounded redumps are retained before restoration. Each original
fixed writer reads its corresponding retained pair with `--verify-existing`;
the outer phase receipt, exact executable/spec pins and strict geometry JSON
must pass. All guarded source identities/hashes and stock content are proved
again before restoration/release. A 900-second group deadline, phase deadlines,
2MiB stream limit and 64MiB generated-output limit bound the work. Verified stock
hardlinks are exempt from generated-byte accounting.

`Fastfile` stays null and `FFBuilt` stays false until the full FF inventory and
both readbacks pass and work/stock restoration and lease release are confirmed.
`Ready`, `GPUVerified` and `PixelsVerified` remain false throughout. Consumer
operations belong to the next owner only after that true retained FF tuple;
this operator does not launch a client/server or alter the original SDK49f,
ea7/d25 or A/B observers. No runtime acceptance is established by source tests.

## Actual Emit A failure and correction, 2026-10-14

The first admitted Emit attempt stopped before launching either writer. The
Python phase creates its fresh log leaf with `mkdir()` and its owned `logs`
parent was missing. The hash-bound launch-error receipt reported
`FileNotFoundError` for `logs/emit-first`; the original Python root exited 2
with a fresh Active0 job snapshot. Native outputs remained empty and no FF ran.

Source proof, empty work restoration and lease release were confirmed with no
cleanup error. The original host then disposed its guards, cleared its context
and actually exited 0. Fresh identities were absent and the registry was empty.
The failed state remains unchanged (SHA256
`8bb419c3f846174e95ed30bae6324fe11011e7bdb3faeefcc12ba920817442c4`);
its launch-error receipt is
`2c769de09a69363a3ef12ada4fed405b5cddec9adf5d8cda42f1c122a2f02eb8`.

The correction creates only the owned common log parent before the child
factory. The source mock now requires that directory at factory entry, including
the failed-factory path. A fresh run root and plan pin are required for retry;
the failed A capsule, source plan and receipts are preserved. This correction
does not itself prove writer emission or FF acceptance.

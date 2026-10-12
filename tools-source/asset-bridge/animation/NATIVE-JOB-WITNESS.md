# Prepared native Job Object witness — not executed

The next command targets the corrected launcher helper only. It does not
recompile or emit the already-proved 281-byte animation writer, build ZoneTool,
read game assets or launch a game. It compiles `Probe-NativeJob.cs` once using
Add-Type into an ignored DLL, then uses the existing PowerShell executable for
short, original process fixtures.

The coordinator must first grant the next exclusive heavy slot, fetch/read the
current `origin/main` resource workflow, and reconcile this clean source branch
with that reviewed baseline. The prepared command itself enforces fresh atomic
4 GiB physical / 6 GiB commit admission before Add-Type or fixture launch. An
admission refusal launches nothing. Do not run this during the H1 build slot.

From **PowerShell 7 x64 at the integrated repository root**, the exact portable
command is:

```powershell
$probeRoot = (git rev-parse --show-toplevel).Trim()
$probeShell = (Get-Process -Id $PID).Path
& $probeShell -NoProfile `
  -File (Join-Path $probeRoot 'tools-source/asset-bridge/animation/Run-NativeJobWitness.ps1') `
  -OutputRoot (Join-Path $probeRoot 'runtime/probe-job-witness-20261012-a') `
  -PowerShellExe $probeShell
```

The output directory must not already exist. Preserve any failed attempt and
choose a fresh suffix for a separately authorized correction. No dependency
install, second SDK, writer rebuild or full game copy is part of this command.

## Observations required for a pass

1. **Normal closure:** parent starts child, child starts grandchild. All three
   report fresh PID/creation/image identities and remain alive until signaled.
   The observer retains their original process handles. After the finish
   signal, all exit with zero and the native owner reports an empty job.
2. **Root exits first:** the parent alone receives an exit signal. Child and
   grandchild must remain alive, and `TreeExited()` must stay false. Then the
   exact owner's `TerminateJobObject`/confirmation path must close both retained
   descendant handles without a process-name scan.
3. **Kill-on-close:** a launcher creates an inner native job containing another
   parent/child/grandchild tree. The observer terminates only the verified
   original launcher process. Every inner descendant must exit before the
   harness invokes any outer-job termination. An outer job remains owned as an
   emergency cleanup boundary; relying on that fallback is a failed witness.
4. **Foreign survival:** a separate fixture runs in a different owned job and
   must remain alive after each target cleanup. This never uses an existing
   user or another chat's process as the witness. It exits normally afterward.
5. **Final accounting:** the production receipt functions reserve 1 MiB of the
   32 MiB total, count the helper DLL, fixture JSON/logs and both final receipts,
   then publish only after the full directory passes. There is no 31 MiB dummy
   filler. Boundary rejection is separately exercised by the small source tests.

Fixture tickets use a unique nonce and expire after three minutes. Every node
self-expires after 60 seconds; readiness waits are 10 seconds, original-handle
exit waits five seconds, and owner cleanup confirmation is bounded. All helper
launches use BelowNormal priority and hidden windows. If cleanup is unconfirmed,
the shared Build lease stays quarantined, including if the harness fails.

The expected successful artifact is `native-receipt.json` with status
`OwnedJobWitnessPassed`, three passed cases, recorded original identities and
`AllOwnedTreesClosed` / `LeaseReleased` true. `resource-after.json` may include a
later reservation acquired by another coordinator; it must not be confused with
this witness's released lease. All generated binaries, PIDs and logs stay in
ignored runtime. The runner records exact source/helper/executable hashes.

## Current evidence boundary

The command has **not run**. The helper remains uncompiled after its review
corrections. `Test-NativeProbeSource.ps1` passes 32 lightweight checks, including
AST parsing of both fixture scripts and admission-before-Add-Type ordering;
these checks never execute the new witness or any of its P/Invoke methods.

The planned witness establishes only the cases above if it passes. It does not
inject a failure precisely between suspended creation and resume, force kernel
accounting failures, test the full native animation runner, or validate animation
FF/runtime behavior. Unconfirmed-owner release refusal is currently supported
by mocked light tests, not a deliberately broken live kernel query. Those limits
remain explicit even after a future three-case pass.

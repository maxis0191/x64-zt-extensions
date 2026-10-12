# Native Job Object witness — three cases passed

The authorized run on 2026-10-12 passed on its first attempt, from 03:04:39 to
03:04:43 UTC. The helper compiled with Add-Type under PowerShell 7.6.5; normal
tree closure, root-first exit/descendant termination and launcher kill-on-close
all passed, with the separate witness surviving each cleanup. The original
11 fixture identities were absent from a fresh post-run process inventory.
The reservation was released and two subsequent snapshots showed an empty
registry. Main's original process identity remained unchanged.

All 31 files, including both final receipts and the 13312-byte helper DLL, total
**22593 bytes**. The [sanitized validation record](job-witness-validation-2026-10-12.json)
binds every artifact and source by hash. The native receipt SHA-256 is
`cf07725dc8293a65617dc62cc481b0f187b76ece46e671b63b0af2872dbda1cb`.
No correction/retry, animation writer rebuild, FF, Add-Type beyond the one helper
library, or game execution was needed for this group.

The reproducible command below targets the corrected launcher helper only. It does not
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

The exact command ran under source commit `908869d`, with reviewed main
`4d705f6`. `Test-NativeProbeSource.ps1` also passes 32 lightweight checks, including
AST parsing of both fixture scripts and admission-before-Add-Type ordering;
those separate checks do not execute the witness or any of its P/Invoke methods.

The native witness establishes only the three cases above. It does not
inject a failure precisely between suspended creation and resume, force kernel
accounting failures, test the full native animation runner, or validate animation
FF/runtime behavior. Unconfirmed-owner release refusal is currently supported
by mocked light tests, not a deliberately broken live kernel query. Those limits
remain open after this three-case pass. Near-cap rejection uses scaled file
tests, not a native output flood. No peak-memory or PowerShell 7.0 runtime claim
is made; compatibility with 7.0 was addressed in source but not exercised here.

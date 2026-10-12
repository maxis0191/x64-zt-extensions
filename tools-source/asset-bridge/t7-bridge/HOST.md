# Reusable catalogue host

`Invoke-T7CatalogueHost.ps1` replaces per-attempt dispatch and finalization code
for **future, separately reviewed attempts**. No code substitution, hard-coded
PID, attempt letter, payload hash or N/L global rename is needed between Plans.
The frozen Q scripts and every historical receipt remain unchanged.

The default invocation calls the existing runner's source-only validation.
Only an explicit `-Run` in a fresh Windows x64 PowerShell 7 process with the exact
`-NoLogo -NoProfile -NoExit -File` argument vector may consume a runtime attempt.
The coordinator must approve the concrete Plan, host contract and source pins
before that invocation. This source change grants no runtime authorization.

## Contract and commands

Prepare a private JSON contract, schema `iw7.t7-catalogue-host/1`, with these fields:

| Field | Value |
| --- | --- |
| `PlanPath`, `PlanSHA256` | Canonical absolute path and approved SHA-256 of the Plan |
| `RunRoot` | Exact `Plan.RunRoot` under this repository's `runtime` directory |
| `HostImage` | Exact PowerShell executable path already bound by the Plan |
| `SourcePins` | Exactly three `{Path, Bytes, SHA256}` entries: the entry script, `T7CatalogueHost.Core.ps1`, and `h1-fixture/H1Native.Core.ps1` |
| `PreservedProcesses` | Explicit reviewed array of `{PID, CreatedUtc, Image}` identities; include the unrelated Python process when applicable |

The contract is capped at 32 KiB, the Plan at 128 KiB, each source binding at
1 MiB, and preserved processes at 16. Wrapper pins stay outside the runner's
Plan binding collection, so this wrapper does not alter V1/V2/V3 policy or count
limits. The existing runner/Profile remains authoritative for all Plan policy,
source bindings, qualification receipts, binary pins, resource admission and
native lifecycle. The wrapper reads no binary content or payload hashes.

Use the same five values for default validation, launch and any same-host Finish:

```powershell
$parameters = @{
    PlanPath = $approvedPlanPath
    PlanSHA256 = $approvedPlanSHA256
    RunRoot = $approvedRunRoot
    HostContractPath = $approvedHostContractPath
    HostContractSHA256 = $approvedHostContractSHA256
}
& $entry @parameters
```

After a separate exact-plan GO, the launch argument order is deliberately fixed:

```powershell
& $approvedPowerShell -NoLogo -NoProfile -NoExit -File $entry `
    -PlanPath $approvedPlanPath -PlanSHA256 $approvedPlanSHA256 `
    -RunRoot $approvedRunRoot -HostContractPath $approvedHostContractPath `
    -HostContractSHA256 $approvedHostContractSHA256 -Run
```

The invocation retains a single state at
`[AppDomain]::CurrentDomain.GetData('IW7.T7CatalogueHost')`. It records the real
host creation identity, invokes the pinned runner once, records its return and
attempts finalization. A runner error such as `NoCatalogue` is recorded without
changing the underlying result. A native quarantine keeps the existing runner
and its original owner/lease/guards alive; this wrapper creates no supervisor.

The executable identity is checked independently through `MainModule.FileName`.
The installed managed PowerShell reports `pwsh.dll` in `GetCommandLineArgs()[0]`;
that element is not treated as the executable path. Argument count and every
argument from index 1 remain exact, including the host flags, script and inputs.

## Finalization and retained ambiguity

Finalization requires the same in-memory host, a returned runner, intact wrapper
source/Plan guards, the matching attempt marker and receipt, and a native lifetime
inside this host's invocation. The receipt must prove tree closure, release and
input revalidation, and its original/alias mappings must exactly match the Plan.
The actual native PID and creation time come from the receipt, never from edited
script literals. A live process using that PID is refused even if it appears to
be an unrelated replacement. Quarantine, remaining leases, root/ambiguous run
processes, heavy processes, changed preserved identities, Main, metadata or file
IDs all block finalization. Preserved process identities are also checked before
the runner starts. Finalization never rehashes a payload.

Create-new sidecars `<RunRoot>.host-start.json`, `.host-return.json` and
`.host-postflight.json` sit beside the RunRoot, preserving the runner's fresh-root
and output-budget checks. Existing sidecars or an already consumed in-memory
host refuse a new Run. Sidecars are evidence, not permission to retry or exit.

Only after all closure checks and successful proof publication are wrapper guards
disposed and in-memory `CanExit` set to true. The wrapper distinguishes its own
observed guard disposal from the existing runner's source-based finalization
evidence. Any unexpected exception retains the host and its remaining guards;
`CanExit` stays false. No automatic exit, kill, lease deletion or retry exists.

If closure requires a separately reviewed recovery, `-Finish` may repeat only
the finalization checks in that original host with the exact same parameters.
It cannot relaunch the runner, adopt a different host, discard a quarantine or
overwrite evidence. Publication/disposal incidents can therefore require explicit
diagnosis rather than a successful repeated Finish. An already successful Finish
is not repeated and retains its existing `CanExit` value.

After `CanExit` becomes true, the operator still records the **actual PTY exit
code**, then an **independent process/scheduler absence witness**. Neither proof
is inferred by this helper or replaced by its sidecar. Native exit 0 and a safely
closed host do not establish catalogue success, compatibility or owner acceptance.

## Source-only validation evidence

`Test-T7CatalogueHost.ps1` uses synthetic small text fixtures and fault injection.
It also launches a lightweight PowerShell probe with the actual fixed argument
vector, verifies the observed `pwsh.dll`/`pwsh.exe` distinction and exits it
explicitly, closing its standard input for the subsequent `-NoExit` prompt.
The probe reads a separate bounded JSON receipt: an initial stdout-only reader
was rejected because PowerShell appended that prompt after the JSON.
The probe imports only the host functions; it never invokes the
catalogue runner, admission or native lifecycle. Wrong executable identity,
count, and changes at every argument position from index 1 remain refusals.
It exercises a safely closable `Failed / NoCatalogue`, bad Plan/receipt/lifetime
and alias mappings, native/host/preserved PID reuse, remaining guard/lease/
quarantine, metadata/file-ID/Main/source drift, publication failure, exact launch
arguments, consumed host and RunRoot refusal. Counts are derived for synthetic
collections of zero, one, eight and twenty extra inputs; this is not validation
of any future collection policy. Disposal failure keeps `CanExit` false even
after postflight publication. Its default-entry integration uses
a stub runner that rejects runtime. No game, native type or resource lease starts.
Actual host/engine execution remains a future, separately approved validation.

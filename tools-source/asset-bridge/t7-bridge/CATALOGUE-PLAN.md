# First real T7 catalogue: one minimal experiment

Updated 2026-10-12 after the completed prepatch diagnostic and the coordinator's
decision to observe missing bootstrap inputs during a bounded catalogue attempt.
This recipe is reviewable, not a launch authorization. Diagnostic proof `0dc01d7`
is separate and has already been integrated by the coordinator in PR 160.

The diagnostic captured all 12 windows, closed normally and released its lease.
The engine worker's offline comparison `8670c43` matched eight specified patterns
and found eight instruction boundaries from six anchors. No concrete refusal
remains in those sampled sites. Other hooks, ABI, initialization and file reads
remain incompletely observed. Those limits do not require another probe or an
exhaustive theoretical bootstrap list before this experiment.

## Fixed command and initial inputs

Use a new ordinary `runtime/t7-catalog-a/work` in the conversion worktree. Check
all ancestors and refuse reparse points. `work/zone` is an ordinary directory
containing exactly one selected FF initially. Do not expose the owner's whole
zone directory, `../zone`, XPAKs or `zonetool_paths`.

```text
t7-zonetool-candidate.exe -t7-iw7-catalog mp_freerun_04
```

Exactly argc 3: no engine/dvar arguments, console fallback or other ZoneTool mode.
The create-only output is
`t7_iw7_catalog_1d7749fdf2454720fad852816e9ddde027a157a4cc486aa18b3eb8fd4a25c2ce/catalog.json`.

| Local input | Verified or observed identity | Use |
| --- | --- | --- |
| `t7-zonetool-candidate.exe` | Ordinary D2, 21,740,032 bytes; SHA256 `94dd29a9cb538504ddeb3545483e43a5dfea195aaca155db5bf147f1c6334c15` | Successful ordinary build, distinct from the diagnostic candidate |
| `BlackOps3_UnrankedDedicatedServer.exe` | 21,737,352 bytes; SHA256 `3df511d71e3690b14517379783bbfb713f6fe2ed2f2e73b445b4878216686156` | Durable read-only acquisition, exact engine filename |
| `steam_api64.dll` | 235,600 bytes; SHA256 `71af8666392acad2080a816b9f1196fe9ccb950e1db8a549f8312c4d231f55a8` | Owner dependency matching the acquired manifest |
| `zone/mp_freerun_04.ff` | Owner file, 16,977,344 bytes, ordinary file; payload SHA256 not measured | Only FF selected for this first attempt |

D2's actual build receipt SHA256 is
`c609bc56523654d8bca4b855024a463393185aab8e19ed4eae94c1ff8f6a09c2`,
and its build-plan SHA256 is
`daa7097f872b83a5762b2cb56bf6dd5a235ed2beee8e0ff077276c61622d53fa`.
The receipt records Passed, InputsReverified, TreeClosureConfirmed and
LeaseReleased, with Quarantined and CandidateExecuted false at that checkpoint.
Match D2 against its actual `Stages[].Artifacts`. The diagnostic runner correctly
refuses ordinary D2; do not weaken its instrumented-only check for this command.

The map is absent from dedicated depot manifest 545991. Its owner-stock origin
is known; its version and compatibility with the acquired engine are unproved.
The companion `mp_freerun_04.fd` exists (1,650,439 bytes), but no evidence yet
requires exposing it. A smaller `core_*.ff` is neither a proven donor nor a safe
substitute: the command refuses zones already loaded during initialization.

## Bootstrap discovery and input qualification

At source `fab9358`, original init `0x140504170` precedes `zonetool::t7::start()` /
`handle_params`. The build and engine workers' source audits establish no named
bootstrap FF list. The four files above are an intentional experiment, not a
claim of complete stock closure.

On a concrete missing-file failure, retain the exact requested filename, logs,
exit status and closure evidence. Do not auto-retry or add assets during a live
attempt. A subsequent reviewed plan may add only a dependency justified by that
result or other exact source evidence. No speculative `core_*` batch, whole-zone
link, game clone, XPAK exposure or bulk download. A failure that names no file
must remain unexplained rather than becoming a guessed dependency list.

The FF is deliberately unsealed during preparation: no payload hash has been
read outside admission. The final profile must support this one observed input,
without pretending it already has a trusted hash. Under the same Extract lease,
check the reviewed absolute path, ordinary-file ancestry, size,
attributes and last-write time; open a read-sharing-only guard, calculate its
SHA256 and retain the guard through closure and reverification. Observe the
source file ID under that guard, match each created alias to it and recheck the
same identities after closure. Neither the FF hash nor its file ID is claimed
as a premeasured trusted value in the plan. Record that hash
as observed provenance, not validation against a depot hash. Changed metadata
requires stopping before launch and revising the plan. Verify the three already
qualified binary hashes under admission.

Create only four same-volume hardlinks with fixed relative names and matching
source/destination file IDs; never overwrite or change attributes/ACLs through a
link. Hold original input guards through the attempt. The aliases reference
60,690,328 bytes without duplicating that stock; count their logical size in the
output budget anyway. Exact machine paths and file IDs remain private.

## Reuse the existing native stage

Reuse the witnessed `Probe-NativeJob.dll`, scheduler and existing
`H1Native.Core.ps1` functions `Invoke-H1OwnedStage`, `Complete-H1Stage`,
`Open-H1Pin`, `Read-H1SmallJson` and `Write-H1Receipt`. No new process owner,
scheduler, arbitrary-command launcher or H1 fixture/compiler policy is needed.
`Run-T7Catalogue.ps1` and `T7Catalogue.Profile.ps1` provide the catalogue command
and report checks. They leave the diagnostic runner/profile unchanged and reuse
only its function-only environment/Main checks. File IDs use the existing
`HudFileIdentity.cs` helper, loaded under admission; no new native helper is added.

Default preparation loads no native provider, obtains no lease, hashes no
payload, creates no links and starts no process. Native mode needs an exact
reviewed plan and one separate coordinator GO. Use a create-only attempt marker,
a fresh PowerShell 7 NoExit host, private TEMP/profile environment and original
job handles. Keep the host alive through closure, release, quarantine inspection
and postflight.

- One Extract lease, BelowNormal, 6 GiB physical / 8 GiB commit. These are still
  conservative estimates, not measured catalogue maxima.
- Total 200 seconds, root 120 seconds, failure closure 5 seconds. Input
  qualification and final acceptance share the total clock.
- Stop on the existing marker, invalid telemetry, commit pressure above 85%,
  output overflow, changed input identity, native failure or deadline. Uncertain
  closure/release retains the existing quarantine context and live host.
- Mutable output 64 MiB, 64-entry tree bound, 64 KiB receipt reserve, logs at most
  1 MiB each and catalogue at most 512 KiB. With four aliases the logical ceiling
  is 127,799,192 bytes. Sampled limits are not OS quotas.
- Preserve Main PID/creation/image/UDP 27016 identity before and after; stop on a
  conflict. No player connection or Main configuration change.

The private layout/environment does not confine every engine I/O. The ZoneTool
XPAK-helper denial occurs after original init and proves nothing about earlier
or independent engine reads. Retain and diagnose unexpected outputs. Keep aliases
after closure; do not add destructive cleanup or clear the shared read-only engine
attribute.

## Evidence and result meaning

The in-process PowerShell validator follows the reviewed
`t7-iw7/catalog_contract.py::validate_catalog` contract: schema
`iw7.t7-iw7-model-catalog/1`, exact requested zone, provenance
`observed_during_requested_zone_load`, sorted unique observed names, at most
1,024 names and 256 KiB name storage. Header counts establish neither mesh
residency nor a convertible donor. Its seven false claim fields stay false.
No export or geometry validation is requested.

Distinguish absent output, invalid output, valid empty catalogue, and valid
catalogue with observed names. Exit 0 alone is insufficient. A valid empty
catalogue records the request but is insufficient donor discovery. Accept a
catalogue observation only after root exit 0, fresh original ActiveProcesses 0,
normal closure, guarded report validation, input reverification and lease
release. A forced stop or deadline cannot become success.

Raw logs, inputs, observed FF hash, identities and receipts remain private.
Publish sanitized evidence of what was actually reached: failure before CLI,
missing dependency, empty catalogue or observed names. No result here proves
source-zone ownership, ABI, conversion, materials, IW7 FF build, rendering or
owner gameplay acceptance.

`Run-T7Catalogue.ps1 -PlanPath <local-plan> -PlanSHA256 <reviewed-hash>` validates
the fixed command, exact D2 build receipt, source pins and original metadata,
then returns `PlanCheckedPendingGO`. `-Run` consumes one create-only attempt and
qualifies the observed FF hash under the same 6/8 GiB lease. Ordinary nonzero exit
retains useful report evidence while remaining Failed. No report is inspected
while the job remains unclosed. After forced closure, only the bounded JSON may
be read outside admission; stock is not rehashed and success remains impossible.

`Test-T7Catalogue.ps1` passes 95 light checks using synthetic files, fake owners
and clocks, with no owner-stock reads, native type loading or real reservation.
It covers report scope/count/name/refusal cases, retained file guards, fixed-plan
and retry refusals, output caps, ordinary root failure, closure quarantine, and
the actual runner finalizer after late release/publication or forced closure.
The native catalogue path itself remains unexecuted. Coordinator review and a
separate exact-plan GO are still required; exhaustive theoretical bootstrap
closure and another prepatch capture are not gates.

## Attempt A: stopped on unlisted startup outputs

The single authorized A invocation at source `8760567`, plan SHA256
`cb8e16f3a98917b4ad4d0fe9264e1086e10c6b2b21d0c452afa4f5efba66bf40`,
ended Failed/NoCatalogue. The output guard encountered paths outside its initial
allowlist: `work/steam_appid.txt` (six bytes, `311210`) and `work/identities/`.
The latter contains only `dedicatedpc/` and its empty `dumps/` and `LPC/`
directories. No identity payload or key was present/read. These are observed
startup outputs, not evidence of engine incompatibility or a missing FF.

The retained original job was stopped and its closure confirmed; the reservation
was released without quarantine. Both outer logs are empty. Four input hardlinks
remain intact. The selected FF hash observed under admission is
`7456c7fbbcfe29ca3b71298bfab3f77e253dfabdda82a88304aa8eecb019125b`.
Because closure was forced, the runner correctly records InputsReverified=false;
no payload was rehashed after release. The subsequent metadata/file-ID check
matched all four sources and aliases, separately from content reverification.

Postflight at 13:22:32 UTC found no lease, heavy workload or original root and
confirmed Main's generation/UDP owner and the preserved Python process. The
launcher host exited normally after its quarantine check; host and candidate
were absent at 13:22:55 UTC. Raw files remain private. The
[sanitized A record](catalogue-runtime-a-20261012.json) binds the receipts.
Prepare a narrowly scoped source correction and a new plan; A must never retry.

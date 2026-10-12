# Recipient observations: source-only runner

This narrow runner requests four non-default recipient references, followed by
one compiled `scripts/engine/utility` export. It does **not** complete a mod
package. Source preparation and synthetic tests were performed on 2026-10-12;
the first authorized native attempt subsequently timed out before producing
reference results. The later H run verified all four requested stock references
after loading all 25 zones, then confirmed restoration. Compiled retail script
bytes remain unobserved by this runner. Coordinator adoption/admission is required
before each `-Run`; there is no automatic retry. See the historical attempts below
and the [next script Plan and Beacon evidence boundaries](SCRIPT-PLAN.md).

## Confirmed retained native API

The existing E7 fulltool is 21,696,512 bytes, SHA256
`e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04`.
Its retained source pin is `fab935826c898806855376662a8a03317b3ad8f1`.
`src/zonetool/zonetool/iw7/zonetool.cpp` hashes to
`f1c9fb861b81727dc7e3882f5116231e6dc0d1a0e6f5838953a62232171059bc`;
`src/zonetool/zonetool/shared/assets/scriptfile.hpp` hashes to
`5f6b30e5540563c41e8ce5d5d42d388f687e138ba7e5c2dbb30dc7eb720fc823`.
These files are not among the candidate's five patched translation units.
`Assert-BeaconCandidate` also verifies its existing build artifact, preparation,
closed build result, three patches and real 413-command compiler evidence.

The two real CLI invocations, in separate original-owned jobs, are:

```text
zonetool.exe -headless -unbuffered-io -strict-content-sources -enemy-reference-check cp_zmb recipient-material.csv sdk_beacon_recipient_a
zonetool.exe -headless -unbuffered-io -strict-content-sources -enemy-script-dump cp_zmb recipient-scripts.txt paris_enemy_cp_zmb_sdk_beacon_recipient_scripts
```

`-enemy-reference-check` immediately exits after writing its result. Concatenated
flags cannot execute both phases. The script request has **no `.gsc` suffix**.
The fixed requests are read from the existing SDK request files, validated
exactly, hash-bound, guarded and staged as hardlinks. No arbitrary asset list or
extra CLI flags can be supplied through the spec.

Reference output is `enemy-catalog/sdk_beacon_recipient_a.csv`: exact header
`type,name,status`, followed by the four ordered request rows, all `verified`.
Native code uses direct registered entries and `DB_IsXAssetDefault`, without
creating defaults. This proves effective resolution only. The CSV's hash is
provenance and **cannot substitute for a serialized asset content hash**.

Script output stays at its original path:
`dump/paris_enemy_cp_zmb_sdk_beacon_recipient_scripts/scripts/engine/utility.gscbin`.
The adjacent pack root `scriptfile-manifest.csv` must contain exactly one row
with the exact donor, pack, module, path, `dumped` status, size and SHA256. The
native exporter indexes `ScriptFile::name`, rejects ambiguous pointers with the
same requested name, compares the dump to loaded bytes and hashes the result.
The Python verifier independently checks name, lengths, exact size and streaming
SHA256 using one original descriptor with stable before/after file metadata.
Manifest parsing and hashing also use one bounded byte snapshot. No second copy
of a potentially large export is made; see [reader limits](SCRIPT-PLAN.md#bounded-output-reader).

The serialization contains the 22-byte ASCII name, NUL, three little-endian
signed int32 lengths (`compressedLen`, `len`, `bytecodeLen`), compressed buffer
and bytecode. Every length is 0..64 MiB. `len` is a scalar only; there is no
decompressed source buffer in the file. Maximum is **134,217,763 bytes**,
not three 64 MiB buffers. Tests use tiny invented bytes, never retail content.

## Shared providers and admission

`provider-pins.json` fixes 12 existing reviewed providers, including common
`StockBinding.Core.ps1` from commit `618c3ba`, Beacon validation/drains, original
`BuildJob.cs`, ModelFF restoration and AnimationFF registration. Supply an
explicit `ProviderRoot` containing those exact bytes. No provider is copied or
changed. A future provider update needs a reviewed pin change.

The spec is a local JSON object with these mandatory fields:

| Field | Meaning |
| --- | --- |
| `RunRoot` | Fresh absolute path inside this checkout's `runtime` |
| `StockRoot` | Canonical absolute retained stock root |
| `StockReceipt`, `StockReceiptSHA256` | Original 72-entry completed receipt, SHA `4cf67ebe1645c6c0761b9a24cb4e4630edee9c5d737742c704d624fe60cb3850` |
| `StockBindingReceipt`, `StockBindingReceiptSHA256` | Explicit current durable `iw7.ff-stock-observation/1` and measured hash |
| `RecipientStockBindingReceipt`, `RecipientStockBindingReceiptSHA256` | Explicit separate PAK metadata receipt and measured hash: original four-PAK schema `/1`, or observed 4+1 schema `/2` after E2; never auto-expanded |
| `ReviewedStockManifest`, `ReviewedStockManifestSHA256` | Reviewed content manifest, SHA `9116255ef148a324df15fa914795a7917615f023973111fdc39ae7329a9dcbf4` |
| `CandidateRoot`, `CandidateArtifactSHA256` | Existing E7 fulltool directory and final artifact hash |
| `PythonExe`, `PythonExeSHA256` | Absolute interpreter path and measured hash |
| `RequestRoot` | Absolute SDK directory holding the two existing request files |
| `MaterialRequestSHA256`, `ScriptRequestSHA256` | Exact measured request hashes |

No machine paths or invented observations are supplied as tracked defaults.
Invoke from a fresh PowerShell 7 host:

```powershell
& ./tools-source/asset-bridge/recipient/Run-RecipientClosure.ps1 -ProviderRoot $providerRoot -SpecPath $specPath
```

Without `-Run`, the runner hashes bounded evidence/providers, reads stock binding
metadata and returns a plan. It performs no Add-Type, stock inventory/content
hashing, reservation, directory creation or child launch. A missing/changed pin
fails; it does not refresh or rewrite historical evidence.

Use the explicit `-ReferencesOnly` switch in both plan and execution for the
Recipient B diagnostic probe. The native reference CLI is unchanged, and no
utility process follows it. The default still runs both phases. A completed
references-only run records `ReferencesObservedScriptNotRun` and leaves
`ScriptBytesVerified=false`, `Ready=false` and `ClosureComplete=false`.

The common binding preserves historical 63-link/9-copy provenance separately
from the baseline's 71 stock hardlinks and one 77-byte mutable sentinel copy.
The post-C [supplemental Recipient profile](STOCK-PROFILE.md) adds four
previously observed PAKs as hardlinks; the separate post-E2 profile adds only
pak69 to that exact list. Neither changes the common FF binding. The original
profile has 75 stock hardlinks and one sentinel copy, totaling 79 transaction
paths with candidate/requests. The 4+1 profile has 76 stock hardlinks and one
sentinel copy, totaling 80 transaction paths. `StockBudget` records the distinct logical
and deduplicated hash-read bytes. Supplemental content is not read during Plan.
Before staging, the admitted operation holds all source guards, checks observed
NTFS identities, hashes deduplicated physical stock content, then verifies
size/time/attributes. The candidate and two requests add three immutable links.
Only the separately identified sentinel may be made writable.

Both native modes call the same source-zone loader: existing shared shader core
zones, then available techsets/base/patch for code_post_gfx, global, common,
global_mp, global_cp, common_mp, common_cp and cp_zmb. The plan derives the exact
available order from the bound profile. Each phase must log that exact sequence
without errors. Bootstrap code_pre_gfx loads through the engine separately and
remains in the bound input inventory. No owner-zone attribution is invented.

One shared reservation covers 8 GiB RAM/11 GiB commit. The runner stops on
commit above 85%, a `stop.request`, 600 seconds overall, or 256 MiB generated
output. Each native phase allows 240 seconds and each original job 245 seconds.
SDK drains cap stdout and stderr at 2 MiB each. The filesystem threshold is
polled, so overshoot is possible; it is not a disk quota or measured memory peak.

Original job PID, image, creation time and BelowNormal priority are captured
**before Resume**. The reviewed scheduler's CIM registration follows Resume,
with a bounded five-second retry; it is not falsely recorded as pre-resume
attachment. Native children inherit the non-breakaway KILL_ON_JOB_CLOSE job.
The unused stdin pipe stays open to avoid the retained console's EOF spin.
Timeout/drain/receipt failures stop that original job, never a rediscovered PID.
Root exit **and zero job members** are required before restoration. Factory or
closure uncertainty preserves guards, inputs and reservation in quarantine.
After root exit a nonzero active count gets a bounded five-second drain, still
within the outer deadline. Every observed count, elapsed time and root exit code
is recorded; it is not treated as immediate failure or successful closure.

Only recorded staging paths are restored, preserving all exports/logs/cache.
Shared restoration verifies sources again before releasing the reservation.
The state records actual phase results separately from restoration. If the
adapter has resumed but no native PID receipt is available, `NativeExecuted`
is null, not an invented true/false result.

## Missing normal image and technique set

These are separate future observations and are deliberately absent from the
two-phase runner and its 256 MiB group. The retained APIs are:

* Normal image: `-dump_streamed_image -enemy-image-dump cp_zmb <one-name-list>
  paris_enemy_cp_zmb_sdk_recipient_normal_images`, with exactly
  `park_clown_zombie_shoes_n_3e46d100_packed_nog` in that list. No `-dds`.
  Existing early registration capture writes an `image-manifest.csv` and copies
  the selected source's header/pixel files. This requires a separately reviewed
  output budget because early capture plus selected-source copy can duplicate
  storage. Verify the header and every required external stream; a header alone
  is insufficient. Actual normal stream presence/count remains unobserved.
* Technique set: **console command**
  `dumpasset techset mopw_l_sm_replace_i0c0s0o0n0p0`, after source-zone loading.
  There is no `-dumpasset` CLI flag. Console `loadzone` commands can prepare the
  matching source order; CLI `-loadzone` exits and cannot be treated as the same
  console session. The dump goes under `dump/assets/techsets`, writes `.techset`,
  `.techset.txt`, referenced technique data and vertex declarations. Shader names
  are serialized, but shader-program dumping calls in `dump_technique` are
  commented out. Therefore this is not complete shader closure. Any later exact
  shader-name dump must also prove program bytes remain valid after loading;
  the early shader hook belongs to the broader `-enemy-extract` path and is not
  silently enabled here.

Utility imports require an actual compiled-file analysis. Effective references,
compiled content, transitive dependencies, complete images, runtime rendering
and owner acceptance remain distinct. Every successful observation still sets
`closure_complete=false`, `package_ready=false`; the outer state retains
`ClosureComplete=false`, `Ready=false`, `RuntimeVerified=false`.

## Source-only checks

```powershell
python -B -m unittest discover -s tools-source/asset-bridge/recipient -p test_recipient.py -v
pwsh -NoProfile -File tools-source/asset-bridge/recipient/Test-Recipient.ps1
pwsh -NoProfile -File tools-source/asset-bridge/recipient/Test-RecipientLight.ps1
```

11 Python fixture tests, 35 PowerShell source/contract checks and 13 pure light
observer identity checks passed. They
cover exact requests/verbs, CSV shape, missing/default/extra rows, paths, names,
hashes, lengths, bounds, source-zone order and default-plan/ownership ordering.
Simulated original owners cover delayed-empty success with retained counts,
five-second persistent-member failure, root-not-exited failure and late closure.
They do not prove native execution, resource peaks, restoration or package
closure.

## First native attempt: timeout, restored

The [sanitized evidence](native-validation-2026-10-12.json) records the single
coordinator-approved execution of `cb3d9ac` with reviewed durable stock and E7.
The native references process started but emitted no stdout/stderr or result CSV.
Its adapter reported `phase timeout` at 240 seconds and exited 2. The original
job still reported two active members during 42 observations through 244.9996
seconds. The outer 245-second deadline then stopped the original job; root exit
and zero members were confirmed. The script phase never started.

Restoration and source preservation passed, all recorded staging paths were
removed, the lease was released and the registry was observed empty. Main's
process identity was unchanged. Final retained output was 1,218,874 bytes,
including two 549,664-byte cache indexes. No CLI, stock, binary or deadline was
changed and no retry occurred. These are failure/lifecycle observations, not
reference, utility, package or rendering validation.

Three exact-process CPU/memory snapshots were retained; native CPU increased
from 4.234375 to 4.46875 seconds between 04:44:24 and 04:46:51 UTC. Thread waits,
stacks and window inventory were not captured before closure. The cause remains
unknown. The unchanged outer state keeps `NativeExecuted=null` because failure
preceded receipt validation; the retained native PID receipt and process
observations independently prove the launch. Next: compare the successful Beacon
bootstrap/stdio and prepare bounded existing-tool diagnostics for review, without
another native execution until separately authorized.

The subsequent [diagnostic plan](DIAGNOSTIC-PLAN.md) compares the actual successful
Beacon receipt with this failure and documents a reproduced reader-buffering
blind spot. Recipient's adapter now uses unbuffered pipes and raw bounded log
files; the pinned SDK drain is unchanged. Review of `4867081` exposed a raw
short-write defect. A local bounded write-all adapter now counts actual accepted
bytes and refuses non-progress or write errors; successful counts must match the
retained files. Review of `f1096b1` also found that non-OSError exceptions could
silently end a drain thread. A local thread-entry guard now records any exception
type, marks capture failed and signals the phase owner. Twenty-three
transport/writer tests cover short live messages, EOF, caps, timeout prefixes,
partial/zero/None writes, errors after a saved prefix, read/write/flush ValueError,
closed pipes, SystemExit and exceptional finalization. Failed captures remain
failures even when the native stub exits zero and output bytes were retained.
This fixes visibility/integrity only; the subsequent B result below does not
establish or fix the native cause. Native-start/capture receipts
explicitly distinguish observed PID/timing from verified creation/job closure.
The B native observation used the existing 8/11 GiB group and light
diagnostics. Full snapshot/CDB capture at 10/14 remains an unexecuted plan
requiring separate review and authorization.

The prepared B plan uses a new RunRoot and the explicit references-only mode.
`Recipient.Light.ps1` is hash-bound with local runner sources but is not invoked
by the native launcher. Its read-only observer links the locator to the original
Python identity, verifies real parent/child creation, image and E7 hash, retains
a process handle during sampling and rechecks identities afterwards. Later
samples must pass the first native identity; replacement PIDs are refused.
It records CPU, memory, IO, up to 256 thread states/waits and the main window.
It does not enumerate all windows or directly query job membership. See the
diagnostic plan for sample timing and output limits.

## Recipient B: visible progress and fatal window, restored

The [sanitized B record](native-validation-b-2026-10-12.json) preserves the one
authorized execution of `379526b` under fresh atomic 8/11 admission. The exact
E7, stock, reference CLI, stdin pipe and deadlines were retained. Live stdout
contains 1,449 bytes through `Loading zone "global_mp"...`; stderr is empty.
The exact native process had the same `Fatal Error` main-window handle in three
identity-checked samples. The body of the dialog and the root cause remain unknown.
Earlier missing `eng_*` notices do not prove the cause.

Samples actually occurred at 43.35, 107.14 and 193.22 seconds, missing the
planned early schedule; their recorded ages take precedence over filenames.
DirectJobMembershipQueried is false. CIM's two-second per-request timeout is
not a hard deadline for the entire observation. CPU grew only 0.266 seconds
between first and final samples; native IO totals were unchanged. These facts
locate a persistent fatal window without supplying a call stack or dialog body.

The existing dialog reader required a private desktop absent from this launch.
The coordinator then authorized `stop.request`. Permission for a bounded Python
ctypes text read arrived after that stop was placed; the stop was not revoked.
No click, new reader, dump, CDB or retry occurred. The original state remains
Failed / `Coordinator requested owned stop.`; root exit code 122 and zero job
members were confirmed. Restoration and source preservation passed, all 75
staged paths disappeared, no owned process or lease remained, and Main retained
its exact identity. Final retained output was 1,225,970 bytes.

No reference CSV, phase receipt or utility phase was produced. The outer
NativeExecuted field remains null; its unchanged meaning is preserved while the
locator and three real process samples independently prove native launch.
Next: prepare the bounded identity-checked dialog text reader before requesting
a separate short diagnostic attempt. B's single-run authorization is exhausted.

## Recipient C: automatic fatal-text probe

`-FatalTextDiagnostic` is an explicit references-only mode. It preserves E7,
native CLI, stdin PIPE, the 72-entry stock and original job owner; it changes no
zone/pool logic. RAM/commit remain 8/11 GiB. The adapter limit is 45 seconds,
the original job limit 50 seconds and the group's active-work limit 60 seconds.
The existing closure wait allows 15 seconds after `Stop` returns, followed by
guarded source verification/restoration. That wait does not bound the `Stop`
call itself or restoration, and is not a promise that the entire lifecycle
completes within 60 wall-clock seconds. Ordinary modes retain their deadlines.

The adapter checks automatically every 250 ms using `recipient_dialog.py`, with
the existing Python interpreter and ctypes. It uses the original Popen process
handle and the current parent's handle; image, true creation FILETIME, PID,
parent relationship and E7 are checked. Only windows owned by that child are
read. A `Fatal Error` caption triggers at most one body capture: at most eight
child controls, STATIC text only, at most 16 KiB UTF-8 of window text and classes.
WM_GETTEXT uses a 200 ms timeout per control. A result of at least 2,047 characters
in its 2,048-wchar buffer marks that control `buffer_saturated` and the aggregate
`text_truncated`, conservatively including an exact fit. No second read is sent.
Identities/HWND ownership are checked
before and after; any reassignment discards the text. No button, command, click,
debugger, dump, new process or compiled reader is used.

The bounded `references/fatal-dialog.json` and failed phase receipt are saved
before `diagnostic-stop.request` tells the original PowerShell job owner to stop.
Missing text or a reader error still stops the diagnostic; neither successful
reference output nor a native zero exit can mark the phase accepted. The outer
status is `DiagnosticFailed`, with no reference/script acceptance. Unknown
closure still retains the original quarantine safeguards.

19 fake Win32 fixtures and 25 pipe/writer fixtures cover identity reuse,
ownership changes, timeouts, buffer saturation, Unicode byte bounds, control limits and automatic
failure signaling. They spawn no process and do not validate a real C dialog.
The subsequently authorized C attempt and its limits are recorded below.

### C result: missing asset-file request, restored

The [sanitized C record](native-validation-c-2026-10-12.json) preserves one
execution of `79735fe` after fresh atomic 8/11 admission. The reader captured:

```text
Could not find asset file assetfile17.pak
```

The fatal record was written about 4.08 seconds after native creation. It contains
three controls, verified original parent/child identity and no text truncation,
buffer saturation, read error or interaction. Stdout remained the same 1,449-byte
sequence as B, ending at `global_mp` loading. The message identifies an unresolved
file request; it does not establish whether the file exists in retained stock.

The automatic stop completed with original root exit 2 and zero job members.
Status remains `DiagnosticFailed`, with no accepted references. Restoration and
stock preservation passed; all 75 staged paths were removed, no owned process or
lease remained, and Main plus the owner IW7 process inventory retained identical
PID/image/UTC creation ticks. Original receipts remain unchanged. Final retained
output was 1,216,572 bytes. No retry, utility phase, pool/zone workaround, dump or
debugger was used. C's single-execution authorization is exhausted.

The subsequent [source-only investigation and correction](STOCK-PROFILE.md)
found pak17 in durable stock and proved its omission from C. A separate profile
now binds the four PAK prerequisites retained in the older CP diagnostics.
No post-C native execution or content requalification has occurred. Further
execution requires review, a fresh admission and a new GO; the next slots remain
GSC then rig.

### D result: progressed to global_cp, fatal body unavailable, restored

One authorized references-only execution of `fde8c49` used the separate four-PAK
profile. The [D record](native-validation-d-2026-10-12.json) retains the exact plan,
command, identities and artifact hashes. Fresh 8/11 admission and guarded stock
requalification passed before staging. The native log reached `global_cp` after
`global_mp`, `patch_global_mp` and `techsets_global_cp`; 15 of the expected 25 zone
messages were observed. No reference CSV or phase receipt was produced.

At native age 18.67 seconds, the original identity-bound light observer reported
`Fatal Error`. It records a title, not control text: D's fatal body and exact
cause remain unknown. The observer preserved its evidence and requested an
immediate original-job stop. Command completion followed about 3.67 seconds after
the request, without waiting for the native deadline. Original root exit 122 and
zero members were confirmed separately; 122 is not a native exit code.

Status remains Failed. All 79 managed paths were removed, source identities and
metadata matched, restoration/source preservation passed, no owned process or
lease remained and owner/Main identities were unchanged. Final generated output
was 1,221,694 bytes. References, script bytes, package closure and Ready remain
false. No retry or PAK expansion followed. Binder overlay-role support remains a
separate coordinator gate and was not bypassed.

Next source-only correction: reuse the existing bounded fatal-body reader in
normal references mode while preserving normal success when no fatal exists.
D's failure record will not be rewritten as a body-capture result. A new plan,
review and GO are required before any further native execution.

## Post-D source correction: fatal text during normal references

The existing `recipient_dialog.py` reader is now invoked every 250 ms during
the normal references phase as well as the explicit diagnostic. Its implementation
and limits are unchanged: original parent/child handles and identities, one fatal
capture, at most eight controls, 16 KiB text, 200 ms per WM_GETTEXT, a 64 KiB
record and no UI interaction. The plan explicitly declares
`FatalTextCapturePhases=['references']`; script export is unchanged.

Normal mode still validates and accepts a successful reference observation when
no fatal or reader failure is observed. On a fatal or an identity/reader error,
it saves `references/fatal-dialog.json` and a failed `references/phase.json`
before emitting `fatal-stop.request`. The existing original PowerShell job owner
checks this marker in its budget loop and stops its original job. The reader
never terminates a process, follows a replacement PID or clicks a dialog.
A native zero exit does not override the captured failure. Missing/unattributable
body text stays missing, with the reader error recorded. Evidence-write failure
also cannot reach reference validation; ordinary outer failure cleanup applies.

`FatalTextDiagnostic` and `DiagnosticOnly` remain distinct: the forced diagnostic
still uses 45/50/60 seconds, always fails qualification, writes its existing
`diagnostic-stop.request`, and cannot accept a no-fatal zero exit. Normal mode
keeps 240/245/600 seconds and may succeed. Normal fatal status is Failed, not a
diagnostic-only success. Both modes require original tree closure and restoration.

143 light checks pass: 37 Python contract/dialog fixtures, 25 unchanged-provider
stream fixtures, 42 PowerShell source/contract checks and 39 supplemental-stock
checks. New full-phase fixtures use fake process/capture/Win32 dependencies and
real tiny receipt files to exercise normal success, normal fatal even with zero
exit, diagnostic fatal/no-fatal, invalid identity, persistence failure and
unchanged script success. They verify both receipts and the appropriate marker
exist before the intercepted failure exit. No real native execution validates
this post-D wiring yet. PAK scope, native E7/CLI, loader, provider pins, resource
budgets and D's original evidence remain unchanged.

## E2 review correction: fresh closure deadline checks

Independent review of the unexecuted E plan found a real acceptance defect in
`Wait-RecipientPhase`: it read elapsed time before `Owner.ExitCode` and `Save`,
then returned for Active=0 without checking the time those calls consumed.
A slow getter or persistence callback could therefore qualify closure after
the 245-second phase or five-second drain limit. The new slow-getter fixture
reproduced that defect against the previous implementation; E was not launched.

The loop now reads the same monotonic Stopwatch before an iteration and after
each original-handle getter, Save and budget callback. The drain clock starts
at the first confirmed root-exit observation, before querying Active. Both
deadlines are checked using fresh time after Save and before any successful
return. Observation timestamps follow the completed ExitCode read. An empty
job returned after either deadline is rejected; a still-populated job fails
at the drain limit. Empty closure exactly at the inclusive limits remains valid.
The original owner still performs stop, verified closure, restoration and
quarantine on failure; none of those mechanisms or limits is weakened.

This change rejects late results; it does not preempt a blocked getter or I/O
callback or establish a hard wall-clock completion bound for Stop/restoration.
Such a late result cannot be accepted as timely closure. Corrective review and
a new exact E2 plan/GO remain mandatory before native execution.

65 PowerShell source/contract fixtures and 39 stock fixtures pass. Added fixtures
advance a fake monotonic clock inside Exited/Active/ExitCode getters, Save and
the budget callback, including 1 ms deadline crossings, and require the exact
deadline error. Slow calls within both limits, exact boundaries and the existing
normal/multi-observation drain cases still pass. Python capture, reader, native
command, PAK scope and provider pins are unchanged by this correction.

### E2 result: exact pak69 fatal captured in normal mode, restored

One separately authorized execution of `4acad77`, recorded in the
[sanitized E2 evidence](native-validation-e2-2026-10-12.json), passed fresh 8/11
admission, guarded content requalification and the unchanged four-PAK staging.
Normal-mode automatic capture returned the exact body:

```text
Could not find asset file assetfile69.pak
```

The original parent/child identities were verified before and after. Three
controls supplied 76 total text bytes, without truncation, saturation, reader
error or interaction. The fatal record was written about 5.34 seconds after
native creation, followed by the failed phase receipt and `fatal-stop.request`.
The stdout hash and 1,665 bytes match D, ending at `global_cp` with 15 of 25
expected zone messages. E2 has its own captured body; D remains body-unknown.

The original owner stopped its job and confirmed root exit 2 with zero members.
Root exit 2 is not a native exit code. Status is Failed with DiagnosticOnly=false;
no reference CSV was accepted and the utility phase never ran. All 79 managed
paths were removed, source metadata/identities matched, restoration and stock
preservation passed, no owned process/lease remained and owner/Main identities
were unchanged. Final generated output was 1,223,303 bytes. Ready, references,
script bytes and package closure remain false. No retry or profile expansion
was performed during E2. The corrected timing-boundary acceptance remains
source-tested; this fatal-stop outcome is not a native deadline-success witness.

Next authorized work is source and metadata investigation of the single observed
pak69, followed by a separately named explicit 4+1 profile and its budget/tests.
No retail hashing without admission, no stock copy and no further native run are
authorized by E2's exhausted GO.

The source-only [explicit 4+1 profile](STOCK-PROFILE.md#explicit-41-profile-after-e2)
is now prepared with a new schema/name, E2 fatal-evidence pin and exact
966,557,876-byte supplemental logical ceiling. The original four-PAK receipt and
600 MiB ceiling remain unchanged. A fresh metadata-only observation and two
identical Plan outputs exist locally; no five-PAK staging or native run occurred.
65 stock fixtures plus 65 source/contract fixtures pass. A separate corrective
review, complete admission/content verification and GO remain required.

### F result: pak101 fatal, five-PAK transaction restored

The [F record](native-validation-f-2026-10-12.json) retains one authorized
references-only execution of `a8c16c0`, exact plan/command pins and fresh 8/11
admission. The five-PAK profile passed guarded content requalification and
source/target identity checks. Normal fatal capture then returned:

```text
Could not find asset file assetfile101.pak
```

Original identities were verified before/after; three controls contained 77
total text bytes without truncation, saturation, error or interaction. The
fatal record was written about 5.34 seconds after native creation. Stdout remains
1,665 bytes, byte-identical to E2/D and ending at `global_cp`; no new completed
zone or qualified reference is inferred from the new missing-file request.

Automatic stop confirmed original root exit 2 and zero job members. Independent
checks confirmed all 80 managed paths removed, source identities/metadata
preserved, restoration/source preservation, no remaining owned process or lease,
and unchanged owner/Main identities. Final generated output was 1,225,406 bytes.
Status remains Failed, DiagnosticOnly=false. No script export, retry, dependency
addition or promotion followed. Binder and package qualification remain separate
unpassed gates. F's single-execution GO is exhausted.

Next: investigate existing source/index evidence and metadata for the complete
CP asset-PAK requirement, rather than automatically adding a sixth PAK. If a
complete dependency index cannot be established from retained evidence, assess
an explicit inventory of existing Doom `assetfile*.pak`, separately from image
PAKs, with measured logical/identity counts and a newly reviewed I/O budget.
No retail hashing or native execution is authorized during that investigation.

The [complete-scope note](COMPLETE-PAK-SCOPE.md) now records that investigation
and the subsequently authorized source preparation. A distinct `/3` profile
covers all 33 reviewed asset PAKs, with pak1 kept in the baseline, 32 additions,
an independent pinned metadata inventory and a 5,148,447,113-byte total stock
hash-read budget. All 59 new, 65 earlier-profile and 65 source/contract checks
pass. A deterministic references-only Plan describes 107 managed paths and an
absent run root. No retail hash, staging or native run was performed. Plan review,
new-profile binder agreement and a separately granted GO remain required.

Independent review subsequently rejected G's inventory-read sequence: its size,
hash and parsed content came from separate path opens. The [correction](COMPLETE-PAK-SCOPE.md#review-correction-one-bounded-guarded-snapshot)
uses one guarded handle and a fixed 128 KiB + 1 buffer, with SHA256 and JSON from
the same snapshot. Its 27 targeted checks and 65 source checks pass. G remains
unapproved and unchanged; no revised Plan is generated before correction review.

## H: four references verified, scripts not run

After favorable snapshot review, a distinct Plan H received one explicit GO
and executed source `e0654a74`. Its complete 33-asset-PAK profile loaded all
25 expected zones through `patch_cp_zmb` and returned **4 verified, 0 missing,
0 default** rows for the exact requested material, techset and two images.
The [H record](native-validation-h-2026-10-12.json) pins the 265-byte result CSV,
native receipt, logs and independent final observation.

Native and original root exit codes were 0. The original job reached zero
members; stdout/stderr drains closed. All 107 staged paths were removed and all
107 source identity/size/time/attribute observations matched. Restoration and
stock preservation were confirmed, owner/Main identities were unchanged, and
zero owned process or lease remained. Final generated output was 1,268,314 bytes.
No post-release retail content hash was performed.

Status is `ReferencesObservedScriptNotRun`: references are verified, but script
bytes, serialized asset content, package closure, binder qualification and
gameplay remain unproven. `ClosureComplete`, `Ready` and `RuntimeVerified` stay
false. H's single-execution GO is exhausted; no utility phase or retry followed.
The coordinator owns the next separate gate and central GitHub integration.

## I: references verified, utility index empty, restoration confirmed

After independent reader/Plan review, the coordinator authorized exactly one
two-phase invocation of source `da643954`. The [I record](native-validation-i-2026-10-12.json)
retains the actual result: references again passed 4/4 with the same 265-byte CSV,
then the script process printed `ENEMY_SCRIPT_INDEX map=cp_zmb available=0`.
Its one-row manifest reports utility `missing_asset`, size 0, no hash; no
`utility.gscbin` was produced. The native C++ exception is `0xE06D7363` with message
`Enemy script dump incomplete; inspect scriptfile-manifest.csv and the errors above`.
This is not evidence that utility is absent from the game; the index construction
and effective load mode still need source investigation.

Both logs contain all 25 planned zone markers in order: 20 load messages and
five already-loaded messages. The first independent post-run observation listed
only the 20 load messages; its immutable supplement records all 25. The failed
script phase is not accepted by this independent log count. Its capture receipt
has `failure=null`, but native exit 3,765,269,347, root exit 1 and no observation;
the outer runner correctly rejects it. The reference native/root exits are 0.

Both original jobs reached zero members, with closed stdout/stderr drains.
All 107 managed paths were removed and all source identity/size/time/attribute
observations matched. Restoration and stock preservation passed, zero owned
process or lease remained, and owner/Main identities were unchanged. Invocation
time was 30.8595525 seconds; final generated output was 1,273,958 bytes.

The retained 186-byte headless error and 189-byte stderr say a minidump was written,
but no dump exists under the documented output path. Source inspection shows the
C++ headless handler terminates before the dump-writing call; that text is not a
dump witness. No fatal-dialog observer was added to the script phase.

`ReferencesVerified=true`; `ScriptBytesVerified`, imports, asset/script closure,
package readiness and runtime acceptance remain false/unobserved. I's GO is
exhausted. Next authorized work is source plus these small logs only: inspect
where and when the script index is populated and compare reference/script load
paths. No retry, retail reread or automatic stock expansion is authorized.

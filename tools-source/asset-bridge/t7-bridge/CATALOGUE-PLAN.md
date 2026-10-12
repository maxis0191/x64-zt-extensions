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

`Test-T7Catalogue.ps1` initially passed 95 light checks using synthetic files, fake owners
and clocks, with no owner-stock reads, native type loading or real reservation.
It covers report scope/count/name/refusal cases, retained file guards, fixed-plan
and retry refusals, output caps, ordinary root failure, closure quarantine, and
the actual runner finalizer after late release/publication or forced closure.
These pure tests do not qualify the native catalogue path. Coordinator review and a
separate exact-plan GO are required; exhaustive theoretical bootstrap
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

## B correction: only the observed startup paths

The new plan declares `EngineOutputProfile=ObservedStartupA`. It permits an
ordinary `steam_appid.txt` of at most six bytes while the engine is writing it;
after ordinary native closure, acceptance requires exactly the bytes `311210`,
with a read-only guard retained through receipt publication. This avoids stopping
on a legitimate transient zero-length file without accepting different final
contents. An unexpected type or seventh byte still stops the attempt.

Only `identities/`, `identities/dedicatedpc/`, and its empty `dumps/` and `LPC/`
directories are permitted. No other descendant, file or reparse point is allowed.
The adapter never reads an identity/key payload. Any newly observed entry is
preserved privately for diagnosis and cannot trigger an automatic broadening.
The existing total size, 64-entry and time limits are unchanged.

These bounds are a deliberate observation-based policy. No writer for these
paths was found in the pinned C++ sources; the exact closed-engine writer is
unknown. The separate `temp/zt-tlsdll.dll` matches the loader resource name in
`src/zonetool/loader/tls.cpp` and stays under existing temporary-output bounds;
its generated binary has not been read or analyzed after the A reservation.

The corrected adapter passes 112 light checks, including partial/exact/incorrect
app-id contents, final read guard, wrong output types, unlisted directories and a
locked synthetic identity file refused without reading it. Plan B uses the same
four inputs, no additional FF/FD/XPAK, and no larger budget. Its native invocation
requires a new explicit coordinator GO. A's receipt, runtime tree and failure
remain unchanged.

## Attempt B: natural exit 0 without a catalogue

The coordinator authorized one B invocation at source `5b64e86`, plan SHA256
`bc5de39e59a5f2ba8a8139570e33cc79075d27d4a46e7a845e36d701c52594ed`.
The native stage lasted 2,180.25 ms and exited naturally with code 0. The new
startup-output checks passed; the complete original job closed without a forced
stop or quarantine. Input hashes, metadata and file IDs were reverified while the
6/8 GiB reservation and guards remained held, then the lease was released.

No catalogue was created. The runner correctly records Failed/NoCatalogue with
`No qualified catalogue was produced.` stdout contains only 70 bytes announcing
`[ INFO ][ zonetool::t7::init_zonetool ]: ZoneTool is initializing...`; stderr is
empty. This log marks entry into initialization, not its successful completion,
original-engine-init return or command dispatch. No missing filename was reported.
The six-byte app-id file and empty identity-directory shape match A; no identity
payload was present or read. No additional FF, FD or XPAK was added.

Postflight at 13:34:00 UTC found zero leases/heavy workloads and no original root,
with Main and the preserved Python generation unchanged. Source/alias metadata
and identities still matched. The host exited normally after its AppDomain
quarantine check; host and candidate were absent at 13:34:11 UTC. Four hardlinks
and private logs/receipts remain retained. The
[sanitized B record](catalogue-runtime-b-20261012.json) binds this evidence.

The build owner is inspecting the actual prepared D2 path from initialization to
command parsing and exit. No compatible-engine conclusion, automatic retry,
speculative bootstrap file or new native probe follows from exit 0 alone.

## C preparation: qualify the instrumented catalogue candidate

`CandidateProfile=t7-catalog-trace` is a narrowly qualified alternative to the
exact ordinary D2 candidate. Missing `CandidateProfile` retains D2 semantics;
unknown profiles and diagnostic candidates remain refused. The CLI stays
`-t7-iw7-catalog mp_freerun_04`, with three arguments including the executable.
The existing H1 owner, limits, admission, aliases and closure code are reused.

The trace path requires its own closed Passed build receipt and pinned build
plan. Both must carry the exact eight-field BuildProfile: Name, Option,
ArgumentCount, TraceSchema, Wiring, PreparedMain, BaseBuildPlan and
BaseBuildReceipt. All four provenance pins must match the receipt, build and
catalogue text bindings. The original D2 plan/receipt hashes remain fixed.
The retained failed-compile provenance must match D2; only its zonetool11/xpak
objects are retained. The new receipt must contain successful, closed main
Compile and link Link stages tied to its own plan. The pinned compiler
dependencies identify the prepared trace main, and the existing pinned link.rsp
consumes that new main object exactly once. Candidate bytes/hash come from the
actual Link artifact. The catalogue preparer does not rehash objects, EXE or
stock outside native admission.

The build owner's completed trace A receipt is 14,430 bytes, SHA256
`6a886fd9befa29b35ef220efa4cfb011a45cd0fd30bdcaff8a9b3374d0df73b3`, for build plan
`0a6af99207b0b35bdf689a7378af3e1760bfd06e2da870fc1e1c9e5164462d31`.
Its actual EXE is 21,741,056 bytes, SHA256
`1034faa2f198f3edc367e6f5d6c24059bddb6962f9950a347400e6108f3b60b0`.
The receipt reports Passed, InputsReverified, TreeClosureConfirmed and
LeaseReleased, with CandidateExecuted and Quarantined false. These are build
observations, not a catalogue runtime result. See the build owner's BUILD-PLAN.

For this candidate only, stderr must contain at most one of each of six known
`[T7_CATALOG_TRACE] schema=iw7.t7-catalog-trace/1` events: enabled,
before_post_unpack, after_post_unpack, before_entry_point, entry_point_return,
exit_hook. Every line is below 256 bytes, total below 1,536 bytes. The reader
accepts LF/CRLF, canonical DWORD thread IDs, int32 codes and 16-digit hex return
addresses. Non-exit pointers and pre-call codes must be zero. Unknown output,
duplicates, incomplete lines, byte-order marks and unsupported encodings are
refused. Failed setvbuf flags are recorded as observed; they do not prove that
buffering succeeded. Event order is recorded without inventing causality.

TraceObserved means the enabled marker and any present events are structurally
valid. It never proves a catalogue, successful dispatch or compatibility. A
trace alone remains Failed/NoCatalogue. Malformed trace does not suppress the
independent catalogue and input checks. After forced closure only bounded trace
and catalogue diagnostics are inspected; payloads are not rehashed after lease
release. Unclosed jobs retain their owner and lease without inspecting output.

Validation: 126 catalogue checks and 123 trace/provenance checks pass using
synthetic files and mocked job/provenance readers. No native types, real lease,
native process or owner stock were used. These tests include strict D2/unknown
refusals, provenance mutations, malformed trace and finalization outcomes.
The exact private Plan C must still pass default validation and coordinator
review before its single native invocation. No new Run is authorized by this
source change; A and B remain consumed Failed attempts.

## C preflight refusal and explicit stopped-Main baseline

Plan C (`4f8cf5a7015080f9280620b5d64b650ebdb3255adca0bd5251655bcf4a1f1845`)
passed source validation but its live preflight found the original Main PID,
expected executable path and UDP27016 absent at 14:11:52 UTC. A second observation
at 14:12:50 UTC matched. Python's preserved generation remained present. The cause
of Main's absence is unknown; no crash or owner action is inferred. C never
created an attempt marker, launched a host/candidate or acquired a lease.

The coordinator separately authorized and reviewed the minimal `4be5bae` delta.
`MainBaseline=Stopped` explicitly requires the old PID to be absent, no process
at the expected Main image and no UDP27016 endpoint. An inaccessible same-name
image, reused old PID, new matching instance or mixed state refuses the check.
The baseline is recorded before admission, immediately before launch and after
confirmed closure, including forced closure. An unknown baseline is refused;
omitting it retains the original exact running-generation/UDP-owner helper.
No shared prepatch helper, other guard, input or resource threshold changed.
314 light/pure checks passed: catalogue139, trace123 and Main52.

## Attempt D: post_unpack returned, then another thread called exit_hook

The unique coordinator GO used source `4be5bae7dbc78c3a560c255cb8ca3bbd65e89ab3`
and Plan D `eb02c7603af92ad026e426784dd2556061be96839cf92e0490d51e5039ded656`.
Fresh preflight at 14:20:50 UTC confirmed Main Stopped, the preserved Python
identity, zero leases/heavy work and admission capacity for 6/8 GiB. The runner
acquired its own atomic reservation and ran only the existing four input aliases.

The native root exited naturally with code 0 after 2,192.60 ms. The outcome stays
**Failed / NoCatalogue**. stdout is the same 70-byte init_zonetool message as B.
The 600-byte bounded stderr trace records, in order:

| Event | Code | Thread | Return address |
| --- | --- | --- | --- |
| enabled, stdout/stderr unbuffered both true | n/a | 31804 | n/a |
| before_entry_point | 0 | 31804 | 0 |
| before_post_unpack | 0 | 31804 | 0 |
| after_post_unpack | 0 | 31804 | 0 |
| exit_hook | 0 | 18184 | `0x140AC00C4` |

No entry_point_return event or catalogue was observed. This establishes a return
from the instrumented post_unpack call and a later observed exit_hook invocation
on another thread. It does not establish the engine's reason for exiting,
original initialization completion, command dispatch, ABI compatibility or a
missing dependency. No extra FF, FD, XPAK or bootstrap input was introduced.

The original job closed without a forced stop or quarantine. All input/alias
hashes, metadata and identities were reverified while the lease remained held.
After release, only bounded text diagnostics and metadata/file IDs were read.
Main remained Stopped before/after. Postflight at 14:22:51 UTC confirmed zero
leases/heavy workloads/original root, unchanged source/alias metadata and IDs,
the preserved Python generation and no host quarantine. The persistent host
exited normally with code 0; host and candidate were absent at 14:23:20 UTC.
The host's code 0 is the worker's retained exec-session 34424 result. The small
host-outcome/absence JSONs establish closure and absence, not that exit code.

The [sanitized D checkpoint](catalogue-runtime-d-20261012.json) binds C's refusal,
D's trace, receipt and postflight evidence. A/B/D remain Failed and C unconsumed.
The build owner now correlates the exact prepared source and exit return address.
No automatic retry, new native invocation, binary analysis or added input follows
from this observation; any subsequent native experiment needs a separate plan/GO.

## Exit-context reader: source-only qualification

The subsequent source investigation could not name `0x140AC00C4` from the
retained captures. The coordinator authorized a separately versioned, bounded
context at the first exit_hook. The build owner owns instrumentation and build;
this adapter only qualifies its provenance and parses the local diagnostics.
No new native invocation or successful context capture is claimed here.

The new explicit candidate profile is `t7-catalog-exit-context`. Its BuildProfile
has the same eight trace fields plus
`ContextSchema=iw7.t7-catalog-exit-context/1`. All four source/base pins, retained
compile provenance, new main Compile/Link stages and actual candidate-artifact
checks remain required. Existing ordinary D2 and `t7-catalog-trace` acceptance
are unchanged. The six original markers retain `iw7.t7-catalog-trace/1` exactly;
their reader still rejects an incomplete marker, unknown fields or 1,536 bytes.

Only the new profile permits total stderr at most 4,096 bytes and nine lines.
After the first exit_hook, up to three new lines use `[T7_CATALOG_EXIT]` and the
context schema, in memory/stack/function order. Every complete line must match
the exit marker's code, thread and return address. Per-line caps are 1,024 bytes
for memory and 512 each for stack/function. Duplicate kinds, reordered lines,
unsupported statuses, mismatched lengths and unrelated stderr are refused.

| Kind | Bounded content | Qualification |
| --- | --- | --- |
| memory | 256 requested bytes starting at RA minus 64; 0..256 returned bytes | Exact uppercase hex length; explicit status/error; successful capture requires expected module/allocation, committed readable region and complete window |
| stack | 0..8 addresses | Exact count and uppercase 16-digit addresses; failed/empty capture has zero addresses |
| function | 0..12-byte RUNTIME_FUNCTION copy from lookup of RA minus 1 | Exact RVA widths/status; success requires full record containing RA minus 1; incomplete/failed copies expose zero RVAs except explicit complete record_invalid observations |

The context reports Absent, Partial or Observed independently of TraceObserved
and catalogue qualification. Observed requires all three complete captures with
status ok; every non-ok status remains explicit in Partial. A recognizable final
context line cut off before its newline is marked incomplete and does not discard
earlier complete captures. Malformed completed lines remain refused. The original
marker parser is unchanged, including the five-event D regression fixture.

Captured bytes are retained only in private bounded stderr/receipt files. No
runtime memory bytes belong in Git checkpoints, redistributable artifacts or
public reports. Tests use invented repeated AB bytes only. No global dump,
unwind-data traversal, .pdata scan or new payload input is introduced by this
reader. A context alone, including a complete one, cannot make NoCatalogue pass.

497 light/pure checks pass: catalogue153, trace/provenance131, context161 and
Main52. The runtime owner, admission, source guards, closure, quarantine, Main
baseline and independent catalogue checks remain intact. The next executable
plan must bind the actual newly built candidate and its Passed receipt; synthetic
test identities cannot stand in for those artifacts. A/B/D remain Failed, C
remains unconsumed and no further build/Run is authorized by this source change.

## Attempt E: complete exit context, still no catalogue

After review of the real context build and the protection-guard correction, the
coordinator authorized one invocation of Plan E
`2cc54a561ac944da036e72bbac6bbc6b48b59a310e1c7c08508b09026a716efb`, using source
`90d28e45c74971a775952042368e997ec8775818`. The actual candidate is 21,744,640 bytes,
SHA256 `f3408671d392b97e3ca09bc3e6e294c761813feccd18d8a1aaa4920874be2847`, from
build plan `0cd2c2f3bdc22021a045d53bec19988b912c8d3db095e02eef061ebfa201880b` and
Passed build receipt `3366373d1cf91e30634bfb3367133bee99771ca2b2cb9c794c7ced784cc9f6b0`.
The fresh preflight confirmed Main Stopped, the preserved Python generation,
zero leases/heavy workloads and capacity for the unchanged 6/8 GiB reservation.

The native root exited naturally with code 0 after 1,964.83 ms. E remains
**Failed / NoCatalogue** with the same 70-byte init_zonetool stdout message.
The 1,917-byte stderr is structurally qualified as TraceObserved and
ExitContext Observed. The same five trace phases as D were observed: enabled,
before_entry_point, before_post_unpack, after_post_unpack, then exit_hook.
The first four use thread 3848; exit_hook uses thread 24404, code 0 and return
address `0x140AC00C4`. No entry_point_return or catalogue was observed.

All three context records completed with status ok and error 0:

| Capture | Observed metadata |
| --- | --- |
| memory | 256/256 bytes from `0x140AC0084`, expected module/allocation `0x140000000`, committed region, protection 64 |
| stack | Eight addresses, retained in the private receipt and sanitized address metadata |
| function | Full 12-byte record; function range `[0x140ABFF48, 0x140AC00DD)`, unwind RVA `0x0105C178` |

The existing Capstone installation decoded only those captured 256 bytes after
the host was closed. The six-byte indirect call at `0x140AC00BE` ends at the
reported return address and references the pointer slot `0x14B4BD078` relative
to RIP. The instruction at the return address is int3. The slot's contents,
EXE/PDB and any additional memory were not read. The initial window starts
inside a function, so its initial instruction alignment remains unproven.
These observations alone do not name the function or establish why it exits.
The build owner owns subsequent source/cause correlation; no further analysis
or runtime is implicit in this checkpoint.

Closure and lease release succeeded without forced stop or quarantine. Inputs
and aliases were reverified under admission. Postflight at 15:07:49 UTC found
zero leases/heavy workloads/original root, equal metadata and file IDs, Main
still Stopped and the same Python generation. The original bank, Main process
state and input set were not changed by this invocation.

Two distinct witnesses establish host closure. First, `tools.write_stdin` for
the persistent terminal **session 12428** returned **exit code 0**, chunk
`6fdf98`, after the guarded exit command for host PID 25580. The private
`host-session-exit.local.json` records this observed tool result; it is not an
inference from PID absence. Separately, a subsequent process inventory at
15:08:08.6666893 UTC found host 25580 and native root 14448 absent, recorded in
`host-absence.local.json`. Both witnesses have separate hashes in the
[sanitized E checkpoint](catalogue-runtime-e-20261012.json).

The checkpoint includes only statuses, addresses, sizes and evidence hashes.
Raw captured bytes, full stderr/receipt and disassembly remain in ignored local
evidence. A/B/D/E remain Failed, C remains unconsumed, and no additional runtime,
capture expansion, dependency input or automatic retry is authorized.

## Caller reader: source-only qualification after E

The coordinator authorized the build owner to instrument the three caller
addresses already observed in E, and this adapter to qualify the separate
`t7-catalog-callers` profile. Producer source is
`39933eb35f85c0267a75138330ecf9da81a90ed4`. This checkpoint only changes source,
tests and this document; no caller candidate, native capture or runtime plan is
created by the adapter. The build owner owns any build plan and candidate.

BuildProfile has exactly ten fields: the eight original trace fields plus
`ContextSchema=iw7.t7-catalog-exit-context/1` and
`CallerSchema=iw7.t7-catalog-callers/1`, with Name `t7-catalog-callers`.
The option, argc 3, four guarded source/base pins, retained D2 compile chain,
new main Compile/Link provenance and actual candidate-artifact checks remain
required. The original trace and EXIT /1 parsers and their caps are unchanged.

Only this new profile permits stderr up to 8,192 bytes and twelve lines. Its
three `[T7_CATALOG_CALLER]` records follow all three EXIT records, in index order
0/1/2, and target only `0x140584FD8`, `0x1401DA015` and `0x140526D02` respectively.
Each record is capped at 2,048 bytes. Producer format tests calculate at most
1,546 bytes per caller and 6,911 bytes for all twelve lines including CRLF.

The reader checks code, thread and exit return address against the original
exit_hook, and frame against the first matching occurrence in the existing
stack capture. An unavailable stack requires stack_unavailable; a missing
target requires absent. Both have frame -1 and zero lookup/read metadata.
No target is accepted merely because it appeared in the historical E stack.

For an attempted code copy, the complete 12-byte function record must contain
RA minus 1. Expected module, image and allocation are `0x140000000`; the code
region must be committed and readable, with checked address arithmetic. A
function of at most 512 bytes wholly inside that region uses scope full.
Otherwise scope window must equal the intersection of `[RA-448, RA+64)`, the
function and the region. The intersection must contain RA minus 1. Exactly
`2 * read` uppercase hex characters accompany a nonzero copy, up to 512 bytes
per caller; a zero copy uses `-`. No unwind payload or RF-region observation is
inferred from fields that the producer does not expose.

Explicit refusals remain diagnostic evidence. Partial/failed RF copies zero
RVAs; record_invalid can retain an invalid complete record. A post-RF
region_invalid may retain the valid complete RF but has no code window.
SEH exceptions preserve bounded metadata/copies while zeroing RVAs. The
producer's serialization clamp is represented by read_failed/error 13 with
start/requested/read zero and scope none. None of these statuses is Observed.

CallersOutcome is independent of TraceOutcome, ExitContextOutcome and
CatalogueOutcome: Absent without caller evidence, Partial for incomplete or
non-ok captures, and Observed only with three complete correlated ok records.
A recognizable final caller line without its newline preserves preceding
complete records as Partial. An ambiguous truncated prefix before the three
EXIT records remains the legacy reader's responsibility. Malformed completed
records, duplicate/reordered indices and unrelated stderr are refused.

All 756 light checks pass: catalogue/lifecycle 169, trace/provenance 165,
EXIT 161, Main 52 and callers 209. The initial empty-stderr test exposed
PowerShell empty-array unrolling; an explicit array wrapper corrected it.
Review also identified and corrected ambiguous short-prefix truncation, with
regression cases. Tests use invented AB bytes and ranges, synthetic private
stderr and in-memory provenance objects. They load no native type, create no
native job or lease, and read no stock. Caller Observed/Partial and forced-close
paths are exercised through the existing finalizer; NoCatalogue stays Failed,
and forced closure does not rehash stock after release.

Run-T7Catalogue and all shared ownership/resource helpers are unchanged. The
new profile is dispatched by the already guarded adapter. Raw code bytes stay
in ignored private stderr/receipts only; they must not enter Git checkpoints or
public artifacts. Independent source review and a real Passed build receipt
are still required before any separately authorized runtime plan can be sealed.

## Attempt F: complete caller context, still no catalogue

The coordinator separately reviewed and authorized one invocation of Plan F
`103f912daa09429c8afcba099c2b28a23afb95502757e995db448d99bf1152fe`
(10,750 bytes), using adapter source `78f134c1ff7df86f13ffdec2f4f0b609a3650e7b`.
The actual callers candidate is 21,747,200 bytes, SHA256
`01aa3310e92a1e458005de044c582c302c12149a81bf7fce23b7cc5ae153bbd4`, from build
plan `455b67c2862105ce5670f9cb2fefb26ba8e86f0167481ae7a1d8cc7f1a1e1b20` and
Passed receipt `9f8b8bc235bd52429a915bb1f1d3fc3ca0afd6b852e8897dfc312d566166aa99`.
Its build and host had closed before runtime admission. Preparation and default
validation read only bounded text and metadata; payload hashes were checked
under the runtime lease. The same zone, arguments, four aliases and 6/8 GiB,
200/120/5-second safeguards were retained, with the reviewed 8,192-byte stderr
cap. The fresh preflight at 15:41:34 UTC found no lease/heavy workload, Main
Stopped, the exact preserved Python generation and an allowed resource budget.

F remains **Failed / NoCatalogue**. The native process exited naturally with
code 0 after 2,146.80 ms, with the same 70-byte init_zonetool stdout message.
The 4,565-byte stderr qualifies as TraceObserved, ExitContext Observed and
Callers Observed. Its original phases are enabled, before_entry_point,
before_post_unpack, after_post_unpack and exit_hook. The first four use thread
15060; exit_hook uses thread 27900, code 0 and return address `0x140AC00C4`.
No entry_point_return or catalogue was observed.

Each caller has status ok/error 0 and a complete 12-byte function record.
Their frame indices are the first occurrences in the newly captured stack.

| Index / frame | Return address | Function range, end exclusive | Captured code |
| --- | --- | --- | --- |
| 0 / 4 | `0x140584FD8` | `[0x140584F50, 0x1405850DF)` | full, 399/399 bytes from `0x140584F50` |
| 1 / 5 | `0x1401DA015` | `[0x1401D9FE0, 0x1401DA135)` | window, 85/85 bytes from `0x1401DA000` |
| 2 / 6 | `0x140526D02` | `[0x140526C80, 0x140526D20)` | full, 160/160 bytes from `0x140526C80` |

The second window is clipped to its observed region and RA-relative bounds;
it is not a full-function capture. In total, the caller records contain 644
code bytes and 36 function-record bytes. The original three EXIT captures also
completed. This adapter only records their qualified metadata: worker 51 alone
owns subsequent decoding and cause analysis. No function name, exit cause,
model export or engine compatibility follows from these diagnostics alone.

Closure, release, engine-output checks, all input revalidation and original
metadata checks succeeded without forced termination or quarantine. Postflight
at 15:42:46.1499719 UTC found zero leases/heavy workloads/original root, four
equal input-metadata records and eight equal source/alias identities. Main
remained Stopped and Python 23352 retained its exact creation/image identity.

Host PID 9028 was created at 15:41:43.8259667 UTC; native root 34564 was created
at 15:42:19.7421835 UTC. The host's guarded exit produced a real
`tools.write_stdin` completion for **session 89803**, chunk **a311f7**, with
**exit code 0**. `host-session-exit.local.json` records that direct witness.
A separate CIM inventory at 15:43:35.0747163 UTC confirmed both host and root
absent; `host-absence.local.json` records the independent absence witness.
Exit status is not inferred from the absence observation.

The [sanitized F checkpoint](catalogue-runtime-f-20261012.json) retains only
metadata and evidence hashes. Raw bytes remain in ignored local stderr/receipt
files and were handed to worker 51 after complete closure. No decoding occurred
in this adapter chat. A/B/D/E/F remain Failed and C remains unconsumed. No retry,
extra zone input, expanded capture or further native invocation is authorized
by this checkpoint.

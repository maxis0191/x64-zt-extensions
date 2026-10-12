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

## Message reader: source-only qualification after F

The coordinator authorized a fifth profile, `t7-catalog-message`, following
worker 51's bounded caller analysis and a separate review of the producer
design. This adapter owns the reader, provenance checks and pure tests only.
There is no message build, candidate, runtime plan or native invocation in
this source checkpoint. The producer's fixed callsite and signature safeguards
are its responsibility; this reader does not patch or read engine memory.

BuildProfile has exactly eleven fields: the ten caller fields plus
`MessageSchema=iw7.t7-catalog-message/1`, with Name `t7-catalog-message`.
The same option/argc, guarded Wiring/PreparedMain/base pins, actual main/Link
receipt and candidate provenance checks remain required. No extra runtime
argument or configurable callsite is introduced. Ordinary D2, trace /1,
EXIT /1 and CALLER /1 retain their existing readers and exact profile fields.
Run-T7Catalogue and shared ownership/resource helpers are unchanged.

Only this profile admits two additional `[T7_CATALOG_MSG]` records under the
fixed schema, for at most fourteen lines and 8,192 bytes of stderr. The closed
grammar permits one install and one buffer record, with canonical decimal
uint32 thread/error fields. Install status is restricted to the agreed set;
installed requires error 0. A complete installation record must follow
before_post_unpack and precede after_post_unpack when that marker exists.
Its thread is independent of the eventual exit winner.

A buffer requires a preceding successful installation. It may arrive during
post_unpack, before after_post_unpack. A same-thread buffer must precede its
exit_hook. A missing exit marker or a different exit thread retains useful
diagnostics as uncorrelated Partial rather than fabricating an association.
Duplicate records, unknown fields/schema/statuses and invalid order are refused.
Recognizable final MSG lines truncated before their newline remain incomplete;
an ambiguous short prefix first remains eligible for the legacy EXIT/CALLER
reader at its current stage. Completed installation without its preceding
boundary is refused; a truncated installation cannot become Observed.

The buffer requests at most 384 bytes. Read cannot exceed requested, and length
cannot exceed read. With nul 1, length is strictly smaller than read; with nul
0, length equals read. Exactly twice length uppercase hex characters represent
the bytes before the first NUL, or `-` for zero length. An aligned `00` byte in
the serialized payload is refused. Bytes remain opaque and private: the reader
does not assume an encoding, turn them into text, or publish their contents.

| MessageOutcome | Required evidence |
| --- | --- |
| Absent | No MSG record or recognizable incomplete MSG line |
| Partial | Refused installation, missing/incomplete buffer, capture error, missing exit or different exit thread |
| Prefix | Installed, full bounded read without NUL, same-thread buffer before exit_hook |
| Observed | Installed, status ok, full bounded read with NUL, same-thread buffer before exit_hook |

A NUL on partial, read_failed or exception never upgrades the outcome. The RPM
false-with-full-count case remains read_failed. The serializer's impossible
count clamp is read_failed/error 13 with all counts zero. Pre-read refusals
have zero counts, nul 0 and no payload. Exception may preserve bounded useful
bytes but remains Partial. Prefix is not a complete message, and neither Prefix
nor Observed establishes catalogue success or an engine-error cause.

All 1,029 pure/light checks pass: catalogue/lifecycle 188, trace/provenance 209,
EXIT 161, Main 52, callers 209 and message 210. They cover both legal buffer
positions, independent installation thread, competing exit winner, every
installation refusal and capture state, NUL/count mismatches, truncation,
duplicate/order refusals and a complete fourteen-line envelope with maximum
caller payloads and a 384-byte message prefix. Tests contain only invented
opaque bytes and synthetic text. The finalizer still reports NoCatalogue as
Failed for Observed, Prefix and Partial messages; forced closure inspects only
bounded diagnostics after release, without rehashing stock.

The next gate is independent source review of both producer and reader. A real
Passed build and separately reviewed exact runtime plan are still required
before any new native invocation. Captured hex or decoded message text must
remain in ignored private evidence, never Git checkpoints or public artifacts.

## Plan G: preflight refused after the Main generation changed

Following independent source/build/plan review, the coordinator authorized one
native invocation of Plan G
`047ee1aa5df8f514e598b837b835639d843dfc36ae64f69dfff9cb2138c7a4d3`
(10,750 bytes). It binds the actual message candidate, 21,750,272 bytes with
SHA256 `57168e99d3dd004e83a531905efe5354a8d29e39592786e3f81b5dd4cd5ce05a`,
from Passed build receipt
`4001a1ed0a320bea393bed3e5ca4f17c8a9c0c1feb3ec43f6b4fc0761ccb3ae6`.
The preparation snapshot at 16:18:48 UTC had observed Main Stopped and an
allowed 6/8 GiB budget; that snapshot was explicitly not runtime admission.

The fresh preflight passed default text/metadata validation, then refused
`Stopped Main baseline differs or is ambiguous.` before creating a persistent
host, taking a runtime lease or invoking Run. At 16:23:17.5341169 UTC, a new
`iw7-paris-voice.exe` process with PID 19932 and creation time
16:21:08.1996220 UTC matched the preserved absolute image path and owned UDP
27016 on `0.0.0.0`. The old PID 27784 was not observed. The start actor and
occupied state were not established; no inference about them is needed to
honor the failed baseline guard.

G remains **unconsumed / PreflightRefused**, with zero native invocations,
no attempt marker and no runtime receipt. There is no G message or catalogue
result to interpret. No payload was read/hashed, no alias was created, and the
plan, observed Main process, bank and network were not modified. Both the
coordinator and build owner were informed. The
[sanitized refusal checkpoint](catalogue-preflight-g-20261012.json) pins the
small private observation without publishing machine-specific paths.

Continuing under a different Main baseline requires a separately sealed plan,
review and exact GO binding the new process identity. Do not silently relabel
the existing G plan as Running, reuse its prior preparation as admission, or
stop the observed Main process to satisfy the plan. No further invocation is
authorized by this refusal checkpoint.

## Plan H: Running baseline prepared, commit headroom refused

H is a separately sealed preparation, 10,774 bytes with SHA256
`1ebd9196d18f6f2182ab4a2544eac68c704776e8dcb15fe48a44c19c3a494433`.
It reuses G's message candidate/build receipt, source bindings, zone, arguments
and 6/8 GiB, 200/120/5-second limits. The existing parameterized Running helper
needs no source change. At 16:27:42.6037227 UTC on 2026-10-12, PID 19932,
created at 16:21:08.1996220 UTC, matched the expected image path and owned UDP
27016. This establishes the process generation and endpoint, not its binary
contents, start actor or occupied state.

The preparation snapshot at 16:27:43.5288340 UTC refused the unchanged budget:
commit was 43,075,686,400 / 47,564,615,680 bytes (90.56%), physical usage 77.4%,
and HighWater true. Physical reserve remained zero and commit reserve remained
9,512,923,136 bytes. Zero leases/heavy workloads and the preserved Python
generation were observed. This dated preparation check is **not runtime
admission**. Default validation returned PlanCheckedPendingGO; the 52 light
Main checks passed during preparation.

The sealed G-to-H delta has seven intentional field changes for the new paths
and Running identity. Its eighth textual difference only removes a trailing
zero from the candidate metadata timestamp; equality at 100 ns precision was
verified. All other fields and bindings are unchanged. The
[sanitized H checkpoint](catalogue-preparation-h-20261012.json) retains the
plan, delta and snapshot pins without private absolute paths or payloads.

H has **zero invocations**, no persistent host, runtime lease, attempt marker,
runtime receipt or captured message. No GO H has been given. G remains
unconsumed; its authorization does not transfer. Preserve H and the candidate,
without repeated measurements, reduced safeguards or changes to processes or
pagefile. A distinct exact GO and a fresh admitted preflight are still required
before a future invocation. This checkpoint only records existing evidence.

## Plan I: dispatch refused before reading a runtime plan

The single requested availability check at 16:48:58 UTC on 2026-10-12 found
Main's recorded PID/image and UDP 27016 absent, with cause unknown. The 6/8 GiB
budget was then available (55.87% committed), but H's Running baseline was
invalid. H and its evidence were preserved. I was separately sealed with a
Stopped baseline using that observation, unchanged original Main identity,
bindings, candidate and limits, and new private directories. Its 10,833-byte
plan hash is `234dc0d788c769e5ddb83cb9d6daa2e9a09d677baf6b4b4aaaef99590e4ff03f`.
Default validation and the 52 pure Main checks passed; replay of the saved
observation accepted I and refused H without a new live measurement.

After exact GO, the real preflight passed at 16:55:06.0316135 UTC: Main Stopped,
Python preserved, no lease/heavy workload, unchanged 6/8 GiB allowed and 53.88%
commit usage. The private dispatch wrapper contained an operator error: its
PlanPath still named F while its supplied hash named I. The runner refused
`Bound input hash/length differs.` in its first text-pin check, before reading
a runtime plan, creating runtime state, taking a lease or loading a native job.
**No native invocation or MSG capture occurred; I remains unconsumed.**

Host 28228, created at 16:55:14.4756166 UTC, returned the refusal and was closed.
The first closure helper omitted the H1 core import; a separate corrected
closure helper completed the checks without rerunning the candidate. The real
session 96726 completion, chunk `0b2ef0`, reported exit 0. An independent
inventory at 16:57:53.9477501 UTC found host and parent 36592 absent, no lease,
and zero I runtime files, attempt markers or candidate aliases.

The [sanitized dispatch checkpoint](catalogue-dispatch-i-20261012.json) pins
the retained erroneous wrapper, refusal, actual exit and independent absence.
A distinct explicit I wrapper passed AST path/argument checks and real default
validation without Run. I, its budgets and candidate remain unchanged. That
correction is pending independent wiring review and a **new explicit GO**;
the refused dispatch does not authorize a silent retry or establish a native
catalogue result. The original erroneous wrapper remains preserved.

## Plan I: corrected dispatch captured the complete MSG record

After independent wiring review and a distinct exact GO, the unchanged Plan I
was invoked once through the explicitly pinned corrected wrapper. Fresh
preflight at 17:04:27.3879210 UTC on 2026-10-12 found Main Stopped, Python
preserved, zero leases/heavy workloads and the unchanged 6/8 GiB budget allowed
at 53.26% commit usage. The runner then performed its own atomic admission.
The previous dispatch refusal and its evidence remain intact.

I remains **Failed / NoCatalogue**, with a natural native exit 0 after
2,246.6043 ms. Trace, EXIT, CALLERS and **MSG are Observed**. Installation is
installed/error 0 on thread 25272. The buffer is ok/error 0 on thread 28892,
with 384 bytes requested and read, 45 useful bytes before NUL, no incomplete
trailing line, and SameThreadBeforeExit correlation. The exit hook has code 0,
thread 28892 and return address `0x140AC00C4`. No entry_point_return or catalogue
was observed. The 4,888-byte stderr hash retained by the runner under guards is
`56f2538ecb2d2b4c3b31a545f9412d099b1942a101bcca27a743a41f46314dd7`.
No binary or capture-payload hash was recalculated after lease release.

The runner confirmed job closure, lease release, input revalidation and engine
output checks without forced termination or quarantine. Postflight at
17:05:07.5548030 UTC confirmed four unchanged input metadata records and eight
matching source/alias identities, zero leases/heavy workloads/original root,
Main Stopped and Python preserved. Native root 33572 was created at
17:04:56.1519471 UTC; host 35524 at 17:04:35.1377251 UTC. Actual host completion
for session 13977, chunk `f4269b`, reported exit 0. Independent observation at
17:05:51.4233562 UTC found that host, parent 35188 and native root absent, with
zero leases. All closure helpers imported their dependencies explicitly.

The [sanitized runtime checkpoint](catalogue-runtime-i-20261012.json) contains
only qualified metadata and small-evidence pins. The private receipt and stderr
were handed to worker 51 after closure for exclusive decoding and interpretation;
the adapter did not decode the capture. Raw hex and decoded message text remain
outside Git. I is now consumed. The next step is review of worker 51's finding
and a separately authorized response; this checkpoint authorizes no retry,
extra input, new build or further native invocation.
## Bootstrap B qualification and Plan J preparation (2026-10-12)

The complete I message led the analysis owner to identify one startup-zone
dependency. An exact 832-byte `en_core_pre_gfx.ff` was qualified separately;
no other FF, prefix, header, alias, copy or native engine was read or created
by that qualification. Two guarded reads established SHA256
`37fa64b205570954c2aec30661f9ee7ad41b8fc490114a3a86907889fb94162c`,
with unchanged file identity, creation time, write time and attributes.
This is **ObservedUnderLeaseNotDepotVerified**. Header semantics, content
compatibility, depot provenance and engine lookup location remain unproved.

The first B dispatch passed a forward-slash `-File` argument to a contract
that requires exact equality with normalized `PSCommandPath`. It refused
before live preflight, lease, marker or payload access. Source guards closed;
session 44110 exited 1 (chunk `99f85e`), and an independent witness found host
and parent absent. The script and this refusal were preserved. A distinct GO
authorized the literal Windows-path correction, with no source change.

Corrected B admitted 6/8 GiB at 17:49:41.3646928 UTC, with physical reserve zero
and unchanged commit reserve. Its successful identity/hash-only receipt was
published at 17:49:42.3089216 UTC. The lease was released, guards closed and
quarantine absent. Session 51026 exited 0 (chunk `7ace0c`); the independent
17:50:38.6993542 UTC witness found host/parent absent, zero leases/heavy work,
Main/UDP absent and the preserved Python identity unchanged. No payload hash
was read after release. The [sanitized checkpoint](catalogue-bootstrap-j-20261012.json)
pins both dispatch outcomes and the private qualification/closure evidence.

The existing catalogue runner now accepts an optional explicit `Bootstrap`
only for `t7-catalog-message`. It requires the exact 832-byte binary pin,
qualified file identity, creation/write metadata, and separately pinned
qualification receipt and script. Default validation checks that successful
receipt while text guards are held. After resource admission, the runner
checks the actual file identity under its binary guard and creates the fifth
alias at `work/zone/en_core_pre_gfx.ff` through the existing guarded alias
helper. Existing final input/alias hash, metadata and file-ID verification
also cover this dependency. The output allowlist admits only this additional
declared file. Plans without `Bootstrap` retain their four-input behavior.

Plan J is 12,690 bytes, SHA256
`44bb6204bf695fdb212c7fd342af740f44f95da5a44201c3f87edacc2b1a9f7a`.
It preserves I's MSG candidate/build, arguments, donor zone, stderr cap,
6/8 GiB reservation and 200/120/5-second limits. It has 25 bindings
(19 text, six binary), five input metadata records and five expected aliases.
The total output ceiling increases by exactly 832 bytes to 127,810,264.
Its Stopped Main observation comes from the closed qualification witness;
that dated observation is not runtime admission. I and its runtime evidence
remain unchanged.

All 1,206 pure checks pass, including 177 bootstrap checks and all 1,029
existing catalogue/trace/exit/Main/caller/message checks. A preparation test
caught single-element array unrolling in the output allowlist; explicit
array construction fixed it before applying the source. Default validation
of the sealed J plan reports `PlanCheckedPendingGO`, without payload hashing,
lease, native type loading or runtime files. No J Run has occurred. The next
step is independent review and a distinct exact GO after the competing heavy
group closes, followed by fresh admission. No catalogue or model export is
claimed by this preparation.

## Plan J: new named startup dependency, complete runtime closure

After independent source/plan/dispatch review and a distinct exact GO, J was
invoked once. Fresh preflight at 18:01:14.9362851 UTC admitted the unchanged
6/8 GiB estimate at 52.81% commit use, with physical reserve zero, the unchanged
commit reserve, no lease/heavy workload, Main Stopped and Python preserved.
The actual persistent-host arguments matched the reviewed launch command;
the dispatcher bound the exact J path/hash and reviewed runner. No new probe,
candidate build or speculative input was added.

J is **Failed / NoCatalogue**, with a natural native exit 0 after
2,194.033 ms. Trace, EXIT, CALLERS and MSG are Observed. The message installation
is installed/error 0 on thread 6172. The buffer is ok/error 0 on thread 23636,
with 384 bytes requested/read, a 42-byte NUL-terminated message, no incomplete
trailing line, and SameThreadBeforeExit correlation. The exit hook reports
code 0 and return address `0x140AC00C4`. These are diagnostic observations,
not successful engine initialization or catalogue production.

Worker 51 alone decoded/interpreted the bounded private capture after closure.
The first complete correlated error names the missing **`core_pre_gfx`** zone.
I had named `en_core_pre_gfx`; J therefore changed the first named failure
after the single localized-bootstrap addition. The 70-byte stdout contains
only initialization-start output. The initialization-complete marker and
model-catalog marker are absent. This does not establish full validity of
the localized FF, its complete lookup path, or an exhaustive dependency list.
Raw message bytes, captured hex and absolute machine paths remain private.

All five input metadata records and ten original/alias file identities matched
in postflight. The runner reverified their hashes under its lease, confirmed
native tree closure, released the lease and disposed its guards before return.
No quarantine was present. The first closure helper rejected an equal creation
time because JSON had converted the timestamp to `System.DateTime` before a
string comparison. The original helper is preserved; a distinct correction
compares UTC ticks exactly (`639274249169605724`) and passed every closure check
without another native invocation.

Host session 65217 exited 0 (tool chunk `edc24d`). The independent witness at
18:04:19.8994175 UTC found host 19432, parent 30128 and native root 10828 absent,
zero leases/heavy workloads, Main/UDP absent and the preserved Python identity
unchanged. No payload hash was read after release. The 14,157-byte receipt and
4,877-byte stderr are retained; the stderr hash in the checkpoint comes from
the guarded runtime receipt. The [sanitized J runtime checkpoint](catalogue-runtime-j-20261012.json)
pins the dispatch, preflight, postflight, actual exit, independent absence and
both closure-helper versions.

The minimal proposed next step is qualification of only the newly named
`core_pre_gfx.ff`, after a distinct coordinator decision and available resource
slot. The earlier metadata inventory lists 22,351,168 bytes; it is a historical
snapshot, not fresh identity/content/hash evidence. Nothing in this checkpoint
opens that payload, implements a new probe, changes J or authorizes a retry.
Because the failed name changed, the conditional exact-open-path diagnostic
for a repeated `en_core_pre_gfx` failure is not justified by this result.

## Core Bootstrap A qualified; explicit two-item Plan K prepared

After J's new named failure, the analysis owner observed only the exact
`core_pre_gfx.ff` metadata and ancestors. A separately reviewed qualification
then received its own exact GO. Fresh preflight at 18:15:16.0541313 UTC admitted
the unchanged 6/8 GiB reservation at 53.08% commit use, with physical reserve
zero. Two guarded reads of exactly 22,351,168 bytes established SHA256
`5016669dba3eab765999bd2d0fdcda01c336f4fe2ea6ee8670c61c48107d97ce`.
File identity, creation/write metadata and attributes matched before/after.
No header, prefix, copy, alias or engine invocation was part of qualification.
The hash is observed under lease, not depot verified; content compatibility
and engine lookup remain unknown.

The successful identity/hash-only receipt was finalized at 18:15:17.0534247 UTC.
Guards closed, the lease released and quarantine was absent. Session 64360
exited 0 (chunk `1f74c6`); an independent 18:15:58.1916795 UTC witness found host
22852 and parent 28012 absent, no lease/heavy workload, Main/UDP absent and
Python's preserved identity unchanged. No payload hash was read after release.
The [sanitized qualification/K checkpoint](catalogue-core-bootstrap-k-20261012.json)
pins the script, receipt, closure and independent absence evidence. The reviewed
qualification retained B's five lifecycle functions unchanged and passed the
same 54 pure host/finalization/release checks before the one real invocation.

The catalogue profile now normalizes the legacy `Bootstrap` object or an
explicit `Bootstraps` array through one shared collection path. The new array
accepts exactly `en_core_pre_gfx.ff` (832 bytes), then `core_pre_gfx.ff`
(22,351,168 bytes), with distinct pinned qualification receipts/scripts and
exact per-item hashes, file identities and metadata. Mixed schemas, unknown,
duplicate, reordered or additional items are refused. The getter validates
the entire collection before publishing any item; a focused fixture verifies
that an invalid second item cannot expose the first to a pipeline consumer.
Existing receipt validators, binary guards, identity checks, alias creation
and final revalidation are reused for each declared item. There is no scan,
automatic dependency discovery or duplicated execution pipeline.

Plan K is 14,736 bytes, SHA256
`cd14c1d897ce7317bf07fca4794189be0f1ce5cb9c0b7e3a5557e7a465170dc0`.
It retains J's MSG candidate/build, arguments, donor zone, stderr cap and
6/8 GiB, 200/120/5-second limits. Its 28 bindings comprise 21 text and seven
binary inputs; six metadata records imply six runtime aliases and twelve
original/alias file-ID checks. The output ceiling rises by the new dependency's
22,351,168 bytes to 150,161,432. J, the localized bootstrap and both completed
qualification receipts remain unchanged. K reuses the closed qualification's
Stopped Main snapshot; fresh identity/capacity checks are still required.

All 1,301 source checks pass: 95 new collection checks and all 1,206 existing
checks. The sealed K default validates both actual qualification receipts
under text guards and returns `PlanCheckedPendingGO` without binary hashing,
native types, lease or runtime files. K's prepared work/evidence/temp directories
remain empty. No K Run, new build, catalogue or model export is claimed.
The next action is independent review and a distinct exact GO after the
current heavy workload closes; this preparation does not authorize execution.

## Catalogue K: one attempt, no catalogue, closure independently confirmed

Following the distinct coordinator GO, the exact reviewed K host command and
pinned dispatcher were used once. Fresh preflight at 18:26:13.0381826 UTC
qualified the unchanged 6/8 GiB reservation at 54.54% commit use. The two
qualified bootstrap aliases and all other inputs were guarded under admission.
The run started at 18:26:46.5244504 UTC and finished at
18:26:50.2309737 UTC. The native root exited naturally with code 0 after
2,354.75 ms.
The result is `Failed / NoCatalogue`, not catalogue success or readiness.
TRACE, EXIT, CALLERS and MSG observations were accepted; the correlated bounded
message is 43 bytes and NUL terminated. Raw message/code bytes remain private
for interpretation by the analysis owner.

Tree closure, lease release, output validation and final input revalidation
completed before wrapper return at 18:26:50.2681373 UTC. Same-host postflight
at 18:30:36.2771848 UTC confirmed six unchanged metadata records, twelve equal
original/alias file IDs, no quarantine, and the preserved Python identity.
Guard disposal is supported by the pinned runner's deterministic finally path
before return; it is not a separately observed guard counter. No payload hash
was read after release.

Host session 61384 exited 0 (tool chunk `4c6082`). The independent witness at
18:31:17.7888245 UTC found host 26988, parent 6072 and native root 30928 absent,
with zero leases/heavy workloads and Main/image/UDP27016 still absent.
The initial independent witness command refused a relative JSON path before
its snapshot; the canonical absolute path passed without another native run.
The [sanitized K runtime checkpoint](catalogue-runtime-k-20261012.json) pins
the 15,410-byte receipt, dispatcher, helper, same-host postflight, actual exit
and independent absence. Its stderr hash was recorded under runtime guards.

The analysis owner independently confirmed the receipt hash and identified
`en_core_patch` as the newly missing startup zone. J had named `core_pre_gfx`.
Stdout is still 70 bytes and reports only initialization starting; neither the
initialization-complete marker nor `T7_IW7_MODEL_CATALOG` is present, and the
catalogue JSON/directory are absent. The changed first named failure is
consistent with startup progress, but proves neither complete loading/validity
of the earlier bootstraps nor an exhaustive dependency sequence.

At 18:32:59.2133576 UTC, the analysis owner observed only the exact
`en_core_patch.ff` metadata: 624,640 bytes, with no file/ancestor reparse point.
No payload content, header or hash was read. K is consumed and retained; the
smallest proposed next action is qualification of that named file through the
existing guarded protocol, after a separate coordinator decision and exact GO.
This result authorizes no new bootstrap, payload read, build or engine
invocation and proves no content compatibility.

## En Core Patch A closed; bounded qualified collection and Plan L

The separately reviewed qualification of `en_core_patch.ff` received one exact
GO and reused Core A's five lifecycle functions byte for byte. Its fresh
18:42:49.6349641 UTC preflight admitted the unchanged 6/8 GiB budget at 56.32%
commit use with no physical reserve. Two guarded 624,640-byte reads established
SHA256 `241f1154237ca5459b98e948156f2138a546968a63f92cd13f70cb2e9794906e`;
metadata and file identity matched before/after. The result finalized at
18:42:50.6266957 UTC as `IdentityAndHashObservedCompatibilityUnknown`.
No header/prefix, depot verification, engine invocation or lookup proof was
part of that qualification.

Same-host closure at 18:43:17.2784906 UTC observed both guard collections empty,
lease release and no quarantine. Session 31860 actually exited 0 (chunk
`b834c8`). The independent 18:44:00.0263747 UTC witness found host 6888 and
parent 30648 absent, zero leases/heavy workloads, Main/image/UDP absent, and
the preserved Python identity unchanged. Its first invocation lacked the H1
function import and refused; the corrected read-only witness passed. No
additional qualification was invoked and no payload hash was read after
release. The [sanitized collection/L checkpoint](catalogue-qualified-collection-l-20261012.json)
pins the preparation, qualification, closure and independent evidence.

After full closure, the authorized source change added the explicit opt-in
`BootstrapPolicy: QualifiedCollectionV1`. It accepts one through eight
individually qualified `Bootstraps`, with safe lowercase ASCII `.ff` basenames,
distinct canonical paths/aliases/file identities and per-item receipt/script
pins. Every item validates before any is returned. All guarded receipts still
validate before admission; after guarded runtime ID collection, a new assertion
refuses original-input hardlink collisions before the first alias directory.
No scan, automatic addition or inferred dependency list is used. Absence of
the policy retains the existing exact J/K validators and their 32-binding
ceiling; the consumed J/K artifacts remain unchanged.

The aggregate bootstrap limit is 32 MiB, matching the existing qualification
reader ceiling without multiplying it by item count. Eight is an administrative
review/handle limit, not a claim about the engine's dependency list. Under this
policy the existing 22 MSG bindings plus three per item imply at most 46
bindings, twelve metadata records/aliases and twenty-four original/alias ID
checks. Byte types and remaining aggregate capacity are checked before each
addition; the output limit remains the exact existing base plus candidate and
declared bootstrap bytes. The 6/8 GiB reservation, 200/120/5-second deadlines,
stderr bound, execution, final revalidation, release and quarantine paths stay
unchanged. Exceeding a limit requires another reviewed policy decision.

All 1,489 source checks pass: 283 collection checks plus the 1,206 existing
checks. Fixtures cover 1/3/8 items, exact size boundaries, unsafe names and
collisions, invalid receipts, and actual runner fragments refusing a late
receipt/ID error before any alias directory is created. They read no retail
payload, load no native support and acquire no lease.

Plan L declares only the three qualified files, totaling 22,976,640 bytes. Its
31 bindings are 23 text/eight binary inputs; seven metadata rows imply seven
aliases and fourteen original/alias ID checks. The output ceiling is
150,786,072 bytes. The candidate, arguments and execution budgets are unchanged.
The 17,136-byte Plan SHA256 is
`1f8f2567708c0bc6318f82c18b7806dde6e207cd85435fccf006ffc806a006a6`.
Its default invocation validated all three real qualification receipts and
returned `PlanCheckedPendingGO` without hashing binary inputs, loading native
types, acquiring a lease or creating runtime files. Prepared work/evidence/temp
directories remain empty and there is no attempt marker. Independent source
review, coordinator-owned exact-head CI/integration, fresh preflight and a
distinct exact GO remain necessary before any catalogue Run. No new catalogue,
model export or content compatibility is claimed.

## Catalogue L: one attempt retained and independently closed

After independent source/Plan and dispatch reviews, L received a distinct GO
for one invocation. The extra read-only preflight client filter initially used
`cod.*`, which incorrectly matched Codex processes. It refused before any
persistent host, lease or payload access. Restricting that additional filter to
the actual IW7/BlackOps3 executable families preserved the common admission
checks and all pinned source/commands. The fresh 18:57:59.7955677 UTC preflight
passed at 54.70% commit use with the unchanged 6/8 GiB budget, no client/heavy
process and no lease. This correction did not cause a native retry.

The exact reviewed host command and pinned L dispatcher were used once. The
native root exited naturally with code 0 after 2,346.66 ms. The run finalized
at 18:58:36.0074576 UTC as `Failed / NoCatalogue`; the wrapper returned at
18:58:36.0327270 UTC. TRACE, EXIT, CALLERS and a complete 40-byte NUL-terminated
MSG capture were observed and correlated. These diagnostics and exit code 0
do not establish a successful catalogue. Raw message/code bytes remain private
for the analysis owner.

Under-lease final hashes, metadata and IDs revalidated all seven sources and
aliases. Same-host postflight at 18:59:05.7206678 UTC confirmed seven unchanged
metadata rows, fourteen equal file IDs, closure/release and no quarantine.
The pinned runner's finally path disposes the guards before wrapper return;
no separate guard counter is claimed. No payload hash was read after release.
Session 52678 actually exited 0 (chunk `f6aaed`); the independent witness at
18:59:28.0712810 UTC found host 3236, parent 14896, native root 35608 and the
run-root processes absent. There were no clients, heavy workloads or leases;
Main/image/UDP remained absent and Python's preserved identity was unchanged.

The [sanitized L runtime checkpoint](catalogue-runtime-l-20261012.json) pins
the 16,614-byte receipt, reviewed dispatch, helper, corrected preflight,
same-host postflight, actual exit and independent absence. The 4,878-byte
stderr hash was recorded under runtime guards; stdout is 70 bytes. L is consumed
and retained. No further dependency, payload read, build or catalogue Run is
authorized by this result.

The analysis owner independently confirmed the receipt and interpreted the
complete correlated message as a missing `core_patch` startup zone, replacing
K's `en_core_patch` failure. Stdout still contains only initialization starting;
the initialization-complete and catalogue markers, catalogue JSON and its
directory are absent. The changed first named failure does not prove complete
validity of the three earlier files or an exhaustive dependency list. No new
asset path or metadata was consulted. The smallest proposed next decision is
an exact metadata observation of `core_patch.ff`, then bounded qualification
only if separately authorized. No dependency is inferred from name symmetry.

## CorePatchA preparation: explicit 64/128 MiB policy

The separately authorized exact metadata observation found `core_patch.ff`
at 45,217,664 bytes, with ordinary file/ancestors. Metadata and an OS file ID
were observed; content/header/hash were not read. It exceeds the original
32 MiB reader limit by itself. Added to the three qualified files it would
total 68,194,304 bytes, exceeding even a 64 MiB aggregate by 1,085,440 bytes.
Preparation stopped on that old boundary before a qualification script or
payload read. This refusal is retained in the
[sanitized CorePatchA preparation checkpoint](catalogue-core-patch-preparation-m-20261012.json).

A distinct source authorization then set 64 MiB **per file** and 128 MiB
**aggregate**, still one through eight explicitly named/qualified files.
`QualifiedCollectionV2` makes that choice explicit. V1 remains at 32/32 MiB;
the exact legacy J/K rules remain unchanged. Names, paths, receipts, IDs,
remaining-cap arithmetic and validation-before-alias requirements are shared.
The 6/8 GiB reservation, deadlines, stderr cap and execution/closure paths
are unchanged. The four-file output ceiling would be 196,003,736 bytes;
the policy maxima are 262,027,160 for the current candidate or 307,385,752
for a 64 MiB candidate.

The existing `Read-SteamSnapshot` range now permits at most 64 MiB, with an
explicit `Allow64MiB` switch required above 32 MiB. Without that switch the
old limit refuses before path validation, opening a stream or allocating its
buffer. CorePatchA passes the switch explicitly and retains the existing
snapshot/hash/guard implementation. Its two exact 45,217,664-byte passes
would read 90,435,328 bytes in total. All five qualification lifecycle
functions are byte-for-byte identical to the predecessor.

All 1,585 source checks pass: 311 collection, 68 reader and 1,206 remaining
catalogue checks. The 54 separate qualification lifecycle checks also pass.
Boundary fixtures cover the actual four-file arithmetic, exact 64/128 MiB
limits, V1's unchanged refusal, and rejection before a reader path/stream or
partial collection can escape. No large fixture allocation, retail content,
native support or real lease is used. CorePatchA default returns
`QualificationScriptCheckedPendingGO`; the future persistent-host command's
actual arguments were captured without launching that host. Its scope,
attempt marker and result receipt are absent.

A small delegation protocol was proposed, not activated: at most three more
dependencies named by complete correlated MSG failures, one qualification and
one catalogue each, no retry and complete closure between stages. A new error
category, repeated/ambiguous name, limit/admission/identity failure or any
uncertain lifecycle stops the batch. It introduces no discovery engine or
scheduler. A separate coordinator acceptance would be needed to delegate
those stages; source authorization alone does not authorize them.

CorePatchA awaits targeted review and a distinct qualification GO. Plan M
does not yet exist: it can use the fourth file only after qualification has
fully closed with a real hash/identity. No runtime compatibility is claimed.

## Accepted bounded batch: CorePatchA and catalogue M closed

The coordinator subsequently accepted the exact three-dependency protocol,
source commit `22bbaa184c583c7d579b991def9b79c73b2a19e4`, V2 profile, reader and
unchanged MSG candidate. The proposal JSON remains immutable historical evidence.
This permits at most six sequential heavy phases, no retries, and continuation
only from the analysis owner's complete correlated message naming one new safe
startup zone. Every existing admission, identity, size and lifecycle stop remains.

CorePatchA ran once at 19:20:48 UTC. Two guarded passes of 45,217,664 bytes
established the actual hash and stable identity; compatibility, headers, depot
integrity and engine lookup remain unproved. Guards closed, the tree closed,
the lease released and quarantine was absent. PTY 98502 exited 0 (`d9fa11`);
the independent 19:25:14 UTC witness found host and parent absent, no clients,
heavy workloads or leases, Main/UDP absent and the preserved Python unchanged.
An interactive proof-write path error was corrected using the explicit absolute
path, without repeating qualification or changing its result.

Plan M declares four qualified inputs totaling 68,194,304 bytes, 34 bindings,
eight metadata rows and an output ceiling of 196,003,736 bytes. Source-only
default and actual host/runner argument capture passed before publication of
the sealed plan and dispatch. Fresh admission passed at 55.11% commit usage,
with the unchanged 6/8 GiB reservation and no RAM reserve.

The unique M run exited naturally with code 0 after 3,025.71 ms, but finalized
as `Failed / NoCatalogue` at 19:27:42 UTC. The correlated private MSG awaits
interpretation by its analysis owner. Under-lease input hashes and identities
revalidated; same-host postflight checked eight metadata rows and sixteen IDs.
The guards' disposal follows the pinned runner's finally path before wrapper
return. PTY 48452 actually exited 0 (`e14b7c`); the independent 19:28:47 UTC
witness confirmed host, parent and native root absent, zero heavy/client/lease
counts, unchanged stopped Main baseline and preserved Python identity.
No payload hash was read after release.

A draft closure helper's cosmetic variable-renaming expression failed parsing
before invocation. The failed draft is retained privately. The corrected helper
kept predecessor variable names, changed only exact attempt values, passed
parsing and the same-host closure checks. No operational source or Run changed.
Future closure helpers should likewise change only fixed attempt values.

The [M checkpoint](catalogue-runtime-m-20261012.json) records both completed
phases and their private evidence pins. One of three dependency cycles is
consumed. Further execution remains conditional on the separately accepted
protocol; no catalogue, export, conversion or rendering has been established.

The analysis owner then confirmed M's complete correlated 41-byte message names
`en_core_gfx`, a new startup-zone failure in the same category. Its single exact
path is an ordinary 768-byte file; only metadata and an OS file ID were read.
Five declared inputs would total 68,195,072 bytes. These observations satisfy the
batch's name/metadata bounds for dependency two; they prove no content validity.

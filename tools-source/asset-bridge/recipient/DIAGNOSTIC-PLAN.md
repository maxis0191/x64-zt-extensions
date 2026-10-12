# Recipient timeout: observation plan and B outcome

The first attempt and restoration are fixed in `0007825`. The separately
authorized B probe has now stopped and restored, as recorded below. No debugger
or dump process was started. The coordinator controls the next native slot. A new
diagnostic run requires reviewed source changes, a fresh plan and a separate GO.
The original `cb3d9ac` commit and failed outputs remain preserved. Implemented
follow-up changes are Recipient's pipe visibility, honest capture receipts,
explicit references-only mode and read-only light observation helpers. Native
flags, stdin policy, stock and E7 remain unchanged.

## What the successful Beacon comparison establishes

[Measured comparison](bootstrap-comparison-2026-10-12.json) binds the actual
successful Creator Beacon build receipt `b0b5f007...49f5c5be` and failed recipient
receipt `512247ff...8227d26`. All 72 stock entries match in source, operational
mode, size, timestamp, attributes, observed content hash and recorded/source
NTFS identities. E7, BuildJob `f6be2a4c...`, Python executable path and common
native flags are the same. Each operation used a fresh work directory and copied
only the mutable sentinel; generated caches are operation-local.

| Detail | Successful Beacon | Recipient references |
| --- | --- | --- |
| Native common flags | `-headless -unbuffered-io -strict-content-sources` | Same |
| Action | `-buildzone/-verifyzone/-dumpzone sdk_beacon` | Fixed `-enemy-reference-check cp_zmb recipient-material.csv sdk_beacon_recipient_a` |
| Native stdin | `Popen` argument omitted, inherited/None | Open `PIPE`, held by adapter |
| Native stdout/stderr | Buffered Python pipes, shared `copy_bounded` | Same |
| Python `-B` | Not supplied | Supplied; affects bytecode-cache writes, not native CLI |
| Process creation | Original shared job, NO_WINDOW/BelowNormal/suspended Python; native CREATE_NO_WINDOW | Same |
| Environment | Inherited without explicit override | Same policy; actual historical values were not captured |
| Map load | No `cp_zmb` preload | 25 source-zone calls after CLI dispatch |
| Retained stdout | 1,212/1,095/668 bytes after successful EOF | Zero bytes at timeout |

No equality of the historical environment contents or stdin handle values is
claimed. Neither source launches through a shell. The exact original-handle
creation and inherited environment are visible in shared `BuildJob::Prepare`.

In pinned native source, `main_internal` makes stdout/stderr unbuffered before
`post_start`, then maps the retail executable and enters it. The console thread
is created by `post_start` and calls `std::getline(std::cin, ...)`. Engine
bootstrap loads code_pre_gfx followed by code_post_gfx/common, then ZoneTool
starts and dispatches CLI parameters. There is also a pre-entry `MessageBoxA`
exception path. The open stdin pipe is a real behavioral difference, but no
captured stack proves it blocked this run. No stdin change is proposed during
the diagnostic reproduction.

## A proven visibility defect, not a proven native cause

The pinned shared drain calls `source.read(4096)`. `Popen` supplies a buffered
reader. A live writer can leave fewer than 4,096 bytes in that read until more
bytes or EOF arrives. Beacon's short successful phases reach EOF; recipient's
timeout executes `os._exit(2)` with daemon drain threads still alive, potentially
discarding their partial buffered data. Native `-unbuffered-io` does not remove
this separate reader-side buffering.

The tiny [pipe experiment](check_drain_visibility.py) loads the exact SDK drain,
starts no child process and uses no retail data. Its 96-byte write remains
invisible with `read`, then becomes visible at exactly 4,096 bytes. A proxy using
`read1` makes 96 bytes visible while the writer remains open. Both drains close
cleanly. Result SHA256:
`61b2125dda109a1fa88521b1e1108f28e2cc21ebc1c9f59aa32ba9723be0f168`.

This invalidates using empty logs to locate the stop before initialization. It
does not establish that the failed native process emitted anything. Following
coordinator authorization, Recipient now supplies `Popen(bufsize=0)` and raw
log destinations while retaining the exact shared drain. Python documents that
this makes pipe reads unbuffered and permits short results. See the official
[Python 3.12 Popen documentation](https://docs.python.org/3.12/library/subprocess.html#subprocess.Popen).
The `read1` proxy remains only a comparison fixture; it is not the implementation.

Twenty-three transport/writer checks pass against the actual unchanged provider:
live short stdout/stderr, EOF with a short tail, exact 2 MiB prefix/truncation,
timeout prefix preservation with no invented closure, read failure, and source
wiring. They also reproduce the reviewed raw-write defect and cover bounded
write-all, zero/None/invalid returns, partial-prefix errors, flush errors,
real-file counters and exceptional thread exits. Eleven contract tests,
33 PowerShell checks and 13 pure light-observer identity checks also pass. No process was
spawned by these stream fixtures. `native-start.json` will record the observed
PID/parent/image/hash promptly; its observation timestamp is explicitly **not**
verified process creation time. Future identity-gated diagnostics must obtain
and check actual creation time before reading a process. Phase receipts report
stream byte counts and whether drain threads actually closed, separately from
the outer job's closure proof.

The review of `4867081` found that raw `FileIO.write` could accept fewer bytes
than requested while the provider counted the entire chunk. The unchanged
provider demonstrably reports ten bytes after an injected five-byte write.
Recipient now wraps raw destinations in a local `BoundedLogWriter`: a chunk of
at most 4,096 bytes gets at most 16 progress-making writes, within the 2 MiB total.
Zero, None, invalid returns, exhausted retries and I/O errors raise `OSError`,
which the pinned provider converts to failed capture. The adapter counts actual
accepted bytes, including a failed prefix; success additionally requires that
count to match the retained file size. Receipt counts still come from file sizes.
The provider's completed-chunk counter is not reported as retained bytes after
failure. This corrects log integrity, not the unresolved native stall.

Review of `f1096b1` then reproduced another failure: a `ValueError` escaped the
provider's OSError-only handler and silently terminated its thread while capture
could still succeed. Each thread now enters a local `guarded_drain` wrapper.
It catches every `BaseException`, marks the destination failed, records its
exception type and signals the owning phase before terminating. The receipt's
existing failure string includes the stream and exception type; no schema or
provider change is needed. Exception formatting is deliberately avoided because
`__str__` can itself fail. Tests exercise read/write/flush `ValueError`, a closed
raw pipe, `SystemExit`, an exceptional finalizer with broken error formatting,
and prompt signaling while the native stub and the other pipe remain live.
Even a zero native exit with saved output cannot accept those failed captures.

```powershell
python -B tools-source/asset-bridge/recipient/check_drain_visibility.py --sdk-drain $reviewedSdkDrain
python -B tools-source/asset-bridge/recipient/check_recipient_streams.py --sdk-drain $reviewedSdkDrain
```

## Proposed next observation, before the watchdog

1. Review the narrow diagnostic adapter before execution: the implemented live
   short-read drain/locator receipt, verified creation identity and explicit
   `-ReferencesOnly` mode. Use the same E7, 72-entry binding, work layout,
   stdin pipe, native flags and original job owner. Never reuse failed run-a.
   The original two-phase production runner remains preserved for comparison.
2. Prefer the existing **8 GiB RAM / 11 GiB commit** group with corrected live
   logs and light observations first. It does not include a snapshot or debugger.
   A future full-capture variant remains preparation only: proposed 10/14 covers
   8/11 plus the existing 2/3 diagnostic estimate and requires separate review/GO.
   Native deadlines stay 240/245 seconds and output stays 256 MiB. Do not nest a
   competing lease or borrow another chat's reservation.
3. At native launch bind PID, executable path, creation time and E7 hash to the
   original child/parent relationship and job. At 10 and 30 seconds capture CPU,
   memory and IO deltas plus individual thread state/wait reason through the
   existing process APIs. Read `WaitReason` only for waiting threads and record
   exiting-thread exceptions as unavailable. Never adopt a replacement PID.
4. Read only that process's `MainWindowHandle`/`MainWindowTitle` with an identity
   check before and after. Do not click, close or focus a window. This is a main
   window observation, not enumeration of every possible dialog. Handle zero
   must not be reported as proof that no window exists.
5. At 45 seconds assess the newly visible logs and light observations. If these
   locate the wait, full capture may be unnecessary. A snapshot is allowed only
   in the separately reviewed/admitted full-capture variant, never implicitly
   under the first 8/11 group. That variant takes **one** stack-oriented snapshot
   using existing `ops/iw7_capture.py`, identity-bound as below. Its mask is
   `0x1820`; retain that mask and do not request a full-memory dump. A snapshot is
   needed here only if logs/window/thread observations still cannot localize the
   wait. Trigger early enough to finish well before the 240-second watchdog.
6. Bound the snapshot child by its own original job: 15 seconds, 64 MiB dump stop
   threshold, 2 MiB per output stream, counted in the overall 256 MiB. Poll file
   size while writing and terminate only the diagnostic job on excess or timeout.
   The existing helper itself has no byte cap or cancellation callback: this
   outer threshold can overshoot and is not a hard disk quota. That integration
   must be reviewed; it is not supplied by invoking the helper standalone.
7. Once sufficient diagnostics are safely written, stop the original native job
   deliberately and mark the diagnostic attempt stopped, never successful. Keep
   the normal root-exit/zero-member/restore/source-preservation proof. Do not
   start the utility phase or repeat a four-minute wait without new evidence.
8. Analyze the bounded dump **offline only**, after native closure, using the
   existing pinned CDB for at most 30 seconds with bounded logs. Retain the raw
   dump locally. Reuse the same complete reservation until all diagnostic jobs
   and the original job are closed, restoration passed, and sources preserved.

These are proposed source changes/limits, not authorization to execute them.
No generic launcher, native-tool patch, new dependency or broad extraction is
needed. Keep a changed source pin/new plan separate from the preserved first run.

### Recipient B: first corrected probe, light observations only

The B execution uses `-ReferencesOnly` in the plan and eventual `-Run` command,
8 GiB RAM / 11 GiB commit, the original reference native CLI, 240/245-second
phase deadlines, five-second post-root drain, 600-second group and 256 MiB output
threshold. It retains the existing 2 MiB-per-log cap. A fresh RunRoot is required.
Utility never starts in this mode, even after a successful reference observation.

The operator imports the source-hash-bound `Recipient.Light.ps1` and obtains
the exact phase/locator from the bounded state and native-start receipts. Near
native start, then at approximately 10 and 30 seconds, call
`Get-RecipientLightObservation` with the plan, original Python phase identity,
locator, and the first sample's native identity for every subsequent sample.
Each call checks actual creation time and image for both parent and child before
and after sampling. Original-handle vs CIM timestamps allow only the existing
one-microsecond precision difference. The locator observation time is not used
as process creation. E7 is rehashed and a process handle is held while sampling.
Direct job membership is explicitly not queried; the known original parent and
the launcher's non-breakaway job inheritance remain the ownership evidence.

Use at most four samples (initial, 10, 30, optional 45 seconds), at most 128 KiB
UTF-8 JSON each, with create-new output names inside this run's evidence folder.
Thread enumeration retains at most 256 entries; exiting threads are unavailable.
Wait reasons are read only while a thread is waiting. CIM requests have a
two-second operation timeout each; this is not a hard whole-call deadline.
Unavailable or exited identities must be recorded as unavailable, never adopted
again from a replacement process. CPU/IO deltas compare the same bound identity.
Window handle zero does not prove the absence of dialogs; no UI interaction occurs.

At 45 seconds inspect bounded live stdout/stderr and these observations. The
existing `stop.request` route can stop the owned group if the coordinator decides
the collected cause is sufficient. Otherwise the original deadlines still apply.
No dump, CDB, snapshot helper, added native flag, stdin experiment, stock change
or automatic retry is part of B. A future full-capture proposal above remains
separate and requires its own source review, admission and GO.

A plan is neither a reservation nor permission to execute. Recheck source and
provider hashes and acquire the complete fresh shared admission only after the
coordinator's one GO. The original job must be closed with zero members before
source-preserving restoration and release; no successful diagnostic observation
can substitute for that lifecycle proof.

The first B planning repeat had equal values but different raw hashes because
ordinary PowerShell request hashtables changed JSON property order across hosts.
Those two local plans and their canonical-equality comparison are retained.
Request maps now have explicit ordering so the reviewed plan can be compared
byte-for-byte across fresh hosts; this changes no native request or argument.

### B execution outcome and remaining observation

One B attempt of `379526b` ran after explicit GO and fresh atomic 8/11 admission.
The [sanitized record](native-validation-b-2026-10-12.json) binds the exact plan,
command and retained hashes. The corrected capture exposed 1,449 bytes of stdout:
bootstrap finalized and the last marker announced `global_mp` loading. Three
identity-checked samples showed the same `Fatal Error` main window. Its body
was not read, so neither the fatal cause nor the missing-language notices are
diagnosed. No reference CSV or script phase was produced.

Actual sample ages were 43.35, 107.14 and 193.22 seconds; the planned early timing
was missed and is not claimed. The direct job-membership query flag remained
false and each CIM timeout remained a per-request bound only. The existing
private-desktop reader was inapplicable and its guard was not bypassed. A later
authorization for Python ctypes text reading arrived after the approved
`stop.request` had already been placed. Shutdown continued without cancelling
the stop. Exact arrival relative to final closure was not independently timed.

The original job stopped with root exit 122 and zero members; restoration and
stock preservation passed. All 75 staging paths were removed, the registry was
empty, both owned processes were absent and Main's identity was unchanged.
The original Failed state and NativeExecuted=null were preserved. This is a
closed diagnostic failure, not reference or package acceptance.

Before another separately authorized attempt, prepare a minimal Python ctypes
reader using the existing interpreter: verify real parent/child image/creation,
E7 and HWND ownership before and after; read at most eight child controls and
16 KiB total; use bounded text reads without clicks or command messages. It
should be ready before launch so useful text can be captured promptly. This
preparation is not permission to rerun B, add a dump or enlarge the budget.

### C implementation and subsequent diagnostic result

The new `-FatalTextDiagnostic` plan selects references only and automatically
polls at 250 ms from the existing Python phase. The native E7 executable,
reference arguments, stdin, stock and original job are unchanged. Complete
admission remains 8/11 GiB. Native/adapter work is limited to 45 seconds, its
original job to 50 seconds, and group active work to 60 seconds. The existing
15-second closure wait starts only after `Stop` returns; it does not bound that
call or the subsequent mandatory source verification/restoration. Do not confuse
these waits with a guaranteed whole-lifecycle wall-clock deadline.

`recipient_dialog.py` loads only existing Windows DLLs through ctypes, and only
when this explicit mode executes. It verifies the original native handle and
the parent's current handle with PID, image and real creation FILETIME. The
parent relationship comes from ProcessBasicInformation; no process is opened
by a rediscovered PID. E7 is checked before/after text collection. Ownership is
checked for the root and every child HWND before/after, and process identities
are rechecked at the end. Failed identity checks discard potentially
misattributed text. DirectJobMembershipQueried remains false.

Root discovery inspects at most 256 HWND ownership entries and eight windows
of this process per poll. It reads no other process's caption. Only the known
`Fatal Error` caption starts the one capture. EnumChildWindows stops at eight
controls; only STATIC control text is read. Caption, classes and body text share
a 16 KiB UTF-8 budget. The complete JSON record is capped at 64 KiB. Each
WM_GETTEXT has a 200 ms timeout with ABORTIFHUNG and ERRORONEXIT; no broadcast or
NOTIMEOUTIFNOTHUNG flag is used. The loop additionally checks a two-second soft
capture deadline. Windows enumeration/API work has no independently guaranteed
whole-call deadline; the original owner's 50/60-second limits remain decisive.

The record and failed phase receipt precede the automatic diagnostic stop
marker. Missing body text, read errors, no fatal window before timeout, or a
native zero exit all remain diagnostic failure. Original stop/closure/restoration
is performed by the reviewed PowerShell job owner, never by the text reader.
`DiagnosticFailed` preserves failed evidence without accepting references.

Review of `dec2792` found that the 2,048-wchar read could return a full buffer
without flagging the possible truncation. The reader now returns a conservative
`buffer_saturated` flag when WM_GETTEXT's result is at least 2,047 characters.
The control records that flag and propagates it into `text_truncated`, even when
the total stays below 16 KiB. An exact fit is deliberately treated as possibly
truncated; no extra message or larger read is attempted. Fake short, boundary
and over-reported responses prove propagation and a single message per control.

19 fake-reader tests, 25 pipe/writer checks, 11 contract tests, 35 PowerShell
checks and 13 pure B-observer identity checks pass. Those source fixtures were
followed by the separately authorized real attempt recorded below.

API contracts were checked against Microsoft's primary documentation:
[GetWindowTextW](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindowtextw)
does not retrieve another process's control text, so the body uses bounded
[SendMessageTimeoutW](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendmessagetimeoutw)
with WM_GETTEXT. The
[EnumChildWindows callback](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-enumchildwindows)
can stop enumeration by returning false.
[NtQueryInformationProcess](https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntqueryinformationprocess)
documents the parent field but is an internal API subject to change; an unavailable
or incompatible result fails the reader rather than weakening identity checks.

The [C evidence](native-validation-c-2026-10-12.json) records one execution of
`79735fe`, fresh 8/11 admission and a successful bounded body read:
`Could not find asset file assetfile17.pak`. The dialog identity was verified and
the body was not truncated. The record was written about 4.08 seconds after
native creation; automatic original-job stop/restoration followed. Original root
exit 2 and zero members, source preservation, no remaining owned process/lease,
all 75 staged paths removed and unchanged owner/Main identities were confirmed.
The result remains DiagnosticFailed, with no references or package acceptance.

The immediate missing-file request is now known. The next source-only action is
to resolve the pinned search path, find pak17 in retained Doom/base stock, and
prove the staging omission before proposing a minimal guarded hardlink addition.
Do not alter pools, skip `global_mp`, copy the full retail installation or rerun
without a separate review/GO. C's original evidence is immutable.

The resulting [separate Recipient stock profile](STOCK-PROFILE.md) is prepared
with four historically observed PAK prerequisites and a metadata-only binding.
The default plan requires that receipt; neither it nor the light fixtures reads
PAK content. Full SHA-256 requalification remains inside the next admitted,
guarded operation. The 72-entry shared FF profile and 12 provider pins are intact.
The next plan requests references only. Its result, memory peak and complete
stock sufficiency remain unverified until a separately authorized execution.

D subsequently executed once under its explicit GO and stopped on a verified
Fatal Error title after reaching `global_cp`. Its [immutable failure record](native-validation-d-2026-10-12.json)
confirms restoration of all 79 paths, source metadata, original job closure,
unchanged owner/Main and released lease. The light observer did not read body
text, so the new error is unknown. D's GO is exhausted. The next source-only
change must enable the existing identity-bound body reader during normal
references mode, retaining successful results only when no fatal is detected.
Keep DiagnosticOnly separate; do not broaden PAKs before exact fatal evidence.

That source correction is prepared. Normal references now use the same existing
bounded reader, preserving normal success when it sees no fatal/reader error.
A failure saves dialog and phase receipts before `fatal-stop.request`; the
original owner stops the job. Forced diagnostics retain their distinct marker
and unconditional qualification failure. The reader implementation and PAK set
are unchanged. 143 light checks pass; the new wiring has no native-run evidence.
Review the source before generating the next exact plan. A separate GO is still
required before execution; do not reuse D's exhausted command/plan approval.

Review of the resulting E plan found stale elapsed-time acceptance in
`Wait-RecipientPhase`. E remains unexecuted. E2 refreshes the monotonic clock
after original-handle getters, Save and budget checks, and checks both phase
and post-root-observation drain deadlines before accepting an empty job. New
mock slow-call cases reproduce the old bug and reject overruns after correction;
65 source/contract plus 39 stock fixtures pass. Stop/closure/quarantine remain
owned by the same caller. This is no waiver for slow or blocked calls: late
closure is failure, and hard preemption is not claimed. The changed Core hash
requires a separate E2 plan, corrective review and GO. PAKs remain unchanged.

## Existing tools and exact constraints

`iw7_capture.py` SHA256
`d2ec79aec62573dee8b24530cfeddb06b9410338b1b70332d2afba3d8dd7162d`
already opens a process handle, checks image/hash/creation time, and writes a new
snapshot file. Its ordinary `--threads` observer reports thread CPU, **not wait
reasons or call stacks**. Do not relabel it as a stack sampler.

The existing HUD stall path demonstrates identity-bound direct snapshot capture
and subsequent offline CDB analysis without live debugger attach. It uses a
different owned launcher/private desktop and is a reference pattern, not a
drop-in recipient launcher. `Debug-Server -Action Snapshot` explicitly requires
its isolated-lab image and flag; do not fabricate those to pass the guard.
`Read-IW7AgentFatalDialog` similarly requires a recorded private desktop absent
from the unchanged recipient launch. Do not forge a DesktopName or move the
target onto a new desktop just for observation.

Future guarded snapshot arguments, filled only from the live exact identity:

```text
python -B <reviewed-ops>/iw7_capture.py --pid <exact-pid> --image <staged-E7-path> --created <exact-created-utc> --sha256 e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04 --snapshot --scenario recipient-reference-stall --output <new-local-stall.dmp>
```

Installed CDB was read/hash-checked, not executed: WinDbg `1.2606.22001.0`,
178,016-byte `amd64/cdb.exe`, SHA256
`5f54abafca3ae5638bbf807d402fabb350a64575c1dfa9fbfc7f5732df5bee67`.
The existing fulltool PDB is retained (135,532,544 bytes); PE/PDB GUID/age and
captured module identities must match before assigning source-level frames.
Retail manually mapped code may remain unresolved; report addresses and matching
module evidence instead of inventing symbols. No symbol download is planned.

```text
cdb -z <bounded-local-stall.dmp> -y <retained-fulltool-symbol-directory> -c "~* kP; lmv; .time; q"
```

The required outcome is a located wait/failure (for example a dialog, filesystem
wait, database wait or console read) with exact thread/module evidence. Shared
stock equality, low CPU and empty logs alone do not select any of those causes.

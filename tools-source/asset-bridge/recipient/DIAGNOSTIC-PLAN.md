# Recipient timeout: targeted observation plan, not executed

The first attempt and restoration are fixed in `0007825`. No further ZoneTool,
debugger, dump or capture process has been started. The coordinator sequences
Material compiler diagnostics and the corrected Aurora candidate first. A new
diagnostic run requires reviewed source changes, a fresh plan and a separate GO.
The original `cb3d9ac` commit and failed outputs remain preserved. The only
implemented follow-up changes are Recipient's pipe visibility and honest capture
receipts; native flags, stdin policy, stock and E7 remain unchanged.

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

Six bounded anonymous-pipe checks pass against the actual unchanged provider:
live short stdout/stderr, EOF with a short tail, exact 2 MiB prefix/truncation,
timeout prefix preservation with no invented closure, read failure, and source
wiring. Eleven contract tests and 29 PowerShell checks also pass. No process was
spawned by these stream fixtures. `native-start.json` will record the observed
PID/parent/image/hash promptly; its observation timestamp is explicitly **not**
verified process creation time. Future identity-gated diagnostics must obtain
and check actual creation time before reading a process. Phase receipts report
stream byte counts and whether drain threads actually closed, separately from
the outer job's closure proof.

```powershell
python -B tools-source/asset-bridge/recipient/check_drain_visibility.py --sdk-drain $reviewedSdkDrain
python -B tools-source/asset-bridge/recipient/check_recipient_streams.py --sdk-drain $reviewedSdkDrain
```

## Proposed next observation, before the watchdog

1. Review a narrow diagnostic adapter before execution: the implemented live
   short-read drain/locator receipt, verified creation identity, one-shot capture scheduling and an explicit
   references-only diagnostic mode. Use the same E7, 72-entry binding, work layout,
   stdin pipe, native flags and original job owner. Never reuse failed run-a.
   The original two-phase production runner remains preserved for comparison.
2. Admit the complete diagnostic group once. Conservative proposal: 10 GiB RAM /
   14 GiB commit, covering the original 8/11 plus the existing 2/3 diagnostic
   estimate. Native deadlines stay 240/245 seconds and output stays 256 MiB.
   Diagnostic outputs count against that same group; do not nest a competing
   resource lease or borrow another chat's reservation.
3. At native launch bind PID, executable path, creation time and E7 hash to the
   original child/parent relationship and job. At 10 and 30 seconds capture CPU,
   memory and IO deltas plus individual thread state/wait reason through the
   existing process APIs. Read `WaitReason` only for waiting threads and record
   exiting-thread exceptions as unavailable. Never adopt a replacement PID.
4. Read only that process's `MainWindowHandle`/`MainWindowTitle` with an identity
   check before and after. Do not click, close or focus a window. This is a main
   window observation, not enumeration of every possible dialog. Handle zero
   must not be reported as proof that no window exists.
5. If still unresolved at 45 seconds, take **one** stack-oriented live snapshot
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

# T7 diagnostic before absolute patches

2026-10-12. The coordinator selected an earlier diagnostic stage than the
catalogue: observe layout, page protections and bounded code windows at the
first intercepted `SetProcessDPIAware` after entrypoint, before component
`post_unpack` / Arxan or other absolute-address patches, then exit. The engine
worker owns that bounded helper and its contract; the T7 worker owns integration
into the existing build preparation. This checkpoint prepares only the local
environment. It starts no process and does not qualify a candidate or hook.

## Environment actually prepared

The new ordinary `runtime/t7-prepatch-a` tree contains `work`, `evidence` and
`temp` directories. Its `work` directory contains exactly two NTFS hardlinks:

| Local filename | Existing source | Bytes | Previously verified SHA256 |
| --- | --- | ---: | --- |
| `BlackOps3_UnrankedDedicatedServer.exe` | Durable one-file Steam acquisition | 21,737,352 | `3df511d71e3690b14517379783bbfb713f6fe2ed2f2e73b445b4878216686156` |
| `steam_api64.dll` | Owner's installed BO3 dependency matching the manifest | 235,600 | `71af8666392acad2080a816b9f1196fe9ccb950e1db8a549f8312c4d231f55a8` |

Source/destination file IDs match for each link. Source length, attributes and
last-write timestamp remained unchanged; all checked ancestors/entries were
free of reparse points. Read-sharing-only source handles were held during link
creation and released afterwards. Hashes are inherited from the verified prior
receipts, not remeasured by this preparation. Reopen retained input guards and
verify exact hashes under the separately admitted runtime stage before use.

There is no candidate, `zone`, `../zone`, FF, FD or XPAK in this tree. No payload
was copied, native provider loaded or resource lease obtained. Exact paths and
file IDs remain private. [The sanitized observation](prepatch-environment-20261012.json)
binds the local preparation receipt by hash. The prepared environment is not
ready to execute until the final helper contract and instrumented candidate
are bound. An uninstrumented D2/E7 candidate must never be substituted.

## Runtime boundary to preserve

No zone/catalogue/export command belongs in this diagnostic. The final argument
and output contract must come from the actual reviewed helper integration;
none is invented here. Bind its final EXE hash, source/build receipt, exact
command, working directory, output location/caps and expected exit codes before
the coordinator's separate GO. Reuse the witnessed NativeJob, common scheduler
and original-handle closure through the existing small profile, with no new
supervision framework.

The entrypoint runs before the intercepted call and may access files or have
other effects. The absence of zone aliases does not prove zero engine I/O or
an OS sandbox. Stop clearly on missing files; preserve the first failure and
do not automatically add assets, Steam DLLs, BATs, playlists or guessed bootstrap
FFs. Failure to reach the hook, a native crash or a deadline is not compatible
layout evidence. No later ZoneTool init at `0x140504170` or absolute patch may
run in the witness path, including on diagnostic failure.

Keep the conservative planned engine admission separate from static inspection:
6 GiB physical / 8 GiB commit is an estimate, not a measured requirement. Pin
the reviewed stage deadlines/output caps in its final runtime plan. Existing
85% commit pressure, explicit stop request, exact original job stop, fresh
root/ActiveProcesses closure and lease quarantine rules remain. Do not shrink
budgets to bypass an occupied slot or interrupt Main/the owner's client.

The aliases are currently retained as prepared evidence. The dedicated EXE's
read-only attribute is shared across its hardlinks: do not clear it through an
alias or use a cleanup that silently changes original attributes. Any future
removal must use exact destination/file-ID checks and a reviewed file-level
method preserving the source attributes; otherwise retain the small aliases.
Do not recursively remove stock. No source/profile/configuration restore is
needed from this preparation because none was overwritten, but external writes
from a future run must be checked before claiming restoration complete.

After this diagnostic is qualified, the separate catalogue still needs its
actual engine/zone compatibility and startup stock decisions. A memory-window
receipt by itself proves neither a real model name nor conversion or rendering.

## Existing-owner invocation now implemented, not executed

`Run-T7Prepatch.ps1 -PlanPath <private-plan> -PlanSHA256 <reviewed-sha256>` checks
source pins, input metadata and the fixed command without hashing binary inputs,
loading native providers, taking a lease, creating files or starting a process.
A pending candidate is explicitly reported; it cannot run. `-Run` additionally
requires the separate coordinator GO and consumes one create-only attempt marker.
The plan and every source pin are retained through the existing `Open-H1Pin` /
`Read-H1SmallJson` helpers. No new pin reader, process owner or scheduler is added.

The candidate must occur in the actual successful, closed build receipt with
the exact expected build-plan SHA256. Its `BuildProfile` must identify
`t7-prepatch-probe`, argc 2, fixed option/report, and the guarded Helper/Wiring/
PreparedMain pins. Ordinary D2 is refused. Only after admission are binary pins
hashed/guarded and the one candidate hardlink created; the two existing aliases
remain. The child gets private TEMP/TMP/profile environment paths, with no claim
that all Windows known-folder or engine I/O honors those variables.

The actual launch and cleanup call `H1Native.Core.ps1::Invoke-H1OwnedStage` and
`Complete-H1Stage`, using the same witnessed NativeJob assembly. NativeJob's
`CloseConfirmed` rechecks its original process exit and ActiveProcesses0 before
releasing handles and retains the original exit code. No H1 compiler or fixture
policy is run. One Extract reservation is 6/8 GiB, the root gets 120 seconds, and
the one total clock is 200 seconds including input checks/finalization; failure
cleanup remains 5 seconds. The generic 64-entry tree guard stays in force. Mutable
outputs get 64 MiB, receipt reserve 64 KiB, each outer log 1 MiB and report 256 KiB;
the three pinned binary aliases are separately added to the accounting ceiling.
Unexpected work-directory output stops the attempt and is preserved.

After ordinary root0 or root2 closure, bounded JSON validation and binary input
reverification occur while the lease and input guards remain held. The JSON is
guarded through receipt publication. The launcher verifies schema/phase, process
generation, module path, counts/read bounds, the 12 exact windows and false
compatibility claims. Results distinguish `NoCapture`, `CapturePartial`,
`CaptureComplete` and a present but unqualified report. Exit2 remains failed as
a diagnostic run even when it produced useful partial evidence. Complete capture
becomes only `CaptureCompletePendingReview` after normal closure, input checks
and lease release; it never authorizes subsequent engine initialization.

On failed runtime cleanup, only the retained job is stopped. Uncertain closure
or release keeps the existing H1 quarantine context and host alive. After forced
closure only the small JSON may be inspected outside admission, never binary
inputs rehashed or a failed run accepted. Original input metadata and Main
generation/UDP27016 ownership are rechecked on the ordinary closed path. Aliases
are retained; the launcher performs no destructive cleanup or source-attribute
change. The record does not assert absence of all possible external engine I/O.

Validation: 47 light PowerShell checks exercise the actual H1 stage with fake
owners/clocks, including root2 normal closure, deadline before start, retained
quarantine on stop/release failure, and the real runner finalization block after
late release or publication. Bounded JSON guard/refusals, exact windows/identity,
ordinary-D2 rejection and candidate/build-plan mismatch also pass. The default
local check reports pending instrumented candidate with no binary hash/provider/
lease/file creation. These tests and preparation do not compile, start or qualify
a native candidate. The final candidate hash remains pending its real build.

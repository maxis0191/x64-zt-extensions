# First admitted CDB fixture: refused, closed and restored

The single authorized v3 fixture ran on 2026-10-12 from 08:51:54.532 to
08:51:57.185 UTC (10:51:54.532 to 10:51:57.185 Paris time). External invocation
duration was 2,649 ms; the core's last monotonic checkpoint was 1,953 ms after
its start. Integrated source was `df11e4f8033cad0e09b347092dea97f27403a695`.
No correction or second attempt occurred during this trial.

The complete fixed fixture 4/6 GiB preflight passed: 20 input pins, a fresh
RunRoot, current origin/main resource/instance/storage workflows, no competing
lease or heavy process, exact Main process/configuration/UDP identity, sufficient
physical/commit headroom and no commit high-water condition. The reviewed command
was invoked once with only `-Run` appended. It used atomic admission.

## Outcome and primary evidence

Result: **`FailedClosedRestored`**, not a qualified capture. The target's retained
stderr ends at `debug_fixture.py:29` with `RuntimeError: Outer owning job required`.
That guard combines an unsuccessful `IsProcessInJob` API call with a false member
result. It did not retain the API BOOL, last-error code or membership separately.
This evidence therefore does not yet establish that the target was outside the
original job; API failure remains a distinct possibility.

The fixture never produced `fixture.json`. The transport then encountered
`FileNotFoundError` while trying to read it. Its serialized Failed event omitted
`FixtureOnly` and `RootPID`, so the PowerShell consumer reported the later generic
`Transport identity differs.` error. The initial traceback and secondary missing
manifest error are both preserved. No source correction is part of this record.

The CDB log confirms Python startup and an initial debugger stop. It contains
zero ARM, BP_PRESENT, WRITE or capture STOP markers. No fixture context, sealed
log or witness exists. `Continued=false` refers to the guarded watch continuation;
the fixture-only startup `g` had already been sent. `LastMembership=null`: the
independent exact-three-member gate was never reached or qualified.

The debugger also printed initialization of its extension gallery, including
46 LocalInstalled packages, and network-symbol suppression messages. These logs
do not establish network traffic, absence of all symbol activity, a measured
memory peak or the cause of the job guard refusal.

## Closure and limits

The original-handle snapshot records root exited, **Active0**, and root exit
code **2**, retained without rewriting it as a successful exit. The independent
deadline helper reports Stop attempted/completed with no failure. This was the
cleanup RequestStop path after refusal, not evidence of a ten-second or
240-second timeout firing under a stalled controller.

`Closed=true`, `Restored=true`, `LeaseReleased=true`, `Quarantined=false`, and
`DiagnosticCaptured=false`. A fresh post-run registry observation contained zero
leases. The process snapshot contained no CDB or newly launched Python; the two
older Python processes and Main remained. Main's creation/image/configuration,
UDP response and file hashes matched the preflight. All 20 Plan pins still
matched. Exact-three membership and target job inheritance remain unqualified,
even though original job closure was confirmed.

Global memory snapshots before/after are preserved. No per-process peak series
was collected and no group memory maximum is inferred. No retail assets, game
state, external process attachment or PID-based adoption/termination was used.

## Retained private artifacts

The integrated checkout retains the run under
`runtime/rig-watch-fixture-93266d4ba35a424fa6ce3d87a828b636` and the invocation
receipts under `runtime/rig-watch-plans/fixture-v3-integrated-20261012-084626-273`.
Nonce: `93266d4ba35a424fa6ce3d87a828b636`. Seven run files total 14,609 bytes.
Raw logs, process identities and machine paths remain ignored private evidence.

| Artifact | SHA-256 |
| --- | --- |
| Approved spec | `b8379ff2b31bdf5958cb69cc10cdef1d5833f8e8a37507275822e4808143b065` |
| Approved default command | `aeffff95f9f7cd0e29b72a415a81cd4f89dc6514861e86b2de78edb2b647b252` |
| Preflight receipt | `42b419e47df1d1df245c5e5fec6446fa123bdb8c2b6e2c04056c4d28ede94910` |
| Invocation receipt | `620c35ca25df79bdd766b9a36b7ceb96e5e26afe47f24f996c4477e67bb5cd4e` |
| After-attempt receipt | `95a806028578cb803c3cec32707beeb7195f4ff8119fcb2d0ecab9ef7484dcab` |
| Original state | `1758e33b9265864f99bafeba4211e1e23b9dd24cfbec4d62c2c232f02dacd901` |
| CDB stdout | `0b0ea52de2bb99a38a9974bc91bb7750ea0fe6d086662e6b79bd4b00a2861d97` |
| Target stderr | `a5cfd5c3df0579581b091f312fea40f343a0b2cb7efd204adaca7d1ad6597c03` |
| Transport Failed event | `bcc51d3d6c3ba0a0ae8053e707e647e0cbc8bfea239b90b0087186c51d01d1a7` |
| Derived evidence manifest v2 | `9f32fc0c8c0b76390711bf606b9336129ea960487299b9089b72187cadc52470` |

The first derived manifest is preserved too: its total-byte aggregation returned
null; v2 only fills that total from the seven retained byte counts. No raw trial
artifact changed.

Next source work is diagnostic: retain explicit x64 API signatures and separate
API/member/last-error values, and preserve bound identity plus the initial cause
in a Failed transport event. Keep the guard. Review a distinct diagnostic Plan
before any new GO; this failure does not authorize a retry or retail observation.

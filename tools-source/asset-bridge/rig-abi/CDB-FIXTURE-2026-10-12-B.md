# Diagnostic fixture: successful API call, target not in a job

One separately authorized diagnostic invocation ran on 2026-10-12 from
09:32:22.297 to 09:32:25.046 UTC (11:32:22.297 to 11:32:25.046 Paris time).
Its external duration was 2,743 ms and the core's monotonic duration 1,953 ms.
Observed checkout HEAD was `e718f61eb4210d1c527066d998939e03555faff8`; the
diagnostic sources had been integrated at `9134fe43162ad7d7f60b89cca63b6472c7767b1e`.
All 20 exact Plan pins remained unchanged despite intervening documentation commits.

The fresh preflight confirmed the exact Main identity and UDP endpoint, no
competing lease/heavy process, sufficient full fixture 4/6 admission headroom,
current workflow blobs and an absent output root. Only the approved command with
`-Run` appended was invoked. No source correction, relaxation or retry occurred.

## Query results retained separately

| Field | Transport self-query | Synthetic target self-query |
| --- | --- | --- |
| API BOOL return | 1 | 1 |
| API succeeded | true | true |
| Last error, captured immediately | 0 | 0 |
| Last error meaningful | false | false |
| Raw member output | 1 | 0 |
| Member output valid | true | true |
| In any job | true | false |
| HANDLE / BOOL bytes | 8 / 4 | 8 / 4 |
| Specific original job proven by this query | false | false |

This removes the API-failure ambiguity from trial A: the target's self-query
succeeded and reported no job membership at that instant. It does not establish
the internal cause, the debugger's creation flags, or that the target had earlier
belonged to and subsequently left the original job. The original-three-member
observation was never reached. No retrospective PID adoption is justified.

The target guard remained active and raised before creating its fixture manifest
or reaching its deliberate DebugBreak/write. The transport retained
`InitialFailure.Type=IsProcessInJobNonmember`, the fixture query, and the immediate
`FileNotFoundError` separately. `FixtureOnly`, root PID, nonce, phase and debugger
PID survived the Failed event and bootstrap handler. PowerShell retained this
bound failure in state and reported:

`Fixture transport failed: IsProcessInJobNonmember: FileNotFoundError: No such file or directory`

There are zero ARM, BP_PRESENT, WRITE and capture STOP markers. `Continued=false`
refers to the watch continuation; the ordinary fixture startup continuation had
already occurred. `LastMembership=null`, with no context, sealed capture or witness.

## Closure

Result was **FailedClosedRestored**. The original root exited with code **2**,
the original job reported **Active0**, and the independent helper's cleanup Stop
was attempted/completed without error. Closed, Restored and LeaseReleased are
true; Quarantined and DiagnosticCaptured are false. This exercises error cleanup,
not expiration of the 10-second or 240-second deadline under a stalled controller.

The post-run registry was empty and its process snapshot contained none of the
three trial PIDs. Main's identity, UDP response and file hashes remained unchanged;
all Plan pins still matched. Original-job closure is recorded separately from
the target's failed membership test. The coordinator was notified immediately
that the heavy slot was released.

Nine retained run files total 18,780 bytes. System snapshots exist before/after;
no process/group memory peak is claimed. No retail, attach, PID adoption or new
native attempt is part of the follow-up source investigation.

## Private evidence references

Run directory in the integrated checkout:
`runtime/rig-watch-diagnostic-80c720e005e046e7949fbdf211483084`.
Invocation/evidence directory:
`runtime/rig-watch-plans/fixture-diagnostic-integrated-20261012-091659-815`.
Nonce: `80c720e005e046e7949fbdf211483084`.

| Artifact | SHA-256 |
| --- | --- |
| Approved spec | `f639c0bdf1c3b288f66150e22f7e30e10b336121bc0e322ec5cc41c06f229200` |
| Approved default command | `dd752e8e88ee52e63e1d927343195b120ad6eb75133c6f753acdfa56ddef8e9f` |
| Preflight | `5f88187a8e39010540ae88c5966c59f4f271f29973ef14022490a9e69127eae9` |
| Invocation | `98d4232f5168d17d9003748134833f005b30cfd74109ebf61622148b9b795c8a` |
| After-attempt receipt | `c7d155ae261a4ac27b774c3101ade41c86e983188c16884543625063d55762a8` |
| Transport self-query | `ec979ee89e76131bb35b2a10718879b8eb954260318d50a14e80713bcca3dc31` |
| Fixture self-query | `de7202d7e4428dd5dea00ffdb568743c3e558906623f112a54ab84cc6fdc1ae7` |
| Bound Failed event | `34271e1e6e075af621f00a0e2017d696f036d3d6b8b9747ed1307693d1c54bd8` |
| Original state | `f4763d3cb7656e65baa8bdf1b1a0fd58146da66a54f2431cf848d5d9ca638428` |
| Target stderr | `5408f7137e1752ce6af5cbcaa5ccbad3d3783ca4ca79cf2292f16a2349ce3faf` |
| CDB stdout | `5a5307a8833d3349959e68b6579ca83aef4013e17ddedc8b435d2ea7c07fb217` |
| Complete diagnostic evidence manifest | `b7c28a4ff259d323bd5252719d5a2701d62ca64525e28ec87601ed7c5f52bf49` |

Next work is bounded official-source research of CDB/DbgEng process creation and
ownership, then a reviewed creation correction or targeted observation proposal.
Keep the guard and original-owner requirements. This record grants no retry.

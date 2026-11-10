# AGENTS.md history

Superseded 2026-11-10. This file keeps, byte for byte, the "Product ownership" section that followed the owner's
current-workflow section in `AGENTS.md` until the refactor of 2026-11-10 (it was written on 2026-10-13). It is a
record, not an instruction: the current rules are in `AGENTS.md`. The first section of `AGENTS.md` ("Current
workflow for every agent - owner rule 2026-11-10") was not changed and is not repeated here.

## Where each old rule is now

Sections named below are sections of the current `AGENTS.md`.

| Old rule (2026-10-13) | Where it is now |
| --- | --- |
| Private asset serializers, converters, readers and adapters for the pinned owner ZoneTool fork; no server gameplay or creator distribution policy | "What this repository is", first bullet |
| Classify the change by product; inspect `product.json`, README and the migration map; canonical owner only for declared exports | "What this repository is", second bullet; the migration map is `migration/` (see `docs/INDEX.md`) |
| Do not add server logic or another product's full tree; extend an explicit interface or dependency rather than copying | "What this repository is", second bullet |
| Do not add game assets, binaries, symbols, credentials, player data or decompiled dumps | "Safety rules that never change", first bullet |
| Keep author and license notices and exact upstream pins | "Safety rules that never change", third bullet |
| Never force-push history | "Safety rules that never change", fourth bullet |
| Preserve unrelated work, ignored evidence and frozen plans; never archive a live worktree | "Safety rules that never change", bullet "Other sessions' work is theirs" |
| Historical results do not qualify relocated input identities | "Safety rules that never change", last bullet |
| Main UDP27016 remains untouched | "Safety rules that never change", bullet on tests; rule 9 of the current workflow; "What needs the owner" |
| Do not delete a lease or lower an estimate to bypass refusal | "Safety rules that never change", bullet on leases |
| Owner-private pull requests, merge commits, return clean synchronized main | "How to land", first bullet |
| Do not change visibility, billing, protection or credentials | "Safety rules that never change", second bullet |
| Report source, build, runtime and owner validation separately | "How to work here", last bullet |
| No automatic Codex memory changes | "Safety rules that never change": never change another agent's memory or configuration |

## Rules dropped on purpose, and what replaced each

| Old rule | Why it was dropped | What holds now |
| --- | --- | --- |
| "Existing features, experiments, workers and heartbeat remain paused; refactoring/source tests do not authorize game, server, extraction or deployment." | The owner resumed work on 2026-10-13 and later gave a standing go for tests on private test servers. | Work is open. Only deployment to players needs the owner ("What needs the owner"); tests follow the current workflow and the safety rules. |
| "Use coherent codex/* commits" | Branches of both families exist. | `claude/*` or `codex/*` ("How to land"). |
| "exact-head checks ... Inspect actual CI jobs. Only the existing account quota refusal before any runner/step has the owner's conditional exception; executed failures must be fixed." | GitHub does not start the jobs; their colour is not a result. | Rule 9 of the current workflow: the local `checks.ps1` run on the exact head is the judge ("How to land", `docs/CHECKS.md`). |
| "Heavy native builds need complete shared resource admission." | The fixed admission thresholds were revoked on 2026-10-13. | Rule 4 of the current workflow: the scheduler admits sessions by free memory, builds stay exclusive. The safety part (leases, estimates) is kept. |
| "No upstream PRs" | The server directive of 2026-10-26 allows a clean, minimal upstream contribution where automatic install for players needs it. | Nothing is sent to the public game-client project or any other upstream project without the owner ("What needs the owner"). |

Rules added in the rewrite that were not in the old text: test-server privacy (password, `sv_lanOnly 1`, loopback),
taken from the server rule of 2026-10-12; "tool first" (owner rule, 2026-11-10); every tracked file is an export.

## The old text, byte for byte

The block below is the old section exactly as it stood (1581 bytes, from its heading to the end of the file).

```text
# Product ownership

Private asset serializers, converters, independent readers and bounded extraction/build adapters for the pinned owner ZoneTool fork. No server gameplay or creator distribution policy.

Before editing, classify the change by product and inspect `product.json`,
README.md and the migration map. This repository is the canonical owner only
for its declared exports. Do not add server logic, another product's full tree,
game assets, binaries, symbols, credentials, player data or decompiled dumps.
Extend an explicit interface/dependency rather than copying implementations.
Keep author/license notices and exact upstream pins. Never force-push history.

Preserve unrelated work, ignored evidence and frozen plans. Historical results
do not qualify relocated input identities. Existing features, experiments,
workers and heartbeat remain paused; refactoring/source tests do not authorize
game, server, extraction or deployment. Main UDP27016 remains untouched.
Heavy native builds need complete shared resource admission. Do not delete a
lease or lower an estimate to bypass refusal. Never archive a live worktree.

Use coherent codex/* commits, owner-private PRs, exact-head checks and merge
commits. Inspect actual CI jobs. Only the existing account quota refusal before
any runner/step has the owner's conditional exception; executed failures must
be fixed. Do not change visibility, billing, protection or credentials.
Return clean synchronized main; report source/build/runtime/owner validation
separately. No upstream PRs or automatic Codex memory changes.
```

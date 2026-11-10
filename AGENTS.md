## Current workflow for every agent - owner rule 2026-11-10

This section replaces older test, build and delegation instructions wherever they differ (they are kept below
as history). The owner's keys: best quality, speed, light weight, total efficiency. A result is a measured run,
never a prediction.

Start here, in the server repository (iw7-paris-server): `docs/DEVKIT.md` says which tool answers which question; `docs/TOOLS-INDEX.md` (when it lands) lists every tool on every branch, merged or not; `docs/DEVKIT-PLAN.md` lists what exists, the holes and the open work; `docs/QUALITY-OBSERVATORY.md` says how problems are found without the owner.

1. Check the files first. Before any build or launch run the file checks for your kind of content (weapon audits
   and mod preflight for weapons; `iwz_emitcheck.py check|diff|route|at` for a map source; the build-log gate and
   the loader readback after a build). A build or a launch made to learn what a file check can say is waste.
2. Never copy the game, and never test in the owner's game folder. Make a bench root (`ops/bench/New-BenchRoot.ps1`,
   2 seconds, hard links); remove it only with `ops/bench/Remove-BenchRoot.ps1 -RunFiles`.
3. Test without a game client whenever no screen is needed: `ops/gamelab/Invoke-GameLabHeadless.ps1` runs a test
   plan on a private server with a bot in about 40 seconds and 1.1 GB. Use a client plan
   (`ops/gamelab/Invoke-GameLab.ps1`) only for frames, frame rate or key presses. One plan answers many questions;
   write expectations; the exit code is the verdict.
4. Sessions queue themselves: pass `-WaitForSlotSeconds`; never write retry loops; never stop a game process you
   did not start; never touch a game instance another application started. The scheduler admits sessions by free
   memory, several at once; builds stay exclusive.
5. Need a lab client: `ops/enginelab/Get-LabClient.ps1`. Changed native code: `ops/enginelab/Invoke-EngineLab.ps1`
   (commit, build in about 70 seconds, plans, verdict).
6. Engine questions: the engine map (what is at an address, who calls it, which function mentions a text, console
   variables), the memory watch (where the game keeps a value), the performance recorder with `iw7_perf.py`
   (frame rate and the functions that cost the time; a change under about 5 % needs three runs a side), the freeze
   reporter, the crash reader. All in iw7-mod-components `ops/engine-map` and its `docs/`.
7. Network questions: `ops/netlab/Invoke-NetLab.ps1` (chosen ping, jitter and loss; key-to-server time).
   Long runs: `ops/soak/Invoke-Soak.ps1`. Every place of a map: `ops/atlas/atlas.py` with the `survey` step.
8. Problems go into the ledger (`ops/quality/ledger.py`), not only into a chat; read its `list` before starting.
9. Landing: the local `checks.ps1` run on the exact head is the judge; GitHub's own checks do not run. Do not run
   a live session while a check run is in progress (some checks need the build slot). Nothing is deployed to
   players without the owner, then to both public servers.
10. Delegation in Claude Code sessions (owner, 2026-11-10): the most capable model designs, writes precise briefs,
    reviews and makes or validates the live proofs; Sonnet subagents write code, tests and documents and land
    branches; Opus for the hardest pieces. Briefs name exact paths, commands, limits and what proves the work.

Older lines this replaces: testing in the owner's base game folder; one heavy session on the whole machine;
waiting for GitHub checks; per-test game copies; launching once per question.

# x64-zt-extensions: this repository

The section above is the owner's current workflow, kept word for word. The older text it says is "kept below
as history" now lives in `docs/archive/AGENTS-HISTORY.md`, with a table from each old rule to its place here.
Everything below is current; each rule appears once.

## What this repository is

- Private. Asset tools for the IW7 engine and the owner's ZoneTool fork (`maxis0191/x64-zt`, pinned in
  `product.json`): readers, writers, converters, audits. No server gameplay, no creator distribution policy.
- One of four products: server = iw7-paris-server, engine tools = iw7-mod-components, creator kit =
  iw7-creator-sdk, asset tools = here. Classify a change by product before editing (`product.json`, `README.md`).
  One canonical implementation per component: extend a declared dependency, never copy another product's files
  and never add server logic here.
- Two populations (table in `tools-source/README.md`): living tools you may change, and frozen October
  experiments whose bytes and paths are pinned by tests and by the other products. Do not edit, move or tidy a
  frozen area unless your task is that area.
- Read next: `docs/INDEX.md` (every document), `docs/CREATION-TOOLS.md` (every living tool, its entry command,
  its test, what was proven in the game). All tools of all repositories: `docs/TOOLS-INDEX.md` in the server
  repository (it has landed).
- The tools the section above names under `ops/bench`, `ops/gamelab`, `ops/enginelab`, `ops/netlab`, `ops/soak`,
  `ops/atlas` and `ops/quality` are in the server repository; `iwz_emitcheck.py` is in iw7-creator-sdk. The file
  checks that live here are the weapon audits and `iw7_mod_preflight.py` (`tools-source/asset-bridge/t7-weapons`)
  and the build-log gate and loader readback (`tools-source/asset-bridge/zone-check`).

## Safety rules that never change

- Never commit game assets, binaries, symbols (PDB), executables, credentials, keys, player data, bank data or
  decompiled dumps. Tools read them from a local path given on the command line.
- Never publish private project code into a public fork; never change repository visibility, billing, branch
  protection or credentials. Public distribution is a separate owner decision with its own license review.
- Keep author and license notices and the exact upstream pins.
- Never force-push; never rewrite published history.
- Never test in the owner's game folder and never copy the game (bench roots only). Every test server is
  private: password, `sv_lanOnly 1`, loopback, absent from the server browser. Main (UDP 27016) and the Canada
  server are never part of a test.
- Never stop a game process you did not start; never touch a game instance another application or session
  started.
- Never delete a resource lease and never lower an estimate to get past a refusal.
- Other sessions' work is theirs: preserve unrelated edits, dirty or unpublished worktrees, ignored evidence
  and frozen plans; never archive or remove a live worktree; never change another agent's memory or
  configuration.
- A historical result does not qualify a moved or rebuilt input: new input, new run. Failed results stay
  recorded as failed.

## How to work here

- Tool first. Real work in the game is also the test of the tools. Whenever a tool, the workflow or the environment is seen to be slow, unoptimized, buggy or blind, or a new tool would be a real jump, fix or build that FIRST, prove it with a measured run, document it, then return to the job. Never grind: the same build or launch repeated more than about three times for one question, a cause that is guessed instead of read from data, minutes of waiting for what a file check answers in seconds, a result judged by looking at a picture, a manual step done twice: each of these means stop and improve the tool. (Owner rule, 2026-11-10.)
- Edit the canonical tracked file; never edit a generated source workspace under `runtime/`.
- Every tracked file is an export: add, move or delete a file and edit `product.json` exports in the same
  commit, or the ownership gate fails.
- Python 3.12, standard library only unless the area README says otherwise. No machine paths, personal names,
  e-mail addresses or account names other than the organisation's in tracked files: take paths as arguments or
  environment variables and fail clearly when one is absent.
- A new tool comes with a test registered in `checks.json` and a row in `docs/CREATION-TOOLS.md`.
- Results are measured runs. State separately what was proven by source tests, by a build, in the running
  game, and by the owner.

## How to land

- Branch (`claude/*` or `codex/*`), coherent commits, private pull request, merge commit, then local main clean
  and equal to `origin/main`.
- The judge, once per head, in the background: `./bootstrap.ps1 -Output runtime/<short>`, then
  `./checks.ps1 -Workspace runtime/<short>`. Post the result on the pull request and merge on it. GitHub's own
  checks do not run; never wait for them.
- Main is green. `docs/CHECKS.md` says how to run a subset and lists every test that is kept out of the judge,
  with its reason; anything red in the judge is yours to fix.

## What needs the owner

- Anything deployed to players (then to both public servers, Main and Canada).
- Making anything public. Nothing is sent to the public game-client project (no issue, no pull request, no
  message) without the owner; the same holds for any other upstream project.
- Reopening a retired effort (Spaceland Rhino, the Doom negative-texture candidate).
- Technical choices do not need the owner: decide, record the decision and its measured reason.

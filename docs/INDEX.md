# Documents: where to read

One page that routes a reader. The rules for agents are in `../AGENTS.md`; this page only says which document
answers which question, and which documents are history.

## You want to make or check content

| Document | What it gives |
| --- | --- |
| `CREATION-TOOLS.md` | Every living tool in one table: entry command, document, test, what was proven in the game |
| `CONTENT-AUDITS.md` | The audit contract: weapon audits, build-log gate, loader readback, exit codes, measured results |
| `../tools-source/README.md` | The area map: which folders are living, which are frozen, who pins them |
| `../README.md`, section "Map compiler" | Where the IW7 map compiler is and its command line |

iw7-creator-sdk has a document that is also named `docs/CREATION-TOOLS.md`. It is that product's own table, not a
copy of this one.

## You want to land a change

| Document | What it gives |
| --- | --- |
| `../AGENTS.md`, "How to work here" and "How to land" | The rules: exports, tests, branch, judge, merge |
| `CHECKS.md` | How to run the local judge or a subset, what each excluded test needs, what is not checked |
| `checks-frozen.json` | The tests that are kept out of the judge, each with its reason and date |

## You want the tools of the other repositories

All in the server repository (iw7-paris-server): `docs/DEVKIT.md` (which tool answers which question),
`docs/TOOLS-INDEX.md` (every tool of every repository), `docs/CREATION-CORE.md` (design and build order of the
creation tools), `docs/DEVKIT-PLAN.md` (what exists, the holes, the open work).

## History

`archive/` holds dated records and checkpoint logs. Their bytes are kept as written; they are evidence, not
instructions. `migration/import.json` and older documents name these files as `docs/<NAME>.md`; they are now
`docs/archive/<NAME>.md`, same bytes.
Because the bytes are unchanged, 24 relative links in the archived documents that start with `../` (written when the
files stood in `docs/`) now need one more `../`; sibling links between archived documents still work.

| Archived document | Last change | What it is |
| --- | --- | --- |
| `archive/AGENTS-HISTORY.md` | 2026-11-10 | The superseded section of `AGENTS.md`, with a table from each old rule to its new place |
| `archive/ANIMATION-AI-BRIDGE.md` | 2026-10-12 | Checkpoint log of the animation and AI asset bridge |
| `archive/ASSET-BRIDGE-H1.md` | 2026-10-27 | Checkpoint log of the H1 to IW7 model converter |
| `archive/AUTHORED-PLATFORM-CPP-2026-10-15.md` | 2026-10-15 | Dated record: standalone writer qualification of the original platform |
| `archive/AUTHORED-PLATFORM-FF-D3-2026-10-15.md` | 2026-10-15 | Dated record: stage refusal, attempt closed as failed |
| `archive/AUTHORED-PLATFORM-FF-D4-2026-10-15.md` | 2026-10-15 | Dated record: stage passed, preflight refused |
| `archive/AUTHORED-PLATFORM-FF-D5-2026-10-15.md` | 2026-10-15 | Dated record: fastfile built, readback failed |
| `archive/AUTHORED-PLATFORM-FF-D6-2026-10-15.md` | 2026-10-15 | Dated record: readback passed, publication failed |
| `archive/CONTENT-SURFACES-BRIDGE.md` | 2026-10-13 | Checkpoint log of the content surfaces bridge |
| `archive/DOOM-SOURCE-CANDIDATES.md` | 2026-10-07 | Candidate list of source models, in French |
| `archive/DOOM-TEXTURES.md` | 2026-10-06 | The negative-texture candidate, retired by owner decision on 2026-10-06 |
| `archive/MATERIAL-C-WITNESS.md` | 2026-10-12 | A prepared witness plan that was never run |
| `archive/MODEL-LAB.md` | 2026-10-13 | Description of the October model lab (`ops/model-lab`); the living model route is `env-model` |
| `archive/NATIVE-SOUND-RELEASE-2026-10-12.md` | 2026-10-13 | Dated record: native sound observer build |
| `archive/SOUND-CLIENT-LOOKUP.md` | 2026-10-12 | Protected client lookup for the sound experiment, not compiled or run |
| `archive/SOUND-CLOSURE-REPRESENTATIONS.md` | 2026-10-12 | Static evidence on sound closure representations |
| `archive/SOUND-HTTP-TRANSPORT.md` | 2026-10-12 | Description of the fixed-route sound transport helper |
| `archive/SOUND-JOB-MEMORY.md` | 2026-10-12 | Telemetry note: memory peaks of the sound phases |
| `archive/SOUND-SOURCE-PROJECTION.md` | 2026-10-14 | Helper manifests of the sound experiment; read it before repairing the frozen sound test |
| `archive/SOUND-STANDARDMOD-C-2026-10-13.md` | 2026-10-13 | Dated record: sound mod production and static closure |
| `archive/WEAPON-ASSET-BRIDGE.md` | 2026-10-12 | H1 weapon animation tables; the living weapon route is `t7-weapons` |
| `archive/WORLD-ASSET-BRIDGE.md` | 2026-10-28 | Checkpoint log of the world asset bridge, newest entry first |

The 165 documents inside the tool areas and `ops/` stay beside their code: many are hashed by the tests next to them.
`migration/README.md` explains the extraction of this repository from the server repository on 2026-10-13.

## Statements in frozen or archived files that are no longer true

These files keep their bytes (tests and other products pin them), so the correction is recorded here instead.

- "Features, experiments and workers remain paused" (old `AGENTS.md`, old `README.md`, several frozen documents): the
  owner resumed work on 2026-10-13. Only deployment to players needs the owner.
- Numeric memory admission ("8 GiB physical / 11 GiB commit" in `archive/SOUND-JOB-MEMORY.md`, "12/12 GiB" in
  `archive/SOUND-STANDARDMOD-C-2026-10-13.md` and others): the fixed thresholds were revoked on 2026-10-13; the
  scheduler now admits sessions by free memory.
- "Reuse the base client" and "the Doom dedicated" (`archive/MATERIAL-C-WITNESS.md`, `archive/MODEL-LAB.md`): today
  no test runs in the owner's game folder; a test uses a bench root and a private test server (`AGENTS.md`).
- The ZoneTool fork under its former account name (`archive/ASSET-BRIDGE-H1.md` lines 88 and 436 and ten frozen
  files: three build scripts under `ops/`, and files in `animation`, `h1-fixture`, `model`, `t7-bridge`, `t7-iw7`): it
  is the same repository as `maxis0191/x64-zt`; the hosting site redirects the old name. The three scripts compare
  the pinned repository address with the old name and are pinned by other products, so they are not edited.
- Machine paths of a retired folder layout: one command in `archive/WORLD-ASSET-BRIDGE.md` (line 258), three lines
  in `tools-source/asset-bridge/animation/rig/Build-RigidControlAssets.ps1` and one in
  `tools-source/asset-bridge/weapon-export/Run-PlayerTemplateExport.ps1`. Both scripts are hashed by their tests.
  Give your own paths; never copy these.
- Commands that say "wait for successful CI" or "inspect the CI jobs": GitHub's checks do not run; the local judge
  decides (`CHECKS.md`).

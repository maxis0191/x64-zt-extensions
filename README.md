# ZoneTool extensions

Private asset tools for the IW7 engine and the owner's ZoneTool fork (`maxis0191/x64-zt`, pinned in `product.json`):
readers, writers, converters and audits for models, characters, weapons, sounds, maps and compiled zones.
No server gameplay and no creator distribution policy live here.

One of four products: the server (iw7-paris-server), the engine tools (iw7-mod-components), the creator kit
(iw7-creator-sdk) and the asset tools (this repository). Rules for agents: [AGENTS.md](AGENTS.md).

## What you can do with it today

Every living tool, with its entry command, its test and what was proven in the game, is in one table:
[docs/CREATION-TOOLS.md](docs/CREATION-TOOLS.md).

- Port a Black Ops 3 weapon (models, animations, sounds, effects, materials) into one mod fastfile.
- Turn a glTF file or a Black Ops 3 environment model into game model sources, with collision boxes.
- Write skinned characters, hero outfits and materials, and fit a mesh to the stock zombie parts.
- Read the game's sound banks and write a bank source for a map or a mod.
- Audit content before a build, gate a build log and read a compiled zone back.

## Map

- [tools-source/README.md](tools-source/README.md): which folders are living tools and which are frozen
  experiments of October 2026 (most of the tree), and who pins them.
- [docs/INDEX.md](docs/INDEX.md): which document answers which question; the archive of dated records.

## Run the checks

```powershell
./bootstrap.ps1 -Output runtime/w1
./checks.ps1 -Workspace runtime/w1
```

This local run on the exact head is the judge of a change; the hosted checks do not run. `-Only <id,...>` runs a
subset (the living tools in under 10 seconds). Details, the tests kept out of the judge and what no check covers:
[docs/CHECKS.md](docs/CHECKS.md).

Prerequisites: Git, PowerShell 7.4+, Python 3.12, and the GitHub CLI signed in with read access to this private
repository (bootstrap downloads the pinned dependency archive once; offline, pass
`-DependencyArchive <dependencies.zip>`). The image tests use the hash-pinned Pillow requirement in
`ops/doom-textures`. No check command calls Node.js or Java, and a search of the test scripts on 2026-11-10 found
no call; only the hosted workflow installed Node.js. Native compilation, which no check performs, needs the VS2022
C++ toolchain.

## How the source package works

- Edit the canonical tracked file here. Never edit a generated source workspace under `runtime/`.
- Every tracked file is an export listed in `product.json` (or one of a few meta files). The ownership gate, first
  step of `checks.ps1`, refuses a tracked file that is not listed and a listed file that is not tracked.
- `bootstrap.ps1` composes a fresh, bounded source workspace: this repository's exports plus only the listed files
  of the three dependencies, at the exact revisions of `product.json`. Dependencies are not vendored here. The
  archive named in `dependency-package.json` is checked by SHA-256, length, members, owners and commits; it holds
  selected text sources, never tools, game data or binaries. A missing archive fails clearly; no other version is
  selected.
- The composer refuses dirty, redirected, oversized (1 MiB a file, 32 MiB in all), binary and overlapping sources.
  One reviewed generated header (`weapon-export/native_pair_body_schema.hpp`) is accepted by its exact digest.
- The composition receipt records every owner, commit, Git blob and byte hash. It does not qualify a native build
  and does not inherit an older runtime receipt.
- Composing and checking install no game, copy no retail asset, build no native code, launch nothing and deploy
  nothing. Build and run entry points inside the package keep their own input, identity and resource gates; run one
  with `bootstrap.ps1 -Entry ops/<entry>.ps1 -Arguments @(...)`.

## Who pins this repository

The three other products list files of this repository in their own `product.json`, at October revisions:
iw7-paris-server (36 files), iw7-creator-sdk (73 files), iw7-mod-components (8 files), as read on 2026-11-10. All
of them are in the frozen areas (`ops/`, `src/` and folders of `tools-source/asset-bridge`); none pins a November
tool or a document. The tests of the frozen areas also hash each other's files. This is why the relative layout is
a compatibility contract and no folder was moved: moving a pinned file breaks a consumer or a test.

## Map compiler

The IW7 map compiler (`zonetool -iwzcompile`, lightmaps, static models, door
brush models, trigger volumes, darkness lights) is on the main line of the owner
ZoneTool fork `maxis0191/x64-zt` since pull request #12, merge commit
`07a5aa08d07d26e3a5011c440ec9fcad8d5bafe9`. Build that main line; no branch is needed.

```
zonetool.exe -headless -unbuffered-io -iwzcompile <template zone> <template map> <new map> <source dir>
zonetool.exe -headless -unbuffered-io -iwzcompile cp_zmb_tpl cp_zmb cp_iwz <work>\iwz_src
```

- Takes: `<source dir>` with `world.bin`, `colmap.hkx`, `navgraph.bin`, `ents.txt`
  (optional `lighting.txt`, `lights.txt`, `probes.txt`, `smodels.txt`, `triggers.txt`,
  `scriptables.txt`, `lightmap/`), the stock template map dumped at
  `<work>\zonetool\<template zone>`, and the game `zone` files in the work folder.
  Switches are environment variables (`IWZ_GEN_TOME=1`, `IWZ_KEEP_ENTSHAPES=1`,
  `IWZ_KEEP_SUBMODELS=1`, `IWZ_TRIGGER_SHAPES=1`, ...).
- Writes: `<work>\dump\<new map>\` (`maps\cp\<map>.d3dbsp.*`, `images`, `lightmaps`,
  `transient_zones`): 18 files, 104 MB for Station Zero, ready for `-buildzone`.
- Measured: 23 to 72 s per compile of the Station Zero input (cold start 72 s,
  warm 23 to 44 s, 7 runs). The output of the main-line build equals the branch build
  except for run-to-run padding bytes and the nine generated trigger shapes
  (volumes); see the pull request for the byte comparison.
- The creator SDK map generator (`iw7-creator-sdk`, `tools-source/iwzmap`,
  `build-sz2.ps1`) calls this command; point its `-ZoneToolExe` at a main-line build.
- The patches in this repository still target ZoneTool `fab9358`
  (`product.json` `upstream`), which this repository keeps as its patch base:
  against the new main line the `flac-dump` and `world-observer` patches no longer
  apply (`sound_bank.cpp`, `zonetool.cpp` includes) and need a rebase before that pin moves.

## What is never in the repository; licensing

Commercial game assets, dumps, installed SDKs, symbols (PDB), executables, credentials and player data are excluded;
tools read them from a local path you give. Preserve upstream notices and per-file provenance
([licenses/README.md](licenses/README.md), `LICENSE.upstream`). No blanket license is granted to all private
adaptations. This repository is private and complements the public owner forks; it does not publish private project
code into them. Public distribution requires its own license and privacy review and an owner decision.

## History

- [migration/README.md](migration/README.md): this repository was extracted from the server repository on
  2026-10-13 with authors and commit messages preserved; `migration/import.json` and `migration/commit-map.txt` map
  the original paths and commits.
- [docs/archive/](docs/archive/): dated records and checkpoint logs. They keep their original bytes and claims.
  Older commands in them refer to their original frozen layout.
- Failed results stay recorded as failed. A moved or rebuilt source needs a new plan and a new run; an old runtime
  receipt never qualifies a newly composed input.
- To roll back an integration, restore its earlier dependency revision in a new reviewed commit, compose a fresh
  source package and rerun the checks. This never restores or deploys game data, banks or binaries.

# ZoneTool extensions

Private asset serializers, converters, independent readers and bounded extraction/build adapters for the pinned owner ZoneTool fork. No server gameplay or creator distribution policy.

This repository is private. It complements the public owner forks; it does not
publish private project code into them. See `product.json` for exact source
revisions and explicit file dependencies. Source extraction preserved authors
and commit messages; `migration/import.json` and `migration/commit-map.txt` map
the original server paths/commits to this history.

## Editing and source preparation

Edit the canonical tracked file here. Do not edit generated source workspaces.
The existing relative source layout is an explicit compatibility contract used
by hash-sensitive tools. Dependencies contribute only their listed files to a
fresh, bounded source package; they are not vendored into this repository.
The composition receipt records every owner, commit, Git blob and checkout-byte
hash. It does not qualify a native build or inherit an older runtime receipt.

The [owned rig binding](tools-source/asset-bridge/animation/rig/OWNED-RIG-BINDING.md)
is a generic decoded-data interface for model bone order, skin influences and
clip channels. It keeps complete typed input identities and immutable results;
authored checks do not qualify real assets or engine playback. BO3 interoperability
and the two secondary demonstrations do not gate generic engine modding work.

Run the pinned IW7-Mod `ops/source_workspace.py` with `--project`, exact
`--revision`, one `--source PRODUCT=CHECKOUT` per dependency, and a fresh `--output`.
Each source checkout must match the manifest revision and have clean tracked
files. Paths with spaces are supported. Missing, different, dirty, redirected,
oversized, binary and overlapping sources are refused before output creation.
Then run `checks.ps1 -Workspace <output>` from this canonical checkout.

The command does not install a game, copy retail assets, build native code,
launch a process fixture, deploy, publish, or change Main. Build/run entrypoints
inside the package retain their own input, identity, resource and authorization
gates. Feature experiments remain paused until the owner's explicit GO.

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

## Evidence and rollback

Historical documents and pinned plans retain their original bytes and claims.
Use the recorded original checkout/commit for a frozen experiment. A moved or
rebuilt source needs a new plan and qualification. Failed results remain failed.
To roll back an integration, restore its earlier dependency revision in a new
reviewed commit, generate a fresh source package, and rerun the relevant tests.
This never restores or deploys game data, banks or binaries automatically.

## Licensing

Preserve upstream notices and per-file provenance. No blanket license is granted
to all private adaptations by this extraction. Public distribution requires its
own license/privacy review and owner decision. Commercial game assets, dumps,
installed SDKs, PDBs, executables, credentials and player data are excluded.

## Reproduce the source checks

Prerequisites: Git, authenticated GitHub CLI with read access to this private
repository, PowerShell 7.4+, Python 3.12 and Node.js 22. Native source checks also
use Java 21; pure native compilation requires the existing VS2022 C++ toolchain.
Asset image tests use the hash-pinned Pillow requirement in ops/doom-textures.

```powershell
./bootstrap.ps1 -Output "$PWD/runtime/source inputs"
./checks.ps1 -Workspace "$PWD/runtime/source inputs"
```

Bootstrap downloads only the immutable source dependency archive named in
`dependency-package.json` from this repository's private release. Its SHA-256,
length, members, owners and commits are checked. It needs no cross-repository
CI secret. Offline use: supply `-DependencyArchive <downloaded dependencies.zip>`.
The archive contains selected text sources, never tools, game data or binaries.
A missing archive fails clearly; no fallback version is selected.

The source composer accepts the reviewed generated body-schema header by its
exact owner, path, blob and byte digest. Other files retain the normal 1 MiB
limit, and the package retains the 32 MiB total limit. An older dependency
archive lacked this qualification and refused the current source tree. The
current archive updates the native source pin without changing old receipts.

Run an authorized operation from the generated package, or use
`bootstrap.ps1 -Entry ops/<entry>.ps1 -Arguments @(...)`. Canonical repositories
are editing locations; operations requiring another product must use prepared
inputs. Older commands in dated documents refer to their original frozen layout.
Do not reuse an old runtime receipt for a newly composed input.

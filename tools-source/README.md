# Area map: what is living and what is frozen

This repository holds two populations side by side. **Living** areas are the tools used today; change them freely,
with a test. **Frozen** areas are the experiments of October 2026: their file paths and bytes are pinned by their own
tests and by the three other products, so they are kept exactly as they are. Nothing was moved to make this split:
the relative paths are a compatibility contract.

"Last change" is the date of the last commit that touched the area on the main line (read on 2026-11-10).
"Pinned by" counts the files of the area that another product lists in its `product.json`
(server = iw7-paris-server, sdk = iw7-creator-sdk, components = iw7-mod-components). Check ids are the ids in
`checks.json`; `docs/CHECKS.md` says how to run one.

## Living areas

| Area | Last change | What it is | Entry document | Check id | Pinned by |
| --- | --- | --- | --- | --- | --- |
| `asset-bridge/t7-weapons` | 2026-11-10 | Black Ops 3 weapon port pipeline, weapon audits, mod preflight, animation codec, materials, effects | `README.md`, `STATUS.md` | `tools-source-asset-bridge-t7-weapons` | none |
| `asset-bridge/zone-check` | 2026-11-10 | Build-log gate and loader readback of a compiled fastfile | `README.md`, `docs/CONTENT-AUDITS.md` | `tools-source-asset-bridge-zone-check` | none |
| `asset-bridge/env-model` | 2026-11-09 | Environment models from glTF or Black Ops 3, model back to glb, collision boxes | `README.md` | `tools-source-asset-bridge-env-model` | none |
| `asset-bridge/iw7-audio` | 2026-11-08 | Sound bank reader and writer for maps and mods | `README.md` | `tools-source-asset-bridge-iw7-audio` | none |
| `asset-bridge/t7-map` | 2026-10-27 | Black Ops 3 map (Kino der Toten) to rigid models, images, materials and sounds | `README.md` | `tools-source-asset-bridge-t7-map` | none |
| `iw7-skinned-writer` | 2026-11-10 | Skinned character model writer, hero materials and outfits | `README.md`, `NOTES.md` | `tools-source-iw7-skinned-writer` | none |
| `iwz-zombie-kit` | 2026-11-10 | Fits an authored mesh to the stock zombie parts | `README.md`, `NOTES.md` | `tools-source-iwz-zombie-kit` | none |

The table of every living tool with its entry command, its test and what was proven in the game is
`docs/CREATION-TOOLS.md`.

## Frozen areas under `tools-source/asset-bridge`

| Area | Last change | What it is | Entry document | Checks | Pinned by |
| --- | --- | --- | --- | --- | --- |
| `animation` | 2026-10-16 | Animation envelope and skeleton preflight; rig experiments under `rig/` | `README.md` | 10 (`tools-source-asset-bridge-animation`, ...) | server 1, sdk 7, components 1 |
| `common` | 2026-10-12 | One shared stock-binding helper and its source test | none (this row) | `Test-StockBindingSource` | server 1, sdk 1 |
| `h1-fixture` | 2026-10-18 | Original H1-format parser fixture and bounded native observation | `README.md` | 7 (`tools-source-asset-bridge-h1-fixture`, ...) | sdk 4, components 3 |
| `model` | 2026-10-27 | Full ZoneTool build job and Blender bridge of the October model experiment | none (this row) | `tools-source-asset-bridge-model` | server 1, sdk 1 |
| `recipient` | 2026-10-12 | Recipient observations, source-only runner | `README.md` | 8 (`tools-source-asset-bridge-recipient`, ...) | sdk 8 |
| `rig-abi` | 2026-10-12 | Offline write observation proposal for one model surface field | `README.md` | 4 (`tools-source-asset-bridge-rig-abi`, ...) | none |
| `surfaces` | 2026-10-15 | Material compiler experiment, authored DDS material, the sound experiment under `sound/` | `AUTHORED-DDS-MATERIAL.md`, `sound/README.md` | 27 (`tools-source-asset-bridge-surfaces`, `surfaces-sound-test_*`, ...) | server 19, sdk 23, components 1 |
| `t7-bridge` | 2026-10-15 | Black Ops 3 to IW7, selected static model (native bridge experiment) | `README.md` | 36 (`tools-source-asset-bridge-t7-bridge`, ...) | server 1, components 1 |
| `t7-iw7` | 2026-10-16 | Black Ops 3 images and build profile experiments, 210 files, almost all at one level | none (this row); start at `BUILD-PLAN.md`, `T7-IMAGES.md` | 15 (`tools-source-asset-bridge-t7-iw7`, ...) | sdk 7 |
| `weapon` | 2026-10-12 | Weapon animation bridge and slot contract of October (the living weapon route is `t7-weapons`) | none (this row) | `tools-source-asset-bridge-weapon` | none |
| `weapon-export` | 2026-10-19 | Bounded player and Pack-a-Punch template source export support | `README.md` | one per test file (`weapon-export-test_*`) | none |
| `world` | 2026-10-27 | Observer harness, physics probe, original arena, platform contact | `original-arena/README.md` | 6 (`tools-source-asset-bridge-world`, ...) | sdk 8 |

## Frozen areas outside `tools-source` (named here because nothing else explains them)

| Path | Last change | What it is | Checks | Pinned by |
| --- | --- | --- | --- | --- |
| `ops/doom-source` | 2026-10-12 | October model lab for one source model (inspection, rigid mesh preparation, writer, fastfile). Its README is in French. | 8 (`test_writer`, `test_ff`, ...) | server 7, sdk 4 |
| `ops/model-lab` | 2026-10-15 | October authored-model fastfile lab (the living model route is `asset-bridge/env-model`) | `model_lab_test` (in `tests/ops`) | server 2, sdk 10 |
| `ops/doom-textures`, `ops/Build-DoomTextureTool.ps1`, `ops/Prepare-DoomTextureWork.ps1` | 2026-10-06 | Negative-texture candidate, **retired** by owner decision on 2026-10-06 | `doom_texture_test` (in `tests/ops`) | server 1, components 1 (the Pillow requirements file) |
| `ops/Build-EnemyZoneTool.ps1` | 2026-10-04 | ZoneTool build script; nothing in this repository calls it | none | server, components |
| `ops/Build-RhinoZoneTool.ps1`, `src/custom_scripts/cp/experiments/zonetool_rhino.hpp` | 2026-10-04 | Spaceland Rhino, **retired** by owner decision on 2026-10-15; kept because the server lists both files | none | server |
| `ops/Inspect-Texture.py` | 2026-10-02 | Texture inspection script; unreferenced, no check | none | none |
| `ops/Test-AssetSourcePins.ps1` | 2026-10-13 | Source test of the asset source pins | `asset-source-pins` | none |
| `tests/ops` | 2026-10-15 | Four files: two Python tests and two PowerShell fixtures they call. Every other test sits beside its code. | `doom_texture_test`, `model_lab_test` | none |

`ops/` is not "operations" here: it is the October model and texture lab plus two ZoneTool build scripts. `src/` holds
one file. Both names are kept because other products pin the paths.

## Three rules

1. A frozen area's files are pinned by tests and by other products: do not edit, rename or reformat them unless your
   task is that area, and then expect to refresh its pins.
2. Frozen documents describe October procedures (testing in the base client, numeric memory thresholds, `codex`
   worktree paths, feature work "paused"). The current procedure is `AGENTS.md`. Statements known to be out of date
   are listed in `docs/INDEX.md` so that nobody has to edit the frozen bytes.
3. A new tool goes in a new folder under `tools-source/asset-bridge/` with a README, a test registered in
   `checks.json` and a row in `docs/CREATION-TOOLS.md`.

## Decisions not to move anything (recorded 2026-11-10)

- The flat frozen areas (`t7-iw7` 210 files, `t7-bridge` 132, `weapon-export` 79, `h1-fixture` 40) stay flat: their
  tests hash each other's files and other products pin their paths.
- `t7-weapons` (living, 63 files at one level) is not split: its tests discover by folder, the preflight imports its
  siblings by name, and weapon ports are being worked on today. Its README and `docs/CREATION-TOOLS.md` are the guide.
- `iw7-skinned-writer` and `iwz-zombie-kit` stay outside `asset-bridge`, although their peers are inside: moving them
  would change the commands in every document and in the scripts of running sessions.
- `ops/`, `src/` and `tests/ops` keep their names (see above).

One name to know: several frozen files call the ZoneTool fork by its former account name. It is the same repository
as `maxis0191/x64-zt` (the hosting site redirects the old name); `product.json` uses the current one.

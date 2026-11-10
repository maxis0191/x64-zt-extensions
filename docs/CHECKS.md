# Checks: the local judge

GitHub's own checks do not run on this account. The judge of a change is the local run of `checks.ps1` on the exact
head that will be merged. **Main is green: a red check on your head is yours to fix.**

## Run the judge

```powershell
./bootstrap.ps1 -Output runtime/<short>      # composes the source workspace of the committed head (about 1 minute)
./checks.ps1 -Workspace runtime/<short>      # ownership gate, then every check of checks.json
```

- `bootstrap.ps1` refuses a dirty tree: commit first. It downloads the pinned dependency archive once
  (`dependency-package.json`); offline, pass `-DependencyArchive <dependencies.zip>`.
- `checks.ps1` first runs the ownership gate (every tracked file is an export of `product.json` or a meta file, and
  every export is tracked; one second), then each entry of `checks.json` from the workspace folder. It writes
  `results.json` and one log per check under `runtime/checks-<id>` (or `-Output <dir>`), and exits non-zero when a
  check fails.
- Run it once per head, in the background, and post the result on the pull request. Do not run a live game session
  while it runs: some checks take the machine's build slot. A check whose log says `Resource busy` or
  `already reserved` lost that slot to another session; run it again alone with `-Only`.
- A full run (no `-Only`) refuses a dirty tree (`git status --porcelain` not empty), runs
  `git diff --check origin/main...HEAD` (whitespace errors, as the hosted workflow did) and fails if the tree or
  `HEAD` changed before it ended.

## Run a subset

```powershell
./checks.ps1 -Workspace runtime/<short> -Only tools-source-asset-bridge-t7-weapons
./checks.ps1 -Workspace runtime/<short> -Only tools-source-asset-bridge-t7-weapons,tools-source-asset-bridge-zone-check
```

`-Only` takes check ids (comma separated). The seven checks of the living tools take under 10 seconds together
(7 seconds when measured):

`tools-source-asset-bridge-t7-weapons`, `tools-source-asset-bridge-zone-check`, `tools-source-asset-bridge-env-model`,
`tools-source-asset-bridge-iw7-audio`, `tools-source-asset-bridge-t7-map`, `tools-source-iw7-skinned-writer`,
`tools-source-iwz-zombie-kit`.

A subset is for working. The full run stays the judge for a merge. The workspace is tied to the commit it was
composed from: after a new commit, bootstrap a new one. A living tool's tests also run straight from the checkout,
without a workspace: `python -B -m unittest discover -s tools-source/asset-bridge/t7-weapons`.

## What the judge contains

149 checks. Measured on 2026-11-11: bootstrap 57 seconds and checks 545 seconds on e1f23d2, bootstrap 38 seconds
and checks 572 seconds on e518808, 149 passed both times. Seven guard the living tools; the others guard the frozen October areas (see
`../tools-source/README.md`). The slow ones: `weapon-export-test_build_default` (65 to 120 seconds),
`weapon-export-test_export_default` (50 to 80), `Test-T7ResidentExport` (about 50), `Test-T7CatalogueBootstraps`
(about 40). The eighteen `weapon-export-*` entries take about 200 seconds together.

Two kinds of entries need a word:

- **Plain temp folder.** `weapon-export-test_build_default`, `weapon-export-test_export_default` and
  `weapon-export-test_definition_export` set `TEMP` and `TMP` to a folder inside the run's output folder. The frozen
  runner they test (`Run-PlayerTemplateExport.ps1`) walks every parent folder of its input with `Get-Item`, which
  does not see hidden folders, and the default temp folder of a Windows account sits under a hidden one. With the
  default temp folder 61 of these tests fail with "Could not find item"; with a plain one all pass (measured
  2026-11-10). The tests and the runner are unchanged.
- **Checkout tests.** `weapon-export-test_native_body_schema_table_source`, `weapon-export-test_native_pair_bodies_source`,
  `weapon-export-test_pair_json_core_source` and `weapon-export-test_pair_owned_session_source` read `product.json`,
  which the checkout has and the composed workspace does not. They run from the checkout; `checks.ps1` tells them
  where it is through the variable `IW7_PRODUCT_ROOT`. Run through `check_product.py` directly, they stop with a
  message that says so. They therefore judge the working tree, not the composed head, so a full run of `checks.ps1`
  refuses a dirty tree at its start and fails if the tree or `HEAD` changed by its end; keep the tree clean from
  bootstrap to the end of the run.

The hidden-folder defect of the frozen runner is real and still open: the plain temp folder keeps its tests
judged, it does not repair the runner.

These two causes, not changed provider bytes, were the whole of the former red check
`iw7-player-template-source-support` (61 failures and 6 errors of 266 tests on every head from 2026-11-09 to
2026-11-10). It is now one entry per test file and all 266 tests are judged.

## Tests kept out of the judge

`checks-frozen.json` lists them with command, reason and date. Nothing was deleted and no assertion was weakened.

| Entry | Kind | Reason in one line |
| --- | --- | --- |
| `surfaces-sound-test_sab_ff` | fails since 2026-10-27 | The sound experiment pins the bytes of a scheduler file of iw7-mod-components in a dated manifest; the dependency pin moved, no new manifest was written |
| `surfaces-sound-test_helper_sources` | fails since 2026-10-27 | Same cause |
| `Test-T7BootstrapGroup` | fails since 2026-10-15 | The qualifier accepts six reviewed sizes of `T7Catalogue.Profile.ps1` (about 150,000 bytes); the file is 203,333 bytes |
| 16 PowerShell test scripts (`test_rig_readback`, `Test-H1Plan`, six under `surfaces/sound/native-checksum`, six under `surfaces/sound`, `Test-PlayerExportStockSource`, `test_observer_plan`) | needs input | Each takes a reviewed plan, a prepared candidate, a provider folder, a game dump file or an installed toolchain by path; a source check has none |

The other seven test files of `surfaces/sound` are judged, one entry per file (`surfaces-sound-test_*`).
Repairing the three failing entries is work inside frozen code (a new dated manifest, a reviewed tuple): a task of
its own, not a side effect of another change. When one is repaired, move its entry back to `checks.json`.

## Test scripts that have no entry because a registered check already runs them

| Script | Run by |
| --- | --- |
| `animation/rig/test_rig_compiler.ps1`, `test_rig_runner.ps1`, `test_rig_owned_phase.ps1` | `test_rig_executor.py` (check `tools-source-asset-bridge-animation-rig`) |
| `t7-bridge/Test-T7ResidentMultiSurfaceBuild.ps1` | `Test-T7ResidentExport.ps1` (check `Test-T7ResidentExport`) |
| `t7-iw7/Test-T7InputBindings.ps1` | `Test-T7BuildProfile.ps1` (check `Test-T7BuildProfile`) |
| `t7-iw7/Test-IncomingImageBuild.ps1`, `Test-ImageRegistrationBuild.ps1` | `Test-RegistrationBindingsBuild.ps1` (check `registration-bindings-build-source`) |
| `world/original-arena/test_coverage.py` | imported by `test_arena.py` (check `world-original-arena`) |
| `tests/ops/Test-AuthoredModelFF.Source.ps1`, `Test-ModelFFPathPreflight.Source.ps1` | fixtures of `tests/ops/model_lab_test.py` (check `model_lab_test`) |

Paths in the two tables are under `tools-source/asset-bridge/` unless they start with `tests/`. The scripts of
the first five rows (eight scripts) were also run alone on 2026-11-10 and passed.

## What no check covers

| Not checked | Why |
| --- | --- |
| Blender export (`iw7-skinned-writer/blender_export.py`, the Blender scripts of `env-model` and `iwz-zombie-kit`) | needs Blender |
| `iw7-skinned-writer/m1_proof.py`, `m2_proof.py`, model and material writers on real assets | need a local game dump |
| `iw7-skinned-writer/ops/*.ps1`, `iwz-zombie-kit/run_zombie.py` end to end | need a game dump, Blender, texconv and, for the proof script, a bench root and a private test server |
| `zone-check/Read-CompiledZone.ps1` | needs the game loader (by design; its Python reader is checked) |
| `ops/Inspect-Texture.py`, `ops/Build-*.ps1`, `ops/Prepare-DoomTextureWork.ps1` | need tools that a source check does not have (ZoneTool sources, a C++ toolchain) |
| The native fixture of `.github/workflows/selected-xpak-fixture.yml` | needs the VS2022 C++ toolchain and a downloaded lz4 source; it has no local entry |

No check proves anything in the running game. Game proofs are made with the tools of the server repository
(`AGENTS.md`, first section) and recorded in the area's own document and in `CREATION-TOOLS.md`.

## The hosted workflows

`.github/workflows/source-checks.yml` and `selected-xpak-fixture.yml` start by hand only (`workflow_dispatch`).
The hosting account does not start their jobs, so a run there, of either colour, is not a result.

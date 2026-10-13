# Resident rigid export connection

This source addition connects the existing Model Lab to an already produced
`t7-iw7-resident-static-v1` XMB/XSB export. It does not launch the T7 exporter,
convert a second mesh, extract textures, or qualify native/exporter provenance.
The original 24-vertex/12-triangle cube route and its measured FF/reader tuples
remain available. Its corrected LOD0 distance of 1000000 is preserved.

The first selected donor is `p7_fre_platform_cap_02`, zone `mp_freerun_04`, LOD0.
This change has been checked with synthetic bytes only. No real donor export,
FF build, resource admission, game run or rendering is part of that validation.

## Inputs and derivation

Future preparation, after an export and its independent receipt review:

```powershell
python -B -S ops/model-lab/prepare_ff.py `
  --export-root $exportRoot --request $requestPath `
  --manifest "$exportRoot/manifest.json" --output $freshSourceRoot `
  --rebind-material mopw/character_park_clown_zombie_shoes
```

The existing independent `tools-source/asset-bridge/t7-iw7/readback.py` validates
the receipt, hashes and serialized static profile: one root/bone/surface/rigid
list/material, 3..65535 vertices and 1..65535 nondegenerate triangles. Request and
native receipt are limited to 4 KiB each, XMB to 1 MiB and XSB to 16 MiB. Model Lab
additionally requires portable CSV/config names (`A-Z a-z 0-9 _ . / -`, safe path
segments). The actual XSB name comes from the verified receipt, never a guessed
suffix. The export root remains untouched; byte-exact raw snapshots are retained
under `evidence/` in the fresh preparation directory.

The required material option changes only the standalone material ASSET string
in the derived XMB. It refers to the existing IW7 recipient material; no BO3 or
IW7 texture/material payload is copied. XSB is byte-identical. All remaining XMB
bytes, including bounds, rig and LOD metadata, are preserved by default.

An additional **explicit** `--lod-distance 1000000` changes only the four bytes
of `lodInfo[0].dist`. `derived-export.json` records both old/new values and both
declared spans. It has its own `iw7.model-derived-export/1` schema; it is never
passed off as the native export receipt. Revalidation reconstructs the declared
derivation from the preserved snapshots and rejects any third change even when
a staged-file hash has been updated.

Zero or a distance below the Model Lab scene's conservative 256-unit margin is
accepted as a source export but blocks this scene's FF preparation gate with an
explicit diagnostic. This guard is not a universal asset-validity rule, a full
culling analysis, or evidence that the donor will be visible. Other sufficient
finite source distances remain unchanged. Dimensions, pivot, camera placement,
LOD behavior and actual pixels still require the future donor run.

## Existing FF and runtime route

`Build-ModelFF.ps1` detects the resident geometry profile in the preparation
plan, checks the derivation before stock staging, and uses the existing resource
lease, stock transaction, debugger, build/verify/dump commands and restoration
guards. The fixed zone is still `paris_model_probe`. Only the two asset input
paths and expected XModel/XModelSurfs inventory names vary. The NCS asset remains
`ncs_mdl_paris_model_probe`, with the actual XModel name in `stringList`.

The resident route uses Python (`-Python` selects an executable) instead of the
cube's native `-ReaderRun`. After the future FF dump, `rigid_export.py verify-dump`
reuses the independent reader and compares parsed model/mesh metadata plus every
packed vertex, triangle and rigid-list byte against the derived source. Opaque
nonzero pointer values may differ between serializations. The bounded receipt
`geometry-roundtrip.json` binds the FF hash/length, source-plan/derivation hashes
and the two retained dump hashes. The FF is limited to 32 MiB. Its false flags
retain the provenance, donor-fidelity, dependency-payload, rendering and runtime
limits of this comparison.

For a subsequent separately authorized runtime witness, `Agent-Lab.ps1` requires
the existing `-ObservationMode model -ModelBuildRun ...` and
`-ModelReaderEvidence geometry-roundtrip.json`, plus an independently reviewed
tuple supplied as `-ModelReviewedBytes`, `-ModelReviewedSHA256` and
`-ModelReviewedEvidenceSHA256`. Do not auto-approve these values from mutable
build metadata. Historical cube admission continues to use its original tuples;
these parameters cannot bypass that allowlist.

The existing protected scene precaches/requests the validated actual XModel
using `paris_model_asset`; it defaults to the cube when unset. Logs identify the
actual model, and runtime observation matches that escaped name. The existing
capture scenario is unchanged. `fs_game` stays `mods/paris_model_probe`, and HTTP
stays `/mods/paris_model_probe/mod.ff`. An existing larger cache is accepted only
if its bytes/hash match the reviewed rigid FF; foreign cache contents are kept
and refused. `SCRIPT_MODEL_REQUESTED`, `READY_MODEL` and a correct download do
not prove visible pixels, correct shading, textures or owner gameplay acceptance.

The shared `HudHttp.cs` has one explicit `CreateRigidModel` factory, fixed to
ModelRoute and at most 32 MiB, called only after the reviewed tuple gate. All
legacy constructors and their existing size/route limits remain unchanged.

## Source validation

`python -B -S tests/ops/model_lab_test.py -v` covers original cube regression,
synthetic irregular geometry, exact material-only and optional LOD derivations,
third-change refusal, packed normal/UV/index mutation refusal, actual names/NCS,
explicit FF/evidence admission, cache preservation and runtime claim limits.
Its FF stand-ins are labeled synthetic data and are never engine inputs.
Resource/process functions are mocked where exercised; no game is launched.

Source checkpoint (2026-10-13): 19 Model Lab tests, 31 independent resident
readback tests and five existing shared HTTP regression tests passed. The agent
ownership suite passed 41 controls; the mocked capture-evidence suite and the
four changed PowerShell files' AST parse passed. GSC runtime compilation, native
FF build and donor rendering remain unexecuted and unqualified.

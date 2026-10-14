# Resident rigid export connection

This source addition connects the existing Model Lab to an already produced
`t7-iw7-resident-static-v1` or explicitly versioned
`t7-iw7-resident-static-v2` XMB/XSB export. It does not launch the T7 exporter,
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

## Explicit multisurface v2

V1 keeps its one-surface contract, scalar `--rebind-material`, manifest schema
`iw7.t7-iw7-resident-export/1` and 4 KiB manifest cap. V2 requires the paired
`iw7.t7-iw7-resident-export/2` and `t7-iw7-resident-static-v2` identifiers; neither
surface count nor file size implicitly upgrades a v1 artifact. The selected
profile remains `resident-rigid-one-lod`: one root/bone, one LOD, 1..255 ordered
surfaces, one rigid list per surface, 3..65535 vertices and 1..65535 triangles
per surface. The model totals must equal all surface records. Material slots
stay in surface order, including repeated dependencies.

Before reading geometry, the common contract and independent reader recompute
`geometry_work_bytes_upper_bound = 256 + 384*N + 60*V + 12*T`, capped at 16777216
bytes. `N`, `V`, `T` are surface count and summed vertex/triangle counts. Every
logical occurrence counts in full, including aliases. This accounts for the
source and destination geometry buffers; it is neither a total RAM/CPU estimate
nor a serialized-file cap. The per-surface allowance includes the 96-byte T7
surface; the earlier 368-byte coefficient assumed 80 bytes and is invalid.
Model Lab rejects metadata claiming that old work value. At `N=6`, `V=267000`,
`T=62888`, the corrected total is exactly 16 MiB; `T=62896`, previously at the
boundary, exceeds it by 96 bytes. V2 manifest bytes have a separate 256 KiB cap,
strings remain bounded to 255 portable ASCII characters, XMB remains at 1 MiB and XSB at
16 MiB. Model Lab v2 derived receipts/plans have a separate 1 MiB metadata cap
for up to 255 surface summaries and material mappings; their v1 cap stays 64 KiB.
No resource admission, mutable-space, FF or HTTP limit is increased by v2.

Future v2 preparation uses `--material-rebinds path/to/rebinds.json` in place of
the v1 scalar option. The JSON file (at most 256 KiB) is an explicit ordered list
with one entry per slot. For example, a **synthetic two-surface** export uses:

```json
[
  {"slot": 0, "source": "original/clay", "target": "mopw/character_park_clown_zombie_shoes"},
  {"slot": 1, "source": "original/clay", "target": "mopw/character_park_clown_zombie_shoes"}
]
```

Each source must match the native manifest's material at that slot. Only the
existing proven recipient reference above is allowed in this step. Shared
ASSET aliases must request the same target. The independent reader identifies
their defining string spans; derivation patches each definition once and keeps
alias record bytes and ledger indices intact. It does not collapse surfaces,
merge their geometry, extract textures or copy material payloads. The recipient
CSV/inventory deduplicates recipient references, while the plan preserves all
ordered slots. The model still has exactly two payload files and five source
files. Optional LOD derivation keeps its existing explicit four-byte scope.

V2 uses internal `iw7.model-derived-export/2`, `iw7.model-ff-plan/2` and
`iw7.model-rigid-roundtrip/2` receipts. They retain `surface_records`, ordered
`material_references` and the recomputed work bound where applicable. Readback
checks every surface's packed position, UV, triangle indices/areas and rigid
coverage. Ordered SHA-256 digests cover all packed vertex/triangle/rigid bytes
for the subsequent FF roundtrip comparison; opaque pointer values may differ.
There is no global expanded position/face list for v2.

The existing runtime gate binds the reviewed FF/evidence tuple to the matching
version, aggregate counts, individual ordered counts, slots and work bound.
Only the exact v1/v2 profile allowlist selects the existing bounded HTTP factory
and larger matching-cache path. Unknown or mixed profiles are refused. Runtime,
pixels, donor fidelity and native provenance remain unqualified by these tests.

## Source validation

`python -B -S tests/ops/model_lab_test.py -v` covers original cube regression,
synthetic irregular geometry, exact material-only and optional LOD derivations,
third-change refusal, packed normal/UV/index mutation refusal, actual names/NCS,
explicit FF/evidence admission, cache preservation and runtime claim limits.
Its FF stand-ins are labeled synthetic data and are never engine inputs.
Resource/process functions are mocked where exercised; no game is launched.

Historical v1 source checkpoint (2026-10-13): 19 Model Lab tests, 31 independent resident
readback tests and five existing shared HTTP regression tests passed. The agent
ownership suite passed 41 controls; the mocked capture-evidence suite and the
four changed PowerShell files' AST parse passed. GSC runtime compilation, native
FF build and donor rendering remain unexecuted and unqualified.

V2 source checkpoint (2026-10-13): 26 Model Lab tests and 40 independent reader
tests passed using original synthetic bytes, including 255 surfaces, exact work
cap/overflow before Reader allocation, repeated material and geometry aliases,
late-surface corruptions, truncations, explicit rebind refusal, proof/plan count
crossing, unknown-profile refusal and the actual HTTP dispatch expression.
The 16 common export-contract tests, five shared HTTP regression tests, 41
ownership controls, mocked capture-evidence suite and four PowerShell AST
parses also passed at this checkpoint.
Initial local test failures (reader return-shape unpacking and a test AST selector
that also selected the null initialization) were corrected before this checkpoint.
No native exporter/FF build, actual readback, game, stock payload read/hash or
resource admission was performed. Next: coordinator source review/integration;
native qualification and any real execution require their distinct approved step.

On 2026-10-14, the render-only streamed export/2 schema was added to the
existing large-manifest dispatch in `load_export`. Its export-manifest cap
remains the reader's 256 KiB; derived receipts and FF plans retain their
separate one-MiB cap. The legacy resident export/1 cap remains four KiB.
A synthetic regression first reproduced the erroneous four-KiB
refusal, then passed full staging and staged verification after the correction.
It retains the exact source manifest and mesh, explicit ordered recipient
bindings and only the declared LOD change. Oversized V2 and legacy V1 manifests
remain refused. This source-only correction does not alter the compiled E5
candidate or prove native FF/runtime behavior.
The 13 streamed-contract tests, 28 Model Lab tests in a fresh pinned source
composition and repository boundaries (715 tracked/697 exports/three
dependencies) passed. An initial Model Lab run from the uncomposed checkout
failed nine dependency-based checks because the Native/SDK files were absent;
the full composed run passed without relaxing those checks.

The community-candidate FF path now defers its full `Assert-BeaconCandidate`
EXE/tlog qualification until the existing Extract lease, before copying/loading
or starting the tool. Its candidate `DryRun` reads bounded producer metadata
and retains the original arena's exact e7 restriction. The existing non-arena
CDB digest check also runs under that lease, once, after candidate qualification.
The legacy ToolProvenance/reader path and World original-owner/stock restoration
remain unchanged. A source-only fixture runs the actual metadata and admission
blocks: candidate preview reads no opaque bytes; changed authored fake EXE bytes
are refused after admission; the valid candidate and diagnostic checks each run
once. This fixture launches no engine and reads no retail or qualified tool PE.

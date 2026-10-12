# Recipient observations: source-only runner

This narrow runner requests four non-default recipient references, followed by
one compiled `scripts/engine/utility` export. It does **not** complete a mod
package. Source preparation and synthetic tests were performed on 2026-10-12;
native execution, source-zone resolution and compiled retail bytes remain
unobserved by this runner. Coordinator adoption/admission is required before
`-Run`. Animation B has priority, then Material. No stock was staged or copied.

## Confirmed retained native API

The existing E7 fulltool is 21,696,512 bytes, SHA256
`e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04`.
Its retained source pin is `fab935826c898806855376662a8a03317b3ad8f1`.
`src/zonetool/zonetool/iw7/zonetool.cpp` hashes to
`f1c9fb861b81727dc7e3882f5116231e6dc0d1a0e6f5838953a62232171059bc`;
`src/zonetool/zonetool/shared/assets/scriptfile.hpp` hashes to
`5f6b30e5540563c41e8ce5d5d42d388f687e138ba7e5c2dbb30dc7eb720fc823`.
These files are not among the candidate's five patched translation units.
`Assert-BeaconCandidate` also verifies its existing build artifact, preparation,
closed build result, three patches and real 413-command compiler evidence.

The two real CLI invocations, in separate original-owned jobs, are:

```text
zonetool.exe -headless -unbuffered-io -strict-content-sources -enemy-reference-check cp_zmb recipient-material.csv sdk_beacon_recipient_a
zonetool.exe -headless -unbuffered-io -strict-content-sources -enemy-script-dump cp_zmb recipient-scripts.txt paris_enemy_cp_zmb_sdk_beacon_recipient_scripts
```

`-enemy-reference-check` immediately exits after writing its result. Concatenated
flags cannot execute both phases. The script request has **no `.gsc` suffix**.
The fixed requests are read from the existing SDK request files, validated
exactly, hash-bound, guarded and staged as hardlinks. No arbitrary asset list or
extra CLI flags can be supplied through the spec.

Reference output is `enemy-catalog/sdk_beacon_recipient_a.csv`: exact header
`type,name,status`, followed by the four ordered request rows, all `verified`.
Native code uses direct registered entries and `DB_IsXAssetDefault`, without
creating defaults. This proves effective resolution only. The CSV's hash is
provenance and **cannot substitute for a serialized asset content hash**.

Script output stays at its original path:
`dump/paris_enemy_cp_zmb_sdk_beacon_recipient_scripts/scripts/engine/utility.gscbin`.
The adjacent pack root `scriptfile-manifest.csv` must contain exactly one row
with the exact donor, pack, module, path, `dumped` status, size and SHA256. The
native exporter indexes `ScriptFile::name`, rejects ambiguous pointers with the
same requested name, compares the dump to loaded bytes and hashes the result.
The Python verifier independently checks name, lengths, exact size and streaming
SHA256. No second copy of a potentially large export is made.

The serialization contains the 22-byte ASCII name, NUL, three little-endian
signed int32 lengths (`compressedLen`, `len`, `bytecodeLen`), compressed buffer
and bytecode. Every length is 0..64 MiB. `len` is a scalar only; there is no
decompressed source buffer in the file. Maximum is **134,217,763 bytes**,
not three 64 MiB buffers. Tests use tiny invented bytes, never retail content.

## Shared providers and admission

`provider-pins.json` fixes 12 existing reviewed providers, including common
`StockBinding.Core.ps1` from commit `618c3ba`, Beacon validation/drains, original
`BuildJob.cs`, ModelFF restoration and AnimationFF registration. Supply an
explicit `ProviderRoot` containing those exact bytes. No provider is copied or
changed. A future provider update needs a reviewed pin change.

The spec is a local JSON object with these mandatory fields:

| Field | Meaning |
| --- | --- |
| `RunRoot` | Fresh absolute path inside this checkout's `runtime` |
| `StockRoot` | Canonical absolute retained stock root |
| `StockReceipt`, `StockReceiptSHA256` | Original 72-entry completed receipt, SHA `4cf67ebe1645c6c0761b9a24cb4e4630edee9c5d737742c704d624fe60cb3850` |
| `StockBindingReceipt`, `StockBindingReceiptSHA256` | Explicit current durable `iw7.ff-stock-observation/1` and measured hash |
| `ReviewedStockManifest`, `ReviewedStockManifestSHA256` | Reviewed content manifest, SHA `9116255ef148a324df15fa914795a7917615f023973111fdc39ae7329a9dcbf4` |
| `CandidateRoot`, `CandidateArtifactSHA256` | Existing E7 fulltool directory and final artifact hash |
| `PythonExe`, `PythonExeSHA256` | Absolute interpreter path and measured hash |
| `RequestRoot` | Absolute SDK directory holding the two existing request files |
| `MaterialRequestSHA256`, `ScriptRequestSHA256` | Exact measured request hashes |

No machine paths or invented observations are supplied as tracked defaults.
Invoke from a fresh PowerShell 7 host:

```powershell
& ./tools-source/asset-bridge/recipient/Run-RecipientClosure.ps1 -ProviderRoot $providerRoot -SpecPath $specPath
```

Without `-Run`, the runner hashes bounded evidence/providers, reads stock binding
metadata and returns a plan. It performs no Add-Type, stock inventory/content
hashing, reservation, directory creation or child launch. A missing/changed pin
fails; it does not refresh or rewrite historical evidence.

The common binding preserves historical 63-link/9-copy provenance separately
from this operation's 71 stock hardlinks and one 77-byte mutable sentinel copy.
Before staging, the admitted operation holds all source guards, checks observed
NTFS identities, hashes deduplicated physical stock content, then verifies
size/time/attributes. The candidate and two requests add three immutable links.
Only the separately identified sentinel may be made writable.

Both native modes call the same source-zone loader: existing shared shader core
zones, then available techsets/base/patch for code_post_gfx, global, common,
global_mp, global_cp, common_mp, common_cp and cp_zmb. The plan derives the exact
available order from the bound profile. Each phase must log that exact sequence
without errors. Bootstrap code_pre_gfx loads through the engine separately and
remains in the bound input inventory. No owner-zone attribution is invented.

One shared reservation covers 8 GiB RAM/11 GiB commit. The runner stops on
commit above 85%, a `stop.request`, 600 seconds overall, or 256 MiB generated
output. Each native phase allows 240 seconds and each original job 245 seconds.
SDK drains cap stdout and stderr at 2 MiB each. The filesystem threshold is
polled, so overshoot is possible; it is not a disk quota or measured memory peak.

Original job PID, image, creation time and BelowNormal priority are captured
**before Resume**. The reviewed scheduler's CIM registration follows Resume,
with a bounded five-second retry; it is not falsely recorded as pre-resume
attachment. Native children inherit the non-breakaway KILL_ON_JOB_CLOSE job.
The unused stdin pipe stays open to avoid the retained console's EOF spin.
Timeout/drain/receipt failures stop that original job, never a rediscovered PID.
Root exit **and zero job members** are required before restoration. Factory or
closure uncertainty preserves guards, inputs and reservation in quarantine.
After root exit a nonzero active count gets a bounded five-second drain, still
within the outer deadline. Every observed count, elapsed time and root exit code
is recorded; it is not treated as immediate failure or successful closure.

Only recorded staging paths are restored, preserving all exports/logs/cache.
Shared restoration verifies sources again before releasing the reservation.
The state records actual phase results separately from restoration. If the
adapter has resumed but no native PID receipt is available, `NativeExecuted`
is null, not an invented true/false result.

## Missing normal image and technique set

These are separate future observations and are deliberately absent from the
two-phase runner and its 256 MiB group. The retained APIs are:

* Normal image: `-dump_streamed_image -enemy-image-dump cp_zmb <one-name-list>
  paris_enemy_cp_zmb_sdk_recipient_normal_images`, with exactly
  `park_clown_zombie_shoes_n_3e46d100_packed_nog` in that list. No `-dds`.
  Existing early registration capture writes an `image-manifest.csv` and copies
  the selected source's header/pixel files. This requires a separately reviewed
  output budget because early capture plus selected-source copy can duplicate
  storage. Verify the header and every required external stream; a header alone
  is insufficient. Actual normal stream presence/count remains unobserved.
* Technique set: **console command**
  `dumpasset techset mopw_l_sm_replace_i0c0s0o0n0p0`, after source-zone loading.
  There is no `-dumpasset` CLI flag. Console `loadzone` commands can prepare the
  matching source order; CLI `-loadzone` exits and cannot be treated as the same
  console session. The dump goes under `dump/assets/techsets`, writes `.techset`,
  `.techset.txt`, referenced technique data and vertex declarations. Shader names
  are serialized, but shader-program dumping calls in `dump_technique` are
  commented out. Therefore this is not complete shader closure. Any later exact
  shader-name dump must also prove program bytes remain valid after loading;
  the early shader hook belongs to the broader `-enemy-extract` path and is not
  silently enabled here.

Utility imports require an actual compiled-file analysis. Effective references,
compiled content, transitive dependencies, complete images, runtime rendering
and owner acceptance remain distinct. Every successful observation still sets
`closure_complete=false`, `package_ready=false`; the outer state retains
`ClosureComplete=false`, `Ready=false`, `RuntimeVerified=false`.

## Source-only checks

```powershell
python -B -m unittest discover -s tools-source/asset-bridge/recipient -p test_recipient.py -v
pwsh -NoProfile -File tools-source/asset-bridge/recipient/Test-Recipient.ps1
```

11 Python fixture tests and 29 PowerShell source/contract checks passed. They
cover exact requests/verbs, CSV shape, missing/default/extra rows, paths, names,
hashes, lengths, bounds, source-zone order and default-plan/ownership ordering.
Simulated original owners cover delayed-empty success with retained counts,
five-second persistent-member failure, root-not-exited failure and late closure.
They do not prove native execution, resource peaks, restoration or package
closure. The next action is coordinator review/adoption and an explicit durable
stock binding, followed by admission when the prioritized work has completed.

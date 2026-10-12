# StandardMod current-source projection

The StandardMod preparer can create a new plan with reviewed current helpers
while keeping the completed F run as immutable evidence. It does not update or
consume an F/A/B plan, restore historical timestamps, read payload bytes, request
admission or authorize native execution. The 8 GiB physical / 11 GiB commit
profile and its existing output/deadline/cleanup limits remain unchanged.

## Why the old preparation refused

The sound-only telemetry correction restored shared `model/BuildJob.cs` to its
exact original bytes, but legitimately changed its modification time. Preparation
previously asserted F's complete old pin for every helper outside the sound
directory, while silently repinning any file inside that directory. The former
refused the restored helper; the latter was too broad for an explicit source
transition. The refusal and correction history remain in `SOUND-JOB-MEMORY.md`.

## Closed source set and retained evidence

`Get-SoundFFCurrentSourceRelatives` names exactly 26 versioned files: the 16 shared
helpers already checked by `sab_ff_helpers.json`, and ten sound-local sources:
`Build-SoundFF.ps1`, `Prepare-SoundFF.ps1`, `prepare_sab_ff.py`, `read_flac.py`,
`read_sab.py`, `sab_contract.json`, `sab_ff_helpers.json`, `sound_ff_phase.py`,
`SoundFF.Core.ps1` and `SoundBuildJob.cs`. No directory-prefix or file-extension
rule can grant projection eligibility. Each current source is bounded to 128 KiB
and must belong to the shared repository named by F; repository relocation is
not part of this change.

The new plan includes `SourceProjection`, schema
`iw7.sound-current-source-projection/1`, bound to the exact immutable F plan hash.
Each row records its closed-list relative path, complete historical pin and
independently observed current pin. `SoundBuildJob.cs` is the only new member and
has a null historical pin. The other 25 historical pins come directly from F.
Current pins also appear in `HashInputs`, so existing transaction guards protect
the precise files selected by the new plan. The execution-plan validator checks
membership, provenance, matching current pins and current source bytes/metadata.
The shared helper manifest's canonical source checks still apply independently.

| Evidence class | Treatment in the new plan |
| --- | --- |
| WAV, FLAC and Python payload pins | Reused exactly, including metadata; still deferred until admitted execution. Preparation does not read/hash their bytes. |
| Stock inputs | The complete F array is retained; the 71-link/77-byte-copy profile is unchanged. No stock staging or live stock hash occurs. |
| Original alias CSV, bank JSON and zone CSV | Complete F pins retained and checked; they are outside the projection list. |
| Historical review/stock JSON and codec checkpoint | Complete F pins retained and checked; no silent metadata refresh. |
| F execution plan and result | Exact fixed evidence hashes and existing lifecycle/readback gates remain required. |
| Candidate receipts | Only the two exact old candidate receipt paths are replaced by already qualified candidate C receipts. Its binary identity is read from those receipts, not rehashed or rebuilt. |
| StandardMod overlay | The existing two source overlays remain separately pinned and checked against their allowed differences from original F sources. |

Unexpected, missing or duplicate projection rows and pins are refused. A row
cannot redirect a helper to a payload, invent historical membership, change an
old pin or silently change a current pin. Every unprojected historical text pin
must remain complete and exact. The payload and stock equality gates are
unchanged. DumpOnly and legacy Build do not receive this new projection route.

## Validation and use

`test_sound_source_projection.ps1` prepares and default-validates a temporary new
plan from the real retained JSON evidence, then exercises 18 mutation refusals.
It blocks and counts any attempted payload hash, checks that no native type or
RunRoot was created, and rechecks the historical plan/result files and metadata.
`test_sound_standard_mod.ps1` retains its existing source/overlay, plan-mutation
and mock-admission-refusal checks. Neither suite starts an admitted workload.

A preparation result is a source review artifact: `Ready=false` and
`HeavyExecutionAuthorizedByPlan=false`. After the source changes are merged,
create and review a fresh plan from the final source set. The closed B attempt
and its refused capacity snapshot do not authorize C. Fresh admission, exact
source/payload guards, original-job closure, restoration and measured memory
evidence still belong to a separately authorized future execution.

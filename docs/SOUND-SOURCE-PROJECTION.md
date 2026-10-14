# StandardMod current-source projection

## Future source contracts - 2026-10-14

Current sound preparation uses `sab_ff_helpers-20261014.json` in Python,
PowerShell and the native build-plan adapter. Both older manifests remain exact.
Relative to the 2026-10-13 manifest, only Scheduler and ModelFF change: Scheduler
now implements `TelemetryOnly`, and ModelFF gained the reviewed authored-arena
and streamed geometry dispatch. The remaining 14 helper source pins are unchanged.
LF/CRLF normalization still qualifies source only; execution guards still bind
exact file bytes, size and metadata.

RAM and commit values are positive typed int64 scenario estimates, without the
former exact 8/11 GiB or 4/6 GiB admission requirement. New review/execution plans
preserve their reviewed estimates and pass them to the one existing shared lease.
The three sound phase/build/sealing observers validate fresh telemetry with the
shared policy instead of stopping at 85 percent commit. Invalid telemetry,
ownership conflicts, original jobs, deadlines, quarantine, restoration and exact
output/log limits retain their existing gates. A source plan grants no native GO.

The future StandardMod projection has 27 members. Its new dated manifest and
`SoundBuildJob.cs` have null historical pins; the 25 existing historical members
retain their complete F pins. The new manifest receives a current runtime pin.
Frozen F/A/B plans, receipts, outputs and earlier source packages are not rewritten.

Source validation: the fresh Sound package passed all 110 Python tests with no
skips; native-checksum passed 23 Python tests. Mocked phase/deadline tests accept
full commit and reject impossible telemetry in all three observers. Eight sealing
cases passed 35 assertions, and 14 tiny-file transaction cases passed with reviewed
1-byte physical / 512-MiB commit estimates transmitted to admission. These tests
do not compile native code, seal retail/toolchain inputs, build SAB/FF, launch a
game or establish playback. A future real plan still needs separate qualification.

The sections below retain the 2026-10-13 projection qualification and its original
26-member source set and scenario estimates.

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

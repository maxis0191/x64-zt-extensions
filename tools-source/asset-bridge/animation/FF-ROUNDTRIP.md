# Next animation gate: original XAB through the existing full ZoneTool

**Prepared source only; no FF phase has run for this animation.** The input is
the actual 281-byte `paris_original_probe_bend.xab` from the native witness,
SHA256 `1284b72cf501ae42f77958579610dbcaf692b9153cd06ff66dcf2d1d11eeda7d`.
Do not rebuild the writer or substitute synthetic test bytes. Recheck that input
and its existing native receipt before any staging.

## Smallest concrete pack

Stage only the original XAB and [one-line zone CSV](fixtures/sdk_animation_probe.csv):

```
xanim/paris_original_probe_bend.xab
zone_source/sdk_animation_probe.csv
```

CSV content is `xanim,paris_original_probe_bend`. The pinned IW7 writer has an
empty `xanim_parts::load_depending`; `zonetool.cpp` adds the zone's branding
rawfile. Expected custom-zone inventory is therefore exactly:

```
xanim,paris_original_probe_bend
rawfile,sdk_animation_probe
```

Reject missing, duplicate, extra, defaulted or unresolved rows, and require the
build log's `Parsing xanim "paris_original_probe_bend"...` marker to establish
that the original file was consumed. No model, material, netconststrings, GSC,
animtree, CP map preload or reference comma belongs in this first pack.

Under the next coordinator GO, run these **sequential phases inside one guarded
transaction**, from its fresh work directory (not as unguarded shell commands):

```text
zonetool.exe -headless -unbuffered-io -strict-content-sources -buildzone sdk_animation_probe
zonetool.exe -headless -unbuffered-io -strict-content-sources -verifyzone sdk_animation_probe
zonetool.exe -headless -unbuffered-io -strict-content-sources -dumpzone sdk_animation_probe
python -B <animation>/read_probe.py <retained-redump.xab> --expected-frequency 1 --ff-roundtrip
```

Retain `zone/sdk_animation_probe.ff` (nonempty, at most 1 MiB), verify inventory,
then read only `dump/sdk_animation_probe/xanim/paris_original_probe_bend.xab`
(at most 64 KiB). Bind FF, dump and reader hashes to real phase exits/receipts.
The input XAB stays byte-identical. The output may have different pointer bytes
and script-string IDs; equality of whole-file hashes is not a semantic gate.

`xanim.cpp:187-209` interns bone/note names into the zone script-string table.
The reader's explicit `--ff-roundtrip` mode therefore accepts only the note ID's
change to another nonzero uint32. It still requires exact `probe_contact` text,
time 0.5, all four key indices/quaternions, header profile and EOF. Default native
writer mode continues to require note ID 3. Three new light tests cover remapping,
null/name/time refusal and CLI opt-in; all 42 Python tests pass. The reader alone
still cannot prove an FF build or any rendered playback.

## Existing dependencies, kept in place

The original ignored `runtime/animation-ff-plan.local.json` retains the
preparation snapshot. The subsequent source-only adapter has its own
`runtime/animation-ff-executable-plan.local.json` and
`runtime/animation-ff-arguments.local.json`; it does not change previous evidence.

| Dependency | Exact reused contract |
| --- | --- |
| Full ZoneTool | H1 owner's `runtime/zt-full-a/bin/zonetool-community.exe`, 21696512 bytes; SHA256 `e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04` |
| Candidate receipt | `build-artifact.local.json`, SHA256 `f0d4d7db132d51c789a999e33ab0ce905b2df749db453029f91356b9aa2e2165`; pin `fab935826c898806855376662a8a03317b3ad8f1`, 413 units, EXPERIMENTAL_IW7, three reviewed patches |
| Existing FF recipe | Coordinator's `sdk/modding/Build-BeaconFF.ps1`, `BeaconFF.Core.ps1`, `beacon_tool_phase.py`; observed hashes retained in the local plan |
| Existing owned process implementation | H1 `tools-source/asset-bridge/model/BuildJob.cs`, SHA256 `f6be2a4cafddb78b5e07a6802354575ada418cb7643d96a3abd0a4c063bc6387`, already used by the real Beacon FF transaction |
| Stock manifest | Completed/restored `model-lod1m-ff-build-20261007/state.local.json`, SHA256 `4cf67ebe1645c6c0761b9a24cb4e4630edee9c5d737742c704d624fe60cb3850`; exact 72 entries, 839210257 logical bytes |
| Stock/restore helpers | Existing `ops/Base-Client.Core.ps1`, `ops/model-lab/ModelFF.Core.ps1`, `ops/hud-lab/HudFileIdentity.cs`, current resource scheduler |

The original plan used `doom-negative-textures/runtime/dt`. Those paths later
became absent; the coordinator inventories and retains a durable alternative via
the separate observation contract above, without rewriting the old receipt.
Reuse the validated 72 immutable/bootstrap inputs by temporary NTFS hardlinks and original
read guards, copying only the existing 77-byte mutable filesystem sentinel.
Link the existing executable and two animation inputs: 75 staged input entries
in total. Do not copy the EXE, PDB, source tool tree, PAKs or full stock. Record
source/target NTFS identities and metadata, use the existing transaction backup,
then verify exact restoration before lease release. No source attributes change.

`Build-BeaconFF.ps1` cannot run unchanged: it pins the Beacon receipt, five source
paths, five-asset inventory, zone name and B77B geometry reader. The smallest
execution adaptation changes only those profile-specific points to the
two inputs/two inventory rows, animation zone and this Python reader. Reuse the
existing candidate proof, owned-job, bounded pipe adapter, stock transaction,
source guards and restoration logic. Keep that specialization inside animation
ownership or have the coordinator apply it; do not edit another author's live
SDK files or build a generic exporter/framework. Re-pin any changed shared helper
before GO instead of silently using its old hash.

If those historical paths disappear, use the separate
[alternate-stock binding contract](STOCK-BINDING.md). Keep the old receipt
unchanged and supply the new binding path/hash; another stock root cannot be
accepted by just replacing path strings in the old transaction.

## Executable specialization, not yet run

[Build-AnimationFF.ps1](Build-AnimationFF.ps1) defaults to a read-only plan.
It imports only parsed function definitions from the three pure shared cores;
no `Add-Type`, reservation, staging or child launch occurs in plan mode. An actual
local plan bound the original 281-byte XAB, completed stock receipt, all 72 stock
entries, and final full candidate successfully. Its proposed run directory did
not exist afterward; the BuildJob and NTFS helper types stayed unloaded.

`-Run` additionally requires all nine provider/transitive hashes, the final
candidate artifact hash, the reviewed existing BuildJob source hash and Python
hash, in a fresh PowerShell host. The resource scheduler alone loads its memory
query during admission; the job and NTFS helpers compile only after the complete
8/11 GiB reservation. Sources stay guarded against write/delete until owned-tree
closure. The exact suspended root is recorded and registered before Resume.
Failed native factory return, unknown job closure or refused restoration retains
the reservation. Unknown closure also retains guards and any returned owner in
an AppDomain quarantine record; it never triggers stock restoration.

[animation_tool_phase.py](animation_tool_phase.py) imports the hash-bound existing
`beacon_tool_phase.py` and replaces only its command factory for this fixed zone
and exact reader flags. Pipe caps, phase timeout, process launch and phase receipt
remain the shared implementation. No other author's files were changed.
The PowerShell wrapper reuses `Assert-BeaconCandidate`, job identity/output budget
helpers, Base transaction save/restore and `Complete-ModelFFRestore`. Its own
checks are the original receipt/CSV, exact two-row inventory and FF reader result.

Light verification for this source tranche: 49 Python tests and 46 PowerShell
checks passed. Refusals cover changed/missing pins, wrong source/receipt shape,
stock duplicates/escape/size, inventory extras/unresolved rows, unsupported command
arguments, and wrong reader scope. Simulated restoration tests prove the shared
restore coordinator runs source-final proof before release and retains the lease
on either restoration or source-final failure; an unclosed tree does neither.
These are pure tests, not a native FF result. Independent review and a separate
coordinator GO remain pending.

Example using the local reviewed argument file (its hashes must be refreshed and
reviewed whenever an imported provider changes):

```powershell
$parameters=Get-Content runtime/animation-ff-arguments.local.json -Raw | ConvertFrom-Json -AsHashtable
& ./tools-source/asset-bridge/animation/Build-AnimationFF.ps1 @parameters
# Only after independent review and the separate coordinator GO:
# & ./tools-source/asset-bridge/animation/Build-AnimationFF.ps1 @parameters -Run
```

## Complete proposed admission and bounds

Use the proven Beacon **8 GiB physical / 11 GiB commit** reservation for all four
phases together; this is larger than the standalone writer's 4/6 GiB budget.
One BelowNormal native phase at a time, no compiler or game overlap. Native phase
timeout 240 seconds (outer allowance 245), reader 30 seconds (outer allowance 35),
overall phase allowance 770 seconds plus bounded cleanup. Plan at most 15 minutes
for the complete attempt; do not lower memory estimates to bypass admission.

Each stdout/stderr stream is capped at 2 MiB, at most 16 MiB across four phases.
Keep the existing 64 MiB generated-output stop threshold, including TOC caches,
all logs/receipts, retained FF and redump. Exclude only verified stock/source
hardlinks from physical-growth accounting; metadata restoration is still required.
Expected output is small (Beacon's measured run retained about 1.2 MiB), but that
is not this animation's measured size. Stop on timeout, coordinator stop file,
85% commit pressure, cap violation or failed phase. Retain failed evidence; an
unconfirmed owned tree or restoration keeps its lease and staging quarantined.

## First real animated example after this gate

Reuse the existing original two-bone skin fixture with exact `tag_origin` /
`tag_probe` names and parent distance 1, under its model owner's responsibility.
The currently tested Beacon is one-bone geometry and cannot demonstrate this
clip's bending. Require that two-bone model's native/FF/bind/weight gates before
combining it with the passed XAnim.

Then one static-origin actor on the existing private test dedicated, base client
free, full-quality observation, fresh engine godmode and inactivity protection:
preload/link the minimal retail-compatible animtree, play this clip on that rig,
and observe 0/+45/-45/0 poses about the same pivot with a static control. Measure
the candidate one-second loop and `probe_contact` once per cycle at half-cycle.
No AI/attack/damage/root-motion integration yet. Animtree API/preload/linkage must
be bound to the engine owner's actual fixture, not guessed from the FF success.
That gameplay allocation is separate: propose 12 GiB client + 4 GiB dedicated
physical and commit, re-admitted only after source/FF work is closed. No gameplay
script, game launch or rendered-animation acceptance is claimed by this plan.

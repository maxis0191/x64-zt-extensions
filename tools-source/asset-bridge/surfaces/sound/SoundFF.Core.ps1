# Sound-local binding of existing admission, original job, and file transactions.
# Importing this file loads no native type and starts nothing.
function Assert-SoundFFPath([string]$Path) {
    if(!$Path -or ![IO.Path]::IsPathFullyQualified($Path)){throw 'Absolute sound path required.'}
    for($p=[IO.Path]::GetFullPath($Path);$p;$p=Split-Path $p -Parent){
        if((Test-Path -LiteralPath $p) -and ((Get-Item -LiteralPath $p -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Redirected sound path refused.'}
    }
}
function Get-SoundFFPin([string]$Path) {
    Assert-SoundFFPath $Path;$f=Get-Item -LiteralPath $Path
    if($f.PSIsContainer){throw 'Regular source file required.'}
    [pscustomobject]@{Path=$f.FullName;Bytes=$f.Length;SHA256=(Get-FileHash -LiteralPath $f.FullName).Hash;Attributes=[int]$f.Attributes;ModifiedUtc=$f.LastWriteTimeUtc.ToString('o')}
}
function Assert-SoundFFPin($Pin) {
    Assert-SoundFFPath $Pin.Path;$f=Get-Item -LiteralPath $Pin.Path
    if($Pin.SHA256 -cnotmatch '^[a-fA-F0-9]{64}$' -or $f.PSIsContainer -or (Get-FileHash -LiteralPath $Pin.Path).Hash -ine $Pin.SHA256){throw ('Sound input hash differs: '+$Pin.Path)}
    if($Pin.PSObject.Properties['Bytes'] -and $f.Length -ne $Pin.Bytes){throw 'Sound input size differs.'}
    if($Pin.PSObject.Properties['Attributes'] -and ([int]$f.Attributes -ne $Pin.Attributes -or $f.LastWriteTimeUtc.Ticks -ne ([datetimeoffset]$Pin.ModifiedUtc).UtcDateTime.Ticks)){throw 'Sound input metadata differs.'}
}
function Assert-SoundFFHelperSources([string]$SoundRoot,[string]$Repo,$HashInputs) {
    $helpers=Get-Content -LiteralPath (Join-Path $SoundRoot 'sab_ff_helpers.json') -Raw|ConvertFrom-Json
    if($helpers.schema -cne 'iw7.original-sound-helper-sources/1' -or $helpers.normalization -cne 'utf8-crlf-to-lf-only/1' -or
        @($helpers.files.PSObject.Properties).Count -ne 16){throw 'Explicit helper source identity required.'}
    foreach($entry in $helpers.files.PSObject.Properties){
        $path=Join-Path $Repo $entry.Name;Assert-SoundFFPath $path
        $raw=[IO.File]::ReadAllBytes($path)
        $utf8=[Text.UTF8Encoding]::new($false,$true)
        $canonical=$utf8.GetBytes($utf8.GetString($raw).Replace("`r`n","`n"))
        if([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($canonical)) -ine $entry.Value){throw ('Shared helper source changed: '+$entry.Name)}
        $pin=@($HashInputs|Where-Object Path -IEQ $path)
        if($pin.Count -ne 1){throw 'Exact helper runtime pin required.'}
        Assert-SoundFFPin $pin[0]
    }
}
function Assert-SoundFFCandidateEvidence($Receipt,$State) {
    if($Receipt.schema -cne 'iw7.sound-checksum-build-receipt/1' -or $Receipt.status -cne 'NativeBuildAndCppProbesPassed' -or
        $State.Schema -cne 'iw7.sound-checksum-supervisor/1'){throw 'Actual sound Build F receipts required.'}
    foreach($name in 'Success','InputsVerifiedBefore','InputsVerifiedAfter','FinalArtifactsVerified','TreeClosed','LeaseReleased'){
        if($State.$name -isnot [bool] -or !$State.$name){throw 'Completed closed Build F required.'}
    }
    if($null -ne $State.Failure -or $null -ne $State.RetainedLeaseToken -or
        ($State.RootExitCode -isnot [int] -and $State.RootExitCode -isnot [long]) -or $State.RootExitCode -ne 0 -or
        ($State.JobActiveAtClose -isnot [int] -and $State.JobActiveAtClose -isnot [long]) -or $State.JobActiveAtClose -ne 0 -or
        $State.PlanSHA256 -cne '91280092489387e909516693d4234c60ea0416657166cf6bd8674bd974729c3a' -or
        $Receipt.plan_sha256 -cne $State.PlanSHA256 -or !$State.RunID -or $Receipt.run_id -cne $State.RunID){throw 'Released successful Build F generation required.'}
    foreach($pair in @(@($Receipt,'native_cpp_probes_verified',$true),@($Receipt,'sab_ff_tested',$false),@($Receipt,'ready',$false),
        @($State,'Ready',$false),@($State,'SABFFVerified',$false))){
        if($pair[0].($pair[1]) -isnot [bool] -or $pair[0].($pair[1]) -ne $pair[2]){throw 'Build provenance cannot grant sound playback.'}
    }
    $artifact=$Receipt.artifacts.candidate_exe;$verified=$State.Artifacts.candidate_exe
    if($artifact.relative -cne 'bin/zonetool-sound-md5.exe' -or $artifact.sha256 -cne '4740f0c22a1a7bab0b01f7a55ec0b133263ac218825ac3c0d15b9e269fe472b0' -or
        ($artifact.bytes -isnot [int] -and $artifact.bytes -isnot [long]) -or $artifact.bytes -ne 21696512 -or
        $verified.relative -cne $artifact.relative -or $verified.sha256 -cne $artifact.sha256 -or $verified.bytes -ne $artifact.bytes){throw 'Verified checksum candidate artifact differs.'}
    $artifact
}
function Assert-SoundFFChecksumCandidate([string]$Root,[string]$ReceiptSHA256,[string]$StateSHA256,$Guards=$null) {
    if($ReceiptSHA256 -ine 'a8253c8efa5b315c7870f27c6732eb6893528c0bd4c8ad3ddcbe7dde407faf62' -or
        $StateSHA256 -ine '5a99ed368636d08d1d4407e3125cab73f5da879344880588c6aa54efcb556ed8'){throw 'Exact completed Build F hashes required.'}
    $receiptPath=Join-Path $Root 'build-receipt.json';$statePath=Join-Path $Root 'supervisor-state.json'
    foreach($pair in @(@($receiptPath,$ReceiptSHA256,512KB),@($statePath,$StateSHA256,16KB))){
        if((Get-Item -LiteralPath $pair[0]).Length -gt $pair[2]){throw 'Bounded Build F metadata required.'}
        Assert-SoundFFPin ([pscustomobject]@{Path=$pair[0];SHA256=$pair[1]})
    }
    $artifact=Assert-SoundFFCandidateEvidence (Get-Content -LiteralPath $receiptPath -Raw|ConvertFrom-Json) (Get-Content -LiteralPath $statePath -Raw|ConvertFrom-Json)
    $exe=Join-Path $Root $artifact.relative;Assert-SoundFFPath $exe
    if((Get-Item -LiteralPath $exe).Length -ne $artifact.bytes){throw 'Existing checksum candidate unavailable.'}
    # Metadata-only in preparation/default Plan. Under admitted execution, take
    # the same transaction guard before the first binary hash and staging.
    if($null -ne $Guards){
        $Guards.Add([IO.File]::Open($exe,'Open','Read','Read'))
        Assert-SoundFFPin ([pscustomobject]@{Path=$exe;Bytes=$artifact.bytes;SHA256=$artifact.sha256})
    }
    [pscustomobject]@{Path=$exe;Bytes=$artifact.bytes;SHA256=$artifact.sha256}
}
function Assert-SoundFFFlacEvidence($Receipt,$State) {
    if($Receipt.schema -cne 'iw7.sound-flac-dump-build-receipt/1' -or $Receipt.status -cne 'NativeBuildAndCppProbesPassed' -or
        $State.Schema -cne 'iw7.sound-checksum-supervisor/1' -or
        $State.PlanSHA256 -cne '19d8a83dc326b47dbe48e541152c10907849798d12a5adcef63c794e02a0232f' -or
        $Receipt.plan_sha256 -cne $State.PlanSHA256 -or !$State.RunID -or $Receipt.run_id -cne $State.RunID){throw 'Actual qualified FLAC Build C required.'}
    foreach($name in 'Success','InputsVerifiedBefore','InputsVerifiedAfter','FinalArtifactsVerified','TreeClosed','LeaseReleased'){
        if($State.$name -isnot [bool] -or !$State.$name){throw 'Incomplete FLAC Build C.'}
    }
    foreach($name in 'AcceptanceGranted','ClosureVerified','CompletionVerified'){
        if($State.QualifiedClosure.$name -isnot [bool] -or !$State.QualifiedClosure.$name){throw 'Unqualified original build closure.'}
    }
    foreach($pair in @(@($State,'DeferredArtifactProofPending'),@($State,'Ready'),@($State,'SABFFVerified'),
        @($Receipt,'sab_ff_tested'),@($Receipt,'ready'))){
        if($pair[0].($pair[1]) -isnot [bool] -or $pair[0].($pair[1])){throw 'Deferred proof or sound promotion refused.'}
    }
    foreach($name in 'native_cpp_probes_verified','flac_header_probe_verified'){
        if($Receipt.$name -isnot [bool] -or !$Receipt.$name){throw 'Native C++ probes required.'}
    }
    foreach($pair in @(@('InputGuardsOpened',1418),@('InputGuardsDisposed',1418),@('RootExitCode',0),@('JobActiveAtClose',0))){
        if(($State.($pair[0]) -isnot [int] -and $State.($pair[0]) -isnot [long]) -or $State.($pair[0]) -ne $pair[1]){throw 'Build guard/exit accounting differs.'}
    }
    if($null -ne $State.Failure -or $null -ne $State.RetainedLeaseToken -or $State.Quarantined -or
        $State.QualifiedClosure.Error -or @($Receipt.steps).Count -ne 17 -or @($Receipt.includes.PSObject.Properties).Count -ne 9){throw 'Complete released Build C evidence required.'}
    foreach($step in $Receipt.steps){
        if(($step.exit_code -isnot [int] -and $step.exit_code -isnot [long]) -or $step.exit_code -ne 0 -or
            $step.normal_eof -isnot [bool] -or !$step.normal_eof){throw 'Every native step must close normally.'}
    }
    $probe=$Receipt.probes.'probe-flac-run'
    if($probe.schema -cne 'iw7.flac-dump-header-probe/1' -or $probe.cases -ne 103 -or
        $probe.input_unchanged -isnot [bool] -or !$probe.input_unchanged -or $probe.extent_checks -isnot [bool] -or !$probe.extent_checks -or
        $probe.native_dump_tested -isnot [bool] -or $probe.native_dump_tested -or $probe.full_conformance -isnot [bool] -or $probe.full_conformance -or
        $probe.ready -isnot [bool] -or $probe.ready){throw 'Exact non-promoting 103-case probe required.'}
    $roles=@('candidate_exe','candidate_pdb','common_library','probe_original','probe_patched','probe_flac')
    foreach($object in @($Receipt.artifacts,$State.Artifacts)){
        if(($object.PSObject.Properties.Name|Sort-Object|ConvertTo-Json -Compress) -cne ($roles|Sort-Object|ConvertTo-Json -Compress)){throw 'Six verified artifacts required.'}
    }
    foreach($role in $roles){
        $a=$Receipt.artifacts.$role;$b=$State.Artifacts.$role
        if($a.sha256 -cnotmatch '^[a-f0-9]{64}$' -or ($a.bytes -isnot [int] -and $a.bytes -isnot [long]) -or $a.bytes -le 0 -or
            $a.sha256 -cne $b.sha256 -or $a.relative -cne $b.relative -or $a.bytes -ne $b.bytes){throw 'Final artifact proof differs.'}
    }
    $a=$Receipt.artifacts.candidate_exe
    if($a.relative -cne 'bin/zonetool-sound-md5.exe' -or $a.bytes -ne 21705728 -or
        $a.sha256 -cne 'cef411cf9b4de69be02cb4017aabd964e9143e340e211188daa6b6bab366493a'){throw 'Observed C candidate differs.'}
    $a
}
function Read-SoundFFPinnedMetadata([string]$Path,[string]$Hash,[long]$Maximum) {
    Assert-SoundFFPath $Path
    if([IO.Path]::GetExtension($Path) -cne '.json' -or (Get-Item -LiteralPath $Path).Length -gt $Maximum){throw 'Bounded JSON evidence required.'}
    Assert-SoundFFPin ([pscustomobject]@{Path=$Path;SHA256=$Hash})
    Get-Content -LiteralPath $Path -Raw|ConvertFrom-Json
}
function Assert-SoundFFFlacCandidate([string]$Root,[string]$ReceiptSHA256,[string]$StateSHA256,$Guards=$null) {
    if($ReceiptSHA256 -ine 'dfe3d7d1ed0d9b3c4ad334fc64d1f3f277508c468df034f05cffd2505f3944f4' -or
        $StateSHA256 -ine '99c5c35fe43ad90bb192db8902dc718402fb901dd2cc6f6689d790e82a5ba149'){throw 'Exact qualified C metadata pins required.'}
    $r=Read-SoundFFPinnedMetadata (Join-Path $Root 'build-receipt.json') $ReceiptSHA256 512KB
    $s=Read-SoundFFPinnedMetadata (Join-Path $Root 'supervisor-state.json') $StateSHA256 16KB
    $a=Assert-SoundFFFlacEvidence $r $s
    $pin=[pscustomobject]@{Path=(Join-Path $Root $a.relative);Bytes=$a.bytes;SHA256=$a.sha256}
    Assert-SoundFFPath $pin.Path
    if($null -ne $Guards){$Guards.Add([IO.File]::Open($pin.Path,'Open','Read','Read'));Assert-SoundFFPin $pin}
    $pin
}
function Get-SoundFFRuntimePins($Plan,$Lease) {
    @($Plan.HashInputs)
    # A failure before admission must not turn cleanup into a payload reader.
    if($Plan.Profile -cin @('DumpOnly','StandardMod') -and $Lease){@($Plan.PayloadInputs)}
}
function Read-SoundFFImmutableF($Evidence) {
    if($Evidence.PlanSHA256 -ine '3d90a5746a8ee698fb08715e270f2855f261b318393257f91a9e7f59e3ad39d5' -or
        $Evidence.StateSHA256 -ine 'd0a57123f7940eee29ef42da7440dd353e63eeffbfc025d37b162f4feda9e1a9'){throw 'Exact preserved F evidence required.'}
    $plan=Read-SoundFFPinnedMetadata $Evidence.PlanPath $Evidence.PlanSHA256 256KB
    $state=Read-SoundFFPinnedMetadata $Evidence.StatePath $Evidence.StateSHA256 128KB
    foreach($name in 'Restored','StockPreserved','JobClosureVerified','JobDisposeCompleted','SourceHashesUnchanged','ReadGuardsReleased'){
        if($state.$name -isnot [bool] -or !$state.$name){throw 'Preserved F lifecycle incomplete.'}
    }
    if($state.Status -cne 'SoundSABAndFFBytesVerified' -or $state.Quarantined -or $state.RetainedLeaseToken -or $state.Failure -or $state.CleanupError -or
        $state.Work -ine $plan.Work -or $state.Ready -or $state.PlaybackVerified -or @($state.Artifacts).Count -ne 3){throw 'Preserved F result differs.'}
    [pscustomobject]@{Plan=$plan;State=$state}
}
function Get-SoundFFCurrentSourceRelatives {
    # Closed, reviewed source set. Never infer eligibility from a directory or
    # extension: historical receipts, stock and original media are not helpers.
    @('ops/Base-Client.Core.ps1','ops/hud-lab/HudFileIdentity.cs','ops/model-lab/ModelFF.Core.ps1',
        'ops/native/ResourceMemory.cs','ops/Resource-Memory.ps1','ops/Resource-RecorderOwnedProcess.Core.ps1',
        'ops/Resource-Scheduler.Core.ps1','sdk/modding/beacon_tool_phase.py','sdk/modding/BeaconFF.Core.ps1',
        'tools-source/asset-bridge/common/StockBinding.Core.ps1','tools-source/asset-bridge/model/BuildJob.cs',
        'tools-source/asset-bridge/surfaces/inspect_content.py','tools-source/asset-bridge/surfaces/material_v2_phase.py',
        'tools-source/asset-bridge/surfaces/MaterialV2.Core.ps1','tools-source/asset-bridge/surfaces/prepare_beacon.py',
        'tools-source/asset-bridge/surfaces/prepare_material_v2.py')
    foreach($name in 'Build-SoundFF.ps1','Prepare-SoundFF.ps1','prepare_sab_ff.py','read_flac.py','read_sab.py',
        'sab_contract.json','sab_ff_helpers.json','sound_ff_phase.py','SoundFF.Core.ps1','SoundBuildJob.cs'){
        'tools-source/asset-bridge/surfaces/sound/'+$name
    }
}
function New-SoundFFSourceProjection($HistoricalPlan,[string]$PlanSHA256) {
    $expectedRoot=Join-Path $HistoricalPlan.SharedRepo 'tools-source/asset-bridge/surfaces/sound'
    if($expectedRoot -ine $PSScriptRoot){throw 'Current sound sources must belong to the preserved shared repository.'}
    $entries=@(foreach($relative in Get-SoundFFCurrentSourceRelatives){
        $path=Join-Path $HistoricalPlan.SharedRepo $relative;Assert-SoundFFPath $path
        if((Get-Item -LiteralPath $path).Length -gt 128KB){throw 'Bounded current helper source required.'}
        $old=@($HistoricalPlan.HashInputs|Where-Object Path -IEQ $path)
        $new=$relative -ceq 'tools-source/asset-bridge/surfaces/sound/SoundBuildJob.cs'
        if($old.Count -ne $(if($new){0}else{1})){throw 'Exact F helper membership required.'}
        [pscustomobject]@{Relative=$relative;HistoricalPin=$(if($new){$null}else{$old[0]});CurrentPin=(Get-SoundFFPin $path)}
    })
    [pscustomobject]@{Schema='iw7.sound-current-source-projection/1';BasisPlanSHA256=$PlanSHA256;Entries=$entries}
}
function Assert-SoundFFSourceProjection($Plan,$HistoricalPlan) {
    $projection=$Plan.SourceProjection;$relatives=@(Get-SoundFFCurrentSourceRelatives)
    if(!$projection -or $projection.Schema -cne 'iw7.sound-current-source-projection/1' -or
        $projection.BasisPlanSHA256 -cne $Plan.ImmutableFF.PlanSHA256 -or @($projection.Entries).Count -ne $relatives.Count){
        throw 'Explicit current-source projection from preserved F required.'
    }
    $currentPaths=@(foreach($relative in $relatives){
        $path=Join-Path $HistoricalPlan.SharedRepo $relative
        $rows=@($projection.Entries|Where-Object Relative -CEQ $relative)
        $old=@($HistoricalPlan.HashInputs|Where-Object Path -IEQ $path)
        $new=$relative -ceq 'tools-source/asset-bridge/surfaces/sound/SoundBuildJob.cs'
        if($rows.Count -ne 1 -or $old.Count -ne $(if($new){0}else{1})){throw 'Closed current-source membership differs.'}
        $historical=if($new){$null}else{$old[0]}
        $row=$rows[0];$bound=@($Plan.HashInputs|Where-Object Path -IEQ $path)
        if(($row.HistoricalPin|ConvertTo-Json -Depth 8 -Compress) -cne ($historical|ConvertTo-Json -Depth 8 -Compress) -or
            $row.CurrentPin.Path -ine $path -or $bound.Count -ne 1 -or
            ($row.CurrentPin|ConvertTo-Json -Depth 8 -Compress) -cne ($bound[0]|ConvertTo-Json -Depth 8 -Compress)){
            throw 'Projected helper provenance or current pin differs.'
        }
        Assert-SoundFFPath $path
        if((Get-Item -LiteralPath $path).Length -gt 128KB){throw 'Bounded current helper source required.'}
        Assert-SoundFFPin $row.CurrentPin
        $path
    })
    $oldCandidate=@('build-receipt.json','supervisor-state.json'|ForEach-Object {Join-Path $HistoricalPlan.CandidateRoot $_})
    foreach($old in $HistoricalPlan.HashInputs){
        if($old.Path -iin $currentPaths -or $old.Path -iin $Plan.PayloadInputs.Path -or $old.Path -iin $oldCandidate){continue}
        $bound=@($Plan.HashInputs|Where-Object Path -IEQ $old.Path)
        if($bound.Count -ne 1 -or ($bound[0]|ConvertTo-Json -Depth 8 -Compress) -cne ($old|ConvertTo-Json -Depth 8 -Compress)){
            throw 'Unprojected historical evidence must retain its complete F pin.'
        }
        Assert-SoundFFPin $old
    }
}
function Assert-SoundFFDumpOnlyInputs($Plan) {
    $f=Read-SoundFFImmutableF $Plan.ImmutableFF
    if(($Plan.StockInputs|ConvertTo-Json -Depth 15 -Compress) -cne ($f.Plan.StockInputs|ConvertTo-Json -Depth 15 -Compress) -or
        $Plan.Review.source -ine $f.Plan.Review.source -or $Plan.Review.stock_root -ine $f.Plan.Review.stock_root -or
        $Plan.SharedRepo -ine $f.Plan.SharedRepo -or $Plan.Python -ine $f.Plan.Python -or
        ($Plan.ImmutableFF.Artifacts|ConvertTo-Json -Depth 6 -Compress) -cne ($f.State.Artifacts|ConvertTo-Json -Depth 6 -Compress) -or
        $Plan.ImmutableFF.InventoryPath -ine (Join-Path $f.Plan.RunRoot 'logs/verify/stdout.log')){throw 'DumpOnly must reuse immutable F inputs.'}
    foreach($root in @($f.Plan.RunRoot,$Plan.CandidateRoot)){
        $root=[IO.Path]::GetFullPath($root).TrimEnd('\','/')
        if($Plan.RunRoot -ieq $root -or $Plan.RunRoot.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase) -or $root.StartsWith($Plan.RunRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Dump output overlaps preserved inputs.'}
    }
    $expected=@($f.Plan.HashInputs|Where-Object {[IO.Path]::GetExtension($_.Path) -iin @('.exe','.wav','.flac')})
    if(($Plan.PayloadInputs|ConvertTo-Json -Depth 6 -Compress) -cne ($expected|ConvertTo-Json -Depth 6 -Compress)){throw 'Exact deferred original/Python identities required.'}
    if($Plan.Profile -ceq 'StandardMod'){Assert-SoundFFSourceProjection $Plan $f.Plan}
    foreach($original in @($f.Plan.HashInputs|Where-Object {$_.Path.StartsWith($f.Plan.Review.source+'\',[StringComparison]::OrdinalIgnoreCase)})){
        $bound=@(@($Plan.HashInputs)+@($Plan.PayloadInputs)|Where-Object Path -IEQ $original.Path)
        if($bound.Count -ne 1 -or $bound[0].SHA256 -ine $original.SHA256 -or $bound[0].Bytes -ne $original.Bytes){throw 'Every original source must retain its F identity and guard.'}
    }
    foreach($pin in $Plan.HashInputs){
        if([IO.Path]::GetExtension($pin.Path) -inotin @('.ps1','.cs','.py','.json','.csv','.log')){throw 'DumpOnly bootstrap accepts source/text only.'}
    }
    foreach($pair in @(@($Plan.ImmutableFF.PlanPath,$Plan.ImmutableFF.PlanSHA256),@($Plan.ImmutableFF.StatePath,$Plan.ImmutableFF.StateSHA256),
        @($Plan.ImmutableFF.InventoryPath,$Plan.ImmutableFF.InventorySHA256))){
        $pins=@($Plan.HashInputs|Where-Object Path -IEQ $pair[0])
        if($pins.Count -ne 1 -or $pins[0].SHA256 -ine $pair[1]){throw 'Preserved F text evidence requires transaction guards.'}
    }
    Assert-SoundFFReadback $f.State.Reader $f.State.Artifacts
}
function Assert-SoundFFJobSource($HashInputs,[string]$SoundRoot) {
    $pin=@($HashInputs|Where-Object Path -IEQ (Join-Path $SoundRoot 'SoundBuildJob.cs'))
    if($pin.Count -ne 1){throw 'Exact sound-local job source pin required.'}
    Assert-SoundFFPin $pin[0]
}
function Assert-SoundFFExecutionPlan($Plan,[string]$SoundRoot) {
    $dumpOnly=$Plan.Profile -ceq 'DumpOnly'
    $standard=$Plan.Profile -ceq 'StandardMod';$qualifiedC=$dumpOnly -or $standard
    if($Plan.Profile -and !$qualifiedC){throw 'Unknown sound execution profile.'}
    foreach($entry in @(@('PhysicalBytes',8GB),@('CommitBytes',11GB),@('OutputStopBytes',64MB),@('LogBytesPerStream',2MB),@('CleanupMs',15000))){
        $value=$Plan.($entry[0]);if(($value -isnot [long] -and $value -isnot [int]) -or $value -ne $entry[1]){throw 'Exact typed native 8/11 budget and limits required.'}
    }
    if($Plan.Schema -cne 'iw7.original-sound-ff-execution/1' -or $Plan.HeavyExecutionAuthorizedByPlan -isnot [bool] -or $Plan.HeavyExecutionAuthorizedByPlan){throw 'Sound execution schema differs.'}
    foreach($path in @($Plan.RunRoot,$Plan.Work,$Plan.SharedRepo,$Plan.Python,$Plan.CandidateRoot,$Plan.Review.source)){Assert-SoundFFPath $path}
    if(Test-Path -LiteralPath $Plan.RunRoot){throw 'Fresh absent native RunRoot required; no retry.'}
    if($Plan.Work -ine (Join-Path $Plan.RunRoot 'work')){throw 'Owned work path differs.'}
    $candidate=if($qualifiedC){Assert-SoundFFFlacCandidate $Plan.CandidateRoot $Plan.CandidateReceiptSHA256 $Plan.CandidateStateSHA256}else{
        Assert-SoundFFChecksumCandidate $Plan.CandidateRoot $Plan.CandidateReceiptSHA256 $Plan.CandidateStateSHA256}
    if($qualifiedC){Assert-SoundFFDumpOnlyInputs $Plan}
    if($standard){Assert-SoundFFStandardSources $Plan $SoundRoot}
    if($Plan.Review.candidate_root -ine $Plan.CandidateRoot -or $Plan.Review.existing_candidate.path -ine $candidate.Path -or
        $Plan.Review.existing_candidate.sha256 -ine $candidate.SHA256 -or $Plan.Review.existing_candidate.bytes -ne $candidate.Bytes){throw 'Review and completed candidate differ.'}
    foreach($pair in @(@('build-receipt.json',$Plan.CandidateReceiptSHA256),@('supervisor-state.json',$Plan.CandidateStateSHA256))){
        $pin=@($Plan.HashInputs|Where-Object Path -IEQ (Join-Path $Plan.CandidateRoot $pair[0]))
        if($pin.Count -ne 1 -or $pin[0].SHA256 -ine $pair[1]){throw 'Candidate evidence must be guarded by the transaction.'}
    }
    if($Plan.Review.phase_adapter -ine (Join-Path $SoundRoot 'sound_ff_phase.py')){throw 'Bound sound phase adapter required.'}
    $staged=@('sound/community_original_sound_v1.all.aliases.csv','sound_assets/community/original_chime_v1.flac','soundbank/community_original_sound_v1.all.json','zone_source/sdk_original_sound_v1.csv')
    if($dumpOnly){$staged=@()}
    if($standard){$staged[3]='zone_source/mod.csv'}
    if(($Plan.Review.source_stage_relatives|Sort-Object|ConvertTo-Json -Compress) -cne ($staged|Sort-Object|ConvertTo-Json -Compress)){throw 'Exact profile source staging required.'}
    foreach($inputRoot in @($Plan.Review.source,$Plan.Review.stock_root,$Plan.CandidateRoot)+@(if($standard){Join-Path $SoundRoot 'standard-mod'})){
        $full=[IO.Path]::GetFullPath($inputRoot).TrimEnd('\','/')
        if($Plan.RunRoot -ieq $full -or $Plan.RunRoot.StartsWith($full+'\',[StringComparison]::OrdinalIgnoreCase) -or $full.StartsWith($Plan.RunRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Native root overlaps input root.'}
    }
    $zone=if($standard){'mod'}else{'sdk_original_sound_v1'};$outputs=@('.ff','.sabl','.sabs'|ForEach-Object {'zone/'+$zone+$_})
    if($dumpOnly){$outputs=@()}
    if(($Plan.MutableOutputs|ConvertTo-Json -Compress) -cne ($outputs|ConvertTo-Json -Compress)){throw 'Exact profile mutable outputs required.'}
    $phases=@($Plan.Review.phase_specs)
    $order=if($dumpOnly){'dump,read'}else{'build,verify,dump,read'}
    if(($phases.phase -join ',') -cne $order){throw 'Exact ordered sound phases required.'}
    $pythonPin=@($(if($qualifiedC){$Plan.PayloadInputs}else{$Plan.HashInputs})|Where-Object Path -IEQ $Plan.Python)
    if($pythonPin.Count -ne 1 -or $pythonPin[0].SHA256 -ine '4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a'){throw 'Reviewed Python required.'}
    foreach($phase in $phases){
        $isRead=$phase.phase -ceq 'read'
        $exe=if($isRead){$Plan.Python}else{Join-Path $Plan.Work 'zonetool.exe'}
        $hash=if($isRead){$pythonPin[0].SHA256}else{$candidate.SHA256}
        $args=if($isRead){@('-B',(Join-Path $SoundRoot 'read_sab.py'),'--source',$Plan.Review.source,'--banks',(Join-Path $Plan.Work 'zone'),
            '--contract',(Join-Path $SoundRoot 'sab_contract.json'),'--dump',(Join-Path $Plan.Work ('dump/'+$zone)),
            '--inventory',(Join-Path $Plan.RunRoot 'logs/verify/stdout.log'))}else{@('-headless','-unbuffered-io','-strict-content-sources',('-'+$phase.phase+'zone'),$zone)}
        if($dumpOnly -and $isRead){$args[11]=$Plan.ImmutableFF.InventoryPath;$args+=@('--dump-profile','DumpOnlyC')}
        if($standard -and $isRead){$args+=@('--dump-profile','StandardModC')}
        if($phase.schema -cne 'iw7.material-v2-phase/1' -or $phase.exe -ine $exe -or $phase.sha256 -ine $hash -or $phase.cwd -ine $Plan.Work -or
            $phase.logs -ine (Join-Path $Plan.RunRoot ('logs/'+$phase.phase)) -or ($phase.timeout -isnot [int] -and $phase.timeout -isnot [long]) -or
            $phase.timeout -ne $(if($isRead){30}else{240}) -or ($phase.arguments|ConvertTo-Json -Compress) -cne ($args|ConvertTo-Json -Compress)){throw 'Sound phase command/path/time differs.'}
    }
    if(@($Plan.StockInputs).Count -ne 72 -or @($Plan.StockInputs|Where-Object Mode -CEQ HardLink).Count -ne 71 -or @($Plan.StockInputs|Where-Object Mode -CEQ Copy).Count -ne 1 -or
        @($Plan.StockInputs|Where-Object {$_.Mode -ceq 'Copy' -and $_.Relative -ceq 'main/fileSysCheck.cfg' -and $_.Bytes -eq 77}).Count -ne 1){throw 'Exact reused 71-link/77-byte sentinel profile required.'}
    $required=@('read_sab.py','read_flac.py','sound_ff_phase.py','sab_contract.json','sab_ff_helpers.json','SoundFF.Core.ps1','Build-SoundFF.ps1')|ForEach-Object {Join-Path $SoundRoot $_}
    Assert-SoundFFHelperSources $SoundRoot $Plan.SharedRepo $Plan.HashInputs
    foreach($path in $required){if(@($Plan.HashInputs|Where-Object Path -IEQ $path).Count -ne 1){throw 'Required sound source pin missing.'}}
    Assert-SoundFFJobSource $Plan.HashInputs $SoundRoot
}
function Get-SoundFFStageSource($Plan,[string]$Relative,[string]$SoundRoot=$PSScriptRoot) {
    if($Plan.Profile -ceq 'StandardMod' -and $Relative -cin @('soundbank/community_original_sound_v1.all.json','zone_source/mod.csv')){
        return Join-Path $SoundRoot ('standard-mod/'+$Relative)
    }
    Join-Path $Plan.Review.source $Relative
}
function Assert-SoundFFStandardSources($Plan,[string]$SoundRoot) {
    foreach($pair in @(@('soundbank/community_original_sound_v1.all.json','soundbank/community_original_sound_v1.all.json'),@('zone_source/mod.csv','zone_source/sdk_original_sound_v1.csv'))){
        $path=Get-SoundFFStageSource $Plan $pair[0] $SoundRoot
        $pin=@($Plan.HashInputs|Where-Object Path -IEQ $path)
        if($pin.Count -ne 1){throw 'Exact standard source pin required.'}
        Assert-SoundFFPin $pin[0]
        $original=Join-Path $Plan.Review.source $pair[1]
        $originalPin=@($Plan.HashInputs|Where-Object Path -IEQ $original)
        if($originalPin.Count -ne 1){throw 'Original text pin required.'};Assert-SoundFFPin $originalPin[0]
        $expected=[IO.File]::ReadAllText($original)
        if($pair[0].EndsWith('.json')){
            $expected=$expected.Replace('"zone": "sdk_original_sound_v1"','"zone": "mod"')
            if(($expected|ConvertFrom-Json).zone -cne 'mod'){throw 'Explicit standard bank.zone required.'}
        }
        # Only checkout newline normalization; all fields, paths and whitespace stay bound.
        if([IO.File]::ReadAllText($path).Replace("`r`n","`n") -cne $expected.Replace("`r`n","`n")){throw 'Standard source differs beyond bank.zone or zone CSV name.'}
    }
}
function Assert-SoundFFStandardReadback($Read,$Artifacts) {
    if($Read.dump_profile -cne 'StandardModC' -or $Read.dump_streaminfo_block_size -ne 4096 -or $Read.inventory_provenance -cne 'CurrentVerifyPhase' -or
        $Read.bank_zone -cne 'mod' -or $Read.disk_zone -cne 'mod'){throw 'Standard reader profile or bank/disk zone differs.'}
    foreach($name in 'standard_source_verified','dump_bank_zone_verified','standard_filenames_verified'){
        if($Read.$name -isnot [bool] -or !$Read.$name){throw 'Standard source/dump/name evidence missing.'}
    }
    if(($Artifacts.Relative -join ',') -cne 'zone/mod.ff,zone/mod.sabl,zone/mod.sabs' -or ($Read.standard_filenames -join ',') -cne 'mod.ff,mod.sabl,mod.sabs'){
        throw 'Exact three standard artifacts required.'
    }
    $ff=$Read.fastfile;$artifact=$Artifacts[0]
    if($ff.bytes -isnot [int] -and $ff.bytes -isnot [long] -or $ff.bytes -ne $artifact.Bytes -or $ff.sha256 -ine $artifact.SHA256){throw 'Observed standard FF differs from retained bytes.'}
}
function Save-SoundFFState($Context) {
    if(Test-Path -LiteralPath $Context.Plan.RunRoot){[IO.File]::WriteAllText($Context.StatePath,($Context.State|ConvertTo-Json -Depth 25))}
}
function Get-SoundFFFileId([string]$Path) {[IW7HudFileIdentity]::Read($Path)}
function New-SoundFFJob([string]$Python,[string]$Arguments,[string]$Work) {[IW7.SoundFFTelemetryV1.BuildJob]::Prepare($Python,$Arguments,$Work)}
function Assert-SoundFFReadback($Read,$Artifacts) {
    if($Read.schema -cne 'iw7.original-sound-sab-read/1' -or $Read.status -cne 'SABBytesVerified' -or
        $Read.loaded.pcm_sha256 -cne '72cb02b5178ce424fd3df3dbfb28b0b9613f69a4da3af71a022b8b542a46ddd9'){throw 'Independent SAB receipt differs.'}
    if(($Read.inventory_asset_count -isnot [int] -and $Read.inventory_asset_count -isnot [long]) -or $Read.inventory_asset_count -ne 2){throw 'Soundbank plus native branding inventory required.'}
    foreach($name in 'source_alias_verified','source_alias_matches_sab_asset','dump_alias_values_verified','inventory_verified','dump_seek_frame_bytes_verified'){
        if($Read.$name -isnot [bool] -or !$Read.$name){throw 'Required sound readback evidence missing.'}
    }
    foreach($name in 'native_alias_index_verified','checksum_checksum_verified','dump_standalone_flac_validated','playback_verified','ready'){
        if($Read.$name -isnot [bool] -or $Read.$name){throw 'Sound readback overclaims acceptance.'}
    }
    foreach($pair in @(@('loaded','.sabl'),@('streamed','.sabs'))){
        $rows=@($Artifacts|Where-Object {$_.Relative.EndsWith($pair[1])});$bank=$Read.($pair[0])
        if($rows.Count -ne 1 -or $bank.sha256 -ine $rows[0].SHA256 -or ($bank.bytes -isnot [long] -and $bank.bytes -isnot [int]) -or $bank.bytes -ne $rows[0].Bytes){throw 'Reader bank bytes do not match retained artifacts.'}
    }
}
function Import-SoundFFHelpers([string]$Repo) {
    foreach($relative in 'ops/Base-Client.Core.ps1','ops/Resource-Scheduler.Core.ps1','ops/model-lab/ModelFF.Core.ps1',
        'sdk/modding/BeaconFF.Core.ps1','tools-source/asset-bridge/common/StockBinding.Core.ps1','tools-source/asset-bridge/surfaces/MaterialV2.Core.ps1'){
        . (Join-Path $Repo $relative)
    }
}
function Initialize-SoundFFNativeTypes([string]$Repo) {
    Add-Type -LiteralPath (Join-Path $PSScriptRoot 'SoundBuildJob.cs')
    Add-Type -LiteralPath (Join-Path $Repo 'ops/hud-lab/HudFileIdentity.cs')
}
function Measure-SoundFFOutputs($Context,[switch]$RecordBudgetFailure) {
    $items=@(Get-ChildItem -LiteralPath $Context.Plan.RunRoot -Recurse -Force)
    if(@($items|Where-Object {$_.Attributes -band [IO.FileAttributes]::ReparsePoint}).Count){throw 'Redirected output refused.'}
    $files=@($items|Where-Object {!$_.PSIsContainer})
    $bytes=Measure-MaterialV2OutputFiles $files $Context.Plan.Work $Context.State.Inputs
    # Keep the measured excess as evidence even when enforcing the stop cap.
    $Context.State.MaxObservedBytes=[math]::Max($Context.State.MaxObservedBytes,$bytes)
    $Context.State.FinalObservedBytes=$bytes;$Context.State.OutputBudgetError=$null
    try{
        Assert-BeaconOutputBudget $bytes
        foreach($file in $files){if($file.Name -in 'stdout.log','stderr.log' -and $file.Length -gt 2MB){throw 'Sound phase log exceeded 2 MiB.'}}
    }catch{
        $Context.State.OutputBudgetError=$_.Exception.Message
        if(!$RecordBudgetFailure){throw}
    }
}
function Save-SoundFFFinalState($Context,[switch]$Diagnostic) {
    if(!(Test-Path -LiteralPath $Context.Plan.RunRoot)){return}
    # Same bounded write/measure convergence as Save-AnimationFinalState. Count
    # the serialized counters and error strings themselves, including UTF-8.
    $Context.State.OutputAccountingStatus='Converged'
    for($pass=0;$pass -lt 4;$pass++){
        Save-SoundFFState $Context
        $previousFinal=$Context.State.FinalObservedBytes;$previousMax=$Context.State.MaxObservedBytes
        $previousError=$Context.State.OutputBudgetError
        Measure-SoundFFOutputs $Context -RecordBudgetFailure
        if($Context.State.FinalObservedBytes -eq $previousFinal -and $Context.State.MaxObservedBytes -eq $previousMax -and
            $Context.State.OutputBudgetError -ceq $previousError){
            if($Context.State.OutputBudgetError -and !$Diagnostic){throw $Context.State.OutputBudgetError}
            return
        }
    }
    throw 'Final sound receipt byte accounting did not converge.'
}
function Record-SoundFFJobCommitPeak($Context) {
    $memory=$Context.State.JobMemory
    if(!$Context.Owner -or !$memory -or !$memory.Phases.Count){return}
    $record=$memory.Phases[-1]
    if($record.Status -cne 'NotQueried'){return}
    $record.JobClosedAtQuery=[bool]$Context.Closed
    try {
        $value=$Context.Owner.PeakJobCommitBytes
        if($value -isnot [uint64]){throw 'Expected an unsigned 64-bit JobObject peak.'}
        $record.PeakJobCommitBytes=$value;$record.Status='Captured'
        if($null -eq $memory.MaxObservedPhaseJobCommitBytes -or $value -gt $memory.MaxObservedPhaseJobCommitBytes){
            $memory.MaxObservedPhaseJobCommitBytes=$value
        }
    }catch{
        # Telemetry cannot replace the original closure/exit decision. Missing
        # data stays null; a query error is not a zero-byte measurement.
        $record.Status='Unavailable';$record.Error=$_.Exception.Message
        if($record.Error.Length -gt 512){$record.Error=$record.Error.Substring(0,512)}
    }
}
function Invoke-SoundFFPhase($Context,$Spec) {
    $plan=$Context.Plan;$state=$Context.State
    if(!$state.JobMemory){
        $state.JobMemory=[ordered]@{Source='JobObjectExtendedLimitInformation.PeakJobMemoryUsed';
            Scope='Phase JobObjects only';SupervisorIncluded=$false;SupervisorPeakCommitBytes=$null;
            TransactionPeakCovered=$false;MaxObservedPhaseJobCommitBytes=$null;Phases=@()}
    }
    $state.JobMemory.Phases+=,[ordered]@{Phase=$Spec.phase;PeakJobCommitBytes=$null;Status='NotQueried';JobClosedAtQuery=$false;Error=$null}
    $specPath=Join-Path $plan.RunRoot ($Spec.phase+'-spec.json')
    [IO.File]::WriteAllText($specPath,($Spec|ConvertTo-Json -Depth 10));$specHash=(Get-FileHash -LiteralPath $specPath).Hash
    $Context.Guards.Add([IO.File]::Open($specPath,'Open','Read','Read'))
    $arguments=ConvertTo-MaterialV2Arguments @('-B',$plan.Review.phase_adapter,'--spec',$specPath,'--spec-sha256',$specHash,'--shared-repo',$plan.SharedRepo)
    # A throwing factory can have created a process without returning its owner.
    # Only positive original-job evidence can establish closure from this point.
    $Context.Closed=$false
    $Context.Owner=New-SoundFFJob $plan.Python $arguments $plan.Work
    $identity=Get-BeaconJobIdentity $Context.Owner $plan.Python $Spec.phase;$identity.SpecSHA256=$specHash;$identity.NativeExecutableSHA256=$Spec.sha256
    $state.Phases+=,$identity;Save-SoundFFState $Context
    $started=Start-MaterialV2OwnedPhase $Context.Owner $Context.Lease.Token
    $identity.StartedUtc=$started.StartedUtc;$identity.SchedulerAttached=$started.SchedulerAttached
    Wait-MaterialV2OwnedPhase $Context.Owner $identity $started.StartedMonotonicMs $Spec.timeout {
        param($snapshot,$changed)
        if($changed){Save-SoundFFState $Context}
        if(Test-Path -LiteralPath (Join-Path $plan.RunRoot 'stop.request')){throw 'Central original-job stop requested.'}
        Measure-SoundFFOutputs $Context
        $memory=Get-IW7ResourceSnapshot;if($memory.Committed -gt $memory.CommitLimit*.85){throw 'Commit pressure stop.'}
    }
    $Context.Closed=$true
    Record-SoundFFJobCommitPeak $Context
    $Context.Owner.Dispose();$Context.Owner=$null
    Assert-MaterialV2PhaseResult (Read-BeaconJson (Join-Path $Spec.logs 'phase.json') 16384) $Spec.phase $Spec.sha256 $identity
    $receipt=Read-BeaconJson (Join-Path $Spec.logs 'sound-phase.json') 16384
    if($receipt.schema -cne 'iw7.original-sound-ff-phase/1' -or $receipt.phase -cne $Spec.phase -or $receipt.verified -isnot [bool] -or !$receipt.verified -or
        $receipt.explicit_normal_pipe_returns -isnot [bool] -or !$receipt.explicit_normal_pipe_returns -or @($receipt.drain_exception_types).Count -ne 0 -or
        (Get-FileHash -LiteralPath (Join-Path $Spec.logs 'phase.json')).Hash -ine $receipt.existing_runner_receipt_sha256){throw 'Sound phase explicit EOF/native receipt failed.'}
    $identity.SoundReceipt=$receipt;Save-SoundFFState $Context
    # Shared wait already checks a fresh monotonic value after its getter/save
    # callback. Receipt/hash/dispose/final-save time must not escape this bound.
    $identity.PostReceiptDecisionElapsedMs=(Get-MaterialV2MonotonicMs)-$started.StartedMonotonicMs
    if($identity.PostReceiptDecisionElapsedMs -ge ($Spec.timeout+5)*1000){throw 'Sound phase acceptance deadline expired after receipt/save.'}
}
function Complete-SoundFFTransaction($Context) {
    $state=$Context.State;$intact=$true;$disposed=$true
    try {
        if($Context.Owner){
            try {
                if(!$Context.Closed){$state.JobCleanup=[ordered]@{};$Context.Closed=Stop-MaterialV2OwnedPhase $Context.Owner $state.JobCleanup}
            }finally{Record-SoundFFJobCommitPeak $Context}
            try{$Context.Owner.Dispose();$Context.Owner=$null}catch{$disposed=$false;$state.CleanupError=$_.Exception.Message}
        }
        foreach($pin in (Get-SoundFFRuntimePins $Context.Plan $Context.Lease)){try{Assert-SoundFFPin $pin}catch{$intact=$false;$state.CleanupError=$_.Exception.Message}}
        try{Assert-SoundFFPin ([pscustomobject]@{Path=$Context.PlanPath;SHA256=$Context.PlanSHA256})}catch{$intact=$false;$state.CleanupError=$_.Exception.Message}
        if($Context.InputsGuarded){try{Assert-ModelFFInputs $state.Inputs $Context.Plan.Work -SourceOnly;Assert-FFStockContent $state.Inputs}catch{$intact=$false;$state.CleanupError=$_.Exception.Message}}
        $state.JobClosureVerified=$Context.Closed;$state.JobDisposeCompleted=$disposed
        $state.SourceHashesUnchanged=($intact -and $Context.Closed -and $disposed)
        # Hard links cannot be removed while their source denies delete sharing.
        # Dispose owner first; unknown closure retains lease/evidence, not locks.
        foreach($guard in $Context.Guards){$guard.Dispose()};$Context.Guards.Clear();$state.ReadGuardsReleased=$true
        if(!$state.SourceHashesUnchanged){throw 'Closure or source proof incomplete; quarantine original inputs.'}
        if($Context.Saved){
            $state.RestorationStatus='Validating'
            Assert-ModelFFVacant $Context.Plan.Work
            Assert-ModelFFInputs $state.Inputs $Context.Plan.Work
            Restore-IW7BaseTransaction $state.Transaction
            $state.RestorationStatus='FilesRestoredPendingSourceProof'
            Assert-ModelFFInputs $state.Inputs $Context.Plan.Work -SourceOnly
            # Fresh guards and full content proof after unlink/restoration.
            foreach($entry in $state.Inputs){$Context.Guards.Add([IO.File]::Open($entry.Source,'Open','Read','Read'))}
            Assert-ModelFFInputs $state.Inputs $Context.Plan.Work -SourceOnly
            Assert-FFStockContent $state.Inputs
            foreach($pin in (Get-SoundFFRuntimePins $Context.Plan $Context.Lease)){Assert-SoundFFPin $pin}
            foreach($artifact in $state.Artifacts){
                $Context.Guards.Add([IO.File]::Open($artifact.ArtifactPath,'Open','Read','Read'))
                Assert-SoundFFPin ([pscustomobject]@{Path=$artifact.ArtifactPath;SHA256=$artifact.SHA256;Bytes=$artifact.Bytes})
            }
            if($state.DumpFlac){$Context.Guards.Add([IO.File]::Open($state.DumpFlac.Path,'Open','Read','Read'));Assert-SoundFFPin $state.DumpFlac}
            $state.Restored=$true;$state.StockPreserved=$true;$state.RestorationStatus='Confirmed'
        }else{$state.Restored=$true;$state.StockPreserved=$true;$state.RestorationStatus='NotStaged'}
        # Dispose the final proof guards before the final receipt so finally
        # cannot add an uncounted ReadGuardsReleased change after lease release.
        foreach($guard in $Context.Guards){$guard.Dispose()};$Context.Guards.Clear();$state.ReadGuardsReleased=$true
        Save-SoundFFFinalState $Context
        if($Context.Lease){Exit-IW7ResourceLease -Token $Context.Lease.Token;$state.RetainedLeaseToken=$null;$Context.Lease=$null}
        # The only normal change after release is token -> null (smaller JSON).
        # Recount it too; no further normal state write follows this convergence.
        Save-SoundFFFinalState $Context
    }catch{
        $state.Quarantined=$true;$state.Status='Failed';$state.CleanupError=$_.Exception.Message;$state.SourceHashesUnchanged=$false
        if($state.RestorationStatus -ceq 'FilesRestoredPendingSourceProof'){$state.RestorationStatus='FilesRestoredUnverified'}
        elseif($state.RestorationStatus -cne 'Confirmed'){$state.RestorationStatus='DeferredQuarantine'}
    }
    finally{foreach($guard in $Context.Guards){$guard.Dispose()};$Context.Guards.Clear();$state.ReadGuardsReleased=$true}
    if($state.Status -ceq 'Failed'){
        try{Save-SoundFFFinalState $Context -Diagnostic}catch{
            # Files may still grow when job closure is unknown. Preserve a
            # bounded attempt and explicitly retract the final byte claim.
            $state.OutputAccountingStatus='Unconfirmed';$state.FinalObservedBytes=$null
            $state.OutputAccountingError=$_.Exception.Message
            Save-SoundFFState $Context
        }
    }
}
function Invoke-SoundFFTransaction($Plan,[string]$PlanPath,[string]$PlanSHA256) {
    $dumpOnly=$Plan.Profile -ceq 'DumpOnly'
    $standard=$Plan.Profile -ceq 'StandardMod';$qualifiedC=$dumpOnly -or $standard
    $state=[ordered]@{Schema='iw7.original-sound-ff-result/1';Status='Preparing';Work=$Plan.Work;Inputs=@();Phases=@();Artifacts=@();Reader=$null;
        Transaction=$null;Restored=$false;StockPreserved=$false;RestorationStatus='Pending';JobClosureVerified=$false;JobDisposeCompleted=$false;
        SourceHashesUnchanged=$false;ReadGuardsReleased=$false;Quarantined=$false;RetainedLeaseToken=$null;Failure=$null;CleanupError=$null;
        MaxObservedBytes=0L;FinalObservedBytes=$null;OutputAccountingStatus='Pending';OutputAccountingError=$null;OutputBudgetError=$null;
        OutputAccountingScope='RunRoot file lengths after state write; only verified staged hardlinks excluded; snapshot, not continuous disk maximum';
        JobCleanup=$null;Ready=$false;PlaybackVerified=$false}
    $c=[pscustomobject]@{Plan=$Plan;PlanPath=$PlanPath;PlanSHA256=$PlanSHA256;State=$state;StatePath=(Join-Path $Plan.RunRoot 'state.local.json');
        Lease=$null;Owner=$null;Closed=$true;Saved=$false;InputsGuarded=$false;Guards=[Collections.Generic.List[IDisposable]]::new()}
    try {
        foreach($pin in @($Plan.HashInputs)+@([pscustomobject]@{Path=$PlanPath;SHA256=$PlanSHA256})){
            $c.Guards.Add([IO.File]::Open($pin.Path,'Open','Read','Read'));Assert-SoundFFPin $pin
        }
        . Import-SoundFFHelpers $Plan.SharedRepo
        $c.Lease=Enter-IW7ResourceLease -Scope $Plan.Work -Kind Extract -PhysicalBytes 8GB -CommitBytes 11GB -Owner 'Original sound SAB and FF build verify dump read'
        $state.RetainedLeaseToken=$c.Lease.Token
        [IO.Directory]::CreateDirectory($Plan.RunRoot)|Out-Null;Save-SoundFFState $c
        if($qualifiedC){
            foreach($pin in $Plan.PayloadInputs){$c.Guards.Add([IO.File]::Open($pin.Path,'Open','Read','Read'));Assert-SoundFFPin $pin}
            $state.Profile=$Plan.Profile;$state.ImmutableFF=$Plan.ImmutableFF
            if($dumpOnly){$state.Artifacts=@($Plan.ImmutableFF.Artifacts)}
        }
        Initialize-SoundFFNativeTypes $Plan.SharedRepo
        $candidate=if($qualifiedC){Assert-SoundFFFlacCandidate $Plan.CandidateRoot $Plan.CandidateReceiptSHA256 $Plan.CandidateStateSHA256 $c.Guards}else{
            Assert-SoundFFChecksumCandidate $Plan.CandidateRoot $Plan.CandidateReceiptSHA256 $Plan.CandidateStateSHA256 $c.Guards}
        $state.Inputs=@($Plan.StockInputs)
        $stage=@(foreach($relative in $Plan.Review.source_stage_relatives){
            $path=Get-SoundFFStageSource $Plan $relative;$pin=@((Get-SoundFFRuntimePins $Plan $c.Lease)|Where-Object Path -IEQ $path)
            if($pin.Count -ne 1){throw 'Staged original sound input pin missing.'}
            [pscustomobject]@{Relative=$relative;Source=$path;ExpectedSHA256=$pin[0].SHA256}
        })+@([pscustomobject]@{Relative='zonetool.exe';Source=$candidate.Path;ExpectedSHA256=$candidate.SHA256})
        if($dumpOnly){$stage+=@(foreach($a in $Plan.ImmutableFF.Artifacts){
            [pscustomobject]@{Relative=$a.Relative;Source=$a.ArtifactPath;ExpectedSHA256=$a.SHA256}
        })}
        foreach($entry in $stage){
            if($entry.Relative -iin $state.Inputs.Relative){throw 'Source/stock collision.'}
            $pin=Get-SoundFFPin $entry.Source
            $state.Inputs+=,[pscustomobject]@{Relative=$entry.Relative;Source=$entry.Source;Mode='HardLink';Bytes=$pin.Bytes;ModifiedUtc=$pin.ModifiedUtc;
                Attributes=$pin.Attributes;ExpectedSHA256=$entry.ExpectedSHA256}
        }
        foreach($entry in $state.Inputs){
            $null=Resolve-IW7BasePath (Split-Path $entry.Source) (Split-Path $entry.Source -Leaf)
            $c.Guards.Add([IO.File]::Open($entry.Source,'Open','Read','Read'));$id=Get-SoundFFFileId $entry.Source
            Assert-FFStockIdentity $entry $id;Set-MaterialV2SourceIdentity $entry $id
            if('ExpectedSourceId' -cnotin $entry.PSObject.Properties.Name){$entry|Add-Member NoteProperty ExpectedSourceId $id}
        }
        $c.InputsGuarded=$true;Assert-ModelFFInputs $state.Inputs $Plan.Work -SourceOnly;Assert-FFStockContent $state.Inputs
        [IO.Directory]::CreateDirectory($Plan.Work)|Out-Null
        $state.Transaction=Save-IW7BaseTransaction ([pscustomobject]@{GameRoot=$Plan.Work;MutableFiles=@($state.Inputs.Relative)+@($Plan.MutableOutputs);ProfileDirectory='unused';ProfileDirectories=@()}) (Join-Path $Plan.RunRoot 'backup')
        $c.Saved=$true;Save-SoundFFState $c
        foreach($entry in $state.Inputs){
            $target=Resolve-IW7BasePath $Plan.Work $entry.Relative;[IO.Directory]::CreateDirectory((Split-Path $target))|Out-Null
            if($entry.Mode -ceq 'Copy'){Copy-Item -LiteralPath $entry.Source -Destination $target}else{New-Item -ItemType HardLink -Path $target -Target $entry.Source|Out-Null}
            $entry|Add-Member NoteProperty TargetId (Get-SoundFFFileId $target)
            if($entry.Mode -ceq 'HardLink' -and $entry.TargetId -cne $entry.SourceId){throw 'Staged hardlink identity differs.'}
            if($entry.Mode -ceq 'Copy'){Assert-MaterialV2CopyIdentity $entry $entry.TargetId;(Get-Item -LiteralPath $target).IsReadOnly=$false}
        }
        Assert-ModelFFInputs $state.Inputs $Plan.Work
        [IO.Directory]::CreateDirectory((Join-Path $Plan.RunRoot 'logs'))|Out-Null
        foreach($spec in $Plan.Review.phase_specs){
            Invoke-SoundFFPhase $c $spec
            if($spec.phase -ceq 'build'){
                [IO.Directory]::CreateDirectory((Join-Path $Plan.RunRoot 'artifacts'))|Out-Null
                foreach($relative in $Plan.MutableOutputs){
                    $path=Resolve-IW7BasePath $Plan.Work $relative;$file=Get-Item -LiteralPath $path
                    $wanted=if($relative.EndsWith('.sabl')){114816}elseif($relative.EndsWith('.sabs')){4096}else{0}
                    if(($wanted -and $file.Length -ne $wanted) -or $file.Length -lt 1 -or $file.Length -gt 1MB){throw 'Native sound output size differs.'}
                    $c.Guards.Add([IO.File]::Open($path,'Open','Read','Read'));$hash=(Get-FileHash -LiteralPath $path).Hash
                    $target=Join-Path $Plan.RunRoot ('artifacts/'+$file.Name);if(Test-Path -LiteralPath $target){throw 'Artifact overwrite refused.'}
                    Copy-Item -LiteralPath $path -Destination $target
                    if((Get-FileHash -LiteralPath $target).Hash -ine $hash){throw 'Artifact preservation hash differs.'}
                    $c.Guards.Add([IO.File]::Open($target,'Open','Read','Read'))
                    $state.Artifacts+=,[pscustomobject]@{Relative=$relative;Bytes=$file.Length;SHA256=$hash;ArtifactPath=$target}
                }
            }
        }
        $read=Read-BeaconJson (Join-Path $Plan.RunRoot 'logs/read/stdout.log') 16384
        Assert-SoundFFReadback $read $state.Artifacts
        if($dumpOnly -and ($read.dump_profile -cne 'DumpOnlyC' -or $read.dump_streaminfo_block_size -ne 4096 -or $read.inventory_provenance -cne 'PreservedBuildF')){throw 'DumpOnly reader profile differs.'}
        if($standard){Assert-SoundFFStandardReadback $read $state.Artifacts}
        $state.Reader=$read;$state.Status=if($dumpOnly){'SoundDumpOnlyBytesVerified'}elseif($standard){'SoundStandardModBytesVerified'}else{'SoundSABAndFFBytesVerified'}
        if($dumpOnly){
            $path=Join-Path $Plan.Work 'dump/sdk_original_sound_v1/sound_assets/community/original_chime_v1.flac'
            $c.Guards.Add([IO.File]::Open($path,'Open','Read','Read'));$state.DumpFlac=Get-SoundFFPin $path
        }
        Measure-SoundFFOutputs $c;Save-SoundFFState $c
    }catch{$state.Status='Failed';$state.Failure=$_.Exception.Message}
    finally{Complete-SoundFFTransaction $c}
    if($state.Status -ceq 'Failed' -or !$state.JobClosureVerified -or !$state.SourceHashesUnchanged -or !$state.Restored -or $state.RetainedLeaseToken){throw ('Sound FF incomplete; preserve state/inputs/reservation. '+$state.Failure+' '+$state.CleanupError)}
    $state
}

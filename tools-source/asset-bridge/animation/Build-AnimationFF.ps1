param(
    [string]$ProviderRoot=(Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent),
    [Parameter(Mandatory)][string]$RunRoot,
    [Parameter(Mandatory)][string]$NativeInput,
    [Parameter(Mandatory)][string]$NativeReceipt,
    [Parameter(Mandatory)][string]$NativeReceiptSHA256,
    [Parameter(Mandatory)][string]$StockRoot,
    [Parameter(Mandatory)][string]$StockReceipt,
    [Parameter(Mandatory)][string]$StockReceiptSHA256,
    [string]$StockBindingReceipt,
    [string]$StockBindingReceiptSHA256,
    [string]$ReviewedStockManifest,
    [string]$ReviewedStockManifestSHA256,
    [Parameter(Mandatory)][string]$CandidateRoot,
    [string]$CandidateArtifactSHA256,
    [Parameter(Mandatory)][string]$JobSource,
    [string]$JobSourceSHA256,
    [Parameter(Mandatory)][string]$PythonExe,
    [string]$PythonSHA256,
    [hashtable]$ProviderHashes,
    [switch]$Run
)
# Default plan has no Add-Type, lease, directory creation or child process.
$ErrorActionPreference='Stop'
. "$PSScriptRoot/AnimationFF.Core.ps1"
$stockCore=Join-Path (Split-Path $PSScriptRoot -Parent) 'common/StockBinding.Core.ps1'
Assert-AnimationPureImport $stockCore
. $stockCore
$bindings=Get-AnimationProviderBindings $ProviderRoot $ProviderHashes -RequirePins:$Run
foreach($name in @('ops/Base-Client.Core.ps1','sdk/modding/BeaconFF.Core.ps1','ops/model-lab/ModelFF.Core.ps1')){
    Assert-AnimationPureImport $bindings[$name].Path
    . $bindings[$name].Path
}
$plan=New-AnimationFFPlan -Bindings $bindings -RunRoot $RunRoot -AnimationRoot $PSScriptRoot -NativeInput $NativeInput `
    -NativeReceipt $NativeReceipt -NativeReceiptSHA256 $NativeReceiptSHA256 -StockRoot $StockRoot -StockReceipt $StockReceipt `
    -StockReceiptSHA256 $StockReceiptSHA256 -CandidateRoot $CandidateRoot -CandidateArtifactSHA256 $CandidateArtifactSHA256 `
    -JobSource $JobSource -JobSourceSHA256 $JobSourceSHA256 -PythonExe $PythonExe -PythonSHA256 $PythonSHA256 `
    -StockBindingReceipt $StockBindingReceipt -StockBindingReceiptSHA256 $StockBindingReceiptSHA256 `
    -ReviewedStockManifest $ReviewedStockManifest -ReviewedStockManifestSHA256 $ReviewedStockManifestSHA256 -RequirePins:$Run
if(!$Run){$plan|ConvertTo-Json -Depth 10;return}
foreach($type in @('IW7.CommunityBuild.BuildJob','IW7HudFileIdentity','IW7ResourceMemoryV1')){
    if($type -as [type]){throw 'Use a fresh PowerShell host for source-bound native helpers.'}
}
$RunRoot=$plan.RunRoot;$work=$plan.Work
$statePath=Join-Path $RunRoot 'state.local.json'
$guards=[Collections.Generic.List[IDisposable]]::new();$lease=$null;$owner=$null;$closed=$true;$saved=$false;$created=$false
$state=[ordered]@{Schema='iw7.animation-ff-build/1';Work=$work;Inputs=@($plan.StockInputs);Plan=$plan;Status='Preparing';Phases=@();
    Restored=$false;StockPreserved=$false;RestorationStatus='Pending';CleanupError=$null;RetainedLeaseToken=$null;FF=$null;
    MaxObservedBytes=0L;FinalObservedBytes=$null;InventoryVerified=$false;AnimationRoundtripVerified=$false;RuntimeVerified=$false;Ready=$false}
$overall=[Diagnostics.Stopwatch]::StartNew()
function Save-AnimationState {Write-ModelFFState $state $statePath}
function Measure-AnimationOutput([switch]$Final) {
    # Copy-mode sentinel is counted. Only verified, guarded hardlinks are exempt.
    $exempt=@($state.Inputs|Where-Object {$_.Mode -ceq 'HardLink' -and $_.TargetId -and $_.TargetId -ceq $_.SourceId}|ForEach-Object Relative)
    $bytes=Measure-BeaconOutputFiles @(Get-ChildItem -LiteralPath $RunRoot -File -Recurse -Force) $work $exempt
    $state.MaxObservedBytes=[math]::Max($state.MaxObservedBytes,$bytes)
    if($Final){$state.FinalObservedBytes=$bytes}
    Assert-BeaconOutputBudget $bytes
}
function Assert-AnimationRunningBudget {
    if($overall.Elapsed.TotalSeconds -gt $plan.OverallSeconds){throw 'Animation group exceeded 900 seconds.'}
    if(Test-Path -LiteralPath (Join-Path $RunRoot 'stop.request')){throw 'Coordinator requested owned stop.'}
    Measure-AnimationOutput
    $memory=Get-IW7ResourceSnapshot
    if($memory.Committed -gt $memory.CommitLimit*0.85){throw 'Commit pressure exceeded 85 percent.'}
}
function Invoke-AnimationPhase([string]$Phase,[string]$Exe,[string]$Hash) {
    Assert-AnimationRunningBudget
    $logs=Join-Path $RunRoot $Phase
    $arguments=@('-B',$plan.Adapter,'--shared-adapter',$bindings['sdk/modding/beacon_tool_phase.py'].Path,
        '--shared-sha256',$bindings['sdk/modding/beacon_tool_phase.py'].SHA256,'--reader-sha256',$plan.SourceHashes[$plan.Reader],
        '--phase',$Phase,'--exe',$Exe,'--sha256',$Hash,'--work',$work,'--logs',$logs,
        '--roundtrip',(Join-Path $RunRoot 'roundtrip/paris_original_probe_bend.xab'))
    $quoted=ConvertTo-AnimationArguments $arguments
    # Even a failed native factory needs explicit closure evidence; do not infer
    # it from absence of a returned owner. A failed Prepare quarantines the lease.
    $script:closed=$false
    $script:owner=[IW7.CommunityBuild.BuildJob]::Prepare($plan.PythonExe,$quoted,$work)
    $identity=Get-BeaconJobIdentity $owner $plan.PythonExe $Phase
    $state.Phases+=,$identity;Save-AnimationState
    # Register the original still-suspended root before it can launch descendants.
    Add-IW7ResourceProcess -Token $lease.Token -ProcessId $owner.PID
    $owner.Resume();$phaseClock=[Diagnostics.Stopwatch]::StartNew()
    $seconds=if($Phase -ceq 'read'){$plan.ReaderSeconds+5}else{$plan.PhaseSeconds+5}
    while(!$owner.Exited -or $owner.Active -ne 0){
        if($owner.Exited -and $owner.Active -ne 0){throw 'Phase parent exited with descendants; stop original job.'}
        if($phaseClock.Elapsed.TotalSeconds -gt $seconds){throw 'Animation phase deadline exceeded; stop original job.'}
        Assert-AnimationRunningBudget
        Start-Sleep -Milliseconds 100
    }
    $identity.ExitCode=$owner.ExitCode;$identity.JobActiveAtClose=$owner.Active
    $script:closed=$true;$owner.Dispose();$script:owner=$null;Save-AnimationState
    Assert-AnimationRunningBudget;Save-AnimationState;Measure-AnimationOutput
    $receipt=Read-BeaconJson (Join-Path $logs 'phase.json')
    if($identity.ExitCode -ne 0 -or $receipt.schema -cne 'iw7.beacon-tool-phase/1' -or $receipt.phase -cne $Phase -or
        $receipt.exit_code -ne 0 -or $receipt.failure -or $receipt.log_limit_each -ne $plan.StreamLimitBytes){throw 'Animation phase failed; bounded logs retained.'}
    [IO.File]::ReadAllText((Join-Path $logs 'stdout.log'))
}
try {
    # Hold every imported provider and bounded source against write/delete races.
    $pins=[ordered]@{}
    foreach($item in $bindings.Values){$pins[$item.Path]=$item.SHA256}
    foreach($path in $plan.SourceHashes.Keys){$pins[$path]=$plan.SourceHashes[$path]}
    $pins[$JobSource]=$JobSourceSHA256;$pins[$plan.PythonExe]=$plan.PythonSHA256
    $pins[$plan.Candidate.Path]=$plan.Candidate.SHA256
    foreach($path in $pins.Keys){$guards.Add([IO.File]::Open($path,'Open','Read','Read'));Assert-BeaconHash $path $pins[$path]}
    . $bindings['ops/Resource-Scheduler.Core.ps1'].Path
    $lease=Enter-IW7ResourceLease -Scope $work -Kind Extract -PhysicalBytes $plan.PhysicalBytes -CommitBytes $plan.CommitBytes -Owner 'Animation FF build inventory dump reader'
    $state.RetainedLeaseToken=$lease.Token
    Add-Type -LiteralPath $JobSource
    Add-Type -LiteralPath $bindings['ops/hud-lab/HudFileIdentity.cs'].Path
    foreach($pair in @(@('zonetool.exe',$plan.Candidate.Path),@('xanim/paris_original_probe_bend.xab',$plan.NativeInput),@('zone_source/sdk_animation_probe.csv',$plan.ZoneCSV))){
        $file=Get-Item -LiteralPath $pair[1]
        $state.Inputs+=,[pscustomobject]@{Relative=$pair[0];Source=$file.FullName;Mode='HardLink';Bytes=$file.Length;ModifiedUtc=$file.LastWriteTimeUtc.ToString('o');Attributes=[int]$file.Attributes}
    }
    foreach($entry in $state.Inputs){
        $null=Resolve-IW7BasePath (Split-Path $entry.Source -Parent) (Split-Path $entry.Source -Leaf)
        $guards.Add([IO.File]::Open($entry.Source,'Open','Read','Read'))
        $sourceId=[IW7HudFileIdentity]::Read($entry.Source)
        Assert-FFStockIdentity $entry $sourceId
        $entry|Add-Member NoteProperty SourceId $sourceId
    }
    # All guards are already held. Deduplicate hash reads by verified NTFS ID,
    # not by guessed relative aliases; no full stock hashing in plan mode.
    Assert-FFStockContent $state.Inputs
    Assert-ModelFFInputs $state.Inputs $work -SourceOnly
    if(Test-Path -LiteralPath $RunRoot){throw 'Animation run directory appeared during admission; preserve it.'}
    New-Item -ItemType Directory -Path $RunRoot -ErrorAction Stop|Out-Null
    $created=$true
    [IO.Directory]::CreateDirectory($work)|Out-Null
    $state.Transaction=Save-IW7BaseTransaction ([pscustomobject]@{GameRoot=$work;MutableFiles=@($state.Inputs.Relative)+@('zone/sdk_animation_probe.ff');ProfileDirectory='unused';ProfileDirectories=@()}) (Join-Path $RunRoot 'backup')
    $saved=$true;Save-AnimationState
    foreach($entry in $state.Inputs){
        $target=Resolve-IW7BasePath $work $entry.Relative
        [IO.Directory]::CreateDirectory((Split-Path $target))|Out-Null
        if($entry.Mode -ceq 'Copy'){Copy-Item -LiteralPath $entry.Source -Destination $target}else{New-Item -ItemType HardLink -Path $target -Target $entry.Source|Out-Null}
        $entry|Add-Member NoteProperty TargetId ([IW7HudFileIdentity]::Read($target))
        if($entry.Mode -ceq 'HardLink' -and $entry.TargetId -cne $entry.SourceId){throw 'Staged NTFS identity differs.'}
        if($entry.Mode -ceq 'Copy'){
            if($entry.TargetId -ceq $entry.SourceId){throw 'Sentinel copy aliases stock; do not alter its attributes.'}
            # Only this separately created owned file may become writable.
            $copy=Get-Item -LiteralPath $target
            if($copy.IsReadOnly){$copy.IsReadOnly=$false}
        }
    }
    Assert-ModelFFInputs $state.Inputs $work
    $state.Status='Building';Save-AnimationState
    $buildLog=Invoke-AnimationPhase build (Join-Path $work 'zonetool.exe') $plan.Candidate.SHA256
    if(!$buildLog.Contains('Parsing xanim "paris_original_probe_bend"...')){throw 'Original animation parsing marker missing.'}
    $ff=Resolve-IW7BasePath $work 'zone/sdk_animation_probe.ff';$size=(Get-Item -LiteralPath $ff).Length
    if($size -lt 1 -or $size -gt $plan.ArtifactLimitBytes){throw 'Animation FF must be nonempty and at most 1 MiB.'}
    Copy-Item -LiteralPath $ff -Destination (Join-Path $RunRoot 'mod.ff')
    $state.FF=@{Bytes=$size;SHA256=(Get-FileHash -LiteralPath $ff).Hash;Path='mod.ff'};Save-AnimationState
    $rows=@(Get-AnimationInventory (Invoke-AnimationPhase verify (Join-Path $work 'zonetool.exe') $plan.Candidate.SHA256))
    $rows|Set-Content -LiteralPath (Join-Path $RunRoot 'assets.csv');$state.InventoryVerified=$true;Save-AnimationState
    $null=Invoke-AnimationPhase dump (Join-Path $work 'zonetool.exe') $plan.Candidate.SHA256
    $dump=Resolve-IW7BasePath $work 'dump/sdk_animation_probe/xanim/paris_original_probe_bend.xab'
    $size=(Get-Item -LiteralPath $dump).Length
    if($size -lt 1 -or $size -gt $plan.DumpLimitBytes){throw 'Original animation re-dump exceeded bound.'}
    [IO.Directory]::CreateDirectory((Join-Path $RunRoot 'roundtrip'))|Out-Null
    $redump=Join-Path $RunRoot 'roundtrip/paris_original_probe_bend.xab'
    Copy-Item -LiteralPath $dump -Destination $redump
    $readback=(Invoke-AnimationPhase read $plan.PythonExe $plan.PythonSHA256)|ConvertFrom-Json
    Assert-AnimationReadback $readback
    if($readback.sha256 -ine (Get-FileHash -LiteralPath $redump).Hash){throw 'Reader result is not bound to retained re-dump.'}
    $state.Readback=$readback;$state.AnimationRoundtripVerified=$true
    $state.Status='FFInventoryAndAnimationRoundtripVerified';Save-AnimationState;Measure-AnimationOutput -Final
} catch {$state.Failure=$_.Exception.Message;$state.Status='Failed';throw}
finally {
    if($owner){
        try{
            $owner.Stop();$stopClock=[Diagnostics.Stopwatch]::StartNew()
            while(($owner.Active -ne 0 -or !$owner.Exited) -and $stopClock.Elapsed.TotalSeconds -lt 15){Start-Sleep -Milliseconds 100}
            $closed=($owner.Active -eq 0 -and $owner.Exited)
        }catch{$closed=$false}
        if($closed){$owner.Dispose();$owner=$null}
    }
    if(!$closed){[AppDomain]::CurrentDomain.SetData(('IW7.AnimationFF.Quarantine.'+$lease.Token),@{Owner=$owner;Guards=$guards;State=$state})}
    Complete-AnimationFF $state $statePath $lease $closed $saved $guards
    if($created){
        try{Save-AnimationState;Measure-AnimationOutput -Final;Save-AnimationState;Measure-AnimationOutput -Final}
        catch{$state.Status='Failed';$state.Failure=$_.Exception.Message;Save-AnimationState;throw}
    }
}

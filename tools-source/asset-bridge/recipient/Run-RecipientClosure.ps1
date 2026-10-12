param([Parameter(Mandatory)][string]$ProviderRoot,[Parameter(Mandatory)][string]$SpecPath,[switch]$Run,[switch]$ReferencesOnly,[switch]$FatalTextDiagnostic)
# Source-only plan by default. Native execution additionally needs coordinator GO.
$ErrorActionPreference='Stop'
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
if(![IO.Path]::IsPathFullyQualified($ProviderRoot) -or ![IO.Path]::IsPathFullyQualified($SpecPath)){throw 'Absolute provider/spec paths required.'}
$pins=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'provider-pins.json') -Raw|ConvertFrom-Json -AsHashtable
$bindings=[ordered]@{}
foreach($name in $pins.Keys){
    $path=[IO.Path]::GetFullPath((Join-Path $ProviderRoot $name));$cursor=$path
    while($cursor){if((Get-Item -LiteralPath $cursor).Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)){throw 'Provider reparse ancestry refused.'};$cursor=Split-Path $cursor -Parent}
    if((Get-FileHash -LiteralPath $path).Hash -ine $pins[$name]){throw "Provider hash changed: $name"}
    $bindings[$name]=[pscustomobject]@{Path=$path;SHA256=$pins[$name]}
}
. $bindings['tools-source/asset-bridge/animation/AnimationFF.Core.ps1'].Path
foreach($name in @('ops/Base-Client.Core.ps1','sdk/modding/BeaconFF.Core.ps1','ops/model-lab/ModelFF.Core.ps1','tools-source/asset-bridge/common/StockBinding.Core.ps1')){
    Assert-AnimationPureImport $bindings[$name].Path
    . $bindings[$name].Path
}
Assert-AnimationPureImport (Join-Path $PSScriptRoot 'Recipient.Core.ps1')
. "$PSScriptRoot/Recipient.Core.ps1"
$specHash=(Get-FileHash -LiteralPath $SpecPath).Hash
$plan=New-RecipientPlan (Read-BeaconJson $SpecPath) $repo $PSScriptRoot $bindings -ReferencesOnly:$ReferencesOnly -FatalTextDiagnostic:$FatalTextDiagnostic
$plan.SourceHashes[$SpecPath]=$specHash
if(!$Run){$plan|ConvertTo-Json -Depth 12;return}
foreach($type in @('IW7.CommunityBuild.BuildJob','IW7HudFileIdentity','IW7ResourceMemoryV1')){
    if($type -as [type]){throw 'Fresh PowerShell host required for source-bound native helpers.'}
}
$runRoot=$plan.RunRoot;$work=$plan.Work;$statePath=Join-Path $runRoot 'state.local.json'
$guards=[Collections.Generic.List[IDisposable]]::new();$lease=$null;$owner=$null;$closed=$true;$saved=$false;$created=$false
$state=[ordered]@{Schema='iw7.recipient-closure-run/1';Work=$work;Inputs=@($plan.StockInputs);Plan=$plan;Status='Preparing';Phases=@();
    Restored=$false;StockPreserved=$false;RestorationStatus='Pending';CleanupError=$null;RetainedLeaseToken=$null;
    MaxObservedBytes=0L;FinalObservedBytes=$null;NativeExecuted=$false;ReferencesVerified=$false;ScriptBytesVerified=$false;DiagnosticOnly=[bool]$plan.FatalTextDiagnostic;
    ClosureComplete=$false;Ready=$false;RuntimeVerified=$false}
$overall=[Diagnostics.Stopwatch]::StartNew()
function Save-RecipientState {Write-ModelFFState $state $statePath}
function Measure-RecipientOutput([switch]$Final) {
    $exempt=@($state.Inputs|Where-Object {$_.Mode -ceq 'HardLink' -and $_.TargetId -and $_.TargetId -ceq $_.SourceId}|ForEach-Object Relative)
    $bytes=Measure-BeaconOutputFiles @(Get-ChildItem -LiteralPath $runRoot -File -Recurse -Force) $work $exempt
    $state.MaxObservedBytes=[math]::Max($state.MaxObservedBytes,$bytes)
    if($Final){$state.FinalObservedBytes=$bytes}
    if($bytes -lt 0 -or $bytes -gt $plan.OutputStopBytes){throw 'Recipient output exceeded 256 MiB stop threshold.'}
}
function Save-RecipientFinalState {
    for($pass=0;$pass -lt 4;$pass++){
        Save-RecipientState;$previousFinal=$state.FinalObservedBytes;$previousMax=$state.MaxObservedBytes
        Measure-RecipientOutput -Final
        if($state.FinalObservedBytes -eq $previousFinal -and $state.MaxObservedBytes -eq $previousMax){return}
    }
    throw 'Final recipient byte accounting did not converge.'
}
function Assert-RecipientBudget {
    if($overall.Elapsed.TotalSeconds -gt $plan.OverallSeconds){throw 'Recipient group active-work deadline exceeded.'}
    if(Test-Path -LiteralPath (Join-Path $runRoot 'stop.request')){throw 'Coordinator requested owned stop.'}
    if($plan.FatalTextDiagnostic -and (Test-Path -LiteralPath (Join-Path $runRoot 'diagnostic-stop.request'))){throw 'Fatal-text diagnostic finished; original job stop required.'}
    Measure-RecipientOutput
    $memory=Get-IW7ResourceSnapshot
    if($memory.Committed -gt $memory.CommitLimit*0.85){throw 'Commit pressure exceeded 85 percent.'}
}
function Invoke-RecipientPhase([string]$Phase) {
    Assert-RecipientBudget
    $logs=Join-Path $runRoot $Phase;$phaseSpec=Join-Path $runRoot ($Phase+'.json')
    $phaseParameters=@{schema='iw7.recipient-phase/1';phase=$Phase;exe=(Join-Path $work 'zonetool.exe');sha256=$plan.Candidate.SHA256;
      cwd=$work;logs=$logs;timeout=$plan.PhaseSeconds}
    if($plan.FatalTextDiagnostic){$phaseParameters['diagnostic_mode']='fatal-text'}
    $phaseParameters|ConvertTo-Json|Set-Content -LiteralPath $phaseSpec
    $guards.Add([IO.File]::Open($phaseSpec,'Open','Read','Read'))
    $arguments=ConvertTo-AnimationArguments @('-B',$plan.Adapter,'--spec',$phaseSpec,'--spec-sha256',
        (Get-FileHash -LiteralPath $phaseSpec).Hash.ToLowerInvariant(),'--sdk-phase',$bindings['sdk/modding/beacon_tool_phase.py'].Path)
    # Factory failure cannot imply closure; quarantine even if no owner returns.
    $script:closed=$false
    $script:owner=[IW7.CommunityBuild.BuildJob]::Prepare($plan.PythonExe,$arguments,$work)
    $identity=Get-BeaconJobIdentity $owner $plan.PythonExe $Phase
    $identity['PostRootExitObservations']=@();$identity['PostRootExitDrainSeconds']=$plan.RootExitDrainSeconds
    $state.Phases+=,$identity;Save-RecipientState
    $owner.Resume();$state.NativeExecuted=$null;$phaseClock=[Diagnostics.Stopwatch]::StartNew()
    $identity['ResourceRegistration']=Register-AnimationPhase $owner $lease.Token {Assert-RecipientBudget}
    Save-RecipientState
    Wait-RecipientPhase $owner $identity $plan.OuterPhaseSeconds $plan.RootExitDrainSeconds `
        {$phaseClock.Elapsed.TotalSeconds} {Assert-RecipientBudget} {Save-RecipientState}
    $identity.ExitCode=$owner.ExitCode;$identity.JobActiveAtClose=$owner.Active
    $script:closed=$true;$owner.Dispose();$script:owner=$null;Save-RecipientState
    Assert-RecipientBudget
    $receipt=Read-BeaconJson (Join-Path $logs 'phase.json')
    if($receipt.pid -gt 0){$state.NativeExecuted=$true}
    Assert-RecipientResult $receipt $Phase $identity
    $log=[IO.File]::ReadAllText((Join-Path $logs 'stdout.log'))
    $stderr=[IO.File]::ReadAllText((Join-Path $logs 'stderr.log'))
    if($stderr -match '\[ ERROR \]|\[ FATAL \]|could not be found|Could not find referenced'){throw 'Native stderr reported source-zone errors.'}
    $identity['ObservedSourceZoneOrder']=@(Assert-RecipientZoneLog $log $plan.SourceZoneOrder)
    $identity['Result']=$receipt;Save-RecipientState
}
try {
    $allPins=[ordered]@{}
    foreach($item in $bindings.Values){$allPins[$item.Path]=$item.SHA256}
    foreach($path in $plan.SourceHashes.Keys){$allPins[$path]=$plan.SourceHashes[$path]}
    $allPins[$plan.Candidate.Path]=$plan.Candidate.SHA256
    foreach($path in $allPins.Keys){$guards.Add([IO.File]::Open($path,'Open','Read','Read'));Assert-BeaconHash $path $allPins[$path]}
    . $bindings['ops/Resource-Scheduler.Core.ps1'].Path
    $leaseOwner=if($FatalTextDiagnostic){'Recipient fatal-text diagnostic'}elseif($ReferencesOnly){'Recipient references-only diagnostic'}else{'Recipient four references and compiled utility'}
    $lease=Enter-IW7ResourceLease -Scope $work -Kind Extract -PhysicalBytes $plan.PhysicalBytes -CommitBytes $plan.CommitBytes -Owner $leaseOwner
    $state.RetainedLeaseToken=$lease.Token
    Add-Type -LiteralPath $bindings['tools-source/asset-bridge/model/BuildJob.cs'].Path
    Add-Type -LiteralPath $bindings['ops/hud-lab/HudFileIdentity.cs'].Path
    $staged=@(@{Relative='zonetool.exe';Source=$plan.Candidate.Path})+@($plan.Requests)
    foreach($item in $staged){
        $file=Get-Item -LiteralPath $item.Source
        $state.Inputs+=,[pscustomobject]@{Relative=$item.Relative;Source=$file.FullName;Mode='HardLink';Bytes=$file.Length;ModifiedUtc=$file.LastWriteTimeUtc.ToString('o');Attributes=[int]$file.Attributes}
    }
    foreach($entry in $state.Inputs){
        $null=Resolve-IW7BasePath (Split-Path $entry.Source -Parent) (Split-Path $entry.Source -Leaf)
        $guards.Add([IO.File]::Open($entry.Source,'Open','Read','Read'))
        $sourceId=[IW7HudFileIdentity]::Read($entry.Source);Assert-FFStockIdentity $entry $sourceId
        $entry|Add-Member NoteProperty SourceId $sourceId
    }
    Assert-FFStockContent $state.Inputs
    Assert-ModelFFInputs $state.Inputs $work -SourceOnly
    if(Test-Path -LiteralPath $runRoot){throw 'Run directory appeared during admission; preserve it.'}
    New-Item -ItemType Directory -Path $runRoot -ErrorAction Stop|Out-Null;$created=$true
    [IO.Directory]::CreateDirectory($work)|Out-Null
    $state.Transaction=Save-IW7BaseTransaction ([pscustomobject]@{GameRoot=$work;MutableFiles=@($state.Inputs.Relative);ProfileDirectory='unused';ProfileDirectories=@()}) (Join-Path $runRoot 'backup')
    $saved=$true;Save-RecipientState
    foreach($entry in $state.Inputs){
        $target=Resolve-IW7BasePath $work $entry.Relative;[IO.Directory]::CreateDirectory((Split-Path $target))|Out-Null
        if($entry.Mode -ceq 'Copy'){Copy-Item -LiteralPath $entry.Source -Destination $target}else{New-Item -ItemType HardLink -Path $target -Target $entry.Source|Out-Null}
        $entry|Add-Member NoteProperty TargetId ([IW7HudFileIdentity]::Read($target))
        if($entry.Mode -ceq 'HardLink' -and $entry.TargetId -cne $entry.SourceId){throw 'Staged NTFS identity differs.'}
        if($entry.Mode -ceq 'Copy'){
            if($entry.TargetId -ceq $entry.SourceId){throw 'Sentinel copy aliases stock; attributes preserved.'}
            $copy=Get-Item -LiteralPath $target;if($copy.IsReadOnly){$copy.IsReadOnly=$false}
        }
    }
    Assert-ModelFFInputs $state.Inputs $work
    $state.Status='Observing';Save-RecipientState
    foreach($phase in $plan.Phases){
        Invoke-RecipientPhase $phase
        if($plan.FatalTextDiagnostic){throw 'Fatal-text diagnostic must never accept references.'}
        if($phase -ceq 'references'){$state.ReferencesVerified=$true}else{$state.ScriptBytesVerified=$true}
    }
    $state.Status=if($ReferencesOnly){'ReferencesObservedScriptNotRun'}else{'ReferenceAndScriptObservationsVerified'}
    Save-RecipientState;Measure-RecipientOutput -Final
} catch {$state.Failure=$_.Exception.Message;$state.Status=if($plan.FatalTextDiagnostic){'DiagnosticFailed'}else{'Failed'};throw}
finally {
    if($owner){
        try{
            $owner.Stop();$stopClock=[Diagnostics.Stopwatch]::StartNew()
            while(($owner.Active -ne 0 -or !$owner.Exited) -and $stopClock.Elapsed.TotalSeconds -lt 15){Start-Sleep -Milliseconds 100}
            $closed=($owner.Active -eq 0 -and $owner.Exited)
            $state['ClosureAfterStop']=@{RootExited=$owner.Exited;Active=$owner.Active;ExitCode=$(if($owner.Exited){$owner.ExitCode}else{$null})}
        }catch{$closed=$false}
        if($closed){$owner.Dispose();$owner=$null}
    }
    if(!$closed){[AppDomain]::CurrentDomain.SetData(('IW7.Recipient.Quarantine.'+$lease.Token),@{Owner=$owner;Guards=$guards;State=$state})}
    Complete-AnimationFF $state $statePath $lease $closed $saved $guards
    if($created){
        try{Save-RecipientFinalState}
        catch{$state.Status='Failed';$state.Failure=$_.Exception.Message;Save-RecipientState;throw}
    }
}

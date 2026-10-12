param(
    [Parameter(Mandatory)][string]$ParametersPath,
    [Parameter(Mandatory)][string]$ParametersSHA256,
    [Parameter(Mandatory)][string]$RunRoot,
    [switch]$Run
)
# Source/plan only by default. Exactly one compile under one4/6GiB lease on -Run.
$ErrorActionPreference='Stop'
function Write-MaterialDiagnosticLine($Stream,$Value) {
    $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($Value|ConvertTo-Json -Depth 12 -Compress)+"`n")
    if($Stream.Length+$bytes.Length -gt 2MB){throw 'Job-member diagnostic exceeded2MiB bound.'}
    $Stream.Write($bytes,0,$bytes.Length);$Stream.Flush()
}
function Read-MaterialJobObservation($Owner) {[IW7.MaterialDiagnostics.JobMembers]::Capture($Owner)}
function Save-MaterialJobObservation($Owner,$Snapshot,[string]$Point,$Stream,$State) {
    try {
        $observation=Read-MaterialJobObservation $Owner
        $row=[ordered]@{Point=$Point;Supervision=$Snapshot;Job=$observation}
        Write-MaterialDiagnosticLine $Stream $row
        $State.LastJobObservation=$row;$State.JobObservations++
    } catch {$State.DiagnosticError=$_.Exception.Message;throw}
}
$parameterFile=[IO.Path]::GetFullPath($ParametersPath)
if($ParametersSHA256 -cnotmatch '^[A-Fa-f0-9]{64}$' -or
   (Get-FileHash -Algorithm SHA256 -LiteralPath $parameterFile).Hash -ine $ParametersSHA256){throw 'Exact source parameter receipt required.'}
$parameters=Get-Content -LiteralPath $parameterFile -Raw|ConvertFrom-Json -AsHashtable
if($parameters.ContainsKey('Run')){throw 'Parameter receipt may not authorize execution.'}
$parameters.RunRoot=$RunRoot
# Invoke ONLY the existing default Plan, never its native execution branch.
$basePlan=((& "$PSScriptRoot/Build-MaterialV2.ps1" @parameters) -join "`n")|ConvertFrom-Json
$shared=$parameters.SharedRepo
. "$shared/ops/Base-Client.Core.ps1"
. "$shared/ops/Resource-Scheduler.Core.ps1"
. "$shared/sdk/modding/BeaconFF.Core.ps1"
. "$PSScriptRoot/MaterialV2.Core.ps1"
$RunRoot=$basePlan.RunRoot
$reader=Join-Path $PSScriptRoot 'MaterialV2.JobMembers.cs'
$hashes=@($basePlan.HashInputs)+@([pscustomobject]@{Path=$reader;SHA256=(Get-FileHash -LiteralPath $reader).Hash},
    [pscustomobject]@{Path=$parameterFile;SHA256=$ParametersSHA256})
$python=(Get-Command python -ErrorAction Stop).Source
if(@($hashes|Where-Object Path -IEQ $python).Count -ne 1){throw 'Exact planned Python source binding required.'}
$plan=[ordered]@{Schema='iw7.material-v2-compile-diagnostic-plan/1';RunRoot=$RunRoot;Phases=@('compile');
    PhysicalBytes=$basePlan.WriterPhysicalBytes;CommitBytes=$basePlan.WriterCommitBytes;TimeoutSeconds=240;OuterDeadlineSeconds=245;
    DrainMilliseconds=2000;CleanupMilliseconds=15000;MemberLogBytes=2MB;NativeLogBytesPerStream=2MB;NewOutputStopBytes=64MB;
    Compiler=$basePlan.Compiler;CompilerArguments=$basePlan.CompilerArguments;Python=$python;HashInputs=$hashes;
    WriterExecution=$false;FFExecution=$false;StockStaging=$false;MainChanges=$false;Ready=$false}
if(!$Run){$plan|ConvertTo-Json -Depth 25;return}
if(('IW7.CommunityBuild.BuildJob' -as [type]) -or ('IW7.MaterialDiagnostics.JobMembers' -as [type])){throw 'Fresh diagnostic PowerShell host required.'}
$state=[ordered]@{Schema='iw7.material-v2-compile-diagnostic/1';Plan=$plan;Status='Preparing';Failure=$null;
    Phase=$null;NativeReceipt=$null;JobObservations=0;LastJobObservation=$null;DiagnosticError=$null;Cleanup=$null;
    JobClosureVerified=$false;SourceHashesUnchanged=$false;RetainedLeaseToken=$null;LeaseReleased=$false;FFExecuted=$false;StockTouched=$false;Ready=$false}
$writerRoot=Join-Path $RunRoot 'writer';$statePath=Join-Path $RunRoot 'state.local.json'
$lease=$null;$owner=$null;$memberStream=$null;$closed=$true;$guards=[Collections.Generic.List[IDisposable]]::new()
function Save-DiagnosticState {if(Test-Path -LiteralPath $RunRoot){$state|ConvertTo-Json -Depth 25|Set-Content -LiteralPath $statePath -Encoding utf8}}
function Assert-DiagnosticOutputs {
    $bytes=[long](@(Get-ChildItem -LiteralPath $RunRoot -File -Recurse -Force)|Measure-Object Length -Sum).Sum
    Assert-BeaconOutputBudget $bytes;$state.OutputBytes=$bytes
}
try {
    $lease=Enter-IW7ResourceLease -Scope $writerRoot -Kind Build -PhysicalBytes $plan.PhysicalBytes -CommitBytes $plan.CommitBytes -Owner 'Material compile-only member identity diagnostic'
    $state.RetainedLeaseToken=$lease.Token
    [IO.Directory]::CreateDirectory($writerRoot)|Out-Null
    foreach($entry in $hashes){$guards.Add([IO.File]::Open($entry.Path,'Open','Read','Read'));Assert-BeaconHash $entry.Path $entry.SHA256}
    Add-Type -LiteralPath "$shared/tools-source/asset-bridge/model/BuildJob.cs"
    Add-Type -LiteralPath $reader
    $memberStream=[IO.File]::Open((Join-Path $RunRoot 'job-members.jsonl'),'CreateNew','Write','Read')
    $compilerHash=(Get-FileHash -LiteralPath $plan.Compiler).Hash
    $logs=Join-Path $RunRoot 'compile';$specPath=Join-Path $RunRoot 'compile-spec.json'
    $spec=[ordered]@{schema='iw7.material-v2-phase/1';phase='compile';exe=$plan.Compiler;sha256=$compilerHash;
        arguments=@($plan.CompilerArguments);cwd=$writerRoot;logs=$logs;timeout=240}
    $spec|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $specPath -Encoding utf8
    $guards.Add([IO.File]::Open($specPath,'Open','Read','Read'));$specHash=(Get-FileHash -LiteralPath $specPath).Hash
    $argsText=ConvertTo-MaterialV2Arguments @('-B',(Join-Path $PSScriptRoot 'material_v2_phase.py'),'--spec',$specPath,
        '--spec-sha256',$specHash,'--sdk-phase',(Join-Path $shared 'sdk/modding/beacon_tool_phase.py'))
    $owner=[IW7.CommunityBuild.BuildJob]::Prepare($python,$argsText,$writerRoot);$closed=$false
    $identity=Get-BeaconJobIdentity $owner $python 'compile';$state.Phase=$identity
    $identity.SpecSHA256=$specHash;$identity.NativeExecutableSHA256=$compilerHash
    Save-MaterialJobObservation $owner $null 'SuspendedBeforeResume' $memberStream $state
    Save-DiagnosticState
    $started=Start-MaterialV2OwnedPhase $owner $lease.Token
    $identity.StartedUtc=$started.StartedUtc;$identity.SchedulerAttached=$started.SchedulerAttached
    Wait-MaterialV2OwnedPhase $owner $identity $started.StartedMonotonicMs 240 {
        param($snapshot,$changed)
        Save-MaterialJobObservation $owner $snapshot 'SupervisionPoll' $memberStream $state
        if($changed){Save-DiagnosticState}
        if(Test-Path -LiteralPath (Join-Path $RunRoot 'stop.request')){throw 'Coordinator requested owned stop.'}
        Assert-DiagnosticOutputs
        $memory=Get-IW7ResourceSnapshot;if($memory.Committed -gt $memory.CommitLimit*0.85){throw 'Commit pressure exceeded85 percent.'}
    }
    $closed=$true;$owner.Dispose();$owner=$null
    $state.NativeReceipt=Read-BeaconJson (Join-Path $logs 'phase.json')
    Assert-MaterialV2PhaseResult $state.NativeReceipt 'compile' $compilerHash $identity
    $state.Status='CompileClosed';Save-DiagnosticState
} catch {$state.Status='Failed';$state.Failure=$_.Exception.Message;throw}
finally {
    if($owner){
        # The last live observation was already taken on the final poll, inside
        # the unchanged deadline. Do not delay exact Stop with another scan.
        $state.Cleanup=[ordered]@{};$closed=Stop-MaterialV2OwnedPhase $owner $state.Cleanup
        $owner.Dispose()
    }
    if($memberStream){$memberStream.Dispose()}
    $state.JobClosureVerified=$closed;$state.SourceHashesUnchanged=$true
    foreach($entry in $hashes){try{Assert-BeaconHash $entry.Path $entry.SHA256}catch{$state.SourceHashesUnchanged=$false;$state.DiagnosticError=$_.Exception.Message}}
    if($closed){foreach($guard in $guards){$guard.Dispose()}}
    if(Test-Path -LiteralPath (Join-Path $RunRoot 'compile/phase.json')){
        try{$state.NativeReceipt=Read-BeaconJson (Join-Path $RunRoot 'compile/phase.json')}catch{$state.DiagnosticError=$_.Exception.Message}
    }
    Save-DiagnosticState
    if($lease -and $closed -and $state.SourceHashesUnchanged){Exit-IW7ResourceLease -Token $lease.Token;$state.RetainedLeaseToken=$null;$state.LeaseReleased=$true}
    Save-DiagnosticState
    if(Test-Path -LiteralPath $RunRoot){
        try{Assert-DiagnosticOutputs;Save-DiagnosticState;Assert-DiagnosticOutputs}
        catch{$state.Status='Failed';$state.Failure=$_.Exception.Message;Save-DiagnosticState;throw}
    }
}
if(!$state.JobClosureVerified -or !$state.SourceHashesUnchanged -or !$state.LeaseReleased -or $state.RetainedLeaseToken){
    $state.Status='Failed';$state.Failure='Diagnostic cleanup/source proof incomplete; preserve reservation and evidence.'
    Save-DiagnosticState;throw $state.Failure
}
$state|ConvertTo-Json -Depth 25

param(
    [Parameter(Mandatory)][string]$PlanPath,
    [Parameter(Mandatory)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$PlanSHA256,
    [switch]$Run
)
$ErrorActionPreference='Stop'
$entryGuards=[Collections.Generic.List[IDisposable]]::new()
try {
$entryGuards.Add([IO.File]::Open($PlanPath,'Open','Read','Read'))
$planFile=Get-Item -LiteralPath $PlanPath
if($planFile.Length -gt 128KB -or (Get-FileHash -LiteralPath $PlanPath).Hash -ine $PlanSHA256){throw 'Bounded hash-bound locator Plan required.'}
$plan=[IO.File]::ReadAllText($PlanPath)|ConvertFrom-Json
$core=Join-Path $PSScriptRoot 'Locator.Supervisor.Core.ps1'
$entryGuards.Add([IO.File]::Open($core,'Open','Read','Read'))
$corePin=@($plan.Sources|Where-Object Relative -CEQ 'Locator.Supervisor.Core.ps1')
if($corePin.Count -ne 1 -or (Get-FileHash -LiteralPath $core).Hash -ine $corePin[0].SHA256){throw 'Locator supervisor source binding differs.'}
. $core
Assert-LocatorPath $PlanPath;Assert-LocatorPath $plan.ProviderRoot;Assert-LocatorPath $plan.RunRoot
$repo=$PSScriptRoot;foreach($step in 1..5){$repo=Split-Path $repo -Parent}
$runtime=Join-Path $repo 'runtime'
$targeted=$plan.Schema -ceq 'iw7.rig-locator-supervisor-plan/2'
if($plan.Schema -cnotin 'iw7.rig-locator-supervisor-plan/1','iw7.rig-locator-supervisor-plan/2' -or $plan.PhysicalBytes -ne 1GB -or $plan.CommitBytes -ne 2GB -or
   $plan.DeadlineSeconds -ne 60 -or $plan.MaximumOutputBytes -ne 4MB -or
   !$plan.RunRoot.StartsWith($runtime+'\',[StringComparison]::OrdinalIgnoreCase) -or
   (Split-Path $plan.RunRoot -Parent) -ine $runtime -or (Test-Path -LiteralPath $plan.RunRoot)) {throw 'Fixed fresh locator scope/budget required.'}
if($targeted){Assert-LocatorTargetedPlan $plan}
if($plan.Python.SHA256 -cne '4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a' -or
   $plan.JobSource.SHA256 -cne 'f6be2a4cafddb78b5e07a6802354575ada418cb7643d96a3abd0a4c063bc6387'){throw 'Pinned Python and original F6 job required.'}
$pins=[Collections.Generic.List[object]]::new()
$scriptName=if($targeted){'locate_targeted.py'}else{'locate_static.py'}
$expected=@('Locator.Supervisor.Core.ps1','Run-Locator.ps1',$scriptName)
if(@($plan.Sources).Count -ne 3 -or @($plan.Sources.Relative|Sort-Object -Unique).Count -ne 3){throw 'Exact supervisor source inventory required.'}
foreach($source in $plan.Sources){
    if($source.Relative -cnotin $expected){throw 'Unexpected locator source.'}
    $pin=[pscustomobject]@{Path=Join-Path $PSScriptRoot $source.Relative;SHA256=$source.SHA256;Bytes=$source.Bytes}
    Assert-LocatorPin $pin;$pins.Add($pin)
}
$plan|Add-Member NoteProperty Script (Join-Path $PSScriptRoot $scriptName)
foreach($pin in @($plan.Python,$plan.JobSource)+@(Get-LocatorProviders $plan.ProviderRoot)){Assert-LocatorPin $pin;$pins.Add($pin)}
$pins.Add([pscustomobject]@{Path=$PlanPath;SHA256=$PlanSHA256.ToLowerInvariant();Bytes=$planFile.Length})
$referencePins=@{text=@(21135360,'5f2953f04a8d5f2a53d1e5a5e076de8f29d5b5303ca652f2420fec8d2a6a9138');
    rdata=@(3194880,'28b66189c1f35442d3e32ea5077e785e7cb8fbf45ed420094dc6b2795afd04e5');
    pdata=@(832608,'8ff97607018c0c531a9d6851282701074a50b141729060f9f23ae728c9fad41e')}
foreach($name in $referencePins.Keys){
    $pin=$plan.References.$name
    if($pin.Bytes -ne $referencePins[$name][0] -or $pin.SHA256 -cne $referencePins[$name][1]){throw 'Exact retained references required.'}
    Assert-LocatorPin $pin -MetadataOnly
}
if(@($plan.RuntimeFiles).Count -lt 4 -or @($plan.RuntimeFiles).Count -gt 128 -or
   [long](($plan.RuntimeFiles|Measure-Object Bytes -Sum).Sum) -gt 32MB){throw 'Bounded interpreter/runtime pins required.'}
foreach($pin in $plan.RuntimeFiles){Assert-LocatorPin $pin -MetadataOnly}
if((@($plan.RuntimeFiles.Path|Sort-Object) -join "`n") -cne ((Get-LocatorRuntimePaths $plan.Python.Path) -join "`n")){throw 'Exact Python DLL/Capstone source inventory required.'}
$guardedBytes=[long](($pins|ForEach-Object {(Get-Item -LiteralPath $_.Path).Length}|Measure-Object -Sum).Sum)+
    [long](($plan.RuntimeFiles|Measure-Object Bytes -Sum).Sum)+25162848L
if($guardedBytes -gt 48MB){throw 'Locator guarded input budget exceeded.'}
$arguments=Get-LocatorArguments $plan
if(!$Run){
    [ordered]@{Schema='iw7.rig-locator-executor-plan/1';PlanSHA256=$PlanSHA256;RunRoot=$plan.RunRoot;Targeted=$targeted;
        Entry=$(if($targeted){$plan.Entry}else{$null});TargetedLimits=$(if($targeted){$plan.TargetedLimits}else{$null});
        Python=$plan.Python;Arguments=$arguments;SourcePins=$pins;RuntimePins=$plan.RuntimeFiles;References=$plan.References;
        PhysicalBytes=1GB;CommitBytes=2GB;DeadlineSeconds=60;MaximumOutputBytes=4MB;
        GuardedBytes=$guardedBytes;MaximumKnownContentReadsBytes=128MB;
        NativeTypesLoaded=$false;LeaseAcquired=$false;ReferenceContentRead=$false;RuntimeHashesPending=$true;ExecutionVerified=$false}|ConvertTo-Json -Depth 8
    return
}
foreach($name in 'IW7.CommunityBuild.BuildJob','IW7HudFileIdentity','IW7ResourceMemoryV1'){
    if($name -as [type]){throw 'Fresh source-bound PowerShell host required.'}
}
$context=@{Owner=$null;Closed=$true;Lease=$null;Guards=[Collections.Generic.List[IDisposable]]::new();Baselines=[Collections.Generic.List[object]]::new()}
$state=[ordered]@{Schema='iw7.rig-locator-supervised-run/1';PlanSHA256=$PlanSHA256;Status='Preparing';Failure=$null;CleanupError=$null;
    RetainedLeaseToken=$null;Closed=$false;Quarantined=$false;SourcesUnchanged=$false;StopRequested=$false;Registration=$null;RegistrationError=$null;
    Admission=$null;Identity=$null;Closure=$null;StartedMonotonicMs=$null;ElapsedMs=$null;MaxObservedBytes=0L;FinalObservedBytes=$null;
    FirstWriterEstablished=$false;LiveBreakpointEstablished=$false;GameOrZoneToolLaunched=$false;Report=$null;
    Targeted=$targeted;Entry=$(if($targeted){$plan.Entry}else{$null})}
$created=$false
try {
    foreach($pin in $pins){Add-LocatorGuard $pin $context}
    . (Join-Path $plan.ProviderRoot 'ops/Resource-Scheduler.Core.ps1')
    $context.Lease=Enter-IW7ResourceLease -Scope $plan.RunRoot -Kind Analysis -PhysicalBytes 1GB -CommitBytes 2GB -Owner 'bounded rig first-write locator'
    $state.RetainedLeaseToken=$context.Lease.Token
    $state.Admission=$context.Lease|Select-Object Token,Kind,Scope,CreatedUtc,PhysicalBytes,CommitBytes,OwnerIdentity
    $null=New-Item -ItemType Directory -Path $plan.RunRoot -ErrorAction Stop;$created=$true
    Save-LocatorState $state $plan.RunRoot
    Add-Type -Path (Join-Path $plan.ProviderRoot 'ops/hud-lab/HudFileIdentity.cs')
    Add-Type -Path $plan.JobSource.Path
    foreach($pin in @($plan.RuntimeFiles)+@($plan.References.PSObject.Properties.Value)){Add-LocatorGuard $pin $context}
    Set-LocatorGuardIds $context
    $state.Status='Running';Save-LocatorState $state $plan.RunRoot
    Invoke-LocatorOwnedProcess $plan $state $context
    $reportPath=Join-Path $plan.RunRoot 'report.local.json'
    if(!(Test-Path -LiteralPath $reportPath) -or (Get-Item -LiteralPath $reportPath).Length -gt 3MB){throw 'Bounded locator report missing.'}
    $report=[IO.File]::ReadAllText($reportPath)|ConvertFrom-Json
    Assert-LocatorReport $report -Targeted $targeted
    $state.Report=[ordered]@{Bytes=(Get-Item -LiteralPath $reportPath).Length;SHA256=(Get-FileHash -LiteralPath $reportPath).Hash;Status=$report.status}
    $state.Status='CandidateRouteNeedsReview'
}catch{$state.Failure=$_.Exception.Message;$state.Status='Failed'}
finally {
    Complete-LocatorOwnership $state $context
    if($created){
        try{Save-LocatorFinalCounters $state $plan.RunRoot}catch{$state.Status='Failed';$state.CleanupError=$_.Exception.Message;Save-LocatorState $state $plan.RunRoot}
    }
}
$state|ConvertTo-Json -Depth 12
if($state.Failure -or $state.CleanupError -or $state.Quarantined -or !$state.Closed){throw 'Locator failed or quarantined; preserve original state and ownership evidence.'}
}finally{foreach($entryGuard in $entryGuards){$entryGuard.Dispose()}}

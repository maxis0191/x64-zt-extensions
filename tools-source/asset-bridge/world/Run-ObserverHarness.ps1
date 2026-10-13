[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$RunRoot,
    [Parameter(Mandatory)][string]$VCToolsRoot,
    [Parameter(Mandatory)][string]$WindowsSdkRoot,
    [string]$WindowsSdkVersion='10.0.26100.0',
    [Parameter(Mandatory)][string]$PythonExe,
    [string]$ProviderRoot=([IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))),
    [Parameter(Mandatory)][string]$StageProviderRoot,
    [Parameter(Mandatory)][string]$LinkProfilePath,
    [Parameter(Mandatory)][string]$NativeJobAssembly,
    [string]$PlanSHA256,
    [switch]$Run
)
# Default Plan is inert. -Run requires this exact Plan hash AND coordinated GO.
# Reuse qualified H1/T7 providers in place; never build/copy the native owner.
$ErrorActionPreference='Stop'
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$manifestPath=Join-Path $PSScriptRoot 'observer-harness-plan.json'
if((Get-Item -LiteralPath $manifestPath).Length -gt 64KB){throw 'Bounded World manifest required.'}
$manifest=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
if($manifest.schema -cne 'iw7.world-clipmap-harness-plan/3'){throw 'World stage plan v3 required.'}
$guards=[Collections.Generic.List[IDisposable]]::new();$entries=[Collections.Generic.List[object]]::new()
$context=[pscustomobject]@{Owner=$null;Closed=$true;Lease=$null;Guards=$guards}
$state=$null;$stageState=$null;$failure=$null;$created=$false;$intact=$true
function Add-WorldBinding([string]$Path,[string]$Expected) {
    $Path=[IO.Path]::GetFullPath($Path)
    $guard=[IO.File]::Open($Path,'Open','Read','Read');$guards.Add($guard)
    if($guard.Length -le 0 -or $guard.Length -gt 64MB){throw 'Bounded World input required.'}
    $hash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($guard)).ToLowerInvariant()
    if($Expected -and $hash -cne $Expected.ToLowerInvariant()){throw "World binding changed: $([IO.Path]::GetFileName($Path))"}
    $entries.Add([pscustomobject]@{Path=$Path;SHA256=$hash;Bytes=$guard.Length})
}
try {
    foreach($group in 'provider_sha256','stage_provider_sha256','source_sha256') {
        $root=switch($group){'provider_sha256'{$ProviderRoot};'stage_provider_sha256'{$StageProviderRoot};default{$repo}}
        foreach($entry in $manifest.$group.PSObject.Properties) {
            if($entry.Name -match '(^|/)\.\.(/|$)|[:\\]' -or [IO.Path]::IsPathRooted($entry.Name)){throw 'Relative manifest path required.'}
            Add-WorldBinding (Join-Path $root $entry.Name) $entry.Value
        }
    }
    Add-WorldBinding $manifestPath ''
    Add-WorldBinding $LinkProfilePath $manifest.link_profile_sha256
    Add-WorldBinding $NativeJobAssembly $manifest.native_job_sha256
    foreach($relative in 'ops/Base-Client.Core.ps1','sdk/modding/BeaconFF.Core.ps1','tools-source/asset-bridge/surfaces/MaterialV2.Compiler.ps1') {
        if($relative -cnotin $manifest.provider_sha256.PSObject.Properties.Name){throw 'Required World provider pin missing.'}
        . (Join-Path $ProviderRoot $relative)
    }
    . "$PSScriptRoot/ObserverHarness.Core.ps1"
    foreach($relative in 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1','tools-source/asset-bridge/h1-fixture/H1Native.Compiler.ps1') {
        if($relative -cnotin $manifest.stage_provider_sha256.PSObject.Properties.Name){throw 'Required H1 source pin missing.'}
        . (Join-Path $StageProviderRoot $relative)
    }
    . $LinkProfilePath
    . "$PSScriptRoot/ObserverStages.Profile.ps1"
    foreach($relative in 'ops/Resource-Scheduler.Core.ps1','ops/Resource-Memory.ps1','ops/Resource-RecorderOwnedProcess.Core.ps1','ops/native/ResourceMemory.cs') {
        if($relative -cnotin $manifest.provider_sha256.PSObject.Properties.Name){throw 'Required scheduler/transitive pin missing.'}
    }
    if('tools-source/asset-bridge/h1-fixture/H1Native.JobMembers.cs' -cnotin $manifest.stage_provider_sha256.PSObject.Properties.Name){throw 'H1 observer pin missing.'}
    foreach($name in 'Run-ObserverHarness.ps1','ObserverHarness.Core.ps1','ObserverStages.Profile.ps1','check_observer_harness.py','test_world_clipmap_observer.cpp','world_clipmap_observer.hpp') {
        if(('tools-source/asset-bridge/world/'+$name) -cnotin $manifest.source_sha256.PSObject.Properties.Name){throw 'World source pin missing.'}
    }
    foreach($entry in $entries){Assert-H1Path $entry.Path}
    Assert-WorldObserverPins $entries
    $RunRoot=Resolve-WorldObserverPath $RunRoot
    $runtime=[IO.Path]::GetFullPath((Join-Path $repo 'runtime'))
    if([IO.Path]::GetDirectoryName($RunRoot) -ine $runtime -or (Test-Path -LiteralPath $RunRoot)){throw 'Fresh directory directly under owned runtime required.'}
    $VCToolsRoot=Resolve-WorldObserverPath $VCToolsRoot;$WindowsSdkRoot=Resolve-WorldObserverPath $WindowsSdkRoot
    $PythonExe=Resolve-WorldObserverPath $PythonExe
    $compiler=Resolve-WorldObserverPath (Join-Path $VCToolsRoot 'bin/Hostx64/x64/cl.exe')
    $policy=Get-MaterialV2CompilerPolicy $compiler
    $link=Join-Path (Split-Path $compiler -Parent) 'link.exe'
    Add-WorldBinding $compiler $policy.CompilerSHA256
    Add-WorldBinding $policy.Telemetry $policy.TelemetrySHA256
    Add-WorldBinding $link 'a364af801a8539e4324d9489313dbf001d959128451fc99a27b24676bbac058f'
    Add-WorldBinding $PythonExe ''
    $arguments=@(Get-WorldObserverCompilerArguments $VCToolsRoot $WindowsSdkRoot $WindowsSdkVersion $PSScriptRoot $RunRoot)
    $stages=@(Get-WorldStages $compiler $PythonExe $arguments $PSScriptRoot $RunRoot)
    $environment=[ordered]@{}
    foreach($key in 'SystemRoot','windir','SystemDrive','COMSPEC','USERPROFILE','LOCALAPPDATA','APPDATA') {
        $value=[Environment]::GetEnvironmentVariable($key)
        if($value){$environment[$key]=$value}
    }
    $environment.PATH=@((Split-Path $compiler -Parent),(Split-Path $PythonExe -Parent),[Environment]::SystemDirectory,$env:SystemRoot)-join ';'
    $plan=[pscustomobject]@{Schema='iw7.world-observer-execution-plan/2';Mode='Plan';RunRoot=$RunRoot;
        Compiler=$compiler;Bindings=$entries.ToArray();Stages=$stages;Environment=[pscustomobject]$environment;
        NativeJobAssembly=[IO.Path]::GetFullPath($NativeJobAssembly);OutputContract=(Get-WorldStageContract);
        PhysicalBytes=4GB;CommitBytes=6GB;OutputLimitBytes=64MB;MetadataReserveBytes=1MB;
        GroupDeadlineSeconds=120;OriginalJobs=4;NativeParallelism=1;ToolchainFullyHermetic=$false;
        SyntheticOnly=$true;EngineObserved=$false;HeavyExecutionAuthorizedByPlan=$false}
    $json=$plan|ConvertTo-Json -Depth 20
    $actualPlanHash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($json))).ToLowerInvariant()
    if(!$Run){[ordered]@{PlanSHA256=$actualPlanHash;Plan=$plan}|ConvertTo-Json -Depth 22;return}
    if($PlanSHA256 -cne $actualPlanHash){throw 'Exact reviewed World Plan SHA256 required before admission.'}
    if(!$IsWindows -or [IntPtr]::Size -ne 8 -or $PSVersionTable.PSVersion.Major -lt 7){throw 'Fresh Windows x64 PowerShell7 required.'}
    foreach($type in 'IW7.AnimationProbe.NativeJob','IW7.H1Diagnostics.JobMembers','IW7ResourceMemoryV1') {
        if($type -as [type]){throw 'Fresh host required for source-bound native helpers.'}
    }
    . "$ProviderRoot/ops/Resource-Scheduler.Core.ps1"
    $context.Lease=Enter-IW7ResourceLease -Scope $RunRoot -Kind Build -PhysicalBytes 4GB -CommitBytes 6GB -Owner 'World original CLIPMAP observer fixture'
    $script:WorldGroupStarted=Get-H1Clock
    $state=[ordered]@{Schema='iw7.world-observer-run/2';Plan=$plan;PlanSHA256=$actualPlanHash;Status='Preparing';
        RetainedLeaseToken=$context.Lease.Token;NativeCompiled=$false;NativeHarnessPassed=$false;EngineObserved=$false;
        JobClosureVerified=$true;SourceHashesUnchanged=$false;LeaseReleased=$false;LeaseReleaseState='NotAttempted';
        Stages=[Collections.Generic.List[object]]::new();FinalBytes=$null;Failure=$null}
    if(Test-Path -LiteralPath $RunRoot){throw 'Output appeared during admission.'}
    $null=Resolve-WorldObserverPath $RunRoot
    [IO.Directory]::CreateDirectory($RunRoot)|Out-Null;$created=$true
    Assert-H1Deadline $script:WorldGroupStarted 120
    [Reflection.Assembly]::LoadFrom($plan.NativeJobAssembly)|Out-Null
    Assert-H1Deadline $script:WorldGroupStarted 120
    Add-Type -LiteralPath (Join-Path $StageProviderRoot 'tools-source/asset-bridge/h1-fixture/H1Native.JobMembers.cs')
    Assert-H1Deadline $script:WorldGroupStarted 120
    $buildStarted=Get-H1Clock;$fixturePin=$null
    foreach($stage in $stages) {
        if(!$context.Closed){throw 'Previous World original job not closed.'}
        $script:WorldCurrentStage=$stage
        $stageRoot=Join-Path $RunRoot $stage.Name
        [IO.Directory]::CreateDirectory($stageRoot)|Out-Null
        $stageState=[ordered]@{Name=$stage.Name;Stage=$stage.Stage;PlanSHA256=$actualPlanHash;DeadlineSeconds=$stage.DeadlineSeconds;
            MaxObservedOutputBytes=0L;MaxObservedStreamBytes=0L;TreeClosureConfirmed=$false;TerminationRequested=$false;
            CompilerTelemetry=[ordered]@{Completed=$false;Action=$null}}
        $state.Stages.Add($stageState)
        $started=if($stage.Stage -in 'Compile','Link'){$buildStarted}else{Get-H1Clock}
        $pins=@(if($stage.Stage -ceq 'Fixture'){$state.Stages[1].Artifacts|Where-Object Path -CEQ $stage.Image}else{$entries|Where-Object Path -CEQ $stage.Image})
        if($pins.Count -ne 1){throw 'Exact stage executable pin required.'}
        $start=New-T7Start $plan $stage $stageRoot
        Invoke-WorldStage $plan $stageState $context $start $pins[0].SHA256 $stageRoot $started
        $stageState.Artifacts=@(Get-H1CompilerArtifacts $plan $context)
        if($stageState.CompilerTelemetry.Completed) {
            foreach($prior in $stageState.CompilerTelemetry.Artifacts) {
                $now=@($stageState.Artifacts|Where-Object Path -CEQ $prior.Path)
                if($now.Count -ne 1 -or $now[0].SHA256 -cne $prior.SHA256 -or $now[0].Bytes -ne $prior.Bytes){throw 'World artifact changed across tool cleanup.'}
            }
        }
        foreach($pin in $stageState.Artifacts){$entries.Add($pin)}
        if($stage.Stage -ceq 'Link'){$state.NativeCompiled=$true}
        if($stage.Stage -ceq 'Fixture'){$fixturePin=Assert-WorldFixtureOutput $plan $context;$entries.Add($fixturePin)}
        if($stage.Stage -ceq 'Check') {
            if((Get-Item -LiteralPath (Join-Path $stageRoot 'stderr.log')).Length -ne 0){throw 'Independent World reader stderr must be empty.'}
            $checked=Read-H1SmallJson (Join-Path $stageRoot 'stdout.log') 4KB
            if($checked.schema -cne 'iw7.world-clipmap-harness-check/1' -or $checked.status -cne 'synthetic-transcript-checked' -or
                $checked.engine_observed -isnot [bool] -or $checked.engine_observed -or $checked.records -ne 24 -or
                $checked.transcript_sha256 -cne $fixturePin.SHA256 -or $checked.transcript_bytes -ne $fixturePin.Bytes){throw 'Exact independent World transcript result required.'}
            $state.Checked=$checked
        }
        Test-H1Budget $plan $stageState
        Assert-H1Deadline $started $stage.DeadlineSeconds
    }
    Assert-WorldObserverPins $entries
    Assert-H1Deadline $script:WorldGroupStarted 120
    $state.NativeHarnessPassed=$true;$state.Status='SyntheticHarnessPassed'
}catch{$failure=$_;if($state){$state.Failure=$_.Exception.Message;$state.Status='Failed'}}
finally {
    if(!$context.Closed -and $stageState -and !$stageState.TerminationRequested){Stop-WorldStageOnFailure $context $stageState}
    try{if(Get-Command Assert-WorldObserverPins -ErrorAction SilentlyContinue){Assert-WorldObserverPins $entries}}catch{$intact=$false;if(!$failure){$failure=$_}}
    if($state){$state.SourceHashesUnchanged=$intact;$state.JobClosureVerified=$context.Closed}
    if($context.Lease -and $created -and $state) {
        try {
            if($failure){$state.Status='Failed';$state.Failure=$failure.Exception.Message}
            Complete-WorldObserverReservation $RunRoot $state $context.Lease $guards -BeforeReleaseCheck {
                if(!$failure){Assert-H1Deadline $script:WorldGroupStarted 120}
            }
            if(!$failure){Assert-H1Deadline $script:WorldGroupStarted 120}
        }catch{if(!$failure){$failure=$_};$state.Status='Failed';$state.Failure=$_.Exception.Message}
    }
    if(!$context.Lease -or ($state -and $state.LeaseReleased)){foreach($guard in $guards){$guard.Dispose()}}
    else{[AppDomain]::CurrentDomain.SetData(('IW7.WorldHarness.Quarantine.'+$context.Lease.Token),@{Context=$context;State=$state;Failure=$failure})}
}
if($failure){
    if($context.Lease -and (!$state -or !$state.LeaseReleased)) {
        $releaseState=if($state){$state.LeaseReleaseState}else{'NotAttempted'}
        $detail=if($state -and $state.Contains('FinalizationFailure') -and $state.FinalizationFailure){' Finalization: '+$state.FinalizationFailure}else{''}
        throw "World failed; lease release $releaseState; retain host and reconcile token $($context.Lease.Token). $($failure.Exception.Message)$detail"
    }
    throw $failure
}
if(!$context.Closed -or !$intact -or !$state.LeaseReleased){throw 'World closure/source/release proof incomplete; retain host for reconciliation.'}
$state|ConvertTo-Json -Depth 22

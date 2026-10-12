[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$RunRoot,
    [Parameter(Mandatory)][string]$VCToolsRoot,
    [Parameter(Mandatory)][string]$WindowsSdkRoot,
    [string]$WindowsSdkVersion='10.0.26100.0',
    [Parameter(Mandatory)][string]$PythonExe,
    [string]$ProviderRoot=([IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))),
    [switch]$Run
)
# Default Plan: reads/hashes/imports pure functions only; no output tree, child,
# lease, resource snapshot, Add-Type or native API call. -Run needs later GO.
$ErrorActionPreference='Stop'
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$manifestPath=Join-Path $PSScriptRoot 'observer-harness-plan.json'
if((Get-Item -LiteralPath $manifestPath).Length -gt 64KB){throw 'Bounded world manifest required.'}
$manifest=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
if($manifest.schema -cne 'iw7.world-clipmap-harness-plan/2'){throw 'Executable world plan v2 required.'}
$guards=[Collections.Generic.List[IDisposable]]::new();$entries=[Collections.Generic.List[object]]::new()
$lease=$null;$owner=$null;$closed=$true;$intact=$true;$state=$null;$failure=$null;$created=$false
try {
    # Bind ALL imports, including the resource helper's transitive source files.
    foreach($group in 'provider_sha256','source_sha256'){
        $root=if($group -ceq 'provider_sha256'){$ProviderRoot}else{$repo}
        foreach($entry in $manifest.$group.PSObject.Properties){
            if($entry.Name -match '(^|/)\.\.(/|$)|[:\\]' -or [IO.Path]::IsPathRooted($entry.Name)){throw 'Relative manifest path required.'}
            $path=[IO.Path]::GetFullPath((Join-Path $root $entry.Name))
            $guards.Add([IO.File]::Open($path,'Open','Read','Read'))
            if($entry.Value -cnotmatch '^[a-f0-9]{64}$' -or (Get-FileHash -LiteralPath $path).Hash -ine $entry.Value){throw "World source/provider pin differs: $($entry.Name)"}
            $entries.Add([pscustomobject]@{Path=$path;SHA256=$entry.Value})
        }
    }
    $guards.Add([IO.File]::Open($manifestPath,'Open','Read','Read'))
    $entries.Add([pscustomobject]@{Path=$manifestPath;SHA256=(Get-FileHash -LiteralPath $manifestPath).Hash})
    foreach($relative in @('ops/Base-Client.Core.ps1','sdk/modding/BeaconFF.Core.ps1',
        'tools-source/asset-bridge/surfaces/MaterialV2.Core.ps1','tools-source/asset-bridge/surfaces/MaterialV2.Compiler.ps1')){
        if($relative -cnotin $manifest.provider_sha256.PSObject.Properties.Name){throw 'Required import pin missing.'}
        . (Join-Path $ProviderRoot $relative)
    }
    if('tools-source/asset-bridge/world/ObserverHarness.Core.ps1' -cnotin $manifest.source_sha256.PSObject.Properties.Name){throw 'World core pin missing.'}
    . "$PSScriptRoot/ObserverHarness.Core.ps1"
    foreach($relative in @('ops/Resource-Scheduler.Core.ps1','ops/Resource-Memory.ps1',
        'ops/Resource-RecorderOwnedProcess.Core.ps1','ops/native/ResourceMemory.cs',
        'tools-source/asset-bridge/model/BuildJob.cs','tools-source/asset-bridge/surfaces/MaterialV2.JobMembers.cs',
        'sdk/modding/beacon_tool_phase.py')){
        if($relative -cnotin $manifest.provider_sha256.PSObject.Properties.Name){throw 'Required native/transitive provider pin missing.'}
    }
    foreach($name in 'Run-ObserverHarness.ps1','observer_harness_driver.py','check_observer_harness.py',
        'test_world_clipmap_observer.cpp','world_clipmap_observer.hpp'){
        if(('tools-source/asset-bridge/world/'+$name) -cnotin $manifest.source_sha256.PSObject.Properties.Name){throw 'Required world source pin missing.'}
    }
    Assert-WorldObserverPins $entries
    $RunRoot=Resolve-WorldObserverPath $RunRoot
    $runtime=[IO.Path]::GetFullPath((Join-Path $repo 'runtime'))+[IO.Path]::DirectorySeparatorChar
    if(!$RunRoot.StartsWith($runtime,[StringComparison]::OrdinalIgnoreCase) -or (Test-Path -LiteralPath $RunRoot)){throw 'Fresh runtime directory within this worktree required.'}
    $VCToolsRoot=Resolve-WorldObserverPath $VCToolsRoot;$WindowsSdkRoot=Resolve-WorldObserverPath $WindowsSdkRoot
    $PythonExe=Resolve-WorldObserverPath $PythonExe
    $compiler=Resolve-WorldObserverPath (Join-Path $VCToolsRoot 'bin/Hostx64/x64/cl.exe')
    $policy=Get-MaterialV2CompilerPolicy $compiler
    Assert-BeaconHash $compiler $policy.CompilerSHA256
    $null=Resolve-WorldObserverPath $policy.Telemetry;Assert-BeaconHash $policy.Telemetry $policy.TelemetrySHA256
    foreach($path in @($compiler,$policy.Telemetry,$PythonExe)){
        $file=Get-Item -LiteralPath $path
        if($file.PSIsContainer -or $file.Length -lt 1 -or $file.Length -gt 32MB){throw 'Bounded installed native tool required.'}
        $guards.Add([IO.File]::Open($path,'Open','Read','Read'))
        $entries.Add([pscustomobject]@{Path=$path;SHA256=(Get-FileHash -LiteralPath $path).Hash})
    }
    $arguments=@(Get-WorldObserverCompilerArguments $VCToolsRoot $WindowsSdkRoot $WindowsSdkVersion $PSScriptRoot $RunRoot)
    $b=Get-WorldObserverBudgets
    $plan=[ordered]@{Schema='iw7.world-observer-execution-plan/1';Mode=$(if($Run){'Run'}else{'Plan'});
        RunRoot=$RunRoot;Compiler=$compiler;CompilerArguments=$arguments;CompilerPolicy=$policy;PythonExe=$PythonExe;
        SourceAndProviderPins=$entries.ToArray();Budgets=$b;OriginalJobs=1;NativeParallelism=1;
        Fixture=Join-Path $RunRoot 'observer.exe';Driver=Join-Path $PSScriptRoot 'observer_harness_driver.py';
        SyntheticOnly=$true;EngineObserved=$false;HeavyExecutionAuthorizedByPlan=$false}
    if(!$Run){$plan|ConvertTo-Json -Depth 15;return}
    if(!$IsWindows -or [IntPtr]::Size -ne 8 -or $PSVersionTable.PSVersion.Major -lt 7){throw 'Fresh Windows x64 PowerShell7 required.'}
    foreach($type in 'IW7.CommunityBuild.BuildJob','IW7.MaterialDiagnostics.JobMembers','IW7ResourceMemoryV1'){
        if($type -as [type]){throw 'Fresh host required for source-bound native helpers.'}
    }
    . "$ProviderRoot/ops/Resource-Scheduler.Core.ps1"
    $lease=Enter-IW7ResourceLease -Scope $RunRoot -Kind Build -PhysicalBytes $b.PhysicalBytes -CommitBytes $b.CommitBytes -Owner 'World original CLIPMAP observer harness'
    $groupStart=Get-MaterialV2MonotonicMs
    if(Test-Path -LiteralPath $RunRoot){throw 'World output directory appeared during admission.'}
    $null=Resolve-WorldObserverPath $RunRoot
    [IO.Directory]::CreateDirectory($RunRoot)|Out-Null;$created=$true
    $state=[ordered]@{Schema='iw7.world-observer-run/1';Plan=$plan;Status='Preparing';RetainedLeaseToken=$lease.Token;
        NativeCompiled=$false;NativeHarnessPassed=$false;EngineObserved=$false;JobClosureVerified=$false;
        SourceHashesUnchanged=$false;LeaseReleased=$false;LeaseReleaseState='NotAttempted';CompilerWitness=[ordered]@{CompilerIdentity=$null;Completed=$false};
        JobCleanup=$null;FixturePermit=$null;FixtureStartedMs=$null;FinalBytes=$null;Failure=$null}
    Add-Type -LiteralPath "$ProviderRoot/tools-source/asset-bridge/model/BuildJob.cs"
    Assert-WorldObserverTime ((Get-MaterialV2MonotonicMs)-$groupStart) 'compile' 0
    Add-Type -LiteralPath "$ProviderRoot/tools-source/asset-bridge/surfaces/MaterialV2.JobMembers.cs"
    Assert-WorldObserverTime ((Get-MaterialV2MonotonicMs)-$groupStart) 'compile' 0
    $token=([guid]::NewGuid().ToString('N')+[guid]::NewGuid().ToString('N'))
    $spec=[ordered]@{schema='iw7.world-observer-driver/1';root=$RunRoot;compiler=$compiler;
        compiler_sha256=$policy.CompilerSHA256.ToLowerInvariant();arguments=$arguments;fixture=$plan.Fixture;
        drain=Join-Path $ProviderRoot 'sdk/modding/beacon_tool_phase.py';
        drain_sha256=$manifest.provider_sha256.'sdk/modding/beacon_tool_phase.py';token=$token}
    $specPath=Join-Path $RunRoot 'spec.json';Write-WorldObserverJson $specPath $spec
    $guards.Add([IO.File]::Open($specPath,'Open','Read','Read'));$specHash=(Get-FileHash -LiteralPath $specPath).Hash
    $argsText=ConvertTo-MaterialV2Arguments @('-B',$plan.Driver,'--spec',$specPath,'--sha256',$specHash)
    Assert-WorldObserverPins $entries
    Assert-WorldObserverTime ((Get-MaterialV2MonotonicMs)-$groupStart) 'compile' 0
    $closed=$false # Even factory failure requires closure proof; never infer it from null.
    $owner=[IW7.CommunityBuild.BuildJob]::Prepare($PythonExe,$argsText,$RunRoot)
    $identity=Get-BeaconJobIdentity $owner $PythonExe 'world-harness'
    $state.Identity=$identity;$state.Status='Running'
    $started=Start-MaterialV2OwnedPhase $owner $lease.Token
    $identity.ResourceRegistration=$started
    $clockStart=$started.StartedMonotonicMs
    Wait-MaterialV2OwnedPhase $owner $identity $clockStart $b.SupervisorSeconds {
        param($snapshot,$changed)
        Assert-WorldObserverPollTime $state $clockStart (Get-MaterialV2MonotonicMs) $groupStart
        if(Test-Path -LiteralPath (Join-Path $RunRoot 'stop.request')){throw 'Coordinator requested original-job stop.'}
        $null=Measure-WorldObserverOutput $RunRoot
        $memory=Get-IW7ResourceSnapshot;if($memory.Committed -gt $memory.CommitLimit*0.85){throw 'Commit pressure exceeded85 percent.'}
        $observation=[IW7.MaterialDiagnostics.JobMembers]::Capture($owner)
        Update-MaterialV2CompilerWitness $state.CompilerWitness $observation $identity.PID $policy
        $compilePath=Join-Path $RunRoot 'compile.json'
        if(Test-Path -LiteralPath $compilePath){
            $receipt=Read-BeaconJson $compilePath 64KB
            Assert-WorldObserverCompileReceipt $receipt $state.CompilerWitness $policy
            $state.NativeCompiled=$true
            if($null -eq $state.FixtureStartedMs){
                if($snapshot.RootExited){throw 'Driver exited before the fixture gate.'}
                Assert-WorldObserverAdvance $observation $identity $state.CompilerWitness $receipt $policy
                $file=Get-Item -LiteralPath $plan.Fixture
                if($file.Length -lt 1 -or $file.Length -gt 8MB){throw 'Bounded compiled world fixture required.'}
                $null=Resolve-WorldObserverPath $plan.Fixture
                $guards.Add([IO.File]::Open($plan.Fixture,'Open','Read','Read'))
                $fixtureHash=(Get-FileHash -LiteralPath $plan.Fixture).Hash
                $entries.Add([pscustomobject]@{Path=$plan.Fixture;SHA256=$fixtureHash})
                $state.FixturePermit=[ordered]@{schema='iw7.world-observer-permit/1';token=$token;fixture_sha256=$fixtureHash.ToLowerInvariant()}
                # callback child scope must persist this transition for later polls.
                $state.FixtureStartedMs=Get-MaterialV2MonotonicMs
                Write-WorldObserverJson (Join-Path $RunRoot 'fixture-go.json') $state.FixturePermit
            }
            if($snapshot.RootExited -and $snapshot.ActiveProcesses -ne 0){
                $null=Complete-MaterialV2CompilerTelemetry $owner $snapshot $observation $receipt $state.CompilerWitness $policy
            }
        }
        Assert-WorldObserverPollTime $state $clockStart (Get-MaterialV2MonotonicMs) $groupStart
    }
    $closed=$true;Assert-WorldObserverClosed $identity
    $checked=Read-BeaconJson (Join-Path $RunRoot 'checked.json') 64KB
    if($checked.schema -cne 'iw7.world-clipmap-harness-check/1' -or $checked.status -cne 'synthetic-transcript-checked' -or
       $checked.engine_observed -isnot [bool] -or $checked.engine_observed -or $checked.records -ne 24){throw 'Checked synthetic transcript required.'}
    $fixtureReceipt=Read-BeaconJson (Join-Path $RunRoot 'fixture.json') 64KB
    Assert-MaterialV2PhaseResult $fixtureReceipt 'fixture' $state.FixturePermit.fixture_sha256 $identity
    Assert-BeaconHash (Join-Path $RunRoot 'fixture.stdout.log') $checked.transcript_sha256
    Assert-WorldObserverPollTime $state $clockStart (Get-MaterialV2MonotonicMs) $groupStart
    $state.Checked=$checked;$state.NativeHarnessPassed=$true;$state.Status='SyntheticHarnessPassed'
} catch {$failure=$_;if($state){$state.Failure=$_.Exception.Message;$state.Status='Failed'}}
finally {
    if($owner -and !$closed){$state.JobCleanup=[ordered]@{};$closed=Stop-MaterialV2OwnedPhase $owner $state.JobCleanup}
    try{if(Get-Command Assert-WorldObserverPins -ErrorAction SilentlyContinue){Assert-WorldObserverPins $entries}}catch{$intact=$false;if(!$failure){$failure=$_}}
    if($state){$state.SourceHashesUnchanged=$intact;$state.JobClosureVerified=$closed}
    if($closed -and $owner){$owner.Dispose();$owner=$null}
    if($lease -and $created -and $state){
        try{
            if($failure){$state.Status='Failed';$state.Failure=$failure.Exception.Message}
            Complete-WorldObserverReservation $RunRoot $state $lease $guards
        }catch{if(!$failure){$failure=$_}}
    }
    if(!$lease -or ($state -and $state.LeaseReleased)){foreach($guard in $guards){$guard.Dispose()}}
    else{[AppDomain]::CurrentDomain.SetData(('IW7.WorldHarness.Quarantine.'+$lease.Token),@{Owner=$owner;Guards=$guards;State=$state;Failure=$failure})}
}
if($failure){
    if($lease -and (!$state -or !$state.LeaseReleased)){
        $releaseState=if($state){$state.LeaseReleaseState}else{'NotAttempted'}
        $finalization=if($state -and $state.FinalizationFailure){" Finalization: $($state.FinalizationFailure)"}else{''}
        throw "World run failed; lease release $releaseState; reconcile token $($lease.Token). $($failure.Exception.Message)$finalization"
    }
    throw $failure
}
if(!$closed -or !$intact -or !$state.LeaseReleased){throw 'World cleanup/source proof incomplete; inspect retained lease.'}
$state|ConvertTo-Json -Depth 20

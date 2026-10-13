param([Parameter(Mandatory)][string]$VCToolsRoot,[Parameter(Mandatory)][string]$WindowsSdkRoot,
    [Parameter(Mandatory)][string]$PythonExe,[Parameter(Mandatory)][string]$StageProviderRoot,
    [Parameter(Mandatory)][string]$LinkProfilePath,[Parameter(Mandatory)][string]$NativeJobAssembly,
    [string]$WindowsSdkVersion='10.0.26100.0')
$ErrorActionPreference='Stop'
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$runRoot=Join-Path $repo ('runtime/world-plan-inert-'+[guid]::NewGuid().ToString('N'))
$script:forbidden=0
function Deny-WorldPlanSideEffect {$script:forbidden++;throw 'Plan attempted a side effect.'}
function Add-Type {Deny-WorldPlanSideEffect}
function Start-Process {Deny-WorldPlanSideEffect}
function Enter-IW7ResourceLease {Deny-WorldPlanSideEffect}
function Get-IW7ResourceSnapshot {Deny-WorldPlanSideEffect}
function Add-IW7ResourceProcess {Deny-WorldPlanSideEffect}
function Exit-IW7ResourceLease {Deny-WorldPlanSideEffect}
$types=@('IW7.AnimationProbe.NativeJob','IW7.H1Diagnostics.JobMembers','IW7ResourceMemoryV1')
foreach($name in $types){if($name -as [type]){throw 'Fresh host required for inert Plan witness.'}}
$arguments=@{RunRoot=$runRoot;VCToolsRoot=$VCToolsRoot;WindowsSdkRoot=$WindowsSdkRoot;WindowsSdkVersion=$WindowsSdkVersion;
    PythonExe=$PythonExe;StageProviderRoot=$StageProviderRoot;LinkProfilePath=$LinkProfilePath;NativeJobAssembly=$NativeJobAssembly}
$raw=& "$PSScriptRoot/Run-ObserverHarness.ps1" @arguments
$result=($raw -join "`n")|ConvertFrom-Json -Depth 25;$plan=$result.Plan
$rawAgain=& "$PSScriptRoot/Run-ObserverHarness.ps1" @arguments
$again=($rawAgain -join "`n")|ConvertFrom-Json -Depth 25
if($result.PlanSHA256 -cne $again.PlanSHA256 -or $result.PlanSHA256 -cnotmatch '^[a-f0-9]{64}$'){throw 'Plan identity is not deterministic.'}
if($plan.Mode -cne 'Plan' -or $plan.Schema -cne 'iw7.world-observer-execution-plan/2' -or
   $plan.PhysicalBytes -ne 4GB -or $plan.CommitBytes -ne 6GB -or $plan.GroupDeadlineSeconds -ne 120 -or
   $plan.OriginalJobs -ne 4 -or $plan.NativeParallelism -ne 1 -or $plan.HeavyExecutionAuthorizedByPlan -or
   $plan.EngineObserved -or $script:forbidden -ne 0 -or (Test-Path -LiteralPath $runRoot)){throw 'Plan was not inert or changed its budgets.'}
if($plan.OutputContract.StrictWriteCap -or $plan.OutputContract.Enforcement -cne 'Sampled' -or
    $null -ne $plan.OutputContract.MaximumOvershootBytes -or $plan.OutputContract.StreamThresholdBytes -ne 2MB){throw 'Sampled logging was represented as strict.'}
foreach($name in $types){if($name -as [type]){throw 'Plan loaded a native helper type.'}}
if(($plan.Stages.Name -join ',') -cne 'compile,link,fixture,check' -or '/c' -cnotin $plan.Stages[0].Arguments -or
    '/link' -cin $plan.Stages[0].Arguments -or @($plan.Stages[0].Arguments|Where-Object{$_ -match '^/(MP|Fe)'}).Count -or
    [IO.Path]::GetFileName($plan.Stages[1].Image) -cne 'link.exe' -or
    $plan.Stages[0].DeadlineSeconds -ne 90 -or $plan.Stages[1].DeadlineSeconds -ne 90 -or
    $plan.Stages[2].DeadlineSeconds -ne 10 -or $plan.Stages[3].DeadlineSeconds -ne 5){throw 'Explicit original-tool stages differ.'}
foreach($key in 'CL','_CL_','LINK','_LINK_','INCLUDE','LIB','LIBPATH') {
    if($key -cin $plan.Environment.PSObject.Properties.Name){throw 'Unreviewed build environment override.'}
}
"PASS: deterministic inert stage Plan; $($plan.Bindings.Count) bindings; no native type/process/tree/lease."

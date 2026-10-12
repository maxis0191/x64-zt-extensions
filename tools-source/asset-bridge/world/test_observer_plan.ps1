param([Parameter(Mandatory)][string]$VCToolsRoot,[Parameter(Mandatory)][string]$WindowsSdkRoot,
    [Parameter(Mandatory)][string]$PythonExe,[string]$WindowsSdkVersion='10.0.26100.0')
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
$types=@('IW7.CommunityBuild.BuildJob','IW7.MaterialDiagnostics.JobMembers','IW7ResourceMemoryV1')
foreach($name in $types){if($name -as [type]){throw 'Fresh host required for inert Plan witness.'}}
$raw=& "$PSScriptRoot/Run-ObserverHarness.ps1" -RunRoot $runRoot -VCToolsRoot $VCToolsRoot `
    -WindowsSdkRoot $WindowsSdkRoot -WindowsSdkVersion $WindowsSdkVersion -PythonExe $PythonExe
$plan=($raw -join "`n")|ConvertFrom-Json
if($plan.Mode -cne 'Plan' -or $plan.Schema -cne 'iw7.world-observer-execution-plan/1' -or
   $plan.Budgets.PhysicalBytes -ne 4GB -or $plan.Budgets.CommitBytes -ne 6GB -or
   $plan.Budgets.GroupMs -ne 120000 -or $plan.Budgets.CompileMs -ne 90000 -or $plan.Budgets.FixtureMs -ne 10000 -or
   $plan.OriginalJobs -ne 1 -or $plan.HeavyExecutionAuthorizedByPlan -or $plan.EngineObserved -or
   $script:forbidden -ne 0 -or (Test-Path -LiteralPath $runRoot)){throw 'Plan was not inert or changed its exact budgets.'}
foreach($name in $types){if($name -as [type]){throw 'Plan loaded a native helper type.'}}
$expected=@('/nologo','/std:c++20','/EHsc','/MD','/O1','/W4','/D_CRT_SECURE_NO_WARNINGS','/link','/INCREMENTAL:NO','bcrypt.lib')
if(@($expected|Where-Object{$_ -cnotin $plan.CompilerArguments}).Count -or
   @($plan.CompilerArguments|Where-Object{$_ -match '^/MP'}).Count){throw 'Plan compiler arguments changed.'}
"PASS: real installed-tool Plan is inert; $($plan.SourceAndProviderPins.Count) bound inputs; no tree/native type/process/lease."

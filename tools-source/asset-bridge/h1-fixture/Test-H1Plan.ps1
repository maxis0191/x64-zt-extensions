[CmdletBinding()]
param([Parameter(Mandatory)][string]$PlanPath,[Parameter(Mandatory)][string]$PlanSHA256)
# Use a reviewed local plan. All mutations are temporary copies, never providers.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$runner=Join-Path $PSScriptRoot 'Run-H1Native.ps1'
$plan=Get-Content -LiteralPath $PlanPath -Raw|ConvertFrom-Json -Depth 20
$checks=0
function Check([bool]$Value,[string]$Message){if(!$Value){throw $Message};$script:checks++}
function Refuses([scriptblock]$Action,[string]$Pattern) {
    $message=$null;try{& $Action|Out-Null}catch{$message=$_.Exception.Message}
    Check ($null -ne $message -and $message -like $Pattern) ('Expected refusal: '+$Pattern+'; actual: '+$message)
}
$accepted=& $runner -PlanPath $PlanPath -PlanSHA256 $PlanSHA256|ConvertFrom-Json
Check ($accepted.BindingsVerified -eq 54 -and !$accepted.NativeTypesLoaded -and !$accepted.LeaseAcquired -and !$accepted.RunRootCreated) 'Read-only plan verification changed state.'
Refuses {& $runner -PlanPath $PlanPath -PlanSHA256 ('0'*64)} '*Reviewed plan hash differs*'
Refuses {& $runner -PlanPath $PlanPath -PlanSHA256 $PlanSHA256 -Stage Probe} '*'

$temp=Join-Path ([IO.Path]::GetTempPath()) ('iw7-h1-plan-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($temp)|Out-Null
$copy=Join-Path $temp 'plan.json';$bound=Join-Path $temp 'input.txt'
function Save-TestPlan($Value) {
    [IO.File]::WriteAllText($copy,($Value|ConvertTo-Json -Depth 20),[Text.UTF8Encoding]::new($false))
    (Get-FileHash -LiteralPath $copy).Hash.ToLowerInvariant()
}
try {
    $changed=$plan|ConvertTo-Json -Depth 20|ConvertFrom-Json -Depth 20
    $changed.Stages.Probe.PhysicalBytes=1
    $hash=Save-TestPlan $changed
    Refuses {& $runner -PlanPath $copy -PlanSHA256 $hash} '*fixed budgets differ*'

    # Simulate same-length source drift after review without editing a real input.
    [IO.File]::WriteAllText($bound,'before!!')
    $changed=$plan|ConvertTo-Json -Depth 20|ConvertFrom-Json -Depth 20
    $changed.Bindings[0]=[pscustomobject]@{Path=$bound;Bytes=8;SHA256=(Get-FileHash -LiteralPath $bound).Hash.ToLowerInvariant()}
    $hash=Save-TestPlan $changed
    [IO.File]::WriteAllText($bound,'after!!!')
    Refuses {& $runner -PlanPath $copy -PlanSHA256 $hash} '*Bound input hash/length differs*'

    # A stale reviewed core hash must fail before core import or provider use.
    $changed=$plan|ConvertTo-Json -Depth 20|ConvertFrom-Json -Depth 20
    ($changed.Bindings|Where-Object Path -CEQ $plan.Core).SHA256='0'*64
    $hash=Save-TestPlan $changed
    Refuses {& $runner -PlanPath $copy -PlanSHA256 $hash} '*Bootstrap source differs*'

    $changed=$plan|ConvertTo-Json -Depth 20|ConvertFrom-Json -Depth 20
    ($changed.Bindings|Where-Object Path -CEQ $plan.JobAssembly).SHA256='0'*64
    $hash=Save-TestPlan $changed
    Refuses {& $runner -PlanPath $copy -PlanSHA256 $hash} '*Bound input hash/length differs*'
}finally{
    foreach($path in @($copy,$bound)){if([IO.File]::Exists($path)){[IO.File]::Delete($path)}}
    [IO.Directory]::Delete($temp,$false)
}
Check (!(Test-Path -LiteralPath $plan.RunRoot)) 'Plan created a runtime output root.'
Check (!(('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7ResourceMemoryV1' -as [type]))) 'Plan loaded native types.'
[ordered]@{Schema='iw7.h1-native-plan-source-tests/1';Assertions=$checks;NativeTypesLoaded=$false;
    LeaseAcquired=$false;RunRootCreated=$false;RealJobsTested=$false}|ConvertTo-Json

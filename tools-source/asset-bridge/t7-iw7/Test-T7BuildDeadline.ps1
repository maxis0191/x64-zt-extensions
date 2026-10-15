# Real H1 stage/deadline functions and the real runner's finally block, with a
# simulated clock/owner/finalizer. No native type, child process or lease.
[CmdletBinding()]
param([Parameter(Mandatory)][string]$H1Core)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. $H1Core
$script:TestClock=600001.0;$script:T7GroupStarted=0.0
function Get-H1Clock { $script:TestClock }
. (Join-Path $PSScriptRoot 'T7Build.Profile.ps1')
$registration=$false;$incoming=$false # Explicit legacy selectors for the isolated real-finalizer harness.
function Require-T7Test($Condition,[string]$Message){if(!$Condition){throw $Message}}
$script:CreatedOwners=0
function New-H1Owner {$script:CreatedOwners++;throw 'Regression: native owner creation reached after group expiry.'}
$plan=[pscustomobject]@{GroupDeadlineSeconds=600}
$state=[ordered]@{Stage='Compile';DeadlineSeconds=120}
$context=[pscustomobject]@{Owner=$null;Closed=$true;Lease=$null}
$caught=$null
try {Invoke-H1OwnedStage $plan $state $context $null ('0'*64) 'unused' 600001.0}catch{$caught=$_}
Require-T7Test ($null -ne $caught -and $script:CreatedOwners -eq 0 -and $context.Closed) 'Expired group reached native creation/start.'

$tokens=$null;$errors=$null
$runner=Join-Path $PSScriptRoot 'Run-T7Build.ps1'
$ast=[Management.Automation.Language.Parser]::ParseFile($runner,[ref]$tokens,[ref]$errors)
Require-T7Test ($errors.Count -eq 0) 'Runner parse failed.'
$outer=@($ast.EndBlock.Statements|Where-Object {$_ -is [Management.Automation.Language.TryStatementAst]})
Require-T7Test ($outer.Count -eq 1) 'One outer runner try/finally required.'
$body=$outer[0].Finally.Extent.Text
$finalize=[scriptblock]::Create($body.Substring(1,$body.Length-2))

# Completing cleanup at 602000 must preserve cleanup and publish only failure.
$script:TestClock=599000.0;$script:CleanupCalls=0
$script:Published=[Collections.Generic.List[string]]::new()
function Complete-H1Stage($Context,$State) {
    $script:CleanupCalls++;$script:TestClock=602000.0
    $Context.Closed=$true;$Context.Lease=$null;$State.LeaseReleased=$true
}
function Write-H1Receipt($Plan,$State,$Root){$script:Published.Add([string]$State.Status)}
$plan=[pscustomobject]@{GroupDeadlineSeconds=600;RunRoot='unused'}
$state=[ordered]@{Status='Pending';InputsReverified=$true;LeaseReleased=$false}
$guards=[Collections.Generic.List[object]]::new()
$context=[pscustomobject]@{Owner=$null;Closed=$true;Lease='simulated';Guards=$guards;PublicationGuards=[Collections.Generic.List[object]]::new();Publications=[Collections.Generic.List[object]]::new();PreReleasePublished=$false;CompletionPublished=$false;CanExit=$false}
$failure=$null;$created=$true;$launcher=$null;$priority=$null
. $finalize
Require-T7Test ($script:CleanupCalls -eq 1 -and $state.LeaseReleased) 'Deadline prevented final cleanup.'
Require-T7Test ($state.Status -ceq 'Failed' -and $null -ne $failure -and
    $script:Published.Count -eq 1 -and $script:Published[0] -ceq 'Failed') 'Late finalization published Passed.'

# The receipt itself is also a costly operation. Keep a late attempt, but no
# canonical Passed receipt. This third check writes only tiny ignored fixtures.
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot ('../../../runtime/t7-deadline-test-'+[guid]::NewGuid().ToString('N'))))
[IO.Directory]::CreateDirectory($root)|Out-Null
$script:TestClock=599000.0;$script:Publications=0
function Complete-H1Stage($Context,$State){$Context.Closed=$true;$Context.Lease=$null;$State.LeaseReleased=$true}
function Write-H1Receipt($Plan,$State,$Root) {
    $script:Publications++
    $raw=[Text.Encoding]::UTF8.GetBytes((@{Status=$State.Status}|ConvertTo-Json -Compress))
    $stream=[IO.FileStream]::new((Join-Path $Root 'receipt.json'),'CreateNew','Write','Read')
    try{$stream.Write($raw,0,$raw.Length)}finally{$stream.Dispose()}
    if($script:Publications -eq 1){$script:TestClock=602000.0}
}
$plan=[pscustomobject]@{GroupDeadlineSeconds=600;RunRoot=$root}
$state=[ordered]@{Status='Pending';InputsReverified=$true;LeaseReleased=$false}
$guards=[Collections.Generic.List[object]]::new()
$context=[pscustomobject]@{Owner=$null;Closed=$true;Lease='simulated';Guards=$guards;PublicationGuards=[Collections.Generic.List[object]]::new();Publications=[Collections.Generic.List[object]]::new();PreReleasePublished=$false;CompletionPublished=$false;CanExit=$false}
$failure=$null;$created=$true;$launcher=$null;$priority=$null
. $finalize
$receipt=Get-Content -LiteralPath (Join-Path $root 'receipt.json') -Raw|ConvertFrom-Json
Require-T7Test ($receipt.Status -ceq 'Failed' -and $state.Status -ceq 'Failed' -and $null -ne $failure -and
    (Test-Path -LiteralPath (Join-Path $root 'receipt.deadline-exceeded.json'))) 'Late receipt remained a canonical Passed result.'
[ordered]@{Tests=3;Passed=$true;NativeTypesLoaded=$false;ChildrenStarted=0;LeaseAcquired=$false;Fixture=$root}|ConvertTo-Json

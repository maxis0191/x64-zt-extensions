# Exercise the real H1 telemetry policy through the T7 Link adapter. Native
# observation/stop/file reads are replaced with explicit synthetic witnesses.
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Providers)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $Providers 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1')
. (Join-Path $Providers 'tools-source/asset-bridge/surfaces/MaterialV2.Compiler.ps1')
. (Join-Path $Providers 'tools-source/asset-bridge/h1-fixture/H1Native.Compiler.ps1')
$script:T7GroupStarted=0.0
function Get-H1Clock {50000.0}
. (Join-Path $PSScriptRoot 'T7Build.Profile.ps1')
function Require-T7LinkTest($Condition,[string]$Message){if(!$Condition){throw $Message}}
$linkSHA='a364af801a8539e4324d9489313dbf001d959128451fc99a27b24676bbac058f'
$telemetrySHA='D591358C6AEE4B673562CA3B3A15C250E612708394FE3B44A7A7EDA2470570A5'.ToLowerInvariant()
$plan=[pscustomobject]@{Compiler='C:\Pinned\cl.exe';GroupDeadlineSeconds=600;Bindings=@(
    [pscustomobject]@{Path='C:\Pinned\link.exe';SHA256=$linkSHA},
    [pscustomobject]@{Path='C:\Pinned\vctip.exe';SHA256=$telemetrySHA})}
$start=[pscustomobject]@{FileName='C:\Pinned\link.exe'}
$identity=[pscustomobject]@{PID=101;Image=$start.FileName;CreatedUtc='2026-10-12T11:00:00.0000000Z'}
function Test-H1Budget($Plan,$State) {}
function Confirm-H1BoundInputs($Plan) {if($script:Case -ceq 'input-change'){throw 'Synthetic changed input.'}}
function Open-H1Pin($Pin) {[IO.MemoryStream]::new()}
function Get-H1CompilerArtifacts($Plan,$Context) {
    $script:ArtifactChecks++
    if($script:Case -ceq 'artifact-change'){throw 'Synthetic changed artifact.'}
    [pscustomobject]@{Path='C:\Private\link\candidate.exe';Bytes=1024;SHA256=('1'*64)}
}
function Get-H1OriginalState($Owner) {
    [pscustomobject]@{RootExited=$true;RootExitCode=$(if($script:Case -ceq 'root-nonzero'){1}else{0});
        ActiveProcesses=$(if($script:Stops){0}else{1});PID=$identity.PID;Image=$identity.Image;CreatedUtc=$identity.CreatedUtc}
}
function Get-H1OriginalMembers($Owner) {
    $script:Captures++
    if($script:Stops){return [pscustomobject]@{AssignedCount=0;ListedCount=0;Members=@()}}
    $member=[pscustomobject]@{PID=202;ParentPID=101;Image='C:\Pinned\vctip.exe';
        CreatedUtc='2026-10-12T11:00:01.0000000Z';InOriginalJob=$true;Error=$null;ParentError=$null}
    if($script:Case -ceq 'wrong-image'){$member.Image='C:\Other\vctip.exe'}
    if($script:Case -ceq 'wrong-parent'){$member.ParentPID=303}
    if($script:Case -ceq 'outside-job'){$member.InOriginalJob=$false}
    if($script:Case -ceq 'pid-reused' -and $script:Captures -eq 2){$member.CreatedUtc='2026-10-12T11:00:02.0000000Z'}
    [pscustomobject]@{AssignedCount=1;ListedCount=1;Members=@($member);CapturedUtc='2026-10-12T11:00:03.0000000Z'}
}
function Stop-H1OriginalJob($Owner) {
    Require-T7LinkTest ($script:ArtifactChecks -eq 1 -and $script:Captures -eq 2) 'Stop occurred before artifact/two-member proof.'
    $script:Stops++
}
function Invoke-H1OwnedStage($Plan,$State,$Context,$Start,$ImageSHA256,$StageRoot,$Started) {
    Require-T7LinkTest ($State.Stage -ceq 'Compile' -and $Plan.Compiler -ceq 'C:\Pinned\link.exe') 'Link did not use the existing strict H1 branch.'
    $policy=Get-MaterialV2CompilerPolicy $Plan.Compiler
    Require-T7LinkTest ($policy.CompilerSHA256 -ceq $linkSHA -and $policy.Telemetry -ceq 'C:\Pinned\vctip.exe') 'Adapter changed telemetry identity.'
    $snapshot=Get-H1OriginalState $Context.Owner
    $accepted=Complete-H1CompilerTelemetry $Plan $State $Context $snapshot $Started
    Require-T7LinkTest $accepted 'Valid synthetic linker residue was not qualified.'
}
$tests=0
foreach($script:Case in @('valid','root-nonzero','wrong-image','wrong-parent','outside-job','pid-reused','input-change','artifact-change')) {
    $script:Stops=0;$script:Captures=0;$script:ArtifactChecks=0
    $state=[ordered]@{Stage='Link';PlanSHA256=('2'*64);Identity=$identity;DeadlineSeconds=120;
        CompilerTelemetry=[ordered]@{Completed=$false;Action=$null}}
    $context=[pscustomobject]@{Owner='synthetic-original-owner'}
    $caught=$null
    try{Invoke-T7OwnedStage $plan $state $context $start $linkSHA 'unused' 50000.0}catch{$caught=$_}
    Require-T7LinkTest ($state.Stage -ceq 'Link') 'Adapter failed to preserve the real Link phase label.'
    if($script:Case -ceq 'valid') {
        Require-T7LinkTest ($null -eq $caught -and $script:Stops -eq 1 -and $state.CompilerTelemetry.Completed -and $script:Captures -eq 3) ('Valid residue failed: '+$caught)
    }else{Require-T7LinkTest ($null -ne $caught -and $script:Stops -eq 0) ('Unsafe residue accepted: '+$script:Case)}
    $tests++
}
$clPolicy=Get-MaterialV2CompilerPolicy 'C:\Pinned\cl.exe'
Require-T7LinkTest ($clPolicy.Compiler -ceq 'C:\Pinned\cl.exe') 'Scoped Link factory escaped into the original cl policy.'
$caught=$null
try{Get-MaterialV2CompilerPolicy 'C:\Pinned\link.exe'|Out-Null}catch{$caught=$_}
Require-T7LinkTest ($null -ne $caught) 'Global compiler policy was broadened.'
$tests++
$caught=$null;$state.Stage='Link'
try{Invoke-T7OwnedStage $plan $state $context $start ('0'*64) 'unused' 50000.0}catch{$caught=$_}
Require-T7LinkTest ($null -ne $caught) 'Unpinned linker image accepted.'
$tests++
[ordered]@{Tests=$tests;Passed=$true;NativeTypesLoaded=$false;ChildrenStarted=0;LeaseAcquired=$false}|ConvertTo-Json

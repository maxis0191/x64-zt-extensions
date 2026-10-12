# Default is source-only validation. A separately approved Run consumes one fresh host/root.
[CmdletBinding(DefaultParameterSetName='Validate')]
param(
    [Parameter(Mandatory)][string]$PlanPath,[Parameter(Mandatory)][string]$PlanSHA256,
    [Parameter(Mandatory)][string]$RunRoot,[Parameter(Mandatory)][string]$HostContractPath,
    [Parameter(Mandatory)][string]$HostContractSHA256,
    [Parameter(Mandatory,ParameterSetName='Run')][switch]$Run,
    [Parameter(Mandatory,ParameterSetName='Finish')][switch]$Finish
)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
if(!$IsWindows -or [IntPtr]::Size -ne 8 -or $PSVersionTable.PSVersion.Major -lt 7){throw 'Windows x64 PowerShell 7 required.'}
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
. (Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7CatalogueHost.Core.ps1')
$existing=[AppDomain]::CurrentDomain.GetData('IW7.T7CatalogueHost')
if($Finish){
    if(!$existing -or $existing.PlanPath -cne $PlanPath -or $existing.PlanSHA256 -cne $PlanSHA256 -or
       $existing.RunRoot -cne $RunRoot -or $existing.ContractPath -cne $HostContractPath -or
       $existing.ContractSHA256 -cne $HostContractSHA256){throw 'Finish requires the original in-memory host contract.'}
    . (Join-Path $repo 'ops/Resource-Scheduler.Core.ps1')
    . (Join-Path $PSScriptRoot 'T7Prepatch.Profile.ps1')
    . (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
    Complete-T7CatalogueHost $existing
    return
}
if($existing){throw 'Host already consumed; no Run re-entry or retry.'}
foreach($suffix in @('.host-start.json','.host-return.json','.host-postflight.json')){
    if(Test-Path -LiteralPath ($RunRoot+$suffix)){throw 'Host evidence already exists; no RunRoot retry.'}
}
$hostState=Open-T7CatalogueHostInputs $PlanPath $PlanSHA256 $RunRoot $HostContractPath $HostContractSHA256 $PSCommandPath $repo
$retained=$false
try {
    # The unchanged runner owns the complete Plan schema, pin and receipt validation.
    & $hostState.Plan.Runner -PlanPath $PlanPath -PlanSHA256 $PlanSHA256
    if(!$Run){return}
    $identity=Get-T7CatalogueHostIdentity
    Assert-T7CatalogueHostArguments $hostState ([Environment]::GetCommandLineArgs()) $identity
    if(('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7ResourceMemoryV1' -as [type]) -or ('IW7HudFileIdentity' -as [type])){throw 'Fresh host runtime types required.'}
    . (Join-Path $repo 'ops/Resource-Scheduler.Core.ps1')
    Assert-T7CataloguePreservedProcesses $hostState.Contract @(Get-IW7ResourceProcesses)
    $hostState.Host=$identity;$hostState.Phase='Running'
    [AppDomain]::CurrentDomain.SetData('IW7.T7CatalogueHost',$hostState);$retained=$true
    Write-T7CatalogueHostEvidence ($RunRoot+'.host-start.json') ([ordered]@{Host=$identity;PlanPath=$PlanPath;
        PlanSHA256=$PlanSHA256;ContractSHA256=$HostContractSHA256;ArgumentsVerified=$true;CanExit=$false})
    try {& $hostState.Plan.Runner -PlanPath $PlanPath -PlanSHA256 $PlanSHA256 -Run}
    catch {$hostState.RunnerError=$_.Exception.Message;Write-Warning ('Runner returned: '+$hostState.RunnerError)}
    finally {
        $hostState.RunnerReturned=$true;$hostState.RunnerReturnedUtc=[DateTime]::UtcNow.ToString('o');$hostState.Phase='Returned'
        Write-T7CatalogueHostEvidence ($RunRoot+'.host-return.json') ([ordered]@{Host=$identity;PlanSHA256=$PlanSHA256;
            ContractSHA256=$HostContractSHA256;RunnerReturned=$true;RunnerReturnedUtc=$hostState.RunnerReturnedUtc;Error=$hostState.RunnerError})
    }
    . (Join-Path $repo 'ops/Resource-Scheduler.Core.ps1')
    . (Join-Path $PSScriptRoot 'T7Prepatch.Profile.ps1')
    . (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
    Complete-T7CatalogueHost $hostState
}finally{
    # Never release host guards just because a runtime/closure command threw.
    if(!$retained){Close-T7CatalogueHostGuards $hostState}
}
# No exit/kill/retry here. Observe actual PTY exit and independent absence separately.

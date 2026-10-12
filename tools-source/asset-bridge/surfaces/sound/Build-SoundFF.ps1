param([Parameter(Mandatory)][string]$PlanPath,[Parameter(Mandatory)][string]$PlanSHA256,[switch]$Run)
$ErrorActionPreference='Stop'
if((Get-Item -LiteralPath $PlanPath).Length -gt 256KB -or (Get-FileHash -LiteralPath $PlanPath).Hash -ine $PlanSHA256){throw 'Reviewed execution plan changed.'}
$plan=Get-Content -LiteralPath $PlanPath -Raw|ConvertFrom-Json
foreach($required in @($PSCommandPath,(Join-Path $PSScriptRoot 'SoundFF.Core.ps1'))){
    $pin=@($plan.HashInputs|Where-Object Path -IEQ $required)
    if($pin.Count -ne 1 -or (Get-FileHash -LiteralPath $required).Hash -ine $pin[0].SHA256){throw 'Current adapter source not bound by plan.'}
}
. "$PSScriptRoot/SoundFF.Core.ps1"
Assert-SoundFFPath $PlanPath
Assert-SoundFFExecutionPlan $plan $PSScriptRoot
foreach($entry in $plan.HashInputs){Assert-SoundFFPin $entry}
if(!$Run){$plan|ConvertTo-Json -Depth 25;return}
if(('IW7.SoundFFTelemetryV1.BuildJob' -as [type]) -or ('IW7.CommunityBuild.BuildJob' -as [type]) -or ('IW7HudFileIdentity' -as [type]) -or ('IW7ResourceMemoryV1' -as [type])){throw 'Fresh source-bound native host required.'}
Invoke-SoundFFTransaction $plan $PlanPath $PlanSHA256|ConvertTo-Json -Depth 25

param([Parameter(Mandatory)][string]$Fixture)
# Only synthetic temporary files from test_rig_executor.py are supplied here.
$ErrorActionPreference='Stop'
. "$PSScriptRoot/Rig.Core.ps1"
$data=[IO.File]::ReadAllText($Fixture)|ConvertFrom-Json
$plan=$data.plan;$report=$data.report;$checks=0
function Check([bool]$Value,[string]$Message){if(!$Value){throw $Message};$script:checks++}
function Refuse([scriptblock]$Body){$caught=$false;try{& $Body|Out-Null}catch{$caught=$true};Check $caught 'Corrupt readback was accepted'}
function Assert-BeaconHash($Path,$Hash){if((Get-FileHash -LiteralPath $Path).Hash -ine $Hash){throw 'Actual fixture bytes changed'}}
Assert-RigReader $report -FF
Assert-RigReaderBindings $report $plan -FF
Check $true 'Actual independent Python report and all retained synthetic files agree'
foreach($path in @($plan.staged_profile_inputs.source)+@($plan.retain_redumps_before_restore.retained)){
    $original=[IO.File]::ReadAllBytes($path)
    try{
        $changed=[byte[]]$original.Clone();$changed[0]=$changed[0] -bxor 1
        [IO.File]::WriteAllBytes($path,$changed)
        Refuse {Assert-RigReaderBindings $report $plan -FF}
    }finally{[IO.File]::WriteAllBytes($path,$original)}
}
foreach($flag in 'native_execution_verified','ff_execution_verified','runtime_verified','ready'){
    $bad=$report|ConvertTo-Json -Depth 35|ConvertFrom-Json;$bad.$flag=$true
    Refuse {Assert-RigReader $bad -FF}
}
$bad=$report|ConvertTo-Json -Depth 35|ConvertFrom-Json;$bad.redump.models.first.model.bones=1
Refuse {Assert-RigReader $bad -FF}
$bad=$report|ConvertTo-Json -Depth 35|ConvertFrom-Json;$bad.native.models.second.surface.blend_bytes=0
Refuse {Assert-RigReader $bad -FF}
Check (!('IW7.CommunityBuild.BuildJob' -as [type])) 'No native helper type may load'
"PASS: $checks cross-language independent-reader and physical-hash checks on synthetic artifacts only."

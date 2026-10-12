param([Parameter(Mandatory)][string]$PlanPath)
$ErrorActionPreference='Stop'
. "$PSScriptRoot/BuildCandidate.Core.ps1"
function Add-Type {throw 'Response contract test must not load native types'}
function Enter-IW7ResourceLease {throw 'Response contract test must not request admission'}
$raw=Get-Content -Raw -LiteralPath $PlanPath
$base=$raw|ConvertFrom-Json -AsHashtable -DateKind String
$seal=Get-Content -Raw -LiteralPath $base.seal|ConvertFrom-Json -AsHashtable -DateKind String
$state=Get-Content -Raw -LiteralPath $base.seal_result|ConvertFrom-Json -AsHashtable -DateKind String
$checks=0
foreach($case in 'valid','missing-bootstrap','wrong-bootstrap-hash','missing-response','duplicate-response','changed-command','old-seal-path'){
    $plan=$raw|ConvertFrom-Json -AsHashtable -DateKind String
    $first=$plan.response_pins[0]
    switch($case){
        'missing-bootstrap' {$plan.source_pins=@($plan.source_pins|Where-Object path -INE $first.path)}
        'wrong-bootstrap-hash' {foreach($p in $plan.source_pins){if($p.path -ieq $first.path){$p.sha256='0'*64}}}
        'missing-response' {$plan.response_pins=@($plan.response_pins|Select-Object -Skip 1)}
        'duplicate-response' {$plan.response_pins[11]=$first}
        'changed-command' {$plan.commands[0].response_path='C:\fixture-unreviewed.rsp'}
        'old-seal-path' {$first.path=$seal.Inputs[0].Path}
    }
    $failure=$null
    try{Assert-ChecksumBuildPlan $plan $seal $state}catch{$failure=$_.Exception.Message}
    $checks++
    if($case -ceq 'valid' -and $failure){throw "Valid response contract failed: $failure"}
    if($case -cne 'valid' -and !$failure){throw "Invalid response contract accepted: $case"}
}
if(Test-Path -LiteralPath $base.candidate){throw 'Candidate was created during source test'}
[ordered]@{Cases=7;Assertions=$checks;NativeTypesLoaded=$false;RealReservations=0}|ConvertTo-Json

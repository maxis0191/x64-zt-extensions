param([Parameter(Mandatory)][string]$PlanPath)
$ErrorActionPreference='Stop'
. "$PSScriptRoot/BuildCandidate.Core.ps1"
. "$PSScriptRoot/FlacBuild.Profile.ps1"
function Add-Type {throw 'Response contract test must not load native types'}
function Enter-IW7ResourceLease {throw 'Response contract test must not request admission'}
$raw=Get-Content -Raw -LiteralPath $PlanPath
$base=$raw|ConvertFrom-Json -AsHashtable -DateKind String
$seal=Get-Content -Raw -LiteralPath $base.seal|ConvertFrom-Json -AsHashtable -DateKind String
$state=Get-Content -Raw -LiteralPath $base.seal_result|ConvertFrom-Json -AsHashtable -DateKind String
$checks=0
$flac=$base.schema -ceq 'iw7.sound-flac-dump-build-plan/1'
$cases=@('valid','missing-bootstrap','wrong-bootstrap-hash','missing-response','duplicate-response','changed-command','old-seal-path')
if($flac){$cases+=@('missing-phase','phase-order','downgrade','extra-extension','duplicate-source','source-identity','source-guard','source-in-seal','review-identity','probe-args','probe-empty','probe-extra','probe-image')}
foreach($case in $cases){
    $plan=$raw|ConvertFrom-Json -AsHashtable -DateKind String
    $first=$plan.response_pins[0]
    switch($case){
        'missing-bootstrap' {$plan.source_pins=@($plan.source_pins|Where-Object path -INE $first.path)}
        'wrong-bootstrap-hash' {foreach($p in $plan.source_pins){if($p.path -ieq $first.path){$p.sha256='0'*64}}}
        'missing-response' {$plan.response_pins=@($plan.response_pins|Select-Object -Skip 1)}
        'duplicate-response' {$plan.response_pins[11]=$first}
        'changed-command' {$plan.commands[0].response_path='C:\fixture-unreviewed.rsp'}
        'old-seal-path' {$first.path=$seal.Inputs[0].Path}
        'missing-phase' {$plan.commands=@($plan.commands|Where-Object phase -CNE 'probe-flac-run')}
        'phase-order' {$plan.commands[6].phase='probe-flac-link'}
        'downgrade' {$plan.schema='iw7.sound-checksum-build-plan/1'}
        'extra-extension' {$plan.flac.extra=$true}
        'duplicate-source' {$plan.source_pins+=@($plan.flac.sources[0])}
        'source-identity' {$plan.flac.sources[0].sha256='0'*64}
        'source-guard' {$plan.source_pins=@($plan.source_pins|Where-Object path -INE $plan.flac.sources[0].path)}
        'source-in-seal' {$plan.flac.sources[0].path=$seal.Inputs[0].Path}
        'review-identity' {$plan.flac.review.sha256='0'*64}
        'probe-args' {$plan.commands[8].arguments=@('--skip')}
        'probe-empty' {$plan.commands[8].arguments=@()}
        'probe-extra' {$plan.commands[8].arguments=@('--verify-headers','--extra')}
        'probe-image' {$plan.commands[8].executable=$plan.commands[5].executable}
    }
    $failure=$null
    try{Assert-ChecksumBuildPlan $plan $seal $state}catch{$failure=$_.Exception.Message}
    $checks++
    if($case -ceq 'valid' -and $failure){throw "Valid response contract failed: $failure"}
    if($case -cne 'valid' -and !$failure){throw "Invalid response contract accepted: $case"}
}
if(Test-Path -LiteralPath $base.candidate){throw 'Candidate was created during source test'}
[ordered]@{Cases=$cases.Count;Assertions=$checks;Flac17=$flac;NativeTypesLoaded=$false;RealReservations=0}|ConvertTo-Json

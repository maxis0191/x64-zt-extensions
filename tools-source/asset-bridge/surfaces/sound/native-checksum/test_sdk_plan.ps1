param([Parameter(Mandatory)][string]$PlanPath)
$ErrorActionPreference='Stop'
. "$PSScriptRoot/BuildCandidate.Core.ps1"
function Add-Type {throw 'SDK contract test must not load native types'}
function Enter-IW7ResourceLease {throw 'SDK contract test must not request admission'}
$raw=Get-Content -Raw -LiteralPath $PlanPath
$base=$raw|ConvertFrom-Json -AsHashtable -DateKind String
$cases=@('valid','missing','duplicate','missing-bootstrap','duplicate-bootstrap','wrong-bootstrap-hash',
    'wrong-version','wrong-architecture','wrong-bytes','wrong-hash','old-seal','missing-sdk-path','extra-path','search-order')
foreach($case in $cases){
    $plan=$raw|ConvertFrom-Json -AsHashtable -DateKind String
    $first=$plan.sdk_tools[0]
    $sealed=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    switch($case){
        'missing' {$plan.sdk_tools=@($first)}
        'duplicate' {$plan.sdk_tools[1]=$first}
        'missing-bootstrap' {$plan.source_pins=@($plan.source_pins|Where-Object path -INE $first.path)}
        'duplicate-bootstrap' {$plan.source_pins+=@($first)}
        'wrong-bootstrap-hash' {foreach($p in $plan.source_pins){if($p.path -ieq $first.path){$p.sha256='0'*64}}}
        'wrong-version' {$first.path=$first.path.Replace('26100','22621')}
        'wrong-architecture' {$first.path=$first.path.Replace('x64','x86')}
        'wrong-bytes' {$first.bytes++}
        'wrong-hash' {$first.sha256='0'*64}
        'old-seal' {[void]$sealed.Add($first.path)}
        'missing-sdk-path' {$plan.environment.PATH=$plan.environment.PATH.Replace(';C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64','')}
        'extra-path' {$plan.environment.PATH+=';C:\unreviewed'}
        'search-order' {$parts=$plan.environment.PATH.Split(';');$plan.environment.PATH=$parts[1]+';'+$parts[0]+';'+$parts[2]}
    }
    $failure=$null
    try{Assert-ChecksumBuildSdkTools $plan $sealed}catch{$failure=$_.Exception.Message}
    if($case -ceq 'valid' -and $failure){throw "Valid SDK contract failed: $failure"}
    if($case -cne 'valid' -and !$failure){throw "Invalid SDK contract accepted: $case"}
}
if(Test-Path -LiteralPath $base.candidate){throw 'SDK contract test created candidate'}
[ordered]@{Cases=$cases.Count;NativeTypesLoaded=$false;RealReservations=0}|ConvertTo-Json

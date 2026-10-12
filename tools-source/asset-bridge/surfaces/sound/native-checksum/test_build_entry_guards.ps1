param([Parameter(Mandatory)][string]$PlanPath)
$ErrorActionPreference='Stop'
$temp=Join-Path ([IO.Path]::GetTempPath()) ('sound-build-entry-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($temp)|Out-Null
$global:SoundBuildEntryFixture=@{Denied=0;JsonReads=0;PlanOutput=0;Paths=@{}}
function AssertFixtureDenied([string]$Name) {
    $path=$global:SoundBuildEntryFixture.Paths[$Name];$stream=$null;$denied=$false
    try{$stream=[IO.File]::Open($path,'Open','ReadWrite','ReadWrite')}
    catch [IO.IOException]{$denied=$true}
    finally{if($stream){$stream.Dispose()}}
    if(!$denied){throw "Bootstrap write interval was open: $Name"}
    $global:SoundBuildEntryFixture.Denied++
}
try {
    $plan=Get-Content -Raw -LiteralPath $PlanPath|ConvertFrom-Json -AsHashtable -DateKind String
    foreach($name in 'Build-ChecksumCandidate.ps1','BuildCandidate.Core.ps1','BuildReceipt.Core.ps1','build_worker.py','build_contract.py'){
        $from=Join-Path $PSScriptRoot $name;$to=Join-Path $temp $name
        [IO.File]::WriteAllBytes($to,[IO.File]::ReadAllBytes($from))
        $global:SoundBuildEntryFixture.Paths[$name]=$to
        foreach($pin in $plan.source_pins){if($pin.path -ieq $from){$pin.path=$to;$pin.bytes=(Get-Item $to).Length;$pin.sha256=(Get-FileHash $to).Hash.ToLowerInvariant()}}
    }
    $plan.worker=$global:SoundBuildEntryFixture.Paths['build_worker.py']
    $copy=Join-Path $temp 'plan.json';$global:SoundBuildEntryFixture.Paths['plan']=$copy
    [IO.File]::WriteAllText($copy,($plan|ConvertTo-Json -Depth 30))
    $hash=(Get-FileHash -LiteralPath $copy).Hash.ToLowerInvariant()
    function ConvertFrom-Json {
        param([string]$InputObject,[switch]$AsHashtable,[string]$DateKind,[int]$Depth)
        $global:SoundBuildEntryFixture.JsonReads++
        if($global:SoundBuildEntryFixture.JsonReads -eq 1){
            foreach($name in 'plan','Build-ChecksumCandidate.ps1','BuildCandidate.Core.ps1','BuildReceipt.Core.ps1'){AssertFixtureDenied $name}
        }else{foreach($name in 'build_worker.py','build_contract.py'){AssertFixtureDenied $name}}
        Microsoft.PowerShell.Utility\ConvertFrom-Json -InputObject $InputObject -AsHashtable:$AsHashtable -DateKind $DateKind -Depth $Depth
    }
    function ConvertTo-Json {
        param([Parameter(ValueFromPipeline)]$InputObject)
        process{
            $global:SoundBuildEntryFixture.PlanOutput++
            foreach($name in $global:SoundBuildEntryFixture.Paths.Keys){AssertFixtureDenied $name}
            Microsoft.PowerShell.Utility\ConvertTo-Json -InputObject $InputObject
        }
    }
    function Add-Type {throw 'Default Plan attempted native type compilation'}
    function Enter-IW7ResourceLease {throw 'Default Plan requested admission'}
    function Get-CimInstance {throw 'Default Plan queried native processes'}
    function Start-Process {throw 'Default Plan started a child'}
    function Get-FileHash {throw 'Default Plan hashed a reusable input'}
    $result=& $global:SoundBuildEntryFixture.Paths['Build-ChecksumCandidate.ps1'] -PlanPath $copy -PlanSHA256 $hash
    if($global:SoundBuildEntryFixture.Denied -ne 14 -or $global:SoundBuildEntryFixture.JsonReads -ne 3 -or $global:SoundBuildEntryFixture.PlanOutput -ne 1){throw 'Expected guarded intervals not observed'}
    if(Test-Path -LiteralPath $plan.candidate){throw 'Default Plan created native candidate'}
    foreach($path in $global:SoundBuildEntryFixture.Paths.Values){$s=[IO.File]::Open($path,'Open','ReadWrite','ReadWrite');$s.Dispose()}
    if(('IW7.CommunityBuild.BuildJob' -as [type]) -or ('IW7.AnimationRig.JobMembers' -as [type])){throw 'Default Plan loaded native type'}
    Write-Output ('Default Plan passed; 14 denied writes across parse/output, 6 handles released afterward, no native types/admission/output.')
}finally{
    $resolved=[IO.Path]::GetFullPath($temp);$parent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$resolved.StartsWith($parent,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -notlike 'sound-build-entry-*'){throw 'Unsafe fixture cleanup path'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
    Remove-Variable -Name SoundBuildEntryFixture -Scope Global -ErrorAction SilentlyContinue
}

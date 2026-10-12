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
    $flac=$plan.schema -ceq 'iw7.sound-flac-dump-build-plan/1'
    $copies=@('Build-ChecksumCandidate.ps1','BuildCandidate.Core.ps1','BuildReceipt.Core.ps1','build_worker.py','build_contract.py')
    if($flac){$copies+=@('FlacBuild.Profile.ps1','flac_build_profile.py','response_revision.py')}
    foreach($name in $copies){
        $from=Join-Path $PSScriptRoot $name;$to=Join-Path $temp $name
        [IO.File]::WriteAllBytes($to,[IO.File]::ReadAllBytes($from))
        if($flac -and $name -ceq 'Build-ChecksumCandidate.ps1'){
            # Instrument the copied entry before each actual open/hash. The
            # production functions and default Plan control flow stay intact.
            $text=[IO.File]::ReadAllText($to)
            foreach($hook in @(
                @('function Open-ChecksumBootstrap([string]$Path,[long]$Maximum) {','AssertFixtureSourceOnly $Path'),
                @('function Get-ChecksumBootstrapHash($Stream) {','AssertFixtureSourceOnly $Stream.Name'))){
                if(($text.Split($hook[0],[StringSplitOptions]::None)).Count -ne 2){throw 'Unique source guard hook required'}
                $text=$text.Replace($hook[0],$hook[0]+"`n    "+$hook[1])
            }
            [IO.File]::WriteAllText($to,$text)
        }
        $global:SoundBuildEntryFixture.Paths[$name]=$to
        foreach($pin in $plan.source_pins){if($pin.path -ieq $from){$pin.path=$to;$pin.bytes=(Get-Item $to).Length;$pin.sha256=(Get-FileHash $to).Hash.ToLowerInvariant()}}
    }
    $plan.worker=$global:SoundBuildEntryFixture.Paths['build_worker.py']
    if(@($plan.response_pins).Count -in 12,14){
        $pin=$plan.response_pins[0];$from=$pin.path;$to=Join-Path $temp 'reviewed-response.rsp'
        [IO.File]::WriteAllBytes($to,[IO.File]::ReadAllBytes($from))
        $pin.path=$to
        foreach($source in $plan.source_pins){if($source.path -ieq $from){$source.path=$to}}
        foreach($command in $plan.commands){if($command.response_path -ieq $from){$command.response_path=$to;$command.arguments=@('@'+$to)}}
        $global:SoundBuildEntryFixture.Paths['reviewed-response.rsp']=$to
    }
    # Extra copies exercise the binary-source guards without requesting write
    # access to installed SDK files. The exact production SDK pins stay intact.
    foreach($pin in $(if($flac){@()}else{$plan.sdk_tools})){
        $name='fixture-'+[IO.Path]::GetFileName($pin.path);$to=Join-Path $temp $name
        [IO.File]::WriteAllBytes($to,[IO.File]::ReadAllBytes($pin.path))
        $plan.source_pins+=@(@{path=$to;bytes=$pin.bytes;sha256=$pin.sha256})
        $global:SoundBuildEntryFixture.Paths[$name]=$to
    }
    $copy=Join-Path $temp 'plan.json';$global:SoundBuildEntryFixture.Paths['plan']=$copy
    [IO.File]::WriteAllText($copy,($plan|ConvertTo-Json -Depth 30))
    $hash=(Get-FileHash -LiteralPath $copy).Hash.ToLowerInvariant()
    $global:SoundBuildEntryFixture.SourceChecks=0
    function AssertFixtureSourceOnly([string]$Path){
        if([IO.Path]::GetExtension($Path).ToLowerInvariant() -notin @('.ps1','.cs','.py','.cpp','.hpp','.h','.json','.rsp')){
            throw 'FLAC default Plan attempted a binary payload open/hash'
        }
        $global:SoundBuildEntryFixture.SourceChecks++
    }
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
    $expected=8+$global:SoundBuildEntryFixture.Paths.Count
    if($global:SoundBuildEntryFixture.Denied -ne $expected -or $global:SoundBuildEntryFixture.JsonReads -ne 3 -or $global:SoundBuildEntryFixture.PlanOutput -ne 1){throw 'Expected guarded intervals not observed'}
    if(Test-Path -LiteralPath $plan.candidate){throw 'Default Plan created native candidate'}
    foreach($path in $global:SoundBuildEntryFixture.Paths.Values){$s=[IO.File]::Open($path,'Open','ReadWrite','ReadWrite');$s.Dispose()}
    if(('IW7.CommunityBuild.BuildJob' -as [type]) -or ('IW7.AnimationRig.JobMembers' -as [type])){throw 'Default Plan loaded native type'}
    if($flac -and $global:SoundBuildEntryFixture.SourceChecks -lt 100){throw 'FLAC source-only open/hash hooks did not cover bootstrap'}
    Write-Output ("Default Plan passed; $expected denied writes across parse/output, $($global:SoundBuildEntryFixture.Paths.Count) handles released afterward, no native types/admission/output.")
    if($flac){Write-Output ("FLAC17: $($global:SoundBuildEntryFixture.SourceChecks) source-only open/hash checks; no SDK/binary payload opened or hashed.")}
}finally{
    $resolved=[IO.Path]::GetFullPath($temp);$parent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$resolved.StartsWith($parent,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -notlike 'sound-build-entry-*'){throw 'Unsafe fixture cleanup path'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
    Remove-Variable -Name SoundBuildEntryFixture -Scope Global -ErrorAction SilentlyContinue
}

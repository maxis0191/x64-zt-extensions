# V3 source contracts and synthetic metadata only. No native candidate or lease.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
. (Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7PrepatchReferenceV2.Profile.ps1')
$script:checks=0
function Check([bool]$Value,[string]$Why){if(!$Value){throw $Why};$script:checks++}
function Refuses([scriptblock]$Body,[string]$Pattern='.'){
    $caught=$false;try{& $Body}catch{$caught=$true;Check ($_.Exception.Message -match $Pattern) ('Unexpected refusal: '+$_.Exception.Message)}
    Check $caught 'Expected fixed-contract refusal'
}
function Clone($Value){$text=$Value|ConvertTo-Json -Depth 20;if((Get-Command ConvertFrom-Json).Parameters.ContainsKey('DateKind')){return ($text|ConvertFrom-Json -Depth 20 -DateKind String)};$text|ConvertFrom-Json -Depth 20}
$tempBase=[IO.Path]::GetFullPath([IO.Path]::GetTempPath());$root=Join-Path $tempBase ('t7-link-v3-source-tests-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($root)|Out-Null
function New-BuildFixture {
    $profile=[ordered]@{Name='t7-prepatch-link-v3';Option='-t7-prepatch-link-v3';ArgumentCount=2;Report='t7-prepatch-link-v3.local.json';ObservationSchema='iw7.t7-prepatch-link-observation/3'};$pins=@()
    foreach($row in @(
        @('Helper',15827,'cf839e18a68adb4ed3aae82d683ef110ab595fa8c172584e47ca4d11bb8db48d'),@('Wiring',2236,'66f70ca5a979745288232d76496a339e08d639ddf34560aada6e6b63c5bcffa1'),
        @('BaseHelper',15785,'0309b81376d3708cc8de43d297b43fbdfbdd535120e0ad054c157735c2c7457a'),@('BaseWiring',3665,'89f3f26699f1240400c4bd96f2987963374658e55a8501cab7dc2543a84ceace'),
        @('BaseBuildPlan',292575,'422e79898fa2b16defc8193182fe146e2db5d73aeb4516c2bd2aaf87c409c4de'),@('BaseBuildReceipt',26199,'af6beecf7a8892e16266a7641d2799f665f86fa8ad7c40c61561b782534f7897'),
        @('BaseV2BuildPlan',303783,'0aca63cb09e8ecfc96dee34e1fdf94f8cb66e400f8a190ffdefd38bec3a2c549'),@('BaseV2Main',14524,'e719365c5a7f407218a7218bd9c7090421934042c34a9f163d9a8e3d42ee1e28'),
        @('PreparedMain',14469,'84cde2924df0a0553dd2cddb0ca173aed54af43d6874b06718c01d1a6cec4989'))){
        $path=Join-Path $root ($row[0]+'.source');$profile[$row[0]]=[pscustomobject]@{Path=$path;Bytes=$row[1];SHA256=$row[2]};$pins+=[pscustomobject]@{Path=$path;Bytes=$row[1];SHA256=$row[2];IsText=$true}
    }
    $marker=[pscustomobject]@{Schema='iw7.t7-prepatch-link-build/3';SourceProfile='t7-prepatch-link-v3';RetainedMainBytes=12854;RetainedMainSHA256='40de5fda829cec32a5d75359f58e69c84db7d8ee54f198cf6befa2a6ebe6f86e';BaseMainBytes=14524;BaseMainSHA256='e719365c5a7f407218a7218bd9c7090421934042c34a9f163d9a8e3d42ee1e28';MainBytes=14469;MainSHA256='84cde2924df0a0553dd2cddb0ca173aed54af43d6874b06718c01d1a6cec4989';HelperBytes=15827;HelperSHA256='cf839e18a68adb4ed3aae82d683ef110ab595fa8c172584e47ca4d11bb8db48d'}
    [pscustomobject]@{Plan=[pscustomobject]@{Bindings=$pins};Build=[pscustomobject]@{Schema='iw7.t7-minimal-build-plan/1';SourceCommit='fab935826c898806855376662a8a03317b3ad8f1';BuildProfile=[pscustomobject]$profile;ReuseCompile=[pscustomobject]@{RecompiledMain=$true;PrepatchLinkV3=$marker};Stages=@(@{Name='main'},@{Name='link'})}}
}
try{
    $protocol=Get-T7ReferenceProtocol 't7-prepatch-link-v3';Check ($protocol.Option -ceq '-t7-prepatch-link-v3' -and $protocol.PlanSchema -ceq 'iw7.t7-prepatch-link-plan/3' -and $protocol.Report -ceq 't7-prepatch-link-v3.local.json') 'V3 protocol differs'
    Refuses {Get-T7ReferenceProtocol @('t7-prepatch-link-v3')} 'scalar';Refuses {Get-T7ReferenceProtocol 'T7-prepatch-link-v3'} 'Unknown';Refuses {Get-T7ReferenceProtocol 't7-prepatch-link-v4'} 'Unknown'
    $f=New-BuildFixture;Assert-T7RefV2Build $f.Plan $f.Build $null $protocol.Name;$script:checks++
    Refuses {Assert-T7RefV2Build $f.Plan $f.Build} 'fields'
    foreach($field in 'Name','Option','Report','ObservationSchema'){$f=New-BuildFixture;$f.Build.BuildProfile.$field=@($f.Build.BuildProfile.$field);Refuses {Assert-T7RefV2Build $f.Plan $f.Build $null $protocol.Name} 'scalar'}
    foreach($field in 'Schema','SourceProfile','RetainedMainSHA256','BaseMainSHA256','MainSHA256','HelperSHA256'){$f=New-BuildFixture;$f.Build.ReuseCompile.PrepatchLinkV3.$field=@($f.Build.ReuseCompile.PrepatchLinkV3.$field);Refuses {Assert-T7RefV2Build $f.Plan $f.Build $null $protocol.Name} 'scalar'}
    foreach($role in 'Helper','Wiring','BaseHelper','BaseWiring','BaseBuildPlan','BaseBuildReceipt','BaseV2BuildPlan','BaseV2Main','PreparedMain'){
        $f=New-BuildFixture;$f.Build.BuildProfile.$role.Bytes++;Refuses {Assert-T7RefV2Build $f.Plan $f.Build $null $protocol.Name} 'pin'
        $f=New-BuildFixture;$f.Plan.Bindings|Where-Object Path -CEQ $f.Build.BuildProfile.$role.Path|ForEach-Object {$_.IsText=$false};Refuses {Assert-T7RefV2Build $f.Plan $f.Build $null $protocol.Name} 'binding'
    }
    foreach($marker in 'PrepatchReferenceV2','ZombiesObservationC','ZombiesAddObservationC2','MaterialParts'){$f=New-BuildFixture;$f.Build.ReuseCompile|Add-Member NoteProperty $marker @{};Refuses {Assert-T7RefV2Build $f.Plan $f.Build $null $protocol.Name} 'mix'}
    $f=New-BuildFixture;Refuses {Assert-T7RefV2Build $f.Plan $f.Build $null @($protocol.Name)} 'scalar'
    $pending=[pscustomobject]@{CandidateSource=$null;CandidateSHA256=$null;BuildReceipt=$null;ExpectedBuildReceiptSHA256=$null;BuildClosedPins=$null;CandidateBytes=0}
    Assert-T7LinkV3PendingCandidate $pending;$script:checks++
    foreach($field in 'CandidateSource','CandidateSHA256','BuildReceipt','ExpectedBuildReceiptSHA256','BuildClosedPins'){$bad=Clone $pending;$bad.$field='unqualified';Refuses {Assert-T7LinkV3PendingCandidate $bad} 'null placeholders'}
    $bad=Clone $pending;$bad.CandidateBytes=1;Refuses {Assert-T7LinkV3PendingCandidate $bad} 'integer'
    $startPlan=[pscustomobject]@{Image=(Join-Path $root $protocol.Image);WorkingDirectory=$root;RunRoot=$root}
    $start=New-T7RefV2Start $startPlan $protocol.Name;Check ($start.ArgumentList.Count -eq 1 -and $start.ArgumentList[0] -ceq '-t7-prepatch-link-v3' -and $start.Environment.Count -eq 9 -and !$start.UseShellExecute) 'Actual V3 native arguments/environment differ'
    $runner=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Run-T7PrepatchReferenceV2.ps1') -Raw
    $gate=$runner.IndexOf('if($SourceOnly -and $Run)')
    Check ($gate -ge 0 -and $gate -lt $runner.IndexOf('Enter-IW7ResourceLease')) 'Source-only review can admit native work'
    [ordered]@{Schema='iw7.t7-link-v3-consumer-source-tests/3';Checks=$script:checks;Status='Passed';NativeExecuted=$false;LeaseAcquired=$false;OpaqueInputsRead=$false;CPPQualified=$false}|ConvertTo-Json
}finally{
    $resolved=[IO.Path]::GetFullPath($root)
    if(!$resolved.StartsWith($tempBase,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -cnotmatch '^t7-link-v3-source-tests-[0-9a-f]{32}$'){throw 'Refuse unverified test cleanup target'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
}

# Execute the real post-admission prelude against synthetic file metadata only.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$sourceRepo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
. (Join-Path $sourceRepo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7PrepatchReferenceV2.Profile.ps1')
$script:checks=0
function Check([bool]$Value,[string]$Why){if(!$Value){throw $Why};$script:checks++}
function Refuses([scriptblock]$Body){$caught=$false;try{& $Body}catch{$caught=$true;Check ($_.Exception.Message -match 'create-only') 'Wrong preexisting-state refusal'};Check $caught 'Expected create-only refusal'}
$tempBase=[IO.Path]::GetFullPath([IO.Path]::GetTempPath());$repo=Join-Path $tempBase ('t7-ref-v2-publication-tests-'+[guid]::NewGuid().ToString('N'))
$run=Join-Path $repo 'runtime/t7-prepatch-reference-fixture';$work=Join-Path $run 'work';$evidence=Join-Path $run 'evidence';$temp=Join-Path $run 'temp'
$pins=[Collections.Generic.List[object]]::new()
function Metadata-File([string]$Path,[long]$Bytes,[string]$Hash,[bool]$Text){
    $stream=[IO.FileStream]::new($Path,'CreateNew','Write','Read');try{$stream.SetLength($Bytes)}finally{$stream.Dispose()}
    $pins.Add([pscustomobject]@{Path=$Path;Bytes=$Bytes;SHA256=$Hash;IsText=$Text})
}
try{
    foreach($path in @($repo,$run,$work,$evidence,$temp)){[IO.Directory]::CreateDirectory($path)|Out-Null}
    $engine=Join-Path $repo 'engine.fixture';$steam=Join-Path $repo 'steam.fixture';$job=Join-Path $repo 'job.fixture';$hostImage=Join-Path $repo 'host.fixture';$recipe=Join-Path $repo 'recipe.fixture';$index=Join-Path $repo 'index.fixture'
    foreach($path in @($engine,(Join-Path $work 'BlackOps3_UnrankedDedicatedServer.exe'))){Metadata-File $path 21737352 '3df511d71e3690b14517379783bbfb713f6fe2ed2f2e73b445b4878216686156' $false}
    foreach($path in @($steam,(Join-Path $work 'steam_api64.dll'))){Metadata-File $path 235600 '71af8666392acad2080a816b9f1196fe9ccb950e1db8a549f8312c4d231f55a8' $false}
    Metadata-File $job 1 '5f613ebb83019dbf4bfa4f6a93c5329098343729b70acc2cfa70aa8b64f195f8' $false
    Metadata-File $hostImage 1 ('a'*64) $false
    Metadata-File $recipe 303783 '0aca63cb09e8ecfc96dee34e1fdf94f8cb66e400f8a190ffdefd38bec3a2c549' $true
    Metadata-File $index 1867 'cfb6f523336ad0fd163c2ffcdeaf4ff5b31b83fc5fa17321662bce89c61353d0' $true
    $mainImage=Join-Path $repo 'main/iw7-paris-voice.exe';$bank=Join-Path ([IO.Path]::GetDirectoryName($mainImage)) 'mods/paris_beta/bank'
    $plan=[pscustomobject]@{Schema='iw7.t7-prepatch-reference-plan/2';CandidateProfile='t7-prepatch-reference-v2';ObservationSchema='iw7.t7-prepatch-reference-observation/2';ReportName='t7-prepatch-reference-v2.local.json';Runner=$PSCommandPath;RunRoot=$run;WorkingDirectory=$work;StageRoot=$evidence;Image=(Join-Path $work 't7-zonetool-prepatch-reference-v2.exe');EngineSource=$engine;SteamSource=$steam;JobAssembly=$job;HostImage=$hostImage;BuildPlan=$recipe;ExpectedBuildPlanSHA256='0aca63cb09e8ecfc96dee34e1fdf94f8cb66e400f8a190ffdefd38bec3a2c549';BuildClosedPins=$index;PhysicalBytes=6GB;CommitBytes=8GB;GroupDeadlineSeconds=200;DeadlineSeconds=120;MutableOutputLimitBytes=64MB;MetadataReserveBytes=64KB;CleanupSeconds=5;ReportLimitBytes=256KB;LogLimitBytes=1MB;RetryAuthorized=$false;CandidateBytes=0;OutputLimitBytes=(64MB+21737352+235600);Arguments=@('-t7-prepatch-reference-v2');MainBaseline='Stopped';PreservedMain=[pscustomobject]@{PID=123;CreatedUtc='2026-10-14T00:00:00.0000000Z';Image=$mainImage};MainFiles=@((Get-T7RefV2Metadata $mainImage));BankSnapshot=(Get-T7RefV2BankSnapshot $bank);Bindings=@($pins)}
    $shell=$hostImage;$PlanSHA256=('b'*64);$state=[ordered]@{LeaseToken='synthetic'};$context=[pscustomobject]@{Guards=[Collections.Generic.List[object]]::new();Lease=$null;Closed=$true}
    $runner=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Run-T7PrepatchReferenceV2.ps1') -Raw
    $anchor='    $state.LeaseToken=$context.Lease.Token';$start=$runner.IndexOf($anchor)+$anchor.Length;$finish=$runner.IndexOf('    Enable-T7RefV2RuntimeProfile',$start)
    Check ($start -ge $anchor.Length -and $finish -gt $start) 'Actual post-admission prelude missing'
    $prelude=$runner.Substring($start,$finish-$start)
    $validation='    Assert-T7RefV2Plan $plan $repo $PSCommandPath'
    Check ($prelude.IndexOf($validation) -ge 0 -and $prelude.IndexOf($validation) -lt $prelude.IndexOf('$taskStartStream=')) 'Final validation does not precede real publication'
    Check ([regex]::Matches($prelude,[regex]::Escape($validation)).Count -eq 1) 'Repeated create-only validation in prelude'
    Check ($prelude.Contains("'CreateNew','Write','Read'")) 'Atomic create-only publication lost'
    Check (!$prelude.Contains('Enter-IW7ResourceLease') -and !$prelude.Contains('Invoke-H1OwnedStage')) 'Test would admit/start native work'
    $preludePath=Join-Path $repo 'actual-prelude.ps1'
    [IO.File]::WriteAllText($preludePath,$prelude,[Text.UTF8Encoding]::new($false));$plan.Runner=$preludePath
    & $preludePath
    Check ((Test-Path -LiteralPath ($run+'.host-start.json')) -and [AppDomain]::CurrentDomain.GetData('IW7.T7PrepatchReferenceV2')) 'Actual prelude did not publish its own host marker'
    Refuses {Assert-T7RefV2Plan $plan $repo $preludePath}
    Remove-Item -LiteralPath ($run+'.host-start.json')
    [AppDomain]::CurrentDomain.SetData('IW7.T7PrepatchReferenceV2',$null)
    # Moving only the final validation back after publication reproduces the P1.
    $badPrelude=$prelude.Replace($validation,'')+"`n"+$validation
    $badPath=Join-Path $repo 'old-order-prelude.ps1'
    [IO.File]::WriteAllText($badPath,$badPrelude,[Text.UTF8Encoding]::new($false));$plan.Runner=$badPath
    Refuses {& $badPath}
    Check (Test-Path -LiteralPath ($run+'.host-start.json')) 'Old-order failure did not follow publication'
    [ordered]@{Schema='iw7.t7-reference-v2-host-publication-source-test/2';Checks=$script:checks;Status='Passed';ActualRunnerPreludeExecuted=$true;NativeExecuted=$false;LeaseAcquired=$false;OpaqueInputsRead=$false;SyntheticMetadataOnly=$true}|ConvertTo-Json
}finally{
    [AppDomain]::CurrentDomain.SetData('IW7.T7PrepatchReferenceV2',$null)
    $resolved=[IO.Path]::GetFullPath($repo)
    if(!$resolved.StartsWith($tempBase,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -cnotmatch '^t7-ref-v2-publication-tests-[0-9a-f]{32}$'){throw 'Refuse unverified fixture cleanup target'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
}

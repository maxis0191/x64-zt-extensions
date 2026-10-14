# Synthetic source/report/lifecycle checks. No game, provider, process or lease.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
. (Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7PrepatchReferenceV2.Profile.ps1')
$script:checks=0
function Check([bool]$Value,[string]$Why){if(!$Value){throw $Why};$script:checks++}
function Refuses([scriptblock]$Body,[string]$Pattern='V2'){
    $caught=$false;try{& $Body}catch{$caught=$true;Check ($_.Exception.Message -match $Pattern) ('Unexpected refusal: '+$_.Exception.Message)}
    Check $caught ('Expected refusal: '+$Body.ToString())
}
function Clone($Value){$text=$Value|ConvertTo-Json -Depth 20;if((Get-Command ConvertFrom-Json).Parameters.ContainsKey('DateKind')){return ($text|ConvertFrom-Json -Depth 20 -DateKind String)};$text|ConvertFrom-Json -Depth 20}
$tempBase=[IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$root=Join-Path $tempBase ('t7-ref-v2-source-tests-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($root)|Out-Null
$module=Join-Path $root 'BlackOps3_UnrankedDedicatedServer.exe'
$identity=[pscustomobject]@{PID=123;CreatedUtc='2026-10-14T00:00:00.0000000Z'}
function New-Report {
    [pscustomobject]@{schema='iw7.t7-prepatch-reference-observation/2';phase='first_dpi_before_component_post_unpack';pid=123;thread_id=321;
        creation_filetime=([datetime]::Parse($identity.CreatedUtc).ToFileTimeUtc().ToString());module_path=$module.Replace('\','/');module_base='0x140000000';base_matches_source=$true;
        source_base='0x140000000';read_limit=4MB;report_limit=256KB;requested_bytes=3000;returned_bytes=3000;window_count=2;window_observations=2;
        capture_complete=$true;status='captured_for_offline_review';boot_authorized=$false;abi_proven=$false;runtime_compatibility_proven=$false;pe=@{size_of_image=0x200000};pdata_records=2;
        windows=@(for($i=0;$i -lt 2;$i++){
            $rva=@(0x1D4600,0x1DB2B0)[$i];$length=@(2048,256)[$i];$begin=0x140000000L+$rva
            [pscustomobject]@{site=@('DB_AddXAsset','Load_SimpleAsset')[$i];rva=$rva;window_rva=$rva;window_bytes=$length;bytes_hex=('00'*$length);
                regions=@([pscustomobject]@{base=('0x{0:x}' -f $begin);size=$length;allocation_base='0x140000000';state=4096;protect=64;allocation_protect=64;type=16777216});
                runtime_function=[pscustomobject]@{begin_rva=$rva;end_rva=$rva+$length;unwind_rva=4096;unwind_header_hex='01000000';unwind_format_validated=$false}}
        })}
}
function New-BuildFixture {
    $profile=[ordered]@{Name='t7-prepatch-reference-v2';Option='-t7-prepatch-reference-v2';ArgumentCount=2;Report='t7-prepatch-reference-v2.local.json';ObservationSchema='iw7.t7-prepatch-reference-observation/2'}
    $pins=@()
    foreach($row in @(
        @('Helper',15785,'0309b81376d3708cc8de43d297b43fbdfbdd535120e0ad054c157735c2c7457a'),@('Wiring',3665,'89f3f26699f1240400c4bd96f2987963374658e55a8501cab7dc2543a84ceace'),
        @('BaseHelper',16281,'a9f458d2783c845af6958c896bda07fa4b92a5ea23a14c9e5d1201fe234a2018'),@('BaseWiring',3078,'162763ab503a7971bc56753e3aba9fc1c76bf181881f9bddf45718456467e129'),
        @('BaseBuildPlan',292575,'422e79898fa2b16defc8193182fe146e2db5d73aeb4516c2bd2aaf87c409c4de'),@('BaseBuildReceipt',26199,'af6beecf7a8892e16266a7641d2799f665f86fa8ad7c40c61561b782534f7897'),
        @('PreparedMain',14524,'e719365c5a7f407218a7218bd9c7090421934042c34a9f163d9a8e3d42ee1e28'))){
        $path=Join-Path $root ($row[0]+'.source');$profile[$row[0]]=[pscustomobject]@{Path=$path;Bytes=$row[1];SHA256=$row[2]};$pins+=[pscustomobject]@{Path=$path;Bytes=$row[1];SHA256=$row[2];IsText=$true}
    }
    $marker=[pscustomobject]@{Schema='iw7.t7-prepatch-reference-build/2';SourceProfile='t7-prepatch-reference-v2';RetainedMainBytes=12854;RetainedMainSHA256='40de5fda829cec32a5d75359f58e69c84db7d8ee54f198cf6befa2a6ebe6f86e';BaseMainBytes=13160;BaseMainSHA256='55081db20863f291f4f1fea8c1c995995e5e548b56acf043201fbb2e361f3934';MainBytes=14524;MainSHA256='e719365c5a7f407218a7218bd9c7090421934042c34a9f163d9a8e3d42ee1e28';HelperBytes=15785;HelperSHA256='0309b81376d3708cc8de43d297b43fbdfbdd535120e0ad054c157735c2c7457a'}
    $candidate=Join-Path $root 'synthetic-candidate.exe'
    $plan=[pscustomobject]@{Bindings=$pins;ExpectedBuildPlanSHA256=('a'*64);CandidateSource=$candidate;CandidateBytes=21777408;CandidateSHA256='f11c683b5379e08cca4e881a7a412a2a8a45b5f872acb690ac62218fce6717f5'}
    $build=[pscustomobject]@{Schema='iw7.t7-minimal-build-plan/1';SourceCommit='fab935826c898806855376662a8a03317b3ad8f1';BuildProfile=[pscustomobject]$profile;ReuseCompile=[pscustomobject]@{RecompiledMain=$true;PrepatchReferenceV2=$marker};Stages=@(@{Name='main'},@{Name='link'})}
    $receipt=[pscustomobject]@{Schema='iw7.t7-minimal-build/1';Status='Passed';PlanSHA256=('a'*64);BuildProfile=[pscustomobject]$profile;InputsReverified=$true;TreeClosureConfirmed=$true;LeaseReleased=$true;Quarantined=$false;CandidateExecuted=$false;Ready=$false;
        Stages=@(for($i=0;$i -lt 2;$i++){[pscustomobject]@{Name=@('main','link')[$i];ExitCode=0;TreeClosureConfirmed=$true;CompilerTelemetry=[pscustomobject]@{Completed=$true;AfterStop=[pscustomobject]@{RootExited=$true;RootExitCode=0;ActiveProcesses=0};AfterStopMembers=[pscustomobject]@{AssignedCount=0;ListedCount=0;Members=@()}};Artifacts=$(if($i){@([pscustomobject]@{Path=$candidate;Bytes=21777408;SHA256=$plan.CandidateSHA256})}else{@()})}})}
    [pscustomobject]@{Plan=$plan;Build=$build;Receipt=$receipt}
}
function New-MainFixture {
    $image=Join-Path $root 'main\iw7-paris-voice.exe';$bank=Join-Path ([IO.Path]::GetDirectoryName($image)) 'mods/paris_beta/bank'
    [pscustomobject]@{MainBaseline='Stopped';PreservedMain=[pscustomobject]@{PID=19932;CreatedUtc='2026-10-12T16:21:08.1996220Z';Image=$image};MainFiles=@((Get-T7RefV2Metadata $image));BankSnapshot=(Get-T7RefV2BankSnapshot $bank)}
}
$script:mockProcesses=@();$script:mockPorts=@()
function Get-IW7ResourceProcesses {$script:mockProcesses}
function Get-NetUDPEndpoint {param($ErrorAction);$script:mockPorts}
try {
    Check ((Get-T7RefV2Outcome (New-Report) $identity 0 $module) -ceq 'CaptureComplete') 'Complete two-window report refused.'
    Check ((Get-T7RefV2Outcome $null $identity 2 $module) -ceq 'NoCapture') 'NoCapture changed.'
    $partial=New-Report;$partial.capture_complete=$false;$partial.status='incomplete_stop';$partial.windows=@();$partial.window_observations=0
    Check ((Get-T7RefV2Outcome $partial $identity 2 $module) -ceq 'CapturePartial') 'Partial report refused.'
    Refuses {Get-T7RefV2Outcome $partial $identity 0 $module}
    foreach($field in 'schema','phase','source_base','status','module_path','module_base','creation_filetime'){
        $report=New-Report;$report.$field=@($report.$field);Refuses {Get-T7RefV2Outcome $report $identity 0 $module} 'scalar string'
    }
    foreach($field in 'pid','thread_id','read_limit','report_limit','window_count','window_observations','requested_bytes','returned_bytes'){
        foreach($kind in 'array','string'){$report=New-Report;if($kind -ceq 'array'){$report.$field=@($report.$field)}else{$report.$field=[string]$report.$field};Refuses {Get-T7RefV2Outcome $report $identity 0 $module} 'scalar integer'}
    }
    foreach($change in @(
        {param($r)$r.window_count=12},{param($r)$r.windows[0].rva++},{param($r)$r.windows[1].window_bytes=257},{param($r)$r.windows[0].bytes_hex='00'},
        {param($r)$r.windows[0].regions[0].allocation_base='0x150000000'},{param($r)$r.windows[0].regions[0].protect=0x101},{param($r)$r.windows[0].regions[0].size=1},
        {param($r)$r.windows[0].runtime_function.end_rva=$r.windows[0].rva},{param($r)$r.windows[0].runtime_function.unwind_format_validated=$true},
        {param($r)$r.pe.size_of_image=1},{param($r)$r.pdata_records=174763},{param($r)$r.returned_bytes=2999},{param($r)$r.requested_bytes=4MB+1},
        {param($r)$r.boot_authorized=$true},{param($r)$r.abi_proven=@($false)},{param($r)$r.creation_filetime='1'},{param($r)$r.base_matches_source=$false}
    )){$report=New-Report;& $change $report;Refuses {Get-T7RefV2Outcome $report $identity 0 $module}}
    $fixture=New-BuildFixture;Assert-T7RefV2Build $fixture.Plan $fixture.Build $fixture.Receipt;$script:checks++
    foreach($field in 'Name','Option','Report','ObservationSchema'){$f=New-BuildFixture;$f.Build.BuildProfile.$field=@($f.Build.BuildProfile.$field);Refuses {Assert-T7RefV2Build $f.Plan $f.Build $f.Receipt} 'scalar string'}
    foreach($field in 'Schema','SourceProfile','RetainedMainSHA256','BaseMainSHA256','MainSHA256','HelperSHA256'){$f=New-BuildFixture;$f.Build.ReuseCompile.PrepatchReferenceV2.$field=@($f.Build.ReuseCompile.PrepatchReferenceV2.$field);Refuses {Assert-T7RefV2Build $f.Plan $f.Build $f.Receipt} 'scalar string'}
    foreach($field in 'Path','SHA256','Bytes'){$f=New-BuildFixture;$f.Build.BuildProfile.Helper.$field=@($f.Build.BuildProfile.Helper.$field);Refuses {Assert-T7RefV2Build $f.Plan $f.Build $f.Receipt} 'scalar'}
    foreach($field in 'InputsReverified','TreeClosureConfirmed','LeaseReleased','Quarantined','CandidateExecuted','Ready'){
        $f=New-BuildFixture;$f.Receipt.$field=@($f.Receipt.$field);Refuses {Assert-T7RefV2Build $f.Plan $f.Build $f.Receipt} 'boolean'
        $f=New-BuildFixture;$f.Receipt.$field=!$f.Receipt.$field;Refuses {Assert-T7RefV2Build $f.Plan $f.Build $f.Receipt} 'closed'
    }
    $f=New-BuildFixture;$f.Receipt.Stages[0].CompilerTelemetry.AfterStop.ActiveProcesses=1;Refuses {Assert-T7RefV2Build $f.Plan $f.Build $f.Receipt}
    $f=New-BuildFixture;$f.Build.ReuseCompile|Add-Member NoteProperty ZombiesAddObservationC2 @{};Refuses {Assert-T7RefV2Build $f.Plan $f.Build $f.Receipt}
    $f=New-BuildFixture;$f.Plan.Bindings[0].SHA256=@($f.Plan.Bindings[0].SHA256);Refuses {Assert-T7RefV2Build $f.Plan $f.Build $f.Receipt} 'binding'
    $f=New-BuildFixture;$f.Receipt.Stages[1].Artifacts[0].SHA256=@($f.Receipt.Stages[1].Artifacts[0].SHA256);Refuses {Assert-T7RefV2Build $f.Plan $f.Build $f.Receipt} 'scalar string'
    $main=New-MainFixture;Check ((Assert-T7RefV2Main $main).BankMetadataUnchanged) 'Stopped Main metadata refused.'
    $script:mockProcesses=@([pscustomobject]@{PID=19932;Image='foreign';Name='foreign.exe'});Refuses {Assert-T7RefV2Main $main} 'ownership';$script:mockProcesses=@()
    $script:mockPorts=@([pscustomobject]@{LocalPort=27016;OwningProcess=456});Refuses {Assert-T7RefV2Main $main} 'ownership';$script:mockPorts=@()
    $main.MainBaseline='Running';Refuses {Assert-T7RefV2Main $main} 'stopped';$main=New-MainFixture
    [IO.Directory]::CreateDirectory($main.BankSnapshot.Root)|Out-Null;Refuses {Assert-T7RefV2Main $main} 'bank metadata'
    $plan=[pscustomobject]@{Image=(Join-Path $root 'candidate.exe');WorkingDirectory=$root;RunRoot=$root;HostImage='pwsh.exe';Runner='runner.ps1'}
    $start=New-T7RefV2Start $plan
    Check ($start.ArgumentList.Count -eq 1 -and $start.ArgumentList[0] -ceq '-t7-prepatch-reference-v2' -and !$start.UseShellExecute -and $start.Environment.Count -eq 9) 'Actual native ProcessStartInfo differs.'
    $command=@('pwsh.exe','-NoLogo','-NoProfile','-NoExit','-File','runner.ps1','-PlanPath','plan.json','-PlanSHA256',('a'*64),'-Run')
    Assert-T7RefV2HostArguments $plan 'plan.json' ('a'*64) $command;$script:checks++
    $bad=@($command);$bad[3]='-NonInteractive';Refuses {Assert-T7RefV2HostArguments $plan 'plan.json' ('a'*64) $bad} 'NoProfile/NoExit'
    $reportPlan=[pscustomobject]@{WorkingDirectory=$root};$reportState=[ordered]@{Identity=$identity;ExitCode=0;CaptureOutcome='NoCapture'};$reportContext=[pscustomobject]@{Guards=[Collections.Generic.List[object]]::new()}
    $capturePath=Join-Path $root 't7-prepatch-reference-v2.local.json';[IO.File]::WriteAllText($capturePath,((New-Report)|ConvertTo-Json -Depth 12))
    Check ((Read-T7RefV2Report $reportPlan $reportState $reportContext) -ceq 'CaptureComplete' -and $reportContext.Guards.Count -eq 1) 'Guarded V2 report was not retained.'
    Refuses {[IO.File]::AppendAllText($capturePath,'x')} '.'
    foreach($guard in $reportContext.Guards){$guard.Dispose()};$reportContext.Guards.Clear()
    $reportPath=Join-Path $root 'report.json';[IO.File]::WriteAllText($reportPath,((New-Report)|ConvertTo-Json -Depth 12))
    Check ((Read-T7RefV2Json $reportPath).creation_filetime -is [string]) 'JSON scalar codec changed.'
    [IO.File]::WriteAllText($reportPath,'{"timestamp":"2026-10-14T00:00:00.0000000Z"}');Check ((Read-T7RefV2Json $reportPath).timestamp -is [string]) 'Literal UTC was auto-converted.'
    [IO.File]::WriteAllBytes($reportPath,[byte[]]::new(256KB+1));Refuses {Read-T7RefV2Json $reportPath 256KB} 'bounded'
    $runnerPath=Join-Path $PSScriptRoot 'Run-T7PrepatchReferenceV2.ps1';$tokens=$null;$errors=$null;$null=[Management.Automation.Language.Parser]::ParseFile($runnerPath,[ref]$tokens,[ref]$errors);Check (!$errors.Count) 'Runner parse failed.'
    $runner=Get-Content -LiteralPath $runnerPath -Raw
    Check ($runner.IndexOf('if(!$Run)') -lt $runner.IndexOf('Enter-IW7ResourceLease')) 'DEFAULT can acquire a lease.'
    Check ($runner.IndexOf('Enter-IW7ResourceLease') -lt $runner.IndexOf("Where-Object {!`$_.IsText}")) 'Opaque hashing can precede admission.'
    Check ($runner.Contains('Complete-H1Stage $context $state') -and $runner.Contains('Invoke-H1OwnedStage $plan $state $context')) 'H1 lifecycle was replaced.'
    [ordered]@{Schema='iw7.t7-prepatch-reference-consumer-source-tests/2';Checks=$script:checks;Status='Passed';NativeExecuted=$false;LeaseAcquired=$false;OpaqueInputsRead=$false}|ConvertTo-Json
}finally{
    $resolved=[IO.Path]::GetFullPath($root)
    if(!$resolved.StartsWith($tempBase,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -cnotmatch '^t7-ref-v2-source-tests-[0-9a-f]{32}$'){throw 'Refuse unverified test cleanup target.'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
}

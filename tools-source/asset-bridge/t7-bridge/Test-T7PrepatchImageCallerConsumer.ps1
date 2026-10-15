# Authored caller report and Source descriptors only. No native process or lease.
# Local IO is limited to a temporary authored JSON report held by the real H1 guard.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path (Split-Path $PSScriptRoot -Parent) 'h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
. (Join-Path $PSScriptRoot 'T7PrepatchReferenceV2.Profile.ps1')
# Synthetic metadata paths; never query or open the purported artifacts.
function Assert-H1Path([string]$Path){if(![IO.Path]::IsPathFullyQualified($Path) -or [IO.Path]::GetFullPath($Path) -cne $Path){throw 'Authored canonical path required'}}
$checks=0
function Check([bool]$Value,[string]$Message){if(!$Value){throw $Message};$script:checks++}
function Refuses([scriptblock]$Action,[string]$Message){$refused=$false;try{& $Action}catch{$refused=$true};Check $refused $Message}
function Copy-Authored($Value){$Value|ConvertTo-Json -Depth 25|ConvertFrom-Json -Depth 25}
$identity=[pscustomobject]@{PID=123;CreatedUtc=[datetime]::FromFileTimeUtc(132000000000000000).ToString('o')}
$module='C:\authored\BlackOps3_UnrankedDedicatedServer.exe'
function New-CallerReport {
    $site=0x1B1E5D;$begin=$site-16;$length=64;$base=[uint64]0x140000000
    $code=[byte[]]::new($length);$code[16]=0xE8
    [BitConverter]::GetBytes([int](0x7DB4C0-$site-5)).CopyTo($code,17)
    [pscustomobject]@{schema='iw7.t7-prepatch-image-caller-observation/1';phase='first_dpi_before_component_post_unpack';source_base='0x140000000';
        read_limit=4194304;report_limit=262144;window_count=1;window_observations=1;requested_bytes=448;returned_bytes=448;pid=123;thread_id=456;
        capture_complete=$true;boot_authorized=$false;abi_proven=$false;runtime_compatibility_proven=$false;writer_proven=$false;
        gfximage_payload_read=$false;outside_interval_followed=$false;creation_filetime='132000000000000000';module_base='0x140000000';
        base_matches_source=$true;module_path=$module;pdata_records=1;status='captured_for_offline_review';
        pe=[pscustomobject]@{size_of_image=16777216;preferred_base='0x140000000';entrypoint_rva=4096;timestamp=1;dll_characteristics=0;
            sections=@([pscustomobject]@{name='.text';rva=4096;virtual_size=16773120;raw_size=16773120;characteristics=0x60000020})};
        windows=@([pscustomobject]@{site='Load_GfxImage_caller';rva=$site;window_rva=$begin;window_bytes=$length;code_limit=8192;
            known_target_rva=0x7DB4C0;callsite_validated=$true;callee_read=$false;
            runtime_function=[pscustomobject]@{begin_rva=$begin;end_rva=($begin+$length);unwind_rva=0x1000;unwind_header_hex='01000000';unwind_format_validated=$false};
            regions=@([pscustomobject]@{base=('0x{0:x}' -f ($base+$begin));size=$length;allocation_base='0x140000000';state=4096;protect=32;allocation_protect=32;type=16777216});
            bytes_hex=[Convert]::ToHexString($code).ToLowerInvariant()})}
}
$report=New-CallerReport
Check ((Get-T7PrepatchImageCallerOutcome $report $identity 0 $module) -ceq 'CallerCapturedForOfflineReview') 'Complete authored caller refused'
$genericPath=New-CallerReport;$genericPath.module_path=$module.Replace('\','/')
Check ((Get-T7PrepatchImageCallerOutcome $genericPath $identity 0 $module) -ceq 'CallerCapturedForOfflineReview') 'Native generic_string module path refused'
Check ((Get-T7PrepatchImageCallerOutcome $null $identity 2 $module) -ceq 'CallerNoCapture') 'Missing capture differs'
$partial=New-CallerReport;$partial.capture_complete=$false;$partial.status='incomplete_stop'
Check ((Get-T7PrepatchImageCallerOutcome $partial $identity 2 $module) -ceq 'CallerCapturePartial') 'Partial/exit2 differs'
Refuses {Get-T7PrepatchImageCallerOutcome $partial $identity 0 $module} 'Partial report with exit0 accepted'
Refuses {Get-T7PrepatchImageCallerOutcome $report $identity 2 $module} 'Complete report with failed exit accepted'
$raw=[Text.UTF8Encoding]::new($false).GetBytes(($report|ConvertTo-Json -Depth 25))
$decoded=ConvertFrom-T7PrepatchImageCallerJson $raw
Check ((Get-T7PrepatchImageCallerOutcome $decoded $identity 0 $module) -ceq 'CallerCapturedForOfflineReview') 'Actual JSON decode differs'
foreach($rawCase in @([byte[]]@(255),[Text.Encoding]::UTF8.GetBytes('[]'),[Text.Encoding]::UTF8.GetBytes('{"x":1,"x":2}'),
    [Text.Encoding]::UTF8.GetBytes('{"x":{"y":1,"y":2}}'),[Text.Encoding]::UTF8.GetBytes('{} trailing'),[byte[]]::new(262145))){
    Refuses {ConvertFrom-T7PrepatchImageCallerJson $rawCase} 'Invalid/ambiguous/big caller JSON accepted'
}
foreach($mutate in @(
    {param($r)$r.schema='iw7.t7-prepatch-link-observation/3'},
    {param($r)$r.phase='after_load'},
    {param($r)$r.pid=$true},
    {param($r)$r.thread_id=0},
    {param($r)$r.requested_bytes=4194305;$r.returned_bytes=4194305},
    {param($r)$r.returned_bytes--},
    {param($r)$r.window_count=2},
    {param($r)$r.windows=@($r.windows[0],$r.windows[0])},
    {param($r)$r.creation_filetime='0'},
    {param($r)$r.module_path='C:\other\BlackOps3_UnrankedDedicatedServer.exe'},
    {param($r)$r.base_matches_source=$false},
    {param($r)$r.pe.size_of_image=0},
    {param($r)$r.pe.sections=@()},
    {param($r)$r.pe.sections[0].raw_size=16777217},
    {param($r)$r.pdata_records=0},
    {param($r)$r.windows[0].rva=0x1B1E5E},
    {param($r)$r.windows[0].code_limit=8193},
    {param($r)$r.windows[0].window_bytes=8193},
    {param($r)$r.windows[0].callsite_validated=$false},
    {param($r)$r.windows[0].known_target_rva++},
    {param($r)$r.windows[0].runtime_function.begin_rva++},
    {param($r)$r.windows[0].runtime_function.end_rva=$r.windows[0].rva+4},
    {param($r)$r.windows[0].runtime_function.unwind_rva=0},
    {param($r)$r.windows[0].runtime_function.unwind_format_validated=$true},
    {param($r)$r.windows[0].bytes_hex=$r.windows[0].bytes_hex.Substring(2)},
    {param($r)$r.windows[0].bytes_hex=$r.windows[0].bytes_hex.ToUpperInvariant()},
    {param($r)$s=$r.windows[0].bytes_hex;$r.windows[0].bytes_hex=$s.Substring(0,32)+'ff'+$s.Substring(34)},
    {param($r)$s=$r.windows[0].bytes_hex;$r.windows[0].bytes_hex=$s.Substring(0,34)+'00'+$s.Substring(36)},
    {param($r)$r.windows[0].regions=@()},
    {param($r)$r.windows[0].regions[0].size--},
    {param($r)$r.windows[0].regions[0].allocation_base='0x140001000'},
    {param($r)$r.windows[0].regions[0].protect=1},
    {param($r)$r.windows[0].regions[0].type=0},
    {param($r)$r|Add-Member NoteProperty fabricated $true},
    {param($r)$r.windows[0]|Add-Member NoteProperty fabricated $true}
)){
    $r=New-CallerReport;& $mutate $r
    Refuses {Get-T7PrepatchImageCallerOutcome $r $identity 0 $module} 'Caller report mutation accepted'
}
foreach($name in 'boot_authorized','abi_proven','runtime_compatibility_proven','writer_proven','gfximage_payload_read','outside_interval_followed'){
    foreach($value in @($true,1,'false')){
        $r=New-CallerReport;$r.$name=$value
        Refuses {Get-T7PrepatchImageCallerOutcome $r $identity 0 $module} 'Caller false claim promoted/coerced'
    }
}
foreach($value in @($true,1,'false')){
    $r=New-CallerReport;$r.windows[0].callee_read=$value
    Refuses {Get-T7PrepatchImageCallerOutcome $r $identity 0 $module} 'Callee-read claim accepted'
}
foreach($length in @(5,8192)){
    $r=New-CallerReport;$row=$r.windows[0];$begin=$row.rva
    $row.window_rva=$begin;$row.window_bytes=$length;$row.runtime_function.begin_rva=$begin;$row.runtime_function.end_rva=$begin+$length
    $code=[byte[]]::new($length);$code[0]=0xE8;[BitConverter]::GetBytes([int](0x7DB4C0-$begin-5)).CopyTo($code,1)
    $row.bytes_hex=[Convert]::ToHexString($code).ToLowerInvariant();$row.regions[0].base=('0x{0:x}' -f ([uint64]0x140000000+$begin));$row.regions[0].size=$length
    $r.requested_bytes=$length+384;$r.returned_bytes=$r.requested_bytes
    Check ((Get-T7PrepatchImageCallerOutcome $r $identity 0 $module) -ceq 'CallerCapturedForOfflineReview') 'Exact function size boundary refused'
}
function New-CallerCohortFixture {
    $c=Get-T7ReferenceBuildCohort 't7-prepatch-image-caller-v1'
    $profile=[ordered]@{Name='t7-prepatch-image-caller-v1';Option='-t7-prepatch-image-caller-v1';ArgumentCount=2;Report='t7-prepatch-image-caller-v1.local.json';ObservationSchema='iw7.t7-prepatch-image-caller-observation/1'}
    $bindings=@()
    foreach($row in @(
        @('Helper',16778,'39fd69039d16285ca574f73a768130e294c618a089ba365bacdf84fd2cfa0019'),
        @('Wiring',2749,'8e6edee60d06dda0c77f8f2cf73bd39677523f0ba046ced2046218cc7eb7d7a2'),
        @('RangeGuard',3117,'0a633964ed558de91bae621b51b28d5e8e0eab20ab790fc000b1b3c6978aa38a'),
        @('RangeGuardSource',3117,'0a633964ed558de91bae621b51b28d5e8e0eab20ab790fc000b1b3c6978aa38a'),
        @('BoundaryFixture',3828,'a2471c937e91191fca49820a50ac15091832eaa54bb993c639671e490dd9ade4'),
        @('FixtureResponse',1193,'5cd1f496bcb97a3c5080c3e68be7213f469097b3cb3482d460150748baae3822'),
        @('BaseHelper',15827,'cf839e18a68adb4ed3aae82d683ef110ab595fa8c172584e47ca4d11bb8db48d'),
        @('BaseWiring',2236,'66f70ca5a979745288232d76496a339e08d639ddf34560aada6e6b63c5bcffa1'),
        @('BaseBuildPlan',292575,'422e79898fa2b16defc8193182fe146e2db5d73aeb4516c2bd2aaf87c409c4de'),
        @('BaseBuildReceipt',26199,'af6beecf7a8892e16266a7641d2799f665f86fa8ad7c40c61561b782534f7897'),
        @('BaseV3BuildPlan',305621,'e484cef7415b2697c188b0202f3771af15377ecb56d98a0a85bfc1d2418fe530'),
        @('BaseV3Main',14469,'84cde2924df0a0553dd2cddb0ca173aed54af43d6874b06718c01d1a6cec4989'),
        @('PreparedMain',14557,'2ff1c104f8dfc99432179b289a0453aa1a81b8a99703803fcede1869fae61133')
    )){
        $path='C:\authored\'+$row[0]+'.txt';$profile[$row[0]]=@{Path=$path;Bytes=$row[1];SHA256=$row[2]}
        $bindings+=@{Path=$path;Bytes=$row[1];SHA256=$row[2];IsText=$true}
    }
    $plan=@{ExpectedBuildPlanSHA256=$c.PlanSHA256;CandidateSource='C:\authored\link\zonetool-t7.exe';CandidateBytes=$c.CandidateBytes;CandidateSHA256=$c.CandidateSHA256;BuildPlan='C:\authored\build-plan.local.json';BuildReceipt='C:\authored\receipt.json';ExpectedBuildReceiptSHA256=$c.ReceiptSHA256;BuildClosedPins='C:\authored\handoff.local.json';Bindings=$bindings}
    foreach($row in @(@($plan.BuildPlan,$c.PlanBytes,$c.PlanSHA256),@($plan.BuildReceipt,$c.ReceiptBytes,$c.ReceiptSHA256),@($plan.BuildClosedPins,$c.IndexBytes,$c.IndexSHA256))){$plan.Bindings+=@{Path=$row[0];Bytes=$row[1];SHA256=$row[2];IsText=$true}}
    $plan.Bindings+=@{Path=$plan.CandidateSource;Bytes=$c.CandidateBytes;SHA256=$c.CandidateSHA256;IsText=$false}
    $marker=@{Schema='iw7.t7-prepatch-image-caller-build/1';SourceProfile='t7-prepatch-image-caller-v1';RetainedMainBytes=12854;RetainedMainSHA256='40de5fda829cec32a5d75359f58e69c84db7d8ee54f198cf6befa2a6ebe6f86e';BaseMainBytes=14469;BaseMainSHA256='84cde2924df0a0553dd2cddb0ca173aed54af43d6874b06718c01d1a6cec4989';MainBytes=14557;MainSHA256='2ff1c104f8dfc99432179b289a0453aa1a81b8a99703803fcede1869fae61133';HelperBytes=16778;HelperSHA256='39fd69039d16285ca574f73a768130e294c618a089ba365bacdf84fd2cfa0019'}
    $build=@{Schema='iw7.t7-minimal-build-plan/1';SourceCommit='fab935826c898806855376662a8a03317b3ad8f1';BuildProfile=$profile;ReuseCompile=@{OriginalStatus='Failed';SourcePlanSHA256='source';ReceiptSHA256='receipt';Checks=51;RecompiledMain=$true;StageRoots=@('C:\authored\zonetool11','C:\authored\xpak');PrepatchImageCallerV1=$marker;SourcePlan='C:\authored\old-plan.json';Receipt='C:\authored\old-receipt.json'};Stages=@()}
    $receipt=@{Schema='iw7.t7-minimal-build/1';Status='Passed';PlanSHA256=$c.PlanSHA256;BuildProfile=$profile;InputsReverified=$true;TreeClosureConfirmed=$true;LeaseReleased=$true;Quarantined=$false;CandidateExecuted=$false;Ready=$false;ImageCallerFixturePassed=$true;Stages=@()}
    for($i=0;$i -lt 4;$i++){
        $name=@('caller-fixture-compile','caller-fixture-test','main','link')[$i];$kind=if($i -eq 1){'Probe'}elseif($i -eq 3){'Link'}else{'Compile'}
        $build.Stages+=@{Name=$name;Stage=$kind;DeadlineSeconds=$(if($i -eq 1){15}else{120})}
        $stage=@{Name=$name;ExitCode=0;TreeClosureConfirmed=$true;CompilerTelemetry=@{Completed=$true};LastOriginalSnapshot=@{RootExited=$true;RootExitCode=0;ActiveProcesses=0};Artifacts=@()}
        if($i -eq 1){$stage.Checks=25;$stage.EngineInvoked=$false}
        if($i -eq 3){$stage.Artifacts=@(@{Path=$plan.CandidateSource;Bytes=$c.CandidateBytes;SHA256=$c.CandidateSHA256})}
        $receipt.Stages+=@($stage)
    }
    $index=@{Schema='iw7.t7-image-caller-cpp-actual-handoff/1';SourceCommit='408af1d5f51469cca9b27128bedc895383aeee29';NativeSourceCommit=$build.SourceCommit;Status='Passed';FixtureChecks=25;ActualPTYAggregateExitCode=0;NativeReport=$null;FreshHeavyProcesses=@();Plan=@{Path=$plan.BuildPlan;Bytes=$c.PlanBytes;SHA256=$c.PlanSHA256};Receipt=@{Path=$plan.BuildReceipt;Bytes=$c.ReceiptBytes;SHA256=$c.ReceiptSHA256};CandidatePinCapturedUnderCPPLease=@{Path=$plan.CandidateSource;Bytes=$c.CandidateBytes;SHA256=$c.CandidateSHA256}}
    foreach($key in 'InputsReverified','TreeClosureConfirmed','LeaseReleased','CompletionPublished','OriginalAppDomainRootSame','OriginalContextGuardsStatePSVariableValuesSame','OriginalReferencesVerified','OriginalHostParentStagesAbsent','ImageCallerFixturePassed','CPPExecuted','SourceMarkerRemainsPending','KnownLimitAcceptedByRootForThisExactImmutablePlanOnly'){$index[$key]=$true}
    foreach($key in 'ImageCallerCPPQualifiedFlagPresent','CandidateExecuted','OpaqueInputsReopenedAfterRelease','CandidateOrSymbolsReopenedForHandoff','NativeObserved','Ready','OpaqueClassificationMutationProtectedByRunner'){$index[$key]=$false}
    Copy-Authored ([pscustomobject]@{Plan=$plan;Build=$build;Receipt=$receipt;Index=$index})
}
$f=New-CallerCohortFixture
Assert-T7ReferenceCandidate $f.Plan 't7-prepatch-image-caller-v1';Assert-T7ImageCallerBuild $f.Plan $f.Build $f.Receipt;Assert-T7ImageCallerClosedBuildPins $f.Plan $f.Index;Check $true 'Authored closed CPP25 tuple refused'
foreach($mutate in @(
    {param($f)$f.Plan.ExpectedBuildPlanSHA256='e484cef7415b2697c188b0202f3771af15377ecb56d98a0a85bfc1d2418fe530'},
    {param($f)$f.Build.BuildProfile.Name='t7-prepatch-link-v3'},
    {param($f)$f.Build.BuildProfile.ArgumentCount='2'},
    {param($f)$f.Build.BuildProfile.Helper=$null},
    {param($f)$f.Build.ReuseCompile|Add-Member NoteProperty PrepatchLinkV3 @{}},
    {param($f)$f.Build.Stages=@($f.Build.Stages[2],$f.Build.Stages[3])},
    {param($f)$f.Build.Stages[1].DeadlineSeconds=120},
    {param($f)$f.Receipt.ImageCallerFixturePassed=1},
    {param($f)$f.Receipt|Add-Member NoteProperty ImageCallerCPPQualified $true},
    {param($f)$f.Receipt.Stages[0].Name=@($f.Receipt.Stages[0].Name)},
    {param($f)$f.Receipt.Stages[1].Checks=24},
    {param($f)$f.Receipt.Stages[1].EngineInvoked=$true},
    {param($f)$f.Receipt.Stages[0].LastOriginalSnapshot.ActiveProcesses=1},
    {param($f)$f.Receipt.Stages[0].LastOriginalSnapshot.RootExitCode=$false},
    {param($f)$f.Receipt.Stages[3].Artifacts[0].SHA256='d89c4cf326f21038d9fbcc6a18c18db2c17c17f448400a8567ee2e5fdca6a8bb'},
    {param($f)$f.Index.SourceCommit='wrong'},
    {param($f)$f.Index.OriginalAppDomainRootSame=$false},
    {param($f)$f.Index.ImageCallerCPPQualifiedFlagPresent=$true},
    {param($f)$f.Index.OpaqueClassificationMutationProtectedByRunner=$true},
    {param($f)$f.Index.ActualPTYAggregateExitCode=$false},
    {param($f)$f.Index.CandidatePinCapturedUnderCPPLease.SHA256=@($f.Index.CandidatePinCapturedUnderCPPLease.SHA256)}
)){
    $f=New-CallerCohortFixture;& $mutate $f
    Refuses {Assert-T7ImageCallerBuild $f.Plan $f.Build $f.Receipt;Assert-T7ImageCallerClosedBuildPins $f.Plan $f.Index} 'CPP25 cohort mutation accepted'
}
$f=New-CallerCohortFixture;$f.Plan.CandidateSHA256=(Get-T7ReferenceBuildCohort 't7-prepatch-link-v3').CandidateSHA256
Refuses {Assert-T7ReferenceCandidate $f.Plan 't7-prepatch-image-caller-v1'} 'Old V3 candidate relabeled as caller'
$protocol=Get-T7ReferenceProtocol 't7-prepatch-image-caller-v1'
Check ($protocol.Option -ceq '-t7-prepatch-image-caller-v1' -and $protocol.Report -ceq 't7-prepatch-image-caller-v1.local.json') 'Caller protocol drift'
Check ((Get-T7ReferenceBuildCohort 't7-prepatch-link-v3').CandidateSHA256 -ceq 'd89c4cf326f21038d9fbcc6a18c18db2c17c17f448400a8567ee2e5fdca6a8bb') 'Old V3 cohort relabeled'
$start=New-T7RefV2Start ([pscustomobject]@{Image='C:\authored\caller.exe';WorkingDirectory='C:\authored\work';RunRoot='C:\authored'}) $protocol.Name
Check ($start.ArgumentList.Count -eq 1 -and $start.ArgumentList[0] -ceq $protocol.Option -and !$start.UseShellExecute -and $start.CreateNoWindow -and $start.Environment.Count -eq 9) 'Actual caller native invocation differs'
# Exercise the real held-stream decoder with authored text only; no opaque input exists.
$tempBase=[IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$tempRoot=Join-Path $tempBase ('t7-caller-source-tests-'+[guid]::NewGuid().ToString('N'))
$context=[pscustomobject]@{Guards=[Collections.Generic.List[object]]::new()}
try{
    [IO.Directory]::CreateDirectory($tempRoot)|Out-Null
    $path=Join-Path $tempRoot $protocol.Report;$module=Join-Path $tempRoot 'BlackOps3_UnrankedDedicatedServer.exe'
    $reportPlan=[pscustomobject]@{WorkingDirectory=$tempRoot}
    $state=[ordered]@{Identity=$identity;ExitCode=0;CaptureOutcome='NoCapture'}
    Check ((Read-T7RefV2Report $reportPlan $state $context $protocol.Name) -ceq 'CallerNoCapture') 'Missing fixed caller report differs'
    $r=New-CallerReport;$r.module_path=$module.Replace('\','/')
    $text=$r|ConvertTo-Json -Depth 25
    [IO.File]::WriteAllText($path,$text,[Text.UTF8Encoding]::new($false))
    Check ((Read-T7RefV2Report $reportPlan $state $context $protocol.Name) -ceq 'CallerCapturedForOfflineReview' -and $context.Guards.Count -eq 1 -and $context.Guards[0].Position -eq 0) 'Caller held-stream decode failed'
    Refuses {[IO.File]::AppendAllText($path,'x')} 'Original caller report guard was not retained'
    foreach($guard in $context.Guards){$guard.Dispose()};$context.Guards.Clear()
    [IO.File]::WriteAllText($path,($text.TrimEnd().Substring(0,$text.TrimEnd().Length-1)+',"writer_proven":false}'),[Text.UTF8Encoding]::new($false))
    Refuses {Read-T7RefV2Report $reportPlan $state $context $protocol.Name} 'Duplicate field bypassed the real held report reader'
    Check ($context.Guards.Count -eq 1 -and $context.Guards[0].Position -eq 0 -and $state.CaptureOutcome -ceq 'CapturePresentUnqualified') 'Refused report lost its original guard'
}finally{
    foreach($guard in $context.Guards){$guard.Dispose()};$context.Guards.Clear()
    $resolved=[IO.Path]::GetFullPath($tempRoot)
    if(!$resolved.StartsWith($tempBase,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -cnotmatch '^t7-caller-source-tests-[0-9a-f]{32}$'){throw 'Refuse unverified authored test cleanup'}
    if(Test-Path -LiteralPath (Join-Path $resolved $protocol.Report)){Remove-Item -LiteralPath (Join-Path $resolved $protocol.Report) -Force}
    if(Test-Path -LiteralPath $resolved){Remove-Item -LiteralPath $resolved -Force}
}
[ordered]@{Checks=$checks;Status='Passed';AuthoredOnly=$true;NativeExecuted=$false;OpaqueInputsRead=$false;LeaseAcquired=$false;Ready=$false}|ConvertTo-Json -Compress

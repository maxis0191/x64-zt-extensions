# Real profile/core functions with fake owners/clock. No native provider or lease.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$core=Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1'
. $core
. (Join-Path $PSScriptRoot 'T7Prepatch.Profile.ps1')
$script:checks=0;$script:clock=0;$script:releaseDelay=0;$script:releaseFails=$false
function Check([bool]$Value,[string]$Why){if(!$Value){throw $Why};$script:checks++}
function Refuses([scriptblock]$Body,[string]$Pattern){
    $caught=$false
    try{& $Body}catch{$caught=$true;Check ($_.Exception.Message -match $Pattern) ('Unexpected error: '+$_.Exception.Message)}
    Check $caught ('Expected refusal: '+$Pattern)
}
function Get-H1Clock {$script:clock}
function Start-Sleep {param([int]$Milliseconds,[int]$Seconds);$script:clock+=$Milliseconds+1000*$Seconds}
function Get-IW7ResourceSnapshot {[pscustomobject]@{CommitLimit=100;Committed=10}}
function Register-H1Original($Lease,$Identity){$script:events.Add('register')}
function Exit-IW7ResourceLease($Token){$script:events.Add('release');$script:clock+=$script:releaseDelay;if($script:releaseFails){throw 'injected release failure'}}
function New-H1Owner { $script:fakeOwner }
$root=Join-Path ([IO.Path]::GetTempPath()) ('t7-prepatch-tests-'+[guid]::NewGuid().ToString('N'))
$work=Join-Path $root 'work';$evidence=Join-Path $root 'evidence'
[IO.Directory]::CreateDirectory($work)|Out-Null;[IO.Directory]::CreateDirectory($evidence)|Out-Null
$module=Join-Path $work 'BlackOps3_UnrankedDedicatedServer.exe'
$identity=[pscustomobject]@{PID=123;CreatedUtc='2026-10-12T00:00:00.0000000Z'}
function New-TestReport {
    $names=@('DB_FindXAssetHeader','DB_LoadXAssets','SL_ConvertToString','boot_call','server_thread_ret','copy_info_branch_1','copy_info_branch_2','image_loader_call','integrity_intact_1','integrity_intact_2','integrity_intact_3','integrity_split')
    $rvas=@(0x1D5FB0,0x1D8740,0x1632C0,0x502AA9,0x537840,0x1A18DF,0x1A1B5B,0x1B1E5D,0x064DC4,0x909BD4,0x10654C1,0x0621A8)
    $lengths=@(256,256,128,96,128,96,96,96,96,96,96,96)
    [pscustomobject]@{schema='iw7.t7-prepatch-memory-observation/1';phase='first_dpi_before_component_post_unpack';pid=123;
        creation_filetime=([DateTime]::Parse($identity.CreatedUtc).ToFileTimeUtc().ToString());module_path=$module.Replace('\','/');base_matches_source=$false;
        source_base='0x140000000';read_limit=4MB;report_limit=256KB;requested_bytes=2000;returned_bytes=2000;
        window_count=12;window_observations=12;capture_complete=$true;status='captured_for_offline_review';
        boot_authorized=$false;abi_proven=$false;runtime_compatibility_proven=$false;
        windows=@(for($i=0;$i -lt 12;$i++){[pscustomobject]@{site=$names[$i];rva=$rvas[$i];window_rva=$rvas[$i]-$(if($i -in 0,1,2,4){0}else{32});window_bytes=$lengths[$i];bytes_hex=('00'*$lengths[$i])}})}
}
function Reset-Owner([int]$Exit=0,[bool]$Empty=$true) {
    $script:clock=0;$script:releaseDelay=0;$script:releaseFails=$false
    $script:events=[Collections.Generic.List[string]]::new()
    $script:fakeOwner=[pscustomobject]@{PID=123;Image=(Join-Path $work 'candidate.exe');CreationFileTime=[DateTime]::Parse($identity.CreatedUtc).ToFileTimeUtc();Closed=$false;ExitCode=$Exit;Empty=$Empty;StopFails=$false}
    $script:fakeOwner|Add-Member ScriptMethod Start {param($start,$hash,$out,$err);$script:events.Add('start')}
    $script:fakeOwner|Add-Member ScriptMethod TreeExited {$this.Empty}
    $script:fakeOwner|Add-Member ScriptMethod CloseConfirmed {if(!$this.Empty){throw 'job active'};$script:events.Add('close');$this.Closed=$true}
    $script:fakeOwner|Add-Member ScriptMethod StopAndConfirm {param($milliseconds);$script:events.Add('stop');if($this.StopFails){throw 'injected stop failure'};$this.Empty=$true;$this.Closed=$true;$this.ExitCode=-1}
    $script:ctx=[pscustomobject]@{Owner=$null;Closed=$true;Lease=[pscustomobject]@{Token='synthetic'};Guards=[Collections.Generic.List[object]]::new()}
    $script:state=[ordered]@{Stage='Prepatch';DeadlineSeconds=120;MaxObservedOutputBytes=0L;TreeClosureConfirmed=$false;LeaseReleased=$false;Quarantined=$false;Status='Running';LeaseToken='synthetic';TerminationRequested=$false;ExitCode=$null}
}
try {
    $report=New-TestReport
    Check ((Get-T7PrepatchOutcome $report $identity 0 $module) -ceq 'CaptureComplete') 'Complete capture was lost because its layout is not approved.'
    Check ((Get-T7PrepatchOutcome $null $identity 2 $module) -ceq 'NoCapture') 'Missing report classification differs.'
    $report.capture_complete=$false;$report.status='incomplete_stop';$report.windows=@();$report.window_observations=0
    Check ((Get-T7PrepatchOutcome $report $identity 2 $module) -ceq 'CapturePartial') 'Partial metadata capture was lost.'
    Refuses {Get-T7PrepatchOutcome $report $identity 0 $module} 'Partial report/exit'
    $report=New-TestReport;$report.pid=456
    Refuses {Get-T7PrepatchOutcome $report $identity 0 $module} 'identity/schema'
    $report=New-TestReport;$report.creation_filetime='1'
    Refuses {Get-T7PrepatchOutcome $report $identity 0 $module} 'generation'
    $report=New-TestReport;$report.boot_authorized=$true
    Refuses {Get-T7PrepatchOutcome $report $identity 0 $module} 'overclaims'
    $report=New-TestReport;$report.windows[3].rva++
    Refuses {Get-T7PrepatchOutcome $report $identity 0 $module} 'window differs'
    $report=New-TestReport;$report.window_observations=11
    Refuses {Get-T7PrepatchOutcome $report $identity 0 $module} 'identity/schema'
    $report=New-TestReport;$report.requested_bytes=4MB+1
    Refuses {Get-T7PrepatchOutcome $report $identity 0 $module} 'identity/schema'
    $report=New-TestReport;$report.module_path=Join-Path $work 'wrong.exe'
    Refuses {Get-T7PrepatchOutcome $report $identity 0 $module} 'Complete capture'
    $path=Join-Path $work 't7-prepatch-probe.local.json'
    [IO.File]::WriteAllText($path,((New-TestReport)|ConvertTo-Json -Depth 10))
    $plan=[pscustomobject]@{WorkingDirectory=$work;Image=(Join-Path $work 'candidate.exe');StageRoot=$evidence;RunRoot=$root;OutputLimitBytes=64MB;MetadataReserveBytes=64KB;LogLimitBytes=1MB}
    $context=[pscustomobject]@{Guards=[Collections.Generic.List[object]]::new()}
    $s=[ordered]@{Identity=$identity;ExitCode=0;CaptureOutcome='NoCapture'}
    Check ((Read-T7PrepatchReport $plan $s $context) -ceq 'CaptureComplete' -and $context.Guards.Count -eq 1) 'Guarded report failed.'
    Refuses {[IO.File]::AppendAllText($path,'x')} '.'
    foreach($g in $context.Guards){$g.Dispose()};$context.Guards.Clear()
    [IO.File]::WriteAllBytes($path,[byte[]]::new(256KB+1))
    Refuses {Read-T7PrepatchReport $plan $s $context} 'JSON size'
    Remove-Item -LiteralPath $path

    $build=[pscustomobject]@{PlanSHA256=('d'*64);Status='Passed';InputsReverified=$true;TreeClosureConfirmed=$true;LeaseReleased=$true;Quarantined=$false;CandidateExecuted=$false;Stages=@();BuildProfile=$null}
    Refuses {Assert-T7PrepatchBuild ([pscustomobject]@{ExpectedBuildPlanSHA256=('d'*64);CandidateSource='unused'}) $build} 'Instrumented build profile'
    $pin=[pscustomobject]@{Path='source';Bytes=10;SHA256=('a'*64);IsText=$true}
    $build.BuildProfile=[pscustomobject]@{Name='t7-prepatch-probe';Option='-t7-prepatch-probe';ArgumentCount=2;Report='t7-prepatch-probe.local.json';Helper=$pin;Wiring=$pin;PreparedMain=$pin}
    $build.Stages=@([pscustomobject]@{Artifacts=@([pscustomobject]@{Path='candidate';Bytes=100;SHA256=('b'*64)})})
    $buildPlan=[pscustomobject]@{ExpectedBuildPlanSHA256=('d'*64);Bindings=@($pin);CandidateSource='candidate';CandidateBytes=100;CandidateSHA256=('b'*64)}
    Assert-T7PrepatchBuild $buildPlan $build;$checks++
    $build.PlanSHA256='e'*64
    Refuses {Assert-T7PrepatchBuild $buildPlan $build} 'successful unexecuted build'
    $build.PlanSHA256='d'*64
    $buildPlan.CandidateSHA256='c'*64
    Refuses {Assert-T7PrepatchBuild $buildPlan $build} 'Candidate differs'
    $start=New-T7PrepatchStart $plan
    Check ($start.ArgumentList.Count -eq 1 -and $start.ArgumentList[0] -ceq '-t7-prepatch-probe' -and !$start.UseShellExecute -and $start.CreateNoWindow -and $start.WorkingDirectory -ceq $work) 'Fixed command changed.'
    Check ($start.Environment['LOCALAPPDATA'].StartsWith((Join-Path $root 'temp')) -and !$start.Environment.ContainsKey('STEAM_COMPAT_DATA_PATH')) 'Private child environment not bounded.'

    # Execute the real existing H1 stage, not a duplicate ownership loop.
    Reset-Owner
    Invoke-H1OwnedStage $plan $state $ctx $start ('a'*64) $evidence
    Complete-H1Stage $ctx $state
    Check ($ctx.Closed -and $state.LeaseReleased -and ($events -join ',') -ceq 'start,register,close,release') 'Ordinary original closure differs.'
    Reset-Owner 2
    Refuses {Invoke-H1OwnedStage $plan $state $ctx $start ('a'*64) $evidence} 'Original stage process failed'
    Complete-H1Stage $ctx $state
    Check ($state.ExitCode -eq 2 -and $ctx.Closed -and $state.LeaseReleased -and !$state.TerminationRequested -and !$events.Contains('stop')) 'Partial exit caused force-stop or lost code2.'
    Reset-Owner 0 $false;$state.DeadlineSeconds=0
    Refuses {Invoke-H1OwnedStage $plan $state $ctx $start ('a'*64) $evidence} 'deadline'
    Check (!$events.Contains('start')) 'Expired stage still started.'
    Reset-Owner 0 $false;$ctx.Owner=$fakeOwner;$ctx.Closed=$false;$fakeOwner.StopFails=$true
    Complete-H1Stage $ctx $state
    Check ($state.Quarantined -and $ctx.Lease -and !$ctx.Closed) 'Unclosed job lost its owner/lease.'
    [AppDomain]::CurrentDomain.SetData('IW7.H1.Quarantine.synthetic',$null)
    Reset-Owner;$ctx.Owner=$fakeOwner;$ctx.Closed=$true;$script:releaseFails=$true
    Complete-H1Stage $ctx $state
    Check ($state.Quarantined -and $ctx.Lease) 'Failed release lost reservation.'
    [AppDomain]::CurrentDomain.SetData('IW7.H1.Quarantine.synthetic',$null)

    # Inject time into the actual runner finally block, including receipt publication.
    $tokens=$null;$errors=$null
    $ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Run-T7Prepatch.ps1'),[ref]$tokens,[ref]$errors)
    Check ($errors.Count -eq 0) 'Runner parse failed.'
    $outer=@($ast.EndBlock.Statements|Where-Object {$_ -is [Management.Automation.Language.TryStatementAst]})[0]
    $text=$outer.Finally.Extent.Text
    $finalizer=[scriptblock]::Create($text.Substring(1,$text.Length-2))
    function Read-T7PrepatchReport($Plan,$State,$Context){'CaptureComplete'}
    function Assert-T7PrepatchMain($Expected){[pscustomobject]@{GenerationAndUDP27016OwnerUnchanged=$true}}
    foreach($lateMode in 'release','publication') {
        Reset-Owner;$context=$ctx;$context.Owner=$fakeOwner;$context.Closed=$true
        $guards=$context.Guards;$attempted=$true;$failure=$null
        $state.InputMetadata=@();$state.InputsReverified=$false;$state.CaptureOutcome='NoCapture';$state.Identity=$identity
        $state.ExitCode=0;$state.Status='Running'
        $plan|Add-Member NoteProperty Bindings @() -Force
        $plan|Add-Member NoteProperty PreservedMain $identity -Force
        Enable-T7PrepatchRuntimeProfile $plan $context
        $script:clock=199999
        if($lateMode -ceq 'release'){$script:releaseDelay=2}
        function Write-H1Receipt($Plan,$State,$StageRoot){$script:publishedStatus=$State.Status;if($script:publicationLate){$script:clock+=2;$script:publicationLate=$false};[IO.File]::WriteAllText((Join-Path $StageRoot 'receipt.json'),($State|ConvertTo-Json -Depth 8))}
        $script:publicationLate=$lateMode -ceq 'publication'
        . $finalizer
        Check ($state.Status -ceq 'Failed' -and $state.LeaseReleased -and $null -ne $failure) ('Late '+$lateMode+' became success.')
        Check ((Get-Content -LiteralPath (Join-Path $evidence 'receipt.json') -Raw|ConvertFrom-Json).Status -ceq 'Failed') 'Late canonical success receipt survived.'
        Remove-Item -LiteralPath (Join-Path $evidence 'receipt.json')
        if(Test-Path -LiteralPath (Join-Path $evidence 'receipt.deadline-exceeded.json')){Remove-Item -LiteralPath (Join-Path $evidence 'receipt.deadline-exceeded.json')}
        . $core # Restore generic functions before next profile installation.
        function Get-H1Clock {$script:clock}
    }
    [ordered]@{Status='Passed';Checks=$checks;NativeTypesLoaded=$false;RealLeaseAcquired=$false;NativeProcessStarted=$false}|ConvertTo-Json
}finally{
    if($context -and $context.Guards){foreach($g in $context.Guards){$g.Dispose()}}
    $resolved=[IO.Path]::GetFullPath($root)
    $parent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$resolved.StartsWith($parent,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -notmatch '^t7-prepatch-tests-[0-9a-f]{32}$'){throw 'Refuse test cleanup outside exact synthetic root.'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
}

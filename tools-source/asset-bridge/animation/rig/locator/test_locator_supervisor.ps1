$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'Locator.Supervisor.Core.ps1')
$script:checks=0
function Check($Condition,[string]$Message){$script:checks++;if(!$Condition){throw $Message}}
$originalRegister=${function:Register-LocatorOriginalProcess}
$originalMeasure=${function:Measure-LocatorOutput}
$originalSave=${function:Save-LocatorState}
foreach($name in 'Locator.Supervisor.Core.ps1','Run-Locator.ps1'){
    $tokens=$null;$errors=$null
    [Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $name),[ref]$tokens,[ref]$errors)|Out-Null
    Check (!$errors.Count) "Parser: $name"
}
function Get-LocatorClock {$script:clock}
function Start-Sleep {param($Milliseconds) $script:clock+=$Milliseconds}
function New-LocatorJob {
    param($Python,$Arguments,$Work)
    $script:events.Add('prepare')
    if($script:case -ceq 'factory'){throw 'factory failed without a returned owner'}
    $job=[pscustomobject]@{PID=1234;Image=$Python;CreatedUtc='2026-10-12T00:00:00.0000000Z';Priority=16384;
        Exited=$true;Active=0;ExitCode=0;Disposed=$false;Resumed=$false;Stopped=$false}
    if($script:case -ceq 'nonzero'){$job.ExitCode=2}
    if($script:case -ceq 'identity'){$job.Image='C:\foreign.exe'}
    if($script:case -ceq 'cim-running'){$job.Exited=$false;$job.Active=1}
    if($script:case -ceq 'descendant'){$job.Active=1}
    $job|Add-Member ScriptMethod Resume {$script:events.Add('resume');$this.Resumed=$true;if($script:case -ceq 'resume'){throw 'resume failure'}}
    $job|Add-Member ScriptMethod Stop {
        $script:events.Add('stop');$this.Stopped=$true
        if($script:case -ceq 'stop-failure'){throw 'unknown closure'}
        if($script:case -ceq 'stop-deadline'){$script:clock+=15000;$this.Active=1;return}
        $this.Exited=$true;$this.Active=0
    }
    $job|Add-Member ScriptMethod Dispose {$script:events.Add('dispose');$this.Disposed=$true}
    $script:lastJob=$job;$job
}
function Register-LocatorOriginalProcess {
    param($Lease,$Identity)
    $script:events.Add('register')
    Check ($script:lastJob.Resumed) 'Resume must precede CIM registration'
    if($script:case -ceq 'slow-cim'){$script:clock+=60000}
    if($script:case -cin 'fast-exit','cim-running'){throw 'CIM unavailable'}
}
function Test-LocatorRunningBudget {
    param($Plan,$State)
    $script:events.Add('budget')
    if($script:case -cin 'output','memory','stop-failure','stop-deadline'){throw 'resource/output refusal'}
    if($script:case -cin 'slow-poll','descendant'){$script:clock+=60000}
}
function Save-LocatorState {param($State,$Root) $script:events.Add('save');if($script:case -ceq 'slow-save'){$script:clock+=60000}}
function Assert-LocatorGuards {param($Context) $script:events.Add('source-proof');if($script:case -ceq 'source'){throw 'source proof differs'}}
function Exit-IW7ResourceLease {param($Token) $script:events.Add('release');if($script:case -ceq 'release'){throw 'release refused'}}
$plan=[pscustomobject]@{RunRoot='C:\fixture';Python=[pscustomobject]@{Path='C:\python.exe'};Script='C:\locator.py';
    References=[pscustomobject]@{text=[pscustomobject]@{Path='C:\text.bin'};rdata=[pscustomobject]@{Path='C:\rdata.bin'};pdata=[pscustomobject]@{Path='C:\pdata.bin'}}}
foreach($script:case in 'success','fast-exit','nonzero','factory','resume','identity','cim-running','slow-cim',
    'slow-poll','slow-save','output','memory','descendant','stop-failure','stop-deadline','source','release'){
    $script:clock=1000L;$script:events=[Collections.Generic.List[string]]::new();$script:lastJob=$null
    $guard=[pscustomobject]@{Disposed=$false};$guard|Add-Member ScriptMethod Dispose {$this.Disposed=$true}
    $guards=[Collections.Generic.List[object]]::new();$guards.Add($guard)
    $context=@{Owner=$null;Closed=$true;Lease=[pscustomobject]@{Token='synthetic';Scope='c:\fixture'};Guards=$guards;Baselines=@()}
    $state=[ordered]@{Status='Running';RetainedLeaseToken='synthetic';MaxObservedBytes=0L;SourcesUnchanged=$false;CleanupError=$null;Failure=$null}
    try{Invoke-LocatorOwnedProcess $plan $state $context}catch{$state.Failure=$_.Exception.Message}
    Complete-LocatorOwnership $state $context
    $quarantine=$script:case -cin 'factory','stop-failure','stop-deadline','source','release'
    Check ($state.Quarantined -eq $quarantine) "Quarantine outcome: $script:case"
    Check (($null -ne $context.Lease) -eq $quarantine) "Retained lease: $script:case"
    Check ($guard.Disposed -eq !$quarantine) "Guard lifetime: $script:case"
    if(!$quarantine){Check ($context.Closed -and $state.Closure.RootExited -and $state.Closure.Active -eq 0) "Fresh original closure: $script:case"}
    if($script:case -cin 'success','fast-exit'){Check (!$state.Failure) "Successful owned close: $script:case"}
    elseif($script:case -cnotin 'source','release'){Check ([bool]$state.Failure) "Expected process failure: $script:case"}
    if($script:case -cin 'slow-cim','slow-poll','slow-save','descendant'){Check ($script:events.Contains('stop')) 'Fresh deadline after blocking call requires exact-job stop'}
    if($quarantine){Check (!$script:lastJob -or !$script:lastJob.Disposed) 'Quarantine retains original owner handle';[AppDomain]::CurrentDomain.SetData('IW7.Locator.Quarantine.synthetic',$null)}
}
# Exercise the actual registration predicate with current scheduler boundaries mocked.
function Invoke-IW7ResourceLock {param($Body) & $Body}
function Read-IW7ResourceState {[pscustomobject]@{Leases=@([pscustomobject]@{Token='s';Kind='Analysis';Scope='c:\s';Processes=@();Phase='Pending'})}}
function Get-IW7ResourceProcesses {[pscustomobject]@{PID=123;Image='C:\foreign.exe';CreatedUtc='different'}}
function Test-IW7ResourceIdentity {param($Record,$Process) $Record.PID -eq $Process.PID -and $Record.Image -ceq $Process.Image -and $Record.CreatedUtc -ceq $Process.CreatedUtc}
function Save-IW7ResourceState {throw 'A mismatched/reused PID must never be persisted'}
$rejected=$false
try{& $originalRegister ([pscustomobject]@{Token='s';Scope='c:\s'}) ([pscustomobject]@{PID=123;Image='C:\python.exe';CreatedUtc='original'})}catch{$rejected=$_.Exception.Message -like 'CIM identity absent*'}
Check $rejected 'Actual registration rejects PID reuse before persistence'
$report=[pscustomobject]@{schema='iw7.rig-first-write-static/1';status='candidate-route-requires-review';file_read_bytes=25162848;report_limit_bytes=3MB;
    reference_hashes_verified=$true;actual_first_writer_established=$false;live_breakpoint_established=$false;reference_live_provenance=$false;
    process_attached=$false;game_or_zonetool_launched=$false;acceptance_changed=$false;decoded_instructions=10;text_scans=2;linear_opcode_search_bytes=42270720}
Assert-LocatorReport $report;Check $true 'Source-bound read-only candidate report accepted within budget'
foreach($bad in @(@('actual_first_writer_established','false'),@('reference_hashes_verified','true'),@('decoded_instructions',128001))){
    $old=$report.($bad[0]);$report.($bad[0])=$bad[1];$blocked=$false
    try{Assert-LocatorReport $report}catch{$blocked=$true}
    Check $blocked 'Nonboolean proof/counter overrun refused';$report.($bad[0])=$old
}
# Targeted mode fixes its seed/bounds and cannot silently fall back to the broad scan.
$targetPlan=[pscustomobject]@{Schema='iw7.rig-locator-supervisor-plan/2';Phase='targeted-continuations';Entry='0x140a17970';
    TargetedLimits=[pscustomobject](Get-LocatorTargetedLimits);RunRoot=$plan.RunRoot;Python=$plan.Python;Script='C:\targeted.py';References=$plan.References}
Assert-LocatorTargetedPlan $targetPlan;Check $true 'Exact targeted Plan accepted without side effects'
$arguments=Get-LocatorArguments $targetPlan
Check ($arguments.EndsWith('"--entry" "0x140a17970"') -and $arguments.Contains('"C:\targeted.py"')) 'Targeted fixed argv selected'
foreach($bad in @(@('fragments',9),@('instructions','8192'),@('fragment_bytes',16385),@('decoded_bytes',32769),
    @('control_edges',64),@('control_edges',513),@('control_edges','512'),
    @('text_scans',1),@('seconds',11),@('external_callees_followed',1))){
    $old=$targetPlan.TargetedLimits.($bad[0]);$targetPlan.TargetedLimits.($bad[0])=$bad[1];$blocked=$false
    try{Assert-LocatorTargetedPlan $targetPlan}catch{$blocked=$true}
    Check $blocked 'Targeted Plan refuses widened or untyped bound';$targetPlan.TargetedLimits.($bad[0])=$old
}
$targetPlan.Entry='0x140a17971';$blocked=$false
try{Assert-LocatorTargetedPlan $targetPlan}catch{$blocked=$true}
Check $blocked 'Targeted Plan refuses a different seed';$targetPlan.Entry='0x140a17970'
$targetPlan.Entry='0x140a17e70';Assert-LocatorTargetedPlan $targetPlan
Check ((Get-LocatorArguments $targetPlan).EndsWith('"--entry" "0x140a17e70"')) 'Second reviewed seed uses only its own exact entry'
$targetPlan.Entry='0x140a17970'
$targetReport=$report|ConvertTo-Json -Depth 8|ConvertFrom-Json
$fields=@{schema='iw7.rig-targeted-static/2';entry='0x140a17970';limits=[pscustomobject](Get-LocatorTargetedLimits);
    decoded_instructions=1;visited_instructions=1;decoded_bytes=1;fragment_count=1;text_scans=0;linear_opcode_search_bytes=0;
    control_edge_count=0;control_edges=@();external_callees_followed=0;root_entries=1;elapsed_seconds=0.1;
    complete_logical_function_established=$false;continuation_same_function_established=$false;
    unvisited_is_unreachable=$false;frontier_queue_exhausted=$true;all_declared_frontiers_traversed=$true;
    refused_frontier_count=0;refused_frontiers=@();current_frontier=$null;pending_frontiers=@();
    fragments=@([pscustomobject]@{bytes=1;decode_complete=$true;instructions=@([pscustomobject]@{mnemonic='ret'})})}
foreach($key in $fields.Keys){$targetReport|Add-Member NoteProperty $key $fields[$key] -Force}
Assert-LocatorReport $targetReport -Targeted $true;Check $true 'Targeted typed report accepted'
foreach($bad in @(@('entry','0x140a17971'),@('text_scans',1),@('external_callees_followed',1),@('elapsed_seconds',10.01),
    @('complete_logical_function_established',$true),@('continuation_same_function_established','false'),
    @('fragment_count',9),@('control_edge_count',513),@('decoded_bytes',32769),@('decoded_instructions',8193),
    @('root_entries','1'),@('visited_instructions',2))){
    $old=$targetReport.($bad[0]);$targetReport.($bad[0])=$bad[1];$blocked=$false
    try{Assert-LocatorReport $targetReport -Targeted $true}catch{$blocked=$true}
    Check $blocked 'Targeted report refuses widening, overclaims, and inconsistent counters';$targetReport.($bad[0])=$old
}
foreach($bad in @(@('entry','0x140a17e70'),@('refused_frontier_count',1),@('unvisited_is_unreachable',$true),
    @('frontier_queue_exhausted',$false),@('all_declared_frontiers_traversed',$false),@('current_frontier',[pscustomobject]@{address='0x1'}))){
    $old=$targetReport.($bad[0]);$targetReport.($bad[0])=$bad[1];$blocked=$false
    try{Assert-LocatorReport $targetReport -Targeted $true}catch{$blocked=$true}
    Check $blocked 'Exact Plan entry and complete frontier accounting required';$targetReport.($bad[0])=$old
}
foreach($field in 'refused_frontiers','pending_frontiers'){
    $targetReport.$field=@([pscustomobject]@{address='0x1'});$blocked=$false
    try{Assert-LocatorReport $targetReport -Targeted $true}catch{$blocked=$true}
    Check $blocked 'Refused or pending frontier array prevents route acceptance';$targetReport.$field=@()
}
$targetReport.fragments[0].decode_complete=$false;$blocked=$false
try{Assert-LocatorReport $targetReport -Targeted $true}catch{$blocked=$true}
Check $blocked 'Partially decoded fragment prevents route acceptance';$targetReport.fragments[0].decode_complete=$true
$targetReport.fragments[0].bytes=16385;$targetReport.decoded_bytes=16385;$blocked=$false
try{Assert-LocatorReport $targetReport -Targeted $true}catch{$blocked=$true}
Check $blocked 'New per-fragment byte ceiling is enforced even within the total byte budget'
$targetReport.fragments[0].bytes=1;$targetReport.decoded_bytes=1
$targetReport.entry='0x140a17e70';Assert-LocatorReport $targetReport -Targeted $true -ExpectedEntry '0x140a17e70'
Check $true 'Report must match the second entry when that exact Plan selected it';$targetReport.entry='0x140a17970'
$edgeReport=$targetReport|ConvertTo-Json -Depth 8|ConvertFrom-Json
$edgeReport.control_edges=@(1..512|ForEach-Object {[pscustomobject]@{kind='call-not-followed';target='0x140011000'}})
$edgeReport.control_edge_count=512
$edgeReport.fragments[0].instructions=@(1..512|ForEach-Object {[pscustomobject]@{mnemonic='call'}})+@([pscustomobject]@{mnemonic='ret'})
$edgeReport.decoded_instructions=513;$edgeReport.visited_instructions=513
$edgeReport.decoded_bytes=2561;$edgeReport.fragments[0].bytes=2561
Assert-LocatorReport $edgeReport -Targeted $true
Check $true 'Exactly 512 reported edges accepted with consistent arrays and aggregate counters'
$edgeReport.control_edges+=@([pscustomobject]@{kind='call-not-followed';target='0x140011000'})
$edgeReport.control_edge_count=513
$edgeReport.fragments[0].instructions+=@([pscustomobject]@{mnemonic='call'})
$edgeReport.decoded_instructions=514;$edgeReport.visited_instructions=514
$edgeReport.decoded_bytes=2566;$edgeReport.fragments[0].bytes=2566
$blocked=$false;try{Assert-LocatorReport $edgeReport -Targeted $true}catch{$blocked=$_.Exception.Message -ceq 'Locator report counter exceeds fixed budget.'}
Check $blocked 'Edge 513 is refused by the fixed counter ceiling even with consistent arrays'
foreach($mode in $true,$false){
    $blocked=$false
    try{if($mode){Assert-LocatorReport $report -Targeted $true}else{Assert-LocatorReport $targetReport}}catch{$blocked=$true}
    Check $blocked 'Reports cannot cross broad/targeted Plan modes'
}
# Real file guards, without native types, protect a synthetic source file.
$temp=Join-Path ([IO.Path]::GetTempPath()) ('iw7-locator-test-'+[guid]::NewGuid().ToString('N'))
$null=New-Item -ItemType Directory -Path $temp
try{
    $file=Join-Path $temp 'source.txt';[IO.File]::WriteAllText($file,'original')
    $context=@{Guards=[Collections.Generic.List[IDisposable]]::new();Baselines=[Collections.Generic.List[object]]::new()}
    Add-LocatorGuard ([pscustomobject]@{Path=$file;SHA256=(Get-FileHash -LiteralPath $file).Hash.ToLowerInvariant();Bytes=8}) $context
    $blocked=$false;try{[IO.File]::WriteAllText($file,'changed')}catch{$blocked=$true}
    Check $blocked 'Read-sharing guard denies a concurrent write'
    foreach($guard in $context.Guards){$guard.Dispose()}
    Check ([IO.File]::ReadAllText($file) -ceq 'original') 'Guarded original bytes preserved'
    [IO.File]::WriteAllBytes((Join-Path $temp 'oversized.bin'),[byte[]]::new(4MB+1))
    [IO.File]::SetAttributes((Join-Path $temp 'oversized.bin'),[IO.FileAttributes]::Hidden)
    $blocked=$false;try{& $originalMeasure $temp|Out-Null}catch{$blocked=$true}
    Check $blocked 'Combined hidden/ordinary output ceiling refuses excess'
}finally{
    $resolved=[IO.Path]::GetFullPath($temp);$parent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    if(!$resolved.StartsWith($parent,[StringComparison]::OrdinalIgnoreCase) -or (Split-Path $resolved -Leaf) -notlike 'iw7-locator-test-*'){throw 'Unexpected synthetic test cleanup root'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
[pscustomobject]@{Checks=$script:checks;NativeProcessStarted=$false;RealLeaseAcquired=$false;Outcome='Passed'}|ConvertTo-Json

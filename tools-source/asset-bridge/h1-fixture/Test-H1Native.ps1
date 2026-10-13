# Light mocked lifecycle checks: no native types, leases, compiler or probe.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'H1Native.Core.ps1')
$reviewedBudget=${function:Test-H1Budget}
$passed=0
function Check([bool]$Value,[string]$Message){if(!$Value){throw $Message};$script:passed++}
function Refuses([scriptblock]$Action,[string]$Message){$failed=$false;try{& $Action|Out-Null}catch{$failed=$true};Check $failed $Message}
function New-FakeOwner([bool]$Empty=$true,[bool]$StopFails=$false,[int]$ExitCode=0) {
    $item=[pscustomobject]@{Empty=$Empty;StopFails=$StopFails;Closed=$false;ExitCode=$ExitCode;
        PID=123;Image='C:\fixture.exe';CreationFileTime=[datetime]::UtcNow.ToFileTimeUtc();Starts=0;Stops=0;StartFails=$false}
    $item|Add-Member ScriptMethod Start {param($a,$b,$c,$d) $this.Starts++;if($this.StartFails){throw 'Partial start failure'}}
    $item|Add-Member ScriptMethod TreeExited {return $this.Empty}
    $item|Add-Member ScriptMethod CloseConfirmed {if(!$this.Empty){throw 'not empty'};$this.Closed=$true}
    $item|Add-Member ScriptMethod StopAndConfirm {param($timeout) $this.Stops++;if($this.StopFails){throw 'unknown closure'};$this.Empty=$true;$this.Closed=$true}
    $item
}
function New-Case {
    $script:events=[Collections.Generic.List[string]]::new()
    $script:clock=0;$script:registrationFails=$false;$script:telemetryDelay=0;$script:releaseFails=$false;$script:factoryFails=$false
    [pscustomobject]@{Owner=$null;Closed=$true;Lease=[pscustomobject]@{Token=[guid]::NewGuid().ToString('N')};Guards=@()}
}
function New-State($Context) {
    [ordered]@{Status='Pending';Stage='Probe';DeadlineSeconds=15;LeaseToken=$Context.Lease.Token;LeaseReleased=$false;
        Quarantined=$false;TreeClosureConfirmed=$true;MaxObservedOutputBytes=0L}
}
function New-H1Owner {if($script:factoryFails){throw 'Factory failed'};$script:fake}
function Get-H1Clock {$script:clock}
function Register-H1Original($Lease,$Identity){$script:events.Add('register');if($script:registrationFails){throw 'CIM absent'}}
function Test-H1Budget($Plan,$State){$script:clock+=$script:telemetryDelay}
function Exit-IW7ResourceLease($Token){$script:events.Add('release');if($script:releaseFails){throw 'release refused'}}
$start=[pscustomobject]@{FileName='C:\fixture.exe'}
$context=New-Case;$state=New-State $context;$script:fake=New-FakeOwner
Invoke-H1OwnedStage $null $state $context $start ('a'*64) 'C:\unused'
Complete-H1Stage $context $state
Check ($state.TreeClosureConfirmed -and $state.LeaseReleased -and $script:fake.Stops -eq 0) 'Normal original-tree closure/release failed.'
Check (($script:events -join ',') -ceq 'register,release') 'Stage registration/release ordering differs.'

$context=New-Case;$state=New-State $context;$script:fake=New-FakeOwner
Refuses {Invoke-H1OwnedStage $null $state $context $start ('a'*64) 'C:\unused' -15000} 'Expired admitted setup budget must prevent process creation.'
Check ($script:fake.Starts -eq 0 -and $context.Closed) 'Setup consumed the deadline but still launched a native child.'

$context=New-Case;$state=New-State $context;$script:fake=New-FakeOwner;$script:registrationFails=$true
Invoke-H1OwnedStage $null $state $context $start ('a'*64) 'C:\unused'
Complete-H1Stage $context $state
Check ($state.Registration -like 'Original job already empty*' -and $state.LeaseReleased) 'Fast exit must use original empty-job evidence.'

$context=New-Case;$state=New-State $context;$script:fake=New-FakeOwner $false;$script:registrationFails=$true
Refuses {Invoke-H1OwnedStage $null $state $context $start ('a'*64) 'C:\unused'} 'Live child with unavailable identity must fail.'
Complete-H1Stage $context $state
Check ($script:fake.Stops -eq 1 -and $state.TreeClosureConfirmed -and $state.LeaseReleased) 'Failure cleanup must stop/confirm original job before release.'

$context=New-Case;$state=New-State $context;$script:fake=New-FakeOwner;$script:telemetryDelay=15001
Refuses {Invoke-H1OwnedStage $null $state $context $start ('a'*64) 'C:\unused'} 'Slow telemetry must not allow late success.'
Complete-H1Stage $context $state
Check $state.LeaseReleased 'Deadline failure cleanup did not release a closed job.'

$context=New-Case;$state=New-State $context;$script:fake=New-FakeOwner $false $true;$script:registrationFails=$true
Refuses {Invoke-H1OwnedStage $null $state $context $start ('a'*64) 'C:\unused'} 'Unknown closure setup failed.'
Complete-H1Stage $context $state
Check ($state.Quarantined -and !$state.LeaseReleased -and $context.Lease -and !($script:events.Contains('release'))) 'Unconfirmed closure released a lease.'
[AppDomain]::CurrentDomain.SetData(('IW7.H1.Quarantine.'+$state.LeaseToken),$null)

$context=New-Case;$state=New-State $context;$script:factoryFails=$true
Refuses {Invoke-H1OwnedStage $null $state $context $start ('a'*64) 'C:\unused'} 'Throwing factory must fail the stage.'
Complete-H1Stage $context $state
Check ($state.Quarantined -and !$state.LeaseReleased) 'A failed owner factory must not prove closure.'
[AppDomain]::CurrentDomain.SetData(('IW7.H1.Quarantine.'+$state.LeaseToken),$null)

$context=New-Case;$state=New-State $context;$script:fake=New-FakeOwner $false;$script:fake.StartFails=$true
Refuses {Invoke-H1OwnedStage $null $state $context $start ('a'*64) 'C:\unused'} 'Partial native start must fail.'
Complete-H1Stage $context $state
Check ($script:fake.Stops -eq 1 -and $state.LeaseReleased) 'Owner was lost across a partial start exception.'

$context=New-Case;$state=New-State $context;$script:fake=New-FakeOwner $true $false 7
Refuses {Invoke-H1OwnedStage $null $state $context $start ('a'*64) 'C:\unused'} 'Nonzero native exit must fail.'
Complete-H1Stage $context $state
Check ($state.ExitCode -eq 7 -and $state.LeaseReleased) 'Nonzero exit must retain exit evidence after cleanup.'

$context=New-Case;$state=New-State $context;$script:fake=New-FakeOwner;$script:releaseFails=$true
Invoke-H1OwnedStage $null $state $context $start ('a'*64) 'C:\unused'
Complete-H1Stage $context $state
Check ($state.Quarantined -and $state.TreeClosureConfirmed -and !$state.LeaseReleased) 'Scheduler release refusal must quarantine admission.'
[AppDomain]::CurrentDomain.SetData(('IW7.H1.Quarantine.'+$state.LeaseToken),$null)

$temp=Join-Path ([IO.Path]::GetTempPath()) ('iw7-h1-source-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($temp)|Out-Null
$path=Join-Path $temp 'bound.txt'
try {
    [IO.File]::WriteAllText($path,'original')
    $pin=[pscustomobject]@{Path=$path;Bytes=8;SHA256=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()}
    $guard=Open-H1Pin $pin
    try{Refuses {[IO.File]::WriteAllText($path,'mutated!')} 'An open input guard must deny writing.'}finally{$guard.Dispose()}
    [IO.File]::WriteAllText($path,'mutated!')
    Refuses {Open-H1Pin $pin} 'Same-length changed source must fail binding.'
    [IO.File]::WriteAllText($path,('x'*130))
    Refuses {Read-H1SmallJson $path 128} 'JSON size bound failed.'
    $budgetPlan=[pscustomobject]@{RunRoot=$temp;OutputLimitBytes=16KB;MetadataReserveBytes=1KB}
    $script:memoryReads=0;$script:memoryFails=$false
    function Get-IW7ResourceSnapshot {
        $script:memoryReads++
        if($script:memoryFails){throw 'Synthetic native memory provider failed.'}
        $script:memorySnapshot
    }
    foreach($percent in @(84.99,85,85.01,99,100)){
        $script:memorySnapshot=[pscustomobject]@{CommitLimit=1000000L;Committed=[long]($percent*10000);
            CapturedUtc=[datetime]::UtcNow.ToString('o');Source='synthetic-no-allocation'}
        foreach($budgetState in @([ordered]@{MaxObservedOutputBytes=0L},[pscustomobject]@{MaxObservedOutputBytes=0L})){
            & $reviewedBudget $budgetPlan $budgetState
            Check ($budgetState.LastMemoryObservation.Policy -ceq 'TelemetryOnly' -and
                $budgetState.LastMemoryObservation.CommitUsedPercent -eq $percent) 'Near/high commit percentage refused or lost telemetry.'
            Check ($budgetState.MaxObservedOutputBytes -eq 130) 'Memory policy change must preserve actual output accounting.'
        }
    }
    Check ($script:memoryReads -eq 10) 'Every budget observation must read fresh native telemetry.'
    $budgetState=[ordered]@{MaxObservedOutputBytes=0L}
    $script:memorySnapshot=[pscustomobject]@{CommitLimit=1000000L;Committed=850100L}
    & $reviewedBudget $budgetPlan $budgetState
    $script:memorySnapshot=[pscustomobject]@{CommitLimit=1000000L;Committed=990000L}
    & $reviewedBudget $budgetPlan $budgetState
    Check ($budgetState.LastMemoryObservation.CommitUsedPercent -eq 99 -and
        @($budgetState.Keys | Where-Object {$_ -eq 'LastMemoryObservation'}).Count -eq 1) 'Fresh observations must replace one bounded record.'
    foreach($invalid in @($null,[pscustomobject]@{CommitLimit=0;Committed=0},
        [pscustomobject]@{CommitLimit=100;Committed=-1},[pscustomobject]@{CommitLimit=100;Committed=101})){
        $script:memorySnapshot=$invalid
        Refuses {& $reviewedBudget $budgetPlan $budgetState} 'Missing/impossible telemetry must still fail.'
    }
    $script:memoryFails=$true
    Refuses {& $reviewedBudget $budgetPlan $budgetState} 'A native memory provider exception must still fail.'
    $script:memoryFails=$false
    $script:memorySnapshot=[pscustomobject]@{CommitLimit=1000000L;Committed=990000L}
    # Exercise the actual budget observer together with synthetic original-job
    # OOM failure/cleanup. No native process or pressure allocation is induced.
    $lifecycleBudget=${function:Test-H1Budget}
    try {
        ${function:Test-H1Budget}=$reviewedBudget
        $context=New-Case;$state=New-State $context;$script:fake=New-FakeOwner $true $false -1073741801
        Refuses {Invoke-H1OwnedStage $budgetPlan $state $context $start ('a'*64) 'C:\unused'} 'An out-of-memory exit must not be converted to success.'
        Complete-H1Stage $context $state
        Check ($state.ExitCode -eq -1073741801 -and $state.LeaseReleased -and
            $state.LastMemoryObservation.CommitUsedPercent -eq 99) 'OOM failure/confirmed teardown must survive telemetry-only memory.'
    }finally{${function:Test-H1Budget}=$lifecycleBudget}
    $overOutputPlan=[pscustomobject]@{RunRoot=$temp;OutputLimitBytes=130;MetadataReserveBytes=1}
    Refuses {& $reviewedBudget $overOutputPlan $budgetState} 'Output cap must still fail even with telemetry-only memory.'
    $outputPlan=[pscustomobject]@{RunRoot=$temp;OutputLimitBytes=132;MetadataReserveBytes=128}
    Refuses {Write-H1Receipt $outputPlan ([ordered]@{Status='Passed'}) $temp} 'Final receipt must count its own bytes.'
    Check (!(Test-Path -LiteralPath (Join-Path $temp 'receipt.json'))) 'Oversized success receipt was published.'
}finally{
    # Only these exact test-created files; never recursive deletion.
    foreach($name in 'bound.txt','receipt.pending.json','receipt.json') {
        $item=Join-Path $temp $name;if([IO.File]::Exists($item)){[IO.File]::Delete($item)}
    }
    [IO.Directory]::Delete($temp,$false)
}
Check (!(('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7ResourceMemoryV1' -as [type]))) 'Light tests loaded native providers.'
[ordered]@{Schema='iw7.h1-native-runner-source-tests/1';Assertions=$passed;NativeTypesLoaded=$false;
    RealJobsTested=$false;LeaseAcquired=$false;CompilerLaunched=$false}|ConvertTo-Json

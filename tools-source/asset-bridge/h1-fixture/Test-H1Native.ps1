# Light mocked lifecycle checks: no native types, leases, compiler or probe.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'H1Native.Core.ps1')
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
    [ordered]@{Status='Pending';DeadlineSeconds=15;LeaseToken=$Context.Lease.Token;LeaseReleased=$false;
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

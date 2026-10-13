[CmdletBinding()]
param([Parameter(Mandatory)][string]$PolicySource)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
if((Get-FileHash -LiteralPath $PolicySource).Hash -ine 'fc024337fdb18c8a759cd6346ad90fe1fb2086d790e4804ade583c30e69d25d6'){throw 'Reviewed MaterialV2 policy required.'}
. $PolicySource
. (Join-Path $PSScriptRoot 'H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'H1Native.Compiler.ps1')
$checks=0
function Check([bool]$Value,[string]$Message){if(!$Value){throw $Message};$script:checks++}
function Refuses([scriptblock]$Body){$caught=$false;try{& $Body|Out-Null}catch{$caught=$true};Check $caught 'Invalid telemetry closure accepted.'}
function New-Fixture {
    $script:tick=0;$script:stops=0;$script:states=0;$script:inputsFail=$false;$script:toolsFail=$false
    $script:artifactsFail=$false;$script:stopFails=$false;$script:stopDelay=0;$script:budgetDelay=0
    $policy=Get-MaterialV2CompilerPolicy 'C:\toolset\cl.exe'
    $identity=[pscustomobject]@{PID=37;Image=$policy.Compiler;CreatedUtc='2026-10-12T04:00:00.0000000Z'}
    $snapshot=[pscustomobject]@{PID=37;Image=$identity.Image;CreatedUtc=$identity.CreatedUtc;RootExited=$true;RootExitCode=0;ActiveProcesses=1}
    $member=[pscustomobject]@{PID=38;ParentPID=37;Image=$policy.Telemetry;CreatedUtc='2026-10-12T04:00:00.3000000Z';InOriginalJob=$true;Error=$null;ParentError=$null}
    $first=[pscustomobject]@{AssignedCount=1;ListedCount=1;CapturedUtc='2026-10-12T04:00:01.0000000Z';Members=@($member)}
    $second=[pscustomobject]@{AssignedCount=1;ListedCount=1;CapturedUtc='2026-10-12T04:00:01.1000000Z';Members=@($member.PSObject.Copy())}
    $empty=[pscustomobject]@{AssignedCount=0;ListedCount=0;CapturedUtc='2026-10-12T04:00:01.2000000Z';Members=@()}
    $script:captures=[Collections.Generic.Queue[object]]::new()
    $script:captures.Enqueue($first);$script:captures.Enqueue($second);$script:captures.Enqueue($empty)
    $script:snapshot=$snapshot
    $owner=[pscustomobject]@{PID=37;Image=$identity.Image;CreationFileTime=([datetime]$identity.CreatedUtc).ToFileTimeUtc();Active=1;Closed=$false;ExitCode=0}
    $owner|Add-Member ScriptMethod Start {param($a,$b,$c,$d)}
    $owner|Add-Member ScriptMethod TreeExited {return $this.Active -eq 0}
    $owner|Add-Member ScriptMethod CloseConfirmed {if($this.Active -ne 0){throw 'still active'};$this.Closed=$true}
    $script:expectedOwner=$owner
    [pscustomobject]@{Policy=$policy;Snapshot=$snapshot;Identity=$identity;First=$first;Second=$second;Empty=$empty;
        Plan=[pscustomobject]@{Compiler=$policy.Compiler;Bindings=@(1,2)};
        Context=[pscustomobject]@{Owner=$owner;Closed=$false;Lease=[pscustomobject]@{Token='mock-only'};Guards=@()};
        State=[ordered]@{Stage='Compile';PlanSHA256=('a'*64);Identity=$identity;DeadlineSeconds=120;CompilerTelemetry=[ordered]@{Completed=$false};
            MaxObservedOutputBytes=0;LeaseToken='mock-only';LeaseReleased=$false;Quarantined=$false}}
}
function Get-H1Clock {$script:tick}
function Start-Sleep {param($Milliseconds) $script:tick+=$Milliseconds}
function Test-H1Budget($Plan,$State){$script:tick+=$script:budgetDelay}
function Confirm-H1BoundInputs($Plan){if($script:inputsFail){throw 'Bound source changed'}}
function Assert-H1CompilerToolPins($Plan,$Policy){if($script:toolsFail){throw 'Pinned compiler/telemetry changed'}}
function Get-H1CompilerArtifacts($Plan,$Context){if($script:artifactsFail){throw 'Artifact missing'};[pscustomobject]@{Path='C:\run\compile\native_probe.exe';Bytes=1;SHA256=('b'*64)}}
function Get-H1OriginalMembers($Owner){if(![object]::ReferenceEquals($Owner,$script:expectedOwner)){throw 'Wrong owner'};$script:captures.Dequeue()}
function Get-H1OriginalState($Owner){$script:states++;$result=$script:snapshot.PSObject.Copy();$result.ActiveProcesses=$Owner.Active;$result}
function Stop-H1OriginalJob($Owner){
    if(![object]::ReferenceEquals($Owner,$script:expectedOwner)){throw 'Wrong owner'}
    $script:stops++;$script:tick+=$script:stopDelay
    if($script:stopFails){throw 'Original job stop failed'};$Owner.Active=0
}
function Complete($f){Complete-H1CompilerTelemetry $f.Plan $f.State $f.Context $f.Snapshot 0}
$f=New-Fixture
Check (Complete $f) 'Exact direct-root compiler/telemetry case failed.'
Check ($script:stops -eq 1 -and $f.State.CompilerTelemetry.Completed -and !$f.Context.Owner.Closed -and $script:captures.Count -eq 0) 'Two live captures plus fresh empty capture required; handles must remain open.'
Check (!(Complete $f) -and $script:stops -eq 1) 'Do not repeat accepted cleanup.'
foreach($code in @(1,$null,'0')){
    $f=New-Fixture;$f.Snapshot.RootExitCode=$code;Refuses {Complete $f}
    Check ($script:stops -eq 0) 'Invalid compiler exit must not trigger accepted stop.'
}
$f=New-Fixture;$f.Snapshot.RootExited=$false
Check (!(Complete $f) -and $script:stops -eq 0) 'Live compiler cannot trigger accepted cleanup.'
$f=New-Fixture;$f.Snapshot.ActiveProcesses=0
Check (!(Complete $f) -and $script:stops -eq 0) 'Empty job needs no telemetry stop.'
foreach($entry in @(@('PID',99),@('Image','C:\wrong\cl.exe'),@('CreatedUtc','2026-10-12T04:00:00.1000000Z'))){
    $f=New-Fixture;$f.Snapshot.($entry[0])=$entry[1];Refuses {Complete $f}
    Check ($script:stops -eq 0) 'Changed original-root identity accepted.'
}
foreach($entry in @(@('Image','C:\other\vctip.exe'),@('Image','C:\toolset\mspdbsrv.exe'),@('ParentPID',99),
    @('InOriginalJob',$false),@('Error','inaccessible'),@('ParentError','unknown'),@('PID','38'),@('PID',37),
    @('CreatedUtc','2026-10-12T03:59:59.0000000Z'),@('CreatedUtc','2026-10-12T04:00:02.0000000Z'))){
    $f=New-Fixture;$f.First.Members[0].($entry[0])=$entry[1];Refuses {Complete $f}
    Check ($script:stops -eq 0) 'Unknown/outside/reused descendant entered accepted cleanup.'
}
foreach($field in 'AssignedCount','ListedCount'){$f=New-Fixture;$f.First.$field=2;Refuses {Complete $f}}
$f=New-Fixture;$f.First.Members+=,$f.First.Members[0];Refuses {Complete $f}
$f=New-Fixture;$f.Snapshot.ActiveProcesses=2;Refuses {Complete $f}
foreach($field in 'PID','ParentPID','Image','CreatedUtc') {
    $f=New-Fixture
    switch($field){'PID'{$value=39};'ParentPID'{$value=99};'Image'{$value='C:\other\vctip.exe'};'CreatedUtc'{$value='2026-10-12T04:00:00.4000000Z'}}
    $f.Second.Members[0].$field=$value;Refuses {Complete $f}
    Check ($script:stops -eq 0) 'Second capture drift must prevent accepted stop.'
}
$f=New-Fixture;$f.Second.CapturedUtc='2026-10-12T04:00:00.9000000Z';Refuses {Complete $f}
foreach($fault in 'inputsFail','toolsFail','artifactsFail') {
    $f=New-Fixture;Set-Variable -Scope Script -Name $fault -Value $true;Refuses {Complete $f}
    Check ($script:stops -eq 0) 'Unbound inputs/artifacts cannot enter accepted cleanup.'
}
$f=New-Fixture;$script:stopFails=$true;Refuses {Complete $f}
Check (!$f.State.CompilerTelemetry.Completed) 'Failed stop cannot be completion.'
$f=New-Fixture;$script:stopDelay=5001;Refuses {Complete $f}
Check (!$f.State.CompilerTelemetry.Completed) 'Late original-job stop cannot be completion.'
$f=New-Fixture;$script:budgetDelay=120001;Refuses {Complete $f}
Check ($script:stops -eq 0) 'Deadline expired after telemetry cannot enter accepted stop.'
$f=New-Fixture;$f.Empty.AssignedCount=1;Refuses {Complete $f}
Check (!$f.State.CompilerTelemetry.Completed) 'Fresh nonempty job capture cannot be accepted.'

# Exercise the REAL wait orchestration around the mocked observations.
function New-H1Owner {$script:expectedOwner}
function Register-H1Original($Lease,$Identity){}
function Exit-IW7ResourceLease($Token){}
$f=New-Fixture
Invoke-H1OwnedStage $f.Plan $f.State $f.Context ([pscustomobject]@{FileName=$f.Policy.Compiler}) $f.Policy.CompilerSHA256 'C:\unused'
Check ($f.Context.Closed -and $f.State.LastOriginalSnapshot.ActiveProcesses -eq 0 -and $script:states -eq 4) 'Fresh ordinary root0/Active0 poll after accepted stop is mandatory.'
Complete-H1Stage $f.Context $f.State
Check ($f.State.TreeClosureConfirmed -and $f.State.LeaseReleased) 'Only fresh closed stage can release admission.'

$cs=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'H1Native.JobMembers.cs') -Raw
Check ($cs -notmatch 'CreateProcess|TerminateProcess|TerminateJobObject|AssignProcessToJobObject|DebugActiveProcess') 'Observer must introduce no launch, stop, reassignment or attach primitive.'
Check ($cs -match 'DangerousAddRef' -and $cs -match 'DangerousRelease' -and $cs -match 'OpenProcess\(0x1000, false, pid\)') 'Observer must protect borrowed handles and use limited query access.'
Check (!(('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7.H1Diagnostics.JobMembers' -as [type]) -or ('IW7ResourceMemoryV1' -as [type]))) 'Source tests loaded native providers.'
[ordered]@{Schema='iw7.h1-compiler-closure-source-tests/1';Assertions=$checks;RealJobsTested=$false;NativeTypesLoaded=$false;LeaseAcquired=$false}|ConvertTo-Json

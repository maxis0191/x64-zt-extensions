$ErrorActionPreference='Stop'
. "$PSScriptRoot/Watchpoint.Core.ps1"
function Check($Condition,[string]$Message){if(!$Condition){throw $Message}}
function Fixture {
    $script:s=New-RigWatchFixtureState ('a'*32)
    $script:s.Identity=[pscustomobject]@{PID=100;CreatedUtc='2026-10-12T01:00:00.0000000Z'}
    $script:target=[pscustomobject]@{pid=200;tid=201;created_filetime=([datetime]'2026-10-12T01:00:01Z').ToFileTimeUtc();
        OriginalHandles=$true;CreatedSuspended=$true;PrimaryResumed=$false;CreationFlags=0x08004004;InheritedHandles=$false}
    $script:event=[pscustomobject]@{Status='TargetCreatedStopped';Target=$script:target;DebuggerPID=$null}
    $script:members=@(
        [pscustomobject]@{PID=100;Image='C:\fake\python.exe';CreatedUtc='2026-10-12T01:00:00.0000000Z';InOriginalJob=$true;Error=$null;ParentPID=99},
        [pscustomobject]@{PID=200;Image='C:\fake\python.exe';CreatedUtc='2026-10-12T01:00:01.0000000Z';InOriginalJob=$true;Error=$null;ParentPID=100})
    $script:obs=[pscustomobject]@{CapturedUtc='2026-10-12T01:00:02Z';AssignedCount=2;ListedCount=2;Members=$script:members}
}
function Confirm {Confirm-RigWatchFixtureMembers $script:s $script:event $script:obs 'C:\fake\python.exe' 'C:\fake\cdb.exe'}
function Attached {
    Confirm
    $script:event.Status='AttachedStopped';$script:event.DebuggerPID=300
    $script:obs=[pscustomobject]@{CapturedUtc='2026-10-12T01:00:04Z';AssignedCount=3;ListedCount=3;Members=@($script:members)+@(
        [pscustomobject]@{PID=300;Image='C:\fake\cdb.exe';CreatedUtc='2026-10-12T01:00:03.0000000Z';InOriginalJob=$true;Error=$null;ParentPID=100})}
}
Fixture;Confirm
Check ($script:event.OriginalJobChecked -and !$script:s.DescendantClosureUnproven -and $script:s.Context.CreationMembership.ListedCount -eq 2) 'Creation proof was not retained'
Fixture;Attached;Confirm
Check ($script:event.OriginalJobChecked -and $script:s.Context.AttachedMembership.ListedCount -eq 3) 'Attached membership failed'
$cases=0
foreach($edit in @(
    {$script:obs.AssignedCount=1},
    {$script:obs.ListedCount=1},
    {$script:obs.Members=@($script:members[0])},
    {$script:members[1].InOriginalJob=$false},
    {$script:members[1].InOriginalJob='true'},
    {$script:members[1].Error='query failed'},
    {$script:members[1].Image='C:\foreign\python.exe'},
    {$script:members[0].CreatedUtc='2026-10-12T01:00:00.0000001Z'},
    {$script:target.pid=100},
    {$script:target.pid='200'},
    {$script:target.created_filetime++},
    {$script:target.OriginalHandles=$false},
    {$script:target.CreatedSuspended=$false},
    {$script:target.PrimaryResumed=$true},
    {$script:target.CreationFlags=0x09004004},
    {$script:target.InheritedHandles=$true},
    {$script:event.DebuggerPID=300}
)){
    Fixture;& $edit;$refused=$false
    try{Confirm}catch{$refused=$true}
    Check ($refused -and $script:s.DescendantClosureUnproven) 'Unproven initial creation accepted'
    Check ([object]::ReferenceEquals($script:s.Context.LastMembership,$script:obs)) 'Failed snapshot discarded'
    $cases++
}
foreach($edit in @(
    {$script:obs.Members[2].InOriginalJob=$false},
    {$script:obs.Members[2].Image='C:\foreign\cdb.exe'},
    {$script:obs.Members[2].PID=100},
    {$script:obs.Members[2].CreatedUtc='2026-10-12T01:00:00.0000000Z'},
    {$script:event.DebuggerPID=301}
)){
    Fixture;Attached;& $edit;$refused=$false
    try{Confirm}catch{$refused=$true}
    Check ($refused -and $script:s.DescendantClosureUnproven -and $script:s.Context.CreationMembership.ListedCount -eq 2) 'Attached failure lost original creation evidence'
    $cases++
}
Fixture;Attached;Confirm
$script:event.Status='ArmedStopped'
$script:event.Target=[pscustomobject]@{pid=200;created_filetime=$script:target.created_filetime}
Confirm
$script:event.Target.created_filetime++;$refused=$false
try{Confirm}catch{$refused=$true}
Check ($refused -and $script:s.DescendantClosureUnproven) 'Changed post-start fixture accepted'
$cases++
Write-Output "PASS 2/3 original-member proofs and $cases identity/ownership refusals, with failed snapshot retention; pure objects only."

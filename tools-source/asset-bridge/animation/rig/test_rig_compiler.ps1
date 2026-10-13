$ErrorActionPreference='Stop'
. "$PSScriptRoot/Rig.Core.ps1"
. "$PSScriptRoot/Rig.Compiler.ps1"
$checks=0
function Check([bool]$Value,[string]$Message){if(!$Value){throw $Message};$script:checks++}
function Refuse([scriptblock]$Body){$caught=$false;try{& $Body|Out-Null}catch{$caught=$true};Check $caught 'Invalid compiler closure was accepted'}
foreach($name in 'Rig.Compiler.ps1','Build-RigChain.ps1'){
    $tokens=$null;$errors=$null
    $null=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $name),[ref]$tokens,[ref]$errors)
    Check (!$errors.Count) "$name parse"
}
function New-Fixture {
    $policy=Get-RigCompilerPolicy 'C:\toolset\cl.exe'
    $owner=[pscustomobject]@{Exited=$true;Active=1;ExitCode=0}
    $compiler=[pscustomobject]@{PID=37;ParentPID=36;Image=$policy.Compiler;CreatedUtc='2026-10-12T04:00:00.0000000Z';InOriginalJob=$true;Error=$null;ParentError=$null}
    $member=[pscustomobject]@{PID=38;ParentPID=37;Image=$policy.Telemetry;CreatedUtc='2026-10-12T04:00:00.3000000Z';InOriginalJob=$true;Error=$null;ParentError=$null}
    $observation=[pscustomobject]@{AssignedCount=1;ListedCount=1;CapturedUtc='2026-10-12T04:00:01.0000000Z';Members=@($member)}
    $evidence=[ordered]@{CompilerIdentity=$null;Completed=$false}
    Update-RigCompilerWitness $evidence ([pscustomobject]@{Members=@($compiler)}) 36 $policy
    $script:expectedOwner=$owner;$script:stopCalls=0;$script:hashCalls=0;$script:stopFails=$false;$script:hashFails=$false
    [pscustomobject]@{Owner=$owner;Policy=$policy;Compiler=$compiler;Member=$member;Observation=$observation;Evidence=$evidence;
        Snapshot=[pscustomobject]@{RootExited=$true;RootExitCode=0;ActiveProcesses=1};
        Receipt=[pscustomobject]@{schema='iw7.rig-chain-phase-result/1';phase='compile';pid=37;exit_code=0;failure=$null;executable_sha256=$policy.CompilerSHA256;spec_sha256=('a'*64);log_limit_each=2MB;ownership='outer original Windows job'}}
}
function Assert-BeaconHash($Path,$Hash){
    $script:hashCalls++
    if($script:hashFails){throw 'Mock pinned tool changed'}
    if($Path -cnotin 'C:\toolset\cl.exe','C:\toolset\vctip.exe' -or $Hash.Length -ne 64){throw 'Wrong image hash gate'}
}
function Stop-RigOwnedPhase($Owner,$Evidence){
    if(![object]::ReferenceEquals($Owner,$script:expectedOwner)){throw 'Different original owner'}
    $script:stopCalls++;$Evidence.Closed=!$script:stopFails
    if($script:stopFails){return $false}
    $Owner.Active=0
    return $true
}
function Complete($f){Complete-RigCompilerTelemetry $f.Owner $f.Snapshot $f.Observation $f.Receipt $f.Evidence $f.Policy}
$f=New-Fixture
Check (Complete $f) 'Exact witnessed vctip should close only its original job'
Check ($script:stopCalls -eq 1 -and $script:hashCalls -eq 2 -and $f.Evidence.Completed -and $f.Owner.Active -eq 0) 'Original job closure and both image hashes required'
Check (!(Complete $f) -and $script:stopCalls -eq 1) 'No repeated telemetry stop'
foreach($entry in @(@('RootExitCode',1),@('RootExitCode',$null),@('RootExitCode','0'))){
    $f=New-Fixture;$f.Snapshot.($entry[0])=$entry[1];Refuse {Complete $f}
    Check ($script:stopCalls -eq 0) 'Root failure must not enter accepted cleanup'
}
$f=New-Fixture;$f.Snapshot.RootExited=$false
Check (!(Complete $f) -and $script:stopCalls -eq 0) 'Live root cannot trigger telemetry closure'
$f=New-Fixture;$f.Snapshot.ActiveProcesses=0
Check (!(Complete $f) -and $script:stopCalls -eq 0) 'Empty job needs no telemetry stop'
foreach($entry in @(@('phase','write'),@('exit_code',1),@('exit_code',$null),@('exit_code','0'),@('pid',99),@('pid',$null),@('failure','timeout'),@('executable_sha256',('b'*64)))){
    $f=New-Fixture;$f.Receipt.($entry[0])=$entry[1];Refuse {Complete $f}
    Check ($script:stopCalls -eq 0) 'Invalid native receipt must not enter accepted cleanup'
}
$f=New-Fixture;$f.Evidence.CompilerIdentity=$null;Refuse {Complete $f}
Check ($script:stopCalls -eq 0) 'Receipt PID alone is not compiler identity'
foreach($entry in @(@('Image','C:\other\vctip.exe'),@('Image','C:\toolset\mspdbsrv.exe'),@('ParentPID',99),
    @('InOriginalJob',$false),@('Error','inaccessible'),@('ParentError','unknown'),@('PID','38'),
    @('CreatedUtc','2026-10-12T03:59:59.0000000Z'),@('CreatedUtc','2026-10-12T04:00:02.0000000Z'))){
    $f=New-Fixture;$f.Member.($entry[0])=$entry[1];Refuse {Complete $f}
    Check ($script:stopCalls -eq 0) 'Unknown/outside/reused descendant must not enter accepted cleanup'
}
foreach($field in 'AssignedCount','ListedCount'){
    $f=New-Fixture;$f.Observation.$field=2;Refuse {Complete $f}
}
$f=New-Fixture;$f.Observation.Members+=,$f.Member;Refuse {Complete $f}
$f=New-Fixture;$f.Snapshot.ActiveProcesses=2;Refuse {Complete $f}
$f=New-Fixture;$script:hashFails=$true;Refuse {Complete $f}
Check ($script:stopCalls -eq 0) 'Changed image hash refuses accepted stop'
$f=New-Fixture;$script:stopFails=$true;Refuse {Complete $f}
Check (!$f.Evidence.Completed -and $f.Owner.Active -eq 1 -and $script:stopCalls -eq 1) 'Stop without closure is never completion'
$f=New-Fixture;$changed=$f.Compiler.PSObject.Copy();$changed.CreatedUtc='2026-10-12T04:00:00.1000000Z'
Refuse {Update-RigCompilerWitness $f.Evidence ([pscustomobject]@{Members=@($changed)}) 36 $f.Policy}
$f=New-Fixture;$f.Compiler.ParentPID=99
Refuse {Update-RigCompilerWitness $f.Evidence ([pscustomobject]@{Members=@($f.Compiler)}) 36 $f.Policy}
# The real wait function still needs a FRESH zero-active sample after mocked Stop.
function Get-RigMonotonicMs {$script:tick}
function Get-RigUtcNow {[datetime]::new(2026,10,12,4,0,0,[DateTimeKind]::Utc)}
function Start-Sleep {param($Milliseconds) $script:tick+=$Milliseconds}
$script:tick=10000;$f=New-Fixture;$identity=[ordered]@{}
Wait-RigOwnedPhase $f.Owner $identity 10000 240 {
    param($sample,$changed)
    $null=Complete-RigCompilerTelemetry $f.Owner $sample $f.Observation $f.Receipt $f.Evidence $f.Policy
}
Assert-RigPhaseResult $f.Receipt 'compile' $f.Policy.CompilerSHA256 ('a'*64) $identity
Check ($identity.Supervision.PollCount -eq 2 -and $identity.JobRootExitedAtClose -and $identity.JobActiveAtClose -eq 0 -and
    $identity.ExitCode -eq 0 -and $script:stopCalls -eq 1) 'Receipt cannot replace fresh exact-owner zero-active gate'
$source=Get-Content -LiteralPath "$PSScriptRoot/Rig.Compiler.ps1" -Raw
Check ($source -notmatch 'SetEnvironmentVariable|Set-Item.+Env:|Stop-Process|taskkill|TerminateProcess') 'No persistent environment or PID/global kill'
"PASS: $checks compiler-closure source/mocked checks; no native process, Add-Type, lease or environment change."

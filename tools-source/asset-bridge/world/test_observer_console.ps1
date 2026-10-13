$ErrorActionPreference='Stop'
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
. "$repo/sdk/modding/BeaconFF.Core.ps1"
. "$repo/tools-source/asset-bridge/surfaces/MaterialV2.Core.ps1"
. "$repo/tools-source/asset-bridge/surfaces/MaterialV2.Compiler.ps1"
. "$PSScriptRoot/ObserverHarness.Core.ps1"
$script:checks=0
function Check($Value,[string]$Message){if(!$Value){throw $Message};$script:checks++}
function Refuse([scriptblock]$Body){$caught=$false;try{& $Body|Out-Null}catch{$caught=$true};Check $caught 'Invalid console fixture accepted'}
function New-ConsoleCase {
    $policy=Get-MaterialV2CompilerPolicy 'C:\reviewed\cl.exe'
    $consolePolicy=Get-WorldObserverConsolePolicy
    $root=[pscustomobject]@{PID=100;Image='C:\reviewed\python.exe';CreatedUtc='2026-10-12T11:28:08.7675061Z'}
    $rootMember=[pscustomobject]@{PID=100;Image=$root.Image;CreatedUtc=$root.CreatedUtc;ParentPID=99;InOriginalJob=$true;Error=$null;ParentError=$null}
    $compiler=[pscustomobject]@{PID=101;Image=$policy.Compiler;CreatedUtc='2026-10-12T11:28:08.8879302Z';ParentPID=100;InOriginalJob=$true;Error=$null;ParentError=$null}
    $console=[pscustomobject]@{PID=102;Image=$consolePolicy.Image;CreatedUtc='2026-10-12T11:28:08.7911626Z';ParentPID=100;InOriginalJob=$true;Error=$null;ParentError=$null}
    $telemetry=[pscustomobject]@{PID=103;Image=$policy.Telemetry;CreatedUtc='2026-10-12T11:28:09.4480203Z';ParentPID=101;InOriginalJob=$true;Error=$null;ParentError=$null}
    [pscustomobject]@{Policy=$policy;ConsolePolicy=$consolePolicy;Root=$root;Console=$console;Telemetry=$telemetry;
        Witness=@{CompilerIdentity=$compiler;Completed=$false};ConsoleWitness=@{Identity=$null;Completed=$false};
        Receipt=[pscustomobject]@{schema='iw7.material-v2-phase-result/1';phase='compile';pid=101;exit_code=0;failure=$null;executable_sha256=$policy.CompilerSHA256};
        Observation=[pscustomobject]@{AssignedCount=3;ListedCount=3;CapturedUtc='2026-10-12T11:28:09.9150780Z';Members=@($rootMember,$console,$telemetry)}}
}
function WitnessConsole($f){Update-WorldObserverConsoleWitness $f.ConsoleWitness $f.Observation $f.Root $f.ConsolePolicy}
function Advance($f){Assert-WorldObserverAdvance $f.Observation $f.Root $f.Witness $f.Receipt $f.Policy $f.ConsoleWitness $f.ConsolePolicy}
function Set-Members($f,$Members){$f.Observation.Members=@($Members);$f.Observation.AssignedCount=@($Members).Count;$f.Observation.ListedCount=@($Members).Count}

# Sanitized replay of the measured three-member topology, including timestamps.
$f=New-ConsoleCase;Refuse {Advance $f};WitnessConsole $f;Advance $f
Check ($f.ConsoleWitness.Identity.PID -eq 102) 'Observed console was not bound'
WitnessConsole $f;Advance $f
foreach($names in @(@('root'),@('root','console'),@('root','telemetry'))){
    $f=New-ConsoleCase;WitnessConsole $f
    Set-Members $f @($f.Observation.Members|Where-Object {($_.PID -eq 100 -and 'root' -in $names) -or ($_.PID -eq 102 -and 'console' -in $names) -or ($_.PID -eq 103 -and 'telemetry' -in $names)})
    Advance $f;Check $true 'Optional member combination'
}
foreach($pair in @(@('ParentPID',999),@('InOriginalJob',$false),@('InOriginalJob',$null),@('Error','unreadable'),@('ParentError','unknown'),
    @('CreatedUtc','2026-10-12T11:28:08.7000000Z'),@('CreatedUtc','2026-10-12T11:28:10.0000000Z'),@('PID',100))){
    $f=New-ConsoleCase;$f.Console.($pair[0])=$pair[1];Refuse {WitnessConsole $f;Advance $f}
}
foreach($path in 'C:\untrusted\conhost.exe','C:\Windows\SysWOW64\conhost.exe','C:\Windows\System32\other.exe'){
    $f=New-ConsoleCase;$f.Console.Image=$path;Refuse {WitnessConsole $f;Advance $f}
}
foreach($pair in @(@('PID',104),@('CreatedUtc','2026-10-12T11:28:08.7921626Z'))){
    $f=New-ConsoleCase;WitnessConsole $f;$f.Console.($pair[0])=$pair[1]
    Refuse {WitnessConsole $f};Refuse {Advance $f}
}
$f=New-ConsoleCase;WitnessConsole $f
Set-Members $f @($f.Observation.Members[0]);WitnessConsole $f
$f.Console.PID=104;Set-Members $f @($f.Observation.Members[0],$f.Console);Refuse {WitnessConsole $f}
foreach($duplicate in 'console','telemetry'){
    $f=New-ConsoleCase;WitnessConsole $f
    $member=if($duplicate -ceq 'console'){$f.Console}else{$f.Telemetry}
    Set-Members $f @($f.Observation.Members[0],$member,$member);Refuse {Advance $f}
    $clone=$member.PSObject.Copy();$clone.PID=104
    Set-Members $f @($f.Observation.Members[0],$member,$clone);Refuse {Advance $f}
    if($duplicate -ceq 'console'){Refuse {WitnessConsole $f}}
}
$f=New-ConsoleCase;WitnessConsole $f;$f.Observation.ListedCount=2;Refuse {Advance $f}
$f=New-ConsoleCase;WitnessConsole $f;$f.Observation.AssignedCount=4;Refuse {Advance $f}

# Signature validation consumes the Run-only Authenticode result; Plan never calls it.
$policy=Get-WorldObserverConsolePolicy
function New-Signature {[pscustomobject]@{Path=$policy.Image;Status='Valid';SignerCertificate=[pscustomobject]@{Subject=$policy.SignerSubject;Thumbprint=$policy.SignerThumbprint}}}
$sig=New-Signature;Assert-WorldObserverConsoleSignature $sig $policy;Check $true 'Reviewed signature'
foreach($pair in @(@('Path','C:\untrusted\conhost.exe'),@('Status','UnknownError'),@('Status','NotSigned'),@('SignerCertificate',$null))){
    $sig=New-Signature;$sig.($pair[0])=$pair[1];Refuse {Assert-WorldObserverConsoleSignature $sig $policy}
}
foreach($pair in @(@('Subject','CN=Microsoft impostor'),@('Thumbprint',('0'*40)))){
    $sig=New-Signature;$sig.SignerCertificate.($pair[0])=$pair[1];Refuse {Assert-WorldObserverConsoleSignature $sig $policy}
}

# Reuse the REAL stop/wait helpers with fake handles and clocks; no native load.
$script:tick=0L;$script:stopCalls=0;$script:stuck=$false;$script:badHash=$false;$script:hashes=@()
function Get-MaterialV2MonotonicMs {$script:tick}
function Get-MaterialV2UtcNow {[datetime]::new(2026,10,12,12,0,0,[DateTimeKind]::Utc).AddMilliseconds($script:tick)}
function Start-Sleep {param($Milliseconds) $script:tick+=$Milliseconds}
function Assert-BeaconHash([string]$Path,[string]$Expected){$script:hashes+=,$Path;if($script:badHash){throw 'Mock changed image'}}
function New-ResidualCase($Roles){
    $f=New-ConsoleCase;WitnessConsole $f
    Set-Members $f @($f.Observation.Members|Where-Object {($_.PID -eq 102 -and 'console' -in $Roles) -or ($_.PID -eq 103 -and 'telemetry' -in $Roles)})
    $owner=[pscustomobject]@{Exited=$true;Active=$f.Observation.Members.Count;ExitCode=0}
    $owner|Add-Member ScriptMethod Stop {$script:stopCalls++;if(!$script:stuck){$this.Active=0}}
    [pscustomobject]@{Fixture=$f;Owner=$owner;Snapshot=[pscustomobject]@{RootExited=$true;RootExitCode=0;ActiveProcesses=$owner.Active}}
}
function Complete($c){$f=$c.Fixture;Complete-WorldObserverResiduals $c.Owner $c.Snapshot $f.Observation $f.Receipt $f.Witness $f.Policy $f.Root $f.ConsoleWitness $f.ConsolePolicy}
foreach($roles in @(@('console'),@('telemetry'),@('console','telemetry'))){
    $c=New-ResidualCase $roles;$before=$script:stopCalls;$script:hashes=@()
    Check (Complete $c) 'Recognized residual did not close'
    Check ($script:stopCalls -eq $before+1 -and $c.Owner.Active -eq 0) 'Wrong owned stop/active count'
    Check ($c.Fixture.ConsoleWitness.Completed -or $c.Fixture.Witness.Completed) 'Closure not recorded'
    if('console' -in $roles){Check ($c.Fixture.ConsolePolicy.Image -in $script:hashes) 'Console image was not rehashed'}
    Check (!(Complete $c)) 'Repeated residual stop'
    $identity=[ordered]@{};Wait-MaterialV2OwnedPhase $c.Owner $identity $script:tick 240 {}
    Assert-WorldObserverClosed $identity;Check $true 'Fresh original root0/Active0 after cleanup'
}
foreach($case in 'root-failed','unwitnessed-console','console-replaced','foreign-parent','unknown','duplicate','count','root-still-listed','receipt-failed','hash-changed'){
    $c=New-ResidualCase @('console','telemetry');$f=$c.Fixture;$before=$script:stopCalls
    switch($case){
        'root-failed'{$c.Snapshot.RootExitCode=2}
        'unwitnessed-console'{$f.ConsoleWitness.Identity=$null}
        'console-replaced'{$f.Console.CreatedUtc='2026-10-12T11:28:08.7921626Z'}
        'foreign-parent'{$f.Console.ParentPID=999}
        'unknown'{$f.Console.Image='C:\untrusted\conhost.exe'}
        'duplicate'{Set-Members $f @($f.Console,$f.Console)}
        'count'{$c.Snapshot.ActiveProcesses=3}
        'root-still-listed'{$f.Console.PID=$f.Root.PID}
        'receipt-failed'{$f.Receipt.exit_code=1}
        'hash-changed'{$script:badHash=$true}
    }
    try {Refuse {Complete $c};Check ($script:stopCalls -eq $before) 'Unqualified residual triggered policy stop'}finally{$script:badHash=$false}
}
$c=New-ResidualCase @('console');$script:stuck=$true
try{Refuse {Complete $c};Check (!$c.Fixture.ConsoleWitness.Completed -and !$c.Fixture.ConsoleWitness.Cleanup.Closed) 'Unconfirmed closure accepted'}finally{$script:stuck=$false}
$c=New-ResidualCase @('console');$c.Snapshot.RootExited=$false;$before=$script:stopCalls
Check (!(Complete $c) -and $script:stopCalls -eq $before) 'Live root was stopped'
$c=New-ResidualCase @('console');$c.Snapshot.ActiveProcesses=0
Check (!(Complete $c)) 'Empty original job was stopped'
"PASS: $script:checks pure/mocked console-policy checks; no lease, Add-Type, compiler or fixture."

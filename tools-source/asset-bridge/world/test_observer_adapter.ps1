$ErrorActionPreference='Stop'
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
. "$repo/ops/Base-Client.Core.ps1"
. "$repo/sdk/modding/BeaconFF.Core.ps1"
. "$repo/tools-source/asset-bridge/surfaces/MaterialV2.Core.ps1"
. "$repo/tools-source/asset-bridge/surfaces/MaterialV2.Compiler.ps1"
. "$PSScriptRoot/ObserverHarness.Core.ps1"
$script:checks=0
function Check($Value,[string]$Message){if(!$Value){throw $Message};$script:checks++}
function Refuse([scriptblock]$Body){$caught=$false;try{& $Body|Out-Null}catch{$caught=$true};Check $caught 'Invalid world fixture accepted'}
foreach($name in 'Run-ObserverHarness.ps1','ObserverHarness.Core.ps1','test_observer_adapter.ps1'){
    $tokens=$null;$errors=$null
    $null=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $name),[ref]$tokens,[ref]$errors)
    Check (!$errors.Count) "$name parse"
}
$b=Get-WorldObserverBudgets
Check ($b.PhysicalBytes -eq 4GB -and $b.CommitBytes -eq 6GB -and $b.GroupMs -eq 120000 -and
    $b.CompileMs -eq 90000 -and $b.FixtureMs -eq 10000 -and $b.SupervisorSeconds -eq 240) 'Fixed world budgets'
Assert-WorldObserverOutput 63MB;Assert-WorldObserverOutput 64MB -Final
Refuse {Assert-WorldObserverOutput (63MB+1)};Refuse {Assert-WorldObserverOutput (64MB+1) -Final}
Refuse {Assert-WorldObserverOutput -1}
Assert-WorldObserverTime 89999 'compile' 89999
Assert-WorldObserverTime 119999 'fixture' 9999
foreach($case in @(@(90000,'compile',90000),@(10000,'fixture',10000),@(120000,'fixture',0),@(-1,'compile',0),@(0,'other',0))){
    Refuse {Assert-WorldObserverTime $case[0] $case[1] $case[2]}
}
$state=@{FixtureStartedMs=$null};Assert-WorldObserverPollTime $state 1000 90999
Refuse {Assert-WorldObserverPollTime $state 1000 91000}
$state.FixtureStartedMs=90000;Assert-WorldObserverPollTime $state 1000 99999
Refuse {Assert-WorldObserverPollTime $state 1000 100000}
Refuse {Assert-WorldObserverPollTime @{FixtureStartedMs=$null} 100000 120000 0}
foreach($path in 'C:\safe\one:stream','\\server\share\file','C:\safe\..\file','C:\safe\bad.','C:\safe\bad ',
    'C:\safe\NUL.txt','C:\safe\COM1','C:\safe\LPT².txt'){Refuse {Resolve-WorldObserverPath $path}}
$source=Join-Path $PSScriptRoot 'ObserverHarness.Core.ps1'
$pins=@([pscustomobject]@{Path=$source;SHA256=(Get-FileHash -LiteralPath $source).Hash})
Assert-WorldObserverPins $pins
$pins[0].SHA256='0'*64;Refuse {Assert-WorldObserverPins $pins}
function New-WorldFixture {
    $policy=Get-MaterialV2CompilerPolicy 'C:\reviewed\cl.exe'
    $root=[pscustomobject]@{PID=36;Image='C:\reviewed\python.exe';CreatedUtc='2026-10-12T10:00:00.0000000Z'}
    $rootMember=[pscustomobject]@{PID=36;ParentPID=35;Image=$root.Image;CreatedUtc=$root.CreatedUtc;InOriginalJob=$true;Error=$null;ParentError=$null}
    $compiler=[pscustomobject]@{PID=37;ParentPID=36;Image=$policy.Compiler;CreatedUtc='2026-10-12T10:00:00.1000000Z';InOriginalJob=$true;Error=$null;ParentError=$null}
    $telemetry=[pscustomobject]@{PID=38;ParentPID=37;Image=$policy.Telemetry;CreatedUtc='2026-10-12T10:00:00.2000000Z';InOriginalJob=$true;Error=$null;ParentError=$null}
    [pscustomobject]@{Policy=$policy;Root=$root;Witness=@{CompilerIdentity=$compiler};Telemetry=$telemetry;
        Receipt=[pscustomobject]@{schema='iw7.material-v2-phase-result/1';phase='compile';pid=37;exit_code=0;failure=$null;executable_sha256=$policy.CompilerSHA256};
        Observation=[pscustomobject]@{AssignedCount=2;ListedCount=2;CapturedUtc='2026-10-12T10:00:01.0000000Z';Members=@($rootMember,$telemetry)}}
}
function Advance($f){Assert-WorldObserverAdvance $f.Observation $f.Root $f.Witness $f.Receipt $f.Policy}
$f=New-WorldFixture;Advance $f
$f.Observation.Members=@($f.Observation.Members[0]);$f.Observation.AssignedCount=1;$f.Observation.ListedCount=1;Advance $f
foreach($pair in @(@('Image','C:\other\vctip.exe'),@('ParentPID',99),@('InOriginalJob',$false),@('Error','unreadable'),
    @('CreatedUtc','2026-10-12T09:00:00.0000000Z'),@('CreatedUtc','2026-10-12T11:00:00.0000000Z'))){
    $f=New-WorldFixture;$f.Telemetry.($pair[0])=$pair[1];Refuse {Advance $f}
}
foreach($pair in @(@('exit_code',1),@('exit_code','0'),@('pid',99),@('failure','deadline'),@('executable_sha256',('f'*64)))){
    $f=New-WorldFixture;$f.Receipt.($pair[0])=$pair[1];Refuse {Advance $f}
}
$f=New-WorldFixture;$f.Witness.CompilerIdentity=$null;Refuse {Advance $f}
$f=New-WorldFixture;$f.Observation.AssignedCount=3;Refuse {Advance $f}
$f=New-WorldFixture;$f.Root.CreatedUtc='2026-10-12T10:00:00.0000001Z';Refuse {Advance $f}
$closed=@{JobRootExitedAtClose=$true;JobActiveAtClose=0;ExitCode=0};Assert-WorldObserverClosed $closed
foreach($pair in @(@('JobRootExitedAtClose',$false),@('JobActiveAtClose',1),@('JobActiveAtClose','0'),@('ExitCode',1),@('ExitCode',$null))){
    $bad=$closed.Clone();$bad[$pair[0]]=$pair[1];Refuse {Assert-WorldObserverClosed $bad}
}
# Execute the reused supervisor with fake original handles and time, never native APIs.
$script:tick=0L;$mockOwner=[pscustomobject]@{Exited=$false;Active=1;ExitCode=0}
function Get-MaterialV2MonotonicMs {$script:tick}
function Get-MaterialV2UtcNow {[datetime]::new(2026,10,12,10,0,0,[DateTimeKind]::Utc).AddMilliseconds($script:tick)}
function Start-Sleep {param($Milliseconds) $script:tick+=$Milliseconds}
$identity=[ordered]@{};$state=@{FixtureStartedMs=$null}
Refuse {Wait-MaterialV2OwnedPhase $mockOwner $identity 0 240 {Assert-WorldObserverPollTime $state 0 (Get-MaterialV2MonotonicMs)}}
Check ($script:tick -eq 90000 -and $identity.Supervision.Failure -like '*compile deadline*') 'World callback failed to tighten reused245s envelope'
$script:tick=90000;$identity=[ordered]@{};$state.FixtureStartedMs=90000
Refuse {Wait-MaterialV2OwnedPhase $mockOwner $identity 0 240 {Assert-WorldObserverPollTime $state 0 (Get-MaterialV2MonotonicMs)}}
Check ($script:tick -eq 100000 -and $identity.Supervision.Failure -like '*fixture deadline*') 'Persistent state lost fixture deadline'
$script:tick=119900;$state.FixtureStartedMs=119900;$identity=[ordered]@{}
Refuse {Wait-MaterialV2OwnedPhase $mockOwner $identity 0 240 {Assert-WorldObserverPollTime $state 0 (Get-MaterialV2MonotonicMs)}}
Check ($script:tick -eq 120000 -and $identity.Supervision.Failure -like '*group deadline*') 'Global120s envelope escaped'
$script:tick=0;$mockOwner.Exited=$true;$mockOwner.Active=0;$identity=[ordered]@{};$state.FixtureStartedMs=0
Refuse {Wait-MaterialV2OwnedPhase $mockOwner $identity 0 240 {$script:tick=10000;Assert-WorldObserverPollTime $state 0 (Get-MaterialV2MonotonicMs)}}
Check ($identity.Supervision.Failure -like '*fixture deadline*') 'Late callback accepted zero-active success'
# Same shared closure code, exact mock owner, failed closure cannot release.
$mockOwner.Active=1;$script:stops=0
$mockOwner|Add-Member ScriptMethod Stop {$script:stops++;$this.Active=0}
$cleanup=[ordered]@{};Check (Stop-MaterialV2OwnedPhase $mockOwner $cleanup) 'Owned stop did not confirm closure'
Check ($script:stops -eq 1 -and $cleanup.Closed) 'Wrong stop count/closure'
$mockOwner|Add-Member ScriptMethod Stop {$script:stops++} -Force;$mockOwner.Active=1;$script:tick=0;$cleanup=[ordered]@{}
Check (!(Stop-MaterialV2OwnedPhase $mockOwner $cleanup) -and !$cleanup.Closed -and $script:tick -eq 15000) 'Stuck closure accepted'
# Original text-only output verifies accounting includes the final receipt.
$testRoot=Join-Path $PSScriptRoot ('.observer-receipt-test-'+[guid]::NewGuid().ToString('N'))
try {
    [IO.Directory]::CreateDirectory($testRoot)|Out-Null
    [IO.File]::WriteAllText((Join-Path $testRoot 'original.txt'),'original fixture')
    $receipt=[ordered]@{Schema='original-world-receipt-test';FinalBytes=$null}
    Write-WorldObserverFinalReceipt $testRoot $receipt
    $saved=Get-Content -LiteralPath (Join-Path $testRoot 'run.json') -Raw|ConvertFrom-Json
    Check ($saved.FinalBytes -eq (Measure-WorldObserverOutput $testRoot -Final)) 'Final receipt excluded its own bytes'
    Refuse {Write-WorldObserverFinalReceipt $testRoot $receipt}
} finally {
    $resolved=[IO.Path]::GetFullPath($testRoot)
    $expected=[IO.Path]::GetFullPath($PSScriptRoot)+[IO.Path]::DirectorySeparatorChar+'.observer-receipt-test-'
    if(!$resolved.StartsWith($expected,[StringComparison]::OrdinalIgnoreCase)){throw 'Unexpected fixture cleanup target.'}
    if(Test-Path -LiteralPath $resolved){Remove-Item -LiteralPath $resolved -Recurse -Force}
}
"PASS: $checks pure/mocked world adapter checks; no lease, Add-Type, compiler or fixture."

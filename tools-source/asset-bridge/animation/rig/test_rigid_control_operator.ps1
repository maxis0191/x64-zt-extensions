param([Parameter(Mandatory)][string]$SourcePackage,[string]$PlanPath)
# Pure source and deterministic owner mocks. No Add-Type, compiler, real lease,
# native writer, stock or game is run. The base transaction uses tiny temp files.
$ErrorActionPreference='Stop'
. "$PSScriptRoot/RigidControlWriter.Core.ps1"
. "$PSScriptRoot/Rig.Core.ps1"
. "$PSScriptRoot/Rig.Compiler.ps1"
. (Join-Path $SourcePackage 'ops/Base-Client.Core.ps1')
$count=0
function Check([bool]$Ok,[string]$Why){if(!$Ok){throw $Why};$script:count++}
function Refuse([scriptblock]$Body){$caught=$false;try{& $Body|Out-Null}catch{$caught=$true};Check $caught 'Unsafe source fixture accepted'}
foreach($name in 'Build-RigidControlWriter.ps1','RigidControlWriter.Core.ps1'){
    $e=$null;$t=$null;$null=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $name),[ref]$t,[ref]$e)
    Check (!$e.Count) ($name+' parse')
}
$driver=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'Build-RigidControlWriter.ps1'))
Check ($driver.IndexOf('if(!$Run)') -lt $driver.IndexOf('Enter-IW7ResourceLease')) 'Default returns before admission'
foreach($imageGate in 'Assert-BeaconHash $plan.compiler','Assert-BeaconHash $policy.Telemetry','Assert-BeaconHash $plan.python'){
    Check ($driver.IndexOf($imageGate) -gt $driver.IndexOf('Enter-IW7ResourceLease')) 'Native executable hashes only under actual lease'
}
Check ($driver.Contains('NativeExecutableHashesRead=$false')) 'Default must state executable hashes are unqualified'
Check ($driver.IndexOf('GetCommandLineArgs()') -lt $driver.IndexOf('Enter-IW7ResourceLease')) 'Persistent host must be proved before admission'
Check ($driver.IndexOf("SetData('IW7.RigidControl.HostContext',`$context)") -lt $driver.IndexOf('Enter-IW7ResourceLease')) 'Context must own everything before admission'
Check ($driver -notmatch 'Stop-Process|taskkill|SetEnvironmentVariable|Set-Item.+Env:') 'No PID or global environment mutation'
Check ($driver -notmatch 'CommitLimit\*|PhysicalAvailable -[lg]t|Minimum.*GB') 'No numeric memory admission minimum'
Check ($driver.IndexOf('Save-IW7BaseTransaction') -lt $driver.IndexOf('Invoke-RCWPhase')) 'Backup must precede compiler creation'
if($PlanPath){$plan=[IO.File]::ReadAllText($PlanPath)|ConvertFrom-Json}else{
    $plan=[pscustomobject]@{
        schema='iw7.original-rig-rigid-writer-operator-plan/1';source_package=[IO.Path]::GetFullPath($SourcePackage);source_package_manifest_sha256=('a'*64)
        prepared_source=(Join-Path ([IO.Path]::GetTempPath()) 'rcw-source-unused');prepared_manifest_sha256='5811ef3ebcd5948eb394ab4a720ec37de4f9a902788774da10d47b8d59a55b5b'
        native_source='C:\rcw-source-unused\native';native_source_pin='fab935826c898806855376662a8a03317b3ad8f1';run_root='C:\IW7-Work\rcw-20990101-test'
        python='C:\rcw-source-unused\python.exe';python_sha256='4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a'
        compiler='C:\rcw-source-unused\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64\cl.exe';compiler_sha256='fe251ef50a1545b1b0835ee17b1e785459712b38d79e45b5c1d3d28970a36619'
        sdk_root='C:\rcw-source-unused\SDK';sdk_version='10.0.26100.0';core_sha256=('a'*64);operator_sha256=('a'*64)
        root_go=$false;compiled=$false;native_writer_executed=$false;ff_built=$false;ready=$false
    }
}
Assert-RCWPlan $plan;Check $true 'Actual closed source plan'
foreach($pair in @(@('ready',$true),@('root_go',$true),@('ff_built','false'),@('python_sha256',('a'*64)),@('run_root','C:\IW7-Work\old-rig'))){
    $bad=$plan.PSObject.Copy();$bad.($pair[0])=$pair[1];Refuse {Assert-RCWPlan $bad}
}
$bad=$plan.PSObject.Copy();$bad|Add-Member NoteProperty command @('arbitrary.exe');Refuse {Assert-RCWPlan $bad}
$commands=Get-RCWCommands $plan
Check ($commands.Phases.Count -eq 2) 'Exactly two compile phases'
Check ($commands.Phases[0].Spec.cwd -cne $commands.Phases[1].Spec.cwd -and $commands.Phases[0].Spec.logs -cne $commands.Phases[1].Spec.logs) 'Separate outputs and logs'
foreach($phase in $commands.Phases){
    Check ($phase.Spec.phase -ceq 'compile' -and $phase.Spec.timeout -eq 120) 'Known compile phase contract'
    Check ($phase.Spec.arguments -ccontains ('/I'+(Join-Path $plan.run_root ('source/'+$phase.Profile)))) 'Header belongs to exact profile'
    Check ($phase.Spec.arguments -ccontains ('/Fe'+(Join-Path $phase.Spec.cwd 'rigid-writer.exe'))) 'Only owned executable output'
}

$events=[Collections.Generic.List[string]]::new();$tick=0;$factoryFail=$false;$polls=0;$receiptFailure=$false
function Get-RigMonotonicMs {$script:tick}
function Start-Sleep {param($Milliseconds) $script:tick+=$Milliseconds}
function ConvertTo-AnimationArguments($Arguments){$Arguments -join '|'}
function New-RigOwnedJob($Python,$Arguments,$Work){$events.Add('prepare');if($script:factoryFail){throw 'Unknown factory failure'};return $script:owner}
function Get-BeaconJobIdentity($Owner,$Python,$Phase){Check ([object]::ReferenceEquals($Owner,$script:owner)) 'Identity from original object';$events.Add('identity');[ordered]@{PID=11;Phase=$Phase;ExitCode=$null;JobActiveAtClose=$null}}
function Get-RigOriginalJobMembers($Owner){
    $members=if($Owner.Active){@([pscustomobject]@{PID=12;ParentPID=11;Image=$plan.compiler;CreatedUtc='2026-10-14T06:00:00.0000000Z';InOriginalJob=$true;Error=$null;ParentError=$null})}else{@()}
    [pscustomobject]@{Members=$members;AssignedCount=$members.Count;ListedCount=$members.Count;CapturedUtc='2026-10-14T06:00:01.0000000Z'}
}
function Register-AnimationPhase($Owner,$Token,$BudgetCheck){$events.Add('register');& $BudgetCheck;[pscustomobject]@{Registered=$true}}
function Read-RigPhaseResult($Logs,$Spec,$Hash,$Identity,$Phase,$RootExitCode){[pscustomobject]@{schema='iw7.rig-chain-phase-result/1';phase='compile';failure=$null;exit_code=$(if($script:receiptFailure){1}else{0});pid=12;executable_sha256=$plan.compiler_sha256;spec_sha256=$Hash;log_limit_each=2MB;ownership='outer original Windows job'}}
function Get-FileHash {param($LiteralPath) [pscustomobject]@{Hash=('c'*64)}}
$owner=[pscustomobject]@{Exited=$false;Active=1;ExitCode=0;Resumes=0;Disposals=0}
$owner|Add-Member ScriptMethod Resume {$this.Resumes++;$events.Add('resume')}
$owner|Add-Member ScriptMethod Dispose {$this.Disposals++;$events.Add('dispose')}
$context=[ordered]@{Plan=$plan;Owner=$null;Closed=$true;Lease=[pscustomobject]@{Token='fake'};Policy=(Get-RigCompilerPolicy $plan.compiler);State=[ordered]@{Phases=@()};Save={$events.Add('save')}}
Invoke-RCWPhase $context $commands.Phases[0] 'C:\test\spec.json' ('b'*64) {
    $script:polls++;if($script:polls -ge 2){$owner.Exited=$true;$owner.Active=0}
}
Check (($events -join ',') -ceq 'prepare,identity,save,resume,register,save,dispose') 'Original identity persisted before resume/registration/disposal'
Check ($context.Closed -and $null -eq $context.Owner -and $context.State.Phases[0].JobActiveAtClose -eq 0) 'Actual closed snapshot and receipt required'
Check ($context.State.Phases[0].Supervision.PollCount -eq 2) 'Fresh closure sample after callback'
$owner.Exited=$false;$owner.Active=1;$owner.Disposals=0;$polls=0;$receiptFailure=$true
Refuse {Invoke-RCWPhase $context $commands.Phases[1] 'C:\test\bad-receipt.json' ('b'*64) {$script:polls++;if($script:polls -ge 2){$owner.Exited=$true;$owner.Active=0}}}
Check ($context.Closed -and [object]::ReferenceEquals($context.Owner,$owner) -and $owner.Disposals -eq 0) 'Invalid receipt keeps original owner available for cleanup'
$context.Owner=$null;$receiptFailure=$false
$factoryFail=$true;$context.Closed=$true
Refuse {Invoke-RCWPhase $context $commands.Phases[1] 'C:\test\spec2.json' ('b'*64) {}}
Check (!$context.Closed -and $null -eq $context.Owner) 'Unknown factory must retain unclosed context'

# Use the actual transaction against owned synthetic compiler outputs.
Remove-Item function:Get-FileHash
$fixture=Join-Path ([IO.Path]::GetTempPath()) ('rcw-source-test-'+[guid]::NewGuid().ToString('N'))
$build=Join-Path $fixture 'build';[IO.Directory]::CreateDirectory($build)|Out-Null
$transaction=Save-IW7BaseTransaction ([pscustomobject]@{GameRoot=$build;MutableFiles=@('first/rigid-writer.exe','second/rigid-writer.exe');ProfileDirectory='unused';ProfileDirectories=@('first','second','tmp')}) (Join-Path $fixture 'backup')
foreach($profile in 'first','second'){$dir=Join-Path $build $profile;[IO.Directory]::CreateDirectory($dir)|Out-Null;[IO.File]::WriteAllText((Join-Path $dir 'rigid-writer.exe'),'synthetic transaction file; never executed')}
$fakeLeases=@([pscustomobject]@{Token='fake'});$releaseFail=$false;$releaseCount=0
function Exit-IW7ResourceLease($Token){$script:releaseCount++;if($script:releaseFail){throw 'Release refused'};$script:fakeLeases=@()}
function Invoke-IW7ResourceLock($Body){& $Body}
function Read-IW7ResourceState {[pscustomobject]@{Leases=$script:fakeLeases}}
$guard=[pscustomobject]@{Disposals=0};$guard|Add-Member ScriptMethod Dispose {$this.Disposals++}
$guards=[Collections.Generic.List[object]]::new();$guards.Add($guard)
$context=[ordered]@{Plan=[pscustomobject]@{run_root=$fixture};Owner=$null;Closed=$false;SourceIntact=$true;Saved=$true;Created=$true;Transaction=$transaction;Guards=$guards;Lease=[pscustomobject]@{Token='fake'};State=[ordered]@{Restored=$false;LeaseReleased=$false;RetainedLeaseToken='fake'}}
Check (!(Complete-RCWContext $context)) 'No restore/release for unknown closure'
Check ($releaseCount -eq 0 -and $guard.Disposals -eq 0 -and !$transaction.Restored) 'All handles retained while closure unknown'
$context.Closed=$true;$context.SourceIntact=$false
Check (!(Complete-RCWContext $context)) 'Source change retains context'
$context.SourceIntact=$true;$releaseFail=$true
# The real restore preflight must refuse a target changed into a directory.
$blocked=Join-Path $build 'first/rigid-writer.exe'
Remove-Item -LiteralPath $blocked
New-Item -ItemType Directory -Path $blocked|Out-Null
Refuse {Complete-RCWContext $context}
Check ($releaseCount -eq 0 -and $guard.Disposals -eq 0 -and !$transaction.Restored) 'Restoration failure retains lease and every guard'
Remove-Item -LiteralPath $blocked
[IO.File]::WriteAllText($blocked,'synthetic transaction file; never executed')
Refuse {Complete-RCWContext $context}
Check ($transaction.Restored -and $null -ne $context.Lease -and $guard.Disposals -eq 0) 'Release failure retains lease and guards after restore'
$releaseFail=$false
Check (Complete-RCWContext $context) 'Closed restored group releases safely'
Check ($context.State.LeaseReleased -and $null -eq $context.Lease -and $guards.Count -eq 0 -and $guard.Disposals -eq 1) 'Release confirmation precedes guard disposal'
Check (@(Get-ChildItem -LiteralPath $build -Force).Count -eq 0) 'Actual restoration removes only synthetic build outputs'
# Keep the tiny backup/receipt fixture as test evidence; do not delete recursively.
[ordered]@{Checks=$count;Fixture=$fixture;NativeTypesLoaded=$false;RealLeaseAcquired=$false;CompilerExecuted=$false;NativeWriterExecuted=$false;Ready=$false}|ConvertTo-Json

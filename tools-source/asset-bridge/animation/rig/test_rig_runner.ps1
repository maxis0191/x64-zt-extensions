# Pure source/managed parsing and deterministic mocks. No BuildJob, Add-Type,
# compiler, CIM, lease, stock staging or restoration provider is invoked.
$ErrorActionPreference='Stop'
. "$PSScriptRoot/Rig.Core.ps1"
. "$PSScriptRoot/Rig.Compiler.ps1"
$checks=0
function Check([bool]$Value,[string]$Message){if(!$Value){throw $Message};$script:checks++}
function Refuse([scriptblock]$Body){$caught=$false;try{& $Body|Out-Null}catch{$caught=$true};Check $caught 'Unsafe fixture accepted'}
foreach($file in Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*.ps1'){
    $errors=$null;$tokens=$null
    $ast=[Management.Automation.Language.Parser]::ParseFile($file.FullName,[ref]$tokens,[ref]$errors)
    Check (!$errors.Count) ($file.Name+' parse')
}
$runner=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'Build-RigChain.ps1'))
$errors=$null;$tokens=$null
$ast=[Management.Automation.Language.Parser]::ParseInput($runner,[ref]$tokens,[ref]$errors)
$planGate=@($ast.EndBlock.Statements|Where-Object {$_ -is [Management.Automation.Language.IfStatementAst] -and $_.Clauses[0].Item1.Extent.Text -ceq '!$Run'})
Check ($planGate.Count -eq 1 -and $planGate[0].Extent.Text.Contains('return')) 'Explicit early-return Plan gate required'
$before=$runner.Substring(0,$planGate[0].Extent.StartOffset)
Check ($before -notmatch 'Add-Type|Enter-IW7ResourceLease|::Prepare|Copy-Item|New-Item') 'Plan cannot execute native/staging/admission calls'
Check ($runner.IndexOf('Exit-IW7ResourceLease -Token $lease.Token') -lt $runner.IndexOf("`$group='ff'")) 'Native release must precede FF group'
Check ($runner.IndexOf("`$script:closed=`$false") -lt $runner.IndexOf('New-RigOwnedJob $plan.python.path')) 'Factory must start in unknown closure state'
Check ($runner.IndexOf('Get-BeaconJobIdentity $owner') -lt $runner.IndexOf('$owner.Resume()')) 'Original identity must precede Resume'
Check ($runner.IndexOf('$owner.Resume()') -lt $runner.IndexOf('Register-AnimationPhase $owner')) 'CIM registration must follow Resume'
Check ($runner.Contains('Assert-RigReaderBindings $readback $plan -FF')) 'Actual retained output hash bindings required'
Check ($runner -notmatch 'Stop-Process|taskkill|SetEnvironmentVariable|Set-Item.+Env:') 'No global/PID termination or persistent environment mutation'

$valid=[pscustomobject]@{schema='iw7.rig-chain-phase-result/1';phase='read-native';failure=$null;
    exit_code=0;executable_sha256=('a'*64);spec_sha256=('b'*64);log_limit_each=2MB;ownership='outer original Windows job'}
$identity=[pscustomobject]@{ExitCode=0;JobActiveAtClose=0;JobRootExitedAtClose=$true}
Assert-RigPhaseResult $valid 'read-native' ('a'*64) ('b'*64) $identity
foreach($pair in @(@('schema','wrong'),@('phase','read-ff'),@('exit_code','0'),@('exit_code',1),@('exit_code',$null),
    @('failure','timeout'),@('log_limit_each',3MB),@('ownership','pid'),@('executable_sha256',('c'*64)),@('spec_sha256',('c'*64)))){
    $bad=$valid.PSObject.Copy();$bad.($pair[0])=$pair[1]
    Refuse {Assert-RigPhaseResult $bad 'read-native' ('a'*64) ('b'*64) $identity}
}
foreach($pair in @(@('ExitCode',1),@('ExitCode','0'),@('ExitCode',$null),@('JobActiveAtClose',1),
    @('JobActiveAtClose','0'),@('JobActiveAtClose',$null),@('JobRootExitedAtClose',$false),@('JobRootExitedAtClose','true'))){
    $bad=$identity.PSObject.Copy();$bad.($pair[0])=$pair[1]
    Refuse {Assert-RigPhaseResult $valid 'read-native' ('a'*64) ('b'*64) $bad}
}
# Exact root handle snapshots with a deterministic clock and no sleeping.
function Get-RigMonotonicMs {$script:tick}
function Start-Sleep {param($Milliseconds) $script:tick+=$Milliseconds}
$script:tick=0
$owner=[pscustomobject]@{Exited=$false;Active=1;ExitCode=0;Stops=0}
$owner|Add-Member ScriptMethod Stop {$this.Stops++;$this.Exited=$true;$this.Active=0}
$id=[ordered]@{}
Wait-RigOwnedPhase $owner $id 0 30 {param($sample) $owner.Exited=$true;$owner.Active=0}
Check ($id.Supervision.PollCount -eq 2 -and $id.JobActiveAtClose -eq 0) 'Callback cannot substitute for a fresh root0/Active0 sample'
$owner.Exited=$true;$owner.Active=1;$script:tick=0;$id=[ordered]@{}
Refuse {Wait-RigOwnedPhase $owner $id 0 30 {param($sample)}}
Check ($script:tick -eq 2000 -and $id.Supervision.Outcome -ceq 'Failed') 'Descendant drain must stop at two seconds'
$owner.Exited=$false;$owner.Active=1;$script:tick=0;$id=[ordered]@{}
Refuse {Wait-RigOwnedPhase $owner $id 0 30 {param($sample)}}
Check ($script:tick -eq 35000) 'Phase plus adapter deadline must remain bounded'
$script:tick=0;$stop=[ordered]@{}
Check (Stop-RigOwnedPhase $owner $stop) 'Exact owner stop should close mock job'
Check ($owner.Stops -eq 1 -and $stop.LastSnapshot.ActiveProcesses -eq 0) 'Original owner stop/closure evidence required'
$stuck=[pscustomobject]@{Exited=$true;Active=1;ExitCode=122}
$stuck|Add-Member ScriptMethod Stop {}
$script:tick=0;$stop=[ordered]@{}
Check (!(Stop-RigOwnedPhase $stuck $stop) -and $script:tick -eq 15000 -and !$stop.Closed) 'Stuck stop must retain unknown ownership'

$entry=[pscustomobject]@{Relative='main/fileSysCheck.cfg';Mode='Copy';Bytes=77;Attributes=33}
Set-RigSourceIdentity $entry 'volume:source'
Set-RigSourceIdentity $entry 'volume:source'
Refuse {Set-RigSourceIdentity $entry 'different:identity'}
Assert-RigCopyIdentity $entry 'volume:copy'
Refuse {Assert-RigCopyIdentity $entry 'volume:source'}
foreach($field in 'Relative','Mode','Bytes'){
    $bad=$entry.PSObject.Copy();$bad.$field='wrong';Refuse {Assert-RigCopyIdentity $bad 'volume:copy'}
}
Check ($entry.Attributes -eq 33) 'Copy gate cannot alter stock attributes'
$rows=@('material,,mopw/character_park_clown_zombie_shoes','xmodelsurfs,paris_doom_skin_two_bone_first_a_lod0',
    'xmodelsurfs,paris_doom_skin_two_bone_second_a_lod0','xmodel,paris_doom_skin_two_bone_first_a',
    'xmodel,paris_doom_skin_two_bone_second_a','xanim,paris_original_probe_bend','rawfile,sdk_original_rig_probe')
$log='Loading zone "sdk_original_rig_probe"'+"`n"+(@($rows|ForEach-Object {$parts=$_ -split ',',2;'Loading asset "'+$parts[1]+'" of type '+$parts[0]+'.'}) -join "`n")
Check (@(Get-RigInventory $log).Count -eq 7) 'Exact seven-row inventory'
foreach($bad in @(($log+"`n"+($log -split "`n")[-1]),($log+"`n[ ERROR ] missing"),$log.Replace('sdk_original_rig_probe','other'))){Refuse {Get-RigInventory $bad}}

# Cleanup order is tested separately from any resource/native implementation.
foreach($closed in $false,$true){foreach($intact in $false,$true){
    $script:actions=[Collections.Generic.List[string]]::new()
    $guard=[pscustomobject]@{};$guard|Add-Member ScriptMethod Dispose {$script:actions.Add('guards')}
    $state=[ordered]@{CleanupError=$null}
    $done=Complete-RigGroup $state $closed $intact $true @($guard) {$script:actions.Add('restore+release')} {$script:actions.Add('release')}
    if($closed -and $intact){Check ($done -and ($script:actions -join ',') -ceq 'guards,restore+release') 'Closed proof before guard disposal then restore/release'}
    else{Check (!$done -and !$script:actions.Count) 'Unconfirmed ownership/source must retain all guards, stock and lease'}
}}
$script:actions=[Collections.Generic.List[string]]::new()
$done=Complete-RigGroup ([ordered]@{}) $true $true $false @() {throw 'No saved transaction exists'} {$script:actions.Add('release')}
Check ($done -and ($script:actions -join ',') -ceq 'release') 'Failure before staging releases only after closed/source proof'
Refuse {Complete-RigGroup ([ordered]@{}) $true $true $true @() {throw 'Mock restoration refusal'} {throw 'Must not release after refusal'}}

$tempRoot=Join-Path ([IO.Path]::GetTempPath()) ('iw7-rig-source-tests-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($tempRoot)|Out-Null
try{
    function Resolve-IW7BasePath($Root,$Relative){[IO.Path]::GetFullPath((Join-Path $Root $Relative))}
    $file=Join-Path $tempRoot 'source.hpp';Write-RigNewText 'original' $file
    Refuse {Write-RigNewText 'overwrite' $file}
    Assert-RigArtifact $file 64KB
    Refuse {Assert-RigArtifact $file 1}
    $inventory=@(Get-RigToolchainInventory @($tempRoot))
    Check ($inventory.Count -eq 1 -and $inventory[0].Bytes -eq 8) 'Metadata inventory reads no content hashes'
    Assert-RigToolchainInventory $inventory @($tempRoot)
    Write-RigNewText 'injected header' (Join-Path $tempRoot 'new.hpp')
    Refuse {Assert-RigToolchainInventory $inventory @($tempRoot)}
    $state=[ordered]@{FinalObservedBytes=$null;MaxObservedBytes=0L}
    $statePath=Join-Path $tempRoot 'state.json'
    Save-RigFinalCounters $state {Write-RigJson $state $statePath} {(Get-Item -LiteralPath $statePath).Length}
    $read=[IO.File]::ReadAllText($statePath)|ConvertFrom-Json
    Check ($read.FinalObservedBytes -eq (Get-Item -LiteralPath $statePath).Length -and $read.MaxObservedBytes -eq $state.MaxObservedBytes) 'Final serialized receipt size must converge'
}finally{
    $resolved=[IO.Path]::GetFullPath($tempRoot)
    $base=[IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    if(!$resolved.StartsWith($base,[StringComparison]::OrdinalIgnoreCase) -or (Split-Path $resolved -Leaf) -notlike 'iw7-rig-source-tests-*'){throw 'Unexpected test cleanup root'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
# Managed C# syntax parsing only; do not emit or load a compiled helper.
foreach($name in 'Microsoft.CodeAnalysis.dll','Microsoft.CodeAnalysis.CSharp.dll'){
    $path=Join-Path $PSHOME $name
    if(!(Test-Path -LiteralPath $path)){throw 'Roslyn syntax reader unavailable; do not substitute Add-Type.'}
    $null=[Reflection.Assembly]::LoadFrom($path)
}
$tree=[Microsoft.CodeAnalysis.CSharp.CSharpSyntaxTree]::ParseText([IO.File]::ReadAllText((Join-Path $PSScriptRoot 'Rig.JobMembers.cs')))
$errors=@($tree.GetDiagnostics()|Where-Object Severity -EQ Error)
Check (!$errors.Count) 'Local job observer C# syntax failed'
Check (!('IW7.AnimationRig.JobMembers' -as [type]) -and !('IW7.CommunityBuild.BuildJob' -as [type]) -and !('IW7HudFileIdentity' -as [type])) 'Tests must never load native helper types'
"PASS: $checks rig runner source/mocked checks; no native helper, compiler, stock or lease execution."

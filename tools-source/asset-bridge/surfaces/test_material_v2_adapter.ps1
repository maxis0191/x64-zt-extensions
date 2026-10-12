$ErrorActionPreference='Stop'
foreach($name in @('Build-MaterialV2.ps1','MaterialV2.Core.ps1')){
    $tokens=$null;$errors=$null
    $null=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $name),[ref]$tokens,[ref]$errors)
    if($errors.Count){throw ($errors|Out-String)}
}
. "$PSScriptRoot/MaterialV2.Core.ps1"
$budgets=Get-MaterialV2Budgets
if($budgets.WriterPhysicalBytes -ne 4GB -or $budgets.WriterCommitBytes -ne 6GB -or
   $budgets.FFPhysicalBytes -ne 8GB -or $budgets.FFCommitBytes -ne 11GB){throw 'Native minimum or FF admission budget changed.'}
function Refuse([scriptblock]$Action){$caught=$false;try{& $Action|Out-Null}catch{$caught=$true};if(!$caught){throw 'Invalid fixture accepted.'}}
$quoted=ConvertTo-MaterialV2Arguments @('-B','C:\path with spaces\adapter.py')
if($quoted -cne '"-B" "C:\path with spaces\adapter.py"'){throw 'Argument quoting differs.'}
foreach($arg in @('a"b',"a`nb",'trailing\','')){Refuse {ConvertTo-MaterialV2Arguments @($arg)}}
$arguments=@(Get-MaterialV2CompilerArguments 'C:\VC' 'C:\SDK' '10.0.26100.0' 'C:\ZT' 'C:\prepared' 'C:\writer')
if('/IC:\ZT\src\zonetool' -cnotin $arguments -or '/FeC:\writer\material-v2-writer.exe' -cnotin $arguments -or
   'C:\prepared\writer-source\writer.cpp' -cnotin $arguments -or '/MP' -in $arguments){throw 'Fixed compiler/output/include contract differs.'}
Refuse {Get-MaterialV2CompilerArguments 'C:\VC' 'C:\SDK' '../10' 'C:\ZT' 'C:\prepared' 'C:\writer'}
$valid=[pscustomobject]@{schema='iw7.material-v2-phase-result/1';phase='read';executable_sha256=('a'*64);failure=$null;exit_code=0}
$identity=[pscustomobject]@{ExitCode=0;JobActiveAtClose=0}
Assert-MaterialV2PhaseResult $valid 'read' ('a'*64) $identity
foreach($pair in @(@('schema','iw7.beacon-tool-phase/1'),@('phase','write'),@('failure','timeout'),@('exit_code',1),@('exit_code',$null),@('exit_code','0'))){
    $bad=$valid|ConvertTo-Json|ConvertFrom-Json;$bad.($pair[0])=$pair[1]
    Refuse {Assert-MaterialV2PhaseResult $bad 'read' ('a'*64) $identity}
}
Refuse {Assert-MaterialV2PhaseResult $valid 'read' ('b'*64) $identity}
Refuse {Assert-MaterialV2PhaseResult $valid 'read' ('a'*64) ([pscustomobject]@{ExitCode=1;JobActiveAtClose=0})}
Refuse {Assert-MaterialV2PhaseResult $valid 'read' ('a'*64) ([pscustomobject]@{ExitCode=0;JobActiveAtClose=1})}
# SourceId semantics are the existing ModelFF contract, not a new stock schema.
$entry=[pscustomobject]@{Relative='one.ff'}
Set-MaterialV2SourceIdentity $entry 'volume:file'
if($entry.SourceId -cne 'volume:file'){throw 'Fresh source identity lost.'}
Set-MaterialV2SourceIdentity $entry 'volume:file'
Refuse {Set-MaterialV2SourceIdentity $entry 'volume:other'}
if($entry.SourceId -cne 'volume:file'){throw 'Conflicting bound identity was overwritten.'}
Refuse {Set-MaterialV2SourceIdentity ([pscustomobject]@{SourceId=''}) 'volume:file'}
Refuse {Set-MaterialV2SourceIdentity ([pscustomobject]@{}) ''}
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
. "$repo/sdk/modding/BeaconFF.Core.ps1"
$work='C:\material-v2-pure-fixture\work'
$files=@([pscustomobject]@{FullName="$work\stock.ff";Length=900000000L},
    [pscustomobject]@{FullName="$work\copied.dll";Length=1024L},
    [pscustomobject]@{FullName="$work\main\fileSysCheck.cfg";Length=77L},
    [pscustomobject]@{FullName='C:\material-v2-pure-fixture\mod.ff';Length=42L})
# Baseline storage modes are provenance only; accounting follows actual staging.
$inputs=@([pscustomobject]@{Relative='stock.ff';Mode='HardLink';BaselineMode='Copy'},
    [pscustomobject]@{Relative='copied.dll';Mode='Copy';BaselineMode='HardLink'},
    [pscustomobject]@{Relative='main/fileSysCheck.cfg';Mode='Copy';BaselineMode='Copy'})
if((Measure-MaterialV2OutputFiles $files $work $inputs) -ne 1143L){throw 'Copied inputs were hidden from generated output budget.'}
$bound=@([pscustomobject]@{Relative='main/code_pre_gfx.ff';Mode='HardLink'},
    [pscustomobject]@{Relative='tlsdll.dll';Mode='Copy'},
    [pscustomobject]@{Relative='main/fileSysCheck.cfg';Mode='Copy';Bytes=77;SourceId='volume:source';Attributes=33})
Set-MaterialV2StagingModes $bound
if($bound[0].BaselineMode -cne 'HardLink' -or $bound[1].BaselineMode -cne 'Copy' -or $bound[1].Mode -cne 'HardLink' -or
   $bound[2].Mode -cne 'Copy' -or $bound[2].Attributes -ne 33){throw 'Operational modes overwrote baseline or source attributes.'}
Assert-MaterialV2CopyIdentity $bound[2] 'volume:owned-copy'
Refuse {Assert-MaterialV2CopyIdentity $bound[2] 'volume:source'}
Refuse {Assert-MaterialV2CopyIdentity $bound[2] ''}
Refuse {Assert-MaterialV2CopyIdentity $bound[1] 'volume:owned-copy'}
$wrongCopy=$bound[2].PSObject.Copy();$wrongCopy.Bytes=78
Refuse {Assert-MaterialV2CopyIdentity $wrongCopy 'volume:owned-copy'}
if($bound[2].Attributes -ne 33){throw 'Pure copy gate mutated source attributes.'}
# Deterministic mocked scheduler/clock/owner: never loads a native job or CIM.
$script:identityFixture=$null
function New-IdentityFixture([string]$Mode){
    $script:identityFixture=[pscustomobject]@{Mode=$Mode;Calls=0;Sleeps=0;ClockCalls=0;Owner=$null}
    $owner=[pscustomobject]@{PID=37;Exited=$false;Resumed=$false}
    $owner|Add-Member ScriptMethod Resume {
        if($script:identityFixture.Mode -ceq 'resume-failure'){throw 'Mock resume failure'}
        $this.Resumed=$true
        if($script:identityFixture.Mode -ceq 'already-finished'){$this.Exited=$true}
    }
    $script:identityFixture.Owner=$owner
    $owner
}
function Get-MaterialV2UtcNow {
    $script:identityFixture.ClockCalls++
    $time=[datetime]::new(2026,10,12,4,0,0,[DateTimeKind]::Utc)
    if($script:identityFixture.Mode -ceq 'timeout' -and $script:identityFixture.ClockCalls -gt 1){$time=$time.AddSeconds(6)}
    $time
}
function Start-Sleep {param($Milliseconds) $script:identityFixture.Sleeps++}
function Add-IW7ResourceProcess {param($Token,$ProcessId)
    if(!$script:identityFixture.Owner.Resumed -or $Token -cne 'mock-token' -or $ProcessId -ne 37){throw 'Registration occurred before verified owner Resume'}
    $script:identityFixture.Calls++
    switch($script:identityFixture.Mode){
        'delay' {if($script:identityFixture.Calls -lt 3){throw 'Child identity unavailable: mocked WMI delay'}}
        'exits-during-query' {$script:identityFixture.Owner.Exited=$true;throw 'Child identity unavailable: root exited'}
        'timeout' {throw 'Child identity unavailable: timeout fixture'}
        'other-error' {throw 'Different scheduler refusal'}
    }
}
$owner=New-IdentityFixture 'delay'
$started=Start-MaterialV2OwnedPhase $owner 'mock-token'
if(!$started.SchedulerAttached -or $script:identityFixture.Calls -ne 3 -or $script:identityFixture.Sleeps -ne 2){throw 'Bounded WMI-delay retry failed.'}
$owner=New-IdentityFixture 'already-finished'
$started=Start-MaterialV2OwnedPhase $owner 'mock-token'
if($started.SchedulerAttached -or $script:identityFixture.Calls -ne 0){throw 'Short phase was unnecessarily registered.'}
$owner=New-IdentityFixture 'exits-during-query'
$started=Start-MaterialV2OwnedPhase $owner 'mock-token'
if($started.SchedulerAttached -or $script:identityFixture.Calls -ne 1 -or $script:identityFixture.Sleeps -ne 0){throw 'Registration retried after original root exited.'}
foreach($mode in @('timeout','other-error','resume-failure')){
    $owner=New-IdentityFixture $mode
    Refuse {Start-MaterialV2OwnedPhase $owner 'mock-token'}
    if($script:identityFixture.Calls -gt 1 -or $script:identityFixture.Sleeps -ne 0){throw 'Unrelated error or expired retry was swallowed.'}
}
'PASS: two parses, native4/6 and FF8/11 budgets, 24 refusals, mode/identity/copy gates and mocked resumed-process WMI/short-phase cases; no Add-Type, lease or native process.'

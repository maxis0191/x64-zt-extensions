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
$inputs=@([pscustomobject]@{Relative='stock.ff';Mode='HardLink'},
    [pscustomobject]@{Relative='copied.dll';Mode='Copy'},
    [pscustomobject]@{Relative='main/fileSysCheck.cfg';Mode='Copy'})
if((Measure-MaterialV2OutputFiles $files $work $inputs) -ne 1143L){throw 'Copied inputs were hidden from generated output budget.'}
'PASS: two parses, native4/6 and FF8/11 budgets, compiler/quoting contract, 17 refusals, source identity and copy accounting; no Add-Type, lease or native process.'

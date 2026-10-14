"""Causal source guards for fixed coverage/reference modal; no retail or native."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(shutil.which('pwsh'), 'PowerShell required')
class CoverageTests(unittest.TestCase):
    def run_script(self, script, *sources):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'check.ps1';path.write_text(script,encoding='utf-8')
            result=subprocess.run([shutil.which('pwsh'),'-NoLogo','-NoProfile','-File',str(path),
                *map(str,sources),temp],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_actual_grouped_diagnostic_composes_strict_runtime_options(self):
        self.run_script(r'''
param($Measure,$Root)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Measure,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Runner parse failed'}
$spec=@($ast.FindAll({param($n);$n -is [Management.Automation.Language.AssignmentStatementAst] -and
    $n.Left.Extent.Text -ceq '$diagnostic' -and $n.Right.Extent.Text.Contains("Mode='reference-with-one-modal'")},$true))
$init=@($ast.FindAll({param($n);$n -is [Management.Automation.Language.AssignmentStatementAst] -and
    $n.Left.Extent.Text -ceq '$options' -and $n.Right.Extent.Text.Contains('CaptureSource=$diagnostic.CaptureSource')},$true))
if($spec.Count -ne 1 -or $init.Count -ne 1){throw 'Exact grouped plan and real runtime initializer required'}
$PackageRoot=$Root;$RunRoot=$Root;$DiagnosticZone='global_mp';$CandidateRoot=$Root
$python=$Measure;$toolSHA='1'*64;$inputs=@();function Get-H1Clock {100L}
. ([scriptblock]::Create($spec[0].Extent.Text))
# Preserve the real planner serialization boundary, including nullable properties.
$diagnostic=($diagnostic|ConvertTo-Json -Depth 8|ConvertFrom-Json)
if($diagnostic.Mode -cne 'reference-with-one-modal' -or $diagnostic.CaptureSource -ne $null -or
   $diagnostic.Cdb -ne $null -or $diagnostic.CdbSHA256 -ne $null -or $diagnostic.CPUSeconds -ne 0){throw 'Explicit combined-only optional diagnostic contract required'}
$fixed=$diagnostic
$old=$fixed|ConvertTo-Json -Depth 8|ConvertFrom-Json
$old.PSObject.Properties.Remove('CaptureSource');$old.PSObject.Properties.Remove('CdbSHA256')
$diagnostic=$old;$failed=$false
try{. ([scriptblock]::Create($init[0].Extent.Text))}catch{$failed=$_.Exception.Message.Contains("'CaptureSource'")}
if(!$failed){throw 'The old actual grouped shape must reproduce prelaunch failure'}
$diagnostic=$fixed
. ([scriptblock]::Create($init[0].Extent.Text))
if($options.CaptureSource -ne $null -or $options.Cdb -ne $null -or $options.CdbSHA256 -ne $null -or
   $options.StartedMs -ne 100 -or $options.Inputs.Count -ne 0){throw 'Fixed real options contract differs'}
if('IW7.AnimationProbe.NativeJob' -as [type]){throw 'Pure initializer test loaded native job'}
''',Path(__file__).with_name('Measure-StockReference.ps1'))

    def test_fixed_group_is_exact_typed_and_preserves_prior_inputs(self):
        self.run_script(r'''
param($Core,$Root)
$ErrorActionPreference='Stop';. $Core
$numbers=@(1,17,19,21,25,26,36,37,52,53,68,69,84,85,100,101,116,117,132,133,148,149,164,165,180,181,196,197,212,213,228,229,244)
$rows=@();$entries=@()
foreach($n in $numbers){
    $name='assetfile'+$n+'.pak';$sha=('{0:x64}' -f $n);$bytes=1000L+$n
    $rows+=[pscustomobject]@{RelativePath=$name;Length=$bytes;SHA256=$sha;Operation='NTFSHardLinkImmutableStock'}
    $entries+=[pscustomobject]@{Relative='zone/'+$name;Source=(Join-Path $Root $name);Mode='HardLink';Bytes=$bytes;ModifiedUtc='2026-09-29T21:46:01.4996203Z';Attributes=32;ExpectedSourceId=('11111111:{0:X16}' -f $n);ExpectedSHA256=$sha}
}
$existing=@(foreach($i in 1..71){[pscustomobject]@{Relative="main/authored-$i.ff"}})+@($entries|Where-Object {$_.Relative -cin @('zone/assetfile1.pak','zone/assetfile17.pak','zone/assetfile37.pak')})
$binding=[pscustomobject]@{Schema='iw7.world-assetfile-coverage/1';BaselineBindingSHA256=('a'*64);RequiredPak17BindingSHA256=('b'*64);RequiredPak37BindingSHA256=('c'*64);ReviewedManifestSHA256='9116255ef148a324df15fa914795a7917615f023973111fdc39ae7329a9dcbf4';NamespaceCoverageOnly=$true;MinimalDependencySet=$false;MetadataOnly=$true;CurrentPayloadHashed=$false;AliasesCreated=$false;Inputs=$entries}
$prior=$existing|ConvertTo-Json -Depth 7 -Compress
$extra=@(Get-ArenaAssetfileCoverageInputs $existing $binding $rows ('a'*64) ('b'*64) ('c'*64))
if($extra.Count -ne 30 -or (@($existing)+$extra).Count -ne 104 -or @($extra|Where-Object {$_.Relative -cin @('zone/assetfile1.pak','zone/assetfile17.pak','zone/assetfile37.pak')}).Count -or ($existing|ConvertTo-Json -Depth 7 -Compress) -cne $prior){throw 'Coverage changed prior inputs or added wrong group'}
foreach($kind in 'missing','duplicate','imagefile','unlisted','provider','volume','bytes','sha','reparse','copy','prior','minimal','hashed','contractarray','entryarray','sizefloat','reviewrow'){
    $bad=$binding|ConvertTo-Json -Depth 7|ConvertFrom-Json;$old=$existing|ConvertTo-Json -Depth 7|ConvertFrom-Json;$review=$rows|ConvertTo-Json -Depth 7|ConvertFrom-Json
    switch($kind){
        missing {$bad.Inputs=$bad.Inputs[0..31]}
        duplicate {$bad.Inputs[32]=$bad.Inputs[31]}
        imagefile {$bad.Inputs[32].Relative='zone/imagefile244.pak'}
        unlisted {$bad.Inputs[32].Relative='zone/assetfile243.pak'}
        provider {$bad.Inputs[32].Source=Join-Path $Root 'other/assetfile244.pak'}
        volume {$bad.Inputs[32].ExpectedSourceId='22222222:0000000000000244'}
        bytes {$bad.Inputs[32].Bytes++}
        sha {$bad.Inputs[32].ExpectedSHA256='f'*64}
        reparse {$bad.Inputs[32].Attributes=1056}
        copy {$bad.Inputs[32].Mode='Copy'}
        prior {$old[72].ExpectedSourceId='11111111:0000000000009999'}
        minimal {$bad.MinimalDependencySet=$true}
        hashed {$bad.CurrentPayloadHashed=$true}
        contractarray {$bad.Schema=@($bad.Schema)}
        entryarray {$bad.Inputs[32].Source=@($bad.Inputs[32].Source)}
        sizefloat {$bad.Inputs[32].Bytes=[double]$bad.Inputs[32].Bytes}
        reviewrow {$review[32].Length++}
    }
    $caught=$false;try{$null=Get-ArenaAssetfileCoverageInputs $old $bad $review ('a'*64) ('b'*64) ('c'*64)}catch{$caught=$true};if(!$caught){throw "Invalid coverage $kind accepted"}
}
foreach($field in 'Relative','Source','Mode','ExpectedSourceId','ExpectedSHA256','Bytes','ModifiedUtc','Attributes'){
    $bad=$binding|ConvertTo-Json -Depth 7|ConvertFrom-Json;$bad.Inputs[32].$field=@($bad.Inputs[32].$field)
    $caught=$false;try{$null=Get-ArenaAssetfileCoverageInputs $existing $bad $rows ('a'*64) ('b'*64) ('c'*64)}catch{$caught=$true};if(!$caught){throw "Singleton $field accepted"}
}
''',Path(__file__).with_name('AssetfileCoverage.Core.ps1'))

    def test_reference_modal_negative_fatal_late_identity_and_unknown_closure(self):
        self.run_script(r'''
param($Core,$Measure,$Root)
$ErrorActionPreference='Stop';. $Core
$script:Clock=55000L;$script:Calls=0;$script:Found=$false;$script:Unknown=$false;$script:Mismatch=$false;$script:BadRecord=$false
$created='2026-10-14T00:00:00.0000006Z'
function Get-H1Clock {$script:Clock}
function Get-H1OriginalState($Owner){[pscustomobject]@{RootExited=$false;PID=$(if($script:Mismatch){124}else{123});Image=$Owner.Image;CreatedUtc=$created}}
function Register-H1Original {}
function Invoke-OriginalArenaTool($Context,$Exe,$SHA,$Arguments,$Work,$RunRoot,$Phase,$Inputs,$Seconds){
    $script:Calls++;if($Seconds -ne 10 -or $Phase -cne 'load-modal' -or '--snapshot' -cin $Arguments -or '-z' -cin $Arguments){throw 'Unexpected helper'}
    if($Arguments[[array]::IndexOf($Arguments,'--created-filetime')+1] -cne [string](([datetimeoffset]$created).UtcDateTime.ToFileTimeUtc()) -or $Arguments[[array]::IndexOf($Arguments,'--parent-pid')+1] -cne [string]$PID){throw 'Original identity lost'}
    if($script:Unknown){$Context.Closed=$false;throw 'Unknown original helper closure'}
    $output=$Arguments[[array]::IndexOf($Arguments,'--output')+1]
    $record=@{schema='iw7.world-modal-window/1';identity_verified_after=$true;modal_window_observed=$script:Found;title='Fatal Error'}
    if($script:BadRecord){$record.modal_window_observed=@($true)}
    $record|ConvertTo-Json|Set-Content $output;$Context.Closed=$true;[pscustomobject]@{JobClosed=$true;ExitCode=0}
}
$logs=Join-Path $Root 'logs';$null=[IO.Directory]::CreateDirectory($logs)
$line='[ INFO ][ zonetool::iw7::load_zone ]: Loading zone "cp_zmb"...'
[IO.File]::WriteAllText((Join-Path $logs 'stdout.log'),$line+"`n")
function New-Case($Name){
    $script:Target=[pscustomobject]@{Owner=[pscustomobject]@{Image=(Join-Path $Root 'authored.exe')};Closed=$false;Lease=[pscustomobject]@{Token='authored'};Work=$Root}
    $script:State=@{Identity=@{PID=123;Image=$Target.Owner.Image;CreatedUtc=$created}}
    $script:Options=[pscustomobject]@{StartedMs=0L;RunRoot=(Join-Path $Root $Name);ReferenceModalOnce=$true;ModalTextOnly=$true;ModalSource='authored-modal.py';Python='authored-python';PythonSHA256=('1'*64);ToolSHA256=('2'*64);Inputs=@()}
    $script:Evidence=[ordered]@{Attempted=$false;LastBytes=(Get-Item (Join-Path $logs 'stdout.log')).Length;LastProgressMs=0L;Outcome='NotTriggered'}
}
New-Case negative;Invoke-ArenaLoadDiagnostic $Target $State $logs $Options $Evidence
if($script:Calls -ne 1 -or $Evidence.Outcome -cne 'NoModalWindowObserved' -or !$Evidence.ReferenceContinues -or !$Target.DiagnosticContext.Closed -or $Evidence.ModalWindowObserved){throw 'NoModal fabricated success or stopped reference'}
Invoke-ArenaLoadDiagnostic $Target $State $logs $Options $Evidence;if($script:Calls -ne 1){throw 'Negative helper repeated'}
$script:Found=$true;New-Case fatal;$caught=$false;try{Invoke-ArenaLoadDiagnostic $Target $State $logs $Options $Evidence}catch{$caught=$_.Exception.Message -ceq 'Owned modal captured; reference not measured.'}
if(!$caught -or $Evidence.Outcome -cne 'Captured' -or !$Evidence.ModalWindowObserved -or $Evidence.ReferenceContinues -or !$Target.DiagnosticContext.Closed){throw 'Captured modal did not fail reference'}
$before=$script:Calls;$script:Clock=225000L;New-Case late;Invoke-ArenaLoadDiagnostic $Target $State $logs $Options $Evidence
if($script:Calls -ne $before -or $Evidence.Outcome -cne 'DeclinedLate'){throw 'Late helper overran phase'}
$script:Clock=55000L;$script:Mismatch=$true;New-Case identity;$caught=$false;try{Invoke-ArenaLoadDiagnostic $Target $State $logs $Options $Evidence}catch{$caught=$_.Exception.Message -ceq 'Original live load identity required.'}
if(!$caught -or $script:Calls -ne $before){throw 'Changed identity reached helper'}
$script:Mismatch=$false;$script:Unknown=$true;New-Case unknown;$caught=$false;try{Invoke-ArenaLoadDiagnostic $Target $State $logs $Options $Evidence}catch{$caught=$_.Exception.Message -ceq 'Unknown original helper closure'}
if(!$caught -or $Target.DiagnosticContext.Closed -or $Target.Closed -or $Evidence.DiagnosticClosed){throw 'Unknown combined closure lost original context'}
$script:Unknown=$false;$script:BadRecord=$true;New-Case malformed;$caught=$false;try{Invoke-ArenaLoadDiagnostic $Target $State $logs $Options $Evidence}catch{$caught=$_.Exception.Message -ceq 'Scalar original modal record fields required.'}
if(!$caught -or $Evidence.Outcome -cne 'Failed'){throw 'Singleton record forged Captured'}
$dummy=@{PackageRoot=$Root;RunRoot=$Root;StockBindingPlan='absent';StockBindingPlanSHA256=('a'*64);ToolSource=$Root;CandidateRoot=$Root;CandidateArtifactSHA256=('b'*64);NativeJobAssembly='absent.dll'}
$caught=$false;try{& $Measure @dummy -ReferenceModalOnce}catch{$caught=$_.Exception.Message -ceq 'Fixed coverage and reference modal-once mode require each other.'};if(!$caught){throw 'Unbound mode reached file/native access'}
if('IW7.AnimationProbe.NativeJob' -as [type]){throw 'Source fixtures loaded native job'}
''',Path(__file__).with_name('LoadDiagnostic.Core.ps1'),Path(__file__).with_name('Measure-StockReference.ps1'))


if __name__=='__main__':
    unittest.main()

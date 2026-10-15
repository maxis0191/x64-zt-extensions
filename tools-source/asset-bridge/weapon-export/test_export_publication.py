"""Execute the actual export finally and publication functions on tiny files.

Only original-job, stock, scheduler, clock and budget boundaries are mocked.
A test-only FileStream subclass injects IO faults on the same real file handle.
No Run body, native tool, SDK/retail input or actual lease is used.
"""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


RUNNER = Path(__file__).with_name('Run-PlayerTemplateExport.ps1').resolve()

HARNESS = r'''
param($Runner,$Directory,$Fault='None',$Target='final-closure.json')
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Runner,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Actual runner syntax failed'}
foreach($name in 'New-PlayerPublicationStream','Write-PlayerPublication','Get-PlayerOriginalGuardHandle'){
 $function=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true)
 if($function){. ([scriptblock]::Create($function.Extent.Text))}
}
Add-Type -TypeDefinition @'
using System;
using System.IO;
public sealed class PlayerPublicationFaultStream : FileStream {
 public string Fault;
 public Microsoft.Win32.SafeHandles.SafeFileHandle OriginalHandle;
 public Action<string, FileStream> Observe;
 public PlayerPublicationFaultStream(string path,string fault) : base(path,FileMode.CreateNew,FileAccess.ReadWrite,FileShare.Read) { OriginalHandle=SafeFileHandle; Fault=fault; }
 public override void Write(byte[] buffer,int offset,int count) {
  if(Observe!=null) Observe("Write",this);
  if(Fault=="Write") throw new IOException("injected publication Write");
  base.Write(buffer,offset,count);
 }
 public override void Flush(bool disk) {
  if(Observe!=null) Observe("Flush",this);
  if(Fault=="Flush") throw new IOException("injected publication Flush");
  base.Flush(disk);
 }
 public override int Read(byte[] buffer,int offset,int count) {
  if(Observe!=null) Observe("Readback",this);
  if(Fault=="Readback") throw new IOException("injected publication Readback");
  int result=base.Read(buffer,offset,count);
  if(Fault=="Hash" && result>0) buffer[offset]^=1;
  return result;
 }
}
'@
$source=Join-Path $Directory 'source.json';[IO.File]::WriteAllText($source,'{}')
$sourceStream=[IO.File]::Open($source,'Open','Read','Read')
$sourceHandle=$sourceStream.SafeFileHandle
$guards=[Collections.Generic.List[object]]::new();$guards.Add($sourceStream)
$sentinelPath=Join-Path $Directory 'sentinel.json';[IO.File]::WriteAllText($sentinelPath,'{}')
$sentinelHandle=[IO.File]::OpenHandle($sentinelPath,'Open','Read','Read');$guards.Add($sentinelHandle)
$foreign=$null
if($Fault -ceq 'Foreign'){
 $foreign=[pscustomobject]@{SafeFileHandle=$sourceHandle;Disposed=$false}
 $foreign|Add-Member ScriptMethod Dispose {$this.Disposed=$true}
 $guards.Add($foreign)
}
$publications=[Collections.Generic.List[object]]::new()
$plan=[pscustomobject]@{RunRoot=$Directory;GroupSeconds=600;GeneratedLimitBytes=16777216;MetadataReserveBytes=1048576;StockManifests=@(1)}
$PlanSHA256='a'*64
$context=[pscustomobject]@{Closed=$true;Lease=[pscustomobject]@{Token='synthetic-only'};Guards=$guards}
$state=[ordered]@{Status='MeasuredPassed';CanExit=$false;UnknownCopyCreation=$false;CandidateExecuted=$true;
 LeaseReleased=$false;GuardsDisposed=$false;PublicationGuardsDisposed=$false;MeasuredReadback=$false;FinalReadback=$false}
$stock=[Collections.Generic.List[object]]::new()
$stock.Add([pscustomobject]@{Plan=[pscustomobject]@{TargetRoot=$Directory};Phase='Prepared';Prepared=$true;SourcePreserved=$true;UnknownCreation=$false;CreatedLinks=@(1)})
$root=@{Context=$context;State=$state;Plan=$plan;StockContexts=$stock;PublicationGuards=$publications}
$global:IW7PlayerTemplateExport=$root;$script:PlayerTemplateExportOriginalRoot=$root
[AppDomain]::CurrentDomain.SetData('Player.Publication.Causal.Original',$root)
$originalRoot=$root;$originalContext=$context;$originalState=$state;$originalGuards=$guards;$originalPublications=$publications
$script:Releases=0;$script:ClosingAllowed=$false;$script:Events=[Collections.Generic.List[string]]::new()
$script:SeenStreams=[Collections.Generic.List[object]]::new();$script:SeenHandles=[Collections.Generic.List[object]]::new()
function Assert-OriginalHeld {
 if(![object]::ReferenceEquals($root,[AppDomain]::CurrentDomain.GetData('Player.Publication.Causal.Original')) -or
    ![object]::ReferenceEquals($root,$global:IW7PlayerTemplateExport) -or ![object]::ReferenceEquals($guards,$originalGuards) -or
    ![object]::ReferenceEquals($publications,$originalPublications) -or !$sourceStream.CanRead -or $sourceHandle.IsClosed -or
    $sentinelHandle.IsClosed -or ![object]::ReferenceEquals($guards[1],$sentinelHandle)){throw 'Original held Source references lost'}
 foreach($publication in $publications){if(!$publication.CanRead -or !$publication.CanWrite){throw 'Publication closed before final validation'}}
}
function New-PlayerPublicationStream([string]$Path){
 if([IO.Path]::GetFileName($Path) -ceq $Target -and $Fault -ceq 'CreateNew'){[IO.File]::WriteAllText($Path,'existing proof')}
 $mode=if([IO.Path]::GetFileName($Path) -ceq $Target){$Fault}else{'None'}
 $stream=[PlayerPublicationFaultStream]::new($Path,$mode)
 $script:SeenStreams.Add($stream);$script:SeenHandles.Add($stream.OriginalHandle)
 $stream.Observe={param($Operation,$Actual)
  if(!$script:ClosingAllowed){Assert-OriginalHeld}
  if(!@($publications|Where-Object {[object]::ReferenceEquals($_,$Actual)}).Count){throw 'Actual publication stream was not enrolled before IO'}
  $script:Events.Add($(if($script:ClosingAllowed){'Closing'}else{$Operation})+':'+[IO.Path]::GetFileName($Actual.Name))
 }
 return $stream
}
function Close-PlayerOriginalJobs {$state.OriginalJobsClosed=$true}
function Confirm-PlayerStock {Assert-OriginalHeld}
function Close-IW7StockLinkGuards($Transaction) {Assert-OriginalHeld}
function Exit-IW7ResourceLease($Token) {Assert-OriginalHeld;$script:Releases++}
function Assert-PlayerExportClock {
 Assert-OriginalHeld
 if($state.LeaseReleased -and $state.FinalReadback){$script:Events.Add('FinalClock');if($Fault -ceq 'Clock'){throw 'injected final clock'}}
}
function Test-PlayerGenerated($State,$Limit=0) {
 Assert-OriginalHeld
 if($State.LeaseReleased -and $State.FinalReadback){$script:Events.Add('FinalBudget');if($Fault -ceq 'Budget'){throw 'injected final budget'};$script:ClosingAllowed=$true}
}
# The historical reader is only used when demonstrating the old finally defect.
function Read-PlayerExportSource($Path,$SHA256,$Bytes) {
 if([IO.Path]::GetFileName($Path) -ceq $Target -and $Fault -ceq 'Readback'){throw 'injected old final readback'}
}
$created=$true;$failure=$null
$try=$ast.Find({param($n) $n -is [Management.Automation.Language.TryStatementAst] -and $null -ne $n.Finally -and $n.Finally.Extent.Text.Contains('ClosedFinalizationIncomplete')},$true)
if(!$try){throw 'Actual runtime finally not found'}
try{
 . ([scriptblock]::Create($try.Finally.Extent.Text.Trim().TrimStart('{').TrimEnd('}'))) *> $null
 $same=[object]::ReferenceEquals($root,$originalRoot) -and [object]::ReferenceEquals($context,$originalContext) -and
       [object]::ReferenceEquals($state,$originalState) -and [object]::ReferenceEquals($guards,$originalGuards) -and
       [object]::ReferenceEquals($publications,$originalPublications)
 $finalPath=Join-Path $Directory 'final-closure.json';$final=$null
 if($state.CanExit){$final=[IO.File]::ReadAllText($finalPath)|ConvertFrom-Json}
 [ordered]@{Status=$state.Status;CanExit=$state.CanExit;SameReferences=$same;Releases=$script:Releases;
  LeaseNull=($null -eq $context.Lease);LeaseReleased=$state.LeaseReleased;Guards=$guards.Count;
  SourceOpen=$sourceStream.CanRead;SourceHandleClosed=$sourceHandle.IsClosed;PublicationGuards=$publications.Count;
  DirectHandleClosed=$sentinelHandle.IsClosed;SameDirectHandle=($guards.Count -eq 0 -or [object]::ReferenceEquals($guards[1],$sentinelHandle));
  ForeignDisposed=($null -ne $foreign -and $foreign.Disposed);
  PublicationOpen=@($publications|Where-Object {$_.CanRead -and $_.CanWrite}).Count;
  AllObservedHandlesClosed=(!@($script:SeenHandles|Where-Object {!$_.IsClosed}).Count);
  GuardsDisposed=$state.GuardsDisposed;PublicationGuardsDisposed=$state.PublicationGuardsDisposed;
  FinalReadback=$state.FinalReadback;Final=$final;Events=$script:Events.ToArray();
  Error=$(if($state.Contains('FinalizationError')){$state.FinalizationError}else{''})}|ConvertTo-Json -Depth 6 -Compress
}finally{
 foreach($stream in $script:SeenStreams){$stream.Fault='None';$stream.Observe=$null;$stream.Dispose()};$sourceStream.Dispose();$sentinelHandle.Dispose()
 [AppDomain]::CurrentDomain.SetData('Player.Publication.Causal.Original',$null)
}
'''


class ExportPublicationTests(unittest.TestCase):
    def test_actual_unmocked_publication_factory_keeps_original_stream_and_refuses_overwrite(self):
        script_text = r'''
param($Runner,$Directory)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Runner,[ref]$tokens,[ref]$errors)
foreach($name in 'New-PlayerPublicationStream','Write-PlayerPublication'){
 $function=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true)
 . ([scriptblock]::Create($function.Extent.Text))
}
$pubs=[Collections.Generic.List[object]]::new()
$script:PlayerTemplateExportOriginalRoot=@{Plan=[pscustomobject]@{MetadataReserveBytes=1048576};PublicationGuards=$pubs}
$path=Join-Path $Directory 'proof.json';$raw=[Text.UTF8Encoding]::new($false).GetBytes('{"proof":true}')
try{
 $sha=Write-PlayerPublication $path $raw;$actual=$pubs[0]
 if($pubs.Count -ne 1 -or $actual -isnot [IO.FileStream] -or !$actual.CanRead -or !$actual.CanWrite){throw 'Actual publication guard absent'}
 if($sha -cne [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant()){throw 'Actual same-stream hash differs'}
 $blocked=$false;try{$writer=[IO.File]::Open($path,'Open','Write','ReadWrite');$writer.Dispose()}catch{$blocked=$true}
 if(!$blocked){throw 'Held publication allowed external mutation'}
 $refused=$false;try{$null=Write-PlayerPublication $path $raw}catch{$refused=$true}
 if(!$refused -or $pubs.Count -ne 1 -or ![object]::ReferenceEquals($actual,$pubs[0]) -or !$actual.CanRead){throw 'CreateNew refusal lost original guard'}
 $held=$actual.SafeFileHandle
 $actual.Dispose()
 if(!$held.IsClosed){throw 'Original publication handle not closed'}
 Write-Output '{"SameOriginalStream":true,"WriteBlocked":true,"CreateNewRefused":true,"OriginalHandleClosed":true}'
}finally{foreach($publication in $pubs){$publication.Dispose()}}
'''
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'actual-factory.ps1'
            script.write_text(script_text, encoding='utf-8')
            result = subprocess.run([shutil.which('pwsh'), '-NoLogo', '-NoProfile', '-File', str(script),
                                     str(RUNNER), directory], capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(all(json.loads(result.stdout).values()))

    def invoke(self, fault='None', target='final-closure.json', runner=RUNNER):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'causal.ps1'
            script.write_text(HARNESS, encoding='utf-8')
            result = subprocess.run([shutil.which('pwsh'), '-NoLogo', '-NoProfile', '-File', str(script),
                                     str(runner), directory, fault, target],
                                    capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)

    def test_actual_finally_retains_original_source_and_publications_on_postrelease_failures(self):
        for fault in ('CreateNew', 'Write', 'Flush', 'Readback', 'Hash', 'Clock', 'Budget'):
            with self.subTest(fault=fault):
                report = self.invoke(fault)
                self.assertEqual((report['Status'], report['CanExit'], report['Releases'], report['LeaseNull'],
                                  report['LeaseReleased'], report['Guards'], report['SourceOpen'],
                                  report['SourceHandleClosed'], report['SameReferences']),
                                 ('ClosedFinalizationIncomplete', False, 1, True, True, 2, True, False, True), report)
                self.assertFalse(report['DirectHandleClosed'], report)
                self.assertTrue(report['SameDirectHandle'], report)
                count = 2 if fault == 'CreateNew' else 3
                self.assertEqual((report['PublicationGuards'], report['PublicationOpen']), (count, count), report)
                self.assertFalse(report['GuardsDisposed'] or report['PublicationGuardsDisposed'], report)
                self.assertTrue(report['Error'], report)

    def test_actual_finally_keeps_same_guards_and_lease_before_release(self):
        for target in ('measured-before-release.json', 'closure-before-release.json'):
            with self.subTest(target=target):
                report = self.invoke('Readback', target)
                self.assertEqual((report['Status'], report['CanExit'], report['Releases'], report['LeaseNull'],
                                  report['LeaseReleased'], report['Guards'], report['SourceOpen'], report['SameReferences']),
                                 ('UnknownRetained', False, 0, False, False, 2, True, True), report)
                count = 1 if target.startswith('measured') else 2
                self.assertEqual((report['PublicationGuards'], report['PublicationOpen']), (count, count), report)

    def test_actual_finally_closes_verified_original_handles_only_after_final_checks(self):
        report = self.invoke()
        self.assertEqual((report['Status'], report['CanExit'], report['Releases'], report['LeaseNull'],
                          report['Guards'], report['PublicationGuards'], report['SourceOpen'],
                          report['SourceHandleClosed'], report['AllObservedHandlesClosed'], report['SameReferences']),
                         ('Passed', True, 1, True, 0, 0, False, True, True, True), report)
        self.assertTrue(report['GuardsDisposed'] and report['PublicationGuardsDisposed'] and report['FinalReadback'], report)
        self.assertTrue(report['DirectHandleClosed'] and report['SameDirectHandle'], report)
        events = report['Events']
        self.assertLess(events.index('FinalClock'), events.index('FinalBudget'), report)
        self.assertTrue(all(event.startswith('Closing:') for event in events[events.index('FinalBudget') + 1:]), report)
        self.assertEqual((report['Final']['Schema'], report['Final']['GuardsDisposed'], report['Final']['SourceGuardsHeld'],
                          report['Final']['PublicationGuardsHeld'], report['Final']['LeaseReleased']),
                         ('iw7.player-export-closure/2', False, 2, 3, True), report)

    def test_actual_mixed_guard_preflight_refuses_foreign_shape_before_any_disposal(self):
        report = self.invoke('Foreign')
        self.assertEqual((report['Status'], report['CanExit'], report['LeaseReleased'], report['LeaseNull'],
                          report['Guards'], report['SourceOpen'], report['SourceHandleClosed'], report['DirectHandleClosed'],
                          report['SameDirectHandle'], report['ForeignDisposed'], report['PublicationOpen']),
                         ('ClosedFinalizationIncomplete', False, True, True, 3, True, False, False, True, False, 3), report)
        self.assertIn('Unexpected original publication/source guard type', report['Error'])


if __name__ == '__main__':
    unittest.main()

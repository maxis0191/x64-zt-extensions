"""Pure source/metadata preflight and before-native refusal checks. No CPP."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import prepare_definition_cohort as recipe

RUNNER = Path(__file__).with_name('Run-PlayerTemplateBuild.ps1').resolve()


class DefaultTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        source = self.root / 'provider.ps1'
        source.write_bytes(b'# synthetic provider, must never be imported\n')
        self.provider = dict(Path=str(source), Bytes=source.stat().st_size,
            SHA256=hashlib.sha256(source.read_bytes()).hexdigest(), IsText=True)
        self.plan = dict(Schema='iw7.player-template-cohort-source/1', Ready=False,
            CandidateExecuted=False, WeaponReady=False, PhysicsQualified=False,
            PAPTransactionQualified=False, RetainedObjects=412, LinkedObjectCount=413,
            SourceBindings=[], PreparedBindings=[], OwnDirectIncludeCoverage=[dict(Pinned=True)],
            RequireActualDependenciesWithinGuardedSet=True, RunRoot=str(self.root/'not-created'),
            Providers={key: str(source) for key in ('Core','CompilerCore','ObserverSource',
                'CompilerPolicySource','Scheduler','Profile')}, ParentBindings=[self.provider],
            RunnerBinding=dict(Path=str(RUNNER), Bytes=RUNNER.stat().st_size,
                SHA256=hashlib.sha256(RUNNER.read_bytes()).hexdigest()),
            GroupDeadlineSeconds=600, OutputLimitBytes=268435456, MetadataReserveBytes=1048576,
            Compiler=str(self.root/'cl.exe'), PreparedRoot=str(self.root/'prepared'), Stages=[])
        for fixture, count in (('name',8),('argv',10)):
            self.plan['Stages'] += [dict(Name=fixture+'-compile', Stage='Compile',
                DeadlineSeconds=120, Image=self.plan['Compiler'],
                Arguments=['@'+str(self.root/'prepared'/(fixture+'.rsp'))],
                Artifacts=[fixture+'.obj',fixture+'.exe',fixture+'.pdb','compile.pdb','dependencies.json']),
                dict(Name=fixture+'-test', Stage='Probe', DeadlineSeconds=15,
                Image=str(self.root/'not-created'/(fixture+'-compile')/(fixture+'.exe')),
                Arguments=[], Artifacts=[], ExpectedChecks=count,
                ExpectedStdout=f'IW7_PLAYER_TEMPLATE_{"NAME" if fixture=="name" else "ARGV"}_CHECKS={count}\n')]
        self.plan['Stages'] += [dict(Name='iw7', Stage='Compile', DeadlineSeconds=120,
            Image=self.plan['Compiler'], Arguments=['@'+str(self.root/'prepared'/'iw7.rsp')],
            Artifacts=['iw7-player-cli.obj','compile.pdb','dependencies.json']),
            dict(Name='link', Stage='Link', DeadlineSeconds=120, Image=str(self.root/'link.exe'),
            Arguments=['@'+str(self.root/'prepared'/'link.rsp')],
            Artifacts=['zonetool-iw7-player.exe','zonetool-iw7-player.pdb','zonetool-iw7-player.lib','zonetool-iw7-player.exp'])]

    def invoke(self, native=False):
        name='cohort-source-plan.json' if self.plan['Schema']=='iw7.authored-pair-core-cpp-source/1' else 'plan.json'
        path=self.root/name;raw=(json.dumps(self.plan)+'\n').encode();path.write_bytes(raw)
        command=[shutil.which('pwsh'),'-NoLogo','-NoProfile','-File',str(RUNNER),
            '-PlanPath',str(path),'-PlanSHA256',hashlib.sha256(raw).hexdigest()]
        if native: command.append('-Run')
        return subprocess.run(command, text=True, capture_output=True, timeout=15)

    def test_default_pure_and_output_absent(self):
        result=self.invoke();self.assertEqual(result.returncode,0,result.stderr)
        report=json.loads(result.stdout)
        self.assertEqual(report['Stages'],6)
        self.assertFalse(any(report[key] for key in ('NativeTypesLoaded','NativeInputsHashed',
            'RunRootCreated','LeaseAcquired','Ready')))
        self.assertFalse(Path(self.plan['RunRoot']).exists())

    def test_ready_claim_refused(self):
        self.plan['Ready']=True
        result=self.invoke();self.assertNotEqual(result.returncode,0)
        self.assertIn('unqualified source cohort',result.stderr)

    def test_sequence_refused(self):
        self.plan['Stages'][0]['Name']='link'
        result=self.invoke();self.assertNotEqual(result.returncode,0)
        self.assertIn('Fixed source-selected',result.stderr)

    def primary_plan(self):
        self.plan['PrimaryGuardFixture']=True
        source=self.root/'prepared'/'src'/'zonetool'/'zonetool'/'iw7'/'zonetool.cpp'
        source.parent.mkdir(parents=True);source.write_bytes(b'// Source fixture IW7_PLAYER_TEMPLATE_PRIMARY_REFUSAL schema=1 first_failure(reader)\n')
        self.plan['PreparedBindings']=[dict(Path=str(source),Bytes=source.stat().st_size,SHA256=hashlib.sha256(source.read_bytes()).hexdigest())]
        self.plan['Stages'][4:4]=[
            dict(Name='primary-compile',Stage='Compile',DeadlineSeconds=120,Image=self.plan['Compiler'],
                Arguments=['@'+str(self.root/'prepared'/'primary.rsp')],
                Artifacts=['primary.obj','primary.exe','primary.pdb','compile.pdb','dependencies.json']),
            dict(Name='primary-test',Stage='Probe',DeadlineSeconds=15,
                Image=str(self.root/'not-created'/'primary-compile'/'primary.exe'),Arguments=[],Artifacts=[],
                ExpectedChecks=36,ExpectedStdout='IW7_PLAYER_TEMPLATE_PRIMARY_CHECKS=36\n')]

    def test_primary_fixture_opt_in_is_pure_and_keeps_native_unopened(self):
        self.primary_plan();result=self.invoke();self.assertEqual(result.returncode,0,result.stderr)
        report=json.loads(result.stdout);self.assertEqual(report['Stages'],8);self.assertEqual(report['PrimaryChecksAuthored'],36)
        self.assertFalse(any(report[key] for key in ('NativeTypesLoaded','NativeInputsHashed','RunRootCreated','LeaseAcquired','Ready')))
        self.assertFalse(Path(self.plan['Compiler']).exists());self.assertFalse(Path(self.plan['RunRoot']).exists())

    def test_pair_cli_requires_matching_module_and_exact_eighteen_checks(self):
        self.primary_plan()
        source=Path(self.plan['PreparedBindings'][0]['Path'])
        source.write_bytes(source.read_bytes()+b'// IW7_PLAYER_PAIR_PROFILE donor=cp_zmb iw7_player_template_cli::pair_selected(args)\n')
        self.plan['PreparedBindings'][0].update(Bytes=source.stat().st_size,SHA256=hashlib.sha256(source.read_bytes()).hexdigest())
        self.plan.update(PairProfileCLI=True)
        self.plan['Stages'][3].update(ExpectedChecks=18,ExpectedStdout='IW7_PLAYER_TEMPLATE_ARGV_CHECKS=18\n')
        good=json.loads(json.dumps(self.plan));r=self.invoke();self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(json.loads(r.stdout)['ArgvChecksAuthored'],18)
        for mutate in (lambda p:p.pop('PairProfileCLI'),lambda p:p.update(PairProfileCLI=[True]),
                       lambda p:p.update(PairProfileCLI=False),lambda p:p['Stages'][3].update(ExpectedChecks='18'),
                       lambda p:p['Stages'][3].update(ExpectedChecks=10),lambda p:p['Stages'][3].update(ExpectedStdout='IW7_PLAYER_TEMPLATE_ARGV_CHECKS=10\n'),
                       lambda p:p.update(PreparedBindings=[])):
            self.plan=json.loads(json.dumps(good));mutate(self.plan)
            self.assertNotEqual(self.invoke().returncode,0)
        self.assertFalse(Path(self.plan['RunRoot']).exists())

    def test_primary_fixture_mixed_or_coerced_contract_refused_before_effects(self):
        self.primary_plan();original=json.loads(json.dumps(self.plan))
        def downgrade_with_new_module(plan):
            plan.pop('PrimaryGuardFixture');del plan['Stages'][4:6]
        mutations=[lambda p:p.update(PrimaryGuardFixture='true'),lambda p:p.update(PrimaryGuardFixture=False),
            lambda p:p.pop('PrimaryGuardFixture'),lambda p:p['Stages'][5].update(ExpectedChecks=35),lambda p:p['Stages'][5].update(ExpectedChecks='36'),
            lambda p:p['Stages'][5].update(ExpectedStdout='IW7_PLAYER_TEMPLATE_PRIMARY_CHECKS=35\n'),
            lambda p:p['Stages'][5].update(ExpectedStdout=['IW7_PLAYER_TEMPLATE_PRIMARY_CHECKS=36\n']),
            lambda p:p.update(PreparedBindings=[]),
            lambda p:p['Stages'][4]['Artifacts'].append('extra.bin'),lambda p:p['Stages'][5]['Arguments'].append('unexpected'),downgrade_with_new_module]
        for i,mutate in enumerate(mutations):
            with self.subTest(case=i):
                self.plan=json.loads(json.dumps(original));mutate(self.plan);result=self.invoke()
                self.assertNotEqual(result.returncode,0);self.assertFalse(Path(self.plan['RunRoot']).exists())

    def definition_plan(self):
        self.primary_plan()
        source=Path(self.plan['PreparedBindings'][0]['Path'])
        source.write_bytes(source.read_bytes()+b'// IW7_PLAYER_PAIR_PROFILE donor=cp_zmb iw7_player_template_cli::pair_selected(args)\n'
            b'// IW7_PLAYER_PAIR_DEFINITIONS donor=cp_zmb iw7_player_template_cli::definitions_selected(args) player_definition_readset::with_pair(\n')
        self.plan['PreparedBindings'][0].update(Bytes=source.stat().st_size,SHA256=hashlib.sha256(source.read_bytes()).hexdigest())
        self.plan.update(PairProfileCLI=True,PairDefinitionsCLI=True)
        self.plan['Stages'][3].update(ExpectedChecks=28,ExpectedStdout='IW7_PLAYER_TEMPLATE_ARGV_CHECKS=28\n')
        self.plan['Stages'][6:6]=[
            dict(Name='definition-compile',Stage='Compile',DeadlineSeconds=120,Image=self.plan['Compiler'],
                 Arguments=['@'+str(self.root/'prepared'/'definition.rsp')],
                 Artifacts=['definition.obj','definition.exe','definition.pdb','compile.pdb','dependencies.json']),
            dict(Name='definition-test',Stage='Probe',DeadlineSeconds=15,
                 Image=str(self.root/'not-created'/'definition-compile'/'definition.exe'),Arguments=[],Artifacts=[],
                 ExpectedChecks=100,ExpectedStdout='IW7_PLAYER_DEFINITION_READSET_CHECKS=100\n')]
        self.plan.update(NativeSourcePin=recipe.support.SOURCE_PIN,CandidateBytes=None,CandidateSHA256=None)
        native=self.root/'unopened-native'/'src'/'zonetool'/'zonetool'/'iw7'/'structs.hpp'
        native_pin=dict(Path=str(native),Bytes=recipe.NATIVE_HEADER[0],SHA256=recipe.NATIVE_HEADER[1])
        self.plan['RetainedInputPins']=[native_pin]
        files=[];self.plan['OwnDirectIncludeCoverage']=[]
        for name in recipe.FIXTURE_FILES:
            target=self.root/'prepared'/name
            target.write_bytes(Path(recipe.HERE/name).read_text().encode())
            binding=dict(Path=str(target),Bytes=target.stat().st_size,SHA256=hashlib.sha256(target.read_bytes()).hexdigest(),IsText=True)
            self.plan['PreparedBindings'].append(binding);files.append(binding)
            self.plan['OwnDirectIncludeCoverage'].append(dict(Path=str(target),Pinned=True))
        for name,text in (('native_definition_fixture_binding.hpp',recipe.binding_header(native)),
                          ('definition.rsp',recipe.definition_response(self.root/'prepared',Path(self.plan['RunRoot'])))):
            target=self.root/'prepared'/name;target.write_bytes(text.encode())
            self.plan['PreparedBindings'].append(dict(Path=str(target),Bytes=target.stat().st_size,SHA256=hashlib.sha256(target.read_bytes()).hexdigest(),IsText=True))
            if name.endswith('.hpp'):self.plan['OwnDirectIncludeCoverage'].append(dict(Path=str(target),Pinned=True))
        self.plan['DefinitionFixture']=dict(Schema='iw7.player-definition-fixture-source/1',Files=files,NativeHeader=native_pin)

    def test_definition_cli_requires_ten_stages_28_argv_and_100_real_source_checks(self):
        self.definition_plan()
        good=json.loads(json.dumps(self.plan));result=self.invoke();self.assertEqual(result.returncode,0,result.stderr)
        report=json.loads(result.stdout);self.assertEqual((report['Stages'],report['ArgvChecksAuthored'],report['DefinitionChecksAuthored']),(10,28,100))
        self.assertTrue(report['DefinitionFixtureSourceVerified']);self.assertTrue(report['ExpectedNoEffects'])
        self.assertIsNone(report['CandidateBytes']);self.assertIsNone(report['CandidateSHA256'])
        for mutate in (lambda p:p.pop('PairDefinitionsCLI'),lambda p:p.update(PairDefinitionsCLI=False),
                       lambda p:p.update(PairDefinitionsCLI=[True]),lambda p:p.pop('PairProfileCLI'),
                       lambda p:p['Stages'][3].update(ExpectedChecks=18),lambda p:p['Stages'][7].update(ExpectedChecks='87'),
                       lambda p:p['Stages'][7].update(ExpectedChecks=86),lambda p:p['Stages'][7].update(ExpectedStdout='different\n'),
                       lambda p:p['Stages'][6]['Artifacts'].append('extra'),lambda p:p.update(PreparedBindings=[]),
                       lambda p:p.pop('DefinitionFixture'),lambda p:p.update(CandidateBytes=22029824),
                       lambda p:p.update(CandidateSHA256='533c'+'0'*60),lambda p:p['DefinitionFixture']['NativeHeader'].update(Bytes='354227')):
            self.plan=json.loads(json.dumps(good));mutate(self.plan)
            self.assertNotEqual(self.invoke().returncode,0)
        self.assertFalse(Path(self.plan['RunRoot']).exists());self.assertFalse(Path(self.plan['Compiler']).exists())
        self.assertFalse(Path(self.plan['DefinitionFixture']['NativeHeader']['Path']).exists())

    def test_definition_metadata_stub_and_injected_response_refused_before_native(self):
        self.definition_plan()
        fixture=Path(self.plan['DefinitionFixture']['Files'][0]['Path']);original=fixture.read_bytes()
        for raw,needle,path in ((b'// stub IW7_PLAYER_DEFINITION_READSET_CHECKS=100\n','metadata stubs refused',fixture),
                (b'/nologo stub.cpp\n','compiler response',self.root/'prepared'/'definition.rsp')):
            before=path.read_bytes();path.write_bytes(raw)
            for group in (self.plan['PreparedBindings'],self.plan['DefinitionFixture']['Files']):
                for binding in group:
                    if binding['Path']==str(path):binding.update(Bytes=len(raw),SHA256=hashlib.sha256(raw).hexdigest())
            result=self.invoke();self.assertNotEqual(result.returncode,0);self.assertIn(needle,result.stderr)
            path.write_bytes(before)
            for group in (self.plan['PreparedBindings'],self.plan['DefinitionFixture']['Files']):
                for binding in group:
                    if binding['Path']==str(path):binding.update(Bytes=len(before),SHA256=hashlib.sha256(before).hexdigest())
        self.assertFalse(Path(self.plan['RunRoot']).exists())

    def test_missing_own_header_coverage_refused(self):
        self.plan['OwnDirectIncludeCoverage'][0]['Pinned']=False
        result=self.invoke();self.assertNotEqual(result.returncode,0)
        self.assertIn('IW7 source coverage',result.stderr)

    def test_output_limit_drift_refused_before_native(self):
        self.plan['OutputLimitBytes'] += 1
        result=self.invoke();self.assertNotEqual(result.returncode,0)
        self.assertIn('deadline/output reserve',result.stderr)

    def test_changed_probe_marker_refused_before_native(self):
        self.plan['Stages'][1]['ExpectedStdout']='checks passed\n'
        result=self.invoke();self.assertNotEqual(result.returncode,0)
        self.assertIn('probe image/marker',result.stderr)

    def test_source_drift_refused_before_import(self):
        Path(self.provider['Path']).write_bytes(b'# changed\n')
        result=self.invoke();self.assertNotEqual(result.returncode,0)
        self.assertIn('Source size differs',result.stderr)

    def test_opaque_source_binding_suffix_refused_before_filesystem_io(self):
        path=self.root/'unopened-candidate.exe'
        self.plan['SourceBindings'].append(dict(Path=str(path),Bytes=1,SHA256='0'*64))
        result=self.invoke();self.assertNotEqual(result.returncode,0)
        self.assertIn('Source/metadata suffix required before filesystem IO',result.stderr)
        self.assertFalse(path.exists());self.assertFalse(Path(self.plan['RunRoot']).exists())

    def test_native_switch_refused_before_types_admission_or_creation(self):
        result=self.invoke(native=True);self.assertNotEqual(result.returncode,0)
        self.assertIn('physical NoExit host',result.stderr)
        self.assertFalse(Path(self.plan['RunRoot']).exists())

    def source_fragment(self, body, *arguments):
        # Execute only the actual bounded reader/finally AST, never the Run body.
        script=self.root/'source-fragment.ps1'
        script.write_text('''param([string]$Runner,[string]$Directory,[int]$FailAt)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Runner,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Source parse failed'}
$reader=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'Read-PlayerSource'},$true)
. ([scriptblock]::Create($reader.Extent.Text))
'''+body,encoding='utf-8')
        return subprocess.run([shutil.which('pwsh'),'-NoLogo','-NoProfile','-File',str(script),
            str(RUNNER),str(self.root),*map(str,arguments)], text=True,capture_output=True,timeout=15)

    def test_verified_source_stream_blocks_replacement_until_disposed(self):
        result=self.source_fragment('''
$path=Join-Path $Directory 'provider.ps1'
$hash=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()
$guards=[Collections.Generic.List[object]]::new()
$null=Read-PlayerSource $path $hash (Get-Item $path).Length $guards
$blocked=$false
try{$writer=[IO.File]::Open($path,'Open','Write','None');$writer.Dispose()}catch{$blocked=$true}
if(!$blocked -or $guards.Count -ne 1){throw 'Verified source guard did not prevent replacement'}
$guards[0].Dispose()
$writer=[IO.File]::Open($path,'Open','Write','None');$writer.Dispose()
Write-Output 'source-guard-causal-pass'
''')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('source-guard-causal-pass',result.stdout)

    def test_deadline_failure_before_and_after_release_keeps_honest_state(self):
        for fail_at in (0,4,7):
            with self.subTest(fail_at=fail_at):
                # Each synthetic finalization has its own new ordinary output.
                result=self.source_fragment('''
$runRoot=Join-Path $Directory ('finalization-'+$FailAt)
[IO.Directory]::CreateDirectory($runRoot)|Out-Null
$plan=[pscustomobject]@{RunRoot=$runRoot;GroupDeadlineSeconds=600;MetadataReserveBytes=1048576;OutputLimitBytes=268435456}
$PlanSHA256='0'*64;$script:T7GroupStarted=0;$script:ClockChecks=0;$script:Releases=0
function Assert-H1Deadline($Started,$Seconds){$script:ClockChecks++;if($FailAt -gt 0 -and $script:ClockChecks -eq $FailAt){throw 'Synthetic original-clock deadline'}}
function Measure-H1Output($Path){[long]$sum=0;foreach($item in Get-ChildItem -LiteralPath $Path -File){$sum+=$item.Length};$sum}
function Exit-IW7ResourceLease($Token){$script:Releases++}
$guards=[Collections.Generic.List[object]]::new();$guards.Add([IO.MemoryStream]::new())
$context=[pscustomobject]@{Closed=$true;Owner=$null;Lease=[pscustomobject]@{Token='synthetic-source-only'};Guards=$guards}
$state=[ordered]@{Status='MeasuredPassed';Host=[ordered]@{SourceOnly=$true};MaxObservedOutputBytes=0L;MeasuredReadback=$false;FinalReadback=$false;LeaseReleased=$false;GuardsDisposed=$false;CanExit=$false;Ready=$false}
$created=$true;$failure=$null
$try=$ast.Find({param($n) $n -is [Management.Automation.Language.TryStatementAst] -and $null -ne $n.Finally -and $n.Finally.Extent.Text.Contains('$state.FinalReadback')},$true)
$text=$try.Finally.Extent.Text
$null=. ([scriptblock]::Create($text.Substring(1,$text.Length-2)))
[ordered]@{Status=$state.Status;CanExit=$state.CanExit;Releases=$script:Releases;Guards=$guards.Count;LeaseHeld=($null -ne $context.Lease);FinalReadback=$state.FinalReadback;Error=$(if($state.Contains('FinalizationError')){$state.FinalizationError}else{''})}|ConvertTo-Json -Compress
''',fail_at)
                self.assertEqual(result.returncode,0,result.stderr)
                report=json.loads(result.stdout)
                if fail_at==0:
                    self.assertEqual((report['Status'],report['CanExit'],report['Releases']),('Passed',True,1),report)
                elif fail_at==4:
                    self.assertEqual((report['Status'],report['CanExit'],report['Releases'],report['Guards'],report['LeaseHeld']),('UnknownRetained',False,0,1,True))
                else:
                    self.assertEqual((report['Status'],report['CanExit'],report['Releases'],report['Guards'],report['LeaseHeld'],report['FinalReadback']),('ClosedFinalizationIncomplete',False,1,0,False,False),report)


    def test_real_finalizer_uses_reserve_for_three_receipts_after_native_63_shape(self):
        for scenario in (0, 1, 2):
            with self.subTest(scenario=scenario):
                result=self.source_fragment(r'''
# Real shared Core functions and real runner finally; no native types/entry.
$core=Join-Path (Split-Path (Split-Path $Runner -Parent) -Parent) 'h1-fixture/H1Native.Core.ps1'
$tokens=$null;$errors=$null
$coreTree=[Management.Automation.Language.Parser]::ParseFile($core,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Shared Core Source parse failed'}
foreach($name in 'Assert-H1Path','Measure-H1Output','Get-H1Clock','Assert-H1Deadline'){
    $definition=$coreTree.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true)
    . ([scriptblock]::Create($definition.Extent.Text))
}
$runRoot=Join-Path $Directory ('owned-shape-'+$FailAt)
[IO.Directory]::CreateDirectory($runRoot)|Out-Null
for($i=0;$i -lt 10;$i++){[IO.Directory]::CreateDirectory((Join-Path $runRoot ('stage-'+$i)))|Out-Null}
for($i=0;$i -lt 53;$i++){[IO.File]::WriteAllText((Join-Path (Join-Path $runRoot ('stage-'+($i%10))) ('owned-'+$i+'.txt')),'x')}
$nativeBytes=Measure-H1Output $runRoot
$oldCapReproduced=$false
if($FailAt -eq 0){
    $first=Join-Path $runRoot 'owned-before.json';$second=Join-Path $runRoot 'owned-closure.json'
    [IO.File]::WriteAllText($first,'{}');$null=Measure-H1Output $runRoot
    [IO.File]::WriteAllText($second,'{}')
    try{$null=Measure-H1Output $runRoot}catch{$oldCapReproduced=$_.Exception.Message -ceq 'Output entry count exceeded 64.'}
    if(!$oldCapReproduced){throw 'Unchanged cap64 did not reproduce original metadata counterexample'}
    Remove-Item -LiteralPath $first,$second
}
$plan=[pscustomobject]@{RunRoot=$runRoot;GroupDeadlineSeconds=600;MetadataReserveBytes=1MB;OutputLimitBytes=256MB}
$PlanSHA256='0'*64;$script:T7GroupStarted=Get-H1Clock;$script:Releases=0
function Exit-IW7ResourceLease($Token){
    if($Token -cne 'owned-source-only'){throw 'Foreign lease reached an isolated Source fixture'}
    if(!(Test-Path -LiteralPath (Join-Path $runRoot 'measured-before-release.json')) -or
       !(Test-Path -LiteralPath (Join-Path $runRoot 'closure-before-release.json')) -or
       (Test-Path -LiteralPath (Join-Path $runRoot 'final-closure.json'))){throw 'Actual Source publication/release order differs'}
    $script:Releases++
}
$guards=[Collections.Generic.List[object]]::new()
$sourceGuard=[IO.FileStream]::new((Join-Path (Join-Path $runRoot 'stage-0') 'owned-0.txt'),'Open','Read','Read')
$sourceHandle=$sourceGuard.SafeFileHandle;$guards.Add($sourceGuard)
$context=[pscustomobject]@{Closed=$true;Owner=$null;Lease=[pscustomobject]@{Token='owned-source-only'};Guards=$guards}
$state=[ordered]@{Status='MeasuredPassed';Host=[ordered]@{SourceOnly=$true};MaxObservedOutputBytes=0L;
    MeasuredReadback=$false;FinalReadback=$false;LeaseReleased=$false;GuardsDisposed=$false;CanExit=$false;Ready=$false}
if($FailAt -eq 1){$state['OwnedPadding']='x'*(1MB)}
if($FailAt -eq 2){$plan.OutputLimitBytes=$plan.MetadataReserveBytes+$nativeBytes-1}
$created=$true;$failure=$null
try{
    $try=$ast.Find({param($n) $n -is [Management.Automation.Language.TryStatementAst] -and $null -ne $n.Finally -and $n.Finally.Extent.Text.Contains('$state.FinalReadback')},$true)
    $text=$try.Finally.Extent.Text
    $null=. ([scriptblock]::Create($text.Substring(1,$text.Length-2)))
    $receipts=@('measured-before-release.json','closure-before-release.json','final-closure.json')
    $published=@($receipts|Where-Object {Test-Path -LiteralPath (Join-Path $runRoot $_)})
    $nativeCapStillStrict=$false
    if($FailAt -eq 0){try{$null=Measure-H1Output $runRoot}catch{$nativeCapStillStrict=$_.Exception.Message -ceq 'Output entry count exceeded 64.'}}
    [ordered]@{Status=$state.Status;CanExit=$state.CanExit;Releases=$script:Releases;Guards=$guards.Count;
        OriginalGuardClosed=$sourceHandle.IsClosed;LeaseHeld=($null -ne $context.Lease);FinalReadback=$state.FinalReadback;
        PublishedReceipts=$published.Count;OldCapReproduced=$oldCapReproduced;NativeCapStillStrict=$nativeCapStillStrict;
        NativeTypeLoaded=[bool]('IW7.AnimationProbe.NativeJob' -as [type]);Error=$(if($state.Contains('FinalizationError')){$state.FinalizationError}else{''})}|ConvertTo-Json -Compress
}finally{foreach($guard in $guards){$guard.Dispose()};$guards.Clear()}
''',scenario)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                report=json.loads(result.stdout)
                self.assertFalse(report['NativeTypeLoaded'])
                if scenario==0:
                    self.assertEqual((report['Status'],report['CanExit'],report['Releases'],report['Guards'],report['LeaseHeld'],report['FinalReadback'],report['PublishedReceipts']),
                        ('Passed',True,1,0,False,True,3),report)
                    self.assertTrue(report['OriginalGuardClosed'])
                    self.assertTrue(report['OldCapReproduced'])
                    self.assertTrue(report['NativeCapStillStrict'])
                else:
                    self.assertEqual((report['Status'],report['CanExit'],report['Releases'],report['Guards'],report['LeaseHeld'],report['FinalReadback'],report['PublishedReceipts']),
                        ('UnknownRetained',False,0,1,True,False,0),report)
                    self.assertFalse(report['OriginalGuardClosed'])
                    self.assertIn('before',report['Error'])


    def authored_plan(self):
        """Synthetic UNQUALIFIED metadata. Providers throw if imported; opaque files do not exist."""
        prepared=self.root/'authored-prepared';prepared.mkdir()
        def binding(name, text, parent=False):
            path=(self.root if parent else prepared)/name
            path.parent.mkdir(parents=True, exist_ok=True)
            raw=text.encode();path.write_bytes(raw)
            return dict(Path=str(path),Bytes=len(raw),SHA256=hashlib.sha256(raw).hexdigest(),IsText=True)
        def metadata(name, value):
            return binding(name, json.dumps(value)+'\n')
        head='f'*40
        source=[binding('invoke-cohort.local.ps1',"throw 'Source-only synthetic capsule'\n",True)]
        postflight={role:binding(role.lower()+'.ps1',"throw 'Source-only postflight'\n",True)
                    for role in ('Writer','Caller','Bootstrap')}
        source.extend(postflight.values())
        parents=[binding('provider-'+str(i)+'.ps1',"throw 'Provider must NEVER import in this Source test'\n",True)
                 for i in range(11)]
        providers=dict(zip(('Core','CompilerCore','ObserverSource','CompilerPolicySource','Scheduler','Profile'),
                           (p['Path'] for p in parents)))
        unopened=self.root/'unopened-opaque'
        raw=dict(Path=str(unopened/'json.hpp'),Bytes=1019792,
            SHA256='33499c641336b51fdfe4d71374b7f2de30cbcd4cb63d0c56f306e1f90ae7d724',
            InputRole='CompilerInclude',DeclaredRoleRoot=str(unopened),ParentPlanSHA256='a'*64,AdmissionRequired=True)
        roles=metadata('input-roles.json',dict(Schema='iw7.authored-core-compiler-input-roles/1',
            OpaqueFilesQueried=False,InheritedQualification=False,AdmissionBeforeOpaqueIO=True,Selected=[raw]))
        lfhash='53855e4a20d7bc92d9624bf0d83fba8e22d0d9de83f9480bd4895651602fa8cc'
        include=metadata('include-closure.json',dict(OpaqueFilesQueried=False,ActualCompilerDependencySubsetStillRequired=True,
            NoPostcompileGuardAdds=True,JSONDiagnostics=1,JSONSourceExpectedLFHash=lfhash,
            DirectIncludeDeclarations=[dict(Declaration=raw)]))
        fixture=metadata('fixture-closure.json',dict(Schema='iw7.authored-fixture-prepared-source-closure/1',
            SourceHead=head,SourceOnly=True,OpaqueFilesQueried=False,OldFourFileDeclarationSetRefuses=True,
            ActualCompilerDependencySubsetStillRequired=True,Ready=False,CanonicalSupportFiles=['source-only']*6,
            GeneratedHeaders=[{},{}],VisitedSourceBindings=[]))
        provenance=metadata('source-provenance.json',dict(SourceOnly=True))
        snapshot=metadata('provider-snapshot.json',dict(SourceOnly=True))
        pins=[roles,include,fixture,provenance,snapshot]
        names=('weapon-core','attachment-core','fixture-compile','fixture-link','fixture-test','weapondef','weaponattachment','filesystem')
        runtime=self.root/'authored-runtime-absent';compiler=unopened/'cl.exe'
        cases=['source_only_'+str(i) for i in range(8)]
        marker=''.join('PASS '+case+'\n' for case in cases)+'IW7_AUTHORED_PAIR_REAL_CORE_FIXTURE=8\n'
        stages=[]
        for i,name in enumerate(names):
            if i==4:
                stages.append(dict(Name=name,Stage='Probe',Image=str(runtime/'fixture-link'/'fixture.exe'),
                    Arguments=[],Artifacts=[],DeadlineSeconds=15,ExpectedChecks=8,ExpectedStdout=marker))
            else:
                artifacts=['fixture.exe','fixture.pdb'] if i==3 else [
                    'fixture.obj' if i==2 else name+'.obj','compile.pdb','dependencies.json']
                pins.append(binding(name+'.rsp','/nologo /W4 /WX /c source-only.cpp\n'))
                stages.append(dict(Name=name,Stage='Link' if i==3 else 'Compile',
                    Image=str(unopened/'link.exe') if i==3 else str(compiler),
                    Arguments=['@'+str(prepared/(name+'.rsp'))],Artifacts=artifacts,DeadlineSeconds=120))
        self.plan=dict(Schema='iw7.authored-pair-core-cpp-source/1',SourceHead=head,
            NativeSourcePin='fab935826c898806855376662a8a03317b3ad8f1',Ready=False,CandidateExecuted=False,
            ChecksExecuted=False,TUsCompiled=False,CoresLinked=False,ParentCPPQualificationInherited=False,
            FatalAllocatorClosure=False,ActualPairParseActivated=False,NoHistoricalObjects=True,NoFullCLILink=True,
            RealOSAllocatorRequested=True,ChecksAuthored=8,GroupDeadlineSeconds=600,OutputLimitBytes=268435456,
            MetadataReserveBytes=1048576,PhysicalReservationBytes=4294967296,CommitReservationBytes=6442450944,
            LogicalFixtureArenaBytes=6208,MaximumSimultaneousFixtureArenas=1,RequireActualDependenciesWithinGuardedSet=True,
            FixtureCompileProfile='RealCoreJSONDiagnostics1RealArena',RunRoot=str(runtime),PreparedRoot=str(prepared),
            Compiler=str(compiler),SourceBindings=source,PreparedBindings=pins,ParentBindings=parents,Providers=providers,
            RunnerBinding=dict(Path=str(RUNNER),Bytes=RUNNER.stat().st_size,SHA256=hashlib.sha256(RUNNER.read_bytes()).hexdigest(),IsText=True),
            Stages=stages,FixtureCases=cases,RetainedInputPins=[raw],CompilerInputRoleManifest=roles,DirectIncludeClosure=include,
            NativeSourceProvenance=provenance,CurrentProviderSourceSnapshot=snapshot,FixtureSourceClosure=fixture,
            PostflightSources=postflight,CheckedMemoryOverlay=dict(StagedBytes=11393,
                StagedSHA256='8835b6da207f4fb872e199a5f6b86f0d98a8714a1d6a11421ac7e8d19ca766d4',ActualActivation=False),
            JSONBinding=dict(RawDeclaration=raw,Diagnostics=1,IdentityVerified=False,
                JSONRevision='484483acad6d562306efc9b3c6d413404f1b1f8a',SourceExpectedLFHash=lfhash),
            GeneratedLinkInputs=[str(runtime/'weapon-core'/'weapon-core.obj'),
                str(runtime/'attachment-core'/'attachment-core.obj'),str(runtime/'fixture-compile'/'fixture.obj')])

    def test_authored_default_stays_source_only_and_checks_all_eleven_providers(self):
        self.authored_plan()
        result=self.invoke();self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        report=json.loads(result.stdout)
        self.assertEqual((report['Stages'],report['ProviderSources'],report['FixtureGroupsAuthored']),(8,11,8))
        for key in ('NativeTypesLoaded','NativeInputsHashed','RunRootCreated','LeaseAcquired','CPPExecuted','Ready'):
            self.assertFalse(report[key],key)
        self.assertFalse((self.root/'unopened-opaque').exists())
        self.assertFalse(Path(self.plan['RunRoot']).exists())
        self.plan['ParentBindings'].pop()
        result=self.invoke();self.assertNotEqual(result.returncode,0)
        self.assertIn('All eleven',result.stderr)

    def test_authored_source_and_json_drift_refuse_before_actual_import(self):
        self.authored_plan()
        self.plan['JSONBinding']['SourceExpectedLFHash']='0'*64
        result=self.invoke();self.assertNotEqual(result.returncode,0)
        self.assertIn('JSON Source/opaque binding',result.stderr)
        self.plan['JSONBinding']['SourceExpectedLFHash']='53855e4a20d7bc92d9624bf0d83fba8e22d0d9de83f9480bd4895651602fa8cc'
        Path(self.plan['ParentBindings'][-1]['Path']).write_text('# changed transitive Source')
        result=self.invoke();self.assertNotEqual(result.returncode,0)
        self.assertIn('Source size differs',result.stderr)
        self.assertFalse((self.root/'unopened-opaque').exists())

    def test_authored_actual_switch_requires_original_physical_capsule_before_import(self):
        self.authored_plan()
        result=self.invoke(native=True);self.assertNotEqual(result.returncode,0)
        self.assertIn('physical NoExit/dot capsule witness',result.stderr)
        self.assertFalse((self.root/'unopened-opaque').exists())
        self.assertFalse(Path(self.plan['RunRoot']).exists())

    def test_authored_real_finalizer_publication_refusal_does_not_own_teardown(self):
        for scenario in range(7):
            with self.subTest(scenario=scenario):
                result = self.source_fragment(r'''
$core=Join-Path (Split-Path (Split-Path $Runner -Parent) -Parent) 'h1-fixture/H1Native.Core.ps1'
. $core
foreach($name in @('Get-PlayerAuthoredSafetyClock','Open-NeutralPublication','Write-NeutralPublication',
    'Read-NeutralPublication','New-NeutralPublication','Save-PlayerAuthoredGuardReferences',
    'Complete-NeutralPublication','Complete-PlayerAuthoredFinalization')){
    $definition=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true)
    if(!$definition){throw ('Canonical finalizer function absent: '+$name)}
    . ([scriptblock]::Create($definition.Extent.Text))
}
$runRoot=Join-Path $Directory ('authored-finalizer-'+$FailAt)
[IO.Directory]::CreateDirectory($runRoot)|Out-Null
$names=@('weapon-core','attachment-core','fixture-compile','fixture-link','fixture-test','weapondef','weaponattachment','filesystem')
$stages=@(for($i=0;$i -lt 8;$i++){
    [pscustomobject]@{Name=$names[$i];Stage=$(if($i -eq 4){'Probe'}elseif($i -eq 3){'Link'}else{'Compile'});
        Artifacts=$(if($i -eq 4){@()}elseif($i -eq 3){@('fixture.exe','fixture.pdb')}
            else{@($(if($i -eq 2){'fixture.obj'}else{$names[$i]+'.obj'}),'compile.pdb','dependencies.json')})}
})
$plan=[pscustomobject]@{RunRoot=$runRoot;GroupDeadlineSeconds=600;MetadataReserveBytes=1MB;OutputLimitBytes=256MB;
    AuthoredOutputBudget=(New-H1AuthoredOutputBudget $runRoot $stages)}
$script:SourceClock=if($FailAt -eq 3){600001}else{1000}
$script:OriginalStarted=0;$script:T7GroupStarted=0;$script:Releases=0;$script:Measurements=0
function Get-H1Clock {$script:SourceClock}
$script:ActualMeasure=(Get-Command Measure-H1Output -CommandType Function).ScriptBlock
function Measure-H1Output($Root,$Budget){$script:Measurements++;& $script:ActualMeasure $Root $Budget}
$owner=[pscustomobject]@{Closed=($FailAt -notin @(4,6));ExitCode=0;Stops=0;StopFails=($FailAt -eq 4)}
$owner|Add-Member ScriptMethod StopAndConfirm {
    param($Timeout)
    $this.Stops++
    if($this.StopFails){throw 'Owned Source closure unknown'}
    $this.Closed=$true
}
$guards=[Collections.Generic.List[object]]::new()
$inputPath=Join-Path $Directory ('authored-source-'+$FailAt+'.ps1')
[IO.File]::WriteAllText($inputPath,'# owned Source input')
$inputGuard=[IO.FileStream]::new($inputPath,'Open','Read','Read')
$inputSFH=$inputGuard.SafeFileHandle;$guards.Add($inputGuard)
$originalLease=[pscustomobject]@{Token='source-causal-owned-lease'}
$context=[pscustomobject]@{Owner=$owner;Closed=$owner.Closed;Lease=$originalLease;Guards=$guards}
$originalContext=$context;$originalOwner=$owner;$originalGuards=$guards
function Exit-IW7ResourceLease($Token){
    if($Token -cne 'source-causal-owned-lease' -or ![object]::ReferenceEquals($context.Lease,$originalLease) -or
       ![object]::ReferenceEquals($context.Owner,$originalOwner) -or !$context.Closed -or !$owner.Closed){
        throw 'Uncorrelated/unclosed original Source owner reached release'
    }
    $script:Releases++
    if($FailAt -eq 5){throw 'Owned Source release refused'}
}
$state=[ordered]@{Schema='source-causal';PlanSHA256=('0'*64);Status='Failed';Error='Original primary64 causal';
    Host=[ordered]@{SourceOnly=$true};MaxObservedOutputBytes=0L;NativeInputsReverified=$false;MeasuredReadback=$false;
    FinalReadback=$false;LeaseReleased=$false;GuardsDisposed=$false;CanExit=$false;Ready=$false}
if($FailAt -in @(0,6)){function New-NeutralPublication {throw 'Owned first-publication refusal'}}
if($FailAt -eq 1){function Write-NeutralPublication($Entry){
    $Entry.Stream.Write($Entry.Bytes,0,1);$Entry.Stream.Flush($true)
    throw 'Owned mid-write refusal'
}}
if($FailAt -eq 2){function Read-NeutralPublication {throw 'Owned readback refusal'}}
try{
    Complete-PlayerAuthoredFinalization $plan $state $context $guards $script:OriginalStarted $null $true
    $refsPresent=$null -ne $context.PSObject.Properties['FinalGuardReferences']
    $sameRefs=if($refsPresent){[object]::ReferenceEquals($context.FinalGuardReferences[0],$inputGuard) -and
        [object]::ReferenceEquals($context.FinalGuardSafeHandles[0],$inputSFH)}else{
        $guards.Count -gt 0 -and [object]::ReferenceEquals($guards[0],$inputGuard)}
    $allClosed=$refsPresent
    if($refsPresent){for($i=0;$i -lt $context.FinalGuardReferences.Count;$i++){
        if(!$context.FinalGuardSafeHandles[$i].IsClosed -or $context.FinalGuardReferences[$i].CanRead -or
           $context.FinalGuardReferences[$i].CanWrite -or $context.FinalGuardReferences[$i].CanSeek){$allClosed=$false}
    }}
    $partial=if($context.PSObject.Properties['PublicationEntries']){$context.PublicationEntries.Count}else{0}
    [ordered]@{Status=$state.Status;CanExit=$state.CanExit;Primary=$state.Error;Releases=$script:Releases;Stops=$owner.Stops;
        Measurements=$script:Measurements;SameContext=[object]::ReferenceEquals($context,$originalContext);
        SameOwner=[object]::ReferenceEquals($context.Owner,$originalOwner);SameList=[object]::ReferenceEquals($guards,$originalGuards);
        SameIndividualRefs=$sameRefs;InputSFHClosed=$inputSFH.IsClosed;AllSavedRefsClosed=$allClosed;GuardsRemaining=$guards.Count;
        LeaseHeld=($null -ne $context.Lease);PartialPublications=$partial;MeasuredReadback=$state.MeasuredReadback;
        FinalReadback=$state.FinalReadback;NativeInputsReverified=$state.NativeInputsReverified;Ready=$state.Ready;
        OriginalClockUnchanged=($script:OriginalStarted -eq 0 -and $script:T7GroupStarted -eq 0);
        NoExitRequired=$context.SafetyClosure.NoExitRequired;ResourcesClosed=$context.SafetyClosure.ResourcesClosed;
        NativeTypeLoaded=[bool]('IW7.AnimationProbe.NativeJob' -as [type])}|ConvertTo-Json -Depth 5 -Compress
}finally{
    # Only test-owned Source handles; fake lease has no external registry.
    foreach($guard in $guards){$guard.Dispose()}
    if($context.PSObject.Properties['PublicationEntries']){foreach($entry in $context.PublicationEntries){if($entry.Stream){$entry.Stream.Dispose()}}}
    [AppDomain]::CurrentDomain.SetData('IW7.H1.Quarantine.source-causal-owned-lease',$null)
}
''', scenario)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                report = json.loads(result.stdout)
                self.assertEqual(report['Primary'], 'Original primary64 causal')
                for key in ('SameContext', 'SameOwner', 'SameList', 'SameIndividualRefs',
                            'OriginalClockUnchanged', 'NoExitRequired'):
                    self.assertTrue(report[key], (key, report))
                for key in ('CanExit', 'FinalReadback', 'NativeInputsReverified', 'Ready', 'NativeTypeLoaded'):
                    self.assertFalse(report[key], (key, report))
                self.assertEqual(report['Stops'], 1 if scenario in (4, 6) else 0, report)
                if scenario in (4, 5):
                    self.assertEqual(report['Releases'], 0 if scenario == 4 else 1, report)
                    self.assertTrue(report['LeaseHeld'], report)
                    self.assertFalse(report['InputSFHClosed'], report)
                    self.assertFalse(report['ResourcesClosed'], report)
                else:
                    self.assertEqual(report['Releases'], 1, report)
                    self.assertFalse(report['LeaseHeld'], report)
                    self.assertEqual(report['GuardsRemaining'], 0, report)
                    self.assertTrue(report['InputSFHClosed'], report)
                    self.assertTrue(report['AllSavedRefsClosed'], report)
                    self.assertTrue(report['ResourcesClosed'], report)
                if scenario == 3:
                    self.assertEqual((report['Measurements'], report['PartialPublications']), (0, 0), report)
                if scenario in (1, 2, 5):
                    self.assertEqual(report['PartialPublications'], 3, report)
                self.assertEqual(report['MeasuredReadback'], scenario == 5, report)


if __name__=='__main__': unittest.main()

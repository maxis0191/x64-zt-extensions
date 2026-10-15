"""Pure source/metadata preflight and before-native refusal checks. No CPP."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

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
        path=self.root/'plan.json';raw=(json.dumps(self.plan)+'\n').encode();path.write_bytes(raw)
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
$state=[ordered]@{Status='MeasuredPassed';Host=[ordered]@{SourceOnly=$true};MeasuredReadback=$false;FinalReadback=$false;LeaseReleased=$false;GuardsDisposed=$false;CanExit=$false;Ready=$false}
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


if __name__=='__main__': unittest.main()

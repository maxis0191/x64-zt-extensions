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
        self.assertIn('Fixed six-stage',result.stderr)

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


if __name__=='__main__': unittest.main()

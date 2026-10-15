"""Pure incoming plan data; no factory, process, lease or opaque read."""
import copy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import test_registration_image_probe as registration
import prepare_incoming_image_probe as probe


class IncomingPlanTests(unittest.TestCase):
    def fixture(self):
        ref, controllers, build, receipt, _, metadata, run = registration.RegistrationPlanTests().fixture()
        build['pin'].update(Bytes=probe.BUILD[0], SHA256=probe.BUILD[1])
        receipt['pin'].update(Bytes=probe.RECEIPT[0], SHA256=probe.RECEIPT[1])
        receipt['data']['Stages'][-1]['Artifacts'][0].update(Bytes=probe.CANDIDATE[0], SHA256=probe.CANDIDATE[1])
        metadata['Bytes'] = probe.CANDIDATE[0]
        controllers[-1]['Path'] = 'C:/authored/incoming-profile.ps1'
        for name in ('IncomingWiring','IncomingContract','IncomingMembers','IncomingModule','IncomingEntry','IncomingFixture','IncomingCapture','IncomingObserver','IncomingBaselineFixture'):
            build['data']['BuildProfile'][name] = registration.pin('C:/authored/'+name+'.json')
        marker = dict(ReviewedPrerequisiteSource=probe.REVIEWED_SOURCE, CompiledExtensionSource=probe.COMPILED_SOURCE)
        for name, (size, sha) in probe.TEXT_PINS.items():
            marker[name] = dict(Path='C:/authored/'+name+'.json', Bytes=size, SHA256=sha)
        build['data']['BuildProfile']['IncomingContract'] = copy.deepcopy(marker['Contract'])
        return ref, controllers, build, receipt, marker, metadata, run

    def test_reduction_preserves_collection_without_file_queries(self):
        args = self.fixture(); before = copy.deepcopy(args[0])
        with patch.object(Path, 'open', side_effect=AssertionError('open')), patch.object(Path, 'stat', side_effect=AssertionError('stat')):
            plan = probe.derive(*args)
        self.assertEqual(args[0], before)
        self.assertEqual((len(plan['Bindings']), sum(p['IsText'] for p in plan['Bindings']), len(plan['InputMetadata'])), (106,78,27))
        self.assertEqual(plan['Bootstraps'], before['Bootstraps'])
        self.assertEqual(plan['SharedQualification'], before['SharedQualification'])
        self.assertEqual(plan['Arguments'], ['-t7-iw7-incoming-image-header-v1','mp_freerun_04','p7_fre_platform_cap_02','0'])
        self.assertEqual((plan['ReportLimitBytes'],plan['TraceStderrLimitBytes']), (32768,16384))
        self.assertEqual((plan['CandidateBytes'],plan['CandidateSHA256']), probe.CANDIDATE)
        self.assertFalse(set(probe.EXPORT_FIELDS) & set(plan))
        self.assertEqual(sum(p['Path'] == args[4]['Contract']['Path'] for p in plan['Bindings']), 1)
        self.assertFalse(any('provider.xpak' in p['Path'] for p in plan['Bindings']))

    def test_wrong_tuple_source_alias_or_inventory_refuses(self):
        for case in ('build','receipt','candidate','link','source','reviewed','alias','duplicate','inventory'):
            args = list(self.fixture())
            if case == 'build': args[2]['pin']['SHA256'] = 'old'
            elif case == 'receipt': args[3]['pin']['SHA256'] = 'old'
            elif case == 'candidate': args[5]['Bytes'] = 22024704
            elif case == 'link': args[3]['data']['Stages'][-1]['Artifacts'][0]['SHA256'] = 'eeeca'
            elif case == 'source': args[4]['CompiledExtensionSource'] = probe.REVIEWED_SOURCE
            elif case == 'reviewed': args[4]['ReviewedPrerequisiteSource'] = probe.COMPILED_SOURCE
            elif case == 'alias': args[4]['Contract']['Path'] = 'C:/authored/other.json'
            elif case == 'duplicate': args[1][0]['Path'] = args[4]['FreshWitness']['Path']
            else: args[0]['Bootstraps'].pop()
            with self.subTest(case=case), patch.object(Path,'open',side_effect=AssertionError('open')), self.assertRaises(ValueError): probe.derive(*args)

    def test_exact_typed_text_pins(self):
        for name in probe.TEXT_PINS:
            for field, value in (('Bytes','1'),('Bytes',[1]),('SHA256','old'),('SHA256',['old'])):
                args = list(self.fixture()); args[4][name][field] = value
                with self.subTest(name=name,field=field), self.assertRaises(ValueError): probe.derive(*args)

    def test_wrong_fixture_size_refuses_before_open(self):
        path = Path.cwd()/'authored-never-created'/'stdout.log'
        with patch.object(Path,'is_symlink',return_value=False), patch.object(Path,'is_junction',return_value=False), \
             patch.object(Path,'stat',return_value=SimpleNamespace(st_size=72)), patch.object(Path,'open',side_effect=AssertionError('open')):
            with self.assertRaises(ValueError): probe.read_source_text(path,probe.FIXTURE)

    def test_constants_match_powershell_receiver(self):
        text = (Path(__file__).parent/'T7IncomingImage.Profile.ps1').read_text(encoding='utf-8')
        for size, sha in (probe.CANDIDATE,probe.BUILD,probe.RECEIPT,*probe.TEXT_PINS.values()):
            self.assertIn(str(size),text); self.assertIn(sha,text)
        self.assertIn(probe.REVIEWED_SOURCE,text); self.assertIn(probe.COMPILED_SOURCE,text)


if __name__ == '__main__':
    unittest.main()

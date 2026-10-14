"""Authored F2 plan reduction; no factory, process, lease or opaque read."""
import copy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import test_material_parts_probe as parts
import prepare_image_provenance_probe as probe
pin = parts.pin


class ProvenancePlanTests(unittest.TestCase):
    def fixture(self):
        reference, controllers, build, _, _, metadata, run = parts.PartsPlanTests().fixture()
        build['pin'].update(Bytes=probe.BUILD[0], SHA256=probe.BUILD[1])
        build['data']['BuildProfile']['PreparedCLI'] = pin('C:\\authored\\prepared-cli.cpp')
        metadata['Bytes'] = probe.CANDIDATE[0]
        stages = [dict(Name=n, Artifacts=[]) for n in
                  ('metadata-fixture-compile', 'metadata-fixture-test', 'main', 'zonetool11', 'link')]
        stages[2]['Artifacts'] = [pin('C:\\authored\\main\\dependencies.json')]
        stages[-1]['Artifacts'] = [dict(Path=metadata['Path'], Bytes=probe.CANDIDATE[0], SHA256=probe.CANDIDATE[1])]
        receipt = dict(pin=dict(pin('C:\\authored\\receipt.json'), Bytes=probe.RECEIPT[0], SHA256=probe.RECEIPT[1]),
                       data=dict(Stages=stages))
        marker = {n: pin('C:\\authored\\'+n+'.json') for n in
                  ('SourceManifest', 'HostWitness', 'ClosureWitness', 'FixtureStdout')}
        return reference, controllers, build, receipt, marker, metadata, run

    def test_reduction_retains_collection_and_exact_d_tuple_without_open(self):
        args = self.fixture(); before = copy.deepcopy(args[0])
        with patch.object(Path, 'open', side_effect=AssertionError('file opened')):
            result = probe.derive(*args)
        self.assertEqual(args[0], before)
        self.assertEqual((len(result['Bindings']), sum(p['IsText'] for p in result['Bindings']),
                          len(result['InputMetadata'])), (88, 60, 27))
        self.assertEqual(result['Bootstraps'], before['Bootstraps'])
        self.assertEqual(result['SharedQualification'], before['SharedQualification'])
        self.assertEqual(result['InputMetadata'][1:], before['InputMetadata'][1:27])
        self.assertEqual(result['Arguments'], ['-t7-iw7-image-provenance-v1', 'mp_freerun_04', 'p7_fre_platform_cap_02', '0'])
        self.assertEqual((result['CandidateBytes'], result['CandidateSHA256']), probe.CANDIDATE)
        self.assertFalse(set(probe.EXPORT_FIELDS) & set(result))
        self.assertFalse(any('provider.xpak' in p['Path'] or 'request.json' in p['Path'] for p in result['Bindings']))

    def test_wrong_cohort_link_inventory_and_duplicate_text_refuse(self):
        for case in ('recipe', 'receipt', 'link', 'candidate', 'inventory', 'duplicate'):
            args = list(self.fixture())
            if case == 'recipe': args[2]['pin']['SHA256'] = 'old'
            elif case == 'receipt': args[3]['pin']['SHA256'] = 'old'
            elif case == 'link': args[3]['data']['Stages'][-1]['Artifacts'][0]['SHA256'] = 'old'
            elif case == 'candidate': args[5]['Bytes'] = 21963264
            elif case == 'inventory': args[0]['Bootstraps'].pop()
            else: args[1][0]['Path'] = args[4]['SourceManifest']['Path']
            with self.subTest(case=case), self.assertRaises(ValueError): probe.derive(*args)

    def test_fixture_log_wrong_size_refuses_before_open(self):
        target = Path.cwd()/'authored-never-created'/'stdout.log'
        with patch.object(Path, 'is_symlink', return_value=False), patch.object(Path, 'is_junction', return_value=False), \
             patch.object(Path, 'stat', return_value=SimpleNamespace(st_size=130)), \
             patch.object(Path, 'open', side_effect=AssertionError('content opened')):
            with self.assertRaises(ValueError): probe.read_source_text(target, probe.FIXTURE)

    def test_fresh_main_snapshot_replaces_historical_generation(self):
        plan = probe.derive(*self.fixture())
        identity = dict(PID=4321, CreatedUtc='2026-10-14T21:45:00Z', Image='C:\\authored\\main.exe')
        snapshot = dict(Schema='iw7.t7-preservation-metadata/1', MainBaseline='Running',
                        PreservedMain=identity, PreservedProcesses=[identity])
        with patch.object(Path, 'open', side_effect=AssertionError('file opened')):
            probe.apply_preservation(plan, snapshot)
        self.assertEqual(plan['PreservedMain'], identity)
        self.assertEqual(plan['MainBaseline'], 'Running')
        snapshot['PreservedMain']['PID'] = 99
        self.assertEqual(plan['PreservedMain']['PID'], 4321)
        snapshot['MainBaseline'] = 'Unknown'
        with self.assertRaises(ValueError): probe.apply_preservation(plan, snapshot)


if __name__ == '__main__':
    unittest.main()

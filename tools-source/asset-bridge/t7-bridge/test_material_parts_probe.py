"""Authored plan reduction, without native invocation or stock access."""
import copy
from pathlib import Path
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import prepare_material_parts_probe as probe

def pin(path):return dict(Path=path,Bytes=1,SHA256='a'*64)

class PartsPlanTests(unittest.TestCase):
    def test_declared_opaque_suffix_refuses_before_any_open(self):
        for suffix in ('.exe','.pdb','.dll','.ff','.xpak','.tlog'):
            target=Path.cwd()/('authored-never-created'+suffix)
            with self.subTest(suffix=suffix),patch.object(Path,'open',side_effect=AssertionError('content opened')):
                with self.assertRaisesRegex(ValueError,'extension'):probe.read_text_pin(target)

    def test_oversize_and_wrong_expected_stat_refuse_before_open(self):
        target=Path.cwd()/'authored-never-created.json'
        for size,expected in ((1024*1024+1,None),(17,(18,'a'*64))):
            with self.subTest(size=size),patch.object(Path,'is_symlink',return_value=False),patch.object(Path,'is_junction',return_value=False),\
                    patch.object(Path,'stat',return_value=SimpleNamespace(st_size=size)),\
                    patch.object(Path,'open',side_effect=AssertionError('content opened')):
                with self.assertRaises(ValueError):probe.read_text_pin(target,expected)

    def fixture(self):
        base='C:\\authored\\'
        boots=[dict(pin(base+f'zone\\boot{i}.ff'),QualificationScript=pin(base+f'script{i%12}.ps1'),
                    QualificationReceipt=pin(base+f'receipt{i}.json')) for i in range(23)]
        opaque=[dict(pin(base+name),IsText=False) for name in ('old.exe','engine.exe','steam.dll','job.dll','pwsh.exe')]
        opaque += [dict(pin(b['Path']),IsText=False) for b in boots]
        texts={b[k]['Path']:b[k] for b in boots for k in ('QualificationScript','QualificationReceipt')}
        shared=dict(Script=boots[0]['QualificationScript'],Plan=pin(base+'shared-plan'),Receipt=pin(base+'shared-receipt'))
        texts.update((p['Path'],p) for p in shared.values())
        names=['old.exe','engine.exe','steam.dll','zone.ff']+[f'zone\\boot{i}.ff' for i in range(23)]+['provider.xpak','request.json']
        reference=dict(Operation='ResidentExportV1',CandidateProfile='t7-catalog-message-publication',
            SelectedStreamedRenderOnlyV2=dict(Schema='iw7.t7-selected-streamed-render-only-plan/2'),
            CandidateSource=base+'old.exe',EngineSource=base+'engine.exe',SteamSource=base+'steam.dll',
            Zone=pin(base+'zone.ff'),Bootstraps=boots,SharedQualification=shared,
            InputMetadata=[dict(Path=base+n,Bytes=1) for n in names],
            Bindings=opaque+[dict(p,IsText=True) for p in texts.values()],
            SelectedXpakProvider=dict(Metadata=pin(base+'provider.xpak')),ExportRequestFile=pin(base+'request.json'))
        controllers=[pin(base+'receiver\\'+str(i)) for i in range(10)]
        build=dict(pin=pin(base+'build-plan'),data=dict(BuildProfile={n:pin(base+n) for n in
            ('Wiring','PreparedMain','BaseBuildPlan','BaseBuildReceipt','LinkResponse')}))
        receipt=dict(pin=pin(base+'build-receipt'),data=dict(Stages=[dict(Artifacts=[pin(base+'main\\dependencies.json')])]))
        marker={n:pin(base+'marker\\'+n) for n in probe.MARKER_PINS}
        metadata=dict(Path=base+'new.exe',Bytes=probe.CANDIDATE_PIN[0],Attributes='Archive',LastWriteUtc='authored')
        return reference,controllers,build,receipt,marker,metadata,Path('C:/authored/runtime/t7-material-parts-a')

    def test_finite_reduction_keeps_all_stock_and_removes_provider_and_export(self):
        args=self.fixture();before=copy.deepcopy(args[0]);result=probe.derive(*args)
        self.assertEqual(args[0],before)
        self.assertEqual((len(result['Bindings']),sum(p['IsText'] for p in result['Bindings']),len(result['InputMetadata'])),(89,61,27))
        self.assertEqual(result['Bootstraps'],before['Bootstraps'])
        self.assertEqual(result['SharedQualification'],before['SharedQualification'])
        self.assertEqual(result['InputMetadata'][1:],before['InputMetadata'][1:27])
        self.assertEqual(result['Arguments'],['-t7-iw7-material-parts-v1','mp_freerun_04','p7_fre_platform_cap_02','0'])
        self.assertEqual(result['ExpectedBuildPlanSHA256'],probe.BUILD_PIN[1])
        self.assertFalse(set(probe.EXPORT_FIELDS)&set(result))
        self.assertFalse(any('provider.xpak' in p['Path'] or 'request.json' in p['Path'] for p in result['Bindings']))

    def test_changed_family_inventory_and_duplicate_source_paths_refuse(self):
        for case in ('family','profile','bootstrap-count','metadata-count','candidate','duplicate'):
            args=list(self.fixture())
            if case=='family':args[0]['Operation']='Catalogue'
            elif case=='profile':args[0]['CandidateProfile']='ordinary-d2'
            elif case=='bootstrap-count':args[0]['Bootstraps'].pop()
            elif case=='metadata-count':args[0]['InputMetadata'].pop()
            elif case=='candidate':args[0]['Bindings']=[p for p in args[0]['Bindings'] if p['Path']!=args[0]['CandidateSource']]
            else:args[1][0]['Path']=args[4]['SourceManifest']['Path']
            with self.subTest(case=case),self.assertRaises(ValueError):probe.derive(*args)

if __name__=='__main__':unittest.main()

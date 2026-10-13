import hashlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import prepare_catalog_trace as p
import prepare_cli


@unittest.skipUnless(os.environ.get('IW7_T7_SOURCE'), 'Retained native source not supplied')
class CatalogueTraceWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, sources = prepare_cli.render(Path(os.environ['IW7_T7_SOURCE']))
        cls.before = sources[prepare_cli.PATHS[0]]
        cls.after = p.wire_main(cls.before)

    def test_removing_only_observations_recovers_exact_original_main(self):
        source = self.after.replace('#include <intrin.h>\n#include <cwchar>\n#include <cstdio>\n', '')
        source = source.replace('\n'+p.SUPPORT, '')
        for line in ('\t\tcatalog_trace_once(32, "exit_hook", code, _ReturnAddress());\n',
                     '\t\t\tcatalog_trace_once(2, "before_post_unpack");\n',
                     '\t\t\tcatalog_trace_once(4, "after_post_unpack");\n',
                     '\tcatalog_trace_initialize();\n'):
            source = source.replace(line, '')
        source = source.replace('\t\tcatalog_trace_once(8, "before_entry_point");\n'
            '\t\tconst auto result = static_cast<int>(entry_point());\n'
            '\t\tcatalog_trace_once(16, "entry_point_return", result);\n\t\treturn result;',
            '\t\treturn static_cast<int>(entry_point());')
        self.assertEqual(source, self.before)

    def test_exit_and_boot_observations_precede_cleanup_and_preserve_call_results(self):
        hook = self.after.split('void WINAPI exit_hook(', 1)[1].split('\n\t}', 1)[0]
        self.assertLess(hook.index('_ReturnAddress()'), hook.index('component_loader::pre_destroy();'))
        self.assertIn('exit(code);', hook)
        stub = self.after.split('BOOL set_process_dpi_aware_stub()', 1)[1].split('FARPROC load_binary()', 1)[0]
        self.assertLess(stub.index('before_post_unpack'), stub.index('component_loader::post_unpack();'))
        self.assertLess(stub.index('component_loader::post_unpack();'), stub.index('after_post_unpack'))
        self.assertIn('return SetProcessDPIAware();', stub)
        self.assertEqual(self.after.count('entry_point()'), 1)
        self.assertIn('"entry_point_return", result);\n\t\treturn result;', self.after)

    def test_exact_existing_command_enables_trace_before_flag_cache_or_engine_work(self):
        self.assertIn('count == 3 && std::wcscmp(args[1], L"-t7-iw7-catalog") == 0', p.SUPPORT)
        self.assertIn("args[2][0] != L'\\0'", p.SUPPORT)
        main = self.after.split('int main()\n{', 1)[1]
        self.assertLess(main.index('catalog_trace_initialize();'), main.index('utils::flags::has_flag'))
        self.assertLess(p.SUPPORT.index('LocalFree(args);'), p.SUPPORT.index('std::setvbuf'))
        self.assertEqual(p.SUPPORT.count('std::setvbuf'), 2)
        self.assertIn('stdout_unbuffered=%d stderr_unbuffered=%d', p.SUPPORT)

    def test_each_static_phase_is_once_only_and_flushed_with_no_payload_or_file_io(self):
        self.assertIn('InterlockedOr(&catalog_trace_seen, bit) & bit', p.SUPPORT)
        self.assertIn('InterlockedOr(&catalog_trace_seen, 1) & 1', p.SUPPORT)
        self.assertEqual(self.after.count('catalog_trace_once('), 6)  # Definition and five sites.
        self.assertEqual(p.SUPPORT.count('std::fprintf(stderr,'), 2)
        self.assertEqual(p.SUPPORT.count('std::fflush(stderr);'), 2)
        for forbidden in ('CreateFile', 'LoadLibrary', 'OpenProcess', 'ReadProcessMemory',
                          'SetCommandLine', 'DB_', 'quick_exit', 'printf(stdout'):
            self.assertNotIn(forbidden, p.SUPPORT)

    def test_anchor_drift_and_double_instrumentation_refuse(self):
        with self.assertRaises(ValueError): p.wire_main(self.after)
        with self.assertRaises(ValueError): p.wire_main(self.before.replace('entry_point()', 'different_entry()'))


class CatalogueBaseTests(unittest.TestCase):
    def fixture(self):
        raw = b'unchanged native source'
        payloads = {'prepared/'+n:raw for n in ('main.cpp','zonetool.cpp','common/xpak.cpp',
            'common/xpak.hpp','t7_iw7_resident_model.hpp','t7_asset_name.hpp','test_t7_asset_name.cpp')}
        bindings = [{'Path':'C:\\old\\prepared\\'+n.removeprefix('prepared/').replace('/', '\\'),
                     'Bytes':len(raw),'SHA256':hashlib.sha256(raw).hexdigest()} for n in payloads]
        prior = {'PreparedRoot':r'C:\old\prepared','Bindings':bindings}
        prior_raw = json.dumps(prior).encode()
        stages = [{'Artifacts':[{'Path':'C:\\old\\'+name+'.obj','Bytes':10,'SHA256':'a'*64}]}
                  for name in ('helper','main','zonetool11','xpak')]
        old_raw = json.dumps({'Stages':stages}).encode()
        base = {'Schema':'iw7.t7-minimal-build-plan/1',**prior,'BuildProfile':None,
                'ReuseCompile':{'SourcePlanSHA256':hashlib.sha256(prior_raw).hexdigest(),
                                'ReceiptSHA256':hashlib.sha256(old_raw).hexdigest()},
                'Stages':[{'Name':'link'}],'Inputs':[s['Artifacts'][0] for s in stages]}
        return base, prior_raw, old_raw, payloads

    def verify(self, base, prior, old, payloads, mutate_receipt=None, *, surface_count_diagnostic=False,
               resident_multisurface_v2=False):
        raw = json.dumps(base).encode(); sha = hashlib.sha256(raw).hexdigest()
        receipt = {'Schema':'iw7.t7-minimal-build/1','PlanSHA256':sha,'Status':'Passed',
                   'InputsReverified':True,'TreeClosureConfirmed':True,'LeaseReleased':True,'Quarantined':False,
                   'Stages':[{'Name':'link','ExitCode':0,'TreeClosureConfirmed':True}]}
        if mutate_receipt: mutate_receipt(receipt)
        receipt_raw = json.dumps(receipt).encode()
        with patch.object(p, 'BASE_PLAN_SHA', sha), patch.object(p, 'BASE_RECEIPT_SHA', hashlib.sha256(receipt_raw).hexdigest()):
            p.verify_base(raw, receipt_raw, prior, old, payloads, surface_count_diagnostic=surface_count_diagnostic,
                          resident_multisurface_v2=resident_multisurface_v2)

    def surface_count_fixture(self):
        base, prior_raw, old, payloads = self.fixture()
        name = p.SURFACE_COUNT_HEADER
        payloads[name] = (p.prepare_cli.HERE/'fixtures/resident-surface-count-v1.hpp').read_text(encoding='utf-8').encode()
        pin = next(row for row in base['Bindings'] if row['Path'].endswith(Path(name).name))
        pin.update(Bytes=p.SURFACE_COUNT_OLD_PIN[0], SHA256=p.SURFACE_COUNT_OLD_PIN[1])
        prior = json.loads(prior_raw); prior['Bindings'] = base['Bindings']
        prior_raw = json.dumps(prior).encode()
        base['ReuseCompile']['SourcePlanSHA256'] = hashlib.sha256(prior_raw).hexdigest()
        return base, prior_raw, old, payloads

    def test_accepts_only_exact_opted_in_surface_count_header_transition(self):
        self.verify(*self.surface_count_fixture(), surface_count_diagnostic=True)
        with self.assertRaises(ValueError): self.verify(*self.surface_count_fixture())

    def multisurface_fixture(self):
        base,prior_raw,old,payloads=self.fixture();transitions={}
        for name,(before,_) in p.MULTISURFACE_TRANSITIONS.items():
            raw=('invented sealed v2 '+name).encode();payloads[name]=raw
            transitions[name]=(before,(len(raw),hashlib.sha256(raw).hexdigest()))
            pin=next(row for row in base['Bindings'] if row['Path'].endswith(Path(name).name))
            pin.update(Bytes=before[0],SHA256=before[1])
        prior=json.loads(prior_raw);prior['Bindings']=base['Bindings'];prior_raw=json.dumps(prior).encode()
        base['ReuseCompile']['SourcePlanSHA256']=hashlib.sha256(prior_raw).hexdigest()
        return (base,prior_raw,old,payloads),transitions

    def test_v2_requires_exact_three_transitions_and_explicit_exclusive_mode(self):
        args,transitions=self.multisurface_fixture()
        with patch.object(p,'MULTISURFACE_TRANSITIONS',transitions):
            self.verify(*args,resident_multisurface_v2=True)
            for flags in ({},{'resident_multisurface_v2':'true'},
                          {'resident_multisurface_v2':True,'surface_count_diagnostic':True}):
                with self.subTest(flags=flags),self.assertRaises(ValueError): self.verify(*args,**flags)

    def test_v2_does_not_allow_changed_payload_by_name_or_unrelated_difference(self):
        for name in ('main.cpp','zonetool.cpp','t7_iw7_resident_model.hpp','common/xpak.cpp','t7_asset_name.hpp'):
            args,transitions=self.multisurface_fixture();args[3]['prepared/'+name]+=b' '
            with patch.object(p,'MULTISURFACE_TRANSITIONS',transitions),self.assertRaises(ValueError):
                self.verify(*args,resident_multisurface_v2=True)
        args,transitions=self.multisurface_fixture();del args[3]['prepared/zonetool.cpp']
        with patch.object(p,'MULTISURFACE_TRANSITIONS',transitions),self.assertRaises(ValueError):
            self.verify(*args,resident_multisurface_v2=True)

    def test_diagnostic_refuses_other_header_new_hash_or_old_pin(self):
        for mode in ('other_header','new_hash','old_pin'):
            with self.subTest(mode=mode):
                args = self.surface_count_fixture()
                if mode == 'other_header': args[3]['prepared/t7_asset_name.hpp'] = b'changed'
                elif mode == 'new_hash': args[3][p.SURFACE_COUNT_HEADER] += b' '
                else:
                    row = next(r for r in args[0]['Bindings'] if r['Path'].endswith('t7_iw7_resident_model.hpp'))
                    row['SHA256'] = '0'*64
                with self.assertRaises(ValueError): self.verify(*args, surface_count_diagnostic=True)

    def test_diagnostic_refuses_truthy_flag_or_missing_transition(self):
        with self.assertRaises(ValueError): self.verify(*self.surface_count_fixture(), surface_count_diagnostic='true')
        with self.assertRaises(ValueError): self.verify(*self.fixture(), surface_count_diagnostic=True)

    def test_accepts_same_sources_and_exact_retained_artifacts(self):
        self.verify(*self.fixture())

    def test_refuses_other_proof_before_parsing(self):
        with self.assertRaisesRegex(ValueError, 'Exact ordinary D2'):
            p.verify_base(b'{}',b'{}',b'{}',b'{}',{})

    def test_rejects_different_main_header_or_catalogue_sources(self):
        for name in ('main.cpp','zonetool.cpp','common/xpak.hpp','t7_asset_name.hpp'):
            args = self.fixture(); args[3]['prepared/'+name] = b'different'
            with self.assertRaisesRegex(ValueError, 'native source differs'): self.verify(*args)

    def test_rejects_changed_retained_binary_pin_or_compile_chain(self):
        args = self.fixture(); args[0]['Inputs'][1]['SHA256'] = 'b'*64
        with self.assertRaisesRegex(ValueError, 'retained object/helper'): self.verify(*args)
        args = self.fixture(); args[0]['ReuseCompile']['ReceiptSHA256'] = 'b'*64
        with self.assertRaisesRegex(ValueError, 'compilation chain'): self.verify(*args)

    def test_rejects_diagnostic_or_incomplete_base(self):
        args = self.fixture(); args[0]['BuildProfile'] = {'Name':'t7-prepatch-probe'}
        with self.assertRaises(ValueError): self.verify(*args)
        for field, value in (('Status','Failed'),('InputsReverified',False),('Quarantined',True)):
            with self.assertRaises(ValueError):
                self.verify(*self.fixture(), mutate_receipt=lambda r:r.update({field:value}))


if __name__ == '__main__': unittest.main()

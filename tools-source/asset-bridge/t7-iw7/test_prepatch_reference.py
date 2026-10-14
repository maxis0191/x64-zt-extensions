"""Source and reuse checks only; no mapped engine bytes are read here."""
import hashlib
import json
import os
from pathlib import Path
import re
import unittest
import prepare_build as build
import prepare_cli
import prepare_prepatch
import prepare_prepatch_reference as p
import test_build_commands as recipes
from test_prepatch_source import selected_sites

HERE = Path(__file__).resolve().parent


class ReferenceSourceTests(unittest.TestCase):
    def test_frozen_v1_and_v2_contracts_match_their_actual_text(self):
        section = json.loads((HERE/'cli-source-contract.json').read_text(encoding='utf-8'))['prepatch_reference_v2']
        self.assertEqual(section['schema'], p.BUILD_SCHEMA)
        self.assertEqual(section['source_profile'], p.NAME)
        self.assertEqual(set(section['files']), set(build.REFERENCE_SOURCE_PINS))
        for name, pin in build.REFERENCE_SOURCE_PINS.items():
            raw = (HERE/name).read_bytes().replace(b'\r\n', b'\n')
            self.assertEqual((len(raw), hashlib.sha256(raw).hexdigest()), pin, name)
            self.assertEqual(section['files'][name], {'lf_bytes':pin[0], 'lf_sha256':pin[1]})

    def test_only_two_fixed_bodies_are_selected_without_callee_following(self):
        source = (HERE/p.HELPER).read_text(encoding='utf-8')
        self.assertEqual(selected_sites(source), [('DB_AddXAsset',0x1D4600,0,0x800), ('Load_SimpleAsset',0x1DB2B0,0,0x100)])
        self.assertIn('std::array<site, 2>', source)
        self.assertEqual(sum(s[3] for s in selected_sites(source)), 2304)
        self.assertIn('argc == 2 && std::wcscmp(argv[1], L"'+p.OPTION+'") == 0', source)
        self.assertIn('L"'+p.REPORT+'"', source)
        self.assertIn('"'+p.SCHEMA+'"', source)

    def test_v2_preserves_every_v1_memory_publication_and_stop_guard(self):
        original = (HERE/prepare_prepatch.HELPER).read_text(encoding='utf-8')
        source = (HERE/p.HELPER).read_text(encoding='utf-8')
        def remove_sites(text):
            return re.sub(r'    inline constexpr std::array<site, (?:2|12)> sites\{\{.*?    \}\};', '<fixed sites>', text, count=1, flags=re.S)
        reversed_v2 = source.replace(p.API, prepare_prepatch.API).replace(p.NAME, prepare_prepatch.NAME).replace(p.SCHEMA,'iw7.t7-prepatch-memory-observation/1')
        self.assertEqual(remove_sites(reversed_v2), remove_sites(original))
        self.assertEqual(len(selected_sites(original)), 12)

    def test_wrong_length_or_content_is_refused(self):
        raw = (HERE/p.HELPER).read_bytes()
        for candidate in (raw+b' ', raw.replace(b'0x1D4600',b'0x1D4601'), b''):
            with self.subTest(size=len(candidate)), self.assertRaises(ValueError):
                p.require_pin(candidate,p.PINS[p.HELPER],'helper')


@unittest.skipUnless(os.environ.get('IW7_T7_SOURCE'), 'Retained native source not supplied')
class ReferenceIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, sources = prepare_cli.render(Path(os.environ['IW7_T7_SOURCE']))
        cls.before = sources[prepare_cli.PATHS[0]]
        cls.after = p.wire_main(cls.before)

    def test_capture_and_refusals_precede_engine_continuation(self):
        stub = self.after.split('\t\tBOOL set_process_dpi_aware_stub()',1)[1].split('\t\tFARPROC load_binary()',1)[0]
        self.assertLess(stub.index('exit_hook('+p.API+'::capture())'), stub.index('component_loader::post_unpack();'))
        self.assertEqual(self.after.count(p.API+'::capture()'), 1)
        self.assertNotIn(prepare_prepatch.API,self.after)
        main = self.after.split('int main()\n',1)[1]
        self.assertLess(main.index(p.API+'::validate_invocation()'),main.index('game::set_mode'))
        self.assertEqual(self.after.count(p.API+'::requested() ? 2 : 0;'),2)
        self.assertIn('entrypoint returned without capture.',self.after)
        self.assertIn('if ('+p.API+'::requested()) return prepatch_early_exit;',self.after)
        self.assertEqual(self.after.split('\tnamespace iw7\n',1)[1].split('\tint main_internal()',1)[0],
                         self.before.split('\tnamespace iw7\n',1)[1].split('\tint main_internal()',1)[0])

    def test_wiring_is_not_idempotent_and_refuses_even_unrelated_drift(self):
        for source in (self.after, self.before+' ', self.before.replace('set_process_dpi_aware_stub','changed_stub')):
            with self.assertRaises(ValueError): p.wire_main(source)

    def fixture(self):
        prior_raw, receipt, payloads, run = recipes.ReuseTests().fixture()
        prior = json.loads(prior_raw)
        old_main = next(pin for pin in prior['Bindings'] if pin['Path'].endswith('main.cpp'))
        old_main.update(Bytes=p.RETAINED_MAIN[0],SHA256=p.RETAINED_MAIN[1])
        prior_raw = json.dumps(prior).encode()
        receipt['PlanSHA256'] = hashlib.sha256(prior_raw).hexdigest()
        payloads['prepared/main.cpp'] = self.after.encode()
        payloads['prepared/'+p.HELPER] = (HERE/p.HELPER).read_bytes()
        return prior_raw, receipt, payloads, run

    def test_reuses_qualified_cli_and_xpak_but_never_old_main(self):
        prior,receipt,payloads,run = self.fixture()
        proof,pins,text = build.reuse_compilation(prior,json.dumps(receipt).encode(),payloads,run,
            recompile_main=True,prepatch_reference_v2=True)
        self.assertTrue(proof['RecompiledMain'])
        self.assertEqual(proof['StageRoots'],[r'C:\old\zonetool11',r'C:\old\xpak'])
        self.assertFalse(any('\\old\\main\\' in pin['Path'] for pin in pins))
        self.assertIn(r'C:\fresh\main\main.obj',payloads['link.rsp'].decode())
        self.assertEqual(len(text),7)

    def test_reuse_refuses_arbitrary_main_helper_or_unrelated_cli(self):
        for changed in ('prepared/main.cpp','prepared/'+p.HELPER,'prepared/zonetool.cpp'):
            prior,receipt,payloads,run = self.fixture()
            payloads[changed] += b' '
            with self.subTest(payload=changed),self.assertRaises(ValueError):
                build.reuse_compilation(prior,json.dumps(receipt).encode(),payloads,run,
                    recompile_main=True,prepatch_reference_v2=True)

    def test_reuse_refuses_wrong_selection_and_unqualified_base_main(self):
        for options in ({'prepatch_reference_v2':True}, {'prepatch_reference_v2':'true','recompile_main':True},
                        {'prepatch_reference_v2':True,'recompile_main':True,'catalog_trace':True}):
            prior,receipt,payloads,run = self.fixture()
            with self.subTest(options=options),self.assertRaises(ValueError):
                build.reuse_compilation(prior,json.dumps(receipt).encode(),payloads,run,**options)
        prior,receipt,payloads,run = self.fixture()
        value = json.loads(prior)
        next(pin for pin in value['Bindings'] if pin['Path'].endswith('main.cpp'))['SHA256'] = '0'*64
        prior = json.dumps(value).encode()
        receipt['PlanSHA256'] = hashlib.sha256(prior).hexdigest()
        with self.assertRaises(ValueError):
            build.reuse_compilation(prior,json.dumps(receipt).encode(),payloads,run,recompile_main=True,prepatch_reference_v2=True)


if __name__ == '__main__':
    unittest.main()

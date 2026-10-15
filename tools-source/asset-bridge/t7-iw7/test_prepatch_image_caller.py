"""Source contracts/reuse only. No C++, engine, PE or opaque input is executed."""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import unittest
import prepare_build as build
import prepare_prepatch_image_caller as caller
import prepare_prepatch_link_v3 as v3
import test_build_commands as recipes

HERE = Path(__file__).resolve().parent


class CallerSourceTests(unittest.TestCase):
    def test_closed_source_contract_and_old_pins(self):
        section = json.loads((HERE/'cli-source-contract.json').read_text())['prepatch_image_caller_v1']
        self.assertEqual(section, dict(schema=caller.BUILD_SCHEMA,source_profile=caller.NAME,
            files={n:dict(lf_bytes=p[0],lf_sha256=p[1]) for n,p in build.CALLER_SOURCE_PINS.items()}))
        for name,pin in build.CALLER_SOURCE_PINS.items():
            raw=(HERE/name).read_bytes().replace(b'\r\n',b'\n')
            self.assertEqual((len(raw),hashlib.sha256(raw).hexdigest()),pin,name)
        contract=json.loads((HERE/'prepatch-image-caller-source-contract.json').read_text())
        self.assertEqual(contract['files'],section['files'])
        self.assertEqual(contract['selection']['callsite_rva'],'0x1B1E5D')
        self.assertEqual(contract['selection']['known_target_rva'],'0x7DB4C0')
        self.assertEqual(contract['selection']['code_limit_bytes'],8192)
        self.assertEqual(contract['fixture']['checks'],25)
        for name in ('native_executed','cpp_qualified','writer_proven','abi_proven','ready'):
            self.assertIs(contract[name],False)

    def test_reader_and_original_guard_implementation_are_unchanged(self):
        before=(HERE/v3.HELPER).read_text()
        after=(HERE/caller.HELPER).read_text()
        def reader(text):
            return text[text.index('    class image_reader'):text.index('    // Caller MUST immediately')]
        self.assertEqual(reader(before),reader(after))
        def metadata(text):
            return text[text.index('                const auto dos ='):text.index('                complete = true;')]
        self.assertEqual(metadata(before),metadata(after))
        self.assertIn('argc == 2 && std::wcscmp(argv[1], L"'+caller.OPTION+'") == 0',after)
        self.assertIn('captured.test_and_set() || bound_output.empty() || !validate_invocation()',after)
        self.assertIn('return complete ? 0 : 2;',after)

    def test_only_one_pdata_selected_body_is_copied_after_bound(self):
        text=(HERE/caller.HELPER).read_text()
        self.assertIn('std::array<site, 1>',text)
        self.assertEqual(re.findall(r'\{"Load_GfxImage_caller", (0x[0-9A-F]+)\}',text),['0x1B1E5D'])
        selection=text.index('caller_range::select(')
        refusal=text.index('require(selection == caller_range::status::ok',selection)
        copy=text.index('const auto body = reader.read(selected.begin, length)',refusal)
        validate=text.index('caller_range::validate_call(',copy)
        publish=text.index('row["bytes_hex"] = bytes_hex(body)',validate)
        self.assertLess(selection,refusal);self.assertLess(refusal,copy);self.assertLess(copy,validate);self.assertLess(validate,publish)
        self.assertNotIn('reader.read(site.',text)
        code=re.sub(r'//[^\n]*|/\*.*?\*/','',text,flags=re.S)
        self.assertIsNone(re.search(r'\b(?:OpenProcess|LoadLibrary\w*|CreateProcess\w*|CreateThread|VirtualProtect\w*|WriteProcessMemory|DB_\w+|load_zone)\s*\(',code))
        self.assertNotIn('utils::hook::',code)
        for name in ('writer_proven','gfximage_payload_read','outside_interval_followed'):
            self.assertIn('{"'+name+'", false}',text)

    def test_cpp_fixture_uses_actual_guard_and_authors_all_boundary_cases(self):
        guard=(HERE/caller.GUARD).read_text();fixture=(HERE/caller.FIXTURE).read_text()
        self.assertIn('#include "'+caller.GUARD+'"',fixture)
        self.assertIn('range::select(',fixture);self.assertIn('range::validate_call(',fixture)
        self.assertEqual(fixture.count('if (!check('),25)
        self.assertIn('checks == 25',fixture)
        for refusal in ('ambiguous','over_limit','missing','call_outside','opcode','target','invalid_metadata'):
            self.assertIn('status::'+refusal,fixture)
        self.assertIn('static_cast<int64_t>(callsite_rva) + 5 + displacement',guard)
        self.assertIn('selected.end - selected.begin > code_limit',guard)
        self.assertIn('selected.end - callsite_rva < 5',guard)
        self.assertNotIn('ReadProcessMemory',guard)

    def test_new_boolean_and_profile_mixtures_refuse(self):
        for value in (None,1,'true'):
            prior,receipt,payloads,run=recipes.ReuseTests().fixture()
            with self.subTest(value=value),self.assertRaises(ValueError):
                build.reuse_compilation(prior,json.dumps(receipt).encode(),payloads,run,prepatch_image_caller_v1=value)

    def test_parser_declares_paired_mode_without_address_or_cap_selector(self):
        text=(HERE/'prepare_build.py').read_text();ast.parse(text)
        for flag in ('--prepatch-image-caller-v1','--prepatch-image-caller-v1-base-plan'):
            self.assertIn("parser.add_argument('"+flag+"'",text)
        self.assertNotIn('--prepatch-image-caller-address',text)
        self.assertNotIn('--prepatch-image-caller-limit',text)


@unittest.skipUnless(os.environ.get('IW7_T7_V3_PLAN'),'Immutable V3 Source plan not supplied')
class CallerWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan_raw=Path(os.environ['IW7_T7_V3_PLAN']).read_bytes()
        cls.before=(Path(json.loads(cls.plan_raw)['PreparedRoot'])/'main.cpp').read_bytes()
        cls.after=caller.wire_main(cls.before.decode()).encode()

    def test_wired_main_only_rebinds_existing_rendezvous(self):
        self.assertEqual((len(self.after),hashlib.sha256(self.after).hexdigest()),caller.MAIN)
        text=self.after.decode()
        self.assertEqual(text.count(caller.API+'::capture()'),1)
        stub=text.split('\t\tBOOL set_process_dpi_aware_stub()',1)[1].split('\t\tFARPROC load_binary()',1)[0]
        self.assertLess(stub.index('exit_hook('+caller.API+'::capture())'),stub.index('component_loader::post_unpack();'))
        self.assertEqual(text.replace(caller.API,v3.API).replace(caller.HELPER,v3.HELPER),self.before.decode())
        with self.assertRaises(ValueError):caller.wire_main(self.before.decode()+' ')
        with self.assertRaises(ValueError):caller.wire_main(text)

    def test_pinned_plan_and_main_read_are_finite_source_only(self):
        def read(path,limit,digest):
            self.assertEqual(path.name,'main.cpp');self.assertEqual(limit,64*1024)
            raw=path.read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),digest);return raw
        self.assertEqual(caller.prepared_main(self.plan_raw,read)[0],self.after)
        with self.assertRaises(ValueError):caller.prepared_main(self.plan_raw+b' ',read)

    def fixture(self):
        prior,receipt,payloads,run=recipes.ReuseTests().fixture()
        value=json.loads(prior)
        next(p for p in value['Bindings'] if p['Path'].endswith('main.cpp')).update(
            Bytes=caller.RETAINED_MAIN[0],SHA256=caller.RETAINED_MAIN[1])
        prior=json.dumps(value).encode();receipt['PlanSHA256']=hashlib.sha256(prior).hexdigest()
        payloads['prepared/main.cpp']=self.after
        for name in (caller.HELPER,caller.GUARD):payloads['prepared/'+name]=(HERE/name).read_bytes().replace(b'\r\n',b'\n')
        return prior,receipt,payloads,run

    def test_finite_reuse_keeps_old_failed_cohort_and_two_retained_tus(self):
        prior,receipt,payloads,run=self.fixture()
        proof,pins,text=build.reuse_compilation(prior,json.dumps(receipt).encode(),payloads,run,
            recompile_main=True,prepatch_image_caller_v1=True)
        self.assertEqual(proof['OriginalStatus'],'Failed')
        self.assertEqual(proof['StageRoots'],[r'C:\old\zonetool11',r'C:\old\xpak'])
        self.assertFalse(any('\\old\\main\\' in p['Path'] for p in pins))
        self.assertEqual(len(text),7)
        self.assertIn(r'C:\fresh\main\main.obj',payloads['link.rsp'].decode())

    def test_new_sources_and_mixed_modes_refuse(self):
        for name in ('prepared/main.cpp','prepared/'+caller.HELPER,'prepared/'+caller.GUARD,'prepared/zonetool.cpp'):
            prior,receipt,payloads,run=self.fixture();payloads[name]+=b' '
            with self.subTest(name=name),self.assertRaises(ValueError):
                build.reuse_compilation(prior,json.dumps(receipt).encode(),payloads,run,recompile_main=True,prepatch_image_caller_v1=True)
        for options in ({'recompile_main':False},{'prepatch_reference_v2':True},{'prepatch_link_v3':True},{'catalog_trace':True}):
            prior,receipt,payloads,run=self.fixture()
            with self.subTest(options=options),self.assertRaises(ValueError):
                build.reuse_compilation(prior,json.dumps(receipt).encode(),payloads,run,
                    **{'recompile_main':True,'prepatch_image_caller_v1':True,**options})


if __name__ == '__main__':unittest.main()

"""Fixed V3 source/reuse checks; no engine, PE or process is read or launched."""
import hashlib
import json
import os
from pathlib import Path
import re
import unittest
import prepare_build as build
import prepare_prepatch_reference as v2
import prepare_prepatch_link_v3 as v3
import test_build_commands as recipes
from test_prepatch_source import selected_sites

HERE = Path(__file__).resolve().parent


class LinkSourceTests(unittest.TestCase):
    def test_exact_pins_and_fixed_three_rows(self):
        section=json.loads((HERE/'cli-source-contract.json').read_text(encoding='utf-8'))['prepatch_link_v3']
        self.assertEqual(section,{'schema':v3.BUILD_SCHEMA,'source_profile':v3.NAME,
            'files':{n:{'lf_bytes':p[0],'lf_sha256':p[1]} for n,p in build.LINK_SOURCE_PINS.items()}})
        for name,pin in build.LINK_SOURCE_PINS.items():
            raw=(HERE/name).read_bytes().replace(b'\r\n',b'\n')
            self.assertEqual((len(raw),hashlib.sha256(raw).hexdigest()),pin,name)
        text=(HERE/v3.HELPER).read_text(encoding='utf-8')
        self.assertEqual(selected_sites(text),[('DB_LinkXAssetEntry',0x1D7960,0x2A60,0x4000),
            ('DB_FindXAssetHeader',0x1D5FB0,0,0x100),('DB_IsXAssetDefault',0x1D7260,0,0x100)])
        self.assertEqual(sum(s[3] for s in selected_sites(text)),16896)
        self.assertEqual(0x1D7960-0x2A60,0x1D4F00)
        self.assertEqual(0x1D4F00+0x4000,0x1D8F00)

    def test_collector_is_unchanged_outside_explicit_constants(self):
        original=(HERE/v2.HELPER).read_text(encoding='utf-8')
        text=(HERE/v3.HELPER).read_text(encoding='utf-8')
        def no_sites(s):
            return re.sub(r'    inline constexpr std::array<site, [23]> sites\{\{.*?    \}\};','<sites>',s,count=1,flags=re.S)
        reverse=text.replace(v3.API,v2.API).replace(v3.NAME,v2.NAME).replace(v3.SCHEMA,v2.SCHEMA)
        self.assertEqual(no_sites(reverse),no_sites(original))
        self.assertIn('argc == 2 && std::wcscmp(argv[1], L"'+v3.OPTION+'") == 0',text)

    def test_optional_v3_selector_cannot_accept_v2_or_other_profiles(self):
        # Reuse validation is independent of any native process or input file.
        for value in ('true',1,None):
            prior,receipt,payloads,run=recipes.ReuseTests().fixture()
            with self.subTest(value=value),self.assertRaises(ValueError):
                build.reuse_compilation(prior,json.dumps(receipt).encode(),payloads,run,prepatch_link_v3=value)


@unittest.skipUnless(os.environ.get('IW7_T7_V2_PLAN'),'Immutable V2 text recipe not supplied')
class LinkIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan_raw=Path(os.environ['IW7_T7_V2_PLAN']).read_bytes()
        cls.before=(Path(json.loads(cls.plan_raw)['PreparedRoot'])/'main.cpp').read_bytes()
        cls.after=v3.wire_main(cls.before.decode()).encode()

    def test_wired_main_uses_exact_old_input_and_exits_before_post_unpack(self):
        self.assertEqual((len(self.before),hashlib.sha256(self.before).hexdigest()),v3.BASE_MAIN)
        self.assertEqual((len(self.after),hashlib.sha256(self.after).hexdigest()),v3.MAIN)
        text=self.after.decode()
        self.assertEqual(text.count(v3.API+'::capture()'),1)
        self.assertNotIn(v2.API,text)
        stub=text.split('\t\tBOOL set_process_dpi_aware_stub()',1)[1].split('\t\tFARPROC load_binary()',1)[0]
        self.assertLess(stub.index('exit_hook('+v3.API+'::capture())'),stub.index('component_loader::post_unpack();'))
        self.assertEqual(text.replace(v3.API,v2.API).replace(v3.HELPER,v2.HELPER),self.before.decode())

    def test_prepared_main_refuses_relocated_content_drift(self):
        def read(path,limit,digest):
            raw=Path(path).read_bytes();self.assertLessEqual(len(raw),limit)
            self.assertEqual(hashlib.sha256(raw).hexdigest(),digest)
            return raw
        actual,path=v3.prepared_main(self.plan_raw,read)
        self.assertEqual(actual,self.after)
        self.assertEqual(path.name,'main.cpp')
        with self.assertRaises(ValueError):v3.prepared_main(self.plan_raw+b' ',read)
        for changed in (self.before+b' ',self.after):
            with self.assertRaises(ValueError):v3.wire_main(changed.decode())

    def fixture(self):
        prior,receipt,payloads,run=recipes.ReuseTests().fixture()
        value=json.loads(prior)
        next(p for p in value['Bindings'] if p['Path'].endswith('main.cpp')).update(
            Bytes=v3.RETAINED_MAIN[0],SHA256=v3.RETAINED_MAIN[1])
        prior=json.dumps(value).encode();receipt['PlanSHA256']=hashlib.sha256(prior).hexdigest()
        payloads['prepared/main.cpp']=self.after
        payloads['prepared/'+v3.HELPER]=(HERE/v3.HELPER).read_bytes()
        return prior,receipt,payloads,run

    def test_only_main_is_new_while_qualified_cli_and_xpak_are_retained(self):
        prior,receipt,payloads,run=self.fixture()
        proof,pins,text=build.reuse_compilation(prior,json.dumps(receipt).encode(),payloads,run,
            recompile_main=True,prepatch_link_v3=True)
        self.assertTrue(proof['RecompiledMain'])
        self.assertEqual(proof['StageRoots'],[r'C:\old\zonetool11',r'C:\old\xpak'])
        self.assertFalse(any('\\old\\main\\' in p['Path'] for p in pins))
        self.assertEqual(len(text),7)
        self.assertIn(r'C:\fresh\main\main.obj',payloads['link.rsp'].decode())

    def test_v3_reuse_refuses_any_other_source_or_mixed_selection(self):
        for name in ('prepared/main.cpp','prepared/'+v3.HELPER,'prepared/zonetool.cpp'):
            prior,receipt,payloads,run=self.fixture();payloads[name]+=b' '
            with self.subTest(name=name),self.assertRaises(ValueError):
                build.reuse_compilation(prior,json.dumps(receipt).encode(),payloads,run,recompile_main=True,prepatch_link_v3=True)
        for opts in ({'recompile_main':False},{'prepatch_reference_v2':True},{'catalog_trace':True}):
            prior,receipt,payloads,run=self.fixture()
            with self.subTest(opts=opts),self.assertRaises(ValueError):
                build.reuse_compilation(prior,json.dumps(receipt).encode(),payloads,run,
                    **{'recompile_main':True,'prepatch_link_v3':True,**opts})


if __name__=='__main__':
    unittest.main()

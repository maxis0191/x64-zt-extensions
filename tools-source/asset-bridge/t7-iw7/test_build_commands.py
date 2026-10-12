import os
import hashlib
import json
from pathlib import Path, PureWindowsPath
import unittest
import prepare_build as p


class RecipeTests(unittest.TestCase):
    def test_response_paths_reject_quote_or_newline(self):
        for value in ('a"b', 'a\nb', 'a\0b'):
            with self.assertRaises(ValueError): p.quote(value)

    def test_dependency_parser_refuses_ambiguous_records(self):
        with self.assertRaises(ValueError): p.read_records('unowned.hpp\n')
        with self.assertRaises(ValueError): p.read_records('^C:\\a.cpp\na.hpp\n^c:\\A.cpp\nb.hpp\n')


class ReuseTests(unittest.TestCase):
    def fixture(self):
        run=PureWindowsPath(r'C:\fresh'); old=PureWindowsPath(r'C:\old'); prepared=old/'prepared'
        payloads={name:b'unchanged source' for name in ('prepared/main.cpp','prepared/zonetool.cpp',
            'prepared/common/xpak.cpp','prepared/common/xpak.hpp','prepared/t7_iw7_resident_model.hpp',
            'prepared/t7_asset_name.hpp','prepared/test_t7_asset_name.cpp')}
        payloads['link.rsp']=('flags\n'+'\n'.join(p.quote(run/obj[:-4]/obj) for _,obj,_ in p.UNITS)+'\n').encode()
        prior={'Schema':'iw7.t7-minimal-build-plan/1','RunRoot':str(old),'PreparedRoot':str(prepared),
               'Bindings':[{'Path':str(prepared/n.removeprefix('prepared/')),'Bytes':len(raw),'SHA256':hashlib.sha256(raw).hexdigest()}
                           for n,raw in payloads.items() if n.startswith('prepared/')]}
        prior_raw=json.dumps(prior).encode()
        stages=[{'Name':n,'ExitCode':0,'TreeClosureConfirmed':True} for n in ('helper','probe','main','zonetool11','xpak','link')]
        stages[1]['Checks']=51
        required={'helper':['native_probe.obj','native_probe.exe','native_probe.pdb','dependencies.json'],
                  **{obj[:-4]:[obj,'compile.pdb','dependencies.json'] for _,obj,_ in p.UNITS}}
        for s in stages:
            if s['Name'] in required:
                s['Artifacts']=[{'Path':str(old/s['Name']/n),'Bytes':1024,'SHA256':'1'*64} for n in required[s['Name']]]
        receipt={'Schema':'iw7.t7-minimal-build/1','PlanSHA256':hashlib.sha256(prior_raw).hexdigest(),
                 'Status':'Failed','TreeClosureConfirmed':True,'LeaseReleased':True,'Quarantined':False,'Stages':stages}
        return prior_raw,receipt,payloads,run

    def test_reuses_only_exact_prior_objects_and_preserves_failed_status(self):
        prior,r,payloads,run=self.fixture()
        reuse,pins,text=p.reuse_compilation(prior,json.dumps(r).encode(),payloads,run)
        self.assertEqual((len(pins),len(text),reuse['Checks'],reuse['OriginalStatus']),(13,7,51,'Failed'))
        response=payloads['link.rsp'].decode()
        self.assertNotIn('C:\\fresh',response)
        self.assertEqual(response.count('C:\\old'),3)
        self.assertEqual(r['Status'],'Failed')

    def test_changed_native_source_prevents_reuse(self):
        prior,r,payloads,run=self.fixture();payloads['prepared/zonetool.cpp']=b'changed source'
        with self.assertRaises(ValueError): p.reuse_compilation(prior,json.dumps(r).encode(),payloads,run)

    def test_unclosed_or_failed_compile_prevents_reuse(self):
        for field,value in (('TreeClosureConfirmed',False),('ExitCode',1)):
            prior,r,payloads,run=self.fixture();r['Stages'][2][field]=value
            with self.assertRaises(ValueError): p.reuse_compilation(prior,json.dumps(r).encode(),payloads,run)

    def test_missing_pdb_or_wrong_probe_prevents_reuse(self):
        prior,r,payloads,run=self.fixture();r['Stages'][2]['Artifacts'].pop()
        with self.assertRaises(ValueError): p.reuse_compilation(prior,json.dumps(r).encode(),payloads,run)
        prior,r,payloads,run=self.fixture();r['Stages'][1]['Checks']=50
        with self.assertRaises(ValueError): p.reuse_compilation(prior,json.dumps(r).encode(),payloads,run)

    def test_wrong_prior_plan_or_quarantine_prevents_reuse(self):
        prior,r,payloads,run=self.fixture();r['PlanSHA256']='0'*64
        with self.assertRaises(ValueError): p.reuse_compilation(prior,json.dumps(r).encode(),payloads,run)
        prior,r,payloads,run=self.fixture();r['Quarantined']=True
        with self.assertRaises(ValueError): p.reuse_compilation(prior,json.dumps(r).encode(),payloads,run)

    def diagnostic_fixture(self):
        prior,r,payloads,run=self.fixture()
        payloads['prepared/main.cpp']=b'instrumented main'
        payloads['prepared/native_prepatch_probe.inc']=b'bounded diagnostic helper'
        return prior,r,payloads,run

    def test_diagnostic_build_reuses_two_objects_and_helper_but_keeps_fresh_main(self):
        prior,r,payloads,run=self.diagnostic_fixture()
        reuse,pins,text=p.reuse_compilation(prior,json.dumps(r).encode(),payloads,run,recompile_main=True)
        self.assertEqual((len(pins),len(text),reuse['RecompiledMain']),(10,7,True))
        response=payloads['link.rsp'].decode()
        self.assertIn(r'C:\fresh\main\main.obj',response)
        self.assertNotIn(r'C:\old\main\main.obj',response)
        self.assertEqual(response.count('C:\\old'),2)
        self.assertEqual(reuse['StageRoots'],[r'C:\old\zonetool11',r'C:\old\xpak'])
        self.assertFalse(any('\\old\\main\\' in pin['Path'] for pin in pins))

    def test_diagnostic_reuse_refuses_changed_other_tu_or_header(self):
        for name in ('zonetool.cpp','common/xpak.cpp','common/xpak.hpp','t7_asset_name.hpp'):
            prior,r,payloads,run=self.diagnostic_fixture();payloads['prepared/'+name]=b'changed'
            with self.assertRaises(ValueError):
                p.reuse_compilation(prior,json.dumps(r).encode(),payloads,run,recompile_main=True)

    def test_diagnostic_reuse_requires_changed_main_and_bounded_helper(self):
        for mode in ('same_main','missing_helper','large_helper','extra_source'):
            prior,r,payloads,run=self.diagnostic_fixture()
            if mode == 'same_main': payloads['prepared/main.cpp']=b'unchanged source'
            elif mode == 'missing_helper': del payloads['prepared/native_prepatch_probe.inc']
            elif mode == 'large_helper': payloads['prepared/native_prepatch_probe.inc']=b'x'*65537
            else: payloads['prepared/unreviewed.cpp']=b'extra'
            with self.assertRaises(ValueError):
                p.reuse_compilation(prior,json.dumps(r).encode(),payloads,run,recompile_main=True)

    def test_ordinary_reuse_cannot_accept_instrumented_payload(self):
        prior,r,payloads,run=self.diagnostic_fixture()
        with self.assertRaises(ValueError): p.reuse_compilation(prior,json.dumps(r).encode(),payloads,run)

    def test_catalogue_trace_rebuilds_only_main_without_prepatch_helper(self):
        prior,r,payloads,run=self.fixture();payloads['prepared/main.cpp']=b'catalogue observations'
        reuse,pins,text=p.reuse_compilation(prior,json.dumps(r).encode(),payloads,run,recompile_main=True,catalog_trace=True)
        self.assertEqual((len(pins),len(text),reuse['RecompiledMain']),(10,7,True))
        self.assertIn(r'C:\fresh\main\main.obj',payloads['link.rsp'].decode())
        self.assertEqual(payloads['link.rsp'].decode().count('C:\\old'),2)

    def test_catalogue_trace_refuses_helper_extra_source_or_unchanged_main(self):
        for mode in ('helper','extra','unchanged'):
            prior,r,payloads,run=self.fixture()
            if mode != 'unchanged': payloads['prepared/main.cpp']=b'catalogue observations'
            if mode == 'helper': payloads['prepared/native_prepatch_probe.inc']=b'other mode'
            if mode == 'extra': payloads['prepared/extra.cpp']=b'new source'
            with self.assertRaises(ValueError):
                p.reuse_compilation(prior,json.dumps(r).encode(),payloads,run,recompile_main=True,catalog_trace=True)

    def publication_fixture(self):
        prior,r,payloads,run=self.fixture()
        payloads['prepared/main.cpp']=b'bounded publication main'
        payloads['prepared/zonetool.cpp']=b'two close-aware CLI exits'
        return prior,r,payloads,run

    def publication_reuse(self, fixture):
        prior,r,payloads,run=fixture
        return p.reuse_compilation(prior,json.dumps(r).encode(),payloads,run,
                                   recompile_main=True,catalog_trace=True,recompile_zonetool=True)

    def test_publication_reuses_only_xpak_and_helper_with_two_fresh_link_objects(self):
        fixture=self.publication_fixture();prior,r,payloads,run=fixture
        reuse,pins,text=self.publication_reuse(fixture)
        self.assertEqual((len(pins),len(text),reuse['RecompiledZonetool']),(7,7,True))
        self.assertEqual(reuse['StageRoots'],[r'C:\old\xpak'])
        response=payloads['link.rsp'].decode()
        for name in ('main','zonetool11'):
            self.assertIn(p.quote(run/name/(name+'.obj')),response)
            self.assertNotIn('C:\\old\\'+name+'\\',response)
            self.assertFalse(any('\\old\\'+name+'\\' in pin['Path'] for pin in pins))
        self.assertEqual(response.count('C:\\old'),1)
        self.assertEqual(r['Status'],'Failed')

    def test_publication_requires_changed_main_and_cli_and_unchanged_other_sources(self):
        for name in ('main.cpp','zonetool.cpp','common/xpak.cpp','common/xpak.hpp','t7_asset_name.hpp'):
            fixture=self.publication_fixture()
            fixture[2]['prepared/'+name]=b'unchanged source' if name in ('main.cpp','zonetool.cpp') else b'changed'
            with self.assertRaises(ValueError): self.publication_reuse(fixture)

    def test_publication_cannot_be_selected_without_main_and_catalogue_or_with_truthy_string(self):
        for main,trace,cli in ((False,False,True),(True,False,True),(False,True,True),(True,True,'true')):
            prior,r,payloads,run=self.publication_fixture()
            with self.assertRaises(ValueError):
                p.reuse_compilation(prior,json.dumps(r).encode(),payloads,run,
                                   recompile_main=main,catalog_trace=trace,recompile_zonetool=cli)

    def test_publication_refuses_stale_duplicate_or_missing_fresh_link_object(self):
        for name in ('main','zonetool11'):
            for mode in ('stale','duplicate','missing'):
                fixture=self.publication_fixture();payloads,run=fixture[2:]
                fresh=p.quote(run/name/(name+'.obj'))+'\n'
                replacement={'stale':p.quote(PureWindowsPath(r'C:\old')/name/(name+'.obj'))+'\n',
                             'duplicate':fresh+fresh,'missing':''}[mode]
                payloads['link.rsp']=payloads['link.rsp'].decode().replace(fresh,replacement).encode()
                with self.assertRaises(ValueError): self.publication_reuse(fixture)


@unittest.skipUnless(os.environ.get('IW7_T7_SOURCE') and os.environ.get('IW7_T7_E7_BUILD'),
                     'Retained T7 source and E7 build paths not supplied')
class ExactCommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e7 = Path(os.environ['IW7_T7_E7_BUILD'])
        cls.cl = p.text_pin(cls.e7/'obj/tlog/CL.command.1.tlog',4*1024**2,p.CL_LOG_SHA)[0].decode('utf-16')
        cls.link = p.text_pin(cls.e7/'obj/tlog/link.command.1.tlog',256*1024,p.LINK_LOG_SHA)[0].decode('utf-16')
        cls.native = os.environ['IW7_T7_SOURCE']

    def commands(self, cl=None, link=None):
        return p.command_payloads(self.cl if cl is None else cl, self.link if link is None else link,
                                  self.native,r'C:\private\prepared',r'C:\private\run')

    def test_three_compile_commands_preserve_abi_and_one_line_macros(self):
        outputs, old = self.commands()
        self.assertEqual(len(old),3)
        for _, obj, _ in p.UNITS:
            command = outputs[obj+'.rsp'].decode()
            for flag in ('/MT ', '/O1 ', '/Zi ', '/W4 ', '/WX ', '/fp:precise ', '/std:c++23preview ', '/Y-'):
                self.assertIn(flag,command)
            for forbidden in ('/Yu','/Fp','/MP','/D\n'):
                self.assertNotIn(forbidden,command)
            self.assertEqual(len(command.splitlines()),1)
            self.assertIn('/D EXPERIMENTAL_IW7',command)
            self.assertIn('C:\\private\\run\\'+obj[:-4]+'\\compile.pdb',command)

    def test_link_preserves_exact_order_of_410_reused_objects(self):
        outputs, replaced = self.commands()
        before = self.link.splitlines()[2:]
        after = outputs['link.rsp'].decode().splitlines()[1:]
        self.assertEqual(len(after),413)
        self.assertEqual(sum(a == b for a,b in zip(before,after)),410)
        self.assertEqual({PureWindowsPath(x).name.casefold() for x in replaced}, {'main.obj','zonetool11.obj','xpak.obj'})
        self.assertIn('/manifest:embed',outputs['link.rsp'].decode())
        self.assertNotIn('/MANIFEST:NO',outputs['link.rsp'].decode())

    def test_changed_compiler_or_link_contract_is_refused(self):
        for before, after in (('/fp:precise','/fp:fast'),('/W4','/W3'),('/MT ','/MD ')):
            with self.assertRaises(ValueError): self.commands(cl=self.cl.replace(before,after))
        with self.assertRaises(ValueError): self.commands(link=self.link.replace('/INCREMENTAL:NO','/INCREMENTAL'))


if __name__ == '__main__': unittest.main()

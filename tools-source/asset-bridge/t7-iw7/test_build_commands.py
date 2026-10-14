import os
import hashlib
import json
from pathlib import Path, PureWindowsPath
import unittest
from unittest.mock import patch
import prepare_build as p


class RecipeTests(unittest.TestCase):
    def test_historical_surface80_adapter_is_rejected_by_the_current_v2_transition(self):
        current=(p.HERE.parent/'t7-bridge/t7_iw7_resident_model.hpp').read_text(encoding='utf-8')
        historical=current.replace('surface96 + rigid16', 'surface80 + rigid16').replace(
            'sizeof(XSurface) == 96', 'sizeof(XSurface) == 80').replace(
            '256 + 384 * surfaces', '256 + 368 * surfaces').encode()
        self.assertEqual((len(historical),hashlib.sha256(historical).hexdigest()),
                         (21290,'97a417b82ab7edf002f73039d1280b5e2a34370594e151ff07698db3a81f65ed'))
        name=p.prepare_catalog_trace.SURFACE_COUNT_HEADER
        old=p.prepare_catalog_trace.MULTISURFACE_TRANSITIONS[name][0]
        pin={'Bytes':old[0],'SHA256':old[1]}
        for wired in (False,True):
            self.assertFalse(p.prepare_catalog_trace.multisurface_payload_delta(name,historical,pin,wired=wired))
            self.assertTrue(p.prepare_catalog_trace.multisurface_payload_delta(name,current.encode(),pin,wired=wired))

    def test_historical_diagnostic_fixture_keeps_its_exact_reviewed_pin(self):
        raw=(p.HERE/'fixtures/resident-surface-count-v1.hpp').read_text(encoding='utf-8').encode()
        self.assertEqual((len(raw),hashlib.sha256(raw).hexdigest()),p.prepare_catalog_trace.SURFACE_COUNT_NEW_PIN)
        current=(p.HERE.parent/'t7-bridge/t7_iw7_resident_model.hpp').read_text(encoding='utf-8').encode()
        old=p.prepare_catalog_trace.SURFACE_COUNT_OLD_PIN
        self.assertFalse(p.prepare_catalog_trace.surface_count_header_delta(
            p.prepare_catalog_trace.SURFACE_COUNT_HEADER,current,{'Bytes':old[0],'SHA256':old[1]}))

    @unittest.skipUnless(os.environ.get('IW7_T7_SOURCE'), 'Retained source not supplied')
    def test_render_only_streamed_plain_and_wired_pins_match_the_native_source(self):
        _,sources=p.prepare_cli.render(Path(os.environ['IW7_T7_SOURCE']))
        main,cli=(sources[p.prepare_cli.PATHS[i]] for i in (0,1))
        header=(p.HERE.parent/'t7-bridge/t7_iw7_resident_model.hpp').read_text(encoding='utf-8')
        plain=dict(zip(('prepared/main.cpp','prepared/zonetool.cpp',p.prepare_catalog_trace.SURFACE_COUNT_HEADER),
                       (main,cli,header)))
        main,cli=p.prepare_message_publication.overlay(p.prepare_catalog_trace.wire_message_main(main),cli)
        wired={**plain,'prepared/main.cpp':main,'prepared/zonetool.cpp':cli}
        for name,(old,_) in p.prepare_catalog_trace.RENDER_ONLY_STREAMED_TRANSITIONS.items():
            pin={'Bytes':old[0],'SHA256':old[1]}
            self.assertTrue(p.prepare_catalog_trace.multisurface_payload_delta(name,plain[name].encode(),pin,render_only_streamed=True))
            self.assertTrue(p.prepare_catalog_trace.multisurface_payload_delta(name,wired[name].encode(),pin,wired=True,render_only_streamed=True))
            self.assertFalse(p.prepare_catalog_trace.multisurface_payload_delta(name,wired[name].encode()+b' ',pin,wired=True,render_only_streamed=True))
            if name != p.prepare_catalog_trace.SURFACE_COUNT_HEADER:
                self.assertFalse(p.prepare_catalog_trace.multisurface_payload_delta(name,plain[name].encode(),pin))

    def test_committed_cli_source_contract_matches_current_text(self):
        contract = json.loads((p.HERE/'cli-source-contract.json').read_text(encoding='utf-8'))
        for name, pin in contract['files'].items():
            with self.subTest(file=name):
                raw = (p.HERE/name).read_text(encoding='utf-8').replace('\r\n', '\n').encode()
                self.assertEqual(len(raw), pin['lf_bytes'])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), pin['lf_sha256'])
        pin=contract['external_adapter']
        raw=(p.HERE.parents[2]/pin['repository_path']).read_text(encoding='utf-8').encode()
        self.assertEqual((len(raw),hashlib.sha256(raw).hexdigest()),(pin['lf_bytes'],pin['lf_sha256']))

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

    def surface_count_fixture(self):
        prior_raw,r,payloads,run=self.publication_fixture()
        prior=json.loads(prior_raw)
        name=p.prepare_catalog_trace.SURFACE_COUNT_HEADER
        payloads[name]=(p.HERE/'fixtures/resident-surface-count-v1.hpp').read_text(encoding='utf-8').encode()
        pin=next(row for row in prior['Bindings'] if row['Path'].endswith('t7_iw7_resident_model.hpp'))
        pin.update(Bytes=p.prepare_catalog_trace.SURFACE_COUNT_OLD_PIN[0],
                   SHA256=p.prepare_catalog_trace.SURFACE_COUNT_OLD_PIN[1])
        prior_raw=json.dumps(prior).encode();r['PlanSHA256']=hashlib.sha256(prior_raw).hexdigest()
        fixture={'base':(prior_raw,r,payloads,run),'dependencies':{}}
        for stage,source in (('helper','test_t7_asset_name.cpp'),('zonetool11','zonetool.cpp'),('xpak','common/xpak.cpp')):
            doc={'Version':'1.2','Data':{'Source':str(PureWindowsPath(prior['PreparedRoot'])/source),
                 'ProvidedModule':'','Includes':[r'C:\sdk\vector'],'ImportedModules':[],'ImportedHeaderUnits':[]}}
            if stage=='zonetool11': doc['Data']['Includes'].append(r'C:\old\prepared\t7_iw7_resident_model.hpp')
            self.set_dependency(fixture,stage,doc)
        fixture['journals']={
            'read':(''.join(f'^C:\\src\\tu{i}.cpp\nC:\\sdk\\vector\n' for i in range(413))).encode('utf-16'),
            'compile':(''.join(f'^C:\\src\\tu{i}.cpp\n/Fo"C:\\e7\\obj\\" /c C:\\src\\tu{i}.cpp\n'
                               for i in range(413))).encode('utf-16'),
            'link':('^C:\\e7\\bin\\tool.exe\n/INCREMENTAL:NO\n'+
                    ''.join(f'"C:\\e7\\obj\\tu{i}.OBJ"\n' for i in range(413))).encode('utf-16')}
        self.pin_fixture_journals(fixture)
        return fixture

    def pin_fixture_journals(self,fixture):
        fixture['journal_pins']={name:(len(raw),hashlib.sha256(raw).hexdigest())
                                 for name,raw in fixture['journals'].items()}

    def set_dependency(self,fixture,stage,doc):
        raw=json.dumps(doc).encode();fixture['dependencies'][stage]=raw
        row=next(s for s in fixture['base'][1]['Stages'] if s['Name']==stage)
        pin=next(p for p in row['Artifacts'] if p['Path'].endswith('dependencies.json'))
        pin.update(Bytes=len(raw),SHA256=hashlib.sha256(raw).hexdigest())

    def surface_count_reuse(self,fixture,**overrides):
        prior,r,payloads,run=fixture['base']
        flags=dict(recompile_main=True,catalog_trace=True,recompile_zonetool=True,
                   surface_count_dependencies=fixture['dependencies'],e7_dependency_text=fixture['journals'])
        flags.update(overrides)
        with patch.object(p,'E7_READ_PIN',fixture['journal_pins']['read']), \
             patch.object(p,'CL_LOG_SHA',fixture['journal_pins']['compile'][1]), \
             patch.object(p,'LINK_LOG_SHA',fixture['journal_pins']['link'][1]):
            return p.reuse_compilation(prior,json.dumps(r).encode(),payloads,run,**flags)

    def test_surface_count_keeps_two_fresh_objects_and_explicit_dependency_proof(self):
        fixture=self.surface_count_fixture();reuse,pins,text=self.surface_count_reuse(fixture)
        proof=reuse['ResidentSurfaceCountDiagnostic']
        self.assertEqual(proof['E7TranslationUnits'],413)
        self.assertEqual(proof['E7Objects'],413)
        self.assertEqual(len(proof['DependencyJSON']),3)
        self.assertEqual(proof['PreviousSHA256'],p.prepare_catalog_trace.SURFACE_COUNT_OLD_PIN[1])
        self.assertEqual(proof['SHA256'],p.prepare_catalog_trace.SURFACE_COUNT_NEW_PIN[1])
        self.assertEqual((len(pins),len(text),reuse['StageRoots']),(7,7,[r'C:\old\xpak']))
        response=fixture['base'][2]['link.rsp'].decode()
        for stage in ('main','zonetool11'):
            self.assertEqual(response.count(f'C:\\fresh\\{stage}\\{stage}.obj'),1)
        self.assertEqual(response.count('C:\\old'),1)

    def multisurface_fixture(self):
        fixture=self.surface_count_fixture()
        prior_raw,r,payloads,run=fixture['base'];prior=json.loads(prior_raw)
        transitions={};wired={}
        for name,(old,_) in p.prepare_catalog_trace.MULTISURFACE_TRANSITIONS.items():
            raw=('invented sealed v2 '+name).encode()
            output=b'publication overlay '+raw
            transitions[name]=(old,(len(raw),hashlib.sha256(raw).hexdigest()))
            wired[name]=(len(output),hashlib.sha256(output).hexdigest())
            payloads[name]=output
            pin=next(row for row in prior['Bindings'] if p.key(row['Path'])==
                     p.key(PureWindowsPath(prior['PreparedRoot'])/name.removeprefix('prepared/')))
            pin.update(Bytes=old[0],SHA256=old[1])
        prior_raw=json.dumps(prior).encode();r['PlanSHA256']=hashlib.sha256(prior_raw).hexdigest()
        fixture['base']=(prior_raw,r,payloads,run)
        fixture['v2_transitions'],fixture['v2_wired']=transitions,wired
        return fixture

    def multisurface_reuse(self,fixture,**overrides):
        with patch.object(p.prepare_catalog_trace,'MULTISURFACE_TRANSITIONS',fixture['v2_transitions']), \
             patch.object(p.prepare_catalog_trace,'MULTISURFACE_WIRED_PINS',fixture['v2_wired']):
            return self.surface_count_reuse(fixture,**{'resident_multisurface_v2':True,**overrides})

    def test_v2_keeps_complete_dependency_proof_and_only_two_fresh_objects(self):
        fixture=self.multisurface_fixture();reuse,pins,text=self.multisurface_reuse(fixture)
        proof=reuse['ResidentMultiSurfaceV2']
        self.assertNotIn('ResidentSurfaceCountDiagnostic',reuse)
        self.assertEqual(proof['Schema'],'iw7.t7-resident-multi-surface-build/2')
        self.assertEqual((proof['E7TranslationUnits'],proof['E7Objects'],len(proof['DependencyJSON'])),(413,413,3))
        self.assertEqual(len(proof['SourceTransitions']),3)
        self.assertEqual((len(pins),len(text),reuse['StageRoots']),(7,7,[r'C:\old\xpak']))
        response=fixture['base'][2]['link.rsp'].decode()
        self.assertEqual(response.count('C:\\old'),1)
        for name in ('main','zonetool11'):
            self.assertEqual(response.count(f'C:\\fresh\\{name}\\{name}.obj'),1)

    def test_v2_refuses_any_unsealed_payload_or_missing_transition(self):
        for name in ('main.cpp','zonetool.cpp','t7_iw7_resident_model.hpp','common/xpak.cpp',
                     'common/xpak.hpp','t7_asset_name.hpp','test_t7_asset_name.cpp'):
            fixture=self.multisurface_fixture();fixture['base'][2]['prepared/'+name]+=b' '
            with self.subTest(name=name),self.assertRaises(ValueError): self.multisurface_reuse(fixture)
        fixture=self.multisurface_fixture();del fixture['base'][2]['prepared/main.cpp']
        with self.assertRaises(ValueError): self.multisurface_reuse(fixture)

    def test_v2_requires_complete_pair_and_exact_old_source_tuple(self):
        for flags in ({'resident_multisurface_v2':False},{'resident_multisurface_v2':'true'},
                      {'recompile_main':False},{'recompile_zonetool':False},{'catalog_trace':False},
                      {'surface_count_dependencies':None},{'e7_dependency_text':None}):
            with self.subTest(flags=flags),self.assertRaises(ValueError):
                self.multisurface_reuse(self.multisurface_fixture(),**flags)
        for name in p.prepare_catalog_trace.MULTISURFACE_TRANSITIONS:
            fixture=self.multisurface_fixture();prior,r,payloads,run=fixture['base'];doc=json.loads(prior)
            next(row for row in doc['Bindings'] if row['Path'].endswith(PureWindowsPath(name).name))['SHA256']='f'*64
            prior=json.dumps(doc).encode();r['PlanSHA256']=hashlib.sha256(prior).hexdigest()
            fixture['base']=(prior,r,payloads,run)
            with self.assertRaises(ValueError): self.multisurface_reuse(fixture)

    def test_v2_rejects_retained_consumers_or_incomplete_e7_provenance(self):
        for mode in ('helper','xpak','e7_consumer','e7_object','e7_hash','dependency_hash'):
            fixture=self.multisurface_fixture()
            if mode in ('helper','xpak'):
                doc=json.loads(fixture['dependencies'][mode])
                doc['Data']['Includes'].append(r'C:\other\t7_iw7_resident_model.hpp')
                self.set_dependency(fixture,mode,doc)
            elif mode=='e7_consumer':
                fixture['journals']['read']=fixture['journals']['read'].decode('utf-16').replace(
                    'C:\\sdk\\vector',r'C:\other\t7_iw7_resident_model.hpp',1).encode('utf-16')
                self.pin_fixture_journals(fixture)
            elif mode=='e7_object':
                fixture['journals']['link']=fixture['journals']['link'].decode('utf-16').replace(
                    'tu412.OBJ','tu411.OBJ').encode('utf-16')
                self.pin_fixture_journals(fixture)
            elif mode=='e7_hash': fixture['journals']['read']+=b' '
            else: fixture['dependencies']['zonetool11']+=b' '
            with self.subTest(mode=mode),self.assertRaises(ValueError): self.multisurface_reuse(fixture)

    def test_surface_count_refuses_other_header_or_hash_and_missing_opt_in(self):
        for mode in ('other_header','new_hash','old_hash','missing_transition','no_evidence'):
            with self.subTest(mode=mode):
                fixture=self.surface_count_fixture();prior,r,payloads,run=fixture['base']
                if mode=='other_header': payloads['prepared/common/xpak.hpp']=b'changed'
                elif mode=='new_hash': payloads[p.prepare_catalog_trace.SURFACE_COUNT_HEADER]+=b' '
                elif mode=='old_hash':
                    doc=json.loads(prior)
                    next(row for row in doc['Bindings'] if row['Path'].endswith('t7_iw7_resident_model.hpp'))['SHA256']='f'*64
                    raw=json.dumps(doc).encode();r['PlanSHA256']=hashlib.sha256(raw).hexdigest()
                    fixture['base']=(raw,r,payloads,run)
                elif mode=='missing_transition': del payloads[p.prepare_catalog_trace.SURFACE_COUNT_HEADER]
                with self.assertRaises(ValueError):
                    if mode=='no_evidence': self.publication_reuse(fixture['base'])
                    else: self.surface_count_reuse(fixture)

    def test_surface_count_refuses_a_retained_helper_or_xpak_consumer_even_at_other_path(self):
        for stage in ('helper','xpak'):
            fixture=self.surface_count_fixture();doc=json.loads(fixture['dependencies'][stage])
            doc['Data']['Includes'].append(r'C:\other\T7_IW7_RESIDENT_MODEL.HPP')
            self.set_dependency(fixture,stage,doc)
            with self.assertRaisesRegex(ValueError,'only the recompiled CLI'): self.surface_count_reuse(fixture)

    def test_surface_count_refuses_missing_changed_or_wrong_source_dependency_evidence(self):
        for mode in ('missing','changed','document','source','module','header_unit','cli_missing_header','cli_wrong_header','relative'):
            with self.subTest(mode=mode):
                fixture=self.surface_count_fixture()
                if mode=='missing': del fixture['dependencies']['xpak']
                elif mode=='changed': fixture['dependencies']['helper']+=b' '
                elif mode=='document': self.set_dependency(fixture,'zonetool11',[])
                else:
                    doc=json.loads(fixture['dependencies']['zonetool11'])
                    if mode=='source': doc['Data']['Source']=r'C:\other\zonetool.cpp'
                    elif mode=='module': doc['Data']['ImportedModules']=['unknown module']
                    elif mode=='header_unit': doc['Data']['ImportedHeaderUnits']=['unknown header unit']
                    elif mode=='cli_missing_header': doc['Data']['Includes'].pop()
                    elif mode=='cli_wrong_header': doc['Data']['Includes'][-1]=r'C:\other\t7_iw7_resident_model.hpp'
                    elif mode=='relative': doc['Data']['Includes'][0]='relative.hpp'
                    self.set_dependency(fixture,'zonetool11',doc)
                with self.assertRaises(ValueError): self.surface_count_reuse(fixture)

    def test_surface_count_refuses_unsealed_incomplete_or_consuming_e7_journal(self):
        for mode in ('hash','missing_record','consumer'):
            with self.subTest(mode=mode):
                fixture=self.surface_count_fixture()
                if mode=='hash': fixture['journals']['read']+=b' '
                else:
                    text=fixture['journals']['read'].decode('utf-16')
                    if mode=='missing_record': text=text.replace('^C:\\src\\tu0.cpp\nC:\\sdk\\vector\n','')
                    else: text=text.replace('C:\\sdk\\vector',r'C:\old\t7_iw7_resident_model.hpp',1)
                    fixture['journals']['read']=text.encode('utf-16')
                    self.pin_fixture_journals(fixture)
                with self.assertRaises(ValueError): self.surface_count_reuse(fixture)

    def test_surface_count_refuses_missing_ambiguous_or_unmatched_object_provenance(self):
        for mode in ('missing_tu','extra_tu','duplicate_output','missing_fo','unknown_object','duplicate_link','command_hash'):
            with self.subTest(mode=mode):
                fixture=self.surface_count_fixture();journals=fixture['journals']
                compile_text=journals['compile'].decode('utf-16');link_text=journals['link'].decode('utf-16')
                if mode=='missing_tu': compile_text='\n'.join(compile_text.splitlines()[2:])+'\n'
                elif mode=='extra_tu': compile_text+='^C:\\src\\extra.cpp\n/Fo"C:\\e7\\obj\\extra.obj" /c extra.cpp\n'
                elif mode=='duplicate_output':
                    compile_text=compile_text.replace('/Fo"C:\\e7\\obj\\"','/Fo"C:\\e7\\obj\\same.obj"',2)
                elif mode=='missing_fo': compile_text=compile_text.replace('/Fo"C:\\e7\\obj\\"','',1)
                elif mode=='unknown_object': link_text=link_text.replace('tu0.OBJ','unknown.OBJ')
                elif mode=='duplicate_link': link_text=link_text.replace('tu0.OBJ','tu1.OBJ')
                journals['compile']=compile_text.encode('utf-16');journals['link']=link_text.encode('utf-16')
                self.pin_fixture_journals(fixture)
                if mode=='command_hash': journals['compile']+=b' '
                with self.assertRaises(ValueError): self.surface_count_reuse(fixture)

    def test_surface_count_refuses_incomplete_pair_or_reused_cli(self):
        for flags in ({'recompile_zonetool':False}, {'e7_dependency_text':None},
                      {'surface_count_dependencies':None}, {'recompile_main':False}):
            with self.assertRaises(ValueError): self.surface_count_reuse(self.surface_count_fixture(),**flags)


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

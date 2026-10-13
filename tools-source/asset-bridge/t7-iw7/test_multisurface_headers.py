"""Source-only dependency-closure tests; no compiler or binary inputs."""
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import unittest
from unittest.mock import patch
import prepare_build as p


class HeaderClosureTests(unittest.TestCase):
    def fixture(self):
        source = Path(r'C:\native'); e7 = Path(r'C:\e7')
        payloads = {name:b'x'*size for name,(size,_) in p.MULTISURFACE_HEADER_PINS.items()}
        pins = {name:(len(raw),hashlib.sha256(raw).hexdigest()) for name,raw in payloads.items()}
        writer = p.key(source/'src/zonetool/zonetool/iw7/assets/xsurface.cpp')
        cli = p.key(source/p.prepare_cli.PATHS[1])
        baseline = {p.key(source/'std_include.hpp')}
        includes = [*baseline,p.key(e7/'obj/community.pch'),*[p.key(source/n) for n in pins]]
        read_text = '^'+writer+'\n'+'\n'.join(includes)+'\n'
        commands = ''.join('^'+name+'\n/c /D EXPERIMENTAL_IW7 /Yu"std_include.hpp" '
                           '/Fo"C:\\e7\\obj\\'+obj+'" '+name.upper()+'\n'
                           for name,obj in ((writer,'writer.obj'),(cli,'cli.obj')))
        return {'source':source,'e7':e7,'pins':pins,'payloads':payloads,'read_text':read_text,
                'commands':commands,'baseline':baseline,'calls':[]}

    def invoke(self, f, *, corrupt_read=False, corrupt_compile=False):
        read_raw = f['read_text'].encode('utf-16'); compile_raw = f['commands'].encode('utf-16')
        def read(path, limit, expected):
            name = str(PureWindowsPath(path).relative_to(PureWindowsPath(f['source']))).replace('\\','/')
            self.assertEqual(limit,16*1024)
            self.assertEqual(expected,f['pins'][name][1])
            f['calls'].append(name)
            if name not in f['payloads']: raise FileNotFoundError(name)
            return f['payloads'][name]
        with patch.object(p,'MULTISURFACE_HEADER_PINS',f['pins']), \
             patch.object(p,'E7_READ_PIN',(len(read_raw),hashlib.sha256(read_raw).hexdigest())), \
             patch.object(p,'CL_LOG_SHA',hashlib.sha256(compile_raw).hexdigest()):
            return p.multisurface_header_inputs(f['source'],f['e7'],read_raw+(b' ' if corrupt_read else b''),
                       compile_raw+(b' ' if corrupt_compile else b''),f['baseline'],read)

    def test_exact_closure_preserves_baseline_and_reads_only_66_bounded_headers(self):
        f=self.fixture(); before=f['baseline'].copy(); pins,proof=self.invoke(f)
        self.assertEqual(f['baseline'],before)
        self.assertEqual((len(pins),sum(row['Bytes'] for row in pins)),(66,87204))
        self.assertEqual(set(f['calls']),set(f['pins']))
        self.assertTrue(proof['CompilerContextMatchesCLI'])
        self.assertEqual(proof['Inputs'],pins)
        self.assertFalse(any(PureWindowsPath(row['Path']).suffix!='.hpp' for row in pins))

    def test_each_missing_or_same_length_mutant_header_is_refused(self):
        for name in p.MULTISURFACE_HEADER_PINS:
            with self.subTest(header=name,mode='missing'):
                f=self.fixture();del f['payloads'][name]
                with self.assertRaises(FileNotFoundError):self.invoke(f)
            with self.subTest(header=name,mode='mutant'):
                f=self.fixture();f['payloads'][name]=b'y'+f['payloads'][name][1:]
                with self.assertRaisesRegex(ValueError,'header pin differs'):self.invoke(f)

    def test_missing_extra_duplicate_or_baseline_overlap_refused_before_source_reads(self):
        for mode in ('missing','extra','duplicate','overlap'):
            f=self.fixture(); header=p.key(f['source']/next(iter(f['pins'])))+'\n'
            if mode=='missing': f['read_text']=f['read_text'].replace(header,'')
            elif mode=='extra': f['read_text']+=p.key(f['source']/'unexpected.hpp')+'\n'
            elif mode=='duplicate': f['read_text']+=header
            else:f['baseline'].add(header.strip())
            with self.subTest(mode=mode),self.assertRaises(ValueError):self.invoke(f)
            self.assertEqual(f['calls'],[])

    def test_unrecorded_or_wrong_pch_cannot_be_silently_excluded(self):
        for mode in ('missing','extra','other'):
            f=self.fixture();pch=p.key(f['e7']/'obj/community.pch')+'\n'
            if mode=='missing':f['read_text']=f['read_text'].replace(pch,'')
            elif mode=='extra':f['read_text']+=p.key(f['e7']/'obj/other.pch')+'\n'
            else:f['read_text']=f['read_text'].replace(pch,pch.replace('community','other'))
            with self.subTest(mode=mode),self.assertRaisesRegex(ValueError,'known E7 PCH'):self.invoke(f)
            self.assertEqual(f['calls'],[])

    def test_different_compiler_context_or_missing_record_is_refused(self):
        for mode in ('define','include','pch','missing_record'):
            f=self.fixture()
            if mode=='define':f['commands']=f['commands'].replace('/D EXPERIMENTAL_IW7','/D OTHER',1)
            elif mode=='include':f['commands']=f['commands'].replace('/c ','/c /I"C:\\other" ',1)
            elif mode=='pch':f['commands']=f['commands'].replace('/Yu"std_include.hpp"','/Y-',1)
            else:f['commands']=f['commands'].replace('/iw7/', '/elsewhere/').replace('\\iw7\\','\\elsewhere\\')
            with self.subTest(mode=mode),self.assertRaises(ValueError):self.invoke(f)
            self.assertEqual(f['calls'],[])

    def test_stale_journal_pins_refused_before_source_reads(self):
        for mode in ('corrupt_read','corrupt_compile'):
            f=self.fixture()
            with self.subTest(mode=mode),self.assertRaisesRegex(ValueError,'Exact E7'):self.invoke(f,**{mode:True})
            self.assertEqual(f['calls'],[])

    @unittest.skipUnless(os.environ.get('IW7_T7_SOURCE') and os.environ.get('IW7_T7_E7_BUILD'),
                         'Retained text-only native source and E7 evidence not supplied')
    def test_real_headers_and_sealed_journals_extend_frozen_a_to_1146_inputs_in_memory(self):
        source=Path(os.environ['IW7_T7_SOURCE']);e7=Path(os.environ['IW7_T7_E7_BUILD'])
        plan_path=p.HERE.parents[2]/'runtime/t7-multisurface-build-plan-a/build-plan.local.json'
        raw,_=p.text_pin(plan_path,2*1024**2,'2a8c4ca3c03c5216cf07cd319150488aa2dac1562db27281d7d292055df3f297')
        plan=json.loads(raw);baseline={p.key(row['Path']) for row in plan['Inputs']}
        self.assertEqual(len(baseline),1080)
        read_raw,_=p.text_pin(e7/'obj/tlog/CL.read.1.tlog',16*1024**2,p.E7_READ_PIN[1])
        compile_raw,_=p.text_pin(e7/'obj/tlog/CL.command.1.tlog',4*1024**2,p.CL_LOG_SHA)
        pins,proof=p.multisurface_header_inputs(source,e7,read_raw,compile_raw,baseline,
                         lambda path,limit,sha:p.text_pin(path,limit,sha)[0])
        self.assertEqual(len(baseline|{p.key(row['Path']) for row in pins}),1146)
        self.assertEqual(proof['Bytes'],87204)
        self.assertFalse(Path(plan['RunRoot']).exists())


if __name__=='__main__':unittest.main()

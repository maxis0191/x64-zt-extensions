"""Fake Win32 fixtures only: no process, DLL, desktop or GUI is opened."""
import ast
import ctypes
import inspect
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import recipient_dialog as dialog
import recipient_phase as phase


class FakeWin32:
    def __init__(self):
        self.parent={'pid':os.getpid(),'parent_pid':1,'created_filetime':100,'image':r'C:\python.exe'}
        self.child={'pid':900,'parent_pid':os.getpid(),'created_filetime':200,'image':r'C:\work\zonetool.exe'}
        self.owners={10:900,20:900,21:900};self.title='Fatal Error'
        self.classes={10:'#32770',20:'Static',21:'Button'}
        self.texts={20:'Could not load fixture asset.'};self.controls=[20,21]
        self.reads=[];self.hook=None;self.saturated=set()

    def current_handle(self): return 1
    def identity(self,handle): return dict(self.parent if handle==1 else self.child)
    def window_owner(self,hwnd): return self.owners[hwnd]
    def windows(self,pid): return [10]
    def caption(self,hwnd): return self.title
    def class_name(self,hwnd): return self.classes[hwnd]
    def children(self,hwnd): return list(self.controls)
    def is_child(self,root,child): return root==10 and child in self.controls
    def static_text(self,hwnd):
        self.reads.append(hwnd)
        if self.hook: self.hook(hwnd)
        value=self.texts[hwnd]
        if isinstance(value,BaseException): raise value
        return value, hwnd in self.saturated


class DialogTests(unittest.TestCase):
    def setUp(self): self.api=FakeWin32()

    def probe(self, digest=None, clock=None):
        return dialog.FatalDialogProbe(self.api,2,900,r'C:\work\zonetool.exe','expected',r'C:\python.exe',
            digest=digest or (lambda path:'expected'),**({'clock':clock} if clock else {}))

    def test_exact_identity_static_text_and_one_capture(self):
        probe=self.probe();result=probe.poll()
        self.assertTrue(result['identity_verified_after'])
        self.assertEqual(result['controls'][0]['text'],'Could not load fixture asset.')
        self.assertEqual(result['controls'][1]['text'],'')
        self.assertEqual(self.api.reads,[20])
        self.assertIsNone(probe.poll());self.assertEqual(self.api.reads,[20])

    def test_nonfatal_window_waits_without_reading_controls(self):
        self.api.title='Loading'
        probe=self.probe();self.assertIsNone(probe.poll());self.assertEqual(self.api.reads,[])
        self.api.title='Fatal Error';self.assertIsNotNone(probe.poll())

    def test_wrong_parent_image_pid_or_creation_refuses_before_window_read(self):
        for field,value in [('pid',901),('parent_pid',4),('created_filetime',99),('image',r'C:\other.exe')]:
            with self.subTest(field=field):
                self.api=FakeWin32();self.api.child[field]=value
                with self.assertRaises(OSError): self.probe()
                self.assertEqual(self.api.reads,[])
        self.api=FakeWin32();self.api.parent['image']=r'C:\different.exe'
        with self.assertRaises(OSError): self.probe()

    def test_reused_process_identity_fails_before_poll(self):
        probe=self.probe();self.api.child['created_filetime']=201
        with self.assertRaises(OSError): probe.poll()
        self.assertEqual(self.api.reads,[])

    def test_reassigned_root_refuses_before_caption_or_controls(self):
        probe=self.probe();self.api.owners[10]=901
        with self.assertRaises(OSError): probe.poll()
        self.assertEqual(self.api.reads,[])

    def test_child_reassignment_during_read_discards_unattributed_text(self):
        probe=self.probe();self.api.hook=lambda hwnd:self.api.owners.update({hwnd:901})
        result=probe.poll()
        self.assertFalse(result['identity_verified_after'])
        self.assertEqual(result['controls'],[]);self.assertEqual(result['text_bytes'],0)

    def test_parent_replacement_after_read_discards_text(self):
        probe=self.probe();self.api.hook=lambda hwnd:self.api.parent.update(created_filetime=101)
        result=probe.poll()
        self.assertFalse(result['identity_verified_after']);self.assertEqual(result['controls'],[])

    def test_e7_hash_mismatch_before_or_after_capture_refuses_text(self):
        for values in (['bad'],['expected','bad']):
            with self.subTest(values=values):
                hashes=iter(values);probe=self.probe(digest=lambda path:next(hashes))
                result=probe.poll()
                self.assertFalse(result['identity_verified_after']);self.assertEqual(result['controls'],[])

    def test_eight_controls_and_utf8_total_bound(self):
        self.api.controls=list(range(20,50))
        for hwnd in self.api.controls:
            self.api.classes[hwnd]='Static';self.api.owners[hwnd]=900;self.api.texts[hwnd]='😀'*3000
        result=self.probe().poll()
        text=[result['title'],result['class']]+[part for c in result['controls'] for part in (c['class'],c['text'])]
        self.assertLessEqual(len(self.api.reads),8)
        self.assertEqual(sum(len(value.encode('utf-8')) for value in text),result['text_bytes'])
        self.assertLessEqual(result['text_bytes'],16*1024);self.assertTrue(result['text_truncated'])

    def test_timeout_reports_missing_body_and_still_stops_on_fatal(self):
        self.api.texts[20]=OSError('WM_GETTEXT failed or timed out (1460)')
        result=self.probe().poll()
        self.assertTrue(result['fatal_window_observed']);self.assertTrue(result['identity_verified_after'])
        self.assertEqual(result['controls'][0]['text'],'')
        self.assertIn('timed out',result['controls'][0]['error'])

    def test_soft_capture_deadline_stops_further_control_reads(self):
        ticks=iter([0,3])
        result=self.probe(clock=lambda:next(ticks)).poll()
        self.assertTrue(result['identity_verified_after']);self.assertTrue(result['text_truncated'])
        self.assertEqual(self.api.reads,[])

    def test_raw_child_enumerator_stops_at_eight_callbacks(self):
        class User:
            def EnumChildWindows(self,root,callback,unused):
                self.visited=0
                for hwnd in range(20,40):
                    self.visited+=1
                    if not callback(hwnd,0): break
        api=dialog.Win32Reader.__new__(dialog.Win32Reader);api.user=User()
        self.assertEqual(len(api.children(10)),8);self.assertEqual(api.user.visited,8)
        with self.assertRaises(OSError): api.children(0)

    def test_only_read_message_with_200ms_and_no_unbounded_timeout_flag(self):
        class User:
            def SendMessageTimeoutW(self,hwnd,message,count,buffer,flags,timeout,result):
                self.call=(hwnd,message,flags,timeout);return 1
        api=dialog.Win32Reader.__new__(dialog.Win32Reader);api.user=User()
        if not hasattr(ctypes,'set_last_error'): self.skipTest('Windows ctypes last-error API')
        self.assertEqual(api.static_text(20),('',False))
        self.assertEqual(api.user.call,(20,0x000D,0x22,200))

    def test_raw_message_result_marks_saturation_without_second_message(self):
        if not hasattr(ctypes,'set_last_error'): self.skipTest('Windows ctypes last-error API')
        for reported in (7,2046,2047,4096):
            with self.subTest(reported=reported):
                class User:
                    calls=0
                    def SendMessageTimeoutW(self,hwnd,message,count,buffer,flags,timeout,result):
                        self.calls+=1
                        value=ctypes.create_unicode_buffer('x'*min(reported,count-1))
                        ctypes.memmove(buffer,value,ctypes.sizeof(value))
                        ctypes.cast(result,ctypes.POINTER(ctypes.c_size_t)).contents.value=reported
                        return 1
                api=dialog.Win32Reader.__new__(dialog.Win32Reader);api.user=User()
                text,saturated=api.static_text(20)
                self.assertEqual(len(text),min(reported,2047))
                self.assertEqual(saturated,reported>=2047)
                self.assertEqual(api.user.calls,1)

    def test_control_saturation_propagates_below_global_text_budget(self):
        for saturated in (False,True):
            with self.subTest(saturated=saturated):
                self.api=FakeWin32();self.api.texts[20]='x'*(2047 if saturated else 7)
                if saturated: self.api.saturated.add(20)
                record=self.probe().poll()
                self.assertTrue(record['identity_verified_after'])
                self.assertLess(record['text_bytes'],dialog.TEXT_LIMIT)
                self.assertEqual(record['controls'][0]['buffer_saturated'],saturated)
                self.assertFalse(record['controls'][1]['buffer_saturated'])
                self.assertEqual(record['text_truncated'],saturated)
                self.assertEqual(self.api.reads,[20])

    def test_saved_record_is_create_new_and_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'dialog.json';record=self.probe().poll()
            dialog.save_record(path,record)
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')),record)
            with self.assertRaises(FileExistsError): dialog.save_record(path,record)
            with self.assertRaises(OSError): dialog.save_record(Path(directory)/'large.json',{'text':'x'*65536})

    def test_import_has_no_dll_load_or_process_action(self):
        tree=ast.parse(inspect.getsource(dialog))
        forbidden=('WinDLL','Popen','run','OpenProcess','TerminateProcess','PostMessageW','SetWindowTextW')
        top=ast.Module(body=[node for node in tree.body if not isinstance(node,(ast.ClassDef,ast.FunctionDef))],type_ignores=[])
        calls=[node for node in ast.walk(top) if isinstance(node,ast.Call)]
        self.assertFalse(any(getattr(node.func,'attr',None) in forbidden for node in calls))

    def test_x64_process_information_layout(self):
        if ctypes.sizeof(ctypes.c_void_p)!=8: self.skipTest('Pinned runtime is x64')
        self.assertEqual(ctypes.sizeof(dialog.BasicInformation),48)
        self.assertEqual(dialog.BasicInformation.pid.offset,32)
        self.assertEqual(dialog.BasicInformation.parent_pid.offset,40)

    def test_diagnostic_scope_and_time_refuse_before_native_launch(self):
        for changes in ({'phase':'script'},{'timeout':240},{'diagnostic_mode':'unreviewed'}):
            spec={'schema':'iw7.recipient-phase/1','phase':'references','sha256':phase.EXE_SHA,
                  'diagnostic_mode':'fatal-text','timeout':45}
            spec.update(changes)
            with self.subTest(changes=changes),mock.patch.object(phase.subprocess,'Popen') as launch:
                with self.assertRaises(ValueError): phase.run(spec,None)
                launch.assert_not_called()


class PhaseExit(BaseException):
    pass


class PhaseDialogTests(unittest.TestCase):
    """Exercise real phase policy/persistence with fake process/capture/Win32."""
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        self.work=self.root/'work';self.work.mkdir()
        self.logs=self.root/'references';self.exe=self.work/'zonetool.exe'
        self.spec={'schema':'iw7.recipient-phase/1','phase':'references','timeout':240,
                   'sha256':phase.EXE_SHA,'exe':str(self.exe),'cwd':str(self.work),'logs':str(self.logs)}
        self.api=FakeWin32();self.api.child['image']=str(self.exe)
        self.process=SimpleNamespace(pid=900,returncode=None,stdin=mock.Mock())
        self.process.poll=lambda:self.process.returncode
        self.receipts_before_exit=False;self.calls=[]

    def exercise(self, *, diagnostic=False, invalid_identity=False, expected_failure=False,
                 fake_native_exit=0, save_error=False):
        if diagnostic: self.spec.update(diagnostic_mode='fatal-text',timeout=45)
        actual_stat=Path.stat
        def fixture_stat(path,*args,**kwargs):
            if path==self.exe: return SimpleNamespace(st_size=21696512)
            return actual_stat(path,*args,**kwargs)
        def make_probe(process,image,digest):
            self.assertIs(process,self.process)
            probe=dialog.FatalDialogProbe(self.api,2,900,image,digest,r'C:\python.exe',digest=lambda path:phase.EXE_SHA)
            if invalid_identity: self.api.child['created_filetime']+=1
            return probe
        def capture(process,logs,drain,timeout,observe):
            self.assertEqual(timeout,45 if diagnostic else 240)
            (logs/'stdout.log').write_bytes(b'fixture log\n');(logs/'stderr.log').write_bytes(b'')
            self.calls.append(observe is not None)
            failure=observe() if observe else None
            self.process.returncode=fake_native_exit
            return failure,[],[]
        def exiting(code):
            self.assertEqual(code,2)
            marker='diagnostic-stop.request' if diagnostic else 'fatal-stop.request'
            record=json.loads((self.logs/'fatal-dialog.json').read_text(encoding='utf-8'))
            receipt=json.loads((self.logs/'phase.json').read_text(encoding='utf-8'))
            self.assertTrue((self.root/marker).is_file())
            self.assertTrue(receipt['failure']);self.assertIsNone(receipt['observation'])
            self.receipts_before_exit=True
            raise PhaseExit(record)
        with mock.patch.object(Path,'stat',fixture_stat),mock.patch.object(phase,'sha',return_value=phase.EXE_SHA),\
             mock.patch.object(phase,'text',return_value='fixture'),mock.patch.object(phase,'validate_requests'),\
             mock.patch.object(phase.subprocess,'Popen',return_value=self.process) as launch,\
             mock.patch.object(phase,'capture_streams',side_effect=capture),\
             mock.patch.object(dialog,'make_probe',side_effect=make_probe),\
             mock.patch.object(phase,'check_output',return_value={'closure_complete':False,'package_ready':False}) as verify,\
             mock.patch.object(phase.os,'_exit',side_effect=exiting) as exit_process:
            if save_error:
                with mock.patch.object(dialog,'save_record',side_effect=OSError('fixture write refused')):
                    with self.assertRaises(OSError): phase.run(self.spec,None)
                verify.assert_not_called();exit_process.assert_not_called()
                self.assertFalse((self.root/'fatal-stop.request').exists())
                self.assertFalse((self.logs/'phase.json').exists())
            elif expected_failure:
                with self.assertRaises(PhaseExit): phase.run(self.spec,None)
                self.assertTrue(self.receipts_before_exit);verify.assert_not_called()
            else:
                self.assertEqual(phase.run(self.spec,None),0)
                verify.assert_called_once_with(self.spec['phase'],self.work);exit_process.assert_not_called()
                self.process.stdin.close.assert_called_once()
                self.assertFalse((self.logs/'fatal-dialog.json').exists())
                self.assertFalse((self.root/'fatal-stop.request').exists())
                self.assertFalse((self.root/'diagnostic-stop.request').exists())
            launch.assert_called_once()
        self.assertEqual(self.calls,[self.spec['phase']=='references'])

    def test_normal_success_without_fatal_accepts_reference_observation(self):
        self.api.title='Loading'
        self.exercise()
        receipt=json.loads((self.logs/'phase.json').read_text(encoding='utf-8'))
        self.assertIsNone(receipt['failure']);self.assertIsNotNone(receipt['observation'])
        self.assertEqual(self.api.reads,[])

    def test_normal_fatal_saves_body_receipt_and_owned_stop_even_with_zero_exit(self):
        self.exercise(expected_failure=True)
        record=json.loads((self.logs/'fatal-dialog.json').read_text(encoding='utf-8'))
        self.assertTrue(record['identity_verified_after'])
        self.assertEqual(record['controls'][0]['text'],'Could not load fixture asset.')
        self.assertEqual(self.api.reads,[20])
        self.assertFalse((self.root/'diagnostic-stop.request').exists())

    def test_diagnostic_fatal_remains_diagnostic_only(self):
        self.exercise(diagnostic=True,expected_failure=True)
        self.assertFalse((self.root/'fatal-stop.request').exists())
        self.assertEqual(self.api.reads,[20])

    def test_diagnostic_without_fatal_cannot_accept_zero_exit(self):
        self.api.title='Loading'
        self.exercise(diagnostic=True,expected_failure=True)
        record=json.loads((self.logs/'fatal-dialog.json').read_text(encoding='utf-8'))
        self.assertFalse(record['fatal_window_observed']);self.assertFalse(record['identity_verified_after'])

    def test_normal_invalid_identity_fails_without_reading_unattributed_body(self):
        self.exercise(invalid_identity=True,expected_failure=True,fake_native_exit=None)
        record=json.loads((self.logs/'fatal-dialog.json').read_text(encoding='utf-8'))
        self.assertFalse(record['identity_verified_after']);self.assertEqual(record['errors'],['OSError'])
        self.assertEqual(self.api.reads,[])
        self.assertNotIn('controls',record)

    def test_script_phase_retains_existing_success_without_dialog_probe(self):
        self.spec['phase']='script'
        self.exercise()
        self.assertEqual(self.api.reads,[])

    def test_normal_fatal_evidence_write_failure_cannot_validate_output(self):
        self.exercise(save_error=True)


if __name__=='__main__': unittest.main()

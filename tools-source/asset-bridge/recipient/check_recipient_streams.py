"""Bounded anonymous-pipe tests using the pinned real SDK drain; no children."""
import argparse
import ast
import hashlib
import importlib.util
import inspect
import io
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest import mock

import recipient_phase as phase

DRAIN = None


class ScriptedSink:
    def __init__(self, actions):
        self.actions = iter(actions)
        self.data = bytearray()
        self.calls = 0

    def write(self, data):
        self.calls += 1
        action = next(self.actions,len(data))
        if isinstance(action,BaseException): raise action
        if type(action) is int and 0 < action <= len(data): self.data.extend(data[:action])
        return action

    def flush(self): pass


class WriteAllTests(unittest.TestCase):
    def test_unwrapped_provider_reproduces_reviewed_short_write_defect(self):
        sink=ScriptedSink([5]);failed=threading.Event()
        count=DRAIN(io.BytesIO(b'0123456789'),sink,failed)
        self.assertEqual((count,len(sink.data)),(10,5))
        self.assertFalse(failed.is_set())

    def invoke(self, data, actions):
        sink = ScriptedSink(actions)
        writer = phase.BoundedLogWriter(sink)
        failed = threading.Event()
        complete_bytes = DRAIN(io.BytesIO(data),writer,failed)
        self.assertEqual(writer.bytes_written,len(sink.data))
        return sink,writer,failed.is_set(),complete_bytes

    def test_partial_writes_complete_before_provider_counts_chunk(self):
        sink,writer,failed,count = self.invoke(b'0123456789',[5,2,3])
        self.assertFalse(failed);self.assertFalse(writer.failed)
        self.assertEqual(bytes(sink.data),b'0123456789')
        self.assertEqual((count,writer.bytes_written,sink.calls),(10,10,3))

    def test_zero_and_none_fail_without_inflating_retained_count(self):
        for invalid in (0,None):
            for prefix in (0,5):
                actions=([prefix] if prefix else [])+[invalid]
                with self.subTest(invalid=invalid,prefix=prefix):
                    sink,writer,failed,count=self.invoke(b'0123456789',actions)
                    self.assertTrue(failed);self.assertTrue(writer.failed)
                    self.assertEqual(bytes(sink.data),b'0123456789'[:prefix])
                    self.assertEqual((count,writer.bytes_written),(0,prefix))

    def test_error_after_completed_chunk_and_partial_prefix_is_failed(self):
        data=b'a'*4096+b'0123456789'
        sink,writer,failed,count=self.invoke(data,[4096,5,OSError('injected disk error')])
        self.assertTrue(failed);self.assertTrue(writer.failed)
        self.assertEqual(bytes(sink.data),data[:4101])
        # SDK counts completed chunks; receipt/adapter count retained bytes.
        self.assertEqual((count,writer.bytes_written),(4096,4101))

    def test_small_progress_retry_count_is_bounded(self):
        sink,writer,failed,count=self.invoke(b'x'*32,[1]*32)
        self.assertTrue(failed)
        self.assertEqual((sink.calls,writer.bytes_written,count),(16,16,0))

    def test_invalid_counts_fail_and_failed_writer_cannot_continue(self):
        for invalid in (-1,11,True,1.5,'5'):
            with self.subTest(invalid=invalid):
                sink,writer,failed,count=self.invoke(b'0123456789',[invalid])
                self.assertTrue(failed);self.assertEqual(count,0)
                with self.assertRaises(OSError): writer.write(b'x')
                self.assertEqual(sink.calls,1)

    def test_writer_enforces_chunk_and_total_bounds_before_writing(self):
        for data,limit in ((b'x'*4097,2097152),(b'abc',2)):
            sink=ScriptedSink([]);writer=phase.BoundedLogWriter(sink,limit=limit)
            with self.assertRaises(OSError): writer.write(data)
            self.assertTrue(writer.failed)
            self.assertEqual((sink.calls,writer.bytes_written),(0,0))

    def test_flush_error_preserves_actual_written_count_and_fails(self):
        sink=ScriptedSink([])
        def failed_flush(): raise OSError('injected flush failure')
        sink.flush=failed_flush
        writer=phase.BoundedLogWriter(sink);failed=threading.Event()
        count=DRAIN(io.BytesIO(b'prefix'),writer,failed)
        self.assertTrue(failed.is_set());self.assertTrue(writer.failed)
        self.assertEqual((count,writer.bytes_written,len(sink.data)),(0,6,6))


class PipeProcess:
    def __init__(self):
        self.code = None
        self.writers = []
        for name in ('stdout','stderr'):
            read_fd, write_fd = os.pipe()
            setattr(self,name,os.fdopen(read_fd,'rb',buffering=0))
            self.writers.append(write_fd)

    def poll(self):
        return self.code

    def write(self,index,data):
        while data:
            used = os.write(self.writers[index],data[:16384])
            data = data[used:]

    def finish(self,code=0):
        for index,fd in enumerate(self.writers):
            if fd is not None:
                os.close(fd);self.writers[index] = None
        self.code = code


class StreamTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.logs = Path(self.temp.name)
        self.process = PipeProcess()
        self.result = None
        self.errors = []

    def start(self, timeout=2, drain=None):
        def target():
            try: self.result = phase.capture_streams(self.process,self.logs,drain or DRAIN,timeout)
            except BaseException as error: self.errors.append(error)
        self.capture = threading.Thread(target=target,daemon=True)
        self.capture.start()

    def visible(self,name,size):
        deadline = time.monotonic()+1
        while time.monotonic() < deadline:
            path = self.logs/(name+'.log')
            if path.exists() and path.stat().st_size == size: return path.read_bytes()
            time.sleep(.005)
        self.fail('Short live output did not reach disk')

    def complete(self):
        self.capture.join(3)
        self.assertFalse(self.capture.is_alive())
        self.assertEqual(self.errors,[])
        self.assertIsNotNone(self.result)
        return self.result

    def tearDown(self):
        self.process.finish(122)
        if hasattr(self,'capture'):
            self.capture.join(3)
        if self.result:
            for worker in self.result[1]: worker.join(2)
            for handle in self.result[2]: handle.close()
        self.process.stdout.close();self.process.stderr.close()
        self.temp.cleanup()

    def test_production_popen_is_raw_with_unchanged_stdin(self):
        tree = ast.parse(inspect.getsource(phase.run))
        call = next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='Popen')
        keywords = {entry.arg:entry.value for entry in call.keywords}
        self.assertEqual(ast.literal_eval(keywords['bufsize']),0)
        self.assertEqual(ast.unparse(keywords['stdin']),'subprocess.PIPE')

    def test_live_small_stdout_and_stderr_before_exit(self):
        self.start()
        self.process.write(0,b'bootstrap marker\n')
        self.process.write(1,b'error detail\n')
        self.assertEqual(self.visible('stdout',17),b'bootstrap marker\n')
        self.assertEqual(self.visible('stderr',13),b'error detail\n')
        self.assertIsNone(self.process.poll())
        self.process.finish()
        failure,workers,_ = self.complete()
        self.assertIsNone(failure);self.assertTrue(all(not w.is_alive() for w in workers))

    def test_eof_preserves_short_tail_and_empty_stream(self):
        self.start()
        data = b'a'*4096+b'last 7!'
        self.process.write(0,data);self.process.finish()
        failure,_,_ = self.complete()
        self.assertIsNone(failure)
        self.assertEqual((self.logs/'stdout.log').read_bytes(),data)
        self.assertEqual((self.logs/'stderr.log').read_bytes(),b'')

    def test_cap_keeps_exact_prefix_and_reports_truncation(self):
        self.start()
        data = b'x'*(2097152+73)
        self.process.write(0,data);self.process.finish()
        failure,workers,_ = self.complete()
        for worker in workers: worker.join(1)
        self.assertIsNotNone(failure)
        self.assertEqual((self.logs/'stdout.log').read_bytes(),data[:2097152])

    def test_timeout_preserves_live_prefix_without_claiming_closure(self):
        self.start(timeout=.15)
        self.process.write(0,b'last observed progress\n')
        self.visible('stdout',23)
        failure,workers,_ = self.complete()
        self.assertEqual(failure,'phase timeout')
        self.assertIsNone(self.process.poll())
        self.assertTrue(any(worker.is_alive() for worker in workers))
        self.assertEqual((self.logs/'stdout.log').read_bytes(),b'last observed progress\n')
        # Model the OUTER original job closing its writers, never a PID kill.
        self.process.finish(122)
        for worker in workers: worker.join(1)
        self.assertTrue(all(not worker.is_alive() for worker in workers))

    def test_read_failure_is_not_successful_capture(self):
        class FailedSource:
            def read(self,size): raise OSError('injected pipe failure')
            def close(self): pass
        self.process.stdout.close()
        self.process.stdout = FailedSource()
        self.start()
        failure,_,_ = self.complete()
        self.assertEqual(failure,'log limit/drain failure')
        self.process.stdout = open(os.devnull,'rb')

    def test_real_file_partial_writes_keep_counts_and_bytes_equal(self):
        original = phase.BoundedLogWriter
        class PartialFile:
            def __init__(self,raw): self.raw=raw
            def write(self,data): return self.raw.write(data[:3])
            def flush(self): self.raw.flush()
            def fileno(self): return self.raw.fileno()
            def close(self): self.raw.close()
        with mock.patch.object(phase,'BoundedLogWriter',lambda raw:original(PartialFile(raw))):
            self.start()
            self.process.write(0,b'0123456789');self.process.finish()
            failure,_,handles=self.complete()
        self.assertIsNone(failure)
        self.assertEqual(handles[0].bytes_written,10)
        self.assertEqual((self.logs/'stdout.log').read_bytes(),b'0123456789')

    def test_real_file_error_after_prefix_is_failed_with_exact_retained_count(self):
        original=phase.BoundedLogWriter
        class FailedFile:
            def __init__(self,raw): self.raw=raw;self.calls=0
            def write(self,data):
                self.calls+=1
                if self.calls==1: return self.raw.write(data[:5])
                raise OSError('injected raw file error after prefix')
            def flush(self): self.raw.flush()
            def fileno(self): return self.raw.fileno()
            def close(self): self.raw.close()
        with mock.patch.object(phase,'BoundedLogWriter',lambda raw:original(FailedFile(raw))):
            self.start()
            self.process.write(0,b'0123456789')
            failure,_,handles=self.complete()
        self.assertEqual(failure,'log limit/drain failure')
        self.assertEqual((self.logs/'stdout.log').read_bytes(),b'01234')
        self.assertEqual(handles[0].bytes_written,5)
        self.assertEqual((self.logs/'stdout.log').stat().st_size,5)

    def test_value_error_read_after_native_zero_exit_is_failed(self):
        class FailedSource:
            def read(self,size): raise ValueError('injected read failure')
            def close(self): pass
        self.process.stdout.close()
        self.process.stdout=FailedSource()
        self.process.finish(0)
        self.start()
        failure,workers,handles=self.complete()
        self.assertEqual(failure,'stdout drain raised ValueError')
        self.assertTrue(handles[0].failed)
        self.assertEqual(handles[0].drain_exception,'ValueError')
        self.assertTrue(all(not worker.is_alive() for worker in workers))

    def test_closed_raw_pipe_value_error_is_not_clean_eof(self):
        self.process.stderr.close()
        self.process.finish(0)
        self.start()
        failure,workers,handles=self.complete()
        self.assertEqual(failure,'stderr drain raised ValueError')
        self.assertTrue(handles[1].failed)
        self.assertEqual(handles[1].bytes_written,0)
        self.assertTrue(all(not worker.is_alive() for worker in workers))

    def test_value_error_signals_owner_while_native_and_other_pipe_remain_live(self):
        class FailedSource:
            def read(self,size): raise ValueError('injected live read failure')
            def close(self): pass
        self.process.stdout.close()
        self.process.stdout=FailedSource()
        self.start(timeout=2)
        self.capture.join(1)
        self.assertFalse(self.capture.is_alive(),'Failure signal must precede phase timeout')
        failure,workers,handles=self.complete()
        self.assertEqual(failure,'stdout drain raised ValueError')
        self.assertIsNone(self.process.poll())
        self.assertTrue(handles[0].failed)
        self.assertTrue(workers[1].is_alive())

    def test_value_error_write_after_prefix_is_failed_with_retained_bytes(self):
        original=phase.BoundedLogWriter
        class FailedFile:
            def __init__(self,raw): self.raw=raw;self.calls=0
            def write(self,data):
                self.calls+=1
                if self.calls==1: return self.raw.write(data[:5])
                raise ValueError('injected write failure')
            def flush(self): self.raw.flush()
            def fileno(self): return self.raw.fileno()
            def close(self): self.raw.close()
        with mock.patch.object(phase,'BoundedLogWriter',lambda raw:original(FailedFile(raw))):
            self.process.write(0,b'0123456789');self.process.finish(0)
            self.start()
            failure,_,handles=self.complete()
        self.assertEqual(failure,'stdout drain raised ValueError')
        self.assertTrue(handles[0].failed)
        self.assertEqual(handles[0].bytes_written,5)
        self.assertEqual((self.logs/'stdout.log').read_bytes(),b'01234')

    def test_value_error_flush_is_failed_after_bytes_are_saved(self):
        original=phase.BoundedLogWriter
        class FailedFile:
            def __init__(self,raw): self.raw=raw
            def write(self,data): return self.raw.write(data)
            def flush(self): raise ValueError('injected flush failure')
            def fileno(self): return self.raw.fileno()
            def close(self): self.raw.close()
        with mock.patch.object(phase,'BoundedLogWriter',lambda raw:original(FailedFile(raw))):
            self.process.write(1,b'prefix');self.process.finish(0)
            self.start()
            failure,_,handles=self.complete()
        self.assertEqual(failure,'stderr drain raised ValueError')
        self.assertTrue(handles[1].failed)
        self.assertEqual(handles[1].bytes_written,6)
        self.assertEqual((self.logs/'stderr.log').read_bytes(),b'prefix')

    def test_system_exit_in_worker_fails_instead_of_silent_termination(self):
        def exit_drain(source,destination,failed): raise SystemExit(0)
        self.process.finish(0)
        self.start(drain=exit_drain)
        failure,workers,handles=self.complete()
        self.assertEqual(failure,'stdout drain raised SystemExit; stderr drain raised SystemExit')
        self.assertTrue(all(handle.failed for handle in handles))
        self.assertTrue(all(not worker.is_alive() for worker in workers))

    def test_exception_during_drain_finalization_cannot_accept_saved_output(self):
        class UnprintableError(RuntimeError):
            def __str__(self): raise ValueError('exception formatting also failed')
        def finalizing_drain(source,destination,failed):
            try: DRAIN(source,destination,failed)
            finally: raise UnprintableError()
        self.process.write(0,b'complete stdout');self.process.write(1,b'complete stderr')
        self.process.finish(0)
        self.start(drain=finalizing_drain)
        failure,workers,handles=self.complete()
        self.assertEqual(failure,'stdout drain raised UnprintableError; stderr drain raised UnprintableError')
        self.assertTrue(all(handle.failed for handle in handles))
        self.assertTrue(all(not worker.is_alive() for worker in workers))
        self.assertEqual((self.logs/'stdout.log').read_bytes(),b'complete stdout')
        self.assertEqual((self.logs/'stderr.log').read_bytes(),b'complete stderr')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-drain',required=True,type=Path)
    args = parser.parse_args()
    if hashlib.sha256(args.sdk_drain.read_bytes()).hexdigest() != phase.SDK_DRAIN_SHA:
        raise ValueError('Exact unchanged SDK drain required')
    spec = importlib.util.spec_from_file_location('sdk_drain',args.sdk_drain)
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    DRAIN = module.copy_bounded
    unittest.main(argv=[__file__],verbosity=2)

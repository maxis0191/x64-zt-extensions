"""Bounded anonymous-pipe tests using the pinned real SDK drain; no children."""
import argparse
import ast
import hashlib
import importlib.util
import inspect
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest

import recipient_phase as phase

DRAIN = None


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

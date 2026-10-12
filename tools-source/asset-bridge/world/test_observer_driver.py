"""Driver logic with fake processes and original bytes; never starts a process."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import observer_harness_driver as driver

ROOT = Path(__file__).resolve().parent
SDK = ROOT.parents[2] / 'sdk/modding/beacon_tool_phase.py'


class FakeProcess:
    pid = 37
    def __init__(self, code=0, polls=0, output=b'original fixture\n'):
        self.returncode = code if not polls else None
        self.code, self.remaining = code, polls
        self.stdout, self.stderr = io.BytesIO(output), io.BytesIO(b'')
    def poll(self):
        if self.remaining:
            self.remaining -= 1
            return None
        self.returncode = self.code
        return self.returncode


class UnformattableError(ValueError):
    def __str__(self):
        raise AssertionError('Worker exception formatting is forbidden')


class UnformattableExit(SystemExit):
    def __str__(self):
        raise AssertionError('Worker exit formatting is forbidden')


class FaultyStream:
    def __init__(self, stream, operation, exception):
        self.stream, self.operation, self.exception = stream, operation, exception
    def invoke(self, operation, *args):
        if operation == self.operation:
            raise self.exception()
        return getattr(self.stream, operation)(*args)
    def read(self, count):
        return self.invoke('read', count)
    def write(self, data):
        return self.invoke('write', data)
    def flush(self):
        return self.invoke('flush')
    def close(self):
        self.stream.close()


class DriverChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='.world-driver-test-', dir=ROOT)
        self.root = Path(self.temp.name)
        self.exe = self.root / 'original.exe'; self.exe.write_bytes(b'original nonexecutable bytes')
        self.sha = driver.digest(self.exe); self.calls = 0; self.now = 0
        self.drain = driver.load_drain(SDK, 'a2ab493cf551a43eea3797e5e8437e41aa8f0246d770838956d8984b68c4701d')
        self.process = FakeProcess()
    def tearDown(self):
        self.temp.cleanup()
    def popen(self, argv, **kwargs):
        self.calls += 1
        self.assertEqual(argv, [str(self.exe)])
        self.assertNotIn('CL', kwargs['env']); self.assertNotIn('_CL_', kwargs['env'])
        self.assertEqual(kwargs['cwd'], self.root)
        return self.process
    def sleep(self, _seconds):
        self.now += 1
    def run_fake(self, **kwargs):
        return driver.run_phase('fixture', self.exe, [], self.sha, self.root, self.drain, 0,
                                clock=lambda: self.now, sleep=self.sleep, popen=self.popen, **kwargs)
    def test_success_one_original_launch_and_receipt(self):
        receipt = self.run_fake()
        self.assertEqual(self.calls, 1); self.assertEqual(receipt['exit_code'], 0)
        self.assertIsNone(receipt['failure'])
        self.assertEqual((self.root/'fixture.stdout.log').read_bytes(), b'original fixture\n')
    def test_exact_phase_group_boundaries(self):
        driver.deadline(89.999, 0, 0, 'compile'); driver.deadline(119.999, 0, 110, 'fixture')
        for values in [(90, 0, 0, 'compile'), (10, 0, 0, 'fixture'), (120, 0, 119, 'fixture'),
                       (-1, 0, 0, 'compile'), (1, 0, 0, 'other')]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                driver.deadline(*values)
    def test_live_timeout_no_retry_or_kill(self):
        self.process = FakeProcess(polls=100)
        with self.assertRaisesRegex(ValueError, 'phase deadline'):
            self.run_fake()
        self.assertEqual(self.calls, 1)
        self.assertIsNone(driver.read_json(self.root/'fixture.json')['exit_code'])
    def test_late_exit_is_not_success(self):
        self.process = FakeProcess(polls=10)
        with self.assertRaisesRegex(ValueError, 'phase deadline'):
            self.run_fake()
        self.assertEqual(self.calls, 1)
    def test_nonzero_and_pin_refusal(self):
        self.exe.write_bytes(b'changed original bytes')
        with self.assertRaisesRegex(ValueError, 'pin differs'):
            self.run_fake()
        self.assertEqual(self.calls, 0)
        self.sha = driver.digest(self.exe); self.process = FakeProcess(code=7)
        with self.assertRaisesRegex(ValueError, 'nonzero'):
            self.run_fake()
        self.assertEqual(self.calls, 1)
    def test_pinned_drain_and_output_bound(self):
        with self.assertRaisesRegex(ValueError, 'drain pin'):
            driver.load_drain(SDK, '0'*64)
        self.process = FakeProcess(output=b'x'*17)
        original = self.drain
        self.drain = lambda source, target, exceeded: original(source, target, exceeded, 16)
        with self.assertRaisesRegex(ValueError, 'Drain failure'):
            self.run_fake()
        self.assertEqual((self.root/'fixture.stdout.log').stat().st_size, 16)
    def test_protocol_limits_duplicates_and_no_overwrite(self):
        path = self.root/'one.json'; driver.publish(path, {'original': True})
        self.assertEqual(driver.read_json(path), {'original': True})
        with self.assertRaises(ValueError):
            driver.publish(path, {'original': False})
        self.assertEqual(driver.read_json(path), {'original': True})
        path.write_text('{"x":1,"x":2}')
        with self.assertRaises(ValueError):
            driver.read_json(path)
        path.write_bytes(b'x'*65537)
        with self.assertRaises(ValueError):
            driver.read_json(path)

    def test_permit_token_and_exact_compiled_hash(self):
        spec = {'token': 'a'*64}
        permit = {'schema': 'iw7.world-observer-permit/1', 'token': spec['token'], 'fixture_sha256': self.sha}
        driver.validate_permit(permit, spec, self.sha)
        for key, value in [('schema', 'other'), ('token', 'b'*64), ('fixture_sha256', '0'*64)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                driver.validate_permit({**permit, key: value}, spec, self.sha)
        self.assertEqual(self.calls, 0)

    def test_guarded_drain_fault_matrix_never_accepts_zero_exit(self):
        # stdout/stderr x read/write/flush x ordinary/BaseException. The real
        # pinned drain catches only OSError, so every case needs the local guard.
        for stream_name in ('stdout', 'stderr'):
            for operation in ('read', 'write', 'flush'):
                for exception in (UnformattableError, UnformattableExit):
                    with self.subTest(stream=stream_name, operation=operation, exception=exception.__name__):
                        root = self.root / f'{stream_name}-{operation}-{exception.__name__}'
                        root.mkdir()
                        process = FakeProcess()
                        process.stderr = io.BytesIO(b'original stderr fixture\n')
                        if operation == 'read':
                            setattr(process, stream_name, FaultyStream(getattr(process, stream_name), operation, exception))
                        actual_open = Path.open
                        def open_fault(path, *args, **kwargs):
                            opened = actual_open(path, *args, **kwargs)
                            if path == root / f'fixture.{stream_name}.log' and operation != 'read':
                                return FaultyStream(opened, operation, exception)
                            return opened
                        calls = []
                        def fake_popen(*args, **kwargs):
                            calls.append(args)
                            return process
                        with patch.object(Path, 'open', open_fault), patch('threading.excepthook') as escaped:
                            with self.assertRaisesRegex(ValueError, 'Drain failure'):
                                driver.run_phase('fixture', self.exe, [], self.sha, root, self.drain, 0,
                                                 clock=lambda: 0, popen=fake_popen)
                            escaped.assert_not_called()
                        receipt = driver.read_json(root / 'fixture.json')
                        self.assertEqual(receipt['exit_code'], 0)
                        self.assertEqual(receipt['failure'], 'Drain failure or inherited pipe')
                        self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()

"""Literal environment/command and failure tests: Popen/job calls are mocked."""
import copy
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from rig_phase import PHASES, parse, run, validate, load_drain, main


class PhaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.exe = self.root / 'mock-not-an-executable.bin'
        self.exe.write_bytes(b'original mocked executable bytes')
        self.spec = {'schema': 'iw7.rig-chain-phase-spec/1', 'phase': 'compile',
                     'exe': str(self.exe), 'sha256': hashlib.sha256(self.exe.read_bytes()).hexdigest(),
                     'arguments': ['/nologo', 'literal argument with spaces'], 'cwd': str(self.root),
                     'logs': str(self.root / 'logs'), 'timeout': 120,
                     'environment': {'SystemRoot': str(self.root), 'WINDIR': str(self.root),
                                     'PATH': str(self.root), 'TEMP': str(self.root), 'TMP': str(self.root),
                                     'INCLUDE': str(self.root), 'LIB': str(self.root),
                                     'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1'}}
        self.process = Mock(pid=37, returncode=0, stdout=io.BytesIO(b'original output'), stderr=io.BytesIO(b''))
        self.process.poll.return_value = 0
        self.popen = Mock(return_value=self.process)
        self.job = Mock()

    @staticmethod
    def drain(source, target, exceeded):
        target.write(source.read())

    def execute(self, **kwargs):
        return run(self.spec, 'a' * 64, kwargs.pop('drain', self.drain),
                   ensure_job=self.job, popen=self.popen, **kwargs)

    def test_literal_argv_explicit_environment_and_receipt(self):
        environment = dict(os.environ)
        code, receipt = self.execute()
        self.assertEqual(code, 0)
        self.assertEqual(receipt['spec_sha256'], 'a' * 64)
        self.assertEqual(receipt['pid'], 37)
        self.assertEqual(receipt['ownership'], 'outer original Windows job')
        self.assertEqual(json.loads((self.root / 'logs/phase.json').read_text()), receipt)
        self.assertEqual(self.popen.call_args.args[0], [str(self.exe), *self.spec['arguments']])
        kwargs = self.popen.call_args.kwargs
        self.assertEqual(kwargs['env'], self.spec['environment'])
        self.assertNotIn('shell', kwargs)
        self.assertNotIn('CL', kwargs['env'])
        self.assertNotIn('PYTHONPATH', kwargs['env'])
        self.assertEqual(dict(os.environ), environment)
        self.job.assert_called_once_with()

    def test_nonzero_native_exit_is_failure(self):
        self.process.poll.return_value = 7
        self.process.returncode = 7
        code, receipt = self.execute()
        self.assertEqual(code, 1)
        self.assertEqual(receipt['exit_code'], 7)

    def test_deadline_has_no_child_pid_termination(self):
        self.process.poll.return_value = None
        self.process.returncode = None
        code, receipt = self.execute(clock=Mock(side_effect=[0, 121]), sleep=Mock())
        self.assertEqual(code, 2)
        self.assertEqual(receipt['failure'], 'phase timeout')
        self.process.kill.assert_not_called()
        self.process.terminate.assert_not_called()

    def test_drain_failure_is_recorded(self):
        def bad_drain(source, target, exceeded):
            exceeded.set()
        code, receipt = self.execute(drain=bad_drain)
        self.assertEqual(code, 2)
        self.assertIn('drain failed', receipt['failure'])

    def test_no_job_no_popen_or_output(self):
        self.job.side_effect = ValueError('no job')
        with self.assertRaisesRegex(ValueError, 'no job'):
            self.execute()
        self.popen.assert_not_called()
        self.assertFalse((self.root / 'logs').exists())

    def test_changed_executable_and_existing_logs_refused(self):
        self.spec['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'executable changed'):
            self.execute()
        self.spec['sha256'] = hashlib.sha256(self.exe.read_bytes()).hexdigest()
        (self.root / 'logs').mkdir()
        with self.assertRaisesRegex(ValueError, 'fresh phase'):
            self.execute()
        self.popen.assert_not_called()

    def test_inherited_injection_variables_refused(self):
        for key in ('CL', '_CL_', 'PYTHONPATH', 'PYTHONHOME', 'LIBPATH', 'CC'):
            bad = copy.deepcopy(self.spec)
            bad['environment'][key] = 'injected'
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'exact explicit'):
                validate(bad)

    def test_fixed_phases_and_timeouts(self):
        for phase, timeout in PHASES.items():
            candidate = {**self.spec, 'phase': phase, 'timeout': timeout}
            validate(candidate)
            for wrong in (True, str(timeout), timeout + 1, 0):
                candidate['timeout'] = wrong
                with self.assertRaisesRegex(ValueError, 'fixed rig timeout'):
                    validate(candidate)

    def test_bad_schema_unknown_phase_and_extra_fields(self):
        for fields in ({'schema': 'other'}, {'phase': 'shell'}, {'unbound': True}):
            with self.assertRaises(ValueError):
                validate({**self.spec, **fields})

    def test_bad_argument_types_and_controls(self):
        for args in ([], [''] , ['a\nb'], ['a\0b'], [None], ['a'] * 65, ['x'] * 32769, 'not a list'):
            with self.assertRaises(ValueError):
                validate({**self.spec, 'arguments': args})

    def test_relative_paths_and_unsafe_environment_refused(self):
        for key in ('exe', 'cwd', 'logs'):
            with self.assertRaises(ValueError):
                validate({**self.spec, key: 'relative'})
        for key, value in (('TEMP', 'relative'), ('WINDIR', 'elsewhere'), ('PATH', ''),
                           ('INCLUDE', ''), ('LIB', '\n'), ('PYTHONNOUSERSITE', '0')):
            bad = copy.deepcopy(self.spec)
            bad['environment'][key] = value
            with self.assertRaises(ValueError):
                validate(bad)

    def test_duplicate_json_and_nan_refused(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}'):
            with self.assertRaises(ValueError):
                parse(raw)

    def test_unreviewed_drain_is_never_imported(self):
        source = self.root / 'unreviewed.py'
        source.write_text('raise RuntimeError("must never import")')
        with self.assertRaisesRegex(ValueError, 'pinned shared drain'):
            load_drain(source)

    def test_bootstrap_collision_retains_original_error_without_phase_receipt(self):
        (self.root / 'logs').mkdir()
        spec_file = self.root / 'build.spec.json'
        raw = json.dumps(self.spec).encode()
        spec_file.write_bytes(raw)
        spec_hash = hashlib.sha256(raw).hexdigest()
        def mocked_run(spec, digest, drain):
            return run(spec, digest, drain, ensure_job=self.job, popen=self.popen)
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = main(['--spec', str(spec_file), '--spec-sha256', spec_hash, '--sdk-phase', str(self.root / 'unused.py')],
                        runner=mocked_run, drain_loader=Mock(return_value=self.drain))
        self.assertEqual(code, 2)
        self.assertFalse((self.root / 'logs/phase.json').exists())
        report = json.loads(spec_file.with_suffix('.launch-error.json').read_text())
        self.assertEqual(report['error'], 'fresh phase log directory required')
        self.assertEqual(report['spec_sha256'], spec_hash)
        self.assertEqual(report['root_pid'], os.getpid())
        self.assertIn(report['error'], stderr.getvalue())
        self.popen.assert_not_called()

    def test_launch_error_never_overwrites_existing_evidence(self):
        spec_file = self.root / 'build.spec.json'
        raw = json.dumps(self.spec).encode()
        spec_file.write_bytes(raw)
        error_file = spec_file.with_suffix('.launch-error.json')
        error_file.write_text('original evidence')
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = main(['--spec', str(spec_file), '--spec-sha256', hashlib.sha256(raw).hexdigest(),
                         '--sdk-phase', str(self.root / 'unused.py')],
                        runner=Mock(side_effect=OSError('initial disk refusal')), drain_loader=Mock())
        self.assertEqual(code, 2)
        self.assertEqual(error_file.read_text(), 'original evidence')
        self.assertIn('initial disk refusal', stderr.getvalue())
        self.assertIn('Could not retain launch error', stderr.getvalue())


if __name__ == '__main__':
    unittest.main()

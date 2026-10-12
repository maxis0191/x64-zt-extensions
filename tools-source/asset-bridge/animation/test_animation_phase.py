"""Pure tests: no process, native import, FF work, or resource reservation."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import animation_tool_phase
from animation_tool_phase import phase_command, pinned


class AnimationPhaseTests(unittest.TestCase):
    def test_fixed_native_profile(self):
        for phase, verb in [('build', '-buildzone'), ('verify', '-verifyzone'), ('dump', '-dumpzone')]:
            with self.subTest(phase=phase):
                self.assertEqual(phase_command(phase, 'tool.exe', 'unused.py', 'unused.xab'),
                                 ['tool.exe', '-headless', '-unbuffered-io', '-strict-content-sources', verb, 'sdk_animation_probe'])

    def test_reader_uses_ff_string_table_profile(self):
        self.assertEqual(phase_command('read', 'python.exe', Path('a/read_probe.py'), 'b/redump.xab'),
                         ['python.exe', '-B', str(Path('a/read_probe.py')), 'b/redump.xab', '--expected-frequency', '1', '--ff-roundtrip'])

    def test_unknown_native_operation_refused(self):
        with self.assertRaises(KeyError):
            phase_command('launch-game', 'tool.exe', '', '')

    def test_source_binding_and_inclusive_size_limit(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'source.py'
            data = b'x' * 128
            path.write_bytes(data)
            sha = hashlib.sha256(data).hexdigest()
            self.assertEqual(pinned(path, sha.upper(), 128), path.resolve())
            with self.assertRaises(ValueError):
                pinned(path, '0' * 64, 128)
            with self.assertRaises(ValueError):
                pinned(path, sha, 127)

    def test_missing_source_refused(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(FileNotFoundError):
                pinned(Path(root) / 'missing.py', '0' * 64, 128)

    def test_shared_entrypoint_receives_only_profile_override_and_remaining_args(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / 'shared.py'
            source.write_text("import sys\ndef main():\n    return command('dump', 'tool.exe', 'work', 'dump.xab'), list(sys.argv)\n", encoding='utf-8')
            reader = Path(animation_tool_phase.__file__).with_name('read_probe.py')
            args = ['adapter.py', '--shared-adapter', str(source), '--shared-sha256', hashlib.sha256(source.read_bytes()).hexdigest(),
                    '--reader-sha256', hashlib.sha256(reader.read_bytes()).hexdigest(), '--phase', 'dump', '--exe', 'tool.exe']
            with patch.object(sys, 'argv', args):
                command, forwarded = animation_tool_phase.main()
            self.assertEqual(command[-2:], ['-dumpzone', 'sdk_animation_probe'])
            self.assertEqual(forwarded, [str(source.resolve()), '--phase', 'dump', '--exe', 'tool.exe'])

    def test_hash_mismatch_refuses_shared_code_before_import(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / 'shared.py'
            source.write_text("raise AssertionError('must never import')\n", encoding='utf-8')
            args = ['adapter.py', '--shared-adapter', str(source), '--shared-sha256', '0' * 64, '--reader-sha256', '0' * 64]
            with patch.object(sys, 'argv', args), self.assertRaises(ValueError):
                animation_tool_phase.main()


if __name__ == '__main__':
    unittest.main()

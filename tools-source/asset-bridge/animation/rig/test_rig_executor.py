"""Light Windows PowerShell mocks; deliberately no native/compiler execution."""
import os
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(os.name == 'nt', 'Windows ownership source contracts')
class ExecutorMockTests(unittest.TestCase):
    def powershell(self):
        pwsh = shutil.which('pwsh')
        if not pwsh:
            bundled = Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
            if bundled.is_file():
                pwsh = str(bundled)
        self.assertTrue(pwsh, 'PowerShell 7 is required for rig source/mocked checks')
        return pwsh

    def test_three_powershell_source_and_mock_suites(self):
        pwsh = self.powershell()
        root = Path(__file__).absolute().parent
        for name in ('test_rig_compiler.ps1', 'test_rig_runner.ps1', 'test_rig_owned_phase.ps1'):
            with self.subTest(script=name):
                result = subprocess.run([pwsh, '-NoProfile', '-NonInteractive', '-File', str(root / name)],
                                        capture_output=True, text=True, timeout=45, check=False)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('PASS:', result.stdout)

    def test_independent_reader_results_bound_to_actual_synthetic_artifacts(self):
        from test_rig_chain import data
        from test_clip_rig import clip_bytes
        from read_rig_chain import MODELS, verify_chain
        files, manifest, pairs = data()
        native_clip, redump_clip = clip_bytes(), clip_bytes(4036)
        report = verify_chain(files, manifest, pairs, native_clip, pairs, redump_clip)
        with tempfile.TemporaryDirectory(prefix='iw7-rig-readback-') as folder:
            root = Path(folder)
            staged, retained = [], []
            for profile, name in MODELS.items():
                for (kind, filename), payload in zip((('xmodel', name + '.xmb'), ('xsurface', name + '_lod0.xsb')), pairs[profile]):
                    relative = kind + '/' + filename
                    source = root / 'native' / profile / relative
                    redump = root / 'roundtrip' / relative
                    for file in (source, redump):
                        file.parent.mkdir(parents=True, exist_ok=True)
                        file.write_bytes(payload)
                    staged.append({'relative': relative, 'source': str(source)})
                    retained.append({'retained': str(redump)})
            relative = 'xanim/paris_original_probe_bend.xab'
            source, redump = root / 'native' / relative, root / 'roundtrip' / relative
            for path, payload in ((source, native_clip), (redump, redump_clip)):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)
            staged.append({'relative': relative, 'source': str(source)})
            retained.append({'retained': str(redump)})
            fixture = root / 'fixture.json'
            fixture.write_text(json.dumps({'report': report, 'plan': {'run_root': str(root),
                               'staged_profile_inputs': staged, 'retain_redumps_before_restore': retained}}), encoding='utf-8')
            script = Path(__file__).absolute().parent / 'test_rig_readback.ps1'
            result = subprocess.run([self.powershell(), '-NoProfile', '-NonInteractive', '-File', str(script),
                                     '-Fixture', str(fixture)], capture_output=True, text=True, timeout=45, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('PASS: 18 ', result.stdout)


if __name__ == '__main__':
    unittest.main()

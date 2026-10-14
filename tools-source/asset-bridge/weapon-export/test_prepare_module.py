import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import prepare_module as support


FIXTURE = ('#include "zonetool.hpp"\nnamespace zonetool::iw7\n{\n'
    '\tvoid load_enemy_source_zones(const std::string& donor_zone);\n'
    + support.ANCHOR + '\n\t\tload_zone(donor_zone);\n\t}\n'
    '\tvoid unchanged_cli() { original_command(); }\n}\n')
FIXTURE_SHA = hashlib.sha256(FIXTURE.encode()).hexdigest()


class PreparationTests(unittest.TestCase):
    def test_inactive_support_preserves_source_and_entry(self):
        result, module = support.wire_module(FIXTURE, FIXTURE_SHA)
        addition = '\n'.join('\t' + line if line else '' for line in module.splitlines()) + '\n\n'
        without_module = result.replace(addition, '', 1).replace(
            '#include <array>\n#include <cmath>\n#include <fstream>\n#include <sstream>\n', '', 1)
        self.assertEqual(without_module, FIXTURE)
        self.assertEqual(result.count('void ' + support.FUNCTION + '('), 1)
        self.assertEqual(result.count(support.FUNCTION), 1)  # no call-site introduced

    def test_source_drift_refused_even_with_same_anchor(self):
        with self.assertRaisesRegex(ValueError, 'Pinned IW7 source changed'):
            support.wire_module(FIXTURE.replace('original_command', 'new_command'), FIXTURE_SHA)

    def test_wrong_namespace_and_missing_or_duplicate_anchor(self):
        for source in (FIXTURE.replace('zonetool::iw7', 'zonetool::t7'),
                       FIXTURE.replace(support.ANCHOR, ''), FIXTURE + support.ANCHOR):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, 'insertion site'):
                support.wire_module(source, hashlib.sha256(source.encode()).hexdigest())

    def test_already_inserted_module_refused(self):
        changed = FIXTURE + '\n// ' + support.FUNCTION
        with self.assertRaisesRegex(ValueError, 'insertion site'):
            support.wire_module(changed, hashlib.sha256(changed.encode()).hexdigest())

    def test_growth_capped_before_decode_or_hash(self):
        class Growth(io.BytesIO):
            def read(self, count=-1):
                self.requested = count
                return super().read(count)
        growth = Growth(b'\xff' * (support.CAP + 1024))
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'small.cpp'
            path.write_bytes(b'tiny')
            with patch.object(Path, 'open', return_value=growth):
                with self.assertRaisesRegex(ValueError, 'Source cap exceeded'):
                    support.read_source(path)
        self.assertEqual(growth.requested, support.CAP + 1)

    def test_bom_crlf_are_normalized(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'source.cpp'
            path.write_bytes(b'\xef\xbb\xbf' + FIXTURE.replace('\n', '\r\n').encode())
            self.assertEqual(support.read_source(path), FIXTURE)

    def test_real_source_outputs_and_overwrite_refusal(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            source = root / 'native' / support.NATIVE_PATH
            source.parent.mkdir(parents=True)
            source.write_text(FIXTURE, encoding='utf-8')
            output = root / 'staged'
            original_wire = support.wire_module
            with patch.object(support, 'wire_module', side_effect=lambda t: original_wire(t, FIXTURE_SHA)):
                report = support.stage(root / 'native', output)
            staged = (output / support.NATIVE_PATH).read_text(encoding='utf-8')
            manifest = json.loads((output / 'module-source.json').read_text())
            self.assertEqual(report, manifest)
            self.assertEqual(manifest['staged_lf_sha256'], hashlib.sha256(staged.encode()).hexdigest())
            self.assertFalse(any(manifest[k] for k in ('cli_wired', 'compiled',
                'native_export_executed', 'full_templates_observed', 'ready')))
            with self.assertRaisesRegex(ValueError, 'Fresh ordinary absolute'):
                support.stage(root / 'native', output)

    def test_relative_and_linked_output_refused_before_source_read(self):
        with self.assertRaisesRegex(ValueError, 'Fresh ordinary absolute'):
            support.stage('not_read', Path('relative'))
        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / 'new'
            with patch.object(Path, 'is_junction', return_value=True):
                with self.assertRaisesRegex(ValueError, 'Fresh ordinary absolute'):
                    support.stage('not_read', output)


if __name__ == '__main__':
    unittest.main()

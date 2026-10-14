"""Actual source renderer and fixed native guards; no CPP, engine or game bytes."""
import hashlib
import json
import os
import re
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import prepare_build as build
import prepare_image_metadata as metadata
import prepare_image_provenance as provenance
from test_image_provenance import ProvenanceTransitionTests


class MetadataSourceTests(unittest.TestCase):
    @staticmethod
    def cli_guard(cli, selector):
        tail = cli.split('const bool '+selector+' =', 1)[1].split('\n', 1)[1]
        return tail.split('throw std::runtime_error(', 1)[0].strip()

    @staticmethod
    def python_predicate(statement):
        if not statement.startswith('if (') or not statement.endswith(')'):
            raise ValueError('Complete C++ if statement required')
        expression = statement[4:-1]
        expression = re.sub(r'utils::flags::has_flag\("([^"]+)"\)',
                            lambda match: repr(match[1])+' in flags', expression)
        return '('+expression.replace('&&', ' and ').replace('||', ' or ').replace('!', 'not ')+')'

    @unittest.skipUnless(os.environ.get('IW7_T7_SOURCE'), 'Exact retained native SOURCE not supplied')
    def test_rendered_cli_guards_parse_refuse_mixed_modes_and_reproduce_failed_c(self):
        base = ProvenanceTransitionTests()
        main, cli = base.base()
        f2main, f2cli, _ = provenance.overlay(main, cli, base.read)
        new_main, new_cli, _ = metadata.overlay(f2main, f2cli, base.read)
        failed_c_cli = new_cli
        for selector, option, surplus in (
                ('image_metadata', 't7-iw7-image-metadata-v1', 1),
                ('provenance', 't7-iw7-image-provenance-v1', 2)):
            statement = self.cli_guard(new_cli, selector)
            self.assertEqual(new_cli.count(statement), 1)
            depth = 0
            for character in statement:
                depth += (character == '(') - (character == ')')
                self.assertGreaterEqual(depth, 0, 'Unmatched rendered C++ guard terminator')
            self.assertEqual(depth, 0)
            predicate = compile(self.python_predicate(statement), '<rendered CLI guard>', 'eval')
            def refused(selected, flags):
                return eval(predicate, {'__builtins__': {}}, {selector: selected, 'flags': flags})
            self.assertFalse(refused(True, {option}), 'Exact exclusive selection must remain usable')
            self.assertTrue(refused(False, {option}), 'Malformed selected argv must refuse')
            self.assertFalse(refused(False, set()), 'Unselected legacy mode must remain untouched')
            exclusions = set(re.findall(r'has_flag\("([^"]+)"\)', statement)) - {option}
            self.assertEqual(len(exclusions), 10)
            for other in exclusions:
                self.assertTrue(refused(True, {option, other}), 'Every mixed mode must refuse')
            # Reverse only the three actual extra terminators and recover the
            # exact source compiled in failed C, rather than a lookalike case.
            failed_statement = statement + ')' * surplus
            with self.assertRaises(SyntaxError):
                compile(self.python_predicate(failed_statement), '<failed C guard>', 'eval')
            failed_c_cli = failed_c_cli.replace(statement, failed_statement, 1)
        self.assertEqual(provenance.pin(failed_c_cli.encode()),
                         (154459, 'd9d3296d79ec5c33e969b773ad124c7e4cf977226e12de7593af278353d29d6e'))
        self.assertEqual(provenance.pin(new_main.encode()),
                         (43482, 'b786f2db40e4c70346846bccb336c86c957efbd76f1c9365994138119a4e4363'))

    def test_exclusive_extension_selection_before_prepare_io(self):
        self.assertFalse(metadata.selected(SimpleNamespace()))
        self.assertTrue(metadata.selected(SimpleNamespace(image_metadata_v1=True, image_provenance_v1=True)))
        for values in ({'image_metadata_v1': 1}, {'image_metadata_v1': 'true'},
                       {'image_metadata_v1': True}, {'image_metadata_v1': True, 'image_provenance_v1': 1}):
            with self.assertRaises(ValueError):
                metadata.selected(SimpleNamespace(**values))
        with patch.object(build, 'path_checked', side_effect=AssertionError('Preparation IO reached')) as read:
            with self.assertRaises(ValueError):
                build.prepare(SimpleNamespace(image_metadata_v1=True))
            read.assert_not_called()

    def test_finite_cap_preserves_legacy_and_f2_limits(self):
        payload = {'source': b'x'*(288*1024+1)}
        with self.assertRaises(ValueError):
            build.require_preparation_bounds(b'{}', payload, provenance_profile=True)
        build.require_preparation_bounds(b'{}', payload, provenance_profile=True, metadata_profile=True)
        with self.assertRaises(ValueError):
            build.require_preparation_bounds(b'{}', payload, metadata_profile=True)
        with self.assertRaises(ValueError):
            build.require_preparation_bounds(b'{}', {'source': b'x'*(320*1024+1)},
                                             provenance_profile=True, metadata_profile=True)

    def test_actual_native_scope_and_reused_guard_order(self):
        entry = (metadata.HERE/'native_image_metadata.inc').read_text()
        predicate = entry.split('if (', 1)[1].split(')\n', 1)[0].replace('||', ' or ')
        for zone, model, lod, refused in [('mp_freerun_04', 'p7_fre_platform_cap_02', '0', False),
                                        ('cp_zmb', 'p7_fre_platform_cap_02', '0', True),
                                        ('mp_freerun_04', 'wrong', '0', True),
                                        ('mp_freerun_04', 'p7_fre_platform_cap_02', '00', True)]:
            self.assertEqual(eval(predicate, {'__builtins__': {}},
                                  dict(zone_arg=zone, model_arg=model, lod_arg=lod)), refused)
        self.assertEqual(entry.count('db_find_x_asset_header('), 1)
        self.assertIn('DB_IsXAssetDefault(ASSET_TYPE_XMODEL', entry)
        self.assertLess(entry.index('DB_IsXAssetDefault('), entry.index('.finish(model)'))
        self.assertLess(entry.index('.finish(model)'), entry.index('selected_image_metadata::observe('))
        self.assertLess(entry.index('ZONETOOL_INFO('), entry.index('report.at("refused")'))
        self.assertNotIn('ASSET_TYPE_IMAGE', entry)
        wrapper = (metadata.HERE/'selected_image_metadata.hpp').read_text()
        self.assertLess(wrapper.index('provenance.at("capture_complete")'), wrapper.index('base::observe_binding('))
        self.assertLess(wrapper.index('capture.count == 2'), wrapper.index('scalar_api::build('))
        self.assertLess(wrapper.index('base::image_metadata(capture.headers[0])'), wrapper.index('scalar_api::build('))
        self.assertIn('capture.range(pointer, bytes)', wrapper)
        self.assertIn('std::memcmp(&capture.headers[0], &capture.headers[1], sizeof(GfxImage))', wrapper)
        self.assertIn('result["image"] = nullptr;', wrapper)
        for flag in ('body_observed', 'association_rechecked', 'header_rechecked', 'name_rechecked'):
            self.assertIn('result["'+flag+'"] = false;', wrapper)
        for forbidden in ('ReadProcessMemory(', 'read.one(', 'read.unchanged(', '->pixels',
                          'get_data_for_xpak_key(', 'ASSET_TYPE_IMAGE', 'copied.name'):
            self.assertNotIn(forbidden, wrapper)

    @unittest.skipUnless(os.environ.get('IW7_T7_SOURCE'), 'Exact retained native SOURCE not supplied')
    def test_actual_measured_overlay_keeps_original_f2_entry_and_refuses_other_epoch(self):
        base = ProvenanceTransitionTests()
        main, cli = base.base()
        f2main, f2cli, _ = provenance.overlay(main, cli, base.read)
        new_main, new_cli, marker = metadata.overlay(f2main, f2cli, base.read)
        contract = json.loads((metadata.HERE/metadata.CONTRACT).read_text())
        for role, text in (('main', new_main), ('cli', new_cli)):
            self.assertEqual((len(text.encode()), hashlib.sha256(text.encode()).hexdigest()),
                             (contract[role]['bytes'], contract[role]['sha256']))
        self.assertEqual(marker['BaseCLISHA256'], provenance.pin(f2cli.encode())[1])
        original_entry = '\n'.join('\t'+line if line else '' for line in
                                  (metadata.HERE/provenance.ENTRY).read_text().splitlines())
        self.assertTrue(original_entry in new_cli, 'Original F2 entry must remain contiguous and unchanged')
        self.assertNotIn('#define IW7_PROVENANCE_FIXTURE', new_cli)
        self.assertNotIn('int main()', new_cli)
        self.assertIn('else if (provenance) observe_selected_image_provenance_iw7', new_cli)
        self.assertIn('if (image_metadata) observe_selected_image_metadata_iw7', new_cli)
        self.assertLess(len(new_cli.encode()), 160*1024)
        with self.assertRaises(ValueError):
            metadata.overlay(new_main, new_cli, base.read)
        with self.assertRaises(ValueError):
            metadata.overlay(main, cli, base.read)


if __name__ == '__main__':
    unittest.main()

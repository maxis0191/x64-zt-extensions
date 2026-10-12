import os
from pathlib import Path
import unittest
import prepare_cli as p


class NativeGuardSourceTests(unittest.TestCase):
    def test_selection_and_xpak_refusal_precede_converter_calls(self):
        source = (p.HERE/'native_export.inc').read_text()
        self.assertLess(source.index('xpak::deny_reads_for_resident_export();'), source.index('load_zone(zone, true, false)'))
        self.assertLess(source.index('resident_iw7::select('), source.index('converter::iw7::xmodel::dump(selected);'))
        self.assertNotIn('dump_zone(', source)
        self.assertNotIn('dump_asset(', source)
        self.assertIn('DB_IsXAssetDefault(ASSET_TYPE_XMODEL, name.c_str())', source)

    def test_exact_command_rejects_unicode_before_lossy_existing_arguments_used(self):
        source = (p.HERE/'native_cli.inc').read_text()
        self.assertLess(source.index('*p > 0x7e'), source.index('export_resident_model_iw7('))
        self.assertIn('args.size() != 5', source)
        self.assertIn('std::quick_exit(EXIT_FAILURE)', source)

    def test_output_receipt_keeps_dependency_and_parse_limits(self):
        source = (p.HERE/'native_export.inc').read_text()
        for name in ('dependency_payloads_verified', 'serialized_parse_verified', 'runtime_verified', 'ready'):
            self.assertIn('{"'+name+'", false}', source)
        self.assertIn('write_enemy_reference_output(root / "manifest.json", bytes)', source)
        self.assertIn('FILE_FLAG_OPEN_REPARSE_POINT', source)


@unittest.skipUnless(os.environ.get('IW7_T7_SOURCE'), 'Retained native source not supplied')
class RetainedPatchTests(unittest.TestCase):
    def test_exact_render_and_existing_cli_preserved(self):
        original, patched = p.render(Path(os.environ['IW7_T7_SOURCE']))
        self.assertEqual(p.patch_for(Path(os.environ['IW7_T7_SOURCE'])), p.PATCH.read_text())
        target = p.PATHS[1]
        tail = original[target].split('\t\tif (args.size() > 1)', 1)[1]
        self.assertIn(tail, patched[target])

    def test_xpak_guard_is_before_any_cache_indexing(self):
        _, patched = p.render(Path(os.environ['IW7_T7_SOURCE']))
        function = patched[p.PATHS[2]].split('get_data_for_xpak_key(', 1)[1]
        self.assertLess(function.index('if (resident_export_reads_denied.load())'), function.index('populate_xpak_cache_iterator'))

    def test_boot_refuses_missing_or_competing_engine_before_main_internal(self):
        _, patched = p.render(Path(os.environ['IW7_T7_SOURCE']))
        main = patched[p.PATHS[0]].split('int main()\n', 1)[1]
        self.assertLess(main.index('!utils::io::file_exists(T7_BINARY)'), main.index('MessageBoxA'))
        self.assertLess(main.index('game::get_mode() != game::t7'), main.index('return main_internal();'))

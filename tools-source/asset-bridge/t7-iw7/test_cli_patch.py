import os
import re
from pathlib import Path
import unittest
import prepare_cli as p


class NativeGuardSourceTests(unittest.TestCase):
    def test_native_work_expression_matches_independent_surface96_goldens(self):
        source = (p.HERE.parent/'t7-bridge/t7_iw7_resident_model.hpp').read_text()
        # Keep compile-time layout checking; these source-only tests do not
        # claim that a compiler has evaluated the corrected native assertion.
        self.assertRegex(source, r'static_assert\(sizeof\(XModelMesh\) == 120 && sizeof\(XSurfaceShared\) == 80 &&\s+'
                                 r'sizeof\(XSurface\) == 96 && sizeof\(XRigidVertList\) == 16\);')
        match = re.search(r'const auto work = (\d+) \+ (\d+) \* surfaces \+ (\d+) \* vertices \+ (\d+) \* triangles;', source)
        self.assertIsNotNone(match)
        base, surface, vertex, triangle = map(int, match.groups())
        for n, v, t, expected in ((1, 3, 1, 832), (5, 15, 5, 3136), (255, 765, 255, 147136),
                                  (2, 8, 3, 1540), (6, 267000, 62888, 16777216),
                                  (6, 267000, 62896, 16777312)):
            with self.subTest(n=n, v=v, t=t):
                self.assertEqual(base+surface*n+vertex*v+triangle*t, expected)
        self.assertIn('detail::require(work <= max_buffer_bytes,', source)

    def test_selection_and_xpak_refusal_precede_converter_calls(self):
        source = (p.HERE/'native_export.inc').read_text()
        self.assertLess(source.index('xpak::deny_reads_for_resident_export();'), source.index('load_zone(zone, true, false)'))
        self.assertLess(source.index('resident_iw7::select('), source.index('converter::iw7::xmodel::dump(selected);'))
        self.assertLess(source.index('const auto root_bone_name ='), source.index('converter::iw7::xmodel::dump(selected);'))
        self.assertIn('SL_ConvertToString(selected->boneNames[0])', source)
        self.assertNotIn('tag_origin', source)
        self.assertNotIn('dump_zone(', source)
        self.assertNotIn('dump_asset(', source)
        self.assertIn('DB_IsXAssetDefault(ASSET_TYPE_XMODEL, name.c_str())', source)

    def test_exact_command_rejects_unicode_before_lossy_existing_arguments_used(self):
        source = (p.HERE/'native_cli.inc').read_text()
        self.assertLess(source.index('*p > 0x7e'), source.index('export_resident_model_iw7('))
        self.assertIn('args.size() != 5', source)
        self.assertIn('std::quick_exit(EXIT_FAILURE)', source)

    def test_v2_is_explicit_and_v1_is_not_selected_from_surface_count(self):
        cli = (p.HERE/'native_cli.inc').read_text()
        export = (p.HERE/'native_export.inc').read_text()
        self.assertIn('args[1] == "-t7-iw7-model-v2"', cli)
        self.assertIn('args[1] != "-t7-iw7-model" && args[1] != "-t7-iw7-model-v2"', cli)
        self.assertIn('const bool multisurface = false', export)
        self.assertIn('(!multisurface && surface_count != 1)', export)
        self.assertIn('multisurface ? "iw7.t7-iw7-resident-export/2" : "iw7.t7-iw7-resident-export/1"', export)
        self.assertIn('multisurface ? 256u * 1024u : 4096u', export)

    def test_multisurface_selector_bounds_all_occurrences_before_payload_scan(self):
        source = (p.HERE.parent/'t7-bridge/t7_iw7_resident_model.hpp').read_text()
        body = source.split('inline XModel* select_impl(', 1)[1]
        self.assertLess(body.index('geometry_work_bytes_upper_bound(mesh.numSurfs'), body.index('readable(shared.data'))
        self.assertLess(body.index('geometry_work_bytes_upper_bound(mesh.numSurfs'), body.index('allocator.allocate<'))
        self.assertIn('materials.numMaterials == mesh.numSurfs', body)
        self.assertIn('surface_context(surface_index, surf)', body)
        self.assertIn('material_slot=', body)
        self.assertIn('surf.shared == mesh.shared', body)
        self.assertIn('sizeof(zonetool::iw7::GfxPackedVertex) == 32', source)

    def test_output_receipt_keeps_dependency_and_parse_limits(self):
        source = (p.HERE/'native_export.inc').read_text()
        for name in ('dependency_payloads_verified', 'serialized_parse_verified', 'runtime_verified', 'ready'):
            self.assertIn('{"'+name+'", false}', source)
        self.assertIn('write_enemy_reference_output(root / "manifest.json", bytes)', source)
        self.assertIn('FILE_FLAG_OPEN_REPARSE_POINT', source)

    def test_native_asset_names_use_common_adapter_rule(self):
        source = (p.HERE/'native_export.inc').read_text()
        self.assertIn('resident_iw7::asset_name(text)', source)
        self.assertNotIn('lower == "con"', source)


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

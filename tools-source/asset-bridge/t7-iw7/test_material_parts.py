"""Parts CLI source selection and finite-transition regression tests."""
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import prepare_build as build
import prepare_cli
import prepare_catalog_trace as trace
import prepare_message_publication as publication
import prepare_material_parts as parts
import prepare_prepatch_reference as reference


class PartsSelectionTests(unittest.TestCase):
    def valid(self):
        return SimpleNamespace(material_parts_v1=True, catalog_message_publication=True,
            selected_streamed_render_only_v2=True, reuse_plan='source-plan', reuse_compile_receipt='source-receipt')

    def test_default_returns_without_source_or_native_input_work(self):
        self.assertFalse(parts.selected(SimpleNamespace()))
        self.assertFalse(parts.selected(SimpleNamespace(material_parts_v1=False)))

    def test_explicit_marker_refuses_types_mixed_profiles_and_missing_proofs_before_io(self):
        for value in (1, 'true', [True], None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parts.selected(SimpleNamespace(material_parts_v1=value))
        self.assertTrue(parts.selected(self.valid()))
        for key,value in [('catalog_message_publication',False), ('selected_streamed_render_only_v2',False),
                          ('selected_streamed_static_v1',True), ('prepatch_reference_v2',True),
                          ('zombies_add_observation_c2',True), ('zombies_catalogue_observation',True),
                          ('resident_multisurface_v2',True), ('resident_surface_count_diagnostic',True),
                          ('prepatch_helper','another-module'), ('reuse_plan',None),
                          ('reuse_compile_receipt',None)]:
            args = self.valid();setattr(args,key,value)
            with self.subTest(key=key), patch.object(build,'path_checked',side_effect=AssertionError('input touched')):
                with self.assertRaises(ValueError):build.prepare(args)

    def test_native_entry_stops_at_selected_metadata_without_geometry_or_payload_io(self):
        source=(parts.HERE/parts.ENTRY).read_text()
        self.assertLess(source.index('resident_export_load_zone('), source.index('db_find_x_asset_header('))
        self.assertIn('DB_IsXAssetDefault(ASSET_TYPE_XMODEL, name.c_str())',source)
        self.assertIn('image_binding_selection{4u, 0xA0AB1041u}',source)
        for forbidden in ('streamed_iw7::select(', 'resident_iw7::select(', 'dump(', 'get_data_for_xpak_key(',
                          'LZ4_decompress', 'CreateFile', 'copy_resident('):
            self.assertNotIn(forbidden,source)
        self.assertIn('T7_SELECTED_MATERIAL_PARTS_METADATA',source)
        self.assertIn('parsed["refused"].get<bool>()',source)


@unittest.skipUnless(os.environ.get('IW7_T7_SOURCE'),'Retained native source not supplied')
class PartsRetainedTransitionTests(unittest.TestCase):
    def base(self):
        _, rendered=prepare_cli.render(Path(os.environ['IW7_T7_SOURCE']))
        self.assertEqual(parts.pin(rendered[prepare_cli.PATHS[0]].encode()),reference.BASE_MAIN)
        main=trace.wire_message_main(rendered[prepare_cli.PATHS[0]])
        return publication.overlay(main,rendered[prepare_cli.PATHS[1]])

    def test_exact_source_transition_preserves_default_and_refuses_other_epochs(self):
        main,cli=self.base()
        self.assertEqual(parts.pin(main.encode()),parts.BASE_MAIN)
        self.assertEqual(parts.pin(cli.encode()),parts.BASE_CLI)
        observer=(parts.HERE/'selected_material_observation.hpp').read_bytes().replace(b'\r\n',b'\n')
        # Authored include-only stub exercises the real text transition; no CPP
        # execution or actual image-parts implementation is inferred here.
        helper=b'#pragma once\n#include "selected_material_observation.hpp"\nnamespace authored_parts_stub {}\n'
        entry=(parts.HERE/parts.ENTRY).read_bytes()
        wired_main=parts.wire_main(main)
        wired_cli=parts.wire_cli(cli,observer,helper,entry)
        self.assertEqual(wired_main.count(parts.FLAG),2)
        self.assertIn('if (parts) observe_selected_material_parts_iw7(args[2], args[3], args[4]);',wired_cli)
        self.assertLess(wired_cli.index('*p > 0x7e'),wired_cli.index('if (parts) observe_selected_material_parts_iw7('))
        self.assertIn('Exclusive exact material-parts arguments required',wired_cli)
        self.assertEqual(wired_cli.count('T7_SELECTED_MATERIAL_PARTS_METADATA'),1)
        self.assertIn('t7_catalog_message_cli_exit(EXIT_SUCCESS)',wired_cli)
        self.assertEqual(self.base(),(main,cli))
        for changed in (main+' ',main.replace('t7-iw7-catalog','other-mode',1)):
            with self.assertRaises(ValueError):parts.wire_main(changed)
        for changed in (cli+' ',cli.replace('t7-iw7-model-streamed-v2','other-mode',1)):
            with self.assertRaises(ValueError):parts.wire_cli(changed,observer,helper,entry)
        with self.assertRaises(ValueError):parts.wire_cli(cli,observer+b' ',helper,entry)
        with self.assertRaises(ValueError):parts.wire_cli(cli,observer,helper.replace(b'#pragma once',b'// absent'),entry)

    def test_real_g3_source_contract_binds_the_complete_generated_pair(self):
        main,cli=self.base()
        reads=[]
        def read(path,limit,expected=None):
            raw=path.read_bytes().replace(b'\r\n',b'\n')
            self.assertLessEqual(len(raw),limit)
            if expected:self.assertEqual(parts.pin(raw)[1],expected)
            reads.append(path.name)
            return raw
        wired_main,wired_cli,marker=parts.overlay(main,cli,read)
        self.assertEqual((marker['MainBytes'],marker['MainSHA256']),parts.pin(wired_main.encode()))
        self.assertEqual((marker['CLIBytes'],marker['CLISHA256']),parts.pin(wired_cli.encode()))
        self.assertEqual(set(reads),{parts.CONTRACT,parts.HELPER,parts.ENTRY,
            'selected_material_parts_observation_fixture.cpp','selected_material_observation.hpp'})
        self.assertEqual(wired_cli.count('namespace zonetool::t7::selected_material_parts_observation'),1)
        self.assertEqual(wired_cli.count('namespace zonetool::t7::selected_material_observation'),1)
        self.assertNotIn('#include "selected_material_observation.hpp"',wired_cli)
        self.assertLessEqual(len(wired_cli.encode()),128*1024)
        # Source changes cannot be hidden by keeping the same declared output.
        def changed(path,limit,expected=None):
            raw=read(path,limit,expected)
            return raw+b' ' if path.name==parts.HELPER else raw
        with self.assertRaises(ValueError):parts.overlay(main,cli,changed)


if __name__=='__main__':unittest.main()

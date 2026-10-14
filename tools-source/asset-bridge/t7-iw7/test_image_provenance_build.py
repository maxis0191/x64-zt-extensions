"""Actual producer source predicates/transition; no prepare(), tlog, SDK or compiler IO."""
import copy
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import prepare_build as build
import prepare_image_provenance as provenance
import prepare_material_parts as parts
import test_material_parts as material_tests


class ProvenanceBuildTests(unittest.TestCase):
    def args(self, **changes):
        values = dict(image_provenance_v1=True, catalog_message_publication=True,
                      selected_streamed_render_only_v2=True, reuse_plan='retained-plan.json',
                      reuse_compile_receipt='retained-receipt.json')
        values.update(changes)
        return SimpleNamespace(**values)

    def test_exclusive_selection_before_any_prepare_io(self):
        self.assertTrue(build.image_provenance_selected(self.args()))
        self.assertFalse(build.image_provenance_selected(SimpleNamespace()))
        for name in ('material_parts_v1', 'prepatch_reference_v2', 'prepatch_link_v3',
                     'selected_streamed_static_v1', 'resident_multisurface_v2',
                     'resident_surface_count_diagnostic', 'zombies_catalogue_observation',
                     'zombies_add_observation_c2', 'catalog_trace', 'catalog_exit',
                     'catalog_callers', 'catalog_message'):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    build.image_provenance_selected(self.args(**{name: True}))
        for changes in ({'image_provenance_v1': 1}, {'image_provenance_v1': []},
                        {'catalog_message_publication': False}, {'selected_streamed_render_only_v2': False},
                        {'reuse_plan': None}, {'reuse_compile_receipt': None}, {'prepatch_helper': 'old.inc'}):
            with self.assertRaises(ValueError):
                build.image_provenance_selected(self.args(**changes))
        with patch.object(build, 'path_checked', side_effect=AssertionError('IO reached')) as io:
            with self.assertRaises(ValueError):
                build.prepare(self.args(material_parts_v1=True))
            io.assert_not_called()

    def test_real_producer_transition_preserves_qualified_api_source_outputs(self):
        main, cli = material_tests.PartsRetainedTransitionTests().base()
        payloads = {'prepared/main.cpp': main.encode(), 'prepared/zonetool.cpp': cli.encode()}
        before = copy.deepcopy(payloads)
        reads = []
        def read(path, limit, expected=None):
            raw = path.read_bytes().replace(b'\r\n', b'\n')
            self.assertLessEqual(len(raw), limit)
            if expected:
                self.assertEqual(parts.pin(raw)[1], expected)
            reads.append(path.name)
            return raw
        generated_main, generated_cli, marker = build.image_provenance_transition(payloads, read)
        contract = json.loads((provenance.HERE/provenance.CONTRACT).read_text())
        for role, raw in (('main', generated_main), ('cli', generated_cli)):
            self.assertEqual(parts.pin(raw), (contract[role]['bytes'], contract[role]['sha256']))
        self.assertEqual(marker['Schema'], 'iw7.t7-image-provenance-build/1')
        self.assertEqual(marker['BaseMainSHA256'], parts.BASE_MAIN[1])
        self.assertEqual(marker['BaseCLISHA256'], parts.BASE_CLI[1])
        self.assertEqual(set(reads), {'prepare_material_parts.py', 'prepare_image_provenance.py',
            provenance.CONTRACT, provenance.HELPER, provenance.ENTRY, provenance.FIXTURE,
            'selected_material_observation.hpp'})
        self.assertEqual(payloads, before)
        self.assertNotIn(b'#define IW7_PROVENANCE_FIXTURE', generated_cli)
        # The old G3 source pair still uses its original independent overlay.
        old_main, old_cli, old = parts.overlay(main, cli, read)
        self.assertNotEqual(old['CLISHA256'], marker['CLISHA256'])
        with self.assertRaises(ValueError):
            build.image_provenance_transition({'prepared/main.cpp': generated_main,
                                              'prepared/zonetool.cpp': generated_cli}, read)

    def test_bounded_payload_and_finite_os_context(self):
        payloads = {'authored-metadata-bytes': b'0'*(256*1024+1)}
        with self.assertRaises(ValueError):
            build.require_preparation_bounds(b'{}', payloads)
        build.require_preparation_bounds(b'{}', payloads, provenance_profile=True)
        with self.assertRaises(ValueError):
            build.require_preparation_bounds(b'{}', payloads, provenance_profile=True, parts_profile=True)
        with self.assertRaises(ValueError):
            build.require_preparation_bounds(b'{}', {'over': b'0'*(288*1024+1)}, provenance_profile=True)
        self.assertTrue(build.os_resource_selected(self.args(os_context_tzres_20261014=True,
                                                             os_context_proof='fixed-proof.json')))
        with self.assertRaises(ValueError):
            build.os_resource_selected(self.args(os_context_tzres_20261014=True))


if __name__ == '__main__':
    unittest.main()

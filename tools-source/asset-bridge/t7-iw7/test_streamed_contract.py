import copy
import unittest
import importlib.util
import sys
from pathlib import Path
import boot_contract as boot
import export_contract as export
import streamed_contract as stream
from test_export_contract import fixture_v2


def fixture():
    request, manifest = fixture_v2(((17, 23), (11, 19)))
    request.update(schema=stream.REQUEST_SCHEMA, profile=stream.PROFILE,
                   xpak_key='ffeeddccbbaa9988',
                   packages=[{'path': 'zone/fixture_zone.xpak',
                              'identity': '89ABCDEF:0123456789ABCDEF', 'bytes': 2 * 1024**2}])
    manifest.update(schema=stream.EXPORT_SCHEMA, profile=stream.PROFILE,
                    geometry_profile=stream.GEOMETRY_PROFILE, output_root_key=stream.root_key(request))
    manifest['selected_mesh_payload'] = dict(
        key_hex=request['xpak_key'], source_shared_flags=9, cpu_view_shared_flags=8,
        source_surface_flags=[0, 32], opaque_descriptor_words_hex=['0000000000000000'] * 3,
        descriptor_field_semantics_verified=False, package_path='zone/fixture_zone.xpak',
        package_identity=request['packages'][0]['identity'], file_bytes=request['packages'][0]['bytes'],
        hash_table_offset=128, hash_entry_offset=128, payload_offset=512,
        compressed_bytes=18752, packed_entry_size=(0xAB << 56) | 18752, indexed_bytes=24,
        opcodes=[0], opaque_header_offsets=[0xFFFFFFFF], payload_bytes=18624,
        payload_sha256='c' * 64, headers_rechecked=True, atomic_snapshot_proven=False,
        engine_object_writes=False)
    return request, manifest


class StreamedContractTests(unittest.TestCase):
    def test_streamed_receipt_uses_same_independent_serialized_geometry_reader(self):
        from test_readback import SyntheticMulti
        synthetic = SyntheticMulti(materials=['original/clay', 'original/metal'])
        request, template = fixture()
        synthetic.request.update(schema=stream.REQUEST_SCHEMA, profile=stream.PROFILE,
                                 xpak_key=request['xpak_key'], packages=request['packages'])
        synthetic.manifest.update(schema=stream.EXPORT_SCHEMA, profile=stream.PROFILE,
                                  geometry_profile=stream.GEOMETRY_PROFILE,
                                  output_root_key=stream.root_key(synthetic.request),
                                  selected_mesh_payload=template['selected_mesh_payload'])
        proof = synthetic.inspect()
        self.assertEqual(proof['mesh']['vertices'], 9)
        self.assertTrue(proof['serialized_parse_verified'])
        self.assertFalse(proof['native_provenance_verified'])
        self.assertFalse(proof['runtime_verified'])
        path = Path(__file__).resolve().parents[3] / 'ops/model-lab/rigid_export.py'
        spec = importlib.util.spec_from_file_location('_streamed_model_lab_test', path)
        lab = importlib.util.module_from_spec(spec); spec.loader.exec_module(lab)
        bindings = [dict(slot=i, source=name, target=lab.MATERIAL)
                    for i, name in enumerate(synthetic.manifest['material_dependencies'])]
        model, receipt = lab.derive(bytes(synthetic.outputs['model']), bytes(synthetic.outputs['mesh']),
                                    synthetic.manifest, synthetic.request, lod_distance=1000000, rebinds=bindings)
        self.assertEqual(receipt['geometry_profile'], stream.GEOMETRY_PROFILE)
        self.assertEqual(receipt['derived_model']['surfaces'], 2)
        self.assertEqual(synthetic.inspect()['model']['materials'], ['original/clay', 'original/metal'])
        sys.path.insert(0, str(path.parent))
        try:
            plan = lab.make_plan(synthetic.manifest, synthetic.request, receipt,
                                 {synthetic.manifest['model']['relative_path']: model,
                                  synthetic.manifest['mesh']['relative_path']: bytes(synthetic.outputs['mesh'])})
        finally:
            sys.path.pop(0)
        self.assertEqual(plan['surface_records'], synthetic.manifest['surface_records'])
        self.assertFalse(plan['ready'])

    def test_explicit_profile_preserves_full_uint64_and_opaque_values(self):
        request, manifest = fixture()
        self.assertGreater(int(request['xpak_key'], 16), 2**53)
        self.assertEqual(boot.validate_request(request), request)
        self.assertTrue(export.validate_export(manifest, request)['receipt_contract_verified'])
        self.assertFalse(export.validate_export(manifest, request)['runtime_verified'])

    def test_key_encoding_rejects_numeric_rounding_and_noncanonical_strings(self):
        request, _ = fixture()
        for key in (int(request['xpak_key'], 16), float(int(request['xpak_key'], 16)),
                    'FFEEDDCCBBAA9988', '0xffeeddccbbaa9988', 'ffeeddccbbaa998', True):
            with self.subTest(key=key), self.assertRaises(ValueError):
                stream.validate_request({**request, 'xpak_key': key})

    def test_package_identity_size_and_aliases_are_explicit(self):
        request, _ = fixture()
        for change in ({'path': '../fixture_zone.xpak'}, {'path': 'zone/sub/fixture_zone.xpak'},
                       {'path': 'zone/CON.xpak'}, {'identity': '89abcdef:0123456789abcdef'},
                       {'bytes': True}, {'bytes': 119}, {'bytes': 16 * 1024**3 + 1}):
            changed = copy.deepcopy(request); changed['packages'][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError): stream.validate_request(changed)
        for packages in ([], request['packages'] * 2, request['packages'] * 9):
            with self.assertRaises(ValueError): stream.validate_request({**request, 'packages': packages})

    def test_command_needs_one_pinned_request_document(self):
        request, _ = fixture()
        review = boot.command_review(request, request_path='streamed_request.json')
        self.assertEqual(review['proposed_arguments'],
                         [stream.OPTION, 'fixture_zone', 'fixture/model', '0', 'streamed_request.json'])
        self.assertFalse(review['zonetool_global_xpak_reads_allowed'])
        for path in ('../request.json', 'zone/request.json', 'request.JSON', 'NUL.json'):
            with self.assertRaises(ValueError): boot.command_review(request, request_path=path)
        self.assertIsNone(boot.command_review(request)['proposed_arguments'])

    def test_root_is_bound_to_key_and_exact_package_identity(self):
        request, _ = fixture(); initial = stream.root_key(request)
        changed = copy.deepcopy(request); changed['xpak_key'] = '0000000000000001'
        self.assertNotEqual(initial, stream.root_key(changed))
        changed = copy.deepcopy(request); changed['packages'][0]['identity'] = '89ABCDEF:0123456789ABCDEE'
        self.assertNotEqual(initial, stream.root_key(changed))
        self.assertNotEqual(initial, boot.command_review(boot.make_request('fixture_zone', 'fixture/model', 0))['private_output_root_key'])

    def test_provenance_cannot_relabel_streamed_as_resident(self):
        request, manifest = fixture()
        for change in ({'schema': export.SCHEMA_V2}, {'geometry_profile': 't7-iw7-resident-static-v2'},
                       {'profile': boot.PROFILE}, {'zonetool_xpak_helper_reads_allowed': True}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                export.validate_export({**manifest, **change}, request)
        resident = boot.make_request('fixture_zone', 'fixture/model', 0)
        with self.assertRaises(ValueError): export.validate_export(manifest, resident)

    def test_payload_provenance_refuses_changed_key_flags_range_codec_or_claim(self):
        request, manifest = fixture()
        changes = [{'key_hex': '0000000000000001'}, {'source_shared_flags': 8},
                   {'cpu_view_shared_flags': 9}, {'source_surface_flags': [0, 2]},
                   {'opaque_descriptor_words_hex': [0, 0, 0]}, {'descriptor_field_semantics_verified': True},
                   {'package_identity': '89ABCDEF:0000000000000000'}, {'file_bytes': True},
                   {'hash_entry_offset': 129}, {'payload_offset': 2 * 1024**2},
                   {'compressed_bytes': 256 * 1024 + 1}, {'packed_entry_size': 10},
                   {'indexed_bytes': 8 * 1024**2 + 1}, {'payload_bytes': 18623},
                   {'payload_sha256': 'C' * 64}, {'opcodes': [6]}, {'opaque_header_offsets': []},
                   {'headers_rechecked': False}, {'atomic_snapshot_proven': True}, {'engine_object_writes': True}]
        for change in changes:
            changed = copy.deepcopy(manifest); changed['selected_mesh_payload'].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError): export.validate_export(changed, request)


if __name__ == '__main__':
    unittest.main()

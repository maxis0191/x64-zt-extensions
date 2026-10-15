"""Geometry/contact correspondence checks; no native processes or game."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import platform_contact as contact

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO/'ops/model-lab'))
from geometry import original_cube


def platform():
    # Only a test input. Production geometry is authored by SDK/serializer owners.
    mesh = original_cube()
    mesh['name'] = 'authored_platform_test'
    for vertex in mesh['surfaces'][0]['vertices']:
        x, y, z = vertex['position']
        vertex['position'] = [x*16, y*16, z+8]
    mesh['bounds'] = {'midpoint': [0, 0, 8], 'half_size': [128, 128, 8]}
    return mesh


class PlatformContactTests(unittest.TestCase):
    def test_source_mesh_maps_exactly_to_fixed_a572_box_at_nonzero_anchor(self):
        result = contact.contact_contract(platform(), [-320, 640, 128])
        self.assertEqual(result['render_transform'], {
            'model_origin': [-320, 640, 224], 'model_angles': [0, 0, 0], 'uniform_scale': 1})
        self.assertEqual(result['world_bounds'], {'minimum': [-448, 512, 224], 'maximum': [-192, 768, 240]})
        self.assertEqual(result['native_box']['origin'], [-320, 640, 232])
        self.assertEqual(result['native_box']['half_size'], [128, 128, 8])
        self.assertEqual(result['player_start'], [-320, 640, 336])
        self.assertEqual(result['native_box']['provider_internal_game_to_havok_scale'], 1/32)
        self.assertFalse(result['native_box']['owner_transform_applied'])
        self.assertFalse(result['actual_anchor_verified'])
        self.assertFalse(result['caller_asset_loading_bound'])
        self.assertFalse(result['sdk_project_bound'])
        self.assertFalse(result['runtime_verified'])

    def test_bounds_alone_cannot_qualify_a_dented_or_open_platform(self):
        for mutation in ('dented', 'missing_face', 'duplicate', 'inward', 'overlap', 'coincident_corners', 'wrong_normal'):
            mesh = platform()
            surface = mesh['surfaces'][0]
            if mutation == 'dented':
                surface['vertices'][0]['position'][1] = -64
            elif mutation == 'missing_face':
                surface['triangles'][-2:] = copy.deepcopy(surface['triangles'][:2])
            elif mutation == 'duplicate':
                surface['triangles'][1] = surface['triangles'][0][:]
            elif mutation == 'inward':
                surface['triangles'][0].reverse()
            elif mutation == 'overlap':
                # Both face triangles share a boundary edge, leaving a hole.
                surface['triangles'][1] = [0, 1, 3]
            elif mutation == 'coincident_corners':
                surface['vertices'][3]['position'] = surface['vertices'][1]['position'][:]
                surface['triangles'][1] = [0, 3, 2]
            else:
                surface['vertices'][0]['normal'] = [0, 0, 1]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                contact.contact_contract(mesh, [0, 0, 0])

    def test_face_order_and_triangle_order_are_not_a_serializer_dependency(self):
        mesh = platform()
        mesh['surfaces'][0]['triangles'].reverse()
        contact.validate_platform(mesh)

    def test_a572_dimensions_identity_and_source_only_claims_are_closed(self):
        for mutation in ('name', 'bounds', 'vertex', 'lod', 'root', 'physics', 'ready', 'bone', 'weight'):
            mesh = platform()
            if mutation == 'name': mesh['name'] = '../other'
            elif mutation == 'bounds': mesh['bounds']['half_size'][0] = 256
            elif mutation == 'vertex': mesh['surfaces'][0]['vertices'][0]['position'][0] = True
            elif mutation == 'lod': mesh['lods'] = True
            elif mutation == 'root': mesh['bones'][0]['translation'][0] = True
            elif mutation == 'physics': mesh['physics_verified'] = True
            elif mutation == 'ready': mesh['ready'] = True
            elif mutation == 'bone': mesh['surfaces'][0]['vertices'][0]['bone'] = True
            else: mesh['surfaces'][0]['vertices'][0]['weight'] = True
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                contact.contact_contract(mesh, [0, 0, 0])

    def test_float32_anchor_and_every_offset_endpoint_must_remain_exact(self):
        for anchor in ([0.1, 0, 0], [True, 0, 0], [0, 0, float('inf')], [0, 0, 2**30]):
            with self.subTest(anchor=anchor), self.assertRaises(ValueError):
                contact.contact_contract(platform(), anchor)

    def test_cli_binds_actual_source_bytes_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, output = root/'geometry.source.json', root/'contact.source.json'
            data = (json.dumps(platform())+'\n').encode()
            source.write_bytes(data)
            result = contact.write_contract(source, output, [0, 0, 0])
            self.assertEqual(result['geometry_source_sha256'], hashlib.sha256(data).hexdigest())
            self.assertEqual(json.loads(output.read_text()), result)
            before = output.read_bytes()
            with self.assertRaises(FileExistsError): contact.write_contract(source, output, [0, 0, 0])
            self.assertEqual(output.read_bytes(), before)

    def test_invalid_duplicate_or_oversized_source_cannot_publish_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, output = root/'geometry.source.json', root/'contact.source.json'
            valid = json.dumps(platform()).encode()
            for data in (valid.replace(b'"lods": 1', b'"lods": 1, "lods": 1'),
                         b' '*(contact.MAX_BYTES+1), b'{}'):
                source.write_bytes(data)
                with self.assertRaises(ValueError): contact.write_contract(source, output, [0, 0, 0])
                self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()

"""Original source-shaped streams, not extracted BO3/Ray Gun/native evidence."""
import copy
import struct
import unittest

from owned_skin_mapping import map_owned_source_surface
from read_blend import read_blend


def fixture():
    positions = b''.join(struct.pack('<3f', i, i + .25, i + .5) for i in range(6))
    attributes = b''.join(bytes([i]) * 16 for i in range(6))
    weight_rows = [(255, 0, 0, 0, 0, 0, 0, 0)] * 3 + [
        (128, 127, 0, 0, 0, 1, 0, 0), (255, 0, 0, 0, 2, 0, 0, 0),
        (64, 191, 0, 0, 1, 2, 0, 0)]
    weights = b''.join(struct.pack('<4B4H', *row) for row in weight_rows)
    indices = struct.pack('<6H', 0, 0, 0, 0, 1, 2)
    payload = bytes(16) + positions + attributes + weights + indices
    shared = dict(dataSize=len(payload), flags=1, vertCount=6, indexCount=6,
                  posOffset=16, vertsOffset=88, skinWeightsOffset=184, indicesOffset=256)
    surface = dict(vertCount=3, triCount=1, baseVertOffset=3, baseIndexOffset=3,
                   flags=2, vertListCount=0, partBits=bytes(48))
    return payload, shared, surface, ['source_root', 'source_joint_a', 'source_joint_b']


class OwnedSkinTests(unittest.TestCase):
    def test_nonzero_bases_and_mixed_classes_keep_every_attribute_and_corner(self):
        inputs = fixture()
        before = copy.deepcopy(inputs)
        result = map_owned_source_surface(*inputs)
        self.assertEqual(inputs, before)
        self.assertEqual(result['new_to_old'], [1, 0, 2])
        self.assertEqual(result['old_to_new'], [1, 0, 2])
        self.assertEqual(result['selected_ranges']['triangles'], (262, 268))
        self.assertEqual(result['snapshot']['positions'], b''.join(
            struct.pack('<3f', i, i + .25, i + .5) for i in (4, 3, 5)))
        self.assertEqual(result['snapshot']['attributes'], b''.join(bytes([i]) * 16 for i in (4, 3, 5)))
        self.assertEqual(result['snapshot']['triangles'], struct.pack('<3H', 1, 0, 2))
        self.assertEqual(result['iw7_blend_counts'], [1, 2, 0, 0])
        self.assertEqual(result['iw7_blend_bytes'], struct.pack('<10H', 2, 0, 0, 1, 128, 0, 1, 2, 64, 0))
        decoded = read_blend(result['iw7_blend_bytes'], result['iw7_blend_counts'], 3)
        self.assertEqual([row['ids'] for row in decoded], [(2,), (0, 1), (1, 2)])
        self.assertEqual([row['stored_weights'] for row in decoded], [(), (128,), (64,)])
        self.assertEqual(result['native_stride_provenance'], 'Pending')
        self.assertIsNone(result['tag_position_stride'])
        self.assertFalse(result['production_admissible'])
        self.assertFalse(result['ready'])

    def test_all_stream_ranges_checked_before_any_slice(self):
        for field in ('posOffset', 'vertsOffset', 'skinWeightsOffset', 'indicesOffset'):
            payload, shared, surface, bones = fixture()
            shared[field] = len(payload) - 1
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'stream_extent'):
                map_owned_source_surface(payload, shared, surface, bones)

    def test_u32_wrap_and_index_base_as_triangle_count_are_refused(self):
        payload, shared, surface, bones = fixture()
        shared['skinWeightsOffset'] = 2**32 - 4
        with self.assertRaisesRegex(ValueError, 'stream_extent'):
            map_owned_source_surface(payload, shared, surface, bones)
        payload, shared, surface, bones = fixture()
        surface['baseIndexOffset'] = 6
        with self.assertRaisesRegex(ValueError, 'shared_counts'):
            map_owned_source_surface(payload, shared, surface, bones)

    def test_immutable_exact_payload_and_separate_skinned_profile(self):
        payload, shared, surface, bones = fixture()
        for invalid in (payload[:-1], bytearray(payload)):
            with self.assertRaisesRegex(ValueError, 'owned_payload'):
                map_owned_source_surface(invalid, shared, surface, bones)
        for flags, lists in ((0x82, 1), (2, 1), (3, 0)):
            surface.update(flags=flags, vertListCount=lists)
            with self.assertRaisesRegex(ValueError, 'surface_profile'):
                map_owned_source_surface(payload, shared, surface, bones)

    def test_bad_joint_ids_local_indices_and_dropped_part_bits_are_refused(self):
        payload, shared, surface, bones = fixture()
        changed = bytearray(payload)
        struct.pack_into('<H', changed, 184 + 3 * 12 + 4, 3)
        with self.assertRaisesRegex(ValueError, 'weight_bone_ids'):
            map_owned_source_surface(bytes(changed), shared, surface, bones)
        changed = bytearray(payload)
        struct.pack_into('<H', changed, 262, 3)
        with self.assertRaisesRegex(ValueError, 'triangle_index'):
            map_owned_source_surface(bytes(changed), shared, surface, bones)
        surface['partBits'] = bytes(47) + b'\x01'
        with self.assertRaisesRegex(ValueError, 'part_bits_loss'):
            map_owned_source_surface(payload, shared, surface, bones)


if __name__ == '__main__':
    unittest.main()

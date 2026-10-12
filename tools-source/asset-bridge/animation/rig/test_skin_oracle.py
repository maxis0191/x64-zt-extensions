"""Original fixtures and deliberately wrong candidates; no asset/tool dependency."""
import math
import struct
import unittest
from skin_oracle import (BindPrefixReader, decode_global_bind, decode_one_two_blend,
                         inspect_retail_bind, inverse_rigid, linear_blend, multiply,
                         original_fixture, rigid_matrix, transform, verify_original_candidate)

# Hand-authored IW7 words: mono 0/0/1/1, dual .25/.25/.75/.75.
# No production writer/packer is imported to produce this expectation.
BLEND = bytes.fromhex("00000000 00000000 01000000 01000000 "
                      "0000010040000000 0000010040000000 "
                      "00000100bf000000 00000100bf000000")
COUNTS = [4, 4, 0, 0, 0, 0, 0, 0]
PARENTS = b"\x01"
ANGLES = bytes.fromhex("000000000000ff7f")
POSITIONS = bytes.fromhex("000000000000000000000041")
BASES = struct.pack("<16f", 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 1, 0, 0, 8, 2)


def report(blend=BLEND, parents=PARENTS, angles=ANGLES, positions=POSITIONS, bases=BASES, counts=COUNTS):
    return verify_original_candidate(parents, angles, positions, bases, blend, counts)


class SkinOracleTests(unittest.TestCase):
    def test_literal_candidate_vs_closed_form(self):
        result = report()
        self.assertEqual((result["vertices"], result["bones"], result["blend_bytes"]), (8, 2, 48))
        self.assertGreater(result["quantization_error_units"], 0)
        self.assertLess(result["quantization_error_units"], .005)
        self.assertGreater(result["opposite_weight_error_units"], 1)
        self.assertFalse(result["engine_deformation_verified"])
        self.assertFalse(result["pixels_verified"])
        self.assertFalse(result["animation_verified"])

    def test_quantized_weight_is_explicit_hypothesis(self):
        a = decode_one_two_blend(BLEND, COUNTS, 2, "first")
        b = decode_one_two_blend(BLEND, COUNTS, 2, "second")
        self.assertEqual(a[:4], [{0: 1}, {0: 1}, {1: 1}, {1: 1}])
        self.assertAlmostEqual(a[4][0], 64 / 255)
        self.assertAlmostEqual(b[4][1], 64 / 255)
        with self.assertRaises(ValueError): decode_one_two_blend(BLEND, COUNTS, 2, "inferred")

    def test_reversed_weight_byte_detected_by_source_bend(self):
        wrong = bytearray(BLEND)
        for offset in (20, 28, 36, 44):
            wrong[offset] = 255 - wrong[offset]
        with self.assertRaisesRegex(ValueError, "deformation tolerance"): report(bytes(wrong))

    def test_wrong_bone_correspondence_detected_even_in_rest_pose(self):
        wrong = bytearray(BLEND)
        struct.pack_into("<H", wrong, 8, 0)
        with self.assertRaisesRegex(ValueError, "correspondence"): report(bytes(wrong))

    def test_h1_premultiplied_bone_id_rejected(self):
        wrong = bytearray(BLEND)
        struct.pack_into("<H", wrong, 8, 64)
        with self.assertRaisesRegex(ValueError, "raw bone ID"): report(bytes(wrong))

    def test_changed_stride_count_and_trailing_bytes_rejected(self):
        for bad in (BLEND[:-2], BLEND + b"\0\0"):
            with self.assertRaisesRegex(ValueError, "blend bytes"): report(bad)
        with self.assertRaises(ValueError): report(counts=[8, 0, 0, 0, 0, 0, 0, 0])

    def test_padding_is_not_ignored(self):
        for offset in (2, 22):
            wrong = bytearray(BLEND)
            struct.pack_into("<H", wrong, offset, 1)
            with self.assertRaisesRegex(ValueError, "padding"): report(bytes(wrong))

    def test_duplicate_dual_ids_rejected(self):
        wrong = bytearray(BLEND)
        struct.pack_into("<H", wrong, 18, 0)
        with self.assertRaisesRegex(ValueError, "dual IDs"): report(bytes(wrong))

    def test_weight_word_range_rejected(self):
        for word in (0, 255, 256, 65535):
            wrong = bytearray(BLEND)
            struct.pack_into("<H", wrong, 20, word)
            with self.assertRaisesRegex(ValueError, "byte-range"): report(bytes(wrong))

    def test_histogram_boolean_and_unsupported_groups_rejected(self):
        for counts in ([True, 4, 0, 0, 0, 0, 0, 0], [4, 3, 1, 0, 0, 0, 0, 0], [65, 0, 0, 0, 0, 0, 0, 0]):
            with self.assertRaises(ValueError): decode_one_two_blend(BLEND, counts, 2, "second")

    def test_inverse_bind_storage_rejected(self):
        wrong = bytearray(BASES)
        struct.pack_into("<f", wrong, 56, -8)
        with self.assertRaisesRegex(ValueError, "positive global bind"): report(bases=bytes(wrong))

    def test_tag_translation_and_parent_mismatch_rejected(self):
        with self.assertRaises(ValueError): report(parents=b"\0")
        with self.assertRaises(ValueError): report(positions=struct.pack("<3f", 0, 0, -8))

    def test_nonidentity_root_and_child_global_bind(self):
        # Rz90/T(3,4,5), then Rx90/T(0,0,8): child global quaternion(.5,.5,.5,.5).
        q = math.sqrt(.5)
        bases = struct.pack("<16f", 0, 0, q, q, 3, 4, 5, 2, .5, .5, .5, .5, 3, 4, 13, 2)
        matrices, error = decode_global_bind(PARENTS, struct.pack("<4h", 23170, 0, 0, 23170), POSITIONS, bases)
        self.assertLess(error, 1e-6)
        self.assertEqual(transform(matrices[0], (1, 0, 0)), [3., 5., 5.])
        self.assertEqual(transform(matrices[1], (0, 0, 0)), [3., 4., 13.])
        # A local child substituted into a global baseMat must fail even though its length is valid.
        local = struct.pack("<8f", q, 0, 0, q, 0, 0, 8, 2)
        with self.assertRaisesRegex(ValueError, "positive global bind"):
            decode_global_bind(PARENTS, struct.pack("<4h", 23170, 0, 0, 23170), POSITIONS, bases[:32] + local)

    def test_rigid_inverse_and_pose_order(self):
        q = math.sqrt(.5)
        bind = rigid_matrix((0, 0, q, q), (3, 4, 5))
        pose = rigid_matrix((0, 0, 0, 1), (7, 8, 9))
        inverse = inverse_rigid(bind)
        self.assertAlmostEqual(math.dist(transform(multiply(bind, inverse), (2, 3, 4)), (2, 3, 4)), 0)
        actual = linear_blend([[3, 5, 5]], [{0: 1}], [bind], [pose])[0]
        self.assertEqual(actual, [8., 8., 9.])
        wrong_order = transform(multiply(inverse, pose), (3, 5, 5))
        self.assertGreater(math.dist(actual, wrong_order), 1)

    def test_matrix_skin_bind_is_identity_for_asymmetric_weights(self):
        vertices, weights, _ = original_fixture()
        bind, _ = decode_global_bind(PARENTS, ANGLES, POSITIONS, BASES)
        self.assertEqual(linear_blend(vertices, weights, bind, bind), vertices)

    def test_invalid_quaternion_and_transweight(self):
        for offset, value in ((12, 0), (28, 1), (32, float("nan")), (60, -2)):
            wrong = bytearray(BASES)
            struct.pack_into("<f", wrong, offset, value)
            with self.assertRaises(ValueError): report(bases=bytes(wrong))
        with self.assertRaises(ValueError): report(angles=b"\0" * 8)

    def test_finite_normalized_skin_inputs(self):
        bind, _ = decode_global_bind(PARENTS, ANGLES, POSITIONS, BASES)
        for row in ({True: 1.}, {2: 1.}, {0: .5}, {0: float("nan")}):
            with self.assertRaises(ValueError): linear_blend([[0, 0, 0]], [row], bind, bind)
        with self.assertRaises(ValueError): linear_blend([[0, 0, float("inf")]], [{0: 1.}], bind, bind)

    def test_prefix_bounds_and_references(self):
        reader = BindPrefixReader(b"\x06\x01original\0\x09" + struct.pack("<II", 0, 0))
        self.assertEqual(reader.string(), "original")
        self.assertEqual(reader.string(), "original")
        for payload in (b"", b"x" * 65537, b"\x08\x01\x01", b"\x06\x01" + b"a" * 129, b"\x09" + struct.pack("<II", 8, 0)):
            with self.assertRaises(ValueError):
                r = BindPrefixReader(payload)
                (r.array(4, 1) if payload.startswith(b"\x08") else r.string())

    def test_retail_hash_required_before_layout_read(self):
        with self.assertRaisesRegex(ValueError, "retail XMB hash"): inspect_retail_bind(b"original synthetic data")


if __name__ == "__main__":
    unittest.main()

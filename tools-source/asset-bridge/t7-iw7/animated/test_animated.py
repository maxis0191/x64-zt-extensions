import copy
import importlib.util
import itertools
from pathlib import Path
import struct
import unittest

import fixtures
from preflight import (ABSENT, FLAGS, NARROWED, ZERO_COUNTS, Refusal, decode_stream_weights,
                       preflight_clip, preflight_skeleton, preflight_weights)
from read_blend import read_blend
from reorder_proposal import regroup_surface


class AnimatedTests(unittest.TestCase):
    def refused(self, code, function, *args):
        with self.assertRaises(Refusal) as caught:
            function(*args)
        self.assertEqual(caught.exception.code, code)

    def clip(self, c):
        return preflight_clip(c, fixtures.skeleton()["names"])

    def test_original_skeleton_and_independent_bind_oracle(self):
        s = fixtures.skeleton()
        report = preflight_skeleton(s)
        self.assertEqual(report["iw7_angle_words"], [(0, 0, 0, 32767)])
        path = Path(__file__).resolve().parents[2] / "animation/rig/skin_oracle.py"
        spec = importlib.util.spec_from_file_location("independent_skin_oracle", path)
        oracle = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(oracle)
        matrices, error = oracle.decode_global_bind(s["parentList"], struct.pack("<4h", 0, 0, 0, 32767),
                                                    s["tagPositions"], s["baseMat"])
        self.assertEqual(error, 0)
        self.assertEqual(oracle.transform(matrices[1], (1, 2, 3)), [1., 2., 7.])
        # The independent reader exposes both hypotheses; this fixture cannot
        # choose the engine convention. A pure +255 X pose makes them distinct.
        wire = bytes.fromhex("0000010040000000")
        pose = [matrices[0], oracle.rigid_matrix((0, 0, 0, 1), (255, 0, 4))]
        for direction, expected in (("first", 191.), ("second", 64.)):
            w = oracle.decode_one_two_blend(wire, [0, 1, 0, 0, 0, 0, 0, 0], 2, direction)
            self.assertEqual(oracle.linear_blend([[0, 0, 4]], w, matrices, pose), [[expected, 0., 4.]])

    def test_skeleton_bad_arrays(self):
        for field in ("parentList", "tagAngles", "tagPositions", "partClassification", "baseMat"):
            for change in (lambda b: b[:-1], lambda b: b + b"\0"):
                with self.subTest(field=field):
                    s = fixtures.skeleton()
                    s[field] = change(s[field])
                    self.refused("array_length", preflight_skeleton, s)

    def test_skeleton_structure_refusals(self):
        cases = [("numBones", True, "integer_range"), ("numBones", 256, "integer_range"),
                 ("numRootBones", 2, "root_profile"), ("numCosmeticBones", 1, "cosmetic_bones"),
                 ("positionLayout", "native-xyz12", "position_stride_unresolved"),
                 ("parentList", b"\0", "parent_distance"), ("parentList", b"\2", "parent_distance"),
                 ("names", ["same", "same"], "bone_names"),
                 ("names", ["tag_origin", "bad\0name"], "bone_names"),
                 ("tagAngles", struct.pack("<4e", 0, 0, 0, float("nan")), "quaternion"),
                 ("tagAngles", struct.pack("<4e", 0, 0, 0, 0), "quaternion"),
                 ("tagPositions", struct.pack("<3f", 0, 0, float("inf")), "nonfinite_position")]
        for field, value, code in cases:
            with self.subTest(field=field, value=value):
                s = fixtures.skeleton()
                s[field] = value
                self.refused(code, preflight_skeleton, s)

    def test_literal_blend_one_through_four_independent_reader(self):
        payload = b"".join(fixtures.weight(v, i) for v, i in (
            ((255,), (3,)), ((64, 191), (0, 1)), ((32, 64, 159), (0, 1, 2)), ((1, 2, 3, 249), (0, 1, 2, 3))))
        report = preflight_weights(payload, 4, 4)
        # Literal wire, independent of implementation's interleaving algorithm.
        wire = bytes.fromhex("03000000 0000010040000000 000001002000020040000000 00000100010002000200030003000000")
        decoded = read_blend(wire, [1, 1, 1, 1], 4)
        self.assertEqual([r["iw7_words"] for r in report["rows"]], [r["words"] for r in decoded])
        self.assertEqual([r["residual"] for r in decoded], [255, 191, 159, 249])

    def test_weight_refusals(self):
        cases = [((0, 0, 0, 0), (0, 0, 0, 0), "weight_holes"),
                 ((64, 0, 191, 0), (0, 0, 1, 0), "weight_holes"),
                 ((64, 190), (0, 1), "weight_sum"),
                 ((64, 191), (1, 1), "weight_bone_ids"),
                 ((64, 191), (0, 2), "weight_bone_ids"),
                 ((255, 0), (0, 1), "inactive_weight_id")]
        for values, ids, code in cases:
            with self.subTest(code=code):
                self.refused(code, preflight_weights, fixtures.weight(values, ids), 1, 2)
        self.refused("weight_vertex_order_loss", preflight_weights, fixtures.ungrouped_surface()["weights"], 3, 2)
        self.refused("array_length", preflight_weights, fixtures.grouped_weights()[:-1], 3, 2)
        self.refused("integer_range", preflight_weights, b"", True, 2)

    def test_independent_reader_refuses_malformed_wire(self):
        good = bytes.fromhex("0000010040000000")
        for wire in (good[:-1], good + b"\0", good[:-2] + b"\1\0",
                     bytes.fromhex("0000000040000000"), bytes.fromhex("0000020040000000"),
                     bytes.fromhex("0000010000000000"), bytes.fromhex("00000100ff000000")):
            with self.subTest(wire=wire), self.assertRaises(ValueError):
                read_blend(wire, [0, 1, 0, 0], 2)
        with self.assertRaises(ValueError):
            read_blend(good, [0, True, 0, 0], 2)

    def test_original_clip_prefix(self):
        report = self.clip(fixtures.clip())
        self.assertEqual(report["rotation_words"], [(0, 0, 0, 32767), (0, 0, 32767, 0), (0, 0, 0, 32767)])
        self.assertEqual(report["random_short_words_consumed"], 12)
        self.assertEqual(report["uninterpreted_schedule_bytes"], 3)
        self.assertFalse(report["clip_semantics_complete"])
        self.assertFalse(report["ready"])

    def test_all_four_counter_losses_before_any_array_read(self):
        for field in NARROWED:
            c = fixtures.clip()
            c[field] = 65536
            self.assertEqual(c[field] & 0xFFFF, 0)  # exact unsigned narrowing
            self.refused("counter_uint16_loss", self.clip, c)
        c = fixtures.clip()
        c["dataByteCount"], c["dataByte"] = 65535, b"\0" * 65535
        self.assertTrue(self.clip(c)["component_checks_passed"])

    def test_clip_discarded_features_are_refused(self):
        for field in tuple(f for f in FLAGS if f != "bLoop") + ABSENT:
            c = fixtures.clip()
            c[field] = True
            self.refused("channel_or_delta_loss", self.clip, c)
        for field in ZERO_COUNTS:
            c = fixtures.clip()
            c[field] = 1
            self.refused("channel_or_metadata_loss", self.clip, c)
        for field in ("primedLength", "loopEntryTime"):
            c = fixtures.clip()
            c[field] = 1.
            self.refused("timing_metadata_loss", self.clip, c)
        c = fixtures.clip()
        c["extraChannelDataCount"], c["extraChannelData"] = 1, b"\x42"
        self.refused("extra_channel_loss", self.clip, c)

    def test_clip_bounded_prefix_and_loss_cases(self):
        cases = [({"dataShort": b"", "dataShortCount": 0}, "random_short_copy_loss"),
                 ({"dataShort": struct.pack("<H", 3)}, "frame_sample_count"),
                 ({"randomDataShort": b"\0" * 22, "randomDataShortCount": 11}, "short_prefix_truncated"),
                 ({"dataShort": b"\2\0\0\0", "dataShortCount": 2}, "short_tail_unsupported"),
                 ({"randomDataShort": b"\0" * 24}, "quaternion"),
                 ({"framerate": float("nan")}, "clip_rate"),
                 ({"bLoop": 1}, "boolean_field"),
                 ({"numframes": True}, "integer_range"),
                 ({"randomDataShortCount": 0xFFFFFFFF}, "clip_byte_budget"),
                 ({"boneCount": [256, 0, 1, 0, 0, 0, 0, 0, 2, 2]}, "bone_counter_uint8_loss"),
                 ({"boneCount": [1, 0, 1, 0, 0, 1, 0, 0, 1, 2]}, "translation_unsupported"),
                 ({"names": ["tag_origin", "missing"]}, "clip_binding")]
        for changes, code in cases:
            with self.subTest(changes=changes):
                c = fixtures.clip()
                c.update(changes)
                self.refused(code, self.clip, c)

    def test_wide_frame_prefix_is_bounded_and_schedule_stays_unverified(self):
        c = fixtures.clip()
        c.update(numframes=256, dataShort=struct.pack("<2H", 2, 256), dataShortCount=2,
                 indices=struct.pack("<3H", 0, 128, 256), indexCount=3)
        self.assertFalse(self.clip(c)["key_schedule_verified"])
        c["dataShort"] = struct.pack("<2H", 2, 257)
        self.refused("frame_index_range", self.clip, c)

    def test_static_rotation_prefix(self):
        c = fixtures.clip()
        c.update(boneCount=[0, 0, 0, 1, 1, 0, 0, 0, 2, 2], dataShortCount=6,
                 dataShort=struct.pack("<6e", 0, 1, 0, 0, -1, 0), randomDataShort=b"", randomDataShortCount=0)
        self.assertEqual(self.clip(c)["rotation_words"], [(0, 32767), (0, 0, -32767, 0)])

    def test_unknown_fields_not_silently_ignored(self):
        for factory, function in ((fixtures.skeleton, preflight_skeleton), (fixtures.clip, self.clip),
                                  (fixtures.ungrouped_surface, regroup_surface)):
            s = factory()
            s["unrecognized_channel"] = b"\1"
            self.refused("snapshot_schema", function, s)

    def test_reproduced_order_loss_and_exact_repair(self):
        s = fixtures.ungrouped_surface()
        original = copy.deepcopy(s)
        rows = decode_stream_weights(s["weights"], 3, 2)
        converter_order = sorted(rows, key=lambda r: r["influences"])
        # Literal expected old vertex IDs: converter currently attaches these
        # weight rows to unchanged vertices [0,1,2]. Both first two are wrong.
        self.assertEqual([r["vertex"] for r in converter_order], [1, 0, 2])
        self.assertEqual(converter_order[0]["ids"], (1,))
        self.assertEqual(rows[0]["ids"], (0, 1))
        report = regroup_surface(s)
        out = report["snapshot"]
        self.assertEqual(report["new_to_old"], [1, 0, 2])
        self.assertEqual(out["triangles"], bytes.fromhex("010000000200"))
        self.assertEqual(out["attributes"], bytes(range(16, 32)) + bytes(range(16)) + bytes(range(32, 48)))
        preflight_weights(out["weights"], 3, 2)
        self.assertEqual(s, original)
        self.assertFalse(report["native_patch_applied"])

    def test_repair_preserves_every_triangle_corner_and_attribute_for_64_class_sequences(self):
        for classes in itertools.product(range(1, 5), repeat=3):
            s = fixtures.ungrouped_surface()
            s["boneCount"] = 4
            s["weights"] = b"".join(fixtures.weight((1,) * (n - 1) + (256 - n,), tuple(range(n))) for n in classes)
            out = regroup_surface(s)["snapshot"]
            remapped = struct.unpack("<3H", out["triangles"])
            for old, new in enumerate(remapped):
                for field, stride in (("positions", 12), ("attributes", 16), ("weights", 12)):
                    self.assertEqual(s[field][old * stride:(old + 1) * stride], out[field][new * stride:(new + 1) * stride])
            preflight_weights(out["weights"], 3, 4)

    def test_repair_refuses_unknown_data_rigid_lists_and_indices(self):
        for field, value, code in (("vertListCount", 1, "surface_profile"), ("sharedFlags", 1, "surface_profile"),
                                   ("surfaceFlags", 34, "surface_profile"), ("triangles", b"\0\0\1\0\3\0", "triangle_index"),
                                   ("partBits", b"\0" * 47 + b"\1", "part_bits_loss")):
            s = fixtures.ungrouped_surface()
            s[field] = value
            self.refused(code, regroup_surface, s)


if __name__ == "__main__":
    unittest.main()

"""Input geometry/byte mutation tests; deliberately rehash invalid semantics."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from prepare_skin_fixture import fixture_files, manifest, INTERFACES
from read_skin_fixture import parse, read, verify_payloads


def candidate():
    files = fixture_files()
    return files, manifest(files, {name: "a" * 64 for name in INTERFACES})


def rehash(meta, files, name):
    meta["files"][name] = {"bytes": len(files[name]), "sha256": hashlib.sha256(files[name]).hexdigest()}


class SkinFixtureTests(unittest.TestCase):
    def test_two_literal_weight_hypotheses(self):
        files, meta = candidate()
        mono = bytes.fromhex("00000000 00000000 01000000 01000000")
        low = bytes.fromhex("0000010040000000")
        high = bytes.fromhex("00000100bf000000")
        self.assertEqual(files["first.blend.u16.bin"], mono + high * 2 + low * 2)
        self.assertEqual(files["second.blend.u16.bin"], mono + low * 2 + high * 2)
        report = verify_payloads(files, meta)
        self.assertEqual(set(report["profiles"]), {"first", "second"})
        for profile in report["profiles"].values():
            self.assertLess(profile["quantization_error_units"], .005)
            self.assertGreater(profile["opposite_weight_error_units"], 1)
        self.assertTrue(report["geometry_bytes_verified"])
        self.assertFalse(report["native_asset_read"])

    def test_actual_input_files_read_with_exact_inventory(self):
        files, meta = candidate()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, payload in files.items():
                (root / name).write_bytes(payload)
            (root / "fixture-input.json").write_text(json.dumps(meta), encoding="utf-8")
            self.assertTrue(read(root)["input_only"])
            (root / "foreign.cpp").write_text("original test", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "inventory"): read(root)

    def test_rehashed_geometry_position_corruption(self):
        files, meta = candidate()
        changed = bytearray(files["positions.f32.bin"])
        struct.pack_into("<f", changed, 32, 15)
        files["positions.f32.bin"] = bytes(changed)
        rehash(meta, files, "positions.f32.bin")
        with self.assertRaisesRegex(ValueError, "actual positions"): verify_payloads(files, meta)

    def test_rehashed_triangle_reversal(self):
        files, meta = candidate()
        changed = bytearray(files["triangles.u16.bin"])
        struct.pack_into("<3H", changed, 0, 0, 1, 4)
        files["triangles.u16.bin"] = bytes(changed)
        rehash(meta, files, "triangles.u16.bin")
        with self.assertRaisesRegex(ValueError, "triangle indexing"): verify_payloads(files, meta)

    def test_rehashed_uv_flip(self):
        files, meta = candidate()
        changed = bytearray(files["uv.f32.bin"])
        struct.pack_into("<f", changed, 4, 1)
        files["uv.f32.bin"] = bytes(changed)
        rehash(meta, files, "uv.f32.bin")
        with self.assertRaisesRegex(ValueError, "UVs"): verify_payloads(files, meta)

    def test_rehashed_normal_corruption(self):
        files, meta = candidate()
        files["normals.f32.bin"] = b"\0" * 96
        rehash(meta, files, "normals.f32.bin")
        with self.assertRaisesRegex(ValueError, "plane normal"): verify_payloads(files, meta)

    def test_blend_group_count_includes_mono_vertices(self):
        files, meta = candidate()
        meta["counts"]["vertices"] = 4
        with self.assertRaisesRegex(ValueError, "skin counts"): verify_payloads(files, meta)

    def test_boolean_count_not_integer(self):
        files, meta = candidate()
        meta["counts"]["roots"] = True
        with self.assertRaisesRegex(ValueError, "typed skin counts"): verify_payloads(files, meta)

    def test_runtime_proof_claims_refused(self):
        files, original = candidate()
        for key in ("pixels_verified", "ff_built", "ready", "native_writer_executed", "part_bits_engine_verified"):
            meta = copy.deepcopy(original)
            meta[key] = True
            with self.assertRaisesRegex(ValueError, "proof boundary"): verify_payloads(files, meta)

    def test_rigid_or_reactive_flags_refused(self):
        files, original = candidate()
        for flags in (0x82, 0x8E, 0xC6):
            meta = copy.deepcopy(original)
            meta["native_surface_flags_proposed"] = flags
            with self.assertRaisesRegex(ValueError, "skinned flags"): verify_payloads(files, meta)
        meta = copy.deepcopy(original)
        meta["native_model_has_rigid_list_proposed"] = True
        with self.assertRaises(ValueError): verify_payloads(files, meta)

    def test_blend_hypotheses_cannot_be_silently_aliased(self):
        files, meta = candidate()
        files["first.blend.u16.bin"] = files["second.blend.u16.bin"]
        rehash(meta, files, "first.blend.u16.bin")
        with self.assertRaisesRegex(ValueError, "deformation tolerance"): verify_payloads(files, meta)

    def test_rehashed_bind_inverse_rejected(self):
        files, meta = candidate()
        changed = bytearray(files["base-mats.f32.bin"])
        struct.pack_into("<f", changed, 56, -8)
        files["base-mats.f32.bin"] = bytes(changed)
        rehash(meta, files, "base-mats.f32.bin")
        with self.assertRaisesRegex(ValueError, "positive global bind"): verify_payloads(files, meta)

    def test_distinct_candidate_names_and_schema(self):
        files, meta = candidate()
        meta["profiles"]["first"]["name"] = "paris_doom_helmet_rigid_a"
        with self.assertRaisesRegex(ValueError, "profile identity"): verify_payloads(files, meta)
        _, meta = candidate()
        meta["schema"] = "iw7.doom-rigid-writer-source/1"
        with self.assertRaisesRegex(ValueError, "distinct source-input"): verify_payloads(files, meta)

    def test_receipt_mismatch(self):
        files, meta = candidate()
        meta["files"]["positions.f32.bin"]["sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "physical stream receipt"): verify_payloads(files, meta)
        _, meta = candidate()
        meta["files"]["parents.u8.bin"]["bytes"] = True
        with self.assertRaisesRegex(ValueError, "physical stream receipt"): verify_payloads(files, meta)

    def test_rehashed_source_weights_differ_from_ideal(self):
        files, meta = candidate()
        source = json.loads(files["geometry.source.json"])
        source["vertices"][4]["weights"] = [{"bone": 0, "weight": .25}, {"bone": 1, "weight": .75}]
        files["geometry.source.json"] = json.dumps(source).encode()
        rehash(meta, files, "geometry.source.json")
        with self.assertRaisesRegex(ValueError, "ideal source weights"): verify_payloads(files, meta)

    def test_rehashed_boolean_parent_and_coordinate_refused(self):
        original, original_meta = candidate()
        for field in ("parent", "coordinate"):
            files, meta = copy.deepcopy(original), copy.deepcopy(original_meta)
            source = json.loads(files["geometry.source.json"])
            if field == "parent": source["bones"][1]["parent"] = False
            else: source["vertices"][0]["xyz"][0] = False
            files["geometry.source.json"] = json.dumps(source).encode()
            rehash(meta, files, "geometry.source.json")
            with self.assertRaises(ValueError): verify_payloads(files, meta)

    def test_missing_stream_or_interface_inventory(self):
        files, meta = candidate()
        del files["first.blend.u16.bin"]
        with self.assertRaisesRegex(ValueError, "stream inventory"): verify_payloads(files, meta)
        files, meta = candidate()
        del meta["interface_hashes"]["iw7/structs.hpp"]
        with self.assertRaisesRegex(ValueError, "interface receipt"): verify_payloads(files, meta)

    def test_duplicate_keys_and_nonfinite_json_rejected(self):
        for payload in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}'):
            with self.assertRaises(ValueError): parse(payload)


if __name__ == "__main__":
    unittest.main()

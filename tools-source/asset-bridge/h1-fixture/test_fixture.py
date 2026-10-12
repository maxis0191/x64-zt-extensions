"""Light source/format tests only; no production C++ parser/converter execution."""
import hashlib
import json
from pathlib import Path
import struct
import unittest

import generate
from inspect_fixture import Reader, inspect_model, inspect_pair, inspect_surface


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.model = generate.model_bytes()
        self.surface = generate.surface_bytes()

    def test_independent_geometry_and_dependency_inspection(self):
        result = inspect_pair(self.model,self.surface)
        self.assertEqual(result["surface"]["geometry_uv_frames_checked"],12)
        self.assertFalse(result["native_validation"])
        self.assertFalse(result["complete_material"])

    def test_literal_source_grammar_and_sizes(self):
        self.assertEqual(self.model[:6],b"\x08\x01\x01\x00\x00\x00")
        self.assertEqual(self.model[686:688],b"\x06\x01")
        self.assertEqual(self.surface[:6],b"\x08\x01\x01\x00\x00\x00")
        self.assertEqual(self.surface[62:64],b"\x06\x01")
        self.assertLess(len(self.model)+len(self.surface),4096)

    def test_literal_h1_axis_words(self):
        self.assertEqual(generate.packed_axis((1,0,0)),0xE00803FF)
        self.assertEqual(generate.packed_axis((0,0,1)),0xFFF80200)
        self.assertEqual(generate.packed_axis((0,0,-1)),0xC0080200)
        # Endpoints are exactly representable as half floats; no rounding claim.
        self.assertEqual(struct.pack("<2e",1,0),b"\x00\x3c\x00\x00")

    def test_every_truncated_prefix_is_rejected(self):
        for payload, reader in ((self.model,inspect_model),(self.surface,inspect_surface)):
            for cut in range(len(payload)):
                with self.assertRaises((ValueError,UnicodeDecodeError)):
                    reader(payload[:cut])

    def test_trailing_bytes_and_wrong_record_tags(self):
        for payload, reader in ((self.model,inspect_model),(self.surface,inspect_surface)):
            with self.assertRaises(ValueError):
                reader(payload+b"\0")
            _,records = reader(payload)
            for offset in records.values():
                broken = bytearray(payload); broken[offset] = 9
                with self.assertRaises(ValueError):
                    reader(broken)

    def test_oversized_count_and_invalid_existence(self):
        for count in (0,2,0xFFFFFFFF):
            broken = bytearray(self.model); struct.pack_into("<I",broken,2,count)
            with self.assertRaises(ValueError):
                inspect_model(broken)
        broken = bytearray(self.model); broken[1] = 2
        with self.assertRaises(ValueError):
            inspect_model(broken)

    def test_model_reference_and_pointer_corruption(self):
        broken = self.model.replace(b"paris_h1_original_material",b"paris_h1_original_materiax")
        with self.assertRaisesRegex(ValueError,"name mismatch"):
            inspect_model(broken)
        broken = bytearray(self.model); broken[6+56] = 1
        with self.assertRaisesRegex(ValueError,"pointer"):
            inspect_model(broken)

    def test_geometry_nonfinite_and_out_of_bounds_indices(self):
        _,records = inspect_surface(self.surface)
        for field, fmt, value in (("vertices","f",float("nan")),("triangles","H",24)):
            broken = bytearray(self.surface)
            struct.pack_into("<"+fmt,broken,records[field]+6,value)
            with self.assertRaises(ValueError):
                inspect_surface(broken)

    def test_normal_and_uv_corruption_fail_geometric_oracle(self):
        _,records = inspect_surface(self.surface)
        # First face lies at +Z. Literal -Z packed word must fail independently.
        broken = bytearray(self.surface)
        struct.pack_into("<I",broken,records["vertices"]+6+24,0xC0080200)
        with self.assertRaisesRegex(ValueError,"geometry/UV frame"):
            inspect_surface(broken)
        broken = bytearray(self.surface)
        for i in range(4):
            struct.pack_into("<2e",broken,records["vertices"]+6+i*32+20,0,0)
        with self.assertRaisesRegex(ValueError,"degenerate UV"):
            inspect_surface(broken)

    def test_rigid_and_optional_stream_guards(self):
        _,records = inspect_surface(self.surface)
        broken = bytearray(self.surface)
        struct.pack_into("<H",broken,records["rigid_lists"]+6,64)
        with self.assertRaisesRegex(ValueError,"rigid vertex coverage"):
            inspect_surface(broken)
        broken = bytearray(self.surface); broken[records["blend"]+1] = 1
        with self.assertRaisesRegex(ValueError,"optional raw stream"):
            inspect_surface(broken)

    def test_input_bound(self):
        with self.assertRaises(ValueError):
            Reader(bytes(1024*1024+1))

    def test_deterministic_golden_files(self):
        golden = json.loads(Path(__file__).with_name("validation.json").read_text())
        for name,data in generate.build_payloads().items():
            self.assertEqual(len(data),golden["files"][name]["bytes"])
            self.assertEqual(hashlib.sha256(data).hexdigest(),golden["files"][name]["sha256"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

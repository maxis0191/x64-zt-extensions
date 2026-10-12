"""Hand-built original dump fixtures, not a production writer/retail payload."""
import copy
import math
import struct
import unittest
from prepare_skin_fixture import fixture_files
from read_skin_native import Reader, packed_unit, verify_outputs


def array(width, values, count):
    return b"\x08\x01" + struct.pack("<I", count) + values if count else b"\x08\x00"


def raw(values):
    return b"\x0a\x01" + struct.pack("<I", len(values)) + values if values else b"\x0a\x00"


def name(value, kind=6):
    return bytes([kind, 0]) if value is None else bytes([kind, 1]) + value.encode() + b"\0"


def synthetic(hypothesis="second"):
    inputs = fixture_files()
    model_name = "paris_doom_skin_two_bone_" + hypothesis + "_a"
    outer = bytearray(56)
    struct.pack_into("<QQH", outer, 0, 0x1111, 0x2222, 1)
    struct.pack_into("<I", outer, 20, 0xC0000000)
    surface = bytearray(256)
    struct.pack_into("<HHHBB8HI", surface, 0, 0x86, 8, 6, 0, 0, 4, 4, 0, 0, 0, 0, 0, 0, 48)
    for offset in (32, 40, 80): struct.pack_into("<Q", surface, offset, 0x3333 + offset)
    struct.pack_into("<I", surface, 224, 0xC0000000)
    # Fixed literal half pairs: U={0,1}, V={0,1,.25,.75}. No half/normal packer.
    uv_words = (0, 0x3C00, 0x3C000000, 0x3C003C00, 0x34000000, 0x34003C00, 0x3A000000, 0x3A003C00)
    vertices = b"".join(inputs["positions.f32.bin"][12 * i:12 * (i + 1)] + struct.pack("<5I", 0x01FE0100, 0xFFFFFFFF, uv_words[i], 0xE0080000, 0x200FFE00) for i in range(8))
    xsb = array(56, outer, 1) + name(model_name + "_lod0") + array(256, surface, 1) + array(32, vertices, 8)
    xsb += array(6, inputs["triangles.u16.bin"], 6) + array(16, b"", 0) + raw(inputs[hypothesis + ".blend.u16.bin"]) + raw(b"") * 3
    model = bytearray(736)
    model[9], model[11], model[12], model[13], model[20], model[21] = 1, 1, 255, 6, 2, 1
    struct.pack_into("<Hf", model, 26, 1, 1)
    struct.pack_into("<7f", model, 40, math.sqrt(272), 0, 0, 8, 0, 4, 8)
    for offset in (0, 152, 160, 168, 176, 184, 192, 216, 232, 616, 624): struct.pack_into("<Q", model, offset, 0x4444 + offset)
    struct.pack_into("<fHH", model, 224, 1000000, 1, 0)
    struct.pack_into("<I", model, 240, 0xC0000000)
    model[704], model[720] = 255, 255
    xmb = array(736, model, 1) + name(model_name) + name("tag_origin") + name("tag_probe")
    xmb += array(1, inputs["parents.u8.bin"], 1) + array(8, inputs["tag-angles.i16.bin"], 1) + array(12, inputs["tag-positions.f32.bin"], 1)
    xmb += array(1, b"\0\0", 2) + array(32, inputs["base-mats.f32.bin"], 2)
    xmb += array(32, b"", 0) + array(1, b"", 0) + array(36, b"", 0)
    infos = struct.pack("<14f", 0, 0, 8, 0, 4, 8, 272, 0, 0, 0, 0, 4, 8, 80)
    xmb += array(28, infos, 2) + array(2, b"\0\0", 1) + array(8, struct.pack("<Q", 0x5555), 1)
    xmb += name("mopw/character_park_clown_zombie_shoes", 7) + name(model_name + "_lod0", 7) + name(None, 7) * 9
    xmb += array(1, b"", 0) * 3
    return xmb, xsb, inputs


def surface_offsets(xsb):
    # Walk only fixture framing to locate records for focused mutations.
    pos = 6 + 56
    pos = xsb.index(b"\0", pos + 2) + 1
    surface = pos + 6
    vertices = surface + 256 + 6
    triangles = vertices + 256 + 6
    blend = triangles + 36 + 2 + 6
    return surface, vertices, triangles, blend


class NativeSkinTests(unittest.TestCase):
    def test_complete_original_fixtures_both_profiles(self):
        for hypothesis in ("first", "second"):
            xmb, xsb, inputs = synthetic(hypothesis)
            report = verify_outputs(xmb, xsb, inputs, hypothesis)
            self.assertTrue(report["model"]["complete_model_bytes_read"])
            self.assertTrue(report["surface"]["source_codec_words_verified"])
            self.assertLess(report["surface"]["normal_tangent_component_error"], .001)
            self.assertFalse(report["surface"]["iw7_shader_encoding_verified"])
            self.assertFalse(report["native_writer_receipt_verified"])
            self.assertFalse(report["draw_verified"])

    def test_axis_words_decoded_without_packer(self):
        n, alpha_n = packed_unit(0xE0080000)
        t, alpha_t = packed_unit(0x200FFE00)
        self.assertEqual(n[0], -1)
        self.assertEqual(t[1], 1)
        self.assertEqual((alpha_n, alpha_t), (3, 0))
        self.assertAlmostEqual(n[1], 1 / 1023)
        self.assertAlmostEqual(t[0], 1 / 1023)

    def test_surface_count_flags_blend_size_rejected(self):
        xmb, xsb, inputs = synthetic()
        s, _, _, _ = surface_offsets(xsb)
        for offset, fmt, value in ((0, "H", 0x82), (2, "H", 4), (6, "B", 1), (24, "I", 49)):
            bad = bytearray(xsb); struct.pack_into("<" + fmt, bad, s + offset, value)
            with self.assertRaises(ValueError): verify_outputs(xmb, bytes(bad), inputs, "second")

    def test_gpu_optional_rigid_pointers_rejected(self):
        xmb, xsb, inputs = synthetic()
        s, _, _, _ = surface_offsets(xsb)
        for offset in (48, 72, 88, 96, 104, 128, 136, 144, 200):
            bad = bytearray(xsb); struct.pack_into("<Q", bad, s + offset, 1234)
            with self.assertRaisesRegex(ValueError, "unexpected native field"): verify_outputs(xmb, bytes(bad), inputs, "second")

    def test_missing_cpu_vertex_or_blend_pointer_rejected(self):
        xmb, xsb, inputs = synthetic()
        s, _, _, _ = surface_offsets(xsb)
        for offset in (32, 40, 80):
            bad = bytearray(xsb); struct.pack_into("<Q", bad, s + offset, 0)
            with self.assertRaisesRegex(ValueError, "pointer presence"): verify_outputs(xmb, bytes(bad), inputs, "second")

    def test_actual_vertex_position_uv_and_normal_corruption(self):
        xmb, xsb, inputs = synthetic()
        _, v, _, _ = surface_offsets(xsb)
        for offset, word in ((0, 0x3F800000), (20, 0x3C000000), (24, 0xFFFFFFFF), (28, 0xE00FFE00)):
            bad = bytearray(xsb); struct.pack_into("<I", bad, v + offset, word)
            with self.assertRaises(ValueError): verify_outputs(xmb, bytes(bad), inputs, "second")

    def test_profile_bytes_cannot_be_swapped(self):
        xmb, xsb, inputs = synthetic()
        _, _, _, b = surface_offsets(xsb)
        bad = xsb[:b] + inputs["first.blend.u16.bin"] + xsb[b + 48:]
        with self.assertRaisesRegex(ValueError, "profile blend"): verify_outputs(xmb, bad, inputs, "second")

    def test_actual_native_triangle_mismatch(self):
        xmb, xsb, inputs = synthetic()
        _, _, t, _ = surface_offsets(xsb)
        bad = bytearray(xsb); struct.pack_into("<3H", bad, t, 0, 1, 4)
        with self.assertRaisesRegex(ValueError, "triangles"): verify_outputs(xmb, bytes(bad), inputs, "second")

    def test_mutated_inputs_do_not_make_mutated_geometry_original(self):
        xmb, xsb, inputs = synthetic()
        _, v, _, _ = surface_offsets(xsb)
        inputs = copy.deepcopy(inputs)
        bad = bytearray(inputs["positions.f32.bin"]); struct.pack_into("<f", bad, 0, 1)
        inputs["positions.f32.bin"] = bytes(bad)
        changed = bytearray(xsb); struct.pack_into("<f", changed, v, 1)
        with self.assertRaisesRegex(ValueError, "independently fixed position"): verify_outputs(xmb, bytes(changed), inputs, "second")

    def test_model_rigid_flags_bone_counts_and_lod_descriptor(self):
        xmb, xsb, inputs = synthetic()
        for offset, fmt, value in ((16, "I", 0x80000), (20, "B", 1), (24, "H", 1), (224, "f", 0), (240, "I", 0x80000000)):
            bad = bytearray(xmb); struct.pack_into("<" + fmt, bad, 6 + offset, value)
            with self.assertRaises(ValueError): verify_outputs(bytes(bad), xsb, inputs, "second")

    def test_extra_model_dependencies_and_missing_bind_pointer(self):
        xmb, xsb, inputs = synthetic()
        for offset, value in ((192, 0), (200, 17), (272, 17), (632, 17), (648, 17), (728, 17)):
            bad = bytearray(xmb); struct.pack_into("<Q", bad, 6 + offset, value)
            with self.assertRaises(ValueError): verify_outputs(bytes(bad), xsb, inputs, "second")

    def test_model_shadow_bounds_and_unused_indices(self):
        xmb, xsb, inputs = synthetic()
        for offset, fmt, value in ((13, "B", 255), (52, "f", -8), (704, "B", 0), (720, "B", 0)):
            bad = bytearray(xmb); struct.pack_into("<" + fmt, bad, 6 + offset, value)
            with self.assertRaises(ValueError): verify_outputs(bytes(bad), xsb, inputs, "second")

    def test_trailing_and_truncated_native_bytes(self):
        xmb, xsb, inputs = synthetic()
        for m, s in ((xmb + b"x", xsb), (xmb, xsb + b"x"), (xmb[:-1], xsb), (xmb, xsb[:-1])):
            with self.assertRaises(ValueError): verify_outputs(m, s, inputs, "second")

    def test_name_and_material_dependencies_not_replaced(self):
        xmb, xsb, inputs = synthetic()
        for bad in (xmb.replace(b"tag_probe", b"tag_fake_"), xmb.replace(b"character_park", b"character_dark")):
            with self.assertRaisesRegex(ValueError, "exact native"): verify_outputs(bad, xsb, inputs, "second")

    def test_blob_alias_and_count_refused(self):
        xmb, xsb, inputs = synthetic()
        with self.assertRaises(ValueError): Reader(b"\x09" + struct.pack("<II", 0, 0)).array(32, 8)
        bad = bytearray(xmb); struct.pack_into("<I", bad, 2, 2)
        with self.assertRaisesRegex(ValueError, "blob count"): verify_outputs(bytes(bad), xsb, inputs, "second")

    def test_typed_name_aliases_bounded(self):
        reader = Reader(name("original") + b"\x09" + struct.pack("<II", 0, 0))
        self.assertEqual(reader.name(expected="original"), "original")
        self.assertEqual(reader.name(expected="original"), "original")
        reader.end()
        for entry, index in ((1, 0), (0, 1)):
            r = Reader(name("original") + b"\x09" + struct.pack("<II", entry, index))
            r.name(expected="original")
            with self.assertRaisesRegex(ValueError, "alias"): r.name(expected="original")


if __name__ == "__main__":
    unittest.main()

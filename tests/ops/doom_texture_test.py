"""Asset-free tests for color/alpha/mip inversion and distinct asset names."""
import importlib.util
import json
import struct
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("negative", ROOT / "ops/doom-textures/prepare_negative.py")
negative = importlib.util.module_from_spec(spec)
spec.loader.exec_module(negative)


def image_dump(name, pixels, width, height, mips, dxgi=28):
    image = bytearray(112)
    struct.pack_into("<I", image, 24, dxgi)
    struct.pack_into("<II4H", image, 40, len(pixels), len(pixels), width, height, 1, 1)
    image[56] = mips
    struct.pack_into("<Q", image, 64, 1)
    return b"\x08\x01\x01\0\0\0" + image + b"\x06\x01" + name.encode() + b"\0\x08\x01" + struct.pack("<I", len(pixels)) + pixels


class NegativeTests(unittest.TestCase):
    def test_rgba_all_mips_and_alpha(self):
        source = bytes((0, 255, 13, 0, 24, 100, 250, 127, 65, 66, 67, 255, 255, 0, 255, 4, 44, 55, 66, 200))
        result = negative.negative_mips(source, 2, 2, 2, 28)
        self.assertEqual(len(result), len(source))
        self.assertEqual(result[3::4], source[3::4])
        for channel in range(3):
            self.assertEqual(bytes(a + b for a, b in zip(source[channel::4], result[channel::4])), bytes([255] * 5))

    def test_bc1_transparency_preserved(self):
        # 3-color DXT1, indices all transparent. Alpha stays zero after RGB inversion.
        result = negative.negative_mips(struct.pack("<HHI", 0, 0, 0xFFFFFFFF), 4, 4, 1, 71)
        self.assertEqual(result[3::4], bytes(16))
        self.assertEqual(result[0::4], bytes([255] * 16))

    def test_bc3_alpha_and_bc7_decoder(self):
        block = bytes((42, 99)) + bytes(6) + struct.pack("<HHI", 0xF800, 0x07E0, 0)
        result = negative.negative_mips(block, 4, 4, 1, 77)
        self.assertEqual(result[:4], bytes((0, 255, 255, 42)))
        result = negative.negative_mips(bytes((0x40,)) + bytes(15), 4, 4, 1, 98)
        self.assertEqual(len(result), 64)

    def test_rejects_bad_size_and_normal_encoding(self):
        for pixels, width, height, mips, fmt in ((bytes(3), 1, 1, 1, 28), (bytes(5), 1, 1, 1, 28), (bytes(16), 4, 4, 1, 83)):
            with self.assertRaises(ValueError):
                negative.negative_mips(pixels, width, height, mips, fmt)

    def test_resident_output_and_original_immutable(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, target = root / "test.iw7Image", root / "doom_negative_test.iw7Image"
            original = image_dump("test", bytes((1, 2, 3, 77)), 1, 1, 1)
            source.write_bytes(original)
            report = negative.invert_image(source, target)
            header, pixels, width, height, mips = negative.read_image(target)
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(pixels, bytes((254, 253, 252, 77)))
            self.assertEqual((width, height, mips, header[57]), (1, 1, 1, 0))
            self.assertEqual(header[:24], bytes(24))
            self.assertEqual(report["original"], "test")

    def test_tagged_aliases_do_not_replace_substrings(self):
        raw = b"\x06\x01body\0\x07\x01skin\0\x07\x01skin_extra\0"
        result = negative.rename_records(raw, "body", {"skin"})
        self.assertEqual(result, b"\x06\x01doom_negative_body\0\x07\x01doom_negative_skin\0\x07\x01skin_extra\0")
        with self.assertRaises(ValueError):
            negative.rename_records(raw + b"\x06\x01body\0", "body", {"skin"})

    def test_color_selection_requires_review_for_shader_specific_maps(self):
        bindings = [dict(image="skin", semantic="2"), dict(image="packed_c_misc", semantic="0"),
                    dict(image="glow_e", semantic="0"), dict(image="normal", semantic="5")]
        self.assertEqual(negative.color_images(bindings), {"skin"})
        self.assertEqual(negative.color_images(bindings, ["glow_e"]), {"skin", "glow_e"})
        for requested in (["missing"], ["normal"]):
            with self.assertRaises(ValueError):
                negative.color_images(bindings, requested)
        with self.assertRaises(ValueError):
            negative.color_images(bindings + [dict(image="skin", semantic="5")])

    def test_pack_preserves_stock_references_and_registry(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, captured, output = root / "source", root / "capture", root / "output"
            for sub in ("xmodel", "materials", "netconststrings", "techsets/state/shader", "techsets/constantbuffer/shader"):
                (source / sub).mkdir(parents=True)
            (captured / "images").mkdir(parents=True)
            (source / "closure.csv").write_text("".join("xmodel," + name + "\n" for name in negative.ROOT_MODELS) + "material,skin\n")
            for name in negative.ROOT_MODELS:
                (source / "xmodel" / (name + ".xmb")).write_bytes(b"\x06\x01" + name.encode() + b"\0\x07\x01skin\0")
            (source / "bindings.csv").write_text("material,image,semantic\nskin,color,2\nskin,normal,5\n")
            (source / "references.csv").write_text("xmodelsurfs,,body_surfaces\n")
            (source / "materials/skin.json").write_text(json.dumps({"techniqueSet->name": "shader", "textureTable": [dict(image="color", semantic=2), dict(image="normal", semantic=5)]}))
            (source / "techsets/state/shader/skin.statebits").write_bytes(b"stock state")
            (source / "techsets/constantbuffer/shader/skin.cbt").write_bytes(b"stock constants")
            (source / "netconststrings/map.json").write_text(json.dumps(dict(stringType=0, sourceType=0, stringList=["original_model"])))
            (captured / "images/color.iw7Image").write_bytes(image_dump("color", bytes((1, 2, 3, 4)), 1, 1, 1))
            report = negative.prepare(source, captured, output)
            rows = (output / "assets.csv").read_text().splitlines()
            first_clone = next(index for index, row in enumerate(rows) if ",," not in row)
            self.assertTrue(all(",," in row for row in rows[:first_clone]))
            self.assertFalse(any(",," in row for row in rows[first_clone:]))
            self.assertIn("image,,normal", rows[:first_clone])
            self.assertIn("techset,,shader", rows[:first_clone])
            self.assertEqual((output / "techsets/state/shader/doom_negative_skin.statebits").read_bytes(), b"stock state")
            self.assertEqual((output / "techsets/constantbuffer/shader/doom_negative_skin.cbt").read_bytes(), b"stock constants")
            registry = json.loads((output / "netconststrings/map.json").read_text())["stringList"]
            self.assertEqual(registry[0], "original_model")
            self.assertEqual(len(registry), 8)
            self.assertFalse(report["gameplay_verified"])
            self.assertFalse(report["external_texture_pack_required"])


if __name__ == "__main__":
    unittest.main()

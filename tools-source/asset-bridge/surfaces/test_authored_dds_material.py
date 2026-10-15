"""Two authored inputs and independent DDS/IW7 header oracles; no native or file IO."""
import copy
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

import authored_dds_material as a


def dds(width=3, height=2, fmt=28, pixels=None, compressed=False):
    # Independent standard DDS writer for this test, not the production encoder.
    if pixels is None:
        pixels = bytes(range(width * height * 4))
    header = [0] * 31
    header[0:7] = [124, 0x1007 | (0x80000 if compressed else 8), height, width,
                   len(pixels) if compressed else width * 4, 0, 1]
    header[18:21] = [32, 4, 0x30315844]
    header[26] = 0x1000
    return b"DDS " + struct.pack("<31I5I", *header, fmt, 3, 0, 1, 0) + pixels


def template():
    material = {}
    material.update({"techniqueSet->name": "iw7_template_technique", "stateFlags": 0,
                     "textureTable": [{"semantic": 15, "image": "iw7_original_normal"},
                                      {"semantic": 14, "image": "old_diffuse"}],
                     "constantTable": None, "subMaterials": None})
    mapping = [{"loadBits": [0] * 6, "depthStencilStateBits": [0] * 14,
                "blendStateBits": [0] * 4, "rasterizerState": 0}]
    return {"material": json.dumps(material).encode(), "statebits": bytes(152),
            "statebitsmap": json.dumps(mapping).encode(), "stateinfo": b'{"stateFlags":0}'}


def prepared(**changes):
    args = dict(zone="author_a", image_name="original_a", material_name="material_a",
                texture_slot=1, dds=dds(), template=template())
    args.update(changes)
    return a.prepare_material(**args)


def iw7_dump(width, height, fmt, pixels, name, semantic):
    scalar = bytearray(112)
    struct.pack_into("<I", scalar, 24, fmt)
    scalar[32:35] = bytes((3, semantic, 3))
    struct.pack_into("<II4H", scalar, 40, len(pixels), len(pixels), width, height, 1, 1)
    scalar[56] = 1
    struct.pack_into("<Q", scalar, 64, 1)
    return (b"\x08\x01\x01\0\0\0" + scalar + b"\x06\x01" + name.encode() + b"\0" +
            b"\x08\x01" + struct.pack("<I", len(pixels)) + pixels)


class AuthoredMaterialTests(unittest.TestCase):
    def test_two_different_projects_preserve_input_bytes_and_use_same_api(self):
        first = dds()
        second = dds(7, 5, 99, bytes(reversed(range(64))), True)
        for zone, name, blob, shape in (("author_a", "red", first, (3, 2, 28, 24)),
                                        ("author_b", "pattern_b", second, (7, 5, 99, 64))):
            source = template(); before = copy.deepcopy(source)
            with patch.object(Path, "open", side_effect=AssertionError("open")), \
                 patch.object(Path, "stat", side_effect=AssertionError("stat")):
                result = prepared(zone=zone, image_name=name, material_name="mat_" + name,
                                  dds=blob, template=source)
            self.assertEqual(source, before)
            self.assertEqual(result["files"][f"images/{name}.dds"], blob)
            self.assertEqual(tuple(result["image"][k] for k in
                                   ("width", "height", "dxgi_format", "pixel_bytes")), shape)
            self.assertEqual(result["material_reference"], "mat_" + name)
            self.assertEqual(result["recipient_references"],
                             {"techset": "iw7_template_technique", "images": ["iw7_original_normal"]})
            self.assertEqual(result["image"]["mip_count"], 1)
            self.assertTrue(all(result[k] is False for k in
                                ("ff_built", "material_verified", "rendered_verified", "ready")))

    def test_explicit_slot_changes_only_its_image_and_renames_sidecars_verbatim(self):
        source = template(); result = prepared(texture_slot=0, template=source)
        expected = json.loads(source["material"])
        expected["textureTable"][0]["image"] = "original_a"
        self.assertEqual(json.loads(result["files"]["materials/material_a.json"]), expected)
        self.assertEqual(result["image"]["iw7_semantic"], 15)
        for role in ("statebits", "statebitsmap", "stateinfo"):
            self.assertEqual(result["files"][f"techsets/state/iw7_template_technique/material_a.{role}"], source[role])
        self.assertIn(b"image,old_diffuse\n", result["files"]["zone_source/author_a_recipient.csv"])

    def test_known_rgba_recipe_reuses_writer_and_roundtrips_unchanged(self):
        pixels = bytes(range(24))
        for srgb, fmt in ((False, 28), (True, 29)):
            image, actual = a.read_dds(a.rgba8_dds(3, 2, pixels, srgb=srgb))
            self.assertEqual((image.width, image.height, image.dxgi_format), (3, 2, fmt))
            self.assertEqual(actual, pixels)

    def test_existing_typed_format_set_and_tight_block_layout(self):
        units = {28:4,29:4,49:2,61:1,71:8,72:8,74:16,75:16,77:16,78:16,
                 80:8,81:8,83:16,84:16,87:4,91:4,98:16,99:16}
        for fmt, unit in units.items():
            compressed = fmt not in (28, 29, 49, 61, 87, 91)
            pixels = bytes(4 * unit if compressed else 7 * 5 * unit)
            blob = dds(7, 5, fmt, pixels, compressed)
            if not compressed:
                blob = bytearray(blob); struct.pack_into("<I", blob, 20, 7 * unit); blob = bytes(blob)
            image, actual = a.read_dds(blob)
            self.assertEqual(image.dxgi_format, fmt)
            self.assertEqual(actual, pixels)

    def test_bad_headers_shapes_mips_pitch_format_and_payload_refuse(self):
        good = dds()
        for offset, value in ((4, 123), (8, 0), (12, 0), (16, 4097), (20, 13), (24, 2),
                              (28, 0), (28, 2), (32, 1), (76, 31), (80, 0), (84, 0),
                              (108, 0x1008), (112, 0x200), (128, 27), (132, 4),
                              (136, 4), (140, 2), (144, 2)):
            blob = bytearray(good); struct.pack_into("<I", blob, offset, value)
            with self.subTest(offset=offset, value=value), self.assertRaises(ValueError): a.read_dds(bytes(blob))
        for bad in (good[:-1], good + b"x", good[:128], bytearray(good), memoryview(good)):
            with self.assertRaises(ValueError): a.read_dds(bad)

    def test_names_slots_recipient_alias_and_template_closure_refuse(self):
        for field, values in (("zone", ("../bad", "a/b", "NUL")),
                              ("image_name", ("a:stream", "a,b", ",retail", "iw7_original_normal")),
                              ("material_name", ("a\\b", "bad name", "../x")),
                              ("texture_slot", (True, -1, 2, "1"))):
            for value in values:
                with self.subTest(field=field,value=value), self.assertRaises(ValueError): prepared(**{field: value})
        for role in ("material", "statebits", "statebitsmap"):
            source = template(); del source[role]
            with self.assertRaises(ValueError): prepared(template=source)
        for role, value in (("statebits", bytes(151)), ("statebits", bytes([2]) * 152),
                            ("statebitsmap", b"[]"), ("stateinfo", b'{"stateFlags":true}')):
            source = template(); source[role] = value
            with self.assertRaises(ValueError): prepared(template=source)

    def test_constant_and_missing_state_sidecars_are_explicit(self):
        source = template(); material = json.loads(source["material"])
        material["constantTable"] = [{"name": "original"}]
        material.pop("stateFlags"); source["material"] = json.dumps(material).encode()
        with self.assertRaises(ValueError): prepared(template=source)
        source.update(cbi=bytes([255]) * 152, cbt=b"owned-buffer")
        result = prepared(template=source)
        self.assertEqual(result["files"]["techsets/constantbuffer/iw7_template_technique/material_a.cbt"], b"owned-buffer")
        del source["stateinfo"]
        with self.assertRaises(ValueError): prepared(template=source)

    def test_readback_reuses_native_byte_oracle_and_never_claims_material_or_renderer(self):
        pixels = bytes(range(24)); blob = dds(pixels=pixels)
        native = iw7_dump(3, 2, 28, pixels, "author_color", 14)
        actual = a.verify_image(blob, native, image_name="author_color", iw7_semantic=14)
        self.assertTrue(actual["serialized_pixel_bytes_verified"])
        self.assertFalse(actual["material_verified"]); self.assertFalse(actual["rendered_verified"])
        for dump, name, semantic in ((native[:-1], "author_color", 14),
                                      (native[:-1] + b"x", "author_color", 14),
                                      (native, "wrong", 14), (native, "author_color", 5)):
            with self.assertRaises(ValueError): a.verify_image(blob, dump, image_name=name, iw7_semantic=semantic)


if __name__ == "__main__":
    unittest.main()

"""Synthetic tests for t7_fx_read.py layout parsing (no game data, no process)."""
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_fx_read as fx  # noqa: E402


def header(looping, one_shot, emission, total, elements=0x1000):
    raw = bytearray(fx.HEADER_SIZE)
    struct.pack_into("<Q", raw, 0, 0xDEAD)
    struct.pack_into("<H", raw, 0x08, 0x802C)
    struct.pack_into("<hhh", raw, 0x0C, looping, one_shot, emission)
    struct.pack_into("<i", raw, 0x14, total)
    struct.pack_into("<ii", raw, 0x18, 0, 800)
    struct.pack_into("<Q", raw, 0x20, elements)
    struct.pack_into("<6f", raw, 0x28, 27.5, 45, 45, 17.5, 0, 0)
    return bytes(raw)


def element(etype, visual=0, dup=0, effect=0, light=0):
    raw = bytearray(fx.ELEM_SIZE)
    struct.pack_into("<I", raw, 0, 0x01000046)
    raw[0xC8] = etype
    for off, value in ((0xF0, visual), (0x130, dup), (0x198, effect), (0x1E8, light)):
        struct.pack_into("<Q", raw, off, value)
    return bytes(raw)


class LayoutTest(unittest.TestCase):
    def test_header(self):
        h = fx.parse_header(header(0, 21, 0, 24588))
        self.assertEqual((h["flags"], h["looping"], h["one_shot"], h["emission"]), (0x802C, 0, 21, 0))
        self.assertEqual((h["total_size"], h["msec_non_looping_life"], h["elements_ptr"]), (24588, 800, 0x1000))
        self.assertEqual(h["bounds"][:4], [27.5, 45.0, 45.0, 17.5])

    def test_element_references(self):
        assets = {0x10: ("material", "ei/gfx_ring_thin"), 0x20: ("material", "ei/gfx_ring_thin|dup"),
                  0x30: ("fx", "zombie/fx_raygun_trail_ring_emit_zmb"), 0x40: ("lightdescription", "omni")}
        e = fx.parse_element(element(2, 0x10, 0x20, 0x30, 0x40), assets)
        self.assertEqual((e["type"], e["type_name"], e["flags"]), (2, "sprite", 0x01000046))
        self.assertEqual(e["visual"]["name"], "ei/gfx_ring_thin")
        self.assertEqual(e["visual_dup"]["name"], "ei/gfx_ring_thin|dup")
        self.assertEqual(e["effect_198"]["kind"], "fx")
        self.assertEqual(e["light"]["kind"], "lightdescription")
        self.assertEqual(len(bytes.fromhex(e["raw"])), fx.ELEM_SIZE)

    def test_visual_array_pointer_and_type_names(self):
        e = fx.parse_element(element(13, 0x5000), {})
        self.assertEqual(e["visual_array_ptr"], 0x5000)
        self.assertEqual(fx.parse_element(element(8), {})["type_name"], "omni_light")
        self.assertEqual(fx.parse_element(element(14), {})["type_name"], "runner")

    def test_wrong_sizes_are_refused(self):
        with self.assertRaises(ValueError):
            fx.parse_header(b"\0" * 8)
        with self.assertRaises(ValueError):
            fx.parse_element(b"\0" * 8, {})


if __name__ == "__main__":
    unittest.main()

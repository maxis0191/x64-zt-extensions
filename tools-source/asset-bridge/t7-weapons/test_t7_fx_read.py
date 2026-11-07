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

    def test_visual_array_is_resolved(self):
        class Memory:
            def readable(self, addr, size=1):
                return addr == 0x5000

            def read(self, addr, size):
                return struct.pack("<3Q", 0x10, 0x11, 0x12)[:size]
        raw = bytearray(element(0, 0x5000))
        raw[0xC9] = 3
        assets = {0x10: ("material", "smoke_a"), 0x11: ("material", "smoke_b"), 0x12: ("material", "smoke_c")}
        e = fx.parse_element(bytes(raw), assets)
        fx.read_visuals(Memory(), e, assets)
        self.assertEqual([v["name"] for v in e["visuals"]], ["smoke_a", "smoke_b", "smoke_c"])
        self.assertEqual(e["visual"]["name"], "smoke_a")

    def test_wrong_sizes_are_refused(self):
        with self.assertRaises(ValueError):
            fx.parse_header(b"\0" * 8)
        with self.assertRaises(ValueError):
            fx.parse_element(b"\0" * 8, {})


class SampleTest(unittest.TestCase):
    def test_visual_state_sample(self):
        base = bytes([64, 255, 0, 115]) + struct.pack("<9f", 0.0, 0.0, 0.83, 0.83, 0.0, 1.0, 0.0, 0.0, 1.0)
        amp = bytes([0, 0, 0, 0]) + struct.pack("<9f", 0.0, 0.0, 0.1, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0)
        s = fx.parse_vis_sample(base + amp)
        self.assertEqual(s["base"]["color"], [64, 255, 0, 115])
        self.assertAlmostEqual(s["base"]["size"][0], 0.83, places=5)
        self.assertAlmostEqual(s["amplitude"]["size"][1], 0.1, places=5)
        self.assertEqual(len(base + amp), fx.VIS_SAMPLE_SIZE)

    def test_velocity_sample(self):
        values = [0.1, 0, 0, 0, 0, 0] + [0] * 6 + [0, 0, 1, 0, 0, 0.5] + [0] * 6
        s = fx.parse_vel_sample(struct.pack("<24f", *values))
        self.assertAlmostEqual(s["local_velocity"]["base"][0], 0.1, places=6)
        self.assertEqual(s["world_velocity"]["base"], [0.0, 0.0, 1.0])
        self.assertEqual(s["world_velocity"]["amplitude"][2], 0.5)

    def test_scalars_and_counts(self):
        raw = bytearray(element(2))
        struct.pack_into("<ii", raw, 2 * 4, 50, 3)
        struct.pack_into("<ii", raw, 15 * 4, 150, 0)
        struct.pack_into("<6f", raw, 17 * 4, -2, 2, 0, 0, 0, 0)
        raw[0xC9], raw[0xCA], raw[0xCD] = 1, 4, 5
        e = fx.parse_element(bytes(raw), {})
        self.assertEqual(e["counts"], {"visual": 1, "vel_intervals": 4, "vis_intervals": 5})
        self.assertEqual(e["scalars"]["spawn"], {"a": 50, "b": 3})
        self.assertEqual(e["scalars"]["lifespan_msec"], {"base": 150, "amplitude": 0})
        self.assertEqual(e["scalars"]["spawn_origin"][0], {"base": -2.0, "amplitude": 2.0})

    def test_spawn_range_cull_radius_delay(self):
        # Distance LOD tiers: the Ray Gun impact repeats its sprites for 0-600, 600-1400 and 2000-2500.
        raw = bytearray(element(2))
        struct.pack_into("<2f", raw, 6 * 4, 600.1, 1399.9)
        struct.pack_into("<f2i", raw, 12 * 4, 332.5, 100, 20)
        e = fx.parse_element(bytes(raw), {})["scalars"]
        self.assertAlmostEqual(e["spawn_range"]["min"], 600.1, places=3)
        self.assertAlmostEqual(e["spawn_range"]["max"], 1399.9, places=3)
        self.assertEqual(e["cull_radius"], 332.5)
        self.assertEqual(e["spawn_delay_msec"], {"base": 100, "amplitude": 20})


if __name__ == "__main__":
    unittest.main()

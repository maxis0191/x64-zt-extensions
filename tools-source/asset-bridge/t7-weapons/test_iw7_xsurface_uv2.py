"""Synthetic tests for iw7_xsurface_uv2.py (no game data)."""
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iw7_xsurface_uv2 as uv2  # noqa: E402


def half(x):
    return struct.unpack("<H", struct.pack("<e", x))[0]


def surface_file(flags=0x84, uvs=((0.25, 0.5), (0.75, 0.125))):
    """A one-surface ZoneTool .xsb: header records, vertices, one triangle, empty lists."""
    surfs = bytearray(uv2.XMODEL_SURFS_SIZE)
    struct.pack_into("<H", surfs, 16, 1)
    head = bytearray(uv2.XSURFACE_SIZE)
    struct.pack_into("<3HB", head, 0, flags, len(uvs), 1, 0)
    verts = bytearray()
    for u, v in uvs:
        vert = bytearray(uv2.VERTEX_SIZE)
        struct.pack_into("<2H", vert, uv2.TEXCOORD, half(u), half(v))
        verts += vert
    data = bytes([8, 1]) + struct.pack("<I", 1) + bytes(surfs)
    data += bytes([6, 1]) + b"wpn_test_view\0"
    data += bytes([8, 1]) + struct.pack("<I", 1) + bytes(head)
    data += bytes([8, 1]) + struct.pack("<I", len(uvs)) + bytes(verts)
    data += bytes([8, 1]) + struct.pack("<I", 1) + struct.pack("<3H", 0, 1, 0)
    data += bytes([8, 0])                                   # rigid vertex lists
    data += bytes([10, 0]) * 4                              # blend verts, lmap, tension data, accum table
    return data


class SecondUvTest(unittest.TestCase):
    def test_camo_records_follow_the_stock_layout(self):
        out, report = uv2.add_second_uv(surface_file())
        self.assertEqual(report["second_uv_added"], 1)
        name, surfaces = uv2.parse(out)
        self.assertEqual(name, "wpn_test_view")
        s = surfaces[0]
        self.assertEqual(s["flags"], 0x484)                  # stock camo-ready Dischord surfaces: 0x482
        records = [struct.unpack_from("<6f", s["second"], k * 24) for k in range(2)]
        self.assertEqual(records, [(0.25, 0.5, 1.0, 0.0, 0.0, 1.0), (0.75, 0.125, 1.0, 0.0, 0.0, 1.0)])

    def test_surfaces_that_have_records_are_kept(self):
        once, _ = uv2.add_second_uv(surface_file())
        twice, report = uv2.add_second_uv(once)
        self.assertEqual(report["second_uv_added"], 0)
        self.assertEqual(once, twice)

    def test_truncated_file_refused(self):
        with self.assertRaises(Exception):
            uv2.parse(surface_file()[:-3])


if __name__ == "__main__":
    unittest.main()

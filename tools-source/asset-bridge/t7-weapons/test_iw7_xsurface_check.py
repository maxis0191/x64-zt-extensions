"""Synthetic tests for iw7_xsurface_check.py (no game data)."""
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iw7_xsurface_check as check  # noqa: E402


def pack(nx, ny, nz, high=True):
    value = 0
    for shift, c in zip((0, 10, 20), (nx, ny, nz)):
        value |= int(round((c + 1.0) / 2.0 * 1023)) << shift
    return value | (check.HIGH_BITS if high else 0)


def xsb(high=True, name='model'):
    """One surface: a triangle whose IW-winding normal is +z."""
    verts = [(0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0)]
    data = bytearray()
    data += bytes([8, 1]) + struct.pack('<I', 1)
    head = bytearray(check.XMODEL_SURFS_SIZE)
    struct.pack_into('<H', head, 16, 1)
    data += head
    data += bytes([6, 1]) + name.encode() + b'\0'
    data += bytes([8, 1]) + struct.pack('<I', 1)
    surface = bytearray(check.XSURFACE_SIZE)
    struct.pack_into('<3H', surface, 0, 0, len(verts), 1)
    data += surface
    data += bytes([8, 1]) + struct.pack('<I', len(verts))
    for x, y, z in verts:
        data += struct.pack('<3f12xI4x', x, y, z, pack(0.0, 0.0, 1.0, high))
    data += bytes([8, 1]) + struct.pack('<I', 1) + struct.pack('<3H', 0, 1, 2)
    return bytes(data)


class SurfaceCheckTest(unittest.TestCase):
    def report(self, data):
        name, surfaces = check.parse(data)
        flags, vertices, triangles = surfaces[0]
        return name, check.check_vertices(vertices, triangles)

    def test_iw7_normals_pass(self):
        name, measures = self.report(xsb())
        self.assertEqual(name, 'model')
        self.assertEqual(check.errors_for(measures), [])
        self.assertEqual(measures['triangle_agreement'], 1.0)

    def test_bo3_normals_fail(self):
        _, measures = self.report(xsb(high=False))
        self.assertIn('lack the IW7 high bits', check.errors_for(measures)[0])

    def test_decode(self):
        self.assertAlmostEqual(check.decode(pack(0.0, 0.0, 1.0))[2], 1.0, places=2)


if __name__ == '__main__':
    unittest.main()

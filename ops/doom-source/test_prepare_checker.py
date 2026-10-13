import copy
import math
import struct
import unittest
from prepare_checker import tga, ribbon, reference_skin


class CheckerTests(unittest.TestCase):
    def test_tga_layout_and_asymmetric_axes(self):
        data = tga(32)
        self.assertEqual(len(data), 18 + 32 * 32 * 4)
        self.assertEqual(data[2], 2)
        self.assertEqual(struct.unpack_from('<HHBB', data, 12), (32, 32, 32, 0x28))
        def rgba(x, y):
            b, g, r, a = data[18 + 4 * (y * 32 + x):22 + 4 * (y * 32 + x)]
            return r, g, b, a
        self.assertEqual(rgba(0, 0), (255, 40, 40, 255))
        self.assertEqual(rgba(31, 0), (40, 255, 40, 255))
        self.assertEqual(rgba(0, 31), (40, 40, 255, 255))
        self.assertEqual(rgba(31, 31), (255, 220, 40, 255))

    def test_original_skin_oracle_preserves_bind_and_moves_only_weighted_regions(self):
        source = ribbon()
        bind = reference_skin(source, 0)
        bend = reference_skin(source, 45)
        for actual, vertex in zip(bind, source['vertices']):
            for a, b in zip(actual, vertex['position_m']):
                self.assertAlmostEqual(a, b)
        self.assertEqual(bend[:2], bind[:2])
        self.assertAlmostEqual(bend[2][1], -0.3 / math.sqrt(2))
        self.assertAlmostEqual(bend[2][2], 0.2 + 0.1 / math.sqrt(2))
        self.assertAlmostEqual(bend[4][1], -0.05 - 0.1 / (2 * math.sqrt(2)))
        self.assertAlmostEqual(bend[4][2], 0.2 - 0.1 / (2 * math.sqrt(2)))

    def test_original_topology_and_weight_sums(self):
        source = ribbon()
        self.assertEqual(len(source['bones']), 2)
        self.assertEqual(len(source['vertices']), 6)
        self.assertEqual(len(source['triangle_indices']), 12)
        self.assertEqual(source['bones'][1]['parent'], 0)
        for vertex in source['vertices']:
            self.assertEqual(sum(row['weight'] for row in vertex['weights']), 1)
        for i in range(0, 12, 3):
            a, b, c = [source['vertices'][index]['position_m'] for index in source['triangle_indices'][i:i + 3]]
            normal_x = (b[1] - a[1]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[1] - a[1])
            self.assertLess(normal_x, 0)


if __name__ == '__main__':
    unittest.main()

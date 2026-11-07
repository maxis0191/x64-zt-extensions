"""Synthetic tests for t7_viewmodel_preview.py (no game data)."""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_viewmodel_preview as pv  # noqa: E402


class RasterTest(unittest.TestCase):
    def test_triangle_ahead_lands_on_screen_centre(self):
        # camera at the origin looking down +x; a triangle 10 units ahead around the axis
        pts = np.array([[10.0, 1.0, -1.0], [10.0, -1.0, -1.0], [10.0, 0.0, 1.0]])
        image = np.zeros((90, 160, 3))
        zbuf = np.full((90, 160), np.inf)
        pv.raster(image, zbuf, pts, np.array([[0, 1, 2]]), (1.0, 0.0, 0.0), np.eye(3), np.zeros(3), 80.0, (160, 90))
        self.assertGreater(image[45, 80, 0], 0)
        self.assertAlmostEqual(zbuf[45, 80], 10.0, places=3)
        self.assertEqual(image[5, 5].sum(), 0)

    def test_geometry_behind_the_near_plane_is_not_drawn(self):
        pts = np.array([[0.5, 1.0, -1.0], [10.0, -1.0, -1.0], [10.0, 0.0, 1.0]])
        image = np.zeros((90, 160, 3))
        pv.raster(image, np.full((90, 160), np.inf), pts, np.array([[0, 1, 2]]), (1, 0, 0), np.eye(3), np.zeros(3),
                  80.0, (160, 90))
        self.assertEqual(image.sum(), 0)

    def test_quaternion_matrix_matches_the_retarget_rotation(self):
        q = pv.rig.qnorm((0.1, 0.2, 0.3, 0.9))
        v = (1.0, 2.0, 3.0)
        np.testing.assert_allclose(pv.quat_matrix(q) @ np.array(v), pv.rig.qrot(q, v), atol=1e-9)


if __name__ == "__main__":
    unittest.main()

"""Synthetic tests for iw7_xanim_layout.py (no game data)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iw7_xanim_layout as layout  # noqa: E402

FRAMES = 300


def keys(count):
    """count rising key frame indices ending at FRAMES."""
    return [round(i * FRAMES / (count - 1)) for i in range(count)]


def bones(full):
    counts = [0] * 10
    counts[2] = full
    return counts


class LayoutTest(unittest.TestCase):
    def test_table_size(self):
        self.assertEqual(layout.table_size(126), 2)
        self.assertEqual(layout.table_size(256), 2)
        self.assertEqual(layout.table_size(257), 3)
        self.assertEqual(layout.table_size(765), 4)

    def test_short_animation_is_not_checked(self):
        self.assertFalse(layout.check(100, bones(1), [3], [])['long'])

    def test_iw7_layout_passes(self):
        small, big = keys(7), keys(274)
        table = [big[0], big[256], big[-1]]
        short = [6] + small + [273] + table
        result = layout.check(FRAMES, bones(2), short, big)
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['large_channels'], 1)
        self.assertEqual(result['rotation_indices'], 274)

    def test_bo3_inline_large_channel_fails(self):
        big = keys(274)
        result = layout.check(FRAMES, bones(1), [273] + big, [])
        self.assertTrue(result['errors'])
        self.assertIn('only 0 entries left', result['errors'][0])

    def test_wrong_table_fails(self):
        big = keys(100)
        result = layout.check(FRAMES, bones(1), [99, big[0], big[-2]], big)
        self.assertIn('lookup table', result['errors'][0])


if __name__ == '__main__':
    unittest.main()

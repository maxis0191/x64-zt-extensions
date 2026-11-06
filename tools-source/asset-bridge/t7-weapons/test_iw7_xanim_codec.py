"""Synthetic tests for iw7_xanim_codec.py and t7_vm_retarget.py (no game data)."""
import math
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iw7_xanim_codec as codec  # noqa: E402
import t7_vm_retarget as retarget  # noqa: E402


def header():
    head = bytearray(codec.HEADER_SIZE)
    struct.pack_into('<Q', head, 8, 1)          # names present
    struct.pack_into('<f', head, 100, 30.0)     # framerate
    struct.pack_into('<f', head, 104, 1.0)      # frequency
    return bytes(head)


def animation(frames):
    anim = codec.Animation()
    anim.name = 'synthetic'
    anim.frames = frames
    anim.header = header()
    anim.notify = [('fire', 0.5)]
    anim.notify_count = 1
    turn = [(f, (0.0, 0.0, math.sin(f / frames), math.cos(f / frames))) for f in range(frames + 1)]
    anim.rotations = {'j_gun': turn, 'tag_static': [(0, (0.0, 0.0, 0.0, 1.0))], 'tag_none': None}
    anim.translations = {'j_gun': [(f, (f * 0.5, 1.0, -2.0)) for f in range(frames + 1)],
                         'tag_static': [(0, (1.0, 2.0, 3.0))], 'tag_none': None}
    return anim


class CodecTest(unittest.TestCase):
    def roundtrip(self, frames):
        path = os.path.join(tempfile.mkdtemp(), 'a.xab')
        codec.encode(animation(frames), path)
        return codec.decode(path)

    def check(self, frames):
        back = self.roundtrip(frames)
        source = animation(frames)
        self.assertEqual(back.frames, frames)
        self.assertEqual(back.notify[0][0], 'fire')
        for f in (0, frames // 2, frames):
            q0 = codec.sample(source.rotations['j_gun'], f, True)
            q1 = codec.sample(back.rotations['j_gun'], f, True)
            self.assertGreater(abs(sum(a * b for a, b in zip(q0, q1))), 0.99999)
            t1 = codec.sample(back.translations['j_gun'], f, False)
            self.assertAlmostEqual(t1[0], f * 0.5, places=2)
        self.assertEqual(back.translations['tag_static'][0][1], (1.0, 2.0, 3.0))
        self.assertIsNone(back.rotations['tag_none'])

    def test_short_animation(self):
        self.check(40)

    def test_long_animation_uses_index_list(self):
        self.check(300)


class RetargetMathTest(unittest.TestCase):
    def test_two_bone_reaches_target(self):
        shoulder, target, pole = (0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (5.0, 0.0, -5.0)
        elbow = retarget.two_bone(shoulder, 6.0, 6.0, target, pole)
        self.assertAlmostEqual(retarget.vlen(retarget.vsub(elbow, shoulder)), 6.0, places=4)
        self.assertAlmostEqual(retarget.vlen(retarget.vsub(target, elbow)), 6.0, places=4)
        self.assertLess(elbow[2], 0.0)   # bends toward the pole

    def test_q_between(self):
        q = retarget.q_between((1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
        v = retarget.qrot(q, (1.0, 0.0, 0.0))
        for a, b in zip(v, (0.0, 1.0, 0.0)):
            self.assertAlmostEqual(a, b, places=6)


if __name__ == '__main__':
    unittest.main()

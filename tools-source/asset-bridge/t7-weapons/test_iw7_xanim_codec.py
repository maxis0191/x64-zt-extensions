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

    def test_long_channels_inline_without_index_list(self):
        # ZoneTool's T7 conversions (the 300-frame Ray Gun idle) keep every channel's indices in
        # dataShort and write no index list; the encoder makes that layout when no channel is "large".
        path = os.path.join(tempfile.mkdtemp(), 'a.xab')
        large = codec.LARGE
        codec.LARGE = 10 ** 9
        try:
            codec.encode(animation(300), path)
        finally:
            codec.LARGE = large
        back = codec.decode(path)
        for f in (0, 150, 300):
            q0 = codec.sample(animation(300).rotations['j_gun'], f, True)
            self.assertGreater(abs(sum(a * b for a, b in zip(q0, codec.sample(back.rotations['j_gun'], f, True)))), 0.99999)
            self.assertAlmostEqual(codec.sample(back.translations['j_gun'], f, False)[0], f * 0.5, places=2)


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


def view_rig():
    """IW7-like view hands: tag_view at the eye, tag_ads the hands root under
    it, tag_camera beside it, the gun on tag_weapon under tag_torso."""
    rig = object.__new__(retarget.Skeleton)
    rig.names = ['tag_origin', 'tag_view', 'tag_ads', 'tag_torso', 'tag_cambone', 'tag_camera', 'tag_weapon']
    rig.parent = [None, 0, 1, 2, 1, 4, 3]
    ident = (0.0, 0.0, 0.0, 1.0)
    rig.local = [(ident, (0.0, 0.0, 0.0)), (ident, (0.0, 0.0, 64.0)), (ident, (0.0, 0.0, 0.0)),
                 (ident, (-1.0, 0.0, -12.0)), (ident, (0.0, 0.0, 0.0)), (ident, (0.0, 0.0, 0.0)),
                 (ident, (14.0, 0.0, 0.0))]
    rig.index = {n: i for i, n in enumerate(rig.names)}
    rig.world = rig.pose({}, {}, 0)
    return rig


class RootAdsTest(unittest.TestCase):
    def test_ads_moves_only_tag_ads_onto_the_camera_axis(self):
        rig = view_rig()
        hip = codec.Animation()
        yaw = math.radians(12.0)
        hip.rotations = {'tag_weapon': [(0, (0.0, 0.0, math.sin(yaw / 2), math.cos(yaw / 2)))]}
        hip.translations = {'tag_weapon': [(0, (13.0, -4.0, 6.0))]}
        source = codec.Animation()
        source.name, source.frames, source.header = 'vm_ads_up', 8, header()
        source.rate, source.frequency, source.flags, source.tail = 30.0, 3.75, 0, b''
        source.notify, source.notify_count = [('end', 1.0)], 1
        gun = (8.0, 0.0, -5.75)
        up, info = retarget.root_ads(source, hip, rig, gun, 'up')
        down, _ = retarget.root_ads(source, hip, rig, gun, 'down')
        self.assertEqual(set(up.rotations), {'tag_ads'})
        self.assertEqual(set(up.translations), {'tag_ads'})
        self.assertEqual(up.header[130], 1)
        rot, tr = dict(hip.rotations), dict(hip.translations)
        rot['tag_ads'] = [(0, codec.sample(up.rotations['tag_ads'], 8, True))]
        tr['tag_ads'] = [(0, codec.sample(up.translations['tag_ads'], 8, False))]
        pose = rig.pose(rot, tr, 0)
        gq, gt = pose[rig.index['tag_weapon']]
        cq, ct = rig.world[rig.index['tag_camera']]
        local = retarget.qrot(retarget.qinv(cq), retarget.vsub(gt, ct))
        for a, b in zip(local, gun):
            self.assertAlmostEqual(a, b, places=4)
        self.assertGreater(abs(retarget.qmul(retarget.qinv(cq), gq)[3]), 0.99999)
        # Lowering ends on the identity: the hip pose is left untouched.
        self.assertGreater(abs(codec.sample(down.rotations['tag_ads'], 8, True)[3]), 0.99999)
        self.assertAlmostEqual(retarget.vlen(codec.sample(down.translations['tag_ads'], 8, False)), 0.0, places=5)
        self.assertEqual(codec.sample(up.translations['tag_ads'], 0, False), (0.0, 0.0, 0.0))

    def test_listed_no_rotation_channel_is_identity_not_bind(self):
        rig = view_rig()
        half = math.radians(40.0) / 2
        rig.local[6] = ((0.0, math.sin(half), 0.0, math.cos(half)), (14.0, 0.0, 0.0))
        self.assertLess(abs(rig.pose({}, {}, 0)[6][0][3]), 0.99)              # absent: bind rotation
        self.assertGreater(abs(rig.pose({'tag_weapon': None}, {}, 0)[6][0][3]), 0.99999)  # listed None: identity

    def test_engine_roots_are_not_hand_channels(self):
        self.assertEqual(retarget.ENGINE_ROOTS, ('tag_view', 'tag_ads'))


def arm_rig(names, parents, offsets):
    rig = object.__new__(retarget.Skeleton)
    rig.names, rig.parent = names, parents
    rig.local = [((0.0, 0.0, 0.0, 1.0), t) for t in offsets]
    rig.index = {n: i for i, n in enumerate(names)}
    rig.world = rig.pose({}, {}, 0)
    return rig


class ShoulderTest(unittest.TestCase):
    def test_shoulders_follow_the_bo3_animation(self):
        # The BO3 DG-2 brings the left shoulder forward; at the IW7 bind shoulder the hand fell
        # 7.3 units short of the gun.
        src = arm_rig(['tag_origin', 'tag_camera', 'tag_torso', 'j_shoulder_le', 'j_elbow_le', 'j_wrist_le',
                       'tag_weapon_right'], [None, 0, 0, 2, 3, 4, 2],
                      [(0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 8, -6), (10, 0, 0), (10, 0, 0), (12, -4, -5)])
        dst = arm_rig(['tag_origin', 'tag_camera', 'tag_torso', 'j_clavicle_le', 'j_shoulder_le', 'j_elbow_le',
                       'j_wrist_le', 'tag_weapon'], [None, 0, 0, 2, 3, 4, 5, 2],
                      [(0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 4, -6), (0, 4, 0), (11, 0, 0), (11, 0, 0), (0, 0, 0)])
        anim = codec.Animation()
        anim.frames, anim.notify = 1, []
        anim.translations = {'j_shoulder_le': [(0, (12.0, 8.0, -6.0))]}
        out, report = retarget.retarget(anim, src, dst, fov=1.0)   # shoulder out of view: kept
        self.assertEqual(report['wrist_error_max'], 0.0)
        pose = dst.pose(out.rotations, out.translations, 0)
        for got, want in zip(pose[dst.index['j_shoulder_le']][1], (12.0, 8.0, -6.0)):
            self.assertAlmostEqual(got, want, places=4)
        for got, want in zip(pose[dst.index['j_wrist_le']][1], (32.0, 8.0, -6.0)):
            self.assertAlmostEqual(got, want, places=3)
        # The clavicle carries the shoulder: their spacing (and the sleeve skin between them) stays bind.
        self.assertEqual(out.translations['j_shoulder_le'], [(0, (0, 4, 0))])
        for got, want in zip(pose[dst.index['j_clavicle_le']][1], (12.0, 4.0, -6.0)):
            self.assertAlmostEqual(got, want, places=4)


class HideShoulderTest(unittest.TestCase):
    CAM = ((0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0))

    def test_shoulder_in_view_is_lowered_within_reach(self):
        # BO3 Thundergun left arm: shoulder 16 forward, 14 down, wrist 35 forward.
        s = retarget.hide_shoulder((15.9, 0.9, -14.3), (34.8, -5.0, -14.5), 22.57, self.CAM)
        self.assertEqual(s[:2], (15.9, 0.9))
        self.assertLess(s[2], -14.3)
        self.assertLessEqual(retarget.vlen(retarget.vsub((34.8, -5.0, -14.5), s)), 0.98 * 22.57 + 1e-6)

    def test_shoulder_out_of_view_is_kept(self):
        self.assertEqual(retarget.hide_shoulder((-5.5, 11.5, -9.5), (8.2, 7.6, -18.6), 22.57, self.CAM),
                         (-5.5, 11.5, -9.5))
        self.assertEqual(retarget.hide_shoulder((8.0, 0.0, -40.0), (20.0, 0.0, -30.0), 22.57, self.CAM),
                         (8.0, 0.0, -40.0))


if __name__ == '__main__':
    unittest.main()

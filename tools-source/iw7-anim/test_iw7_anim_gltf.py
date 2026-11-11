"""Tests of iw7_anim_gltf.py on synthetic skeletons and clips (no game file)."""
import contextlib
import io
import json
import math
import os
import struct
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import iw7_anim_gltf as T  # noqa: E402
import author_clip  # noqa: E402

BONES = [  # name, parent, local rotation (x, y, z, w), local translation (inches)
    ('tag_origin', None, (0, 0, 0, 1), (0, 0, 0)),
    ('j_mainroot', 'tag_origin', (0.5, -0.5, 0.5, 0.5), (-1, 0, 38)),
    ('j_spine4', 'j_mainroot', (0, 0, 0.1, 0.995), (14, 0, 0)),
    ('j_head', 'j_spine4', (0, 0.1, 0, 0.995), (12, 0, 0)),
    ('j_shoulder_ri', 'j_spine4', (0.1, -0.4, -0.1, 0.9), (5, 0, -8)),
    ('j_elbow_ri', 'j_shoulder_ri', (0, 0, -0.4, 0.92), (11, 0, 0)),
    ('j_wrist_ri', 'j_elbow_ri', (0, 0, 0, 1), (10, 0, 0)),
    ('j_knee_le', 'j_mainroot', (0, 0, 0.5, 0.87), (-18, 0, 4)),
    ('j_knee_ri', 'j_mainroot', (0, 0, 0.5, 0.87), (-18, 0, -4)),
]


def skeleton():
    return T.Skeleton('synthetic', [b[0] for b in BONES],
                      [-1 if b[1] is None else [x[0] for x in BONES].index(b[1]) for b in BONES],
                      [b[2] for b in BONES], [b[3] for b in BONES])


def clip(skel, frames=40, move=(60, 5, 0), loop=True):
    c = author_clip.build(skel, 'synthetic_clip', frames / 30.0, 30.0,
                          [('j_spine4', (40, 0, 0)), ('j_shoulder_ri', (0, 100, 20)), ('j_head', (0, 0, -30)),
                           ('j_knee_le', (0, 0, 25)), ('j_knee_ri', (0, 0, -25))],
                          move, [('hit', frames / 60.0)], loop)
    c.bones.append('j_mainroot')
    i = skel.index['j_mainroot']
    c.rot['j_mainroot'] = [skel.q[i]] * (frames + 1)
    c.trans['j_mainroot'] = [(0.0, math.sin(f / 5.0), 0.2 * f) for f in range(frames + 1)]     # offsets from the bind translation
    c.bones.append('tag_origin')
    c.rot['tag_origin'] = [T.IDENT] * (frames + 1)
    c.trans['tag_origin'] = None
    return c


def save(path, doc):
    with open(path, 'w') as f:
        json.dump(doc, f)


def load(path):
    with open(path) as f:
        return json.load(f)


SKELETON_DOC = {'name': 'synthetic', 'bones': [{'name': b[0], 'parent': b[1], 'q': b[2], 't': b[3]} for b in BONES]}


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = T.main([str(a) for a in argv])
    return code, json.loads(out.getvalue())


class MathAndSkeleton(unittest.TestCase):
    def test_axis_change_is_a_rotation_and_inverts(self):
        v, q = (1.5, -2.0, 3.0), T.q_norm((0.2, -0.3, 0.4, 0.8))
        self.assertEqual(T.to_game_v(T.to_gltf_v(v)), v)
        self.assertEqual(T.to_game_q(T.to_gltf_q(q)), q)
        rotated = T.to_gltf_v(T.q_rot(q, v))
        direct = T.q_rot(T.to_gltf_q(q), T.to_gltf_v(v))
        self.assertLess(T.v_len(T.v_sub(rotated, direct)), 1e-12)

    def test_skeleton_from_json_and_model_dump_agree(self):
        import xmodel as xm
        import ztdump
        skel = skeleton()
        m = xm.XModel()
        m.name = 'synthetic'
        m.set('numBones', len(BONES))
        m.set('numRootBones', 1)
        m.bone_names = list(skel.names)
        m.parents = [i - skel.parents[i] for i in range(1, len(BONES))]
        m.tag_angles = [tuple(int(round(c * 32767)) for c in skel.q[i]) for i in range(1, len(BONES))]
        m.tag_positions = [skel.t[i] for i in range(1, len(BONES))]
        m.part_class = bytes(len(BONES))
        gq, gt = skel.globals()
        m.base_mat = [(*gq[i], *gt[i], 1.0) for i in range(len(BONES))]
        m.rm_parts = m.rm_tweaks = m.coll_surfs = m.unknown03 = m.unknown_vec3 = m.unknown04 = ztdump.Rec(ztdump.T_ARRAY)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'synthetic.xmb')
            with open(path, 'wb') as f:
                f.write(xm.write(m))
            loaded = T.Skeleton.load(path)
            js = os.path.join(d, 'skeleton.json')
            save(js, SKELETON_DOC)
            from_json = T.Skeleton.load(js)
        self.assertEqual(loaded.names, skel.names)
        self.assertEqual(loaded.parents, skel.parents)
        self.assertEqual(from_json.parents, skel.parents)
        for a, b in zip(loaded.q, skel.q):
            self.assertLess(T.q_angle(a, b), 0.01)
        for a, b in zip(loaded.t, skel.t):
            self.assertLess(T.v_len(T.v_sub(a, b)), 1e-5)

    def test_parent_must_come_first(self):
        with self.assertRaises(T.Problem):
            T.Skeleton('x', ['a', 'b'], [1, -1], [T.IDENT] * 2, [(0, 0, 0)] * 2)


class RoundTrip(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.d = self.dir.name
        self.skel = skeleton()
        self.sk = os.path.join(self.d, 'skeleton.json')
        save(self.sk, SKELETON_DOC)

    def tearDown(self):
        self.dir.cleanup()

    def test_game_to_gltf_to_game_keeps_tracks_root_motion_notes_and_loop(self):
        for frames in (0, 1, 40, 300):
            src = clip(self.skel, frames) if frames else clip(self.skel, 1)
            if not frames:
                src.frames = 0
                for n in src.bones:
                    src.rot[n] = src.rot[n][:1]
                    src.trans[n] = src.trans[n][:1] if src.trans[n] else None
                src.delta_t = None
                src.notes = []
            a = src.write_xanim(os.path.join(self.d, 'a%d' % frames))
            code, to = run('to-gltf', a, '--model', self.sk, '--out', os.path.join(self.d, 'c%d.glb' % frames))
            self.assertEqual(code, 0, to)
            code, back = run('from-gltf', os.path.join(self.d, 'c%d.glb' % frames), '--skeleton', self.sk, '--out', os.path.join(self.d, 'b%d' % frames))
            self.assertEqual(code, 0, back)
            code, cmp = run('compare', a, back['written'], '--model', self.sk)
            self.assertEqual(code, 0, cmp)
            self.assertLess(cmp['rotation_deg']['worst'], 0.01)
            self.assertLess(cmp['translation_units']['worst'], 0.002)
            self.assertLess(cmp['model_space_units']['worst'], 0.01)
            self.assertTrue(cmp['notes_equal'] and cmp['loop_equal'])
            self.assertEqual(cmp['only_in_a'] + cmp['only_in_b'], [])
            if frames:
                self.assertLess(cmp['root_motion']['translation_units_worst'], 0.005)
                self.assertEqual(back['root_motion_end'][:2], [60.0, 5.0])

    def test_header_bytes_of_a_stock_animation_survive(self):
        src = clip(self.skel)
        a = src.write_xanim(os.path.join(self.d, 'a'), asset_type=7, flags=3, unk=(2, 1))
        run('to-gltf', a, '--model', self.sk, '--out', os.path.join(self.d, 'c.glb'))
        _, back = run('from-gltf', os.path.join(self.d, 'c.glb'), '--skeleton', self.sk, '--out', os.path.join(self.d, 'b'))
        _, info = run('inspect', back['written'])
        self.assertEqual((info['flags'], info['asset_type'], info['byte131'], info['byte132']), (3, 7, 2, 1))
        self.assertEqual(info['kind'], 'full body')
        self.assertTrue(info['has_delta'] and info['loop'])
        self.assertEqual(info['delta']['end_translation'][0], 60.0)

    def test_cut_splits_a_clip_into_in_hold_and_out(self):
        src = clip(self.skel, 40, move=None)
        src.notes = [('show', 10 / 40), ('fx_flash', 12 / 40), ('hide', 30 / 40), ('end', 1.0)]
        a = src.write_xanim(os.path.join(self.d, 'src'), asset_type=6, flags=0, unk=(2, 2))
        code, cin = run('cut', a, '--from', '0', '--to', '20', '--name', 'p_in', '--out', self.d, '--drop-note', 'fx_')
        self.assertEqual(code, 0, cin)
        self.assertEqual((cin['frames'], cin['asset_type'], cin['loop']), (20, 6, False))
        self.assertEqual([(n['name'], n['time']) for n in cin['notes']], [('show', 0.5), ('end', 1.0)])
        code, hold = run('cut', a, '--from', '20', '--to', '25', '--name', 'p_hold', '--out', self.d, '--pingpong', '--loop', '--no-notes')
        self.assertEqual(code, 0, hold)
        self.assertEqual((hold['frames'], hold['loop']), (10, True))
        back = T.Clip.from_xanim(hold['written'])
        for n in back.bones:
            self.assertLess(T.q_angle(back.rot[n][0], back.rot[n][-1]), 0.01)  # seamless loop
            self.assertLess(T.q_angle(back.rot[n][5], src.rot[n][25]), 0.01)
        code, out = run('cut', a, '--from', '25', '--to', '40', '--name', 'p_out', '--out', self.d)
        self.assertEqual(code, 0, out)
        self.assertEqual([n['name'] for n in out['notes']], ['hide', 'end'])
        self.assertAlmostEqual(out['notes'][0]['time'], 5 / 15, places=4)
        self.assertLess(out['rotation_deg_worst_vs_source'], 0.01)
        code, bad = run('cut', a, '--from', '30', '--to', '50', '--name', 'x', '--out', self.d)
        self.assertNotEqual(code, 0)
        moving = clip(self.skel, 40).write_xanim(os.path.join(self.d, 'mv'))
        code, bad = run('cut', moving, '--from', '0', '--to', '10', '--name', 'y', '--out', self.d)
        self.assertNotEqual(code, 0)

    def test_empty_delta_part_and_rotation_delta_round_trip(self):
        src = clip(self.skel, move=None)
        src.has_delta_part = True
        a = src.write_xanim(os.path.join(self.d, 'a'))
        self.assertTrue(T.Clip.from_xanim(a).has_delta_part)
        self.assertIsNone(T.Clip.from_xanim(a).delta_t)
        for three_d in (False, True):
            src = clip(self.skel)
            src.delta_q = [T.q_norm((0.2 * f / 40 if three_d else 0.0, 0.0, math.sin(f / 80.0), math.cos(f / 80.0))) for f in range(41)]
            src.three_d = three_d
            a = src.write_xanim(os.path.join(self.d, 'r%d' % three_d))
            back = T.Clip.from_xanim(a)
            self.assertEqual(back.three_d, three_d)
            self.assertLess(max(T.q_angle(x, y) for x, y in zip(src.delta_q, back.delta_q)), 0.01)
            run('to-gltf', a, '--model', self.sk, '--out', os.path.join(self.d, 'r.glb'))
            code, again = run('from-gltf', os.path.join(self.d, 'r.glb'), '--skeleton', self.sk, '--out', os.path.join(self.d, 'rb%d' % three_d))
            self.assertEqual(code, 0)
            self.assertEqual(again['root_motion_3d'], three_d)
            code, cmp = run('compare', a, again['written'], '--model', self.sk)
            self.assertEqual(code, 0, cmp)
            self.assertLess(cmp['root_motion']['rotation_deg_worst'], 0.01)

    def test_static_delta_translation(self):
        src = clip(self.skel, move=(0, 0, 0))
        src.delta_t = [(3.0, 0.0, 1.0)] * 41
        a = src.write_xanim(os.path.join(self.d, 'a'))
        self.assertEqual(T.Clip.from_xanim(a).delta_t[40], (3.0, 0.0, 1.0))

    def test_compare_reports_a_changed_bone(self):
        a = clip(self.skel)
        b = clip(self.skel)
        b.rot['j_head'] = [T.q_mul(q, author_clip.euler((0, 0, 2.0))) for q in b.rot['j_head']]
        pa, pb = a.write_xanim(os.path.join(self.d, 'a')), b.write_xanim(os.path.join(self.d, 'b'))
        code, cmp = run('compare', pa, pb, '--model', self.sk)
        self.assertEqual(code, 1)
        self.assertFalse(cmp['pass'])
        self.assertEqual(cmp['rotation_deg']['bone'], 'j_head')
        self.assertAlmostEqual(cmp['rotation_deg']['worst'], 2.0, delta=0.02)

    def test_compare_refuses_different_lengths_and_missing_files(self):
        pa = clip(self.skel, 40).write_xanim(os.path.join(self.d, 'a'))
        pb = clip(self.skel, 30).write_xanim(os.path.join(self.d, 'b'))
        code, cmp = run('compare', pa, pb)
        self.assertEqual(code, 1)
        self.assertIn('error', cmp)
        code, out = run('inspect', os.path.join(self.d, 'absent.xab'))
        self.assertEqual(code, 2)
        self.assertIn('error', out)

    def test_sample_gives_model_space_positions(self):
        src = clip(self.skel)
        a = src.write_xanim(os.path.join(self.d, 'a'))
        code, out = run('sample', a, '--model', self.sk, '--bones', 'j_head,j_wrist_ri,j_knee_le')
        self.assertEqual(code, 0)
        _, gt = self.skel.globals()
        first = out['samples'][0]
        self.assertLess(T.v_len(T.v_sub(first['j_wrist_ri'], gt[self.skel.index['j_wrist_ri']])), 1e-3)   # frame 0 is the bind pose: a zero offset moves nothing
        lifted = T.v_sub(out['samples'][40]['j_knee_le'], gt[self.skel.index['j_knee_le']])
        self.assertAlmostEqual(lifted[2], 8.0, delta=0.5)                                                   # the root offset of 0.2 a frame lifts the legs with it
        self.assertGreater(T.v_len(T.v_sub(out['samples'][40]['j_wrist_ri'], first['j_wrist_ri'])), 5)
        code, out = run('sample', a, '--model', self.sk, '--bones', 'nope')
        self.assertEqual(code, 2)

    def test_zone_source_lists_every_animation_and_the_name_table(self):
        clip(self.skel).write_xanim(os.path.join(self.d, 'dump'))
        c = clip(self.skel)
        c.name = 'second_clip'
        c.write_xanim(os.path.join(self.d, 'dump'))
        code, out = run('zone-source', os.path.join(self.d, 'dump'), '--zone', 'mod', '--out', os.path.join(self.d, 'tree'))
        self.assertEqual(code, 0)
        with open(out['csv']) as f:
            listed = f.read()
        self.assertEqual(listed, 'xanim,second_clip\nxanim,synthetic_clip\nnetconststrings,ncs_anm_mod\nrawfile,animtrees/mod_anims.atr\n')
        with open(os.path.join(out['tree'], 'animtrees', 'mod_anims.atr')) as f:
            self.assertEqual([l for l in f.read().splitlines() if not l.startswith('//')], ['second_clip', 'synthetic_clip'])
        table = load(os.path.join(out['tree'], 'netconststrings', 'ncs_anm_mod.json'))
        self.assertEqual(table, {'stringType': 16, 'sourceType': 2, 'stringList': ['second_clip', 'synthetic_clip']})
        self.assertTrue(os.path.isfile(os.path.join(out['tree'], 'xanim', 'second_clip.xab')))


class GameRun(unittest.TestCase):
    """Samples as the gamelab verdict writes them: entity origin, angles and tag origins every server frame."""

    def setUp(self):
        self.skel = skeleton()
        self.clip = clip(self.skel, 60, move=None, loop=False)
        self.tags = ['j_head', 'j_wrist_ri']

    def samples(self, offset=0.1, yaw=37.0, posed=True):
        origin = (100.0, 200.0, 30.0)
        fw, lf, up = T.angle_axes((0.0, yaw, 0.0))
        rows = []
        for k in range(50):
            t = max(0.0, min(2.0, k * 0.05 - offset)) if posed else 0.0
            pos = T.pose_between(self.clip, self.skel, t * 30)
            rows.append({'k': k, 'ms': k * 50, 'origin': list(origin), 'angles': [0.0, yaw, 0.0],
                         'tags': {n: [origin[i] + pos[self.skel.index[n]][0] * fw[i] + pos[self.skel.index[n]][1] * lf[i] + pos[self.skel.index[n]][2] * up[i]
                                      for i in range(3)] for n in self.tags}})
        return {'samples': rows}

    def test_axes_of_a_yawed_entity(self):
        fw, lf, up = T.angle_axes((0.0, 90.0, 0.0))
        for got, want in ((fw, (0, 1, 0)), (lf, (-1, 0, 0)), (up, (0, 0, 1))):
            self.assertLess(T.v_len(T.v_sub(got, want)), 1e-9)

    def test_a_posed_run_matches_and_the_start_offset_is_found(self):
        r = T.compare_run(self.samples(), self.clip, self.skel)
        self.assertEqual(r['verdict'], 'posed')
        self.assertAlmostEqual(r['start_offset_seconds'], 0.1, delta=0.002)
        self.assertLess(r['worst_units'], 0.05)
        self.assertGreater(r['measured_travel_units']['j_wrist_ri'], 5)

    def test_a_run_whose_tags_never_move_is_reported_as_not_posed(self):
        r = T.compare_run(self.samples(posed=False), self.clip, self.skel)
        self.assertTrue(r['verdict'].startswith('not posed'))
        self.assertNotIn('worst_units', r)

    def test_a_looping_clip_that_jumps_at_its_loop_point(self):
        # The pose at the end differs from the pose at the start: a sample taken on the loop point may show either.
        loop = clip(self.skel, 60, move=None, loop=True)
        origin = (0.0, 0.0, 0.0)
        rows = []
        for k in range(100):
            t = (k * 0.05 - 0.2) % 2.0
            if k * 0.05 - 0.2 > 0 and abs(t) < 1e-9:
                t = 2.0                                  # the game shows the last pose on the loop point
            pos = T.pose_between(loop, self.skel, max(0.0, t) * 30)
            rows.append({'k': k, 'ms': k * 50, 'origin': list(origin), 'angles': [0.0, 0.0, 0.0],
                         'tags': {n: list(pos[self.skel.index[n]]) for n in self.tags}})
        r = T.compare_run({'samples': rows[4:]}, loop, self.skel)
        self.assertEqual(r['verdict'], 'posed')
        self.assertAlmostEqual(r['start_offset_seconds'] % 2.0, 0.2, delta=0.002)
        self.assertLess(r['worst_units'], 0.05)

    def test_a_stretch_of_the_log_can_be_chosen(self):
        doc = self.samples()
        for row in doc['samples'][30:]:                       # after 1.5 s the entity does something else
            row['tags'] = {n: [c + 9.0 for c in v] for n, v in row['tags'].items()}
        whole = T.compare_run(doc, self.clip, self.skel)
        self.assertGreater(whole['worst_units'], 5)
        part = T.compare_run(doc, self.clip, self.skel, to_ms=1450)
        self.assertLess(part['worst_units'], 0.05)
        self.assertEqual((part['samples'], part['within_limit_until_ms']), (30, 1450))

    def test_a_wrong_clip_is_far_off(self):
        other = clip(self.skel, 60, move=None, loop=False)
        other.rot['j_shoulder_ri'] = [T.q_mul(q, author_clip.euler((0, 0, 40.0 * f / 60))) for f, q in enumerate(other.rot['j_shoulder_ri'])]
        r = T.compare_run(self.samples(), other, self.skel)
        self.assertGreater(r['worst_units'], 2.0)

    def test_command_line(self):
        with tempfile.TemporaryDirectory() as d:
            sk = os.path.join(d, 'skeleton.json')
            save(sk, SKELETON_DOC)
            xab = self.clip.write_xanim(d)
            save(os.path.join(d, 'anim-x.json'), self.samples())
            code, r = run('compare-run', os.path.join(d, 'anim-x.json'), xab, '--model', sk)
            self.assertEqual((code, r['pass']), (0, True))
            save(os.path.join(d, 'anim-y.json'), self.samples(posed=False))
            code, r = run('compare-run', os.path.join(d, 'anim-y.json'), xab, '--model', sk)
            self.assertEqual((code, r['pass']), (1, False))


class ForeignGltf(unittest.TestCase):
    """A file as another tool writes it: a wrapper node, centimetres, 24 keys a second, step and spline samplers, extra nodes."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.d = self.dir.name
        self.skel = skeleton()

    def tearDown(self):
        self.dir.cleanup()

    def write(self, interpolation='LINEAR', wrapper_scale=1.0, rate=24.0, extra=True):
        skel = self.skel
        w = T.GlbWriter()
        nodes = [{'name': 'Armature', 'children': [1], 'scale': [wrapper_scale] * 3}]
        for i, name in enumerate(skel.names):
            node = {'name': name.upper() if name == 'j_head' else name,
                    'translation': list(T.to_gltf_v(skel.t[i], T.INCH / wrapper_scale)), 'rotation': list(T.to_gltf_q(skel.q[i]))}
            kids = [j + 1 for j, p in enumerate(skel.parents) if p == i]
            if kids:
                node['children'] = kids
            nodes.append(node)
        if extra:
            nodes.append({'name': 'ik_target', 'translation': [0, 0, 0]})
            nodes[0]['children'].append(len(nodes) - 1)
        keys = [0.0, 0.5, 1.0]
        i = skel.index['j_spine4']
        quats = [T.to_gltf_q(T.q_mul(skel.q[i], author_clip.euler((a, 0, 0)))) for a in (0, 30, 60)]
        if interpolation == 'CUBICSPLINE':
            rows = []
            for q in quats:
                rows += [(0, 0, 0, 0), q, (0, 0, 0, 0)]
        else:
            rows = quats
        times = w.add('f', keys, 'SCALAR', minmax=True)
        samplers = [{'input': times, 'output': w.add('f', rows, 'VEC4'), 'interpolation': interpolation}]
        channels = [{'sampler': 0, 'target': {'node': i + 1, 'path': 'rotation'}}]
        if extra:
            samplers.append({'input': times, 'output': w.add('f', [(0, 0, 0), (1, 0, 0), (2, 0, 0)], 'VEC3'), 'interpolation': 'LINEAR'})
            channels.append({'sampler': 1, 'target': {'node': len(nodes) - 1, 'path': 'translation'}})
        path = os.path.join(self.d, 'foreign.glb')
        w.save(path, {'asset': {'version': '2.0'}, 'scene': 0, 'scenes': [{'nodes': [0]}], 'nodes': nodes,
                      'animations': [{'name': 'Take 001', 'samplers': samplers, 'channels': channels}]})
        return path

    def convert(self, path, *more):
        sk = os.path.join(self.d, 'skeleton.json')
        save(sk, SKELETON_DOC)
        return run('from-gltf', path, '--skeleton', sk, '--name', 'Foreign_Clip', '--out', os.path.join(self.d, 'out'), *more)

    def spine_angle(self, report, frame):
        c = T.Clip.from_xanim(report['written'])
        return T.q_angle(c.rot['j_spine4'][frame], self.skel.q[self.skel.index['j_spine4']])

    def test_resampled_to_30_and_names_matched_without_case(self):
        code, r = self.convert(self.write())
        self.assertEqual(code, 0, r)
        self.assertEqual((r['animation'], r['frames'], r['rate']), ('foreign_clip', 30, 30.0))
        self.assertEqual(r['bones_matched'], len(BONES))
        self.assertEqual(r['bones_written'], 1)
        self.assertEqual(r['animated_nodes_not_in_skeleton'], ['ik_target'])
        self.assertFalse(r['root_motion'])
        self.assertAlmostEqual(self.spine_angle(r, 15), 30.0, delta=0.01)
        self.assertAlmostEqual(self.spine_angle(r, 30), 60.0, delta=0.01)
        self.assertAlmostEqual(self.spine_angle(r, 6), 12.0, delta=0.05)
        self.assertEqual(r['notes'], [])
        self.assertEqual([n for n, _ in T.Clip.from_xanim(r['written']).notes], ['end'])

    def test_strict_fails_on_an_animated_node_without_a_bone(self):
        code, r = self.convert(self.write(), '--strict')
        self.assertEqual(code, 2)
        self.assertIn('ik_target', r['error'])

    def test_wrapper_scale_and_units_do_not_move_the_bones(self):
        code, r = self.convert(self.write(wrapper_scale=0.01, extra=False))
        self.assertEqual(code, 0, r)
        self.assertEqual(r['bones_written'], 1)       # every other bone is still at its bind pose
        self.assertEqual(r['bones_with_translation'], 0)

    def test_step_and_spline_samplers(self):
        code, r = self.convert(self.write('STEP', extra=False))
        self.assertEqual(code, 0, r)
        self.assertAlmostEqual(self.spine_angle(r, 14), 0.0, delta=0.01)
        self.assertAlmostEqual(self.spine_angle(r, 15), 30.0, delta=0.01)
        code, r = self.convert(self.write('CUBICSPLINE', extra=False))
        self.assertEqual(code, 0, r)
        self.assertAlmostEqual(self.spine_angle(r, 15), 30.0, delta=0.01)
        self.assertAlmostEqual(self.spine_angle(r, 30), 60.0, delta=0.01)

    def test_notes_loop_fps_and_no_match(self):
        code, r = self.convert(self.write(extra=False), '--note', 'hit:0.5', '--loop', '--fps', '20')
        self.assertEqual(code, 0, r)
        self.assertEqual((r['frames'], r['rate'], r['loop']), (20, 20.0, True))
        c = T.Clip.from_xanim(r['written'])
        self.assertEqual([(n, round(t, 4)) for n, t in c.notes], [('hit', 0.5), ('end', 1.0)])
        self.assertTrue(c.loop)
        code, r = self.convert(self.write(extra=False), '--note', 'late:9')
        self.assertEqual(code, 2)
        other = os.path.join(self.d, 'other.json')
        save(other, {'bones': [{'name': 'unrelated', 'parent': None}]})
        code, r = run('from-gltf', self.write(extra=False), '--skeleton', other, '--out', os.path.join(self.d, 'x'))
        self.assertEqual(code, 2)

    def test_root_motion_from_the_named_node(self):
        skel = self.skel
        c = author_clip.build(skel, 'mover', 1.0, 30.0, [('j_head', (0, 0, 20))], (48, 0, 0))
        path = os.path.join(self.d, 'mover.glb')
        T.write_gltf(path, skel, c)
        g = T.Gltf(path)
        del g.doc['animations'][0]['extras']              # as a DCC tool exports it: no extras
        del g.doc['asset']['extras']
        text = json.dumps(g.doc).encode()
        text += b' ' * (-len(text) % 4)
        blob = g.buffers[0]
        with open(path, 'wb') as f:
            f.write(struct.pack('<III', 0x46546C67, 2, 28 + len(text) + len(blob)))
            f.write(struct.pack('<II', len(text), 0x4E4F534A) + text + struct.pack('<II', len(blob), 0x004E4942) + blob)
        code, r = self.convert(path)
        self.assertEqual(code, 0, r)
        self.assertTrue(r['root_motion'])
        self.assertEqual(r['root_motion_end'], [48.0, 0.0, 0.0])
        _, info = run('inspect', r['written'])
        self.assertEqual((info['flags'], info['asset_type']), (2, 2))


if __name__ == '__main__':
    unittest.main()

"""Unit tests of the env-model tools (no game data needed): python -m unittest test_env_model -v"""
import os
import struct
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collision_boxes  # noqa: E402
import iw7_model_author as author  # noqa: E402
import iw7_model_to_glb as to_glb  # noqa: E402
import iw7_xmodel_io as io  # noqa: E402
import iw7_zt_stream as zs  # noqa: E402
import mesh_glb  # noqa: E402
import t7_env_material as envmat  # noqa: E402
import t7_env_port as port  # noqa: E402


def cube(size=10.0, z0=0.0):
    """Closed axis-aligned box, outward counter-clockwise faces, per-face UVs (24 vertices)."""
    s = size
    faces = [((0, 0, 1), [(0, 0, s), (s, 0, s), (s, s, s), (0, s, s)]),
             ((0, 0, -1), [(0, 0, 0), (0, s, 0), (s, s, 0), (s, 0, 0)]),
             ((1, 0, 0), [(s, 0, 0), (s, s, 0), (s, s, s), (s, 0, s)]),
             ((-1, 0, 0), [(0, 0, 0), (0, 0, s), (0, s, s), (0, s, 0)]),
             ((0, 1, 0), [(0, s, 0), (0, s, s), (s, s, s), (s, s, 0)]),
             ((0, -1, 0), [(0, 0, 0), (s, 0, 0), (s, 0, s), (0, 0, s)])]
    P, N, UV, T = [], [], [], []
    for n, quad in faces:
        b = len(P)
        P += [(x, y, z + z0) for x, y, z in quad]
        N += [n] * 4
        UV += [(0, 0), (1, 0), (1, 1), (0, 1)]
        T += [(b, b + 1, b + 2), (b, b + 2, b + 3)]
    return {'P': np.array(P, float), 'N': np.array(N, float), 'UV': np.array(UV, float), 'tris': np.array(T)}


class Stream(unittest.TestCase):
    def test_records_roundtrip(self):
        w = zs.Writer()
        w.array(b'\x01\x02\x03\x04', 2)
        w.array(None, 4)
        w.string('abc')
        w.asset(None)
        w.raw(b'xyz')
        w.asset(('offset', 3, 0))
        r = zs.Reader(w.bytes())
        self.assertEqual(r.array(2), b'\x01\x02\x03\x04')
        self.assertIsNone(r.array(4))
        self.assertEqual(r.string(), 'abc')
        self.assertIsNone(r.asset())
        self.assertEqual(r.raw(), b'xyz')
        self.assertEqual(r.asset(), ('offset', 3, 0))
        self.assertTrue(r.at_end())

    def test_array_size_checked(self):
        with self.assertRaises(zs.StreamError):
            zs.Writer().array(b'\x01\x02\x03', 2)


class Author(unittest.TestCase):
    def build(self, lods):
        d = tempfile.mkdtemp()
        rep = author.build_model('t_cube', lods, d)
        return d, rep

    def test_cube_model(self):
        d, rep = self.build([{'dist': 500, 'groups': {'mo/a': cube()}}, {'dist': 0, 'groups': {'mo/a': cube()}}])
        xm = io.parse_xmodel(open(os.path.join(d, 'xmodel', 't_cube.xmb'), 'rb').read())
        self.assertEqual(io.write_xmodel(xm), open(os.path.join(d, 'xmodel', 't_cube.xmb'), 'rb').read())
        self.assertEqual(xm['head'][io.XM['numLods']], 2)
        self.assertEqual(io.lod_info(xm['head'], 0)['dist'], 500)
        self.assertGreaterEqual(io.lod_info(xm['head'], 1)['dist'], author.LAST_LOD_DIST)
        xs = io.parse_xsurfs(open(os.path.join(d, 'xsurface', 't_cube_lod0.xsb'), 'rb').read())
        s = xs['surfs'][0]
        self.assertEqual(len(s['verts']), 24)
        self.assertEqual(len(s['tris']), 12)
        self.assertTrue(np.all(s['verts']['normal'] >> 30 == 3))
        # IW winding: (b - a) x (c - a) opposes the vertex normal
        P = s['verts']['xyz'].astype(float)
        N = to_glb.decode_unit(s['verts']['normal'])
        t = s['tris'].astype(int)
        fn = np.cross(P[t[:, 1]] - P[t[:, 0]], P[t[:, 2]] - P[t[:, 0]])
        self.assertTrue(np.all(np.sum(fn * N[t[:, 0]], 1) < 0))
        # tangent = dP/du; sign bits 0 where dP/dv = N x T
        T = to_glb.decode_unit(s['verts']['tangent'])
        top = np.where(N[:, 2] > 0.9)[0]
        self.assertTrue(np.allclose(T[top], [1, 0, 0], atol=0.01))
        self.assertTrue(np.all(s['verts']['tangent'][top] >> 30 == 0))

    def test_lod_order_refused(self):
        big = cube()
        small = {k: v for k, v in cube().items()}
        small['tris'] = small['tris'][:6]
        with self.assertRaises(ValueError):
            self.build([{'dist': 100, 'groups': {'mo/a': small}}, {'dist': 0, 'groups': {'mo/a': big}}])

    def test_bad_normals_rebuilt(self):
        c = cube()
        c['N'] = -c['N']                     # inverted source normals
        st = {}
        P, N, UV, T = author.prepare(c, stats=st)
        self.assertTrue(st['normals_rebuilt'])
        self.assertEqual(st['normal_agreement'], 1.0)

    def test_split_large_surface(self):
        n = 70000
        P = np.random.rand(n * 3, 3) * 100
        g = {'P': P, 'N': np.tile([0, 0, 1.0], (n * 3, 1)), 'UV': np.random.rand(n * 3, 2), 'tris': np.arange(n * 3).reshape(-1, 3)}
        chunks = list(author.split_surface(g['P'], g['N'], g['UV'], g['tris']))
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c[0]) <= author.MAX_VERTS for c in chunks))
        self.assertEqual(sum(len(c[3]) for c in chunks), n)


class Collision(unittest.TestCase):
    def test_hollow_box_keeps_opening(self):
        # a 96-wide box without its +y wall: the opening must stay free of boxes
        c = cube(96)
        keep = [i for i, t in enumerate(c['tris']) if not np.all(c['P'][t][:, 1] > 95)]
        c['tris'] = c['tris'][keep]
        boxes = collision_boxes.boxes_from_mesh({'a': c}, 8)
        self.assertTrue(boxes)
        inside = [b for b in boxes if b[0][1] > 20 and b[1][1] > 100 and 20 < b[0][0] < 70 and 20 < b[0][2] < 70]
        self.assertFalse(inside)


class Material(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(envmat.classify({'name': 'a', 'techset': ',mc/lit_decal_reveal#x'}), 'skip')
        self.assertEqual(envmat.classify({'name': 'a', 'techset': ',mc/glass#x'}), 'glass')
        self.assertEqual(envmat.classify({'name': 'a', 'techset': ',mc/lit_decal#x', 'alpha': 'cutout'}), 'decal')
        self.assertEqual(envmat.classify({'name': 'a', 'techset': ',mc/lit_advanced#x'}), 'opaque')
        self.assertEqual(envmat.classify({'name': 'a', 'techset': ',mc/lit#x', 'emissive': {'path': 'e.png'}}), 'emissive')


class MaterialDetail(unittest.TestCase):
    def test_scale_normal(self):
        n = np.zeros((2, 2, 3), np.float32)
        n[..., 0], n[..., 2] = 0.6, 0.8
        self.assertTrue(np.allclose(envmat.scale_normal(n, 0.0), [0, 0, 1]))
        h = envmat.scale_normal(n, 0.5)
        self.assertTrue(np.allclose(np.linalg.norm(h, axis=-1), 1.0))
        self.assertLess(h[0, 0, 0], 0.6)

    def test_dedupe_images(self):
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, 'images'))
        os.makedirs(os.path.join(d, 'materials', 'mo'))
        for n, b in (('a_nog', b'same'), ('b_nog', b'same'), ('b_cs', b'other')):
            open(os.path.join(d, 'images', n + '.dds'), 'wb').write(b)
        import json
        json.dump({'textureTable': [{'image': 'b_nog'}, {'image': 'b_cs'}]}, open(os.path.join(d, 'materials', 'mo', 'b.json'), 'w'))
        mats = [{'iw7': 'mo/b', 'images': {'nog': 'b_nog', 'cs': 'b_cs'}}]
        self.assertEqual(port.dedupe_images(d, mats), {'b_nog': 'a_nog'})
        self.assertEqual(mats[0]['images']['nog'], 'a_nog')
        self.assertFalse(os.path.exists(os.path.join(d, 'images', 'b_nog.dds')))
        self.assertEqual(json.load(open(os.path.join(d, 'materials', 'mo', 'b.json')))['textureTable'][0]['image'], 'a_nog')


class Glb(unittest.TestCase):
    def test_glb_roundtrip_through_iw7(self):
        d = tempfile.mkdtemp()
        author.build_model('t_rt', [{'dist': 0, 'groups': {'mo/a': cube(10, 5)}}], d)
        out = os.path.join(d, 'rt.glb')
        to_glb.write_glb(out, to_glb.load(d, 't_rt', 0), {})
        g = mesh_glb.meshes(out)['mo/a']
        self.assertTrue(np.allclose(g['P'].min(0), [0, 0, 5], atol=1e-3))
        self.assertTrue(np.allclose(g['P'].max(0), [10, 10, 15], atol=1e-3))
        self.assertEqual(author.normal_agreement(g['P'], g['N'], g['tris']), 1.0)


if __name__ == '__main__':
    unittest.main()

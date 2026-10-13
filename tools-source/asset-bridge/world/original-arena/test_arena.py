"""Targeted original geometry/invalid-format/collision-reference checks; no native."""
import copy
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest

import arena
import prepare
import readback


class ArenaTests(unittest.TestCase):
    def setUp(self):
        self.scene = arena.original_scene()

    def test_original_scene_geometry_has_seven_closed_boxes(self):
        mesh = arena.geometry(self.scene)
        surface = mesh['surfaces'][0]
        self.assertEqual((len(surface['vertices']), len(surface['triangles'])), (168, 84))
        self.assertEqual(mesh['bounds'], {'midpoint': [0, 0, 40], 'half_size': [272, 208, 56]})
        for t in surface['triangles']:
            a,b,c = [surface['vertices'][i] for i in t]
            u = [y-x for x,y in zip(a['position'], b['position'])]
            v = [y-x for x,y in zip(a['position'], c['position'])]
            cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
            self.assertGreater(sum(x*y for x,y in zip(cross,a['normal'])), 0)
        self.assertFalse(mesh['iw7_serialized'])

    def test_invalid_boxes_counts_identifiers_and_claims_refused(self):
        for change in ('nan', 'inverted', 'degenerate', 'oversized', 'duplicate', 'too_many', 'runtime', 'material', 'unknown'):
            with self.subTest(change=change):
                s = copy.deepcopy(self.scene)
                if change == 'nan': s['solids'][0]['minimum'][0] = math.nan
                if change == 'inverted': s['solids'][0]['minimum'][0] = 300
                if change == 'degenerate': s['solids'][0]['maximum'][2] = -16
                if change == 'oversized': s['solids'][0]['maximum'][0] = 5000
                if change == 'duplicate': s['solids'][1]['name'] = s['solids'][0]['name']
                if change == 'too_many': s['solids'] *= 2
                if change == 'runtime': s['runtime_verified'] = True
                if change == 'material': s['material_reference'] = 'invented'
                if change == 'unknown': s['unknown'] = 1
                with self.assertRaises(ValueError): arena.validate(s)

    def test_floor_hit_and_outside_miss(self):
        floor = self.scene['solids'][0]
        hit = arena.swept_box(floor, [0, 0, 32], [0, 0, -32], [0,0,0])
        self.assertTrue(hit['hit']); self.assertEqual(hit['fraction'], .5); self.assertEqual(hit['normal'], [0,0,1])
        self.assertFalse(arena.swept_box(floor, [300,0,32], [300,0,-32], [0,0,0])['hit'])

    def test_actor_falls_to_floor_at_center_height_36(self):
        hit = arena.trace(self.scene, [0,0,80], [0,0,20], self.scene['actor_half_size'])
        self.assertEqual(hit['solid'], 'floor')
        self.assertAlmostEqual(hit['fraction'], 44/60)

    def test_tangent_floor_motion_clear_but_motion_into_floor_blocked(self):
        floor = self.scene['solids'][0]; half = self.scene['actor_half_size']
        self.assertFalse(arena.swept_box(floor, [-128,-96,36], [128,-96,36], half)['hit'])
        self.assertEqual(arena.swept_box(floor, [0,0,36], [0,0,20], half)['fraction'], 0)
        self.assertFalse(arena.swept_box(floor, [0,0,36], [0,0,80], half)['hit'])

    def test_side_wall_and_obstacle_block_actor(self):
        half = self.scene['actor_half_size']
        wall = arena.trace(self.scene, [200,80,36], [300,80,36], half)
        self.assertEqual(wall['solid'], 'east'); self.assertAlmostEqual(wall['fraction'], .41)
        obstacle = arena.trace(self.scene, [-64,0,36], [96,0,36], half)
        self.assertEqual(obstacle['solid'], 'obstacle'); self.assertAlmostEqual(obstacle['fraction'], 65/160)

    def test_start_inside_stationary_and_degenerate_queries(self):
        floor = self.scene['solids'][0]
        self.assertTrue(arena.swept_box(floor, [0,0,-8], [0,0,-8], [0,0,0])['start_solid'])
        self.assertFalse(arena.swept_box(floor, [0,0,32], [0,0,32], [0,0,0])['hit'])
        for half in ([0,-1,0], [True,0,0]):
            with self.assertRaises(ValueError): arena.swept_box(floor,[0,0,32],[0,0,-32],half)

    def test_route_reaches_goal_around_obstacle_and_door_is_clear(self):
        route = arena.route_check(self.scene)
        self.assertTrue(route['clear']); self.assertTrue(route['goal_reached'])
        self.assertFalse(route['native_collision_verified'])
        self.assertFalse(arena.trace(self.scene,[0,-160,36],[0,-224,36],self.scene['actor_half_size'])['hit'])

    def test_goal_reuses_trigger_adapter_without_claiming_solid_collision(self):
        source, converted = arena.goal_trigger(self.scene)
        self.assertEqual(source['trigger']['hulls'][0]['bounds'], {'midPoint': [152,112,40], 'halfSize': [40,32,40]})
        self.assertEqual(converted['trigger']['count'], 1)
        self.assertFalse(converted['runtime_ready'])

    def test_prepared_source_reuses_writer_and_refuses_changed_seam(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/'prepared'
            result = prepare.prepare(output)
            self.assertEqual(result['prepared_files'], 7)
            self.assertFalse(result['native_collision_verified'])
            cpp = (output/'arena_writer.cpp').read_text()
            self.assertIn('probe_vertex_count', cpp)
            self.assertIn('paris_original_arena.xmb', cpp)
            self.assertIn('!rm->physicsAsset', cpp)
            self.assertNotIn('paris_model_probe', cpp)
            with self.assertRaises(ValueError): prepare.prepare(output)
            base = (arena.REPO/'ops/model-lab/writer.cpp').read_text()
            with self.assertRaises(ValueError): prepare.adapt_writer(base.replace('surf.vertCount=24;', 'surf.vertCount=23;'))

    def test_generated_cpp_literals_and_report_are_well_formed(self):
        mesh = arena.geometry(self.scene)
        self.assertIn('probe_radius_squared = 126464.0f;', prepare.header(mesh))
        cpp = prepare.adapt_writer((arena.REPO/'ops/model-lab/writer.cpp').read_text())
        line = next(x for x in cpp.splitlines() if 'std::cout' in x)
        import re
        strings = [json.loads(x) for x in re.findall(r'"(?:[^"\\]|\\.)*"', line)]
        report = json.loads(strings[0]+'168'+strings[1]+'84'+strings[2])
        self.assertEqual(report['schema'], 'iw7.original-arena-roundtrip/1')
        self.assertFalse(report['physics_serialized'])


def synthetic_records(mesh):
    """Tiny authored typed streams for reader fault injection, never retail data."""
    def array(payload, count):
        return b'\x08\x00' if not count else b'\x08\x01'+struct.pack('<I',count)+payload
    def name(text, kind=6):
        return bytes((kind,0)) if text is None else bytes((kind,1))+text.encode()+b'\0'
    surface = mesh['surfaces'][0]
    n, t = len(surface['vertices']), len(surface['triangles'])
    midpoint, half = mesh['bounds']['midpoint'], mesh['bounds']['half_size']
    radius = max(sum(v*v for v in item['position']) for item in surface['vertices'])
    h = bytearray(736);h[20:23]=bytes((1,1,0))
    struct.pack_into('<HHf',h,24,0,1,1);struct.pack_into('<f',h,40,math.sqrt(radius))
    struct.pack_into('<6f',h,44,*(midpoint+half));struct.pack_into('<fHH',h,224,1000000,1,0)
    model = array(h,1)+name(mesh['name'])+name('tag_origin')+array(b'',0)*3+array(bytes(1),1)
    model += array(struct.pack('<8f',0,0,0,1,0,0,0,2),1)+array(b'',0)*3
    model += array(struct.pack('<7f',*(midpoint+half+[radius])),1)+array(bytes(2),1)+array(bytes(8),1)
    model += name(None,7)+name(mesh['name']+'_lod0',7)+name(None,7)*9+array(b'',0)*3
    g = bytearray(56);struct.pack_into('<H',g,16,1)
    s = bytearray(256);struct.pack_into('<3H2B',s,0,0x82,n,t,1,0)
    vertices = b''
    for v in surface['vertices']:
        packed_normal = 0xc0000000
        for i,x in enumerate(v['normal']):packed_normal |= math.floor((x+1)*.5*1023+.5) << (10*i)
        vertices += struct.pack('<3fII2eII',*v['position'],0,0xffffffff,*v['uv'],packed_normal,0)
    faces = b''.join(struct.pack('<3H',*tri) for tri in surface['triangles'])
    raw = array(g,1)+name(mesh['name']+'_lod0')+array(s,1)+array(vertices,n)+array(faces,t)
    raw += array(struct.pack('<4HQ',0,n,0,t,0),1)+b'\x0a\x00'*4
    return model,raw


class IndependentReaderTests(unittest.TestCase):
    def test_valid_original_records_and_native_limits_remain_explicit(self):
        source = arena.geometry(arena.original_scene());model,mesh = synthetic_records(source)
        report=readback.inspect(model,mesh,source)
        self.assertEqual((report['vertices'],report['triangles']),(168,84))
        self.assertFalse(report['physics_serialized']);self.assertFalse(report['runtime_verified'])

    def test_truncation_type_count_trailing_and_geometry_corruption(self):
        source = arena.geometry(arena.original_scene());model,mesh = synthetic_records(source)
        variants = [(model[:-1],mesh),(model,mesh[:-1]),(model+b'x',mesh),(model,mesh+b'x')]
        broken=bytearray(model);broken[0]=7;variants.append((bytes(broken),mesh))
        broken=bytearray(model);struct.pack_into('<I',broken,2,2);variants.append((bytes(broken),mesh))
        # First packed vertex follows group/name/surface/vertex record headers.
        p=6+56+2+len('paris_original_arena_lod0')+1+6+256+6
        broken=bytearray(mesh);struct.pack_into('<f',broken,p,500);variants.append((model,bytes(broken)))
        broken=bytearray(mesh);struct.pack_into('<f',broken,p,float('nan'));variants.append((model,bytes(broken)))
        for m,s in variants:
            with self.subTest(model=len(m),mesh=len(s)):
                with self.assertRaises(ValueError):readback.inspect(m,s,source)


if __name__ == '__main__':
    unittest.main()

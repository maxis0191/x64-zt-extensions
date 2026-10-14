"""Targeted original geometry/invalid-format/collision-reference checks; no native."""
import copy
import hashlib
import json
import math
import re
from pathlib import Path
import struct
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import arena
import prepare
import readback
import model_lab
import prepare_writer
import modal_window
from test_coverage import CoverageTests


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

    def test_halfway_float32_literal_rounds_before_decimal_formatting(self):
        self.assertEqual(prepare.literal(1+2**-24), '1.0f')
        self.assertEqual(prepare.literal(-(1+2**-24)), '-1.0f')

    def test_first_obstacle_contract_selects_existing_faces_and_absolute_bounds(self):
        contract = arena.first_box_contract(self.scene, 'obstacle', [0, 0, 0])
        self.assertEqual(contract['local_bounds'], {'minimum': [16, -32, 0], 'maximum': [48, 32, 32]})
        self.assertEqual(contract['world_bounds'], contract['local_bounds'])
        self.assertEqual(contract['mesh_selection'], {'surface': 0, 'first_vertex': 144,
                         'vertex_count': 24, 'first_triangle': 72, 'triangle_count': 12,
                         'isolated_render_model': False})
        native = contract['native_box']
        self.assertEqual((native['world'], native['observed']), (0, 1))
        self.assertEqual(native['origin'], [32, 0, 16])
        self.assertEqual(native['half_size'], [16, 32, 16])
        self.assertEqual(native['rotation_xyzw'], [0, 0, 0, 1])
        self.assertFalse(native['owner_transform_applied'])
        self.assertEqual(native['provider_internal_game_to_havok_scale'], 1/32)
        self.assertTrue(native['solid_before_create_required'])
        self.assertTrue(all(value is False for key, value in contract.items() if key.endswith('_verified')))

    def test_translated_scaled_box_matches_all_selected_mesh_corners(self):
        contract = arena.first_box_contract(self.scene, 'obstacle', [1024, 2048, 512], 3)
        world = contract['world_bounds']
        self.assertEqual(world, {'minimum': [1072, 1952, 512], 'maximum': [1168, 2144, 608]})
        self.assertEqual(contract['native_box']['origin'], [1120, 2048, 560])
        self.assertEqual(contract['native_box']['half_size'], [48, 96, 48])
        surface = arena.geometry(self.scene)['surfaces'][0]
        vertices = surface['vertices'][144:168]
        transformed = [[3*v['position'][i]+[1024, 2048, 512][i] for i in range(3)] for v in vertices]
        self.assertEqual([min(v[i] for v in transformed) for i in range(3)], world['minimum'])
        self.assertEqual([max(v[i] for v in transformed) for i in range(3)], world['maximum'])
        corners = {(x, y, z) for x in (1072, 1168) for y in (1952, 2144) for z in (512, 608)}
        self.assertEqual({tuple(v) for v in transformed}, corners)
        self.assertTrue(all(144 <= i < 168 for triangle in surface['triangles'][72:84] for i in triangle))
        # Internal provider conversion belongs to the provider, not to GSC bounds.
        self.assertEqual([h/32 for h in contract['native_box']['half_size']], [1.5, 3, 1.5])

    def test_first_box_refuses_missing_names_invalid_or_lossy_placement(self):
        cases = [('missing', [0, 0, 0], 1), ('obstacle', [0, 0], 1),
                 ('obstacle', [True, 0, 0], 1), ('obstacle', [math.nan, 0, 0], 1),
                 ('obstacle', [1+2**-24, 0, 0], 1), ('obstacle', [2**30, 0, 0], 1),
                 ('obstacle', [0, 0, 0], 0), ('obstacle', [0, 0, 0], -1),
                 ('obstacle', [0, 0, 0], True), ('obstacle', [0, 0, 0], math.inf),
                 ('obstacle', [0, 0, 0], 1+2**-24), ('obstacle', [0, 0, 0], 2**124)]
        for name, origin, scale in cases:
            with self.subTest(name=name, origin=origin, scale=scale), self.assertRaises(ValueError):
                arena.first_box_contract(self.scene, name, origin, scale)
        # Exact endpoints alone do not guarantee exact float32 midpoint/half.
        scene = copy.deepcopy(self.scene)
        scene['solids'][-1]['minimum'][0] = .25+2**-25
        scene['solids'][-1]['maximum'][0] = 4096
        with self.assertRaisesRegex(ValueError, 'midpoint/half rounding'):
            arena.first_box_contract(scene, 'obstacle', [0, 0, 0])

    def test_optional_box_sidecar_preserves_existing_writer_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            baseline, selected = root/'baseline', root/'selected'
            prepare.prepare(baseline)
            result = prepare.prepare(selected, first_box='obstacle', model_origin=[1024, 2048, 512], model_scale=3)
            self.assertEqual((result['vertices'], result['triangles'], result['prepared_files']), (168, 84, 8))
            for path in baseline.iterdir():
                self.assertEqual(path.read_bytes(), (selected/path.name).read_bytes())
            contract = json.loads((selected/'first-box.source.json').read_bytes())
            self.assertEqual(contract['geometry_source_sha256'], hashlib.sha256((selected/'geometry.source.json').read_bytes()).hexdigest())
            self.assertIsNone(contract['material_reference'])
            self.assertFalse(contract['rendered_bounds_verified'])
            self.assertFalse(contract['physics_serialized'])
            for kwargs in ({'first_box': 'absent'}, {'model_origin': [1, 2, 3]}, {'model_scale': 2}):
                output = root/'invalid'
                with self.assertRaises(ValueError): prepare.prepare(output, **kwargs)
                self.assertFalse(output.exists())


def synthetic_records(mesh, material=None):
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
    h[8:15] = bytes((0,1,0,1,255,6,0))
    radius_f32, = struct.unpack('<f',struct.pack('<f',radius))
    struct.pack_into('<HHf',h,24,0,1,1);struct.pack_into('<f',h,40,math.sqrt(radius_f32))
    struct.pack_into('<6f',h,44,*(midpoint+half));struct.pack_into('<fHH',h,224,1000000,1,0)
    struct.pack_into('<I',h,240,0x80000000)
    model = array(h,1)+name(mesh['name'])+name('tag_origin')+array(b'',0)*3+array(bytes(1),1)
    model += array(struct.pack('<8f',0,0,0,1,0,0,0,2),1)+array(b'',0)*3
    model += array(struct.pack('<7f',*(midpoint+half+[radius])),1)+array(bytes(2),1)+array(struct.pack('<Q',bool(material)),1)
    model += name(material,7)+name(mesh['name']+'_lod0',7)+name(None,7)*9+array(b'',0)*3
    g = bytearray(56);struct.pack_into('<H',g,16,1)
    s = bytearray(256);struct.pack_into('<3H2B',s,0,0x82,n,t,1,0)
    struct.pack_into('<I',g,20,0x80000000);struct.pack_into('<I',s,224,0x80000000)
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
    def test_character_bounds_byte_matches_native_header_and_old_reader_refuses_it(self):
        source=arena.geometry(arena.original_scene())
        model,mesh=synthetic_records(source,readback.MATERIAL)
        # Closed writerB's observed seven bytes, independently grounded in
        # pinned XModel's layout and the writer's zero-initialized member.
        observed=bytes((0,1,0,1,255,6,0))
        self.assertEqual(model[6+8:6+15], observed)
        text=Path(readback.__file__).read_text()
        corrected='tuple(header[8:15]) == (0,1,0,1,255,6,0)'
        self.assertEqual(text.count(corrected),1)
        prior=text.replace(corrected,'tuple(header[8:15]) == (0,1,0,1,255,6,1)',1)
        namespace={'__name__':'_prior_arena_reader','__file__':readback.__file__}
        exec(compile(prior,readback.__file__,'exec'),namespace)
        with self.assertRaisesRegex(ValueError,'LOD/shadow/collision metadata'):
            namespace['inspect'](model,mesh,source,expected_material=readback.MATERIAL)
        self.assertTrue(readback.inspect(model,mesh,source,expected_material=readback.MATERIAL)['geometry_roundtrip_verified'])
        for offset,value in ((9,0),(12,0),(13,0),(14,1)):
            bad=bytearray(model);bad[6+offset]=value
            with self.subTest(offset=offset),self.assertRaisesRegex(ValueError,'LOD/shadow/collision metadata'):
                readback.inspect(bytes(bad),mesh,source,expected_material=readback.MATERIAL)

    def test_all_three_rigid_masks_refuse_lod_group_and_surface_corruption(self):
        source=arena.geometry(arena.original_scene());model,mesh=synthetic_records(source)
        surface_offset=6+56+2+len('paris_original_arena_lod0')+1+6
        for role,offset in (('model',6+240),('group',6+20),('surface',surface_offset+224)):
            for byte in (0,31):
                changed=bytearray(model if role=='model' else mesh);changed[offset+byte]^=1
                with self.subTest(role=role,byte=byte),self.assertRaisesRegex(ValueError,'root part bits'):
                    readback.inspect(bytes(changed) if role=='model' else model,
                                     mesh if role=='model' else bytes(changed),source)
    def test_explicit_material_binding_and_opaque_pointer_relocation(self):
        source=arena.geometry(arena.original_scene())
        unbound,mesh=synthetic_records(source)
        bound,_=synthetic_records(source,readback.MATERIAL)
        self.assertTrue(readback.inspect(bound,mesh,source,expected_material=readback.MATERIAL)['material_bound'])
        with self.assertRaises(ValueError):readback.inspect(bound,mesh,source)
        with self.assertRaises(ValueError):readback.inspect(unbound,mesh,source,expected_material=readback.MATERIAL)
        with self.assertRaises(ValueError):readback.inspect(bound,mesh,source,expected_material='invented')
        for offset in (9,12,13):
            changed=bytearray(bound);changed[6+offset]=0
            with self.assertRaises(ValueError):readback.inspect(bytes(changed),mesh,source,expected_material=readback.MATERIAL)
    def test_valid_original_records_and_native_limits_remain_explicit(self):
        source = arena.geometry(arena.original_scene());model,mesh = synthetic_records(source)
        report=readback.inspect(model,mesh,source)
        self.assertEqual((report['vertices'],report['triangles']),(168,84))
        self.assertFalse(report['physics_serialized']);self.assertFalse(report['runtime_verified'])

    def test_decimal_scene_uses_actual_float32_bounds_positions_and_radius(self):
        for change in ('floor', 'radius'):
            with self.subTest(change=change):
                scene=arena.original_scene()
                if change == 'floor':
                    scene['solids'][0]['minimum'][2] = -16.1
                else:
                    scene['solids'][3]['maximum'][0] = 272.1
                    scene['solids'][3]['maximum'][2] = 96.1
                self.assertTrue(arena.route_check(scene)['clear'])
                source=arena.geometry(scene);model,mesh=synthetic_records(source)
                self.assertTrue(readback.inspect(model,mesh,source)['geometry_roundtrip_verified'])
                # A one-ULP corruption remains refused; the fix is not epsilon.
                broken=bytearray(model)
                bits,=struct.unpack_from('<I',broken,6+44)
                struct.pack_into('<I',broken,6+44,bits+1)
                with self.assertRaisesRegex(ValueError,'model bounds'):
                    readback.inspect(bytes(broken),mesh,source)
                broken=bytearray(model)
                bits,=struct.unpack_from('<I',broken,6+40)
                struct.pack_into('<I',broken,6+40,bits+1)
                with self.assertRaisesRegex(ValueError,'radius'):
                    readback.inspect(bytes(broken),mesh,source)

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


class ModelLabTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('pwsh'), 'PowerShell pack binding source checks require pwsh')
    def test_required_pack37_is_unique_after_pack17_and_refuses_coercions(self):
        script=r'''
param($Helper17,$Helper37,$Measure,$Root)
$ErrorActionPreference='Stop'
. $Helper17
. $Helper37
$baseline=@(foreach($i in 1..71){[pscustomobject]@{Relative="main/authored-$i.ff";Source=(Join-Path $Root "absent-$i.ff");Mode='HardLink'}})
$baseline+=[pscustomobject]@{Relative='main/fileSysCheck.cfg';Source=(Join-Path $Root 'sentinel');Mode='Copy'}
$baseline[0]=[pscustomobject]@{Relative='zone/assetfile1.pak';Source=(Join-Path $Root 'assetfile1.pak');Mode='HardLink';ExpectedSourceId='11111111:0000000000000001'}
$record17=[pscustomobject]@{Schema='iw7.world-required-pak17/1';BaselineBindingSHA256=('a'*64);ReviewedManifestSHA256='9116255ef148a324df15fa914795a7917615f023973111fdc39ae7329a9dcbf4';Input=[pscustomobject]@{Relative='zone/assetfile17.pak';Source=(Join-Path $Root 'assetfile17.pak');Mode='HardLink';Bytes=104595492L;ModifiedUtc='2026-09-29T21:45:47.6718742Z';Attributes=32;ExpectedSourceId='11111111:0000000000000017';ExpectedSHA256='6f5c0d1937b5a707d4e1fb3009f68a827714d9e4a72ff2d6570b57dbf6b0f058'}}
$existing=@($baseline)+@(Get-ArenaRequiredPak17Input $baseline $record17 ('a'*64))
$record=[pscustomobject]@{Schema='iw7.world-required-pak37/1';BaselineBindingSHA256=('a'*64);RequiredPak17BindingSHA256=('b'*64);ReviewedManifestSHA256='9116255ef148a324df15fa914795a7917615f023973111fdc39ae7329a9dcbf4';CauseModalRecordSHA256='fb2ec614bc6ed8bce15dd8067aea4eed69b7da288e0c96fac3d8a8835350a9c6';Input=[pscustomobject]@{Relative='zone/assetfile37.pak';Source=(Join-Path $Root 'assetfile37.pak');Mode='HardLink';Bytes=53477412L;ModifiedUtc='2026-09-29T21:46:01.4996203Z';Attributes=32;ExpectedSourceId='11111111:0000000000000037';ExpectedSHA256='839c1da30e43b9c5c78cc457d3fa3ef61bd85ae818c81a2d2d0b30ff187fb349'}}
$prior=$existing|ConvertTo-Json -Depth 6 -Compress
$one=Get-ArenaRequiredPak37Input $existing $record ('a'*64) ('b'*64)
if($one.Relative -cne 'zone/assetfile37.pak' -or $one.ExpectedSourceId -cne $record.Input.ExpectedSourceId -or $one.ExpectedSHA256 -cne $record.Input.ExpectedSHA256 -or (@($existing)+@($one)).Count -ne 74){throw 'Wrong unique pack37 binding'}
if(($existing|ConvertTo-Json -Depth 6 -Compress) -cne $prior -or $baseline.Count -ne 72){throw 'Preceding profile mutated'}
foreach($kind in 'relative','source','mode','bytes','sha','id','attrs','baseline','pack17','manifest','cause','date'){
    $bad=$record|ConvertTo-Json -Depth 6|ConvertFrom-Json
    switch($kind){
        relative {$bad.Input.Relative='zone/assetfile38.pak'}
        source {$bad.Input.Source=Join-Path $Root 'other-provider/assetfile37.pak'}
        mode {$bad.Input.Mode='Copy'}
        bytes {$bad.Input.Bytes=1}
        sha {$bad.Input.ExpectedSHA256='0'*64}
        id {$bad.Input.ExpectedSourceId='22222222:0000000000000037'}
        attrs {$bad.Input.Attributes=1056}
        baseline {$bad.BaselineBindingSHA256='0'*64}
        pack17 {$bad.RequiredPak17BindingSHA256='0'*64}
        manifest {$bad.ReviewedManifestSHA256='0'*64}
        cause {$bad.CauseModalRecordSHA256='0'*64}
        date {$bad.Input.ModifiedUtc='not-a-date'}
    }
    $caught=$false;try{$null=Get-ArenaRequiredPak37Input $existing $bad ('a'*64) ('b'*64)}catch{$caught=$true}
    if(!$caught){throw "Invalid supplemental $kind accepted"}
}
foreach($field in 'Schema','BaselineBindingSHA256','RequiredPak17BindingSHA256','ReviewedManifestSHA256','CauseModalRecordSHA256'){
    $bad=$record|ConvertTo-Json -Depth 6|ConvertFrom-Json;$bad.$field=@($bad.$field)
    $caught=$false;try{$null=Get-ArenaRequiredPak37Input $existing $bad ('a'*64) ('b'*64)}catch{$caught=$true};if(!$caught){throw "Singleton contract $field accepted"}
}
foreach($field in 'Relative','Mode','Source','ExpectedSHA256','ExpectedSourceId','Bytes','ModifiedUtc','Attributes'){
    $bad=$record|ConvertTo-Json -Depth 6|ConvertFrom-Json;$bad.Input.$field=@($bad.Input.$field)
    $caught=$false;try{$null=Get-ArenaRequiredPak37Input $existing $bad ('a'*64) ('b'*64)}catch{$caught=$true};if(!$caught){throw "Singleton input $field accepted"}
}
foreach($badNumber in @('53477412',53477412.0,$true)){
    $bad=$record|ConvertTo-Json -Depth 6|ConvertFrom-Json;$bad.Input.Bytes=$badNumber
    $caught=$false;try{$null=Get-ArenaRequiredPak37Input $existing $bad ('a'*64) ('b'*64)}catch{$caught=$true};if(!$caught){throw 'Coerced size accepted'}
}
foreach($time in @($record.Input.ModifiedUtc,[datetime]'2026-09-29T21:46:01.4996203Z',[datetimeoffset]'2026-09-29T21:46:01.4996203Z')){
    $bad=$record|ConvertTo-Json -Depth 6|ConvertFrom-Json;$bad.Input.ModifiedUtc=$time;$null=Get-ArenaRequiredPak37Input $existing $bad ('a'*64) ('b'*64)
}
foreach($kind in 'missing17','otherpak','repeat37','arrayidentifier','arrayreceipt','arrayinput'){
    $badExisting=$existing|ConvertTo-Json -Depth 6|ConvertFrom-Json;$bad=$record|ConvertTo-Json -Depth 6|ConvertFrom-Json
    switch($kind){
        missing17 {$badExisting=$baseline}
        otherpak {$badExisting[2].Relative='zone/assetfile38.pak'}
        repeat37 {$badExisting=@($badExisting)+@($one)}
        arrayidentifier {$badExisting[2].Relative=@($badExisting[2].Relative)}
        arrayreceipt {$bad=@($bad)}
        arrayinput {$bad.Input=@($bad.Input)}
    }
    $caught=$false;try{$null=Get-ArenaRequiredPak37Input $badExisting $bad ('a'*64) ('b'*64)}catch{$caught=$true};if(!$caught){throw "Invalid profile $kind accepted"}
}
$dummy=@{PackageRoot=$Root;RunRoot=$Root;StockBindingPlan='absent';StockBindingPlanSHA256=('a'*64);ToolSource=$Root;CandidateRoot=$Root;CandidateArtifactSHA256=('b'*64);NativeJobAssembly='absent.dll'}
$caught=$false;try{& $Measure @dummy -RequiredPak37Binding absent -RequiredPak37BindingSHA256 ('c'*64)}catch{$caught=$_.Exception.Message -ceq 'Pack37 requires the preceding reviewed pack17 supplement.'};if(!$caught){throw 'Missing pack17 not refused before file/native access'}
$caught=$false;try{& $Measure @dummy -RequiredPak37Binding absent}catch{$caught=$_.Exception.Message -ceq 'Pack37 supplement needs its exact metadata receipt and digest.'};if(!$caught){throw 'Unpaired pack37 receipt not refused before file/native access'}
if('IW7.AnimationProbe.NativeJob' -as [type]){throw 'Pure checks loaded a native job'}
'''
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'pack37.ps1';path.write_text(script,encoding='utf-8')
            here=Path(model_lab.__file__).parent
            result=subprocess.run([shutil.which('pwsh'),'-NoLogo','-NoProfile','-File',str(path),
                str(here/'Pak17Binding.Core.ps1'),str(here/'Pak37Binding.Core.ps1'),
                str(here/'Measure-StockReference.ps1'),temp],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    @unittest.skipUnless(shutil.which('pwsh'), 'PowerShell pack binding source checks require pwsh')
    def test_required_pack17_is_opt_in_same_provider_and_preserves_baseline(self):
        script=r'''
param($Helper,$Root)
$ErrorActionPreference='Stop'
. $Helper
$baseline=@(foreach($i in 1..71){[pscustomobject]@{Relative="main/authored-$i.ff";Source=(Join-Path $Root "absent-$i.ff");Mode='HardLink'}})
$baseline+=[pscustomobject]@{Relative='main/fileSysCheck.cfg';Source=(Join-Path $Root 'sentinel');Mode='Copy'}
$baseline[0]=[pscustomobject]@{Relative='zone/assetfile1.pak';Source=(Join-Path $Root 'assetfile1.pak');Mode='HardLink';ExpectedSourceId='11111111:0000000000000001'}
$record=[pscustomobject]@{Schema='iw7.world-required-pak17/1';BaselineBindingSHA256=('a'*64);ReviewedManifestSHA256='9116255ef148a324df15fa914795a7917615f023973111fdc39ae7329a9dcbf4';Input=[pscustomobject]@{Relative='zone/assetfile17.pak';Source=(Join-Path $Root 'assetfile17.pak');Mode='HardLink';Bytes=104595492L;ModifiedUtc='2026-09-29T21:45:47.6718742Z';Attributes=32;ExpectedSourceId='11111111:0000000000000017';ExpectedSHA256='6f5c0d1937b5a707d4e1fb3009f68a827714d9e4a72ff2d6570b57dbf6b0f058'}}
$prior=$baseline|ConvertTo-Json -Depth 5 -Compress
$one=Get-ArenaRequiredPak17Input $baseline $record ('a'*64)
if($one.Relative -cne 'zone/assetfile17.pak' -or $one.ExpectedSourceId -cne $record.Input.ExpectedSourceId -or $one.ExpectedSHA256 -cne $record.Input.ExpectedSHA256){throw 'Supplement lost guarded identity/content binding'}
if($baseline.Count -ne 72 -or ($baseline|ConvertTo-Json -Depth 5 -Compress) -cne $prior){throw 'Original baseline mutated'}
if(@($baseline)+@($one) -isnot [array] -or (@($baseline)+@($one)).Count -ne 73){throw 'Wrong supplement size'}
foreach($kind in 'relative','source','mode','bytes','sha','id','attrs','baseline','manifest'){
    $bad=$record|ConvertTo-Json -Depth 5|ConvertFrom-Json
    switch($kind){
        relative {$bad.Input.Relative='assetfile17.pak'}
        source {$bad.Input.Source=Join-Path $Root 'different-provider/assetfile17.pak'}
        mode {$bad.Input.Mode='Copy'}
        bytes {$bad.Input.Bytes=1}
        sha {$bad.Input.ExpectedSHA256='0'*64}
        id {$bad.Input.ExpectedSourceId='22222222:0000000000000017'}
        attrs {$bad.Input.Attributes=33}
        baseline {$bad.BaselineBindingSHA256='b'*64}
        manifest {$bad.ReviewedManifestSHA256='0'*64}
    }
    $caught=$false;try{$null=Get-ArenaRequiredPak17Input $baseline $bad ('a'*64)}catch{$caught=$true}
    if(!$caught){throw "Invalid supplemental $kind accepted"}
}
foreach($field in 'Schema','BaselineBindingSHA256','ReviewedManifestSHA256'){
    $bad=$record|ConvertTo-Json -Depth 5|ConvertFrom-Json;$bad.$field=@($bad.$field)
    $caught=$false;try{$null=Get-ArenaRequiredPak17Input $baseline $bad ('a'*64)}catch{$caught=$true}
    if(!$caught){throw "Singleton receipt $field accepted"}
}
foreach($field in 'Relative','Mode','Source','ExpectedSHA256','ExpectedSourceId','Bytes','ModifiedUtc','Attributes'){
    $bad=$record|ConvertTo-Json -Depth 5|ConvertFrom-Json;$bad.Input.$field=@($bad.Input.$field)
    $caught=$false;try{$null=Get-ArenaRequiredPak17Input $baseline $bad ('a'*64)}catch{$caught=$true}
    if(!$caught){throw "Singleton input $field accepted"}
}
foreach($badSize in @('104595492',104595492.0,$true)){
    $bad=$record|ConvertTo-Json -Depth 5|ConvertFrom-Json;$bad.Input.Bytes=$badSize
    $caught=$false;try{$null=Get-ArenaRequiredPak17Input $baseline $bad ('a'*64)}catch{$caught=$true}
    if(!$caught){throw 'Coerced non-integer size accepted'}
}
foreach($time in @($record.Input.ModifiedUtc,[datetime]'2026-09-29T21:45:47.6718742Z',[datetimeoffset]'2026-09-29T21:45:47.6718742Z')){
    $bad=$record|ConvertTo-Json -Depth 5|ConvertFrom-Json;$bad.Input.ModifiedUtc=$time
    $null=Get-ArenaRequiredPak17Input $baseline $bad ('a'*64)
}
'''
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'pack17.ps1';path.write_text(script,encoding='utf-8')
            result=subprocess.run([shutil.which('pwsh'),'-NoLogo','-NoProfile','-File',str(path),
                str(Path(model_lab.__file__).with_name('Pak17Binding.Core.ps1')),temp],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    @unittest.skipUnless(shutil.which('pwsh'), 'PowerShell diagnostic source checks require pwsh')
    def test_load_diagnostic_is_one_shot_original_identity_and_offline_only(self):
        script=r'''
param($Helper,$Root)
$ErrorActionPreference='Stop'
. $Helper
$marker='[ INFO ][ zonetool::iw7::load_zone ]: Loading zone "global_mp"...'
$e=[ordered]@{Attempted=$false;LastBytes=10L;LastProgressMs=30000L}
if(Test-ArenaLoadDiagnosticTrigger $e 44999 10 $marker){throw 'Early diagnostic'}
if(!(Test-ArenaLoadDiagnosticTrigger $e 45000 10 $marker)){throw 'Exact timed stall not detected'}
$cpMarker='[ INFO ][ zonetool::iw7::load_zone ]: Loading zone "global_cp"...'
$cp=[ordered]@{Attempted=$false;LastBytes=10L;LastProgressMs=30000L}
if(Test-ArenaLoadDiagnosticTrigger $cp 45000 10 $marker 'global_cp'){throw 'MP triggered the CP-only witness'}
if(Test-ArenaLoadDiagnosticTrigger $cp 45000 10 $cpMarker){throw 'CP triggered the default MP witness'}
if(!(Test-ArenaLoadDiagnosticTrigger $cp 45000 10 $cpMarker 'global_cp')){throw 'Exact CP stall not detected'}
$cp.Attempted=$true;if(Test-ArenaLoadDiagnosticTrigger $cp 50000 10 $cpMarker 'global_cp'){throw 'CP witness repeated'}
$late=[ordered]@{Attempted=$false;LastBytes=10L;LastProgressMs=90000L;Outcome='NotTriggered'}
if(Test-ArenaLoadDiagnosticTrigger $late 105000 10 $marker){throw 'Late trigger can overrun original deadline'}
if($late.Outcome -cne 'DeclinedLate'){throw 'Late refusal not recorded'}
$e.Attempted=$true;if(Test-ArenaLoadDiagnosticTrigger $e 60000 10 $marker){throw 'Diagnostic repeated'}
$e.Attempted=$false;if(Test-ArenaLoadDiagnosticTrigger $e 60000 11 $marker){throw 'Progress mistaken for stall'}
$script:Clock=55000L
function Get-H1Clock {$script:Clock}
$budget=[pscustomobject]@{StartedMs=0L}
if((Get-ArenaDiagnosticSeconds $budget 20) -ne 20){throw 'Nominal budget changed early'}
$script:Clock=105000L;if((Get-ArenaDiagnosticSeconds $budget 20) -ne 5){throw 'Phase failed to inherit global remaining time'}
$script:Clock=111000L;$caught=$false;try{$null=Get-ArenaDiagnosticSeconds $budget 20}catch{$caught=$true};if(!$caught){throw 'Exhausted global reserve accepted'}
$script:Clock=55000L
function Get-H1OriginalState($Owner){[pscustomobject]@{RootExited=$false;PID=$Owner.PID;Image=$Owner.Image;CreatedUtc='2026-10-14T00:00:00Z';ActiveProcesses=1}}
$script:Calls=@();$script:Registered=0
function Register-H1Original { $script:Registered++ }
function Invoke-OriginalArenaTool($Context,$Exe,$SHA,$Arguments,$Work,$RunRoot,$Phase,$Inputs,$Seconds){
    $script:Calls+=,$Phase
    if($Phase -ceq 'load-cpu' -and ($Seconds -ne 10 -or '--threads' -cnotin $Arguments)){throw 'Wrong CPU witness'}
    if($Phase -ceq 'load-snapshot'){
        if($Seconds -ne 15 -or '--snapshot' -cnotin $Arguments){throw 'Wrong snapshot bound'}
        $output=$Arguments[[array]::IndexOf($Arguments,'--output')+1];[IO.File]::WriteAllText($output,'Authored minidump placeholder')
    }
    if($Phase -ceq 'load-stack' -and ($Seconds -ne 20 -or '-z' -cnotin $Arguments -or '-p' -cin $Arguments)){throw 'Debugger must read only offline dump'}
    $Context.Closed=$true;[pscustomobject]@{ExitCode=0;JobClosed=$true}
}
$logs=Join-Path $Root 'logs';[IO.Directory]::CreateDirectory($logs)|Out-Null
[IO.File]::WriteAllText((Join-Path $logs 'stdout.log'),$marker+"`n")
$target=[pscustomobject]@{Owner=[pscustomobject]@{PID=123;Image=(Join-Path $Root 'authored.exe')};Closed=$false;Lease=[pscustomobject]@{Token='authored'};Work=$Root}
$state=@{Identity=@{PID=123;Image=$target.Owner.Image;CreatedUtc='2026-10-14T00:00:00Z'}}
$options=[pscustomobject]@{StartedMs=0L;RunRoot=$Root;CaptureSource='authored.py';Python='authored-python';PythonSHA256=('1'*64);Cdb='authored-cdb';CdbSHA256=('2'*64);Symbols=$Root;ToolSHA256=('3'*64);Inputs=@()}
$e=[ordered]@{Attempted=$false;LastBytes=(Get-Item -LiteralPath (Join-Path $logs 'stdout.log')).Length;LastProgressMs=0L;Outcome='NotTriggered'}
$caught=$false;try{Invoke-ArenaLoadDiagnostic $target $state $logs $options $e}catch{$caught=$_.Exception.Message -ceq 'Load diagnostic captured; material reference not measured.'}
if(!$caught -or $e.Outcome -cne 'Captured' -or $script:Calls.Count -ne 3 -or $script:Registered -ne 1 -or !$target.DiagnosticContext.Closed){throw 'Bounded capture/closure differs'}
$script:Calls=@();$e.Attempted=$false;$state.Identity.PID=124
$caught=$false;try{Invoke-ArenaLoadDiagnostic $target $state $logs $options $e}catch{$caught=$true}
if(!$caught -or $script:Calls.Count){throw 'Nonoriginal target allowed diagnostics'}
$e.Attempted=$false;$state.Identity.PID=123;$state.Identity.CreatedUtc='2026-10-14T00:00:01Z'
$caught=$false;try{Invoke-ArenaLoadDiagnostic $target $state $logs $options $e}catch{$caught=$true}
if(!$caught -or $script:Calls.Count){throw 'Different root generation allowed diagnostics'}
'''
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'diagnostic-source.ps1';path.write_text(script,encoding='utf-8')
            result=subprocess.run([shutil.which('pwsh'),'-NoLogo','-NoProfile','-File',str(path),
                str(Path(model_lab.__file__).with_name('LoadDiagnostic.Core.ps1')),temp],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    @unittest.skipUnless(shutil.which('pwsh'), 'PowerShell stock date source checks require pwsh')
    def test_modal_text_is_one_original_helper_and_no_dialog_stays_negative(self):
        script=r'''
param($Core,$Measure,$Root)
$ErrorActionPreference='Stop'
. $Core
function Get-H1Clock {55000L}
$script:Created='2026-10-14T00:00:00.0000006Z'
function Get-H1OriginalState($Owner){[pscustomobject]@{RootExited=$false;PID=$Owner.PID;Image=$Owner.Image;CreatedUtc=$script:Created}}
function Register-H1Original {}
$script:Calls=0;$script:Found=$true
function Invoke-OriginalArenaTool($Context,$Exe,$SHA,$Arguments,$Work,$RunRoot,$Phase,$Inputs,$Seconds){
    $script:Calls++
    if($Phase -cne 'load-modal' -or $Seconds -ne 10 -or '--snapshot' -cin $Arguments -or '-z' -cin $Arguments){throw 'Only one modal helper is allowed'}
    $filetime=$Arguments[[array]::IndexOf($Arguments,'--created-filetime')+1]
    if($filetime -cne [string](([datetimeoffset]$script:Created).UtcDateTime.ToFileTimeUtc())){throw 'Exact original 100ns creation identity lost'}
    if($Arguments[[array]::IndexOf($Arguments,'--parent-pid')+1] -cne [string]$PID){throw 'Original caller identity lost'}
    $output=$Arguments[[array]::IndexOf($Arguments,'--output')+1]
    @{schema='iw7.world-modal-window/1';identity_verified_after=$true;modal_window_observed=$script:Found}|ConvertTo-Json|Set-Content -LiteralPath $output
    $Context.Closed=$true;[pscustomobject]@{ExitCode=0;JobClosed=$true}
}
$logs=Join-Path $Root 'logs';[IO.Directory]::CreateDirectory($logs)|Out-Null
$marker='[ INFO ][ zonetool::iw7::load_zone ]: Loading zone "global_mp"...'
[IO.File]::WriteAllText((Join-Path $logs 'stdout.log'),$marker+"`n")
$target=[pscustomobject]@{Owner=[pscustomobject]@{PID=123;Image=(Join-Path $Root 'authored.exe')};Closed=$false;Lease=[pscustomobject]@{Token='authored'};Work=$Root}
$state=@{Identity=@{PID=123;Image=$target.Owner.Image;CreatedUtc=$script:Created}}
$options=[pscustomobject]@{StartedMs=0L;RunRoot=(Join-Path $Root 'found');ModalTextOnly=$true;ModalSource='authored-modal.py';Python='authored-python';PythonSHA256=('1'*64);ToolSHA256=('3'*64);Inputs=@()}
$e=[ordered]@{Attempted=$false;LastBytes=(Get-Item -LiteralPath (Join-Path $logs 'stdout.log')).Length;LastProgressMs=0L;Outcome='NotTriggered'}
$caught=$false;try{Invoke-ArenaLoadDiagnostic $target $state $logs $options $e}catch{$caught=$_.Exception.Message -ceq 'Load diagnostic captured; material reference not measured.'}
if(!$caught -or $script:Calls -ne 1 -or $e.Outcome -cne 'Captured' -or !$e.ModalWindowObserved -or !$target.DiagnosticContext.Closed){throw 'Modal capture differs'}
$script:Calls=0;$script:Found=$false;$e.Attempted=$false;$e.Outcome='NotTriggered';$options.RunRoot=Join-Path $Root 'negative'
$caught=$false;try{Invoke-ArenaLoadDiagnostic $target $state $logs $options $e}catch{$caught=$_.Exception.Message -ceq 'No owned modal window observed in the bounded scan.'}
if(!$caught -or $script:Calls -ne 1 -or $e.Outcome -cne 'NoModalWindowObserved' -or $e.ModalWindowObserved -or !$target.DiagnosticContext.Closed){throw 'Negative modal outcome was fabricated or closure lost'}
$options|Add-Member NoteProperty DiagnosticZone 'global_cp'
$options.RunRoot=Join-Path $Root 'cp';$script:Calls=0;$script:Found=$true;$e.Attempted=$false;$e.Outcome='NotTriggered'
Invoke-ArenaLoadDiagnostic $target $state $logs $options $e
if($script:Calls -ne 0 -or $e.Attempted){throw 'MP log invoked the CP-only modal helper'}
$cpMarker='[ INFO ][ zonetool::iw7::load_zone ]: Loading zone "global_cp"...'
[IO.File]::WriteAllText((Join-Path $logs 'stdout.log'),$cpMarker+"`n")
$e.LastBytes=(Get-Item -LiteralPath (Join-Path $logs 'stdout.log')).Length;$e.LastProgressMs=0L
$caught=$false;try{Invoke-ArenaLoadDiagnostic $target $state $logs $options $e}catch{$caught=$_.Exception.Message -ceq 'Load diagnostic captured; material reference not measured.'}
if(!$caught -or $script:Calls -ne 1 -or $e.Outcome -cne 'Captured' -or !$target.DiagnosticContext.Closed){throw 'CP-only modal dispatch differs'}
$dummy=@{PackageRoot=$Root;RunRoot=$Root;StockBindingPlan='absent';StockBindingPlanSHA256=('1'*64);ToolSource=$Root;CandidateRoot=$Root;CandidateArtifactSHA256=('2'*64);NativeJobAssembly='absent.dll'}
$caught=$false;try{& $Measure @dummy -ModalTextOnly}catch{$caught=$_.Exception.Message -ceq 'Modal text requires the explicit load diagnostic opt-in.'}
if(!$caught){throw 'Modal path without diagnostic opt-in was not refused before file access'}
$caught=$false;try{& $Measure @dummy -LoadDiagnostic -ModalTextOnly -DiagnosticZone global_cp}catch{$caught=$_.Exception.Message -ceq 'The global_cp witness requires modal text-only diagnostic and the reviewed pack17 supplement.'}
if(!$caught){throw 'CP witness without required pack17 was not refused before file access'}
'''
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'modal-source.ps1';path.write_text(script,encoding='utf-8')
            result=subprocess.run([shutil.which('pwsh'),'-NoLogo','-NoProfile','-File',str(path),
                str(Path(model_lab.__file__).with_name('LoadDiagnostic.Core.ps1')),
                str(Path(model_lab.__file__).with_name('Measure-StockReference.ps1')),temp],
                capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    @unittest.skipUnless(shutil.which('pwsh'), 'PowerShell stock date source checks require pwsh')
    def test_stock_metadata_accepts_typed_and_short_dates_but_refuses_changed_ticks(self):
        # Evaluate the actual refusal predicate with authored metadata only.
        # No retail file, native type, reservation or process owner is consulted.
        script=r'''
param($Helper)
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Helper,[ref]$tokens,[ref]$errors)
$node=@($ast.FindAll({param($n);$n -is [Management.Automation.Language.IfStatementAst] -and $n.Extent.Text.Contains("throw 'Retained stock metadata changed.'")},$true))[0]
if(!$node){throw 'Exact stock metadata refusal predicate required'}
$check=[scriptblock]::Create($node.Extent.Text)
$time=[datetimeoffset]'2026-09-29T21:46:16.8069800Z'
$file=[pscustomobject]@{Length=77L;LastWriteTimeUtc=$time.UtcDateTime;Attributes=[IO.FileAttributes]::Archive}
$typed=(' {"ModifiedUtc":"2026-09-29T21:46:16.80698Z"}'|ConvertFrom-Json).ModifiedUtc
foreach($date in @('2026-09-29T21:46:16.8069800Z','2026-09-29T21:46:16.80698Z',$typed)){
    $entry=[pscustomobject]@{Bytes=77L;ModifiedUtc=$date;Attributes=32}
    & $check
}
foreach($kind in 'ticks','bytes','attributes'){
    $entry=[pscustomobject]@{Bytes=77L;ModifiedUtc=$time.AddTicks(1).ToString('o');Attributes=32}
    if($kind -ceq 'bytes'){$entry.ModifiedUtc=$time.ToString('o');$entry.Bytes=78L}
    if($kind -ceq 'attributes'){$entry.ModifiedUtc=$time.ToString('o');$entry.Attributes=33}
    $caught=$false;try{& $check}catch{$caught=$true}
    if(!$caught){throw 'Changed stock metadata was accepted'}
}
'''
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'stock-date.ps1';path.write_text(script,encoding='utf-8')
            result=subprocess.run([shutil.which('pwsh'),'-NoLogo','-NoProfile','-File',str(path),
                str(Path(model_lab.__file__).with_name('Measure-StockReference.ps1'))],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    @unittest.skipUnless(shutil.which('pwsh'), 'PowerShell admission source checks require pwsh')
    def test_writer_readback_stdout_path_is_canonical_before_strict_json_read(self):
        script=r'''
param($Writer,$Core,$Root)
$ErrorActionPreference='Stop'
. $Core
$dir=[IO.Path]::GetFullPath((Join-Path $Root 'check with space'))
[IO.Directory]::CreateDirectory($dir)|Out-Null
$file=Join-Path $dir 'stdout.log'
[IO.File]::WriteAllText($file,'{"schema":"iw7.original-arena-independent-readback/1","vertices":168,"triangles":84}',[Text.UTF8Encoding]::new($false))
$legacy='$checked=Read-H1SmallJson "$dir/stdout.log" 4KB'
$caught=$false;try{. ([scriptblock]::Create($legacy))}catch{$caught=$_.Exception.Message -ceq 'Canonical absolute path required.'}
if(!$caught){throw 'Old slash path was not refused by the real strict reader'}
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Writer,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Writer source parse failed'}
$read=@($ast.FindAll({param($node);$node -is [Management.Automation.Language.AssignmentStatementAst] -and $node.Left.Extent.Text -ceq '$checked'},$true))
if($read.Count -ne 1){throw 'One actual readback assignment required'}
. ([scriptblock]::Create($read[0].Extent.Text))
if($checked.schema -cne 'iw7.original-arena-independent-readback/1' -or $checked.vertices -ne 168 -or $checked.triangles -ne 84){throw 'Canonical assignment did not read the original JSON'}
# Keep path and size guards strict; do not normalize inside the generic reader.
$caught=$false;try{Read-H1SmallJson 'relative/stdout.log' 4KB}catch{$caught=$_.Exception.Message -ceq 'Canonical absolute path required.'}
if(!$caught){throw 'Relative path became accepted'}
[IO.File]::WriteAllText($file,('x'*4097),[Text.UTF8Encoding]::new($false))
$caught=$false;try{. ([scriptblock]::Create($read[0].Extent.Text))}catch{$caught=$_.Exception.Message -ceq 'JSON input exceeds bound.'}
if(!$caught){throw 'Bounded reader accepted oversized stdout'}
'''
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'canonical-check-path.ps1';path.write_text(script,encoding='utf-8')
            result=subprocess.run([shutil.which('pwsh'),'-NoLogo','-NoProfile','-File',str(path),
                str(Path(model_lab.__file__).with_name('Build-ArenaWriter.ps1')),
                str(arena.REPO/'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1'),temp],
                capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    @unittest.skipUnless(shutil.which('pwsh'), 'PowerShell admission source checks require pwsh')
    def test_world_opaque_qualification_is_deferred_to_existing_admission(self):
        script=r'''
param($Writer,$FF,$Root)
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$writerAst=[Management.Automation.Language.Parser]::ParseFile($Writer,[ref]$tokens,[ref]$errors)
$pin=@($writerAst.FindAll({param($node);$node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq 'Pin'},$true))[0]
. ([scriptblock]::Create($pin.Extent.Text))
$guards=[Collections.Generic.List[IDisposable]]::new();$entries=[Collections.Generic.List[object]]::new();$Run=$true
$fake=Join-Path $Root 'authored.exe';[IO.File]::WriteAllText($fake,'Authored changed binary')
try{$result=Pin $fake ('1'*64);if($result.SHA256 -cne ('1'*64)){throw 'Opaque bytes were hashed before admission'}}finally{foreach($guard in $guards){$guard.Dispose()}}
$commands=@($writerAst.FindAll({param($node);$node -is [Management.Automation.Language.CommandAst]},$true))
$lease=@($commands|Where-Object {$_.GetCommandName() -ceq 'Enter-IW7ResourceLease'})[0]
$hash=@($commands|Where-Object {$_.GetCommandName() -ceq 'Assert-BeaconHash'})[0]
if(!$lease -or !$hash -or $hash.Extent.StartOffset -le $lease.Extent.EndOffset){throw 'Writer opaque validation must follow existing admission'}
$ast=[Management.Automation.Language.Parser]::ParseFile($FF,[ref]$tokens,[ref]$errors)
$block=@($ast.FindAll({param($node);$node -is [Management.Automation.Language.IfStatementAst] -and $node.Clauses[0].Item1.Extent.Text.Trim() -ceq '$CandidateRoot'},$true))[0]
$arena=$true;$ToolProvenance='';$CandidateArtifactSHA256='1'*64;$NativeJobAssembly='absent-owner.dll'
$CandidateRoot=Join-Path $Root 'candidate';$repo=Join-Path $Root 'package'
[IO.Directory]::CreateDirectory((Join-Path $repo 'sdk/modding'))|Out-Null;[IO.Directory]::CreateDirectory($CandidateRoot)|Out-Null
[IO.File]::WriteAllText((Join-Path $repo 'sdk/modding/BeaconFF.Core.ps1'),'# Authored pure import')
$toolPath=Join-Path $CandidateRoot 'bin/zonetool-community.exe';$sha='e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04'
@{schema='iw7.zonetool-community-candidate/1';executable=@{path=$toolPath;sha256=$sha}}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $CandidateRoot 'build-artifact.local.json')
$script:Admitted=$false;$script:QualificationCalls=0
function Resolve-IW7BasePath($Root,$Relative){Join-Path $Root $Relative}
function Assert-BeaconHash($Path,$SHA){if(!(Split-Path $Path -Leaf).Equals('build-artifact.local.json')){throw 'Opaque pre-admission hash'}}
function Read-BeaconJson($Path,$Limit){Get-Content -LiteralPath $Path -Raw|ConvertFrom-Json}
function Assert-BeaconCandidate($Root,$Artifact){if(!$script:Admitted){throw 'Opaque candidate qualified without admission'};$script:QualificationCalls++;[pscustomobject]@{Path=$toolPath;SHA256=$sha}}
. ([scriptblock]::Create($block.Extent.Text))
if($script:QualificationCalls -ne 0 -or $tool -ine $toolPath){throw 'LIGHT metadata must not qualify candidate binary'}
$calls=@($ast.FindAll({param($node);$node -is [Management.Automation.Language.CommandAst] -and $node.GetCommandName() -ceq 'Assert-BeaconCandidate'},$true))
$lease=@($ast.FindAll({param($node);$node -is [Management.Automation.Language.CommandAst] -and $node.GetCommandName() -ceq 'Enter-IW7ResourceLease'},$true))[0]
$admittedCall=@($calls|Where-Object {$_.Extent.StartOffset -gt $lease.Extent.EndOffset})[0]
if(!$admittedCall){throw 'World FF qualifier must follow existing admission'}
$underLease=$admittedCall;while($underLease -and $underLease -isnot [Management.Automation.Language.IfStatementAst]){$underLease=$underLease.Parent}
$script:Admitted=$true;$state=@{}
. ([scriptblock]::Create($underLease.Extent.Text))
if($script:QualificationCalls -ne 1 -or !$state.CandidateQualifiedUnderLease){throw 'Admitted actual candidate validation missing'}
'''
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'admission-source.ps1';path.write_text(script,encoding='utf-8')
            result=subprocess.run([shutil.which('pwsh'),'-NoLogo','-NoProfile','-File',str(path),
                str(Path(model_lab.__file__).with_name('Build-ArenaWriter.ps1')),
                str(arena.REPO/'ops/model-lab/Build-ModelFF.ps1'),temp],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    @unittest.skipUnless(shutil.which('pwsh'), 'PowerShell LIGHT plan checks require pwsh')
    def test_writer_pin_matches_closed_reader_receipt_and_refuses_old_pin(self):
        script = r'''
param($Writer,$Root)
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Writer,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Writer source parse failed'}
$pin=@($ast.FindAll({param($node);$node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq 'Pin'},$true))[0]
. ([scriptblock]::Create($pin.Extent.Text))
$assignment=@($ast.FindAll({param($node);$node -is [Management.Automation.Language.AssignmentStatementAst] -and $node.Left.Extent.Text -ceq '$pythonPin'},$true))
if($assignment.Count -ne 1){throw 'One existing Python pin assignment required'}
$guards=[Collections.Generic.List[IDisposable]]::new();$entries=[Collections.Generic.List[object]]::new()
$python=Join-Path $Root 'authored-python.exe';[IO.File]::WriteAllText($python,'Authored source placeholder; not a tool')
# Historical closed M7D reader receipt, supplied as text, never a new opaque hash.
$closedReaderSHA='4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a'
$script:Admitted=$false;$script:Calls=0
function Assert-BeaconHash($Path,$Expected){
    if(!$script:Admitted){throw 'Opaque qualification before admission'}
    $script:Calls++
    if($Path -cne $python -or $Expected -cne $closedReaderSHA){throw 'Declared pin differs from historical reader receipt'}
}
try {
    # Actual source Pin defers known binary digests, including the stale one.
    $old=Pin $python '31073dad142bc7f3374e3122aa668270052c9ad37d0aaab803ae73f184c3a43b'
    . ([scriptblock]::Create($assignment[0].Extent.Text))
    if($script:Calls -ne 0){throw 'Planning qualified an opaque tool'}
    $script:Admitted=$true
    $refused=$false;try{Assert-BeaconHash $old.Path $old.SHA256}catch{$refused=$_.Exception.Message -ceq 'Declared pin differs from historical reader receipt'}
    if(!$refused){throw 'Stale writer pin was not refused'}
    Assert-BeaconHash $pythonPin.Path $pythonPin.SHA256
    if($script:Calls -ne 2){throw 'Expected stale failure and corrected match'}
} finally {foreach($guard in $guards){$guard.Dispose()}}
'''
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'writer-pin-source.ps1';path.write_text(script,encoding='utf-8')
            result=subprocess.run([shutil.which('pwsh'),'-NoLogo','-NoProfile','-File',str(path),
                str(Path(model_lab.__file__).with_name('Build-ArenaWriter.ps1')),temp],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    @unittest.skipUnless(shutil.which('pwsh'), 'PowerShell LIGHT plan checks require pwsh')
    def test_light_measurement_plan_binds_checker_and_local_imports(self):
        helper=Path(model_lab.__file__).with_name('Measure-StockReference.ps1')
        # Authored source/receipt placeholders only; default planning must never
        # inspect the nonexistent native candidate, stock or assembly below.
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);package=root/'package';tool=root/'tool'
            names=set(re.findall(r"'((?:ops|sdk|tools-source)/[^']+\.(?:ps1|py|cs))'",helper.read_text()))
            for name in names:
                path=package/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('Authored source '+name)
            (package/'ops/model-lab/prepare_writer.py').write_text("INTERFACES=['normal-a','normal-b','normal-c']\n")
            for name in ('normal-a','normal-b','normal-c'):
                path=tool/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('Authored normal proof')
            (package/'source-workspace.json').write_text(json.dumps({'revisions':{'iw7-mod-components':'2f9462db806bbd3ab51f9ecb2f3b25ae54ae10f1'}}))
            inputs=[{'Relative':f'main/source-{i}.ff','Source':str(root/f'absent-stock-{i}'),'Mode':'HardLink'} for i in range(71)]
            inputs.append({'Relative':'main/fileSysCheck.cfg','Source':str(root/'absent-sentinel'),'Mode':'Copy'})
            binding=root/'stock.json';binding.write_text(json.dumps({'stock_binding':{'inputs':inputs}}))
            args=[shutil.which('pwsh'),'-NoLogo','-NoProfile','-File',str(helper),'-PackageRoot',str(package),
                  '-RunRoot',str(package/'runtime/reference'),'-StockBindingPlan',str(binding),
                  '-StockBindingPlanSHA256',model_lab.digest(binding.read_bytes()),'-ToolSource',str(tool),
                  '-CandidateRoot',str(root/'absent-candidate'),'-CandidateArtifactSHA256','1'*64,
                  '-NativeJobAssembly',str(root/'absent-owner.dll')]
            def planned(*extra):
                result=subprocess.run(args+list(extra),capture_output=True,text=True,timeout=20)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                value=json.loads(result.stdout)
                self.assertFalse(value['StockBytesRead']);self.assertFalse(value['NativeTypesLoaded']);self.assertFalse(value['LeaseAcquired'])
                return value
            baseline=planned();prior=baseline['PlanSHA256']
            modal=planned('-LoadDiagnostic','-ModalTextOnly')
            self.assertEqual(modal['Plan']['Diagnostic']['Mode'], 'global-mp-modal-text')
            self.assertIsNone(modal['Plan']['Diagnostic']['Cdb'])
            self.assertEqual([modal['Plan']['Diagnostic'][name] for name in ('CPUSeconds','SnapshotSeconds','OfflineStackSeconds')], [0,0,0])
            for name in ('tools-source/asset-bridge/world/original-arena/modal_window.py',
                         'tools-source/asset-bridge/recipient/recipient_dialog.py'):
                self.assertIn(str(package/name), [pin['Path'] for pin in modal['Plan']['SourcePins']])
            for name in ('tools-source/asset-bridge/world/original-arena/model_lab.py',
                         'tools-source/asset-bridge/world/original-arena/readback.py',
                         'tools-source/asset-bridge/h1-fixture/inspect_fixture.py'):
                path=package/name
                self.assertIn(str(path),[pin['Path'] for pin in baseline['Plan']['SourcePins']])
                path.write_text(path.read_text()+'\nAuthored checker mutation')
                current=planned()['PlanSHA256'];self.assertNotEqual(current,prior);prior=current
            self.assertFalse((package/'runtime/reference').exists())

    @unittest.skipUnless(shutil.which('pwsh'), 'PowerShell source caller checks require pwsh')
    def test_original_job_caller_keeps_unknown_owner_and_accepts_telemetry_only(self):
        # Authored PowerShell mocks only: no native type/job, tool/game process,
        # retail content or resource reservation is used by this source check.
        script = r'''
param($Helper,$Root)
$ErrorActionPreference='Stop'
. $Helper
$script:Mode='pass';$script:Bytes=0L
function Measure-BeaconOutputFiles {return $script:Bytes}
function Get-IW7ResourceSnapshot {return [pscustomobject]@{Committed=99;CommitLimit=100}}
function Invoke-H1OwnedStage($Plan,$State,$Context,$Start,$SHA,$Logs){
    if($Start.WorkingDirectory -cne $Context.Work -or $Start.ArgumentList[0] -cne '-strict-content-sources'){throw 'Literal direct original tool start differs'}
    $Context.Closed=$false
    if($script:Mode -cne 'unknown'){
        $Context.Owner=[pscustomobject]@{Closed=$false;StopCalls=0}
        $Context.Owner|Add-Member ScriptMethod StopAndConfirm {param($Ms);if($Ms -ne 5000){throw 'Wrong original stop deadline'};$this.StopCalls++;$this.Closed=$true}
    }
    if($script:Mode -ceq 'diag-unknown'){$Context|Add-Member NoteProperty DiagnosticContext ([pscustomobject]@{Closed=$false})}
    if($script:Mode -cne 'pass'){throw 'Authored owner failure'}
    Test-H1Budget $Plan $State
    $State.Identity=[ordered]@{PID=1234;Image=$Start.FileName;CreatedUtc='2026-10-14T00:00:00Z'}
    $State.TreeClosureConfirmed=$true;$State.ExitCode=0;$Context.Closed=$true;$Context.Owner.Closed=$true
}
foreach($mode in 'pass','failed','unknown','diag-unknown'){
    $script:Mode=$mode;$work=Join-Path $Root $mode;[IO.Directory]::CreateDirectory($work)|Out-Null
    $context=[pscustomobject]@{Owner=$null;Closed=$true;Lease=[pscustomobject]@{Token='authored'};Work=$work}
    if($mode -ceq 'pass'){
        $result=Invoke-OriginalArenaTool $context (Join-Path $work 'authored.exe') ('1'*64) @('-strict-content-sources') $work $work probe @() 30
        if(!$result.JobClosed -or !$result.RootExited -or $result.ActiveProcesses -ne 0 -or !$context.Closed){throw 'Closed source witness differs'}
    }else{
        $caught=$false;try{$null=Invoke-OriginalArenaTool $context (Join-Path $work 'authored.exe') ('1'*64) @('-strict-content-sources') $work $work probe @() 30}catch{$caught=$true}
        if(!$caught){throw 'Failure was accepted'}
        if($mode -ceq 'failed' -and (!$context.Closed -or $context.Owner.StopCalls -ne 1)){throw 'Original owner cleanup differs'}
        if($mode -ceq 'unknown' -and ($context.Closed -or $context.Owner)){throw 'Unknown factory was treated as closed'}
        if($mode -ceq 'diag-unknown' -and ($context.Closed -or $context.Owner.StopCalls -ne 1 -or !$context.Owner.Closed)){throw 'Closed target falsely qualified unknown diagnostic job'}
    }
}
$work=Join-Path $Root 'reused';[IO.Directory]::CreateDirectory($work)|Out-Null
$context=[pscustomobject]@{Owner=$null;Closed=$true;Lease=[pscustomobject]@{Token='authored'};Work=$work}
$script:Mode='pass'
$null=Invoke-OriginalArenaTool $context (Join-Path $work 'authored.exe') ('1'*64) @('-strict-content-sources') $work $work first @() 30
$previous=$context.Owner
$script:Mode='unknown';$caught=$false
try{$null=Invoke-OriginalArenaTool $context (Join-Path $work 'authored.exe') ('1'*64) @('-strict-content-sources') $work $work second @() 30}catch{$caught=$true}
if(!$caught -or $context.Closed -or $context.Owner -or $previous.StopCalls -ne 0){throw 'Previous closed owner falsely qualified a new unknown factory'}
'''
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'source-caller.ps1';path.write_text(script,encoding='utf-8')
            result=subprocess.run([shutil.which('pwsh'),'-NoLogo','-NoProfile','-File',str(path),
                str(Path(model_lab.__file__).with_name('OriginalArena.Process.ps1')),temp],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def reference_fixture(self,root):
        tool,_,_,legacy=self.binding_fixture(root)
        measurement=root/'measurement';measurement.mkdir()
        request={'schema':'iw7.original-arena-reference-request/1','recipient':'cp_zmb',
                 'material':readback.MATERIAL,'input_csv':'requested.csv','output_csv':'world_material'}
        request_raw=model_lab.json_bytes(request)
        (measurement/'reference-request.json').write_bytes(request_raw)
        (measurement/'requested.csv').write_bytes(('material,'+readback.MATERIAL+'\n').encode())
        closure={'Schema':'iw7.original-arena-reference-process/1','ExitCode':0,'RootExited':True,
                 'ActiveProcesses':0,'JobClosed':True,'Restored':True,'StockPreserved':True,
                 'ImageSHA256':model_lab.REFERENCE_TOOL_SHA256,
                 'Identity':{'PID':1234,'Image':str(root/'fixture-tool.exe'),'CreatedUtc':'2026-10-14T00:00:00Z'},
                 'Arguments':['-headless','-unbuffered-io','-strict-content-sources','-enemy-reference-check',
                              'cp_zmb','requested.csv','world_material'],'RequestSHA256':model_lab.digest(request_raw)}
        plan={'Schema':'iw7.original-arena-reference-plan/1','Image':closure['Identity']['Image'],
              'ImageSHA256':model_lab.REFERENCE_TOOL_SHA256,'Arguments':closure['Arguments'],
              'RequestSHA256':closure['RequestSHA256'],'OriginalOwnerAssemblySHA256':model_lab.REFERENCE_OWNER_SHA256}
        plan_raw=model_lab.json_bytes(plan);(measurement/'reference-plan.json').write_bytes(plan_raw)
        closure['PlanSHA256']=model_lab.digest(plan_raw)
        outputs={'csv':('type,name,status\nmaterial,'+readback.MATERIAL+',verified\n').encode(),
                 'stdout':b'ENEMY_REFERENCE_CHECK map=cp_zmb rows=1 verified=1 missing=0 default=0 output=enemy-catalog/world_material.csv\n',
                 'closure':model_lab.json_bytes(closure)}
        snapshots={}
        for key,data in outputs.items():
            name='enemy-catalog/world_material.csv' if key=='csv' else key+('.json' if key=='closure' else '.txt')
            (measurement/name).parent.mkdir(exist_ok=True);(measurement/name).write_bytes(data)
            snapshots[key]={'path':name,'bytes':len(data),'sha256':model_lab.digest(data)}
        evidence={'schema':'iw7.original-arena-recipient-reference/1','source_pin':prepare_writer.PIN,
                  'recipient':'cp_zmb','material':readback.MATERIAL,'snapshot_only':True,
                  'runtime_verified':False,'material_payload_verified':False,
                  'reference_snapshot':snapshots,'normal_encoding_source':legacy['normal_encoding_source']}
        path=root/'reference.json';path.write_bytes(model_lab.json_bytes(evidence))
        return tool,measurement,path,evidence,closure

    def test_current_reference_binding_requires_nondefault_row_closed_job_and_exact_request(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);tool,measurement,path,evidence,closure=self.reference_fixture(root)
            self.assertEqual(model_lab.validate_reference_evidence(tool,path,measurement)[0],readback.MATERIAL)
            for kind in ('default','missing','extra','open','wrong-tool','wrong-request','identity',
                         'plan-digest','root-image','unrestored','stock-changed','marker-path','extra-marker'):
                altered=copy.deepcopy(evidence);changed=copy.deepcopy(closure)
                csv_path=measurement/evidence['reference_snapshot']['csv']['path']
                csv_original=csv_path.read_bytes()
                log_path=measurement/evidence['reference_snapshot']['stdout']['path'];log_original=log_path.read_bytes()
                if kind in ('default','missing','extra'):
                    data=(('type,name,status\nmaterial,'+readback.MATERIAL+','+kind+'\n') if kind!='extra'
                          else csv_original.decode()+'material,other,verified\n').encode()
                    csv_path.write_bytes(data)
                    altered['reference_snapshot']['csv'].update(bytes=len(data),sha256=model_lab.digest(data))
                elif kind in ('marker-path','extra-marker'):
                    data=(log_original.replace(b'world_material.csv',b'other.csv') if kind=='marker-path' else
                          log_original+b'ENEMY_REFERENCE_CHECK map=cp_rave rows=1 verified=1 missing=0 default=0 output=other.csv\n')
                    log_path.write_bytes(data)
                    altered['reference_snapshot']['stdout'].update(bytes=len(data),sha256=model_lab.digest(data))
                else:
                    if kind=='open':changed['ActiveProcesses']=1
                    if kind=='wrong-tool':changed['ImageSHA256']='0'*64
                    if kind=='wrong-request':changed['Arguments'][4]='cp_rave'
                    if kind=='identity':changed['Identity']['PID']=0
                    if kind=='plan-digest':changed['PlanSHA256']='1'*64
                    if kind=='root-image':changed['Identity']['Image']=str(root/'other.exe')
                    if kind=='unrestored':changed['Restored']=False
                    if kind=='stock-changed':changed['StockPreserved']=False
                    data=model_lab.json_bytes(changed);(measurement/'closure.json').write_bytes(data)
                    altered['reference_snapshot']['closure'].update(bytes=len(data),sha256=model_lab.digest(data))
                path.write_bytes(model_lab.json_bytes(altered))
                with self.subTest(kind=kind),self.assertRaises(ValueError):
                    model_lab.validate_reference_evidence(tool,path,measurement)
                csv_path.write_bytes(csv_original)
                log_path.write_bytes(log_original)
                (measurement/'closure.json').write_bytes(model_lab.json_bytes(closure))
            path.write_bytes(model_lab.json_bytes(evidence))
            hashes=prepare_writer.source_hashes(tool,check_pin=False)
            with patch.object(prepare,'source_hashes',return_value=hashes):
                prepare.prepare(root/'new-bound',tool_source=tool,recipient_evidence=path,stock_root=measurement)
            self.assertIn(readback.MATERIAL,(root/'new-bound/probe_geometry.hpp').read_text())

    def binding_fixture(self,root):
        tool,stock=root/'tool',root/'stock'
        for name in prepare_writer.INTERFACES:
            path=tool/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(('Original source fixture '+name).encode())
        snapshots={}
        for name in ('closure','load_log','material_json'):
            raw=('Original evidence fixture '+name).encode();path=stock/(name+'.txt')
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            snapshots[name]={'path':path.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        evidence={'schema':'iw7.model-recipient-evidence/1','source_pin':prepare_writer.PIN,'recipient':'cp_zmb',
                  'material':readback.MATERIAL,'snapshot_only':True,'runtime_verified':False,'material_snapshot':snapshots,
                  'normal_encoding_source':[{'path':name,'sha256':hashlib.sha256((tool/name).read_bytes()).hexdigest()}
                                            for name in prepare_writer.INTERFACES[-3:]]}
        path=root/'recipient.json';path.write_text(json.dumps(evidence))
        return tool,stock,path,evidence

    def prepare_fixture(self,root,**kwargs):
        tool,stock,evidence,_=self.binding_fixture(root)
        prepared=root/'prepared'
        # Test-authored interfaces/evidence; this bypass is scoped to this mock,
        # never a production CLI flag or a claim about live retail snapshots.
        hashes=prepare_writer.source_hashes(tool,check_pin=False)
        with patch.object(prepare,'source_hashes',return_value=hashes):
            prepare.prepare(prepared,tool_source=tool,recipient_evidence=evidence,stock_root=stock,**kwargs)
        geometry=json.loads((prepared/'geometry.source.json').read_bytes())
        artifacts=root/'artifacts'
        for name,raw in zip(model_lab.PAIR,synthetic_records(geometry,readback.MATERIAL)):
            path=artifacts/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        return prepared,artifacts

    def test_material_source_is_separate_from_unchanged_unbound_variant(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);prepared,_=self.prepare_fixture(root)
            manifest=json.loads((prepared/'arena-writer-source.json').read_bytes())
            self.assertEqual(manifest['selected_counts']['vertices'],168)
            self.assertFalse(manifest['compiled']);self.assertFalse(manifest['physics_serialized'])
            self.assertIn('model.lodInfo[0].partBits[0]=surf.partBits[0]',(prepared/'arena_writer.cpp').read_text())
            self.assertIn(json.dumps(readback.MATERIAL),(prepared/'probe_geometry.hpp').read_text())
            unbound=root/'unbound';prepare.prepare(unbound)
            self.assertEqual(len(list(unbound.iterdir())),7)
            self.assertNotIn(readback.MATERIAL,(unbound/'probe_geometry.hpp').read_text())
            for name in ('geometry.source.json','arena.source.json','route.reference.json'):
                self.assertEqual((prepared/name).read_bytes(),(unbound/name).read_bytes())
            with self.assertRaises(ValueError):prepare.prepare(root/'partial',recipient_evidence=root/'recipient.json')

    def test_first_box_sidecar_keeps_named_material_reference_unqualified(self):
        with tempfile.TemporaryDirectory() as temp:
            prepared,_ = self.prepare_fixture(Path(temp),first_box='obstacle')
            contract = json.loads((prepared/'first-box.source.json').read_bytes())
            self.assertEqual(contract['material_reference'], readback.MATERIAL)
            self.assertFalse(contract['material_payload_verified'])
            self.assertFalse(contract['rendered_bounds_verified'])
            manifest = json.loads((prepared/'arena-writer-source.json').read_bytes())
            self.assertEqual(set(manifest['source_files']), {'geometry.source.json', 'probe_geometry.hpp', 'arena_writer.cpp'})
            self.assertEqual(manifest['selected_counts']['vertices'], 168)

    def test_shared_recipient_validator_refuses_missing_changed_and_escape_proofs(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);tool,stock,path,evidence=self.binding_fixture(root)
            self.assertEqual(prepare_writer.validate_recipient_evidence(tool,path,stock)[0],readback.MATERIAL)
            for kind in ('empty','changed','escape','normal','runtime'):
                altered=copy.deepcopy(evidence)
                if kind=='empty':altered['material_snapshot']={}
                if kind=='changed':altered['material_snapshot']['closure']['sha256']='0'*64
                if kind=='escape':altered['material_snapshot']['closure']['path']='../recipient.json'
                if kind=='normal':altered['normal_encoding_source'].pop()
                if kind=='runtime':altered['runtime_verified']=True
                path.write_text(json.dumps(altered))
                with self.subTest(kind=kind),self.assertRaises(ValueError):
                    prepare_writer.validate_recipient_evidence(tool,path,stock)

    def test_five_payload_stage_uses_existing_zone_and_original_profile(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);prepared,artifacts=self.prepare_fixture(root)
            output=root/'stage';plan=model_lab.stage(artifacts,prepared,output)
            self.assertEqual(plan['geometry_profile'],model_lab.PROFILE)
            self.assertEqual(len(plan['source_files']),5);self.assertEqual(len(plan['validation_files']),8)
            self.assertEqual(model_lab.verify_stage(output)[0],plan)
            self.assertFalse(plan['native_provenance_verified']);self.assertFalse(plan['ready'])
            self.assertEqual((output/'zone_source/paris_model_probe.csv').read_bytes(),
                             model_lab.assets(model_lab.MODEL,model_lab.MESH)['zone_source/paris_model_probe.csv'])
            with self.assertRaises(ValueError):model_lab.stage(artifacts,prepared,output)
            isolated=subprocess.run([sys.executable,'-I','-S','-B',str(Path(model_lab.__file__)),'verify-stage',
                                      '--source',str(output)],capture_output=True,text=True,timeout=20)
            self.assertEqual(isolated.returncode,0,isolated.stderr)
            self.assertEqual(json.loads(isolated.stdout),plan)

    def test_shared_python_process_ignores_foreign_named_module_cache(self):
        with patch.dict(sys.modules,{'readback':object(),'prepare_writer':object(),'rigid_export':object(),'geometry':object()}):
            fresh=model_lab.local_module('_arena_test_foreign_cache',Path(model_lab.__file__))
            self.assertEqual(fresh.readback.MATERIAL,readback.MATERIAL)
            self.assertEqual(fresh.PIN,prepare_writer.PIN)

    def test_changed_prepared_and_every_consulted_staged_input_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);prepared,artifacts=self.prepare_fixture(root)
            output=root/'stage';plan=model_lab.stage(artifacts,prepared,output)
            header=prepared/'probe_geometry.hpp';header.write_bytes(header.read_bytes()+b'changed')
            with self.assertRaises(ValueError):model_lab.stage(artifacts,prepared,root/'bad-stage')
            for name in plan['validation_files']:
                path=output/name;original=path.read_bytes();path.write_bytes(original+b'x')
                try:
                    with self.subTest(name=name),self.assertRaises(ValueError):model_lab.verify_stage(output)
                finally:path.write_bytes(original)

    def test_redump_packed_stream_corruption_refused_and_pointer_relocation_allowed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);prepared,artifacts=self.prepare_fixture(root)
            output=root/'stage';model_lab.stage(artifacts,prepared,output)
            ff=root/'fixture.ff';ff.write_bytes(b'Original test fixture; not a native fastfile')
            proof=model_lab.verify_dump(output,artifacts,ff)
            self.assertEqual(proof['schema'],'iw7.model-original-arena-roundtrip/1')
            self.assertTrue(proof['packed_attributes_byte_identical']);self.assertFalse(proof['runtime_verified'])
            model_path=artifacts/model_lab.PAIR[0];model=model_path.read_bytes()
            changed=bytearray(model);changed[6+240]^=1;model_path.write_bytes(changed)
            with self.assertRaisesRegex(ValueError,'root part bits'):model_lab.verify_dump(output,artifacts,ff)
            model_path.write_bytes(model)
            mesh_path=artifacts/model_lab.PAIR[1];mesh=mesh_path.read_bytes()
            p=6+56+2+len(model_lab.MESH)+1+6+256+6
            for offset in (12,28):
                changed=bytearray(mesh);changed[p+offset]^=1;mesh_path.write_bytes(changed)
                with self.assertRaises(ValueError):model_lab.verify_dump(output,artifacts,ff)
            mesh_path.write_bytes(mesh)
            model_path=artifacts/model_lab.PAIR[0];model=model_path.read_bytes()
            token=b'\x08\x01'+struct.pack('<IQ',1,1)+b'\x07\x01'+readback.MATERIAL.encode()
            replacement=b'\x08\x01'+struct.pack('<IQ',1,1234)+b'\x07\x01'+readback.MATERIAL.encode()
            self.assertEqual(model.count(token),1);model_path.write_bytes(model.replace(token,replacement))
            self.assertTrue(model_lab.verify_dump(output,artifacts,ff)['geometry_roundtrip_verified'])

    @unittest.skipUnless(shutil.which('pwsh'),'PowerShell source dispatch check unavailable')
    def test_modelf_five_asset_dispatch_inventory_and_parser(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);prepared,artifacts=self.prepare_fixture(root)
            output=root/'stage';plan=model_lab.stage(artifacts,prepared,output)
            core=str(arena.REPO/'ops/model-lab/ModelFF.Core.ps1').replace("'","''")
            builder=str(arena.REPO/'ops/model-lab/Build-ModelFF.ps1').replace("'","''")
            source=str(output/'model-ff-plan.json').replace("'","''")
            script=root/'source-test.ps1'
            script.write_text("$ErrorActionPreference='Stop'\n. '"+core+"'\n"+
                "$p=Get-Content -Raw -LiteralPath '"+source+"'|ConvertFrom-Json\n"+
                "$names=@(Get-ModelFFSourceNames $p)\n"+
                "if($names.Count -ne 5 -or $names[0] -cne 'xmodel/paris_original_arena.xmb'){throw 'Arena dispatch'}\n"+
                "if(@(Get-ModelFFSourceNames ([pscustomobject]@{}))[0] -cne 'xmodel/paris_model_probe.xmb'){throw 'Cube dispatch'}\n"+
                "$p.geometry_profile='t7-iw7-resident-static-v1';$null=Get-ModelFFSourceNames $p\n"+
                "$p.geometry_profile='iw7-original-arena-rigid-v1';$p.selected_counts.vertices=$true\n"+
                "$refused=$false;try{$null=Get-ModelFFSourceNames $p}catch{$refused=$true};if(!$refused){throw 'Boolean count accepted'}\n"+
                "$tokens=$null;$errors=$null;$null=[Management.Automation.Language.Parser]::ParseFile('"+builder+"',[ref]$tokens,[ref]$errors)\n"+
                "if($errors.Count){throw ($errors|Out-String)}\n")
            result=subprocess.run([shutil.which('pwsh'),'-NoProfile','-File',str(script)],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)


class ModalWindowTests(unittest.TestCase):
    class API:
        def __init__(self):
            self.helper = dict(pid=44, parent_pid=7, created_filetime=300, image=r'C:\python.exe')
            self.target = dict(pid=9, parent_pid=7, created_filetime=200, image=r'C:\work\zonetool.exe')
            self.owners = {10:9, 20:9, 21:9}
            self.classes = {10:'#32770', 20:'Static', 21:'Button'}
            self.title = 'Engine notice'
            self.controls = [20, 21]
            self.texts = {20:'Authored error fixture.'}
            self.reads = []; self.enumerations = 0; self.hook = None

        def current_handle(self): return 1
        def identity(self, handle): return dict(self.helper if handle == 1 else self.target)
        def window_owner(self, hwnd): return self.owners[hwnd]
        def windows(self, pid): self.enumerations += 1; return [10]
        def class_name(self, hwnd): return self.classes[hwnd]
        def caption(self, hwnd): return self.title
        def children(self, hwnd): return list(self.controls)
        def is_child(self, root, child): return root == 10 and child in self.controls
        def static_text(self, hwnd):
            self.reads.append(hwnd)
            if self.hook: self.hook(hwnd)
            value = self.texts[hwnd]
            if isinstance(value, BaseException): raise value
            return value, False

    def setUp(self):
        self.api = self.API()
        self.expected = dict(self.api.target, sha256='expected')

    def snapshot(self, digest=lambda path:'expected', clock=lambda:0):
        return modal_window.capture(self.api, 2, self.expected, digest, clock)

    def test_any_owned_dialog_caption_and_only_static_text(self):
        record = self.snapshot()
        self.assertTrue(record['identity_verified_after'])
        self.assertTrue(record['modal_window_observed'])
        self.assertEqual(record['title'], 'Engine notice')
        self.assertEqual(record['controls'][0]['text'], 'Authored error fixture.')
        self.assertEqual(self.api.reads, [20])
        self.assertFalse(record['interaction_performed'])

    def test_original_creation_parent_and_image_refuse_before_window_enumeration(self):
        for field, value in [('pid',99), ('parent_pid',8), ('created_filetime',201), ('image',r'C:\other.exe')]:
            with self.subTest(field=field):
                self.api = self.API(); self.api.target[field] = value
                with self.assertRaises(OSError): self.snapshot()
                self.assertEqual(self.api.enumerations, 0)
        self.api = self.API(); self.api.helper['parent_pid'] = 8
        with self.assertRaises(OSError): self.snapshot()

    def test_root_reassignment_and_hash_failure_discard_text(self):
        self.api.owners[10] = 99
        record = self.snapshot()
        self.assertFalse(record['identity_verified_after']); self.assertEqual(self.api.reads, [])
        self.api = self.API(); record = self.snapshot(digest=lambda path:'bad')
        self.assertFalse(record['identity_verified_after']); self.assertEqual(self.api.enumerations, 0)

    def test_child_reassignment_after_read_discards_all_attribution(self):
        self.api.hook = lambda hwnd:self.api.owners.update({hwnd:99})
        record = self.snapshot()
        self.assertFalse(record['identity_verified_after'])
        self.assertEqual((record['title'], record['controls'], record['text_bytes']), (None, [], 0))

    def test_no_dialog_is_an_observed_negative_with_no_control_read(self):
        self.api.classes[10] = 'ConsoleWindowClass'
        record = self.snapshot()
        self.assertTrue(record['identity_verified_after']); self.assertFalse(record['modal_window_observed'])
        self.assertEqual(self.api.reads, [])

    def test_timeout_keeps_owned_caption_and_marks_missing_body(self):
        self.api.texts[20] = OSError('WM_GETTEXT timeout')
        record = self.snapshot()
        self.assertTrue(record['identity_verified_after']); self.assertTrue(record['modal_window_observed'])
        self.assertEqual(record['controls'][0]['text'], '')
        self.assertIn('timeout', record['controls'][0]['error'])

    def test_caption_buffer_saturation_marks_truncation(self):
        self.api.title = 'x' * 511
        record = self.snapshot()
        self.assertTrue(record['identity_verified_after'])
        self.assertTrue(record['caption_buffer_saturated']); self.assertTrue(record['text_truncated'])

    def test_control_and_utf8_bounds_and_soft_deadline(self):
        self.api.controls = list(range(20,50))
        for hwnd in self.api.controls:
            self.api.owners[hwnd] = 9; self.api.classes[hwnd] = 'Static'; self.api.texts[hwnd] = '😀'*3000
        record = self.snapshot()
        self.assertLessEqual(len(self.api.reads), 8); self.assertLessEqual(record['text_bytes'], 16*1024)
        self.assertTrue(record['text_truncated'])
        self.api = self.API(); ticks = iter([0,3])
        record = self.snapshot(clock=lambda:next(ticks))
        self.assertEqual(self.api.reads, []); self.assertTrue(record['text_truncated'])

    def test_changed_caption_and_final_hash_discard_snapshot(self):
        self.api.hook = lambda hwnd:setattr(self.api, 'title', 'Changed')
        self.assertFalse(self.snapshot()['identity_verified_after'])
        self.api = self.API(); hashes = iter(['expected','bad'])
        record = self.snapshot(digest=lambda path:next(hashes))
        self.assertFalse(record['identity_verified_after']); self.assertEqual(record['controls'], [])


if __name__ == '__main__':
    unittest.main()

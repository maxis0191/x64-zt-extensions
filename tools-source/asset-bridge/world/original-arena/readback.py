"""Independent bounded record/geometry check of the original arena XMB/XSB.

Does not import the arena generator or native serializer. Reuses only the
existing typed-record cursor; shader compatibility and physics are not inferred.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct

BASE = Path(__file__).resolve().parents[2] / 'h1-fixture/inspect_fixture.py'
spec = importlib.util.spec_from_file_location('_arena_record_reader', BASE)
records = importlib.util.module_from_spec(spec)
spec.loader.exec_module(records)
Reader, check, values = records.Reader, records.check, records.values
MATERIAL = 'mopw/character_park_clown_zombie_shoes'


def bounded(path, maximum):
    with Path(path).open('rb') as stream:
        raw = stream.read(maximum+1)
    check(0 < len(raw) <= maximum, 'Arena input exceeds bound')
    return raw


def f32(value):
    """Match assignment of the generated decimal literal to a C++ float."""
    check(type(value) in (int, float) and math.isfinite(value), 'Finite expected float required')
    try:
        result, = struct.unpack('<f', struct.pack('<f', value))
    except (OverflowError, struct.error):
        check(False, 'Expected value outside float32 range')
    check(math.isfinite(result), 'Expected float32 overflow')
    return result


def inspect(model, mesh, source, *, expected_material=None):
    check(expected_material is None or expected_material == MATERIAL, 'Explicit reviewed recipient material required')
    check(source.get('schema') == 'iw7.original-mesh-source/1' and source.get('name') == 'paris_original_arena', 'Original arena identity')
    check(len(source['surfaces']) == 1 and source['surfaces'][0]['material_reference'] is None, 'One material-unbound surface required')
    vertices, triangles = source['surfaces'][0]['vertices'], source['surfaces'][0]['triangles']
    check(24 <= len(vertices) <= 192 and len(vertices) % 24 == 0 and len(triangles) == len(vertices)//2, 'Original box geometry counts')
    midpoint, half = source['bounds']['midpoint'], source['bounds']['half_size']
    check(len(midpoint) == len(half) == 3 and all(type(v) in (int,float) and math.isfinite(v) for v in midpoint+half), 'Finite bounds')
    radius_squared = max(sum(v*v for v in item['position']) for item in vertices)
    bounds_f32 = tuple(f32(v) for v in midpoint+half)
    radius_squared_f32 = f32(radius_squared)
    # Header emits probe_radius_squared as float; std::sqrt(float) then stores
    # its float result in XModel.radius. Do not square that rounded radius and
    # compare it to the original double sum, or tolerate unrelated large error.
    radius_f32 = f32(math.sqrt(radius_squared_f32))
    m = Reader(model); header = m.array('model', 736, 1)
    check(tuple(header[8:15]) == (0,1,0,1,255,6,1), 'Rigid model LOD/shadow/collision metadata')
    check(values(header, 20, '3B') == (1,1,0) and values(header, 24, 'HH') == (0,1), 'One rigid root and surface')
    check(values(header, 28, 'f') == (1.0,), 'Model scale')
    check(values(header, 44, '6f') == bounds_f32, 'Authored model bounds')
    check(values(header,40,'f') == (radius_f32,), 'Authored radius')
    check(values(header,224,'fHH') == (1000000.0,1,0), 'LOD contract')
    m.name('model_name',6,'paris_original_arena');m.name('root',6,'tag_origin')
    for label,stride in (('parents',1),('angles',8),('positions',12)):
        m.array(label,stride,0)
    check(m.array('classification',1,1) == bytes(1), 'Root classification')
    check(values(m.array('base',32,1),0,'8f') == (0,0,0,1,0,0,0,2), 'Identity root transform')
    for label,stride in (('reactive',16),('reactive_tweaks',16),('coll_surfs',36)):
        m.array(label,stride,0)
    bone = values(m.array('bone',28,1),0,'7f')
    check(bone == bounds_f32+(radius_squared_f32,), 'Authored bone bounds')
    check(m.array('mip',2,1) == bytes(2), 'Mip metadata')
    handle = m.array('material_handles',8,1)
    check((handle != bytes(8)) == (expected_material is not None), 'Material handle presence differs')
    m.name('material',7,expected_material);m.name('lod0',7,'paris_original_arena_lod0')
    for i in range(1,6):m.name('lod'+str(i),7,None)
    for name in ('physics_asset','physics_fx','scriptable','procedural'):
        m.name(name,7,None)
    for name in ('unknown03','unknown_vec3','unknown04'):m.array(name,1,0)
    m.finish()
    s = Reader(mesh);group=s.array('group',56,1)
    check(values(group,16,'H') == (1,), 'One surface group')
    s.name('mesh_name',6,'paris_original_arena_lod0')
    h=s.array('surface',256,1)
    check(values(h,0,'3H2B') == (0x82,len(vertices),len(triangles),1,0), 'Surface counts/flags')
    check(values(group,20,'8I') == values(h,224,'8I') == (0x80000000,0,0,0,0,0,0,0), 'Rigid root part bits')
    packed=s.array('vertices',32,len(vertices))
    for i,v in enumerate(vertices):
        check(all(type(n) in (int,float) and math.isfinite(n) for n in v['position']+v['normal']+v['uv']), 'Finite source vertex')
        check(values(packed,32*i,'3f') == tuple(f32(component) for component in v['position']), 'Vertex position differs')
        check(values(packed,32*i+20,'2e') == tuple(v['uv']), 'Vertex UV differs')
        check(values(packed,32*i+16,'I') == (0xffffffff,), 'Original white color')
        normal,=values(packed,32*i+24,'I')
        decoded=[2*((normal>>(10*j))&1023)/1023-1 for j in range(3)]
        check(all(abs(a-b) <= 1/1023+1e-8 for a,b in zip(decoded,v['normal'])), 'Packed normal candidate differs')
    faces=s.array('triangles',6,len(triangles))
    for actual,expected in zip(struct.iter_unpack('<3H',faces),triangles):
        check(actual == tuple(expected) and len(set(actual)) == 3 and max(actual) < len(vertices), 'Triangle differs or invalid')
    rigid=s.array('rigid',16,1)
    check(values(rigid,0,'4HQ') == (0,len(vertices),0,len(triangles),0), 'Rigid coverage or unexpected collision tree')
    for name in ('blend','lmap','tension','tension_accum'):s.absent_raw(name)
    s.finish()
    return {'schema':'iw7.original-arena-independent-readback/1','vertices':len(vertices),'triangles':len(triangles),
            'model_bytes':len(model),'mesh_bytes':len(mesh),'geometry_roundtrip_verified':True,
            'material_bound':expected_material is not None,'material_reference':expected_material,
            'packed_streams_sha256':{key:hashlib.sha256(raw).hexdigest() for key,raw in
                                     (('vertices',packed),('triangles',faces),('rigid',rigid))},
            'physics_serialized':False,'runtime_verified':False}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts',required=True,type=Path)
    parser.add_argument('--geometry-source',required=True,type=Path)
    parser.add_argument('--expected-material',choices=[MATERIAL])
    args=parser.parse_args()
    source=json.loads(bounded(args.geometry_source,128*1024),parse_constant=lambda v:check(False,'Nonfinite source constant'))
    print(json.dumps(inspect(bounded(args.artifacts/'xmodel/paris_original_arena.xmb',8192),
                             bounded(args.artifacts/'xsurface/paris_original_arena_lod0.xsb',8192),source,
                             expected_material=args.expected_material),indent=2))

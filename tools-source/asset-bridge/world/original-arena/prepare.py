"""Prepare original arena/header and adapt the existing model writer in fresh scratch."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct

from arena import NAME, REPO, geometry, goal_trigger, original_scene, parse, route_check, validate
_spec = importlib.util.spec_from_file_location('_arena_writer_contract',REPO/'ops/model-lab/prepare_writer.py')
_contract = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_contract)
safe_path,source_hashes,validate_recipient_evidence,PIN = (_contract.safe_path,_contract.source_hashes,
                                                          _contract.validate_recipient_evidence,_contract.PIN)
MATERIAL = 'mopw/character_park_clown_zombie_shoes'


def literal(value):
    # Round to the actual declared C++ type first. Formatting an unrounded
    # double midpoint can move a float32 halfway value to the wrong side.
    value, = struct.unpack('<f', struct.pack('<f', value))
    text = f'{value:.9g}'
    return text+('.0' if '.' not in text and 'e' not in text.lower() else '')+'f'


def header(mesh, material=None):
    if material is not None and material != MATERIAL:
        raise ValueError('Material binding requires its separately verified recipient contract')
    surface = mesh['surfaces'][0]
    rows = []
    for i, vertex in enumerate(surface['vertices']):
        a, b = surface['vertices'][(i//4)*4:(i//4)*4+2]
        edge = [y-x for x,y in zip(a['position'], b['position'])]
        length = math.sqrt(sum(v*v for v in edge))
        tangent = [v/length for v in edge]
        values = vertex['position']+vertex['normal']+vertex['uv']+tangent
        rows.append('    {'+', '.join(literal(v) for v in values)+'}')
    triangles = ['    {'+', '.join(map(str, t))+'}' for t in surface['triangles']]
    midpoint, half = mesh['bounds']['midpoint'], mesh['bounds']['half_size']
    radius_squared = max(sum(v*v for v in item['position']) for item in surface['vertices'])
    array = lambda name, values: 'inline constexpr float '+name+'[3] = {'+', '.join(literal(v) for v in values)+'};\n'
    declaration = json.dumps(material) if material is not None else 'nullptr'
    return ('#pragma once\ninline constexpr const char* probe_material_name = '+declaration+';\n'
            'struct ProbeVertex { float xyz[3], normal[3], uv[2], tangent[3]; };\n'
            f'inline constexpr unsigned probe_vertex_count = {len(rows)};\n'
            f'inline constexpr unsigned probe_triangle_count = {len(triangles)};\n'
            +array('probe_bounds_mid', midpoint)+array('probe_bounds_half', half)
            +f'inline constexpr float probe_radius_squared = {literal(radius_squared)};\n'
            +'inline constexpr ProbeVertex probe_vertices[probe_vertex_count] = {\n'+',\n'.join(rows)+'\n};\n'
            +'inline constexpr unsigned short probe_triangles[probe_triangle_count][3] = {\n'+',\n'.join(triangles)+'\n};\n')


def adapt_writer(source, *, material=None):
    """Narrow adaptation, not a second serializer implementation."""
    replacements = {
        'd.dump_array(s.verts0.packedVerts0,24);d.dump_array(s.triIndices,12);':
            'd.dump_array(s.verts0.packedVerts0,probe_vertex_count);d.dump_array(s.triIndices,probe_triangle_count);',
        's.vertCount==24 && s.triCount==12': 's.vertCount==probe_vertex_count && s.triCount==probe_triangle_count',
        'GfxPackedVertex vertices[24]{};Face triangles[12]{};':
            'GfxPackedVertex vertices[probe_vertex_count]{};Face triangles[probe_triangle_count]{};',
        'for(unsigned i=0;i<24;i++)': 'for(unsigned i=0;i<probe_vertex_count;i++)',
        'for(unsigned i=0;i<12;i++)': 'for(unsigned i=0;i<probe_triangle_count;i++)',
        'rigid.vertCount=24;rigid.triCount=12;': 'rigid.vertCount=probe_vertex_count;rigid.triCount=probe_triangle_count;',
        'surf.vertCount=24;surf.triCount=12;': 'surf.vertCount=probe_vertex_count;surf.triCount=probe_triangle_count;',
        'for(float& f:info.bounds.halfSize)f=8;info.radiusSquared=192;':
            'memcpy(info.bounds.midPoint,probe_bounds_mid,sizeof(probe_bounds_mid));memcpy(info.bounds.halfSize,probe_bounds_half,sizeof(probe_bounds_half));info.radiusSquared=probe_radius_squared;',
        'model.radius=std::sqrt(192.0f);for(float& f:model.bounds.halfSize)f=8;':
            'model.radius=std::sqrt(probe_radius_squared);memcpy(model.bounds.midPoint,probe_bounds_mid,sizeof(probe_bounds_mid));memcpy(model.bounds.halfSize,probe_bounds_half,sizeof(probe_bounds_half));',
    }
    for old, new in replacements.items():
        if source.count(old) != 1:
            raise ValueError('Existing writer seam changed: '+old)
        source = source.replace(old, new)
    lines = source.splitlines()
    reports = [i for i,line in enumerate(lines) if 'std::cout<<' in line]
    if len(reports) != 1:
        raise ValueError('Exactly one existing writer report required')
    suffix = ',"geometry_roundtrip_verified":true,"physics_serialized":false,"ff_built":false,"runtime_verified":false'
    if material is not None:
        if material != MATERIAL:
            raise ValueError('Explicit reviewed recipient material required')
        suffix += ',"material_reference":'+json.dumps(material)+',"bones":1,"surfaces":1,"lods":1'
    lines[reports[0]] = ('    std::cout << '+json.dumps('{"schema":"iw7.original-arena-roundtrip/1","vertices":')
                         +' << probe_vertex_count << '+json.dumps(',"triangles":')
                         +' << probe_triangle_count << '+json.dumps(suffix+'}\n')+';')
    source = '\n'.join(lines)+'\n'
    if 'paris_model_probe' not in source:
        raise ValueError('Existing model writer identity changed')
    return source.replace('paris_model_probe', NAME)


def prepare(output, scene_path=None, *, tool_source=None, recipient_evidence=None, stock_root=None):
    output = safe_path(output)
    if output.exists():
        raise ValueError('Fresh output directory required')
    material, evidence_hash, tool_hashes = None, None, None
    if any(value is not None for value in (tool_source, recipient_evidence, stock_root)):
        if any(value is None for value in (tool_source, recipient_evidence, stock_root)):
            raise ValueError('Material binding requires source, recipient evidence and stock snapshot together')
        tool_hashes = source_hashes(tool_source)
        with safe_path(recipient_evidence).open('rb') as stream:
            evidence_data = stream.read(1024**2+1)
        if not 0 < len(evidence_data) <= 1024**2:
            raise ValueError('Bounded recipient evidence required')
        evidence_header = json.loads(evidence_data)
        if evidence_header.get('schema') == 'iw7.original-arena-recipient-reference/1':
            ref_spec=importlib.util.spec_from_file_location('_arena_reference_binding',Path(__file__).with_name('model_lab.py'))
            ref_module=importlib.util.module_from_spec(ref_spec);ref_spec.loader.exec_module(ref_module)
            material,evidence_hash=ref_module.validate_reference_evidence(tool_source,recipient_evidence,stock_root)
        else:
            material, evidence_hash = validate_recipient_evidence(tool_source, recipient_evidence, stock_root)
    if scene_path is None:
        source = original_scene()
    else:
        with safe_path(scene_path).open('rb') as stream:
            source = parse(stream.read(1024*1024+1))
    scene = validate(source)
    mesh = geometry(scene)
    trigger, converted = goal_trigger(scene)
    route = route_check(scene)
    if not route['clear'] or not route['goal_reached']:
        raise ValueError('Authored route is blocked or misses the goal')
    base = REPO / 'ops/model-lab/writer.cpp'
    base_bytes = base.read_bytes()
    writer = adapt_writer(base_bytes.decode().replace('\r\n', '\n'), material=material)
    payloads = {'arena.source.json': scene, 'geometry.source.json': mesh, 'goal-trigger.h1.json': trigger,
                'goal-trigger.iw7.json': converted, 'route.reference.json': route}
    output.mkdir(parents=True)
    for name, value in payloads.items():
        with (output/name).open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write('\n')
    for name, value in (('probe_geometry.hpp', header(mesh, material)), ('arena_writer.cpp', writer)):
        with (output/name).open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(value)
    if material is not None:
        manifest = {'schema':'iw7.original-arena-writer-source/1','source_pin':PIN,
                    'model_name':NAME,'mesh_name':NAME+'_lod0','material_reference':material,
                    'selected_counts':{'bones':1,'roots':1,'surfaces':1,
                                       'vertices':len(mesh['surfaces'][0]['vertices']),
                                       'triangles':len(mesh['surfaces'][0]['triangles'])},
                    'source_hashes':tool_hashes,'recipient_evidence_sha256':evidence_hash,
                    'source_files':{name:hashlib.sha256((output/name).read_bytes()).hexdigest() for name in
                                    ('geometry.source.json','probe_geometry.hpp','arena_writer.cpp')},
                    'lod0_dist':1000000,'has_lods':True,'shadow_cutoff_lod':6,'collision_lod':255,
                    'compiled':False,'ff_built':False,'runtime_verified':False,'physics_serialized':False}
        with (output/'arena-writer-source.json').open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(manifest,stream,indent=2,allow_nan=False);stream.write('\n')
    return {'name': NAME, 'solids': len(scene['solids']), 'vertices': len(mesh['surfaces'][0]['vertices']),
            'triangles': len(mesh['surfaces'][0]['triangles']), 'existing_writer_sha256': hashlib.sha256(base_bytes).hexdigest(),
            'geometry_source_bytes': (output/'geometry.source.json').stat().st_size, 'prepared_files': len(list(output.iterdir())),
            'native_compiled': False, 'ff_built': False, 'native_collision_verified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--scene', type=Path)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--recipient-evidence', type=Path)
    parser.add_argument('--stock-root', type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.output, args.scene,tool_source=args.source,
                             recipient_evidence=args.recipient_evidence,stock_root=args.stock_root), indent=2))

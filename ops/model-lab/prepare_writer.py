"""Prepare existing rigid-writer source from original geometry; never compile/run."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import os
_spec=importlib.util.spec_from_file_location('_model_writer_original_cube',Path(__file__).with_name('geometry.py'))
_geometry=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_geometry)
original_cube,validate=_geometry.original_cube,_geometry.validate
validate_authored,AUTHORED_PROFILE=_geometry.validate_authored,_geometry.AUTHORED_PROFILE

PIN = 'fab935826c898806855376662a8a03317b3ad8f1'
SHADOW_SENTINEL_SOURCE = 'src/zonetool/zonetool/h1/converter/iw7/assets/xmodel.cpp'
INTERFACES = [
    'src/zonetool/zonetool/utils/io/assetmanager.hpp',
    'src/zonetool/zonetool/utils/io/filesystem.hpp',
    'src/zonetool/zonetool/utils/memory.hpp',
    'src/zonetool/zonetool/iw7/structs.hpp',
    'src/zonetool/zonetool/iw7/assets/xmodel.cpp',
    'src/zonetool/zonetool/iw7/assets/xsurface.cpp',
    SHADOW_SENTINEL_SOURCE,
    'src/zonetool/game/shared.cpp',
    'src/zonetool/zonetool/h1/converter/iw7/assets/xsurface.cpp',
    'src/zonetool/zonetool/iw7/converter/h1/assets/xsurface.cpp',
]

def safe_path(path):
    path = Path(path).absolute()
    for ancestor in [path, *path.parents]:
        if ancestor.is_symlink() or (hasattr(ancestor, 'is_junction') and ancestor.is_junction()):
            raise ValueError('Linked output/source ancestry refused')
    return Path(os.path.abspath(path))

def header(data, material=None):
    validate(data)
    surf = data['surfaces'][0]
    rows = []
    for i, vertex in enumerate(surf['vertices']):
        first, second = surf['vertices'][(i//4)*4:(i//4)*4+2]
        tangent = [(b-a)/16 for a,b in zip(first['position'],second['position'])]
        values = vertex['position'] + vertex['normal'] + vertex['uv'] + tangent
        rows.append('    {' + ', '.join(f'{float(v):.1f}f' for v in values) + '}')
    triangles = ['    {'+', '.join(map(str,t))+'}' for t in surf['triangles']]
    material_decl='inline constexpr const char* probe_material_name = '+(json.dumps(material) if material else 'nullptr')+';\n'
    return material_decl+'#pragma once\nstruct ProbeVertex { float xyz[3], normal[3], uv[2], tangent[3]; };\ninline constexpr ProbeVertex probe_vertices[24] = {\n'+',\n'.join(rows)+'\n};\ninline constexpr unsigned short probe_triangles[12][3] = {\n'+',\n'.join(triangles)+'\n};\n'

def source_hashes(source, *, check_pin=True):
    """Existing pinned source validation shared by small original writers."""
    source = safe_path(source)
    if check_pin:
        head = subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'], text=True).strip()
        if head != PIN:
            raise ValueError('Exact ZoneTool source pin required')
        if subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=all'],text=True).strip():
            raise ValueError('Preserve changed ZoneTool checkout')
    hashes={}
    for name in INTERFACES:
        p=safe_path(source/name)
        hashes[name]=hashlib.sha256(p.read_bytes()).hexdigest()
    return hashes


def validate_recipient_evidence(source, recipient_evidence, stock_root):
    """Reuse the cube's measured reference checks without emitting another cube."""
    source = safe_path(source)
    with safe_path(recipient_evidence).open('rb') as stream:
        evidence_bytes=stream.read(1024**2+1)
    if not 0 < len(evidence_bytes) <= 1024**2:
        raise ValueError('Bounded recipient evidence required')
    evidence=json.loads(evidence_bytes)
    if (evidence.get('schema')!='iw7.model-recipient-evidence/1' or evidence.get('source_pin')!=PIN or
        evidence.get('recipient')!='cp_zmb' or evidence.get('material')!='mopw/character_park_clown_zombie_shoes' or
        evidence.get('snapshot_only') is not True or evidence.get('runtime_verified') is not False):
        raise ValueError('Exact measured recipient reference required, gameplay remains pending')
    if stock_root is None:
        raise ValueError('Measured stock snapshot must be rechecked before binding the material')
    stock=safe_path(stock_root)
    if set(evidence.get('material_snapshot',{})) != {'closure','load_log','material_json'}:
        raise ValueError('Complete measured recipient snapshot required')
    for key,ref in evidence['material_snapshot'].items():
        path=safe_path(stock/ref['path'])
        if (not path.is_relative_to(stock) or type(ref['bytes']) is not int or not 0 < ref['bytes'] <= 1024**2 or
            path.stat().st_size!=ref['bytes'] or
            hashlib.sha256(path.read_bytes()).hexdigest()!=ref['sha256']):
            raise ValueError('Measured recipient snapshot changed')
    expected_refs=set(INTERFACES[-3:])
    if len(evidence['normal_encoding_source']) != 3 or set(ref['path'] for ref in evidence['normal_encoding_source'])!=expected_refs:
        raise ValueError('Exact pinned normal source proof set required')
    for ref in evidence['normal_encoding_source']:
        path=safe_path(source/ref['path'])
        if not path.is_relative_to(source) or hashlib.sha256(path.read_bytes()).hexdigest()!=ref['sha256']:
            raise ValueError('Normal encoding source proof changed')
    return evidence['material'], hashlib.sha256(evidence_bytes).hexdigest()


def prepare(output, source, *, check_pin=True, recipient_evidence=None, stock_root=None):
    output, source = safe_path(output), safe_path(source)
    if output.exists():
        raise ValueError('Fresh output directory required')
    hashes=source_hashes(source, check_pin=check_pin)
    material=None
    evidence_hash=None
    if recipient_evidence is not None:
        material,evidence_hash=validate_recipient_evidence(source,recipient_evidence,stock_root)
    original=validate(original_cube())
    own=Path(__file__).parent/'writer.cpp'
    payload=own.read_bytes()
    generated_header=header(original,material)
    original_text=json.dumps(original,indent=2)+'\n'
    manifest={'schema':'iw7.model-writer-source/1','source_pin':PIN,'source_hashes':hashes,
              'writer_sha256':hashlib.sha256(payload).hexdigest(),
              'header_sha256':hashlib.sha256(generated_header.encode()).hexdigest(),
              'geometry_source_sha256':hashlib.sha256(original_text.encode()).hexdigest(),'compiled':False,
              'geometry_roundtrip_verified':False,'iw7_normal_encoding_verified':False,
              'shadow_cutoff_lod':6,'collision_lod':255,'shadow_sentinel_source':SHADOW_SENTINEL_SOURCE,
              'lod0_dist':1000000,'has_lods':True,'candidate_variable':'lodInfo[0].dist',
              'material_reference':material,'recipient_evidence_sha256':evidence_hash,'ff_built':False,'pixels_verified':False,'ready':False}
    output.mkdir(parents=True)
    (output/'geometry.source.json').write_text(original_text,encoding='utf-8',newline='\n')
    (output/'probe_geometry.hpp').write_text(generated_header,encoding='utf-8',newline='\n')
    (output/'writer.cpp').write_bytes(payload)
    (output/'writer-source.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def authored_header(data, *, mesh_name):
    data = validate_authored(data)
    _geometry.authored_name(mesh_name)
    surface = data['surfaces'][0]
    def literal(value):
        text = format(_geometry.float32(value), '.9g')
        return text + ('.0' if '.' not in text and 'e' not in text else '') + 'f'
    rows = []
    for vertex, tangent in zip(surface['vertices'], _geometry.authored_tangents(data)):
        values = vertex['position'] + vertex['normal'] + vertex['uv'] + tangent
        rows.append('    {' + ', '.join(map(literal, values)) + '}')
    triangles = ['    {' + ', '.join(map(str, triangle)) + '}' for triangle in surface['triangles']]
    radius_squared = max(sum(p*p for p in vertex['position']) for vertex in surface['vertices'])
    radius = _geometry.float32(radius_squared)
    if radius < radius_squared:
        import struct
        bits = struct.unpack('<I', struct.pack('<f', radius))[0]
        radius = struct.unpack('<f', struct.pack('<I', bits+1))[0]
    return ('#pragma once\n' +
            ''.join('inline constexpr const char* '+key+' = '+json.dumps(value)+';\n' for key, value in (
                ('probe_model_name', data['name']), ('probe_mesh_name', mesh_name),
                ('probe_model_path', 'xmodel/'+data['name']+'.xmb'),
                ('probe_mesh_path', 'xsurface/'+mesh_name+'.xsb'),
                ('probe_material_name', surface['material_reference']))) +
            f'inline constexpr unsigned probe_vertex_count = {len(rows)}, probe_triangle_count = {len(triangles)};\n' +
            ''.join('inline constexpr float probe_bounds_'+suffix+'[3] = {'+', '.join(map(literal, data['bounds'][key]))+'};\n'
                    for suffix, key in (('mid', 'midpoint'), ('half', 'half_size'))) +
            'inline constexpr float probe_radius_squared = '+literal(radius)+';\n' +
            'struct ProbeVertex { float xyz[3], normal[3], uv[2], tangent[3]; };\n' +
            'inline constexpr ProbeVertex probe_vertices[probe_vertex_count] = {\n'+',\n'.join(rows)+'\n};\n' +
            'inline constexpr unsigned short probe_triangles[probe_triangle_count][3] = {\n'+',\n'.join(triangles)+'\n};\n' +
            'inline constexpr unsigned probe_packed_uvs[probe_vertex_count] = {\n    '+
            ', '.join(f'0x{_geometry.packed_uv(vertex["uv"]):08x}u' for vertex in surface['vertices'])+'\n};\n')


def adapt_authored_writer(template, contract):
    """Adapt the existing serializer AND reader, with exact seam-drift refusal."""
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
        'v.texCoord.packed=pack_uv(input.uv);': 'v.texCoord.packed=probe_packed_uvs[i];',
        'surfs.name="paris_model_probe_lod0";': 'surfs.name=probe_mesh_name;',
        'model.name="paris_model_probe";': 'model.name=probe_model_name;',
    }
    for old, new in replacements.items():
        if template.count(old) != 1:
            raise ValueError('Existing authored writer seam changed: '+old)
        template = template.replace(old, new)
    for old, new, count in (('"xmodel/paris_model_probe.xmb"', 'probe_model_path', 3),
                            ('"xsurface/paris_model_probe_lod0.xsb"', 'probe_mesh_path', 3)):
        if template.count(old) != count:
            raise ValueError('Existing owned writer/reader path seam changed')
        template = template.replace(old, new)
    lines = template.splitlines()
    uv = [i for i, line in enumerate(lines) if line.startswith('static uint32_t pack_uv(')]
    reports = [i for i, line in enumerate(lines) if 'std::cout<<' in line]
    if len(uv) != 1 or len(reports) != 1:
        raise ValueError('Existing UV/report seam changed')
    lines[0] = '// Authored bounded rigid geometry; same pinned serializer/reader, no native proof yet.'
    lines[uv[0]] = '// UV words are prepared binary16 nearest-even U-low/V-high values.'
    report = dict(schema='iw7.model-roundtrip/1', geometry_profile=AUTHORED_PROFILE,
                  namespace=contract['namespace'], zone=contract['zone'], model_name=contract['model_name'],
                  mesh_name=contract['mesh_name'], vertices=contract['vertices'], triangles=contract['triangles'],
                  bones=1, surfaces=1, lods=1, shadow_cutoff_lod=6, collision_lod=255, lod0_dist=1000000,
                  has_lods=True, geometry_roundtrip_verified=True, read_existing_supported=True,
                  normal_encoding='H1-1010102-candidate', iw7_normal_encoding_verified=False,
                  material_reference=contract['material_reference'], physics_serialized=False,
                  ff_built=False, pixels_verified=False, ready=False)
    lines[reports[0]] = '    std::cout << '+json.dumps(json.dumps(report, separators=(',', ':'))+'\n')+';'
    return '\n'.join(lines)+'\n'


def _authored_payloads(data, *, namespace, zone, mesh_name, material_reference):
    data = validate_authored(data, material_reference=material_reference)
    for name in (namespace, zone, mesh_name):
        _geometry.authored_name(name)
    ncs = 'ncs_mdl_'+zone
    surface = data['surfaces'][0]
    contract = dict(namespace=namespace, zone=zone, model_name=data['name'], mesh_name=mesh_name,
                    material_reference=surface['material_reference'], ncs_name=ncs,
                    vertices=len(surface['vertices']), triangles=len(surface['triangles']), bounds=data['bounds'])
    template = Path(__file__).with_name('writer.cpp').read_bytes()
    payloads = {
        'geometry.source.json': (json.dumps(data, indent=2, allow_nan=False)+'\n').encode(),
        'probe_geometry.hpp': authored_header(data, mesh_name=mesh_name).encode(),
        'writer.cpp': adapt_authored_writer(template.decode(), contract).encode(),
        # The authored material is a local payload dependency, NEVER an ignored recipient reference.
        'zone_source/'+zone+'.csv': ('material,'+material_reference+'\nxmodel,'+data['name']+
                                    '\nnetconststrings,'+ncs+'\n').encode(),
        'netconststrings/'+ncs+'.json': (json.dumps({'stringType': 0, 'sourceType': 2,
                                                   'stringList': [data['name']]}, indent=2)+'\n').encode(),
    }
    return contract, payloads, hashlib.sha256(template).hexdigest()


def prepare_authored(output, source, geometry_path, *, namespace, zone, mesh_name,
                     material_reference, check_pin=True):
    output = safe_path(output)
    if output.exists():
        raise ValueError('Fresh authored source directory required')
    with safe_path(geometry_path).open('rb') as stream:
        raw = stream.read(512*1024+1)
    if not 0 < len(raw) <= 512*1024:
        raise ValueError('Authored geometry source exceeds 512 KiB')
    data = json.loads(raw)
    contract, payloads, template_hash = _authored_payloads(data, namespace=namespace, zone=zone,
        mesh_name=mesh_name, material_reference=material_reference)
    hashes = source_hashes(source, check_pin=check_pin)
    manifest = dict(schema='iw7.model-writer-source/1', geometry_profile=AUTHORED_PROFILE,
        source_pin=PIN, source_hashes=hashes, **contract, writer_template_sha256=template_hash,
        geometry_input_sha256=hashlib.sha256(raw).hexdigest(),
        source_files={name: hashlib.sha256(payload).hexdigest() for name, payload in payloads.items()},
        writer_sha256=hashlib.sha256(payloads['writer.cpp']).hexdigest(),
        header_sha256=hashlib.sha256(payloads['probe_geometry.hpp']).hexdigest(),
        geometry_source_sha256=hashlib.sha256(payloads['geometry.source.json']).hexdigest(),
        artifact_paths=['xmodel/'+data['name']+'.xmb', 'xsurface/'+mesh_name+'.xsb'],
        compiled=False, geometry_roundtrip_verified=False, iw7_normal_encoding_verified=False,
        shadow_cutoff_lod=6, collision_lod=255, shadow_sentinel_source=SHADOW_SENTINEL_SOURCE,
        lod0_dist=1000000, has_lods=True, candidate_variable='lodInfo[0].dist',
        material_payload_present=False, material_closure_required=True, physics_serialized=False,
        ff_built=False, pixels_verified=False, ready=False)
    output.mkdir(parents=True)
    for name, payload in payloads.items():
        path = output/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    (output/'writer-source.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8', newline='\n')
    return manifest


def verify_authored_preparation(prepared):
    """Source recipe gate used by the existing build wrapper before compilation."""
    root = safe_path(prepared)
    def document(name):
        with safe_path(root/name).open('rb') as stream:
            raw = stream.read(512*1024+1)
        if not 0 < len(raw) <= 512*1024:
            raise ValueError('Bounded authored source document required')
        return json.loads(raw)
    manifest, data = document('writer-source.json'), document('geometry.source.json')
    if manifest.get('schema') != 'iw7.model-writer-source/1' or manifest.get('geometry_profile') != AUTHORED_PROFILE or manifest.get('source_pin') != PIN:
        raise ValueError('Explicit authored source profile required')
    for field in ('compiled', 'geometry_roundtrip_verified', 'iw7_normal_encoding_verified',
                  'material_payload_present', 'physics_serialized', 'ff_built', 'pixels_verified', 'ready'):
        if manifest.get(field) is not False:
            raise ValueError('Authored source cannot claim qualification/payloads')
    if manifest.get('material_closure_required') is not True or manifest.get('shadow_sentinel_source') != SHADOW_SENTINEL_SOURCE:
        raise ValueError('Authored dependency/sentinel source contract differs')
    for field, value in (('shadow_cutoff_lod', 6), ('collision_lod', 255), ('lod0_dist', 1000000),
                         ('has_lods', True), ('candidate_variable', 'lodInfo[0].dist')):
        if type(manifest.get(field)) is not type(value) or manifest[field] != value:
            raise ValueError('Authored source LOD metadata differs')
    contract, payloads, template_hash = _authored_payloads(data, **{key: manifest[key] for key in (
        'namespace', 'zone', 'mesh_name', 'material_reference')})
    if any(json.dumps(manifest.get(key), sort_keys=True, allow_nan=False) != json.dumps(value, sort_keys=True, allow_nan=False)
           for key, value in contract.items()) or manifest.get('writer_template_sha256') != template_hash:
        raise ValueError('Authored source contract/template changed')
    for field, name in (('writer_sha256', 'writer.cpp'), ('header_sha256', 'probe_geometry.hpp'),
                        ('geometry_source_sha256', 'geometry.source.json')):
        if manifest.get(field) != hashlib.sha256(payloads[name]).hexdigest():
            raise ValueError('Authored recipe hash differs')
    expected = {name: hashlib.sha256(payload).hexdigest() for name, payload in payloads.items()}
    if manifest.get('source_files') != expected or manifest.get('artifact_paths') != [
            'xmodel/'+contract['model_name']+'.xmb', 'xsurface/'+contract['mesh_name']+'.xsb']:
        raise ValueError('Exact authored source/artifact inventory required')
    for name, payload in payloads.items():
        with safe_path(root/name).open('rb') as stream:
            actual = stream.read(len(payload)+1)
        if actual != payload:
            raise ValueError('Prepared authored source changed: '+name)
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--source',type=Path)
    parser.add_argument('--recipient-evidence',type=Path)
    parser.add_argument('--stock-root',type=Path)
    parser.add_argument('--geometry-source',type=Path)
    parser.add_argument('--namespace')
    parser.add_argument('--zone')
    parser.add_argument('--mesh-name')
    parser.add_argument('--material-reference')
    parser.add_argument('--verify-authored',type=Path)
    args=parser.parse_args()
    authored = (args.geometry_source, args.namespace, args.zone, args.mesh_name, args.material_reference)
    if args.verify_authored:
        if any(authored) or args.output or args.source or args.recipient_evidence or args.stock_root:
            parser.error('--verify-authored accepts only its prepared source directory')
        result = verify_authored_preparation(args.verify_authored)
    elif not args.output or not args.source:
        parser.error('--output and --source required for preparation')
    elif any(value is not None for value in authored):
        if any(value is None for value in authored) or args.recipient_evidence or args.stock_root:
            parser.error('Authored preparation requires geometry/namespace/zone/mesh/material together, without recipient options')
        result = prepare_authored(args.output,args.source,args.geometry_source,namespace=args.namespace,
            zone=args.zone,mesh_name=args.mesh_name,material_reference=args.material_reference)
    else:
        result = prepare(args.output,args.source,recipient_evidence=args.recipient_evidence,stock_root=args.stock_root)
    print(json.dumps(result,indent=2))

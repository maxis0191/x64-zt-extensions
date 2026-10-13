"""Prepare source/header only for an original, fixed probe; never compile or launch."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import os
from geometry import original_cube, validate

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

def prepare(output, source, *, check_pin=True, recipient_evidence=None, stock_root=None):
    output, source = safe_path(output), safe_path(source)
    if output.exists():
        raise ValueError('Fresh output directory required')
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
    material=None
    evidence_hash=None
    if recipient_evidence is not None:
        evidence_bytes=safe_path(recipient_evidence).read_bytes()
        evidence=json.loads(evidence_bytes)
        if (evidence.get('schema')!='iw7.model-recipient-evidence/1' or evidence.get('source_pin')!=PIN or
            evidence.get('recipient')!='cp_zmb' or evidence.get('material')!='mopw/character_park_clown_zombie_shoes' or
            evidence.get('snapshot_only') is not True or evidence.get('runtime_verified') is not False):
            raise ValueError('Exact measured recipient reference required, gameplay remains pending')
        if stock_root is None:
            raise ValueError('Measured stock snapshot must be rechecked before binding the material')
        stock=safe_path(stock_root)
        for key,ref in evidence['material_snapshot'].items():
            path=safe_path(stock/ref['path'])
            if (not path.is_relative_to(stock) or path.stat().st_size!=ref['bytes'] or ref['bytes']>1024**2 or
                hashlib.sha256(path.read_bytes()).hexdigest()!=ref['sha256']):
                raise ValueError('Measured recipient snapshot changed')
        expected_refs=set(INTERFACES[-3:])
        if set(ref['path'] for ref in evidence['normal_encoding_source'])!=expected_refs:
            raise ValueError('Exact pinned normal source proof set required')
        for ref in evidence['normal_encoding_source']:
            path=safe_path(source/ref['path'])
            if not path.is_relative_to(source) or hashlib.sha256(path.read_bytes()).hexdigest()!=ref['sha256']:
                raise ValueError('Normal encoding source proof changed')
        material=evidence['material']
        evidence_hash=hashlib.sha256(evidence_bytes).hexdigest()
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

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--recipient-evidence',type=Path)
    parser.add_argument('--stock-root',type=Path)
    args=parser.parse_args()
    print(json.dumps(prepare(args.output,args.source,recipient_evidence=args.recipient_evidence,stock_root=args.stock_root),indent=2))

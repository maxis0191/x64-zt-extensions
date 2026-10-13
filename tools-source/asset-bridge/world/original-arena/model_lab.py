"""Stage/recheck original arena records through the existing ModelLab FF path."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re

LAB = Path(__file__).resolve().parents[4] / 'ops/model-lab'
def local_module(name,path):
    spec = importlib.util.spec_from_file_location(name,path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

writer = local_module('_arena_model_lab_writer',LAB/'prepare_writer.py')
sources = local_module('_arena_model_lab_sources',LAB/'rigid_export.py')
readback = local_module('_arena_model_lab_readback',Path(__file__).with_name('readback.py'))
PIN,safe_path,assets = writer.PIN,writer.safe_path,sources.assets

PROFILE = 'iw7-original-arena-rigid-v1'
MODEL = 'paris_original_arena'
MESH = MODEL+'_lod0'
MATERIAL = readback.MATERIAL
PAIR = ('xmodel/'+MODEL+'.xmb', 'xsurface/'+MESH+'.xsb')
GEOMETRY = 'evidence/geometry.source.json'
WRITER = 'evidence/arena-writer-source.json'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, allow_nan=False)+'\n').encode()


def document(path, limit):
    raw = readback.bounded(safe_path(path), limit)
    def pairs(items):
        result = {}
        for key, value in items:
            readback.check(key not in result, 'Duplicate JSON field')
            result[key] = value
        return result
    def nonfinite(_):
        raise ValueError('Nonfinite JSON number')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite), raw


def source_context(manifest, geometry, geometry_raw):
    readback.check(type(manifest) is dict and type(geometry) is dict, 'Source JSON objects required')
    readback.check(manifest.get('schema') == 'iw7.original-arena-writer-source/1' and
                   manifest.get('source_pin') == PIN and manifest.get('model_name') == MODEL and
                   manifest.get('mesh_name') == MESH and manifest.get('material_reference') == MATERIAL,
                   'Explicit original material-bound writer source required')
    readback.check(all(manifest.get(key) is False for key in
                      ('compiled','ff_built','runtime_verified','physics_serialized')),
                   'Writer source is not native/game evidence')
    hashes = manifest.get('source_files', {})
    readback.check(set(hashes) == {'geometry.source.json','probe_geometry.hpp','arena_writer.cpp'} and
                   all(type(value) is str and re.fullmatch('[a-f0-9]{64}', value) for value in hashes.values()) and
                   hashes['geometry.source.json'] == digest(geometry_raw), 'Writer source/geometry binding differs')
    readback.check(type(manifest.get('recipient_evidence_sha256')) is str and
                   re.fullmatch('[a-f0-9]{64}', manifest['recipient_evidence_sha256']) and
                   type(manifest.get('source_hashes')) is dict and bool(manifest['source_hashes']) and
                   all(type(value) is str and re.fullmatch('[a-f0-9]{64}', value)
                       for value in manifest['source_hashes'].values()), 'Measured source reference bindings required')
    counts = {'bones':1,'roots':1,'surfaces':1,
              'vertices':len(geometry['surfaces'][0]['vertices']),
              'triangles':len(geometry['surfaces'][0]['triangles'])}
    declared = manifest.get('selected_counts', {})
    readback.check(type(declared) is dict and set(declared) == set(counts) and
                   all(type(value) is int for value in declared.values()) and declared == counts and
                   manifest.get('lod0_dist') == 1000000 and manifest.get('has_lods') is True and
                   manifest.get('shadow_cutoff_lod') == 6 and manifest.get('collision_lod') == 255,
                   'Original rigid count/LOD metadata differs')
    return counts


def make_plan(manifest, geometry_raw, writer_raw, payloads):
    return {'schema':'iw7.model-ff-plan/1','geometry_profile':PROFILE,'origin':'authored-arena',
            'source_pin':PIN,'zone':'paris_model_probe','recipient':'cp_zmb',
            'model_name':MODEL,'mesh_name':MESH,'material_reference':MATERIAL,
            'selected_counts':manifest['selected_counts'],'lod0_dist':1000000,'has_lods':True,
            'shadow_cutoff_lod':6,'collision_lod':255,
            'source_files':{name:digest(raw) for name,raw in payloads.items()},
            'validation_files':[*payloads,GEOMETRY,WRITER,'model-ff-plan.json'],
            'geometry_source_sha256':digest(geometry_raw),'writer_source_sha256':digest(writer_raw),
            'material_payload_copied':False,'native_provenance_verified':False,
            'physics_serialized':False,'ff_built':False,'pixels_verified':False,'ready':False}


def stage(artifacts, prepared_source, output):
    artifacts, prepared, output = map(safe_path, (artifacts,prepared_source,output))
    readback.check(not output.exists() and not output.is_relative_to(artifacts) and
                   not output.is_relative_to(prepared), 'Fresh staging outside immutable inputs required')
    manifest, writer_raw = document(prepared/'arena-writer-source.json', 65536)
    geometry, geometry_raw = document(prepared/'geometry.source.json', 128*1024)
    source_context(manifest, geometry, geometry_raw)
    for name, expected in manifest['source_files'].items():
        readback.check(digest(readback.bounded(safe_path(prepared/name),128*1024)) == expected,
                       'Prepared writer source changed: '+name)
    model, mesh = (readback.bounded(safe_path(artifacts/name),8192) for name in PAIR)
    readback.inspect(model,mesh,geometry,expected_material=MATERIAL)
    payloads = {PAIR[0]:model,PAIR[1]:mesh,**assets(MODEL,MESH)}
    plan = make_plan(manifest,geometry_raw,writer_raw,payloads)
    payloads.update({GEOMETRY:geometry_raw,WRITER:writer_raw,'model-ff-plan.json':json_bytes(plan)})
    output.mkdir(parents=True)
    for name, raw in payloads.items():
        path = output/name
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    return plan


def verify_stage(source):
    source = safe_path(source)
    plan, _ = document(source/'model-ff-plan.json',65536)
    manifest, writer_raw = document(source/WRITER,65536)
    geometry, geometry_raw = document(source/GEOMETRY,128*1024)
    source_context(manifest,geometry,geometry_raw)
    model,mesh = (readback.bounded(safe_path(source/name),8192) for name in PAIR)
    report = readback.inspect(model,mesh,geometry,expected_material=MATERIAL)
    payloads = {PAIR[0]:model,PAIR[1]:mesh,**assets(MODEL,MESH)}
    expected = make_plan(manifest,geometry_raw,writer_raw,payloads)
    readback.check(json.dumps(plan,sort_keys=True) == json.dumps(expected,sort_keys=True),
                   'Original arena FF source plan changed')
    for name,raw in payloads.items():
        readback.check(readback.bounded(safe_path(source/name),8192) == raw,
                       'Original arena FF input changed: '+name)
    return plan,geometry,report


def verify_dump(source,dump,ff):
    plan,geometry,original = verify_stage(source)
    dumped = [readback.bounded(safe_path(Path(dump)/name),8192) for name in PAIR]
    report = readback.inspect(*dumped,geometry,expected_material=MATERIAL)
    readback.check(report == original, 'FF re-dump differs from original rigid geometry/packed streams')
    ff_raw = readback.bounded(safe_path(ff),32*1024**2)
    return {'schema':'iw7.model-original-arena-roundtrip/1','geometry_profile':PROFILE,'origin':'authored-arena',
            'model_name':MODEL,'mesh_name':MESH,'material_reference':MATERIAL,
            'selected_counts':plan['selected_counts'],'lod0_dist':1000000,
            'source_plan_sha256':digest(readback.bounded(safe_path(Path(source)/'model-ff-plan.json'),65536)),
            'geometry_source_sha256':plan['geometry_source_sha256'],
            'ff':{'bytes':len(ff_raw),'sha256':digest(ff_raw)},
            'inputs':[{'relative_path':'roundtrip/'+name,'bytes':len(raw),'sha256':digest(raw)}
                      for name,raw in zip(PAIR,dumped)],
            'packed_streams_sha256':report['packed_streams_sha256'],
            'geometry_roundtrip_verified':True,'source_geometry_correspondence_verified':True,
            'packed_attributes_byte_identical':True,'native_provenance_verified':False,
            'physics_serialized':False,'runtime_verified':False,'pixels_verified':False,'ready':False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command',required=True)
    staging = commands.add_parser('stage')
    staging.add_argument('--artifacts',type=Path,required=True)
    staging.add_argument('--prepared-source',type=Path,required=True)
    staging.add_argument('--output',type=Path,required=True)
    for name in ('verify-stage','verify-dump'):
        command = commands.add_parser(name)
        command.add_argument('--source',type=Path,required=True)
        if name == 'verify-dump':
            command.add_argument('--dump',type=Path,required=True)
            command.add_argument('--ff',type=Path,required=True)
    args = parser.parse_args()
    result = (stage(args.artifacts,args.prepared_source,args.output) if args.command == 'stage' else
              verify_stage(args.source)[0] if args.command == 'verify-stage' else
              verify_dump(args.source,args.dump,args.ff))
    print(json.dumps(result,indent=2,allow_nan=False))

"""Stage/recheck original arena records through the existing ModelLab FF path."""
import argparse
import csv
import hashlib
import importlib.util
import json
import io
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


def validate_reference_evidence(tool_source,evidence_path,measurement_root):
    """One named nondefault stock reference; no material payload/GPU claim."""
    evidence,raw = document(evidence_path,65536)
    readback.check(type(evidence) is dict and evidence.get('schema') == 'iw7.original-arena-recipient-reference/1' and
                   evidence.get('source_pin') == PIN and evidence.get('recipient') == 'cp_zmb' and
                   evidence.get('material') == MATERIAL and evidence.get('snapshot_only') is True and
                   evidence.get('runtime_verified') is False and evidence.get('material_payload_verified') is False,
                   'Explicit original arena stock reference measurement required')
    root = safe_path(measurement_root)
    snapshots = evidence.get('reference_snapshot',{})
    readback.check(type(snapshots) is dict and set(snapshots) == {'csv','stdout','closure'},
                   'Complete reference CSV/log/original-job closure snapshot required')
    captured = {}
    for key,item in snapshots.items():
        readback.check(type(item) is dict and set(item) == {'path','bytes','sha256'} and
                       type(item['path']) is str and type(item['bytes']) is int and 0 < item['bytes'] <= 1024**2,
                       'Bounded reference snapshot entry required')
        path = safe_path(root/item['path'])
        readback.check(path.is_relative_to(root), 'Reference snapshot path escapes measurement root')
        data = readback.bounded(path,1024**2)
        readback.check(len(data) == item['bytes'] and digest(data) == item['sha256'], 'Reference snapshot changed')
        captured[key] = data
    rows = list(csv.reader(io.StringIO(captured['csv'].decode('utf-8-sig'))))
    readback.check(rows == [['type','name','status'],['material',MATERIAL,'verified']],
                   'Exactly one nondefault registered stock material reference required')
    log = captured['stdout'].decode('utf-8-sig')
    marker = 'ENEMY_REFERENCE_CHECK map=cp_zmb rows=1 verified=1 missing=0 default=0 output='
    readback.check(sum(line.startswith(marker) for line in log.splitlines()) == 1 and
                   not re.search(r'\[ (?:ERROR|FATAL) \]',log), 'Actual selective CP reference-check log required')
    closure,_ = document(root/snapshots['closure']['path'],1024**2)
    readback.check(type(closure) is dict, 'Original reference process closure object required')
    expected_args = ['-headless','-unbuffered-io','-strict-content-sources','-enemy-reference-check','cp_zmb']
    args = closure.get('Arguments',[]) if type(closure) is dict else []
    readback.check(closure.get('Schema') == 'iw7.original-arena-reference-process/1' and
                   type(closure.get('ExitCode')) is int and closure['ExitCode'] == 0 and
                   closure.get('RootExited') is True and type(closure.get('ActiveProcesses')) is int and
                   closure['ActiveProcesses'] == 0 and closure.get('JobClosed') is True and
                   type(closure.get('PlanSHA256')) is str and re.fullmatch('[a-f0-9]{64}',closure['PlanSHA256']) and
                   closure.get('ImageSHA256') == 'e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04' and
                   type(args) is list and len(args) == 7 and args[:5] == expected_args and
                   type(args[6]) is str and re.fullmatch('[a-z0-9_]{1,128}',args[6]),
                   'Successful closed original selective-reference process required')
    identity = closure.get('Identity',{})
    readback.check(type(identity) is dict and type(identity.get('PID')) is int and identity['PID'] > 0 and
                   type(identity.get('Image')) is str and Path(identity['Image']).is_absolute() and
                   type(identity.get('CreatedUtc')) is str and re.fullmatch(
                       r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,7})?(?:Z|\+00:00)',identity['CreatedUtc']),
                   'Original process identity required with reference measurement')
    requests,requests_raw = document(root/'reference-request.json',4096)
    readback.check(requests == {'schema':'iw7.original-arena-reference-request/1','recipient':'cp_zmb',
                                'material':MATERIAL,'input_csv':args[5],'output_csv':args[6]} and
                   digest(requests_raw) == closure.get('RequestSHA256'), 'Closed reference process request binding differs')
    input_path = safe_path(root/args[5])
    readback.check(input_path.is_relative_to(root) and
                   readback.bounded(input_path,4096) == ('material,'+MATERIAL+'\n').encode(), 'Single material request CSV differs')
    readback.check(safe_path(root/snapshots['csv']['path']) == safe_path(root/'enemy-catalog'/(args[6]+'.csv')),
                   'Selective reference output path differs from the actual native command')
    refs = evidence.get('normal_encoding_source',[])
    readback.check(type(refs) is list and len(refs) == 3 and
                   {ref['path'] for ref in refs} == set(writer.INTERFACES[-3:]), 'Exact normal-source proof set required')
    for ref in refs:
        path = safe_path(Path(tool_source)/ref['path'])
        readback.check(path.is_relative_to(safe_path(tool_source)) and
                       digest(readback.bounded(path,1024**2)) == ref['sha256'], 'Normal source proof changed')
    return MATERIAL,digest(raw)


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

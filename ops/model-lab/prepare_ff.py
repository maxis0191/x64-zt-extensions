"""Stage original model inputs/CSV only after measured standalone roundtrip."""
import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
from prepare_writer import safe_path, PIN
import importlib.util
import sys
import re

MATERIAL='mopw/character_park_clown_zombie_shoes'
ARTIFACTS=('xmodel/paris_model_probe.xmb','xsurface/paris_model_probe_lod0.xsb')

def candidate_metadata(data):
    return (type(data.get('lod0_dist')) in (int, float) and data['lod0_dist'] == 1000000 and
            data.get('has_lods') is True and type(data.get('shadow_cutoff_lod')) is int and
            data['shadow_cutoff_lod'] == 6 and type(data.get('collision_lod')) is int and data['collision_lod'] == 255)

def stage(writer_run, output):
    run,output=safe_path(writer_run),safe_path(output)
    if output.exists():
        raise ValueError('Fresh model FF staging directory required')
    provenance=run/'writer-provenance.json'
    if provenance.stat().st_size>1024**2:
        raise ValueError('Bounded writer provenance required')
    provenance_raw=bounded(provenance,1024**2)
    data=json.loads(provenance_raw)
    validate_native_closure(run,data,provenance_raw)
    roundtrip=data.get('Roundtrip',{})
    if (data.get('Schema')!='iw7.model-writer-build/1' or data.get('SourcePin')!=PIN or
        data.get('Source',{}).get('material_reference')!=MATERIAL or
        roundtrip.get('geometry_roundtrip_verified') is not True or roundtrip.get('material_reference')!=MATERIAL or
        roundtrip.get('vertices')!=24 or roundtrip.get('triangles')!=12 or roundtrip.get('bones')!=1 or
        roundtrip.get('surfaces')!=1 or roundtrip.get('lods')!=1 or data.get('Ready') is not False or data.get('FFBuilt') is not False):
        raise ValueError('Exact material-linked measured original roundtrip required')
    if (not candidate_metadata(data.get('Source',{})) or not candidate_metadata(roundtrip) or
        data['Source'].get('candidate_variable') != 'lodInfo[0].dist'):
        raise ValueError('Exact measured one-variable LOD distance and unchanged model metadata required')
    entries=data.get('Artifacts',[])
    if len(entries)!=2 or {e.get('Path') for e in entries}!=set(ARTIFACTS):
        raise ValueError('Exact original XMB/XSB inventory required')
    payloads={}
    for entry in entries:
        name=entry['Path'];path=safe_path(run/'artifacts'/name)
        if not path.is_relative_to(run) or not 1<=entry.get('Bytes',0)<=8192 or path.stat().st_size!=entry['Bytes']:
            raise ValueError('Bounded measured original artifact required')
        payload=path.read_bytes()
        if hashlib.sha256(payload).hexdigest().upper()!=entry.get('SHA256','').upper():
            raise ValueError('Original writer artifact changed')
        payloads[name]=payload
    output.mkdir(parents=True)
    for name,payload in payloads.items():
        path=output/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(payload)
    (output/'zone_source').mkdir()
    (output/'zone_source/paris_model_probe_recipient.csv').write_text('material,'+MATERIAL+'\n',encoding='utf-8',newline='\n')
    # Ignore causes typed material dependencies to be references, no retail bytes.
    (output/'zone_source/paris_model_probe.csv').write_text('ignore,paris_model_probe_recipient\nxmodel,paris_model_probe\nnetconststrings,ncs_mdl_paris_model_probe\n',encoding='utf-8',newline='\n')
    (output/'netconststrings').mkdir()
    (output/'netconststrings/ncs_mdl_paris_model_probe.json').write_text(json.dumps({'stringType':0,'sourceType':2,'stringList':['paris_model_probe']},indent=2)+'\n')
    plan={'schema':'iw7.model-ff-plan/1','zone':'paris_model_probe','recipient':'cp_zmb',
          'source_pin':PIN,'writer_provenance_sha256':hashlib.sha256(provenance.read_bytes()).hexdigest(),
          'material_reference':MATERIAL,'material_payload_copied':False,'original_model_template_copied':False,
          'candidate_variable':'lodInfo[0].dist','lod0_dist':1000000,'has_lods':True,'shadow_cutoff_lod':6,'collision_lod':255,
          'expected_inventory':[{'type':'material','name':','+MATERIAL,'recipient_reference':True},
                                {'type':'xmodelsurfs','name':'paris_model_probe_lod0'},
                                {'type':'xmodel','name':'paris_model_probe'},
                                {'type':'netconststrings','name':'ncs_mdl_paris_model_probe'},
                                {'type':'rawfile','name':'paris_model_probe'}],
          'offline_context_required':'cp_zmb with measured material linked; bootstrap-only cannot prove this reference',
          'engine_build_args':['-headless','-unbuffered-io','-buildzone','paris_model_probe'],
          'normal_encoding_runtime_verified':False,'ff_built':False,'pixels_verified':False,'ready':False}
    plan['source_files']={str(p.relative_to(output)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in output.rglob('*') if p.is_file()}
    (output/'model-ff-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    return plan


def authored_surfaces():
    """Use the canonical surfaces producer/inspector, never copy their formats."""
    path = Path(__file__).resolve().parents[2]/'tools-source/asset-bridge/surfaces'
    sys.path.insert(0, str(path))
    try:
        import authored_dds_material
        import inspect_content
        return authored_dds_material, inspect_content
    finally:
        sys.path.pop(0)


def bounded(path, limit):
    with safe_path(path).open('rb') as stream:
        raw = stream.read(limit+1)
    if not 0 < len(raw) <= limit:
        raise ValueError('Bounded authored input required: '+str(path))
    return raw


def validate_native_closure(root, provenance, provenance_raw):
    """New pending receipts require closure in BOTH legacy and authored routes."""
    if 'NativeReleasePending' not in provenance:
        return None, None  # Historical nonpending receipt contract remains unchanged.
    if (provenance['NativeReleasePending'] is not True or provenance.get('NativeClosureEvidence') != 'writer-closure.json' or
        type(provenance.get('NativeRootKey')) is not str or not re.fullmatch(r'IW7\.ModelWriter\.Root\.[a-f0-9]{32}', provenance['NativeRootKey'])):
        raise ValueError('Explicit two-phase native publication contract required')
    _, inspector=authored_surfaces()
    closure_raw=bounded(safe_path(root)/'writer-closure.json',65536)
    closure=inspector.parse_json(closure_raw)
    native_raw=bounded(safe_path(root)/'writer-native-run.json',1024**2)
    native=inspector.parse_json(native_raw)
    expected=dict(Schema='iw7.model-writer-native-run/1',Status='NativeRoundtripPassed',
        NativeRootKey=provenance['NativeRootKey'],SourcePin=provenance.get('SourcePin'),Source=provenance.get('Source'),
        WriterSHA256=provenance.get('WriterSHA256'),CompilerSHA256=provenance.get('CompilerSHA256'),
        ReleasePending=True,LeaseReleased=False,TreeClosureConfirmed=True,Quarantined=False,Ready=False)
    if type(native) is not dict or any(json.dumps(native.get(key),sort_keys=True,allow_nan=False) != json.dumps(value,sort_keys=True,allow_nan=False)
                                       for key,value in expected.items()):
        raise ValueError('Native run must be the same successful typed writer/source/root snapshot')
    for field in ('WriterSHA256','CompilerSHA256'):
        if type(native[field]) is not str or not re.fullmatch('[a-fA-F0-9]{64}',native[field]):
            raise ValueError('Measured native writer/compiler hashes required')
    stages=native.get('Stages')
    if type(stages) is not list or len(stages) != 3:
        raise ValueError('Three original native stages required')
    for stage,(name,kind,image) in zip(stages,(('discovery','Fixture','vswhere.exe'),('compile','Compile','cl.exe'),('fixture','Fixture','model-writer.exe'))):
        if (type(stage) is not dict or stage.get('Name') != name or stage.get('Stage') != kind or
            type(stage.get('ExitCode')) is not int or stage['ExitCode'] != 0 or stage.get('TreeClosureConfirmed') is not True or
            type(stage.get('ImageSHA256')) is not str or not re.fullmatch('[a-fA-F0-9]{64}',stage['ImageSHA256'])):
            raise ValueError('Native stages must be ordered, successful and closed')
        identity=stage.get('Identity')
        if (type(identity) is not dict or type(identity.get('PID')) is not int or not 1 <= identity['PID'] <= 0xffffffff or
            type(identity.get('Image')) is not str or not PureWindowsPath(identity['Image']).is_absolute() or
            PureWindowsPath(identity['Image']).name.lower() != image or type(identity.get('CreatedUtc')) is not str or
            not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{7}Z',identity['CreatedUtc'])):
            raise ValueError('Original native stage identity required')
        expected_hash=native['CompilerSHA256'] if name == 'compile' else native['WriterSHA256'] if name == 'fixture' else None
        if expected_hash is not None and stage['ImageSHA256'].lower() != expected_hash.lower():
            raise ValueError('Native stage image differs from measured compiler/writer')
    if (closure.get('Schema') != 'iw7.model-writer-closure/1' or
        closure.get('NativeRootKey') != provenance['NativeRootKey'] or
        closure.get('WriterProvenanceSHA256') != hashlib.sha256(provenance_raw).hexdigest() or
        closure.get('NativeRunSHA256') != hashlib.sha256(native_raw).hexdigest() or
        any(closure.get(key) is not True for key in ('JobClosureVerified','LeaseReleased','InputGuardsClosed','PreReleasePublicationsVerified')) or
        closure.get('Ready') is not False):
        raise ValueError('Final original native closure does not bind the pre-release receipts')
    return closure_raw,native_raw


def authored_material_inputs(value, *, zone, material_reference):
    producer, inspector = authored_surfaces()
    if type(value) is not dict or type(value.get('files')) is not dict or not 1 <= len(value['files']) <= 12:
        raise ValueError('Explicit authored material producer result required')
    files = value['files']
    if any(type(raw) is not bytes or not 0 < len(raw) <= 17*1024**2 for raw in files.values()) or sum(map(len, files.values())) > 20*1024**2:
        raise ValueError('Bounded owned material payloads required')
    if value.get('material_reference') != material_reference:
        raise ValueError('Geometry/material producer reference differs')
    name = value['image']['name']
    material_path = 'materials/'+material_reference+'.json'
    technique = inspector.parse_json(files[material_path])['techniqueSet->name']
    template = {'material': files[material_path]}
    for role in ('statebits', 'statebitsmap', 'stateinfo', 'cbi', 'cbt'):
        family = 'constantbuffer' if role in ('cbi', 'cbt') else 'state'
        path = f'techsets/{family}/{technique}/{material_reference}.{role}'
        if path in files:
            template[role] = files[path]
    expected = producer.prepare_material(zone=zone, image_name=name, material_name=material_reference,
        texture_slot=value['texture_slot'], dds=files['images/'+name+'.dds'], template=template)
    metadata = lambda data: json.dumps({key: item for key, item in data.items() if key != 'files'}, sort_keys=True, allow_nan=False)
    if files != expected['files'] or metadata(value) != metadata(expected):
        raise ValueError('Authored material closure/metadata differs from canonical producer')
    return expected


def _authored_stage_payloads(writer_root, material_inputs, *, artifacts_root=None):
    import prepare_writer
    root = safe_path(writer_root)
    manifest = prepare_writer.verify_authored_preparation(root)
    _, inspector = authored_surfaces()
    provenance_raw = bounded(root/'writer-provenance.json', 512*1024)
    provenance = inspector.parse_json(provenance_raw)
    report = provenance.get('Roundtrip', {})
    if (provenance.get('Schema') != 'iw7.model-writer-build/1' or provenance.get('SourcePin') != PIN or
        json.dumps(provenance.get('Source'), sort_keys=True) != json.dumps(manifest, sort_keys=True) or provenance.get('Ready') is not False or provenance.get('FFBuilt') is not False or
        provenance.get('PixelsVerified') is not False or type(provenance.get('WriterSHA256')) is not str):
        raise ValueError('Measured authored writer provenance required')
    if not re.fullmatch('[a-fA-F0-9]{64}', provenance['WriterSHA256']):
        raise ValueError('Explicit measured native reader hash required')
    closure_raw,native_raw=validate_native_closure(root,provenance,provenance_raw)
    for key in ('geometry_profile', 'namespace', 'zone', 'model_name', 'mesh_name', 'material_reference', 'vertices', 'triangles'):
        if type(report.get(key)) is not type(manifest[key]) or report[key] != manifest[key]:
            raise ValueError('Measured authored writer identity/counts differ')
    if report.get('schema') != 'iw7.model-roundtrip/1' or not candidate_metadata(report):
        raise ValueError('Measured authored writer profile differs')
    for key, value in (('geometry_roundtrip_verified', True), ('read_existing_supported', True),
                       ('iw7_normal_encoding_verified', False), ('physics_serialized', False),
                       ('ff_built', False), ('pixels_verified', False), ('ready', False)):
        if report.get(key) is not value:
            raise ValueError('Measured authored writer qualification differs')
    if any(type(report.get(key)) is not int or report[key] != 1 for key in ('bones', 'surfaces', 'lods')):
        raise ValueError('Measured one-root/surface/LOD writer required')
    entries = provenance.get('Artifacts')
    paths = manifest['artifact_paths']
    if type(entries) is not list or len(entries) != 2 or {entry.get('Path') for entry in entries} != set(paths):
        raise ValueError('Exact measured authored geometry artifacts required')
    payloads = {}
    artifacts = safe_path(artifacts_root) if artifacts_root is not None else root/'artifacts'
    for entry in entries:
        if type(entry.get('Bytes')) is not int or not 0 < entry['Bytes'] <= 8192:
            raise ValueError('Authored geometry exceeds existing reader envelope')
        raw = bounded(artifacts/entry['Path'], 8192)
        if len(raw) != entry['Bytes'] or hashlib.sha256(raw).hexdigest().lower() != str(entry.get('SHA256')).lower():
            raise ValueError('Measured authored geometry changed')
        payloads[entry['Path']] = raw
    material = authored_material_inputs(material_inputs, zone=manifest['zone'], material_reference=manifest['material_reference'])
    payloads.update(material['files'])
    zone, model, mesh, ncs = (manifest[key] for key in ('zone', 'model_name', 'mesh_name', 'ncs_name'))
    payloads['zone_source/'+zone+'.csv'] += f'xmodel,{model}\nnetconststrings,{ncs}\n'.encode()
    ncs_path = 'netconststrings/'+ncs+'.json'
    payloads[ncs_path] = bounded(root/ncs_path, 4096)
    references = material['recipient_references']
    inventory = ([{'type': 'techset', 'name': ','+references['techset'], 'recipient_reference': True}] +
                 [{'type': 'image', 'name': ','+name, 'recipient_reference': True} for name in references['images']] +
                 [{'type': kind, 'name': name} for kind, name in (
                     ('image', material['image']['name']), ('material', manifest['material_reference']),
                     ('xmodelsurfs', mesh), ('xmodel', model), ('netconststrings', ncs), ('rawfile', zone))])
    plan = dict(schema='iw7.model-ff-plan/3', geometry_profile=prepare_writer.AUTHORED_PROFILE, origin='authored-rigid',
        source_pin=PIN, namespace=manifest['namespace'], zone=zone, recipient='cp_zmb', model_name=model, mesh_name=mesh,
        ncs_name=ncs, material_reference=manifest['material_reference'], image=material['image'],
        recipient_references=references, expected_inventory=inventory, artifact_paths=paths,
        selected_counts=dict(bones=1, roots=1, surfaces=1, vertices=manifest['vertices'], triangles=manifest['triangles']),
        writer_provenance_sha256=hashlib.sha256(provenance_raw).hexdigest(), writer_sha256=provenance['WriterSHA256'],
        geometry_source_sha256=manifest['geometry_source_sha256'],
        material_payload_copied=True, material_closure_verified=False, normal_encoding_runtime_verified=False,
        physics_serialized=False, shadow_cutoff_lod=6, collision_lod=255, lod0_dist=1000000, has_lods=True,
        source_files={name: hashlib.sha256(raw).hexdigest() for name, raw in payloads.items()},
        ff_built=False, pixels_verified=False, ready=False)
    plan['dump_files'] = paths + sorted(name.replace('.dds', '.iw7Image') if name.startswith('images/') else name
        for name in material['files'] if not name.startswith('zone_source/'))
    evidence = {'evidence/writer/'+name: bounded(root/name, 512*1024) for name in (
        'writer-source.json', 'writer-provenance.json', *manifest['source_files'])}
    if closure_raw is not None:
        evidence['evidence/writer/writer-closure.json'] = closure_raw
        evidence['evidence/writer/writer-native-run.json'] = native_raw
    metadata = {key: value for key, value in material.items() if key != 'files'}
    metadata['files'] = {name: hashlib.sha256(raw).hexdigest() for name, raw in material['files'].items()}
    evidence['evidence/material-inputs.json'] = (json.dumps(metadata, indent=2)+'\n').encode()
    return plan, payloads, evidence


def stage_authored(writer_run, output, *, material_inputs):
    output = safe_path(output)
    if output.exists():
        raise ValueError('Fresh authored FF stage required')
    plan, files, evidence = _authored_stage_payloads(writer_run, material_inputs)
    output.mkdir(parents=True)
    for name, raw in {**files, **evidence}.items():
        path = output/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    (output/'model-ff-plan.json').write_text(json.dumps(plan, indent=2)+'\n', encoding='utf-8', newline='\n')
    verify_authored_stage(output)
    return plan


def verify_authored_stage(source):
    root = safe_path(source)
    _, inspector = authored_surfaces()
    plan = inspector.parse_json(bounded(root/'model-ff-plan.json', 512*1024))
    metadata = inspector.parse_json(bounded(root/'evidence/material-inputs.json', 65536))
    names = metadata['files']
    if type(names) is not dict or not 1 <= len(names) <= 12:
        raise ValueError('Bounded material source inventory required')
    files, total = {}, 0
    for name, sha in names.items():
        inspector.relative(name)
        if name == 'zone_source/'+plan['zone']+'.csv':
            # Material producer CSV precedes the two model-specific rows.
            combined = bounded(root/name, 65536)
            suffix = f'xmodel,{plan["model_name"]}\nnetconststrings,{plan["ncs_name"]}\n'.encode()
            if not combined.endswith(suffix):
                raise ValueError('Authored combined zone CSV changed')
            raw = combined[:-len(suffix)]
        else:
            raw = bounded(root/name, 17*1024**2)
        if hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError('Authored material payload changed')
        total += len(raw)
        if total > 20*1024**2:
            raise ValueError('Authored material read budget exceeded')
        files[name] = raw
    metadata['files'] = files
    expected, payloads, _ = _authored_stage_payloads(root/'evidence/writer', metadata, artifacts_root=root)
    if plan != expected:
        raise ValueError('Authored FF plan differs from measured geometry/material recipe')
    for name, raw in payloads.items():
        if bounded(root/name, 20*1024**2) != raw:
            raise ValueError('Authored FF payload differs')
    references = plan['recipient_references']
    check = inspector.Inspector(root, plan['zone'], [('techset', references['techset'])] +
        [('image', name) for name in references['images']], strict_reader_prepared=True)
    check.material(plan['material_reference'])
    if check.report()['errors']:
        raise ValueError('Authored material dependency preflight failed: '+json.dumps(check.report()['findings']))
    return plan


def verify_authored_dump(source, dump, ff):
    """Existing typed image verifier plus bounded material/sidecar comparison."""
    root, dumped = safe_path(source), safe_path(dump)
    plan = verify_authored_stage(root)
    producer, inspector = authored_surfaces()
    material_path = 'materials/'+plan['material_reference']+'.json'
    before = inspector.parse_json(bounded(root/material_path, 256*1024))
    after = inspector.parse_json(bounded(dumped/material_path, 256*1024))
    if type(after) is not dict or any(key not in after or after[key] != value for key, value in before.items()):
        raise ValueError('Dumped authored material fields differ')
    metadata = inspector.parse_json(bounded(root/'evidence/material-inputs.json', 65536))
    for name in metadata['files']:
        if not name.startswith('techsets/'):
            continue
        actual = bounded(dumped/name, 256*1024)
        expected = bounded(root/name, 256*1024)
        if name.endswith('.cbt'):
            # The native dump has pointers; presence is NOT a CBT layout/ABI proof.
            continue
        if name.endswith(('.stateinfo', '.statebitsmap')):
            if inspector.parse_json(actual) != inspector.parse_json(expected):
                raise ValueError('Dumped authored material state differs')
        elif actual != expected:
            raise ValueError('Dumped authored material sidecar differs')
    image = plan['image']
    image_result = producer.verify_image(bounded(root/('images/'+image['name']+'.dds'), 17*1024**2),
        bounded(dumped/('images/'+image['name']+'.iw7Image'), image['pixel_bytes']+382),
        image_name=image['name'], iw7_semantic=image['iw7_semantic'])
    ff_bytes = bounded(ff, 32*1024**2)
    return dict(schema='iw7.authored-material-roundtrip/1', geometry_profile=plan['geometry_profile'],
        namespace=plan['namespace'], zone=plan['zone'], material_reference=plan['material_reference'],
        source_plan_sha256=hashlib.sha256(bounded(root/'model-ff-plan.json', 512*1024)).hexdigest(),
        ff=dict(bytes=len(ff_bytes), sha256=hashlib.sha256(ff_bytes).hexdigest()), image=image_result,
        material_fields_verified=True, native_cbt_semantics_verified=False, recipient_resolution_verified=False,
        pixels_rendered_verified=False, physics_serialized=False, ready=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--writer-run',type=Path)
    source.add_argument('--export-root',type=Path)
    source.add_argument('--verify-authored-stage',type=Path)
    source.add_argument('--verify-authored-dump',type=Path)
    parser.add_argument('--dump',type=Path)
    parser.add_argument('--ff',type=Path)
    parser.add_argument('--request',type=Path)
    parser.add_argument('--manifest',type=Path)
    materials=parser.add_mutually_exclusive_group()
    materials.add_argument('--rebind-material')
    materials.add_argument('--material-rebinds',type=Path)
    parser.add_argument('--lod-distance',type=float)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.verify_authored_stage or args.verify_authored_dump:
        if any(value is not None for value in (args.output,args.request,args.manifest,args.rebind_material,args.material_rebinds,args.lod_distance)):
            parser.error('Authored verification accepts only its source and optional dump/FF')
        if args.verify_authored_dump:
            if not args.dump or not args.ff:
                parser.error('Authored dump verification requires --dump and --ff')
            result=verify_authored_dump(args.verify_authored_dump,args.dump,args.ff)
        else:
            if args.dump or args.ff:
                parser.error('Dump/FF options require --verify-authored-dump')
            result=verify_authored_stage(args.verify_authored_stage)
    elif not args.output:
        parser.error('Preparation requires --output')
    elif args.dump or args.ff:
        parser.error('Dump/FF options require --verify-authored-dump')
    elif args.export_root:
        if not args.request or not args.manifest or not (args.rebind_material or args.material_rebinds):
            parser.error('Resident export requires --request, --manifest and explicit material rebinds')
        import rigid_export
        rebinds=rigid_export.read_document(args.material_rebinds,256*1024) if args.material_rebinds else None
        result=rigid_export.stage(args.export_root,args.request,args.manifest,args.output,args.rebind_material,args.lod_distance,rebinds=rebinds)
    else:
        if args.request or args.manifest or args.rebind_material or args.material_rebinds or args.lod_distance is not None:
            parser.error('Resident derivation options require --export-root')
        result=stage(args.writer_run,args.output)
    print(json.dumps(result,indent=2))

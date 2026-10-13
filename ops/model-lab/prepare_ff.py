"""Stage original model inputs/CSV only after measured standalone roundtrip."""
import argparse
import hashlib
import json
from pathlib import Path
from prepare_writer import safe_path, PIN

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
    data=json.loads(provenance.read_text(encoding='utf-8-sig'))
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

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--writer-run',type=Path)
    source.add_argument('--export-root',type=Path)
    parser.add_argument('--request',type=Path)
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--rebind-material')
    parser.add_argument('--lod-distance',type=float)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if args.export_root:
        if not args.request or not args.manifest or not args.rebind_material:
            parser.error('Resident export requires --request, --manifest and explicit --rebind-material')
        import rigid_export
        result=rigid_export.stage(args.export_root,args.request,args.manifest,args.output,args.rebind_material,args.lod_distance)
    else:
        if args.request or args.manifest or args.rebind_material or args.lod_distance is not None:
            parser.error('Resident derivation options require --export-root')
        result=stage(args.writer_run,args.output)
    print(json.dumps(result,indent=2))

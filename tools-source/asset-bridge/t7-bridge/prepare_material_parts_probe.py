"""Prepare one finite G3 recipient plan from qualified E5 stock metadata.

Reads text evidence and candidate stat metadata only. Never opens an EXE/FF/XPAK,
creates a retail alias, runs DEFAULT, acquires admission or launches a tool.
"""
import argparse
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath

REFERENCE_PIN=(70998,'90deea83d976a0bc96a16f481362019bcdf1d7c02ff09d131412df1c0dca1f7c')
BUILD_PIN=(372668,'cfeb5610dd5322d9137eaa9804590cf023a865236a1132e95e354919ef23084e')
RECEIPT_PIN=(25651,'e81604ea36272540d2a62df7aaa236dcdd92bb0d04821ab9b2f887636a074a25')
CANDIDATE_PIN=(21963264,'cce8bbb8f068b4897a391880db316bd1d7586f26f7ec0c1cee2316d76c8644b3')
MARKER_PINS={
    'SourceManifest':(331468,'ed972cfad8de6985b9c307f65b56a0fe03de6cba442e590eebdddb0b7869db28'),
    'HostWitness':(606,'9b1879b319d5acf9cbdfaa47322e57bc36f9cc05bb8a2a87dc9ef4e38a5ac061'),
    'ClosureWitness':(1264,'9018cc01cf90db101b291f56affa99c376a22e9adccdde7d8651bb61762c623c'),
    'PartsHeader':(8380,'f2dbec9ad952978ef5d88dafd608a0aef6417fd649b0f04fa7088732c822fbb5'),
    'PartsEntry':(2589,'dd1ed27601e23ba3eace1115b84cfa7c85404497451b8a41eb194e6df9764f4c'),
    'PartsContract':(838,'b01c9c8f57816b26a8a09b72e2799cda5858083bde4a332fdb7d8ed5ccb89e9e')}
CONTROLLERS=('tools-source/asset-bridge/t7-bridge/Run-T7Catalogue.ps1',
    'tools-source/asset-bridge/t7-bridge/T7Catalogue.Profile.ps1',
    'tools-source/asset-bridge/t7-bridge/T7Prepatch.Profile.ps1',
    'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1',
    'ops/Resource-Scheduler.Core.ps1','ops/Resource-Memory.ps1',
    'ops/Resource-RecorderOwnedProcess.Core.ps1','ops/native/ResourceMemory.cs',
    'ops/hud-lab/HudFileIdentity.cs','tools-source/asset-bridge/t7-bridge/T7MaterialParts.Profile.ps1')
EXPORT_FIELDS=('ExportRequest','ExportRequestFile','ExportModelLimitBytes','ExportMeshLimitBytes',
    'SourceCataloguePlan','SourceCatalogueReceipt','SourceCatalogue','ReadbackSources',
    'ResidentMultiSurfaceV2','SelectedXpakProvider','SelectedStreamedRequestMetadata','SelectedStreamedRenderOnlyV2')

def require(value,message):
    if not value:raise ValueError(message)

def key(path):return str(path).replace('/','\\').casefold()

def read_text_pin(path,expected=None):
    path=Path(path)
    require(path.is_absolute() and path==path.resolve(),'Canonical absolute text path required')
    require(path.suffix.lower() in ('.json','.ps1','.py','.cs','.hpp','.inc','.cpp','.rsp'),'Declared source/JSON extension required')
    for parent in (path,*path.parents):
        require(not parent.is_symlink() and not parent.is_junction(),'Reparse text path refused')
    declared_size=path.stat().st_size
    require(0<declared_size<=1024*1024,'Bounded source/JSON text required')
    if expected:require(declared_size==expected[0],'Exact retained text length differs before open')
    with path.open('rb') as stream:
        size=os.fstat(stream.fileno()).st_size
        require(0<size<=1024*1024,'Opened source/JSON size differs')
        if expected:require(size==expected[0],'Exact retained text length differs')
        raw=stream.read(1024*1024+1)
        require(len(raw)==size,'Source/JSON text changed during read')
    raw.decode('utf-8-sig')
    pin=dict(Path=str(path),Bytes=len(raw),SHA256=hashlib.sha256(raw).hexdigest())
    if expected:require((pin['Bytes'],pin['SHA256'])==expected,'Exact retained text identity differs')
    return pin,raw

def derive(reference,controllers,build,receipt,marker,candidate_metadata,run):
    require(reference['Operation']=='ResidentExportV1' and reference['CandidateProfile']=='t7-catalog-message-publication' and
        reference['SelectedStreamedRenderOnlyV2']['Schema']=='iw7.t7-selected-streamed-render-only-plan/2',
        'Exact E5 reference family required')
    require(len(reference['Bootstraps'])==23 and len(reference['InputMetadata'])==29,'Qualified E5 inventory required')
    result=copy.deepcopy(reference)
    for name in EXPORT_FIELDS:result.pop(name,None)
    result.update(Schema='iw7.t7-material-parts-plan/1',Operation='MaterialPartsV1',CandidateProfile='t7-material-parts-v1',
        Arguments=['-t7-iw7-material-parts-v1','mp_freerun_04','p7_fre_platform_cap_02','0'],
        OutputKey='t7_iw7_material_parts_v1',ReportLimitBytes=65536,TraceStderrLimitBytes=16384,
        RunRoot=str(run),WorkingDirectory=str(run/'work'),StageRoot=str(run/'evidence'),
        Image=str(run/'work/t7-zonetool-candidate.exe'),CandidateSource=candidate_metadata['Path'],
        CandidateBytes=CANDIDATE_PIN[0],CandidateSHA256=CANDIDATE_PIN[1],
        BuildPlan=build['pin']['Path'],ExpectedBuildPlanSHA256=BUILD_PIN[1],
        BuildReceipt=receipt['pin']['Path'],ExpectedBuildReceiptSHA256=RECEIPT_PIN[1],
        Runner=controllers[0]['Path'],SelectedMaterialPartsV1=dict(Schema='iw7.t7-material-parts-probe/1',**marker))
    allowed={key(reference['EngineSource']),key(reference['SteamSource']),key(reference['Zone']['Path'])}
    allowed.update(key(p['Path']) for p in reference['Bootstraps'])
    result['InputMetadata']=[copy.deepcopy(p) for p in reference['InputMetadata'] if key(p['Path']) in allowed]
    result['InputMetadata'].insert(0,candidate_metadata)
    require(len(result['InputMetadata'])==27,'Only candidate/engine/Steam/zone and 23 bootstraps may remain')
    retained={key(p['QualificationScript']['Path']) for p in reference['Bootstraps']}
    retained.update(key(p['QualificationReceipt']['Path']) for p in reference['Bootstraps'])
    retained.update(key(reference['SharedQualification'][name]['Path']) for name in ('Script','Plan','Receipt'))
    bindings=[copy.deepcopy(p) for p in reference['Bindings'] if not p['IsText'] or key(p['Path']) in retained]
    candidates=[p for p in bindings if key(p['Path'])==key(reference['CandidateSource'])]
    require(len(candidates)==1,'One old candidate binding required')
    candidates[0].update(Path=candidate_metadata['Path'],Bytes=CANDIDATE_PIN[0],SHA256=CANDIDATE_PIN[1])
    text=[build['pin'],receipt['pin'],*controllers,*marker.values()]
    profile=build['data']['BuildProfile']
    text.extend(profile[name] for name in ('Wiring','PreparedMain','BaseBuildPlan','BaseBuildReceipt','LinkResponse'))
    dependency=[p for p in receipt['data']['Stages'][0]['Artifacts'] if PureWindowsPath(p['Path']).name=='dependencies.json']
    require(len(dependency)==1,'One admitted main dependency text required');text.extend(dependency)
    bindings.extend(dict(p,IsText=True) for p in text)
    require(len({key(p['Path']) for p in bindings})==len(bindings)==89,'Exact unique G3 binding set required')
    result['Bindings']=bindings
    result['OutputLimitBytes']=16977344+21737352+235600+64*1024**2+CANDIDATE_PIN[0]+sum(p['Bytes'] for p in reference['Bootstraps'])
    return result

def candidate_stat(path):
    # Operational stat only; content is verified later by the admitted recipient.
    stat=path.stat()
    require(stat.st_size==CANDIDATE_PIN[0] and stat.st_file_attributes==32,'Exact candidate length/Archive metadata required')
    seconds,ns=divmod(stat.st_mtime_ns,10**9)
    stamp=datetime.datetime.fromtimestamp(seconds,datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')+f'.{ns//100:07d}Z'
    return dict(Path=str(path),Bytes=stat.st_size,Attributes='Archive',LastWriteUtc=stamp)

def prepare(args):
    source=Path(__file__).resolve().parents[3]
    source_pin,source_raw=read_text_pin(source/'source-workspace.json')
    workspace=json.loads(source_raw)
    require(workspace.get('schema')=='iw7.source-workspace/1' and workspace.get('product')=='x64-zt-extensions',
        'Committed composed recipient source package required')
    reference_pin,raw=read_text_pin(args.reference,REFERENCE_PIN);reference=json.loads(raw)
    build_pin,raw=read_text_pin(args.build_plan,BUILD_PIN);build=json.loads(raw)
    receipt_pin,raw=read_text_pin(args.build_receipt,RECEIPT_PIN);receipt=json.loads(raw)
    marker_paths=dict(SourceManifest=args.build_manifest,HostWitness=args.host_witness,ClosureWitness=args.closure_witness,
        PartsHeader=Path(args.build_manifest).parent/'tools-source/asset-bridge/t7-iw7/selected_material_parts_observation.hpp',
        PartsEntry=Path(args.build_manifest).parent/'tools-source/asset-bridge/t7-iw7/native_material_parts.inc',
        PartsContract=Path(args.build_manifest).parent/'tools-source/asset-bridge/t7-iw7/material-parts-source-contract.json')
    marker={name:read_text_pin(path,MARKER_PINS[name])[0] for name,path in marker_paths.items()}
    controllers=[read_text_pin(source/name)[0] for name in CONTROLLERS]
    source_rows={row['path']:row for row in workspace['files']}
    for name,pin in zip(CONTROLLERS,controllers):
        row=source_rows.get(name,{})
        require((row.get('bytes'),row.get('sha256'))==(pin['Bytes'],pin['SHA256']),'Receiver source differs from its manifest')
    candidate=[p for stage in receipt['Stages'] for p in stage['Artifacts'] if p['Path'].endswith('\\zonetool-t7.exe')]
    require(len(candidate)==1 and (candidate[0]['Bytes'],candidate[0]['SHA256'])==CANDIDATE_PIN,'Exact admitted candidate tuple required')
    run=Path(args.run);output=Path(args.output)
    require(run.is_absolute() and run==run.resolve() and run.parent==source/'runtime' and
        run.name.startswith('t7-material-parts-') and not run.exists(),'Fresh source-owned parts runtime required')
    require(output.is_absolute() and output==output.resolve() and not output.exists(),'Fresh control output required')
    plan=derive(reference,controllers,dict(pin=build_pin,data=build),dict(pin=receipt_pin,data=receipt),
        marker,candidate_stat(Path(candidate[0]['Path'])),run)
    # Validate every source/JSON binding now. No opaque binding is read/hashed.
    for pin in plan['Bindings']:
        if pin['IsText']:read_text_pin(pin['Path'],(pin['Bytes'],pin['SHA256']))
    entry=source/'tools-source/asset-bridge/t7-bridge/Invoke-T7CatalogueHost.ps1'
    host_pins=[read_text_pin(path)[0] for path in (entry,source/'tools-source/asset-bridge/t7-bridge/T7CatalogueHost.Core.ps1',source/'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1')]
    shells=[p for p in plan['Bindings'] if not p['IsText'] and PureWindowsPath(p['Path']).name=='pwsh.exe']
    require(len(shells)==1,'One retained bundled host binding required')
    raw=(json.dumps(plan,indent=2)+'\n').encode();require(len(raw)<=128*1024,'Plan exceeds existing recipient limit')
    plan_path=output/'plan.local.json';plan_sha=hashlib.sha256(raw).hexdigest()
    host=dict(Schema='iw7.t7-material-parts-host/1',PlanPath=str(plan_path),PlanSHA256=plan_sha,RunRoot=str(run),
        HostImage=shells[0]['Path'],SourcePins=host_pins,PreservedProcesses=[])
    host_raw=(json.dumps(host,indent=2)+'\n').encode();host_path=output/'host-contract.local.json';host_sha=hashlib.sha256(host_raw).hexdigest()
    # No alias or native output is prepared. Directories are ordinary empty roots.
    output.mkdir(parents=True,exist_ok=False);run.mkdir(parents=True,exist_ok=False)
    for name in ('work','evidence','temp'):(run/name).mkdir()
    with plan_path.open('xb') as file:file.write(raw)
    with host_path.open('xb') as file:file.write(host_raw)
    return dict(Plan=str(plan_path),PlanBytes=len(raw),PlanSHA256=plan_sha,HostContract=str(host_path),HostContractSHA256=host_sha,
        NativeCommand=dict(Executable=host['HostImage'],Arguments=['-NoLogo','-NoProfile','-NoExit','-File',str(entry),'-PlanPath',str(plan_path),
            '-PlanSHA256',plan_sha,'-RunRoot',str(run),'-HostContractPath',str(host_path),'-HostContractSHA256',host_sha,'-Run']),
        ReferencePlan=reference_pin,ReceiverSourceManifest=source_pin,ReceiverSourceRevision=workspace['revisions']['x64-zt-extensions'],
        Bindings=89,InputMetadata=27,NativeExecuted=False,OpaqueContentRead=False,LeaseAcquired=False,Ready=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('reference','build-plan','build-receipt','build-manifest','host-witness','closure-witness','output','run'):
        parser.add_argument('--'+name,type=Path,required=True)
    print(json.dumps(prepare(parser.parse_args()),indent=2))

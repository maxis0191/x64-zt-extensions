"""Prepare the fixed ten-stage player-definition Source cohort after Analysis GO.

Default validates bounded Source/metadata and reports expected no effects. The
explicit --prepare writes Source only; its caller must provide the separately
reviewed admitted H1 Analysis context. No compiler, PE/PDB, SDK or retail IO,
process launch, admission, host adoption or candidate measurement exists here.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import prepare_module as support

HERE = Path(__file__).resolve().parent
PLAN_SHA = '9aacc6cd93bbf2404a7351af1b427bc7db43b8cd6aa7ccac6235009bb465d423'
QUALIFICATION_SHA = 'a89dea0685eda05e1386aa91530c65f28d278b8cd8e8e9811062968d2705e7bc'
CAPSULE_SHA = '3c0cb0218b7318643ef2e8f03cf01c1788fdaf50ca39d0391aff89d6cd622540'
NATIVE_HEADER = (354227, 'adb62e481a533d27f97829e64d9038b13c5e9cd88e6b4aee8cac339b9492921a')
FIXTURE_FILES = ('test_definition_readset.cpp', 'native_definition_access.hpp', 'native_definition_readset.hpp',
                 'native_definition_fields.inc', 'native_definition_gate.hpp')
COPY_FILES = ('native_bounded_name.hpp','native_player_cli.hpp','test_bounded_name.cpp','test_player_cli.cpp',
              'native_primary_guard.hpp','test_primary_guard.cpp',*FIXTURE_FILES)
SUPPORT_FILES = ('prepare_module.py','generate_definition_readset.py','native_player_templates.inc','native_player_cli.inc',
                 'Run-PlayerTemplateBuild.ps1','prepare_definition_cohort.py',*COPY_FILES)
TEXT_SUFFIXES = {'.json','.py','.ps1','.cs','.hpp','.cpp','.inc','.rsp','.h','.hh','.inl','.vcxproj','.txt'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def key(path):
    return str(PureWindowsPath(path)).casefold()


def safe_path(path):
    value = str(path).replace('\\','/')
    require(not value.casefold().startswith(('//?/','//./','/??/','//??/')) and ':' not in value[2:] and
            not any(ord(c)<32 or c=='"' for c in value) and not PureWindowsPath(path).is_reserved(), 'Ordinary lexical path required')
    result=Path(path)
    require(result.is_absolute(), 'Absolute path required')
    return result


def read_text(path, expected=None):
    # Opaque suffix refusal precedes ALL filesystem queries.
    require(Path(path).suffix.lower() in TEXT_SUFFIXES, 'Source/metadata suffix required before filesystem IO')
    path=safe_path(path)
    require(not any(p.is_symlink() or p.is_junction() for p in (path,*path.parents)), 'Reparse Source ancestry refused')
    with path.open('rb') as stream:
        raw=stream.read(support.CAP+1)
    require(0<len(raw)<=support.CAP and b'\0' not in raw, 'Bounded Source text required')
    raw.decode('utf-8-sig',errors='strict')
    pin=dict(Path=str(path),Bytes=len(raw),SHA256=hashlib.sha256(raw).hexdigest(),IsText=True)
    require(expected is None or (pin['SHA256']==expected['SHA256'] and pin['Bytes']==expected['Bytes']), 'Exact Source pin differs')
    return pin,raw


def json_source(raw):
    def pairs(items):
        result={}
        for name,value in items:
            require(name not in result,'Duplicate Source JSON key')
            result[name]=value
        return result
    def constant(_):
        raise ValueError('Nonfinite Source JSON number')
    value=json.loads(raw.decode('utf-8-sig'),object_pairs_hook=pairs,parse_constant=constant)
    require(type(value) is dict,'Source JSON object required')
    return value


def write_text(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)
    return dict(Path=str(path),Bytes=len(raw),SHA256=hashlib.sha256(raw).hexdigest(),IsText=True)


def definition_response(prepared,run):
    stage=run/'definition-compile'
    return ('/nologo /std:c++17 /EHsc /MT /DNDEBUG /W4 /WX /Zi /Od /Y- /I"'+str(prepared)+
        '" /FI"'+str(prepared/'native_definition_fixture_binding.hpp')+'" /Fo"'+str(stage/'definition.obj')+
        '" /Fe"'+str(stage/'definition.exe')+'" /Fd"'+str(stage/'compile.pdb')+'" /sourceDependencies "'+
        str(stage/'dependencies.json')+'" "'+str(prepared/'test_definition_readset.cpp')+
        '" /link /INCREMENTAL:NO /DEBUG /PDB:"'+str(stage/'definition.pdb')+'"\n')


def binding_header(native_header):
    return '#pragma once\n#define IW7_NATIVE_STRUCTS_HEADER "'+str(native_header).replace('\\','/')+'"\n'


def historical_reference(base):
    plan_pin,raw=read_text(base/'cohort-source-plan.json')
    require(plan_pin['SHA256']==PLAN_SHA,'Exact historical closed J Source plan required')
    parent=json_source(raw)
    qual_pin,raw=read_text(base/'qualification-handoff.local.json')
    require(qual_pin['SHA256']==QUALIFICATION_SHA,'Exact historical closed J qualification text required')
    qualified=json_source(raw)
    require(qualified['Status']=='PassedClosed' and qualified['CPPQualified'] is True and qualified['NativeChecks']==62 and
            qualified['ManagedPTYExitCode']==0 and qualified['FreshPresentIDs']==[] and qualified['FreshLeases']==0,
            'Historical J must be closed, never inherited as current CPP proof')
    proof_pins=[]
    for expected in qualified['Proofs']:
        pin,_=read_text(expected['Path'],expected);proof_pins.append(pin)
    cap_pin,cap=read_text(base/'invoke-cohort.local.ps1')
    require(cap_pin['SHA256']==CAPSULE_SHA,'Original reviewed H1 CPP capsule Source required')
    return parent,[plan_pin,qual_pin,cap_pin,*proof_pins],cap.decode('utf-8-sig')


def source_inputs(source,revision,manifest_sha):
    manifest_pin,raw=read_text(source/'source-workspace.json')
    require(manifest_pin['SHA256']==manifest_sha,'Exact composed Source manifest required')
    workspace=json_source(raw)
    require(workspace['schema']=='iw7.source-workspace/1' and workspace['product']=='x64-zt-extensions' and
            type(workspace['files']) is list and re.fullmatch('[0-9a-f]{40}',revision) and workspace['revisions']['x64-zt-extensions']==revision,
            'Exact reviewed Source revision required')
    require(HERE==source/'tools-source/asset-bridge/weapon-export','Execute the builder from the exact composed Source package')
    pins=[manifest_pin];texts={}
    for name in SUPPORT_FILES:
        pin,raw=read_text(HERE/name)
        rows=[p for p in workspace['files'] if p['path']==(HERE/name).relative_to(source).as_posix()]
        require(len(rows)==1 and rows[0]['commit']==revision and rows[0]['sha256']==pin['SHA256'] and rows[0]['bytes']==pin['Bytes'],
                'Owned reviewed Source input differs: '+name)
        pins.append(pin);texts[name]=raw.decode('utf-8-sig').replace('\r\n','\n').encode()
    return workspace,pins,texts


def derive(parent,prepared,run,revision,runner_pin,prepared_pins,source_pins,native_header,base_plan_pin):
    require(parent['NativeSourcePin']==support.SOURCE_PIN and parent['PairProfileCLI'] is True and
            parent['PrimaryGuardFixture'] is True and len(parent['RetainedInputPins'])==1151 and
            len(parent['ParentBindings'])==171 and parent['RetainedObjects']==412 and parent['LinkedObjectCount']==413,
            'Fixed historical declarations required')
    plan=copy.deepcopy(parent)
    old_prepared=str(Path(parent['PreparedRoot']));old_run=str(Path(parent['RunRoot']))
    old_support=Path(parent['RunnerBinding']['Path']).parent
    plan.update(RunRoot=str(run),PreparedRoot=str(prepared),PairDefinitionsCLI=True,RunnerBinding=runner_pin,
        Status='SourceOnlyUnexecuted',
        WeaponSourceMerge=revision,CLIWireMerge=revision,PreparedBindings=prepared_pins,
        ParentCPPSourcePlan=base_plan_pin,ParentCPPQualificationInherited=False,ParentCPPQualifiedOnlyForJ=True,
        SourceDelta='Neutral definitions172 Source recipe. Historical J metadata only; no CPP/ABI/lifetime/extraction qualification inherited.',
        CandidateBytes=None,CandidateSHA256=None,DefinitionChecksAuthored=100,DefinitionChecksExecuted=False,
        NativeInputsRead=False,NativeTypesLoaded=False,LeaseAcquired=False,CPPPassed=False,
        NameChecksExecuted=False,ArgvChecksExecuted=False,PrimaryChecksExecuted=False,CandidateExecuted=False,
        TemplatesObserved=False,FullDefinitionsObserved=False,WeaponReady=False,PhysicsQualified=False,PAPTransactionQualified=False,Ready=False)
    plan.pop('ParentCPPQualifiedOnlyForI',None)
    plan.pop('ParentCPPStatus',None)
    for stage in plan['Stages']:
        stage['Image']=str(Path(stage['Image'])).replace(old_run,str(run))
        require(all(type(arg) is str and arg.startswith('@') for arg in stage['Arguments']),'Only fixed response-file arguments permitted')
        stage['Arguments']=['@'+str(Path(arg[1:])).replace(old_prepared,str(prepared)) for arg in stage['Arguments']]
    plan['Stages'][3].update(ExpectedChecks=28,ExpectedStdout='IW7_PLAYER_TEMPLATE_ARGV_CHECKS=28\n')
    plan['Stages'][6:6]=[
        dict(Name='definition-compile',Stage='Compile',Image=plan['Compiler'],Arguments=['@'+str(prepared/'definition.rsp')],
             DeadlineSeconds=120,Artifacts=['definition.obj','definition.exe','definition.pdb','compile.pdb','dependencies.json']),
        dict(Name='definition-test',Stage='Probe',Image=str(run/'definition-compile/definition.exe'),Arguments=[],DeadlineSeconds=15,
             Artifacts=[],ExpectedChecks=100,ExpectedStdout='IW7_PLAYER_DEFINITION_READSET_CHECKS=100\n')]
    plan['DefinitionFixture']=dict(Schema='iw7.player-definition-fixture-source/1',
        Files=[p for p in prepared_pins if Path(p['Path']).name in FIXTURE_FILES],NativeHeader=native_header)
    coverage=[]
    for row in parent['OwnDirectIncludeCoverage']:
        row=copy.deepcopy(row);row['Path']=str(Path(row['Path'])).replace(old_prepared,str(prepared));coverage.append(row)
    for name in (*FIXTURE_FILES,'native_definition_fixture_binding.hpp'):
        path=str(prepared/name)
        if not any(key(row['Path'])==key(path) for row in coverage):coverage.append(dict(Include=name,Path=path,Pinned=True,Consumer='test_definition_readset.cpp'))
    plan['OwnDirectIncludeCoverage']=coverage
    sources={key(p['Path']):p for p in parent['SourceBindings'] if not Path(p['Path']).is_relative_to(old_support)}
    for pin in source_pins:
        identity=key(pin['Path']);require(identity not in sources or sources[identity]['SHA256']==pin['SHA256'],'Source binding conflict')
        sources[identity]=pin
    plan['SourceBindings']=list(sources.values())
    for name in ('Providers','Environment','ParentBindings','RetainedInputPins','ExcludedObject','ObservedTransitiveSourcePins'):
        require(plan[name]==parent[name],'Historical expected declarations changed: '+name)
    return plan


def prepare(source,revision,manifest_sha,base,native,output,execute=False):
    output=safe_path(output);run=output/'runtime/cpp-WAIT-ROOT';prepared=output/'prepared'
    require(not output.exists() and not any(p.is_symlink() or p.is_junction() for p in output.parents),'Fresh ordinary Source output required')
    workspace,pins,texts=source_inputs(source,revision,manifest_sha)
    parent,proof_pins,capsule=historical_reference(base);pins.extend(proof_pins)
    expected_native=[p for p in parent['RetainedInputPins'] if key(p['Path'])==key(native/support.definition_readset.NATIVE/'structs.hpp')]
    require(len(expected_native)==1 and (expected_native[0]['Bytes'],expected_native[0]['SHA256'])==NATIVE_HEADER,'Original declared native header required')
    native_header=dict(expected_native[0],Path=str(native/support.definition_readset.NATIVE/'structs.hpp'))
    default=dict(Schema='iw7.player-definition-recipe-default/1',SourceRevision=revision,Stages=10,ChecksAuthored=[8,28,36,100],
        ExpectedNoEffects=True,SourceOutputCreated=False,RunRootCreated=False,NativeInputsRead=False,SDKInputsRead=False,
        NativeTypesLoaded=False,NativeSourceTextsRead=False,LeaseAcquired=False,ProcessStarted=False,CPPExecuted=False,CandidateBytes=None,CandidateSHA256=None,Ready=False)
    if not execute:return default
    report=support.stage(native,prepared,player_cli=True)
    require(report['build_extension']['definition_fixture_checks_authored']==100 and not report['compiled'],'Actual uncompiled100 fixture profile required')
    prepared_pins=[]
    for path in (prepared/support.NATIVE_PATH,prepared/'module-source.json'):
        pin,_=read_text(path);prepared_pins.append(pin)
    for name in COPY_FILES:prepared_pins.append(write_text(prepared/name,texts[name]))
    prepared_pins.append(write_text(prepared/'native_definition_fixture_binding.hpp',binding_header(native_header['Path']).encode()))
    old_root=str(base);new_root=str(output)
    for name in ('name','argv','primary','iw7','link'):
        expected=next(p for p in parent['PreparedBindings'] if key(p['Path'])==key(base/'prepared'/(name+'.rsp')))
        pin,raw=read_text(expected['Path'],expected);pins.append(pin)
        raw=raw.decode('utf-8-sig').replace(old_root,new_root).replace('\r\n','\n').encode()
        prepared_pins.append(write_text(prepared/(name+'.rsp'),raw))
    prepared_pins.append(write_text(prepared/'definition.rsp',definition_response(prepared,run).encode()))
    link=next(read_text(p['Path'])[1].decode() for p in prepared_pins if Path(p['Path']).name=='link.rsp')
    objects=re.findall(r'^"([^"\r\n]+\.obj)"$',link,re.M|re.I);retained={key(p['Path']) for p in parent['RetainedInputPins']}
    fresh=key(run/'iw7/iw7-player-cli.obj')
    require(len(objects)==len(set(map(key,objects)))==413 and sum(key(p)==fresh for p in objects)==1 and
            all(key(p) in retained for p in objects if key(p)!=fresh),'Same412 expected objects plus one future fresh TU required')
    runner_pin=next(p for p in pins if Path(p['Path']).name=='Run-PlayerTemplateBuild.ps1')
    base_pin=next(p for p in proof_pins if p['SHA256']==PLAN_SHA)
    plan=derive(parent,prepared,run,revision,runner_pin,prepared_pins,pins,native_header,base_pin)
    plan_pin=write_text(output/'cohort-source-plan.json',(json.dumps(plan,indent=2)+'\n').encode())
    capsule=capsule.replace(str(base),str(output)).replace(str(Path(parent['RunnerBinding']['Path'])),str(HERE/'Run-PlayerTemplateBuild.ps1')).replace(PLAN_SHA,plan_pin['SHA256'])
    cap_pin=write_text(output/'invoke-cohort.local.ps1',capsule.encode())
    default.update(Schema='iw7.player-definition-recipe-source/1',ExpectedNoEffects=False,NativeSourceTextsRead=True,SourceOutputCreated=True,Plan=plan_pin,Capsule=cap_pin,
        PreparedBindings=len(prepared_pins),SourceBindings=len(plan['SourceBindings']),HistoricalJOnly=True)
    write_text(output/'recipe-source-receipt.json',(json.dumps(default,indent=2)+'\n').encode())
    return default


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','base','native-source-root','output'):parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--source-revision',required=True);parser.add_argument('--source-manifest-sha256',required=True)
    parser.add_argument('--prepare',action='store_true')
    args=parser.parse_args()
    print(json.dumps(prepare(args.source,args.source_revision,args.source_manifest_sha256,args.base,args.native_source_root,args.output,args.prepare)))


if __name__=='__main__':main()

"""Prepare a private three-TU build. Reads text/metadata only; never runs native code."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import prepare_cli
import prepare_prepatch
import prepare_catalog_trace

HERE = Path(__file__).resolve().parent
CL_LOG_SHA = 'a7083ce5b9ba2fe1421c4f8733cf1d1e0b286549dbc55a44f3ef30ceb3c05333'
LINK_LOG_SHA = '70455d2f32a9b034dda20fbaf48443ee68a02e552381edbf88b19d219f1f66b2'
SEED_SHA = 'f52867e7c26d05466ba57d72eef601d42376c1109dfcf61f219a1a028229f388'
CL_SHA = 'fe251ef50a1545b1b0835ee17b1e785459712b38d79e45b5c1d3d28970a36619'
JOB_SHA = '5f613ebb83019dbf4bfa4f6a93c5329098343729b70acc2cfa70aa8b64f195f8'
UNITS = tuple(zip(prepare_cli.PATHS[:3], ('main.obj', 'zonetool11.obj', 'xpak.obj'),
                  ('main.cpp', 'zonetool.cpp', 'common/xpak.cpp')))
SDK_PINS = {'rc.exe': (55640, '43da1503c262c30894c851589bf0155f8365d77e63a5f7bc13982320e3a6b42d'),
            'rcdll.dll': (264536, '9a11e4759adc48abe1fa9e3082ad7db4b53f4d6d77701c13729f4ffd47ae934c')}


def require(ok, message):
    if not ok: raise ValueError(message)


def key(path): return str(PureWindowsPath(path)).casefold()


def path_checked(path):
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        require(not part.is_symlink() and not part.is_junction(), 'Reparse path refused')
    return path


def text_pin(path, limit=1024*1024, expected=None):
    path = path_checked(path)
    before = path.stat()
    require(path.is_file() and 0 < before.st_size <= limit, 'Bounded text input required')
    raw = path.read_bytes()
    after = path.stat()
    require(len(raw) == before.st_size and (before.st_ino, before.st_mtime_ns, before.st_size) ==
            (after.st_ino, after.st_mtime_ns, after.st_size), 'Text input changed')
    digest = hashlib.sha256(raw).hexdigest()
    require(expected is None or digest == expected, 'Text pin differs: '+str(path))
    return raw, {'Path': str(path), 'Bytes': len(raw), 'SHA256': digest}


def quote(value):
    require(not any(c in str(value) for c in '\r\n\0"'), 'Unsafe response argument')
    return '"'+str(value)+'"'


def replace_one(pattern, replacement, text):
    result, count = re.subn(pattern, lambda _: replacement, text)
    require(count == 1, 'Expected one exact recorded field: '+pattern)
    return result


def command_payloads(cl_text, link_text, native, prepared, run):
    native, prepared, run = map(PureWindowsPath, (native, prepared, run))
    lines = cl_text.splitlines()
    payloads = {}
    for source, obj, relative in UNITS:
        original = native/source
        matches = [i for i, row in enumerate(lines) if row.startswith('^') and key(row[1:]) == key(original)]
        require(len(matches) == 1, 'Exact source record required')
        command = lines[matches[0]+1]
        for flag in ('/c ', '/MT ', '/O1 ', '/Zi ', '/W4 ', '/WX ', '/fp:precise ', '/std:c++23preview '):
            require(flag in command, 'Original compiler contract differs')
        require('/MP' not in command, 'Parallel compiler refused')
        command = replace_one(r'/Yu"[^"]+"', '/Y-', command)
        command = replace_one(r'/Fp"[^"]+"', '', command)
        stage = run/obj.removesuffix('.obj')
        command = replace_one(r'/Fo"[^"]+"', '/Fo'+quote(stage/obj), command)
        command = replace_one(r'/Fd"[^"]+"', '/Fd'+quote(stage/'compile.pdb'), command)
        command = replace_one(r'\s+"?'+re.escape(lines[matches[0]][1:])+r'"?\s*$',
            ' /I'+quote(original.parent)+' /sourceDependencies '+quote(stage/'dependencies.json')+' '+quote(prepared/relative), command)
        # Keep each /D and argument on the SAME line. Sound E proved that
        # serializing /D on its own response line causes MSVC D8004.
        command = '/I'+quote(prepared)+' '+command
        require('/fp:precise' in command and '/Yu' not in command and '/Fp' not in command, 'PCH/precision differs')
        require(len(re.findall(r'/D [A-Za-z_][A-Za-z0-9_]*', command)) == 12, 'Twelve retained definitions required')
        payloads[obj+'.rsp'] = (command+'\n').encode()
    rows = link_text.splitlines()
    require(len(rows) == 415 and rows[0].startswith('^'), 'Exact 413-object link record required')
    flags, objects = rows[1], rows[2:]
    require(all(re.fullmatch(r'"[^"\r\n]+\.OBJ"', o) for o in objects), 'Ordered object paths required')
    require(len({key(o[1:-1]) for o in objects}) == 413, 'Duplicate object input')
    replaced = []
    for _, obj, _ in UNITS:
        indices = [i for i, o in enumerate(objects) if PureWindowsPath(o[1:-1]).name.casefold() == obj]
        require(len(indices) == 1, 'One replacement object required')
        index = indices[0]; replaced.append(objects[index][1:-1])
        objects[index] = quote(run/obj.removesuffix('.obj')/obj)
    for flag, name in (('OUT', 'zonetool-t7.exe'), ('PDB', 'zonetool-t7.pdb'), ('IMPLIB', 'zonetool-t7.lib')):
        flags = replace_one('/'+flag+r':"[^"]+"', '/'+flag+':'+quote(run/'link'/name), flags)
    require('/INCREMENTAL:NO' in flags and '/manifest:embed' in flags, 'Link/manifest contract differs')
    libraries = re.findall(r'(?i)(?<!:)"([^"\r\n]+\.lib)"', flags)
    resources = re.findall(r'(?i)"([^"\r\n]+\.res)"', flags)
    require(len(libraries) == 18 and len(resources) == 1, '18 project libraries and one resource required')
    payloads['link.rsp'] = (flags+'\n'+'\n'.join(objects)+'\n').encode()
    return payloads, replaced


def read_records(text):
    records = {}; current = None
    for line in text.splitlines():
        if line.startswith('^'):
            current = key(line[1:]); require(current not in records, 'Duplicate dependency record'); records[current] = []
        elif line:
            require(current is not None, 'Dependency without record'); records[current].append(line)
    return records


def reuse_compilation(prior_plan_raw, receipt_raw, payloads, run, *, recompile_main=False, catalog_trace=False):
    """Bind successful sub-stages of the retained failed group, never relabel it."""
    prior = json.loads(prior_plan_raw); receipt = json.loads(receipt_raw)
    require(prior['Schema'] == 'iw7.t7-minimal-build-plan/1' and
            receipt['Schema'] == 'iw7.t7-minimal-build/1' and
            receipt['PlanSHA256'] == hashlib.sha256(prior_plan_raw).hexdigest() and
            receipt['Status'] == 'Failed' and receipt['TreeClosureConfirmed'] is True and
            receipt['LeaseReleased'] is True and receipt['Quarantined'] is False,
            'Exact failed, closed prior group required')
    stages = receipt['Stages']
    require([s['Name'] for s in stages] == ['helper','probe','main','zonetool11','xpak','link'], 'Prior six-stage identity differs')
    require(all(s['ExitCode'] == 0 and s['TreeClosureConfirmed'] is True for s in stages[:5]) and
            stages[1]['Checks'] == 51, 'Successful closed compilation and exact 51-check probe required')
    prior_bindings = {key(p['Path']):p for p in prior['Bindings']}
    prepared = PureWindowsPath(prior['PreparedRoot']); old_root = PureWindowsPath(prior['RunRoot'])
    expected_payloads = {'prepared/'+name for name in ('main.cpp','zonetool.cpp','common/xpak.cpp',
        'common/xpak.hpp','t7_iw7_resident_model.hpp','t7_asset_name.hpp','test_t7_asset_name.cpp')}
    require(not catalog_trace or recompile_main, 'Catalogue trace requires a fresh main')
    if recompile_main and not catalog_trace: expected_payloads.add('prepared/'+prepare_prepatch.HELPER)
    require({n for n in payloads if n.startswith('prepared/')} == expected_payloads,
            'Exact native payload inventory required for reuse')
    old_text = []
    for name, raw in payloads.items():
        if not name.startswith('prepared/'): continue
        if recompile_main and not catalog_trace and name == 'prepared/'+prepare_prepatch.HELPER:
            require(0 < len(raw) <= 64*1024, 'Bounded pre-patch helper required')
            continue
        path = prepared/name.removeprefix('prepared/')
        pin = prior_bindings.get(key(path))
        if recompile_main and name == 'prepared/main.cpp':
            require(pin and pin['SHA256'] != hashlib.sha256(raw).hexdigest(),
                    'Diagnostic main must differ from retained non-instrumented main')
            old_text.append(pin)
            continue
        require(pin and pin['Bytes'] == len(raw) and pin['SHA256'] == hashlib.sha256(raw).hexdigest(),
                'Native source/header/fixture differs from compiled prior stage')
        old_text.append(pin)
    inputs = []
    reused_units = tuple(u for u in UNITS if not recompile_main or u[1] != 'main.obj')
    required = {'helper':['native_probe.obj','native_probe.exe','native_probe.pdb','dependencies.json'],
                **{obj[:-4]:[obj,'compile.pdb','dependencies.json'] for _,obj,_ in reused_units}}
    for stage in stages:
        if stage['Name'] not in required: continue
        expected = {key(old_root/stage['Name']/name) for name in required[stage['Name']]}
        require({key(p['Path']) for p in stage['Artifacts']} == expected, 'Prior artifact inventory differs')
        for pin in stage['Artifacts']:
            require(type(pin['Bytes']) is int and 0 < pin['Bytes'] <= 32*1024**2 and
                    re.fullmatch('[0-9a-f]{64}',pin['SHA256']), 'Prior artifact pin invalid')
            inputs.append(pin)
    response = payloads['link.rsp'].decode()
    for _, obj, _ in reused_units:
        source = quote(PureWindowsPath(run)/obj[:-4]/obj)
        require(response.splitlines().count(source) == 1, 'One new object path required before reuse')
        response = response.replace(source+'\n', quote(old_root/obj[:-4]/obj)+'\n')
    payloads['link.rsp'] = response.encode()
    return {'OriginalStatus':'Failed','SourcePlanSHA256':receipt['PlanSHA256'],
            'ReceiptSHA256':hashlib.sha256(receipt_raw).hexdigest(),'Checks':51,
            'RecompiledMain':recompile_main,
            'StageRoots':[str(old_root/obj[:-4]) for _,obj,_ in reused_units]}, inputs, old_text


def prepare(args):
    source, e7, output, run, adapter, providers, job = [path_checked(getattr(args, n)) for n in
        ('source', 'e7', 'output', 'run', 'adapter', 'providers', 'job')]
    runtime = HERE.parents[2]/'runtime'
    require(output.parent == runtime and run.parent == runtime and output != run and
            not output.exists() and not run.exists(), 'Separate fresh owned runtime roots required')
    text_inputs = []
    def read(path, limit=1024*1024, expected=None):
        raw, pin = text_pin(path, limit, expected); text_inputs.append(pin); return raw
    cl = read(e7/'obj/tlog/CL.command.1.tlog', 4*1024**2, CL_LOG_SHA).decode('utf-16')
    link = read(e7/'obj/tlog/link.command.1.tlog', 256*1024, LINK_LOG_SHA).decode('utf-16')
    payloads, replaced = command_payloads(cl, link, source, output/'prepared', run)
    _, patched = prepare_cli.render(source)
    prepatch_helper = getattr(args, 'prepatch_helper', None)
    catalog_callers = getattr(args, 'catalog_callers', False)
    catalog_exit = bool(getattr(args, 'catalog_exit', False) or catalog_callers)
    catalog_trace = bool(getattr(args, 'catalog_trace', False) or catalog_exit)
    require(sum(map(bool, (prepatch_helper, getattr(args, 'catalog_trace', False),
                          getattr(args, 'catalog_exit', False), catalog_callers))) <= 1,
            'Pre-patch, catalogue trace, exit-context and caller profiles are exclusive')
    require(bool(getattr(args, 'ordinary_plan', None)) == catalog_trace and
            bool(getattr(args, 'ordinary_receipt', None)) == catalog_trace,
            'Catalogue trace requires both ordinary D2 text proofs')
    recompile_main = bool(prepatch_helper or catalog_trace)
    if recompile_main:
        require(args.reuse_plan and args.reuse_compile_receipt, 'Main rebuild must reuse qualified prior compilation')
    if prepatch_helper:
        payloads['prepared/'+prepare_prepatch.HELPER] = read(prepatch_helper,64*1024)
        patched[prepare_cli.PATHS[0]] = prepare_prepatch.wire_main(patched[prepare_cli.PATHS[0]])
    for path, _, relative in UNITS: payloads['prepared/'+relative] = patched[path].encode()
    payloads['prepared/common/xpak.hpp'] = patched[prepare_cli.PATHS[3]].encode()
    contract = json.loads(read(HERE/'cli-source-contract.json'))
    external = contract['external_adapter']
    for name, pin in [('t7_iw7_resident_model.hpp', external), ('t7_asset_name.hpp', external['required_sibling']),
                      ('test_t7_asset_name.cpp', external['native_boundary_fixture'])]:
        raw = read(adapter/name).decode().replace('\r\n', '\n').encode()
        require(hashlib.sha256(raw).hexdigest() == pin['lf_sha256'] and len(raw) == pin['lf_bytes'], 'Exact conversion header/fixture required')
        payloads['prepared/'+name] = raw
    for name, pin in contract['files'].items():
        raw = read(HERE/name).decode().replace('\r\n', '\n').encode()
        require(hashlib.sha256(raw).hexdigest() == pin['lf_sha256'], 'CLI source contract differs')
    for name in ('prepare_build.py', 'prepare_prepatch.py', 'Run-T7Build.ps1', 'T7Build.Profile.ps1'):
        read(HERE/name)
    if catalog_trace: read(HERE/'prepare_catalog_trace.py')
    read(HERE.parent/'recipient/script-names/prepare_observer.py')
    roles = {'Core': 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1',
             'CompilerCore': 'tools-source/asset-bridge/h1-fixture/H1Native.Compiler.ps1',
             'ObserverSource': 'tools-source/asset-bridge/h1-fixture/H1Native.JobMembers.cs',
             'CompilerPolicySource': 'tools-source/asset-bridge/surfaces/MaterialV2.Compiler.ps1',
             'Scheduler': 'ops/Resource-Scheduler.Core.ps1'}
    for name in (*roles.values(), 'ops/Resource-Memory.ps1', 'ops/native/ResourceMemory.cs',
                 'ops/Resource-RecorderOwnedProcess.Core.ps1'):
        read(providers/name)
    seed = json.loads(read(args.seed_seal, 2*1024**2, SEED_SHA))
    expected = {key(p['Path']): {k: p[k] for k in ('Path','Bytes','SHA256')} for p in seed['Inputs']}
    # Preserve the qualified E7 artifacts explicitly, in addition to every
    # reused link input. Read this small historical receipt, not the binaries.
    e7_receipt = json.loads(read(e7/'build-artifact.local.json'))
    require(e7_receipt['executable']['sha256'] == 'e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04', 'E7 identity differs')
    anchors = []
    for name in ('executable', 'pdb'):
        pin = e7_receipt[name]
        require(key(pin['path']) == key(e7/'bin'/('zonetool-community.'+('exe' if name == 'executable' else 'pdb'))), 'E7 anchor path differs')
        expected[key(pin['path'])] = {'Path':pin['path'],'Bytes':pin['bytes'],'SHA256':pin['sha256']}
        anchors.append(key(pin['path']))
    vc = Path(r'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207')
    sdk = Path(r'C:\Program Files (x86)\Windows Kits\10')
    sdkbin = sdk/'bin/10.0.26100.0/x64'; compiler_dir = vc/'bin/Hostx64/x64'
    for name, (size, sha) in SDK_PINS.items():
        path = sdkbin/name; expected[key(path)] = {'Path':str(path), 'Bytes':size, 'SHA256':sha}
    expected[key(job)] = {'Path':str(job), 'Bytes':13312, 'SHA256':JOB_SHA}
    if args.extra_pins:
        extra = json.loads(read(args.extra_pins, 8192))
        extra_names = {'loadedsound.obj','loadedsound1.obj','loadedsound2.obj','loadedsound3.obj','sound_bank.obj'}
        require(extra['Schema'] == 'iw7.t7-extra-input-pins/1' and len(extra['Inputs']) == 5 and
                {key(p['Path']) for p in extra['Inputs']} == {key(e7/'obj'/n) for n in extra_names},
                'Only the five missing E7 object pins may supplement Seal C')
        for pin in extra['Inputs']:
            require(re.fullmatch('[0-9a-f]{64}',pin['SHA256']) and type(pin['Bytes']) is int and 0 < pin['Bytes'] < 16*1024**2,
                    'Bounded exact supplemental object pin required')
            expected[key(pin['Path'])] = pin
    deps = read_records(read(e7/'obj/tlog/CL.read.1.tlog', 16*1024**2).decode('utf-16'))
    wanted = set()
    for path in [source/row[0] for row in UNITS]+[source/'src/zonetool/std_include.cpp']:
        require(key(path) in deps, 'Affected TU/PCH dependency record missing')
        wanted.update(key(p) for p in deps[key(path)] if Path(p).suffix.casefold() != '.pch')
    linked = read_records(read(e7/'obj/tlog/link.read.1.tlog', 256*1024).decode('utf-16'))
    require(len(linked) == 1, 'Single original link dependency record required')
    wanted.update(key(p) for p in next(iter(linked.values())))
    wanted.difference_update(map(key, replaced))
    # Recorded toolchain/debug closure is reused as an expected pin set, NOT as
    # a native T7 seal or a claim of hermetic Windows/system DLL dependencies.
    wanted.update(key(p['Path']) for p in seed['Inputs'] if p['Category'] == 'toolchain')
    wanted.update(key(sdkbin/n) for n in SDK_PINS)
    wanted.add(key(job))
    wanted.update(anchors)
    missing = []; inputs = []
    for path in sorted(wanted):
        actual = path_checked(path); require(actual.is_file(), 'Recorded input missing: '+path)
        if path not in expected:
            if actual.suffix in ('.hpp', '.h'):
                _, pin = text_pin(actual, 256*1024)
                inputs.append(pin)
            else:
                missing.append({'Path':str(actual),'Bytes':actual.stat().st_size})
        else:
            pin = expected[path]; require(actual.stat().st_size == pin['Bytes'], 'Expected input size differs')
            inputs.append(pin)
    helper = run/'helper'; helper_source = output/'prepared/test_t7_asset_name.cpp'
    helper_args = ['/nologo','/std:c++20','/EHsc','/W4','/WX','/MT','/Od','/Z7',
                   '/sourceDependencies',str(helper/'dependencies.json'),
                   '/Fo'+str(helper/'native_probe.obj'), '/Fe'+str(helper/'native_probe.exe'), str(helper_source),
                   '/link','/INCREMENTAL:NO','/DEBUG','/PDB:'+str(helper/'native_probe.pdb')]
    stages = [{'Name':'helper','Stage':'Compile','Image':str(compiler_dir/'cl.exe'), 'Arguments':helper_args,
               'DeadlineSeconds':120,'Artifacts':['native_probe.obj','native_probe.exe','native_probe.pdb','dependencies.json']},
              {'Name':'probe','Stage':'Probe','Image':str(helper/'native_probe.exe'), 'Arguments':[],
               'DeadlineSeconds':15,'Artifacts':[]}]
    for _, obj, _ in UNITS:
        stages.append({'Name':obj.removesuffix('.obj'),'Stage':'Compile','Image':str(compiler_dir/'cl.exe'),
                       'Arguments':['@'+str(output/(obj+'.rsp'))], 'DeadlineSeconds':120,
                       'Artifacts':[obj,'compile.pdb','dependencies.json']})
    stages.append({'Name':'link','Stage':'Link','Image':str(compiler_dir/'link.exe'),
                   'Arguments':['@'+str(output/'link.rsp')],'DeadlineSeconds':120,
                   'Artifacts':['zonetool-t7.exe','zonetool-t7.pdb','zonetool-t7.lib','zonetool-t7.exp']})
    reuse = None
    require(bool(args.reuse_plan) == bool(args.reuse_compile_receipt), 'Both prior plan and receipt required')
    if args.reuse_plan:
        prior_raw = read(args.reuse_plan,2*1024**2)
        prior_receipt_raw = read(args.reuse_compile_receipt,128*1024)
        if catalog_trace:
            prepare_catalog_trace.verify_base(
                read(args.ordinary_plan,2*1024**2,prepare_catalog_trace.BASE_PLAN_SHA),
                read(args.ordinary_receipt,128*1024,prepare_catalog_trace.BASE_RECEIPT_SHA),
                prior_raw, prior_receipt_raw, payloads)
            wire = (prepare_catalog_trace.wire_callers_main if catalog_callers else
                    prepare_catalog_trace.wire_exit_main if catalog_exit else prepare_catalog_trace.wire_main)
            payloads['prepared/main.cpp'] = wire(payloads['prepared/main.cpp'].decode()).encode()
        reuse, reused_inputs, reused_text = reuse_compilation(prior_raw,
            prior_receipt_raw, payloads, run, recompile_main=recompile_main, catalog_trace=catalog_trace)
        reuse.update({'SourcePlan':str(path_checked(args.reuse_plan)),
                      'Receipt':str(path_checked(args.reuse_compile_receipt))})
        for pin in reused_inputs:
            require(path_checked(pin['Path']).stat().st_size == pin['Bytes'], 'Reused artifact size differs')
        for pin in reused_text:
            read(pin['Path'],256*1024,pin['SHA256'])
        inputs += reused_inputs
        stages = [s for s in stages if s['Name'] in (('main','link') if recompile_main else ('link',))]
    environment = {'SystemRoot':r'C:\Windows','WINDIR':r'C:\Windows','SystemDrive':'C:',
        'COMSPEC':r'C:\Windows\System32\cmd.exe', 'PATH':str(compiler_dir)+';'+str(sdkbin)+r';C:\Windows\System32',
        'INCLUDE':';'.join(map(str,[vc/'include']+[sdk/'Include/10.0.26100.0'/n for n in ('ucrt','shared','um','winrt','cppwinrt')])),
        'LIB':';'.join(map(str,[vc/'lib/x64',sdk/'Lib/10.0.26100.0/ucrt/x64',sdk/'Lib/10.0.26100.0/um/x64'])),
        'VSLANG':'1033','NUMBER_OF_PROCESSORS':'1'}
    for name in ('CL','_CL_','LINK','_LINK_','LIBPATH','PYTHONPATH','PYTHONHOME'): environment[name] = ''
    for name, raw in payloads.items():
        text_inputs.append({'Path':str(output/name),'Bytes':len(raw),'SHA256':hashlib.sha256(raw).hexdigest()})
    # Keep H1's repeated compiler-residual checks small. Full sealed inputs are
    # guarded once across all stages and verified again after the last closure.
    bindings = {key(p['Path']):dict(p,IsText=True) for p in text_inputs}
    for path in (job, compiler_dir/'cl.exe', compiler_dir/'vctip.exe', compiler_dir/'link.exe', *[sdkbin/n for n in SDK_PINS]):
        bindings[key(path)] = dict(expected[key(path)], IsText=False)
    require(bindings[key(compiler_dir/'cl.exe')]['SHA256'] == CL_SHA, 'Pinned compiler differs')
    profile = None
    if prepatch_helper:
        profile = {'Name':prepare_prepatch.NAME,'Option':prepare_prepatch.OPTION,'ArgumentCount':2,
                   'Report':prepare_prepatch.REPORT}
        for name, path in [('Helper',output/'prepared'/prepare_prepatch.HELPER),
                           ('Wiring',HERE/'prepare_prepatch.py'),('PreparedMain',output/'prepared/main.cpp')]:
            profile[name] = {k:bindings[key(path)][k] for k in ('Path','Bytes','SHA256')}
    elif catalog_trace:
        profile = {'Name':(prepare_catalog_trace.CALLERS_NAME if catalog_callers else
                          prepare_catalog_trace.EXIT_NAME if catalog_exit else prepare_catalog_trace.NAME),
                   'Option':prepare_catalog_trace.OPTION,'ArgumentCount':3,
                   'TraceSchema':prepare_catalog_trace.SCHEMA}
        if catalog_exit: profile['ContextSchema'] = prepare_catalog_trace.EXIT_SCHEMA
        if catalog_callers: profile['CallerSchema'] = prepare_catalog_trace.CALLERS_SCHEMA
        for name, path in [('Wiring',HERE/'prepare_catalog_trace.py'),('PreparedMain',output/'prepared/main.cpp'),
                           ('BaseBuildPlan',args.ordinary_plan),('BaseBuildReceipt',args.ordinary_receipt)]:
            profile[name] = {k:bindings[key(path)][k] for k in ('Path','Bytes','SHA256')}
    plan = {'Schema':'iw7.t7-minimal-build-plan/1','SourceCommit':contract['native_source_commit'],
        'RunRoot':str(run),'PreparedRoot':str(output/'prepared'),'Runner':str(HERE/'Run-T7Build.ps1'),
        'Profile':str(HERE/'T7Build.Profile.ps1'), **{k:str(providers/v) for k,v in roles.items()},
        'Compiler':str(compiler_dir/'cl.exe'),'JobAssembly':str(job),'Bindings':list(bindings.values()),
        'Inputs':inputs,'MissingExpectedPins':missing,'InputPinsComplete':not missing,'Environment':environment,
        'Stages':stages,'ReuseCompile':reuse,'BuildProfile':profile,
        'PhysicalBytes':4*1024**3,'CommitBytes':6*1024**3,'GroupDeadlineSeconds':600,
        'OutputLimitBytes':256*1024**2,'MetadataReserveBytes':1024**2,'CleanupSeconds':5,
        'ReusedObjects':410,'ReusedProjectLibraries':18,'ReusedResources':1,'NativeExecuted':False,
        'ToolchainFullyHermetic':False,'Ready':False}
    raw = (json.dumps(plan,indent=2)+'\n').encode()
    require(len(raw) <= 2*1024**2 and sum(map(len,payloads.values())) <= 256*1024, 'Preparation bound exceeded')
    payloads['build-plan.local.json'] = raw
    output.mkdir()
    for name, data in payloads.items():
        target = output/name; target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream: stream.write(data)
    return {'Plan':str(output/'build-plan.local.json'),'SHA256':hashlib.sha256(raw).hexdigest(),
            'Files':len(payloads),'InputPins':len(inputs),'MissingExpectedPins':missing,
            'NativeExecuted':False,'CandidateCreated':False,'Ready':False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for n in ('source','e7','output','run','adapter','providers','job','seed-seal'): parser.add_argument('--'+n,type=Path,required=True)
    parser.add_argument('--extra-pins',type=Path)
    parser.add_argument('--reuse-plan',type=Path)
    parser.add_argument('--reuse-compile-receipt',type=Path)
    parser.add_argument('--prepatch-helper',type=Path)
    parser.add_argument('--catalog-trace',action='store_true')
    parser.add_argument('--catalog-exit',action='store_true')
    parser.add_argument('--catalog-callers',action='store_true')
    parser.add_argument('--ordinary-plan',type=Path)
    parser.add_argument('--ordinary-receipt',type=Path)
    print(json.dumps(prepare(parser.parse_args()),indent=2))

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
import prepare_message_publication

HERE = Path(__file__).resolve().parent
CL_LOG_SHA = 'a7083ce5b9ba2fe1421c4f8733cf1d1e0b286549dbc55a44f3ef30ceb3c05333'
LINK_LOG_SHA = '70455d2f32a9b034dda20fbaf48443ee68a02e552381edbf88b19d219f1f66b2'
E7_READ_PIN = (15206288, 'd9cdd533796a9fe14e0d5140d8adcbf5cbc932fafd4c06e18a615d15199a2185')
SEED_SHA = 'f52867e7c26d05466ba57d72eef601d42376c1109dfcf61f219a1a028229f388'
CL_SHA = 'fe251ef50a1545b1b0835ee17b1e785459712b38d79e45b5c1d3d28970a36619'
JOB_SHA = '5f613ebb83019dbf4bfa4f6a93c5329098343729b70acc2cfa70aa8b64f195f8'
UNITS = tuple(zip(prepare_cli.PATHS[:3], ('main.obj', 'zonetool11.obj', 'xpak.obj'),
                  ('main.cpp', 'zonetool.cpp', 'common/xpak.cpp')))
SDK_PINS = {'rc.exe': (55640, '43da1503c262c30894c851589bf0155f8365d77e63a5f7bc13982320e3a6b42d'),
            'rcdll.dll': (264536, '9a11e4759adc48abe1fa9e3082ad7db4b53f4d6d77701c13729f4ffd47ae934c')}


# The explicit IW7 writer include pulls in this exact 66-header facade. These
# are raw source pins from native fab935826c898806855376662a8a03317b3ad8f1,
# justified by its sealed E7 xsurface TU dependency record; no discovery glob.
MULTISURFACE_HEADER_PINS = {
    'src/zonetool/component/iw7/command.hpp': (1079, 'ff39ace55d37a3daa189bc662f0e8ced3fbb7638ce51dab45e920f06c01a1f78'),
    'src/zonetool/component/iw7/scheduler.hpp': (858, 'a0ce7d867026aea722f85b654efba781e4d152561ff8c5fc6d84fc00d91b2ff6'),
    'src/zonetool/game/iw7/game.hpp': (773, '959d5583ce5d46f06ce3a6837347b475ee90d369360cad0654a97d97e3711571'),
    'src/zonetool/game/iw7/structs.hpp': (12260, 'a44114ab513d92e5d42d4b3a564ba32e3811c33f00d254dcaa3b42bf4cd387d6'),
    'src/zonetool/game/iw7/symbols.hpp': (7667, '5e1e5c47ab9c8ae8c9ecc46d06f86da6cacfa0a19d431f40c5a762654e0d1a09'),
    'src/zonetool/zonetool/iw7/assets/aipaths.hpp': (911, '43b64da885c94cf2bfcc5d9dfe4836125aff40c59f496567c8f268e3057282fc'),
    'src/zonetool/zonetool/iw7/assets/clipmap.hpp': (1171, '69982e0a7a7d5544c07c82045af4b4d8e4805b4f654c06ef1c0bac60e8a5ddcf'),
    'src/zonetool/zonetool/iw7/assets/computeshader.hpp': (745, '634b7a7234213674513adc6f30780213edb47373b12045a79e1b6ce790627108'),
    'src/zonetool/zonetool/iw7/assets/comworld.hpp': (725, 'b274a97a6558030d25be5230ab5746a2e7162366d262623e1c6d1c2434de2ced'),
    'src/zonetool/zonetool/iw7/assets/ddl.hpp': (723, 'eba1113cf20b3c8a1b1babe312fc326dcd10e6599648bd04593ed2cff40125fc'),
    'src/zonetool/zonetool/iw7/assets/domainshader.hpp': (765, '3556c98cb23ddeed04430d813d29d162a3b4ecef123f49cdb55f0b48aa9897cb'),
    'src/zonetool/zonetool/iw7/assets/fxeffectdef.hpp': (738, 'd4c6c8847fe35432eb1376eded793a0b9fc55e056c82f088c58d9ca71c8168c9'),
    'src/zonetool/zonetool/iw7/assets/fxparticlesimanimation.hpp': (783, 'dbd9d8b94edebf6f621df560d7f0e23456694bdc69064080c4279398e970c605'),
    'src/zonetool/zonetool/iw7/assets/fxworld.hpp': (721, '42f0fb397187a4e14b61f4a2396abfc645dee3aabfc8fb72fc95231e5bbd64e2'),
    'src/zonetool/zonetool/iw7/assets/gesture.hpp': (775, '03e0d54267b021a90fd11ee36640a3bd111b54de863573504a65a26101a3fd6c'),
    'src/zonetool/zonetool/iw7/assets/gfximage.hpp': (1231, 'eba9121056f3ef41fdb972dc1da7b9e870d45b45b91d8f1ace9a73116fc9aa4d'),
    'src/zonetool/zonetool/iw7/assets/gfxlightdef.hpp': (738, '8f04897e2daea1de03c4042a4c3edd605999821e392c7e2bc4cce2a857f48a86'),
    'src/zonetool/zonetool/iw7/assets/gfxlightmap.hpp': (738, 'fac30373307ed1c0bf19cd528b48c257a57f6b4fba8b5d6b7d87fbd679c89f91'),
    'src/zonetool/zonetool/iw7/assets/gfxworld.hpp': (754, '7572d8d7f30c52a43d41e17d9419e8801ebd95731121de459b448c2e5b4e7531'),
    'src/zonetool/zonetool/iw7/assets/gfxworld_tr.hpp': (767, '5936187acea267c54ab8fbcadb1ae70932574a4e4a32aa75ba17857f0a07f10f'),
    'src/zonetool/zonetool/iw7/assets/glassworld.hpp': (735, '36b303947e1def0ace6352294624c89cf77c5e6be6b837662a728c2339bd7e88'),
    'src/zonetool/zonetool/iw7/assets/hullshader.hpp': (757, '0d903d00b9e9d69aa8e70fb8b1f77de75c50782618bb41ea396cde3197916362'),
    'src/zonetool/zonetool/iw7/assets/impactfx.hpp': (740, '9e2f203bf53ae2b9f67c0e2fc348bd52e6d4b55180a98dcc58421b93526ca285'),
    'src/zonetool/zonetool/iw7/assets/laser.hpp': (721, 'b2de83e86bd61bbc4a923c597bb89e01e6a0b30ddb0db557eca4b9965161a386'),
    'src/zonetool/zonetool/iw7/assets/localize.hpp': (153, 'e807f80ec35180b51412f1c530d8061ec13d264424580f32f524e3a88ed9ce4b'),
    'src/zonetool/zonetool/iw7/assets/luafile.hpp': (141, '587e7fc04a17479d644a263ef34518ddd217fd1d95ae469d58668af12a1b8c1b'),
    'src/zonetool/zonetool/iw7/assets/mapents.hpp': (1649, '24b6f08c7dea08a924bb8ed05cec320d167cd28a91fae469bc1cc854e0439952'),
    'src/zonetool/zonetool/iw7/assets/material.hpp': (1011, '155c2339db46dee75b2ae4f6acdc93a2791e9bc836974740748c6964ce32917d'),
    'src/zonetool/zonetool/iw7/assets/navmesh.hpp': (914, '3c500824e65fbabedc2ce6f5a569335be7c23cc09f7bf2f35b16d4eade94cbaa'),
    'src/zonetool/zonetool/iw7/assets/netconststrings.hpp': (747, '86135467eed681cef0be0243f529132211653506b8b4ebb90a465736f1d7a1fb'),
    'src/zonetool/zonetool/iw7/assets/particle_system.hpp': (758, '5908f984259938c4a64805e14336820704243820e9addfe47d03f41b7ab62147'),
    'src/zonetool/zonetool/iw7/assets/physics_asset.hpp': (741, '2405f1dcd6c2e62a47f74d0a664c4366cdfb2f740d3057a2c30552d25ad95811'),
    'src/zonetool/zonetool/iw7/assets/physics_fx_pipeline.hpp': (762, 'ce9fb7d2197deb9a9cad716cf609e3d1e26c3606c4da84d00ab6e1b67a9cf91c'),
    'src/zonetool/zonetool/iw7/assets/physics_fx_shape.hpp': (750, '2f5717ddf052d15925bd7328a2009577c17ef4216f32f024377a291cb069d7df'),
    'src/zonetool/zonetool/iw7/assets/physics_library.hpp': (749, '375343c2e727e1f82fefe19c32ed48240032d720c19b3b3ae484a3ad63c3a848'),
    'src/zonetool/zonetool/iw7/assets/physics_sfx_event.hpp': (769, '8a6a8ada938bfbd99b97f26a462a00088f7a098b5530413ebba3f9e0569681a9'),
    'src/zonetool/zonetool/iw7/assets/physics_vfx_event.hpp': (769, '7455e75bc34765a357e7a6cd2451045769232b0441686ce27ae95734b5727db3'),
    'src/zonetool/zonetool/iw7/assets/pixelshader.hpp': (761, 'cffa5c276425f375697eae02aab6efd991b3d4eab7e79e0c745a91eea65d54e9'),
    'src/zonetool/zonetool/iw7/assets/rawfile.hpp': (139, 'ed30186b27796e28a111271f2577bb20e6612c5f3a00ea8a84f0bacd4443e768'),
    'src/zonetool/zonetool/iw7/assets/reticle.hpp': (729, 'eb07c87a716d5a76eedb7d94edf2e935244cd259175875b7a58cae32a5cfbb18'),
    'src/zonetool/zonetool/iw7/assets/rumble.hpp': (728, '5478cd5401f27c0162486eaf888f8cb17fa2a0ccd3fd486c9a991f998dad9c38'),
    'src/zonetool/zonetool/iw7/assets/rumble_graph.hpp': (737, 'f90e6566c73b8532e9824aaaa79f78597b215bb28d47838233b0eb7646c683bc'),
    'src/zonetool/zonetool/iw7/assets/scriptabledef.hpp': (2189, 'ed1e3717b08d18ce17e04431764aa5bd2867c3a04c4ba8ee96c831761853f93a'),
    'src/zonetool/zonetool/iw7/assets/scriptfile.hpp': (148, '902dd67debe872c4fe1785370e5bc9b8b43e52356f98a58836fad17eb97058a5'),
    'src/zonetool/zonetool/iw7/assets/sound_bank.hpp': (723, 'e4ed88851d9bacc9d208fb31dc1a770365f62aa27064ec4513ca673262b3ca49'),
    'src/zonetool/zonetool/iw7/assets/sound_globals.hpp': (12403, 'f3562a2a9beb70ec53cdf91e06bb7c50bea8f7636508d2a5b79b51a4ea5bbb6f'),
    'src/zonetool/zonetool/iw7/assets/streaming_info.hpp': (745, 'd547939960a38d3835a2d86ed77b367c16010e47147d068df345caf73abfbec9'),
    'src/zonetool/zonetool/iw7/assets/stringtable.hpp': (152, '374ce28b1bee3d36e1f1fd657c6ba8a3ae38799c97ebe02e8d63ee7c4083c56a'),
    'src/zonetool/zonetool/iw7/assets/techset.hpp': (2700, 'beaedd847e3d9c43928d0fc098caa1254377c5404e745ea03cb73fdcc64eed5d'),
    'src/zonetool/zonetool/iw7/assets/tracer.hpp': (725, '4e4b209085c4fc9a03ef96a0044dcc475f6a5813fca0d800ca81ebb2648b0751'),
    'src/zonetool/zonetool/iw7/assets/ttfdef.hpp': (134, '42b45801a65b14d0eded46c944e0533ccbdfdf4bc26892037728a8c964cf5bcb'),
    'src/zonetool/zonetool/iw7/assets/vectorfield.hpp': (737, '0cba4d00640c5829a8b072d491517bdfa895873bf32c0f62571c0f825e2eddd8'),
    'src/zonetool/zonetool/iw7/assets/vertexdecl.hpp': (164, '134de72293622d9d03650ba43bee23ea5d5e4975fbf367ddc1aa17e3a7b0f410'),
    'src/zonetool/zonetool/iw7/assets/vertexshader.hpp': (765, 'f5933d656f2f515bb7b7e0ac1235960b3f186923e7a5938794ee4a30894703e8'),
    'src/zonetool/zonetool/iw7/assets/weapon_anim_package.hpp': (814, '2ffdaddeff258f5d68e325f61cfef9c135b282f45372270052d6a644060ff792'),
    'src/zonetool/zonetool/iw7/assets/weapon_sfx_package.hpp': (758, 'f12c935f9c10038e598315f29934ed182399a88e64344d1df2dd7322843aca56'),
    'src/zonetool/zonetool/iw7/assets/weapon_vfx_package.hpp': (758, 'd215252b6f567a4b473ca7d67ae8904c83b46e15a4c17ecbfead84da19243c2b'),
    'src/zonetool/zonetool/iw7/assets/weaponattachment.hpp': (945, '1c4000505ae7229792561bb95ec48c654aff13e177b48cdf99108003bf48b5c2'),
    'src/zonetool/zonetool/iw7/assets/weapondef.hpp': (2894, 'b519dcb68cc9d15e2e7f997a949bf01f8e9ec0acffdb32b2ee07aad23aa75972'),
    'src/zonetool/zonetool/iw7/assets/xanim.hpp': (921, '7f485034bc2faddb24f1fac62532707291c59506e1574530937ae6df02fd44e5'),
    'src/zonetool/zonetool/iw7/assets/xmodel.hpp': (897, '5e978a88b5e3e8a881f5eb21c12955d8cc1c72a210357f60e04cf3e86210a13a'),
    'src/zonetool/zonetool/iw7/assets/xsurface.hpp': (735, '5b71c1049114cc9b06168576a845fe80596d1973e87f9d731cf47ecf539228a8'),
    'src/zonetool/zonetool/iw7/functions.hpp': (1512, 'ddb66a3bcd48723bf0e1b3edd509f7dcac113f26a688cffaa11348bc55307cd9'),
    'src/zonetool/zonetool/iw7/variables.hpp': (476, 'a472d37859e7a25febdcad9ca4e48a3f3699bb10ec8c1064afc47b0bbd1e8f6f'),
    'src/zonetool/zonetool/iw7/zone.hpp': (868, '18c68575dcaecab76ea243eeb3decc57bfb066a9752118a91e95f4a9bd81736d'),
    'src/zonetool/zonetool/iw7/zonetool.hpp': (3159, '612de0e4a64fceb5ec1b762fd5825d66c40f231e290c684d71896f50441f165a'),
}


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


def multisurface_header_inputs(source, e7, read_raw, compile_raw, wanted, read):
    """Extend only v2's baseline with the reviewed transitive writer headers."""
    require((len(read_raw), hashlib.sha256(read_raw).hexdigest()) == E7_READ_PIN and
            hashlib.sha256(compile_raw).hexdigest() == CL_LOG_SHA,
            'Exact E7 header dependency and compiler journals required')
    source, e7 = Path(source), Path(e7)
    writer = key(source/'src/zonetool/zonetool/iw7/assets/xsurface.cpp')
    cli = key(source/prepare_cli.PATHS[1])
    records = read_records(read_raw.decode('utf-16'))
    commands = read_records(compile_raw.decode('utf-16'))
    require(writer in records and writer in commands and cli in commands,
            'Exact E7 writer and CLI records required')
    contexts = []
    for name in (writer, cli):
        require(len(commands[name]) == 1, 'Unique E7 compiler context required')
        context = replace_one(r'/Fo"[^"]+"', '/Fo"<OBJECT>"', commands[name][0])
        context = replace_one(r'\s+"?'+re.escape(name.upper())+r'"?\s*$', ' <SOURCE>', context)
        contexts.append(context)
    require(contexts[0] == contexts[1], 'E7 writer and CLI compiler contexts differ')
    includes = [key(p) for p in records[writer]]
    require(len(includes) == len(set(includes)), 'Duplicate E7 writer dependency refused')
    pch = key(e7/'obj/community.pch')
    require([p for p in includes if PureWindowsPath(p).suffix == '.pch'] == [pch],
            'Only the known E7 PCH may be excluded for the prepared /Y- context')
    headers = {key(source/name): (name, pin) for name, pin in MULTISURFACE_HEADER_PINS.items()}
    require(len(headers) == 66 and sum(pin[0] for pin in MULTISURFACE_HEADER_PINS.values()) == 87204 and
            not set(headers).intersection(wanted) and
            set(includes) - {pch} - wanted == set(headers),
            'Exact 66 additional multisurface headers required; missing or extra dependency refused')
    pins = []
    for name, (size, sha) in sorted(headers.values()):
        path = source/name
        raw = read(path, 16*1024, sha)
        require((len(raw), hashlib.sha256(raw).hexdigest()) == (size, sha),
                'Multisurface header pin differs: '+name)
        pins.append({'Path':str(path), 'Bytes':size, 'SHA256':sha})
    return pins, {'Count':len(pins), 'Bytes':sum(p['Bytes'] for p in pins),
                  'E7TranslationUnit':writer, 'E7ReadSHA256':E7_READ_PIN[1],
                  'E7CompileSHA256':CL_LOG_SHA, 'CompilerContextMatchesCLI':True,
                  'PCHExcludedForPreparedYMinus':pch, 'Inputs':pins}


def surface_count_dependency_proof(prior, receipt, dependency_json, e7_journals, *, resident_multisurface_v2=False):
    """Check compiler text evidence, not retained object or library contents."""
    require(type(resident_multisurface_v2) is bool, 'Multisurface selection must be boolean')
    require(type(dependency_json) is dict and set(dependency_json) == {'helper','zonetool11','xpak'},
            'Exact helper/CLI/xpak dependency JSON set required')
    prepared = PureWindowsPath(prior['PreparedRoot']); old_root = PureWindowsPath(prior['RunRoot'])
    header = prepared/prepare_catalog_trace.SURFACE_COUNT_HEADER.removeprefix('prepared/')
    header_name = header.name.casefold()
    pins = []
    for stage, source in (('helper','test_t7_asset_name.cpp'), ('zonetool11','zonetool.cpp'), ('xpak','common/xpak.cpp')):
        rows = [s for s in receipt['Stages'] if s['Name'] == stage]
        require(len(rows) == 1, 'Unique dependency stage required')
        matches = [p for p in rows[0]['Artifacts'] if key(p['Path']) == key(old_root/stage/'dependencies.json')]
        require(len(matches) == 1, 'Receipt-bound dependency JSON required')
        pin = matches[0]; raw = dependency_json[stage]
        require(isinstance(raw, bytes) and 0 < len(raw) <= 128*1024 and
                (len(raw), hashlib.sha256(raw).hexdigest()) == (pin['Bytes'], pin['SHA256']),
                'Dependency JSON pin differs')
        doc = json.loads(raw)
        require(type(doc) is dict and set(doc) == {'Version','Data'}, 'Unambiguous compiler dependency document required')
        data = doc['Data']
        require(doc.get('Version') == '1.2' and type(data) is dict and
                set(data) == {'Source','ProvidedModule','Includes','ImportedModules','ImportedHeaderUnits'} and
                type(data['Source']) is str and key(data['Source']) == key(prepared/source) and
                data['ProvidedModule'] == '' and data['ImportedModules'] == [] and data['ImportedHeaderUnits'] == [],
                'Complete non-module dependency record for the exact source required')
        includes = data['Includes']
        require(type(includes) is list and 0 < len(includes) <= 4096 and
                all(type(p) is str and PureWindowsPath(p).is_absolute() and
                    not any(c in p for c in '\r\n\0') and '..' not in PureWindowsPath(p).parts for p in includes),
                'Bounded absolute include list required')
        consumers = [key(p) for p in includes if PureWindowsPath(p).name.casefold() == header_name]
        require(consumers == ([key(header)] if stage == 'zonetool11' else []),
                'Diagnostic header consumer must be only the recompiled CLI')
        pins.append(pin)
    require(type(e7_journals) is dict and set(e7_journals) == {'read','compile','link'},
            'Complete sealed E7 read/compile/link journal set required')
    e7_read_raw = e7_journals['read']
    require(isinstance(e7_read_raw, bytes) and
            (len(e7_read_raw), hashlib.sha256(e7_read_raw).hexdigest()) == E7_READ_PIN,
            'Exact sealed E7 dependency journal required')
    for name, limit, digest in (('compile',4*1024**2,CL_LOG_SHA), ('link',256*1024,LINK_LOG_SHA)):
        raw = e7_journals[name]
        require(isinstance(raw, bytes) and 0 < len(raw) <= limit and hashlib.sha256(raw).hexdigest() == digest,
                'Exact sealed E7 command journal required')
    records = read_records(e7_read_raw.decode('utf-16'))
    require(len(records) == 413 and all(records.values()), 'Complete E7 dependency journal required')
    commands = read_records(e7_journals['compile'].decode('utf-16'))
    require(set(commands) == set(records), 'Every E7 compilation must have one dependency record')
    objects = {}
    for source, rows in commands.items():
        require(PureWindowsPath(source).is_absolute() and len(rows) == 1, 'Unique absolute E7 translation unit required')
        outputs = re.findall(r'/Fo"([^"\r\n]+)"', rows[0])
        require(len(outputs) == 1 and PureWindowsPath(outputs[0]).is_absolute(), 'One absolute compiler object output required')
        output = PureWindowsPath(outputs[0])
        if output.suffix.casefold() != '.obj':
            require(outputs[0].endswith(('\\','/')), 'Explicit compiler output directory required')
            output /= PureWindowsPath(source).with_suffix('.obj').name
        require(key(output) not in objects, 'Ambiguous E7 object producer refused')
        objects[key(output)] = source
    link_rows = e7_journals['link'].decode('utf-16').splitlines()
    require(len(link_rows) == 415 and link_rows[0].startswith('^') and
            all(re.fullmatch(r'"[^"\r\n]+\.OBJ"', row) for row in link_rows[2:]),
            'Exact E7 413-object link inventory required')
    linked = [key(row[1:-1]) for row in link_rows[2:]]
    require(len(set(linked)) == 413 and set(linked) == set(objects),
            'Every linked E7 object must have one compiler and dependency record')
    require(not any(PureWindowsPath(p).name.casefold() == header_name
                    for source, includes in records.items() for p in (source, *includes)),
            'Retained E7 consumer of diagnostic header refused')
    return {'Header':prepare_catalog_trace.SURFACE_COUNT_HEADER,
            'PreviousSHA256':prepare_catalog_trace.SURFACE_COUNT_OLD_PIN[1],
            'SHA256':(prepare_catalog_trace.MULTISURFACE_TRANSITIONS[prepare_catalog_trace.SURFACE_COUNT_HEADER][1][1]
                      if resident_multisurface_v2 else prepare_catalog_trace.SURFACE_COUNT_NEW_PIN[1]),
            'DependencyJSON':pins,'E7ReadSHA256':E7_READ_PIN[1],
            'E7CompileSHA256':CL_LOG_SHA,'E7LinkSHA256':LINK_LOG_SHA,
            'E7TranslationUnits':len(records),'E7Objects':len(objects)}


def reuse_compilation(prior_plan_raw, receipt_raw, payloads, run, *, recompile_main=False, catalog_trace=False,
                      recompile_zonetool=False, surface_count_dependencies=None, e7_dependency_text=None,
                      resident_multisurface_v2=False):
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
    require(type(recompile_zonetool) is bool and
            (not recompile_zonetool or (recompile_main is True and catalog_trace is True)),
            'CLI rebuild requires the explicit two-TU catalogue path')
    require(type(resident_multisurface_v2) is bool, 'Multisurface selection must be boolean')
    header_evidence = surface_count_dependencies is not None
    diagnostic = header_evidence and not resident_multisurface_v2
    require((e7_dependency_text is not None) == header_evidence and
            (not resident_multisurface_v2 or header_evidence) and
            (not header_evidence or (recompile_main is True and catalog_trace is True and recompile_zonetool is True)),
            'Surface-count diagnostic requires both fresh TUs and complete dependency evidence')
    diagnostic_proof = None
    if resident_multisurface_v2:
        require(all(prepare_catalog_trace.multisurface_payload_delta(name, payloads.get(name),
                    prior_bindings.get(key(prepared/name.removeprefix('prepared/'))), wired=True)
                    for name in prepare_catalog_trace.MULTISURFACE_TRANSITIONS),
                'Exact wired multisurface v2 transitions required')
    elif diagnostic:
        name = prepare_catalog_trace.SURFACE_COUNT_HEADER
        require(prepare_catalog_trace.surface_count_header_delta(name, payloads.get(name),
                prior_bindings.get(key(prepared/name.removeprefix('prepared/')))),
                'Exact surface-count diagnostic transition required')
    if header_evidence:
        diagnostic_proof = surface_count_dependency_proof(prior, receipt, surface_count_dependencies, e7_dependency_text,
                                                         resident_multisurface_v2=resident_multisurface_v2)
        if resident_multisurface_v2:
            diagnostic_proof.update(Schema='iw7.t7-resident-multi-surface-build/2',
                SourceTransitions=[{'Path':name,'PreviousBytes':old[0],'PreviousSHA256':old[1],
                    'Bytes':new[0],'SHA256':new[1],
                    'WiredBytes':prepare_catalog_trace.MULTISURFACE_WIRED_PINS[name][0],
                    'WiredSHA256':prepare_catalog_trace.MULTISURFACE_WIRED_PINS[name][1]}
                    for name,(old,new) in prepare_catalog_trace.MULTISURFACE_TRANSITIONS.items()])
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
        if resident_multisurface_v2 and prepare_catalog_trace.multisurface_payload_delta(name, raw, pin, wired=True):
            old_text.append(pin)
            continue
        if diagnostic and prepare_catalog_trace.surface_count_header_delta(name, raw, pin):
            old_text.append(pin)
            continue
        if (recompile_main and name == 'prepared/main.cpp') or (recompile_zonetool and name == 'prepared/zonetool.cpp'):
            require(pin and pin['SHA256'] != hashlib.sha256(raw).hexdigest(),
                    'Recompiled TU must differ from its retained source: '+name)
            old_text.append(pin)
            continue
        require(pin and pin['Bytes'] == len(raw) and pin['SHA256'] == hashlib.sha256(raw).hexdigest(),
                'Native source/header/fixture differs from compiled prior stage')
        old_text.append(pin)
    inputs = []
    reused_units = tuple(u for u in UNITS if not (recompile_main and u[1] == 'main.obj')
                         and not (recompile_zonetool and u[1] == 'zonetool11.obj'))
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
    if recompile_zonetool:
        for obj in ('main.obj', 'zonetool11.obj'):
            expected = quote(PureWindowsPath(run)/obj[:-4]/obj)
            matches = [line for line in response.splitlines() if
                       line.startswith('"') and line.endswith('"') and
                       PureWindowsPath(line[1:-1]).name.casefold() == obj]
            require(matches == [expected], 'Two-TU link requires each fresh object exactly once: '+obj)
    for _, obj, _ in reused_units:
        source = quote(PureWindowsPath(run)/obj[:-4]/obj)
        require(response.splitlines().count(source) == 1, 'One new object path required before reuse')
        response = response.replace(source+'\n', quote(old_root/obj[:-4]/obj)+'\n')
    payloads['link.rsp'] = response.encode()
    return {'OriginalStatus':'Failed','SourcePlanSHA256':receipt['PlanSHA256'],
            'ReceiptSHA256':hashlib.sha256(receipt_raw).hexdigest(),'Checks':51,
            'RecompiledMain':recompile_main, **({'RecompiledZonetool':True} if recompile_zonetool else {}),
            **({'ResidentSurfaceCountDiagnostic':diagnostic_proof} if diagnostic else {}),
            **({'ResidentMultiSurfaceV2':diagnostic_proof} if resident_multisurface_v2 else {}),
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
    cl_raw = read(e7/'obj/tlog/CL.command.1.tlog', 4*1024**2, CL_LOG_SHA)
    link_raw = read(e7/'obj/tlog/link.command.1.tlog', 256*1024, LINK_LOG_SHA)
    cl, link = cl_raw.decode('utf-16'), link_raw.decode('utf-16')
    payloads, replaced = command_payloads(cl, link, source, output/'prepared', run)
    _, patched = prepare_cli.render(source)
    prepatch_helper = getattr(args, 'prepatch_helper', None)
    catalog_publication = bool(getattr(args, 'catalog_message_publication', False))
    surface_count_diagnostic = getattr(args, 'resident_surface_count_diagnostic', False)
    resident_multisurface_v2 = getattr(args, 'resident_multisurface_v2', False)
    require(type(resident_multisurface_v2) is bool and
            (not resident_multisurface_v2 or (catalog_publication and surface_count_diagnostic is False)),
            'Multisurface v2 requires exclusive two-TU publication selection')
    require(type(surface_count_diagnostic) is bool and (not surface_count_diagnostic or catalog_publication),
            'Surface-count diagnostic requires the existing main/CLI publication profile')
    catalog_message = bool(getattr(args, 'catalog_message', False) or catalog_publication)
    catalog_callers = bool(getattr(args, 'catalog_callers', False) or catalog_message)
    catalog_exit = bool(getattr(args, 'catalog_exit', False) or catalog_callers)
    catalog_trace = bool(getattr(args, 'catalog_trace', False) or catalog_exit)
    require(sum(map(bool, (prepatch_helper, getattr(args, 'catalog_trace', False),
                          getattr(args, 'catalog_exit', False), getattr(args, 'catalog_callers', False),
                          getattr(args, 'catalog_message', False), catalog_publication))) <= 1,
            'Pre-patch and catalogue diagnostic profiles are exclusive')
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
    if catalog_publication:
        read(HERE/'prepare_message_publication.py',64*1024)
        read(HERE/'native_message_publication.inc',16*1024)
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
    e7_dependency_text = read(e7/'obj/tlog/CL.read.1.tlog', 16*1024**2,
                              E7_READ_PIN[1] if surface_count_diagnostic or resident_multisurface_v2 else None)
    deps = read_records(e7_dependency_text.decode('utf-16'))
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
    multisurface_headers = None
    if resident_multisurface_v2:
        header_pins, multisurface_headers = multisurface_header_inputs(
            source, e7, e7_dependency_text, cl_raw, wanted, read)
        for pin in header_pins:
            wanted.add(key(pin['Path']))
            expected[key(pin['Path'])] = pin
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
        surface_count_dependencies = None
        if catalog_trace:
            prepare_catalog_trace.verify_base(
                read(args.ordinary_plan,2*1024**2,prepare_catalog_trace.BASE_PLAN_SHA),
                read(args.ordinary_receipt,128*1024,prepare_catalog_trace.BASE_RECEIPT_SHA),
                prior_raw, prior_receipt_raw, payloads, surface_count_diagnostic=surface_count_diagnostic,
                resident_multisurface_v2=resident_multisurface_v2)
            if surface_count_diagnostic or resident_multisurface_v2:
                prior = json.loads(prior_raw); receipt = json.loads(prior_receipt_raw)
                surface_count_dependencies = {}
                for stage in ('helper','zonetool11','xpak'):
                    path = PureWindowsPath(prior['RunRoot'])/stage/'dependencies.json'
                    pins = [p for s in receipt['Stages'] if s['Name'] == stage
                            for p in s['Artifacts'] if key(p['Path']) == key(path)]
                    require(len(pins) == 1, 'Receipt-bound dependency JSON required')
                    surface_count_dependencies[stage] = read(Path(path),128*1024,pins[0]['SHA256'])
            wire = (prepare_catalog_trace.wire_message_main if catalog_message else
                    prepare_catalog_trace.wire_callers_main if catalog_callers else
                    prepare_catalog_trace.wire_exit_main if catalog_exit else prepare_catalog_trace.wire_main)
            payloads['prepared/main.cpp'] = wire(payloads['prepared/main.cpp'].decode()).encode()
            if catalog_publication:
                main, cli = prepare_message_publication.overlay(payloads['prepared/main.cpp'].decode(),
                                                                payloads['prepared/zonetool.cpp'].decode())
                payloads['prepared/main.cpp'], payloads['prepared/zonetool.cpp'] = main.encode(), cli.encode()
        reuse, reused_inputs, reused_text = reuse_compilation(prior_raw,
            prior_receipt_raw, payloads, run, recompile_main=recompile_main, catalog_trace=catalog_trace,
            recompile_zonetool=catalog_publication, surface_count_dependencies=surface_count_dependencies,
            e7_dependency_text={'read':e7_dependency_text,'compile':cl_raw,'link':link_raw}
                if surface_count_diagnostic or resident_multisurface_v2 else None,
            resident_multisurface_v2=resident_multisurface_v2)
        if resident_multisurface_v2:
            reuse['ResidentMultiSurfaceV2']['AdditionalHeaderInputs'] = multisurface_headers
        reuse.update({'SourcePlan':str(path_checked(args.reuse_plan)),
                      'Receipt':str(path_checked(args.reuse_compile_receipt))})
        for pin in reused_inputs:
            require(path_checked(pin['Path']).stat().st_size == pin['Bytes'], 'Reused artifact size differs')
        for pin in reused_text:
            read(pin['Path'],256*1024,pin['SHA256'])
        inputs += reused_inputs
        stages = [s for s in stages if s['Name'] in (('main','zonetool11','link') if catalog_publication
                                                   else ('main','link') if recompile_main else ('link',))]
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
        profile = {'Name':('t7-catalog-message-publication' if catalog_publication else
                          prepare_catalog_trace.MESSAGE_NAME if catalog_message else
                          prepare_catalog_trace.CALLERS_NAME if catalog_callers else
                          prepare_catalog_trace.EXIT_NAME if catalog_exit else prepare_catalog_trace.NAME),
                   'Option':prepare_catalog_trace.OPTION,'ArgumentCount':3,
                   'TraceSchema':prepare_catalog_trace.SCHEMA}
        if catalog_exit: profile['ContextSchema'] = prepare_catalog_trace.EXIT_SCHEMA
        if catalog_callers: profile['CallerSchema'] = prepare_catalog_trace.CALLERS_SCHEMA
        if catalog_message: profile['MessageSchema'] = prepare_catalog_trace.MESSAGE_SCHEMA
        for name, path in [('Wiring',HERE/'prepare_catalog_trace.py'),('PreparedMain',output/'prepared/main.cpp'),
                           ('BaseBuildPlan',args.ordinary_plan),('BaseBuildReceipt',args.ordinary_receipt)]:
            profile[name] = {k:bindings[key(path)][k] for k in ('Path','Bytes','SHA256')}
        if catalog_publication:
            profile['PublicationSchema'] = 'iw7.t7-message-publication-build/1'
            for name, path in [('PublicationWiring',HERE/'prepare_message_publication.py'),
                               ('PublicationSource',HERE/'native_message_publication.inc'),
                               ('PreparedCLI',output/'prepared/zonetool.cpp'),
                               ('MainResponse',output/'main.obj.rsp'),('CLIResponse',output/'zonetool11.obj.rsp'),
                               ('LinkResponse',output/'link.rsp')]:
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
    parser.add_argument('--catalog-message',action='store_true')
    parser.add_argument('--catalog-message-publication',action='store_true')
    parser.add_argument('--resident-surface-count-diagnostic',action='store_true')
    parser.add_argument('--resident-multisurface-v2',action='store_true')
    parser.add_argument('--ordinary-plan',type=Path)
    parser.add_argument('--ordinary-receipt',type=Path)
    print(json.dumps(prepare(parser.parse_args()),indent=2))

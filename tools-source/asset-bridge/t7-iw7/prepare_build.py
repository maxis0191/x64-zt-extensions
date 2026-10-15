"""Prepare a private three-TU build. Reads text/metadata only; never runs native code."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import prepare_cli
import prepare_prepatch
import prepare_prepatch_reference as reference_probe
import prepare_prepatch_link_v3 as link_probe
import prepare_prepatch_image_caller as caller_probe
import prepare_catalog_trace
import prepare_message_publication
import prepare_catalog_zombies_observation as zombies_observer
import prepare_catalog_add_observation as add_observer
import prepare_material_parts as material_parts
import prepare_image_provenance as image_provenance
import prepare_image_metadata as image_metadata
import prepare_image_registration_metadata as registration_metadata
import prepare_incoming_image_metadata as incoming_metadata
import prepare_registration_bindings_build as bindings_build

IMAGE_FIXTURE_SOURCE = '678bf7dde6a99207654256c1e53ebaaec286ffe1'
IMAGE_FIXTURE_API_PINS = {
    'ProvenanceSource': (15069, 'd8b3f07f787f03dbda7c0305e2aad685c131130fbe43a839145e869858925c16'),
    'ProvenanceEntry': (1254, '360bcf806e2d69f3ecba2d2422b99c8c86a775397438117607115ed0d8b5573e'),
    'ProvenanceFixture': (14892, 'f123c92c219c6d133882cadda2c8f62967de9bb86f2de0f55d0b468384d5f574'),
}
IMAGE_FIXTURE_PROOFS = {
    'Receipt': ('image-provenance-fixture-h/receipt.local.json', 11759,
                '7e612f958494f52f236dd8a48c3b5d69437eb25ca5fe73036e3b0974243762a6'),
    'PreExit': ('image-provenance-fixture-h.preexit.local.json', 4479,
                'c8eebce6a47af7c35f572f8ec4457a8e32d035fb9f577c26467a9ad5e1305e7e'),
    'Closure': ('image-provenance-fixture-h.closure.local.json', 369,
                '5203527eed2c6e92575845a57e65aa0d8b6b3f30759e751e64d8e5436b1e75b8'),
    'Stdout': ('image-provenance-fixture-h/test.stdout.log', 76,
               '6a704c3d42c843b585a02f93dc12dd82156dce6c7b441cf9374e94bb4e926f8f'),
}


def image_fixture_proof_requested(args):
    root = getattr(args, 'image_provenance_fixture_proof_root', None)
    require(root is None or getattr(args, 'image_provenance_v1', False) is True,
            'H fixture proof requires the explicit image provenance profile')
    return root


def image_fixture_proof(root, read):
    """Consume only the four reviewed H text files; never opens their artifact paths."""
    root = path_checked(root)
    proof = {'Schema': 'iw7.t7-image-fixture-proof/1',
             'SourceCommit': IMAGE_FIXTURE_SOURCE, 'ExpectedChecks': 53}
    documents = {}
    for role, (relative, count, digest) in IMAGE_FIXTURE_PROOFS.items():
        path = root / relative
        raw = read(path, count, digest)
        require(type(raw) is bytes and len(raw) == count and
                hashlib.sha256(raw).hexdigest() == digest, 'Exact H text proof required')
        proof[role] = dict(Path=str(path), Bytes=count, SHA256=digest)
        if role != 'Stdout':
            documents[role] = json.loads(raw)
    receipt, preexit, closure = (documents[role] for role in ('Receipt', 'PreExit', 'Closure'))
    require(receipt['SourceCommit'] == IMAGE_FIXTURE_SOURCE and
            receipt['FixtureSynthetic'] is True and receipt['EngineInvoked'] is False and
            receipt['Quarantined'] is False and type(receipt['ExpectedChecks']) is int and
            receipt['ExpectedChecks'] == 53 and receipt['FixtureSHA256'] ==
            'c0c60d905c9afcbe70f6dfbab062a3b08a9f49b70aeb37336966ef8a666746cb',
            'Actual synthetic H source qualification required')
    for document in (receipt, preexit):
        require(all(document[name] is True for name in
                    ('Passed', 'TreeClosureConfirmed', 'InputsReverified', 'LeaseReleased',
                     'CompletionPublished')), 'Closed and published H proof required')
    require(preexit['SameOriginalAppDomain'] is True and preexit['OwnerClosed'] is True and
            preexit['CanExit'] is True and type(preexit['Guards']) is int and preexit['Guards'] == 0,
            'Original H context exit qualification required')
    require([phase['Phase'] for phase in receipt['Phases']] == ['compile', 'test'] and
            all(type(phase['ExitCode']) is int and phase['ExitCode'] == 0 and
                phase['TreeClosureConfirmed'] is True for phase in receipt['Phases']),
            'Real H compile/test completion required')
    host = receipt['Host']
    require(preexit['Host']['PID'] == host['PID'] and
            preexit['Host']['CreationFileTime'] == host['CreationFileTime'] and
            host['ActualHostProof']['NoExitVerified'] is True and
            host['ActualHostProof']['VerifiedBeforeImportsAndAdmission'] is True,
            'Same original H NoExit host required')
    require(closure['Passed'] is True and closure['FixtureExecuted'] is True and
            closure['ExpectedChecks'] == 53 and closure['PhaseExits'] == [0, 0] and
            closure['ActualPTYSession'] == 96124 and closure['ActualPTYExit'] == 0 and
            closure['RemainingOwn'] == [] and closure['HeavyProcesses'] == [] and
            closure['Leases'] == [] and host['PID'] in closure['ExpectedIDs'] and
            host['Parent']['PID'] in closure['ExpectedIDs'],
            'Actual terminal exit and fresh empty H closure required')
    return proof

HERE = Path(__file__).resolve().parent


def image_provenance_selected(args):
    selected = getattr(args, 'image_provenance_v1', False)
    require(type(selected) is bool, 'Explicit image-provenance boolean required')
    if selected:
        require(getattr(args, 'catalog_message_publication', False) is True and
                getattr(args, 'selected_streamed_render_only_v2', False) is True and
                all(getattr(args, name, False) is False for name in (
                    'material_parts_v1', 'prepatch_reference_v2', 'prepatch_link_v3', 'prepatch_image_caller_v1',
                    'selected_streamed_static_v1', 'resident_multisurface_v2',
                    'resident_surface_count_diagnostic', 'zombies_catalogue_observation',
                    'zombies_add_observation_c2', 'catalog_trace', 'catalog_exit',
                    'catalog_callers', 'catalog_message')) and
                not getattr(args, 'prepatch_helper', None) and
                bool(getattr(args, 'reuse_plan', None)) and bool(getattr(args, 'reuse_compile_receipt', None)),
                'Image provenance requires exclusive E5 publication and retained compile proofs')
    return selected


def image_provenance_transition(payloads, read):
    # Bind both adapters: the frozen provenance overlay reuses parts' exact E5/G2 primitives.
    read(HERE/'prepare_material_parts.py', 32*1024)
    read(HERE/'prepare_image_provenance.py', 32*1024)
    main, cli, marker = image_provenance.overlay(payloads['prepared/main.cpp'].decode(),
                                              payloads['prepared/zonetool.cpp'].decode(), read)
    marker.update(BaseMainBytes=material_parts.BASE_MAIN[0], BaseMainSHA256=material_parts.BASE_MAIN[1],
                  BaseCLIBytes=material_parts.BASE_CLI[0], BaseCLISHA256=material_parts.BASE_CLI[1])
    return main.encode(), cli.encode(), marker
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
REFERENCE_SOURCE_PINS = {**reference_probe.PINS,
    'prepare_prepatch_reference.py': (3665, '89f3f26699f1240400c4bd96f2987963374658e55a8501cab7dc2543a84ceace')}
LINK_SOURCE_PINS = {**link_probe.PINS,
    'prepare_prepatch_link_v3.py': (2236, '66f70ca5a979745288232d76496a339e08d639ddf34560aada6e6b63c5bcffa1')}
CALLER_SOURCE_PINS = {**caller_probe.PINS,
    'prepare_prepatch_image_caller.py': (2749, '8e6edee60d06dda0c77f8f2cf73bd39677523f0ba046ced2046218cc7eb7d7a2')}

# Source25 approved module; this finite C transition does not relax E4 reuse.
ZOMBIES_SOURCE_PINS = {
    'native_catalog_zombies_observation.inc': (9668, '50361fbd5deb38b7410e31b995b1dcd7cdf6e43f04dc81835ed213f74155d181'),
    'prepare_catalog_zombies_observation.py': (7613, '1bf133356025893ff59c4d3de7e3614ac60f00a098f16b4b707e0eaa012da445'),
}
ZOMBIES_BASE_CLI_PIN = (107785, 'c480fbd39525df09bd5677026678743c73fa66eb3ca0752e78729eee2f4dcc50')
ZOMBIES_CLI_PIN = (118485, '917c2f9025185d23a8b2b683157144c2da62fe747f17f11e0f8c1abcf66be987')


def zombies_observation_selected(args):
    selected = getattr(args, 'zombies_catalogue_observation', False)
    require(type(selected) is bool, 'Explicit boolean Zombies observation selector required')
    if selected:
        require(getattr(args, 'catalog_message_publication', False) is True and
                getattr(args, 'selected_streamed_static_v1', False) is True and
                getattr(args, 'selected_streamed_render_only_v2', False) is False and
                getattr(args, 'zombies_add_observation_c2', False) is False and
                bool(getattr(args, 'reuse_plan', None)) and bool(getattr(args, 'reuse_compile_receipt', None)),
                'Zombies observation requires explicit publication, selected-streamed and retained proofs')
    return selected


def zombies_observation_transition(raw):
    require(type(raw) is bytes and (len(raw), hashlib.sha256(raw).hexdigest()) == ZOMBIES_BASE_CLI_PIN,
            'Exact current publication CLI required before Zombies observation')
    for name, pin in ZOMBIES_SOURCE_PINS.items():
        source = (HERE/name).read_bytes()
        require((len(source), hashlib.sha256(source).hexdigest()) == pin, 'Approved Zombies observation source differs')
    rendered = zombies_observer.wire_cli(raw.decode('utf-8')).encode()
    require((len(rendered), hashlib.sha256(rendered).hexdigest()) == ZOMBIES_CLI_PIN,
            'Exact reviewed Zombies observation transition required')
    return rendered, {'Schema':'iw7.t7-zm-observation-build/1', 'SourceProfile':zombies_observer.SOURCE_PROFILE,
        'BaseCLIBytes':ZOMBIES_BASE_CLI_PIN[0], 'BaseCLISHA256':ZOMBIES_BASE_CLI_PIN[1],
        'CLIBytes':ZOMBIES_CLI_PIN[0], 'CLISHA256':ZOMBIES_CLI_PIN[1]}


# C2 is a separate finite transition from the reviewed render-only V2 factory.
# Frozen C/V1 source pins and transition above stay unchanged.
ADD_SOURCE_PINS = {
    'native_catalog_add_observation.inc': (6397, 'fe37357ad1f3162f24ae79af51f325763b81e05851eb263f8681b5558835f11d'),
    'prepare_catalog_add_observation.py': (6156, 'cf6551b918e21d0046136ea3e328494960b70a62334bc3f2727e0a52fee5ec6f'),
}
ADD_BASE_CLI_PIN = (112377, 'c63d9552464da674d3b03c35f7edc16385fb9370b113a3925fd7bc4835fb005a')
ADD_CLI_PIN = (119139, '19af683d0c609d43cefc7c93dd3d7fa6f7ae1a6f5b90d2945d37b1830bda1111')


def add_observation_selected(args):
    selected = getattr(args, 'zombies_add_observation_c2', False)
    require(type(selected) is bool, 'Explicit boolean C2 observation selector required')
    if selected:
        require(getattr(args, 'catalog_message_publication', False) is True and
                getattr(args, 'selected_streamed_render_only_v2', False) is True and
                getattr(args, 'selected_streamed_static_v1', False) is False and
                getattr(args, 'zombies_catalogue_observation', False) is False and
                bool(getattr(args, 'reuse_plan', None)) and bool(getattr(args, 'reuse_compile_receipt', None)),
                'C2 requires exclusive explicit publication, render-only V2 and retained proofs')
    return selected


def add_observation_transition(raw):
    require(type(raw) is bytes and (len(raw), hashlib.sha256(raw).hexdigest()) == ADD_BASE_CLI_PIN,
            'Exact render-only V2 publication CLI required before C2')
    for name, pin in ADD_SOURCE_PINS.items():
        source = (HERE/name).read_bytes()
        require((len(source), hashlib.sha256(source).hexdigest()) == pin, 'Approved C2 source differs')
    rendered = add_observer.wire_cli(raw.decode('utf-8')).encode()
    require((len(rendered), hashlib.sha256(rendered).hexdigest()) == ADD_CLI_PIN,
            'Exact reviewed C2 source transition required')
    return rendered, {'Schema':'iw7.t7-zm-add-observation-build/1', 'SourceProfile':add_observer.SOURCE_PROFILE,
        'BaseCLIBytes':ADD_BASE_CLI_PIN[0], 'BaseCLISHA256':ADD_BASE_CLI_PIN[1],
        'CLIBytes':ADD_CLI_PIN[0], 'CLISHA256':ADD_CLI_PIN[1]}


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
                      resident_multisurface_v2=False, selected_streamed_static_v1=False, selected_streamed_render_only_v2=False,
                      prepatch_reference_v2=False, prepatch_link_v3=False, prepatch_image_caller_v1=False):
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
    require(type(selected_streamed_static_v1) is bool and
            (not selected_streamed_static_v1 or resident_multisurface_v2), 'Explicit selected-streamed reuse required')
    require(type(selected_streamed_render_only_v2) is bool and
            not (selected_streamed_static_v1 and selected_streamed_render_only_v2) and
            (not selected_streamed_render_only_v2 or resident_multisurface_v2), 'Explicit render-only reuse required')
    transitions = (prepare_catalog_trace.RENDER_ONLY_STREAMED_TRANSITIONS if selected_streamed_render_only_v2 else
                   prepare_catalog_trace.SELECTED_STREAMED_TRANSITIONS if selected_streamed_static_v1 else
                   prepare_catalog_trace.MULTISURFACE_TRANSITIONS)
    wired_pins = (prepare_catalog_trace.RENDER_ONLY_STREAMED_WIRED_PINS if selected_streamed_render_only_v2 else
                  prepare_catalog_trace.SELECTED_STREAMED_WIRED_PINS if selected_streamed_static_v1 else
                  prepare_catalog_trace.MULTISURFACE_WIRED_PINS)
    header_evidence = surface_count_dependencies is not None
    diagnostic = header_evidence and not resident_multisurface_v2
    require((e7_dependency_text is not None) == header_evidence and
            (not resident_multisurface_v2 or header_evidence) and
            (not header_evidence or (recompile_main is True and catalog_trace is True and recompile_zonetool is True)),
            'Surface-count diagnostic requires both fresh TUs and complete dependency evidence')
    diagnostic_proof = None
    if resident_multisurface_v2:
        require(all(prepare_catalog_trace.multisurface_payload_delta(name, payloads.get(name),
                    prior_bindings.get(key(prepared/name.removeprefix('prepared/'))), wired=True,
                    selected_streamed=selected_streamed_static_v1, render_only_streamed=selected_streamed_render_only_v2) for name in transitions),
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
                    'WiredBytes':wired_pins[name][0], 'WiredSHA256':wired_pins[name][1]}
                    for name,(old,new) in transitions.items()])
    require(type(prepatch_reference_v2) is bool and (not prepatch_reference_v2 or
            (recompile_main is True and catalog_trace is False and recompile_zonetool is False and
             not resident_multisurface_v2 and not selected_streamed_static_v1 and not selected_streamed_render_only_v2)),
            'Prepatch V2 requires its exclusive main/link profile')
    require(type(prepatch_link_v3) is bool and (not prepatch_link_v3 or
            (not prepatch_reference_v2 and recompile_main is True and catalog_trace is False and recompile_zonetool is False and
             not resident_multisurface_v2 and not selected_streamed_static_v1 and not selected_streamed_render_only_v2)),
            'Prepatch V3 requires its exclusive main/link profile')
    require(type(prepatch_image_caller_v1) is bool and (not prepatch_image_caller_v1 or
            (not prepatch_reference_v2 and not prepatch_link_v3 and recompile_main is True and
             catalog_trace is False and recompile_zonetool is False and not resident_multisurface_v2 and
             not selected_streamed_static_v1 and not selected_streamed_render_only_v2)),
            'Image-caller requires its exclusive fixture/main/link profile')
    prepatch_module = (caller_probe.HELPER if prepatch_image_caller_v1 else link_probe.HELPER if prepatch_link_v3
                       else reference_probe.HELPER if prepatch_reference_v2 else prepare_prepatch.HELPER)
    if recompile_main and not catalog_trace: expected_payloads.add('prepared/'+prepatch_module)
    if prepatch_image_caller_v1: expected_payloads.add('prepared/'+caller_probe.GUARD)
    require({n for n in payloads if n.startswith('prepared/')} == expected_payloads,
            'Exact native payload inventory required for reuse')
    old_text = []
    for name, raw in payloads.items():
        if not name.startswith('prepared/'): continue
        if prepatch_image_caller_v1 and name == 'prepared/'+caller_probe.GUARD:
            reference_probe.require_pin(raw,caller_probe.PINS[caller_probe.GUARD],'image-caller range guard')
            continue
        if recompile_main and not catalog_trace and name == 'prepared/'+prepatch_module:
            require(0 < len(raw) <= 64*1024, 'Bounded pre-patch helper required')
            if prepatch_reference_v2: reference_probe.require_pin(raw, reference_probe.PINS[prepatch_module], 'helper')
            if prepatch_link_v3: reference_probe.require_pin(raw, link_probe.PINS[prepatch_module], 'V3 helper')
            if prepatch_image_caller_v1: reference_probe.require_pin(raw,caller_probe.PINS[prepatch_module],'image-caller helper')
            continue
        path = prepared/name.removeprefix('prepared/')
        pin = prior_bindings.get(key(path))
        if resident_multisurface_v2 and prepare_catalog_trace.multisurface_payload_delta(name, raw, pin, wired=True,
                selected_streamed=selected_streamed_static_v1, render_only_streamed=selected_streamed_render_only_v2):
            old_text.append(pin)
            continue
        if diagnostic and prepare_catalog_trace.surface_count_header_delta(name, raw, pin):
            old_text.append(pin)
            continue
        if (recompile_main and name == 'prepared/main.cpp') or (recompile_zonetool and name == 'prepared/zonetool.cpp'):
            if prepatch_reference_v2:
                require(pin and (pin['Bytes'],pin['SHA256']) == reference_probe.RETAINED_MAIN,
                        'Prepatch V2 must retain its exact base main')
                reference_probe.require_pin(raw, reference_probe.MAIN, 'wired main')
            if prepatch_link_v3:
                require(pin and (pin['Bytes'],pin['SHA256']) == link_probe.RETAINED_MAIN,
                        'Prepatch V3 must retain its exact C base main')
                reference_probe.require_pin(raw,link_probe.MAIN,'V3 wired main')
            if prepatch_image_caller_v1:
                require(pin and (pin['Bytes'],pin['SHA256']) == caller_probe.RETAINED_MAIN,
                        'Image-caller must retain its exact C base main')
                reference_probe.require_pin(raw,caller_probe.MAIN,'image-caller wired main')
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
            **({'SelectedStreamedStaticV1':{'Schema':'iw7.t7-selected-streamed-static-build/1',
                'GeometryProfile':'t7-iw7-selected-streamed-static-v1'}} if selected_streamed_static_v1 else {}),
            **({'SelectedStreamedRenderOnlyV2':{'Schema':'iw7.t7-selected-streamed-render-only-build/2',
                'GeometryProfile':'t7-iw7-selected-streamed-render-only-v2',
                'CollisionPolicy':'omit-source-rigid-collision-trees'}} if selected_streamed_render_only_v2 else {}),
            'StageRoots':[str(old_root/obj[:-4]) for _,obj,_ in reused_units]}, inputs, old_text


def require_preparation_bounds(raw, payloads, *, parts_profile=False, provenance_profile=False, metadata_profile=False, registration_profile=False, incoming_profile=False, bindings_profile=False):
    require(type(parts_profile) is bool, 'Explicit parts preparation profile required')
    require(type(provenance_profile) is bool and not (parts_profile and provenance_profile),
            'Exclusive explicit provenance preparation profile required')
    require(type(metadata_profile) is bool and (not metadata_profile or provenance_profile),
            'Finite metadata extension requires provenance preparation')
    # Only the closed, explicitly selected G3 source transition gets this cap.
    # This bounds authored output bytes, not RAM/commit admission or asset reads.
    require(type(registration_profile) is bool and (not registration_profile or metadata_profile),
            'Registration payload requires its exact metadata base')
    require(type(incoming_profile) is bool and (not incoming_profile or registration_profile),
            'Incoming payload requires its exact registration base')
    require(type(bindings_profile) is bool and (not bindings_profile or (registration_profile and not incoming_profile)),
            'Bindings payload requires its exclusive registration base')
    payload_limit = (448 if incoming_profile or bindings_profile else 384 if registration_profile else 320 if metadata_profile else 288 if parts_profile or provenance_profile else 256) * 1024
    require(len(raw) <= 2*1024**2 and sum(map(len,payloads.values())) <= payload_limit,
            'Preparation bound exceeded')


OS_RESOURCE_PATH = r'C:\WINDOWS\SYSTEM32\TZRES.DLL'
OS_RESOURCE_BEFORE = 'f3f5ef83a67c503991d728f62cf039cbb52a18d6eb82197dec23ede8f0996108'
OS_RESOURCE_AFTER = '1398cf1d866e49a8ba351e2a30a7803b50c8b595d17f776abe8d2ec4a9c6fb10'
OS_RESOURCE_PROOF = (8907, '5a282c19995af210fd9d7c55a8692d87d4456526352fe21034a8f07d83a9fd9d')


def os_resource_selected(args):
    flag = getattr(args, 'os_context_tzres_20261014', False)
    proof = getattr(args, 'os_context_proof', None)
    require(type(flag) is bool and bool(proof) == flag, 'Explicit paired TZRES context/proof required')
    if flag:
        require(getattr(args, 'material_parts_v1', False) is True or
                getattr(args, 'prepatch_link_v3', False) is True or
                getattr(args, 'prepatch_image_caller_v1', False) is True or
                getattr(args, 'image_provenance_v1', False) is True,
                'TZRES context requires explicit parts, provenance or V3')
    return flag


def os_resource_context(path, read, expected):
    raw = read(path, 16*1024, OS_RESOURCE_PROOF[1])
    require(len(raw) == OS_RESOURCE_PROOF[0], 'Exact dated OS qualification proof required')
    proof = json.loads(raw)
    require(type(proof) is dict and proof.get('Schema') == 'iw7.t7-os-resource-qualification/1' and
            proof.get('Status') == 'ObservationComplete' and proof.get('GuardsDisposed') is True and
            proof.get('LeaseReleased') is True and proof.get('Ready') is False and
            proof.get('CPPExecuted') is False and proof.get('CandidateExecuted') is False and
            proof.get('StockRead') is False and proof.get('Postflight', {}).get('Leases') == [],
            'Closed non-native OS qualification required')
    resource = proof.get('OSResource', {})
    required = dict(Path=OS_RESOURCE_PATH, HistoricalBytes=12288, HistoricalSHA256=OS_RESOURCE_BEFORE,
        ObservedBytes=12288, ObservedSHA256=OS_RESOURCE_AFTER, ProductVersion='10.0.26100.9711',
        CompanyName='Microsoft Corporation', SignatureStatus='Valid', SignatureType='Catalog',
        SignerSubject='CN=Microsoft Windows, O=Microsoft Corporation, L=Redmond, S=Washington, C=US',
        SignerThumbprint='667BBA1E1F478221AA65DE4F75187A751B03A453', ContractAccepted=False, PinAdopted=False)
    require(all(type(resource.get(k)) is type(v) and resource[k] == v for k,v in required.items()),
            'Exact measured Microsoft TZRES resource required')
    require(type(proof.get('Pins')) is list and len(proof['Pins']) == 10 and
            all(p.get('GuardPassed') is True and p.get('ExpectedBytes') == p.get('ActualBytes') and
                p.get('ExpectedSHA256') == p.get('ActualSHA256') for p in proof['Pins']),
            'Exact unchanged D/V3 suffix qualification required')
    before = dict(Path=OS_RESOURCE_PATH, Bytes=12288, SHA256=OS_RESOURCE_BEFORE)
    require(expected.get(key(OS_RESOURCE_PATH)) == before, 'Historical TZRES pin must remain exact')
    after = dict(before, SHA256=OS_RESOURCE_AFTER)
    expected[key(OS_RESOURCE_PATH)] = after
    return dict(Schema='iw7.t7-os-resource-context/1', Name='windows-tzres-20261014', SourceOSDate='2026-10-14',
        Before=before, After=after, Evidence=dict(Path=str(path), Bytes=OS_RESOURCE_PROOF[0], SHA256=OS_RESOURCE_PROOF[1]),
        ProductVersion='10.0.26100.9711', SignatureStatus='Valid', SignatureType='Catalog',
        SignerThumbprint=required['SignerThumbprint'], KBFileAttributionVerified=False)


def incoming_build_transition(main, cli, registration_observer, registration_args, read):
    """Bounded authored-source/RSP transition, usable without prepare()/SDK/tlogs."""
    read(HERE/'prepare_incoming_image_metadata.py',32*1024)
    base_main,base_cli=main,cli
    main,cli=incoming_metadata.overlay(main,cli,read)
    marker={'Schema':'iw7.t7-incoming-image-build/1','SourceProfile':incoming_metadata.NAME,
        'SourceOnlyPending':True,'CPPQualified':False,'Ready':False,
        'BaseMainBytes':len(base_main.encode()),'BaseMainSHA256':hashlib.sha256(base_main.encode()).hexdigest(),
        'BaseCLIBytes':len(base_cli.encode()),'BaseCLISHA256':hashlib.sha256(base_cli.encode()).hexdigest(),
        'MainBytes':len(main.encode()),'MainSHA256':hashlib.sha256(main.encode()).hexdigest(),
        'CLIBytes':len(cli.encode()),'CLISHA256':hashlib.sha256(cli.encode()).hexdigest()}
    capture=read(HERE/registration_metadata.CAPTURE,32*1024,incoming_metadata.BASE_CAPTURE[1]).replace(b'\r\n',b'\n')
    members=read(HERE/incoming_metadata.MEMBERS,16*1024).replace(b'\r\n',b'\n')
    fixture=read(HERE/registration_metadata.FIXTURE,32*1024,incoming_metadata.BASE_FIXTURE[1]).replace(b'\r\n',b'\n')
    generated={
        'prepared/selected_image_incoming_capture.hpp':incoming_metadata.capture_source(capture,members).encode(),
        'prepared/selected_image_incoming_observer.hpp':incoming_metadata.observer_source(registration_observer).encode(),
        'prepared/incoming_registration_baseline_fixture.cpp':incoming_metadata.fixture_source(fixture).encode()}
    incoming_args=registration_args.copy()
    old_fixture=str(HERE/registration_metadata.FIXTURE)
    require(incoming_args.count(old_fixture)==1,'Exact one baseline registration fixture argument required')
    incoming_args[incoming_args.index(old_fixture)]=str(HERE/incoming_metadata.FIXTURE)
    return main,cli,marker,generated,incoming_args


def prepare(args):
    image_observation = image_provenance_selected(args)
    image_metadata_enabled = image_metadata.selected(args)
    registration_enabled = registration_metadata.selected(args)
    incoming_enabled = incoming_metadata.selected(args)
    bindings_enabled = bindings_build.selected(args)
    fixture_proof_root = image_fixture_proof_requested(args)
    os_context_enabled = os_resource_selected(args)
    parts_observation = material_parts.selected(args)
    zombies_observation = zombies_observation_selected(args)
    add_observation = add_observation_selected(args)
    source, e7, output, run, adapter, providers, job = [path_checked(getattr(args, n)) for n in
        ('source', 'e7', 'output', 'run', 'adapter', 'providers', 'job')]
    runtime = HERE.parents[2]/'runtime'
    require(output.parent == runtime and run.parent == runtime and output != run and
            not output.exists() and not run.exists(), 'Separate fresh owned runtime roots required')
    text_inputs = []
    def read(path, limit=1024*1024, expected=None):
        raw, pin = text_pin(path, limit, expected); text_inputs.append(pin); return raw
    fixture_proof = image_fixture_proof(fixture_proof_root, read) if fixture_proof_root is not None else None
    cl_raw = read(e7/'obj/tlog/CL.command.1.tlog', 4*1024**2, CL_LOG_SHA)
    link_raw = read(e7/'obj/tlog/link.command.1.tlog', 256*1024, LINK_LOG_SHA)
    cl, link = cl_raw.decode('utf-16'), link_raw.decode('utf-16')
    payloads, replaced = command_payloads(cl, link, source, output/'prepared', run)
    _, patched = prepare_cli.render(source)
    prepatch_helper = getattr(args, 'prepatch_helper', None)
    prepatch_reference_v2 = getattr(args, 'prepatch_reference_v2', False)
    require(type(prepatch_reference_v2) is bool, 'Explicit prepatch V2 boolean required')
    prepatch_link_v3 = getattr(args, 'prepatch_link_v3', False)
    link_base_plan = getattr(args, 'prepatch_link_v3_base_plan', None)
    require(type(prepatch_link_v3) is bool and bool(link_base_plan) == prepatch_link_v3,
            'Prepatch V3 requires its exclusive exact V2 base plan')
    prepatch_image_caller_v1 = getattr(args, 'prepatch_image_caller_v1', False)
    caller_base_plan = getattr(args, 'prepatch_image_caller_v1_base_plan', None)
    require(type(prepatch_image_caller_v1) is bool and bool(caller_base_plan) == prepatch_image_caller_v1,
            'Image-caller requires its exclusive exact V3 base plan')
    catalog_publication = bool(getattr(args, 'catalog_message_publication', False))
    surface_count_diagnostic = getattr(args, 'resident_surface_count_diagnostic', False)
    selected_streamed_static_v1 = getattr(args, 'selected_streamed_static_v1', False)
    selected_streamed_render_only_v2 = getattr(args, 'selected_streamed_render_only_v2', False)
    resident_requested = getattr(args, 'resident_multisurface_v2', False)
    require(type(selected_streamed_static_v1) is bool and type(selected_streamed_render_only_v2) is bool and
            type(resident_requested) is bool and sum((selected_streamed_static_v1,selected_streamed_render_only_v2,resident_requested)) <= 1, 'One explicit resident or selected-streamed profile required')
    resident_multisurface_v2 = resident_requested or selected_streamed_static_v1 or selected_streamed_render_only_v2
    require(type(resident_multisurface_v2) is bool and
            (not resident_multisurface_v2 or (catalog_publication and surface_count_diagnostic is False)),
            'Multisurface v2 requires exclusive two-TU publication selection')
    require(type(surface_count_diagnostic) is bool and (not surface_count_diagnostic or catalog_publication),
            'Surface-count diagnostic requires the existing main/CLI publication profile')
    catalog_message = bool(getattr(args, 'catalog_message', False) or catalog_publication)
    catalog_callers = bool(getattr(args, 'catalog_callers', False) or catalog_message)
    catalog_exit = bool(getattr(args, 'catalog_exit', False) or catalog_callers)
    catalog_trace = bool(getattr(args, 'catalog_trace', False) or catalog_exit)
    require(sum(map(bool, (prepatch_helper, prepatch_reference_v2, prepatch_link_v3, prepatch_image_caller_v1, getattr(args, 'catalog_trace', False),
                          getattr(args, 'catalog_exit', False), getattr(args, 'catalog_callers', False),
                          getattr(args, 'catalog_message', False), catalog_publication))) <= 1,
            'Pre-patch and catalogue diagnostic profiles are exclusive')
    require(bool(getattr(args, 'ordinary_plan', None)) == catalog_trace and
            bool(getattr(args, 'ordinary_receipt', None)) == catalog_trace,
            'Catalogue trace requires both ordinary D2 text proofs')
    recompile_main = bool(prepatch_helper or prepatch_reference_v2 or prepatch_link_v3 or prepatch_image_caller_v1 or catalog_trace)
    if recompile_main:
        require(args.reuse_plan and args.reuse_compile_receipt, 'Main rebuild must reuse qualified prior compilation')
    if prepatch_helper:
        payloads['prepared/'+prepare_prepatch.HELPER] = read(prepatch_helper,64*1024)
        patched[prepare_cli.PATHS[0]] = prepare_prepatch.wire_main(patched[prepare_cli.PATHS[0]])
    elif prepatch_reference_v2:
        payloads['prepared/'+reference_probe.HELPER] = read(HERE/reference_probe.HELPER,64*1024).replace(b'\r\n',b'\n')
        patched[prepare_cli.PATHS[0]] = reference_probe.wire_main(patched[prepare_cli.PATHS[0]])
    for path, _, relative in UNITS: payloads['prepared/'+relative] = patched[path].encode()
    link_base_main = None
    if prepatch_link_v3:
        payloads['prepared/'+link_probe.HELPER] = read(HERE/link_probe.HELPER,64*1024).replace(b'\r\n',b'\n')
        payloads['prepared/main.cpp'],link_base_main = link_probe.prepared_main(read(link_base_plan,1024**2),read)
    caller_base_main = None
    if prepatch_image_caller_v1:
        for name in (caller_probe.HELPER,caller_probe.GUARD):
            payloads['prepared/'+name] = read(HERE/name,64*1024).replace(b'\r\n',b'\n')
        payloads['prepared/main.cpp'],caller_base_main = caller_probe.prepared_main(read(caller_base_plan,1024**2),read)
    payloads['prepared/common/xpak.hpp'] = patched[prepare_cli.PATHS[3]].encode()
    contract = json.loads(read(HERE/'cli-source-contract.json'))
    external = contract['external_adapter']
    for name, pin in [('t7_iw7_resident_model.hpp', external), ('t7_asset_name.hpp', external['required_sibling']),
                      ('test_t7_asset_name.cpp', external['native_boundary_fixture'])]:
        raw = read(adapter/name).decode().replace('\r\n', '\n').encode()
        require(hashlib.sha256(raw).hexdigest() == pin['lf_sha256'] and len(raw) == pin['lf_bytes'], 'Exact conversion header/fixture required')
        payloads['prepared/'+name] = raw
    if prepatch_reference_v2 or prepatch_link_v3 or prepatch_image_caller_v1:
        payloads.update(reference_probe.retained_payloads(read(args.reuse_plan,2*1024**2),
            read(args.reuse_compile_receipt,128*1024),read))
    for name, pin in contract['files'].items():
        raw = read(HERE/name).decode().replace('\r\n', '\n').encode()
        require(hashlib.sha256(raw).hexdigest() == pin['lf_sha256'], 'CLI source contract differs')
    if prepatch_reference_v2:
        expected_reference = {'schema':reference_probe.BUILD_SCHEMA,'source_profile':reference_probe.NAME,
            'files':{name:{'lf_bytes':pin[0],'lf_sha256':pin[1]} for name,pin in REFERENCE_SOURCE_PINS.items()}}
        require(contract.get('prepatch_reference_v2') == expected_reference, 'Exact prepatch V2 source contract required')
        for name,pin in REFERENCE_SOURCE_PINS.items():
            reference_probe.require_pin(read(HERE/name,64*1024).replace(b'\r\n',b'\n'),pin,name)
    if prepatch_link_v3:
        expected_link = {'schema':link_probe.BUILD_SCHEMA,'source_profile':link_probe.NAME,
            'files':{name:{'lf_bytes':pin[0],'lf_sha256':pin[1]} for name,pin in LINK_SOURCE_PINS.items()}}
        require(contract.get('prepatch_link_v3') == expected_link,'Exact prepatch V3 source contract required')
        for name,pin in LINK_SOURCE_PINS.items():
            reference_probe.require_pin(read(HERE/name,64*1024).replace(b'\r\n',b'\n'),pin,name)
    if prepatch_image_caller_v1:
        expected_caller = {'schema':caller_probe.BUILD_SCHEMA,'source_profile':caller_probe.NAME,
            'files':{name:{'lf_bytes':pin[0],'lf_sha256':pin[1]} for name,pin in CALLER_SOURCE_PINS.items()}}
        require(contract.get('prepatch_image_caller_v1') == expected_caller,'Exact image-caller Source contract required')
        for name,pin in CALLER_SOURCE_PINS.items():
            reference_probe.require_pin(read(HERE/name,64*1024).replace(b'\r\n',b'\n'),pin,name)
    for name in ('prepare_build.py', 'prepare_prepatch.py', 'Run-T7Build.ps1', 'T7Build.Profile.ps1'):
        read(HERE/name)
    if prepatch_reference_v2:
        for name in ('prepare_prepatch_reference.py', *reference_probe.PINS): read(HERE/name,64*1024)
    if catalog_trace: read(HERE/'prepare_catalog_trace.py')
    if catalog_publication:
        read(HERE/'prepare_message_publication.py',64*1024)
        read(HERE/'native_message_publication.inc',16*1024)
    if zombies_observation:
        for name, pin in ZOMBIES_SOURCE_PINS.items():
            raw = read(HERE/name,16*1024,pin[1])
            require(len(raw) == pin[0], 'Approved Zombies observation source length differs')
    if add_observation:
        for name, pin in ADD_SOURCE_PINS.items():
            raw = read(HERE/name,16*1024,pin[1])
            require(len(raw) == pin[0], 'Approved C2 observation source length differs')
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
    os_context = os_resource_context(args.os_context_proof, read, expected) if os_context_enabled else None
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
                resident_multisurface_v2=resident_multisurface_v2, selected_streamed_static_v1=selected_streamed_static_v1, selected_streamed_render_only_v2=selected_streamed_render_only_v2)
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
            resident_multisurface_v2=resident_multisurface_v2, selected_streamed_static_v1=selected_streamed_static_v1, selected_streamed_render_only_v2=selected_streamed_render_only_v2,
            prepatch_reference_v2=prepatch_reference_v2, prepatch_link_v3=prepatch_link_v3,
            prepatch_image_caller_v1=prepatch_image_caller_v1)
        if prepatch_reference_v2: reuse['PrepatchReferenceV2'] = reference_probe.marker()
        if prepatch_link_v3: reuse['PrepatchLinkV3'] = link_probe.marker()
        if prepatch_image_caller_v1: reuse['PrepatchImageCallerV1'] = caller_probe.marker()
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
    if prepatch_image_caller_v1:
        fixture_root = run/'caller-fixture-compile'
        fixture_args = ['/nologo','/std:c++20','/EHsc','/W4','/WX','/MT','/Od','/Z7','/I'+str(HERE),
            '/sourceDependencies',str(fixture_root/'dependencies.json'),
            '/Fo'+str(fixture_root/'caller-fixture.obj'),'/Fe'+str(fixture_root/'caller-fixture.exe'),
            str(HERE/caller_probe.FIXTURE),'/link','/INCREMENTAL:NO','/DEBUG','/PDB:'+str(fixture_root/'caller-fixture.pdb')]
        payloads['caller-fixture.rsp'] = ' '.join(map(quote,fixture_args)).encode()
        stages = [dict(Name='caller-fixture-compile',Stage='Compile',Image=str(compiler_dir/'cl.exe'),
                       Arguments=['@'+str(output/'caller-fixture.rsp')],DeadlineSeconds=120,
                       Artifacts=['caller-fixture.obj','caller-fixture.exe','caller-fixture.pdb','dependencies.json']),
                  dict(Name='caller-fixture-test',Stage='Probe',Image=str(fixture_root/'caller-fixture.exe'),
                       Arguments=[],DeadlineSeconds=15,Artifacts=[])] + stages
    if zombies_observation:
        require(reuse is not None and catalog_publication and selected_streamed_static_v1,
                'Zombies observation requires the verified current publication reuse closure')
        payloads['prepared/zonetool.cpp'], reuse['ZombiesObservationC'] = zombies_observation_transition(
            payloads['prepared/zonetool.cpp'])
    if add_observation:
        require(reuse is not None and catalog_publication and selected_streamed_render_only_v2,
                'C2 requires the verified render-only V2 publication reuse closure')
        payloads['prepared/zonetool.cpp'], reuse['ZombiesAddObservationC2'] = add_observation_transition(
            payloads['prepared/zonetool.cpp'])
    if parts_observation:
        require(reuse is not None and catalog_publication and selected_streamed_render_only_v2,
                'Parts metadata requires the verified E5 publication reuse closure')
        read(HERE/'prepare_material_parts.py', 32*1024)
        main, cli, marker = material_parts.overlay(payloads['prepared/main.cpp'].decode(),
                                                   payloads['prepared/zonetool.cpp'].decode(), read)
        payloads['prepared/main.cpp'], payloads['prepared/zonetool.cpp'] = main.encode(), cli.encode()
        reuse['MaterialParts'] = marker
    if image_observation:
        require(reuse is not None and catalog_publication and selected_streamed_render_only_v2,
                'Image provenance requires the verified E5 publication reuse closure')
        payloads['prepared/main.cpp'], payloads['prepared/zonetool.cpp'], reuse['ImageProvenance'] = \
            image_provenance_transition(payloads, read)
        if image_metadata_enabled:
            read(HERE/'prepare_image_metadata.py', 16*1024)
            main, cli, reuse['ImageMetadata'] = image_metadata.overlay(
                payloads['prepared/main.cpp'].decode(), payloads['prepared/zonetool.cpp'].decode(), read)
            payloads['prepared/main.cpp'], payloads['prepared/zonetool.cpp'] = main.encode(), cli.encode()
            observer = read(HERE/'selected_material_observation.hpp', 32*1024,
                            material_parts.BASE_OBSERVER[1]).replace(b'\r\n', b'\n')
            payloads['prepared/'+image_metadata.GUARDED_OBSERVER] = image_metadata.guarded_observer_source(observer).encode()
            read(HERE/'selected_image_metadata_guard_fixture.cpp', 16*1024)
            fixture_root = run/'metadata-fixture-compile'
            fixture_args = ['/nologo', '/std:c++20', '/EHsc', '/W4', '/WX', '/MT', '/Od', '/Z7', '/external:W0',
                '/external:I'+str(source/'src/zonetool'),
                '/external:I'+str(source/'deps/json/single_include/nlohmann'),
                '/I'+str(HERE), '/I'+str(output/'prepared'),
                '/sourceDependencies', str(fixture_root/'dependencies.json'),
                '/Fo'+str(fixture_root/'metadata-fixture.obj'), '/Fe'+str(fixture_root/'metadata-fixture.exe'),
                str(HERE/'selected_image_metadata_guard_fixture.cpp'), '/link', '/INCREMENTAL:NO',
                '/DEBUG', '/PDB:'+str(fixture_root/'metadata-fixture.pdb')]
            payloads['metadata-fixture.rsp'] = ' '.join(map(quote, fixture_args)).encode()
            stages = [dict(Name='metadata-fixture-compile', Stage='Compile', Image=str(compiler_dir/'cl.exe'),
                           Arguments=['@'+str(output/'metadata-fixture.rsp')], DeadlineSeconds=120,
                           Artifacts=['metadata-fixture.obj','metadata-fixture.exe','metadata-fixture.pdb','dependencies.json']),
                      dict(Name='metadata-fixture-test', Stage='Probe', Image=str(fixture_root/'metadata-fixture.exe'),
                           Arguments=[], DeadlineSeconds=15, Artifacts=[])] + stages
            if registration_enabled:
                read(HERE/'prepare_image_registration_metadata.py', 32*1024)
                main, cli, reuse['RegistrationMetadata'] = registration_metadata.overlay(main, cli, read)
                payloads['prepared/main.cpp'], payloads['prepared/zonetool.cpp'] = main.encode(), cli.encode()
                f2observer = read(HERE/image_provenance.HELPER, 32*1024,
                                  registration_metadata.BASE_OBSERVER[1]).replace(b'\r\n', b'\n')
                payloads['prepared/selected_image_registration_observer.hpp'] = registration_metadata.observer_source(f2observer).encode()
                registration_root = run/'registration-fixture-compile'
                registration_args = ['/nologo', '/std:c++20', '/EHsc', '/W4', '/WX', '/MT', '/Od', '/Z7', '/external:W0',
                    '/external:I'+str(source/'src/zonetool'),
                    '/external:I'+str(source/'deps/json/single_include/nlohmann'),
                    '/I'+str(HERE), '/I'+str(output/'prepared'),
                    '/sourceDependencies', str(registration_root/'dependencies.json'),
                    '/Fo'+str(registration_root/'registration-fixture.obj'), '/Fe'+str(registration_root/'registration-fixture.exe'),
                    str(HERE/registration_metadata.FIXTURE), '/link', '/INCREMENTAL:NO',
                    '/DEBUG', '/PDB:'+str(registration_root/'registration-fixture.pdb')]
                payloads['registration-fixture.rsp'] = ' '.join(map(quote, registration_args)).encode()
                # The new API has its own 39-check gate. Do not relabel the
                # unchanged historical mapper54/guard13 as this actual fixture.
                stages = [dict(Name='registration-fixture-compile', Stage='Compile', Image=str(compiler_dir/'cl.exe'),
                               Arguments=['@'+str(output/'registration-fixture.rsp')], DeadlineSeconds=120,
                               Artifacts=['registration-fixture.obj','registration-fixture.exe','registration-fixture.pdb','dependencies.json']),
                          dict(Name='registration-fixture-test', Stage='Probe', Image=str(registration_root/'registration-fixture.exe'),
                               Arguments=[], DeadlineSeconds=15, Artifacts=[])] + stages[2:]
                if incoming_enabled:
                    main,cli,reuse['IncomingObservation'],generated,incoming_args=incoming_build_transition(
                        main,cli,payloads['prepared/selected_image_registration_observer.hpp'],registration_args,read)
                    payloads['prepared/main.cpp'],payloads['prepared/zonetool.cpp']=main.encode(),cli.encode()
                    payloads.update(generated)
                    payloads['registration-fixture.rsp']=' '.join(map(quote,incoming_args)).encode()
                if bindings_enabled:
                    main,cli,reuse['RegistrationBindingsObservation'],generated,bindings_args=bindings_build.transition(
                        main,cli,payloads['prepared/selected_image_registration_observer.hpp'],registration_args,read,output/'prepared')
                    payloads['prepared/main.cpp'],payloads['prepared/zonetool.cpp']=main.encode(),cli.encode()
                    payloads.update(generated)
                    payloads['registration-fixture.rsp']=' '.join(map(quote,bindings_args)).encode()
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
    if prepatch_image_caller_v1:
        profile = {'Name':caller_probe.NAME,'Option':caller_probe.OPTION,'ArgumentCount':2,
                   'Report':caller_probe.REPORT,'ObservationSchema':caller_probe.SCHEMA}
        for name,path in [('Helper',output/'prepared'/caller_probe.HELPER),('Wiring',HERE/'prepare_prepatch_image_caller.py'),
                           ('RangeGuard',output/'prepared'/caller_probe.GUARD),('RangeGuardSource',HERE/caller_probe.GUARD),
                           ('BoundaryFixture',HERE/caller_probe.FIXTURE),('FixtureResponse',output/'caller-fixture.rsp'),
                           ('BaseHelper',HERE/link_probe.HELPER),('BaseWiring',HERE/'prepare_prepatch_link_v3.py'),
                           ('BaseBuildPlan',args.reuse_plan),('BaseBuildReceipt',args.reuse_compile_receipt),
                           ('BaseV3BuildPlan',caller_base_plan),('BaseV3Main',caller_base_main),('PreparedMain',output/'prepared/main.cpp')]:
            profile[name] = {k:bindings[key(path)][k] for k in ('Path','Bytes','SHA256')}
    elif prepatch_link_v3:
        profile = {'Name':link_probe.NAME,'Option':link_probe.OPTION,'ArgumentCount':2,
                   'Report':link_probe.REPORT,'ObservationSchema':link_probe.SCHEMA}
        for name,path in [('Helper',output/'prepared'/link_probe.HELPER),('Wiring',HERE/'prepare_prepatch_link_v3.py'),
                           ('BaseHelper',HERE/reference_probe.HELPER),('BaseWiring',HERE/'prepare_prepatch_reference.py'),
                           ('BaseBuildPlan',args.reuse_plan),('BaseBuildReceipt',args.reuse_compile_receipt),
                           ('BaseV2BuildPlan',link_base_plan),('BaseV2Main',link_base_main),('PreparedMain',output/'prepared/main.cpp')]:
            profile[name] = {k:bindings[key(path)][k] for k in ('Path','Bytes','SHA256')}
    elif prepatch_reference_v2:
        profile = {'Name':reference_probe.NAME,'Option':reference_probe.OPTION,'ArgumentCount':2,
                   'Report':reference_probe.REPORT,'ObservationSchema':reference_probe.SCHEMA}
        for name, path in [('Helper',output/'prepared'/reference_probe.HELPER),
                           ('Wiring',HERE/'prepare_prepatch_reference.py'),
                           ('BaseHelper',HERE/'native_prepatch_probe.inc'),('BaseWiring',HERE/'prepare_prepatch.py'),
                           ('BaseBuildPlan',args.reuse_plan),('BaseBuildReceipt',args.reuse_compile_receipt),
                           ('PreparedMain',output/'prepared/main.cpp')]:
            profile[name] = {k:bindings[key(path)][k] for k in ('Path','Bytes','SHA256')}
    elif prepatch_helper:
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
        if image_observation:
            profile.update(Name=image_provenance.NAME, Option=image_provenance.OPTION,
                           ArgumentCount=5, ObservationSchema=image_provenance.SCHEMA,
                           SourceOnlyPending=fixture_proof is None)
            if fixture_proof is not None:
                profile['FixtureProof'] = fixture_proof
            for name, path in [('ProvenanceBaseWiring',HERE/'prepare_material_parts.py'),
                               ('ProvenanceWiring',HERE/'prepare_image_provenance.py'),
                               ('ProvenanceSource',HERE/image_provenance.HELPER),
                               ('ProvenanceEntry',HERE/image_provenance.ENTRY),
                               ('ProvenanceContract',HERE/image_provenance.CONTRACT),
                               ('ProvenanceFixture',HERE/image_provenance.FIXTURE)]:
                profile[name] = {k:bindings[key(path)][k] for k in ('Path','Bytes','SHA256')}
            if fixture_proof is not None:
                for role, expected_pin in IMAGE_FIXTURE_API_PINS.items():
                    require((profile[role]['Bytes'], profile[role]['SHA256']) == expected_pin,
                            'H proof cannot qualify another provenance API source')
            if image_metadata_enabled:
                profile.update(MetadataSchema=image_metadata.SCHEMA, MetadataOption=image_metadata.OPTION,
                               MetadataFixtureNativeRoot=str(source), MetadataMapperChecks=54, MetadataGuardChecks=13)
                for name, path in [('MetadataWiring', HERE/'prepare_image_metadata.py'),
                                   ('MetadataContract', HERE/image_metadata.CONTRACT),
                                   ('MetadataPartsSource', HERE/'selected_material_parts_observation.hpp'),
                                   ('MetadataBuilder', HERE/'selected_image_header_metadata.hpp'),
                                   ('MetadataBuilderFixture', HERE/'selected_image_header_metadata_fixture.cpp'),
                                   ('MetadataSource', HERE/'selected_image_metadata.hpp'),
                                   ('MetadataReadGuard', HERE/'selected_image_metadata_read_guard.hpp'),
                                   ('MetadataGuardFixture', HERE/'selected_image_metadata_guard_fixture.cpp'),
                                   ('MetadataGuardedObserver', output/'prepared'/image_metadata.GUARDED_OBSERVER),
                                   ('MetadataFixtureResponse', output/'metadata-fixture.rsp'),
                                   ('MetadataEntry', HERE/'native_image_metadata.inc')]:
                    profile[name] = {k:bindings[key(path)][k] for k in ('Path','Bytes','SHA256')}
                if registration_enabled:
                    profile.update(Name=registration_metadata.NAME, Option=registration_metadata.OPTION,
                        ObservationSchema=registration_metadata.SCHEMA, RegistrationSchema=registration_metadata.SCHEMA,
                        RegistrationFixtureChecks=39, RegistrationCPPQualified=False)
                    for name, path in [('RegistrationWiring', HERE/'prepare_image_registration_metadata.py'),
                                       ('RegistrationContract', HERE/registration_metadata.CONTRACT),
                                       ('RegistrationCapture', HERE/registration_metadata.CAPTURE),
                                       ('RegistrationEntry', HERE/registration_metadata.ENTRY),
                                       ('RegistrationFixture', HERE/registration_metadata.FIXTURE),
                                       ('RegistrationObserver', output/'prepared/selected_image_registration_observer.hpp'),
                                       ('RegistrationResponse', output/'registration-fixture.rsp')]:
                        profile[name] = {k:bindings[key(path)][k] for k in ('Path','Bytes','SHA256')}
                    if incoming_enabled:
                        profile.update(Name=incoming_metadata.NAME,Option=incoming_metadata.OPTION,
                            ObservationSchema=incoming_metadata.SCHEMA,IncomingSchema=incoming_metadata.SCHEMA,
                            IncomingFixtureChecks=48,IncomingCPPQualified=False)
                        for name,path in [('IncomingWiring',HERE/'prepare_incoming_image_metadata.py'),
                                          ('IncomingContract',HERE/incoming_metadata.CONTRACT),('IncomingMembers',HERE/incoming_metadata.MEMBERS),
                                          ('IncomingModule',HERE/incoming_metadata.MODULE),('IncomingEntry',HERE/incoming_metadata.ENTRY),
                                          ('IncomingFixture',HERE/incoming_metadata.FIXTURE),
                                          ('IncomingCapture',output/'prepared/selected_image_incoming_capture.hpp'),
                                          ('IncomingObserver',output/'prepared/selected_image_incoming_observer.hpp'),
                                          ('IncomingBaselineFixture',output/'prepared/incoming_registration_baseline_fixture.cpp')]:
                            profile[name]={k:bindings[key(path)][k] for k in ('Path','Bytes','SHA256')}
                    if bindings_enabled:
                        bindings_build.extend_profile(profile,output/'prepared',
                            lambda path:{k:bindings[key(path)][k] for k in ('Path','Bytes','SHA256')})
        if zombies_observation:
            profile['Name'] = zombies_observer.SOURCE_PROFILE
            profile['ObservationSchema'] = zombies_observer.SCHEMA
            for name, path in [('ObserverSource',HERE/'native_catalog_zombies_observation.inc'),
                               ('ObserverAdapter',HERE/'prepare_catalog_zombies_observation.py')]:
                profile[name] = {k:bindings[key(path)][k] for k in ('Path','Bytes','SHA256')}
        if add_observation:
            profile['Name'] = add_observer.SOURCE_PROFILE
            profile['ObservationSchema'] = add_observer.SCHEMA
            for name, path in [('ObserverSource',HERE/'native_catalog_add_observation.inc'),
                               ('ObserverAdapter',HERE/'prepare_catalog_add_observation.py')]:
                profile[name] = {k:bindings[key(path)][k] for k in ('Path','Bytes','SHA256')}
        if parts_observation:
            profile.update(Name=material_parts.NAME, Option=material_parts.OPTION,
                           ArgumentCount=5, ObservationSchema=material_parts.SCHEMA)
            for name, path in [('PartsWiring',HERE/'prepare_material_parts.py'),
                               ('PartsSource',HERE/material_parts.HELPER),
                               ('PartsEntry',HERE/material_parts.ENTRY),
                               ('PartsContract',HERE/material_parts.CONTRACT),
                               ('PartsFixture',HERE/'selected_material_parts_observation_fixture.cpp')]:
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
    if os_context is not None: plan['OSResourceContext'] = os_context
    raw = (json.dumps(plan,indent=2)+'\n').encode()
    require_preparation_bounds(raw, payloads, parts_profile=parts_observation, provenance_profile=image_observation,
                               metadata_profile=image_metadata_enabled, registration_profile=registration_enabled,
                               incoming_profile=incoming_enabled, bindings_profile=bindings_enabled)
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
    parser.add_argument('--prepatch-reference-v2',action='store_true')
    parser.add_argument('--prepatch-link-v3',action='store_true')
    parser.add_argument('--prepatch-link-v3-base-plan',type=Path)
    parser.add_argument('--prepatch-image-caller-v1',action='store_true')
    parser.add_argument('--prepatch-image-caller-v1-base-plan',type=Path)
    parser.add_argument('--catalog-trace',action='store_true')
    parser.add_argument('--catalog-exit',action='store_true')
    parser.add_argument('--catalog-callers',action='store_true')
    parser.add_argument('--catalog-message',action='store_true')
    parser.add_argument('--catalog-message-publication',action='store_true')
    parser.add_argument('--resident-surface-count-diagnostic',action='store_true')
    parser.add_argument('--resident-multisurface-v2',action='store_true')
    parser.add_argument('--selected-streamed-static-v1',action='store_true')
    parser.add_argument('--selected-streamed-render-only-v2',action='store_true')
    parser.add_argument('--zombies-catalogue-observation',action='store_true')
    parser.add_argument('--zombies-add-observation-c2',action='store_true')
    parser.add_argument('--material-parts-v1',action='store_true')
    parser.add_argument('--image-provenance-v1',action='store_true')
    parser.add_argument('--image-metadata-v1',action='store_true')
    parser.add_argument('--image-registration-metadata-v1',action='store_true')
    parser.add_argument('--image-incoming-header-v1',action='store_true')
    parser.add_argument('--image-registration-bindings-v1',action='store_true')
    parser.add_argument('--image-provenance-fixture-proof-root',type=Path)
    parser.add_argument('--os-context-tzres-20261014',action='store_true')
    parser.add_argument('--os-context-proof',type=Path)
    parser.add_argument('--ordinary-plan',type=Path)
    parser.add_argument('--ordinary-receipt',type=Path)
    print(json.dumps(prepare(parser.parse_args()),indent=2))

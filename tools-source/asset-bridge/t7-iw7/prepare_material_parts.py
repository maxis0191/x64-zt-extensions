"""Finite opt-in image-parts CLI transition; default E5/C2 factories stay exact."""
import hashlib
import json
from pathlib import Path
import prepare_cli

HERE = Path(__file__).resolve().parent
NAME = 't7-material-parts-v1'
OPTION = '-t7-iw7-material-parts-v1'
SCHEMA = 'iw7.t7-selected-material-observation/3'
BUILD_SCHEMA = 'iw7.t7-material-parts-build/1'
CONTRACT = 'material-parts-source-contract.json'
HELPER = 'selected_material_parts_observation.hpp'
ENTRY = 'native_material_parts.inc'
BASE_MAIN = (43254, '5aef1fad310071f5e680a9f5b4dbd6a303af6ea8605fccb5dc5705cb386b761d')
BASE_CLI = (112377, 'c63d9552464da674d3b03c35f7edc16385fb9370b113a3925fd7bc4835fb005a')
BASE_OBSERVER = (18583, 'a8848a92b8d7918fbe91ec4b68df123b1eaab89edde9d8a7c24d5a0cfb576ffc')
FLAG = 'utils::flags::has_flag("t7-iw7-material-parts-v1")'
ANCHOR_FLAG = 'utils::flags::has_flag("t7-iw7-catalog")'


def pin(raw):
    return len(raw), hashlib.sha256(raw).hexdigest()


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def require_pin(raw, expected, label):
    require(type(raw) is bytes and pin(raw) == expected, 'Exact material-parts ' + label + ' required')


def selected(args):
    value = getattr(args, 'material_parts_v1', False)
    require(type(value) is bool, 'Explicit material-parts boolean required')
    if value:
        require(getattr(args, 'catalog_message_publication', False) is True and
                getattr(args, 'selected_streamed_render_only_v2', False) is True and
                all(getattr(args, key, False) is False for key in
                    ('prepatch_reference_v2', 'selected_streamed_static_v1', 'resident_multisurface_v2',
                     'resident_surface_count_diagnostic', 'zombies_catalogue_observation',
                     'zombies_add_observation_c2')) and
                not getattr(args, 'prepatch_helper', None) and
                bool(getattr(args, 'reuse_plan', None)) and bool(getattr(args, 'reuse_compile_receipt', None)),
                'Material-parts requires exclusive E5 publication and retained compile proofs')
    return value


def wire_main(source):
    require_pin(source.encode(), BASE_MAIN, 'base main')
    require(source.count(ANCHOR_FLAG) == 2, 'Exact main mode-guard inventory required')
    return source.replace(ANCHOR_FLAG, '(' + ANCHOR_FLAG + ' || ' + FLAG + ')')


def wire_cli(source, observer, helper, entry):
    require_pin(source.encode(), BASE_CLI, 'base CLI')
    require_pin(observer, BASE_OBSERVER, 'G2 observer')
    require(type(helper) is bytes and 0 < len(helper) <= 32*1024 and
            type(entry) is bytes and 0 < len(entry) <= 8*1024, 'Bounded parts helper/entry required')
    once = prepare_cli.helper.once
    observer_inline = observer.decode().replace('#pragma once\n', '').replace('#include "resident_image_copy.hpp"\n', '')
    require(source.count(observer_inline) == 1, 'One exact G2 observer must precede the opt-in module')
    helper_inline = helper.decode()
    helper_inline = once(helper_inline, '#pragma once\n', '')
    helper_inline = once(helper_inline, '#include "selected_material_observation.hpp"\n', '')
    source = once(source, observer_inline, observer_inline + '\n\n' + helper_inline)
    require(source.count(ANCHOR_FLAG) == 1, 'Exact CLI mode-guard inventory required')
    source = source.replace(ANCHOR_FLAG, '(' + ANCHOR_FLAG + ' || ' + FLAG + ')')
    source = once(source, '\tvoid handle_params()\n',
                  '\n'.join('\t' + line if line else '' for line in entry.decode().splitlines()) +
                  '\n\n\tvoid handle_params()\n')
    catalog = '\t\t\t\tconst bool catalog = args.size() == 3 && args[1] == "-t7-iw7-catalog";'
    exclusive = '\t\t\t\tconst bool parts = args.size() == 5 && args[1] == "' + OPTION + '";\n'
    exclusive += '\t\t\t\tif ((' + FLAG + ' && !parts) || (parts && (' + '\n'
    exclusive += '\t\t\t\t\tutils::flags::has_flag("t7-iw7-model") || utils::flags::has_flag("t7-iw7-model-v2") ||\n'
    exclusive += '\t\t\t\t\tutils::flags::has_flag("t7-iw7-model-streamed-v1") || utils::flags::has_flag("t7-iw7-model-streamed-v2") ||\n'
    exclusive += '\t\t\t\t\tutils::flags::has_flag("t7-iw7-catalog") || utils::flags::has_flag("t7-prepatch-probe") ||\n'
    exclusive += '\t\t\t\t\tutils::flags::has_flag("t7-prepatch-reference-v2"))))\n'
    exclusive += '\t\t\t\t\tthrow std::runtime_error("Exclusive exact material-parts arguments required");\n'
    source = once(source, catalog, exclusive + catalog)
    source = once(source, '\t\t\t\tif (catalog) catalog_resident_models_iw7(args[2]);',
                  '\t\t\t\tif (parts) observe_selected_material_parts_iw7(args[2], args[3], args[4]);\n'
                  '\t\t\t\telse if (catalog) catalog_resident_models_iw7(args[2]);')
    error = '\t\t\t\tif (utils::flags::has_flag("t7-iw7-model-streamed-v1") || utils::flags::has_flag("t7-iw7-model-streamed-v2"))'
    source = once(source, error,
                  '\t\t\t\tif (' + FLAG + ')\n'
                  '\t\t\t\t\tZONETOOL_ERROR("T7 material parts metadata refused: %s", error.what());\n'
                  '\t\t\t\telse ' + error.lstrip())
    require(len(source.encode()) <= 128*1024, 'Parts CLI must preserve its 128-KiB source cap')
    return source


def load_contract(read):
    raw = read(HERE / CONTRACT, 16*1024)
    contract = json.loads(raw)
    require(type(contract) is dict and contract.get('schema') == 'iw7.t7-material-parts-source/1' and
            contract.get('source_profile') == NAME and
            set(contract) == {'schema', 'source_profile', 'files', 'main', 'cli'}, 'Exact parts source contract required')
    require(set(contract['files']) == {HELPER, ENTRY, 'selected_material_parts_observation_fixture.cpp'},
            'Exact parts source inventory required')
    sources = {}
    for name, item in contract['files'].items():
        require(type(item) is dict and set(item) == {'lf_bytes', 'lf_sha256'} and
                type(item['lf_bytes']) is int and 0 < item['lf_bytes'] <= 64*1024 and
                type(item['lf_sha256']) is str and len(item['lf_sha256']) == 64, 'Typed parts source pin required')
        sources[name] = read(HERE / name, 64*1024, item['lf_sha256']).replace(b'\r\n', b'\n')
        require_pin(sources[name], (item['lf_bytes'], item['lf_sha256']), name)
    for role in ('main', 'cli'):
        require(type(contract[role]) is dict and set(contract[role]) == {'bytes', 'sha256'} and
                type(contract[role]['bytes']) is int and 0 < contract[role]['bytes'] <= 128*1024 and
                type(contract[role]['sha256']) is str and len(contract[role]['sha256']) == 64,
                'Typed parts output pin required')
    return contract, sources


def overlay(main, cli, read):
    contract, sources = load_contract(read)
    observer = read(HERE / 'selected_material_observation.hpp', 32*1024, BASE_OBSERVER[1]).replace(b'\r\n', b'\n')
    main = wire_main(main)
    cli = wire_cli(cli, observer, sources[HELPER], sources[ENTRY])
    for role, text in (('main', main), ('cli', cli)):
        require_pin(text.encode(), (contract[role]['bytes'], contract[role]['sha256']), 'wired ' + role)
    return main, cli, {'Schema': BUILD_SCHEMA, 'SourceProfile': NAME,
        'BaseMainBytes': BASE_MAIN[0], 'BaseMainSHA256': BASE_MAIN[1],
        'BaseCLIBytes': BASE_CLI[0], 'BaseCLISHA256': BASE_CLI[1],
        'MainBytes': contract['main']['bytes'], 'MainSHA256': contract['main']['sha256'],
        'CLIBytes': contract['cli']['bytes'], 'CLISHA256': contract['cli']['sha256']}

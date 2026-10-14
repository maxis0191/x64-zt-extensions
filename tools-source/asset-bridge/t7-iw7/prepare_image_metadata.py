"""Finite metadata extension over the unchanged F2 source pair; no prepare/run."""
import json
from pathlib import Path
import prepare_cli
import prepare_image_provenance as provenance
import prepare_material_parts as parts

HERE = Path(__file__).resolve().parent
NAME = 't7-image-metadata-v1'
OPTION = '-t7-iw7-image-metadata-v1'
SCHEMA = 'iw7.t7-selected-image-metadata/1'
FLAG = 'utils::flags::has_flag("t7-iw7-image-metadata-v1")'
CONTRACT = 'image-metadata-source-contract.json'
SOURCE_FILES = ('selected_material_parts_observation.hpp',
                'selected_image_header_metadata.hpp',
                'selected_image_header_metadata_fixture.cpp',
                'selected_image_metadata.hpp', 'native_image_metadata.inc',
                'selected_image_metadata_read_guard.hpp',
                'selected_image_metadata_guard_fixture.cpp')
GUARDED_OBSERVER = 'selected_material_metadata_guarded.hpp'


def selected(args):
    value = getattr(args, 'image_metadata_v1', False)
    parts.require(type(value) is bool, 'Explicit metadata extension boolean required')
    parts.require(not value or getattr(args, 'image_provenance_v1', False) is True,
                  'Metadata extension requires the exclusive provenance producer')
    return value


def guarded_observer_source(observer):
    parts.require_pin(observer, parts.BASE_OBSERVER, 'immutable G2 reader')
    once = prepare_cli.helper.once
    text = once(observer.decode(), '#include "resident_image_copy.hpp"\n',
                '#include "resident_image_copy.hpp"\n#include "selected_image_metadata_read_guard.hpp"\n')
    anchor = 'inline nlohmann::ordered_json image_metadata(const GfxImage& source)\n    {\n'
    text = once(text, anchor, anchor+'        selected_image_metadata_read_guard::validate_if_active(source);\n')
    copy = '            std::memcpy(&value, source, sizeof(T));\n'
    return once(text, copy, copy+
                '            if constexpr (std::is_same_v<T, GfxImage>)\n'
                '                selected_image_metadata_read_guard::validate_if_active(value);\n')


def wire(main, cli, source_files, base_contract, observer):
    for role, raw in (('main', main), ('cli', cli)):
        pin = base_contract[role]
        parts.require_pin(raw.encode(), (pin['bytes'], pin['sha256']), 'metadata F2 base '+role)
    parts.require(set(source_files) == set(SOURCE_FILES), 'Exact metadata source inventory required')
    once = prepare_cli.helper.once
    policy = once(source_files[SOURCE_FILES[5]].decode(), '#pragma once\n', '')
    policy = once(policy, '#include "resident_image_copy.hpp"\n', '')
    base = observer.decode().replace('#pragma once\n', '').replace('#include "resident_image_copy.hpp"\n', '')
    checked = guarded_observer_source(observer).replace('#pragma once\n', '').replace(
        '#include "resident_image_copy.hpp"\n', '').replace('#include "selected_image_metadata_read_guard.hpp"\n', '')
    cli = once(cli, base, policy+'\n#define IW7_SELECTED_IMAGE_METADATA_GUARD_INSTALLED 1\n'+checked)
    guard = source_files[SOURCE_FILES[0]].decode()
    guard = once(guard, '#pragma once\n', '')
    guard = once(guard, '#include "selected_material_observation.hpp"\n', '')
    builder = once(source_files[SOURCE_FILES[1]].decode(), '#pragma once\n', '')
    wrapper = once(source_files[SOURCE_FILES[3]].decode(), '#pragma once\n', '')
    for name in ('selected_material_parts_observation.hpp', 'selected_image_header_metadata.hpp',
                 'selected_image_metadata_read_guard.hpp'):
        wrapper = once(wrapper, '#include "'+name+'"\n', '')
    anchor = '\nnamespace zonetool::t7 {\nusing image_provenance_observer ='
    cli = once(cli, anchor, '\n'+guard+'\n'+builder+'\n'+wrapper+anchor)
    entry = source_files[SOURCE_FILES[4]].decode()
    old_entry_anchor = '\t// Exact opt-in route. Existing MODEL lookup and original add behavior are retained.\n'
    cli = once(cli, old_entry_anchor,
               '\n'.join('\t'+line if line else '' for line in entry.splitlines())+
               '\n\n'+old_entry_anchor)
    parts.require(main.count(provenance.FLAG) == 2, 'Exact F2 main guard inventory required')
    main = main.replace(provenance.FLAG, '('+provenance.FLAG+' || '+FLAG+')')
    old_guard = '('+parts.ANCHOR_FLAG+' || '+provenance.FLAG+')'
    cli = once(cli, old_guard, '('+old_guard+' || '+FLAG+')')
    selector = '\t\t\t\tconst bool image_metadata = args.size() == 5 && args[1] == "'+OPTION+'";\n'
    selector += '\t\t\t\tif (('+FLAG+' && !image_metadata) || (image_metadata && (\n'
    exclusions = ('t7-iw7-model', 't7-iw7-model-v2', 't7-iw7-model-streamed-v1',
                  't7-iw7-model-streamed-v2', 't7-iw7-catalog', 't7-prepatch-probe',
                  't7-prepatch-reference-v2', 't7-prepatch-link-v3',
                  't7-iw7-material-parts-v1', 't7-iw7-image-provenance-v1')
    for i, option in enumerate(exclusions):
        selector += '\t\t\t\t\tutils::flags::has_flag("'+option+'")'+(' ||\n' if i+1 < len(exclusions) else ')))\n')
    selector += '\t\t\t\t\tthrow std::runtime_error("Exclusive exact image-metadata arguments required");\n'
    cli = once(cli, '\t\t\t\tconst bool provenance =', selector+'\t\t\t\tconst bool provenance =')
    # The immutable F2 source pair includes one surplus guard terminator.
    # Replace its complete terminal line in this extension, including the
    # original terminator; a partial match left another extra ')' behind.
    cli = once(cli, 'utils::flags::has_flag("t7-iw7-material-parts-v1")))))\n',
               'utils::flags::has_flag("t7-iw7-material-parts-v1") || '+FLAG+')))\n')
    cli = once(cli, '\t\t\t\tif (provenance) observe_selected_image_provenance_iw7(args[2], args[3], args[4]);',
               '\t\t\t\tif (image_metadata) observe_selected_image_metadata_iw7(args[2], args[3], args[4]);\n'
               '\t\t\t\telse if (provenance) observe_selected_image_provenance_iw7(args[2], args[3], args[4]);')
    cli = once(cli, '\t\t\t\tif ('+provenance.FLAG+')\n',
               '\t\t\t\tif ('+FLAG+')\n'
               '\t\t\t\t\tZONETOOL_ERROR("T7 image metadata refused: %s", error.what());\n'
               '\t\t\t\telse if ('+provenance.FLAG+')\n')
    parts.require(len(cli.encode()) <= 160*1024, 'Finite metadata CLI source cap exceeded')
    return main, cli


def overlay(main, cli, read):
    base = json.loads(read(HERE/provenance.CONTRACT, 16*1024))
    contract = json.loads(read(HERE/CONTRACT, 16*1024))
    parts.require(type(contract) is dict and set(contract) == {'schema', 'source_profile', 'files', 'main', 'cli', 'guarded_observer'} and
                  contract['schema'] == 'iw7.t7-image-metadata-source/1' and
                  contract['source_profile'] == NAME and set(contract['files']) == set(SOURCE_FILES),
                  'Exact metadata extension source contract required')
    files = {}
    for name, pin in contract['files'].items():
        parts.require(type(pin) is dict and set(pin) == {'lf_bytes', 'lf_sha256'} and
                      type(pin['lf_bytes']) is int and 0 < pin['lf_bytes'] <= 16*1024 and
                      type(pin['lf_sha256']) is str and len(pin['lf_sha256']) == 64,
                      'Typed finite metadata source pin required')
        raw = read(HERE/name, 16*1024, pin['lf_sha256']).replace(b'\r\n', b'\n')
        parts.require_pin(raw, (pin['lf_bytes'], pin['lf_sha256']), name)
        files[name] = raw
    observer = read(HERE/'selected_material_observation.hpp', 32*1024, parts.BASE_OBSERVER[1]).replace(b'\r\n', b'\n')
    guarded_pin = contract['guarded_observer']
    parts.require(type(guarded_pin) is dict and set(guarded_pin) == {'bytes', 'sha256'} and
                  type(guarded_pin['bytes']) is int and 0 < guarded_pin['bytes'] <= 32*1024 and
                  type(guarded_pin['sha256']) is str, 'Finite guarded observer output pin required')
    parts.require_pin(guarded_observer_source(observer).encode(),
                      (guarded_pin['bytes'], guarded_pin['sha256']), 'same guarded observer')
    new_main, new_cli = wire(main, cli, files, base, observer)
    for role, value in (('main', new_main), ('cli', new_cli)):
        pin = contract[role]
        parts.require(type(pin) is dict and set(pin) == {'bytes', 'sha256'} and
                      type(pin['bytes']) is int and 0 < pin['bytes'] <= 160*1024 and
                      type(pin['sha256']) is str and len(pin['sha256']) == 64,
                      'Typed finite metadata output pin required')
        parts.require_pin(value.encode(), (pin['bytes'], pin['sha256']), role)
    return new_main, new_cli, {'Schema': 'iw7.t7-image-metadata-build/1', 'SourceProfile': NAME,
        'BaseMainBytes': len(main.encode()), 'BaseMainSHA256': provenance.pin(main.encode())[1],
        'BaseCLIBytes': len(cli.encode()), 'BaseCLISHA256': provenance.pin(cli.encode())[1],
        'MainBytes': len(new_main.encode()), 'MainSHA256': provenance.pin(new_main.encode())[1],
        'CLIBytes': len(new_cli.encode()), 'CLISHA256': provenance.pin(new_cli.encode())[1]}

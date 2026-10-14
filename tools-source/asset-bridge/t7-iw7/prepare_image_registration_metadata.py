"""One additive registration-copy seam over the exact immutable metadata source pair."""
import hashlib
import json
from pathlib import Path
import prepare_cli
import prepare_image_metadata as metadata
import prepare_image_provenance as provenance
import prepare_material_parts as parts

HERE = Path(__file__).resolve().parent
NAME = 't7-registration-image-header-metadata-v1'
OPTION = '-t7-iw7-image-registration-metadata-v1'
FLAG = 'utils::flags::has_flag("t7-iw7-image-registration-metadata-v1")'
SCHEMA = 'iw7.t7-registration-image-header-metadata/1'
CONTRACT = 'registration-image-metadata-source-contract.json'
CAPTURE = 'registration_image_header_capture.hpp'
ENTRY = 'native_image_registration_metadata.inc'
FIXTURE = 'registration_image_header_fixture.cpp'
BASE_OBSERVER = (15069, 'd8b3f07f787f03dbda7c0305e2aad685c131130fbe43a839145e869858925c16')
BASE_PAIR = {'main': (43482, 'b786f2db40e4c70346846bccb336c86c957efbd76f1c9365994138119a4e4363'),
             'cli': (154456, '17c07359a55e23324239f9663a8d4ead3cb9d3343a8b7ff0d4baf01ca4dfae6b')}


def selected(args):
    value = getattr(args, 'image_registration_metadata_v1', False)
    parts.require(type(value) is bool, 'Explicit registration metadata boolean required')
    parts.require(not value or (getattr(args, 'image_provenance_v1', False) is True and
                              getattr(args, 'image_metadata_v1', False) is True),
                  'Registration metadata requires the exact measured metadata source pair')
    return value


def observer_source(original):
    parts.require_pin(original, BASE_OBSERVER, 'immutable F2 observer')
    once = prepare_cli.helper.once
    text = original.decode()
    text = once(text, '#include <mutex>\n', '#include <mutex>\n#include "'+CAPTURE+'"\n')
    text = once(text, '        snapshot registration_, lookup_;\n',
        '        snapshot registration_, lookup_;\n'
        '        registration_image_header_capture::cache registration_copy_;\n'
        '        bool registration_copy_enabled_ = false;\n'
        '        static registration_image_header_capture::association copied_association(const snapshot& value)\n'
        '        {\n'
        '            return {value.ordinal, value.returned, value.material, value.table, value.image,\n'
        '                value.bound, value.memory.complete && value.memory.readable};\n'
        '        }\n')
    text = once(text, '                    registration_ = capture(pointer, reinterpret_cast<std::uintptr_t>(incoming.data));\n',
        '                    registration_ = capture(pointer, reinterpret_cast<std::uintptr_t>(incoming.data));\n'
        '                    if (registration_copy_enabled_)\n'
        '                        registration_copy_.record(copied_association(registration_), pointer,\n'
        '                            readable_, query_, &registration_image_header_capture::copy_leaf);\n')
    text = once(text, '        void begin()\n',
        '        void begin_registration_metadata()\n'
        '        {\n'
        '            const std::lock_guard lock(mutex_);\n'
        '            resident_image::require(!begun_, "Registration context is single-use");\n'
        '            registration_copy_.reset();\n'
        '            registration_copy_enabled_ = true;\n'
        '            begun_ = true; active_.store(true);\n'
        '        }\n'
        '        nlohmann::ordered_json finish_registration_metadata(const XModel* pointer, bool nondefault)\n'
        '        {\n'
        '            const auto provenance = finish(pointer);\n'
        '            const std::lock_guard lock(mutex_);\n'
        '            resident_image::require(registration_copy_enabled_, "Registration mode was not enabled");\n'
        '            return registration_copy_.finish(provenance, copied_association(registration_),\n'
        '                copied_association(lookup_), nondefault);\n'
        '        }\n'
        '        void begin()\n')
    return text


def wire(main, cli, original_observer, capture_source, entry_source):
    for role, text in (('main', main), ('cli', cli)):
        parts.require_pin(text.encode(), BASE_PAIR[role], 'registration base '+role)
    once = prepare_cli.helper.once
    old = original_observer.decode().replace('#pragma once\n', '').replace('#include "selected_material_observation.hpp"\n', '')
    derived = observer_source(original_observer).replace('#pragma once\n', '').replace(
        '#include "selected_material_observation.hpp"\n', '').replace('#include "'+CAPTURE+'"\n', '')
    capture = capture_source.decode().replace('#pragma once\n', '').replace(
        '#include "selected_material_observation.hpp"\n', '').replace('#include "selected_image_header_metadata.hpp"\n', '')
    # Mapper124 is already embedded by the exact base metadata overlay. Move
    # this definition after that mapper but before the derived F2 observer.
    mapper = (HERE/'selected_image_header_metadata.hpp').read_text().replace('#pragma once\n', '')
    cli = once(cli, '\n'+mapper+'\n', '\n')
    cli = once(cli, old, mapper+'\n'+capture+'\n'+derived)
    parts.require(main.count(metadata.FLAG) == 2, 'Exact prior main selector inventory required')
    main = main.replace(metadata.FLAG, '('+metadata.FLAG+' || '+FLAG+')')
    old_guard = '('+parts.ANCHOR_FLAG+' || '+provenance.FLAG+')'
    cli = once(cli, '('+old_guard+' || '+metadata.FLAG+')', '(('+old_guard+' || '+metadata.FLAG+') || '+FLAG+')')
    entry_anchor = '\t// Distinct opt-in body-metadata route; never runs from the F2 provenance option.\n'
    cli = once(cli, entry_anchor, '\n'.join('\t'+line if line else '' for line in entry_source.decode().splitlines())+'\n\n'+entry_anchor)
    selector = '\t\t\t\tconst bool registration_metadata = args.size() == 5 && args[1] == "'+OPTION+'";\n'
    exclusions = ('t7-iw7-model', 't7-iw7-model-v2', 't7-iw7-model-streamed-v1',
        't7-iw7-model-streamed-v2', 't7-iw7-catalog', 't7-prepatch-probe',
        't7-prepatch-reference-v2', 't7-prepatch-link-v3', 't7-iw7-material-parts-v1',
        't7-iw7-image-provenance-v1', 't7-iw7-image-metadata-v1')
    selector += '\t\t\t\tif (('+FLAG+' && !registration_metadata) || (registration_metadata && (\n'
    selector += ' ||\n'.join('\t\t\t\t\tutils::flags::has_flag("'+option+'")' for option in exclusions)+')))\n'
    selector += '\t\t\t\t\tthrow std::runtime_error("Exclusive exact registration-metadata arguments required");\n'
    cli = once(cli, provenance.FLAG+')))\n', provenance.FLAG+' || '+FLAG+')))\n')
    cli = once(cli, metadata.FLAG+')))\n', metadata.FLAG+' || '+FLAG+')))\n')
    cli = once(cli, '\t\t\t\tconst bool image_metadata =', selector+'\t\t\t\tconst bool image_metadata =')
    dispatch = '\t\t\t\tif (image_metadata) observe_selected_image_metadata_iw7(args[2], args[3], args[4]);'
    cli = once(cli, dispatch, '\t\t\t\tif (registration_metadata) observe_registration_image_metadata_iw7(args[2], args[3], args[4]);\n'
        '\t\t\t\telse if (image_metadata) observe_selected_image_metadata_iw7(args[2], args[3], args[4]);')
    error = '\t\t\t\tif ('+metadata.FLAG+')\n'
    cli = once(cli, error, '\t\t\t\tif ('+FLAG+')\n'
        '\t\t\t\t\tZONETOOL_ERROR("T7 registration metadata refused: %s", error.what());\n'
        '\t\t\t\telse if ('+metadata.FLAG+')\n')
    parts.require(len(cli.encode()) <= 192*1024, 'Finite registration CLI source cap exceeded')
    return main, cli


def overlay(main, cli, read):
    contract = json.loads(read(HERE/CONTRACT, 32*1024))
    parts.require(type(contract) is dict and contract.get('schema') == 'iw7.t7-registration-image-metadata-source/1' and
                  contract.get('source_profile') == NAME and contract.get('report_schema') == SCHEMA and
                  contract.get('native_option') == OPTION and contract.get('source_only_pending') is True,
                  'Exact source-pending registration contract required')
    files = {}
    for name in (CAPTURE, ENTRY, FIXTURE):
        item = contract['files'][name]
        raw = read(HERE/name, 32*1024, item['sha256']).replace(b'\r\n', b'\n')
        parts.require_pin(raw, (item['bytes'], item['sha256']), name)
        files[name] = raw
    original = read(HERE/provenance.HELPER, 32*1024, BASE_OBSERVER[1]).replace(b'\r\n', b'\n')
    derived = observer_source(original)
    parts.require_pin(derived.encode(), (contract['derived_observer']['bytes'], contract['derived_observer']['sha256']),
                      'new registration observer source')
    new_main, new_cli = wire(main, cli, original, files[CAPTURE], files[ENTRY])
    for role, value in (('main', new_main), ('cli', new_cli)):
        parts.require_pin(value.encode(), (contract[role]['bytes'], contract[role]['sha256']), 'registration '+role)
    return new_main, new_cli, {'Schema': 'iw7.t7-registration-image-metadata-build/1', 'SourceProfile': NAME,
        'SourceOnlyPending': True, 'CPPQualified': False, 'Ready': False,
        'BaseMainBytes': len(main.encode()), 'BaseMainSHA256': hashlib.sha256(main.encode()).hexdigest(),
        'BaseCLIBytes': len(cli.encode()), 'BaseCLISHA256': hashlib.sha256(cli.encode()).hexdigest(),
        'MainBytes': len(new_main.encode()), 'MainSHA256': hashlib.sha256(new_main.encode()).hexdigest(),
        'CLIBytes': len(new_cli.encode()), 'CLISHA256': hashlib.sha256(new_cli.encode()).hexdigest()}

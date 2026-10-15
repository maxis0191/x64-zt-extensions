"""Additive SOURCE renderer; preparation/CPP/native recipes belong to their owners."""
import hashlib
import json
from pathlib import Path
import prepare_cli
import prepare_image_registration_metadata as registration
import prepare_incoming_image_metadata as incoming
import prepare_material_parts as parts

HERE = Path(__file__).resolve().parent
NAME = 't7-registration-material-bindings-v1'
OPTION = '-t7-iw7-registration-material-bindings-v1'
FLAG = 'utils::flags::has_flag("t7-iw7-registration-material-bindings-v1")'
SCHEMA = 'iw7.t7-registration-material-bindings/1'
CONTRACT = 'registration-material-bindings-source-contract.json'
MODULE = 'registration_material_bindings.hpp'
ENTRY = 'native_registration_material_bindings.inc'
FIXTURE = 'registration_material_bindings_fixture.cpp'
CAPTURE_NAME = 'selected_image_material_bindings_capture.hpp'
OBSERVER_NAME = 'selected_image_material_bindings_observer.hpp'


def pin(raw):
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def capture_source(original, members):
    # Derive the same private cache without changing either frozen input.
    parts.require_pin(original, incoming.BASE_CAPTURE, 'immutable CPP39 capture')
    once = prepare_cli.helper.once
    text = members.decode()
    text = once(text, 'typename Readable, typename Query, typename Copy>',
                'typename Recheck, typename Readable, typename Query, typename Copy>')
    text = once(text, 'void record_incoming(const GfxImage* pointer, const std::string& expected_raw_name,',
                'void record_binding(const GfxImage* pointer, Recheck recheck,')
    text = once(text, 'first == second && first_name == second_name && first_name == expected_raw_name',
                'first == second && first_name == second_name')
    text = once(text, '        fresh_query(query, pointer);\n        GfxImage copied{};',
                '        for (const unsigned char c : first_name)\n'
                '            scalar::require(c >= 0x20, "Control byte in registration image name");\n'
                '        fresh_query(query, pointer);\n        GfxImage copied{};')
    text = once(text, '        fresh_query(query, pointer);\n        GfxImage copied{};',
                '        recheck(); // Original MODEL/material/table/binding, within this callback.\n'
                '        fresh_query(query, pointer);\n        GfxImage copied{};')
    text = once(text,
        '        // Association here is ONLY this callback header and its twice-owned exact name.\n'
        '        // It is not the selected MODEL binding, renderer identity or a resolved asset.\n',
        '        // Rechecked numeric MODEL binding and twice-owned name; no renderer/asset identity claim.\n')
    return incoming.capture_source(original, text.encode())


def observer_source(original):
    parts.require_pin(original, incoming.BASE_OBSERVER, 'immutable CPP39 observer')
    once = prepare_cli.helper.once
    text = once(original.decode(), '#include "registration_image_header_capture.hpp"\n',
        '#include "'+CAPTURE_NAME+'"\n#include "'+MODULE+'"\n')
    text = once(text, '        bool registration_copy_enabled_ = false;\n',
        '        bool registration_copy_enabled_ = false;\n'
        '        registration_material_bindings::collector material_bindings_;\n'
        '        bool material_bindings_enabled_ = false;\n')
    text = once(text, '                    registration_ = capture(pointer, reinterpret_cast<std::uintptr_t>(incoming.data));\n',
        '                    registration_ = capture(pointer, reinterpret_cast<std::uintptr_t>(incoming.data));\n'
        '                    if (material_bindings_enabled_)\n'
        '                        material_bindings_.record(registration_.ordinal, pointer, readable_, query_,\n'
        '                            &registration_image_header_capture::copy_leaf);\n')
    return once(text, '        void begin_registration_metadata()\n',
        '        void begin_material_bindings()\n'
        '        {\n'
        '            const std::lock_guard lock(mutex_);\n'
        '            resident_image::require(!begun_, "Material bindings context is single-use");\n'
        '            material_bindings_enabled_ = true; begun_ = true; active_.store(true);\n'
        '        }\n'
        '        nlohmann::ordered_json finish_material_bindings(bool zone_complete)\n'
        '        {\n'
        '            const std::lock_guard lock(mutex_);\n'
        '            resident_image::require(begun_ && !finished_ && material_bindings_enabled_,\n'
        '                "Original material bindings context required");\n'
        '            active_.store(false); finished_ = true;\n'
        '            return material_bindings_.finish(callbacks_, matches_, duplicate_, search_refused_.load(), zone_complete);\n'
        '        }\n'
        '        void begin_registration_metadata()\n')


def wire(main, cli, base_observer, base_capture, members, module, entry):
    for role, text in (('main', main), ('cli', cli)):
        parts.require_pin(text.encode(), incoming.BASE_PAIR[role], 'material bindings base '+role)
    once = prepare_cli.helper.once
    embedded = incoming.embedded
    old_capture = embedded(base_capture.decode(), ('selected_material_observation.hpp', 'selected_image_header_metadata.hpp'))
    new_capture = embedded(capture_source(base_capture, members), ('selected_material_observation.hpp', 'selected_image_header_metadata.hpp'))
    old_observer = embedded(base_observer.decode(), ('selected_material_observation.hpp', 'registration_image_header_capture.hpp'))
    new_observer = embedded(observer_source(base_observer), ('selected_material_observation.hpp', CAPTURE_NAME, MODULE))
    cli = once(cli, old_capture, new_capture)
    cli = once(cli, old_observer, embedded(module.decode(), (CAPTURE_NAME,))+'\n'+new_observer)
    parts.require(main.count(registration.FLAG) == 2, 'Exact CPP39 selector inventory required')
    main = main.replace(registration.FLAG, '('+registration.FLAG+' || '+FLAG+')')
    cli = once(cli, ' || '+registration.FLAG+'))\n', ' || '+registration.FLAG+' || '+FLAG+'))\n')
    anchor = '\t// New opt-in route. Copy header/name only inside the original registration callback.\n'
    cli = once(cli, anchor, ''.join('\t'+line+'\n' if line else '\n' for line in entry.decode().splitlines())+'\n'+anchor)
    selector = '\t\t\t\tconst bool material_bindings = args.size() == 5 && args[1] == "'+OPTION+'";\n'
    exclusions = ('t7-iw7-model', 't7-iw7-model-v2', 't7-iw7-model-streamed-v1', 't7-iw7-model-streamed-v2',
        't7-iw7-catalog', 't7-prepatch-probe', 't7-prepatch-reference-v2', 't7-prepatch-link-v3',
        't7-iw7-material-parts-v1', 't7-iw7-image-provenance-v1', 't7-iw7-image-metadata-v1',
        't7-iw7-image-registration-metadata-v1', 't7-iw7-incoming-image-header-v1')
    selector += '\t\t\t\tif (('+FLAG+' && !material_bindings) || (material_bindings && (\n'
    selector += ' ||\n'.join('\t\t\t\t\tutils::flags::has_flag("'+option+'")' for option in exclusions)+')))\n'
    selector += '\t\t\t\t\tthrow std::runtime_error("Exclusive exact material-bindings arguments required");\n'
    for name, prior in (('registration_metadata',registration.FLAG),
                        ('image_metadata',registration.metadata.FLAG), ('provenance',registration.provenance.FLAG)):
        guard = 'if (('+prior+' && !'+name+') || ('+name+' && (\n'
        cli = once(cli, guard, guard+'\t\t\t\t\t'+FLAG+' ||\n')
    cli = once(cli, '\t\t\t\tconst bool registration_metadata =', selector+'\t\t\t\tconst bool registration_metadata =')
    cli = once(cli, '\t\t\t\tif (registration_metadata) observe_registration_image_metadata_iw7(args[2], args[3], args[4]);',
        '\t\t\t\tif (material_bindings) observe_registration_material_bindings_iw7(args[2], args[3], args[4]);\n'
        '\t\t\t\telse if (registration_metadata) observe_registration_image_metadata_iw7(args[2], args[3], args[4]);')
    cli = once(cli, '\t\t\t\tif ('+registration.FLAG+')\n', '\t\t\t\tif ('+FLAG+')\n'
        '\t\t\t\t\tZONETOOL_ERROR("T7 material bindings refused: %s", error.what());\n'
        '\t\t\t\telse if ('+registration.FLAG+')\n')
    parts.require(len(cli.encode()) <= 192*1024, 'Finite new material-bindings CLI source cap exceeded')
    return main, cli


def inputs(read):
    c = json.loads(read(HERE/CONTRACT, 16*1024))
    parts.require(type(c) is dict and c['schema'] == 'iw7.t7-registration-material-bindings-source/1' and
        c['source_profile'] == NAME and c['native_option'] == OPTION and c['report_schema'] == SCHEMA and
        c['source_only_pending'] is True and c['cpp_qualified'] is False and c['native_observed'] is False and
        c['ready'] is False and type(c['files']) is dict and set(c['files']) == {MODULE,ENTRY,FIXTURE},
        'Exact pending material bindings source contract required')
    files = {}
    for name, item in c['files'].items():
        parts.require(type(item) is dict and set(item) == {'bytes','sha256'} and type(item['bytes']) is int and
            0 < item['bytes'] <= 32*1024 and type(item['sha256']) is str and len(item['sha256']) == 64,
            'Typed bounded material bindings source pin required')
        raw = read(HERE/name, 32*1024, item['sha256']).replace(b'\r\n', b'\n')
        parts.require_pin(raw, (item['bytes'],item['sha256']), name)
        files[name] = raw
    original_capture = read(HERE/registration.CAPTURE, 32*1024, incoming.BASE_CAPTURE[1]).replace(b'\r\n',b'\n')
    original_observer = registration.observer_source(read(HERE/registration.provenance.HELPER,
        32*1024,registration.BASE_OBSERVER[1]).replace(b'\r\n',b'\n')).encode()
    members = read(HERE/incoming.MEMBERS, 16*1024, c['base_members']['sha256']).replace(b'\r\n',b'\n')
    parts.require_pin(members, (c['base_members']['bytes'],c['base_members']['sha256']), 'existing CPP87 members')
    for role, value in (('derived_capture',capture_source(original_capture,members)),
                        ('derived_observer',observer_source(original_observer))):
        parts.require_pin(value.encode(), (c[role]['bytes'],c[role]['sha256']), role)
    return c, files, original_observer, original_capture, members


def overlay(main, cli, read):
    c, files, observer, capture, members = inputs(read)
    main, cli = wire(main,cli,observer,capture,members,files[MODULE],files[ENTRY])
    for role, value in (('main',main),('cli',cli)):
        parts.require_pin(value.encode(), (c[role]['bytes'],c[role]['sha256']), 'material bindings '+role)
    return main, cli

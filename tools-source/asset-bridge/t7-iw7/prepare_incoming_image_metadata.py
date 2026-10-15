"""One bounded incoming-IMAGE observation seam over the exact frozen CPP39 source pair."""
import json
from pathlib import Path
import prepare_cli
import prepare_image_registration_metadata as registration
import prepare_material_parts as parts

HERE = Path(__file__).resolve().parent
NAME = 't7-incoming-image-header-observation-v1'
OPTION = '-t7-iw7-incoming-image-header-v1'
FLAG = 'utils::flags::has_flag("t7-iw7-incoming-image-header-v1")'
SCHEMA = 'iw7.t7-incoming-image-header-observation/1'
CONTRACT = 'incoming-image-source-contract.json'
MEMBERS = 'incoming_image_capture_members.inc'
MODULE = 'incoming_image_event_observation.hpp'
ENTRY = 'native_incoming_image_metadata.inc'
FIXTURE = 'incoming_image_event_fixture.cpp'
BASE_CAPTURE = (16485, 'edf7bec2865e2098782bb4b31e58a48508c83bcbdf35d190affa7b451f0e6345')
BASE_OBSERVER = (16575, '9c82b0969e3d44c9dbafb5fa4d6cf0b60fce450d60a77291342e97518c365380')
BASE_FIXTURE = (12041, 'fb067267b3b7ecd7081a2d72ecd7add7bbdf468d13085dd75a85c498eb4a59fa')
BASE_PAIR = {'main': (43620, '05f601ffdeff533809acb023e53b850570f08f79594d5954232338f3a1b597b8'),
             'cli': (175031, '26e9ae7ff1a3f016130b57cea265a73a8ecbcdb6bed20b3bc39a4c7f51742967')}


def selected(args):
    value = getattr(args, 'image_incoming_header_v1', False)
    parts.require(type(value) is bool, 'Explicit incoming-image boolean required')
    parts.require(not value or getattr(args, 'image_registration_metadata_v1', False) is True,
                  'Incoming source extension requires its exact registration base')
    return value


def capture_source(original, members):
    parts.require_pin(original, BASE_CAPTURE, 'immutable CPP39 capture')
    return prepare_cli.helper.once(original.decode(), '    public:\n        void reset()\n',
        '    public:\n'+''.join('        '+line+'\n' if line else '\n' for line in members.decode().splitlines())+
        '        void reset()\n')


def observer_source(original):
    parts.require_pin(original, BASE_OBSERVER, 'immutable CPP39 observer')
    once = prepare_cli.helper.once
    text = once(original.decode(), '#include "registration_image_header_capture.hpp"\n',
        '#include "selected_image_incoming_capture.hpp"\n#include "incoming_image_event_observation.hpp"\n')
    text = once(text, '        bool registration_copy_enabled_ = false;\n',
        '        bool registration_copy_enabled_ = false;\n'
        '        incoming_image_event_observation::collector incoming_events_;\n'
        '        std::atomic<bool> incoming_enabled_{false}, incoming_selected_{false}, incoming_lock_refused_{false};\n')
    text = once(text, '        void begin_registration_metadata()\n',
        '        void configure_incoming(const std::vector<std::string>& args, bool requested)\n'
        '        {\n'
        '            const std::lock_guard lock(mutex_);\n'
        '            const bool selected = incoming_events_.arm(args, requested);\n'
        '            incoming_selected_.store(selected); incoming_enabled_.store(selected);\n'
        '        }\n'
        '        bool incoming_selected() const noexcept { return incoming_selected_.load(); }\n'
        '        void before_image_bypass(XAssetType type, XAssetHeader incoming) noexcept\n'
        '        {\n'
        '            if (type != ASSET_TYPE_IMAGE || !incoming_enabled_.load()) return;\n'
        '            try { const std::lock_guard lock(mutex_);\n'
        '                incoming_events_.observe(type, incoming, readable_, query_, &registration_image_header_capture::copy_leaf); }\n'
        '            catch (...) { incoming_lock_refused_.store(true); }\n'
        '        }\n'
        '        void begin_incoming_map()\n'
        '        { const std::lock_guard lock(mutex_); incoming_events_.begin_map(); }\n'
        '        nlohmann::ordered_json finish_incoming(bool map_complete)\n'
        '        {\n'
        '            const std::lock_guard lock(mutex_); incoming_enabled_.store(false);\n'
        '            return incoming_events_.finish(map_complete, incoming_lock_refused_.load());\n'
        '        }\n'
        '        void begin_registration_metadata()\n')
    return text


def embedded(text, includes):
    for token in ('#pragma once\n', *('#include "'+name+'"\n' for name in includes)):
        text = text.replace(token, '')
    return text


def fixture_source(original):
    parts.require_pin(original, BASE_FIXTURE, 'immutable registration fixture39')
    text=prepare_cli.helper.once(original.decode(), '#include "selected_image_registration_observer.hpp"',
        '#include "selected_image_incoming_observer.hpp"')
    return prepare_cli.helper.once(text, 'int main()', 'int original_registration_fixture_main()')


def wire(main, cli, base_observer, base_capture, members, module, entry):
    for role, text in (('main', main), ('cli', cli)):
        parts.require_pin(text.encode(), BASE_PAIR[role], 'incoming base '+role)
    once = prepare_cli.helper.once
    old_capture = embedded(base_capture.decode(), ('selected_material_observation.hpp', 'selected_image_header_metadata.hpp'))
    new_capture = embedded(capture_source(base_capture, members), ('selected_material_observation.hpp', 'selected_image_header_metadata.hpp'))
    old_observer = embedded(base_observer.decode(), ('selected_material_observation.hpp', 'registration_image_header_capture.hpp'))
    new_observer = embedded(observer_source(base_observer), ('selected_material_observation.hpp', 'selected_image_incoming_capture.hpp', MODULE))
    cli = once(cli, old_capture, new_capture)
    cli = once(cli, old_observer, embedded(module.decode(), ('selected_image_incoming_capture.hpp',))+'\n'+new_observer)
    parts.require(main.count(registration.FLAG) == 2, 'Exact CPP39 main selector inventory required')
    main = main.replace(registration.FLAG, '('+registration.FLAG+' || '+FLAG+')')
    cli = once(cli, ' || '+registration.FLAG+'))\n',
        ' || '+registration.FLAG+' || selected_image_provenance_context.incoming_selected()))\n')
    bypass = '\t\tif (type == ASSET_TYPE_IMAGE)\n\t\t{\n\t\t\treturn header;\n\t\t}'
    cli = once(cli, bypass, '\t\tif (type == ASSET_TYPE_IMAGE)\n\t\t{\n'
        '\t\t\tselected_image_provenance_context.before_image_bypass(type, header);\n\t\t\treturn header;\n\t\t}')
    # get_command_line_arguments() is the EXISTING OS argv route, defined before init.
    # This is on post_unpack, before hook creation and the subsequent ComInit bootstraps.
    cli = once(cli, '\t\t// enable dumping\n',
        '\t\tconst bool incoming_profile_requested = '+FLAG+';\n'
        '\t\tif (incoming_profile_requested)\n'
        '\t\t\tselected_image_provenance_context.configure_incoming(get_command_line_arguments(), true);\n\n'
        '\t\t// enable dumping\n')
    anchor = '// New opt-in route. Copy header/name only inside the original registration callback.\n'
    cli = once(cli, '\t'+anchor, ''.join('\t'+line+'\n' if line else '\n' for line in entry.decode().splitlines())+'\n\t'+anchor)
    selector = '\t\t\t\tconst bool incoming_metadata = args.size() == 5 && args[1] == "'+OPTION+'";\n'
    cli = once(cli, '\t\t\t\tconst bool registration_metadata =', selector+'\t\t\t\tconst bool registration_metadata =')
    cli = once(cli, '\t\t\t\tif (registration_metadata) observe_registration_image_metadata_iw7(args[2], args[3], args[4]);',
        '\t\t\t\tif (incoming_metadata) observe_incoming_image_metadata_iw7(args[2], args[3], args[4]);\n'
        '\t\t\t\telse if (registration_metadata) observe_registration_image_metadata_iw7(args[2], args[3], args[4]);')
    cli = once(cli, '\t\t\t\tif ('+registration.FLAG+')\n',
        '\t\t\t\tif (selected_image_provenance_context.incoming_selected())\n'
        '\t\t\t\t\tZONETOOL_ERROR("T7 incoming image observation refused: %s", error.what());\n'
        '\t\t\t\telse if ('+registration.FLAG+')\n')
    parts.require(len(cli.encode()) <= 192*1024, 'Finite incoming CLI source cap exceeded')
    return main, cli


def overlay(main, cli, read):
    c = json.loads(read(HERE/CONTRACT, 16*1024))
    parts.require(type(c) is dict and c['schema'] == 'iw7.t7-incoming-image-source/1' and c['source_profile'] == NAME and
        c['native_option'] == OPTION and c['report_schema'] == SCHEMA and c['target_name'] == '$camo_base_normal' and
        c['source_only_pending'] is True and c['cpp_qualified'] is False and c['native_observed'] is False and c['ready'] is False and
        type(c['files']) is dict and set(c['files']) == {MEMBERS,MODULE,ENTRY,FIXTURE},
        'Exact pending incoming source contract required')
    files={}
    for name,item in c['files'].items():
        parts.require(type(item) is dict and set(item) == {'bytes','sha256'} and type(item['bytes']) is int and
            0 < item['bytes'] <= 32*1024 and type(item['sha256']) is str and len(item['sha256']) == 64,
            'Typed bounded incoming source pin required')
        raw=read(HERE/name,32*1024,item['sha256']).replace(b'\r\n',b'\n')
        parts.require_pin(raw,(item['bytes'],item['sha256']),name)
        files[name]=raw
    base_capture = read(HERE/registration.CAPTURE, 32*1024, BASE_CAPTURE[1]).replace(b'\r\n', b'\n')
    base_observer = registration.observer_source(read(HERE/'selected_image_provenance.hpp', 32*1024,
        registration.BASE_OBSERVER[1]).replace(b'\r\n', b'\n')).encode()
    for role,value in (('derived_capture',capture_source(base_capture,files[MEMBERS])),
                       ('derived_observer',observer_source(base_observer)),
                       ('derived_baseline_fixture',fixture_source(read(HERE/registration.FIXTURE,32*1024,BASE_FIXTURE[1]).replace(b'\r\n',b'\n')))):
        parts.require_pin(value.encode(),(c[role]['bytes'],c[role]['sha256']),role)
    main, cli = wire(main, cli, base_observer, base_capture, files[MEMBERS], files[MODULE], files[ENTRY])
    for role, value in (('main',main),('cli',cli)):
        parts.require_pin(value.encode(), (c[role]['bytes'],c[role]['sha256']), 'incoming '+role)
    return main, cli

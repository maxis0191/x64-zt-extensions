"""Render the pinned real JSON parser cores in memory; no native invocation.

DEFAULT preserves all input strings. Opt-in composes the three rejecting FILE
hooks and checked memory, then shares actual parser bodies with legacy wrappers.
No SDK, filesystem, data capture, allocator or compiler is opened here.
"""
import hashlib
import re

import prepare_pair_checked_parse as session
import prepare_pair_checked_memory as memory

NATIVE = session.NATIVE
SESSION_HEADER = 'tools-source/asset-bridge/weapon-export/native_pair_session.hpp'
STRUCTS = NATIVE + 'iw7/structs.hpp'
PINS = {**session.PINS, STRUCTS: '482affaf3641dc5318422c4cef45383923183349ae91d18e9d3ff29699f8a0df',
        SESSION_HEADER: '65995c3552058107c572c70bd12f2b8134c81550edd87cf584fdbb5176dc7d93'}
CORE_HEADER = NATIVE + 'iw7/assets/weapon_pair_json_core.hpp'
WEAPON_CORE = NATIVE + 'iw7/assets/weapon_pair_json_core.cpp'
ATTACHMENT_CORE = NATIVE + 'iw7/assets/attachment_pair_json_core.cpp'
# Inclusive LF line spans and hashes from immutable fab935 Git blobs.
CUTS = {
    'weapon_map': (6, 16, '439feca5b6d2075c7719c9bd8c4223ec3615d0741ad7b49d0a6f1d5a5a0041a5'),
    'weapon_macros': (30, 190, 'bce82be7ca1c6ca5a538f61d12c39280379eff034408bb333375d584713f843e'),
    'weapon_helpers': (192, 1139, 'd30bf5cc4769c7395319e560d4f1db3209332f00635d2b7d1bc95f7a59f0d4e3'),
    'weapon_root': (1158, 1162, '8d3cd2b78a4d24cf273cbc8457c13f262ef5c23fab301ab88813da6112b904fb'),
    'attachment_map': (84, 94, '0c55cbc0dae0a7dd5d92456d91c71b000805f291cfd094d58b8bad52e2650522'),
    'attachment_macros': (108, 177, 'e7cd850b71524c2ff78f1a4e4540b27e1d290978ce197f36265a621a861de516'),
    'attachment_helpers': (179, 662, '204b42dc647533c982fd9c9dcea7e478208d0cfda9ace13e5c4a4cb7a492e6b6'),
    'attachment_dispatch': (664, 673, 'a6f2450cff5f71143bd0cebca349692053440cf601c723457cc6ad2dc0795b25'),
    'attachment_root': (694, 782, 'c0ea4400bf8fc42465c20a18767a4d7ac93eb9de0586bf4a71f7fc3e2d893be7'),
}

HEADER = r'''#pragma once
// Private opt-in core. Real pinned types; no engine/FILE/builder interface.
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <Windows.h>
#ifdef min
#undef min
#endif
#ifdef max
#undef max
#endif
#include <array>
#include <algorithm>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <exception>
#include <limits>
#include <mutex>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>
#ifndef assert_sizeof
#define assert_sizeof(__ASSET__, __SIZE__) static_assert(sizeof(__ASSET__) == __SIZE__)
#endif
#ifndef assert_offsetof
#define assert_offsetof(__ASSET__, __VARIABLE__, __OFFSET__) static_assert(offsetof(__ASSET__, __VARIABLE__) == __OFFSET__)
#endif
#include "../structs.hpp"
#ifdef min
#undef min
#endif
#ifdef max
#undef max
#endif
#if defined(JSON_DIAGNOSTICS) && JSON_DIAGNOSTICS != 1
#error "The pinned core requires JSON_DIAGNOSTICS=1 in every translation unit"
#endif
#ifndef JSON_DIAGNOSTICS
#define JSON_DIAGNOSTICS 1
#endif
#include <json.hpp>
#include "../../utils/memory.hpp"
namespace zonetool::iw7::pair_json
{
    using ordered_json = nlohmann::ordered_json;
    using ScriptStrings = std::vector<std::pair<scr_string_t*, const char*>>;
    WeaponCompleteDef* parse_weapon_json(ordered_json&, zone_memory*, ScriptStrings&);
    WeaponAttachment* parse_attachment_json(ordered_json&, zone_memory*, ScriptStrings&);
}
'''


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def once(text, old, new):
    need(text.count(old) == 1, 'Unique pinned core anchor required')
    return text.replace(old, new, 1)


def _validate(sources):
    need(type(sources) is dict and set(sources) == set(PINS), 'Exact twelve Source roles required')
    normalized = {}
    for path, digest in PINS.items():
        value = sources[path]
        need(type(value) is str and len(value) <= 2097152, 'Source character bound before scans')
        need('\0' not in value, 'NUL-free Source required')
        try:
            raw = value.encode('utf-8', errors='strict')
        except UnicodeError as error:
            raise ValueError('Strict UTF-8 Source required') from error
        need(len(raw) <= 2097152, 'Source byte bound')
        text = value.replace('\r\n', '\n')
        need(sha(text) == digest, 'Pinned core Source drift: ' + path)
        normalized[path] = text
    return normalized


def _cut(text, key):
    first, last, digest = CUTS[key]
    raw = ''.join(text.splitlines(keepends=True)[first-1:last])
    need(sha(raw) == digest, 'Pinned core cut differs: ' + key)
    return raw


def _context(text):
    return text.replace('this->add_script_string(', 'add_script_string(strings, ')


def _map(text, cls):
    text = once(text, 'void ' + cls + '::add_script_string(scr_string_t* ptr, const char* str)',
                'static void add_script_string(ScriptStrings& strings, scr_string_t* ptr, const char* str)')
    return text.replace('this->script_strings', 'strings')


def _weapon_helpers(text):
    # Every actual helper signature and actual call has the same final mem arg.
    signatures = re.findall(r'void weapon_def::(\w+)\(([^\n]+)\)', text)
    need(len(signatures) == 9, 'Nine real weapon helper overloads required')
    forwards = ''.join('void ' + name + '(' + args + ', ScriptStrings& strings);\n' for name, args in signatures)
    body = text.replace('weapon_def::', '')
    need(body.count('zone_memory* mem)') == 9, 'Exact helper parameter anchors required')
    body = body.replace('zone_memory* mem)', 'zone_memory* mem, ScriptStrings& strings)')
    body = body.replace('ScriptStrings& strings)\n\t{',
                        'ScriptStrings& strings)\n\t{\n\t\tstatic_cast<void>(strings);\n\t\tstatic_cast<void>(mem);')
    # These are the eight pinned calls; no string/comment or JSON parser match.
    need(len(re.findall(r'\bparse(?:_\w+)?\([^\n]*, mem\);', body)) == 8, 'Eight real helper calls required')
    body = re.sub(r'(\bparse(?:_\w+)?\([^\n]*), mem\);', r'\1, mem, strings);', body)
    return forwards + body


def render(sources, *, stage_core=False):
    source = _validate(sources)  # All pins precede any cut or output construction.
    need(type(stage_core) is bool, 'Literal Source staging selection required')
    metadata = dict(native_pin=session.PIN, source_only=True, core_staged=False,
                    cpp_compiled=False, cpp_linked=False, actual_parse=False,
                    file_route_qualified=False, ready=False,
                    json_revision='484483acad6d562306efc9b3c6d413404f1b1f8a',
                    json_header_sha256='53855e4a20d7bc92d9624bf0d83fba8e22d0d9de83f9480bd4895651602fa8cc',
                    json_diagnostics=1)
    if not stage_core:
        return dict(sources), metadata
    wpath = NATIVE + 'iw7/assets/weapondef.cpp'
    apath = NATIVE + 'iw7/assets/weaponattachment.cpp'
    blocks = {key: _cut(source[wpath if key.startswith('weapon') else apath], key) for key in CUTS}
    # Compose the existing hooks without a pathname read. Their bodies still reject.
    out, _ = session.render({p: source[p] for p in session.PINS}, stage_inactive=True,
                            source_header=source[SESSION_HEADER])
    out[STRUCTS] = source[STRUCTS]
    out[SESSION_HEADER] = source[SESSION_HEADER]
    out[memory.SOURCE_PATH], _ = memory.render(source[memory.SOURCE_PATH], stage_checked=True)
    wbody = _context(blocks['weapon_macros'] + '\n' + _weapon_helpers(blocks['weapon_helpers']))
    # Explicit unused-parameter expressions preserve /W4 /WX without inheriting
    # std_include's global warning suppression or changing the real operations.
    ahelpers = blocks['attachment_helpers'].replace('zone_memory* mem)\n\t{',
        'zone_memory* mem)\n\t{\n\t\tstatic_cast<void>(mem);')
    abody = _context(blocks['attachment_macros'] + '\n' + ahelpers + '\n' + blocks['attachment_dispatch'])
    wroot = once(blocks['weapon_root'], 'parse_complete(asset, data, mem);', 'detail::parse_complete(asset, data, mem, strings);')
    aroot = _context(blocks['attachment_root'])
    prefix = '#include "weapon_pair_json_core.hpp"\nnamespace zonetool::iw7::pair_json\n{\nnamespace detail\n{\n'
    out[WEAPON_CORE] = prefix + _map(blocks['weapon_map'], 'weapon_def') + wbody + '\n}\nWeaponCompleteDef* parse_weapon_json(ordered_json& data, zone_memory* mem, ScriptStrings& strings)\n{\n' + wroot + '}\n}\n'
    # Attachment macros need the same real context helper in their lexical namespace.
    aroot = aroot.replace('add_script_string(strings, ', 'detail::add_script_string(strings, ')
    # The parse_att overloads are internal; qualify the dispatch macro's call.
    abody = abody.replace('parse_att(asset->__att__,', 'detail::parse_att(asset->__att__,')
    out[ATTACHMENT_CORE] = prefix + _map(blocks['attachment_map'], 'weapon_attachment') + abody + '\n}\nWeaponAttachment* parse_attachment_json(ordered_json& data, zone_memory* mem, ScriptStrings& strings)\n{\nusing detail::add_script_string;\n' + aroot + '}\n}\n'
    out[CORE_HEADER] = HEADER
    for path, cls, root, key in [(wpath, 'weapon_def', 'WeaponCompleteDef', 'weapon'), (apath, 'weapon_attachment', 'WeaponAttachment', 'attachment')]:
        body = out[path]
        # Move the real helper/macro definitions, not their handwritten replicas.
        for label in (('weapon_macros', 'weapon_helpers') if key == 'weapon' else ('attachment_macros', 'attachment_helpers', 'attachment_dispatch')):
            body = once(body, blocks[label], '// Pinned Source moved to pair JSON core: ' + label + '\n')
        body = once(body, '#include "' + ('weapondef' if key == 'weapon' else 'weaponattachment') + '.hpp"',
                    '#include "' + ('weapondef' if key == 'weapon' else 'weaponattachment') + '.hpp"\n#include "weapon_pair_json_core.hpp"')
        call = '\t\treturn pair_json::parse_' + key + '_json(data, mem, this->script_strings);\n'
        body = once(body, blocks[key + '_root'], call)
        out[path] = body
    for path in (WEAPON_CORE, ATTACHMENT_CORE):
        need(not re.search(r'\b(?:DB_|SL_|ZONETOOL_|filesystem::|asset_interface)', out[path]), 'Engine/FILE surface in standalone core')
    metadata.update(core_staged=True, staged_rejecting_hooks=3,
                    core_hashes={p: sha(out[p]) for p in (CORE_HEADER, WEAPON_CORE, ATTACHMENT_CORE)},
                    checked_memory_sha256=sha(out[memory.SOURCE_PATH]))
    return out, metadata

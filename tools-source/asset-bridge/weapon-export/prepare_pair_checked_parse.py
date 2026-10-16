"""Render inactive checked-parser/route hooks in memory from ten Source pins.

No output tree, native invocation, CLI wiring, allocation probe or producer.
Default rendering preserves every input byte. Staged hooks always reject.
"""
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIN = 'fab935826c898806855376662a8a03317b3ad8f1'
BASE = '0d56ddb107b51e6741b178d1f8cf7b927226e3b6'
NATIVE = 'src/zonetool/zonetool/'
PINS = {
    NATIVE + 'iw7/assets/weapondef.cpp': 'fc6defc7d4cdad56d3615ff2d13a1c6715f8b6e53dbdc7dd4be25ce4255050b5',
    NATIVE + 'iw7/assets/weaponattachment.cpp': '746d520c49f122bc650652da78deed45b091198bb10b30dc48bc6a38c9227e4c',
    NATIVE + 'iw7/assets/weapondef.hpp': '3c1f7b2fd4fd5ce7a4919dbabc6a5bf4e1ac1591029a89e29f3cf77c1821d084',
    NATIVE + 'iw7/assets/weaponattachment.hpp': 'ce53d8d720236d55e2b174cf40ef5d56158c958f1b0ed885b55fb820d7d825ff',
    NATIVE + 'utils/io/filesystem.hpp': 'd1534192326ac803ef7e5e1759a8649034e7e69511274372ce717823d2e0796d',
    NATIVE + 'utils/io/filesystem.cpp': '580cdb455ad178b1cb14fcadecea1a7ec2738ecdd25b655aa12254b9098a76c2',
    NATIVE + 'utils/memory.hpp': '9025b835313ee45ba3418e3322210dec3b6d334e504a1dd3b59e9f38e2898f35',
    'tools-source/asset-bridge/weapon-export/native_neutral_dependencies.hpp': 'b5d4aa4f09db9eb28434e350e5cd9358ee522cd683882539476e2a0bb6e4c95e',
    'tools-source/asset-bridge/weapon-export/neutral_pair_bodies.py': '820c8580549c3d0e5022e58d5f5bfc120d23db64b9f9f6e4513e05494c178626',
    'tools-source/asset-bridge/weapon-export/NATIVE-BODY-SCHEMA.md': 'ac2980872c1ae97b76a998998e43b88601eb33ae14ab6a3677d3c6fb1b338809',
}
HEADER_DESTINATION = NATIVE + 'utils/native_pair_session.hpp'
EXPLICIT_HEADER_BYTES = 8349
EXPLICIT_HEADER_SHA256 = '65995c3552058107c572c70bd12f2b8134c81550edd87cf584fdbb5176dc7d93'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def replace_once(text, anchor, replacement):
    require(text.count(anchor) == 1, 'Unique pinned staging anchor required')
    return text.replace(anchor, replacement, 1)


def validate_sources(sources):
    require(type(sources) is dict and set(sources) == set(PINS), 'Exactly ten Source roles required')
    for path, digest in PINS.items():
        text = sources[path]
        require(type(text) is str and '\0' not in text and len(text.encode('utf-8')) <= 2097152,
                'Bounded Source text required: ' + path)
        require(hashlib.sha256(text.replace('\r\n', '\n').encode()).hexdigest() == digest,
                'Pinned Source drift: ' + path)


def render(sources, *, stage_inactive=False, source_header=None):
    validate_sources(sources)
    require(type(stage_inactive) is bool, 'Literal Source staging selection required')
    result = dict(sources)
    metadata = {'native_pin': PIN, 'support_base': BASE, 'source_only': True,
                'actual_activation': False, 'fatal_allocator_covered': False,
                'schema_native_bridge': False, 'live_file_identity': False,
                'route_alias_exclusion': False, 'cpp_fixture_executed': False}
    if not stage_inactive:
        return result, metadata
    # Only our authored header is read; never a body, SDK or native artifact.
    if source_header is None:
        header_path = HERE / 'native_pair_session.hpp'
        require(header_path.is_file() and not header_path.is_symlink(), 'Regular authored Source header required')
        with header_path.open('rb') as stream:
            raw = stream.read(2097153)
    else:
        require(type(source_header) is str and len(source_header) <= 2097152,
                'Bounded explicit authored Source header required')
        raw = source_header.replace('\r\n', '\n').encode('utf-8', errors='strict')
        require(len(raw) == EXPLICIT_HEADER_BYTES and hashlib.sha256(raw).hexdigest() == EXPLICIT_HEADER_SHA256,
                'Pinned explicit authored Source header drift')
    require(len(raw) <= 2097152 and b'\0' not in raw, 'Bounded authored Source header required')
    header = raw.decode('utf-8', errors='strict').replace('\r\n', '\n')
    require('[[noreturn]] inline void reject_native_activation()' in header, 'Inactive rejection contract absent')
    result[HEADER_DESTINATION] = header
    for filename, cls, root in [('weapondef', 'weapon_def', 'WeaponCompleteDef'),
                                ('weaponattachment', 'weapon_attachment', 'WeaponAttachment')]:
        hp = NATIVE + 'iw7/assets/' + filename + '.hpp'
        cp = NATIVE + 'iw7/assets/' + filename + '.cpp'
        include = '#include "../zonetool.hpp"'
        result[hp] = replace_once(result[hp], include, include + '\n#include "../../utils/native_pair_session.hpp"')
        signature = '\t\t' + root + '* parse(const std::string& name, zone_memory* mem);'
        declaration = '\n\t\t' + root + '* parse_checked_inactive(const std::string& name, zone_memory* mem, const player_pair_session::ReadRequest& request);'
        result[hp] = replace_once(result[hp], signature, signature + declaration)
        anchor = '\tvoid ' + cls + '::init(const std::string& name, zone_memory* mem)'
        stub = ('\t' + root + '* ' + cls + '::parse_checked_inactive(const std::string& name, zone_memory* mem, const player_pair_session::ReadRequest& request)\n'
                '\t{\n\t\tstatic_cast<void>(name);\n\t\tstatic_cast<void>(mem);\n\t\tstatic_cast<void>(request);\n'
                '\t\tplayer_pair_session::reject_native_activation();\n\t}\n\n')
        result[cp] = replace_once(result[cp], anchor, stub + anchor)
    hp, cp = NATIVE + 'utils/io/filesystem.hpp', NATIVE + 'utils/io/filesystem.cpp'
    declaration = ('\t\t// Deliberately cannot seal or restore a live route in this Source lot.\n'
                   '\t\tclass pair_route_seal_inactive final\n\t\t{\n\t\tpublic:\n'
                   '\t\t\tpair_route_seal_inactive();\n'
                   '\t\t\tpair_route_seal_inactive(const pair_route_seal_inactive&) = delete;\n'
                   '\t\t\tpair_route_seal_inactive& operator=(const pair_route_seal_inactive&) = delete;\n'
                   '\t\t\tpair_route_seal_inactive(pair_route_seal_inactive&&) = delete;\n'
                   '\t\t\tpair_route_seal_inactive& operator=(pair_route_seal_inactive&&) = delete;\n\t\t};\n\n')
    anchor = '\t\tvoid set_fastfile(const std::string& ff);'
    result[hp] = replace_once(result[hp], anchor, declaration + anchor)
    # The CPP includes the authored helper without changing existing header APIs.
    include = '#include "filesystem.hpp"'
    result[cp] = replace_once(result[cp], include, include + '\n#include "../native_pair_session.hpp"')
    anchor = '\t\tvoid set_fastfile(const std::string& ff)'
    stub = ('\t\tpair_route_seal_inactive::pair_route_seal_inactive()\n\t\t{\n'
            '\t\t\tplayer_pair_session::reject_native_activation();\n\t\t}\n\n')
    result[cp] = replace_once(result[cp], anchor, stub + anchor)
    metadata['authored_header_sha256'] = hashlib.sha256(header.encode()).hexdigest()
    metadata['staged_inactive_hooks'] = 3
    return result, metadata

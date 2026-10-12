"""Read-only inspection of a bounded v11 HKX envelope or pinned runtime strings.

No native calls, shape decoding, cooking, relocation, writing or readiness claim.
The three-section v11 layout is corroborated by one retained PhysicsAsset; it
does not establish the required root/schema of an IW7 world collision packfile.
"""
import argparse
import hashlib
import json
import re
import struct

from trigger_bridge import checked_path, require

MAX_HKX = 1024 * 1024
RDATA_SIZE = 3194880
RDATA_SHA256 = '28b66189c1f35442d3e32ea5077e785e7cb8fbf45ed420094dc6b2795afd04e5'
HEADER = struct.Struct('<4I4B5i16sI2h')
SECTION = struct.Struct('<20s7I16s')
VERSION = b'hk_2014.2.5-r1'
MARKERS = (
    b'hk_2014.2.5-r1', b'HavokPhysicsAsset', b'HavokPhysicsShapeList',
    b'HavokPhysicsShapeListShapeTagData', b'hknpConvexPolytopeShape',
    b'hknpPhysicsSystemData', b'hknpCompressedMeshShapeData',
    b'hkGeometry', b'hkRootLevelContainer', b'Util\\hkSerializeUtil.cpp',
    b'Packfile\\hkPackfileWriter.cpp',
)


def cstring(data, label, maximum=128):
    end = data.find(b'\0', 0, maximum + 1)
    require(end >= 0, label + ': bounded NUL terminator required')
    try:
        value = data[:end].decode('ascii')
    except UnicodeError as error:
        raise ValueError(label + ': ASCII required') from error
    require(value and all(32 <= ord(char) < 127 for char in value), label + ': invalid text')
    return value


def inspect_hkx(data):
    require(type(data) is bytes and HEADER.size <= len(data) <= MAX_HKX,
            'HKX input must contain a 64-byte header and be at most 1 MiB')
    (magic1, magic2, user_tag, version, pointer, little, reuse, empty,
     section_count, root_section, root_offset, class_section, class_offset,
     contents_version, flags, predicate, predicate_padding) = HEADER.unpack_from(data)
    require((magic1, magic2) == (0x57E0E057, 0x10C0C010), 'Packfile magic differs')
    require(version == 11, 'Only the observed v11 section layout is supported')
    require((pointer, little, reuse, empty) == (8, 1, 0, 1), 'IW7 x64 layout differs')
    require(cstring(contents_version, 'version', 15).encode() == VERSION, 'Havok version differs')
    require(section_count == 3, 'Only the observed three-section layout is supported')
    table_end = HEADER.size + section_count * SECTION.size
    require(len(data) >= table_end, 'Truncated section table')
    sections, previous_end = [], table_end
    expected_names = ('__classnames__', '__types__', '__data__')
    for index in range(section_count):
        name, start, local, global_, virtual, exports, imports, end, _ = SECTION.unpack_from(
            data, HEADER.size + index * SECTION.size)
        name = cstring(name, 'section tag', 19)
        require(name == expected_names[index], 'Unknown section ordering/name')
        offsets = (local, global_, virtual, exports, imports, end)
        require(list(offsets) == sorted(offsets), 'Section offsets are not monotonic')
        require(start >= previous_end and start + end <= len(data), 'Section overlap/out-of-file range')
        sections.append({'name': name, 'start': start, 'data_bytes': local,
                         'local_fixups': local, 'global_fixups': global_,
                         'virtual_fixups': virtual, 'exports': exports,
                         'imports': imports, 'end': end})
        previous_end = start + end
    require(0 <= root_section < section_count and 0 <= class_section < section_count,
            'Root section index outside table')
    root, names = sections[root_section], sections[class_section]
    require(0 <= root_offset < root['data_bytes'], 'Root object outside section data')
    require(names['name'] == '__classnames__' and 0 <= class_offset < names['data_bytes'],
            'Root class outside class-name data')
    end = names['start'] + names['data_bytes']
    root_class = cstring(data[names['start'] + class_offset:end], 'root class')
    name_data = data[names['start']:end]
    classes = sorted(set(match.group()[:-1].decode() for match in
                         re.finditer(rb'(?:Havok|hknp|hkp|hkRoot)[A-Za-z0-9_:]*\0', name_data)))
    return {'schema': 'iw7.asset-bridge.hkx-envelope-inspection/1',
            'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'file_version': version, 'contents_version': VERSION.decode(),
            'layout': [pointer, little, reuse, empty], 'root_section': root_section,
            'root_offset': root_offset, 'root_class': root_class,
            'sections': sections, 'class_names': classes,
            'shape_graph_validated': False, 'fixups_validated': False,
            'runtime_ready': False}


def inspect_rdata(data):
    require(len(data) == RDATA_SIZE and hashlib.sha256(data).hexdigest() == RDATA_SHA256,
            'Runtime snapshot differs from the retained reference')
    markers = {}
    for marker in MARKERS:
        offsets = [match.start() for match in re.finditer(re.escape(marker + b'\0'), data)]
        require(offsets, 'Expected runtime marker missing: ' + marker.decode())
        markers[marker.decode()] = offsets
    return {'schema': 'iw7.asset-bridge.havok-runtime-markers/1',
            'bytes': len(data), 'sha256': RDATA_SHA256, 'markers_at_file_offsets': markers,
            'meaning': 'String presence in a previously patched runtime snapshot; no function ABI proof',
            'runtime_ready': False}


def read_bounded(path, limit):
    with checked_path(path, True).open('rb') as stream:
        data = stream.read(limit + 1)
    require(len(data) <= limit, 'Input exceeds inspection budget')
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--hkx')
    mode.add_argument('--rdata')
    args = parser.parse_args()
    try:
        report = (inspect_hkx(read_bounded(args.hkx, MAX_HKX)) if args.hkx else
                  inspect_rdata(read_bounded(args.rdata, RDATA_SIZE)))
        print(json.dumps(report, indent=2))
    except (ValueError, OSError) as error:
        parser.exit(2, str(error) + '\n')

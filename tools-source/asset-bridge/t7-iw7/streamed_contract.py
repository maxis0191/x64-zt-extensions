"""Explicit selected-XPAK request/provenance contract; no stock or engine IO."""
import hashlib
import re
from boot_contract import require, safe_name

REQUEST_SCHEMA = 'iw7.t7-iw7-selected-streamed-request/1'
EXPORT_SCHEMA = 'iw7.t7-iw7-selected-streamed-export/1'
PROFILE = 'selected-streamed-rigid-one-lod'
GEOMETRY_PROFILE = 't7-iw7-selected-streamed-static-v1'
OPTION = '-t7-iw7-model-streamed-v1'
REQUEST_FIELDS = {'schema', 'target', 'profile', 'zone', 'model', 'lod', 'xpak_key', 'packages'}
PACKAGE_FIELDS = {'path', 'identity', 'bytes'}
PAYLOAD_FIELDS = {'key_hex', 'source_shared_flags', 'cpu_view_shared_flags', 'source_surface_flags',
                  'opaque_descriptor_words_hex', 'descriptor_field_semantics_verified',
                  'package_path', 'package_identity', 'file_bytes', 'hash_table_offset',
                  'hash_entry_offset', 'payload_offset', 'compressed_bytes', 'packed_entry_size',
                  'indexed_bytes', 'opcodes', 'opaque_header_offsets', 'payload_bytes', 'payload_sha256',
                  'headers_rechecked', 'atomic_snapshot_proven', 'engine_object_writes'}


def hex64(value):
    require(type(value) is str and re.fullmatch(r'[0-9a-f]{16}', value) is not None,
            'Exact lower-case 16-digit hexadecimal uint64 required')
    return value


def validate_request(value):
    require(type(value) is dict and set(value) == REQUEST_FIELDS, 'Exact selected-streamed request fields required')
    require(value['schema'] == REQUEST_SCHEMA and value['target'] == 'iw7' and value['profile'] == PROFILE,
            'Explicit selected-streamed profile required')
    safe_name(value['zone'], zone=True)
    safe_name(value['model'])
    require(type(value['lod']) is int and 0 <= value['lod'] <= 5, 'Canonical selected-streamed LOD required')
    hex64(value['xpak_key'])
    packages = value['packages']
    require(type(packages) is list and 1 <= len(packages) <= 8, 'Explicit 1..8 selected packages required')
    paths, identities = set(), set()
    for package in packages:
        require(type(package) is dict and set(package) == PACKAGE_FIELDS, 'Exact selected package fields required')
        path = package['path']
        require(type(path) is str and re.fullmatch(r'zone/[A-Za-z0-9_][A-Za-z0-9_-]*\.xpak', path) is not None,
                'Flat .xpak in the private zone directory required')
        safe_name(path)
        safe_name(path[5:-5], zone=True)
        identity = package['identity']
        require(type(identity) is str and re.fullmatch(r'[0-9A-F]{8}:[0-9A-F]{16}', identity) is not None,
                'Exact retained H1 file identity required')
        require(type(package['bytes']) is int and 120 <= package['bytes'] <= 16 * 1024**3,
                'Bounded selected package byte metadata required')
        require(path not in paths and identity not in identities, 'Duplicate selected package path/identity')
        paths.add(path); identities.add(identity)
    return {**value, 'packages': [dict(p) for p in packages]}


def root_key(value):
    value = validate_request(value)
    rows = [GEOMETRY_PROFILE, value['zone'], value['model'], str(value['lod']), value['xpak_key']]
    for package in value['packages']:
        rows += [package['path'], package['identity'], str(package['bytes'])]
    return 't7_iw7_streamed_' + hashlib.sha256('\n'.join(rows).encode('ascii')).hexdigest()


def command_review(value, request_path=None):
    value = validate_request(value)
    if request_path is not None:
        safe_name(request_path)
        require(re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_-]*\.json', request_path) is not None,
                'One flat pinned request JSON in the private working directory required')
        safe_name(request_path[:-5], zone=True)
    return {'schema': 'iw7.t7-iw7-selected-streamed-command-review/1',
            'proposed_arguments': None if request_path is None else
                [OPTION, value['zone'], value['model'], str(value['lod']), request_path],
            'request_file_required': True, 'private_output_root_key': root_key(value),
            'source_engine': 'BlackOps3_UnrankedDedicatedServer.exe', 'expected_source_mode': 't7',
            'xpak_payload_files_allowed': [p['path'] for p in value['packages']],
            'zonetool_global_xpak_reads_allowed': False,
            'stock_access_performed': False, 'native_go': False, 'native_executed': False, 'ready': False}


def validate_payload(value, request, surface_count):
    request = validate_request(request)
    require(type(value) is dict and set(value) == PAYLOAD_FIELDS, 'Exact selected mesh payload provenance required')
    require(hex64(value['key_hex']) == request['xpak_key'], 'Payload key differs from observed selection')
    require(type(value['source_shared_flags']) is int and value['source_shared_flags'] == 9 and
            type(value['cpu_view_shared_flags']) is int and value['cpu_view_shared_flags'] == 8,
            'Raw flags 9 and distinct owned CPU routing flags 8 required')
    flags = value['source_surface_flags']
    require(type(flags) is list and len(flags) == surface_count and
            all(type(f) is int and 0 <= f <= 65535 and not f & 2 for f in flags),
            'Exactly N ordered raw rigid surface flags required')
    opaque = value['opaque_descriptor_words_hex']
    require(type(opaque) is list and len(opaque) == 3, 'Exactly three opaque descriptor words required')
    for word in opaque: hex64(word)
    require(value['descriptor_field_semantics_verified'] is False, 'Engine descriptor semantics remain unproved')
    matches = [p for p in request['packages'] if p['path'] == value['package_path'] and
               p['identity'] == value['package_identity'] and p['bytes'] == value['file_bytes']]
    require(len(matches) == 1 and type(value['file_bytes']) is int,
            'Payload must come from exactly one admitted package identity and byte size')
    file_bytes = value['file_bytes']
    for field in ('hash_table_offset', 'hash_entry_offset', 'payload_offset', 'compressed_bytes',
                  'packed_entry_size', 'indexed_bytes', 'payload_bytes'):
        require(type(value[field]) is int and 0 <= value[field] <= 2**64 - 1, 'Exact unsigned payload scalar required')
    require(120 <= value['hash_table_offset'] <= value['hash_entry_offset'] <= file_bytes - 24,
            'Selected hash entry range differs')
    require((value['hash_entry_offset'] - value['hash_table_offset']) % 24 == 0,
            'Selected hash entry must preserve the 24-byte record alignment')
    require(120 <= value['payload_offset'] <= file_bytes and
            1 <= value['compressed_bytes'] <= 256 * 1024 and
            value['compressed_bytes'] <= file_bytes - value['payload_offset'], 'Selected encoded extent outside bounds')
    require(value['packed_entry_size'] & ((1 << 56) - 1) == value['compressed_bytes'],
            'Packed entry extent differs from selected reader')
    require(24 <= value['indexed_bytes'] <= 8 * 1024**2, 'Bounded observed index reads required')
    require(value['payload_bytes'] == 18624, 'Exactly 18,624 decoded bytes required')
    require(type(value['payload_sha256']) is str and re.fullmatch(r'[0-9a-f]{64}', value['payload_sha256']) is not None,
            'Exact owned payload digest required')
    groups = value['opaque_header_offsets']
    require(type(groups) is list and 1 <= len(groups) <= 128 and
            all(type(v) is int and 0 <= v <= 2**32 - 1 for v in groups), 'Opaque command-header offsets required')
    opcodes = value['opcodes']
    require(type(opcodes) is list and len(groups) <= len(opcodes) <= 30 * len(groups) and
            all(type(v) is int and v in (0, 3) for v in opcodes), 'Only observed raw/LZ4 commands required')
    require(value['headers_rechecked'] is True and value['atomic_snapshot_proven'] is False and
            value['engine_object_writes'] is False, 'Rechecked headers do not prove atomic ownership or allow engine writes')
    return value

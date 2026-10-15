"""Pure reader for Native60's generated private-pair report and raw byte pins.

Source contract: iw7-mod-components 5fbc198395fe67da75c8e927dbcf587cfbab72ae,
ops/raygun/prepare_iw7_clone.py. This is not its retail capture-manifest reader.
No I/O, producer import, native body schema, parser, arena or builder authority.
"""
import hashlib
import json
import math
import re

__all__ = ('validate_private_pair_report', 'verify_private_pair_bytes')

_REPORT_CAP = 65536
_DEFINITION_CAP = 2097152
_HASH = re.compile(r'[0-9a-f]{64}\Z')
_WEAPON_PATH = 'weapons/sdk_shredder_clone_zm.json'
_ATTACHMENT_PATH = 'attachments/sdk_shredder_clone_pap_zm.json'
_CSV_PATH = 'zone_source/sdk_shredder_clone_zm.csv'
_CSV = b'weapon,sdk_shredder_clone_zm\nattachment,sdk_shredder_clone_pap_zm\n'
_CSV_HASH = 'f539cb31e182b7648cac4eb4da369e344d0a8da1a877c4fbed1dc23ef105f2c8'
_PATH_CAPS = {_WEAPON_PATH: _DEFINITION_CAP, _ATTACHMENT_PATH: _DEFINITION_CAP, _CSV_PATH: len(_CSV)}
_FALSE_FLAGS = (
    'bo3_assets_authenticated', 'external_name_driven_gameplay_verified', 'native_parser_verified',
    'ff_built', 'roundtrip_verified', 'runtime_abi_verified', 'lifetime_verified', 'weapon_granted',
    'projectile_damage_verified', 'physics_qualified', 'retail_pap_transaction_verified', 'gameplay_accepted', 'ready',
)
_TEXT = {
    'schema': 'iw7.neutral-weapon-clone/1', 'profile': 'iw7-shredder-neutral-1-0',
    'weapon': 'sdk_shredder_clone_zm', 'pap_attachment': 'sdk_shredder_clone_pap_zm',
    'source_weapon': 'iw7_shredder_zm', 'source_pap_attachment': 'shredderpap1',
    'upgraded_engine_variant': 'sdk_shredder_clone_zm+sdk_shredder_clone_pap_zm',
    'source_layout_pin': 'fab935826c898806855376662a8a03317b3ad8f1',
    'external_name_driven_gameplay': 'unverified: private names do not inherit Shredder GSC callbacks',
    'visuals': 'unchanged IW7 references; dependency bodies not captured',
}
_SLOTS = ('attachments', 'attachments2', 'attachments3', 'attachments4', 'attachments5', 'attachments6')
_KEYS = {*_TEXT, *_FALSE_FLAGS, 'pap_attachment_slot', 'observed_base_type', 'observed_pap_type',
         'source_enum_map', 'json_mechanics_fields_preserved', 'input_sha256', 'files'}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _hash_string(value):
    return type(value) is str and _HASH.fullmatch(value) is not None


def _raw_pin(raw, expected_bytes, expected_sha256, cap):
    _require(type(raw) is bytes, 'Immutable original bytes required')
    _require(type(expected_bytes) is int and 0 < expected_bytes <= cap,
             'Positive bounded integer byte length required')
    _require(0 < len(raw) <= cap and len(raw) == expected_bytes, 'Raw byte length differs or exceeds cap')
    _require(_hash_string(expected_sha256), 'Canonical external SHA256 required')
    _require(hashlib.sha256(raw).hexdigest() == expected_sha256, 'Raw SHA256 differs')


def _unique_pairs(items):
    result = {}
    for key, value in items:
        _require(key not in result, 'Duplicate JSON key')
        result[key] = value
    return result


def _invalid_constant(_value):
    raise ValueError('Nonfinite JSON constant refused')


def _tree_bounds(value):
    pending = [(value, 0)]
    nodes = 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        _require(nodes <= 32768 and depth <= 64, 'Report JSON node/depth bound exceeded')
        if type(item) is dict:
            for key in item:
                key.encode('utf-8', errors='strict')
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            _require(len(item) <= 8192, 'Report JSON per-array bound exceeded')
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            item.encode('utf-8', errors='strict')
        elif type(item) is float:
            _require(math.isfinite(item), 'Finite report JSON number required')


def _closed_object(value, keys, message):
    _require(type(value) is dict and set(value) == set(keys), message)


def validate_private_pair_report(raw_report: bytes, expected_bytes: int, expected_sha256: str) -> dict:
    """Return ordinary decoded report data after external raw pin/schema checks.

    The returned dict and its three file rows carry no authority. A later byte
    check must use verify_private_pair_bytes with the ORIGINAL bytes and pin.
    """
    _raw_pin(raw_report, expected_bytes, expected_sha256, _REPORT_CAP)
    try:
        report = json.loads(raw_report.decode('utf-8', errors='strict'),
                            object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant)
        _tree_bounds(report)
    except (UnicodeError, RecursionError, json.JSONDecodeError) as error:
        raise ValueError('Strict bounded UTF-8 report JSON required') from error
    _closed_object(report, _KEYS, 'Closed thirty-key generated private-pair report required')
    for key, expected in _TEXT.items():
        _require(type(report[key]) is str and report[key] == expected, 'Fixed private report text differs: ' + key)
    _require(type(report['pap_attachment_slot']) is str and report['pap_attachment_slot'] in _SLOTS,
             'One exact producer attachment slot required')
    for key, expected in (('observed_base_type', 1), ('observed_pap_type', 0)):
        _require(type(report[key]) is int and report[key] == expected, 'Uncoerced neutral integer profile required')
    _require(report['json_mechanics_fields_preserved'] is True, 'Literal mechanics-preserved boolean required')
    _require(all(report[key] is False for key in _FALSE_FLAGS), 'All thirteen qualification flags must remain false')
    enums = report['source_enum_map']
    _closed_object(enums, ('base', 'pap'), 'Closed Source enum map required')
    _require(enums == {'base': 'WEAPTYPE_BULLET', 'pap': 'WEAPTYPE_NONE'}, 'Source enum labels differ')
    provenance = report['input_sha256']
    _closed_object(provenance, ('manifest', 'weapon', 'pap'), 'Closed input hash metadata required')
    _require(all(_hash_string(value) for value in provenance.values()), 'Canonical input provenance hashes required')
    rows = report['files']
    _require(type(rows) is list and len(rows) == 3, 'Exactly three generated file rows required')
    seen = set()
    for row in rows:
        _closed_object(row, ('path', 'bytes', 'sha256'), 'Closed generated file row required')
        path = row['path']
        _require(type(path) is str and path in _PATH_CAPS and path not in seen, 'Exact unique generated path required')
        seen.add(path)
        _require(type(row['bytes']) is int and 0 < row['bytes'] <= _PATH_CAPS[path], 'Bounded file byte length required')
        _require(_hash_string(row['sha256']), 'Canonical generated file hash required')
        if path == _CSV_PATH:
            _require(row['bytes'] == len(_CSV) and row['sha256'] == _CSV_HASH, 'Exact two-row CSV pin required')
    return report


def verify_private_pair_bytes(raw_report: bytes, expected_bytes: int, expected_sha256: str,
                              weapon_raw: bytes, attachment_raw: bytes, csv_raw: bytes) -> None:
    """Revalidate original raw report/pin, then check the three raw buffers.

    Does NOT decode definition bodies, prove physical files/lifetimes, validate
    native shapes, or authorize a parser/arena/zone/builder. Success returns None.
    """
    report = validate_private_pair_report(raw_report, expected_bytes, expected_sha256)
    rows = {row['path']: row for row in report['files']}
    for path, raw in ((_WEAPON_PATH, weapon_raw), (_ATTACHMENT_PATH, attachment_raw), (_CSV_PATH, csv_raw)):
        row = rows[path]
        _raw_pin(raw, row['bytes'], row['sha256'], _PATH_CAPS[path])
    _require(csv_raw == _CSV, 'Exact two-row CSV bytes required')

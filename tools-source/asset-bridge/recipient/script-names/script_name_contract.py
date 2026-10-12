"""Pure validator for the two-key observer; no engine, token substitution or payload read."""
import hashlib
import json
import os
from pathlib import Path
import stat

KEYS = ('scripts/engine/utility', '2626')
LIMIT = 4096
COUNTERS = {'callbacks', 'null_headers', 'null_names', 'named', 'decimal_names', 'unmatched', 'matched'}
ROW = {'identity', 'type', 'content_name', 'database_name', 'compressed_len', 'source_len', 'bytecode_len', 'is_default'}
TOP = {'schema', 'donor_map', 'asset_type', 'token_alias_inferred', 'enumeration', 'targets',
       'payload_bytes_read', 'script_bytes_verified', 'closure_complete', 'ready'}

def require(value, message):
    if not value:
        raise ValueError(message)

def fields(value, expected, label):
    require(type(value) is dict and set(value) == expected, f'Exact {label} fields required')

def number(value, high, label):
    require(type(value) is int and 0 <= value <= high, f'Invalid {label}')

def name(value):
    require(type(value) is str and 1 <= len(value) <= 240 and
            all(0x20 <= ord(c) <= 0x7e for c in value), 'Invalid bounded ASCII name')

def validate(value):
    fields(value, TOP, 'observation')
    require(value['schema'] == 'iw7.recipient-script-names/1' and value['donor_map'] == 'cp_zmb', 'Unknown schema/map')
    require(type(value['asset_type']) is int and value['asset_type'] == 49, 'ScriptFile type required')
    for flag in ('token_alias_inferred', 'script_bytes_verified', 'closure_complete', 'ready'):
        require(value[flag] is False, 'No alias/payload/closure/readiness qualification is permitted')
    require(type(value['payload_bytes_read']) is int and value['payload_bytes_read'] == 0, 'Observer payload reads forbidden')
    counts = value['enumeration']
    fields(counts, COUNTERS, 'counter')
    for key, count in counts.items():
        number(count, LIMIT, key)
    require(counts['callbacks'] == counts['null_headers'] + counts['null_names'] + counts['named'], 'Counter partition differs')
    require(counts['named'] == counts['unmatched'] + counts['matched'], 'Match partition differs')
    require(counts['decimal_names'] <= counts['named'], 'Numeric count exceeds named count')
    require(type(value['targets']) is list and len(value['targets']) == 2, 'Exactly two target rows required')
    identities, matched = {}, 0
    for key, target in zip(KEYS, value['targets']):
        fields(target, {'key', 'enum_occurrences', 'enum', 'direct'}, 'target')
        require(target['key'] == key, 'Exact ordered canonical and numeric keys required')
        number(target['enum_occurrences'], LIMIT, 'enum occurrences')
        require(bool(target['enum_occurrences']) == (target['enum'] is not None), 'Enum presence/count differs')
        matched += target['enum_occurrences']
        for origin in ('enum', 'direct'):
            row = target[origin]
            if row is None:
                continue
            fields(row, ROW, 'identity row')
            number(row['identity'], 4, 'identity ordinal')
            require(row['identity'] > 0 and type(row['type']) is int and row['type'] == 49, 'Invalid identity/type')
            name(row['content_name']); name(row['database_name'])
            if origin == 'enum':
                require(row['content_name'] == key, 'Enum raw name differs from matched key')
            for length in ('compressed_len', 'source_len', 'bytecode_len'):
                number(row[length], 67108864, length)
            require(type(row['is_default']) is bool, 'Default status must be observed boolean')
            signature = {k: v for k, v in row.items() if k != 'identity'}
            require(row['identity'] not in identities or identities[row['identity']] == signature,
                    'One identity has conflicting metadata')
            identities[row['identity']] = signature
    require(matched == counts['matched'], 'Per-key match counts differ')
    require(value['targets'][1]['enum_occurrences'] <= counts['decimal_names'], 'Numeric matches exceed numeric names')
    require(sorted(identities) == list(range(1, len(identities)+1)), 'Identity ordinals must be contiguous')
    return {'enum_callbacks': counts['callbacks'], 'requested_match_occurrences': matched,
            'canonical_matches': value['targets'][0]['enum_occurrences'],
            'numeric_matches': value['targets'][1]['enum_occurrences'],
            'observed_identities': len(identities), 'token_alias_inferred': False,
            'script_bytes_verified': False, 'closure_complete': False, 'ready': False}

def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON field')
        result[key] = value
    return result

def read_observation(path):
    # A single descriptor binds these small output bytes to the digest.
    with Path(path).open('rb', buffering=0) as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= LIMIT, 'Invalid observer output size/type')
        data = stream.read(LIMIT+1)
        after = os.fstat(stream.fileno())
        signature = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        require(len(data) == before.st_size and len(data) <= LIMIT and signature(before) == signature(after),
                'Observer output changed/truncated/exceeded limit')
    value = json.loads(data.decode('utf-8'), object_pairs_hook=unique_pairs)
    return {**validate(value), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

"""Validate bounded catalogue observations; does not certify native execution."""
import json
from boot_contract import require, safe_name

FALSE_FIELDS = ('truncated', 'asset_zone_ownership_verified', 'zonetool_xpak_helper_reads_allowed',
                'engine_io_verified', 'geometry_verified', 'runtime_verified', 'ready')
FIELDS = {'schema', 'requested_zone', 'provenance', 'model_count', 'name_bytes', 'models', *FALSE_FIELDS}


def validate_catalog(value, zone):
    safe_name(zone, zone=True)
    require(type(value) is dict and set(value) == FIELDS, 'Exact catalogue fields required')
    require(value['schema'] == 'iw7.t7-iw7-model-catalog/1' and value['requested_zone'] == zone and
            value['provenance'] == 'observed_during_requested_zone_load', 'Catalogue request/provenance differs')
    require(all(value[k] is False for k in FALSE_FIELDS), 'Catalogue cannot claim completeness beyond its request')
    rows = value['models']
    require(type(rows) is list and len(rows) <= 1024 and type(value['model_count']) is int and
            value['model_count'] == len(rows), 'Model count exceeds bound or differs')
    names = []
    for row in rows:
        require(type(row) is dict and set(row) == {'name', 'reference', 'resolved_nondefault', 'counts'}, 'Exact row required')
        name = row['name']
        require(type(name) is str and 1 <= len(name) <= 255 and
                all(0x20 <= ord(c) < 0x7f for c in name), 'Bounded observed ASCII name required')
        require(type(row['reference']) is bool and row['reference'] == name.startswith(',') and
                type(row['resolved_nondefault']) is bool, 'Exact reference/resolution status required')
        names.append(name)
        if row['resolved_nondefault']:
            require(not row['reference'], 'Referenced alias cannot be resolved donor')
            counts = row['counts']
            require(type(counts) is dict and set(counts) == {'bones', 'roots', 'cosmetic_bones', 'lods'}, 'Header counts only')
            require(all(type(v) is int and 0 <= v <= (65535 if k == 'cosmetic_bones' else 255)
                        for k, v in counts.items()), 'Header count width differs')
        else:
            require(row['counts'] is None, 'Unresolved model cannot claim counts')
    require(names == sorted(set(names)), 'Names must be sorted, unique and unmodified')
    require(type(value['name_bytes']) is int and value['name_bytes'] == sum(len(n)+1 for n in names) and
            value['name_bytes'] <= 256*1024, 'Name buffer byte count differs')
    require(len((json.dumps(value, ensure_ascii=False, separators=(',', ':'))+'\n').encode()) <= 512*1024,
            'Catalogue publication exceeds bound')
    return value

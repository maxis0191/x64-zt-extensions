"""Unused finite weapon-name module and text reader; never builds, loads or activates."""
from pathlib import Path
import re
import prepare_cli

HERE = Path(__file__).resolve().parent
SCHEMA = 'iw7.t7-weapon-name-observation/1'
PREFIX = '[T7_WEAPON_NAMES] schema=' + SCHEMA + ' '
MAX_CALLS, NAME_BYTES, MAX_LINES, MAX_LINE_BYTES, MAX_BYTES, COMBINED_MAX_BYTES = 8, 96, 19, 512, 8192, 16384


def wire_unused_module(text):
    """Append support after unchanged C2 helpers. Add no call-site or activation."""
    if type(text) is not str or '\r' in text or 'weapon_names_' in text:
        raise ValueError('Fresh LF-only CLI required')
    if text.count('namespace zonetool::t7\n{') != 1:
        raise ValueError('Exact single T7 namespace required')
    c2 = (HERE / 'native_catalog_add_observation.inc').read_text(encoding='utf-8')
    anchor = '\n'.join('\t' + line if line else '' for line in c2.splitlines())
    module = (HERE / 'native_weapon_name_observation.inc').read_text(encoding='utf-8')
    addition = '\n\n' + '\n'.join('\t' + line if line else '' for line in module.splitlines())
    return prepare_cli.helper.once(text, anchor, anchor + addition)


PATTERNS = (
    r'kind=enabled scope=historical_f23_startup weapon_presence=unknown',
    r'kind=overflow',
    r'kind=enter call=(?P<call>[0-7]) type=(?P<type>23|24|25|26) '
    r'read=(?P<read>read|prefix|null|unreadable|getter_exception) length=(?P<length>\d+) '
    r'nul=(?P<nul>[01]) reference=(?P<reference>[01]) name_hex=(?P<name_hex>-|[0-9a-f]{2,192}) '
    r'caller=(?P<caller>[0-9A-Fa-f]{16}) header_present=(?P<header_present>[01])',
    r'kind=return call=(?P<call>[0-7]) type=(?P<type>23|24|25|26) result_present=(?P<result_present>[01])',
    r'kind=finished entered=(?P<entered>[0-8]) returned=(?P<returned>[0-8]) '
    r'overflow=(?P<overflow>[01]) write_failed=(?P<write_failed>[01])',
)


def split_observation(text):
    """Strip only our marker. Missing/refused/bounded output never proves absence."""
    if type(text) is not str or len(text.encode('ascii')) > COMBINED_MAX_BYTES:
        raise ValueError('Bounded ASCII combined trace required')
    legacy, rows, sequences, entries, returned = [], [], set(), {}, {}
    enabled = overflow = False
    finished = None
    late = False
    byte_count = 0
    for line in text.splitlines(keepends=True):
        if not line.startswith('[T7_WEAPON_NAMES]'):
            legacy.append(line)
            continue
        if not line.endswith('\n') or len(line) > MAX_LINE_BYTES:
            raise ValueError('Complete bounded weapon-name line required')
        row = line.removesuffix('\n').removesuffix('\r')
        head = re.fullmatch(re.escape(PREFIX) + r'seq=(\d+) tid=(\d+) (.+)', row)
        if not head:
            raise ValueError('Exact weapon-name schema required')
        seq, tid = map(int, head.groups()[:2])
        if not 0 <= seq < MAX_LINES or seq in sequences or not 0 < tid <= 0xffffffff:
            raise ValueError('Sequence/thread outside bounds or duplicated')
        sequences.add(seq)
        body = head[3]
        match = next((m for pattern in PATTERNS if (m := re.fullmatch(pattern, body))), None)
        if not match:
            raise ValueError('Unknown weapon-name record')
        kind = body.split(' ', 1)[0].removeprefix('kind=')
        fields = match.groupdict()
        for key, value in tuple(fields.items()):
            if key not in ('read', 'name_hex', 'caller'):
                fields[key] = int(value)
        if kind == 'enabled':
            if enabled or rows:
                raise ValueError('Single leading enable required')
            enabled = True
        elif not enabled:
            raise ValueError('Weapon record before enable')
        elif kind == 'overflow':
            if overflow:
                raise ValueError('Duplicate overflow')
            late |= finished is not None
            overflow = True
        elif kind == 'enter':
            if fields['call'] in entries:
                raise ValueError('Duplicate call entry')
            late |= finished is not None
            raw = b'' if fields['name_hex'] == '-' else bytes.fromhex(fields['name_hex'])
            if len(raw) != fields['length'] or b'\0' in raw or fields['length'] > NAME_BYTES:
                raise ValueError('Name length/encoding differs')
            if fields['read'] == 'read':
                if not fields['nul'] or len(raw) >= NAME_BYTES:
                    raise ValueError('Complete name requires a NUL before the cap')
            elif fields['read'] == 'prefix':
                if fields['nul'] or len(raw) != NAME_BYTES:
                    raise ValueError('Prefix must fill the entire name cap')
            elif raw or fields['nul'] or fields['reference']:
                raise ValueError('Refused name cannot retain bytes/flags')
            if fields['reference'] != int(bool(raw) and raw.startswith(b',')):
                raise ValueError('Reference prefix differs')
            entries[fields['call']] = dict(fields, tid=tid)
        elif kind == 'return':
            late |= finished is not None
            entry = entries.get(fields['call'])
            if entry is None or fields['call'] in returned or (entry['tid'], entry['type']) != (tid, fields['type']):
                raise ValueError('Orphan/duplicate/mismatched return')
            returned[fields['call']] = fields
        elif kind == 'finished':
            if finished is not None or fields['returned'] > fields['entered'] or fields['entered'] < len(entries) or \
                    fields['overflow'] != int(overflow):
                raise ValueError('Finish inventory differs')
            finished = fields
        byte_count += len(line)
        if byte_count > MAX_BYTES or len(rows) >= MAX_LINES:
            raise ValueError('Weapon-name trace bound exceeded')
        rows.append(dict(kind=kind, seq=seq, tid=tid, **fields))
    if not rows:
        outcome = 'Absent'
    elif finished is None or late or overflow or finished['write_failed'] or \
            finished['entered'] != len(entries) or \
            len(returned) != len(entries) or finished['returned'] != len(returned) or \
            any(e['read'] != 'read' or not e['length'] for e in entries.values()):
        outcome = 'Incomplete'
    else:
        outcome = 'NamesObserved' if entries else 'NoNamesObserved'
    return ''.join(legacy), {
        'schema': SCHEMA, 'outcome': outcome, 'records': rows,
        'weapon_types_seen': sorted({e['type'] for e in entries.values()}),
        'asset_availability_verified': False, 'asset_zone_ownership_verified': False,
        'default_resolution_verified': False, 'weapon_role_bindings_verified': False,
        'runtime_compatible': False, 'ready': False,
    }

"""Pure fab935 private-pair input dialect, demand and alignment preflight.

No native import, I/O, arena, parser or builder. A successful check returns None,
never permission to parse different bytes or use a different arena/order/base.
"""
import json
import math
import struct

from native_body_schema import SCHEMA as _SCHEMA
from neutral_pair_inputs import (verify_private_pair_bytes, validate_private_pair_report,
                                 _unique_pairs, _invalid_constant, _tree_bounds)

__all__ = ('validate_private_pair_bodies',)
_SIZE_MAX = (1 << 64) - 1
_ARRAY_CELLS = 8192
_SLOTS = ('attachments', 'attachments2', 'attachments3', 'attachments4', 'attachments5', 'attachments6')


def _need(condition, path, reason):
    if not condition:
        # Paths are generated Source labels plus bounded numeric indices only.
        raise ValueError(path + ': ' + reason)


def _closed(value, keys, path):
    _need(type(value) is dict and set(value) == set(keys), path, 'exact closed object keys required')


def _list(value, size, path):
    _need(type(value) is list and len(value) == size, path, 'exact array cardinality required')


def _layout(ty):
    value = _SCHEMA['types'].get(ty)
    _need(value is not None, 'Source.' + ty, 'unknown type/layout')
    return value


def _scalar(value, ty, path):
    desc = _layout(ty)
    kind = desc['kind']
    if kind == 'bool':
        _need(type(value) is bool, path, 'literal boolean required')
    elif kind in ('int', 'enum'):
        _need(type(value) is int and desc['min'] <= value <= desc['max'], path, 'uncoerced target integer range required')
        if kind == 'enum':
            if desc.get('semantic_domain_unknown'):
                _need(ty == 'WeaponChargeType' and desc.get('storage_domain_only') is True,
                      path, 'unknown semantic enum domain refused')
            else:
                _need(value in desc['values'], path, 'declared nonsentinel enum value required')
    elif kind in ('float', 'double'):
        _need(type(value) in (int, float), path, 'uncoerced numeric value required')
        try:
            number = float(value)
            converted = struct.unpack('<f', struct.pack('<f', number))[0] if kind == 'float' else number
        except (OverflowError, struct.error):
            raise ValueError(path + ': floating target overflow') from None
        _need(math.isfinite(number) and math.isfinite(converted), path, 'finite floating target required')
        _need(number == 0 or converted != 0, path, 'nonzero floating target underflow refused')
    else:
        raise ValueError(path + ': unsupported scalar target ' + ty)


def _text(value, path, nullable=True, empty=False):
    if value is None and nullable: return
    _need(type(value) is str, path, 'string required')
    try: encoded = value.encode('utf-8', errors='strict')
    except UnicodeError: raise ValueError(path + ': valid UTF-8 scalar string required') from None
    _need(b'\0' not in encoded and (empty or len(encoded) > 0), path, 'NUL-free supported string shape required')


class _Trace:
    """Ordinary test diagnostics, never an arena owner or an authority token."""
    def __init__(self, alignment=True):
        self.offset = 0
        self.cells = 0
        self.script_entries = 0
        self.string_bytes = 0
        self.events = []
        self.alignment = alignment

    def allocate(self, ty, count, path, *, size=None, cells=False, effective=None):
        desc = _layout(ty)
        unit = desc['size'] if size is None else size
        alignment = max(desc['align'], _layout(effective)['align'] if effective else 1)
        _need(type(count) is int and 0 <= count <= _SIZE_MAX, path, 'bounded allocation count required')
        _need(type(unit) is int and unit > 0 and type(alignment) is int and alignment > 0,
              path, 'known positive Source size/alignment required')
        if count == 0: return  # Actual legacy allocator returns nullptr here.
        _need(count <= _SIZE_MAX // unit, path, 'allocation multiplication overflow')
        total = unit * count
        _need(self.offset <= _SIZE_MAX - total, path, 'allocation addition overflow')
        if self.alignment:
            _need(self.offset % alignment == 0, path, 'legacy cursor misalignment for ' + ty)
        if cells:
            _need(self.cells <= _ARRAY_CELLS - count, path, 'two-root aggregate native array-cell bound exceeded')
            self.cells += count
        self.events.append((path, ty, self.offset, total, alignment))
        self.offset += total

    def string(self, value, path):
        size = len(value.encode('utf-8')) + 1
        self.allocate('char', size, path)
        self.string_bytes += size
        _need(self.string_bytes <= 2 * 2097152 + 65536, path, 'two-root string storage bound exceeded')

    def script(self, path):
        self.script_entries += 1
        _need(self.script_entries <= 65536, path, 'two-root script-map entry bound exceeded')


def _cstring(value, path, trace, *, empty=False, script=False, nullable=True):
    _text(value, path, nullable=nullable, empty=empty)
    if value is not None:
        trace.string(value, path)
        if script: trace.script(path)


def _asset(value, ty, path, trace, *, full=False):
    _text(value, path)
    if value is not None:
        trace.allocate(ty, 1, path, size=None if full else 8)
        trace.string(value, path + '.name')


def _fx(value, path, trace):
    if value is None: return
    _closed(value, ('type', 'fx'), path)
    _need(type(value['type']) is int and value['type'] in (0, 1), path + '.type', 'FX tag0 or1 required')
    _text(value['fx'], path + '.fx', nullable=False)
    # The char allocation is then used through u.fx->name, a typed header.
    trace.allocate('char', 1, path, size=8, effective='FxEffectDef')
    trace.string(value['fx'], path + '.fx')


def _graphs(value, path):
    _list(value, 2, path)
    counts = []
    for i, graph in enumerate(value):
        p = path + '[' + str(i) + ']'
        _need(graph is None or type(graph) is list and 0 < len(graph) <= 65535, p, 'null or positive uint16 graph required')
        counts.append(0 if graph is None else len(graph))
        if graph is not None:
            for j, knot in enumerate(graph):
                k = p + '[' + str(j) + ']'
                _list(knot, 2, k)
                for cell in knot: _scalar(cell, 'float', k)
    return counts


def _shared_groups(ty, data, path):
    groups = {}
    for rule in _SCHEMA['structures'][ty]['ops']:
        if type(rule.get('count')) is str:
            groups.setdefault(rule['count'], []).append(rule)
    for rules in groups.values():
        values = [data[r['key']] for r in rules]
        nulls = [v is None for v in values]
        _need(all(nulls) or not any(nulls), path, 'shared count requires one explicit null policy')
        if not all(nulls):
            _need(all(type(v) is list and len(v) > 0 for v in values), path, 'positive dynamic arrays required')
            _need(len({len(v) for v in values}) == 1, path, 'shared count lengths differ')
            for rule in rules: _scalar(len(values[0]), rule['count_type'], path + '.' + rule['key'])


def _array(rule, data, path, trace):
    value, kind, ty = data[rule['key']], rule['op'], rule['type']
    desc = _layout(ty)
    inline = desc['kind'] == 'array'
    count = rule['count'] if type(rule['count']) is int else (0 if value is None else len(value))
    if value is None:
        _need(not inline, path, 'inline arrays cannot be null/defaulted')
        return
    _list(value, count, path)
    _need(count > 0, path, 'zero pointer arrays normalize to null and are unsupported')
    elem = desc['element']
    if inline:
        _need(desc['extents'] == [count], path, 'native inline extent differs')
    else:
        trace.allocate(elem, count, path, cells=True)
    for i, item in enumerate(value):
        p = path + '[' + str(i) + ']'
        if kind.startswith('ASSET'):
            _asset(item, _layout(elem)['element'], p, trace)
        elif kind.startswith('SCRIPT_STRING'):
            _cstring(item, p, trace, script=True)
        elif kind.startswith('FXCOMBINED'):
            _fx(item, p, trace)
        elif kind == 'STRING_ARR':
            _cstring(item, p, trace)
        else:
            _scalar(item, elem, p)


def _manual(handler, data, path, trace, parent):
    kind, *args = handler
    if kind == 'object':
        key, ty = args
        _walk(ty, data[key], path + '.' + key, trace, parent)
    elif kind == 'entries':
        key, ty = args
        value, p = data[key], path + '.' + key
        if value is not None:
            _need(type(value) is list and 0 < len(value) <= 65535, p, 'positive outer uint16 cast length required')
            trace.allocate(ty, len(value), p, cells=True)
            for i, item in enumerate(value): _walk(ty, item, p + '[' + str(i) + ']', trace, parent)
    elif kind == 'graphs':
        counts = _graphs(data['accuracyGraphKnots'], path + '.accuracyGraphKnots')
        for i, count in enumerate(counts): trace.allocate('vec2_t', count, path + '.accuracyGraphKnots[' + str(i) + ']', cells=True)
    elif kind == 'definition':
        trace.allocate('WeaponDef', 1, path + '.weapDef')
        _walk('WeaponDef', data['weapDef'], path + '.weapDef', trace, data)
    elif kind == 'original_graphs':
        counts = _graphs(parent['accuracyGraphKnots'], path + '.parent.accuracyGraphKnots')
        names, original_counts = data['accuracyGraphName'], data['originalAccuracyGraphKnotCount']
        _list(names, 2, path + '.accuracyGraphName')
        _list(original_counts, 2, path + '.originalAccuracyGraphKnotCount')
        highest = 2 if counts[1] else 1 if counts[0] else 0
        graphs = data.get('originalAccuracyGraphKnots')
        if highest: _list(graphs, highest, path + '.originalAccuracyGraphKnots')
        for i, count in enumerate(counts):
            p = path + '.originalAccuracyGraphKnots[' + str(i) + ']'
            # Native tests JSON-value empty(), not std::string/Python emptiness:
            # even "" is a nonempty JSON value and duplicates its NUL byte.
            nullable = count == 0 and type(original_counts[i]) is int and original_counts[i] == 0
            _text(names[i], path + '.accuracyGraphName', nullable=nullable, empty=True)
            if names[i] is not None: trace.string(names[i], path + '.accuracyGraphName[' + str(i) + ']')
            trace.allocate('vec2_t', count, p, cells=True)
            if i < highest:
                if not count: _need(graphs[i] is None, p, 'zero original graph hole must be null')
                else:
                    _list(graphs[i], count, p)
                    for knot in graphs[i]:
                        _list(knot, 2, p)
                        for cell in knot: _scalar(cell, 'float', p)
            _scalar(original_counts[i], 'unsigned short', path + '.originalAccuracyGraphKnotCount')
            _need(original_counts[i] == count, p, 'original count must equal parent allocation count')
    elif kind == 'overrides':
        entries = (('animOverrides', 'AnimOverride'), ('sfxOverrides', 'SFXOverride'), ('vfxOverrides', 'VFXOverride'))
        for key, _ in entries: _list(data[key], 21, path + '.' + key)
        # Native parser interleaves the three types within each index.
        for i in range(21):
            for key, ty in entries: _walk(ty, data[key][i], path + '.' + key + '[' + str(i) + ']', trace, parent)
    elif kind == 'unk_material':
        _asset(data['unk0']['material'], 'Material', path + '.unk0.material', trace, full=True)
    elif kind == 'internal_script':
        trace.script(path + '.internalName')  # Reuses szInternalName, no second strdup.
    else:
        raise ValueError(path + ': unknown manual Source handler')


def _walk(ty, data, path, trace, parent=None):
    schema = _SCHEMA['structures'][ty]
    keys = set(schema['keys'])
    if ty == 'WeaponDef':
        counts = _graphs(parent['accuracyGraphKnots'], path + '.parent.accuracyGraphKnots')
        if not any(counts): keys.remove('originalAccuracyGraphKnots')
    _closed(data, keys, path)
    if ty == 'WeaponDef':
        unknown = [r['key'][5:] for r in schema['ops'] if r.get('key', '').startswith('unk0.')]
        _closed(data['unk0'], ['material', *unknown], path + '.unk0')
    _shared_groups(ty, data, path)
    for rule in schema['ops']:
        if rule['op'] == 'MANUAL':
            _manual(rule['handler'], data, path, trace, parent)
            continue
        key, kind, native = rule['key'], rule['op'], rule['type']
        p = path + '.' + key
        value = data['unk0'][key[5:]] if key.startswith('unk0.') else data[key]
        if kind in ('FIELD', 'FIELD_RENAME'): _scalar(value, native, p)
        elif kind == 'STRING': _cstring(value, p, trace, empty=rule['flavor'] == 'weapon')
        elif kind == 'SCRIPT_STRING': _cstring(value, p, trace, script=True)
        elif kind == 'ASSET': _asset(value, _layout(native)['element'], p, trace)
        elif kind == 'FXCOMBINED': _fx(value, p, trace)
        elif kind == 'OPTIONAL':
            if value is not None:
                target = _layout(native)['element']
                trace.allocate(target, 1, p)
                _walk(target, value, p, trace, parent)
        elif 'ARR' in kind: _array(rule, data, p, trace)
        else: raise ValueError(p + ': unknown generated Source operation')


def _inspect(weapon, attachment, *, alignment=True):
    trace = _Trace(alignment)
    trace.allocate('WeaponCompleteDef', 1, 'weapon')
    _walk('WeaponCompleteDef', weapon, 'weapon', trace)
    trace.allocate('WeaponAttachment', 1, 'attachment')
    _walk('WeaponAttachment', attachment, 'attachment', trace)
    return trace


def _decode(raw, path):
    try:
        data = json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=_unique_pairs,
                          parse_constant=_invalid_constant, parse_float=_float_literal)
        _tree_bounds(data)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ValueError(path + ': strict bounded UTF-8 JSON required') from error
    # Tree bounds check UTF-8; also forbid keys containing native C-string NUL.
    stack = [data]
    while stack:
        value = stack.pop()
        if type(value) is dict:
            _need(all('\0' not in key for key in value), path, 'NUL-free JSON keys required')
            stack.extend(value.values())
        elif type(value) is list: stack.extend(value)
        elif type(value) is str: _need('\0' not in value, path, 'NUL-free JSON strings required')
    return data


def _float_literal(token):
    value = float(token)
    mantissa = token.lower().split('e', 1)[0]
    _need(math.isfinite(value), 'body.number', 'finite JSON floating literal required')
    _need(value != 0 or not any(c in '123456789' for c in mantissa),
          'body.number', 'nonzero JSON floating literal underflow refused')
    return value


def validate_private_pair_bodies(raw_report: bytes, expected_bytes: int, expected_sha256: str,
                                 weapon_raw: bytes, attachment_raw: bytes, csv_raw: bytes) -> None:
    """Validate original byte bindings, full dialect and no-padding cursor trace.

    The single fresh arena model uses weapon then attachment. Actual base address,
    arena capacity, FILE identity/routing, ownership and runtime ABI remain absent.
    Input bytes/report flags remain unchanged. This function opens nothing.
    """
    verify_private_pair_bytes(raw_report, expected_bytes, expected_sha256, weapon_raw, attachment_raw, csv_raw)
    report = validate_private_pair_report(raw_report, expected_bytes, expected_sha256)
    weapon, attachment = _decode(weapon_raw, 'weapon'), _decode(attachment_raw, 'attachment')
    # First check every shape/range/count and demand before alignment can mask a
    # later unsupported field. No native object is constructed in either pass.
    _inspect(weapon, attachment, alignment=False)
    _need(weapon['szInternalName'] == report['weapon'], 'weapon.szInternalName', 'private identity differs')
    _need(attachment['szInternalName'] == report['pap_attachment'], 'attachment.szInternalName', 'private identity differs')
    _need(type(weapon['weapDef']['weapType']) is int and weapon['weapDef']['weapType'] == 1,
          'weapon.weapDef.weapType', 'neutral BULLET1 required')
    _need(type(attachment['weaponType']) is int and attachment['weaponType'] == 0,
          'attachment.weaponType', 'neutral NONE0 required')
    _need(attachment['papAttachment'] is True, 'attachment.papAttachment', 'literal true PAP flag required')
    matches = []
    for key in _SLOTS:
        values = weapon[key]
        for value in values or []:
            if value == report['pap_attachment']: matches.append(key)
            _need(value not in (',' + report['pap_attachment'], report['weapon'], ',' + report['weapon']),
                  'weapon.' + key, 'private identity alias or wrong association')
    _need(matches == [report['pap_attachment_slot']], 'weapon.attachments', 'one private PAP association in declared slot required')
    _inspect(weapon, attachment, alignment=True)

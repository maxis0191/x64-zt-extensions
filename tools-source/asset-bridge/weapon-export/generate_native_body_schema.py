"""Finite, pin-first Source extraction for fab935's two native input parsers.

Only the reviewed C++ text grammar is supported. No compiler, SDK, game body or
producer is imported. Manual operations are bound to exact pinned source sites.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

from generate_definition_readset import functions as dump_functions, MACRO as DUMP_MACRO

PIN = 'fab935826c898806855376662a8a03317b3ad8f1'
PINS = {
    'iw7/assets/weapondef.cpp': 'fc6defc7d4cdad56d3615ff2d13a1c6715f8b6e53dbdc7dd4be25ce4255050b5',
    'iw7/assets/weaponattachment.cpp': '746d520c49f122bc650652da78deed45b091198bb10b30dc48bc6a38c9227e4c',
    'iw7/structs.hpp': '482affaf3641dc5318422c4cef45383923183349ae91d18e9d3ff29699f8a0df',
    'iw7/assets/weapondef.hpp': '3c1f7b2fd4fd5ce7a4919dbabc6a5bf4e1ac1591029a89e29f3cf77c1821d084',
    'iw7/assets/weaponattachment.hpp': 'ce53d8d720236d55e2b174cf40ef5d56158c958f1b0ed885b55fb820d7d825ff',
    'utils/memory.hpp': '9025b835313ee45ba3418e3322210dec3b6d334e504a1dd3b59e9f38e2898f35',
}
CONVERSION_PINS = {
    'deps/premake/json.lua': '07576e7b7123d221f90c1962e4d2ab529af5061f198070af2e7d303082574fdf',
    'src/zonetool/std_include.hpp': '13da341aa6b558a3735bcbe3570772f079bcc2342d586229227aa03668df9425',
    'deps/json/single_include/nlohmann/json.hpp': '53855e4a20d7bc92d9624bf0d83fba8e22d0d9de83f9480bd4895651602fa8cc',
}
JSON_REVISION = '484483acad6d562306efc9b3c6d413404f1b1f8a'
CALL = re.compile(r'^\s*((?:WEAPON|ATTACHMENT)_PARSE_[A-Z_]+|PARSE_ATT|PARSE_UNK0)\(([^\n]*?)\);', re.M)
SIGNATURE = re.compile(r'(?:void|WeaponAttachment\*)\s+(?:(?:weapon_def|weapon_attachment)::)?'
                       r'(parse\w*)\(([^\n]*?)\)\s*\{')
# Ordered direct branches, not inferred from a serializer readset.
MANUAL = {
    'WeaponDef': [(412, 'object', 'overlay', 'ADSOverlay'), (583, 'original_graphs'),
                  (961, 'object', 'rotationParams', 'GrenadeRotationParams'),
                  (963, 'overrides'), (976, 'unk_material')],
    'WeaponCompleteDef': [(1068, 'entries', 'notetrackOverrides', 'NoteTrackToSoundEntry'),
                          (1081, 'entries', 'notetrackSuitEntries', 'NoteTrackToSuitSoundEntry'),
                          (1110, 'graphs'), (1137, 'definition')],
    'WeaponAttachment': [(698, 'internal_script')],
}
MANUAL_KEYS = {
    'WeaponDef': ['overlay', 'rotationParams', 'animOverrides', 'sfxOverrides', 'vfxOverrides',
                  'accuracyGraphName', 'originalAccuracyGraphKnots', 'originalAccuracyGraphKnotCount', 'unk0'],
    'WeaponCompleteDef': ['notetrackOverrides', 'notetrackSuitEntries', 'accuracyGraphKnots', 'weapDef'],
}
MANUAL_BODY_SHA256 = {
    'WeaponDef': '730ad262e28b925be58c71ca560b95ff21aca483cda5c2bb53e1abc467a431f9',
    'WeaponCompleteDef': '28ee98f7acaf34e5b6bb87744b1cbe993714138688ad8fd8c2121aaa00443dd6',
    'WeaponAttachment': '218195b69b9d46a35f364107aabb27aa4e54cec91bfb5521a221fc8d92b9a327',
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def block(text, start):
    depth, end = 1, start
    while depth and end < len(text):
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    require(depth == 0, 'Unclosed finite Source block')
    return text[start:end - 1], end


def integer(expression, names=None):
    """The enum/count grammar: literal, earlier enum name, unary sign and bits."""
    expression = re.sub(r'(?<=\d)[uUlL]+\b', '', expression.strip())
    node = ast.parse(expression, mode='eval').body
    def visit(n):
        if isinstance(n, ast.Constant) and type(n.value) is int:
            return n.value
        if isinstance(n, ast.Name) and n.id in (names or {}):
            return names[n.id]
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd, ast.Invert)):
            v = visit(n.operand)
            return -v if isinstance(n.op, ast.USub) else +v if isinstance(n.op, ast.UAdd) else ~v
        if isinstance(n, ast.BinOp):
            a, b = visit(n.left), visit(n.right)
            if isinstance(n.op, ast.LShift):
                require(0 <= b <= 63, 'Unreviewed enum shift')
                return a << b
            if isinstance(n.op, ast.BitOr): return a | b
            if isinstance(n.op, ast.BitAnd): return a & b
            if isinstance(n.op, ast.Add): return a + b
            if isinstance(n.op, ast.Sub): return a - b
        raise ValueError('Unreviewed integer Source expression: ' + expression)
    return visit(node)


def canonical(text):
    return re.sub(r'\s+', ' ', text.replace(' *', '*').replace('* ', '*').strip())


def uint64_bitfield_units(widths):
    """Reviewed MSVC x64 uint64 storage units, solely for GfxDrawSurfFields.

    Consecutive fields share one 64-bit unit; a field never straddles a unit.
    Zero-width/anonymous/mixed-type/packed forms are outside this finite rule.
    """
    require(bool(widths), 'Nonempty reviewed bitfield sequence required')
    units, used = 0, 64
    for width in widths:
        require(type(width) is int and 0 < width <= 64, 'Unreviewed uint64 bitfield width')
        if used + width > 64:
            units += 1
            used = 0
        used += width
    return units * 8, 8


class Declarations:
    """Reachable declarations only; Windows x64 LLP64, default pack8.

    Declared sizeof assertions supply native struct sizes. Alignment is derived
    recursively from members and active packing, never Python's host ABI.
    Unasserted structs must have the finite simple layout grammar below.
    """
    def __init__(self, source):
        self.source = re.sub(r'//[^\n]*|/\*.*?\*/', '', source, flags=re.S)
        self.structs, self.aliases, self.enums, self.cache = {}, {}, {}, {}
        self.sizes = {n: integer(v) for n, v in re.findall(r'assert_sizeof\((\w+),\s*([^)]*)\)', self.source)}
        for m in re.finditer(r'\b(struct|union)\s+(\w+)\s*\{', self.source):
            body, _ = block(self.source, m.end())
            stack = [8]
            for pragma in re.findall(r'#pragma pack\((.*?)\)', self.source[:m.start()]):
                if pragma == 'pop':
                    require(len(stack) > 1, 'Unbalanced packing')
                    stack.pop()
                else:
                    pm = re.fullmatch(r'push,\s*(1|2|4|8)', pragma)
                    require(pm is not None, 'Unreviewed packing')
                    stack.append(int(pm[1]))
            self.structs[m[2]] = (m[1], body, stack[-1])
        for decl, name, dims in re.findall(r'\btypedef\s+([^;{}]+?)\s+(\w+)\s*((?:\[\d+\])*)\s*;', self.source):
            self.aliases[name] = canonical(decl) + dims
        self.names = {}
        for m in re.finditer(r'\benum\s+(\w+)\s*(?::\s*([^\{]+))?\s*\{([^}]+)\}', self.source):
            self.enums[m[1]] = (canonical(m[2] or 'int'), m[3])

    def members(self, name):
        require(name in self.structs, 'Unknown native structure: ' + name)
        body = self.structs[name][1]
        units, lookup = [], {}
        # Only anonymous unions are nested in the reviewed reachable roots.
        while body.strip():
            body = body.lstrip()
            if body.startswith('union'):
                m = re.match(r'union\s*\{', body)
                require(m is not None, 'Unreviewed nested union')
                inner, end = block(body, m.end())
                require(body[end:].lstrip().startswith(';'), 'Named nested union unsupported')
                cells = self.simple_members(inner)
                lookup.update({k: v['type'] for k, v in cells.items()})
                units.append(('union', list(cells.values())))
                body = body[end:].lstrip()[1:]
            else:
                pos = body.find(';')
                require(pos >= 0, 'Unclosed member declaration')
                cells = self.simple_members(body[:pos + 1])
                require(not set(cells) & set(lookup), 'Duplicate member')
                lookup.update({k: v['type'] for k, v in cells.items()})
                units.extend(('member', [v]) for v in cells.values())
                body = body[pos + 1:]
        return lookup, units

    @staticmethod
    def simple_members(body):
        result = {}
        for decl in body.split(';'):
            if not decl.strip(): continue
            m = re.fullmatch(r'\s*(.*?)\s+(\w+)\s*((?:\[\d+\])*)\s*(?::\s*(\d+))?\s*', decl, re.S)
            require(m is not None, 'Unreviewed member: ' + decl[:100])
            require(m[2] not in result, 'Duplicate declaration')
            result[m[2]] = {'type': canonical(m[1]) + m[3], 'bits': int(m[4]) if m[4] is not None else None}
        return result

    def field(self, owner, expression):
        ty = owner
        for member in expression.split('.'):
            ty = self.members(ty)[0].get(member)
            require(ty is not None, 'Unknown field: ' + owner + '.' + expression)
        return ty

    def describe(self, ty):
        ty = canonical(ty)
        if ty in self.cache: return self.cache[ty]
        dims = re.findall(r'\[(\d+)\]', ty)
        if dims:
            base = self.describe(ty[:ty.index('[')])
            count = 1
            for n in dims: count *= int(n)
            row = {'kind': 'array', 'size': base['size'] * count, 'align': base['align'],
                   'element': ty[:ty.index('[')], 'extents': [int(n) for n in dims]}
        elif ty.endswith('*'):
            row = {'kind': 'pointer', 'size': 8, 'align': 8, 'element': ty[:-1]}
        elif ty.startswith('const '):
            row = dict(self.describe(ty[6:]))
        elif ty in self.aliases:
            row = dict(self.describe(self.aliases[ty]))
        elif ty in ('bool', 'float', 'double'):
            size = 1 if ty == 'bool' else 4 if ty == 'float' else 8
            row = {'kind': ty, 'size': size, 'align': size}
        elif ty in ('char', 'signed char', 'unsigned char', 'short', 'short int', 'unsigned short',
                    'unsigned short int', 'int', 'unsigned int', 'long', 'unsigned long',
                    'long long', 'unsigned long long', '__int64', 'unsigned __int64') or re.fullmatch(r'std::(?:u?int)(?:8|16|32|64)_t', ty):
            bits = int(re.search(r'(8|16|32|64)', ty)[1]) if ty.startswith('std::') else (8 if 'char' in ty else 16 if 'short' in ty else 64 if ('long long' in ty or '__int64' in ty) else 32)
            unsigned = ty.startswith('unsigned') or ty.startswith('std::uint')
            row = {'kind': 'int', 'size': bits // 8, 'align': bits // 8,
                   'min': 0 if unsigned else -(1 << (bits - 1)),
                   'max': (1 << bits) - 1 if unsigned else (1 << (bits - 1)) - 1}
        elif ty in self.enums:
            underlying, body = self.enums[ty]
            vals, names, next_value = [], {}, 0
            for item in body.split(','):
                if not item.strip(): continue
                parts = item.strip().split('=', 1)
                value = integer(parts[1], {**self.names, **names}) if len(parts) == 2 else next_value
                require(re.fullmatch(r'\w+', parts[0].strip()), 'Unreviewed enum member')
                names[parts[0].strip()] = value
                # Declared sentinels are not usable enum values in this dialect.
                if not re.search(r'(?:^NUM_|_NUM$|_COUNT$|_INVALID$)', parts[0].strip()): vals.append(value)
                next_value = value + 1
            self.names.update(names)
            row = {**self.describe(underlying), 'kind': 'enum', 'values': sorted(set(vals)), 'members': names}
            if not names:
                require(ty == 'WeaponChargeType' and underlying == 'std::int32_t', 'Unknown empty enum domain')
                row['semantic_domain_unknown'] = True
                row['storage_domain_only'] = True
                row['conversion_basis'] = 'fixed-int32-default-json-' + JSON_REVISION
        elif ty in self.structs:
            kind, _, packing = self.structs[ty]
            members, units = self.members(ty)
            bitfields = [cell for _, cells in units for cell in cells if cell['bits'] is not None]
            if bitfields:
                expected_names = ['objectId', 'pad0', 'tessellation', 'pad1', 'pad2']
                expected_widths = [16, 32, 2, 14, 64]
                require(ty == 'GfxDrawSurfFields' and kind == 'struct' and packing == 8
                        and list(members) == expected_names and len(units) == 5
                        and all(unit == 'member' and len(cells) == 1 for unit, cells in units)
                        and all(cell['type'] == 'unsigned __int64' for cell in bitfields)
                        and [cell['bits'] for cell in bitfields] == expected_widths,
                        'Unreviewed native bitfield layout: ' + ty)
                size, alignment = uint64_bitfield_units(expected_widths)
                row = {'kind': 'object', 'size': size, 'align': alignment, 'pack': packing,
                       'size_basis': 'reviewed-msvc-x64-uint64-bitfield-units',
                       'bitfields': list(zip(expected_names, expected_widths))}
                self.cache[ty] = row
                return row
            offset, alignment = 0, 1
            for unit_kind, cells in units:
                layouts = [self.describe(v['type']) for v in cells]
                a = min(packing, max(v['align'] for v in layouts))
                size = max(v['size'] for v in layouts) if unit_kind == 'union' else layouts[0]['size']
                alignment = max(alignment, a)
                offset = max(offset, size) if kind == 'union' else (offset + a - 1) // a * a + size
            calculated = (offset + alignment - 1) // alignment * alignment
            size = self.sizes.get(ty, calculated)
            require(size == calculated, 'Derived layout differs from pinned sizeof assertion: ' + ty)
            row = {'kind': 'object', 'size': size, 'align': alignment, 'pack': packing,
                   'size_basis': 'assert_sizeof' if ty in self.sizes else 'finite-member-layout'}
        else:
            raise ValueError('Unreviewed native type/layout: ' + ty)
        self.cache[ty] = row
        return row


def parser_functions(text, attachment=False):
    result = []
    for m in SIGNATURE.finditer(text):
        native = re.match(r'(\w+)\* asset', m[2])
        if native:
            ty = native[1]
        elif attachment and m[2] == 'const std::string& name, zone_memory* mem':
            ty = 'WeaponAttachment'
        else: continue
        body, end = block(text, m.end())
        first = text.count('\n', 0, m.end()) + 1
        result.append((ty, body, first, text.count('\n', 0, end) + 1))
    return result


def body_coverage(ty, body):
    if ty in MANUAL_BODY_SHA256:
        require(hashlib.sha256(body.encode()).hexdigest() == MANUAL_BODY_SHA256[ty],
                'Unreviewed manual parser branch: ' + ty)
    else:
        remainder = re.sub(r'//[^\n]*|/\*.*?\*/', '', CALL.sub('', body), flags=re.S)
        require(not remainder.strip(), 'Unclassified nonmacro parser statement: ' + ty)


def macro_rule(owner, macro, arguments, declarations, line):
    args = [a.strip() for a in arguments.split(',')]
    flavor = 'attachment' if macro.startswith('ATTACHMENT') or macro == 'PARSE_ATT' else 'weapon'
    kind = macro.removeprefix('WEAPON_PARSE_').removeprefix('ATTACHMENT_PARSE_')
    field = args[0]
    require(re.fullmatch(r'\w+(?:\.\w+)*', field), 'Unreviewed field expression')
    native_field = field
    key = args[1].strip('"') if kind == 'FIELD_RENAME' else field
    if macro == 'PARSE_UNK0':
        key, kind = 'unk0.' + field, 'FIELD'
    if macro == 'PARSE_ATT': kind = 'OPTIONAL'
    ty = declarations.field(owner, native_field)
    rule = {'op': kind, 'key': key, 'field': native_field, 'type': ty, 'flavor': flavor, 'line': line}
    accepted = {'FIELD', 'FIELD_RENAME', 'STRING', 'SCRIPT_STRING', 'ASSET', 'FXCOMBINED', 'OPTIONAL',
                'ASSET_ALLOC_ARR_MODVAL', 'ASSET_FIELD_ARR', 'SCRIPT_STRING_ALLOC_ARR',
                'FXCOMBINED_ALLOC_ARR', 'FIELD_ARR', 'FIELD_ALLOC_ARR', 'STRING_ARR',
                'SCRIPT_STRING_ALLOC_ARR_MODVAL', 'ASSET_ARR'}
    require(kind in accepted, 'Unreviewed parser macro: ' + macro)
    arity = 2 if ('ARR' in kind or kind == 'FIELD_RENAME') else 1
    require(len(args) == arity, 'Unreviewed parser arity')
    if kind == 'FIELD_RENAME':
        require(re.fullmatch(r'"[A-Za-z_]\w*"', args[1]), 'Literal renamed JSON key required')
    if 'ARR' in kind:
        if args[1].isdecimal(): rule['count'] = int(args[1])
        else:
            require(re.fullmatch(r'asset->\w+', args[1]), 'Unreviewed count expression')
            rule['count'] = args[1][7:]
            rule['count_type'] = declarations.field(owner, rule['count'])
            cd = declarations.describe(rule['count_type'])
            require(not cd.get('semantic_domain_unknown'), 'Unknown enum cannot be an allocation count')
    desc = declarations.describe(ty)
    if desc.get('semantic_domain_unknown'):
        require(kind == 'FIELD' and (owner, field) in {('WeaponDef', 'chargeType'), ('AttCharged', 'chargeType')}
                and ty == 'WeaponChargeType', 'Conversion-only enum used outside its two reviewed scalar fields')
        rule['semantic_domain_unknown'] = True
    if kind in ('FIELD', 'FIELD_RENAME'):
        require(desc['kind'] in ('bool', 'int', 'enum', 'float', 'double'), 'Unreviewed scalar type')
    if kind == 'STRING':
        require(ty == 'const char*' or declarations.aliases.get(ty) == 'const char*', 'Native C string required')
    if kind == 'SCRIPT_STRING':
        require(ty == 'scr_string_t', 'Native script-string type required')
    if kind == 'FXCOMBINED':
        require(ty == 'FxCombinedDef', 'Native FX combined type required')
    if kind in ('ASSET', 'OPTIONAL'):
        require(desc['kind'] == 'pointer', 'Pointer field required')
        declarations.describe(desc['element'])
    if 'ARR' in kind:
        require(desc['kind'] in ('pointer', 'array'), 'Array storage declaration required')
        elem = desc['element']
        ed = declarations.describe(elem)
        require(not ed.get('semantic_domain_unknown'), 'Conversion-only enum cannot be an array/index')
        if kind.startswith('ASSET'):
            require(ed['kind'] == 'pointer', 'Asset pointer array required')
            declarations.describe(ed['element'])
    return rule


def extract(blobs):
    """Internal finite extraction; public generate verifies every Source pin first."""
    decls = Declarations(blobs['iw7/structs.hpp'])
    structures, total, direct_sites = {}, 0, {}
    for filename in ('weapondef.cpp', 'weaponattachment.cpp'):
        text = blobs['iw7/assets/' + filename]
        dumped = {ty: body for ty, _, body, _ in dump_functions(text, filename)}
        for ty, body, first, last in parser_functions(text, filename.startswith('weaponattachment')):
            require(ty not in structures, 'Duplicate parser structure')
            body_coverage(ty, body)
            ops = []
            for m in CALL.finditer(body):
                line = first + body.count('\n', 0, m.start())
                # Leading whitespace may include a newline; use the macro token position.
                line = first + body.count('\n', 0, m.start(1))
                ops.append(macro_rule(ty, m[1], m[2], decls, line))
                total += 1
            parsed_keys = {r['key'] for r in ops}
            require(len(parsed_keys) == len(ops), 'Duplicate parser field rule')
            dump_keys = set()
            for macro, args in DUMP_MACRO.findall(dumped[ty]):
                parts = [p.strip() for p in args.split(',')]
                key = parts[1].strip('"') if macro.endswith('RENAME') else parts[0]
                if macro == 'DUMP_UNK0': key = 'unk0.' + key
                dump_keys.add(key)
            require(parsed_keys == dump_keys, 'Unresolved parser/dump macro keys: ' + ty)
            for item in MANUAL.get(ty, []):
                ops.append({'line': item[0], 'op': 'MANUAL', 'handler': list(item[1:])})
            ops.sort(key=lambda op: op['line'])
            keys = sorted({k.split('.')[0] if k.startswith('unk0.') else k for k in parsed_keys}
                          | set(MANUAL_KEYS.get(ty, [])))
            structures[ty] = {'keys': keys, 'ops': ops, 'layout': decls.describe(ty),
                              'source': filename, 'first': first, 'last': last}
            direct_sites[ty] = [{'line': first + i, 'text': line.strip()} for i, line in enumerate(body.splitlines())
                               if 'data[' in line or 'mem->' in line or 'add_script_string' in line]
    require(len(structures) == 41 and total == 1203, 'Finite complete overload/macro set changed')
    # Full native material allocation differs from macro named shells.
    for ty in ('Material', 'vec2_t', 'scr_string_t', 'FxCombinedDef'):
        decls.describe(ty)
    # Every Source file is hash pinned; each direct site is preserved for review.
    # Manual branches are deliberately finite, bound to these exact Source lines.
    require(set(k for k, v in direct_sites.items() if v) == {'WeaponDef', 'WeaponCompleteDef', 'WeaponAttachment'},
            'Unclassified direct parser branch')
    return {'pin': PIN, 'source_pins': PINS, 'platform': 'Windows-x64-LLP64-default-pack8',
            'enum_conversion_source': {'json_revision': JSON_REVISION, 'pins': CONVERSION_PINS},
            'structures': structures, 'types': dict(sorted(decls.cache.items())),
            'coverage': {'typed_structures': 41, 'macro_sites': total, 'direct_sites': direct_sites,
                         'manual_handlers': MANUAL, 'complete_pinned_extraction': True,
                         'actual_input_admissibility': False, 'runtime_abi_verified': False}}


def generate(root):
    root = Path(root)
    blobs = {}
    inputs = [(rel, root / 'src/zonetool/zonetool' / rel, expected) for rel, expected in PINS.items()]
    inputs += [(rel, root / rel, expected) for rel, expected in CONVERSION_PINS.items()]
    for rel, path, expected in inputs:
        require(path.is_file() and not path.is_symlink(), 'Regular pinned Source required: ' + rel)
        with path.open('rb') as stream: raw = stream.read(2097153)
        require(len(raw) <= 2097152 and b'\0' not in raw, 'Bounded Source text required')
        text = raw.decode('utf-8', errors='strict').replace('\r\n', '\n')
        require(hashlib.sha256(text.encode()).hexdigest() == expected, 'Pinned native Source changed: ' + rel)
        blobs[rel] = text
    return extract(blobs)


def render(schema):
    # One finite field/type record per line makes a large generated data table
    # reviewable without thousands of repeated indentation-only lines.
    lines = ['"""Generated finite fab935 input rules; see generate_native_body_schema.py.',
             'No native imports or runtime authority. Source layout is not runtime ABI proof.',
             '"""', 'SCHEMA = {']
    for key in sorted(schema):
        value = schema[key]
        if key == 'structures':
            lines.append("    'structures': {")
            for name, item in sorted(value.items()):
                lines.append('        ' + repr(name) + ': {')
                for field in sorted(item):
                    if field != 'ops': lines.append('            ' + repr(field) + ': ' + repr(item[field]) + ',')
                lines.append("            'ops': [")
                lines.extend('                ' + repr(rule) + ',' for rule in item['ops'])
                lines.extend(['            ],', '        },'])
            lines.append('    },')
        elif key == 'types':
            lines.append("    'types': {")
            lines.extend('        ' + repr(name) + ': ' + repr(desc) + ',' for name, desc in sorted(value.items()))
            lines.append('    },')
        else:
            lines.append('    ' + repr(key) + ': ' + repr(value) + ',')
    return '\n'.join([*lines, '}', ''])


# Constants-only projection. The existing extractor, renderer and CLI above are
# unchanged. No file is read or written by these helpers.
CPP_SCHEMA_PIN = {'git_blob': '99e084aeac3e26798a9b4349e22c245b5a15b664',
                  'bytes_lf': 262207,
                  'sha256_lf': '5e18fe147f2bbc55459f60c4e724dbdd15b86fe4bb23de92562016c2345813db'}
CPP_EXTRACTION_GENERATOR_PIN = {'git_blob': '4717a82a21117be7f744bc6e0e6ce56cf9c7db92',
                                'bytes_lf': 24497,
                                'sha256_lf': '4ddfdf8a9c46b2d78af8ccc70f74524596c16a116f5d04423cfe7d6cb413f9e6'}
CPP_TYPE_TAGS = ('object', 'pointer', 'enum', 'array', 'bool', 'int', 'float')
CPP_OP_TAGS = ('ASSET', 'ASSET_ALLOC_ARR_MODVAL', 'ASSET_ARR', 'ASSET_FIELD_ARR',
               'FIELD', 'FIELD_ALLOC_ARR', 'FIELD_ARR', 'FIELD_RENAME', 'FXCOMBINED',
               'FXCOMBINED_ALLOC_ARR', 'MANUAL', 'OPTIONAL', 'SCRIPT_STRING',
               'SCRIPT_STRING_ALLOC_ARR', 'SCRIPT_STRING_ALLOC_ARR_MODVAL', 'STRING', 'STRING_ARR')
CPP_MANUAL_TAGS = ('object', 'entries', 'graphs', 'definition', 'original_graphs',
                   'overrides', 'unk_material', 'internal_script')
CPP_TYPE_OPTIONALS = ('pack', 'size_basis', 'element', 'extents', 'min', 'max',
                       'values', 'members', 'bitfields', 'conversion_basis',
                       'semantic_domain_unknown', 'storage_domain_only')
CPP_OP_OPTIONALS = ('field', 'key', 'flavor', 'type', 'count', 'count_type',
                     'semantic_domain_unknown', 'handler')
CPP_RECORDS = {
    'StringSpan': (('offset', 'u32'), ('count', 'u32')),
    'Integer': (('negative', 'bool'), ('magnitude', 'u64')),
    'NamedInteger': (('name', 'u32'), ('value', 'Integer')),
    'NamedUnsigned': (('name', 'u32'), ('value', 'u64')),
    'TypeRecord': (('name', 'u32'), ('kind', 'u32'), ('present', 'u32'), ('size', 'u64'),
                   ('align', 'u64'), ('pack', 'u64'), ('size_basis', 'u32'),
                   ('element_tag', 'u32'), ('element', 'u32'), ('extents', 'StringSpan'), ('minimum', 'Integer'),
                   ('maximum', 'Integer'), ('values', 'StringSpan'), ('members', 'StringSpan'),
                   ('bitfields', 'StringSpan'), ('conversion_basis', 'u32'),
                   ('semantic_domain_unknown', 'bool'), ('storage_domain_only', 'bool')),
    'Operation': (('tag', 'u32'), ('line', 'u32'), ('present', 'u32'), ('field', 'u32'),
                  ('key', 'u32'), ('flavor', 'u32'), ('type', 'u32'), ('count_tag', 'u32'),
                  ('fixed_count', 'u64'), ('named_count', 'u32'), ('count_type', 'u32'),
                  ('semantic_domain_unknown', 'bool'), ('manual', 'u32')),
    'Manual': (('owner', 'u32'), ('line', 'u32'), ('tag', 'u32'), ('arguments', 'StringSpan')),
    'DirectSite': (('line', 'u32'), ('text', 'u32')),
    'Structure': (('name', 'u32'), ('layout', 'u32'), ('source', 'u32'), ('first', 'u32'),
                   ('last', 'u32'), ('keys', 'StringSpan'), ('ops', 'StringSpan'),
                   ('direct_sites', 'StringSpan')),
    'OwnerSpan': (('owner', 'u32'), ('items', 'StringSpan')),
    'SourcePin': (('name', 'u32'), ('sha256', 'u32')),
    'Provenance': (('role', 'u32'), ('git_blob', 'u32'), ('bytes_lf', 'u64'), ('sha256_lf', 'u32')),
    'Metadata': (('pin', 'u32'), ('platform', 'u32'), ('json_revision', 'u32'),
                  ('typed_structures', 'u32'), ('macro_sites', 'u32'),
                  ('complete_pinned_extraction', 'bool'), ('actual_input_admissibility', 'bool'),
                  ('runtime_abi_verified', 'bool')),
}
CPP_TABLES = {'strings': 'StringSpan', 'extents': 'u64', 'integers': 'Integer',
              'enum_members': 'NamedInteger', 'bitfields': 'NamedUnsigned',
              'types': 'TypeRecord', 'key_ids': 'u32', 'argument_ids': 'u32',
              'manuals': 'Manual', 'operations': 'Operation', 'direct_sites': 'DirectSite',
              'structures': 'Structure', 'direct_owners': 'OwnerSpan', 'manual_ids': 'u32',
              'manual_owners': 'OwnerSpan', 'source_pins': 'SourcePin',
              'conversion_pins': 'SourcePin', 'manual_body_pins': 'SourcePin',
              'provenance': 'Provenance', 'type_tags': 'u32', 'op_tags': 'u32',
              'manual_tags': 'u32', 'metadata': 'Metadata'}


def _cpp_u(value, bits):
    require(type(value) is int and 0 <= value < 1 << bits, 'C++ table unsigned narrowing')
    return value


def _cpp_integer(value):
    require(type(value) is int and -(1 << 64) < value < 1 << 64,
            'C++ table sign/magnitude range')
    return (value < 0, abs(value))


def _cpp_same(left, right):
    if type(left) is not type(right): return False
    if isinstance(left, dict):
        return list(left) == list(right) and all(_cpp_same(left[k], right[k]) for k in left)
    if isinstance(left, (list, tuple)):
        return len(left) == len(right) and all(_cpp_same(a, b) for a, b in zip(left, right))
    return left == right


def _cpp_source_pin(pin):
    require(type(pin) is dict and set(pin) == {'git_blob', 'bytes_lf', 'sha256_lf'},
            'Closed Source provenance pin')
    require(type(pin['git_blob']) is str and re.fullmatch('[0-9a-f]{40}', pin['git_blob']) and
            type(pin['sha256_lf']) is str and re.fullmatch('[0-9a-f]{64}', pin['sha256_lf']),
            'Canonical Source provenance digest')
    require(type(pin['bytes_lf']) is int and 0 < pin['bytes_lf'] <= 2097152,
            'Bounded Source provenance length')


def _cpp_literal(schema_raw, expected_schema_pin):
    _cpp_source_pin(expected_schema_pin)
    require(type(schema_raw) is bytes and len(schema_raw) <= 2097152 and b'\0' not in schema_raw,
            'Bounded literal Source bytes')
    text = schema_raw.decode('utf-8', errors='strict').replace('\r\n', '\n')
    encoded = text.encode('utf-8')
    require(len(encoded) == expected_schema_pin['bytes_lf'] and
            hashlib.sha256(encoded).hexdigest() == expected_schema_pin['sha256_lf'],
            'Literal Source pin differs before AST parse')
    require(hashlib.sha1(b'blob ' + str(len(encoded)).encode() + b'\0' + encoded).hexdigest() ==
            expected_schema_pin['git_blob'], 'Literal Source Git blob differs before AST parse')
    tree = ast.parse(text)
    require(len(tree.body) == 2 and isinstance(tree.body[0], ast.Expr) and
            isinstance(tree.body[0].value, ast.Constant) and type(tree.body[0].value.value) is str,
            'Only docstring and one literal SCHEMA assignment permitted')
    assignment = tree.body[1]
    require(isinstance(assignment, ast.Assign) and len(assignment.targets) == 1 and
            isinstance(assignment.targets[0], ast.Name) and assignment.targets[0].id == 'SCHEMA',
            'One literal SCHEMA assignment required')
    return ast.literal_eval(assignment.value)


def _cpp_schema(schema):
    require(type(schema) is dict and set(schema) == {'coverage', 'enum_conversion_source',
            'pin', 'platform', 'source_pins', 'structures', 'types'}, 'Closed SCHEMA fields')
    require(schema['pin'] == PIN and schema['platform'] == 'Windows-x64-LLP64-default-pack8' and
            _cpp_same(schema['source_pins'], PINS), 'Exact native Source provenance')
    conversion = schema['enum_conversion_source']
    require(type(conversion) is dict and set(conversion) == {'json_revision', 'pins'} and
            conversion['json_revision'] == JSON_REVISION and _cpp_same(conversion['pins'], CONVERSION_PINS),
            'Exact conversion Source provenance')
    types, structures, coverage = schema['types'], schema['structures'], schema['coverage']
    require(type(types) is dict and len(types) == 239 and type(structures) is dict and
            len(structures) == 41, 'Finite type/structure identities')
    for name, desc in types.items():
        require(type(name) is str and type(desc) is dict and desc.get('kind') in CPP_TYPE_TAGS,
                'Closed type kind')
        kind = desc['kind']; base = {'kind', 'size', 'align'}
        extra = {'object': {'pack', 'size_basis'}, 'pointer': {'element'},
                 'enum': {'min', 'max', 'values', 'members'}, 'array': {'element', 'extents'},
                 'bool': set(), 'int': {'min', 'max'}, 'float': set()}[kind]
        optional = {'object': {'bitfields'}, 'enum': {'conversion_basis', 'semantic_domain_unknown',
                    'storage_domain_only'}}.get(kind, set())
        require(base | extra <= set(desc) <= base | extra | optional, 'Unknown/missing type fields')
        for field in ('size', 'align', 'pack'):
            if field in desc: _cpp_u(desc[field], 64)
        require(desc['align'] > 0, 'Nonzero Source alignment')
        if 'element' in desc:
            require(type(desc['element']) is str and (kind == 'pointer' or desc['element'] in types),
                    'Exact pointer label or known array element type')
        if 'extents' in desc:
            require(type(desc['extents']) is list and desc['extents'], 'Explicit array extents')
            for value in desc['extents']: _cpp_u(value, 64)
        for field in ('min', 'max'):
            if field in desc: _cpp_integer(desc[field])
        if 'values' in desc:
            require(type(desc['values']) is list, 'Present enum values list')
            for value in desc['values']: _cpp_integer(value)
        if 'members' in desc:
            require(type(desc['members']) is dict, 'Present ordered enum declaration map')
            for member, value in desc['members'].items():
                require(type(member) is str, 'Enum declaration name'); _cpp_integer(value)
        if 'bitfields' in desc:
            require(type(desc['bitfields']) is list, 'Ordered bitfield metadata')
            for pair in desc['bitfields']:
                require(type(pair) is tuple and len(pair) == 2 and type(pair[0]) is str, 'Named bitfield tuple')
                _cpp_u(pair[1], 64)
        for field in ('semantic_domain_unknown', 'storage_domain_only'):
            if field in desc: require(type(desc[field]) is bool, 'Exact boolean type flag')
        for field in ('size_basis', 'conversion_basis'):
            if field in desc: require(type(desc[field]) is str, 'Exact layout/conversion label')
    require(type(coverage) is dict and set(coverage) == {'typed_structures', 'macro_sites', 'direct_sites',
            'manual_handlers', 'complete_pinned_extraction', 'actual_input_admissibility', 'runtime_abi_verified'},
            'Closed coverage fields')
    require(type(coverage['typed_structures']) is int and coverage['typed_structures'] == 41 and
            type(coverage['macro_sites']) is int and coverage['macro_sites'] == 1203, 'Exact coverage counts')
    for field in ('complete_pinned_extraction', 'actual_input_admissibility', 'runtime_abi_verified'):
        require(type(coverage[field]) is bool, 'Exact coverage boolean')
    require(type(coverage['direct_sites']) is dict and set(coverage['direct_sites']) == set(structures), 'Every direct-site owner retained')
    require(_cpp_same(coverage['manual_handlers'], MANUAL), 'Pinned manual sites/order/arguments')
    total = manual = 0
    for name, structure in structures.items():
        require(type(name) is str and type(structure) is dict and set(structure) == {'first', 'keys', 'last', 'layout', 'source', 'ops'}, 'Closed structure fields')
        require(name in types and _cpp_same(structure['layout'], types[name]), 'Complete structure layout matches referenced type')
        require(type(structure['source']) is str and structure['source'] in ('weapondef.cpp', 'weaponattachment.cpp'), 'Closed Source filename')
        _cpp_u(structure['first'], 32); _cpp_u(structure['last'], 32)
        require(structure['first'] <= structure['last'] and type(structure['keys']) is list and
                all(type(k) is str for k in structure['keys']) and type(structure['ops']) is list, 'Ordered structure keys/operations')
        for op in structure['ops']:
            require(type(op) is dict and op.get('op') in CPP_OP_TAGS, 'Closed operation tag')
            _cpp_u(op['line'], 32); total += 1
            if op['op'] == 'MANUAL':
                require(set(op) == {'op', 'line', 'handler'} and type(op['handler']) is list and
                        op['handler'] and op['handler'][0] in CPP_MANUAL_TAGS and
                        all(type(v) is str for v in op['handler']), 'Closed manual handler')
                arity = 3 if op['handler'][0] in ('object', 'entries') else 1
                require(len(op['handler']) == arity, 'Manual argument arity')
                if arity == 3: require(op['handler'][2] in structures, 'Manual target structure')
                manual += 1
            else:
                base = {'op', 'line', 'field', 'key', 'flavor', 'type'}
                dynamic = op['op'] in ('ASSET_ALLOC_ARR_MODVAL', 'ASSET_ARR', 'SCRIPT_STRING_ALLOC_ARR_MODVAL')
                counted = dynamic or op['op'] in ('FIELD_ALLOC_ARR', 'FIELD_ARR', 'SCRIPT_STRING_ALLOC_ARR', 'ASSET_FIELD_ARR', 'FXCOMBINED_ALLOC_ARR', 'STRING_ARR')
                expected = base | ({'count', 'count_type'} if dynamic else {'count'} if counted else set())
                require(expected <= set(op) <= expected | ({'semantic_domain_unknown'} if op['op'] == 'FIELD' else set()), 'Unknown/missing operation field')
                require(all(type(op[k]) is str for k in ('field', 'key', 'flavor', 'type')) and
                        op['flavor'] in ('weapon', 'attachment') and op['type'] in types, 'Closed operation strings/type reference')
                if dynamic: require(type(op['count']) is str and type(op['count_type']) is str and op['count_type'] in types, 'Named count and distinct type')
                elif counted: _cpp_u(op['count'], 64)
                if 'semantic_domain_unknown' in op: require(type(op['semantic_domain_unknown']) is bool, 'Exact operation boolean flag')
        sites = coverage['direct_sites'][name]
        require(type(sites) is list, 'Ordered direct sites')
        for site in sites:
            require(type(site) is dict and set(site) == {'line', 'text'} and type(site['text']) is str, 'Closed direct-site record')
            _cpp_u(site['line'], 32)
    require(total == 1213 and manual == 10 and total - manual == coverage['macro_sites'], 'Exact finite operation/manual totals')


def _cpp_project(schema, provenance):
    _cpp_schema(schema)
    require(type(provenance) is dict and set(provenance) == {'schema', 'extraction_generator', 'projection_generator', 'body_validator'}, 'Closed offline provenance roles')
    for pin in provenance.values(): _cpp_source_pin(pin)
    require(_cpp_same(provenance['extraction_generator'], CPP_EXTRACTION_GENERATOR_PIN),
            'Historical extraction provenance is not the new projection generator')
    pool = {''}
    def strings(value):
        if type(value) is str:
            require('\0' not in value, 'NUL-free Source string'); value.encode('utf-8', errors='strict'); pool.add(value)
        elif isinstance(value, dict):
            for k, v in value.items(): strings(k); strings(v)
        elif isinstance(value, (list, tuple)):
            for v in value: strings(v)
    strings(schema); strings(provenance); strings(MANUAL_BODY_SHA256)
    for values in (CPP_TYPE_TAGS, CPP_OP_TAGS, CPP_MANUAL_TAGS): strings(values)
    names = sorted(pool, key=lambda s: s.encode('utf-8')); sid = {v: i for i, v in enumerate(names)}
    types = sorted(schema['types'], key=lambda s: s.encode('utf-8')); tid = {v: i for i, v in enumerate(types)}
    structures = sorted(schema['structures'], key=lambda s: s.encode('utf-8')); owners = {v: i for i, v in enumerate(structures)}
    tables = {name: [] for name in CPP_TABLES}; char_pool = bytearray()
    def span(table, values):
        values = list(values); start = _cpp_u(len(tables[table]), 32); count = _cpp_u(len(values), 32)
        require(count <= (1 << 32) - 1 - start, 'Span append overflow')
        tables[table].extend(values); return (start, count)
    for name in names:
        encoded = name.encode('utf-8'); tables['strings'].append((_cpp_u(len(char_pool), 32), _cpp_u(len(encoded), 32))); char_pool.extend(encoded)
    for name in types:
        d = schema['types'][name]; mask = sum(1 << i for i, key in enumerate(CPP_TYPE_OPTIONALS) if key in d)
        tables['types'].append((sid[name], CPP_TYPE_TAGS.index(d['kind']), mask, d['size'], d['align'], d.get('pack', 0),
            sid[d.get('size_basis', '')], 0 if 'element' not in d else 1 if d['element'] in tid else 2,
            tid[d['element']] if 'element' in d and d['element'] in tid else sid[d['element']] if 'element' in d else 0,
            span('extents', d.get('extents', [])), _cpp_integer(d.get('min', 0)), _cpp_integer(d.get('max', 0)),
            span('integers', (_cpp_integer(v) for v in d.get('values', []))),
            span('enum_members', ((sid[k], _cpp_integer(v)) for k, v in d.get('members', {}).items())),
            span('bitfields', ((sid[k], v) for k, v in d.get('bitfields', []))), sid[d.get('conversion_basis', '')],
            d.get('semantic_domain_unknown', False), d.get('storage_domain_only', False)))
    manual_lookup = {}
    for name in structures:
        d = schema['structures'][name]; operations = []
        for op in d['ops']:
            mask = sum(1 << i for i, key in enumerate(CPP_OP_OPTIONALS) if key in op)
            count_tag = 0 if 'count' not in op else 1 if type(op['count']) is int else 2
            manual_id = 0
            if op['op'] == 'MANUAL':
                handler = op['handler']; key = (name, op['line'], *handler)
                require(key not in manual_lookup, 'Duplicate manual site identity')
                manual_id = len(tables['manuals']); manual_lookup[key] = manual_id
                tables['manuals'].append((owners[name], op['line'], CPP_MANUAL_TAGS.index(handler[0]), span('argument_ids', (sid[v] for v in handler[1:]))))
            operations.append((CPP_OP_TAGS.index(op['op']), op['line'], mask, sid[op.get('field', '')], sid[op.get('key', '')],
                sid[op.get('flavor', '')], tid[op['type']] if 'type' in op else 0, count_tag,
                op['count'] if count_tag == 1 else 0, sid[op['count']] if count_tag == 2 else 0,
                tid[op['count_type']] if 'count_type' in op else 0, op.get('semantic_domain_unknown', False), manual_id))
        sites = schema['coverage']['direct_sites'][name]
        tables['structures'].append((sid[name], tid[name], sid[d['source']], d['first'], d['last'],
            span('key_ids', (sid[k] for k in d['keys'])), span('operations', operations),
            span('direct_sites', ((s['line'], sid[s['text']]) for s in sites))))
    for name in schema['coverage']['direct_sites']:
        tables['direct_owners'].append((owners[name], tables['structures'][owners[name]][7]))
    for name, sites in schema['coverage']['manual_handlers'].items():
        ids = [manual_lookup[(name, *site)] for site in sites]
        tables['manual_owners'].append((owners[name], span('manual_ids', ids)))
    tables['source_pins'] = [(sid[k], sid[v]) for k, v in schema['source_pins'].items()]
    tables['conversion_pins'] = [(sid[k], sid[v]) for k, v in schema['enum_conversion_source']['pins'].items()]
    tables['manual_body_pins'] = [(sid[k], sid[v]) for k, v in MANUAL_BODY_SHA256.items()]
    tables['provenance'] = [(sid[k], sid[provenance[k]['git_blob']], provenance[k]['bytes_lf'], sid[provenance[k]['sha256_lf']])
                            for k in ('schema', 'extraction_generator', 'projection_generator', 'body_validator')]
    for table, tags in (('type_tags', CPP_TYPE_TAGS), ('op_tags', CPP_OP_TAGS), ('manual_tags', CPP_MANUAL_TAGS)):
        tables[table] = [sid[v] for v in tags]
    c = schema['coverage']; tables['metadata'] = [(sid[schema['pin']], sid[schema['platform']], sid[schema['enum_conversion_source']['json_revision']],
        c['typed_structures'], c['macro_sites'], c['complete_pinned_extraction'], c['actual_input_admissibility'], c['runtime_abi_verified'])]
    _cpp_check_tables(tables, bytes(char_pool))
    return tables, bytes(char_pool)


def _cpp_check_tables(tables, char_pool):
    require(type(tables) is dict and set(tables) == set(CPP_TABLES), 'Closed table names')
    require(type(char_pool) is bytes and len(char_pool) < 1 << 32, 'Bounded char pool')
    def cell(value, kind):
        if kind in ('u32', 'u64'): _cpp_u(value, int(kind[1:])); return
        if kind == 'bool': require(type(value) is bool, 'Exact record boolean'); return
        require(type(value) is tuple and len(value) == len(CPP_RECORDS[kind]), 'Closed record width')
        for v, (_, ty) in zip(value, CPP_RECORDS[kind]): cell(v, ty)
        if kind == 'Integer': require(not(value[0] and value[1] == 0), 'No negative zero')
    for table, kind in CPP_TABLES.items():
        require(type(tables[table]) is list and len(tables[table]) < 1 << 32, 'Bounded typed table')
        for value in tables[table]: cell(value, kind)
    def ref(value, table): require(value < len(tables[table]), 'Orphan table reference')
    def span(value, table):
        length = len(char_pool) if table == 'char_pool' else len(tables[table])
        require(value[0] <= length and value[1] <= length - value[0], 'Orphan/subtraction-checked table span')
    for value in tables['strings']: span(value, 'char_pool')
    def text(index):
        ref(index, 'strings'); start, count = tables['strings'][index]
        return char_pool[start:start+count].decode('utf-8', errors='strict')
    type_names = {text(row[0]) for row in tables['types']}
    require(len(type_names) == len(tables['types']), 'Unique type identity names')
    for table in ('key_ids', 'argument_ids', 'type_tags', 'op_tags', 'manual_tags'):
        for value in tables[table]: ref(value, 'strings')
    for table in ('enum_members', 'bitfields', 'source_pins', 'conversion_pins', 'manual_body_pins'):
        for row in tables[table]:
            ref(row[0], 'strings')
            if table in ('source_pins', 'conversion_pins', 'manual_body_pins'): ref(row[1], 'strings')
    for row in tables['types']:
        ref(row[0], 'strings'); require(row[1] < len(CPP_TYPE_TAGS) and row[2] < 1 << len(CPP_TYPE_OPTIONALS), 'Closed type tag/presence')
        if row[1] in (CPP_TYPE_TAGS.index('pointer'), CPP_TYPE_TAGS.index('array')):
            require(row[2] & (1 << 2), 'Pointer/array element presence required')
        for i in (6, 15): ref(row[i], 'strings')
        if not row[2] & (1 << 2): require(row[7] == 0 and row[8] == 0, 'Absent element tag/reference')
        elif row[7] == 1: ref(row[8], 'types')
        elif row[7] == 2:
            require(row[1] == CPP_TYPE_TAGS.index('pointer') and text(row[8]) not in type_names,
                    'Only unexpanded pointer labels use tag2; known labels require tag1')
        else: raise ValueError('Closed element reference tag')
        if row[1] == CPP_TYPE_TAGS.index('array'): require(row[7] == 1, 'Array element requires known type')
        for i, table in ((9, 'extents'), (12, 'integers'), (13, 'enum_members'), (14, 'bitfields')): span(row[i], table)
    for row in tables['operations']:
        require(row[0] < len(CPP_OP_TAGS) and row[2] < 1 << len(CPP_OP_OPTIONALS) and row[7] in (0, 1, 2), 'Closed op tag/presence/count')
        for i in (3, 4, 5, 9): ref(row[i], 'strings')
        if row[2] & (1 << 3): ref(row[6], 'types')
        if row[2] & (1 << 5): ref(row[10], 'types')
        if row[0] == CPP_OP_TAGS.index('MANUAL'): ref(row[12], 'manuals')
    for row in tables['manuals']:
        ref(row[0], 'structures'); require(row[2] < len(CPP_MANUAL_TAGS), 'Closed manual tag'); span(row[3], 'argument_ids')
    for row in tables['direct_sites']: ref(row[1], 'strings')
    for row in tables['structures']:
        ref(row[0], 'strings'); ref(row[1], 'types'); ref(row[2], 'strings')
        for i, table in ((5, 'key_ids'), (6, 'operations'), (7, 'direct_sites')): span(row[i], table)
    for table, target in (('direct_owners', 'direct_sites'), ('manual_owners', 'manual_ids')):
        for row in tables[table]: ref(row[0], 'structures'); span(row[1], target)
    for value in tables['manual_ids']: ref(value, 'manuals')
    for row in tables['provenance']:
        for i in (0, 1, 3): ref(row[i], 'strings')
    for row in tables['metadata']:
        for i in (0, 1, 2): ref(row[i], 'strings')


def render_cpp(schema_raw, expected_schema_pin, source_provenance):
    """Pure constants-only projection. Provenance is not an execution token.

    The future caller must externally pin this executing generator and its
    transitive executable Source BEFORE import. Its new Git identity is supplied
    after phase1 freeze, avoiding a generator/header self-hash cycle.
    """
    schema = _cpp_literal(schema_raw, expected_schema_pin)
    require(type(source_provenance) is dict, 'Explicit offline provenance data')
    require(_cpp_same(source_provenance.get('schema'), expected_schema_pin), 'Schema provenance matches external pin')
    tables, pool = _cpp_project(schema, source_provenance)
    def value(v, kind):
        if kind == 'bool': return 'true' if v else 'false'
        if kind in ('u32', 'u64'): return str(v) + ('ULL' if kind == 'u64' else 'U')
        return '{' + ','.join(value(x, ty) for x, (_, ty) in zip(v, CPP_RECORDS[kind])) + '}'
    lines = ['// Generated offline Source constants. No runtime or ABI authority.', '#pragma once',
             '#include <array>', '#include <cstdint>', 'namespace iw7::neutral::body_schema {']
    for name, fields in CPP_RECORDS.items():
        ty = {'u32': 'std::uint32_t', 'u64': 'std::uint64_t', 'bool': 'bool'}
        lines.append('struct '+name+' {'+' '.join(ty.get(kind, kind)+' '+field+';' for field, kind in fields)+'};')
    lines.append('inline constexpr char string_pool[] = {')
    for offset in range(0, len(pool), 16):
        lines.append(','.join('static_cast<char>(0x%02x)' % b for b in pool[offset:offset+16])+',')
    lines.append('};')
    for name, kind in CPP_TABLES.items():
        ty = {'u32': 'std::uint32_t', 'u64': 'std::uint64_t', 'bool': 'bool'}.get(kind, kind)
        lines.append('inline constexpr std::array<'+ty+','+str(len(tables[name]))+'> '+name+'{{')
        lines.extend(value(row, kind)+',' for row in tables[name])
        lines.append('}};')
    lines.extend(['} // namespace iw7::neutral::body_schema', ''])
    return '\n'.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    schema = generate(args.native_source_root)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(render(schema))
    print(json.dumps(schema['coverage']))

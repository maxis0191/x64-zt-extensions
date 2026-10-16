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
                lookup.update(cells)
                units.append(('union', list(cells.values())))
                body = body[end:].lstrip()[1:]
            else:
                pos = body.find(';')
                require(pos >= 0, 'Unclosed member declaration')
                cells = self.simple_members(body[:pos + 1])
                require(not set(cells) & set(lookup), 'Duplicate member')
                lookup.update(cells)
                units.extend(('member', [v]) for v in cells.values())
                body = body[pos + 1:]
        return lookup, units

    @staticmethod
    def simple_members(body):
        result = {}
        for decl in body.split(';'):
            if not decl.strip(): continue
            m = re.fullmatch(r'\s*(.*?)\s+(\w+)\s*((?:\[\d+\])*)\s*(?::\s*\d+)?\s*', decl, re.S)
            require(m is not None, 'Unreviewed member: ' + decl[:100])
            require(m[2] not in result, 'Duplicate declaration')
            result[m[2]] = canonical(m[1]) + m[3]
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
            _, units = self.members(ty)
            offset, alignment = 0, 1
            for unit_kind, cells in units:
                layouts = [self.describe(v) for v in cells]
                a = min(packing, max(v['align'] for v in layouts))
                size = max(v['size'] for v in layouts) if unit_kind == 'union' else layouts[0]['size']
                alignment = max(alignment, a)
                offset = max(offset, size) if kind == 'union' else (offset + a - 1) // a * a + size
            calculated = (offset + alignment - 1) // alignment * alignment
            # Bitfields in asserted dependency structs have Source size assertions;
            # their alignment still follows their declared storage types/packing.
            size = self.sizes.get(ty, calculated)
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    schema = generate(args.native_source_root)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(render(schema))
    print(json.dumps(schema['coverage']))

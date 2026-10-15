"""Finite Source-only readset generation for the two pinned IW7 serializers.

No C++, SDK, binary or native execution. Exact source hashes precede extraction;
unknown macros/count expressions refuse instead of producing partial coverage.
The generated typed field calls are reviewed together with the manual readsets.
"""
import argparse
import hashlib
from pathlib import Path
import re

SERIALIZERS = {
    'assets/weapondef.cpp': 'fc6defc7d4cdad56d3615ff2d13a1c6715f8b6e53dbdc7dd4be25ce4255050b5',
    'assets/weaponattachment.cpp': '746d520c49f122bc650652da78deed45b091198bb10b30dc48bc6a38c9227e4c',
}
HEADERS = {
    'structs.hpp': '482affaf3641dc5318422c4cef45383923183349ae91d18e9d3ff29699f8a0df',
    'assets/weapondef.hpp': '3c1f7b2fd4fd5ce7a4919dbabc6a5bf4e1ac1591029a89e29f3cf77c1821d084',
    'assets/weaponattachment.hpp': 'ce53d8d720236d55e2b174cf40ef5d56158c958f1b0ed885b55fb820d7d825ff',
}
NATIVE = Path('src/zonetool/zonetool/iw7')
CAP = 2 * 1024 * 1024
# Pinned native declarations are Material* [16], unlike complex-model and
# attachment variation/material fields, which are true pointer fields.
INLINE_ASSET_ARRAYS = {
    ('WeaponDef', 'camoWorldModelMaterialOverride'): 16,
    ('WeaponDef', 'camoViewModelMaterialOverride'): 16,
}
MACRO = re.compile(r'\b((?:WEAPON|ATTACHMENT)_DUMP_[A-Z_]+|DUMP_UNK0|DUMP_ATT)\(([^;\n]*)\)\s*;')


def source(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Regular pinned serializer source required')
    with path.open('rb') as stream:
        raw = stream.read(CAP + 1)
    if len(raw) > CAP or b'\0' in raw:
        raise ValueError('Bounded serializer text required')
    return raw.decode('utf-8-sig').replace('\r\n', '\n')


def functions(text, filename):
    pattern = r'(?:void|ordered_json)\s+(?:(?:weapon_def|weapon_attachment)::)?(dump\w*)\(([^\n]*?)\)\s*\{'
    result = []
    for match in re.finditer(pattern, text):
        if 'ordered_json' not in match[2] and match[1] != 'dump_complete' and match[2] != 'WeaponAttachment* asset':
            continue
        start = match.end()
        depth, end = 1, start
        while depth and end < len(text):
            depth += (text[end] == '{') - (text[end] == '}')
            end += 1
        if depth:
            raise ValueError('Unclosed pinned serializer function')
        body = re.sub(r'//[^\n]*|/\*.*?\*/', '', text[start:end-1], flags=re.S)
        native_type = re.fullmatch(r'(\w+)\* asset(?:, WeaponCompleteDef\* parent)?(?:, ordered_json& data)?', match[2])
        if not native_type:
            raise ValueError('Unexpected native dump signature')
        result.append((native_type[1], match[1], body, filename))
    return result


def field_call(native_type, macro, arguments):
    args = [arg.strip() for arg in arguments.split(',')]
    field = args[0]
    if not re.fullmatch(r'[A-Za-z_]\w*(?:\[\d+\])*(?:\.[A-Za-z_]\w*(?:\[\d+\])*)*', field):
        raise ValueError('Unreviewed serializer field expression: ' + repr(field))
    label = f'"{native_type}.{field}"'
    address = f'&asset->{field}'
    kind = macro.removeprefix('WEAPON_DUMP_').removeprefix('ATTACHMENT_DUMP_')
    if macro == 'DUMP_UNK0' or kind in ('FIELD', 'FIELD_RENAME'):
        return f'r.scalar({address}, {label})'
    if kind == 'STRING':
        return f'r.string_field({address}, {label})'
    if kind == 'SCRIPT_STRING':
        return f'r.script_field({address}, {label})'
    if kind == 'ASSET':
        return f'r.asset_field({address}, {label})'
    if kind == 'FXCOMBINED':
        return f'r.fx(asset->{field}, {label})'
    if macro == 'DUMP_ATT':
        return f'optional(r, {address}, {label})'
    if len(args) != 2:
        raise ValueError('Unreviewed serializer macro shape: ' + macro)
    size = args[1]
    if kind == 'FIELD_ARR':
        if not size.isdecimal():
            raise ValueError('Unreviewed fixed scalar array size')
        return f'r.fixed_scalars({address}, {size}, {label})'
    if kind == 'STRING_ARR':
        if not size.isdecimal():
            raise ValueError('Unreviewed fixed native string array size')
        return f'r.native_string_array({address}, {size}, {label})'
    visitors = {'FIELD_ALLOC_ARR': 'r.scalar(value, {label})', 'ASSET_ARR': 'r.asset_field(value, {label})',
                'SCRIPT_STRING_ALLOC_ARR': 'r.script_field(value, {label})', 'FXCOMBINED_ALLOC_ARR': 'r.fx(*value, {label})'}
    if kind not in visitors:
        raise ValueError('Uncovered serializer macro: ' + macro)
    visit = visitors[kind].format(label=label)
    callback = f'[&](const auto* value) {{ return {visit}; }}'
    if kind == 'ASSET_ARR' and (native_type, field) in INLINE_ASSET_ARRAYS:
        if size != str(INLINE_ASSET_ARRAYS[(native_type, field)]):
            raise ValueError('Pinned inline asset-array extent changed')
        return f'r.inline_objects({address}, {label}, {callback})'
    if size.isdecimal():
        return f'r.pointer_array({address}, {size}, {label}, {callback})'
    if re.fullmatch(r'asset->\w+', size):
        return f'r.counted_array({address}, &{size}, {label}, {callback})'
    raise ValueError('Unreviewed dynamic serializer count')


def manual(native_type):
    if native_type == 'WeaponDef':
        return '''
        if (!validate(r, &asset->overlay) || !validate(r, &asset->rotationParams) ||
            !r.asset_field(&asset->unkMaterial, "WeaponDef.unkMaterial")) return false;
        if (!r.object(parent, "WeaponDef.parent")) return false;
        for (size_t i = 0; i < 2; ++i)
        {
            if (!r.string_field(&asset->accuracyGraphName[i], "WeaponDef.accuracyGraphName")) return false;
            std::remove_cv_t<std::remove_reference_t<decltype(parent->accuracyGraphKnotCount[0])>> parent_raw{};
            std::remove_cv_t<std::remove_reference_t<decltype(asset->originalAccuracyGraphKnotCount[0])>> original_raw{};
            size_t count, original_count;
            if (!r.load(&parent->accuracyGraphKnotCount[i], parent_raw, "WeaponDef.parentKnotCount") ||
                !r.load(&asset->originalAccuracyGraphKnotCount[i], original_raw, "WeaponDef.originalKnotCount") ||
                !r.count(parent_raw, count, "WeaponDef.parentKnotCount") ||
                !r.count(original_raw, original_count, "WeaponDef.originalKnotCount") || original_count < count)
                return r.fail("WeaponDef.originalKnotCountMismatch");
            if (!r.pointer_array(&asset->originalAccuracyGraphKnots[i], count, "WeaponDef.originalAccuracyGraphKnots",
                [&](const auto* value) { return r.scalar(value, "WeaponDef.originalAccuracyGraphKnots"); }, true)) return false;
        }
'''
    if native_type == 'WeaponCompleteDef':
        return '''
        WeaponDef* definition;
        if (!r.load(&asset->weapDef, definition, "WeaponCompleteDef.weapDef") || !validate(r, definition, asset)) return false;
        if (!r.counted_array(&asset->notetrackOverrides, &asset->numNotetrackOverrides, "WeaponCompleteDef.notetrackOverrides",
            [&](const auto* value) { return validate(r, value); }) ||
            !r.counted_array(&asset->notetrackSuitEntries, &asset->numNotetrackSuitEntries, "WeaponCompleteDef.notetrackSuitEntries",
            [&](const auto* value) { return validate(r, value); })) return false;
        for (size_t i = 0; i < 2; ++i)
        {
            std::remove_cv_t<std::remove_reference_t<decltype(asset->accuracyGraphKnotCount[0])>> raw{};
            size_t count;
            if (!r.load(&asset->accuracyGraphKnotCount[i], raw, "WeaponCompleteDef.accuracyGraphKnotCount") ||
                !r.count(raw, count, "WeaponCompleteDef.accuracyGraphKnotCount") ||
                !r.pointer_array(&asset->accuracyGraphKnots[i], count, "WeaponCompleteDef.accuracyGraphKnots",
                    [&](const auto* value) { return r.scalar(value, "WeaponCompleteDef.accuracyGraphKnots"); })) return false;
        }
'''
    return ''


def render(native_root):
    all_functions = []
    for filename, expected in HEADERS.items():
        text = source(Path(native_root) / NATIVE / filename)
        if hashlib.sha256(text.encode()).hexdigest() != expected:
            raise ValueError('Pinned native readset declaration changed: ' + filename)
    for filename, expected in SERIALIZERS.items():
        text = source(Path(native_root) / NATIVE / filename)
        if hashlib.sha256(text.encode()).hexdigest() != expected:
            raise ValueError('Pinned serializer source changed: ' + filename)
        all_functions.extend(functions(text, filename))
    types = [row[0] for row in all_functions]
    if len(types) != 41 or len(types) != len(set(types)) or 'WeaponDef' not in types or 'WeaponAttachment' not in types:
        raise ValueError('Finite complete serializer overload set changed')
    output = ['#pragma once', '// Generated finite readset for native fab935; see generate_definition_readset.py.',
              '// Macro fields and manually reviewed nested/loop readsets together precede serializer entry.',
              'namespace player_definition_readset', '{']
    for native_type in types:
        parent = ', const WeaponCompleteDef* parent' if native_type == 'WeaponDef' else ''
        output.append(f'    inline bool validate(Reader& r, const {native_type}* asset{parent});')
    output.extend(['    template<class T> inline bool optional(Reader& r, T* const* address, const char* field)', '    {',
                   '        T* value;', '        return r.json_token(4, field) && r.load(address, value, field) && (!value || validate(r, value));', '    }'])
    total_macros = 0
    for native_type, name, body, filename in all_functions:
        calls = MACRO.findall(body)
        total_macros += len(calls)
        output.append(f'    // {filename}: {name}({native_type}*), {len(calls)} exact macro fields.')
        parent = ', const WeaponCompleteDef* parent' if native_type == 'WeaponDef' else ''
        output.extend([f'    inline bool validate(Reader& r, const {native_type}* asset{parent})', '    {',
                       f'        if (!r.object(asset, "{native_type}")) return false;'])
        if native_type == 'WeaponDef':
            for field in ('animOverrides', 'sfxOverrides', 'vfxOverrides'):
                output.append(f'        if (!r.inline_objects(&asset->{field}, "WeaponDef.{field}", [&](const auto* value) {{ return validate(r, value); }})) return false;')
        for macro, args in calls:
            output.append('        if (!' + field_call(native_type, macro, args) + ') return false;')
        extra = manual(native_type).strip('\n')
        if extra:
            output.extend(extra.splitlines())
        output.extend(['        return true;', '    }'])
    if total_macros != 1203:
        raise ValueError('Complete pinned serializer macro coverage changed')
    output.extend(['}', ''])
    return '\n'.join(output), dict(functions=len(types), macro_fields=total_macros, serializer_sources=SERIALIZERS,
        declaration_sources=HEADERS, inline_asset_arrays={native+'.'+field:count for (native,field),count in INLINE_ASSET_ARRAYS.items()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    text, metadata = render(args.native_source_root)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(text)
    print(metadata)

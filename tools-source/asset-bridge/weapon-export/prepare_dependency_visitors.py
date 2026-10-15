"""Render an opt-in Source diff in memory. No output package, build or CLI wiring.

The production .inc files are mechanically derived from exact pinned upstream
traversals, with field/index origins and a sink instead of a zone. Re-rendering
must match the reviewed tracked files before a patched native source is returned.
"""
import hashlib
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIN = 'fab935826c898806855376662a8a03317b3ad8f1'
PREFIX = 'src/zonetool/zonetool/iw7/assets/'
PINS = {
    'weapondef.cpp': 'fc6defc7d4cdad56d3615ff2d13a1c6715f8b6e53dbdc7dd4be25ce4255050b5',
    'weaponattachment.cpp': '746d520c49f122bc650652da78deed45b091198bb10b30dc48bc6a38c9227e4c',
    'weapondef.hpp': '3c1f7b2fd4fd5ce7a4919dbabc6a5bf4e1ac1591029a89e29f3cf77c1821d084',
    'weaponattachment.hpp': 'ce53d8d720236d55e2b174cf40ef5d56158c958f1b0ed885b55fb820d7d825ff',
}


def require(value, message):
    if not value:
        raise ValueError(message)


def body(text, signature):
    require(text.count(signature) == 1, 'Unique exact native function required')
    start = text.index(signature)
    opening = text.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        require(end < len(text), 'Closed function required')
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return start, opening, end


def traversal(text, signature, name, native_type, prefix, attachment=False):
    _, opening, end = body(text, signature)
    lines = ['template<class Sink> bool ' + name + '(' + native_type + '* asset, Sink& sink)',
             '{', '    if (!sink.required(asset != nullptr)) return false;']
    for raw in text[opening + 1:end - 1].splitlines():
        raw = raw.strip()
        if not raw or raw.startswith('//') or 'auto* asset = this->asset_' in raw:
            continue
        if raw.startswith('load_depending_weapondef('):
            lines.append('    if (!visit_weapon_fields(asset->weapDef, sink)) return false;')
            continue
        loop = re.fullmatch(r'for \(auto i = (0u?); i < (.*); i\+\+\)', raw)
        if loop:
            count = loop[2]
            lines.append(f'    if (!sink.count(static_cast<size_t>({count}), {str(count != "21").lower()})) return false;')
            if attachment:
                arrays = {'asset->numModelVariations': ('worldModelVariations', 'viewModelVariations'),
                          'asset->numWorldModelCamoMaterials': ('worldModelCamoMaterials',),
                          'asset->numViewModelCamoMaterials': ('viewModelCamoMaterials',),
                          'asset->numReticles': ('reticles',), 'asset->numAltReticles': ('altReticles',)}[count]
                for array in arrays:
                    lines.append(f'    if (!sink.required(!({count}) || asset->{array} != nullptr)) return false;')
            lines.append('    ' + raw)
            continue
        if raw in ('{', '}'):
            lines.append('    ' + raw)
            continue
        call = re.fullmatch(r'(WEAPON_SUBASSET_DEPENDING\w*|ATTACHMENT_(?:ATT_)?SUBASSET_DEPENDING\w*)\((.*)\);', raw)
        require(call, 'Unmapped traversal statement: ' + raw)
        macro, args = call[1], [arg.strip() for arg in call[2].split(',')]
        nested = macro.startswith('ATTACHMENT_ATT_')
        field = args[0] + '->' + args[1] if nested else args[0]
        path = prefix + field.replace('->', '.').replace('[i]', '[]')
        index = 'static_cast<unsigned>(i)' if '[i]' in field else '0'
        guard = f'asset->{args[0]} && ' if nested else ''
        if macro.endswith('_ARR'):
            field, asset_type, count = args if 'FXCOMBINED' not in macro else (args[0], None, args[1])
            inline = '_FIELD_ARR' in macro
            lines.append(f'    if (!sink.count(static_cast<size_t>({count}), {str(count.startswith("asset->")).lower()})) return false;')
            if not inline:
                lines.append(f'    if (!sink.required(!({count}) || asset->{field} != nullptr)) return false;')
                lines.append(f'    if (asset->{field})')
            lines += ['    {', f'        for (auto idx = 0u; idx < (unsigned int){count}; ++idx)', '        {']
            origin = '{"' + prefix + field + '[]", idx}'
            if 'FXCOMBINED' in macro:
                lines.append(f'            if (!emit_fx(asset->{field}[idx], {origin}, sink)) return false;')
            else:
                lines.append(f'            if (asset->{field}[idx] && !sink.asset({asset_type}, asset->{field}[idx]->name, {origin})) return false;')
            lines += ['        }', '    }']
        elif 'FXCOMBINED' in macro:
            origin = '{"' + path + '", ' + index + '}'
            lines.append(f'    if ({guard}!emit_fx(asset->{field}, {origin}, sink)) return false;')
        else:
            origin = '{"' + path + '", ' + index + '}'
            lines.append(f'    if ({guard}asset->{field} && !sink.asset({args[-1]}, asset->{field}->name, {origin})) return false;')
    lines += ['    return true;', '}', '']
    return '\n'.join(lines)


SIGNATURES = {
    'weapondef.cpp': ('void weapon_def::load_depending_weapondef(WeaponDef* asset, zone_base* zone)',
                      'void weapon_def::load_depending(zone_base* zone)'),
    'weaponattachment.cpp': ('void weapon_attachment::load_depending(zone_base* zone)',),
}


def derive(sources):
    """Text-only trusted Source inputs. Never parse weapon data or touch a tool."""
    require(set(sources) == set(PINS), 'Exactly four pinned native Source texts required')
    for name, sha in PINS.items():
        require(isinstance(sources[name], str) and len(sources[name].encode()) <= 2 * 1024 * 1024,
                'Bounded Source text required')
        require(hashlib.sha256(sources[name].encode()).hexdigest() == sha, 'Pinned Source differs: ' + name)
    weapon, attachment = sources['weapondef.cpp'], sources['weaponattachment.cpp']
    provenance = '// Derived from maxis0191/x64-zt ' + PIN + '.\n// Preserve original author/license notices in the native source.\n'
    return {
        'native_weapon_dependencies.inc': provenance + traversal(weapon, SIGNATURES['weapondef.cpp'][0],
            'visit_weapon_fields', 'WeaponDef', 'weapDef.') + traversal(weapon, SIGNATURES['weapondef.cpp'][1],
            'visit_weapon', 'WeaponCompleteDef', ''),
        'native_attachment_dependencies.inc': provenance + traversal(attachment, SIGNATURES['weaponattachment.cpp'][0],
            'visit_attachment', 'WeaponAttachment', '', True),
    }


def render(sources):
    derived = derive(sources)
    for name, text in derived.items():
        require(text == (HERE / name).read_text(encoding='utf-8'), 'Reviewed production walker differs: ' + name)
    result = dict(sources)
    for filename, signatures in SIGNATURES.items():
        text = result[filename]
        for signature in reversed(signatures):
            start, _, end = body(text, signature)
            function = 'visit_attachment' if filename == 'weaponattachment.cpp' else (
                'visit_weapon_fields' if 'load_depending_weapondef' in signature else 'visit_weapon')
            pointer = 'asset' if function == 'visit_weapon_fields' else 'this->asset_'
            replacement = signature + '\n\t{\n\t\tneutral_dependencies::LegacyAdapter<zone_base> sink{zone};\n' + \
                '\t\t(void)neutral_dependencies::' + function + '(' + pointer + ', sink);\n\t}'
            text = text[:start] + replacement + text[end:]
        # Remove only now-unused dependency macros; keep every other native byte.
        macro = '#define ' + ('ATTACHMENT' if filename == 'weaponattachment.cpp' else 'WEAPON') + '_SUBASSET_DEPENDING('
        start = text.index(macro)
        stop = text.index('void ', start)
        text = text[:start] + text[stop:]
        anchor = '#include "' + filename.removesuffix('.cpp') + '.hpp"'
        require(text.count(anchor) == 1, 'One header insertion site required')
        result[filename] = text.replace(anchor, anchor + '\n#include "native_neutral_dependencies.hpp"', 1)
    return result

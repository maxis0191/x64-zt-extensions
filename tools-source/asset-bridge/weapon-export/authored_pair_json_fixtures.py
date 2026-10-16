"""Source fixture bytes/oracles for the future real-core C++ witness.

These are entirely authored data using the existing owned fixture builders,
never captured definitions. Production PR215/216 validate every original buffer
before any C++ Source is emitted. No I/O, process, arena or runtime authority.
"""
import hashlib

import neutral_pair_bodies as validation
from test_native_body_schema import private_pair
from test_neutral_pair_inputs import CSV, encode, fixture

# Complete owned Source support for the C++ witness. Future Source capsules copy
# this list, including Inventory's transitive walkers; generated headers are
# supplied separately by the real core renderer and render_header().
FIXTURE_SOURCE_FILES = (
    'test_authored_pair_json.cpp',
    'native_pair_session.hpp',
    'native_neutral_dependencies.hpp',
    'native_definition_access.hpp',
    'native_weapon_dependencies.inc',
    'native_attachment_dependencies.inc',
)

FX_NAME = 'authored_fx0001'
OTHER_FX = 'authored_fx0002'
RETICLE = 'authored_rt0001'


def _approved_case(label, rename=False, swap=False):
    weapon, attachment = private_pair()
    fields = weapon['weapDef']
    fields['projExplosionEffect'] = {'type': 1 if swap else 0, 'fx': OTHER_FX if rename else FX_NAME}
    fields['projDudEffect'] = {'type': 0 if swap else 1, 'fx': FX_NAME}
    fields['knifeAttachTagOverride'] = 'authored_wtag01'
    attachment['reticles'] = [RETICLE]
    attachment['attachPoint'] = 'authored_atag01'
    report, wr, ar = fixture(encode(weapon), encode(attachment))
    rr = encode(report)
    raw = (rr, wr, ar, CSV)
    pins = tuple((len(value), hashlib.sha256(value).hexdigest()) for value in raw)
    validation.validate_private_pair_bodies(rr, *pins[0], wr, ar, CSV)
    trace = validation._inspect(weapon, attachment, alignment=True)
    # These are layout diagnostics, not admission or a new schema token.
    woffset = next(offset for _path, ty, offset, _size, _align in trace.events if ty == 'WeaponDef')
    aoffset = next(offset for path, ty, offset, _size, _align in trace.events if path == 'attachment' and ty == 'WeaponAttachment')
    # Literal independent oracle; do not use a walker to compute expected rows.
    refs = [('ASSET_TYPE_ATTACHMENT', 'sdk_shredder_clone_pap_zm', True),
            ('ASSET_TYPE_VFX' if swap else 'ASSET_TYPE_FX', OTHER_FX if rename else FX_NAME, False),
            ('ASSET_TYPE_FX' if swap else 'ASSET_TYPE_VFX', FX_NAME, False),
            ('ASSET_TYPE_RETICLE', RETICLE, False)]
    edges = [(0, 'weapon', 'attachments6[0]'), (1, 'weapon', 'weapDef.projExplosionEffect'),
             (2, 'weapon', 'weapDef.projDudEffect'), (3, 'attachment', 'reticles[0]')]
    return dict(label=label, raw=raw, pins=pins, capacity=trace.offset,
                weapondef_offset=woffset, attachment_offset=aoffset,
                references=refs, edges=edges, occurrences=4)


def cases():
    """Only these three explicitly authored variants have trusted Source pins."""
    return (_approved_case('base'), _approved_case('renamed', rename=True), _approved_case('swapped', swap=True))


def validate_originals(raw, pins):
    """Source-only refusal causals; a mutable verdict never enters the C++."""
    if type(raw) is not tuple or len(raw) != 4 or type(pins) is not tuple or len(pins) != 4:
        raise ValueError('Four original buffers and external Source pins required')
    for value, (size, digest) in zip(raw, pins):
        if type(value) is not bytes or type(size) is not int or len(value) != size or hashlib.sha256(value).hexdigest() != digest:
            raise ValueError('Original Source binding differs')
    validation.validate_private_pair_bodies(raw[0], *pins[0], raw[1], raw[2], raw[3])


def render_header():
    approved = cases()  # Every PR215/216 check finishes before output creation.
    lines = ['#pragma once', '// Authored test Source only. Thirteen report flags remain false.',
             'namespace authored_pair_fixture {', 'inline const AuthoredCase approved_cases[] = {']
    for case in approved:
        lines.append('  {"' + case['label'] + '", {{')
        for raw in case['raw']:
            text = raw.decode('utf-8', errors='strict')
            if ')IW7AUTH"' in text or '\0' in text:
                raise ValueError('Authored literal delimiter or NUL refused')
            lines.append('    R"IW7AUTH(' + text + ')IW7AUTH",')
        lines.append('  }}, {{')
        for size, digest in case['pins']:
            lines.append('    {' + str(size) + ', "' + digest + '"},')
        lines.append('  }}, ' + ', '.join(str(case[key]) for key in ('capacity', 'weapondef_offset', 'attachment_offset')) + ', {{')
        for ty, name, owned in case['references']:
            lines.append('    {' + ty + ', "' + name + '", ' + ('true' if owned else 'false') + '},')
        lines.append('  }}, {{')
        for ref, owner, path in case['edges']:
            lines.append('    {' + str(ref) + ', nd::Owner::' + owner + ', "' + path + '"},')
        lines.append('  }}, ' + str(case['occurrences']) + '},')
    lines += ['};', '}']
    return '\n'.join(lines) + '\n'

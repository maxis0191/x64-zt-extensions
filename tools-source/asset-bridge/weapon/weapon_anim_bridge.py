"""Convert H1 weapon animation references into IW7 animpkg JSON.

Only reference-slot structure is converted. Clips, timers, notetracks, rigs,
attachments, and the rest of the weapon are not converted or game-validated.
The CLI requires explicit retained IW7 templates and their provenance files.
"""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import re

from source_contract import bounded, build, digest, require

FIELDS = {'szXAnims':'base', 'szXAnimsRightHanded':'right', 'szXAnimsLeftHanded':'left'}
SCALARS = ('meleeAnimType', 'meleeAnimPrimaryCount', 'meleeAnimAltCount')
PACKAGE_KEYS = {*SCALARS, 'fireAnimTimesMs', 'anims', 'timers', 'footsteps'}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key: '+key)
        result[key] = value
    return result


def read_json(path):
    data = bounded(path)
    value = json.loads(data.decode('utf-8-sig'), object_pairs_hook=unique_object,
                       parse_constant=lambda value: require(False, 'Nonfinite JSON number'))
    return value, digest(data)


def integer(value, low, high):
    require(type(value) is int and low <= value <= high, 'Integer outside native scalar range')


def reference(value):
    require(type(value) is str and len(value) <= 240, 'Bounded string asset reference required')
    if value:
        require(re.fullmatch(r'[A-Za-z0-9_./@-]+', value) is not None and
                all(part not in ('', '.', '..') for part in value.split('/')),
                'Unsupported/ambiguous asset reference: '+value)


def validate_package(package, contract):
    require(type(package) is dict and set(package) == PACKAGE_KEYS, 'IW7 native animpkg fields required')
    for field in SCALARS:
        integer(package[field], -(2**31), 2**31-1)
    times = package['fireAnimTimesMs']
    require(type(times) is list and len(times) == 4, 'Exactly four fireAnimTimesMs required')
    for value in times:
        integer(value, -(2**31), 2**31-1)
    anims = package['anims']
    require(type(anims) is dict and set(anims) == set(contract['iw7_slots']),
            'Explicit 260-slot IW7 template required')
    for value in anims.values():
        reference(value)
    timers = package['timers']
    if timers is not None:
        require(type(timers) is dict and set(timers) == set(contract['timer_fields']),
                'Complete IW7 timer fields required; no inferred defaults')
        for field, kind in contract['timer_fields'].items():
            if kind == 'bool':
                require(type(timers[field]) is bool, 'Native timer bool required')
            else:
                integer(timers[field], 0, 65535)
    footsteps = package['footsteps']
    if footsteps is not None:
        require(type(footsteps) is dict and set(footsteps) == {'footstep'} and
                type(footsteps['footstep']) is list and len(footsteps['footstep']) == 9,
                'Nine IW7 footstep records required')
        for record in footsteps['footstep']:
            require(type(record) is dict and set(record) == {'leftCount', 'step', 'movement'},
                    'Invalid footstep record fields')
            integer(record['leftCount'], -(2**31), 2**31-1)
            for key, flag in (('step', 'isLeft'), ('movement', 'isLeadIn')):
                require(type(record[key]) is list and len(record[key]) == 4, 'Four footstep samples required')
                for sample in record[key]:
                    require(type(sample) is dict and set(sample) == {'time', flag}, 'Invalid footstep sample')
                    require(type(sample[flag]) is bool, 'Footstep bool required')
                    require(type(sample['time']) in (int, float) and math.isfinite(sample['time']) and
                            abs(sample['time']) <= 3.402823466e38, 'Finite float32-range footstep time required')


def convert(weapon, templates, prefix, contract):
    """Pure conversion; test callers must identify synthetic input separately."""
    require(type(prefix) is str and re.fullmatch(r'[a-z][a-z0-9_]{0,95}', prefix) is not None,
            'Portable lowercase package prefix required')
    require(type(weapon) is dict and all(field in weapon for field in FIELDS), 'Three explicit H1 animation tables required')
    require(weapon.get('animOverrides') in (None, []) and weapon.get('numAnimOverrides', 0) == 0,
            'Attachment animation overrides require a separate conversion')
    active = {field for field in FIELDS if weapon[field] is not None}
    require(active and set(templates) == active, 'One explicit IW7 template per active H1 table required')
    h1_keys = {slot['key'] for slot in contract['h1_slots']}
    packages, links, conversions, dependencies, retained = {}, {}, [], {}, {}
    for field, suffix in FIELDS.items():
        if field not in active:
            links[field] = ''
            continue
        donor = weapon[field]
        require(type(donor) is dict and set(donor) == h1_keys, 'Complete exact H1 190-slot table required: '+field)
        template = templates[field]
        validate_package(template, contract)
        output = deepcopy(template)
        mapped_targets = set()
        for source_index, slot in enumerate(contract['h1_slots']):
            value = donor[slot['key']]
            reference(value)
            index = slot['iw7_index']
            if index is None:
                require(not value, 'Nonempty H1 slot has no exact IW7 enum match: '+slot['key'])
                continue
            target_key = contract['iw7_slots'][index]
            require(target_key == slot['symbol'] and target_key not in mapped_targets, 'Ambiguous slot mapping')
            mapped_targets.add(target_key)
            # Empty donor slots also clear common slots: no silent base-clip fallback.
            output['anims'][target_key] = value
            if value:
                conversions.append({'field':field, 'source_key':slot['key'], 'source_index':source_index,
                                    'target_key':target_key, 'target_index':index, 'clip':value})
                dependencies.setdefault(value, set()).add('h1-unconverted-clip')
        retained[field] = [key for key, value in output['anims'].items() if key not in mapped_targets and value]
        for key in retained[field]:
            dependencies.setdefault(output['anims'][key], set()).add('iw7-template-clip')
        name = prefix+'_'+suffix
        links[field] = name
        validate_package(output, contract)
        packages[name] = output
    folded = {}
    for name in dependencies:
        require(name.casefold() not in folded or folded[name.casefold()] == name, 'Case-ambiguous clip references')
        folded[name.casefold()] = name
    report = {'schema':'iw7.weapon-animation-bridge/1', 'source_pin':contract['source_pin'],
              'scope':'animation-reference slots only', 'conversions':conversions,
              'retained_iw7_only_slots':retained,
              'dependencies':[{'name':name, 'origins':sorted(origins)} for name, origins in sorted(dependencies.items())],
              'unconverted_h1_fields':sorted(set(weapon)-set(FIELDS)),
              'nonanimation_template_fields_preserved':True,
              'clip_conversion_verified':False, 'native_parser_executed':False,
              'fastfile_built':False, 'playable_weapon_verified':False}
    return {'packages':packages, 'weapondef_links':{'weapDef':links}, 'report':report}


def prepare(request_path, source_root):
    """Validate/bind every file before creating any output directory."""
    request, request_hash = read_json(request_path)
    contract, contract_hash = read_json(Path(__file__).with_name('slot-contract.json'))
    require(build(source_root) == contract, 'Retained source differs from pinned contract')
    require(Path(request['h1_weapon']).is_absolute(), 'Absolute retained H1 dump path required')
    weapon, weapon_hash = read_json(request['h1_weapon'])
    templates, receipts = {}, {}
    require(type(request['templates']) is dict, 'Explicit native template map required')
    for field, spec in request['templates'].items():
        require(field in FIELDS and spec['source_kind'] == 'iw7-native-animpkg-dump',
                'Retained IW7 native dump required; fixtures are not production templates')
        require(Path(spec['path']).is_absolute() and Path(spec['evidence_path']).is_absolute(),
                'Absolute retained template/provenance paths required')
        template, template_hash = read_json(spec['path'])
        require(template_hash == spec['sha256'], 'Template digest mismatch')
        evidence = bounded(spec['evidence_path'])
        require(evidence and digest(evidence) == spec['evidence_sha256'], 'Template provenance file digest mismatch')
        templates[field] = template
        receipts[field] = {'path':str(Path(spec['path']).resolve()), 'sha256':template_hash,
                           'source_kind':spec['source_kind'],
                           'evidence_path':str(Path(spec['evidence_path']).resolve()),
                           'evidence_sha256':digest(evidence),
                           'native_origin_independently_verified':False}
    result = convert(weapon, templates, request['package_prefix'], contract)
    result['report'].update({'request_sha256':request_hash, 'h1_weapon_sha256':weapon_hash,
                             'slot_contract_sha256':contract_hash, 'templates':receipts,
                             'template_provenance':'Caller-selected retained dump and evidence, byte-bound; source origin requires review'})
    return result


def write_outputs(result, root):
    # An existing destination is never modified, even when empty.
    root = Path(root)
    require(not root.exists(), 'Output directory must not exist')
    payloads = {'animpkg/'+name+'.json':data for name, data in result['packages'].items()}
    payloads['weapondef-links.fragment.json'] = result['weapondef_links']
    payloads['conversion-report.local.json'] = result['report']
    encoded = {name:(json.dumps(value, indent=2, allow_nan=False)+'\n').encode() for name, value in payloads.items()}
    require(sum(map(len, encoded.values())) <= 8*1024*1024, 'Output exceeds 8 MiB source envelope')
    root.mkdir(parents=True, exist_ok=False)
    for name, data in encoded.items():
        path = root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(data)
    return {name:digest(data) for name, data in encoded.items()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True, type=Path)
    parser.add_argument('--source-root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        result = prepare(args.request, args.source_root)
        hashes = write_outputs(result, args.output)
        print(json.dumps({'status':'source-conversion-only', 'outputs':hashes}, indent=2))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, str(error)+'\n')

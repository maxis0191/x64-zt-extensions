"""Check bounded Ray Gun reference metadata; never read or emit game payloads."""
import argparse
import json
from pathlib import Path
import re

LIMIT = 64 * 1024
PIN = 'fab935826c898806855376662a8a03317b3ad8f1'
FIELDS = {'view': 'weapDef.gunXModel', 'world': 'weapDef.worldModel',
          'hands': 'weapDef.handXModel'}
PACKAGES = ['weapDef.szXAnims', 'weapDef.szXAnimsRightHanded',
            'weapDef.szXAnimsLeftHanded']
SLOTS = {'idle': ('WEAP_ANIM_IDLE', 107), 'empty_idle': ('WEAP_ANIM_EMPTY_IDLE', 108),
         'fire': ('WEAP_ANIM_FIRE', 109), 'reload': ('WEAP_ANIM_RELOAD', 171),
         'reload_empty': ('WEAP_ANIM_RELOAD_EMPTY', 172),
         'raise': ('WEAP_ANIM_RAISE', 179), 'drop': ('WEAP_ANIM_DROP', 182),
         'ads_fire': ('WEAP_ANIM_ADS_FIRE', 207), 'ads_up': ('WEAP_ANIM_ADS_UP', 249),
         'ads_down': ('WEAP_ANIM_ADS_DOWN', 250)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def keys(value, expected, label):
    require(isinstance(value, dict) and set(value) == set(expected),
            f'{label}: unexpected or missing fields')


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def read_metadata(path):
    # The bound applies to the bytes actually read, including a growing file.
    with Path(path).open('rb') as stream:
        raw = stream.read(LIMIT + 1)
    require(len(raw) <= LIMIT, 'Metadata exceeds 64 KiB')
    return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique_pairs)


def name(value):
    require(isinstance(value, str) and len(value) <= 128 and
            re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_./-]*', value) is not None and
            '..' not in value and not value.endswith('/'), 'Invalid exact asset/tag name')
    return value


def names(values):
    if values is None:
        return None
    require(isinstance(values, list) and 0 < len(values) <= 512, 'Invalid name array')
    checked = [name(value) for value in values]
    require(len({value.casefold() for value in checked}) == len(checked),
            'Duplicate or case-ambiguous bone/channel names')
    return checked


def check(plan, slot_contract):
    keys(plan, ('schema', 'source_pin', 'private_weapon_proposals', 'weapon_name_candidates', 'evidence',
                'models', 'clips', 'tags', 'recipient'), 'Plan')
    require(plan['schema'] == 'iw7.raygun-source-plan/1' and plan['source_pin'] == PIN,
            'Unreviewed source schema/pin')
    require(plan['private_weapon_proposals'] == ['sdk_raygun_zm', 'sdk_raygun_pap_zm'],
            'Private IDs are proposals; changed IDs require coordination')
    candidates = plan['weapon_name_candidates']
    require(isinstance(candidates, list) and len(candidates) <= 8,
            'Invalid bounded weapon candidate list')
    for candidate in candidates:
        keys(candidate, ('weapon_name', 'upgraded_name', 'source_kind', 'source_url',
                         'runtime_observed'), 'Weapon candidate')
        name(candidate['weapon_name'])
        name(candidate['upgraded_name'])
        require(candidate['source_kind'] == 'third-party-bo3-mod-table' and
                candidate['runtime_observed'] is False and
                isinstance(candidate['source_url'], str) and
                re.fullmatch(r'https://github\.com/[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+/'
                             r'blob/[0-9a-f]{40}/[A-Za-z0-9_./-]+(?:#L[0-9]+)?',
                             candidate['source_url']) is not None,
                'Candidate requires a pinned source; runtime promotion is refused')
    require(slot_contract['source_pin'] == PIN and len(slot_contract['iw7_slots']) == 260,
            'Recipient slot contract changed')
    recipient = plan['recipient']
    keys(recipient, ('model_fields', 'package_fields', 'slots', 'muzzle_tag_expectation'),
         'Recipient')
    require(recipient['model_fields'] == FIELDS and recipient['package_fields'] == PACKAGES
            and recipient['muzzle_tag_expectation'] == 'tag_flash',
            'Recipient model/package/tag expectation changed')
    require(recipient['slots'] == {role: list(value) for role, value in SLOTS.items()},
            'Recipient slot mapping changed')
    for symbol, index in SLOTS.values():
        require(slot_contract['iw7_slots'][index] == symbol, 'Recipient slot identity mismatch')
    keys(plan['models'], FIELDS, 'Model roles')
    keys(plan['clips'], SLOTS, 'Clip roles')
    keys(plan['tags'], ('view_muzzle', 'world_muzzle'), 'Tag roles')
    require(isinstance(plan['evidence'], dict), 'Evidence registry must be an object')
    for identifier, evidence in plan['evidence'].items():
        name(identifier)
        keys(evidence, ('source_kind', 'receipt_sha256', 'observed_field'), 'Evidence')
        require(evidence['source_kind'] == 'retained-bo3-metadata' and
                isinstance(evidence['receipt_sha256'], str) and
                re.fullmatch(r'[0-9a-f]{64}', evidence['receipt_sha256']) is not None and
                isinstance(evidence['observed_field'], str) and
                0 < len(evidence['observed_field']) <= 256 and
                not any(ord(char) < 32 for char in evidence['observed_field']),
                'Invalid evidence declaration')

    unresolved, references, model_bones = [], [], {}
    spellings = {}
    for category, metadata_key in (('models', 'bone_names'), ('clips', 'channel_names')):
        for role, asset in plan[category].items():
            if asset is None:
                unresolved.append(f'{category}.{role}.identity')
                continue
            keys(asset, ('name', 'evidence_ref', metadata_key), f'{category}.{role}')
            asset_name = name(asset['name'])
            require(isinstance(asset['evidence_ref'], str) and
                    asset['evidence_ref'] in plan['evidence'], 'Unbound evidence reference')
            spelling_key = (category, asset_name.casefold())
            require(spelling_key not in spellings or spellings[spelling_key] == asset_name,
                    'Case-ambiguous asset identity')
            spellings[spelling_key] = asset_name
            resolved_names = names(asset[metadata_key])
            if resolved_names is None:
                unresolved.append(f'{category}.{role}.{metadata_key}')
            if category == 'models':
                model_bones[role] = resolved_names
            references.append({'role': f'{category}.{role}', 'name': asset_name,
                               'evidence_ref': asset['evidence_ref']})

    # A compatible hands model is not assumed merely from an asset name.
    view_names = model_bones.get('view')
    hands_names = model_bones.get('hands')
    for role, clip in plan['clips'].items():
        if clip is None or clip['channel_names'] is None:
            continue
        if view_names is None or hands_names is None:
            unresolved.append(f'clips.{role}.view_hands_binding')
        else:
            require(set(clip['channel_names']) <= set(view_names + hands_names),
                    f'Clip {role}: channel absent from declared view/hands names')
    for role, tag in plan['tags'].items():
        if tag is None:
            unresolved.append(f'tags.{role}')
            continue
        keys(tag, ('source_name', 'evidence_ref'), f'Tag {role}')
        source_name = name(tag['source_name'])
        require(isinstance(tag['evidence_ref'], str) and
                tag['evidence_ref'] in plan['evidence'], 'Unbound tag evidence')
        bones = model_bones.get(role.split('_')[0])
        require(bones is not None and source_name in bones,
                f'Tag {role}: absent from declared model names')

    return {'schema': 'iw7.raygun-source-handoff/1', 'source_pin': PIN,
            'private_weapon_ids_are_proposals': True, 'references': references,
            'weapon_name_candidates': candidates,
            'unresolved_metadata': unresolved,
            'metadata_declarations_complete': not unresolved,
            'recipient_slots_checked': True, 'evidence_content_read': False,
            'provenance_independently_verified': False,
            'hierarchy_bind_influences_verified': False, 'clip_semantics_verified': False,
            'notetrack_delivery_verified': False, 'native_payload_verified': False,
            'textures_verified': False, 'render_verified': False,
            'playable_weapon_verified': False, 'pap_verified': False,
            'projectile_physics_verified': False, 'ready': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path,
                        default=Path(__file__).with_name('source-plan.json'))
    args = parser.parse_args()
    slot_path = Path(__file__).resolve().parents[3] / 'weapon' / 'slot-contract.json'
    report = check(read_metadata(args.request), read_metadata(slot_path))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()

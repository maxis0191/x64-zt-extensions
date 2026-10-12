"""Pure proposed T7-to-IW7 request contract. No native adapter or stock access."""
import hashlib
import re

SCHEMA = 'iw7.t7-iw7-resident-model-request/1'
FIELDS = {'schema', 'target', 'profile', 'zone', 'model', 'lod'}
PROFILE = 'resident-rigid-one-lod'
PROPOSED_OPTION = '-t7-iw7-model'
SOURCE_ENGINE = 'BlackOps3_UnrankedDedicatedServer.exe'
RESERVED = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}


def require(value, message):
    if not value: raise ValueError(message)


def safe_name(value, *, zone=False):
    require(type(value) is str and 1 <= len(value) <= (64 if zone else 128), 'Name length/type refused')
    require(re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_/-]*', value) is not None, 'Exact portable ASCII name required')
    parts = value.split('/')
    require(len(parts) <= (1 if zone else 8) and all(parts), 'Name path depth/empty segment refused')
    require(all(len(part) <= 64 and part.upper() not in RESERVED for part in parts), 'Unsafe name segment refused')
    return value


def validate_request(value):
    require(type(value) is dict and set(value) == FIELDS, 'Exact request fields required')
    require(value['schema'] == SCHEMA and value['target'] == 'iw7' and value['profile'] == PROFILE,
            'Only the explicit resident T7-to-IW7 profile is proposed')
    safe_name(value['zone'], zone=True)
    safe_name(value['model'])
    require(type(value['lod']) is int and 0 <= value['lod'] <= 5, 'Explicit integer LOD 0..5 required')
    return value.copy()


def make_request(zone, model, lod):
    return validate_request({'schema': SCHEMA, 'target': 'iw7', 'profile': PROFILE,
                             'zone': zone, 'model': model, 'lod': lod})


def command_review(value):
    value = validate_request(value)
    key_input = f"{value['zone']}\n{value['model']}\n{value['lod']}".encode('ascii')
    return {'schema': 'iw7.t7-iw7-boot-command-review/1',
            'proposed_arguments': [PROPOSED_OPTION, value['zone'], value['model'], str(value['lod'])],
            'source_engine': SOURCE_ENGINE, 'expected_source_mode': 't7', 'target': 'iw7',
            'exact_model_names': [value['model']], 'selected_lod': value['lod'],
            'private_output_root_key': 't7_iw7_'+hashlib.sha256(key_input).hexdigest(),
            'xpak_payload_files_allowed': [], 'stock_access_performed': False,
            'supported_by_unmodified_base_cli': False, 'native_adapter_source_prepared': True,
            'native_adapter_compiled': False, 'native_patch_applied': False,
            'native_go': False, 'native_executed': False, 'ready': False}


def parse_proposed_arguments(arguments):
    """Review parser only; do not pass this proposal to the unmodified binary."""
    require(type(arguments) is list and len(arguments) == 4 and all(type(x) is str for x in arguments),
            'Exactly one proposed option, zone, model and LOD required')
    require(arguments[0] == PROPOSED_OPTION and re.fullmatch(r'[0-5]', arguments[3]) is not None,
            'Explicit target option and canonical LOD required')
    return make_request(arguments[1], arguments[2], int(arguments[3]))

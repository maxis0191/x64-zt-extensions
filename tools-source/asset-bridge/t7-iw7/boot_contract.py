"""Pure proposed T7-to-IW7 request contract. No native adapter or stock access."""
import hashlib
import re

SCHEMA = 'iw7.t7-iw7-resident-model-request/1'
FIELDS = {'schema', 'target', 'profile', 'zone', 'model', 'lod'}
PROFILE = 'resident-rigid-one-lod'
PROPOSED_OPTION = '-t7-iw7-model'
PROPOSED_OPTION_V2 = '-t7-iw7-model-v2'
SOURCE_ENGINE = 'BlackOps3_UnrankedDedicatedServer.exe'
RESERVED = {'CON', 'PRN', 'AUX', 'NUL', 'CONIN$', 'CONOUT$', 'CLOCK$',
            *(f'COM{i}' for i in range(10)), *(f'LPT{i}' for i in range(10))}


def require(value, message):
    if not value: raise ValueError(message)


def safe_name(value, *, zone=False):
    require(type(value) is str and 1 <= len(value) <= (64 if zone else 255), 'Name length/type refused')
    require(all(0x20 <= ord(c) < 0x7f and c not in ':<>"|?*' for c in value), 'Exact portable ASCII name required')
    if zone:
        require(re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_-]*', value) is not None, 'Flat zone token required')
    else:
        require(not value.startswith(','), 'Referenced-asset alias refused')
    parts = re.split(r'[/\\]', value)
    for part in parts:
        require(part and part not in ('.', '..') and part[-1] not in '. ', 'Unsafe path segment')
        require(part.split('.', 1)[0].rstrip(' ').upper() not in RESERVED, 'Windows device alias refused')
    return value


def validate_request(value):
    if type(value) is dict and value.get('schema') == 'iw7.t7-iw7-selected-streamed-request/1':
        from streamed_contract import validate_request as validate_streamed_request
        return validate_streamed_request(value)
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


def export_option(version):
    require(type(version) is int and version in (1, 2), 'Explicit export version 1 or 2 required')
    return PROPOSED_OPTION if version == 1 else PROPOSED_OPTION_V2


def command_review(value, *, version=1, request_path=None):
    value = validate_request(value)
    if value['schema'] != SCHEMA:
        from streamed_contract import command_review as review_streamed
        return review_streamed(value, request_path)
    option = export_option(version)
    key_input = f"{value['zone']}\n{value['model']}\n{value['lod']}".encode('ascii')
    return {'schema': 'iw7.t7-iw7-boot-command-review/1',
            'proposed_arguments': [option, value['zone'], value['model'], str(value['lod'])],
            'source_engine': SOURCE_ENGINE, 'expected_source_mode': 't7', 'target': 'iw7',
            'exact_model_names': [value['model']], 'selected_lod': value['lod'],
            'private_output_root_key': 't7_iw7_'+hashlib.sha256(key_input).hexdigest(),
            'xpak_payload_files_allowed': [], 'stock_access_performed': False,
            'supported_by_unmodified_base_cli': False, 'native_adapter_source_prepared': True,
            'native_adapter_compiled': False, 'native_patch_applied': False,
            'native_go': False, 'native_executed': False, 'ready': False}


def parse_proposed_arguments(arguments, *, version=1):
    """Review parser only; do not pass this proposal to the unmodified binary."""
    require(type(arguments) is list and len(arguments) == 4 and all(type(x) is str for x in arguments),
            'Exactly one proposed option, zone, model and LOD required')
    require(arguments[0] == export_option(version) and re.fullmatch(r'[0-5]', arguments[3]) is not None,
            'Explicit target option and canonical LOD required')
    return make_request(arguments[1], arguments[2], int(arguments[3]))

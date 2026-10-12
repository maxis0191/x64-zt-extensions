"""Pure receipt validator; this cannot qualify engine/job/stock or rendered bytes."""
import re
from boot_contract import PROFILE, command_review, require, safe_name, validate_request

FIELDS = {'schema', 'requested_zone', 'source_model', 'selected_source_lod', 'output_model_name',
          'output_mesh_name', 'output_root_key', 'target', 'profile', 'geometry_profile',
          'root_bone_name', 'selected_counts',
          'material_dependencies', 'model', 'mesh', 'zonetool_xpak_helper_reads_allowed', 'engine_io_verified',
          'dependency_payloads_verified', 'asset_zone_ownership_verified',
          'serialized_parse_verified', 'runtime_verified', 'ready'}


def validate_export(value, request):
    request = validate_request(request)
    require(type(value) is dict and set(value) == FIELDS, 'Exact export receipt fields required')
    require(value['schema'] == 'iw7.t7-iw7-resident-export/1' and value['target'] == 'iw7' and
            value['profile'] == PROFILE and value['geometry_profile'] == 't7-iw7-resident-static-v1',
            'Unexpected export/geometry profile')
    require(value['requested_zone'] == request['zone'] and value['source_model'] == request['model'] and
            type(value['selected_source_lod']) is int and value['selected_source_lod'] == request['lod'],
            'Export differs from selected request')
    require(value['output_model_name'] == request['model'], 'Source model was renamed')
    mesh = safe_name(value['output_mesh_name'])
    require(value['output_root_key'] == command_review(request)['private_output_root_key'], 'Private root key differs')
    require(type(value['material_dependencies']) is list and len(value['material_dependencies']) == 1,
            'Exactly one unresolved material name required')
    safe_name(value['material_dependencies'][0])
    bone = value['root_bone_name']
    require(type(bone) is str and 1 <= len(bone) <= 255 and all(0x20 <= ord(c) < 0x7f for c in bone),
            'Exact bounded engine root-bone name required')
    counts = value['selected_counts']
    require(type(counts) is dict and set(counts) == {'bones', 'roots', 'surfaces', 'vertices', 'triangles'},
            'Exact selected geometry counts required')
    for key, low, high in (('bones',1,1), ('roots',1,1), ('surfaces',1,1),
                           ('vertices',3,65535), ('triangles',1,65535)):
        require(type(counts[key]) is int and low <= counts[key] <= high, 'Selected geometry count outside pilot')
    for key in ('zonetool_xpak_helper_reads_allowed', 'engine_io_verified', 'dependency_payloads_verified', 'asset_zone_ownership_verified',
                'serialized_parse_verified', 'runtime_verified', 'ready'):
        require(value[key] is False, 'Receipt must preserve unqualified claims')
    for role, path, limit in (('model', 'xmodel/'+request['model'].replace('\\','/')+'.xmb', 1024**2),
                              ('mesh', 'xsurface/'+mesh.replace('\\','/')+'.xsb', 16*1024**2)):
        artifact = value[role]
        require(type(artifact) is dict and set(artifact) == {'relative_path', 'bytes', 'sha256'}, 'Exact artifact fields required')
        require(artifact['relative_path'] == path and type(artifact['bytes']) is int and
                0 < artifact['bytes'] <= limit, 'Artifact path/size differs')
        require(type(artifact['sha256']) is str and re.fullmatch('[0-9a-fA-F]{64}', artifact['sha256']) is not None,
                'Full artifact digest required')
    return {'receipt_contract_verified': True, 'artifact_bytes_freshly_verified': False,
            'process_acceptance_verified': False, 'dependency_payloads_verified': False,
            'asset_zone_ownership_verified': False, 'serialized_parse_verified': False,
            'runtime_verified': False, 'ready': False}

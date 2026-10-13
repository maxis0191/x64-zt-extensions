"""Pure receipt validator; this cannot qualify engine/job/stock or rendered bytes."""
import re
from boot_contract import PROFILE, command_review, require, safe_name, validate_request

SCHEMA_V1 = 'iw7.t7-iw7-resident-export/1'
SCHEMA_V2 = 'iw7.t7-iw7-resident-export/2'
GEOMETRY_WORK_LIMIT = 16 * 1024**2
MANIFEST_LIMIT_V1, MANIFEST_LIMIT_V2 = 4096, 256 * 1024

FIELDS = {'schema', 'requested_zone', 'source_model', 'selected_source_lod', 'output_model_name',
          'output_mesh_name', 'output_root_key', 'target', 'profile', 'geometry_profile',
          'root_bone_name', 'selected_counts',
          'material_dependencies', 'model', 'mesh', 'zonetool_xpak_helper_reads_allowed', 'engine_io_verified',
          'dependency_payloads_verified', 'asset_zone_ownership_verified',
          'serialized_parse_verified', 'runtime_verified', 'ready'}
FIELDS_V2 = FIELDS | {'surface_records', 'geometry_work_bytes_upper_bound'}
SURFACE_FIELDS = {'index', 'material_slot', 'vertices', 'triangles'}


def geometry_work_bytes_upper_bound(surfaces, vertices, triangles):
    """Expanded logical geometry, counting every occurrence even when aliased.

    Source: mesh120 + shared80 + N*(surface80 + rigid16) + V*28 + T*6.
    Destination: mesh56 + N*(surface256 + rigid16) + V*32 + T*6.
    Indices count in both representations even when native conversion borrows
    them. This is not serialized size, CPU traffic or process/Python heap RAM.
    Names, model/bone/material metadata and container overhead are bounded
    separately; they do not enter this geometry-only accounting.
    """
    require(type(surfaces) is int and 1 <= surfaces <= 255 and
            type(vertices) is int and 3 * surfaces <= vertices <= 65535 * surfaces and
            type(triangles) is int and surfaces <= triangles <= 65535 * surfaces,
            'Aggregate geometry counts outside v2')
    result = 256 + 368 * surfaces + 60 * vertices + 12 * triangles
    require(result <= GEOMETRY_WORK_LIMIT, 'Expanded logical geometry exceeds 16 MiB')
    return result


def validate_export(value, request):
    request = validate_request(request)
    require(type(value) is dict, 'Export receipt must be an object')
    schema = value.get('schema')
    require(type(schema) is str and schema in (SCHEMA_V1, SCHEMA_V2), 'Explicit export schema required')
    v2 = schema == SCHEMA_V2
    require(set(value) == (FIELDS_V2 if v2 else FIELDS), 'Exact versioned export receipt fields required')
    require(value['target'] == 'iw7' and value['profile'] == PROFILE and
            value['geometry_profile'] == ('t7-iw7-resident-static-v2' if v2 else 't7-iw7-resident-static-v1'),
            'Unexpected export/geometry profile')
    require(value['requested_zone'] == request['zone'] and value['source_model'] == request['model'] and
            type(value['selected_source_lod']) is int and value['selected_source_lod'] == request['lod'],
            'Export differs from selected request')
    require(value['output_model_name'] == request['model'], 'Source model was renamed')
    mesh = safe_name(value['output_mesh_name'])
    require(value['output_root_key'] == command_review(request)['private_output_root_key'], 'Private root key differs')
    bone = value['root_bone_name']
    require(type(bone) is str and 1 <= len(bone) <= 255 and all(0x20 <= ord(c) < 0x7f for c in bone),
            'Exact bounded engine root-bone name required')
    counts = value['selected_counts']
    require(type(counts) is dict and set(counts) == {'bones', 'roots', 'surfaces', 'vertices', 'triangles'},
            'Exact selected geometry counts required')
    max_surfaces = 255 if v2 else 1
    for key, low, high in (('bones',1,1), ('roots',1,1), ('surfaces',1,max_surfaces),
                           ('vertices',3,65535*max_surfaces), ('triangles',1,65535*max_surfaces)):
        require(type(counts[key]) is int and low <= counts[key] <= high, 'Selected geometry count outside pilot')
    if v2:
        records = value['surface_records']
        require(type(records) is list and len(records) == counts['surfaces'],
                'Exactly N ordered surface records required')
        vertices = triangles = 0
        for index, record in enumerate(records):
            require(type(record) is dict and set(record) == SURFACE_FIELDS,
                    'Exact surface record fields required')
            require(type(record['index']) is int and record['index'] == index and
                    type(record['material_slot']) is int and record['material_slot'] == index,
                    'Surface indices and material slots must preserve source order')
            require(type(record['vertices']) is int and 3 <= record['vertices'] <= 65535 and
                    type(record['triangles']) is int and 1 <= record['triangles'] <= 65535,
                    'Per-surface geometry count outside uint16 profile')
            vertices += record['vertices']
            triangles += record['triangles']
        require((vertices, triangles) == (counts['vertices'], counts['triangles']),
                'Aggregate geometry counts differ from ordered surfaces')
        work = geometry_work_bytes_upper_bound(counts['surfaces'], vertices, triangles)
        require(type(value['geometry_work_bytes_upper_bound']) is int and
                value['geometry_work_bytes_upper_bound'] == work,
                'Logical geometry work bound differs')
    require(type(value['material_dependencies']) is list and
            len(value['material_dependencies']) == counts['surfaces'],
            'Exactly N unresolved material slots required')
    for material in value['material_dependencies']:
        safe_name(material)  # Repeated names are intentional ordered slots.
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

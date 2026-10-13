"""Bounded Model Lab adaptation of an existing resident T7 -> IW7 export.

The independent resident reader owns geometry parsing. This module changes only
the declared material string and, optionally, the selected LOD distance. It is
neither a second converter nor evidence of native provenance or visible pixels.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import struct
import sys

BRIDGE = Path(__file__).resolve().parents[2] / 'tools-source/asset-bridge/t7-iw7'
sys.path.insert(0, str(BRIDGE))
try:
    spec = importlib.util.spec_from_file_location('_model_lab_resident_readback', BRIDGE / 'readback.py')
    rb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rb)
    from boot_contract import safe_name
finally:
    sys.path.pop(0)

PROFILE = 't7-iw7-resident-static-v1'
MATERIAL = 'mopw/character_park_clown_zombie_shoes'
SCENE_MIN_DISTANCE = 256
FF_LIMIT = 32 * 1024**2


def digest(data):
    return hashlib.sha256(data).hexdigest()


def lab_name(value):
    safe_name(value)
    # The underlying export contract is broader. CSV and server-config names
    # deliberately use this smaller, unambiguous portable subset.
    rb.check(re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_./-]{0,254}', value) is not None,
             'Model Lab requires a portable CSV/config asset name')
    return value


def model_prefix(data, manifest):
    """Locate the material record with the existing typed record reader."""
    r = rb.Reader(data, rb.MODEL_LIMIT)
    r.array('model', 736, 1)
    r.name('model_name', 6, manifest['output_model_name'])
    r.name('root_bone', 6, manifest['root_bone_name'])
    for label, stride in (('parents', 1), ('angles', 8), ('positions', 12)):
        r.array(label, stride, 0)
    r.array('classification', 1, 1)
    r.array('base_mat', 32, 1)
    for label, stride in (('reactive_parts', 16), ('reactive_tweaks', 16), ('coll_surfs', 36)):
        r.array(label, stride, 0)
    r.array('bone_info', 28, 1)
    r.array('mip_radius', 2, 1)
    r.array('material_handles', 8, 1)
    start = r.pos
    r.name('material', 7, manifest['material_dependencies'][0], layout='material')
    rb.check(data[start:start+2] == b'\x07\x01', 'Material must be a standalone ASSET record')
    return start + 2, r.pos - 1


def derive(model, mesh, manifest, request, material, lod_distance=None):
    rb.check(material == MATERIAL, 'Explicit proven recipient material required')
    raw = rb.inspect_pair(model, mesh, manifest, request)
    lab_name(manifest['output_model_name'])
    lab_name(manifest['output_mesh_name'])
    start, end = model_prefix(model, manifest)
    derived = model[:start] + material.encode('ascii') + model[end:]
    transformations = [{'field': 'material', 'old': raw['model']['material'], 'new': material,
                        'source_string_span': [start, end]}]
    if lod_distance is not None:
        rb.check(type(lod_distance) in (int, float) and math.isfinite(lod_distance) and
                 0 <= lod_distance <= rb.FLOAT32_MAX, 'Finite nonnegative explicit LOD distance required')
        # First record is the independently validated model ARRAY (6-byte
        # framing). This field precedes the variable-length material string.
        encoded = struct.pack('<f', lod_distance)
        distance = struct.unpack('<f', encoded)[0]
        derived = derived[:230] + encoded + derived[234:]
        transformations.append({'field': 'lodInfo[0].dist', 'old': raw['model']['lod_distance'],
                                'new': distance, 'source_byte_span': [230, 234]})
    context = copy.deepcopy(manifest)
    context['material_dependencies'] = [material]
    # A private parse context is not an amended native exporter manifest.
    parsed = rb.parse_model(derived, context)
    expected = dict(raw['model'], material=material)
    if lod_distance is not None:
        expected['lod_distance'] = distance
    rb.check(parsed == expected, 'Undeclared model metadata change')
    return derived, {'schema': 'iw7.model-derived-export/1', 'geometry_profile': PROFILE,
                     'transformations': transformations, 'source_readback': raw,
                     'derived_model': parsed, 'model_sha256': digest(derived),
                     'mesh_sha256': digest(mesh), 'mesh_byte_identical': True,
                     'only_declared_bytes_changed': True, 'native_provenance_verified': False,
                     'runtime_verified': False, 'pixels_verified': False, 'ready': False}


def json_bytes(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode('utf-8')


def load_export(root, request_path, manifest_path):
    request_bytes = rb.read_bounded(request_path, 4096)
    manifest_bytes = rb.read_bounded(manifest_path, 4096)
    request, manifest = decode_document(request_bytes), decode_document(manifest_bytes)
    rb.validate_export(manifest, request)
    model = rb.read_bounded(root / manifest['model']['relative_path'], rb.MODEL_LIMIT)
    mesh = rb.read_bounded(root / manifest['mesh']['relative_path'], rb.MESH_LIMIT)
    return request, manifest, model, mesh, request_bytes, manifest_bytes


def assets(model_name, mesh_name):
    return {'zone_source/paris_model_probe_recipient.csv': ('material,' + MATERIAL + '\n').encode(),
            'zone_source/paris_model_probe.csv': ('ignore,paris_model_probe_recipient\nxmodel,' +
                model_name + '\nnetconststrings,ncs_mdl_paris_model_probe\n').encode(),
            'netconststrings/ncs_mdl_paris_model_probe.json': json_bytes(
                {'stringType': 0, 'sourceType': 2, 'stringList': [model_name]})}


def stage(export_root, request_path, manifest_path, output, material, lod_distance=None):
    from prepare_writer import safe_path, PIN
    root, output = safe_path(export_root), safe_path(output)
    rb.check(not output.exists() and not output.is_relative_to(root),
             'Fresh output outside immutable export root required')
    request, manifest, model, mesh, request_bytes, manifest_bytes = load_export(root, request_path, manifest_path)
    derived, receipt = derive(model, mesh, manifest, request, material, lod_distance)
    model_name, mesh_name = manifest['output_model_name'], manifest['output_mesh_name']
    payloads = assets(model_name, mesh_name)
    payloads[manifest['model']['relative_path']] = derived
    payloads[manifest['mesh']['relative_path']] = mesh
    distance = receipt['derived_model']['lod_distance']
    plan = {'schema': 'iw7.model-ff-plan/1', 'geometry_profile': PROFILE, 'source_pin': PIN,
            'zone': 'paris_model_probe', 'recipient': 'cp_zmb', 'model_name': model_name,
            'mesh_name': mesh_name, 'material_reference': MATERIAL, 'material_payload_copied': False,
            'selected_counts': manifest['selected_counts'], 'selected_source_lod': request['lod'],
            'lod0_dist': distance, 'has_lods': True, 'shadow_cutoff_lod': 6, 'collision_lod': 255,
            'scene_lod_minimum': SCENE_MIN_DISTANCE,
            'scene_lod_distance_sufficient': distance >= SCENE_MIN_DISTANCE,
            'source_files': {name: digest(data) for name, data in payloads.items()},
            'derived_receipt_sha256': digest(json_bytes(receipt)),
            'ff_built': False, 'pixels_verified': False, 'ready': False}
    # Retain byte-exact raw evidence under its own namespace. The export itself
    # is never edited and no derived artifact receives a native-export receipt.
    payloads.update({'evidence/request.json': request_bytes,
                     'evidence/manifest.json': manifest_bytes,
                     'evidence/source.xmb': model, 'evidence/source.xsb': mesh,
                     'derived-export.json': json_bytes(receipt), 'model-ff-plan.json': json_bytes(plan)})
    output.mkdir(parents=True)
    for name, data in payloads.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return plan


def decode_document(raw):
    # The same strict duplicate/nonfinite policy, with a larger receipt bound.
    def pairs(items):
        value = {}
        for key, item in items:
            rb.check(key not in value, 'Duplicate JSON field')
            value[key] = item
        return value
    def nonfinite(_):
        raise ValueError('Nonfinite JSON number')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


def read_document(path, limit=65536):
    return decode_document(rb.read_bounded(path, limit))


def verify_stage(root, *, scene=False):
    plan = read_document(root / 'model-ff-plan.json')
    receipt = read_document(root / 'derived-export.json')
    request = rb.read_json(root / 'evidence/request.json')
    manifest = rb.read_json(root / 'evidence/manifest.json')
    rb.validate_export(manifest, request)
    model = rb.read_bounded(root / 'evidence/source.xmb', rb.MODEL_LIMIT)
    mesh = rb.read_bounded(root / 'evidence/source.xsb', rb.MESH_LIMIT)
    transforms = receipt['transformations']
    rb.check(type(transforms) is list and len(transforms) in (1, 2), 'Only material and optional LOD changes allowed')
    distance = transforms[1]['new'] if len(transforms) == 2 else None
    derived, expected_receipt = derive(model, mesh, manifest, request, MATERIAL, distance)
    rb.check(receipt == json.loads(json_bytes(expected_receipt)), 'Derived receipt changed or undeclared transform')
    model_name, mesh_name = manifest['output_model_name'], manifest['output_mesh_name']
    expected = assets(model_name, mesh_name)
    expected[manifest['model']['relative_path']] = derived
    expected[manifest['mesh']['relative_path']] = mesh
    from prepare_writer import PIN
    rb.check(plan['schema'] == 'iw7.model-ff-plan/1' and plan['geometry_profile'] == PROFILE and
             plan['source_pin'] == PIN and plan['zone'] == 'paris_model_probe' and plan['recipient'] == 'cp_zmb' and
             plan['model_name'] == model_name and plan['mesh_name'] == mesh_name and
             plan['selected_counts'] == manifest['selected_counts'] and plan['selected_source_lod'] == request['lod'] and
             plan['material_reference'] == MATERIAL and plan['material_payload_copied'] is False and
             plan['ff_built'] is False and plan['pixels_verified'] is False and plan['ready'] is False and
             plan['has_lods'] is True and plan['shadow_cutoff_lod'] == 6 and plan['collision_lod'] == 255 and
             plan['derived_receipt_sha256'] == digest(rb.read_bounded(root / 'derived-export.json', 65536)) and
             plan['source_files'] == {name: digest(data) for name, data in expected.items()} and
             plan['lod0_dist'] == receipt['derived_model']['lod_distance'] and
             plan['scene_lod_minimum'] == SCENE_MIN_DISTANCE and
             plan['scene_lod_distance_sufficient'] is (plan['lod0_dist'] >= SCENE_MIN_DISTANCE),
             'FF plan differs from verified export derivation')
    for name, data in expected.items():
        limit = rb.MESH_LIMIT if name.endswith('.xsb') else rb.MODEL_LIMIT
        rb.check(rb.read_bounded(root / name, limit) == data, 'Undeclared staged byte change: ' + name)
    if scene:
        rb.check(plan['scene_lod_distance_sufficient'],
                 'Source LOD distance is below this scene\'s 256-unit margin; export is not invalid. '
                 'Review an explicit --lod-distance 1000000 derivation before FF admission; visibility remains unproven.')
    return plan, manifest, request, derived, mesh, receipt


def packed_geometry(mesh, manifest):
    r = rb.Reader(mesh, rb.MESH_LIMIT)
    r.array('mesh', 56, 1)
    r.name('mesh_name', 6, manifest['output_mesh_name'])
    r.array('surfaces', 256, 1)
    return (r.array('vertices', 32, manifest['selected_counts']['vertices']),
            r.array('triangles', 6, manifest['selected_counts']['triangles']),
            r.array('rigid_lists', 16, 1))


def verify_dump(source, dump, ff):
    plan, manifest, request, model, mesh, receipt = verify_stage(source, scene=True)
    context = copy.deepcopy(manifest)
    context['material_dependencies'] = [MATERIAL]
    dumped = {role: rb.read_bounded(dump / manifest[role]['relative_path'], limit)
              for role, limit in (('model', rb.MODEL_LIMIT), ('mesh', rb.MESH_LIMIT))}
    rb.check(rb.parse_model(dumped['model'], context) == rb.parse_model(model, context) and
             rb.parse_mesh(dumped['mesh'], context) == rb.parse_mesh(mesh, context) and
             packed_geometry(dumped['mesh'], context) == packed_geometry(mesh, context),
             'FF dump differs from derived geometry, packed attributes, rig or LOD/material metadata')
    ff_bytes = rb.read_bounded(ff, FF_LIMIT)
    return {'schema': 'iw7.model-rigid-roundtrip/1', 'geometry_profile': PROFILE,
            'model_name': plan['model_name'], 'mesh_name': plan['mesh_name'],
            'selected_counts': plan['selected_counts'], 'lod0_dist': plan['lod0_dist'],
            'material_reference': MATERIAL, 'ff': {'bytes': len(ff_bytes), 'sha256': digest(ff_bytes)},
            'source_plan_sha256': digest(rb.read_bounded(source / 'model-ff-plan.json', 65536)),
            'derived_receipt_sha256': plan['derived_receipt_sha256'],
            'inputs': [{'relative_path': 'roundtrip/' + manifest[role]['relative_path'],
                        'bytes': len(data), 'sha256': digest(data)} for role, data in dumped.items()],
            'geometry_roundtrip_verified': True, 'packed_attributes_byte_identical': True,
            'native_provenance_verified': False, 'source_geometry_correspondence_verified': False,
            'dependency_payloads_verified': False, 'runtime_verified': False, 'pixels_verified': False, 'ready': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    verify = commands.add_parser('verify-stage')
    verify.add_argument('--source', type=Path, required=True)
    dump = commands.add_parser('verify-dump')
    dump.add_argument('--source', type=Path, required=True)
    dump.add_argument('--dump', type=Path, required=True)
    dump.add_argument('--ff', type=Path, required=True)
    args = parser.parse_args()
    result = verify_stage(args.source, scene=True)[0] if args.command == 'verify-stage' else verify_dump(args.source, args.dump, args.ff)
    print(json.dumps(result, indent=2, allow_nan=False))

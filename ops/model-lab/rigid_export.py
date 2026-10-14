"""Bounded Model Lab adaptation of an existing resident T7 -> IW7 export.

The independent resident reader owns geometry parsing. This module changes only
declared material strings and, optionally, the selected LOD distance. It is
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
PROFILE_V2 = 't7-iw7-resident-static-v2'
MULTISURFACE_PROFILES = (PROFILE_V2, rb.STREAMED_PROFILE, rb.STREAMED_PROFILE_V2)
MATERIAL = 'mopw/character_park_clown_zombie_shoes'
SCENE_MIN_DISTANCE = 256
FF_LIMIT = 32 * 1024**2
# Independent metadata bound, not part of the native geometry-work accounting.
DOCUMENT_LIMIT = 1024**2


def digest(data):
    return hashlib.sha256(data).hexdigest()


def lab_name(value):
    safe_name(value)
    # The underlying export contract is broader. CSV and server-config names
    # deliberately use this smaller, unambiguous portable subset.
    rb.check(re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_./-]{0,254}', value) is not None,
             'Model Lab requires a portable CSV/config asset name')
    return value


def material_bindings(manifest, material, rebinds):
    if manifest['geometry_profile'] == PROFILE:
        rb.check(material == MATERIAL and rebinds is None, 'Explicit proven recipient material required')
        return [{'slot': 0, 'source': manifest['material_dependencies'][0], 'target': material}]
    rb.check(material is None and type(rebinds) is list and
             len(rebinds) == manifest['selected_counts']['surfaces'],
             'V2 requires an explicit ordered material rebind for every surface slot')
    for i, item in enumerate(rebinds):
        rb.check(type(item) is dict and set(item) == {'slot', 'source', 'target'} and
                 type(item['slot']) is int and item['slot'] == i and
                 item['source'] == manifest['material_dependencies'][i] and
                 type(item['target']) is str, 'Invalid ordered material rebind')
    return rebinds


def derive(model, mesh, manifest, request, material=None, lod_distance=None, *, rebinds=None):
    raw = rb.inspect_pair(model, mesh, manifest, request)
    lab_name(manifest['output_model_name'])
    lab_name(manifest['output_mesh_name'])
    bindings = material_bindings(manifest, material, rebinds)
    names = rb.parse_model(model, manifest, with_material_records=True)['material_records']
    definitions = {}
    for item, name in zip(bindings, names):
        entry = definitions.setdefault(name['definition'], dict(name, target=item['target'], slots=[]))
        rb.check(entry['target'] == item['target'], 'Aliased material slots require the same target')
        entry['slots'].append(item['slot'])
    rb.check(all(item['target'] == MATERIAL for item in bindings), 'Explicit proven recipient material required')
    transformations = []
    for entry in definitions.values():
        start, end = entry['string_span']
        change = {'field': 'material', 'old': entry['source'], 'new': entry['target'],
                  'source_string_span': [start, end]}
        if manifest['geometry_profile'] in MULTISURFACE_PROFILES:
            change.update(definition=entry['definition'], slots=entry['slots'])
        transformations.append(change)
    derived = model
    # Patch each defining ASSET string once, backwards; alias indices and all
    # other records retain their exact bytes and positions in the ledger.
    for change in reversed(transformations):
        start, end = change['source_string_span']
        derived = derived[:start] + change['new'].encode('ascii') + derived[end:]
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
    context['material_dependencies'] = [item['target'] for item in bindings]
    # A private parse context is not an amended native exporter manifest.
    parsed = rb.parse_model(derived, context)
    expected = dict(raw['model'])
    expected.update({'material': material} if manifest['geometry_profile'] == PROFILE else
                    {'materials': context['material_dependencies']})
    if lod_distance is not None:
        expected['lod_distance'] = distance
    rb.check(parsed == expected, 'Undeclared model metadata change')
    receipt = {'schema': 'iw7.model-derived-export/' + ('1' if manifest['geometry_profile'] == PROFILE else '2'),
                     'geometry_profile': manifest['geometry_profile'],
                     'transformations': transformations, 'source_readback': raw,
                     'derived_model': parsed, 'model_sha256': digest(derived),
                     'mesh_sha256': digest(mesh), 'mesh_byte_identical': True,
                     'only_declared_bytes_changed': True, 'native_provenance_verified': False,
                     'runtime_verified': False, 'pixels_verified': False, 'ready': False}
    if manifest['geometry_profile'] in MULTISURFACE_PROFILES:
        receipt['material_rebinds'] = copy.deepcopy(bindings)
    rb.check(len(json_bytes(receipt)) <= DOCUMENT_LIMIT, 'Derived metadata exceeds independent bound')
    return derived, receipt


def json_bytes(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode('utf-8')


def load_export(root, request_path, manifest_path):
    request_bytes = rb.read_bounded(request_path, 4096)
    manifest_bytes = rb.read_bounded(manifest_path, rb.MANIFEST_LIMIT)
    request, manifest = decode_document(request_bytes), decode_document(manifest_bytes)
    rb.check(type(manifest) is dict, 'Export manifest object required')
    rb.check(manifest.get('schema') in ('iw7.t7-iw7-resident-export/2', rb.STREAMED_SCHEMA) or len(manifest_bytes) <= 4096,
             'V1 manifest exceeds 4 KiB')
    rb.validate_export(manifest, request)
    model = rb.read_bounded(root / manifest['model']['relative_path'], rb.MODEL_LIMIT)
    mesh = rb.read_bounded(root / manifest['mesh']['relative_path'], rb.MESH_LIMIT)
    return request, manifest, model, mesh, request_bytes, manifest_bytes


def assets(model_name, mesh_name, materials=(MATERIAL,)):
    return {'zone_source/paris_model_probe_recipient.csv': ''.join(
                'material,' + name + '\n' for name in dict.fromkeys(materials)).encode(),
            'zone_source/paris_model_probe.csv': ('ignore,paris_model_probe_recipient\nxmodel,' +
                model_name + '\nnetconststrings,ncs_mdl_paris_model_probe\n').encode(),
            'netconststrings/ncs_mdl_paris_model_probe.json': json_bytes(
                {'stringType': 0, 'sourceType': 2, 'stringList': [model_name]})}


def stage(export_root, request_path, manifest_path, output, material=None, lod_distance=None, *, rebinds=None):
    from prepare_writer import safe_path
    root, output = safe_path(export_root), safe_path(output)
    rb.check(not output.exists() and not output.is_relative_to(root),
             'Fresh output outside immutable export root required')
    request, manifest, model, mesh, request_bytes, manifest_bytes = load_export(root, request_path, manifest_path)
    derived, receipt = derive(model, mesh, manifest, request, material, lod_distance, rebinds=rebinds)
    model_name, mesh_name = manifest['output_model_name'], manifest['output_mesh_name']
    materials = [item['target'] for item in material_bindings(manifest, material, rebinds)]
    payloads = assets(model_name, mesh_name, materials)
    payloads[manifest['model']['relative_path']] = derived
    payloads[manifest['mesh']['relative_path']] = mesh
    plan = make_plan(manifest, request, receipt, payloads)
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


def make_plan(manifest, request, receipt, payloads):
    from prepare_writer import PIN
    model_name, mesh_name = manifest['output_model_name'], manifest['output_mesh_name']
    distance = receipt['derived_model']['lod_distance']
    v2 = manifest['geometry_profile'] in MULTISURFACE_PROFILES
    plan = {'schema': 'iw7.model-ff-plan/' + ('2' if v2 else '1'),
            'geometry_profile': manifest['geometry_profile'], 'source_pin': PIN,
            'zone': 'paris_model_probe', 'recipient': 'cp_zmb', 'model_name': model_name,
            'mesh_name': mesh_name, 'material_reference': MATERIAL, 'material_payload_copied': False,
            'selected_counts': manifest['selected_counts'], 'selected_source_lod': request['lod'],
            'lod0_dist': distance, 'has_lods': True, 'shadow_cutoff_lod': 6, 'collision_lod': 255,
            'scene_lod_minimum': SCENE_MIN_DISTANCE,
            'scene_lod_distance_sufficient': distance >= SCENE_MIN_DISTANCE,
            'source_files': {name: digest(data) for name, data in payloads.items()},
            'derived_receipt_sha256': digest(json_bytes(receipt)),
            'ff_built': False, 'pixels_verified': False, 'ready': False}
    if v2:
        del plan['material_reference']
        plan.update(material_references=[item['target'] for item in receipt['material_rebinds']],
                    surface_records=manifest['surface_records'],
                    geometry_work_bytes_upper_bound=manifest['geometry_work_bytes_upper_bound'])
    rb.check(len(json_bytes(plan)) <= DOCUMENT_LIMIT, 'Plan metadata exceeds independent bound')
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


def read_document(path, limit=DOCUMENT_LIMIT):
    return decode_document(rb.read_bounded(path, limit))


def verify_stage(root, *, scene=False):
    plan = read_document(root / 'model-ff-plan.json')
    receipt = read_document(root / 'derived-export.json')
    request = rb.read_json(root / 'evidence/request.json')
    manifest = rb.read_json(root / 'evidence/manifest.json', manifest=True)
    rb.validate_export(manifest, request)
    if manifest['geometry_profile'] == PROFILE:
        for name in ('model-ff-plan.json', 'derived-export.json'):
            rb.read_bounded(root / name, 65536)
    model = rb.read_bounded(root / 'evidence/source.xmb', rb.MODEL_LIMIT)
    mesh = rb.read_bounded(root / 'evidence/source.xsb', rb.MESH_LIMIT)
    transforms = receipt['transformations']
    rb.check(type(transforms) is list and 1 <= len(transforms) <= 256 and
             all(type(item) is dict for item in transforms), 'Only material and optional LOD changes allowed')
    distances = [item['new'] for item in transforms if item.get('field') == 'lodInfo[0].dist']
    rb.check(len(distances) <= 1, 'Duplicate LOD change')
    distance = distances[0] if distances else None
    v2 = manifest['geometry_profile'] in MULTISURFACE_PROFILES
    rebinds = receipt.get('material_rebinds') if v2 else None
    derived, expected_receipt = derive(model, mesh, manifest, request, None if v2 else MATERIAL,
                                       distance, rebinds=rebinds)
    # Canonical JSON comparison keeps booleans distinct from integer 0/1.
    rb.check(json.dumps(receipt, sort_keys=True) == json.dumps(expected_receipt, sort_keys=True),
             'Derived receipt changed or undeclared transform')
    model_name, mesh_name = manifest['output_model_name'], manifest['output_mesh_name']
    materials = [item['target'] for item in rebinds] if v2 else [MATERIAL]
    expected = assets(model_name, mesh_name, materials)
    expected[manifest['model']['relative_path']] = derived
    expected[manifest['mesh']['relative_path']] = mesh
    expected_plan = make_plan(manifest, request, expected_receipt, expected)
    rb.check(json.dumps(plan, sort_keys=True) == json.dumps(expected_plan, sort_keys=True) and
             plan['derived_receipt_sha256'] == digest(rb.read_bounded(root / 'derived-export.json', DOCUMENT_LIMIT)),
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
    # Legacy v1 metadata omits packed fingerprints; v2 includes them per surface.
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
    v2 = manifest['geometry_profile'] in MULTISURFACE_PROFILES
    context['material_dependencies'] = plan['material_references'] if v2 else [MATERIAL]
    dumped = {role: rb.read_bounded(dump / manifest[role]['relative_path'], limit)
              for role, limit in (('model', rb.MODEL_LIMIT), ('mesh', rb.MESH_LIMIT))}
    # V2 parse_mesh compares each ordered packed vertex/face/rigid digest too.
    rb.check(rb.parse_model(dumped['model'], context) == rb.parse_model(model, context) and
             rb.parse_mesh(dumped['mesh'], context) == rb.parse_mesh(mesh, context) and
             (v2 or packed_geometry(dumped['mesh'], context) == packed_geometry(mesh, context)),
             'FF dump differs from derived geometry, packed attributes, rig or LOD/material metadata')
    ff_bytes = rb.read_bounded(ff, FF_LIMIT)
    proof = {'schema': 'iw7.model-rigid-roundtrip/' + ('2' if v2 else '1'), 'geometry_profile': manifest['geometry_profile'],
            'model_name': plan['model_name'], 'mesh_name': plan['mesh_name'],
            'selected_counts': plan['selected_counts'], 'lod0_dist': plan['lod0_dist'],
            'material_reference': MATERIAL, 'ff': {'bytes': len(ff_bytes), 'sha256': digest(ff_bytes)},
            'source_plan_sha256': digest(rb.read_bounded(source / 'model-ff-plan.json', DOCUMENT_LIMIT)),
            'derived_receipt_sha256': plan['derived_receipt_sha256'],
            'inputs': [{'relative_path': 'roundtrip/' + manifest[role]['relative_path'],
                        'bytes': len(data), 'sha256': digest(data)} for role, data in dumped.items()],
            'geometry_roundtrip_verified': True, 'packed_attributes_byte_identical': True,
            'native_provenance_verified': False, 'source_geometry_correspondence_verified': False,
            'dependency_payloads_verified': False, 'runtime_verified': False, 'pixels_verified': False, 'ready': False}
    if v2:
        del proof['material_reference']
        proof.update(material_references=plan['material_references'], surface_records=plan['surface_records'],
                     geometry_work_bytes_upper_bound=plan['geometry_work_bytes_upper_bound'])
    return proof


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

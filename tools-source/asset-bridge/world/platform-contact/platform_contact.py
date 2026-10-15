"""Join one authored platform mesh to the fixed a572 player-contact box, SOURCE only."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from trigger_bridge import (MAX_BYTES, checked_path, fields, f32, lexical_path,
                            parse, require, vector)

MINIMUM = [-128, -128, 0]
MAXIMUM = [128, 128, 16]


def exact_vector(value, label):
    result = vector(value, label)
    require(result == value, label + ': exact float32 required')
    return result


def asset_name(value, label):
    require(type(value) is str and len(value) <= 96 and
            re.fullmatch(r'[a-z][a-z0-9_]*(/[a-z][a-z0-9_]*)*', value),
            label + ': portable authored asset name required')
    return value


def validate_platform(mesh):
    """Check the actual closed rectangular surface, not only its bounding box.

    This consumes the existing original-mesh-source format. It neither authors
    the mesh nor validates a serialized XModel/material/SDK project.
    """
    fields(mesh, ('schema', 'name', 'bones', 'surfaces', 'lods', 'bounds',
                  'iw7_serialized', 'ready'), 'mesh')
    require(mesh['schema'] == 'iw7.original-mesh-source/1', 'Original mesh source required')
    asset_name(mesh['name'], 'model name')
    require(mesh['iw7_serialized'] is False and mesh['ready'] is False,
            'Source input cannot claim serialization/readiness')
    require(type(mesh['lods']) is int and mesh['lods'] == 1, 'One LOD required')
    require(type(mesh['bones']) is list and len(mesh['bones']) == 1, 'One rigid root required')
    root = mesh['bones'][0]
    fields(root, ('name', 'parent', 'translation', 'rotation_xyzw'), 'root')
    require(root['name'] == 'tag_origin' and root['parent'] is None and
            exact_vector(root['translation'], 'root translation') == [0, 0, 0],
            'Identity tag_origin required')
    rotation = root['rotation_xyzw']
    require(type(rotation) is list and len(rotation) == 4 and
            [f32(v, 'root rotation') for v in rotation] == rotation == [0, 0, 0, 1],
            'Identity root rotation required')
    fields(mesh['bounds'], ('midpoint', 'half_size'), 'mesh bounds')
    require(exact_vector(mesh['bounds']['midpoint'], 'mesh midpoint') == [0, 0, 8] and
            exact_vector(mesh['bounds']['half_size'], 'mesh half size') == [128, 128, 8],
            'Fixed 256 by 256 by 16 platform bounds required')
    require(type(mesh['surfaces']) is list and len(mesh['surfaces']) == 1, 'One surface required')
    surface = mesh['surfaces'][0]
    fields(surface, ('material_reference', 'vertices', 'triangles'), 'surface')
    if surface['material_reference'] is not None:
        asset_name(surface['material_reference'], 'material reference')
    vertices, triangles = surface['vertices'], surface['triangles']
    require(type(vertices) is list and len(vertices) == 24 and
            type(triangles) is list and len(triangles) == 12, '24 vertices/12 triangles required')
    positions = []
    for vertex in vertices:
        fields(vertex, ('position', 'normal', 'uv', 'bone', 'weight'), 'vertex')
        position = exact_vector(vertex['position'], 'vertex position')
        require(all(position[i] in (MINIMUM[i], MAXIMUM[i]) for i in range(3)),
                'Every vertex must be an actual platform corner')
        exact_vector(vertex['normal'], 'vertex normal')
        uv = vertex['uv']
        require(type(uv) is list and len(uv) == 2 and
                all(0 <= f32(v, 'UV') <= 1 for v in uv), 'Finite bounded UV required')
        require(type(vertex['bone']) is int and vertex['bone'] == 0 and
                f32(vertex['weight'], 'weight') == vertex['weight'] == 1,
                'Rigid root weight required')
        positions.append(position)
    faces = {}
    used = set()
    for triangle in triangles:
        require(type(triangle) is list and len(triangle) == 3 and
                all(type(i) is int and 0 <= i < 24 for i in triangle) and
                len(set(triangle)) == 3, 'Three distinct bounded indices required')
        points = [positions[i] for i in triangle]
        axes = [i for i in range(3) if len({p[i] for p in points}) == 1]
        require(len(axes) == 1, 'Nondegenerate axis-aligned face required')
        axis = axes[0]
        side = int(points[0][axis] == MAXIMUM[axis])
        normal = [(1 if side else -1) if i == axis else 0 for i in range(3)]
        require(all(vertices[i]['normal'] == normal for i in triangle), 'Outward flat normals required')
        u = [points[1][i] - points[0][i] for i in range(3)]
        v = [points[2][i] - points[0][i] for i in range(3)]
        cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
        require(sum(a*b for a, b in zip(cross, normal)) > 0, 'Outward triangle winding required')
        faces.setdefault((axis, side), []).append(set(triangle))
        used.update(triangle)
    require(len(faces) == 6 and len(used) == 24, 'All six faces and 24 face-local vertices required')
    for (axis, _), pair in faces.items():
        require(len(pair) == 2 and len(pair[0] | pair[1]) == 4 and len(pair[0] & pair[1]) == 2 and
                len({tuple(positions[i]) for i in pair[0] | pair[1]}) == 4,
                'Two distinct triangles per rectangular face required')
        diagonal = list(pair[0] & pair[1])
        require(all(positions[diagonal[0]][i] != positions[diagonal[1]][i]
                    for i in range(3) if i != axis), 'Triangles must share the face diagonal')
    return mesh


def contact_contract(mesh, anchor):
    mesh = validate_platform(mesh)
    anchor = exact_vector(anchor, 'source anchor P')
    offset = lambda delta, label: exact_vector([anchor[i]+delta[i] for i in range(3)], label)
    origin = offset([0, 0, 96], 'model origin')
    lo = offset([-128, -128, 96], 'absolute minimum')
    hi = offset([128, 128, 112], 'absolute maximum')
    center = offset([0, 0, 104], 'native center')
    start = offset([0, 0, 208], 'player start')
    # The Python float64 addition can itself lose small offsets at huge P,
    # before exact_vector sees the value. Endpoint self-equality cannot prove
    # that the requested platform still has its original nonzero dimensions.
    require([hi[i]-lo[i] for i in range(3)] == [256, 256, 16],
            'Absolute box must preserve exact 256 by 256 by 16 dimensions')
    require(all(abs(v) <= 30000 for v in anchor), 'a572 source anchor must remain within +/-30000')
    require(all(origin[i]+MINIMUM[i] == lo[i] and origin[i]+MAXIMUM[i] == hi[i] and
                center[i]-[128, 128, 8][i] == lo[i] and center[i]+[128, 128, 8][i] == hi[i]
                for i in range(3)), 'Render and native endpoints must be identical exact float32')
    return {
        'schema': 'iw7.platform-contact-source/1',
        'geometry_schema': mesh['schema'], 'model_name': mesh['name'],
        'material_reference': mesh['surfaces'][0]['material_reference'],
        'source_anchor': anchor,
        'local_bounds': {'minimum': MINIMUM[:], 'maximum': MAXIMUM[:]},
        'render_transform': {'model_origin': origin, 'model_angles': [0, 0, 0], 'uniform_scale': 1},
        'world_bounds': {'minimum': lo, 'maximum': hi},
        'native_box': {'world': 0, 'owner_class': 'script_model', 'owner_distinct_from_renderer': True,
                       'solid_before_create_required': True, 'observed': 1,
                       'bounds_space': 'absolute IW7 game coordinates', 'owner_transform_applied': False,
                       'origin': center, 'half_size': [128, 128, 8], 'rotation_xyzw': [0, 0, 0, 1],
                       'provider_internal_game_to_havok_scale': 0.03125},
        'player_start': start,
        'behavior_requirements': {
            'visual_present_in_all_phases': True, 'visual_additional_colliders': 0,
            'F0': 'No body; fall with visual present',
            'F1': 'One body; fall, landing, standing 600ms, ordinary forward movement 300ms/4..64 units',
            'Use': 'One coordinated press after released-stable 250ms; one counter increment/toggle and F2 removal request',
            'F2': 'Remove body with owner alive; new fall; delete owner afterward',
        },
        'source_geometry_verified': True,
        'sdk_project_bound': False, 'caller_asset_loading_bound': False,
        'actual_anchor_verified': False, 'material_payload_verified': False,
        'render_transform_verified': False, 'rendered_bounds_verified': False,
        'native_collision_verified': False, 'player_movement_verified': False,
        'prediction_verified': False, 'cooperative_client_verified': False, 'runtime_verified': False,
    }


def write_contract(geometry_path, output_path, anchor):
    source, destination = lexical_path(geometry_path), lexical_path(output_path)
    require(source.suffix == '.json' and destination.suffix == '.json', 'Source/output .json required')
    source, destination = checked_path(source, True), checked_path(destination, False)
    with source.open('rb') as stream:
        data = stream.read(MAX_BYTES+1)
    result = contact_contract(parse(data), anchor)
    result['geometry_source_sha256'] = hashlib.sha256(data).hexdigest()
    encoded = (json.dumps(result, indent=2, allow_nan=False)+'\n').encode('utf-8')
    with destination.open('xb') as stream:
        stream.write(encoded)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--geometry-source', required=True)
    parser.add_argument('--source-anchor', nargs=3, type=float, required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        result = write_contract(args.geometry_source, args.output, args.source_anchor)
        print(json.dumps(result, indent=2, allow_nan=False))
    except (ValueError, OSError) as error:
        parser.exit(2, str(error)+'\n')

"""Original rigid cube input for the future pinned IW7 assetmanager writer.

This emits source geometry only. It does not produce XMB/XSB/FF or game evidence.
"""
import argparse
import copy
import json
import math
from pathlib import Path
import re
import struct


AUTHORED_PROFILE = 'iw7-authored-rigid-v1'
MAX_VERTICES, MAX_TRIANGLES = 192, 96
MAX_POSITION = 32768


def authored_name(value, *, asset=False):
    """Portable authored identifiers, not an allowlist of individual assets."""
    limit = 127 if asset else 63
    pattern = r'[A-Za-z0-9_]+(?:/[A-Za-z0-9_]+)*' if asset else r'[A-Za-z0-9_]+'
    if type(value) is not str or not 1 <= len(value) <= limit or not re.fullmatch(pattern, value):
        raise ValueError('Bounded portable authored name required')
    reserved = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)),
                *(f'LPT{i}' for i in range(1, 10))}
    if any(part.upper() in reserved for part in value.split('/')):
        raise ValueError('Reserved path component refused')
    return value


def float32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def _vector(values, count):
    if type(values) is not list or len(values) != count or any(type(v) not in (int, float) for v in values):
        raise ValueError('Finite numeric vectors required')
    try:
        finite = all(math.isfinite(v) for v in values)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError('Finite numeric vectors required')
    return values


def derived_bounds(vertices):
    """Conservative float32 AABB of serialized positions, in model-local space."""
    if type(vertices) is not list or not vertices:
        raise ValueError('Vertices required to derive bounds')
    vectors = [_vector(v['position'], 3) for v in vertices]
    if any(abs(value) > MAX_POSITION for point in vectors for value in point):
        raise ValueError('Bounded authored positions required')
    points = [list(map(float32, point)) for point in vectors]
    midpoint, half = [], []
    for axis in range(3):
        low, high = min(p[axis] for p in points), max(p[axis] for p in points)
        mid = float32((low + high) / 2)
        extent = max(high - mid, mid - low)
        size = float32(extent)
        if size < extent:
            bits = struct.unpack('<I', struct.pack('<f', size))[0]
            size = struct.unpack('<f', struct.pack('<I', bits + 1))[0]
        midpoint.append(mid)
        half.append(size)
    return {'midpoint': midpoint, 'half_size': half}


def packed_uv(uv):
    """Same binary16 nearest-even, U-low/V-high convention as half_uv.hpp."""
    return struct.unpack('<I', struct.pack('<ee', *map(float32, uv)))[0]


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def authored_tangents(data):
    """UV-derived unit tangents; mirrored/degenerate UVs need another profile."""
    surface = data['surfaces'][0]
    vertices = surface['vertices']
    sums = [[0.0, 0.0, 0.0] for _ in vertices]
    used = set()
    for indices in surface['triangles']:
        a, b, c = (vertices[i] for i in indices)
        edge1 = [b['position'][j] - a['position'][j] for j in range(3)]
        edge2 = [c['position'][j] - a['position'][j] for j in range(3)]
        face = _cross(edge1, edge2)
        if not _dot(face, face) or any(_dot(face, v['normal']) <= 0 for v in (a, b, c)):
            raise ValueError('Degenerate/inverted triangle or opposing normal')
        # Derive from the UVs the native stream will actually contain.
        uv = [struct.unpack('<ee', struct.pack('<I', packed_uv(v['uv']))) for v in (a, b, c)]
        u1, v1 = uv[1][0]-uv[0][0], uv[1][1]-uv[0][1]
        u2, v2 = uv[2][0]-uv[0][0], uv[2][1]-uv[0][1]
        determinant = u1*v2-u2*v1
        if determinant <= 0:
            raise ValueError('Mirrored/degenerate half-precision UV triangle refused')
        tangent = [(edge1[j]*v2-edge2[j]*v1)/determinant for j in range(3)]
        length = math.sqrt(_dot(tangent, tangent))
        if not length:
            raise ValueError('Degenerate tangent refused')
        for index in indices:
            used.add(index)
            sums[index] = [sums[index][j] + tangent[j]/length for j in range(3)]
    if len(used) != len(vertices):
        raise ValueError('Unreferenced authored vertex refused')
    result = []
    for vertex, total in zip(vertices, sums):
        normal = vertex['normal']
        projection = _dot(total, normal)/_dot(normal, normal)
        tangent = [total[j]-normal[j]*projection for j in range(3)]
        length = math.sqrt(_dot(tangent, tangent))
        if length < 1e-10:
            raise ValueError('Conflicting authored vertex tangents refused')
        result.append([float32(t/length) for t in tangent])
    return result


def validate_authored(data, *, model_name=None, material_reference=None):
    """Validate a bounded authored rigid mesh; return float32 source and bounds.

    This is source validation, never IW7 ABI, native roundtrip or pixel evidence.
    The historical validate()/original_cube() contract is deliberately separate.
    """
    keys = {'schema', 'name', 'bones', 'surfaces', 'lods', 'bounds', 'iw7_serialized', 'ready'}
    if type(data) is not dict or set(data) != keys or data.get('schema') != 'iw7.original-mesh-source/1':
        raise ValueError('Explicit authored mesh source fields required')
    authored_name(data['name'])
    if model_name is not None and data['name'] != authored_name(model_name):
        raise ValueError('Authored model identity differs')
    if type(data['lods']) is not int or data['lods'] != 1 or data['ready'] is not False or data['iw7_serialized'] is not False:
        raise ValueError('One source-only LOD required')
    bones = data['bones']
    if type(bones) is not list or len(bones) != 1 or type(bones[0]) is not dict or set(bones[0]) != {
            'name', 'parent', 'translation', 'rotation_xyzw'}:
        raise ValueError('Exactly one identity root required')
    bone = bones[0]
    if bone['name'] != 'tag_origin' or bone['parent'] is not None or _vector(bone['translation'], 3) != [0, 0, 0] or _vector(
            bone['rotation_xyzw'], 4) != [0, 0, 0, 1]:
        raise ValueError('Exactly one identity root required')
    surfaces = data['surfaces']
    if type(surfaces) is not list or len(surfaces) != 1 or type(surfaces[0]) is not dict or set(surfaces[0]) != {
            'material_reference', 'vertices', 'triangles'}:
        raise ValueError('Exactly one explicit authored surface required')
    surface = surfaces[0]
    material = authored_name(surface['material_reference'], asset=True)
    if material_reference is not None and material != authored_name(material_reference, asset=True):
        raise ValueError('Authored material reference differs')
    vertices, triangles = surface['vertices'], surface['triangles']
    if type(vertices) is not list or not 3 <= len(vertices) <= MAX_VERTICES or type(triangles) is not list or not 1 <= len(triangles) <= MAX_TRIANGLES:
        raise ValueError('Authored reader envelope requires 3..192 vertices and 1..96 triangles')
    result = copy.deepcopy(data)
    for vertex in result['surfaces'][0]['vertices']:
        if type(vertex) is not dict or set(vertex) != {'position', 'normal', 'uv', 'bone', 'weight'}:
            raise ValueError('Explicit authored vertex fields required')
        for key, count in (('position', 3), ('normal', 3), ('uv', 2)):
            values = _vector(vertex[key], count)
            limit = MAX_POSITION if key == 'position' else 1
            if any(abs(v) > limit or (key == 'uv' and v < 0) for v in values):
                raise ValueError('Authored position/normal/UV outside profile bounds')
            vertex[key] = list(map(float32, values))
        if type(vertex['bone']) is not int or vertex['bone'] != 0 or type(vertex['weight']) not in (int, float) or vertex['weight'] != 1:
            raise ValueError('Rigid identity-root weights required')
        if abs(_dot(vertex['normal'], vertex['normal']) - 1) > 1e-6:
            raise ValueError('Unit authored normals required')
    for triangle in triangles:
        if type(triangle) is not list or len(triangle) != 3 or any(
                type(index) is not int or not 0 <= index < len(vertices) for index in triangle) or len(set(triangle)) != 3:
            raise ValueError('Distinct bounded authored triangle indices required')
    bounds = data['bounds']
    if type(bounds) is not dict or set(bounds) != {'midpoint', 'half_size'}:
        raise ValueError('Explicit derived authored bounds required')
    expected = derived_bounds(result['surfaces'][0]['vertices'])
    for key in expected:
        values = _vector(bounds[key], 3)
        if any(abs(v) > 2*MAX_POSITION for v in values) or list(map(float32, values)) != expected[key]:
            raise ValueError('Declared bounds differ from serialized authored positions')
    result['bounds'] = expected
    authored_tangents(result)
    return result


def original_cube():
    # Each face has its own four vertices for discontinuous flat normals/UVs.
    # Viewed from outside, each face winds counterclockwise.
    faces = [
        ((1, 0, 0), ((8, -8, -8), (8, 8, -8), (8, 8, 8), (8, -8, 8))),
        ((-1, 0, 0), ((-8, 8, -8), (-8, -8, -8), (-8, -8, 8), (-8, 8, 8))),
        ((0, 1, 0), ((8, 8, -8), (-8, 8, -8), (-8, 8, 8), (8, 8, 8))),
        ((0, -1, 0), ((-8, -8, -8), (8, -8, -8), (8, -8, 8), (-8, -8, 8))),
        ((0, 0, 1), ((-8, -8, 8), (8, -8, 8), (8, 8, 8), (-8, 8, 8))),
        ((0, 0, -1), ((-8, 8, -8), (8, 8, -8), (8, -8, -8), (-8, -8, -8))),
    ]
    vertices, triangles = [], []
    for normal, corners in faces:
        start = len(vertices)
        for position, uv in zip(corners, ((0, 0), (1, 0), (1, 1), (0, 1))):
            vertices.append({'position': list(position), 'normal': list(normal),
                             'uv': list(uv), 'bone': 0, 'weight': 1.0})
        triangles.extend(((start, start + 1, start + 2), (start, start + 2, start + 3)))
    return {'schema': 'iw7.original-mesh-source/1', 'name': 'paris_model_probe',
            'bones': [{'name': 'tag_origin', 'parent': None, 'translation': [0, 0, 0],
                       'rotation_xyzw': [0, 0, 0, 1]}],
            'surfaces': [{'material_reference': None, 'vertices': vertices,
                          'triangles': [list(t) for t in triangles]}],
            'lods': 1, 'bounds': {'midpoint': [0, 0, 0], 'half_size': [8, 8, 8]},
            'iw7_serialized': False, 'ready': False}


def validate(data):
    if data.get('schema') != 'iw7.original-mesh-source/1' or data.get('name') != 'paris_model_probe':
        raise ValueError('Original probe identity required')
    expected = original_cube()
    if data.get('bones') != expected['bones'] or data.get('lods') != 1:
        raise ValueError('Exactly one rigid identity root and one LOD required')
    surfaces = data.get('surfaces')
    if not isinstance(surfaces, list) or len(surfaces) != 1:
        raise ValueError('Exactly one surface required')
    surface = surfaces[0]
    if surface.get('material_reference') is not None:
        raise ValueError('Material awaits a measured retail reference')
    vertices, triangles = surface.get('vertices'), surface.get('triangles')
    if not isinstance(vertices, list) or len(vertices) != 24 or not isinstance(triangles, list) or len(triangles) != 12:
        raise ValueError('Probe requires 24 vertices and 12 triangles')
    for vertex in vertices:
        for key, count in (('position', 3), ('normal', 3), ('uv', 2)):
            values = vertex.get(key)
            if not isinstance(values, list) or len(values) != count or any(
                    isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
                raise ValueError('Finite vectors required')
        if vertex.get('bone') != 0 or vertex.get('weight') != 1.0:
            raise ValueError('Rigid root weights required')
        if abs(sum(v * v for v in vertex['normal']) - 1.0) > 1e-6 or any(not 0 <= v <= 1 for v in vertex['uv']):
            raise ValueError('Unit normals and bounded UVs required')
        if any(abs(v) > 8 for v in vertex['position']):
            raise ValueError('Position escapes explicit bounds')
    for triangle in triangles:
        if not isinstance(triangle, list) or len(triangle) != 3 or len(set(triangle)) != 3 or any(
                isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < len(vertices) for i in triangle):
            raise ValueError('Bounded distinct triangle indices required')
        a, b, c = (vertices[i] for i in triangle)
        u = [b['position'][j] - a['position'][j] for j in range(3)]
        v = [c['position'][j] - a['position'][j] for j in range(3)]
        cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
        if sum(cross[j] * a['normal'][j] for j in range(3)) <= 0 or any(
                vertex['normal'] != a['normal'] for vertex in (b, c)):
            raise ValueError('Degenerate/inverted face or mixed face normals')
    if data.get('bounds') != expected['bounds'] or data.get('ready') is not False or data.get('iw7_serialized') is not False:
        raise ValueError('Geometry preparation cannot claim an IW7 artifact/readiness')
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    data = validate(original_cube())
    # Exclusive file creation; no game directory or existing source is overwritten.
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(data, output, indent=2, allow_nan=False)
        output.write('\n')

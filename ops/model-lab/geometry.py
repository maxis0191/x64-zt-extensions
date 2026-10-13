"""Original rigid cube input for the future pinned IW7 assetmanager writer.

This emits source geometry only. It does not produce XMB/XSB/FF or game evidence.
"""
import argparse
import json
import math
from pathlib import Path


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

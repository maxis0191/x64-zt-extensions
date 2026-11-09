"""Check the vertex normals of ZoneTool IW7 .xsb model surfaces (stdlib only).

IW7 packs a model vertex normal as 10:10:10 (each component (v / 1023) * 2 - 1)
and sets the two high bits on every vertex: 180,445 of 180,445 vertices of 300
stock cp_zmb surfaces. Black Ops III uses the same direction encoding with the
high bits clear; a converted model that keeps them clear renders black in IW7.
This also checks that normals are unit length; agreement with the triangles
is reported for information (deforming stock meshes can disagree).

    python iw7_xsurface_check.py <file.xsb> [...]

Prints one JSON report per file and exits 1 when a file fails. Surfaces with
packed motion vertices are reported as skipped. A pass is a data check, not a
rendering proof.
"""
import json
import math
import struct
import sys

XMODEL_SURFS_SIZE = 0x38
XSURFACE_SIZE = 0x100
VERTEX_SIZE = 32          # GfxPackedVertex: xyz, selfVisibility, color, texCoord, normal, tangent
FLAG_MOTION_VERTS = 8
HIGH_BITS = 0xC0000000


def decode(packed):
    return [((packed >> shift) & 0x3FF) / 1023.0 * 2.0 - 1.0 for shift in (0, 10, 20)]


def check_vertices(vertices, triangles):
    """vertices: (x, y, z, normal); triangles: (a, b, c). Returns measures."""
    high = sum(1 for v in vertices if (v[3] & HIGH_BITS) == HIGH_BITS)
    lengths = sorted(math.sqrt(sum(c * c for c in decode(v[3]))) for v in vertices)
    agree = total = 0
    for a, b, c in triangles:
        if max(a, b, c) >= len(vertices):
            return None
        pa, pb, pc = (vertices[i][:3] for i in (a, b, c))
        u = [pb[k] - pa[k] for k in range(3)]
        w = [pc[k] - pa[k] for k in range(3)]
        face = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
        if not any(face):
            continue
        for i in (a, b, c):
            dot = sum(f * n for f, n in zip(face, decode(vertices[i][3])))
            total += 1
            agree += dot < 0  # IW winding: face cross product opposes the vertex normal
    return {'vertices': len(vertices), 'normal_high_bits_set': high,
            'normal_length_median': round(lengths[len(lengths) // 2], 3) if lengths else None,
            'triangle_agreement': round(agree / total, 3) if total else None}


def errors_for(measures):
    errors = []
    if measures['normal_high_bits_set'] != measures['vertices']:
        errors.append('%d of %d vertex normals lack the IW7 high bits' %
                      (measures['vertices'] - measures['normal_high_bits_set'], measures['vertices']))
    if measures['normal_length_median'] is not None and abs(measures['normal_length_median'] - 1.0) > 0.05:
        errors.append('vertex normals are not unit length (median %s)' % measures['normal_length_median'])
    return errors


def parse(data):
    """Return the model name and per-surface (flags, vertices, triangles).

    The exact record walk of iw7_xsurface_uv2 is tried first: it also reads surfaces that carry a second UV
    set, which the search below takes for the next vertex array when two surfaces have the same vertex count.
    """
    try:
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import iw7_xsurface_uv2 as exact
        name, found = exact.parse(data)
    except (ImportError, ValueError, IndexError, struct.error):
        return parse_by_search(data)
    surfaces = []
    for item in found:
        if item['flags'] & FLAG_MOTION_VERTS or item['verts'] is None or item['tris'] is None:
            surfaces.append((item['flags'], None, None))
            continue
        vertices = [struct.unpack_from('<3f12xI4x', item['verts'], i * VERTEX_SIZE)
                    for i in range(item['vert_count'])]
        triangles = [struct.unpack_from('<3H', item['tris'], i * 6) for i in range(item['tri_count'])]
        surfaces.append((item['flags'], vertices, triangles))
    return name, surfaces


def parse_by_search(data):
    """The same result, finding each vertex array by its count (surfaces without a second UV set)."""
    pos = 0

    def record(kind):
        nonlocal pos
        if data[pos] != kind or data[pos + 1] != 1:
            raise ValueError('expected record %d at byte %d' % (kind, pos))
        pos += 2

    record(8)
    if struct.unpack_from('<I', data, pos)[0] != 1:
        raise ValueError('XModelSurfs record count')
    pos += 4
    numsurfs = struct.unpack_from('<H', data, pos + 16)[0]
    pos += XMODEL_SURFS_SIZE
    record(6)
    end = data.index(b'\0', pos)
    name = data[pos:end].decode('ascii')
    pos = end + 1
    record(8)
    if struct.unpack_from('<I', data, pos)[0] != numsurfs:
        raise ValueError('surface count differs')
    pos += 4
    headers = [data[pos + i * XSURFACE_SIZE:pos + (i + 1) * XSURFACE_SIZE] for i in range(numsurfs)]
    pos += numsurfs * XSURFACE_SIZE
    surfaces = []
    for head in headers:
        flags, vert_count, tri_count = struct.unpack_from('<3H', head, 0)
        # Each surface's vertex array follows its predecessor's records.
        key = bytes([8, 1]) + struct.pack('<I', vert_count)
        pos = data.index(key, pos) + 6
        if flags & FLAG_MOTION_VERTS:
            surfaces.append((flags, None, None))
            continue
        vertices = [struct.unpack_from('<3f12xI4x', data, pos + i * VERTEX_SIZE) for i in range(vert_count)]
        pos += vert_count * VERTEX_SIZE
        record(8)
        if struct.unpack_from('<I', data, pos)[0] != tri_count:
            raise ValueError('triangle count differs')
        pos += 4
        triangles = [struct.unpack_from('<3H', data, pos + i * 6) for i in range(tri_count)]
        pos += tri_count * 6
        surfaces.append((flags, vertices, triangles))
    return name, surfaces


def check_file(path):
    with open(path, 'rb') as handle:
        name, surfaces = parse(handle.read())
    report = {'name': name, 'surfaces': [], 'errors': []}
    for index, (flags, vertices, triangles) in enumerate(surfaces):
        if vertices is None:
            report['surfaces'].append({'surface': index, 'skipped': 'packed motion vertices'})
            continue
        measures = check_vertices(vertices, triangles)
        if measures is None:
            report['errors'].append('surface %d: triangle index outside the vertices' % index)
            continue
        measures['surface'] = index
        report['surfaces'].append(measures)
        report['errors'] += ['surface %d: %s' % (index, e) for e in errors_for(measures)]
    return report


def main(argv=None):
    paths = argv if argv is not None else sys.argv[1:]
    if not paths:
        print(__doc__.strip().splitlines()[0])
        return 2
    failed = False
    for path in paths:
        report = check_file(path)
        failed |= bool(report['errors'])
        print(json.dumps(report))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())

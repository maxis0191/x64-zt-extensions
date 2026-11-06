"""Rebuild the vertex normals of ZoneTool IW7 .xsb model surfaces from their triangles (stdlib only).

Some Black Ops III models come out of the T7 -> IW7 conversion with unit-length normals (high bits set,
iw7_xsurface_check passes) that point in arbitrary directions: p7_zm_teddybear's normals are outward for
49..55% of the vertices (a closed body: about 100% expected) while its triangle winding is outward like a
stock mesh, so the model is lit and shaded wrongly. This recomputes every rigid vertex normal as the
area-weighted mean of the front directions of the triangles that use it (IW winding: front = -(a->b x a->c),
the iw7_xsurface_check convention), smoothed across vertices that share a position (UV seams), and packs it
10:10:10 with the IW7 high bits. Positions, UVs, tangents, colours, triangles and all other bytes are kept.

    python iw7_xsurface_normals.py <file.xsb> [...] [--out-dir <dir>] [--check-only]

One JSON line per file: per surface the share of normals pointing away from the surface centroid and the
triangle agreement, before and after. A data repair, not a rendering proof.
"""
import argparse
import json
import math
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iw7_xsurface_check as check  # noqa: E402

NORMAL_OFFSET = 24        # GfxPackedVertex: xyz 12, selfVisibility 4, color 4, texCoord 4, normal 4, tangent 4


def locate(data):
    """Per surface: (flags, vertex array offset, vertices, triangle offset, triangles)."""
    pos = 2 + 4
    numsurfs = struct.unpack_from('<H', data, pos + 16)[0]
    pos += check.XMODEL_SURFS_SIZE + 2
    pos = data.index(b'\0', pos) + 1 + 2 + 4
    heads = [data[pos + i * check.XSURFACE_SIZE:pos + (i + 1) * check.XSURFACE_SIZE] for i in range(numsurfs)]
    pos += numsurfs * check.XSURFACE_SIZE
    out = []
    for head in heads:
        flags, vert_count, tri_count = struct.unpack_from('<3H', head, 0)
        pos = data.index(bytes([8, 1]) + struct.pack('<I', vert_count), pos) + 6
        if flags & check.FLAG_MOTION_VERTS:
            out.append((flags, None, None, None, None))
            continue
        vat = pos
        vertices = [struct.unpack_from('<3f12xI4x', data, pos + i * check.VERTEX_SIZE) for i in range(vert_count)]
        pos += vert_count * check.VERTEX_SIZE
        if data[pos] != 8 or data[pos + 1] != 1 or struct.unpack_from('<I', data, pos + 2)[0] != tri_count:
            raise ValueError('triangle record not found')
        pos += 6
        triangles = [struct.unpack_from('<3H', data, pos + i * 6) for i in range(tri_count)]
        out.append((flags, vat, vertices, pos, triangles))
        pos += tri_count * 6
    return out


def pack(n):
    v = 0
    for k, shift in enumerate((0, 10, 20)):
        q = int(round((max(-1.0, min(1.0, n[k])) + 1.0) / 2.0 * 1023.0))
        v |= (q & 0x3FF) << shift
    return v | check.HIGH_BITS


def outward(vertices):
    cx = [sum(v[k] for v in vertices) / len(vertices) for k in range(3)]
    return round(sum(1 for v in vertices if sum(check.decode(v[3])[k] * (v[k] - cx[k]) for k in range(3)) > 0) / len(vertices), 3)


def rebuild(vertices, triangles):
    acc = {}
    for a, b, c in triangles:
        pa, pb, pc = (vertices[i][:3] for i in (a, b, c))
        u = [pb[k] - pa[k] for k in range(3)]
        w = [pc[k] - pa[k] for k in range(3)]
        front = [-(u[1] * w[2] - u[2] * w[1]), -(u[2] * w[0] - u[0] * w[2]), -(u[0] * w[1] - u[1] * w[0])]
        for i in (a, b, c):
            key = tuple(round(x, 3) for x in vertices[i][:3])
            s = acc.setdefault(key, [0.0, 0.0, 0.0])
            for k in range(3):
                s[k] += front[k]
    normals = []
    for v in vertices:
        s = acc.get(tuple(round(x, 3) for x in v[:3]))
        length = math.sqrt(sum(x * x for x in s)) if s else 0.0
        normals.append([x / length for x in s] if length > 0 else check.decode(v[3]))
    return normals


def fix(data):
    data = bytearray(data)
    report = []
    for index, (flags, vat, vertices, _, triangles) in enumerate(locate(bytes(data))):
        if vertices is None:
            report.append({'surface': index, 'skipped': 'packed motion vertices'})
            continue
        before = check.check_vertices(vertices, triangles)
        row = {'surface': index, 'vertices': len(vertices), 'outward_before': outward(vertices),
               'agreement_before': before['triangle_agreement']}
        for i, n in enumerate(rebuild(vertices, triangles)):
            struct.pack_into('<I', data, vat + i * check.VERTEX_SIZE + NORMAL_OFFSET, pack(n))
        new = [v[:3] + (struct.unpack_from('<I', data, vat + i * check.VERTEX_SIZE + NORMAL_OFFSET)[0],)
               for i, v in enumerate(vertices)]
        after = check.check_vertices(new, triangles)
        row.update(outward_after=outward(new), agreement_after=after['triangle_agreement'],
                   errors=check.errors_for(after))
        report.append(row)
    return bytes(data), report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument('files', nargs='+')
    ap.add_argument('--out-dir', help='write repaired copies here (default: rewrite in place)')
    ap.add_argument('--check-only', action='store_true')
    args = ap.parse_args(argv)
    status = 0
    for path in args.files:
        try:
            with open(path, 'rb') as f:
                fixed, report = fix(f.read())
        except (ValueError, struct.error) as exc:
            print(json.dumps({'file': path, 'error': str(exc)}))
            status = 1
            continue
        if any(r.get('errors') for r in report):
            status = 1
        if not args.check_only:
            out = os.path.join(args.out_dir, os.path.basename(path)) if args.out_dir else path
            if args.out_dir:
                os.makedirs(args.out_dir, exist_ok=True)
            with open(out, 'wb') as f:
                f.write(fixed)
        print(json.dumps({'file': os.path.basename(path), 'surfaces': report}))
    return status


if __name__ == '__main__':
    sys.exit(main())

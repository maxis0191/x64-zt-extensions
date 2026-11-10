"""Check (and fix) the LOD order of a ZoneTool IW7 .xmb model against its .xsb surfaces (stdlib only).

An IW7 XModel draws lodInfo[0] up close. The T7 -> IW7 conversion of p7_zm_teddybear wrote its six
XModelSurfs names lowest detail first (68 triangles as LOD0, 2042 as LOD5), so the bear was drawn as a
ragged 68-triangle shape at any distance (run w4/w5 frames). This lists the XModelSurfs names in the order
the .xmb stores them with each one's triangle count (from <xsurface dir>/<name>.xsb), and with --fix
rewrites the names in descending triangle order. Names are swapped in place only when they all have the
same length (ZoneTool's hashed suffixes do), so every other byte keeps its offset; LOD distances stay.

    python iw7_xmodel_lods.py <model.xmb> --xsurface <dir> [--fix] [--out <file>]
"""
import argparse
import json
import os
import re
import struct
import sys


def triangles(path):
    with open(path, 'rb') as f:
        data = f.read()
    numsurfs = struct.unpack_from('<H', data, 2 + 4 + 16)[0]
    pos = data.index(b'\0', 2 + 4 + 0x38 + 2) + 1 + 2 + 4
    return sum(struct.unpack_from('<3H', data, pos + i * 0x100)[2] for i in range(numsurfs))


def lods(data, xsurface):
    """(offset, name, triangles) for every string of the .xmb that names an existing .xsb."""
    out = []
    for m in re.finditer(rb'[A-Za-z0-9_./-]{4,}', data):
        name = m.group().decode('ascii')
        path = os.path.join(xsurface, name + '.xsb')
        if os.path.isfile(path):
            out.append((m.start(), name, triangles(path)))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument('xmb')
    ap.add_argument('--xsurface', required=True)
    ap.add_argument('--fix', action='store_true')
    ap.add_argument('--out')
    args = ap.parse_args(argv)
    with open(args.xmb, 'rb') as f:
        data = bytearray(f.read())
    found = lods(bytes(data), args.xsurface)
    tris = [t for _, _, t in found]
    ok = tris == sorted(tris, reverse=True)
    report = {'model': os.path.basename(args.xmb), 'lods': [{'name': n, 'triangles': t} for _, n, t in found],
              'descending': ok}
    if args.fix and not ok:
        if len({len(n) for _, n, _ in found}) != 1:
            report['error'] = 'names differ in length; reorder by rebuilding the model'
        else:
            order = sorted(found, key=lambda x: -x[2])
            for (offset, _, _), (_, name, _) in zip(found, order):
                data[offset:offset + len(name)] = name.encode('ascii')
            with open(args.out or args.xmb, 'wb') as f:
                f.write(data)
            report['fixed'] = [n for _, n, _ in order]
    print(json.dumps(report, indent=1))
    return 1 if (not ok and not report.get('fixed')) else 0


if __name__ == '__main__':
    sys.exit(main())

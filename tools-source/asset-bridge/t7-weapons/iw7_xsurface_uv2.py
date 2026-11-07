"""Give converted IW7 model surfaces a second UV set (ZoneTool .xsb), stdlib only.

IW7 weapon materials that take a camo (Pack-a-Punch camos, "+camoNN") use
"_2uvt" techniques, which read a second UV set with its tangent basis. Stock
camo-ready weapon surfaces (Dischord view model, flags 0x482) carry it under
flag 0x400 (ZoneTool's SURF_FLAG_MAYHEM_SELFVIS), stored per vertex in
``shProbeSimplexVertData.data2``, written last in the surface's block
(ZoneTool iw7/assets/xsurface.cpp): 24 bytes, measured on the stock data as
float u, v (equal to the first UV set) then the 2x2 basis 1, 0, 0, 1. Black
Ops III weapon meshes converted by ZoneTool have none (flags 0x84) and the
stock camo techniques drew them black. This rewrites a surface file so every
static surface carries one, built from its first UV set.

ZoneTool dump records (utils/io/assetmanager.hpp): type byte, then
ARRAY(8)/RAW(10): exists byte, [u32 count|size, data]; OFFSET(9): u32 index,
u32 array index; STRING(6): exists byte, [C string].

    python iw7_xsurface_uv2.py <in.xsb> [--out <out.xsb>] [--inspect]
"""
import argparse
import json
import struct
import sys

XMODEL_SURFS_SIZE = 0x38
XSURFACE_SIZE = 0x100
VERTEX_SIZE = 32
MOTION_VERTEX_SIZE = 48
FLAG_MOTION = 0x8
FLAG_SECONDUV = 0x100
FLAG_SELFVIS = 0x400
SECOND_UV_SIZE = 8
FLAG_UV2 = FLAG_SELFVIS   # stock camo surfaces: u, v, then a 2x2 basis
UV2_SIZE = 24
ARRAY, OFFSET, STRING, RAW = 8, 9, 6, 10
SUBDIV_PTR = 0xA0         # XSurface::subdiv
TEXCOORD = 20             # GfxPackedVertex: xyz 12, selfVisibility 4, color 4, texCoord 4
RIGID_SIZE = 16           # XRigidVertList: four u16, collision tree pointer


class Reader:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def record(self, kinds, size=None):
        """One record: (start, end, payload or None). size: element size of an array."""
        start = self.pos
        kind = self.data[self.pos]
        if kind not in kinds:
            raise ValueError("record %d at byte %d, expected %s" % (kind, start, kinds))
        self.pos += 1
        if kind == OFFSET:
            self.pos += 8
            return start, self.pos, None
        exists = self.data[self.pos]
        self.pos += 1
        if not exists:
            return start, self.pos, None
        if kind == STRING:
            end = self.data.index(b"\0", self.pos)
            payload = self.data[self.pos:end]
            self.pos = end + 1
            return start, self.pos, payload
        count, = struct.unpack_from("<I", self.data, self.pos)
        self.pos += 4
        length = count * size if kind == ARRAY else count
        payload = self.data[self.pos:self.pos + length]
        self.pos += length
        return start, self.pos, payload


def parse(data):
    """Surfaces with the byte span of their header, their vertex array and their block end."""
    r = Reader(data)
    r.record((ARRAY,), XMODEL_SURFS_SIZE)
    _, _, name = r.record((STRING,))
    _, _, heads = r.record((ARRAY,), XSURFACE_SIZE)
    heads_start = r.pos - len(heads)
    surfaces = []
    for i in range(len(heads) // XSURFACE_SIZE):
        head = heads[i * XSURFACE_SIZE:(i + 1) * XSURFACE_SIZE]
        flags, vert_count, tri_count, rigid_count = struct.unpack_from("<3HB", head, 0)
        if struct.unpack_from("<Q", head, SUBDIV_PTR)[0]:
            raise ValueError("surface %d has subdivision data (not handled)" % i)
        vsize = MOTION_VERTEX_SIZE if flags & FLAG_MOTION else VERTEX_SIZE
        _, _, verts = r.record((ARRAY, OFFSET), vsize)
        r.record((ARRAY, OFFSET), 6)                        # triangles
        _, _, rigid = r.record((ARRAY, OFFSET), RIGID_SIZE)
        for v in range(rigid_count if rigid else 0):
            tree_ptr, = struct.unpack_from("<Q", rigid, v * RIGID_SIZE + 8)
            if tree_ptr:
                raise ValueError("surface %d has a collision tree (not handled)" % i)
        for _ in range(4):                                  # blend verts, lmap unwrap, tension data, accum table
            r.record((RAW, OFFSET))
        second = None
        if flags & FLAG_SECONDUV or flags & FLAG_SELFVIS:
            size = 32 if (flags & 0x500) == 0x500 else (SECOND_UV_SIZE if flags & FLAG_SECONDUV else 24)
            _, _, second = r.record((ARRAY, OFFSET), size)
        surfaces.append({"index": i, "flags": flags, "vert_count": vert_count, "tri_count": tri_count,
                         "head": heads_start + i * XSURFACE_SIZE, "verts": verts, "end": r.pos, "second": second})
    if r.pos != len(data):
        raise ValueError("%d trailing bytes" % (len(data) - r.pos))
    return name.decode("ascii"), surfaces


def half(v):
    return struct.unpack("<e", struct.pack("<H", v))[0]


def texcoords(verts):
    """First UV set of packed vertices (two half floats)."""
    out = []
    for k in range(len(verts) // VERTEX_SIZE):
        u, v = struct.unpack_from("<2H", verts, k * VERTEX_SIZE + TEXCOORD)
        out.append((half(u), half(v)))
    return out


def second_uv_bytes(verts):
    """The camo UV records of a surface's vertices: the first set as floats, identity basis."""
    return b"".join(struct.pack("<6f", u, v, 1.0, 0.0, 0.0, 1.0) for u, v in texcoords(verts))


def add_second_uv(data):
    name, surfaces = parse(data)
    out = bytearray()
    last = 0
    added = 0
    for s in surfaces:
        if s["flags"] & (FLAG_MOTION | FLAG_SECONDUV | FLAG_SELFVIS) or s["verts"] is None:
            continue
        out += data[last:s["end"]]
        out += bytes([ARRAY, 1]) + struct.pack("<I", s["vert_count"]) + second_uv_bytes(s["verts"])
        last = s["end"]
        added += 1
    out += data[last:]
    for s in surfaces:
        if not s["flags"] & (FLAG_MOTION | FLAG_SECONDUV | FLAG_SELFVIS) and s["verts"] is not None:
            struct.pack_into("<H", out, s["head"], s["flags"] | FLAG_UV2)
    return bytes(out), {"model": name, "surfaces": len(surfaces), "second_uv_added": added}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("xsb")
    ap.add_argument("--out")
    ap.add_argument("--inspect", action="store_true", help="print each surface's flags and first second-UV values")
    args = ap.parse_args(argv)
    data = open(args.xsb, "rb").read()
    if args.inspect:
        name, surfaces = parse(data)
        for s in surfaces:
            first = texcoords(s["verts"][:VERTEX_SIZE * 3]) if s["verts"] and not s["flags"] & FLAG_MOTION else None
            second = None
            if s["second"] and (s["flags"] & 0x500) == FLAG_UV2:
                second = [[round(c, 5) for c in struct.unpack_from("<6f", s["second"], k * UV2_SIZE)]
                          for k in range(min(3, s["vert_count"]))]
                raw = s["second"][:UV2_SIZE].hex()
            else:
                raw = None
            print(json.dumps({"surface": s["index"], "flags": hex(s["flags"]), "verts": s["vert_count"],
                              "uv": first, "uv2_records": second, "uv2_raw": raw}))
        return 0
    out, report = add_second_uv(data)
    with open(args.out or args.xsb, "wb") as f:
        f.write(out)
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())

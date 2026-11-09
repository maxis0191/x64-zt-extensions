"""IW7 XModelSurfs (.xsb ZoneTool dump) reader/writer.

Layout follows x64-zt src/zonetool/zonetool/iw7/structs.hpp (XSurface 0x100, XModelSurfs 0x38) and the dump order
of iw7/assets/xsurface.cpp. Every stream is decoded into Python values and re-encoded on write.
"""
import struct

from ztdump import Reader, Writer, Rec, T_ARRAY, T_RAW
import vertex_codec as vc

MODEL_SURFS = struct.Struct("<QQH2x8i4x")            # name, surfs, numsurfs, partBits[8]  (0x38)
SURF_HEAD = struct.Struct("<HHHBB8HI4s")             # flags..pad0 (32 bytes)
SURF_PTRS = ("verts0 triIndices vb0 vb0View indexBuffer rigidVertLists blendVerts blendVertsBuffer blendVertsView "
             "lmapUnwrap vblmapBuffer vblmapView subdiv tensionData tensionAccumTable tensionAccumTableBuffer "
             "tensionAccumTableView tensionDataBuffer tensionDataView indexBufferView").split()
SURF_TAIL = struct.Struct("<ii")                      # unk (vertexLightingIndex), pad
SURF_PTRS2 = ("shProbeSimplexVertData", "shProbeSimplexVertBuffer", "shProbeSimplexVertBufferView")
assert SURF_HEAD.size + 8 * len(SURF_PTRS) + SURF_TAIL.size + 8 * 3 + 32 == 0x100

VERT = struct.Struct("<3fIIIII")                      # GfxPackedVertex / GfxPackedMotionVertex (32 bytes)
RIGID = struct.Struct("<HHHHQ")                       # XRigidVertList (16 bytes)
COLL_TREE_SIZE, COLL_NODE_SIZE, COLL_LEAF_SIZE = 56, 16, 2
SUBDIV_INFO_SIZE, SUBDIV_LEVEL_SIZE = 0x38, 0xE8

SURF_FLAG_VERTCOL_GREY, SURF_FLAG_VERTCOL_NONE, SURF_FLAG_SKINNED, SURF_FLAG_REACTIVE_MOTION = 1, 2, 4, 8
SURF_FLAG_LIGHTMAP_COORDS, SURF_FLAG_SUBDIV, SURF_FLAG_TENSION, SURF_FLAG_SELF_VISIBILITY = 0x10, 0x20, 0x40, 0x80


class Surface:
    def __init__(self):
        self.flags = 0
        self.vert_count = 0
        self.tri_count = 0
        self.rigid_count = 0
        self.subdiv_level_count = 0
        self.blend_counts = [0] * 8
        self.blend_size = 0
        self.pad0 = b"\0" * 4
        self.ptrs = {k: 0 for k in SURF_PTRS + list(SURF_PTRS2)}
        self.unk = 0
        self.pad1 = 0
        self.part_bits = [0] * 8
        # streams
        self.verts = []        # list of [x, y, z, selfvis_or_binormalsign, color, uv, normal, tangent] (packed u32s)
        self.faces = []        # list of (a, b, c)
        self.rigid = []        # list of [boneOffsetIndex, vertCount, triOffset, triCount, treePtr]
        self.trees = []        # per rigid list: None or dict(head=bytes56, leafs=Rec, nodes=Rec)
        self.blend = None      # list of u16 or None
        self.lmap = None       # bytes or None
        self.tension = None    # bytes or None
        self.tension_accum = None
        self.subdiv = None     # list of Rec (kept verbatim: no stock hero surface uses subdiv)
        self.shprobe = None    # Rec or None
        self.vert_rec = self.face_rec = self.rigid_rec = None  # offset records (never seen in practice)

    # ---------------------------------------------------------------- header
    def unpack_head(self, b):
        (self.flags, self.vert_count, self.tri_count, self.rigid_count, self.subdiv_level_count, *rest) = \
            SURF_HEAD.unpack_from(b, 0)
        self.blend_counts = list(rest[:8])
        self.blend_size, self.pad0 = rest[8], rest[9]
        o = SURF_HEAD.size
        for k in SURF_PTRS:
            self.ptrs[k] = struct.unpack_from("<Q", b, o)[0]
            o += 8
        self.unk, self.pad1 = SURF_TAIL.unpack_from(b, o)
        o += SURF_TAIL.size
        for k in SURF_PTRS2:
            self.ptrs[k] = struct.unpack_from("<Q", b, o)[0]
            o += 8
        self.part_bits = list(struct.unpack_from("<8i", b, o))

    def pack_head(self):
        out = SURF_HEAD.pack(self.flags, self.vert_count, self.tri_count, self.rigid_count, self.subdiv_level_count,
                             *self.blend_counts, self.blend_size, self.pad0)
        out += b"".join(struct.pack("<Q", self.ptrs[k]) for k in SURF_PTRS)
        out += SURF_TAIL.pack(self.unk, self.pad1)
        out += b"".join(struct.pack("<Q", self.ptrs[k]) for k in SURF_PTRS2)
        out += struct.pack("<8i", *self.part_bits)
        assert len(out) == 0x100
        return out

    # ---------------------------------------------------------------- semantic views
    def blend_groups(self):
        """Decode blendVerts: yields (vertex_index, [(bone, weight_float), ...]) for skinned verts."""
        return vc.decode_blend(self.blend or [], self.blend_counts)

    def blend_vert_total(self):
        return sum(self.blend_counts)


class ModelSurfs:
    def __init__(self):
        self.name = ""
        self.head_ptrs = (0, 0)
        self.part_bits = [0] * 8
        self.surfs = []
        self.name_rec = None


def read(blob):
    r = Reader(blob)
    ms = ModelSurfs()
    rec = r.array(MODEL_SURFS.size)
    name_p, surfs_p, numsurfs, *pb = MODEL_SURFS.unpack(rec.data)
    ms.head_ptrs, ms.part_bits = (name_p, surfs_p), pb
    ms.name = r.string().data
    srec = r.array(0x100)
    for i in range(numsurfs):
        s = Surface()
        s.unpack_head(srec.data[i * 0x100:(i + 1) * 0x100])
        ms.surfs.append(s)
    for s in ms.surfs:
        v = r.array(VERT.size)
        s.verts = [list(t) for t in VERT.iter_unpack(v.data)] if v.data else []
        f = r.array(6)
        s.faces = list(struct.iter_unpack("<3H", f.data)) if f.data else []
        rl = r.array(RIGID.size)
        s.rigid = [list(t) for t in RIGID.iter_unpack(rl.data)] if rl.data else []
        s.trees = []
        for k in range(s.rigid_count):
            if s.rigid and s.rigid[k][4]:
                t = {"head": r.array(COLL_TREE_SIZE)}
                head = t["head"].data
                leafs_p, nodes_p = struct.unpack_from("<Q", head, 48)[0], struct.unpack_from("<Q", head, 32)[0]
                # dump order: leafs then nodes
                t["leafs"] = r.array(COLL_LEAF_SIZE) if leafs_p else None
                t["nodes"] = r.array(COLL_NODE_SIZE) if nodes_p else None
                s.trees.append(t)
            else:
                s.trees.append(None)
        b = r.raw()
        s.blend = list(struct.unpack("<%dH" % (len(b.data) // 2), b.data)) if b.data else None
        s.lmap = r.raw().data
        s.tension = r.raw().data
        s.tension_accum = r.raw().data
        if s.ptrs["subdiv"]:
            info = r.array(SUBDIV_INFO_SIZE)
            recs = [info]
            if struct.unpack_from("<Q", info.data, 0)[0]:
                recs.append(r.array(SUBDIV_LEVEL_SIZE))
                for _ in range(s.subdiv_level_count):
                    recs += [r.raw() for _ in range(10)]
            s.subdiv = recs
        if (s.flags & 0x500) == 0x500:
            s.shprobe = r.array(32)
        elif s.flags & 0x100:
            s.shprobe = r.array(8)
        elif s.flags & 0x400:
            s.shprobe = r.array(24)
    if not r.at_end():
        raise ValueError("trailing bytes at 0x%x" % r.p)
    return ms


def write(ms):
    w = Writer()
    w.array(MODEL_SURFS.pack(ms.head_ptrs[0], ms.head_ptrs[1], len(ms.surfs), *ms.part_bits), 1)
    w.string(ms.name)
    w.array(b"".join(s.pack_head() for s in ms.surfs), len(ms.surfs))
    for s in ms.surfs:
        w.array(b"".join(VERT.pack(*v) for v in s.verts), len(s.verts))
        w.array(b"".join(struct.pack("<3H", *f) for f in s.faces), len(s.faces))
        w.array(b"".join(RIGID.pack(*x) for x in s.rigid), len(s.rigid))
        for t in s.trees[:s.rigid_count]:
            if t:
                w.rec(t["head"])
                if t["leafs"]:
                    w.rec(t["leafs"])
                if t["nodes"]:
                    w.rec(t["nodes"])
        w.raw(struct.pack("<%dH" % len(s.blend), *s.blend) if s.blend else None)
        w.raw(s.lmap)
        w.raw(s.tension)
        w.raw(s.tension_accum)
        if s.ptrs["subdiv"] and s.subdiv:
            for rr in s.subdiv:
                w.rec(rr)
        if s.shprobe is not None:
            w.rec(s.shprobe)
    return w.bytes()

"""IW7 XModel (.xmb ZoneTool dump) reader/writer.

Struct layout: x64-zt src/zonetool/zonetool/iw7/structs.hpp (XModel 0x2E0, XModelLodInfo 0x40);
dump order: iw7/assets/xmodel.cpp xmodel::dump. Havok physics LOD data lives in a separate file (xmodel/<name>_lod*)
and is not part of the .xmb.
"""
import math
import struct

from ztdump import Reader, Writer

XMODEL_SIZE = 0x2E0
FIELDS = {  # name: (offset, struct fmt)
    "hasLods": (9, "B"), "maxLoadedLod": (10, "B"), "numLods": (11, "B"), "collLod": (12, "B"),
    "shadowCutoffLod": (13, "B"), "characterCollBoundsType": (14, "B"), "flags": (16, "i"),
    "numBones": (20, "B"), "numRootBones": (21, "B"), "numReactiveMotionParts": (22, "B"),
    "numClientBones": (24, "H"), "numsurfs": (26, "H"), "scale": (28, "f"), "numCollSurfs": (32, "H"),
    "contents": (36, "i"), "radius": (40, "f"), "bounds": (44, "6f"), "memUsage": (68, "i"),
    "physicsLODDataSize": (72, "I"), "physicsUsageCounter": (76, "3i"),
    "scriptableMoverDef": (88, "Q"), "proceduralBones": (96, "Q"), "aimAssistBones": (104, "Q"),
    "numAimAssistBones": (112, "B"), "edgeLength": (116, "f"), "noScalePartBits": (120, "8I"),
    "boneNames": (152, "Q"), "parentList": (160, "Q"), "tagAngles": (168, "Q"), "tagPositions": (176, "Q"),
    "partClassification": (184, "Q"), "baseMat": (192, "Q"), "reactiveMotionParts": (200, "Q"),
    "reactiveMotionTweaks": (208, "Q"), "materialHandles": (216, "Q"),
    "collSurfs": (608, "Q"), "boneInfo": (616, "Q"), "invHighMipRadius": (624, "Q"), "physicsAsset": (632, "Q"),
    "physicsFXShape": (640, "Q"), "physicsLODData": (648, "Q"), "physicsLODDataNameCount": (656, "I"),
    "physicsLODDataNames": (664, "Q"), "impactType": (672, "B"), "unknown03Count": (688, "B"),
    "unknownVec3Count": (705, "B"), "unknown04Count": (721, "B"),
}
LOD = struct.Struct("<fHHQ8iQiB3x")  # dist, numsurfs, surfIndex, modelSurfs, partBits[8], surfs, subdivMask, flags


class XModel:
    def __init__(self):
        self.head = bytearray(XMODEL_SIZE)
        self.name = ""
        self.bone_names = []
        self.parents = []          # numBones+numClient-numRoot u8 (relative: parent = index - value)
        self.tag_angles = []       # (x, y, z, base) shorts: quantized quaternion (x,y,z,w) * 32767
        self.tag_positions = []    # (x, y, z) float
        self.part_class = b""
        self.base_mat = []         # (qx,qy,qz,qw, tx,ty,tz, transWeight)
        self.rm_parts = None
        self.rm_tweaks = None
        self.coll_surfs = None
        self.bone_info = []        # (midx,midy,midz, halfx,halfy,halfz, radiusSquared)
        self.inv_high_mip = []
        self.materials = []        # material names
        self.material_ptrs = b""   # raw pointer array (values only matter as non-null)
        self.lod_surfs = [None] * 6
        self.physics_asset = self.physics_fx = None
        self.physics_lod_names = []
        self.scriptable = self.procedural = None
        self.aim_assist = []
        self.unknown03 = self.unknown_vec3 = self.unknown04 = None
        self.recs = {}

    def get(self, k):
        off, fmt = FIELDS[k]
        v = struct.unpack_from("<" + fmt, self.head, off)
        return v[0] if len(v) == 1 else list(v)

    def set(self, k, v):
        off, fmt = FIELDS[k]
        struct.pack_into("<" + fmt, self.head, off, *(v if isinstance(v, (list, tuple)) else [v]))

    def lod(self, i):
        return list(LOD.unpack_from(self.head, 224 + i * 64))

    def set_lod(self, i, vals):
        LOD.pack_into(self.head, 224 + i * 64, *vals)

    @property
    def n_bones(self):
        return self.get("numBones") + self.get("numClientBones")

    def parent_index(self, i):
        """Absolute parent index of bone i, or -1 for roots (parentList stores index - parent)."""
        nr = self.get("numRootBones")
        return -1 if i < nr else i - self.parents[i - nr]

    def local_quat(self, i):
        nr = self.get("numRootBones")
        if i < nr:
            return (0.0, 0.0, 0.0, 1.0)
        x, y, z, w = self.tag_angles[i - nr]
        return tuple(c / 32768.0 for c in (x, y, z, w))


def _arr(rec, fmt):
    if rec.data is None:
        return []
    s = struct.Struct("<" + fmt)
    return [t if len(t) > 1 else t[0] for t in s.iter_unpack(rec.data)]


def read(blob):
    r = Reader(blob)
    m = XModel()
    m.head = bytearray(r.array(XMODEL_SIZE).data)
    m.name = r.string().data
    for _ in range(m.n_bones):
        m.bone_names.append(r.string().data)
    m.recs["parents"] = rp = r.array(1)
    m.parents = list(rp.data or b"")
    m.tag_angles = _arr(r.array(8), "4h")
    m.tag_positions = _arr(r.array(12), "3f")
    m.part_class = r.array(1).data
    m.base_mat = _arr(r.array(32), "8f")
    m.rm_parts = r.array(16)
    m.rm_tweaks = r.array(16)
    m.coll_surfs = r.array(36)
    m.bone_info = _arr(r.array(28), "7f")
    m.inv_high_mip = _arr(r.array(2), "H")
    mh = r.array(8)
    m.material_ptrs = mh.data
    m.material_recs = [r.asset() for _ in range(m.get("numsurfs"))]
    m.materials = [r.resolve(x).data for x in m.material_recs]
    m._materials_src = list(m.materials)
    m.lod_surfs = [r.asset().data for _ in range(6)]
    m.physics_asset = r.asset().data
    m.physics_fx = r.asset().data
    m.physics_lod_names = [r.string().data for _ in range(m.get("physicsLODDataNameCount"))]
    m.scriptable = r.asset().data
    m.procedural = r.asset().data
    m.aim_assist = [r.string().data for _ in range(m.get("numAimAssistBones"))]
    m.unknown03 = r.array(1)
    m.unknown_vec3 = r.array(12)
    m.unknown04 = r.array(24)
    if not r.at_end():
        raise ValueError("trailing bytes at 0x%x" % r.p)
    return m


def _pack(rows, fmt):
    s = struct.Struct("<" + fmt)
    return b"".join(s.pack(*(row if isinstance(row, (list, tuple)) else [row])) for row in rows)


def write(m):
    w = Writer()
    w.array(m.head, 1)
    w.string(m.name)
    for b in m.bone_names:
        w.string(b)
    w.array(bytes(m.parents), len(m.parents))
    w.array(_pack(m.tag_angles, "4h"), len(m.tag_angles))
    w.array(_pack(m.tag_positions, "3f"), len(m.tag_positions))
    w.array(m.part_class, len(m.part_class or b""))
    w.array(_pack(m.base_mat, "8f"), len(m.base_mat))
    w.rec(m.rm_parts)
    w.rec(m.rm_tweaks)
    w.rec(m.coll_surfs)
    w.array(_pack(m.bone_info, "7f"), len(m.bone_info))
    w.array(_pack(m.inv_high_mip, "H"), len(m.inv_high_mip))
    w.array(m.material_ptrs, len(m.materials))
    recs = getattr(m, "material_recs", None)
    if recs and [x.data if x.offset is None else None for x in recs] is not None and len(recs) == len(m.materials) \
            and getattr(m, "_materials_src", None) == m.materials:
        for x in recs:
            w.rec(x)
    else:
        for mat in m.materials:
            w.asset(mat)
    for s in m.lod_surfs:
        w.asset(s)
    w.asset(m.physics_asset)
    w.asset(m.physics_fx)
    for s in m.physics_lod_names:
        w.string(s)
    w.asset(m.scriptable)
    w.asset(m.procedural)
    for s in m.aim_assist:
        w.string(s)
    w.rec(m.unknown03)
    w.rec(m.unknown_vec3)
    w.rec(m.unknown04)
    return w.bytes()


# ------------------------------------------------------------------ math helpers
def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def qrot(q, v):
    x, y, z, w = q
    vx, vy, vz = v
    tx, ty, tz = 2 * (y * vz - z * vy), 2 * (z * vx - x * vz), 2 * (x * vy - y * vx)
    return (vx + w * tx + (y * tz - z * ty), vy + w * ty + (z * tx - x * tz), vz + w * tz + (x * ty - y * tx))


def qnorm(q):
    n = math.sqrt(sum(c * c for c in q)) or 1.0
    return tuple(c / n for c in q)

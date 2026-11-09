"""Build IW7 XModel + XModelSurfs ZoneTool dumps (.xmb/.xsb) from a blender_export.py JSON.

python -I build_model.py <mesh.json> --base-xmodel <stock .xmb> --name <new model name> --out <dump root>
       [--material-map <json {"blender material": "iw7 material"}>] [--report <report.json>]

Writes <out>/xmodel/<name>.xmb and <out>/xsurface/<name>_lod0.xsb (one LOD). The skeleton (bone list/order, parents,
rest pose, part classification, procedural bones, collision bounds type, ...) is copied from --base-xmodel; meshes
must be weighted to bones of that skeleton (names). Materials: --material-map, else a stock material of the base
model whose name after the last '/' equals the Blender material name, else the Blender name is used as is.
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vertex_codec as vc  # noqa: E402
import xmodel  # noqa: E402
import xsurface  # noqa: E402

MAX_INFLUENCES = 4          # stock IW7 heroes use groups 0..3; ZoneTool T7->IW7 and IW7->H1 converters handle 4
MAX_SURF_VERTS = 0xFFFF     # XSurface.vertCount / Face indices are u16
MAX_SURF_TRIS = 0xFFFF      # XSurface.triCount u16
FLAGS_SKINNED = xsurface.SURF_FLAG_VERTCOL_NONE | xsurface.SURF_FLAG_SKINNED | xsurface.SURF_FLAG_SELF_VISIBILITY
SELFVIS_DEFAULT = None


def pack_selfvis(v):
    """ZoneTool XSurfacePackSelfVisibility (game/shared.cpp)."""
    c = lambda x: min(max(x, 0.0), 1.0)
    a = int(c((v[0] + 1.0) * 0.5) * 511.0 + 0.5)
    b = int(c((v[1] + 1.0) * 0.5) * 511.0 + 0.5)
    z = int(c(v[2]) * 127.0 + 0.5)
    w = int(c(v[3]) * 127.0 + 0.5)
    return (a | (((z | (w << 7)) << 9 | b) << 9)) & 0xFFFFFFFF


SELFVIS_DEFAULT = pack_selfvis([0.0, 0.0, 1.0, 0.0])  # value the ZoneTool T7->IW7 converter writes


def quantize_weights(raw, bone_index, problems):
    """raw: [[bone name, weight], ...] -> [(bone index, u16 weight or None for the implicit first), ...]."""
    acc = {}
    for name, w in raw:
        if name not in bone_index:
            problems["unknown_bones"][name] = problems["unknown_bones"].get(name, 0) + 1
            continue
        acc[bone_index[name]] = acc.get(bone_index[name], 0.0) + w
    inf = sorted(acc.items(), key=lambda x: (-x[1], x[0]))
    if not inf:
        problems["unweighted_verts"] += 1
        inf = [(bone_index.get("j_mainroot", 0), 1.0)]
    if len(inf) > MAX_INFLUENCES:
        problems["clamped_verts"] += 1
        inf = inf[:MAX_INFLUENCES]
    tot = sum(w for _, w in inf)
    inf = [(b, w / tot) for b, w in inf]
    out = [(inf[0][0], None)]
    used = 0
    for b, w in inf[1:]:
        q = int(round(w * 65536.0))
        if q <= 0:
            continue
        q = min(q, 65535 - used)  # first weight stays > 0
        if q <= 0:
            continue
        used += q
        out.append((b, q))
    return out


def build_surface(src, bone_index, problems, vlight_base):
    verts = src["verts"]
    infl = [quantize_weights(v["w"], bone_index, problems) for v in verts]
    order = sorted(range(len(verts)), key=lambda i: (len(infl[i]), i))   # blend groups: 1-bone verts first
    remap = {old: new for new, old in enumerate(order)}
    s = xsurface.Surface()
    s.flags = FLAGS_SKINNED
    s.vert_count = len(verts)
    s.tri_count = len(src["tris"])
    for i in order:
        v = verts[i]
        p = v["p"]
        top = 3 if v["s"] >= 0 else 0  # tangent bits 30-31: bitangent sign (checked against stock in m2_proof.py)
        s.verts.append([float(p[0]), float(p[1]), float(p[2]), SELFVIS_DEFAULT, 0xFFFFFFFF,
                        vc.pack_uv(v["uv"][0], v["uv"][1]), vc.pack_normal(v["n"], 3), vc.pack_normal(v["t"], top)])
    # Blender/glTF counter-clockwise -> IW7 order (a, c, b)
    s.faces = [(remap[a], remap[c], remap[b]) for a, b, c in src["tris"]]
    blend, counts = vc.encode_blend([infl[i] for i in order])
    s.blend, s.blend_counts = blend, counts
    s.blend_size = 2 * len(blend)
    s.rigid_count, s.rigid, s.trees = 0, [], []
    bones = set()
    for inf in infl:
        bones.update(b for b, _ in inf)
    s.part_bits = vc.part_bits(bones)
    s.unk = vlight_base
    # pointer fields: ZoneTool only tests subdiv / collision tree pointers; keep stream pointers non-null like dumps
    for k in s.ptrs:
        s.ptrs[k] = 0
    s.ptrs["verts0"] = s.ptrs["triIndices"] = s.ptrs["blendVerts"] = 1
    return s


class StockTransfer:
    """Per-vertex lighting data of a stock body (LOD0 .xsb) moved to new vertices by nearest bind-pose position:
    the packed self-visibility and the 8-byte SH probe simplex record (flag 0x100: 4 probe indices u8 + 4 weights u8
    summing to 255 over the character's 6 probe points). 'mopw' hero materials light the model from it: without it
    a writer-built body renders black (run o2_200)."""

    CELL = 2.0

    def __init__(self, xsb_path):
        ms = xsurface.read(open(xsb_path, "rb").read())
        self.grid = {}
        self.flags = None
        for s in ms.surfs:
            if not (s.shprobe is not None and s.shprobe.count == s.vert_count and len(s.shprobe.data) == 8 * s.vert_count):
                continue
            if s.flags & xsurface.SURF_FLAG_SKINNED and self.flags is None:
                self.flags = s.flags
            for k, v in enumerate(s.verts):
                key = tuple(int(math.floor(c / self.CELL)) for c in v[:3])
                self.grid.setdefault(key, []).append((v[0], v[1], v[2], v[3], s.shprobe.data[8 * k:8 * k + 8],
                                                      vc.unpack_normal(v[6])))
        if not self.grid:
            raise SystemExit("transfer source has no SH probe records: " + xsb_path)
        self.max_dist = 0.0

    def nearest(self, p, n=None):
        """Nearest stock vertex; among vertices within 0.05 in (seam duplicates, overlapping surfaces) the one with
        the closest normal wins."""
        c = tuple(int(math.floor(x / self.CELL)) for x in p)
        best = None
        for r in range(0, 64):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    for dz in range(-r, r + 1):
                        if max(abs(dx), abs(dy), abs(dz)) != r:
                            continue
                        for q in self.grid.get((c[0] + dx, c[1] + dy, c[2] + dz), ()):
                            d = math.sqrt((q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 + (q[2] - p[2]) ** 2)
                            score = d + (0.05 * (1.0 - sum(a * b for a, b in zip(n, q[5]))) if n is not None else 0.0)
                            if best is None or score < best[0]:
                                best = (score, d, q)
            if best is not None and best[1] <= r * self.CELL:
                break
        if best is None:
            raise ValueError("no stock vertex near %r" % (p,))
        self.max_dist = max(self.max_dist, best[1])
        return best[2]
    def apply(self, s):
        sh = bytearray()
        for v in s.verts:
            q = self.nearest(v[:3], vc.unpack_normal(v[6]))
            v[3] = q[3]
            sh += q[4]
        s.shprobe = xsurface.Rec(xsurface.T_ARRAY, bytes(sh), s.vert_count)
        s.flags = self.flags or (s.flags | 0x300)


def split_surface(src):
    """Split a surface whose vertex or triangle count exceeds the u16 limits (greedy by triangles)."""
    if len(src["verts"]) <= MAX_SURF_VERTS and len(src["tris"]) <= MAX_SURF_TRIS:
        return [src]
    parts, cur, vmap = [], None, None
    for tri in src["tris"]:
        if cur is None or len(cur["verts"]) + 3 > MAX_SURF_VERTS or len(cur["tris"]) >= MAX_SURF_TRIS:
            cur = dict(src, verts=[], tris=[])
            vmap = {}
            parts.append(cur)
        t = []
        for k in tri:
            if k not in vmap:
                vmap[k] = len(cur["verts"])
                cur["verts"].append(src["verts"][k])
            t.append(vmap[k])
        cur["tris"].append(t)
    return parts


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mesh")
    ap.add_argument("--base-xmodel", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--material-map", default="")
    ap.add_argument("--surface-order", default="", help="comma list of Blender material names giving surface order")
    ap.add_argument("--lod-dist", type=float, default=1000000.0)
    ap.add_argument("--report", default="")
    ap.add_argument("--transfer-from", default="",
                    help="stock LOD0 .xsb of the base model: copy per-vertex self-visibility and SH probe simplex "
                         "records from the nearest stock vertex (required for 'mopw' hero materials)")
    a = ap.parse_args(argv)
    transfer = StockTransfer(a.transfer_from) if a.transfer_from else None

    mesh = json.load(open(a.mesh))
    base = xmodel.read(open(a.base_xmodel, "rb").read())
    bone_index = {n: i for i, n in enumerate(base.bone_names)}
    problems = {"unknown_bones": {}, "unweighted_verts": 0, "clamped_verts": 0}

    # skeleton check: exported armature heads vs the stock base pose (baseMat translations, inches)
    skel = {"checked": 0, "max_err_in": 0.0, "missing": []}
    if mesh.get("armature"):
        for b in mesh["armature"]["bones"]:
            i = bone_index.get(b["name"])
            if i is None:
                skel["missing"].append(b["name"])
                continue
            t = base.base_mat[i][4:7]
            skel["checked"] += 1
            skel["max_err_in"] = max(skel["max_err_in"], max(abs(x - y) for x, y in zip(t, b["head"])))

    mmap = json.load(open(a.material_map)) if a.material_map else {}
    stock_by_short = {}
    for m in base.materials:
        if m:
            stock_by_short.setdefault(m.split("/")[-1], m)

    srcs = mesh["surfaces"]
    if a.surface_order:
        order = a.surface_order.split(",")
        srcs = sorted(srcs, key=lambda s: (order.index(s["material"]) if s["material"] in order else len(order),
                                           s["object"]))
    surfaces, materials, inv_mip = [], [], []
    base_lod0 = base.lod(0)
    stock_inv = {}
    for k in range(base_lod0[1]):
        mat = base.materials[base_lod0[2] + k]
        if mat and k < len(base.inv_high_mip):
            stock_inv.setdefault(mat, base.inv_high_mip[base_lod0[2] + k])
    vbase = 0
    for src in srcs:
        for part in split_surface(src):
            s = build_surface(part, bone_index, problems, vbase)
            if transfer:
                transfer.apply(s)
            vbase += s.vert_count
            surfaces.append(s)
            short = part["material"].split(".")[0] if part["material"] not in mmap else part["material"]
            mat = mmap.get(part["material"]) or stock_by_short.get(short) or part["material"]
            materials.append(mat)
            inv_mip.append(stock_inv.get(mat, 0xFFFF))

    ms = xsurface.ModelSurfs()
    ms.name = a.name + "_lod0"
    ms.head_ptrs = (1, 1)
    union = set()
    for s in surfaces:
        union |= vc.surface_bones(s)
    ms.part_bits = vc.part_bits(union)
    ms.surfs = surfaces

    m = base
    m.name = a.name
    m.set("numsurfs", len(surfaces))
    m.set("numLods", 1)
    m.set("hasLods", 0)
    m.materials = materials
    m.material_recs = None
    m.material_ptrs = b"\1" * 8 * len(materials)
    m.inv_high_mip = inv_mip
    m.lod_surfs = [ms.name, None, None, None, None, None]
    for i in range(6):
        lod = [a.lod_dist, 0, 0, 0] + [0] * 8 + [0, 0, 0]
        if i == 0:
            lod = [a.lod_dist, len(surfaces), 0, 1] + ms.part_bits + [0, 0, 0]
        m.set_lod(i, lod)
    pts = [v[:3] for s in surfaces for v in s.verts]
    mins = [min(p[i] for p in pts) for i in range(3)]
    maxs = [max(p[i] for p in pts) for i in range(3)]
    half = [(maxs[i] - mins[i]) / 2 for i in range(3)]
    m.set("bounds", [half[i] + mins[i] for i in range(3)] + half)
    m.set("radius", max(math.sqrt(p[0] ** 2 + p[1] ** 2 + p[2] ** 2) for p in pts))

    os.makedirs(os.path.join(a.out, "xmodel"), exist_ok=True)
    os.makedirs(os.path.join(a.out, "xsurface"), exist_ok=True)
    xsb = xsurface.write(ms)
    xmb = xmodel.write(m)
    # self check: the dumps read back to the same values
    assert xsurface.write(xsurface.read(xsb)) == xsb and xmodel.write(xmodel.read(xmb)) == xmb
    open(os.path.join(a.out, "xsurface", ms.name + ".xsb"), "wb").write(xsb)
    open(os.path.join(a.out, "xmodel", a.name + ".xmb"), "wb").write(xmb)
    rep = {"name": a.name, "surfaces": [{"material": mt, "verts": s.vert_count, "tris": s.tri_count,
                                         "blend_counts": s.blend_counts[:4]} for s, mt in zip(surfaces, materials)],
           "problems": problems, "skeleton_check": skel,
           "transfer": {"source": a.transfer_from, "max_dist_in": transfer.max_dist, "flags": hex(transfer.flags or 0)}
           if transfer else None, "bounds": m.get("bounds"), "radius": m.get("radius")}
    if a.report:
        json.dump(rep, open(a.report, "w"), indent=1)
    print(json.dumps(rep)[:1500])
    if problems["unknown_bones"] or skel["missing"]:
        sys.exit(2)


if __name__ == "__main__":
    main()

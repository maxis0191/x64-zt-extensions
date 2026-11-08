"""Write rigid IW7 models (ZoneTool .xmb + .xsb sources) from triangle meshes (numpy).

Conventions measured on stock IW7 dumps (cp_disco props, 2026-11-08, see README):
* GfxPackedVertex: xyz float; selfVisibility 0x01FE0000; colour 0xFFFFFFFF; UV half2 (D3D top-left);
  normal/tangent 10:10:10 ((v + 1) / 2 * 1023); normal high bits 0b11; tangent = dP/du, its high bits
  0b00 when dP/dv = +(N x T) and 0b11 when dP/dv = -(N x T).
* Triangles are clockwise seen from the front (stock: (b - a) x (c - a) opposes the vertex normal):
  input triangles are counter-clockwise (glTF, Blender) and are reversed here.
* Surface flags 0x80 (self visibility), one rigid vertex list on bone 0, no collision tree, no
  lightmap/blend/tension/subdiv data: the layout of ZoneTool's T7 -> IW7 converted p7_zm_teddybear,
  which renders textured and lit in a private engine run (iwz-stage2 audio w6).
* XModel: one bone (tag_origin), up to 6 LODs, numsurfs = all LOD surfaces, physics none (world
  collision is generated separately), radius/bounds from the LOD0 mesh, invHighMipRadius from UV
  density (stock bench and teddy: about 330000 / inches per UV unit).
Surfaces above 65535 vertices are split.
"""
import os
import struct

import numpy as np

import iw7_xmodel_io as io

SELFVIS = 0x01FE0000
COLOR = 0xFFFFFFFF
HIGH = 0xC0000000
SURF_FLAGS = 0x80
PARTBIT_BONE0 = 0x80000000
MIP_K = 330000.0
MAX_VERTS = 65535
LAST_LOD_DIST = 20000.0


def pack_unit(v):
    q = np.clip(np.rint((np.clip(v, -1.0, 1.0) + 1.0) * 0.5 * 1023.0), 0, 1023).astype(np.uint32)
    return q[:, 0] | (q[:, 1] << 10) | (q[:, 2] << 20)


def pack_uv(uv):
    h = uv.astype(np.float16)
    return np.ascontiguousarray(h).view(np.uint32).reshape(-1)


def weld(P, N, UV, tris, eps=1e-4):
    """Merge vertices that share position, normal and UV (glTF exports are often unwelded)."""
    key = np.concatenate([np.round(P / eps), np.round(N * 1e4), np.round(UV * 1e5)], 1).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.reshape(-1)
    return P[first], N[first], UV[first], inv[tris]


def face_normals(P, tris):
    a, b, c = P[tris[:, 0]], P[tris[:, 1]], P[tris[:, 2]]
    return np.cross(b - a, c - a)          # CCW front: points outward


def smooth_normals(P, tris):
    fn = face_normals(P, tris)
    n = np.zeros_like(P)
    for k in range(3):
        np.add.at(n, tris[:, k], fn)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


def tangents(P, N, UV, tris):
    """Per-vertex tangent (dP/du, orthogonalised) and bitangent sign (+1: dP/dv = N x T)."""
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    e1, e2 = P[b] - P[a], P[c] - P[a]
    d1, d2 = UV[b] - UV[a], UV[c] - UV[a]
    r = d1[:, 0] * d2[:, 1] - d2[:, 0] * d1[:, 1]
    ok = np.abs(r) > 1e-12
    r = np.where(ok, r, 1.0)
    tu = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) / r[:, None]
    bv = (e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) / r[:, None]
    tu[~ok] = 0
    bv[~ok] = 0
    T = np.zeros_like(P)
    B = np.zeros_like(P)
    for k in range(3):
        np.add.at(T, tris[:, k], tu)
        np.add.at(B, tris[:, k], bv)
    T = T - N * np.sum(T * N, 1, keepdims=True)
    bad = np.linalg.norm(T, axis=1) < 1e-9
    if bad.any():            # no UV gradient: any vector orthogonal to N
        alt = np.where(np.abs(N[:, 0:1]) < 0.9, [[1.0, 0, 0]], [[0, 1.0, 0]])
        alt = alt - N * np.sum(alt * N, 1, keepdims=True)
        T[bad] = alt[bad]
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
    sign = np.where(np.sum(np.cross(N, T) * B, 1) >= 0, 1, -1)
    return T, sign


def uv_density(P, UV, tris):
    """Inches per UV unit (sqrt of world area / UV area)."""
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    wa = 0.5 * np.linalg.norm(np.cross(P[b] - P[a], P[c] - P[a]), axis=1).sum()
    d1, d2 = UV[b] - UV[a], UV[c] - UV[a]
    ua = 0.5 * np.abs(d1[:, 0] * d2[:, 1] - d2[:, 0] * d1[:, 1]).sum()
    return float(np.sqrt(wa / ua)) if ua > 1e-12 else 64.0


def surface_record(P, N, UV, tris):
    """One IW7 XSurface (dict for iw7_xmodel_io.write_xsurfs). tris are counter-clockwise front."""
    T, sign = tangents(P, N, UV, tris)
    v = np.zeros(len(P), io.VERT_DTYPE)
    v['xyz'] = P.astype(np.float32)
    v['selfvis'] = SELFVIS
    v['color'] = COLOR
    v['uv'] = pack_uv(UV)
    v['normal'] = pack_unit(N) | np.uint32(HIGH)
    v['tangent'] = pack_unit(T) | np.where(sign > 0, np.uint32(0), np.uint32(HIGH)).astype(np.uint32)
    iw_tris = tris[:, [0, 2, 1]].astype(np.uint16)          # clockwise
    head = bytearray(io.XSURFACE_SIZE)
    struct.pack_into('<3H2B', head, 0, SURF_FLAGS, len(P), len(tris), 1, 0)
    struct.pack_into('<Q', head, 32, 1)       # verts0 (non-null marker)
    struct.pack_into('<Q', head, 40, 1)       # triIndices
    struct.pack_into('<Q', head, 72, 1)       # rigidVertLists
    struct.pack_into('<I', head, io.XS['partBits'], PARTBIT_BONE0)
    return {'head': head, 'flags': SURF_FLAGS, 'verts': v, 'tris': iw_tris,
            'rigid': [{'bone': 0, 'verts': len(P), 'tri_offset': 0, 'tris': len(tris), 'tree': None}],
            'blend': None, 'lmap': None, 'tension': None, 'tension_accum': None, 'shprobe': None}


def split_surface(P, N, UV, tris):
    """Yield (P, N, UV, tris) chunks with at most MAX_VERTS vertices each."""
    if len(P) <= MAX_VERTS:
        yield P, N, UV, tris
        return
    start = 0
    while start < len(tris):
        used = {}
        end = start
        while end < len(tris):
            new = [i for i in tris[end] if i not in used]
            if len(used) + len(new) > MAX_VERTS:
                break
            for i in new:
                used[i] = len(used)
            end += 1
        idx = np.array(list(used.keys()))
        remap = np.vectorize(used.get)
        yield P[idx], N[idx], UV[idx], remap(tris[start:end])
        start = end


MIN_AGREEMENT = 0.9


def prepare(group, recompute_normals=False, stats=None):
    """Drop degenerate triangles; keep the source normals when they agree with the faces (>= 90 % of the
    corners), else rebuild them with crease_normals (GrayWolf decodes some BO3 meshes' normals wrongly:
    p7_zm_teddybear 54 %); weld."""
    P, N, UV, tris = group['P'], group['N'], group['UV'], group['tris']
    fn = face_normals(P, tris)
    tris = tris[np.linalg.norm(fn, axis=1) > 1e-10]
    agree = normal_agreement(P, N, tris) if np.any(N) else 0.0
    rebuilt = recompute_normals or agree < MIN_AGREEMENT
    if rebuilt:
        N3 = crease_normals(P, tris)
        P = P[tris].reshape(-1, 3)
        UV = UV[tris].reshape(-1, 2)
        N = N3.reshape(-1, 3)
        tris = np.arange(len(P)).reshape(-1, 3)
    P, N, UV, tris = weld(P, N, UV, tris)
    if stats is not None:
        stats.update(normal_agreement_source=round(agree, 3), normals_rebuilt=bool(rebuilt),
                     normal_agreement=round(normal_agreement(P, N, tris), 3))
    return P, N, UV, tris


def build_model(name, lods, out_dir, bone='tag_origin', recompute_normals=False):
    """lods: [{'dist': float, 'groups': {material: {'P','N','UV','tris'}}}], LOD0 first, most detailed.
    Writes <out>/xmodel/<name>.xmb and <out>/xsurface/<name>_lod<i>.xsb; returns a report dict."""
    if not 1 <= len(lods) <= 6:
        raise ValueError('1..6 LODs required')
    os.makedirs(os.path.join(out_dir, 'xmodel'), exist_ok=True)
    os.makedirs(os.path.join(out_dir, 'xsurface'), exist_ok=True)
    materials, inv_mip, lod_names, report = [], [], [], {'name': name, 'lods': []}
    lod_rows = []
    all_p = []
    surf_index = 0
    prev_tris = None
    for li, lod in enumerate(lods):
        surfs = []
        tri_total = 0
        for mat in sorted(lod['groups']):
            st = {}
            P, N, UV, tris = prepare(lod['groups'][mat], recompute_normals, st)
            if len(tris) == 0:
                continue
            if li == 0:
                report.setdefault('normals', {})[mat] = st
            if li == 0:
                all_p.append(P)
            for cP, cN, cUV, ctris in split_surface(P, N, UV, tris):
                surfs.append(surface_record(cP, cN, cUV, ctris))
                materials.append(mat)
                inv_mip.append(int(min(65535, max(1, MIP_K / uv_density(cP, cUV, ctris)))))
                tri_total += len(ctris)
        if not surfs:
            raise ValueError('LOD %d of %s has no triangles' % (li, name))
        if prev_tris is not None and tri_total > prev_tris:
            raise ValueError('LOD %d has more triangles (%d) than LOD %d (%d): LODs must go from the most '
                             'to the least detailed' % (li, tri_total, li - 1, prev_tris))
        prev_tris = tri_total
        lname = '%s_lod%d' % (name, li)
        sh = bytearray(io.XMODELSURFS_SIZE)
        struct.pack_into('<QQ', sh, 0, 1, 1)
        struct.pack_into('<I', sh, 20, PARTBIT_BONE0)
        with open(os.path.join(out_dir, 'xsurface', lname + '.xsb'), 'wb') as f:
            f.write(io.write_xsurfs({'head': sh, 'name': lname, 'surfs': surfs}))
        # lodInfo.dist is the distance where this LOD hands over to the next (stock bench 165 / 835 / 20879):
        # the last LOD keeps the model up to LAST_LOD_DIST unless the caller gives a larger value
        dist = float(lod.get('dist') or 0.0)
        if li == len(lods) - 1:
            dist = max(dist, LAST_LOD_DIST)
        elif dist <= 0:
            raise ValueError('LOD %d of %s needs a switch distance' % (li, name))
        lod_rows.append((dist, len(surfs), surf_index))
        surf_index += len(surfs)
        lod_names.append(lname)
        report['lods'].append({'name': lname, 'dist': lod['dist'], 'surfaces': len(surfs), 'tris': tri_total})
    P = np.concatenate(all_p)
    lo, hi = P.min(0), P.max(0)
    mid, half = (lo + hi) / 2, (hi - lo) / 2
    radius = float(np.max(np.linalg.norm(P - mid, axis=1)))
    head = bytearray(io.XMODEL_SIZE)
    struct.pack_into('<Q', head, 0, 1)
    head[io.XM['hasLods']] = 1 if len(lods) > 1 else 0
    head[io.XM['numLods']] = len(lods)
    head[io.XM['collLod']] = 255
    head[io.XM['shadowCutoffLod']] = 6
    head[io.XM['numBones']] = 1
    head[io.XM['numRootBones']] = 1
    struct.pack_into('<H', head, io.XM['numsurfs'], len(materials))
    struct.pack_into('<f', head, io.XM['scale'], 1.0)
    struct.pack_into('<f', head, io.XM['radius'], radius)
    struct.pack_into('<6f', head, io.XM['bounds'], *mid, *half)
    struct.pack_into('<Q', head, 152, 1)       # boneNames
    struct.pack_into('<Q', head, 184, 1)       # partClassification
    struct.pack_into('<Q', head, 192, 1)       # baseMat
    struct.pack_into('<Q', head, 216, 1)       # materialHandles
    struct.pack_into('<Q', head, 616, 1)       # boneInfo
    struct.pack_into('<Q', head, 624, 1)       # invHighMipRadius
    for i in range(6):
        o = io.XM['lodInfo'] + i * io.LOD_SIZE
        if i < len(lod_rows):
            d, ns, si = lod_rows[i]
            struct.pack_into('<f2H', head, o, d, ns, si)
            struct.pack_into('<Q', head, o + 8, 1)
            struct.pack_into('<I', head, o + 16, PARTBIT_BONE0)
            struct.pack_into('<Q', head, o + 48, 1)
        else:
            struct.pack_into('<f', head, o, 1000000.0)
    head[704] = 0xFF        # unknownIndex  (stock and converted models: 0xff)
    head[720] = 0xFF        # unknownIndex2
    bone_info = struct.pack('<6ff', *mid, *half, float(np.sum(half ** 2)))
    m = {'head': head, 'name': name, 'bones': [bone], 'parentList': None, 'tagAngles': None, 'tagPositions': None,
         'partClassification': b'\0', 'baseMat': struct.pack('<8f', 0, 0, 0, 1, 0, 0, 0, 2),
         'reactiveMotionParts': None, 'reactiveMotionTweaks': None, 'collSurfs': None, 'boneInfo': bone_info,
         'invHighMipRadius': struct.pack('<%dH' % len(inv_mip), *inv_mip),
         'materialHandles': b'\1' + b'\0' * (8 * len(materials) - 1), 'materials': materials,
         'lods': lod_names + [None] * (6 - len(lod_names)), 'physicsAsset': None, 'physicsFXShape': None,
         'physicsLODDataNames': [], 'scriptableMoverDef': None, 'proceduralBones': None, 'aimAssistBones': [],
         'unknown03': None, 'unknownVec3': None, 'unknown04': None}
    with open(os.path.join(out_dir, 'xmodel', name + '.xmb'), 'wb') as f:
        f.write(io.write_xmodel(m))
    report.update(materials=sorted(set(materials)), surfaces=len(materials), bounds=[lo.tolist(), hi.tolist()],
                  radius=radius)
    return report


def normal_agreement(P, N, tris):
    """Share of triangle corners whose vertex normal faces the same side as the (counter-clockwise) face."""
    fn = face_normals(P, tris)
    d = np.sum(fn[:, None, :] * N[tris], 2)
    return float(np.mean(d > 0)) if len(tris) else 1.0


def crease_normals(P, tris, crease_deg=50.0):
    """Recompute corner normals from the faces: faces around a position are averaged when within crease_deg of
    the corner's own face, so hard edges stay hard. Returns un-indexed (corner) arrays: P3, N3, tris3."""
    fn = face_normals(P, tris)
    area = np.linalg.norm(fn, axis=1)
    fu = fn / np.maximum(area[:, None], 1e-12)
    key = np.round(P / 1e-3).astype(np.int64)
    _, pid = np.unique(key, axis=0, return_inverse=True)
    pid = pid.reshape(-1)
    corners = pid[tris]                       # (m, 3) position ids
    order = np.argsort(corners.reshape(-1), kind='stable')
    flat = corners.reshape(-1)[order]
    starts = np.r_[0, np.nonzero(np.diff(flat))[0] + 1, len(flat)]
    face_of = (order // 3)
    cos = np.cos(np.radians(crease_deg))
    N3 = np.zeros((len(tris) * 3, 3))
    for a, b in zip(starts[:-1], starts[1:]):
        fs = face_of[a:b]
        u = fu[fs]
        w = fn[fs]
        sim = u @ u.T >= cos
        acc = sim.astype(np.float64) @ w
        acc /= np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-12)
        N3[order[a:b]] = acc
    return N3.reshape(len(tris), 3, 3)

"""Blender (headless) zombie outfit fit: AI full-character mesh -> IW7 modular zombie parts on the stock zombie skeleton.

blender -b --factory-startup -P fit_zombie.py -- --config <zombie.json> [--quick] [--reuse-fit]

Reuses the hero fit pipeline (heroes/tools/fit/fit_hero.py + fitlib.py, loaded WITHOUT running its main): similarity
ICP, per-chain pose fit, robust weight transfer, decimation, Cycles bake, renders. Zombie specifics here:
 1 stock part set (torso + arm_l/r + leg_l/r + head) attached on the torso skeleton; merged skeleton = torso bones +
   the extra bones of each part (fingers, knees, jaw, eyes ...)
 2 the WHOLE AI mesh is the outfit (hands, head, hair included); decimated to the stock part budget in the AI pose
 3 face labels = stock part of the closest posed stock surface (+ coat rule: cloth below the hips away from the legs
   stays on the torso), smoothed; weights transferred, then restricted per vertex to the bones of every part that
   uses it (seam vertices: intersection of both skeletons, same row on both sides -> no gap in any pose)
 4 smart UV (body atlas + head atlas), bake from the high-res AI mesh, unpose to the stock bind pose
 5 split by label -> normal parts; torso sockets capped (zmb_dismembered_caps); damaged gibs = part beyond the stock
   cut plane (least-squares plane of the stock gib's cap vertices), capped, rigid on the stock gib root bone
 6 every export object is placed in its stock model frame (part root bone space) under a copy of the stock part
   armature, ready for iw7-skinned-writer blender_export.py + build_model.py (base = stock part xmb)
Outputs: heroes/zombies/fit/<id>/ (<id>_parts.blend, renders/, textures/, fit_report.json).
"""
import json
import math
import os
import sys
import time
import types

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

FIT_DIR = os.environ.get("IWZ_FIT_DIR", "")  # folder of the local fit_hero.py; run_zombie.py sets it


def load_fit_hero():
    if not FIT_DIR:
        raise SystemExit("Set the environment variable IWZ_FIT_DIR to the folder that holds fit_hero.py "
                         "(run_zombie.py sets it to <IWZ_HEROES>/tools/fit).")
    src_path = os.path.join(FIT_DIR, "fit_hero.py")
    src = open(src_path, encoding="utf-8").read()
    lines = src.rstrip().split("\n")
    if lines[-1].strip() == "main()":
        lines = lines[:-1]
    mod = types.ModuleType("fit_hero")
    mod.__file__ = src_path
    sys.modules["fit_hero"] = mod
    exec(compile("\n".join(lines), src_path, "exec"), mod.__dict__)
    return mod


fh = load_fit_hero()
fl = fh.fl
HEROES = fh.HEROES
T0 = time.time()
REPORT = {}
PART_ORDER = ["torso", "arm_l", "arm_r", "leg_l", "leg_r", "head"]
GIBS = ["arm_l", "arm_r", "leg_l", "leg_r", "head"]
CAP_MAT = "zmb_dismembered_caps"


def log(*a):
    print('[zfit %7.1fs]' % (time.time() - T0), *a, flush=True)


def P(rel):
    return rel if os.path.isabs(rel) else os.path.join(HEROES, rel)


GENDER = {
    "male": {
        "parts": {"torso": "zmb_male_normal_torso_outfit_01", "arm_l": "zmb_male_normal_arm_l_outfit_01",
                  "arm_r": "zmb_male_normal_arm_r_outfit_01", "leg_l": "zmb_male_normal_leg_l_outfit_01",
                  "leg_r": "zmb_male_normal_leg_r_outfit_01", "head": "zmb_male_head_01"},
        "damaged": {"arm_l": "zmb_male_damaged_arm_l_outfit_01", "arm_r": "zmb_male_damaged_arm_r_outfit_01",
                    "leg_l": "zmb_male_damaged_leg_l_outfit_01", "leg_r": "zmb_male_damaged_leg_r_outfit_01",
                    "head": "zmb_male_head_01_damaged"}},
    "female": {
        "parts": {"torso": "zmb_female_normal_torso_outfit_01", "arm_l": "zmb_female_normal_arm_l",
                  "arm_r": "zmb_female_normal_arm_r", "leg_l": "zmb_female_normal_leg_l_outfit_01",
                  "leg_r": "zmb_female_normal_leg_r_outfit_01", "head": "zmb_female_head_01"},
        "damaged": {"arm_l": "zmb_female_damaged_arm_l", "arm_r": "zmb_female_damaged_arm_r",
                    "leg_l": "zmb_female_damaged_leg_l_outfit_01", "leg_r": "zmb_female_damaged_leg_r_outfit_01",
                    "head": "zmb_female_head_01_damaged"}},
}

ZDEFAULTS = {
    "stock_dir": "stock_zombies/iw/models",
    "budget_total": 26000,
    "texture_size": 2048,
    "head_texture_size": 1024,
    "fit_exclude_materials": ["dismembered_caps", "inside_mouth", "eyes", "teeth", "eye"],
    "rigid_remap": {"j_jaw": "j_head", "j_eyeball_le": "j_head", "j_eyeball_ri": "j_head", "j_eyelid_bot_le": "j_head",
                    "j_eyelid_bot_ri": "j_head", "j_eyelid_top_le": "j_head", "j_eyelid_top_ri": "j_head"},
    "coat": None,
    "label_smooth_iters": 6,
    "cap_inset": 0.012,
    "cap_uv_scale": 0.16,
    "fused_face_ratio": 2.5,
    "min_island_faces": 24,
    "gib_cut": {},
}


def parse_args():
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    o = {"config": None, "quick": False, "reuse_fit": False}
    i = 0
    while i < len(a):
        if a[i] == '--config':
            o["config"] = a[i + 1]; i += 2
        elif a[i] == '--quick':
            o["quick"] = True; i += 1
        elif a[i] == '--reuse-fit':
            o["reuse_fit"] = True; i += 1
        else:
            raise SystemExit('unknown arg ' + a[i])
    return o


def stock_glb(cfg, name):
    return os.path.join(P(cfg["stock_dir"]), name, name + "_LOD0.glb")


def npm(m):
    return np.array(m, dtype=float)


def separate_by_material(ob):
    fh.activate(ob)
    if len(ob.material_slots) > 1:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.separate(type='MATERIAL')
        bpy.ops.object.mode_set(mode='OBJECT')
    return [o for o in bpy.context.selected_objects if o.type == 'MESH'] or [ob]


def copy_armature(arm, name):
    ex = arm.copy()
    ex.data = arm.data.copy()
    ex.name = name
    bpy.context.scene.collection.objects.link(ex)
    ex.hide_render = True
    return ex


def face_adjacency(T):
    """pairs of faces sharing an edge."""
    e = np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]])
    f = np.tile(np.arange(len(T)), 3)
    e.sort(axis=1)
    key = e[:, 0].astype(np.int64) * (int(T.max()) + 1) + e[:, 1]
    o = np.argsort(key, kind='stable')
    ks, fs = key[o], f[o]
    same = ks[1:] == ks[:-1]
    return np.stack([fs[:-1][same], fs[1:][same]], 1)


def smooth_labels(lab, adj, nlab, iters):
    for _ in range(iters):
        cnt = np.zeros((len(lab), nlab))
        cnt[np.arange(len(lab)), lab] += 1.5
        np.add.at(cnt, (adj[:, 0], lab[adj[:, 1]]), 1)
        np.add.at(cnt, (adj[:, 1], lab[adj[:, 0]]), 1)
        lab = np.argmax(cnt, axis=1)
    return lab


def relabel_small_components(lab, adj, nlab, keep_frac=0.05):
    """per label: connected components (through same-label face adjacency); components smaller than keep_frac of the
    label's largest component take the majority label of their neighbours."""
    n = len(lab)
    parent = np.arange(n)

    def find(x):
        r = x
        while parent[r] != r:
            r = parent[r]
        while parent[x] != r:
            parent[x], x = r, parent[x]
        return r
    for a, b in adj:
        if lab[a] == lab[b]:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra
    roots = np.array([find(i) for i in range(n)])
    changed = 0
    for L in range(nlab):
        m = lab == L
        if not m.any():
            continue
        u, c = np.unique(roots[m], return_counts=True)
        big = c.max()
        for r, cc in zip(u, c):
            if cc >= keep_frac * big:
                continue
            fm = roots == r
            nb = np.concatenate([lab[adj[fm[adj[:, 0]], 1]], lab[adj[fm[adj[:, 1]], 0]]])
            nb = nb[nb != L]
            if len(nb):
                lab[fm] = np.bincount(nb, minlength=nlab).argmax()
                changed += int(fm.sum())
    return lab, changed


def restrict_weights(W, vparts, part_bones, skel, remap):
    """W (n,B); vparts list of frozenset(part names) per vertex. Remap + move disallowed influence to the nearest
    allowed ancestor."""
    W = W.copy()
    for src, dst in remap.items():
        if src in skel.index and dst in skel.index:
            W[:, skel.index[dst]] += W[:, skel.index[src]]
            W[:, skel.index[src]] = 0
    combos = {}
    for i, ps in enumerate(vparts):
        combos.setdefault(ps, []).append(i)
    stats = {}
    for ps, ids in combos.items():
        allowed = None
        for p in ps:
            allowed = set(part_bones[p]) if allowed is None else allowed & set(part_bones[p])
        if not allowed:
            allowed = set(part_bones["torso"])
        al = np.zeros(len(skel.names), bool)
        al[[skel.index[b] for b in allowed if b in skel.index]] = True
        ids = np.array(ids)
        sub = W[ids]
        moved = 0.0
        for b in np.nonzero(sub.any(0) & ~al)[0]:
            a = b
            while a >= 0 and not al[a]:
                a = skel.parents[a]
            if a < 0:
                a = int(np.nonzero(al)[0][0])
            moved += float(sub[:, b].sum())
            sub[:, a] += sub[:, b]
            sub[:, b] = 0
        W[ids] = sub
        stats["+".join(sorted(ps))] = {"verts": len(ids), "allowed": len(allowed), "moved_weight": round(moved, 2)}
    return fl.limit_prune(fl.normalize_rows(W), 4, 0.01), stats


def object_from_faces(src, fmask, name):
    """duplicate src (mesh + groups + uv + materials + custom normals) keeping only the masked faces."""
    ob = src.copy()
    ob.data = src.data.copy()
    ob.name = name
    ob.data.name = name
    bpy.context.scene.collection.objects.link(ob)
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.nonzero(~fmask)[0]], context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(ob.data); bm.free(); ob.data.update()
    return ob


def cap_material_index(ob):
    for i, s in enumerate(ob.material_slots):
        if s.material and s.material.name == CAP_MAT:
            return i
    m = bpy.data.materials.get(CAP_MAT) or bpy.data.materials.new(CAP_MAT)
    m.diffuse_color = (0.35, 0.02, 0.02, 1)
    ob.data.materials.append(m)
    return len(ob.material_slots) - 1


def boundary_loops_bm(bm, vert_filter=None):
    """ordered boundary loops (lists of (BMVert, BMVert) directed edges as they run in the adjacent face)."""
    edges = [e for e in bm.edges if e.is_boundary]
    nxt = {}
    for e in edges:
        f = e.link_faces[0]
        for l in f.loops:
            if l.edge == e:
                a, b = l.vert, l.link_loop_next.vert
                nxt[a.index] = (a, b)
    loops, seen = [], set()
    for k in list(nxt):
        if k in seen:
            continue
        lp = []
        cur = k
        while cur in nxt and cur not in seen:
            seen.add(cur)
            a, b = nxt[cur]
            lp.append((a, b))
            cur = b.index
        if len(lp) >= 3:
            loops.append(lp)
    if vert_filter is not None:
        loops = [lp for lp in loops if vert_filter(lp)]
    return loops


def fill_caps(ob, loops_pick, inset, inward_dir_fn, uv_scale, group_weights=None):
    """fan-fill boundary loops with a centre vertex pushed `inset` along inward_dir_fn(centre, loop normal) (concave
    wound), cap material, planar UVs; returns cap faces count and loop stats."""
    mi = cap_material_index(ob)
    me = ob.data
    bm = bmesh.new(); bm.from_mesh(me)
    bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    uvl = bm.loops.layers.uv.active or bm.loops.layers.uv.new('UVMap')
    dl = bm.verts.layers.deform.verify()
    loops = loops_pick(bm)
    nf = 0
    stats = []
    for lp in loops:
        pts = np.array([list(a.co) for a, b in lp])
        c = pts.mean(0)
        # loop normal by Newell; orient with the caller's direction (pointing INTO the kept body)
        nrm = np.zeros(3)
        for i in range(len(pts)):
            p, q = pts[i], pts[(i + 1) % len(pts)]
            nrm += np.cross(p - c, q - c)
        nrm /= max(np.linalg.norm(nrm), 1e-12)
        d_in = inward_dir_fn(c, nrm)
        cv = bm.verts.new(Vector(c + d_in * inset))
        # centre weights = mean of the loop
        acc = {}
        for a, b in lp:
            for g, w in a[dl].items():
                acc[g] = acc.get(g, 0) + w / len(lp)
        for g, w in acc.items():
            cv[dl][g] = w
        if group_weights is not None:
            cv[dl].clear()
            for g, w in group_weights.items():
                cv[dl][g] = w
        u_ = np.cross(d_in, [0, 0, 1] if abs(d_in[2]) < 0.9 else [1, 0, 0]); u_ /= np.linalg.norm(u_)
        v_ = np.cross(d_in, u_)
        for a, b in lp:
            try:
                f = bm.faces.new((b, a, cv))
            except ValueError:
                continue
            f.material_index = mi
            f.smooth = True
            for l in f.loops:
                p = np.array(l.vert.co) - c
                l[uvl].uv = (0.5 + float(p @ u_) / uv_scale, 0.5 + float(p @ v_) / uv_scale)
            nf += 1
        stats.append({"verts": len(lp), "centre": [round(x, 4) for x in c.tolist()],
                      "radius_mm": round(float(np.linalg.norm(pts - c, axis=1).mean() * 1000), 1)})
    bm.to_mesh(me); bm.free(); me.update()
    return nf, stats


def main():
    a = parse_args()
    user = json.load(open(a["config"]))
    g = GENDER[user["gender"]]
    cfg = fh.merge(fh.DEFAULTS, ZDEFAULTS)
    cfg = fh.merge(cfg, {"parts": g["parts"], "damaged": g["damaged"]})
    cfg = fh.merge(cfg, user)
    zid = cfg["zombie"]
    quick = a["quick"]
    out = P(cfg.get("out_dir", os.path.join("zombies", "fit", zid)))
    rdir = os.path.join(out, "renders"); tdir = os.path.join(out, "textures"); wdir = os.path.join(out, "work")
    for d in (out, rdir, tdir, wdir):
        os.makedirs(d, exist_ok=True)
    if quick:
        cfg["texture_size"] = 512; cfg["head_texture_size"] = 256
    prefix = cfg.get("name_prefix", "zmb_iwz_%s" % zid.lower())
    mats = {"body": "iwz_%s_body" % zid.lower(), "head": "iwz_%s_head" % zid.lower()}
    REPORT.update({"zombie": zid, "gender": cfg["gender"], "config": os.path.abspath(a["config"]), "quick": quick,
                   "materials": mats})
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # ---------------------------------------------------------------- stock part set on the torso skeleton
    objs = fh.import_glb(stock_glb(cfg, cfg["parts"]["torso"]))
    body_arm = [o for o in objs if o.type == 'ARMATURE'][0]
    body_arm.name = 'ARM_torso'
    part_meshes = {"torso": [o for o in objs if o.type == 'MESH']}
    part_bones = {"torso": [b.name for b in body_arm.data.bones]}
    exarm = {"torso": body_arm}
    part_root = {"torso": None}
    Morig = {}
    sub_arms = {}
    for p in PART_ORDER[1:]:
        o2 = fh.import_glb(stock_glb(cfg, cfg["parts"][p]))
        harm = [o for o in o2 if o.type == 'ARMATURE'][0]
        hm = [o for o in o2 if o.type == 'MESH']
        exarm[p] = copy_armature(harm, 'EXARM_' + p)
        key = [b.name for b in harm.data.bones if b.name in body_arm.data.bones][0]
        Morig[p] = npm(harm.matrix_world @ harm.data.bones[key].matrix_local)
        fh.attach(harm, body_arm, hm)
        harm.hide_render = True
        part_meshes[p] = hm
        part_bones[p] = [b.name for b in harm.data.bones]
        part_root[p] = key
        sub_arms[p] = harm
    # merged skeleton
    sk0 = fh.skeleton_of(body_arm)
    names, parents, A = list(sk0.names), list(sk0.parents), list(sk0.A)
    mismatch = {}
    for p, harm in sub_arms.items():
        pend = list(harm.data.bones)
        while pend:
            rest = []
            for b in pend:
                M = npm(harm.matrix_world @ b.matrix_local)
                if b.name in names:
                    d = float(np.linalg.norm(M[:3, 3] - A[names.index(b.name)][:3, 3]))
                    if d > 1e-4:
                        mismatch["%s:%s" % (p, b.name)] = round(d * 1000, 2)
                    continue
                if b.parent and b.parent.name not in names:
                    rest.append(b); continue
                names.append(b.name)
                parents.append(names.index(b.parent.name) if b.parent else -1)
                A.append(M)
            if len(rest) == len(pend):
                raise SystemExit("cannot order bones of " + p)
            pend = rest
    skel = fl.Skeleton(names, parents, np.array(A))
    REPORT["skeleton"] = {"bones": len(names), "shared_bone_mismatch_mm": mismatch,
                          "part_bones": {p: len(v) for p, v in part_bones.items()}, "part_root": part_root}
    log('merged skeleton', len(names), 'bones; mismatches', mismatch)

    # stock fit parts (outer surfaces only)
    parts, part_id = [], []
    excl = cfg["fit_exclude_materials"]
    for pi, p in enumerate(PART_ORDER):
        for o in list(part_meshes[p]):
            for s in separate_by_material(o):
                mn = fh.short(s.material_slots[0].material.name) if s.material_slots and s.material_slots[0].material else ''
                if any(k in mn for k in excl):
                    s.hide_render = True
                    continue
                pp = fh.Part(s, skel, 1 if p == "head" else 0)
                pp.keep, pp.fit, pp.zpart = False, True, p
                parts.append(pp)
    log('stock fit surfaces', [(pp.zpart, pp.name, len(pp.T)) for pp in parts])
    offs = np.cumsum([0] + [len(pp.V) for pp in parts])
    Vs = np.concatenate([pp.V for pp in parts]); Ws = np.concatenate([pp.W for pp in parts])
    Ts = np.concatenate([pp.T + offs[i] for i, pp in enumerate(parts)])
    kind = np.concatenate([np.full(len(pp.V), pp.kind) for pp in parts])
    face_part = np.concatenate([np.full(len(pp.T), PART_ORDER.index(pp.zpart)) for pp in parts])
    floor_z = float(Vs[kind == 0][:, 2].min())

    # ---------------------------------------------------------------- AI mesh, align, pose fit
    aobjs = fh.import_glb(P(cfg["ai_glb"]))
    hi = [o for o in aobjs if o.type == 'MESH'][0]
    mw = hi.matrix_world.copy(); hi.parent = None; hi.data.transform(mw); hi.matrix_world = Matrix.Identity(4)
    for o in aobjs:
        if o.type == 'EMPTY':
            bpy.data.objects.remove(o, do_unlink=True)
    hi.name = 'ai_hi'
    bm = bmesh.new(); bm.from_mesh(hi.data)
    nv0 = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bm.to_mesh(hi.data); bm.free()
    Va, Ta = fh.mesh_arrays(hi)
    log('AI mesh verts %d -> %d welded, tris %d' % (nv0, len(Va), len(Ta)))
    REPORT["ai_mesh"] = {"verts_welded": len(Va), "tris": len(Ta)}
    fitjson = os.path.join(wdir, 'fit.json')
    reuse = a["reuse_fit"] and os.path.exists(fitjson)
    if reuse:
        fj = json.load(open(fitjson)); M = np.array(fj["M"]); params = fj["params"]
        REPORT["align"] = fj["align"]; REPORT["pose_fit"] = fj["pose_fit"]
    else:
        bvh0 = BVHTree.FromPolygons(Va.tolist(), Ta.tolist(), all_triangles=True)
        pre = tuple(cfg["align"]["bone_prefixes"])
        abones = [i for i, n in enumerate(skel.names) if n.startswith(pre)]
        amask = (Ws[:, abones].sum(1) > 0.8) & (kind == 0)
        X = Vs[amask]
        X = X[np.random.default_rng(3).choice(len(X), min(cfg["align"]["samples"], len(X)), replace=False)]
        M, arep = fh.icp_align(cfg, Va, Ta, bvh0, X, floor_z, Vs)
        REPORT["align"] = arep
        del bvh0
    hi.data.transform(Matrix(M.tolist())); hi.data.update()
    Va, Ta = fh.mesh_arrays(hi)
    bvh_ai = BVHTree.FromPolygons(Va.tolist(), Ta.tolist(), all_triangles=True)
    if not reuse:
        params, prep = fh.fit_pose(cfg, skel, Vs, Ws, kind, Va, bvh_ai, quick)
        REPORT["pose_fit"] = prep
        json.dump({"M": M.tolist(), "params": params, "align": REPORT["align"], "pose_fit": prep},
                  open(fitjson, 'w'), indent=1, default=lambda x: x.tolist() if hasattr(x, 'tolist') else str(x))
    pose_fit = {skel.index[n]: fl.rotvec_to_mat(np.radians(r)) for n, r in params.items()}
    S_fit = skel.skin_mats(pose_fit)
    Pfit = fl.lbs(Vs, Ws, S_fit)
    Pj_fit = skel.fk(pose_fit)
    log('align', json.dumps({k: REPORT["align"][k] for k in ("scale", "yaw_deg", "best_rms_trim_mm")}, default=str))

    # overlay evidence (red = AI, green = posed stock) - stock posed via numpy (merged skeleton) as a temp mesh
    fh.setup_render(cfg)
    tmp = fh.new_mesh_object('stock_posed_tmp', Pfit, Ts)
    for pp in parts:
        pp.ob.hide_render = True
    bb = (np.minimum(Va.min(0), Pfit.min(0)), np.maximum(Va.max(0), Pfit.max(0)))
    pa = fh.render_views([hi], os.path.join(wdir, 'chk_ai'), [('front', 0), ('side', 90)], bb)
    pb = fh.render_views([tmp], os.path.join(wdir, 'chk_stockposed'), [('front', 0), ('side', 90)], bb)
    ov = []
    for x, y, nm in zip(pa, pb, ('front', 'side')):
        ia = bpy.data.images.load(x); ib = bpy.data.images.load(y)
        w, h = ia.size
        A1 = np.empty(w * h * 4, np.float32); ia.pixels.foreach_get(A1)
        B1 = np.empty(w * h * 4, np.float32); ib.pixels.foreach_get(B1)
        A1 = A1.reshape(h, w, 4); B1 = B1.reshape(h, w, 4)
        C = A1.copy(); ga = A1[..., :3].mean(-1); gb = B1[..., :3].mean(-1)
        C[..., 0] = ga; C[..., 1] = gb; C[..., 2] = (ga + gb) / 2
        o = bpy.data.images.new('ov', w, h); o.pixels.foreach_set(C.ravel())
        pth = os.path.join(rdir, 'align_overlay_%s.png' % nm)
        o.filepath_raw = pth; o.file_format = 'PNG'; o.save()
        ov.append(pth)
    REPORT["renders"] = {"align_overlay": ov}
    bpy.data.objects.remove(tmp, do_unlink=True)

    # ---------------------------------------------------------------- game mesh (whole AI mesh, decimated)
    gbody = fh.new_mesh_object('zbody_' + zid, Va, Ta)
    bt = cfg["budget_total"] // (3 if quick else 1)
    d0, d1 = fh.decimate(gbody, bt)
    dropped = fh.drop_small_islands(gbody, cfg["min_island_faces"])
    REPORT["decimate"] = {"from": d0, "to": len(gbody.data.polygons), "small_island_faces_dropped": dropped}
    Vb, Tb = fh.mesh_arrays(gbody)
    Nb = fh.vertex_normals(gbody)
    # region labels for the weight transfer (zombie skeleton has no 'pelvis'/'j_helmet')
    regions = fh.regions_default(skel)
    regions['torso']["seg"] = [['j_mainroot', 'j_spine4'], ['j_spine4', 'j_neck']]
    regions['head']["seg"] = [['j_neck', 'j_head'], ['j_head', 'j_head', 0.12]]
    labs_s, rnames = fh.region_labels(skel, regions, None, W=Ws)
    lab_sf = np.array([np.bincount(labs_s[t], minlength=len(rnames)).argmax() for t in Ts])
    lab_t, _ = fh.region_labels(skel, regions, Pj_fit, X=Vb)
    # incompatible region faces (AI fusion bridges hand<->coat, arm<->torso) are deleted
    ok = set((r, r) for r in rnames)
    for s_ in ('le', 'ri'):
        for x_, y_ in (('torso', 'uarm_'), ('uarm_', 'farm_'), ('farm_', 'hand_'), ('torso', 'thigh_'),
                       ('thigh_', 'shin_'), ('shin_', 'foot_')):
            x2 = x_ + s_ if x_.endswith('_') else x_
            ok.add((x2, y_ + s_)); ok.add((y_ + s_, x2))
    ok |= {('torso', 'head'), ('head', 'torso'), ('thigh_le', 'thigh_ri'), ('thigh_ri', 'thigh_le')}
    okm = np.zeros((len(rnames), len(rnames)), bool)
    for x_, y_ in ok:
        if x_ in rnames and y_ in rnames:
            okm[rnames.index(x_), rnames.index(y_)] = True
    L3 = lab_t[Tb]
    badf = ~(okm[L3[:, 0], L3[:, 1]] & okm[L3[:, 1], L3[:, 2]] & okm[L3[:, 0], L3[:, 2]])
    if badf.any():
        bm = bmesh.new(); bm.from_mesh(gbody.data); bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.nonzero(badf)[0]], context='FACES')
        bm.to_mesh(gbody.data); bm.free(); gbody.data.update()
        fh.drop_small_islands(gbody, cfg["min_island_faces"])
        Vb, Tb = fh.mesh_arrays(gbody); Nb = fh.vertex_normals(gbody)
        lab_t, _ = fh.region_labels(skel, regions, Pj_fit, X=Vb)
    REPORT["incompatible_region_faces_deleted"] = int(badf.sum())
    Wb, trep = fh.robust_transfer(cfg, Vb, Nb, Tb, Pfit, Ts, Ws, lab_t, lab_sf)
    REPORT["weight_transfer"] = trep
    log('transfer', trep)

    # ---------------------------------------------------------------- part labels per face
    bvh_s = BVHTree.FromPolygons(Pfit.tolist(), Ts.tolist(), all_triangles=True)
    fc = Vb[Tb].mean(1)
    flab = np.zeros(len(Tb), int)
    fdist = np.zeros(len(Tb))
    for i, c in enumerate(fc):
        l, nr, f, d = bvh_s.find_nearest(Vector(c))
        flab[i] = face_part[f]
        fdist[i] = d
    # layer rule below the hips: a face is LEG when it is the innermost surface seen from the nearest leg axis (pants,
    # boots) and lies below the stock torso bottom; outer layers (coat panels, skirt over the legs) stay on the torso
    coat = cfg.get("coat") or {}
    L_LEG = (PART_ORDER.index("leg_l"), PART_ORDER.index("leg_r"))
    hipz = 0.5 * (Pj_fit[skel.index['j_hip_le']][2, 3] + Pj_fit[skel.index['j_hip_ri']][2, 3])
    tz = Pfit[np.isin(np.arange(len(Pfit)), np.unique(Ts[face_part == 0]))][:, 2]
    z_cut = float(cfg.get("leg_top_z") or np.quantile(tz, 0.03))
    bvh_g = BVHTree.FromPolygons(Vb.tolist(), Tb.tolist(), all_triangles=True)
    below = fc[:, 2] < hipz
    inner = np.zeros(len(Tb), bool)
    side_of = np.zeros(len(Tb), int)
    segs = {}
    for s_, L in (('le', L_LEG[0]), ('ri', L_LEG[1])):
        segs[L] = [(Pj_fit[skel.index[a_n + s_]][:3, 3], Pj_fit[skel.index[b_n + s_]][:3, 3])
                   for a_n, b_n in (('j_hip_', 'j_knee_'), ('j_knee_', 'j_ankle_'), ('j_ankle_', 'j_ball_'))]
    for i in np.nonzero(below)[0]:
        c = fc[i]
        best = None
        for L, sl in segs.items():
            for a_, b_ in sl:
                ab = b_ - a_; t_ = np.clip((c - a_) @ ab / (ab @ ab), 0, 1); q = a_ + t_ * ab
                d = np.linalg.norm(c - q)
                if best is None or d < best[0]:
                    best = (d, q, L)
        d, q, L = best
        side_of[i] = L
        if d < 1e-4:
            inner[i] = True; continue
        u = (c - q) / d
        hit = bvh_g.ray_cast(Vector(q), Vector(u), d + 1e-3)
        inner[i] = hit[2] is not None and (hit[2] == i or hit[3] >= d - 2e-3)
    layer_leg = below & inner & (fc[:, 2] < z_cut)
    outer = below & ~inner
    flab[below & np.isin(flab, L_LEG) & ~layer_leg] = 0
    flab[layer_leg] = side_of[layer_leg]
    adj = face_adjacency(Tb)
    flab = smooth_labels(flab, adj, len(PART_ORDER), cfg["label_smooth_iters"])
    flab, nre = relabel_small_components(flab, adj, len(PART_ORDER))
    coat_faces = outer & (flab == 0) if cfg.get("coat") else np.zeros(len(Tb), bool)
    REPORT["layer_rule"] = {"hip_z": hipz, "leg_top_z": z_cut, "below_hip": int(below.sum()), "inner": int((below & inner).sum()),
                            "outer": int(outer.sum()), "leg_faces": int(layer_leg.sum())}
    REPORT["labels"] = {"faces": {PART_ORDER[k]: int((flab == k).sum()) for k in range(len(PART_ORDER))},
                        "coat_faces": int(coat_faces.sum()), "small_components_relabelled": nre}
    log('labels', REPORT["labels"])
    # coat weights (pelvis/thigh blend, no knee) for torso faces hanging below the hips
    if cfg.get("coat"):
        cv = np.zeros(len(Vb), bool); cv[Tb[coat_faces & (flab == 0)].ravel()] = True
        Pj = Pj_fit
        root = skel.index[coat.get("root", "j_mainroot")]
        yrel = Vb[:, 1] - Pj[root][1, 3]
        sl = np.clip(0.5 + yrel / coat.get("lateral", 0.16), 0, 1)
        ps = coat.get("pelvis_share", 0.4)
        Wc = np.zeros_like(Wb)
        Wc[:, root] = ps
        Wc[:, skel.index['j_hip_le']] = (1 - ps) * sl
        Wc[:, skel.index['j_hip_ri']] = (1 - ps) * (1 - sl)
        Wb[cv] = Wc[cv]
        Ec = fl.edges_of_tris(Tb)
        grow = cv.copy()
        for _ in range(3):
            g2 = grow.copy(); g2[Ec[grow[Ec[:, 0]], 1]] = True; g2[Ec[grow[Ec[:, 1]], 0]] = True; grow = g2
        Wb = fl.limit_prune(fl.smooth_weights(Wb, Ec, 6, 0.5, mask=grow), 4, 0.01)
        REPORT["coat_verts"] = int(cv.sum())
    # restrict weights to the part skeletons (seam rows valid in both)
    vsets = [set() for _ in range(len(Vb))]
    for f, L in enumerate(flab):
        for v in Tb[f]:
            vsets[v].add(PART_ORDER[L])
    vparts = [frozenset(s) if s else frozenset(["torso"]) for s in vsets]
    Wb, rstat = restrict_weights(Wb, vparts, part_bones, skel, cfg["rigid_remap"])
    REPORT["weight_restrict"] = rstat
    seam_verts = int(sum(1 for s in vparts if len(s) > 1))
    REPORT["seam_verts"] = seam_verts

    # ---------------------------------------------------------------- materials, UV, bake (AI pose)
    gbody.data.materials.append(fh.game_material(mats["body"], cfg["texture_size"]))
    gbody.data.materials.append(fh.game_material(mats["head"], cfg["head_texture_size"]))
    gbody.data.polygons.foreach_set('material_index', (flab == PART_ORDER.index("head")).astype(np.int32))
    gbody.data.polygons.foreach_set('use_smooth', np.ones(len(Tb), bool))
    gbody.data.update()
    fh.activate(gbody)
    gbody.data.uv_layers.new(name='UVMap')
    bpy.ops.object.mode_set(mode='EDIT')
    for si in range(len(gbody.material_slots)):
        bpy.ops.mesh.select_all(action='DESELECT')
        gbody.active_material_index = si
        bpy.ops.object.material_slot_select()
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003, area_weight=0.0,
                                 correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.scene.objects:
        o.hide_render = False
    texmaps, brep = fh.bake_all(cfg, hi, [(gbody, {mats["body"]: cfg["texture_size"], mats["head"]: cfg["head_texture_size"]})],
                                tdir, quick)
    REPORT["bake"] = brep
    REPORT["textures"] = texmaps
    for slot in gbody.material_slots:
        fh.preview_material(slot.material, texmaps[slot.material.name])

    # ---------------------------------------------------------------- unpose to the bind pose
    Vr = fl.unskin(Vb, Wb, S_fit)
    fh.set_mesh_co(gbody, Vr)
    fh.write_groups(gbody, skel, Wb)
    def _elen(V, T):
        return np.stack([np.linalg.norm(V[T[:, i]] - V[T[:, (i + 1) % 3]], axis=1) for i in range(3)], 1)
    ratio_f = (_elen(Vr, Tb) / np.maximum(_elen(Vb, Tb), 1e-6)).max(1)
    fused = ratio_f > cfg["fused_face_ratio"]
    REPORT["fused_faces_deleted"] = int(fused.sum())
    # vertex normals of the whole mesh at rest -> custom normals (identical across part seams)
    gbody.data.update()
    vn = fh.vertex_normals(gbody)
    gbody.data.normals_split_custom_set_from_vertices([tuple(v) for v in vn])
    keepf = ~fused
    for o in list(bpy.context.scene.objects):
        if o.type == 'MESH' and o not in (gbody, hi):
            o.hide_render = True

    # ---------------------------------------------------------------- split into parts (torso world, rest pose)
    pobj = {}
    for k, p in enumerate(PART_ORDER):
        pobj[p] = object_from_faces(gbody, (flab == k) & keepf, '%s_%s_rest' % (prefix, p))
    seam_vertex_set = set(i for i, s in enumerate(vparts) if len(s) > 1)
    REPORT["parts_tris"] = {p: len(o.data.polygons) for p, o in pobj.items()}

    # torso socket caps: loops whose vertices lie on part seams
    # map split-object vertices back to full-mesh vertices by position (objects are copies, exact coords)
    from mathutils.kdtree import KDTree
    kd_full = KDTree(len(Vr))
    for i, v in enumerate(Vr):
        kd_full.insert(v, i)
    kd_full.balance()

    def seam_local(ob):
        co = np.empty(len(ob.data.vertices) * 3); ob.data.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
        s = set()
        for i, c in enumerate(co):
            _, j, d = kd_full.find(c)
            if d < 1e-6 and j in seam_vertex_set:
                s.add(i)
        return s
    torso_seam_local = seam_local(pobj["torso"])

    def inward_torso(c, nrm):
        # towards the torso centre line (spine)
        ax0 = skel.A[skel.index['j_mainroot']][:3, 3]; ax1 = skel.A[skel.index['j_neck']][:3, 3]
        u = ax1 - ax0; t = np.clip((c - ax0) @ u / (u @ u), 0, 1)
        d = (ax0 + t * u) - c
        d /= max(np.linalg.norm(d), 1e-9)
        return nrm if nrm @ d > 0 else -nrm
    ncap, cstats = fill_caps(pobj["torso"], lambda bm: boundary_loops_bm(bm, lambda lp: sum(1 for a, b in lp if a.index in torso_seam_local) >= 0.6 * len(lp)),
                             cfg["cap_inset"], inward_torso, cfg["cap_uv_scale"])
    REPORT["torso_caps"] = {"faces": ncap, "loops": cstats}
    log('torso caps', ncap, [s["radius_mm"] for s in cstats])

    # ---------------------------------------------------------------- damaged gibs
    gib = {}
    REPORT["gibs"] = {}
    for p in GIBS:
        dname = cfg["damaged"][p]
        o3 = fh.import_glb(stock_glb(cfg, dname))
        garm = [o for o in o3 if o.type == 'ARMATURE'][0]
        garm.name = 'GIBARM_' + p
        garm.hide_render = True
        groot = garm.data.bones[0].name
        G = npm(garm.matrix_world @ garm.data.bones[groot].matrix_local)
        Ar = skel.A[skel.index[groot]]
        to_torso = Ar @ np.linalg.inv(G)
        capv, allv = [], []
        for o in o3:
            if o.type != 'MESH':
                continue
            mwo = npm(o.matrix_world)
            co = np.empty(len(o.data.vertices) * 3); o.data.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
            Wv = co @ mwo[:3, :3].T + mwo[:3, 3]
            Wt = Wv @ to_torso[:3, :3].T + to_torso[:3, 3]
            allv.append(Wt)
            for poly in o.data.polygons:
                mn = o.material_slots[poly.material_index].material.name if o.material_slots else ''
                if 'dismembered_caps' in mn:
                    capv += [Wt[v] for v in poly.vertices]
            bpy.data.objects.remove(o, do_unlink=True)
        capv = np.array(capv)
        child = {"arm_l": "j_elbow_le", "arm_r": "j_elbow_ri", "leg_l": "j_knee_le", "leg_r": "j_knee_ri", "head": "j_head"}[p]
        jr = skel.A[skel.index[groot]][:3, 3]; jc = skel.A[skel.index[child]][:3, 3]
        # cut plane: normal = limb axis (root -> child joint), position = median depth of the stock cap vertices
        n = (jc - jr) / np.linalg.norm(jc - jr)
        c = jr + n * float(np.median((capv - jr) @ n))
        override = cfg["gib_cut"].get(p, {})
        c = c + n * override.get("offset", 0.0)
        # stock gib geometry vs the stock normal part surface (validates the gib frame mapping)
        allv = np.concatenate(allv)
        pid = PART_ORDER.index(p)
        sel = [i for i, pp in enumerate(parts) if pp.zpart == p]
        sv = np.concatenate([parts[i].V for i in sel]); so = np.cumsum([0] + [len(parts[i].V) for i in sel])
        st = np.concatenate([parts[i].T + so[k] for k, i in enumerate(sel)])
        bvh_p = BVHTree.FromPolygons(sv.tolist(), st.tolist(), all_triangles=True)
        dd = np.array([bvh_p.find_nearest(Vector(x))[3] for x in allv[::7]])
        # cut our part
        ob = pobj[p].copy(); ob.data = pobj[p].data.copy(); ob.name = '%s_%s_damaged_rest' % (prefix, p)
        bpy.context.scene.collection.objects.link(ob)
        bm = bmesh.new(); bm.from_mesh(ob.data)
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=Vector(c), plane_no=Vector(n), clear_inner=True)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bm.to_mesh(ob.data); bm.free(); ob.data.update()
        # keep the connected part beyond the plane; drop tiny islands
        fh.drop_small_islands(ob, cfg["min_island_faces"])
        ob.vertex_groups.clear()
        vg = ob.vertex_groups.new(name=groot)
        vg.add(list(range(len(ob.data.vertices))), 1.0, 'REPLACE')
        ng, gstats = fill_caps(ob, lambda bm: boundary_loops_bm(bm), cfg["cap_inset"], lambda cc, nr: n, cfg["cap_uv_scale"])
        gib[p] = {"ob": ob, "arm": garm, "G": G, "root": groot}
        REPORT["gibs"][p] = {"stock": dname, "root": groot, "plane_c": c.tolist(), "plane_n": n.tolist(),
                             "plane_dist_from_root_mm": round(float((c - jr) @ n) * 1000, 1),
                             "stock_gib_to_stock_part_mm_p50": round(float(np.median(dd) * 1000), 2),
                             "stock_gib_to_stock_part_mm_p95": round(float(np.quantile(dd, 0.95) * 1000), 2),
                             "tris": len(ob.data.polygons), "cap_faces": ng, "cap_loops": gstats}
        log('gib', p, REPORT["gibs"][p]["plane_dist_from_root_mm"], 'mm', 'tris', len(ob.data.polygons), 'caps', ng,
            'stock map p50', REPORT["gibs"][p]["stock_gib_to_stock_part_mm_p50"])

    # ---------------------------------------------------------------- renders (rest, torso world)
    fh.setup_render(cfg)
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            o.hide_render = True
    normal_objs = [pobj[p] for p in PART_ORDER]
    views = [('front', 0), ('side', 90), ('back', 180), ('threequarter', 35)]
    rp = fh.render_views(normal_objs, os.path.join(rdir, 'parts'), views)
    REPORT["renders"]["parts_sheet"] = fh.sheet(rp, os.path.join(rdir, 'sheet_parts.png'))
    # exploded view (parts pushed apart) shows the split + caps
    expl = []
    cen = np.mean([np.array(o.matrix_world.translation) for o in normal_objs], 0)
    offsets = {"torso": (0, 0, 0), "arm_l": (0, 0.25, 0.05), "arm_r": (0, -0.25, 0.05), "leg_l": (0, 0.12, -0.25),
               "leg_r": (0, -0.12, -0.25), "head": (0, 0, 0.25)}
    for p in PART_ORDER:
        pobj[p].location = offsets[p]
    bpy.context.view_layer.update()
    expl = fh.render_views(normal_objs, os.path.join(rdir, 'exploded'), [('front', 0), ('threequarter', 35), ('back', 180)])
    for p in PART_ORDER:
        pobj[p].location = (0, 0, 0)
    gl = [gib[p]["ob"] for p in GIBS]
    for i, p in enumerate(GIBS):
        gib[p]["ob"].location = (0, (i - 2) * 0.35, 0)
    bpy.context.view_layer.update()
    gr = fh.render_views(gl, os.path.join(rdir, 'gibs'), [('front', 0), ('threequarter', 35), ('back', 180)])
    for p in GIBS:
        gib[p]["ob"].location = (0, 0, 0)
    bpy.context.view_layer.update()
    REPORT["renders"]["exploded_sheet"] = fh.sheet(expl + gr, os.path.join(rdir, 'sheet_exploded_gibs.png'), cols=3)

    # ---------------------------------------------------------------- export objects in their stock model frames
    export = {}
    for p in PART_ORDER:
        ob = pobj[p]
        name = '%s_normal_%s' % (prefix, p) if p != "head" else '%s_head' % prefix
        arm = exarm[p]
        Mp = np.eye(4) if p == "torso" else Morig[p] @ np.linalg.inv(skel.A[skel.index[part_root[p]]])
        ob.name = 'EX_' + name
        ob.parent = arm
        ob.matrix_world = Matrix(Mp.tolist())
        md = ob.modifiers.new('Armature', 'ARMATURE'); md.object = arm
        export[name] = {"object": ob.name, "base": cfg["parts"][p], "part": p, "kind": "normal"}
    for p in GIBS:
        ob = gib[p]["ob"]
        name = '%s_damaged_%s' % (prefix, p) if p != "head" else '%s_head_damaged' % prefix
        Mg = gib[p]["G"] @ np.linalg.inv(skel.A[skel.index[gib[p]["root"]]])
        ob.name = 'EX_' + name
        ob.parent = gib[p]["arm"]
        ob.matrix_world = Matrix(Mg.tolist())
        md = ob.modifiers.new('Armature', 'ARMATURE'); md.object = gib[p]["arm"]
        export[name] = {"object": ob.name, "base": cfg["damaged"][p], "part": p, "kind": "damaged"}
    REPORT["export"] = export
    for o in list(bpy.context.scene.objects):
        if o.type == 'MESH' and not o.name.startswith('EX_') and o is not hi:
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.objects.remove(hi, do_unlink=True)
    blend = os.path.join(out, '%s_parts.blend' % zid)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
    REPORT["blend"] = blend
    REPORT["seconds"] = round(time.time() - T0, 1)
    json.dump(REPORT, open(os.path.join(out, 'fit_report.json'), 'w'), indent=1,
              default=lambda x: x.tolist() if hasattr(x, 'tolist') else str(x))
    log('ZFIT_DONE', blend)


main()

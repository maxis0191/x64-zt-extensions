"""Offline proofs of an authored weapon fragment against its donor (data, exit code 1 on a failed proof).

    python -I authored_weapon_proof.py <recipe.json> --donor-dump <dir> --out <fragment> [--json <file>]
           [--preview-dir <dir>]

Per recipe model:
  bones      names, parents, bind matrices, tag angles/positions and part classification byte-equal to the donor
  weights    every vertex of every LOD in blend group 0 (one bone at weight 1), bone index inside the skeleton,
             no rigid lists; per bone vertex counts
  bounds     per bone: our box vs the donor's box; hand zones of the recipe (x window, optional z window, measured
             extents) within their tolerance of the donor
  camo       every surface whose material uses a _2uvt technique has flag 0x400 and one 24-byte record per
             vertex, read with iw7_xsurface_uv2.parse (independent reader); max deviation of the basis from identity
  roundtrip  xmodel / xsurface read and write back byte-identical; iw7_xsurface_check normals pass
With --preview-dir: first-person frames from the donor's own animations (t7_viewmodel_preview camera; hands, gun
parts posed by the gun skeleton), ours beside the donor's, as PNG. They are for the lead's information only.
"""
import argparse
import json
import math
import os
import struct
import sys

try:
    import numpy as np
except ImportError:  # python -I leaves out the user site, where numpy / Pillow are installed on this machine
    import site
    sys.path.append(site.getusersitepackages())
    import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
T7 = os.path.dirname(HERE)
WRITER = os.path.normpath(os.path.join(T7, "..", "..", "iw7-skinned-writer"))
sys.path[:0] = [WRITER, T7, HERE, os.path.join(T7, "..", "animation")]

import iw7_xsurface_check  # noqa: E402
import iw7_xsurface_uv2  # noqa: E402
import vertex_codec as vc  # noqa: E402
import xmodel  # noqa: E402
import xsurface  # noqa: E402
from build_authored_weapon import expand, load_recipe  # noqa: E402


def load(dump, name):
    raw = open(os.path.join(dump, "xmodel", name + ".xmb"), "rb").read()
    xm = xmodel.read(raw)
    lods = []
    for i in range(xm.get("numLods")):
        ls = xm.lod_surfs[i]
        p = os.path.join(dump, "xsurface", ls + ".xsb")
        lods.append((p, xsurface.read(open(p, "rb").read()) if os.path.exists(p) else None))
    return raw, xm, lods


def bone_tris(xm, ms):
    """{bone name: (N, 3, 3) triangles} of a surfaces file: rigid lists (contiguous vertex runs) and skinned vertices
    (the bone of largest weight; a triangle goes to its first vertex's bone). Surfaces whose vertices are re-used
    from another surface (offset record) are skipped."""
    out = {}
    for s in ms.surfs:
        if not s.verts:
            continue
        vb = [0] * len(s.verts)
        v0 = 0
        for rl in s.rigid:
            for k in range(v0, v0 + rl[1]):
                vb[k] = rl[0]
            v0 += rl[1]
        for vi, inf, _ in vc.decode_blend(s.blend or [], s.blend_counts):
            vb[vi] = max(inf, key=lambda x: x[1])[0]
        pos = np.array([v[:3] for v in s.verts], float)
        faces = np.array(s.faces, int)
        for b in np.unique([vb[f[0]] for f in faces]):
            sel = np.array([vb[f[0]] == b for f in faces])
            out.setdefault(xm.bone_names[b], []).append(pos[faces[sel]])
    return {k: np.concatenate(v) for k, v in out.items()}


def box(tris):
    a = tris.reshape(-1, 3)
    return [round(float(x), 3) for x in list(a.min(0)) + list(a.max(0))]


def _clip(poly, axis, value, keep_greater):
    out = []
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        pin = p[axis] >= value if keep_greater else p[axis] <= value
        qin = q[axis] >= value if keep_greater else q[axis] <= value
        if pin:
            out.append(p)
        if pin != qin:
            t = (value - p[axis]) / (q[axis] - p[axis])
            out.append(p + t * (q - p))
    return out


def zone_extents(tris, zone):
    """Extents of the surface inside the zone's x window (and z window): triangles clipped to the windows, so long
    faces with no vertex inside the window still count."""
    pts = []
    lo_x, hi_x = zone["x"]
    windows = [(0, lo_x, True), (0, hi_x, False)]
    if "z" in zone:
        windows += [(2, zone["z"][0], True), (2, zone["z"][1], False)]
    tmin, tmax = tris.min(1), tris.max(1)
    sel = (tmax[:, 0] >= lo_x) & (tmin[:, 0] <= hi_x)
    if "z" in zone:
        sel &= (tmax[:, 2] >= zone["z"][0]) & (tmin[:, 2] <= zone["z"][1])
    for t in tris[sel]:
        poly = [t[0], t[1], t[2]]
        for axis, value, greater in windows:
            poly = _clip(poly, axis, value, greater)
            if not poly:
                break
        pts += poly
    if not pts:
        return None
    a = np.array(pts)
    lo, hi = a.min(0), a.max(0)
    return {"xmin": lo[0], "xmax": hi[0], "ymin": lo[1], "ymax": hi[1], "zmin": lo[2], "zmax": hi[2]}


def compare_zone(ours, donor, zone):
    eo, ed = zone_extents(ours, zone), zone_extents(donor, zone)
    if eo is None or ed is None:
        return {"zone": zone["name"], "ok": False, "why": "no surface in the window", "ours": eo, "donor": ed}
    keys = zone.get("measure", ["ymin", "ymax", "zmin", "zmax"])
    d = {k: round(float(eo[k] - ed[k]), 3) for k in keys}
    worst = max(abs(v) for v in d.values())
    return {"zone": zone["name"], "bone": zone["bone"], "ok": worst <= zone["tolerance"], "worst_in": round(worst, 3),
            "delta": d, "ours": {k: round(float(eo[k]), 3) for k in keys},
            "donor": {k: round(float(ed[k]), 3) for k in keys}}


def check_bones(ours, donor):
    fails = []
    if ours.bone_names != donor.bone_names:
        fails.append("bone names differ")
    if ours.parents != donor.parents:
        fails.append("parents differ")
    for field in ("base_mat", "tag_angles", "tag_positions"):
        if getattr(ours, field) != getattr(donor, field):
            fails.append(field + " differ")
    if ours.part_class != donor.part_class:
        fails.append("part classification differs")
    for k in ("numBones", "numRootBones", "numClientBones"):
        if ours.get(k) != donor.get(k):
            fails.append(k + " differs")
    return fails


def check_weights(xm, lods):
    fails, per_bone, verts = [], {}, 0
    nb = xm.get("numBones") + xm.get("numClientBones")
    for li, (_, ms) in enumerate(lods):
        for si, s in enumerate(ms.surfs):
            verts += s.vert_count
            if s.rigid or s.rigid_count:
                fails.append("lod%d surf%d has rigid lists" % (li, si))
            if any(s.blend_counts[1:]):
                fails.append("lod%d surf%d has multi-bone vertices %r" % (li, si, s.blend_counts[:4]))
            if s.blend_counts[0] != s.vert_count:
                fails.append("lod%d surf%d: %d of %d vertices weighted" % (li, si, s.blend_counts[0], s.vert_count))
            for _, inf, _ in vc.decode_blend(s.blend or [], s.blend_counts):
                if len(inf) != 1 or abs(inf[0][1] - 1.0) > 1e-9 or not 0 <= inf[0][0] < nb:
                    fails.append("lod%d surf%d: bad influence %r" % (li, si, inf))
                    break
                n = xm.bone_names[inf[0][0]]
                per_bone[n] = per_bone.get(n, 0) + 1
    return fails, per_bone, verts


def check_camo(out_dir, xm, lods):
    res, fails = [], []
    for li, (path, ms) in enumerate(lods):
        _, parsed = iw7_xsurface_uv2.parse(open(path, "rb").read())
        first = xm.lod(li)[2]
        for si, s in enumerate(parsed):
            mat = xm.materials[first + si]
            mpath = os.path.join(out_dir, "materials", mat.replace("/", os.sep) + ".json")
            technique = json.load(open(mpath))["techniqueSet->name"] if os.path.exists(mpath) else "?"
            camo = "_2uvt" in technique
            rec = s["second"]
            n = len(rec) // 24 if rec else 0
            dev = 0.0
            for k in range(n):
                b = struct.unpack_from("<4f", rec, 24 * k + 8)
                dev = max(dev, abs(b[0] - 1), abs(b[1]), abs(b[2]), abs(b[3] - 1))
            row = {"lod": li, "surface": si, "material": mat, "camo_technique": camo, "flags": hex(s["flags"]),
                   "records": n, "verts": s["vert_count"], "basis_max_dev": round(dev, 6)}
            res.append(row)
            if camo and not (s["flags"] & 0x400 and n == s["vert_count"]):
                fails.append("lod%d surf%d (%s) lacks camo records" % (li, si, mat))
    return res, fails


def check_roundtrip(raw, lods):
    fails, normals = [], []
    if xmodel.write(xmodel.read(raw)) != raw:
        fails.append("xmodel round trip differs")
    for path, _ in lods:
        b = open(path, "rb").read()
        if xsurface.write(xsurface.read(b)) != b:
            fails.append("xsurface round trip differs: " + os.path.basename(path))
        r = iw7_xsurface_check.check_file(path)
        normals.append(r)
    return fails, normals


# ------------------------------------------------------------------ first-person preview
def gun_mesh(xm, ms):
    verts, bones, tris = [], [], []
    for s in ms.surfs:
        if not s.verts:
            continue
        base = len(verts)
        vb = [None] * len(s.verts)
        if s.rigid:
            v0 = 0
            for rl in s.rigid:
                for k in range(v0, v0 + rl[1]):
                    vb[k] = rl[0]
                v0 += rl[1]
        for vi, inf, _ in vc.decode_blend(s.blend or [], s.blend_counts):
            vb[vi] = max(inf, key=lambda x: x[1])[0]
        verts += [v[:3] for v in s.verts]
        bones += [b if b is not None else 0 for b in vb]
        tris += [(a + base, b + base, c + base) for a, b, c in s.faces]
    return np.array(verts), np.array(bones), np.array(tris)


def render_shots(recipe, dump, out_dir, vm_name, donor_name, preview_dir):
    import t7_viewmodel_preview as pv
    import t7_vm_retarget as rig
    import iw7_xanim_codec as codec
    from PIL import Image
    cfg = expand(recipe["proof"]["preview"])
    skel = rig.Skeleton(cfg["hands_skeleton"])
    hands = pv.load_mesh(cfg["hands_mesh"])
    size = tuple(int(x) for x in cfg["size"].split("x"))
    made = []
    guns = {}
    for tag, root, name in (("ours", out_dir, vm_name), ("donor", dump, donor_name)):
        raw, xm, lods = load(root, name)
        guns[tag] = (rig.Skeleton(os.path.join(root, "xmodel", name + ".xmb")), gun_mesh(xm, lods[0][1]))
    for shot in cfg["shots"]:
        anim = codec.decode(os.path.join(cfg["anim_dir"], shot["anim"] + ".xab"))
        frame = shot["frame"] if shot["frame"] >= 0 else anim.frames - 1
        panels = []
        for tag in ("ours", "donor"):
            gskel, (verts, vbones, tris) = guns[tag]
            pose = pv.pose_of(skel, anim, frame)
            cam_rot, cam_pos = pose["tag_camera"]
            gpose = gskel.pose(anim.rotations, anim.translations, frame)
            trot, tpos = pose["tag_weapon"]
            world = np.zeros_like(verts)
            for b in np.unique(vbones):
                sel = vbones == b
                bq, bp = gskel.world[b]
                pq, pp = gpose[b]
                local = (verts[sel] - np.array(bp)) @ pv.quat_matrix(bq)
                model = local @ pv.quat_matrix(pq).T + np.array(pp)
                world[sel] = model @ trot.T + tpos
            w, h = size
            half = math.atan(math.tan(math.radians(cfg["fov"]) / 2) * (w / h) / (4 / 3))
            focal = (w / 2) / math.tan(half)
            image = np.zeros((h, w, 3))
            zbuf = np.full((h, w), np.inf)
            pv.raster(image, zbuf, pv.skin(hands, pose), hands["tris"], (0.35, 0.55, 0.95), cam_rot, cam_pos, focal,
                      size)
            pv.raster(image, zbuf, world, tris, (0.3, 0.85, 0.45) if tag == "ours" else (1.0, 0.6, 0.2), cam_rot,
                      cam_pos, focal, size)
            panels.append((np.clip(image, 0, 1) * 255).astype(np.uint8))
        img = np.concatenate(panels, axis=1)
        p = os.path.join(preview_dir, "fp_%s_f%d.png" % (shot["anim"], frame))
        Image.fromarray(img).save(p)
        made.append(p)
    return made


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("recipe")
    ap.add_argument("--donor-dump", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--json")
    ap.add_argument("--preview-dir")
    a = ap.parse_args(argv)
    recipe = load_recipe(a.recipe)
    result = {"models": {}, "ok": True}
    vm_donor_pts = None
    for mi, m in enumerate(recipe["models"]):
        raw, xm, lods = load(a.out, m["name"])
        _, dxm, dlods = load(a.donor_dump, m["donor"])
        r = {}
        r["bones_fail"] = check_bones(xm, dxm)
        wf, per_bone, nverts = check_weights(xm, lods)
        r["weights_fail"], r["verts_per_bone"], r["verts_total"] = wf, per_bone, nverts
        ours_pts = bone_tris(xm, lods[0][1])
        donor_pts = bone_tris(dxm, dlods[0][1])
        r["bounds"] = {b: {"ours": box(ours_pts[b]), "donor": box(donor_pts[b]) if b in donor_pts else None}
                       for b in sorted(ours_pts)}
        r["model_bounds"] = {"ours": xm.get("bounds"), "donor": dxm.get("bounds")}
        zones = []
        if mi == 0:
            for z in recipe.get("proof", {}).get("hand_zones", []):
                if z["bone"] in ours_pts and z["bone"] in donor_pts:
                    zones.append(compare_zone(ours_pts[z["bone"]], donor_pts[z["bone"]], z))
                else:
                    zones.append({"zone": z["name"], "ok": False, "why": "bone has no surface"})
            vm_donor_pts = donor_pts
        r["hand_zones"] = zones
        built = {at["materials"][m.get("view", "vm")]["name"] for at in recipe["atlases"].values()
                 if at["materials"][m.get("view", "vm")]}
        r["materials_fail"] = ["material %s is not one the recipe builds" % mn for mn in sorted(set(xm.materials))
                               if mn not in built]
        r["camo"], r["camo_fail"] = check_camo(a.out, xm, lods)
        r["roundtrip_fail"], r["normals"] = check_roundtrip(raw, lods)
        normals_fail = [n for n in r["normals"] if n.get("errors")]
        r["lods"] = [{"surfaces": len(ms.surfs), "tris": sum(s.tri_count for s in ms.surfs),
                      "verts": sum(s.vert_count for s in ms.surfs), "dist": xm.lod(i)[0]}
                     for i, (_, ms) in enumerate(lods)]
        r["donor_lods"] = [{"tris": sum(s.tri_count for s in ms.surfs)} for _, ms in dlods if ms]
        ok = not (r["bones_fail"] or wf or r["camo_fail"] or r["roundtrip_fail"] or normals_fail or r["materials_fail"]
                  or any(not z["ok"] for z in zones))
        r["ok"] = ok
        result["ok"] &= ok
        result["models"][m["name"]] = r
    if a.preview_dir and recipe.get("proof", {}).get("preview"):
        os.makedirs(a.preview_dir, exist_ok=True)
        try:
            result["previews"] = render_shots(recipe, a.donor_dump, a.out, recipe["models"][0]["name"],
                                              recipe["models"][0]["donor"], a.preview_dir)
        except KeyError as e:
            result["previews"] = "skipped: %s" % e
    if a.json:
        json.dump(result, open(a.json, "w"), indent=1, default=str)
    for name, r in result["models"].items():
        print("%s ok=%s bones_fail=%s weights_fail=%d verts=%d camo_fail=%d roundtrip_fail=%s materials_fail=%s" % (
            name, r["ok"], r["bones_fail"], len(r["weights_fail"]), r["verts_total"], len(r["camo_fail"]),
            r["roundtrip_fail"], r["materials_fail"]))
        for z in r["hand_zones"]:
            print("  zone %-24s ok=%s worst=%s delta=%s" % (z["zone"], z["ok"], z.get("worst_in"), z.get("delta")))
        print("  lods", r["lods"], "donor", r["donor_lods"])
    print("PROOF_OK" if result["ok"] else "PROOF_FAILED")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

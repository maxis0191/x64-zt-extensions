"""M1 proof: byte-exact read->write of IW7 .xsb/.xmb dumps and decode cross-check against GrayWolf glb exports.

python -I m1_proof.py --dump <cp_zmb dump dir> --glb-root <heroes/stock_cp_zmb/iw/models> --out <report.json>
"""
import argparse
import glob
import hashlib
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xmodel  # noqa: E402
import xsurface  # noqa: E402
import vertex_codec as vc  # noqa: E402
from glb_read import Glb  # noqa: E402

INCH_TO_GLB = 2.54  # GrayWolf/Greyhound glb mesh space is centimetres (root node then scales by 0.01)

CASES = [  # (xmodel, lod0 xsurface glob, glb model folder)
    ("body_zmb_hero_jock", "body_zmb_hero_jock_lod0*.xsb", "body_zmb_hero_jock"),
    ("head_zmb_hero_jock", "head_hero_jock*.xsb", "head_zmb_hero_jock"),
    ("fullbody_zmb_hero_jock_viewmodel_arms", "zmb_hero_jock_viewmodel_arms_lod0*.xsb",
     "fullbody_zmb_hero_jock_viewmodel_arms"),
]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def roundtrip(path, mod):
    b = open(path, "rb").read()
    out = mod.write(mod.read(b))
    return {"file": os.path.basename(path), "bytes": len(b), "sha256": sha(b), "rewrite_sha256": sha(out),
            "exact": out == b}


def crosscheck(xm, ms, glb):
    jn = glb.joint_names()
    res = {"glb_joint_order_equals_xmodel_bones": jn == xm.bone_names, "surfaces": []}
    prims = list(glb.primitives())
    for si, s in enumerate(ms.surfs):
        r = {"surface": si, "flags": hex(s.flags), "verts": s.vert_count, "tris": s.tri_count,
             "blend_counts": s.blend_counts, "rigid_lists": [x[:4] for x in s.rigid]}
        if si >= len(prims):
            r["glb"] = "missing"
            res["surfaces"].append(r)
            continue
        prim = prims[si][3]
        A = prim["attributes"]
        P, N, T = glb.accessor(A["POSITION"]), glb.accessor(A["NORMAL"]), glb.accessor(A["TEXCOORD_0"])
        J, W = glb.accessor(A["JOINTS_0"]), glb.accessor(A["WEIGHTS_0"])
        I = glb.accessor(prim["indices"])
        r["glb_verts"] = len(P)
        if len(P) != s.vert_count:
            r["glb"] = "vertex count differs"
            res["surfaces"].append(r)
            continue
        r["max_pos_err_in"] = max(abs(P[k][i] / INCH_TO_GLB - v[i]) for k, v in enumerate(s.verts) for i in range(3))
        r["max_normal_err"] = max(abs(a - b) for k, v in enumerate(s.verts) for a, b in zip(vc.unpack_normal(v[6]), N[k]))
        r["normal_reencode_exact"] = sum(1 for v in s.verts if vc.pack_normal(vc.unpack_normal(v[6]), v[6] >> 30) == v[6])
        r["max_uv_err"] = max(abs(a - b) for k, v in enumerate(s.verts) for a, b in zip(vc.unpack_uv(v[5]), T[k]))
        r["uv_reencode_exact"] = sum(1 for v in s.verts if vc.pack_uv(*vc.unpack_uv(v[5])) == v[5])
        tri = [tuple(I[i:i + 3]) for i in range(0, len(I), 3)]
        r["faces_equal_glb"] = tri == [tuple(f) for f in s.faces]
        r["faces_equal_glb_reversed"] = [(a, c, b) for a, b, c in tri] == [tuple(f) for f in s.faces]
        bone_mis = 0
        werr = 0.0
        if s.blend:
            for vi, inf, _ in s.blend_groups():
                gl = sorted([(J[vi][i], W[vi][i]) for i in range(4) if W[vi][i] > 0], key=lambda x: (-x[1], x[0]))
                mine = sorted(inf, key=lambda x: (-x[1], x[0]))
                if len(gl) != len(mine) or {b for b, _ in gl} != {b for b, _ in mine}:
                    bone_mis += 1
                    continue
                werr = max(werr, max(abs(a[1] - b[1]) for a, b in zip(gl, mine)))
        else:
            start = 0
            for rl in s.rigid:
                for k in range(start, start + rl[1]):
                    if J[k][0] != rl[0] or abs(W[k][0] - 1.0) > 1e-6:
                        bone_mis += 1
                start += rl[1]
        r["bone_mismatches"] = bone_mis
        r["max_weight_err"] = werr
        used = vc.surface_bones(s)
        r["part_bits_formula_matches"] = vc.part_bits(used) == s.part_bits
        res["surfaces"].append(r)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", required=True)
    ap.add_argument("--glb-root", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    report = {"roundtrip": [], "crosscheck": {}}
    for model, surf_glob, glb_dir in CASES:
        xmb = os.path.join(a.dump, "xmodel", model + ".xmb")
        report["roundtrip"].append(roundtrip(xmb, xmodel))
        xm = xmodel.read(open(xmb, "rb").read())
        for p in sorted(glob.glob(os.path.join(a.dump, "xsurface", surf_glob))):
            report["roundtrip"].append(roundtrip(p, xsurface))
        lod0 = os.path.join(a.dump, "xsurface", xm.lod_surfs[0] + ".xsb")
        ms = xsurface.read(open(lod0, "rb").read())
        glbp = glob.glob(os.path.join(a.glb_root, glb_dir, "*_LOD0.glb"))
        if glbp:
            report["crosscheck"][model] = crosscheck(xm, ms, Glb(glbp[0]))
    report["all_exact"] = all(r["exact"] for r in report["roundtrip"])
    json.dump(report, open(a.out, "w"), indent=1)
    print("roundtrip files %d exact=%s" % (len(report["roundtrip"]), report["all_exact"]))
    for k, v in report["crosscheck"].items():
        print(k, "joints==bones", v["glb_joint_order_equals_xmodel_bones"])
        for s in v["surfaces"]:
            print("  s%d %s v=%d pos_err=%.2g n_err=%.2g n_re=%s uv_err=%.2g faces=%s/%s bone_mis=%s w_err=%.2g partbits=%s" % (
                s["surface"], s["flags"], s["verts"], s.get("max_pos_err_in", -1), s.get("max_normal_err", -1),
                s.get("normal_reencode_exact"), s.get("max_uv_err", -1), s.get("faces_equal_glb"),
                s.get("faces_equal_glb_reversed"), s.get("bone_mismatches"), s.get("max_weight_err", -1),
                s.get("part_bits_formula_matches")))


if __name__ == "__main__":
    main()

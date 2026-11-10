"""M2 proof: compare a writer-built XModelSurfs (from the unmodified stock glb through Blender) with the stock dump.

python -I m2_proof.py <built .xsb> <stock .xsb> [--out report.json]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vertex_codec as vc  # noqa: E402
import xsurface  # noqa: E402


def compare(b, s):
    r = {"verts": (b.vert_count, s.vert_count), "tris": (b.tri_count, s.tri_count),
         "blend_counts_equal": b.blend_counts == s.blend_counts}
    if b.vert_count != s.vert_count:
        return r
    n = b.vert_count
    r["max_pos_err_in"] = max(abs(x - y) for bv, sv in zip(b.verts, s.verts) for x, y in zip(bv[:3], sv[:3]))
    r["uv_exact"] = sum(1 for bv, sv in zip(b.verts, s.verts) if bv[5] == sv[5]) / n
    r["normal_exact"] = sum(1 for bv, sv in zip(b.verts, s.verts) if bv[6] == sv[6]) / n
    r["normal_max_err"] = max(abs(x - y) for bv, sv in zip(b.verts, s.verts)
                              for x, y in zip(vc.unpack_normal(bv[6]), vc.unpack_normal(sv[6])))
    r["tangent_sign_agree"] = sum(1 for bv, sv in zip(b.verts, s.verts) if bv[7] >> 30 == sv[7] >> 30) / n
    dots = []
    for bv, sv in zip(b.verts, s.verts):
        tb, ts = vc.unpack_normal(bv[7]), vc.unpack_normal(sv[7])
        dots.append(sum(x * y for x, y in zip(tb, ts)))
    dots.sort()
    r["tangent_dot_p01_p50"] = (dots[len(dots) // 100], dots[len(dots) // 2])
    r["faces_equal"] = b.faces == s.faces
    r["blend_equal"] = b.blend == s.blend if s.blend else None
    if s.blend and b.blend != s.blend:
        werr = 0.0
        bm = 0
        for (vi, ib, _), (_, is_, _) in zip(b.blend_groups(), s.blend_groups()):
            if [x for x, _ in ib] != [x for x, _ in is_]:
                bm += 1
            werr = max([werr] + [abs(x[1] - y[1]) for x, y in zip(ib, is_)])
        r["blend_bone_order_mismatch"], r["blend_max_weight_err"] = bm, werr
    if not s.blend and s.rigid:
        r["stock_rigid_bone"] = s.rigid[0][0]
        r["built_single_bones"] = sorted({inf[0][0] for _, inf, _ in b.blend_groups()})
    r["part_bits_equal"] = b.part_bits == s.part_bits
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("built")
    ap.add_argument("stock")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    B = xsurface.read(open(a.built, "rb").read())
    S = xsurface.read(open(a.stock, "rb").read())
    rep = {"built": a.built, "stock": a.stock, "surfaces": [compare(b, s) for b, s in zip(B.surfs, S.surfs)]}
    rep["model_part_bits_equal"] = B.part_bits == S.part_bits
    for i, r in enumerate(rep["surfaces"]):
        print(i, json.dumps(r))
    if a.out:
        json.dump(rep, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()

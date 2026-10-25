"""Approximate Kino player collision with cloned IW7 stock collision plates.

Voxelizes BO3 clip brushes (player-blocking contents), the clip triangle soup
and selected static-model bounds; flood-fills the player-reachable space near
the BO3 pathnodes; then greedily covers the floor and wall faces bordering that
space with axis-aligned plates whose volume never enters reachable cells.
Output: collision.json, a list of {donor, origin, angles} in BO3 coordinates.
"""
import argparse, array, json, math, re
import numpy as np
from scipy import ndimage

R = 16.0  # voxel size
# Measured cp_zmb donors: size (x, y, z), local offset of geometry center from origin.
DONORS = {
    "playerai512x512x8": ((256, 256, 8), (0, 0, 4)),
    "playerai128x128x8": ((128, 128, 8), (0, 0, 4)),
    "player64x64x8": ((64, 64, 8), (0, 0, 4)),
    "player32x32x8": ((32, 32, 8), (0, 0, 4)),
}
PLATES = ["playerai512x512x8", "playerai128x128x8", "player64x64x8", "player32x32x8"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--reach", type=float, default=260.0)
    a = ap.parse_args()
    E = a.export
    clip = json.load(open(E + "/clip.json"))
    pn = json.load(open(E + "/pathnodes.json"))
    ents = open(E + "/mapents.txt", encoding="latin-1").read()
    nodes = np.array([n["origin"] for n in pn], dtype=np.float64)
    lo = nodes.min(0) - np.array([700, 700, 300]); hi = nodes.max(0) + np.array([700, 700, 900])
    dims = np.ceil((hi - lo) / R).astype(int)
    print("grid", dims, dims.prod())
    solid = np.zeros(dims, dtype=bool)

    def idx(p):
        return np.floor((np.asarray(p) - lo) / R).astype(int)

    centers = [lo[k] + (np.arange(dims[k]) + 0.5) * R for k in range(3)]

    # Brushes.
    used = 0
    for b in clip["brushes"]:
        if not (b["contents"] & 0x10001):
            continue
        mn = np.maximum(idx(b["mins"]), 0); mx = np.minimum(idx(b["maxs"]) + 1, dims)
        if np.any(mx <= mn):
            continue
        X, Y, Z = np.meshgrid(centers[0][mn[0]:mx[0]], centers[1][mn[1]:mx[1]], centers[2][mn[2]:mx[2]], indexing="ij")
        inside = (X >= b["mins"][0]) & (X <= b["maxs"][0]) & (Y >= b["mins"][1]) & (Y <= b["maxs"][1]) & (Z >= b["mins"][2]) & (Z <= b["maxs"][2])
        for s in b["sides"]:
            pl = s["plane"]
            if pl:
                inside &= (X * pl[0] + Y * pl[1] + Z * pl[2]) <= pl[3] + R * 0.5
        solid[mn[0]:mx[0], mn[1]:mx[1], mn[2]:mx[2]] |= inside
        used += 1
    print("brushes used", used, "solid", int(solid.sum()))

    # Triangle soup: dense barycentric samples.
    v = np.frombuffer(open(E + "/clip_verts.f32", "rb").read(), dtype=np.float32).reshape(-1, 3).astype(np.float64)
    t = np.frombuffer(open(E + "/clip_tris.u32", "rb").read(), dtype=np.uint32).reshape(-1, 3)
    A, B, C = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    span = np.maximum(np.maximum(np.linalg.norm(B - A, axis=1), np.linalg.norm(C - A, axis=1)), np.linalg.norm(C - B, axis=1))
    for steps in (2, 4, 8, 16, 32, 64, 128, 256):
        sel = (span <= steps * R * 0.5) & (span > (steps // 2) * R * 0.5) if steps > 2 else (span <= steps * R * 0.5)
        if not sel.any():
            continue
        uu, vv = np.meshgrid(np.linspace(0, 1, steps + 1), np.linspace(0, 1, steps + 1))
        m = (uu + vv) <= 1.0
        uu, vv = uu[m], vv[m]
        a_, b_, c_ = A[sel], B[sel], C[sel]
        pts = a_[:, None, :] + (b_ - a_)[:, None, :] * uu[None, :, None] + (c_ - a_)[:, None, :] * vv[None, :, None]
        ii = idx(pts.reshape(-1, 3))
        ok = np.all((ii >= 0) & (ii < dims), axis=1)
        ii = ii[ok]
        solid[ii[:, 0], ii[:, 1], ii[:, 2]] = True
    big = span > 128 * R * 0.5
    print("tris", len(t), "oversized skipped", int(big.sum()), "solid", int(solid.sum()))

    # Static models with player-blocking contents (bounds, skipping tiny debris).
    smc = 0
    for s in clip["static_models"]:
        if not (s["contents"] & 0x10001):
            continue
        mn_, mx_ = np.array(s["absmin"]), np.array(s["absmax"])
        size = mx_ - mn_
        if size[2] < 24 or max(size[0], size[1]) < 12 or max(size) > 600:
            continue
        a0 = np.maximum(idx(mn_ + 2), 0); a1 = np.minimum(idx(mx_ - 2) + 1, dims)
        if np.any(a1 <= a0):
            continue
        solid[a0[0]:a1[0], a0[1]:a1[1], a0[2]:a1[2]] = True
        smc += 1
    print("static model boxes", smc)

    # Reachable space: empty cells within reach of a pathnode, connected to them.
    near = np.zeros(dims, dtype=bool)
    rr = int(math.ceil(a.reach / R))
    for n in nodes:
        c = idx(n)
        x0, x1 = max(c[0] - rr, 0), min(c[0] + rr + 1, dims[0])
        y0, y1 = max(c[1] - rr, 0), min(c[1] + rr + 1, dims[1])
        z0, z1 = max(c[2] - 3, 0), min(c[2] + 10, dims[2])
        near[x0:x1, y0:y1, z0:z1] = True
    empty = near & ~solid
    lab, count = ndimage.label(empty)
    seeds = set()
    for n in nodes:
        c = idx(n) + np.array([0, 0, 1])
        if np.all(c >= 0) and np.all(c < dims) and lab[tuple(c)]:
            seeds.add(lab[tuple(c)])
    reach = np.isin(lab, list(seeds))
    print("reachable cells", int(reach.sum()), "components", len(seeds))

    plates = []

    def cover(mask, notreach, place_fn):
        """Greedy cover of a 2D mask with square plates whose footprint stays in non-reachable cells."""
        todo = mask.copy()
        h, w = mask.shape
        ii_nr = np.zeros((h + 1, w + 1), dtype=np.int32)
        ii_nr[1:, 1:] = np.cumsum(np.cumsum(notreach.astype(np.int32), 0), 1)
        for donor in PLATES:
            (sx, sy, _), _ = DONORS[donor]
            n = int(sx // R)
            if n < 1 or n > min(h, w):
                continue
            ok = (ii_nr[n:, n:] - ii_nr[:-n, n:] - ii_nr[n:, :-n] + ii_nr[:-n, :-n]) == n * n  # anchor (i0,j0) valid
            offs = sorted({0, n // 2, n - 1})
            cells = np.argwhere(todo)
            for i, j in cells:
                if not todo[i, j]:
                    continue
                best = None
                for di in offs:
                    for dj in offs:
                        i0, j0 = i - di, j - dj
                        if i0 < 0 or j0 < 0 or i0 + n > h or j0 + n > w or not ok[i0, j0]:
                            continue
                        gain = int(todo[i0:i0 + n, j0:j0 + n].sum())
                        if best is None or gain > best[0]:
                            best = (gain, i0, j0)
                if best and (best[0] >= max(1, (n * n) // 4) or donor == PLATES[-1]):
                    _, i0, j0 = best
                    todo[i0:i0 + n, j0:j0 + n] = False
                    place_fn(donor, i0, j0, n)
        return int(todo.sum())

    # Floors: solid cell with reachable cell directly above.
    floor = solid[:, :, :-1] & reach[:, :, 1:]
    left_floor = 0
    for z in range(dims[2] - 1):
        m = floor[:, :, z]
        if not m.any():
            continue
        notreach = ~reach[:, :, z]

        def place(donor, i0, j0, n, z=z):
            cx = lo[0] + (i0 + n / 2.0) * R; cy = lo[1] + (j0 + n / 2.0) * R
            top = lo[2] + (z + 1) * R
            plates.append({"donor": donor, "kind": "floor", "origin": [cx, cy, top - 8.0], "angles": [0, 0, 0]})
        left_floor += cover(m, notreach, place)

    # Walls: solid cell with a reachable horizontal neighbour; plate stands in the solid cell.
    left_wall = 0
    for axis, sign in ((0, 1), (0, -1), (1, 1), (1, -1)):
        sh = np.roll(reach, -sign, axis=axis)
        if sign > 0:
            sl = [slice(None)] * 3; sl[axis] = slice(-1, None); sh[tuple(sl)] = False
        else:
            sl = [slice(None)] * 3; sl[axis] = slice(0, 1); sh[tuple(sl)] = False
        face = solid & sh
        for k in range(dims[axis]):
            if axis == 0:
                m = face[k, :, :]; nr = ~reach[k, :, :]
            else:
                m = face[:, k, :]; nr = ~reach[:, k, :]
            if not m.any():
                continue

            def place(donor, i0, j0, n, k=k, axis=axis, sign=sign):
                # Plate face flush with the reachable side of the solid cell.
                faceplane = lo[axis] + (k + (1 if sign > 0 else 0)) * R
                mid_h = lo[1 - axis] + (i0 + n / 2.0) * R
                mid_z = lo[2] + (j0 + n / 2.0) * R
                c = [0.0, 0.0, mid_z]
                c[axis] = faceplane - sign * 4.0
                c[1 - axis] = mid_h
                if axis == 0:
                    ang = [90, 0, 0]       # thin along x
                    # pitch 90: local +z -> world +x; geometry center offset (0,0,4) -> (4,0,0)
                    off = [4.0, 0.0, 0.0]
                else:
                    ang = [0, 0, 90]       # roll 90: thin along y
                    off = [0.0, -4.0, 0.0]
                plates.append({"donor": donor, "kind": "wall", "origin": [c[0] - off[0], c[1] - off[1], c[2] - off[2]], "angles": ang})
            left_wall += cover(m, nr, place)

    kinds = {}
    for p in plates:
        kinds[(p["kind"], p["donor"])] = kinds.get((p["kind"], p["donor"]), 0) + 1
    print("plates", len(plates), kinds, "uncovered floor", left_floor, "wall", left_wall)
    json.dump({"schema": "kino.collision/1", "voxel": R, "plates": plates}, open(a.out, "w"))


if __name__ == "__main__":
    main()

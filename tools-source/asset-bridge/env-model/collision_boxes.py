"""Axis-aligned clip boxes for a model from a surface voxelisation (numpy).

Every triangle marks the voxels it passes through (sampled densely: a triangle is split into points no further
apart than half a voxel); the occupied voxels are merged greedily into boxes (x runs, then y, then z). Thin
walls stay one voxel thick; openings wider than about two voxels (doors, gaps) stay open. Boxes are in model
space: [[minx, miny, minz], [maxx, maxy, maxz]] inches, for the map generator's world collision.
"""
import numpy as np


def sample_points(P, tris, step):
    pts = [P[tris].mean(1)]
    a, b, c = P[tris[:, 0]], P[tris[:, 1]], P[tris[:, 2]]
    edge = np.maximum(np.maximum(np.linalg.norm(b - a, axis=1), np.linalg.norm(c - b, axis=1)),
                      np.linalg.norm(a - c, axis=1))
    n = np.clip(np.ceil(edge / step).astype(int), 1, 256)
    for k in np.unique(n):
        sel = n == k
        i, j = np.meshgrid(np.arange(k + 1), np.arange(k + 1), indexing='ij')
        keep = (i + j) <= k
        u = (i[keep] / k)[None, :, None]
        v = (j[keep] / k)[None, :, None]
        pts.append((a[sel][:, None] * (1 - u - v) + b[sel][:, None] * u + c[sel][:, None] * v).reshape(-1, 3))
    return np.concatenate(pts)


def greedy_boxes(occ):
    """occ: bool (X, Y, Z) -> list of (x0, y0, z0, x1, y1, z1) index boxes (exclusive ends)."""
    occ = occ.copy()
    X, Y, Z = occ.shape
    out = []
    for z in range(Z):
        for y in range(Y):
            x = 0
            while x < X:
                if not occ[x, y, z]:
                    x += 1
                    continue
                x1 = x
                while x1 < X and occ[x1, y, z]:
                    x1 += 1
                y1 = y + 1
                while y1 < Y and occ[x:x1, y1, z].all():
                    y1 += 1
                z1 = z + 1
                while z1 < Z and occ[x:x1, y:y1, z1].all():
                    z1 += 1
                occ[x:x1, y:y1, z:z1] = False
                out.append((x, y, z, x1, y1, z1))
                x = x1
    return out


def boxes_from_mesh(groups, voxel, min_thickness=4.0):
    P = np.concatenate([g['P'] for g in groups.values()])
    lo = P.min(0) - voxel
    pts = []
    for g in groups.values():
        if len(g['tris']):
            pts.append(sample_points(g['P'], g['tris'], voxel * 0.5))
    pts = np.concatenate(pts)
    idx = np.floor((pts - lo) / voxel).astype(int)
    shape = idx.max(0) + 2
    occ = np.zeros(shape, bool)
    occ[idx[:, 0], idx[:, 1], idx[:, 2]] = True
    out = []
    for x0, y0, z0, x1, y1, z1 in greedy_boxes(occ):
        mn = lo + np.array([x0, y0, z0]) * voxel
        mx = lo + np.array([x1, y1, z1]) * voxel
        # keep a minimum thickness so a player capsule cannot slip through a one-voxel wall
        for k in range(3):
            if mx[k] - mn[k] < min_thickness:
                c = (mx[k] + mn[k]) / 2
                mn[k], mx[k] = c - min_thickness / 2, c + min_thickness / 2
        out.append([[round(float(v), 2) for v in mn], [round(float(v), 2) for v in mx]])
    return out

"""Build a walk graph over the BO3 pathnodes for scripted IW7 zombies.

IW7 agents need a navmesh, which cannot be authored for the overlay, so the
server moves zombies along this graph instead. Nodes are snapped to the
walkable floor sampled exactly as in kino_collision.py; two nodes are linked
when the straight walk between them stays on walkable cells with steps of at
most STEP units. Output kino.navgraph/1 (BO3 coordinates).
"""
import argparse, json, math
import numpy as np
import kino_collision as kc

LINK = 360.0
STEP = 20.0
SAMPLE = 8.0
SHORT = 240.0
BRIDGE = 300.0
SOLID = DIMS = None


def walkable_columns(E):
    nodes = np.array([n["origin"] for n in json.load(open(E + "/pathnodes.json"))], dtype=np.float64)
    R = kc.R
    lo = nodes.min(0) - np.array([700, 700, 300]); hi = nodes.max(0) + np.array([700, 700, 900])
    dims = np.ceil((hi - lo) / R).astype(int)
    brushes, A, B, C = kc.brushes_and_tris(E)
    solid = kc.voxelize(brushes, A, B, C, lo, dims)
    H = kc.surface_heights(brushes, A, B, C, lo, dims)
    cols = {}
    global SOLID, DIMS
    SOLID, DIMS = solid, dims
    for (i, j), zs in H.items():
        for z in sorted(set(round(z, 1) for z in zs)):
            k = int((z + 17 - lo[2]) // R)
            if k < 0 or k + 4 >= dims[2] or solid[i, j, k:k + 4].any():
                continue
            cols.setdefault((i, j), []).append(z)
    return nodes, lo, cols


def floor_at(cols, lo, p, z_hint, up, down):
    i, j = int((p[0] - lo[0]) // kc.R), int((p[1] - lo[1]) // kc.R)
    best = None
    for z in cols.get((i, j), ()):
        if z_hint - down <= z <= z_hint + up and (best is None or abs(z - z_hint) < abs(best - z_hint)):
            best = z
    return best


def walk(cols, lo, a, b):
    """Short links between raw BO3 node heights (nodes float a constant
    distance above their floor): small height change and a clear segment at
    chest height. The inflated voxels make body-height tests too strict."""
    d = np.linalg.norm(b[:2] - a[:2])
    dz = abs(b[2] - a[2])
    if d > SHORT or dz > max(40.0, 0.75 * d):
        return False
    steep = dz > 40.0   # stairs: BO3 keeps few nodes on them; require support
    steps = max(1, int(d // SAMPLE))
    for s in range(1, steps):
        p = a + (b - a) * (s / steps)
        i, j = int((p[0] - lo[0]) // kc.R), int((p[1] - lo[1]) // kc.R)
        if steep:
            k0, k1 = int((p[2] - 90 - lo[2]) // kc.R), int((p[2] - lo[2]) // kc.R)
            if not SOLID[i, j, max(k0, 0):max(k1, 0)].any():
                return False
        for h in (10.0, 30.0):
            kk = int((p[2] + h - lo[2]) // kc.R)
            if 0 <= kk < DIMS[2] and SOLID[i, j, kk]:
                return False
    return True


def build(E):
    raw, lo, cols = walkable_columns(E)
    nodes = []
    for n in raw:
        z = floor_at(cols, lo, n, n[2], 12, 72)
        nodes.append([float(n[0]), float(n[1]), float(z if z is not None else n[2] - 30)])
    P = np.array(raw, dtype=np.float64)
    edges = set()
    for i in range(len(P)):
        d = np.linalg.norm(P[:, :2] - P[i, :2], axis=1)
        for j in np.nonzero((d > 0) & (d < LINK))[0]:
            if j > i and (i, j) not in edges and walk(cols, lo, P[i], P[j]) and walk(cols, lo, P[j], P[i]):
                edges.add((i, int(j)))
    return nodes, sorted(edges)


def labels(n, edges):
    parent = list(range(n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in edges:
        parent[find(a)] = find(b)
    return [find(i) for i in range(n)]


def bridge(nodes, edges, reach=BRIDGE):
    """Join every smaller component to the main one through its closest node
    pair (window/ledge traversals BO3 links with negotiation nodes)."""
    P = np.array(nodes)
    edges = list(edges)
    bridges = []
    while True:
        lab = np.array(labels(len(P), edges))
        main = np.bincount(lab).argmax()
        inside = np.nonzero(lab == main)[0]
        best = None
        for c in set(lab.tolist()) - {main}:
            members = np.nonzero(lab == c)[0]
            d = np.linalg.norm(P[members][:, None, :] - P[inside][None, :, :], axis=2)
            k = np.unravel_index(d.argmin(), d.shape)
            if d[k] <= reach and (best is None or d[k] < best[0]):
                best = (d[k], int(members[k[0]]), int(inside[k[1]]))
        if best is None:
            return sorted(edges), bridges
        edges.append((min(best[1], best[2]), max(best[1], best[2])))
        bridges.append([best[1], best[2]])


def components(n, edges):
    parent = list(range(n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in edges:
        parent[find(a)] = find(b)
    sizes = {}
    for i in range(n):
        sizes[find(i)] = sizes.get(find(i), 0) + 1
    return sorted(sizes.values(), reverse=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--zone-dir", default="")
    a = ap.parse_args()
    kc.ZONE_DIR = a.zone_dir or None
    nodes, edges = build(a.export)
    edges, bridges = bridge(nodes, edges)
    comp = components(len(nodes), edges)
    json.dump({"schema": "kino.navgraph/1", "nodes": nodes, "edges": edges, "bridges": bridges}, open(a.out, "w"))
    print(json.dumps({"nodes": len(nodes), "edges": len(edges), "bridges": len(bridges), "components": comp[:8], "isolated": comp.count(1)}))


if __name__ == "__main__":
    main()

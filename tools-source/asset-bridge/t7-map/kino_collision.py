"""Approximate BO3 map collision with cloned IW7 stock collision brushmodels.

1. Voxelize player-blocking clip brushes, the clip triangle soup and (with
   --zone-dir) collidable static models of 32+ units, and flood-fill the space reachable from the BO3 pathnodes.
2. Sample exact walkable heights on a 16-unit grid from upward clip triangles
   and brush top planes; keep heights with 64 units of clearance in reachable
   space.
3. Group cells into sheets (4-neighbours within 20 units) and cover each sheet
   with plates fitted to its local plane (slopes and stairs become ramps).
4. Trace each sheet's boundary against blocked space into loops, simplify them
   and stand yaw-rotated plates/pillars along the segments.

Output kino.collision/3: donor targetname, origin and angles per piece in BO3
coordinates. Donor origins are bottom-face centers (measured on cp_zmb).
"""
import argparse, json, math
import numpy as np


R = 16.0
SIMPLIFY = 12.0
MIN_LOOP_EXTENT = 96.0
MIN_SEGMENT = 20.0
SHEET_STEP = 20.0
MIN_SHEET_CELLS = 12
PLANE_TOL = 7.0
ZONE_DIR = None  # BO3 zone directory: adds collidable static-model triangles
FLOOR_DONORS = (("playerai512x512x8", 256), ("playerai128x128x8", 128), ("player64x64x8", 64))
WALL_PLATES = (("playerai128x128x8", 128, 128), ("playerai512x512x8", 256, 256))


def brushes_and_tris(E):
    clip = json.load(open(E + "/clip.json"))
    v = np.frombuffer(open(E + "/clip_verts.f32", "rb").read(), dtype=np.float32).reshape(-1, 3).astype(np.float64)
    t = np.frombuffer(open(E + "/clip_tris.u32", "rb").read(), dtype=np.uint32).reshape(-1, 3)
    nodes = np.array([n["origin"] for n in json.load(open(E + "/pathnodes.json"))], dtype=np.float64)
    # Submodel (door, trap) brushes are stored in their entity's local space,
    # so they pile up around the map origin; drop any brush that fits inside a
    # door or other small submodel's local bounds. Doors are emitted separately.
    small = [m for m in clip["submodels"][1:] if max(np.subtract(m["maxs"], m["mins"])) < 400]
    subs = [(np.array(m["mins"]) - 1, np.array(m["maxs"]) + 1) for m in door_submodels(E, clip) + small]
    brushes = []
    dropped = {"local": 0, "submodel": 0, "holds_node": 0}
    for b in clip["brushes"]:
        if not b["contents"] & 0x10001:
            continue
        mn, mx = np.array(b["mins"]), np.array(b["maxs"])
        if any(np.all(mn >= smn) and np.all(mx <= smx) for smn, smx in subs):
            dropped["submodel"] += 1
            continue
        # Origin-centred boxes are submodel brushes in local space, not world.
        if np.all(np.abs(mn + mx) < 6) and np.min(mx - mn) > 32:
            dropped["local"] += 1
            continue
        # AI walks pathnodes, so a brush enclosing one at body height is not
        # player/AI blocking (volumes and other non-colliding solids).
        body = nodes + np.array([0.0, 0.0, 24.0])
        hit = np.all((body >= mn + 2) & (body <= mx - 2), axis=1)
        if hit.any() and all(brush_contains(b, q) for q in body[hit][:4]):
            dropped["holds_node"] += 1
            continue
        brushes.append(b)
    A, B, C = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    if ZONE_DIR:
        import kino_props_geom
        pa, pb, pc = kino_props_geom.prop_triangles(E, ZONE_DIR)
        A, B, C = np.concatenate([A, pa]), np.concatenate([B, pb]), np.concatenate([C, pc])
        dropped["prop_tris"] = len(pa)
    print("brushes", len(brushes), dropped)
    return brushes, A, B, C


def brush_contains(b, q):
    return all(s["plane"] is None or q[0] * s["plane"][0] + q[1] * s["plane"][1] + q[2] * s["plane"][2] <= s["plane"][3] - 2 for s in b["sides"])


def voxelize(brushes, A, B, C, lo, dims):
    solid = np.zeros(dims, dtype=bool)
    centers = [lo[k] + (np.arange(dims[k]) + 0.5) * R for k in range(3)]
    idx = lambda p: np.floor((np.asarray(p) - lo) / R).astype(int)
    for b in brushes:
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
    span = np.maximum(np.maximum(np.linalg.norm(B - A, axis=1), np.linalg.norm(C - A, axis=1)), np.linalg.norm(C - B, axis=1))
    prev = 0.0
    for steps in (2, 4, 8, 16, 32, 64, 128, 256, 512):
        lim = steps * R * 0.5
        sel = np.nonzero((span <= lim) & (span > prev))[0]
        prev = lim
        if not len(sel):
            continue
        uu, vv = np.meshgrid(np.linspace(0, 1, steps + 1), np.linspace(0, 1, steps + 1))
        m = (uu + vv) <= 1.0
        uu, vv = uu[m], vv[m]
        for chunk in np.array_split(sel, len(sel) // 20000 + 1):
            a_, b_, c_ = A[chunk], B[chunk], C[chunk]
            pts = a_[:, None, :] + (b_ - a_)[:, None, :] * uu[None, :, None] + (c_ - a_)[:, None, :] * vv[None, :, None]
            ii = idx(pts.reshape(-1, 3))
            ii = ii[np.all((ii >= 0) & (ii < dims), axis=1)]
            solid[ii[:, 0], ii[:, 1], ii[:, 2]] = True
    return solid


def surface_heights(brushes, A, B, C, lo, dims):
    """Exact candidate floor heights per grid column: list of z per (i, j)."""
    H = {}
    cx = lo[0] + (np.arange(dims[0]) + 0.5) * R
    cy = lo[1] + (np.arange(dims[1]) + 0.5) * R
    n = np.cross(B - A, C - A)
    nl = np.linalg.norm(n, axis=1)
    up = np.abs(n[:, 2]) > 0.5 * np.maximum(nl, 1e-9)
    for a, b, c in zip(A[up], B[up], C[up]):
        x0, x1 = min(a[0], b[0], c[0]), max(a[0], b[0], c[0])
        y0, y1 = min(a[1], b[1], c[1]), max(a[1], b[1], c[1])
        i0 = max(int((x0 - lo[0]) // R), 0); i1 = min(int((x1 - lo[0]) // R) + 1, dims[0])
        j0 = max(int((y0 - lo[1]) // R), 0); j1 = min(int((y1 - lo[1]) // R) + 1, dims[1])
        if i1 <= i0 or j1 <= j0:
            continue
        X, Y = np.meshgrid(cx[i0:i1], cy[j0:j1], indexing="ij")
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-9:
            continue
        w0 = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / d
        w1 = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / d
        w2 = 1 - w0 - w1
        ins = (w0 >= -0.01) & (w1 >= -0.01) & (w2 >= -0.01)
        Z = w0 * a[2] + w1 * b[2] + w2 * c[2]
        for i, j in np.argwhere(ins):
            H.setdefault((i0 + i, j0 + j), []).append(float(Z[i, j]))
    for bsh in brushes:
        tops = [s["plane"] for s in bsh["sides"] if s["plane"] and s["plane"][2] > 0.5]
        i0 = max(int((bsh["mins"][0] - lo[0]) // R), 0); i1 = min(int((bsh["maxs"][0] - lo[0]) // R) + 1, dims[0])
        j0 = max(int((bsh["mins"][1] - lo[1]) // R), 0); j1 = min(int((bsh["maxs"][1] - lo[1]) // R) + 1, dims[1])
        for i in range(i0, i1):
            for j in range(j0, j1):
                x, y = cx[i], cy[j]
                if not (bsh["mins"][0] <= x <= bsh["maxs"][0] and bsh["mins"][1] <= y <= bsh["maxs"][1]):
                    continue
                z = bsh["maxs"][2]
                for pl in tops:
                    z = min(z, (pl[3] - pl[0] * x - pl[1] * y) / pl[2])
                if z >= bsh["mins"][2]:
                    H.setdefault((i, j), []).append(float(z))
    return H


def door_entities(E):
    import re
    text = open(E + "/mapents.txt", encoding="utf-8", errors="replace").read()
    ents = [dict(re.findall(r'"([^"]+)" "([^"]*)"', blk)) for blk in re.findall(r"\{(.*?)\}", text, re.S)]
    names = {e["target"] for e in ents if e.get("targetname") == "zombie_door"}
    return [e for e in ents if e.get("targetname") in names and e.get("classname") == "script_brushmodel"
            and e.get("model", "").startswith("*")]


def door_submodels(E, clip):
    sub = {m["index"]: m for m in clip["submodels"]}
    return [sub[int(e["model"][1:])] for e in door_entities(E)]


def doors(E):
    """One standing plate per door brushmodel, tagged with the door name, at
    the entity origin plus the submodel's local bounds (closed position)."""
    clip = json.load(open(E + "/clip.json"))
    sub = {m["index"]: m for m in clip["submodels"]}
    out = []
    for e in door_entities(E):
        b = sub[int(e["model"][1:])]
        o = np.array([float(v) for v in e["origin"].split()])
        mn, mx = o + np.array(b["mins"]), o + np.array(b["maxs"])
        c, ext = (mn + mx) / 2, mx - mn
        thin = 0 if ext[0] < ext[1] else 1          # plate thickness along the thin axis
        yaw = 0.0 if thin == 0 else 90.0
        donor, size = ("playerai128x128x8", 128.0)
        base = c.copy(); base[thin] -= 4.0          # center the 8-unit thickness on the brush
        out.append({"donor": donor, "kind": "door", "door": e["targetname"],
                    "origin": [float(base[0]), float(base[1]), float(mx[2] - size / 2.0)], "angles": [90, yaw, 0]})
    return out


def rdp(points, eps):
    if len(points) < 3:
        return points
    a, b = np.array(points[0]), np.array(points[-1])
    d = b - a
    n = np.hypot(*d)
    best, k = 0.0, 0
    for i in range(1, len(points) - 1):
        p = np.array(points[i]) - a
        dist = abs(d[0] * p[1] - d[1] * p[0]) / n if n > 1e-9 else np.hypot(*p)
        if dist > best:
            best, k = dist, i
    if best > eps:
        return rdp(points[:k + 1], eps)[:-1] + rdp(points[k:], eps)
    return [points[0], points[-1]]


def plane_angles(nx, ny, nz):
    """Angles that tilt a horizontal plate onto the plane with unit normal n."""
    # IW7 angles (pitch, yaw, 0) map local +z to (sin p cos y, sin p sin y, cos p).
    pitch = math.degrees(math.atan2(math.hypot(nx, ny), nz))
    yaw = math.degrees(math.atan2(ny, nx))
    return [pitch, yaw, 0.0] if pitch > 0.5 else [0.0, 0.0, 0.0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--reach", type=float, default=260.0)
    ap.add_argument("--zone-dir", default="", help="BO3 zone directory (xpak) for static-model collision")
    ap.add_argument("--gameplay", default="", help="kino.gameplay/1 JSON: seed teleport-only rooms")
    a = ap.parse_args()
    global ZONE_DIR
    ZONE_DIR = a.zone_dir or None
    E = a.export
    nodes = np.array([n["origin"] for n in json.load(open(E + "/pathnodes.json"))], dtype=np.float64)
    if a.gameplay:
        # Teleport-only places (projection room, bonus rooms) have no path
        # nodes; seed walkable space there too.
        g = json.load(open(a.gameplay))
        extra = [it["origin"] for key in ("bonus_spots", "pack_a_punch") for it in g.get(key, [])]
        nodes = np.vstack([nodes, np.array(extra, dtype=np.float64) + np.array([0.0, 0.0, 30.0])])
    lo = nodes.min(0) - np.array([700, 700, 300]); hi = nodes.max(0) + np.array([700, 700, 900])
    dims = np.ceil((hi - lo) / R).astype(int)
    idx = lambda p: np.floor((np.asarray(p) - lo) / R).astype(int)
    brushes, A, B, C = brushes_and_tris(E)
    solid = voxelize(brushes, A, B, C, lo, dims)
    near = np.zeros(dims, dtype=bool)
    rr = int(math.ceil(a.reach / R))
    for n in nodes:
        c = idx(n)
        near[max(c[0] - rr, 0):c[0] + rr + 1, max(c[1] - rr, 0):c[1] + rr + 1, max(c[2] - 3, 0):c[2] + 10] = True
    from scipy import ndimage  # only the generator itself needs scipy
    lab, _ = ndimage.label(near & ~solid)
    seeds = set()
    for n in nodes:
        c = idx(n) + np.array([0, 0, 1])
        if np.all(c >= 0) and np.all(c < dims) and lab[tuple(c)]:
            seeds.add(lab[tuple(c)])
    reach = np.isin(lab, list(seeds))
    H = surface_heights(brushes, A, B, C, lo, dims)

    # Walkable samples: reachable just above, 64 units clear above, deduplicated.
    cells = {}
    for (i, j), zs in H.items():
        for z in sorted(set(round(z, 1) for z in zs)):
            k = int((z + 17 - lo[2]) // R)  # first voxel clear of the R/2 inflation
            if k < 0 or k + 4 >= dims[2] or not reach[i, j, k]:
                continue
            if solid[i, j, k + 1:k + 4].any():
                continue
            lst = cells.setdefault((i, j), [])
            if all(abs(z - q) > SHEET_STEP for q in lst):
                lst.append(z)
    # Sheets: union-find over (i, j, z) samples.
    keys = [(i, j, z) for (i, j), zs in cells.items() for z in zs]
    pos = {k: n for n, k in enumerate(keys)}
    parent = list(range(len(keys)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for (i, j, z), n in pos.items():
        for di, dj in ((1, 0), (0, 1)):
            for z2 in cells.get((i + di, j + dj), ()):
                if abs(z2 - z) <= SHEET_STEP:
                    ra, rb = find(n), find(pos[(i + di, j + dj, z2)])
                    if ra != rb:
                        parent[ra] = rb
    sheets = {}
    for k, n in pos.items():
        sheets.setdefault(find(n), []).append(k)
    pieces = []
    stats = {"sheets": 0, "small_sheets": 0}
    for members in sheets.values():
        if len(members) < MIN_SHEET_CELLS:
            stats["small_sheets"] += 1
            continue
        stats["sheets"] += 1
        hmap = {(i, j): z for i, j, z in members}
        cover_floor(pieces, hmap, lo, cells)
        trace_walls(pieces, hmap, lo, solid, dims)
    pieces += doors(E)
    kinds = {}
    for p in pieces:
        kinds[(p["kind"], p["donor"])] = kinds.get((p["kind"], p["donor"]), 0) + 1
    print("pieces", len(pieces), stats, kinds)
    json.dump({"schema": "kino.collision/3", "voxel": R, "pieces": pieces}, open(a.out, "w"))


def cover_floor(pieces, hmap, lo, cells):
    todo = set(hmap)
    for donor, size in FLOOR_DONORS:
        n = int(size // R)
        offs = sorted({0, n // 2, n - 1})
        for (i, j) in sorted(todo):
            if (i, j) not in todo:
                continue
            best = None
            for di in offs:
                for dj in offs:
                    i0, j0 = i - di, j - dj
                    foot = [(i0 + u, j0 + v) for u in range(n) for v in range(n)]
                    inside = [c for c in foot if c in hmap]
                    if len(inside) < 0.7 * len(foot) and donor != FLOOR_DONORS[-1][0]:
                        continue
                    if len(inside) < 0.3 * len(foot):
                        continue
                    P = np.array([[lo[0] + (c[0] + 0.5) * R, lo[1] + (c[1] + 0.5) * R, hmap[c]] for c in inside])
                    M = np.c_[P[:, 0], P[:, 1], np.ones(len(P))]
                    coef, *_ = np.linalg.lstsq(M, P[:, 2], rcond=None)
                    res = np.abs(M @ coef - P[:, 2]).max()
                    if res > PLANE_TOL:
                        continue
                    # An overhang must not become a low ceiling over another
                    # walkable level (stacked floors, stair landings).
                    ztop_c = coef[0] * (lo[0] + (i0 + n / 2) * R) + coef[1] * (lo[1] + (j0 + n / 2) * R) + coef[2]
                    if any(0 < ztop_c - z2 < 130 for c in foot if c not in hmap for z2 in cells.get(c, ())):
                        continue
                    gain = sum(1 for c in inside if c in todo)
                    if best is None or gain > best[0]:
                        best = (gain, i0, j0, coef)
            if best and (best[0] * 4 >= n * n or donor == FLOOR_DONORS[-1][0]):
                _, i0, j0, coef = best
                for u in range(n):
                    for v in range(n):
                        todo.discard((i0 + u, j0 + v))
                cxy = (lo[0] + (i0 + n / 2) * R, lo[1] + (j0 + n / 2) * R)
                ztop = coef[0] * cxy[0] + coef[1] * cxy[1] + coef[2]
                nrm = np.array([-coef[0], -coef[1], 1.0]); nrm /= np.linalg.norm(nrm)
                # Plate top through the fitted plane at the footprint center.
                origin = np.array([cxy[0], cxy[1], ztop]) - nrm * 8.0
                pieces.append({"donor": donor, "kind": "floor", "origin": [float(x) for x in origin],
                               "angles": plane_angles(*nrm)})
    # Uneven cells no plane fit accepted (seat rows, rubble): flat 64 plates at
    # the local top so no walkable cell is left without a floor.
    donor, size = FLOOR_DONORS[-1]
    for (i, j) in sorted(todo):
        if (i, j) not in todo:
            continue
        z0 = hmap[(i, j)]
        for u in range(-1, 3):
            for v in range(-1, 3):
                c = (i + u, j + v)
                if c in todo and abs(hmap[c] - z0) <= 12:
                    todo.discard(c)
        cxy = (lo[0] + (i + 1) * R, lo[1] + (j + 1) * R)
        pieces.append({"donor": donor, "kind": "floor", "origin": [cxy[0], cxy[1], z0 - 8.0], "angles": [0.0, 0.0, 0.0]})


def trace_walls(pieces, hmap, lo, solid, dims):
    nxt = {}
    edge_top = {}
    for (i, j), z in hmap.items():
        for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (i + dx, j + dy)
            if nb in hmap and abs(hmap[nb] - z) <= SHEET_STEP:
                continue
            ni, nj = nb
            if not (0 <= ni < dims[0] and 0 <= nj < dims[1]):
                continue
            k = int((z + 17 - lo[2]) // R)  # first voxel clear of the R/2 inflation
            if not solid[ni, nj, max(k + 1, 0):k + 6].any():
                continue  # open edge (ledge/drop): BO3 has no wall there either
            # Wall top: end of the neighbour's solid run, so a platform side
            # never rises through the walkable top of that platform.
            run = 0
            for kk in range(k, min(k + 16, dims[2])):
                if solid[ni, nj, kk]:
                    run = kk - k + 1
                elif run:
                    break
            if dx == 1:
                e = ((i + 1, j), (i + 1, j + 1))
            elif dx == -1:
                e = ((i, j + 1), (i, j))
            elif dy == 1:
                e = ((i + 1, j + 1), (i, j + 1))
            else:
                e = ((i, j), (i + 1, j))
            nxt.setdefault(e[0], []).append(e[1])
            edge_top[e[0]] = (z, lo[2] + (k + run) * R - 8.0)
    while nxt:
        start = next(iter(nxt))
        loop = [start]
        cur = start
        while cur in nxt:
            n2 = nxt[cur].pop()
            if not nxt[cur]:
                del nxt[cur]
            loop.append(n2)
            cur = n2
            if cur == start:
                break
        pts = [(lo[0] + px * R, lo[1] + py * R) for px, py in loop]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        if (max(xs) - min(xs)) + (max(ys) - min(ys)) < MIN_LOOP_EXTENT:
            continue
        where = {}
        for n, q in enumerate(pts):
            where.setdefault(q, n)
        simple = rdp(pts, SIMPLIFY)
        for k in range(len(simple) - 1):
            a0, a1 = np.array(simple[k]), np.array(simple[k + 1])
            d = a1 - a0
            L = float(np.hypot(*d))
            if L < MIN_SEGMENT:
                continue
            n0, n1 = where[tuple(simple[k])], where[tuple(simple[k + 1])]
            span = [edge_top[loop[n]] for n in range(n0, n1 if n1 > n0 else len(loop) - 1) if loop[n] in edge_top]
            if not span:
                continue
            floor_h = min(f for f, _ in span)
            # Players jump about 40 units: walls need not rise past floor + 96.
            top = min(max(t for _, t in span), floor_h + 96.0)
            place_wall(pieces, a0, a1, (d[1] / L, -d[0] / L), floor_h, top)


PILLARS = (("player64x64x64", 64), ("player64x64x128", 128), ("player64x64x256", 256))


def place_wall(pieces, a0, a1, nrm, floor_h, top):
    """Vertical pieces along a0-a1 from the floor to the obstacle top,
    thickness into the wall (right side), no overhang past the segment ends."""
    # Cell borders sit 0-16 units in front of the real surface (R/2 voxel
    # inflation); move the wall face 8 units into the obstacle.
    shift = np.array(nrm) * 8.0
    a0, a1 = a0 + shift, a1 + shift
    d = a1 - a0
    length = float(np.hypot(*d))
    u = d / length
    yaw = math.degrees(math.atan2(nrm[1], nrm[0]))
    need = max(top - (floor_h - 16), 32.0)
    plate = None
    for cand in WALL_PLATES:
        if length >= cand[1] * 0.75:
            plate = cand
            break
    if plate:
        donor, width, height = plate
    else:
        donor, height = next(((n, h) for n, h in PILLARS if h >= need), PILLARS[-1])
        width = 64
    count = max(1, int(math.ceil(length / width)))
    for k in range(count):
        c = min(k * width + width / 2.0, length - width / 2.0) if length >= width else length / 2.0
        p = a0 + u * c
        # One piece per column, ending at the obstacle top (it may reach below
        # the floor, never above the obstacle).
        if plate:
            # Pitch 90 stands the plate up: local +z (thickness) -> yaw, local x -> down.
            pieces.append({"donor": donor, "kind": "wall", "origin": [p[0], p[1], top - height / 2.0], "angles": [90, yaw, 0]})
        else:
            pieces.append({"donor": donor, "kind": "wall", "origin": [p[0] + nrm[0] * 32, p[1] + nrm[1] * 32, top - height], "angles": [0, yaw, 0]})


if __name__ == "__main__":
    main()

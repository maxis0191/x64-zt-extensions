"""Offline check of a kino.collision/3 piece set against the BO3 pathnodes.

For every node: a floor face must lie between 72 units below and 12 above it
(BO3 nodes float above the floor) and no piece may come within 10 units of the
body axis 18-66 units above that face. Donor sizes are the measured cp_zmb
clone extents; origins are bottom-face centers, as in the generator.
"""
import argparse, json, math
import numpy as np

SIZES = {
    "playerai512x512x8": (258, 258, 10), "playerai128x128x8": (128, 128, 8),
    "player64x64x8": (64, 64, 8), "player64x64x256": (64, 64, 256),
    "player64x64x128": (64, 64, 128), "player64x64x64": (64, 64, 64),
}


def frame(pitch, yaw):
    """IW7 forward/left/up for angles (pitch, yaw, 0)."""
    p, y = math.radians(pitch), math.radians(yaw)
    f = np.array([math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), -math.sin(p)])
    left = np.array([-math.sin(y), math.cos(y), 0.0])
    u = np.array([math.sin(p) * math.cos(y), math.sin(p) * math.sin(y), math.cos(p)])
    return f, left, u


def local(pieces):
    out = []
    for p in pieces:
        f, l, u = frame(*p["angles"][:2])
        out.append((np.array(p["origin"], dtype=float), f, l, u, SIZES[p["donor"]], p["kind"]))
    return out


def check(pieces, nodes):
    L = local(pieces)
    origins = np.array([o for o, *_ in L])
    unsupported, blocked = [], []
    for n in nodes:
        near = np.nonzero(np.linalg.norm(origins[:, :2] - n[:2], axis=1) < 200)[0]
        # BO3 pathnodes float 26-60 units above their floor: find the highest
        # floor face 72 below to 12 above the node (nodes can sit slightly under thin
        # floor faces), then test the body above that face.
        floor = None
        for k in near:
            o, f, l, u, (sx, sy, sz), kind = L[k]
            if kind != "floor" or u[2] < 0.5:
                continue
            top = o + u * sz
            t = np.dot(top - n, u) / u[2]
            q = n + np.array([0, 0, t]) - o
            if -72 <= t <= 12 and abs(q @ f) <= sx / 2 + 1 and abs(q @ l) <= sy / 2 + 1:
                floor = t if floor is None else max(floor, t)
        if floor is None:
            unsupported.append(n)
            continue
        base = n + np.array([0, 0, floor])
        hit = False
        for k in near:
            o, f, l, u, (sx, sy, sz), kind = L[k]
            for h in (18, 40, 66):
                q = base + np.array([0, 0, h]) - o
                dl = np.array([max(abs(q @ f) - sx / 2, 0), max(abs(q @ l) - sy / 2, 0), max(-(q @ u), (q @ u) - sz, 0)])
                if np.linalg.norm(dl) < 10:
                    hit = True
                    break
            if hit:
                break
        if hit:
            blocked.append(n)
    return unsupported, blocked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", required=True)
    ap.add_argument("--collision", required=True)
    a = ap.parse_args()
    nodes = np.array([n["origin"] for n in json.load(open(a.export + "/pathnodes.json"))], dtype=float)
    pieces = json.load(open(a.collision))["pieces"]
    un, bl = check(pieces, nodes)
    print(json.dumps({"nodes": len(nodes), "pieces": len(pieces), "unsupported": len(un), "blocked": len(bl),
                      "unsupported_sample": [[round(v) for v in n] for n in un[:8]],
                      "blocked_sample": [[round(v) for v in n] for n in bl[:8]]}))


if __name__ == "__main__":
    main()

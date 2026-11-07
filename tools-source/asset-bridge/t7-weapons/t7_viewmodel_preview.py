"""Render a first-person view model pose offline: hands + gun from one animation frame.

The in-game witness only shows a pose after a zone build and a client run,
and a wrong placement is easy to misread there (a DG-2 stock crossing the eye
looked like "the gun seen from close"). This draws the same pose without the
game, for either engine's rig, so a ported pose can be set beside the BO3
original under the same camera and field of view, and the renderer itself can
be checked against an in-game frame of a stock IW7 weapon.

Inputs: the hands skeleton (ZoneTool .xmb, as t7_vm_retarget reads it), mesh
exports (GrayWolf XMODEL_EXPORT) of the hands and the gun, an animation
(.xab), a frame. The hands mesh is skinned with its export's bone weights;
the gun is rigid on the attach bone (IW7 tag_weapon, BO3 tag_weapon_right).
The camera is tag_camera (x forward, y left, z up); cg_fov is horizontal at
4:3 and widens with the image (hor+), as IW7's is. Shading: albedo-free
Lambert from the camera, hands blue, gun orange, z-buffered, near plane 1.

    python t7_viewmodel_preview.py --skeleton <hands.xmb> --hands <hands XMODEL_EXPORT>
        --gun <gun XMODEL_EXPORT> --anim <anim.xab> [--frame 0] [--attach tag_weapon]
        [--fov 65] [--size 1280x720] --out <png>
"""
import argparse
import math
import os
import re
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "..", "animation")]
import iw7_xanim_codec as codec  # noqa: E402
import t7_vm_retarget as rig  # noqa: E402

NEAR = 1.0
FLOAT = r"(-?[\d.]+(?:e[-+]?\d+)?)"


def load_mesh(path):
    """Bones (name, bind position, bind axes rows), vertices with (bone, weight) lists, triangles."""
    text = open(path, encoding="utf-8", errors="replace").read()
    names = {int(i): n for i, n in re.findall(r'BONE (\d+) -?\d+ "([^"]+)"', text)}
    binds = {}
    for m in re.finditer(r"BONE (\d+)\nOFFSET %s, %s, %s\nSCALE [^\n]*\nX %s, %s, %s\nY %s, %s, %s\nZ %s, %s, %s"
                         % ((FLOAT,) * 12), text):
        v = [float(x) for x in m.groups()[1:]]
        binds[int(m.group(1))] = (np.array(v[0:3]), np.array([v[3:6], v[6:9], v[9:12]]))
    verts, weights = [], []
    for m in re.finditer(r"VERT \d+\nOFFSET %s, %s, %s\nBONES (\d+)\n((?:BONE \d+ [-\d.e]+\n?)+)" % ((FLOAT,) * 3), text):
        verts.append([float(m.group(i)) for i in (1, 2, 3)])
        weights.append([(int(b), float(w)) for b, w in re.findall(r"BONE (\d+) ([-\d.e]+)", m.group(5))])
    tris = [tuple(int(x) for x in t) for t in
            re.findall(r"TRI [^\n]*\nVERT (\d+)\n(?:[^\n]*\n){3}VERT (\d+)\n(?:[^\n]*\n){3}VERT (\d+)", text)]
    return {"names": names, "binds": binds, "verts": np.array(verts), "weights": weights, "tris": np.array(tris)}


def quat_matrix(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def skin(mesh, pose):
    """World positions of the mesh's vertices for pose: {bone name: (3x3 rotation, position)}."""
    out = np.zeros_like(mesh["verts"])
    for i, (v, ws) in enumerate(zip(mesh["verts"], mesh["weights"])):
        acc = np.zeros(3)
        total = 0.0
        for b, w in ws:
            name = mesh["names"].get(b)
            if name not in pose or b not in mesh["binds"]:
                continue
            bpos, baxes = mesh["binds"][b]
            local = baxes @ (v - bpos)              # rows are the bone's axes in bind space
            prot, ppos = pose[name]
            acc += w * (ppos + prot @ local)
            total += w
        out[i] = acc / total if total else v
    return out


def rigid(mesh, rotation, position):
    return mesh["verts"] @ rotation.T + position


def raster(images, zbuf, pts, tris, color, cam_rot, cam_pos, focal, size):
    w, h = size
    cam = (pts - cam_pos) @ cam_rot              # columns of cam_rot: forward, left, up
    x, y, z = cam[:, 0], cam[:, 1], cam[:, 2]
    with np.errstate(divide="ignore", invalid="ignore"):
        sx = w / 2 - y / x * focal
        sy = h / 2 - z / x * focal
    for a, b, c in tris:
        if x[a] < NEAR or x[b] < NEAR or x[c] < NEAR:
            continue
        p = np.array([[sx[a], sy[a]], [sx[b], sy[b]], [sx[c], sy[c]]])
        x0, y0 = np.floor(p.min(0)).astype(int)
        x1, y1 = np.ceil(p.max(0)).astype(int)
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, w - 1), min(y1, h - 1)
        if x0 > x1 or y0 > y1:
            continue
        n = np.cross(cam[b] - cam[a], cam[c] - cam[a])
        norm = np.linalg.norm(n)
        if norm == 0:
            continue
        shade = 0.25 + 0.75 * abs(n[0]) / norm
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        d = (p[1, 1] - p[2, 1]) * (p[0, 0] - p[2, 0]) + (p[2, 0] - p[1, 0]) * (p[0, 1] - p[2, 1])
        if abs(d) < 1e-9:
            continue
        l0 = ((p[1, 1] - p[2, 1]) * (gx - p[2, 0]) + (p[2, 0] - p[1, 0]) * (gy - p[2, 1])) / d
        l1 = ((p[2, 1] - p[0, 1]) * (gx - p[2, 0]) + (p[0, 0] - p[2, 0]) * (gy - p[2, 1])) / d
        l2 = 1 - l0 - l1
        inside = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
        if not inside.any():
            continue
        depth = 1.0 / (l0 / x[a] + l1 / x[b] + l2 / x[c])
        region = zbuf[y0:y1 + 1, x0:x1 + 1]
        closer = inside & (depth < region)
        region[closer] = depth[closer]
        images[y0:y1 + 1, x0:x1 + 1][closer] = np.array(color) * shade


def pose_of(skeleton, anim, frame):
    world = skeleton.pose(anim.rotations, anim.translations, frame) if anim else skeleton.world
    return {n: (quat_matrix(world[i][0]), np.array(world[i][1])) for n, i in skeleton.index.items()}


def render(skeleton, hands, gun, anim, frame, attach, fov, size, offset=(0.0, 0.0, 0.0)):
    pose = pose_of(skeleton, anim, frame)
    cam_rot, cam_pos = pose["tag_camera"]
    # preview a rigid camera-space shift of the whole view model (forward, left, up)
    shift = cam_rot @ np.array(offset, dtype=float)
    pose = {n: (r, p + shift) if n != "tag_camera" else (r, p) for n, (r, p) in pose.items()}
    w, h = size
    # cg_fov is the horizontal field of view of a 4:3 view, widened for wider images (hor+)
    half = math.atan(math.tan(math.radians(fov) / 2) * (w / h) / (4 / 3))
    focal = (w / 2) / math.tan(half)
    image = np.zeros((h, w, 3))
    zbuf = np.full((h, w), np.inf)
    if hands is not None:
        raster(image, zbuf, skin(hands, pose), hands["tris"], (0.35, 0.55, 0.95), cam_rot, cam_pos, focal, size)
    if gun is not None and attach in pose:
        rot, pos = pose[attach]
        raster(image, zbuf, rigid(gun, rot, pos), gun["tris"], (1.0, 0.6, 0.2), cam_rot, cam_pos, focal, size)
    return (np.clip(image, 0, 1) * 255).astype(np.uint8)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--skeleton", required=True)
    ap.add_argument("--hands")
    ap.add_argument("--gun")
    ap.add_argument("--anim")
    ap.add_argument("--frame", type=int, default=0)
    ap.add_argument("--attach", default="tag_weapon")
    ap.add_argument("--fov", type=float, default=65.0)
    ap.add_argument("--size", default="1280x720")
    ap.add_argument("--offset", default="0,0,0", help="camera-space shift of the view model: forward,left,up")
    ap.add_argument("--overlay", help="in-game frame to blend under the render (same size): checks the camera")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    size = tuple(int(x) for x in args.size.split("x"))
    skeleton = rig.Skeleton(args.skeleton)
    anim = codec.decode(args.anim) if args.anim else None
    hands = load_mesh(args.hands) if args.hands else None
    gun = load_mesh(args.gun) if args.gun else None
    image = render(skeleton, hands, gun, anim, args.frame, args.attach, args.fov, size,
                   tuple(float(v) for v in args.offset.split(",")))
    if args.overlay:
        frame = np.asarray(Image.open(args.overlay).convert("RGB").resize(size)).astype(np.float32)
        drawn = image.any(axis=2, keepdims=True)
        image = np.where(drawn, 0.5 * frame + 0.5 * image, frame).astype(np.uint8)
    Image.fromarray(image).save(args.out)
    print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Retarget converted BO3 viewmodel animations onto the IW7 view hands (stdlib only).

BO3 view hands have no clavicle (tag_torso -> j_shoulder_*), IW7's do
(tag_torso -> j_clavicle_* -> j_shoulder_*), and IW7 carries the gun on
tag_weapon, which its animations keep equal to tag_weapon_right; BO3 leaves
tag_weapon unanimated. Played directly, a BO3 animation puts IW7 arm bones
under the wrong parents and the gun at the view origin.

For every frame this evaluates the BO3 pose on the BO3 hands, aligns the BO3
camera (tag_camera) with the IW7 one, then poses the IW7 hands:
* each arm by two-bone IK: the IW7 wrist lands on the BO3 wrist, the elbow
  bends toward the BO3 elbow; IW7 bone lengths are kept;
* hands and fingers take the BO3 world orientation relative to each rig's
  bind pose;
* tag_weapon follows the BO3 tag_weapon_right (gun root), so the gun keeps
  its BO3 placement relative to the camera;
* channels of bones only the gun has (tag_*_animate...) are copied.

    python t7_vm_retarget.py --source-hands <bo3 hands.xmb> --target-hands <iw7 hands.xmb>
        --out <dir> <anim.xab> [...]

Writes <out>/<anim>.xab (same name) and prints a JSON report per animation
with the largest wrist/elbow placement error. Models are ZoneTool IW7 dumps
(.xmb); the BO3 hands come from the T7 -> IW7 converter.
"""
import argparse
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'animation'))
import iw7_xanim_codec as codec  # noqa: E402
import xab_preflight as xab  # noqa: E402

ARMS = (('le', 'j_shoulder_le', 'j_elbow_le', 'j_wrist_le'), ('ri', 'j_shoulder_ri', 'j_elbow_ri', 'j_wrist_ri'))


# --- quaternion helpers (x, y, z, w) ---
def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def qinv(q):
    return (-q[0], -q[1], -q[2], q[3])


def qnorm(q):
    length = math.sqrt(sum(c * c for c in q)) or 1.0
    return tuple(c / length for c in q)


def qrot(q, v):
    return qmul(qmul(q, (v[0], v[1], v[2], 0.0)), qinv(q))[:3]


def vsub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def vadd(a, b):
    return tuple(x + y for x, y in zip(a, b))


def vscale(a, s):
    return tuple(x * s for x in a)


def vdot(a, b):
    return sum(x * y for x, y in zip(a, b))


def vlen(a):
    return math.sqrt(vdot(a, a))


def vnorm(a):
    length = vlen(a) or 1.0
    return vscale(a, 1.0 / length)


def vcross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def q_between(u, v):
    """Shortest rotation taking direction u onto direction v."""
    u, v = vnorm(u), vnorm(v)
    d = vdot(u, v)
    if d < -0.999999:
        axis = vcross((1.0, 0.0, 0.0), u)
        if vlen(axis) < 1e-6:
            axis = vcross((0.0, 1.0, 0.0), u)
        axis = vnorm(axis)
        return (axis[0], axis[1], axis[2], 0.0)
    c = vcross(u, v)
    return qnorm((c[0], c[1], c[2], 1.0 + d))


# --- models ---
class Skeleton:
    def __init__(self, path):
        data = open(path, 'rb').read()
        name = os.path.basename(path)[:-4].encode()
        start = data.index(b'\x06\x01' + name + b'\0')
        reader = xab.Reader(data)
        blob = reader.array(1, start - 6)
        bones, roots = blob[20], blob[21]
        client = struct.unpack_from('<H', blob, 24)[0]
        reader.string()
        self.names = [reader.string() for _ in range(bones + client)]
        count = bones + client - roots
        parents = list(reader.array(count, 1))
        reader.array(count, 8)
        reader.array(count, 12)
        reader.array(bones, 1)
        mats = reader.array(bones + client, 32)
        self.world = [(qnorm(struct.unpack_from('<4f', mats, i * 32)), struct.unpack_from('<3f', mats, i * 32 + 16))
                      for i in range(bones + client)]
        self.parent = [None] * len(self.names)
        for i in range(roots, len(self.names)):
            self.parent[i] = i - parents[i - roots]
        self.index = {n: i for i, n in enumerate(self.names)}
        self.local = []
        for i in range(len(self.names)):
            q, t = self.world[i]
            p = self.parent[i]
            if p is None:
                self.local.append((q, t))
            else:
                pq, pt = self.world[p]
                self.local.append((qmul(qinv(pq), q), qrot(qinv(pq), vsub(t, pt))))

    def pose(self, rotations, translations, frame):
        """World transforms with an animation frame applied over the bind pose."""
        out = [None] * len(self.names)
        for i, name in enumerate(self.names):
            lq, lt = self.local[i]
            keys = rotations.get(name)
            if keys is not None:
                lq = codec.sample(keys, frame, True)
            keys = translations.get(name)
            if keys is not None:
                lt = codec.sample(keys, frame, False)
            p = self.parent[i]
            if p is None:
                out[i] = (lq, lt)
            else:
                pq, pt = out[p]
                out[i] = (qnorm(qmul(pq, lq)), vadd(pt, qrot(pq, lt)))
        return out


def two_bone(shoulder, a, b, target, pole):
    """Elbow position for upper length a and lower length b reaching target."""
    axis = vsub(target, shoulder)
    d = max(abs(a - b) + 1e-4, min(a + b - 1e-4, vlen(axis)))
    u = vnorm(axis)
    side = vsub(vsub(pole, shoulder), vscale(u, vdot(vsub(pole, shoulder), u)))
    if vlen(side) < 1e-6:
        side = vcross(u, (0.0, 0.0, 1.0))
    v = vnorm(side)
    cos_a = max(-1.0, min(1.0, (a * a + d * d - b * b) / (2 * a * d)))
    sin_a = math.sqrt(max(0.0, 1.0 - cos_a * cos_a))
    return vadd(shoulder, vadd(vscale(u, a * cos_a), vscale(v, a * sin_a)))


def retarget(anim, src, dst):
    out = codec.Animation()
    out.__dict__.update({k: getattr(anim, k) for k in ('name', 'frames', 'rate', 'frequency', 'flags', 'header', 'tail', 'notify', 'notify_count')})
    frames = range(anim.frames + 1)
    rot_keys = {}
    trans_keys = {}
    report = {'frames': anim.frames, 'wrist_error_max': 0.0}
    bind_src = {n: src.world[i] for n, i in src.index.items()}
    bind_dst = {n: dst.world[i] for n, i in dst.index.items()}
    mapped = [n for n in dst.names if n in src.index and (n.startswith('j_') and not n.startswith('j_clavicle'))]
    gun_only = [n for n in anim.rotations if n not in dst.index and n not in src.index]
    cam_src = src.index.get('tag_camera', 0)
    cam_dst = dst.index['tag_camera']
    for f in frames:
        sp = src.pose(anim.rotations, anim.translations, f)
        offset = vsub(dst.world[cam_dst][1], sp[cam_src][1])
        want = {}
        for n in mapped:
            q, t = sp[src.index[n]]
            # BO3 world orientation, expressed relative to each rig's bind pose.
            want[n] = (qnorm(qmul(qmul(q, qinv(bind_src[n][0])), bind_dst[n][0])), vadd(t, offset))
        world = {}
        local = {}
        for i, n in enumerate(dst.names):
            lq, lt = dst.local[i]
            p = dst.parent[i]
            pq, pt = world[dst.names[p]] if p is not None else ((0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0))
            if n in want:
                lq = qnorm(qmul(qinv(pq), want[n][0]))
            wq = qnorm(qmul(pq, lq))
            wt = vadd(pt, qrot(pq, lt))
            world[n] = (wq, wt)
            local[n] = lq
        # Two-bone IK per arm toward the BO3 wrist, elbow toward the BO3 elbow.
        for _, s, e, w in ARMS:
            if not all(x in dst.index and x in src.index for x in (s, e, w)):
                continue
            S = world[s][1]
            a = vlen(dst.local[dst.index[e]][1])
            b = vlen(dst.local[dst.index[w]][1])
            target = want[w][1]
            elbow = two_bone(S, a, b, target, want[e][1])
            # Shoulder: rotate so the elbow lands on the solved point.
            sq = world[s][0]
            fix = q_between(qrot(sq, dst.local[dst.index[e]][1]), vsub(elbow, S))
            sq = qnorm(qmul(fix, sq))
            parent_s = dst.parent[dst.index[s]]
            local[s] = qnorm(qmul(qinv(world[dst.names[parent_s]][0]), sq))
            eq = qnorm(qmul(sq, local[e]))
            fix = q_between(qrot(eq, dst.local[dst.index[w]][1]), vsub(target, elbow))
            eq = qnorm(qmul(fix, eq))
            local[e] = qnorm(qmul(qinv(sq), eq))
            local[w] = qnorm(qmul(qinv(eq), want[w][0]))
            reached = vadd(elbow, qrot(eq, dst.local[dst.index[w]][1]))
            report['wrist_error_max'] = max(report['wrist_error_max'], vlen(vsub(reached, target)))
        # Recompute world for tag_weapon's parent chain after IK.
        world2 = {}
        for i, n in enumerate(dst.names):
            p = dst.parent[i]
            pq, pt = world2[dst.names[p]] if p is not None else ((0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0))
            world2[n] = (qnorm(qmul(pq, local[n])), vadd(pt, qrot(pq, dst.local[i][1])))
        if 'tag_weapon' in dst.index and 'tag_weapon_right' in src.index:
            gq, gt = sp[src.index['tag_weapon_right']]
            gt = vadd(gt, offset)
            parent = dst.names[dst.parent[dst.index['tag_weapon']]]
            pq, pt = world2[parent]
            rot_keys.setdefault('tag_weapon', []).append((f, qnorm(qmul(qinv(pq), gq))))
            trans_keys.setdefault('tag_weapon', []).append((f, qrot(qinv(pq), vsub(gt, pt))))
        for n in dict.fromkeys(mapped + [x for _, *chain in ARMS for x in chain]):
            if n in local:
                rot_keys.setdefault(n, []).append((f, local[n]))
    # Every hand bone is listed, as stock view animations do: the client showed
    # bones left out of the animation collapsed onto the view origin. Bones
    # that do not move get static channels with their bind values.
    for i, n in enumerate(dst.names):
        if dst.parent[i] is None:
            continue
        bind_q, bind_t = dst.local[i]
        out.rotations[n] = rot_keys.get(n) or [(0, bind_q)]
        out.translations[n] = trans_keys.get(n) or [(0, bind_t)]
    for n in gun_only:
        out.rotations[n] = anim.rotations[n]
        out.translations[n] = anim.translations.get(n)
    # Gun bones the hands do not have keep their own channels.
    for n in list(anim.translations):
        if n not in out.translations and n not in dst.index and not n.startswith('#'):
            out.translations[n] = anim.translations[n]
            out.rotations.setdefault(n, anim.rotations.get(n))
    report['channels'] = sum(1 for k in out.rotations.values() if k is not None)
    report['wrist_error_max'] = round(report['wrist_error_max'], 3)
    return out, report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument('--source-hands', required=True)
    ap.add_argument('--target-hands', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('anims', nargs='+')
    args = ap.parse_args(argv)
    src = Skeleton(args.source_hands)
    dst = Skeleton(args.target_hands)
    os.makedirs(args.out, exist_ok=True)
    for path in args.anims:
        anim = codec.decode(path)
        out, report = retarget(anim, src, dst)
        target = os.path.join(args.out, os.path.basename(path))
        codec.encode(out, target)
        report['name'] = anim.name
        report['bytes'] = os.path.getsize(target)
        print(json.dumps(report))
    return 0


if __name__ == '__main__':
    sys.exit(main())

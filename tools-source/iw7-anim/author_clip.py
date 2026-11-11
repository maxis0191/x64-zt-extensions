"""Author a simple animation on a game skeleton, outside the game, as glTF (stdlib only).

    python author_clip.py <xmodel|skeleton.json> --out wave.glb --seconds 2
        --rotate j_shoulder_ri:0,-70,0 --rotate j_spine4:0,0,40 [--move 96,0,0] [--note hit:1.0] [--loop]

Each --rotate turns one bone from its bind pose by the given degrees about its own x, y and z axes, easing in
and out over the clip; --move slides the whole character (root motion) by that many game units. The result is
an ordinary glTF animation: `iw7_anim_gltf.py from-gltf` turns it into a game animation. It exists to prove
the path and to make test clips; real animation is keyed in a DCC tool on the `skeleton` glb.
"""
import argparse
import json
import math
import sys

import iw7_anim_gltf as T


def euler(deg):
    q = T.IDENT
    for axis, angle in zip(((1, 0, 0), (0, 1, 0), (0, 0, 1)), deg):
        h = math.radians(angle) / 2
        q = T.q_mul(q, (axis[0] * math.sin(h), axis[1] * math.sin(h), axis[2] * math.sin(h), math.cos(h)))
    return q


def ease(u, there_and_back):
    if there_and_back:
        u = 1 - abs(2 * u - 1)
    return u * u * (3 - 2 * u)


def build(skel, name, seconds, rate, rotations, move=None, notes=(), loop=False, there_and_back=False):
    clip = T.Clip()
    clip.name, clip.rate, clip.loop = name, rate, loop
    clip.frames = int(round(seconds * rate))
    for bone, deg in rotations:
        i = skel.index[bone]
        clip.bones.append(bone)
        clip.rot[bone] = [T.q_norm(T.q_mul(skel.q[i], euler([a * ease(f / clip.frames, there_and_back) for a in deg])))
                          for f in range(clip.frames + 1)]
        clip.trans[bone] = None
    if move:
        clip.delta_t = [tuple(c * f / clip.frames for c in move) for f in range(clip.frames + 1)]
    clip.notes = [(n, s / seconds) for n, s in notes]
    return clip


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('model')
    ap.add_argument('--out', required=True)
    ap.add_argument('--name', default='authored_clip')
    ap.add_argument('--seconds', type=float, default=2.0)
    ap.add_argument('--fps', type=float, default=30.0)
    ap.add_argument('--rotate', action='append', default=[], help='BONE:x,y,z degrees about the bone\'s own axes')
    ap.add_argument('--move', help='x,y,z game units of root motion over the clip')
    ap.add_argument('--note', action='append', default=[], help='NAME:SECONDS')
    ap.add_argument('--loop', action='store_true')
    ap.add_argument('--there-and-back', action='store_true', help='return to the bind pose at the end')
    a = ap.parse_args(argv)
    skel = T.Skeleton.load(a.model)
    rotations = []
    for text in a.rotate:
        bone, _, deg = text.partition(':')
        if bone not in skel.index:
            print(json.dumps({'error': 'not in the model: ' + bone}))
            return 2
        rotations.append((bone, [float(c) for c in deg.split(',')]))
    notes = [(t.rpartition(':')[0], float(t.rpartition(':')[2])) for t in a.note]
    move = [float(c) for c in a.move.split(',')] if a.move else None
    clip = build(skel, a.name, a.seconds, a.fps, rotations, move, notes, a.loop, a.there_and_back)
    print(json.dumps(T.write_gltf(a.out, skel, clip)))
    return 0


if __name__ == '__main__':
    sys.exit(main())

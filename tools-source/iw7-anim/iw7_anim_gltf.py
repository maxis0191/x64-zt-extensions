"""glTF <-> IW7 animation for full-body characters (stdlib only).

    python iw7_anim_gltf.py skeleton <xmodel|skeleton.json> --out rig.glb
    python iw7_anim_gltf.py to-gltf <xanim> --model <xmodel> --out clip.glb
    python iw7_anim_gltf.py from-gltf clip.glb --skeleton <xmodel> --name my_clip --out <dump folder>
    python iw7_anim_gltf.py compare <a> <b> [--model <xmodel>]
    python iw7_anim_gltf.py inspect <xanim>
    python iw7_anim_gltf.py sample <xanim|glb> --model <xmodel> --bones j_head,j_wrist_ri
    python iw7_anim_gltf.py zone-source <dump folder> --zone mod --out <work tree>
    python iw7_anim_gltf.py compare-run <run>/anim-<name>.json clip.glb --model <xmodel>

Mapping (docs/ANIM-GLTF.md has the reasons):
  * the game stores, per bone, the rotation relative to the parent bone and the translation as an
    offset from the model's bind translation; glTF gets the plain local rotation and translation
    (bind + offset); a bone the animation does not list stays in the model's bind pose;
  * game (x forward, y left, z up, inches) -> glTF (x, z, -y), metres (scale 0.0254, --scale);
    Blender's importer turns this back into the game's axes;
  * one key per game frame (30 per second unless the animation says otherwise), linear;
  * the root delta (root motion) is the node `iw7_root_motion`, parent of the skeleton;
  * notetracks, the loop flag and the header bytes travel in animations[0].extras.iw7.
"""
import argparse
import base64
import bisect
import json
import math
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'asset-bridge', 't7-weapons'))
sys.path.insert(0, os.path.join(HERE, '..', 'iw7-skinned-writer'))
import iw7_xanim_codec as codec  # noqa: E402

ROOT_MOTION = 'iw7_root_motion'
INCH = 0.0254
PTR = 0xFDFDFDFDFDFDFDFD
ANIM_LOOP, ANIM_DELTA, ANIM_DELTA_3D = 1, 2, 4
IDENT = (0.0, 0.0, 0.0, 1.0)


class Problem(ValueError):
    pass


# ------------------------------------------------------------------ math
def q_mul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def q_conj(q):
    return (-q[0], -q[1], -q[2], q[3])


def q_norm(q):
    n = math.sqrt(q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3]) or 1.0
    return (q[0] / n, q[1] / n, q[2] / n, q[3] / n)


def q_rot(q, v):
    x, y, z, w = q
    vx, vy, vz = v
    tx, ty, tz = 2 * (y * vz - z * vy), 2 * (z * vx - x * vz), 2 * (x * vy - y * vx)
    return (vx + w * tx + (y * tz - z * ty), vy + w * ty + (z * tx - x * tz), vz + w * tz + (x * ty - y * tx))


def q_dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3]


def q_angle(a, b):
    """Angle in degrees between two rotations."""
    return math.degrees(2.0 * math.acos(min(1.0, abs(q_dot(a, b)))))


def q_nlerp(a, b, t):
    if q_dot(a, b) < 0:
        b = (-b[0], -b[1], -b[2], -b[3])
    return q_norm(tuple(x + (y - x) * t for x, y in zip(a, b)))


def q_slerp(a, b, t):
    d = q_dot(a, b)
    if d < 0:
        b, d = (-b[0], -b[1], -b[2], -b[3]), -d
    if d > 0.9995:
        return q_norm(tuple(x + (y - x) * t for x, y in zip(a, b)))
    th = math.acos(d)
    sa, sb = math.sin((1 - t) * th) / math.sin(th), math.sin(t * th) / math.sin(th)
    return tuple(x * sa + y * sb for x, y in zip(a, b))


def v_add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def v_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def v_len(a):
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def to_gltf_v(v, scale=1.0):
    return (v[0] * scale, v[2] * scale, -v[1] * scale)


def to_game_v(v, scale=1.0):
    return (v[0] * scale, -v[2] * scale, v[1] * scale)


def to_gltf_q(q):
    return (q[0], q[2], -q[1], q[3])


def to_game_q(q):
    return (q[0], -q[2], q[1], q[3])


def percentile(values, p):
    if not values:
        return 0.0
    s = sorted(values)
    return s[min(len(s) - 1, int(math.ceil(p / 100.0 * len(s))) - 1)]


# ------------------------------------------------------------------ skeleton
class Skeleton:
    """Bones in model order: names, parent index (-1 for a root), local bind rotation and translation
    (a root's local transform is its model-space bind)."""

    def __init__(self, name, names, parents, quats, trans):
        self.name, self.names, self.parents = name, list(names), list(parents)
        self.q = [q_norm(tuple(q)) for q in quats]
        self.t = [tuple(t) for t in trans]
        self.index = {n: i for i, n in enumerate(self.names)}
        if len(self.index) != len(self.names):
            raise Problem('duplicate bone names in the skeleton')
        for i, p in enumerate(self.parents):
            if not -1 <= p < i:
                raise Problem('bone %s: the parent must be an earlier bone' % self.names[i])

    @classmethod
    def load(cls, path):
        if path.lower().endswith('.json'):
            with open(path) as f:
                doc = json.load(f)
            bones = doc['bones']
            names = [b['name'] for b in bones]
            parents = [-1 if b.get('parent') is None else names.index(b['parent']) for b in bones]
            return cls(doc.get('name', os.path.splitext(os.path.basename(path))[0]), names, parents,
                       [b.get('q', IDENT) for b in bones], [b.get('t', (0, 0, 0)) for b in bones])
        import xmodel as xmodel_io
        with open(path, 'rb') as f:
            m = xmodel_io.read(f.read())
        roots = m.get('numRootBones')
        quats, trans, parents = [], [], []
        for i in range(m.n_bones):
            parents.append(m.parent_index(i))
            if i < roots:
                b = m.base_mat[i]
                quats.append(b[0:4])
                trans.append(b[4:7])
            else:
                quats.append(m.local_quat(i))
                trans.append(m.tag_positions[i - roots])
        return cls(m.name, m.bone_names, parents, quats, trans)

    def globals(self, lq=None, lt=None):
        """Model-space (rotation, translation) of every bone from local transforms."""
        lq, lt = lq or self.q, lt or self.t
        gq, gt = [], []
        for i, p in enumerate(self.parents):
            if p < 0:
                gq.append(lq[i])
                gt.append(lt[i])
            else:
                gq.append(q_mul(gq[p], lq[i]))
                gt.append(v_add(gt[p], q_rot(gq[p], lt[i])))
        return gq, gt


# ------------------------------------------------------------------ the root delta
def _records(tail):
    out, p = [], 0
    while p < len(tail):
        kind, present = tail[p], tail[p + 1]
        if kind not in (8, 10) or present != 1:
            raise Problem('unexpected record after the notetracks')
        n = struct.unpack_from('<I', tail, p + 2)[0]
        size = n * 24 if kind == 8 else n
        out.append(tail[p + 6:p + 6 + size])
        p += 6 + size
    return out


def decode_delta(anim):
    """-> None or {'trans': keys|None, 'quat': keys|None, 'three_d': bool}; keys = [(frame, value)]."""
    if not anim.tail:
        return None
    recs = _records(anim.tail)
    ptrs = struct.unpack('<3Q', recs[0])
    wide = anim.frames >= 256
    k = 1
    out = {'trans': None, 'quat': None, 'three_d': False}

    def indices(raw, offset, n):
        return list(struct.unpack_from('<%d%s' % (n + 1, 'H' if wide else 'B'), raw, offset))

    if ptrs[0]:
        raw = recs[k]
        k += 1
        n, small = struct.unpack_from('<HB', raw, 0)
        if not n:
            out['trans'] = [(0, struct.unpack_from('<3f', raw, 8))]
        else:
            mins, step = struct.unpack_from('<3f', raw, 8), struct.unpack_from('<3f', raw, 20)
            frames = recs[k]
            k += 1
            keys = []
            for j, f in enumerate(indices(raw, 40, n)):
                v = frames[j * 3:j * 3 + 3] if small else struct.unpack_from('<3H', frames, j * 6)
                keys.append((f, tuple(mins[i] + step[i] * v[i] for i in range(3))))
            out['trans'] = keys
    for slot, width in ((1, 2), (2, 4)):
        if not ptrs[slot]:
            continue
        raw = recs[k]
        k += 1
        n = struct.unpack_from('<H', raw, 0)[0]

        def quat(values):
            v = (0, 0) + tuple(values) if width == 2 else tuple(values)
            return q_norm(tuple(c / 32767.0 for c in v))

        if not n:
            keys = [(0, quat(struct.unpack_from('<%dh' % width, raw, 8)))]
        else:
            frames = recs[k]
            k += 1
            keys = [(f, quat(struct.unpack_from('<%dh' % width, frames, j * width * 2)))
                    for j, f in enumerate(indices(raw, 16, n))]
        out['quat'] = keys
        out['three_d'] = width == 4
    if k != len(recs):
        raise Problem('root delta records not fully read')
    return out


def _array1(payload):
    return bytes([8, 1]) + struct.pack('<I', 1) + payload


def _raw(payload):
    return bytes([10, 1]) + struct.pack('<I', len(payload)) + payload


def encode_delta(frames, trans, quats, three_d):
    """Root delta records: one key per frame (or a single static value). trans/quats are per-frame lists or None."""
    wide = frames >= 256
    idx = struct.pack('<%d%s' % (frames + 1, 'H' if wide else 'B'), *range(frames + 1))
    out = [_array1(struct.pack('<3Q', PTR if trans else 0, PTR if quats and not three_d else 0,
                               PTR if quats and three_d else 0))]
    if trans:
        if frames == 0 or all(v_len(v_sub(v, trans[0])) < 1e-7 for v in trans):
            out.append(_raw(struct.pack('<HB5x3f28x', 0, 0, *trans[0])))
        else:
            mins = [min(v[i] for v in trans) for i in range(3)]
            step = [(max(v[i] for v in trans) - mins[i]) / 65535.0 for i in range(3)]
            head = bytearray(struct.pack('<HB5x3f3fQ', frames, 0, *mins, *step, PTR)) + idx
            head += bytes(max(0, 48 + (frames + 1) * (2 if wide else 1) - len(head)))
            out.append(_raw(bytes(head)))
            keys = bytearray()
            for v in trans:
                keys += struct.pack('<3H', *(int(round((v[i] - mins[i]) / step[i])) if step[i] else 0 for i in range(3)))
            out.append(_raw(bytes(keys)))
    if quats:
        width = 4 if three_d else 2

        def shorts(q):
            q = q_norm(q)
            if q[3] < 0:
                q = tuple(-c for c in q)
            v = q if three_d else q_norm((0.0, 0.0, q[2], q[3]))[2:]
            return [max(-32767, min(32767, int(round(c * 32767)))) for c in v]

        if frames == 0 or all(q_angle(q, quats[0]) < 1e-5 for q in quats):
            body = struct.pack('<H6x%dh' % width, 0, *shorts(quats[0]))
            out.append(_raw(body + bytes((28 if three_d else 24) - len(body))))
        else:
            out.append(_raw(struct.pack('<H6xQ', frames, PTR) + idx + bytes(max(0, 8 - len(idx)))))
            keys, prev = bytearray(), None
            for q in quats:
                if prev is not None and q_dot(prev, q) < 0:
                    q = tuple(-c for c in q)
                prev = q
                s = q_norm(q) if three_d else q_norm((0.0, 0.0, q[2], q[3]))[2:]
                keys += struct.pack('<%dh' % width, *(max(-32767, min(32767, int(round(c * 32767)))) for c in s))
            out.append(_raw(bytes(keys)))
    return b''.join(out)


# ------------------------------------------------------------------ clips
def dense(keys, frames, rotation):
    """Value at every frame 0..frames of a sparse key list (the game interpolates linearly)."""
    if len(keys) == 1:
        return [keys[0][1]] * (frames + 1)
    out, k = [], 0
    for f in range(frames + 1):
        while k + 1 < len(keys) - 1 and keys[k + 1][0] <= f:
            k += 1
        (f0, v0), (f1, v1) = keys[k], keys[k + 1]
        if f <= f0:
            out.append(v0)
        elif f >= f1:
            out.append(v1)
        else:
            t = (f - f0) / (f1 - f0)
            out.append(q_nlerp(v0, v1, t) if rotation else tuple(a + (b - a) * t for a, b in zip(v0, v1)))
    return out


class Clip:
    """A decoded or imported animation, one value per frame.

    rot[bone] = list of quaternions (relative to the parent bone); trans[bone] = list of offsets from the
    model's bind translation, as the game stores them, or None (no offset);
    delta_t / delta_q = per-frame root delta or None; notes = [(name, time 0..1)]."""

    def __init__(self):
        self.name, self.frames, self.rate, self.loop = '', 0, 30.0, False
        self.rot, self.trans = {}, {}
        self.delta_t = self.delta_q = None
        self.three_d = False
        self.notes = []
        self.header_bytes = None     # (flags, assetType, byte 131, byte 132) of a stock animation
        self.has_delta_part = False  # stock animations may carry a root delta record with nothing in it
        self.bones = []

    @classmethod
    def from_xanim(cls, path):
        a = codec.decode(path)
        c = cls()
        c.name, c.frames, c.rate, c.loop = a.name, a.frames, a.rate, bool(a.flags & ANIM_LOOP)
        c.header_bytes = (a.flags, a.header[130], a.header[131], a.header[132])
        c.bones = list(a.rotations)
        for n in c.bones:
            r, t = a.rotations[n], a.translations.get(n)
            c.rot[n] = [IDENT] * (c.frames + 1) if r is None else dense(r, c.frames, True)
            c.trans[n] = None if t is None else dense(t, c.frames, False)
        d = decode_delta(a)
        if d:
            c.delta_t = dense(d['trans'], c.frames, False) if d['trans'] else None
            c.delta_q = dense(d['quat'], c.frames, True) if d['quat'] else None
            c.three_d = d['three_d']
        c.has_delta_part = bool(a.tail)
        c.notes = list(a.notify)
        return c

    def duration(self):
        return self.frames / self.rate

    def pose(self, skel, frame):
        """Model-space (rotations, translations) of every skeleton bone at a frame."""
        lq, lt = list(skel.q), list(skel.t)
        for n, i in skel.index.items():
            if n in self.rot:
                lq[i] = self.rot[n][frame]
                if self.trans.get(n) is not None:
                    lt[i] = v_add(skel.t[i], self.trans[n][frame])
        return skel.globals(lq, lt)

    def write_xanim(self, out_dir, asset_type=None, flags=None, unk=(0, 0)):
        a = codec.Animation()
        a.name, a.frames, a.rate = self.name, self.frames, self.rate
        const_q = lambda v: all(max(abs(x - y) for x, y in zip(q, v[0])) < 2e-6 for q in v)  # noqa: E731
        for n in self.bones:
            r, t = self.rot[n], self.trans.get(n)
            if const_q(r):
                a.rotations[n] = None if q_angle(r[0], IDENT) < 1e-4 else [(0, r[0])]
            else:
                a.rotations[n] = list(enumerate(r))
            if t is None:
                a.translations[n] = None
            elif all(v_len(v_sub(v, t[0])) < 2e-5 for v in t):
                a.translations[n] = [(0, t[0])]
            else:
                a.translations[n] = list(enumerate(t))
        a.notify = sorted(self.notes, key=lambda x: x[1])
        if not any(n == 'end' for n, _ in a.notify):
            a.notify.append(('end', 1.0))
        if len(a.notify) > 255:
            raise Problem('more than 255 notetracks')
        moving = self.delta_t is not None or self.delta_q is not None
        delta = moving or self.has_delta_part
        a.tail = encode_delta(self.frames, self.delta_t, self.delta_q, self.three_d) if delta else b''
        if flags is None:
            flags = (ANIM_LOOP if self.loop else 0) | (ANIM_DELTA if moving else 0) | (ANIM_DELTA_3D if moving and self.three_d else 0)
        if asset_type is None:
            asset_type = 2 if moving else 1
        head = bytearray(codec.HEADER_SIZE)
        struct.pack_into('<QQ', head, 0, PTR, PTR if self.bones else 0)
        struct.pack_into('<Q', head, 80, PTR if delta else 0)
        struct.pack_into('<ff', head, 100, self.rate, self.rate / self.frames if self.frames else 0.0)
        head[118], head[130], head[131], head[132] = flags, asset_type, unk[0], unk[1]
        a.header = bytes(head)
        folder = os.path.join(out_dir, 'xanim')
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, self.name + '.xab')
        codec.encode(a, path)
        return path


# ------------------------------------------------------------------ glTF writing
class GlbWriter:
    def __init__(self):
        self.blob, self.views, self.accessors = bytearray(), [], []

    def add(self, fmt, rows, kind, component=5126, target=None, minmax=False):
        flat = [c for row in rows for c in row] if kind != 'SCALAR' else list(rows)
        while len(self.blob) % 4:
            self.blob.append(0)
        view = {'buffer': 0, 'byteOffset': len(self.blob), 'byteLength': struct.calcsize('<' + fmt) * len(flat)}
        if target:
            view['target'] = target
        self.blob += struct.pack('<%d%s' % (len(flat), fmt), *flat)
        self.views.append(view)
        acc = {'bufferView': len(self.views) - 1, 'componentType': component, 'count': len(rows), 'type': kind}
        if minmax:
            if kind == 'SCALAR':
                acc['min'], acc['max'] = [min(flat)], [max(flat)]
            else:
                width = len(rows[0])
                acc['min'] = [min(r[i] for r in rows) for i in range(width)]
                acc['max'] = [max(r[i] for r in rows) for i in range(width)]
        self.accessors.append(acc)
        return len(self.accessors) - 1

    def save(self, path, doc):
        doc['buffers'] = [{'byteLength': len(self.blob)}]
        doc['bufferViews'], doc['accessors'] = self.views, self.accessors
        text = json.dumps(doc, separators=(',', ':')).encode()
        text += b' ' * (-len(text) % 4)
        blob = bytes(self.blob) + bytes(-len(self.blob) % 4)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(text) + 8 + len(blob)))
            f.write(struct.pack('<II', len(text), 0x4E4F534A) + text)
            f.write(struct.pack('<II', len(blob), 0x004E4942) + blob)


def f32(v):
    return struct.unpack('<f', struct.pack('<f', v))[0]


def _proxy_mesh(skel, scale):
    """A thin pyramid from every bone to each child, weighted to the bone: enough for a DCC tool to
    build an armature and show the pose. Not the character's mesh."""
    _, gt = skel.globals()
    pos, joints, tris = [], [], []
    for i, p in enumerate(skel.parents):
        if p < 0:
            continue
        a, b = to_gltf_v(gt[p], scale), to_gltf_v(gt[i], scale)
        d = v_sub(b, a)
        length = v_len(d)
        if length < 1e-5:
            continue
        axis = (1.0, 0.0, 0.0) if abs(d[0]) < 0.9 * length else (0.0, 1.0, 0.0)
        u = (d[1] * axis[2] - d[2] * axis[1], d[2] * axis[0] - d[0] * axis[2], d[0] * axis[1] - d[1] * axis[0])
        ul = v_len(u)
        u = tuple(c / ul for c in u)
        w = (d[1] * u[2] - d[2] * u[1], d[2] * u[0] - d[0] * u[2], d[0] * u[1] - d[1] * u[0])
        w = tuple(c / length for c in w)
        r = max(0.004, min(0.03, length * 0.12)) * (scale / INCH)
        base = len(pos)
        for k in range(3):
            ang = 2 * math.pi * k / 3
            pos.append(tuple(a[j] + r * (math.cos(ang) * u[j] + math.sin(ang) * w[j]) for j in range(3)))
        pos.append(b)
        joints.extend([(p + 1, 0, 0, 0)] * 4)
        tris += [(base, base + 1, base + 2), (base, base + 3, base + 1), (base + 1, base + 3, base + 2), (base + 2, base + 3, base)]
    if not pos:
        pos, joints, tris = [(0, 0, 0), (0.01, 0, 0), (0, 0.01, 0)], [(1, 0, 0, 0)] * 3, [(0, 1, 2)]
    return [tuple(f32(c) for c in v) for v in pos], joints, tris


def write_gltf(path, skel, clip=None, scale=INCH):
    """Skeleton (bind pose from the model) and, when given, one animation."""
    w = GlbWriter()
    nodes = [{'name': ROOT_MOTION, 'children': [i + 1 for i, p in enumerate(skel.parents) if p < 0]}]
    for i, name in enumerate(skel.names):
        node = {'name': name, 'translation': [f32(c) for c in to_gltf_v(skel.t[i], scale)],
                'rotation': [f32(c) for c in to_gltf_q(skel.q[i])]}
        kids = [j + 1 for j, p in enumerate(skel.parents) if p == i]
        if kids:
            node['children'] = kids
        nodes.append(node)
    gq, gt = skel.globals()
    inverse = [(1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0)]
    for q, t in zip(gq, gt):
        qi = q_conj(to_gltf_q(q))
        ti = q_rot(qi, tuple(-c for c in to_gltf_v(t, scale)))
        cols = [q_rot(qi, e) for e in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
        inverse.append((*cols[0], 0.0, *cols[1], 0.0, *cols[2], 0.0, *ti, 1.0))
    pos, joints, tris = _proxy_mesh(skel, scale)
    prim = {'attributes': {
        'POSITION': w.add('f', pos, 'VEC3', target=34962, minmax=True),
        'JOINTS_0': w.add('H', joints, 'VEC4', component=5123, target=34962),
        'WEIGHTS_0': w.add('f', [(1.0, 0.0, 0.0, 0.0)] * len(pos), 'VEC4', target=34962)},
        'indices': w.add('I', [i for t in tris for i in t], 'SCALAR', component=5125, target=34963)}
    nodes.append({'name': 'iw7_proxy_mesh', 'mesh': 0, 'skin': 0})
    info = {'tool': 'iw7_anim_gltf', 'model': skel.name, 'scale': scale, 'axes': 'game (x,y,z) -> glTF (x,z,-y)'}
    doc = {'asset': {'version': '2.0', 'generator': 'iw7_anim_gltf', 'extras': {'iw7': info}},
           'scene': 0, 'scenes': [{'nodes': [0, len(nodes) - 1]}], 'nodes': nodes,
           'meshes': [{'name': 'iw7_proxy', 'primitives': [prim]}],
           'skins': [{'name': skel.name, 'skeleton': 0, 'joints': list(range(len(skel.names) + 1)),
                      'inverseBindMatrices': w.add('f', inverse, 'MAT4')}]}
    report = {'model': skel.name, 'bones': len(skel.names), 'scale': scale}
    if clip is not None:
        missing = [n for n in clip.bones if n not in skel.index]
        times = w.add('f', [f / clip.rate for f in range(clip.frames + 1)], 'SCALAR', minmax=True)
        samplers, channels = [], []

        def channel(node, target, rows, kind):
            samplers.append({'input': times, 'output': w.add('f', rows, kind), 'interpolation': 'LINEAR'})
            channels.append({'sampler': len(samplers) - 1, 'target': {'node': node, 'path': target}})

        def continuous(quats):
            out, prev = [], None
            for q in quats:
                if prev is not None and q_dot(prev, q) < 0:
                    q = tuple(-c for c in q)
                out.append(q)
                prev = q
            return out

        for n in clip.bones:
            if n in missing:
                continue
            node = skel.index[n] + 1
            channel(node, 'rotation', [to_gltf_q(q) for q in continuous(clip.rot[n])], 'VEC4')
            if clip.trans.get(n) is not None:
                bind = skel.t[skel.index[n]]
                channel(node, 'translation', [to_gltf_v(v_add(bind, v), scale) for v in clip.trans[n]], 'VEC3')
        if clip.delta_t is not None:
            channel(0, 'translation', [to_gltf_v(v, scale) for v in clip.delta_t], 'VEC3')
        if clip.delta_q is not None:
            channel(0, 'rotation', [to_gltf_q(q) for q in continuous(clip.delta_q)], 'VEC4')
        extras = dict(info, name=clip.name, frames=clip.frames, rate=clip.rate, loop=clip.loop,
                      delta=clip.delta_t is not None or clip.delta_q is not None,
                      delta_part=bool(getattr(clip, 'has_delta_part', False)), delta_3d=clip.three_d,
                      notes=[{'name': n, 'time': t, 'seconds': t * clip.duration()} for n, t in clip.notes])
        if clip.header_bytes:
            extras['header'] = dict(zip(('flags', 'asset_type', 'byte131', 'byte132'), clip.header_bytes))
        doc['animations'] = [{'name': clip.name, 'samplers': samplers, 'channels': channels, 'extras': {'iw7': extras}}]
        report.update(animation=clip.name, frames=clip.frames, rate=clip.rate, animated_bones=len(clip.bones) - len(missing),
                      bones_missing_from_model=missing, root_motion=extras['delta'], notes=len(clip.notes))
    w.save(path, doc)
    return report


# ------------------------------------------------------------------ glTF reading
class Gltf:
    SIZES = {5120: ('b', 127.0), 5121: ('B', 255.0), 5122: ('h', 32767.0), 5123: ('H', 65535.0), 5125: ('I', None), 5126: ('f', None)}
    WIDTH = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}

    def __init__(self, path):
        with open(path, 'rb') as f:
            data = f.read()
        base = os.path.dirname(os.path.abspath(path))
        self.buffers = []
        if data[:4] == b'glTF':
            p, self.doc, blob = 12, None, b''
            while p < len(data):
                size, kind = struct.unpack_from('<II', data, p)
                body = data[p + 8:p + 8 + size]
                if kind == 0x4E4F534A:
                    self.doc = json.loads(body.decode('utf-8'))
                elif kind == 0x004E4942:
                    blob = body
                p += 8 + size
            if self.doc is None:
                raise Problem('no JSON chunk in the glb')
        else:
            self.doc, blob = json.loads(data.decode('utf-8')), b''
        for b in self.doc.get('buffers', []):
            uri = b.get('uri')
            if uri is None:
                self.buffers.append(blob)
            elif uri.startswith('data:'):
                self.buffers.append(base64.b64decode(uri.split(',', 1)[1]))
            else:
                with open(os.path.join(base, uri), 'rb') as f:
                    self.buffers.append(f.read())
        self.nodes = self.doc.get('nodes', [])
        self.parent = {}
        for i, n in enumerate(self.nodes):
            for c in n.get('children', []):
                self.parent[c] = i
        self._cache = {}

    def accessor(self, index):
        if index in self._cache:
            return self._cache[index]
        acc = self.doc['accessors'][index]
        if 'sparse' in acc:
            raise Problem('sparse accessors are not supported')
        view = self.doc['bufferViews'][acc['bufferView']]
        fmt, norm = self.SIZES[acc['componentType']]
        width = self.WIDTH[acc['type']]
        size = struct.calcsize('<' + fmt) * width
        stride = view.get('byteStride') or size
        start = view.get('byteOffset', 0) + acc.get('byteOffset', 0)
        buf = self.buffers[view['buffer']]
        rows = []
        for i in range(acc['count']):
            row = struct.unpack_from('<%d%s' % (width, fmt), buf, start + i * stride)
            if acc.get('normalized') and norm:
                row = tuple(max(-1.0, c / norm) for c in row)
            rows.append(row[0] if width == 1 else row)
        self._cache[index] = rows
        return rows

    def local(self, node):
        """Static (translation, rotation, uniform scale) of a node."""
        n = self.nodes[node]
        if 'matrix' in n:
            m = n['matrix']
            s = [v_len(m[0:3]), v_len(m[4:7]), v_len(m[8:11])]
            r = [[m[c * 4 + r_] / (s[c] or 1.0) for c in range(3)] for r_ in range(3)]
            tr = r[0][0] + r[1][1] + r[2][2]
            if tr > 0:
                k = math.sqrt(tr + 1.0) * 2
                q = ((r[2][1] - r[1][2]) / k, (r[0][2] - r[2][0]) / k, (r[1][0] - r[0][1]) / k, 0.25 * k)
            else:
                i = max(range(3), key=lambda a: r[a][a])
                j, l = (i + 1) % 3, (i + 2) % 3
                k = math.sqrt(1.0 + r[i][i] - r[j][j] - r[l][l]) * 2
                q = [0.0] * 4
                q[i], q[j], q[l], q[3] = 0.25 * k, (r[j][i] + r[i][j]) / k, (r[l][i] + r[i][l]) / k, (r[l][j] - r[j][l]) / k
            return tuple(m[12:15]), q_norm(tuple(q)), s
        return tuple(n.get('translation', (0.0, 0.0, 0.0))), q_norm(tuple(n.get('rotation', IDENT))), list(n.get('scale', (1.0, 1.0, 1.0)))


def _sample_channel(times, values, mode, t, rotation):
    n = len(times)
    if mode == 'CUBICSPLINE':
        value = lambda i: values[i * 3 + 1]  # noqa: E731
    else:
        value = lambda i: values[i]  # noqa: E731
    if t <= times[0] or n == 1:
        v = value(0)
    elif t >= times[-1]:
        v = value(n - 1)
    else:
        i = bisect.bisect_right(times, t + (1e-5 if mode == 'STEP' else 0.0)) - 1
        i = min(i, n - 2)
        t0, t1 = times[i], times[i + 1]
        u = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
        if mode == 'STEP':
            v = value(i)
        elif mode == 'CUBICSPLINE':
            dt = t1 - t0
            p0, m0, p1, m1 = value(i), values[i * 3 + 2], value(i + 1), values[(i + 1) * 3]
            u2, u3 = u * u, u * u * u
            v = tuple((2 * u3 - 3 * u2 + 1) * a + (u3 - 2 * u2 + u) * dt * b + (-2 * u3 + 3 * u2) * c + (u3 - u2) * dt * d
                      for a, b, c, d in zip(p0, m0, p1, m1))
        elif rotation:
            return q_slerp(q_norm(value(i)), q_norm(value(i + 1)), u)
        else:
            v = tuple(a + (b - a) * u for a, b in zip(value(i), value(i + 1)))
    return q_norm(v) if rotation else tuple(v)


def read_gltf(path, skel, name=None, animation=None, rate=None, scale=None, loop=None, notes=None,
              keep_bind_bones=True, root_motion_node=ROOT_MOTION):
    """A glTF animation (or, without one, its static pose) as a Clip on skel. Returns (clip, report)."""
    g = Gltf(path)
    anims = g.doc.get('animations', [])
    anim = None
    if anims:
        if animation is None:
            anim = anims[0]
        elif str(animation).isdigit() and int(animation) < len(anims):
            anim = anims[int(animation)]
        else:
            anim = next((a for a in anims if a.get('name') == animation), None)
            if anim is None:
                raise Problem('animation %r not found; the file has: %s' % (animation, ', '.join(a.get('name', '?') for a in anims)))
    extras = ((anim or {}).get('extras') or {}).get('iw7') or {}
    asset = (g.doc.get('asset', {}).get('extras') or {}).get('iw7') or {}
    scale = scale or extras.get('scale') or asset.get('scale') or INCH
    rate = float(rate or extras.get('rate') or 30.0)
    by_name = {}
    duplicates = set()
    for i, n in enumerate(g.nodes):
        nm = n.get('name')
        if nm in by_name:
            duplicates.add(nm)
        elif nm is not None:
            by_name[nm] = i
    lower = {k.lower(): v for k, v in by_name.items()}
    node_of = {}
    for b in skel.names:
        i = by_name.get(b, lower.get(b.lower()))
        if i is not None:
            node_of[b] = i
    ref = by_name.get(root_motion_node)
    channels = {}
    scaled = set()
    t_min, t_max = None, None
    for ch in (anim or {}).get('channels', []):
        target = ch['target']
        if 'node' not in target or target['path'] not in ('translation', 'rotation', 'scale'):
            continue
        s = anim['samplers'][ch['sampler']]
        times, values = g.accessor(s['input']), g.accessor(s['output'])
        if not times:
            continue
        if target['path'] == 'scale':
            if any(abs(c - 1.0) > 1e-3 for v in values for c in v):
                scaled.add(g.nodes[target['node']].get('name', '#%d' % target['node']))
            continue
        channels[(target['node'], target['path'])] = (times, values, s.get('interpolation', 'LINEAR'))
        t_min = times[0] if t_min is None else min(t_min, times[0])
        t_max = times[-1] if t_max is None else max(t_max, times[-1])
    if extras.get('frames') is not None and rate == extras.get('rate'):
        frames, t_min = int(extras['frames']), 0.0
    else:
        frames = int(round((t_max - t_min) * rate)) if channels else 0
        t_min = t_min or 0.0
    if frames > 65535:
        raise Problem('%d frames: over the game limit of 65535' % frames)
    animated_nodes = {n for n, _ in channels}
    static = {}
    non_uniform = []

    def local(node, t):
        if node not in static:
            static[node] = g.local(node)
            s = static[node][2]
            if max(s) - min(s) > 1e-3 * max(1.0, max(s)):
                non_uniform.append(g.nodes[node].get('name', '#%d' % node))
        tr, q, s = static[node]
        c = channels.get((node, 'translation'))
        if c:
            tr = _sample_channel(c[0], c[1], c[2], t, False)
        c = channels.get((node, 'rotation'))
        if c:
            q = _sample_channel(c[0], c[1], c[2], t, True)
        return tr, q, s[0]

    def world(node, t, memo):
        if node in memo:
            return memo[node]
        tr, q, s = local(node, t)
        p = g.parent.get(node)
        if p is not None:
            pt, pq, ps = world(p, t, memo)
            tr, q, s = v_add(pt, tuple(ps * c for c in q_rot(pq, tr))), q_mul(pq, q), ps * s
        memo[node] = (tr, q, s)
        return memo[node]

    def moves(node):
        while node is not None and node != ref:
            if node in animated_nodes:
                return True
            node = g.parent.get(node)
        return False

    unit = 1.0 / scale
    bind_gq, bind_gt = skel.globals()
    rot = {b: [] for b in skel.names}
    trans = {b: [] for b in skel.names}
    delta_t, delta_q = [], []
    for f in range(frames + 1):
        t = t_min + f / rate
        memo = {}
        if ref is not None:
            rt, rq, rs = world(ref, t, memo)
            delta_t.append(to_game_v(rt, unit))
            delta_q.append(to_game_q(rq))
        else:
            rt, rq, rs = (0.0, 0.0, 0.0), IDENT, 1.0
        gq, gt = [], []
        for i, b in enumerate(skel.names):
            p = skel.parents[i]
            if b in node_of:
                wt, wq, _ = world(node_of[b], t, memo)
                mq = to_game_q(q_mul(q_conj(rq), wq))
                mt = to_game_v(q_rot(q_conj(rq), v_sub(wt, rt)), unit / rs)
            elif p < 0:
                mq, mt = bind_gq[i], bind_gt[i]
            else:
                mq, mt = q_mul(gq[p], skel.q[i]), v_add(gt[p], q_rot(gq[p], skel.t[i]))
            gq.append(mq)
            gt.append(mt)
            if p < 0:
                rot[b].append(mq)
                trans[b].append(mt)
            else:
                inv = q_conj(gq[p])
                rot[b].append(q_norm(q_mul(inv, mq)))
                trans[b].append(q_rot(inv, v_sub(mt, gt[p])))
    clip = Clip()
    clip.name = (name or extras.get('name') or (anim or {}).get('name') or os.path.splitext(os.path.basename(path))[0]).lower()
    clip.frames, clip.rate = frames, rate
    clip.loop = bool(extras.get('loop')) if loop is None else loop
    included, bind_only = [], []
    for i, b in enumerate(skel.names):
        if b not in node_of:
            continue
        off_bind = max(q_angle(q, skel.q[i]) for q in rot[b]) > 0.01 or max(v_len(v_sub(v, skel.t[i])) for v in trans[b]) > 1e-3
        if not (node_of[b] in animated_nodes or off_bind):
            continue
        if not keep_bind_bones and not off_bind:
            bind_only.append(b)
            continue
        included.append(b)
    for b in included:
        i = skel.index[b]
        clip.rot[b] = rot[b]
        offsets = [v_sub(v, skel.t[i]) for v in trans[b]]
        at_bind = max(v_len(v) for v in offsets) < 2e-5 * max(1.0, v_len(skel.t[i]))
        clip.trans[b] = None if at_bind else offsets
    clip.bones = included
    if ref is not None and ((ref, 'translation') in channels or (ref, 'rotation') in channels or extras.get('delta')):
        t0 = (0.0, 0.0, 0.0) if extras.get('delta') else delta_t[0]
        clip.delta_t = [v_sub(v, t0) for v in delta_t]
        clip.delta_q = delta_q
        clip.three_d = max(math.hypot(q[0], q[1]) for q in delta_q) > 1e-4
        if extras.get('delta') and (ref, 'rotation') not in channels:
            clip.delta_q = None
        if extras.get('delta') and (ref, 'translation') not in channels:
            clip.delta_t = None
        if not extras.get('delta') and max(v_len(v) for v in clip.delta_t) < 1e-4 and max(q_angle(q, IDENT) for q in delta_q) < 1e-3:
            clip.delta_t = clip.delta_q = None      # keyed by the DCC tool but never moved: no root motion
            clip.three_d = False
    note_list = [(n['name'], float(n['time'])) for n in extras.get('notes', [])] if notes is None else []
    for text in notes or []:
        nm, _, when = text.rpartition(':')
        if not nm:
            raise Problem('a note is NAME:SECONDS, got %r' % text)
        seconds = float(when)
        if not 0 <= seconds <= frames / rate + 1e-6:
            raise Problem('note %s at %g s is outside the clip (%g s)' % (nm, seconds, frames / rate))
        note_list.append((nm, min(1.0, seconds * rate / frames) if frames else 0.0))
    clip.notes = note_list
    if extras.get('header'):
        h = extras['header']
        clip.header_bytes = (h['flags'], h['asset_type'], h['byte131'], h['byte132'])
    clip.has_delta_part = bool(extras.get('delta_part'))
    skeleton_nodes = set(node_of.values()) | ({ref} if ref is not None else set())
    report = {
        'animation': clip.name, 'frames': frames, 'rate': rate, 'seconds': frames / rate, 'scale': scale,
        'bones_in_skeleton': len(skel.names), 'bones_matched': len(node_of), 'bones_written': len(included),
        'bones_with_translation': sum(1 for b in included if clip.trans[b] is not None),
        'skeleton_bones_not_in_file': [b for b in skel.names if b not in node_of],
        'animated_nodes_not_in_skeleton': sorted({g.nodes[n].get('name', '#%d' % n) for n in animated_nodes if n not in skeleton_nodes}),
        'bones_left_out_at_bind': bind_only, 'scale_animation_ignored_on': sorted(scaled),
        'non_uniform_scale_on': sorted(set(non_uniform)), 'duplicate_node_names': sorted(duplicates & set(skel.names)),
        'root_motion': clip.delta_t is not None or clip.delta_q is not None, 'root_motion_3d': clip.three_d,
        'notes': [{'name': n, 'time': t} for n, t in clip.notes], 'loop': clip.loop}
    if clip.delta_t:
        report['root_motion_end'] = [round(c, 4) for c in clip.delta_t[-1]]
    return clip, report


# ------------------------------------------------------------------ compare / sample
def load_clip(path, skel):
    if path.lower().endswith(('.glb', '.gltf')):
        if skel is None:
            raise Problem('comparing a glTF file needs --model')
        return read_gltf(path, skel)[0]
    return Clip.from_xanim(path)


def compare_clips(a, b, skel=None):
    """Per bone and frame: local rotation error (degrees), local translation error (game units) and,
    with a skeleton, the model-space position error. b is sampled at a's frames."""
    out = {'a': a.name, 'b': b.name, 'frames': [a.frames, b.frames], 'rate': [a.rate, b.rate]}
    if a.frames != b.frames or abs(a.rate - b.rate) > 1e-6:
        out['error'] = 'frame count or rate differ'
        return out
    bones = [n for n in a.bones if n in b.rot]
    only_a, only_b = [n for n in a.bones if n not in b.rot], [n for n in b.bones if n not in a.rot]
    rot_err, tr_err = [], []
    worst_r, worst_t = (0.0, None, 0), (0.0, None, 0)
    skipped = []

    zero = [(0.0, 0.0, 0.0)] * (a.frames + 1)

    def tracks(clip, n):
        i = skel.index.get(n) if skel else None
        r = clip.rot.get(n)
        t = clip.trans.get(n)
        if r is None:           # the clip does not list the bone: it stays in the bind pose
            r = [skel.q[i]] * (a.frames + 1) if i is not None else None
        return r, t if t is not None else zero

    for n in bones + only_a + only_b:
        ra, ta = tracks(a, n)
        rb, tb = tracks(b, n)
        if ra is None or rb is None:
            skipped.append(n)
            continue
        for f in range(a.frames + 1):
            e = q_angle(ra[f], rb[f])
            rot_err.append(e)
            if e > worst_r[0]:
                worst_r = (e, n, f)
        if ta is zero and tb is zero:
            continue
        for f in range(a.frames + 1):
            e = v_len(v_sub(ta[f], tb[f]))
            tr_err.append(e)
            if e > worst_t[0]:
                worst_t = (e, n, f)
    out.update(bones_compared=len(bones), only_in_a=only_a, only_in_b=only_b, skipped=skipped,
               rotation_deg={'worst': worst_r[0], 'p99': percentile(rot_err, 99), 'bone': worst_r[1], 'frame': worst_r[2]},
               translation_units={'worst': worst_t[0], 'p99': percentile(tr_err, 99), 'bone': worst_t[1], 'frame': worst_t[2]})
    if skel is not None:
        pos_err, worst_p = [], (0.0, None, 0)
        for f in range(a.frames + 1):
            _, pa = a.pose(skel, f)
            _, pb = b.pose(skel, f)
            for i, (x, y) in enumerate(zip(pa, pb)):
                e = v_len(v_sub(x, y))
                pos_err.append(e)
                if e > worst_p[0]:
                    worst_p = (e, skel.names[i], f)
        out['model_space_units'] = {'worst': worst_p[0], 'p99': percentile(pos_err, 99), 'bone': worst_p[1], 'frame': worst_p[2]}
    delta = {}
    if (a.delta_t is None) != (b.delta_t is None) or (a.delta_q is None) != (b.delta_q is None):
        delta['error'] = 'root motion present on one side only'
    else:
        if a.delta_t is not None:
            delta['translation_units_worst'] = max(v_len(v_sub(x, y)) for x, y in zip(a.delta_t, b.delta_t))
        if a.delta_q is not None:
            delta['rotation_deg_worst'] = max(q_angle(x, y) for x, y in zip(a.delta_q, b.delta_q))
    out['root_motion'] = delta
    na = sorted((n, round(t, 6)) for n, t in a.notes)
    nb = sorted((n, round(t, 6)) for n, t in b.notes)
    out['notes_equal'] = na == nb
    out['loop_equal'] = a.loop == b.loop
    return out


def sample_positions(clip, skel, bones, with_delta=False):
    """Model-space origin of each named bone at every frame (game units)."""
    rows = []
    for f in range(clip.frames + 1):
        _, gt = clip.pose(skel, f)
        row = {'frame': f, 'time': f / clip.rate}
        for b in bones:
            p = gt[skel.index[b]]
            if with_delta and clip.delta_t is not None:
                dq = clip.delta_q[f] if clip.delta_q is not None else IDENT
                p = v_add(clip.delta_t[f], q_rot(dq, p))
            row[b] = [round(c, 4) for c in p]
        rows.append(row)
    return rows


def angle_axes(angles):
    """The game's (pitch, yaw, roll) in degrees -> the forward, left and up axes of an entity."""
    p, y, r = (math.radians(a) for a in angles)
    sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(r), math.cos(r)
    forward = (cp * cy, cp * sy, -sp)
    right = (-sr * sp * cy + cr * sy, -sr * sp * sy - cr * cy, -sr * cp)
    up = (cr * sp * cy + sr * sy, cr * sp * sy - sr * cy, cr * cp)
    return forward, tuple(-c for c in right), up


def pose_between(clip, skel, frame):
    """Model-space bone positions at a fractional frame (local tracks interpolated as the game does)."""
    f0 = max(0, min(clip.frames, int(math.floor(frame))))
    f1 = min(clip.frames, f0 + 1)
    u = min(1.0, max(0.0, frame - f0))
    lq, lt = list(skel.q), list(skel.t)
    for n, i in skel.index.items():
        if n in clip.rot:
            lq[i] = q_nlerp(clip.rot[n][f0], clip.rot[n][f1], u)
            tr = clip.trans.get(n)
            if tr is not None:
                lt[i] = tuple(c + a + (b - a) * u for c, a, b in zip(skel.t[i], tr[f0], tr[f1]))
    return skel.globals(lq, lt)[1]


def compare_run(doc, clip, skel, loop=None, window=0.5, bind_tolerance=0.05, from_ms=None, to_ms=None, limit=1.0):
    """Tag positions sampled in the running game (a gamelab `anim-<name>.json`) against the clip.

    Each sample carries the entity's origin and angles, so the expected world position of a tag is
    origin + axes * (model-space position at that time). The one unknown is when the game started the clip
    relative to the script's clock: the start offset is searched (within `window` seconds, or over the whole
    loop for a looping clip) and reported. If no tag ever leaves its first position the game did not pose the
    model at all, and that is the verdict. `from_ms` / `to_ms` keep only the samples of that stretch (a zombie
    plays a clip only while it stays in that animation state); `within_limit_until_ms` says how long the game
    stayed within `limit` units of the clip."""
    loop = clip.loop if loop is None else loop
    samples = [x for x in doc['samples'] if x['k'] >= 0 and x.get('origin') and x.get('tags')
               and (from_ms is None or x['ms'] >= from_ms) and (to_ms is None or x['ms'] <= to_ms)]
    if not samples:
        return {'verdict': 'no samples'}
    tags = [t for t in samples[0]['tags'] if t in skel.index]
    local = []          # per sample: tag -> position in the entity's own axes
    for x in samples:
        fw, lf, up = angle_axes(x.get('angles') or (0.0, 0.0, 0.0))
        row = {}
        for t in tags:
            d = v_sub(x['tags'][t], x['origin'])
            row[t] = (d[0] * fw[0] + d[1] * fw[1] + d[2] * fw[2], d[0] * lf[0] + d[1] * lf[1] + d[2] * lf[2], d[0] * up[0] + d[1] * up[1] + d[2] * up[2])
        local.append(row)
    travel = {t: max(v_len(v_sub(r[t], local[0][t])) for r in local) for t in tags}
    expected_travel = {}
    frames = [pose_between(clip, skel, f) for f in range(clip.frames + 1)]
    for t in tags:
        i = skel.index[t]
        expected_travel[t] = max(v_len(v_sub(fr[i], frames[0][i])) for fr in frames)
    _, bind = skel.globals()
    bind_error = max(v_len(v_sub(local[0][t], bind[skel.index[t]])) for t in tags) if tags else 0.0
    out = {'animation': clip.name, 'samples': len(samples), 'tags': tags, 'seconds_sampled': (samples[-1]['ms'] - samples[0]['ms']) / 1000.0,
           'measured_travel_units': {t: round(v, 3) for t, v in travel.items()},
           'authored_travel_units': {t: round(v, 3) for t, v in expected_travel.items()},
           'first_sample_from_bind_units': round(bind_error, 4)}
    if max(travel.values(), default=0.0) < bind_tolerance and max(expected_travel.values(), default=0.0) > 1.0:
        out['verdict'] = 'not posed: no tag moved in the game although the clip moves them'
        return out
    duration = clip.duration()

    index = [skel.index[t] for t in tags]
    keyed = [[fr[i] for i in index] for fr in frames]       # tag positions at whole frames: enough to find the offset

    seam = 0.5 / clip.rate      # a sample this close to the loop point may show the last pose or the first

    def clip_times(x, offset):
        t = x['ms'] / 1000.0 - offset
        if loop and duration > 0:
            t %= duration
            if t < seam or duration - t < seam:
                return (0.0, duration)
        return (max(0.0, min(duration, t)),)

    def errors(offset):
        errs = []
        for x, row in zip(samples, local):
            best_rows = None
            for t in clip_times(x, offset):
                pos = pose_between(clip, skel, t * clip.rate)
                rows = [(v_len(v_sub(row[tag], pos[skel.index[tag]])), tag, x['ms']) for tag in tags]
                if best_rows is None or sum(r[0] for r in rows) < sum(r[0] for r in best_rows):
                    best_rows = rows
            errs.extend(best_rows)
        return errs

    def rms(offset):
        total, count = 0.0, 0
        for x, row in zip(samples, local):
            best_sum = None
            for t in clip_times(x, offset):
                f = t * clip.rate
                f0 = min(clip.frames, int(f))
                f1 = min(clip.frames, f0 + 1)
                u = f - f0
                part = 0.0
                for k, tag in enumerate(tags):
                    a, b, m = keyed[f0][k], keyed[f1][k], row[tag]
                    d0, d1, d2 = a[0] + (b[0] - a[0]) * u - m[0], a[1] + (b[1] - a[1]) * u - m[1], a[2] + (b[2] - a[2]) * u - m[2]
                    part += d0 * d0 + d1 * d1 + d2 * d2
                if best_sum is None or part < best_sum:
                    best_sum = part
            total += best_sum
            count += len(tags)
        return math.sqrt(total / count)

    span = duration if loop else window
    start = 0.0 if loop else -window
    step = 0.01
    best = min((start + k * step for k in range(int(round((span - start if not loop else span) / step)) + 1)), key=rms)
    for fine in (0.002, 0.0005):
        best = min((best + k * fine for k in range(-6, 7)), key=rms)
    e = errors(best)
    worst = max(e)
    per_tag = {t: round(max(v[0] for v in e if v[1] == t), 4) for t in tags}
    over = sorted(v[2] for v in e if v[0] > limit)
    out['within_limit_until_ms'] = (max(x['ms'] for x in samples if x['ms'] < over[0]) if any(x['ms'] < over[0] for x in samples) else None) if over else samples[-1]['ms']
    exact = math.sqrt(sum(v[0] * v[0] for v in e) / len(e))
    # The clip's own travel over the sampled stretch, from the pose at the first sample: comparable with the measured one.
    first = pose_between(clip, skel, clip_times(samples[0], best)[0] * clip.rate)
    along = [pose_between(clip, skel, clip_times(x, best)[-1] * clip.rate) for x in samples]
    out['authored_travel_units'] = {t: round(max(v_len(v_sub(pos[skel.index[t]], first[skel.index[t]])) for pos in along), 3) for t in tags}
    out.update(verdict='posed', start_offset_seconds=round(best, 4), rms_units=round(exact, 4),
               worst_units=round(worst[0], 4), worst_tag=worst[1], worst_at_ms=worst[2],
               p99_units=round(percentile([v[0] for v in e], 99), 4), worst_by_tag_units=per_tag)
    return out


def inspect(path):
    a = codec.decode(path)
    d = decode_delta(a)
    names = list(a.rotations)
    low = [n.lower() for n in names]
    view = 'tag_view' in low or a.name.startswith(('vm_', 'viewmodel_'))
    body = not view and sum(1 for n in ('j_mainroot', 'j_spine4', 'j_head', 'j_knee_le', 'j_knee_ri') if n in low) >= 4
    asset_type = a.header[130]
    kind = 'viewmodel' if view else 'full body' if body else 'other (prop, partial body or face)'
    return {
        'name': a.name, 'kind': kind, 'additive_suspected': asset_type == 6,
        'frames': a.frames, 'rate': a.rate, 'seconds': a.frames / a.rate if a.rate else 0.0,
        'loop': bool(a.flags & ANIM_LOOP), 'flags': a.flags, 'asset_type': asset_type,
        'byte131': a.header[131], 'byte132': a.header[132],
        'has_delta': bool(a.flags & ANIM_DELTA), 'delta_part': bool(a.tail),
        'delta': None if not d else {'translation_keys': len(d['trans'] or []), 'rotation_keys': len(d['quat'] or []),
                                     'three_d': d['three_d'],
                                     'end_translation': [round(c, 4) for c in d['trans'][-1][1]] if d['trans'] else None},
        'bones': len(names),
        'rotation': {'identity': sum(1 for n in names if a.rotations[n] is None),
                     'static': sum(1 for n in names if a.rotations[n] and len(a.rotations[n]) == 1),
                     'animated': sum(1 for n in names if a.rotations[n] and len(a.rotations[n]) > 1)},
        'translation': {'bind': sum(1 for n in names if a.translations.get(n) is None),
                        'static': sum(1 for n in names if a.translations.get(n) and len(a.translations[n]) == 1),
                        'animated': sum(1 for n in names if a.translations.get(n) and len(a.translations[n]) > 1)},
        'notes': [{'name': n, 'time': round(t, 6)} for n, t in a.notify], 'bone_names': names}


def zone_source(dump, zone, out, tree_name=None):
    """A ZoneTool source tree for every animation of a dump folder: the files, the zone list, the table of names
    (`ncs_anm_<zone>`) and an animation tree file (`animtrees/<tree>.atr`): a script that names an animation as a
    value (`#using_animtree("<tree>"); %my_clip`, for getanimlength, getmovedelta, getnotetracktimes) needs the
    animation listed in that tree."""
    tree_name = tree_name or zone + '_anims'
    src = os.path.join(dump, 'xanim')
    names = sorted(f[:-4] for f in os.listdir(src) if f.lower().endswith('.xab'))
    if not names:
        raise Problem('no .xab under ' + src)
    tree = os.path.join(out, 'zonetool', zone)
    os.makedirs(os.path.join(tree, 'xanim'), exist_ok=True)
    os.makedirs(os.path.join(tree, 'netconststrings'), exist_ok=True)
    os.makedirs(os.path.join(out, 'zone_source'), exist_ok=True)
    for n in names:
        with open(os.path.join(src, n + '.xab'), 'rb') as f, open(os.path.join(tree, 'xanim', n + '.xab'), 'wb') as g:
            g.write(f.read())
    table = 'ncs_anm_' + zone
    with open(os.path.join(tree, 'netconststrings', table + '.json'), 'w', newline='\n') as f:
        json.dump({'stringType': 16, 'sourceType': 2, 'stringList': names}, f, indent=4)
    os.makedirs(os.path.join(tree, 'animtrees'), exist_ok=True)
    with open(os.path.join(tree, 'animtrees', tree_name + '.atr'), 'w', newline='\n') as f:
        f.write('// written by iw7_anim_gltf.py zone-source\n' + ''.join(n + '\n' for n in names))
    with open(os.path.join(out, 'zone_source', zone + '.csv'), 'w', newline='\n') as f:
        f.write(''.join('xanim,%s\n' % n for n in names) + 'netconststrings,%s\n' % table + 'rawfile,animtrees/%s.atr\n' % tree_name)
    return {'zone': zone, 'animations': names, 'name_table': table, 'animtree': tree_name, 'tree': tree,
            'csv': os.path.join(out, 'zone_source', zone + '.csv')}


# ------------------------------------------------------------------ command line
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('skeleton', help='a model skeleton in bind pose as glb, to animate on')
    p.add_argument('model')
    p.add_argument('--out', required=True)
    p.add_argument('--scale', type=float, default=INCH, help='metres per game unit (default 0.0254)')
    p = sub.add_parser('to-gltf', help='a game animation on a model skeleton as a glTF animation')
    p.add_argument('xanim')
    p.add_argument('--model', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--scale', type=float, default=INCH)
    p = sub.add_parser('from-gltf', help='a glTF animation as a ZoneTool animation source')
    p.add_argument('gltf')
    p.add_argument('--skeleton', required=True)
    p.add_argument('--name')
    p.add_argument('--out', required=True, help='dump folder; writes <out>/xanim/<name>.xab')
    p.add_argument('--animation', help='name or index when the file has several')
    p.add_argument('--fps', type=float, help='game frame rate (default: the file\'s own, else 30)')
    p.add_argument('--scale', type=float, help='metres per game unit in the file (default: the file\'s own, else 0.0254)')
    p.add_argument('--loop', action='store_true')
    p.add_argument('--no-loop', action='store_true')
    p.add_argument('--note', action='append', help='NAME:SECONDS, repeatable; replaces the notes carried in the file')
    p.add_argument('--drop-bind-bones', action='store_true', help='leave out bones that never leave the bind pose')
    p.add_argument('--asset-type', type=int)
    p.add_argument('--strict', action='store_true', help='fail when an animated node has no bone in the skeleton')
    p = sub.add_parser('compare', help='error between two animations (.xab or .glb)')
    p.add_argument('a')
    p.add_argument('b')
    p.add_argument('--model')
    p.add_argument('--max-rotation', type=float, default=0.05)
    p.add_argument('--max-translation', type=float, default=0.01)
    p = sub.add_parser('inspect', help='what an animation is')
    p.add_argument('xanim')
    p.add_argument('--names', action='store_true', help='also list the bone names')
    p = sub.add_parser('zone-source', help='a ZoneTool source tree (files, zone list, name table) for a dump folder')
    p.add_argument('dump')
    p.add_argument('--zone', default='mod')
    p.add_argument('--tree', help='name of the animation tree file written for scripts (default: <zone>_anims)')
    p.add_argument('--out', required=True)
    p = sub.add_parser('compare-run', help='tag positions sampled in the running game against a clip')
    p.add_argument('run_json', help='anim-<name>.json written by the gamelab verdict')
    p.add_argument('clip', help='the source .glb or the built .xab')
    p.add_argument('--model', required=True)
    p.add_argument('--loop', action='store_true', help='the game loops the clip (default: the clip\'s own flag)')
    p.add_argument('--window', type=float, default=0.5, help='seconds searched for the start offset of a clip that does not loop')
    p.add_argument('--max-error', type=float, default=1.0, help='worst tag error in game units for a pass')
    p.add_argument('--from-ms', type=int, help='use only the samples from this time of the log on')
    p.add_argument('--to-ms', type=int, help='use only the samples up to this time of the log')
    p = sub.add_parser('sample', help='model-space bone positions at every frame')
    p.add_argument('clip')
    p.add_argument('--model', required=True)
    p.add_argument('--bones', required=True)
    p.add_argument('--with-root-motion', action='store_true')
    p.add_argument('--out')
    a = ap.parse_args(argv)
    started = time.perf_counter()
    try:
        if a.cmd == 'skeleton':
            report = write_gltf(a.out, Skeleton.load(a.model), None, a.scale)
        elif a.cmd == 'to-gltf':
            report = write_gltf(a.out, Skeleton.load(a.model), Clip.from_xanim(a.xanim), a.scale)
        elif a.cmd == 'from-gltf':
            skel = Skeleton.load(a.skeleton)
            clip, report = read_gltf(a.gltf, skel, a.name, a.animation, a.fps, a.scale,
                                     True if a.loop else False if a.no_loop else None, a.note, not a.drop_bind_bones)
            if not clip.bones:
                raise Problem('no bone of the file matches the skeleton by name')
            if a.strict and report['animated_nodes_not_in_skeleton']:
                raise Problem('animated nodes without a bone: ' + ', '.join(report['animated_nodes_not_in_skeleton']))
            if clip.header_bytes and not (a.loop or a.no_loop or a.asset_type):
                flags, asset_type, unk = clip.header_bytes[0], clip.header_bytes[1], clip.header_bytes[2:]
                path = clip.write_xanim(a.out, asset_type, flags, unk)
            else:
                path = clip.write_xanim(a.out, a.asset_type)
            back = Clip.from_xanim(path)
            err = compare_clips(clip, back, skel)
            report.update(written=path, bytes=os.path.getsize(path),
                          compression='one key per frame; rotations as 4 x 16 bit, translations as 3 x 16 bit of their range',
                          compression_error={'rotation_deg_worst': err['rotation_deg']['worst'],
                                             'translation_units_worst': err['translation_units']['worst'],
                                             'model_space_units_worst': err['model_space_units']['worst'],
                                             'root_motion': err['root_motion']})
        elif a.cmd == 'compare':
            skel = Skeleton.load(a.model) if a.model else None
            report = compare_clips(load_clip(a.a, skel), load_clip(a.b, skel), skel)
            ok = 'error' not in report and report['rotation_deg']['worst'] <= a.max_rotation and \
                report['translation_units']['worst'] <= a.max_translation and 'error' not in report['root_motion']
            report['pass'] = ok
        elif a.cmd == 'compare-run':
            skel = Skeleton.load(a.model)
            with open(a.run_json, encoding='utf-8') as f:
                doc = json.load(f)
            report = compare_run(doc, load_clip(a.clip, skel), skel, True if a.loop else None, a.window,
                                 from_ms=a.from_ms, to_ms=a.to_ms, limit=a.max_error)
            report['pass'] = report.get('verdict') == 'posed' and report['worst_units'] <= a.max_error
        elif a.cmd == 'zone-source':
            report = zone_source(a.dump, a.zone, a.out, a.tree)
        elif a.cmd == 'inspect':
            report = inspect(a.xanim)
            if not a.names:
                del report['bone_names']
        else:
            skel = Skeleton.load(a.model)
            bones = [b for b in a.bones.split(',') if b]
            unknown = [b for b in bones if b not in skel.index]
            if unknown:
                raise Problem('not in the model: ' + ', '.join(unknown))
            clip = load_clip(a.clip, skel)
            report = {'animation': clip.name, 'frames': clip.frames, 'rate': clip.rate,
                      'samples': sample_positions(clip, skel, bones, a.with_root_motion)}
            if a.out:
                with open(a.out, 'w') as f:
                    json.dump(report, f)
                report = {'animation': clip.name, 'frames': clip.frames, 'written': a.out}
    except (Problem, OSError, KeyError, struct.error, ValueError) as exc:
        print(json.dumps({'error': '%s: %s' % (type(exc).__name__, exc)}))
        return 2
    report['seconds_taken'] = round(time.perf_counter() - started, 3)
    print(json.dumps(report, indent=1))
    return 0 if report.get('pass', True) else 1


if __name__ == '__main__':
    sys.exit(main())

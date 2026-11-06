"""Decode and encode ZoneTool IW7 .xab animations (stdlib only).

Layout (verified on every stock cp_zmb animation: each data array consumed
exactly, and every decoded key index sequence starts at 0 and rises strictly
within the frame count; a channel may stop before the last frame):

* names: bones grouped by rotation part type: none, half (2D), full,
  half static, full static (boneCount[0..4]).
* dataByte: for animations under 256 frames, first every animated channel's
  key frame indices (bytes, rotation channels then translation channels);
  then, in all animations, the translation order (one name index per bone,
  groups small, precise, static, none = boneCount[5..8]).
* dataShort: per animated rotation channel its key count - 1 (n); for 256+
  frames followed inline by its n + 1 indices when n < 64, else by a lookup
  table (the index at every 256th key, then the last; ((n - 1) >> 8) + 2
  entries) while the indices go to the index list. Then static rotations
  (2 or 4 shorts), then the same per animated translation channel.
* randomDataShort: rotation keys (2 shorts z,w or 4 shorts x,y,z,w; /32767),
  then precise translation keys (3 unsigned shorts).
* randomDataByte: small translation keys (3 bytes).
* dataInt (floats): per animated translation channel mins then size, then
  static translations.

Keys between indices are interpolated (nlerp for rotations, lerp for
translations). Notetracks and the root delta part are carried over raw.
"""
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'animation'))
import xab_preflight as xab  # noqa: E402

HEADER_SIZE = 136
LARGE = 64


class Animation:
    """frames, rate, frequency, flags; rotations[name] = None (identity) or a
    list of (frame, quat); translations[name] = None (bind) or (frame, vec)
    list; a static channel is a one-entry list at frame 0."""

    def __init__(self):
        self.name = ''
        self.frames = 0
        self.rate = 30.0
        self.frequency = 1.0
        self.flags = 0
        self.rotations = {}
        self.translations = {}
        self.rotation_kind = {}     # name -> 'half' | 'full' (animated/static)
        self.header = bytes(HEADER_SIZE)
        self.tail = b''             # notify + delta records, raw
        self.notify_count = 0


def _norm(q):
    length = math.sqrt(sum(c * c for c in q)) or 1.0
    return tuple(c / length for c in q)


def _q(raw, half):
    if half:
        return _norm((0.0, 0.0, raw[0] / 32767.0, raw[1] / 32767.0))
    return _norm(tuple(c / 32767.0 for c in raw))


def decode(path):
    data = open(path, 'rb').read()
    reader = xab.Reader(data)
    head = xab.header(reader, 'iw7')
    anim = Animation()
    raw_header = data[6:6 + HEADER_SIZE]
    anim.header = raw_header
    anim.name = reader.string()
    names = [reader.string() for _ in range(head['bone_counts'][9])]
    labels = ('dataByte', 'dataShort', 'dataInt', 'randomDataShort', 'randomDataByte', 'randomDataInt', 'indices')
    F = head['frames']
    widths = (1, 2, 4, 2, 1, 4, 2 if F >= 256 else 1)
    arrays = {}
    for label, count, width in zip(labels, head['counts'], widths):
        arrays[label] = reader.array(count, width) if count else b''
    anim.notify_count = head['notify_count']
    anim.notify = []
    if anim.notify_count:
        raw = reader.array(anim.notify_count, 8)
        times = [struct.unpack_from('<f', raw, i * 8 + 4)[0] for i in range(anim.notify_count)]
        anim.notify = [(reader.string(), t) for t in times]
    anim.tail = data[reader.pos:]   # root delta part records (no strings)
    if 9 in anim.tail[:1]:
        raise ValueError('aliased records after the notetracks are not supported')
    anim.frames, anim.rate, anim.frequency, anim.flags = F, head['rate'], head['frequency'], head['flags']
    b = head['bone_counts']
    db = arrays['dataByte']
    ds = struct.unpack('<%dH' % (len(arrays['dataShort']) // 2), arrays['dataShort'])
    ints = struct.unpack('<%df' % (len(arrays['dataInt']) // 4), arrays['dataInt'])
    rs = struct.unpack('<%dh' % (len(arrays['randomDataShort']) // 2), arrays['randomDataShort'])
    rb = arrays['randomDataByte']
    width = 2 if F >= 256 else 1
    idx = struct.unpack('<%d%s' % (len(arrays['indices']) // width, 'H' if width == 2 else 'B'), arrays['indices'])
    pos = {'ds': 0, 'db': 0, 'idx': 0, 'rs': 0, 'rb': 0}

    def counts_and_indices(channels, bones=None):
        out = []
        if F < 256:
            ns = list(ds[pos['ds']:pos['ds'] + channels])
            pos['ds'] += channels
            for n in ns:
                if bones is not None:
                    # Short animations: each translation channel's bone byte
                    # precedes its index bytes.
                    bones.append(db[pos['db']])
                    pos['db'] += 1
                out.append(list(db[pos['db']:pos['db'] + n + 1]))
                pos['db'] += n + 1
            return out
        for _ in range(channels):
            n = ds[pos['ds']]
            pos['ds'] += 1
            if n >= LARGE:
                pos['ds'] += ((n - 1) >> 8) + 2
                out.append(list(idx[pos['idx']:pos['idx'] + n + 1]))
                pos['idx'] += n + 1
            else:
                out.append(list(ds[pos['ds']:pos['ds'] + n + 1]))
                pos['ds'] += n + 1
        return out

    k = 0
    for _ in range(b[0]):
        anim.rotations[names[k]] = None
        k += 1
    animated_rot = counts_and_indices(b[1] + b[2])
    for c, frames in enumerate(animated_rot):
        half = c < b[1]
        size = 2 if half else 4
        keys = []
        for f in frames:
            keys.append((f, _q(rs[pos['rs']:pos['rs'] + size], half)))
            pos['rs'] += size
        anim.rotations[names[k]] = keys
        anim.rotation_kind[names[k]] = 'half' if half else 'full'
        k += 1
    for bucket, size in ((3, 2), (4, 4)):
        for _ in range(b[bucket]):
            raw = struct.unpack('<%dh' % size, struct.pack('<%dH' % size, *ds[pos['ds']:pos['ds'] + size]))
            pos['ds'] += size
            anim.rotations[names[k]] = [(0, _q(raw, size == 2))]
            anim.rotation_kind[names[k]] = 'half' if size == 2 else 'full'
            k += 1
    def bone(index):
        # Some stock character animations list a channel past the names.
        return names[index] if index < len(names) else '#%d' % index

    animated = b[5] + b[6]
    trans_bones = []
    if F < 256:
        animated_trans = counts_and_indices(animated, trans_bones)
        rest = list(db[pos['db']:pos['db'] + b[7] + b[8]])
        pos['db'] += b[7] + b[8]
    else:
        animated_trans = counts_and_indices(animated)
        trans_bones = list(db[:animated])
        rest = list(db[animated:animated + b[7] + b[8]])
        pos['db'] = animated + b[7] + b[8]
    order = trans_bones + rest
    for c, frames in enumerate(animated_trans):
        mins, size = ints[6 * c:6 * c + 3], ints[6 * c + 3:6 * c + 6]
        keys = []
        for f in frames:
            if c < b[5]:
                raw = rb[pos['rb']:pos['rb'] + 3]
                pos['rb'] += 3
                vec = tuple(mins[i] + size[i] * raw[i] / 255.0 for i in range(3))
            else:
                raw = struct.unpack('<3H', struct.pack('<3h', *rs[pos['rs']:pos['rs'] + 3]))
                pos['rs'] += 3
                vec = tuple(mins[i] + size[i] * raw[i] / 65535.0 for i in range(3))
            keys.append((f, vec))
        anim.translations[bone(order[c])] = keys
    base = 6 * (b[5] + b[6])
    for c in range(b[7]):
        anim.translations[bone(order[b[5] + b[6] + c])] = [(0, tuple(ints[base + 3 * c:base + 3 * c + 3]))]
    # The entries of the untranslated group are not reliable bone indices
    # (converted BO3 animations hold out-of-range values there); those bones
    # are the ones no other group lists, and they keep their bind translation.
    for name in names:
        anim.translations.setdefault(name, None)
    for name in names:
        for keys in (anim.rotations.get(name), anim.translations.get(name)):
            if keys and len(keys) > 1:
                frames_seen = [k[0] for k in keys]
                if frames_seen[0] != 0 or frames_seen[-1] > F or any(x >= y for x, y in zip(frames_seen, frames_seen[1:])):
                    raise ValueError('key indices of %s do not rise from 0 within %d frames' % (name, F))
    consumed = {'dataShort': pos['ds'] == len(ds), 'dataByte': pos['db'] == len(db),
                'indices': pos['idx'] == len(idx), 'randomDataShort': pos['rs'] == len(rs),
                'randomDataByte': pos['rb'] == len(rb), 'dataInt': base + 3 * b[7] == len(ints)}
    if not all(consumed.values()):
        raise ValueError('layout not fully consumed: %s' % consumed)
    return anim


def sample(keys, frame, rotation):
    """Value of a key list at an integer frame."""
    if keys is None:
        return None
    if len(keys) == 1 or frame <= keys[0][0]:
        return keys[0][1]
    for (f0, v0), (f1, v1) in zip(keys, keys[1:]):
        if f0 <= frame <= f1:
            t = 0.0 if f1 == f0 else (frame - f0) / (f1 - f0)
            if rotation:
                if sum(a * b for a, b in zip(v0, v1)) < 0:
                    v1 = tuple(-c for c in v1)
                return _norm(tuple(a + (b - a) * t for a, b in zip(v0, v1)))
            return tuple(a + (b - a) * t for a, b in zip(v0, v1))
    return keys[-1][1]


def _record_array(count, payload):
    return bytes([8, 1]) + struct.pack('<I', count) + payload


def _record_string(text):
    return bytes([6, 1]) + text.encode('ascii') + b'\0'


def encode(anim, path):
    """Write anim with every animated channel keyed at every frame: rotations
    as full quaternions, translations as precise (unsigned short) keys."""
    F = anim.frames
    frames = list(range(F + 1))
    none_rot = [n for n, k in anim.rotations.items() if k is None]
    anim_rot = [n for n, k in anim.rotations.items() if k is not None and len(k) > 1]
    static_rot = [n for n, k in anim.rotations.items() if k is not None and len(k) == 1]
    names = none_rot + anim_rot + static_rot
    anim_tr = [n for n in names if anim.translations.get(n) is not None and len(anim.translations[n]) > 1]
    static_tr = [n for n in names if anim.translations.get(n) is not None and len(anim.translations[n]) == 1]
    none_tr = [n for n in names if anim.translations.get(n) is None]
    order = [names.index(n) for n in anim_tr + static_tr + none_tr]
    if len(names) > 255 or len(order) != len(names):
        raise ValueError('bone set')
    data_short, data_byte, indices, rand_short, ints = [], [], [], [], []
    key_count = F  # n = keys - 1

    def put_indices():
        if F < 256:
            data_byte.extend(frames)
        elif key_count >= LARGE:
            data_short.extend([frames[j * 256] for j in range(((key_count - 1) >> 8) + 1)] + [frames[-1]])
            indices.extend(frames)
        else:
            data_short.extend(frames)

    def q16(q):
        return [max(-32767, min(32767, int(round(c * 32767)))) for c in _norm(q)]

    if F < 256:
        data_short.extend([key_count] * len(anim_rot))
        for _ in anim_rot:
            put_indices()
    else:
        for _ in anim_rot:
            data_short.append(key_count)
            put_indices()
    for n in anim_rot:
        prev = None
        for f in frames:
            q = sample(anim.rotations[n], f, True)
            if prev is not None and sum(a * b for a, b in zip(prev, q)) < 0:
                q = tuple(-c for c in q)
            prev = q
            rand_short.extend(q16(q))
    for n in static_rot:
        data_short.extend(v & 0xFFFF for v in q16(anim.rotations[n][0][1]))
    if F < 256:
        data_short.extend([key_count] * len(anim_tr))
        for n in anim_tr:
            data_byte.append(names.index(n))   # bone byte before its indices
            put_indices()
    else:
        for _ in anim_tr:
            data_short.append(key_count)
            put_indices()
    for n in anim_tr:
        values = [sample(anim.translations[n], f, False) for f in frames]
        mins = [min(v[i] for v in values) for i in range(3)]
        size = [max(v[i] for v in values) - mins[i] for i in range(3)]
        ints.extend(mins + size)
        for v in values:
            for i in range(3):
                unsigned = int(round((v[i] - mins[i]) / size[i] * 65535)) if size[i] else 0
                rand_short.append(unsigned - 65536 if unsigned > 32767 else unsigned)  # stored as signed shorts
    for n in static_tr:
        ints.extend(anim.translations[n][0][1])

    # Translation order: short animations already placed each animated channel's
    # bone before its indices; the static and untranslated groups follow.
    data_byte.extend(order if F >= 256 else order[len(anim_tr):])
    head = bytearray(anim.header)
    counts = {
        'dataByte': (len(data_byte), 16, 108, 'H'), 'dataShort': (len(data_short), 24, 110, 'H'),
        'dataInt': (len(ints), 32, 112, 'H'), 'randomDataShort': (len(rand_short), 40, 88, 'I'),
        'randomDataByte': (0, 48, 92, 'I'), 'randomDataInt': (0, 56, 114, 'H'),
        'indices': (len(indices), 64, 96, 'I')}
    for label, (count, ptr, off, fmt) in counts.items():
        if fmt == 'H' and count > 0xFFFF:
            raise ValueError('%s exceeds the IW7 count' % label)
        struct.pack_into('<' + fmt, head, off, count)
        struct.pack_into('<Q', head, ptr, 0xFDFDFDFDFDFDFDFD if count else 0)
    struct.pack_into('<H', head, 116, F)
    bucket = [len(none_rot), 0, len(anim_rot), 0, len(static_rot), 0, len(anim_tr), len(static_tr), len(none_tr), len(names)]
    head[119:129] = bytes(bucket)
    head[129] = len(anim.notify)
    struct.pack_into('<Q', head, 72, 0xFDFDFDFDFDFDFDFD if anim.notify else 0)
    out = bytearray(_record_array(1, bytes(head)))
    out += _record_string(anim.name)
    for n in names:
        out += _record_string(n)
    out += _record_array(len(data_byte), bytes(data_byte)) if data_byte else b''
    out += _record_array(len(data_short), struct.pack('<%dH' % len(data_short), *data_short)) if data_short else b''
    out += _record_array(len(ints), struct.pack('<%df' % len(ints), *ints)) if ints else b''
    out += _record_array(len(rand_short), struct.pack('<%dh' % len(rand_short), *rand_short)) if rand_short else b''
    width = 'H' if F >= 256 else 'B'
    out += _record_array(len(indices), struct.pack('<%d%s' % (len(indices), width), *indices)) if indices else b''
    if anim.notify:
        out += _record_array(len(anim.notify), b''.join(struct.pack('<If', 0, t) for _, t in anim.notify))
        for name, _ in anim.notify:
            out += _record_string(name)
    out += anim.tail
    with open(path, 'wb') as handle:
        handle.write(bytes(out))

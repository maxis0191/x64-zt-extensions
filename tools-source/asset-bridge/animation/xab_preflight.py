"""Bounded ZoneTool H1/IW7 .xab envelope and skeleton preflight (stdlib only).

This reads serialized metadata, never executes native code or decodes compressed
bone tracks. A pass is NOT a valid animation, retarget, fastfile or runtime proof.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

MAX_BYTES = 4 * 1024 * 1024
MAX_STRING = 4096


class Invalid(ValueError):
    pass


class Unsupported(Invalid):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def value(data, fmt, offset):
    return struct.unpack_from('<' + fmt, data, offset)[0]


class Reader:
    """Typed dump envelope; string aliases only, no native pointer dereference."""
    def __init__(self, data):
        require(len(data) <= MAX_BYTES, 'input exceeds 4 MiB preflight budget')
        self.data, self.pos, self.entries = data, 0, []

    def take(self, size):
        require(0 <= size <= len(self.data) - self.pos,
                f'truncated record at byte {self.pos}, need {size}')
        result = self.data[self.pos:self.pos + size]
        self.pos += size
        return result

    def number(self, fmt):
        return struct.unpack('<' + fmt, self.take(struct.calcsize('<' + fmt)))[0]

    def prefix(self, kind):
        actual = self.number('B')
        if actual == 9:
            index, element = self.number('I'), self.number('I')
            require(index < len(self.entries), 'alias refers to an absent/future record')
            old_kind, payload = self.entries[index]
            if kind == 6:
                require(old_kind == 6 and element == 0, 'invalid string alias')
                return payload
            raise Unsupported('blob aliases require a separate allocation/element-size audit')
        require(actual == kind, f'expected record type {kind}, got {actual}')
        require(self.number('B') == 1, 'required record is null or has invalid presence marker')
        return None

    def string(self):
        alias = self.prefix(6)
        if alias is not None:
            return alias
        end = self.data.find(b'\0', self.pos, self.pos + MAX_STRING + 1)
        require(end >= 0, 'unterminated/oversized string')
        raw = self.take(end - self.pos + 1)[:-1]
        try:
            name = raw.decode('ascii')
        except UnicodeDecodeError as exc:
            raise Unsupported('non-ASCII asset/bone/event name') from exc
        require(name and all(32 <= ord(c) < 127 for c in name), 'empty/control-character name')
        self.entries.append((6, name))
        return name

    def array(self, count, width):
        self.prefix(8)
        require(self.number('I') == count, 'array count differs from its header')
        payload = self.take(count * width)
        self.entries.append((8, payload))
        return payload

    def raw(self):
        self.prefix(10)
        payload = self.take(self.number('I'))
        self.entries.append((10, payload))
        return payload


def header(reader, game):
    require(game in ('h1', 'iw7'), 'explicit game must be h1 or iw7')
    blob = reader.array(1, 216 if game == 'h1' else 136)
    if game == 'iw7':
        offsets = [16, 24, 32, 40, 48, 56, 64]
        counts = [value(blob, 'H', i) for i in (108, 110, 112)]
        counts += [value(blob, 'I', 88), value(blob, 'I', 92), value(blob, 'H', 114), value(blob, 'I', 96)]
        frames, flags = value(blob, 'H', 116), blob[118]
        bones, notes = list(blob[119:129]), blob[129]
        names_ptr, notify_ptr, delta_ptr = (value(blob, 'Q', i) for i in (8, 72, 80))
        rate, frequency = value(blob, 'f', 100), value(blob, 'f', 104)
        extras = []
    else:
        # Offsets are derived from the x64 field order, not stale inline comments:
        # numframes spans 14..15, flags is 16, boneCount starts 17, frequency 52.
        offsets = [64, 72, 80, 88, 96, 104, 112]
        counts = [value(blob, 'H', i) for i in (8, 10, 12)]
        counts += [value(blob, 'I', 36), value(blob, 'I', 32), value(blob, 'I', 40), value(blob, 'I', 44)]
        frames, flags = value(blob, 'H', 14), blob[16]
        bones, notes = list(blob[17:27]), blob[29]
        names_ptr, notify_ptr, delta_ptr = (value(blob, 'Q', i) for i in (56, 120, 128))
        rate, frequency = value(blob, 'f', 48), value(blob, 'f', 52)
        extras = [name for name, present in (
            ('extra bone buckets', any(blob[27:29])), ('ikType', blob[31]),
            ('secondaryName', value(blob, 'Q', 136)),
            ('alternate weights/count', any(blob[144:146])),
            ('blendShapeCount', value(blob, 'H', 146)),
            ('blend-shape buffers', any(blob[152:200])),
            ('alternativeAnim', value(blob, 'Q', 200)),
            ('scripted viewmodel data', value(blob, 'Q', 208)),
        ) if present]
    require(math.isfinite(rate) and rate > 0, 'framerate must be finite and positive')
    require(math.isfinite(frequency) and frequency >= 0, 'frequency must be finite and nonnegative')
    require(bool(names_ptr) == bool(bones[9]), 'name pointer/count mismatch')
    require(bool(notify_ptr) == bool(notes), 'notify pointer/count mismatch')
    for offset, count in zip(offsets, counts):
        require(bool(value(blob, 'Q', offset)) == bool(count), 'data pointer/count mismatch')
    if extras:
        raise Unsupported('H1 extensions need explicit conversion: ' + ', '.join(extras))
    return dict(frames=frames, flags=flags, bone_counts=bones, notify_count=notes,
                counts=counts, delta=bool(delta_ptr), rate=rate, frequency=frequency)


def delta_parts(reader, frames):
    """Check dump lengths and key indices; compressed root values remain opaque."""
    ptrs = struct.unpack('<QQQ', reader.array(1, 24))
    width = 2 if frames >= 256 else 1
    report = {}
    for kind, pointer in zip(('translation', 'quat2', 'quat4'), ptrs):
        if not pointer:
            continue
        raw = reader.raw()
        base = 48 if kind == 'translation' else 24
        require(len(raw) >= base, 'short delta structure')
        size = value(raw, 'H', 0)
        require(size <= frames, 'delta key count exceeds frame domain')
        extra = (size + 1) * width if size else (4 if kind == 'quat4' else 0)
        require(len(raw) == base + extra, 'delta raw length differs from dumper contract')
        if size:
            index_offset = 40 if kind == 'translation' else 16
            indices = [value(raw, 'H' if width == 2 else 'B', index_offset + i * width)
                       for i in range(size + 1)]
            require(all(a < b for a, b in zip(indices, indices[1:])), 'delta indices must increase')
            require(indices[-1] <= frames, 'delta index exceeds frame domain')
            frames_ptr = value(raw, 'Q', 32 if kind == 'translation' else 8)
            require(frames_ptr != 0, 'animated delta has no frames buffer')
            if kind == 'translation':
                require(raw[2] in (0, 1), 'invalid smallTrans')
                key_width = 3 if raw[2] else 6
            else:
                key_width = 4 if kind == 'quat2' else 8
            require(len(reader.raw()) == (size + 1) * key_width, 'delta frame buffer length mismatch')
        report[kind] = {'key_count': size + 1, 'animated': bool(size)}
    return report


def inspect(data, game):
    reader = Reader(data)
    h = header(reader, game)
    name = reader.string()
    names = [reader.string() for _ in range(h['bone_counts'][9])]
    require(len(set(names)) == len(names), 'duplicate animation channel names')
    buffers = {}
    labels = ('dataByte', 'dataShort', 'dataInt', 'randomDataShort',
              'randomDataByte', 'randomDataInt', 'indices')
    widths = (1, 2, 4, 2, 1, 4, 2 if h['frames'] >= 256 else 1)
    for label, count, width in zip(labels, h['counts'], widths):
        if count:
            payload = reader.array(count, width)
            buffers[label] = {'count': count, 'bytes': len(payload),
                              'sha256': hashlib.sha256(payload).hexdigest()}
    notes = []
    if h['notify_count']:
        raw = reader.array(h['notify_count'], 8)
        for i in range(h['notify_count']):
            time = value(raw, 'f', i * 8 + 4)
            require(math.isfinite(time) and 0 <= time <= 1, 'notetrack time outside [0,1]')
            notes.append({'name': reader.string(), 'normalized_time': time})
    delta = delta_parts(reader, h['frames']) if h['delta'] else {}
    require(reader.pos == len(data), 'unparsed trailing bytes')
    return {'schema': 'iw7.animation-preflight/1', 'game': game,
            'evidence': 'serialized-envelope-only', 'runtime_verified': False,
            'compressed_tracks_decoded': False, 'retarget_verified': False,
            'sha256': hashlib.sha256(data).hexdigest(), 'input_bytes': len(data),
            'name': name, 'numframes': h['frames'], 'framerate': h['rate'],
            'frequency': h['frequency'], 'flags': h['flags'],
            'bone_counts': h['bone_counts'], 'channels': names,
            'notetracks': notes, 'buffers': buffers, 'delta_parts': delta,
            'root_motion_values_decoded': False,
            'h1_to_iw7_blockers': ([] if game == 'iw7' else [
                'Native header layout differs; never rename/copy this XAB into IW7.',
                'Compressed channel encoding and root-motion behavior need a measured roundtrip.',
            ]) + (['randomDataIntCount exceeds IW7 ushort'] if h['counts'][5] > 65535 else [])}


def bind_skeleton(report, skeleton):
    """Produce a parent-distance and exact-name channel plan, not a retarget."""
    require(isinstance(skeleton, dict), 'skeleton must be an object')
    require(skeleton.get('schema') == 'iw7.skeleton-binding/1', 'unsupported skeleton schema')
    require(type(skeleton.get('num_client_bones')) is int and skeleton['num_client_bones'] == 0,
            'client bones are outside this initial profile')
    bones = skeleton.get('bones')
    require(isinstance(bones, list) and 1 <= len(bones) <= 255, 'expected 1..255 regular bones')
    names, distances, roots, nonroot = [], [], 0, False
    for i, bone in enumerate(bones):
        require(isinstance(bone, dict) and set(bone) == {'name', 'parent'}, 'expected name and parent only')
        name, parent = bone['name'], bone['parent']
        require(isinstance(name, str) and 0 < len(name) <= MAX_STRING and
                all(32 <= ord(c) < 127 for c in name), 'invalid bone name')
        require(name not in names, 'duplicate skeleton bone')
        if parent is None:
            require(not nonroot, 'roots must precede all children')
            roots += 1
        else:
            nonroot = True
            require(type(parent) is int and 0 <= parent < i, 'parent must be an earlier bone index')
            distances.append(i - parent)
        names.append(name)
    missing = [name for name in report['channels'] if name not in names]
    require(not missing, 'unmapped animation channels: ' + ', '.join(missing))
    return {'evidence': 'exact-names-and-topology-only', 'num_bones': len(names),
            'num_root_bones': roots, 'parent_list_u8': distances,
            'channel_to_bone': [names.index(name) for name in report['channels']],
            'unanimated_bones': [name for name in names if name not in report['channels']],
            'bind_pose_verified': False, 'coordinate_basis_verified': False,
            'weights_verified': False}


def bounded_read(path):
    with Path(path).open('rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    require(len(data) <= MAX_BYTES, 'input exceeds 4 MiB preflight budget')
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('xab')
    parser.add_argument('--game', choices=('h1', 'iw7'), required=True)
    parser.add_argument('--skeleton', help='optional exact-name binding JSON; no retargeting')
    args = parser.parse_args(argv)
    try:
        report = inspect(bounded_read(args.xab), args.game)
        if args.skeleton:
            # Python's integer digit guard raises plain ValueError, not
            # JSONDecodeError. Catch it only around JSON parsing so an unrelated
            # implementation ValueError is not disguised as malformed input.
            try:
                skeleton = json.loads(bounded_read(args.skeleton))
            except ValueError as exc:
                raise Invalid('invalid skeleton JSON: ' + str(exc)) from exc
            report['skeleton_binding'] = bind_skeleton(report, skeleton)
        print(json.dumps({'status': 'envelope-pass', **report}, indent=2, allow_nan=False))
        return 0
    except (Invalid, OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        print(json.dumps({'status': 'unsupported' if isinstance(exc, Unsupported) else 'invalid',
                          'error': str(exc), 'runtime_verified': False}))
        return 2


if __name__ == '__main__':
    sys.exit(main())

"""Check the rotation key-index layout of ZoneTool IW7 .xab animations (stdlib only).

IW7 animations of 256 frames or more keep each rotation channel's key frame
indices inline in dataShort only below 64 keys. A larger channel keeps a lookup
table inline (the key at every 256th position, then the last key:
((keys - 2) >> 8) + 2 entries) and its full index list in XAnimParts::indices,
consumed channel after channel. Every long stock cp_zmb animation follows this.
Black Ops III keeps all indices inline; an unconverted large channel makes the
IW7 client read a null index list (access violation reading 0x200 when the
channel has 273 keys).

    python iw7_xanim_layout.py <file.xab> [...]

Prints one JSON report per file; exits 1 when any file breaks the layout.
Envelope parsing reuses ../animation/xab_preflight.py. A pass is a layout
check, not proof that the animation plays or looks right.
"""
import json
import os
import struct
import sys

LARGE_CHANNEL_KEYS = 64
ROTATION_BUCKETS = (1, 2)  # half and full quaternion channels with keys
LABELS = ('dataByte', 'dataShort', 'dataInt', 'randomDataShort', 'randomDataByte', 'randomDataInt', 'indices')


def table_size(frame_count):
    """Inline lookup entries of a large channel (frame_count = keys - 1)."""
    return ((frame_count - 1) >> 8) + 2


def check(frames, bone_counts, data_short, indices):
    """Walk the rotation channels; return a report with any layout errors."""
    errors = []
    channels = large = 0
    pos = used = 0
    if frames < 256:
        return {'long': False, 'errors': [], 'channels': 0, 'large_channels': 0}
    for bucket in ROTATION_BUCKETS:
        for _ in range(bone_counts[bucket]):
            channels += 1
            if pos >= len(data_short):
                errors.append('channel %d: dataShort ends before its frame count' % channels)
                return report(frames, channels, large, errors, pos, used, data_short, indices)
            n = data_short[pos] & 0xFFFF
            pos += 1
            keys = n + 1
            if n >= LARGE_CHANNEL_KEYS:
                large += 1
                size = table_size(n)
                table = data_short[pos:pos + size]
                pos += size
                seq = indices[used:used + keys]
                used += keys
                if len(seq) != keys:
                    errors.append('channel %d: %d keys but only %d entries left in indices' % (channels, keys, len(seq)))
                    continue
                expected = [seq[j * 256] for j in range(size - 1)] + [seq[-1]]
                if [v & 0xFFFF for v in table] != expected:
                    errors.append('channel %d: lookup table %s differs from indices %s' % (channels, table, expected))
                if seq[-1] != frames or any(a >= b for a, b in zip(seq, seq[1:])):
                    errors.append('channel %d: indices do not rise to frame %d' % (channels, frames))
            else:
                seg = [v & 0xFFFF for v in data_short[pos:pos + keys]]
                pos += keys
                if len(seg) != keys or seg[-1] != frames or any(a >= b for a, b in zip(seg, seg[1:])):
                    errors.append('channel %d: inline indices do not rise to frame %d' % (channels, frames))
    return report(frames, channels, large, errors, pos, used, data_short, indices)


def report(frames, channels, large, errors, pos, used, data_short, indices):
    return {'long': True, 'frames': frames, 'channels': channels, 'large_channels': large,
            'rotation_short_entries': pos, 'data_short_count': len(data_short),
            'rotation_indices': used, 'index_count': len(indices), 'errors': errors}


def load(path):
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(here, '..', 'animation'))
    import xab_preflight as xab
    data = xab.bounded_read(path) if hasattr(xab, 'bounded_read') else open(path, 'rb').read()
    reader = xab.Reader(data)
    head = xab.header(reader, 'iw7')
    name = reader.string()
    for _ in range(head['bone_counts'][9]):
        reader.string()
    widths = (1, 2, 4, 2, 1, 4, 2 if head['frames'] >= 256 else 1)
    formats = {1: 'B', 2: 'h', 4: 'i'}
    buffers = {}
    for label, count, width in zip(LABELS, head['counts'], widths):
        if count:
            payload = reader.array(count, width)
            fmt = ('H' if width == 2 else 'B') if label == 'indices' else formats[width]
            buffers[label] = list(struct.unpack('<%d%s' % (count, fmt), payload))
    return name, head, buffers


def main(argv=None):
    paths = (argv if argv is not None else sys.argv[1:])
    if not paths:
        print(__doc__.strip().splitlines()[0])
        return 2
    failed = False
    for path in paths:
        name, head, buffers = load(path)
        result = check(head['frames'], head['bone_counts'], buffers.get('dataShort', []), buffers.get('indices', []))
        result['name'] = name
        failed |= bool(result['errors'])
        print(json.dumps(result))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())

"""Independent exact-profile reader for future native original-probe XAB output.

No writer/preparer import. Refuses all profiles except the four-key quat4 probe.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys


def require(ok, message):
    if not ok:
        raise ValueError(message)


class ProbeReader:
    def __init__(self, data):
        require(len(data) <= 65536, '64 KiB original probe budget exceeded')
        self.data, self.offset = data, 0

    def take(self, count):
        require(count <= len(self.data) - self.offset, 'truncated probe')
        result = self.data[self.offset:self.offset + count]
        self.offset += count
        return result

    def array(self, count, width):
        require(self.take(2) == b'\x08\x01', 'expected present unaliased ARRAY')
        require(struct.unpack('<I', self.take(4))[0] == count, 'unexpected probe array count')
        return self.take(count * width)

    def exact_string(self, name):
        expected = b'\x06\x01' + name.encode('ascii') + b'\0'
        require(self.take(len(expected)) == expected, 'unexpected probe name/alias')


def read_probe(data, expected_frequency, *, ff_roundtrip=False):
    require(expected_frequency == 1.0, 'only the original probe frequency candidate 1 is supported')
    reader = ProbeReader(data)
    header = bytearray(reader.array(1, 136))
    for offset in (0, 8, 16, 24, 40, 72):
        require(struct.unpack_from('<Q', header, offset)[0] != 0, 'required probe pointer is null')
        header[offset:offset + 8] = bytes(8)
    expected = bytearray(136)
    struct.pack_into('<I', expected, 88, 16)
    struct.pack_into('<ffHH', expected, 100, 30.0, expected_frequency, 4, 1)
    struct.pack_into('<H', expected, 116, 30)
    expected[118] = 1
    expected[119:129] = bytes([1, 0, 1, 0, 0, 0, 0, 0, 2, 2])
    expected[129] = 1
    require(header == expected, 'probe header/profile differs, including padding or optional streams')
    reader.exact_string('paris_original_probe_bend')
    reader.exact_string('tag_origin')
    reader.exact_string('tag_probe')
    frames = list(reader.array(4, 1))
    require(frames == [0, 10, 20, 30], 'probe key frames changed')
    require(struct.unpack('<H', reader.array(1, 2))[0] == 3, 'probe key-count-minus-one changed')
    packed = list(struct.unpack('<16h', reader.array(16, 2)))
    # Independently fixed reference samples, not values imported from generator.
    require(packed == [0, 0, 0, 32767, 12539, 0, 0, 30272,
                       -12539, 0, 0, 30272, 0, 0, 0, 32767], 'probe packed rotation changed')
    raw_notes = reader.array(1, 8)
    note_id, note_time = struct.unpack('<If', raw_notes)
    # XAnim::prepare interns the note name into the zone script-string table;
    # a loaded FF can assign a different nonzero ID. The following serialized
    # string remains the exact semantic identity in both modes.
    require(note_time == 0.5 and (note_id > 0 if ff_roundtrip else note_id == 3),
            'probe note identity/time changed')
    reader.exact_string('probe_contact')
    require(reader.offset == len(data), 'trailing probe data')
    samples = []
    for i, target in enumerate([0, 45, -45, 0]):
        q = [v / 32767.0 for v in packed[i * 4:i * 4 + 4]]
        length = math.sqrt(sum(v * v for v in q))
        require(abs(length - 1) < 0.0001, 'probe quaternion not near unit')
        angle = math.degrees(2 * math.atan2(q[0], q[3]))
        require(abs(angle - target) < 0.01, 'probe angle outside 0.01 degree budget')
        samples.append({'frame': frames[i], 'quat_xyzw_div32767': q,
                        'x_degrees': angle, 'norm': length})
    return {'schema': 'iw7.original-probe-readback/1', 'status': 'original-probe-data-pass',
            'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
            'decoded_profile': 'four-key-int16-quat4-only', 'samples': samples,
            'root_rotation': 'identity', 'translations': 'no authored translation tracks',
            'notetrack': {'name': 'probe_contact', 'normalized_time': 0.5, 'script_string_id': note_id},
            'readback_scope': 'ff-redump-profile' if ff_roundtrip else 'original-native-writer-profile',
            'frequency_input': expected_frequency, 'frequency_runtime_verified': False,
            'general_xanim_decoder': False, 'runtime_verified': False,
            'input_provenance': ('must be bound to actual FF build/verify/dump receipts separately' if ff_roundtrip else
                                 'must be bound to actual native writer receipt separately')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('xab')
    parser.add_argument('--expected-frequency', type=float, required=True)
    parser.add_argument('--ff-roundtrip', action='store_true',
                        help='Accept a remapped nonzero note script-string ID; exact note name/time and all other fields stay required')
    args = parser.parse_args()
    try:
        with Path(args.xab).open('rb') as stream:
            payload = stream.read(65537)
        print(json.dumps(read_probe(payload, args.expected_frequency, ff_roundtrip=args.ff_roundtrip), indent=2, allow_nan=False))
    except (ValueError, OSError, struct.error) as exc:
        print(json.dumps({'status': 'invalid-probe', 'error': str(exc)}))
        sys.exit(2)

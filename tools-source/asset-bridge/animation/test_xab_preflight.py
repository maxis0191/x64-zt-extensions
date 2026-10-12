"""Synthetic dump oracle and failure corpus. No game or native dependencies."""
import copy
import json
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile
import unittest

import xab_preflight as preflight


def array(blob, count=1):
    return b'\x08\x01' + struct.pack('<I', count) + blob


def raw(blob):
    return b'\x0a\x01' + struct.pack('<I', len(blob)) + blob


def string(text):
    return b'\x06\x01' + text.encode('ascii') + b'\0'


def synthetic(game='iw7', frames=30, notify_time=0.5, delta=None, channels=None):
    """Independent source-shaped binary fixture; does not call production code."""
    channels = channels if channels is not None else ['tag_origin', 'tag_probe']
    header = bytearray(136 if game == 'iw7' else 216)
    def put(offset, fmt, number):
        struct.pack_into('<' + fmt, header, offset, number)
    put(0, 'Q', 0x1010)
    bones = [len(channels), 0, 0, 0, 0, 0, 0, 0, len(channels), len(channels)]
    if game == 'iw7':
        put(8, 'Q', 1 if channels else 0)
        put(72, 'Q', 2)
        put(80, 'Q', 3 if delta else 0)
        put(100, 'f', 30)
        put(104, 'f', 1)
        put(116, 'H', frames)
        header[118] = 2 if delta else 1
        header[119:129] = bytes(bones)
        header[129] = 1
    else:
        put(14, 'H', frames)
        header[16] = 2 if delta else 1
        header[17:27] = bytes(bones)
        header[29] = 1
        put(48, 'f', 30)
        put(52, 'f', 1)
        put(56, 'Q', 1 if channels else 0)
        put(120, 'Q', 2)
        put(128, 'Q', 3 if delta else 0)
    tail = string('original_probe') + b''.join(string(n) for n in channels)
    tail += array(struct.pack('<If', 900, notify_time)) + string('probe_contact')
    if delta:
        animated = delta.endswith('_keys')
        kind = delta.removesuffix('_keys')
        ptrs = [0, 0, 0]
        ptrs[{'translation': 0, 'quat2': 1, 'quat4': 2}[kind]] = 0x5000
        tail += array(struct.pack('<QQQ', *ptrs))
        base = 48 if kind == 'translation' else 24
        width = 2 if frames >= 256 else 1
        extra = 2 * width if animated else (4 if kind == 'quat4' else 0)
        part = bytearray(base + extra)
        struct.pack_into('<H', part, 0, 1 if animated else 0)
        if animated:
            pointer_offset, index_offset = (32, 40) if kind == 'translation' else (8, 16)
            struct.pack_into('<Q', part, pointer_offset, 0x6000)
            struct.pack_into('<2H' if width == 2 else '<2B', part, index_offset, 0, frames)
            if kind == 'translation':
                part[2] = 1
        tail += raw(part)
        if animated:
            tail += raw(bytes(2 * {'translation': 3, 'quat2': 4, 'quat4': 8}[kind]))
    return array(header) + tail


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.rig = json.loads((Path(__file__).parent / 'fixtures/two-bone.skeleton.json').read_text())

    def test_same_metadata_different_abis(self):
        h1 = preflight.inspect(synthetic('h1'), 'h1')
        iw7 = preflight.inspect(synthetic(), 'iw7')
        for key in ('channels', 'notetracks', 'numframes', 'framerate', 'frequency', 'bone_counts'):
            self.assertEqual(h1[key], iw7[key])
        self.assertTrue(h1['h1_to_iw7_blockers'])
        self.assertFalse(iw7['runtime_verified'])
        self.assertFalse(iw7['compressed_tracks_decoded'])

    def test_explicit_game_layout_cannot_be_swapped(self):
        for data, game in ((synthetic('h1'), 'iw7'), (synthetic(), 'h1')):
            with self.assertRaises(preflight.Invalid):
                preflight.inspect(data, game)

    def test_exact_binding_preserves_animation_channel_order(self):
        report = preflight.inspect(synthetic(channels=['tag_probe', 'tag_origin']), 'iw7')
        binding = preflight.bind_skeleton(report, self.rig)
        self.assertEqual(binding['channel_to_bone'], [1, 0])
        self.assertEqual(binding['parent_list_u8'], [1])
        self.assertFalse(binding['bind_pose_verified'])

    def test_missing_case_changed_and_duplicate_channels_refused(self):
        for names in (['missing'], ['TAG_ORIGIN'], ['tag_origin', 'tag_origin']):
            with self.assertRaises(preflight.Invalid):
                preflight.bind_skeleton(preflight.inspect(synthetic(channels=names), 'iw7'), self.rig)

    def test_bad_topology_and_client_bones_refused(self):
        for parent in (1, 4, -1, True, '0'):
            rig = copy.deepcopy(self.rig)
            rig['bones'][1]['parent'] = parent
            with self.assertRaises(preflight.Invalid):
                preflight.bind_skeleton({'channels': []}, rig)
        for changed in ({'num_client_bones': 1}, {'num_client_bones': False}, {'bones': self.rig['bones'] * 128},
                        {'bones': []}, {'bones': [{'name': 'x', 'parent': 0}]}):
            with self.assertRaises(preflight.Invalid):
                preflight.bind_skeleton({'channels': []}, {**self.rig, **changed})

    def test_noncontiguous_roots_refused(self):
        self.rig['bones'].append({'name': 'late_root', 'parent': None})
        with self.assertRaises(preflight.Invalid):
            preflight.bind_skeleton({'channels': []}, self.rig)

    def test_notify_bounds_finite_and_endpoints(self):
        for time in (-0.01, 1.01, float('nan'), float('inf')):
            with self.assertRaises(preflight.Invalid):
                preflight.inspect(synthetic(notify_time=time), 'iw7')
        for time in (0, 1):
            self.assertEqual(preflight.inspect(synthetic(notify_time=time), 'iw7')['notetracks'][0]['normalized_time'], time)

    def test_delta_forms_and_index_width_boundary(self):
        for game in ('h1', 'iw7'):
            for frames in (255, 256):
                for kind in ('translation', 'quat2', 'quat4'):
                    for suffix in ('', '_keys'):
                        with self.subTest(game=game, frames=frames, kind=kind, suffix=suffix):
                            result = preflight.inspect(synthetic(game, frames=frames, delta=kind + suffix), game)
                            self.assertEqual(result['delta_parts'][kind]['key_count'], 2 if suffix else 1)
                            self.assertFalse(result['root_motion_values_decoded'])

    def test_truncated_at_every_byte_refused(self):
        for game in ('h1', 'iw7'):
            data = synthetic(game, frames=256, delta='translation_keys')
            for length in range(len(data)):
                with self.assertRaises(preflight.Invalid, msg=f'{game} byte {length}'):
                    preflight.inspect(data[:length], game)

    def test_trailing_data_refused(self):
        with self.assertRaises(preflight.Invalid):
            preflight.inspect(synthetic() + b'junk', 'iw7')

    def test_delta_semantic_length_and_key_failures(self):
        original = synthetic(frames=256, delta='translation_keys')
        part_start = original.index(b'\x0a\x01') + 6
        for offset, fmt, number in ((0, 'H', 300), (2, 'B', 3), (32, 'Q', 0),
                                    (40, 'H', 256), (42, 'H', 257)):
            blob = bytearray(original)
            struct.pack_into('<' + fmt, blob, part_start + offset, number)
            with self.assertRaises(preflight.Invalid):
                preflight.inspect(blob, 'iw7')
        blob = bytearray(original)
        struct.pack_into('<I', blob, part_start - 4, 50)
        with self.assertRaises(preflight.Invalid):
            preflight.inspect(blob, 'iw7')

    def test_max_regular_bones_and_parent_distance(self):
        rig = {'schema': 'iw7.skeleton-binding/1', 'num_client_bones': 0,
               'bones': [{'name': 'root', 'parent': None}] +
                        [{'name': f'b{i}', 'parent': 0} for i in range(1, 255)]}
        result = preflight.bind_skeleton({'channels': ['b254', 'root']}, rig)
        self.assertEqual(result['parent_list_u8'][-1], 254)
        self.assertEqual(result['channel_to_bone'], [254, 0])

    def test_presence_markers_are_exact(self):
        for presence in (0, 2, 255):
            blob = bytearray(synthetic())
            blob[1] = presence
            with self.assertRaises(preflight.Invalid):
                preflight.inspect(blob, 'iw7')

    def test_count_and_pointer_inconsistency_refused(self):
        for offset, fmt, number in ((16, 'Q', 1), (108, 'H', 1), (8, 'Q', 0), (72, 'Q', 0)):
            blob = bytearray(synthetic())
            struct.pack_into('<' + fmt, blob, 6 + offset, number)
            with self.assertRaises(preflight.Invalid):
                preflight.inspect(blob, 'iw7')

    def test_regular_data_arrays_and_indices_boundary(self):
        for frames, width in ((255, 1), (256, 2)):
            blob = bytearray(synthetic(frames=frames))
            struct.pack_into('<Q', blob, 6 + 16, 1)
            struct.pack_into('<H', blob, 6 + 108, 3)
            struct.pack_into('<Q', blob, 6 + 64, 1)
            struct.pack_into('<I', blob, 6 + 96, 2)
            insert = blob.index(b'\x08\x01', 6 + 136)
            blob[insert:insert] = array(b'ABC', 3) + array(bytes(2 * width), 2)
            report = preflight.inspect(blob, 'iw7')
            self.assertEqual(report['buffers']['dataByte']['bytes'], 3)
            self.assertEqual(report['buffers']['indices']['bytes'], 2 * width)
            struct.pack_into('<I', blob, insert + 2, 0xffffffff)
            with self.assertRaises(preflight.Invalid):
                preflight.inspect(blob, 'iw7')

    def test_h1_extensions_are_not_silently_dropped(self):
        for offset, fmt in ((27, 'B'), (31, 'B'), (136, 'Q'), (144, 'B'), (146, 'H'),
                            (152, 'Q'), (160, 'Q'), (200, 'Q'), (208, 'Q')):
            blob = bytearray(synthetic('h1'))
            struct.pack_into('<' + fmt, blob, 6 + offset, 1)
            with self.assertRaises(preflight.Unsupported):
                preflight.inspect(blob, 'h1')

    def test_alias_references_do_not_dereference_pointers(self):
        blob = synthetic().replace(string('probe_contact'), b'\x09' + struct.pack('<II', 2, 0))
        self.assertEqual(preflight.inspect(blob, 'iw7')['notetracks'][0]['name'], 'tag_origin')
        for index, element in ((900, 0), (0, 0), (2, 1)):
            bad = synthetic().replace(string('probe_contact'), b'\x09' + struct.pack('<II', index, element))
            with self.assertRaises(preflight.Invalid):
                preflight.inspect(bad, 'iw7')

    def test_blob_alias_reports_unsupported(self):
        blob = synthetic()
        note = blob.index(array(struct.pack('<If', 900, 0.5)))
        blob = blob[:note] + b'\x09' + struct.pack('<II', 0, 0) + blob[note + 14:]
        with self.assertRaises(preflight.Unsupported):
            preflight.inspect(blob, 'iw7')

    def test_empty_control_and_oversized_names_refused(self):
        for token in (b'\0', b'bad\x01name\0', b'A' * 4097 + b'\0'):
            with self.assertRaises(preflight.Invalid):
                preflight.inspect(synthetic().replace(b'original_probe\0', token), 'iw7')

    def test_finite_rate(self):
        for rate in (0, -1, float('inf'), float('nan')):
            blob = bytearray(synthetic())
            struct.pack_into('<f', blob, 6 + 100, rate)
            with self.assertRaises(preflight.Invalid):
                preflight.inspect(blob, 'iw7')

    def test_budget_before_decode(self):
        with self.assertRaises(preflight.Invalid):
            preflight.inspect(bytes(preflight.MAX_BYTES + 1), 'iw7')

    def test_small_deterministic_mutation_corpus_no_unhandled_exceptions(self):
        rng = random.Random(27016)
        seed = synthetic(delta='quat4_keys')
        for _ in range(500):
            blob = bytearray(seed)
            index = rng.randrange(len(blob))
            blob[index] ^= rng.randrange(1, 256)
            try:
                result = preflight.inspect(blob, 'iw7')
            except preflight.Invalid:
                continue
            # Opaque compressed bytes/pointers may mutate without invalidating an envelope.
            self.assertFalse(result['compressed_tracks_decoded'])

    def test_cli_exit_codes_and_no_file_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'probe.xab'
            source.write_bytes(synthetic())
            cmd = [sys.executable, '-B', str(Path(preflight.__file__)), str(source), '--game', 'iw7']
            run = subprocess.run(cmd, capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertEqual(json.loads(run.stdout)['status'], 'envelope-pass')
            self.assertEqual(source.read_bytes(), synthetic())
            rig = Path(tmp) / 'rig.json'
            rig.write_text(json.dumps(self.rig))
            bound = subprocess.run(cmd + ['--skeleton', str(rig)], capture_output=True, text=True, check=False)
            self.assertEqual(bound.returncode, 0, bound.stdout + bound.stderr)
            self.assertEqual(json.loads(bound.stdout)['skeleton_binding']['channel_to_bone'], [0, 1])
            rig.write_text('{')
            invalid_rig = subprocess.run(cmd + ['--skeleton', str(rig)], capture_output=True, text=True, check=False)
            self.assertEqual(invalid_rig.returncode, 2)
            self.assertEqual(json.loads(invalid_rig.stdout)['status'], 'invalid')
            source.write_bytes(b'invalid')
            run = subprocess.run(cmd, capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 2)
            self.assertEqual(json.loads(run.stdout)['status'], 'invalid')

    def test_cli_hostile_integer_json_is_structured_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, rig = Path(tmp) / 'probe.xab', Path(tmp) / 'rig.json'
            source.write_bytes(synthetic())
            rig.write_text('{"num_client_bones":' + '9' * 5000 + '}')
            cmd = [sys.executable, '-B', '-X', 'int_max_str_digits=4300',
                   str(Path(preflight.__file__)), str(source), '--game', 'iw7', '--skeleton', str(rig)]
            run = subprocess.run(cmd, capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
            self.assertEqual(json.loads(run.stdout)['status'], 'invalid')
            self.assertIn('invalid skeleton JSON', json.loads(run.stdout)['error'])
            self.assertNotIn('Traceback', run.stderr)


if __name__ == '__main__':
    unittest.main()

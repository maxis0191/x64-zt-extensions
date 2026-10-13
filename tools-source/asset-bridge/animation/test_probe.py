"""Tiny original-only codec/readback tests; never a native serializer witness."""
import copy
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import prepare_probe
import read_probe
import xab_preflight


def independent_native_shape(frequency=1.0):
    """Synthetic MSVC-layout envelope, no generator/production serializer call."""
    def array(data, count):
        return b'\x08\x01' + struct.pack('<I', count) + data
    def string(name):
        return b'\x06\x01' + name.encode() + b'\0'
    header = bytearray(136)
    for offset in (0, 8, 16, 24, 40, 72):
        struct.pack_into('<Q', header, offset, 0x1000 + offset)
    struct.pack_into('<I', header, 88, 16)
    struct.pack_into('<ffHH', header, 100, 30, frequency, 4, 1)
    struct.pack_into('<H', header, 116, 30)
    header[118] = 1
    header[119:129] = bytes([1, 0, 1, 0, 0, 0, 0, 0, 2, 2])
    header[129] = 1
    return (array(header, 1) + string('paris_original_probe_bend') + string('tag_origin') + string('tag_probe') +
            array(bytes([0, 10, 20, 30]), 4) + array(struct.pack('<H', 3), 1) +
            array(struct.pack('<16h', 0, 0, 0, 32767, 12539, 0, 0, 30272,
                              -12539, 0, 0, 30272, 0, 0, 0, 32767), 16) +
            array(struct.pack('<If', 3, 0.5), 1) + string('probe_contact'))


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.clip = json.loads((prepare_probe.HERE / 'fixtures/probe-clip.json').read_text())

    def test_authoring_quantization_matches_independent_words(self):
        encoded = prepare_probe.compile_original(self.clip)
        self.assertEqual(encoded['data_byte'], [0, 10, 20, 30])
        self.assertEqual(encoded['data_short'], [3])
        self.assertEqual(encoded['random_data_short'], [0, 0, 0, 32767, 12539, 0, 0, 30272,
                                                       -12539, 0, 0, 30272, 0, 0, 0, 32767])

    def test_unknown_authoring_profiles_refused(self):
        for key, changed in (('frequency', 2), ('root_motion', True), ('framerate', 60),
                             ('channels', ['root', 'arm']), ('loop', False)):
            clip = copy.deepcopy(self.clip)
            clip[key] = changed
            with self.assertRaises(ValueError):
                prepare_probe.compile_original(clip)

    def test_reader_decodes_actual_fields_without_writer_import(self):
        result = read_probe.read_probe(independent_native_shape(), 1.0)
        self.assertFalse(result['runtime_verified'])
        self.assertFalse(result['general_xanim_decoder'])
        self.assertEqual([k['frame'] for k in result['samples']], [0, 10, 20, 30])
        self.assertAlmostEqual(result['samples'][1]['x_degrees'], 45, delta=0.01)
        source = Path(read_probe.__file__).read_text()
        self.assertNotRegex(source, r'^import prepare_probe|^from prepare_probe', msg='reader must stay independent')

    def test_generic_envelope_also_reads_probe(self):
        result = xab_preflight.inspect(independent_native_shape(), 'iw7')
        self.assertEqual(result['buffers']['randomDataShort']['count'], 16)
        self.assertEqual(result['notetracks'][0]['normalized_time'], 0.5)

    def test_ff_redump_allows_only_explicit_script_id_remap(self):
        original = independent_native_shape()
        offset = original.rfind(struct.pack('<If', 3, 0.5))
        for note_id in (1, 12345, 0xffffffff):
            data = bytearray(original)
            struct.pack_into('<I', data, offset, note_id)
            with self.assertRaises(ValueError):
                read_probe.read_probe(data, 1.0)
            result = read_probe.read_probe(data, 1.0, ff_roundtrip=True)
            self.assertEqual(result['notetrack']['script_string_id'], note_id)
            self.assertEqual(result['notetrack']['name'], 'probe_contact')
            self.assertFalse(result['runtime_verified'])

    def test_ff_redump_keeps_note_time_name_and_zero_id_guards(self):
        original = independent_native_shape()
        offset = original.rfind(struct.pack('<If', 3, 0.5))
        for note_id, time in ((0, 0.5), (12345, 0.25), (12345, float('nan'))):
            data = bytearray(original)
            struct.pack_into('<If', data, offset, note_id, time)
            with self.assertRaises(ValueError):
                read_probe.read_probe(data, 1.0, ff_roundtrip=True)
        with self.assertRaises(ValueError):
            read_probe.read_probe(original.replace(b'probe_contact', b'probe_changed'), 1.0, ff_roundtrip=True)

    def test_ff_redump_cli_requires_opt_in(self):
        data = bytearray(independent_native_shape())
        struct.pack_into('<I', data, data.rfind(struct.pack('<If', 3, 0.5)), 12345)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'synthetic-redump.xab'
            path.write_bytes(data)
            command = [sys.executable, '-B', str(Path(read_probe.__file__)), str(path), '--expected-frequency', '1']
            refused = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(refused.returncode, 2)
            accepted = subprocess.run(command + ['--ff-roundtrip'], capture_output=True, text=True, check=False)
            self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
            self.assertEqual(json.loads(accepted.stdout)['readback_scope'], 'ff-redump-profile')

    def test_every_truncation_fails(self):
        data = independent_native_shape()
        for length in range(len(data)):
            with self.assertRaises(ValueError):
                read_probe.read_probe(data[:length], 1.0)

    def test_all_nonpointer_header_bytes_are_guarded(self):
        mutable_pointer_bytes = {i for offset in (0, 8, 16, 24, 40, 72) for i in range(offset, offset + 8)}
        for offset in set(range(136)) - mutable_pointer_bytes:
            data = bytearray(independent_native_shape())
            data[6 + offset] ^= 1
            with self.assertRaises(ValueError, msg=f'offset {offset}'):
                read_probe.read_probe(data, 1.0)

    def test_null_required_pointers_refused(self):
        for offset in (0, 8, 16, 24, 40, 72):
            data = bytearray(independent_native_shape())
            data[6 + offset:6 + offset + 8] = bytes(8)
            with self.assertRaises(ValueError):
                read_probe.read_probe(data, 1.0)

    def test_every_payload_byte_mutation_fails(self):
        original = independent_native_shape()
        for i in range(142, len(original)):
            data = bytearray(original)
            data[i] ^= 1
            with self.assertRaises(ValueError, msg=f'payload offset {i}'):
                read_probe.read_probe(data, 1.0)

    def test_frequency_not_inferred_or_silently_replaced(self):
        for number in (0, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                read_probe.read_probe(independent_native_shape(), number)
        with self.assertRaises(ValueError):
            read_probe.read_probe(independent_native_shape(2.0), 1.0)
        with self.assertRaises(ValueError):
            read_probe.read_probe(independent_native_shape(2.0), 2.0)

    def test_frequency_candidate_matches_two_bounded_header_observations(self):
        evidence = json.loads((prepare_probe.HERE / 'frequency-observations.json').read_text())
        self.assertEqual(evidence['total_bytes_read'], 284)
        for item in evidence['observations']:
            ratio = struct.unpack('<f', struct.pack('<f', item['framerate'] / item['numframes']))[0]
            self.assertEqual(ratio, item['frequency'])
            self.assertEqual(bool(item['flags'] & 1), item['loop'])
        self.assertFalse(evidence['runtime_verified'])

    def test_output_budget_and_trailing_bytes(self):
        for data in (bytes(65537), independent_native_shape() + b'\0'):
            with self.assertRaises(ValueError):
                read_probe.read_probe(data, 1.0)

    def test_native_dump_method_extracted_without_body_rewrite(self):
        body = '\tvoid xanim_parts::dump(XAnimParts* asset)\n\t{\n\t\tdump.dump_single(asset);\n\t}\n'
        generated = prepare_probe.dump_method(('namespace zonetool::iw7\n{\n' + body + '}\n').encode())
        self.assertIn(body.encode(), generated)
        no_final_lf = prepare_probe.dump_method(('namespace zonetool::iw7\n{\n' + body + '}').encode())
        self.assertEqual(generated, no_final_lf)
        with self.assertRaises(ValueError):
            prepare_probe.dump_method(b'changed method')

    def test_source_contract_hashes_are_well_formed(self):
        contract = json.loads((prepare_probe.HERE / 'probe-source-contract.json').read_text())
        for hash_value in list(contract['zonetool_sha256'].values()) + [r['sha256'] for r in contract['references']]:
            self.assertRegex(hash_value, r'^[a-f0-9]{64}$')
        self.assertLess(sum(r['bytes'] for r in contract['references']), 150000)

    def test_prepare_rejects_existing_output_before_source_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(prepare_probe, 'check_sources') as check:
                with self.assertRaises(ValueError):
                    prepare_probe.prepare(Path(tmp), Path(tmp), Path(tmp))
                check.assert_not_called()

    def test_cli_actual_exit_success_and_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'native-shape.xab'
            path.write_bytes(independent_native_shape())
            cmd = [sys.executable, '-B', str(Path(read_probe.__file__)), str(path), '--expected-frequency', '1']
            run = subprocess.run(cmd, capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertEqual(json.loads(run.stdout)['status'], 'original-probe-data-pass')
            path.write_bytes(path.read_bytes() + b'\0')
            run = subprocess.run(cmd, capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 2)
            self.assertEqual(json.loads(run.stdout)['status'], 'invalid-probe')


if __name__ == '__main__':
    unittest.main()

"""Light synthetic reader/contract tests. NO native dump is produced or claimed."""
import argparse
import json
from pathlib import Path
import struct
import tempfile
import unittest

import generate
import inspect_dump as reader
import inspect_fixture
import prepare_dump
import prepare_native

SOURCE = None


def synthetic_pair():
    """Test-only stream builder. Never used to deliver IW7 assets or by C++."""
    h1_model, h1_surface = generate.build_payloads().values()
    _, mr = inspect_fixture.inspect_model(h1_model)
    _, sr = inspect_fixture.inspect_surface(h1_surface)
    def copied(data, records, label, width, count):
        return generate.array(reader.source_array(data, records, label, width, count), count)
    m = bytearray(736)
    m[8:15] = bytes((0, 1, 0, 1, 0, 6, 1))
    struct.pack_into('<3B', m, 20, 1, 1, 0)
    struct.pack_into('<Hf', m, 26, 1, 1.)
    m[40:68] = h1_model[550:578]
    struct.pack_into('<I', m, 120, 0x80000000)
    struct.pack_into('<fHH', m, 224, 1000., 1, 0)
    struct.pack_into('<I', m, 240, 0x80000000)
    for i, offset in enumerate((0, 152, 184, 192, 216, 232, 616, 624)):
        struct.pack_into('<Q', m, offset, 0x10000 + i * 0x100)
    m[704] = m[720] = 255
    xmb = generate.array(m, 1) + generate.named(6, reader.MODEL) + generate.named(6, 'tag_origin')
    xmb += generate.array() * 3
    xmb += copied(h1_model, mr, 'classification', 1, 1) + copied(h1_model, mr, 'base_mat', 32, 1)
    xmb += generate.array() * 3
    xmb += copied(h1_model, mr, 'bone_info', 28, 1) + copied(h1_model, mr, 'mip_radius', 2, 1)
    xmb += generate.array(struct.pack('<Q', 0x20000), 1)
    xmb += generate.named(7, reader.MATERIAL) + generate.named(7, reader.SURFACE)
    xmb += generate.named(7) * 9 + generate.array() * 3
    group = bytearray(56)
    struct.pack_into('<QQH', group, 0, 0x30000, 0x40000, 1)
    struct.pack_into('<I', group, 20, 0x80000000)
    surface = bytearray(256)
    struct.pack_into('<HHHBB', surface, 0, 0x80, 24, 12, 1, 0)
    for offset in (32, 40, 72):
        struct.pack_into('<Q', surface, offset, 0x50000 + offset)
    struct.pack_into('<I', surface, 224, 0x80000000)
    vertices = bytearray(reader.source_array(h1_surface, sr, 'vertices', 32, 24))
    for i in range(24):
        struct.pack_into('<I', vertices, i * 32 + 12, 0x01FE0100)
    xsb = generate.array(group, 1) + generate.named(6, reader.SURFACE) + generate.array(surface, 1)
    xsb += generate.array(vertices, 24) + copied(h1_surface, sr, 'triangles', 6, 12)
    xsb += copied(h1_surface, sr, 'rigid_lists', 16, 1) + b'\x0a\x00' * 4
    return bytes(xmb), bytes(xsb), h1_model, h1_surface


class ReadbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = synthetic_pair()

    def test_original_profile_is_data_proof_only(self):
        report = reader.inspect_pair(*self.inputs)
        self.assertEqual(report['vertices_checked'], 24)
        for flag in ('bone_engine_token_resolved', 'native_provenance_verified', 'ff_built',
                     'render_verified', 'material_complete', 'lod_named_reference_linked'):
            self.assertFalse(report[flag])

    def test_every_output_truncation_and_trailing_bytes_fail(self):
        for index in (0, 1):
            for length in range(len(self.inputs[index])):
                with self.subTest(file=index, truncated=length):
                    values = list(self.inputs); values[index] = values[index][:length]
                    with self.assertRaises(ValueError): reader.inspect_pair(*values)
            values = list(self.inputs); values[index] += b'\0'
            with self.assertRaises(ValueError): reader.inspect_pair(*values)

    def test_model_flags_pointers_bounds_and_dependencies_fail(self):
        # Header fields include optional GPU/physics pointers, counts, LOD and
        # sentinel fields: retain raw pointer values only as presence, not IDs.
        for offset in (8, 9, 11, 13, 14, 16, 20, 21, 24, 26, 28, 40, 44, 56, 88,
                       120, 160, 200, 224, 240, 280, 608, 632, 704, 720, 728):
            with self.subTest(offset=offset):
                changed = bytearray(self.inputs[0]); changed[6 + offset] ^= 1
                with self.assertRaises(ValueError): reader.inspect_pair(bytes(changed), *self.inputs[1:])
        for name in (reader.MODEL, 'tag_origin', reader.MATERIAL, reader.SURFACE):
            changed = self.inputs[0].replace(name.encode() + b'\0', b'x' + name.encode()[1:] + b'\0')
            with self.assertRaises(ValueError): reader.inspect_pair(changed, *self.inputs[1:])

    def test_surface_streams_geometry_topology_and_root_fail(self):
        _, sr = inspect_fixture.inspect_surface(self.inputs[3])
        records = reader.read_surface(self.inputs[1], self.inputs[3], sr)
        mutations = [(records['surfaces'] + 6 + n) for n in (0, 2, 4, 6, 8, 24, 48, 80, 104, 128, 144, 192, 224)]
        mutations += [records['vertices'] + 6 + n for n in (0, 12, 16, 20, 24, 28, 23 * 32)]
        mutations += [records['triangles'] + 6, records['rigid_lists'] + 6,
                      records['blend'] + 1, records['lmap'] + 1]
        for offset in mutations:
            with self.subTest(offset=offset):
                changed = bytearray(self.inputs[1]); changed[offset] ^= 1
                with self.assertRaises(ValueError): reader.inspect_pair(self.inputs[0], bytes(changed), *self.inputs[2:])

    def test_required_pointer_presence_not_machine_address_identity(self):
        for offset in (0, 152, 184, 192, 216, 232, 616, 624):
            changed = bytearray(self.inputs[0]); changed[6 + offset:14 + offset] = bytes(8)
            with self.assertRaises(ValueError): reader.inspect_pair(bytes(changed), *self.inputs[1:])
        _, sr = inspect_fixture.inspect_surface(self.inputs[3])
        records = reader.read_surface(self.inputs[1], self.inputs[3], sr)
        for offset in (6, 14, *(records['surfaces'] + 6 + n for n in (32, 40, 72))):
            changed = bytearray(self.inputs[1]); changed[offset:offset + 8] = bytes(8)
            with self.assertRaises(ValueError): reader.inspect_pair(self.inputs[0], bytes(changed), *self.inputs[2:])
        changed = bytearray(self.inputs[0]); struct.pack_into('<Q', changed, 6, 0xDEADBEEF)
        self.assertEqual(reader.inspect_pair(bytes(changed), *self.inputs[1:])['status'],
                         'original-h1-iw7-dump-profile-pass')

    def test_typed_names_only_alias_known_matching_entries(self):
        data = generate.named(6, 'tag_origin') + b'\x09' + struct.pack('<II', 0, 0)
        r = reader.Reader(data)
        r.name('first', 6, 'tag_origin'); r.name('alias', 6, 'tag_origin'); r.finish()
        for entry, index, kind, expected in ((1, 0, 6, 'tag_origin'), (0, 1, 6, 'tag_origin'),
                                             (0, 0, 7, 'tag_origin'), (0, 0, 6, 'other'), (0, 0, 6, None)):
            r = reader.Reader(generate.named(6, 'tag_origin') + b'\x09' + struct.pack('<II', entry, index))
            r.name('first', 6, 'tag_origin')
            with self.assertRaises(ValueError): r.name('alias', kind, expected)
        r = reader.Reader(generate.array(b'1234', 1) + b'\x09' + struct.pack('<II', 0, 0))
        r.array('first', 4, 1)
        with self.assertRaises(ValueError): r.array('alias', 4, 1)

    def test_original_source_and_size_are_exact(self):
        values = list(self.inputs); values[2] = values[2][:-1] + b'x'
        with self.assertRaises(ValueError): reader.inspect_pair(*values)
        with self.assertRaises(ValueError): reader.Reader(b'x' * 65537)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'large'; path.write_bytes(b'x' * 65537)
            with self.assertRaises(ValueError): reader.bounded(path)


class PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if SOURCE is None:
            raise unittest.SkipTest('Exact dump source preparation requires explicit --source-repo')
        cls.sources, cls.hashes = prepare_dump.checked_sources(SOURCE)
        cls.payloads, cls.fragments = prepare_dump.assemble(cls.sources)

    def test_production_dump_and_helpers_are_verbatim(self):
        output = self.payloads['production_dumps.inc'].decode()
        for name, marker in (('xmodel', '\tvoid xmodel::dump('), ('xsurface', '\tvoid dump_subdiv(')):
            source = self.sources[prepare_native.BASE + 'iw7/assets/' + name + '.cpp']
            self.assertIn(source[source.index(marker):-1], output)
        source = self.sources[prepare_native.BASE + 'iw7/common/havok.cpp']
        self.assertIn(source[source.index('\t\t\tvoid dump_havok_data('):], output)
        self.assertNotIn('parse_havok_data(', output)

    def test_existing_parser_converter_support_bytes_unchanged(self):
        baseline, _ = prepare_native.probe_sources(self.sources)
        for name in ('parser_declarations.inc', 'production_parsers.inc', 'production_converters.inc',
                     'production_support.inc', 'fixture_bytes.inc'):
            self.assertEqual(self.payloads[name], baseline[name])
        probe = self.payloads['native_probe.cpp'].decode()
        self.assertEqual(probe.count('dump_original(model_parser, source_model, model, group);'), 1)
        self.assertIn(r'\"bone_engine_token_resolved\":false', probe)
        self.assertIn(r'\"dump_executed\":true', probe)
        self.assertIn('SL_ConvertToString(asset->boneNames[i])', self.payloads['production_dumps.inc'].decode())

    def test_preparation_rejects_overwrite_drift_and_extra_files(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'prepared'
            receipt = prepare_dump.prepare(SOURCE, output)
            self.assertFalse(receipt['native_executed'])
            self.assertLess(sum(p.stat().st_size for p in output.iterdir()), 1024**2)
            with self.assertRaises(ValueError): prepare_dump.prepare(SOURCE, output)
            path = output / 'native_probe.cpp'; original = path.read_bytes(); path.write_bytes(original + b' ')
            with self.assertRaises(ValueError): prepare_dump.verify_prepared(SOURCE, output)
            path.write_bytes(original)
            (output / 'unexpected').write_bytes(b'')
            with self.assertRaises(ValueError): prepare_dump.verify_prepared(SOURCE, output)


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--source-repo', type=Path)
    args, remaining = cli.parse_known_args()
    SOURCE = args.source_repo
    unittest.main(argv=['test_dump.py'] + remaining)

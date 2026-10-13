"""Adversarial serialized-byte model of the pinned writer, not native execution.

The record reader is independent of this writer model. Source wiring checks
tie the remediation to native_export.inc; native compilation/runtime remains
a separate gate. All addresses below are invented logical range labels.
"""
from pathlib import Path
import struct
import unittest

from export_contract import geometry_work_bytes_upper_bound
from readback import Reader


def serialize_face_ranges(ranges):
    """Reproduce fab9358 assetmanager.hpp's untyped range/offset rule."""
    ledger, output = [], bytearray()
    for start, raw in ranges:
        count = len(raw) // 6
        end = start + 6 * (count - 1)
        for index, (previous_start, previous_end) in enumerate(ledger):
            if previous_start <= start and previous_end >= end:
                output.extend(struct.pack('<BII', 9, index, (start-previous_start)//6))
                break
        else:
            ledger.append((start, end))
            output.extend(struct.pack('<BBI', 8, 1, count))
            output.extend(raw)
    return bytes(output)


def own_face_ranges(ranges):
    """Model N independent allocations alive until the writer closes."""
    owned, next_address = [], 0x10000
    for _, raw in ranges:
        copied = bytes(bytearray(raw))
        owned.append((next_address, copied))
        next_address += len(copied) + 16
    return owned


def parse_face_ranges(data, counts):
    reader = Reader(data, 16*1024**2)
    result = [list(struct.iter_unpack('<3H', reader.array(f'faces{i}', 6, count, layout='faces')))
              for i, count in enumerate(counts)]
    reader.finish()
    return result


class TriangleOwnershipTests(unittest.TestCase):
    positions = ((0, 0), (1, 0), (0, 1), (1, 1))
    indices = (0, 1, 2, 3, 1, 2)

    def fixture(self, index_offset):
        shared = struct.pack('<6H', *self.indices)
        ranges = [(0x1000, shared), (0x1000+2*index_offset, shared[2*index_offset:2*index_offset+6])]
        expected = [[self.indices[:3], self.indices[3:]], [self.indices[index_offset:index_offset+3]]]
        for faces in expected:
            for face in faces:
                a,b,c = (self.positions[index] for index in face)
                area = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
                self.assertNotEqual(area, 0)
        self.assertEqual(geometry_work_bytes_upper_bound(2, 8, 3), 1540)
        return ranges, expected

    def test_pinned_writer_silently_changes_valid_plus_two_and_plus_four_byte_faces(self):
        for offset in (1, 2):
            with self.subTest(byte_offset=2*offset):
                ranges, expected = self.fixture(offset)
                observed = parse_face_ranges(serialize_face_ranges(ranges), (2, 1))
                self.assertEqual(observed[0], expected[0])
                self.assertNotEqual(observed[1], expected[1])
                self.assertEqual(observed[1], [(0, 1, 2)])

    def test_owned_copies_preserve_plus_two_plus_four_plus_six_and_exact_geometry(self):
        for offset in (1, 2, 3, 0):
            with self.subTest(byte_offset=2*offset):
                ranges, expected = self.fixture(offset)
                owned = own_face_ranges(ranges)
                observed = parse_face_ranges(serialize_face_ranges(owned), (2, 1))
                self.assertEqual(observed, expected)
                self.assertEqual(sum(len(raw) for _,raw in owned), 6*3)
                self.assertEqual([raw for _,raw in owned], [raw for _,raw in ranges])

    def test_aligned_and_exact_borrowed_aliases_are_valid_positive_controls(self):
        for offset in (3, 0):
            ranges, expected = self.fixture(offset)
            self.assertEqual(parse_face_ranges(serialize_face_ranges(ranges), (2, 1)), expected)

    def test_native_v2_owns_each_triangle_occurrence_before_the_pinned_writer(self):
        source = (Path(__file__).parent/'native_export.inc').read_text(encoding='utf-8')
        helper = source.split('static void resident_export_dump_multisurface_mesh(', 1)[1].split(
            'static void export_resident_model_iw7(', 1)[0]
        self.assertIn('i < converted->numsurfs', helper)
        self.assertIn('allocator.allocate_array<zonetool::iw7::Face>(surface.triCount)', helper)
        self.assertIn('std::memcpy(owned_faces, surface.triIndices, sizeof(zonetool::iw7::Face) * surface.triCount)', helper)
        self.assertLess(helper.index('surface.triIndices = owned_faces;'), helper.index('zonetool::iw7::xsurface::dump(converted);'))
        self.assertIn('if (multisurface) resident_export_dump_multisurface_mesh(selected->meshes[0]);', source)
        self.assertIn('else converter::iw7::xmodel_mesh::dump(selected->meshes[0]);', source)

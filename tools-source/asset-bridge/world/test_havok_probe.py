"""Original synthetic envelope tests only; fixture bytes are NOT usable Havok."""
import struct
import unittest

import havok_probe as probe


def envelope():
    # A deliberately nonfunctional envelope, never emitted as an .hkx asset.
    header = probe.HEADER.pack(0x57E0E057, 0x10C0C010, 0, 11, 8, 1, 0, 1,
                               3, 2, 0, 0, 0, probe.VERSION + b'\0\xff\xff', 0, 0, 0)
    sections = b''.join(probe.SECTION.pack(name, start, *([size] * 6), b'\xff' * 16)
                        for name, start, size in ((b'__classnames__', 256, 32),
                                                  (b'__types__', 288, 0),
                                                  (b'__data__', 288, 16)))
    return bytearray(header + sections + b'OriginalEnvelopeOnly\0'.ljust(32, b'\xff') + b'\0' * 16)


class HavokProbeTest(unittest.TestCase):
    def test_original_envelope_is_never_runtime_proof(self):
        report = probe.inspect_hkx(bytes(envelope()))
        self.assertEqual(report['root_class'], 'OriginalEnvelopeOnly')
        self.assertEqual(report['file_version'], 11)
        self.assertFalse(report['runtime_ready'])
        self.assertFalse(report['shape_graph_validated'])
        self.assertFalse(report['fixups_validated'])

    def test_truncation_and_budget(self):
        source = envelope()
        for count in (0, 1, 63, 64, 255, 303):
            with self.subTest(count=count), self.assertRaises(ValueError):
                probe.inspect_hkx(bytes(source[:count]))
        with self.assertRaises(ValueError):
            probe.inspect_hkx(b'\0' * (probe.MAX_HKX + 1))

    def test_header_versions_layout_and_roots(self):
        for offset, fmt, value in ((0, 'I', 0), (12, 'I', 10), (16, 'B', 4),
                                   (17, 'B', 0), (18, 'B', 1), (19, 'B', 0),
                                   (20, 'i', -1), (20, 'i', 1000000), (24, 'i', 3),
                                   (28, 'i', -1), (28, 'i', 16), (32, 'i', -1),
                                   (36, 'i', 32)):
            data = envelope(); struct.pack_into('<' + fmt, data, offset, value)
            with self.subTest(offset=offset, value=value), self.assertRaises(ValueError):
                probe.inspect_hkx(bytes(data))
        for value in (b'X' * 16, b'hk_2014.2.0-r1\0\xff\xff'):
            data = envelope(); data[40:56] = value
            with self.assertRaises(ValueError):
                probe.inspect_hkx(bytes(data))

    def test_sections_and_strings(self):
        for offset, value in ((84, 255), (88, 40), (108, 999999),
                              (148, 280), (212, 280)):
            data = envelope(); struct.pack_into('<I', data, offset, value)
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                probe.inspect_hkx(bytes(data))
        for offset, length in ((64, 20), (256, 32)):
            data = envelope(); data[offset:offset+length] = b'X' * length
            with self.assertRaises(ValueError):
                probe.inspect_hkx(bytes(data))

    def test_unpinned_runtime_refused(self):
        with self.assertRaises(ValueError):
            probe.inspect_rdata(b'not the retained snapshot')


if __name__ == '__main__':
    unittest.main(verbosity=2)

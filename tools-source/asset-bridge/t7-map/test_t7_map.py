"""Source tests for the T7 map bridge (no game data, no game process)."""
import math
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_xpak  # noqa: E402
import kino_compose as kc  # noqa: E402


def lz4_literals(data):
    """Minimal valid LZ4 block holding only literals (final sequence)."""
    n = len(data)
    if n < 15:
        return bytes([n << 4]) + data
    out = bytearray([0xF0])
    rest = n - 15
    while rest >= 255:
        out.append(255)
        rest -= 255
    out.append(rest)
    return bytes(out) + data


class Lz4Tests(unittest.TestCase):
    def test_literals_roundtrip(self):
        for n in (0, 1, 14, 15, 16, 300, 4000):
            data = bytes((i * 7) & 0xFF for i in range(n))
            self.assertEqual(t7_xpak.lz4_block(lz4_literals(data)), data)

    def test_overlapping_match(self):
        # literal "ab" then a match of length 6 at offset 2 -> "abababab"
        block = bytes([0x22]) + b"ab" + struct.pack("<H", 2)
        self.assertEqual(t7_xpak.lz4_block(block), b"abababab")

    def test_overflow_refused(self):
        block = bytes([0x1F]) + b"a" + struct.pack("<H", 1) + bytes([255] * 300)
        with self.assertRaises(ValueError):
            t7_xpak.lz4_block(block, max_out=1000)


class XPakTests(unittest.TestCase):
    def write_pak(self, root, key, groups, pad_to=128):
        """Header + hash table + one entry made of padded command groups."""
        body = bytearray()
        produced = 0
        for chunks in groups:
            hdr = struct.pack("<II", len(chunks), produced)
            cmds = [(3 << 24) | len(lz4_literals(c)) for c in chunks] + [0] * (30 - len(chunks))
            body += hdr + struct.pack("<30I", *cmds)
            for c in chunks:
                body += lz4_literals(c)
                produced += len(c)
            while len(body) % pad_to:
                body.append(0xCD)
        hdr_size = t7_xpak.HDR.size
        hash_off = hdr_size
        data_off = hash_off + 24
        header = t7_xpak.HDR.pack(0x4950414B, 0, 0xD, 0, 0, 1, data_off, len(body), 1, hash_off, 24, 0, 0, 0, 0, 0, 0)
        path = os.path.join(root, "test.xpak")
        with open(path, "wb") as f:
            f.write(header + struct.pack("<QQQ", key, 0, len(body)) + body)
        return path

    def test_groups_with_padding(self):
        with tempfile.TemporaryDirectory() as d:
            a, b, c = b"A" * 100, b"B" * 37, b"C" * 5
            self.write_pak(d, 0x1234, [[a, b], [c]])
            xs = t7_xpak.XPakSet(d)
            self.assertEqual(xs.get("0000000000001234"), a + b + c)
            self.assertIsNone(xs.get(0x99))


class EncodingTests(unittest.TestCase):
    def test_unit_vector_roundtrip(self):
        for v in ((0, 0, 1), (0, 0, -1), (1, 0, 0), (0.6, -0.8, 0), (0.3, 0.4, 0.866)):
            u = kc.encode_n(v)
            self.assertEqual(u >> 30, 0)
            d = kc.decode_n(u)
            l = math.sqrt(sum(x * x for x in v))
            for k in range(3):
                self.assertAlmostEqual(d[k], v[k] / l, delta=0.004)

    def test_known_bo3_words(self):
        # Stock-observed axis words (top bits are IW7's constant 11 for normals).
        self.assertEqual(kc.encode_n((0, 0, -1)) | 0xC0000000, 0xC0080200)
        for got, want in zip(kc.decode_n(0xFFF7FDFF), (0.0, 0.0, 1.0)):
            self.assertAlmostEqual(got, want, delta=0.003)

    def test_half(self):
        self.assertEqual(kc.half(0x3C00), 1.0)
        self.assertEqual(kc.half(0xC000), -2.0)
        self.assertEqual(kc.half(0), 0.0)

    def test_mip_sizes(self):
        self.assertEqual(kc.mip_size(512, 512, 8), 131072)
        self.assertEqual(kc.mip_size(2, 1, 16), 16)
        self.assertEqual(kc.mip_size(128, 64, 8), 4096)

    def test_kimg_record(self):
        rec = kc.kimg("kino_x", 71, 4, 4, 3, 0x101, b"\x00" * 24)
        self.assertEqual(rec[:8], struct.pack("<II", 0x474D494B, 1))
        n = struct.unpack_from("<H", rec, 8)[0]
        self.assertEqual(rec[10:10 + n], b"kino_x")
        self.assertEqual(struct.unpack_from("<IIIIII", rec, 10 + n), (71, 4, 4, 3, 0x101, 24))

    def test_dds_to_kimg_unorm_and_flags(self):
        hdr = struct.pack("<4sIIIIIII44sII4s" + "I" * 15, b"DDS ", 124, 0, 8, 8, 32, 1, 4, bytes(44), 32, 4, b"DX10",
                          0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 72, 3, 0, 1, 0)
        rec = kc.dds_to_kimg("kino_y", hdr + b"\x00" * 56)
        fmt, w, h, levels, flags, size = struct.unpack_from("<IIIIII", rec, 10 + len("kino_y"))
        self.assertEqual((fmt, w, h, levels, size), (71, 8, 8, 4, 56))  # sRGB stored as UNORM
        self.assertEqual(flags, 0x1 | 0x100)  # NOPICMIP + GAMMA_SRGB

    def test_material_names_are_flat(self):
        self.assertEqual(kc.sanitize("wc/t7_Wood-Planks"), "t7_wood_planks")
        self.assertNotIn("/", "kino_t_" + kc.sanitize("i_t7_x/y"))


if __name__ == "__main__":
    unittest.main()

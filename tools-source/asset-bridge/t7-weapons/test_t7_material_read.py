"""Synthetic tests for t7_material_read.py (no game data)."""
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_material_read as mr  # noqa: E402


class FakeProcess:
    def __init__(self, blocks):
        self.blocks = blocks

    def _find(self, addr, size):
        for base, data in self.blocks.items():
            if base <= addr and addr + size <= base + len(data):
                return data[addr - base:addr - base + size]
        return None

    def readable(self, addr, size=1):
        return self._find(addr, size) is not None

    def read(self, addr, size):
        data = self._find(addr, size)
        if data is None:
            raise OSError(0, "unreadable")
        return data

    def cstr(self, addr):
        data = self.blocks[addr]
        return data.split(b"\0", 1)[0].decode()


def constant(name, values):
    return struct.pack("<I12s4f", 0x1234, name.encode(), *values)


class MaterialReadTest(unittest.TestCase):
    def test_constants_textures_and_techset(self):
        header = bytearray(mr.MATERIAL_SIZE)
        header[0x270], header[0x272] = 1, 2
        struct.pack_into("<4Q", header, 0x278, 0x5000, 0x6000, 0, 0x7000)
        blocks = {
            0x1000: bytes(header),
            0x5000: struct.pack("<Q", 0x5100),
            0x5100: b"mc/lit_emissive#e6142445\0",
            0x6000: struct.pack("<QI", 0x9000, 0xA0AB1041) + bytes(20),
            0x7000: constant("hdrScale", (16.0, 0, 0, 0)) + constant("emissiveTint", (0.026, 0.151, 0.672, 1.0)),
        }
        m = mr.read_material(FakeProcess(blocks), {0x9000: {"name": "i_wpn_t7_zmb_raygun_power_e"}}, 0x1000)
        self.assertEqual(m["techset"], "mc/lit_emissive#e6142445")
        self.assertEqual(m["constants"]["hdrScale"], [16.0, 0.0, 0.0, 0.0])
        self.assertEqual(m["constants"]["emissiveTint"][:3], [0.026, 0.151, 0.672])
        self.assertEqual(m["textures"], [{"semantic": "0xA0AB1041", "image": "i_wpn_t7_zmb_raygun_power_e"}])

    def test_unresolved_emissive_technique_uses_the_checked_layout(self):
        # Ray Gun reticle: lit_emissive's lit technique is a stub in zm_levelcommon; the buffer stays.
        header = bytearray(mr.MATERIAL_SIZE)
        struct.pack_into("<Q", header, 0x30 + 48 * 6 + 32, 0x8000)
        struct.pack_into("<4Q", header, 0x278, 0x5000, 0, 0, 0)
        data = bytearray(224)
        struct.pack_into("<3f", data, 160, 1.0, 0.0, 0.0)
        struct.pack_into("<2f", data, 176, 0.0, 13.0)
        struct.pack_into("<f", data, 188, 64.0)
        buf = bytearray(72)
        struct.pack_into("<QI", buf, 40, 0x9000, 224)
        blocks = {0x1000: bytes(header), 0x5000: struct.pack("<Q", 0x5100) + bytes(16 + 8 * 12),
                  0x5100: b"mc/lit_emissive#e6142445" + bytes(1), 0x8000: bytes(buf), 0x9000: bytes(data)}
        m = mr.read_material(FakeProcess(blocks), {}, 0x1000)
        self.assertEqual(m["constants"]["hdrScale"], [64.0])
        self.assertEqual(m["constants"]["glossRange"], [0.0, 13.0])
        self.assertEqual(m["constants"]["colorTint"], [1.0, 0.0, 0.0])

    def test_material_without_tables(self):
        m = mr.read_material(FakeProcess({0x1000: bytes(mr.MATERIAL_SIZE)}), {}, 0x1000)
        self.assertEqual(m, {"techset": None, "constants": {}, "textures": []})



def dxbc_with_globals(variables):
    """A minimal DXBC holding an SM5 RDEF chunk with one $Globals cbuffer."""
    strings = bytearray()

    def add(text):
        off = 60 + 24 + 40 * len(variables) + len(strings)
        strings.extend(text.encode() + b"\0")
        return off
    cb_name = add("$Globals")
    var_names = [add(n) for n, _, _ in variables]
    rd = bytearray(struct.pack("<IIIIBBHI", 1, 60, 0, 0, 0, 5, 0xFFFF, 0, ) + struct.pack("<I", 0))
    rd = rd.ljust(60, b"\0")
    rd += struct.pack("<IIIIII", cb_name, len(variables), 84, 16 * len(variables), 0, 0)
    for off, (_, start, size) in zip(var_names, variables):
        rd += struct.pack("<IIIIIIIIII", off, start, size, 2, 0, 0, 0, 0, 0, 0)
    rd += strings
    chunk = b"RDEF" + struct.pack("<I", len(rd)) + bytes(rd)
    head = b"DXBC" + bytes(16) + struct.pack("<III", 1, 36 + len(chunk), 1) + struct.pack("<I", 36)
    return head + chunk


class RdefTest(unittest.TestCase):
    def test_globals_layout_and_values(self):
        layout = mr.rdef_globals(dxbc_with_globals([("hdrScale", 188, 4), ("emissiveTint1", 304, 16)]))
        self.assertEqual(layout, {"hdrScale": (188, 4), "emissiveTint1": (304, 16)})
        data = bytearray(336)
        struct.pack_into("<f", data, 188, 16.0)
        struct.pack_into("<4f", data, 304, 0.0257, 0.1509, 0.6724, 1.0)
        values = mr.globals_values(layout, bytes(data))
        self.assertEqual(values["hdrScale"], [16.0])
        self.assertEqual(values["emissiveTint1"], [0.0257, 0.1509, 0.6724, 1.0])

    def test_not_a_shader(self):
        self.assertEqual(mr.rdef_globals(b"nope"), {})


if __name__ == "__main__":
    unittest.main()

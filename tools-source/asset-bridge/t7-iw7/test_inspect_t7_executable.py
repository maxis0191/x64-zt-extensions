"""Small synthetic PE cases only; no retail file or native process is needed."""
import contextlib
import io
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import inspect_t7_executable as subject


def synthetic_pe():
    data = bytearray(0x800)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 60, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HHI", data, 0x84, 0x8664, 2, 123456)
    struct.pack_into("<H", data, 0x94, 0xF0)
    opt = 0x98
    struct.pack_into("<H", data, opt, 0x20B)
    struct.pack_into("<I", data, opt + 16, 0x1000)
    struct.pack_into("<Q", data, opt + 24, subject.BASE)
    struct.pack_into("<I", data, opt + 56, 0x3000)
    struct.pack_into("<I", data, opt + 108, 16)
    struct.pack_into("<II", data, opt + 112 + 8, 0x2000, 0x300)
    struct.pack_into("<II", data, opt + 112 + 3 * 8, 0x2050, 12)
    for index, name, values, flags in (
        (0, b".text", (0x300, 0x1000, 0x200, 0x200), 0x60000020),
        (1, b".rdata", (0x400, 0x2000, 0x400, 0x400), 0x40000040),
    ):
        off = 0x188 + index * 40
        data[off:off + len(name)] = name
        struct.pack_into("<IIII", data, off + 8, *values)
        struct.pack_into("<I", data, off + 36, flags)
    data[0x200:0x400] = b"\x90" * 0x200
    struct.pack_into("<5I", data, 0x400, 0x20D0, 0, 0, 0x20C0, 0x20D0)
    struct.pack_into("<III", data, 0x450, 0x1000, 0x1080, 0x20A0)
    data[0x4A0:0x4A4] = b"\x01\x00\x00\x00"
    data[0x4C0:0x4CB] = b"user32.dll\0"
    struct.pack_into("<Q", data, 0x4D0, 0x20F0)
    data[0x4F2:0x505] = b"SetProcessDPIAware\0"
    return data


class InspectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "synthetic.bin"

    def image(self, mutate=None):
        data = synthetic_pe()
        if mutate:
            mutate(data)
        self.path.write_bytes(data)
        source = subject.ObservedFile(self.path)
        self.addCleanup(source.file.close)
        return source, subject.PE(source)

    def test_section_rva_is_not_file_offset_and_exact_end_is_allowed(self):
        src, pe = self.image()
        self.assertEqual(pe.read(0x1000, 1), b"\x90")
        self.assertEqual(pe.read(0x11FF, 1), b"\x90")
        with self.assertRaises(ValueError):
            pe.read(0x11FF, 2)
        self.assertLess(src.bytes_read, subject._reader.LIMIT)

    def test_bss_is_mapped_but_not_file_backed(self):
        _, pe = self.image()
        self.assertEqual(pe.section(0x1200, 1)["name"], ".text")
        with self.assertRaisesRegex(ValueError, "file backing"):
            pe.read(0x1200, 1)

    def test_negative_outside_and_cross_section_ranges_refused(self):
        _, pe = self.image()
        for rva, count in ((-1, 1), (0x3000, 1), (0x1000, 0), (0x1200, 0x1000)):
            with self.subTest(rva=rva, count=count), self.assertRaises(ValueError):
                pe.read(rva, count)

    def test_overlapping_virtual_sections_refused(self):
        with self.assertRaisesRegex(ValueError, "overlapping virtual"):
            self.image(lambda b: struct.pack_into("<I", b, 0x1B0 + 12, 0x1100))

    def test_overlapping_raw_sections_refused(self):
        with self.assertRaisesRegex(ValueError, "overlapping file"):
            self.image(lambda b: struct.pack_into("<I", b, 0x1B0 + 20, 0x300))

    def test_truncated_raw_section_refused(self):
        with self.assertRaisesRegex(ValueError, "exceeds file"):
            self.image(lambda b: struct.pack_into("<I", b, 0x1B0 + 16, 0x500))

    def test_bounded_metadata_and_optional_header(self):
        with self.assertRaises(ValueError):
            self.image(lambda b: struct.pack_into("<H", b, 0x94, 0xFFFF))
        src, _ = self.image()
        with patch.object(subject._reader, "LIMIT", src.bytes_read):
            with self.assertRaisesRegex(ValueError, "budget"):
                src.read(0, 1)

    def test_imports_use_terminated_descriptors_not_entire_directory_size(self):
        _, pe = self.image()
        self.assertEqual(pe.imports(), [{"dll": "user32.dll", "symbols": ["SetProcessDPIAware"]}])

    def test_unterminated_import_string_refused(self):
        _, pe = self.image(lambda b: b.__setitem__(slice(0x4C0, 0x800), b"A" * 0x340))
        with self.assertRaises(ValueError):
            pe.imports()

    def test_pdata_lookup_and_unwind_are_bounded(self):
        _, pe = self.image()
        pdata = pe.pdata()
        self.assertEqual(pe.unwind(pdata, 0x1020)["begin_rva"], 0x1000)
        self.assertIsNone(pe.unwind(pdata, 0x1080))
        self.assertIsNone(pe.unwind(pdata, 0x0FFF))

    def test_bad_pdata_extent_refused(self):
        _, pe = self.image(lambda b: struct.pack_into("<I", b, 0x98 + 112 + 3 * 8 + 4, 13))
        with self.assertRaises(ValueError):
            pe.pdata()

    def test_overlapping_pdata_is_indeterminate_not_an_independent_anchor(self):
        def overlap(data):
            struct.pack_into("<I", data, 0x98 + 112 + 3 * 8 + 4, 24)
            struct.pack_into("<III", data, 0x45C, 0x1010, 0x1090, 0x20A0)
        _, pe = self.image(overlap)
        with self.assertRaisesRegex(ValueError, "overlapping .pdata"):
            pe.pdata()
        with patch.object(subject, "SITES", [("ambiguous", 0x1020, 0x20, 64, "entry")]):
            report = subject.inspect(self.path)
        row = report["windows"][0]
        self.assertEqual(row["decode_anchor"], "source_assumed_site")
        self.assertIsNone(row["runtime_function"])
        self.assertTrue(any("overlapping .pdata" in error for error in report["indeterminate"]))
        self.assertEqual(report["decision"], "indeterminate_manual_review_required")
        self.assertFalse(report["boot_authorized"])

    def test_adjacent_pdata_ranges_have_unique_half_open_ownership(self):
        def adjacent(data):
            struct.pack_into("<I", data, 0x98 + 112 + 3 * 8 + 4, 24)
            struct.pack_into("<III", data, 0x45C, 0x1080, 0x1090, 0x20A0)
        _, pe = self.image(adjacent)
        pdata = pe.pdata()
        self.assertEqual(pe.unwind(pdata, 0x107F)["begin_rva"], 0x1000)
        self.assertEqual(pe.unwind(pdata, 0x1080)["begin_rva"], 0x1080)
        self.assertIsNone(pe.unwind(pdata, 0x1090))

    def test_invalid_unwind_header_cannot_anchor_decoding(self):
        _, pe = self.image(lambda b: b.__setitem__(0x4A0, 0))
        with self.assertRaisesRegex(ValueError, "unwind header"):
            pe.unwind(pe.pdata(), 0x1000)

    def test_call_expectation_is_computed_not_a_known_good_fingerprint(self):
        good = bytes.fromhex("e8 c2 16 00 00")
        failures, detail = subject.expectation("call_init", good, 0x502AA9)
        self.assertEqual(failures, [])
        self.assertEqual(detail["direct_call_target"], "0x140504170")
        self.assertTrue(subject.expectation("call_init", b"\xe8\0\0\0\0", 0x502AA9)[0])
        self.assertTrue(subject.expectation("call", b"\x90" * 5, 0x502AA9)[0])

    def test_inspection_never_authorizes_boot_or_claims_full_hash(self):
        self.path.write_bytes(synthetic_pe())
        with patch.object(subject, "SITES", [("synthetic_entry", 0x1000, 0, 32, "entry")]):
            report = subject.inspect(self.path, "a" * 64)
        self.assertFalse(report["boot_authorized"])
        self.assertFalse(report["executable_loaded"])
        self.assertFalse(report["runtime_compatibility_proven"])
        self.assertFalse(report["identity"]["full_file_sha256_computed"])
        self.assertEqual(report["windows"][0]["decode_anchor"], "pdata_begin")
        self.assertEqual(report["decision"], "indeterminate_manual_review_required")

    @unittest.skipUnless(importlib.util.find_spec("capstone"), "optional local Capstone disassembly")
    def test_instruction_spanning_hook_site_stops_boot(self):
        data = synthetic_pe()
        data[0x200:0x20A] = bytes.fromhex("48 b8 00 00 00 00 00 00 00 00")
        self.path.write_bytes(data)
        with patch.object(subject, "SITES", [("inside_mov", 0x1002, 2, 32, "entry")]):
            report = subject.inspect(self.path)
        self.assertEqual(report["decision"], "stop_before_boot")
        self.assertTrue(any("inside an instruction" in e for e in report["conflicts"]))

    def test_missing_capstone_is_explicitly_indeterminate(self):
        self.path.write_bytes(synthetic_pe())
        with patch.dict("sys.modules", {"capstone": None}):
            with patch.object(subject, "SITES", [("synthetic_entry", 0x1000, 0, 32, "entry")]):
                report = subject.inspect(self.path)
        self.assertFalse(report["boot_authorized"])
        self.assertNotIn("instructions", report["windows"][0])
        self.assertTrue(any("capstone unavailable" in e for e in report["indeterminate"]))

    def test_changed_file_identity_refuses_report(self):
        self.path.write_bytes(synthetic_pe())
        with patch.object(subject.ObservedFile, "identity", side_effect=[(1, 2, 3, 4, 5), (1, 2, 3, 4, 6)]):
            with patch.object(subject, "SITES", []), self.assertRaisesRegex(ValueError, "changed"):
                subject.inspect(self.path)

    def test_cli_refuses_tracked_raw_output_before_reading_input(self):
        with patch("sys.argv", ["inspect", "never-opened.exe", "--output", str(self.path.with_suffix(".json"))]):
            with patch.object(subject, "inspect", side_effect=AssertionError("input must not be read")):
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(subject.main(), 2)
        self.assertIn("raw output", json.loads(output.getvalue())["error"])


if __name__ == "__main__":
    unittest.main()

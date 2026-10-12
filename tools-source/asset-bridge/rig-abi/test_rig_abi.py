"""Source-only tests. No debugger, native target or retail bytes are executed."""
import json
from pathlib import Path
import re
import struct
import tempfile
import unittest
import uuid

import capture
import symbol_identity as symbols


def context():
    # Synthetic addresses/PID only; never write this as a usable runtime receipt.
    return {"schema": capture.SCHEMA, "profile": "first", "run_id": "a" * 32,
            "tool_sha256": capture.TOOL_SHA, "ff_sha256": capture.FF_SHA,
            "pid": 0x1234, "creation_utc": "2026-10-12T00:00:00Z",
            "image_path": "C:\\synthetic-fixture-only\\zonetool.exe",
            "xsurface": "0x20000", "xmodelsurfs": "0x30000", "arm_rip": "0x140001000",
            "arm_code_hex": "90" * 8,
            "review": {"phase": "after-initial-copy-before-postload", "evidence_sha256": "b" * 64,
                       "mapping_verified": True, "stopped_identity_verified": True,
                       "launch_job_owned": True, "breakpoint_table_empty": True,
                       "all_threads_stopped": True, "deadline_armed": True,
                       "admission_lease_id": "synthetic-not-an-admission"}}


def witness(new=0x40000, now=0x40000):
    prefix = "RIG58 " + "a" * 32 + " "
    return (prefix + "ARM pid=1234 tid=2 rip=140001000 xs=20000 ms=30000 old=0 name_before=40000\n" +
            prefix + "BP_PRESENT\n" + prefix + "ARM_ATTEMPT_STOPPED\n" +
            prefix + f"WRITE pid=1234 tid=3 rip=140002010 xs=20000 ms=30000 old=0 new={new:x} "
                     f"name_before=40000 name_now={now:x}\n" +
            prefix + "STACK_BEGIN\n00 synthetic_frame_only\n" +
            prefix + "STACK_END\n" + prefix + "STOP\n").encode()


class CaptureTests(unittest.TestCase):
    def test_register_destinations_use_documented_r_syntax(self):
        arm = capture.emit(context())["arm.cdb"]
        self.assertIn("r $t0 =", arm)
        self.assertNotIn("r @$", arm)

    def test_checked_in_context_cannot_emit(self):
        template = capture.load_context(Path(__file__).with_name("context.template.json"))
        with self.assertRaises(ValueError):
            capture.emit(template)

    def test_one_shot_no_resume_or_process_action(self):
        files = capture.emit(context())
        arm = files["arm.cdb"]
        self.assertIn('ba3 w 8 /1 0x20058 "', arm)
        self.assertIn("kv 6", arm)
        self.assertIn(".expr /s masm", arm)
        self.assertIn("CODE_BYTES", arm)
        self.assertIn("TOO_LATE_OR_NONZERO", arm)
        self.assertIn("ARM_ATTEMPT_STOPPED", arm)
        self.assertIn("@$bp3 == 0x20058", arm)
        self.assertNotIn("r @$", arm)
        self.assertNotIn("; g", arm)
        self.assertNotIn("; q", arm)
        self.assertNotIn(".attach", arm)
        self.assertNotIn(".shell", arm)
        self.assertNotIn(".call", arm)
        self.assertNotIn("ed ", arm)
        self.assertLess(max(map(len, arm.splitlines())), 4096)
        self.assertFalse(json.loads(files["fragments.local.json"])["runtime_validated"])

    def test_second_profile_has_different_name_guard(self):
        other = context()
        other["profile"] = "second"
        self.assertNotEqual(capture.emit(other)["arm.cdb"], capture.emit(context())["arm.cdb"])

    def test_breakpoint_string_preserves_printf_escape(self):
        arm = capture.emit(context())["arm.cdb"]
        quoted = re.search(r'ba3 w 8 /1 0x20058 ("(?:[^"\\]|\\.)*")', arm)[1]
        inner = json.loads(quoted)  # C-compatible escapes in this ASCII fragment.
        self.assertIn('name_now=%I64x\\n",', inner)
        self.assertNotIn("\n", inner)
        self.assertIn("kv 6", inner)

    def test_each_review_gate_required(self):
        for key, value in context()["review"].items():
            with self.subTest(key=key):
                item = context()
                item["review"][key] = False if type(value) is bool else None
                with self.assertRaises(ValueError):
                    capture.emit(item)

    def test_literal_address_injection_and_alignment(self):
        for value in ("poi(0x20000)", "0x20000;g", "0", "0x0", "0xffffffffffffffff", "0x20001", None):
            with self.subTest(value=value):
                item = context()
                item["xsurface"] = value
                with self.assertRaises(ValueError):
                    capture.emit(item)

    def test_unknown_pins_names_and_missing_phase(self):
        for key, value in (("tool_sha256", "0" * 64), ("ff_sha256", "0" * 64),
                           ("profile", "first; g"), ("run_id", "x" * 32), ("pid", True),
                           ("creation_utc", ""), ("image_path", "C:\\game\\iw7-paris-voice.exe"),
                           ("review", None), ("arm_code_hex", "00" * 33),
                           ("xmodelsurfs", "0x20008")):
            with self.subTest(key=key):
                item = context()
                item[key] = value
                with self.assertRaises(ValueError):
                    capture.emit(item)

    def test_byte_comparison_includes_nul_and_handles_all_widths(self):
        expr = capture.same_bytes("base", b"abcdefghijklmno\0")
        self.assertEqual(expr.count("qwo("), 2)
        expr = capture.same_bytes("base", b"abcdefghijklmno")
        self.assertEqual([expr.count(op + "(") for op in ("qwo", "dwo", "wo", "by")], [1, 1, 3, 1])
        self.assertIn("0x6f", expr)

    def test_capture_categories_never_accept_semantics(self):
        for new, now, label in ((0, 0x40000, "zero"), (0x40000, 0x40000, "equals_current_name_address"),
                                (0x40000, 0x50000, "equals_name_address_at_arm"),
                                (0x60000, 0x40000, "other_nonzero_unclassified")):
            with self.subTest(label=label):
                result = capture.parse_capture(context(), witness(new, now))
                self.assertEqual(result["new_category"], label)
                self.assertFalse(result["semantic_acceptance"])
                self.assertFalse(result["process_closure_verified"])
                self.assertFalse(result["complete_ff_verify"])
                self.assertFalse(result["stack_frames_verified"])
                self.assertTrue(result["trap_rip_is_not_resolved_store_instruction"])

    def test_truncated_replayed_foreign_and_refused_logs_fail(self):
        raw = witness()
        cases = (raw[:-50], raw + raw, raw.replace(b"a" * 32, b"b" * 32, 1),
                 raw + b"RIG58_REFUSED_TOO_LATE_OR_NONZERO\n", raw.replace(b"pid=1234", b"pid=1235"),
                 raw.replace(b"xs=20000", b"xs=20008", 1), raw.replace(b"old=0", b"old=1", 1),
                 raw.replace(b"name_before=40000", b"name_before=50000", 1),
                 raw.replace(b"tid=2", b"tid=2 tid=3", 1), raw.replace(b"tid=2", b"tid=0", 1),
                 raw.replace(b"00 synthetic_frame_only\n", b""), b"x" * (capture.MAX_LOG + 1))
        for i, case in enumerate(cases):
            with self.subTest(case=i), self.assertRaises(ValueError):
                capture.parse_capture(context(), case)

    def test_prompt_echo_is_not_an_event_or_a_refusal(self):
        raw = b"0:000> .if (0) { .echo RIG58_REFUSED_PID }\n" + witness()
        self.assertEqual(capture.parse_capture(context(), raw)["new_category"], "equals_current_name_address")

    def test_stack_limit_counts_bytes_not_unicode_characters(self):
        raw = witness().replace(b"00 synthetic_frame_only", ("\u00e9" * 4096).encode("utf-8"))
        with self.assertRaises(ValueError):
            capture.parse_capture(context(), raw)

    def test_json_duplicates_and_oversize_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "context.json"
            for raw in (b'{"pid":1,"pid":2}', b" " * 32769):
                path.write_bytes(raw)
                with self.assertRaises(ValueError):
                    capture.load_context(path)


GUID = uuid.UUID("aa767c25-a609-474e-a2de-9922d7dc159b")


def fake_pe():
    data = bytearray(4096)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 60, 128)
    data[128:132] = b"PE\0\0"
    struct.pack_into("<HHI", data, 132, 0x8664, 1, 123)
    struct.pack_into("<H", data, 148, 240)
    opt = 152
    struct.pack_into("<H", data, opt, 0x20B)
    struct.pack_into("<Q", data, opt + 24, 0x160000000)
    struct.pack_into("<I", data, opt + 56, 8192)
    struct.pack_into("<I", data, opt + 108, 16)
    struct.pack_into("<II", data, opt + 160, 0x1000, 28)
    struct.pack_into("<IIII", data, opt + 240 + 8, 1024, 0x1000, 1024, 512)
    cv = b"RSDS" + GUID.bytes_le + struct.pack("<I", 1) + b"C:\\private\\fixture.pdb\0"
    struct.pack_into("<IIII", data, 512 + 12, 2, len(cv), 0x1080, 640)
    data[640:640 + len(cv)] = cv
    return data


def fake_pdb():
    data = bytearray(512 * 6)
    data[:32] = symbols.MAGIC
    struct.pack_into("<6I", data, 32, 512, 1, 6, 16, 0, 2)
    struct.pack_into("<I", data, 1024, 3)
    struct.pack_into("<4I", data, 1536, 2, 0, 28, 4)
    struct.pack_into("<III", data, 2048, 20000404, 0, 1)
    data[2060:2076] = GUID.bytes_le
    return data


class SymbolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pe, self.pdb = (Path(self.tmp.name) / name for name in ("fixture.exe", "fixture.pdb"))
        self.pe.write_bytes(fake_pe())
        self.pdb.write_bytes(fake_pdb())

    def test_pair_matches_with_bounded_reads_and_without_hash_claim(self):
        report = symbols.pair_report(self.pe, self.pdb)
        self.assertTrue(report["guid_age_match"])
        self.assertFalse(report["full_hash_verified"])
        self.assertFalse(report["runtime_mapping_verified"])
        self.assertLess(report["pe"]["metadata_bytes_read"], 600)
        self.assertEqual(report["pdb"]["metadata_bytes_read"], 104)
        self.assertEqual(report["pe"]["codeview"]["name"], "fixture.pdb")

    def test_age_mismatch(self):
        data = fake_pdb()
        struct.pack_into("<I", data, 2056, 2)
        self.pdb.write_bytes(data)
        self.assertFalse(symbols.pair_report(self.pe, self.pdb)["guid_age_match"])

    def test_bad_pe_inputs(self):
        changes = ((0, b"XX"), (148, struct.pack("<H", 1)), (132, struct.pack("<H", 0x14C)),
                   (134, struct.pack("<H", 97)), (312, struct.pack("<I", 0x9999)),
                   (512 + 16, struct.pack("<I", 9000)), (640, b"NB10"))
        for offset, value in changes:
            with self.subTest(offset=offset):
                data = fake_pe()
                data[offset:offset + len(value)] = value
                self.pe.write_bytes(data)
                with self.assertRaises(ValueError):
                    symbols.pe_identity(self.pe)

    def test_bad_pdb_inputs(self):
        changes = ((0, b"X"), (32, struct.pack("<I", 123)), (40, struct.pack("<I", 999)),
                   (44, struct.pack("<I", 1)), (52, struct.pack("<I", 99)),
                   (1024, struct.pack("<I", 99)), (1536, struct.pack("<I", 100000)),
                   (1544, struct.pack("<I", 0xFFFFFFFF)), (1548, struct.pack("<I", 99)),
                   (2048, struct.pack("<I", 1)))
        for offset, value in changes:
            with self.subTest(offset=offset):
                data = fake_pdb()
                data[offset:offset + len(value)] = value
                self.pdb.write_bytes(data)
                with self.assertRaises(ValueError):
                    symbols.pdb_identity(self.pdb)

    def test_truncation_is_not_a_match(self):
        for reader, path in ((symbols.pe_identity, self.pe), (symbols.pdb_identity, self.pdb)):
            with self.subTest(reader=reader.__name__):
                path.write_bytes(path.read_bytes()[:100])
                with self.assertRaises(ValueError):
                    reader(path)

    def test_budget_enforced_before_read(self):
        with symbols.BoundedFile(self.pe) as reader:
            reader.bytes_read = symbols.LIMIT
            with self.assertRaises(ValueError):
                reader.read(0, 1)
            self.assertEqual(reader.bytes_read, symbols.LIMIT)


if __name__ == "__main__":
    unittest.main()

"""Synthetic JSON and bounded decoder checks; no retail files or processes."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest

import compare_prepatch_reports as subject


def fixtures():
    base = subject.BASE
    section = dict(name=".text", rva=0, virtual_size=0x10000000, raw_size=0x10000000,
                   characteristics=0x60000020)
    pe = dict(size_of_image=0x10000000, timestamp=123, entrypoint_rva=4096,
              dll_characteristics=0, sections=[section], pdata_records=0)
    static = dict(schema="iw7.t7-static-executable-inspection/1", source_commit=subject.SOURCE,
                  identity=dict(acquisition_sha256_unverified="a" * 64, file_bytes=123), pe=copy.deepcopy(pe),
                  conflicts=["boot_call: disk conflict"], indeterminate=["g_zones: not file backed"], windows=[])
    capture = dict(schema="iw7.t7-prepatch-memory-observation/1", phase="first_dpi_before_component_post_unpack",
                   source_base=hex(base), read_limit=4194304, report_limit=262144, window_count=12,
                   window_observations=12, requested_bytes=2000, returned_bytes=2000, capture_complete=True,
                   status="captured_for_offline_review", module_base=hex(base), base_matches_source=True,
                   pe=copy.deepcopy(pe), pdata_records=0, windows=[], pid=123,
                   creation_filetime="133485408001234567", module_path=r"C:\stage\work\BlackOps3_UnrankedDedicatedServer.exe",
                   **dict.fromkeys(subject.FALSE_FLAGS, False))
    for name, rva, before, length, kind in subject.SITES:
        data = bytearray(b"\x90" * length)
        if kind in ("call", "call_init"):
            data[before:before+5] = b"\xe8" + struct.pack("<i", 0x504170 - rva - 5)
        elif kind == "short_branch":
            data[before] = 0x74
        elif kind == "intact":
            data[before:before+7] = bytes.fromhex("89 04 8a 83 45 01 ff")
        elif kind == "split":
            data[before:before+4] = bytes.fromhex("89 04 8a e9")
        row = dict(site=name, rva=rva, window_rva=rva-before, window_bytes=length,
                   bytes_hex=data.hex(), sha256=hashlib.sha256(data).hexdigest())
        static["windows"].append(copy.deepcopy(row))
        if name in subject.NAMES:
            row.update(runtime_function=None, regions=[dict(base=hex(base), size=0x10000000,
                       allocation_base=hex(base), state=0x1000, protect=0x40, type=0x1000000)])
            capture["windows"].append(row)
    return static, capture


def chain(static, capture):
    cp, pp = dict(sha256="b"*64, bytes=1234), dict(sha256="c"*64, bytes=5000)
    plan = dict(Schema="iw7.t7-prepatch-plan/1", WorkingDirectory=r"C:\stage\work",
                Image=r"C:\stage\work\probe.exe", EngineSource=r"C:\engine\dedicated.exe")
    plan["Bindings"] = [dict(Path=p, SHA256="a"*64, Bytes=123)
                        for p in (plan["EngineSource"], capture["module_path"])]
    receipt = dict(Schema="iw7.t7-prepatch-run/1", PlanSHA256=pp["sha256"],
                   Report=dict(SHA256=cp["sha256"], Bytes=cp["bytes"]),
                   Identity=dict(PID=123, Image=plan["Image"], CreatedUtc="2024-01-01T00:00:00.1234567Z"),
                   Status="CaptureCompletePendingReview", CaptureOutcome="CaptureComplete", ExitCode=0,
                   TreeClosureConfirmed=True, LeaseReleased=True, InputsReverified=True,
                   OriginalInputMetadataUnchanged=True, Quarantined=False, TerminationRequested=False,
                   CompatibilityProven=False, Ready=False)
    return receipt, plan, cp, pp


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.static, self.capture = fixtures()

    def test_patterns_can_match_without_abi_or_runner_qualification(self):
        result = subject.compare(self.static, self.capture)
        self.assertFalse(result["runtime_conflicts"])
        self.assertFalse(result["runner_qualified_capture"])
        self.assertTrue(all(result[k] is False for k in subject.FALSE_FLAGS))
        self.assertEqual(result["static_baseline"]["unknowns_cleared_by_this_comparison"], 0)
        self.assertEqual(len(result["static_baseline"]["sites_outside_capture"]), 26)

    def test_changed_bytes_and_wrong_boot_target_are_reported(self):
        row = self.capture["windows"][3]
        data = bytearray.fromhex(row["bytes_hex"])
        data[33] ^= 1
        row["bytes_hex"] = data.hex()
        result = subject.compare(self.static, self.capture)
        self.assertEqual(result["windows"][3]["changed_bytes"], 1)
        self.assertIn("original CALL target differs", result["runtime_conflicts"][0])

    def test_relocated_image_does_not_reuse_source_absolute_call_target(self):
        self.capture.update(module_base=hex(subject.BASE + 0x100000), base_matches_source=False)
        for row in self.capture["windows"]:
            row["regions"][0].update(base=self.capture["module_base"], allocation_base=self.capture["module_base"])
        result = subject.compare(self.static, self.capture)
        self.assertIn("mapped base differs", result["runtime_conflicts"][0])
        call = result["windows"][3]["mapped_pattern"]
        self.assertEqual(call["actual_mapped_call_target"], hex(subject.BASE + 0x604170))
        self.assertEqual(call["expected_absolute_target"], "0x140504170")

    def test_page_permissions_are_separate_from_section_flags(self):
        self.capture["pe"]["sections"][0]["characteristics"] = 0x40000040
        result = subject.compare(self.static, self.capture)
        self.assertTrue(result["windows"][0]["memory"]["site_executable"])
        self.assertFalse(result["windows"][0]["mapped_section"]["executable"])
        self.capture["windows"][0]["regions"][0]["protect"] = 4
        self.assertIn("not executable", subject.compare(self.static, self.capture)["runtime_conflicts"][0])

    def test_regions_reject_gaps_overlap_guard_and_foreign_allocation(self):
        row = self.capture["windows"][0]
        for field, value in (("size", 1), ("protect", 0x140), ("allocation_base", "0x1"), ("state", 0x2000)):
            with self.subTest(field=field):
                bad = copy.deepcopy(row)
                bad["regions"][0][field] = value
                with self.assertRaises(ValueError):
                    subject.memory_at(bad, subject.BASE)
        row["regions"] *= 2
        with self.assertRaises(ValueError):
            subject.memory_at(row, subject.BASE)

    def test_window_order_and_digest_fail_closed(self):
        self.capture["windows"].reverse()
        with self.assertRaises(ValueError):
            subject.compare(self.static, self.capture)
        self.capture["windows"].reverse()
        self.static["windows"][0]["sha256"] = "0"*64
        with self.assertRaises(ValueError):
            subject.compare(self.static, self.capture)

    def test_pdata_header_is_not_full_unwind_or_boundary_proof(self):
        row = self.capture["windows"][0]
        row["runtime_function"] = dict(begin_rva=row["rva"], end_rva=row["rva"]+100,
            unwind_rva=1000, unwind_header_hex="19040200", unwind_format_validated=False)
        result = subject.compare(self.static, self.capture)["windows"][0]["pdata"]
        self.assertTrue(result["begin_available_in_window"])
        self.assertFalse(result["instruction_boundary_proven"])
        row["runtime_function"]["unwind_format_validated"] = True
        with self.assertRaises(ValueError):
            subject.compare(self.static, self.capture)

    def test_partial_capture_stays_partial(self):
        self.capture.update(capture_complete=False, status="incomplete_stop", windows=[], window_observations=0)
        result = subject.compare(self.static, self.capture)
        self.assertFalse(result["capture_claims_complete"])
        self.assertFalse(result["windows"])

    def test_complete_capture_with_error_is_refused(self):
        self.capture["windows"][0]["error"] = "read failed"
        with self.assertRaises(ValueError):
            subject.compare(self.static, self.capture)

    def test_saved_chain_matches_without_reopening_engine(self):
        result = subject.correlate(self.static, self.capture, *chain(self.static, self.capture))
        self.assertTrue(result["report_links_match"])
        self.assertTrue(result["runner_qualified_capture"])

    def test_generation_hash_and_input_pin_mismatches_are_refused(self):
        for field in ("creation", "plan", "capture", "input"):
            with self.subTest(field=field):
                receipt, plan, cp, pp = chain(self.static, self.capture)
                if field == "creation": receipt["Identity"]["CreatedUtc"] = "2024-01-01T00:00:00.1234568Z"
                if field == "plan": receipt["PlanSHA256"] = "0"*64
                if field == "capture": cp["sha256"] = "0"*64
                if field == "input": plan["Bindings"][0]["SHA256"] = "0"*64
                with self.assertRaises(ValueError):
                    subject.correlate(self.static, self.capture, receipt, plan, cp, pp)

    def test_false_closure_and_string_booleans_never_qualify(self):
        for field, value in (("TreeClosureConfirmed", False), ("LeaseReleased", "true"), ("ExitCode", False),
                             ("Quarantined", True), ("TerminationRequested", True), ("InputsReverified", False)):
            receipt, plan, cp, pp = chain(self.static, self.capture)
            receipt[field] = value
            self.assertFalse(subject.correlate(self.static, self.capture, receipt, plan, cp, pp)["runner_qualified_capture"])

    def test_json_caps_duplicates_hash_and_nonfinite_are_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "input.json"
            for data in (b'{"a":1,"a":2}', b'{"a":NaN}'):
                path.write_bytes(data)
                with self.assertRaises(ValueError): subject.read_json(path, 256)
            path.write_bytes(b'{"a":1}')
            with self.assertRaises(ValueError): subject.read_json(path, 2)
            with self.assertRaises(ValueError): subject.read_json(path, 256, "0"*64)
            self.assertEqual(subject.read_json(path, 256)[0], {"a": 1})

    def test_conditional_decode_reports_mid_instruction_and_never_disassembles_unanchored(self):
        class Decoder:
            def disasm(self, data, address):
                return [type("Instruction", (), dict(address=address, size=6))()]
        row = self.capture["windows"][3]
        row["runtime_function"] = dict(begin_rva=row["rva"]-2)
        decoded = subject.decode_anchor(row, bytes.fromhex(row["bytes_hex"]), subject.BASE, Decoder())
        self.assertEqual(decoded["checks"][hex(subject.BASE+row["rva"])], "inside_instruction")
        row["runtime_function"]["begin_rva"] = row["window_rva"]-1
        self.assertFalse(subject.decode_anchor(row, b"", subject.BASE, Decoder())["available"])


if __name__ == "__main__":
    unittest.main()

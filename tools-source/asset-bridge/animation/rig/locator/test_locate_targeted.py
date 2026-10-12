"""Synthetic fragments only; never opens retail references."""
import struct
import time
import unittest

from locate_targeted import TargetedLocator, IMAGE, TEXT, LIMITS


def pdata(*ranges):
    return b"".join(struct.pack("<III", start - IMAGE, start - IMAGE + length, 0) for start, length in ranges)


def relative(opcode, source, target):
    return bytes([opcode]) + struct.pack("<i", target - source - 5)


def fixture(parts, **limits):
    last = max(offset + len(code) for offset, code in parts)
    code = bytearray(b"\xcc" * last)
    for offset, payload in parts:
        code[offset:offset + len(payload)] = payload
    return TargetedLocator(bytes(code), pdata(*[(TEXT + offset, len(code)) for offset, code in parts]),
                           limits={**LIMITS, **limits})


class TargetedTests(unittest.TestCase):
    def test_external_call_recorded_without_owner_lookup_or_global_scan(self):
        locator = fixture([(0, relative(0xe8, TEXT, TEXT + 0x10000) + b"\xc3")])
        result = locator.analyze(TEXT)
        self.assertEqual(result["fragment_count"], 1)
        self.assertEqual(result["calls_not_followed"][0]["target"], hex(TEXT + 0x10000))
        self.assertEqual(result["external_callees_followed"], 0)
        self.assertEqual(result["text_scans"], 0)
        self.assertEqual(result["linear_opcode_search_bytes"], 0)

    def test_explicit_jump_reaches_another_fragment_without_gap_scan(self):
        locator = fixture([(0, relative(0xe9, TEXT, TEXT + 0x40)), (0x40, b"\xc3")])
        result = locator.analyze(TEXT)
        self.assertEqual(result["fragment_count"], 2)
        self.assertEqual(result["decoded_bytes"], 6)
        self.assertEqual(result["control_edges"][0]["kind"], "direct-branch")
        self.assertFalse(result["continuation_same_function_established"])

    def test_conditional_branch_follows_both_explicit_paths(self):
        locator = fixture([(0, b"\x74\x1e\xc3"), (0x20, b"\xc3")])
        result = locator.analyze(TEXT)
        self.assertEqual(result["reachable_instructions"], 3)
        self.assertEqual(result["fragment_count"], 2)

    def test_loop_branch_deduplicates_and_retains_fallthrough(self):
        locator = fixture([(0, b"\x90\xe2\xfd\xc3")])
        result = locator.analyze(TEXT)
        self.assertEqual(result["reachable_instructions"], 3)
        self.assertEqual(result["control_edge_count"], 1)

    def test_boundary_fallthrough_requires_an_owned_decoded_continuation(self):
        result = fixture([(0, b"\x90"), (1, b"\xc3")]).analyze(TEXT)
        self.assertEqual(result["control_edges"][0]["kind"], "boundary-fallthrough")
        with self.assertRaisesRegex(ValueError, "ownership"):
            fixture([(0, b"\x90")]).analyze(TEXT)

    def test_unreachable_jump_skipped_code_is_not_followed_or_writer_candidate(self):
        code = b"\xeb\x04\x48\x89\x48\x58\xc3"
        result = fixture([(0, code)]).analyze(TEXT)
        self.assertEqual(result["reachable_instructions"], 2)
        self.assertEqual(result["fragments"][0]["offset_58_overlap_candidates"], [])

    def test_target_inside_instruction_is_refused(self):
        locator = fixture([(0, b"\xeb\x01\x48\x89\xc0\xc3")])
        with self.assertRaisesRegex(ValueError, "boundary"):
            locator.analyze(TEXT)

    def test_incomplete_fragment_decode_refuses_even_a_ret_prefix(self):
        with self.assertRaisesRegex(ValueError, "incomplete"):
            fixture([(0, b"\xc3\x0f")]).analyze(TEXT)

    def test_overlap_anywhere_inside_selected_fragment_refused(self):
        locator = TargetedLocator(b"\x90" * 8 + b"\xc3", pdata((TEXT, 9), (TEXT + 3, 2)))
        with self.assertRaisesRegex(ValueError, "overlaps"):
            locator.analyze(TEXT)

    def test_missing_and_outside_pdata_are_refused(self):
        with self.assertRaisesRegex(ValueError, "ownership"):
            TargetedLocator(b"\xc3", b"").analyze(TEXT)
        with self.assertRaisesRegex(ValueError, "outside"):
            TargetedLocator(b"\xc3", pdata((TEXT, 2))).analyze(TEXT)

    def test_indirect_jump_is_reported_and_not_followed(self):
        result = fixture([(0, b"\xff\xe0")]).analyze(TEXT)
        self.assertEqual(result["unresolved"][0]["reason"], "indirect control target not followed")
        self.assertEqual(result["reachable_instructions"], 1)
        self.assertFalse(result["complete_logical_function_established"])

    def test_explicit_overlapping_writes_remain_unproved_candidates(self):
        # mov [rax+58],rcx; movups [rax+50],xmm0; cmp [rax+58],rcx; ret
        code = b"\x48\x89\x48\x58\x0f\x11\x40\x50\x48\x39\x48\x58\xc3"
        result = fixture([(0, code)]).analyze(TEXT)
        candidates = result["fragments"][0]["offset_58_overlap_candidates"]
        self.assertEqual([row["displacement"] for row in candidates], [0x58, 0x50])
        self.assertEqual(candidates[1]["classification"], "mov-family-memory-destination")
        self.assertEqual(len(result["fragments"][0]["offset_58_overlap_references"]), 3)
        self.assertTrue(all(not row["surface_base_traced"] and not row["writer_proved"] for row in candidates))
        self.assertFalse(result["actual_first_writer_established"])

    def test_instruction_limit_is_checked_before_accepting_extra_instruction(self):
        locator = fixture([(0, b"\x90\x90\x90\xc3")], instructions=3)
        with self.assertRaisesRegex(RuntimeError, "instruction bound"):
            locator.analyze(TEXT)
        self.assertEqual(locator.decoded, 3)

    def test_fragment_count_byte_and_total_limits_fail_closed(self):
        for changes, expected in (({"fragments": 1}, "fragment count"),
                                  ({"fragment_bytes": 4}, "fragment byte"),
                                  ({"decoded_bytes": 5}, "decoded byte")):
            locator = fixture([(0, relative(0xe9, TEXT, TEXT + 0x20)), (0x20, b"\xc3")], **changes)
            with self.assertRaisesRegex(RuntimeError, expected):
                locator.analyze(TEXT)

    def test_edge_limit_stops_before_extra_branch(self):
        locator = fixture([(0, b"\x74\x01\xc3\xeb\xfb")], control_edges=1)
        with self.assertRaisesRegex(RuntimeError, "control edge"):
            locator.analyze(TEXT)
        self.assertEqual(len(locator.edges), 1)

    def test_deadline_refuses_without_guessing_or_widening(self):
        locator = fixture([(0, b"\xc3")])
        locator.started = time.monotonic() - 11
        with self.assertRaisesRegex(RuntimeError, "deadline"):
            locator.analyze(TEXT)
        self.assertEqual(locator.decoded, 0)


if __name__ == "__main__":
    unittest.main()

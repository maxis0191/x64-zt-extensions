"""Synthetic code only: false-edge, dataflow and hard-cap regressions."""
import struct
import time
import unittest
from unittest.mock import patch
from locate_static import Locator, IMAGE, TEXT, LIMITS


def unwind(start, length):
    return struct.pack("<III", start - IMAGE, start - IMAGE + length, 0)


def call(source, target):
    return b"\xe8" + struct.pack("<i", target - source - 5)


class LocatorTests(unittest.TestCase):
    def test_actual_instruction_edge_and_type_seven(self):
        target = TEXT + 0x1000
        code = b"\xb9\x07\0\0\0" + call(TEXT + 5, target) + b"\xc3"
        locator = Locator(code, unwind(TEXT, len(code)))
        self.assertEqual(locator.direct_edges(target), [TEXT + 5])
        start, instructions = locator.edge(TEXT + 5, target)
        self.assertEqual(start, TEXT)
        self.assertEqual(locator.type_seven(instructions, TEXT + 5), TEXT)

    def test_embedded_immediate_edge_is_not_instruction_boundary(self):
        target = TEXT + 0x1000
        code = b"\x48\xb8" + call(TEXT + 2, target) + b"\0\0\0\xc3"
        locator = Locator(code, unwind(TEXT, len(code)))
        self.assertEqual(locator.direct_edges(target), [TEXT + 2])
        with self.assertRaisesRegex(ValueError, "boundary"):
            locator.edge(TEXT + 2, target)

    def test_clobbered_type_argument_not_accepted(self):
        target = TEXT + 0x1000
        for middle in (b"\x31\xc9", call(TEXT + 5, TEXT + 0x800)):
            prefix = b"\xb9\x07\0\0\0" + middle
            code = prefix + call(TEXT + len(prefix), target) + b"\xc3"
            locator = Locator(code, unwind(TEXT, len(code)))
            _, instructions = locator.edge(TEXT + len(prefix), target)
            self.assertIsNone(locator.type_seven(instructions, TEXT + len(prefix)))

    def test_jump_skipping_argument_assignment_is_not_accepted(self):
        target = TEXT + 0x1000
        code = b"\x74\x05\xb9\x07\0\0\0" + call(TEXT + 7, target) + b"\xc3"
        locator = Locator(code, unwind(TEXT, len(code)))
        _, instructions = locator.edge(TEXT + 7, target)
        self.assertIsNone(locator.type_seven(instructions, TEXT + 7))

    def test_missing_or_overlapping_unwind_is_refused(self):
        for pdata in (b"", unwind(TEXT, 8) + unwind(TEXT + 1, 6)):
            with self.assertRaisesRegex(ValueError, "unwind ownership"):
                Locator(b"\x90" * 8, pdata).owner(TEXT + 2)

    def test_loop_family_and_counter_zero_branch_cannot_bypass_assignment(self):
        target = TEXT + 0x1000
        for branch in (b"\xe2\x05", b"\xe1\x05", b"\xe0\x05", b"\xe3\x05", b"\x67\xe3\x05"):
            prefix = branch + b"\xb9\x07\0\0\0"
            code = prefix + call(TEXT + len(prefix), target) + b"\xc3"
            locator = Locator(code, unwind(TEXT, len(code)))
            _, instructions = locator.edge(TEXT + len(prefix), target)
            self.assertIsNone(locator.type_seven(instructions, TEXT + len(prefix)), branch.hex())

    def test_internal_call_cannot_enter_after_type_assignment(self):
        target = TEXT + 0x1000
        for first_target, expected in ((TEXT + 10, None), (TEXT + 0x800, TEXT + 5)):
            code = call(TEXT, first_target) + b"\xb9\x07\0\0\0" + call(TEXT + 10, target) + b"\xc3"
            locator = Locator(code, unwind(TEXT, len(code)))
            _, instructions = locator.edge(TEXT + 10, target)
            self.assertEqual(locator.type_seven(instructions, TEXT + 10), expected)

    def test_both_edge_opcodes_share_one_linear_search(self):
        target = TEXT + 0x1000
        code = call(TEXT, target) + b"\xe9" + struct.pack("<i", target - TEXT - 10)
        locator = Locator(code, unwind(TEXT, len(code)))
        self.assertEqual(locator.direct_edges(target), [TEXT, TEXT + 5])
        self.assertEqual(locator.scans, 1)
        self.assertEqual(locator.search_bytes, len(code))

    def test_last_instruction_cannot_cross_the_instruction_limit(self):
        locator = Locator(b"\x90" * 4, unwind(TEXT, 4))
        with patch.dict(LIMITS, instructions=3):
            with self.assertRaisesRegex(RuntimeError, "instruction bound"):
                locator.function(TEXT)
        self.assertEqual(locator.decoded, 3)

    def test_function_and_deadline_caps_stop_not_skip(self):
        locator = Locator(b"\x90" * 8193, unwind(TEXT, 8193))
        with self.assertRaisesRegex(RuntimeError, "function window bound"):
            locator.function(TEXT)
        locator = Locator(b"\xc3", unwind(TEXT, 1))
        locator.started = time.monotonic() - LIMITS["seconds"] - 1
        with self.assertRaisesRegex(RuntimeError, "deadline"):
            locator.check()

    def test_offset_store_is_candidate_not_surface_proof(self):
        code = b"\x48\x89\x48\x58\xc3"  # mov [rax+58h],rcx; ret
        locator = Locator(code, unwind(TEXT, len(code)))
        locator.function(TEXT)
        store = locator.report_functions()[0]["offset_58_candidates"][0]
        self.assertFalse(store["surface_base_traced"])
        self.assertFalse(store["writer_proved"])

    def test_bounded_reverse_route_uses_decoded_callers(self):
        target = TEXT + 0x1000
        wrapper = b"\xb9\x07\0\0\0" + call(TEXT + 5, target) + b"\xc3"
        caller_start = TEXT + 0x20
        caller = call(caller_start, TEXT) + b"\xc3"
        code = wrapper + b"\xcc" * (0x20 - len(wrapper)) + caller
        locator = Locator(code, unwind(TEXT, len(wrapper)) + unwind(caller_start, len(caller)))
        result = locator.analyze(target)
        self.assertEqual(result["registration"][0]["owner"], hex(TEXT))
        self.assertEqual(result["reverse_routes"][0]["owner"], hex(caller_start))
        self.assertFalse(result["actual_first_writer_established"])
        self.assertFalse(result["live_breakpoint_established"])


if __name__ == "__main__":
    unittest.main()

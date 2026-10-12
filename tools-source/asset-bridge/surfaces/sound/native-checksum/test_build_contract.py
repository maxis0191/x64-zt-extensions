import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_contract import COMMON_MEMBERS, CORRUPT, EXPECTED, archive_members, compare_archive, include_report, json_bytes, probe_result


def archive(objects):
    def member(name, payload):
        header = name.ljust(16) + "0".ljust(12) + "0".ljust(6) + "0".ljust(6) + "100644".ljust(8) + str(len(payload)).ljust(10) + "`\n"
        return header.encode() + payload + (b"\n" if len(payload) % 2 else b"")
    names, offsets = b"", {}
    for name in objects:
        offsets[name] = len(names)
        names += ("C:\\fixture\\common\\" + name).encode() + b"\0"
    result = b"!<arch>\n" + member("/", b"") + member("//", names)
    for name, payload in objects.items():
        result += member("/" + str(offsets[name]), payload)
    return result


class BuildContracts(unittest.TestCase):
    def test_real_probe_requires_correct_original_and_patched_modes(self):
        for original in (True, False):
            data = {"source_checksum": CORRUPT if original else EXPECTED,
                    "matches_original_md5": not original, "field_matches": True,
                    "payload_unchanged": True, "outside_field_unchanged": True,
                    "native_ff_tested": False, "ready": False}
            raw = json.dumps(data).encode()
            self.assertEqual(probe_result(raw, original), data)
            with self.assertRaisesRegex(ValueError, "digest differs"):
                probe_result(raw, not original)
            data["payload_unchanged"] = False
            with self.assertRaisesRegex(ValueError, "conservation"):
                probe_result(json.dumps(data).encode(), original)

    def test_probe_rejects_untyped_flags_duplicates_and_promotion(self):
        base = {"source_checksum": EXPECTED, "matches_original_md5": True, "field_matches": True,
                "payload_unchanged": True, "outside_field_unchanged": True, "native_ff_tested": False, "ready": False}
        for name, value in (("ready", True), ("native_ff_tested", True), ("field_matches", 1)):
            with self.assertRaises(ValueError):
                probe_result(json.dumps({**base, name: value}).encode(), False)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            json_bytes(b'{"ready":false,"READY":true}')

    def test_exact_thirteen_member_archive_and_one_replacement(self):
        old = {name: (name + "-original").encode() for name in sorted(COMMON_MEMBERS)}
        self.assertEqual(archive_members(archive(old)), old)
        changed = {**old, "bit_buffer.obj": b"actual newly compiled bit-buffer object"}
        result = compare_archive(archive(changed), changed)
        self.assertEqual(len(result), 13)
        self.assertTrue(all(archive_members(archive(changed))[name] == data
                            for name, data in old.items() if name != "bit_buffer.obj"))
        with self.assertRaisesRegex(ValueError, "payload differs"):
            compare_archive(archive(changed), old)

    def test_archive_rejects_missing_unknown_truncated_and_duplicate_member(self):
        old = {name: name.encode() for name in sorted(COMMON_MEMBERS)}
        missing = dict(old)
        del missing["thread.obj"]
        for raw in (archive(missing), archive({**old, "other.obj": b"x"}), archive(old)[:-1],
                    archive({**old, "C:\\other\\thread.obj": b"x"})):
            with self.assertRaises(ValueError):
                archive_members(raw)

    def test_include_trace_requires_exact_private_header_and_sealed_closure(self):
        expected = r"C:\review\patch-inputs\utils\bit_buffer.hpp"
        forbidden = r"C:\shared\src\common\utils\bit_buffer.hpp"
        standard = r"C:\VC\include\array"
        raw = ("Note: including file:  " + expected + "\nNote: including file: " + standard + "\n").encode()
        self.assertEqual(len(include_report(raw, [expected, standard], expected, forbidden)), 2)
        with self.assertRaisesRegex(ValueError, "unsealed include"):
            include_report(raw, [expected], expected, forbidden)
        with self.assertRaisesRegex(ValueError, "not established"):
            include_report(("Note: including file: " + standard).encode(), [standard], expected, forbidden)
        with self.assertRaisesRegex(ValueError, "wrong bit-buffer"):
            include_report(raw + ("Note: including file: " + forbidden).encode(),
                           [expected, standard, forbidden], expected, forbidden)


if __name__ == "__main__":
    unittest.main()

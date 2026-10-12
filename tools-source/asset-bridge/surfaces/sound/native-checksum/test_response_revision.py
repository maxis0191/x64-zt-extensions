import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_contract import key, reviewed_responses
from response_revision import repair


class ResponseRepair(unittest.TestCase):
    old = r"C:\fixture\runtime\zt-sound-md5-b"
    new = r"C:\fixture\runtime\zt-sound-md5-c"

    def source(self, newline="\n"):
        lines = ["/c", "/WX", "/W4", "/O1", "/MT", "/fp:precise", "/Y-", "/showIncludes"]
        for i in range(11):
            lines += ["/D", "MACRO_"+str(i)]
        lines += ['/Fo"'+self.old+r'\one.obj"', '/Fd"'+self.old+r'\private.pdb"', r'"C:\shared\source.cpp"']
        return (newline.join(lines)+newline).encode()

    def test_joins_definition_only_and_moves_private_outputs(self):
        for newline in ("\n", "\r\n"):
            before = self.source(newline)
            after, macros, moved = repair(before, self.old, self.new, True)
            self.assertEqual(macros, ["MACRO_"+str(i) for i in range(11)])
            self.assertEqual(moved, 2)
            expected = before.replace(self.old.encode(), self.new.encode())
            for macro in macros:
                expected = expected.replace(("/D"+newline+macro).encode(), ("/D"+macro).encode())
            self.assertEqual(after, expected)
            self.assertIn(b"/WX", after)
            self.assertIn(b"/fp:precise", after)
            self.assertNotIn(("/D"+newline).encode(), after)

    def test_link_response_changes_only_new_output_path(self):
        before = ('/INCREMENTAL:NO\n/OUT:"'+self.old+'\\candidate.exe"\n"C:\\shared\\old.obj"\n').encode()
        after, macros, moved = repair(before, self.old, self.new, False)
        self.assertEqual(after, before.replace(self.old.encode(), self.new.encode()))
        self.assertEqual(macros, [])
        self.assertEqual(moved, 1)

    def test_refuses_orphan_unknown_duplicate_and_unchanged_target(self):
        source = self.source()
        cases = [(source+b"/D\n", True), (source.replace(b"/D\nMACRO_0", b"/D\n/WX"), True),
                 (source.replace(b"MACRO_1\n", b"MACRO_0\n"), True), (source, False),
                 (source.replace(b"MACRO_0", b'"MACRO_0=spaced value"'), True)]
        for raw, compile_kind in cases:
            with self.subTest(raw=raw[:80]), self.assertRaises(ValueError):
                repair(raw, self.old, self.new, compile_kind)
        with self.assertRaises(ValueError):
            repair(source, self.old, self.old, True)

    def fixture_plan(self):
        pins = [{"path": r"C:\review"+"\\"+str(i)+".rsp", "bytes": 123, "sha256": format(i+1, "064x")} for i in range(12)]
        commands = [{"kind": "candidate_compile", "response_path": p["path"], "response_sha256": p["sha256"]} for p in pins]
        return {"response_pins": pins, "source_pins": copy.deepcopy(pins), "commands": commands}

    def test_new_response_sources_require_independent_bootstrap_pins(self):
        plan = self.fixture_plan()
        result = reviewed_responses(plan, {})
        self.assertEqual(len(result), 12)
        self.assertEqual(result[key(plan["response_pins"][0]["path"])]["Bytes"], 123)
        for change in ("missing-source", "changed-hash", "duplicate", "unbound-command", "old-sealed-path"):
            changed = copy.deepcopy(plan)
            sealed = {}
            if change == "missing-source":
                changed["source_pins"].pop()
            elif change == "changed-hash":
                changed["response_pins"][0]["sha256"] = "a"*64
            elif change == "duplicate":
                changed["response_pins"][-1] = changed["response_pins"][0]
            elif change == "unbound-command":
                changed["commands"][0]["response_path"] = r"C:\unreviewed.rsp"
            else:
                sealed[key(changed["response_pins"][0]["path"])] = {}
            with self.subTest(change=change), self.assertRaises(ValueError):
                reviewed_responses(changed, sealed)


if __name__ == "__main__":
    unittest.main()

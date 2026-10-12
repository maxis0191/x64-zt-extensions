"""Source portability only; never launch a native helper or rewrite a provider."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from read_sab import Inputs, sha
import sound_ff_phase as phase

REPO = Path(__file__).resolve().parents[4]
FILES = json.loads(Path(__file__).with_name("sab_ff_helpers.json").read_bytes())["files"]


def fixture(root, newline):
    for relative in FILES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((REPO / relative).read_bytes().replace(b"\r\n", b"\n").replace(b"\n", newline))


class HelperSourceTests(unittest.TestCase):
    def test_lf_crlf_same_source_but_distinct_exact_runtime_pins(self):
        for newline in (b"\n", b"\r\n"):
            with self.subTest(newline=newline), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); fixture(root, newline)
                inputs = Inputs(); phase.verify_helpers(inputs, root); inputs.recheck()
                for relative, canonical in FILES.items():
                    path = root / relative; raw = path.read_bytes()
                    self.assertEqual(phase.source_digest(raw), canonical)
                    self.assertEqual(inputs.observed[path], (len(raw), sha(raw)))
                    if newline == b"\r\n": self.assertNotEqual(sha(raw), canonical)

    def test_line_endings_changed_after_plan_observation_are_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); fixture(root, b"\n")
            inputs = Inputs(); phase.verify_helpers(inputs, root)
            path = root / "tools-source/asset-bridge/surfaces/MaterialV2.Core.ps1"
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
            with self.assertRaisesRegex(ValueError, "changed"): inputs.recheck()

    def test_real_content_changes_in_every_helper_are_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); fixture(root, b"\r\n")
            for relative in FILES:
                path = root / relative; raw = path.read_bytes(); path.write_bytes(raw + b" ")
                with self.subTest(path=relative), self.assertRaisesRegex(ValueError, "shared helper changed"):
                    phase.verify_helpers(Inputs(), root)
                path.write_bytes(raw)

    def test_no_other_normalization(self):
        raw = b"original\n"
        for changed in (b"\xef\xbb\xbf" + raw, raw[:-1], raw + b" ", b"original\r", b"Original\n"):
            self.assertNotEqual(phase.source_digest(raw), phase.source_digest(changed))
        with self.assertRaises(UnicodeDecodeError): phase.source_digest(b"\xff")

    def test_unknown_normalization_refused(self):
        actual = phase.strict_json
        def altered(raw, *args):
            value = actual(raw, *args); value["normalization"] = "strip-all-whitespace"
            return value
        with patch.object(phase, "strict_json", altered), self.assertRaisesRegex(ValueError, "explicit helper"):
            phase.verify_helpers(Inputs(), REPO)

    def test_existing_runner_and_sdk_drain_import_for_both_checkouts(self):
        # Import only: the returned functions are never executed here.
        for newline in (b"\n", b"\r\n"):
            with self.subTest(newline=newline), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); fixture(root, newline)
                runner, drain = phase.load_runner(root)
                self.assertTrue(callable(runner.run)); self.assertEqual(drain.__name__, "copy_bounded")


if __name__ == "__main__":
    unittest.main()

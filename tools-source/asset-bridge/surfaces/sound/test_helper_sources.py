"""Source portability only; never launch a native helper or rewrite a provider."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from read_sab import Inputs, sha
import sound_ff_phase as phase

REPO = Path(__file__).resolve().parents[4]
FILES = json.loads(Path(__file__).with_name(phase.HELPER_MANIFEST).read_bytes())["files"]


def fixture(root, newline):
    for relative in FILES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((REPO / relative).read_bytes().replace(b"\r\n", b"\n").replace(b"\n", newline))


class HelperSourceTests(unittest.TestCase):
    def test_legacy_helper_pin_is_preserved_and_not_current_qualification(self):
        legacy = json.loads(Path(__file__).with_name("sab_ff_helpers.json").read_bytes())["files"]
        changed = [p for p in FILES if FILES[p] != legacy[p]]
        self.assertEqual(changed, ["ops/Resource-Scheduler.Core.ps1", "ops/model-lab/ModelFF.Core.ps1"])
        self.assertEqual(legacy[changed[1]], "4dc68627b6a0b14cf41a5f77859ce7c84b2f674035fcb87cf6fb48253f21ea8e")
        prior = json.loads(Path(__file__).with_name("sab_ff_helpers-20261013.json").read_bytes())["files"]
        self.assertEqual([p for p in FILES if FILES[p] != prior[p]], changed)
        self.assertEqual(prior[changed[0]], legacy[changed[0]])
        self.assertEqual(prior[changed[1]], "63f91ad11dfb5e04e8bddfb802d0d1279c28688ed1c4aab87ef641e1cbd34abb")
        for relative in changed:
            self.assertEqual(phase.source_digest((REPO / relative).read_bytes()), FILES[relative])
            self.assertNotEqual(FILES[relative], prior[relative])

    def test_sound_job_is_only_namespace_and_counter_delta_from_shared_base(self):
        base = (REPO / "tools-source/asset-bridge/model/BuildJob.cs").read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(sha(base), "f6be2a4cafddb78b5e07a6802354575ada418cb7643d96a3abd0a4c063bc6387")
        source = Path(__file__).with_name("SoundBuildJob.cs").read_text(encoding="utf-8")
        declaration = '    [DllImport("kernel32.dll", SetLastError=true)] static extern bool QueryInformationJobObject(IntPtr job,int cls,out ExtendedLimits info,int size,out uint returned);\n'
        self.assertEqual(source.count(declaration), 1)
        start = source.index("    // Class 9: JOBOBJECT_EXTENDED_LIMIT_INFORMATION.PeakJobMemoryUsed.\n")
        end = source.index("    static void Fail()", start)
        self.assertEqual(len(source[start:end].splitlines()), 9)
        restored = (source[:start] + source[end:]).replace(declaration, "").replace(
            "namespace IW7.SoundFFTelemetryV1 {", "namespace IW7.CommunityBuild {")
        self.assertEqual(restored.encode(), base)
        # This consumer uses exact bytes, unlike the sound portable manifest.
        material = json.loads(Path(__file__).parents[1].joinpath("material_v2_helpers.json").read_bytes())
        self.assertEqual(material["tools-source/asset-bridge/model/BuildJob.cs"], sha(base))

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

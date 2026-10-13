"""Pure Python transcript tests and static checks; never compile/run the fixture."""
import contextlib
import io
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

import resident_image_fixture_check as checker

ROOT = Path(__file__).parent
CPP = (ROOT / "resident_image_fixture.cpp").read_text(encoding="utf-8")
CODE = re.sub(r"//[^\n]*|/\*.*?\*/", "", CPP, flags=re.S)
PLAN = json.loads((ROOT / "resident_image_fixture_plan.json").read_text(encoding="utf-8"))


def transcript(**changes):
    return json.dumps(dict(checker.EXPECTED, **changes)).encode("utf-8")


class FixtureTranscriptTests(unittest.TestCase):
    def test_exact_synthetic_transcript_never_proves_native_execution(self):
        data = transcript()
        result = checker.inspect(data)
        self.assertEqual(result["status"], "synthetic-transcript-checked")
        self.assertEqual(result["expected_cases"], 54)
        self.assertEqual(result["transcript_bytes"], len(data))
        self.assertRegex(result["transcript_sha256"], r"^[0-9a-f]{64}$")
        self.assertIs(result["engine_observed"], False)
        self.assertIs(result["native_execution_verified"], False)

    def test_wrong_counts_schema_callback_and_status_refused(self):
        for key, value in (("copied_cases", 5), ("format_cases", 17), ("refused_cases", 29),
                           ("largest_pixel_copy", 97), ("layout_bytes", 256), ("name_offset", 240),
                           ("schema", "iw7.t7-resident-image-fixture/2"), ("status", "pass"),
                           ("readable_callback", "VirtualQuery")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                checker.inspect(transcript(**{key: value}))

    def test_evidence_overclaims_refused(self):
        for key in ("engine_observed", "atomic_snapshot", "seh_verified"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                checker.inspect(transcript(**{key: True}))

    def test_strict_types_refuse_numeric_booleans_and_equal_floats(self):
        for key, value in (("engine_observed", 0), ("atomic_snapshot", 0),
                           ("seh_verified", 0), ("copied_cases", 6.0), ("format_cases", "18"),
                           ("refused_cases", True)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                checker.inspect(transcript(**{key: value}))

    def test_missing_extra_and_duplicate_fields_refused(self):
        missing = dict(checker.EXPECTED)
        missing.pop("seh_verified")
        duplicate = transcript()[:-1] + b', "copied_cases": 6}'
        for data in (json.dumps(missing).encode(), transcript(native_execution_verified=True), duplicate):
            with self.subTest(data=data), self.assertRaises(ValueError):
                checker.inspect(data)

    def test_malformed_truncated_trailing_and_invalid_utf8_refused(self):
        for data in (b"[]", b"null", b"", b"{", transcript()[:-1], transcript() + b"{}", b"\xff"):
            with self.subTest(data=data), self.assertRaises(ValueError):
                checker.inspect(data)

    def test_byte_limit_inclusive_and_oversize_refused(self):
        data = transcript()
        checker.inspect(data + b" " * (checker.MAX_TRANSCRIPT_BYTES - len(data)))
        with self.assertRaises(ValueError):
            checker.inspect(data + b" " * (checker.MAX_TRANSCRIPT_BYTES + 1 - len(data)))

    def test_cli_caps_read_and_reports_failure_without_launch(self):
        stream = io.BytesIO(b" " * 2048)
        with patch("sys.argv", ["checker", "synthetic-stdout.log"]), \
             patch.object(Path, "open", return_value=stream), \
             patch.object(stream, "read", wraps=stream.read) as read, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(checker.main(), 2)
            read.assert_called_once_with(1025)
        result = json.loads(output.getvalue())
        self.assertIn("error", result)
        self.assertIs(result["native_execution_verified"], False)


class FixturePreparationTests(unittest.TestCase):
    def test_real_adapter_included_and_abi_assertions_active(self):
        self.assertIn('#include "resident_image_copy.hpp"', CODE)
        self.assertIn("static_assert(sizeof(void*) == 8)", CODE)
        self.assertIn("sizeof(t7::GfxImage) == 264 && offsetof(t7::GfxImage, name) == 248", CODE)
        self.assertIn("#define assert_sizeof(T, N) static_assert(sizeof(T) == N)", CODE)
        self.assertIn("#define assert_offsetof(T, M, N) static_assert(offsetof(T, M) == N)", CODE)
        self.assertNotRegex(CODE, r"\bstruct\s+GfxImage\b|#undef\s+assert_|#if\s+0")

    def test_independent_fixture_cases_match_transcript_counts(self):
        run = CODE.split("void run()", 1)[1].split("int main", 1)[0]
        copies = re.findall(r"copies\((\d+), (\d+), (\d+), (DXGI_FORMAT_\w+), (\d+)\);", run)
        self.assertEqual([(int(w), int(h), int(m), int(n)) for w, h, m, _, n in copies],
                         [(2, 2, 1, 16), (3, 5, 3, 72), (7, 5, 3, 48),
                          (7, 5, 3, 96), (1, 1, 1, 8), (3, 2, 2, 7)])
        formats = re.findall(r"\{(DXGI_FORMAT_\w+),(\d+)\}", run)
        self.assertEqual(len(formats), checker.EXPECTED["format_cases"])
        self.assertEqual(len({name for name, _ in formats}), len(formats))
        self.assertEqual(len(re.findall(r'\b(?:changed|refusal)\("', run)), checker.EXPECTED["refused_cases"])
        self.assertIn("copied_cases == 6 && format_cases == 18 && refused_cases == 30", run)
        self.assertNotIn("image::validate(", CODE)

    def test_readability_uses_actual_bounded_storage_without_native_io(self):
        self.assertIn("std::array<std::uint8_t, 128> pixels{}", CODE)
        self.assertIn("pointer == &source && bytes == sizeof(source)", CODE)
        self.assertIn("pointer != pixels.data()", CODE)
        self.assertIn("bytes > readable_bytes", CODE)
        self.assertIn("fixture(const fixture&) = delete", CODE)
        self.assertIn("result.pixels[0] == original", CODE)
        self.assertNotRegex(CODE, r"\b(?:Virtual\w+|Create\w+|Open\w+|LoadLibrary\w*|"
                            r"ReadProcessMemory|WriteProcessMemory|DB_\w+|system|fopen|freopen|"
                            r"get_data_for_xpak_key|__try|__except)\s*\(")

    def test_proposal_inert_and_reuses_existing_owner(self):
        self.assertEqual(PLAN["source_pin"], "fab935826c898806855376662a8a03317b3ad8f1")
        for key in ("execution_authorized", "native_compiled", "native_executed"):
            self.assertIs(PLAN[key], False)
        reuse = PLAN["reuse"]
        self.assertEqual([reuse["stage_entry"], reuse["direct_compile_link_adapter"], reuse["original_owner_loop"]],
                         ["Invoke-WorldStage", "Invoke-T7OwnedStage", "Invoke-H1OwnedStage"])
        self.assertIs(reuse["new_supervisor"], False)
        self.assertIs(reuse["world_cli_accepts_this_profile_unchanged"], False)
        self.assertIs(PLAN["gates"]["retry_authorized"], False)

    def test_stages_direct_and_bind_real_headers_with_no_shell_wrapper(self):
        stages = PLAN["stages"]
        self.assertEqual([s["kind"] for s in stages], ["Compile", "Link", "Fixture", "Check"])
        compile_args = stages[0]["arguments"]
        self.assertIn("/external:I<NATIVE_SOURCE>/src/zonetool", compile_args)
        self.assertIn("/sourceDependencies", compile_args)
        self.assertIn("/WX", compile_args)
        self.assertIn("/c", compile_args)
        self.assertNotIn("/link", compile_args)
        self.assertEqual(stages[2]["tool"], "<RUN_ROOT>/link/resident_image_fixture.exe")
        self.assertEqual(stages[2]["arguments"], [])
        self.assertEqual(stages[3]["arguments"][:3], ["-I", "-S", "-B"])
        self.assertTrue(all("<" in stage["tool"] for stage in stages))
        self.assertFalse(any(re.search(r"(?:cmd|powershell|pwsh)\.exe", stage["tool"], re.I) for stage in stages))

    def test_budget_and_acceptance_preserve_proof_limits(self):
        budget = PLAN["budgets"]
        self.assertEqual(budget["fixture_stdout_acceptance_bytes"], checker.MAX_TRANSCRIPT_BYTES)
        self.assertEqual(budget["fixture_stderr_acceptance_bytes"], 0)
        self.assertEqual(budget["largest_successful_pixel_copy_bytes"], checker.EXPECTED["largest_pixel_copy"])
        self.assertIs(budget["strict_log_write_cap"], False)
        self.assertIs(budget["native_peaks_measured"], False)
        for key in ("engine_observed", "atomic_snapshot_proven", "seh_verified"):
            self.assertIs(PLAN["gates"][key], False)
        source_files = list(ROOT.glob("resident_image_fixture*")) + list(ROOT.glob("test_resident_image*.py"))
        source_files += [ROOT / "resident_image_copy.hpp", ROOT / "resident_image.py", ROOT / "T7-IMAGES.md"]
        self.assertLess(sum(path.stat().st_size for path in source_files), 1024 * 1024)


if __name__ == "__main__":
    unittest.main()

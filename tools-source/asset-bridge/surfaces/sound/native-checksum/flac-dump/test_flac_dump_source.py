"""Pure source/preparation and model tests; NOT compiled C++ or codec evidence."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import flac_dump_vectors as vectors
import prepare_flac_dump_source as prep

ROOT = Path(__file__).resolve().parent


class FlacDumpSourceTests(unittest.TestCase):
    def test_synthetic_vector_oracle_and_unique_names(self):
        cases = vectors.cases()
        self.assertGreater(len(cases), 90)
        self.assertEqual(len({c["name"] for c in cases}), len(cases))
        for case in cases:
            with self.subTest(case=case["name"]):
                raw = bytes.fromhex(case["data_hex"])
                observed = vectors.oracle(case["entry"], raw, case["null"])
                self.assertEqual(list(observed) if observed else None, case["expected"])

    def test_crc_published_check_value(self):
        # CRC-8 polynomial 0x07, init zero, no reflection/xorout.
        self.assertEqual(vectors.crc8(b"123456789"), 0xf4)
        for case in vectors.cases():
            if case["expected"]:
                start = case["entry"][1]
                raw = bytes.fromhex(case["data_hex"])[start:]
                count = case["expected"][1]
                self.assertEqual(vectors.crc8(raw[:count]), 0)

    def test_every_long_header_truncation_refused(self):
        cases = {c["name"]: c for c in vectors.cases()}
        self.assertEqual(len(vectors.header(rate_code=13)), 10)
        for length in range(10):
            self.assertIsNone(cases[f"truncated-{length}"]["expected"])

    def test_body_is_opaque_and_no_conformance_claim(self):
        case = next(c for c in vectors.cases() if c["name"] == "invalid-later-body-not-conformance")
        self.assertEqual(case["expected"], [4096, 8])
        source = (ROOT / "flac_dump_probe.cpp").read_text()
        self.assertIn('full_conformance\\\":false', source)
        self.assertIn('native_dump_tested\\\":false', source)

    def test_cpp_case_source_preserves_all_expected_values(self):
        generated = vectors.cpp_cases().decode()
        for case in vectors.cases():
            self.assertEqual(generated.count('"' + case["name"] + '"'), 1)
            self.assertIn('"' + case["data_hex"] + '"', generated)
        self.assertIn("4294967295u, 18u", generated)
        self.assertLess(len(generated), 32768)

    def test_patch_touches_only_sound_dump_and_checked_reader(self):
        source = (ROOT / "zonetool-fab9358-flac-dump.patch").read_text()
        self.assertEqual(source.count("diff --git "), 1)
        self.assertIn("a/" + prep.SOURCE_REL, source)
        added = "\n".join(line[1:] for line in source.splitlines() if line.startswith("+") and not line.startswith("+++"))
        self.assertIn("info.min_blocksize = derived.block_size;", added)
        self.assertIn("info.max_blocksize = derived.block_size;", added)
        self.assertNotIn("4096", added)
        self.assertNotIn("BlocksizeKB", added)
        self.assertNotIn("info.md5sum", added)
        self.assertNotIn("source_checksum", added)
        self.assertNotIn("read_bytes", added)
        self.assertIn("file.read(target, 1, count) != count", added)
        self.assertIn("file.write(buffer.data(), 1, buffer.size())", added)
        self.assertIn("written != buffer.size() || closed != 0", added)
        self.assertIn("std::memchr(asset_name, 0, sizeof(asset_name))", added)
        self.assertLess(added.index("flac_metadata::derive"), added.index('file.open("wb")'))
        self.assertIn('ZONETOOL_FATAL("FLAC dump refused', added)

    def test_helper_has_no_io_or_shared_bit_reader(self):
        source = (ROOT / "sound_flac_metadata.hpp").read_text()
        for forbidden in ("filesystem", "read_bits", "BlocksizeKB", "new ", "malloc", "4096", "fopen"):
            self.assertNotIn(forbidden, source)
        self.assertIn("static_cast<std::uint64_t>(entry.encoded_bytes) + entry.seek_bytes", source)
        self.assertIn("count <= extent - offset", source)

    def test_strict_patch_applier_context_counts_and_target(self):
        prefix = f"diff --git a/{prep.SOURCE_REL} b/{prep.SOURCE_REL}\n--- a/{prep.SOURCE_REL}\n+++ b/{prep.SOURCE_REL}\n"
        change = prefix + "@@ -1,2 +1,3 @@\n one\n-two\n+TWO\n+three\n"
        self.assertEqual(prep.apply_source_patch("one\ntwo\n", change), "one\nTWO\nthree\n")
        for bad in (change.replace("-two", "-wrong"), change.replace("+1,3", "+1,4"),
                    change.replace(prep.SOURCE_REL, "other.cpp"), change.replace("+1,3", "+2,3"), prefix):
            with self.subTest(bad=bad[-50:]), self.assertRaises(ValueError):
                prep.apply_source_patch("one\ntwo\n", bad)

    def test_unknown_source_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            parent = repo / "runtime/content-surfaces"
            parent.mkdir(parents=True)
            source = repo / "sound_bank.cpp"
            source.write_text("unreviewed source")
            output = parent / "original-sound-flac-dump-source-test"
            with self.assertRaisesRegex(ValueError, "pinned upstream"):
                prep.prepare(repo, source, output)
            self.assertFalse(output.exists())

    def test_existing_or_escaping_output_refused_without_source_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            parent = repo / "runtime/content-surfaces"
            parent.mkdir(parents=True)
            occupied = parent / "original-sound-flac-dump-source-test"
            occupied.mkdir()
            for out in (occupied, repo / "original-sound-flac-dump-source-other"):
                with patch.object(prep, "small", side_effect=AssertionError("must not read")):
                    with self.assertRaisesRegex(ValueError, "fresh private"):
                        prep.prepare(repo, repo / "sound_bank.cpp", out)


if __name__ == "__main__":
    unittest.main()

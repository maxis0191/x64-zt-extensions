"""Source-model regression only; this does not compile/execute the C++ fixture."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest

from test_sab import fixture

ROOT = Path(__file__).resolve().parent
CONTRACT = json.loads((ROOT / "native-checksum/source-contract.json").read_bytes())


def cursor_model(streaminfo, width):
    """Explain cursor movement and low-byte truncation, not MSVC FP overflow.

    The old read_bits_internal also converts pow(2,p) beyond a uint64 range.
    Its complete C++ behavior is not inferred by this arbitrary-precision model.
    The pinned E7 output already supplies the observed 78 + fifteen zero bytes.
    """
    position, reads, result = 144, [], bytearray()
    for _ in range(16):
        reads.append((position, width, position + width <= len(streaminfo) * 8))
        value = int.from_bytes(streaminfo[position // 8:(position + width) // 8], "big") if reads[-1][2] else 0
        result.append(value & 255)
        position += width
    return bytes(result), reads, position


class NativeChecksumSourceTests(unittest.TestCase):
    def test_exact_original_streaminfo_and_retained_failure(self):
        raw = bytes.fromhex(CONTRACT["original_streaminfo_hex"])
        checkpoint = json.loads((ROOT / "sab-ff-checkpoint-2026-10-12.json").read_bytes())
        self.assertEqual(len(raw), 34)
        self.assertEqual(raw[18:].hex(), CONTRACT["expected_pcm_md5"])
        self.assertEqual(checkpoint["sab_source_checksum_observed"], CONTRACT["observed_sab_source_checksum"])
        self.assertEqual(checkpoint["source_pcm_md5"], raw[18:].hex())
        self.assertFalse(checkpoint["full_independent_bank_validation_passed"])
        probe = (ROOT / "native-checksum/checksum_probe.cpp").read_text()
        streaminfo = re.search(r"streaminfo\{(.*?)\};", probe, re.S).group(1)
        native_bytes = bytes(int(value, 16) for value in re.findall(r"0x([0-9a-f]{2})", streaminfo))
        self.assertEqual(native_bytes, raw)
        expected = re.search(r"original_md5\{(.*?)\};", probe, re.S).group(1)
        native_md5 = bytes(int(value, 16) for value in re.findall(r"0x([0-9a-f]{2})", expected))
        self.assertEqual(native_md5, raw[18:])

    def test_bad_cursor_width_explains_observed_tail_and_fifteen_overreads(self):
        result, reads, position = cursor_model(bytes.fromhex(CONTRACT["original_streaminfo_hex"]), 128)
        self.assertEqual(result.hex(), CONTRACT["observed_sab_source_checksum"])
        self.assertEqual(sum(valid for _, _, valid in reads), 1)
        self.assertEqual(reads[0], (144, 128, True))
        self.assertEqual(reads[1], (272, 128, False))
        self.assertEqual(position, 144 + 16 * 128)

    def test_bytewise_copy_reads_128_bits_total_without_overread(self):
        result, reads, position = cursor_model(bytes.fromhex(CONTRACT["original_streaminfo_hex"]), 8)
        self.assertEqual(result.hex(), CONTRACT["expected_pcm_md5"])
        self.assertTrue(all(valid for _, _, valid in reads))
        self.assertEqual(position, 272)
        self.assertEqual(sum(width for _, width, _ in reads), 128)

    def test_observed_field_is_not_an_endian_permutation(self):
        expected = bytes.fromhex(CONTRACT["expected_pcm_md5"])
        observed = bytes.fromhex(CONTRACT["observed_sab_source_checksum"])
        self.assertNotEqual(Counter(expected), Counter(observed))
        self.assertEqual(observed[1:], bytes(15))

    def test_synthetic_field_write_preserves_original_seek_frame_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            source, banks, _, _ = fixture(Path(temp))
            flac = (source / "sound_assets/community/original_chime_v1.flac").read_bytes()
            seeded = bytearray((banks / "sdk_original_sound_v1.sabl").read_bytes())
            offset = CONTRACT["sab_source_checksum_offset"]
            seeded[offset:offset + 16] = b"\xa5" * 16
            before = bytes(seeded)
            result, _, _ = cursor_model(flac[8:42], 8)
            out = bytearray(before)
            # Test a newly generated synthetic envelope only, never retained A.
            out[offset:offset + 16] = result
            self.assertEqual(out[offset:offset + 16], flac[26:42])
            self.assertEqual(out[:offset], before[:offset])
            self.assertEqual(out[offset + 16:], before[offset + 16:])
            self.assertEqual([i for i, (old, new) in enumerate(zip(before, out)) if old != new], list(range(offset, offset + 16)))
            self.assertEqual(out[4096:4096 + 96348], flac[46:])
            self.assertEqual(hashlib.md5(out[4096:4096 + 96348]).hexdigest(), "300613dc8d3bf1f785a7345a0466d15c")

    def test_private_patch_is_one_byte_width_fix_and_reader_stays_strict(self):
        patch = (ROOT / "native-checksum" / CONTRACT["patch"]["path"]).read_bytes()
        self.assertEqual(hashlib.sha256(patch).hexdigest(), CONTRACT["patch"]["sha256"])
        minus = [s for s in patch.decode().splitlines() if s.startswith("-") and not s.startswith("---")]
        plus = [s for s in patch.decode().splitlines() if s.startswith("+") and not s.startswith("+++")]
        self.assertEqual(len(minus), 1)
        self.assertEqual(len(plus), 1)
        self.assertIn("read_bits<std::uint8_t>(num_bits)", minus[0])
        self.assertIn("read_bits<std::uint8_t>(8)", plus[0])
        reader = (ROOT / "read_sab.py").read_text()
        self.assertIn('== hashlib.md5(pcm).digest() == flac[26:42], "SAB PCM checksum mismatch"', reader)


if __name__ == "__main__":
    unittest.main()

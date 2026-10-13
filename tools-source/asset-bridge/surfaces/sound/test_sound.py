"""Source-only PCM/FLAC controls. No executable, SAB/FF or playback test."""
import ast
import csv
import hashlib
import io
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import wave

import pcm_source as enc
import prepare_sound as prep
import read_flac as reader


class SoundTests(unittest.TestCase):
    def setUp(self):
        self.wav = enc.original_wave()
        self.pcm = enc.read_wave(self.wav)
        self.flac = enc.encode_flac(self.pcm)

    def test_original_wave_stdlib_reader(self):
        with wave.open(io.BytesIO(self.wav)) as f:
            self.assertEqual((f.getnchannels(), f.getsampwidth(), f.getframerate(), f.getnframes()),
                             (1, 2, 48000, 48000))
            self.assertEqual(f.readframes(48000), self.pcm)
        samples = struct.unpack("<48000h", self.pcm)
        self.assertLessEqual(max(map(abs, samples)), 4096)
        self.assertEqual(samples[:2400], (0,) * 2400)
        self.assertEqual(samples[43200:], (0,) * 4800)

    def test_reproducible(self):
        self.assertEqual(self.wav, enc.original_wave())
        self.assertEqual(self.flac, enc.encode_flac(self.pcm))

    def test_separate_decoder_roundtrip(self):
        pcm, report = reader.decode(self.flac)
        self.assertEqual(pcm, self.pcm)
        self.assertEqual(report["pcm_sha256"], hashlib.sha256(self.pcm).hexdigest())
        self.assertEqual(report["frames"], 12)
        self.assertFalse(report["native_codec_verified"])
        self.assertFalse(report["ready"])

    def test_boundary_blocks(self):
        for count in (16, 4095, 4096, 4097, 8192, 96000):
            with self.subTest(count=count):
                pcm = struct.pack("<h", -32768) * count
                decoded, report = reader.decode(enc.encode_flac(pcm))
                self.assertEqual(decoded, pcm)
                self.assertEqual(report["samples"], count)

    def test_signed_extremes(self):
        pcm = struct.pack("<hhhh", -32768, -1, 0, 32767) * 20
        self.assertEqual(reader.decode(enc.encode_flac(pcm))[0], pcm)

    def test_crc_known_checks(self):
        self.assertEqual(enc.crc(b"123456789", 8, 7), 0xF4)
        self.assertEqual(enc.crc(b"123456789", 16, 0x8005), 0xFEE8)
        self.assertEqual(reader.remainder(b"123456789\xf4", 8, 7), 0)
        self.assertEqual(reader.remainder(b"123456789\xfe\xe8", 16, 0x8005), 0)

    def test_decoder_does_not_import_encoder(self):
        tree = ast.parse(Path(reader.__file__).read_text())
        modules = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        modules += [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
        self.assertNotIn("pcm_source", modules)
        self.assertNotIn("prepare_sound", modules)

    def test_wave_refusals(self):
        cases = {"truncated": self.wav[:-1], "trailing": self.wav + b"\0",
                 "empty": b"", "oversize": b"\0" * 192045}
        for label, offset, replacement in (("riff", 0, b"RF64"), ("format", 20, b"\3\0"),
                                           ("stereo", 22, b"\2\0"), ("rate", 24, struct.pack("<I", 44100)),
                                           ("byterate", 28, b"\0\0\0\0"), ("align", 32, b"\0\4"),
                                           ("bits", 34, b"\x18\0"), ("chunk", 36, b"JUNK")):
            bad = bytearray(self.wav)
            bad[offset:offset + len(replacement)] = replacement
            cases[label] = bytes(bad)
        for label, data in cases.items():
            with self.subTest(label=label), self.assertRaises(ValueError):
                enc.read_wave(data)

    def test_pcm_bounds(self):
        for data in (b"", b"\0" * 30, b"\0" * 33, b"\0" * 192002):
            with self.subTest(size=len(data)), self.assertRaises(ValueError):
                enc.encode_flac(data)

    def test_flac_metadata_refusals(self):
        for offset in (0, 4, 7, 8, 12, 15, 18, 25, 26, 42, 45, 46, 54, 63):
            bad = bytearray(self.flac)
            bad[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                reader.decode(bytes(bad))

    def test_flac_frame_refusals(self):
        start = 46 + int.from_bytes(self.flac[43:46], "big")
        for offset in (0, 1, 2, 3, 4, 5, 7, 8, 20, 8202):
            bad = bytearray(self.flac)
            bad[start + offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                reader.decode(bytes(bad))

    def test_valid_crc_cannot_hide_pcm_change(self):
        # Repair the frame checksum after changing one sample: STREAMINFO MD5 must still fail.
        bad = bytearray(self.flac)
        start = 46 + int.from_bytes(bad[43:46], "big")
        end = start + 8 + 1 + 4096 * 2
        bad[start + 9] ^= 1
        bad[end:end + 2] = struct.pack(">H", enc.crc(bad[start:end], 16, 0x8005))
        with self.assertRaisesRegex(ValueError, "MD5"):
            reader.decode(bytes(bad))

    def test_truncated_or_extra_flac_refused(self):
        for data in (self.flac[:40], self.flac[:-1], self.flac + b"\0", b"\0" * 200001):
            with self.subTest(size=len(data)), self.assertRaises(ValueError):
                reader.decode(data)

    def test_alias_exact_columns_no_retail(self):
        fields = prep.parse_json((prep.SURFACES / "source_contract.json").read_bytes())["alias_csv_fields"]
        rows = list(csv.reader(io.StringIO(prep.alias_csv(fields).decode())))
        self.assertEqual(rows[0], fields)
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(rows[1]), 53)
        row = dict(zip(fields, rows[1]))
        self.assertEqual((row["Name"], row["File"], row["type"], row["loop"]),
                         (prep.ALIAS, prep.SAMPLE, "loaded", "nonlooping"))
        for key in ("SecondaryAliasName", "StopAliasName", "duck", "Subtitle"):
            self.assertEqual(row[key], "")
        self.assertEqual((row["ignoreDistanceCheck"], row["precached"], row["ForceSubtitle"]),
                         ("False", "True", "False"))

    def test_plan_writes_nothing(self):
        fields = prep.parse_json((prep.SURFACES / "source_contract.json").read_bytes())["alias_csv_fields"]
        with tempfile.TemporaryDirectory() as root, patch.object(prep, "contract", return_value=(fields, {})):
            out = Path(root) / "absent"
            report = prep.prepare(root, out)
            self.assertFalse(out.exists())
            self.assertEqual(report["status"], "Plan")
            self.assertFalse(report["native_sab_built"])
            self.assertFalse(report["ready"])

    def test_source_write_and_overwrite_refusal(self):
        fields = prep.parse_json((prep.SURFACES / "source_contract.json").read_bytes())["alias_csv_fields"]
        with tempfile.TemporaryDirectory() as root, patch.object(prep, "contract", return_value=(fields, {})):
            out = Path(root) / "source"
            report = prep.prepare(root, out, write_source=True)
            for name, entry in report["source_files"].items():
                self.assertEqual(prep.digest((out / name).read_bytes()), entry["sha256"])
            self.assertEqual(len(list(out.rglob("*.sabl"))), 0)
            self.assertEqual(len(list(out.rglob("*.ff"))), 0)
            preflight = prep.parse_json((out / "content-preflight.json").read_bytes())
            self.assertEqual((preflight["errors"], preflight["pending"]), (0, 1))
            before = {str(p): p.read_bytes() for p in out.rglob("*") if p.is_file()}
            with self.assertRaisesRegex(ValueError, "fresh absent"):
                prep.prepare(root, out, write_source=True)
            self.assertEqual(before, {str(p): p.read_bytes() for p in out.rglob("*") if p.is_file()})

    def test_original_attestation_required(self):
        fields = prep.parse_json((prep.SURFACES / "source_contract.json").read_bytes())["alias_csv_fields"]
        with tempfile.TemporaryDirectory() as root, patch.object(prep, "contract", return_value=(fields, {})):
            path = Path(root) / "original.wav"
            path.write_bytes(self.wav)
            with self.assertRaisesRegex(ValueError, "attestation"):
                prep.prepare(root, Path(root) / "out", path)
            report = prep.prepare(root, Path(root) / "out", path, attest_original=True)
            self.assertIn("caller-attested", report["provenance"])
            self.assertFalse((Path(root) / "out").exists())

    def test_missing_pin_refused_before_write(self):
        with tempfile.TemporaryDirectory() as root:
            out = Path(root) / "out"
            with self.assertRaises((ValueError, FileNotFoundError)):
                prep.prepare(root, out, write_source=True)
            self.assertFalse(out.exists())

    def test_alias_mutation_before_preflight_refuses_success_manifest(self):
        fields = prep.parse_json((prep.SURFACES / "source_contract.json").read_bytes())["alias_csv_fields"]
        original_inspector = prep.Inspector
        with tempfile.TemporaryDirectory() as root, patch.object(prep, "contract", return_value=(fields, {})):
            out = Path(root) / "source"

            class MutatingInspector(original_inspector):
                def soundbank(self, name):
                    path = out / ("sound/" + prep.BANK + ".aliases.csv")
                    path.write_bytes(path.read_bytes().replace(b",0.5,0.5,", b",0.2,0.2,"))
                    return super().soundbank(name)

            with patch.object(prep, "Inspector", MutatingInspector), self.assertRaisesRegex(ValueError, "preflight bytes"):
                prep.prepare(root, out, write_source=True)
            self.assertFalse((out / "sound-source.json").exists())
            self.assertIn(b",0.2,0.2,", (out / ("sound/" + prep.BANK + ".aliases.csv")).read_bytes())

    def test_uninspected_file_mutation_refuses_success_manifest(self):
        fields = prep.parse_json((prep.SURFACES / "source_contract.json").read_bytes())["alias_csv_fields"]
        original_inspector = prep.Inspector
        for relative in ("original/source.wav", "pcm-readback.json", "zone_source/" + prep.ZONE + ".csv",
                         "sound/" + prep.BANK + ".aliases.csv", "soundbank/" + prep.BANK + ".json",
                         "sound_assets/" + prep.SAMPLE + ".flac"):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as root, patch.object(prep, "contract", return_value=(fields, {})):
                out = Path(root) / "source"

                class MutatingInspector(original_inspector):
                    def soundbank(self, name):
                        result = super().soundbank(name)
                        path = out / relative
                        path.write_bytes(path.read_bytes() + b"changed")
                        return result

                with patch.object(prep, "Inspector", MutatingInspector), self.assertRaisesRegex(ValueError, "prepared file changed"):
                    prep.prepare(root, out, write_source=True)
                self.assertFalse((out / "sound-source.json").exists())
                self.assertTrue((out / relative).read_bytes().endswith(b"changed"))


if __name__ == "__main__":
    unittest.main()

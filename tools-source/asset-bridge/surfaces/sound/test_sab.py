"""Original synthetic fixtures only; no native process, stock or retail bank."""
import ast
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import pcm_source
import prepare_sound
import read_sab as reader

CONTRACT = Path(__file__).with_name("sab_contract.json")


def fixture(root):
    """Hand-packed expected layout; deliberately does not call the SAB reader."""
    root = Path(root)
    source, banks, dump = root / "source", root / "banks", root / "dump"
    for folder in (source, banks, dump):
        folder.mkdir()
    wav = pcm_source.original_wave()
    pcm = wav[44:]
    flac = pcm_source.encode_flac(pcm)
    common = json.loads((Path(__file__).parents[1] / "source_contract.json").read_text())
    alias = prepare_sound.alias_csv(common["alias_csv_fields"])
    bank = dict(name="community_original_sound_v1.all", zone="sdk_original_sound_v1",
                gameLanguage="all", soundLanguage="all", aliases=["sound/community_original_sound_v1.all.aliases.csv"])
    bank.update({key: [] for key in prepare_sound.SOUND_TABLES})
    files = {"original/source.wav": wav, "sound_assets/community/original_chime_v1.flac": flac,
             "sound/community_original_sound_v1.all.aliases.csv": alias,
             "soundbank/community_original_sound_v1.all.json": prepare_sound.encoded(bank),
             "zone_source/sdk_original_sound_v1.csv": b"soundbank,community_original_sound_v1.all\n"}
    for name, data in files.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    for streamed in (False, True):
        size = 4096 if streamed else 114816
        raw = bytearray(size)
        packed = struct.pack("<8I3Q16s512s2Q64s8s3s2I5s", 0x23585532, 4, 44, 16, 64,
                             0 if streamed else 1, 8, 4, size, 0 if streamed else 102400,
                             0 if streamed else 106496, b"\xcc" * 16, bytes(512),
                             0 if streamed else 110592, 0 if streamed else 114688,
                             b"sdk_original_sound_v1", b"pc", b"all", 4, 0 if streamed else 98304, bytes(5))
        raw[:len(packed)] = packed
        if not streamed:
            raw[4096:100444] = flac[46:]
            raw[102400:102444] = struct.pack("<5IQiBBBHH5B", 1496246593, 96132, 216, 48000, 0,
                                           4096, 48000, 1, 0, 8, 0, 0, 0, 0, 0, 0, 0)
            raw[106496:106512] = hashlib.md5(flac[46:]).digest()
            raw[110592:110608] = hashlib.md5(pcm).digest()
            name = b"community/original_chime_v1"
            raw[114688:114688 + len(name)] = name
        (banks / ("sdk_original_sound_v1.sabs" if streamed else "sdk_original_sound_v1.sabl")).write_bytes(raw)
    for relative, data in (("sound/community_original_sound_v1.all.aliases.csv", alias),
                            ("sound_assets/community/original_chime_v1.flac", flac)):
        path = dump / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = bytearray(data)
        if relative.endswith(".flac"):
            raw[8:18] = b"\x04\x00\x04\x00" + bytes(6)
            raw[26:42] = bytes(16)
        path.write_bytes(raw)
    inventory = root / "verify.log"
    inventory.write_text('Loading zone "sdk_original_sound_v1"\nLoading asset "community_original_sound_v1.all" of type soundbank.\n')
    return source, banks, dump, inventory


class SABTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source, self.banks, self.dump, self.inventory = fixture(self.temp.name)
        self.sabl = self.banks / "sdk_original_sound_v1.sabl"
        self.sabs = self.banks / "sdk_original_sound_v1.sabs"

    def inspect(self, dump=True):
        return reader.inspect(self.source, self.banks, CONTRACT,
                              self.dump if dump else None, self.inventory if dump else None)

    def test_original_bank_and_dump_pass_without_overclaim(self):
        result = self.inspect()
        self.assertEqual(result["loaded"]["samples"], 48000)
        self.assertEqual(result["streamed"]["entries"], 0)
        self.assertTrue(result["dump_alias_values_verified"])
        self.assertTrue(result["inventory_verified"])
        self.assertTrue(result["loaded"]["payload_md5_verified"])
        self.assertTrue(result["loaded"]["pcm_md5_verified"])
        for flag in ("native_alias_index_verified", "checksum_checksum_verified", "dump_standalone_flac_validated", "ready", "playback_verified"):
            self.assertFalse(result[flag])
        self.assertLess(result["input_bytes_read_including_recheck"], 2 * 1024 * 1024)
        self.assertLess(sum(p.stat().st_size for p in Path(self.temp.name).rglob("*") if p.is_file()), 1024 * 1024)

    def test_bank_only_does_not_claim_dump_or_inventory(self):
        result = self.inspect(False)
        self.assertFalse(result["inventory_verified"])
        self.assertFalse(result["dump_alias_values_verified"])

    def test_reader_imports_no_encoder_or_writer(self):
        tree = ast.parse(Path(reader.__file__).read_text())
        names = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        self.assertIn("read_flac", names)
        self.assertFalse({"pcm_source", "prepare_sound"} & set(names))

    def test_every_header_field_is_bound(self):
        original = self.sabl.read_bytes()
        # Start of every scalar/string/reserved field in the packed 688B header.
        for offset in (0, 4, 8, 12, 16, 20, 24, 28, 32, 40, 48, 56, 72, 584, 592, 600, 664, 672, 675, 679, 683):
            with self.subTest(offset=offset):
                raw = bytearray(original); raw[offset] ^= 1; self.sabl.write_bytes(raw)
                with self.assertRaises(ValueError): self.inspect(False)
        self.sabl.write_bytes(original)

    def test_every_entry_field_is_bound(self):
        original = self.sabl.read_bytes()
        for offset in (0, 4, 8, 12, 16, 20, 28, 32, 33, 34, 35, 37, 39, 40, 41, 42, 43):
            with self.subTest(offset=offset):
                raw = bytearray(original); raw[102400 + offset] ^= 1; self.sabl.write_bytes(raw)
                with self.assertRaises(ValueError): self.inspect(False)

    def test_padding_and_names_cannot_hide_surplus(self):
        original = self.sabl.read_bytes()
        for offset in (688, 4095, 100444, 102443 + 1, 106512, 110608, 114688, 114815):
            with self.subTest(offset=offset):
                raw = bytearray(original); raw[offset] ^= 1; self.sabl.write_bytes(raw)
                with self.assertRaises(ValueError): self.inspect(False)

    def test_truncation_and_trailing_bytes_rejected(self):
        for path in (self.sabl, self.sabs):
            raw = path.read_bytes()
            for changed in (raw[:40], raw[:-1], raw + b"\0", raw + bytes(300000)):
                with self.subTest(path=path.name, size=len(changed)):
                    path.write_bytes(changed)
                    with self.assertRaises(ValueError): self.inspect(False)
            path.write_bytes(raw)

    def test_seek_frame_and_both_checksums_rejected(self):
        original = self.sabl.read_bytes()
        for offset in (4096, 4096 + 216, 4096 + 216 + 9, 100443, 106496, 110592):
            with self.subTest(offset=offset):
                raw = bytearray(original); raw[offset] ^= 1; self.sabl.write_bytes(raw)
                with self.assertRaises(ValueError): self.inspect(False)

    def test_streamed_bank_cannot_contain_entry(self):
        raw = bytearray(self.sabs.read_bytes()); struct.pack_into("I", raw, 20, 1); self.sabs.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "empty SABS"): self.inspect(False)

    def test_contract_refuses_unknown_duplicate_noninteger_and_nonfinite(self):
        raw = CONTRACT.read_bytes()
        for field in ("samples", "sample_rate", "channels", "bits_per_sample", "alias_id", "asset_id"):
            for value in (True, None, "48000", 48000.0, -1, 1 << 64):
                altered = json.loads(raw); altered[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    reader.contract(json.dumps(altered).encode())
        for altered in (raw.replace(b'"samples": 48000', b'"samples": 48000, "samples": 48000'),
                        raw.replace(b'"samples": 48000', b'"samples": NaN'),
                        raw.replace(b'"samples": 48000', b'"surplus": 1, "samples": 48000')):
            with self.assertRaises(ValueError): reader.contract(altered)

    def test_source_pin_fields_and_sizes_strict(self):
        for value in (True, 96044.0, "96044", 0, 1 << 50):
            spec = json.loads(CONTRACT.read_bytes()); spec["sources"]["original/source.wav"]["bytes"] = value
            with self.subTest(value=value), self.assertRaises(ValueError): reader.contract(json.dumps(spec).encode())
        spec = json.loads(CONTRACT.read_bytes()); spec["sources"]["../outside"] = spec["sources"]["original/source.wav"]
        with self.assertRaises(ValueError): reader.contract(json.dumps(spec).encode())

    def test_changed_source_alias_or_original_pcm_refused(self):
        for relative in (reader.ALIAS_PATH, "original/source.wav", reader.FLAC_PATH, reader.BANK_PATH):
            path = self.source / relative; original = path.read_bytes()
            path.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
            with self.subTest(path=relative), self.assertRaisesRegex(ValueError, "source changed"): self.inspect(False)
            path.write_bytes(original)

    def test_dump_alias_semantics_and_positional_header(self):
        path = self.dump / reader.ALIAS_PATH; original = path.read_bytes()
        path.write_bytes(original.replace(b",0.5,0.5,", b",0.500000,0.500000,"))
        self.assertTrue(self.inspect()["dump_alias_values_verified"])
        for altered in (original.replace(b",0.5,0.5,", b",NaN,0.5,"), original.replace(b",0.5,0.5,", b",0.2,0.5,"),
                        original.replace(b"community_original_chime_v1", b"other_alias"), original + original.splitlines()[1] + b"\n",
                        original.replace(b"vol_min,vol_max", b"vol_max,vol_min")):
            path.write_bytes(altered)
            with self.assertRaises(ValueError): self.inspect()

    def test_dump_payload_or_lossy_header_must_match_exact_contract(self):
        path = self.dump / reader.FLAC_PATH; original = path.read_bytes()
        for offset in (8, 12, 18, 26, 42, 46, 262, len(original)-1):
            changed = bytearray(original); changed[offset] ^= 1; path.write_bytes(changed)
            with self.subTest(offset=offset), self.assertRaisesRegex(ValueError, "dump FLAC"): self.inspect()

    def test_inventory_missing_duplicate_extra_or_errors_refused(self):
        original = self.inventory.read_bytes()
        for raw in (b"", original + original, original.replace(b"soundbank.", b"material."),
                    original + b'[ ERROR ] failure\n', original + b'Loading asset "extra" of type image.\n'):
            self.inventory.write_bytes(raw)
            with self.assertRaises(ValueError): self.inspect()

    def test_partial_dump_request_refused(self):
        with self.assertRaisesRegex(ValueError, "together"):
            reader.inspect(self.source, self.banks, CONTRACT, self.dump)

    def test_final_recheck_refuses_drift(self):
        actual = reader.read_bank
        def tamper(*args, **kwargs):
            result = actual(*args, **kwargs)
            if args[1]:
                path = self.source / reader.ALIAS_PATH
                path.write_bytes(path.read_bytes().replace(b"0.5,0.5", b"0.2,0.5"))
            return result
        with patch.object(reader, "read_bank", side_effect=tamper), self.assertRaisesRegex(ValueError, "between reads"):
            self.inspect(False)

    def test_link_and_total_read_bounds(self):
        with patch.object(Path, "is_junction", return_value=True), self.assertRaisesRegex(ValueError, "linked"):
            reader.Inputs().read(CONTRACT)
        inputs = reader.Inputs(); inputs.total = reader.MAX_TOTAL
        with self.assertRaisesRegex(ValueError, "total read"): inputs.read(CONTRACT)


if __name__ == "__main__":
    unittest.main()

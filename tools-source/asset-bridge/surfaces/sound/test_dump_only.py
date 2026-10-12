"""Synthetic dump bytes only. No native tool, reservation, or retained payload."""
import copy
from pathlib import Path
import tempfile
import unittest

import read_sab
import sound_ff_phase
from test_sab import CONTRACT, fixture
from test_sab_ff import spec


class DumpOnlyTests(unittest.TestCase):
    def test_profiles_remain_distinct_and_entire_dump_is_bound(self):
        with tempfile.TemporaryDirectory() as root:
            source, banks, dump, inventory = fixture(root)
            path = dump / read_sab.FLAC_PATH
            legacy = path.read_bytes()
            self.assertEqual(read_sab.inspect(source, banks, CONTRACT, dump, inventory)["dump_streaminfo_block_size"], 1024)
            with self.assertRaises(ValueError):
                read_sab.inspect(source, banks, CONTRACT, dump, inventory, "DumpOnlyC")
            current = bytearray(legacy)
            current[8:12] = b"\x10\x00\x10\x00"
            path.write_bytes(current)
            report = read_sab.inspect(source, banks, CONTRACT, dump, inventory, "DumpOnlyC")
            self.assertEqual(report["dump_streaminfo_block_size"], 4096)
            self.assertEqual(report["inventory_provenance"], "PreservedBuildF")
            self.assertTrue(report["dump_seek_frame_bytes_verified"])
            for name in ("ready", "playback_verified", "dump_standalone_flac_validated", "native_alias_index_verified"):
                self.assertFalse(report[name])
            with self.assertRaises(ValueError):
                read_sab.inspect(source, banks, CONTRACT, dump, inventory)
            # Both block bounds, each frame-size byte, MD5, seek table, first and
            # final audio frame, and trailing data must retain their exact bytes.
            for offset in (8, 10, *range(12, 18), 26, 41, 46, 261, 262, len(current) - 1):
                with self.subTest(offset=offset):
                    changed = bytearray(current); changed[offset] ^= 1; path.write_bytes(changed)
                    with self.assertRaises(ValueError):
                        read_sab.inspect(source, banks, CONTRACT, dump, inventory, "DumpOnlyC")
            path.write_bytes(current + b"extra")
            with self.assertRaises(ValueError):
                read_sab.inspect(source, banks, CONTRACT, dump, inventory, "DumpOnlyC")

    def test_unknown_or_missing_dump_profile_fails_before_reads(self):
        for profile, dump in (("anything", None), ("DumpOnlyC", None)):
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                read_sab.inspect("absent", "absent", "absent", dump_profile=profile)

    def test_candidate_c_accepts_only_exact_dump(self):
        with tempfile.TemporaryDirectory() as root:
            current = spec(root, "dump"); current["sha256"] = sound_ff_phase.DUMP_C_SHA
            self.assertIs(sound_ff_phase.validate(current), current)
            for phase in ("build", "verify"):
                changed = spec(root, phase); changed["sha256"] = sound_ff_phase.DUMP_C_SHA
                with self.subTest(phase=phase), self.assertRaises(ValueError):
                    sound_ff_phase.validate(changed)
            for key, value in (("sha256", "0" * 64), ("timeout", 241), ("arguments", current["arguments"] + ["-verifyzone"])):
                changed = copy.deepcopy(current); changed[key] = value
                with self.subTest(key=key), self.assertRaises(ValueError):
                    sound_ff_phase.validate(changed)

    def test_reader_accepts_only_closed_profile_switch(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            args = ["-B", str(root / "read_sab.py")]
            for name in ("source", "banks", "contract", "dump", "inventory"):
                args.extend(["--" + name, str(root / name)])
            item = dict(schema="iw7.material-v2-phase/1", phase="read", exe=str(root / "python.exe"),
                        sha256=sound_ff_phase.PYTHON_SHA, arguments=args, cwd=str(root), logs=str(root / "logs"), timeout=30)
            sound_ff_phase.validate(item)
            item["arguments"] = args + ["--dump-profile", "DumpOnlyC"]
            sound_ff_phase.validate(item)
            for suffix in (["--dump-profile", "NativeDumpF"], ["--dump-profile", "4096"], ["--anything", "DumpOnlyC"]):
                item["arguments"] = args + suffix
                with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                    sound_ff_phase.validate(item)


if __name__ == "__main__":
    unittest.main()

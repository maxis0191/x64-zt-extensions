"""Standard filenames and bank.zone are independent synthetic assertions."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import read_sab as reader
import sound_ff_phase
from test_sab import CONTRACT, fixture
from test_sab_ff import spec


class StandardModTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source, self.banks, self.dump, self.inventory = fixture(self.temp.name)
        for suffix in ("sabl", "sabs"):
            old = self.banks / (reader.ZONE + "." + suffix)
            raw = bytearray(old.read_bytes()); raw[600:664] = b"mod" + bytes(61)
            old.unlink(); (self.banks / ("mod." + suffix)).write_bytes(raw)
        (self.banks / "mod.ff").write_bytes(b"Synthetic opaque FF; format proof belongs to native verify/dump")
        bank = json.loads((self.source / reader.BANK_PATH).read_bytes()); bank["zone"] = "mod"
        for key, (relative, content) in reader.AUXILIARY.items():
            bank[key] = [relative]
            auxiliary = self.dump / relative; auxiliary.parent.mkdir(parents=True, exist_ok=True)
            auxiliary.write_bytes(content)
        (self.dump / "mod").write_bytes(b"Compiled using x64 ZoneTool.")
        path = self.dump / reader.BANK_PATH; path.parent.mkdir(); path.write_text(json.dumps(bank))
        flac = self.dump / reader.FLAC_PATH
        raw = bytearray(flac.read_bytes()); raw[8:12] = b"\x10\x00" * 2; flac.write_bytes(raw)
        self.inventory.write_text(self.inventory.read_text().replace(reader.ZONE, "mod"))

    def inspect(self):
        return reader.inspect(self.source, self.banks, CONTRACT, self.dump, self.inventory, "StandardModC")

    def test_standard_package_and_original_pcm(self):
        result = self.inspect()
        self.assertEqual(result["standard_filenames"], ["mod.ff", "mod.sabl", "mod.sabs"])
        self.assertEqual(result["bank_zone"], "mod")
        self.assertEqual(result["disk_zone"], "mod")
        self.assertEqual(result["loaded"]["pcm_sha256"], "72cb02b5178ce424fd3df3dbfb28b0b9613f69a4da3af71a022b8b542a46ddd9")
        self.assertEqual(result["inventory_provenance"], "CurrentVerifyPhase")
        for name in ("ready", "playback_verified", "native_alias_index_verified", "dump_standalone_flac_validated"):
            self.assertFalse(result[name])
        self.assertTrue(result["dump_bank_zone_verified"])

    def test_each_wrong_disk_name_fails_even_with_correct_bank_zone(self):
        for suffix in ("ff", "sabl", "sabs"):
            original = self.banks / ("mod." + suffix)
            renamed = self.banks / (reader.ZONE + "." + suffix)
            original.rename(renamed)
            with self.subTest(suffix=suffix), self.assertRaises(FileNotFoundError): self.inspect()
            renamed.rename(original)

    def test_each_wrong_sab_zone_fails_even_with_correct_disk_names(self):
        for suffix in ("sabl", "sabs"):
            path = self.banks / ("mod." + suffix); original = path.read_bytes()
            raw = bytearray(original); raw[600:664] = reader.pad_text(reader.ZONE, 64); path.write_bytes(raw)
            with self.subTest(suffix=suffix), self.assertRaisesRegex(ValueError, "SAB identity"): self.inspect()
            path.write_bytes(original)

    def test_wrong_dumped_bank_zone_fails_with_correct_sab_and_disk(self):
        path = self.dump / reader.BANK_PATH
        bank = json.loads(path.read_bytes()); bank["zone"] = reader.ZONE; path.write_text(json.dumps(bank))
        with self.assertRaisesRegex(ValueError, "dump bank.zone"): self.inspect()

    def test_wrong_source_bank_zone_fails_without_modifying_tracked_source(self):
        actual_read = reader.Inputs.read
        def changed(instance, path, limit=reader.MAX_FILE):
            raw = actual_read(instance, path, limit)
            if Path(path) == Path(reader.__file__).with_name("standard-mod") / reader.BANK_PATH:
                bank = json.loads(raw); bank["zone"] = reader.ZONE
                return json.dumps(bank).encode()
            return raw
        with patch.object(reader.Inputs, "read", changed), self.assertRaisesRegex(ValueError, "standard source bank.zone"):
            self.inspect()

    def test_inventory_cannot_reuse_historical_f(self):
        self.inventory.write_text(self.inventory.read_text().replace('"mod"', '"' + reader.ZONE + '"'))
        with self.assertRaises(ValueError): self.inspect()

    def test_historical_profiles_do_not_accept_standard_package(self):
        for profile in ("NativeDumpF", "DumpOnlyC"):
            with self.subTest(profile=profile), self.assertRaises(FileNotFoundError):
                reader.inspect(self.source, self.banks, CONTRACT, self.dump, self.inventory, profile)

    def test_closed_native_candidate_zone_matrix(self):
        for phase in ("build", "verify", "dump"):
            current = spec(self.temp.name, phase)
            current["arguments"][-1] = "mod"; current["sha256"] = sound_ff_phase.DUMP_C_SHA
            sound_ff_phase.validate(current)
            for key, value in (("sha256", sound_ff_phase.TOOL_SHA), ("sha256", "0" * 64),
                               ("arguments", current["arguments"][:-1] + ["mod2"])):
                changed = copy.deepcopy(current); changed[key] = value
                with self.subTest(phase=phase, key=key, value=value), self.assertRaises(ValueError):
                    sound_ff_phase.validate(changed)

    def test_standard_reader_command_keeps_closed_profile(self):
        root = Path(self.temp.name)
        args = ["-B", str(root / "read_sab.py")]
        for name in ("source", "banks", "contract", "dump", "inventory"):
            args.extend(["--" + name, str(root / name)])
        item = dict(schema="iw7.material-v2-phase/1", phase="read", exe=str(root / "python.exe"),
                    sha256=sound_ff_phase.PYTHON_SHA, arguments=args + ["--dump-profile", "StandardModC"],
                    cwd=str(root), logs=str(root / "logs"), timeout=30)
        sound_ff_phase.validate(item)
        for suffix in (["--dump-profile", "standardmodc"], ["--other-profile", "StandardModC"],
                       ["--dump-profile", "StandardModC", "extra"]):
            item["arguments"] = args + suffix
            with self.subTest(suffix=suffix), self.assertRaises(ValueError): sound_ff_phase.validate(item)


if __name__ == "__main__":
    unittest.main()

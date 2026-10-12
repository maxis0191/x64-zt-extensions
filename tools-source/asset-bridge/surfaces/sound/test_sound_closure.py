"""Synthetic StandardMod representations; never opens an existing game payload."""
import base64
import copy
import csv
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch

import read_sab as reader
import test_standard_mod


class SoundClosureTests(unittest.TestCase):
    def setUp(self):
        self.case = test_standard_mod.StandardModTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)

    def inspect(self):
        return self.case.inspect()

    def test_raw_representation_pins_and_pure_consumer(self):
        result = self.inspect()
        with patch.object(Path, "open", side_effect=AssertionError("pure consumer must not read files")):
            evidence = reader.validate_closure_evidence(result)
        for name, relative in (("soundbank", reader.BANK_PATH), ("rawfile", "mod")):
            raw = (self.case.dump / relative).read_bytes()
            node = evidence["representations"][name]
            self.assertEqual(node["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(node["bytes"], len(raw))
            self.assertEqual(base64.b64decode(node["content_base64"]), raw)
            self.assertNotEqual(node["sha256"], result["fastfile"]["sha256"])
        self.assertLess(len(json.dumps(evidence)), reader.CLOSURE_LIMIT)
        self.assertFalse(result["ready"])
        self.assertFalse(result["playback_verified"])

    def test_raw_json_format_changes_hash_without_rewriting_bytes(self):
        first = self.inspect()["closure_evidence"]["representations"]["soundbank"]
        path = self.case.dump / reader.BANK_PATH
        raw = json.dumps(json.loads(path.read_bytes()), indent=4, sort_keys=True).encode() + b"\n"
        path.write_bytes(raw)
        second = self.inspect()["closure_evidence"]["representations"]["soundbank"]
        self.assertNotEqual(first["sha256"], second["sha256"])
        self.assertEqual(second["sha256"], hashlib.sha256(raw).hexdigest())

    def test_native_shaped_receipt_fits_unchanged_16k_consumer(self):
        # Match pinned writer formatting, using only generated original source.
        path = self.case.dump / reader.BANK_PATH
        bank_raw = json.dumps(json.loads(path.read_bytes()), indent=4).encode()
        path.write_bytes(bank_raw)
        path = self.case.dump / reader.ALIAS_PATH
        row = reader.alias_row(path.read_bytes())
        for field in reader.NUMERIC - {"StartDelay", "masterPriority", "stereoSpreadMaxAngle"}:
            row[field] = format(Decimal(row[field]), ".6f")
        stream = io.StringIO(newline="")
        writer = csv.writer(stream, lineterminator="\n"); writer.writerow(row); writer.writerow(row.values())
        alias_raw = stream.getvalue().encode(); path.write_bytes(alias_raw)
        self.assertEqual(len(bank_raw), 1692)
        self.assertEqual(len(alias_raw), 1111)
        result = self.inspect()
        receipt = (json.dumps(result, indent=2) + "\n").replace("\n", "\r\n").encode()
        self.assertLessEqual(len(receipt), 16384)
        # Same real consumer cap; no native tool is invoked by Read-BeaconJson.
        receipt_path = Path(self.case.temp.name) / "readback.json"
        receipt_path.write_bytes(receipt)
        self.assertLessEqual(len(json.dumps(result["closure_evidence"]).encode()), reader.CLOSURE_LIMIT)
        if shutil.which("pwsh"):
            script = receipt_path.with_suffix(".ps1")
            script.write_text('''param([string]$Repo,[string]$Receipt)
$ErrorActionPreference='Stop'
. "$Repo/ops/Base-Client.Core.ps1"
. "$Repo/ops/Agent-Scenario.Core.ps1"
. "$Repo/sdk/modding/BeaconFF.Core.ps1"
. "$Repo/tools-source/asset-bridge/surfaces/sound/SoundFF.Core.ps1"
. "$Repo/ops/modding/Agent-Sound.Package.ps1"
$r=Read-BeaconJson $Receipt 16384
$null=Read-IW7SoundMetadata $Receipt (Get-FileHash -LiteralPath $Receipt).Hash 16384
$artifacts=@(foreach($name in 'mod.ff','mod.sabl','mod.sabs'){
    $pin=$r.closure_evidence.artifacts.$name
    [pscustomobject]@{Relative='zone/'+$name;Bytes=$pin.bytes;SHA256=$pin.sha256}
})
Assert-SoundFFReadback $r $artifacts
Assert-SoundFFStandardReadback $r $artifacts
'real metadata consumers passed'
''')
            run = subprocess.run(["pwsh", "-NoLogo", "-NoProfile", "-File", str(script),
                                  str(Path(reader.__file__).resolve().parents[4]), str(receipt_path)],
                                 capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn("real metadata consumers passed", run.stdout)

    def test_valid_but_oversized_json_receipt_is_refused(self):
        path = self.case.dump / reader.BANK_PATH
        path.write_bytes(b" " * 4096 + path.read_bytes())
        with self.assertRaisesRegex(ValueError, "bound"):
            self.inspect()

    def test_alias_numeric_format_hashes_exact_dump_bytes(self):
        path = self.case.dump / reader.ALIAS_PATH
        raw = path.read_bytes().replace(b"0.5,0.5", b"0.500000,0.500000")
        path.write_bytes(raw)
        aliases = self.inspect()["closure_evidence"]["dependencies"]["aliases"]
        self.assertEqual(aliases["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertNotEqual(aliases["sha256"], reader.SOURCE_ALIAS_SHA)

    def test_fixed_headers_match_retained_native_measurements(self):
        # Independent historical metadata, never dump contents or copied node pins.
        checkpoint = json.loads(Path(reader.__file__).with_name("sab-ff-f-checkpoint-2026-10-12.json").read_bytes())
        def walk(value):
            if isinstance(value, dict):
                if {"relative", "bytes", "sha256"} <= set(value): yield value
                for child in value.values(): yield from walk(child)
            elif isinstance(value, list):
                for child in value: yield from walk(child)
        entries = list(walk(checkpoint))
        for path, raw in reader.AUXILIARY.values():
            pins = [entry for entry in entries if entry["relative"] == "work/dump/sdk_original_sound_v1/" + path]
            with self.subTest(path=path):
                self.assertEqual(len(pins), 1)
                self.assertEqual(pins[0]["bytes"], len(raw))
                self.assertEqual(pins[0]["sha256"], hashlib.sha256(raw).hexdigest())

    def test_rawfile_missing_wrong_newline_and_oversized_refused(self):
        path = self.case.dump / "mod"
        path.unlink()
        with self.assertRaises(FileNotFoundError): self.inspect()
        for raw in (b"", b"x" * 28, b"Compiled using x64 ZoneTool.\n", b"x" * 1024):
            path.write_bytes(raw)
            with self.subTest(raw=raw[:32]), self.assertRaises(ValueError): self.inspect()

    def test_bank_unknown_fields_dependencies_and_duplicates_refused(self):
        path = self.case.dump / reader.BANK_PATH
        original = json.loads(path.read_bytes())
        for field, value in (("extra", []), ("ADSRSettings", []), ("ADSRSettings", ["../outside.csv"]),
                             ("Unks", ["sound/other.json"]), ("aliases", [reader.ALIAS_PATH, "extra.csv"])):
            changed = copy.deepcopy(original); changed[field] = value
            path.write_text(json.dumps(changed))
            with self.subTest(field=field, value=value), self.assertRaises(ValueError): self.inspect()
        path.write_bytes(json.dumps(original).encode()[:-1] + b',"zone":"mod"}')
        with self.assertRaisesRegex(ValueError, "duplicate"): self.inspect()

    def test_all_auxiliary_data_rows_or_malformed_exports_refused(self):
        for key, (relative, raw) in reader.AUXILIARY.items():
            path = self.case.dump / relative
            for changed in (raw + b"\n", b"[]" if key == "Unks" else raw + b"unexpected,data\n",
                            b"null\n" if key == "Unks" else b"wrong,header\n"):
                path.write_bytes(changed)
                with self.subTest(key=key, changed=changed[:32]), self.assertRaises(ValueError): self.inspect()
            path.write_bytes(raw)

    def test_representation_and_auxiliary_final_recheck(self):
        actual = reader.Inputs.recheck
        for relative in (reader.BANK_PATH, reader.ALIAS_PATH, "mod", reader.AUXILIARY["Unks"][0]):
            path = self.case.dump / relative; raw = path.read_bytes()
            def drift(inputs):
                path.write_bytes(b"x" * len(raw))
                actual(inputs)
            with self.subTest(path=relative), patch.object(reader.Inputs, "recheck", drift), self.assertRaisesRegex(ValueError, "between reads"):
                self.inspect()
            path.write_bytes(raw)

    def test_pure_consumer_rejects_changed_pins_paths_content_and_overclaims(self):
        original = self.inspect()
        edits = [
            (lambda r: r.update(ready=True)),
            (lambda r: r.update(inventory_provenance="PreservedBuildF")),
            (lambda r: r.update(dump_profile="NativeDumpF")),
            (lambda r: r["closure_evidence"]["representations"]["soundbank"].update(sha256=r["fastfile"]["sha256"])),
            (lambda r: r["closure_evidence"]["representations"]["rawfile"].update(path="../mod")),
            (lambda r: r["closure_evidence"]["representations"]["rawfile"].update(bytes=True)),
            (lambda r: r["closure_evidence"]["representations"]["rawfile"].update(content_base64="!")),
            (lambda r: r["closure_evidence"]["representations"]["rawfile"].update(content_base64="A" * 1000)),
            (lambda r: r["closure_evidence"]["dependencies"]["auxiliary"].pop("Unks")),
            (lambda r: r["closure_evidence"]["artifacts"]["mod.sabl"].update(sha256="0" * 64)),
            (lambda r: r["closure_evidence"]["dependencies"]["sample"].update(bytes=0)),
        ]
        for index, edit in enumerate(edits):
            result = copy.deepcopy(original); edit(result)
            with self.subTest(index=index), self.assertRaises(ValueError): reader.validate_closure_evidence(result)

    def test_refreshed_hash_does_not_authorize_changed_dependency_content(self):
        original = self.inspect()
        for name, path, raw in (("aliases", reader.ALIAS_PATH, (self.case.dump / reader.ALIAS_PATH).read_bytes().replace(b"0.5,0.5", b"0.2,0.5")),
                                ("source_alias", reader.ALIAS_PATH, b"unapproved source")):
            result = copy.deepcopy(original)
            result["closure_evidence"]["dependencies"][name] = reader.representation(path, raw)
            with self.assertRaises(ValueError): reader.validate_closure_evidence(result)
        result = copy.deepcopy(original)
        path, _ = reader.AUXILIARY["Unks"]
        result["closure_evidence"]["dependencies"]["auxiliary"]["Unks"] = reader.representation(path, b"[{}]")
        with self.assertRaises(ValueError): reader.validate_closure_evidence(result)


if __name__ == "__main__":
    unittest.main()

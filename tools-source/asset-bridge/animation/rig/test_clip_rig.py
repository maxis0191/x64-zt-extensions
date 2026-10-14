"""Original synthetic XAB test bytes; no writer, native compiler or game."""
import hashlib
import copy
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest

from prepare_skin_fixture import fixture_files, manifest
from verify_clip_rig import closed_form, inspect, read_bounded, verify


def recovery_source_expectations(recovery_payload, lineage):
    """Keep the historical receipt exact; only one reviewed source revision differs."""
    recovery_sha = "8b29a5aebc7e96014bb4d9938cb8f6fa68a32b0b411a0d0d3a4bd083797717b4"
    if hashlib.sha256(recovery_payload).hexdigest() != recovery_sha or lineage.get("recovery_manifest_sha256") != recovery_sha:
        raise ValueError("historical recovery receipt changed")
    if lineage.get("schema") != "iw7.animation-rig-source-lineage/1" or set(lineage.get("changed_files", {})) != {"read_skin_native.py"}:
        raise ValueError("closed reviewed source lineage required")
    if lineage.get("recovery_commit") != "567f0dc90e35cddacddcbcd34d15d6dff4c1802c":
        raise ValueError("original recovery commit required")
    change = lineage["changed_files"]["read_skin_native.py"]
    if change.get("source_commit") != "aae3fbf3b080f82511eb7321020872fc23e591f3" or change.get("after") != {
        "bytes": 12239, "sha256": "fb801e69fb45d40fa8f33cb53ae9aa8e120891937176f14a0212839d4bab865e",
        "git_blob": "ffce1b27eb2463b0d6f6f099861ae0d9c6a64608"}:
        raise ValueError("exact reviewed CPU reader revision required")
    for flag in ("historical_recovery_modified", "native_compilation", "native_execution", "game_execution", "rendering_qualified"):
        if lineage.get(flag) is not False:
            raise ValueError("source lineage cannot invent runtime evidence")
    recovery = json.loads(recovery_payload)
    entries = {row["file"]: dict(row) for row in recovery["recovered_files"]}
    if len(recovery["recovered_files"]) != 12 or len(entries) != 12:
        raise ValueError("exact original recovery inventory required")
    before = change["before"]
    old = entries["read_skin_native.py"]
    if before.get("bytes") != old["bytes"] or before.get("sha256") != old["sha256"] or before.get("git_blob") != "d5cc5e848f05e63eeb7de85c4581b2878eab32fa":
        raise ValueError("source transition must start at the immutable recovery")
    entries["read_skin_native.py"].update(change["after"])
    return entries


def verify_recovery_source_payloads(recovery_payload, lineage, payloads):
    expected = recovery_source_expectations(recovery_payload, lineage)
    if set(payloads) != set(expected):
        raise ValueError("exact current source inventory required")
    for name, record in expected.items():
        payload = payloads[name]
        if len(payload) != record["bytes"] or hashlib.sha256(payload).hexdigest() != record["sha256"]:
            raise ValueError("current source differs from reviewed lineage: " + name)


def clip_bytes(note_id=3):
    # Hand-authored exact profile, deliberately no import of an XAB generator.
    header = bytearray(136)
    for offset in (0, 8, 16, 24, 40, 72):
        struct.pack_into("<Q", header, offset, 1)
    struct.pack_into("<I", header, 88, 16)
    struct.pack_into("<ffHH", header, 100, 30., 1., 4, 1)
    struct.pack_into("<H", header, 116, 30)
    header[118:130] = bytes((1, 1, 0, 1, 0, 0, 0, 0, 0, 2, 2, 1))
    def array(payload, count):
        return b"\x08\x01" + struct.pack("<I", count) + payload
    def name(value):
        return b"\x06\x01" + value.encode("ascii") + b"\0"
    return (array(header, 1) + name("paris_original_probe_bend") + name("tag_origin") + name("tag_probe")
            + array(bytes((0, 10, 20, 30)), 4) + array(struct.pack("<H", 3), 1)
            + array(struct.pack("<16h", 0, 0, 0, 32767, 12539, 0, 0, 30272,
                                -12539, 0, 0, 30272, 0, 0, 0, 32767), 16)
            + array(struct.pack("<If", note_id, .5), 1) + name("probe_contact"))


def meta(files):
    return manifest(files, {name: "0" * 64 for name in (
        "iw7/structs.hpp", "iw7/assets/xsurface.cpp", "iw7/assets/xmodel.cpp",
        "h1/converter/iw7/assets/xsurface.cpp", "iw7/converter/h1/assets/xsurface.cpp",
        "t7/converter/iw7/assets/xmodel_mesh.cpp")})


class ClipRigTests(unittest.TestCase):
    def test_all_four_keys_for_both_weight_hypotheses(self):
        files = fixture_files()
        result = verify(files, meta(files), clip_bytes())
        self.assertEqual(result["status"], "four-key-rig-cpu-pass")
        self.assertEqual(result["channel_to_bone"], [0, 1])
        for profile in result["profiles"].values():
            self.assertEqual([s["frame"] for s in profile["samples"]], [0, 10, 20, 30])
            for sample in profile["samples"]:
                self.assertLess(sample["max_error_units"], .005)
                if sample["frame"] in (10, 20):
                    self.assertGreater(sample["opposite_hypothesis_error_units"], 2.)
                else:
                    self.assertLess(sample["max_error_units"], 1e-10)
        for key in ("native_model_read", "ff_model_verified", "runtime_animation_verified",
                    "engine_weight_direction_verified", "note_delivery_verified",
                    "loop_duration_verified", "ready"):
            self.assertIs(result[key], False)
        self.assertIs(result["clip_matches_retained_evidence_hash"], False)

    def test_analytical_negative_pose_has_independent_known_point(self):
        k = 1 / math.sqrt(2)
        self.assertAlmostEqual(closed_form(-45)[2][1], 4 * k)
        self.assertAlmostEqual(closed_form(-45)[2][2], 8 + 12 * k)
        self.assertEqual(closed_form(0)[2], [0., -4., 16.])

    def test_ff_note_remap_needs_explicit_profile_and_remains_data_only(self):
        files = fixture_files()
        with self.assertRaises(ValueError):
            verify(files, meta(files), clip_bytes(4036))
        result = verify(files, meta(files), clip_bytes(4036), ff_roundtrip=True)
        self.assertEqual(result["notetrack_data"], {"name": "probe_contact", "normalized_time": .5, "script_string_id": 4036})
        self.assertFalse(result["note_delivery_verified"])

    def test_missing_channel_and_trailing_clip_data_refused(self):
        files = fixture_files()
        for bad in (clip_bytes().replace(b"tag_probe", b"tag_other"), clip_bytes() + b"\0"):
            with self.assertRaises(ValueError):
                verify(files, meta(files), bad)

    def test_rehashed_geometry_and_wrong_parent_do_not_pass(self):
        for field, value in (("parents.u8.bin", b"\0"),
                             ("positions.f32.bin", struct.pack("<24f", *([0.] * 24)))):
            files = fixture_files()
            files[field] = value
            with self.assertRaises(ValueError):
                verify(files, meta(files), clip_bytes())

    def test_rehashed_weight_profile_exchange_refused(self):
        files = fixture_files()
        files["first.blend.u16.bin"], files["second.blend.u16.bin"] = files["second.blend.u16.bin"], files["first.blend.u16.bin"]
        with self.assertRaises(ValueError):
            verify(files, meta(files), clip_bytes())

    def test_neutral_bind_and_clip_root_not_replaced_by_model_global_motion(self):
        files = fixture_files()
        mutated = bytearray(files["base-mats.f32.bin"])
        struct.pack_into("<f", mutated, 16, 1.)
        files["base-mats.f32.bin"] = bytes(mutated)
        with self.assertRaises(ValueError):
            verify(files, meta(files), clip_bytes())

    def test_cli_inspection_requires_retained_real_clip_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            inputs = root / "inputs"
            inputs.mkdir()
            files = fixture_files()
            for name, payload in files.items():
                (inputs / name).write_bytes(payload)
            (inputs / "fixture-input.json").write_text(json.dumps(meta(files)), encoding="utf-8")
            clip = root / "synthetic.xab"
            clip.write_bytes(clip_bytes())
            with self.assertRaisesRegex(ValueError, "actual retained clip hash"):
                inspect(inputs, clip)
            (inputs / "unexpected").write_bytes(b"x")
            with self.assertRaisesRegex(ValueError, "inventory"):
                inspect(inputs, clip)

    def test_bounded_reader_rejects_empty_large_and_relative_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input"
            for payload in (b"", b"x" * 17):
                path.write_bytes(payload)
                with self.assertRaises(ValueError):
                    read_bounded(path, 16)
        with self.assertRaisesRegex(ValueError, "absolute"):
            read_bounded(Path("relative"), 16)

    def test_recovery_manifest_matches_original_source_bytes(self):
        root = Path(__file__).absolute().parent
        recovery_payload = (root / "recovered-source.json").read_bytes()
        lineage = json.loads((root / "source-lineage.json").read_bytes())
        expected = recovery_source_expectations(recovery_payload, lineage)
        verify_recovery_source_payloads(recovery_payload, lineage, {name: (root / name).read_bytes() for name in expected})

    def test_recovery_lineage_refuses_corruption_even_if_metadata_is_rehashed(self):
        root = Path(__file__).absolute().parent
        recovery_payload = (root / "recovered-source.json").read_bytes()
        lineage = json.loads((root / "source-lineage.json").read_bytes())
        expected = recovery_source_expectations(recovery_payload, lineage)
        payloads = {name: (root / name).read_bytes() for name in expected}
        for name in expected:
            changed = dict(payloads)
            changed[name] += b"\n"
            with self.assertRaisesRegex(ValueError, "current source differs"):
                verify_recovery_source_payloads(recovery_payload, lineage, changed)
        forged = copy.deepcopy(lineage)
        changed = payloads["read_skin_native.py"] + b"\n"
        forged["changed_files"]["read_skin_native.py"]["after"].update(bytes=len(changed), sha256=hashlib.sha256(changed).hexdigest())
        with self.assertRaisesRegex(ValueError, "exact reviewed CPU reader"):
            recovery_source_expectations(recovery_payload, forged)
        forged = copy.deepcopy(lineage)
        forged["changed_files"]["another_file.py"] = forged["changed_files"]["read_skin_native.py"]
        with self.assertRaisesRegex(ValueError, "closed reviewed"):
            recovery_source_expectations(recovery_payload, forged)
        forged = copy.deepcopy(lineage)
        forged["recovery_manifest_sha256"] = hashlib.sha256(recovery_payload + b"\n").hexdigest()
        with self.assertRaisesRegex(ValueError, "historical recovery"):
            recovery_source_expectations(recovery_payload + b"\n", forged)


if __name__ == "__main__":
    unittest.main()

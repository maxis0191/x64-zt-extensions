"""Closed source/reader fixtures only; no native or retained opaque asset reads."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import prepare_root_rotation as prepare
from read_root_rotation import read_root_rotation, primitives


def array(data, count):
    return b"\x08\x01" + struct.pack("<I", count) + data


def string(value):
    return b"\x06\x01" + value.encode("ascii") + b"\0"


def fixture(note_id=3):
    # Independent literal stream, not obtained from the producer.
    header = bytearray(136)
    for offset in (0, 8, 16, 24, 40, 72):
        struct.pack_into("<Q", header, offset, 0x1000 + offset)
    struct.pack_into("<I", header, 88, 16)
    struct.pack_into("<ffHH", header, 100, 30, 1, 4, 1)
    struct.pack_into("<H", header, 116, 30)
    header[118] = 1
    header[119:129] = bytes([0, 0, 1, 0, 0, 0, 0, 0, 1, 1])
    header[129] = 1
    return (array(header, 1) + string("paris_original_probe_root_rotate") + string("tag_origin") +
            array(bytes([0, 10, 20, 30]), 4) + array(struct.pack("<H", 3), 1) +
            array(struct.pack("<16h", 0, 0, 0, 32767, 12539, 0, 0, 30272,
                              -12539, 0, 0, 30272, 0, 0, 0, 32767), 16) +
            array(struct.pack("<If", note_id, .5), 1) + string("probe_contact"))


class RootRotationTests(unittest.TestCase):
    def test_exact_authoring_and_source_counts(self):
        clip = json.loads((prepare.HERE / "clip.source.json").read_text())
        encoded = prepare.compile_root(clip)
        self.assertEqual(encoded["bone_counts"], [0, 0, 1, 0, 0, 0, 0, 0, 1, 1])
        self.assertEqual(encoded["data_byte"], [0, 10, 20, 30])
        self.assertEqual(encoded["data_short"], [3])
        self.assertEqual(encoded["random_data_short"],
                         [0, 0, 0, 32767, 12539, 0, 0, 30272,
                          -12539, 0, 0, 30272, 0, 0, 0, 32767])

    def test_other_channel_motion_and_typed_authoring_refused(self):
        changes = [("channels", ["tag_origin", "tag_probe"]), ("name", "paris_original_probe_bend"),
                   ("root_motion", True), ("translation_tracks", True), ("frequency", True),
                   ("frequency", 2), ("numframes", 31), ("loop", 1)]
        for key, value in changes:
            bad = copy.deepcopy(prepare.original_root_clip())
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                prepare.compile_root(bad)
        bad = prepare.original_root_clip()
        bad["tag_origin_x_degrees"][1][1] = 90
        with self.assertRaises(ValueError):
            prepare.compile_root(bad)

    def test_duplicate_and_nonfinite_authoring_refused(self):
        for payload in (b'{"frequency":1,"frequency":1}', b'{"frequency":NaN}'):
            with self.assertRaises(ValueError):
                prepare.parse_clip(payload)

    def test_full_one_channel_reader_and_false_runtime_claims(self):
        report = read_root_rotation(fixture())
        self.assertEqual(report["channels"], ["tag_origin"])
        self.assertEqual(report["animated_channel_indices"], [0])
        for sample, expected in zip(report["samples"], (0, 45, -45, 0)):
            self.assertAlmostEqual(sample["x_degrees"], expected, delta=.01)
        self.assertEqual(report["decoder_conventions"],
                         {"pinned_QuatInt16": 32767, "Greyhound_IW_DivideBySize": 32768})
        for key in ("runtime_tree_binding_verified", "runtime_model_binding_verified",
                    "runtime_root_pose_verified", "runtime_world_motion_verified",
                    "frequency_runtime_verified", "note_delivery_verified", "pixels_verified", "ready"):
            self.assertIs(report[key], False)

    def test_two_bone_header_null_optional_stream_and_padding_refused(self):
        for offset, value in ((119, 1), (128, 2), (118, 3), (80, 1), (132, 1)):
            bad = bytearray(fixture())
            bad[6 + offset] = value
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                read_root_rotation(bad)
        for offset in (0, 8, 16, 24, 40, 72):
            bad = bytearray(fixture())
            bad[6 + offset:6 + offset + 8] = bytes(8)
            with self.subTest(pointer=offset), self.assertRaises(ValueError):
                read_root_rotation(bad)

    def test_every_truncation_extra_channel_alias_and_trailing_refused(self):
        data = fixture()
        for length in range(len(data)):
            with self.subTest(length=length), self.assertRaises(ValueError):
                read_root_rotation(data[:length])
        for bad in (data + b"\0", data.replace(string("tag_origin"), string("tag_probe")),
                    data.replace(string("tag_origin"), string("tag_origin") + string("tag_probe")),
                    data.replace(b"\x08\x01", b"\x08\x02", 1)):
            with self.assertRaises(ValueError):
                read_root_rotation(bad)

    def test_only_explicit_ff_note_remap_and_fixed_frequency(self):
        with self.assertRaises(ValueError):
            read_root_rotation(fixture(42))
        report = read_root_rotation(fixture(42), ff_roundtrip=True)
        self.assertEqual(report["notetrack"]["script_string_id"], 42)
        for data, freq, ff in ((fixture(0), 1, True), (fixture(), 2, False),
                               (fixture(), True, False), (fixture(), 1, 1)):
            with self.assertRaises(ValueError):
                read_root_rotation(data, freq, ff_roundtrip=ff)

    def test_legacy_reader_profile_remains_closed(self):
        # Loading the frozen reader primitives does not change its old decoder.
        self.assertEqual(primitives().__name__, "ProbeReader")
        legacy = prepare.legacy()
        original = json.loads((prepare.BASE / "fixtures/probe-clip.json").read_text())
        self.assertEqual(legacy.compile_original(original)["bone_counts"],
                         [1, 0, 1, 0, 0, 0, 0, 0, 2, 2])

    def test_writer_has_one_name_and_unchanged_serialization_body(self):
        old = (prepare.BASE / "writer_probe.cpp").read_bytes()
        new = prepare.writer_source(old)
        self.assertIn(b'scr_string_t names[]={static_cast<scr_string_t>(1)};', new)
        self.assertNotIn(b'"tag_probe"', new)
        for anchor in (b'#include "probe_native_abi.hpp"', b'#include "probe_dump.inc"',
                       b'xanim_parts::dump(&asset);', b'asset.flags=ANIM_LOOP;', b'asset.notifyCount=1;'):
            self.assertIn(anchor, new)
        with self.assertRaises(ValueError):
            prepare.writer_source(old + b"\n")

    def test_preparation_transaction_with_synthetic_source_provider(self):
        # Only provider source qualification is mocked. Generated writer/ABI/
        # header and create-only transaction use the actual production functions.
        legacy = prepare.legacy()
        refs = {"DBGameAssets.h": ("struct IWXAnim\n{\n" + "\n".join(
            "uint8_t " + name + ";" for name in prepare.CATEGORIES) +
            "\n};\nstruct IWXAnimDeltaParts\n{};\n").encode(),
            "GameInfiniteWarfare.cpp": b"// synthetic source mapping\n",
            "CoDXAnimTranslator.cpp": b"// synthetic source stages\n"}
        shared = b"// synthetic pinned quaternion source\n"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sources, references, out = root / "native", root / "refs", root / "prepared"
            sources.mkdir(); references.mkdir()
            p = sources / "src/zonetool/zonetool/iw7/assets/xanim.cpp"
            p.parent.mkdir(parents=True)
            p.write_text("namespace n {\n\tvoid xanim_parts::dump(XAnimParts* asset)\n\t{\n\t}\n}")
            p = sources / "src/zonetool/game/shared.cpp"
            p.parent.mkdir(parents=True)
            p.write_bytes(shared)
            for name, data in refs.items():
                (references / name).write_bytes(data)
            real_digest = prepare.digest
            def scoped_digest(payload):
                if payload == shared:
                    return "de421b87b65d230622e77c6bca1da2d2435ddf646b2ab9c506cc55c043301d41"
                return real_digest(payload)
            with patch.object(prepare, "legacy", return_value=legacy), \
                    patch.object(legacy, "check_sources", return_value={"mock_provider": "a" * 64}), \
                    patch.object(prepare, "REFERENCE_PINS", {n: real_digest(d) for n, d in refs.items()}), \
                    patch.object(prepare, "digest", side_effect=scoped_digest):
                manifest = prepare.prepare(sources, references, out)
                self.assertTrue(manifest["source_only"])
                self.assertFalse(manifest["compiled"])
                self.assertFalse(manifest["native_writer_executed"])
                self.assertIsNone(manifest["native_artifact"])
                self.assertEqual(len(list(out.iterdir())), 7)
                self.assertFalse(list(out.glob("*.xab")))
                self.assertFalse(list(out.glob("*.exe")))
                for name, digest in manifest["generated_sha256"].items():
                    self.assertEqual(real_digest((out / name).read_bytes()), digest)
                before = {f.name: f.read_bytes() for f in out.iterdir()}
                with self.assertRaises(ValueError):
                    prepare.prepare(sources, references, out)
                self.assertEqual({f.name: f.read_bytes() for f in out.iterdir()}, before)
                (references / "DBGameAssets.h").write_bytes(refs["DBGameAssets.h"] + b"changed")
                with self.assertRaises(ValueError):
                    prepare.prepare(sources, references, root / "bad")
                self.assertFalse((root / "bad").exists())


if __name__ == "__main__":
    unittest.main()

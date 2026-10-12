"""Original source preparation tests; no compiler, native output or game assets."""
import copy
import hashlib
import json
from pathlib import Path
import re
import struct
import tempfile
import unittest
from unittest.mock import patch
from prepare_skin_fixture import fixture_files, manifest
from prepare_skin_writer import EXTRA_INTERFACES, OWN_FILES, PIN, geometry_header, prepare, tool_snapshot, verify_prepared
from read_skin_fixture import SIZES, read
from skin_oracle import verify_original_candidate


def sha(value):
    return hashlib.sha256(value).hexdigest()


def refs():
    return {name: "0" * 64 for name in ("iw7/structs.hpp", "iw7/assets/xsurface.cpp", "iw7/assets/xmodel.cpp",
                                      "h1/converter/iw7/assets/xsurface.cpp", "iw7/converter/h1/assets/xsurface.cpp",
                                      "t7/converter/iw7/assets/xmodel_mesh.cpp")}


def parsed_array(header, name, code):
    # Independently parse the emitted C++ numerical constants back into bytes.
    # This is not a native writer/ABI test and cannot emit an XMB or XSB.
    match = re.search(r"\b" + name + r"\[(\d+)\]\[(\d+)\]=\{(.*?)\n\};", header, re.S)
    if match is None:
        raise ValueError("missing generated stream")
    values = re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[-+]?\d+)?f?", match[3])
    count = int(match[1]) * int(match[2])
    if len(values) != count:
        raise ValueError("generated stream count")
    values = [float(v.rstrip("f")) if code == "f" else int(v) for v in values]
    return struct.pack("<" + str(count) + code, *values)


class SkinWriterPreparationTests(unittest.TestCase):
    def test_every_generated_stream_against_original_raw_bytes(self):
        files = fixture_files()
        header = geometry_header(files, manifest(files, refs())).decode("ascii")
        for name, filename, code in (("positions", "positions.f32.bin", "f"), ("normals", "normals.f32.bin", "f"),
                                     ("uvs", "uv.f32.bin", "f"), ("triangles", "triangles.u16.bin", "H"),
                                     ("parents", "parents.u8.bin", "B"), ("angles", "tag-angles.i16.bin", "h"),
                                     ("tag_positions", "tag-positions.f32.bin", "f"), ("bases", "base-mats.f32.bin", "f"),
                                     ("first_blend", "first.blend.u16.bin", "H"), ("second_blend", "second.blend.u16.bin", "H")):
            self.assertEqual(parsed_array(header, name, code), files[filename])

    def test_generated_binds_and_hypotheses_checked_by_independent_oracle(self):
        files = fixture_files()
        header = geometry_header(files, manifest(files, refs())).decode("ascii")
        binds = tuple(parsed_array(header, name, code) for name, code in (("parents", "B"), ("angles", "h"), ("tag_positions", "f"), ("bases", "f")))
        for hypothesis in ("first", "second"):
            blend = parsed_array(header, hypothesis + "_blend", "H")
            report = verify_original_candidate(*binds, blend, [4, 4, 0, 0, 0, 0, 0, 0], hypothesis)
            self.assertLess(report["quantization_error_units"], .005)
            other = "first" if hypothesis == "second" else "second"
            with self.assertRaises(ValueError):
                verify_original_candidate(*binds, blend, [4, 4, 0, 0, 0, 0, 0, 0], other)

    def test_rehashed_geometry_mutation_does_not_become_writer_input(self):
        files = fixture_files()
        changed = bytearray(files["positions.f32.bin"])
        struct.pack_into("<f", changed, 0, 1.)
        files["positions.f32.bin"] = bytes(changed)
        with self.assertRaisesRegex(ValueError, "actual positions"):
            geometry_header(files, manifest(files, refs()))

    def test_old_rigid_or_replaced_profile_refused(self):
        files = fixture_files()
        meta = manifest(files, refs())
        for replacement in ("paris_doom_slayer_helmet_a", "arbitrary_model"):
            changed = copy.deepcopy(meta)
            changed["profiles"]["first"]["name"] = replacement
            with self.assertRaisesRegex(ValueError, "profile identity"):
                geometry_header(files, changed)

    def test_rehashed_bind_mutation_refused(self):
        files = fixture_files()
        changed = bytearray(files["base-mats.f32.bin"])
        struct.pack_into("<f", changed, 56, 9.)
        files["base-mats.f32.bin"] = bytes(changed)
        with self.assertRaises(ValueError):
            geometry_header(files, manifest(files, refs()))

    def roots(self, root):
        inputs, source, output = root / "inputs", root / "pinned-source", root / "prepared"
        inputs.mkdir();source.mkdir()
        files = fixture_files()
        interfaces = refs()
        for name in (*interfaces, *EXTRA_INTERFACES):
            relative = "src/zonetool/game/shared.cpp" if name == "../game/shared.cpp" else "src/zonetool/zonetool/" + name
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = ("original synthetic source interface for preparation guard test: " + name).encode()
            path.write_bytes(payload)
            if name in interfaces:
                interfaces[name] = sha(payload)
        for name, payload in files.items():
            (inputs / name).write_bytes(payload)
        (inputs / "fixture-input.json").write_text(json.dumps(manifest(files, interfaces)), encoding="utf-8")
        return inputs, source, output

    @staticmethod
    def git_reply(command, **kwargs):
        return PIN + "\n" if command[3:] == ["rev-parse", "HEAD"] else ""

    def test_actual_preparation_writes_only_new_source_and_false_native_claims(self):
        with tempfile.TemporaryDirectory() as directory, patch("prepare_skin_writer.subprocess.check_output", side_effect=self.git_reply):
            inputs, source, output = self.roots(Path(directory))
            self.assertTrue(read(inputs)["input_only"])
            result = prepare(inputs, source, output)
            self.assertEqual({p.name for p in output.iterdir()}, set(OWN_FILES) | {"skin_geometry.hpp", "skin-writer-source.json"})
            for name, value in result["prepared_hashes"].items():
                self.assertEqual(sha((output / name).read_bytes()), value)
            self.assertEqual(len(result["interface_hashes"]), 11)
            for key in ("compiled", "native_writer_executed", "native_output_read", "ff_built", "pixels_verified", "ready"):
                self.assertIs(result[key], False)
            self.assertTrue(result["interface_bytes_reverified"])
            self.assertEqual(verify_prepared(inputs, source, output), result)

    def test_prepared_writer_rehashed_mutation_still_refused(self):
        with tempfile.TemporaryDirectory() as directory, patch("prepare_skin_writer.subprocess.check_output", side_effect=self.git_reply):
            inputs, source, output = self.roots(Path(directory))
            prepare(inputs, source, output)
            path = output / "writer_skin_two_bone.cpp"
            path.write_bytes(path.read_bytes() + b"\n// mutated prepared adapter\n")
            meta = json.loads((output / "skin-writer-source.json").read_bytes())
            meta["prepared_hashes"][path.name] = sha(path.read_bytes())
            (output / "skin-writer-source.json").write_text(json.dumps(meta))
            with self.assertRaisesRegex(ValueError, "reviewed source/input"):
                verify_prepared(inputs, source, output)

    def test_prepared_header_rehashed_mutation_still_refused(self):
        with tempfile.TemporaryDirectory() as directory, patch("prepare_skin_writer.subprocess.check_output", side_effect=self.git_reply):
            inputs, source, output = self.roots(Path(directory))
            prepare(inputs, source, output)
            path = output / "skin_geometry.hpp"
            path.write_bytes(path.read_bytes().replace(b"32767", b"32766"))
            meta = json.loads((output / "skin-writer-source.json").read_bytes())
            meta["prepared_hashes"][path.name] = sha(path.read_bytes())
            (output / "skin-writer-source.json").write_text(json.dumps(meta))
            with self.assertRaisesRegex(ValueError, "reviewed source/input"):
                verify_prepared(inputs, source, output)

    def test_false_compiled_claim_and_extra_file_refused(self):
        with tempfile.TemporaryDirectory() as directory, patch("prepare_skin_writer.subprocess.check_output", side_effect=self.git_reply):
            inputs, source, output = self.roots(Path(directory))
            prepare(inputs, source, output)
            path = output / "skin-writer-source.json"
            meta = json.loads(path.read_bytes());meta["compiled"] = True
            path.write_text(json.dumps(meta))
            with self.assertRaisesRegex(ValueError, "exact typed prepared writer source receipt"):
                verify_prepared(inputs, source, output)
            (output / "unexpected.xmb").write_bytes(b"original unexpected test bytes")
            with self.assertRaisesRegex(ValueError, "inventory"):
                verify_prepared(inputs, source, output)

    def test_numeric_false_claim_is_not_a_typed_boolean(self):
        with tempfile.TemporaryDirectory() as directory, patch("prepare_skin_writer.subprocess.check_output", side_effect=self.git_reply):
            inputs, source, output = self.roots(Path(directory))
            prepare(inputs, source, output)
            path = output / "skin-writer-source.json"
            meta = json.loads(path.read_bytes());meta["compiled"] = 0
            path.write_text(json.dumps(meta))
            with self.assertRaisesRegex(ValueError, "exact typed prepared writer source receipt"):
                verify_prepared(inputs, source, output)

    def test_stale_output_refused_without_modification(self):
        with tempfile.TemporaryDirectory() as directory:
            inputs, source, output = self.roots(Path(directory))
            output.mkdir();(output / "preserve").write_bytes(b"original")
            with self.assertRaisesRegex(ValueError, "fresh writer"):
                prepare(inputs, source, output)
            self.assertEqual((output / "preserve").read_bytes(), b"original")

    def test_wrong_pin_and_dirty_checkout_refused_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            inputs, source, output = self.roots(Path(directory))
            for responses, message in ((["wrong\n"], "exact clean"), ([PIN + "\n", " M shared.cpp\n"], "preserved")):
                with patch("prepare_skin_writer.subprocess.check_output", side_effect=responses), self.assertRaisesRegex(ValueError, message):
                    prepare(inputs, source, output)
                self.assertFalse(output.exists())

    def test_physical_interface_hash_checked_against_input_receipt(self):
        with tempfile.TemporaryDirectory() as directory, patch("prepare_skin_writer.subprocess.check_output", side_effect=self.git_reply):
            inputs, source, output = self.roots(Path(directory))
            (source / "src/zonetool/zonetool/iw7/structs.hpp").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "physical interface differs"):
                prepare(inputs, source, output)
            self.assertFalse(output.exists())

    def test_extra_pinned_interface_change_after_freeze_refused(self):
        with tempfile.TemporaryDirectory() as directory, patch("prepare_skin_writer.subprocess.check_output", side_effect=self.git_reply):
            inputs, source, output = self.roots(Path(directory))
            calls = 0
            def changed_snapshot(tool, meta):
                nonlocal calls
                calls += 1
                if calls == 2:
                    (tool / "src/zonetool/game/shared.cpp").write_bytes(b"changed after freeze")
                return tool_snapshot(tool, meta)
            with patch("prepare_skin_writer.tool_snapshot", side_effect=changed_snapshot), self.assertRaisesRegex(ValueError, "tool changed during"):
                prepare(inputs, source, output)
            self.assertFalse(output.exists())

    def test_input_mutation_after_header_freeze_refused(self):
        with tempfile.TemporaryDirectory() as directory, patch("prepare_skin_writer.subprocess.check_output", side_effect=self.git_reply):
            inputs, source, output = self.roots(Path(directory))
            def changed_header(files, meta):
                result = geometry_header(files, meta)
                (inputs / "first.blend.u16.bin").write_bytes(b"mutated")
                return result
            with patch("prepare_skin_writer.geometry_header", side_effect=changed_header), self.assertRaises(ValueError):
                prepare(inputs, source, output)
            self.assertFalse(output.exists())

    def test_relative_root_refused(self):
        with self.assertRaisesRegex(ValueError, "absolute"):
            prepare(Path("relative"), Path("relative-source"), Path("relative-output"))


if __name__ == "__main__":
    unittest.main()

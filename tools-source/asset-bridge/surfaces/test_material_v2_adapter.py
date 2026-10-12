"""Pure/synthetic v2 adapter checks, including mocked native processes only."""
import copy
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock

import material_v2_checks as checks
import material_v2_phase as phase
import prepare_material_v2 as v


class MaterialV2AdapterTests(unittest.TestCase):
    def test_prepared_inventory_is_bounded_even_for_empty_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i in range(65):
                (root/str(i)).mkdir()
            with self.assertRaisesRegex(ValueError, "entry bound"):
                checks.prepared_inventory(root)

    def report(self):
        return dict(schema="iw7.content-material-roundtrip/1", model=v.MODEL,
                    material_reference=v.MATERIAL, vertices=24, triangles=12, bones=1,
                    surfaces=1, lods=1, shadow_cutoff_lod=6, collision_lod=255,
                    has_lods=True, geometry_roundtrip_verified=True, read_existing_supported=True,
                    normal_encoding="H1-1010102-candidate", iw7_normal_encoding_verified=False,
                    ff_built=False, pixels_verified=False, ready=False, lod0_dist=1000000)

    def log(self):
        return f'Loading zone "{v.ZONE}"\n' + "\n".join(
            f'Loading asset "{r["name"]}" of type {r["type"]}.' for r in v.expected_inventory())

    def image(self, fmt=28):
        header = bytearray(112)
        struct.pack_into("<I", header, 24, fmt)
        struct.pack_into("<II4H", header, 40, 4096, 4096, 32, 32, 1, 1)
        header[56] = 1
        struct.pack_into("<Q", header, 64, 1)
        pixels = v.tga()[18:]
        if fmt in (28, 29):
            pixels = b"".join(bytes((pixels[i+2], pixels[i+1], pixels[i], pixels[i+3])) for i in range(0, 4096, 4))
        return b"\x08\x01\x01\0\0\0" + header + b"\x06\x01" + v.IMAGE.encode() + b"\0\x08\x01\0\x10\0\0" + pixels

    def test_exact_report(self):
        self.assertEqual(checks.roundtrip(self.report())["model"], v.MODEL)

    def test_old_variant_and_truthy_status_refused(self):
        for field, value in (("schema", "iw7.model-roundtrip/1"), ("model", v.OLD_MODEL),
                             ("material_reference", v.OLD_MATERIAL), ("vertices", True),
                             ("geometry_roundtrip_verified", 1), ("ready", "false"),
                             ("pixels_verified", True), ("lod0_dist", "1000000"),
                             ("iw7_normal_encoding_verified", True)):
            data = self.report()
            data[field] = value
            with self.assertRaises(ValueError, msg=field):
                checks.roundtrip(data)

    def test_exact_inventory(self):
        self.assertEqual(len(checks.inventory(self.log())), 8)

    def test_extra_missing_duplicate_or_unresolved_inventory_refused(self):
        log = self.log()
        for changed in (log + '\nLoading asset "extra" of type image.',
                        "\n".join(log.splitlines()[:-1]), log + "\n" + log.splitlines()[-1],
                        log + "\n[ ERROR ] missing", log.replace(v.ZONE, "sdk_beacon"),
                        log.replace('type xmodel.', 'type xmodel?')):
            with self.assertRaises(ValueError):
                checks.inventory(changed)

    def test_rgba_and_bgra_exact_pixels(self):
        results = [checks.resident_pixels(self.image(fmt)) for fmt in (28, 29, 87, 91)]
        self.assertEqual(len({r["decoded_rgba_sha256"] for r in results}), 1)

    def test_bad_shape_format_streaming_or_missing_pointer_refused(self):
        for offset, replacement in ((6+24, b"\x47\0\0\0"), (6+48, b"\x10\0"),
                                    (6+57, b"\1"), (6+56, b"\2"), (6+64, bytes(8))):
            data = bytearray(self.image())
            data[offset:offset+len(replacement)] = replacement
            with self.assertRaises(ValueError):
                checks.resident_pixels(bytes(data))

    def test_wrong_image_name_truncated_or_extra_array_refused(self):
        raw = self.image()
        for data in (raw.replace(v.IMAGE.encode(), b"old_image"), raw[:-1], raw+b"extra"):
            with self.assertRaises(ValueError):
                checks.resident_pixels(data)

    def test_orientation_channel_alpha_changes_refused(self):
        raw = self.image()
        pixels = raw[-4096:]
        changed = (pixels[::-1], pixels[128:]+pixels[:128], pixels[:3]+b"\0"+pixels[4:])
        for data in changed:
            with self.assertRaisesRegex(ValueError, "pixel/orientation/alpha"):
                checks.resident_pixels(raw[:-4096]+data)

    def test_dumped_material_and_sidecars(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepared, dump = root/"prepared", root/"dump"
            fixtures = {
                f"materials/{v.MATERIAL}.json": json.dumps({"techniqueSet->name": v.TECHNIQUE,
                    "textureTable": [{"semantic": 15, "image": v.NORMAL}, {"semantic": 14, "image": v.IMAGE}]}).encode(),
                f"techsets/state/{v.TECHNIQUE}/{v.MATERIAL}.stateinfo": b'{"stateFlags":57}',
                f"techsets/state/{v.TECHNIQUE}/{v.MATERIAL}.statebitsmap": b'[{"rasterizerState":1}]',
                f"techsets/state/{v.TECHNIQUE}/{v.MATERIAL}.statebits": bytes(152),
                f"techsets/constantbuffer/{v.TECHNIQUE}/{v.MATERIAL}.cbi": bytes(152),
                f"techsets/constantbuffer/{v.TECHNIQUE}/{v.MATERIAL}.cbt": b'synthetic-only',
            }
            for base in (prepared/"ff-inputs", dump):
                for name, data in fixtures.items():
                    path = base/name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
            path = dump/f"images/{v.IMAGE}.iw7Image"
            path.parent.mkdir()
            path.write_bytes(self.image())
            result = checks.dumped_surface(dump, prepared)
            self.assertTrue(result["original_diffuse_verified"])
            self.assertFalse(result["recipient_resolution_verified"])
            self.assertFalse(result["native_cbt_semantics_verified"])
            self.assertFalse(result["pixels_rendered_verified"])
            material = dump/f"materials/{v.MATERIAL}.json"
            material.write_bytes(material.read_bytes().replace(v.NORMAL.encode(), b"wrong_normal"))
            with self.assertRaisesRegex(ValueError, "textureTable"):
                checks.dumped_surface(dump, prepared)

    def spec(self, root):
        exe = root/"mock-only.exe"
        exe.write_bytes(b"not executable")
        return {"schema": "iw7.material-v2-phase/1", "phase": "write", "timeout": 30,
                "exe": str(exe), "sha256": v.digest(exe.read_bytes()), "arguments": ["fresh-output"],
                "cwd": str(root), "logs": str(root/"logs")}

    def test_spec_refuses_unknown_phase_timeout_relative_and_control_args(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = self.spec(Path(tmp))
            for key, value in (("phase", "game"), ("timeout", 240), ("cwd", "relative"),
                               ("arguments", ["a\nargument"]), ("arguments", [])):
                changed = copy.deepcopy(spec)
                changed[key] = value
                with self.assertRaises(ValueError):
                    phase.validate_spec(changed)

    def test_mock_native_success_records_exact_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = self.spec(Path(tmp))
            process = mock.Mock(pid=37, returncode=0, stdout=io.BytesIO(b"{}"), stderr=io.BytesIO())
            process.poll.return_value = 0
            def drain(source, dest, exceeded):
                dest.write(source.read())
            with mock.patch.object(phase.subprocess, "Popen", return_value=process) as launch:
                self.assertEqual(phase.run(spec, drain), 0)
            self.assertEqual(launch.call_args.args[0], [spec["exe"], "fresh-output"])
            self.assertNotIn("shell", launch.call_args.kwargs)
            result = json.loads((Path(spec["logs"])/"phase.json").read_text())
            self.assertEqual(result["phase"], "write")
            self.assertEqual(result["executable_sha256"], spec["sha256"])

    def test_compile_environment_is_a_scoped_copy_without_unproved_telemetry_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = self.spec(Path(tmp))
            spec.update(phase="compile", timeout=240)
            inherited = {"PATH": "parent-path", "CL": "/parent-option",
                         "VSCMD_SKIP_SENDTELEMETRY": "parent-value"}
            process = mock.Mock(pid=37, returncode=0, stdout=io.BytesIO(), stderr=io.BytesIO())
            process.poll.return_value = 0
            with mock.patch.dict(phase.os.environ, inherited, clear=True), \
                    mock.patch.object(phase.subprocess, "Popen", return_value=process) as launch:
                self.assertEqual(phase.run(spec, lambda s,d,e: None), 0)
                env = launch.call_args.kwargs["env"]
                self.assertIsNot(env, phase.os.environ)
                self.assertEqual(env["CL"], inherited["CL"])
                self.assertEqual(env["VSCMD_SKIP_SENDTELEMETRY"], inherited["VSCMD_SKIP_SENDTELEMETRY"])
                self.assertEqual(env["PATH"], str(Path(spec["exe"]).parent) + phase.os.pathsep + inherited["PATH"])
                self.assertEqual(dict(phase.os.environ), inherited)

    def test_tampered_executable_never_starts_even_mock_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = self.spec(Path(tmp))
            Path(spec["exe"]).write_bytes(b"modified")
            with mock.patch.object(phase.subprocess, "Popen") as launch:
                with self.assertRaisesRegex(ValueError, "executable changed"):
                    phase.run(spec, None)
                launch.assert_not_called()

    def test_mock_native_failure_is_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = self.spec(Path(tmp))
            process = mock.Mock(pid=37, returncode=5, stdout=io.BytesIO(), stderr=io.BytesIO())
            process.poll.return_value = 5
            with mock.patch.object(phase.subprocess, "Popen", return_value=process):
                self.assertEqual(phase.run(spec, lambda s,d,e: None), 1)

    def test_mock_drain_failure_delegates_stop_to_original_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = self.spec(Path(tmp))
            process = mock.Mock(pid=37, returncode=0, stdout=io.BytesIO(), stderr=io.BytesIO())
            process.poll.return_value = 0
            with mock.patch.object(phase.subprocess, "Popen", return_value=process), \
                    mock.patch.object(phase.os, "_exit", side_effect=RuntimeError("outer job stops")) as stop:
                with self.assertRaisesRegex(RuntimeError, "outer job stops"):
                    phase.run(spec, lambda s,d,e: e.set())
                stop.assert_called_once_with(2)
                process.kill.assert_not_called()
            self.assertIsNotNone(json.loads((Path(spec["logs"])/"phase.json").read_text())["failure"])

    def test_mock_timeout_retains_unclosed_native_status_for_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = self.spec(Path(tmp))
            process = mock.Mock(pid=37, stdout=io.BytesIO(), stderr=io.BytesIO())
            process.poll.return_value = None
            with mock.patch.object(phase.subprocess, "Popen", return_value=process), \
                    mock.patch.object(phase.time, "monotonic", side_effect=[0, 31]), \
                    mock.patch.object(phase.os, "_exit", side_effect=RuntimeError("outer job stops")):
                with self.assertRaises(RuntimeError):
                    phase.run(spec, lambda s,d,e: None)
                process.kill.assert_not_called()
            result = json.loads((Path(spec["logs"])/"phase.json").read_text())
            self.assertEqual(result["failure"], "phase timeout")
            self.assertIsNone(result["exit_code"])


if __name__ == "__main__":
    unittest.main()

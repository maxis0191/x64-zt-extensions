"""Synthetic dependency regressions; no retail files, native build or game."""
import csv
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest

from inspect_content import BYTE_FIELDS, Inputs, Inspector, parse_json, relative
from prepare_reader_patch import transform
from prepare_beacon import tga


class SurfacesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="iw7-surfaces-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def put(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value if isinstance(value, bytes) else json.dumps(value).encode())
        return path

    def checker(self):
        header = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, 2, 2, 32, 0x28)
        return header + bytes((0, 0, 255, 255, 0, 255, 0, 255, 255, 0, 0, 255, 0, 255, 255, 255))

    def material(self, constants=False):
        data = dict.fromkeys(BYTE_FIELDS, 0)
        data.update(surfaceTypeBits=0, stateFlags=0, subMaterials=[],
                    constantTable=([dict(name="color", nameHash=7, literal=[1., 1., 1., 1.])] if constants else []),
                    textureTable=[dict(firstCharacter=99, lastCharacter=112, samplerState=0,
                                       semantic=14, typeHash=1, image="original")])
        data["techniqueSet->name"] = "recipient_tech"
        self.put("materials/probe.json", data)
        self.put("images/original.tga", self.checker())
        self.put("techsets/state/recipient_tech/probe.statebits", bytes([0]) + bytes([255]) * 151)
        self.put("techsets/state/recipient_tech/probe.statebitsmap",
                 [dict(loadBits=[0] * 6, depthStencilStateBits=[0] * 14,
                       blendStateBits=[0] * 4, rasterizerState=1)])
        if constants:
            self.put("techsets/constantbuffer/recipient_tech/probe.cbi", bytes([0]) * 152)
            self.put("techsets/constantbuffer/recipient_tech/probe.cbt", b"opaque-test-only")
        return data

    def inspect_material(self, zone="paris_enemy_synthetic"):
        check = Inspector(self.root, zone, [("techset", "recipient_tech")])
        check.material("probe")
        return check.report()

    def codes(self, report):
        return {item["code"] for item in report["findings"]}

    def test_resident_tga(self):
        self.put("images/original.tga", self.checker())
        check = Inspector(self.root, "original_zone")
        check.image("original")
        report = check.report()
        self.assertEqual(report["status"], "bounded_checks_passed")
        self.assertFalse(report["ready"])
        self.assertEqual(report["metadata"]["image:original"]["route"], "resident_FF_no_PAK")

    def test_beacon_original_axes_and_opacity(self):
        data = tga()
        self.assertEqual(len(data), 4114)
        def rgba(x, y):
            b, g, r, a = data[18 + (y * 32 + x) * 4:22 + (y * 32 + x) * 4]
            return r, g, b, a
        self.assertEqual([rgba(x, y) for x, y in ((0, 0), (31, 0), (0, 31), (31, 31))],
                         [(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255), (255, 255, 0, 255)])
        self.assertEqual(rgba(10, 0), (255, 255, 255, 255))
        self.assertEqual(rgba(0, 10), (255, 0, 255, 255))
        self.assertTrue(all(data[i] == 255 for i in range(21, len(data), 4)))

    def test_material_closure_keeps_recipient_unverified(self):
        self.material()
        report = self.inspect_material()
        self.assertEqual(report["errors"], 0)
        self.assertEqual(report["status"], "incomplete")
        self.assertIn(["material:probe", "image:original"], report["edges"])
        self.assertIn("recipient_resolution", self.codes(report))

    def test_non_enemy_zone_reproduces_early_lookup_gate(self):
        self.material()
        self.assertIn("early_db_material_lookup", self.codes(self.inspect_material("community_beacon")))

    def test_foreign_sidecar_never_borrowed(self):
        self.material()
        path = self.root / "techsets/state/recipient_tech/probe.statebits"
        path.rename(path.with_name("other_material.statebits"))
        report = self.inspect_material()
        self.assertGreater(report["errors"], 0)
        self.assertNotIn("techsets/state/recipient_tech/other_material.statebits", report["files"])

    def test_truncated_technique_indices(self):
        self.material()
        self.put("techsets/state/recipient_tech/probe.statebits", bytes(151))
        self.assertGreater(self.inspect_material()["errors"], 0)

    def test_state_index_bounds(self):
        self.material()
        self.put("techsets/state/recipient_tech/probe.statebits", bytes([1]) * 152)
        self.assertGreater(self.inspect_material()["errors"], 0)

    def test_missing_constant_buffer_is_not_success(self):
        data = self.material()
        data["constantTable"] = [dict(name="value", nameHash=1, literal=[0, 0, 0, 0])]
        self.put("materials/probe.json", data)
        self.assertGreater(self.inspect_material()["errors"], 0)

    def test_opaque_constant_buffer_never_accepted_as_decoded(self):
        self.material(constants=True)
        report = self.inspect_material()
        self.assertEqual(report["errors"], 0)
        self.assertIn("constant_buffer_native_layout", self.codes(report))

    def test_constant_name_overflow_refused(self):
        data = self.material()
        data["constantTable"] = [dict(name="thirteen_name", nameHash=1, literal=[0, 0, 0, 0])]
        self.put("materials/probe.json", data)
        self.assertGreater(self.inspect_material()["errors"], 0)

    def test_twelve_byte_name_and_missing_optional_table(self):
        data = self.material(constants=True)
        data["constantTable"][0]["name"] = "reflectionRa"
        del data["subMaterials"]
        self.put("materials/probe.json", data)
        report = self.inspect_material()
        self.assertEqual(report["errors"], 0)
        self.assertIn("constant_name_reader_copy", self.codes(report))

    def test_truncated_tga(self):
        self.put("images/original.tga", self.checker()[:-1])
        check = Inspector(self.root, "probe")
        check.image("original")
        self.assertEqual(check.report()["errors"], 1)

    def test_png_does_not_satisfy_image_dependency(self):
        self.put("images/original.png", b"synthetic-not-a-supported-source")
        check = Inspector(self.root, "probe")
        check.image("original")
        self.assertEqual(check.report()["errors"], 1)

    def test_shadowed_image_representations(self):
        self.put("images/original.tga", self.checker())
        self.put("images/original.iw7Image", b"opaque")
        check = Inspector(self.root, "probe")
        check.image("original")
        self.assertEqual(check.report()["errors"], 1)

    def test_native_streamed_images_need_reader(self):
        self.put("streamed_images/original.iw7Image", b"not-a-native-layout-claim")
        check = Inspector(self.root, "probe")
        check.image("original")
        self.assertIn("native_image_uninspected", self.codes(check.report()))

    def test_shader_bad_signature(self):
        self.put("techsets/ps/probe.cso", bytes(40))
        check = Inspector(self.root, "probe")
        check.shader("ps", "probe")
        self.assertEqual(check.report()["errors"], 1)

    def test_shader_outside_chunk(self):
        data = b"DXBC" + bytes(20) + struct.pack("<III", 36, 1, 4000)
        self.put("techsets/vs/probe.cso", data)
        check = Inspector(self.root, "probe")
        check.shader("vs", "probe")
        self.assertEqual(check.report()["errors"], 1)

    def test_shader_container_does_not_claim_stage_or_render(self):
        data = b"DXBC" + bytes(20) + struct.pack("<III", 44, 1, 36) + b"TEST" + bytes(4)
        self.put("techsets/ps/probe.cso", data)
        check = Inspector(self.root, "probe")
        check.shader("ps", "probe")
        self.assertIn("shader_linkage_required", self.codes(check.report()))
        self.assertFalse(check.report()["runtime_verified"])

    def bank(self, secondary="", sample="original", wav=False):
        fields = json.loads(Path(__file__).with_name("source_contract.json").read_text())["alias_csv_fields"]
        row = dict.fromkeys(fields, "")
        row.update(Name="beacon", SecondaryAliasName=secondary, File=sample, type="loaded")
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(fields)
        writer.writerow([row[key] for key in fields])
        self.put("sound/probe.aliases.csv", buffer.getvalue().encode())
        self.put("soundbank/probe.json", dict(name="probe", zone="probe", gameLanguage="all",
                                             soundLanguage="all", aliases=["sound/probe.aliases.csv"]))
        if sample:
            self.put("sound_assets/" + sample + (".wav" if wav else ".flac"),
                     b"RIFFtest" if wav else b"fLaC\x80\x00\x00\x22" + bytes(34))

    def test_alias_closure_missing_secondary(self):
        self.bank(secondary="unprovided")
        check = Inspector(self.root, "probe")
        check.soundbank("probe")
        self.assertEqual(check.report()["errors"], 1)

    def test_recursive_alias_does_not_recurse_validator(self):
        self.bank(secondary="beacon")
        check = Inspector(self.root, "probe")
        check.soundbank("probe")
        self.assertEqual(check.report()["errors"], 0)
        self.assertIn("sab_build_and_playback", self.codes(check.report()))

    def test_wav_rejected_even_when_present(self):
        self.bank(wav=True)
        check = Inspector(self.root, "probe")
        check.soundbank("probe")
        self.assertIn("wav_sab_unsupported", self.codes(check.report()))

    def test_flac_signature_is_not_playback_evidence(self):
        self.bank()
        check = Inspector(self.root, "probe")
        check.soundbank("probe")
        self.assertEqual(check.report()["errors"], 0)
        self.assertIn("sab_build_and_playback", self.codes(check.report()))

    def test_ui_entry_no_execution(self):
        self.put("ui_scripts/probe/__init__.lua", b'error("must never execute")')
        check = Inspector(self.root, "probe")
        check.ui("probe")
        self.assertEqual(check.report()["errors"], 0)
        self.assertIn("client_ui_delivery", self.codes(check.report()))

    def test_foreign_lua_bytecode_refused(self):
        self.put("ui_scripts/probe/__init__.lua", b"\x1bLua")
        check = Inspector(self.root, "probe")
        check.ui("probe")
        self.assertEqual(check.report()["errors"], 1)

    def test_paths_fail_closed(self):
        for value in ("../outside", "C:/outside", "a/../b", "/root", "a//b", "a:ads", "CON", "a.", "a/ "):
            with self.subTest(value=value), self.assertRaises(ValueError):
                relative(value)

    def test_input_limit_before_read(self):
        self.put("file", b"x" * 100)
        with self.assertRaises(ValueError):
            Inputs(self.root).read("file", 99)

    def test_duplicate_and_nonfinite_json(self):
        for value in (b'{"x":1,"x":2}', b'{"x":NaN}'):
            with self.assertRaises(ValueError):
                parse_json(value)

    def test_wrong_nested_json_shape_stays_structured_error(self):
        data = self.material()
        data["textureTable"] = [17]
        self.put("materials/probe.json", data)
        self.assertEqual(self.inspect_material()["errors"], 1)
        self.put("soundbank/probe.json", [])
        check = Inspector(self.root, "probe")
        check.soundbank("probe")
        self.assertEqual(check.report()["errors"], 1)

    def test_patch_unknown_or_changed_source_refused(self):
        with self.assertRaises(ValueError):
            transform("material.cpp", "foreign source")
        with self.assertRaises(ValueError):
            transform("unowned.cpp", "")


if __name__ == "__main__":
    unittest.main()

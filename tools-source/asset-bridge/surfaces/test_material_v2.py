"""Light source-gate regressions. No native code, FF or game is executed."""
import json
from pathlib import Path
import tempfile
import unittest

import prepare_material_v2 as v2


class MaterialV2Tests(unittest.TestCase):
    def fixture(self):
        writer = (b"paris_model_probe\r\n" * 8
                  + b'\\"schema\\":\\"iw7.model-roundtrip/1\\",'
                  + b"packed-normal-and-geometry-unchanged")
        header = (f'inline constexpr const char* probe_material_name = "{v2.OLD_MATERIAL}";\r\n'
                  '#pragma once\r\ngeometry-unchanged\r\n').encode()
        return writer, header

    def test_rewrite_retains_every_other_writer_byte(self):
        writer, header = self.fixture()
        result, _ = v2.rewrite_writer(writer, header)
        restored = result.replace(v2.MODEL.encode(), v2.OLD_MODEL.encode()).replace(
            b'\\"schema\\":\\"iw7.content-material-roundtrip/1\\",\\"model\\":\\"paris_model_probe\\",',
            b'\\"schema\\":\\"iw7.model-roundtrip/1\\",')
        self.assertEqual(restored, writer)

    def test_geometry_header_only_changes_binding(self):
        writer, header = self.fixture()
        _, result = v2.rewrite_writer(writer, header)
        self.assertEqual(result.replace(v2.MATERIAL.encode(), v2.OLD_MATERIAL.encode()), header)

    def test_missing_or_extra_model_anchor_refused(self):
        writer, header = self.fixture()
        for changed in (writer.replace(b"paris_model_probe", b"renamed", 1), writer + b"paris_model_probe"):
            with self.assertRaisesRegex(ValueError, "eight model-name"):
                v2.rewrite_writer(changed, header)

    def test_schema_drift_or_duplicate_refused(self):
        writer, header = self.fixture()
        for changed in (writer.replace(b"iw7.model-roundtrip/1", b"other/1"),
                        writer + b'\\"schema\\":\\"iw7.model-roundtrip/1\\",'):
            with self.assertRaisesRegex(ValueError, "one original roundtrip"):
                v2.rewrite_writer(changed, header)

    def test_header_drift_refused(self):
        writer, header = self.fixture()
        for changed in (b"prefix" + header, header.replace(v2.OLD_MATERIAL.encode(), b"other")):
            with self.assertRaisesRegex(ValueError, "material header"):
                v2.rewrite_writer(writer, changed)

    def test_variant1_cannot_appear_in_expected_inventory(self):
        rows = v2.expected_inventory()
        self.assertEqual(len(rows), 8)
        self.assertEqual(len({(r["type"], r["name"]) for r in rows}), 8)
        self.assertNotIn(v2.OLD_MODEL, json.dumps(rows))
        self.assertNotIn(v2.OLD_MATERIAL, json.dumps(rows))
        self.assertEqual([(r["type"], r["name"]) for r in rows if r.get("recipient_reference")],
                         [("techset", "," + v2.TECHNIQUE), ("image", "," + v2.NORMAL)])

    def test_modified_or_missing_pinned_source_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "writer.cpp").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "pinned input changed"):
                v2.checked_inputs(root, {"writer.cpp": v2.WRITER_INPUTS["writer.cpp"]})
            with self.assertRaisesRegex(ValueError, "missing file"):
                v2.checked_inputs(root, {"absent": "0" * 64})

    def test_unknown_builder_receipt_refused_without_opening_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            path.write_text(json.dumps({"executable": {"path": "must-not-open.exe", "sha256": v2.BUILDER_EXE}}))
            with self.assertRaisesRegex(ValueError, "reviewed full-tool receipt"):
                v2.builder_metadata(path)

    def test_existing_output_refused_before_inputs_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "fresh material-v2 output"):
                v2.prepare("absent", "absent", "absent", tmp)


if __name__ == "__main__":
    unittest.main()

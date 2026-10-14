"""Source preservation and closed-profile controls; no compiler or asset inputs."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("rigid_control_source", HERE / "prepare_rigid_control.py")
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


def vertex_rows(header):
    body = header.split("probe_vertices[probe_vertex_count]={\n", 1)[1].split("\n};", 1)[0]
    return [[float(value.strip().removesuffix("f")) for value in row.split(",")]
            for row in re.findall(r"\{([^{}]+)\}", body)]


def triangle_rows(header):
    body = header.split("probe_triangles[probe_triangle_count][3]={\n", 1)[1].split("\n};", 1)[0]
    return [[int(value.strip()) for value in row.split(",")]
            for row in re.findall(r"\{([^{}]+)\}", body)]


class RigidControlSourceTests(unittest.TestCase):
    def test_header_preserves_measured_original_streams(self):
        geometry = control.original_geometry()
        for profile in control.NAMES:
            header = control.geometry_header(geometry, profile).decode()
            rows = vertex_rows(header)
            self.assertEqual(len(rows), 8)
            for start, width, expected in ((0, 3, "a8ce120d40a527d9d7dac67b117644eb986e95eda0dbd14265b3ed9f93a239a8"),
                                           (3, 3, "4d8cbe1729a0323c13e1eab08968e0fa2287d53cb966e5456b0d5e94d38efdbc"),
                                           (6, 2, "161d3a67d42f8c9c403f81438f0b6977c7157f35fe7fcce8c13062c9e67cc599")):
                values = [v for row in rows for v in row[start:start + width]]
                payload = struct.pack("<" + str(len(values)) + "f", *values)
                self.assertEqual(hashlib.sha256(payload).hexdigest(), expected)
            self.assertTrue(all(row[8:] == [0., 1., 0.] for row in rows))
            triangles = triangle_rows(header)
            self.assertEqual(len(triangles), 6)
            indices = [x for tri in triangles for x in tri]
            self.assertEqual(hashlib.sha256(struct.pack("<18H", *indices)).hexdigest(),
                             "c9b62a848a1d944e4f5f7815b316617cb91f8ca7f70e7e3ad6cc4bccd7815c73")

    def test_geometry_mutation_and_wrong_profile_refuse(self):
        data = control.original_geometry()
        bad = copy.deepcopy(data)
        bad["vertices"][0]["xyz"][0] = 1.
        with self.assertRaisesRegex(ValueError, "Exact original"):
            control.geometry_header(bad, "first")
        with self.assertRaisesRegex(ValueError, "Exactly first"):
            control.geometry_header(data, "third")

    def test_generated_writer_uses_primary_rigid_and_preserved_bits(self):
        inputs = control.source_inputs()
        text = control.writer_source(inputs["ops/doom-source/writer_rigid.cpp"]).decode()
        self.assertIn("v.tangent.packed=pack_unit_candidate(input.tangent) & 0x3FFFFFFFu;", text)
        self.assertIn("surf.flags=0x82", text)
        self.assertIn("surf.rigidVertListCount=1", text)
        self.assertIn("model.flags=XMODEL_FLAG_HAS_RIGID_VERT_LIST", text)
        self.assertIn("model.numBones=1;model.numRootBones=1", text)
        self.assertIn("info.radiusSquared=272.0f", text)
        self.assertIn("model.unknownIndex=255;model.unknownIndex2=255", text)
        self.assertIn("Rigid blend counts must be zero", text)
        self.assertIn("Surface part bits differ", text)
        self.assertNotIn("One-variable candidate", text)
        with self.assertRaisesRegex(ValueError, "Pinned rigid"):
            control.writer_source(inputs["ops/doom-source/writer_rigid.cpp"] + b"\n")

    def test_actual_preparation_is_source_only_distinct_and_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "rigid-control"
            manifest = control.prepare(output, "A")
            plan = json.loads((output / "plan.source.json").read_text())
            self.assertEqual(plan["artifact_variant"], "RigidControl")
            self.assertEqual(plan["runtime"]["addon_case"], "A")
            self.assertEqual(plan["runtime"]["addon"]["sha256"], control.ADDONS["A"]["sha256"])
            self.assertEqual(plan["rigid_expectation"]["surface_flags"], 0x82)
            self.assertEqual(plan["rigid_expectation"]["part_bits"], [0x80000000] + [0] * 7)
            self.assertEqual(plan["rigid_expectation"]["blend_bytes"], 0)
            self.assertEqual(len(plan["expected_inventory"]), 6)
            self.assertNotIn("xanim", (output / "zone_source" / (control.ZONE + ".csv")).read_text())
            self.assertEqual(len(set(plan["models"].values())), 2)
            self.assertFalse(plan["ready"] or plan["ff_built"] or plan["native_writer_compiled"])
            self.assertTrue(all(value is None for value in plan["fastfile"].values()))
            for name, record in manifest["generated"].items():
                self.assertEqual(control.digest((output / name).read_bytes()), record["sha256"])
            self.assertFalse(list(output.rglob("*.exe")) + list(output.rglob("*.ff")) + list(output.rglob("*.xmb")))
            with self.assertRaisesRegex(ValueError, "Fresh output"):
                control.prepare(output, "A")

    def test_addon_choice_is_explicit_and_does_not_change_writer_geometry(self):
        with tempfile.TemporaryDirectory() as temporary:
            a, b = Path(temporary) / "a", Path(temporary) / "b"
            control.prepare(a, "A")
            control.prepare(b, "B")
            for name in ("writer.cpp", "first/rigid_geometry.hpp", "second/rigid_geometry.hpp"):
                self.assertEqual((a / name).read_bytes(), (b / name).read_bytes())
            plan = json.loads((b / "plan.source.json").read_text())
            self.assertEqual(plan["runtime"]["addon"], control.ADDONS["B"])
            with self.assertRaisesRegex(ValueError, "explicit A/B"):
                control.prepare(Path(temporary) / "refused", "auto")
            self.assertFalse((Path(temporary) / "refused").exists())


if __name__ == "__main__":
    unittest.main()

"""Original synthetic IW7 byte fixtures; no retail bytes or native conversion.

The irregular translated pyramid and tetrahedron below are explicit independent
geometric expectations. This small record encoder is test-only, not an exporter.
"""
import copy
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from boot_contract import PROFILE, command_review, make_request
import readback as rb

PYRAMID = ((2., -3., 1.), (6., -3., 1.), (5., 2., 1.), (2., 1., 1.), (3., -1., 7.))
PYRAMID_FACES = ((0, 2, 1), (0, 3, 2), (0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4))
TETRA = ((-4., 1., 2.), (-1., 1., 2.), (-4., 5., 2.), (-3., 2., 8.))
TETRA_FACES = ((0, 2, 1), (0, 1, 3), (1, 2, 3), (2, 0, 3))


def array(data, count=1):
    return b"\x08\x01" + struct.pack("<I", count) + data


def name(text, kind=6):
    return bytes((kind, 0)) if text is None else bytes((kind, 1)) + text.encode("ascii") + b"\0"


def alias(entry, index=0):
    return b"\x09" + struct.pack("<II", entry, index)


class Synthetic:
    def __init__(self, positions=PYRAMID, faces=PYRAMID_FACES, *, names=None, lod=3):
        names = names or ("original/slanted_pyramid", "original/slanted_mesh", "root pivot", "original/clay")
        model_name, mesh_name, root_name, material_name = names
        self.positions, self.faces = tuple(positions), tuple(faces)
        self.request = make_request("synthetic_zone", model_name, lod)
        self.manifest = dict(schema="iw7.t7-iw7-resident-export/1", requested_zone="synthetic_zone",
                             source_model=model_name, selected_source_lod=lod, output_model_name=model_name,
                             output_mesh_name=mesh_name, output_root_key=command_review(self.request)["private_output_root_key"],
                             target="iw7", profile=PROFILE, geometry_profile="t7-iw7-resident-static-v1",
                             root_bone_name=root_name, selected_counts=dict(bones=1, roots=1, surfaces=1,
                             vertices=len(positions), triangles=len(faces)), material_dependencies=[material_name])
        for key in ("zonetool_xpak_helper_reads_allowed", "engine_io_verified", "dependency_payloads_verified",
                    "asset_zone_ownership_verified", "serialized_parse_verified", "runtime_verified", "ready"):
            self.manifest[key] = False
        self.records = {"model": {}, "mesh": {}}
        self.outputs = {"model": bytearray(), "mesh": bytearray()}

        def emit(role, label, data):
            self.records[role][label] = len(self.outputs[role])
            self.outputs[role].extend(data)

        low = tuple(min(p[i] for p in positions) for i in range(3))
        high = tuple(max(p[i] for p in positions) for i in range(3))
        center = tuple((a+b)/2 for a, b in zip(low, high))
        half = tuple((b-a)/2 for a, b in zip(low, high))
        model = bytearray(736)
        # Deliberately different nonzero pointer sentinels. They are not
        # addresses to dereference or expected values for the reader.
        for i, offset in enumerate((0, 152, 184, 192, 216, 232, 616, 624)):
            struct.pack_into("<Q", model, offset, 0x12340000 + 0x100*i)
        model[8:15] = bytes((0, 1, 0, 1, 255, 6, 1))
        model[20:22] = b"\x01\x01"
        struct.pack_into("<Hf", model, 26, 1, 1.25)
        struct.pack_into("<I7f", model, 36, 0x200000, 20., *center, *half)
        struct.pack_into("<fHH", model, 224, 317., 1, 0)
        struct.pack_into("<I", model, 240, 0x80000000)
        for i in range(1, 6):
            struct.pack_into("<f", model, 224 + i*64, 1000000.)
        model[704] = model[720] = 255
        emit("model", "model", array(model))
        emit("model", "model_name", name(model_name))
        emit("model", "root_bone", name(root_name))
        for label in ("parents", "angles", "positions"):
            emit("model", label, b"\x08\x00")
        emit("model", "classification", array(b"\x07"))
        emit("model", "base_mat", array(struct.pack("<8f", 0., 0., 0., 1., 0., 0., 0., 2.)))
        for label in ("reactive_parts", "reactive_tweaks", "coll_surfs"):
            emit("model", label, b"\x08\x00")
        emit("model", "bone_info", array(struct.pack("<7f", *center, *half, 400.)))
        emit("model", "mip_radius", array(struct.pack("<e", 0.375)))
        emit("model", "material_handles", array(struct.pack("<Q", 0x12349876)))
        emit("model", "material", name(material_name, 7))
        emit("model", "lod0", name(mesh_name, 7))
        for label in (*(f"lod{i}" for i in range(1, 6)), "physics_asset", "physics_fx_shape",
                      "scriptable_mover", "procedural_bones"):
            emit("model", label, name(None, 7))
        for label in ("unknown03", "unknown_vec3", "unknown04"):
            emit("model", label, b"\x08\x00")

        header = bytearray(56)
        struct.pack_into("<QQH", header, 0, 0x56780000, 0x56781000, 1)
        struct.pack_into("<I", header, 20, 0x80000000)
        emit("mesh", "mesh", array(header))
        emit("mesh", "mesh_name", name(mesh_name))
        surface = bytearray(256)
        struct.pack_into("<3H2B", surface, 0, 0x80, len(positions), len(faces), 1, 0)
        for i, offset in enumerate((32, 40, 72)):
            struct.pack_into("<Q", surface, offset, 0x98760000 + 0x100*i)
        struct.pack_into("<I", surface, 224, 0x80000000)
        emit("mesh", "surfaces", array(surface))
        packed = b"".join(struct.pack("<3fII2eII", *p, 0x01fe0100, 0xff804020,
                                     float(i % 2), float((i//2) % 2), 0x12345678, 0x87654321)
                          for i, p in enumerate(positions))
        emit("mesh", "vertices", array(packed, len(positions)))
        emit("mesh", "triangles", array(b"".join(struct.pack("<3H", *f) for f in faces), len(faces)))
        emit("mesh", "rigid_lists", array(struct.pack("<4HQ", 0, len(positions), 0, len(faces), 0)))
        for label in ("blend", "lmap", "tension", "tension_accum"):
            emit("mesh", label, b"\x0a\x00")
        self.refresh()

    def refresh(self):
        for role, folder, key, suffix in (("model", "xmodel", "output_model_name", ".xmb"),
                                         ("mesh", "xsurface", "output_mesh_name", ".xsb")):
            data = self.outputs[role]
            path = folder + "/" + self.manifest[key].replace("\\", "/") + suffix
            self.manifest[role] = dict(relative_path=path, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())

    def change(self, role, label, offset, fmt, *items):
        struct.pack_into("<" + fmt, self.outputs[role], self.records[role][label] + offset, *items)
        self.refresh()
        return self

    def inspect(self):
        return rb.inspect_pair(bytes(self.outputs["model"]), bytes(self.outputs["mesh"]), self.manifest, self.request)


class ReadbackGeometryTests(unittest.TestCase):
    def test_original_translated_pyramid_matches_independent_geometry(self):
        f = Synthetic()
        result = f.inspect()
        parsed = rb.parse_mesh(bytes(f.outputs["mesh"]), f.manifest)
        self.assertEqual(tuple(parsed["positions"]), PYRAMID)
        self.assertEqual(tuple(parsed["triangles"]), PYRAMID_FACES)
        self.assertEqual(result["model"]["bounds"]["center"], (4., -.5, 4.))
        self.assertEqual(result["model"]["bounds"]["half_extent"], (2., 2.5, 3.))
        self.assertEqual(result["mesh"]["position_min"], (2., -3., 1.))
        self.assertEqual(result["mesh"]["position_max"], (6., 2., 7.))
        self.assertTrue(result["serialized_parse_verified"])
        for key in ("ready", "native_provenance_verified", "runtime_verified", "engine_io_verified",
                    "source_geometry_correspondence_verified", "dependency_payloads_verified",
                    "asset_zone_ownership_verified", "process_acceptance_verified", "bone_space_geometry_verified",
                    "packed_shading_semantics_verified"):
            self.assertIs(result[key], False, key)

    def test_different_topology_names_and_selected_lod(self):
        f = Synthetic(TETRA, TETRA_FACES, names=(r"original\tetra", r"mesh\tetra", "unusual root 9", "material/red"), lod=5)
        result = f.inspect()
        self.assertEqual(result["mesh"]["vertices"], 4)
        self.assertEqual(result["mesh"]["triangle_count"], 4)
        self.assertEqual(result["model"]["root_bone"], "unusual root 9")
        self.assertEqual(result["model"]["material"], "material/red")
        self.assertEqual(result["selected_source_lod"], 5)

    def test_uint16_counts_above_old_fixture_limits(self):
        # Original repeated geometry exercises the maximum binary count without
        # implying a retail model or realistic topology. About 2.5 MiB of bytes.
        f = Synthetic(PYRAMID * 13107, (PYRAMID_FACES[0],) * 65535)
        self.assertGreater(len(f.outputs["mesh"]), rb.MODEL_LIMIT)
        result = f.inspect()
        self.assertEqual((result["mesh"]["vertices"], result["mesh"]["triangle_count"]), (65535, 65535))

    def test_minimum_triangle_profile_and_flat_axis(self):
        f = Synthetic(PYRAMID[:3], ((0, 1, 2),), lod=0)
        self.assertEqual(f.inspect()["model"]["bounds"]["half_extent"][2], 0.)

    def test_larger_model_bounds_are_allowed_for_selected_lod(self):
        f = Synthetic().change("model", "model", 6 + 56, "3f", 20., 20., 20.)
        self.assertTrue(f.inspect()["positions_within_model_bounds_verified"])

    def test_names_use_full_contract_bound(self):
        names = ("m"*255, "s"*255, "r"*255, "a"*255)
        self.assertEqual(Synthetic(names=names).inspect()["model"]["root_bone"], "r"*255)

    def test_arbitrary_required_pointer_values_are_not_dereferenced(self):
        f = Synthetic().change("model", "model", 6, "Q", 0xffffffffffffffff)
        f.change("mesh", "surfaces", 6 + 32, "Q", 1)
        self.assertTrue(f.inspect()["serialized_parse_verified"])

    def test_model_and_manifest_remain_unchanged(self):
        f = Synthetic()
        before = copy.deepcopy((f.manifest, f.request, f.outputs))
        f.inspect()
        self.assertEqual(before, (f.manifest, f.request, f.outputs))


class ReadbackRejectionTests(unittest.TestCase):
    def test_all_truncation_points_in_both_files_refuse(self):
        original = Synthetic()
        for role in ("model", "mesh"):
            data = original.outputs[role]
            for length in range(len(data)):
                f = copy.deepcopy(original)
                f.outputs[role] = data[:length]
                f.refresh()  # reach parsing, not merely the digest check
                with self.subTest(role=role, length=length), self.assertRaises(ValueError):
                    f.inspect()

    def test_trailing_bytes_and_wrong_record_tags(self):
        for role in ("model", "mesh"):
            f = Synthetic()
            f.outputs[role] += b"\x00"
            f.refresh()
            with self.assertRaisesRegex(ValueError, "trailing"):
                f.inspect()
            f = Synthetic().change(role, role, 0, "B", 10)
            with self.assertRaisesRegex(ValueError, "type mismatch"):
                f.inspect()

    def test_noncanonical_present_empty_and_overflow_counts(self):
        for role, label in (("model", "model"), ("mesh", "vertices"), ("mesh", "triangles")):
            for count in (0, 65536, 0xffffffff):
                f = Synthetic().change(role, label, 2, "I", count)
                with self.subTest(role=role, label=label, count=count), self.assertRaises(ValueError):
                    f.inspect()
            f = Synthetic().change(role, label, 1, "B", 2)
            with self.assertRaisesRegex(ValueError, "existence"):
                f.inspect()

    def test_nonfinite_geometry_bounds_and_bind_data(self):
        for role, label, offset, fmt in (("mesh", "vertices", 0, "f"), ("mesh", "vertices", 20, "e"),
            ("model", "model", 28, "f"), ("model", "model", 40, "f"),
            ("model", "model", 44, "f"), ("model", "model", 56, "f"),
            ("model", "model", 224, "f"), ("model", "base_mat", 12, "f"),
            ("model", "base_mat", 28, "f"), ("model", "bone_info", 0, "f"),
            ("model", "bone_info", 24, "f"), ("model", "mip_radius", 0, "e")):
            for value in (float("nan"), float("inf"), -float("inf")):
                f = Synthetic().change(role, label, 6 + offset, fmt, value)
                with self.subTest(role=role, label=label, offset=offset, value=value), self.assertRaises(ValueError):
                    f.inspect()

    def test_negative_scale_radii_and_extents(self):
        for label, offset, fmt in (("model", 28, "f"), ("model", 40, "f"), ("model", 56, "f"),
                                  ("bone_info", 12, "f"), ("bone_info", 24, "f"), ("mip_radius", 0, "e")):
            f = Synthetic().change("model", label, 6 + offset, fmt, -1.)
            with self.subTest(label=label, offset=offset), self.assertRaises(ValueError):
                f.inspect()

    def test_zero_scale_and_out_of_bounds_position(self):
        with self.assertRaises(ValueError):
            Synthetic().change("model", "model", 34, "f", 0.).inspect()
        with self.assertRaisesRegex(ValueError, "outside model bounds"):
            Synthetic().change("mesh", "vertices", 6, "f", 100.).inspect()

    def test_finite_bounds_whose_endpoints_overflow_float32(self):
        for label in ("model", "bone_info"):
            offset = 44 if label == "model" else 0
            f = Synthetic().change("model", label, 6 + offset, "f", 3e38)
            f.change("model", label, 6 + offset + 12, "f", 3e38)
            with self.assertRaisesRegex(ValueError, "float32 range"):
                f.inspect()

    def test_bounds_tolerance_is_limited_to_float32_rounding_scale(self):
        # At x=6 a single float32 step is acceptable; a 1/1024-unit drift is not.
        f = Synthetic().change("mesh", "vertices", 6 + 32, "f", 6. + 2**-21)
        self.assertTrue(f.inspect()["positions_within_model_bounds_verified"])
        f.change("mesh", "vertices", 6 + 32, "f", 6. + 2**-10)
        with self.assertRaisesRegex(ValueError, "outside model bounds"):
            f.inspect()

    def test_out_of_range_or_degenerate_triangles(self):
        for face in ((0, 1, 5), (0, 65535, 2), (0, 0, 1)):
            f = Synthetic().change("mesh", "triangles", 6, "3H", *face)
            with self.subTest(face=face), self.assertRaises(ValueError):
                f.inspect()
        f = Synthetic(((0., 0., 0.), (1., 2., 3.), (2., 4., 6.)), ((0, 1, 2),))
        with self.assertRaisesRegex(ValueError, "degenerate"):
            f.inspect()

    def test_names_counts_hashes_and_request_mismatch(self):
        for key, value in (("output_mesh_name", "other/mesh"), ("root_bone_name", "other root"),
                           ("material_dependencies", ["other/material"]), ("ready", True)):
            f = Synthetic()
            f.manifest[key] = value
            f.refresh()
            with self.subTest(key=key), self.assertRaises(ValueError):
                f.inspect()
        for key, value in (("bones", 2), ("roots", 0), ("surfaces", 2), ("vertices", 4), ("triangles", 5)):
            f = Synthetic()
            f.manifest["selected_counts"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                f.inspect()
        for role in ("model", "mesh"):
            for key, value in (("bytes", 1), ("sha256", "0"*64), ("relative_path", "../escape")):
                f = Synthetic()
                f.manifest[role][key] = value
                with self.subTest(role=role, key=key), self.assertRaises(ValueError):
                    f.inspect()
        f = Synthetic()
        f.request["lod"] = 1
        with self.assertRaises(ValueError):
            f.inspect()

    def test_unsupported_model_fields_and_required_pointers(self):
        for offset, fmt, value in ((11, "B", 2), (20, "B", 2), (21, "B", 0), (24, "H", 1),
            (26, "H", 2), (32, "H", 1), (16, "I", 8), (72, "I", 32), (88, "Q", 1),
            (112, "B", 1), (120, "I", 1), (160, "Q", 1), (200, "Q", 1), (304, "Q", 1),
            (608, "Q", 1), (648, "Q", 1), (656, "I", 1), (688, "B", 1), (728, "Q", 1),
            (152, "Q", 0), (616, "Q", 0)):
            f = Synthetic().change("model", "model", 6 + offset, fmt, value)
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                f.inspect()

    def test_unsupported_mesh_fields_flags_streams_and_rigid_ranges(self):
        for label, offset, fmt, value in (("mesh", 16, "H", 2), ("surfaces", 0, "H", 0x81),
            ("surfaces", 0, "H", 0x88), ("surfaces", 7, "B", 1), ("surfaces", 8, "H", 1),
            ("surfaces", 24, "I", 1), ("surfaces", 32, "Q", 0), ("surfaces", 80, "Q", 1),
            ("surfaces", 128, "Q", 1), ("surfaces", 200, "Q", 1), ("rigid_lists", 0, "H", 1),
            ("rigid_lists", 2, "H", 4), ("rigid_lists", 4, "H", 1), ("rigid_lists", 6, "H", 5),
            ("rigid_lists", 8, "Q", 1)):
            f = Synthetic().change("mesh", label, 6 + offset, fmt, value)
            with self.subTest(label=label, offset=offset), self.assertRaises(ValueError):
                f.inspect()
        for label in ("blend", "lmap", "tension", "tension_accum"):
            f = Synthetic().change("mesh", label, 1, "B", 1)
            with self.subTest(label=label), self.assertRaises(ValueError):
                f.inspect()

    def test_part_bits_cannot_refer_to_missing_bones_or_disagree(self):
        for role, label, offset in (("model", "model", 240), ("mesh", "mesh", 20), ("mesh", "surfaces", 224)):
            f = Synthetic().change(role, label, 6 + offset, "I", 0x40000000)
            with self.assertRaisesRegex(ValueError, "part bits"):
                f.inspect()
        with self.assertRaisesRegex(ValueError, "part bits differ"):
            Synthetic().change("model", "model", 6 + 240, "I", 0).inspect()

    def test_absent_required_arrays_names_and_material_handle(self):
        for role, label in (("model", "classification"), ("model", "model_name"),
                            ("model", "root_bone"), ("mesh", "vertices")):
            f = Synthetic().change(role, label, 1, "B", 0)
            with self.assertRaises(ValueError):
                f.inspect()
        with self.assertRaises(ValueError):
            Synthetic().change("model", "material_handles", 6, "Q", 0).inspect()


class ReadbackAliasTests(unittest.TestCase):
    def test_valid_typed_backward_array_slice_and_ledger_stability(self):
        data = array(struct.pack("<4H", 11, 22, 33, 44), 4) + b"\x08\x00" + alias(0, 1) + alias(0, 2)
        r = rb.Reader(data, rb.MESH_LIMIT)
        self.assertEqual(r.array("full", 2, 4, layout="u16"), struct.pack("<4H", 11, 22, 33, 44))
        r.array("absent", 4, 0)
        self.assertEqual(r.array("slice", 2, 2, layout="u16"), struct.pack("<2H", 22, 33))
        self.assertEqual(r.array("last", 2, 2, layout="u16"), struct.pack("<2H", 33, 44))
        self.assertEqual(len(r.entries), 1)
        r.finish()

    def test_name_alias_in_full_pair(self):
        f = Synthetic(names=("shared_name", "mesh_name", "shared_name", "material_name"))
        pos = f.records["model"]["root_bone"]
        end = pos + len(name("shared_name"))
        f.outputs["model"][pos:end] = alias(1)  # model array=0, model name=1
        f.refresh()
        self.assertEqual(f.inspect()["model"]["root_bone"], "shared_name")

    def test_names_same_kind_and_asset_layout_only(self):
        r = rb.Reader(name("foo", 7) + alias(0), 1024)
        r.name("a", 7, "foo", layout="material")
        self.assertEqual(r.name("b", 7, "foo", layout="material"), "foo")
        r.finish()
        for kind, layout in ((6, "material"), (7, "xmodel_surfs")):
            r = rb.Reader(name("foo", 7) + alias(0), 1024)
            r.name("a", 7, "foo", layout="material")
            with self.assertRaisesRegex(ValueError, "layout"):
                r.name("b", kind, "foo", layout=layout)

    def test_forward_out_of_bounds_overrun_and_wrong_stride_aliases(self):
        for entry, index, count, stride, layout in ((1, 0, 1, 2, "u16"), (0xffffffff, 0, 1, 2, "u16"),
            (0, 0xffffffff, 1, 2, "u16"), (0, 4, 1, 2, "u16"), (0, 3, 2, 2, "u16"),
            (0, 0, 0, 2, "u16"), (0, 0, 1, 4, "u16"), (0, 0, 1, 2, "other")):
            r = rb.Reader(array(bytes(8), 4) + alias(entry, index), 1024)
            r.array("a", 2, 4, layout="u16")
            with self.subTest(entry=entry, index=index, count=count, stride=stride, layout=layout), self.assertRaises(ValueError):
                r.array("b", stride, count, layout=layout)

    def test_alias_truncation_and_wrong_name_index(self):
        for length in range(1, 9):
            r = rb.Reader(name("foo") + alias(0)[:length], 1024)
            r.name("a", 6, "foo")
            with self.assertRaises(ValueError):
                r.name("b", 6, "foo")
        r = rb.Reader(name("foo") + alias(0, 1), 1024)
        r.name("a", 6, "foo")
        with self.assertRaises(ValueError):
            r.name("b", 6, "foo")

    def test_string_bounds_control_bytes_and_unterminated_names(self):
        for data in (name("x"*256), b"\x06\x01", b"\x06\x01foo", name(""), name("bad\n"), b"\x06\x01\xff\x00"):
            r = rb.Reader(data, 1024)
            with self.assertRaises(ValueError):
                r.name("a", 6, "foo")


class ReadbackFileTests(unittest.TestCase):
    def test_cli_only_reads_original_synthetic_files(self):
        f = Synthetic()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for role in ("model", "mesh"):
                path = root / f.manifest[role]["relative_path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(f.outputs[role])
            (root / "manifest.json").write_text(json.dumps(f.manifest), encoding="utf-8")
            (root / "request.json").write_text(json.dumps(f.request), encoding="utf-8")
            cmd = [sys.executable, str(Path(rb.__file__)), "--manifest", str(root / "manifest.json"),
                   "--request", str(root / "request.json"), "--root", str(root)]
            run = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads(run.stdout)
            self.assertTrue(result["serialized_parse_verified"])
            self.assertFalse(result["native_provenance_verified"])
            (root / f.manifest["mesh"]["relative_path"]).write_bytes(b"broken")
            run = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn("Readback refused", run.stderr)

    def test_file_and_json_bounds(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "synthetic.json"
            for data in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b" "*4097, b""):
                p.write_bytes(data)
                with self.assertRaises(ValueError):
                    rb.read_json(p)
            p.write_bytes(b"abcd")
            with self.assertRaises(ValueError):
                rb.read_bounded(p, 3)
            self.assertEqual(rb.read_bounded(p, 4), b"abcd")

    def test_reader_size_and_bytes_type_limits(self):
        for data, limit in ((b"", 1), (bytearray(b"a"), 1), (b"aa", 1), (b"a", rb.MESH_LIMIT+1)):
            with self.assertRaises(ValueError):
                rb.Reader(data, limit)


if __name__ == "__main__":
    unittest.main()

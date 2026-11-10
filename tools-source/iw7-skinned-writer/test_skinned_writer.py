"""Source tests of the skinned writer on synthetic data (standard library only, no game dump, no Blender).

    python -B -m unittest discover -s tools-source/iw7-skinned-writer

They prove the codecs and the record stream round trip and that the model and surface writers return the bytes
they read. They do not prove that a written model loads or draws in the game: that needs a game dump and a run
(m1_proof.py, m2_proof.py and NOTES.md).
"""
import json
import os
import struct
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import glb_read  # noqa: E402
import ship_heroes  # noqa: E402
import vertex_codec as vc  # noqa: E402
import xmodel  # noqa: E402
import xsurface  # noqa: E402
import ztdump  # noqa: E402


class VertexCodec(unittest.TestCase):
    def test_uv_round_trip_is_exact_for_half_floats(self):
        for u, v in ((0.0, 0.0), (0.5, 0.25), (1.0, -1.0), (3.75, 0.125)):
            self.assertEqual(vc.unpack_uv(vc.pack_uv(u, v)), (u, v))
        self.assertEqual(vc.pack_uv(1.0, 0.0), 0x3C00)
        self.assertEqual(vc.pack_uv(0.0, 1.0), 0x3C00 << 16)

    def test_normal_packs_three_ten_bit_fields_and_the_top_bits(self):
        self.assertEqual(vc.pack_normal((1.0, 1.0, 1.0)), 0xFFFFFFFF)
        self.assertEqual(vc.pack_normal((-1.0, -1.0, -1.0), top=0), 0)
        self.assertEqual(vc.pack_normal((1.0, -1.0, -1.0), top=0), 0x3FF)
        self.assertEqual(vc.pack_normal((5.0, -5.0, 0.0), top=0) & 0xFFFFF, 0x3FF)  # clamped
        for n in ((0.0, 0.0, 1.0), (0.6, -0.8, 0.0), (-0.267, 0.534, 0.802)):
            packed = vc.pack_normal(n)
            self.assertEqual(packed >> 30, 3)
            for got, want in zip(vc.unpack_normal(packed), n):
                self.assertAlmostEqual(got, want, delta=1.0 / 1023.0)
            self.assertEqual(vc.pack_normal(vc.unpack_normal(packed)), packed)

    def test_part_bits_sets_the_documented_bit_as_signed_words(self):
        self.assertEqual(vc.part_bits([0]), [-(1 << 31), 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(vc.part_bits([31, 32, 33]), [1, -(1 << 31) + (1 << 30), 0, 0, 0, 0, 0, 0])
        self.assertEqual(vc.part_bits([255])[7], 1)
        self.assertEqual(vc.part_bits([]), [0] * 8)

    def test_blend_stream_round_trip(self):
        influences = [
            [(3, None)],
            [(1, None), (2, 16384)],
            [(4, None), (5, 8192), (6, 4096)],
            [(7, None), (8, 100), (9, 200), (10, 300)],
        ]
        shorts, counts = vc.encode_blend(influences)
        self.assertEqual(counts, [1, 1, 1, 1, 0, 0, 0, 0])
        self.assertEqual(len(shorts), 2 + 4 + 6 + 8)
        decoded = vc.decode_blend(shorts, counts)
        self.assertEqual([vertex for vertex, _, _ in decoded], [0, 1, 2, 3])
        self.assertEqual([[bone for bone, _ in inf] for _, inf, _ in decoded], [[3], [1, 2], [4, 5, 6], [7, 8, 9, 10]])
        self.assertEqual(decoded[0][1][0][1], 1.0)
        self.assertEqual(decoded[1][1], [(1, 0.75), (2, 0.25)])
        for _, inf, trail in decoded:
            self.assertAlmostEqual(sum(weight for _, weight in inf), 1.0, places=9)
            self.assertEqual(trail, 0)


class RecordStream(unittest.TestCase):
    def test_every_record_kind_round_trips(self):
        w = ztdump.Writer()
        w.array(struct.pack("<3I", 1, 2, 3), 3)
        w.string("body_test")
        w.asset("mo/test_material")
        w.raw(b"\x01\x02\x03")
        w.array(None, 0)
        w.raw(None)
        w.string(None)
        w.rec(ztdump.Rec(ztdump.T_ASSET, offset=(2, 0)))
        blob = w.bytes()
        r = ztdump.Reader(blob)
        array = r.array(4)
        self.assertEqual((array.count, array.data), (3, struct.pack("<3I", 1, 2, 3)))
        self.assertEqual(r.string().data, "body_test")
        self.assertEqual(r.asset().data, "mo/test_material")
        self.assertEqual(r.raw().data, b"\x01\x02\x03")
        for absent in (r.array(4), r.raw(), r.string()):
            self.assertFalse(absent.exists)
        reuse = r.asset()
        self.assertEqual(reuse.offset, (2, 0))
        self.assertEqual(r.resolve(reuse).data, "mo/test_material")
        self.assertTrue(r.at_end())
        # the same records written again give the same bytes
        again = ztdump.Writer()
        r = ztdump.Reader(blob)
        for record in (r.array(4), r.string(), r.asset(), r.raw(), r.array(4), r.raw(), r.string(), r.asset()):
            again.rec(record)
        self.assertEqual(again.bytes(), blob)

    def test_wrong_kind_and_truncated_array_are_refused(self):
        w = ztdump.Writer()
        w.string("x")
        with self.assertRaisesRegex(ValueError, "dump type 6"):
            ztdump.Reader(w.bytes()).array(4)
        w = ztdump.Writer()
        w.array(b"\0" * 8, 2)
        with self.assertRaisesRegex(ValueError, "truncated array"):
            ztdump.Reader(w.bytes()[:-1]).array(4)


def synthetic_surfaces():
    surface = xsurface.Surface()
    surface.flags = xsurface.SURF_FLAG_SKINNED
    surface.verts = [
        [0.0, 0.0, 0.0, 0, 0xFFFFFFFF, vc.pack_uv(0.0, 0.0), vc.pack_normal((0.0, 0.0, 1.0)), vc.pack_normal((1.0, 0.0, 0.0))],
        [1.0, 0.0, 0.0, 0, 0xFFFFFFFF, vc.pack_uv(1.0, 0.0), vc.pack_normal((0.0, 0.0, 1.0)), vc.pack_normal((1.0, 0.0, 0.0))],
        [0.0, 2.5, 0.0, 0, 0xFFFFFFFF, vc.pack_uv(0.0, 1.0), vc.pack_normal((0.0, 0.0, 1.0)), vc.pack_normal((1.0, 0.0, 0.0), top=0)],
    ]
    surface.faces = [(0, 1, 2)]
    surface.vert_count, surface.tri_count = 3, 1
    surface.blend, surface.blend_counts = vc.encode_blend([[(0, None)], [(0, None), (1, 32768)], [(0, None), (1, 16384)]])
    surface.blend_size = len(surface.blend) * 2
    surface.ptrs["verts0"] = surface.ptrs["triIndices"] = surface.ptrs["blendVerts"] = 1
    surface.part_bits = vc.part_bits(vc.surface_bones(surface))
    surfaces = xsurface.ModelSurfs()
    surfaces.name = "body_test_lod0"
    surfaces.head_ptrs = (1, 1)
    surfaces.part_bits = list(surface.part_bits)
    surfaces.surfs = [surface]
    return surfaces


class SurfaceFile(unittest.TestCase):
    def test_written_surfaces_read_back_equal_and_write_back_byte_exact(self):
        source = synthetic_surfaces()
        blob = xsurface.write(source)
        got = xsurface.read(blob)
        self.assertEqual(got.name, "body_test_lod0")
        self.assertEqual(len(got.surfs), 1)
        surface = got.surfs[0]
        self.assertEqual(surface.verts, source.surfs[0].verts)
        self.assertEqual(surface.faces, [(0, 1, 2)])
        self.assertEqual((surface.vert_count, surface.tri_count, surface.flags), (3, 1, xsurface.SURF_FLAG_SKINNED))
        self.assertEqual(surface.blend_counts, [1, 2, 0, 0, 0, 0, 0, 0])
        self.assertEqual(vc.surface_bones(surface), {0, 1})
        self.assertEqual(surface.part_bits, vc.part_bits([0, 1]))
        self.assertEqual([[bone for bone, _ in inf] for _, inf, _ in surface.blend_groups()], [[0], [0, 1], [0, 1]])
        self.assertIsNone(surface.lmap)
        self.assertEqual(xsurface.write(got), blob)

    def test_surface_header_is_256_bytes_and_keeps_every_field(self):
        surface = synthetic_surfaces().surfs[0]
        surface.unk, surface.pad0 = 7, b"\x01\x02\x03\x04"
        head = surface.pack_head()
        self.assertEqual(len(head), 0x100)
        other = xsurface.Surface()
        other.unpack_head(head)
        self.assertEqual(other.pack_head(), head)
        self.assertEqual((other.unk, other.pad0, other.blend_size), (7, b"\x01\x02\x03\x04", surface.blend_size))

    def test_trailing_bytes_are_refused(self):
        with self.assertRaisesRegex(ValueError, "trailing bytes"):
            xsurface.read(xsurface.write(synthetic_surfaces()) + b"\0")


def synthetic_model_blob(material_reuse=False):
    """A two-bone, one-surface model written record by record in the order xmodel.read expects."""
    head = bytearray(xmodel.XMODEL_SIZE)
    for key, value in (("numBones", 2), ("numRootBones", 1), ("numsurfs", 2 if material_reuse else 1), ("numLods", 1),
                       ("scale", 1.0), ("radius", 12.5)):
        offset, fmt = xmodel.FIELDS[key]
        struct.pack_into("<" + fmt, head, offset, value)
    w = ztdump.Writer()
    w.array(head, 1)
    w.string("body_test")
    w.string("tag_origin")
    w.string("j_mainroot")
    w.array(bytes([1]), 1)                                              # parentList: bone 1 hangs on bone 0
    w.array(struct.pack("<4h", 0, 0, 0, 32767), 1)                      # tagAngles
    w.array(struct.pack("<3f", 0.0, 0.0, 36.0), 1)                      # tagPositions
    w.array(bytes([0, 2]), 2)                                           # partClassification
    w.array(struct.pack("<16f", *([0, 0, 0, 1, 0, 0, 0, 2] + [0, 0, 0, 1, 0, 0, 36, 2])), 2)   # baseMat
    w.array(None, 0)                                                    # reactiveMotionParts
    w.array(None, 0)                                                    # reactiveMotionTweaks
    w.array(None, 0)                                                    # collSurfs
    w.array(struct.pack("<14f", *([0.0] * 6 + [1.0] + [0.0] * 6 + [4.0])), 2)                 # boneInfo
    w.array(struct.pack("<H", 100), 1)                                  # invHighMipRadius
    count = 2 if material_reuse else 1
    w.array(struct.pack("<%dQ" % count, *([1] * count)), count)         # materialHandles
    w.asset("mo/test_material")
    if material_reuse:
        w.rec(ztdump.Rec(ztdump.T_ASSET, offset=(12, 0)))               # the same material, as a re-use record
    w.asset("body_test_lod0")
    for _ in range(5):
        w.asset(None)
    for _ in range(4):                                                  # physics asset, physics fx, scriptable, procedural
        w.asset(None)
    w.array(None, 0)
    w.array(None, 0)
    w.array(None, 0)
    return w.bytes()


class ModelFile(unittest.TestCase):
    def test_model_reads_named_fields_and_writes_back_byte_exact(self):
        blob = synthetic_model_blob()
        model = xmodel.read(blob)
        self.assertEqual(model.name, "body_test")
        self.assertEqual(model.bone_names, ["tag_origin", "j_mainroot"])
        self.assertEqual((model.n_bones, model.get("numRootBones"), model.get("numsurfs")), (2, 1, 1))
        self.assertEqual((model.parent_index(0), model.parent_index(1)), (-1, 0))
        self.assertEqual(model.local_quat(0), (0.0, 0.0, 0.0, 1.0))
        self.assertAlmostEqual(model.local_quat(1)[3], 1.0, places=4)
        self.assertEqual(model.tag_positions, [(0.0, 0.0, 36.0)])
        self.assertEqual(model.materials, ["mo/test_material"])
        self.assertEqual(model.lod_surfs, ["body_test_lod0", None, None, None, None, None])
        self.assertEqual(model.get("radius"), 12.5)
        self.assertEqual(xmodel.write(model), blob)

    def test_renamed_material_is_written_as_a_new_name(self):
        model = xmodel.read(synthetic_model_blob())
        model.materials = ["mo/other_material"]
        model.set("radius", 20.0)
        again = xmodel.read(xmodel.write(model))
        self.assertEqual(again.materials, ["mo/other_material"])
        self.assertEqual(again.get("radius"), 20.0)
        self.assertEqual(again.bone_names, model.bone_names)

    def test_material_reuse_record_resolves_and_survives_the_round_trip(self):
        blob = synthetic_model_blob(material_reuse=True)
        model = xmodel.read(blob)
        self.assertEqual(model.materials, ["mo/test_material", "mo/test_material"])
        self.assertEqual(xmodel.write(model), blob)

    def test_lod_row_and_quaternion_helpers(self):
        model = xmodel.read(synthetic_model_blob())
        row = [300.0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 3]
        model.set_lod(0, row)
        self.assertEqual(model.lod(0), row)
        self.assertEqual(model.lod(1)[0], 0.0)
        quarter = xmodel.qnorm((0.0, 0.0, 1.0, 1.0))                    # 90 degrees about z
        for got, want in zip(xmodel.qrot(quarter, (1.0, 0.0, 0.0)), (0.0, 1.0, 0.0)):
            self.assertAlmostEqual(got, want, places=6)
        for got, want in zip(xmodel.qmul(quarter, quarter), (0.0, 0.0, 1.0, 0.0)):
            self.assertAlmostEqual(got, want, places=6)


def minimal_glb(path):
    positions = struct.pack("<9f", 0, 0, 0, 1, 0, 0, 0, 1, 0)
    indices = struct.pack("<3H", 0, 1, 2) + b"\0\0"
    joints = struct.pack("<12B", 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0)
    weights = struct.pack("<12B", 255, 0, 0, 0, 128, 127, 0, 0, 255, 0, 0, 0)
    binary = positions + indices + joints + weights
    document = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": 36}, {"buffer": 0, "byteOffset": 36, "byteLength": 6},
                        {"buffer": 0, "byteOffset": 44, "byteLength": 12}, {"buffer": 0, "byteOffset": 56, "byteLength": 12}],
        "accessors": [{"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3"},
                      {"bufferView": 1, "componentType": 5123, "count": 3, "type": "SCALAR"},
                      {"bufferView": 2, "componentType": 5121, "count": 3, "type": "VEC4"},
                      {"bufferView": 3, "componentType": 5121, "count": 3, "type": "VEC4", "normalized": True}],
        "meshes": [{"name": "tri", "primitives": [{"attributes": {"POSITION": 0, "JOINTS_0": 2, "WEIGHTS_0": 3}, "indices": 1}]}],
        "nodes": [{"name": "j_mainroot"}, {"name": "j_spine4"}, {"name": "tri", "mesh": 0, "skin": 0}],
        "skins": [{"joints": [0, 1]}],
    }
    text = json.dumps(document).encode()
    text += b" " * (-len(text) % 4)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(text) + 8 + len(binary)))
        f.write(struct.pack("<II", len(text), 0x4E4F534A) + text)
        f.write(struct.pack("<II", len(binary), 0x004E4942) + binary)


class GlbReader(unittest.TestCase):
    def test_minimal_skinned_triangle(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "tri.glb")
            minimal_glb(path)
            glb = glb_read.Glb(path)
            primitives = list(glb.primitives())
            self.assertEqual([(mesh, index, name) for mesh, index, name, _ in primitives], [(0, 0, "tri")])
            primitive = primitives[0][3]
            self.assertEqual(glb.accessor(primitive["attributes"]["POSITION"]), [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)])
            self.assertEqual(glb.accessor(primitive["indices"]), [0, 1, 2])
            self.assertEqual(glb.accessor(primitive["attributes"]["JOINTS_0"])[1], (0, 1, 0, 0))
            weights = glb.accessor(primitive["attributes"]["WEIGHTS_0"])
            self.assertEqual(weights[0], (1.0, 0.0, 0.0, 0.0))
            self.assertAlmostEqual(sum(weights[1]), 1.0, places=9)
            self.assertEqual(glb.joint_names(), ["j_mainroot", "j_spine4"])

    def test_a_file_that_is_not_a_glb_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "bad.glb")
            with open(path, "wb") as f:
                f.write(b"\0" * 12)
            with self.assertRaises(AssertionError):
                glb_read.Glb(path)


class ShipConfig(unittest.TestCase):
    ENVIRONMENT = {"IWZ_DUMP": "D:/dump", "IWZ_HEROES": "D:/heroes", "IWZ_BLENDER": "D:/blender.exe", "IWZ_TEXCONV": "D:/texconv.exe"}
    EXAMPLE = os.path.join(HERE, "ship_heroes.example.json")

    def test_tracked_example_has_no_machine_path_and_resolves_from_the_environment(self):
        with open(self.EXAMPLE, encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn(":\\", text)
        self.assertNotIn("Users", text)
        config = ship_heroes.load_config(self.EXAMPLE, self.ENVIRONMENT)
        self.assertEqual(config["stock_dump"], "D:/dump/cp_zmb")
        self.assertEqual(config["techsets_dump"], "D:/dump/techsets_cp_zmb")
        self.assertEqual((config["blender"], config["texconv"]), ("D:/blender.exe", "D:/texconv.exe"))
        self.assertEqual(sorted(config["heroes"]), ["aj", "andre", "poindexter"])
        rows = config["heroes"]["aj"]["models"]["body"]["lods"]
        self.assertEqual([distance for _, distance in rows], [1000, 10000])
        self.assertEqual(rows[0][0], os.path.join("D:/heroes/writer/heroes_v2/lods", "aj_body_lod1.json"))
        for hero in config["heroes"].values():
            self.assertEqual(sorted(hero["models"]), ["body", "hair", "viewmodel"])

    def test_missing_variables_are_named(self):
        with self.assertRaises(SystemExit) as refused:
            ship_heroes.load_config(self.EXAMPLE, {"IWZ_DUMP": "D:/dump"})
        message = str(refused.exception)
        for name in ("IWZ_BLENDER", "IWZ_HEROES", "IWZ_TEXCONV"):
            self.assertIn(name, message)
        self.assertNotIn("IWZ_DUMP", message)

    def test_absolute_lod_paths_are_kept_and_relative_ones_need_a_root(self):
        with tempfile.TemporaryDirectory() as folder:
            absolute = os.path.join(folder, "lod1.json")
            path = os.path.join(folder, "config.json")
            config = {"stock_dump": "s", "heroes": {"h": {"models": {"body": {"lods": [[absolute, 500]]}}}}}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config, f)
            self.assertEqual(ship_heroes.load_config(path, {})["heroes"]["h"]["models"]["body"]["lods"], [[absolute, 500]])
            config["heroes"]["h"]["models"]["body"]["lods"] = [["lod1.json", 500]]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config, f)
            with self.assertRaisesRegex(SystemExit, "lods_root"):
                ship_heroes.load_config(path, {})


if __name__ == "__main__":
    unittest.main()

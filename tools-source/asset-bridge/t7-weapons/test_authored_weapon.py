"""Tests of the generic parts of the authored-weapon chain (authored/), on synthetic data: no Blender, no game dump.

They prove the recipe handling, the bone remapping of exported meshes, the texture packing formulas, the material
rebinding, the zone rows, the camo UV records the writer adds and the proof's hand-zone measure. They do not prove
that a built model loads or draws in the game.
"""
import json
import math
import os
import struct
import sys
import tempfile
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
WRITER = os.path.normpath(os.path.join(HERE, "..", "..", "iw7-skinned-writer"))
sys.path[:0] = [os.path.join(HERE, "authored"), WRITER]

import authored_weapon_proof as proof  # noqa: E402
import build_authored_weapon as baw  # noqa: E402
import build_model  # noqa: E402
import vertex_codec as vc  # noqa: E402
import xsurface  # noqa: E402


def vert(p, bone, uv=(0.0, 0.0), uv2=None):
    v = {"p": list(p), "n": [0, 0, 1], "t": [1, 0, 0], "s": 1.0, "uv": list(uv), "w": [[bone, 1.0]]}
    if uv2 is not None:
        v["uv2"] = list(uv2)
    return v


def tri_surface(obj, material, bone, z=0.0):
    return {"object": obj, "material": material, "tris": [[0, 1, 2]],
            "verts": [vert((0, 0, z), bone, (0, 0)), vert((1, 0, z), bone, (1, 0)), vert((0, 1, z), bone, (0, 1))]}


class Recipe(unittest.TestCase):
    def test_environment_variables_expand_and_a_missing_one_is_named(self):
        self.assertEqual(baw.expand({"a": ["${X}\\b"]}, {"X": "C:"}), {"a": ["C:\\b"]})
        with self.assertRaises(KeyError) as e:
            baw.expand("${NOPE}", {})
        self.assertIn("NOPE", str(e.exception))

    def test_atlas_cannot_be_camo_and_blend(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.json")
            with open(p, "w") as f:
                json.dump({"models": [{"name": "m", "donor": "d"}], "atlases": {"a": {"camo": True, "blend": True}}}, f)
            with self.assertRaises(ValueError):
                baw.load_recipe(p, {})

    def test_tracked_recipe_names_no_machine_path(self):
        with open(os.path.join(HERE, "authored", "exact_change.recipe.json")) as f:
            text = f.read()
        self.assertNotRegex(text, r"[A-Za-z]:\\\\")
        r = json.loads(text)
        self.assertTrue(all(v.startswith("${") for v in r["tools"].values()))

    def test_derived_params_read_donor_bones(self):
        class X:
            bone_names = ["root", "a", "b"]
            base_mat = [(0, 0, 0, 1, 0, 0, 0, 2), (0, 0, 0, 1, 1.5, 0, 2, 2), (0, 0, 0, 1, -3, 1, 0, 2)]
        r = {"from_donor": {"xs": ["xs", "d", ["a", "b"]], "p": ["pos", "d", "b"]}, "atlases": {}}
        out = baw.derive_params(r, {"d": X()})
        self.assertEqual(out["xs"], [1.5, -3])
        self.assertEqual(out["p"], [-3, 1, 0])


class MeshRemap(unittest.TestCase):
    def test_bones_are_renamed_dropped_and_positions_shifted(self):
        mesh = {"surfaces": [tri_surface("a", "main", "hammer"), tri_surface("b", "main", "mag2"),
                             tri_surface("c", "acc", "body")]}
        out, rep = baw.remap_mesh(mesh, {"hammer": "body", "mag2": None}, [10, 0, 0], {"body"})
        self.assertEqual(len(out["surfaces"]), 2)
        self.assertEqual(rep["dropped_surfaces"], ["b"])
        self.assertEqual(rep["renamed"], {"hammer": "body"})
        self.assertEqual(out["surfaces"][0]["verts"][1]["p"], [11, 0, 0])
        self.assertTrue(all(v["w"] == [["body", 1.0]] for s in out["surfaces"] for v in s["verts"]))

    def test_unknown_bone_and_non_rigid_surface_are_refused(self):
        with self.assertRaises(ValueError):
            baw.remap_mesh({"surfaces": [tri_surface("a", "m", "ghost")]}, {}, [0, 0, 0], {"body"})
        s = tri_surface("a", "m", "body")
        s["verts"][0]["w"] = [["body", 0.5], ["lever", 0.5]]
        with self.assertRaises(ValueError):
            baw.remap_mesh({"surfaces": [s]}, {}, [0, 0, 0], {"body", "lever"})

    def test_an_atlas_without_material_in_a_view_is_left_out(self):
        mesh = {"surfaces": [tri_surface("a", "main", "x"), tri_surface("b", "glass", "y")]}
        out = baw.keep_atlases(mesh, {"main": "m2o/main"})
        self.assertEqual([s["material"] for s in out["surfaces"]], ["main"])

    def test_camo_scale_is_read_from_lod0_and_rebuilt_on_decimated_lods(self):
        s = tri_surface("a", "main", "x")
        for v in s["verts"]:
            v["uv2"] = [3.0 * v["uv"][0] - 2.0, 3.0 * v["uv"][1] - 2.0]
        fits = baw.fit_uv2_scale({"surfaces": [s]})
        np.testing.assert_allclose(fits["main"], (3.0, -2.0, -2.0), atol=1e-12)
        lod = tri_surface("a", "main", "x")
        lod["verts"][1]["uv2"] = [9.0, 9.0]                     # broken by the decimator
        out = baw.apply_uv2_scale({"surfaces": [lod, tri_surface("g", "glass", "x")]}, fits)
        np.testing.assert_allclose(out["surfaces"][0]["verts"][1]["uv2"], [1.0, -2.0], atol=1e-12)
        self.assertNotIn("uv2", out["surfaces"][1]["verts"][0])

    def test_surfaces_of_one_material_merge_with_offset_indices(self):
        mesh = {"surfaces": [tri_surface("a", "main", "x"), tri_surface("b", "acc", "y"),
                             tri_surface("c", "main", "z")]}
        out = baw.merge_surfaces(mesh)
        self.assertEqual([s["material"] for s in out["surfaces"]], ["main", "acc"])
        self.assertEqual(out["surfaces"][0]["tris"], [[0, 1, 2], [3, 4, 5]])
        self.assertEqual(len(out["surfaces"][0]["verts"]), 6)


class Textures(unittest.TestCase):
    def test_gloss_is_monotonic_and_bounded(self):
        r = np.linspace(0.02, 1.0, 50)
        g = baw.gloss_from_roughness(r)
        self.assertTrue(np.all(np.diff(g) <= 1e-12))
        self.assertTrue(0.0 <= g.min() and g.max() <= 1.0)
        # power check: R decodes to 2^(20 (1 - sqrt(1 - R))) + 2 == 2 / r^4 - 2 inside the representable range
        r0 = 0.3
        power = 2 ** (20 * (1 - math.sqrt(1 - float(baw.gloss_from_roughness(r0))))) + 2
        self.assertAlmostEqual(power, 2 / r0 ** 4 - 2, delta=0.5)

    def test_packed_cs_dielectric_and_metal(self):
        alb = np.array([[[0.25, 0.5, 1.0, 1.0], [0.81, 0.64, 0.36, 1.0]]])
        cs = baw.pack_cs(alb, np.array([[0.0, 1.0]]))
        np.testing.assert_allclose(cs[0, 0], [0.5, math.sqrt(0.5), 1.0, 0.04])
        np.testing.assert_allclose(cs[0, 1, :3] ** 2, [0.71, 0.54, 0.26], atol=1e-9)
        self.assertAlmostEqual(cs[0, 1, 3], 1.0)

    def test_octahedral_normal_round_trip_and_green_flip(self):
        rng = np.random.default_rng(1)
        n = rng.normal(size=(8, 8, 3))
        n[..., 2] = np.abs(n[..., 2]) + 0.2
        n /= np.linalg.norm(n, axis=-1, keepdims=True)
        gl = np.concatenate([n * 0.5 + 0.5, np.ones((8, 8, 1))], -1)
        nog = baw.pack_nog(gl, np.zeros((8, 8)), np.ones((8, 8)))
        back = baw.unpack_nog_normal(nog)
        expect = n * np.array([1, -1, 1])           # OpenGL bake -> DirectX green
        np.testing.assert_allclose(back, expect, atol=1e-9)
        self.assertTrue(np.all(nog[..., 2] == 1.0))

    def test_atlas_images_put_the_mask_in_packed_a_and_glass_uses_packed_ng(self):
        maps = {"albedo": np.full((4, 4, 4), 0.5), "params": np.zeros((4, 4, 4)), "normal": np.zeros((4, 4, 4)),
                "ao": np.full((4, 4, 4), 0.25)}
        maps["normal"][..., 2] = 1.0
        maps["normal"][..., :2] = 0.5
        maps["params"][..., 2] = 0.7
        opaque = baw.atlas_images(maps, False)
        glass = baw.atlas_images(maps, True)
        self.assertEqual(sorted(opaque), ["packed_a", "packed_cs", "packed_nog"])
        self.assertEqual(sorted(glass), ["packed_a", "packed_cs", "packed_ng"])
        self.assertTrue(np.allclose(opaque["packed_a"][..., 0], 0.7))
        self.assertTrue(np.allclose(opaque["packed_nog"][..., 2], 0.25))
        self.assertTrue(np.allclose(glass["packed_ng"][..., 2], 1.0))


class Materials(unittest.TestCase):
    TEMPLATE = {"techniqueSet->name": "t_2uvt_vm", "textureTable": [
        {"semantic": 14, "image": "old_cs"}, {"semantic": 15, "image": "old_nog"}, {"semantic": 16, "image": "old_a"},
        {"semantic": 9, "image": "blank_o"}]}

    def test_rebind_touches_only_the_packed_semantics(self):
        m = baw.rebind_material(self.TEMPLATE, {"cs": "n_cs", "nog": "n_nog", "a": "n_a"})
        self.assertEqual([t["image"] for t in m["textureTable"]], ["n_cs", "n_nog", "n_a", "blank_o"])
        self.assertEqual(self.TEMPLATE["textureTable"][0]["image"], "old_cs")

    def test_techset_files_are_copied_under_the_new_name(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as out:
            for kind, ext in (("state", ".statebits"), ("constantbuffer", ".cbt")):
                d = os.path.join(root, "techsets", kind, "tech", "m2o")
                os.makedirs(d)
                for stem in ("tpl", "tpl_other"):
                    with open(os.path.join(d, stem + ext), "w") as f:
                        f.write("x")
            got = baw.copy_techset_files(root, "tech", "m2o/tpl", out, "m2o/new")
            self.assertEqual(sorted(got), ["techsets/constantbuffer/tech/m2o/new.cbt",
                                           "techsets/state/tech/m2o/new.statebits"])

    def test_rows_list_materials_before_models(self):
        self.assertEqual(baw.zone_rows(["m2o/a"], ["vm"]), ["material,m2o/a", "xmodel,vm"])


class CamoRecords(unittest.TestCase):
    def test_scaled_second_uv_gives_identity_basis(self):
        verts = [vert((0, 0, 0), "b", (0, 0), (0, 0)), vert((1, 0, 0), "b", (0.5, 0), (2, 0)),
                 vert((0, 1, 0), "b", (0, 0.5), (0, 2))]
        rec = build_model.camo_records(verts, [(0, 1, 2)])
        self.assertEqual(len(rec), 72)
        vals = [struct.unpack_from("<6f", rec, 24 * k) for k in range(3)]
        self.assertEqual(vals[1][:2], (2.0, 0.0))
        for v in vals:
            np.testing.assert_allclose(v[2:], (1, 0, 0, 1), atol=1e-6)

    def test_uniform_scale_gives_identity_even_on_slivers(self):
        # a near-degenerate triangle whose float32-rounded uv2 would give a noisy Jacobian
        verts = [vert((0, 0, 0), "b", (0.1, 0.1), (0.35, 0.35)), vert((1, 0, 0), "b", (0.1000001, 0.1), (0.3500004, 0.35)),
                 vert((0, 1, 0), "b", (0.1, 0.1000002), (0.35, 0.3500003)), vert((2, 2, 0), "b", (0.9, 0.8), (3.15, 2.8))]
        self.assertTrue(build_model.uniform_scale(verts))
        rec = build_model.camo_records(verts, [(0, 1, 2), (1, 3, 2)])
        for k in range(4):
            np.testing.assert_allclose(struct.unpack_from("<6f", rec, 24 * k)[2:], (1, 0, 0, 1))
        verts[3]["uv2"] = [0.9, 3.15]
        self.assertFalse(build_model.uniform_scale(verts))

    def test_rotated_second_uv_gives_a_unit_rotation(self):
        verts = [vert((0, 0, 0), "b", (0, 0), (0, 0)), vert((1, 0, 0), "b", (1, 0), (0, 1)),
                 vert((0, 1, 0), "b", (0, 1), (-1, 0))]
        vals = struct.unpack_from("<6f", build_model.camo_records(verts, [(0, 1, 2)]), 0)
        a, b, c, d = vals[2:]
        self.assertAlmostEqual(a * d - b * c, 1.0, places=6)
        self.assertAlmostEqual(math.hypot(a, b), 1.0, places=6)

    def test_camo_surface_gets_flag_and_one_record_per_vertex(self):
        src = tri_surface("a", "main", "body")
        problems = {"unknown_bones": {}, "unweighted_verts": 0, "clamped_verts": 0}
        s = build_model.build_surface(src, {"body": 0}, problems, 0, camo=True)
        self.assertTrue(s.flags & 0x400)
        self.assertEqual(s.shprobe.count, 3)
        ms = xsurface.ModelSurfs()
        ms.name, ms.head_ptrs, ms.surfs = "t", (1, 1), [s]
        blob = xsurface.write(ms)
        self.assertEqual(xsurface.write(xsurface.read(blob)), blob)
        import iw7_xsurface_uv2
        _, parsed = iw7_xsurface_uv2.parse(blob)
        self.assertEqual(len(parsed[0]["second"]), 72)
        plain = build_model.build_surface(src, {"body": 0}, problems, 0)
        self.assertFalse(plain.flags & 0x400)
        self.assertEqual(plain.blend_counts[:2], [3, 0])


class HandZones(unittest.TestCase):
    def test_long_triangles_count_inside_the_window(self):
        # one long quad from x=-10 to x=10 with no vertex inside the window [-1, 1]
        tris = np.array([[[-10, -1, 0], [10, -1, 0], [10, 1, 2]], [[-10, -1, 0], [10, 1, 2], [-10, 1, 2]]], float)
        e = proof.zone_extents(tris, {"x": [-1, 1]})
        self.assertAlmostEqual(e["ymin"], -1.0)
        self.assertAlmostEqual(e["zmax"], 2.0)
        e = proof.zone_extents(tris, {"x": [-1, 1], "z": [0.5, 1.5]})
        self.assertAlmostEqual(e["zmin"], 0.5)
        self.assertAlmostEqual(e["zmax"], 1.5)

    def test_compare_zone_tolerance(self):
        a = np.array([[[0, -1, 0], [1, 1, 0], [0, 0, 1]]], float)
        b = a + np.array([0, 0, 0.3])
        z = {"name": "z", "bone": "b", "x": [0, 1], "tolerance": 0.25}
        r = proof.compare_zone(a, b, z)
        self.assertFalse(r["ok"])
        self.assertAlmostEqual(r["worst_in"], 0.3)
        self.assertTrue(proof.compare_zone(a, b, dict(z, tolerance=0.31))["ok"])


class WeightCheck(unittest.TestCase):
    def test_multi_bone_vertices_are_reported(self):
        class X:
            bone_names = ["root", "body"]

            def get(self, k):
                return {"numBones": 2, "numClientBones": 0}[k]
        problems = {"unknown_bones": {}, "unweighted_verts": 0, "clamped_verts": 0}
        good = build_model.build_surface(tri_surface("a", "m", "body"), {"root": 0, "body": 1}, problems, 0)
        ms = xsurface.ModelSurfs()
        ms.surfs = [good]
        fails, per_bone, n = proof.check_weights(X(), [("p", ms)])
        self.assertEqual((fails, per_bone, n), ([], {"body": 3}, 3))
        src = tri_surface("b", "m", "body")
        src["verts"][0]["w"] = [["body", 0.5], ["root", 0.5]]
        bad = build_model.build_surface(src, {"root": 0, "body": 1}, problems, 0)
        ms.surfs = [bad]
        fails, _, _ = proof.check_weights(X(), [("p", ms)])
        self.assertTrue(any("multi-bone" in f for f in fails))


if __name__ == "__main__":
    unittest.main()

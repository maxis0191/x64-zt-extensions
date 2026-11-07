"""Synthetic tests for t7_material_pack.py template binding (no game data, no texconv)."""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_material_pack as pack  # noqa: E402


def slot(image, semantic):
    return {"image": image, "semantic": semantic, "samplerState": 243}


EMISSIVE_TEMPLATE = {
    "techniqueSet->name": "m2o_l_sm_replace_i0c0s0o0n0e0p0_vm",
    "constantTable": [{"name": "colorTint", "literal": [1.0, 1.0, 1.0, 1.0]},
                      {"name": "emissivePara", "literal": [1.0, 0.0, 0.0, 0.0]}],
    "textureTable": [slot("stock_e", 2), slot("stock_packed_nog", 15), slot("stock_packed_cs", 14)],
}
OPAQUE_TEMPLATE = {
    "techniqueSet->name": "m2o_l_sm_replace_i0c0s0o0n0p0_vm",
    "constantTable": [],
    "textureTable": [slot("stock_packed_nog", 15), slot("stock_packed_cs", 14)],
}


class BindingTest(unittest.TestCase):
    def test_emissive_slot_is_bound_and_scaled(self):
        images = {"cs": "m_packed_cs", "nog": "m_packed_nog", "alpha": "m_packed_a", "emissive": "m_e"}
        m = pack.rebind(EMISSIVE_TEMPLATE, "m", images, emissive_scale=2.5)
        bound = {t["semantic"]: t["image"] for t in m["textureTable"]}
        self.assertEqual(bound, {2: "m_e", 15: "m_packed_nog", 14: "m_packed_cs"})
        para = [c for c in m["constantTable"] if c["name"] == "emissivePara"][0]
        self.assertEqual(para["literal"][0], 2.5)
        # The template itself is not modified.
        self.assertEqual(EMISSIVE_TEMPLATE["constantTable"][1]["literal"][0], 1.0)

    def test_templates_with_and_without_emissive_slot(self):
        self.assertTrue(pack.has_emissive_slot(EMISSIVE_TEMPLATE))
        self.assertFalse(pack.has_emissive_slot(OPAQUE_TEMPLATE))
        # A colour map named *_e on another semantic is not an emissive slot.
        self.assertFalse(pack.is_emissive_slot(slot("decal_e", 5)))

    def test_emissive_tint(self):
        self.assertEqual(pack.emissive_tint({"emissive": {"color": [0.1, 0.2, 0.4], "path": "x"}}), [0.1, 0.2, 0.4])
        # The reticle glows in its colour tint when the emissive has no colour.
        self.assertEqual(pack.emissive_tint({"emissive": {"path": "x"}, "color_tint": {"color": [1.0, 0.0, 0.0]}}),
                         [1.0, 0.0, 0.0])
        self.assertIsNone(pack.emissive_tint({"emissive": {"path": "x"}}))


def shader_cs(cs):
    """What the stock weapon pixel shader (ps 0170a07b0cc77bc0) makes of a packed_cs texel (0..255):
    colour squared; alpha up to 0.1 is the dielectric reflectance, above it a metalness ramp."""
    rgb = (np.asarray(cs[:3], np.float64) / 255.0) ** 2
    a = cs[3] / 255.0
    m = min(max((a - 0.1) * 1.111111, 0.0), 1.0)
    return rgb * max(1.0 - m, 0.0), m * rgb + min(a, 0.1)


def shader_normal(g, a):
    """The same shader's normal: G and A are a 45-degree rotated octahedral encoding."""
    z, w = g / 255.0 * 2 - 1, a / 255.0 * 2 - 1
    x, y = (z + w) / 2, (z - w) / 2
    n = np.array([x, y, 1 - abs(x) - abs(y)])
    return n / np.linalg.norm(n)


class ShaderPackingTest(unittest.TestCase):
    def test_dielectric_keeps_albedo_and_low_reflectance(self):
        albedo = np.array([[[200.0, 60.0, 50.0, 255.0]]])
        spec = np.array([[[56.0, 56.0, 56.0, 255.0]]])   # BO3 dielectric: F0 0.04 in sRGB
        cs = pack.pack_cs(albedo, spec, None)[0, 0]
        diffuse, specular = shader_cs(cs)
        np.testing.assert_allclose(diffuse, pack.srgb_to_linear(albedo[0, 0, :3] / 255.0), atol=0.01)
        np.testing.assert_allclose(specular, [0.04] * 3, atol=0.005)
        self.assertLessEqual(cs[3], 0.1 * 255)   # no metal: the old luminance packing gave 0.22

    def test_metal_moves_colour_into_specular(self):
        albedo = np.array([[[20.0, 20.0, 20.0, 255.0]]])
        spec = np.array([[[230.0, 170.0, 110.0, 255.0]]])  # copper-like BO3 specular colour
        cs = pack.pack_cs(albedo, spec, None)[0, 0]
        diffuse, specular = shader_cs(cs)
        self.assertGreater(cs[3], 0.5 * 255)
        np.testing.assert_allclose(specular, pack.srgb_to_linear(spec[0, 0, :3] / 255.0), atol=0.06)
        np.testing.assert_allclose(diffuse, pack.srgb_to_linear(albedo[0, 0, :3] / 255.0), atol=0.06)

    def test_scalar_metalness_without_specular_map(self):
        albedo = np.array([[[128.0, 128.0, 128.0, 255.0]]])
        self.assertAlmostEqual(pack.pack_cs(albedo, None, 0.0)[0, 0, 3], 0.04 * 255, delta=0.5)
        self.assertAlmostEqual(pack.pack_cs(albedo, None, 1.0)[0, 0, 3], 255.0, delta=0.5)

    def test_emissive_is_linear_tint_stored_squared(self):
        emis = np.array([[[255.0, 255.0, 255.0, 255.0], [128.0, 128.0, 128.0, 255.0]]])
        out = pack.pack_emissive(emis, [0.026, 0.151, 0.672])
        # the shader squares the stored value: full white under the Ray Gun's blue tint
        np.testing.assert_allclose((out[0, 0, :3] / 255.0) ** 2, np.array([0.026, 0.151, 0.672]) / 0.672, atol=0.002)
        np.testing.assert_allclose((out[0, 1, :3] / 255.0) ** 2,
                                   pack.srgb_to_linear(128 / 255.0) * np.array([0.026, 0.151, 0.672]) / 0.672, atol=0.002)

    def test_normals_round_trip_through_the_shader_decode(self):
        for x, y in [(0.0, 0.0), (0.5, 0.2), (-0.3, 0.6), (0.7, -0.7)]:
            z = np.sqrt(max(0.0, 1 - x * x - y * y))
            src = np.array([[[(x + 1) / 2 * 255, (y + 1) / 2 * 255, 0.0, 255.0]]])
            g, a = pack.octahedral_ga(src)
            want = np.array([x, y, z]) / np.linalg.norm([x, y, z])
            np.testing.assert_allclose(shader_normal(g[0, 0], a[0, 0]), want, atol=0.02)


if __name__ == "__main__":
    unittest.main()

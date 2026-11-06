"""Synthetic tests for t7_material_pack.py template binding (no game data, no texconv)."""
import os
import sys
import unittest

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


if __name__ == "__main__":
    unittest.main()

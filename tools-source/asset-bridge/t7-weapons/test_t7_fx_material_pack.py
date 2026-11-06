"""Synthetic tests for t7_fx_material_pack.py (no game data, no texconv)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_fx_material_pack as pack  # noqa: E402

TEMPLATE = {
    "techniqueSet->name": "eq_effectunlit_zfeather_add_tab_lin_ndw_nocast_evc",
    "textureAtlasRowCount": 8, "textureAtlasColumnCount": 8,
    "constantTable": [{"name": "textureAtlas", "literal": [8.0, 8.0, 1.0, 1.0]}],
    "textureTable": [{"image": "stock_anim", "semantic": 2}],
}


def effect(material, atlas):
    return {"elements": [{"visual": {"kind": "material", "name": material}, "scalars": {"atlas": atlas}}]}


class FxMaterialTest(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(pack.classify("ei/gfx_ring_thin", "ei/effect_lit_emissive_blend#1"), "add")
        self.assertEqual(pack.classify("ei/gfx_smk_whisp_anim_em", "ei/effect_lit_emissive_blend#1"), "blend")
        self.assertEqual(pack.classify("ei/gfx_bubbles", "ei/effect_lit_specular_blend#1"), "blend")
        self.assertEqual(pack.classify("ei/gfx_distort_heat", "ei/effect_distortion#1"), "skip")

    def test_atlas_from_elements(self):
        effects = {"a": effect("ei/x", [3, 2, 1, 0, 0, 0, 0, 0]), "b": effect("ei/y", [0, 0, 1, 0, 0, 0, 0, 0])}
        self.assertEqual(pack.atlas_of(effects), {"ei/x": (8, 4), "ei/y": (1, 1)})
        clash = {"a": effect("ei/x", [3, 2, 1, 0]), "b": effect("ei/x", [2, 2, 1, 0])}
        with self.assertRaises(SystemExit):
            pack.atlas_of(clash)

    def test_size_cap_keeps_aspect(self):
        self.assertEqual(pack.scaled_size(2048, 1024, 512), (512, 256))
        self.assertEqual(pack.scaled_size(256, 256, 512), (256, 256))
        self.assertEqual(pack.scaled_size(1024, 2048, 0), (1024, 2048))

    def test_bind(self):
        m = pack.bind(TEMPLATE, "bo3wpn_x_c", 8, 4)
        self.assertEqual(m["textureTable"][0]["image"], "bo3wpn_x_c")
        self.assertEqual((m["textureAtlasColumnCount"], m["textureAtlasRowCount"]), (8, 4))
        self.assertEqual(m["constantTable"][0]["literal"][:2], [8.0, 4.0])
        self.assertEqual(TEMPLATE["textureAtlasRowCount"], 8)


if __name__ == "__main__":
    unittest.main()

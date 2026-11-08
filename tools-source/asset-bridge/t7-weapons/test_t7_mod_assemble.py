"""Synthetic tests for t7_mod_assemble.py (no game data)."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_mod_assemble as asm  # noqa: E402


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class AssembleTest(unittest.TestCase):
    def test_merges_assets_lines_and_bank(self):
        root = tempfile.mkdtemp()
        mod, csv = os.path.join(root, "mod"), os.path.join(root, "mod.csv")
        write(csv, "require,cp_zmb\nweapon,iw7_raygun_zm\nsoundbank,mod.all\n")
        write(os.path.join(mod, "soundbank", "mod.all.json"),
              json.dumps({"name": "mod.all", "zone": "mod", "aliases": ["sound/mod.all.aliases.csv"]}))
        port = os.path.join(root, "port")
        write(os.path.join(port, "zone", "weapons", "iw7_tg_zm.json"), "{}")
        write(os.path.join(port, "zone", "sound", "iw7_tg_zm.aliases.csv"), "Name\n")
        write(os.path.join(port, "zone", "soundbank", "iw7_tg_zm.json"), "{}")
        write(os.path.join(port, "zone.csv"), "xmodel,tg_view\nweapon,iw7_tg_zm\n")
        write(os.path.join(port, "catalog.txt"), "iw7_tg_zm:iw7_tg_zm_pap1:tgpap1:tgpap2\n")
        write(os.path.join(port, "behaviour.txt"), "iw7_tg_zm|zm_weap_thundergun|tg_fling_range=480||\n")
        gsc = os.path.join(root, "mod.gsc")
        write(gsc, 'catalog()\n{\n    // BEGIN t7_mod_assemble catalog\n    return ["iw7_raygun_zm:iw7_raygun_zm_pap1"];\n'
                   '    // END t7_mod_assemble catalog\n}\n'
                   'behaviours()\n{\n    // BEGIN t7_mod_assemble behaviours\n    return [];\n'
                   '    // END t7_mod_assemble behaviours\n}\n')
        out = asm.assemble(mod, csv, "mod.all", "mod", [port], gsc=gsc)
        self.assertTrue(os.path.exists(os.path.join(mod, "weapons", "iw7_tg_zm.json")))
        self.assertFalse(os.path.exists(os.path.join(mod, "soundbank", "iw7_tg_zm.json")))
        self.assertEqual(out["bank_aliases"], ["sound/mod.all.aliases.csv", "sound/iw7_tg_zm.aliases.csv"])
        self.assertEqual(out["added_lines"], ["xmodel,tg_view", "weapon,iw7_tg_zm"])
        # the hand-built weapon already in the module stays, the port is appended
        self.assertEqual(out["catalog"], ["iw7_raygun_zm:iw7_raygun_zm_pap1", "iw7_tg_zm:iw7_tg_zm_pap1:tgpap1:tgpap2"])
        with open(gsc, encoding="utf-8") as f:
            text = f.read()
        self.assertIn('    return [\n        "iw7_raygun_zm:iw7_raygun_zm_pap1",\n        "iw7_tg_zm:iw7_tg_zm_pap1:tgpap1:tgpap2"\n    ];\n'
                      '    // END t7_mod_assemble catalog\n}\n', text)
        self.assertEqual(out["behaviours"], ["iw7_tg_zm|zm_weap_thundergun|tg_fling_range=480||"])
        self.assertIn('    return [\n        "iw7_tg_zm|zm_weap_thundergun|tg_fling_range=480||"\n    ];\n'
                      '    // END t7_mod_assemble behaviours\n', text)
        again = asm.assemble(mod, csv, "mod.all", "mod", [port], gsc=gsc)       # idempotent
        self.assertEqual(again["added_lines"], [])
        self.assertEqual(len(again["catalog"]), 2)
        with open(gsc, encoding="utf-8") as f:
            self.assertEqual(f.read(), text)

    def test_gsc_without_block_is_refused(self):
        root = tempfile.mkdtemp()
        gsc = os.path.join(root, "x.gsc")
        write(gsc, "catalog() { return []; }\n")
        with self.assertRaises(SystemExit):
            asm.update_gsc(gsc, ["a"])

    def test_catalog_keyed_by_weapon_not_probe(self):
        # a generated entry replaces the module's entry for the same weapon whatever its probe alias
        merged = asm.merge_catalog(["wpn_old_fire=iw7_raygun_zm:iw7_raygun_zm_pap1:rgpap1:rgpap2", "iw7_x_zm"],
                                   ["wpn_rgun_fire_plr=iw7_raygun_zm:iw7_raygun_zm_pap1:raygun_zpap1:raygun_zpap2"])
        self.assertEqual(merged, ["wpn_rgun_fire_plr=iw7_raygun_zm:iw7_raygun_zm_pap1:raygun_zpap1:raygun_zpap2",
                                  "iw7_x_zm"])

    def test_catalog_refuses_shared_raw_name(self):
        # iw7_raygun_mark2_zm's raw name is "raygun": it replaced the Ray Gun's level.pap entry
        with self.assertRaises(SystemExit):
            asm.merge_catalog(["a=iw7_raygun_zm"], ["b=iw7_raygun_mark2_zm"])

    def test_refused_catalog_writes_nothing(self):
        root = tempfile.mkdtemp()
        mod, csv, port = (os.path.join(root, x) for x in ("mod", "zone.csv", "port"))
        write(os.path.join(mod, "catalog.txt"), "a=iw7_raygun_zm\n")
        write(csv, "weapon,iw7_raygun_zm\n")
        write(os.path.join(port, "zone", "weapons", "iw7_raygun_mark2_zm.json"), "{}")
        write(os.path.join(port, "zone.csv"), "weapon,iw7_raygun_mark2_zm\n")
        write(os.path.join(port, "catalog.txt"), "b=iw7_raygun_mark2_zm\n")
        with self.assertRaises(SystemExit):
            asm.assemble(mod, csv, "mod.all", "mod", [port])
        with open(csv, encoding="utf-8") as f:
            self.assertEqual(f.read(), "weapon,iw7_raygun_zm\n")
        self.assertFalse(os.path.exists(os.path.join(mod, "weapons", "iw7_raygun_mark2_zm.json")))


if __name__ == "__main__":
    unittest.main()

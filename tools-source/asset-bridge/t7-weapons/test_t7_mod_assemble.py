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

    def test_bank_files_are_the_mod_zones(self):
        # iw7-mod opens only mod.sabl/mod.sabs: a bank of zone bo3wpn would name files no client loads
        root = tempfile.mkdtemp()
        mod, csv = os.path.join(root, "bo3wpn"), os.path.join(root, "bo3wpn.csv")
        write(csv, "soundbank,bo3wpn.all\n")
        write(os.path.join(mod, "soundbank", "bo3wpn.all.json"),
              json.dumps({"name": "bo3wpn.all", "zone": "bo3wpn", "aliases": []}))
        port = os.path.join(root, "port")
        write(os.path.join(port, "zone", "weapons", "iw7_tg_zm.json"), "{}")
        write(os.path.join(port, "zone.csv"), "weapon,iw7_tg_zm\n")
        write(os.path.join(port, "catalog.txt"), "iw7_tg_zm:iw7_tg_zm_pap1\n")
        asm.assemble(mod, csv, "bo3wpn.all", "bo3wpn", [port])
        with open(os.path.join(mod, "soundbank", "bo3wpn.all.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["zone"], "mod")

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

    def test_shared_alias_defined_once_in_the_bank(self):
        root = tempfile.mkdtemp()
        write(os.path.join(root, "sound", "a.aliases.csv"), "Name,File\nwpn_dry,t7\\a\\dry\nwpn_a,t7\\a\\a\n")
        write(os.path.join(root, "sound", "b.aliases.csv"), "Name,File\n#comment\nwpn_dry,t7\\b\\dry\nwpn_b,t7\\b\\b\n")
        dropped = asm.dedupe_bank_aliases(root, ["sound/a.aliases.csv", "sound/b.aliases.csv", "sound/none.csv"])
        self.assertEqual(dropped, [["wpn_dry", "sound/a.aliases.csv", "sound/b.aliases.csv"]])
        with open(os.path.join(root, "sound", "b.aliases.csv"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "Name,File\n#comment\nwpn_b,t7\\b\\b\n")
        with open(os.path.join(root, "sound", "a.aliases.csv"), encoding="utf-8") as f:
            self.assertIn("wpn_dry", f.read())

    def test_variant_rows_of_one_table_are_kept(self):
        root = tempfile.mkdtemp()
        write(os.path.join(root, "sound", "a.aliases.csv"), "Name,File\nwpn_shot,t7/a/shot\nwpn_shot,t7/a/shot_v2\n")
        write(os.path.join(root, "sound", "b.aliases.csv"), "Name,File\nwpn_shot,t7/b/shot\nwpn_shot,t7/b/shot_v2\n")
        dropped = asm.dedupe_bank_aliases(root, ["sound/a.aliases.csv", "sound/b.aliases.csv"])
        self.assertEqual(dropped, [["wpn_shot", "sound/a.aliases.csv", "sound/b.aliases.csv"]] * 2)
        with open(os.path.join(root, "sound", "a.aliases.csv"), encoding="utf-8") as f:
            self.assertEqual(f.read().count("wpn_shot"), 2)

    def test_measure_mix(self):
        # the engine hash of the Paris mod's own mix, as recorded in the server docs
        self.assertEqual(asm.sound_hash("paris_music_off"), 3429397084)
        root = tempfile.mkdtemp()
        bank = {"aliases": [], "MixDefs": []}
        asm.write_measure_mix(root, "mod.all", bank)
        self.assertEqual(bank["MixDefs"], ["sound/mod.all.mixes.csv"])
        with open(os.path.join(root, "sound", "mod.all.mixes.csv"), encoding="ascii") as f:
            rows = f.read().splitlines()
        self.assertEqual(rows[0], "idString,VolMod,Volume,Fade")
        self.assertIn("%d,music,0.000000,0.100000" % asm.sound_hash("bo3wpn_measure"), rows)
        self.assertFalse(any(",wpn_plr," in r for r in rows))

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

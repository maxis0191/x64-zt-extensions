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
        write(os.path.join(port, "catalog.txt"), "wpn_tg_fire_plr=iw7_tg_zm\n")
        out = asm.assemble(mod, csv, "mod.all", "mod", [port])
        self.assertTrue(os.path.exists(os.path.join(mod, "weapons", "iw7_tg_zm.json")))
        self.assertFalse(os.path.exists(os.path.join(mod, "soundbank", "iw7_tg_zm.json")))
        self.assertEqual(out["bank_aliases"], ["sound/mod.all.aliases.csv", "sound/iw7_tg_zm.aliases.csv"])
        self.assertEqual(out["added_lines"], ["xmodel,tg_view", "weapon,iw7_tg_zm"])
        self.assertEqual(out["catalog"], ["wpn_tg_fire_plr=iw7_tg_zm"])
        again = asm.assemble(mod, csv, "mod.all", "mod", [port])       # idempotent
        self.assertEqual(again["added_lines"], [])


if __name__ == "__main__":
    unittest.main()

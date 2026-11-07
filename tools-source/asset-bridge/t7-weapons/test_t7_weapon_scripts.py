"""Synthetic tests for t7_weapon_scripts.py (no game data)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_weapon_scripts as scripts  # noqa: E402

TESLA = '''#using scripts\\shared\\util_shared;
#using scripts\\zm\\_zm_lightning_chain;
function __init__()
{
    level.weaponzmteslagun = getweapon( "tesla_gun" );
    level.weaponzmteslagunupgraded = getweapon( "tesla_gun_upgraded" );
}
function __main__()
{
    level._effect["tesla_viewmodel_rail"] = "zombie/fx_tesla_rail_view_zmb";
    zombie_utility::set_zombie_var( "tesla_max_arcs", 5 );
    zombie_utility::set_zombie_var( "tesla_radius_decay", 20.5 );
}
'''
CHAIN = '''function arc()
{
    level._effect["tesla_bolt"] = "zombie/fx_tesla_bolt_secondary_zmb";
}
'''
OTHER = '''function x() { a = getweapon( "thundergun" ); }'''


class ScriptsTest(unittest.TestCase):
    def setUp(self):
        self.sources = {"scripts/zm/_zm_weap_tesla.gsc": TESLA, "scripts/zm/_zm_lightning_chain.gsc": CHAIN,
                        "scripts/zm/_zm_weap_thundergun.gsc": OTHER}

    def test_selects_scripts_naming_the_weapon_and_their_usings(self):
        self.assertEqual(scripts.select(self.sources, ["tesla_gun"]),
                         ["scripts/zm/_zm_lightning_chain.gsc", "scripts/zm/_zm_weap_tesla.gsc"])

    def test_extracts_tuning_and_effects(self):
        info = scripts.extract(TESLA)
        self.assertEqual(info["zombie_vars"], {"tesla_max_arcs": 5, "tesla_radius_decay": 20.5})
        self.assertEqual(info["effects"], {"tesla_viewmodel_rail": "zombie/fx_tesla_rail_view_zmb"})
        self.assertEqual(info["weapons"], ["tesla_gun", "tesla_gun_upgraded"])

    def test_no_reference_no_script(self):
        self.assertEqual(scripts.select(self.sources, ["ray_gun"]), [])


if __name__ == "__main__":
    unittest.main()

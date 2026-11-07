"""Synthetic tests for t7_port_weapon.py helpers (no game data)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_port_weapon as port  # noqa: E402


class AdsTest(unittest.TestCase):
    def test_sight_line_over_rear_and_front_tops(self):
        verts = [(-4, 0, 1), (-2, 0, 5.2), (0, 0.2, 4), (4, 0, 4.4), (10, 0, 6.3), (14, 0, 3), (5, 3, 20)]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "m_LOD0.XMODEL_EXPORT")
            with open(p, "w") as f:
                f.write("MODEL\n" + "".join("OFFSET %f, %f, %f\n" % v for v in verts))
            self.assertEqual(port.ads_gun_from_mesh(p), (8.0, 0.0, -5.75))   # (5.2 + 6.3) / 2; side point ignored


class PackageTest(unittest.TestCase):
    def test_vfx_package_roles(self):
        spec = {"fx": {"flash_view": {"iw7": "vfx/t7/a"}, "flash_world": {"iw7": "vfx/t7/b"}}}
        v = port.vfx_package(spec)["vfx"]
        self.assertEqual(v["viewFlashEffect"], {"type": 1, "fx": "vfx/t7/a"})
        self.assertEqual(v["viewFlashADSEffect"], {"type": 1, "fx": "vfx/t7/a"})
        self.assertEqual(v["worldFlashEffect"], {"type": 1, "fx": "vfx/t7/b"})
        self.assertIsNone(v["viewShellEjectEffect"])

    def test_sfx_package_roles(self):
        tpl = {"sounds": {"name": "x", "fireSound": "stock_fire", "fireSoundPlayer": "stock_plr",
                          "pickupSound": "weap_pickup_npc", "reloadSound": "stock_reload"}}
        spec = {"name": "iw7_t_zm", "sounds": {"fire_npc": "wpn_t_npc", "fire_plr": "wpn_t_plr"}}
        s = port.sfx_package(spec, tpl)["sounds"]
        self.assertEqual((s["name"], s["fireSound"], s["fireSoundPlayer"]), ("iw7_t_zm_sfxpackage", "wpn_t_npc", "wpn_t_plr"))
        self.assertEqual(s["reloadSound"], "")          # no stock sound leaks into a BO3 weapon
        self.assertEqual(s["pickupSound"], "weap_pickup_npc")


class AuthorEffectsTest(unittest.TestCase):
    def test_template_effects_never_leak(self):
        import iw7_weapon_author as author
        weapon = {"szDisplayName": "", "iClipSize": 0, "notetrackSoundMapKeys": [""], "notetrackSoundMapValues": [""],
                  "weapDef": {"szDisplayName": "", "projTrailEffect": None, "projExplosionEffect": None}}
        projectile = {"weapDef": {"projTrailEffect": {"type": 1, "fx": "vfx/iw7/stock_trail"},
                                  "projExplosionEffect": {"type": 1, "fx": "vfx/iw7/stock_impact"},
                                  "projDudEffect": {"type": 1, "fx": "vfx/iw7/stock_dud"}, "iProjectileSpeed": 1}}
        spec = {"name": "iw7_t_zm", "anims": {}, "xab_dir": ".", "clip": 2, "max_ammo": 12, "fire_time_ms": 950,
                "view_model": "v", "world_model": "w",
                "projectile": {"iProjectileSpeed": 2000, "projTrailEffect": "vfx/t7/zombie/trail"}}
        w, _ = author.author(spec, weapon, {"anims": {}, "timers": {}}, projectile)
        d = w["weapDef"]
        self.assertEqual(d["projTrailEffect"], {"type": 1, "fx": "vfx/t7/zombie/trail"})
        self.assertIsNone(d["projExplosionEffect"])      # BO3 has none: no stock impact either
        self.assertIsNone(d["projDudEffect"])
        self.assertEqual(d["iProjectileSpeed"], 2000)


if __name__ == "__main__":
    unittest.main()

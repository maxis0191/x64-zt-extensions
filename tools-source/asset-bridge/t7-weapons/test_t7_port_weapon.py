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


class BehaviourTest(unittest.TestCase):
    FOUND = {
        "scripts/zm/_zm_weap_thundergun.csc": {"namespace": "zm_weap_thundergun", "zombie_vars": {}, "effects": {},
                                               "sounds": []},
        "scripts/zm/_zm_weap_thundergun.gsc": {
            "namespace": "zm_weap_thundergun",
            "zombie_vars": {"thundergun_cylinder_radius": 180, "thundergun_fling_range": 480},
            "effects": {"thundergun_smoke_cloud": "zombie/fx_thundergun_smoke_cloud",
                        "thundergun_knockdown_ground": "zombie/fx_thundergun_knockback_ground"},
            "sounds": ["fly_thundergun_forcehit", "tesla_idle"]},
    }

    def test_one_line_per_weapon_with_built_effects_and_carried_sounds(self):
        lines = port.behaviour_lines(["iw7_thundergun_zm", "iw7_thundergun_zm_pap1"], self.FOUND,
                                     {"zombie/fx_thundergun_smoke_cloud"}, {"fly_thundergun_forcehit"})
        self.assertEqual(lines, [
            "iw7_thundergun_zm|zm_weap_thundergun|thundergun_cylinder_radius=180,thundergun_fling_range=480|"
            "thundergun_smoke_cloud=vfx/t7/zombie/fx_thundergun_smoke_cloud|fly_thundergun_forcehit",
            "iw7_thundergun_zm_pap1|zm_weap_thundergun|thundergun_cylinder_radius=180,thundergun_fling_range=480|"
            "thundergun_smoke_cloud=vfx/t7/zombie/fx_thundergun_smoke_cloud|fly_thundergun_forcehit"])

    def test_alias_passed_as_parameter_is_carried(self):
        found = {"t.gsc": {"namespace": "_zm_weap_tesla", "zombie_vars": {"tesla_max_arcs": 5}, "effects": {},
                           "sounds": [], "literals": ["tesla_gun", "wpn_tesla_bounce"]}}
        self.assertEqual(port.behaviour_lines(["w"], found, set(), {"wpn_tesla_bounce"}),
                         ["w|_zm_weap_tesla|tesla_max_arcs=5||wpn_tesla_bounce"])

    def test_scripts_of_one_namespace_merge_into_one_line(self):
        found = {"lc.csc": {"namespace": "lightning_chain", "zombie_vars": {}, "effects": {"tesla_bolt": "z/bolt"},
                            "sounds": []},
                 "lc.gsc": {"namespace": "lightning_chain", "zombie_vars": {}, "effects": {"tesla_bolt": "z/bolt"},
                            "sounds": ["zmb_electrocute_zombie"]},
                 "t.csc": {"namespace": "_zm_weap_tesla", "zombie_vars": {}, "effects": {"rail": "z/rail"}},
                 "t.gsc": {"namespace": "_zm_weap_tesla", "zombie_vars": {"tesla_max_arcs": 5}, "effects": {}}}
        lines = port.behaviour_lines(["w"], found, {"z/bolt", "z/rail"}, {"zmb_electrocute_zombie"})
        self.assertEqual(sorted(lines), ["w|_zm_weap_tesla|tesla_max_arcs=5|rail=vfx/t7/z/rail|",
                                         "w|lightning_chain||tesla_bolt=vfx/t7/z/bolt|zmb_electrocute_zombie"])

    def test_scripts_without_namespace_or_data_add_nothing(self):
        found = {"a.gsc": {"namespace": None, "zombie_vars": {"x": 1}, "effects": {}},
                 "b.csc": {"namespace": "zm_weap_x", "zombie_vars": {}, "effects": {}}}
        self.assertEqual(port.behaviour_lines(["w"], found, set()), [])


class ModelSurfacesTest(unittest.TestCase):
    def test_surfaces_are_the_ones_the_model_names(self):
        root = tempfile.mkdtemp()
        surf = os.path.join(root, "xsurface")
        os.makedirs(surf)
        for name in ("wpn_hd_gun_view4b01d4fb", "wpn_hd_gun_lod0c315ca95", "wpn_gun_view_other"):
            open(os.path.join(surf, name + ".xsb"), "wb").close()
        xmb = os.path.join(root, "wpn_gun_view.xmb")
        with open(xmb, "wb") as f:
            f.write(b"\x06\x01wpn_gun_view\x00\x10\x00wpn_hd_gun_view4b01d4fb\x00mc/mtl_gun\x00")
        self.assertEqual([os.path.basename(p) for p in port.model_surfaces(xmb, surf)],
                         ["wpn_hd_gun_view4b01d4fb.xsb"])


class SnapshotConfigTest(unittest.TestCase):
    def test_snapshot_folder_supplies_scan_and_effects(self):
        cfg = port.with_snapshot({"snapshots": "snap", "zone": "zm_island"})
        self.assertEqual(cfg["scan"], os.path.join("snap", "zm_island.weapons.json"))
        self.assertEqual(cfg["effects"], os.path.join("snap", "zm_island.effects.json"))

    def test_explicit_paths_win(self):
        cfg = port.with_snapshot({"snapshots": "snap", "zone": "zm_island", "scan": "mine.json"})
        self.assertEqual(cfg["scan"], "mine.json")


if __name__ == "__main__":
    unittest.main()

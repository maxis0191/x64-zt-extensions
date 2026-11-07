"""Synthetic tests for t7_weapon_spec.py (no game data)."""
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_weapon_spec as spec  # noqa: E402


def asset(off, typ, name):
    return {"off": off, "kind": "asset", "type": typ, "name": name}


def string(off, value):
    return {"off": off, "kind": "string", "value": value}


def block(size, refs, children=None, ints=(), floats=()):
    raw = bytearray(size)
    for off, value in ints:
        struct.pack_into("<i", raw, off, value)
    for off, value in floats:
        struct.pack_into("<f", raw, off, value)
    b = {"addr": "0x1000", "size": size, "hex": raw.hex(), "refs": refs}
    if children:
        b["children"] = children
    return b


def anim_table(names):
    # 44 default entries, an inline string pool, its null terminator, then the anim array
    refs = [string((71 + i) * 8, n) for i, n in enumerate(names) if n]
    return block(0x800, refs)


def scan(anims, upgraded=True):
    weapdef = block(0x2000, [
        asset(0x8, "xmodel", "wpn_t7_zmb_thundergun_view"),
        asset(0x878, "xmodel", "wpn_t7_zmb_thundergun_world"),
        asset(0x2e0, "fx", "zombie/fx_muz_thundergun_1p"),
        asset(0x2e8, "fx", "zombie/fx_muz_thundergun_3p"),
        asset(0x11b8, "fx", "zombie/fx_trail_thundergun"),
        string(0x358, "wpn_thundergun_proj_loop"),
        string(0x378, "wpn_thundergun_fire_npc"),
        string(0x380, "wpn_thundergun_fire_plr"),
        string(0x1088, "wpn_thundergun_proj_impact"),
    ], children={"96": anim_table(anims)}, ints=[(0x8F8, 12), (0x8FC, 12), (0xA1C, 950), (0xFEC, 2000)],
        floats=[(0x1004, 0.5), (0x1268 + 8, -30.0)])
    root = block(0x400, [string(0x0, "thundergun_zm"), string(0x8, "thundergun"), string(0x20, "WEAPON_THUNDERGUN")],
                 children={"24": weapdef}, ints=[(0x194, 2)])
    weapons = {"thundergun_zm": root}
    if upgraded:
        weapons["thundergun_upgraded_zm"] = root
    return {"weapons": weapons}


class SpecTest(unittest.TestCase):
    def test_roles_stats_and_names(self):
        s = spec.build(scan(["vm_thunder_gun_idle", None, None, "vm_thunder_gun_fire",
                             "vm_thunder_gun_reload_empty", "vm_thunder_gun_ads_base_up"]),
                       "thundergun_zm", zone="zm_levelcommon")
        self.assertEqual(s["name"], "iw7_thundergun_zm")
        self.assertEqual(s["view_model"], "wpn_t7_zmb_thundergun_view")
        self.assertEqual(s["world_model"], "wpn_t7_zmb_thundergun_world")
        self.assertEqual((s["clip"], s["max_ammo"], s["start_ammo"], s["fire_time_ms"]), (2, 12, 12, 950))
        self.assertEqual(s["fx"]["trail"], {"bo3": "zombie/fx_trail_thundergun", "iw7": "vfx/t7/zombie/fx_trail_thundergun"})
        self.assertEqual(s["sounds"]["fire_plr"], "wpn_thundergun_fire_plr")
        self.assertEqual(s["projectile"]["iProjectileSpeed"], 2000)
        # a straight shot carries its zero launch components, so no template lob survives
        self.assertEqual((s["projectile"]["iProjectileSpeedUp"], s["projectile"]["iProjectileSpeedForward"]), (0, 0))
        self.assertAlmostEqual(s["projectile"]["projLifetime"], 0.5)
        self.assertEqual(s["upgrade"], "thundergun_upgraded_zm")
        self.assertEqual(s["display_key"], "WEAPON_THUNDERGUN")
        self.assertEqual(s["base"], "thundergun")
        self.assertEqual(s["kick"]["fHipGunKickPitchMin"], -30.0)

    def test_anim_roles_from_suffixes(self):
        s = spec.build(scan(["vm_dg2_idle", "vm_dg2_idle", None, "vm_dg2_fire", "vm_dg2_reload_empty",
                             "vm_dg2_pullout", "vm_dg2_first_raise", "vm_dg2_putaway", "vm_dg2_fire_ads",
                             "vm_dg2_ads_base_up", "vm_dg2_ads_base_down", "vm_dg2_sprint_in"]), "thundergun_zm")
        a = s["anims"]
        self.assertEqual(a["idle"], "vm_dg2_idle")
        self.assertEqual(a["reload"], "vm_dg2_reload_empty")      # no plain reload: the empty one serves
        self.assertEqual(a["reload_empty"], "vm_dg2_reload_empty")
        self.assertEqual(a["ads_up"], "vm_dg2_ads_base_up")
        self.assertEqual(a["fire_ads"], "vm_dg2_fire_ads")
        self.assertEqual(a["sprint_in"], "vm_dg2_sprint_in")
        self.assertNotIn("crawl_in", a)
        self.assertIn("vm_dg2_fire_ads", s["all_anims"])

    def test_missing_upgrade_is_none(self):
        s = spec.build(scan(["vm_x_idle"], upgraded=False), "thundergun_zm")
        self.assertIsNone(s["upgrade"])

    def test_unknown_weapon_refused(self):
        with self.assertRaises(SystemExit):
            spec.build(scan(["vm_x_idle"]), "nope_zm")


if __name__ == "__main__":
    unittest.main()

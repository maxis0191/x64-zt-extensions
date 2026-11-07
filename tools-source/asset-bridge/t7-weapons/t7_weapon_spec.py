"""Build an IW7 port spec for any BO3 (T7) weapon from a t7_weapon_scan.py capture.

Every T7 weapon shares one WeaponDef layout, so each role sits at a fixed
offset (measured on the Ray Gun, its upgrade, the Thundergun and the
Wunderwaffe DG-2; see STATUS.md). Nothing here names a particular weapon:
the spec is the input of iw7_weapon_author.py and of t7_port_weapon.py.

  WeaponVariantDef (root):  +0x0 name, +0x8 base name (scripts), +0x20 display
                            string key, +0x194 clip
  WeaponDef (root child 24): models, flash/impact/trail effects and sound
  aliases (ROLE_*), ammo, fire time, projectile values, gun/view kick, and at
  +0x60 a block whose anim name array follows an inline string pool.

Anim roles come from each name's suffix after the weapon's common anim prefix
(``vm_thunder_gun_`` + ``ads_base_up`` -> ``ads_up``). The upgrade is the
``<base>_upgraded_zm`` weapon when the scan holds it: the variant memory after
+0x300 belongs to whichever asset follows in memory and is not a link.
"""
import argparse
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_weapon_kick  # noqa: E402

WEAPDEF = "24"            # WeaponVariantDef +0x18 -> WeaponDef
ANIM_TABLE = "96"         # WeaponDef +0x60
ROLE_MODELS = {"view_model": 0x8, "world_model": 0x878}
ROLE_FX = {"flash_view": 0x2E0, "flash_world": 0x2E8, "impact": 0x1028, "trail": 0x11B8}
ROLE_SOUNDS = {"proj_loop": 0x358, "fire_npc": 0x378, "fire_plr": 0x380, "fire_npc_last": 0x418,
               "fire_plr_last": 0x420, "dryfire_npc": 0x428, "dryfire_plr": 0x430, "proj_impact": 0x1088}
CLIP = 0x194              # in the variant
INTS = {"max_ammo": 0x8F8, "start_ammo": 0x8FC, "fire_time_ms": 0xA1C}
PROJECTILE_INTS = {"iExplosionInnerDamage": 0xFB4, "iExplosionRadius": 0xFB8, "iExplosionOuterDamage": 0xFC0,
                   "iProjectileSpeed": 0xFEC}
PROJECTILE_FLOATS = {"projLifetime": 0x1004}
# role -> accepted suffixes, first match wins
ANIM_ROLES = {
    "idle": ["idle"], "empty_idle": ["empty_idle"], "fire": ["fire"], "fire_ads": ["fire_ads"],
    "lastshot": ["lastshot", "fire_last"], "reload": ["reload", "reload_empty"], "reload_empty": ["reload_empty"],
    "pullout": ["pullout"], "first_raise": ["first_raise"], "putaway": ["putaway"],
    "pullout_quick": ["pullout_quick"], "putaway_quick": ["putaway_quick"],
    "ads_up": ["ads_up", "ads_base_up"], "ads_down": ["ads_down", "ads_base_down"],
    "sprint_in": ["sprint_in"], "sprint_loop": ["sprint_loop"], "sprint_out": ["sprint_out"],
}


def refs_at(block):
    out = {}
    for r in block.get("refs", []):
        out[r["off"]] = r["name"] if r["kind"] == "asset" else r.get("value")
    return out


def anim_names(table):
    """Anim names in array order (the array follows the string pool; only names matter here)."""
    names = [r["value"] for r in sorted(table.get("refs", []), key=lambda r: r["off"]) if r["kind"] == "string"]
    return list(dict.fromkeys(n for n in names if n))


def common_prefix(names):
    if not names:
        return ""
    if len(names) == 1:
        return names[0].rsplit("_", 1)[0] + "_"
    prefix = os.path.commonprefix(names)
    return prefix[:prefix.rfind("_") + 1]


def anim_roles(names):
    prefix = common_prefix(names)
    by_suffix = {n[len(prefix):]: n for n in names}
    roles = {}
    for role, suffixes in ANIM_ROLES.items():
        for s in suffixes:
            if s in by_suffix:
                roles[role] = by_suffix[s]
                break
    return roles


def iw7_fx_name(bo3):
    return "vfx/t7/" + bo3


def build(scan, weapon, zone=None, name=None):
    weapons = scan["weapons"]
    if weapon not in weapons:
        raise SystemExit("weapon %s is not in the scan" % weapon)
    variant = weapons[weapon]
    wd = variant.get("children", {}).get(WEAPDEF)
    if wd is None:
        raise SystemExit("weapon %s has no WeaponDef block in the scan" % weapon)
    vraw, wraw = bytes.fromhex(variant["hex"]), bytes.fromhex(wd["hex"])
    vrefs, wrefs = refs_at(variant), refs_at(wd)
    i32 = lambda raw, off: struct.unpack_from("<i", raw, off)[0]  # noqa: E731
    f32 = lambda raw, off: round(struct.unpack_from("<f", raw, off)[0], 4)  # noqa: E731

    names = anim_names(wd.get("children", {}).get(ANIM_TABLE, {}))
    upgrade = weapon[:-3] + "_upgraded_zm" if weapon.endswith("_zm") else None
    spec = {
        "name": name or "iw7_" + weapon,
        "source": {"bo3_weapon": weapon, "zone": zone},
        "base": vrefs.get(0x8),              # the name BO3 scripts use: getweapon("<base>")
        "display_key": vrefs.get(0x20),
        "upgrade": upgrade if upgrade in weapons else None,
        "clip": i32(vraw, CLIP),
        "anims": anim_roles(names),
        "all_anims": names,
        "fx": {}, "sounds": {}, "projectile": {},
        "kick": t7_weapon_kick.kick_fields(wraw),
    }
    for role, off in ROLE_MODELS.items():
        spec[role] = wrefs.get(off)
    for role, off in INTS.items():
        spec[role] = i32(wraw, off)
    for role, off in ROLE_FX.items():
        if wrefs.get(off):
            spec["fx"][role] = {"bo3": wrefs[off], "iw7": iw7_fx_name(wrefs[off])}
    for role, off in ROLE_SOUNDS.items():
        if wrefs.get(off):
            spec["sounds"][role] = wrefs[off]
    for key, off in PROJECTILE_INTS.items():
        spec["projectile"][key] = i32(wraw, off)
    for key, off in PROJECTILE_FLOATS.items():
        spec["projectile"][key] = f32(wraw, off)
    if "trail" in spec["fx"]:
        spec["projectile"]["projTrailEffect"] = spec["fx"]["trail"]["iw7"]
    if "impact" in spec["fx"]:
        spec["projectile"]["projExplosionEffect"] = spec["fx"]["impact"]["iw7"]
    return spec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scan", required=True, help="t7_weapon_scan.py JSON")
    ap.add_argument("--weapon", required=True, help="BO3 weapon asset (e.g. thundergun_zm)")
    ap.add_argument("--zone", help="BO3 zone the scan came from")
    ap.add_argument("--name", help="IW7 weapon name (default iw7_<bo3 weapon>)")
    ap.add_argument("--out", help="write the spec here (default stdout)")
    args = ap.parse_args(argv)
    with open(args.scan, encoding="utf-8") as f:
        spec = build(json.load(f), args.weapon, args.zone, args.name)
    text = json.dumps(spec, indent=1)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

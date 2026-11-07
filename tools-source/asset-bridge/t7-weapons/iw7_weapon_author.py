"""Author an IW7 weapon and anim package from a BO3 weapon spec.

The spec (JSON) carries what was measured on the BO3 side (models, anim
names, clip/ammo, fire time, projectile values, notetrack sound aliases).
Stock IW7 templates provide every field BO3 has no equivalent for. Anim
durations come from the converted IW7 ``.xab`` files (independent reader
``animation/xab_preflight.py``), so timers match the animations exactly.

Outputs (ZoneTool IW7 source layout) under ``--out``:
  weapons/<name>.json
  animpkg/<name>_package.json
"""
import argparse
import copy
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
XAB_READER = os.path.join(HERE, "..", "animation", "xab_preflight.py")

# BO3 anim-name suffix -> IW7 anim package slots.
SLOT_MAP = {
    "idle": ["WEAP_ANIM_IDLE", "WEAP_ANIM_EMPTY_IDLE"],
    "fire": ["WEAP_ANIM_FIRE", "WEAP_ANIM_LASTSHOT", "WEAP_ANIM_ADS_FIRE", "WEAP_ANIM_ADS_LASTSHOT"],
    "fire_ads": ["WEAP_ANIM_ADS_FIRE", "WEAP_ANIM_ADS_LASTSHOT"],
    "reload": ["WEAP_ANIM_RELOAD", "WEAP_ANIM_RELOAD_EMPTY"],
    "reload_empty": ["WEAP_ANIM_RELOAD_EMPTY"],
    "pullout": ["WEAP_ANIM_RAISE", "WEAP_ANIM_QUICK_RAISE", "WEAP_ANIM_EMPTY_RAISE"],
    "first_raise": ["WEAP_ANIM_FIRST_RAISE"],
    "putaway": ["WEAP_ANIM_DROP", "WEAP_ANIM_QUICK_DROP", "WEAP_ANIM_EMPTY_DROP"],
    "ads_up": ["WEAP_ANIM_ADS_UP"],
    "ads_down": ["WEAP_ANIM_ADS_DOWN"],
    "sprint_in": ["WEAP_ANIM_SPRINT_IN"],
    "sprint_loop": ["WEAP_ANIM_SPRINT_LOOP"],
    "sprint_out": ["WEAP_ANIM_SPRINT_OUT"],
}
# Slots whose stock additive/finger-pose anims would fight a full BO3 pose.
CLEAR_SLOTS = ("WEAP_ANIM_ADDITIVE_SPRINT_OFFSET", "WEAP_ANIM_ADDITIVE_FINGER_POSE_LEFT",
               "WEAP_ANIM_ADDITIVE_FINGER_POSE_RIGHT", "WEAP_ANIM_ADDITIVE_SETTLE_ADS",
               "WEAP_ANIM_RECOIL_SETTLE", "WEAP_ANIM_RECOIL")
# IW7 timer -> BO3 anim suffix whose duration defines it.
TIMER_MAP = {
    "iReloadTime": "reload", "iReloadEmptyTime": "reload_empty|reload",
    "iRaiseTime": "pullout", "quickRaiseTime": "pullout", "iEmptyRaiseTime": "pullout",
    "iFirstRaiseTime": "first_raise",
    "iDropTime": "putaway", "quickDropTime": "putaway", "iEmptyDropTime": "putaway",
    "sprintInTime": "sprint_in", "sprintLoopTime": "sprint_loop", "sprintOutTime": "sprint_out",
}
PROJECTILE_FIELDS = ("iExplosionRadius", "iExplosionInnerDamage", "iExplosionOuterDamage",
                     "iProjectileSpeed", "projLifetime")


def anim_info(xab_dir, name):
    path = os.path.join(xab_dir, name + ".xab")
    out = subprocess.run([sys.executable, "-B", XAB_READER, path, "--game", "iw7"],
                         capture_output=True, text=True)
    if out.returncode:
        raise SystemExit("xab check failed for %s: %s" % (name, out.stdout or out.stderr))
    info = json.loads(out.stdout)
    duration_ms = round(1000.0 * info["numframes"] / info["framerate"]) if info["framerate"] else 0
    return {"duration_ms": duration_ms, "notetracks": info["notetracks"]}


def author(spec, weapon_tpl, animpkg_tpl, projectile_tpl):
    anims = spec["anims"]
    infos = {k: anim_info(spec["xab_dir"], v) for k, v in anims.items()}

    pkg = copy.deepcopy(animpkg_tpl)
    for slot in CLEAR_SLOTS:
        if slot in pkg["anims"]:
            pkg["anims"][slot] = ""
    for suffix, slots in SLOT_MAP.items():
        if suffix in anims:
            for slot in slots:
                pkg["anims"][slot] = anims[suffix]
    for timer, sources in TIMER_MAP.items():
        for suffix in sources.split("|"):
            if suffix in infos:
                pkg["timers"][timer] = infos[suffix]["duration_ms"]
                break
    reload_add = spec.get("reload_add_notetrack")
    if reload_add and "reload" in infos:
        for nt in infos["reload"]["notetracks"]:
            if nt["name"] == reload_add:
                pkg["timers"]["iReloadAddTime"] = round(nt["normalized_time"] * infos["reload"]["duration_ms"])
                break

    w = copy.deepcopy(weapon_tpl)
    d = w["weapDef"]
    w["szInternalName"] = spec["name"]
    w["szDisplayName"] = spec.get("display", w["szDisplayName"])
    w["iClipSize"] = spec["clip"]
    d["iMaxAmmo"] = spec["max_ammo"]
    d["iStartAmmo"] = spec.get("start_ammo", spec["max_ammo"])
    d["iFireTime"] = spec["fire_time_ms"]
    d["gunXModel"] = d["defaultViewModel"] = spec["view_model"]
    d["worldModel"] = d["defaultWorldModel"] = spec["world_model"]
    for key in ("complexWorldModel", "complexGunXModel", "camoWorldModelMaterialOverride",
                "camoViewModelMaterialOverride"):
        if isinstance(d.get(key), list):
            d[key] = ["" for _ in d[key]]
    for key in ("animOverrides", "sfxOverrides"):
        for entry in d.get(key, []):
            for field in entry:
                if isinstance(entry[field], str):
                    entry[field] = ""
    for key in [k for k in w if k.startswith("attachments")]:
        if isinstance(w[key], list):
            w[key] = ["" for _ in w[key]]
    d["szXAnims"] = spec["name"] + "_package"

    sounds = spec.get("notetrack_sounds", {})
    keys = list(sounds)[:len(w["notetrackSoundMapKeys"])]
    w["notetrackSoundMapKeys"] = keys + [""] * (len(w["notetrackSoundMapKeys"]) - len(keys))
    w["notetrackSoundMapValues"] = [sounds[k] for k in keys] + [""] * (len(w["notetrackSoundMapValues"]) - len(keys))

    proj = spec.get("projectile")
    if proj:
        pd = projectile_tpl["weapDef"]
        for key, value in pd.items():
            low = key.lower()
            if low.startswith(("proj", "iprojectile", "iexplosion")) or key in (
                    "projectileModel", "bProjImpactExplode", "vProjectileColor", "parallelBounce",
                    "perpendicularBounce", "weapType"):
                # the template's own effects never reach a ported weapon: BO3's or nothing
                d[key] = None if key.endswith("Effect") else copy.deepcopy(value)
        for key in PROJECTILE_FIELDS:
            if key in proj:
                d[key] = proj[key]
        for key in ("projTrailEffect", "projExplosionEffect"):
            if key in proj:
                d[key] = {"type": 1, "fx": proj[key]}
    return w, pkg


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("spec")
    ap.add_argument("--weapon-template", required=True)
    ap.add_argument("--animpkg-template", required=True)
    ap.add_argument("--projectile-template", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    load = lambda p: json.load(open(p, encoding="utf-8"))
    spec = load(args.spec)
    w, pkg = author(spec, load(args.weapon_template), load(args.animpkg_template), load(args.projectile_template))
    for sub, name, data in (("weapons", spec["name"], w), ("animpkg", spec["name"] + "_package", pkg)):
        os.makedirs(os.path.join(args.out, sub), exist_ok=True)
        with open(os.path.join(args.out, sub, name + ".json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    print(json.dumps({"weapon": spec["name"], "timers": {k: pkg["timers"][k] for k in
                      list(TIMER_MAP) + ["iReloadAddTime"] if k in pkg["timers"]}}, indent=1))


if __name__ == "__main__":
    sys.exit(main())

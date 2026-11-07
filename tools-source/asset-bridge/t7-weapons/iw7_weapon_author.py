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
# The template weapon's third-person finger poses (hm_fingers_zapper_*).
TEMPLATE_WEAPON_SLOTS = ("WEAP_ANIM_3P_FINGER_POSE_LEFT", "WEAP_ANIM_3P_FINGER_POSE_RIGHT")
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
                     "iProjectileSpeed", "iProjectileSpeedUp", "iProjectileSpeedForward", "projLifetime")


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
    # Every weapon-specific slot starts empty: a slot BO3 does not fill must not keep the template
    # weapon's motion (the upgraded ports had played the IW7 zapper's idle, fire and reload).
    # Engine-wide generic additives (jump, walk, crawl, melee knife) stay.
    for slot in CLEAR_SLOTS + TEMPLATE_WEAPON_SLOTS + tuple(s for slots in SLOT_MAP.values() for s in slots):
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
    # Never the template's name (the generic ports had shown the IW7 facemelter's): the configured
    # BO3 name, else the BO3 display key made readable (WEAPON_THUNDERGUN -> Thundergun).
    key = spec.get("display_key") or spec["name"]
    w["szDisplayName"] = spec.get("display") or key.split("WEAPON_", 1)[-1].replace("_", " ").title()
    w["iClipSize"] = spec["clip"]
    d["iMaxAmmo"] = spec["max_ammo"]
    d["iStartAmmo"] = spec.get("start_ammo", spec["max_ammo"])
    d["iFireTime"] = spec["fire_time_ms"]
    if (spec.get("burst_count") or 1) > 1:
        # BO3 burst weapons (Ray Gun Mark II: 3 bolts per pull)
        d["fireType"] = 2               # WEAPON_FIRETYPE_BURST
        d["burstCount"] = spec["burst_count"]
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
    # The table grows with the weapon (stock IW7 weapons carry 1 to 20 entries): the template's four
    # slots had dropped the Ray Gun's reload_close.
    keys = list(sounds)
    size = max(len(w["notetrackSoundMapKeys"] or []), len(keys))
    w["notetrackSoundMapKeys"] = keys + [""] * (size - len(keys))
    w["notetrackSoundMapValues"] = [sounds[k] for k in keys] + [""] * (size - len(keys))

    # View-model effects played on an anim notetrack: {notetrack: [IW7 effect, tag]} (the DG-2 rail
    # when the gun switches on). The template's own entries never reach a ported weapon.
    fx_map = spec.get("notetrack_fx") or {}
    if isinstance(d.get("notetrackFXMapKeys"), list) or fx_map:
        keys = list(fx_map)
        size = max(len(d.get("notetrackFXMapKeys") or []), len(keys))
        pad = size - len(keys)
        d["notetrackFXMapKeys"] = keys + [""] * pad
        d["notetrackFXMapValues"] = [{"type": 1, "fx": fx_map[k][0]} for k in keys] + [None] * pad
        d["notetrackFXMapTagValues"] = [fx_map[k][1] for k in keys] + [""] * pad

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
    # The template's tracer is a map's own asset (the zapper's shredder_bullet exists on Spaceland
    # only: on Rave the client faulted holding the Ray Gun); BO3 Wonder Weapons draw no tracer.
    d["tracerType"] = spec.get("tracer", "")
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

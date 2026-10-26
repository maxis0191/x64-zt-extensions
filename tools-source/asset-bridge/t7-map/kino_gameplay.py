"""Extract Kino der Toten gameplay placements from the BO3 map entities.

Writes kino.gameplay/1: player starts and zone respawns, zombie spawners by
zone, window goals, perk machines, wall buys, box (magic wheel) locations,
GobbleGum (Fate & Fortune) machines, Pack-a-Punch, power switch, teleporter
pad, doors and the three 115 meteors. Each BO3 item carries its IW7 Zombies
equivalent so the server can stage a lore-consistent Willard Wyler remake
with retail IW7 systems. Coordinates stay in BO3 map space.
"""
import argparse, json, re
from collections import OrderedDict

# BO3 perk -> IW7 Zombies perk machine interaction (same role in the game).
PERKS = {
    "specialty_armorvest": "perk_machine_tough",                   # Juggernog -> Tuff 'Nuff
    "specialty_quickrevive": "perk_machine_revive",                # Quick Revive -> Up 'N Atoms
    "specialty_fastreload": "perk_machine_flash",                  # Speed Cola -> Quickies
    "specialty_doubletap2": "perk_machine_rat_a_tat",              # Double Tap -> Bang Bangs
    "specialty_additionalprimaryweapon": "perk_machine_more",      # Mule Kick -> Mule Munchies
    "specialty_staminup": "perk_machine_run",                      # Stamin-Up -> Racin' Stripes
    "specialty_phdflopper": "perk_machine_boom",                   # PhD -> Bomb Stoppers
    "specialty_deadshot": "perk_machine_deadeye",                  # Deadshot -> Deadeye Dewdrops
    "specialty_electriccherry": "perk_machine_zap",                # Electric Cherry -> Blue Bolts
}

# BO3 wall weapon -> one of the eight weapons that have wall-buy structs on the
# cp_zmb host (same class where possible). Two Kino spots may share a weapon
# when the host has two separate structs for it; frag grenades have no host
# wall buy.
WALL = {
    "pistol_burst": "iw7_revolver_zm", "pistol_fullauto": "iw7_ump45_zml",
    "smg_mp40_1940": "iw7_ump45_zml", "smg_fastfire": "iw7_erad_zm",
    "smg_versatile": "iw7_crb_zml", "smg_burst": "iw7_erad_zm",
    "ar_standard": "iw7_m4_zm", "ar_accurate": "iw7_ake_zml",
    "ar_marksman": "iw7_m1c_zm", "ar_longburst": "iw7_ake_zml",
    "shotgun_precision": "iw7_sonic_zmr",
}

# GobbleGum machines: three become Fate & Fortune card machines (one per host
# machine), the rest host extra IWZ perks absent from BO3 Kino.
FNF_SPOTS = ((-181, -929), (-202, 1884), (-1395, -300))
EXTRA_PERKS = ("perk_machine_run", "perk_machine_boom", "perk_machine_zap")


def vec(s):
    return [float(v) for v in s.split()] if s else [0.0, 0.0, 0.0]


def item(e, **extra):
    out = OrderedDict(origin=vec(e.get("origin")), angles=vec(e.get("angles")))
    out.update(extra)
    return out


def parse(text):
    return [dict(re.findall(r'"([^"]+)" "([^"]*)"', b)) for b in re.findall(r"\{(.*?)\}", text, re.S)]


def extract(ents):
    by = lambda name: [e for e in ents if e.get("targetname") == name]
    g = OrderedDict(schema="kino.gameplay/1", map="zm_theater")
    g["initial_spawns"] = [item(e) for e in by("initial_spawn_points")]
    zones = OrderedDict()
    for e in ents:
        t = e.get("targetname", "")
        if t.startswith("player_respawn_point_"):
            zones.setdefault(t[len("player_respawn_point_"):], []).append(item(e))
    g["respawns"] = zones
    spawners = OrderedDict()
    for e in ents:
        t = e.get("targetname", "")
        if e.get("classname") == "script_struct" and (t.startswith("zombie_spawner_") or t == "foyer_zone_spawners"):
            zone = "foyer" if t == "foyer_zone_spawners" else t[len("zombie_spawner_"):]
            spawners.setdefault(zone, []).append(item(e, kind=e.get("script_noteworthy", "spawn_location")))
    g["zombie_spawners"] = spawners
    g["window_goals"] = [item(e) for e in by("exterior_goal")]
    g["perks"] = [item(e, bo3=e["script_noteworthy"], iw7=PERKS[e["script_noteworthy"]]) for e in by("zm_perk_machine")]
    g["wall_buys"] = [item(e, bo3=e["zombie_weapon_upgrade"], iw7=WALL[e["zombie_weapon_upgrade"]])
                      for e in by("weapon_upgrade") if e.get("zombie_weapon_upgrade") in WALL]
    g["box"] = [item(e, name=e.get("script_noteworthy", ""), start=e.get("script_noteworthy") == "start_chest")
                for e in by("treasure_chest_use")]
    bgb = by("bgb_machine_use")
    near = lambda e, spot: abs(vec(e["origin"])[0] - spot[0]) < 2 and abs(vec(e["origin"])[1] - spot[1]) < 2
    fnf = [e for e in bgb if any(near(e, spot) for spot in FNF_SPOTS)]
    g["fate_fortune"] = [item(e) for e in fnf]
    spare = [e for e in bgb if e not in fnf]
    g["perks"] += [item(e, bo3="bgb_machine", iw7=perk) for e, perk in zip(spare, EXTRA_PERKS)]
    g["pack_a_punch"] = [item(e) for e in by("zm_pack_a_punch")]
    g["power_switch"] = [item(e) for e in by("use_elec_switch")]
    g["telepad"] = [item(e, part=e.get("script_sound", "")) for e in by("telepad")]
    doors = OrderedDict()
    for e in by("zombie_door"):
        d = doors.setdefault(e["target"], OrderedDict(name=e["target"], cost=int(e.get("zombie_cost", "1000")),
                                                    electric=e.get("script_noteworthy") == "electric_door",
                                                    flag=e.get("script_flag", ""), target=vec(e.get("targetOrigin")), triggers=[]))
        d["triggers"].append(vec(e["origin"]))
    g["doors"] = list(doors.values())
    g["meteors"] = [item(e) for e in by("songstructs")]
    return g


def add_facing(g, nodes):
    """Yaw from each machine toward the walkable room (mean direction to the
    path nodes within 220 units, snapped to the BO3 yaw plus a multiple of
    90 degrees); machines are placed facing that way."""
    import math
    for key in ("perks", "box", "fate_fortune", "pack_a_punch", "power_switch", "meteors"):
        for it in g[key]:
            o = it["origin"]
            vx = vy = 0.0
            for n in nodes:
                dx, dy = n[0] - o[0], n[1] - o[1]
                d = math.hypot(dx, dy)
                if 24 < d < 220 and abs(n[2] - o[2]) < 120:
                    vx += dx / d; vy += dy / d
            raw = math.degrees(math.atan2(vy, vx)) if (vx or vy) else it["angles"][1]
            # BO3 machines stand square to their wall: keep the BO3 yaw grid.
            base = it["angles"][1]
            it["facing"] = (base + 90.0 * round((raw - base) / 90.0)) % 360.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--navgraph", default="")
    a = ap.parse_args()
    g = extract(parse(open(a.export + "/mapents.txt", encoding="utf-8", errors="replace").read()))
    if a.navgraph:
        add_facing(g, json.load(open(a.navgraph))["nodes"])
    json.dump(g, open(a.out, "w"), indent=1)
    print(json.dumps({k: (len(v) if isinstance(v, (list, dict)) else v) for k, v in g.items()}))


if __name__ == "__main__":
    main()

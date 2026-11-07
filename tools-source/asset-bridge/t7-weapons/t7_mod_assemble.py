"""Merge t7_port_weapon.py outputs into one IW7 mod zone, stdlib only.

Each port writes its own ZoneTool asset tree (``<port>/zone``), its zone lines
(``zone.csv``) and its module catalog entry (``catalog.txt``). A mod is one
zone: this copies every port's assets into the mod zone source, appends the
lines the zone CSV lacks, and lists every weapon's alias table in the mod's
single sound bank (``soundbank/<bank>.json``; ZoneTool then writes one
mod.sabl/mod.sabs). The per-weapon bank JSONs are not copied.

    python t7_mod_assemble.py --mod-zone zonetool/bo3wpn --csv zone_source/bo3wpn.csv
        --bank bo3wpn.all --zone bo3wpn --port port/thundergun_zm [--port ...]
"""
import argparse
import json
import os
import shutil
import sys

BANK_LISTS = ('sendEffectParams', 'ADSRSettings', 'AmbientDefs', 'AmbientEvents', 'AmbientElements',
              'FilterDefs', 'MixDefs', 'NPCAdsrZoneEntry', 'PLRAdsrZoneEntry', 'OccludeDefs',
              'ReverbDefs', 'TimescaleEntrys', 'ZoneDefs', 'Unks', 'FullOcclusionDefs', 'PlayerBreathStateDefs')


def read_lines(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [line.rstrip("\r\n") for line in f]


def assemble(mod_zone, csv_path, bank, zone, ports):
    bank_path = os.path.join(mod_zone, "soundbank", bank + ".json")
    if os.path.exists(bank_path):
        with open(bank_path, encoding="utf-8") as f:
            bank_def = json.load(f)
    else:
        bank_def = {"name": bank, "zone": zone, "gameLanguage": "all", "soundLanguage": "all", "aliases": []}
        bank_def.update({k: [] for k in BANK_LISTS})
    lines = read_lines(csv_path)
    present = set(lines)
    added, catalog = [], []
    for port in ports:
        src = os.path.join(port, "zone")
        for folder, _, files in os.walk(src):
            rel = os.path.relpath(folder, src)
            if rel.split(os.sep)[0] == "soundbank":
                continue
            for name in files:
                dest = os.path.join(mod_zone, rel, name)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(os.path.join(folder, name), dest)
                if rel == "sound" and name.endswith(".aliases.csv"):
                    entry = "sound/" + name
                    if entry not in bank_def["aliases"]:
                        bank_def["aliases"].append(entry)
        for line in read_lines(os.path.join(port, "zone.csv")):
            if line and line not in present:
                lines.append(line)
                present.add(line)
                added.append(line)
        catalog += [c for c in read_lines(os.path.join(port, "catalog.txt")) if c]
    if bank_def["aliases"] and "soundbank," + bank not in present:
        lines.append("soundbank," + bank)
        added.append("soundbank," + bank)
    os.makedirs(os.path.dirname(bank_path), exist_ok=True)
    with open(bank_path, "w", encoding="utf-8") as f:
        json.dump(bank_def, f, indent=1)
    with open(csv_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return {"added_lines": added, "bank_aliases": bank_def["aliases"], "catalog": catalog}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mod-zone", required=True, help="ZoneTool asset root of the mod zone (zonetool/<zone>)")
    ap.add_argument("--csv", required=True, help="the mod zone's zone_source CSV")
    ap.add_argument("--bank", required=True, help="the mod zone's sound bank name (e.g. bo3wpn.all)")
    ap.add_argument("--zone", required=True, help="mod zone name")
    ap.add_argument("--port", action="append", required=True, help="t7_port_weapon.py output folder")
    args = ap.parse_args(argv)
    print(json.dumps(assemble(args.mod_zone, args.csv, args.bank, args.zone, args.port), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

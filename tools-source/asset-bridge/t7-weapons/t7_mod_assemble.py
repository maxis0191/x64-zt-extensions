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
import re
import shutil
import sys

BANK_LISTS = ('sendEffectParams', 'ADSRSettings', 'AmbientDefs', 'AmbientEvents', 'AmbientElements',
              'FilterDefs', 'MixDefs', 'NPCAdsrZoneEntry', 'PLRAdsrZoneEntry', 'OccludeDefs',
              'ReverbDefs', 'TimescaleEntrys', 'ZoneDefs', 'Unks', 'FullOcclusionDefs', 'PlayerBreathStateDefs')


GSC_BEGIN = "// BEGIN t7_mod_assemble catalog"
GSC_END = "// END t7_mod_assemble catalog"
GSC_ENTRY = re.compile(r'"([^"]+)"')


def merge_catalog(existing, new):
    """Entries keyed by weapon (first field); a new entry replaces the old one in place."""
    out = {}
    for entry in list(existing) + list(new):
        out[entry.split(":")[0]] = entry
    return list(out.values())


def gsc_block(text):
    """(start, end, entries) of the generated catalog block, or None."""
    begin, end = text.find(GSC_BEGIN), text.find(GSC_END)
    if begin < 0 or end < begin:
        return None
    body_start = text.index("\n", begin) + 1
    body_end = text.rindex("\n", 0, end) + 1
    return body_start, body_end, GSC_ENTRY.findall(text[body_start:body_end])


def render_gsc(entries, indent="    "):
    if not entries:
        return indent + "return [];\n"
    rows = (",\n" + indent * 2).join('"%s"' % e for e in entries)
    return "%sreturn [\n%s%s\n%s];\n" % (indent, indent * 2, rows, indent)


def update_gsc(path, new):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    block = gsc_block(text)
    if block is None:
        raise SystemExit("%s has no '%s' ... '%s' block" % (path, GSC_BEGIN, GSC_END))
    start, end, existing = block
    entries = merge_catalog(existing, new)
    indent = re.match(r"[ \t]*", text[text.rindex("\n", 0, text.find(GSC_BEGIN)) + 1:]).group(0)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text[:start] + render_gsc(entries, indent or "    ") + text[end:])
    return entries


def read_lines(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [line.rstrip("\r\n") for line in f]


def assemble(mod_zone, csv_path, bank, zone, ports, gsc=None):
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
    catalog_path = os.path.join(mod_zone, "catalog.txt")
    full = merge_catalog([c for c in read_lines(catalog_path) if c], catalog)
    if gsc:
        full = update_gsc(gsc, full)
    with open(catalog_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("".join(c + "\n" for c in full))
    return {"added_lines": added, "bank_aliases": bank_def["aliases"], "catalog": full}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mod-zone", required=True, help="ZoneTool asset root of the mod zone (zonetool/<zone>)")
    ap.add_argument("--csv", required=True, help="the mod zone's zone_source CSV")
    ap.add_argument("--bank", required=True, help="the mod zone's sound bank name (e.g. bo3wpn.all)")
    ap.add_argument("--zone", required=True, help="mod zone name")
    ap.add_argument("--port", action="append", required=True, help="t7_port_weapon.py output folder")
    ap.add_argument("--gsc", help="server module whose generated catalog block to rewrite")
    args = ap.parse_args(argv)
    print(json.dumps(assemble(args.mod_zone, args.csv, args.bank, args.zone, args.port, args.gsc), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

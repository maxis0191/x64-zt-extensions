"""Merge t7_port_weapon.py outputs into one IW7 mod zone, stdlib only.

Each port writes its own ZoneTool asset tree (``<port>/zone``), its zone lines
(``zone.csv``) and its module catalog entry (``catalog.txt``). A mod is one
zone: this copies every port's assets into the mod zone source, appends the
lines the zone CSV lacks, and lists every weapon's alias table in the mod's
single sound bank (``soundbank/<bank>.json``; ZoneTool then writes one
mod.sabl/mod.sabs). The per-weapon bank JSONs are not copied.

The server module reads two generated lists, kept in the mod zone root and,
with ``--gsc``, rewritten in the module between
``// BEGIN t7_mod_assemble <block>`` and ``// END t7_mod_assemble <block>``
(entries already there, such as hand-built weapons, are kept):

  catalog     probe alias=weapon[:pap weapon:pap1 attachment:pap2 attachment] (catalog.txt)
  behaviours  weapon|BO3 script namespace|tuning|effects|sounds (behaviour.txt)

    python t7_mod_assemble.py --mod-zone zonetool/bo3wpn --csv zone_source/bo3wpn.csv
        --bank bo3wpn.all --zone bo3wpn --port port/thundergun_zm [--port ...] [--gsc paris_bo3wpn.gsc]
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


GSC_ENTRY = re.compile(r'"([^"]+)"')
# generated GSC blocks: name -> key of an entry (a new entry replaces the one with the same key)
BLOCK_KEYS = {
    "catalog": lambda e: e.split("=", 1)[-1].split(":")[0],  # probe alias=weapon[:pap weapon:pap1:pap2]
    "behaviours": lambda e: "|".join(e.split("|")[:2]),      # weapon|namespace|tuning|effects|sounds
}


def gsc_markers(block):
    return "// BEGIN t7_mod_assemble " + block, "// END t7_mod_assemble " + block


def merge_entries(existing, new, block="catalog"):
    """Entries keyed per block; a new entry replaces the old one in place."""
    key = BLOCK_KEYS[block]
    out = {}
    for entry in list(existing) + list(new):
        out[key(entry)] = entry
    return list(out.values())


def merge_catalog(existing, new):
    """Merged catalog; two weapons sharing a raw name (iw7_<raw>_...) are refused: retail keys level.pap
    and the magic wheel by it, so the later one silently replaced the other's Pack-a-Punch."""
    merged = merge_entries(existing, new, "catalog")
    seen = {}
    for entry in merged:
        weapon = BLOCK_KEYS["catalog"](entry)
        raw = weapon.split("_")[1] if weapon.startswith("iw7_") and weapon.count("_") >= 1 else weapon
        if raw in seen:
            raise SystemExit("catalog weapons %s and %s share the raw name %r" % (seen[raw], weapon, raw))
        seen[raw] = weapon
    return merged


def gsc_block(text, block="catalog"):
    """(start, end, entries) of a generated block, or None."""
    begin_marker, end_marker = gsc_markers(block)
    begin, end = text.find(begin_marker), text.find(end_marker)
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


def update_gsc(path, new, block="catalog"):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    found = gsc_block(text, block)
    if found is None:
        raise SystemExit("%s has no '%s' ... '%s' block" % ((path,) + gsc_markers(block)))
    start, end, existing = found
    entries = merge_catalog(existing, new) if block == "catalog" else merge_entries(existing, new, block)
    begin = text.find(gsc_markers(block)[0])
    indent = re.match(r"[ \t]*", text[text.rindex("\n", 0, begin) + 1:]).group(0)
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
    added, catalog, behaviours = [], [], []
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
        behaviours += [b for b in read_lines(os.path.join(port, "behaviour.txt")) if b]
    if bank_def["aliases"] and "soundbank," + bank not in present:
        lines.append("soundbank," + bank)
        added.append("soundbank," + bank)
    os.makedirs(os.path.dirname(bank_path), exist_ok=True)
    with open(bank_path, "w", encoding="utf-8") as f:
        json.dump(bank_def, f, indent=1)
    with open(csv_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    out = {"added_lines": added, "bank_aliases": bank_def["aliases"]}
    for block, new in (("catalog", catalog), ("behaviours", behaviours)):
        path = os.path.join(mod_zone, block + ".txt")
        full = merge_entries([c for c in read_lines(path) if c], new, block)
        if gsc:
            full = update_gsc(gsc, full, block)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("".join(c + "\n" for c in full))
        out[block] = full
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mod-zone", required=True, help="ZoneTool asset root of the mod zone (zonetool/<zone>)")
    ap.add_argument("--csv", required=True, help="the mod zone's zone_source CSV")
    ap.add_argument("--bank", required=True, help="the mod zone's sound bank name (e.g. bo3wpn.all)")
    ap.add_argument("--zone", required=True, help="mod zone name")
    ap.add_argument("--port", action="append", required=True, help="t7_port_weapon.py output folder")
    ap.add_argument("--gsc", help="server module whose generated catalog and behaviours blocks to rewrite")
    args = ap.parse_args(argv)
    print(json.dumps(assemble(args.mod_zone, args.csv, args.bank, args.zone, args.port, args.gsc), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

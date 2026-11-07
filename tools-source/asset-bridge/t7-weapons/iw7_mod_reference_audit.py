"""Audit a mod zone's references against every map it loads on (stdlib only).

A mod fastfile is loaded on every Zombies map, but its assets can name stock
assets they do not embed (a weapon's tracer, projectile model, generic
animations, techsets, images). A name that only one map's zone carries
works on that map and breaks the others: the BO3 Ray Gun inherited the
zapper template's tracer "shredder_bullet", a Spaceland asset, and the client
faulted holding it on Rave in the Redwoods.

This collects every asset-like string in the mod zone's ZoneTool sources and
reports those that are neither the mod's own assets, nor in the zones every
map loads (--common: ZoneTool zone csvs or "type,name" lists), nor in every
listed map zone (--map). A map can name several lists separated by ";": its
level zone and its techsets zone (techsets_cp_zmb holds the weapon glass and
effect techniques Spaceland alone loads; a level-zone-only audit missed them).
Exit 1 when such references exist.

    python iw7_mod_reference_audit.py <zonetool/<zone>> --common <csv> [...]
        --map "cp_zmb=<cp_zmb csv>;<techsets_cp_zmb csv>" --map "cp_rave=<cp_rave csv>;<techsets_cp_rave csv>"
"""
import argparse
import glob
import json
import os
import re
import sys

NAME = re.compile(r"[\w/$.#-]+")


def csv_names(path):
    """Asset names of a ZoneTool zone csv or reference list (type,name lines)."""
    out = set()
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            parts = line.split(",")
            if len(parts) >= 2:
                out.add(parts[-1].lstrip(","))
    return out


def own_assets(zone_dir):
    return {os.path.splitext(os.path.basename(p))[0]
            for p in glob.glob(os.path.join(zone_dir, "**", "*"), recursive=True) if os.path.isfile(p)}


def references(zone_dir):
    """{name: set of asset folders whose JSON names it}."""
    refs = {}
    for path in glob.glob(os.path.join(zone_dir, "**", "*.json"), recursive=True):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            continue
        folder = os.path.relpath(path, zone_dir).split(os.sep)[0]
        stack = [data]
        while stack:
            o = stack.pop()
            if isinstance(o, dict):
                stack.extend(o.values())
            elif isinstance(o, list):
                stack.extend(o)
            elif isinstance(o, str) and 0 < len(o) < 120 and NAME.fullmatch(o):
                refs.setdefault(o, set()).add(folder)
    return refs


def audit(refs, own, common, maps):
    """References some listed map lacks: {name: {"in": maps having it, "missing": maps lacking it}}."""
    out = {}
    for name, folders in refs.items():
        if name in own or name in common:
            continue
        having = sorted(m for m, names in maps.items() if name in names)
        if not having:
            continue      # a plain string (alias, notetrack, tag), not a map asset
        missing = sorted(m for m in maps if m not in having)
        if missing:
            out[name] = {"in": having, "missing": missing, "used_by": sorted(folders)}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("zone_dir")
    ap.add_argument("--common", action="append", default=[], help="zone csv every map loads")
    ap.add_argument("--map", action="append", default=[], metavar="NAME=CSV", help="a map zone csv")
    args = ap.parse_args(argv)
    common = set()
    for path in args.common:
        common |= csv_names(path)
    maps = {}
    for item in args.map:
        name, _, paths = item.partition("=")
        maps[name] = set()
        for path in paths.split(";"):
            maps[name] |= csv_names(path)
    if len(maps) < 2:
        raise SystemExit("list at least two map zones (--map name=csv)")
    found = audit(references(args.zone_dir), own_assets(args.zone_dir), common, maps)
    print(json.dumps({"maps": sorted(maps), "map_only_references": found}, indent=1))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())

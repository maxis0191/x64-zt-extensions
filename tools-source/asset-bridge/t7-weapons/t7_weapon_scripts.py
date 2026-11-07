"""Find and read the BO3 (T7) scripts behind a weapon's behaviour, stdlib only.

A Wonder Weapon's behaviour lives in script, not in its WeaponDef (the
Thundergun's blast, the DG-2's chain lightning, view-model effects played by
client script). The port exports every script of the weapon's zone with
GrayWolf (compiled ``.gscc``/``.cscc``), decompiles them with xensik
gsc-tool (``-g t7``; server and ``-i client``), then keeps:

* the scripts that call ``getweapon( "<base>" )`` for the weapon or its
  upgrade (``base`` is the variant name at WeaponVariantDef +0x8);
* the zone scripts those ``#using`` (the DG-2 pulls _zm_lightning_chain).

From each it reads its ``#namespace`` (the behaviour family the IW7 module
implements once, e.g. zm_weap_thundergun), the tuning
(``set_zombie_var( "name", value )``), the effects it plays
(``level._effect[key] = "path"``), the sound aliases it plays and the weapons
it names.
The decompiled sources are the reference for the IW7 behaviour module.

    python t7_weapon_scripts.py --decompiled <dir> --base thundergun [--base thundergun_upgraded]
"""
import argparse
import json
import os
import re
import sys

GETWEAPON = re.compile(r'getweapon\(\s*"([a-z0-9_]+)"\s*\)')
USING = re.compile(r'^#using\s+([\w\\/]+);', re.M)
ZOMBIE_VAR = re.compile(r'set_zombie_var\(\s*"([a-z0-9_]+)"\s*,\s*(-?[0-9.]+)')
EFFECT = re.compile(r'level\._effect\[\s*"([a-z0-9_]+)"\s*\]\s*=\s*"([a-z0-9_/]+)"')
NAMESPACE = re.compile(r'^#namespace\s+([a-z0-9_]+);', re.M)
# literal aliases the script plays (world sounds: blast hits, arcs, idle loops); an alias can also be
# passed as a parameter (the DG-2 arc sound), so every literal is kept for matching against the alias table
SOUND = re.compile(r'\b(?:playsound|playsoundatposition|playloopsound|playsoundtoplayer)\(\s*"([a-z0-9_]+)"')
LITERAL = re.compile(r'"([a-z0-9_]+)"')


def number(text):
    return float(text) if "." in text else int(text)


def module_key(path):
    """'scripts\\zm\\_zm_lightning_chain' and 'scripts/zm/_zm_lightning_chain.gsc' -> same key."""
    return os.path.splitext(path.replace("\\", "/"))[0].lower()


def select(sources, bases):
    """Script paths (sorted) that name one of the weapon bases, plus the zone scripts they #using."""
    picked = {p for p, text in sources.items() if set(GETWEAPON.findall(text)) & set(bases)}
    todo = list(picked)
    while todo:
        for using in USING.findall(sources[todo.pop()]):
            # a module may exist as both .gsc and .csc: take every variant present in the zone
            for p in sources:
                if module_key(p) == module_key(using) and p not in picked:
                    picked.add(p)
                    todo.append(p)
    return sorted(picked)


def extract(text):
    ns = NAMESPACE.search(text)
    return {
        "namespace": ns.group(1) if ns else None,
        "zombie_vars": {name: number(value) for name, value in ZOMBIE_VAR.findall(text)},
        "effects": dict(EFFECT.findall(text)),
        "sounds": list(dict.fromkeys(SOUND.findall(text))),
        "literals": sorted(set(LITERAL.findall(text))),
        "weapons": list(dict.fromkeys(GETWEAPON.findall(text))),
    }


def load_sources(root):
    sources = {}
    for folder, _, files in os.walk(root):
        for name in files:
            if name.endswith((".gsc", ".csc", ".gscc", ".cscc")):
                path = os.path.join(folder, name)
                with open(path, encoding="utf-8", errors="replace") as f:
                    rel = os.path.relpath(path, root).replace("\\", "/")
                    # gsc-tool keeps the input extension (.gscc/.cscc): name them as the game does
                    rel = re.sub(r"\.(gsc|csc)c$", r".\1", rel)
                    sources[rel] = f.read()
    return sources


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--decompiled", required=True, help="gsc-tool output folder (decompiled/t7)")
    ap.add_argument("--base", action="append", required=True, help="weapon base name (repeat for the upgrade)")
    args = ap.parse_args(argv)
    sources = load_sources(args.decompiled)
    out = {p: extract(sources[p]) for p in select(sources, args.base)}
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

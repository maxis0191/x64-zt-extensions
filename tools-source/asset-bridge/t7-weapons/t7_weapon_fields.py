"""Infer BO3 (T7) weapon definition fields from a t7_weapon_scan.py capture.

BO3's WeaponDef layout is not public. Every weapon asset shares one layout, so
a field is the same (block path, offset) across weapons. This tool:

* flattens each weapon's annotated block tree into (path, offset) slots;
* reports, per slot, the referenced assets/strings for every weapon (anim
  tables, models, FX, sounds are then self-describing by asset name);
* locates numeric fields by matching known values across several weapons
  (``--known clip=ray_gun_zm:20,thundergun_zm:2``): only offsets whose int32
  (or float32) equals every listed value are reported, so each extra weapon
  shrinks the candidate set. Nothing is guessed; ambiguous results stay
  ambiguous and are reported as such.
"""
import argparse
import json
import struct
import sys
from collections import defaultdict


def flatten(block, path="root", out=None):
    """Yield (path, block) for a block and all nested children."""
    if out is None:
        out = []
    out.append((path, block))
    for off, child in sorted(block.get("children", {}).items(), key=lambda kv: int(kv[0])):
        flatten(child, "%s/%s" % (path, off), out)
    return out


def blocks_by_path(weapon_block):
    return {path: block for path, block in flatten(weapon_block)}


def read_scalar(block, off, kind):
    raw = bytes.fromhex(block["hex"])
    size = 4
    if off + size > len(raw):
        return None
    if kind == "i32":
        return struct.unpack_from("<i", raw, off)[0]
    if kind == "u16":
        return struct.unpack_from("<H", raw, off)[0]
    if kind == "u8":
        return raw[off]
    if kind == "f32":
        value = struct.unpack_from("<f", raw, off)[0]
        return round(value, 4)
    raise ValueError(kind)


def find_numeric(scan, known, kinds=("i32", "f32"), tolerance=1e-3):
    """known: {weapon: value}. Returns [(path, off, kind)] matching every weapon."""
    weapons = scan["weapons"]
    missing = [w for w in known if w not in weapons]
    if missing:
        raise SystemExit("weapons not in scan: %s" % ", ".join(missing))
    per_weapon = {w: blocks_by_path(weapons[w]) for w in known}
    common_paths = set.intersection(*(set(b) for b in per_weapon.values()))
    hits = []
    for path in sorted(common_paths):
        size = min(per_weapon[w][path]["size"] for w in known)
        step = 4
        for off in range(0, size - 3, step):
            for kind in kinds:
                ok = True
                for w, expected in known.items():
                    got = read_scalar(per_weapon[w][path], off, kind)
                    if got is None:
                        ok = False
                        break
                    if kind == "f32":
                        if abs(got - float(expected)) > tolerance * max(1.0, abs(float(expected))):
                            ok = False
                            break
                    elif got != int(expected):
                        ok = False
                        break
                if ok:
                    hits.append((path, off, kind))
    return hits


def ref_table(scan, weapons=None, kinds=("asset", "string")):
    """{(path, off): {weapon: 'type:name' or '"string"'}} for annotated slots."""
    table = defaultdict(dict)
    for w, block in scan["weapons"].items():
        if weapons and w not in weapons:
            continue
        for path, b in flatten(block):
            for ref in b["refs"]:
                if ref["kind"] not in kinds:
                    continue
                label = ("%s:%s" % (ref["type"], ref["name"]) if ref["kind"] == "asset"
                         else '"%s"' % ref["value"])
                table[(path, ref["off"])][w] = label
    return table


def parse_known(text):
    known = {}
    for item in text.split(","):
        weapon, value = item.rsplit(":", 1)
        known[weapon.strip()] = float(value) if "." in value else int(value)
    return known


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("scan")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("refs", help="annotated reference slots")
    r.add_argument("--weapon", nargs="*")
    r.add_argument("--type", help="only this asset type name (e.g. xanim)")
    n = sub.add_parser("numeric", help="locate fields by known values")
    n.add_argument("--known", action="append", required=True,
                   help="name=weapon:value,weapon:value (repeatable)")
    n.add_argument("--kinds", default="i32,f32")
    args = ap.parse_args()

    with open(args.scan, encoding="utf-8") as f:
        scan = json.load(f)
    if args.cmd == "refs":
        table = ref_table(scan, set(args.weapon) if args.weapon else None)
        for (path, off), per in sorted(table.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            if args.type and not any(v.startswith(args.type + ":") for v in per.values()):
                continue
            print("%s+0x%x\t%s" % (path, off, json.dumps(per, sort_keys=True)))
    else:
        result = {}
        for spec in args.known:
            field, values = spec.split("=", 1)
            hits = find_numeric(scan, parse_known(values), tuple(args.kinds.split(",")))
            result[field] = [{"path": p, "off": "0x%x" % o, "kind": k} for p, o, k in hits]
        print(json.dumps(result, indent=1))


if __name__ == "__main__":
    sys.exit(main())

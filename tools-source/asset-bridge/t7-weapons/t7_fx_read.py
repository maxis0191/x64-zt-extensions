"""Read BO3 (T7) effects (FxEffectDef) resident in a ZoneTool T7 process to JSON.

ZoneTool (owner fork) runs with ``-assetlog <file> -holdzone <zone> <release>``.
This tool reads the effect headers that log lists and their element arrays,
read-only, and writes the fields established so far plus every element's raw
bytes, so that an IW7 particle-system converter can be built on top of them.

Layout established on all 582 effects / 5809 elements of zm_levelcommon
(BO2's FxEffectDef/FxElemDef order, 64-bit, extended):

  FxEffectDef (0x90)
    0x00 name            0x08 u16 flags
    0x0c i16 looping, 0x0e i16 one-shot, 0x10 i16 emission element counts
    0x14 i32 totalSize   0x18 i32 msecLoopingLife, 0x1c i32 msecNonLoopingLife
    0x20 elements        0x28 6 floats: bounding box dims, centre
  FxElemDef (0x260; totalSize always >= count * 0x260)
    0x00 u32 flags       0xc8 u8 element type
    0xf0 visual: material (types 0-6), xmodel (7), light description (8),
         effect (14); a pointer to a visual array when there are several
    0x130 second material (the "|dup" variant the engine draws)
    0x198/0x1a0/0x1a8/0x1d0 effects (impact, death, emitted...); 0x1e8 light
         description or klf
  Element types (by the visual kind they carry): 0-6 sprites/tails/trails
  (5 = geometry trail), 7 model, 8 omni light, 12 klf, 13 array, 14 runner.

Nothing is written to the target process. GPL-3.0-or-later (ZoneTool lineage).
"""
import argparse
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from t7_weapon_scan import Process  # noqa: E402

HEADER_SIZE = 0x90
ELEM_SIZE = 0x260
FX_TYPE_NAME = "fx"
ELEM_TYPES = {0: "sprite", 1: "sprite", 2: "sprite", 3: "tail", 4: "sprite", 5: "trail", 6: "sprite",
              7: "model", 8: "omni_light", 12: "klf", 13: "array", 14: "runner"}
VISUAL_SLOTS = {"visual": 0xF0, "visual_dup": 0x130}
EFFECT_SLOTS = {"effect_198": 0x198, "effect_1a0": 0x1A0, "effect_1a8": 0x1A8, "effect_1d0": 0x1D0}
LIGHT_SLOT = 0x1E8


def load_asset_log(path):
    assets, effects = {}, {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 4:
                continue
            _, type_name, name, addr = parts
            name = name.lstrip(",")
            address = int(addr, 16)
            assets[address] = (type_name, name)
            if type_name == FX_TYPE_NAME:
                effects[name] = address
    return assets, effects


def parse_header(raw):
    if len(raw) < HEADER_SIZE:
        raise ValueError("short effect header")
    looping, one_shot, emission = struct.unpack_from("<hhh", raw, 0x0C)
    return {
        "flags": struct.unpack_from("<H", raw, 0x08)[0],
        "looping": looping, "one_shot": one_shot, "emission": emission,
        "total_size": struct.unpack_from("<i", raw, 0x14)[0],
        "msec_looping_life": struct.unpack_from("<i", raw, 0x18)[0],
        "msec_non_looping_life": struct.unpack_from("<i", raw, 0x1C)[0],
        "elements_ptr": struct.unpack_from("<Q", raw, 0x20)[0],
        "bounds": [round(v, 4) for v in struct.unpack_from("<6f", raw, 0x28)],
    }


def ref(assets, value):
    if value in assets:
        kind, name = assets[value]
        return {"kind": kind, "name": name}
    return None


def parse_element(raw, assets):
    if len(raw) != ELEM_SIZE:
        raise ValueError("element must be 0x%x bytes" % ELEM_SIZE)
    etype = raw[0xC8]
    out = {"type": etype, "type_name": ELEM_TYPES.get(etype, "unknown"),
           "flags": struct.unpack_from("<I", raw, 0)[0], "type_bytes": list(raw[0xC8:0xD0])}
    for key, off in list(VISUAL_SLOTS.items()) + list(EFFECT_SLOTS.items()) + [("light", LIGHT_SLOT)]:
        value = struct.unpack_from("<Q", raw, off)[0]
        r = ref(assets, value)
        if r:
            out[key] = r
        elif key == "visual" and value:
            out["visual_array_ptr"] = value
    out["raw"] = raw.hex()
    return out


def read_effect(proc, assets, address):
    head = parse_header(proc.read(address, HEADER_SIZE))
    count = head["looping"] + head["one_shot"] + head["emission"]
    if count < 0 or count * ELEM_SIZE > head["total_size"]:
        raise ValueError("element count %d does not fit totalSize %d" % (count, head["total_size"]))
    raw = proc.read(head.pop("elements_ptr"), count * ELEM_SIZE)
    head["elements"] = [parse_element(raw[i * ELEM_SIZE:(i + 1) * ELEM_SIZE], assets) for i in range(count)]
    return head


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--assetlog", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", nargs="*", help="effect names (default: all)")
    ap.add_argument("--follow", action="store_true", help="also read effects the chosen ones reference")
    args = ap.parse_args(argv)
    assets, effects = load_asset_log(args.assetlog)
    wanted = list(args.only or effects)
    proc = Process(args.pid)
    out = {"schema": "t7.fx-read/1", "effects": {}}
    while wanted:
        name = wanted.pop(0)
        if name in out["effects"]:
            continue
        if name not in effects:
            raise SystemExit("effect %s is not in the asset log" % name)
        fx = read_effect(proc, assets, effects[name])
        out["effects"][name] = fx
        if args.follow:
            for e in fx["elements"]:
                for key in list(EFFECT_SLOTS) + ["visual"]:
                    r = e.get(key)
                    if r and r["kind"] == FX_TYPE_NAME:
                        wanted.append(r["name"])
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({"effects": len(out["effects"]),
                      "elements": sum(len(e["elements"]) for e in out["effects"].values()), "out": args.out}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

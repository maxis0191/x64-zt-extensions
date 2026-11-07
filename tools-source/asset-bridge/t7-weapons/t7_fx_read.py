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
    0xc9 visual count, 0xca velocity interval count, 0xcd visual-state
    interval count (samples = intervals + 1)
    0xd0 velocity samples, 0x60 each: local velocity, local total delta, world
         velocity, world total delta; each 3 floats base + 3 floats amplitude
    0xe0 visual-state samples, 0x50 each: base then amplitude, 10 dwords:
         colour RGBA bytes, rotation delta, rotation total, size[2], scale,
         4 more (unnamed, kept)
    Scalars (dword index, BO2 order; spawn and life confirmed on the Ray Gun):
    1 flags2, 2-3 spawn (looping: interval ms, count; one-shot: count base,
    amplitude), 7-14 integers (fade/delay ranges, unconfirmed), 15-16 lifespan ms
    (int) base/amplitude,
    17-22 spawn origin x/y/z base/amplitude, 48 atlas bytes.
  Sample arrays that are not inside the effect block are shared (deduplicated)
  arrays; the counts above still apply.

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


def range_pairs(values):
    return [{"base": values[i], "amplitude": values[i + 1]} for i in range(0, len(values), 2)]


def parse_scalars(raw):
    f = struct.unpack_from("<50f", raw, 0)
    i = struct.unpack_from("<50i", raw, 0)
    return {
        "flags2": i[1],
        "spawn": {"a": i[2], "b": i[3]},
        "ints_7_14": list(i[7:15]),
        # camera distance band where the element spawns (BO3 distance LOD tiers), 0..0 unbounded
        "spawn_range": {"min": f[6], "max": f[7]},
        "cull_radius": f[12],
        "spawn_delay_msec": {"base": i[13], "amplitude": i[14]},
        "lifespan_msec": {"base": i[15], "amplitude": i[16]},
        "spawn_origin": range_pairs(list(f[17:23])),
        "atlas": list(raw[48 * 4:49 * 4 + 4]),
    }


def parse_vel_sample(raw):
    v = struct.unpack_from("<24f", raw, 0)
    vec = lambda k: {"base": list(v[k:k + 3]), "amplitude": list(v[k + 3:k + 6])}  # noqa: E731
    return {"local_velocity": vec(0), "local_total_delta": vec(6), "world_velocity": vec(12), "world_total_delta": vec(18)}


def parse_visual_state(raw):
    f = struct.unpack_from("<10f", raw, 0)
    return {"color": list(raw[0:4]), "rotation_delta": f[1], "rotation_total": f[2], "size": [f[3], f[4]],
            "scale": f[5], "extra": list(f[6:10])}


def parse_vis_sample(raw):
    return {"base": parse_visual_state(raw[0:0x28]), "amplitude": parse_visual_state(raw[0x28:0x50])}


VEL_SAMPLE_SIZE = 0x60
VIS_SAMPLE_SIZE = 0x50


def read_samples(proc, raw_elem):
    out = {}
    for key, ptr_off, count_off, size, parse in (("vel_samples", 0xD0, 0xCA, VEL_SAMPLE_SIZE, parse_vel_sample),
                                                  ("vis_samples", 0xE0, 0xCD, VIS_SAMPLE_SIZE, parse_vis_sample)):
        ptr = struct.unpack_from("<Q", raw_elem, ptr_off)[0]
        count = raw_elem[count_off] + 1
        if not ptr or not proc.readable(ptr, count * size):
            continue
        blob = proc.read(ptr, count * size)
        out[key] = [parse(blob[k * size:(k + 1) * size]) for k in range(count)]
    return out


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
    out["counts"] = {"visual": raw[0xC9], "vel_intervals": raw[0xCA], "vis_intervals": raw[0xCD]}
    out["scalars"] = parse_scalars(raw)
    out["raw"] = raw.hex()
    return out


def read_visuals(proc, element, assets):
    """An element with several visuals (counts.visual > 1: one picked per particle) points at an array
    of visual pointers; resolve it into ``visuals`` and keep the first as ``visual``."""
    ptr, count = element.get("visual_array_ptr"), element["counts"]["visual"]
    if not ptr or count < 2 or not proc.readable(ptr, count * 8):
        return
    blob = proc.read(ptr, count * 8)
    visuals = [ref(assets, struct.unpack_from("<Q", blob, i * 8)[0]) for i in range(count)]
    visuals = [v for v in visuals if v]
    if visuals:
        element["visuals"] = visuals
        element["visual"] = visuals[0]


def read_effect(proc, assets, address):
    head = parse_header(proc.read(address, HEADER_SIZE))
    count = head["looping"] + head["one_shot"] + head["emission"]
    if count < 0 or count * ELEM_SIZE > head["total_size"]:
        raise ValueError("element count %d does not fit totalSize %d" % (count, head["total_size"]))
    raw = proc.read(head.pop("elements_ptr"), count * ELEM_SIZE)
    elements = []
    for i in range(count):
        chunk = raw[i * ELEM_SIZE:(i + 1) * ELEM_SIZE]
        e = parse_element(chunk, assets)
        e["spawn_kind"] = "looping" if i < head["looping"] else ("one_shot" if i < head["looping"] + head["one_shot"] else "emission")
        e.update(read_samples(proc, chunk))
        read_visuals(proc, e, assets)
        elements.append(e)
    head["elements"] = elements
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

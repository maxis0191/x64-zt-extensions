"""Convert BO3 (T7) effects into IW7 particle systems (.iw7VFX), stdlib only.

Input: effects read by t7_fx_read.py, the material map printed by
t7_fx_material_pack.py (BO3 material -> IW7 effect material), and stock IW7
particle systems decoded by iw7_vfx.py that provide one template emitter per
element kind. Each BO3 element becomes one IW7 emitter cloned from the
template of its kind, then rewritten:

* life: particleLife = lifespan ms / 1000 (base, base + amplitude);
* spawn: one-shot -> burst (count base, base + amplitude); a looping element
  with a finite count (BO3: one particle batch every interval ms, count in
  total) -> burst of `count`, particleDelay spread over count * interval; an
  endless looping element (count INT_MAX) -> particleSpawnRate 1000/interval;
* material: INIT_MATERIAL -> the converted IW7 effect material;
* colour: COLOR_GRAPH from the visual-state samples (RGBA / 255 over the
  normalised life, min and max sets equal);
* size: SIZE_GRAPH from the samples; BO3 sizes are radii, IW7 sizes diameters;
* spawn origin: INIT_SPAWN_SHAPE_BOX min/max = base / base + amplitude;
* velocity: INIT_ATTRIBUTES velocity from the first velocity sample (BO3
  units per ms -> units per s);
* atlas: INIT_ATLAS kept for atlas materials, dropped otherwise;
* light: INIT_LIGHT_OMNI keeps the stock light definition; colour and radius
  from the samples.

Elements with no IW7 counterpart here (distortion materials, models,
runners, BO3 types without a template) are reported and skipped.
Intensity (INTENSITY_GRAPH, HDR scale) is a tuning parameter: --intensity.
"""
import argparse
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iw7_vfx as vfx  # noqa: E402

INT_MAX = 2147483647
# T7 element types follow T6: 0 billboard, 1 oriented, 2 rotated, 3 tail, 4 line, 5 trail, 6 cloud,
# 7 model, 8 omni light. A LINE (velocity-aligned streak) maps to the IW7 tail.
LINE_TYPE = 4
KIND_OF_TYPE = {0: "sprite", 1: "sprite", 2: "sprite", 4: "tail", 6: "sprite", 3: "tail", 5: "trail",
                8: "light"}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def emitter_from(path, index):
    model = vfx.decode(open(path, "rb").read()) if path.lower().endswith(".iw7vfx") else load_json(path)
    return copy.deepcopy(model["system"]["emitterDefs"][index])


def modules(emitter):
    for g in emitter["stateDefs"][0]["moduleGroupDefs"]:
        for m in g.get("moduleDefs") or []:
            yield g, m


def find(emitter, type_name):
    for g, m in modules(emitter):
        if m["moduleType"] == "PARTICLE_MODULE_" + type_name:
            return vfx.module_data(m)
    return None


def drop(emitter, type_name):
    for g in emitter["stateDefs"][0]["moduleGroupDefs"]:
        if g.get("moduleDefs"):
            g["moduleDefs"] = [m for m in g["moduleDefs"] if m["moduleType"] != "PARTICLE_MODULE_" + type_name]


def times(n):
    return [0.0] if n <= 1 else [i / (n - 1) for i in range(n)]


def curve(pairs, scale):
    if len(pairs) == 1:
        pairs = [pairs[0], (1.0, pairs[0][1])]
    return {"controlPoints": vfx.new_curve_points(pairs), "numControlPoints": len(pairs), "scale": vfx.f32(scale)}


def set_curves(data, curves):
    for i, c in enumerate(curves):
        target = data["m_curves"][i]
        target["controlPoints"] = c["controlPoints"]
        target["numControlPoints"] = c["numControlPoints"]
        target["scale"] = c["scale"]
        target["controlPoints@ptr"] = "0x0"   # new data: encode() assigns a fresh pointer


def colour_curves(samples):
    t = times(len(samples))
    channels = [[(t[i], s["base"]["color"][c] / 255.0) for i, s in enumerate(samples)] for c in range(4)]
    return [curve(ch, 1.0) for ch in channels] * 2


def size_curves(samples, radius_to_size=2.0, line=False):
    """x, y, z size curves (min then max). A BO3 LINE keeps its width in size[0] and its full
    length in size[1]: the IW7 tail gets the width as a diameter, the length as is, no depth."""
    t = times(len(samples))
    out = []
    axes = [(0, radius_to_size), (1, 1.0), (None, 0.0)] if line else [(0, radius_to_size), (1, radius_to_size), (1, radius_to_size)]
    for axis, factor in axes:
        values = [0.0 if axis is None else max(0.0, s["base"]["size"][axis]) * factor for s in samples]
        scale = max(values) or 1.0
        out.append(curve([(t[i], v / scale) for i, v in enumerate(values)], scale))
    return out * 2


def rewrite(emitter, element, fx, material, intensity):
    sc = element["scalars"]
    life = sc["lifespan_msec"]
    emitter["particleLife"] = {"min": vfx.f32(life["base"] / 1000.0),
                               "max": vfx.f32((life["base"] + max(0, life["amplitude"])) / 1000.0)}
    rng = sc.get("spawn_range")
    if rng and rng["max"] > 0:
        # BO3 repeats elements per camera distance tier; IW7 keeps the band squared.
        emitter["spawnRangeSq"] = {"min": vfx.f32(rng["min"] ** 2), "max": vfx.f32(rng["max"] ** 2)}
    delay = sc.get("spawn_delay_msec")
    if delay:
        emitter["emitterDelay"] = {"min": vfx.f32(delay["base"] / 1000.0),
                                   "max": vfx.f32((delay["base"] + max(0, delay["amplitude"])) / 1000.0)}
    a, b = sc["spawn"]["a"], sc["spawn"]["b"]
    if element["spawn_kind"] == "looping" and b >= INT_MAX:
        emitter["particleSpawnRate"] = {"min": vfx.f32(1000.0 / max(1, a)), "max": vfx.f32(1000.0 / max(1, a))}
        emitter["particleBurstCount"] = {"min": 1, "max": 1}
        emitter["particleDelay"] = {"min": 0.0, "max": 0.0}
        emitter["particleCountMax"] = max(emitter["particleCountMax"], int(life["base"] + life["amplitude"]) // max(1, a) + 2)
    elif element["spawn_kind"] == "looping":
        emitter["particleBurstCount"] = {"min": b, "max": b}
        emitter["particleDelay"] = {"min": 0.0, "max": vfx.f32(a * max(0, b - 1) / 1000.0)}
        emitter["particleCountMax"] = max(1, b)
    else:
        emitter["particleBurstCount"] = {"min": max(1, a), "max": max(1, a + b)}
        emitter["particleDelay"] = {"min": 0.0, "max": 0.0}
        emitter["particleCountMax"] = max(1, a + b)
    if material:
        mat = find(emitter, "INIT_MATERIAL")
        if mat is not None:
            mat["m_linkedAssetList"]["assetList"] = [vfx.new_linked_asset("PARTICLE_MODULE_INIT_MATERIAL", material=material["iw7"])]
            mat["m_linkedAssetList"]["numAssets"] = 1
            mat["m_linkedAssetList"]["assetList@ptr"] = "0x0"
        if material["atlas"][0] * material["atlas"][1] <= 1:
            drop(emitter, "INIT_ATLAS")
    samples = element.get("vis_samples") or []
    if samples:
        cg = find(emitter, "COLOR_GRAPH")
        if cg is not None:
            set_curves(cg, colour_curves(samples))
            cg["m_flags"] = 0
        sg = find(emitter, "SIZE_GRAPH")
        if sg is not None:
            set_curves(sg, size_curves(samples, line=element["type"] == LINE_TYPE))
            sg["m_flags"] = 0
    ig = find(emitter, "INTENSITY_GRAPH")
    if ig is not None:
        set_curves(ig, [curve([(0.0, 1.0), (1.0, 1.0)], intensity)] * 2)
        ig["m_flags"] = 0
    box = find(emitter, "INIT_SPAWN_SHAPE_BOX")
    if box is not None:
        o = sc["spawn_origin"]
        box["m_dimensionsMin"] = [vfx.f32(r["base"]) for r in o] + [0.0]
        box["m_dimensionsMax"] = [vfx.f32(r["base"] + r["amplitude"]) for r in o] + [0.0]
    attrs = find(emitter, "INIT_ATTRIBUTES")
    vel = (element.get("vel_samples") or [None])[0]
    if attrs is not None and vel:
        v = vel["local_velocity"]
        lo = [min(x, x + y) * 1000.0 for x, y in zip(v["base"], v["amplitude"])]
        hi = [max(x, x + y) * 1000.0 for x, y in zip(v["base"], v["amplitude"])]
        attrs["m_velocityMin"] = [vfx.f32(x) for x in lo] + [0.0]   # BO3 amplitude may be negative
        attrs["m_velocityMax"] = [vfx.f32(x) for x in hi] + [0.0]
    return emitter


def convert(name, fx, templates, materials, intensity):
    model = vfx.new_model(name)
    report = {"effect": name, "emitters": 0, "skipped": []}
    for i, e in enumerate(fx["elements"]):
        kind = KIND_OF_TYPE.get(e["type"])
        visual = e.get("visual") or {}
        material = None
        if kind in ("sprite", "tail", "trail"):
            material = materials.get(visual.get("name"))
            if material is None:
                report["skipped"].append({"element": i, "reason": "material %s not converted" % visual.get("name")})
                continue
            if material["atlas"][0] * material["atlas"][1] > 1 and kind == "sprite":
                kind = "sprite_atlas"
        if kind is None or kind not in templates:
            report["skipped"].append({"element": i, "reason": "type %s (%s) has no template" % (e["type"], e["type_name"])})
            continue
        emitter = rewrite(copy.deepcopy(templates[kind]), e, fx, material, intensity.get(material["mode"] if material else "light", 1.0))
        model["system"]["emitterDefs"].append(emitter)
        report["emitters"] += 1
    model["system"]["numEmitters"] = len(model["system"]["emitterDefs"])
    model["system"]["flags"] = vfx.system_flags(model)
    return model, report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--effects", required=True, help="t7_fx_read.py JSON")
    ap.add_argument("--materials", required=True, help="t7_fx_material_pack.py report JSON")
    ap.add_argument("--template", action="append", default=[], required=True,
                    help="KIND=PATH:INDEX, KIND in sprite, sprite_atlas, tail, trail, light; PATH a stock .iw7VFX")
    ap.add_argument("--map", action="append", default=[], required=True,
                    help="BO3_EFFECT=IW7_NAME (e.g. zombie/fx_raygun_1p_zmb=vfx/bo3wpn/raygun/fx_raygun_1p)")
    ap.add_argument("--out", required=True, help="ZoneTool IW7 asset root (writes particlesystem/<name>.iw7VFX)")
    ap.add_argument("--intensity-add", type=float, default=20.0)
    ap.add_argument("--intensity-blend", type=float, default=1.0)
    ap.add_argument("--intensity-light", type=float, default=1.0)
    args = ap.parse_args(argv)
    effects = load_json(args.effects)["effects"]
    materials = {m["bo3"]: m for m in load_json(args.materials)["materials"]}
    templates = {}
    for spec in args.template:
        kind, rest = spec.split("=", 1)
        path, index = rest.rsplit(":", 1)
        templates[kind] = emitter_from(path, int(index))
    intensity = {"add": args.intensity_add, "blend": args.intensity_blend, "light": args.intensity_light}
    reports = []
    for spec in args.map:
        bo3, iw7 = spec.split("=", 1)
        if bo3 not in effects:
            raise SystemExit("effect %s not in %s" % (bo3, args.effects))
        model, report = convert(iw7, effects[bo3], templates, materials, intensity)
        if not report["emitters"]:
            # reported, not written: the port references only the effects that were built
            report["not_built"] = True
            reports.append(report)
            continue
        data = vfx.encode(model)
        check = vfx.decode(data)
        if len(check["system"]["emitterDefs"]) != report["emitters"]:
            raise SystemExit("%s: encoded emitter count differs" % iw7)
        path = os.path.join(args.out, "particlesystem", *iw7.split("/")) + ".iw7VFX"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        report["bytes"] = len(data)
        reports.append(report)
    print(json.dumps(reports, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

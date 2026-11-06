"""Convert BO3 (T7) particle materials into IW7 effect materials (ZoneTool sources).

Input: GrayWolf material JSON exports of BO3 effect materials (``ei/*.json``,
``el/*.json`` with their ``images/*.png``) and the effects that use them, as
read by t7_fx_read.py (each sprite element gives its material's texture
atlas: columns = 1 << atlas byte 0, rows = 1 << atlas byte 1).

Output (a ZoneTool IW7 asset root): ``materials/<prefix>/<name>.json`` from a
stock IW7 effect material template and ``images/<name>_c.dds`` (BC7_UNORM, the
BO3 colour map with its alpha). Templates (stock, loaded by cp_zmb):
  additive      eq_effectunlit_add_lin_ndw_nocast_evc        (eq/gfx_flare_wtr)
  blend         eq_effectunlit_blend_lin_ndw_nocast_evc      (eq/vfx_pyro_flash_ark_green_p)
  additive atlas eq_effectunlit_zfeather_add_tab_lin_ndw_nocast_evc
  blend atlas   eq_effectunlit_zfeather_blend_tab_lin_ndw_nocast_evc
"_evc" techniques take the particle colour from the emitter, as BO3's do.
BO3 "emissive" materials become additive except smoke and debris (blend);
distortion materials are reported and skipped (no IW7 counterpart here).
"""
import argparse
import copy
import glob
import json
import os
import re
import subprocess
import sys
import tempfile

ALPHA_BLEND_HINTS = ("smk", "smoke", "debris", "bubble", "dust")


def safe(name):
    return re.sub(r"[^A-Za-z0-9_]", "_", name)


def classify(material_name, techset):
    t = techset.lower()
    if "distortion" in t:
        return "skip"
    base = material_name.split("/")[-1].lower()
    if "emissive" in t and not any(h in base for h in ALPHA_BLEND_HINTS):
        return "add"
    return "blend"


def atlas_of(effects):
    """Material name -> (columns, rows) from the sprite elements that use it."""
    out = {}
    for fx in effects.values():
        for e in fx.get("elements", []):
            visual = e.get("visual")
            atlas = e.get("scalars", {}).get("atlas")
            if not visual or visual.get("kind") != "material" or not atlas or len(atlas) < 2:
                continue
            cols, rows = 1 << atlas[0], 1 << atlas[1]
            prev = out.get(visual["name"])
            if prev and prev != (cols, rows):
                raise SystemExit("material %s used with two atlas layouts %s / %s" % (visual["name"], prev, (cols, rows)))
            out[visual["name"]] = (cols, rows)
    return out


def bind(template, image, cols, rows):
    m = copy.deepcopy(template)
    for t in m["textureTable"]:
        if t["semantic"] == 2:
            t["image"] = image
    m["textureAtlasColumnCount"] = cols
    m["textureAtlasRowCount"] = rows
    for c in m.get("constantTable", []):
        if c.get("name") == "textureAtlas":
            c["literal"][0], c["literal"][1] = float(cols), float(rows)
    return m


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--materials", required=True, help="GrayWolf export root holding materials/ and images/")
    ap.add_argument("--effects", required=True, help="t7_fx_read.py JSON")
    ap.add_argument("--add-template", required=True)
    ap.add_argument("--blend-template", required=True)
    ap.add_argument("--add-atlas-template", required=True)
    ap.add_argument("--blend-atlas-template", required=True)
    ap.add_argument("--texconv", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--prefix", default="eq", help="material folder (asset name prefix)")
    ap.add_argument("--name-prefix", default="bo3wpn_")
    args = ap.parse_args(argv)

    with open(args.effects, encoding="utf-8") as f:
        effects = json.load(f)["effects"]
    atlases = atlas_of(effects)
    templates = {}
    for key in ("add", "blend", "add_atlas", "blend_atlas"):
        with open(getattr(args, key + "_template"), encoding="utf-8") as f:
            templates[key] = json.load(f)
        if templates[key]["textureTable"][0]["semantic"] != 2:
            raise SystemExit("template %s: first texture is not a colour map" % key)
    os.makedirs(os.path.join(args.out, "images"), exist_ok=True)
    os.makedirs(os.path.join(args.out, "materials", args.prefix), exist_ok=True)
    report = {"materials": [], "skipped": []}
    used = set(atlases)
    for path in sorted(glob.glob(os.path.join(args.materials, "materials", "*", "*.json"))):
        with open(path, encoding="utf-8") as f:
            src = json.load(f)
        name = src["name"]
        if name not in used:
            continue
        kind = classify(name, src["techset"])
        if kind == "skip":
            report["skipped"].append({"material": name, "reason": "distortion"})
            continue
        diffuse = [i["name"] for i in src["images"] if i.get("usage") == "diffuse"]
        if not diffuse:
            report["skipped"].append({"material": name, "reason": "no diffuse image"})
            continue
        png = os.path.join(args.materials, "images", diffuse[0] + ".png")
        if not os.path.isfile(png):
            raise SystemExit("missing image %s" % png)
        cols, rows = atlases[name]
        new_name = args.name_prefix + safe(name.split("/")[-1])
        image = new_name + "_c"
        with tempfile.TemporaryDirectory() as tmp:
            staged = os.path.join(tmp, image + ".png")
            with open(png, "rb") as fi, open(staged, "wb") as fo:
                fo.write(fi.read())
            subprocess.run([args.texconv, "-nologo", "-y", "-m", "0", "-f", "BC7_UNORM", "-o",
                            os.path.join(args.out, "images"), staged], check=True, stdout=subprocess.DEVNULL)
        template = templates[kind + ("_atlas" if cols * rows > 1 else "")]
        with open(os.path.join(args.out, "materials", args.prefix, new_name + ".json"), "w", encoding="utf-8") as f:
            json.dump(bind(template, image, cols, rows), f, indent=4)
        report["materials"].append({"bo3": name, "iw7": "%s/%s" % (args.prefix, new_name), "mode": kind,
                                    "atlas": [cols, rows], "technique": template["techniqueSet->name"]})
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

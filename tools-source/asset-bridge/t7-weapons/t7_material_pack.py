"""Pack BO3 material images into IW7 weapon material sources.

Input: a GrayWolf ``*.materials.json`` (BO3 bindings: albedo, xy normal,
occlusion, inverted-gloss roughness, specular, emissive) and a stock IW7
weapon material JSON used as template (techset, constants, sampler states).

Output, under ``--out`` (ZoneTool IW7 source layout):
  images/<mat>_packed_cs.dds   RGB albedo, A specular (luminance of BO3 spec)
  images/<mat>_packed_nog.dds  R gloss, G normal Y, B occlusion, A normal X
  images/<mat>_packed_a.dds    R alpha (opacity), BC4
  images/<mat>_e.dds           emissive (only when BO3 binds one; tint baked, BC7_UNORM)
  materials/<mat>.json         template with the texture table rebound

Channel layouts follow measured stock IW7 weapon textures (see STATUS.md);
they are a design until a rendered comparison confirms them. Compression uses
Microsoft texconv in the stock formats: BC7_UNORM colour (sRGB values stored
as is) and data, BC4_UNORM packed_a.
"""
import argparse
import copy
import json
import os
import re
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

# IW7 texture-table semantics observed in stock weapon materials.
SEM_CS = 14       # *_packed_cs
SEM_NOG = 15      # *_packed_nog
SEM_ALPHA = 16    # *_packed_a
SEM_EMISSIVE = 2          # colour-map semantic; the emissive slot holds a *_e image
SEM_EMISSIVE_CANDIDATES = ("blank_e",)


def emissive_tint(mat):
    """BO3 emissive tint: the emissive colour, else the material colour tint
    (the reticle glows in its tint). None when the map is used as is."""
    for key in ("emissive", "color_tint"):
        b = mat.get(key)
        if isinstance(b, dict) and b.get("color"):
            return [float(c) for c in b["color"][:3]]
    return None


def load_rgba(path, size=None):
    im = Image.open(path).convert("RGBA")
    if size and im.size != size:
        im = im.resize(size, Image.Resampling.LANCZOS)
    return np.asarray(im).astype(np.float32)


def resolve(base, binding):
    if not binding:
        return None
    path = binding["path"] if isinstance(binding, dict) else binding
    full = os.path.normpath(os.path.join(base, path))
    return full if os.path.exists(full) else None


def channel(img, binding, default):
    if img is None:
        return default
    ch = {"r": 0, "g": 1, "b": 2, "a": 3}[binding.get("channel", "r")] if isinstance(binding, dict) else 0
    data = img[..., ch]
    if isinstance(binding, dict) and binding.get("invert"):
        data = 255.0 - data
    return data


def pack_material(mat, base, max_size=0):
    albedo_path = resolve(base, mat.get("albedo"))
    if not albedo_path:
        raise ValueError("material %s has no albedo" % mat["name"])
    albedo = load_rgba(albedo_path)
    h, w = albedo.shape[:2]
    if max_size and max(w, h) > max_size:
        scale = max_size / max(w, h)
        w, h = max(4, int(w * scale)), max(4, int(h * scale))
        albedo = load_rgba(albedo_path, (w, h))
    size = (w, h)

    def opt(key):
        p = resolve(base, mat.get(key))
        return (load_rgba(p, size), mat.get(key)) if p else (None, None)

    normal, nb = opt("normal")
    occl, ob = opt("occlusion")
    rough, rb = opt("roughness")
    spec, _ = opt("specular")
    emis, _ = opt("emissive")
    if emis is not None:
        # The BO3 map is a mask/colour multiplied by a tint; bake the tint's
        # hue, peak channel 1 (the IW7 material has no emissive colour).
        tint = emissive_tint(mat)
        if tint and max(tint) > 0:
            emis = emis.copy()
            emis[..., :3] *= np.array(tint, np.float32) / max(tint)

    cs = np.empty((h, w, 4), np.float32)
    cs[..., :3] = albedo[..., :3]
    if spec is not None:
        cs[..., 3] = spec[..., :3] @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    else:
        cs[..., 3] = 10.0  # stock dielectric level

    nog = np.empty((h, w, 4), np.float32)
    # BO3 roughness binding is inverted gloss; undo the inversion for IW7 gloss.
    gloss = 255.0 - channel(rough, rb, np.full((h, w), 127.0, np.float32)) if rough is not None else np.full((h, w), 127.0, np.float32)
    nog[..., 0] = gloss
    nog[..., 1] = normal[..., 1] if normal is not None else 128.0
    nog[..., 2] = channel(occl, ob, np.full((h, w), 255.0, np.float32))
    nog[..., 3] = normal[..., 0] if normal is not None else 128.0
    return {"cs": cs, "nog": nog, "emissive": emis, "alpha": albedo[..., 3]}


def texconv(texconv_exe, png, out_dir, fmt, srgb):
    args = [texconv_exe, "-nologo", "-y", "-m", "0", "-f", fmt, "-o", out_dir]
    args += ["-srgb"] if srgb else []
    args.append(png)
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL)


def safe(name):
    return re.sub(r"[^A-Za-z0-9_]", "_", name)


def is_emissive_slot(t):
    return t["image"] in SEM_EMISSIVE_CANDIDATES or (t["semantic"] == SEM_EMISSIVE and t["image"].endswith("_e"))


def rebind(template, mat_name, images, emissive_scale=1.0):
    m = copy.deepcopy(template)
    table = []
    for t in m["textureTable"]:
        t = dict(t)
        if t["semantic"] == SEM_CS:
            t["image"] = images["cs"]
        elif t["semantic"] == SEM_NOG:
            t["image"] = images["nog"]
        elif t["semantic"] == SEM_ALPHA:
            t["image"] = images.get("alpha", t["image"])
        elif is_emissive_slot(t) and images.get("emissive"):
            t["image"] = images["emissive"]
        table.append(t)
    m["textureTable"] = table
    for c in m.get("constantTable", []):
        if c.get("name") == "emissivePara":
            c["literal"][0] = emissive_scale
    return m


def has_emissive_slot(template):
    return any(is_emissive_slot(t) for t in template.get("textureTable", []))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("materials_json")
    ap.add_argument("--template", required=True, help="stock IW7 weapon material JSON")
    ap.add_argument("--emissive-template", help="stock IW7 weapon material JSON with an emissive slot, for BO3 "
                    "materials that bind an emissive map (e.g. m2o/attachment_thermalhybrid.json)")
    ap.add_argument("--emissive-scale", type=float, default=1.0, help="emissivePara intensity")
    ap.add_argument("--blend-template", help="stock IW7 alpha-blended weapon material JSON, for BO3 materials "
                    "whose alpha mode is blend (glass), e.g. m2o/weapon_zappers_headcutter_glass.json; an opaque "
                    "'replace' template draws them solid and hides what is behind them")
    ap.add_argument("--texconv", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", nargs="*", help="BO3 material names to convert")
    ap.add_argument("--max-size", type=int, default=0,
                    help="downscale images whose larger side exceeds this (download budget)")
    args = ap.parse_args()

    base = os.path.dirname(os.path.abspath(args.materials_json))
    with open(args.materials_json, encoding="utf-8") as f:
        mats = json.load(f)["materials"]
    with open(args.template, encoding="utf-8") as f:
        template = json.load(f)
    emissive_template = None
    if args.emissive_template:
        with open(args.emissive_template, encoding="utf-8") as f:
            emissive_template = json.load(f)
        if not has_emissive_slot(emissive_template):
            raise SystemExit("emissive template has no emissive (*_e) slot")
    blend_template = None
    if args.blend_template:
        with open(args.blend_template, encoding="utf-8") as f:
            blend_template = json.load(f)
        if "_blend" not in blend_template.get("techniqueSet->name", ""):
            raise SystemExit("blend template technique is not a blend technique")
    for t in (template, emissive_template, blend_template):
        technique = (t or {}).get("techniqueSet->name", "")
        if "2uvt" in technique:
            # Two-UV (camo) techniques read a second UV set BO3 weapon meshes do
            # not have: the client drew the converted Ray Gun black with them.
            raise SystemExit("template technique %s needs a second UV set; use a single-UV weapon template "
                             "(for example m2o_l_sm_replace_i0c0s0o0n0p0_vm)" % technique)
    img_dir = os.path.join(args.out, "images")
    mat_dir = os.path.join(args.out, "materials")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(mat_dir, exist_ok=True)

    report = []
    with tempfile.TemporaryDirectory() as tmp:
        for mat in mats:
            if args.only and mat["name"] not in args.only:
                continue
            name = mat["name"]
            packed = pack_material(mat, base, args.max_size)
            stem = safe(name)
            images = {"cs": stem + "_packed_cs", "nog": stem + "_packed_nog", "alpha": stem + "_packed_a"}
            # Stock formats (GfxImage headers of stock weapon materials): packed_cs
            # and packed_nog BC7_UNORM, packed_a BC4_UNORM, a single red channel.
            # sRGB colour is stored as is; packed_a's red channel holds the alpha.
            alpha = np.zeros(packed["cs"].shape, np.float32)
            alpha[..., 0] = packed["alpha"] if packed["alpha"].shape == alpha.shape[:2] else 255.0
            alpha[..., 3] = 255.0
            jobs = [("cs", packed["cs"], "BC7_UNORM", False), ("nog", packed["nog"], "BC7_UNORM", False),
                    ("alpha", alpha, "BC4_UNORM", False)]
            use = template
            if mat.get("alpha") == "blend" and blend_template is not None:
                use = blend_template
            if packed["emissive"] is not None:
                images["emissive"] = stem + "_e"
                # Stock *_e weapon images are BC7_UNORM, colour stored as is.
                jobs.append(("emissive", packed["emissive"], "BC7_UNORM", False))
                if emissive_template is not None:
                    use = emissive_template
            for key, data, fmt, srgb in jobs:
                png = os.path.join(tmp, images[key] + ".png")
                Image.fromarray(np.clip(data + 0.5, 0, 255).astype(np.uint8), "RGBA").save(png)
                texconv(args.texconv, png, img_dir, fmt, srgb)
            with open(os.path.join(mat_dir, name + ".json"), "w", encoding="utf-8") as f:
                json.dump(rebind(use, name, images, args.emissive_scale), f, indent=4)
            report.append({"material": name, "images": images, "technique": use.get("techniqueSet->name"),
                           "size": list(packed["cs"].shape[1::-1])})
    print(json.dumps({"materials": report}, indent=1))


if __name__ == "__main__":
    sys.exit(main())

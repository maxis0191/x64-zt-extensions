"""Pack BO3 material images into IW7 weapon material sources.

Input: a GrayWolf ``*.materials.json`` (BO3 bindings: albedo, xy normal,
occlusion, inverted-gloss roughness, specular, emissive) and a stock IW7
weapon material JSON used as template (techset, constants, sampler states).

Output, under ``--out`` (ZoneTool IW7 source layout):
  images/<mat>_packed_cs.dds   RGB albedo, A specular (luminance of BO3 spec)
  images/<mat>_packed_nog.dds  R gloss, G normal Y, B occlusion, A normal X
  images/<mat>_e.dds           emissive (only when BO3 binds one)
  materials/<mat>.json         template with the texture table rebound

Channel layouts follow measured stock IW7 weapon textures (see STATUS.md);
they are a design until a rendered comparison confirms them. Compression uses
Microsoft texconv (BC7, sRGB for colour, linear for data).
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
SEM_EMISSIVE_CANDIDATES = ("blank_e",)


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


def rebind(template, mat_name, images):
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
        elif t["image"] in SEM_EMISSIVE_CANDIDATES and images.get("emissive"):
            t["image"] = images["emissive"]
        table.append(t)
    m["textureTable"] = table
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("materials_json")
    ap.add_argument("--template", required=True, help="stock IW7 weapon material JSON")
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
            alpha = np.empty(packed["cs"].shape, np.float32)
            alpha[..., :3] = 8.0  # stock packed_a colour channels are constant
            alpha[..., 3] = packed["alpha"] if packed["alpha"].shape == alpha.shape[:2] else 255.0
            jobs = [("cs", packed["cs"], "BC7_UNORM_SRGB", True), ("nog", packed["nog"], "BC7_UNORM", False),
                    ("alpha", alpha, "BC7_UNORM", False)]
            if packed["emissive"] is not None:
                images["emissive"] = stem + "_e"
                jobs.append(("emissive", packed["emissive"], "BC7_UNORM_SRGB", True))
            for key, data, fmt, srgb in jobs:
                png = os.path.join(tmp, images[key] + ".png")
                Image.fromarray(np.clip(data + 0.5, 0, 255).astype(np.uint8), "RGBA").save(png)
                texconv(args.texconv, png, img_dir, fmt, srgb)
            with open(os.path.join(mat_dir, name + ".json"), "w", encoding="utf-8") as f:
                json.dump(rebind(template, name, images), f, indent=4)
            report.append({"material": name, "images": images,
                           "size": list(packed["cs"].shape[1::-1])})
    print(json.dumps({"materials": report}, indent=1))


if __name__ == "__main__":
    sys.exit(main())

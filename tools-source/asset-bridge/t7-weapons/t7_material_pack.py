"""Pack BO3 material images into IW7 weapon material sources.

Input: a GrayWolf ``*.materials.json`` (BO3 bindings: albedo, xy normal,
occlusion, inverted-gloss roughness, specular, emissive) and a stock IW7
weapon material JSON used as template (techset, constants, sampler states).

Output, under ``--out`` (ZoneTool IW7 source layout):
  images/<mat>_packed_cs.dds   RGB colour (gamma 2.0), A reflectance/metalness
  images/<mat>_packed_nog.dds  R gloss, G/A octahedral normal, B occlusion
  images/<mat>_packed_a.dds    R alpha (opacity), BC4
  images/<mat>_e.dds           emissive (only when BO3 binds one; linear tint, gamma 2.0)
  materials/<mat>.json         template with the texture table rebound

The layouts are the stock weapon pixel shaders' own reads (D3D disassembly,
2026-11-07): opaque m2o_l_sm_replace_..._vm ps 0170a07b0cc77bc0, emissive
ps e9fc6ee4b98ae873, glass m2o_l_sm_ndw_blend_..._vm ps c726a0599d2222d2
(packed_ng: same R/G/A, no occlusion):

* packed_cs: rgb squared; alpha a <= 0.1 is the dielectric reflectance F0,
  above it metalness (a - 0.1) / 0.9: diffuse rgb^2 (1 - m), specular
  m rgb^2 + 0.1. Stock dielectrics read 0.04 (wood, glass), metals ~0.97.
* packed_nog: R gloss (specular power 2^(20 (1 - sqrt(1 - R))) + 2);
  x = (G' + A') / 2, y = (G' - A') / 2, z = 1 - |x| - |y| with G', A' in
  -1..1; B occlusion.
* _e: rgb squared times emissivePara.

BO3 maps are a specular-colour workflow in sRGB; pack_cs converts them.
Compression uses Microsoft texconv in the stock formats: BC7_UNORM colour and
data, BC4_UNORM packed_a.
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


LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)
DIELECTRIC_F0 = 0.04        # stock dielectric packed_cs alpha (wood stool, glass): 10/255
METAL_THRESHOLD = 0.1       # shader: alpha above 0.1 ramps metalness 0..1 over 0.1..1.0


def srgb_to_linear(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def pack_cs(albedo, spec, metalness):
    """packed_cs from BO3 albedo and specular colour (sRGB, 0..255), as the stock weapon pixel shader
    (ps 0170a07b0cc77bc0) reads it: colour = rgb squared; alpha a <= 0.1 is the dielectric reflectance
    F0, above it metalness m = (a - 0.1) / 0.9 with diffuse rgb^2 (1 - m) and specular m rgb^2 + 0.1.
    BO3 is a specular-colour workflow: the specular map is F0. Dielectrics keep their albedo and F0;
    where F0 exceeds 0.1 (metals) diffuse + specular - 0.1 is the colour and the metalness the share
    of the specular in it. Materials with no specular map take BO3's scalar metalness."""
    d = srgb_to_linear(albedo[..., :3] / 255.0)
    out = np.empty(albedo.shape[:2] + (4,), np.float32)
    if spec is None:
        m = np.float32(metalness or 0.0)
        out[..., :3] = np.sqrt(d)
        out[..., 3] = DIELECTRIC_F0 if m <= 0 else METAL_THRESHOLD + (1 - METAL_THRESHOLD) * m
        out[..., 3] *= 255.0
        return out
    s = srgb_to_linear(spec[..., :3] / 255.0)
    f0 = s @ LUMA
    metal = f0 > METAL_THRESHOLD
    c2 = np.where(metal[..., None], np.maximum(d + s - METAL_THRESHOLD, 0.0), d)
    share = np.clip((s - METAL_THRESHOLD) @ LUMA / np.maximum(c2 @ LUMA, 1e-6), 0.0, 1.0)
    out[..., :3] = np.sqrt(np.clip(c2, 0.0, 1.0)) * 255.0
    out[..., 3] = np.where(metal, METAL_THRESHOLD + (1 - METAL_THRESHOLD) * share, f0) * 255.0
    return out


IW7_GLOSS_EXPONENT = 20.0   # packed_nog R: specular power 2^(20 (1 - sqrt(1 - R))) + 2
EMISSIVE_REFERENCE = 16.0   # BO3 hdrScale that --emissive-scale stands for (Ray Gun power cell)


def bo3_gloss_to_r(texel, gloss_range):
    """packed_nog R for a BO3 gloss texel (0..255). BO3 materials scale the gloss map into their own
    glossRange (compiled constant; Ray Gun plastic 4..13, metal 0..17, DG-2 wood 2..10) and read it
    as a log2 specular power, as published for BO2 (8192^gloss, range 13). IW7 decodes R into the
    exponent 20 (1 - sqrt(1 - R)); R is chosen so the exponents match."""
    lo, hi = gloss_range
    g = lo + (hi - lo) * (np.asarray(texel, np.float32) / 255.0)
    e = np.clip(g / IW7_GLOSS_EXPONENT, 0.0, 1.0)
    return (1.0 - (1.0 - e) ** 2) * 255.0


def lookup_constants(constants, name):
    """Compiled BO3 constants of a material (t7_material_read): weapon materials are named "mc/<name>"."""
    if not constants:
        return {}
    return constants.get(name) or constants.get("mc/" + name) or {}


def pack_emissive(emis, tint):
    """The *_e image as the emissive weapon shader (ps e9fc6ee4b98ae873) reads it: rgb squared, times
    emissivePara. The BO3 map (sRGB) is a mask/colour multiplied by a tint: the tint's hue is applied in
    linear light, peak channel 1 (the IW7 material has no emissive colour)."""
    out = emis.copy()
    lin = srgb_to_linear(emis[..., :3] / 255.0)
    if tint and max(tint) > 0:
        lin = lin * (np.array(tint, np.float32) / max(tint))
    out[..., :3] = np.sqrt(np.clip(lin, 0.0, 1.0)) * 255.0
    return out


def octahedral_ga(normal):
    """packed_nog G and A from a BO3 xy normal map (R = x, G = y, 0..255): the shader decodes
    x = (G' + A') / 2, y = (G' - A') / 2, z = 1 - |x| - |y| (octahedral, rotated 45 degrees)."""
    x = normal[..., 0] / 255.0 * 2 - 1
    y = normal[..., 1] / 255.0 * 2 - 1
    z = np.sqrt(np.clip(1 - x * x - y * y, 0.0, 1.0))
    norm = np.abs(x) + np.abs(y) + z
    px, py = x / norm, y / norm
    return (px + py + 1) / 2 * 255.0, (px - py + 1) / 2 * 255.0


def pack_material(mat, base, max_size=0, constants=None):
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
        emis = pack_emissive(emis, emissive_tint(mat))

    cs = pack_cs(albedo, spec, mat.get("metalness_value"))

    nog = np.empty((h, w, 4), np.float32)
    # BO3 roughness binding is inverted gloss; undo the inversion for IW7 gloss. A scalar roughness
    # (BO3 metalness-workflow materials) gives a constant gloss.
    gloss_range = (constants or {}).get("glossRange")
    if rough is not None:
        gloss = 255.0 - channel(rough, rb, np.full((h, w), 127.0, np.float32))
        if gloss_range:
            gloss = bo3_gloss_to_r(gloss, gloss_range[:2])
    elif mat.get("roughness_value") is not None:
        gloss = np.full((h, w), (1.0 - float(mat["roughness_value"])) * 255.0, np.float32)
    else:
        gloss = np.full((h, w), 127.0, np.float32)
    nog[..., 0] = gloss
    if normal is not None:
        nog[..., 1], nog[..., 3] = octahedral_ga(normal)
    else:
        nog[..., 1] = nog[..., 3] = 127.5
    nog[..., 2] = channel(occl, ob, np.full((h, w), 255.0, np.float32))
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
    ap.add_argument("--emissive-scale", type=float, default=1.0,
                    help="emissivePara for a BO3 hdrScale of %g; other materials scale with their hdrScale"
                    % EMISSIVE_REFERENCE)
    ap.add_argument("--constants", help="t7_material_read output (<zone>.materials.json): compiled BO3 "
                    "glossRange and hdrScale per material")
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
    constants = {}
    if args.constants:
        with open(args.constants, encoding="utf-8") as f:
            constants = {k: v.get("constants", {}) for k, v in json.load(f)["materials"].items()}
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
            consts = lookup_constants(constants, name)
            packed = pack_material(mat, base, args.max_size, consts)
            scale = args.emissive_scale
            if consts.get("hdrScale"):
                scale = args.emissive_scale * consts["hdrScale"][0] / EMISSIVE_REFERENCE
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
                json.dump(rebind(use, name, images, scale), f, indent=4)
            report.append({"material": name, "images": images, "technique": use.get("techniqueSet->name"),
                           "size": list(packed["cs"].shape[1::-1]), "gloss_range": consts.get("glossRange"),
                           "emissive_scale": scale if packed["emissive"] is not None else None,
                           "bo3_constants": bool(consts)})
    print(json.dumps({"materials": report}, indent=1))


if __name__ == "__main__":
    sys.exit(main())

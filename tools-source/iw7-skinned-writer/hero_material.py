"""IW7 hero material images (Blender headless: numpy + Blender PNG IO).

blender -b --factory-startup -P hero_material.py -- <mode> ...

  decode --cs <*_packed_cs.png> --nog <*_packed_nog.png> --out <dir>
      stock packed images (GrayWolf export keeps the stored channels) -> authoring maps:
      albedo.png (sRGB), normal.png (tangent space, R=x G=y B=z, 0..255), gloss.png, ao.png, reflectance.png
  pack --albedo <png> [--hue <deg>] [--normal <png>] [--gloss <png> | --roughness <png>] [--ao <png>]
       [--reflectance <png> | --metalness <0..1>] [--max-size N] --stem <image stem> --out <dir>
       [--ref-cs <png> --ref-nog <png>]   (report the difference against stock packed images)
      -> <stem>_c_packed_cs.png, <stem>_n_packed_nog.png (+ pack_report.json)

Layouts (as the stock IW7 pixel shaders read them, see asset-bridge/t7-weapons/t7_material_pack.py):
  packed_cs  RGB = sqrt(linear albedo) (gamma 2.0), A = reflectance: a <= 0.1 dielectric F0 (stock 0.04),
             above it metalness (a - 0.1) / 0.9
  packed_nog R = gloss, G/A = octahedral normal (x = (G' + A') / 2, y = (G' - A') / 2, z = 1 - |x| - |y|),
             B = occlusion
"""
import json
import os
import sys

import bpy
import numpy as np


def load(path, size=None):
    img = bpy.data.images.load(path, check_existing=False)
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    if size and (w, h) != tuple(size):
        img.scale(size[0], size[1])
        w, h = size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4) * 255.0          # bottom-up rows, consistent with save()


def save(path, arr):
    h, w = arr.shape[:2]
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=True)
    img.colorspace_settings.name = "Non-Color"
    img.alpha_mode = "STRAIGHT"
    img.pixels.foreach_set((np.clip(np.round(arr), 0, 255) / 255.0).astype(np.float32).ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


# ------------------------------------------------------------------ packed_cs
def pack_cs(albedo, reflectance=None, metalness=None):
    out = np.empty(albedo.shape[:2] + (4,), np.float32)
    lin = srgb_to_linear(albedo[..., :3] / 255.0)
    out[..., :3] = np.sqrt(lin) * 255.0
    if reflectance is not None:
        out[..., 3] = reflectance[..., 0]
    elif metalness:
        out[..., 3] = (0.1 + 0.9 * float(metalness)) * 255.0
    else:
        out[..., 3] = 0.04 * 255.0
    return out


def unpack_cs(cs):
    alb = np.empty_like(cs)
    alb[..., :3] = linear_to_srgb((cs[..., :3] / 255.0) ** 2) * 255.0
    alb[..., 3] = 255.0
    refl = np.repeat(cs[..., 3:4], 4, axis=2)
    refl[..., 3] = 255.0
    return alb, refl


# ------------------------------------------------------------------ packed_nog
def octahedral_ga(normal):
    x = normal[..., 0] / 255.0 * 2 - 1
    y = normal[..., 1] / 255.0 * 2 - 1
    z = np.clip(normal[..., 2] / 255.0 * 2 - 1, 0.0, 1.0)
    n = np.abs(x) + np.abs(y) + z
    n = np.where(n < 1e-6, 1.0, n)
    px, py = x / n, y / n
    return (px + py + 1) / 2 * 255.0, (px - py + 1) / 2 * 255.0


def pack_nog(normal, gloss, ao):
    h, w = gloss.shape[:2]
    out = np.empty((h, w, 4), np.float32)
    out[..., 0] = gloss
    if normal is None:
        out[..., 1] = out[..., 3] = 127.5
    else:
        out[..., 1], out[..., 3] = octahedral_ga(normal)
    out[..., 2] = ao
    return out


def unpack_nog(nog):
    g = nog[..., 1] / 255.0 * 2 - 1
    a = nog[..., 3] / 255.0 * 2 - 1
    x, y = (g + a) / 2, (g - a) / 2
    z = np.clip(1 - np.abs(x) - np.abs(y), 0.0, 1.0)
    ln = np.sqrt(x * x + y * y + z * z)
    ln = np.where(ln < 1e-6, 1.0, ln)
    nrm = np.empty_like(nog)
    nrm[..., 0], nrm[..., 1], nrm[..., 2] = [(c / ln + 1) / 2 * 255.0 for c in (x, y, z)]
    nrm[..., 3] = 255.0
    gray = lambda c: np.dstack([c, c, c, np.full_like(c, 255.0)])
    return nrm, gray(nog[..., 0]), gray(nog[..., 2])


def pad_islands(arr, valid, iters=12):
    """Edge padding: grow the UV islands into the unused atlas texels (average of valid neighbours, `iters` rings),
    the rest takes the island mean. Stops black / max-gloss background bleeding into islands through mips and BC7."""
    out = arr.copy()
    v = valid.copy()
    for _ in range(iters):
        if v.all():
            break
        acc = np.zeros_like(out)
        cnt = np.zeros(v.shape, np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            sv = np.roll(np.roll(v, dy, 0), dx, 1)
            so = np.roll(np.roll(out, dy, 0), dx, 1)
            acc += so * sv[..., None]
            cnt += sv
        grow = (~v) & (cnt > 0)
        out[grow] = acc[grow] / cnt[grow][:, None]
        v = v | grow
    if (~v).any():
        out[~v] = out[v].mean(axis=0) if v.any() else 0
    return out


def hue_rotate(rgb, deg):
    """Rotate the hue of sRGB colours around the grey axis (keeps luminance roughly)."""
    t = np.radians(deg)
    c, s = np.cos(t), np.sin(t)
    k = 1.0 / 3.0
    sq = np.sqrt(k)
    m = np.array([[c + (1 - c) * k, k * (1 - c) - sq * s, k * (1 - c) + sq * s],
                  [k * (1 - c) + sq * s, c + k * (1 - c), k * (1 - c) - sq * s],
                  [k * (1 - c) - sq * s, k * (1 - c) + sq * s, c + k * (1 - c)]], np.float32)
    out = rgb.copy()
    out[..., :3] = np.clip(rgb[..., :3] @ m.T, 0, 255)
    return out


def opts(argv):
    o, i = {}, 0
    while i < len(argv):
        if argv[i].startswith("--"):
            o[argv[i][2:]] = argv[i + 1]
            i += 2
        else:
            o.setdefault("_", []).append(argv[i])
            i += 1
    return o


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    mode, o = argv[0], opts(argv[1:])
    os.makedirs(o["out"], exist_ok=True)
    if mode == "normcheck":
        # Which green convention does a tangent normal map follow? A baked normal map is the gradient of a height
        # field, so its slope field (p, q) = (-x/z, -y/z) is curl-free in the image frame of its convention:
        # OpenGL (+Y = image up) or DirectX (+Y = image down). The convention with the smaller curl wins.
        rep = {}
        for key in [k for k in o if k.startswith("img")]:
            arr = load(o[key])                       # rows bottom-up (Blender): row index grows image-up
            if o.get(key + "-nog") == "1" or "_nog" in o[key]:
                nrm, _, _ = unpack_nog(arr)
            else:
                nrm = arr
            x = nrm[..., 0] / 255.0 * 2 - 1
            y = nrm[..., 1] / 255.0 * 2 - 1
            z = np.clip(nrm[..., 2] / 255.0 * 2 - 1, 0.2, 1.0)
            p, q = -x / z, -y / z
            dp_dup = np.diff(p, axis=0)[:, :-1]      # d/d(up)
            dq_dx = np.diff(q, axis=1)[:-1, :]
            curl_gl = float(np.mean(np.abs(dp_dup - dq_dx)))   # q = dh/d(up)
            curl_dx = float(np.mean(np.abs(-dp_dup - dq_dx)))  # q = dh/d(down)
            rep[o[key]] = {"curl_opengl": curl_gl, "curl_directx": curl_dx,
                           "verdict": "opengl" if curl_gl < curl_dx else "directx"}
        json.dump(rep, open(os.path.join(o["out"], "normcheck.json"), "w"), indent=1)
        print("NORMCHECK " + json.dumps(rep))
        return
    if mode == "decode":
        cs, nog = load(o["cs"]), load(o["nog"])
        alb, refl = unpack_cs(cs)
        nrm, gloss, ao = unpack_nog(nog)
        for name, arr in (("albedo", alb), ("reflectance", refl), ("normal", nrm), ("gloss", gloss), ("ao", ao)):
            save(os.path.join(o["out"], name + ".png"), arr)
        print("DECODE_OK", cs.shape)
        return
    alb = load(o["albedo"])
    if o.get("max-size") and max(alb.shape[:2]) > int(o["max-size"]):
        f = int(o["max-size"]) / max(alb.shape[:2])
        alb = load(o["albedo"], (int(alb.shape[1] * f), int(alb.shape[0] * f)))
    size = (alb.shape[1], alb.shape[0])
    if o.get("hue"):
        alb = hue_rotate(alb, float(o["hue"]))
    ld = lambda k: load(o[k], size) if o.get(k) else None
    refl, nrm, ao = ld("reflectance"), ld("normal"), ld("ao")
    if nrm is not None and o.get("flip-green") == "1":
        nrm[..., 1] = 255.0 - nrm[..., 1]          # OpenGL <-> DirectX green
    if o.get("gloss"):
        gloss = ld("gloss")[..., 0]
    elif o.get("roughness"):
        gloss = 255.0 - ld("roughness")[..., 0]
    else:
        gloss = np.full(alb.shape[:2], 127.0, np.float32)
    ao = ao[..., 0] if ao is not None else np.full(alb.shape[:2], 255.0, np.float32)
    rep_fix = {}
    if o.get("pad") == "1":
        # island mask: texels the bake wrote (albedo or roughness non-black); fit bakes leave the rest black
        rough_src = ld("roughness")
        valid = alb[..., :3].sum(-1) > 3.0
        if rough_src is not None:
            valid |= rough_src[..., 0] > 0.5
        rep_fix["island_fraction"] = float(valid.mean())
        # AO: texels inside islands the AO bake missed (0) mean 'not baked', not 'fully occluded'
        ao = np.where(valid & (ao < 1.0), 255.0, ao)
        rep_fix["ao_unbaked_fraction"] = float((valid & (ao >= 255.0)).mean())
        stack = np.dstack([alb[..., :3], gloss, ao] + ([refl[..., 0]] if refl is not None else []) +
                          ([nrm[..., :3]] if nrm is not None else []))
        stack = pad_islands(stack.astype(np.float32), valid)
        alb = np.dstack([stack[..., 0:3], alb[..., 3:4]])
        gloss, ao = stack[..., 3], stack[..., 4]
        k = 5
        if refl is not None:
            refl = np.repeat(stack[..., k:k + 1], 4, axis=2)
            k += 1
        if nrm is not None:
            nrm = np.dstack([stack[..., k:k + 3], np.full(gloss.shape, 255.0, np.float32)])
    if o.get("ao-floor"):
        f = float(o["ao-floor"])        # 0..1: keep only part of the baked occlusion (stock cloth AO is mostly light)
        ao = 255.0 - (255.0 - ao) * (1.0 - f)
    if o.get("gloss-scale"):
        gloss = np.clip(gloss * float(o["gloss-scale"]), 0, 255)
    rep_fix.update({"ao_mean": float(ao.mean()), "gloss_mean": float(gloss.mean())})
    cs = pack_cs(alb, refl, float(o["metalness"]) if o.get("metalness") else None)
    nog = pack_nog(nrm, gloss, ao)
    stem = o["stem"]
    p_cs = os.path.join(o["out"], stem + "_c_packed_cs.png")
    p_nog = os.path.join(o["out"], stem + "_n_packed_nog.png")
    save(p_cs, cs)
    save(p_nog, nog)
    rep = {"size": list(size), "cs": p_cs, "nog": p_nog, "hue": o.get("hue"), "fix": rep_fix}
    for key, arr in (("ref-cs", cs), ("ref-nog", nog)):
        if o.get(key):
            ref = load(o[key], size)
            d = np.abs(np.round(np.clip(arr, 0, 255)) - ref)
            rep[key] = {"mean_abs_per_channel": [float(d[..., c].mean()) for c in range(4)],
                        "p99_abs_per_channel": [float(np.percentile(d[..., c], 99)) for c in range(4)]}
    json.dump(rep, open(os.path.join(o["out"], "pack_report.json"), "w"), indent=1)
    print("PACK_OK " + json.dumps(rep))


main()

"""Build an original weapon from a Blender generator onto a stock donor skeleton, in one command.

    python -I build_authored_weapon.py <recipe.json> --donor-dump <dir> --out <zonetool fragment dir>
           [--work <dir>] [--preview-dir <dir>] [--skip-generator] [--fast]

The recipe (see exact_change.recipe.json) names the generator, the donor models, the bone bindings, the atlases and
their material templates. No weapon name appears in this code. Steps (each timed in <work>/build_report.json):

  generate   blender -b --factory-startup -P <generator> -- --params <work>/params.json --out <work>/gen
             (model.blend: one mesh per (bone, atlas), vertex group = bone, UV "uv" + "camo"; bake/*.npy maps)
  export     tools-source/iw7-skinned-writer/blender_export.py --all-meshes --unit 1 --uv2 camo, once per LOD ratio
  models     per recipe model: bones renamed / dropped by its bone_map, moved by its offset (or onto its align
             bone), then build_model.py on the donor skeleton (camo UV records on camo atlases), physics LOD copied
  textures   per atlas: packed_cs / packed_nog (packed_ng for blend) BC7, packed_a BC4 via texconv
  materials  per atlas and view: the template material JSON with the images rebound, its techset state and
             constant buffer files copied under the new name
  rows       <out>/rows.csv: material rows, then xmodel rows
  proofs     authored_weapon_proof.py (exit code), viewmodel preview PNGs

Machine paths come from the recipe's "tools" block, which may use ${ENV} variables.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

try:
    import numpy as np
except ImportError:  # python -I leaves out the user site, where numpy / Pillow are installed on this machine
    import site
    sys.path.append(site.getusersitepackages())
    import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
T7 = os.path.dirname(HERE)
WRITER = os.path.normpath(os.path.join(T7, "..", "..", "iw7-skinned-writer"))
sys.path[:0] = [WRITER, T7]

SEM_CS, SEM_NOG, SEM_ALPHA = 14, 15, 16


# ------------------------------------------------------------------ recipe
def expand(value, env=None):
    """${NAME} -> environment value; a missing variable is an error naming it."""
    env = os.environ if env is None else env
    if isinstance(value, str):
        def sub(m):
            if m.group(1) not in env:
                raise KeyError("environment variable %s is not set" % m.group(1))
            return env[m.group(1)]
        return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", sub, value)
    if isinstance(value, dict):
        return {k: expand(v, env) for k, v in value.items()}
    if isinstance(value, list):
        return [expand(v, env) for v in value]
    return value


def load_recipe(path, env=None):
    with open(path, encoding="utf-8") as f:
        r = json.load(f)
    r["tools"] = expand(r.get("tools", {}), env)
    r["_dir"] = os.path.dirname(os.path.abspath(path))
    for m in r["models"]:
        if not m.get("name") or not m.get("donor"):
            raise ValueError("every model needs a name and a donor")
    for key, a in r["atlases"].items():
        if a.get("camo") and a.get("blend"):
            raise ValueError("atlas %s cannot be camo and blend" % key)
    return r


# ------------------------------------------------------------------ donor data
def bone_positions(xm):
    """{bone name: model-space bind position} (baseMat translation)."""
    return {n: tuple(xm.base_mat[i][4:7]) for i, n in enumerate(xm.bone_names)}


def derive_params(recipe, donors):
    """generator_params with "from_donor" entries resolved: ["pos", model, bone] -> [x, y, z];
    ["xs", model, [bones]] -> [x, ...]."""
    out = dict(recipe.get("generator_params", {}))
    for key, spec in recipe.get("from_donor", {}).items():
        kind, model = spec[0], spec[1]
        pos = bone_positions(donors[model])
        if kind == "pos":
            out[key] = list(pos[spec[2]])
        elif kind == "xs":
            out[key] = [pos[b][0] for b in spec[2]]
        else:
            raise ValueError("unknown from_donor kind " + kind)
    out["atlases"] = recipe["atlases"]
    out["camo_uv_per_inch"] = recipe.get("camo_uv_per_inch", 0.12)
    return out


# ------------------------------------------------------------------ mesh JSON transforms (generic, unit tested)
def remap_mesh(mesh, bone_map, offset, allowed_bones):
    """Rename bones (bone_map value None drops the vertex's surface), shift positions by offset, check every vertex
    names exactly one bone of allowed_bones. Returns (new mesh, report). Surfaces whose bone is dropped are removed
    (every authored surface is rigid: one bone)."""
    out = dict(mesh, surfaces=[])
    rep = {"dropped_surfaces": [], "renamed": {}, "kept_surfaces": 0}
    for s in mesh["surfaces"]:
        bones = {w[0][0] if len(w) == 1 else None for w in (v["w"] for v in s["verts"])}
        if None in bones or len(bones) != 1:
            raise ValueError("surface %s is not rigid (one bone at weight 1 per vertex)" % s["object"])
        src = bones.pop()
        dst = bone_map.get(src, src)
        if dst is None:
            rep["dropped_surfaces"].append(s["object"])
            continue
        if dst not in allowed_bones:
            raise ValueError("bone %s (from %s) is not in the donor skeleton" % (dst, src))
        if dst != src:
            rep["renamed"][src] = dst
        ns = dict(s, verts=[])
        for v in s["verts"]:
            nv = dict(v)
            nv["p"] = [v["p"][i] + offset[i] for i in range(3)]
            nv["w"] = [[dst, 1.0]]
            ns["verts"].append(nv)
        out["surfaces"].append(ns)
        rep["kept_surfaces"] += 1
    out["armature"] = None
    return out, rep


def fit_uv2_scale(mesh):
    """{material: (k, cu, cv)} with uv2 = k * uv + (cu, cv), least squares over the surfaces that carry uv2."""
    acc = {}
    for s in mesh["surfaces"]:
        for v in s["verts"]:
            if "uv2" in v:
                acc.setdefault(s["material"], []).append((v["uv"], v["uv2"]))
    fits = {}
    for mat, pairs in acc.items():
        n = len(pairs)
        mu = [sum(p[0][i] for p in pairs) / n for i in range(2)]
        mw = [sum(p[1][i] for p in pairs) / n for i in range(2)]
        cov = sum((p[0][i] - mu[i]) * (p[1][i] - mw[i]) for p in pairs for i in range(2))
        var = sum((p[0][i] - mu[i]) ** 2 for p in pairs for i in range(2))
        k = cov / var if var else 1.0
        fits[mat] = (k, mw[0] - k * mu[0], mw[1] - k * mu[1])
    return fits


def apply_uv2_scale(mesh, fits):
    """Decimated LODs: the decimator interpolates each UV layer on its own and breaks uv2 = k uv + c at seams;
    the camo layer of an authored atlas is that scale by contract, so it is rebuilt from the first UV set."""
    out = dict(mesh, surfaces=[])
    for s in mesh["surfaces"]:
        f = fits.get(s["material"])
        if f is None:
            out["surfaces"].append(s)
            continue
        ns = dict(s, verts=[dict(v, uv2=[f[0] * v["uv"][0] + f[1], f[0] * v["uv"][1] + f[2]]) for v in s["verts"]])
        out["surfaces"].append(ns)
    return out


def keep_atlases(mesh, material_map):
    """Only the surfaces whose atlas has a material in this view (a recipe material of null leaves it out)."""
    return dict(mesh, surfaces=[s for s in mesh["surfaces"] if s["material"] in material_map])


def merge_surfaces(mesh):
    """Join surfaces of the same material (one draw per material and LOD; bones stay per vertex)."""
    by = {}
    order = []
    for s in mesh["surfaces"]:
        key = s["material"]
        if key not in by:
            by[key] = {"object": key, "material": key, "verts": [], "tris": []}
            order.append(key)
        d = by[key]
        base = len(d["verts"])
        d["verts"] += s["verts"]
        d["tris"] += [[a + base, b + base, c + base] for a, b, c in s["tris"]]
    return dict(mesh, surfaces=[by[k] for k in order])


# ------------------------------------------------------------------ textures (generic, unit tested)
def gloss_from_roughness(r):
    """packed_nog R for a GGX roughness: IW7 decodes R into a specular power 2^(20 (1 - sqrt(1 - R))) + 2;
    the Blinn-Phong power matching GGX alpha = r^2 is 2 / alpha^2 - 2."""
    r = np.clip(np.asarray(r, np.float64), 0.02, 1.0)
    power = 2.0 / r ** 4 - 2.0
    e = np.clip(np.log2(np.maximum(power - 2.0, 1.0)) / 20.0, 0.0, 1.0)
    return 1.0 - (1.0 - e) ** 2


def pack_cs(albedo, metal):
    """packed_cs (0..1 floats): rgb^2 is the colour, alpha <= 0.1 dielectric F0 (0.04), above it metalness
    m = (a - 0.1) / 0.9 whose specular is m rgb^2 + 0.1 (t7_material_pack.py, stock pixel shader)."""
    a = np.clip(albedo[..., :3], 0.0, 1.0)
    m = np.clip(metal, 0.0, 1.0)
    metallic = m >= 0.02
    c2 = np.where(metallic[..., None], np.clip(a - 0.1 * m[..., None], 0.0, 1.0), a)
    out = np.empty(a.shape[:2] + (4,), np.float64)
    out[..., :3] = np.sqrt(c2)
    out[..., 3] = np.where(metallic, 0.1 + 0.9 * m, 0.04)
    return out


def pack_nog(normal_gl, gloss, ao):
    """packed_nog: R gloss, G/A octahedral normal (DirectX green: Blender's tangent bake is OpenGL), B occlusion."""
    n = normal_gl[..., :3] * 2.0 - 1.0
    x, y, z = n[..., 0], -n[..., 1], np.clip(n[..., 2], 0.0, 1.0)
    s = np.abs(x) + np.abs(y) + z
    s = np.where(s <= 1e-6, 1.0, s)
    px, py = x / s, y / s
    out = np.empty(n.shape[:2] + (4,), np.float64)
    out[..., 0] = gloss
    out[..., 1] = (px + py + 1.0) / 2.0
    out[..., 2] = ao
    out[..., 3] = (px - py + 1.0) / 2.0
    return out


def unpack_nog_normal(nog):
    """Inverse of the octahedral packing (DirectX tangent space), for checks."""
    g, a = nog[..., 1] * 2 - 1, nog[..., 3] * 2 - 1
    x, y = (g + a) / 2, (g - a) / 2
    z = 1 - np.abs(x) - np.abs(y)
    v = np.stack([x, y, z], -1)
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def atlas_images(maps, blend):
    """maps: albedo, params (R rough, G metal, B mask/opacity), normal, ao arrays (H, W, 4) floats ->
    {suffix: (H, W, 4) 0..1 array} for packed_cs, packed_nog/packed_ng, packed_a."""
    rough, metal, mask = maps["params"][..., 0], maps["params"][..., 1], maps["params"][..., 2]
    ao = maps["ao"][..., 0] if not blend else np.ones_like(rough)
    cs = pack_cs(maps["albedo"], metal)
    nog = pack_nog(maps["normal"], gloss_from_roughness(rough), ao)
    a = np.zeros_like(cs)
    a[..., 0] = np.clip(mask, 0.0, 1.0)
    a[..., 3] = 1.0
    return {"packed_cs": cs, "packed_ng" if blend else "packed_nog": nog, "packed_a": a}


def write_png(arr, path):
    from PIL import Image
    Image.fromarray((np.clip(arr, 0, 1) * 255.0 + 0.5).astype(np.uint8), "RGBA").save(path)


def texconv(exe, png, out_dir, fmt):
    subprocess.run([exe, "-nologo", "-y", "-m", "0", "-f", fmt, "-o", out_dir, png], check=True,
                   stdout=subprocess.DEVNULL)


# ------------------------------------------------------------------ materials (generic, unit tested)
def rebind_material(template, images):
    """Template material JSON with semantics 14/15/16 rebound to the new images."""
    m = json.loads(json.dumps(template))
    for t in m["textureTable"]:
        if t["semantic"] == SEM_CS:
            t["image"] = images["cs"]
        elif t["semantic"] == SEM_NOG:
            t["image"] = images["nog"]
        elif t["semantic"] == SEM_ALPHA:
            t["image"] = images["a"]
    return m


def copy_techset_files(template_root, technique, template_name, out_root, new_name):
    copied = []
    for kind in ("state", "constantbuffer"):
        src_dir = os.path.join(template_root, "techsets", kind, technique, os.path.dirname(template_name))
        stem = os.path.basename(template_name)
        if not os.path.isdir(src_dir):
            continue
        for f in sorted(os.listdir(src_dir)):
            if os.path.splitext(f)[0] == stem:
                dst = os.path.join(out_root, "techsets", kind, technique, new_name.replace("/", os.sep)
                                   + os.path.splitext(f)[1])
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(os.path.join(src_dir, f), dst)
                copied.append(os.path.relpath(dst, out_root).replace(os.sep, "/"))
    return copied


def zone_rows(materials, models):
    """rows.csv lines: every material before the models that use it, models last."""
    rows = ["material,%s" % m for m in materials]
    rows += ["xmodel,%s" % m for m in models]
    return rows


# ------------------------------------------------------------------ steps
def run(cmd, log):
    t = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    with open(log, "w", encoding="utf-8") as f:
        f.write(" ".join(cmd) + "\n\n" + p.stdout + "\n" + p.stderr)
    if p.returncode != 0:
        raise SystemExit("step failed (%d), see %s" % (p.returncode, log))
    return time.time() - t, p.stdout


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("recipe")
    ap.add_argument("--donor-dump", required=True, help="dump root holding xmodel/ and xsurface/ of the donors")
    ap.add_argument("--out", required=True, help="ZoneTool zone tree fragment to write")
    ap.add_argument("--work", help="work folder (default <out>/../work)")
    ap.add_argument("--preview-dir", help="where the preview PNGs go (default <out>/../preview)")
    ap.add_argument("--skip-generator", action="store_true", help="reuse <work>/gen (iterate on later steps)")
    ap.add_argument("--fast", action="store_true", help="atlases at 1/4 size and few samples (layout iteration)")
    a = ap.parse_args(argv)

    import xmodel
    recipe = load_recipe(a.recipe)
    tools = recipe["tools"]
    out = os.path.abspath(a.out)
    work = os.path.abspath(a.work or os.path.join(out, "..", "work"))
    preview_dir = os.path.abspath(a.preview_dir or os.path.join(out, "..", "preview"))
    for d in (out, work, preview_dir):
        os.makedirs(d, exist_ok=True)
    timing = {}
    report = {"recipe": os.path.abspath(a.recipe), "out": out, "timing_s": timing}

    donors = {}
    for m in recipe["models"]:
        donors[m["donor"]] = xmodel.read(open(os.path.join(a.donor_dump, "xmodel", m["donor"] + ".xmb"), "rb").read())

    # 1. generator
    gen = os.path.join(work, "gen")
    params = derive_params(recipe, donors)
    if a.fast:
        params["atlases"] = {k: dict(v, size=max(64, v["size"] // 4), samples=4) for k, v in params["atlases"].items()}
        if params.get("preview"):
            params["preview"] = dict(params["preview"], samples=8)
    with open(os.path.join(work, "params.json"), "w") as f:
        json.dump(params, f, indent=1)
    generator = os.path.join(recipe["_dir"], recipe["generator"])
    if not a.skip_generator:
        if os.path.isdir(gen):
            shutil.rmtree(gen)
        timing["generate"], _ = run([tools["blender"], "-b", "--factory-startup", "-P", generator, "--",
                                     "--params", os.path.join(work, "params.json"), "--out", gen],
                                    os.path.join(work, "generate.log"))
    report["generator"] = json.load(open(os.path.join(gen, "generator.json")))

    # 2. export (one per LOD ratio)
    ratios = sorted({l.get("decimate", 1.0) for m in recipe["models"] for l in m["lods"]}, reverse=True)
    meshes = {}
    t = time.time()
    for r in ratios:
        path = os.path.join(work, "export_%03d.json" % int(round(r * 100)))
        cmd = [tools["blender"], "-b", "--factory-startup", os.path.join(gen, "model.blend"), "-P",
               os.path.join(WRITER, "blender_export.py"), "--", "--out", path, "--all-meshes", "--unit", "1",
               "--uv2", "camo"]
        if r < 1.0:
            cmd += ["--decimate", str(r)]
        run(cmd, os.path.join(work, "export_%03d.log" % int(round(r * 100))))
        meshes[r] = json.load(open(path))
        unknown = sorted({s["material"] for s in meshes[r]["surfaces"]} - set(recipe["atlases"]))
        if unknown:
            raise SystemExit("exported surfaces carry materials that are not atlases: %s" % unknown)
    timing["export"] = time.time() - t
    if 1.0 not in meshes:
        raise SystemExit("one LOD of the recipe must use decimate 1.0 (the camo scale is read from it)")
    uv2_fits = {k: v for k, v in fit_uv2_scale(meshes[1.0]).items() if recipe["atlases"].get(k, {}).get("camo")}
    for r in meshes:
        meshes[r] = apply_uv2_scale(meshes[r], uv2_fits)
    report["uv2_scale"] = uv2_fits

    # 3. textures + materials (names first: the models reference them)
    prefix = recipe["image_prefix"]
    img_dir = os.path.join(out, "images")
    os.makedirs(img_dir, exist_ok=True)
    t = time.time()
    tex_report, material_rows = {}, []
    tmp_png = os.path.join(work, "png")
    os.makedirs(tmp_png, exist_ok=True)
    for key, atlas in sorted(recipe["atlases"].items()):
        maps = {c: np.load(os.path.join(gen, "bake", "%s_%s.npy" % (key, c))).astype(np.float64)
                for c in ("albedo", "params", "normal", "ao")}
        imgs = atlas_images(maps, atlas.get("blend", False))
        names = {}
        for suffix, arr in imgs.items():
            stem = "%s_%s_%s" % (prefix, key, suffix)
            png = os.path.join(tmp_png, stem + ".png")
            write_png(arr, png)
            texconv(tools["texconv"], png, img_dir, "BC4_UNORM" if suffix == "packed_a" else "BC7_UNORM")
            if not os.path.exists(os.path.join(img_dir, stem + ".dds")):
                raise SystemExit("texconv wrote no " + stem + ".dds")
            names["a" if suffix == "packed_a" else "cs" if suffix == "packed_cs" else "nog"] = stem
        tex_report[key] = {"images": names, "size": int(maps["albedo"].shape[0]),
                           "mask_mean": float(maps["params"][..., 2].mean())}
        for view, mat in atlas["materials"].items():
            if mat is None:          # this view leaves the atlas out (its surfaces are dropped from that model)
                continue
            tpl_path = os.path.join(tools["template_root"], "materials", mat["template"].replace("/", os.sep) + ".json")
            template = json.load(open(tpl_path))
            if atlas.get("camo") and "_2uvt" not in template["techniqueSet->name"]:
                raise SystemExit("atlas %s is camo but template %s is not a camo (_2uvt) technique"
                                 % (key, mat["template"]))
            m = rebind_material(template, names)
            dst = os.path.join(out, "materials", mat["name"].replace("/", os.sep) + ".json")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "w") as f:
                json.dump(m, f, indent=4)
            tex_report[key].setdefault("materials", {})[view] = {
                "name": mat["name"], "technique": m["techniqueSet->name"],
                "techset_files": copy_techset_files(tools["template_root"], m["techniqueSet->name"], mat["template"],
                                                    out, mat["name"])}
            material_rows.append(mat["name"])
    timing["textures_materials"] = time.time() - t
    report["textures"] = tex_report

    # 4. models
    import build_model
    t = time.time()
    model_rows, model_reports = [], {}
    vm_donor = donors[recipe["models"][0]["donor"]]
    for m in recipe["models"]:
        donor = donors[m["donor"]]
        offset = m.get("offset", [0.0, 0.0, 0.0])
        if m.get("align_bone"):
            pa = bone_positions(donor)[m["align_bone"]]
            pb = bone_positions(vm_donor)[m["align_bone"]]
            offset = [pa[i] - pb[i] for i in range(3)]
        view = m.get("view", "vm")
        mat_map = {k: at["materials"][view]["name"] for k, at in recipe["atlases"].items() if at["materials"][view]}
        inv = {}
        for k, at in recipe["atlases"].items():
            if not at["materials"][view]:
                continue
            tpl = at["materials"][view]["template"]
            for i, mn in enumerate(donor.materials):
                if mn == tpl and i < len(donor.inv_high_mip):
                    inv[at["materials"][view]["name"]] = donor.inv_high_mip[i]
                    break
        mm_path = os.path.join(work, m["name"] + "_materials.json")
        inv_path = os.path.join(work, m["name"] + "_invmip.json")
        json.dump(mat_map, open(mm_path, "w"))
        json.dump(inv, open(inv_path, "w"))
        lod_paths, mrep = [], {}
        for li, lod in enumerate(m["lods"]):
            mesh, rep = remap_mesh(meshes[lod.get("decimate", 1.0)], m.get("bone_map", {}), offset,
                                   set(donor.bone_names))
            mesh = merge_surfaces(keep_atlases(mesh, mat_map))
            p = os.path.join(work, "%s_lod%d.json" % (m["name"], li))
            json.dump(mesh, open(p, "w"))
            lod_paths.append((p, lod["dist"]))
            mrep["lod%d" % li] = rep
        cmd = [lod_paths[0][0], "--base-xmodel", os.path.join(a.donor_dump, "xmodel", m["donor"] + ".xmb"),
               "--name", m["name"], "--out", out, "--material-map", mm_path, "--inv-mip-map", inv_path,
               "--camo-materials", ",".join(k for k, at in recipe["atlases"].items() if at.get("camo")
                                            and k in mat_map),
               "--surface-order", ",".join(recipe.get("surface_order", sorted(recipe["atlases"]))),
               "--lod-dist", str(lod_paths[0][1]), "--report", os.path.join(work, m["name"] + "_build.json")]
        if len(lod_paths) > 1:
            cmd += ["--lods", ",".join("%s:%s" % (p, d) for p, d in lod_paths[1:])]
        run([sys.executable, "-I", os.path.join(WRITER, "build_model.py")] + cmd,
            os.path.join(work, m["name"] + "_build.log"))
        mrep["build"] = json.load(open(os.path.join(work, m["name"] + "_build.json")))
        mrep["offset"] = offset
        if m.get("copy_physics_lod"):
            src = os.path.join(a.donor_dump, "xmodel", m["donor"] + "_lod.hkx")
            if os.path.exists(src):
                shutil.copyfile(src, os.path.join(out, "xmodel", m["name"] + "_lod.hkx"))
                mrep["physics_lod"] = m["donor"] + "_lod.hkx"
        model_reports[m["name"]] = mrep
        model_rows.append(m["name"])
    timing["models"] = time.time() - t
    report["models"] = model_reports

    rows = zone_rows(material_rows, model_rows)
    with open(os.path.join(out, "rows.csv"), "w", newline="\n") as f:
        f.write("\n".join(rows) + "\n")
    report["rows"] = rows

    # 5. proofs and previews
    t = time.time()
    proof_json = os.path.join(work, "proof.json")
    p = subprocess.run([sys.executable, "-I", os.path.join(HERE, "authored_weapon_proof.py"), a.recipe,
                        "--donor-dump", a.donor_dump, "--out", out, "--json", proof_json,
                        "--preview-dir", preview_dir], capture_output=True, text=True, errors="replace")
    open(os.path.join(work, "proof.log"), "w", encoding="utf-8").write(p.stdout + p.stderr)
    timing["proofs"] = time.time() - t
    report["proof_exit"] = p.returncode
    import hashlib
    report["sha256"] = {}
    for sub in ("xmodel", "xsurface", "images"):
        for f in sorted(os.listdir(os.path.join(out, sub))):
            with open(os.path.join(out, sub, f), "rb") as fh:
                report["sha256"]["%s/%s" % (sub, f)] = hashlib.sha256(fh.read()).hexdigest()
    if os.path.exists(os.path.join(gen, "blender_3q.png")):
        shutil.copyfile(os.path.join(gen, "blender_3q.png"), os.path.join(preview_dir, "blender_3q.png"))
    with open(os.path.join(work, "build_report.json"), "w") as f:
        json.dump(report, f, indent=1)
    print(json.dumps({"out": out, "rows": rows, "timing_s": timing, "proof_exit": p.returncode}, indent=1))
    print(p.stdout[-3000:])
    return p.returncode


if __name__ == "__main__":
    sys.exit(main())

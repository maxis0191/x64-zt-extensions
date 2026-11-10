"""Ship fitted hero outfits (heroes/fit/<hero>/export) as zone-ready IW7 assets.

python -I ship_heroes.py --config ship_heroes.example.json --out <dir> [--heroes aj,andre] [--skip-pack]

The config names local inputs. Its root values (stock_dump, techsets_dump, fit_root, lods_root, blender, texconv) may
contain ${NAME}: the environment variable NAME is put there, and a missing one stops the run with its name. A model's
"lods" paths that are not absolute resolve under lods_root. ship_heroes.example.json uses IWZ_DUMP, IWZ_HEROES,
IWZ_BLENDER and IWZ_TEXCONV (the same variables as the zombie kit).

Per hero: pack the fit textures (normal map green flipped: the fit bakes OpenGL +Y, stock IW7 packed_nog decodes as
DirectX +Y down, see hero_material.py normcheck), make the new materials (hero_material_zone.py, stock templates),
build body (lighting data transferred from the stock body LOD0), rigid hair / headwear and viewmodel arms
(build_model.py), optional cleaned stock head (surfaces dropped), and a manifest of models for the zone.
Output: <out>/kitdump (xmodel, xsurface), <out>/matroot (images, materials, techsets), <out>/manifest.json
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
sys.path.insert(0, HERE)
import xmodel  # noqa: E402
import xsurface  # noqa: E402


def run(cmd, log):
    with open(log, "w") as f:
        rc = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT).returncode
    if rc:
        raise SystemExit("FAILED (%d): %s (log %s)" % (rc, " ".join(cmd[:6]), log))


def strip_model(dump, src_name, new_name, drop, out):
    """Copy a stock xmodel and all its LOD surfaces without the surfaces whose material is in drop."""
    m = xmodel.read(open(os.path.join(dump, "xmodel", src_name + ".xmb"), "rb").read())
    mats, inv, lods = [], [], []
    for i in range(m.get("numLods")):
        lod = m.lod(i)
        ms = xsurface.read(open(os.path.join(dump, "xsurface", m.lod_surfs[i] + ".xsb"), "rb").read())
        keep = [k for k in range(lod[1]) if m.materials[lod[2] + k] not in drop]
        start = len(mats)
        new_surfs = []
        for k in keep:
            mats.append(m.materials[lod[2] + k])
            inv.append(m.inv_high_mip[lod[2] + k])
            new_surfs.append(ms.surfs[k])
        ms.surfs = new_surfs
        ms.name = "%s_lod%d" % (new_name, i)
        bits = set()
        for s in new_surfs:
            for w in range(8):
                for b in range(32):
                    if s.part_bits[w] & (0x80000000 >> b) & 0xFFFFFFFF:
                        bits.add(w * 32 + b)
        import vertex_codec as vc
        ms.part_bits = vc.part_bits(bits)
        open(os.path.join(out, "xsurface", ms.name + ".xsb"), "wb").write(xsurface.write(ms))
        lod[1], lod[2] = len(keep), start
        lod[4:12] = ms.part_bits
        lods.append((lod, ms.name))
    m.name = new_name
    m.materials = mats
    m.material_recs = None
    m.material_ptrs = b"\1" * 8 * len(mats)
    m.inv_high_mip = inv
    m.set("numsurfs", len(mats))
    for i, (lod, nm) in enumerate(lods):
        m.set_lod(i, lod)
        m.lod_surfs[i] = nm
    open(os.path.join(out, "xmodel", new_name + ".xmb"), "wb").write(xmodel.write(m))
    return {"model": new_name, "materials_per_lod": [l[0][1] for l in lods], "dropped": sorted(drop)}


ROOT_KEYS = ("stock_dump", "techsets_dump", "fit_root", "lods_root", "blender", "texconv")


def load_config(path, environ=None):
    """Read a ship config: put environment variables in the root values, resolve relative LOD paths."""
    environ = os.environ if environ is None else environ
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    missing = []

    def expand(match):
        value = environ.get(match.group(1))
        if not value:
            missing.append(match.group(1))
            return match.group(0)
        return value

    for key in ROOT_KEYS:
        if isinstance(cfg.get(key), str):
            cfg[key] = re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", expand, cfg[key])
    if missing:
        raise SystemExit("%s: set the environment variable(s) %s" % (path, ", ".join(sorted(set(missing)))))
    for hero in cfg.get("heroes", {}).values():
        for spec in hero.get("models", {}).values():
            lods = spec.get("lods") or []
            if any(not os.path.isabs(p) for p, _ in lods) and not cfg.get("lods_root"):
                raise SystemExit("%s: relative \"lods\" paths need the root value \"lods_root\"" % path)
            spec["lods"] = [[p if os.path.isabs(p) else os.path.join(cfg["lods_root"], p), d] for p, d in lods]
    return cfg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--heroes", default="")
    ap.add_argument("--skip-pack", action="store_true")
    a = ap.parse_args()
    cfg = load_config(a.config)
    out = a.out
    kit, matroot = os.path.join(out, "kitdump"), os.path.join(out, "matroot")
    for d in (os.path.join(kit, "xmodel"), os.path.join(kit, "xsurface"), matroot, os.path.join(out, "logs")):
        os.makedirs(d, exist_ok=True)
    dump = cfg["stock_dump"]
    manifest = {"models": [], "heroes": {}}
    heroes = a.heroes.split(",") if a.heroes else list(cfg["heroes"])
    for hero in heroes:
        h = cfg["heroes"][hero]
        fit = os.path.join(cfg["fit_root"], hero)
        tex = os.path.join(fit, "textures")
        packed = os.path.join(out, hero, "packed")
        os.makedirs(packed, exist_ok=True)
        rep = {"materials": {}, "models": {}}
        # 1. textures -> packed PNG -> BC7 DDS + material JSON (stock template)
        for part, spec in h["materials"].items():
            stem = "iwz_%s_%s" % (hero, part)
            if not a.skip_pack:
                cmd = [cfg["blender"], "-b", "--factory-startup", "-P", os.path.join(HERE, "hero_material.py"), "--",
                       "pack", "--albedo", os.path.join(tex, stem + "_albedo.png"),
                       "--normal", os.path.join(tex, stem + "_normal.png"), "--flip-green", "1",
                       "--roughness", os.path.join(tex, stem + "_roughness.png"),
                       "--ao", os.path.join(tex, stem + "_ao.png"),
                       "--reflectance", os.path.join(tex, stem + "_reflectance.png"),
                       "--pad", "1", "--ao-floor", str(cfg.get("ao_floor", 0.4)),
                       "--gloss-scale", str(cfg.get("gloss_scale", 0.6)), "--stem", stem, "--out", packed]
                run(cmd, os.path.join(out, "logs", "pack_%s.log" % stem))
            for mat_name, template in spec:
                cmd = [PY, "-I", os.path.join(HERE, "hero_material_zone.py"), "--techsets-dump", cfg["techsets_dump"],
                       "--template", template, "--name", mat_name,
                       "--cs", os.path.join(packed, stem + "_c_packed_cs.png"),
                       "--nog", os.path.join(packed, stem + "_n_packed_nog.png"),
                       "--texconv", cfg["texconv"], "--out", matroot]
                run(cmd, os.path.join(out, "logs", "mat_%s.log" % mat_name.replace("/", "_")))
                rep["materials"][mat_name] = template
        # 2. models
        for kind, spec in h["models"].items():
            mmap = os.path.join(out, "logs", "map_%s_%s.json" % (hero, kind))
            json.dump(spec["material_map"], open(mmap, "w"))
            cmd = [PY, "-I", os.path.join(HERE, "build_model.py"), os.path.join(fit, "export", "%s_%s.json" % (hero, kind)),
                   "--base-xmodel", os.path.join(dump, "xmodel", spec["base"] + ".xmb"), "--name", spec["name"],
                   "--out", kit, "--material-map", mmap,
                   "--report", os.path.join(out, "logs", "build_%s.json" % spec["name"])]
            if spec.get("lod_dist"):
                cmd += ["--lod-dist", str(spec["lod_dist"])]
            if spec.get("lods"):
                cmd += ["--lods", ",".join("%s:%s" % (p, d) for p, d in spec["lods"])]
            if spec.get("transfer_from"):
                cmd += ["--transfer-from", os.path.join(dump, "xsurface", spec["transfer_from"] + ".xsb")]
            run(cmd, os.path.join(out, "logs", "build_%s.log" % spec["name"]))
            rep["models"][kind] = json.load(open(os.path.join(out, "logs", "build_%s.json" % spec["name"])))
            manifest["models"].append(spec["name"])
        if h.get("clean_head"):
            ch = h["clean_head"]
            rep["models"]["head"] = strip_model(dump, ch["base"], ch["name"], set(ch["drop"]), kit)
            manifest["models"].append(ch["name"])
        manifest["heroes"][hero] = rep
        print("HERO_OK", hero, json.dumps({k: [s["material"] for s in v.get("surfaces", [])] if "surfaces" in v else v
                                           for k, v in rep["models"].items()}))
    json.dump(manifest, open(os.path.join(out, "manifest.json"), "w"), indent=1)


if __name__ == "__main__":
    main()

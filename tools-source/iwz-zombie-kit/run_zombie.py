"""One-command zombie outfit pipeline (system Python, stdlib only).

python -I run_zombie.py --config configs/zombie_<id>.json [--quick] [--reuse-fit] [--skip-fit] [--out-root <dir>]

1. Blender fit_zombie.py -> <out>/<id>_parts.blend + textures + fit_report.json (export objects per part)
2. writer blender_export.py per export object -> export/<name>.json
3. writer build_model.py (base = the stock part xmodel: skeleton, physics preset of the gibs) -> kitdump/xmodel,xsurface
4. writer hero_material.py pack (body + head) -> textures/packed/*_packed_cs/nog.png
5. writer hero_material_zone.py: mo/<prefix>_body (template mo/zmb_<gender>_body), mo/<prefix>_head (template the stock
   head material, emissive rebound to black), semantic 16 packed_a -> white -> matroot/ (images, materials, techsets)
6. scriptables: clone_scriptable.py zombie_<gender>_outfit_1 -> zombie_iwz_<id> with the new part model names
Writes export/run_summary.json (models list for staging, material root, scriptable path).
"""
import argparse
import json
import os
import struct
import subprocess
import sys
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
HEROES = r"C:\Users\ezvalo\Documents\IW7-Runtime\iwz-stage2\heroes"
BLENDER = os.environ.get("IWZ_BLENDER", r"C:\Users\ezvalo\Documents\IW7-Tools\blender-4.5.15\blender-4.5.15-windows-x64\blender.exe")
WRITER = os.environ.get("IWZ_WRITER", os.path.join(os.path.dirname(HERE), "iw7-skinned-writer"))
DUMP = r"C:\Users\ezvalo\Documents\IW7-Runtime\iwz-map-ref-a\dump"
TEXCONV = r"C:\Users\ezvalo\Documents\IW7-Tools\texconv-may2026\texconv.exe"
GENDER = {
    "male": {"body_template": "mo/zmb_male_body", "head_template": "mo/zmb_male_head_01",
             "scriptable": "zombie_male_outfit_1",
             "swap": {"torso": "zmb_male_normal_torso_outfit_01", "arm_l": "zmb_male_normal_arm_l_outfit_01",
                      "arm_r": "zmb_male_normal_arm_r_outfit_01", "leg_l": "zmb_male_normal_leg_l_outfit_01",
                      "leg_r": "zmb_male_normal_leg_r_outfit_01", "head": "zmb_male_head_01",
                      "head2": "zmb_male_head_02",
                      "damaged_arm_l": "zmb_male_damaged_arm_l_outfit_01", "damaged_arm_r": "zmb_male_damaged_arm_r_outfit_01",
                      "damaged_leg_l": "zmb_male_damaged_leg_l_outfit_01", "damaged_leg_r": "zmb_male_damaged_leg_r_outfit_01",
                      "damaged_head": "zmb_male_head_01_damaged"}},
    "female": {"body_template": "mo/zmb_female_body", "head_template": "mo/zmb_head_female_01_head",
               "scriptable": "zombie_female_outfit_1",
               "swap": {"torso": "zmb_female_normal_torso_outfit_01", "arm_l": "zmb_female_normal_arm_l",
                        "arm_r": "zmb_female_normal_arm_r", "leg_l": "zmb_female_normal_leg_l_outfit_01",
                        "leg_r": "zmb_female_normal_leg_r_outfit_01", "head": "zmb_female_head_01",
                        "head2": "zmb_female_head_02",
                        "damaged_arm_l": "zmb_female_damaged_arm_l", "damaged_arm_r": "zmb_female_damaged_arm_r",
                        "damaged_leg_l": "zmb_female_damaged_leg_l_outfit_01", "damaged_leg_r": "zmb_female_damaged_leg_r_outfit_01",
                        "damaged_head": "zmb_female_head_01_damaged"}},
}


def run(cmd, log):
    t = time.time()
    with open(log, "w", encoding="utf-8", errors="replace") as fh:
        r = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT)
    tail = open(log, encoding="utf-8", errors="replace").read().splitlines()[-4:]
    print("[run] rc=%d %.0fs %s" % (r.returncode, time.time() - t, os.path.basename(log)), flush=True)
    for line in tail:
        print("   ", line[:220])
    return r.returncode


def png_const(path, rgba, size=64):
    """tiny constant-colour RGBA PNG (stdlib)."""
    raw = b"".join(b"\0" + bytes(rgba) * size for _ in range(size))
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)) + \
        chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    open(path, "wb").write(png)
    return path


def lod0_xsb(name):
    d = os.path.join(DUMP, "cp_zmb", "xsurface")
    c = [f for f in os.listdir(d) if f.startswith(name + "_lod0") and "auto" not in f[len(name):]]
    return os.path.join(d, c[0]) if c else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--reuse-fit", action="store_true")
    ap.add_argument("--skip-fit", action="store_true")
    ap.add_argument("--only", default="", help="comma list of steps: fit,export,build,pack,mat,scriptable")
    a = ap.parse_args()
    cfgp = os.path.abspath(a.config)
    cfg = json.load(open(cfgp))
    zid = cfg["zombie"]
    g = GENDER[cfg["gender"]]
    out = cfg.get("out_dir", os.path.join("zombies", "fit", zid))
    out = out if os.path.isabs(out) else os.path.join(HEROES, out)
    exp = os.path.join(out, "export")
    os.makedirs(exp, exist_ok=True)
    steps = set(a.only.split(",")) if a.only else {"fit", "export", "build", "pack", "mat", "scriptable"}
    if a.skip_fit:
        steps.discard("fit")
    py = sys.executable
    summary = {"zombie": zid, "config": cfgp, "steps": {}}
    if "fit" in steps:
        cmd = [BLENDER, "-b", "--factory-startup", "-P", os.path.join(HERE, "fit_zombie.py"), "--", "--config", cfgp]
        if a.quick:
            cmd.append("--quick")
        if a.reuse_fit:
            cmd.append("--reuse-fit")
        rc = run(cmd, os.path.join(out, "fit.log"))
        if rc == 0 and "ZFIT_DONE" not in open(os.path.join(out, "fit.log"), encoding="utf-8", errors="replace").read():
            rc = 9
        summary["steps"]["fit"] = rc
        if rc:
            return rc
    rep = json.load(open(os.path.join(out, "fit_report.json")))
    prefix = cfg.get("name_prefix", "zmb_iwz_%s" % zid.lower())
    mats = rep["materials"]
    mo_body = "mo/%s_body" % prefix
    mo_head = "mo/%s_head" % prefix
    mmap = {mats["body"]: mo_body, mats["head"]: mo_head, "zmb_dismembered_caps": "mo/zmb_dismembered_caps"}
    mmap_path = os.path.join(exp, "material_map.json")
    json.dump(mmap, open(mmap_path, "w"), indent=1)
    kit = os.path.join(out, "kitdump")
    models = []
    for name, e in rep["export"].items():
        js = os.path.join(exp, name + ".json")
        if "export" in steps:
            rc = run([BLENDER, "-b", "--factory-startup", rep["blend"], "-P", os.path.join(WRITER, "blender_export.py"), "--",
                      "--out", js, "--objects", e["object"]], os.path.join(exp, "export_%s.log" % name))
            summary["steps"]["export_" + name] = rc
            if rc:
                continue
        if "build" in steps:
            rp = os.path.join(exp, "build_%s_report.json" % name)
            cmd = [py, "-I", os.path.join(WRITER, "build_model.py"), js, "--base-xmodel",
                   os.path.join(DUMP, "cp_zmb", "xmodel", e["base"] + ".xmb"), "--name", name, "--out", kit,
                   "--report", rp, "--material-map", mmap_path]
            rc = run(cmd, os.path.join(exp, "build_%s.log" % name))
            summary["steps"]["build_" + name] = rc
            if rc == 0 and os.path.exists(rp):
                summary.setdefault("build", {})[name] = json.load(open(rp))
        models.append(name)
    summary["models"] = models
    pk = os.path.join(out, "textures", "packed")
    os.makedirs(pk, exist_ok=True)
    stems = {mats["body"]: prefix + "_body", mats["head"]: prefix + "_head"}
    if "pack" in steps:
        for mat, maps in rep["textures"].items():
            cmd = [BLENDER, "-b", "--factory-startup", "-P", os.path.join(WRITER, "hero_material.py"), "--", "pack",
                   "--albedo", maps["albedo"], "--normal", maps["normal"], "--roughness", maps["roughness"],
                   "--ao", maps["ao"], "--reflectance", maps["reflectance"], "--stem", stems[mat], "--out", pk]
            summary["steps"]["pack_" + mat] = run(cmd, os.path.join(pk, "pack_%s.log" % mat))
    matroot = os.path.join(out, "matroot")
    if "mat" in steps:
        white = png_const(os.path.join(pk, "zmb_iwz_white_packed_a.png"), (255, 255, 255, 255))
        black = png_const(os.path.join(pk, "zmb_iwz_black_e.png"), (0, 0, 0, 255))
        for mat, tpl, mo, extra in ((mats["body"], g["body_template"], mo_body, ["16=" + white]),
                                    (mats["head"], g["head_template"], mo_head, ["2=" + black, "16=" + white])):
            st = stems[mat]
            cmd = [py, "-I", os.path.join(WRITER, "hero_material_zone.py"), "--techsets-dump",
                   os.path.join(DUMP, "techsets_cp_zmb"), "--template", tpl, "--name", mo,
                   "--cs", os.path.join(pk, st + "_c_packed_cs.png"), "--nog", os.path.join(pk, st + "_n_packed_nog.png"),
                   "--texconv", TEXCONV, "--out", matroot]
            for x in extra:
                cmd += ["--tex", x]
            summary["steps"]["mat_" + mat] = run(cmd, os.path.join(pk, "matzone_%s.log" % mat))
    summary["matroot"] = matroot
    summary["materials"] = [mo_body, mo_head]
    if "scriptable" in steps:
        sw = g["swap"]
        nm = {"torso": prefix + "_normal_torso", "arm_l": prefix + "_normal_arm_l", "arm_r": prefix + "_normal_arm_r",
              "leg_l": prefix + "_normal_leg_l", "leg_r": prefix + "_normal_leg_r", "head": prefix + "_head",
              "head2": prefix + "_head", "damaged_arm_l": prefix + "_damaged_arm_l",
              "damaged_arm_r": prefix + "_damaged_arm_r", "damaged_leg_l": prefix + "_damaged_leg_l",
              "damaged_leg_r": prefix + "_damaged_leg_r", "damaged_head": prefix + "_head_damaged"}
        swap = {sw[k]: nm[k] for k in sw}
        sname = "zombie_iwz_%s" % zid.lower()
        swap[g["scriptable"]] = sname
        sdir = os.path.join(out, "scriptable")
        os.makedirs(sdir, exist_ok=True)
        mp = os.path.join(sdir, sname + "_map.json")
        spec = {"swap": swap, "hair_to": "zmb_female_head_hair_nodraw", "hair_prefixes": ["zmb_male_head_0", "zmb_head_0",
                                                                                            "zmb_female_head_0"]}
        json.dump(spec, open(mp, "w"), indent=1)
        rc = run([py, "-I", os.path.join(HERE, "clone_scriptable.py"), os.path.join(DUMP, "cp_zmb", "scriptable", g["scriptable"]),
                  os.path.join(sdir, sname), mp], os.path.join(sdir, "clone.log"))
        summary["steps"]["scriptable"] = rc
        summary["scriptable"] = os.path.join(sdir, sname)
    json.dump(summary, open(os.path.join(exp, "run_summary.json"), "w"), indent=1)
    print("RUN_DONE", zid, json.dumps(summary["steps"]))
    return 0 if all(v == 0 for v in summary["steps"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())

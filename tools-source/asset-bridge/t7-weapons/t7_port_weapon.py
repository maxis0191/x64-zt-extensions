"""Port one BO3 (T7) weapon to IW7 in one command: every asset it uses, from the BO3 data.

    python t7_port_weapon.py --config port-config.json --weapon thundergun_zm --out <dir>

Nothing here names a weapon. Each stage reads the spec that t7_weapon_spec.py
builds from the BO3 WeaponDef (and, when the scan holds it, the spec of its
``_upgraded_zm`` twin for Pack-a-Punch), then runs the bridge tool of that
asset family. Stages write under ``--out``:

  spec     spec.json (+ spec_upgraded.json)
  export   GrayWolf (MCP, scripted): view/world models of both specs with PNG
           images; the effects' materials; the sound files of every alias
  materials  t7_material_pack.py -> zone/materials, zone/images (texture cap)
  models   ZoneTool-converted xmodel/xsurface copied, normals checked
  anims    t7_vm_retarget.py onto the IW7 view hands, ADS aim from the BO3
           ADS raise, long-anim layout checked
  sounds   t7_weapon_sound.py for the weapon's aliases and anim notetracks
  fx       effects of both specs and their linked effects:
           t7_fx_material_pack.py then t7_fx_to_iw7.py (stock emitter library)
  author   iw7_weapon_author.py + vfx/sfx packages + BO3 kick (+ _pap1 and
           its two attachments from the upgraded spec)
  zone     zone.csv (lines for the mod zone) and catalog.txt (module entry)

The config file names the machine's inputs (BO3 install, GrayWolf, texconv,
the zone snapshot folder of t7_zone_snapshot.py, ZoneTool T7->IW7 dumps,
stock IW7 dumps, hands); see
port-config.example.json. Stages can be run alone (--stages) and each one
records what it wrote in manifest.json.
"""
import argparse
import csv
import glob
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import t7_weapon_scripts  # noqa: E402
import t7_weapon_spec  # noqa: E402

STAGES = ["spec", "scripts", "export", "materials", "models", "anims", "sounds", "fx", "author", "zone"]
# Stock IW7 templates (relative to the stock dump root), chosen once for every weapon.
TEMPLATES = {
    "weapon": "weapons/iw7_facemelter_zm.json",
    "projectile": "weapons/iw7_zapper_grey.json",
    "animpkg": "animpkg/iw7_zapper_mp_package.json",
    "sfxpkg": "sfxpkg/iw7_facemelter_mp_sfxpackage.json",
    "pap_attachment": "attachments/fmpap1.json",
    "aliases": "sound/cp_zmb.all.aliases.csv",
}
MATERIAL_TEMPLATES = {   # relative to the stock material root
    "opaque": "m2o/weapon_ar57_sight.json",
    "emissive": "m2o/attachment_thermalhybrid.json",
    "blend": "m2o/weapon_zappers_headcutter_glass.json",
    "fx_add": "eq/gfx_flare_wtr.json",
    "fx_blend": "eq/vfx_pyro_flash_ark_green_p.json",
    "fx_add_atlas": "eq/vfx_pyro_fire_inferno_burst_short_1_anim_0z.json",
    "fx_blend_atlas": "eq/vfx_pyro_fire_flame_base_smoky.json",
}
# Stock emitters every converted element is cloned from (all fields are rewritten).
FX_TEMPLATES = {
    "sprite": ("particlesystem/vfx/iw7/core/zombie/weapon/impact/vfx_zmb_impact_green_ch1.iw7VFX", 2),
    "sprite_atlas": ("particlesystem/vfx/iw7/core/zombie/weapon/impact/vfx_zmb_impact_green_ch1.iw7VFX", 5),
    "tail": ("particlesystem/vfx/iw7/core/zombie/weapon/impact/vfx_zmb_impact_green_ch1.iw7VFX", 3),
    "light": ("particlesystem/vfx/iw7/core/zombie/weapon/impact/vfx_zmb_impact_green_ch1.iw7VFX", 1),
    "trail": ("particlesystem/vfx/iw7/_requests/mp/vfx_plasma_trail_friendly.iw7VFX", 1),
}
FX_LINK_KEYS = ("effect_",)   # element slots that name another effect (runners, emitted effects)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)


def run(cmd, **kw):
    print("+ " + " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def with_snapshot(cfg):
    """``snapshots`` (t7_zone_snapshot.py output folder) supplies ``scan``/``effects`` for ``zone``."""
    cfg = dict(cfg)
    if cfg.get("snapshots") and cfg.get("zone"):
        base = os.path.join(cfg["snapshots"], cfg["zone"])
        cfg.setdefault("scan", base + ".weapons.json")
        cfg.setdefault("effects", base + ".effects.json")
    return cfg


class Port:
    def __init__(self, cfg, weapon, out, name=None):
        cfg = with_snapshot(cfg)
        self.cfg, self.weapon, self.out = cfg, weapon, os.path.abspath(out)
        self.zone = os.path.join(self.out, "zone")
        self.name = name
        self.manifest_path = os.path.join(self.out, "manifest.json")
        self.manifest = load(self.manifest_path) if os.path.exists(self.manifest_path) else {"weapon": weapon, "stages": {}}

    # -- helpers ---------------------------------------------------------------------------
    def specs(self):
        out = [load(os.path.join(self.out, "spec.json"))]
        up = os.path.join(self.out, "spec_upgraded.json")
        if os.path.exists(up):
            out.append(load(up))
        return out

    def record(self, stage, data):
        self.manifest["stages"][stage] = data
        save(self.manifest_path, self.manifest)

    def stock(self, rel):
        return os.path.join(self.cfg["iw7_dump"], rel)

    def py(self, tool):
        return [self.cfg.get("python", sys.executable), "-B", os.path.join(HERE, tool)]

    def graywolf(self):
        import graywolf_mcp
        return graywolf_mcp.GrayWolf(self.cfg["graywolf"])

    def gw_export(self, gw, out_name, args):
        # GrayWolf keeps writing into an existing output folder: give each port its own, emptied first.
        gw_name = "t7port-%s-%s" % (self.weapon, out_name)
        stale = os.path.join(os.environ.get("LOCALAPPDATA", ""), "GrayWolf", "mcp", gw_name)
        if os.path.isdir(stale):
            shutil.rmtree(stale)
        args = dict(args, install=self.cfg["bo3_install"], out_name=gw_name, wait=True)
        result = gw.call("graywolf_export", args)
        if result.get("failures"):
            raise SystemExit("GrayWolf %s: %s" % (out_name, result["failures"]))
        folder = result.get("out") or os.path.join(gw_root(result), gw_name)
        dest = os.path.join(self.out, "gw", out_name)
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        shutil.copytree(folder, dest)    # GrayWolf output folders can vanish later
        game = os.path.join(dest, "bo3")  # GrayWolf nests its output under the game id
        return (game if os.path.isdir(game) else dest), result

    def gw_dir(self, out_name):
        dest = os.path.join(self.out, "gw", out_name)
        game = os.path.join(dest, "bo3")
        return game if os.path.isdir(game) else dest

    def alias_table(self):
        return os.path.join(self.out, "aliases.csv")

    def export_alias_tables(self, gw):
        """One alias table for the port: every sound zone's table, the first zone defining an alias wins.
        Returns {alias: zone}."""
        owner, header, rows = {}, None, []
        for i, zone in enumerate(self.cfg.get("sound_zones") or [self.cfg["sound_zone"]]):
            d, _ = self.gw_export(gw, "aliases_%d" % i, {"zones": [zone], "kinds": ["sound"], "sound_aliases": True,
                                                         "name_filter": ["zzzz_alias_table_only"]})
            for path in glob.glob(os.path.join(d, "sounds", "*.csv")):
                with open(path, encoding="utf-8", newline="") as f:
                    table = list(csv.reader(f))
                header = header or table[0]
                fresh = {r[0] for r in table[1:] if r and r[0] not in owner}
                for r in table[1:]:
                    if r and r[0] in fresh:
                        rows.append(r)
                owner.update({n: zone for n in fresh})
        with open(self.alias_table(), "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerows([header] + rows)
        _ALIASES.pop(self.alias_table(), None)
        return owner

    # -- stages ----------------------------------------------------------------------------
    def stage_spec(self):
        scan = load(self.cfg["scan"])
        spec = t7_weapon_spec.build(scan, self.weapon, self.cfg.get("zone"), self.name)
        save(os.path.join(self.out, "spec.json"), spec)
        written = ["spec.json"]
        if spec["upgrade"]:
            up = t7_weapon_spec.build(scan, spec["upgrade"], self.cfg.get("zone"), spec["name"] + "_pap1")
            save(os.path.join(self.out, "spec_upgraded.json"), up)
            written.append("spec_upgraded.json")
        self.record("spec", {"written": written, "upgrade": spec["upgrade"]})

    def stage_scripts(self):
        """BO3 scripts behind the weapon (decompiled once per zone into the script cache)."""
        bases = [s["base"] for s in self.specs() if s.get("base")]
        picked, info = [], {}
        dest = os.path.join(self.out, "scripts")
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        for zone in self.cfg.get("script_zones") or [self.cfg["model_zone"]]:
            root = self.decompiled_scripts(zone)
            sources = t7_weapon_scripts.load_sources(root)
            for rel in t7_weapon_scripts.select(sources, bases):
                path = os.path.join(dest, *rel.split("/"))
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(sources[rel])
                picked.append(rel)
                info[rel] = t7_weapon_scripts.extract(sources[rel])
        self.record("scripts", {"scripts": picked, "found": info})

    def decompiled_scripts(self, zone):
        cache = os.path.join(self.cfg.get("script_cache", os.path.join(self.out, "..", "_scripts")),
                             os.path.splitext(os.path.basename(zone))[0])
        done = os.path.join(cache, "decompiled", "t7")
        if os.path.isdir(done):
            return done
        with self.graywolf() as gw:
            d, _ = self.gw_export(gw, "scripts", {"zones": [zone], "kinds": ["script"]})
        if os.path.isdir(cache):
            shutil.rmtree(cache)
        shutil.copytree(os.path.join(d, "scripts"), cache)
        # one pass decompiles both .gscc and .cscc (gsc-tool exits non-zero with -i client)
        run([self.cfg["gsc_tool"], "-m", "decomp", "-g", "t7", "-s", "pc", "."], cwd=cache, stdout=subprocess.DEVNULL)
        return done

    def stage_export(self):
        specs = self.specs()
        models = sorted({s[k] for s in specs for k in ("view_model", "world_model") if s.get(k)})
        effects = self.effect_closure(specs)
        fx_materials = sorted({e["visual"]["name"] for name in effects for e in self.effects()[name]["elements"]
                               if (e.get("visual") or {}).get("kind") == "material"})
        with self.graywolf() as gw:
            mdir, _ = self.gw_export(gw, "models", {
                "zones": [self.cfg["model_zone"]], "assets": ["model:" + m for m in models],
                "model_format": ["xmodel_export"], "image_format": "png"})
            fdir, _ = self.gw_export(gw, "fx_materials", {
                "zones": [self.cfg["model_zone"]], "assets": ["material:" + m for m in fx_materials],
                "image_format": "png"}) if fx_materials else (None, None)
            owner = self.export_alias_tables(gw)
            aliases = self.sound_aliases(specs)
            files = {}
            for alias, path in self.sound_files(aliases):
                files.setdefault(owner.get(alias), set()).add(path)
            root = os.path.join(self.out, "sounds")
            if os.path.isdir(root):
                shutil.rmtree(root)
            for i, (zone, paths) in enumerate(sorted(files.items(), key=lambda kv: str(kv[0]))):
                d, _ = self.gw_export(gw, "sounds_%d" % i, {
                    # GrayWolf ignores "assets" for sounds; name_filter matches the file base name.
                    "zones": [zone], "kinds": ["sound"], "audio_format": "flac",
                    "name_filter": sorted({sound_stem(p) for p in paths})})
                shutil.copytree(os.path.join(d, "sounds"), root, dirs_exist_ok=True)
        self.record("export", {"models": models, "fx_materials": fx_materials, "aliases": aliases,
                               "sound_files": sorted(p for ps in files.values() for p in ps)})

    def stage_materials(self):
        root = self.cfg["iw7_materials"]
        written = []
        for mj in sorted(glob.glob(os.path.join(self.out, "gw", "models", "**", "*_LOD0.materials.json"), recursive=True)):
            run(self.py("t7_material_pack.py") + [
                mj, "--template", os.path.join(root, MATERIAL_TEMPLATES["opaque"]),
                "--emissive-template", os.path.join(root, MATERIAL_TEMPLATES["emissive"]),
                "--blend-template", os.path.join(root, MATERIAL_TEMPLATES["blend"]),
                "--texconv", self.cfg["texconv"], "--out", self.zone, "--max-size", self.cfg.get("max_texture", 512)],
                stdout=subprocess.DEVNULL)
            written.append(os.path.relpath(mj, self.out))
        # The asset name is the file path under materials/: put each one where the converted models
        # reference it (BO3 weapon models name their materials "mc/<name>").
        mdir = os.path.join(self.zone, "materials")
        for ref in self.model_material_refs():
            folder, base = ref.rsplit("/", 1) if "/" in ref else ("", ref)
            flat = os.path.join(mdir, base + ".json")
            if folder and os.path.exists(flat):
                os.makedirs(os.path.join(mdir, folder), exist_ok=True)
                os.replace(flat, os.path.join(mdir, folder, base + ".json"))
        self.record("materials", {"from": written, "materials": sorted(
            os.path.relpath(p, os.path.join(self.zone, "materials")).replace("\\", "/")[:-5]
            for p in glob.glob(os.path.join(self.zone, "materials", "**", "*.json"), recursive=True))})

    def stage_models(self):
        src = self.cfg["t7_models"]
        models = sorted({s[k] for s in self.specs() for k in ("view_model", "world_model") if s.get(k)})
        copied = []
        for m in models:
            xmb = os.path.join(src, "xmodel", m + ".xmb")
            if not os.path.exists(xmb):
                raise SystemExit("model %s not converted under %s (run ZoneTool -dumpzoneto iw7)" % (m, src))
            dst = os.path.join(self.zone, "xmodel")
            os.makedirs(dst, exist_ok=True)
            shutil.copy2(xmb, dst)
            for xsb in glob.glob(os.path.join(src, "xsurface", m + "*.xsb")):
                os.makedirs(os.path.join(self.zone, "xsurface"), exist_ok=True)
                shutil.copy2(xsb, os.path.join(self.zone, "xsurface"))
                run(self.py("iw7_xsurface_check.py") + [xsb], stdout=subprocess.DEVNULL)
            copied.append(m)
        self.record("models", {"models": copied})

    def stage_anims(self):
        specs = self.specs()
        names = sorted({a for s in specs for a in s["anims"].values()})
        src = [os.path.join(self.cfg["t7_anims"], n + ".xab") for n in names]
        missing = [p for p in src if not os.path.exists(p)]
        if missing:
            raise SystemExit("anims not converted: %s" % missing)
        out = os.path.join(self.zone, "xanim")
        a = specs[0]["anims"]
        cmd = self.py("t7_vm_retarget.py") + ["--source-hands", self.cfg["bo3_hands_xmb"],
                                              "--target-hands", self.cfg["iw7_hands_xmb"], "--out", out]
        if "ads_up" in a and "ads_down" in a and "idle" in a:
            mesh = glob.glob(os.path.join(self.out, "gw", "models", "**", specs[0]["view_model"] + "_LOD0.XMODEL_EXPORT"),
                             recursive=True)
            if not mesh:
                raise SystemExit("view model export missing: run the export stage")
            gun = ads_gun_from_mesh(mesh[0])
            cmd += ["--ads-gun", ",".join("%.3f" % v for v in gun), "--ads-idle", a["idle"],
                    "--ads-up", a["ads_up"], "--ads-down", a["ads_down"]]
            self.manifest["ads_gun"] = gun
        run(cmd + src, stdout=subprocess.DEVNULL)
        run(self.py("iw7_xanim_layout.py") + [os.path.join(out, n + ".xab") for n in names], stdout=subprocess.DEVNULL)
        self.record("anims", {"anims": names})

    def stage_sounds(self):
        aliases = self.sound_aliases(self.specs())
        # One alias table per weapon (sound/<weapon>.aliases.csv); the mod assembly merges them into the
        # mod zone's single sound bank.
        out = run(self.py("t7_weapon_sound.py") + [
            "--bo3-aliases", self.alias_table(), "--flac-root", os.path.join(self.out, "sounds"),
            "--template", self.stock(TEMPLATES["aliases"]), "--out", self.zone,
            "--bank", self.specs()[0]["name"], "--zone", self.cfg.get("mod_zone", "bo3wpn"),
            "--prefix", "%s/%s" % (self.cfg.get("sound_prefix", "t7"), self.weapon), "--alias"] + aliases
            + [x for alias, role in self.sound_roles().items() for x in ("--role", "%s=%s" % (alias, role))],
            stdout=subprocess.PIPE, text=True)
        report = json.loads(out.stdout)["aliases"]
        self.record("sounds", {"aliases": [r["alias"] for r in report if not r.get("silent")],
                               "silent": [r["alias"] for r in report if r.get("silent")]})

    def stage_fx(self):
        specs = self.specs()
        effects = self.effect_closure(specs)
        report = os.path.join(self.out, "fx_materials.json")
        root = self.cfg["iw7_materials"]
        with open(report, "w", encoding="utf-8") as f:
            run(self.py("t7_fx_material_pack.py") + [
                "--materials", self.gw_dir("fx_materials"), "--effects", self.cfg["effects"],
                "--add-template", os.path.join(root, MATERIAL_TEMPLATES["fx_add"]),
                "--blend-template", os.path.join(root, MATERIAL_TEMPLATES["fx_blend"]),
                "--add-atlas-template", os.path.join(root, MATERIAL_TEMPLATES["fx_add_atlas"]),
                "--blend-atlas-template", os.path.join(root, MATERIAL_TEMPLATES["fx_blend_atlas"]),
                "--texconv", self.cfg["texconv"], "--out", self.zone, "--name-prefix", "t7_",
                "--max-size", self.cfg.get("max_texture", 512)], stdout=f)
        cmd = self.py("t7_fx_to_iw7.py") + ["--effects", self.cfg["effects"], "--materials", report,
                                            "--out", self.zone, "--intensity-add", self.cfg.get("fx_intensity_add", 2.0)]
        for kind, (rel, index) in FX_TEMPLATES.items():
            cmd += ["--template", "%s=%s:%d" % (kind, self.stock(rel), index)]
        for e in effects:
            cmd += ["--map", "%s=%s" % (e, t7_weapon_spec.iw7_fx_name(e))]
        with open(os.path.join(self.out, "fx_report.json"), "w", encoding="utf-8") as f:
            run(cmd, stdout=f)
        self.record("fx", {"effects": effects})

    def stage_author(self):
        import iw7_weapon_author as author
        specs = self.specs()
        tpl = {k: load(self.stock(v)) for k, v in TEMPLATES.items() if k != "aliases"}
        written, missing = [], set()
        for i, spec in enumerate(specs):
            silent = set(self.manifest["stages"].get("sounds", {}).get("silent", []))
            # only effects the fx stage wrote are referenced: a dangling name fails the zone build
            built = {r: f for r, f in spec["fx"].items() if os.path.exists(
                os.path.join(self.zone, "particlesystem", *f["iw7"].split("/")) + ".iw7VFX")}
            missing.update(f["bo3"] for r, f in spec["fx"].items() if r not in built)
            proj = {k: v for k, v in spec["projectile"].items()
                    if not (k.endswith("Effect") and v not in {f["iw7"] for f in built.values()})}
            # BO3 anim notetracks carry the alias name: IW7 maps notetrack -> alias per weapon
            notetracks = {a: a for a in self.notetrack_sounds([spec]) if a not in silent}
            spec = dict(spec, xab_dir=os.path.join(self.zone, "xanim"), fx=built, projectile=proj,
                        notetrack_sounds=notetracks,
                        sounds={k: v for k, v in spec["sounds"].items() if v not in silent})
            w, pkg = author.author(spec, tpl["weapon"], tpl["animpkg"], tpl["projectile"])
            d = w["weapDef"]
            d.update(spec["kick"])
            d["vfxPackage"] = spec["name"] + "_vfxpackage"
            d["sfxPackage"] = spec["name"] + "_sfxpackage"
            save(os.path.join(self.zone, "weapons", spec["name"] + ".json"), w)
            save(os.path.join(self.zone, "animpkg", spec["name"] + "_package.json"), pkg)
            save(os.path.join(self.zone, "vfxpkg", spec["name"] + "_vfxpackage.json"), vfx_package(spec))
            save(os.path.join(self.zone, "sfxpkg", spec["name"] + "_sfxpackage.json"), sfx_package(spec, tpl["sfxpkg"]))
            written.append(spec["name"])
        if len(specs) == 2:
            base, up = specs
            atts = [base["name"].replace("iw7_", "")[:8] + "pap1", base["name"].replace("iw7_", "")[:8] + "pap2"]
            weapons = {}
            for spec in specs:
                path = os.path.join(self.zone, "weapons", spec["name"] + ".json")
                weapons[spec["name"]] = w = load(path)
                w["attachments6"] = atts
                save(path, w)
            for att in atts:
                save(os.path.join(self.zone, "attachments", att + ".json"),
                     pap_attachment(tpl["pap_attachment"], att, weapons[up["name"]]))
            self.manifest["pap"] = {"weapon": up["name"], "attachments": atts}
        self.record("author", {"weapons": written, "effects_not_built": sorted(missing)})

    def stage_zone(self):
        lines = []
        m = self.manifest["stages"]
        for mat in m.get("materials", {}).get("materials", []):
            lines.append("material," + mat)
        for mdl in m.get("models", {}).get("models", []):
            lines.append("xmodel," + mdl)
        for a in m.get("anims", {}).get("anims", []):
            lines.append("xanim," + a)
        for e in m.get("fx", {}).get("effects", []):
            lines.append("vfx," + t7_weapon_spec.iw7_fx_name(e))
        specs = self.specs()
        for s in specs:
            lines += ["animpkg,%s_package" % s["name"], "sfxpkg,%s_sfxpackage" % s["name"],
                      "vfxpkg,%s_vfxpackage" % s["name"]]
        pap = self.manifest.get("pap")
        if pap:
            lines += ["attachment," + a for a in pap["attachments"]]
        lines += ["weapon," + s["name"] for s in specs]
        with open(os.path.join(self.out, "zone.csv"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        # weapon[:pap weapon:pap1 attachment:pap2 attachment], one module catalog string
        entry = specs[0]["name"]
        if pap:
            entry += ":%s:%s:%s" % (pap["weapon"], pap["attachments"][0], pap["attachments"][1])
        with open(os.path.join(self.out, "catalog.txt"), "w", encoding="utf-8") as f:
            f.write(entry + "\n")
        built = {e for e in m.get("fx", {}).get("effects", []) if os.path.exists(
            os.path.join(self.zone, "particlesystem", *t7_weapon_spec.iw7_fx_name(e).split("/")) + ".iw7VFX")}
        sounds = set(m.get("sounds", {}).get("aliases", []))
        behaviours = behaviour_lines([s["name"] for s in specs], m.get("scripts", {}).get("found", {}), built, sounds)
        with open(os.path.join(self.out, "behaviour.txt"), "w", encoding="utf-8") as f:
            f.write("".join(b + "\n" for b in behaviours))
        self.record("zone", {"lines": len(lines), "catalog": entry, "behaviours": behaviours})

    # -- data ------------------------------------------------------------------------------
    def model_material_refs(self):
        """Material names the ZoneTool-converted models reference (strings in the .xmb)."""
        refs = set()
        for s in self.specs():
            for key in ("view_model", "world_model"):
                path = os.path.join(self.cfg["t7_models"], "xmodel", (s.get(key) or "") + ".xmb")
                if s.get(key) and os.path.exists(path):
                    with open(path, "rb") as f:
                        data = f.read()
                    refs.update(m.decode() for m in re.findall(rb"[a-z0-9_]+/mtl_[a-z0-9_]+", data))
        return sorted(refs)

    _effects = None

    def effects(self):
        if Port._effects is None:
            data = load(self.cfg["effects"])
            Port._effects = data.get("effects", data)
        return Port._effects

    def effect_closure(self, specs):
        """Effects of the specs plus every effect their elements link to (runners, emitted effects)."""
        all_fx = self.effects()
        todo = [f["bo3"] for s in specs for f in s["fx"].values()]
        # effects the weapon's scripts play (Thundergun blast, DG-2 view-model rail and tubes, arcs)
        for found in self.manifest["stages"].get("scripts", {}).get("found", {}).values():
            todo += list(found["effects"].values())
        seen = []
        while todo:
            name = todo.pop(0)
            if name in seen or name not in all_fx:
                continue
            seen.append(name)
            for e in all_fx[name]["elements"]:
                for key, ref in e.items():
                    if key.startswith(FX_LINK_KEYS) and isinstance(ref, dict) and ref.get("kind") == "fx":
                        todo.append(ref["name"])
        return seen

    def sound_aliases(self, specs):
        names = [a for s in specs for a in s["sounds"].values()]
        for n in self.notetrack_sounds(specs):
            names.append(n)
        names += self.script_sounds()
        return list(dict.fromkeys(n for n in names if n))

    def script_sounds(self):
        """Aliases the weapon's scripts play that the zone's alias table defines."""
        rows = alias_rows(self.alias_table())
        found = self.manifest["stages"].get("scripts", {}).get("found", {})
        return [a for info in found.values() for a in info.get("sounds", []) if a in rows]

    def sound_roles(self):
        """IW7 sound role of each alias, from the WeaponDef slot naming it; anim notetracks are foley;
        sounds the scripts play are world (3D) sounds."""
        roles = {}
        for s in self.specs():
            for slot, alias in s["sounds"].items():
                roles.setdefault(alias, SOUND_ROLES.get(slot, "foley"))
            for alias in self.notetrack_sounds([s]):
                roles.setdefault(alias, "foley")
        for alias in self.script_sounds():
            roles.setdefault(alias, "impact")
        return roles

    def notetrack_sounds(self, specs):
        """Notetracks of the weapon's anims that name a BO3 sound alias."""
        aliases = set(alias_rows(self.alias_table()))
        out = []
        reader = os.path.join(HERE, "..", "animation", "xab_preflight.py")
        for name in sorted({a for s in specs for a in s["anims"].values()}):
            path = os.path.join(self.cfg["t7_anims"], name + ".xab")
            if not os.path.exists(path):
                continue
            info = json.loads(subprocess.run([sys.executable, "-B", reader, path, "--game", "iw7"],
                                             capture_output=True, text=True).stdout or "{}")
            out += [nt["name"] for nt in info.get("notetracks", []) if nt["name"] in aliases]
        return out

    def sound_files(self, aliases):
        """(alias, FileSpec) of every alias and of the secondary aliases they chain to."""
        rows = alias_rows(self.alias_table())
        files, todo, seen = [], [(a, a) for a in aliases], set()
        while todo:
            a, chain = todo.pop()
            if a in seen or a not in rows:
                continue
            seen.add(a)
            for r in rows[a]:
                if r.get("FileSpec"):
                    files.append((chain, r["FileSpec"]))
                if r.get("Secondary"):
                    todo.append((r["Secondary"], chain))
        return sorted(set(files))


_ALIASES = {}


def alias_rows(path):
    if path not in _ALIASES:
        rows = {}
        with open(path, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                rows.setdefault(r["Name"], []).append(r)
        _ALIASES[path] = rows
    return _ALIASES[path]


def mesh_points(xmodel_export):
    pts = []
    with open(xmodel_export, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("OFFSET"):
                pts.append(tuple(float(x.strip(",")) for x in line.split()[1:4]))
    return pts


def ads_gun_from_mesh(xmodel_export, forward=8.0, band=0.6):
    """Gun origin in camera space when aiming (t7_vm_retarget --ads-gun): BO3 Wonder Weapons have no
    sight tag, so the sight line runs over the top of the gun, from the highest centreline point of its
    rear third to that of its front third (the camera sits on their mean height). On the Ray Gun this
    gives 5.78, against the 5.75 tuned in game."""
    pts = [p for p in mesh_points(xmodel_export) if abs(p[1]) <= band]
    if not pts:
        raise SystemExit("no centreline vertices in %s" % xmodel_export)
    lo, hi = min(p[0] for p in pts), max(p[0] for p in pts)
    third = (hi - lo) / 3.0
    rear = max(p[2] for p in pts if p[0] <= lo + third)
    front = max(p[2] for p in pts if p[0] >= hi - third)
    return (forward, 0.0, -round((rear + front) / 2.0, 3))


def gw_root(result):
    return result.get("output_root") or os.path.join(os.environ.get("LOCALAPPDATA", ""), "GrayWolf", "mcp")


def sound_stem(filespec):
    return os.path.splitext(filespec.replace("/", "\\").split("\\")[-1])[0]


def sound_asset(filespec):
    """GrayWolf sound asset name of a BO3 FileSpec: rooted at "all", no extension."""
    parts = [p for p in filespec.replace("/", "\\").split("\\") if p]
    if parts[:1] != ["all"]:
        parts = ["all"] + parts
    return os.path.splitext("\\".join(parts))[0]     # alias tables name .flac, .opus or .wav


def vfx_package(spec):
    fx = lambda role: {"type": 1, "fx": spec["fx"][role]["iw7"]} if role in spec["fx"] else None  # noqa: E731
    keys = ["viewFlashOverchargeEffect", "viewFlashOverchargeADSEffect", "worldFlashOverchargeEffect",
            "viewShellEjectEffect", "worldShellEjectEffect", "viewLastShotEjectEffect", "worldLastShotEjectEffect",
            "viewMagEjectEffect"]
    out = {"viewFlashEffect": fx("flash_view"), "worldFlashEffect": fx("flash_world"),
           "viewFlashADSEffect": fx("flash_view")}
    out.update({k: None for k in keys})
    return {"vfx": out}


SOUND_ROLES = {"fire_plr": "player", "fire_plr_last": "player", "dryfire_plr": "player",
               "fire_npc": "npc", "fire_npc_last": "npc", "dryfire_npc": "npc",
               "proj_loop": "projectile", "proj_impact": "impact"}
SFX_ROLES = {"fireSound": "fire_npc", "fireSoundPlayer": "fire_plr", "fireLastSound": "fire_npc_last",
             "fireLastSoundPlayer": "fire_plr_last", "projectileSound": "proj_loop",
             "emptyFireSound": "dryfire_npc", "emptyFireSoundPlayer": "dryfire_plr"}


def sfx_package(spec, template):
    pkg = json.loads(json.dumps(template))
    sounds = pkg["sounds"]
    sounds["name"] = spec["name"] + "_sfxpackage"
    for key in list(sounds):
        if key != "name" and isinstance(sounds[key], str) and key not in ("pickupSound", "pickupSoundPlayer",
                                                                            "ammoPickupSound"):
            sounds[key] = ""
    for key, role in SFX_ROLES.items():
        if key in sounds and spec["sounds"].get(role):
            sounds[key] = spec["sounds"][role]
    return pkg


def behaviour_lines(weapons, found, built_effects, sounds=()):
    """One ``weapon|namespace|tuning|effects|sounds`` line per weapon and BO3 behaviour script.

    The namespace (zm_weap_thundergun) names the behaviour family the IW7 module implements once;
    tuning is the script's zombie vars (``name=value``), effects its ``level._effect`` keys mapped to
    the converted IW7 effects (``key=vfx/t7/...``, built ones only), sounds the aliases it plays that
    the port carries. Scripts without a namespace or without tuning/effects add nothing."""
    lines = []
    for rel in sorted(found):
        info = found[rel]
        ns = info.get("namespace")
        if not ns or not (info.get("zombie_vars") or info.get("effects")):
            continue
        tuning = ",".join("%s=%s" % kv for kv in info.get("zombie_vars", {}).items())
        fx = ",".join("%s=%s" % (k, t7_weapon_spec.iw7_fx_name(v)) for k, v in info.get("effects", {}).items()
                      if v in built_effects)
        snd = ",".join(a for a in info.get("sounds", []) if a in sounds)
        lines += ["%s|%s|%s|%s|%s" % (w, ns, tuning, fx, snd) for w in weapons]
    return list(dict.fromkeys(lines))


def pap_attachment(template, name, upgraded):
    """Pack-a-Punch attachment carrying the upgraded BO3 weapon's ammunition and damage (stock fmpap1 shape)."""
    a = json.loads(json.dumps(template))
    wd = upgraded["weapDef"]
    a["szInternalName"] = name
    a["szDisplayName"] = "ZOM_WEAPON_PAP1" if name.endswith("1") else "ZOM_WEAPON_PAP2"
    for k in ("ammogeneral", "tracer", "reload", "laser", "regeneration"):
        a[k] = None
    a["ammunition"] = {"maxAmmo": wd["iMaxAmmo"], "startAmmo": wd["iStartAmmo"], "clipSize": upgraded["iClipSize"],
                       "shotCount": wd["shotCount"], "reloadAmmoAdd": wd["iReloadAmmoAdd"], "reloadStartAdd": 0,
                       "requireAmmoUsedPerShot": wd["requireAmmoUsedPerShot"]}
    a["damage"] = {k: wd[k] for k in ("damage", "mid1Damage", "mid2Damage", "mid3Damage", "minDamage", "meleeDamage",
                                      "maxDamageRange", "mid1DamageRange", "mid2DamageRange", "mid3DamageRange",
                                      "minDamageRange", "playerDamage", "mid1PlayerDamage", "mid2PlayerDamage",
                                      "mid3PlayerDamage", "minPlayerDamage")}
    return a


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", required=True)
    ap.add_argument("--weapon", required=True, help="BO3 weapon asset, e.g. thundergun_zm")
    ap.add_argument("--name", help="IW7 weapon name (default iw7_<bo3 weapon>)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--stages", default=",".join(STAGES), help="comma list, in order: " + ",".join(STAGES))
    args = ap.parse_args(argv)
    port = Port(load(args.config), args.weapon, args.out, args.name)
    for stage in args.stages.split(","):
        if stage not in STAGES:
            raise SystemExit("unknown stage %s" % stage)
        print("== %s" % stage, flush=True)
        getattr(port, "stage_" + stage)()
    print(json.dumps(port.manifest["stages"].get("zone", {}), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

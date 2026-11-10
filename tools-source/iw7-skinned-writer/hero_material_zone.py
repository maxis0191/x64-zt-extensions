"""Add a NEW IW7 hero material (clone of a stock one) with new embedded images to a ZoneTool zone source.

python -I hero_material_zone.py --techsets-dump <dump of techsets_cp_zmb> --template mopw/zmb_hero_jock_jacket
       --name mopw/zmb_hero_jock_jacket_szred --cs <stem>_c_packed_cs.png --nog <stem>_n_packed_nog.png
       --texconv <texconv.exe> --out <zonetool/<zone> dir> [--csv <zone_source csv> --after-row <row>]

Writes (ZoneTool IW7 source layout):
  images/<cs stem>.dds, images/<nog stem>.dds   BC7_UNORM with full mips (stock hero formats, values stored as is)
  materials/<name>.json                         template JSON, texture table semantics 14 (cs) / 15 (nog) rebound
  techsets/state/<techset>/<name>.*, techsets/constantbuffer/<techset>/<name>.*   copies of the template's files
The technique set stays the stock one (provided by the runtime techset zone), so no shader is embedded.
With --csv the material row is added (ZoneTool also pulls it as an xmodel dependency).
"""
import argparse
import glob
import json
import os
import shutil
import subprocess

SEM_CS, SEM_NOG = 14, 15


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--techsets-dump", required=True)
    ap.add_argument("--template", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--cs")
    ap.add_argument("--nog")
    ap.add_argument("--texconv", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--csv", default="")
    ap.add_argument("--tex", action="append", default=[],
                    help="extra SEMANTIC=png rebinding (e.g. 16=white.png for packed_a, 2=black.png for emissive)")
    a = ap.parse_args()

    tpl_path = os.path.join(a.techsets_dump, "materials", a.template.replace("/", os.sep) + ".json")
    mat = json.load(open(tpl_path))
    technique = mat["techniqueSet->name"]
    img_dir = os.path.join(a.out, "images")
    os.makedirs(img_dir, exist_ok=True)
    images = {}
    extra = [(int(x.split("=", 1)[0]), x.split("=", 1)[1]) for x in a.tex]
    for sem, png in [(SEM_CS, a.cs), (SEM_NOG, a.nog)] + extra:
        if not png:
            continue
        stem = os.path.splitext(os.path.basename(png))[0]
        subprocess.run([a.texconv, "-nologo", "-y", "-m", "0", "-f", "BC7_UNORM", "-o", img_dir, png],
                       check=True, stdout=subprocess.DEVNULL)
        if not os.path.exists(os.path.join(img_dir, stem + ".dds")):
            raise SystemExit("texconv produced no " + stem + ".dds")
        images[sem] = stem
    for t in mat["textureTable"]:
        if t["semantic"] in images:
            t["image"] = images[t["semantic"]]
    mat_out = os.path.join(a.out, "materials", a.name.replace("/", os.sep) + ".json")
    os.makedirs(os.path.dirname(mat_out), exist_ok=True)
    json.dump(mat, open(mat_out, "w"), indent=4)
    copied = []
    for kind in ("state", "constantbuffer"):
        src_glob = os.path.join(a.techsets_dump, "techsets", kind, technique, a.template.replace("/", os.sep) + ".*")
        for src in glob.glob(src_glob):
            ext = os.path.splitext(src)[1]
            dst = os.path.join(a.out, "techsets", kind, technique, a.name.replace("/", os.sep) + ext)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
            copied.append(os.path.relpath(dst, a.out))
    if a.csv:
        rows = open(a.csv, encoding="utf-8").read().split("\n")
        row = "material," + a.name
        if row not in rows:
            i = next((k for k, r in enumerate(rows) if r.startswith("xmodel,")), len(rows))
            rows.insert(i, row)
            open(a.csv, "w", encoding="utf-8", newline="\n").write("\n".join(rows))
    rep = {"material": a.name, "technique": technique, "images": {str(k): v for k, v in images.items()},
           "state_files": copied}
    print(json.dumps(rep))


if __name__ == "__main__":
    main()

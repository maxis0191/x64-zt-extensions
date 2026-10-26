"""Write an IW7 sound bank source for ZoneTool (soundbank/<bank>.json, the
alias table and FLAC assets). ZoneTool's IW7 sound bank builder then writes
the .sabl/.sabs next to the fastfile.

    python kino_sound.py --out <zonetool work dir> --bank kino.all --zone kino \
        --template <dumped stock aliases.csv> --music kino_mus_abracadavre=<file.flac>

Music aliases copy a stock streamed music row (2D, music bus, non-looping)
from the template table and replace name, secondary alias, file and volume.
"""
import argparse, csv, json, os, shutil


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--bank", default="kino.all")
    ap.add_argument("--zone", default="kino")
    ap.add_argument("--template", required=True, help="stock aliases.csv with a cp_level_up music row")
    ap.add_argument("--template-alias", default="cp_level_up")
    ap.add_argument("--music", action="append", default=[], help="alias=path/to/file.flac")
    a = ap.parse_args()
    with open(a.template, newline="") as f:
        rows = list(csv.reader(f))
    header = rows[0]
    base = next(r for r in rows[1:] if r and r[0] == a.template_alias)
    col = {name: i for i, name in enumerate(header)}
    sound = os.path.join(a.out, "sound")
    os.makedirs(sound, exist_ok=True)
    # ZoneTool's IW7 asset root for sound files is sound_assets/ (not sound/).
    assets = os.path.join(a.out, "sound_assets", "music", a.zone)
    os.makedirs(assets, exist_ok=True)
    os.makedirs(os.path.join(a.out, "soundbank"), exist_ok=True)
    out_rows = [header]
    for spec in a.music:
        alias, src = spec.split("=", 1)
        rel = "music\\%s\\%s" % (a.zone, alias)
        shutil.copyfile(src, os.path.join(assets, alias + ".flac"))
        row = list(base)
        row[col["Name"]] = alias
        row[col["SecondaryAliasName"]] = ""
        row[col["File"]] = rel
        row[col["vol_min"]] = row[col["vol_max"]] = "0.800000"   # a song, not a jingle
        out_rows.append(row)
    table = os.path.join(sound, a.bank + ".aliases.csv")
    with open(table, "w", newline="") as f:
        csv.writer(f).writerows(out_rows)
    bank = {"name": a.bank, "zone": a.zone, "gameLanguage": "all", "soundLanguage": "all",
            "aliases": ["sound/%s.aliases.csv" % a.bank]}
    for key in ("sendEffectParams", "ADSRSettings", "AmbientDefs", "AmbientEvents", "AmbientElements",
                "FilterDefs", "MixDefs", "NPCAdsrZoneEntry", "PLRAdsrZoneEntry", "OccludeDefs",
                "ReverbDefs", "TimescaleEntrys", "ZoneDefs", "Unks", "FullOcclusionDefs", "PlayerBreathStateDefs"):
        bank[key] = []
    with open(os.path.join(a.out, "soundbank", a.bank + ".json"), "w") as f:
        json.dump(bank, f, indent=4)
    print("bank %s: %d alias(es) -> %s" % (a.bank, len(out_rows) - 1, a.out))


if __name__ == "__main__":
    main()

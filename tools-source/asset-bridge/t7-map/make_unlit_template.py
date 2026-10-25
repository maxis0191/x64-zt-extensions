"""Derive the unlit material template from a ZoneTool `dumpasset material` output.

Stock donor: mopw/zmb_neon_light_blue (techset mopw_unlit_replace_lin_ct_nocast),
dumped after `loadzone techsets_cp_zmb` + `loadzone cp_zmb`. The colorTint literal
(JSON and baked .cbt constant buffer) is set to white. Output is local game-derived
data; never commit it.
"""
import json, os, struct, sys

DONOR = "mopw/zmb_neon_light_blue"
TECH = "mopw_unlit_replace_lin_ct_nocast"


def main(dump_assets, out):
    os.makedirs(os.path.join(out, "materials"), exist_ok=False)
    os.makedirs(os.path.join(out, "zone_source"))
    m = json.load(open(os.path.join(dump_assets, "materials", DONOR + ".json")))
    if m["techniqueSet->name"] != TECH:
        raise SystemExit("Unexpected donor technique: " + m["techniqueSet->name"])
    tint = next(c for c in m["constantTable"] if c["name"] == "colorTint")
    old = struct.pack("<4f", *tint["literal"])
    tint["literal"] = [1.0, 1.0, 1.0, 1.0]
    json.dump(m, open(os.path.join(out, "materials", "sdk_author_platform_material.json"), "w"), indent=4)
    for kind, exts in (("constantbuffer", ("cbi", "cbt")), ("state", ("statebits", "statebitsmap", "stateinfo"))):
        d = os.path.join(out, "techsets", kind, TECH)
        os.makedirs(d)
        for e in exts:
            b = bytearray(open(os.path.join(dump_assets, "techsets", kind, TECH, DONOR + "." + e), "rb").read())
            if e == "cbt":
                i = b.find(old)
                if i < 0:
                    raise SystemExit("colorTint constant not found in the donor buffer")
                b[i:i + 16] = struct.pack("<4f", 1, 1, 1, 1)
            open(os.path.join(d, "sdk_author_platform_material." + e), "wb").write(b)
    open(os.path.join(out, "zone_source", "sdk_author_platform_recipient.csv"), "w", newline="\n").write("techset,%s\n" % TECH)
    print("template written:", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

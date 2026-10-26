"""Write Kino vision sets (rawfiles) derived from the stock cp_zmb vision:
no fog, fixed exposure. Appends rawfile rows to the zone CSV."""
import sys, os, re
tmpl, out = sys.argv[1], sys.argv[2]
base = open(tmpl, encoding="ascii").read()
def setkv(text, key, value):
    return re.sub(r'(?m)^%s "[^"]*"' % re.escape(key), '%s "%s"' % (key, value), text)
os.makedirs(os.path.join(out, "vision"), exist_ok=True)
rows = []
for name, exposure in (("kino_a", 10), ("kino_b", 13), ("kino_c", 16)):
    t = base
    for k, v in (("fogMaxOpacity", "0"), ("fogColorIntensity", "0"), ("tonemapAuto", "0"), ("tonemapExposure", str(exposure)),
                 ("clut1Image", ""), ("r_hdrSkyIntensity", "1"), ("volumetricAirDensity", "0")):
        t = setkv(t, k, v)
    open(os.path.join(out, "vision", name + ".vision"), "w", newline="\r\n").write(t)
    rows.append("rawfile,vision/%s.vision" % name)
csv = os.path.join(out, "zone_source", "kino.csv")
open(csv, "a", newline="\n").write("\n".join(rows) + "\n")
print(rows)

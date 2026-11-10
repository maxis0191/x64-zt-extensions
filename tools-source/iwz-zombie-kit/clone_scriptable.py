"""clone_scriptable.py - data-driven clone of a ZoneTool IW7 scriptable dump (binary assetmanager format).

python -I clone_scriptable.py <src_dump> <out_dump> <map.json>
map.json = {"old string": "new string", ...}                       (plain swap)
        or {"swap": {...}, "hair_to": "<model>", "hair_prefixes": ["zmb_male_head_0", ...]}
           (every string starting with a hair prefix and containing 'hair' or 'flock' -> hair_to: the stock
            per-head hair options become the no-draw model, the new head carries its own hair)

Format facts (ZoneTool assetmanager.hpp dump_string, L203-230): a string is written as [type][existing] + NUL
terminated bytes; a pointer that was already written is an OFFSET record (entry index, not a byte offset). So a whole
string can be replaced by one of any length without breaking the stream. Only exact whole strings are replaced
(previous byte must be non-printable, next byte NUL). Prints counts; exit 2 if a swap key is not found.
"""
import json
import re
import sys


def strings_in(b):
    return set(m.group(1).decode() for m in re.finditer(rb'(?<![\x20-\x7e])([\x20-\x7e]{3,})\x00', bytes(b)))


def swap_all(b, mp):
    counts = {}
    for old, new in sorted(mp.items(), key=lambda kv: -len(kv[0])):
        o = old.encode() + b'\0'
        n = new.encode() + b'\0'
        out = bytearray()
        i = 0
        c = 0
        while True:
            j = b.find(o, i)
            if j < 0:
                out += b[i:]
                break
            if j > 0 and 0x20 <= b[j - 1] <= 0x7e:  # tail of a longer string
                out += b[i:j + 1]
                i = j + 1
                continue
            out += b[i:j] + n
            i = j + len(o)
            c += 1
        b = out
        counts[old] = c
    return b, counts


def main():
    src, dst, mpath = sys.argv[1], sys.argv[2], sys.argv[3]
    spec = json.load(open(mpath))
    b = bytearray(open(src, 'rb').read())
    if "swap" in spec:
        mp = dict(spec["swap"])
        hair = {}
        if spec.get("hair_to"):
            for s in strings_in(b):
                if s in mp or s == spec["hair_to"]:
                    continue
                if any(s.startswith(p) for p in spec.get("hair_prefixes", [])) and ("hair" in s or "flock" in s):
                    hair[s] = spec["hair_to"]
        required = set(mp)
        mp.update(hair)
    else:
        mp, required, hair = spec, set(spec), {}
    b, counts = swap_all(b, mp)
    open(dst, 'wb').write(b)
    print(json.dumps({"swapped": {k: v for k, v in counts.items() if k in required}, "hair_options_to_nodraw": len(hair),
                      "bytes": len(b)}, indent=1))
    missing = [k for k in required if counts.get(k, 0) == 0]
    if missing:
        print('MISSING', missing)
        sys.exit(2)


if __name__ == '__main__':
    main()

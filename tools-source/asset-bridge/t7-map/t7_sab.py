"""Read BO3 (T7) sound asset banks (.sabl/.sabs, version 15).

The container matches IW7's (magic 0x23585532, same header fields up to the
entry/checksum offsets); T7 entries are 36 bytes:
    id u32, size u32, frameCount u32, reserved u32, offset u64,
    rateIndex u8, channels u8, looping u8, format u8, envelope bytes (8)
Format 8 entries are complete FLAC files, so they can be re-banked for IW7
(ZoneTool's IW7 sound bank builder reads FLAC) without re-encoding.

    python t7_sab.py list <bank> [--min-seconds N]
    python t7_sab.py extract <bank> <index> <out.flac>
"""
import argparse, struct

MAGIC = 0x23585532
RATES = {0: 8000, 1: 12000, 2: 16000, 3: 24000, 4: 32000, 5: 44100, 6: 48000, 7: 96000, 8: 192000}


def entries(path):
    with open(path, "rb") as f:
        head = f.read(0x40)
        magic, version, esz, _, _, count, _, _, _, eoff, _ = struct.unpack_from("<8IQQQ", head)
        if magic != MAGIC or version != 15 or esz != 36:
            raise ValueError("not a T7 sound asset bank: %s" % path)
        f.seek(eoff)
        raw = f.read(esz * count)
    out = []
    for i in range(count):
        e = raw[i * 36:(i + 1) * 36]
        eid, size, frames, _, offset = struct.unpack_from("<IIIIQ", e)
        rate = RATES.get(e[24], 0)
        out.append(dict(index=i, id=eid, size=size, frames=frames, offset=offset, rate=rate,
                        channels=e[25], looping=e[26], format=e[27],
                        seconds=frames / rate if rate else 0.0))
    return out


def extract(path, index, out):
    e = entries(path)[index]
    with open(path, "rb") as f:
        f.seek(e["offset"])
        data = f.read(e["size"])
    if e["format"] == 8 and not data.startswith(b"fLaC"):
        raise ValueError("format 8 entry without a FLAC header")
    with open(out, "wb") as f:
        f.write(data)
    return e


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    ls = sub.add_parser("list"); ls.add_argument("bank"); ls.add_argument("--min-seconds", type=float, default=0)
    ex = sub.add_parser("extract"); ex.add_argument("bank"); ex.add_argument("index", type=int); ex.add_argument("out")
    a = ap.parse_args()
    if a.cmd == "list":
        for e in entries(a.bank):
            if e["seconds"] >= a.min_seconds:
                print("%4d id=%08x %7.1fs %dch loop=%d fmt=%d size=%d" % (e["index"], e["id"], e["seconds"], e["channels"], e["looping"], e["format"], e["size"]))
    else:
        e = extract(a.bank, a.index, a.out)
        print("wrote %s (%.1fs, %d Hz, %d ch)" % (a.out, e["seconds"], e["rate"], e["channels"]))


if __name__ == "__main__":
    main()

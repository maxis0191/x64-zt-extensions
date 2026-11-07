"""Copy BO3 (T7) weapon kick (gun kick, view kick) into an IW7 weapon JSON, stdlib only.

Input: the weapon scan of t7_weapon_scan.py (WeaponDef bytes under the variant's
pointer at +0x18) and a ZoneTool IW7 weapon JSON. Two blocks in the T7
WeaponDef follow BO2's field order (gun kick then view kick), ADS first:

  ADS +0x1208, hip +0x1268:
    +0  i32 reduced-kick bullets      +4  f32 reduced-kick percent
    +8  gun kick pitch min, max, yaw min, max, accel, speed max, speed decay,
        static decay (f32)
    +40 view kick pitch min, max, min magnitude, yaw min, yaw max (f32)

Established on zm_levelcommon: the hip block of every Wonder Weapon reads
accel 1000, speed max 1200, speed decay 100, static decay 2, the values IW7
weapons carry for the same fields; the Thundergun and Wunderwaffe differ only
by their stronger hip view kick (100-110 against 40-45), as in game. IW7's
extra *GunKickMagMin has no T7 counterpart and is set to 0.
"""
import argparse
import json
import struct
import sys

BLOCKS = {"ads": 0x1208, "hip": 0x1268}


def read_block(weapdef, offset):
    bullets, percent = struct.unpack_from("<if", weapdef, offset)
    gun = struct.unpack_from("<8f", weapdef, offset + 8)
    view = struct.unpack_from("<5f", weapdef, offset + 40)
    return {"bullets": bullets, "percent": percent, "gun": list(gun), "view": list(view)}


def iw7_fields(prefix, block):
    """IW7 weapDef keys for one block; prefix "Ads" or "Hip"."""
    low = prefix.lower()
    pmin, pmax, ymin, ymax, accel, smax, sdecay, static = block["gun"]
    vpmin, vpmax, vmag, vymin, vymax = block["view"]
    return {
        "%sGunKickReducedKickBullets" % low: block["bullets"],
        "%sGunKickReducedKickPercent" % low: block["percent"],
        "f%sGunKickPitchMin" % prefix: pmin, "f%sGunKickPitchMax" % prefix: pmax,
        "f%sGunKickYawMin" % prefix: ymin, "f%sGunKickYawMax" % prefix: ymax,
        "f%sGunKickMagMin" % prefix: 0.0,
        "f%sGunKickAccel" % prefix: accel, "f%sGunKickSpeedMax" % prefix: smax,
        "f%sGunKickSpeedDecay" % prefix: sdecay, "f%sGunKickStaticDecay" % prefix: static,
        "f%sViewKickPitchMin" % prefix: vpmin, "f%sViewKickPitchMax" % prefix: vpmax,
        "f%sViewKickYawMin" % prefix: min(vymin, vymax), "f%sViewKickYawMax" % prefix: max(vymin, vymax),
        "f%sViewKickMagMin" % prefix: vmag,
    }


def kick_fields(weapdef):
    out = {}
    out.update(iw7_fields("Ads", read_block(weapdef, BLOCKS["ads"])))
    out.update(iw7_fields("Hip", read_block(weapdef, BLOCKS["hip"])))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scan", required=True, help="t7_weapon_scan.py JSON")
    ap.add_argument("--weapon", required=True, help="BO3 weapon name in the scan (e.g. ray_gun_zm)")
    ap.add_argument("--iw7", required=True, nargs="+", help="IW7 weapon JSON files to update")
    args = ap.parse_args(argv)
    with open(args.scan, encoding="utf-8") as f:
        scan = json.load(f)
    entry = scan["weapons"].get(args.weapon)
    if not entry or "24" not in entry.get("children", {}):
        raise SystemExit("weapon %s has no WeaponDef block in the scan" % args.weapon)
    weapdef = bytes.fromhex(entry["children"]["24"]["hex"])
    if len(weapdef) < BLOCKS["hip"] + 60:
        raise SystemExit("WeaponDef block too short")
    fields = kick_fields(weapdef)
    for path in args.iw7:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        wd = data["weapDef"]
        missing = [k for k in fields if k not in wd]
        if missing:
            raise SystemExit("%s lacks %s" % (path, missing))
        before = {k: wd[k] for k in fields}
        wd.update(fields)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(json.dumps({"file": path, "changed": {k: [before[k], v] for k, v in fields.items() if before[k] != v}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

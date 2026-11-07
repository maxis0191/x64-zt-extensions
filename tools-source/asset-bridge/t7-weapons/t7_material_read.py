"""Read the BO3 (T7) material constants of a zone held resident by ZoneTool, stdlib only.

GrayWolf's material export gives a material's textures and its emissive tint,
but not the rest of the compiled constant table: the per-material emissive
intensity (``hdrScale``, the GDT's scaleRGB: Ray Gun power cell 16, reticle
64), tints, scroll and UV parameters. A T7 ``Material`` (ZoneTool
``t7/structs.hpp``, 0x2A0 bytes) carries them as ``MaterialConstantDef``
records (name hash, the name's first 12 characters, a float4):

    0x270 textureCount  0x271 samplerCount  0x272 constantCount
    0x278 techniqueSet  0x280 textureTable  0x290 constantTable

Weapon materials leave that table empty: their values sit in per-technique
static constant buffers (``constantBufferInfo``, 12 techniques x ds/vs/ps x 2,
each a ``MaterialStaticConstantBuffer`` whose initData is the raw ``$Globals``
cbuffer). The names and offsets come from the technique's own pixel shader:
its DXBC RDEF chunk (``rdef_globals``). Material +0x30 holds the buffers
(48 bytes per technique, ps at +32); technique set +0x10 the techniques;
technique +8 the draw methods (88 bytes, pixel shader at +32); pixel shader
+24 the program and +32 its size.

This reads every material in the ZoneTool asset log (type 6) and writes
``t7.material-read/1``: per material its techset name, its constants by name
(constant table, then every technique's ``$Globals`` variables) and its
textures (name hash, image asset). Run by t7_zone_snapshot.py on the
holding pid. Nothing is written to the target process. GPL-3.0-or-later
(ZoneTool lineage).
"""
import argparse
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from t7_weapon_scan import Process, load_asset_log  # noqa: E402

MATERIAL_TYPE = 6
MATERIAL_SIZE = 0x2A0
CONSTANT_SIZE = 32
TEXTURE_SIZE = 32
TECHNIQUES = 12
DRAW_METHODS = 8
DRAW_METHOD_SIZE = 88


def rdef_globals(dxbc):
    """{name: (offset, size)} of the $Globals cbuffer in a DXBC program's RDEF chunk."""
    if dxbc[:4] != b"DXBC":
        return {}
    count, = struct.unpack_from("<I", dxbc, 28)
    for i in range(count):
        off, = struct.unpack_from("<I", dxbc, 32 + 4 * i)
        if dxbc[off:off + 4] != b"RDEF":
            continue
        size, = struct.unpack_from("<I", dxbc, off + 4)
        rd = dxbc[off + 8:off + 8 + size]
        cb_count, cb_off = struct.unpack_from("<II", rd, 0)
        major = rd[17]
        var_size = 40 if major >= 5 else 24

        def name_at(o):
            return rd[o:rd.index(b"\0", o)].decode("ascii", "replace")
        for c in range(cb_count):
            name_off, var_count, var_off, _cb_size = struct.unpack_from("<IIII", rd, cb_off + 24 * c)
            if name_at(name_off) != "$Globals":
                continue
            out = {}
            for v in range(var_count):
                vname, start, vsize = struct.unpack_from("<III", rd, var_off + var_size * v)
                out[name_at(vname)] = (start, vsize)
            return out
    return {}


def globals_values(layout, data):
    """Variables of a $Globals layout read from a static buffer's bytes (floats)."""
    out = {}
    for name, (start, size) in layout.items():
        if start + size <= len(data) and size % 4 == 0:
            out[name] = [round(v, 6) for v in struct.unpack_from("<%df" % (size // 4), data, start)]
    return out


def parse_material(raw):
    """Counts and table pointers of one Material header."""
    texture_count, sampler_count, constant_count = raw[0x270], raw[0x271], raw[0x272]
    technique, textures, _samplers, constants = struct.unpack_from("<4Q", raw, 0x278)
    return {"texture_count": texture_count, "constant_count": constant_count, "techset_ptr": technique,
            "textures_ptr": textures, "constants_ptr": constants}


def parse_constants(raw, count):
    out = {}
    for i in range(count):
        name_hash, = struct.unpack_from("<I", raw, i * CONSTANT_SIZE)
        name = raw[i * CONSTANT_SIZE + 4:i * CONSTANT_SIZE + 16].split(b"\0", 1)[0].decode("ascii", "replace")
        value = [round(v, 6) for v in struct.unpack_from("<4f", raw, i * CONSTANT_SIZE + 16)]
        out[name or "0x%08X" % name_hash] = value
    return out


def parse_textures(raw, count, assets):
    """Texture slots by semantic. The image is not named: ZoneTool logs image headers at a reused
    address (every zm_prototype image at one), so an address does not identify an image."""
    out = []
    for i in range(count):
        _image, name_hash = struct.unpack_from("<QI", raw, i * TEXTURE_SIZE)
        out.append({"semantic": "0x%08X" % name_hash})
    return out


def ptr(proc, address):
    if not address or not proc.readable(address, 8):
        return 0
    return struct.unpack("<Q", proc.read(address, 8))[0]


# $Globals layouts of techsets whose techniques a zone leaves unresolved (their shaders load from
# another zone), keyed by techset name and buffer size. Derived from the buffer contents and checked
# against the BO3 mod tools GDT (model_export/wpn_t7_zmb_weapons.gdt) on two materials:
# mtl_wpn_t7_zmb_raygun_reticle (colorTint 1 0 0, glossRange 0-13, scaleRGB 64) and
# mtl_wpn_t7_zmb_raygun_meter (glossRange 0-17, scaleRGB 16, emissiveFalloff 2, tint 0.3613 linear).
KNOWN_LAYOUTS = {
    ("mc/lit_emissive", 224): {"colorTint": (160, 12), "glossRange": (176, 8), "hdrScale": (188, 4),
                               "emissiveFalloffPower": (192, 4), "emissiveTint1": (196, 12),
                               "relativeHDR": (208, 4)},
}


def technique_globals(proc, raw, techset, layouts, techset_name=None):
    """$Globals values of every technique that has a pixel shader static buffer."""
    out = {}
    for t in range(TECHNIQUES):
        buf = struct.unpack_from("<Q", raw, 0x30 + 48 * t + 32)[0]
        technique = ptr(proc, techset + 16 + 8 * t) if techset else 0
        if not buf or not proc.readable(buf, 72):
            continue
        init, size = struct.unpack_from("<QI", proc.read(buf, 72), 40)
        if not init or not size:
            continue
        data = proc.read(init, size)
        if not technique:
            known = KNOWN_LAYOUTS.get(((techset_name or "").split("#")[0], size))
            if known:
                for name, value in globals_values(known, data).items():
                    out.setdefault(name, value)
            continue
        # The buffer belongs to whichever draw method's pixel shader declares a $Globals that fits it.
        for method in range(DRAW_METHODS):
            shader = ptr(proc, technique + 8 + DRAW_METHOD_SIZE * method + 32)
            if not shader or not proc.readable(shader, 40):
                continue
            program, program_size = struct.unpack_from("<QI", proc.read(shader, 40), 24)
            if program not in layouts:
                layouts[program] = (rdef_globals(proc.read(program, program_size))
                                    if program and 0 < program_size < (1 << 24) and proc.readable(program, program_size)
                                    else {})
            layout = layouts[program]
            if layout and all(start + vsize <= size for start, vsize in layout.values()):
                for name, value in globals_values(layout, data).items():
                    out.setdefault(name, value)
                break
    return out


def read_material(proc, assets, address, layouts=None):
    raw = proc.read(address, MATERIAL_SIZE)
    head = parse_material(raw)
    result = {"techset": None, "constants": {}, "textures": []}
    if head["techset_ptr"] and proc.readable(head["techset_ptr"], 8):
        name_ptr, = struct.unpack("<Q", proc.read(head["techset_ptr"], 8))
        result["techset"] = proc.cstr(name_ptr) if name_ptr else None
    if head["constant_count"] and proc.readable(head["constants_ptr"], head["constant_count"] * CONSTANT_SIZE):
        result["constants"] = parse_constants(proc.read(head["constants_ptr"], head["constant_count"] * CONSTANT_SIZE),
                                              head["constant_count"])
    if head["texture_count"] and proc.readable(head["textures_ptr"], head["texture_count"] * TEXTURE_SIZE):
        result["textures"] = parse_textures(proc.read(head["textures_ptr"], head["texture_count"] * TEXTURE_SIZE),
                                            head["texture_count"], assets)
    for name, value in technique_globals(proc, raw, head["techset_ptr"], {} if layouts is None else layouts,
                                         result["techset"]).items():
        result["constants"].setdefault(name, value)
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--assetlog", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    assets, _ = load_asset_log(args.assetlog)
    proc = Process(args.pid)
    materials, failed, layouts = {}, [], {}
    for address, entry in sorted(assets.items()):
        if entry["type"] != MATERIAL_TYPE:
            continue
        try:
            materials[entry["name"]] = read_material(proc, assets, address, layouts)
        except OSError:
            failed.append(entry["name"])
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"schema": "t7.material-read/1", "materials": materials, "unreadable": failed}, f, indent=1)
    print(json.dumps({"materials": len(materials), "unreadable": len(failed)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

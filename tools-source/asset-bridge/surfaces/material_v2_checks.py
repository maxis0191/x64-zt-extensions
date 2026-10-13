"""Pure bounded v2 source/roundtrip/inventory/pixel gates; no native execution."""
import argparse
import json
from pathlib import Path
import re
import struct

from inspect_content import Inputs, no_links, parse_json, require, verify_contract
import prepare_material_v2 as v


def prepared_inventory(root):
    pending, files, count = [no_links(Path(root).absolute())], set(), 0
    while pending:
        for path in pending.pop().iterdir():
            count += 1
            require(count <= 64, "prepared entry bound exceeded")
            no_links(path)
            if path.is_dir():
                pending.append(path)
            else:
                require(path.is_file(), "regular prepared file required")
                files.add(path.relative_to(root).as_posix())
    return files


def source(prepared, writer, checker, receipt, zt):
    expected, plan = v.payloads(writer, checker, receipt)
    actual = Inputs(prepared)
    require(prepared_inventory(actual.root) == set(expected), "exact prepared inventory required")
    for name, data in expected.items():
        require(actual.read(name, v.LIMIT) == data, "prepared source differs: " + name)
    interfaces = Inputs(zt)
    for name, sha in plan["writer_interface_hashes"].items():
        require(v.digest(interfaces.read(name)) == sha, "writer interface differs: " + name)
    verify_contract(zt)  # Pins gfximage native dump/layout readers too.
    return plan


def roundtrip(data):
    fields = dict(schema="iw7.content-material-roundtrip/1", model=v.MODEL,
                  material_reference=v.MATERIAL, vertices=24, triangles=12, bones=1,
                  surfaces=1, lods=1, shadow_cutoff_lod=6, collision_lod=255,
                  has_lods=True, geometry_roundtrip_verified=True, read_existing_supported=True,
                  normal_encoding="H1-1010102-candidate", iw7_normal_encoding_verified=False,
                  ff_built=False, pixels_verified=False, ready=False)
    for name, value in fields.items():
        require(type(data.get(name)) is type(value) and data[name] == value, "v2 roundtrip mismatch: " + name)
    require(type(data.get("lod0_dist")) in (int, float) and data["lod0_dist"] == 1000000,
            "exact LOD distance required")
    return data


def inventory(log):
    require(f'Loading zone "{v.ZONE}"' in log and
            not re.search(r'could not be found|Could not find referenced|\[ ERROR \]|\[ FATAL \]', log),
            "v2 inventory unresolved or missing")
    rows = []
    for line in log.splitlines():
        if "Loading asset " not in line:
            continue
        match = re.search(r'Loading asset "([^"\r\n]+)" of type ([a-z0-9]+)\.$', line)
        require(match is not None, "malformed inventory callback")
        rows.append(match[2] + "," + match[1])
    expected = {r["type"] + "," + r["name"] for r in v.expected_inventory()}
    require(len(rows) == 8 and len(set(rows)) == 8 and set(rows) == expected, "exact eight-asset v2 inventory required")
    return rows


def resident_pixels(raw):
    # Native assetmanager scalar/array and GfxImage0x70 at the pinned IW7 source.
    # This one-image gate decodes only one opaque uncompressed32x32 mip.
    require(len(raw) < 8192 and raw[:6] == b"\x08\x01\x01\0\0\0" and len(raw) >= 126,
            "bounded IW7 image scalar required")
    image = raw[6:118]
    fmt = struct.unpack_from("<I", image, 24)[0]
    require(fmt in (28, 29, 87, 91), "RGBA8/BGRA8 format required")
    require(struct.unpack_from("<II4H", image, 40) == (4096, 4096, 32, 32, 1, 1)
            and image[56] == 1 and image[57] == 0 and struct.unpack_from("<Q", image, 64)[0] != 0,
            "exact resident32x32 single mip required")
    require(raw[118:120] == b"\x06\x01", "literal image name required")
    end = raw.find(b"\0", 120, 376)
    require(end != -1 and raw[120:end] == v.IMAGE.encode(), "custom image identity differs")
    tail = raw[end + 1:]
    require(tail[:6] == b"\x08\x01\x00\x10\x00\x00" and len(tail) == 4102,
            "exact pixel array without trailing payload required")
    pixels = tail[6:]
    bgra = v.tga()[18:]
    rgba = b"".join(bytes((bgra[i+2], bgra[i+1], bgra[i], bgra[i+3])) for i in range(0, 4096, 4))
    require(pixels == (rgba if fmt in (28, 29) else bgra), "original diffuse pixel/orientation/alpha mismatch")
    return {"format": fmt, "width": 32, "height": 32, "mips": 1, "decoded_rgba_sha256": v.digest(rgba)}


def dumped_surface(root, prepared):
    dump = Inputs(root)
    source_files = Inputs(Path(prepared) / "ff-inputs")
    material_name = f"materials/{v.MATERIAL}.json"
    expected = parse_json(source_files.read(material_name, 65536))
    actual = parse_json(dump.read(material_name, 65536))
    for key, value in expected.items():
        require(key in actual and actual[key] == value, "dumped material field differs: " + key)
    # Exact sidecars are required again; native CBT contains pointers, so byte
    # equality after a native reload is intentionally not an ABI claim.
    for suffix in ("stateinfo", "statebits", "statebitsmap"):
        name = f"techsets/state/{v.TECHNIQUE}/{v.MATERIAL}.{suffix}"
        before, after = source_files.read(name, 65536), dump.read(name, 65536)
        require((parse_json(before) == parse_json(after)) if suffix in ("stateinfo", "statebitsmap")
                else before == after, "dumped material state differs: " + suffix)
    cbi = f"techsets/constantbuffer/{v.TECHNIQUE}/{v.MATERIAL}.cbi"
    require(source_files.read(cbi, 152) == dump.read(cbi, 152), "dumped constant indices differ")
    require(bool(dump.read(f"techsets/constantbuffer/{v.TECHNIQUE}/{v.MATERIAL}.cbt", 65536)),
            "dumped constant buffer missing")
    pixels = resident_pixels(dump.read(f"images/{v.IMAGE}.iw7Image", 8192))
    return {"material_fields_verified": True, "image": pixels, "original_diffuse_verified": True,
            "normal_is_recipient_reference": v.NORMAL, "recipient_resolution_verified": False,
            "native_cbt_semantics_verified": False, "pixels_rendered_verified": False, "ready": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("source")
    for name in ("prepared", "writer", "checker", "receipt", "zt"):
        p.add_argument("--" + name, required=True, type=Path)
    for name in ("roundtrip", "inventory"):
        sub.add_parser(name).add_argument("--path", required=True, type=Path)
    p = sub.add_parser("surface")
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--prepared", required=True, type=Path)
    args = parser.parse_args()
    if args.action == "source":
        result = source(args.prepared, args.writer, args.checker, args.receipt, args.zt)
    elif args.action == "surface":
        result = dumped_surface(args.root, args.prepared)
    else:
        path = no_links(args.path.absolute())
        raw = Inputs(path.parent).read(path.name, 2 * 1024 * 1024)
        result = roundtrip(parse_json(raw)) if args.action == "roundtrip" else inventory(raw.decode("utf-8"))
    print(json.dumps(result, indent=2))

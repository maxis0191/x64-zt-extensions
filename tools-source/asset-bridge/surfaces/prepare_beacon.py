"""Tiny original surface witness using measured IW7 material state as a template.

Only writes a fresh source directory. Does not compile, pack, launch or deploy.
The template is read from retained checker preparation, never from a game process.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from inspect_content import Inputs, Inspector, no_links, parse_json, require


MATERIAL = "community_beacon_material_a"
IMAGE = "community_beacon_color_a"
ZONE = "community_beacon_surface_a"
TECHNIQUE = "mopw_l_sm_replace_i0c0s0o0n0p0"
NORMAL = "park_clown_zombie_shoes_n_3e46d100_packed_nog"
TEMPLATE = "paris_doom_checker_material_a"


def tga():
    # Original asymmetric 32px witness: four corners, one white top bar, magenta left bar.
    pixels = bytearray()
    for y in range(32):
        for x in range(32):
            color = ((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0))[(y >= 16) * 2 + (x >= 16)]
            if 8 <= x < 24 and y < 3:
                color = (255, 255, 255)
            if x < 3 and 8 <= y < 24:
                color = (255, 0, 255)
            r, g, b = color
            pixels.extend((b, g, r, 255))
    header = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, 32, 32, 32, 0x28)
    return header + pixels


def prepare(checker_root, output):
    source = Inputs(checker_root)
    output = no_links(Path(output).absolute())
    require(not output.exists(), "fresh beacon output required")
    require(not output.is_relative_to(source.root) and not source.root.is_relative_to(output),
            "beacon source and output must be separate")
    contract = parse_json(Path(__file__).with_name("source_contract.json").read_bytes())
    inputs = {}
    for path, expected in contract["beacon_fixture_inputs"].items():
        data = source.read(path, 65536)
        require(hashlib.sha256(data).hexdigest() == expected, "measured checker template changed: " + path)
        inputs[path] = data
    material = parse_json(inputs[f"materials/{TEMPLATE}.json"])
    require(material["techniqueSet->name"] == TECHNIQUE and
            [(r["semantic"], r["image"]) for r in material["textureTable"]] ==
            [(15, NORMAL), (14, "paris_doom_checker_color_a")], "measured texture bindings changed")
    material["textureTable"][1]["image"] = IMAGE
    payloads = {f"images/{IMAGE}.tga": tga(),
                f"materials/{MATERIAL}.json": (json.dumps(material, indent=2) + "\n").encode()}
    for path, data in inputs.items():
        if path.startswith("techsets/"):
            payloads[path.replace(TEMPLATE, MATERIAL)] = data
    payloads[f"zone_source/{ZONE}_recipient.csv"] = f"techset,{TECHNIQUE}\nimage,{NORMAL}\n".encode()
    payloads[f"zone_source/{ZONE}.csv"] = f"ignore,{ZONE}_recipient\nmaterial,{MATERIAL}\nimage,{IMAGE}\n".encode()
    manifest = {"schema": "iw7.beacon-surface-source/1", "zone": ZONE, "material": MATERIAL, "image": IMAGE,
                "source_pin": contract["zonetool"]["revision"], "required_builder_argument": "-strict-content-sources",
                "recipient": "cp_zmb", "template_inputs": contract["beacon_fixture_inputs"],
                "source_files": {k: hashlib.sha256(v).hexdigest() for k, v in payloads.items()},
                "bytes": sum(map(len, payloads.values())), "new_pixels": "original 32x32 BGRA8 top-origin opaque",
                "material_state": "measured IW7 template reused without texture/normal retail payload",
                "delivery": "resident image in FF; no mod PAK expected", "model_binding": MATERIAL,
                "sdk_integration": "merge ignore/material/image rows into model zone; bind model surface to material name",
                "model_supplied": False, "ff_built": False, "pixels_verified": False, "ready": False}
    output.mkdir(parents=True, exist_ok=False)
    for path, data in payloads.items():
        target = output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
    check = Inspector(output, ZONE, [("techset", TECHNIQUE), ("image", NORMAL)], strict_reader_prepared=True)
    check.material(MATERIAL)
    report = check.report()
    require(report["errors"] == 0, "generated surface preflight failed: " + json.dumps(report["findings"]))
    # Generator declares planned reader behavior; the CLI must verify actual prepared patch bytes.
    manifest["preflight"] = {"errors": report["errors"], "pending": report["pending"],
                              "reader_patch_verified_here": False}
    with (output / "beacon-surface.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2)
        stream.write("\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checker-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.checker_root, args.output), indent=2))

"""Build distinct model/material/image sources from a bounded local IW7 dump.

Color mip pixels use RGB = 255 - RGB. Alpha, normal/roughness maps, geometry,
animation and physics are preserved. Proprietary input/output stays in runtime.
Pillow decodes the original BC data; output is resident RGBA8 (no external PAK).
"""
import argparse
import csv
import hashlib
import io
import json
import struct
from pathlib import Path

PREFIX = "doom_negative_"
ROOT_MODELS = (
    "park_alien_gray", "zmb_brute_mascot_body", "park_clown_zombie",
    "park_clown_zombie_blue", "park_clown_zombie_green", "park_clown_zombie_orange", "park_clown_zombie_yellow",
)


def read_image(source: Path, include_name=False):
    raw = source.read_bytes()
    if raw[:6] != b"\x08\x01\x01\x00\x00\x00" or len(raw) < 121 or raw[118:120] != b"\x06\x01":
        raise ValueError(f"Unexpected IW7 image layout: {source.name}")
    image = bytearray(raw[6:118])
    end = raw.index(0, 120) + 1
    name = raw[120:end - 1].decode("ascii")
    if name.replace("*", "_") != source.stem:
        raise ValueError("Image dump name differs from its file name")
    if image[57]:
        streams = []
        previous_size = 0
        for index in range(4):
            width, height, packed = struct.unpack_from("<HHI", image, 72 + 8 * index)
            cumulative, levels = packed & 0x3FFFFFF, packed >> 26
            if not cumulative:
                continue
            pixels = source.with_name(f"{source.stem}_stream{index}.pixels").read_bytes()
            if len(pixels) != cumulative - previous_size or not width or not height:
                raise ValueError("Incomplete image stream")
            streams.append((width, height, levels, pixels))
            previous_size = cumulative
        if not streams:
            raise ValueError("No texture streams")
        width, height, levels, _ = streams[-1]
        pixels = b"".join(item[3] for item in reversed(streams))
    else:
        width, height = struct.unpack_from("<HH", image, 48)
        levels = image[56]
        length = struct.unpack_from("<I", image, 40)[0]
        if raw[end:end + 2] != b"\x08\x01" or struct.unpack_from("<I", raw, end + 2)[0] != length:
            raise ValueError("Missing resident pixel array")
        pixels = raw[end + 6:]
        if len(pixels) != length:
            raise ValueError("Resident pixel array size mismatch")
    if not width or not height or not 1 <= levels <= 16:
        raise ValueError("Invalid image dimensions/mip count")
    depth, elements = struct.unpack_from("<HH", image, 52)
    if depth > 1 or elements > 1:
        raise ValueError("Only ordinary 2D color maps are supported")
    result = image, pixels, width, height, levels
    return (*result, name) if include_name else result


def negative_mips(pixels, width, height, levels, dxgi):
    from PIL import Image
    # Only color encodings; packed normal/specular data must remain untouched.
    formats = {71: (8, "DXT1"), 72: (8, "DXT1"), 77: (16, "DXT5"), 78: (16, "DXT5"),
               98: (16, "BC7"), 99: (16, "BC7"), 28: (4, "RGBA"), 29: (4, "RGBA"),
               87: (4, "BGRA"), 91: (4, "BGRA")}
    if dxgi not in formats:
        raise ValueError(f"Unsupported color DXGI format {dxgi}")
    size, codec = formats[dxgi]
    result = bytearray()
    offset = 0
    for _ in range(levels):
        count = width * height * size if codec in ("RGBA", "BGRA") else max(1, (width + 3) // 4) * max(1, (height + 3) // 4) * size
        part = pixels[offset:offset + count]
        if len(part) != count:
            raise ValueError("Truncated color mip")
        if codec in ("RGBA", "BGRA"):
            decoded = Image.frombytes("RGBA", (width, height), part, "raw", codec).tobytes()
        else:
            # DDS DX10 header delegates decoding to Pillow's documented DDS decoder.
            flags = 0x81007
            header = struct.pack("<7I", 124, flags, height, width, count, 0, 1) + bytes(44)
            header += struct.pack("<II4s5I", 32, 4, b"DX10", 0, 0, 0, 0, 0)
            header += struct.pack("<5I", 0x1000, 0, 0, 0, 0)
            dds = b"DDS " + header + struct.pack("<5I", dxgi, 3, 0, 1, 0) + part
            decoded = Image.open(io.BytesIO(dds)).convert("RGBA").tobytes()
        # No quantization, color-space conversion or alpha edit.
        negative = bytearray(decoded)
        table = bytes(range(255, -1, -1))
        negative[0::4] = decoded[0::4].translate(table)
        negative[1::4] = decoded[1::4].translate(table)
        negative[2::4] = decoded[2::4].translate(table)
        if negative[3::4] != decoded[3::4]:
            raise ValueError("Alpha changed")
        result += negative
        offset += count
        width, height = max(1, width // 2), max(1, height // 2)
    if offset != len(pixels):
        raise ValueError("Unconsumed source mip bytes")
    return bytes(result)


def invert_image(source: Path, destination: Path):
    image, pixels, width, height, levels, original_name = read_image(source, include_name=True)
    dxgi = struct.unpack_from("<I", image, 24)[0]
    negative = negative_mips(pixels, width, height, levels, dxgi)
    image[:24] = bytes(24)
    struct.pack_into("<I", image, 24, 29 if dxgi in (29, 72, 78, 99, 91) else 28)
    struct.pack_into("<II4H", image, 40, len(negative), len(negative), width, height, 1, 1)
    image[56:59] = bytes((levels, 0, 0))
    struct.pack_into("<Q", image, 64, 1)
    image[72:104] = bytes(32)
    name = PREFIX + original_name
    output = b"\x08\x01\x01\x00\x00\x00" + image + b"\x06\x01" + name.encode("ascii") + b"\x00"
    output += b"\x08\x01" + struct.pack("<I", len(negative)) + negative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(output)
    return dict(name=name, original=original_name, width=width, height=height, mips=levels,
                format=dxgi, bytes=len(negative), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                sha256=hashlib.sha256(output).hexdigest())


def typed_alias(source, kind, name):
    folder, suffix = ("xmodel", ".xmb") if kind == "xmodel" else ("scriptable", "")
    path = source.with_name(source.name + "_aliases") / folder / (PREFIX + name + suffix)
    raw = path.read_bytes()
    own = b"\x06\x01" + (PREFIX + name).encode("ascii") + b"\x00"
    if raw.count(own) != 1:
        raise ValueError(f"Expected a typed aliased dump: {name}")
    return raw


def color_images(bindings, extra_colors=()):
    colors = {r["image"] for r in bindings if int(r["semantic"]) in (2, 14)}
    known = {r["image"] for r in bindings}
    for name in extra_colors:
        if name not in known:
            raise ValueError(f"Extra color image has no material binding: {name}")
        colors.add(name)
    for row in bindings:
        if row["image"] in colors and int(row["semantic"]) not in (0, 2, 14):
            raise ValueError(f"Color image is also bound as non-color data: {row['image']}")
    if not colors:
        raise ValueError("No verified color image bindings")
    return colors


def material_auxiliary(source, name, data):
    clean = name.replace("*", "_")
    techset = data["techniqueSet->name"].replace("*", "_")
    required = [("state", ".statebits"), ("state", ".statebitsmap")]
    if "stateFlags" not in data:
        required.append(("state", ".stateinfo"))
    if data.get("constantTable"):
        required += [("constantbuffer", ".cbi"), ("constantbuffer", ".cbt")]
    for kind, extension in required:
        path = source / "techsets" / kind / techset / (clean + extension)
        if not path.is_file() or not path.stat().st_size:
            raise ValueError(f"Incomplete material state/constants: {name}{extension}")
    return [(kind, path) for kind in ("state", "constantbuffer")
            for path in (source / "techsets" / kind / techset).glob(clean + ".*")]


def prepare(source: Path, captured: Path, destination: Path, extra_colors=()):
    if destination.exists():
        raise ValueError("Destination must be new; preserve previous candidates")
    rows = [row for row in csv.reader((source / "closure.csv").read_text().splitlines()) if row]
    groups = {kind: {name for row_kind, name in rows if row_kind == kind} for kind in ("xmodel", "material", "scriptable")}
    if not set(ROOT_MODELS).issubset(groups["xmodel"]):
        raise ValueError("Incomplete root model roster")
    with (source / "bindings.csv").open(newline="", encoding="utf-8-sig") as file:
        bindings = list(csv.DictReader(file))
    # Semantic 0 is shader-specific. Emission maps require explicit review,
    # rather than guessing from a file-name fragment and inverting packed data.
    colors = color_images(bindings, extra_colors)
    material_data = {name: json.loads((source / "materials" / (name.replace("*", "_") + ".json")).read_text())
                     for name in groups["material"]}
    auxiliary_files = {name: material_auxiliary(source, name, data) for name, data in material_data.items()}
    aliased = {(kind, name): typed_alias(source, kind, name)
               for kind in ("xmodel", "scriptable") for name in groups[kind]}
    images = []
    for name in sorted(colors):
        clean = name.replace("*", "_")
        candidates = [captured / "streamed_images" / (clean + ".iw7Image"), captured / "images" / (clean + ".iw7Image")]
        found = [path for path in candidates if path.exists()]
        if len(found) != 1:
            raise ValueError(f"Expected one complete image source: {name}")
        images.append(invert_image(found[0], destination / "images" / (PREFIX + clean + ".iw7Image")))
    for kind, folder, suffix in (("xmodel", "xmodel", ".xmb"), ("scriptable", "scriptable", "")):
        for name in sorted(groups[kind]):
            original = source / folder / (name + suffix)
            target = destination / folder / (PREFIX + name + suffix)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(aliased[kind, name])
            # Optional model physics LOD file uses the clone name, unchanged body.
            if kind == "xmodel":
                for extra in original.parent.glob(name + "_lod*"):
                    (target.parent / (PREFIX + extra.name)).write_bytes(extra.read_bytes())
    for name in sorted(groups["material"]):
        data = material_data[name]
        for binding in data["textureTable"]:
            if binding["image"] in colors:
                binding["image"] = PREFIX + binding["image"]
        target = destination / "materials" / (PREFIX + name.replace("*", "_") + ".json")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, indent=2) + "\n")
        techset = data["techniqueSet->name"].replace("*", "_")
        # State/constant-buffer bodies refer to the material's file name.
        # Preserve their exact bytes under the new material name.
        for kind, auxiliary in auxiliary_files[name]:
            target = destination / "techsets" / kind / techset / (PREFIX + name.replace("*", "_") + auxiliary.suffix)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(auxiliary.read_bytes())
    registries = []
    for path in (source / "netconststrings").glob("*.json"):
        data = json.loads(path.read_text())
        if data["stringType"] == 0 and data["sourceType"] == 0:
            registries.append((path, data))
    if len(registries) != 1:
        raise ValueError("Expected exactly one effective Spaceland model registry")
    path, data = registries[0]
    data["stringList"] += [PREFIX + name for name in sorted(groups["xmodel"])]
    target = destination / "netconststrings" / path.name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2) + "\n")
    references = (source / "references.csv").read_text().splitlines()
    # All original dependencies are references, retaining stock bytes and shaders.
    for material_name in sorted(groups["material"]):
        data = json.loads((source / "materials" / (material_name.replace("*", "_") + ".json")).read_text())
        references += [f"techset,,{data['techniqueSet->name']}"]
        references += [f"image,,{r['image']}" for r in data["textureTable"] if r["image"] not in colors]
    # Register every stock reference before adding a clone: dependency recursion
    # must not serialize a retail shader/surface/image into this small pack.
    asset_rows = references + [f"{kind},{PREFIX}{name}" for kind, names in groups.items() for name in sorted(names)]
    asset_rows += [f"image,{PREFIX}{name}" for name in sorted(colors)]
    asset_rows += [f"netconststrings,{path.stem}"]
    (destination / "assets.csv").write_text("\n".join(dict.fromkeys(asset_rows)) + "\n")
    report = dict(models=sorted(groups["xmodel"]), scriptables=sorted(groups["scriptable"]),
                  materials=sorted(groups["material"]), images=images, resident_bytes=sum(r["bytes"] for r in images),
                  native_client_required=False, external_texture_pack_required=False, gameplay_verified=False)
    (destination / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("captured", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--extra-color", action="append", default=[], help="Reviewed shader-specific color/emission image")
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.captured, args.destination, args.extra_color), indent=2))

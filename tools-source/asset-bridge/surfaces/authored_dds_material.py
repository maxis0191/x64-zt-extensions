"""Pure authored DDS/material inputs for the existing IW7 loader and FF path.

All inputs are already owned bytes. No file/process/retail access or execution.
This authoring contract supplies no facts about captured retail T7 images.
"""
import copy
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

from inspect_content import parse_json, relative, require, uint
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "t7-iw7"))
from resident_image import (CompleteImageObject, DDS_HEADER_BYTES, FORMATS,
                            MAX_PIXEL_BYTES, object_layout, object_to_dds,
                            verify_iw7_object)

SCHEMA = "iw7.authored-dds-material/1"


def asset_name(value):
    require(type(value) is str and len(value) <= 128, "bounded asset name required")
    relative(value)
    require(re.fullmatch(r"[A-Za-z0-9_]+(?:/[A-Za-z0-9_]+)*", value),
            "portable literal asset name required")
    return value


def read_dds(data):
    """Accept one explicit tight 2D DX10 mip; return the existing object view."""
    require(type(data) is bytes and DDS_HEADER_BYTES < len(data) <= DDS_HEADER_BYTES + MAX_PIXEL_BYTES,
            "bounded immutable DDS bytes required")
    require(data[:4] == b"DDS ", "DDS magic required")
    header = struct.unpack_from("<31I", data, 4)
    require(header[0] == 124 and header[18:21] == (32, 4, 0x30315844),
            "DDS_HEADER and DX10 pixel format required")
    require(header[1] & 0x1007 == 0x1007 and header[1] & ~(0x1007 | 0x8 | 0x20000 | 0x80000) == 0,
            "explicit 2D DDS header flags required")
    require(header[5] in (0, 1) and header[6] == 1,
            "one explicit authored mip required; no zero/default or inferred mip count")
    require(not any(header[7:18]) and not any(header[21:26]) and
            header[26] == 0x1000 and not any(header[27:]),
            "plain single-surface DDS required; no cube/volume/reserved fields")
    fmt, dimension, misc, array_size, alpha = struct.unpack_from("<5I", data, 128)
    require(dimension == 3 and misc == 0 and array_size == 1 and alpha == 0,
            "one Texture2D with unknown alpha mode required; no arrays/cubes/transforms")
    pixels = data[DDS_HEADER_BYTES:]
    image = CompleteImageObject(header[3], header[2], 1, 1, header[6], fmt,
                                len(pixels), "DXGI_FORMAT")
    mip, = object_layout(image)  # Existing typed formats, tight size and dimension limits.
    compressed = FORMATS[fmt].block_compressed
    pitch_flag = 0x80000 if compressed else 0x8
    require(header[1] & (0x80000 | 0x8) == pitch_flag and
            header[4] == (mip.slice_pitch if compressed else mip.row_pitch),
            "explicit tight DDS pitch/linear size required")
    return image, pixels


def rgba8_dds(width, height, pixels, *, srgb=False):
    """Reuse the existing encoder for an original text recipe's RGBA bytes."""
    require(type(srgb) is bool and type(width) is int and type(height) is int,
            "typed authored dimensions and sRGB choice required")
    image = CompleteImageObject(width, height, 1, 1, 1, 29 if srgb else 28,
                                len(pixels), "DXGI_FORMAT")
    return object_to_dds(image, pixels)


def prepare_material(*, zone, image_name, material_name, texture_slot, dds, template):
    """Return source payloads and a one-surface material reference, never an FF.

    Template roles are original IW7 JSON/state/buffer bytes, not T7 layouts.
    Existing content inspection/native build still qualify the complete template.
    """
    for name in (zone, image_name, material_name):
        asset_name(name)
    require("/" not in zone and len(zone) <= 63, "flat bounded zone name required")
    image, pixels = read_dds(dds)
    require(type(template) is dict and {"material", "statebits", "statebitsmap"} <= set(template) and
            set(template) <= {"material", "statebits", "statebitsmap", "stateinfo", "cbi", "cbt"},
            "explicit IW7 material/sidecar roles required")
    for data in template.values():
        require(type(data) is bytes and 0 < len(data) <= 256 * 1024,
                "bounded immutable template bytes required")
    material = parse_json(template["material"])
    require(type(material) is dict, "IW7 material JSON object required")
    technique = asset_name(material["techniqueSet->name"])
    textures = material.get("textureTable")
    require(type(textures) is list and 1 <= len(textures) <= 255 and
            type(texture_slot) is int and 0 <= texture_slot < len(textures),
            "explicit existing texture-table slot required")
    require(not material.get("subMaterials"), "layered materials outside authored v1")
    for row in textures:
        require(type(row) is dict and uint(row.get("semantic"), 8) and row["semantic"] < 0x11,
                "explicit IW7 texture semantic required")
        asset_name(row["image"])
    other_images = sorted({row["image"] for i, row in enumerate(textures) if i != texture_slot})
    recipient_keys = {name.casefold() for name in other_images}
    require(len(recipient_keys) == len(other_images) and image_name.casefold() not in recipient_keys,
            "authored image cannot alias a recipient image, including Windows case aliases")
    constants = material.get("constantTable")
    require(constants is None or type(constants) is list, "IW7 constant table required")
    if constants:
        require({"cbi", "cbt"} <= set(template) and len(template["cbi"]) == 152,
                "constant material requires exact cbi and original cbt")
    else:
        require(not ({"cbi", "cbt"} & set(template)), "unexpected constant-buffer sidecars")
    if material.get("stateFlags") is None:
        require("stateinfo" in template, "missing material stateinfo")
    else:
        require(uint(material["stateFlags"], 8), "IW7 stateFlags uint8 required")
    if "stateinfo" in template:
        info = parse_json(template["stateinfo"])
        require(type(info) is dict and uint(info.get("stateFlags"), 8), "IW7 stateinfo required")
    mapping = parse_json(template["statebitsmap"])
    require(len(template["statebits"]) == 152 and type(mapping) is list and 1 <= len(mapping) <= 255 and
            all(value == 255 or value < len(mapping) for value in template["statebits"]),
            "152 valid IW7 state indices required")
    material = copy.deepcopy(material)
    material["textureTable"][texture_slot]["image"] = image_name
    material_raw = (json.dumps(material, indent=2, allow_nan=False) + "\n").encode()
    require(len(material_raw) <= 256 * 1024, "bounded material source required")
    files = {f"images/{image_name}.dds": dds, f"materials/{material_name}.json": material_raw}
    for role, data in template.items():
        if role != "material":
            family = "constantbuffer" if role in ("cbi", "cbt") else "state"
            files[f"techsets/{family}/{technique}/{material_name}.{role}"] = data
    files[f"zone_source/{zone}_recipient.csv"] = (
        f"techset,{technique}\n" + "".join(f"image,{name}\n" for name in other_images)).encode()
    files[f"zone_source/{zone}.csv"] = (
        f"ignore,{zone}_recipient\nimage,{image_name}\nmaterial,{material_name}\n").encode()
    return {"schema": SCHEMA, "files": files, "material_reference": material_name,
            "image": {"name": image_name, "width": image.width, "height": image.height,
                      "dxgi_format": image.dxgi_format, "format_namespace": image.format_namespace,
                      "mip_count": image.level_count, "pixel_bytes": len(pixels),
                      "pixel_sha256": hashlib.sha256(pixels).hexdigest(),
                      "dds_sha256": hashlib.sha256(dds).hexdigest(),
                      "iw7_semantic": textures[texture_slot]["semantic"]},
            "texture_slot": texture_slot,
            "recipient_references": {"techset": technique, "images": other_images},
            "ff_built": False, "material_verified": False, "rendered_verified": False, "ready": False}


def verify_image(dds, dumped_image, *, image_name, iw7_semantic):
    """Reuse the existing independent IW7 image-byte comparison after a future dump."""
    asset_name(image_name)
    image, pixels = read_dds(dds)
    return verify_iw7_object(image, pixels, dumped_image, image_name, iw7_semantic)

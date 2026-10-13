"""Bounded DDS serialization and IW7 readback of a copied resident T7 2D image.

No engine/process access, image decoding, color conversion or XPAK fallback.
The DDS DX10 layout follows the retained DirectXTex DDS.h/EncodeDDSHeader path.
"""
import argparse
from dataclasses import dataclass, fields
import hashlib
import json
from pathlib import Path
import struct

SCHEMA = "iw7.t7-resident-image-copy/1"
MAX_DIMENSION = 4096
MAX_PIXEL_BYTES = 16 * 1024 * 1024
DDS_HEADER_BYTES = 148  # magic + DDS_HEADER(124) + DDS_HEADER_DXT10(20)


@dataclass(frozen=True)
class Format:
    name: str
    unit_bytes: int
    block_compressed: bool = False
    srgb: bool = False


# Explicit typed DXGI values, not the different T7 GfxPixelFormat enum.
# Unknown, TYPELESS, packed/video/depth, arrays, HDR and compressed BC6 are outside v1.
FORMATS = {
    28: Format("R8G8B8A8_UNORM", 4), 29: Format("R8G8B8A8_UNORM_SRGB", 4, srgb=True),
    49: Format("R8G8_UNORM", 2), 61: Format("R8_UNORM", 1),
    71: Format("BC1_UNORM", 8, True), 72: Format("BC1_UNORM_SRGB", 8, True, True),
    74: Format("BC2_UNORM", 16, True), 75: Format("BC2_UNORM_SRGB", 16, True, True),
    77: Format("BC3_UNORM", 16, True), 78: Format("BC3_UNORM_SRGB", 16, True, True),
    80: Format("BC4_UNORM", 8, True), 81: Format("BC4_SNORM", 8, True),
    83: Format("BC5_UNORM", 16, True), 84: Format("BC5_SNORM", 16, True),
    87: Format("B8G8R8A8_UNORM", 4), 91: Format("B8G8R8A8_UNORM_SRGB", 4, srgb=True),
    98: Format("BC7_UNORM", 16, True), 99: Format("BC7_UNORM_SRGB", 16, True, True),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


@dataclass(frozen=True)
class CopiedImage:
    width: int
    height: int
    depth: int
    width1: int
    height1: int
    level_count: int
    level_count1: int
    dxgi_format: int
    total_size: int
    map_type: int
    flags: int
    streaming: int
    streamed_part_count: int
    use_fallback: int
    fallback_level: int
    fallback_size: int
    fallback_pointer_present: bool
    delay_load_pixels: bool
    source_semantic: int


@dataclass(frozen=True)
class Mip:
    width: int
    height: int
    offset: int
    row_pitch: int
    slice_pitch: int


def layout(image):
    """Accept a conservative v1 subset; zero unknown flags is policy, not an ABI claim."""
    require(type(image) is CopiedImage, "a copied scalar image view is required")
    bool_fields = {"fallback_pointer_present", "delay_load_pixels"}
    for field in fields(image):
        value = getattr(image, field.name)
        expected = bool if field.name in bool_fields else int
        require(type(value) is expected, "invalid metadata type: " + field.name)
        if expected is int:
            require(0 <= value <= 0xFFFFFFFF, "metadata integer outside uint32: " + field.name)
    require(1 <= image.width <= MAX_DIMENSION and 1 <= image.height <= MAX_DIMENSION,
            "dimensions exceed the 1..4096 pilot range")
    require(image.map_type == 1 and image.depth == 1, "only T7 MAPTYPE_2D=1, depth=1 is supported")
    require(image.width1 == image.width and image.height1 == image.height and
            image.level_count1 == image.level_count, "ambiguous primary/resident dimensions or mip count")
    require(1 <= image.level_count <= max(image.width, image.height).bit_length(), "invalid mip count")
    require(image.flags == 0, "unmapped T7 image flags are outside the v1 profile")
    require(image.streaming == 0 and image.streamed_part_count == 0, "streamed images are not resident input")
    require(image.use_fallback == 0 and image.fallback_level == 0 and image.fallback_size == 0 and
            not image.fallback_pointer_present, "fallback/tail images are refused")
    require(not image.delay_load_pixels, "delayed pixels are refused")
    require(0 <= image.source_semantic < 0x15, "invalid T7 semantic")
    require(0 < image.total_size <= MAX_PIXEL_BYTES, "pixel budget exceeds 16 MiB or is empty")
    fmt = FORMATS.get(image.dxgi_format)
    require(fmt is not None, "unsupported typed DXGI format")
    result, offset = [], 0
    for level in range(image.level_count):
        width, height = max(1, image.width >> level), max(1, image.height >> level)
        columns = (width + 3) // 4 if fmt.block_compressed else width
        rows = (height + 3) // 4 if fmt.block_compressed else height
        pitch = columns * fmt.unit_bytes
        size = pitch * rows
        require(size <= MAX_PIXEL_BYTES - offset, "declared mip chain exceeds pixel budget")
        result.append(Mip(width, height, offset, pitch, size))
        offset += size
    require(offset == image.total_size, "totalSize differs from the tight declared mip chain")
    return tuple(result)


def to_dds(image, pixels):
    """Return a DX10 DDS, preserving every input pixel/block byte unchanged."""
    mips = layout(image)
    # bytes makes ownership/stability explicit: no borrowed memoryview/engine pointer.
    require(type(pixels) is bytes and len(pixels) == image.total_size, "exact immutable copied pixels required")
    fmt = FORMATS[image.dxgi_format]
    header = [0] * 31
    header[0] = 124
    header[1] = 0x1007 | 0x20000 | (0x80000 if fmt.block_compressed else 0x8)
    header[2:7] = [image.height, image.width,
                   mips[0].slice_pitch if fmt.block_compressed else mips[0].row_pitch,
                   1, image.level_count]
    header[18:21] = [32, 0x4, 0x30315844]  # DDS_PIXELFORMAT, FOURCC, 'DX10'
    header[26] = 0x1000 | (0x400008 if image.level_count > 1 else 0)
    # Texture2D, no cube/array flags, one array element, unknown alpha mode.
    # No guessed alpha premultiplication, semantic, channel packing or gamma transform.
    extended = (image.dxgi_format, 3, 0, 1, 0)
    return b"DDS " + struct.pack("<31I5I", *header, *extended) + pixels


def metadata(image):
    """A tiny copy manifest; contains no pointers, names or inferred material mapping."""
    layout(image)
    return {"schema": SCHEMA, "format_namespace": "DXGI_FORMAT", "image":
            {field.name: getattr(image, field.name) for field in fields(image)}}


def from_metadata(value):
    require(type(value) is dict and set(value) == {"schema", "format_namespace", "image"}, "exact copy schema required")
    require(value["schema"] == SCHEMA and value["format_namespace"] == "DXGI_FORMAT", "copy schema/format namespace differs")
    require(type(value["image"]) is dict and set(value["image"]) == {f.name for f in fields(CopiedImage)},
            "exact scalar fields required")
    result = CopiedImage(**value["image"])
    layout(result)
    return result


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def read_copy(metadata_path, pixels_path):
    """Read only the two explicit bounded files, never a metadata-supplied path."""
    with metadata_path.open("rb") as stream:
        raw = stream.read(16385)
    require(len(raw) <= 16384, "copy metadata exceeds 16 KiB")
    value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_object,
                       parse_constant=lambda _: require(False, "non-finite JSON value"))
    image = from_metadata(value)
    with pixels_path.open("rb") as stream:
        pixels = stream.read(image.total_size + 1)
    require(len(pixels) == image.total_size, "exact immutable copied pixels required")
    return image, pixels


def verify_iw7_image(image, pixels, raw, expected_name, expected_semantic):
    """Compare one pinned IW70x70 image dump with the selected copied bytes.

    Semantic is an explicit IW7 binding, never inferred from T7 source_semantic.
    Compressed blocks are compared unchanged; this does not decode their channels
    or establish source capture provenance, shader compatibility or rendering.
    """
    mips = layout(image)
    require(type(pixels) is bytes and len(pixels) == image.total_size,
            "exact immutable copied pixels required")
    require(type(expected_name) is str and expected_name and "\0" not in expected_name,
            "explicit image name required")
    name = expected_name.encode("utf-8")
    require(len(name) <= 255, "image name exceeds 255 bytes")
    require(type(expected_semantic) is int and 0 <= expected_semantic < 0x11,
            "explicit IW7 texture semantic required")
    require(type(raw) is bytes and 126 <= len(raw) <= image.total_size + 382 and
            raw[:6] == b"\x08\x01\x01\0\0\0", "bounded IW7 image scalar required")
    scalar = raw[6:118]
    require(struct.unpack_from("<I", scalar, 24)[0] == image.dxgi_format,
            "IW7 typed format differs")
    require(scalar[32] == 3 and scalar[33] == expected_semantic and scalar[34] == 3,
            "IW7 2D/file-image category or explicit semantic differs")
    require(struct.unpack_from("<II4H", scalar, 40) ==
            (image.total_size, image.total_size, image.width, image.height, 1, 1) and
            scalar[56] == image.level_count and scalar[57] == 0 and
            struct.unpack_from("<Q", scalar, 64)[0] != 0,
            "IW7 resident dimensions/mips/byte counts differ")
    literal = b"\x06\x01" + name + b"\0"
    require(raw[118:118 + len(literal)] == literal, "IW7 image identity differs")
    tail = raw[118 + len(literal):]
    require(tail[:6] == b"\x08\x01" + struct.pack("<I", image.total_size) and
            tail[6:] == pixels, "IW7 pixel/block array differs or has trailing bytes")
    return {"image": expected_name, "dxgi_format": image.dxgi_format,
            "width": image.width, "height": image.height, "mip_count": len(mips),
            "pixel_bytes": image.total_size, "iw7_semantic": expected_semantic,
            "pixel_sha256": hashlib.sha256(pixels).hexdigest(),
            "serialized_pixel_bytes_verified": True,
            "material_verified": False, "rendered_verified": False}


def verify_files(metadata_path, pixels_path, dump_path, expected_name, expected_semantic):
    image, pixels = read_copy(metadata_path, pixels_path)
    with dump_path.open("rb") as stream:
        raw = stream.read(image.total_size + 383)
    return verify_iw7_image(image, pixels, raw, expected_name, expected_semantic)


def convert_files(metadata_path, pixels_path, output_path):
    """Offline explicit files only. Never follows paths embedded in metadata."""
    image, pixels = read_copy(metadata_path, pixels_path)
    payload = to_dds(image, pixels)
    require(output_path.suffix.lower() == ".dds", "DDS output extension required")
    with output_path.open("xb") as stream:
        stream.write(payload)
    return {"dds_bytes": len(payload), "pixel_bytes": image.total_size,
            "dxgi_format": image.dxgi_format, "format": FORMATS[image.dxgi_format].name,
            "mip_count": image.level_count, "pixel_bytes_unchanged": True,
            "runtime_verified": False, "material_verified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metadata", type=Path)
    parser.add_argument("pixels", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--verify-iw7-image", type=Path)
    parser.add_argument("--image-name")
    parser.add_argument("--iw7-semantic", type=int)
    args = parser.parse_args()
    try:
        if args.verify_iw7_image is not None:
            require(args.output is None and args.image_name is not None and args.iw7_semantic is not None,
                    "readback requires explicit name/semantic and no DDS output")
            result = verify_files(args.metadata, args.pixels, args.verify_iw7_image,
                                  args.image_name, args.iw7_semantic)
        else:
            require(args.output is not None and args.image_name is None and args.iw7_semantic is None,
                    "explicit DDS output or complete readback arguments required")
            result = convert_files(args.metadata, args.pixels, args.output)
        print(json.dumps(result))
        return 0
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        print(json.dumps({"error": str(exc), "runtime_verified": False, "material_verified": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

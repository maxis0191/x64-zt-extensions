"""Emit an original, source-derived H1 XMB/XSB parser probe, never IW7 output.

No game, compiler, converter, asset database or external dependency is invoked.
The material is an explicit named reference, not a complete render material.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import stat
import struct
import subprocess

PIN = "fab935826c898806855376662a8a03317b3ad8f1"
MODEL = "paris_h1_original_cube"
SURFACE = MODEL + "_lod0"
MATERIAL = "paris_h1_original_material"
LIMIT = 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def regular_ancestry(path):
    require(path.is_absolute() and ".." not in path.parts, "absolute normalized path required")
    for item in (path, *path.parents):
        if item.exists() or item.is_symlink():
            info = item.lstat()
            require(not stat.S_ISLNK(info.st_mode) and
                    not getattr(info, "st_file_attributes", 0) & 0x400,
                    "reparse/symlink ancestry refused")
    return path


def verify_sources(repo):
    regular_ancestry(repo)
    require(repo.is_dir(), "source directory missing")
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True).stdout.strip()
    require(head == PIN, "source revision differs from the reviewed pin")
    contract = json.loads(Path(__file__).with_name("source-contract.json").read_text())
    require(contract["pin"] == PIN, "source contract pin mismatch")
    for name, expected in contract["lf_sha256"].items():
        path = regular_ancestry(repo / name)
        require(path.is_file() and path.stat().st_size <= LIMIT, "source file absent or oversized")
        content = path.read_bytes().replace(b"\r\n", b"\n")
        require(hashlib.sha256(content).hexdigest() == expected, "source drift: " + name)
    return contract


def array(payload=b"", count=0):
    if not count:
        require(not payload, "null array has payload")
        return b"\x08\x00"
    require(0 < count <= 256 and payload, "invalid array")
    return b"\x08\x01" + struct.pack("<I", count) + payload


def named(kind, value=None):
    require(kind in (6, 7), "invalid string/asset record")
    if value is None:
        return bytes((kind, 0))
    require(value and len(value) <= 128 and value.isascii() and "\0" not in value,
            "bounded ASCII name required")
    return bytes((kind, 1)) + value.encode("ascii") + b"\0"


def packed_axis(vector):
    # H1 Vec3PackUnitVec_H1, shared.cpp:400-408. Only literal unit axes used.
    values = [math.floor((x + 1.0) * 0.5 * 1023.0 + 0.5) for x in vector]
    return 0xC0000000 | values[0] | values[1] << 10 | values[2] << 20


def geometry():
    faces = (
        (((-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)), (0,0,1), (1,0,0)),
        (((1,-1,-1),(-1,-1,-1),(-1,1,-1),(1,1,-1)), (0,0,-1), (-1,0,0)),
        (((1,-1,1),(1,-1,-1),(1,1,-1),(1,1,1)), (1,0,0), (0,0,-1)),
        (((-1,-1,-1),(-1,-1,1),(-1,1,1),(-1,1,-1)), (-1,0,0), (0,0,1)),
        (((-1,1,1),(1,1,1),(1,1,-1),(-1,1,-1)), (0,1,0), (1,0,0)),
        (((-1,-1,-1),(1,-1,-1),(1,-1,1),(-1,-1,1)), (0,-1,0), (1,0,0)),
    )
    vertices, triangles = bytearray(), bytearray()
    for face, (points, normal, tangent) in enumerate(faces):
        for point, uv in zip(points, ((0,0),(1,0),(1,1),(0,1))):
            vertices += struct.pack("<4fI", *(v * 8.0 for v in point), 1.0, 0xFFFFFFFF)
            vertices += struct.pack("<2eII", *uv, packed_axis(normal), packed_axis(tangent))
        for indices in ((0,1,2),(0,2,3)):
            triangles += struct.pack("<3H", *(face * 4 + i for i in indices))
    return bytes(vertices), bytes(triangles)


def model_bytes():
    # Windows x64 H1 ABI, structs.hpp:4333-4387. Zero pointer slots: the
    # production parser replaces them from typed records, never dereferences them.
    header = bytearray(680)
    struct.pack_into("<3B", header, 8, 1, 1, 1)
    struct.pack_into("<fI", header, 16, 1.0, 0x80000000)
    struct.pack_into("<fHH", header, 128, 1000.0, 1, 0)
    struct.pack_into("<I", header, 144, 0x80000000)
    header[512] = 1
    struct.pack_into("<7f", header, 544, math.sqrt(192), 0, 0, 0, 8, 8, 8)
    data = array(header, 1) + named(6, MODEL)
    data += array(struct.pack("<i", 0), 1) + named(6, "tag_origin")
    data += array() * 3  # parentList, tagAngles, tagPositions: one root only
    data += array(b"\0", 1)
    data += array(struct.pack("<8f", 0, 0, 0, 1, 0, 0, 0, 2), 1)
    data += array() * 3  # reactive parts, tweaks, collision surfaces
    data += array(struct.pack("<7f", 0, 0, 0, 8, 8, 8, 192), 1)
    data += array(struct.pack("<H", 0xFFFF), 1)
    data += array(bytes(8), 1) + named(7, MATERIAL)
    data += named(7, SURFACE) + named(7) * 5
    data += named(7) * 2  # physics preset/collmap
    data += array() * 4  # blend weight names/maps, MDAO, composite models
    data += named(7) + array()  # skeleton script, bone physics
    return data


def surface_bytes():
    group = bytearray(56)
    struct.pack_into("<H", group, 16, 1)
    struct.pack_into("<I", group, 20, 0x80000000)
    surface = bytearray(264)
    struct.pack_into("<HHHBB", surface, 0, 0, 24, 12, 1, 0)
    struct.pack_into("<I", surface, 228, 0x80000000)
    vertices, triangles = geometry()
    rigid = struct.pack("<4HQ", 0, 24, 0, 12, 0)
    data = array(group, 1) + named(6, SURFACE) + array(surface, 1)
    data += array(vertices, 24) + array(triangles, 12) + array(triangles, 12)
    data += array(rigid, 1)
    data += b"\x0a\x00" * 6  # unknown0, blend, blend table, lmap, tension, accumulation
    data += array()  # no subdivision branch, no blend shapes
    return data


def build_payloads():
    return {f"xmodel/{MODEL}.xmb": model_bytes(),
            f"xsurface/{SURFACE}.xsb": surface_bytes()}


def emit(repo, output):
    contract = verify_sources(repo)
    regular_ancestry(output)
    require(output.parent.is_dir() and not output.exists(), "fresh output directory required")
    payloads = build_payloads()
    from inspect_fixture import inspect_pair
    inspection = inspect_pair(*payloads.values())
    receipt = {
        "schema": "iw7.h1-original-parser-fixture/1", "source_pin": PIN,
        "original_geometry": "16-unit cube, flat face normals, positive UV handedness",
        "native_parser_executed": False, "native_converter_executed": False,
        "ff_built": False, "rendering_verified": False, "retail_h1_compatibility": False,
        "material": {"name": MATERIAL, "representation": "H1 DUMP_TYPE_ASSET named reference",
                     "payload_included": False, "dependency_closure_complete": False},
        "bone_strings": "tag_origin retained by H1 parser; numeric token 0 is not a live engine ID",
        "inspection": inspection, "source_contract_lf_sha256": contract["lf_sha256"],
        "files": {name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                  for name, data in payloads.items()},
    }
    payloads["fixture.json"] = (json.dumps(receipt, indent=2) + "\n").encode()
    require(sum(map(len, payloads.values())) < LIMIT, "fixture exceeds one MiB")
    output.mkdir()
    for relative, data in payloads.items():
        path = output / relative
        path.parent.mkdir(exist_ok=True)
        with path.open("xb") as stream:
            stream.write(data)
        require(path.read_bytes() == data, "output verification failed")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(emit(args.source_repo, args.output), indent=2))

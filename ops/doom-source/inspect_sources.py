"""Bounded data-only inspection; never starts Blender or evaluates source code."""
import argparse
import collections
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile

MAX_MEMBER = 16 * 1024 * 1024
MAX_BLEND_READ = 32 * 1024 * 1024


def dna_struct_names(data, endian):
    """Resolve BHead SDNA indexes from the file's own schema, no field offsets."""
    stream = io.BytesIO(data)
    def tag(value):
        if stream.read(4) != value:
            raise ValueError("SDNA section differs")
    def integer():
        raw = stream.read(4)
        if len(raw) != 4:
            raise ValueError("SDNA integer truncated")
        return struct.unpack(endian + "I", raw)[0]
    def strings(count):
        if count > 65536:
            raise ValueError("SDNA names exceed bound")
        values = []
        for _ in range(count):
            value = bytearray()
            while True:
                b = stream.read(1)
                if not b or len(value) > 1024:
                    raise ValueError("SDNA name truncated/oversized")
                if b == b"\0":
                    break
                value.extend(b)
            values.append(value.decode("ascii"))
        stream.seek((stream.tell() + 3) & ~3)
        return values
    tag(b"SDNA");tag(b"NAME");strings(integer())
    tag(b"TYPE");types = strings(integer())
    tag(b"TLEN");stream.seek(len(types)*2, 1);stream.seek((stream.tell()+3)&~3)
    tag(b"STRC");count = integer()
    if count > 65536:
        raise ValueError("SDNA structures exceed bound")
    names = []
    for _ in range(count):
        raw = stream.read(4)
        if len(raw) != 4:
            raise ValueError("SDNA structure truncated")
        type_index, fields = struct.unpack(endian + "HH", raw)
        if type_index >= len(types) or len(stream.read(fields*4)) != fields*4:
            raise ValueError("SDNA fields truncated")
        names.append(types[type_index])
    return names


def identity(path, expected, maximum):
    if not path.is_file() or not 0 < path.stat().st_size <= maximum:
        raise ValueError("source file size outside bound")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    actual = digest.hexdigest()
    if actual != expected.lower():
        raise ValueError("exact source SHA-256 differs")
    return {"bytes": path.stat().st_size, "sha256": actual}


def member_name(name):
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts or "\\" in name or ":" in name:
        raise ValueError("unsafe archive member name")
    return str(p)


def collada(data):
    if len(data) > MAX_MEMBER or b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        raise ValueError("bounded XML without DTD/entity required")
    root = ET.fromstring(data)
    ns = {"c": "http://www.collada.org/2005/11/COLLADASchema"}
    if root.tag != "{" + ns["c"] + "}COLLADA":
        raise ValueError("Collada namespace differs")
    asset = root.find("c:asset", ns)
    nodes = root.findall(".//c:visual_scene//c:node", ns)
    skins = root.findall(".//c:controller/c:skin", ns)
    geometries = []
    for g in root.findall(".//c:library_geometries/c:geometry", ns):
        positions = []
        for ref in g.findall("c:mesh/c:vertices/c:input", ns):
            if ref.get("semantic") == "POSITION":
                source_id = ref.get("source", "").lstrip("#")
                for source in g.findall("c:mesh/c:source", ns):
                    if source.get("id") == source_id:
                        accessor = source.find("c:technique_common/c:accessor", ns)
                        positions.append(int(accessor.get("count")))
        primitives = []
        for tag in ("triangles", "polylist", "polygons"):
            for p in g.findall("c:mesh/c:" + tag, ns):
                primitives.append({"kind": tag, "count": int(p.get("count")), "material": p.get("material")})
        geometries.append({"id": g.get("id"), "position_counts": positions, "primitives": primitives})
    return {
        "version": root.get("version"),
        "authoring_tools": [x.text for x in root.findall(".//c:contributor/c:authoring_tool", ns)],
        "up_axis": asset.findtext("c:up_axis", namespaces=ns) if asset is not None else None,
        "unit": asset.find("c:unit", ns).attrib if asset is not None and asset.find("c:unit", ns) is not None else None,
        "geometries": geometries,
        "joint_nodes": [{"name": n.get("name"), "sid": n.get("sid"), "id": n.get("id")} for n in nodes if n.get("type") == "JOINT"],
        "skin_controllers": [{"mesh_source": s.get("source"), "vertex_weights_count": int(s.find("c:vertex_weights", ns).get("count")) if s.find("c:vertex_weights", ns) is not None else None} for s in skins],
        "animation_channels": len(root.findall(".//c:library_animations//c:channel", ns)),
        "animation_clips": len(root.findall(".//c:library_animation_clips/c:animation_clip", ns)),
        "materials": [m.get("id") for m in root.findall(".//c:library_materials/c:material", ns)],
        "image_references": [x.text for x in root.findall(".//c:library_images/c:image/c:init_from", ns)],
    }


def inspect_zip(path, expected):
    result = identity(path, expected, 256 * 1024 * 1024)
    with zipfile.ZipFile(path) as z:
        entries = z.infolist()
        if len(entries) > 128 or len({e.filename for e in entries}) != len(entries):
            raise ValueError("bounded unique ZIP inventory required")
        result["members"] = []
        for entry in entries:
            name = member_name(entry.filename)
            if entry.flag_bits & 1 or entry.file_size > 128 * 1024 * 1024:
                raise ValueError("encrypted/oversized member refused")
            row = {"name": name, "bytes": entry.file_size, "compressed_bytes": entry.compress_size}
            suffix = PurePosixPath(name).suffix.lower()
            if suffix == ".dae":
                if entry.file_size > MAX_MEMBER:
                    raise ValueError("Collada size exceeds extraction bound")
                with z.open(entry) as stream:
                    data = stream.read(MAX_MEMBER + 1)
                row["sha256"] = hashlib.sha256(data).hexdigest()
                row["collada"] = collada(data)
            elif suffix == ".fbx":
                with z.open(entry) as stream:
                    header = stream.read(27)
                row["binary_fbx_version"] = struct.unpack_from("<I", header, 23)[0] if header[:23] == b"Kaydara FBX Binary  \x00\x1a\x00" else None
            elif suffix == ".png":
                with z.open(entry) as stream:
                    header = stream.read(33)
                if len(header) != 33 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
                    raise ValueError("PNG header invalid")
                row["png"] = {"width": int.from_bytes(header[16:20], "big"), "height": int.from_bytes(header[20:24], "big"), "bit_depth": header[24], "color_type": header[25]}
            result["members"].append(row)
    result["animations_not_imported"] = True
    return result


def inspect_blend(path, expected, dependency_dir):
    result = identity(path, expected, 32 * 1024 * 1024)
    if dependency_dir:
        sys.path.insert(0, str(dependency_dir.resolve()))
    import zstandard
    if zstandard.__version__ != "0.25.0":
        raise ValueError("pinned zstandard 0.25.0 required")
    with path.open("rb") as handle:
        magic = handle.read(4)
        handle.seek(0)
        if magic != b"\x28\xb5\x2f\xfd":
            raise ValueError("expected Zstandard source magic")
        # Limit the decompressor window and streamed output, not just compressed size.
        decoder = zstandard.ZstdDecompressor(max_window_size=8*1024*1024)
        with decoder.stream_reader(handle, read_across_frames=True) as stream:
            header = stream.read(12)
            if len(header) != 12 or header[:7] != b"BLENDER" or header[7:8] not in (b"_", b"-") or header[8:9] not in (b"v", b"V"):
                raise ValueError("legacy Blender header invalid")
            pointer = 8 if header[7:8] == b"-" else 4
            endian = "<" if header[8:9] == b"v" else ">"
            result.update({"container": "Zstandard", "blender_version": header[9:12].decode("ascii"), "pointer_bytes": pointer, "byte_order": "little" if endian == "<" else "big"})
            consumed = 12
            codes = collections.Counter()
            struct_counts = collections.Counter()
            schema = None
            complete = False
            for _ in range(65536):
                size = 16 + pointer
                if consumed + size > MAX_BLEND_READ:
                    break
                bhead = stream.read(size)
                if len(bhead) != size:
                    raise ValueError("incomplete Blender block header")
                consumed += size
                code = bhead[:4].rstrip(b"\x00").decode("ascii", "backslashreplace")
                body_size = struct.unpack_from(endian + "I", bhead, 4)[0]
                sdna_index, elements = struct.unpack_from(endian + "II", bhead, 8+pointer)
                if consumed + body_size > MAX_BLEND_READ:
                    result["next_block_over_budget"] = {"code": code, "bytes": body_size}
                    break
                remaining = body_size
                dna = bytearray()
                while remaining:
                    piece = stream.read(min(remaining, 65536))
                    if not piece:
                        raise ValueError("truncated Blender block body")
                    remaining -= len(piece)
                    consumed += len(piece)
                    if code == "DNA1":
                        dna.extend(piece)
                    if decoder.memory_size() > MAX_BLEND_READ:
                        raise ValueError("decoder context exceeds memory bound")
                codes[code] += 1
                if code not in ("DNA1", "ENDB", "REND", "TEST"):
                    struct_counts[sdna_index] += elements
                if code == "DNA1":
                    schema = dna_struct_names(dna, endian)
                if code == "ENDB":
                    complete = True
                    break
            decoded = {schema[i]: n for i,n in struct_counts.items() if schema and i < len(schema)}
            result.update({"streamed_bytes": consumed, "stream_limit": MAX_BLEND_READ, "decoder_memory_bytes": decoder.memory_size(), "complete_block_inventory": complete, "block_codes": dict(codes), "sdna_struct_element_counts": decoded, "rig_animation_compatibility_verified": False})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slayer", type=Path, required=True)
    parser.add_argument("--slayer-sha", required=True)
    parser.add_argument("--imp", type=Path, required=True)
    parser.add_argument("--imp-sha", required=True)
    parser.add_argument("--dependency-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {"schema": "iw7.doom-source-inspection/1", "ready": False, "slayer": inspect_zip(args.slayer, args.slayer_sha), "imp": inspect_blend(args.imp, args.imp_sha, args.dependency_dir)}
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"ready": False, "slayer_members": len(result["slayer"]["members"]), "imp": result["imp"]}, indent=2))


if __name__ == "__main__":
    main()

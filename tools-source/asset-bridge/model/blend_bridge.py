"""Bounded H1 -> IW7 blend-stream conversion, not an XSB/FF/model importer.

The pinned ZoneTool converter handles influences 1..4, but copies all eight
counts. Refuse unsupported groups instead of emitting inconsistent counts/data.
Weights are opaque uint16 words: their engine interpretation is NOT established.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

PIN = "fab935826c898806855376662a8a03317b3ad8f1"
MAX_BYTES = 1024 * 1024
SCHEMA = "iw7.asset-bridge.h1-blend/1"
FIELDS = {"schema", "blend_vert_counts", "vertex_count", "bone_count", "rigid_vert_list_count"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_metadata(meta):
    require(type(meta) is dict and set(meta) == FIELDS, "exact blend metadata fields required")
    require(meta["schema"] == SCHEMA, "unsupported blend metadata schema")
    counts = meta["blend_vert_counts"]
    require(type(counts) is list and len(counts) == 8, "eight blend counts required")
    # H1 declares signed shorts; do not reproduce the native unsigned cast.
    require(all(type(n) is int and 0 <= n <= 32767 for n in counts), "H1 nonnegative int16 counts required")
    require(not any(counts[4:]), "influences 5..8 are unsupported; conversion refused")
    require(type(meta["vertex_count"]) is int and 1 <= meta["vertex_count"] <= 65535,
            "vertex_count must be a positive uint16")
    require(type(meta["rigid_vert_list_count"]) is int and meta["rigid_vert_list_count"] == 0,
            "this profile requires zero rigid lists")
    require(sum(counts) == meta["vertex_count"], "blend counts must cover every vertex")
    # Deliberately excludes client bones / extended palettes in this profile.
    # H1 XModel::numBones is uint8, so the largest representable count is 255.
    require(type(meta["bone_count"]) is int and 1 <= meta["bone_count"] <= 255,
            "this profile requires 1..255 H1 model bones, without client bones")
    return counts


def convert_h1(payload, meta):
    """Convert exact H1 raw little-endian uint16 records; preserve weight words."""
    counts = validate_metadata(meta)
    expected = sum((2 * influences - 1) * count * 2 for influences, count in enumerate(counts, 1))
    require(type(payload) is bytes and len(payload) == expected <= MAX_BYTES,
            "H1 blend byte count differs (truncation, trailing bytes or budget)")
    output = bytearray()
    offset = 0
    for influences, count in enumerate(counts[:4], 1):
        width = 2 * influences - 1
        for _ in range(count):
            record = list(struct.unpack_from("<" + "H" * width, payload, offset))
            offset += 2 * width
            # H1 interleaves bone and weight after the initial bone.
            for index in [0] + list(range(1, width, 2)):
                require(record[index] % 64 == 0, "H1 bone offset must be divisible by 64")
                record[index] //= 64
                require(record[index] < meta["bone_count"], "H1 bone index outside model skeleton")
            output.extend(struct.pack("<" + "H" * (width + 1), *record, 0))
    require(offset == len(payload) and len(output) <= MAX_BYTES, "conversion bounds")
    return bytes(output)


def inspect_iw7(payload, meta):
    """Independent readback: decode records into bones and untouched weights.

    Does not call the forward converter or interpret/normalize stored weights.
    The result is also suitable for preflighting an existing raw IW7 blend blob.
    """
    counts = validate_metadata(meta)
    expected = sum(4 * influences * count for influences, count in enumerate(counts, 1))
    require(type(payload) is bytes and len(payload) == expected <= MAX_BYTES,
            "IW7 blend byte count differs (truncation, trailing bytes or budget)")
    offset, records = 0, []
    for group in range(4):
        influences = group + 1
        for _ in range(counts[group]):
            bone = struct.unpack_from("<H", payload, offset)[0]
            offset += 2
            bones, weights = [bone], []
            for _ in range(group):
                bone, weight = struct.unpack_from("<HH", payload, offset)
                offset += 4
                bones.append(bone)
                weights.append(weight)
            require(struct.unpack_from("<H", payload, offset)[0] == 0, "IW7 trailing record word must be zero")
            offset += 2
            require(all(bone < meta["bone_count"] for bone in bones), "IW7 bone index outside model skeleton")
            records.append({"bones": bones, "weight_words": weights})
    require(offset == len(payload), "IW7 readback must consume every byte")
    return records


def verify_correspondence(source, converted, meta):
    """Compare independent readback with each original H1 word, not a re-encode."""
    counts = validate_metadata(meta)
    records = inspect_iw7(converted, meta)
    expected = sum((2 * i - 1) * n * 2 for i, n in enumerate(counts, 1))
    require(type(source) is bytes and len(source) == expected <= MAX_BYTES, "H1 source correspondence length")
    offset = 0
    used = set()
    for record in records:
        for i, bone in enumerate(record["bones"]):
            require(struct.unpack_from("<H", source, offset)[0] == bone * 64, "bone correspondence differs")
            offset += 2
            used.add(bone)
            if i:
                require(struct.unpack_from("<H", source, offset)[0] == record["weight_words"][i - 1],
                        "weight word correspondence differs")
                offset += 2
    require(offset == len(source), "H1 correspondence must consume every byte")
    return {"schema": "iw7.asset-bridge.blend-result/1", "zonetool_reference": PIN,
            "vertices": len(records), "bone_indices_used": sorted(used),
            "blend_vert_counts": counts, "h1_bytes": len(source), "iw7_bytes": len(converted),
            "h1_sha256": hashlib.sha256(source).hexdigest(),
            "iw7_sha256": hashlib.sha256(converted).hexdigest(),
            "independent_word_readback": True, "weight_words_preserved": True,
            "weight_direction_engine_verified": False, "xsb_emitted": False,
            "ff_built": False, "render_verified": False}


def unlinked(path):
    require(path.is_absolute(), "absolute file path required")
    # Reject dot segments before resolving; no link-following canonicalization.
    require(".." not in path.parts, "parent traversal refused")
    for part in (path, *path.parents):
        require(not part.is_symlink() and not part.is_junction(), "linked file ancestry refused")


def read_bounded(path, limit):
    unlinked(path)
    require(path.is_file(), "input must be a regular file")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    require(len(data) <= limit, "input file exceeds budget")
    return data


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate metadata field")
        result[key] = value
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--h1-blend", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="fresh raw IW7 .u16.bin; not .xsb")
    args = parser.parse_args(argv)
    try:
        meta = json.loads(read_bounded(args.metadata, 4096), object_pairs_hook=unique_object)
        source = read_bounded(args.h1_blend, MAX_BYTES)
        converted = convert_h1(source, meta)
        receipt = verify_correspondence(source, converted, meta)
        unlinked(args.output)
        require(args.output.name.endswith(".u16.bin"), "output must be a raw .u16.bin file")
        require(args.output.parent.is_dir(), "existing output directory required")
        # Exclusive creation refuses existing assets, inputs and hardlink aliases.
        with args.output.open("xb") as stream:
            require(stream.write(converted) == len(converted), "short output write")
        require(read_bounded(args.output, MAX_BYTES) == converted, "disk readback differs")
        print(json.dumps(receipt, indent=2))
        return 0
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""Bounded decoded T7 component snapshots, not a native asset/file reader.

Only original fixtures qualify this profile. Passing means the local checks
completed; it never authorizes native conversion, export or engine loading.
"""
import math
import struct

PIN = "fab935826c898806855376662a8a03317b3ad8f1"
MAX_BYTES = 4 * 1024 * 1024


class Refusal(ValueError):
    def __init__(self, code, detail):
        self.code = code
        super().__init__(f"{code}: {detail}")


def require(ok, code, detail):
    if not ok:
        raise Refusal(code, detail)


def integer(value, low, high, field):
    require(type(value) is int and low <= value <= high, "integer_range", field)
    return value


def schema(value, keys):
    require(type(value) is dict and set(value) == set(keys), "snapshot_schema", "exact declared fields required")


def blob(value, size, field):
    require(type(value) is bytes and size <= MAX_BYTES and len(value) == size, "array_length", field)
    return value


def names(value, count):
    require(type(value) is list and len(value) == count, "bone_names", "resolved names count")
    require(all(type(n) is str and 0 < len(n) <= 128 and n.isascii()
                and all(32 < ord(c) < 127 for c in n) for n in value),
            "bone_names", "bounded printable ASCII names, no string-table IDs")
    require(len(set(value)) == count, "bone_names", "unique names")


def evidence(component):
    return {"profile": "t7-decoded-animated-components-v1", "component": component,
            "source_pin": PIN, "component_checks_passed": True,
            "ready": False, "real_t7_provenance": False,
            "complete_native_reader": False, "engine_verified": False}


def quaternion(values, field):
    require(all(math.isfinite(v) and -1 <= v <= 1 for v in values), "quaternion", field)
    require(abs(sum(v * v for v in values) - 1) <= .002, "quaternion", field + " near-unit policy")
    # Same bounded float -> short operation as game/shared.cpp:304-307.
    # Python int and C++ cast both truncate toward zero. No normalization/clamp.
    return tuple(int(v * 32767) for v in values)


def preflight_skeleton(s):
    schema(s, ("numBones", "numRootBones", "numCosmeticBones", "names", "parentList",
               "tagAngles", "tagPositions", "partClassification", "baseMat", "positionLayout"))
    n = integer(s["numBones"], 2, 255, "numBones")
    require(type(s["numRootBones"]) is int and s["numRootBones"] == 1, "root_profile", "one root only")
    require(type(s["numCosmeticBones"]) is int and s["numCosmeticBones"] == 0, "cosmetic_bones", "untested converter path")
    require(s["positionLayout"] == "original-declaration-shaped-xyz12", "position_stride_unresolved",
            "T7 declaration is 12 bytes; Load_Stream comment says 16; no native stride selected")
    names(s["names"], n)
    parents = blob(s["parentList"], n - 1, "parentList")
    require(all(1 <= d <= i for i, d in enumerate(parents, 1)), "parent_distance", "backward relative parent index")
    blob(s["tagAngles"], 8 * (n - 1), "tagAngles")
    blob(s["tagPositions"], 12 * (n - 1), "tagPositions")
    blob(s["partClassification"], n, "partClassification")
    blob(s["baseMat"], 32 * n, "baseMat")
    angles = [quaternion(row, "tagAngles") for row in struct.iter_unpack("<4e", s["tagAngles"])]
    require(all(math.isfinite(v) for row in struct.iter_unpack("<3f", s["tagPositions"]) for v in row),
            "nonfinite_position", "tagPositions")
    for row in struct.iter_unpack("<8f", s["baseMat"]):
        require(all(math.isfinite(v) for v in row), "nonfinite_bind", "baseMat")
        quaternion(row[:4], "baseMat")
        require(abs(row[7] - 2 / sum(v * v for v in row[:4])) < .001, "bind_transweight", "original positive-bind policy")
    return {**evidence("skeleton"), "bones": n, "iw7_angle_words": angles,
            "native_position_stride_verified": False, "bind_hierarchy_consistency_verified": False}


def decode_stream_weights(payload, vertex_count, bone_count):
    """Source-shaped words; does not assume any T7 vertex ordering invariant."""
    integer(vertex_count, 1, 65535, "vertCount")
    integer(bone_count, 2, 255, "bone_count")
    blob(payload, vertex_count * 12, "GfxStreamWeight")
    rows = []
    for index, raw in enumerate(struct.iter_unpack("<4B4H", payload)):
        values, ids = raw[:4], raw[4:]
        active = sum(v != 0 for v in values)
        require(active > 0 and all(values[:active]) and not any(values[active:]),
                "weight_holes", f"vertex {index}: positive contiguous influences required")
        require(sum(values) == 255, "weight_sum", f"vertex {index}: sum 255 is a conservative profile policy")
        require(len(set(ids[:active])) == active and all(i < bone_count for i in ids[:active]),
                "weight_bone_ids", f"vertex {index}: distinct raw IDs within skeleton")
        require(not any(ids[active:]), "inactive_weight_id", f"vertex {index}: unused IDs must be zero")
        words = [ids[0]]
        for k in range(1, active):
            words.extend((ids[k], values[k - 1]))
        words.append(0)
        rows.append({"vertex": index, "influences": active, "ids": ids[:active],
                     "source_values": values[:active], "iw7_words": tuple(words)})
    return rows


def preflight_weights(payload, vertex_count, bone_count):
    rows = decode_stream_weights(payload, vertex_count, bone_count)
    classes = [r["influences"] for r in rows]
    require(classes == sorted(classes), "weight_vertex_order_loss",
            "pinned converter groups weights without moving vertex attributes or triangle indices")
    return {**evidence("weights"), "vertices": vertex_count,
            "histogram": [classes.count(i) for i in range(1, 5)], "rows": rows,
            "weight_direction_verified": False, "t7_grouping_invariant_verified": False}


STREAMS = {"dataByte": 1, "dataShort": 2, "dataInt": 4, "randomDataShort": 2,
           "randomDataByte": 1, "randomDataInt": 4, "indices": 0, "extraChannelData": 1}
NARROWED = ("dataByteCount", "dataShortCount", "dataIntCount", "randomDataIntCount")
FLAGS = ("bLoop", "bLoopSync", "bDelta", "bDelta3D", "bLeftHandGripIK", "bHasBoneMask", "bExtraChannel")
ZERO_COUNTS = ("streamedFileSize", "numIKPitchLayers", "numIKPitchBones", "notifyCount",
               "startupNotifyCount", "shutdownNotifyCount", "assetType")
ABSENT = ("ikPitchLayersPresent", "ikPitchBonesPresent", "notifyPresent",
          "startupNotifyPresent", "shutdownNotifyPresent", "deltaPartPresent")
CLIP_FIELDS = ("numframes", "numBones", "boneCount", "names", "framerate", "frequency",
               "primedLength", "loopEntryTime", *FLAGS, *ZERO_COUNTS, *ABSENT,
               *STREAMS, *(k + "Count" if k != "indices" else "indexCount" for k in STREAMS))


def preflight_clip(c, skeleton_names):
    """Validate representable fields and only the pinned rotation short prefix.

    Byte/ushort index schedule semantics are deliberately not decoded. Passing
    cannot establish a complete clip, even when all short words are consumed.
    """
    schema(c, CLIP_FIELDS)
    for field in NARROWED:
        integer(c[field], 0, 0xFFFFFFFF, field)
        require(c[field] <= 65535, "counter_uint16_loss", field + " would be truncated before copy")
    frames = integer(c["numframes"], 1, 65535, "numframes")
    total = integer(c["numBones"], 2, 255, "numBones")
    bc = c["boneCount"]
    require(type(bc) is list and len(bc) == 10, "bone_categories", "ten counters")
    for count in bc:
        integer(count, 0, 65535, "boneCount[]")
        require(count <= 255, "bone_counter_uint8_loss", "release assertions cannot prevent narrowing")
    require(sum(bc[:5]) == sum(bc[5:9]) == bc[9] == total, "bone_categories", "rotation/translation partitions")
    require(bc[5:8] == [0, 0, 0], "translation_unsupported", "only no-translation category qualified")
    names(c["names"], total)
    require(type(skeleton_names) is list and 2 <= len(skeleton_names) <= 255, "clip_binding", "bounded skeleton names")
    names(skeleton_names, len(skeleton_names))
    require(set(c["names"]) <= set(skeleton_names), "clip_binding", "clip names must resolve in skeleton")
    for field in FLAGS + ABSENT:
        require(type(c[field]) is bool, "boolean_field", field)
        require(field == "bLoop" or not c[field], "channel_or_delta_loss", field)
    for field in ZERO_COUNTS:
        integer(c[field], 0, 0xFFFFFFFF, field)
        require(c[field] == 0, "channel_or_metadata_loss", field)
    for field in ("primedLength", "loopEntryTime"):
        require(type(c[field]) in (int, float) and math.isfinite(c[field]) and c[field] == 0,
                "timing_metadata_loss", field)
    for field in ("framerate", "frequency"):
        require(type(c[field]) in (int, float) and math.isfinite(c[field]) and 0 < c[field] <= 1000,
                "clip_rate", field)
    size = 0
    for field, stride in STREAMS.items():
        counter = "indexCount" if field == "indices" else field + "Count"
        count = integer(c[counter], 0, 0xFFFFFFFF, counter)
        stride = stride or (2 if frames > 255 else 1)
        size += count * stride
        require(size <= MAX_BYTES, "clip_byte_budget", "4 MiB maximum before stream traversal")
        blob(c[field], count * stride, field)
    require(c["extraChannelDataCount"] == 0, "extra_channel_loss", "converter omits extraChannelData")
    require(not any(c[k + "Count"] for k in ("dataInt", "randomDataInt", "randomDataByte")),
            "clip_stream_unsupported", "not part of qualified rotation prefix")
    require(c["dataShortCount"] != 0 or c["randomDataShortCount"] == 0,
            "random_short_copy_loss", "converter copies random shorts only inside dataShortCount branch")
    data, random = c["dataShort"], c["randomDataShort"]
    cursor, random_cursor, samples = 0, 0, []

    def take_data(words):
        nonlocal cursor
        require(cursor + words * 2 <= len(data), "short_prefix_truncated", "dataShort")
        part = data[cursor:cursor + words * 2]
        cursor += words * 2
        return part

    for category, width in ((1, 2), (2, 4)):
        for _ in range(bc[category]):
            frame_count = struct.unpack("<H", take_data(1))[0]
            require(frame_count <= frames, "frame_sample_count", "sample count exceeds numframes + 1")
            if frames > 255:
                raw_index = struct.unpack("<H", take_data(1))[0]
                require(raw_index <= frames, "frame_index_range", "raw prefix word; schedule semantics unresolved")
            byte_count = (frame_count + 1) * width * 2
            require(random_cursor + byte_count <= len(random), "short_prefix_truncated", "randomDataShort")
            for offset in range(random_cursor, random_cursor + byte_count, width * 2):
                samples.append(quaternion(struct.unpack_from("<" + "e" * width, random, offset), "rotation sample"))
            random_cursor += byte_count
    for category, width in ((3, 2), (4, 4)):
        for _ in range(bc[category]):
            samples.append(quaternion(struct.unpack("<" + "e" * width, take_data(width)), "static rotation"))
    require(cursor == len(data) and random_cursor == len(random), "short_tail_unsupported",
            "uninterpreted trailing short words cannot be qualified")
    return {**evidence("clip_rotation_prefix"), "bones": total, "rotation_words": samples,
            "data_short_words_consumed": cursor // 2, "random_short_words_consumed": random_cursor // 2,
            "uninterpreted_schedule_bytes": len(c["dataByte"]) + len(c["indices"]),
            "clip_semantics_complete": False, "key_schedule_verified": False}

"""Offline proof of proposed source-surface permutation; not a native exporter.

All 16 bytes of GfxStreamVertex, all 12 position bytes and all 12 weight bytes
move together. Triangle indices are remapped by the inverse permutation. Only
resident pure-skinned snapshots without rigid/collision lists fit this proposal.
"""
import struct

from .preflight import blob, decode_stream_weights, evidence, integer, require, schema


def regroup_surface(s):
    schema(s, ("positions", "attributes", "triangles", "weights", "vertCount", "triCount",
               "boneCount", "sharedFlags", "surfaceFlags", "vertListCount", "partBits"))
    count = integer(s["vertCount"], 1, 65535, "vertCount")
    tris = integer(s["triCount"], 1, 65535, "triCount")
    for field, expected in (("sharedFlags", 0), ("surfaceFlags", 2), ("vertListCount", 0)):
        require(type(s[field]) is int and s[field] == expected, "surface_profile", field)
    blob(s["partBits"], 48, "partBits")
    require(not any(s["partBits"][32:]), "part_bits_loss", "converter retains only 8 of 12 words")
    for field, stride in (("positions", 12), ("attributes", 16), ("weights", 12)):
        blob(s[field], stride * count, field)
    blob(s["triangles"], 6 * tris, "triangles")
    indices = struct.unpack("<" + "H" * (3 * tris), s["triangles"])
    require(all(i < count for i in indices), "triangle_index", "surface-local indices required")
    rows = decode_stream_weights(s["weights"], count, s["boneCount"])
    new_to_old = sorted(range(count), key=lambda i: rows[i]["influences"])
    old_to_new = [0] * count
    for new, old in enumerate(new_to_old):
        old_to_new[old] = new
    output = dict(s)
    for field, stride in (("positions", 12), ("attributes", 16), ("weights", 12)):
        output[field] = b"".join(s[field][old * stride:(old + 1) * stride] for old in new_to_old)
    output["triangles"] = struct.pack("<" + "H" * len(indices), *(old_to_new[i] for i in indices))
    return {**evidence("regrouping_proposal"), "snapshot": output, "new_to_old": new_to_old,
            "old_to_new": old_to_new, "native_patch_applied": False,
            "native_patch_compiled": False, "real_donor_occurrence_observed": False}

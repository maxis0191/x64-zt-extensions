"""Independent known IW7 blend-row reader. No source decoder/writer imports.

Stored weight direction remains unresolved; results are wire words, not a
deformation or a claim that T7 weights carry identical engine semantics.
"""
import struct


def read_blend(payload, counts, bone_count):
    if (type(payload) is not bytes or type(counts) is not list or len(counts) != 4
            or any(type(n) is not int or not 0 <= n <= 65535 for n in counts)
            or not 1 <= sum(counts) <= 65535
            or type(bone_count) is not int or not 2 <= bone_count <= 255):
        raise ValueError("bounded blend input")
    if len(payload) != sum(n * (i + 1) * 4 for i, n in enumerate(counts)):
        raise ValueError("exact blend length")
    offset, result = 0, []
    for influence_count, count in enumerate(counts, 1):
        for _ in range(count):
            row = struct.unpack_from("<" + "H" * (2 * influence_count), payload, offset)
            offset += 4 * influence_count
            ids = (row[0],) + tuple(row[2 * k - 1] for k in range(1, influence_count))
            stored = tuple(row[2 * k] for k in range(1, influence_count))
            if row[-1] or len(set(ids)) != influence_count or any(i >= bone_count for i in ids):
                raise ValueError("blend IDs or padding")
            if any(not 0 < w < 255 for w in stored) or sum(stored) >= 255:
                raise ValueError("positive byte-range stored weights and residual")
            result.append({"ids": ids, "stored_weights": stored, "residual": 255 - sum(stored), "words": row})
    return result

"""Bounded CPU oracle for candidate skin bytes; never writes/builds game assets.

This module does not import a writer or its unpacker. Matrix linear-blend skinning
is checked against an original analytical fixture. IW7 stored-weight direction
remains an explicit hypothesis until an engine/retail deformation proves it.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

RETAIL_BIND_SHA = "3b1b61b7ce7186341e3ff2f5e80a8baa4d9e5365531ba6ed6ea04b0192e7728b"
TOOL_PIN = "fab935826c898806855376662a8a03317b3ad8f1"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def finite(values):
    return all(type(v) in (int, float) and math.isfinite(v) for v in values)


def multiply(a, b):
    return [[sum(a[r][k] * b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]


def transform(m, v):
    require(len(v) == 3 and finite(v), "finite three-coordinate vertex")
    return [sum(m[r][c] * v[c] for c in range(3)) + m[r][3] for r in range(3)]


def rigid_matrix(quat, translation):
    require(len(quat) == 4 and len(translation) == 3 and finite([*quat, *translation]), "finite rigid transform")
    norm = sum(v * v for v in quat)
    require(0.99 < norm < 1.01, "bounded unit quaternion")
    x, y, z, w = [v / math.sqrt(norm) for v in quat]
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w), translation[0]],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w), translation[1]],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y), translation[2]],
            [0., 0., 0., 1.]]


def inverse_rigid(m):
    # Row-major matrices acting on column points: R^-1=R^T, t^-1=-R^T*t.
    return [[*[m[c][r] for c in range(3)], -sum(m[c][r] * m[c][3] for c in range(3))] for r in range(3)] + [[0., 0., 0., 1.]]


def decode_global_bind(parents, angles, positions, base_mats):
    """Compare baseMat global binds with parent/global * local tags independently."""
    require(isinstance(parents, bytes) and isinstance(angles, bytes) and isinstance(positions, bytes) and isinstance(base_mats, bytes), "byte streams")
    count = len(parents) + 1
    require(1 <= count <= 255 and len(angles) == 8 * (count - 1) and len(positions) == 12 * (count - 1) and len(base_mats) == 32 * count, "one-root bounded bind lengths")
    bases = []
    for i in range(count):
        row = struct.unpack_from("<8f", base_mats, 32 * i)
        require(finite(row), "finite baseMat")
        norm = sum(v * v for v in row[:4])
        require(norm > 0 and abs(row[7] - 2 / norm) < 0.001, "baseMat quaternion transWeight relationship")
        bases.append(rigid_matrix(row[:4], row[4:7]))
    reconstructed = [bases[0]]
    max_error = 0.
    for i, distance in enumerate(parents, 1):
        require(0 < distance <= i, "backward parent distance")
        raw = struct.unpack_from("<4h", angles, 8 * (i - 1))
        q = [value / 32767 for value in raw]
        local = rigid_matrix(q, struct.unpack_from("<3f", positions, 12 * (i - 1)))
        world = multiply(reconstructed[i - distance], local)
        reconstructed.append(world)
        max_error = max(max_error, max(abs(world[r][c] - bases[i][r][c]) for r in range(4) for c in range(4)))
    require(max_error < 0.0002, "baseMat must match positive global bind, not inverse/local bind")
    return bases, max_error


def decode_one_two_blend(payload, counts, num_bones, stored_weight_bone):
    """IW7 words inferred from pinned converters; weight assignment is explicit."""
    require(isinstance(payload, bytes) and isinstance(counts, list) and len(counts) == 8 and all(type(v) is int and 0 <= v <= 64 for v in counts), "bounded histogram")
    require(counts[2:] == [0] * 6 and 0 < sum(counts) <= 64, "one/two influences only")
    require(type(num_bones) is int and 1 <= num_bones <= 255, "bone count")
    require(stored_weight_bone in ("first", "second"), "explicit unverified stored-weight direction")
    require(len(payload) == 4 * counts[0] + 8 * counts[1], "exact blend bytes and strides")
    rows = []
    offset = 0
    for _ in range(counts[0]):
        bone, padding = struct.unpack_from("<HH", payload, offset)
        offset += 4
        require(bone < num_bones and padding == 0, "raw bone ID and zero padding")
        rows.append({bone: 1.})
    for _ in range(counts[1]):
        first, second, weight, padding = struct.unpack_from("<HHHH", payload, offset)
        offset += 8
        require(first < num_bones and second < num_bones and first != second and 0 < weight < 255 and padding == 0, "dual IDs, byte-range weight and padding")
        fraction = weight / 255
        rows.append({first: fraction if stored_weight_bone == "first" else 1 - fraction,
                     second: fraction if stored_weight_bone == "second" else 1 - fraction})
    return rows


def linear_blend(vertices, weights, bind_matrices, pose_matrices):
    require(0 < len(vertices) == len(weights) <= 64 and len(bind_matrices) == len(pose_matrices), "bounded skin inputs")
    skin = [multiply(pose, inverse_rigid(bind)) for bind, pose in zip(bind_matrices, pose_matrices)]
    result = []
    for vertex, row in zip(vertices, weights):
        require(isinstance(row, dict) and 1 <= len(row) <= 2 and all(type(b) is int and 0 <= b < len(skin) for b in row), "valid bone references")
        require(finite(list(row.values())) and all(w > 0 for w in row.values()) and abs(sum(row.values()) - 1) < 1e-9, "normalized positive weights")
        transformed = {bone: transform(skin[bone], vertex) for bone in row}
        result.append([sum(row[bone] * transformed[bone][axis] for bone in row) for axis in range(3)])
    return result


def original_fixture():
    """Original 8-vertex strip; fixed analytical values are independent of codecs."""
    vertices = [[0., y, z] for z in (0., 16., 4., 12.) for y in (-4., 4.)]
    weights = [{0: 1.}, {0: 1.}, {1: 1.}, {1: 1.}, {0: .75, 1: .25}, {0: .75, 1: .25}, {0: .25, 1: .75}, {0: .25, 1: .75}]
    k = 1 / math.sqrt(2)
    bend = [[0., -4., 0.], [0., 4., 0.], [0., -12 * k, 8 + 4 * k], [0., -4 * k, 8 + 12 * k],
            [0., -3., 5 - 2 * k], [0., 3 + 2 * k, 5.], [0., -1 - 6 * k, 9.], [0., 1., 9 + 6 * k]]
    return vertices, weights, bend


def verify_original_candidate(parents, angles, positions, bases, blend, counts, stored_weight_bone="second"):
    require(parents == b"\x01" and counts == [4, 4, 0, 0, 0, 0, 0, 0], "exact original hierarchy/histogram")
    bind, bind_error = decode_global_bind(parents, angles, positions, bases)
    require(len(bind) == 2 and max(abs(bind[0][r][c] - (1. if r == c else 0.)) for r in range(4) for c in range(4)) < 1e-7 and abs(bind[1][2][3] - 8) < 1e-7, "original root/pivot")
    vertices, source_weights, expected = original_fixture()
    root = rigid_matrix((0, 0, 0, 1), (0, 0, 0))
    child = rigid_matrix((math.sin(math.pi / 8), 0, 0, math.cos(math.pi / 8)), (0, 0, 8))
    ideal = linear_blend(vertices, source_weights, bind, [root, child])
    require(max(math.dist(a, b) for a, b in zip(ideal, expected)) < 1e-10, "matrix oracle vs closed-form source bend")
    decoded = decode_one_two_blend(blend, counts, 2, stored_weight_bone)
    expected_ids = [(0,), (0,), (1,), (1,), (0, 1), (0, 1), (0, 1), (0, 1)]
    require([tuple(row) for row in decoded] == expected_ids, "original vertex/bone correspondence")
    quantized = linear_blend(vertices, decoded, bind, [root, child])
    quant_error = max(math.dist(a, b) for a, b in zip(quantized, expected))
    require(quant_error < 0.005, "asymmetric source-vs-wire deformation tolerance")
    rest = linear_blend(vertices, decoded, bind, bind)
    require(max(math.dist(a, b) for a, b in zip(rest, vertices)) < 1e-10, "bind pose identity")
    opposite = decode_one_two_blend(blend, counts, 2, "first" if stored_weight_bone == "second" else "second")
    opposite_error = max(math.dist(a, b) for a, b in zip(linear_blend(vertices, opposite, bind, [root, child]), expected))
    return {"vertices": 8, "bones": 2, "blend_bytes": len(blend), "bind_matrix_error": bind_error,
            "quantization_error_units": quant_error, "opposite_weight_error_units": opposite_error,
            "stored_weight_direction": stored_weight_bone + "_bone_hypothesis_only", "engine_deformation_verified": False,
            "pixels_verified": False, "animation_verified": False}


class BindPrefixReader:
    """Read only through XMB baseMat. Trailing asset data is deliberately untouched."""
    def __init__(self, payload):
        require(isinstance(payload, bytes) and 0 < len(payload) <= 65536, "bounded XMB")
        self.payload, self.offset, self.entries = payload, 0, []

    def take(self, count):
        require(0 <= count <= 65536 and self.offset + count <= len(self.payload), "truncated XMB prefix")
        value = self.payload[self.offset:self.offset + count]
        self.offset += count
        return value

    def array(self, size, count):
        require(self.take(2) == b"\x08\x01" and struct.unpack("<I", self.take(4))[0] == count, "array kind/presence/count")
        value = self.take(size * count)
        self.entries.append(("array", value))
        return value

    def string(self):
        kind = self.take(1)
        if kind == b"\x09":
            entry, index = struct.unpack("<II", self.take(8))
            require(entry < len(self.entries) and index == 0 and self.entries[entry][0] == "string", "bounded string reference")
            return self.entries[entry][1]
        require(kind == b"\x06" and self.take(1) == b"\x01", "string kind/presence")
        end = self.payload.find(b"\0", self.offset, self.offset + 129)
        require(end >= self.offset, "bounded terminated string")
        value = self.take(end - self.offset + 1)[:-1].decode("ascii")
        self.entries.append(("string", value))
        return value


def inspect_retail_bind(payload):
    require(isinstance(payload, bytes) and 0 < len(payload) <= 65536, "bounded retail bind bytes")
    require(hashlib.sha256(payload).hexdigest() == RETAIL_BIND_SHA, "exact retained retail XMB hash")
    reader = BindPrefixReader(payload)
    model = reader.array(736, 1)
    require(reader.string() == "park_clown_zombie", "exact retail model")
    count, roots = model[20:22]
    client = struct.unpack_from("<H", model, 24)[0]
    require((count, roots, client) == (106, 1, 0), "exact measured retail skeleton")
    for _ in range(count):
        reader.string()
    parents = reader.array(1, count - 1)
    angles = reader.array(8, count - 1)
    positions = reader.array(12, count - 1)
    reader.array(1, count)
    bases = reader.array(32, count)
    _, error = decode_global_bind(parents, angles, positions, bases)
    return {"source_sha256": RETAIL_BIND_SHA, "source_bytes": len(payload), "bones": count,
            "consumed_prefix_bytes": reader.offset, "global_bind_max_matrix_element_error": error,
            "full_asset_verified": False, "retail_blend_bytes_inspected": False,
            "engine_deformation_verified": False, "pixels_verified": False, "tool_pin": TOOL_PIN}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retail-bind", type=Path, required=True)
    args = parser.parse_args()
    require(args.retail_bind.is_absolute() and args.retail_bind.is_file() and not args.retail_bind.is_symlink() and not args.retail_bind.is_junction(), "absolute regular retained input")
    require(args.retail_bind.stat().st_size <= 65536, "bounded retail input before read")
    print(json.dumps(inspect_retail_bind(args.retail_bind.read_bytes()), indent=2))


if __name__ == "__main__":
    main()

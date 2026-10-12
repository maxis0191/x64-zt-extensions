"""Independent readback of the current resident static T7 -> IW7 dump profile.

No converter, fixture generator, engine or native preparer is imported. The
shared bounded record reader supplies cursor/type/end checks; this module adds
the current IW7 layouts and conservative typed backward-reference handling.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import stat
import struct

from export_contract import validate_export

_base_path = Path(__file__).resolve().parent.parent / "h1-fixture" / "inspect_fixture.py"
_spec = importlib.util.spec_from_file_location("_t7_readback_record_base", _base_path)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)
check, values, zero_except = _base.check, _base.values, _base.zero_except
MODEL_LIMIT, MESH_LIMIT = 1024**2, 16 * 1024**2
FLOAT32_MAX = float.fromhex("0x1.fffffep+127")
BOUNDS_REL_TOLERANCE = 4 * 2**-23


class Reader(_base.Reader):
    """Reuse bounded take/start/finish, without the old fixture's 256-item cap.

    The native ledger is untyped. We accept only backward references to an
    already read, identical logical layout, wholly within its element range.
    Absent records and references never extend the ledger. Cross-layout native
    pointer reinterpretations are deliberately unqualified and rejected.
    """
    def __init__(self, data, limit):
        check(type(data) is bytes and 0 < len(data) <= limit <= MESH_LIMIT,
              "input size/type outside readback bound")
        self.data, self.pos, self.records, self.entries = data, 0, {}, []

    def alias(self, label, kind, layout, stride, count):
        self.records[label] = self.pos
        if self.data[self.pos:self.pos + 1] != b"\x09":
            return None
        self.take(1)
        entry, index = struct.unpack("<II", self.take(8))
        check(entry < len(self.entries), "forward or missing alias: " + label)
        old_kind, old_layout, old_stride, old_count, data = self.entries[entry]
        check((kind, layout, stride) == (old_kind, old_layout, old_stride),
              "alias layout mismatch: " + label)
        check(0 < count <= old_count and index <= old_count - count,
              "alias element range: " + label)
        if kind in (6, 7):
            check(index == 0, "name alias index: " + label)
            return data
        return data[index * stride:(index + count) * stride]

    def array(self, label, stride, expected, *, layout=None):
        check(type(expected) is int and 0 <= expected <= 65535 and
              type(stride) is int and 0 < stride <= 736, "array bounds")
        layout = layout or label
        data = self.alias(label, 8, layout, stride, expected)
        if data is not None:
            return data
        if not self.start(label, 8):
            check(expected == 0, "required array absent: " + label)
            return b""
        count, = struct.unpack("<I", self.take(4))
        check(0 < count == expected, "array count mismatch: " + label)
        # Division check before multiplication/allocation also documents the
        # overflow boundary for native consumers of these uint32 record counts.
        check(count <= (len(self.data) - self.pos) // stride, "truncated array: " + label)
        data = self.take(count * stride)
        self.entries.append((8, layout, stride, count, data))
        return data

    def name(self, label, kind, expected, *, layout="string"):
        check(kind in (6, 7), "unsupported name type")
        value = self.alias(label, kind, layout, 1, 1 if expected is not None else 0)
        if value is None:
            if not self.start(label, kind):
                check(expected is None, "required name absent: " + label)
                return None
            stop = self.data.find(b"\0", self.pos, self.pos + 256)
            check(stop > self.pos, "name missing bounded terminator: " + label)
            raw = self.take(stop - self.pos + 1)[:-1]
            check(all(0x20 <= b < 0x7f for b in raw), "nonportable name: " + label)
            value = raw.decode("ascii")
            self.entries.append((kind, layout, 1, 1, value))
        check(expected is not None and value == expected, "name mismatch: " + label)
        return value


def finite(items, label):
    check(all(math.isfinite(v) for v in items), "nonfinite " + label)
    return items


def bounds(data, offset, label):
    center = finite(values(data, offset, "3f"), label)
    half = finite(values(data, offset + 12, "3f"), label)
    check(all(v >= 0 for v in half), "negative half extent: " + label)
    low = tuple(c - h for c, h in zip(center, half))
    high = tuple(c + h for c, h in zip(center, half))
    check(all(abs(v) <= FLOAT32_MAX for v in (*low, *high)), "bounds exceed float32 range: " + label)
    return {"center": center, "half_extent": half, "min": low, "max": high}


def pointers(data, offsets):
    for offset in offsets:
        check(values(data, offset, "Q")[0] != 0, "required pointer missing at " + str(offset))


def root_bits(data, offset):
    bits = values(data, offset, "8I")
    check(bits[0] in (0, 0x80000000) and not any(bits[1:]), "part bits outside root bone")
    return bits


def parse_model(data, manifest):
    r = Reader(data, MODEL_LIMIT)
    h = r.array("model", 736, 1)
    check(tuple(h[8:15]) == (0, 1, 0, 1, 255, 6, 1), "model LOD metadata outside profile")
    check(values(h, 20, "3B") == (1, 1, 0) and values(h, 24, "HH") == (0, 1),
          "model bone/surface counts outside profile")
    scale, = finite(values(h, 28, "f"), "model scale")
    radius, = finite(values(h, 40, "f"), "model radius")
    check(scale > 0 and radius >= 0, "invalid model scale/radius")
    model_bounds = bounds(h, 44, "model bounds")
    distance, surfaces, first = values(h, 224, "fHH")
    check(math.isfinite(distance) and distance >= 0 and (surfaces, first) == (1, 0),
          "invalid selected LOD descriptor")
    part_bits = root_bits(h, 240)
    required = (0, 152, 184, 192, 216, 232, 616, 624)
    pointers(h, required)
    for i in range(1, 6):
        check(values(h, 224 + 64 * i, "f")[0] == 1000000.0, "unused LOD distance")
    check(h[704] == h[720] == 255, "unused model index sentinel")
    zero_except(h, [(o, 8) for o in required] +
                [(8, 7), (20, 2), (26, 6), (36, 32), (224, 8), (240, 32), (704, 1), (720, 1)] +
                [(224 + 64 * i, 4) for i in range(1, 6)])
    model_name = r.name("model_name", 6, manifest["output_model_name"])
    root_name = r.name("root_bone", 6, manifest["root_bone_name"])
    for label, stride in (("parents", 1), ("angles", 8), ("positions", 12)):
        r.array(label, stride, 0)
    classification = r.array("classification", 1, 1)[0]
    base_mat = finite(values(r.array("base_mat", 32, 1), 0, "8f"), "root bind matrix")
    for label, stride in (("reactive_parts", 16), ("reactive_tweaks", 16), ("coll_surfs", 36)):
        r.array(label, stride, 0)
    bone = r.array("bone_info", 28, 1)
    bone_bounds = bounds(bone, 0, "bone bounds")
    bone_radius, = finite(values(bone, 24, "f"), "bone radius squared")
    check(bone_radius >= 0, "negative bone radius squared")
    mip, = finite(values(r.array("mip_radius", 2, 1), 0, "e"), "mip radius")
    check(mip >= 0, "negative mip radius")
    pointers(r.array("material_handles", 8, 1), (0,))
    material = r.name("material", 7, manifest["material_dependencies"][0], layout="material")
    mesh = r.name("lod0", 7, manifest["output_mesh_name"], layout="xmodel_surfs")
    for i in range(1, 6):
        r.name("lod" + str(i), 7, None, layout="xmodel_surfs")
    for label in ("physics_asset", "physics_fx_shape", "scriptable_mover", "procedural_bones"):
        r.name(label, 7, None, layout=label)
    for label, stride in (("unknown03", 1), ("unknown_vec3", 12), ("unknown04", 24)):
        r.array(label, stride, 0)
    r.finish()
    return {"name": model_name, "mesh": mesh, "root_bone": root_name, "material": material,
            "bones": 1, "roots": 1, "surfaces": surfaces, "part_bits": part_bits,
            "bounds": model_bounds, "radius": radius, "scale": scale, "lod_distance": distance,
            "bone_bounds": bone_bounds, "bone_radius_squared": bone_radius,
            "root_bind_matrix": base_mat, "classification": classification, "mip_radius": mip}


def parse_mesh(data, manifest):
    r = Reader(data, MESH_LIMIT)
    h = r.array("mesh", 56, 1)
    pointers(h, (0, 8))
    check(values(h, 16, "H") == (1,), "mesh surface count outside profile")
    part_bits = root_bits(h, 20)
    zero_except(h, [(0, 18), (20, 32)])
    name = r.name("mesh_name", 6, manifest["output_mesh_name"])
    surf = r.array("surfaces", 256, 1)
    flags, vertices, triangles, rigid_count, subdiv = values(surf, 0, "3H2B")
    check(flags == 0x80 and rigid_count == 1 and subdiv == 0, "surface flags/streams outside profile")
    counts = manifest["selected_counts"]
    check(3 <= vertices == counts["vertices"] <= 65535 and
          1 <= triangles == counts["triangles"] <= 65535, "mesh counts differ from manifest")
    pointers(surf, (32, 40, 72))
    surface_bits = root_bits(surf, 224)
    zero_except(surf, [(0, 7), (32, 16), (72, 8), (224, 32)])
    packed = r.array("vertices", 32, vertices)
    positions = []
    for offset in range(0, len(packed), 32):
        positions.append(finite(values(packed, offset, "3f"), "vertex position"))
        finite(values(packed, offset + 20, "2e"), "vertex UV")
    faces = list(struct.iter_unpack("<3H", r.array("triangles", 6, triangles)))
    for face in faces:
        check(all(i < vertices for i in face), "triangle index out of range")
        a, b, c = (positions[i] for i in face)
        # Cross-product area, computed in Python binary64 from read
        # float32 positions. No fixed mesh topology, winding or cube constants.
        u, v = tuple(bi - ai for ai, bi in zip(a, b)), tuple(ci - ai for ai, ci in zip(a, c))
        cross = (u[1]*v[2] - u[2]*v[1], u[2]*v[0] - u[0]*v[2], u[0]*v[1] - u[1]*v[0])
        area2 = sum(x*x for x in cross)
        check(math.isfinite(area2) and area2 > 0, "degenerate triangle")
    rigid = values(r.array("rigid_lists", 16, 1), 0, "4HQ")
    check(rigid == (0, vertices, 0, triangles, 0), "rigid root/coverage/collision outside profile")
    for label in ("blend", "lmap", "tension", "tension_accum"):
        r.absent_raw(label)
    r.finish()
    return {"name": name, "surfaces": 1, "vertices": vertices, "triangle_count": triangles,
            "part_bits": part_bits, "surface_part_bits": surface_bits,
            "positions": positions, "triangles": faces,
            "position_min": tuple(min(p[i] for p in positions) for i in range(3)),
            "position_max": tuple(max(p[i] for p in positions) for i in range(3))}


def inspect_pair(model_bytes, mesh_bytes, manifest, request):
    """Verify these immutable byte snapshots, not native provenance or T7 fidelity."""
    validate_export(manifest, request)
    for role, data, limit in (("model", model_bytes, MODEL_LIMIT), ("mesh", mesh_bytes, MESH_LIMIT)):
        item = manifest[role]
        check(type(data) is bytes and 0 < len(data) <= limit and len(data) == item["bytes"],
              role + " artifact size/type differs")
        check(hashlib.sha256(data).hexdigest() == item["sha256"].lower(), role + " artifact digest differs")
    model, mesh = parse_model(model_bytes, manifest), parse_mesh(mesh_bytes, manifest)
    for key in ("bones", "roots", "surfaces"):
        check(model[key] == manifest["selected_counts"][key], "model counts differ from manifest")
    check(model["part_bits"] == mesh["part_bits"], "model LOD and mesh part bits differ")
    for p in mesh["positions"]:
        for i, value in enumerate(p):
            center, half = model["bounds"]["center"][i], model["bounds"]["half_extent"][i]
            tolerance = BOUNDS_REL_TOLERANCE * max(1.0, abs(center), half)
            check(abs(value - center) <= half + tolerance, "vertex outside model bounds")
    return {"schema": "iw7.t7-iw7-static-readback/1", "geometry_profile": manifest["geometry_profile"],
            "requested_zone": request["zone"], "selected_source_lod": request["lod"],
            "artifact_snapshots": {role: dict(manifest[role]) for role in ("model", "mesh")},
            "model": model, "mesh": {key: value for key, value in mesh.items() if key not in ("positions", "triangles")},
            "receipt_contract_verified": True, "artifact_snapshot_bytes_verified": True,
            "serialized_parse_verified": True, "triangle_indices_and_areas_verified": True,
            "positions_within_model_bounds_verified": True,
            "native_provenance_verified": False, "process_acceptance_verified": False,
            "source_geometry_correspondence_verified": False, "asset_zone_ownership_verified": False,
            "dependency_payloads_verified": False, "packed_shading_semantics_verified": False,
            "bone_space_geometry_verified": False, "engine_io_verified": False,
            "runtime_verified": False, "ready": False}


def read_bounded(path, limit):
    """One bounded regular-file snapshot; does not qualify an outer Run receipt."""
    path = Path(path).absolute()
    for item in (*reversed(path.parents), path):
        info = item.lstat()
        check(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
              "symlink/reparse input refused")
    before = path.stat()
    check(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= limit, "input file size/type")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        check((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
              (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns), "input changed before read")
        data = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    check((opened.st_size, opened.st_mtime_ns) == (after.st_size, after.st_mtime_ns) and
          len(data) == opened.st_size, "input changed during read")
    return data


def read_json(path):
    def pairs(items):
        value = {}
        for key, item in items:
            check(key not in value, "duplicate JSON field")
            value[key] = item
        return value

    def nonfinite(_):
        raise ValueError("nonfinite JSON number")

    return json.loads(read_bounded(path, 4096).decode("utf-8"), object_pairs_hook=pairs, parse_constant=nonfinite)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True, help="Closed export root containing xmodel/ and xsurface/")
    args = parser.parse_args()
    try:
        request, manifest = read_json(args.request), read_json(args.manifest)
        validate_export(manifest, request)
        model = read_bounded(args.root / manifest["model"]["relative_path"], MODEL_LIMIT)
        mesh = read_bounded(args.root / manifest["mesh"]["relative_path"], MESH_LIMIT)
        result = inspect_pair(model, mesh, manifest, request)
    except (ValueError, OSError) as error:
        parser.exit(1, "Readback refused: " + str(error) + "\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

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

from export_contract import validate_export, geometry_work_bytes_upper_bound, MANIFEST_LIMIT_V2, GEOMETRY_WORK_LIMIT

_base_path = Path(__file__).resolve().parent.parent / "h1-fixture" / "inspect_fixture.py"
_spec = importlib.util.spec_from_file_location("_t7_readback_record_base", _base_path)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)
check, values, zero_except = _base.check, _base.values, _base.zero_except
MODEL_LIMIT, MESH_LIMIT = 1024**2, 16 * 1024**2
V1, V2 = 't7-iw7-resident-static-v1', 't7-iw7-resident-static-v2'
MANIFEST_LIMIT = MANIFEST_LIMIT_V2
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
        self.name_spans, self.name_records, self.alias_entry = {}, {}, None

    def alias(self, label, kind, layout, stride, count):
        self.records[label] = self.pos
        self.alias_entry = None
        if self.data[self.pos:self.pos + 1] != b"\x09":
            return None
        self.take(1)
        entry, index = struct.unpack("<II", self.take(8))
        check(entry < len(self.entries), "forward or missing alias: " + label)
        old_kind, old_layout, old_stride, old_count, data = self.entries[entry]
        self.alias_entry = entry
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
            entry = len(self.entries)
            self.name_spans[entry] = (self.pos, stop)
            raw = self.take(stop - self.pos + 1)[:-1]
            check(all(0x20 <= b < 0x7f for b in raw), "nonportable name: " + label)
            value = raw.decode("ascii")
            self.entries.append((kind, layout, 1, 1, value))
        else:
            entry = self.alias_entry
        check(expected is not None and value == expected, "name mismatch: " + label)
        self.name_records[label] = {'definition': entry, 'string_span': self.name_spans[entry]}
        return value


def geometry_layout(manifest):
    """Independent allocation/work gate, also used by direct parse callers.

    Every logical occurrence counts, even if the serialization uses aliases.
    This is not a Python RAM/CPU estimate or a serialized file size limit.
    """
    version = manifest.get('geometry_profile')
    check((manifest.get('schema'), version) in (('iw7.t7-iw7-resident-export/1', V1),
                                               ('iw7.t7-iw7-resident-export/2', V2)), 'mixed export/profile versions')
    counts = manifest['selected_counts']
    check(type(counts) is dict and set(counts) == {'bones', 'roots', 'surfaces', 'vertices', 'triangles'} and
          all(type(v) is int for v in counts.values()) and counts['bones'] == counts['roots'] == 1,
          'geometry count types/root profile')
    n = counts['surfaces']
    check(1 <= n <= (1 if version == V1 else 255), 'surface count outside selected profile')
    if version == V1:
        check('surface_records' not in manifest and 'geometry_work_bytes_upper_bound' not in manifest,
              'v2 geometry fields in v1')
        records = [dict(index=0, material_slot=0, vertices=counts['vertices'], triangles=counts['triangles'])]
    else:
        records = manifest['surface_records']
    check(type(records) is list and len(records) == n, 'ordered surface records required')
    vertices = triangles = 0
    for i, record in enumerate(records):
        check(type(record) is dict and set(record) == {'index', 'material_slot', 'vertices', 'triangles'} and
              all(type(v) is int for v in record.values()) and record['index'] == record['material_slot'] == i and
              3 <= record['vertices'] <= 65535 and 1 <= record['triangles'] <= 65535, 'surface record order/count')
        vertices += record['vertices']
        triangles += record['triangles']
    work = geometry_work_bytes_upper_bound(n, vertices, triangles)
    check(vertices == counts['vertices'] and triangles == counts['triangles'],
          'aggregate geometry count/work budget')
    if version == V2:
        check(type(manifest['geometry_work_bytes_upper_bound']) is int and
              manifest['geometry_work_bytes_upper_bound'] == work, 'geometry work formula mismatch')
    check(type(manifest['material_dependencies']) is list and len(manifest['material_dependencies']) == n,
          'ordered material slots required')
    return records, work


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


def parse_model(data, manifest, *, with_material_records=False):
    records, _ = geometry_layout(manifest)
    n = len(records)
    r = Reader(data, MODEL_LIMIT)
    h = r.array("model", 736, 1)
    check(tuple(h[8:15]) == (0, 1, 0, 1, 255, 6, 1), "model LOD metadata outside profile")
    check(values(h, 20, "3B") == (1, 1, 0) and values(h, 24, "HH") == (0, n),
          "model bone/surface counts outside profile")
    scale, = finite(values(h, 28, "f"), "model scale")
    radius, = finite(values(h, 40, "f"), "model radius")
    check(scale > 0 and radius >= 0, "invalid model scale/radius")
    model_bounds = bounds(h, 44, "model bounds")
    distance, surfaces, first = values(h, 224, "fHH")
    check(math.isfinite(distance) and distance >= 0 and (surfaces, first) == (n, 0),
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
    mips = finite(values(r.array("mip_radius", 2, n), 0, str(n) + "e"), "mip radius")
    check(all(mip >= 0 for mip in mips), "negative mip radius")
    pointers(r.array("material_handles", 8, n), tuple(8*i for i in range(n)))
    material_labels = ['material' if n == 1 else 'material_' + str(i) for i in range(n)]
    materials = [r.name(label, 7, expected, layout='material')
                 for label, expected in zip(material_labels, manifest['material_dependencies'])]
    mesh = r.name("lod0", 7, manifest["output_mesh_name"], layout="xmodel_surfs")
    for i in range(1, 6):
        r.name("lod" + str(i), 7, None, layout="xmodel_surfs")
    for label in ("physics_asset", "physics_fx_shape", "scriptable_mover", "procedural_bones"):
        r.name(label, 7, None, layout=label)
    for label, stride in (("unknown03", 1), ("unknown_vec3", 12), ("unknown04", 24)):
        r.array(label, stride, 0)
    r.finish()
    result = {"name": model_name, "mesh": mesh, "root_bone": root_name,
            "bones": 1, "roots": 1, "surfaces": surfaces, "part_bits": part_bits,
            "bounds": model_bounds, "radius": radius, "scale": scale, "lod_distance": distance,
            "bone_bounds": bone_bounds, "bone_radius_squared": bone_radius,
            "root_bind_matrix": base_mat, "classification": classification}
    if manifest['geometry_profile'] == V1:
        result.update(material=materials[0], mip_radius=mips[0])
    else:
        result.update(materials=materials, mip_radii=mips)
    if with_material_records:
        result['material_records'] = [dict(slot=i, source=materials[i], **r.name_records[label])
                                      for i, label in enumerate(material_labels)]
    return result


def parse_mesh(data, manifest, *, model_bounds=None):
    records, work = geometry_layout(manifest)
    n = len(records)
    legacy = manifest['geometry_profile'] == V1
    r = Reader(data, MESH_LIMIT)
    h = r.array("mesh", 56, 1)
    pointers(h, (0, 8))
    check(values(h, 16, "H") == (n,), "mesh surface count outside profile")
    part_bits = root_bits(h, 20)
    zero_except(h, [(0, 18), (20, 32)])
    name = r.name("mesh_name", 6, manifest["output_mesh_name"])
    headers = r.array("surfaces", 256, n)
    # Check ALL headers/counts before the first geometry scan/allocation.
    for i, record in enumerate(records):
        surf = headers[256*i:256*(i+1)]
        flags, vertices, triangles, rigid_count, subdiv = values(surf, 0, "3H2B")
        check(flags == 0x80 and rigid_count == 1 and subdiv == 0, "surface flags/streams outside profile")
        check(vertices == record['vertices'] and triangles == record['triangles'], "mesh counts differ from manifest")
        pointers(surf, (32, 40, 72))
        root_bits(surf, 224)
        zero_except(surf, [(0, 7), (32, 16), (72, 8), (224, 32)])
    surfaces = []
    for i, record in enumerate(records):
        vertices, triangles = record['vertices'], record['triangles']
        # Labels locate a record; layouts represent stable types across surfaces.
        def label(key):
            return key if legacy else 'surface_' + str(i) + '.' + key
        packed = r.array(label('vertices'), 32, vertices, layout='vertices')
        low, high = [math.inf]*3, [-math.inf]*3
        positions = [] if legacy else None
        for offset in range(0, len(packed), 32):
            position = finite(values(packed, offset, '3f'), 'vertex position')
            finite(values(packed, offset + 20, '2e'), 'vertex UV')
            for axis, value in enumerate(position):
                low[axis], high[axis] = min(low[axis], value), max(high[axis], value)
                if model_bounds is not None:
                    center, half = model_bounds['center'][axis], model_bounds['half_extent'][axis]
                    tolerance = BOUNDS_REL_TOLERANCE * max(1.0, abs(center), half)
                    check(abs(value-center) <= half+tolerance, 'vertex outside model bounds')
            if legacy:
                positions.append(position)
        face_bytes = r.array(label('triangles'), 6, triangles, layout='triangles')
        faces = [] if legacy else None
        for face in struct.iter_unpack('<3H', face_bytes):
            check(all(index < vertices for index in face), 'triangle index out of range')
            a, b, c = (values(packed, index*32, '3f') for index in face)
            u, v = tuple(bi-ai for ai, bi in zip(a, b)), tuple(ci-ai for ai, ci in zip(a, c))
            cross = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
            area2 = sum(x*x for x in cross)
            check(math.isfinite(area2) and area2 > 0, 'degenerate triangle')
            if legacy:
                faces.append(face)
        rigid_bytes = r.array(label('rigid_lists'), 16, 1, layout='rigid_lists')
        check(values(rigid_bytes, 0, '4HQ') == (0, vertices, 0, triangles, 0), 'rigid root/coverage/collision outside profile')
        for key in ('blend', 'lmap', 'tension', 'tension_accum'):
            r.absent_raw(label(key))
        surface = {'index': i, 'material_slot': i, 'vertices': vertices, 'triangle_count': triangles,
                   'surface_part_bits': root_bits(headers[256*i:256*(i+1)], 224),
                   'position_min': tuple(low), 'position_max': tuple(high)}
        if legacy:
            surface.update(positions=positions, triangles=faces)
        else:
            surface['packed_sha256'] = {key: hashlib.sha256(payload).hexdigest() for key, payload in
                                       (('vertices', packed), ('triangles', face_bytes), ('rigid_lists', rigid_bytes))}
        surfaces.append(surface)
    r.finish()
    result = {'name': name, 'surfaces': n, 'vertices': manifest['selected_counts']['vertices'],
              'triangle_count': manifest['selected_counts']['triangles'], 'part_bits': part_bits}
    if legacy:
        result.update({key: value for key, value in surfaces[0].items() if key not in ('index', 'material_slot', 'vertices', 'triangle_count')})
    else:
        result.update(surface_records=surfaces, geometry_work_bytes_upper_bound=work)
    return result


def inspect_pair(model_bytes, mesh_bytes, manifest, request):
    """Verify these immutable byte snapshots, not native provenance or T7 fidelity."""
    validate_export(manifest, request)
    for role, data, limit in (("model", model_bytes, MODEL_LIMIT), ("mesh", mesh_bytes, MESH_LIMIT)):
        item = manifest[role]
        check(type(data) is bytes and 0 < len(data) <= limit and len(data) == item["bytes"],
              role + " artifact size/type differs")
        check(hashlib.sha256(data).hexdigest() == item["sha256"].lower(), role + " artifact digest differs")
    model = parse_model(model_bytes, manifest)
    mesh = parse_mesh(mesh_bytes, manifest, model_bounds=model['bounds'])
    for key in ("bones", "roots", "surfaces"):
        check(model[key] == manifest["selected_counts"][key], "model counts differ from manifest")
    check(model["part_bits"] == mesh["part_bits"], "model LOD and mesh part bits differ")
    return {"schema": "iw7.t7-iw7-static-readback/1" if manifest['geometry_profile'] == V1 else "iw7.t7-iw7-static-readback/2", "geometry_profile": manifest["geometry_profile"],
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


def read_json(path, *, manifest=False):
    def pairs(items):
        value = {}
        for key, item in items:
            check(key not in value, "duplicate JSON field")
            value[key] = item
        return value

    def nonfinite(_):
        raise ValueError("nonfinite JSON number")

    raw = read_bounded(path, MANIFEST_LIMIT if manifest else 4096)
    result = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=nonfinite)
    if manifest:
        limit = MANIFEST_LIMIT if type(result) is dict and result.get('schema') == 'iw7.t7-iw7-resident-export/2' else 4096
        check(len(raw) <= limit, 'manifest exceeds its version size bound')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True, help="Closed export root containing xmodel/ and xsurface/")
    args = parser.parse_args()
    try:
        request, manifest = read_json(args.request), read_json(args.manifest, manifest=True)
        validate_export(manifest, request)
        model = read_bounded(args.root / manifest["model"]["relative_path"], MODEL_LIMIT)
        mesh = read_bounded(args.root / manifest["mesh"]["relative_path"], MESH_LIMIT)
        result = inspect_pair(model, mesh, manifest, request)
    except (ValueError, OSError) as error:
        parser.exit(1, "Readback refused: " + str(error) + "\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

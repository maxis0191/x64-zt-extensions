"""Independent exact-profile IW7 readback against the original H1 input bytes.

Reuses the strict H1 reader/math validation and the rig reader's typed name-alias
rule. No generator, converter, native preparer or serializer is imported. This
checks a dump, not an FF or rendering; native provenance requires its own receipt.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

from inspect_fixture import Reader as H1Reader, check, inspect_model, inspect_surface, values, zero_except

MODEL = "paris_h1_original_cube"
SURFACE = MODEL + "_lod0"
MATERIAL = "paris_h1_original_material"
ORIGINAL_HASHES = ("49c8c9cca648ee4a21b05ccc4e92588ec1b889de932e680dfe3af2db3b055339",
                   "17aedd6d7343cbc48495623be5828efc26022918bdf3e47f57d397eb10d717d2")


class Reader(H1Reader):
    def __init__(self, data):
        check(isinstance(data, bytes) and 0 < len(data) <= 65536, "64 KiB IW7 dump limit")
        super().__init__(data)
        self.entries = []

    def array(self, label, stride, expected):
        data = super().array(label, stride, expected)
        if expected:
            self.entries.append((8, data))
        return data

    def name(self, label, kind, expected):
        # Same bounded typed-name OFFSET rule as animation/rig/read_skin_native.py.
        # Blob aliases are deliberately refused by the inherited array method.
        self.records[label] = self.pos
        if self.data[self.pos:self.pos + 1] == b"\x09":
            self.take(1)
            entry, index = struct.unpack("<II", self.take(8))
            check(entry < len(self.entries) and index == 0 and self.entries[entry][0] == kind,
                  "typed bounded name alias required")
            value = self.entries[entry][1]
            check(value == expected and expected is not None, "name alias identity mismatch")
            return value
        value = super().name(label, kind, expected)
        if value is not None:
            self.entries.append((kind, value))
        return value


def pointer(record, offset):
    check(values(record, offset, "Q")[0] != 0, "required pointer missing at " + str(offset))


def source_array(data, records, label, stride, count):
    pos = records[label]
    check(data[pos:pos + 6] == b"\x08\x01" + struct.pack("<I", count), "source array identity")
    return data[pos + 6:pos + 6 + stride * count]


def read_model(data, original, source_records):
    r = Reader(data)
    h = r.array("model", 736, 1)
    check(tuple(h[8:15]) == (0, 1, 0, 1, 0, 6, 1), "converted model metadata")
    check(values(h, 20, "3B") == (1, 1, 0) and values(h, 24, "HH") == (0, 1), "model bone/surface counts")
    check(values(h, 28, "f") == (1.0,) and h[40:68] == original[6 + 544:6 + 572], "radius/bounds correspondence")
    check(values(h, 120, "8I") == (0x80000000, 0, 0, 0, 0, 0, 0, 0), "noScale root bits")
    pointers = (0, 152, 184, 192, 216, 232, 616, 624)
    for offset in pointers:
        pointer(h, offset)
    check(values(h, 224, "fHH") == (1000.0, 1, 0) and
          values(h, 240, "8I") == (0x80000000, 0, 0, 0, 0, 0, 0, 0), "LOD descriptor")
    check(h[704] == h[720] == 255, "unused index sentinels")
    zero_except(h, [(o, 8) for o in pointers] + [(8, 7), (20, 2), (26, 6), (40, 28),
                (120, 32), (224, 8), (240, 32), (704, 1), (720, 1)])
    r.name("model_name", 6, MODEL)
    r.name("bone_string", 6, "tag_origin")
    for label, stride in (("parents", 1), ("angles", 8), ("positions", 12)):
        r.array(label, stride, 0)
    for label, stride, count in (("classification", 1, 1), ("base_mat", 32, 1)):
        check(r.array(label, stride, count) == source_array(original, source_records, label, stride, count),
              "bind/classification correspondence")
    for label, stride in (("reactive_parts", 16), ("reactive_tweaks", 16), ("coll_surfs", 36)):
        r.array(label, stride, 0)
    for label, stride in (("bone_info", 28), ("mip_radius", 2)):
        check(r.array(label, stride, 1) == source_array(original, source_records, label, stride, 1),
              "bone bounds/mip radius correspondence")
    pointer(r.array("material_handles", 8, 1), 0)
    r.name("material", 7, MATERIAL)
    r.name("lod0", 7, SURFACE)
    for i in range(1, 6):
        r.name("lod" + str(i), 7, None)
    for label in ("physics", "physics_fx", "scriptable", "procedural"):
        r.name(label, 7, None)
    for label, stride in (("unknown03", 1), ("unknownVec3", 12), ("unknown04", 24)):
        r.array(label, stride, 0)
    r.finish()
    return r.records


def read_surface(data, original, source_records):
    r = Reader(data)
    h = r.array("model_surfs", 56, 1)
    pointer(h, 0); pointer(h, 8)
    check(values(h, 16, "H") == (1,) and
          values(h, 20, "8I") == (0x80000000, 0, 0, 0, 0, 0, 0, 0), "surface group identity")
    zero_except(h, ((0, 18), (20, 32)))
    r.name("surface_name", 6, SURFACE)
    s = r.array("surfaces", 256, 1)
    check(values(s, 0, "HHHBB") == (0x80, 24, 12, 1, 0), "converted rigid surface profile")
    check(values(s, 224, "8I") == (0x80000000, 0, 0, 0, 0, 0, 0, 0), "surface root bits")
    for offset in (32, 40, 72):
        pointer(s, offset)
    zero_except(s, ((0, 8), (32, 16), (72, 8), (224, 32)))
    vertices = r.array("vertices", 32, 24)
    source = source_array(original, source_records, "vertices", 32, 24)
    for index in range(24):
        start = index * 32
        actual, prior = vertices[start:start + 32], source[start:start + 32]
        check(actual[:12] == prior[:12] and actual[16:] == prior[16:],
              "vertex position/color/UV/normal/tangent correspondence")
        check(values(actual, 12, "I") == (0x01FE0100,), "selfVisibility codec word")
    for label, stride, count in (("triangles", 6, 12), ("rigid_lists", 16, 1)):
        check(r.array(label, stride, count) == source_array(original, source_records, label, stride, count),
              "topology/rigid root correspondence")
    for label in ("blend", "lmap", "tension", "tension_accum"):
        r.absent_raw(label)
    r.finish()
    return r.records


def inspect_pair(xmb, xsb, h1_xmb, h1_xsb):
    check(tuple(hashlib.sha256(d).hexdigest() for d in (h1_xmb, h1_xsb)) == ORIGINAL_HASHES,
          "exact original H1 inputs required")
    _, model_records = inspect_model(h1_xmb)
    _, surface_records = inspect_surface(h1_xsb)  # Includes independent triangle/UV frame checks.
    read_model(xmb, h1_xmb, model_records)
    read_surface(xsb, h1_xsb, surface_records)
    return {"schema": "iw7.h1-dump-readback/1", "status": "original-h1-iw7-dump-profile-pass",
            "outputs": {name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                        for name, data in (("xmb", xmb), ("xsb", xsb))},
            "vertices_checked": 24, "triangles_checked": 12, "bone_string": "tag_origin",
            "source_bone_token": 0, "bone_engine_token_resolved": False,
            "material_reference": MATERIAL, "material_complete": False,
            "lod_reference": SURFACE, "lod_named_reference_linked": False,
            "whole_zonetool_application": False, "ff_built": False, "render_verified": False,
            "native_provenance_verified": False,
            "provenance_requires": "separate admitted native receipt and output hashes; synthetic tests are insufficient"}


def bounded(path):
    # Consume at most LIMIT+1, even if the file grows after open.
    with path.open("rb", buffering=0) as stream:
        data = stream.read(65537)
    check(0 < len(data) <= 65536, "64 KiB readback limit")
    return data


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--dump-root", type=Path, required=True)
    cli.add_argument("--fixture-root", type=Path, required=True)
    args = cli.parse_args()
    try:
        files = ("xmodel/" + MODEL + ".xmb", "xsurface/" + SURFACE + ".xsb")
        payloads = [bounded(root / name) for root in (args.dump_root, args.fixture_root) for name in files]
        print(json.dumps(inspect_pair(*payloads), indent=2))
    except (OSError, ValueError, struct.error) as error:
        print(json.dumps({"status": "invalid-h1-dump", "error": str(error)}))
        sys.exit(2)

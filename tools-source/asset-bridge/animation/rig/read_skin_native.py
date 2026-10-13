"""Independent strict reader for proposed original two-bone XMB/XSB outputs.

Only synthetic original outputs have exercised this reader so far. No writer
has emitted these files, and source-code packing conformity is not shader proof.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
from read_skin_fixture import read as read_inputs
from skin_oracle import original_fixture, verify_original_candidate

COUNTS = [4, 4, 0, 0, 0, 0, 0, 0]
PARTS = (0xC0000000, 0, 0, 0, 0, 0, 0, 0)
MATERIAL = "mopw/character_park_clown_zombie_shoes"


def require(ok, message):
    if not ok:
        raise ValueError(message)


class Reader:
    def __init__(self, payload):
        require(isinstance(payload, bytes) and 0 < len(payload) <= 65536, "bounded native output")
        self.payload, self.offset, self.entries = payload, 0, []

    def take(self, count):
        require(0 <= count <= 65536 and self.offset + count <= len(self.payload), "truncated native output")
        value = self.payload[self.offset:self.offset + count]
        self.offset += count
        return value

    def blob(self, kind, width, count):
        # This fixed original profile uses separate allocations, no blob aliases.
        require(self.take(1) == bytes([kind]), "native blob kind")
        present = self.take(1)
        require(present == (b"\x01" if count else b"\x00"), "native blob presence")
        if not count:
            return b""
        require(struct.unpack("<I", self.take(4))[0] == count, "native blob count")
        value = self.take(width * count)
        self.entries.append((kind, value))
        return value

    def array(self, width, count):
        return self.blob(8, width, count)

    def raw(self, count):
        return self.blob(10, 1, count)

    def name(self, kind=6, expected=None):
        type_byte = self.take(1)[0]
        if type_byte == 9:
            entry, index = struct.unpack("<II", self.take(8))
            require(entry < len(self.entries) and index == 0 and self.entries[entry][0] == kind, "typed bounded native name alias")
            value = self.entries[entry][1]
        else:
            require(type_byte == kind, "native name kind")
            present = self.take(1)
            require(present == (b"\x00" if expected is None else b"\x01"), "native name presence")
            if present == b"\x00":
                return None
            end = self.payload.find(b"\0", self.offset, self.offset + 129)
            require(end >= self.offset, "bounded native name")
            value = self.take(end - self.offset + 1)[:-1].decode("ascii")
            self.entries.append((kind, value))
        require(value == expected, "exact native model/bone/dependency name")
        return value

    def end(self):
        require(self.offset == len(self.payload), "native trailing bytes")


def pointer(record, offset, present):
    require(bool(struct.unpack_from("<Q", record, offset)[0]) is present, "native pointer presence at " + str(offset))


def zero_except(record, ranges):
    allowed = set()
    for offset, count in ranges:
        allowed.update(range(offset, offset + count))
    require(all(value == 0 for i, value in enumerate(record) if i not in allowed), "unexpected native field/padding/dependency")


def packed_unit(word):
    return tuple(2 * ((word >> shift) & 1023) / 1023 - 1 for shift in (0, 10, 20)), word >> 30


def read_surface(payload, inputs, hypothesis, *, cpu_ff_loaded=False):
    require(type(cpu_ff_loaded) is bool, "explicit CPU read scope flag")
    require(hypothesis in ("first", "second"), "explicit profile hypothesis")
    name = "paris_doom_skin_two_bone_" + hypothesis + "_a_lod0"
    reader = Reader(payload)
    outer = reader.array(56, 1)
    pointer(outer, 0, True)
    pointer(outer, 8, True)
    require(struct.unpack_from("<H", outer, 16)[0] == 1 and struct.unpack_from("<8I", outer, 20) == PARTS, "native one-surface outer record")
    zero_except(outer, [(0, 18), (20, 32)])
    reader.name(expected=name)
    surface = reader.array(256, 1)
    require(struct.unpack_from("<HHHBB", surface) == (0x86, 8, 6, 0, 0), "native skinned surface counts/flags")
    require(list(struct.unpack_from("<8H", surface, 8)) == COUNTS and struct.unpack_from("<I", surface, 24)[0] == 48, "native blend counts/bytes")
    for offset in (32, 40, 80):
        pointer(surface, offset, True)
    require(struct.unpack_from("<8I", surface, 224) == PARTS, "native proposed surface partBits")
    # Authored input must have no GPU state. A separately selected CPU-only FF
    # read preserves the observed opaque buffer slot without qualifying it.
    allowed = [(0, 28), (32, 16), (80, 8), (224, 32)]
    if cpu_ff_loaded:
        allowed.append((88, 8))
    zero_except(surface, allowed)
    vertices = reader.array(32, 8)
    positions = inputs["positions.f32.bin"]
    uv_source = inputs["uv.f32.bin"]
    expected_positions, _, _ = original_fixture()
    require(len(positions) == 96 and list(struct.iter_unpack("<3f", positions)) == [tuple(v) for v in expected_positions], "independently fixed position inputs")
    require(len(uv_source) == 64 and struct.unpack("<16f", uv_source) == (0., 0., 1., 0., 0., 1., 1., 1., 0., .25, 1., .25, 0., .75, 1., .75), "independently fixed UV inputs")
    max_normal_error = 0.
    for i in range(8):
        record = vertices[32 * i:32 * (i + 1)]
        require(record[:12] == positions[12 * i:12 * (i + 1)], "actual native original vertex positions")
        visibility, color, uv, normal, tangent = struct.unpack_from("<5I", record, 12)
        require(visibility == 0x01FE0100 and color == 0xFFFFFFFF, "native candidate selfVisibility/opaque color")
        # IEEE binary16 decoding is from Python's stdlib, not the writer codec.
        expected_uv = struct.unpack_from("<2f", uv_source, 8 * i)
        require(struct.unpack("<2e", struct.pack("<I", uv)) == expected_uv, "native IEEE half UV correspondence")
        require(normal == 0xE0080000 and tangent == 0x200FFE00, "native pinned-source normal/tangent words")
        n, normal_alpha = packed_unit(normal)
        t, tangent_alpha = packed_unit(tangent)
        max_normal_error = max(max_normal_error, max(abs(n[k] - (-1., 0., 0.)[k]) for k in range(3)), max(abs(t[k] - (0., 1., 0.)[k]) for k in range(3)))
        require(normal_alpha == 3 and tangent_alpha == 0 and max_normal_error <= 1 / 1023 + 1e-12, "source-code unit vectors and negative tangent handedness")
    triangles = reader.array(6, 6)
    require(triangles == inputs["triangles.u16.bin"], "actual native original triangles")
    require(struct.unpack("<18H", triangles) == (0, 4, 1, 1, 4, 5, 4, 6, 5, 5, 6, 7, 6, 2, 7, 7, 2, 3), "independently fixed native triangles")
    reader.array(16, 0)
    blend = reader.raw(48)
    require(blend == inputs[hypothesis + ".blend.u16.bin"], "actual native profile blend bytes")
    for _ in range(3):
        reader.raw(0)
    reader.end()
    return {"vertices": 8, "triangles": 6, "blend_bytes": 48, "normal_tangent_component_error": max_normal_error,
            "source_codec_words_verified": True, "iw7_shader_encoding_verified": False}, blend


def read_model(payload, inputs, hypothesis, *, cpu_ff_loaded=False):
    require(type(cpu_ff_loaded) is bool, "explicit CPU read scope flag")
    name = "paris_doom_skin_two_bone_" + hypothesis + "_a"
    reader = Reader(payload)
    model = reader.array(736, 1)
    require(tuple(model[8:15]) == (0, 1, 0, 1, 255, 6, 0), "native single-LOD model metadata")
    require(struct.unpack_from("<I", model, 16)[0] == 0 and tuple(model[20:23]) == (2, 1, 0) and struct.unpack_from("<HH", model, 24) == (0, 1), "native two-bone model flags/counts")
    require(struct.unpack_from("<f", model, 28)[0] == 1. and abs(struct.unpack_from("<f", model, 40)[0] - math.sqrt(272)) < 1e-5 and struct.unpack_from("<6f", model, 44) == (0., 0., 8., 0., 4., 8.), "native model scale/radius/bounds")
    for offset in (0, 152, 160, 168, 176, 184, 192, 216, 232, 616, 624):
        pointer(model, offset, True)
    require(struct.unpack_from("<fHH", model, 224) == (1000000., 1, 0) and struct.unpack_from("<8I", model, 240) == PARTS, "native LOD0 descriptor")
    require(model[704] == 255 and model[720] == 255, "native unused-index sentinels")
    allowed = [(0, 15), (20, 2), (26, 6), (40, 28), (152, 48), (216, 56), (616, 16), (704, 1), (720, 1)]
    if cpu_ff_loaded:
        pointer(model, 272, True)
        allowed.append((272, 8))
    zero_except(model, allowed)
    reader.name(expected=name)
    reader.name(expected="tag_origin")
    reader.name(expected="tag_probe")
    parents = reader.array(1, 1)
    angles = reader.array(8, 1)
    tags = reader.array(12, 1)
    require((parents, angles, tags) == (inputs["parents.u8.bin"], inputs["tag-angles.i16.bin"], inputs["tag-positions.f32.bin"]), "native parent/local-tag input correspondence")
    require(reader.array(1, 2) == b"\0\0", "native part classification")
    bases = reader.array(32, 2)
    require(bases == inputs["base-mats.f32.bin"], "native global bind input correspondence")
    reader.array(32, 0)  # ReactiveMotionModelPart, absent count; width unused.
    reader.array(1, 0)   # ReactiveMotionModelTweaks, absent pointer; width unused.
    reader.array(36, 0)
    infos = reader.array(28, 2)
    # Conservative proposal: whole original mesh bounds in each bone's bind
    # coordinates. This does not establish engine culling/deformation behavior.
    expected_infos = ((0., 0., 8., 0., 4., 8., 272.), (0., 0., 0., 0., 4., 8., 80.))
    require(tuple(struct.iter_unpack("<7f", infos)) == expected_infos, "native proposed conservative bone bounds")
    require(reader.array(2, 1) == b"\0\0", "native invHighMipRadius")
    handles = reader.array(8, 1)
    pointer(handles, 0, True)
    reader.name(7, MATERIAL)
    reader.name(7, name + "_lod0")
    for _ in range(5):
        reader.name(7, None)
    reader.name(7, None)  # PhysicsAsset
    reader.name(7, None)  # PhysicsFXShape
    reader.name(7, None)  # ScriptableMoverDef
    reader.name(7, None)  # ProceduralBones
    for width in (1, 12, 24):
        reader.array(width, 0)
    reader.end()
    return {"bones": 2, "roots": 1, "client_bones": 0, "lods": 1, "complete_model_bytes_read": True,
            "bone_bounds_engine_verified": False}, (parents, angles, tags, bases)


def verify_outputs(xmb, xsb, inputs, hypothesis):
    require(hypothesis in ("first", "second"), "explicit native profile hypothesis")
    model, bind = read_model(xmb, inputs, hypothesis)
    surface, blend = read_surface(xsb, inputs, hypothesis)
    oracle = verify_original_candidate(*bind, blend, COUNTS, hypothesis)
    return {"schema": "iw7.doom-two-bone-native-read/1", "hypothesis": hypothesis, "model": model,
            "surface": surface, "cpu_oracle": oracle, "xmb_sha256": hashlib.sha256(xmb).hexdigest(),
            "xsb_sha256": hashlib.sha256(xsb).hexdigest(), "native_writer_receipt_verified": False,
            "part_bits_engine_verified": False, "draw_verified": False, "pixels_verified": False, "ready": False}


def read_file(path):
    require(path.is_absolute() and path.is_file() and not path.is_symlink() and not path.is_junction() and 0 < path.stat().st_size <= 65536, "absolute bounded native output file")
    for parent in path.parents:
        require(not parent.is_symlink() and not parent.is_junction(), "linked native output ancestry")
    return path.read_bytes()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--xmb", type=Path, required=True)
    parser.add_argument("--xsb", type=Path, required=True)
    parser.add_argument("--hypothesis", choices=("first", "second"), required=True)
    args = parser.parse_args()
    read_inputs(args.inputs)
    inputs = {name: (args.inputs / name).read_bytes() for name in ("positions.f32.bin", "uv.f32.bin", "triangles.u16.bin", "parents.u8.bin", "tag-angles.i16.bin", "tag-positions.f32.bin", "base-mats.f32.bin", args.hypothesis + ".blend.u16.bin")}
    print(json.dumps(verify_outputs(read_file(args.xmb), read_file(args.xsb), inputs, args.hypothesis), indent=2))

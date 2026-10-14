"""Independent one-channel root-rotation XAB reader; data proof only, no Run."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import types

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
LEGACY_READER_SHA256 = "1b3630ae9526469fc85a7a0f30ecfaf6e5a3c7bfb78d28a684d9d08b0da01941"
NAME = "paris_original_probe_root_rotate"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def primitives():
    path = BASE / "read_probe.py"
    for part in (path, *path.parents):
        require(not part.is_symlink() and not part.is_junction(), "Linked reader source refused")
    require(path.is_file() and 0 < path.stat().st_size < 65536, "Bounded reader source required")
    payload = path.read_bytes()
    require(len(payload) < 65536 and hashlib.sha256(payload).hexdigest() == LEGACY_READER_SHA256,
            "Pinned independent reader primitives changed")
    module = types.ModuleType("_root_clip_reader_primitives")
    module.__file__ = str(path)
    exec(compile(payload, str(path), "exec"), module.__dict__)
    return module.ProbeReader


def read_root_rotation(data, expected_frequency=1.0, *, ff_roundtrip=False):
    require(type(expected_frequency) in (int, float) and expected_frequency == 1.0,
            "Only frequency candidate 1 is supported")
    require(type(ff_roundtrip) is bool, "Explicit typed FF scope required")
    reader = primitives()(data)
    header = bytearray(reader.array(1, 136))
    for offset in (0, 8, 16, 24, 40, 72):
        require(struct.unpack_from("<Q", header, offset)[0] != 0, "Required root clip pointer is null")
        header[offset:offset + 8] = bytes(8)
    expected = bytearray(136)
    struct.pack_into("<I", expected, 88, 16)
    struct.pack_into("<ffHH", expected, 100, 30.0, 1.0, 4, 1)
    struct.pack_into("<H", expected, 116, 30)
    expected[118] = 1
    # Independent literals from IWXAnim categories, not the producer's constants.
    expected[119:129] = bytes([0, 0, 1, 0, 0, 0, 0, 0, 1, 1])
    expected[129] = 1
    require(header == expected, "Root clip header/profile differs, including padding/optional streams")
    reader.exact_string(NAME)
    reader.exact_string("tag_origin")
    frames = list(reader.array(4, 1))
    require(frames == [0, 10, 20, 30], "Root clip key frames differ")
    require(struct.unpack("<H", reader.array(1, 2))[0] == 3, "Root key-count-minus-one differs")
    packed = list(struct.unpack("<16h", reader.array(16, 2)))
    require(packed == [0, 0, 0, 32767, 12539, 0, 0, 30272,
                       -12539, 0, 0, 30272, 0, 0, 0, 32767], "Original root rotations differ")
    note_id, note_time = struct.unpack("<If", reader.array(1, 8))
    require(note_time == 0.5 and (note_id > 0 if ff_roundtrip else note_id == 3),
            "Root note identity/time differs")
    reader.exact_string("probe_contact")
    require(reader.offset == len(data), "Trailing root clip data")
    samples = []
    for i, target in enumerate((0, 45, -45, 0)):
        q = [v / 32767.0 for v in packed[i * 4:i * 4 + 4]]
        norm = math.sqrt(sum(v * v for v in q))
        require(abs(norm - 1.0) < 0.0001, "Root quaternion is not near unit")
        degrees = math.degrees(2 * math.atan2(q[0], q[3]))
        require(abs(degrees - target) < 0.01, "Root angle differs")
        samples.append({"frame": frames[i], "x_degrees": degrees,
                        "quat_xyzw_div32767": q, "norm_div32767": norm,
                        "norm_div32768": math.sqrt(sum((v / 32768.0) ** 2
                                                       for v in packed[i * 4:i * 4 + 4]))})
    return {"schema": "iw7.original-root-rotation-readback/1",
            "status": "original-root-rotation-data-pass",
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "decoded_profile": "one-tag-origin-four-key-quat4-only",
            "channels": ["tag_origin"], "animated_channel_indices": [0], "samples": samples,
            "translations": "no authored translation streams", "delta_root_motion_authored": False,
            "notetrack": {"name": "probe_contact", "normalized_time": 0.5, "script_string_id": note_id},
            "readback_scope": "ff-redump-profile" if ff_roundtrip else "original-native-writer-profile",
            "decoder_conventions": {"pinned_QuatInt16": 32767, "Greyhound_IW_DivideBySize": 32768},
            "engine_quaternion_normalization_verified": False, "frequency_runtime_verified": False,
            "runtime_tree_binding_verified": False, "runtime_model_binding_verified": False,
            "runtime_root_pose_verified": False, "runtime_world_motion_verified": False,
            "note_delivery_verified": False, "pixels_verified": False, "ready": False,
            "general_xanim_decoder": False,
            "input_provenance": "Bind actual native/FF receipts separately; source fixtures are not artifacts"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xab", type=Path)
    parser.add_argument("--expected-frequency", type=float, required=True)
    parser.add_argument("--ff-roundtrip", action="store_true")
    args = parser.parse_args()
    try:
        require(".." not in args.xab.parts, "Canonical clip path required")
        path = args.xab.absolute()
        for p in (path, *path.parents):
            require(not p.is_symlink() and not p.is_junction(), "Linked root clip ancestry refused")
        with path.open("rb") as stream:
            data = stream.read(65537)
        print(json.dumps(read_root_rotation(data, args.expected_frequency,
                                           ff_roundtrip=args.ff_roundtrip), indent=2))
    except (OSError, ValueError, struct.error) as error:
        print(json.dumps({"status": "invalid-root-rotation", "error": str(error)}))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

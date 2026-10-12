"""Read the original two-bone inputs and four-key XAB, then compute CPU poses.

No native process, FF, runtime script, writer import or asset generation. The
matrix result assumes normalized quaternions and linear blend skinning; it does
not assert that the engine uses these conventions or consumes the notetrack.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

from read_skin_fixture import SIZES, parse, verify_payloads
from skin_oracle import (decode_global_bind, decode_one_two_blend, linear_blend,
                         original_fixture, rigid_matrix)

# Fixed sibling reader, never a caller-selected module or a writer's decoder.
sys.path.insert(0, str(Path(__file__).absolute().parent.parent))
from read_probe import read_probe
sys.path.pop(0)

COUNTS = [4, 4, 0, 0, 0, 0, 0, 0]
CLIP_HASHES = {
    "native": "1284b72cf501ae42f77958579610dbcaf692b9153cd06ff66dcf2d1d11eeda7d",
    "ff": "a357ae4d2269e14be43f2e4222bc2d8b00712d371f2cab7d21133a823729c221",
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def closed_form(degrees):
    """Ideal geometry/weights, independent of packed tracks and matrix helpers."""
    cosine, sine = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    result = []
    for z, weight in ((0., 0.), (16., 1.), (4., .25), (12., .75)):
        for y in (-4., 4.):
            rotated_y = cosine * y - sine * (z - 8.)
            rotated_z = 8. + sine * y + cosine * (z - 8.)
            result.append([0., (1. - weight) * y + weight * rotated_y,
                           (1. - weight) * z + weight * rotated_z])
    return result


def verify(files, manifest, xab, *, ff_roundtrip=False):
    input_report = verify_payloads(files, manifest)
    clip = read_probe(xab, 1.0, ff_roundtrip=ff_roundtrip)
    # The exact-profile XAB reader checks both channel names/order itself.
    geometry = parse(files["geometry.source.json"])
    require([(b["name"], b["parent"]) for b in geometry["bones"]] ==
            [("tag_origin", None), ("tag_probe", 0)], "exact clip-to-rig topology")
    binds, bind_error = decode_global_bind(
        files["parents.u8.bin"], files["tag-angles.i16.bin"],
        files["tag-positions.f32.bin"], files["base-mats.f32.bin"])
    vertices, _, _ = original_fixture()
    root = rigid_matrix((0., 0., 0., 1.), (0., 0., 0.))
    profiles = {}
    for hypothesis in ("first", "second"):
        weights = decode_one_two_blend(files[hypothesis + ".blend.u16.bin"], COUNTS, 2, hypothesis)
        opposite = decode_one_two_blend(files[hypothesis + ".blend.u16.bin"], COUNTS, 2,
                                        "second" if hypothesis == "first" else "first")
        samples = []
        for sample, ideal_degrees in zip(clip["samples"], (0., 45., -45., 0.)):
            child = rigid_matrix(sample["quat_xyzw_div32767"], (0., 0., 8.))
            posed = linear_blend(vertices, weights, binds, [root, child])
            expected = closed_form(ideal_degrees)
            error = max(math.dist(a, b) for a, b in zip(posed, expected))
            require(error < .005, "four-key pose differs from independent analytical bend")
            require(posed[:2] == vertices[:2], "root-weighted vertices moved")
            if ideal_degrees == 0.:
                require(error < 1e-10, "neutral key is not the bind pose")
            wrong = linear_blend(vertices, opposite, binds, [root, child])
            wrong_error = max(math.dist(a, b) for a, b in zip(wrong, expected))
            if ideal_degrees != 0.:
                require(wrong_error > 2., "asymmetric weight profiles are not distinguishable")
            samples.append({"frame": sample["frame"], "target_degrees": ideal_degrees,
                            "decoded_degrees": sample["x_degrees"], "positions": posed,
                            "max_error_units": error, "opposite_hypothesis_error_units": wrong_error})
        profiles[hypothesis] = {"model": manifest["profiles"][hypothesis]["name"],
                                "stored_weight_direction": hypothesis + "_bone_hypothesis_only",
                                "samples": samples}
    return {"schema": "iw7.original-probe-rig-cpu/1", "status": "four-key-rig-cpu-pass",
            "clip_sha256": clip["sha256"], "clip_readback_scope": clip["readback_scope"],
            "clip_matches_retained_evidence_hash": clip["sha256"] == CLIP_HASHES["ff" if ff_roundtrip else "native"],
            "channel_to_bone": [0, 1], "parent_distances": [1], "bind_matrix_error": bind_error,
            "geometry_input_verified": input_report["geometry_bytes_verified"], "profiles": profiles,
            "notetrack_data": clip["notetrack"], "root_motion_authored": False,
            "quaternion_normalization": "CPU assumption, not measured engine behavior",
            "native_model_read": False, "ff_model_verified": False, "runtime_animation_verified": False,
            "engine_weight_direction_verified": False, "note_delivery_verified": False,
            "loop_duration_verified": False, "ready": False}


def read_bounded(path, limit):
    require(path.is_absolute(), "absolute input required")
    for current in (path, *path.parents):
        require(not current.is_symlink() and not current.is_junction(), "linked input ancestry refused")
    require(path.is_file() and 0 < path.stat().st_size <= limit, "bounded regular input required")
    with path.open("rb") as stream:
        payload = stream.read(limit + 1)
    require(0 < len(payload) <= limit, "input grew past byte limit")
    return payload


def inspect(inputs, xab, *, ff_roundtrip=False):
    require(inputs.is_absolute() and inputs.is_dir(), "absolute input directory required")
    require({p.name for p in inputs.iterdir()} == set(SIZES) | {"fixture-input.json"},
            "exact source bundle inventory")
    files = {name: read_bounded(inputs / name, 16384) for name in SIZES}
    manifest = parse(read_bounded(inputs / "fixture-input.json", 16384))
    clip = read_bounded(xab, 65536)
    profile = "ff" if ff_roundtrip else "native"
    require(hashlib.sha256(clip).hexdigest() == CLIP_HASHES[profile],
            "CLI requires the actual retained clip hash for the selected profile")
    return verify(files, manifest, clip, ff_roundtrip=ff_roundtrip)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--xab", type=Path, required=True)
    parser.add_argument("--ff-roundtrip", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.inputs, args.xab, ff_roundtrip=args.ff_roundtrip),
                         indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError, struct.error, KeyError, TypeError) as error:
        print(json.dumps({"status": "invalid-rig-binding", "error": str(error)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())

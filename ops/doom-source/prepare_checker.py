"""Original procedural UV witness and two-bone source; no tool/game execution."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import struct

MATERIAL_SHA = "687924c80afb088a285c5df4704475b0786310738687fc555db77a3974c7c8b6"
TECHNIQUE = "mopw_l_sm_replace_i0c0s0o0n0p0"
NORMAL = "park_clown_zombie_shoes_n_3e46d100_packed_nog"
COLOR = "park_clown_zombie_shoes_pink_c_park_clown_zombie_shoes_g_packed_cs"
IMAGE = "paris_doom_checker_color_a"
MATERIAL = "paris_doom_checker_material_a"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pixel(x, y, size):
    """RGBA, x right/y down in TGA top-origin storage; deliberately asymmetric."""
    q = size // 4
    if x < q and y < q:
        return (255, 40, 40, 255)
    if x >= size - q and y < q:
        return (40, 255, 40, 255)
    if x < q and y >= size - q:
        return (40, 40, 255, 255)
    if x >= size - q and y >= size - q:
        return (255, 220, 40, 255)
    if y < size // 16:
        return (255, 255, 255, 255)
    if x < size // 16:
        return (255, 0, 255, 255)
    gray = 224 if (x // (size // 8) + y // (size // 8)) % 2 == 0 else 32
    return (gray, gray, gray, 255)


def tga(size=256):
    require(type(size) is int and 32 <= size <= 512 and size % 16 == 0, "bounded aligned checker size")
    # Type 2 uncompressed true-color, BGRA, top-origin plus 8 alpha bits.
    header = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, size, size, 32, 0x28)
    body = bytearray()
    for y in range(size):
        for x in range(size):
            r, g, b, a = pixel(x, y, size)
            body.extend((b, g, r, a))
    return header + body


def material(payload):
    require(len(payload) <= 16384 and hashlib.sha256(payload).hexdigest() == MATERIAL_SHA, "exact small measured material template")
    original = json.loads(payload)
    require(original.get("techniqueSet->name") == TECHNIQUE, "measured technique")
    rows = original.get("textureTable")
    require(isinstance(rows, list) and len(rows) == 2, "exact two texture semantics")
    require([(r.get("semantic"), r.get("image")) for r in rows] == [(15, NORMAL), (14, COLOR)], "measured normal/color bindings")
    result = copy.deepcopy(original)
    result["textureTable"][1]["image"] = IMAGE
    return result


def ribbon():
    """Z-up strip, four full-weight endpoints before two half-weight middle verts."""
    positions = [(0, -0.1, 0), (0, 0.1, 0), (0, -0.1, 0.4), (0, 0.1, 0.4), (0, -0.1, 0.2), (0, 0.1, 0.2)]
    weights = [[(0, 1.0)], [(0, 1.0)], [(1, 1.0)], [(1, 1.0)], [(0, 0.5), (1, 0.5)], [(0, 0.5), (1, 0.5)]]
    vertices = [{"position_m": list(p), "normal": [-1, 0, 0], "uv": [(p[1] + 0.1) / 0.2, p[2] / 0.4], "weights": [{"bone": b, "weight": w} for b, w in row]} for p, row in zip(positions, weights)]
    # Opposite face normal/winding would be a failure, not an automatic reversal.
    indices = [0, 4, 1, 1, 4, 5, 4, 2, 5, 5, 2, 3]
    return {"schema": "iw7.original-skin-source/1", "authorship": "procedural original diagnostic geometry", "ready": False,
            "model": "paris_doom_skin_two_bone_a", "coordinate_system": "Z_UP_metres", "height_engine_units": 16,
            "bones": [{"name": "tag_origin", "parent": None, "bind_translation_m": [0, 0, 0], "bind_quaternion_xyzw": [0, 0, 0, 1]},
                      {"name": "tag_probe", "parent": 0, "bind_translation_m": [0, 0, 0.2], "bind_quaternion_xyzw": [0, 0, 0, 1]}],
            "vertices": vertices, "triangle_indices": indices,
            "pose_samples": [{"name": "bind", "child_rotation_degrees_about_X": 0}, {"name": "bend", "child_rotation_degrees_about_X": 45}],
            "runtime_animation_request": "unimplemented; no XAnim or tag-control proof", "weight_quantization": "candidate only; reader/runtime verification required"}


def reference_skin(source, degrees):
    """Independent CPU oracle in metres, row-vector free child T*R*T^-1."""
    require(type(degrees) in (int, float) and math.isfinite(degrees), "finite pose")
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    out = []
    for vertex in source["vertices"]:
        x, y, z = vertex["position_m"]
        child = [x, c * y - s * (z - 0.2), s * y + c * (z - 0.2) + 0.2]
        value = [0., 0., 0.]
        for influence in vertex["weights"]:
            p = vertex["position_m"] if influence["bone"] == 0 else child
            for axis in range(3):
                value[axis] += influence["weight"] * p[axis]
        out.append(value)
    return out


def prepare(donor_root, output):
    donor_root, output = donor_root.resolve(), output.absolute()
    require(not output.exists(), "fresh checker root")
    for parent in (output, *output.parents):
        require(not parent.is_symlink() and not parent.is_junction(), "linked output refused")
    path = donor_root / "materials/mopw/character_park_clown_zombie_shoes.json"
    payload = path.read_bytes()
    transformed = material(payload)
    files = {f"images/{IMAGE}.tga": tga(), f"materials/{MATERIAL}.json": (json.dumps(transformed, indent=2) + "\n").encode()}
    sidecar_hashes = {}
    for branch, suffixes in [("state", ["stateinfo", "statebits", "statebitsmap"]), ("constantbuffer", ["cbi", "cbt"])]:
        for suffix in suffixes:
            relative = f"techsets/{branch}/{TECHNIQUE}/mopw/character_park_clown_zombie_shoes.{suffix}"
            source = donor_root / relative
            require(source.stat().st_size <= 65536, "bounded measured material sidecar")
            value = source.read_bytes()
            files[f"techsets/{branch}/{TECHNIQUE}/{MATERIAL}.{suffix}"] = value
            sidecar_hashes[relative] = hashlib.sha256(value).hexdigest()
    skin = ribbon()
    files["two-bone-source.json"] = (json.dumps(skin, indent=2) + "\n").encode()
    oracle = {"schema": "iw7.original-skin-oracle/1", "bind_m": reference_skin(skin, 0), "bend45_m": reference_skin(skin, 45), "writer_built": False, "ff_built": False, "pixels_verified": False, "ready": False}
    files["two-bone-cpu-oracle.json"] = (json.dumps(oracle, indent=2) + "\n").encode()
    plan = {"schema": "iw7.original-checker-stage/1", "source_material_sha256": MATERIAL_SHA, "donor_sidecar_sha256": sidecar_hashes,
            "custom_material": MATERIAL, "custom_image": IMAGE, "image": {"width": 256, "height": 256, "storage": "TGA BGRA8 top-origin", "alpha": "255", "mips": 1,
            "top_left_rgba": pixel(0, 0, 256), "top_right_rgba": pixel(255, 0, 256), "bottom_left_rgba": pixel(0, 255, 256), "bottom_right_rgba": pixel(255, 255, 256)},
            "retail_references_only": {"techniqueset": TECHNIQUE, "normal_image": NORMAL}, "retail_image_payload_copied": False,
            "material_change": "replace semantic14 color image only; preserve constants/state/sampler and semantic15 retail normal reference",
            "portable_image_path": "DirectXTex custom resident image -> streamed=0 -> FF pixelData; no PAK expected for this original resident checker",
            "portable_streamed_path": "reuse pinned Rhino portable stream descriptor/PAK validation for any later streamed images; do not fabricate stream pointers",
            "sidecars_review_required": True, "ff_builder_implemented": False, "image_roundtrip_verified": False, "runtime_uv_orientation_verified": False,
            "two_bone_writer_implemented": False, "runtime_skinning_verified": False, "ready": False,
            "files": {name: hashlib.sha256(value).hexdigest() for name, value in files.items()}}
    output.mkdir(parents=True, exist_ok=False)
    for name, value in files.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(value)
    with (output / "checker-stage.local.json").open("x", encoding="utf-8") as stream:
        json.dump(plan, stream, indent=2)
    return plan


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--donor-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.donor_root, args.output), indent=2))

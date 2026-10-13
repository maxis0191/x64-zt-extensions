"""Export an original two-bone input bundle, never XMB/XSB/FF or packed vertices."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess

PIN = "fab935826c898806855376662a8a03317b3ad8f1"
INTERFACES = ["iw7/structs.hpp", "iw7/assets/xsurface.cpp", "iw7/assets/xmodel.cpp",
              "h1/converter/iw7/assets/xsurface.cpp", "iw7/converter/h1/assets/xsurface.cpp",
              "t7/converter/iw7/assets/xmodel_mesh.cpp"]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def original_source():
    vertices = []
    # Mono group precedes dual group. Engine coordinates are explicit, no rescale.
    for z, child_weight in ((0., 0.), (16., 1.), (4., .25), (12., .75)):
        for y in (-4., 4.):
            weights = [(0, 1.)] if child_weight == 0 else [(1, 1.)] if child_weight == 1 else [(0, 1 - child_weight), (1, child_weight)]
            vertices.append({"xyz": [0., y, z], "normal": [-1., 0., 0.], "uv": [(y + 4) / 8, z / 16],
                             "weights": [{"bone": b, "weight": w} for b, w in weights]})
    return {"schema": "iw7.doom-original-two-bone-source/1", "origin": "original_procedural_geometry",
            "coordinate_system": "Z_UP_engine_units", "vertices": vertices,
            "triangles": [[0, 4, 1], [1, 4, 5], [4, 6, 5], [5, 6, 7], [6, 2, 7], [7, 2, 3]],
            "bones": [{"name": "tag_origin", "parent": None, "global_bind_xyz": [0., 0., 0.]},
                      {"name": "tag_probe", "parent": 0, "global_bind_xyz": [0., 0., 8.]}]}


def fixture_files():
    source = original_source()
    files = {"geometry.source.json": (json.dumps(source, indent=2) + "\n").encode()}
    for key, count, filename in (("xyz", 3, "positions.f32.bin"), ("normal", 3, "normals.f32.bin"), ("uv", 2, "uv.f32.bin")):
        values = [v for vertex in source["vertices"] for v in vertex[key]]
        files[filename] = struct.pack("<" + str(8 * count) + "f", *values)
    files["triangles.u16.bin"] = struct.pack("<18H", *[v for row in source["triangles"] for v in row])
    files["parents.u8.bin"] = b"\x01"
    files["tag-angles.i16.bin"] = struct.pack("<4h", 0, 0, 0, 32767)
    files["tag-positions.f32.bin"] = struct.pack("<3f", 0, 0, 8)
    files["base-mats.f32.bin"] = struct.pack("<16f", 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 1, 0, 0, 8, 2)
    for hypothesis in ("first", "second"):
        words = []
        for vertex in source["vertices"]:
            weights = vertex["weights"]
            if len(weights) == 1:
                words.extend((weights[0]["bone"], 0))
            else:
                index = 0 if hypothesis == "first" else 1
                words.extend((0, 1, int(math.floor(weights[index]["weight"] * 255 + .5)), 0))
        files[hypothesis + ".blend.u16.bin"] = struct.pack("<24H", *words)
    return files


def manifest(files, interface_hashes):
    return {"schema": "iw7.doom-two-bone-input/1", "source_pin": PIN, "interface_hashes": interface_hashes,
            "files": {name: {"bytes": len(payload), "sha256": sha(payload)} for name, payload in files.items()},
            "profiles": {h: {"name": "paris_doom_skin_two_bone_" + h + "_a", "stored_weight_bone_hypothesis": h,
                             "blend_file": h + ".blend.u16.bin"} for h in ("first", "second")},
            "counts": {"vertices": 8, "triangles": 6, "bones": 2, "roots": 1, "client_bones": 0,
                       "surfaces": 1, "rigid_lists": 0, "blend": [4, 4, 0, 0, 0, 0, 0, 0], "blend_bytes": 48},
            "native_surface_flags_proposed": 0x86, "native_model_has_rigid_list_proposed": False,
            "bounds": {"mid": [0., 0., 8.], "half": [0., 4., 8.], "radius": math.sqrt(272)},
            "part_bits_proposed": [0xC0000000] + [0] * 7, "part_bits_engine_verified": False,
            "packed_vertex_encoding_verified": False, "tangent_handedness_engine_verified": False,
            "native_writer_executed": False, "ff_built": False, "animation_verified": False,
            "pixels_verified": False, "ready": False}


def unlinked(path):
    require(path.is_absolute(), "absolute source/output")
    for current in (path, *path.parents):
        require(not current.is_symlink() and not current.is_junction(), "linked ancestry refused")
    return path


def prepare(source, output):
    source, output = unlinked(source), unlinked(output)
    require(source.is_dir() and not output.exists(), "existing source and fresh output")
    require(subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip() == PIN, "pinned tool source")
    require(not subprocess.check_output(["git", "-C", str(source), "status", "--porcelain", "--untracked-files=all"], text=True).strip(), "preserve changed tool source")
    refs = {}
    for name in INTERFACES:
        path = unlinked(source / "src/zonetool/zonetool" / name)
        require(path.is_file() and path.stat().st_size < 2 * 1024 * 1024, "bounded pinned interface")
        refs[name] = sha(path.read_bytes())
    files = fixture_files()
    result = manifest(files, refs)
    output.mkdir(parents=True, exist_ok=False)
    for name, payload in files.items():
        unlinked(output / name)
        with (output / name).open("xb") as stream:
            stream.write(payload)
    with (output / "fixture-input.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output), indent=2))

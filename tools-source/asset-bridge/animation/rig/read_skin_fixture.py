"""Independent original-input reader; does not import the exporter or writer."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct
from skin_oracle import original_fixture, verify_original_candidate

PIN = "fab935826c898806855376662a8a03317b3ad8f1"
SIZES = {"geometry.source.json": None, "positions.f32.bin": 96, "normals.f32.bin": 96, "uv.f32.bin": 64,
         "triangles.u16.bin": 36, "parents.u8.bin": 1, "tag-angles.i16.bin": 8,
         "tag-positions.f32.bin": 12, "base-mats.f32.bin": 64,
         "first.blend.u16.bin": 48, "second.blend.u16.bin": 48}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def parse(payload):
    require(isinstance(payload, bytes) and 0 < len(payload) <= 16384, "bounded JSON bytes")
    return json.loads(payload, object_pairs_hook=unique_object,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON number")))


def vector(value, expected):
    require(isinstance(value, list) and len(value) == len(expected) and all(type(x) in (int, float) and math.isfinite(x) for x in value) and value == expected, "exact finite original vector")


def verify_payloads(files, meta):
    require(isinstance(files, dict) and set(files) == set(SIZES), "exact original stream inventory")
    require(isinstance(meta, dict), "manifest object")
    require(meta.get("schema") == "iw7.doom-two-bone-input/1" and meta.get("source_pin") == PIN, "distinct source-input profile")
    expected_counts = {"vertices": 8, "triangles": 6, "bones": 2, "roots": 1, "client_bones": 0, "surfaces": 1,
                       "rigid_lists": 0, "blend": [4, 4, 0, 0, 0, 0, 0, 0], "blend_bytes": 48}
    counts = meta.get("counts")
    require(isinstance(counts, dict) and counts == expected_counts and all(type(counts[k]) is int for k in counts if k != "blend") and all(type(v) is int for v in counts["blend"]), "exact typed skin counts")
    require(type(meta.get("native_surface_flags_proposed")) is int and meta["native_surface_flags_proposed"] == 0x86 and meta.get("native_model_has_rigid_list_proposed") is False, "skinned flags without rigid-list model flag")
    for key in ("part_bits_engine_verified", "packed_vertex_encoding_verified", "tangent_handedness_engine_verified",
                "native_writer_executed", "ff_built", "animation_verified", "pixels_verified", "ready"):
        require(meta.get(key) is False, "source-only proof boundary " + key)
    require(meta.get("part_bits_proposed") == [0xC0000000] + [0] * 7 and all(type(v) is int for v in meta["part_bits_proposed"]), "proposed two-bone part bits")
    bounds = meta.get("bounds")
    require(isinstance(bounds, dict) and set(bounds) == {"mid", "half", "radius"} and type(bounds["radius"]) in (int, float) and bounds["radius"] == math.sqrt(272), "original bounds")
    vector(bounds["mid"], [0., 0., 8.])
    vector(bounds["half"], [0., 4., 8.])
    refs = meta.get("interface_hashes")
    expected_refs = {"iw7/structs.hpp", "iw7/assets/xsurface.cpp", "iw7/assets/xmodel.cpp",
                     "h1/converter/iw7/assets/xsurface.cpp", "iw7/converter/h1/assets/xsurface.cpp", "t7/converter/iw7/assets/xmodel_mesh.cpp"}
    require(isinstance(refs, dict) and set(refs) == expected_refs and all(isinstance(v, str) and re.fullmatch("[0-9a-f]{64}", v) for v in refs.values()), "interface receipt inventory")
    hashes = meta.get("files")
    require(isinstance(hashes, dict) and set(hashes) == set(SIZES), "manifest stream inventory")
    for name, payload in files.items():
        require(isinstance(payload, bytes) and 0 < len(payload) <= 8192 and (SIZES[name] is None or len(payload) == SIZES[name]), "bounded exact stream size " + name)
        require(isinstance(hashes[name], dict) and type(hashes[name].get("bytes")) is int and
                hashes[name] == {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}, "physical stream receipt " + name)
    expected_vertices, expected_weights, _ = original_fixture()
    positions = [list(row) for row in struct.iter_unpack("<3f", files["positions.f32.bin"])]
    require(positions == expected_vertices, "actual positions vs analytical original fixture")
    normals = [list(row) for row in struct.iter_unpack("<3f", files["normals.f32.bin"])]
    require(normals == [[-1., 0., 0.]] * 8, "original plane normal")
    uvs = [list(row) for row in struct.iter_unpack("<2f", files["uv.f32.bin"])]
    expected_uv = [[(v[1] + 4) / 8, v[2] / 16] for v in expected_vertices]
    require(uvs == expected_uv, "asymmetric original UVs")
    triangles = list(struct.iter_unpack("<3H", files["triangles.u16.bin"]))
    require(triangles == [(0, 4, 1), (1, 4, 5), (4, 6, 5), (5, 6, 7), (6, 2, 7), (7, 2, 3)], "original triangle indexing")
    source = parse(files["geometry.source.json"])
    require(isinstance(source, dict), "source object")
    require(source.get("schema") == "iw7.doom-original-two-bone-source/1" and source.get("origin") == "original_procedural_geometry" and source.get("coordinate_system") == "Z_UP_engine_units", "original source contract")
    rows = source.get("vertices")
    require(isinstance(rows, list) and len(rows) == 8, "eight source vertices")
    for i, row in enumerate(rows):
        require(isinstance(row, dict), "vertex object")
        vector(row["xyz"], expected_vertices[i])
        vector(row["normal"], normals[i])
        vector(row["uv"], expected_uv[i])
        weights = row.get("weights")
        require(isinstance(weights, list) and len(weights) == len(expected_weights[i]), "original influence count")
        require(all(type(w["bone"]) is int and type(w["weight"]) in (int, float) and math.isfinite(w["weight"]) for w in weights) and
                [(w["bone"], w["weight"]) for w in weights] == list(expected_weights[i].items()), "ideal source weights independent of wire")
    require(source.get("triangles") == [list(row) for row in triangles] and all(type(v) is int for row in source["triangles"] for v in row), "source triangle correspondence")
    bones = source.get("bones")
    require(isinstance(bones, list) and len(bones) == 2 and bones[0].get("name") == "tag_origin" and bones[0].get("parent") is None and
            bones[1].get("name") == "tag_probe" and type(bones[1].get("parent")) is int and bones[1]["parent"] == 0, "original bone names and hierarchy")
    vector(bones[0]["global_bind_xyz"], [0., 0., 0.])
    vector(bones[1]["global_bind_xyz"], [0., 0., 8.])
    profiles = meta.get("profiles")
    require(isinstance(profiles, dict) and set(profiles) == {"first", "second"}, "two explicit hypotheses")
    reports = {}
    for hypothesis in ("first", "second"):
        expected = {"name": "paris_doom_skin_two_bone_" + hypothesis + "_a", "stored_weight_bone_hypothesis": hypothesis, "blend_file": hypothesis + ".blend.u16.bin"}
        require(profiles[hypothesis] == expected, "distinct hypothesis profile identity")
        reports[hypothesis] = verify_original_candidate(files["parents.u8.bin"], files["tag-angles.i16.bin"], files["tag-positions.f32.bin"],
                                                       files["base-mats.f32.bin"], files[hypothesis + ".blend.u16.bin"], counts["blend"], hypothesis)
    require(files["first.blend.u16.bin"] != files["second.blend.u16.bin"], "asymmetric hypotheses must differ")
    return {"schema": "iw7.doom-two-bone-input-read/1", "profiles": reports, "geometry_bytes_verified": True,
            "interface_bytes_reverified": False, "input_only": True, "native_asset_read": False,
            "native_writer_executed": False, "ff_built": False, "pixels_verified": False, "ready": False}


def read(root):
    require(root.is_absolute() and root.is_dir(), "absolute prepared input directory")
    for path in (root, *root.parents):
        require(not path.is_symlink() and not path.is_junction(), "linked root ancestry")
    entries = list(root.iterdir())
    require({p.name for p in entries} == set(SIZES) | {"fixture-input.json"}, "exact physical inventory")
    for path in entries:
        require(path.is_file() and not path.is_symlink() and not path.is_junction() and path.stat().st_size <= 16384, "bounded regular input")
    files = {name: (root / name).read_bytes() for name in SIZES}
    return verify_payloads(files, parse((root / "fixture-input.json").read_bytes()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(read(args.input), indent=2))

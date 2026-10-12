"""Prepare the distinct original-color beacon source; never build, pack or launch.

Only exact retained tiny inputs are accepted. The emitted FF inputs intentionally
lack XMB/XSB until a separately admitted native writer and independent reread run.
"""
import argparse
import hashlib
import json
from pathlib import Path

from inspect_content import Inputs, Inspector, no_links, parse_json, require
from prepare_beacon import NORMAL, TECHNIQUE, TEMPLATE, tga


MODEL = "community_beacon_model_v2"
MATERIAL = "community_beacon_material_v2"
IMAGE = "community_beacon_color_v2"
ZONE = "sdk_beacon_material_v2"
NCS = "ncs_mdl_" + MODEL
PIN = "fab935826c898806855376662a8a03317b3ad8f1"
OLD_MODEL = "paris_model_probe"
OLD_MATERIAL = "mopw/character_park_clown_zombie_shoes"
WRITER_INPUTS = {
    "writer.cpp": "3494bbacda6964c5b6966673698851ffe083341f2dabed3cd48de99559021b38",
    "probe_geometry.hpp": "ee88389a86effcef215e9fe8e0a4278d811b41fb00190181d65a524dda4d5e25",
    "geometry.source.json": "3ad4ef633136ee7d2a956eb9bc3412b10f1235953b07fb13d5e951fc69e18e52",
    "writer-source.json": "355a3f629eca5f3a30e45b9b91a788b7395df5652542eb501e9a5d0c8d07bcee",
}
BUILDER_RECEIPT = "f0d4d7db132d51c789a999e33ab0ce905b2df749db453029f91356b9aa2e2165"
BUILDER_EXE = "e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04"
STRICT_PATCH = "4d7049216f24474e077ab704dac625c7f335c8264434b7de525e56a96a988d08"
LIMIT = 128 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(data):
    return (json.dumps(data, indent=2) + "\n").encode()


def checked_inputs(root, expected):
    inputs = Inputs(root)
    result = {}
    for path, sha in expected.items():
        data = inputs.read(path, 65536)
        require(digest(data) == sha, "pinned input changed: " + path)
        result[path] = data
    return result


def rewrite_writer(writer, header):
    # Exact input hashes are checked before calling. Preserve bytes, line endings,
    # packed vertices, LOD settings and all actual assetmanager reader assertions.
    require(writer.count(OLD_MODEL.encode()) == 8, "eight model-name anchors required")
    writer = writer.replace(OLD_MODEL.encode(), MODEL.encode())
    old = b'\\"schema\\":\\"iw7.model-roundtrip/1\\",'
    new = (b'\\"schema\\":\\"iw7.content-material-roundtrip/1\\",'
           + b'\\"model\\":\\"' + MODEL.encode() + b'\\",')
    require(writer.count(old) == 1, "one original roundtrip schema anchor required")
    writer = writer.replace(old, new)
    old = ('inline constexpr const char* probe_material_name = "' + OLD_MATERIAL + '";').encode()
    new = ('inline constexpr const char* probe_material_name = "' + MATERIAL + '";').encode()
    require(header.count(old) == 1 and header.startswith(old), "exact material header anchor required")
    header = header.replace(old, new)
    require(OLD_MODEL.encode() not in writer and OLD_MATERIAL.encode() not in header,
            "old model/material binding survived")
    return writer, header


def builder_metadata(receipt_path):
    path = no_links(Path(receipt_path).absolute())
    source = Inputs(path.parent)
    raw = source.read(path.name, 16384)
    require(digest(raw) == BUILDER_RECEIPT, "reviewed full-tool receipt required")
    receipt = parse_json(raw)
    require(receipt["schema"] == "iw7.zonetool-community-candidate/1"
            and receipt["source_pin"] == PIN and receipt["macro_compiled"] is True
            and receipt["compile_units_verified"] == 413 and receipt["fresh_candidate_pch"] is True
            and receipt["executable"]["sha256"] == BUILDER_EXE
            and receipt["patch_sha256"]["strict-content-sources.patch"] == STRICT_PATCH,
            "full-tool contract mismatch")
    # No machine paths, PDB, executable or build-log copies. Metadata alone is
    # not fresh executable verification; the future runner must hash it itself.
    return {"receipt_sha256": BUILDER_RECEIPT, "executable_sha256": BUILDER_EXE,
            "executable_bytes": receipt["executable"]["bytes"], "strict_patch_sha256": STRICT_PATCH,
            "executable_verified_here": False, "reuse_existing_tool": True}


def expected_inventory():
    return [
        {"type": "techset", "name": "," + TECHNIQUE, "recipient_reference": True},
        {"type": "image", "name": "," + NORMAL, "recipient_reference": True},
        {"type": "image", "name": IMAGE}, {"type": "material", "name": MATERIAL},
        {"type": "xmodelsurfs", "name": MODEL + "_lod0"}, {"type": "xmodel", "name": MODEL},
        {"type": "netconststrings", "name": NCS}, {"type": "rawfile", "name": ZONE},
    ]


def payloads(writer_root, checker_root, receipt_path):
    original = checked_inputs(writer_root, WRITER_INPUTS)
    writer, header = rewrite_writer(original["writer.cpp"], original["probe_geometry.hpp"])
    contract = parse_json(Path(__file__).with_name("source_contract.json").read_bytes())
    inputs = checked_inputs(checker_root, contract["beacon_fixture_inputs"])
    material = parse_json(inputs[f"materials/{TEMPLATE}.json"])
    require(material["techniqueSet->name"] == TECHNIQUE and
            [(r["semantic"], r["image"]) for r in material["textureTable"]] ==
            [(15, NORMAL), (14, "paris_doom_checker_color_a")], "measured texture bindings changed")
    material["textureTable"][1]["image"] = IMAGE
    result = {"writer-source/writer.cpp": writer, "writer-source/probe_geometry.hpp": header,
              "writer-source/geometry.baseline.json": original["geometry.source.json"],
              f"ff-inputs/images/{IMAGE}.tga": tga(),
              f"ff-inputs/materials/{MATERIAL}.json": encoded(material)}
    for path, data in inputs.items():
        if path.startswith("techsets/"):
            result["ff-inputs/" + path.replace(TEMPLATE, MATERIAL)] = data
    result[f"ff-inputs/zone_source/{ZONE}_recipient.csv"] = f"techset,{TECHNIQUE}\nimage,{NORMAL}\n".encode()
    result[f"ff-inputs/zone_source/{ZONE}.csv"] = (
        f"ignore,{ZONE}_recipient\nimage,{IMAGE}\nmaterial,{MATERIAL}\n"
        f"xmodel,{MODEL}\nnetconststrings,{NCS}\n").encode()
    result[f"ff-inputs/netconststrings/{NCS}.json"] = encoded(
        {"stringType": 0, "sourceType": 2, "stringList": [MODEL]})
    plan = {
        "schema": "iw7.content-material-source/1", "source_pin": PIN,
        "zone": ZONE, "model": MODEL, "material": MATERIAL, "image": IMAGE, "recipient": "cp_zmb",
        "builder": builder_metadata(receipt_path),
        "template_inputs": contract["beacon_fixture_inputs"], "writer_inputs": WRITER_INPUTS,
        "writer_interface_hashes": parse_json(original["writer-source.json"])["source_hashes"],
        "identity_changes": {"model_from": OLD_MODEL, "model_to": MODEL,
                             "material_from": OLD_MATERIAL, "material_to": MATERIAL},
        "geometry_source": "original cube retained byte-for-byte as geometry.baseline.json; header binding changed only",
        "geometry": {"vertices": 24, "triangles": 12, "bones": 1, "surfaces": 1, "lods": 1,
                     "lod0_dist": 1000000, "has_lods": True, "shadow_cutoff_lod": 6, "collision_lod": 255},
        "required_writer_report": {"schema": "iw7.content-material-roundtrip/1", "model": MODEL,
                                   "material_reference": MATERIAL, "geometry_roundtrip_verified": True},
        "required_artifacts": [f"xmodel/{MODEL}.xmb", f"xsurface/{MODEL}_lod0.xsb"],
        "expected_inventory": expected_inventory(),
        "engine_build_args": ["-headless", "-unbuffered-io", "-strict-content-sources", "-buildzone", ZONE],
        "independent_reread_args": ["--verify-existing", "<fresh-owned-FF-dump>"],
        "new_pixels": "original 32x32 opaque BGRA8 asymmetric color witness, resident FF without PAK",
        "recipient_references_verified": False, "normal_encoding_runtime_verified": False,
        "limits": {"source_bytes": LIMIT, "ff_bytes": 1048576, "per_model_artifact_bytes": 8192},
        "next_run_admission": {"writer_ram_gib": 2, "writer_commit_gib": 3,
                               "ff_ram_gib": 8, "ff_commit_gib": 11,
                               "full_quality_client_plus_dedicated_ram_commit_gib": [14, 16],
                               "sequential_shared_lease": True},
        "pending": [
            "Native writer compile under verified source hashes; record exact compiler/source/executable hashes.",
            "Execute writer in fresh owned directory; reread real model/material binding and all geometry.",
            "Stage only measured bounded XMB/XSB with native report and hashes; reject variant1 identities.",
            "Reuse and freshly verify E7C956 full builder; build/verify/dump in bounded SDK job with strict flag.",
            "Independently reread FF dump using this variant's exact built writer; enforce eight-entry inventory.",
            "Reread image/material dump: actual32x32 decoded pixels, semantic14 color, semantic15 normal, state/constants.",
            "Add scoped native diagnostic fs_game/model route; current paris_model_probe gate excludes SDK paths.",
            "Fresh private launch telemetry, engine godmode/inactivity protection, then full-quality visual proof.",
        ],
        "source_files": {path: {"sha256": digest(data), "bytes": len(data)} for path, data in result.items()},
        "payload_bytes": sum(map(len, result.values())),
        "native_writer_compiled": False, "model_supplied": False, "ff_built": False,
        "pixels_verified": False, "ready": False,
    }
    result["material-v2-plan.json"] = encoded(plan)
    require(sum(map(len, result.values())) <= LIMIT, "source output budget exceeded")
    return result, plan


def prepare(writer_root, checker_root, receipt_path, output):
    output = no_links(Path(output).absolute())
    require(not output.exists(), "fresh material-v2 output required")
    for source in (Path(writer_root).absolute(), Path(checker_root).absolute(), Path(receipt_path).absolute().parent):
        require(not output.is_relative_to(source) and not source.is_relative_to(output),
                "source and output must be separate")
    files, plan = payloads(writer_root, checker_root, receipt_path)
    output.mkdir(parents=True, exist_ok=False)
    for path, data in files.items():
        target = output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
    check = Inspector(output / "ff-inputs", ZONE, [("techset", TECHNIQUE), ("image", NORMAL)],
                      strict_reader_prepared=True)
    check.material(MATERIAL)
    report = check.report()
    require(report["errors"] == 0, "generated material preflight failed: " + json.dumps(report["findings"]))
    # No native source execution/CBT decode/recipient resolution is inferred.
    return {"plan": plan, "static_preflight": report,
            "total_bytes": sum(map(len, files.values())), "total_files": len(files)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--writer-root", required=True, type=Path)
    parser.add_argument("--checker-root", required=True, type=Path)
    parser.add_argument("--builder-receipt", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.writer_root, args.checker_root, args.builder_receipt, args.output), indent=2))

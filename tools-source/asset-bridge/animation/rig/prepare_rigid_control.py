"""Prepare the fixed original ribbon's rigid-control source; no native/FF/game run."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[4]
PIN = "fab935826c898806855376662a8a03317b3ad8f1"
ZONE = "sdk_original_rig_rigid_control"
MATERIAL = "mopw/character_park_clown_zombie_shoes"
NAMES = {p: "paris_doom_skin_two_bone_" + p + "_a" for p in ("first", "second")}
PINS = {
    "ops/doom-source/writer_rigid.cpp": "2c55580fef066be023fa687d7276d714b08e2783c3cbcc283d56c48d720b127f",
    "ops/doom-source/half_uv.hpp": "f532d525a81e0073c9c8ca6beeb9781734f56990f1db59cbd87b55efba2ae3d9",
    "tools-source/asset-bridge/animation/rig/prepare_skin_fixture.py": "b65564a3ecf3edc25b359f2cd420926c247f887375d6081b2c7f71f596a50353",
}
ADDONS = {
    "A": {"source": "sdk_original_rig_stock_witness.gsc", "sha256": "649b7497af5e2f11c7ca5a959f5e0cabfa0e42fc4939675578ffc8bfe3275a7e"},
    "B": {"source": "sdk_original_rig_stock_witness_scale_after.gsc", "sha256": "40e8990cb27f49244499c57ae9f19b635f0515c5c35442919af0b90c8a377ed0"},
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def source_inputs():
    result = {}
    for name, expected in PINS.items():
        path = ROOT / name
        require(not path.is_symlink(), "Linked producer source refused")
        payload = path.read_bytes()
        require(len(payload) < 65536 and digest(payload) == expected, "Pinned source differs: " + name)
        result[name] = payload
    return result


def original_geometry(payload=None):
    name = "tools-source/asset-bridge/animation/rig/prepare_skin_fixture.py"
    if payload is None:
        payload = (ROOT / name).read_bytes()
    require(digest(payload) == PINS[name], "Pinned original geometry source required")
    namespace = {"__name__": "rigid_control_original_source", "__file__": str(ROOT / name)}
    exec(compile(payload, str(ROOT / name), "exec"), namespace)
    return namespace["original_source"]()


def replace_once(text, before, after):
    require(text.count(before) == 1, "Unique rigid-writer anchor required: " + before[:64])
    return text.replace(before, after, 1)


def writer_source(payload):
    require(digest(payload) == PINS["ops/doom-source/writer_rigid.cpp"], "Pinned rigid writer required")
    text = payload.decode("utf-8")
    text = replace_once(text, "// Rigid Doom prop source candidate. Derived from the measured cube adapter,",
                        "// Original ribbon rigid control, derived from the pinned rigid prop writer,")
    text = replace_once(text, "// IEEE half 0/1 are exact for this fixed UV set. No general mesh import is claimed.",
                        "// Original 0/.25/.75/1 UVs are exact IEEE halves. No general mesh import is claimed.")
    text = replace_once(text, "// One-variable candidate: the loaded invisible baseline has dist=0 while\n    // its buffers/material exist. Keep hasLods and every other model field.",
                        "// Preserve the original ribbon's single-LOD distance and hasLods field.")
    # Preserve the original skin fixture's negative tangent handedness bits.
    text = replace_once(text, "v.tangent.packed=pack_unit_candidate(input.tangent);",
                        "v.tangent.packed=pack_unit_candidate(input.tangent) & 0x3FFFFFFFu;")
    text = replace_once(text, "info.radiusSquared=probe_radius*probe_radius;", "info.radiusSquared=272.0f;")
    text = replace_once(text, 'require(s.vertCount==probe_vertex_count',
                        'for(const auto count:s.blendVertCounts)require(count==0,"Rigid blend counts must be zero");\n    require(s.blendVertSize==0,"Rigid blend byte size must be zero");\n    require(s.vertCount==probe_vertex_count')
    anchor = "model.lodInfo[0].numsurfs=1;"
    text = replace_once(text, anchor, "model.unknownIndex=255;model.unknownIndex2=255;\n    " + anchor)
    text = replace_once(text, "iw7.doom-rigid-roundtrip/1", "iw7.original-rig-rigid-control-roundtrip/1")
    require(text.count("engine_units_per_metre") == 2, "Rigid unit-label anchors differ")
    text = text.replace("engine_units_per_metre", "source_units_to_engine")
    text = replace_once(text, 'require(rm->radius==model.radius',
                        'require(rm->flags==XMODEL_FLAG_HAS_RIGID_VERT_LIST && rm->unknownIndex==255 && rm->unknownIndex2==255,"Rigid flag or retained raw sentinels differ");\n    require(rm->radius==model.radius')
    text = replace_once(text, 'require(!memcmp(rs->surfs[0].rigidVertLists,&rigid,sizeof(rigid))',
                        'require(!memcmp(rs->surfs[0].partBits,surf.partBits,sizeof(surf.partBits)),"Surface part bits differ");\n    require(!memcmp(rs->surfs[0].rigidVertLists,&rigid,sizeof(rigid))')
    return text.encode("utf-8")


def float_literal(value):
    value = struct.unpack("<f", struct.pack("<f", value))[0]
    text = format(value, ".9g")
    if "." not in text and "e" not in text:
        text += ".0"
    return text + "f"


def geometry_header(data, profile):
    require(profile in NAMES, "Exactly first or second profile")
    require(digest((json.dumps(data, indent=2) + "\n").encode()) ==
            "18aed61ac8b4017f677dca5f56c92b5f3e0cc2ffa717766a0e04eeb39004c00a", "Exact original geometry reference required")
    vertices, triangles = data["vertices"], data["triangles"]
    require(len(vertices) == 8 and len(triangles) == 6, "Fixed original ribbon counts")
    name = NAMES[profile]
    lines = ["#pragma once", "#include <cstddef>",
             'inline constexpr const char* probe_model_name="' + name + '";',
             'inline constexpr const char* probe_surfs_name="' + name + '_lod0";',
             'inline constexpr const char* probe_material_name="' + MATERIAL + '";',
             "inline constexpr unsigned probe_vertex_count=8, probe_triangle_count=6;",
             "inline constexpr float probe_source_units_to_engine=1.0f, probe_radius=" + float_literal(math.sqrt(272)) + ";",
             "inline constexpr float probe_bounds_mid[3]={0.0f,0.0f,8.0f}, probe_bounds_half[3]={0.0f,4.0f,8.0f};",
             "struct ProbeVertex { float xyz[3], normal[3], uv[2], tangent[3]; };",
             "inline constexpr ProbeVertex probe_vertices[probe_vertex_count]={"]
    for i, vertex in enumerate(vertices):
        values = vertex["xyz"] + vertex["normal"] + vertex["uv"] + [0., 1., 0.]
        require(all(type(x) in (int, float) and math.isfinite(x) for x in values), "Finite original vertex")
        lines.append("    {" + ", ".join(float_literal(x) for x in values) + "}" + ("," if i < 7 else ""))
    lines += ["};", "inline constexpr unsigned short probe_triangles[probe_triangle_count][3]={"]
    for i, row in enumerate(triangles):
        require(len(row) == 3 and all(type(x) is int and 0 <= x < 8 for x in row), "Original triangle range")
        lines.append("    {" + ", ".join(map(str, row)) + "}" + ("," if i < 5 else ""))
    return ("\n".join(lines + ["};", ""])).encode()


def prepare(output, addon_case):
    output = Path(output)
    require(output.is_absolute(), "Absolute fresh source output required")
    for path in (output, *output.parents):
        require(not path.is_symlink() and not path.is_junction(), "Linked output ancestry refused")
    require(not output.exists() and addon_case in ADDONS, "Fresh output and explicit A/B addon choice")
    inputs = source_inputs()
    geometry = original_geometry(inputs["tools-source/asset-bridge/animation/rig/prepare_skin_fixture.py"])
    generated = {
        "writer.cpp": writer_source(inputs["ops/doom-source/writer_rigid.cpp"]),
        "half_uv.hpp": inputs["ops/doom-source/half_uv.hpp"],
        "geometry-reference.json": (json.dumps(geometry, indent=2) + "\n").encode(),
        "zone_source/" + ZONE + ".csv": ("material,," + MATERIAL + "\n" + "\n".join("xmodel," + n for n in NAMES.values()) + "\n").encode(),
    }
    for profile in NAMES:
        generated[profile + "/rigid_geometry.hpp"] = geometry_header(geometry, profile)
    plan = {
        "schema": "iw7.original-rig-rigid-control-source-plan/1",
        "purpose": "Exact original ribbon rigid-format control; source preparation only",
        "artifact_variant": "RigidControl", "zone": ZONE, "native_source_pin": PIN,
        "models": NAMES, "material_reference": MATERIAL,
        "geometry": {"vertices": 8, "triangles": 6, "xyz": "unchanged original engine units", "uv": "unchanged/no V flip", "tangent_packed": "200ffe00", "normal_packed": "e0080000", "self_visibility_packed": "01fe0100", "vertex_color_packed": "ffffffff"},
        "rigid_expectation": {"bones": 1, "roots": 1, "client_bones": 0, "surfaces": 1, "lods": 1, "surface_flags": 0x82, "model_flags": 0x80000, "rigid_lists": 1, "bone_offset": 0, "vertex_coverage": 8, "triangle_offset": 0, "triangle_coverage": 6, "collision_tree": None, "blend_counts": [0] * 8, "blend_bytes": 0, "part_bits": [0x80000000] + [0] * 7},
        "expected_inventory": ["material,," + MATERIAL, *[t + "," + n + suffix for n in NAMES.values() for t, suffix in (("xmodelsurfs", "_lod0"), ("xmodel", ""))], "rawfile," + ZONE],
        "original_fastfile_reference": {"bytes": 1064, "sha256": "ea7ba4be1d5e6f0878431b51e7b9b1ba9d2b10bf74b1ad21da14d55c414e145d", "reused_as_control": False},
        "runtime": {"fs_game": "mods/sdk_original_rig_probe", "sdk_core_sha256": "49f7e1aa336bb2fdb73e5c36be03c213311ead4555fc9bca0d7b4e69ccdc219b", "addon_case": addon_case, "addon": ADDONS[addon_case], "mode": "DISPLAY only; ANIMATE refused", "native": "B78 unchanged, raw header counts only; fresh protected bound session", "native_sha256": "b78b6020c1e0afdd9e548b81fc3910c68477c253abfb43ede159aed36d9752ce", "stock_filter": "explicitly enabled for the chosen stock addon", "profile_gate": "New RigidControl requires real native emission and FF build/dump/readback receipts; default Original still exact ea7", "camera_and_poses": "unchanged SDK49f/original scene; no teleport or new map"},
        "future_stages": ["separately admit compile first/second writer with matching rigid_geometry.hpp and pinned native headers", "emit distinct named first/second native pairs in fresh owned roots", "same existing ZoneTool build/verify/dump for distinct zone", "each writer --verify-existing on its owned FF redump; compare every packed vertex/index/material/bind/bounds", "55 qualifies closed profile and transactional separate FF installation only from real tuple/receipts", "one separately authorized protected private DISPLAY comparison"],
        "fastfile": {"bytes": None, "sha256": None, "build_receipt": None, "readback_receipt": None},
        "native_writer_compiled": False, "native_writer_executed": False, "ff_built": False,
        "rigid_material_technique_verified": False, "gpu_verified": False, "pixels_verified": False, "ready": False,
    }
    generated["plan.source.json"] = (json.dumps(plan, indent=2) + "\n").encode()
    manifest = {"schema": "iw7.original-rig-rigid-control-source-manifest/1", "artifact_variant": "RigidControl", "source_inputs": PINS, "generated": {n: {"bytes": len(p), "sha256": digest(p)} for n, p in generated.items()}, "source_only": True, "native_or_stock_read": False, "compiled": False, "ff_built": False, "runtime_verified": False}
    output.mkdir(parents=True, exist_ok=False)
    for name, payload in generated.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(payload)
    with (output / "source-manifest.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, indent=2)
        stream.write("\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--addon-case", required=True, choices=tuple(ADDONS))
    args = parser.parse_args()
    print(json.dumps(prepare(args.output, args.addon_case), indent=2))

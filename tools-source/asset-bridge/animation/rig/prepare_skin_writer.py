"""Freeze source for a distinct native two-bone writer; never compile or run it."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from read_skin_fixture import PIN, SIZES, parse, read, verify_payloads

OWN_FILES = ("writer_skin_two_bone.cpp", "skin_native_abi.hpp", "half_uv.hpp")
EXTRA_INTERFACES = ("utils/io/assetmanager.hpp", "utils/io/filesystem.hpp", "utils/memory.hpp",
                    "h1/converter/iw7/assets/xmodel.cpp", "../game/shared.cpp")
MATERIAL = "mopw/character_park_clown_zombie_shoes"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def unlinked(path):
    require(path.is_absolute(), "absolute source/input/output path")
    for current in (path, *path.parents):
        require(not current.is_symlink() and not current.is_junction(), "linked source/input/output ancestry")
    return path


def literal(value):
    text = format(value, ".9g")
    if "." not in text and "e" not in text:
        text += ".0"
    return text + "f"


def geometry_header(files, manifest):
    # This independent reader also compares to the fixed analytical original.
    verify_payloads(files, manifest)
    lines = ["#pragma once", "#include <cstdint>", "namespace doom_skin_input {",
             'inline constexpr const char* first_name="paris_doom_skin_two_bone_first_a";',
             'inline constexpr const char* second_name="paris_doom_skin_two_bone_second_a";',
             'inline constexpr const char* material_name="' + MATERIAL + '";']
    streams = (("positions", "float", "positions.f32.bin", "f", 8, 3),
               ("normals", "float", "normals.f32.bin", "f", 8, 3),
               ("uvs", "float", "uv.f32.bin", "f", 8, 2),
               ("triangles", "std::uint16_t", "triangles.u16.bin", "H", 6, 3),
               ("parents", "std::uint8_t", "parents.u8.bin", "B", 1, 1),
               ("angles", "std::int16_t", "tag-angles.i16.bin", "h", 1, 4),
               ("tag_positions", "float", "tag-positions.f32.bin", "f", 1, 3),
               ("bases", "float", "base-mats.f32.bin", "f", 2, 8),
               ("first_blend", "std::uint16_t", "first.blend.u16.bin", "H", 1, 24),
               ("second_blend", "std::uint16_t", "second.blend.u16.bin", "H", 1, 24))
    for name, ctype, filename, code, rows, columns in streams:
        values = struct.unpack("<" + str(rows * columns) + code, files[filename])
        values = [literal(v) if code == "f" else str(v) for v in values]
        lines.append("inline constexpr " + ctype + " " + name + "[" + str(rows) + "][" + str(columns) + "]={")
        lines.extend("    {" + ", ".join(values[r * columns:(r + 1) * columns]) + "}" + ("," if r + 1 < rows else "") for r in range(rows))
        lines.append("};")
    lines.extend(("}", ""))
    return "\n".join(lines).encode("ascii")


def input_snapshot(root):
    unlinked(root)
    read(root)
    result = {name: (root / name).read_bytes() for name in (*SIZES, "fixture-input.json")}
    files = {name: result[name] for name in SIZES}
    manifest = parse(result["fixture-input.json"])
    verify_payloads(files, manifest)
    return result, manifest


def tool_snapshot(source, manifest):
    unlinked(source)
    require(source.is_dir(), "existing tool source")
    require(subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip() == PIN, "exact clean ZoneTool pin")
    require(not subprocess.check_output(["git", "-C", str(source), "status", "--porcelain", "--untracked-files=all"], text=True).strip(), "changed shared tool source must be preserved")
    result = {}
    for name in (*manifest["interface_hashes"], *EXTRA_INTERFACES):
        relative = "src/zonetool/game/shared.cpp" if name == "../game/shared.cpp" else "src/zonetool/zonetool/" + name
        path = unlinked(source / relative)
        require(path.is_file() and 0 < path.stat().st_size <= 2 * 1024 * 1024, "bounded regular pinned interface " + name)
        result[name] = digest(path.read_bytes())
        if name in manifest["interface_hashes"]:
            require(result[name] == manifest["interface_hashes"][name], "physical interface differs from input receipt " + name)
    return result


def source_report(originals, manifest, refs, files):
    return {"schema": "iw7.doom-two-bone-writer-source/1", "source_pin": PIN,
            "input_manifest_sha256": digest(originals["fixture-input.json"]),
            "input_hashes": {name: digest(value) for name, value in originals.items()},
            "interface_hashes": refs, "prepared_hashes": {name: digest(value) for name, value in files.items()},
            "profiles": manifest["profiles"], "material_reference": MATERIAL,
            "counts": manifest["counts"], "original_input_bytes_verified": True,
            "interface_bytes_reverified": True, "compiled": False, "native_writer_executed": False,
            "native_output_read": False, "ff_built": False, "pixels_verified": False, "ready": False}


def verify_prepared(inputs, source, prepared):
    inputs, source, prepared = map(unlinked, (inputs, source, prepared))
    require(prepared.is_dir(), "existing prepared writer source directory")
    require({p.name for p in prepared.iterdir()} == set(OWN_FILES) | {"skin_geometry.hpp", "skin-writer-source.json"}, "exact prepared writer source inventory")
    originals, manifest = input_snapshot(inputs)
    refs = tool_snapshot(source, manifest)
    own = Path(__file__).absolute().parent
    files = {name: unlinked(own / name).read_bytes() for name in OWN_FILES}
    files["skin_geometry.hpp"] = geometry_header({name: originals[name] for name in SIZES}, manifest)
    for name, expected in files.items():
        path = unlinked(prepared / name)
        require(path.is_file() and 0 < path.stat().st_size <= 65536 and path.read_bytes() == expected, "prepared source differs from reviewed source/input " + name)
    path = unlinked(prepared / "skin-writer-source.json")
    require(path.is_file() and 0 < path.stat().st_size <= 16384, "bounded prepared writer source receipt")
    receipt = parse(path.read_bytes())
    expected = source_report(originals, manifest, refs, files)
    require(json.dumps(receipt, sort_keys=True) == json.dumps(expected, sort_keys=True), "exact typed prepared writer source receipt")
    require(input_snapshot(inputs)[0] == originals, "input changed during prepared-source verification")
    require(tool_snapshot(source, manifest) == refs, "tool changed during prepared-source verification")
    return expected


def prepare(inputs, source, output):
    inputs, source, output = map(unlinked, (inputs, source, output))
    require(not output.exists(), "fresh writer source directory")
    # The generated header freezes both hypotheses; no runtime input parser or
    # arbitrary candidate/material selector enters the native executable.
    originals, manifest = input_snapshot(inputs)
    refs = tool_snapshot(source, manifest)
    own = Path(__file__).absolute().parent
    files = {name: unlinked(own / name).read_bytes() for name in OWN_FILES}
    require(all(0 < len(value) <= 65536 for value in files.values()), "bounded reviewed writer source")
    files["skin_geometry.hpp"] = geometry_header({name: originals[name] for name in SIZES}, manifest)
    require(input_snapshot(inputs)[0] == originals, "input changed during source preparation")
    require(tool_snapshot(source, manifest) == refs, "tool changed during source preparation")
    require(all((own / name).read_bytes() == files[name] for name in OWN_FILES), "reviewed writer source changed during preparation")
    report = source_report(originals, manifest, refs, files)
    output.mkdir(parents=True, exist_ok=False)
    unlinked(output)
    for name, payload in files.items():
        with unlinked(output / name).open("xb") as stream:
            stream.write(payload)
    with unlinked(output / "skin-writer-source.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    require(all((output / name).read_bytes() == payload for name, payload in files.items()), "prepared source write differs")
    require(input_snapshot(inputs)[0] == originals, "input changed during source writes")
    require(tool_snapshot(source, manifest) == refs, "tool changed during source writes")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify-prepared", action="store_true", help="Read/revalidate only; no writes or compiler")
    args = parser.parse_args()
    operation = verify_prepared if args.verify_prepared else prepare
    print(json.dumps(operation(args.inputs, args.source, args.output), indent=2))

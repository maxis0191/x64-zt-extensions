"""Prepare one fixed root-channel clip's text sources, never native assets or Run."""
import argparse
import hashlib
import json
from pathlib import Path
import math
import stat
import sys
import types

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
NAME = "paris_original_probe_root_rotate"
LEGACY_PINS = {
    "prepare_probe.py": "9246a55ab62dbc7534effcc59f171c685357fa49135c0bac23f6365b064409be",
    "writer_probe.cpp": "3b9c1f6873b10dcfcaaea7fe14de53fd90d092c613ec627b5206ccd3cc9aeb6b",
    "probe_native_abi.hpp": "d00c5d3be94f09927e60930b2d4fcd64d25610088e01eb87f954c56eb94d292f",
}
REFERENCE_PINS = {
    "CoDXAnimTranslator.cpp": "7f9e02358f83ded3a032be78aac2114f69140f16060b6d77585dafea72396334",
    "GameInfiniteWarfare.cpp": "3ce8dd51025df1cc2d097d7aa4d9bb58b6c8c08157bb1019207e0a33c7929964",
    "DBGameAssets.h": "6e86f287debced404ba50b3bee60fe00a476008d2ed15057fd03c06207b28740",
}
# DBGameAssets::IWXAnim field order, mapped by GameInfiniteWarfare::ReadXAnim.
# Translator stages consume zero-rotations, quat2, then quat4 in names order;
# this profile has only quat4 root rotation and no authored translation stream.
CATEGORIES = ("NoneRotatedBoneCount", "TwoDRotatedBoneCount", "NormalRotatedBoneCount",
              "TwoDStaticRotatedBoneCount", "NormalStaticRotatedBoneCount",
              "NormalTranslatedBoneCount", "PreciseTranslatedBoneCount",
              "StaticTranslatedBoneCount", "NoneTranslatedBoneCount", "TotalBoneCount")
COUNTS = [0, 0, 1, 0, 0, 0, 0, 0, 1, 1]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def unlinked(path):
    require(path.is_absolute() and ".." not in path.parts, "Absolute canonical source path required")
    for p in (path, *path.parents):
        info = p.lstat() if p.exists() or p.is_symlink() else None
        require(not p.is_symlink() and not (info and getattr(info, "st_file_attributes", 0) &
                getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024)), "Source reparse ancestry refused")


def bounded_text(path, limit=262144):
    unlinked(path)
    require(path.is_file() and 0 < path.stat().st_size <= limit, "Bounded source text required")
    data = path.read_bytes()
    require(0 < len(data) <= limit and b"\0" not in data, "Source text grew or contains NUL")
    data.decode("utf-8")
    return data


def legacy():
    payload = bounded_text(BASE / "prepare_probe.py")
    require(digest(payload) == LEGACY_PINS["prepare_probe.py"], "Frozen preparer source changed")
    module = types.ModuleType("_root_clip_fixed_legacy")
    module.__file__ = str(BASE / "prepare_probe.py")
    exec(compile(payload, module.__file__, "exec"), module.__dict__)
    return module


def original_root_clip():
    return {"schema": "iw7.original-root-rotation-authoring/1", "name": NAME,
            "channels": ["tag_origin"], "numframes": 30, "framerate": 30,
            "loop": True, "tag_origin_x_degrees": [[0, 0], [10, 45], [20, -45], [30, 0]],
            "notetrack": {"name": "probe_contact", "normalized_time": 0.5},
            "frequency": 1, "root_motion": False, "translation_tracks": False}


def parse_clip(payload):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "Duplicate authoring key refused")
            result[key] = value
        return result
    return json.loads(payload, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite authoring value")))


def compile_root(clip):
    # Exact values and types: True is not an authored integer 1.
    expected = original_root_clip()
    require(json.dumps(clip, sort_keys=True, allow_nan=False) ==
            json.dumps(expected, sort_keys=True), "Only the closed root-rotation authoring profile is supported")
    producer = legacy()
    samples = []
    for _, angle in clip["tag_origin_x_degrees"]:
        half = math.radians(angle) / 2
        samples.extend(int(producer.f32(producer.f32(v) * 32767.0))
                       for v in (math.sin(half), 0, 0, math.cos(half)))
    return {"data_byte": [0, 10, 20, 30], "data_short": [3],
            "random_data_short": samples, "bone_counts": COUNTS.copy()}


def writer_source(payload):
    require(digest(payload) == LEGACY_PINS["writer_probe.cpp"], "Frozen original writer source changed")
    text = payload.decode("utf-8")
    replacements = {
        'static constexpr auto asset_name = "paris_original_probe_bend";':
        'static constexpr auto asset_name = "' + NAME + '";',
        'scr_string_t names[]={static_cast<scr_string_t>(1),static_cast<scr_string_t>(2)};':
        'scr_string_t names[]={static_cast<scr_string_t>(1)};',
        'case 1:return "tag_origin";case 2:return "tag_probe";case 3:return "probe_contact";':
        'case 1:return "tag_origin";case 3:return "probe_contact";',
    }
    for before, after in replacements.items():
        require(text.count(before) == 1, "Unique pinned writer anchor required")
        text = text.replace(before, after, 1)
    # All serialization/IO/ABI code remains the pinned original implementation.
    return text.encode("utf-8")


def prepare(source_root, reference_root, output):
    source_root, reference_root, output = map(Path, (source_root, reference_root, output))
    for p in (source_root, reference_root, output):
        unlinked(p)
    require(not output.exists() and output.parent.is_dir(), "Fresh source output under existing parent required")
    inputs = {name: bounded_text(BASE / name) for name in LEGACY_PINS}
    for name, payload in inputs.items():
        require(digest(payload) == LEGACY_PINS[name], "Pinned legacy source differs: " + name)
    references = {name: bounded_text(reference_root / name) for name in REFERENCE_PINS}
    for name, payload in references.items():
        require(digest(payload) == REFERENCE_PINS[name], "Pinned primary reference differs: " + name)
    header = references["DBGameAssets.h"].decode("utf-8").replace("\r\n", "\n")
    section = header[header.index("struct IWXAnim\n"):header.index("struct IWXAnimDeltaParts\n")]
    positions = [section.index("uint8_t " + field + ";") for field in CATEGORIES]
    require(positions == sorted(positions), "Pinned IW category order differs")
    producer = legacy()
    source_hashes = producer.check_sources(source_root, reference_root)
    shared = bounded_text(source_root / "src/zonetool/game/shared.cpp")
    require(digest(shared) == "de421b87b65d230622e77c6bca1da2d2435ddf646b2ab9c506cc55c043301d41",
            "Pinned quaternion encoder source changed")
    source_hashes["src/zonetool/game/shared.cpp"] = digest(shared)
    clip_payload = bounded_text(HERE / "clip.source.json", 4096)
    clip = parse_clip(clip_payload)
    encoded = compile_root(clip)
    lines = ["#pragma once", "namespace original_probe {"]
    for name, values in encoded.items():
        kind = "char" if name == "data_byte" else "unsigned char" if name == "bone_counts" else "short"
        lines.append("inline " + kind + " " + name + "[]={" + ", ".join(map(str, values)) + "};")
    generated = {"writer.cpp": writer_source(inputs["writer_probe.cpp"]),
                 "probe_native_abi.hpp": inputs["probe_native_abi.hpp"],
                 "probe_clip.hpp": ("\n".join(lines + ["}", ""])).encode(),
                 "probe_dump.inc": producer.dump_method(bounded_text(
                     source_root / "src/zonetool/zonetool/iw7/assets/xanim.cpp")),
                 "clip.source.json": (json.dumps(clip, indent=2) + "\n").encode(),
                 "zone.source.csv": ("xanim," + NAME + "\n").encode()}
    manifest = {"schema": "iw7.prepared-original-root-rotation-source/1",
                "zonetool_pin": producer.PIN, "source_hashes": source_hashes,
                "legacy_source_pins": LEGACY_PINS, "reference_source_pins": REFERENCE_PINS,
                "preparer_sha256": digest(bounded_text(Path(__file__))),
                "reader_sha256": digest(bounded_text(HERE / "read_root_rotation.py")),
                "authoring_source_sha256": digest(clip_payload),
                "category_order": list(CATEGORIES), "bone_counts": COUNTS,
                "channels": ["tag_origin"], "rotation_keys": clip["tag_origin_x_degrees"],
                "model_variant": "RigidControl", "model_bones": ["tag_origin"],
                "source_only": True, "compiled": False, "native_writer_executed": False,
                "native_artifact": None, "ff_built": False, "fastfile": None,
                "runtime_tree_binding_verified": False, "runtime_root_pose_verified": False,
                "runtime_world_motion_verified": False, "pixels_verified": False, "ready": False,
                "frequency_runtime_verified": False, "note_delivery_verified": False,
                "pose_interpretation": "authored local-root rotation hypothesis, not an engine outcome",
                "generated_sha256": {name: digest(data) for name, data in generated.items()},
                "prepared_bytes": sum(map(len, generated.values()))}
    output.mkdir()
    for name, data in generated.items():
        with (output / name).open("xb") as stream:
            stream.write(data)
    with (output / "source-manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2)
        stream.write("\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--reference-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.source_root, args.reference_root, args.output), indent=2))
    except (OSError, ValueError) as error:
        print(json.dumps({"status": "invalid-root-rotation-source", "error": str(error)}))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

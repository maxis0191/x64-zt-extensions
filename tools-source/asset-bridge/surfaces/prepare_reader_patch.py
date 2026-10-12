"""Prepare a pinned, opt-in reader correction without editing shared sources."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path

from inspect_content import Inputs, no_links, require, verify_contract


BASE = "src/zonetool/zonetool/iw7/assets/"
FLAG = 'utils::flags::has_flag("strict-content-sources")'


def replace_exact(text, old, new, count=1):
    require(text.count(old) == count, "source anchor changed: " + old[:100])
    return text.replace(old, new)


def transform(name, text):
    """Only explicit builder opt-in changes behavior; no new zone-name policy."""
    text = text.replace("\r\n", "\n")
    if name in ("material.cpp", "techset.cpp"):
        text = replace_exact(text, "#include <std_include.hpp>\n",
                             "#include <std_include.hpp>\n#include <utils/flags.hpp>\n")
    if name == "material.cpp":
        # Dumping a full-width name must not scan the following float literals.
        # name.data() below still stops at an embedded NUL, preserving JSON text.
        text = replace_exact(text,
                             "std::string name = asset->constantTable[i].name;",
                             "std::string name(asset->constantTable[i].name, sizeof(asset->constantTable[i].name));")
        # All three occurrences: parse texture names, parse techset name, reject DB default.
        marker = 'filesystem::get_fastfile().starts_with("paris_enemy_")'
        text = replace_exact(text, marker, FLAG + " || " + marker, 3)
        old = '\t\t\t\tstrcat(constant_def[i].name, constantTable[i]["name"].get<std::string>().data());'
        new = ('\t\t\t\tif (' + FLAG + ')\n\t\t\t\t{\n'
               '\t\t\t\t\tconst auto constant_name = constantTable[i]["name"].get<std::string>();\n'
               '\t\t\t\t\tif (constant_name.size() > sizeof(constant_def[i].name))\n'
               '\t\t\t\t\t\tthrow std::runtime_error("IW7 content constant name exceeds fixed field: " + constant_name);\n'
               '\t\t\t\t\tstd::memset(constant_def[i].name, 0, sizeof(constant_def[i].name));\n'
               '\t\t\t\t\tstd::memcpy(constant_def[i].name, constant_name.data(), constant_name.size());\n'
               '\t\t\t\t}\n\t\t\t\telse\n\t' + old)
        text = replace_exact(text, old, new)
    elif name == "gfximage.cpp":
        old = 'if (filesystem::get_fastfile().starts_with("paris_enemy_") &&\n\t\t\tasset->imageFormat'
        new = 'if ((' + FLAG + ' || filesystem::get_fastfile().starts_with("paris_enemy_")) &&\n\t\t\tasset->imageFormat'
        text = replace_exact(text, old, new)
        # Do not change image source precedence or the old donor-stream capture path.
        old = 'if (filesystem::get_fastfile().starts_with("paris_enemy_"))\n\t\t\t\tthrow std::runtime_error("Required IW7 enemy image source missing: " + name);'
        new = 'if (' + FLAG + ')\n\t\t\t\tthrow std::runtime_error("Required IW7 content image source missing: " + name);\n\t\t\t' + old
        text = replace_exact(text, old, new)
    elif name == "techset.cpp":
        # Existing builder fallback is retained unless this explicit contract is selected.
        text = replace_exact(text, "\t\t\t// get a random one from the directory\n",
                             "\t\t\t// Strict content builds must not borrow another material's state/buffers.\n"
                             "\t\t\tif (" + FLAG + ") return path;\n\n"
                             "\t\t\t// get a random one from the directory\n")
        text = replace_exact(text, "\t\t\t(*def_ptr) = nullptr;\n\t\t\treturn;\n",
                             "\t\t\tif (" + FLAG + ")\n"
                             '\t\t\t\tthrow std::runtime_error("Required IW7 content constant buffer missing: " + path);\n'
                             "\t\t\t(*def_ptr) = nullptr;\n\t\t\treturn;\n")
        for buffer in ("indexes", "statebits"):
            old = f"\t\t\tfread({buffer}, MaterialTechniqueType::TECHNIQUE_COUNT, 1, fp);"
            new = ("\t\t\tif (" + FLAG + " && file.size() != static_cast<std::size_t>(MaterialTechniqueType::TECHNIQUE_COUNT))\n"
                   '\t\t\t\tthrow std::runtime_error("IW7 content technique-index length mismatch: " + path);\n' + old)
            text = replace_exact(text, old, new)
    else:
        raise ValueError("unowned patch target")
    return text


def verify_prepared(source, output):
    verify_contract(source)
    original, prepared = Inputs(source), Inputs(output)
    manifest = prepared.json("reader-patch.json")
    require(manifest.get("builder_argument") == "-strict-content-sources" and
            manifest.get("compiled") is False and manifest.get("ready") is False,
            "source-only patch manifest required")
    diffs = []
    for name in ("material.cpp", "techset.cpp", "gfximage.cpp"):
        path = BASE + name
        before = original.read(path).decode("utf-8").replace("\r\n", "\n")
        after = transform(name, before)
        require(prepared.read(path) == after.encode(), "prepared reader bytes differ from recomputed patch: " + name)
        diffs.extend(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                         fromfile="a/" + path, tofile="b/" + path))
    require(prepared.read("strict-content-sources.patch") == "".join(diffs).encode(), "prepared diff differs")
    actual = {k: v["sha256"] for k, v in prepared.files.items() if k != "reader-patch.json"}
    require(manifest.get("generated_files") == actual, "prepared hashes differ")
    return manifest


def prepare(source, output):
    source, output = no_links(Path(source).absolute()), no_links(Path(output).absolute())
    require(not output.exists(), "fresh patch output directory required")
    require(not output.is_relative_to(source) and not source.is_relative_to(output),
            "patch output must be separate from shared source")
    contract = verify_contract(source)
    inputs = Inputs(source)
    generated = {}
    patch = []
    for name in ("material.cpp", "techset.cpp", "gfximage.cpp"):
        path = BASE + name
        before = inputs.read(path).decode("utf-8").replace("\r\n", "\n")
        after = transform(name, before)
        generated[path] = after.encode()
        patch.extend(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                          fromfile="a/" + path, tofile="b/" + path))
    generated["strict-content-sources.patch"] = "".join(patch).encode()
    manifest = {"schema": "iw7.content-reader-patch/1", "source_pin": contract["zonetool"]["revision"],
                "builder_argument": "-strict-content-sources", "default_source_resolution_changed": False,
                "fixed_name_dump_read_bounded": True,
                "generated_files": {k: hashlib.sha256(v).hexdigest() for k, v in generated.items()},
                "compiled": False, "runtime_verified": False, "ready": False,
                "remaining": ["Native compile/tests", "Original material/image checker roundtrip and pixels",
                              "Recipient-reference resolution", "Retail regression without flag"]}
    output.mkdir(parents=True, exist_ok=False)
    for path, data in generated.items():
        destination = output / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(data)
    with (output / "reader-patch.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2)
        stream.write("\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zt-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.zt_source, args.output), indent=2))

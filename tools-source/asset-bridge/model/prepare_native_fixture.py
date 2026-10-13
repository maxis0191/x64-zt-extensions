"""Prepare a tiny native test from actual patched production bodies. Never compile.

Includes real H1/IW7 headers in place, not copied SDKs. The caller must obtain
parent GO and resource admission before invoking a compiler or the executable.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from blend_bridge import read_bounded, require, unlinked
from prepare_zonetool_patch import SOURCE, git
from verify_zonetool_patch import verify


def prepare(repo, output):
    receipt = verify(repo)
    patch = Path(__file__).with_name("zonetool-fab9358-h1-xsurface.patch")
    unlinked(output)
    require(output.parent.is_dir() and not output.exists(), "fresh fixture directory required")
    with tempfile.TemporaryDirectory(prefix="iw7-h1-native-source-") as directory:
        root = Path(directory).resolve()
        target = root / SOURCE
        target.parent.mkdir(parents=True)
        target.write_bytes(git(repo, "show", "HEAD:" + SOURCE).replace(b"\r\n", b"\n"))
        git(root, "apply", str(patch.resolve()))
        applied = target.read_bytes().replace(b"\r\n", b"\n")
    require(hashlib.sha256(applied).hexdigest() == receipt["patched_lf_sha256"], "native candidate source hash")
    source = applied.decode()
    begin, end = "\t\t\tvoid ValidateH1BlendVerts(", "\n\t\t\tvoid dump("
    require(source.count(begin) == source.count(end) == 1, "production function boundary mismatch")
    bodies = source[source.index(begin):source.index(end)]
    # Copy the three real converter macros verbatim, without unrelated includes.
    macro_path = repo / "src/zonetool/zonetool/h1/converter/include.hpp"
    macros_source = read_bounded(macro_path, 65536).decode().replace("\r\n", "\n")
    require(macros_source.encode() == git(repo, "show", "HEAD:src/zonetool/zonetool/h1/converter/include.hpp").replace(b"\r\n", b"\n"),
            "native macro source differs from pin")
    macros = []
    for name in ("COPY_VALUE", "COPY_ARR", "REINTERPRET_CAST_SAFE"):
        marker = "#define " + name + "("
        require(macros_source.count(marker) == 1, "production macro boundary mismatch")
        start = macros_source.index(marker)
        stop = macros_source.find("\n\n", start)
        require(stop > start, "production macro end missing")
        macros.append(macros_source[start:stop])
    include = ('// Exact production functions and macros from the checked patch.\n'
               '#define BRIDGE_PRODUCTION_SHA256 "' + receipt["patched_lf_sha256"] + '"\n'
               + '\n\n'.join(macros) + '\nnamespace zonetool::h1::converter::iw7 {\n' + bodies + '\n}\n')
    template = Path(__file__).with_name("native_fixture.cpp").read_bytes()
    headers = ("src/zonetool/zonetool/h1/structs.hpp", "src/zonetool/zonetool/iw7/structs.hpp", "src/common/utils/memory.hpp")
    header_hashes = {}
    for relative in headers:
        data = read_bounded(repo / relative, 1024 * 1024)
        require(data.replace(b"\r\n", b"\n") == git(repo, "show", "HEAD:" + relative).replace(b"\r\n", b"\n"),
                "native header differs from pin")
        header_hashes[relative] = hashlib.sha256(data).hexdigest()
    # All validation completes before a fresh directory or any outputs exist.
    output.mkdir()
    (output / "native_fixture.cpp").write_bytes(template)
    (output / "native_production.inc").write_bytes(include.encode())
    receipt.update(schema="iw7.asset-bridge.native-fixture-preparation/1", native_compiled=False,
                   native_behavior_executed=False, headers_read_in_place_sha256=header_hashes,
                   production_function_body_sha256=hashlib.sha256(bodies.encode()).hexdigest(),
                   generated_files_sha256={name:hashlib.sha256((output/name).read_bytes()).hexdigest()
                                           for name in ("native_fixture.cpp", "native_production.inc")},
                   generated_source_bytes=len(template)+len(include.encode()),
                   compiler_arguments_after_go=["cl.exe", "/nologo", "/std:c++20", "/EHsc", "/W4", "/MT",
                       "/I"+str(repo/"src/zonetool"), "/I"+str(repo/"src/common"),
                       "/Fo"+str(output/"native_fixture.obj"), "/Fe"+str(output/"native_fixture.exe"),
                       str(output/"native_fixture.cpp")])
    (output / "preparation.local.json").write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source_repo, args.output), indent=2))

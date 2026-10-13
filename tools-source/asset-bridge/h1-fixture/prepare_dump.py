"""Prepare exact IW7 dump bodies around the witnessed H1 harness; no native work.

The existing B preparation and source contracts remain separate. The only C++
adaptations are declarations, logging, the original-fixture string bridge and a
hook after existing parser/converter checks, all recorded in this receipt.
"""
import argparse
import json
from pathlib import Path

import generate
import prepare_native as native

OWN = Path(__file__).resolve().parent
EXTRA_NAMES = ("iw7/assets/xmodel.cpp", "iw7/assets/xsurface.cpp", "iw7/common/havok.cpp",
               "iw7/common/havok.hpp")


def checked_sources(repo):
    sources, prior = native.checked_sources(repo)
    contract = json.loads(native.raw_bounded(OWN / "dump-source-contract.json"))
    generate.require(contract["pin"] == generate.PIN and
                     set(contract["lf_sha256"]) == {native.BASE + n for n in EXTRA_NAMES},
                     "dump contract identity")
    for name, sha in contract["lf_sha256"].items():
        data = native.bounded(repo / name)
        generate.require(native.digest(data) == sha, "dump source drift: " + name)
        sources[name] = data.decode()
    return sources, {**prior["lf_sha256"], **contract["lf_sha256"]}


def assemble(sources):
    payloads, fragments = native.probe_sources(sources)
    def remember(name, text):
        fragments[name] = {"bytes": len(text.encode()), "lf_sha256": native.digest(text.encode())}
        return text
    havok = sources[native.BASE + "iw7/common/havok.cpp"]
    # Keep real header validation and the complete helper, including its absent-
    # data early return. Optional Havok is rejected by the fixture before dump.
    support = native.between(havok, "namespace zonetool::iw7", "\n\t\t\tchar* parse_havok_data(")
    support += havok[havok.index("\t\t\tvoid dump_havok_data("):]
    text = remember("iw7_havok_dump_support", support) + "\nnamespace zonetool::iw7 {\n"
    for name, marker in (("xmodel", "\tvoid xmodel::dump("), ("xsurface", "\tvoid dump_subdiv(")):
        source = sources[native.BASE + "iw7/assets/" + name + ".cpp"]
        generate.require(source.count(marker) == 1 and source.endswith("\n}"), "dump boundary changed")
        # Remove namespace closing only; every function byte is unmodified.
        text += remember("iw7_" + name + "_dump", source[source.index(marker):-1]) + "\n"
    text += "}\n"
    payloads["production_dumps.inc"] = text.encode()
    payloads["native_dump_adapter.inc"] = native.bounded(OWN / "native_dump_adapter.inc")
    probe = payloads["native_probe.cpp"].decode()
    replacements = {
        "static void observe(const std::filesystem::path& root)":
            '#include "native_dump_adapter.inc"\n\nstatic void observe(const std::filesystem::path& root)',
        "    // No pointer addresses or local paths in emitted evidence. No dump call exists.":
            "    dump_original(model_parser, source_model, model, group);\n    // Dump bytes remain local; JSON exposes no addresses.",
        "iw7.h1-parser-converter-observation/1": "iw7.h1-parser-converter-dump-observation/1",
        r'\"dump_executed\":false': r'\"dump_executed\":true,\"fixture_string_adapter\":true,\"string_calls\":1,\"dump_files\":2',
    }
    for old, new in replacements.items():
        generate.require(probe.count(old) == 1, "dump hook source boundary changed")
        probe = probe.replace(old, new)
    payloads["native_probe.cpp"] = probe.encode()
    return payloads, fragments


def expected(repo):
    sources, hashes = checked_sources(repo)
    payloads, fragments = assemble(sources)
    receipt = {"schema": "iw7.h1-dump-preparation/1", "source_pin": generate.PIN,
               "source_lf_sha256": hashes, "fragments": fragments,
               "reviewed_patch_lf_sha256": native.PATCH_SHA, "patched_surface_lf_sha256": native.PATCHED_SHA,
               "native_compiled": False, "native_executed": False, "dump_executed": False,
               "bone_engine_token_resolved": False, "material_complete": False,
               "fixture_string_adapter": "token 0 -> actual H1 parser address-keyed tag_origin; token unchanged",
               "io": "production filesystem in fresh retained probe/dump/h1_original directories",
               "limits": "64 KiB per dump; 32 MiB combined stage budget; no FF or render claim",
               "prepared_files": {n: {"bytes": len(d), "sha256": native.digest(d)} for n, d in payloads.items()}}
    payloads["preparation.local.json"] = (json.dumps(receipt, indent=2) + "\n").encode()
    generate.require(sum(map(len, payloads.values())) < 1024**2, "one MiB preparation limit")
    return payloads, receipt


def verify_prepared(repo, output):
    payloads, receipt = expected(repo)
    generate.regular_ancestry(output)
    generate.require(set(p.name for p in output.iterdir()) == set(payloads), "dump prepared file set differs")
    for name, data in payloads.items():
        generate.require(native.raw_bounded(output / name) == data, "dump prepared bytes differ: " + name)
    return {"schema": "iw7.h1-dump-preflight/1", "prepared_files_verified": len(payloads),
            "source_files_verified": len(receipt["source_lf_sha256"]), "native_executed": False}


def prepare(repo, output):
    payloads, receipt = expected(repo)
    generate.regular_ancestry(output)
    generate.require(output.parent.is_dir() and not output.exists(), "fresh dump preparation directory required")
    output.mkdir()
    for name, data in payloads.items():
        with (output / name).open("xb") as stream:
            stream.write(data)
    verify_prepared(repo, output)
    return receipt


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--source-repo", type=Path, required=True)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--verify", action="store_true")
    args = cli.parse_args()
    print(json.dumps((verify_prepared if args.verify else prepare)(args.source_repo, args.output), indent=2))

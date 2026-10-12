"""Prepare an exact-production-body H1 parser/converter probe; NEVER build/run.

Windows SDK and production headers are read in place. Preparation is small Python
work; compilation and execution need separate parent GO/resource admission.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

import generate
from inspect_fixture import inspect_pair

BASE = "src/zonetool/zonetool/"
PATCH_SHA = "e50c7f18b9e3b8904b441ddf10bb32a3315442d22afec7d174bda699f9db26a0"
PATCHED_SHA = "f0910695382533abf9aed8a0c03f2f0da9d9af1ce2baee0efb5e78d252218a15"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def raw_bounded(path):
    generate.regular_ancestry(path)
    generate.require(path.is_file() and path.stat().st_size <= 1024*1024, "bounded source required")
    return path.read_bytes()


def bounded(path):
    return raw_bounded(path).replace(b"\r\n", b"\n")


def checked_sources(repo):
    generate.regular_ancestry(repo)
    head = subprocess.run(["git","-C",str(repo),"rev-parse","HEAD"],
                          capture_output=True,text=True,check=True).stdout.strip()
    contract = json.loads(Path(__file__).with_name("native-source-contract.json").read_text())
    generate.require(head == contract["pin"] == generate.PIN, "native source pin mismatch")
    result = {}
    for name, expected in contract["lf_sha256"].items():
        content = bounded(repo/name)
        generate.require(digest(content) == expected, "native source drift: " + name)
        result[name] = content.decode("utf-8")
    return result, contract


def between(text, start, stop):
    generate.require(text.count(start) == 1 and text.count(stop) == 1, "source boundary not unique")
    begin, end = text.index(start), text.index(stop)
    generate.require(begin < end, "source boundaries reversed")
    return text[begin:end]


def apply_exact_patch(source, patch):
    """Apply only the pinned single-file unified patch in memory, no git mutation."""
    generate.require(digest(patch.encode()) == PATCH_SHA, "surface patch hash mismatch")
    lines, old = patch.splitlines(keepends=True), source.splitlines(keepends=True)
    target = BASE + "h1/converter/iw7/assets/xsurface.cpp"
    generate.require(lines[:2] == ["--- a/"+target+"\n", "+++ b/"+target+"\n"],
                     "patch target mismatch")
    out, cursor, index = [], 0, 2
    while index < len(lines):
        match = re.fullmatch(r"@@ -(\d+),(\d+) \+(\d+),(\d+) @@.*\n", lines[index])
        generate.require(match is not None, "unexpected patch header")
        old_start, old_count, new_start, new_count = map(int, match.groups())
        old_start -= 1; new_start -= 1
        generate.require(cursor <= old_start <= len(old), "invalid old patch position")
        out.extend(old[cursor:old_start]); cursor = old_start
        generate.require(len(out) == new_start, "invalid new patch position")
        consumed = emitted = 0; index += 1
        while index < len(lines) and not lines[index].startswith("@@"):
            row = lines[index]; index += 1
            generate.require(row[0] in " +-", "unexpected patch row")
            if row[0] in " -":
                generate.require(cursor < len(old) and old[cursor] == row[1:], "patch context mismatch")
                cursor += 1; consumed += 1
            if row[0] in " +":
                out.append(row[1:]); emitted += 1
        generate.require((consumed,emitted) == (old_count,new_count), "patch counts mismatch")
    out.extend(old[cursor:])
    result = "".join(out)
    generate.require(digest(result.encode()) == PATCHED_SHA, "patched converter hash mismatch")
    return result


def declaration(text, member_begin, parse_marker):
    members = between(text, member_begin, "\n\tpublic:")
    begin = text.index(parse_marker)
    end = text.index(";",begin)+1
    signature = text[begin:end]
    return members + "\n" + signature + "\n"


def assemble(sources, patch):
    fragments = {}
    def remember(name, text):
        fragments[name] = {"bytes":len(text.encode()),"lf_sha256":digest(text.encode())}
        return text
    h1_model = sources[BASE+"h1/assets/xmodel.cpp"]
    h1_surface = sources[BASE+"h1/assets/xsurface.cpp"]
    parsers = remember("h1_xmodel_parser_and_string_table",between(h1_model,"namespace zonetool::h1","\n\tvoid xmodel::init("))+"\n}\n"
    parsers += remember("h1_xsurface_parser_and_subdivision",between(h1_surface,"namespace zonetool::h1","\n\tvoid xsurface::init("))+"\n}\n"
    model_decl = declaration(sources[BASE+"h1/assets/xmodel.hpp"],"\t\tstd::string name_;",
                             "\t\tXModel* parse(")
    surface_decl = declaration(sources[BASE+"h1/assets/xsurface.hpp"],"\t\tstd::string name_;",
                               "\t\tXModelSurfs* parse(")
    declarations = ("// Original fields/signatures; only class envelope/access adapted.\n"
                    "namespace zonetool::h1 {\nclass xmodel { public:\n" +
                    remember("model_declaration_members",model_decl) + "};\nclass xsurface { public:\n" +
                    remember("surface_declaration_members",surface_decl) + "};\n}\n")
    macros = sources[BASE+"h1/converter/include.hpp"]
    macros = macros[macros.index("#define COPY_VALUE("):]
    model_convert = between(sources[BASE+"h1/converter/iw7/assets/xmodel.cpp"],
                            "\t\t\tzonetool::iw7::XModel* convert(","\n\t\t\tvoid dump(")
    patched = apply_exact_patch(sources[BASE+"h1/converter/iw7/assets/xsurface.cpp"],patch)
    surface_convert = between(patched,"\t\t\tvoid ValidateH1BlendVerts(","\n\t\t\tvoid dump(")
    converters = remember("converter_macros",macros)
    converters += "\nnamespace zonetool::h1::converter::iw7::xmodel {\n" + remember("model_convert",model_convert) + "\n}\n"
    converters += "namespace zonetool::h1::converter::iw7::xsurface {\n" + remember("patched_surface_convert",surface_convert) + "\n}\n"
    io = sources["src/common/utils/io.cpp"]
    # Exact reachable support. No whole utils/io.cpp copy with unrelated delete/copy helpers.
    support = "namespace utils::io {\n"
    support += remember("directory_exists",between(io,"\tbool directory_exists(","\n\tbool directory_is_empty("))
    support += remember("list_files",between(io,"\tstd::vector<std::string> list_files(","\n\tvoid copy_folder("))
    support += "\n}\n"
    fs = sources[BASE+"utils/io/filesystem.cpp"]
    support += remember("production_filesystem",fs[fs.index("namespace zonetool"):])
    memory = sources["src/common/utils/memory.cpp"]
    support += remember("production_allocator",between(memory,"namespace utils\n{","\n\tbool memory::is_set("))+"\n}\n"
    shared = sources["src/zonetool/game/shared.cpp"]
    support += "namespace zonetool {\n" + remember("production_half_and_visibility_codecs",
                between(shared,"\tnamespace half_float","\n\tnamespace Byte4")) + "\n}\n"
    for forbidden in ("db_find_x_asset", "SL_ConvertToString", "SL_GetString", "LoadLibrary", "void dump("):
        generate.require(forbidden not in parsers+converters+support, "unexpected engine/dump coupling: "+forbidden)
    return {"parser_declarations.inc":declarations.encode(), "production_parsers.inc":parsers.encode(),
            "production_converters.inc":converters.encode(), "production_support.inc":support.encode()}, fragments


def compile_plan(repo, output):
    return {"authorization":"native GO not granted by preparation", "compile_executed":False,
            "estimated_physical_gib":4,"estimated_commit_gib":6,"new_artifact_limit_mib":32,
            "estimate_is_measured":False,"compiler_processes":1,"pch":False,"mp":False,
            "planned_compile_arguments":["cl.exe","/nologo","/std:c++20","/EHsc","/W4","/MT","/Od","/Z7",
                "/I"+str(repo/"src/zonetool"),"/I"+str(repo/"src/common"),
                "/Fo"+str(output/"native_probe.obj"),"/Fe"+str(output/"native_probe.exe"),
                str(output/"native_probe.cpp"),"/link","/INCREMENTAL:NO","user32.lib"],
            "run_requires":"parent GO, byte/source revalidation, scheduler/job ownership and fresh fixture path",
            "estimated_run_physical_gib":0.25,"estimated_run_commit_gib":0.25,
            "parser_pool_bytes":1024*1024,"compile_deadline_seconds":120,"run_deadline_seconds":15}


def probe_sources(sources):
    own = Path(__file__).resolve().parent
    patch = bounded(own/"h1-xsurface-reviewed.patch").decode()
    payloads, fragments = assemble(sources,patch)
    assets = generate.build_payloads()
    inspect_pair(*assets.values())
    literal = "// Exact original positive inputs; rejects all other bytes before production parsers.\n"
    for label,data in zip(("model_bytes","surface_bytes"),assets.values()):
        literal += "static constexpr unsigned char " + label + "[] = {\n"
        literal += "\n".join("    "+",".join(f"0x{b:02x}" for b in data[i:i+24])+"," for i in range(0,len(data),24))
        literal += "\n};\n"
    payloads["fixture_bytes.inc"] = literal.encode()
    payloads["native_probe.cpp"] = bounded(own/"native_probe.cpp")
    return payloads, fragments


def verify_prepared(repo, output):
    """Read-only preflight against regenerated exact source, not just receipt hashes."""
    sources, contract = checked_sources(repo)
    payloads, fragments = probe_sources(sources)
    receipt = json.loads(bounded(output/"preparation.local.json"))
    generate.require(receipt["schema"] == "iw7.h1-native-probe-preparation/1" and
                     receipt["source_pin"] == generate.PIN, "prepared receipt identity")
    generate.require(receipt["source_lf_sha256"] == contract["lf_sha256"] and
                     receipt["fragments"] == fragments, "prepared source contract differs")
    generate.require(receipt["reviewed_patch_lf_sha256"] == PATCH_SHA and
                     receipt["patched_surface_lf_sha256"] == PATCHED_SHA and
                     receipt["plan_after_go"] == compile_plan(repo,output), "prepared plan/patch differs")
    generate.require(set(receipt["prepared_files"]) == set(payloads), "prepared file set differs")
    for name, expected in payloads.items():
        actual = raw_bounded(output/name)
        generate.require(actual == expected, "prepared source differs: " + name)
        generate.require(receipt["prepared_files"][name] == {"bytes":len(expected),"sha256":digest(expected)},
                         "prepared receipt hash differs: " + name)
    generate.require(not receipt["native_compiled"] and not receipt["native_executed"],
                     "preparation must not claim native results")
    return {"schema":"iw7.h1-native-preflight/1","prepared_files_verified":len(payloads),
            "source_files_verified":len(contract["lf_sha256"]),"native_executed":False,
            "authorization":"parent GO and live admission still required"}


def prepare(repo, output):
    sources, contract = checked_sources(repo)
    payloads, fragments = probe_sources(sources)
    generate.regular_ancestry(output)
    generate.require(output.parent.is_dir() and not output.exists(),"fresh preparation directory required")
    receipt = {"schema":"iw7.h1-native-probe-preparation/1", "source_pin":generate.PIN,
               "native_compiled":False,"native_executed":False,"dump_executed":False,
               "material_complete":False,"bone_engine_token_resolved":False,"shared_sources_modified":False,
               "declaration_adapter":"source fields/signatures retained; virtual base/engine methods omitted; string getter public",
               "source_lf_sha256":contract["lf_sha256"],"fragments":fragments,
               "reviewed_patch_lf_sha256":PATCH_SHA,"patched_surface_lf_sha256":PATCHED_SHA,
               "prepared_files":{name:{"bytes":len(data),"sha256":digest(data)} for name,data in payloads.items()},
               "plan_after_go":compile_plan(repo,output)}
    payloads["preparation.local.json"] = (json.dumps(receipt,indent=2)+"\n").encode()
    generate.require(sum(map(len,payloads.values())) < 1024*1024,"preparation exceeds one MiB")
    output.mkdir()
    for name,data in payloads.items():
        with (output/name).open("xb") as stream:
            stream.write(data)
        generate.require((output/name).read_bytes() == data,"preparation verification failed")
    return receipt


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--source-repo",type=Path,required=True)
    cli.add_argument("--output",type=Path,required=True)
    cli.add_argument("--verify",action="store_true",help="read-only prepared-source preflight")
    args = cli.parse_args()
    action = verify_prepared if args.verify else prepare
    print(json.dumps(action(args.source_repo,args.output),indent=2))

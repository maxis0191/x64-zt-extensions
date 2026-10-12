"""Bind a small review Plan to Seal C; never read large inputs or start a tool."""
import argparse
import json
import ntpath
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_contract import COMMON_MEMBERS, PROVIDERS, SCHEMA, json_bytes, key, require, sha, validate_plan

SEAL_SHA = "f52867e7c26d05466ba57d72eef601d42376c1109dfcf61f219a1a028229f388"
STATE_SHA = "fc502fb025a87278c9d9b9854b5186383d94b98add0c230ea39124404247c582"
REVIEW_SHA = "75ad217b9841856a7401785fef53b8281e3b80e26bf5525e37e8250ee2826ce9"


def small(path, maximum=1024*1024):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= maximum, "bounded source/metadata file required")
    raw = path.read_bytes()
    require(len(raw) <= maximum, "small source grew")
    return raw


def prepare(repo, python, output):
    root = repo / "runtime/content-surfaces"
    seal_path = root / "original-sound-checksum-seal-a/sealed-inputs.local.json"
    state_path = seal_path.with_name("state.local.json")
    seal_raw, state_raw = small(seal_path), small(state_path)
    require(sha(seal_raw) == SEAL_SHA and sha(state_raw) == STATE_SHA, "completed Seal C required")
    seal, state = json_bytes(seal_raw), json_bytes(state_raw)
    require(state["Status"] == "Sealed" and state["LeaseReleased"] is True and state["RetainedLeaseToken"] is None,
            "complete released input seal required")
    entries = {key(e["Path"]): e for e in seal["Inputs"]}
    require(len(entries) == 1410, "exact Seal C inventory required")
    review_root = root / "original-sound-checksum-build-review-a"
    raw = small(review_root / "command-review.local.json")
    require(sha(raw) == REVIEW_SHA, "reviewed fourteen command draft changed")
    review = json_bytes(raw)
    candidate = review["candidate_path"]
    require(not Path(candidate).exists() and not output.exists(), "fresh Plan and candidate paths required")
    source = Path(__file__).resolve().parent
    original_header = root / "original-sound-checksum-source-a/src/common/utils/bit_buffer.hpp"
    common_library = next(e["Path"] for e in seal["Inputs"] if key(e["Path"]).endswith(r"\build\bin\x64\release\common.lib"))
    native = Path(common_library).parents[4]
    common_objects = {name: str(native / "build/obj/x64/Release/common" / name) for name in sorted(COMMON_MEMBERS)}
    commands = []
    for item in review["commands"]:
        c = {k: item[k] for k in ("phase", "kind", "executable", "arguments", "working_directory")}
        if item["kind"] != "probe_run":
            c["response_path"] = item["arguments"][0][1:]
            c["response_sha256"] = item["response_sha256"]
            require(entries[key(c["response_path"])]["SHA256"] == c["response_sha256"], "response is outside Seal C")
            c["executable_sha256"] = entries[key(c["executable"])]["SHA256"]
        commands.append(c)
    providers = json_bytes(small(root / "original-sound-checksum-providers-v6/providers.local.json"))
    if not any(p["role"] == "job" for p in providers):
        job = repo / "tools-source/asset-bridge/model/BuildJob.cs"
        providers.append({"role": "job", "path": str(job), "bytes": entries[key(job)]["Bytes"], "sha256": PROVIDERS["job"]})
    compiler = commands[0]["executable"]
    vc = Path(compiler).parents[3]
    sdk = Path(r"C:\Program Files (x86)\Windows Kits\10")
    tmp = ntpath.join(candidate, "tmp")
    env = {"SystemRoot": r"C:\Windows", "WINDIR": r"C:\Windows", "SystemDrive": "C:",
           "COMSPEC": r"C:\Windows\System32\cmd.exe", "PATH": str(Path(compiler).parent) + r";C:\Windows\System32",
           "INCLUDE": ";".join([str(vc / "include"), *[str(sdk / "Include/10.0.26100.0" / part)
                                                     for part in ("ucrt", "shared", "um", "winrt", "cppwinrt")]]),
           "LIB": ";".join([str(vc / "lib/x64"), str(sdk / "Lib/10.0.26100.0/ucrt/x64"), str(sdk / "Lib/10.0.26100.0/um/x64")]),
           "CL": "", "_CL_": "", "LINK": "", "_LINK_": "", "LIBPATH": "", "PYTHONPATH": "", "PYTHONHOME": "",
           "VSLANG": "1033", "NUMBER_OF_PROCESSORS": "1", "TEMP": tmp, "TMP": tmp}
    helpers = json_bytes(small(source.parent / "sab_ff_helpers.json"))
    sources = [source / name for name in ("Build-ChecksumCandidate.ps1", "BuildCandidate.Core.ps1", "BuildReceipt.Core.ps1",
                                        "build_contract.py", "build_worker.py", "prepare_build_plan.py")]
    sources += [source.parent / name for name in ("sound_ff_phase.py", "sab_ff_helpers.json", "read_sab.py", "read_flac.py")]
    sources += [repo / relative for relative in helpers["files"]]
    source_pins = []
    for path in sorted(set(sources), key=lambda p: key(p)):
        raw = small(path)
        relative = path.relative_to(repo).as_posix()
        if relative in helpers["files"]:
            require(sha(raw.replace(b"\r\n", b"\n")) == helpers["files"][relative], "unchanged phase provider required")
        source_pins.append({"path": str(path), "bytes": len(raw), "sha256": sha(raw)})
    plan = {"schema": SCHEMA, "source_pin": "fab935826c898806855376662a8a03317b3ad8f1",
            "gsc_provider_revision": "eabe74ab65d8ce2a943b54d24b15a60749a0cf2a", "candidate": candidate, "output": candidate,
            "shared_repo": str(repo), "python": str(python), "python_sha256": entries[key(python)]["SHA256"],
            "worker": str(source / "build_worker.py"), "scheduler": str(repo / "ops/Resource-Scheduler.Core.ps1"),
            "compiler": compiler, "original_header": str(original_header),
            "patched_header": str(review_root / "patch-inputs/src/common/utils/bit_buffer.hpp"),
            "shared_original_header": str(native / "src/common/utils/bit_buffer.hpp"),
            "original_common_library": common_library, "common_objects": common_objects,
            "inventory": str(root / "original-sound-checksum-seal-plan-a/input-inventory.local.json"),
            "sealed": True, "seal": str(seal_path), "seal_sha256": SEAL_SHA,
            "seal_result": str(state_path), "seal_result_sha256": STATE_SHA,
            "source_pins": source_pins, "providers": providers, "environment": env, "commands": commands,
            "physical_bytes": 4*1024**3, "commit_bytes": 6*1024**3,
            "stop_bytes": 512*1024**2, "planning_ceiling_bytes": 768*1024**2,
            "sab_ff_authorized": False, "ready": False}
    for path in [plan["shared_original_header"], plan["original_header"], plan["patched_header"], *common_objects.values()]:
        require(key(path) in entries, "source/object binding is outside the seal")
    validate_plan(plan, sealed=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(plan, indent=2) + "\n").encode()
    with output.open("xb") as stream:
        stream.write(raw)
    return {"plan": str(output), "sha256": sha(raw), "bytes": len(raw), "commands": 14,
            "native_started": False, "candidate_created": False, "ready": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.repo.resolve(), args.python.resolve(), args.output.resolve()), indent=2))

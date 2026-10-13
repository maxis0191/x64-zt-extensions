"""Sound build consumer of the existing phase/EOF runner inside one owned job.

No admission or job owner is created here. Execution requires the separately
reviewed outer launcher; default invocation only validates the small Plan.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_contract import (COMMON_MEMBERS, ORDER, compare_archive, include_report, json_bytes, reviewed_responses, reviewed_sdk_tools,
                            key, probe_result, require, sha, validate_plan, is_flac, build_order)


def bounded(path, limit):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= limit, "bounded regular build input required")
    raw = path.read_bytes()
    require(len(raw) <= limit, "build input grew past bound")
    return raw


def write_new(path, data):
    raw = (json.dumps(data, indent=2) + "\n").encode()
    require(len(raw) <= 2 * 1024 * 1024, "bounded build receipt required")
    with Path(path).open("xb") as stream:
        stream.write(raw)
    return sha(raw)


def verify_seal(plan):
    raw = bounded(plan["seal"], 4 * 1024 * 1024)
    require(sha(raw) == plan["seal_sha256"], "input seal changed")
    seal = json_bytes(raw)
    raw = bounded(plan["seal_result"], 16384)
    require(sha(raw) == plan["seal_result_sha256"], "sealing lifecycle receipt changed")
    state = json_bytes(raw)
    require(state["Status"] == "Sealed" and state["LeaseReleased"] is True and state["RetainedLeaseToken"] is None
            and state["InputHashesVerifiedTwice"] is True and state["ManifestSHA256"] == plan["seal_sha256"],
            "complete separately admitted input seal required")
    require(seal["Schema"] == "iw7.sound-checksum-sealed-inputs/1" and seal["FileCount"] == len(seal["Inputs"]),
            "sealed inventory shape differs")
    lookup = {key(entry["Path"]): entry for entry in seal["Inputs"]}
    require(len(lookup) == len(seal["Inputs"]), "duplicate sealed input")
    return lookup


def import_runner(plan):
    # Existing adapter verifies its sixteen unchanged providers and imports the
    # existing native phase runner plus bounded SDK drain. No process starts.
    sound = Path(plan["shared_repo"]) / "tools-source/asset-bridge/surfaces/sound"
    sys.path.insert(0, str(sound))
    spec = importlib.util.spec_from_file_location("checksum_existing_sound_phase", sound / "sound_ff_phase.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    runner, drain = module.load_runner(Path(plan["shared_repo"]))
    return module, runner, drain


def verify_sdk_tools(plan, inputs):
    for pin in reviewed_sdk_tools(plan, inputs):
        raw = bounded(pin["path"], 1024 * 1024)
        require(len(raw) == pin["bytes"] and sha(raw) == pin["sha256"], "guarded SDK resource tool changed")


def native_phase(plan, command, expected, adapter, runner, drain):
    name = command["phase"]
    is_probe = command["kind"] == "probe_run"
    spec = {"schema": "iw7.material-v2-phase/1", "phase": "read" if is_probe else "compile",
            "exe": command["executable"], "sha256": expected, "arguments": command["arguments"],
            "cwd": plan["candidate"], "logs": str(Path(plan["candidate"]) / "logs" / name),
            "timeout": 30 if is_probe else 240}
    events, errors, lock = [], [], threading.Lock()
    def guarded(source, destination, failed):
        event = threading.Event()
        with lock:
            events.append(event)
        adapter.guarded_drain(drain, source, destination, failed, event, errors)
    code = runner.run(spec, guarded)
    log = Path(spec["logs"])
    receipt_raw = bounded(log / "phase.json", 16384)
    receipt = json_bytes(receipt_raw)
    require(type(code) is int and code == 0 and len(events) == 2 and all(e.is_set() for e in events) and not errors,
            "native phase did not return zero with explicit normal EOF")
    require(receipt["schema"] == "iw7.material-v2-phase-result/1" and receipt["phase"] == spec["phase"]
            and type(receipt["exit_code"]) is int and receipt["exit_code"] == 0 and receipt["failure"] is None
            and receipt["executable_sha256"] == expected and receipt["log_limit_each"] == 2 * 1024 * 1024,
            "native phase receipt differs")
    require(sha(bounded(spec["exe"], 32 * 1024 * 1024)) == expected, "native phase executable changed")
    return {"name": name, "native_phase": spec["phase"], "exit_code": 0, "normal_eof": True,
            "executable_sha256": expected, "receipt_sha256": sha(receipt_raw),
            "stdout_sha256": sha(bounded(log / "stdout.log", 2 * 1024 * 1024)),
            "stderr_sha256": sha(bounded(log / "stderr.log", 2 * 1024 * 1024))}


def run(plan, plan_sha):
    validate_plan(plan, sealed=True)
    require(os.environ.get("IW7_SOUND_BUILD_PLAN") == plan_sha, "reviewed outer sound supervisor required")
    run_id, token = os.environ.get("IW7_SOUND_BUILD_RUN_ID"), os.environ.get("IW7_SOUND_BUILD_LEASE")
    owner = os.environ.get("IW7_SOUND_BUILD_OWNER")
    require(run_id and len(run_id) == 32 and token and owner and owner.isdecimal(), "owned build generation missing")
    inputs = verify_seal(plan)
    response_sources = reviewed_responses(plan, inputs)
    include_inputs = dict(inputs)
    if is_flac(plan):
        import flac_build_profile as flac
        include_inputs.update(flac.validate_extension(plan, inputs))
        flac.verify_responses(plan, bounded, inputs)
    verify_sdk_tools(plan, inputs)
    for path in [plan["original_common_library"], plan["original_header"], plan["patched_header"],
                 plan["shared_original_header"], *plan["common_objects"].values()]:
        require(key(path) in inputs, "native source/library/object binding is outside the input seal")
    root = Path(plan["candidate"])
    require(root.is_dir() and not (root / "build-receipt.json").exists(), "fresh supervisor-created candidate required")
    for directory in ("probe", "obj", "common", "bin", "logs", "tmp"):
        (root / directory).mkdir(exist_ok=False)
    adapter, runner, drain = import_runner(plan)
    original_environment = dict(os.environ)
    receipt = {"schema": "iw7.sound-checksum-build-receipt/1", "status": "Running", "run_id": run_id,
               "root_pid": os.getpid(), "lease_owner_pid": int(owner), "lease_token": token,
               "plan_sha256": plan_sha, "seal_sha256": plan["seal_sha256"], "steps": [],
               "probes": {}, "includes": {}, "common_members": {}, "artifacts": {},
               "native_cpp_probes_verified": False, "sab_ff_tested": False, "ready": False}
    if is_flac(plan):
        receipt["schema"] = flac.RECEIPT
        receipt["flac_header_probe_verified"] = False
    try:
        # Fully declared native environment, including neutralized CL/_CL_ and
        # LINK/_LINK_. No personal variables are serialized or sent to tools.
        os.environ.clear()
        os.environ.update(plan["environment"])
        originals = {name: bounded(path, 4 * 1024 * 1024) for name, path in plan["common_objects"].items()}
        require(set(originals) == COMMON_MEMBERS, "thirteen original common objects required")
        compare_archive(bounded(plan["original_common_library"], 8 * 1024 * 1024), originals)
        for command in plan["commands"]:
            name, exe = command["phase"], Path(command["executable"])
            require(name == build_order(plan)[len(receipt["steps"])], "native step order changed")
            if command["kind"] == "probe_run":
                expected = sha(bounded(exe, 8 * 1024 * 1024))
            else:
                require(key(exe) in inputs, "unsealed native executable")
                expected = inputs[key(exe)]["SHA256"]
                require(command["arguments"] == ["@" + command["response_path"]], "literal response-file command required")
                response = bounded(command["response_path"], 128 * 1024)
                response_pin = response_sources.get(key(command["response_path"]), inputs.get(key(command["response_path"])))
                require(response_pin and len(response) == response_pin["Bytes"] and
                        sha(response) == response_pin["SHA256"] == command["response_sha256"], "response file changed")
            if name == "link-candidate":
                verify_sdk_tools(plan, inputs)
            step = native_phase(plan, command, expected, adapter, runner, drain)
            if name == "link-candidate":
                verify_sdk_tools(plan, inputs)
            receipt["steps"].append(step)
            stdout = root / "logs" / name / "stdout.log"
            if command["kind"] == "probe_run":
                receipt["probes"][name] = (flac.probe_result(bounded(stdout, 4096)) if name == "probe-flac-run"
                                           else probe_result(bounded(stdout, 4096), name == "probe-original-run"))
            if command["kind"].endswith("compile"):
                expected_header = plan["original_header"] if name == "probe-original-compile" else plan["patched_header"]
                forbidden = plan["patched_header"] if name == "probe-original-compile" else plan["original_header"]
                if name == "probe-flac-compile":
                    expected_header = str(Path(plan["flac"]["overlay"]) / "sound_flac_metadata.hpp")
                raw = bounded(stdout, 2 * 1024 * 1024)
                observed = include_report(raw, include_inputs, expected_header, forbidden)
                require(key(plan["shared_original_header"]) not in observed, "compiler used shared unpatched common header")
                if is_flac(plan) and name in ("compile-sound_bank", "probe-flac-compile"):
                    for header in (["sound_flac_metadata.hpp", "flac_dump_cases.hpp"] if name == "probe-flac-compile"
                                   else ["sound_flac_metadata.hpp"]):
                        require(key(Path(plan["flac"]["overlay"]) / header) in observed, "actual FLAC include missing")
                    if name == "probe-flac-compile":
                        require(key(plan["patched_header"]) not in observed, "unrelated checksum header in FLAC probe")
                receipt["includes"][name] = {"expected_header": expected_header, "paths": observed,
                                               "report_sha256": step["stdout_sha256"]}
            if name == "archive-common":
                replacement = dict(originals)
                replacement["bit_buffer.obj"] = bounded(root / "common/bit_buffer.obj", 4 * 1024 * 1024)
                receipt["common_members"] = compare_archive(bounded(root / "common/common.lib", 8 * 1024 * 1024), replacement)
        require(len(receipt["steps"]) == len(build_order(plan)) and len(receipt["includes"]) == (9 if is_flac(plan) else 8)
                and len(receipt["probes"]) == (3 if is_flac(plan) else 2),
                "complete native build/probe evidence required")
        artifacts = {
            "candidate_exe": "bin/zonetool-sound-md5.exe", "candidate_pdb": "bin/zonetool-sound-md5.pdb",
            "common_library": "common/common.lib", "probe_original": "probe/original.exe",
            "probe_patched": "probe/patched.exe"}
        if is_flac(plan):
            artifacts["probe_flac"] = "probe/flac-header.exe"
        for role, relative in artifacts.items():
            path = root / relative
            require(path.is_file() and path.stat().st_size <= 256 * 1024 * 1024, "bounded expected build artifact required")
            with path.open("rb") as stream:
                import hashlib
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            receipt["artifacts"][role] = {"relative": relative, "bytes": path.stat().st_size, "sha256": digest}
        receipt["native_cpp_probes_verified"] = True
        if is_flac(plan):
            receipt["flac_header_probe_verified"] = True
        receipt["status"] = "NativeBuildAndCppProbesPassed"
        write_new(root / "build-receipt.json", receipt)
        return 0
    finally:
        os.environ.clear()
        os.environ.update(original_environment)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    raw = bounded(args.plan, 2 * 1024 * 1024)
    require(sha(raw) == args.plan_sha256, "reviewed native build plan changed")
    plan = validate_plan(json_bytes(raw), sealed=True)
    if not args.execute:
        print(json.dumps({"status": "PlanOnly", "commands": len(plan["commands"]), "native_started": False}))
        return 0
    return run(plan, args.plan_sha256)


if __name__ == "__main__":
    raise SystemExit(main())

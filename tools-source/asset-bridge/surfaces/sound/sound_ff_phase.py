"""Sound-local safety adapter around the unchanged existing FF phase runner.

Never owns a lease/job: a reviewed outer supervisor must own every invocation.
No shared provider is patched. The CLI alone does not authorize native work.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import threading

from read_sab import Inputs, ZONE, plain, require, sha, strict_json

TOOL_SHA = "4740f0c22a1a7bab0b01f7a55ec0b133263ac218825ac3c0d15b9e269fe472b0"
# Qualified C: historical dump only, plus the closed standard mod build cycle.
DUMP_C_SHA = "cef411cf9b4de69be02cb4017aabd964e9143e340e211188daa6b6bab366493a"
PYTHON_SHA = "4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a"
SOURCE_IDENTITY = "utf8-crlf-to-lf-only/1"
# Current source-composition qualification; dated manifests remain immutable.
HELPER_MANIFEST = "sab_ff_helpers-20261014.json"


def source_digest(raw):
    # Only checkout newline conversion is portable. Keep BOM, whitespace,
    # final newline, lone CR and every other byte significant.
    raw.decode("utf-8", errors="strict")
    return sha(raw.replace(b"\r\n", b"\n"))


def verify_helpers(inputs, repo):
    pins = strict_json(inputs.read(Path(__file__).with_name(HELPER_MANIFEST), 16384))
    require(type(pins) is dict and set(pins) == {"schema", "normalization", "files"}
            and pins["schema"] == "iw7.original-sound-helper-sources/1" and pins["normalization"] == SOURCE_IDENTITY
            and type(pins["files"]) is dict and len(pins["files"]) == 16, "explicit helper source identity required")
    for relative, expected in pins["files"].items():
        require(not Path(relative).is_absolute() and ".." not in Path(relative).parts
                and type(expected) is str and len(expected) == 64, "bounded helper source pin required")
        # Inputs records and rechecks the exact bytes/length, never this digest.
        require(source_digest(inputs.read(repo / relative)) == expected, "shared helper changed: " + relative)


def validate(spec):
    require(type(spec) is dict and set(spec) == {"schema", "phase", "exe", "sha256", "arguments", "cwd", "logs", "timeout"},
            "exact phase fields required")
    require(spec["schema"] == "iw7.material-v2-phase/1" and spec["phase"] in ("build", "verify", "dump", "read"), "sound phase differs")
    require(type(spec["timeout"]) is int and spec["timeout"] == (30 if spec["phase"] == "read" else 240), "phase timeout differs")
    for name in ("exe", "cwd", "logs"):
        require(type(spec[name]) is str and Path(spec[name]).is_absolute(), "absolute phase path required")
        plain(spec[name])
    args = spec["arguments"]
    require(type(args) is list and all(type(a) is str and 0 < len(a) <= 1024 and not any(ord(c) < 32 for c in a) for a in args),
            "literal bounded phase arguments required")
    if spec["phase"] != "read":
        prefix = ["-headless", "-unbuffered-io", "-strict-content-sources", "-" + spec["phase"] + "zone"]
        historical = (args == prefix + [ZONE] and
                      (spec["sha256"] == TOOL_SHA or (spec["phase"] == "dump" and spec["sha256"] == DUMP_C_SHA)))
        standard = args == prefix + ["mod"] and spec["sha256"] == DUMP_C_SHA
        require((historical or standard)
                and Path(spec["exe"]).name == "zonetool.exe", "exact original zone/tool required")
    else:
        require(spec["sha256"] == PYTHON_SHA and (len(args) == 12 or
                (len(args) == 14 and args[12] == "--dump-profile" and args[13] in ("DumpOnlyC", "StandardModC")))
                and args[0] == "-B" and Path(args[1]).name == "read_sab.py"
                and args[2:12:2] == ["--source", "--banks", "--contract", "--dump", "--inventory"], "exact reader command required")
        require(all(Path(value).is_absolute() for value in [args[1], *args[3:12:2]]), "absolute reader paths required")
    return spec


def guarded_drain(drain, source, destination, failed, completion, errors):
    try:
        drain(source, destination, failed, 2 * 1024 * 1024)
    except BaseException as error:
        errors.append(type(error).__name__[:128])
        failed.set()
    else:
        if not failed.is_set():
            completion.set()


def run(spec, runner, drain):
    validate(spec)
    # Existing runner creates fresh logs and owns its normal deadline/pipe joins.
    events, errors = [], []
    lock = threading.Lock()
    def guarded(source, destination, failed):
        completed = threading.Event()
        with lock:
            events.append(completed)
        guarded_drain(drain, source, destination, failed, completed, errors)
    code = runner.run(spec, guarded)
    path = Path(spec["logs"]) / "phase.json"
    receipt_raw = Inputs().read(path, 16384)
    receipt = strict_json(receipt_raw)
    normal = len(events) == 2 and all(event.is_set() for event in events) and not errors
    valid = (type(code) is int and code == 0 and normal and receipt.get("schema") == "iw7.material-v2-phase-result/1"
             and receipt.get("phase") == spec["phase"] and type(receipt.get("exit_code")) is int and receipt["exit_code"] == 0
             and receipt.get("failure") is None and receipt.get("executable_sha256") == spec["sha256"]
             and type(receipt.get("log_limit_each")) is int and receipt["log_limit_each"] == 2 * 1024 * 1024)
    result = {"schema": "iw7.original-sound-ff-phase/1", "phase": spec["phase"], "verified": valid,
              "explicit_normal_pipe_returns": normal, "drain_exception_types": errors[:2],
              "existing_runner_receipt_sha256": sha(receipt_raw), "ready": False, "playback_verified": False}
    with (path.parent / "sound-phase.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2); stream.write("\n")
    return 0 if valid else 1


def load_runner(repo):
    repo = plain(repo)
    inputs = Inputs()
    verify_helpers(inputs, repo)
    sys.path.insert(0, str(repo / "tools-source/asset-bridge/surfaces"))
    spec = importlib.util.spec_from_file_location("pinned_existing_ff_phase", repo / "tools-source/asset-bridge/surfaces/material_v2_phase.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Load the already verified unchanged SDK implementation locally. Its own
    # standalone loader has an LF-only byte pin, unsuitable for CRLF checkouts.
    drain_spec = importlib.util.spec_from_file_location("pinned_sound_existing_drain", repo / "sdk/modding/beacon_tool_phase.py")
    drain_module = importlib.util.module_from_spec(drain_spec)
    drain_spec.loader.exec_module(drain_module)
    inputs.recheck()
    return module, drain_module.copy_bounded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--spec-sha256", required=True)
    parser.add_argument("--shared-repo", required=True, type=Path)
    args = parser.parse_args()
    raw = Inputs().read(args.spec, 16384)
    require(sha(raw) == args.spec_sha256.lower(), "reviewed sound spec changed")
    spec = validate(strict_json(raw))
    runner, drain = load_runner(args.shared_repo)
    return run(spec, runner, drain)


if __name__ == "__main__":
    raise SystemExit(main())

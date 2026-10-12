"""Bounded native phase inside the existing shared BuildJob; never owns a lease.

The PowerShell adapter creates the exact spec, hashes it and owns all descendants.
Log draining is reused from the pinned SDK adapter, not reimplemented here.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import threading
import time

from inspect_content import Inputs, no_links, parse_json, require
from prepare_material_v2 import digest

SDK_PHASE_SHA = "a2ab493cf551a43eea3797e5e8437e41aa8f0246d770838956d8984b68c4701d"


def validate_spec(spec):
    require(spec.get("schema") == "iw7.material-v2-phase/1", "phase spec schema differs")
    require(spec.get("phase") in ("compile", "write", "build", "verify", "dump", "read"), "unknown phase")
    require(type(spec.get("timeout")) is int and spec["timeout"] == (30 if spec["phase"] in ("write", "read") else 240),
            "phase time bound differs")
    require(isinstance(spec.get("arguments"), list) and 1 <= len(spec["arguments"]) <= 40 and
            all(isinstance(a, str) and 0 < len(a) <= 1024 and not any(ord(c) < 32 for c in a)
                for a in spec["arguments"]), "bounded literal arguments required")
    for name in ("exe", "cwd", "logs"):
        require(isinstance(spec.get(name), str) and Path(spec[name]).is_absolute(), "absolute phase paths required")
        no_links(Path(spec[name]))
    require(isinstance(spec.get("sha256"), str) and len(spec["sha256"]) == 64, "executable hash required")
    return spec


def load_drain(path):
    path = no_links(Path(path).absolute())
    raw = Inputs(path.parent).read(path.name, 16384)
    require(digest(raw) == SDK_PHASE_SHA, "shared SDK drain changed")
    module_spec = importlib.util.spec_from_file_location("shared_beacon_drain", path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module.copy_bounded


def run(spec, drain):
    validate_spec(spec)
    exe = no_links(Path(spec["exe"]))
    require(exe.is_file() and exe.stat().st_size <= 32 * 1024 * 1024, "bounded native executable required")
    require(digest(exe.read_bytes()) == spec["sha256"].lower(), "phase executable changed")
    logs = Path(spec["logs"])
    require(not logs.exists(), "fresh phase logs required")
    logs.mkdir()
    exceeded = threading.Event()
    handles, workers = [], []
    env = os.environ.copy()
    if spec["phase"] == "compile":
        env["PATH"] = str(exe.parent) + os.pathsep + env.get("PATH", "")
    # No shell. Descendants inherit the parent's existing non-breakaway job.
    process = subprocess.Popen([str(exe), *spec["arguments"]], cwd=spec["cwd"], env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               creationflags=0x08000000 if os.name == "nt" else 0)
    for name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
        handle = (logs / (name + ".log")).open("xb")
        handles.append(handle)
        worker = threading.Thread(target=drain, args=(stream, handle, exceeded), daemon=True)
        worker.start()
        workers.append(worker)
    failure = None
    deadline = time.monotonic() + spec["timeout"]
    while process.poll() is None:
        if exceeded.is_set() or time.monotonic() >= deadline:
            failure = "log bound/output error" if exceeded.is_set() else "phase timeout"
            break
        time.sleep(.05)
    if failure is None:
        for worker in workers:
            worker.join(2)
        if exceeded.is_set() or any(w.is_alive() for w in workers):
            failure = "drain failed or inherited pipe remains open"
    result = {"schema": "iw7.material-v2-phase-result/1", "phase": spec["phase"], "pid": process.pid,
              "exit_code": process.poll(), "failure": failure, "executable_sha256": spec["sha256"],
              "log_limit_each": 2 * 1024 * 1024, "ownership": "outer shared Windows job"}
    (logs / "phase.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if failure:
        for handle, worker in zip(handles, workers):
            if not worker.is_alive():
                handle.close()
        os._exit(2)  # Parent stops its original job; never kill/reidentify by PID.
    for handle in handles:
        handle.close()
    return 0 if process.returncode == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--spec-sha256", required=True)
    parser.add_argument("--sdk-phase", required=True, type=Path)
    args = parser.parse_args()
    path = no_links(args.spec.absolute())
    raw = Inputs(path.parent).read(path.name, 32768)
    require(digest(raw) == args.spec_sha256.lower(), "phase spec changed")
    raise SystemExit(run(parse_json(raw), load_drain(args.sdk_phase)))

"""Eight fixed rig-chain phases inside the coordinator's original Windows job.

No lease or process-tree owner here. Reuse the pinned Beacon bounded drain.
The parent owns all descendants and interprets the exact phase receipt.
"""
import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time

PHASES = {"compile": 120, "emit-first": 30, "emit-second": 30, "read-native": 30,
          "build": 240, "verify": 240, "dump": 240, "read-ff": 30}
DRAIN_SHA = "a2ab493cf551a43eea3797e5e8437e41aa8f0246d770838956d8984b68c4701d"
ENV_KEYS = {"SystemRoot", "WINDIR", "PATH", "TEMP", "TMP", "INCLUDE", "LIB",
            "PYTHONNOUSERSITE", "PYTHONDONTWRITEBYTECODE"}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def no_links(path):
    require(path.is_absolute() and ".." not in path.parts, "absolute canonical phase path required")
    for current in (path, *path.parents):
        require(not current.is_symlink() and not current.is_junction(), "reparse phase path refused")
    return path


def bounded(path, cap):
    no_links(path)
    with path.open("rb") as stream:
        data = stream.read(cap + 1)
    require(0 < len(data) <= cap, "phase input exceeds limit")
    return data


def parse(data):
    def unique(pairs):
        result = {}
        for k, v in pairs:
            require(k not in result, "duplicate phase key")
            result[k] = v
        return result
    return json.loads(data, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite phase value")))


def validate(spec):
    require(isinstance(spec, dict) and set(spec) == {"schema", "phase", "exe", "sha256", "arguments", "cwd", "logs", "timeout", "environment"}, "exact rig phase fields required")
    require(spec["schema"] == "iw7.rig-chain-phase-spec/1" and spec["phase"] in PHASES, "fixed rig phase required")
    require(type(spec["timeout"]) is int and spec["timeout"] == PHASES[spec["phase"]], "fixed rig timeout required")
    require(isinstance(spec["sha256"], str) and re.fullmatch("[a-fA-F0-9]{64}", spec["sha256"]), "phase executable hash required")
    require(isinstance(spec["arguments"], list) and 1 <= len(spec["arguments"]) <= 64 and
            all(isinstance(a, str) and 0 < len(a) <= 32768 and not any(ord(c) < 32 for c in a) for a in spec["arguments"]), "bounded literal phase arguments required")
    for key in ("exe", "cwd", "logs"):
        require(isinstance(spec[key], str), "string phase path required")
        no_links(Path(spec[key]))
    env = spec["environment"]
    require(isinstance(env, dict) and set(env) == ENV_KEYS, "exact explicit child environment required")
    require(all(isinstance(v, str) and len(v) <= 32768 and not any(ord(c) < 32 for c in v) for v in env.values()), "bounded child environment values required")
    require(env["PYTHONNOUSERSITE"] == env["PYTHONDONTWRITEBYTECODE"] == "1", "isolated Python environment required")
    require(env["SystemRoot"] == env["WINDIR"] and env["TEMP"] == env["TMP"], "fixed system and temporary roots required")
    for key in ("SystemRoot", "WINDIR", "TEMP", "TMP"):
        no_links(Path(env[key]))
    require(bool(env["PATH"]) and bool(env["INCLUDE"]) and bool(env["LIB"]), "frozen toolchain search paths required")
    return spec


def assert_outer_job():
    require(os.name == "nt", "Windows job execution required")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.IsProcessInJob.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
    member = ctypes.c_int()
    require(kernel.IsProcessInJob(kernel.GetCurrentProcess(), None, ctypes.byref(member)) and member.value,
            "phase root must already belong to an outer Windows job")


def load_drain(path):
    require(hashlib.sha256(bounded(path, 65536)).hexdigest() == DRAIN_SHA, "pinned shared drain differs")
    spec = importlib.util.spec_from_file_location("_rig_beacon_drain", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.copy_bounded


def run(spec, spec_sha256, drain, *, ensure_job=assert_outer_job, popen=subprocess.Popen,
        clock=time.monotonic, sleep=time.sleep):
    validate(spec)
    ensure_job()
    exe = Path(spec["exe"])
    require(hashlib.sha256(bounded(exe, 32 * 1024**2)).hexdigest() == spec["sha256"].lower(), "phase executable changed")
    logs = no_links(Path(spec["logs"]))
    require(not logs.exists(), "fresh phase log directory required")
    logs.mkdir()
    exceeded = threading.Event()
    handles, workers = [], []
    # Explicit dictionary, never os.environ mutation/inheritance. CL, _CL_,
    # PYTHONPATH, PYTHONHOME and unrelated tool variables cannot inject options.
    process = popen([str(exe), *spec["arguments"]], cwd=spec["cwd"], env=dict(spec["environment"]),
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    creationflags=0x08000000 if os.name == "nt" else 0)
    for name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
        handle = (logs / (name + ".log")).open("xb")
        handles.append(handle)
        worker = threading.Thread(target=drain, args=(stream, handle, exceeded), daemon=True)
        worker.start()
        workers.append(worker)
    failure = None
    deadline = clock() + spec["timeout"]
    while process.poll() is None:
        if exceeded.is_set() or clock() >= deadline:
            failure = "log bound/output error" if exceeded.is_set() else "phase timeout"
            break
        sleep(.05)
    if failure is None:
        for worker in workers:
            worker.join(2)
        if exceeded.is_set() or any(w.is_alive() for w in workers):
            failure = "drain failed or inherited pipe remains open"
    receipt = {"schema": "iw7.rig-chain-phase-result/1", "phase": spec["phase"], "spec_sha256": spec_sha256,
               "pid": process.pid, "exit_code": process.poll(), "failure": failure,
               "executable_sha256": spec["sha256"], "log_limit_each": 2 * 1024**2,
               "ownership": "outer original Windows job"}
    with (logs / "phase.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    for handle, worker in zip(handles, workers):
        if not worker.is_alive():
            handle.close()
    return (2 if failure else 0 if process.returncode == 0 else 1), receipt


def main(argv=None, *, runner=run, drain_loader=load_drain, hard_exit=os._exit):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--spec-sha256", required=True)
    parser.add_argument("--sdk-phase", required=True, type=Path)
    args = parser.parse_args(argv)
    spec = None
    try:
        raw = bounded(args.spec, 65536)
        require(hashlib.sha256(raw).hexdigest() == args.spec_sha256.lower(), "phase spec changed")
        spec = parse(raw)
        code, receipt = runner(spec, args.spec_sha256.lower(), drain_loader(args.sdk_phase))
    except Exception as error:
        # Errors before child/log creation still need a durable, distinct record.
        # This sibling of the bound spec is fresh and never overwrites phase.json
        # or an existing log directory. The outer owner validates PID/spec binding.
        failure = {'schema': 'iw7.rig-chain-launch-error/1',
                   'phase': spec.get('phase') if isinstance(spec, dict) else None,
                   'spec_sha256': args.spec_sha256.lower(), 'root_pid': os.getpid(),
                   'error_type': type(error).__name__[:128], 'error': str(error)[:8192]}
        try:
            target = no_links(args.spec.with_suffix('.launch-error.json'))
            with target.open('x', encoding='utf-8', newline='\n') as stream:
                json.dump(failure, stream, indent=2, ensure_ascii=False)
                stream.write('\n')
        except (OSError, ValueError) as publication_error:
            print('Could not retain launch error: ' + str(publication_error), file=sys.stderr, flush=True)
        print('Rig phase bootstrap failed: ' + str(error), file=sys.stderr, flush=True)
        return 2
    if receipt["failure"]:
        hard_exit(code)  # Parent closes its original job; no PID-based kill here.
    return code


if __name__ == "__main__":
    raise SystemExit(main())

"""Concrete future CDB pipe transport for the owned Python fixture only.

Imports/tests do not launch anything. Retail execution has no implementation.
The outer original BuildJob must own this root, CDB and the fixture, enforce its
independent deadline and close the complete job on every terminal state.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capture

CDB_SHA = "5f54abafca3ae5638bbf807d402fabb350a64575c1dfa9fbfc7f5732df5bee67"
PROMPT = re.compile(rb"(?:^|[\r\n])[0-9]+:[0-9a-fA-F]{3}>[ \t]*$")


def digest(path):
    value = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            value.update(chunk)
    return value.hexdigest()


def atomic_json(path, value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii")
    capture.require(len(raw) <= 16384, "bounded transport state required")
    temporary = path.with_suffix(".tmp")
    with temporary.open("wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def error_description(error):
    # Preserve ordinary exception text without calling custom __str__/__repr__.
    parts = [part[:512] for part in BaseException.args.__get__(error)[:2] if type(part) is str]
    return (type(error).__name__ + (": " + "; ".join(parts) if parts else ""))[:512]


def failed_event(spec, error, root_pid, *, debugger_pid=None, workers=None, phase="bootstrap", byte_count=0, pipe_failure=None, job_evidence=None):
    immediate = {"Type": type(error).__name__, "Message": error_description(error)}
    initial = immediate
    for item in job_evidence or ():
        query = item.get("query", {})
        if query.get("ApiSucceeded") is False or (query.get("ApiSucceeded") is True and query.get("InAnyJob") is False):
            initial = {"Type": "IsProcessInJobAPIFailure" if query["ApiSucceeded"] is False else "IsProcessInJobNonmember",
                       "Role": item["role"], "Query": query}
            break
    return {"schema": "iw7.rig-watch-transport/1", "Nonce": spec["nonce"], "FixtureOnly": True,
            "RootPID": root_pid, "DebuggerPID": debugger_pid, "Status": "Failed", "Healthy": False,
            "Bytes": byte_count, "Workers": workers, "PipeFailure": pipe_failure,
            "Phase": phase, "Error": initial["Type"] + ": " + error_description(error),
            "InitialFailure": initial, "ImmediateFailure": immediate,
            "JobEvidence": job_evidence}


def retain_failure(root, spec, error, root_pid, **details):
    """Keep the first bound failure; a bootstrap wrapper must not replace it."""
    path = root / "transport.json"
    if path.exists():
        previous = json.loads(capture.bounded(path, 16384), object_pairs_hook=capture.unique_pairs)
        if (previous.get("schema") == "iw7.rig-watch-transport/1" and previous.get("Status") == "Failed" and
                previous.get("Nonce") == spec["nonce"] and previous.get("RootPID") == root_pid and
                previous.get("FixtureOnly") is True):
            return previous
    evidence = []
    for name, role in (("transport-job.json", "transport"), ("fixture-job.json", "fixture")):
        candidate = root / name
        if candidate.exists():
            item = json.loads(capture.bounded(candidate, 4096), object_pairs_hook=capture.unique_pairs)
            capture.require(item.get("schema") == "iw7.rig-watch-self-job/1" and item.get("nonce") == spec["nonce"] and
                            item.get("role") == role, "foreign job evidence refused")
            evidence.append(item)
    event = failed_event(spec, error, root_pid, job_evidence=evidence, **details)
    atomic_json(path, event)
    return event


def fixture_command(spec, root):
    capture.require(spec.get("mode") == "fixture", "retail mode unavailable: locator binding required")
    return [spec["cdb"], "-sins", "-y", str(root / "symbols"), "-netsyms:no", "-nosqm", "-noshell",
            "-cf", str(root / "startup.cdb"), spec["python"], "-I", "-B",
            str(Path(__file__).with_name("debug_fixture.py")), "--manifest", str(root / "fixture.json"),
            "--nonce", spec["nonce"]]


class PipeIO:
    """Blocking pipe I/O stays on daemon workers; the controller never waits on it."""
    def __init__(self, process):
        self.process = process
        self.events = queue.Queue(maxsize=64)
        self.commands = queue.Queue(maxsize=4)
        self.failure = threading.Event()
        self.error = None
        self.raw = {"stdout": bytearray(), "stderr": bytearray()}
        self.eof = set()
        self.worker_done = {name: threading.Event() for name in ("stdout", "stderr", "stdin")}
        self.worker_outcome = {name: "running" for name in self.worker_done}
        for name in ("stdout", "stderr"):
            threading.Thread(target=self.drain, args=(name, getattr(process, name)), daemon=True).start()
        threading.Thread(target=self.write, daemon=True).start()

    def fail(self, reason):
        # Signal first. Never invoke exception __str__/__repr__ (or a str
        # subclass hook) while reporting the failure that must stop acceptance.
        self.failure.set()
        self.error = reason[:128] if type(reason) is str else "pipe worker failure"

    def drain(self, name, stream):
        try:
            while True:
                chunk = stream.read1(4096)
                self.events.put_nowait((name, chunk))
                if not chunk:
                    self.worker_outcome[name] = "eof"
                    return
        except BaseException:
            self.worker_outcome[name] = "failed"
            self.fail("pipe drain failed")
        finally:
            self.worker_done[name].set()

    def write(self):
        try:
            while True:
                command = self.commands.get()
                self.process.stdin.write(command)
                self.process.stdin.flush()
        except BaseException:
            self.worker_outcome["stdin"] = "failed"
            self.fail("pipe writer failed")
        finally:
            self.worker_done["stdin"].set()

    def worker_status(self):
        return {name: {"Terminated": done.is_set(), "Outcome": self.worker_outcome[name]}
                for name, done in self.worker_done.items()}

    def assert_healthy(self):
        capture.require(not self.failure.is_set(), "pipe failure")
        capture.require(not any(done.is_set() for done in self.worker_done.values()),
                        "pipe worker terminated before owned closure")
        capture.require(not self.eof, "debugger pipe EOF before owned closure")
        capture.require(self.process.poll() is None, "debugger exited before owned closure")

    def send(self, command):
        raw = command.encode("ascii")
        capture.require(0 < len(raw) <= 8192 and raw.endswith(b"\n"), "bounded complete CDB command required")
        try:
            self.commands.put_nowait(raw)
        except queue.Full:
            self.fail("stdin queue overflow")

    def pump(self):
        self.assert_healthy()
        # At most 64 queued chunks per poll, never an unbounded draining loop.
        for _ in range(64):
            try:
                name, raw = self.events.get_nowait()
            except queue.Empty:
                break
            if not raw:
                self.eof.add(name)
            elif sum(map(len, self.raw.values())) + len(raw) > capture.MAX_LOG:
                self.fail("combined stdout/stderr cap exceeded")
            else:
                self.raw[name].extend(raw)
        self.assert_healthy()
        return bytes(self.raw["stdout"])


def has_prompt(raw, after=0):
    return PROMPT.search(raw[after:]) is not None


def marker(raw, nonce, word):
    expression = rb"(?m)^RIG58 " + nonce.encode() + b" " + word.encode() + rb"\r?$"
    matches = list(re.finditer(expression, raw))
    capture.require(len(matches) <= 1, "duplicate protocol marker")
    return matches[0].end() if matches else None


def make_fixture_context(spec, manifest, probe):
    capture.require(manifest.get("schema") == "iw7.rig-watch-fixture/1" and
                    manifest.get("nonce") == spec["nonce"] and manifest.get("pid") == probe["pid"],
                    "stopped fixture PID/nonce differs")
    proof = hashlib.sha256(json.dumps([manifest, probe], sort_keys=True).encode()).hexdigest()
    result = {"schema": capture.FIXTURE_SCHEMA, "profile": "first", "run_id": spec["nonce"],
              "tool_sha256": spec["python_sha256"], "fixture_source_sha256": spec["fixture_sha256"],
              "ff_sha256": None, "pid": manifest["pid"], "creation_utc": manifest["creation_utc"],
              "image_path": spec["python"], "xsurface": manifest["xsurface"], "xmodelsurfs": manifest["xmodelsurfs"],
              "arm_rip": hex(probe["rip"]), "arm_code_hex": probe["code"].to_bytes(8, "little").hex(),
              "review": {"phase": "fixture-after-allocation-before-write", "evidence_sha256": proof,
                         "mapping_verified": True, "stopped_identity_verified": True,
                         "launch_job_owned": True, "breakpoint_table_empty": True,
                         "all_threads_stopped": True, "deadline_armed": True,
                         "admission_lease_id": spec["lease_token"]}}
    capture.validate(result)
    return result


class FixtureProtocol:
    """Concrete command sequencing; filesystem/pipe operations are injectable in tests."""
    def __init__(self, spec, root, io, read_json=None, write_json=atomic_json, write_bytes=None):
        self.spec, self.root, self.io = spec, root, io
        self.read_json = read_json or (lambda path: json.loads(capture.bounded(path, 16384)))
        self.write_json = write_json
        self.write_bytes = write_bytes or (lambda path, data: path.write_bytes(data))
        self.phase = "initial"
        self.cursor = 0
        self.target = None
        self.context = None
        self.witness = None
        self.continued = False
        self.state = {"schema": "iw7.rig-watch-transport/1", "Nonce": spec["nonce"], "Healthy": True,
                      "Status": "Loading", "Bytes": 0, "IdentityChecked": False,
                      "BreakpointChecked": False, "RetailRuntimeReady": False, "FixtureOnly": True}

    def step(self, raw, continuation=None):
        nonce = self.spec["nonce"]
        capture.require(len(raw) <= capture.MAX_LOG, "stdout cap")
        capture.require(not re.search(rb"(?m)^RIG58_REFUSED_", raw), "CDB guard refused")
        # Refuse debugger command errors, including a failed ba/r/.if parse.
        capture.require(not re.search(rb"(?im)^(?:syntax error|bad register|couldn't resolve|unable to insert breakpoint)", raw),
                        "CDB command error")
        self.state["Bytes"] = len(raw)
        if self.phase == "initial" and has_prompt(raw):
            self.cursor = len(raw)
            self.io.send("bl\n")
            self.phase = "empty"
        elif self.phase == "empty" and has_prompt(raw, self.cursor):
            capture.require(not re.search(rb"(?m)^\s*[0-9]+\s+[ed]\s+", raw[self.cursor:]), "fresh empty breakpoint table required")
            self.cursor = len(raw)
            self.io.send("g\n")  # Fixture-only startup; retail startup is unavailable.
            self.phase = "fixture"
        elif self.phase == "fixture" and has_prompt(raw, self.cursor):
            self.target = self.read_json(self.root / "fixture.json")
            self.cursor = len(raw)
            self.io.send('.if ($vvalid(@rip,8)) { .printf "RIG58_PROBE ' + nonce +
                         ' pid=%I64x rip=%I64x code=%I64x\\n", @$tpid, @rip, qwo(@rip) } '
                         '.else { .echo RIG58_REFUSED_PROBE_RANGE }\n')
            self.phase = "probe"
        elif self.phase == "probe" and has_prompt(raw, self.cursor):
            expression = rb"(?m)^RIG58_PROBE " + nonce.encode() + rb" pid=([0-9a-fA-F]+) rip=([0-9a-fA-F]+) code=([0-9a-fA-F]+)\r?$"
            matches = list(re.finditer(expression, raw[self.cursor:]))
            capture.require(len(matches) == 1, "exact stopped-context probe required")
            probe = dict(zip(("pid", "rip", "code"), (int(x, 16) for x in matches[0].groups())))
            self.context = make_fixture_context(self.spec, self.target, probe)
            self.write_json(self.root / "context.json", self.context)
            commands = capture.emit(self.context)
            self.cursor = len(raw)
            self.io.send(commands["arm.cdb"])
            self.phase = "arm"
        elif self.phase == "arm":
            attempted = marker(raw, nonce, "ARM_ATTEMPT_STOPPED")
            if attempted is not None and has_prompt(raw, attempted):
                capture.require(marker(raw, nonce, "BP_PRESENT") is not None, "actual breakpoint address was not confirmed")
                self.state.update(Status="ArmedStopped", IdentityChecked=True, BreakpointChecked=True,
                                  Target=self.target, ContextSHA256=hashlib.sha256(json.dumps(self.context, sort_keys=True).encode()).hexdigest())
                self.phase = "armed"
        elif self.phase == "armed" and continuation is not None:
            capture.require(continuation == {"Nonce": nonce, "Command": "continue-once"}, "invalid continuation request")
            capture.require(not self.continued, "duplicate continuation")
            self.cursor = len(raw)
            self.io.send("g\n")
            self.continued = True
            self.state["Status"] = "Running"
            self.phase = "write"
        elif self.phase == "write":
            stop = marker(raw, nonce, "STOP")
            if stop is not None and has_prompt(raw, stop):
                self.witness = capture.parse_capture(self.context, raw)
                capture.require(self.witness["fixture_only"] and
                                self.witness["new_category"] == "equals_current_name_address", "known fixture write not observed")
                self.write_bytes(self.root / "sealed.log", raw)
                self.write_json(self.root / "witness.json", self.witness)
                self.state.update(Status="CaptureStopped", SealedSHA256=hashlib.sha256(raw).hexdigest(),
                                  SealedBytes=len(raw), WitnessParsed=True)
                self.phase = "sealed"
        return dict(self.state)


def query_job_membership(kernel, ffi=ctypes):
    """Self-query only. NULL JobHandle means any job, never our specific owner."""
    kernel.GetCurrentProcess.argtypes = []
    kernel.GetCurrentProcess.restype = ffi.c_void_p
    kernel.IsProcessInJob.argtypes = [ffi.c_void_p, ffi.c_void_p, ffi.POINTER(ffi.c_int)]
    kernel.IsProcessInJob.restype = ffi.c_int
    handle_bytes, bool_bytes = ffi.sizeof(ffi.c_void_p), ffi.sizeof(ffi.c_int)
    if handle_bytes != 8 or bool_bytes != 4:
        raise RuntimeError("Explicit Windows x64 HANDLE/BOOL layout required")
    member = ffi.c_int(0)
    process = kernel.GetCurrentProcess()
    ffi.set_last_error(0)
    result = int(kernel.IsProcessInJob(process, None, ffi.byref(member)))
    last_error = int(ffi.get_last_error())
    return {"ApiReturn": result, "ApiSucceeded": result != 0, "LastError": last_error,
            "LastErrorMeaningful": result == 0, "MemberValue": int(member.value),
            "MemberValid": result != 0, "InAnyJob": bool(member.value) if result else None,
            "HandleBytes": handle_bytes, "BOOLBytes": bool_bytes, "SpecificOriginalJobProven": False}


def assert_job(spec, root):
    capture.require(os.name == "nt", "Windows original-job host required")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    job = query_job_membership(kernel)
    atomic_json(root / "transport-job.json", {"schema": "iw7.rig-watch-self-job/1", "nonce": spec["nonce"],
                                             "pid": os.getpid(), "role": "transport", "query": job})
    capture.require(job["ApiSucceeded"] and job["InAnyJob"] is True,
                    f"Outer job guard refused: ApiReturn={job['ApiReturn']} LastError={job['LastError']} "
                    f"MemberValue={job['MemberValue']} MemberValid={job['MemberValid']}")


def run(spec, root):
    capture.require(spec.get("mode") == "fixture", "retail mode remains unavailable")
    capture.require(re.fullmatch(r"[a-f0-9]{32}", spec["nonce"]), "nonce")
    capture.require(re.fullmatch(r"[A-Za-z0-9_-]{8,128}", spec["lease_token"]), "lease token")
    assert_job(spec, root)
    capture.require(spec["cdb_sha256"] == CDB_SHA and digest(spec["cdb"]) == CDB_SHA, "CDB pin changed")
    capture.require(digest(spec["python"]) == spec["python_sha256"] and
                    digest(Path(__file__).with_name("debug_fixture.py")) == spec["fixture_sha256"], "fixture/python pins changed")
    capture.require(Path(spec["python"]).resolve() == Path(sys.executable).resolve(), "same admitted Python required")
    (root / "symbols").mkdir(exist_ok=False)
    (root / "startup.cdb").write_text(".expr /s masm\n", encoding="ascii")
    env = dict(os.environ)
    for key in ("_NT_SYMBOL_PATH", "_NT_ALT_SYMBOL_PATH", "_NT_SOURCE_PATH", "_NT_DEBUGGER_EXTENSION_PATH"):
        env.pop(key, None)
    process = subprocess.Popen(fixture_command(spec, root), cwd=root, env=env, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, close_fds=True,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    io = PipeIO(process)
    protocol = FixtureProtocol(spec, root, io)
    deadline = time.monotonic() + 240
    last = None
    last_flush = 0.0
    try:
        while time.monotonic() < deadline:
            raw = io.pump()
            control_path = root / "continue.json"
            continuation = None
            if protocol.phase == "armed" and control_path.exists():
                continuation = json.loads(capture.bounded(control_path, 1024))
            state = protocol.step(raw, continuation)
            io.assert_healthy()
            state.update(DebuggerPID=process.pid, RootPID=os.getpid(), Workers=io.worker_status())
            if state != last and (time.monotonic() - last_flush >= 0.1 or state["Status"] in ("ArmedStopped", "CaptureStopped")):
                for name, data in io.raw.items():
                    (root / (name + ".raw.log")).write_bytes(data)
                io.assert_healthy()
                atomic_json(root / "transport.json", state)
                io.assert_healthy()
                last = state
                last_flush = time.monotonic()
            time.sleep(0.025)
        raise ValueError("transport local deadline; original owner must close job")
    except Exception as exc:
        retain_failure(root, spec, exc, os.getpid(), debugger_pid=process.pid, workers=io.worker_status(),
                       phase=protocol.phase, byte_count=sum(map(len, io.raw.values())), pipe_failure=io.error)
        raise
    finally:
        # No kill(), detach, process-name enumeration or private replacement job.
        # The independent original-job deadline/parent owns terminal recovery.
        for name, data in io.raw.items():
            (root / (name + ".raw.log")).write_bytes(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--spec-sha256", required=True)
    parser.add_argument("--run-fixture", action="store_true")
    args = parser.parse_args()
    spec = None
    try:
        raw = capture.bounded(args.spec, 16384)
        capture.require(hashlib.sha256(raw).hexdigest() == args.spec_sha256, "bound spec required")
        spec = json.loads(raw, object_pairs_hook=capture.unique_pairs)
        if not args.run_fixture:
            print(json.dumps({"mode": spec.get("mode"), "native_go": False, "runtime_ready": False}))
            return
        run(spec, args.spec.parent)
    except Exception as exc:
        if args.run_fixture and isinstance(spec, dict) and spec.get("mode") == "fixture":
            try:
                retain_failure(args.spec.parent, spec, exc, os.getpid())
                atomic_json(args.spec.parent / "bootstrap-error.json", {
                    "schema": "iw7.rig-watch-bootstrap-error/1", "Nonce": spec.get("nonce"),
                    "RootPID": os.getpid(), "FixtureOnly": True, "Error": error_description(exc)})
            except (OSError, ValueError):
                pass  # Original root exit remains a failure, even if evidence I/O fails.
        parser.exit(2, "refused: " + error_description(exc) + "\n")


if __name__ == "__main__":
    main()

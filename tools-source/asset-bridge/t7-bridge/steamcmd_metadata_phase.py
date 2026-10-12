"""Fixed SteamCMD metadata query inside the coordinator's existing NativeJob.

The outer job owns admission, process identities, deadline enforcement and tree
closure. This adapter permits SteamCMD's self-update by keeping Python as the
pinned job root. It cannot download an app/depot or log into a personal account.
No successful exit here establishes application identity or asset availability.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import threading
import time

BOOTSTRAP_SHA256 = "fc103a323d70caaac475ae1cfcacfd8eec4c6b1e130005c4793f2013b4b019f8"
DISK_LIMIT = 512 * 1024 * 1024
METADATA_RESERVE = 1024 * 1024
LOG_LIMIT = 2 * 1024 * 1024
DEADLINE_SECONDS = 180
ARGUMENTS = ("+@ShutdownOnFailedCommand", "1", "+@NoPromptForPassword", "1",
             "+login", "anonymous", "+app_info_update", "1",
             "+app_info_print", "545990", "+quit")


def plain_directory(path):
    if not path.is_absolute() or path != path.resolve(strict=True) or not path.is_dir():
        raise ValueError("Existing canonical absolute directory required")
    for parent in (path, *path.parents):
        if parent.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError("Reparse directory refused")


def tree_bytes(root):
    """Bounded metadata walk; no payload reads and no reparse traversal."""
    pending = [root]
    count = total = 0
    while pending:
        directory = pending.pop()
        try:
            entries = os.scandir(directory)
        except FileNotFoundError:
            if directory == root:
                raise
            continue  # Updater removed a private temporary directory.
        with entries:
            for entry in entries:
                count += 1
                if count > 20000:
                    raise ValueError("Tool tree entry bound exceeded")
                try:
                    info = entry.stat(follow_symlinks=False)
                except FileNotFoundError:
                    continue  # Expected self-update rename/removal race.
                if info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                    raise ValueError("Reparse entry in tool tree")
                if stat.S_ISDIR(info.st_mode):
                    pending.append(Path(entry.path))
                elif stat.S_ISREG(info.st_mode):
                    total += info.st_size
                    if total > DISK_LIMIT - METADATA_RESERVE:
                        raise ValueError("Tool/cache/log total exceeds 512 MiB observation limit")
                else:
                    raise ValueError("Unsupported entry in tool tree")
    return total


def output_copy_function():
    # Reuse the existing reviewed bounded-pipe helper, not another subprocess
    # supervisor. The coordinator must pin this dependency in its launch plan.
    repo = Path(__file__).resolve().parents[3]
    path = repo / "sdk" / "modding" / "beacon_tool_phase.py"
    spec = importlib.util.spec_from_file_location("existing_beacon_output", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.copy_bounded


def guarded_copy(copy_bounded, source, destination, exceeded):
    # Thread failures do not propagate to the caller. Every failure, including
    # SystemExit, must mark the phase unsuccessful before this worker ends.
    try:
        copy_bounded(source, destination, exceeded, LOG_LIMIT)
    except BaseException:
        exceeded.set()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool-root", required=True)
    args = parser.parse_args()
    if os.name != "nt":
        raise ValueError("Windows-only coordinated phase")
    root = Path(args.tool_root)
    plain_directory(root)
    # A fresh bootstrap directory makes preexisting owner/account state and
    # accidental reruns fail before execution. Repeated attempts need a new plan.
    if {p.name for p in root.iterdir()} != {"steamcmd.exe", "steamcmd.zip"}:
        raise ValueError("Expected only the prepared ZIP and bootstrap executable")
    initial_bytes = tree_bytes(root)
    executable = root / "steamcmd.exe"
    if executable.stat().st_size != 1687464 or hashlib.sha256(executable.read_bytes()).hexdigest() != BOOTSTRAP_SHA256:
        raise ValueError("Prepared bootstrap identity differs")
    copy_bounded = output_copy_function()
    logs = root / "metadata-attempt-a"
    logs.mkdir()
    temp = logs / "temp"
    temp.mkdir()
    environment = os.environ.copy()
    environment["TEMP"] = environment["TMP"] = str(temp)
    exceeded = threading.Event()
    handles, workers = [], []
    failure = None
    maximum_bytes = initial_bytes
    started = time.monotonic()
    process = subprocess.Popen([str(executable), *ARGUMENTS], cwd=root, env=environment,
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, creationflags=0x08000000)
    for label, source in (("stdout", process.stdout), ("stderr", process.stderr)):
        destination = (logs / f"{label}.log").open("xb")
        handles.append(destination)
        worker = threading.Thread(target=guarded_copy,
                                  args=(copy_bounded, source, destination, exceeded), daemon=True)
        worker.start()
        workers.append(worker)
    try:
        while process.poll() is None:
            maximum_bytes = max(maximum_bytes, tree_bytes(root))
            if exceeded.is_set() or time.monotonic() - started >= DEADLINE_SECONDS:
                failure = "log bound/output error" if exceeded.is_set() else "phase deadline"
                break
            time.sleep(0.25)
        if failure is None:
            if time.monotonic() - started >= DEADLINE_SECONDS:
                failure = "phase deadline"
        if failure is None:
            for worker in workers:
                worker.join(2)
            if exceeded.is_set() or any(worker.is_alive() for worker in workers):
                failure = "output error or inherited pipe remains open"
            maximum_bytes = max(maximum_bytes, tree_bytes(root))
            if time.monotonic() - started >= DEADLINE_SECONDS:
                failure = "phase deadline"
    except (OSError, ValueError) as error:
        failure = str(error)
    result = {
        "schema": "iw7.steamcmd-metadata-phase/1", "command": list(ARGUMENTS),
        "bootstrap_sha256_before": BOOTSTRAP_SHA256, "steamcmd_pid": process.pid,
        "steamcmd_exit_code": process.poll(), "failure": failure,
        "elapsed_seconds": time.monotonic() - started,
        "deadline_seconds": DEADLINE_SECONDS, "observed_maximum_tool_bytes": maximum_bytes,
        "disk_observation_limit_bytes": DISK_LIMIT, "log_limit_each_bytes": LOG_LIMIT,
        "metadata_reserve_bytes": METADATA_RESERVE,
        "disk_limit_is_os_quota": False, "app_or_depot_download_requested": False,
        "personal_login_requested": False, "application_identity_confirmed": False,
        "closure_owner": "coordinator original Windows job; this result does not prove closure"
    }
    (logs / "phase.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if failure:
        # Never kill/adopt by PID. The outer observer must terminate its original
        # job, freshly confirm root exit/zero active members, then release lease.
        os._exit(2)
    for handle in handles:
        handle.close()
    return 0 if process.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Snapshot one BO3 (T7) zone: every weapon and every effect, in one step, stdlib only.

A port reads two things from a zone held resident by the owner-fork ZoneTool:
the weapon headers (t7_weapon_scan.py) and the effects with their samples
(t7_fx_read.py). Holding the zone by hand and reading it later loses the hold
when the reads are late. This starts ZoneTool with ``-holdzone``, waits for its
``ZONETOOL_HOLD <zone> <pid>`` line, runs both readers on that pid at once,
then writes the release file and waits for ZoneTool to exit. One snapshot
serves every weapon of that zone (zm_levelcommon, a DLC map zone, ...):

    <out>/<zone>.assets.tsv    ZoneTool asset log
    <out>/<zone>.weapons.json  t7.weapon-scan/1, all weapons
    <out>/<zone>.effects.json  t7.fx-read/1, all effects with samples
    <out>/<zone>.materials.json t7.material-read/1, every material's constants

    python t7_zone_snapshot.py --zonetool <zt-t7>/zonetool.exe --zone zm_levelcommon --out <dir>

Resource leases are the caller's (the machine's scheduler), not this tool's.
Nothing is written to the ZoneTool process. GPL-3.0-or-later (ZoneTool lineage).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HOLD = re.compile(r"ZONETOOL_HOLD\s+(\S+)\s+(\d+)")


def outputs(out_dir, zone):
    base = os.path.join(os.path.abspath(out_dir), zone)
    return {"assetlog": base + ".assets.tsv", "weapons": base + ".weapons.json", "effects": base + ".effects.json",
            "materials": base + ".materials.json"}


def reader_commands(python, pid, paths):
    return [
        [python, "-B", os.path.join(HERE, "t7_weapon_scan.py"), "--pid", str(pid),
         "--assetlog", paths["assetlog"], "--out", paths["weapons"]],
        [python, "-B", os.path.join(HERE, "t7_fx_read.py"), "--pid", str(pid),
         "--assetlog", paths["assetlog"], "--out", paths["effects"]],
        [python, "-B", os.path.join(HERE, "t7_material_read.py"), "--pid", str(pid),
         "--assetlog", paths["assetlog"], "--out", paths["materials"]],
    ]


def wait_for_hold(proc, zone, timeout, log):
    """Read ZoneTool's stdout until it says the zone is resident; returns the holding pid."""
    found = {}

    def pump():
        for line in proc.stdout:
            log.append(line.rstrip())
            m = HOLD.search(line)
            if m and m.group(1) == zone and "pid" not in found:
                found["pid"] = int(m.group(2))
    t = threading.Thread(target=pump, daemon=True)
    t.start()
    deadline = time.monotonic() + timeout
    while "pid" not in found:
        if proc.poll() is not None:
            t.join(2)
            if "pid" in found:
                break
            raise SystemExit("ZoneTool exited (%s) before holding %s:\n%s" % (proc.returncode, zone, "\n".join(log[-20:])))
        if time.monotonic() > deadline:
            raise SystemExit("ZoneTool did not hold %s within %ss" % (zone, timeout))
        time.sleep(0.2)
    return found["pid"]


def snapshot(zonetool_cmd, cwd, zone, out_dir, python=sys.executable, timeout=900, readers=None):
    """zonetool_cmd: the ZoneTool executable (or a command list ending before its arguments)."""
    paths = outputs(out_dir, zone)
    os.makedirs(os.path.dirname(paths["assetlog"]), exist_ok=True)
    release = os.path.join(cwd, "release-snapshot-%s.txt" % zone)
    if os.path.exists(release):
        os.remove(release)
    cmd = (list(zonetool_cmd) if isinstance(zonetool_cmd, (list, tuple)) else [zonetool_cmd]) + [
        "-unbuffered-io", "-assetlog", paths["assetlog"], "-holdzone", zone, os.path.basename(release)]
    log = []
    proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            errors="replace")
    results = []
    try:
        pid = wait_for_hold(proc, zone, timeout, log)
        for rc in (readers or reader_commands)(python, pid, paths):
            r = subprocess.run(rc, capture_output=True, text=True)
            if r.returncode:
                raise SystemExit("reader failed: %s\n%s" % (" ".join(rc[:3]), (r.stdout + r.stderr)[-2000:]))
            results.append(r.stdout.strip())
    finally:
        with open(release, "w") as f:
            f.write("x")
        try:
            proc.wait(60)
        except subprocess.TimeoutExpired:
            proc.kill()
        proc.stdout.close()
        if os.path.exists(release):
            os.remove(release)
    return {"zone": zone, "holder_pid": pid, "paths": paths, "readers": results}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--zonetool", required=True, help="owner-fork ZoneTool (T7) next to the BO3 zone folder")
    ap.add_argument("--zone", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=int, default=900, help="seconds to wait for the zone to load")
    args = ap.parse_args(argv)
    zt = os.path.abspath(args.zonetool)
    print(json.dumps(snapshot(zt, os.path.dirname(zt), args.zone, args.out, timeout=args.timeout), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

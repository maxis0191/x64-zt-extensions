"""Read-only scan of BO3 (T7) weapon assets resident in a ZoneTool T7 process.

ZoneTool (owner fork) runs with ``-assetlog <file> -holdzone <zone> <release>``:
it records every registered asset header address and keeps the zone resident.
This tool reads the weapon headers it lists, follows pointers a bounded number
of levels, and annotates every 8-byte slot that refers to another registered
asset (anim, model, fx, sound, ...) or to a C string. The output is raw,
annotated memory: field meanings are inferred separately (t7_weapon_fields.py).

Nothing is written to the target process. GPL-3.0-or-later (ZoneTool lineage).
"""
import argparse
import bisect
import ctypes
import ctypes.wintypes as wt
import json
import os
import re
import sys

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
READABLE = {0x02, 0x04, 0x08, 0x20, 0x40, 0x80}  # RO, RW, WC, XR, XRW, XWC

WEAPON_TYPE = 0x17


class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wt.DWORD), ("PartitionId", wt.WORD),
                ("RegionSize", ctypes.c_size_t), ("State", wt.DWORD),
                ("Protect", wt.DWORD), ("Type", wt.DWORD)]


class Process:
    def __init__(self, pid):
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        self.k = k
        k.OpenProcess.restype = wt.HANDLE
        k.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                        ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
        k.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(MBI), ctypes.c_size_t]
        k.VirtualQueryEx.restype = ctypes.c_size_t
        self.h = k.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
        if not self.h:
            raise OSError(ctypes.get_last_error(), "OpenProcess failed")
        # The zone is resident and the process idle (-holdzone), so the readable
        # region map is enumerated once and searched by bisection.
        self.starts, self.ends = [], []
        addr = 0x10000
        mbi = MBI()
        while addr < 0x7FFFFFFF0000:
            if not k.VirtualQueryEx(self.h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
                break
            base = mbi.BaseAddress or 0
            end = base + mbi.RegionSize
            if (mbi.State == MEM_COMMIT and (mbi.Protect & 0xFF) in READABLE
                    and not mbi.Protect & 0x100):
                if self.ends and self.ends[-1] == base:
                    self.ends[-1] = end
                else:
                    self.starts.append(base)
                    self.ends.append(end)
            addr = end
        self.str_cache = {}

    def region_end(self, addr):
        i = bisect.bisect_right(self.starts, addr) - 1
        if i < 0 or addr >= self.ends[i]:
            return None
        return self.ends[i]

    def readable(self, addr, size=1):
        end = self.region_end(addr)
        return end is not None and addr + size <= end

    def read(self, addr, size):
        buf = ctypes.create_string_buffer(size)
        got = ctypes.c_size_t()
        if not self.k.ReadProcessMemory(self.h, ctypes.c_void_p(addr), buf, size, ctypes.byref(got)):
            raise OSError(ctypes.get_last_error(), "ReadProcessMemory 0x%x" % addr)
        return buf.raw[:got.value]

    def read_clamped(self, addr, size):
        """Read up to size bytes, stopping at the end of the readable region."""
        end = self.region_end(addr)
        if end is None:
            return b""
        return self.read(addr, max(0, min(size, end - addr)))

    def cstr(self, addr, limit=256):
        if addr in self.str_cache:
            return self.str_cache[addr]
        result = None
        raw = self.read_clamped(addr, limit)
        end = raw.find(b"\0")
        if end >= 2 and re.fullmatch(rb"[\x20-\x7e]+", raw[:end]):
            result = raw[:end].decode("ascii")
        self.str_cache[addr] = result
        return result


def load_asset_log(path):
    by_addr = {}
    weapons = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 4:
                continue
            type_index, type_name, name, addr = parts
            entry = {"type": int(type_index), "type_name": type_name, "name": name.lstrip(",")}
            address = int(addr, 16)
            by_addr[address] = entry
            if entry["type"] == WEAPON_TYPE:
                weapons.append((entry["name"], address))
    return by_addr, weapons


def scan_block(proc, assets, addr, size, depth, windows, seen, budget):
    raw = proc.read_clamped(addr, size)
    block = {"addr": "0x%x" % addr, "size": len(raw), "hex": raw.hex(), "refs": []}
    children = []
    for off in range(0, len(raw) - 7, 8):
        value = int.from_bytes(raw[off:off + 8], "little")
        if value in assets:
            a = assets[value]
            block["refs"].append({"off": off, "kind": "asset", "type": a["type_name"], "name": a["name"]})
            continue
        if not proc.readable(value):
            continue
        text = proc.cstr(value)
        if text is not None:
            block["refs"].append({"off": off, "kind": "string", "value": text})
            continue
        block["refs"].append({"off": off, "kind": "pointer", "target": "0x%x" % value})
        if depth + 1 < len(windows) and value not in seen and budget[0] > 0:
            children.append((off, value))
    for off, value in children:
        if value in seen or budget[0] <= 0:
            continue
        seen.add(value)
        budget[0] -= 1
        child = scan_block(proc, assets, value, windows[depth + 1], depth + 1, windows, seen, budget)
        block.setdefault("children", {})[str(off)] = child
    return block


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--assetlog", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", nargs="*", help="weapon names to scan (default: all)")
    ap.add_argument("--windows", default="0x400,0x2000,0x800,0x200",
                    help="bytes read at each pointer depth")
    ap.add_argument("--max-blocks", type=int, default=400, help="nested blocks per weapon")
    args = ap.parse_args()

    windows = [int(x, 0) for x in args.windows.split(",")]
    assets, weapons = load_asset_log(args.assetlog)
    if args.only:
        wanted = set(args.only)
        weapons = [w for w in weapons if w[0] in wanted]
    proc = Process(args.pid)
    out = {"schema": "t7.weapon-scan/1", "pid": args.pid, "windows": windows,
           "asset_count": len(assets), "weapons": {}}
    for name, addr in weapons:
        seen = {addr}
        budget = [args.max_blocks]
        out["weapons"][name] = scan_block(proc, assets, addr, windows[0], 0, windows, seen, budget)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f)
    print(json.dumps({"weapons": len(out["weapons"]), "assets": len(assets), "out": args.out}))


if __name__ == "__main__":
    sys.exit(main())

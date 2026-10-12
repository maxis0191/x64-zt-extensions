"""Future owned CDB qualification target; never imported for light tests.

No retail file or game code. One allocation, one intentional DebugBreak, one
known write. The original outer job must terminate this fixture after capture.
"""
import argparse
import ctypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--nonce", required=True)
    args = parser.parse_args()
    if os.name != "nt" or len(args.nonce) != 32 or any(c not in "0123456789abcdef" for c in args.nonce):
        parser.error("Windows and exact nonce required")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.DebugBreak.argtypes = []
    kernel.DebugBreak.restype = None
    kernel.IsProcessInJob.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
    member = ctypes.c_int()
    if not kernel.IsProcessInJob(kernel.GetCurrentProcess(), None, ctypes.byref(member)) or not member.value:
        raise RuntimeError("Outer owning job required")
    kernel.GetProcessTimes.argtypes = [ctypes.c_void_p] + [ctypes.POINTER(ctypes.c_uint64)] * 4
    clocks = [ctypes.c_uint64() for _ in range(4)]
    if not kernel.GetProcessTimes(kernel.GetCurrentProcess(), *(ctypes.byref(item) for item in clocks)):
        raise ctypes.WinError(ctypes.get_last_error())
    name = ctypes.create_string_buffer(b"paris_doom_skin_two_bone_first_a_lod0\0")
    surface = (ctypes.c_uint64 * 32)()
    model_surfs = (ctypes.c_uint64 * 7)()
    model_surfs[0] = ctypes.addressof(name)
    model_surfs[1] = ctypes.addressof(surface)
    ctypes.c_uint16.from_address(ctypes.addressof(model_surfs) + 16).value = 1
    seconds, fraction = divmod(clocks[0].value, 10000000)
    created = datetime.fromtimestamp(seconds - 11644473600, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    manifest = {"schema": "iw7.rig-watch-fixture/1", "nonce": args.nonce, "pid": os.getpid(),
                "created_filetime": clocks[0].value,
                "creation_utc": created + f".{fraction:07d}Z",
                "xsurface": hex(ctypes.addressof(surface)), "xmodelsurfs": hex(ctypes.addressof(model_surfs)),
                "name_address": hex(ctypes.addressof(name)), "expected_new_category": "equals_current_name_address"}
    with args.manifest.open("x", encoding="ascii") as handle:
        json.dump(manifest, handle, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    kernel.DebugBreak()  # CDB must stop here; no unowned invocation is valid.
    surface[11] = ctypes.addressof(name)  # Exactly XSurface+0x58, an eight-byte write.
    while True:
        time.sleep(1)  # Owned watchdog closes us; no exit0/retail claim.


if __name__ == "__main__":
    main()

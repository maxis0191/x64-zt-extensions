"""Read-only BO3 (T7) loaded-map extractor.

Reads the running BlackOps3.exe process memory (no writes, no injection) and
exports the loaded map's render world (GfxWorld surfaces/vertices/materials),
collision (clipMap brushes and triangle soup, submodels, static models),
pathnodes (GameWorld) and map entity string.

The GfxWorld/material/static-model offsets and asset pool address are ported
from Husky (C) 2018 Philip/Scobalula, GPL-3.0, as maintained in vugi99/C2M
(src/Husky/Husky/Games/BlackOps3.cs, HuskyUtil.cs). Clip/path layouts follow
the T7 structure declarations of the pinned x64-zt fork (t7/structs.hpp).
This file is therefore GPL-3.0-or-later.
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import struct
import sys

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
TH32CS_SNAPPROCESS = 0x2
TH32CS_SNAPMODULE = 0x8
TH32CS_SNAPMODULE32 = 0x10
POOLS_RVA = 0x93883F0  # boiii-launched BlackOps3.exe (manifest 9A24E723...); Husky listed 0x94073F0
POOL_STRIDE = 0x20
T_XMODEL, T_CLIPMAP, T_GAMEWORLD, T_MAPENTS, T_GFXWORLD = 0x4, 0xC, 0xE, 0xF, 0x10

k32 = ctypes.WinDLL("kernel32", use_last_error=True)


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
                ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wt.DWORD),
                ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
                ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD), ("szExeFile", ctypes.c_wchar * 260)]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD), ("th32ProcessID", wt.DWORD),
                ("GlblcntUsage", wt.DWORD), ("ProccntUsage", wt.DWORD), ("modBaseAddr", ctypes.c_void_p),
                ("modBaseSize", wt.DWORD), ("hModule", wt.HMODULE), ("szModule", ctypes.c_wchar * 256),
                ("szExePath", ctypes.c_wchar * 260)]


k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.OpenProcess.restype = wt.HANDLE
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]


def find_process(name):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    entry = PROCESSENTRY32W(dwSize=ctypes.sizeof(PROCESSENTRY32W))
    found = []
    ok = k32.Process32FirstW(snap, ctypes.byref(entry))
    while ok:
        if entry.szExeFile.lower() == name.lower():
            found.append(entry.th32ProcessID)
        ok = k32.Process32NextW(snap, ctypes.byref(entry))
    k32.CloseHandle(snap)
    return found


def module_base(pid, name):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    entry = MODULEENTRY32W(dwSize=ctypes.sizeof(MODULEENTRY32W))
    ok = k32.Module32FirstW(snap, ctypes.byref(entry))
    base = None
    while ok:
        if entry.szModule.lower() == name.lower():
            base = entry.modBaseAddr
            break
        ok = k32.Module32NextW(snap, ctypes.byref(entry))
    k32.CloseHandle(snap)
    return base


class Reader:
    def __init__(self, pid):
        self.h = k32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
        if not self.h:
            raise OSError("OpenProcess failed: %d" % ctypes.get_last_error())

    def read(self, addr, size):
        if size <= 0:
            return b""
        buf = ctypes.create_string_buffer(size)
        got = ctypes.c_size_t()
        if not addr or not k32.ReadProcessMemory(self.h, ctypes.c_void_p(addr), buf, size, ctypes.byref(got)) or got.value != size:
            raise OSError("read failed at 0x%x size %d" % (addr or 0, size))
        return buf.raw

    def u8(self, a): return self.read(a, 1)[0]
    def u16(self, a): return struct.unpack("<H", self.read(a, 2))[0]
    def i32(self, a): return struct.unpack("<i", self.read(a, 4))[0]
    def u32(self, a): return struct.unpack("<I", self.read(a, 4))[0]
    def i64(self, a): return struct.unpack("<q", self.read(a, 8))[0]
    def f32s(self, a, n): return list(struct.unpack("<%df" % n, self.read(a, 4 * n)))

    def cstr(self, a, limit=1024):
        if not a:
            return ""
        out = bytearray()
        while len(out) < limit:
            chunk = self.read(a + len(out), 64) if True else b""
            z = chunk.find(b"\0")
            if z >= 0:
                out += chunk[:z]
                break
            out += chunk
        return out.decode("latin-1")

    def cstr_safe(self, a, limit=1024):
        try:
            return self.cstr(a, limit)
        except OSError:
            # Strings near a page end: read byte-wise.
            out = bytearray()
            for i in range(limit):
                try:
                    b = self.u8(a + i)
                except OSError:
                    break
                if b == 0:
                    break
                out.append(b)
            return out.decode("latin-1")


def pool(r, base, t):
    return r.i64(base + POOLS_RVA + t * POOL_STRIDE)


def read_material(r, addr, cache):
    if addr in cache:
        return cache[addr]
    name = r.cstr_safe(r.i64(addr)).replace("*", "")
    images = {}
    count = r.u8(addr + 624)
    table = r.i64(addr + 640)
    sem = {0xA0AB1041: "color", 0x59D30D0F: "normal", 0x34ECCCB3: "specular", 0x34D849D5: "height",
           0x34614347: "emission", 0x6001F931: "occlusion"}
    for i in range(count):
        try:
            img = r.i64(table + i * 32)
            h = r.u32(table + i * 32 + 8)
            iname = r.cstr_safe(r.i64(img + 0xF8))
        except OSError:
            continue
        key = sem.get(h, "0x%08X" % h)
        images.setdefault(key, iname)
    cache[addr] = {"name": name, "images": images}
    return cache[addr]


def export_world(r, base, out, meta):
    g = pool(r, base, T_GFXWORLD)
    name = r.cstr_safe(r.i64(g))
    mapname = r.cstr_safe(r.i64(g + 8))
    surf_count = r.i32(g + 24)
    vcount = r.i32(g + 0x268)
    vptr = r.i64(g + 0x270)
    vdata = r.i64(g + 0x288)
    icount = r.i64(g + 0x298)
    iptr = r.i64(g + 0x2A0)
    smcount = r.i32(g + 0x2FC)
    sptr = r.i64(g + 0x430)
    smptr = r.i64(g + 0x438)
    meta["gfxworld"] = {"name": name, "map": mapname, "surfaces": surf_count, "vertices": vcount,
                        "indices": icount, "static_models": smcount}
    if not name or vcount <= 0 or surf_count <= 0:
        raise SystemExit("No BSP loaded")
    pos = r.read(vptr, vcount * 12)
    dat = r.read(vdata, vcount * 20)
    idx = r.read(iptr, icount * 2)
    with open(os.path.join(out, "world_positions.f32"), "wb") as f:
        f.write(pos)
    with open(os.path.join(out, "world_vertexdata.bin"), "wb") as f:
        f.write(dat)
    with open(os.path.join(out, "world_indices.u16"), "wb") as f:
        f.write(idx)
    mats = {}
    surfaces = []
    raw = r.read(sptr, surf_count * 96)
    for i in range(surf_count):
        s = raw[i * 96:(i + 1) * 96]
        vbo, = struct.unpack_from("<i", s, 0x0C)
        vdo, = struct.unpack_from("<i", s, 0x1C)
        vidx, = struct.unpack_from("<i", s, 0x20)
        vc, fc = struct.unpack_from("<HH", s, 0x28)
        fidx, = struct.unpack_from("<i", s, 0x2C)
        mptr, = struct.unpack_from("<q", s, 0x48)
        m = read_material(r, mptr, mats) if mptr else {"name": "", "images": {}}
        surfaces.append({"vertex_buffer_offset": vbo, "vertex_data_offset": vdo, "vertex_index": vidx,
                         "vertex_count": vc, "face_count": fc, "face_index": fidx, "material": m["name"]})
    smodels = []
    sraw = r.read(smptr, smcount * 152) if smcount else b""
    for i in range(smcount):
        s = sraw[i * 152:(i + 1) * 152]
        o = struct.unpack_from("<3f", s, 0)
        m = struct.unpack_from("<9f", s, 12)
        scale, = struct.unpack_from("<f", s, 48)
        mp, = struct.unpack_from("<q", s, 88)
        try:
            mname = r.cstr_safe(r.i64(mp)) if mp else ""
        except OSError:
            mname = ""
        smodels.append({"model": mname, "model_ptr": mp, "origin": o, "axis": m, "scale": scale})
    json.dump({"surfaces": surfaces, "materials": list(mats.values()), "static_models": smodels},
              open(os.path.join(out, "world.json"), "w"), indent=1)


CPLANE = 20
BRUSH = 112  # observed client stride; zonetool t7 cbrush_t declares 104 (+1 trailing pointer here)


def read_brushes(r, info_addr, verts_cap=200000):
    # ClipInfo layout (x64 natural alignment), see t7/structs.hpp.
    nb = r.u16(info_addr + 112)
    bptr = r.i64(info_addr + 120)
    brushes = []
    raw = r.read(bptr, nb * BRUSH) if nb else b""
    for i in range(nb):
        b = raw[i * BRUSH:(i + 1) * BRUSH]
        mins = struct.unpack_from("<3f", b, 0)
        contents, = struct.unpack_from("<I", b, 12)
        maxs = struct.unpack_from("<3f", b, 16)
        numsides, = struct.unpack_from("<I", b, 28)
        sides, = struct.unpack_from("<q", b, 32)
        numverts, = struct.unpack_from("<I", b, 88)
        vptr, = struct.unpack_from("<q", b, 96)
        planes = []
        if numsides and sides and numsides < 512:
            sraw = r.read(sides, numsides * 16)
            for k in range(numsides):
                pptr, cflags, sflags = struct.unpack_from("<qIi", sraw, k * 16)
                pl = struct.unpack("<4f", r.read(pptr, 16)) if pptr else None
                planes.append({"plane": pl, "cflags": cflags, "sflags": sflags})
        verts = []
        if numverts and vptr and numverts < 4096:
            v = struct.unpack("<%df" % (numverts * 3), r.read(vptr, numverts * 12))
            verts = [v[k:k + 3] for k in range(0, len(v), 3)]
        brushes.append({"mins": mins, "maxs": maxs, "contents": contents, "sides": planes, "verts": verts})
    return brushes


def export_clip(r, base, out, meta):
    c = pool(r, base, T_CLIPMAP)
    name = r.cstr_safe(r.i64(c))
    info = c + 16
    brushes = read_brushes(r, info)
    nsm = r.u32(c + 168)
    smptr = r.i64(c + 176)
    vcount = r.u32(c + 216)
    vptr = r.i64(c + 224)
    tcount = r.i32(c + 232)
    tptr = r.i64(c + 240)
    walk = r.i64(c + 248)
    nsub = r.u32(c + 288)
    subptr = r.i64(c + 296)
    meta["clipmap"] = {"name": name, "brushes": len(brushes), "static_models": nsm, "verts": vcount,
                       "tris": tcount, "submodels": nsub}
    with open(os.path.join(out, "clip_verts.f32"), "wb") as f:
        f.write(r.read(vptr, vcount * 12) if vcount else b"")
    with open(os.path.join(out, "clip_tris.u32"), "wb") as f:
        f.write(r.read(tptr, tcount * 12) if tcount else b"")
    try:
        with open(os.path.join(out, "clip_tri_walkable.u8"), "wb") as f:
            f.write(r.read(walk, tcount) if (tcount and walk) else b"")
    except OSError:
        pass
    smodels = []
    for i in range(nsm):
        a = smptr + i * 112
        xm = r.i64(a + 8)
        try:
            nm = r.cstr_safe(r.i64(xm)) if xm else ""
        except OSError:
            nm = ""
        smodels.append({"model": nm, "contents": r.u32(a + 16), "origin": r.f32s(a + 20, 3),
                        "inv_scaled_axis": r.f32s(a + 32, 9), "absmin": r.f32s(a + 68, 3), "absmax": r.f32s(a + 80, 3)})
    subs = []
    # cmodel_t: mins(12) maxs(12) radius(4) pad(4) info ptr(8) leaf(cLeaf_t 56) -> 96
    for i in range(nsub):
        a = subptr + i * 96
        mins = r.f32s(a, 3)
        maxs = r.f32s(a + 12, 3)
        iptr = r.i64(a + 32)
        sb = []
        if iptr and iptr != info:
            try:
                sb = read_brushes(r, iptr)
            except OSError:
                sb = []
        subs.append({"index": i, "mins": mins, "maxs": maxs, "brushes": sb})
    json.dump({"brushes": brushes, "static_models": smodels, "submodels": subs},
              open(os.path.join(out, "clip.json"), "w"))


def export_paths(r, base, out, meta):
    gw = pool(r, base, T_GAMEWORLD)
    name = r.cstr_safe(r.i64(gw))
    count = r.u32(gw + 8)
    nodes = r.i64(gw + 16)
    meta["gameworld"] = {"name": name, "nodes": count}
    stride = 224
    res = []
    for i in range(count):
        a = nodes + i * stride
        t = r.i32(a)
        origin = r.f32s(a + 48, 3)
        angle = r.f32s(a + 60, 1)[0]
        links = r.u16(a + 80)
        lptr = r.i64(a + 88)
        ls = []
        if links and lptr and links < 256:
            raw = r.read(lptr, links * 16)
            for k in range(links):
                dist, num = struct.unpack_from("<fH", raw, k * 16)
                ls.append([num, round(dist, 2)])
        res.append({"type": t, "spawnflags": r.i32(a + 4), "origin": origin, "angle": angle, "links": ls})
    json.dump(res, open(os.path.join(out, "pathnodes.json"), "w"))


def export_ents(r, base, out, meta):
    m = pool(r, base, T_MAPENTS)
    text = r.cstr_safe(r.i64(m + 8), limit=64 * 1024 * 1024)
    meta["mapents"] = {"name": r.cstr_safe(r.i64(m)), "chars": len(text)}
    open(os.path.join(out, "mapents.txt"), "w", encoding="latin-1").write(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--process", default="boiii.exe")
    ap.add_argument("--module", default="BlackOps3.exe")
    ap.add_argument("--expect-map", default="")
    a = ap.parse_args()
    pids = find_process(a.process)
    if len(pids) != 1:
        raise SystemExit("Expected exactly one %s, found %r" % (a.process, pids))
    pid = pids[0]
    base = module_base(pid, a.module)
    if not base:
        raise SystemExit("module base not found")
    r = Reader(pid)
    first = r.cstr_safe(r.i64(r.i64(base + POOLS_RVA + T_XMODEL * POOL_STRIDE)))
    if first != "void":
        raise SystemExit("Unsupported executable (first xmodel %r)" % first)
    g = pool(r, base, T_GFXWORLD)
    loaded = r.cstr_safe(r.i64(g + 8))
    if a.expect_map and a.expect_map not in loaded:
        raise SystemExit("Map not loaded yet: %r" % loaded)
    os.makedirs(a.out, exist_ok=False)
    meta = {"schema": "t7.loaded-map-export/1", "pid": pid, "module_base": hex(base)}
    for step in (export_world, export_clip, export_paths, export_ents):
        try:
            step(r, base, a.out, meta)
        except Exception as e:  # keep partial evidence; report the failing step
            meta.setdefault("errors", []).append("%s: %s" % (step.__name__, e))
    json.dump(meta, open(os.path.join(a.out, "meta.json"), "w"), indent=1)
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()

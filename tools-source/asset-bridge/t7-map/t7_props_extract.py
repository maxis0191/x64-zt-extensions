"""Read-only export of LOD0 rigid geometry for every static model referenced
by an already exported T7 GfxWorld (world.json). Layouts: pinned x64-zt
t7/structs.hpp (XModel 0x188, XModelMesh 0x78, XSurface, XSurfaceShared).
GPL-3.0-or-later (shares the Husky-derived reader module)."""
import sys, os, struct, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_map_extract as t

def surf_rows(r, mesh_ptr):
    numsurfs = r.u8(mesh_ptr + 0x3C)
    surfs = r.i64(mesh_ptr + 0x68)
    return numsurfs, surfs

def export_mesh(r, a, mesh, mats, blob):
    mm = r.i64(a + 0xC8)
    nmat = r.u16(mm)
    matptrs = r.i64(mm + 8)
    numsurfs = r.u8(mesh + 0x3C)
    surfs = r.i64(mesh + 0x68)
    staged = []
    for k in range(numsurfs):
        sa = surfs + k * 96
        vc = r.u16(sa + 4); tc = r.u16(sa + 6)
        bvo = r.u32(sa + 8); bio = r.u32(sa + 12)
        sh = r.i64(sa + 16)
        data = r.i64(sh + 16); posoff = r.u32(sh + 28); vertoff = r.u32(sh + 32); idxoff = r.u32(sh + 36)
        pos = r.read(data + posoff + bvo * 12, vc * 12)
        att = r.read(data + vertoff + bvo * 16, vc * 16)
        idx = r.read(data + idxoff + bio * 2, tc * 6)
        mp = r.i64(matptrs + k * 8) if k < nmat else 0
        staged.append((pos, att, idx, mp, vc, tc))
    rows = []
    for pos, att, idx, mp, vc, tc in staged:
        m = t.read_material(r, mp, mats) if mp else {"name": "", "images": {}}
        off = blob.tell()
        blob.write(pos); blob.write(att); blob.write(idx)
        rows.append({"material": m["name"], "verts": vc, "tris": tc, "offset": off})
    return rows

def main():
    src, out = sys.argv[1], sys.argv[2]
    prev = sys.argv[3] if len(sys.argv) > 3 else None
    done = set()
    if prev:
        for p in prev.split(";"):
            done |= set(json.load(open(os.path.join(p, "props.json")))["models"])
    pid = t.find_process("boiii.exe")[0]
    base = t.module_base(pid, "BlackOps3.exe")
    r = t.Reader(pid)
    w = json.load(open(os.path.join(src, "world.json")))
    ptrs = {}
    for s in w["static_models"]:
        if s["model"] and not s["model"].startswith("*"):
            ptrs.setdefault(s["model"], s["model_ptr"])
    os.makedirs(out, exist_ok=False)
    blob = open(os.path.join(out, "props.bin"), "wb")
    mats = {}
    index = {}
    failures = {}
    lowlod = {}
    for name, a in sorted(ptrs.items()):
        if name in done:
            continue
        try:
            mesh = r.i64(a + 0x88)
            rows = export_mesh(r, a, mesh, mats, blob)
            index[name] = rows
        except Exception as e:
            failures[name] = str(e)
            if "--lowlod" in sys.argv:
                nl = r.u8(a + 0x40)
                for lod in range(1, min(nl, 8)):
                    try:
                        index[name] = export_mesh(r, a, r.i64(a + 0x88 + lod * 8), mats, blob)
                        lowlod[name] = lod
                        del failures[name]
                        break
                    except Exception:
                        pass
    blob.close()
    json.dump({"schema": "t7.static-model-lod0/1", "layout": "per surface: pos f32x3*V, attr(color u8x4, uv f16x2, normal u32, tangent u32)*V, idx u16x3*T",
               "models": index, "lowlod": lowlod, "materials": list(mats.values()), "failures": failures},
              open(os.path.join(out, "props.json"), "w"))
    print("models", len(index), "failures", len(failures), list(failures.items())[:5])

main()

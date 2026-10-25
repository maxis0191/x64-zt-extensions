"""Read-only T7 metadata export: every material used by the loaded GfxWorld
surfaces and by its static models, each image's streamed xpak parts, and the
xpak entries/layouts of static-model LOD0 meshes. GPL-3.0-or-later."""
import os, sys, json, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_map_extract as t


def xpak_entry(raw, off):
    key, offset, size, bits = struct.unpack_from("<QqQQ", raw, off)
    return {"key": "%016x" % key, "offset": offset, "size": size, "xpak_index": bits & 0x1F,
            "compressed": (bits >> 5) & 1, "valid": (bits >> 6) & 1}


def image_meta(r, img):
    raw = r.read(img, 0x108)
    parts = []
    count = raw[160]
    for i in range(min(count, 4)):
        lc, w, h = struct.unpack_from("<IHH", raw, i * 40)
        e = xpak_entry(raw, i * 40 + 8)
        e.update({"level_count_and_size": lc, "width": w, "height": h})
        parts.append(e)
    width, height, depth = struct.unpack_from("<HHH", raw, 196)
    levels = raw[208]
    pixels, = struct.unpack_from("<Q", raw, 216)
    total, = struct.unpack_from("<I", raw, 232)
    fmt, = struct.unpack_from("<I", raw, 240)
    name = r.cstr_safe(struct.unpack_from("<Q", raw, 248)[0])
    return {"name": name, "width": width, "height": height, "depth": depth, "levels": levels, "dxgi_format": fmt,
            "map_type": raw[162], "semantic": raw[161], "flags": struct.unpack_from("<I", raw, 184)[0],
            "resident_pixels": bool(pixels), "total_size": total, "streamed_parts": parts}


def material_meta(r, addr, images):
    name = r.cstr_safe(r.i64(addr)).replace("*", "")
    count = r.u8(addr + 624)
    table = r.i64(addr + 640)
    tech = r.i64(addr + 632)
    slots = []
    for i in range(count):
        img = r.i64(table + i * 32)
        h = r.u32(table + i * 32 + 8)
        if img not in images:
            try:
                images[img] = image_meta(r, img)
            except OSError as e:
                images[img] = {"error": str(e)}
        slots.append({"semantic_hash": "%08x" % h, "image": images[img].get("name")})
    try:
        tname = r.cstr_safe(r.i64(tech))
    except OSError:
        tname = ""
    return {"name": name, "techset": tname, "images": slots}


def main():
    export = sys.argv[1]
    pid = t.find_process("boiii.exe")[0]
    base = t.module_base(pid, "BlackOps3.exe")
    r = t.Reader(pid)
    g = t.pool(r, base, t.T_GFXWORLD)
    if "zm_theater" not in r.cstr_safe(r.i64(g + 8)):
        raise SystemExit("zm_theater not loaded")
    images, materials = {}, {}
    surf_count = r.i32(g + 24)
    sptr = r.i64(g + 0x430)
    raw = r.read(sptr, surf_count * 96)
    for i in range(surf_count):
        mp, = struct.unpack_from("<q", raw, i * 96 + 0x48)
        if mp and mp not in materials:
            materials[mp] = material_meta(r, mp, images)
    w = json.load(open(os.path.join(export, "world.json")))
    ptrs = {}
    for s in w["static_models"]:
        if s["model"] and not s["model"].startswith("*"):
            ptrs.setdefault(s["model"], s["model_ptr"])
    meshes = {}
    for name, a in ptrs.items():
        try:
            mm = r.i64(a + 0xC8)
            nmat = r.u16(mm)
            matptrs = r.i64(mm + 8)
            mats = []
            for k in range(nmat):
                mp = r.i64(matptrs + k * 8)
                if mp and mp not in materials:
                    materials[mp] = material_meta(r, mp, images)
                mats.append(materials[mp]["name"] if mp else "")
            mesh = r.i64(a + 0x88)
            mraw = r.read(mesh, 0x78)
            numsurfs = mraw[0x3C]
            surfs, shared = struct.unpack_from("<QQ", mraw, 0x68)
            rows = []
            for k in range(numsurfs):
                sa = surfs + k * 96
                srow = r.read(sa, 96)
                flags, vc, tc, bvo, bio = struct.unpack_from("<HHHII", srow, 2)
                sh, = struct.unpack_from("<Q", srow, 16)
                shr = r.read(sh, 48)
                sflags, svc, sskin, sidx = struct.unpack_from("<IIII", shr, 0)
                data, = struct.unpack_from("<Q", shr, 16)
                dsize, posoff, vertoff, idxoff, skinoff = struct.unpack_from("<IIIII", shr, 24)
                rows.append({"flags": flags, "verts": vc, "tris": tc, "base_vert": bvo, "base_index": bio,
                             "shared": {"flags": sflags, "verts": svc, "indices": sidx, "data_size": dsize,
                                        "pos_offset": posoff, "verts_offset": vertoff, "indices_offset": idxoff,
                                        "skin_offset": skinoff}})
            meshes[name] = {"xpak": xpak_entry(mraw, 0x48), "surfaces": rows, "materials": mats,
                            "num_lods": r.u8(a + 0x40)}
        except OSError as e:
            meshes[name] = {"error": str(e)}
    json.dump({"schema": "t7.asset-meta/1", "materials": list(materials.values()), "images": list(images.values()),
               "meshes": meshes}, open(os.path.join(export, "assets_meta.json"), "w"))
    print("materials", len(materials), "images", len(images), "meshes", len(meshes),
          "mesh errors", sum(1 for m in meshes.values() if "error" in m))


main()

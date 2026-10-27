"""Read-only T7 metadata export: every material used by the loaded GfxWorld
surfaces and by its static models, each image's streamed xpak parts, and the
xpak entries/layouts of static-model LOD0 meshes. GPL-3.0-or-later."""
import argparse, os, sys, json, struct
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


def validate_identity(meta, pid, base, creation, world_address, world_name, map_name):
    expected_world = meta.get("gfxworld", {})
    if (meta.get("schema") != "t7.loaded-map-export/1" or meta.get("errors") or
            meta.get("pid") != pid or meta.get("module_base") != hex(base) or
            meta.get("process_creation_filetime") != creation or
            meta.get("gfxworld_address") != hex(world_address) or
            not world_name or not map_name or expected_world.get("name") != world_name or
            expected_world.get("map") != map_name):
        raise ValueError("Export identity does not match the loaded process/world; re-export this map")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", help="directory produced by t7_map_extract.py in this process session")
    parser.add_argument("--process", default="boiii.exe")
    parser.add_argument("--module", default="BlackOps3.exe")
    args = parser.parse_args()
    export = args.export
    pids = t.find_process(args.process)
    if len(pids) != 1:
        raise SystemExit("Expected exactly one %s, found %r" % (args.process, pids))
    pid = pids[0]
    base = t.module_base(pid, args.module)
    if not base:
        raise SystemExit("module base not found")
    r = t.Reader(pid)
    g = t.pool(r, base, t.T_GFXWORLD)
    with open(os.path.join(export, "meta.json"), encoding="utf-8") as stream:
        meta = json.load(stream)
    try:
        validate_identity(meta, pid, base, r.creation_time(), g,
                          r.cstr_safe(r.i64(g)), r.cstr_safe(r.i64(g + 8)))
    except ValueError as error:
        raise SystemExit(str(error)) from error
    images, materials = {}, {}
    surf_count = r.i32(g + 24)
    sptr = r.i64(g + 0x430)
    raw = r.read(sptr, surf_count * 96)
    for i in range(surf_count):
        mp, = struct.unpack_from("<q", raw, i * 96 + 0x48)
        if mp and mp not in materials:
            materials[mp] = material_meta(r, mp, images)
    with open(os.path.join(export, "world.json"), encoding="utf-8") as stream:
        w = json.load(stream)
    ptrs = {}
    for s in w["static_models"]:
        if s["model"] and not s["model"].startswith("*"):
            ptrs.setdefault(s["model"], s["model_ptr"])
    for name, address in ptrs.items():
        try:
            if r.cstr_safe(r.i64(address)) != name:
                raise ValueError("model name changed")
        except (OSError, ValueError) as error:
            raise SystemExit("Stale static-model pointer; re-export this map") from error
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


if __name__ == "__main__":
    main()

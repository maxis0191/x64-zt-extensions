"""Compose IW7 inputs for the Kino der Toten overlay from a T7 export.

Outputs (fresh directory): kmsh/ chunk meshes for kino_writer.exe, images/*.dds
(BO3 color maps, DX10, top mip <= MAX_TEX), materials/*.json and per-material
techset state copies from an authored template, zone_source/kino.csv,
netconststrings, and layout.json (chunk origins in BO3 space + placement offset).
"""
import argparse, array, json, math, os, re, shutil, struct, sys, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_xpak

MAX_TEX = 512
CELL = 1024.0
MAX_SURF_VERTS = 30000  # keep deduplicated vertex counts below 32768
MAX_SURFS_PER_MODEL = 32  # IW7 only draws the first 32 surfaces of a model (observed: surfaces 38+ vanish)
COLOR = "a0ab1041"
WIND = (0, 1, 2)  # IW7 stock surfaces use the same order as BO3: index cross product opposite the outward normal
SKIP_MAT = re.compile(r"decal|sky|caulk|shadow|collision|_clip|clip_|\$|portal|volume|nodraw|reveal|water|fog|lightmap|glass|ui_", re.I)
BLOCK = {71: 8, 72: 8, 80: 8, 81: 8, 74: 16, 75: 16, 77: 16, 78: 16, 83: 16, 84: 16, 95: 16, 96: 16, 98: 16, 99: 16}


def sanitize(name):
    base = name.split("/", 1)[-1] if "/" in name else name
    return re.sub(r"[^a-z0-9_]", "_", base.lower())[:60]


def mip_size(w, h, block):
    return max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * block


def build_dds(img, xs):
    fmt = img["dxgi_format"]
    block = BLOCK.get(fmt)
    parts = img.get("streamed_parts") or []
    if not block or not parts:
        return None
    k = max([i for i, p in enumerate(parts) if max(p["width"], p["height"]) <= MAX_TEX] or [0])
    chain = b""
    for i in range(k, 0, -1):
        d = xs.get(parts[i]["key"])
        if d is None or len(d) != mip_size(parts[i]["width"], parts[i]["height"], block):
            return None
        chain += d
    low = xs.get(parts[0]["key"])
    lc = parts[0]["level_count_and_size"]
    if low is None or len(low) != lc >> 4:
        return None
    chain += low
    w, h = parts[k]["width"], parts[k]["height"]
    # Exactly BO3's level count (its low chain stops at 4x4); trailing bytes are padding.
    levels = k + (lc & 15)
    expect, ww, hh = 0, w, h
    for _ in range(levels):
        expect += mip_size(ww, hh, block)
        ww, hh = max(1, ww // 2), max(1, hh // 2)
    if expect > len(chain):
        return None
    chain = chain[:expect]
    # IW7 creates the full chain down to 1x1; BO3 stops at 4x4. Extend with
    # copies of the last 4x4 block (each remaining level is a single block).
    full = int(math.floor(math.log2(max(w, h)))) + 1
    last = chain[-block:]
    while levels < full:
        chain += last * (mip_size(ww, hh, block) // block)
        ww, hh = max(1, ww // 2), max(1, hh // 2)
        levels += 1
    hdr = struct.pack("<4sIIIIIII44sII4s" + "I" * 15, b"DDS ", 124, 0x1 | 0x2 | 0x4 | 0x1000 | 0x20000 | 0x80000,
                      h, w, mip_size(w, h, block), 1, levels, b"\0" * 44, 32, 0x4, b"DX10", 0, 0, 0, 0, 0,
                      0x1000 | 0x400000 | 0x8, 0, 0, 0, 0, fmt, 3, 0, 1, 0)
    return hdr + chain


UNORM = {72: 71, 78: 77, 99: 98, 75: 74, 96: 95}
RGBA_TEX = 256


def to_rgba_dds(bc_dds):
    """Decode a BC DDS (Pillow) and re-encode as uncompressed R8G8B8A8, one mip:
    the only custom-image layout proven to load in IW7 so far (authored af6)."""
    import io
    from PIL import Image
    b = bytearray(bc_dds)
    fmt = struct.unpack_from("<I", b, 128)[0]
    struct.pack_into("<I", b, 128, UNORM.get(fmt, fmt))
    struct.pack_into("<I", b, 28, 1)  # top mip only for the decoder
    im = Image.open(io.BytesIO(bytes(b))).convert("RGBA")
    w, h = im.size
    scale = min(1.0, RGBA_TEX / float(max(w, h)))
    if scale < 1.0:
        im = im.resize((max(4, int(w * scale)), max(4, int(h * scale))), Image.LANCZOS)
    w, h = im.size
    hdr = struct.pack("<4sIIIIIII44sII4s" + "I" * 15, b"DDS ", 124, 0x1 | 0x2 | 0x4 | 0x8 | 0x1000,
                      h, w, w * 4, 1, 1, bytes(44), 32, 0x4, b"DX10", 0, 0, 0, 0, 0,
                      0x1000, 0, 0, 0, 0, 28, 3, 0, 1, 0)
    return hdr + im.tobytes()


SRGB = {72, 75, 78, 99, 29, 91, 93}


def kimg(name, fmt, w, h, levels, flags, data):
    nb = name.encode()
    return (struct.pack("<II", 0x474D494B, 1) + struct.pack("<H", len(nb)) + nb +
            struct.pack("<IIIIII", fmt, w, h, levels, flags, len(data)) + data)


def dds_to_kimg(name, dds):
    """Keep the BO3 block-compressed chain; flags as stock loaded IW7 images:
    NOPICMIP, plus GAMMA_SRGB for sRGB formats (NOMIPMAPS for single level)."""
    h, w = struct.unpack_from("<II", dds, 12)
    levels = struct.unpack_from("<I", dds, 28)[0]
    fmt = struct.unpack_from("<I", dds, 128)[0]
    flags = 0x1 | (0x100 if fmt in SRGB else 0) | (0x2 if levels <= 1 else 0)
    # Stock IW7 images never use *_SRGB DXGI formats: they keep the UNORM format
    # and mark gamma with IMG_DISK_FLAG_GAMMA_SRGB (sRGB formats fail creation).
    return kimg(name, UNORM.get(fmt, fmt), w, h, levels, flags, bytes(dds[148:]))


def encode_n(v):
    """Packed unit vector: three 10-bit fields, floor((c + 1) * 1023 / 2 + 0.5),
    as in stock IW7 surfaces (-1 -> 0, +1 -> 1023). Callers add the top bits."""
    l = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) or 1.0
    out = 0
    for k in range(3):
        c = max(-1.0, min(1.0, v[k] / l))
        out |= int(math.floor((c + 1.0) * 0.5 * 1023.0 + 0.5)) << (10 * k)
    return out


def decode_n(u):
    v = [(((u >> (10 * k)) & 1023) - 512) / 511.0 for k in range(3)]
    l = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / l for x in v]


def half(h):
    s = -1.0 if h & 0x8000 else 1.0
    e = (h >> 10) & 31
    m = h & 1023
    if e == 0:
        return s * m * 2.0 ** -24
    if e == 31:
        return 0.0
    return s * (1 + m / 1024.0) * 2.0 ** (e - 15)


class Chunk:
    def __init__(self):
        self.mats = collections.OrderedDict()

    def add(self, mat, tri):
        surfs = self.mats.setdefault(mat, [[[], {}]])
        cur = surfs[-1]
        if len(cur[0]) + 3 > MAX_SURF_VERTS:
            cur = [[], {}]
            surfs.append(cur)
        cur[0].extend(tri)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", required=True)
    ap.add_argument("--zone-dir", required=True)
    ap.add_argument("--template", required=True, help="authored material source root (materials/techsets)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--margin", type=float, default=700.0)
    ap.add_argument("--limit-cells", default="")
    ap.add_argument("--no-props", action="store_true")
    ap.add_argument("--only-up", action="store_true")
    ap.add_argument("--only-mat", default="", help="substring filter on the IW7 material name")
    ap.add_argument("--one-cell", action="store_true", help="group all geometry by material (fewer rendered surfaces)")
    ap.add_argument("--anchor", default="", help="BO3-space x,y,z shared model origin (lighting anchor)")
    a = ap.parse_args()
    E = a.export
    os.makedirs(a.out, exist_ok=False)
    w = json.load(open(os.path.join(E, "world.json")))
    meta = json.load(open(os.path.join(E, "assets_meta.json")))
    pn = json.load(open(os.path.join(E, "pathnodes.json")))
    lo = [min(n["origin"][i] for n in pn) - a.margin for i in range(3)]
    hi = [max(n["origin"][i] for n in pn) + a.margin for i in range(3)]
    hi[2] += 600.0
    inside = lambda p: all(lo[i] <= p[i] <= hi[i] for i in range(3))
    mats = {m["name"]: m for m in meta["materials"]}
    imgs = {i.get("name"): i for i in meta["images"] if i.get("name")}
    xs = t7_xpak.XPakSet(a.zone_dir)

    # Material translation: BO3 material -> IW7 material backed by its color map.
    mat_map, mat_full, image_jobs, stats = {}, {}, {}, collections.Counter()

    def iw7_material(name):
        if name in mat_map:
            return mat_map[name]
        if a.only_mat:
            res = iw7_material_full(name)
            mat_map[name] = res if (res and a.only_mat in res) else None
            return mat_map[name]
        return iw7_material_full(name)

    def iw7_material_full(name):
        if name in mat_full:
            return mat_full[name]
        res = None
        m = mats.get(name)
        # Blend surfaces (floors, rubble) use a decal-reveal technique but are real
        # geometry; render their first color layer opaque. Overlay decals stay out.
        tech_skip = SKIP_MAT.search(m.get("techset", "")) if m else None
        if m and not SKIP_MAT.search(name) and (not tech_skip or "blend" in name):
            color = next((s["image"] for s in m["images"] if s["semantic_hash"] == COLOR and s["image"]), None)
            if color and color in imgs:
                # One IW7 material per color image keeps the rendered surface
                # count low; images without streamed data share one gray material.
                im = imgs[color]
                if im.get("streamed_parts") and im.get("dxgi_format") in BLOCK:
                    res = "kino_t_" + sanitize(color)
                    image_jobs[res] = color
                else:
                    res = "kino_t_fallback"
                    image_jobs[res] = None
        mat_full[name] = res
        mat_map.setdefault(name, res)
        return res

    chunks = collections.defaultdict(Chunk)
    cell_of = (lambda p: (0, 0)) if a.one_cell else (lambda p: (int(math.floor(p[0] / CELL)), int(math.floor(p[1] / CELL))))

    # World BSP surfaces.
    pos = array.array("f"); pos.frombytes(open(os.path.join(E, "world_positions.f32"), "rb").read())
    vdat = open(os.path.join(E, "world_vertexdata.bin"), "rb").read()
    idx = array.array("H"); idx.frombytes(open(os.path.join(E, "world_indices.u16"), "rb").read())

    def wvert(i):
        col, u, v, n, t = struct.unpack_from("<IffII", vdat, i * 20)
        return (pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2]), decode_n(n), decode_n(t), t >> 30, (u, v), col

    for s in w["surfaces"]:
        mat = iw7_material(s["material"])
        if not mat:
            stats["world_tris_skipped_material"] += s["face_count"]
            continue
        base = s["vertex_buffer_offset"] // 12
        for f in range(s["face_count"]):
            ids = [idx[s["face_index"] + f * 3 + k] + base for k in WIND]
            if len(set(ids)) < 3:
                continue
            vs = [wvert(i) for i in ids]
            if a.only_up and vs[0][1][2] < 0.7:
                continue
            c = [sum(v[0][k] for v in vs) / 3 for k in range(3)]
            if not inside(c):
                stats["world_tris_outside"] += 1
                continue
            chunks[cell_of(c)].add(mat, vs)
            stats["world_tris"] += 1

    # Static models, baked as instances.
    meshes = meta["meshes"]
    blob_cache = {}
    props_index = json.load(open(os.path.join(E, "props", "props.json")))["models"]
    props_blob = open(os.path.join(E, "props", "props.bin"), "rb").read()

    def prop_surfaces(name):
        if name in blob_cache:
            return blob_cache[name]
        m = meshes.get(name)
        out = []
        resident = props_index.get(name)
        data = None
        if m and "surfaces" in m and m["xpak"]["key"] != "0000000000000000":
            data = xs.get(m["xpak"]["key"])
        if m and "surfaces" in m:
            for k, s in enumerate(m["surfaces"]):
                if s["flags"] & 0x2:
                    continue  # skinned
                mat = iw7_material(m["materials"][k]) if k < len(m["materials"]) else None
                if not mat:
                    continue
                sh = s["shared"]
                vc, tc = s["verts"], s["tris"]
                if data is not None and len(data) == sh["data_size"]:
                    p = struct.unpack_from("<%df" % (vc * 3), data, sh["pos_offset"] + s["base_vert"] * 12)
                    att = data[sh["verts_offset"] + s["base_vert"] * 16: sh["verts_offset"] + (s["base_vert"] + vc) * 16]
                    ii = struct.unpack_from("<%dH" % (tc * 3), data, sh["indices_offset"] + s["base_index"] * 2)
                elif resident and k < len(resident) and resident[k]["verts"] == vc and resident[k]["tris"] == tc:
                    o0 = resident[k]["offset"]
                    p = struct.unpack_from("<%df" % (vc * 3), props_blob, o0)
                    att = props_blob[o0 + vc * 12: o0 + vc * 28]
                    ii = struct.unpack_from("<%dH" % (tc * 3), props_blob, o0 + vc * 28)
                else:
                    continue
                verts = []
                for v in range(vc):
                    col, uu, vv, n, tg = struct.unpack_from("<IHHII", att, v * 16)
                    verts.append(((p[v * 3], p[v * 3 + 1], p[v * 3 + 2]), decode_n(n), decode_n(tg), tg >> 30, (half(uu), half(vv)), col))
                out.append((mat, verts, ii))
        blob_cache[name] = out
        return out

    for sm in ([] if a.no_props else w["static_models"]):
        if not sm["model"] or sm["model"].startswith("*") or not inside(sm["origin"]):
            continue
        surfs = prop_surfaces(sm["model"])
        if not surfs:
            stats["prop_instances_unbuilt"] += 1
            continue
        o, m, sc = sm["origin"], sm["axis"], sm["scale"]
        cell = cell_of(o)
        for mat, verts, ii in surfs:
            tv = []
            for (p, n, tg, ts, uv, col) in verts:
                wp = tuple(o[j] + sc * (p[0] * m[j] + p[1] * m[3 + j] + p[2] * m[6 + j]) for j in range(3))
                wn = [n[0] * m[j] + n[1] * m[3 + j] + n[2] * m[6 + j] for j in range(3)]
                wt = [tg[0] * m[j] + tg[1] * m[3 + j] + tg[2] * m[6 + j] for j in range(3)]
                tv.append((wp, wn, wt, ts, uv, col))
            for t in range(len(ii) // 3):
                a0, a1, a2 = (ii[t * 3 + k] for k in WIND)
                if len({a0, a1, a2}) < 3:
                    continue
                chunks[cell].add(mat, [tv[a0], tv[a1], tv[a2]])
                stats["prop_tris"] += 1
        stats["prop_instances"] += 1

    # Write chunk meshes (vertex dedup per surface).
    kdir = os.path.join(a.out, "kmsh"); os.makedirs(kdir)
    layout = {"schema": "kino.layout/1", "region": {"lo": lo, "hi": hi}, "chunks": []}
    limit = set(a.limit_cells.split(",")) if a.limit_cells else None
    model_names = []
    for (cx, cy), ch in sorted(chunks.items()):
        key = "%d_%d" % (cx, cy)
        if limit and key not in limit:
            continue
        center = [(cx + 0.5) * CELL, (cy + 0.5) * CELL, 0.0]
        if a.anchor:
            center = [float(v) for v in a.anchor.split(",")]
        surfaces = []
        for mat, parts in ch.mats.items():
            for tris, _ in parts:
                remap, P, N, U, C, I = {}, [], [], [], [], []
                for (p, n, tg, ts, uv, col) in tris:
                    pn, pt = encode_n(n) | 0xC0000000, encode_n(tg) | (ts << 30)  # IW7 normals always carry top bits 11
                    kk = (p, uv, pn, pt)
                    if kk not in remap:
                        remap[kk] = len(P) // 3
                        P += [p[0] - center[0], p[1] - center[1], p[2] - center[2]]; N += [pn, pt]; U += [uv[0], uv[1]]; C.append(col)
                    I.append(remap[kk])
                surfaces.append((mat, P, N, U, C, I))
        for part in range(0, len(surfaces), MAX_SURFS_PER_MODEL):
            name = "kino_c_%s_%d" % (key.replace("-", "m"), part // MAX_SURFS_PER_MODEL)
            with open(os.path.join(kdir, name + ".kmsh"), "wb") as f:
                f.write(struct.pack("<II", 0x48534D4B, 2))
                nb = name.encode(); f.write(struct.pack("<H", len(nb)) + nb)
                group = surfaces[part:part + MAX_SURFS_PER_MODEL]
                f.write(struct.pack("<I", len(group)))
                for mat, P, N, U, C, I in group:
                    mb = mat.encode(); f.write(struct.pack("<H", len(mb)) + mb)
                    f.write(struct.pack("<II", len(C), len(I) // 3))
                    f.write(struct.pack("<%df" % len(P), *P)); f.write(struct.pack("<%dI" % len(N), *N))
                    f.write(struct.pack("<%df" % len(U), *U)); f.write(struct.pack("<%dI" % len(C), *C))
                    f.write(struct.pack("<%dH" % len(I), *I))
            model_names.append(name)
            layout["chunks"].append({"model": name, "cell": [cx, cy], "origin": center,
                                     "materials": sorted({s[0] for s in surfaces[part:part + MAX_SURFS_PER_MODEL]})})

    # Images and materials for the materials actually used by written chunks.
    used = sorted({m for c in layout["chunks"] for m in c["materials"]})
    for d in ("images", "materials", "techsets", "zone_source", "netconststrings"):
        os.makedirs(os.path.join(a.out, d))
    tmpl = json.load(open(os.path.join(a.template, "materials", "sdk_author_platform_material.json")))
    tech_root = os.path.join(a.template, "techsets")
    tech_files = [(os.path.relpath(dp, tech_root), fn) for dp, _, fs in os.walk(tech_root) for fn in fs]
    images_written, fallback = {}, []
    csv = ["ignore,kino_recipient", "image,kino_fallback_gray"]
    gray = struct.pack("<HHI", 0x8410, 0x8410, 0)  # one BC1 block, mid gray
    open(os.path.join(a.out, "images", "kino_fallback_gray.kimg"), "wb").write(
        kimg("kino_fallback_gray", 28, 4, 4, 1, 0x1 | 0x2, bytes([128, 128, 128, 255]) * 16))
    for mat in used:
        bo3img = image_jobs[mat]
        iname = "kino_" + sanitize(bo3img) if bo3img else "kino_fallback_gray"
        if bo3img is None:
            images_written[iname] = False
        if iname not in images_written:
            dds = build_dds(imgs[bo3img], xs)
            images_written[iname] = dds is not None
            if dds:
                open(os.path.join(a.out, "images", iname + ".kimg"), "wb").write(dds_to_kimg(iname, dds))
                csv.append("image," + iname)
        m = json.loads(json.dumps(tmpl))
        # Color slot = the colorMap type hash entry of the template material.
        slot = next(t for t in m["textureTable"] if t["typeHash"] == 2695565377)
        if images_written[iname]:
            slot["image"] = iname
        else:
            slot["image"] = "kino_fallback_gray"
            fallback.append(mat)
        json.dump(m, open(os.path.join(a.out, "materials", mat.replace("/", "_") + ".json"), "w"), indent=2)
        for rel, fn in tech_files:
            ext = os.path.splitext(fn)[1]
            dst = os.path.join(a.out, "techsets", rel)
            os.makedirs(dst, exist_ok=True)
            shutil.copyfile(os.path.join(tech_root, rel, fn), os.path.join(dst, mat.replace("/", "_") + ext))
        csv.append("material," + mat)
    for n in model_names:
        csv.append("xmodel," + n)
    csv.append("netconststrings,ncs_mdl_kino")
    open(os.path.join(a.out, "zone_source", "kino.csv"), "w", newline="\n").write("\n".join(csv) + "\n")
    shutil.copyfile(os.path.join(a.template, "zone_source", "sdk_author_platform_recipient.csv"),
                    os.path.join(a.out, "zone_source", "kino_recipient.csv"))
    json.dump({"stringType": 0, "sourceType": 2, "stringList": model_names},
              open(os.path.join(a.out, "netconststrings", "ncs_mdl_kino.json"), "w"), indent=2)
    layout["stats"] = dict(stats)
    layout["materials"] = len(used); layout["images"] = sum(images_written.values()); layout["fallback_materials"] = fallback
    json.dump(layout, open(os.path.join(a.out, "layout.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in layout.items() if k not in ("chunks", "fallback_materials")}, indent=1))
    print("chunks", len(layout["chunks"]), "fallback", len(fallback))


if __name__ == "__main__":
    main()

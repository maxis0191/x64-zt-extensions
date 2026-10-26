"""World-space LOD0 triangles of collidable BO3 static models.

BO3 stairs, railings and furniture collide through their static-model
collision, which is absent from the clip brushes and triangle soup. The render
LOD0 approximates it. Mesh data comes from the same sources as kino_compose:
resident props (props/props.bin) or the streamed xpak mesh entry.
"""
import json, os, struct
import numpy as np
import t7_xpak


def collidable_instances(E):
    """world.json static models whose clip entry has player/AI-blocking contents."""
    clip = json.load(open(os.path.join(E, "clip.json")))["static_models"]
    key = lambda m, o: (m, round(o[0], 1), round(o[1], 1), round(o[2], 1))
    # Clutter under 32 units (cans, papers, bricks) only adds floor bumps.
    solid = {key(s["model"], s["origin"]) for s in clip if s["contents"] & 0x10001
             and max(np.subtract(s["absmax"], s["absmin"])) >= 32}
    world = json.load(open(os.path.join(E, "world.json")))["static_models"]
    return [sm for sm in world if sm["model"] and not sm["model"].startswith("*") and key(sm["model"], sm["origin"]) in solid]


def mesh_loader(E, zone_dir):
    meta = json.load(open(os.path.join(E, "assets_meta.json")))["meshes"]
    resident = json.load(open(os.path.join(E, "props", "props.json")))["models"]
    blob = open(os.path.join(E, "props", "props.bin"), "rb").read()
    xs = t7_xpak.XPakSet(zone_dir) if zone_dir else None
    cache = {}

    def load(name):
        if name in cache:
            return cache[name]
        out = []
        m = meta.get(name)
        data = None
        if xs and m and "surfaces" in m and m["xpak"]["key"] != "0000000000000000":
            data = xs.get(m["xpak"]["key"])
        if m and "surfaces" in m:
            res = resident.get(name)
            for k, s in enumerate(m["surfaces"]):
                if s["flags"] & 0x2:
                    continue  # skinned
                sh, vc, tc = s["shared"], s["verts"], s["tris"]
                if data is not None and len(data) == sh["data_size"]:
                    p = struct.unpack_from("<%df" % (vc * 3), data, sh["pos_offset"] + s["base_vert"] * 12)
                    ii = struct.unpack_from("<%dH" % (tc * 3), data, sh["indices_offset"] + s["base_index"] * 2)
                elif res and k < len(res) and res[k]["verts"] == vc and res[k]["tris"] == tc:
                    o0 = res[k]["offset"]
                    p = struct.unpack_from("<%df" % (vc * 3), blob, o0)
                    ii = struct.unpack_from("<%dH" % (tc * 3), blob, o0 + vc * 28)
                else:
                    continue
                out.append((np.array(p, dtype=np.float64).reshape(-1, 3), np.array(ii, dtype=np.int64).reshape(-1, 3)))
        cache[name] = out
        return out
    return load


def prop_triangles(E, zone_dir):
    """(A, B, C) world triangles of every collidable static-model instance."""
    load = mesh_loader(E, zone_dir)
    tris = []
    for sm in collidable_instances(E):
        o = np.array(sm["origin"]); ax = np.array(sm["axis"]).reshape(3, 3); sc = sm["scale"]
        for P, I in load(sm["model"]):
            W = o + sc * (P @ ax)
            tris.append(W[I])
    if not tris:
        z = np.zeros((0, 3))
        return z, z, z
    T = np.concatenate(tris)
    return T[:, 0], T[:, 1], T[:, 2]

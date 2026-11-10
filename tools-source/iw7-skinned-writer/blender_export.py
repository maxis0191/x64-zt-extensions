"""Blender (headless) exporter: skinned meshes -> intermediate JSON for build_model.py.

blender -b --factory-startup [<file.blend>] -P blender_export.py -- --out <mesh.json>
        [--glb <in.glb>]                 import a glb first (GrayWolf/Greyhound hero export)
        [--modify <expr>]                optional test edit after import, e.g. "offset:zmb_hero_jock_jacket:0.5"
                                         (move verts of objects whose material matches along their normal by N inches)
        [--objects a,b]                  restrict to these mesh objects (default: all meshes bound to an armature)
        [--unit 0.0254]                  Blender metres per IW7 unit (glb hero import: 1 in = 0.0254 m)

Space: a Greyhound glb imported by Blender lands in IW7 axes (x fwd, y left, z up) at 0.0254 m per inch, so the
exporter writes world-space positions / normals / tangents divided by --unit. Bone rest heads are exported too so the
writer can verify the armature still matches the stock skeleton.

Per output surface (one per (object, material slot)): vertices split by loop attributes (position, normal, uv,
tangent sign), up to 8 raw influences (writer clamps to 4), triangles in Blender winding (CCW).
"""
import json
import sys

import bmesh
import bpy
from mathutils import Vector


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = {"out": None, "glb": None, "modify": [], "objects": None, "unit": 0.0254, "decimate": 1.0}
    i = 0
    while i < len(a):
        k = a[i]
        if k == "--out":
            o["out"] = a[i + 1]
        elif k == "--glb":
            o["glb"] = a[i + 1]
        elif k == "--modify":
            o["modify"].append(a[i + 1])
        elif k == "--objects":
            o["objects"] = a[i + 1].split(",")
        elif k == "--unit":
            o["unit"] = float(a[i + 1])
        elif k == "--decimate":
            o["decimate"] = float(a[i + 1])
        i += 2
    return o


def armature_of(ob):
    for md in ob.modifiers:
        if md.type == "ARMATURE" and md.object:
            return md.object
    return ob.parent if ob.parent and ob.parent.type == "ARMATURE" else None


def apply_modify(spec, unit):
    kind, mat, amount = spec.split(":")
    amount = float(amount) * unit
    n = 0
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        slots = [s.material.name if s.material else "" for s in ob.material_slots]
        if not any(mat in s for s in slots):
            continue
        me = ob.data
        idx = {i for i, s in enumerate(slots) if mat in s}
        verts = set()
        for p in me.polygons:
            if p.material_index in idx:
                verts.update(p.vertices)
        if kind == "offset":
            # offset along the (custom) corner normals averaged per vertex: seam duplicates of the imported mesh carry
            # the same custom normal, so they move together (no cracks)
            acc = {}
            for li, loop in enumerate(me.loops):
                if loop.vertex_index in verts:
                    acc[loop.vertex_index] = acc.get(loop.vertex_index, Vector()) + me.corner_normals[li].vector
            for vi in verts:
                v = me.vertices[vi]
                nrm = acc.get(vi, v.normal).normalized()
                v.co = v.co + nrm * (amount / max(ob.matrix_world.to_scale()[0], 1e-9))
        elif kind == "scale":
            c = sum((me.vertices[vi].co for vi in verts), Vector()) / max(len(verts), 1)
            for vi in verts:
                v = me.vertices[vi]
                v.co = c + (v.co - c) * float(spec.split(":")[2])
        n += len(verts)
        me.update()
    return n


def export_object(ob, unit, decimate=1.0):
    arm = armature_of(ob)
    # rest-pose mesh data (apply any non-armature modifiers in Blender before exporting)
    if decimate < 1.0:
        # LOD: collapse-decimated rest-pose copy (vertex groups interpolated by the modifier)
        arms = [(md, md.show_viewport) for md in ob.modifiers if md.type == "ARMATURE"]
        for md, _ in arms:
            md.show_viewport = False
        dec = ob.modifiers.new("iw7_lod_decimate", "DECIMATE")
        dec.ratio = decimate
        dec.use_collapse_triangulate = True
        deps = bpy.context.evaluated_depsgraph_get()
        deps.update()
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(deps), preserve_all_data_layers=True, depsgraph=deps)
        ob.modifiers.remove(dec)
        for md, s in arms:
            md.show_viewport = s
    else:
        me = ob.data.copy()
    if any(len(p.vertices) != 3 for p in me.polygons):
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bm.to_mesh(me)
        bm.free()
    uv = me.uv_layers.active
    has_uv = uv is not None
    uvs = [0.0] * (2 * len(me.loops))
    if has_uv:
        uv.uv.foreach_get("vector", uvs)  # read before calc_tangents (it can reallocate corner layers)
        me.calc_tangents(uvmap=uv.name)
    mw = ob.matrix_world
    nw = mw.to_3x3().inverted().transposed()
    groups = {g.index: g.name for g in ob.vertex_groups}
    bone_names = set(arm.data.bones.keys()) if arm else set()
    surfaces = {}
    corner_normals = me.corner_normals if hasattr(me, "corner_normals") else None
    for poly in me.polygons:
        mi = poly.material_index
        mat = ob.material_slots[mi].material.name if mi < len(ob.material_slots) and ob.material_slots[mi].material else "default"
        surf = surfaces.setdefault(mi, {"object": ob.name, "material": mat, "verts": [], "tris": [], "_key": {}})
        tri = []
        for li in poly.loop_indices:
            loop = me.loops[li]
            v = me.vertices[loop.vertex_index]
            p = mw @ v.co
            n = (nw @ (corner_normals[li].vector if corner_normals else loop.normal)).normalized()
            if has_uv:
                t = (mw.to_3x3() @ loop.tangent).normalized()
                sign = loop.bitangent_sign
                u, vv = uvs[2 * li], uvs[2 * li + 1]
            else:
                t, sign, u, vv = Vector((1, 0, 0)), 1.0, 0.0, 0.0
            w = sorted(((groups[g.group], g.weight) for g in v.groups
                        if g.group in groups and g.weight > 1e-6 and (not bone_names or groups[g.group] in bone_names)),
                       key=lambda x: -x[1])
            # split a vertex only when uv / tangent sign differ or the normals really differ (custom normal storage
            # in Blender jitters by ~1e-3, which must not split the stock seams)
            key = (loop.vertex_index, round(u, 6), round(vv, 6), sign)
            k = None
            for kk, nn in surf["_key"].get(key, []):
                if nn.dot(n) > 0.9995:
                    k = kk
                    break
            if k is None:
                k = len(surf["verts"])
                surf["_key"].setdefault(key, []).append((k, n.copy()))
                surf["verts"].append({
                    "p": [c / unit for c in p], "n": list(n), "t": list(t), "s": sign,
                    # Blender UV origin is bottom-left; IW7/glTF origin top-left
                    "uv": [u, 1.0 - vv], "w": [[b, round(x, 7)] for b, x in w[:8]], "src": loop.vertex_index})
            tri.append(k)
        surf["tris"].append(tri)
    bpy.data.meshes.remove(me)
    out = []
    for mi in sorted(surfaces):
        s = surfaces[mi]
        del s["_key"]
        # deterministic order: by source mesh vertex (keeps the stock vertex order for imported stock meshes)
        order = sorted(range(len(s["verts"])), key=lambda i: (s["verts"][i]["src"], i))
        remap = {o: n for n, o in enumerate(order)}
        s["verts"] = [s["verts"][i] for i in order]
        s["tris"] = [[remap[k] for k in t] for t in s["tris"]]
        out.append(s)
    return arm, out


def main():
    o = args()
    if o["glb"]:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=o["glb"])
    modified = {m: apply_modify(m, o["unit"]) for m in o["modify"]}
    meshes = [ob for ob in bpy.data.objects if ob.type == "MESH" and armature_of(ob)
              and (o["objects"] is None or ob.name in o["objects"])]
    result = {"schema": "iw7-skinned-writer/blender-1", "unit": o["unit"], "modified": modified, "surfaces": [],
              "armature": None}
    arm = None
    for ob in meshes:
        a, surfs = export_object(ob, o["unit"], o["decimate"])
        arm = arm or a
        result["surfaces"] += surfs
    if arm:
        result["armature"] = {"name": arm.name, "bones": [
            {"name": b.name, "parent": b.parent.name if b.parent else None,
             "head": [c / o["unit"] for c in (arm.matrix_world @ b.head_local)]} for b in arm.data.bones]}
    json.dump(result, open(o["out"], "w"))
    print("EXPORT_OK surfaces=%d verts=%d tris=%d modified=%s" % (
        len(result["surfaces"]), sum(len(s["verts"]) for s in result["surfaces"]),
        sum(len(s["tris"]) for s in result["surfaces"]), modified))


main()

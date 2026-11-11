"""Generic Blender helpers for original weapons built on a stock donor skeleton (Blender 4.5, headless).

A weapon generator (e.g. exact_change_gun.py) imports this module, builds its parts with the shape helpers, gives
each part a bone (vertex group), an atlas and a look material, then calls `finish(...)`, which:

  1. unwraps every atlas (UV1 "uv", one shared texture per atlas) and adds the camo UV layer "camo"
     (UV1 scaled to a fixed camo density in UV units per inch, so the camo basis is the identity);
  2. bakes per atlas, with Cycles, from the look materials: albedo (linear), params (R roughness, G metalness,
     B mask: camo mask for camo atlases, opacity for blend atlases), tangent-space normal (OpenGL), ambient occlusion;
     the arrays are saved as float16 .npy, top row first (IW7 / glTF UV origin);
  3. adds the copies made after the bake (parts sharing one UV island: tokens, magazine twins);
  4. assigns one export material per atlas (named after the atlas key), joins parts per (bone, atlas) and saves the
     .blend that tools-source/iw7-skinned-writer/blender_export.py --all-meshes --uv2 camo --unit 1 reads;
  5. renders a 3/4 preview with the baked maps.

Units: 1 Blender unit = 1 inch, axes of the donor model (x forward, y left, z up). Every object keeps an identity
transform: geometry is written in model space.

Look material contract (what the bake reads): a material made by `look_material(name, build)` holds the nodes
"CH_albedo" (colour output 0), "CH_rough", "CH_metal", "CH_mask" (value output 0) and a Principled BSDF named
"BSDF" whose Normal input carries the bump. `build(nodes, links, ctx)` returns those sockets.
"""
import json
import math
import os
import random
import time

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

STATE = {"parts": [], "after_bake": [], "cutters": []}


# ------------------------------------------------------------------ scene
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "NONE"
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for kind in ("OPTIX", "CUDA"):
            try:
                prefs.compute_device_type = kind
                prefs.get_devices()
                if any(d.type == kind for d in prefs.devices):
                    for d in prefs.devices:
                        d.use = d.type == kind
                    sc.cycles.device = "GPU"
                    break
            except TypeError:
                continue
    except KeyError:
        pass
    STATE["parts"].clear()
    STATE["after_bake"].clear()
    STATE["cutters"].clear()
    return sc


def _link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _mesh_object(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = _link(bpy.data.objects.new(name, me))
    return ob


# ------------------------------------------------------------------ shapes (model space, inches)
def box(name, lo, hi):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector([lo[i] + (hi[i] - lo[i]) * (v.co[i] + 0.5) for i in range(3)])
    return _mesh_object(name, bm)


def prism(name, pts, d0, d1, plane="xz"):
    """Polygon pts (2D, counter-clockwise seen from +normal) in plane 'xz' (extruded along y from d0 to d1),
    'xy' (along z) or 'yz' (along x)."""
    axes = {"xz": (0, 2, 1), "xy": (0, 1, 2), "yz": (1, 2, 0)}[plane]
    bm = bmesh.new()

    def co(p, d):
        c = [0.0, 0.0, 0.0]
        c[axes[0]], c[axes[1]], c[axes[2]] = p[0], p[1], d
        return Vector(c)

    bottom = [bm.verts.new(co(p, d0)) for p in pts]
    top = [bm.verts.new(co(p, d1)) for p in pts]
    bm.faces.new(bottom)
    bm.faces.new(list(reversed(top)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([bottom[i], top[i], top[j], bottom[j]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return _mesh_object(name, bm)


def cylinder(name, center, axis, radius, length, segs=24, radius2=None):
    """Closed cylinder (cone when radius2) along axis 'x'|'y'|'z', centred on center."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=radius,
                          radius2=radius if radius2 is None else radius2, depth=length)
    rot = {"x": Matrix.Rotation(math.pi / 2, 4, "Y"), "y": Matrix.Rotation(-math.pi / 2, 4, "X"),
           "z": Matrix.Identity(4)}[axis]
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(center)) @ rot, verts=bm.verts[:])
    return _mesh_object(name, bm)


def tube(name, center, axis, r_out, r_in, length, segs=32):
    """Hollow tube (open ring caps) along axis."""
    bm = bmesh.new()
    rings = []
    for r in (r_out, r_in):
        for z in (-length / 2, length / 2):
            ring = []
            for k in range(segs):
                a = 2 * math.pi * k / segs
                ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
            rings.append(ring)
    o0, o1, i0, i1 = rings
    for k in range(segs):
        j = (k + 1) % segs
        bm.faces.new([o0[k], o0[j], o1[j], o1[k]])          # outer wall
        bm.faces.new([i0[k], i1[k], i1[j], i0[j]])          # inner wall
        bm.faces.new([o1[k], o1[j], i1[j], i1[k]])          # front ring
        bm.faces.new([o0[k], i0[k], i0[j], o0[j]])          # back ring
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    rot = {"x": Matrix.Rotation(math.pi / 2, 4, "Y"), "y": Matrix.Rotation(-math.pi / 2, 4, "X"),
           "z": Matrix.Identity(4)}[axis]
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(center)) @ rot, verts=bm.verts[:])
    return _mesh_object(name, bm)


def ribbed_cylinder(name, center, axis, radius, length, pitch, groove=0.03, segs=16):
    """A stack of coins seen from the side: a cylinder whose radius dips at every coin seam."""
    n = max(1, int(round(length / pitch)))
    prof = []
    for k in range(n + 1):
        z = -length / 2 + k * length / n
        if 0 < k < n:
            prof += [(radius, z - 0.012), (radius - groove, z), (radius, z + 0.012)]
        else:
            prof.append((radius, z))
    bm = bmesh.new()
    rings = []
    for r, z in prof:
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * s / segs), r * math.sin(2 * math.pi * s / segs), z))
                      for s in range(segs)])
    for a, b in zip(rings, rings[1:]):
        for s in range(segs):
            t = (s + 1) % segs
            bm.faces.new([a[s], a[t], b[t], b[s]])
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    rot = {"x": Matrix.Rotation(math.pi / 2, 4, "Y"), "y": Matrix.Rotation(-math.pi / 2, 4, "X"),
           "z": Matrix.Identity(4)}[axis]
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(center)) @ rot, verts=bm.verts[:])
    return _mesh_object(name, bm)


def dome(name, center, normal, radius, height=None, segs=10):
    """Rivet / screw head: a half sphere (flattened to height) sitting on the plane through center. Built ring by
    ring (bmesh remove_doubles merged the clamped sphere in a different vertex order on every run)."""
    bm = bmesh.new()
    h = (height or radius) / radius
    rings = max(2, segs // 4)
    verts = []
    for r in range(rings):
        a = (math.pi / 2) * r / rings
        verts.append([bm.verts.new((radius * math.cos(a) * math.cos(2 * math.pi * k / segs),
                                    radius * math.cos(a) * math.sin(2 * math.pi * k / segs),
                                    radius * math.sin(a) * h)) for k in range(segs)])
    top = bm.verts.new((0.0, 0.0, radius * h))
    for lo, hi in zip(verts, verts[1:]):
        for k in range(segs):
            j = (k + 1) % segs
            bm.faces.new([lo[k], lo[j], hi[j], hi[k]])
    for k in range(segs):
        bm.faces.new([verts[-1][k], verts[-1][(k + 1) % segs], top])
    bm.faces.new(list(reversed(verts[0])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    rot = Vector((0, 0, 1)).rotation_difference(Vector(normal)).to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(center)) @ rot, verts=bm.verts[:])
    return _mesh_object(name, bm)


def curve_tube(name, points, radius, closed=False, resolution=6, bevel_resolution=4):
    """A round bar along a smooth path (Bezier with automatic handles), capped."""
    cu = bpy.data.curves.new(name + "_crv", "CURVE")
    cu.dimensions = "3D"
    cu.resolution_u = resolution
    cu.bevel_depth = radius
    cu.bevel_resolution = bevel_resolution
    cu.use_fill_caps = True
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(points) - 1)
    for bp, p in zip(sp.bezier_points, points):
        bp.co = Vector(p)
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    sp.use_cyclic_u = closed
    tmp = _link(bpy.data.objects.new(name + "_tmp", cu))
    ob = to_mesh(tmp, name)
    return ob


def text(name, body, size, center, right, up, depth, bold=0.0):
    """Raised lettering: text in the plane spanned by right/up, extruded depth along right x up, centred."""
    cu = bpy.data.curves.new(name + "_txt", "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = depth / 2
    cu.offset = bold
    cu.resolution_u = 3
    tmp = _link(bpy.data.objects.new(name + "_tmp", cu))
    r, u = Vector(right).normalized(), Vector(up).normalized()
    n = r.cross(u)
    m = Matrix((r, u, n)).transposed().to_4x4()
    tmp.matrix_world = Matrix.Translation(Vector(center) + n * depth / 2) @ m
    return to_mesh(tmp, name)


def groove(ob, pts, face, depth=0.025, width=0.035, plane="xz", closed=True):
    """Cut a panel seam: a groove of the given width following the 2D polyline pts on the face at coordinate `face`
    (the plane's third axis; positive or negative side), depth into the part."""
    n = len(pts)
    sign = 1.0 if face > 0 else -1.0
    for i in range(n if closed else n - 1):
        p, q = Vector(pts[i]), Vector(pts[(i + 1) % n])
        d = (q - p).normalized()
        nrm = Vector((-d.y, d.x)) * width / 2
        ext = d * width / 2
        quad = [p - ext - nrm, q + ext - nrm, q + ext + nrm, p - ext + nrm]
        c = prism("%s_groove%d" % (ob.name, i), [tuple(v) for v in quad], face - sign * depth, face + sign * 0.2,
                  plane)
        cut(ob, c)
    return ob


def to_mesh(ob, name=None):
    """Evaluate modifiers / curves into a plain mesh object with identity transform (custom normals kept)."""
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    me.transform(ob.matrix_world)
    new = _link(bpy.data.objects.new(name or ob.name, me))
    old_data = ob.data
    bpy.data.objects.remove(ob)
    if isinstance(old_data, bpy.types.Curve):
        bpy.data.curves.remove(old_data)
    return new


def cut(ob, cutter):
    """Boolean difference (exact); the cutter is removed at finish."""
    md = ob.modifiers.new("cut_" + cutter.name, "BOOLEAN")
    md.operation = "DIFFERENCE"
    md.solver = "EXACT"
    md.object = cutter
    cutter.hide_render = True
    cutter.hide_viewport = True
    STATE["cutters"].append(cutter)
    return ob


def bevel(ob, width, segments=2, angle=35.0):
    md = ob.modifiers.new("bevel", "BEVEL")
    md.width = width
    md.segments = segments
    md.limit_method = "ANGLE"
    md.angle_limit = math.radians(angle)
    md.harden_normals = True
    md.miter_outer = "MITER_ARC"
    return ob


def clean(ob, dist=1e-5):
    """Merge coincident vertices and drop degenerate faces (curve caps, boolean slivers): Cycles 4.5 crashed in
    sync_mesh on such meshes (EXCEPTION_ACCESS_VIOLATION while baking)."""
    me = ob.data
    for name in [a.name for a in me.attributes if not a.name.startswith(".") and a.name not in
                 ("position", "sharp_edge", "sharp_face", "material_index")]:
        a = me.attributes.get(name)
        if a is not None and a.domain == "CORNER" and a.data_type == "FLOAT2":
            me.uv_layers.remove(me.uv_layers[name]) if name in me.uv_layers else me.attributes.remove(a)
        elif a is not None:
            me.attributes.remove(a)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=dist)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=dist)
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()


def smooth(ob, angle=35.0):
    me = ob.data
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    if hasattr(me, "set_sharp_from_angle"):
        me.set_sharp_from_angle(angle=math.radians(angle))


def transformed_copy(ob, name, matrix):
    me = ob.data.copy()
    me.transform(matrix)
    return _link(bpy.data.objects.new(name, me))


# ------------------------------------------------------------------ parts
def part(ob, bone, atlas, material, bevel_width=0.0, segments=2, angle=35.0, smooth_angle=35.0):
    """Register a modelled object: bone (vertex group name), atlas key, look material. Applies booleans + bevel."""
    if bevel_width > 0:
        bevel(ob, bevel_width, segments, angle)
    ob.data.polygons.foreach_set("use_smooth", [True] * len(ob.data.polygons))
    if bevel_width <= 0:
        smooth(ob, smooth_angle)
    if ob.modifiers:
        ob = to_mesh(ob)
    if bevel_width <= 0:
        clean(ob)
        smooth(ob, smooth_angle)
    ob.data.materials.clear()
    ob.data.materials.append(material)
    ob["bone"] = bone
    ob["atlas"] = atlas
    STATE["parts"].append(ob)
    return ob


def copy_after_bake(src, name, bone, matrix):
    """A part that shares src's UV island (same texels): created after the bake, from src's final mesh."""
    STATE["after_bake"].append((src, name, bone, matrix))


# ------------------------------------------------------------------ look materials
def look_material(name, build, ctx=None):
    """build(nodes, links, ctx) -> dict(albedo=socket, rough=socket, metal=socket, mask=socket, normal=socket|None)."""
    mat = bpy.data.materials.new("look_" + name)   # never the name of an atlas (export) material
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.name = "OUT"
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.name = "BSDF"
    s = build(nt.nodes, nt.links, ctx or {})
    for key in ("albedo", "rough", "metal", "mask"):
        rr = nt.nodes.new("NodeReroute" if key == "albedo" else "ShaderNodeMath")
        if key != "albedo":
            rr.operation = "ADD"
            rr.inputs[1].default_value = 0.0
            rr.use_clamp = True
        rr.name = "CH_" + key
        nt.links.new(s[key], rr.inputs[0])
    nt.links.new(nt.nodes["CH_albedo"].outputs[0], bsdf.inputs["Base Color"])
    nt.links.new(nt.nodes["CH_rough"].outputs[0], bsdf.inputs["Roughness"])
    nt.links.new(nt.nodes["CH_metal"].outputs[0], bsdf.inputs["Metallic"])
    if s.get("normal") is not None:
        nt.links.new(s["normal"], bsdf.inputs["Normal"])
    nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
    return mat


class N:
    """Small node-graph helpers bound to one material tree."""

    def __init__(self, nodes, links):
        self.n, self.l = nodes, links

    def node(self, kind, **props):
        nd = self.n.new(kind)
        for k, v in props.items():
            setattr(nd, k, v)
        return nd

    def val(self, v):
        nd = self.n.new("ShaderNodeValue")
        nd.outputs[0].default_value = v
        return nd.outputs[0]

    def rgb(self, c):
        nd = self.n.new("ShaderNodeRGB")
        nd.outputs[0].default_value = (c[0], c[1], c[2], 1.0)
        return nd.outputs[0]

    def math(self, op, a, b=None, clamp=False):
        nd = self.n.new("ShaderNodeMath")
        nd.operation = op
        nd.use_clamp = clamp
        for i, x in enumerate((a, b)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                nd.inputs[i].default_value = x
            else:
                self.l.new(x, nd.inputs[i])
        return nd.outputs[0]

    def mix(self, fac, a, b):
        """Colour lerp a -> b by fac."""
        nd = self.n.new("ShaderNodeMix")
        nd.data_type = "RGBA"
        for sock, x in ((nd.inputs[0], fac), (nd.inputs[6], a), (nd.inputs[7], b)):
            if isinstance(x, (int, float)):
                sock.default_value = x
            elif isinstance(x, tuple):
                sock.default_value = (x[0], x[1], x[2], 1.0)
            else:
                self.l.new(x, sock)
        return nd.outputs[2]

    def lerp(self, fac, a, b):
        d = self.math("SUBTRACT", b, a) if not isinstance(b, (int, float)) or not isinstance(a, (int, float)) \
            else self.val(b - a)
        return self.math("ADD", a, self.math("MULTIPLY", fac, d))

    def coords(self, scale=(1, 1, 1)):
        tc = self.n.new("ShaderNodeTexCoord")
        mp = self.n.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = scale
        self.l.new(tc.outputs["Object"], mp.inputs["Vector"])
        return mp.outputs[0]

    def noise(self, scale, detail=4.0, rough=0.55, vec=None, distortion=0.0):
        nd = self.n.new("ShaderNodeTexNoise")
        nd.inputs["Scale"].default_value = scale
        nd.inputs["Detail"].default_value = detail
        nd.inputs["Roughness"].default_value = rough
        nd.inputs["Distortion"].default_value = distortion
        if vec is not None:
            self.l.new(vec, nd.inputs["Vector"])
        return nd.outputs["Fac"]

    def smoothstep(self, x, e0, e1):
        mr = self.n.new("ShaderNodeMapRange")
        mr.interpolation_type = "SMOOTHSTEP"
        mr.inputs["From Min"].default_value = e0
        mr.inputs["From Max"].default_value = e1
        self.l.new(x, mr.inputs["Value"])
        return mr.outputs[0]

    def edge(self, radius, gain):
        """0 on flat faces, toward 1 on convex/concave edges: 1 - dot(bevelled normal, true normal)."""
        bv = self.n.new("ShaderNodeBevel")
        bv.samples = 8
        bv.inputs["Radius"].default_value = radius
        geo = self.n.new("ShaderNodeNewGeometry")
        dp = self.n.new("ShaderNodeVectorMath")
        dp.operation = "DOT_PRODUCT"
        self.l.new(bv.outputs[0], dp.inputs[0])
        self.l.new(geo.outputs["Normal"], dp.inputs[1])
        return self.math("MULTIPLY", self.math("SUBTRACT", 1.0, dp.outputs["Value"]), gain, clamp=True)

    def cavity(self, distance, gain=1.0):
        """0 in the open, toward 1 in crevices (ambient occlusion node)."""
        ao = self.n.new("ShaderNodeAmbientOcclusion")
        ao.samples = 8
        ao.inputs["Distance"].default_value = distance
        return self.math("MULTIPLY", self.math("SUBTRACT", 1.0, ao.outputs["AO"]), gain, clamp=True)

    def bump(self, height, strength, distance=0.02, normal=None):
        b = self.n.new("ShaderNodeBump")
        b.inputs["Strength"].default_value = strength
        b.inputs["Distance"].default_value = distance
        self.l.new(height, b.inputs["Height"])
        if normal is not None:
            self.l.new(normal, b.inputs["Normal"])
        return b.outputs["Normal"]


# ------------------------------------------------------------------ UVs
def _select_only(objs):
    bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode != "OBJECT" else None
    for o in bpy.context.scene.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]


def unwrap_atlas(objs, margin=0.004, angle=55.0):
    for o in objs:
        me = o.data
        while me.uv_layers:
            me.uv_layers.remove(me.uv_layers[0])
        me.uv_layers.new(name="uv")
    _select_only(objs)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, margin=margin)
    bpy.ops.object.mode_set(mode="OBJECT")
    strip_internal(objs)


def strip_internal(objs):
    """Drop the selection layers edit mode leaves (.select_*, .vs.<uv>, .es.<uv>, .pn.<uv>): Cycles 4.5 crashed at
    random in sync_mesh (ustring assignment) on meshes carrying them."""
    for o in objs:
        me = o.data
        for name in [a.name for a in me.attributes if a.name.startswith((".select", ".vs.", ".es.", ".pn."))]:
            try:
                me.attributes.remove(me.attributes[name])
            except RuntimeError:
                pass


def uv_density(objs, layer="uv"):
    """UV units per inch over the given objects (sqrt of UV area / surface area)."""
    a3 = a2 = 0.0
    for o in objs:
        me = o.data
        uv = me.uv_layers[layer].uv
        for p in me.polygons:
            a3 += p.area
            pts = [uv[li].vector for li in p.loop_indices]
            s = 0.0
            for i in range(len(pts)):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % len(pts)]
                s += x0 * y1 - x1 * y0
            a2 += abs(s) / 2
    return math.sqrt(a2 / a3) if a3 else 0.0


def add_camo_uv(objs, density):
    """'camo' layer = 'uv' * k, k = density / measured UV1 density (identity basis in the camo records)."""
    k = density / max(uv_density(objs), 1e-9)
    for o in objs:
        me = o.data
        src = me.uv_layers["uv"]
        cam = me.uv_layers.get("camo") or me.uv_layers.new(name="camo")
        vals = [0.0] * (2 * len(me.loops))
        src.uv.foreach_get("vector", vals)
        cam.uv.foreach_set("vector", [v * k for v in vals])
        me.uv_layers.active = src
        src.active_render = True
    return k


# ------------------------------------------------------------------ bake
def _image(name, size):
    img = bpy.data.images.new(name, size, size, alpha=True, float_buffer=True)
    img.colorspace_settings.name = "Non-Color"
    return img


def _materials_of(objs):
    seen = []
    for o in objs:
        for m in o.data.materials:
            if m and m not in seen:
                seen.append(m)
    return seen


def _set_bake_target(mats, img):
    for m in mats:
        nt = m.node_tree
        nd = nt.nodes.get("BAKE_TARGET") or nt.nodes.new("ShaderNodeTexImage")
        nd.name = "BAKE_TARGET"
        nd.image = img
        nt.nodes.active = nd


def _emit_from(mats, channel):
    """Temporarily drive the output with an emission of one channel (or R/G/B = rough/metal/mask)."""
    saved = []
    for m in mats:
        nt = m.node_tree
        out = nt.nodes["OUT"]
        saved.append((m, [l.from_socket for l in out.inputs["Surface"].links]))
        em = nt.nodes.get("BAKE_EMIT") or nt.nodes.new("ShaderNodeEmission")
        em.name = "BAKE_EMIT"
        em.inputs["Strength"].default_value = 1.0
        if channel == "albedo":
            nt.links.new(nt.nodes["CH_albedo"].outputs[0], em.inputs["Color"])
        else:
            cc = nt.nodes.get("BAKE_COMBINE") or nt.nodes.new("ShaderNodeCombineColor")
            cc.name = "BAKE_COMBINE"
            nt.links.new(nt.nodes["CH_rough"].outputs[0], cc.inputs[0])
            nt.links.new(nt.nodes["CH_metal"].outputs[0], cc.inputs[1])
            nt.links.new(nt.nodes["CH_mask"].outputs[0], cc.inputs[2])
            nt.links.new(cc.outputs[0], em.inputs["Color"])
        nt.links.new(em.outputs[0], out.inputs["Surface"])
    return saved


def _restore(saved):
    for m, socks in saved:
        nt = m.node_tree
        out = nt.nodes["OUT"]
        for l in list(out.inputs["Surface"].links):
            nt.links.remove(l)
        for s in socks:
            nt.links.new(s, out.inputs["Surface"])


def _save(img, path):
    w, h = img.size
    arr = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(arr)
    arr = arr.reshape(h, w, 4)[::-1]          # Blender rows start at the bottom; UV v is flipped on export
    np.save(path, arr.astype(np.float16))


def bake_atlas(key, objs, size, out_dir, samples=16, ao_distance=0.6, margin=8):
    sc = bpy.context.scene
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.render.bake.margin = margin
    sc.render.bake.margin_type = "EXTEND"
    sc.render.bake.use_clear = True
    if sc.world is None:
        sc.world = bpy.data.worlds.new("bake_world")
    sc.world.light_settings.distance = ao_distance
    mats = _materials_of(objs)
    _select_only(objs)
    out = {}
    for chan, btype in (("albedo", "EMIT"), ("params", "EMIT"), ("normal", "NORMAL"), ("ao", "AO")):
        img = _image("%s_%s" % (key, chan), size)
        _set_bake_target(mats, img)
        saved = _emit_from(mats, chan) if btype == "EMIT" else None
        kw = {"type": btype, "margin": margin, "use_clear": True}
        if btype == "NORMAL":
            kw.update(normal_space="TANGENT")
        if btype == "AO":
            sc.cycles.samples = max(samples * 2, 32)
        bpy.ops.object.bake(**kw)
        sc.cycles.samples = samples
        if saved:
            _restore(saved)
        path = os.path.join(out_dir, "%s_%s.npy" % (key, chan))
        _save(img, path)
        out[chan] = img
    return out


# ------------------------------------------------------------------ finish
def _preview_material(key, imgs, blend):
    mat = bpy.data.materials.new(key)
    if mat.name != key:
        raise RuntimeError("material name %s is taken (got %s)" % (key, mat.name))
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    t = {}
    for chan in ("albedo", "params", "normal"):
        nd = nt.nodes.new("ShaderNodeTexImage")
        nd.image = imgs[chan]
        nd.interpolation = "Linear"
        t[chan] = nd
    nt.links.new(t["albedo"].outputs[0], bsdf.inputs["Base Color"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(t["params"].outputs[0], sep.inputs[0])
    nt.links.new(sep.outputs[0], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs[1], bsdf.inputs["Metallic"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.uv_map = "uv"
    nt.links.new(t["normal"].outputs[0], nm.inputs["Color"])
    nt.links.new(nm.outputs[0], bsdf.inputs["Normal"])
    if blend:
        nt.links.new(sep.outputs[2], bsdf.inputs["Alpha"])
        mat.surface_render_method = "BLENDED"
    return mat


def _join(objs, name):
    if len(objs) == 1:
        objs[0].name = name
        return objs[0]
    _select_only(objs)
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    return ob


def render_preview(path, camera_loc, target, lens=50, size=(1600, 1000), samples=96):
    sc = bpy.context.scene
    cam_data = bpy.data.cameras.new("preview_cam")
    cam_data.lens = lens
    cam_data.clip_start = 0.5
    cam_data.clip_end = 1000
    cam = _link(bpy.data.objects.new("preview_cam", cam_data))
    cam.location = Vector(camera_loc)
    cam.rotation_euler = (Vector(target) - Vector(camera_loc)).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    world = sc.world or bpy.data.worlds.new("w")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    sky = world.node_tree.nodes.new("ShaderNodeTexSky") if False else None
    bg.inputs["Color"].default_value = (0.42, 0.45, 0.5, 1.0)
    bg.inputs["Strength"].default_value = 0.6
    for nm, loc, energy, sz in (("key", (-10, 40, 40), 30000, 20), ("fill", (20, -30, 15), 9000, 30),
                                ("rim", (-50, -10, 20), 14000, 15)):
        ld = bpy.data.lights.new(nm, "AREA")
        ld.energy = energy
        ld.size = sz
        lo = _link(bpy.data.objects.new(nm, ld))
        lo.location = Vector(loc)
        lo.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    sc.render.resolution_x, sc.render.resolution_y = size
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "AgX"
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def finish(out_dir, atlases, camo_density, preview=None):
    """atlases: {key: {"size": px, "blend": bool, "camo": bool}}. Writes <out_dir>/model.blend, bake/*.npy,
    generator.json (what was built) and the preview."""
    os.makedirs(os.path.join(out_dir, "bake"), exist_ok=True)
    for c in STATE["cutters"]:
        bpy.data.objects.remove(c)
    STATE["cutters"].clear()
    by_atlas = {}
    for p in STATE["parts"]:
        by_atlas.setdefault(p["atlas"], []).append(p)
    report = {"atlases": {}, "parts": len(STATE["parts"]), "timing_s": {}}
    imgs = {}
    clock = time.time()
    for key in sorted(by_atlas):
        objs = by_atlas[key]
        cfg = atlases[key]
        t0 = time.time()
        unwrap_atlas(objs, margin=cfg.get("margin", 0.004))
        report["timing_s"]["unwrap_" + key] = round(time.time() - t0, 2)
        k = add_camo_uv(objs, camo_density) if cfg.get("camo") else None
        if not cfg.get("camo"):
            for o in objs:
                me = o.data
                cam = me.uv_layers.new(name="camo")
                vals = [0.0] * (2 * len(me.loops))
                me.uv_layers["uv"].uv.foreach_get("vector", vals)
                cam.uv.foreach_set("vector", vals)
                me.uv_layers.active = me.uv_layers["uv"]
        t0 = time.time()
        imgs[key] = bake_atlas(key, objs, cfg["size"], os.path.join(out_dir, "bake"),
                               samples=cfg.get("samples", 16))
        report["timing_s"]["bake_" + key] = round(time.time() - t0, 2)
        report["atlases"][key] = {"objects": len(objs), "size": cfg["size"], "uv1_per_inch": uv_density(objs),
                                  "camo_scale": k}
    # copies sharing a UV island
    for src, name, bone, matrix in STATE["after_bake"]:
        ob = transformed_copy(src, name, matrix)
        ob["bone"] = bone
        ob["atlas"] = src["atlas"]
        STATE["parts"].append(ob)
    # export materials + join per (bone, atlas)
    export_mats = {key: _preview_material(key, imgs[key], atlases[key].get("blend", False)) for key in imgs}
    groups = {}
    for p in STATE["parts"]:
        p.data.materials.clear()
        p.data.materials.append(export_mats[p["atlas"]])
        groups.setdefault((p["bone"], p["atlas"]), []).append(p)
    built = []
    for (bone, key), objs in sorted(groups.items()):
        ob = _join(objs, "%s__%s" % (key, bone))
        ob.vertex_groups.clear()
        vg = ob.vertex_groups.new(name=bone)
        vg.add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")
        built.append({"object": ob.name, "bone": bone, "atlas": key, "verts": len(ob.data.vertices),
                      "tris": sum(len(p.vertices) - 2 for p in ob.data.polygons)})
    report["objects"] = built
    report["tris"] = sum(b["tris"] for b in built)
    keep = set(export_mats.values())
    for m in list(bpy.data.materials):
        if m not in keep:
            bpy.data.materials.remove(m)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, "model.blend"))
    report["timing_s"]["uv_bake_join_save"] = round(time.time() - clock, 2)
    if preview:
        t0 = time.time()
        render_preview(**preview)
        report["timing_s"]["preview_render"] = round(time.time() - t0, 2)
    with open(os.path.join(out_dir, "generator.json"), "w") as f:
        json.dump(report, f, indent=1)
    return report


def rng(seed):
    return random.Random(seed)

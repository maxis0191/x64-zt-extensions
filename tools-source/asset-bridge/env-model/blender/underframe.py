"""Subway car underframe in Blender (headless): centre sill, cross bearers and bevelled equipment boxes, glTF out.

  blender -b --factory-startup -P underframe.py -- --out <dir> --images <dir of PNG maps> [--spec boxes.json]

Boxes are (x0, x1, y0, y1, z0, z1) in car inches, z = 0 at the rail top (the car origin of the env-model ports), placed
between the bogies. Every box gets a 0.6-inch bevel and box-projected world UVs (one UV unit = 48 inches), material
iwz_underframe (dark painted steel, BO3 micro painted maps) or iwz_underframe_grime for the sill and bearers.
Writes underframe.glb + underframe.materials.json (GrayWolf layout) for t7_env_port.py.
"""
import argparse
import json
import os
import sys

import bmesh
import bpy

INCH = 0.0254
DEFAULT = {
    'iwz_underframe_grime': [(-250, 250, -6, 6, 22, 30), (-126, -118, -56, 56, 23, 30), (118, 126, -56, 56, 23, 30)],
    'iwz_underframe': [(-104, -34, -42, -8, 10, 27), (-24, 58, 8, 44, 12, 27), (68, 112, -44, -12, 14, 27),
                       (-62, -30, 12, 38, 16, 27), (20, 52, -36, -14, 17, 27)],
}
MATERIALS = [
    {'name': 'iwz_underframe', 'albedo': 'i_t7_micro_metal_painted_01_c.png', 'normal': 'i_t7_micro_metal_painted_01_n.png',
     'tint': [0.035, 0.036, 0.038]},
    {'name': 'iwz_underframe_grime', 'albedo': 'i_t7_micro_metal_rust_heavy_01_c.png', 'roughness': 'i_t7_micro_metal_rust_heavy_01_g.png',
     'normal': 'i_t7_micro_metal_rust_n.png', 'tint': [0.45, 0.4, 0.38]},
]


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--images', required=True)
    ap.add_argument('--spec')
    a = ap.parse_args(argv)
    spec = json.load(open(a.spec)) if a.spec else DEFAULT
    bpy.ops.wm.read_factory_settings(use_empty=True)
    me = bpy.data.meshes.new('underframe')
    ob = bpy.data.objects.new('underframe', me)
    bpy.context.scene.collection.objects.link(ob)
    names = list(spec)
    for n in names:
        me.materials.append(bpy.data.materials.new(n))
    bm = bmesh.new()
    for mi, n in enumerate(names):
        for x0, x1, y0, y1, z0, z1 in spec[n]:
            r = bmesh.ops.create_cube(bm, size=1.0)
            vs = r['verts']
            for v in vs:
                v.co.x = (x0 if v.co.x < 0 else x1) * INCH
                v.co.y = (y0 if v.co.y < 0 else y1) * INCH
                v.co.z = (z0 if v.co.z < 0 else z1) * INCH
            faces = list({f for v in vs for f in v.link_faces})
            for f in faces:
                f.material_index = mi
            edges = list({e for f in faces for e in f.edges})
            bmesh.ops.bevel(bm, geom=edges, offset=0.6 * INCH, segments=1, affect='EDGES')
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        nx, ny, nz = (abs(c) for c in f.normal)
        for loop in f.loops:
            c = loop.vert.co / INCH
            u, v = ((c.y, c.z) if nx >= max(ny, nz) else (c.x, c.z) if ny >= nz else (c.x, c.y))
            loop[uv].uv = (u / 48.0, v / 48.0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, 'underframe.glb')
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_yup=True,
                              export_materials='EXPORT')
    rel = os.path.relpath(a.images, a.out).replace(os.sep, '/')
    mats = []
    for m in MATERIALS:
        e = {'name': m['name'], 'alpha': 'opaque', 'techset': 'authored', 'color_tint': {'color': m['tint']}}
        for k in ('albedo', 'normal', 'roughness'):
            if m.get(k):
                e[k] = {'path': rel + '/' + m[k], **({'channel': 'r', 'invert': True} if k == 'roughness' else {}),
                        **({'encoding': 'xy'} if k == 'normal' else {})}
        mats.append(e)
    json.dump({'adapter': 'authored', 'format': 'greyhound-materials', 'materials': mats},
              open(os.path.join(a.out, 'underframe.materials.json'), 'w'), indent=1)
    print('UNDERFRAME', path)


if __name__ == '__main__':
    main()

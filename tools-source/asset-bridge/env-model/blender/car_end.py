"""Subway car end dressing in Blender (headless): destination blind box over the end door (line, car number, NOT IN
SERVICE), white head lamps and red marker lamps on the end posts, coupler (shank, head, carrier bracket) under the
gangway. glTF out, for one car end facing +x; the port manifest places it twice (yaw 0 and 180).

  blender -b --factory-startup -P car_end.py -- --out <dir> --images <dir of PNG maps> [--spec end.json]

Coordinates are car inches, z = 0 at the rail top (the car origin of the env-model ports). The defaults fit the
BO3 mp_banzai car (end wall x 238, end posts' face x 241.6, gangway curtains |y| 26..39 (top folds down to z ~161), door top z 149.8, sill
end x 250 at z 22..30). Writes car_end.glb + car_end.materials.json (GrayWolf layout) for t7_env_port.py.
"""
import argparse
import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix

INCH = 0.0254
DEFAULT = {
    # destination blind: housing box and the blind face (UV 0..1 over the face, text upright seen from +x)
    # (kept below z 161: the gangway curtains' top folds hang over the end wall above that)
    'blind_housing': (238.0, 239.8, -22.0, 22.0, 149.9, 161.4),
    'blind_face': (239.85, -20.0, 20.0, 150.2, 160.2),
    # marker lamps on the end posts: (y, z, radius, depth) on the post face x
    'post_face_x': 241.6,
    'lamps': [(50.0, 46.0, 3.0, 2.2), (-50.0, 46.0, 3.0, 2.2)],
    # head / tail lamps (white lens, unlit: the car is dead) above the markers
    'head_lamps': [(50.0, 60.0, 3.6, 2.4), (-50.0, 60.0, 3.6, 2.4)],
    # coupler: carrier bracket under the sill end, shank, head (all boxes x0, x1, y0, y1, z0, z1)
    'coupler': [(245.5, 251.5, -5.0, 5.0, 14.0, 22.0), (240.0, 260.0, -3.5, 3.5, 13.5, 19.5),
                (258.0, 266.5, -7.0, 7.0, 10.0, 20.0)],
}
MATERIALS = [
    {'name': 'iwz_end_housing', 'albedo': 'i_t7_micro_metal_painted_01_c.png', 'normal': 'i_t7_micro_metal_painted_01_n.png',
     'tint': [0.05, 0.052, 0.055], 'roughness_value': 0.6},
    {'name': 'iwz_dest_blind', 'albedo': 'iwz_dest_blind_c.png', 'roughness_value': 0.75},
    {'name': 'iwz_end_lamp_red', 'tint': [0.22, 0.012, 0.01], 'roughness_value': 0.15},
    {'name': 'iwz_end_lamp_white', 'tint': [0.55, 0.55, 0.5], 'roughness_value': 0.1},
    {'name': 'iwz_end_lamp_bezel', 'albedo': 'i_t7_micro_metal_painted_01_c.png', 'tint': [0.03, 0.03, 0.032],
     'roughness_value': 0.55},
    {'name': 'iwz_underframe_grime', 'albedo': 'i_t7_micro_metal_rust_heavy_01_c.png',
     'roughness': 'i_t7_micro_metal_rust_heavy_01_g.png', 'normal': 'i_t7_micro_metal_rust_n.png', 'tint': [0.45, 0.4, 0.38]},
]


def box(bm, mi, x0, x1, y0, y1, z0, z1, bevel=0.4):
    r = bmesh.ops.create_cube(bm, size=1.0)
    vs = r['verts']
    for v in vs:
        v.co.x = (x0 if v.co.x < 0 else x1) * INCH
        v.co.y = (y0 if v.co.y < 0 else y1) * INCH
        v.co.z = (z0 if v.co.z < 0 else z1) * INCH
    faces = list({f for v in vs for f in v.link_faces})
    for f in faces:
        f.material_index = mi
    if bevel:
        edges = list({e for f in faces for e in f.edges})
        bmesh.ops.bevel(bm, geom=edges, offset=bevel * INCH, segments=1, affect='EDGES')


def cylinder_x(bm, mi, x0, y, z, radius, depth, segments=16):
    """Closed cylinder along +x from x0, depth long."""
    r = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments, radius1=radius * INCH,
                              radius2=radius * INCH, depth=depth * INCH)
    m = Matrix.Translation(((x0 + depth / 2) * INCH, y * INCH, z * INCH)) @ Matrix.Rotation(math.pi / 2, 4, 'Y')
    bmesh.ops.transform(bm, matrix=m, verts=r['verts'])
    for f in {f for v in r['verts'] for f in v.link_faces}:
        f.material_index = mi
    return r['verts']


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--images', required=True)
    ap.add_argument('--spec')
    a = ap.parse_args(argv)
    spec = dict(DEFAULT, **(json.load(open(a.spec)) if a.spec else {}))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    me = bpy.data.meshes.new('car_end')
    ob = bpy.data.objects.new('car_end', me)
    bpy.context.scene.collection.objects.link(ob)
    names = [m['name'] for m in MATERIALS]
    for n in names:
        me.materials.append(bpy.data.materials.new(n))
    H, BL, LR, LW, BZ, GR = (names.index(n) for n in ('iwz_end_housing', 'iwz_dest_blind', 'iwz_end_lamp_red',
                                                       'iwz_end_lamp_white', 'iwz_end_lamp_bezel', 'iwz_underframe_grime'))
    bm = bmesh.new()
    box(bm, H, *spec['blind_housing'])
    fx, y0, y1, z0, z1 = spec['blind_face']
    vs = [bm.verts.new((fx * INCH, y * INCH, z * INCH)) for y, z in ((y0, z0), (y1, z0), (y1, z1), (y0, z1))]
    face = bm.faces.new(vs)                 # counter-clockwise seen from +x: normal +x
    face.material_index = BL
    px = spec['post_face_x']
    for y, z, rad, depth in spec['lamps']:
        cylinder_x(bm, BZ, px, y, z, rad + 0.9, depth * 0.6)
        cylinder_x(bm, LR, px, y, z, rad, depth)
    for y, z, rad, depth in spec['head_lamps']:
        cylinder_x(bm, BZ, px, y, z, rad + 0.9, depth * 0.6)
        cylinder_x(bm, LW, px, y, z, rad, depth)
    for b in spec['coupler']:
        box(bm, GR, *b, bevel=0.5)
    bmesh.ops.recalc_face_normals(bm, faces=[f for f in bm.faces if f is not face])
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        for loop in f.loops:
            c = loop.vert.co / INCH
            if f is face:
                # blind: u along +y (viewer's right seen from +x), v up (Blender bottom-left; glTF export flips)
                loop[uv].uv = ((c.y - y0) / (y1 - y0), (c.z - z0) / (z1 - z0))
                continue
            nx, ny, nz = (abs(k) for k in f.normal)
            u, v = ((c.y, c.z) if nx >= max(ny, nz) else (c.x, c.z) if ny >= nz else (c.x, c.y))
            loop[uv].uv = (u / 48.0, v / 48.0)
    bm.to_mesh(me)
    bm.free()
    if me.polygons[[p.material_index for p in me.polygons].index(BL)].normal.x < 0:
        raise SystemExit('blind face points away from +x')
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, 'car_end.glb')
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_yup=True,
                              export_materials='EXPORT')
    rel = os.path.relpath(a.images, a.out).replace(os.sep, '/')
    mats = []
    for m in MATERIALS:
        e = {'name': m['name'], 'alpha': 'opaque', 'techset': 'authored'}
        if m.get('tint'):
            e['color_tint'] = {'color': m['tint']}
        if 'roughness_value' in m:
            e['roughness_value'] = m['roughness_value']
        for k in ('albedo', 'normal', 'roughness'):
            if m.get(k):
                e[k] = {'path': rel + '/' + m[k], **({'channel': 'r', 'invert': True} if k == 'roughness' else {}),
                        **({'encoding': 'xy'} if k == 'normal' else {})}
        mats.append(e)
    json.dump({'adapter': 'authored', 'format': 'greyhound-materials', 'materials': mats},
              open(os.path.join(a.out, 'car_end.materials.json'), 'w'), indent=1)
    print('CAR_END', path, len(me.polygons), 'faces')


if __name__ == '__main__':
    main()

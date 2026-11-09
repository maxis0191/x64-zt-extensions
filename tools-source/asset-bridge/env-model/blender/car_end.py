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
    # closed gangway diaphragm: x from the end wall to the coupling face, outer / inner (half width, z0, z1)
    'gangway_x': (238.4, 266.5), 'gangway_outer': (35.0, 29.0, 171.0), 'gangway_inner': (27.6, 36.0, 165.0),
    # run-number plate on the -y end post: (y centre, z0, z1, width)
    'run_plate': (-50.0, 100.0, 112.0, 10.0),
    # gangway end door filling the diaphragm opening just inside its face frame (seen at an uncoupled end; two coupled
    # cars' doors face each other behind the meeting frames): x0, x1, window (y half, z0, z1), handle (y, z)
    'end_door': (263.0, 264.6, (9.0, 104.0, 140.0), (-18.0, 88.0)),
    # buffers (y, z, stock radius, head radius) on a buffer beam under the diaphragm; heads end at 266.3
    'buffer_beam': (248.5, 252.0, -52.0, 52.0, 17.0, 26.0),
    'buffers': [(44.0, 21.5, 3.2, 6.0), (-44.0, 21.5, 3.2, 6.0)],
    # battery emergency lamp on the ceiling near the end (car interior, ceiling at z 162): housing / lens boxes
    'emergency_lamp': ((198.0, 214.0, -5.0, 5.0, 159.4, 162.0), (199.5, 212.5, -3.8, 3.8, 158.9, 159.5)),
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
    {'name': 'iwz_gangway_rubber', 'tint': [0.028, 0.027, 0.026], 'roughness_value': 0.8},
    {'name': 'iwz_run_plate', 'albedo': 'iwz_run_plate_c.png', 'roughness_value': 0.4},
    {'name': 'iwz_end_door', 'albedo': 'i_t7_micro_metal_painted_01_c.png', 'normal': 'i_t7_micro_metal_painted_01_n.png',
     'tint': [0.03, 0.045, 0.06], 'roughness_value': 0.55},
    {'name': 'iwz_end_door_glass', 'tint': [0.012, 0.013, 0.014], 'roughness_value': 0.08},
    # dim amber battery lamp lens (self-lit: the dead car's emergency lighting reads through the windows)
    {'name': 'iwz_car_emergency_lamp', 'albedo': 'iwz_car_lamp_e.png', 'emissive': 'iwz_car_lamp_e.png',
     'roughness_value': 0.3},
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
        bmesh.ops.bevel(bm, geom=edges, offset=bevel * INCH, segments=1, affect='EDGES', material=mi)


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
    # closed gangway diaphragm (replaces BO3's open side curtains): accordion rings round the end door from the end
    # wall to the coupled face, a steel face frame; coupled cars' faces meet (pitch 534 = 2 x 266.5 + 1)
    RB = names.index('iwz_gangway_rubber')
    gx0, gx1 = spec['gangway_x']
    (oy, oz0, oz1), (iy, iz0, iz1) = spec['gangway_outer'], spec['gangway_inner']
    n = int(round((gx1 - 1.0 - gx0) / 2.8))
    for k in range(n):
        xa = gx0 + (gx1 - 1.0 - gx0) * k / n
        xb = gx0 + (gx1 - 1.0 - gx0) * (k + 1) / n
        e = 2.4 if k % 2 == 0 else 0.0
        for (y0, y1, z0, z1) in ((-oy - e, -iy, oz0 - e, oz1 + e), (iy, oy + e, oz0 - e, oz1 + e),
                                 (-iy, iy, oz0 - e, iz0), (-iy, iy, iz1, oz1 + e)):
            box(bm, RB, xa, xb, y0, y1, z0, z1, bevel=0.3 if e else 0.0)
    for (y0, y1, z0, z1) in ((-oy - 0.6, -iy, oz0 - 0.6, oz1 + 0.6), (iy, oy + 0.6, oz0 - 0.6, oz1 + 0.6),
                             (-iy, iy, oz0 - 0.6, iz0), (-iy, iy, iz1, oz1 + 0.6)):
        box(bm, H, gx1 - 1.0, gx1, y0, y1, z0, z1, bevel=0.2)
    # gangway end door in the diaphragm opening: slab, dark window, handle
    DR, DG, BZ_ = names.index('iwz_end_door'), names.index('iwz_end_door_glass'), names.index('iwz_end_lamp_bezel')
    dx0, dx1, (wy, wz0, wz1), (hy, hz) = spec['end_door']
    box(bm, DR, dx0, dx1, -iy, iy, iz0, wz0, bevel=0.0)                # below the window
    box(bm, DR, dx0, dx1, -iy, iy, wz1, iz1, bevel=0.0)                # above
    box(bm, DR, dx0, dx1, -iy, -wy, wz0, wz1, bevel=0.0)               # window side stiles
    box(bm, DR, dx0, dx1, wy, iy, wz0, wz1, bevel=0.0)
    box(bm, DG, dx0 + 0.3, dx1 - 0.6, -wy, wy, wz0, wz1, bevel=0.0)    # glass recessed 0.6 in
    box(bm, BZ_, dx1, dx1 + 1.2, hy - 1.0, hy + 1.0, hz - 4.0, hz + 4.0, bevel=0.2)
    for z in (iz0 + 18.0, iz1 - 18.0):                                 # hinges
        box(bm, BZ_, dx1, dx1 + 0.5, iy - 3.0, iy - 0.5, z - 3.0, z + 3.0, bevel=0.0)
    # buffer beam and two buffers (stock + head)
    box(bm, H, *spec['buffer_beam'], bevel=0.3)
    for by, bz, rs, rh in spec['buffers']:
        cylinder_x(bm, GR, spec['buffer_beam'][1], by, bz, rs, 9.0)
        cylinder_x(bm, H, spec['buffer_beam'][1] + 9.0, by, bz, rh, 3.3, segments=20)
    # emergency lamp on the ceiling near this end
    EL = names.index('iwz_car_emergency_lamp')
    hb, lb = spec['emergency_lamp']
    box(bm, H, *hb, bevel=0.2)
    box(bm, EL, *lb, bevel=0.0)
    # run-number plate on the end post (white enamel, black numerals), facing +x
    RP = names.index('iwz_run_plate')
    py, pz0, pz1, pw = spec['run_plate']
    plates = {}
    for py_ in (py, -py):                     # both end posts: one faces the platform whichever way the car stands
        rp = [bm.verts.new((px_ * INCH, y_ * INCH, z_ * INCH)) for px_, y_, z_ in
              ((spec['post_face_x'] + 0.08, py_ - pw / 2, pz0), (spec['post_face_x'] + 0.08, py_ + pw / 2, pz0),
               (spec['post_face_x'] + 0.08, py_ + pw / 2, pz1), (spec['post_face_x'] + 0.08, py_ - pw / 2, pz1))]
        f_ = bm.faces.new(rp)
        f_.material_index = RP
        plates[f_] = py_
        # blank steel backing: seen from behind (g27d: a mirrored "47" from the trackside) the plate is a plain plate
        box(bm, H, spec['post_face_x'] - 0.6, spec['post_face_x'], py_ - pw / 2 - 0.6, py_ + pw / 2 + 0.6,
            pz0 - 0.6, pz1 + 0.6, bevel=0.0)
    for b in spec['coupler']:
        box(bm, GR, *b, bevel=0.5)
    bmesh.ops.recalc_face_normals(bm, faces=[f for f in bm.faces if f is not face and f not in plates])
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        for loop in f.loops:
            c = loop.vert.co / INCH
            if f is face:
                # blind: u along +y (viewer's right seen from +x), v up (Blender bottom-left; glTF export flips)
                loop[uv].uv = ((c.y - y0) / (y1 - y0), (c.z - z0) / (z1 - z0))
                continue
            if f in plates:
                loop[uv].uv = ((c.y - (plates[f] - pw / 2)) / pw, (c.z - pz0) / (pz1 - pz0))
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
        for k in ('albedo', 'normal', 'roughness', 'emissive'):
            if m.get(k):
                e[k] = {'path': rel + '/' + m[k], **({'channel': 'r', 'invert': True} if k == 'roughness' else {}),
                        **({'encoding': 'xy'} if k == 'normal' else {})}
        mats.append(e)
    json.dump({'adapter': 'authored', 'format': 'greyhound-materials', 'materials': mats},
              open(os.path.join(a.out, 'car_end.materials.json'), 'w'), indent=1)
    print('CAR_END', path, len(me.polygons), 'faces')


if __name__ == '__main__':
    main()

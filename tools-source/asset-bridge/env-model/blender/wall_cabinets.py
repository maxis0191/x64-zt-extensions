"""Period wall fittings in Blender (headless), as replacements for modern cabinets: a fire-hose cabinet (red steel box,
glazed door frame, hose reel with a coiled canvas hose and a brass nozzle, FIRE HOSE enamel label) and a help-point
backing plate (Zero Line enamel label for the BO3 hanging vintage phone). glTF out, one file per fitting.

  blender -b --factory-startup -P wall_cabinets.py -- --out <dir> --images <dir of PNG maps>

Model space in inches: the wall plane is y = 0, the fitting stands out to -y (its front), z = 0 its bottom.
"""
import argparse
import json
import math
import os
import sys

import bmesh
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from genset import Builder, front_quad   # noqa: E402

MATERIALS = [
    {'name': 'iwz_cab_red', 'albedo': 'i_t7_micro_metal_painted_01_c.png', 'normal': 'i_t7_micro_metal_painted_01_n.png',
     'tint': [0.32, 0.025, 0.02], 'roughness_value': 0.45},
    {'name': 'iwz_cab_steel', 'albedo': 'i_t7_micro_metal_rust_heavy_01_c.png', 'roughness': 'i_t7_micro_metal_rust_heavy_01_g.png',
     'normal': 'i_t7_micro_metal_rust_n.png', 'tint': [0.25, 0.23, 0.22]},
    {'name': 'iwz_cab_hose', 'tint': [0.55, 0.47, 0.33], 'roughness_value': 0.85},
    {'name': 'iwz_cab_brass', 'tint': [0.45, 0.33, 0.12], 'roughness_value': 0.3},
    {'name': 'iwz_cab_glass', 'tint': [0.6, 0.65, 0.65], 'alpha': 'blend', 'roughness_value': 0.1},
    {'name': 'iwz_cab_navy', 'albedo': 'i_t7_micro_metal_painted_01_c.png', 'tint': [0.02, 0.035, 0.09],
     'roughness_value': 0.5},
    {'name': 'iwz_firehose_label', 'albedo': 'iwz_firehose_label_c.png', 'roughness_value': 0.35},
    {'name': 'iwz_helppoint_label', 'albedo': 'iwz_helppoint_label_c.png', 'roughness_value': 0.35},
    {'name': 'iwz_rad_frame', 'albedo': 'i_t7_micro_metal_painted_01_c.png', 'normal': 'i_t7_micro_metal_painted_01_n.png',
     'tint': [0.09, 0.115, 0.095], 'roughness_value': 0.55},
    {'name': 'iwz_rad_core', 'albedo': 'i_t7_micro_metal_rust_heavy_01_c.png', 'roughness': 'i_t7_micro_metal_rust_heavy_01_g.png',
     'normal': 'i_t7_micro_metal_rust_n.png', 'tint': [0.16, 0.14, 0.13]},
    {'name': 'iwz_g2_stencil_steel', 'albedo': 'iwz_g2_stencil_steel_c.png', 'roughness_value': 0.6},
]


def build(name, fn, a):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    me = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    used = fn.__defaults__[0] if fn.__defaults__ else None
    names = [m['name'] for m in MATERIALS]
    for n in names:
        me.materials.append(bpy.data.materials.new(n))
    bm = bmesh.new()
    b = Builder(bm, {n: i for i, n in enumerate(names)})
    fn(b)
    for f in bm.faces:
        if f in b.mapped:
            continue
        nx, ny, nz = (abs(v) for v in f.normal)
        for loop in f.loops:
            co = loop.vert.co / 0.0254
            u, v = ((co.y, co.z) if nx >= max(ny, nz) else (co.x, co.z) if ny >= nz else (co.x, co.y))
            loop[b.uv].uv = (u / 24.0, v / 24.0)
    bmesh.ops.recalc_face_normals(bm, faces=[f for f in bm.faces if f not in b.mapped])
    bm.to_mesh(me)
    bm.free()
    # drop unused material slots so the port only bakes what the fitting uses
    keep = sorted({p.material_index for p in me.polygons})
    path = os.path.join(a.out, name + '.glb')
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_yup=True,
                              export_materials='EXPORT')
    rel = os.path.relpath(a.images, a.out).replace(os.sep, '/')
    mats = []
    for i in keep:
        m = MATERIALS[i]
        e = {'name': m['name'], 'alpha': m.get('alpha', 'opaque'), 'techset': 'authored'}
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
              open(os.path.join(a.out, name + '.materials.json'), 'w'), indent=1)
    print('CABINET', path, len(me.polygons), 'faces')


def fire_hose(b):
    W, D, H = 30.0, 10.0, 36.0
    x0, x1 = -W / 2, W / 2
    b.box('iwz_cab_red', x0, x1, -D, 0, 0, H, bevel=0.3)                         # body (front open behind the door)
    b.box('iwz_cab_steel', x0 + 1, x1 - 1, -D + 0.5, -1, 1, H - 1)              # dark interior back
    # hose reel: drum on a wall bracket, canvas hose coils, brass nozzle hanging in front
    b.cyl('iwz_cab_steel', (0, -1, 20), (0, -4, 20), 2.0, 12)
    for k, r in enumerate((10.5, 9.4, 8.3, 7.2)):
        b.cyl('iwz_cab_hose', (0, -2.2, 20), (0, -7.0 + 0.25 * k, 20), r, 24)
        b.cyl('iwz_cab_red', (0, -1.9, 20), (0, -2.2, 20), r + 0.6, 24) if k == 0 else None
    b.cyl('iwz_cab_brass', (6.5, -7.5, 9.5), (6.5, -7.5, 4.0), 0.9, 10)
    b.cyl('iwz_cab_hose', (6.5, -7.5, 9.5), (6.5, -7.5, 11.5), 1.0, 10)
    # door: steel frame bars with a glass pane, handle
    zf = (0.6, H - 0.6)
    b.box('iwz_cab_red', x0, x0 + 1.6, -D - 0.8, -D, *zf)
    b.box('iwz_cab_red', x1 - 1.6, x1, -D - 0.8, -D, *zf)
    b.box('iwz_cab_red', x0, x1, -D - 0.8, -D, H - 7.2, H - 0.6)                 # top rail carries the label
    b.box('iwz_cab_red', x0, x1, -D - 0.8, -D, 0.6, 2.2)
    b.quad('iwz_cab_glass', [(x0 + 1.6, -D - 0.4, 2.2), (x1 - 1.6, -D - 0.4, 2.2), (x1 - 1.6, -D - 0.4, H - 7.2),
                             (x0 + 1.6, -D - 0.4, H - 7.2)])
    b.box('iwz_cab_brass', x1 - 3.2, x1 - 2.4, -D - 2.0, -D - 0.8, 14, 19)
    front_quad(b, 'iwz_firehose_label', x0 + 2.5, x1 - 2.5, H - 6.6, H - 1.2, -D - 0.85)


def help_point(b):
    # enamel backing plate (12 x 30) the BO3 hanging phone mounts on (phone origin at (0, -0.4, 6)), label at the top
    b.box('iwz_cab_navy', -6, 6, -0.4, 0, 0, 30, bevel=0.15)
    front_quad(b, 'iwz_helppoint_label', -5, 5, 19, 29, -0.45)
    for x, z in ((-5, 1), (5, 1), (-5, 29), (5, 29)):
        b.cyl('iwz_cab_steel', (x, -0.4, z), (x, -0.7, z), 0.35, 6)


def radiator(b):
    """G-2's remote radiator (the cooler): a painted steel frame on four legs, a rusted finned core facing -y, top and
    bottom tanks, a fan shroud with blades on the back (+y), coolant pipes on the -x side, G-2 stencil on the top tank.
    Model space: floor z 0, front -y, footprint x -32..32, y -16..20, 74 high."""
    W, D = 30.0, 14.0
    for x in (-W, W - 3):                                         # legs
        for y in (-D, D - 3):
            b.box('iwz_rad_frame', x, x + 3, y, y + 3, 0, 8)
    b.box('iwz_rad_frame', -W - 1, W + 1, -D - 1, D + 1, 8, 12, bevel=0.3)             # bottom tank
    b.box('iwz_rad_frame', -W - 1, W + 1, -D - 1, D + 1, 62, 70, bevel=0.3)            # top tank
    b.box('iwz_rad_frame', -W - 1, -W + 2, -D - 1, D + 1, 12, 62)                      # side frames
    b.box('iwz_rad_frame', W - 2, W + 1, -D - 1, D + 1, 12, 62)
    b.box('iwz_rad_core', -W + 2, W - 2, -D + 2, D - 2, 12, 62)                        # core block
    x = -W + 3.0
    while x < W - 3:                                                                   # front fins
        b.box('iwz_rad_core', x, x + 0.35, -D - 0.2, -D + 2, 12.5, 61.5)
        x += 1.1
    b.cyl('iwz_rad_frame', (0, D, 37), (0, D + 5, 37), 22, 24)                         # fan shroud ring (back)
    b.cyl('iwz_rad_core', (0, D + 2, 37), (0, D + 3, 37), 4, 12)                       # hub
    for k in range(6):                                                                 # blades
        t = math.radians(60 * k + 15)
        b.cyl('iwz_rad_core', (0, D + 2.5, 37), (19 * math.cos(t), D + 2.5, 37 + 19 * math.sin(t)), 1.6, 6)
    b.cyl('iwz_rad_frame', (-W - 1, 0, 66), (-W - 8, 0, 66), 2.2, 12)                  # top hose stub
    b.cyl('iwz_rad_frame', (-W - 1, 0, 10), (-W - 8, 0, 10), 2.2, 12)                  # bottom hose stub
    b.cyl('iwz_rad_frame', (6, 0, 70), (6, 0, 74), 1.8, 10)                            # filler cap
    front_quad(b, 'iwz_g2_stencil_steel', -10, 10, 62.5, 69.5, -D - 1.06)


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--images', required=True)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    build('fire_hose_cabinet', fire_hose, a)
    build('help_point_plate', help_point, a)
    build('g2_radiator', radiator, a)


if __name__ == '__main__':
    main()

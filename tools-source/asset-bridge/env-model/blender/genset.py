"""Generator set G-2 dressing in Blender (headless): the authored parts around two BO3 machines (zm_cosmodrome diesel
engine, zm_island industrial alternator, placed by the port manifest) - stained concrete plinth with anchor bolts,
steel skid and engine bed, coupling guard, switchgear cabinet with breakers (one tripped, red, with a DO NOT RESTART
lockout tag and scorch), engraved label plate, G-2 stencils, oil stains, cable trough with cables. glTF out.

  blender -b --factory-startup -P genset.py -- --out <dir> --images <dir of PNG maps>

Model space in inches, z = 0 the room floor, +x along the set (engine at -x, alternator at +x, switchgear beyond),
front = -y. The BO3 parts sit at: engine (-48, 0, 44) scale 1.6, alternator (42, 0, 18) yaw -90 scale 1.6 (its drive
end towards the engine), knife-switch disconnect p7_electrical_box_set2_box04 (160, 38, 22) yaw 90. Writes genset.glb +
genset.materials.json (GrayWolf layout) and anchors.json (placement / dressing anchors for the level).
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
PL, SK, BED = 12.0, 6.0, 26.0          # plinth top, skid height, engine bed height (crank to the alternator shaft)

MATERIALS = [
    {'name': 'iwz_g2_plinth', 'albedo': 'i_t7_concrete_poured_bunker_dirty_01_c.png', 'tint': [0.55, 0.53, 0.5]},
    {'name': 'iwz_g2_steel', 'albedo': 'i_t7_micro_metal_rust_heavy_01_c.png', 'roughness': 'i_t7_micro_metal_rust_heavy_01_g.png',
     'normal': 'i_t7_micro_metal_rust_n.png', 'tint': [0.22, 0.2, 0.19]},
    {'name': 'iwz_g2_guard', 'albedo': 'i_t7_micro_metal_painted_01_c.png', 'normal': 'i_t7_micro_metal_painted_01_n.png',
     'tint': [0.55, 0.38, 0.04], 'roughness_value': 0.55},
    {'name': 'iwz_g2_cabinet', 'albedo': 'i_t7_micro_metal_painted_01_c.png', 'normal': 'i_t7_micro_metal_painted_01_n.png',
     'tint': [0.1, 0.13, 0.11], 'roughness_value': 0.5},
    {'name': 'iwz_g2_panel', 'tint': [0.02, 0.02, 0.022], 'roughness_value': 0.45},
    {'name': 'iwz_g2_handle', 'tint': [0.03, 0.03, 0.03], 'roughness_value': 0.35},
    {'name': 'iwz_g2_handle_tripped', 'tint': [0.45, 0.04, 0.03], 'roughness_value': 0.35},
    {'name': 'iwz_g2_rubber', 'tint': [0.018, 0.018, 0.018], 'roughness_value': 0.7},
    {'name': 'iwz_g2_label', 'albedo': 'iwz_g2_label_c.png', 'roughness_value': 0.4},
    # stencils, scorched breaker window and tag are opaque faces with the art composited over the surface they sit on
    # (in engine the IW7 decal template drew them faintly and the cutout template black: train runs e5 / e6)
    {'name': 'iwz_g2_tag', 'albedo': 'iwz_g2_tag_opaque_c.png', 'roughness_value': 0.8},
    {'name': 'iwz_g2_stencil_steel', 'albedo': 'iwz_g2_stencil_steel_c.png', 'roughness_value': 0.6},
    {'name': 'iwz_g2_stencil_conc', 'albedo': 'iwz_g2_stencil_conc_c.png', 'roughness_value': 0.8},
    {'name': 'iwz_g2_stencil_green', 'albedo': 'iwz_g2_stencil_green_c.png', 'roughness_value': 0.5},
    {'name': 'iwz_g2_window', 'albedo': 'iwz_g2_window_c.png', 'roughness_value': 0.5},
    {'name': 'iwz_g2_oil', 'albedo': 'iwz_g2_oil_c.png', 'decal': True},
]


class Builder:
    def __init__(self, bm, mats):
        self.bm, self.m = bm, mats
        self.uv = bm.loops.layers.uv.verify()
        self.mapped = set()

    def box(self, mat, x0, x1, y0, y1, z0, z1, bevel=0.0):
        r = bmesh.ops.create_cube(self.bm, size=1.0)
        for v in r['verts']:
            v.co.x = (x0 if v.co.x < 0 else x1) * INCH
            v.co.y = (y0 if v.co.y < 0 else y1) * INCH
            v.co.z = (z0 if v.co.z < 0 else z1) * INCH
        faces = list({f for v in r['verts'] for f in v.link_faces})
        for f in faces:
            f.material_index = self.m[mat]
        if bevel:
            bmesh.ops.bevel(self.bm, geom=list({e for f in faces for e in f.edges}), offset=bevel * INCH, segments=1,
                            affect='EDGES', material=self.m[mat])

    def cyl(self, mat, p0, p1, r, seg=12):
        """Closed cylinder from p0 to p1 (inches)."""
        ax = [b - a for a, b in zip(p0, p1)]
        L = math.sqrt(sum(c * c for c in ax))
        res = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r * INCH,
                                    radius2=r * INCH, depth=L * INCH)
        from mathutils import Vector
        q = Vector((0, 0, 1)).rotation_difference(Vector(ax).normalized())
        mid = [(a + b) / 2 * INCH for a, b in zip(p0, p1)]
        bmesh.ops.transform(self.bm, matrix=Matrix.Translation(mid) @ q.to_matrix().to_4x4(), verts=res['verts'])
        for f in {f for v in res['verts'] for f in v.link_faces}:
            f.material_index = self.m[mat]

    def quad(self, mat, corners):
        """A textured face: corners in inches, counter-clockwise seen from the front, UV (0,0) at the first (bottom-left
        of the image as seen), (1,0) the second (bottom-right), (1,1), (0,1)."""
        vs = [self.bm.verts.new(tuple(c * INCH for c in p)) for p in corners]
        f = self.bm.faces.new(vs)
        f.material_index = self.m[mat]
        for loop, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            loop[self.uv].uv = uv
        self.mapped.add(f)
        return f


def front_quad(b, mat, x0, x1, z0, z1, y):
    """A face facing -y (the set's front) at y, x0..x1 left to right as seen from the front, z0..z1."""
    b.quad(mat, [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)])


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--images', required=True)
    a = ap.parse_args(argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    me = bpy.data.meshes.new('genset')
    ob = bpy.data.objects.new('genset', me)
    bpy.context.scene.collection.objects.link(ob)
    names = [m['name'] for m in MATERIALS]
    for n in names:
        me.materials.append(bpy.data.materials.new(n))
    bm = bmesh.new()
    b = Builder(bm, {n: i for i, n in enumerate(names)})
    # plinth with a chamfer, anchor bolts along the skid
    b.box('iwz_g2_plinth', -112, 100, -52, 52, 0, PL, bevel=1.0)
    for y in (-30, 30):
        b.box('iwz_g2_steel', -100, 90, y - 3, y + 3, PL, PL + SK, bevel=0.3)                 # skid channels
        for x in (-95, -60, -25, 10, 45, 80):
            for yo in (-5.5, 5.5):
                b.cyl('iwz_g2_steel', (x, y + yo, PL), (x, y + yo, PL + 1.2), 1.4, 6)           # nut
                b.cyl('iwz_g2_steel', (x, y + yo, PL + 1.2), (x, y + yo, PL + 2.4), 0.6, 8)     # bolt end
    for x in (-100, -50, 0, 50, 88):
        b.box('iwz_g2_steel', x, x + 2, -33, 33, PL, PL + SK - 1)                             # cross members
    b.box('iwz_g2_steel', -88, -8, -30, 30, PL + SK, PL + SK + BED, bevel=0.5)               # engine bed
    b.box('iwz_g2_guard', -9, 2, -14, 14, PL + SK + 8, PL + SK + 36, bevel=0.6)               # coupling guard
    # switchgear cabinet (front at y 26, facing -y), plinth, door seams, breaker window, handles
    b.box('iwz_g2_plinth', 110, 162, 24, 48, 0, 4, bevel=0.5)
    b.box('iwz_g2_cabinet', 112, 160, 26, 46, 4, 86, bevel=0.4)
    b.box('iwz_g2_panel', 135.8, 136.2, 25.7, 26.0, 6, 84)                                     # door seam
    b.box('iwz_g2_panel', 118, 154, 25.5, 26.0, 40, 70)                                       # breaker window
    front_quad(b, 'iwz_g2_window', 118, 154, 40, 70, 25.45)         # its face: dark panel scorched round the tripped one
    tripped = (1, 1)
    for row, z in enumerate((48, 60)):
        for col, x in enumerate((122, 131, 140, 149)):
            if (row, col) == tripped:
                b.box('iwz_g2_handle_tripped', x - 1.5, x + 1.5, 23.0, 25.5, z - 2.5, z + 1.5)     # tripped: mid-throw
            else:
                b.box('iwz_g2_handle', x - 1.5, x + 1.5, 23.5, 25.5, z, z + 5)
    front_quad(b, 'iwz_g2_label', 120, 152, 72, 80, 25.9)
    # lockout tag hanging from the tripped handle (tilted 12 deg), both faces
    tx, tz = 131, 57.5
    c, s = math.cos(math.radians(12)), math.sin(math.radians(12))
    corners = [(tx - 1.5, 22.8, tz - 6.0), (tx + 1.5, 22.8, tz - 6.0), (tx + 1.5, 22.8, tz), (tx - 1.5, 22.8, tz)]
    corners = [(x, 22.8 - (tz - z) * s * 0.3, tz - (tz - z) * c) for x, y, z in corners]
    b.quad('iwz_g2_tag', corners)                 # one face: the cutout template draws it two-sided
    b.box('iwz_g2_steel', tx - 0.15, tx + 0.15, 22.8, 23.2, tz - 0.2, tz + 1.6)                # tag wire
    # G-2 stencils: engine bed front, plinth front, cabinet side (+x face)
    front_quad(b, 'iwz_g2_stencil_steel', -78, -38, PL + SK + 3, PL + SK + 23, -30.06)
    front_quad(b, 'iwz_g2_stencil_conc', -104, -84, 1, 11, -52.06)
    b.quad('iwz_g2_stencil_green', [(160.06, 28, 62), (160.06, 44, 62), (160.06, 44, 70), (160.06, 28, 70)])
    # oil: on the plinth top under the engine front and on the floor in front of it
    b.quad('iwz_g2_oil', [(-110, -50, PL + 0.06), (-70, -50, PL + 0.06), (-70, -12, PL + 0.06), (-110, -12, PL + 0.06)])
    b.quad('iwz_g2_oil', [(-92, -112, 0.06), (-28, -112, 0.06), (-28, -52.5, 0.06), (-92, -52.5, 0.06)])
    # cable trough and three cables: alternator terminal end -> down the plinth end -> into the cabinet base
    b.box('iwz_g2_steel', 84, 100, 27, 39, PL, PL + 3)
    b.box('iwz_g2_steel', 100, 112, 27, 39, 0, 3)
    for k, y in enumerate((30, 33, 36)):
        b.cyl('iwz_g2_rubber', (82, y, PL + 2), (100.5, y, PL + 2), 1.2, 8)
        b.cyl('iwz_g2_rubber', (100.5, y, PL + 2), (101.5, y, 2), 1.2, 8)
        b.cyl('iwz_g2_rubber', (101.5, y, 2), (113, y, 2), 1.2, 8)
    # UVs: box projection (one UV unit = 48 in) except the mapped label / decal / tag faces
    for f in bm.faces:
        if f in b.mapped:
            continue
        nx, ny, nz = (abs(v) for v in f.normal)
        for loop in f.loops:
            co = loop.vert.co / INCH
            u, v = ((co.y, co.z) if nx >= max(ny, nz) else (co.x, co.z) if ny >= nz else (co.x, co.y))
            loop[b.uv].uv = (u / 48.0, v / 48.0)
    bmesh.ops.recalc_face_normals(bm, faces=[f for f in bm.faces if f not in b.mapped])
    bm.to_mesh(me)
    bm.free()
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, 'genset.glb')
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_yup=True,
                              export_materials='EXPORT')
    rel = os.path.relpath(a.images, a.out).replace(os.sep, '/')
    mats = []
    for m in MATERIALS:
        e = {'name': m['name'], 'alpha': m.get('alpha', 'auto' if m.get('decal') else 'opaque'),
             'techset': 'lit_decal' if m.get('decal') else 'authored'}
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
              open(os.path.join(a.out, 'genset.materials.json'), 'w'), indent=1)
    anchors = {
        'footprint': {'x': [-112, 162], 'y': [-52, 52], 'note': 'model space, z 0 = room floor, front = -y'},
        'clearance_front': 48, 'height': 80,
        'breaker_tripped': [131, 23.0, 58], 'lockout_tag': [131, 22.8, 54.5], 'label_plate': [136, 25.9, 76],
        'engine_bed_stencil': [-58, -30.06, 31], 'cabinet_front_use_spot': [136, -10, 0],
        'exhaust_flange_top': [-48, 0, 101], 'alternator_terminal_end': [82, 33, 30],
        'dressing_floor_spots': [[-130, -70, 0], [-60, -80, 0], [175, -20, 0]],
    }
    json.dump(anchors, open(os.path.join(a.out, 'anchors.json'), 'w'), indent=1)
    print('GENSET', path, len(me.polygons), 'faces')


if __name__ == '__main__':
    main()

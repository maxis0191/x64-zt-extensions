"""Procedural railway track parts in Blender (headless), exported as glTF for t7_env_port.py.

  blender -b --factory-startup -P track_kit.py -- --out <dir> --images <dir of PNG maps> [--length 256]

Writes, in game units (inches, Z up; Blender metres x 0.0254) and with world-scale UVs (one UV unit = --texel inches):
  rails_<L>.glb        two running rails, AREMA 115 RE-like profile (6 5/8 in tall, head 2 23/32, base 5 1/2),
                       standard gauge 56.5 in between the head inner faces, rail centre lines at y = +-29.61;
                       materials: rail_web (rusted steel: web, base, head sides), rail_head (polished running band)
  ballast_<L>.glb      ballast prism: top 124 wide at z = 0, base 172 wide at z = -16, ends open (segments abut)
  third_rail_<L>.glb   low conductor rail (smaller flat-bottom profile, top 3.5 in above the running rail top) on
                       porcelain insulators every 128 in, centre line at y = -(29.61 + 27.5)
  *_lod1.glb           the same with coarser profiles (fewer segments), for the second LOD
and <name>.materials.json (GrayWolf "greyhound-materials" layout) naming the source maps of each material, so the
port's material baker treats authored parts like ported ones. Z = 0 is the top of the sleepers' rail seats for the
rails and third rail (they sit on the BO3 tie p7_zm_ctl_railroad_tie: seat top 6.51 above its base).
"""
import argparse
import json
import math
import os
import sys

import bmesh
import bpy

INCH = 0.0254
GAUGE = 56.5
HEAD_W = 2.72
RAIL_CY = GAUGE / 2 + HEAD_W / 2            # 29.61
RAIL_BASE_Z = 5.01      # running rail base above the ballast top (tie embedded 1.5, BO3 tie seat 6.51)


def rail_profile(scale=1.0, lod=0):
    """Half profile (y >= 0 half mirrored), counter-clockwise outline in (y, z) inches, z = 0 at the base."""
    s = scale
    # base 5.5 wide, 0.3 edge, slope to web, web 0.62, fillets, head 2.72 wide 1.7 deep with rounded top
    pts = [(0.0, 0.0), (2.75, 0.0), (2.75, 0.32), (1.2, 0.95), (0.31, 1.45), (0.31, 4.5), (1.18, 4.95),
           (1.36, 5.25), (1.36, 6.25), (1.15, 6.55), (0.7, 6.65), (0.0, 6.68)]
    if lod:
        pts = [(0.0, 0.0), (2.75, 0.0), (2.75, 0.32), (0.31, 1.45), (0.31, 4.5), (1.36, 5.1), (1.36, 6.4),
               (0.8, 6.65), (0.0, 6.68)]
    half = [(y * s, z * s) for y, z in pts]
    # full outline: right half from bottom centre up, then the left half mirrored back down
    right = half[:-1]
    left = [(-y, z) for y, z in reversed(half[1:])]
    return right + [half[-1]] + left[1:]


HEAD_BAND = 0.48     # the top HEAD_BAND inches of a profile are the polished running band


def extrude_profile(bm, prof, x0, x1, cy, cz, mats, texel, head_mat, web_mat):
    """Extrude a closed (y, z) outline along x; quads get the head or web material; UV v = perimeter / texel."""
    n = len(prof)
    head_z = max(z for _, z in prof) - HEAD_BAND
    per = [0.0]
    for i in range(1, n + 1):
        a, b = prof[i - 1], prof[i % n]
        per.append(per[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    ring0 = [bm.verts.new(((x0) * INCH, (cy + y) * INCH, (cz + z) * INCH)) for y, z in prof]
    ring1 = [bm.verts.new(((x1) * INCH, (cy + y) * INCH, (cz + z) * INCH)) for y, z in prof]
    uv = bm.loops.layers.uv.verify()
    for i in range(n):
        j = (i + 1) % n
        f = bm.faces.new((ring0[i], ring1[i], ring1[j], ring0[j]))
        zmid = (prof[i][1] + prof[j][1]) / 2
        f.material_index = mats[head_mat] if zmid >= head_z else mats[web_mat]
        coords = ((x0, per[i]), (x1, per[i]), (x1, per[i + 1]), (x0, per[i + 1]))
        for loop, (u, v) in zip(f.loops, coords):
            loop[uv].uv = (u / texel, v / texel)
    # end caps (visible at the buffer stop / tunnel mouth): fan triangles
    for ring, sign in ((ring0, -1), (ring1, 1)):
        c = bm.verts.new((ring[0].co.x, cy * INCH, (cz + 3.3) * INCH))
        for i in range(n):
            j = (i + 1) % n
            tri = (c, ring[j], ring[i]) if sign > 0 else (c, ring[i], ring[j])
            f = bm.faces.new(tri)
            f.material_index = mats[web_mat]
            for loop in f.loops:
                loop[uv].uv = (loop.vert.co.y / INCH / texel, loop.vert.co.z / INCH / texel)


def new_object(name, materials):
    me = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for m in materials:
        mat = bpy.data.materials.get(m) or bpy.data.materials.new(m)
        me.materials.append(mat)
    return ob, {m: i for i, m in enumerate(materials)}


def finish(ob, bm):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()


def build_rails(L, texel, lod):
    ob, mats = new_object('rails', ['iwz_rail_web', 'iwz_rail_head'])
    bm = bmesh.new()
    prof = rail_profile(lod=lod)
    for side in (-1, 1):
        extrude_profile(bm, prof, 0, L, side * RAIL_CY, 0.0, mats, texel, 'iwz_rail_head', 'iwz_rail_web')
    finish(ob, bm)
    return ob


def build_third_rail(L, texel, lod):
    ob, mats = new_object('third_rail', ['iwz_rail_web', 'iwz_rail_head', 'iwz_insulator'])
    bm = bmesh.new()
    cy = -(RAIL_CY + 27.5)
    # conductor top 3.5 in above the running rail top; z = 0 is the ballast top, RAIL_BASE_Z the running rail base
    ins_h = RAIL_BASE_Z + 6.68 + 3.5 - 6.68 * 0.8
    prof = rail_profile(scale=0.8, lod=lod)
    extrude_profile(bm, prof, 0, L, cy, ins_h, mats, texel, 'iwz_rail_head', 'iwz_rail_web')
    uv = bm.loops.layers.uv.verify()
    seg = 8 if lod else 16
    for xc in [L / 4 + k * 128 for k in range(int(L // 128))]:
        # porcelain insulator: stacked rings (sheds) from the base plate to the rail base
        rings = [(0.0, 2.2), (0.6, 2.2), (0.9, 1.6), (1.4, 2.0), (1.8, 1.4), (2.3, 1.8), (2.7, 1.3), (ins_h, 1.3)]
        prev = None
        for zi, (z, r) in enumerate(rings):
            ring = [bm.verts.new(((xc + r * math.cos(2 * math.pi * k / seg)) * INCH,
                                  (cy + r * math.sin(2 * math.pi * k / seg)) * INCH, z * INCH)) for k in range(seg)]
            if prev is not None:
                for k in range(seg):
                    f = bm.faces.new((prev[k], prev[(k + 1) % seg], ring[(k + 1) % seg], ring[k]))
                    f.material_index = mats['iwz_insulator']
                    for loop, (u, v) in zip(f.loops, ((k, zi - 1), (k + 1, zi - 1), (k + 1, zi), (k, zi))):
                        loop[uv].uv = (u / seg, v / 8.0)
            prev = ring
        # steel base plate under the insulator
        for zz in ((-1.0, 0.0),):
            pass
    finish(ob, bm)
    return ob


def build_ballast(L, texel):
    ob, mats = new_object('ballast', ['iwz_ballast'])
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    top, base, h = 62.0, 86.0, 16.0
    # cross section: shoulders slightly rounded (3 steps per slope)
    sec = [(-base, -h), (-top - 14, -h + 6), (-top - 4, -2.5), (-top, 0.0), (top, 0.0), (top + 4, -2.5),
           (top + 14, -h + 6), (base, -h)]
    nx = int(L // 32)
    rows = []
    for i in range(nx + 1):
        x = L * i / nx
        rows.append([bm.verts.new((x * INCH, y * INCH, z * INCH)) for y, z in sec])
    for i in range(nx):
        for k in range(len(sec) - 1):
            f = bm.faces.new((rows[i][k], rows[i][k + 1], rows[i + 1][k + 1], rows[i + 1][k]))
            f.material_index = 0
            for loop in f.loops:
                c = loop.vert.co
                loop[uv].uv = (c.x / INCH / texel, c.y / INCH / texel)
    finish(ob, bm)
    return ob


def export(objs, path):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_yup=True,
                              export_apply=True, export_materials='EXPORT')


def materials_json(path, images, mats):
    rel = os.path.relpath(images, os.path.dirname(path)).replace(os.sep, '/')
    out = []
    for m in mats:
        e = {'name': m['name'], 'alpha': 'opaque', 'techset': 'authored'}
        for key in ('albedo', 'normal', 'roughness', 'specular', 'occlusion'):
            if m.get(key):
                b = {'path': rel + '/' + m[key]}
                if key == 'roughness':
                    b.update(channel='r', invert=True)
                if key == 'normal':
                    b['encoding'] = 'xy'
                e[key] = b
        if m.get('tint'):
            e['color_tint'] = {'color': m['tint']}
        if m.get('layers'):
            e['layers'] = [{**l, **{k: {'path': rel + '/' + l[k], **({'channel': 'r', 'invert': True} if k == 'roughness' else {})}
                                   for k in ('albedo', 'normal', 'roughness') if l.get(k)},
                            **({'mask': {'path': rel + '/' + l['mask'], 'channel': 'r', 'uv_scale': l.get('mask_scale', [1, 1])}}
                               if l.get('mask') else {})} for l in m['layers']]
        out.append(e)
    json.dump({'adapter': 'authored', 'format': 'greyhound-materials', 'materials': out}, open(path, 'w'), indent=1)


MATERIALS = [
    # rusted rail steel; the BO3 micro maps tile 2x per UV unit
    {'name': 'iwz_rail_web', 'albedo': 'i_t7_micro_metal_rust_heavy_01_c.png', 'roughness': 'i_t7_micro_metal_rust_heavy_01_g.png',
     'normal': 'i_t7_micro_metal_rust_n.png'},
    # running band: bright worn steel polished by wheels
    {'name': 'iwz_rail_head', 'albedo': 'i_t7_micro_metal_bare_scuffed_01_c.png', 'roughness': 'i_t7_micro_metal_bare_scuffed_01_g.png',
     'normal': 'i_t7_micro_metal_bare_scuffed_01_n.png', 'specular': 'i_t7_micro_metal_bare_01_s.png'},
    # glazed porcelain, dark brown
    {'name': 'iwz_insulator', 'albedo': 'i_t7_micro_plastic_rough_02_c.png', 'roughness': 'i_t7_micro_plastic_rough_02_g.png',
     'normal': 'i_t7_micro_plastic_rough_02_n.png', 'tint': [0.16, 0.07, 0.035]},
    {'name': 'iwz_ballast', 'albedo': 'gravel_pebble_bed_c.png', 'normal': 'gravel_pebble_bed_n.png'},
]


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--images', required=True)
    ap.add_argument('--length', type=float, default=256.0)
    ap.add_argument('--texel', type=float, default=48.0, help='inches per UV unit (rails)')
    ap.add_argument('--ballast-texel', type=float, default=72.0)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    L = a.length
    tag = '%d' % L
    for lod in (0, 1):
        sfx = '' if lod == 0 else '_lod1'
        for builder, name in ((lambda: build_rails(L, a.texel, lod), 'rails'),
                              (lambda: build_third_rail(L, a.texel, lod), 'third_rail'),
                              (lambda: build_ballast(L, a.ballast_texel), 'ballast')):
            bpy.ops.wm.read_factory_settings(use_empty=True)
            ob = builder()
            path = os.path.join(a.out, '%s_%s%s.glb' % (name, tag, sfx))
            export([ob], path)
            used = {s.material.name for s in ob.material_slots if s.material}
            materials_json(os.path.splitext(path)[0] + '.materials.json', a.images,
                           [m for m in MATERIALS if m['name'] in used])
            print('TRACKKIT', path)


if __name__ == '__main__':
    main()

"""Headless Blender preview of glTF models (offline look check, not engine evidence).

  blender -b --factory-startup -P blender_preview.py -- --out <dir> --glb a.glb [b.glb ...]
          [--view name:x,y,z:tx,ty,tz[:lens]] ... [--size 1280x720] [--engine workbench|eevee]

Coordinates of --view are game inches (Z up), like the map: the camera at x,y,z looks at tx,ty,tz.
Workbench draws base-colour textures with studio lighting; eevee uses the glTF materials.
"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Vector

INCH = 0.0254


def game_to_blender(v):
    # glTF importer maps glTF (x, y, z) Y-up to Blender (x, -z, y); game (x, y, z) Z-up inches == Blender Z-up
    return Vector((v[0] * INCH, v[1] * INCH, v[2] * INCH))


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--glb', nargs='+', required=True)
    ap.add_argument('--view', action='append', default=[])
    ap.add_argument('--size', default='1280x720')
    ap.add_argument('--engine', default='workbench')
    a = ap.parse_args(argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for g in a.glb:
        bpy.ops.import_scene.gltf(filepath=g)
    scene = bpy.context.scene
    w, h = (int(x) for x in a.size.split('x'))
    scene.render.resolution_x, scene.render.resolution_y = w, h
    if a.engine == 'workbench':
        scene.render.engine = 'BLENDER_WORKBENCH'
        scene.display.shading.light = 'STUDIO'
        scene.display.shading.color_type = 'TEXTURE'
        scene.display.shading.show_shadows = True
        scene.display.shading.show_cavity = True
    else:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
        world = bpy.data.worlds.new('w')
        world.color = (0.4, 0.4, 0.45)
        scene.world = world
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    scene.collection.objects.link(cam)
    scene.camera = cam
    os.makedirs(a.out, exist_ok=True)
    views = a.view or ['auto:0,0,0:0,0,0']
    meshes = [o for o in scene.objects if o.type == 'MESH']
    for spec in views:
        parts = spec.split(':')
        name = parts[0]
        if name == 'auto':
            pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
            mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
            mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
            c = (mn + mx) / 2
            r = (mx - mn).length
            eye, tgt, lens = c + Vector((0.55, -0.75, 0.35)) * r, c, 35
        else:
            eye = game_to_blender([float(x) for x in parts[1].split(',')])
            tgt = game_to_blender([float(x) for x in parts[2].split(',')])
            lens = float(parts[3]) if len(parts) > 3 else 24
        cam.location = eye
        cam.rotation_euler = (tgt - eye).to_track_quat('-Z', 'Y').to_euler()
        cam.data.lens = lens
        cam.data.clip_start, cam.data.clip_end = 0.01, 500
        scene.render.filepath = os.path.join(a.out, name + '.png')
        bpy.ops.render.render(write_still=True)
        print('PREVIEW', scene.render.filepath)


if __name__ == '__main__':
    main()

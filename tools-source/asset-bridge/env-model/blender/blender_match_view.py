"""Render a model at an engine view (headless Blender): material-ID pass and reference colour pass.

  blender -b --factory-startup -P blender_match_view.py -- --glb model.glb --origin x,y,z --yaw deg
          --eye x,y,z --view yaw,pitch --hfov deg --size 1920x1080 --out <dir> --tag <name>

Game units (inches, Z up), IW angles (yaw about Z from +X, pitch positive looks down). Writes <tag>_id.png (flat
colour per material, legend <tag>_legend.json) and <tag>_ref.png (base-colour texture, flat light: the material's
intended colour without lighting).
"""
import argparse
import colorsys
import json
import math
import os
import sys

import bpy
from mathutils import Vector

INCH = 0.0254


def vec(s):
    return [float(x) for x in s.split(',')]


def main():
    argv = sys.argv[sys.argv.index('--') + 1:]
    ap = argparse.ArgumentParser()
    for k in ('glb', 'origin', 'eye', 'view', 'out', 'tag'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--yaw', type=float, default=0.0)
    ap.add_argument('--hfov', type=float, default=80.0)
    ap.add_argument('--size', default='1920x1080')
    a = ap.parse_args(argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=a.glb)
    o = vec(a.origin)
    for ob in [x for x in bpy.context.scene.objects if x.parent is None]:
        ob.location = Vector(o) * INCH
        ob.rotation_mode = 'XYZ'
        ob.rotation_euler = (0, 0, math.radians(a.yaw))
    scene = bpy.context.scene
    w, h = (int(x) for x in a.size.split('x'))
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'FLAT'
    scene.display.shading.show_shadows = False
    scene.display.shading.show_cavity = False
    scene.view_settings.view_transform = 'Standard'
    scene.render.dither_intensity = 0
    scene.render.film_transparent = True
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    scene.collection.objects.link(cam)
    scene.camera = cam
    e = Vector(vec(a.eye)) * INCH
    yaw, pitch = (math.radians(x) for x in vec(a.view))
    fwd = Vector((math.cos(pitch) * math.cos(yaw), math.cos(pitch) * math.sin(yaw), -math.sin(pitch)))
    cam.location = e
    cam.rotation_euler = fwd.to_track_quat('-Z', 'Y').to_euler()
    cam.data.sensor_fit = 'HORIZONTAL'
    cam.data.angle = math.radians(a.hfov)
    cam.data.clip_start, cam.data.clip_end = 0.02, 400
    os.makedirs(a.out, exist_ok=True)
    scene.display.shading.color_type = 'TEXTURE'
    scene.render.filepath = os.path.join(a.out, a.tag + '_ref.png')
    bpy.ops.render.render(write_still=True)
    mats = sorted({m.name for x in scene.objects if x.type == 'MESH' for m in x.data.materials if m})
    legend = {}
    for i, n in enumerate(mats):
        r, g, b = colorsys.hsv_to_rgb((i * 0.618034) % 1.0, 0.5 + 0.5 * ((i * 7) % 3) / 2, 0.55 + 0.45 * ((i * 5) % 2))
        lin = [r, g, b]
        bpy.data.materials[n].diffuse_color = (*lin, 1)
        srgb = [round((12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055) * 255) for c in lin]
        legend[n] = srgb
    scene.display.shading.color_type = 'MATERIAL'
    scene.render.filepath = os.path.join(a.out, a.tag + '_id.png')
    bpy.ops.render.render(write_still=True)
    json.dump(legend, open(os.path.join(a.out, a.tag + '_legend.json'), 'w'), indent=1)
    print('MATCHVIEW', a.tag)


if __name__ == '__main__':
    main()

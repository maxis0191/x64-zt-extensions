"""Key a clear motion on a game skeleton in Blender and export it as glb (Blender 4.x / 5.x, command line).

    blender -b --factory-startup -P blender_key_clip.py -- --rig rig.glb --out clip.glb
        --turn j_shoulder_le:x:100 --turn j_spine4:z:-35 [--seconds 2] [--fps 30] [--name my_clip]

`rig.glb` comes from `iw7_anim_gltf.py skeleton`. Each --turn rotates one bone about a world axis of the scene
(x = the character's forward, z = up: Blender shows the game's axes) through the bone's own joint, from the
bind pose at the first frame to the turned pose at the last, with Blender's default easing. List a parent
before its children. This is the smallest honest example of "animated in Blender": an animator would key the
same armature by hand and export with the same settings.
"""
import argparse
import math
import sys

import bpy
from mathutils import Matrix

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--rig', required=True)
ap.add_argument('--out', required=True)
ap.add_argument('--turn', action='append', default=[])
ap.add_argument('--seconds', type=float, default=2.0)
ap.add_argument('--fps', type=int, default=30)
ap.add_argument('--name', default='blender_clip')
a = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a.rig)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
scene = bpy.context.scene
scene.render.fps = a.fps
last = 1 + int(round(a.seconds * a.fps))
scene.frame_start, scene.frame_end = 1, last
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')
turns = []
for text in a.turn:
    bone, axis, deg = text.split(':')
    turns.append((arm.pose.bones[bone], axis.upper(), math.radians(float(deg))))
for pb, _, _ in turns:
    pb.rotation_mode = 'QUATERNION'
scene.frame_set(1)
for pb, _, _ in turns:
    pb.keyframe_insert('rotation_quaternion', frame=1)
scene.frame_set(last)
for pb, axis, angle in turns:
    head = pb.matrix.to_translation()
    pb.matrix = Matrix.Translation(head) @ Matrix.Rotation(angle, 4, axis) @ Matrix.Translation(-head) @ pb.matrix
    bpy.context.view_layer.update()
    pb.keyframe_insert('rotation_quaternion', frame=last)
if arm.animation_data and arm.animation_data.action:
    arm.animation_data.action.name = a.name
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.export_scene.gltf(filepath=a.out, export_format='GLB', export_animations=True, export_force_sampling=True,
                          export_frame_range=True, export_yup=True)
print('BLENDER_KEY_CLIP wrote', a.out, 'frames', last - 1, 'bones', [pb.name for pb, _, _ in turns])

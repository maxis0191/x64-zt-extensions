"""Lower LODs of glTF models with Blender's collapse decimation (headless), materials and UV seams kept.

  blender -b --factory-startup -P blender_decimate.py -- --ratio 0.35 --out <dir> <a.glb> [b.glb ...]

Each input becomes <out>/<name>_r<ratio>.glb. Skinned GrayWolf meshes are applied to their joint first (the rigid
pose), so the output is plain static geometry in the same space. Triangle counts before/after are printed.
"""
import argparse
import os
import sys

import bpy


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--ratio', type=float, default=0.35)
    ap.add_argument('--out', required=True)
    ap.add_argument('glbs', nargs='+')
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    for path in a.glbs:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=path)
        meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
        before = after = 0
        for o in meshes:
            bpy.context.view_layer.objects.active = o
            for m in list(o.modifiers):              # bake the armature (rigid bind) into the mesh
                bpy.ops.object.modifier_apply(modifier=m.name)
            mw = o.matrix_world.copy()               # then the world transform: plain geometry in scene space
            o.parent = None
            o.data.transform(mw)
            o.matrix_world.identity()
            before += sum(len(p.vertices) - 2 for p in o.data.polygons)
            mod = o.modifiers.new('dec', 'DECIMATE')
            mod.decimate_type = 'COLLAPSE'
            mod.ratio = a.ratio
            mod.use_collapse_triangulate = True
            bpy.ops.object.modifier_apply(modifier='dec')
            after += sum(len(p.vertices) - 2 for p in o.data.polygons)
        for o in list(bpy.context.scene.objects):
            if o.type == 'ARMATURE':
                bpy.data.objects.remove(o, do_unlink=True)
        bpy.ops.object.select_all(action='DESELECT')
        for o in meshes:
            o.select_set(True)
        stem = os.path.splitext(os.path.basename(path))[0]
        out = os.path.join(a.out, '%s_r%02d.glb' % (stem, int(a.ratio * 100)))
        bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=True, export_yup=True,
                                  export_apply=True, export_materials='EXPORT', export_skins=False)
        print('DECIMATE %s tris %d -> %d' % (out, before, after))


if __name__ == '__main__':
    main()

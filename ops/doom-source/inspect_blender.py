"""Future raw-datablock inspector; no depsgraph, drivers or embedded Text execution.

Not executed yet. Admit the complete load before using factory startup and
disable-autoexec BEFORE the .blend path, then this controlled local script.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

IMP_SHA = 'c94068d904c5495feb1f29779eba04a43f6bd5efd0d29d16729564574c9a2fd3'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def vec(value):
    result = [float(v) for v in value]
    require(len(result) <= 16 and all(math.isfinite(v) for v in result), 'bounded finite source vector')
    return result


def matrix(value):
    return [vec(row) for row in value]


def inspect(output):
    import bpy
    require(not bpy.context.preferences.filepaths.use_scripts_auto_execute, 'automatic Python execution must remain disabled')
    source = Path(bpy.data.filepath).resolve()
    require(source.suffix.lower() == '.blend' and source.stat().st_size == 12268984, 'exact Imp source size')
    require(hashlib.sha256(source.read_bytes()).hexdigest() == IMP_SHA, 'exact Imp source hash')
    output = output.absolute()
    require(not output.exists(), 'fresh inspector result')
    for parent in (output, *output.parents):
        require(not parent.is_symlink() and not parent.is_junction(), 'linked output refused')
    for values, bound, name in [(bpy.data.objects, 2048, 'objects'), (bpy.data.meshes, 256, 'meshes'),
                                (bpy.data.armatures, 8, 'armatures'), (bpy.data.images, 64, 'images'),
                                (bpy.data.materials, 256, 'materials'), (bpy.data.actions, 128, 'actions')]:
        require(len(values) <= bound, f'bounded {name}')
    require(sum(len(mesh.vertices) for mesh in bpy.data.meshes) <= 1000000, 'bounded raw mesh positions')
    armatures = []
    for armature in bpy.data.armatures:
        require(len(armature.bones) <= 1024, 'bounded raw bones')
        armatures.append({'name': armature.name, 'bones': [{'name': bone.name, 'parent': bone.parent.name if bone.parent else None,
                          'use_deform': bool(bone.use_deform), 'head_local': vec(bone.head_local), 'tail_local': vec(bone.tail_local),
                          'matrix_local': matrix(bone.matrix_local)} for bone in armature.bones]})
    objects = []
    for obj in bpy.data.objects:
        require(len(obj.modifiers) <= 32 and len(obj.vertex_groups) <= 1024, 'bounded modifiers/groups')
        animation = obj.animation_data
        objects.append({'name': obj.name, 'type': obj.type, 'data': obj.data.name if obj.data else None,
                        'parent': obj.parent.name if obj.parent else None, 'matrix_local': matrix(obj.matrix_local),
                        'armature_modifiers': [{'name': modifier.name, 'armature_object': modifier.object.name if modifier.object else None,
                          'vertex_group': modifier.vertex_group, 'vertex_groups_enabled': bool(modifier.use_vertex_groups),
                          'envelopes_enabled': bool(modifier.use_bone_envelopes)} for modifier in obj.modifiers if modifier.type == 'ARMATURE'],
                        'vertex_groups': [group.name for group in obj.vertex_groups],
                        'action': animation.action.name if animation and animation.action else None,
                        'drivers_count': len(animation.drivers) if animation else 0,
                        'nla_tracks_count': len(animation.nla_tracks) if animation else 0})
    meshes = [{'name': mesh.name, 'positions': len(mesh.vertices), 'edges': len(mesh.edges), 'polygons': len(mesh.polygons),
               'uv_layers': [layer.name for layer in mesh.uv_layers], 'materials': [mat.name if mat else None for mat in mesh.materials]} for mesh in bpy.data.meshes]
    images = [{'name': image.name, 'source': image.source, 'packed': bool(image.packed_file),
               'packed_file_count': len(image.packed_files), 'dimensions': list(image.size), 'is_float': bool(image.is_float),
               'colorspace': image.colorspace_settings.name, 'file_basename': Path(image.filepath).name} for image in bpy.data.images]
    actions = [{'name': action.name, 'frame_range': vec(action.frame_range), 'fcurves_count': len(action.fcurves)} for action in bpy.data.actions]
    result = {'schema': 'iw7.imp-blender-inspection/1', 'source_sha256': IMP_SHA, 'source_bytes': source.stat().st_size,
              'blender_version': bpy.app.version_string, 'automatic_script_execution_disabled': True,
              'embedded_text_count': len(bpy.data.texts), 'embedded_text_executed': False, 'drivers_evaluated': False,
              'depsgraph_evaluated': False, 'mesh_modifiers_applied': False, 'armatures': armatures, 'objects': objects,
              'meshes': meshes, 'images': images, 'actions': actions, 'deform_weights_exported': False,
              'clips_baked': False, 'retargeted': False, 'converted_iw7': False, 'ready': False}
    require(hashlib.sha256(source.read_bytes()).hexdigest() == IMP_SHA, 'Imp source changed during inspection')
    require(not bpy.context.preferences.filepaths.use_scripts_auto_execute, 'autoexec changed during inspection')
    serialized = json.dumps(result, indent=2)
    require(len(serialized.encode()) <= 8 * 1024 * 1024, 'bounded inspection output')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        stream.write(serialized)
    print(json.dumps({'schema': result['schema'], 'meshes': len(meshes), 'armatures': len(armatures), 'actions': len(actions), 'ready': False}))


if __name__ == '__main__':
    require('--' in sys.argv, 'explicit controlled script argument separator')
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    inspect(args.output)

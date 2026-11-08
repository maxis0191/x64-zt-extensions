"""Port Black Ops III (or any glTF) environment models to IW7 usermap model sources in one command.

    python t7_env_port.py --manifest port.json --out <dump root> [--graywolf <GrayWolf.exe>]

The manifest lists IW7 models, each composed of one or more source models (GrayWolf exports or Blender-made
.glb) with an offset/yaw, plus material overrides. Stages, all data-driven (no model names in code):

1. export   GrayWolf (graywolf_mcp.py, stdio MCP) exports the BO3 models as .glb + PNG images + materials.json
            into <out>/gw, unless the manifest's "export_dir" already holds them (copied, GrayWolf output can vanish)
2. materials t7_env_material.py bakes every BO3 material the models use into an IW7 model material
            (opaque / cutout / decal / glass / emissive templates; skipped roles drop their triangles)
3. models   mesh_glb.py reads the meshes in game space (inches, Z up); iw7_model_author.py checks the normals
            against the faces (rebuilds them with creases when < 90 % agree), welds, splits at 65535 vertices,
            computes tangents and writes xmodel/<name>.xmb + xsurface/<name>_lod<i>.xsb (LOD order checked:
            the most detailed first; extra LODs come from Blender decimation, blender_lods.py)
4. collision clip boxes in model space from a surface voxelisation (greedy-merged), for the map generator's
            world collision (players, bullets) and navmesh cut; written to <out>/collision/<name>.json
5. report   <out>/port_report.json: per model triangles per LOD, surfaces, materials and roles, normals,
            bounds, origin, sizes of the written files, collision boxes; exit 1 on any failure

<out> is a dump root that kit_import.py (iw7-creator-sdk) links into a usermap zone like a stock zone dump:
xmodel/, xsurface/, materials/, images/*.dds (embedded pixels), techsets/state|constantbuffer/.
"""
import argparse
import glob
import json
import math
import os
import shutil
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mesh_glb  # noqa: E402
import iw7_model_author as author  # noqa: E402
import t7_env_material as envmat  # noqa: E402
import collision_boxes  # noqa: E402


def gw_export(cfg, out_gw, graywolf_exe):
    sys.path.insert(0, os.path.join(HERE, '..', 't7-weapons'))
    from graywolf_mcp import GrayWolf
    names = sorted({p['model'] for m in cfg['models'] for p in m['parts'] if not p.get('glb')})
    gw = GrayWolf(graywolf_exe)
    found = gw.call('graywolf_find_assets', {'install': cfg['install'], 'names': names, 'kinds': ['model']})
    zones = {}
    for row in found.get('items', []):
        zones.setdefault(row['name'], row['zone'])          # smallest zone first
    by_zone = {}
    for n, z in zones.items():
        by_zone.setdefault(z, []).append('model:' + n)
    for z, assets in by_zone.items():
        r = gw.call('graywolf_export', {'install': cfg['install'], 'zones': [z], 'out_name': 'env_port',
                                        'assets': assets, 'model_format': ['glb'], 'image_format': 'png'})
        src = os.path.join(r['out'], 'bo3')
        shutil.copytree(src, out_gw, dirs_exist_ok=True)
    missing = [n for n in names if n not in zones]
    if missing:
        raise SystemExit('GrayWolf did not find: %s' % missing)


def part_paths(gw_root, part):
    if part.get('glb'):
        glb = part['glb']
        mj = os.path.splitext(glb)[0] + '.materials.json'
        return glb, (mj if os.path.exists(mj) else None)
    d = os.path.join(gw_root, 'models', part['model'])
    glb = glob.glob(os.path.join(d, '*_LOD0.glb'))
    if not glb:
        raise SystemExit('no export for %s in %s' % (part['model'], d))
    mj = glob.glob(os.path.join(d, '*_LOD0.materials.json'))
    return glb[0], (mj[0] if mj else None)


def transform(group, offset, yaw):
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    r = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    return {'P': group['P'] @ r.T + np.asarray(offset, float), 'N': group['N'] @ r.T, 'UV': group['UV'],
            'tris': group['tris']}


def merge(groups):
    P, N, UV, T, base = [], [], [], [], 0
    for g in groups:
        P.append(g['P']); N.append(g['N']); UV.append(g['UV']); T.append(g['tris'] + base)
        base += len(g['P'])
    return {'P': np.concatenate(P), 'N': np.concatenate(N), 'UV': np.concatenate(UV), 'tris': np.concatenate(T)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--graywolf', help='GrayWolf.exe (stage 1 when the manifest has no export_dir)')
    ap.add_argument('--skip-materials', action='store_true', help='reuse the materials of an earlier run')
    a = ap.parse_args(argv)
    cfg = json.load(open(a.manifest))
    out = a.out
    os.makedirs(out, exist_ok=True)
    gw_root = os.path.join(out, 'gw')
    if cfg.get('export_dir'):
        if not os.path.isdir(os.path.join(gw_root, 'models')):
            shutil.copytree(cfg['export_dir'], gw_root, dirs_exist_ok=True)
    elif not os.path.isdir(os.path.join(gw_root, 'models')):
        if not a.graywolf:
            raise SystemExit('no export_dir in the manifest and no --graywolf')
        gw_export(cfg, gw_root, a.graywolf)
    prefix = cfg.get('prefix', 'mo/t7e_')
    report = {'manifest': os.path.abspath(a.manifest), 'models': [], 'materials': [], 'errors': []}

    # ---- materials
    mat_jsons = []
    for m in cfg['models']:
        for p in m['parts']:
            _, mj = part_paths(gw_root, p)
            if mj and mj not in mat_jsons:
                mat_jsons.append(mj)
    mat_report_path = os.path.join(out, 'materials.report.json')
    if a.skip_materials and os.path.exists(mat_report_path):
        mats = json.load(open(mat_report_path))['materials']
    else:
        args = mat_jsons + ['--templates', cfg['templates'], '--texconv', cfg['texconv'], '--out', out,
                            '--prefix', prefix, '--size', str(cfg.get('texture_size', 1024))]
        if cfg.get('material_overrides'):
            mp = os.path.join(out, 'material_overrides.json')
            json.dump(cfg['material_overrides'], open(mp, 'w'), indent=1)
            args += ['--manifest', mp]
        if cfg.get('keep_materials'):
            args += ['--keep'] + cfg['keep_materials']
        import io as _io
        import contextlib
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            envmat.main(args)
        mats = json.loads(buf.getvalue())['materials']
        json.dump({'materials': mats}, open(mat_report_path, 'w'), indent=1)
    report['materials'] = mats
    role = {m['material']: m for m in mats}

    # ---- models
    def compose(m, parts):
        groups = {}
        for p in parts:
            glb, _ = part_paths(gw_root, p)
            skip = set(p.get('skip_materials', []))
            for mat, g in mesh_glb.meshes(glb).items():
                info = role.get(mat)
                if mat in skip or any(k in mat for k in p.get('skip_contains', [])):
                    continue
                if info is None:
                    report['errors'].append('%s: material %s was not baked' % (m['name'], mat))
                    continue
                if info['role'] == 'skip':
                    continue
                for off in p.get('repeat', [p.get('offset', [0, 0, 0])]):
                    groups.setdefault(info['iw7'], []).append(transform(g, off, p.get('yaw', 0)))
        return {k: merge(v) for k, v in groups.items()}

    for m in cfg['models']:
        groups = compose(m, m['parts'])
        lods = [{'dist': m.get('lod0_dist', 0.0), 'groups': groups}]
        for extra in m.get('lods', []):              # coarser LODs from their own (simpler) part lists
            lods.append({'dist': extra['dist'], 'groups': compose(m, extra['parts'])})
        if m.get('origin') == 'base':
            allp = np.concatenate([g['P'] for g in groups.values()])
            lo, hi = allp.min(0), allp.max(0)
            shift = np.array([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
            for lod in lods:
                for g in lod['groups'].values():
                    g['P'] = g['P'] + shift
        try:
            rep = author.build_model(m['name'], lods, out, recompute_normals=m.get('recompute_normals', False))
        except ValueError as e:
            report['errors'].append('%s: %s' % (m['name'], e))
            continue
        rep['parts'] = m['parts']
        rep['roles'] = {k: next((x['role'] for x in mats if x.get('iw7') == k), 'source') for k in groups}
        files = [os.path.join(out, 'xmodel', m['name'] + '.xmb')] + \
            [os.path.join(out, 'xsurface', l['name'] + '.xsb') for l in rep['lods']]
        rep['bytes'] = sum(os.path.getsize(f) for f in files)
        if m.get('collision', {}).get('voxel'):
            col = m['collision']
            solid = {k: g for k, g in groups.items()
                     if rep['roles'].get(k) not in ('decal',) and not any(s in k for s in col.get('exclude', []))}
            boxes = collision_boxes.boxes_from_mesh(solid, col['voxel'], col.get('min_thickness', 4.0))
            os.makedirs(os.path.join(out, 'collision'), exist_ok=True)
            json.dump({'model': m['name'], 'voxel': col['voxel'], 'boxes': boxes},
                      open(os.path.join(out, 'collision', m['name'] + '.json'), 'w'))
            rep['collision_boxes'] = len(boxes)
        report['models'].append(rep)
    img_bytes = sum(os.path.getsize(f) for f in glob.glob(os.path.join(out, 'images', '*.dds')))
    report['image_bytes'] = img_bytes
    json.dump(report, open(os.path.join(out, 'port_report.json'), 'w'), indent=1, default=str)
    for r in report['models']:
        print('%-34s lods %s tris %s surfaces %d materials %d bytes %.1f MB boxes %s' % (
            r['name'], len(r['lods']), [l['tris'] for l in r['lods']], r['surfaces'], len(r['materials']),
            r['bytes'] / 1e6, r.get('collision_boxes')))
    print('images %.1f MB; errors %s' % (img_bytes / 1e6, report['errors']))
    return 1 if report['errors'] else 0


if __name__ == '__main__':
    sys.exit(main())

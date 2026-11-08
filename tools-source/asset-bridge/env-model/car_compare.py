"""Per-material comparison of an in-engine frame against a reference render of the same model from the same camera.

  python car_compare.py --blender <blender.exe> --glb <model.glb> --origin x,y,z --yaw deg
         --view name:eye_x,eye_y,eye_z:yaw,pitch:<engine on frame>[:<engine off frame>] [--view ...]
         [--hfov 80.7] [--fit-fov] --out <dir> [--json report.json]

For each view, Blender (blender/blender_match_view.py) renders the model at the engine camera: a material-ID pass and
a reference pass (the material's base-colour texture, unlit). Pixels count for a material only where the ID pass shows
it AND the engine frame shows the model (with an off frame: where on and off differ; without one: everywhere the ID
pass covers). Per material region it measures, in the engine frame and in the reference:
  chroma   mean linear RGB / its sum (hue and saturation, independent of light level)
  white balance: the engine colour is divided by the median engine/reference colour ratio of the regions that are grey
           in the reference (all opaque regions when none is)
  luma     mean linear luma; the engine/reference ratio is divided by the median ratio of all regions in the view, so
           a region that is much darker or brighter than the rest of the model stands out ('rel_luma')
  hf       high-frequency energy: mean |Laplacian of luma| / mean luma (noise such as a mask used as colour: 'granite')
  black    share of engine pixels with luma < 12/255
Verdict per region: FAIL when chroma distance > --chroma (0.06), rel_luma outside [0.45, 2.2], hf ratio > --hf (2.0) or
black share > 0.35. --fit-fov picks the horizontal FOV (70..90) whose model silhouette best matches the engine A/B mask.
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)


def lin(img):
    c = img[..., :3].astype(np.float32) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lap(l):
    p = np.pad(l, 1, mode='edge')
    return np.abs(4 * l - p[:-2, 1:-1] - p[2:, 1:-1] - p[1:-1, :-2] - p[1:-1, 2:])


def render(a, name, eye, ang, hfov, out):
    tag = '%s_f%d' % (name, round(hfov * 10))
    if not os.path.exists(os.path.join(out, tag + '_id.png')):
        subprocess.run([a.blender, '-b', '--factory-startup', '-P', os.path.join(HERE, 'blender', 'blender_match_view.py'), '--',
                        '--glb', a.glb, '--origin', a.origin, '--yaw', str(a.yaw), '--eye', eye, '--view', ang,
                        '--hfov', str(hfov), '--out', out, '--tag', tag, '--size', '%dx%d' % a.size],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ids = np.asarray(Image.open(os.path.join(out, tag + '_id.png')).convert('RGBA'))
    ref = np.asarray(Image.open(os.path.join(out, tag + '_ref.png')).convert('RGBA'))
    legend = json.load(open(os.path.join(out, tag + '_legend.json')))
    return ids, ref, legend


def model_mask(on, off):
    if off is None:
        return None
    m = np.abs(on.astype(int) - off.astype(int)).sum(2) > 30
    k = sum(np.roll(np.roll(m, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1)) >= 6
    return k


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--blender', required=True)
    ap.add_argument('--glb', required=True)
    ap.add_argument('--origin', required=True)
    ap.add_argument('--yaw', type=float, default=0.0)
    ap.add_argument('--view', action='append', required=True)
    ap.add_argument('--hfov', type=float, default=80.7)
    ap.add_argument('--fit-fov', action='store_true')
    ap.add_argument('--chroma', type=float, default=0.06)
    ap.add_argument('--hf', type=float, default=2.0)
    ap.add_argument('--min-px', type=int, default=1500)
    ap.add_argument('--out', required=True)
    ap.add_argument('--json')
    ap.add_argument('--roles', help='materials.report.json of the port: decal / glass regions are blended over what is '
                    'behind them, so they are reported but not judged')
    a = ap.parse_args(argv)
    blend = set()
    if a.roles:
        for m in json.load(open(a.roles))['materials']:
            if m.get('role') in ('decal', 'glass') and m.get('iw7'):
                blend.add(m['iw7'])
    os.makedirs(a.out, exist_ok=True)
    report = {'views': []}
    for spec in a.view:
        name, eye, ang, on_p = spec.split(':', 3)[:3] + [spec.split(':', 3)[3]]
        off_p = None
        if '|' in on_p:
            on_p, off_p = on_p.split('|')
        on = np.asarray(Image.open(on_p).convert('RGB'))
        off = np.asarray(Image.open(off_p).convert('RGB')) if off_p else None
        a.size = (on.shape[1], on.shape[0])
        mm = model_mask(on, off)
        hfov = a.hfov
        if a.fit_fov and mm is not None:
            best = None
            for f in (70.0, 74.0, 78.0, 80.7, 84.0, 88.0):
                ids, _, _ = render(a, name, eye, ang, f, a.out)
                sil = ids[..., 3] > 0
                iou = (sil & mm).sum() / max((sil | mm).sum(), 1)
                if best is None or iou > best[0]:
                    best = (iou, f)
            hfov = best[1]
        ids, ref, legend = render(a, name, eye, ang, hfov, a.out)
        el, rl = lin(on), lin(ref)
        eluma, rluma = el @ LUMA, rl @ LUMA
        elap, rlap = lap(eluma), lap(rluma)
        rows = []
        for mat, col in legend.items():
            sel = (np.abs(ids[..., :3].astype(int) - np.array(col)).sum(2) < 12) & (ids[..., 3] > 0)
            if mm is not None:
                sel &= mm
            n = int(sel.sum())
            if n < a.min_px:
                continue
            ec, rc = el[sel].mean(0), rl[sel].mean(0)
            r = {'material': mat, 'pixels': n,
                 'engine_chroma': (ec / max(ec.sum(), 1e-6)).round(3).tolist(), 'ref_chroma': (rc / max(rc.sum(), 1e-6)).round(3).tolist(),
                 'engine_luma': round(float(eluma[sel].mean()), 4), 'ref_luma': round(float(rluma[sel].mean()), 4),
                 'engine_hf': round(float(elap[sel].mean() / max(eluma[sel].mean(), 1e-4)), 3),
                 'ref_hf': round(float(rlap[sel].mean() / max(rluma[sel].mean(), 1e-4)), 3),
                 'black': round(float((eluma[sel] < (12 / 255.0) ** 2.2).mean()), 3)}
            r['_e'], r['_r'] = ec.tolist(), rc.tolist()
            rows.append(r)
        # light: the station's light colour and level differ from the unlit reference. Divide them out with the median
        # engine/reference ratio over the opaque regions (white balance + exposure), then judge each region.
        opaque = [r for r in rows if r['material'] not in blend]
        eps = 0.02
        if opaque:
            # light colour from the regions that are grey in the reference (a strongly coloured paint covering most of
            # the view would otherwise pull the white balance toward its own hue); all opaque regions when none is grey
            grey = [r for r in opaque if max(r['_r']) / max(sum(r['_r']), 1e-6) - min(r['_r']) / max(sum(r['_r']), 1e-6) < 0.05]
            tint = np.median([np.array(r['_e']) / np.maximum(np.array(r['_r']), 1e-4) for r in (grey or opaque)], axis=0)
            gain = float(np.median([(r['engine_luma'] + eps) / (r['ref_luma'] + eps) for r in opaque]))
        else:
            tint, gain = np.ones(3), 1.0
        for r in rows:
            ec = np.array(r['_e']) / np.maximum(tint, 1e-4)
            rc = np.array(r['_r'])
            r['engine_chroma_wb'] = (ec / max(ec.sum(), 1e-6)).round(3).tolist()
            r['chroma_dist'] = round(float(np.abs(np.array(r['engine_chroma_wb']) - np.array(r['ref_chroma'])).sum() / 2), 3)
            r['rel_luma'] = round(((r['engine_luma'] + eps) / (r['ref_luma'] + eps)) / max(gain, 1e-6), 2)
            r['hf_ratio'] = round(r['engine_hf'] / max(r['ref_hf'], 0.25), 2)     # flat paints: engine shading alone gives ~0.3
            del r['_e'], r['_r']
            if r['material'] in blend:
                r['verdict'] = 'n/a (blended over the scene)'
                continue
            fails = []
            # very dark references (navy paint, rubber): reflections of the scene lift and desaturate them in any
            # renderer, so their hue is judged more loosely
            tol = a.chroma + 0.08 * (1.0 - min(1.0, r['ref_luma'] / 0.03))
            r['chroma_tol'] = round(tol, 3)
            if r['chroma_dist'] > tol:
                fails.append('colour')
            if not 0.45 <= r['rel_luma'] <= 2.2:
                fails.append('luma')
            if r['hf_ratio'] > a.hf:
                fails.append('noise')
            if r['black'] > 0.35:
                fails.append('black')
            r['verdict'] = 'FAIL ' + ','.join(fails) if fails else 'PASS'
        rows.sort(key=lambda r: -r['pixels'])
        report['views'].append({'view': name, 'hfov': hfov, 'regions': rows})
        print('== %s (hfov %.1f)' % (name, hfov))
        for r in rows:
            print('  %-50s px %7d chroma %.3f rel_luma %5.2f hf %5.2f/%5.2f black %.2f %s' % (
                r['material'][-50:], r['pixels'], r['chroma_dist'], r['rel_luma'], r['engine_hf'], r['ref_hf'], r['black'], r['verdict']))
    if a.json:
        json.dump(report, open(a.json, 'w'), indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main())

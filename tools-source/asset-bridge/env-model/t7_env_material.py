"""Bake Black Ops III environment materials (GrayWolf *.materials.json) into IW7 model materials.

BO3 environment materials layer tiling "micro" maps (albedo, gloss, normal, specular) with their own UV
scales, blend them through reveal masks and tint them; IW7 model materials read one packed colour map
(packed_cs), one packed normal/gloss/occlusion map (packed_nog) and, for alpha, packed_a. This bakes one
UV period [0, 1)^2 of the BO3 composite (every BO3 scale is an integer, so the composite repeats with the
model UVs and the IW7 sampler's wrap reproduces it) and writes stock-format images through texconv:

  role     BO3 techset / alpha                           IW7 template (techsets shared at runtime)
  opaque   lit*, micro_tile*, backlit                    mo/barrier_handrail          mo_l_sm_replace_i0c0s0o0n0p0
  cutout   alpha test on a non-decal techset with holes  mopw/metal_painted_wall_decal_sheet_01 (atest, packed_a)
  decal    lit_decal*, cutout decals                     mopw/dirt_stain_leaking_01   (ndw blend, packed_a)
  glass    glass, transparent, alpha blend               mo/light_interior_ceiling_spotlight_01_glass (blend)
  emissive any material with an emissive map            mo/signage_exit_sign_emergency_on (+ _e image)
  skip     decal_normal (normal-only decals), decal_reveal (moss/overgrowth) unless --keep

Packing (pack_cs, octahedral normal, gloss) is t7_material_pack's, the stock IW7 shader layout. Per-material
overrides (reveal threshold, tint, role, size) come from an optional JSON manifest.

  python t7_env_material.py <materials.json> [...] --templates <techsets_cp_zmb dump> --texconv <exe>
         --out <dump root> [--prefix mo/] [--size 1024] [--manifest overrides.json] [--keep moss]
Writes <out>/materials/<prefix><name>.json, <out>/images/*.dds, <out>/techsets/{state,constantbuffer}/...
copies of the template's per-material state files (kit_import needs them), and prints a JSON report.
"""
import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 't7-weapons'))
from t7_material_pack import pack_cs, octahedral_ga  # noqa: E402

TEMPLATES = {
    'opaque': 'mo/barrier_handrail',
    'cutout': 'mopw/metal_painted_wall_decal_sheet_01',
    'decal': 'mopw/dirt_stain_leaking_01',
    'glass': 'mo/light_interior_ceiling_spotlight_01_glass',
    'emissive': 'mo/signage_exit_sign_emergency_on',
}
SEM_COLOR, SEM_CS, SEM_NOG, SEM_A = 2, 14, 15, 16


def classify(mat, keep=()):
    tech = (mat.get('techset') or '').lower()
    alpha = (mat.get('alpha') or 'opaque').lower()
    name = mat['name'].lower()
    if any(k in name for k in keep):
        pass
    elif 'decal_reveal' in tech:
        return 'skip'
    elif 'decal_normal' in tech:
        return 'skip'
    if mat.get('emissive'):
        return 'emissive'
    if 'glass' in tech or 'transparent' in tech or alpha == 'blend':
        return 'glass'
    if 'decal' in tech:
        return 'decal'
    if alpha == 'cutout':
        return 'cutout?'
    return 'opaque'


class Bake:
    def __init__(self, base, size):
        self.base = base
        self.size = size
        self.cache = {}

    def path(self, binding):
        if not binding:
            return None
        p = binding['path'] if isinstance(binding, dict) else binding
        full = os.path.normpath(os.path.join(self.base, p))
        return full if os.path.exists(full) else None

    def load(self, binding):
        p = self.path(binding)
        if p is None:
            return None
        if p not in self.cache:
            self.cache[p] = np.asarray(Image.open(p).convert('RGBA')).astype(np.float32) / 255.0
        return self.cache[p]

    def tile(self, binding, scale=(1.0, 1.0)):
        """The image repeated scale times over one baked UV period (size x size), RGBA 0..1."""
        img = self.load(binding)
        if img is None:
            return None
        s = self.size
        su, sv = max(1e-3, float(scale[0])), max(1e-3, float(scale[1]))
        tw, th = max(1, int(round(s / su))), max(1, int(round(s / sv)))
        key = (id(img), tw, th)
        if key not in self.cache:
            im = Image.fromarray(np.clip(img * 255 + 0.5, 0, 255).astype(np.uint8), 'RGBA')
            self.cache[key] = np.asarray(im.resize((tw, th), Image.Resampling.LANCZOS)).astype(np.float32) / 255.0
        t = self.cache[key]
        ry, rx = -(-s // th), -(-s // tw)
        return np.tile(t, (ry, rx, 1))[:s, :s]

    def channel(self, binding, scale=(1.0, 1.0), default=1.0):
        t = self.tile(binding, scale)
        if t is None:
            return np.full((self.size, self.size), default, np.float32)
        ch = {'r': 0, 'g': 1, 'b': 2, 'a': 3}[(binding.get('channel') or 'r')] if isinstance(binding, dict) else 0
        c = t[..., ch]
        return 1.0 - c if isinstance(binding, dict) and binding.get('invert') else c


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / max(e1 - e0, 1e-6), 0, 1)
    return t * t * (3 - 2 * t)


def unit_normal(rgba):
    x = rgba[..., 0] * 2 - 1
    y = rgba[..., 1] * 2 - 1
    z = np.sqrt(np.clip(1 - x * x - y * y, 0, 1))
    return np.stack([x, y, z], -1)


def composite(mat, bk, over):
    """Linear albedo (s,s,3), alpha (s,s), gloss 0..1 (s,s), normal (s,s,3), occlusion (s,s), specular sRGB or None."""
    s = bk.size
    tint = np.array(over.get('tint') or ((mat.get('color_tint') or {}).get('color') or [1, 1, 1])[:3], np.float32)
    has_tint = bool(over.get('tint') or (mat.get('color_tint') or {}).get('color'))
    alb = bk.tile(mat.get('albedo'))
    if alb is None:
        alb = np.ones((s, s, 4), np.float32)
    lin = alb[..., :3] ** 2.2
    if has_tint:
        # BO3 tinted "micro" materials: a grey colour map is detail around the tint (normalised to its mean)
        sat = float(np.mean(alb[..., :3].max(-1) - alb[..., :3].min(-1)))
        if sat < 0.06:
            lin = lin / max(float(lin.mean()), 1e-3)
        lin = np.clip(lin * tint[None, None, :], 0, 1)
    alpha = alb[..., 3].copy()
    gloss = bk.channel(mat.get('roughness'), default=0.5) if mat.get('roughness') else np.full((s, s), 0.5, np.float32)
    nrm = bk.tile(mat.get('normal'))
    n = unit_normal(nrm) if nrm is not None else np.dstack([np.zeros((s, s)), np.zeros((s, s)), np.ones((s, s))])
    occ = bk.channel(mat.get('occlusion'), default=1.0) if mat.get('occlusion') else np.ones((s, s), np.float32)
    spec = bk.tile(mat.get('specular'))
    spec = spec[..., :3] if spec is not None else None
    for k, layer in enumerate(mat.get('layers') or []):
        sc = layer.get('uv_scale') or [1, 1]
        la = bk.tile(layer.get('albedo'), sc)
        if la is None:
            continue
        lt = np.array((layer.get('tint') or [1, 1, 1])[:3], np.float32)
        l_lin = np.clip(la[..., :3] ** 2.2 * lt, 0, 1)
        l_gloss = bk.channel(layer.get('roughness'), sc, 0.5) if layer.get('roughness') else gloss
        ln = bk.tile(layer.get('normal'), sc)
        l_n = unit_normal(ln) if ln is not None else n
        if layer.get('mask'):
            m = bk.channel(layer['mask'], layer['mask'].get('uv_scale') or [1, 1], 0.0)
            th = float(over.get('reveal', 0.72))
            w = smoothstep(th - 0.08, th + 0.08, m)[..., None]
        else:
            w = np.ones((s, s, 1), np.float32)
        lin = lin * (1 - w) + l_lin * w
        gloss = gloss * (1 - w[..., 0]) + l_gloss * w[..., 0]
        n = n * (1 - w) + l_n * w
        if spec is not None and k > 0:
            spec = spec * (1 - w) + 0.22 * w            # revealed layers (rust, grime) are dielectric
    n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-6)
    if 'albedo_gain' in over:
        lin = np.clip(lin * float(over['albedo_gain']), 0, 1)
    return lin, alpha, gloss, n, occ, spec


def texconv(exe, png, out_dir, fmt):
    subprocess.run([exe, '-nologo', '-y', '-m', '0', '-f', fmt, '-o', out_dir, png], check=True,
                   stdout=subprocess.DEVNULL)


NAME_MAX = 40


def short_name(name):
    """Material / image stems stay short: names longer than NAME_MAX keep their head plus a stable hash (suspected
    cause of the BO3 car not drawing in run a1: its image names reached 78 characters, the drawn zod car's 63)."""
    if len(name) <= NAME_MAX:
        return name
    import hashlib
    return name[:NAME_MAX - 9] + '_' + hashlib.sha1(name.encode()).hexdigest()[:8]


def safe(name):
    return re.sub(r'[^A-Za-z0-9_]', '_', name)


def copy_state(templates_root, tmpl, techset, new_name, out):
    """Per-material state/constant files of the template, renamed for the new material."""
    copied = []
    for sub in ('state', 'constantbuffer'):
        src_dir = os.path.join(templates_root, 'techsets', sub, techset, os.path.dirname(tmpl))
        if not os.path.isdir(src_dir):
            continue
        stem = os.path.basename(tmpl)
        for f in os.listdir(src_dir):
            if f.startswith(stem + '.'):
                dst = os.path.join(out, 'techsets', sub, techset, os.path.dirname(new_name),
                                   os.path.basename(new_name) + f[len(stem):])
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(os.path.join(src_dir, f), dst)
                copied.append(os.path.relpath(dst, out).replace(os.sep, '/'))
    return copied


def passthrough_iw7(mat, base, templates_root, out, prefix, role, over, texconv_exe, tmp):
    """An IW7 source material (GrayWolf "iw" export): its images already are the stock packed layout
    (packed_cs, packed_ng/nog, packed_a); re-encode them in the stock formats under the new name."""
    def img(binding):
        p = os.path.normpath(os.path.join(base, binding['path'])) if binding else None
        return np.asarray(Image.open(p).convert('RGBA')).astype(np.float32) if p and os.path.exists(p) else None
    cs = img(mat.get('albedo'))
    nog = img(mat.get('normal'))
    if nog is None:
        nog = np.full(cs.shape, 127.5, np.float32)
    if '_packed_ng' in (mat.get('normal') or {}).get('path', ''):
        nog[..., 2] = 255.0                                  # packed_ng has no occlusion: full
    role = role if role not in ('cutout?',) else 'opaque'
    tmpl = TEMPLATES['opaque' if role in ('skip',) else role]
    template = json.load(open(os.path.join(templates_root, 'materials', tmpl + '.json')))
    techset = template['techniqueSet->name']
    new_name = prefix + short_name(mat['name'])
    stem = safe(new_name)
    images = {'cs': stem + '_packed_cs', 'nog': stem + '_packed_nog'}
    jobs = [('cs', cs, 'BC7_UNORM'), ('nog', nog, 'BC7_UNORM')]
    a = None
    for s_ in mat.get('sources', []):
        if '_packed_a' in s_.get('path', ''):
            a = img(s_)
    if role in ('cutout', 'decal', 'glass'):
        if a is None:
            a = np.full(cs.shape, 255.0, np.float32)
        images['a'] = stem + '_packed_a'
        jobs.append(('a', a, 'BC4_UNORM'))
    img_dir = os.path.join(out, 'images')
    os.makedirs(img_dir, exist_ok=True)
    for key, data, fmt in jobs:
        png = os.path.join(tmp, images[key] + '.png')
        Image.fromarray(np.clip(data + 0.5, 0, 255).astype(np.uint8), 'RGBA').save(png)
        texconv(texconv_exe, png, img_dir, fmt)
    m = copy.deepcopy(template)
    for t in m['textureTable']:
        if t['semantic'] == SEM_CS:
            t['image'] = images['cs']
        elif t['semantic'] == SEM_NOG:
            t['image'] = images['nog']
        elif t['semantic'] == SEM_A and 'a' in images:
            t['image'] = images['a']
    mat_path = os.path.join(out, 'materials', new_name + '.json')
    os.makedirs(os.path.dirname(mat_path), exist_ok=True)
    json.dump(m, open(mat_path, 'w'), indent=4)
    state = copy_state(templates_root, tmpl, techset, new_name, out)
    return {'material': mat['name'], 'iw7': new_name, 'role': role, 'template': tmpl, 'techset': techset,
            'size': int(cs.shape[0]), 'images': images, 'state_files': len(state), 'source': 'iw7 packed passthrough'}


def bake_material(mat, base, templates_root, out, prefix, size, over, texconv_exe, keep, tmp):
    role = over.get('role') or classify(mat, keep)
    if role == 'skip':
        return {'material': mat['name'], 'role': 'skip'}
    if not mat.get('layers'):
        # single-scale material: bake at the largest map it binds (64 .. --size)
        dims = [64]
        for key in ('albedo', 'normal', 'roughness', 'specular', 'occlusion', 'emissive'):
            b = mat.get(key)
            p = os.path.normpath(os.path.join(base, b['path'])) if isinstance(b, dict) and b.get('path') else None
            if p and os.path.exists(p) and not os.path.basename(p).startswith('$'):
                dims.append(max(Image.open(p).size))
        size = min(size, max(dims))
    size = int(over.get('size', size))
    bk = Bake(base, size)
    iw_cs = (mat.get('albedo') or {}).get('path', '')
    if '_packed_cs' in iw_cs:
        return passthrough_iw7(mat, base, templates_root, out, prefix, role, over, texconv_exe, tmp)
    lin, alpha, gloss, n, occ, spec = composite(mat, bk, over)
    if role == 'cutout?':
        role = 'cutout' if float(np.mean(alpha < 0.5)) > 0.01 else 'opaque'
    if role == 'glass' and 'alpha' in over:
        alpha = alpha * float(over['alpha'])
    tmpl = TEMPLATES[role]
    tech_json = os.path.join(templates_root, 'materials', tmpl + '.json')
    template = json.load(open(tech_json))
    techset = template['techniqueSet->name']
    new_name = prefix + short_name(mat['name'])
    stem = safe(new_name)
    srgb = np.clip(lin, 0, 1) ** (1 / 2.2)
    albedo255 = np.dstack([srgb * 255.0, np.full(srgb.shape[:2], 255.0)])
    spec255 = spec * 255.0 if spec is not None else None
    cs = pack_cs(albedo255, spec255, mat.get('metalness_value'))
    if spec255 is None:
        # t7_material_pack.pack_cs leaves the colour in 0..1 when a material has no specular map (weapon materials
        # always have one); the stock layout is 0..255 like the alpha it scales
        cs[..., :3] *= 255.0
    nog = np.empty(cs.shape, np.float32)
    nog[..., 0] = np.clip(gloss, 0, 1) * 255.0
    g, a = octahedral_ga(np.dstack([(n[..., 0] + 1) / 2 * 255.0, (n[..., 1] + 1) / 2 * 255.0]))
    nog[..., 1], nog[..., 3] = g, a
    nog[..., 2] = np.clip(occ, 0, 1) * 255.0
    images = {'cs': stem + '_packed_cs', 'nog': stem + '_packed_nog'}
    jobs = [('cs', cs, 'BC7_UNORM'), ('nog', nog, 'BC7_UNORM')]
    if role in ('cutout', 'decal', 'glass'):
        am = np.zeros(cs.shape, np.float32)
        am[..., 0] = np.clip(alpha, 0, 1) * 255.0
        am[..., 3] = 255.0
        images['a'] = stem + '_packed_a'
        jobs.append(('a', am, 'BC4_UNORM'))
    if role == 'emissive':
        e = bk.tile(mat.get('emissive'))
        em = np.zeros(cs.shape, np.float32)
        em[..., :3] = np.sqrt(np.clip(e[..., :3] ** 2.2, 0, 1)) * 255.0
        em[..., 3] = 255.0
        images['e'] = stem + '_e'
        jobs.append(('e', em, 'BC7_UNORM'))
    img_dir = os.path.join(out, 'images')
    os.makedirs(img_dir, exist_ok=True)
    for key, data, fmt in jobs:
        png = os.path.join(tmp, images[key] + '.png')
        Image.fromarray(np.clip(data + 0.5, 0, 255).astype(np.uint8), 'RGBA').save(png)
        texconv(texconv_exe, png, img_dir, fmt)
    m = copy.deepcopy(template)
    table = []
    for t in m['textureTable']:
        t = dict(t)
        if t['semantic'] == SEM_CS:
            t['image'] = images['cs']
        elif t['semantic'] == SEM_NOG:
            t['image'] = images['nog']
        elif t['semantic'] == SEM_A and 'a' in images:
            t['image'] = images['a']
        elif t['semantic'] == SEM_COLOR and 'e' in images:
            t['image'] = images['e']
        table.append(t)
    m['textureTable'] = table
    for c in m.get('constantTable', []):
        if c.get('name') == 'emissivePara' and 'emissive' in over:
            c['literal'][0] = float(over['emissive'])
    mat_path = os.path.join(out, 'materials', new_name + '.json')
    os.makedirs(os.path.dirname(mat_path), exist_ok=True)
    json.dump(m, open(mat_path, 'w'), indent=4)
    state = copy_state(templates_root, tmpl, techset, new_name, out)
    return {'material': mat['name'], 'iw7': new_name, 'role': role, 'template': tmpl, 'techset': techset,
            'size': size, 'images': images, 'state_files': len(state),
            'albedo_mean_srgb': [round(float(x), 3) for x in srgb.reshape(-1, 3).mean(0)],
            'alpha_mean': round(float(alpha.mean()), 3)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('materials', nargs='+')
    ap.add_argument('--templates', required=True, help='ZoneTool dump root with materials/ and techsets/ of the templates (techsets_cp_zmb)')
    ap.add_argument('--texconv', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--prefix', default='mo/')
    ap.add_argument('--size', type=int, default=1024)
    ap.add_argument('--manifest', help='JSON {material: {role, tint, reveal, size, alpha, emissive, albedo_gain}}')
    ap.add_argument('--keep', nargs='*', default=[], help='name substrings of materials never skipped')
    ap.add_argument('--only', nargs='*')
    a = ap.parse_args(argv)
    over_all = json.load(open(a.manifest)) if a.manifest else {}
    done, report = set(), []
    with tempfile.TemporaryDirectory() as tmp:
        for mj in a.materials:
            base = os.path.dirname(os.path.abspath(mj))
            for mat in json.load(open(mj))['materials']:
                if mat['name'] in done or (a.only and mat['name'] not in a.only):
                    continue
                done.add(mat['name'])
                over = over_all.get(mat['name'], {})
                report.append(bake_material(mat, base, a.templates, a.out, a.prefix, a.size, over, a.texconv,
                                            a.keep, tmp))
    print(json.dumps({'materials': report}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())

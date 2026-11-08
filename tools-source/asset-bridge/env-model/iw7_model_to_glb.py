"""Write a ZoneTool IW7 model dump (.xmb + .xsb [+ materials/images]) back out as a binary glTF, for inspection.

  python iw7_model_to_glb.py <dump root> <model> <out.glb> [--lod 0] [--texconv <exe>]

Decodes exactly what the engine will read: packed positions, 10:10:10 normals, half UVs and the clockwise IW
triangles (reversed back to glTF's counter-clockwise front). With --texconv each material's packed_cs image
(colour in RGB) becomes the glTF base colour texture, so a Blender render (blender/blender_preview.py) shows
the model as built, not as authored.
"""
import argparse
import json
import os
import struct
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iw7_xmodel_io as io  # noqa: E402


def decode_unit(p):
    return np.stack([((p >> s) & 0x3FF) / 1023.0 * 2 - 1 for s in (0, 10, 20)], 1)


def load(root, name, lod):
    xm = io.parse_xmodel(open(os.path.join(root, 'xmodel', name + '.xmb'), 'rb').read())
    head = xm['head']
    li = io.lod_info(head, lod)
    mats = []
    last = None
    for m in xm['materials']:
        last = m if not isinstance(m, tuple) else last          # OFFSET back-references repeat the material
        mats.append(last)
    xs = io.parse_xsurfs(open(os.path.join(root, 'xsurface', xm['lods'][lod] + '.xsb'), 'rb').read())
    out = []
    for k, s in enumerate(xs['surfs']):
        v = s['verts']
        P = v['xyz'].astype(np.float32) * 0.0254
        N = decode_unit(v['normal']).astype(np.float32)
        UV = np.ascontiguousarray(v['uv']).view(np.float16).reshape(-1, 2).astype(np.float32)
        T = s['tris'][:, [0, 2, 1]].astype(np.uint32)
        out.append((mats[li['surfIndex'] + k], P, N, UV, T))
    return out


def to_gltf_axes(a):
    # game (x, y, z) Z-up -> glTF (x, z, -y) Y-up
    return np.stack([a[:, 0], a[:, 2], -a[:, 1]], 1).astype(np.float32)


def write_glb(path, surfs, textures):
    blob = bytearray()
    views, accs, meshes, mats, imgs, texs = [], [], [], [], [], []
    mat_index = {}

    def add(arr, target=None):
        b = arr.tobytes()
        while len(blob) % 4:
            blob.append(0)
        views.append({'buffer': 0, 'byteOffset': len(blob), 'byteLength': len(b), **({'target': target} if target else {})})
        blob.extend(b)
        return len(views) - 1

    for name, P, N, UV, T in surfs:
        if name not in mat_index:
            m = {'name': name, 'pbrMetallicRoughness': {'metallicFactor': 0.0, 'roughnessFactor': 0.8}}
            png = textures.get(name)
            if png:
                bv = add(np.frombuffer(open(png, 'rb').read(), np.uint8))
                imgs.append({'bufferView': bv, 'mimeType': 'image/png'})
                texs.append({'source': len(imgs) - 1})
                m['pbrMetallicRoughness']['baseColorTexture'] = {'index': len(texs) - 1}
            mats.append(m)
            mat_index[name] = len(mats) - 1
        p, n = to_gltf_axes(P), to_gltf_axes(N)
        prims = {}
        for key, arr, typ in (('POSITION', p, 'VEC3'), ('NORMAL', n, 'VEC3'), ('TEXCOORD_0', UV, 'VEC2')):
            bv = add(np.ascontiguousarray(arr), 34962)
            acc = {'bufferView': bv, 'componentType': 5126, 'count': len(arr), 'type': typ}
            if key == 'POSITION':
                acc['min'] = p.min(0).tolist()
                acc['max'] = p.max(0).tolist()
            accs.append(acc)
            prims[key] = len(accs) - 1
        bv = add(np.ascontiguousarray(T.reshape(-1)), 34963)
        accs.append({'bufferView': bv, 'componentType': 5125, 'count': T.size, 'type': 'SCALAR'})
        meshes.append({'primitives': [{'attributes': prims, 'indices': len(accs) - 1, 'material': mat_index[name]}]})
    gl = {'asset': {'version': '2.0', 'generator': 'iw7_model_to_glb'}, 'buffers': [{'byteLength': len(blob)}],
          'bufferViews': views, 'accessors': accs, 'meshes': meshes, 'materials': mats,
          'nodes': [{'mesh': i} for i in range(len(meshes))], 'scenes': [{'nodes': list(range(len(meshes)))}], 'scene': 0}
    if imgs:
        gl['images'], gl['textures'] = imgs, texs
    j = json.dumps(gl).encode()
    while len(j) % 4:
        j += b' '
    while len(blob) % 4:
        blob.append(0)
    with open(path, 'wb') as f:
        f.write(struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(j) + 8 + len(blob)))
        f.write(struct.pack('<II', len(j), 0x4E4F534A) + j)
        f.write(struct.pack('<II', len(blob), 0x004E4942) + bytes(blob))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('root')
    ap.add_argument('model')
    ap.add_argument('out')
    ap.add_argument('--lod', type=int, default=0)
    ap.add_argument('--texconv')
    a = ap.parse_args(argv)
    surfs = load(a.root, a.model, a.lod)
    textures = {}
    if a.texconv:
        tmp = tempfile.mkdtemp()
        for name in {s[0] for s in surfs}:
            mp = os.path.join(a.root, 'materials', name + '.json')
            if not os.path.exists(mp):
                continue
            for t in json.load(open(mp))['textureTable']:
                if t['semantic'] == 14:
                    dds = os.path.join(a.root, 'images', t['image'] + '.dds')
                    if os.path.exists(dds):
                        subprocess.run([a.texconv, '-nologo', '-y', '-ft', 'png', '-f', 'R8G8B8A8_UNORM', '-m', '1',
                                        '-o', tmp, dds], check=True, stdout=subprocess.DEVNULL)
                        png = os.path.join(tmp, t['image'] + '.png')
                        from PIL import Image
                        Image.open(png).convert('RGB').save(png)        # alpha holds metalness: drop it
                        textures[name] = png
    write_glb(a.out, surfs, textures)
    print(json.dumps({'model': a.model, 'surfaces': len(surfs), 'tris': int(sum(len(s[4]) for s in surfs)),
                      'textured': len(textures)}))


if __name__ == '__main__':
    sys.exit(main())

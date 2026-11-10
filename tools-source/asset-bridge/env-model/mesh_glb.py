"""Read a binary glTF (.glb) into game-space triangle meshes grouped by material (numpy).

Node transforms are applied, then glTF Y-up metres become IW/T7 game space (Z-up, inches):
game = (gx, -gz, gy) / 0.0254. That holds for GrayWolf/Greyhound exports (their root node
"cod_to_gltf" maps game centimetres to glTF metres) and for Blender's glTF exporter (+Y up).
Triangles keep glTF's counter-clockwise front; iw7_model_author reverses them for IW7.
Skins are ignored: environment models are rigid.
"""
import json
import struct

import numpy as np

CTYPE = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NCOMP = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
INCH = 0.0254


def load_glb(path):
    with open(path, 'rb') as f:
        d = f.read()
    if d[:4] != b'glTF':
        raise ValueError('%s is not a binary glTF' % path)
    jl = struct.unpack_from('<I', d, 12)[0]
    j = json.loads(d[20:20 + jl])
    o = 20 + jl
    blob = b''
    if o + 8 <= len(d):
        bl = struct.unpack_from('<I', d, o)[0]
        blob = d[o + 8:o + 8 + bl]
    return j, blob


def accessor(j, blob, index):
    a = j['accessors'][index]
    bv = j['bufferViews'][a['bufferView']]
    n = NCOMP[a['type']]
    dt = np.dtype(CTYPE[a['componentType']])
    off = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    stride = bv.get('byteStride') or dt.itemsize * n
    count = a['count']
    out = np.empty((count, n), dt)
    raw = np.frombuffer(blob, np.uint8)
    for k in range(n):
        idx = off + np.arange(count) * stride + k * dt.itemsize
        out[:, k] = raw[idx[:, None] + np.arange(dt.itemsize)].copy().view(dt).reshape(count)
    if a.get('normalized') and dt.kind in 'iu':
        out = out.astype(np.float32) / np.iinfo(dt).max
    return out


def node_matrix(node):
    if 'matrix' in node:
        return np.array(node['matrix'], np.float64).reshape(4, 4).T
    t = np.array(node.get('translation', [0, 0, 0]), np.float64)
    q = np.array(node.get('rotation', [0, 0, 0, 1]), np.float64)
    s = np.array(node.get('scale', [1, 1, 1]), np.float64)
    x, y, z, w = q
    r = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    m = np.eye(4)
    m[:3, :3] = r * s
    m[:3, 3] = t
    return m


GLTF_TO_GAME = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], np.float64) * (1.0 / INCH)
GLTF_TO_GAME[3, 3] = 1.0


def meshes(path, skip_materials=()):
    """{material name: {'P': (n,3) inches, 'N': (n,3), 'UV': (n,2), 'tris': (m,3)}} in game space."""
    j, blob = load_glb(path)
    out = {}
    world = {}

    def walk(i, parent):
        m = parent @ node_matrix(j['nodes'][i])
        world[i] = m
        for c in j['nodes'][i].get('children', []):
            walk(c, m)

    scene = j.get('scenes', [{'nodes': list(range(len(j['nodes'])))}])[j.get('scene', 0)]
    for root in scene['nodes']:
        walk(root, GLTF_TO_GAME)
    for i in range(len(j['nodes'])):        # joints outside the scene roots
        if i not in world:
            walk(i, GLTF_TO_GAME)
    for i, node in enumerate(j['nodes']):
        if 'mesh' not in node or i not in world:
            continue
        m = world[i]
        if 'skin' in node:
            # skinned mesh: glTF ignores the node transform; rigid models bind every vertex to the
            # first joint (GrayWolf: the model's lod0 bone under cod_to_gltf)
            skin = j['skins'][node['skin']]
            jm = world[skin['joints'][0]]
            ib = np.eye(4)
            if 'inverseBindMatrices' in skin:
                ib = accessor(j, blob, skin['inverseBindMatrices'])[0].astype(np.float64).reshape(4, 4).T
            m = jm @ ib
        nm = np.linalg.inv(m[:3, :3]).T
        for prim in j['meshes'][node['mesh']]['primitives']:
            if prim.get('mode', 4) != 4:
                continue
            mat = j['materials'][prim['material']]['name'] if 'material' in prim else 'default'
            if mat in skip_materials:
                continue
            at = prim['attributes']
            p = accessor(j, blob, at['POSITION']).astype(np.float64)
            p = p @ m[:3, :3].T + m[:3, 3]
            if 'NORMAL' in at:
                n = accessor(j, blob, at['NORMAL']).astype(np.float64) @ nm.T
                n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
            else:
                n = None
            uv = accessor(j, blob, at['TEXCOORD_0']).astype(np.float64) if 'TEXCOORD_0' in at else np.zeros((len(p), 2))
            if 'indices' in prim:
                t = accessor(j, blob, prim['indices']).reshape(-1, 3).astype(np.int64)
            else:
                t = np.arange(len(p)).reshape(-1, 3)
            if np.linalg.det(m[:3, :3]) < 0:
                t = t[:, ::-1]
            g = out.setdefault(mat, {'P': [], 'N': [], 'UV': [], 'tris': [], 'base': 0})
            t = t + g['base']
            g['base'] += len(p)
            g['P'].append(p)
            g['N'].append(n if n is not None else np.zeros_like(p))
            g['UV'].append(uv)
            g['tris'].append(t)
    for mat, g in out.items():
        out[mat] = {'P': np.concatenate(g['P']), 'N': np.concatenate(g['N']), 'UV': np.concatenate(g['UV']),
                    'tris': np.concatenate(g['tris'])}
    return out


def material_images(path):
    """{material: {'baseColor': uri/name, 'normal': ...}} from the glTF material table (informational)."""
    j, _ = load_glb(path)
    imgs = j.get('images', [])
    tex = j.get('textures', [])

    def name(ti):
        if ti is None:
            return None
        src = tex[ti['index']].get('source')
        im = imgs[src] if src is not None else {}
        return im.get('uri') or im.get('name')
    out = {}
    for m in j.get('materials', []):
        pbr = m.get('pbrMetallicRoughness', {})
        out[m['name']] = {'baseColor': name(pbr.get('baseColorTexture')), 'normal': name(m.get('normalTexture')),
                          'alphaMode': m.get('alphaMode', 'OPAQUE')}
    return out

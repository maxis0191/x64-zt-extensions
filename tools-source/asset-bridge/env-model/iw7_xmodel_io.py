"""IW7 XModel (.xmb) and XModelSurfs (.xsb) ZoneTool dumps: parse, edit and write (numpy).

Schemas follow the x64-zt IW7 dumper (assets/xmodel.cpp, assets/xsurface.cpp) and structs.hpp
(XModel 0x2E0, XModelSurfs 0x38, XSurface 0x100, XRigidVertList 16, XSurfaceCollisionTree 56,
GfxPackedVertex 32). Subdivision surfaces are refused; everything else round-trips byte for byte
(test_iw7_xmodel_io.py).
"""
import struct

import numpy as np

from iw7_zt_stream import Reader, Writer, StreamError

XMODEL_SIZE = 0x2E0
XMODELSURFS_SIZE = 0x38
XSURFACE_SIZE = 0x100
RIGID_SIZE = 16
TREE_SIZE = 56
NODE_SIZE = 16
LEAF_SIZE = 2
VERT_SIZE = 32
LOD_SIZE = 0x40

VERT_DTYPE = np.dtype([('xyz', '<f4', 3), ('selfvis', '<u4'), ('color', '<u4'), ('uv', '<u4'),
                       ('normal', '<u4'), ('tangent', '<u4')])
NODE_DTYPE = np.dtype([('mins', '<u2', 3), ('maxs', '<u2', 3), ('child', '<u2'), ('count', '<u2')])

# XModel field offsets (structs.hpp, x64)
XM = {
    'hasLods': 9, 'maxLoadedLod': 10, 'numLods': 11, 'collLod': 12, 'shadowCutoffLod': 13,
    'flags': 16, 'numBones': 20, 'numRootBones': 21, 'numReactiveMotionParts': 22,
    'numClientBones': 24, 'numsurfs': 26, 'scale': 28, 'numCollSurfs': 32, 'contents': 36,
    'radius': 40, 'bounds': 44, 'memUsage': 68, 'physicsLODDataSize': 72, 'numAimAssistBones': 112,
    'edgeLength': 116, 'lodInfo': 224, 'physicsLODDataNameCount': 656, 'impactType': 672,
    'unknown03Count': 688, 'unknownVec3Count': 705, 'unknown04Count': 721,
}
# XSurface field offsets
XS = {'flags': 0, 'vertCount': 2, 'triCount': 4, 'rigidVertListCount': 6, 'subdivLevelCount': 7,
      'blendVertCounts': 8, 'blendVertSize': 24, 'subdiv': 128, 'vertexLightingIndex': 192, 'partBits': 224}


# ------------------------------------------------------------------ XModelSurfs
def parse_xsurfs(data):
    r = Reader(data)
    head = r.array(XMODELSURFS_SIZE)
    name = r.string()
    numsurfs = struct.unpack_from('<H', head, 16)[0]
    sb = r.array(XSURFACE_SIZE)
    surfs = []
    for i in range(numsurfs):
        h = sb[i * XSURFACE_SIZE:(i + 1) * XSURFACE_SIZE]
        flags, vc, tc, rc, sc = struct.unpack_from('<3H2B', h, 0)
        s = {'head': bytearray(h), 'flags': flags}
        vb = r.array(VERT_SIZE)
        if flags & 8:
            s['motion_verts'] = vb
            s['verts'] = None
        else:
            s['verts'] = np.frombuffer(vb, VERT_DTYPE).copy() if vb else None
        tb = r.array(6)
        s['tris'] = np.frombuffer(tb, '<u2').reshape(-1, 3).copy() if tb else None
        rb = r.array(RIGID_SIZE)
        s['rigid'] = []
        for k in range(rc):
            bone, rvc, toff, rtc, tree_ptr = struct.unpack_from('<4HQ', rb, k * RIGID_SIZE)
            ent = {'bone': bone, 'verts': rvc, 'tri_offset': toff, 'tris': rtc, 'tree': None, 'ptr': tree_ptr}
            if tree_ptr:
                th = r.array(TREE_SIZE)
                trans = struct.unpack_from('<3f', th, 0)
                scale = struct.unpack_from('<3f', th, 12)
                ncount, nptr, lcount, lptr = struct.unpack_from('<I4xQI4xQ', th, 24)
                leafs = nodes = None
                if lptr:
                    leafs = np.frombuffer(r.array(LEAF_SIZE), '<u2').copy()
                if nptr:
                    nodes = np.frombuffer(r.array(NODE_SIZE), NODE_DTYPE).copy()
                ent['tree'] = {'trans': trans, 'scale': scale, 'nodes': nodes, 'leafs': leafs, 'ptrs': (nptr, lptr)}
            s['rigid'].append(ent)
        s['blend'] = r.raw()
        s['lmap'] = r.raw()
        s['tension'] = r.raw()
        s['tension_accum'] = r.raw()
        if struct.unpack_from('<Q', h, XS['subdiv'])[0]:
            raise StreamError('subdiv surfaces are not supported')
        if (flags & 0x500) == 0x500:
            s['shprobe'] = (0x500, r.array(32))
        elif flags & 0x100:
            s['shprobe'] = (0x100, r.array(8))
        elif flags & 0x400:
            s['shprobe'] = (0x400, r.array(24))
        else:
            s['shprobe'] = None
        surfs.append(s)
    if not r.at_end():
        raise StreamError('trailing bytes in xsb at %d' % r.p)
    return {'head': bytearray(head), 'name': name, 'surfs': surfs}


def write_xsurfs(m):
    w = Writer()
    head = bytearray(m['head'])
    struct.pack_into('<H', head, 16, len(m['surfs']))
    w.array(head, XMODELSURFS_SIZE)
    w.string(m['name'])
    heads = b''.join(bytes(s['head']) for s in m['surfs'])
    w.array(heads, XSURFACE_SIZE)
    for s in m['surfs']:
        if s.get('motion_verts') is not None:
            w.array(s['motion_verts'], VERT_SIZE)
        else:
            w.array(s['verts'].tobytes() if s['verts'] is not None else None, VERT_SIZE)
        w.array(s['tris'].astype('<u2').tobytes() if s['tris'] is not None else None, 6)
        rb = b''.join(struct.pack('<4HQ', e['bone'], e['verts'], e['tri_offset'], e['tris'], (e.get('ptr') or 1) if e['tree'] else 0)
                      for e in s['rigid'])
        w.array(rb if s['rigid'] else None, RIGID_SIZE)
        for e in s['rigid']:
            t = e['tree']
            if not t:
                continue
            nodes, leafs = t['nodes'], t['leafs']
            nptr, lptr = t.get('ptrs') or (1, 1)
            th = struct.pack('<3f3fI4xQI4xQ', *t['trans'], *t['scale'],
                             len(nodes) if nodes is not None else 0, (nptr or 1) if nodes is not None else 0,
                             len(leafs) if leafs is not None else 0, (lptr or 1) if leafs is not None else 0)
            w.array(th, TREE_SIZE)
            if leafs is not None:
                w.array(leafs.astype('<u2').tobytes(), LEAF_SIZE)
            if nodes is not None:
                w.array(nodes.tobytes(), NODE_SIZE)
        w.raw(s.get('blend'))
        w.raw(s.get('lmap'))
        w.raw(s.get('tension'))
        w.raw(s.get('tension_accum'))
        if s.get('shprobe'):
            kind, b = s['shprobe']
            w.array(b, {0x500: 32, 0x100: 8, 0x400: 24}[kind])
    return w.bytes()


# ------------------------------------------------------------------ XModel
def parse_xmodel(data):
    """XModel dump -> dict with the raw head (0x2E0) and every record, in dump order."""
    r = Reader(data)
    head = bytearray(r.array(XMODEL_SIZE))
    name = r.string()
    nb = head[XM['numBones']] + struct.unpack_from('<H', head, XM['numClientBones'])[0]
    numsurfs = struct.unpack_from('<H', head, XM['numsurfs'])[0]
    m = {'head': head, 'name': name}
    m['bones'] = [r.string() for _ in range(nb)]
    m['parentList'] = r.array(1)
    m['tagAngles'] = r.array(8)
    m['tagPositions'] = r.array(12)
    m['partClassification'] = r.array(1)
    m['baseMat'] = r.array(32)
    m['reactiveMotionParts'] = r.array(16)
    m['reactiveMotionTweaks'] = r.array(16)
    m['collSurfs'] = r.array(36)
    m['boneInfo'] = r.array(28)
    m['invHighMipRadius'] = r.array(2)
    m['materialHandles'] = r.array(8)
    m['materials'] = [r.asset() for _ in range(numsurfs)]
    m['lods'] = [r.asset() for _ in range(6)]
    m['physicsAsset'] = r.asset()
    m['physicsFXShape'] = r.asset()
    pcount = struct.unpack_from('<I', head, XM['physicsLODDataNameCount'])[0]
    m['physicsLODDataNames'] = [r.string() for _ in range(pcount)]
    m['scriptableMoverDef'] = r.asset()
    m['proceduralBones'] = r.asset()
    m['aimAssistBones'] = [r.string() for _ in range(head[XM['numAimAssistBones']])]
    m['unknown03'] = r.array(1)
    m['unknownVec3'] = r.array(12)
    m['unknown04'] = r.array(24)
    if not r.at_end():
        raise StreamError('trailing bytes in xmb at %d' % r.p)
    return m


def write_xmodel(m):
    w = Writer()
    w.array(m['head'], XMODEL_SIZE)
    w.string(m['name'])
    for b in m['bones']:
        w.string(b)
    for key, size in (('parentList', 1), ('tagAngles', 8), ('tagPositions', 12), ('partClassification', 1),
                      ('baseMat', 32), ('reactiveMotionParts', 16), ('reactiveMotionTweaks', 16),
                      ('collSurfs', 36), ('boneInfo', 28), ('invHighMipRadius', 2), ('materialHandles', 8)):
        w.array(m[key], size)
    for a in m['materials']:
        w.asset(a)
    for a in m['lods']:
        w.asset(a)
    w.asset(m['physicsAsset'])
    w.asset(m['physicsFXShape'])
    for s in m['physicsLODDataNames']:
        w.string(s)
    w.asset(m['scriptableMoverDef'])
    w.asset(m['proceduralBones'])
    for s in m['aimAssistBones']:
        w.string(s)
    w.array(m['unknown03'], 1)
    w.array(m['unknownVec3'], 12)
    w.array(m['unknown04'], 24)
    return w.bytes()


def lod_info(head, i):
    o = XM['lodInfo'] + i * LOD_SIZE
    dist, ns, si = struct.unpack_from('<f2H', head, o)
    return {'dist': dist, 'numsurfs': ns, 'surfIndex': si, 'flags': head[o + 60]}


def set_lod_info(head, i, dist, numsurfs, surf_index):
    o = XM['lodInfo'] + i * LOD_SIZE
    struct.pack_into('<f2H', head, o, dist, numsurfs, surf_index)

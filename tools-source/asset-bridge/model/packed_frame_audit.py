"""Read-only, bounded frame audit for the original rigid cube XSB prefix.

This checks geometry/source conventions. It does not establish the IW7 shader
decoder or the meaning of the top two packed bits, and never rewrites an asset.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct

MAX_BYTES = 2 * 1024 * 1024

def require(value, message):
    if not value:
        raise ValueError(message)

def sha(data): return hashlib.sha256(data).hexdigest()
def sub(a, b): return tuple(x-y for x, y in zip(a, b))
def dot(a, b): return sum(x*y for x, y in zip(a, b))
def cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def unit(v):
    require(all(math.isfinite(x) for x in v), 'Nonfinite vector')
    length = math.sqrt(dot(v, v))
    require(length > 1e-12, 'Degenerate vector')
    return tuple(x/length for x in v)

def decode(word, codec='h1_unorm10'):
    require(type(word) is int and 0 <= word <= 0xffffffff, 'uint32 word required')
    fields = tuple((word >> shift) & 1023 for shift in (0, 10, 20))
    if codec == 'h1_unorm10': return tuple(2*x/1023-1 for x in fields)
    if codec == 'midpoint10': return tuple((x+0.5)/512-1 for x in fields)
    if codec == 'signed10': return tuple(max(-1., (x if x < 512 else x-1024)/511) for x in fields)
    raise ValueError('Unknown codec hypothesis')

class PrefixReader:
    def __init__(self, data):
        require(isinstance(data, bytes) and 0 < len(data) <= MAX_BYTES, 'Bounded byte payload required')
        self.data, self.offset = data, 0
    def take(self, n):
        require(0 <= n <= MAX_BYTES and self.offset+n <= len(self.data), 'Truncated prefix')
        value = self.data[self.offset:self.offset+n]
        self.offset += n
        return value
    def array(self, width, count):
        require(self.take(2) == b'\x08\x01', 'Independent present array required; aliases unsupported in this profile')
        require(struct.unpack('<I', self.take(4))[0] == count, 'Array count differs from bounded profile')
        return self.take(width*count)
    def name(self):
        require(self.take(2) == b'\x06\x01', 'Present name required')
        end = self.data.find(b'\0', self.offset, self.offset+129)
        require(end >= self.offset, 'Bounded ASCII name required')
        return self.take(end-self.offset+1)[:-1].decode('ascii')

def read_prefix(data):
    reader = PrefixReader(data)
    outer = reader.array(56, 1)
    require(struct.unpack_from('<H', outer, 16)[0] == 1, 'Only one surface is supported')
    name = reader.name()
    surface = reader.array(256, 1)
    flags, nv, nt, rigid, subdiv = struct.unpack_from('<HHHBB', surface)
    require(not flags & 8 and subdiv == 0 and rigid == 1, 'Only ordinary rigid, non-subdivision vertices are supported')
    require(3 <= nv <= 256 and 1 <= nt <= 512, 'Small original probe profile required')
    vertices = reader.array(32, nv)
    triangles = reader.array(6, nt)
    rows = []
    for i in range(nv):
        xyz = struct.unpack_from('<3f', vertices, i*32)
        visibility, color, uv, normal, tangent = struct.unpack_from('<5I', vertices, i*32+12)
        uvs = struct.unpack('<2e', struct.pack('<I', uv))
        require(all(math.isfinite(x) for x in (*xyz, *uvs)), 'Nonfinite position/UV')
        rows.append({'position':xyz, 'uv':uvs, 'normal':normal, 'tangent':tangent,
                     'visibility':visibility, 'color':color})
    indices = list(struct.iter_unpack('<3H', triangles))
    require(all(i < nv for face in indices for i in face), 'Index outside vertex array')
    return {'name':name, 'flags':flags, 'rows':rows, 'triangles':indices,
            'vertex_bytes':vertices, 'triangle_bytes':triangles, 'prefix_bytes':reader.offset,
            'trailing_bytes_not_audited':len(data)-reader.offset}

def audit_frames(mesh, codec='h1_unorm10'):
    normal_errors, tangent_errors, normal_angles, tangent_angles, handedness = [], [], [], [], []
    for triangle in mesh['triangles']:
        a, b, c = (mesh['rows'][i] for i in triangle)
        e1, e2 = sub(b['position'], a['position']), sub(c['position'], a['position'])
        du1, dv1 = sub(b['uv'], a['uv'])
        du2, dv2 = sub(c['uv'], a['uv'])
        determinant = du1*dv2-du2*dv1
        require(abs(determinant) > 1e-12, 'Degenerate UV triangle')
        normal = unit(cross(e1, e2))
        tangent = unit(tuple((e1[k]*dv2-e2[k]*dv1)/determinant for k in range(3)))
        bitangent = unit(tuple((e2[k]*du1-e1[k]*du2)/determinant for k in range(3)))
        handedness.append(1 if dot(cross(normal, tangent), bitangent) > 0 else -1)
        for vertex in (a, b, c):
            n, t = decode(vertex['normal'], codec), decode(vertex['tangent'], codec)
            normal_errors.append(max(abs(x-y) for x, y in zip(n, normal)))
            tangent_errors.append(max(abs(x-y) for x, y in zip(t, tangent)))
            normal_angles.append(math.degrees(math.acos(max(-1., min(1., dot(unit(n), normal))))))
            tangent_angles.append(math.degrees(math.acos(max(-1., min(1., dot(unit(t), tangent))))))
    return {'codec_hypothesis':codec, 'triangle_count':len(handedness),
            'normal_max_component_error':max(normal_errors), 'tangent_max_component_error':max(tangent_errors),
            'normal_max_angle_degrees':max(normal_angles), 'tangent_max_angle_degrees':max(tangent_angles),
            'positive_uv_handedness_triangles':handedness.count(1), 'negative_uv_handedness_triangles':handedness.count(-1),
            'source_geometry_consistent':max(normal_errors+tangent_errors) <= 1/1023+1e-12}

def read_bounded(path):
    with path.open('rb') as stream: data = stream.read(MAX_BYTES+1)
    require(len(data) <= MAX_BYTES, 'File exceeds 2 MiB bound')
    return data

def audit(source, roundtrip):
    original, returned = read_bounded(source), read_bounded(roundtrip)
    a, b = read_prefix(original), read_prefix(returned)
    require(a['name'] == b['name'], 'Different surface names')
    return {'schema':'iw7.packed-frame-source-audit/1',
            'source':{'bytes':len(original), 'sha256':sha(original)},
            'roundtrip':{'bytes':len(returned), 'sha256':sha(returned)},
            'surface':a['name'], 'vertices':len(a['rows']), 'triangles':len(a['triangles']),
            'vertex_stride':32, 'normal_offset':24, 'tangent_offset':28,
            'prefix_only':True, 'remaining_bytes_not_audited':a['trailing_bytes_not_audited'],
            'vertex_bytes_identical':a['vertex_bytes'] == b['vertex_bytes'],
            'triangle_bytes_identical':a['triangle_bytes'] == b['triangle_bytes'],
            'vertex_stream_sha256':sha(a['vertex_bytes']),
            'normal_top_two_bits':dict(Counter(str(v['normal'] >> 30) for v in a['rows'])),
            'tangent_top_two_bits':dict(Counter(str(v['tangent'] >> 30) for v in a['rows'])),
            'normal_words':sorted({f"0x{v['normal']:08X}" for v in a['rows']}),
            'tangent_words':sorted({f"0x{v['tangent']:08X}" for v in a['rows']}),
            'hypotheses':[audit_frames(a, codec) for codec in ('h1_unorm10','midpoint10','signed10')],
            'roundtrip_h1_hypothesis':audit_frames(b),
            'iw7_shader_decoder_verified':False, 'tangent_sign_semantics_verified':False,
            'lighting_cause_established':False, 'assets_modified':False}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--roundtrip', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.source, args.roundtrip), indent=2))

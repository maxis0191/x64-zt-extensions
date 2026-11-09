"""IW7 packed vertex / blend encodings (pure Python)."""
import math
import struct


def half_to_float(h):
    return struct.unpack("<e", struct.pack("<H", h))[0]


def float_to_half(f):
    return struct.unpack("<H", struct.pack("<e", f))[0]


def unpack_uv(packed):
    return half_to_float(packed & 0xFFFF), half_to_float(packed >> 16)


def pack_uv(u, v):
    return float_to_half(u) | (float_to_half(v) << 16)


def unpack_normal(packed):
    """PackedUnitVec: 3 x 10-bit unorm (x bits 0-9, y 10-19, z 20-29), c = q/1023*2-1; bits 30-31 = w/sign.
    Normals always carry 3 in bits 30-31; tangents carry 3 or 0 (bitangent sign)."""
    return tuple(((packed >> (10 * i)) & 0x3FF) / 1023.0 * 2.0 - 1.0 for i in range(3))


def pack_normal(n, top=3):
    out = 0
    for i, c in enumerate(n):
        q = int(math.floor((max(-1.0, min(1.0, c)) + 1.0) * 0.5 * 1023.0 + 0.5))
        out |= min(1023, max(0, q)) << (10 * i)
    return out | ((top & 3) << 30)


def part_bits(bones):
    """int[8] bone mask: bone b sets bit (0x80000000 >> (b & 31)) of word b >> 5 (signed int32 values)."""
    w = [0] * 8
    for b in bones:
        w[b >> 5] |= 0x80000000 >> (b & 31)
    return [x - (1 << 32) if x & 0x80000000 else x for x in w]


def surface_bones(s):
    used = set()
    for rl in s.rigid:
        used.add(rl[0])
    if s.blend:
        for _, inf, _ in decode_blend(s.blend, s.blend_counts):
            used.update(b for b, _ in inf)
    return used


def decode_blend(shorts, counts):
    """IW7 XBlendInfo stream. Group g (g+1 influences) stores per vertex 2*(g+1) u16:
    bone0, then (bone_i, weight_i) for i=1..g, then one trailing u16. Bones are plain bone indices
    (H1 stores index*64). weight_i is a u16 fraction of 65536; weight0 = 1 - sum(weight_i).
    Vertices covered by blend groups are the first sum(counts) vertices, in group order."""
    out = []
    a = vi = 0
    for g, n in enumerate(counts):
        for _ in range(n):
            bones = [shorts[a]]
            ws = []
            for i in range(g):
                bones.append(shorts[a + 1 + 2 * i])
                ws.append(shorts[a + 2 + 2 * i])
            trail = shorts[a + 2 * g + 1]
            w0 = 65536 - sum(ws)
            out.append((vi, list(zip(bones, [w0 / 65536.0] + [w / 65536.0 for w in ws])), trail))
            a += 2 * (g + 1)
            vi += 1
    return out


def encode_blend(influences_by_vertex):
    """influences_by_vertex: list (vertex order) of [(bone, weight_u16_or_None), ...] with the vertex list already
    sorted by influence count. Returns (shorts, counts). weight of the first influence is implicit."""
    counts = [0] * 8
    shorts = []
    for inf in influences_by_vertex:
        g = len(inf) - 1
        counts[g] += 1
        shorts.append(inf[0][0])
        for b, w in inf[1:]:
            shorts += [b, w]
        shorts.append(0)
    return shorts, counts

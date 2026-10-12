"""Strict independent reader for this original H1 probe, not a retail importer.

Follows production read order; validates geometry from triangle/UV cross products.
Does not implement or emulate H1->IW7 conversion. OFFSET and optional streams
are deliberately outside this fixture's profile.
"""
import argparse
import json
import math
from pathlib import Path
import struct


def check(ok, reason):
    if not ok:
        raise ValueError(reason)


class Reader:
    def __init__(self, data):
        check(0 < len(data) <= 1024 * 1024, "input size outside fixture bound")
        self.data, self.pos = data, 0
        self.records = {}

    def take(self, count):
        check(0 <= count <= len(self.data) - self.pos, "truncated record")
        start = self.pos
        self.pos += count
        return self.data[start:self.pos]

    def start(self, label, kind):
        self.records[label] = self.pos
        tag, exists = self.take(2)
        check(tag == kind, "record type mismatch: " + label)
        check(exists in (0, 1), "noncanonical existence tag")
        return exists

    def array(self, label, stride, expected):
        exists = self.start(label, 8)
        if not exists:
            check(expected == 0, "required array absent: " + label)
            return b""
        count, = struct.unpack("<I", self.take(4))
        check(0 < count <= 256 and count == expected, "array count mismatch: " + label)
        return self.take(count * stride)

    def name(self, label, kind, expected):
        if not self.start(label, kind):
            check(expected is None, "required name absent: " + label)
            return None
        stop = self.data.find(b"\0", self.pos, self.pos + 129)
        check(stop >= self.pos, "name missing bounded terminator")
        value = self.take(stop - self.pos + 1)[:-1].decode("ascii")
        check(value == expected, "name mismatch: " + label)
        return value

    def absent_raw(self, label):
        check(not self.start(label, 10), "optional raw stream outside profile")

    def finish(self):
        check(self.pos == len(self.data), "unexpected trailing bytes")


def values(data, offset, fmt):
    return struct.unpack_from("<" + fmt, data, offset)


def zero_except(data, ranges):
    rest = bytearray(data)
    for offset, length in ranges:
        rest[offset:offset + length] = bytes(length)
    check(not any(rest), "unexpected pointer/optional/reserved field")


def inspect_model(data):
    r = Reader(data)
    h = r.array("model", 680, 1)
    check(values(h, 8, "4B") == (1, 1, 1, 0), "one rigid root/material profile required")
    check(values(h, 16, "f") == (1.0,), "model scale")
    check(values(h, 20, "8I") == (0x80000000, 0, 0, 0, 0, 0, 0, 0), "root noScale bits")
    check(values(h, 128, "fHH") == (1000.0, 1, 0), "LOD range")
    check(values(h, 144, "8I") == (0x80000000, 0, 0, 0, 0, 0, 0, 0), "LOD root bits")
    check(values(h, 512, "4BHH") == (1, 0, 0, 0, 0, 0), "unsupported model features")
    radius, = values(h, 544, "f")
    check(abs(radius * radius - 192) < 0.0001, "bounding radius")
    check(values(h, 548, "6f") == (0, 0, 0, 8, 8, 8), "model bounds")
    zero_except(h, ((8,3),(16,36),(128,8),(144,32),(512,1),(544,28)))
    model = r.name("model_name", 6, "paris_h1_original_cube")
    check(r.array("bone_names", 4, 1) == bytes(4), "unresolved source token must be zero")
    r.name("bone_string", 6, "tag_origin")
    for label, stride in (("parents",1),("angles",8),("positions",12)):
        r.array(label, stride, 0)
    check(r.array("classification",1,1) == b"\0", "bone classification")
    check(values(r.array("base_mat",32,1),0,"8f") == (0,0,0,1,0,0,0,2), "identity bind pose")
    for label, stride in (("reactive_parts",16),("reactive_tweaks",16),("coll_surfs",36)):
        r.array(label,stride,0)
    check(values(r.array("bone_info",28,1),0,"7f") == (0,0,0,8,8,8,192), "bone bounds")
    check(r.array("mip_radius",2,1) == b"\xff\xff", "mip radius sentinel")
    check(r.array("material_handles",8,1) == bytes(8), "pointer-free material handle")
    material = r.name("material",7,"paris_h1_original_material")
    surface = r.name("lod0",7,"paris_h1_original_cube_lod0")
    for i in range(1,6):
        r.name("lod" + str(i),7,None)
    for label in ("physics_preset","physics_collmap"):
        r.name(label,7,None)
    for label, stride in (("weight_names",4),("weight_maps",8),("mdao",1),("composite",8)):
        r.array(label,stride,0)
    r.name("skeleton",7,None)
    r.array("bone_physics",1,0)
    r.finish()
    return {"model":model,"surface":surface,"material_reference":material,
            "num_bones":1,"num_lods":1,"bounds_half_size":[8,8,8]}, r.records


def subtract(a,b):
    return tuple(x-y for x,y in zip(a,b))


def dot(a,b):
    return sum(x*y for x,y in zip(a,b))


def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def unit(v):
    length = math.sqrt(dot(v,v))
    check(length > 1e-8, "degenerate vector")
    return tuple(x/length for x in v)


def direction(word):
    check(word >> 30 == 3, "H1 normal/tangent upper bits")
    return unit(tuple(((word >> shift) & 1023) / 1023 * 2 - 1 for shift in (0,10,20)))


def inspect_surface(data):
    r = Reader(data)
    h = r.array("model_surfs",56,1)
    check(values(h,16,"H") == (1,), "single surface required")
    check(values(h,20,"8I") == (0x80000000,0,0,0,0,0,0,0), "surface group root bits")
    zero_except(h, ((16,2),(20,32)))
    name = r.name("surface_name",6,"paris_h1_original_cube_lod0")
    s = r.array("surfaces",264,1)
    check(values(s,0,"HHHBB") == (0,24,12,1,0), "rigid ordinary vertex profile")
    check(values(s,228,"8I") == (0x80000000,0,0,0,0,0,0,0), "surface root bits")
    zero_except(s, ((0,8),(228,32)))
    raw = r.array("vertices",32,24)
    vertices = []
    for offset in range(0,len(raw),32):
        x,y,z,sign,color = values(raw,offset,"4fI")
        uv = values(raw,offset+20,"2e")
        normal,tangent = values(raw,offset+24,"2I")
        check(all(math.isfinite(v) for v in (x,y,z,sign,*uv)), "nonfinite vertex")
        check(all(abs(v) == 8 for v in (x,y,z)), "cube position/bounds mismatch")
        check(sign == 1 and color == 0xFFFFFFFF, "vertex sign/color")
        check(all(v in (0,1) for v in uv), "fixture UV range")
        vertices.append(((x,y,z), uv, direction(normal), direction(tangent)))
    triangles = r.array("triangles",6,12)
    check(r.array("triangles_secondary",6,12) == triangles, "secondary topology differs")
    rigid = r.array("rigid_lists",16,1)
    check(values(rigid,0,"4HQ") == (0,24,0,12,0), "rigid vertex coverage/collision tree")
    for label in ("unknown0","blend","blend_table","lmap","tension","tension_accum"):
        r.absent_raw(label)
    r.array("blend_shapes",1,0)
    r.finish()
    normals, used = {}, set()
    for offset in range(0,len(triangles),6):
        indices = values(triangles,offset,"3H")
        check(len(set(indices)) == 3 and max(indices) < 24, "invalid triangle indices")
        used.update(indices)
        a,b,c = (vertices[i] for i in indices)
        e1,e2 = subtract(b[0],a[0]),subtract(c[0],a[0])
        n = unit(cross(e1,e2))
        check(dot(n,a[0]) > 0, "triangle points inward")
        du1,dv1 = subtract(b[1],a[1]); du2,dv2 = subtract(c[1],a[1])
        det = du1*dv2-du2*dv1
        check(abs(det) > 1e-8, "degenerate UVs")
        tangent = unit(tuple((x*dv2-y*dv1)/det for x,y in zip(e1,e2)))
        bitangent = unit(tuple((y*du1-x*du2)/det for x,y in zip(e1,e2)))
        check(dot(cross(n,tangent),bitangent) > .999, "negative UV handedness")
        for v in (a,b,c):
            check(dot(n,v[2]) > .99999 and dot(tangent,v[3]) > .99999,
                  "packed frame disagrees with independent geometry/UV frame")
        normals[n] = normals.get(n,0)+1
    axes = {(1.,0.,0.),(-1.,0.,0.),(0.,1.,0.),(0.,-1.,0.),(0.,0.,1.),(0.,0.,-1.)}
    check(set(normals) == axes and set(normals.values()) == {2} and len(used) == 24,
          "cube face/vertex coverage")
    return {"surface":name,"vertices":24,"triangles":12,"rigid_groups":1,
            "optional_streams":False,"geometry_uv_frames_checked":12}, r.records


def inspect_pair(xmb, xsb):
    model,_ = inspect_model(xmb)
    surface,_ = inspect_surface(xsb)
    check(model["surface"] == surface["surface"], "LOD dependency mismatch")
    return {"model":model,"surface":surface,"format":"H1 x64 assetmanager dump",
            "native_validation":False,"complete_material":False}


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("xmb",type=Path)
    cli.add_argument("xsb",type=Path)
    args = cli.parse_args()
    for path in (args.xmb,args.xsb):
        check(path.is_file() and path.stat().st_size <= 1024*1024, "bounded file required")
    print(json.dumps(inspect_pair(args.xmb.read_bytes(),args.xsb.read_bytes()),indent=2))

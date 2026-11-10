"""Minimal pure-Python glTF 2.0 binary (.glb) reader: meshes/primitives/accessors and skins."""
import json
import struct

_CT = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}
_NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


class Glb:
    def __init__(self, path):
        b = open(path, "rb").read()
        magic, ver, length = struct.unpack_from("<III", b, 0)
        assert magic == 0x46546C67, "not a glb"
        p, self.json, self.bin = 12, None, b""
        while p < length:
            clen, ctype = struct.unpack_from("<II", b, p)
            chunk = b[p + 8:p + 8 + clen]
            if ctype == 0x4E4F534A:
                self.json = json.loads(chunk)
            elif ctype == 0x004E4942:
                self.bin = chunk
            p += 8 + clen

    def accessor(self, i):
        a = self.json["accessors"][i]
        bv = self.json["bufferViews"][a["bufferView"]]
        n, ct = _NC[a["type"]], _CT[a["componentType"]]
        size = struct.calcsize("<" + ct) * n
        stride = bv.get("byteStride", size)
        off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        out = []
        norm = a.get("normalized", False)
        scale = {"B": 255.0, "H": 65535.0, "b": 127.0, "h": 32767.0}.get(ct, 1.0) if norm else 1.0
        for k in range(a["count"]):
            v = struct.unpack_from("<%d%s" % (n, ct), self.bin, off + k * stride)
            if scale != 1.0:
                v = tuple(x / scale for x in v)
            out.append(v if n > 1 else v[0])
        return out

    def primitives(self):
        for mi, mesh in enumerate(self.json.get("meshes", [])):
            for pi, prim in enumerate(mesh["primitives"]):
                yield mi, pi, mesh.get("name"), prim

    def joint_names(self, skin=0):
        sk = self.json["skins"][skin]
        return [self.json["nodes"][j].get("name") for j in sk["joints"]]

import struct
import unittest
import zlib

from inspect_fbx import inspect, Reader


def scalar(value):
    if type(value) is int:
        return b"L"+struct.pack("<q", value)
    payload = value.encode()
    return b"S"+struct.pack("<I", len(payload))+payload


def array(format_, values, compressed=True):
    raw = b"".join(struct.pack("<"+format_, value) for value in values)
    packed = zlib.compress(raw) if compressed else raw
    return format_.encode()+struct.pack("<III", len(values), int(compressed), len(packed))+packed


def node(start, name, properties=(), children=()):
    name = name.encode()
    properties = list(properties)
    payload = b"".join(properties)
    offset = start+13+len(name)+len(payload)
    child_bytes = b""
    for child in children:
        encoded = node(offset, **child)
        child_bytes += encoded
        offset += len(encoded)
    if children:
        child_bytes += b"\x00"*13
    return struct.pack("<IIIB", start+13+len(name)+len(payload)+len(child_bytes), len(properties), len(payload), len(name))+name+payload+child_bytes


def fixture(positions=None, indices=None):
    geometry = {"name": "Geometry", "properties": [scalar(1), scalar("mesh"), scalar("Mesh")], "children": [
        {"name": "Vertices", "properties": [array("d", positions or [0.,0.,0.,1.,0.,0.,0.,1.,0.])]},
        {"name": "PolygonVertexIndex", "properties": [array("i", indices or [0,1,-3])]}]}
    objects = node(27, "Objects", children=[geometry, {"name": "Model", "properties": [scalar(2), scalar("mesh"), scalar("Mesh")]}])
    return b"Kaydara FBX Binary  \x00\x1a\x00"+struct.pack("<I", 7400)+objects+b"\x00"*13


class FbxTests(unittest.TestCase):
    def test_mesh_counts_are_source_only(self):
        report = inspect(fixture())
        self.assertEqual(report["meshes"][0]["source_positions"], 3)
        self.assertEqual(report["meshes"][0]["source_polygons"], 1)
        self.assertEqual(report["meshes"][0]["fan_triangulation_count_only"], 1)
        self.assertEqual(report["object_type_counts"], {"Geometry": 1, "Model": 1})
        self.assertEqual(report["deformers"], [])
        self.assertEqual(report["animation_stacks"], [])
        self.assertFalse(report["converted"])

    def test_bad_source_vertices_indices_and_polygon(self):
        for payload in (fixture([float("nan"),0.,0.]), fixture(indices=[0,1,-4]), fixture(indices=[0,1,2]), fixture(indices=[0,0,-3])):
            with self.assertRaises(ValueError):
                inspect(payload)

    def test_end_offsets_and_property_bytes(self):
        for offset in (27, 27+4, 27+8):
            data = bytearray(fixture())
            struct.pack_into("<I", data, offset, 0xFFFFFFFF)
            with self.assertRaises(ValueError):
                inspect(bytes(data))
        with self.assertRaises(ValueError):
            inspect(fixture()[:-20])

    def test_compression_count_and_expansion_bounds(self):
        data = b"i"+struct.pack("<III", 1, 1, len(zlib.compress(b"x"*1000)))+zlib.compress(b"x"*1000)
        reader = Reader(fixture())
        reader.payload = data
        reader.offset = 0
        with self.assertRaises(ValueError):
            reader.property(len(data))
        reader.payload = b"d"+struct.pack("<III", 2*1024*1024, 0, 0)
        reader.offset = 0
        with self.assertRaises(ValueError):
            reader.property(len(reader.payload))


if __name__ == "__main__":
    unittest.main()

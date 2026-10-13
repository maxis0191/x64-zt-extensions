"""Bounded binary FBX inventory; never imports a 3D runtime or evaluates code."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import zlib

from prepare_writer import unlinked, require

MAX_INPUT = 4*1024*1024
MAX_ARRAY = 8*1024*1024


class Reader:
    def __init__(self, payload):
        require(27 <= len(payload) <= MAX_INPUT and payload[:23] == b"Kaydara FBX Binary  \x00\x1a\x00", "bounded binary FBX required")
        self.payload = payload
        self.version = int.from_bytes(payload[23:27], "little")
        require(self.version in (7400, 7500), "explicit FBX7400/7500 format required")
        self.offset = 27
        self.nodes = 0
        self.expanded_bytes = 0
        self.header = "<QQQB" if self.version >= 7500 else "<IIIB"
        self.header_bytes = struct.calcsize(self.header)

    def take(self, count, end):
        require(type(count) is int and count >= 0 and self.offset+count <= end <= len(self.payload), "truncated/out-of-owner FBX data")
        result = self.payload[self.offset:self.offset+count]
        self.offset += count
        return result

    def number(self, format_, end):
        return struct.unpack(format_, self.take(struct.calcsize(format_), end))[0]

    def property(self, end):
        type_ = self.take(1, end)
        scalars = {b"Y": "<h", b"C": "<?", b"I": "<i", b"F": "<f", b"D": "<d", b"L": "<q"}
        if type_ in scalars:
            value = self.number(scalars[type_], end)
            require(not isinstance(value, float) or math.isfinite(value), "nonfinite FBX scalar")
            return value
        if type_ in (b"S", b"R"):
            size = self.number("<I", end)
            require(size <= 256*1024, "bounded FBX string/raw property required")
            data = self.take(size, end)
            return data.decode("utf-8", errors="strict") if type_ == b"S" else {"raw_bytes": size}
        arrays = {b"f": "<f", b"d": "<d", b"i": "<i", b"l": "<q", b"b": "<?", b"c": "<b"}
        require(type_ in arrays, "unsupported FBX property type")
        count, encoding, size = struct.unpack("<III", self.take(12, end))
        width = struct.calcsize(arrays[type_])
        require(0 < count <= 2*1024*1024 and count*width <= MAX_ARRAY and encoding in (0, 1), "bounded typed FBX array required")
        packed = self.take(size, end)
        if encoding:
            decoder = zlib.decompressobj()
            data = decoder.decompress(packed, count*width+1)
            require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail, "exact bounded FBX compressed array required")
        else:
            data = packed
        require(len(data) == count*width, "FBX array count/bytes differ")
        self.expanded_bytes += len(data)
        require(self.expanded_bytes <= 32*1024*1024, "FBX total expanded array bound exceeded")
        values = [value[0] for value in struct.iter_unpack(arrays[type_], data)]
        require(all(not isinstance(value, float) or math.isfinite(value) for value in values), "nonfinite FBX array")
        return values

    def node(self, parent_end, depth=0):
        require(depth <= 32 and self.nodes < 16384, "bounded FBX node tree required")
        header = self.take(self.header_bytes, parent_end)
        end, count, property_bytes, name_bytes = struct.unpack(self.header, header)
        if not any(header):
            return None
        self.nodes += 1
        require(self.offset <= end <= parent_end and count <= 4096 and property_bytes <= MAX_INPUT and name_bytes <= 128, "owned FBX node end/count required")
        name = self.take(name_bytes, end).decode("ascii", errors="strict")
        property_end = self.offset+property_bytes
        require(property_end <= end, "properties cross FBX node end")
        properties = [self.property(property_end) for _ in range(count)]
        require(self.offset == property_end, "FBX property byte length differs")
        children = []
        while self.offset < end:
            child = self.node(end, depth+1)
            if child is None:
                require(self.offset == end, "FBX node sentinel differs from end")
                break
            children.append(child)
        require(self.offset == end, "FBX node not consumed")
        return {"name": name, "properties": properties, "children": children}

    def read(self):
        nodes = []
        while self.offset+self.header_bytes <= len(self.payload):
            node = self.node(len(self.payload))
            if node is None:
                break
            nodes.append(node)
        return nodes


def one_child(node, name):
    values = [child for child in node["children"] if child["name"] == name]
    require(len(values) == 1, "one exact FBX array node required: "+name)
    return values[0]["properties"]


def inspect(payload):
    reader = Reader(payload)
    tree = reader.read()
    objects = [node for node in tree if node["name"] == "Objects"]
    require(len(objects) == 1, "one FBX Objects section required")
    objects = objects[0]["children"]
    counts = {}
    for node in objects:
        counts[node["name"]] = counts.get(node["name"], 0)+1
    meshes = []
    for node in objects:
        if node["name"] != "Geometry" or len(node["properties"]) != 3 or node["properties"][2] != "Mesh":
            continue
        positions, = one_child(node, "Vertices")
        indices, = one_child(node, "PolygonVertexIndex")
        require(isinstance(positions, list) and len(positions)%3 == 0 and isinstance(indices, list), "typed mesh arrays required")
        vertex_count = len(positions)//3
        polygons = []
        polygon = []
        for index in indices:
            require(type(index) is int, "integral FBX polygon index required")
            vertex = -index-1 if index < 0 else index
            require(0 <= vertex < vertex_count, "FBX polygon index outside positions")
            polygon.append(vertex)
            if index < 0:
                require(3 <= len(polygon) <= 64 and len(set(polygon)) == len(polygon), "bounded nonrepeating source polygon required")
                polygons.append(polygon)
                polygon = []
        require(not polygon, "unterminated FBX polygon")
        polygon_sizes = {}
        for polygon in polygons:
            polygon_sizes[str(len(polygon))] = polygon_sizes.get(str(len(polygon)), 0)+1
        meshes.append({"id": node["properties"][0], "name": node["properties"][1], "source_positions": vertex_count,
                       "source_polygons": len(polygons), "polygon_size_counts": polygon_sizes,
                       "fan_triangulation_count_only": sum(len(polygon)-2 for polygon in polygons),
                       "layer_elements": [child["name"] for child in node["children"] if child["name"].startswith("LayerElement")],
                       "triangulation_evaluated": False, "split_vertex_count_measured": False})
    models = [{"id": node["properties"][0], "name": node["properties"][1], "type": node["properties"][2]}
              for node in objects if node["name"] == "Model" and len(node["properties"]) == 3]
    deformers = [{"id": node["properties"][0], "name": node["properties"][1], "type": node["properties"][2]}
                 for node in objects if node["name"] == "Deformer" and len(node["properties"]) == 3]
    stacks = [{"id": node["properties"][0], "name": node["properties"][1]}
              for node in objects if node["name"] == "AnimationStack" and len(node["properties"]) >= 2]
    return {"schema": "iw7.doom-fbx-inventory/1", "fbx_version": reader.version,
            "input_bytes": len(payload), "source_sha256": hashlib.sha256(payload).hexdigest().upper(),
            "parsed_nodes": reader.nodes, "expanded_array_bytes": reader.expanded_bytes, "object_type_counts": counts,
            "meshes": meshes, "models": models, "deformers": deformers, "animation_stacks": stacks,
            "rig_evaluated": False, "animations_evaluated": False, "converted": False, "ready": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    source = unlinked(arguments.source)
    require(0 < source.stat().st_size <= MAX_INPUT, "bounded regular FBX file required")
    payload = source.read_bytes()
    require(hashlib.sha256(payload).hexdigest().upper() == arguments.sha256.upper(), "FBX source hash differs")
    value = inspect(payload)
    output = unlinked(arguments.output)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
    print(json.dumps(value, indent=2))

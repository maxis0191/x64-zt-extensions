"""Source-fixture bridge from an immutable decoded span to existing skin mapping.

No IO, decoding, pointers, native stride admission, binds or weapon serialization.
The 12/16/12/2 strides reproduce primary source, not an observed Ray Gun payload.
"""
import math
import struct
from animated.preflight import decode_stream_weights, integer, names, require, schema
from animated.reorder_proposal import regroup_surface


def _slice_range(offset, base, count, stride, extent):
    integer(offset, 0, 2**32 - 1, 'stream offset')
    integer(base, 0, 2**32 - 1, 'stream base')
    start = offset + base * stride  # Unbounded arithmetic, never a uint32 wrap.
    require(start <= extent and count <= (extent - start) // stride,
            'stream_extent', 'selected rows outside the owned decoded span')
    return start, start + count * stride


def map_owned_source_surface(payload, shared, surface, bone_names):
    """Prepare source-shaped rows for serializer51; production admission stays false."""
    schema(shared, ('dataSize', 'flags', 'vertCount', 'indexCount', 'posOffset',
                    'vertsOffset', 'skinWeightsOffset', 'indicesOffset'))
    schema(surface, ('vertCount', 'triCount', 'baseVertOffset', 'baseIndexOffset',
                     'flags', 'vertListCount', 'partBits'))
    extent = integer(shared['dataSize'], 1, 256 * 1024, 'dataSize')
    require(type(payload) is bytes and len(payload) == extent,
            'owned_payload', 'exact immutable decoded bytes required')
    require(type(shared['flags']) is int and shared['flags'] in (0, 1),
            'shared_flags', 'resident/streamed source declaration only')
    require(type(surface['flags']) is int and surface['flags'] == 2 and
            type(surface['vertListCount']) is int and surface['vertListCount'] == 0,
            'surface_profile', 'separate pure-skinned source profile; no rigid/collision list')
    vertices = integer(surface['vertCount'], 1, 65535, 'vertCount')
    triangles = integer(surface['triCount'], 1, 65535, 'triCount')
    shared_vertices = integer(shared['vertCount'], 1, 2**32 - 1, 'shared vertCount')
    shared_indices = integer(shared['indexCount'], 1, 2**32 - 1, 'shared indexCount')
    bv = integer(surface['baseVertOffset'], 0, 2**32 - 1, 'baseVertOffset')
    bi = integer(surface['baseIndexOffset'], 0, 2**32 - 1, 'baseIndexOffset')
    require(bv <= shared_vertices and vertices <= shared_vertices - bv and
            bi <= shared_indices and 3 * triangles <= shared_indices - bi,
            'shared_counts', 'surface exceeds selected shared counts')
    require(type(bone_names) is list, 'bone_names', 'resolved names required, not ScrString IDs')
    bone_count = integer(len(bone_names), 2, 255, 'source fixture bone count')
    names(bone_names, bone_count)
    # Check every range before copying any source row. Bi counts indices, not triangles.
    ranges = {field: _slice_range(shared[offset], base, count, stride, extent)
              for field, offset, base, count, stride in (
                  ('positions', 'posOffset', bv, vertices, 12),
                  ('attributes', 'vertsOffset', bv, vertices, 16),
                  ('weights', 'skinWeightsOffset', bv, vertices, 12),
                  ('triangles', 'indicesOffset', bi, 3 * triangles, 2))}
    snapshot = {field: payload[start:end] for field, (start, end) in ranges.items()}
    require(all(math.isfinite(value) for row in struct.iter_unpack('<3f', snapshot['positions'])
                for value in row), 'nonfinite_position', 'source positions')
    snapshot.update(vertCount=vertices, triCount=triangles, boneCount=bone_count,
                    sharedFlags=0, surfaceFlags=2, vertListCount=0,
                    partBits=surface['partBits'])
    # sharedFlags=0 describes the new owned snapshot, not a mutation of the donor.
    mapped = regroup_surface(snapshot)
    rows = decode_stream_weights(mapped['snapshot']['weights'], vertices, bone_count)
    counts = [sum(row['influences'] == count for row in rows) for count in range(1, 5)]
    words = tuple(word for row in rows for word in row['iw7_words'])
    return {**mapped, 'selected_ranges': ranges, 'source_shared_flags': shared['flags'],
            'resolved_bone_names': tuple(bone_names), 'influence_rows': rows,
            'iw7_blend_counts': counts, 'iw7_blend_words': words,
            'iw7_blend_bytes': struct.pack('<' + 'H' * len(words), *words),
            'native_stride_provenance': 'Pending', 'tag_position_stride': None,
            'production_admissible': False, 'raygun_donor_observed': False,
            'binds_verified': False, 'weight_direction_engine_verified': False}

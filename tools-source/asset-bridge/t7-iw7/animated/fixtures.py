"""Original author-created arrays. No retail/extracted bytes or string IDs."""
import struct

from preflight import ABSENT, FLAGS, STREAMS, ZERO_COUNTS


def skeleton():
    return {"numBones": 2, "numRootBones": 1, "numCosmeticBones": 0,
            "names": ["tag_origin", "tag_original_hinge"], "parentList": b"\x01",
            "tagAngles": struct.pack("<4e", 0, 0, 0, 1),
            "tagPositions": struct.pack("<3f", 0, 0, 4), "partClassification": b"\0\0",
            "baseMat": struct.pack("<16f", 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 1, 0, 0, 4, 2),
            "positionLayout": "original-declaration-shaped-xyz12"}


def weight(values, ids):
    return struct.pack("<4B4H", *(tuple(values) + (0,) * (4 - len(values))),
                       *(tuple(ids) + (0,) * (4 - len(ids))))


def grouped_weights():
    return weight((255,), (0,)) + weight((255,), (1,)) + weight((64, 191), (0, 1))


def ungrouped_surface():
    # Triangle with all distinct positions and every attribute byte identifiable.
    # Classes [2,1,2]; no T7 donor or universal format invariant is asserted.
    return {"positions": struct.pack("<9f", 0, 0, 0, 1, 0, 0, 0, 1, 0),
            "attributes": bytes(range(48)), "triangles": struct.pack("<3H", 0, 1, 2),
            "weights": weight((64, 191), (0, 1)) + weight((255,), (1,)) + weight((128, 127), (0, 1)),
            "vertCount": 3, "triCount": 1, "boneCount": 2, "sharedFlags": 0,
            "surfaceFlags": 2, "vertListCount": 0, "partBits": b"\0" * 48}


def clip():
    c = {key: False for key in FLAGS + ABSENT}
    c.update({key: 0 for key in ZERO_COUNTS})
    for key in STREAMS:
        c[key] = b""
        c["indexCount" if key == "indices" else key + "Count"] = 0
    c.update(numframes=2, numBones=2, boneCount=[1, 0, 1, 0, 0, 0, 0, 0, 2, 2],
             names=skeleton()["names"], framerate=30., frequency=15., primedLength=0., loopEntryTime=0.,
             dataByte=b"\0\x01\x02", dataByteCount=3,
             dataShort=struct.pack("<H", 2), dataShortCount=1,
             randomDataShort=struct.pack("<12e", 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1),
             randomDataShortCount=12)
    return c

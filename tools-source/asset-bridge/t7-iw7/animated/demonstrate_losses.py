"""Print minimal original reproductions. No files, assets or processes are read."""
import json
import struct

import fixtures
from preflight import NARROWED, Refusal, preflight_clip, preflight_weights
from reorder_proposal import regroup_surface


def refusal(function, *args):
    try:
        function(*args)
    except Refusal as error:
        return error.code
    raise AssertionError("expected an explicit refusal")


def demonstrate():
    surface = fixtures.ungrouped_surface()
    fixed = regroup_surface(surface)
    counters = []
    for field in NARROWED:
        c = fixtures.clip()
        stream = field[:-5]
        stride = 1 if stream == "dataByte" else 2 if stream == "dataShort" else 4
        c[field], c[stream] = 65536, b"\0" * (65536 * stride)
        counters.append({"field": field, "source_count": 65536, "unsigned_short_cast": 0,
                         "original_array_bytes": len(c[stream]),
                         "refusal": refusal(preflight_clip, c, c["names"])})
    c = fixtures.clip()
    c["extraChannelData"], c["extraChannelDataCount"] = b"\x42", 1
    channel = refusal(preflight_clip, c, c["names"])
    c = fixtures.clip()
    c["startupNotifyCount"] = 1
    notification = refusal(preflight_clip, c, c["names"])
    return {"evidence": "original source-algorithm reproduction; not a native execution",
            "weight_order": {"source_influence_classes": [2, 1, 2],
                             "pinned_converter_vertex_order": [0, 1, 2],
                             "pinned_converter_weight_source_vertices": [1, 0, 2],
                             "refusal": refusal(preflight_weights, surface["weights"], 3, 2),
                             "proposed_vertex_order": fixed["new_to_old"],
                             "proposed_triangle": list(struct.unpack("<3H", fixed["snapshot"]["triangles"]))},
            "counter_losses": counters,
            "omitted_extra_channel": {"original_byte": 66, "refusal": channel},
            "omitted_startup_notification": {"original_count": 1, "refusal": notification},
            "real_donor_occurrence_observed": False, "native_patch_applied": False,
            "native_patch_compiled": False, "ready": False}


if __name__ == "__main__":
    print(json.dumps(demonstrate(), indent=2))

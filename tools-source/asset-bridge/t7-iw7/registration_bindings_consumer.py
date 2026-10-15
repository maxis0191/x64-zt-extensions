"""Interpret one closed registration material's seven bindings; metadata only.

No image selection, provider access, pointer dereference, native call or mip fact.
Per-row refusal is distinct from an incomplete MODEL registration window.
"""
import argparse
import copy
import json
from pathlib import Path

import image_metadata_consumer as bounded
import incoming_image_consumer as leaf
import selected_image_request as copied

SCHEMA = "iw7.t7-registration-material-bindings/1"
PROFILE = "t7-registration-material-bindings-v1"
OUTPUT = "iw7.t7-registration-bindings-consumer/1"
PHASE = "after_original_model_add"
FALSES = "descriptor_admissible source_asset_name_association_proven model_binding_correlated renderer_binding_proven same_object_proven allocation_retained atomic_snapshot_proven runtime_abi_proven lifetime_proven pixels_copied ready".split()
BOOLS = "duplicate_registration registration_search_refused zone_load_complete bindings_enumerated refused".split()
TOP = set(FALSES + BOOLS + "schema source_profile native_source_commit zone model lod slot model_default capture_phase recheck_phase capture_ordinal model_callbacks matched_registrations registration_chain bindings binding_count image_header_bytes header_copies completed_header_bytes header_byte_limit image_name_max_utf8_bytes metadata_read_limit reason qualified_object_mip_count payload_bytes_read".split())
CHAIN = {"model_header_hex", "material_hex", "texture_table_hex"}
ROW_CHAIN = CHAIN | {"image_field_hex"}
ROW = set("index binding_hash_u32 usage_u16 image_pointer_present raw_name leading_comma_reference registration_chain binding_rechecked snapshot".split())
need, uint = copied.need, copied.uint


def chain(value, keys):
    leaf.exact(value, keys)
    return {key: bounded.address(value[key]) for key in keys}


def consume(report):
    leaf.exact(report, TOP)
    need((report["schema"], report["source_profile"], report["native_source_commit"],
          report["zone"], report["model"], report["capture_phase"], report["recheck_phase"]) ==
         (SCHEMA, PROFILE, copied.PIN, "mp_freerun_04", bounded.MODEL, PHASE, PHASE),
         "exact registration bindings source/model/phases required")
    for key in FALSES:
        need(report[key] is False, "metadata cannot promote descriptor, association or runtime proof")
    for key in BOOLS:
        need(type(report[key]) is bool, "typed registration window flag required")
    need(report["model_default"] is None and report["qualified_object_mip_count"] is None,
         "default lookup and object mip facts remain unmeasured NULL")
    for key, expected in (("lod", 0), ("slot", 0), ("binding_count", 7), ("image_header_bytes", 264),
                          ("header_byte_limit", 3696), ("image_name_max_utf8_bytes", 255),
                          ("metadata_read_limit", 65536), ("payload_bytes_read", 0)):
        need(uint(report[key]) == expected, "exact finite registration scope/budget required")
    callbacks = uint(report["model_callbacks"], 1025)
    matches = uint(report["matched_registrations"], 1024)
    ordinal = uint(report["capture_ordinal"], 1)
    need(matches <= callbacks and report["duplicate_registration"] is (matches > 1),
         "MODEL registration counters differ")
    need(callbacks <= 1024 or report["registration_search_refused"], "search trigger lacks refusal")
    need(not ordinal or matches > 0, "capture requires an original selected registration")
    outer_chain = chain(report["registration_chain"], CHAIN)
    need(bool(outer_chain["material_hex"]) == bool(outer_chain["texture_table_hex"]),
         "material and texture table are published as one captured chain")
    need(not outer_chain["material_hex"] or outer_chain["model_header_hex"], "material chain lacks MODEL")
    need(not outer_chain["texture_table_hex"] or all(outer_chain.values()), "texture table chain incomplete")
    rows = report["bindings"]
    need(type(rows) is list and len(rows) <= 7, "bounded ordered binding prefix required")
    if rows:
        need(ordinal == 1 and all(outer_chain.values()), "binding rows require their recorded registration chain")
    copies, copy_fault, summaries = 0, False, []
    for index, row in enumerate(rows):
        leaf.exact(row, ROW)
        need(uint(row["index"], 6) == index, "binding indices must be the exact ordered prefix")
        uint(row["binding_hash_u32"]); uint(row["usage_u16"], 65535)
        for key in ("image_pointer_present", "binding_rechecked"):
            need(type(row[key]) is bool, "typed binding flag required")
        pointers = chain(row["registration_chain"], ROW_CHAIN)
        need(all(pointers[key] == outer_chain[key] for key in CHAIN), "row registration chain differs")
        need(row["image_pointer_present"] is (pointers["image_field_hex"] != 0),
             "recorded image pointer presence differs")
        observed, nonzero = leaf.snapshot(row["snapshot"], row["raw_name"])
        need(row["binding_rechecked"] is observed, "binding recheck differs from the owned snapshot")
        shot = row["snapshot"]
        need(not shot["header_copies"] or row["image_pointer_present"], "header copies require a recorded image field")
        if observed:
            name = row["raw_name"]  # The shared DTO validator requires bounded owned UTF-8, no NUL.
            need(not any(ord(char) < 0x20 for char in name), "C0 image name refused by registration profile")
            need(type(row["leading_comma_reference"]) is bool and
                 row["leading_comma_reference"] is name.startswith(","), "one leading-comma classification differs")
        else:
            need(row["raw_name"] is None and row["leading_comma_reference"] is None,
                 "refused binding cannot synthesize an owned image name")
        copies += shot["header_copies"]
        copy_fault = copy_fault or shot["copy_fault"]
        summaries.append({"index": index, "snapshot_observed": observed,
                          "name_category": None if not observed else
                              "reference" if row["leading_comma_reference"] else "ordinary",
                          "nonzero_descriptor_scalar_fields": nonzero})
    need(uint(report["header_copies"], 14) == copies, "published header copy count differs")
    if ordinal == 0:
        need(not rows and not any(outer_chain.values()) and not report["bindings_enumerated"],
             "no capture must retain no rows or chain")
    if report["bindings_enumerated"]:
        need(ordinal == 1 and len(rows) == 7, "enumeration requires the seven published rows")
    unknown_bytes = copy_fault or (ordinal == 1 and not report["bindings_enumerated"])
    expected_bytes = None if unknown_bytes else copies * 264
    need(report["completed_header_bytes"] is None if unknown_bytes else
         type(report["completed_header_bytes"]) is int and report["completed_header_bytes"] == expected_bytes,
         "structural/partial faults keep copied-byte total NULL; known totals must agree")
    complete = (ordinal == 1 and report["bindings_enumerated"] and report["zone_load_complete"] and
                matches == 1 and not report["duplicate_registration"] and
                not report["registration_search_refused"] and len(rows) == 7)
    need(report["refused"] is (not complete), "global refusal differs from the original registration window")
    if complete:
        need(report["reason"] is None, "complete enumeration has no global refusal reason")
    else:
        leaf.reason(report["reason"], 255)
        need(bool(report["reason"]), "global refusal requires its reason")
    return {"schema": OUTPUT, "source_schema": SCHEMA, "metadata_only": True,
            "observation_status": "complete" if complete else "refused",
            "observation": copy.deepcopy(report), "binding_summaries": summaries,
            "published_bindings": len(rows), "unpublished_bindings": 7 - len(rows),
            "observed_snapshots": sum(row["snapshot_observed"] for row in summaries),
            "refused_snapshots": sum(not row["snapshot_observed"] for row in summaries),
            **dict.fromkeys(FALSES, False), "same_pointer_proven": False,
            "qualified_object_mip_count": None, "payload_bytes_read": 0}


def classify(report, native_exit_code):
    need(type(native_exit_code) is int and -(2**31) <= native_exit_code <= 2**32 - 1,
         "typed original native exit required")
    if report is None:
        return {"outcome": "NoReport", "native_exit_code": native_exit_code, "ready": False}
    result = consume(report)
    if result["observation_status"] == "refused":
        need(native_exit_code != 0, "global refusal contradicts successful original native exit")
        outcome = "RegistrationBindingsRefused"
    else:
        outcome = "RegistrationBindingsObserved" if native_exit_code == 0 else "ValidRegistrationBindingsFromFailedProcess"
    return dict(result, outcome=outcome, native_exit_code=native_exit_code)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--native-exit-code", type=int, required=True)
    args = parser.parse_args()
    report = bounded.strict_json(bounded.read_report(args.report))
    need(type(report) is dict, "existing report must be an object; JSON null is not NoReport")
    print(json.dumps(classify(report, args.native_exit_code), indent=2))


if __name__ == "__main__":
    main()

"""Interpret closed incoming metadata. No asset selection or native/provider IO.

Ordinary names and nonzero descriptors are metadata, never full definitions.
Both names, four bounded slots and failed/partial observations remain distinct.
"""
import argparse
import json
from pathlib import Path

import image_metadata_consumer as bounded
import selected_image_request as copied

SCHEMA = "iw7.t7-incoming-image-header-observation/1"
PROFILE = "t7-incoming-image-header-observation-v1"
TARGET = "$camo_base_normal"
RULE = "strip_one_leading_comma_then_exact_case_and_dollar"
FALSES = "descriptor_admissible source_asset_name_association_proven model_binding_correlated renderer_binding_proven same_pointer_proven same_object_proven allocation_retained atomic_snapshot_proven runtime_abi_proven lifetime_proven pixels_copied ready".split()
BOOLS = "exact_argv_validated_before_arm bootstrap_complete map_complete window_complete cap_refused reference_name_observed ordinary_name_observed refused".split()
OUTER = set(FALSES + BOOLS + "schema source_profile native_source_commit target_name zone arm_phase capture_phase name_comparison_rule arm_generation image_callbacks non_target_callbacks callback_limit target_case_limit_per_phase read_bytes read_limit reference_events ordinary_name_events ordinary_absence_scope cases reason payload_bytes_read qualified_object_mip_count".split())
CASE = set("phase name_category callback_ordinal raw_name effective_name leading_comma_reference snapshot matching_events_in_phase state single_event_observed_in_phase unique_in_phase repeated_headers_compared conflict_absence_proven nonzero_descriptor_scalar_fields descriptor_admissible".split())
SNAPSHOT = set("header_observed header_copies completed_header_bytes header_rechecked name_rechecked callback_header_name_rechecked copy_fault image refused reason".split())
NONZERO = "width height depth width1 height1 level_count level_count1 map_type dxgi_format total_size flags streaming streamed_part_count".split()
ORDER = (("bootstrap", "reference"), ("bootstrap", "ordinary"),
         ("map_load", "reference"), ("map_load", "ordinary"))
need, uint = copied.need, copied.uint


def exact(value, fields):
    need(type(value) is dict and set(value) == fields, "exact observation fields required")


def reason(value, maximum):
    need(type(value) is str and len(value.encode("utf-8")) <= maximum,
         "bounded refusal reason required")


def snapshot(value, raw_name):
    exact(value, SNAPSHOT)
    for key in ("header_observed", "header_rechecked", "name_rechecked",
                "callback_header_name_rechecked", "copy_fault", "refused"):
        need(type(value[key]) is bool, "typed snapshot flag required")
    count = uint(value["header_copies"], 2)
    expected = None if value["copy_fault"] else count * 264
    need(value["completed_header_bytes"] is None if expected is None else
         type(value["completed_header_bytes"]) is int and value["completed_header_bytes"] == expected,
         "complete copy bytes differ; partial faults must stay unknown")
    observed = value["header_observed"]
    need(value["refused"] is (not observed), "snapshot refusal contradicts observation")
    for key in ("header_rechecked", "name_rechecked", "callback_header_name_rechecked"):
        need(value[key] is observed, "snapshot recheck flags contradict observation")
    if not observed:
        need(value["image"] is None, "refused snapshot cannot publish an image")
        reason(value["reason"], 255)
        return False, None
    need(not value["copy_fault"] and count == 2 and value["reason"] is None,
         "successful snapshot requires two complete rechecked copies")
    copied.validate_copied_image_metadata(value["image"])
    need(value["image"]["image_name"] == raw_name, "owned DTO name differs from callback name")
    return True, sum(value["image"][key] != 0 for key in NONZERO)


def consume(report):
    exact(report, OUTER)
    need((report["schema"], report["source_profile"], report["native_source_commit"],
          report["target_name"], report["zone"], report["arm_phase"], report["capture_phase"],
          report["name_comparison_rule"]) ==
         (SCHEMA, PROFILE, copied.PIN, TARGET, "mp_freerun_04", "before_db_add_hook_create",
          "before_image_bypass", RULE), "exact source, target and observation phases required")
    for key in FALSES:
        need(report[key] is False, "metadata cannot promote descriptor, identity, mip or runtime proof")
    for key in BOOLS:
        need(type(report[key]) is bool, "typed observation flag required")
    need(report["qualified_object_mip_count"] is None, "observed metadata cannot qualify a mip count")
    for key, value in (("arm_generation", 1), ("callback_limit", 65536),
                       ("target_case_limit_per_phase", 16), ("read_limit", 2097152), ("payload_bytes_read", 0)):
        need(uint(report[key]) == value, "exact observation scope and zero payload required")
    need(report["exact_argv_validated_before_arm"], "original exact argv must precede arm")
    callbacks = uint(report["image_callbacks"], 65537)
    nonmatches = uint(report["non_target_callbacks"], 65536)
    uint(report["read_bytes"], 2097152)
    references = uint(report["reference_events"], 34)
    ordinary = uint(report["ordinary_name_events"], 34)
    need(report["reference_name_observed"] is (references != 0) and
         report["ordinary_name_observed"] is (ordinary != 0), "name presence contradicts event counts")
    need(not report["map_complete"] or report["bootstrap_complete"], "map completion requires original bootstrap")
    need(report["window_complete"] is (not report["refused"]) and
         (report["refused"] or report["map_complete"]), "refusal/window/map completion contradict")
    need(not report["cap_refused"] or report["refused"], "cap cannot qualify a complete window")
    if report["refused"]:
        reason(report["reason"], 191)
    else:
        need(report["reason"] is None, "successful window cannot carry a refusal reason")
    if ordinary:
        need(report["ordinary_absence_scope"] is None, "observed name cannot claim absence")
    else:
        need(report["ordinary_absence_scope"] in
             ("partial_or_refused_callback_window", "not_observed_in_this_bounded_callback_window"),
             "absence must stay scoped to the bounded callback window")
        if report["window_complete"]:
            need(report["ordinary_absence_scope"] == "not_observed_in_this_bounded_callback_window",
                 "complete window absence scope differs")
    rows = report["cases"]
    need(type(rows) is list and len(rows) == 4, "four fixed observation slots required")
    counts, ordinals, summaries = [], [], []
    for row, (phase, category) in zip(rows, ORDER):
        exact(row, CASE)
        need((row["phase"], row["name_category"]) == (phase, category), "fixed slot order differs")
        count = uint(row["matching_events_in_phase"], 17)
        counts.append(count)
        for key in ("descriptor_admissible", "repeated_headers_compared", "conflict_absence_proven"):
            need(row[key] is False, "a first sample cannot qualify a descriptor or compare repeats")
        need(type(row["single_event_observed_in_phase"]) is bool and
             row["single_event_observed_in_phase"] is (count == 1), "singleton event flag differs")
        observed, nonzero = False, None
        if row["raw_name"] is None:
            need(all(row[key] is None for key in
                     ("callback_ordinal", "effective_name", "leading_comma_reference", "snapshot")),
                 "missing sample must not synthesize callback or image values")
        else:
            need(count > 0 and row["raw_name"] == (("," if category == "reference" else "") + TARGET) and
                 row["effective_name"] == TARGET and row["leading_comma_reference"] is (category == "reference"),
                 "exact owned names and one-comma classification required")
            ordinal = uint(row["callback_ordinal"], callbacks)
            need(ordinal > 0, "observed callback ordinal required")
            ordinals.append((phase, ordinal))
            observed, nonzero = snapshot(row["snapshot"], row["raw_name"])
        state = ("not_observed" if not count else "target_matched_sample_refused" if not observed else
                 "repeated_target_ambiguous" if count > 1 else "first_complete_sample")
        need(row["state"] == state, "sample state contradicts count/copy observation")
        need(type(row["unique_in_phase"]) is bool and
             row["unique_in_phase"] is (not report["refused"] and observed and count == 1),
             "uniqueness requires a complete original window and one observed event")
        need(row["nonzero_descriptor_scalar_fields"] is None if nonzero is None else
             type(row["nonzero_descriptor_scalar_fields"]) is int and row["nonzero_descriptor_scalar_fields"] == nonzero,
             "nonzero scalar summary differs from the owned DTO")
        need(count != 0 or row["raw_name"] is None, "absent slot contains a fabricated sample")
        need(not count or observed or report["refused"], "failed matching sample cannot qualify a complete window")
        summaries.append({key: row[key] for key in
                          ("phase", "name_category", "state", "raw_name", "effective_name",
                           "matching_events_in_phase", "unique_in_phase", "nonzero_descriptor_scalar_fields")})
        summaries[-1]["image"] = row["snapshot"]["image"] if observed else None
    need(references == counts[0] + counts[2] and ordinary == counts[1] + counts[3], "event totals differ from slots")
    accounted = nonmatches + references + ordinary
    need(accounted <= callbacks <= accounted + 1 and (report["refused"] or accounted == callbacks),
         "callback accounting differs")
    need(callbacks <= 65536 or accounted == 65536, "over-limit callback is an unprobed trigger")
    need(report["bootstrap_complete"] or not any(counts[2:]), "map samples require the original phase transition")
    need(not (callbacks > 65536 or any(count > 16 for count in counts)) or report["cap_refused"],
         "over-limit trigger requires cap refusal")
    need(len({value for _, value in ordinals}) == len(ordinals), "sample callback ordinals must be distinct")
    bootstrap = [value for phase, value in ordinals if phase == "bootstrap"]
    mapping = [value for phase, value in ordinals if phase == "map_load"]
    need(not bootstrap or not mapping or max(bootstrap) < min(mapping), "callback phase order differs")
    return {"schema": "iw7.t7-incoming-image-consumer/1", "observation_status": "refused" if report["refused"] else "complete",
            "window_complete": report["window_complete"], "cases": summaries, "metadata_only": True,
            "descriptor_admissible": False, "qualified_object_mip_count": None,
            "source_asset_name_association_proven": False, "model_binding_correlated": False,
            "renderer_binding_proven": False, "same_object_proven": False, "runtime_abi_proven": False,
            "pixels_copied": False, "ready": False}


def classify(report, native_exit_code):
    need(type(native_exit_code) is int and -(2**31) <= native_exit_code <= 2**32-1,
         "original native exit required")
    if report is None:
        return {"outcome": "NoReport", "native_exit_code": native_exit_code, "ready": False}
    result = consume(report)
    if result["observation_status"] == "refused":
        need(native_exit_code != 0, "refused observation contradicts successful native exit")
        result["outcome"] = "IncomingMetadataRefused"
    else:
        result["outcome"] = "IncomingMetadataObserved" if native_exit_code == 0 else "ValidIncomingMetadataFromFailedProcess"
    result["native_exit_code"] = native_exit_code
    return result


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

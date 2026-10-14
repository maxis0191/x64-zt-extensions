"""Read only the existing two-epoch JSON; never capture, dereference or admit IO."""
import argparse
import hashlib
import json
from pathlib import Path
import re

LIMIT = 32768
MAX64 = 2**64 - 1
MODEL = "p7_fre_platform_cap_02"
HASH = 2695565377
BOOLS = "capture_complete refused duplicate_registration registration_search_refused association_complete same_object_proven lifetime_proven allocation_retained pixels_copied image_header_read image_body_admitted g3_image_header_admission_changed registration_path_changed ready".split()
FALSES = BOOLS[5:]
ZEROES = "image_body_bytes_read payload_bytes_read".split()
TOP = set(BOOLS + ZEROES + "schema model lod slot binding_index binding_name_hash model_callbacks matched_registrations registration lookup header_changed same_numeric_image_field".split())
EBOOLS = "binding_observed binding_rechecked query_complete range_readable_at_query query_failed range_overflow region_limit_refused atomic_snapshot_proven".split()
POINTERS = "incoming_model_header_hex selected_model_header_hex material_hex texture_table_hex image_field_hex".split()
EPOCH = set(EBOOLS + POINTERS + "phase ordinal thread_id tick_milliseconds lod slot binding_index expected_binding_name_hash texture_count failure queried_span_bytes regions image_body_bytes_read".split())
REGION = {"base_hex", "allocation_base_hex", "region_extent", "state_raw", "protect_raw", "type_raw"}


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def integer(value, maximum=MAX64):
    need(type(value) is int and 0 <= value <= maximum, "bounded integer required")
    return value


def address(value):
    need(type(value) is str and re.fullmatch("[0-9a-f]{16}", value), "exact scalar hexadecimal metadata required")
    return int(value, 16)  # Arithmetic on recorded metadata only, never a pointer cast.


def strict_json(raw):
    need(type(raw) is bytes and 0 < len(raw) <= LIMIT, "bounded JSON report required")
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "duplicate JSON field")
            result[key] = value
        return result
    def constant(_):
        raise ValueError("nonfinite JSON number")
    return json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=pairs, parse_constant=constant)


def epoch(value, phase):
    need(type(value) is dict and set(value) == EPOCH, "exact epoch fields required")
    need(value["phase"] == phase, "epoch order differs")
    for name in EBOOLS:
        need(type(value[name]) is bool, "typed epoch flag required")
    for name, maximum in (("ordinal", MAX64), ("thread_id", 2**32-1), ("tick_milliseconds", MAX64)):
        integer(value[name], maximum)
    for name, expected in (("lod", 0), ("slot", 0), ("binding_index", 4), ("expected_binding_name_hash", HASH), ("queried_span_bytes", 264), ("image_body_bytes_read", 0)):
        need(integer(value[name]) == expected, "exact epoch selection/span required")
    need(value["atomic_snapshot_proven"] is False, "metadata cannot prove an atomic snapshot")
    need(type(value["failure"]) is str and len(value["failure"].encode("utf-8")) <= 1024, "bounded failure text required")
    for name in POINTERS:
        expected = value["ordinal"] > 0 if name == "selected_model_header_hex" else value["binding_observed"]
        if name == "incoming_model_header_hex":
            expected = value["ordinal"] > 0 and phase == "after_original_model_add"
        need((value[name] is not None) == expected, "epoch pointer nullability differs")
        if expected:
            address(value[name])
    if value["binding_observed"]:
        need(5 <= integer(value["texture_count"], 16), "selected binding count differs")
        need(all(address(value[name]) != 0 for name in POINTERS[1:4]), "observed association requires nonzero model/material/table")
    else:
        need(value["texture_count"] is None, "unobserved binding has a count")
    need(not value["binding_rechecked"] or (value["binding_observed"] and not value["failure"]), "rechecked binding contradicts refusal")
    rows = value["regions"]
    need(type(rows) is list and len(rows) <= 2, "bounded region list required")
    readable = True
    cursor = address(value["image_field_hex"]) if value["binding_observed"] else 0
    end = cursor + 264
    covered = cursor > 0 and end <= MAX64
    for row in rows:
        need(type(row) is dict and set(row) == REGION, "exact region metadata required")
        base = address(row["base_hex"]); address(row["allocation_base_hex"])
        extent = integer(row["region_extent"])
        state, protect, _ = (integer(row[name], 2**32-1) for name in ("state_raw", "protect_raw", "type_raw"))
        covered = covered and cursor < end and base <= cursor and extent > 0 and base + extent <= MAX64 and base + extent > cursor
        cursor = min(end, base + extent)
        readable = readable and state == 0x1000 and not (protect & 0x100) and (protect & 0xff) in {2, 4, 8, 32, 64, 128}
    query_valid = covered and bool(rows) and cursor == end and not any(value[name] for name in ("query_failed", "range_overflow", "region_limit_refused"))
    if value["query_complete"] and value["binding_rechecked"]:
        need(query_valid, "complete rechecked query has inconsistent coverage")
        need(value["range_readable_at_query"] == readable, "readable claim differs from region metadata")
    need(not value["range_readable_at_query"] or value["query_complete"], "incomplete query cannot claim readability")
    return {"phase": phase, "binding_rechecked": value["binding_rechecked"], "query_complete": value["query_complete"],
            "range_readable_at_query": value["range_readable_at_query"], "failure": value["failure"],
            "query_failed": value["query_failed"], "range_overflow": value["range_overflow"], "region_limit_refused": value["region_limit_refused"]}


def consume(report):
    need(type(report) is dict and set(report) == TOP, "exact producer report fields required")
    need(report["schema"] == "iw7.t7-selected-image-provenance/1" and report["model"] == MODEL, "producer/model differs")
    for name in BOOLS:
        need(type(report[name]) is bool, "typed producer flag required")
    need(all(report[name] is False for name in FALSES), "metadata report attempts to promote runtime/body proof")
    for name in ZEROES:
        need(integer(report[name]) == 0, "body/payload bytes forbidden")
    for name, expected in (("lod", 0), ("slot", 0), ("binding_index", 4), ("binding_name_hash", HASH)):
        need(integer(report[name]) == expected, "exact producer selection required")
    callbacks = integer(report["model_callbacks"], 2**32-1)
    matches = integer(report["matched_registrations"], 1024)
    need(matches <= callbacks, "registration counters contradict")
    need(report["duplicate_registration"] == (matches > 1), "duplicate registration counter differs")
    need(callbacks <= 1024 or report["registration_search_refused"], "search limit lacks its refusal")
    summaries = [epoch(report["registration"], "after_original_model_add"), epoch(report["lookup"], "after_zone_model_lookup")]
    associated = all(item["binding_rechecked"] for item in summaries)
    need(report["association_complete"] == associated, "association claim differs")
    expected_complete = matches == 1 and not report["duplicate_registration"] and not report["registration_search_refused"] and associated and all(item["query_complete"] for item in summaries)
    need(report["capture_complete"] == expected_complete and report["refused"] == (not expected_complete), "capture/refusal claim differs")
    registration, lookup = report["registration"], report["lookup"]
    need(registration["ordinal"] == (1 if matches else 0) and lookup["ordinal"] == registration["ordinal"] + 1, "capture ordinal order differs")
    if associated:
        need(type(report["header_changed"]) is bool and type(report["same_numeric_image_field"]) is bool, "associated comparisons require booleans")
        need(report["header_changed"] == (registration["selected_model_header_hex"] != lookup["selected_model_header_hex"]), "header comparison differs")
        need(report["same_numeric_image_field"] == (registration["image_field_hex"] == lookup["image_field_hex"]), "numeric image comparison differs")
    else:
        need(report["header_changed"] is None and report["same_numeric_image_field"] is None, "unassociated comparisons must stay null")
    comparisons = {"header_changed": report["header_changed"], "same_numeric_image_field": report["same_numeric_image_field"],
                   "incoming_equals_returned": None, "material_changed": None, "texture_table_changed": None}
    if registration["ordinal"]:
        comparisons["incoming_equals_returned"] = registration["incoming_model_header_hex"] == registration["selected_model_header_hex"]
    if associated:
        for field, name in (("material_hex", "material_changed"), ("texture_table_hex", "texture_table_changed")):
            comparisons[name] = registration[field] != lookup[field]
    refusals = []
    if matches == 0:
        refusals.append("no_selected_registration")
    for name in ("duplicate_registration", "registration_search_refused"):
        if report[name]:
            refusals.append(name)
    for name, item in zip(("registration", "lookup"), summaries):
        if not item["binding_rechecked"]:
            refusals.append(name + "_association_not_rechecked")
        if not item["query_complete"]:
            refusals.append(name + "_query_incomplete")
    return {"schema": "iw7.t7-image-metadata-consumer/1", "model": MODEL, "observation_status": "complete" if expected_complete else "refused",
            "refusal_reasons": refusals,
            "epochs": summaries, "comparisons": comparisons, "reference_only": True,
            "image_header_admitted": False, "extraction_authorized": False, "pointer_transform_authorized": False,
            "same_object_proven": False, "lifetime_proven": False, "authentic_bo3_texture_proven": False, "ready": False}


def classify(report, exit_code):
    """Interpret a closed record and the original exit; never turn failure into success."""
    need(type(exit_code) is int and -(2**31) <= exit_code <= 2**32-1, "native exit code required")
    if report is None:
        return {"outcome": "NoReport", "native_exit_code": exit_code, "ready": False}
    result = consume(report)
    if result["observation_status"] == "refused":
        need(exit_code != 0, "refused capture contradicts successful native exit")
        result["outcome"] = "ProvenanceMetadataRefused"
    else:
        result["outcome"] = "ProvenanceMetadataObserved" if exit_code == 0 else "ValidMetadataFromFailedProcess"
    result["native_exit_code"] = exit_code
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Existing producer JSON; missing report is an error, never fabricated")
    parser.add_argument("--native-exit-code", type=int, help="Original closed process exit; omitted means metadata validation only")
    args = parser.parse_args()
    with args.report.open("rb") as stream:
        raw = stream.read(LIMIT + 1)
    report = strict_json(raw)
    need(type(report) is dict, "existing producer record must be a JSON object")
    result = consume(report) if args.native_exit_code is None else classify(report, args.native_exit_code)
    result["source_report_sha256"] = hashlib.sha256(raw).hexdigest()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

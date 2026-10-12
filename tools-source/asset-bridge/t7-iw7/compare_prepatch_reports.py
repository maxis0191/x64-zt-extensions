"""Compare saved T7 JSON observations only; never open a PE or a process."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import ntpath
from pathlib import Path
import re
import struct

from inspect_t7_executable import BASE, SOURCE, SITES, expectation, require

NAMES = (
    "DB_FindXAssetHeader", "DB_LoadXAssets", "SL_ConvertToString", "boot_call",
    "server_thread_ret", "copy_info_branch_1", "copy_info_branch_2",
    "image_loader_call", "integrity_intact_1", "integrity_intact_2",
    "integrity_intact_3", "integrity_split",
)
SELECTED = [s for s in SITES if s[0] in NAMES]
FALSE_FLAGS = ("abi_proven", "runtime_compatibility_proven", "boot_authorized")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def read_json(path, limit, expected_hash=None):
    require(path.suffix.lower() == ".json", "only saved JSON inputs are accepted")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    require(0 < len(data) <= limit, "JSON size limit exceeded or empty input")
    digest = hashlib.sha256(data).hexdigest()
    if expected_hash is not None:
        require(re.fullmatch(r"[0-9a-fA-F]{64}", expected_hash) is not None,
                "invalid expected JSON SHA256")
        require(digest == expected_hash.lower(), "JSON SHA256 differs")
    result = json.loads(data.decode("utf-8-sig"), object_pairs_hook=unique_object,
                        parse_constant=lambda _: require(False, "non-finite JSON number"))
    require(isinstance(result, dict), "JSON object required")
    return result, {"sha256": digest, "bytes": len(data)}


def number(value, maximum=0xFFFFFFFFFFFFFFFF):
    if isinstance(value, str) and re.fullmatch(r"0x[0-9a-fA-F]+", value):
        value = int(value, 16)
    require(type(value) is int and 0 <= value <= maximum, "invalid bounded integer")
    return value


def window_data(row, site):
    name, rva, before, length, _ = site
    require(row["site"] == name and row["rva"] == rva and
            row["window_rva"] == rva - before and row["window_bytes"] == length,
            "fixed window differs: " + name)
    value = row["bytes_hex"]
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{%d}" % (2 * length), value),
            "window bytes malformed: " + name)
    return bytes.fromhex(value)


def section_at(pe, rva):
    sections = pe["sections"]
    require(isinstance(sections, list) and 1 <= len(sections) <= 96, "invalid sections")
    found = []
    for row in sections:
        start = number(row["rva"], 0xFFFFFFFF)
        size = max(number(row["virtual_size"], 0xFFFFFFFF), number(row["raw_size"], 0xFFFFFFFF))
        if start <= rva < start + size:
            found.append(row)
    require(len(found) == 1, "site section missing or ambiguous")
    row = found[0]
    flags = number(row["characteristics"], 0xFFFFFFFF)
    return {"name": row["name"], "characteristics": hex(flags),
            "executable": bool(flags & 0x20000000)}


def memory_at(row, base):
    """Validate saved VirtualQuery coverage, not the current state of any page."""
    start = base + row["window_rva"]
    end = start + row["window_bytes"]
    site = base + row["rva"]
    cursor, spans, site_exec = start, [], None
    require(0 < len(row["regions"]) <= 128, "invalid region count")
    previous_end = None
    for item in row["regions"]:
        begin, size = number(item["base"]), number(item["size"])
        require(size > 0 and begin + size <= 0xFFFFFFFFFFFFFFFF and begin <= cursor < begin + size,
                "region gap or invalid extent")
        require(cursor < end and (previous_end is None or begin == previous_end),
                "overlapping or extra region")
        require(number(item["allocation_base"]) == base and item["type"] == 0x1000000,
                "region ownership or MEM_IMAGE differs")
        protection = number(item["protect"], 0xFFFFFFFF)
        require(item["state"] == 0x1000 and not protection & 0x101,
                "uncommitted, guarded or inaccessible saved region")
        executable = (protection & 0xFF) in (0x10, 0x20, 0x40, 0x80)
        if begin <= site < begin + size:
            site_exec = executable
        spans.append({"base": hex(begin), "size": size, "protect": hex(protection),
                      "executable": executable})
        previous_end = begin + size
        cursor = min(end, previous_end)
    require(cursor == end and site_exec is not None, "incomplete region coverage")
    return {"site_executable": site_exec, "whole_window_executable": all(s["executable"] for s in spans),
            "regions": spans, "observation_is_atomic": False}


def source_pattern(kind, data, rva, base):
    failures, details = expectation(kind, data, rva)
    result = {"kind": kind, "specified": kind != "entry", "conflicts": failures}
    if "direct_call_target" in details:
        result["source_base_relative_target"] = details["direct_call_target"]
        result["actual_mapped_call_target"] = hex(base + rva + 5 + struct.unpack_from("<i", data, 1)[0])
        result["expected_absolute_target"] = details["expected_target_from_source"]
    return result


def anchor_at(row, image_size):
    fn = row.get("runtime_function")
    if fn is None:
        return {"present": False, "instruction_boundary_proven": False}
    begin, end, unwind = (number(fn[k], 0xFFFFFFFF) for k in ("begin_rva", "end_rva", "unwind_rva"))
    require(begin <= row["rva"] < end <= image_size and 0 < unwind <= image_size - 4,
            "runtime-function range differs")
    require(fn["unwind_format_validated"] is False and
            re.fullmatch(r"[0-9a-fA-F]{8}", fn["unwind_header_hex"]), "unwind observation differs")
    head = bytes.fromhex(fn["unwind_header_hex"])
    return {"present": True, "begin_rva": begin, "end_rva": end, "unwind_rva": unwind,
            "header_version_bits": head[0] & 7, "header_flags_bits": head[0] >> 3,
            "unwind_bytes_observed": 4, "unwind_format_validated": False,
            "begin_available_in_window": row["window_rva"] <= begin <= row["rva"],
            "instruction_boundary_proven": False,
            "limit": "Range containment only; no full unwind parse, forward decode or calling-convention proof."}


def decode_anchor(row, data, base, decoder):
    fn = row.get("runtime_function")
    if not fn or not row["window_rva"] <= fn["begin_rva"] <= row["rva"]:
        return {"available": False, "reason": "no pdata begin inside captured window"}
    if decoder is None:
        return {"available": False, "reason": "decoder not requested"}
    start = fn["begin_rva"]
    code = data[start - row["window_rva"]:]
    instructions = list(decoder.disasm(code, base + start))
    boundaries = {i.address for i in instructions}
    targets = [row["rva"]]
    if row["site"] == "DB_LoadXAssets":
        targets += [0x1D87AE, 0x1D87B3]
    checks = {hex(base + rva): ("decoded_boundary" if base + rva in boundaries else
              "inside_instruction" if any(i.address < base + rva < i.address + i.size for i in instructions) else
              "not_reached") for rva in targets}
    return {"available": True, "start_rva": start, "bytes_submitted": len(code),
            "instruction_count": len(instructions), "checks": checks,
            "limit": "Forward decode conditional on saved pdata begin; no complete unwind or ABI validation."}


def compare(static, capture, decoder=None):
    require(static["schema"] == "iw7.t7-static-executable-inspection/1" and
            static["source_commit"] == SOURCE, "static schema or source pin differs")
    require(capture["schema"] == "iw7.t7-prepatch-memory-observation/1" and
            capture["phase"] == "first_dpi_before_component_post_unpack", "capture phase or schema differs")
    require(all(capture[k] is False for k in FALSE_FLAGS), "capture overclaims compatibility")
    require(type(capture["capture_complete"]) is bool and capture["source_base"] == hex(BASE) and
            capture["read_limit"] == 4194304 and capture["report_limit"] == 262144 and
            capture["window_count"] == 12, "capture contract differs")
    require(len(static["windows"]) == len(SITES), "static window count differs")
    for row, site in zip(static["windows"], SITES):
        require(row["site"] == site[0], "static sites/order differ")
    disk = {r["site"]: r for r in static["windows"]}
    rows = capture["windows"]
    require(len(rows) <= 12 and capture["window_observations"] == len(rows), "capture row count differs")
    requested = number(capture["requested_bytes"], 4194304)
    returned = number(capture["returned_bytes"], requested)
    complete = capture["capture_complete"]
    require(capture["status"] == ("captured_for_offline_review" if complete else "incomplete_stop"),
            "capture status differs")
    if complete:
        require(len(rows) == 12 and requested > 0 and returned == requested and
                not any(k in capture for k in ("capture_error", "metadata_error")), "complete capture is inconsistent")
    result = {"schema": "iw7.t7-prepatch-comparison/1", "source_commit": SOURCE,
              "capture_claims_complete": complete, "runner_qualified_capture": False,
              "report_links_match": False, "windows": [], "runtime_conflicts": [],
              "static_baseline": {"windows": len(SITES), "conflicts": static["conflicts"],
                  "indeterminate": static["indeterminate"],
                  "unknown_categories": dict(Counter(s.split(": ", 1)[-1] for s in static["indeterminate"])),
                  "sites_outside_capture": [s[0] for s in SITES if s[0] not in NAMES],
                  "unknowns_cleared_by_this_comparison": 0},
              "input_binary_hashes_recomputed": False, **dict.fromkeys(FALSE_FLAGS, False)}
    if not rows:
        return result
    base = number(capture["module_base"])
    require(capture["base_matches_source"] is (base == BASE), "module base assertion differs")
    if base != BASE:
        result["runtime_conflicts"].append("mapped base differs from source absolute addresses")
    image_size = number(capture["pe"]["size_of_image"], 1024 * 1024 * 1024)
    require(image_size >= 4096 and base + image_size <= 0xFFFFFFFFFFFFFFFF, "mapped image extent differs")
    result["pe_changes"] = {key: {"disk": static["pe"][key], "mapped": capture["pe"][key]}
                            for key in ("size_of_image", "timestamp", "entrypoint_rva", "dll_characteristics")
                            if static["pe"][key] != capture["pe"][key]}
    result["pdata_record_counts"] = {"disk": static["pe"]["pdata_records"], "mapped": capture["pdata_records"]}
    for row, site in zip(rows, SELECTED):
        name, rva, before, length, kind = site
        require(row["site"] == name, "capture sites/order differ")
        if "error" in row:
            require(not complete, "complete capture has a window error")
            result["windows"].append({"site": name, "observation_incomplete": True})
            continue
        old, new = window_data(disk[name], site), window_data(row, site)
        require(rva - before + length <= image_size, "window exceeds mapped image")
        require(hashlib.sha256(old).hexdigest() == disk[name]["sha256"], "static window digest differs")
        saved_memory = memory_at(row, base)
        pattern = source_pattern(kind, new[before:], rva, base)
        anchor = anchor_at(row, image_size)
        decoded = decode_anchor(row, new, base, decoder)
        result["runtime_conflicts"].extend(name + ": " + s for s in pattern["conflicts"])
        result["runtime_conflicts"].extend(name + ": " + address + " inside instruction from saved pdata begin"
            for address, status in decoded.get("checks", {}).items() if status == "inside_instruction")
        if not saved_memory["site_executable"]:
            result["runtime_conflicts"].append(name + ": observed site page is not executable")
        result["windows"].append({"site": name, "source_va": hex(BASE + rva), "mapped_va": hex(base + rva),
            "rva": rva, "bytes_compared": length,
            "changed_bytes": sum(a != b for a, b in zip(old, new)),
            "disk_sha256": hashlib.sha256(old).hexdigest(), "mapped_sha256": hashlib.sha256(new).hexdigest(),
            "disk_section": section_at(static["pe"], rva), "mapped_section": section_at(capture["pe"], rva),
            "memory": saved_memory, "disk_pattern": source_pattern(kind, old[before:], rva, BASE),
            "mapped_pattern": pattern, "pdata": anchor, "bounded_decode": decoded})
    return result


def filetime_utc(value):
    require(isinstance(value, str) and re.fullmatch(r"[0-9]{1,19}", value), "invalid creation FILETIME")
    ticks = int(value) - 116444736000000000
    seconds, fraction = divmod(ticks, 10000000)
    return datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + f".{fraction:07d}Z"


def correlate(static, capture, receipt, plan, capture_pin, plan_pin):
    """Link saved metadata; the existing runner owns qualification and binary pin checks."""
    require(receipt["Schema"] == "iw7.t7-prepatch-run/1" and plan["Schema"] == "iw7.t7-prepatch-plan/1",
            "receipt or plan schema differs")
    require(receipt["PlanSHA256"].lower() == plan_pin["sha256"] and
            receipt["Report"]["SHA256"].lower() == capture_pin["sha256"] and
            receipt["Report"]["Bytes"] == capture_pin["bytes"], "report/receipt/plan hashes differ")
    identity = receipt["Identity"]
    require(type(capture["pid"]) is int and capture["pid"] > 0 and capture["pid"] == identity["PID"] and
            filetime_utc(capture["creation_filetime"]) == identity["CreatedUtc"], "process generation differs")
    normal = lambda p: ntpath.normcase(ntpath.normpath(p))
    alias = ntpath.join(plan["WorkingDirectory"], "BlackOps3_UnrankedDedicatedServer.exe")
    require(normal(capture["module_path"]) == normal(alias) and normal(identity["Image"]) == normal(plan["Image"]),
            "module or runner image identity differs")
    digest = static["identity"]["acquisition_sha256_unverified"]
    require(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest), "static acquisition pin missing")
    require(len(plan["Bindings"]) <= 32, "binding count exceeds runner contract")
    for path in (plan["EngineSource"], alias):
        matches = [p for p in plan["Bindings"] if normal(p["Path"]) == normal(path)]
        require(len(matches) == 1 and matches[0]["SHA256"] == digest and
                matches[0]["Bytes"] == static["identity"]["file_bytes"], "engine pin differs from static acquisition label")
    require(receipt["CompatibilityProven"] is False and receipt["Ready"] is False, "receipt overclaims readiness")
    qualified = (capture["capture_complete"] and receipt["Status"] == "CaptureCompletePendingReview" and
                 receipt["CaptureOutcome"] == "CaptureComplete" and type(receipt["ExitCode"]) is int and
                 receipt["ExitCode"] == 0 and all(receipt[k] is True for k in
                    ("TreeClosureConfirmed", "LeaseReleased", "InputsReverified", "OriginalInputMetadataUnchanged")) and
                 all(receipt[k] is False for k in ("Quarantined", "TerminationRequested")))
    return {"report_links_match": True, "runner_qualified_capture": bool(qualified),
            "acquisition_sha256_label": digest,
            "provenance_limit": "Saved JSON links only; runner supplies binary verification and closure evidence."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("static", type=Path)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--static-sha256", required=True)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--receipt-sha256")
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--plan-sha256")
    parser.add_argument("--decode-anchors", action="store_true", help="optional Capstone on saved anchored windows only")
    parser.add_argument("--output", type=Path, help="new sanitized JSON; no byte windows or disassembly")
    args = parser.parse_args()
    try:
        static, static_pin = read_json(args.static, 1048576, args.static_sha256)
        capture, capture_pin = read_json(args.capture, 262144)
        decoder = None
        if args.decode_anchors:
            import capstone
            decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
        report = compare(static, capture, decoder)
        report["decoder_version"] = capstone.__version__ if args.decode_anchors else None
        report["inputs"] = {"static": static_pin, "capture": capture_pin}
        options = (args.receipt, args.receipt_sha256, args.plan, args.plan_sha256)
        require(not any(options) or all(options), "receipt, plan and both expected hashes are required together")
        if all(options):
            receipt, receipt_pin = read_json(args.receipt, 1048576, args.receipt_sha256)
            plan, plan_pin = read_json(args.plan, 1048576, args.plan_sha256)
            report.update(correlate(static, capture, receipt, plan, capture_pin, plan_pin))
            report["inputs"].update(receipt=receipt_pin, plan=plan_pin)
        report["next_step"] = ("review_observed_conflicts_before_any_catalogue_plan" if report["runtime_conflicts"] else
                               "prepare_separately_reviewed_single_zone_catalogue_plan")
        if not report["runner_qualified_capture"]:
            report["next_step"] = "obtain_or_review_qualified_capture_evidence_no_catalogue"
        text = json.dumps(report, indent=2) + "\n"
        if args.output:
            require(args.output.suffix.lower() == ".json", "JSON output required")
            with args.output.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
        else:
            print(text, end="")
        return 0  # A comparison was emitted, never an ABI approval.
    except (OSError, ValueError, KeyError, TypeError, OverflowError, RecursionError, ImportError) as exc:
        print(json.dumps({"comparison_failed": True, "error": str(exc), **dict.fromkeys(FALSE_FLAGS, False)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

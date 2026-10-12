"""Generate stopped CDB fragments or parse one bounded offline write witness.

This program never launches, attaches, resumes, kills or reads a process. The
review context is an external attestation, not a replacement for its evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re


TOOL_SHA = "e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04"
FF_SHA = "ea7ba4be1d5e6f0878431b51e7b9b1ba9d2b10bf74b1ad21da14d55c414e145d"
SCHEMA = "iw7.rig-abi.watch-context/1"
MAX_LOG = 256 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def bounded(path, limit):
    with open(path, "rb") as stream:
        data = stream.read(limit + 1)
    require(len(data) <= limit, "input exceeds size limit")
    return data


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def load_context(path):
    return json.loads(bounded(path, 32768), object_pairs_hook=unique_pairs)


def address(value):
    require(isinstance(value, str) and re.fullmatch(r"0x[0-9a-fA-F]{1,16}", value),
            "address must be a literal hex value, not a debugger expression")
    number = int(value, 16)
    require(0x10000 <= number <= 0x7FFFFFFEFFFF, "address outside bounded user range")
    return number


def validate(context):
    require(isinstance(context, dict) and context.get("schema") == SCHEMA, "wrong context schema")
    require(context.get("profile") in ("first", "second"), "unknown original rig profile")
    require(isinstance(context.get("run_id"), str) and re.fullmatch(r"[0-9a-f]{32}", context["run_id"]),
            "run_id must be 32 lowercase hex digits")
    require(context.get("tool_sha256") == TOOL_SHA and context.get("ff_sha256") == FF_SHA,
            "original rig/tool pins do not match")
    pid = context.get("pid")
    require(type(pid) is int and 0 < pid <= 0xFFFFFFFF, "positive process ID required")
    require(isinstance(context.get("image_path"), str) and
            PureWindowsPath(context["image_path"]).is_absolute() and
            PureWindowsPath(context["image_path"]).name.lower() == "zonetool.exe", "offline image path required")
    require(isinstance(context.get("creation_utc"), str) and
            re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,7})?Z", context["creation_utc"]),
            "process creation identity required")
    review = context.get("review")
    require(isinstance(review, dict) and review.get("phase") == "after-initial-copy-before-postload",
            "reviewed loader arm point is missing")
    require(isinstance(review.get("evidence_sha256"), str) and
            re.fullmatch(r"[0-9a-f]{64}", review["evidence_sha256"]) and
            review["evidence_sha256"] != "0" * 64, "review evidence hash required")
    for key in ("mapping_verified", "stopped_identity_verified", "launch_job_owned",
                "breakpoint_table_empty", "all_threads_stopped", "deadline_armed"):
        require(review.get(key) is True, f"review gate unresolved: {key}")
    require(isinstance(review.get("admission_lease_id"), str) and
            re.fullmatch(r"[a-zA-Z0-9_-]{8,128}", review["admission_lease_id"]), "admission receipt required")
    xs, ms, rip = (address(context.get(key)) for key in ("xsurface", "xmodelsurfs", "arm_rip"))
    require(xs % 8 == 0 and ms % 8 == 0, "surface records must be 8-byte aligned")
    require(xs + 256 <= ms or ms + 56 <= xs, "surface records overlap")
    code = context.get("arm_code_hex")
    require(isinstance(code, str) and re.fullmatch(r"(?:[0-9a-f]{2}){8,32}", code),
            "8..32 reviewed arm instruction bytes required")
    return xs, ms, rip, bytes.fromhex(code)


def same_bytes(base, data):
    """Bounded integer reads, no arbitrary strings or unbounded C-string walk."""
    checks, index = [], 0
    for width, operator in ((8, "qwo"), (4, "dwo"), (2, "wo"), (1, "by")):
        while len(data) - index >= width:
            expected = int.from_bytes(data[index:index + width], "little")
            checks.append(f"({operator}({base}+0x{index:x}) == 0x{expected:x})")
            index += width
    return " && ".join(checks)


def guard(condition, body, refusal):
    return f".if ({condition}) {{ {body} }} .else {{ .echo RIG58_REFUSED_{refusal} }}"


def emit(context):
    xs, ms, rip, code = validate(context)
    nonce, pid = context["run_id"], context["pid"]
    name = ("paris_doom_skin_two_bone_" + context["profile"] + "_a_lod0").encode() + b"\0"
    prefix = f"RIG58 {nonce} "
    # t0..t3 and breakpoint ID 3 are owned exclusively by this fresh session.
    hit = (f'.printf "{prefix}WRITE pid=%I64x tid=%I64x rip=%I64x xs=%I64x ms=%I64x '
           'old=%I64x new=%I64x name_before=%I64x name_now=%I64x\\n", '
           '@$tpid, @$tid, @rip, @$t0, @$t1, @$t2, poi(@$t0+0x58), @$t3, poi(@$t1); '
           f'.echo {prefix}STACK_BEGIN; kv 6; .echo {prefix}STACK_END; '
           f'.echo {prefix}STOP')
    hit = guard(same_bytes("poi(@$t1)", name), hit, "NAME_CHANGED")
    hit = guard(f"$vvalid(poi(@$t1),0x{len(name):x})", hit, "NAME_UNREADABLE")
    hit = guard("poi(@$t1+8) == @$t0 && wo(@$t1+0x10) == 1", hit, "RECORD_CHANGED")
    hit = guard("$vvalid(@$t0,0x100) && $vvalid(@$t1,0x38)", hit, "RECORD_UNREADABLE")
    hit = guard(f"@$tpid == 0x{pid:x}", hit, "PID")
    # Two parsers: the outer breakpoint string must preserve the inner printf
    # escape. Escape backslashes first, then quotes (C-style command string).
    quoted_hit = hit.replace("\\", "\\\\").replace('"', '\\"')
    body = (f"r $t0 = 0x{xs:x}; r $t1 = 0x{ms:x}; "
            f"r $t2 = poi(@$t0+0x58); r $t3 = poi(@$t1); "
            f'.printf "{prefix}ARM pid=%I64x tid=%I64x rip=%I64x xs=%I64x ms=%I64x '
            'old=%I64x name_before=%I64x\\n", '
            '@$tpid, @$tid, @rip, @$t0, @$t1, @$t2, @$t3; '
            f'ba3 w 8 /1 0x{xs+0x58:x} "{quoted_hit}"; bl 3; '
            f'.echo {prefix}ARM_ATTEMPT_STOPPED')
    body = guard(f"poi(0x{xs+0x58:x}) == 0 && poi(0x{xs+0x60:x}) == 0", body, "TOO_LATE_OR_NONZERO")
    body = guard(same_bytes(f"poi(0x{ms:x})", name), body, "NAME")
    body = guard(f"$vvalid(poi(0x{ms:x}),0x{len(name):x})", body, "NAME_UNREADABLE")
    body = guard(f"poi(0x{ms+8:x}) == 0x{xs:x} && wo(0x{ms+16:x}) == 1", body, "SHAPE")
    body = guard(same_bytes(f"0x{rip:x}", code), body, "CODE_BYTES")
    body = guard(f"$vvalid(0x{xs:x},0x100) && $vvalid(0x{ms:x},0x38) && "
                 f"$vvalid(0x{rip:x},0x{len(code):x})", body, "RANGE")
    body = guard(f"@$tpid == 0x{pid:x} && @rip == 0x{rip:x}", body, "IDENTITY_OR_STOP")
    # The MASM evaluator is explicit even if a previous session used C++.
    arm = ".expr /s masm\n" + body + "\n"
    require(len(body.encode("ascii")) < 4096, "generated command exceeds conservative line limit")
    clear = ".expr /s masm\n" + guard(
        f"@$tpid == 0x{pid:x} && @$t0 == 0x{xs:x} && @$t1 == 0x{ms:x}",
        f"bc 3; .echo {prefix}CLEARED_STOPPED", "CLEAR_IDENTITY") + "\n"
    canonical = json.dumps(context, sort_keys=True, separators=(",", ":")).encode()
    receipt = {"schema": "iw7.rig-abi.fragments/1", "run_id": nonce,
               "context_sha256": hashlib.sha256(canonical).hexdigest(),
               "max_write_hits": 1, "watch_bytes": 8, "stack_frames_requested": 6,
               "launches": 0, "auto_resume": False, "runtime_validated": False,
               "review_context_is_external_attestation": True}
    return {"arm.cdb": arm, "clear.cdb": clear,
            "fragments.local.json": json.dumps(receipt, indent=2) + "\n"}


def classify(value, name_before, name_now):
    if value == 0:
        return "zero"
    if value == name_now:
        return "equals_current_name_address"
    if value == name_before:
        return "equals_name_address_at_arm"
    return "other_nonzero_unclassified"


def parse_capture(context, raw):
    xs, ms, rip, _ = validate(context)
    require(isinstance(raw, bytes) and len(raw) <= MAX_LOG, "capture exceeds log bound")
    text = raw.decode("utf-8", "strict")
    nonce, events, stack, collecting = context["run_id"], [], [], False
    stack_seen = False
    records = {}
    for line in text.splitlines():
        line = line.strip()
        require(not line.startswith("RIG58_REFUSED_"), "capture contains a refused guard")
        # Only output records are valid. A CDB prompt echo is not an event.
        if line.startswith("RIG58 "):
            parts = line.split()
            require(len(parts) >= 3 and parts[1] == nonce, "foreign or malformed capture event")
            event = parts[2]
            require(not collecting or event == "STACK_END", "event interleaved into stack")
            events.append(event)
            if event in ("ARM", "WRITE"):
                fields = {}
                for entry in parts[3:]:
                    require(re.fullmatch(r"[a-z_]+=[0-9a-fA-F]{1,16}", entry), "malformed numeric field")
                    key, value = entry.split("=")
                    require(key not in fields, "duplicate capture field")
                    fields[key] = int(value, 16)
                records[event] = fields
            elif event == "STACK_BEGIN":
                collecting, stack_seen = True, True
            elif event == "STACK_END":
                require(collecting, "unopened stack block")
                collecting = False
            else:
                require(len(parts) == 3, "unexpected event arguments")
        elif collecting:
            stack.append(line)
            require(sum(len(item.encode("utf-8")) + 1 for item in stack) <= 8192, "stack text exceeds limit")
    require(events == ["ARM", "ARM_ATTEMPT_STOPPED", "WRITE", "STACK_BEGIN", "STACK_END", "STOP"],
            "incomplete, repeated or out-of-order one-write capture")
    require(stack_seen and not collecting and bool(stack), "missing stack output")
    arm, write = records["ARM"], records["WRITE"]
    require(set(arm) == {"pid", "tid", "rip", "xs", "ms", "old", "name_before"}, "wrong arm fields")
    require(set(write) == set(arm) | {"new", "name_now"}, "wrong write fields")
    for row in (arm, write):
        require(row["pid"] == context["pid"] and row["xs"] == xs and row["ms"] == ms,
                "capture process or allocation mismatch")
        require(row["tid"] > 0 and row["rip"] > 0 and row["name_before"] > 0, "missing identity values")
    require(arm["rip"] == rip and arm["old"] == write["old"] == 0 and
            arm["name_before"] == write["name_before"] and write["name_now"] > 0, "capture continuity mismatch")
    return {"schema": "iw7.rig-abi.write-witness/1", "run_id": nonce,
            "context_sha256": hashlib.sha256(json.dumps(context, sort_keys=True,
                                                        separators=(",", ":")).encode()).hexdigest(),
            "arm": arm, "write": write,
            "old_category": classify(write["old"], write["name_before"], write["name_now"]),
            "new_category": classify(write["new"], write["name_before"], write["name_now"]),
            "stack_text": stack, "stack_frames_verified": False,
            "trap_rip_is_not_resolved_store_instruction": True,
            "log_sha256": hashlib.sha256(raw).hexdigest(), "semantic_acceptance": False,
            "process_closure_verified": False, "complete_ff_verify": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("emit")
    generate.add_argument("--context", type=Path, required=True)
    generate.add_argument("--out", type=Path, required=True)
    report = commands.add_parser("report")
    report.add_argument("--context", type=Path, required=True)
    report.add_argument("--log", type=Path, required=True)
    args = parser.parse_args()
    try:
        context = load_context(args.context)
        if args.command == "emit":
            fragments = emit(context)  # Validate everything before writing.
            args.out.mkdir(parents=True, exist_ok=False)
            for name, text in fragments.items():
                (args.out / name).write_text(text, encoding="ascii", newline="\n")
            print(json.dumps({"output": str(args.out), "files": list(fragments), "native_go": False}))
        else:
            print(json.dumps(parse_capture(context, bounded(args.log, MAX_LOG)), indent=2))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f"refused: {exc}\n")


if __name__ == "__main__":
    main()

"""Closed FLAC-17 extension of the existing sound build; pure unless reading text."""
import copy
import ntpath
from pathlib import Path
import re

from build_contract import json_bytes, key, require, sha

SCHEMA = "iw7.sound-flac-dump-build-plan/1"
RECEIPT = "iw7.sound-flac-dump-build-receipt/1"
EXTRA_ORDER = ("probe-flac-compile", "probe-flac-link", "probe-flac-run")
REVIEW_SHA = "75ad217b9841856a7401785fef53b8281e3b80e26bf5525e37e8250ee2826ce9"
SOURCE_SHA = "46bc9e333cc9985ad3358e68a44adbc9b8469feabdbfe946aeb4eff8c1a068b5"
SOURCE_PINS = {
    "sound_bank.cpp": (113219, "8142eead0fe7cbdb6a0b17cc106efa4d02f0652e9955657f220ce1b82d66c95e"),
    "sound_flac_metadata.hpp": (6337, "2226b5a9fa8afc241f843a5a1dc8da38574eb0c931a43f4d66a1b5eae0a19eca"),
    "flac_dump_probe.cpp": (2226, "3f0015a2e7958ccb4d7194e876212767ea19b0f3467ab52f96d3993f39064e86"),
    "flac_dump_cases.hpp": (10402, "fbf0e8c03c850af01b45c46a03bf183b8ce5355c294b2618493ca72a75673cb3"),
}


def probe_result(raw):
    require(len(raw) <= 4096, "bounded FLAC probe JSON required")
    result = json_bytes(raw)
    expected = {"schema": "iw7.flac-dump-header-probe/1", "cases": 103,
                "input_unchanged": True, "extent_checks": True, "native_dump_tested": False,
                "full_conformance": False, "ready": False}
    require(type(result) is dict and result.keys() == expected.keys(), "exact FLAC probe fields required")
    require(all(type(result[k]) is type(v) and result[k] == v for k, v in expected.items()),
            "actual 103-case C++ header probe required; no runtime promotion")
    return result


def validate_extension(plan, sealed_inputs):
    extension = plan.get("flac")
    require(type(extension) is dict and set(extension) == {"overlay", "sources", "review", "original_sound_bank"},
            "closed FLAC source extension required")
    overlay = extension["overlay"]
    require(ntpath.isabs(overlay) and key(ntpath.dirname(overlay)) == key(ntpath.join(plan["shared_repo"], "runtime/content-surfaces"))
            and re.fullmatch(r"original-sound-flac-dump-source-[a-z0-9-]+", ntpath.basename(overlay)), "private FLAC source overlay required")
    sources = {key(p["path"]): p for p in plan["source_pins"]}
    require(len(sources) == len(plan["source_pins"]), "duplicate bootstrap source")
    require(len(extension["sources"]) == 4, "exact four new FLAC sources required")
    result = {}
    for pin in extension["sources"]:
        name = ntpath.basename(pin["path"])
        require(set(pin) == {"path", "bytes", "sha256"} and name in SOURCE_PINS and
                key(pin["path"]) == key(ntpath.join(overlay, name)) and key(pin["path"]) not in result and
                type(pin["bytes"]) is int and (pin["bytes"], pin["sha256"]) == SOURCE_PINS[name], "reviewed FLAC source identity differs")
        require(sources.get(key(pin["path"])) == pin and key(pin["path"]) not in sealed_inputs,
                "new FLAC source must have its own retained guard, not Seal C")
        result[key(pin["path"])] = {"Path": pin["path"], "Bytes": pin["bytes"], "SHA256": pin["sha256"]}
    review = extension["review"]
    require(set(review) == {"path", "bytes", "sha256"} and review["sha256"] == REVIEW_SHA and
            type(review["bytes"]) is int and 0 < review["bytes"] <= 131072 and sources.get(key(review["path"])) == review,
            "retained exact original response review required")
    original = extension["original_sound_bank"]
    require(ntpath.isabs(original) and key(original).endswith(r"\src\zonetool\zonetool\iw7\assets\sound_bank.cpp"),
            "original IW7 source path required")
    if sealed_inputs:
        require(sealed_inputs.get(key(original), {}).get("SHA256") == SOURCE_SHA, "original sound source outside Seal C")
    return result


def replace_once(text, old, new):
    pattern = re.compile(re.escape(old), re.I)
    require(len(pattern.findall(text)) == 1, "exact response source token required")
    return pattern.sub(lambda _: new, text)


def expected_commands(plan, read):
    """Rebuild response bytes from the immutable original review and Seal C RSPs."""
    from response_revision import repair
    review_raw = read(plan["flac"]["review"]["path"], 131072)
    require(sha(review_raw) == REVIEW_SHA, "original response review changed")
    review = json_bytes(review_raw)
    overlay, candidate = plan["flac"]["overlay"], plan["candidate"]
    commands, responses = [], {}
    for item in review["commands"]:
        command = {k: item[k] for k in ("phase", "kind", "executable", "arguments", "working_directory")}
        command["working_directory"] = candidate
        if item["kind"] == "probe_run":
            command["executable"] = item["executable"].replace(review["candidate_path"], candidate)
        else:
            base = read(item["arguments"][0][1:], 131072)
            require(sha(base) == item["response_sha256"], "sealed original response changed")
            raw, _, _ = repair(base, review["candidate_path"], candidate, item["kind"].endswith("compile"))
            if item["phase"] == "compile-sound_bank":
                text = replace_once(raw.decode(), plan["flac"]["original_sound_bank"], ntpath.join(overlay, "sound_bank.cpp"))
                lines = text.splitlines(keepends=True)
                lines.insert(1, '/I"' + ntpath.dirname(plan["flac"]["original_sound_bank"]) + '"\n')
                raw = "".join(lines).encode()
            responses[item["phase"]] = raw
        commands.append(command)
    extras = []
    for phase in EXTRA_ORDER:
        base_phase = phase.replace("flac", "original")
        command = copy.deepcopy(next(c for c in commands if c["phase"] == base_phase))
        command["phase"] = phase
        if phase.endswith("-run"):
            command["executable"] = ntpath.join(candidate, "probe", "flac-header.exe")
            command["arguments"] = ["--verify-headers"]
        else:
            raw = responses[base_phase].decode()
            raw = raw.replace(ntpath.join(candidate, "probe", "original"), ntpath.join(candidate, "probe", "flac-header"))
            if phase.endswith("-compile"):
                raw = replace_once(raw, ntpath.join(plan["shared_repo"], *"tools-source/asset-bridge/surfaces/sound/native-checksum/checksum_probe.cpp".split("/")),
                                   ntpath.join(overlay, "flac_dump_probe.cpp"))
            responses[phase] = raw.encode()
        extras.append(command)
    return commands[:6] + extras + commands[6:], responses


def verify_responses(plan, read, sealed_inputs):
    validate_extension(plan, sealed_inputs)
    commands, responses = expected_commands(plan, read)
    for expected, actual in zip(commands, plan["commands"], strict=True):
        for field in ("phase", "kind", "executable", "working_directory"):
            require(actual[field] == expected[field], "closed FLAC native command differs")
        if actual["kind"] == "probe_run":
            require(actual["arguments"] == expected["arguments"], "FLAC probe arguments differ")
        else:
            raw = read(actual["response_path"], 131072)
            require(raw == responses[actual["phase"]] and sha(raw) == actual["response_sha256"],
                    "FLAC response changed outside reviewed source/include/output edits")
    return True

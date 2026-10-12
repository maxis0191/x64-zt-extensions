"""Pure contracts for the sound-only incremental build; importing starts nothing."""
import hashlib
import json
import ntpath
import re
from pathlib import Path

SCHEMA = "iw7.sound-checksum-build-plan/1"
FLAC_SCHEMA = "iw7.sound-flac-dump-build-plan/1"
EXPECTED = "24fe5af1473ea8f4be33912348210c78"
CORRUPT = "78000000000000000000000000000000"
SDK_BIN = r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64"
SDK_TOOLS = {
    "rc.exe": (55640, "43da1503c262c30894c851589bf0155f8365d77e63a5f7bc13982320e3a6b42d"),
    "rcdll.dll": (264536, "9a11e4759adc48abe1fa9e3082ad7db4b53f4d6d77701c13729f4ffd47ae934c"),
}
COMMON_MEMBERS = frozenset(name + ".obj" for name in (
    "binary_resource", "bit_buffer", "compression", "cryptography", "flags", "hook",
    "io", "memory", "minidump", "nt", "signature", "string", "thread"))
ORDER = (
    "probe-original-compile", "probe-original-link", "probe-original-run",
    "probe-patched-compile", "probe-patched-link", "probe-patched-run",
    "compile-loadedsound", "compile-loadedsound1", "compile-loadedsound2",
    "compile-loadedsound3", "compile-sound_bank", "compile-common-bit-buffer",
    "archive-common", "link-candidate")
PROVIDERS = {
    "supervision": "b6125dfaa4c6b16e4ebc6f54f160369788cfe5290f4c734edb925101af4f3471",
    "completion": "9710dd10beaa1db17d0bca51916679145f5d76460bc3c43463f888bc9aff3ad0",
    "diagnostics": "971284b7643182a351a0294c8df52e74794ecc57a7fb870749ccd141f5222379",
    "residual_policy": "86c2d8f3f6c79e5dd644f11741521f74b3ccd6960f45189ba41da38f17ef3888",
    "members": "5a02254764277b62f752792f1ec4f5b93b85237b171a3381a78d58f6af190e91",
    "job": "f6be2a4cafddb78b5e07a6802354575ada418cb7643d96a3abd0a4c063bc6387",
}


def is_flac(plan):
    return plan.get("schema") == FLAC_SCHEMA


def build_order(plan):
    return ORDER[:6] + ("probe-flac-compile", "probe-flac-link", "probe-flac-run") + ORDER[6:] if is_flac(plan) else ORDER


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def json_bytes(raw):
    def unique(pairs):
        out, seen = {}, set()
        for name, value in pairs:
            require(name.casefold() not in seen, "duplicate JSON key")
            seen.add(name.casefold())
            out[name] = value
        return out
    return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique,
                      parse_constant=lambda value: require(False, "nonfinite JSON number"))


def key(path):
    return ntpath.normcase(ntpath.normpath(str(path)))


def probe_result(raw, original):
    require(len(raw) <= 4096, "probe output too large")
    data = json_bytes(raw)
    fields = {"source_checksum", "matches_original_md5", "field_matches", "payload_unchanged",
              "outside_field_unchanged", "native_ff_tested", "ready"}
    require(type(data) is dict and set(data) == fields, "probe fields differ")
    require(data["source_checksum"] == (CORRUPT if original else EXPECTED), "native C++ digest differs")
    for field in fields - {"source_checksum"}:
        require(type(data[field]) is bool, "typed probe flags required")
    require(data["matches_original_md5"] is (not original), "native probe claim differs")
    require(all(data[f] for f in ("field_matches", "payload_unchanged", "outside_field_unchanged")),
            "native synthetic field/payload conservation failed")
    require(not data["native_ff_tested"] and not data["ready"], "probe cannot promote SAB or runtime")
    return data


def archive_members(raw):
    """Read bounded standard COFF archives without invoking a native librarian."""
    require(8 <= len(raw) <= 8 * 1024 * 1024 and raw[:8] == b"!<arch>\n", "bounded COFF archive required")
    offset, names, result = 8, b"", {}
    while offset < len(raw):
        header = raw[offset:offset + 60]
        require(len(header) == 60 and header[58:] == b"`\n", "archive header differs")
        name = header[:16].decode("ascii").strip()
        length = int(header[48:58])
        start, end = offset + 60, offset + 60 + length
        require(length >= 0 and end <= len(raw), "archive member out of bounds")
        if name == "//":
            require(not names, "duplicate archive long-name table")
            names = raw[start:end]
        elif name != "/":
            if name.startswith("/"):
                index = int(name[1:])
                require(0 <= index < len(names), "archive long-name offset invalid")
                name = names[index:].split(b"\0", 1)[0].split(b"/\n", 1)[0].decode("ascii")
            else:
                name = name.rstrip("/")
            basename = ntpath.basename(name).casefold()
            require(basename in COMMON_MEMBERS and basename not in result, "unknown/duplicate common member")
            result[basename] = raw[start:end]
        offset = end + length % 2
        require(offset <= len(raw), "archive padding missing")
    require(set(result) == COMMON_MEMBERS, "thirteen exact common members required")
    return result


def compare_archive(raw, objects):
    members = archive_members(raw)
    require(set(objects) == COMMON_MEMBERS, "complete common object mapping required")
    for name in sorted(COMMON_MEMBERS):
        require(members[name] == objects[name], "common member payload differs: " + name)
    return {name: {"bytes": len(data), "sha256": sha(data)} for name, data in sorted(members.items())}


def include_report(raw, allowed, expected_header, forbidden_header):
    require(len(raw) <= 2 * 1024 * 1024, "compiler include report exceeds bound")
    # VSLANG=1033 is explicit in the exact native environment.
    prefix = "Note: including file:"
    paths = [line.strip()[len(prefix):].strip() for line in raw.decode("utf-8", "replace").splitlines()
             if line.strip().startswith(prefix)]
    observed = {key(p) for p in paths}
    require(key(expected_header) in observed, "patched/original header not established by compiler")
    require(key(forbidden_header) not in observed, "wrong bit-buffer header consumed")
    require(observed <= {key(p) for p in allowed}, "compiler consumed an unsealed include")
    return sorted(observed)


def reviewed_responses(plan, sealed_inputs):
    """New tiny response sources are Plan-pinned, never relabelled as Seal C."""
    responses = plan.get("response_pins", [])
    allowed = (14,) if is_flac(plan) else (0, 12)
    require(type(responses) is list and len(responses) in allowed, "exact reviewed response source count required")
    if not responses:
        return {}
    source_list = plan["source_pins"]
    sources = {key(p["path"]): p for p in source_list}
    require(len(sources) == len(source_list), "duplicate source pin")
    expected = {key(c["response_path"]) for c in plan["commands"] if c["kind"] != "probe_run"}
    result = {}
    for pin in responses:
        path = key(pin["path"])
        require(ntpath.isabs(pin["path"]) and path not in result and path not in sealed_inputs,
                "unique new response path required")
        require(type(pin["bytes"]) is int and 0 < pin["bytes"] <= 128*1024 and
                re.fullmatch("[0-9a-f]{64}", pin["sha256"]), "bounded exact response pin required")
        require(path in sources and sources[path] == pin, "response must be guarded as a bootstrap source")
        result[path] = {"Path": pin["path"], "Bytes": pin["bytes"], "SHA256": pin["sha256"]}
    require(set(result) == expected and len(expected) == (14 if is_flac(plan) else 12), "exact command responses must be reviewed")
    for command in plan["commands"]:
        if command["kind"] != "probe_run":
            require(result[key(command["response_path"])]["SHA256"] == command["response_sha256"], "command response pin differs")
    return result


def reviewed_sdk_tools(plan, sealed_inputs):
    """SDK additions are guarded Plan sources, not retroactive Seal C entries."""
    pins = plan.get("sdk_tools")
    require(type(pins) is list and len(pins) == 2, "two exact SDK resource tools required")
    expected = {key(ntpath.join(SDK_BIN, name)): (length, digest)
                for name, (length, digest) in SDK_TOOLS.items()}
    sources = plan["source_pins"]
    seen = set()
    for pin in pins:
        require(type(pin) is dict and set(pin) == {"path", "bytes", "sha256"}, "exact SDK pin fields required")
        path = key(pin["path"])
        require(path in expected and path not in seen and path not in sealed_inputs, "unique new SDK path required")
        seen.add(path)
        require(type(pin["bytes"]) is int and (pin["bytes"], pin["sha256"]) == expected[path],
                "reviewed SDK byte identity differs")
        matches = [source for source in sources if key(source["path"]) == path]
        require(matches == [pin], "SDK tool must be guarded as one bootstrap source")
    expected_path = ntpath.dirname(plan["compiler"]) + ";" + SDK_BIN + r";C:\Windows\System32"
    require(plan["environment"].get("PATH") == expected_path, "exact compiler/SDK/system PATH required")
    return pins


def validate_plan(plan, sealed=False):
    require(type(plan) is dict and plan.get("schema") in (SCHEMA, FLAC_SCHEMA), "sound build plan schema differs")
    if is_flac(plan):
        from flac_build_profile import validate_extension
        validate_extension(plan, {})
    else:
        require("flac" not in plan, "FLAC extension cannot use historical checksum schema")
    require(plan.get("source_pin") == "fab935826c898806855376662a8a03317b3ad8f1", "native source pin differs")
    require(plan.get("gsc_provider_revision") == "eabe74ab65d8ce2a943b54d24b15a60749a0cf2a", "v6 source revision differs")
    require(plan.get("physical_bytes") == 4 * 1024**3 and plan.get("commit_bytes") == 6 * 1024**3,
            "complete build resource budget differs")
    require(plan.get("stop_bytes") == 512 * 1024**2 and plan.get("planning_ceiling_bytes") == 768 * 1024**2,
            "build output bound differs")
    require(tuple(c.get("phase") for c in plan.get("commands", [])) == build_order(plan), "closed native command order required")
    require(len(plan["providers"]) == 6, "exact provider count required")
    require({p["role"]: p["sha256"] for p in plan["providers"]} == PROVIDERS, "qualified provider identities differ")
    for field in ("candidate", "output", "shared_repo", "python", "inventory", "seal", "seal_result", "worker", "compiler"):
        require(type(plan.get(field)) is str and ntpath.isabs(plan[field]), "absolute build binding required: " + field)
        require('"' not in plan[field] and not any(ord(c) < 32 for c in plan[field]), "literal build path required")
    require(key(plan["candidate"]) == key(plan["output"]), "single private output root required")
    require(set(plan["common_objects"]) == COMMON_MEMBERS, "thirteen common object paths required")
    require(plan.get("sealed") is bool(sealed), "input sealing state differs")
    if sealed:
        for field in ("seal_sha256", "seal_result_sha256", "python_sha256"):
            require(type(plan.get(field)) is str and re.fullmatch("[0-9a-f]{64}", plan[field]), "reviewed digest required")
    for command in plan["commands"]:
        phase = command["phase"]
        require(key(command["working_directory"]) == key(plan["candidate"]), "private command directory required")
        if phase.endswith("-run"):
            original = phase == "probe-original-run"
            flac = phase == "probe-flac-run"
            require(command["kind"] == "probe_run" and command["arguments"] ==
                    ([] if flac else ["--expect-observed-corrupt" if original else "--expect-original"]), "exact native probe mode required")
            require(key(command["executable"]) == key(ntpath.join(plan["candidate"], "probe",
                    "flac-header.exe" if flac else ("original.exe" if original else "patched.exe"))), "private compiled probe required")
        else:
            require(command["arguments"] == ["@" + command["response_path"]], "literal response-file invocation required")
            require(re.fullmatch("[0-9a-f]{64}", command["executable_sha256"]), "sealed tool digest required")
            expected = "cl.exe" if command["kind"].endswith("compile") else ("lib.exe" if phase == "archive-common" else "link.exe")
            require(key(command["executable"]) == key(ntpath.join(ntpath.dirname(plan["compiler"]), expected)), "single native toolchain required")
    env = plan["environment"]
    for field in ("CL", "_CL_", "LINK", "_LINK_", "LIBPATH", "PYTHONPATH", "PYTHONHOME"):
        require(env.get(field) == "", "implicit tool options/search path not neutralized: " + field)
    require(env.get("VSLANG") == "1033" and env.get("NUMBER_OF_PROCESSORS") == "1", "fixed native environment required")
    require(key(env["TEMP"]) == key(ntpath.join(plan["candidate"], "tmp")) and env["TMP"] == env["TEMP"],
            "private native temporary directory required")
    require(plan.get("sab_ff_authorized") is False and plan.get("ready") is False, "build cannot authorize SAB or runtime")
    reviewed_responses(plan, {})
    reviewed_sdk_tools(plan, {})
    return plan

"""Prepare one concrete FLAC17 Plan from qualified metadata and source text only."""
import argparse
import copy
import json
import ntpath
from pathlib import Path
import re

from build_contract import key, sha, require, json_bytes, validate_plan
import flac_build_profile as flac

BASE_PLAN_SHA = "91280092489387e909516693d4234c60ea0416657166cf6bd8674bd974729c3a"
ROOT = Path(__file__).resolve().parent


def source_bytes(path, maximum=1024 * 1024):
    path = Path(path)
    require(path.suffix.lower() in {".ps1", ".cs", ".py", ".cpp", ".hpp", ".h", ".json", ".rsp"},
            "preparation can read source/metadata only, never binary/audio payloads")
    require(path.is_file() and not path.is_symlink(), "regular source required")
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    require(len(raw) <= maximum, "bounded source required")
    return raw


def pin(path, raw):
    return {"path": str(path), "bytes": len(raw), "sha256": sha(raw)}


def prepare(repo, overlay, review_output, candidate, output, write=True):
    repo, overlay = repo.resolve(), overlay.resolve()
    review_output, candidate, output = review_output.absolute(), candidate.absolute(), output.absolute()
    require(review_output.parent == repo / "runtime/content-surfaces" and
            re.fullmatch(r"original-sound-flac-build-review-[a-z0-9-]+", review_output.name) and
            candidate.parent == repo / "runtime" and re.fullmatch(r"zt-sound-flac-[a-z0-9-]+", candidate.name) and
            output.parent == review_output.parent and re.fullmatch(r"original-sound-flac-build-plan-[a-z0-9-]+\.local\.json", output.name),
            "private literal FLAC preparation paths required")
    require(not review_output.exists() and not candidate.exists() and not output.exists(), "fresh preparation and native output required")
    baseline = source_bytes(repo / "runtime/content-surfaces/original-sound-checksum-build-plan-a/build-plan-f.local.json", 2*1024*1024)
    require(sha(baseline) == BASE_PLAN_SHA, "exact completed Build F metadata required")
    plan = copy.deepcopy(json_bytes(baseline))
    require(key(plan["shared_repo"]) == key(repo), "same source-owned repository required")
    seal_raw = source_bytes(plan["seal"], 4*1024*1024)
    require(sha(seal_raw) == plan["seal_sha256"], "immutable Seal C metadata required")
    seal = json_bytes(seal_raw)
    entries = {key(e["Path"]): e for e in seal["Inputs"]}
    require(len(entries) == 1410, "complete Seal C metadata required")
    review_path = repo / "runtime/content-surfaces/original-sound-checksum-build-review-a/command-review.local.json"
    review_raw = source_bytes(review_path, 131072)
    require(sha(review_raw) == flac.REVIEW_SHA, "exact original command review required")
    review = json_bytes(review_raw)
    original_cpp = next(e["Path"] for e in seal["Inputs"] if key(e["Path"]).endswith(r"\tools\x64-zt-enemy\src\zonetool\zonetool\iw7\assets\sound_bank.cpp"))
    old_responses = {key(p["path"]) for p in plan["response_pins"]}
    old_responses.add(key(plan["response_revision"]))
    sdk = {key(p["path"]): p for p in plan["sdk_tools"]}
    sources = {}
    for previous in plan["source_pins"]:
        path = previous["path"]
        if key(path) in old_responses:
            continue
        # These exact declarations are rechecked by both validators. No SDK file
        # is opened or hashed until the new profile's admitted execution.
        sources[key(path)] = copy.deepcopy(sdk[key(path)]) if key(path) in sdk else pin(path, source_bytes(path))
    source_pins = []
    for name, (length, digest) in flac.SOURCE_PINS.items():
        path = overlay / name
        raw = source_bytes(path)
        require(len(raw) == length and sha(raw) == digest, "reviewed FLAC overlay changed")
        item = pin(path, raw)
        source_pins.append(item)
        sources[key(path)] = item
    for path in (ROOT / "flac_build_profile.py", ROOT / "FlacBuild.Profile.ps1", Path(__file__), review_path):
        sources[key(path)] = pin(path, source_bytes(path))
    plan.update(schema=flac.SCHEMA, candidate=str(candidate), output=str(candidate), response_revision=None)
    plan["environment"]["TEMP"] = plan["environment"]["TMP"] = str(candidate / "tmp")
    plan["flac"] = {"overlay": str(overlay), "sources": source_pins, "review": pin(review_path, review_raw),
                    "original_sound_bank": original_cpp}
    commands, response_bytes = flac.expected_commands(plan, source_bytes)
    response_pins = []
    prepared = {}
    for command in commands:
        if command["kind"] != "probe_run":
            raw = response_bytes[command["phase"]]
            path = review_output / (command["phase"] + ".rsp")
            item = pin(path, raw)
            command.update(arguments=["@" + str(path)], response_path=str(path), response_sha256=item["sha256"],
                           executable_sha256=entries[key(command["executable"])]["SHA256"])
            response_pins.append(item)
            sources[key(path)] = item
            prepared[key(path)] = raw
    plan.update(commands=commands, response_pins=response_pins, source_pins=sorted(sources.values(), key=lambda p: key(p["path"])))
    require(len(plan["source_pins"]) <= 64, "bootstrap source count bound exceeded")
    validate_plan(plan, sealed=True)
    flac.validate_extension(plan, entries)
    flac.verify_responses(plan, lambda p, maximum: prepared[key(p)] if key(p) in prepared else source_bytes(p, maximum), entries)
    raw = (json.dumps(plan, indent=2) + "\n").encode()
    require(len(raw) <= 2*1024*1024, "bounded Plan required")
    if write:
        review_output.mkdir()
        for item in response_pins:
            with Path(item["path"]).open("xb") as stream:
                stream.write(prepared[key(item["path"])])
        with output.open("xb") as stream:
            stream.write(raw)
    return plan, raw, prepared


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repo", "overlay", "review-output", "candidate", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    plan, raw, _ = prepare(args.repo, args.overlay, args.review_output, args.candidate, args.output)
    print(json.dumps({"plan": str(args.output), "bytes": len(raw), "sha256": sha(raw), "commands": len(plan["commands"]),
                      "source_pins": len(plan["source_pins"]), "native_started": False, "admission_requested": False,
                      "candidate_created": False, "sdk_payloads_read": False, "ready": False}, indent=2))

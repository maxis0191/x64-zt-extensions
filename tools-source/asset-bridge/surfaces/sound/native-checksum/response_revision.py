"""Pure, bounded D8004 response repair; no compiler, lease or native output."""
import argparse
import copy
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_contract import json_bytes, key, require, sha

REVIEW_SHA = "75ad217b9841856a7401785fef53b8281e3b80e26bf5525e37e8250ee2826ce9"
SEAL_SHA = "f52867e7c26d05466ba57d72eef601d42376c1109dfcf61f219a1a028229f388"


def small(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 1024*1024, "bounded response/review file required")
    raw = path.read_bytes()
    require(len(raw) <= 1024*1024, "response/review grew")
    return raw


def relocate(text, old, new):
    return re.subn(re.escape(old), lambda match: new, text, flags=re.IGNORECASE)


def repair(raw, old_candidate, new_candidate, compilation):
    require(key(old_candidate) != key(new_candidate), "fresh candidate identity required")
    text = raw.decode("utf-8")
    lines, out, definitions = text.splitlines(keepends=True), [], []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.rstrip("\r\n") == "/D":
            require(compilation and index+1 < len(lines), "orphan/foreign definition option")
            argument = lines[index+1].rstrip("\r\n")
            require(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:=[^\s\"]+)?", argument), "literal macro argument required")
            require(argument not in definitions, "duplicate definition in recorded response")
            definitions.append(argument)
            out.append("/D" + lines[index+1])
            index += 2
        else:
            out.append(line)
            index += 1
    require((len(definitions) in (11, 12)) if compilation else not definitions,
            "exact recorded macro count required")
    joined = "".join(out)
    require(not any(line == "/D" for line in joined.splitlines()), "standalone /D remains")
    revised, count = relocate(joined, old_candidate, new_candidate)
    require(count > 0 and old_candidate.casefold() not in revised.casefold(), "old output path remains or no relocation occurred")
    return revised.encode("utf-8"), definitions, count


def read_baseline(repo):
    root = repo / "runtime/content-surfaces"
    raw = small(root / "original-sound-checksum-build-review-a/command-review.local.json")
    require(sha(raw) == REVIEW_SHA, "original command review changed")
    review = json_bytes(raw)
    raw = small(root / "original-sound-checksum-seal-a/sealed-inputs.local.json")
    require(sha(raw) == SEAL_SHA, "Seal C changed")
    seal = json_bytes(raw)
    entries = {key(e["Path"]): e for e in seal["Inputs"]}
    return review, entries


def validate_revision(repo, path):
    revision = json_bytes(small(path))
    review, entries = read_baseline(repo)
    require(revision["schema"] == "iw7.sound-checksum-response-revision/1" and
            revision["base_review_sha256"] == REVIEW_SHA and revision["seal_sha256"] == SEAL_SHA,
            "exact prior source bindings required")
    candidate = Path(revision["candidate"])
    require(candidate.is_absolute() and candidate.parent == repo / "runtime" and
            re.fullmatch(r"zt-sound-md5-[a-z0-9-]+", candidate.name) and not candidate.exists(),
            "fresh private candidate required")
    old_candidate = review["candidate_path"]
    require(key(revision["base_candidate"]) == key(old_candidate) and len(revision["responses"]) == 12,
            "exact response revision inventory required")
    records = {item["phase"]: item for item in revision["responses"]}
    require(len(records) == 12, "unique response phases required")
    commands, pins, source_files = [], [], set()
    for original in review["commands"]:
        command = copy.deepcopy(original)
        command["working_directory"] = str(candidate)
        if command["kind"] == "probe_run":
            command["executable"], count = relocate(command["executable"], old_candidate, str(candidate))
            require(count == 1, "one probe output path required")
        else:
            item = records[command["phase"]]
            base = original["arguments"][0][1:]
            require(key(item["base_path"]) == key(base) and item["base_sha256"] == original["response_sha256"] ==
                    entries[key(base)]["SHA256"], "original response is outside Seal C")
            before = small(base)
            require(sha(before) == item["base_sha256"], "original sealed response changed")
            expected, macros, moved = repair(before, old_candidate, str(candidate), command["kind"].endswith("compile"))
            target = Path(item["path"])
            require(target.parent == path.parent and target.name == Path(base).name and key(target) not in source_files,
                    "exact fresh response path required")
            source_files.add(key(target))
            actual = small(target)
            require(actual == expected and item["sha256"] == sha(actual) and item["bytes"] == len(actual) and
                    item["definitions"] == macros and item["relocated_paths"] == moved,
                    "response repair changed more than definitions/output paths")
            command["arguments"] = ["@" + str(target)]
            command["response_sha256"] = sha(actual)
            pins.append({"path": str(target), "bytes": len(actual), "sha256": sha(actual)})
        commands.append(command)
    return candidate, commands, pins


def prepare(repo, output, candidate):
    require(not output.exists() and not candidate.exists(), "fresh response/candidate directories required")
    require(output.parent == repo / "runtime/content-surfaces" and candidate.parent == repo / "runtime" and
            re.fullmatch(r"zt-sound-md5-[a-z0-9-]+", candidate.name), "private fresh preparation paths required")
    review, entries = read_baseline(repo)
    prepared, records = [], []
    for command in review["commands"]:
        if command["kind"] == "probe_run":
            continue
        base = command["arguments"][0][1:]
        before = small(base)
        require(sha(before) == command["response_sha256"] == entries[key(base)]["SHA256"], "sealed base response changed")
        after, macros, moved = repair(before, review["candidate_path"], str(candidate), command["kind"].endswith("compile"))
        target = output / Path(base).name
        prepared.append((target, after))
        records.append({"phase": command["phase"], "base_path": base, "base_sha256": sha(before),
                        "path": str(target), "bytes": len(after), "sha256": sha(after),
                        "definitions": macros, "relocated_paths": moved})
    require(len(records) == 12 and sum(len(r["definitions"]) for r in records) == 93, "twelve responses and 93 exact definitions required")
    output.mkdir()
    for target, raw in prepared:
        with target.open("xb") as stream:
            stream.write(raw)
    result = {"schema": "iw7.sound-checksum-response-revision/1", "base_review_sha256": REVIEW_SHA,
              "seal_sha256": SEAL_SHA, "base_candidate": review["candidate_path"], "candidate": str(candidate),
              "responses": records, "native_started": False, "ready": False}
    manifest = output / "response-revision.local.json"
    raw = (json.dumps(result, indent=2) + "\n").encode()
    with manifest.open("xb") as stream:
        stream.write(raw)
    validate_revision(repo, manifest)
    return {"manifest": str(manifest), "bytes": len(raw), "sha256": sha(raw), "responses": 12,
            "definitions_joined": 93, "candidate_created": False, "native_started": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.repo.resolve(), args.output.resolve(), args.candidate.resolve()), indent=2))

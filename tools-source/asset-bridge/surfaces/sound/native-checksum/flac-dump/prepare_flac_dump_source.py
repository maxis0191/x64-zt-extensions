"""Materialize only a pinned private source overlay. Never start/hash native tools."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from flac_dump_vectors import cpp_cases

ROOT = Path(__file__).resolve().parent
SOURCE_REL = "src/zonetool/zonetool/iw7/assets/sound_bank.cpp"
BASE_LF_SHA = "12222be055cb422d9d07d17766c9f22882597e03819eeae5c500137439f71246"
PATCHED_LF_SHA = "8142eead0fe7cbdb6a0b17cc106efa4d02f0652e9955657f220ce1b82d66c95e"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def small(path):
    # One bounded read. Only callers' closed source file list is accepted below.
    require(path.is_file() and not path.is_symlink(), "regular source required")
    with path.open("rb") as stream:
        raw = stream.read(128 * 1024 + 1)
    require(len(raw) <= 128 * 1024, "source exceeds bound")
    return raw


def apply_source_patch(before, patch):
    """Strict one-file unified patch application; no shell/git/native subprocess."""
    lines = patch.splitlines(keepends=True)
    require(lines[:3] == [f"diff --git a/{SOURCE_REL} b/{SOURCE_REL}\n",
                         f"--- a/{SOURCE_REL}\n", f"+++ b/{SOURCE_REL}\n"], "wrong patch target")
    original, out, position, index, hunks = before.splitlines(keepends=True), [], 0, 3, 0
    while index < len(lines):
        match = re.fullmatch(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@.*\n", lines[index])
        require(match is not None, "malformed patch hunk")
        start, old_count, new_start, new_count = (int(v) if v is not None else 1 for v in match.groups())
        require(position <= start - 1 <= len(original), "overlapping/out-of-bounds patch hunk")
        out.extend(original[position:start - 1])
        position = start - 1
        require(len(out) == new_start - 1, "new hunk position mismatch")
        old_seen = new_seen = 0
        index += 1
        while index < len(lines) and not lines[index].startswith("@@ "):
            line = lines[index]
            require(line[:1] in (" ", "+", "-"), "unexpected patch line")
            if line[0] in " -":
                require(position < len(original) and original[position] == line[1:], "patch source context differs")
                position += 1
                old_seen += 1
            if line[0] in " +":
                out.append(line[1:])
                new_seen += 1
            index += 1
        require((old_seen, new_seen) == (old_count, new_count), "patch hunk count differs")
        hunks += 1
    require(hunks > 0, "empty patch")
    out.extend(original[position:])
    return "".join(out)


def render(raw, patch):
    before = raw.replace(b"\r\n", b"\n")
    require(sha(before) == BASE_LF_SHA, "pinned upstream sound source required")
    after = apply_source_patch(before.decode("utf-8"), patch.decode("utf-8")).encode()
    require(sha(after) == PATCHED_LF_SHA, "exact reviewed patched source required")
    return after


def prepare(repo, source, output):
    repo, source = repo.resolve(), source.absolute()
    output = output.absolute()
    require(source.name == "sound_bank.cpp", "sound source only")
    require(output.parent.resolve() == repo / "runtime/content-surfaces" and
            re.fullmatch(r"original-sound-flac-dump-source-[a-z0-9-]+", output.name) and not output.exists(),
            "fresh private source overlay required")
    inputs = {name: small(ROOT / name) for name in (
        "zonetool-fab9358-flac-dump.patch", "sound_flac_metadata.hpp", "flac_dump_probe.cpp", "flac_dump_vectors.py")}
    original = small(source)
    files = {
        "sound_bank.cpp": render(original, inputs["zonetool-fab9358-flac-dump.patch"]),
        "sound_flac_metadata.hpp": inputs["sound_flac_metadata.hpp"],
        "flac_dump_probe.cpp": inputs["flac_dump_probe.cpp"],
        "flac_dump_cases.hpp": cpp_cases(),
    }
    manifest = {"schema": "iw7.flac-dump-source-overlay/1",
                "source_pin": "fab935826c898806855376662a8a03317b3ad8f1",
                "base_source_lf_sha256": BASE_LF_SHA, "base_source_raw_sha256": sha(original),
                "inputs": {name: {"bytes": len(raw), "sha256": sha(raw)} for name, raw in inputs.items()},
                "files": {name: {"bytes": len(raw), "sha256": sha(raw)} for name, raw in files.items()},
                "scope": "fixed-multiframe-explicit16-hybrid0-header-only",
                "executable_plan": False, "native_started": False, "ready": False}
    # Complete all pure checks before creating anything. Never reuse a partial root.
    output.mkdir()
    for name, raw in files.items():
        with (output / name).open("xb") as stream:
            stream.write(raw)
    with (output / "source-manifest.local.json").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.repo, args.source, args.output)
    print(json.dumps({"files": result["files"], "executable_plan": False, "native_started": False, "ready": False}, indent=2))

"""Materialize the one H1-marked JSON record; transport only, no DTO qualification.

The original log and receipts remain immutable. The unchanged consumer CLI reads
the new .json artifact separately with the original native exit code.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"t7-iw7"))
import image_metadata_consumer as bounded
import registration_bindings_consumer as consumer
from selected_image_request import PIN as NATIVE_SOURCE

MARKER = b"T7_REGISTRATION_MATERIAL_BINDINGS"
LOG_LIMIT = 1024*1024
RECORD_LIMIT = 32768
MANIFEST_LIMIT = 16384
need = bounded.need


def extract_record(raw):
    """Match the existing H1 one-line transport and preserve UTF-8 byte offsets."""
    need(type(raw) is bytes and 0 < len(raw) <= LOG_LIMIT, "bounded stdout bytes required")
    raw.decode("utf-8", errors="strict")
    need(raw.count(MARKER) == 1, "exactly one global bindings marker required")
    matches = list(re.finditer(rb"(?m)^[^\r\n]*?"+MARKER+rb" (\{[^\r\n]*\})\r?$", raw))
    need(len(matches) == 1, "one complete H1 JSON line without trailer required")
    match = matches[0]; record = match.group(1)
    need(len(record) <= RECORD_LIMIT, "bindings JSON exceeds 32 KiB")
    value = bounded.strict_json(record)
    need(type(value) is dict, "bindings JSON object required")
    for name, expected in (("schema", consumer.SCHEMA), ("source_profile", consumer.PROFILE),
                           ("native_source_commit", NATIVE_SOURCE)):
        need(type(value.get(name)) is str and value[name] == expected, "bindings record identity differs")
    # Same generic nesting bound as H1 JsonDocument; no 41/9/10 DTO interpretation.
    pending = [(value, 1)]
    while pending:
        item, depth = pending.pop()
        need(depth <= 25, "H1 JSON depth exceeds 25")
        children = item.values() if type(item) is dict else item if type(item) is list else ()
        pending.extend((child, depth+1) for child in children if type(child) in (dict, list))
    return record, dict(marker_byte_offset=raw.index(MARKER), record_byte_offset=match.start(1), record_byte_length=len(record))


def ordinary_path(value, suffix):
    lexical = str(value).replace("\\", "/")
    need(not lexical.casefold().startswith(("//?/", "//./", "/??/", "//??/")), "device path refused")
    drive = re.match("[A-Za-z]:", lexical)
    remainder = lexical[2:] if drive else lexical
    need(":" not in remainder and (not drive or remainder.startswith("/")), "ADS or drive-relative path refused")
    need(not any(PureWindowsPath(part).is_reserved() for part in PureWindowsPath(lexical).parts), "reserved path refused")
    path = Path(value)
    need(path.suffix.lower() == suffix and path.is_absolute(), "ordinary absolute role suffix required")
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    for entry in (path, *path.parents):
        try:
            info = entry.lstat()
        except FileNotFoundError:
            continue
        need(not stat.S_ISLNK(info.st_mode) and not (getattr(info, "st_file_attributes", 0) & reparse), "reparse path refused")
    need(path == path.resolve(), "canonical role path required")
    return path


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_new_output(path, stream, opened, raw):
    ordinary_path(path, ".json")
    stream.seek(0)
    need(stream.read(len(raw)+1) == raw, "new output readback differs")
    current = os.fstat(stream.fileno()); leaf = path.lstat()
    need(stat.S_ISREG(current.st_mode) and stat.S_ISREG(leaf.st_mode) and
         (current.st_dev, current.st_ino, current.st_size) == (opened.st_dev, opened.st_ino, len(raw)) and
         (leaf.st_dev, leaf.st_ino, leaf.st_size) == (opened.st_dev, opened.st_ino, len(raw)),
         "new output path identity/size differs")


@contextmanager
def write_new_verified(path, raw):
    # Hold both original output streams throughout provenance publication.
    with path.open("x+b") as stream:
        opened = os.fstat(stream.fileno())
        need(stat.S_ISREG(opened.st_mode) and opened.st_size == 0, "new regular empty output required")
        need(stream.write(raw) == len(raw), "short new output write")
        stream.flush(); os.fsync(stream.fileno())
        verify_new_output(path, stream, opened, raw)
        yield stream, opened
        verify_new_output(path, stream, opened, raw)


def materialize(log, log_bytes, log_sha256, output, manifest, native_exit_code):
    need(type(log_bytes) is int and 0 < log_bytes <= LOG_LIMIT and type(log_sha256) is str and
         re.fullmatch("[0-9a-f]{64}", log_sha256), "exact original stdout pin required")
    need(type(native_exit_code) is int and -2147483648 <= native_exit_code <= 4294967295, "original native exit integer required")
    log = ordinary_path(log, ".log"); output = ordinary_path(output, ".json"); manifest = ordinary_path(manifest, ".json")
    need(log.name == "stdout.log", "existing H1 stdout.log required")
    need(len({str(p).casefold() for p in (log, output, manifest)}) == 3, "distinct transport paths required")
    need(not output.exists() and not manifest.exists(), "fresh output and provenance paths required")
    need(output.parent.is_dir() and manifest.parent.is_dir(), "existing ordinary output parents required")
    declared = log.lstat()
    need(stat.S_ISREG(declared.st_mode) and declared.st_size == log_bytes, "original stdout metadata differs")
    source = Path(__file__).resolve()
    need(0 < source.stat().st_size <= LOG_LIMIT, "bounded extractor Source required")
    source_raw = source.read_bytes()
    with log.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        need(stat.S_ISREG(opened.st_mode) and (opened.st_dev, opened.st_ino, opened.st_size) ==
             (declared.st_dev, declared.st_ino, log_bytes), "original opened stdout identity differs")
        raw = stream.read(LOG_LIMIT+1)
        need(len(raw) == log_bytes and sha(raw) == log_sha256, "original stdout pin differs")
        record, offsets = extract_record(raw)
        provenance = dict(schema="iw7.t7-registration-bindings-record-transport/1",
            origin_log=dict(Path=str(log), Bytes=log_bytes, SHA256=log_sha256), marker=MARKER.decode("ascii"), **offsets,
            record=dict(Path=str(output), Bytes=len(record), SHA256=sha(record)),
            extractor_source=dict(Path=str(source), Bytes=len(source_raw), SHA256=sha(source_raw)),
            native_exit_code=native_exit_code, transport_only=True, semantic_validation_performed=False, ready=False)
        encoded = (json.dumps(provenance, indent=2)+"\n").encode("utf-8")
        need(len(encoded) <= MANIFEST_LIMIT, "transport provenance exceeds 16 KiB")
        with write_new_verified(output, record) as record_output:
            # Verify the original held log before and after provenance publication.
            stream.seek(0)
            need(stream.read(LOG_LIMIT+1) == raw, "original stdout changed during extraction")
            with write_new_verified(manifest, encoded) as provenance_output:
                verify_new_output(output, *record_output, record)
                verify_new_output(manifest, *provenance_output, encoded)
                stream.seek(0)
                need(stream.read(LOG_LIMIT+1) == raw, "original stdout changed during publication")
        stream.seek(0)
        after = os.fstat(stream.fileno()); leaf = log.lstat()
        need(stream.read(LOG_LIMIT+1) == raw and (after.st_dev, after.st_ino, after.st_size) ==
             (opened.st_dev, opened.st_ino, log_bytes) and (leaf.st_dev, leaf.st_ino, leaf.st_size) ==
             (opened.st_dev, opened.st_ino, log_bytes), "original stdout changed before completion")
    return provenance


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--log-bytes", type=int, required=True)
    parser.add_argument("--log-sha256", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--provenance-json", type=Path, required=True)
    parser.add_argument("--native-exit-code", type=int, required=True)
    args = parser.parse_args(argv)
    result = materialize(args.log, args.log_bytes, args.log_sha256, args.output_json, args.provenance_json, args.native_exit_code)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

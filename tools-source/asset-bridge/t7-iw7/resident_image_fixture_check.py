"""Check one bounded synthetic native-fixture transcript; never run its executable."""
import argparse
import hashlib
import json
from pathlib import Path

MAX_TRANSCRIPT_BYTES = 1024
EXPECTED = {
    "schema": "iw7.t7-resident-image-fixture/1", "status": "synthetic-pass",
    "copied_cases": 6, "format_cases": 18, "refused_cases": 30,
    "largest_pixel_copy": 96, "layout_bytes": 264, "name_offset": 248,
    "engine_observed": False, "atomic_snapshot": False, "seh_verified": False,
    "readable_callback": "synthetic-allowlist",
}


def unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate fixture transcript key")
        value[key] = item
    return value


def inspect(data):
    if not 0 < len(data) <= MAX_TRANSCRIPT_BYTES:
        raise ValueError("fixture transcript exceeds 1 KiB or is empty")
    value = json.loads(data.decode("utf-8"), object_pairs_hook=unique)
    if type(value) is not dict or value.keys() != EXPECTED.keys():
        raise ValueError("exact fixture transcript fields required")
    if any(type(value[k]) is not type(v) or value[k] != v for k, v in EXPECTED.items()):
        raise ValueError("fixture result differs or overclaims evidence")
    return {"schema": "iw7.t7-resident-image-fixture-check/1", "status": "synthetic-transcript-checked",
            "transcript_bytes": len(data), "transcript_sha256": hashlib.sha256(data).hexdigest(),
            "expected_cases": 54, "engine_observed": False, "native_execution_verified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stdout", type=Path)
    args = parser.parse_args()
    try:
        with args.stdout.open("rb") as stream:
            report = inspect(stream.read(MAX_TRANSCRIPT_BYTES + 1))
        print(json.dumps(report))
        return 0
    except (OSError, ValueError, TypeError, RecursionError) as error:
        print(json.dumps({"error": str(error), "engine_observed": False, "native_execution_verified": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

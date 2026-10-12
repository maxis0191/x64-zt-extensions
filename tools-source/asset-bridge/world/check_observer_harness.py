"""Read a bounded synthetic harness transcript; never compile or launch anything."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

PREFIX = b'WORLD_CLIPMAP_OBSERVATION '
SUMMARY = b'WORLD_CLIPMAP_HARNESS '
READ_LIMIT = 2048
OUTPUT_LIMIT = 4096
RECORDS = 24
TRANSCRIPT_LIMIT = 128 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key')
        result[key] = value
    return result


def decode(raw):
    def invalid_constant(_value):
        raise ValueError('Non-finite JSON constant')
    value = json.loads(raw.decode('ascii'), object_pairs_hook=unique_object,
                       parse_constant=invalid_constant)
    require(isinstance(value, dict), 'JSON object required')
    return value


def validate(raw):
    require(isinstance(raw, bytes) and 0 < len(raw) <= TRANSCRIPT_LIMIT, 'Transcript size bound')
    require(b'\r' not in raw and b'\0' not in raw, 'Canonical binary LF transcript required')
    lines = raw.splitlines(keepends=True)
    require(len(lines) == RECORDS + 1 and all(line.endswith(b'\n') for line in lines), 'Complete record count/newlines')
    records, lengths = [], []
    for line in lines[:-1]:
        require(len(line) <= OUTPUT_LIMIT and line.startswith(PREFIX), 'Observation prefix/4 KiB limit')
        record = decode(line[len(PREFIX):])
        require(record.get('runtime_ready') is False, 'Synthetic runtime boundary')
        if record.get('reason') == 'metadata_budget':
            require(record == {'status': 'refused', 'reason': 'metadata_budget', 'runtime_ready': False},
                    'Exact defensive fallback required')
        else:
            require(record.get('schema') == 'iw7.world-clipmap-observer/1', 'Observer schema')
            require(record.get('signature_checked') is False and record.get('collision_validated') is False,
                    'Synthetic signatures/collision boundary')
            require(type(record.get('reads')) is int and 0 <= record['reads'] <= READ_LIMIT, '2 KiB read bound')
            require(record.get('status') in ('observed', 'refused'), 'Observation status')
            require(isinstance(record.get('reason'), str), 'Refusal reason token')
            require(isinstance(record.get('sections'), list) and len(record['sections']) == 3, 'Three metadata sections')
        records.append(record)
        lengths.append(len(line))
    require(lines[-1].startswith(SUMMARY), 'Harness summary missing')
    summary = decode(lines[-1][len(SUMMARY):])
    expected = {'schema': 'iw7.world-clipmap-harness/1', 'records': RECORDS,
                'largest_record_bytes': max(lengths), 'read_limit': READ_LIMIT, 'output_limit': OUTPUT_LIMIT,
                'fixture_only': True, 'engine_observed': False, 'status': 'passed'}
    require(summary == expected and summary.get('fixture_only') is True and summary.get('engine_observed') is False and
            all(type(summary[key]) is int for key in ('records', 'largest_record_bytes', 'read_limit', 'output_limit')),
            'Exact measured harness summary')
    require([i for i, record in enumerate(records) if record['status'] == 'observed'] == [0, 18],
            'Positive and nested forwarding witnesses missing')
    reasons = Counter(record['reason'] for record in records)
    require(reasons == Counter({'none': 2, 'unsupported_header': 3, 'already_fixed_up': 1,
            'section_bounds': 1, 'root_bounds': 1, 'root_class_limit_or_charset': 1,
            'address_overflow': 2, 'unreadable_memory': 1, 'read_budget_or_address': 3,
            'first_clipmap_name_mismatch': 2, 'post_fixup_relation': 2, 'original_exception': 1,
            'no_clipmap_observed': 1, 'post_count_bounds': 1, 'synthetic_max_width': 1, 'metadata_budget': 1}),
            'Refusal/exception/budget coverage differs')
    require(records[13].get('original_threw') is True and records[20].get('reads') == READ_LIMIT and
            records[21].get('reads') == 1 and records[22].get('reads') == READ_LIMIT,
            'Exception or exact budget witnesses missing')
    return {'schema': 'iw7.world-clipmap-harness-check/1', 'status': 'synthetic-transcript-checked',
            'records': RECORDS, 'largest_record_bytes': max(lengths), 'transcript_bytes': len(raw),
            'transcript_sha256': hashlib.sha256(raw).hexdigest(), 'engine_observed': False,
            'binary_identity_and_original_job_closure_require_outer_receipt': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('transcript', type=Path)
    args = parser.parse_args()
    with args.transcript.open('rb') as stream:
        raw = stream.read(TRANSCRIPT_LIMIT + 1)
    print(json.dumps(validate(raw), indent=2))

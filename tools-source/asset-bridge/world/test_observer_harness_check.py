"""Original JSON fixtures test the reader only, never the unexecuted C++ harness."""
import json
import unittest

import check_observer_harness as check

REASONS = ['none', 'unsupported_header', 'unsupported_header', 'already_fixed_up',
           'unsupported_header', 'section_bounds', 'root_bounds', 'root_class_limit_or_charset',
           'address_overflow', 'unreadable_memory', 'read_budget_or_address', 'first_clipmap_name_mismatch',
           'post_fixup_relation', 'original_exception', 'no_clipmap_observed', 'post_fixup_relation',
           'post_count_bounds', 'address_overflow', 'none', 'first_clipmap_name_mismatch',
           'read_budget_or_address', 'read_budget_or_address', 'synthetic_max_width', 'metadata_budget']


def fixtures():
    records = []
    for i, reason in enumerate(REASONS):
        record = {'status': 'observed' if reason == 'none' else 'refused',
                  'reason': reason, 'runtime_ready': False}
        if reason != 'metadata_budget':
            record.update(schema='iw7.world-clipmap-observer/1', signature_checked=False,
                          collision_validated=False, reads=2048 if i in (20, 22) else 1,
                          original_threw=i == 13, sections=[{}, {}, {}])
        records.append(record)
    return records


def transcript(records):
    lines = [check.PREFIX + json.dumps(record, separators=(',', ':')).encode() + b'\n' for record in records]
    summary = {'schema': 'iw7.world-clipmap-harness/1', 'records': 24,
               'largest_record_bytes': max(map(len, lines)), 'read_limit': 2048, 'output_limit': 4096,
               'fixture_only': True, 'engine_observed': False, 'status': 'passed'}
    return b''.join(lines) + check.SUMMARY + json.dumps(summary, separators=(',', ':')).encode() + b'\n'


class ReaderChecks(unittest.TestCase):
    def test_original_reader_fixture(self):
        result = check.validate(transcript(fixtures()))
        self.assertEqual(result['records'], 24)
        self.assertFalse(result['engine_observed'])

    def test_exact_and_excess_output_boundary(self):
        records = fixtures()
        base = len(check.PREFIX + json.dumps(records[0], separators=(',', ':')).encode() + b'\n')
        records[0]['padding'] = 'x' * (4096 - base - len(',"padding":""'))
        self.assertEqual(check.validate(transcript(records))['largest_record_bytes'], 4096)
        records[0]['padding'] += 'x'
        with self.assertRaisesRegex(ValueError, '4 KiB'):
            check.validate(transcript(records))

    def test_invalid_reads_and_engine_claims(self):
        for key, value in [('reads', 2049), ('reads', -1), ('reads', True),
                           ('signature_checked', True), ('collision_validated', True), ('runtime_ready', True)]:
            records = fixtures(); records[0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                check.validate(transcript(records))

    def test_framing_coverage_and_duplicate_keys(self):
        raw = transcript(fixtures())
        for changed in (raw[:-1], raw + b'extra\n', raw.replace(b'\n', b'\r\n'),
                        raw.replace(b'"reads":1,', b'"reads":1,"reads":1,', 1)):
            with self.subTest(changed=changed[:80]), self.assertRaises(ValueError):
                check.validate(changed)
        records = fixtures(); records[13]['reason'] = 'none'
        with self.assertRaises(ValueError):
            check.validate(transcript(records))

    def test_summary_and_transcript_limits(self):
        raw = transcript(fixtures())
        for value in (b'true', b'0'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                check.validate(raw.replace(b'"engine_observed":false', b'"engine_observed":' + value))
        with self.assertRaises(ValueError):
            check.validate(b'x' * (check.TRANSCRIPT_LIMIT + 1))


if __name__ == '__main__':
    unittest.main()

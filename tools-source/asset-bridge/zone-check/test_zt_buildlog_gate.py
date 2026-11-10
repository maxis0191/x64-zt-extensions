"""Synthetic tests for zt_buildlog_gate.py (no game data, no ZoneTool)."""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 't7-weapons'))
import iw7_audit_common as common  # noqa: E402
import zt_buildlog_gate as gate  # noqa: E402

IMG = '[ WARNING ][ zonetool::iw7::gfx_image::init ]: Image "%s" not found, it will probably look messed up ingame!'
MAT = '[ WARNING ][ zonetool::iw7::material::init ]: Missing material "%s", using default...'
EMPTY = '[ WARNING ][ zonetool::iw7::material::init ]: material %s has an empty image, assigning default...'
DONE = '[ INFO ][ zonetool::iw7::zone_interface::build ]: Successfully compiled fastfile "%s"!'


def write(root, rel, text):
    path = os.path.join(root, *rel.split('/'))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(text)
    return path


def log(root, lines, name='build.log'):
    return write(root, name, '\n'.join(lines) + '\n')


def run(path, **kw):
    kw.setdefault('stock', common.StockDump([]))
    kw.setdefault('intent', common.Intent())
    return gate.audit(path, **kw)


def codes(report, severity=None):
    return [f['code'] for f in report.findings if severity in (None, f['severity'])]


def find(report, code):
    return [f for f in report.findings if f['code'] == code]


class CompletionTest(unittest.TestCase):
    def test_not_completed_is_an_error_and_completed_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = log(tmp, ['[ INFO ][ a::b ]: working'], 'bad.log')
            good = log(tmp, ['[ INFO ][ a::b ]: working', DONE % 'mod'], 'good.log')
            self.assertEqual(codes(run(bad), 'error'), ['LOG-NOT-COMPLETED'])
            report = run(good)
            self.assertEqual(codes(report), [])
            self.assertEqual(report.facts['zone'], 'mod')

    def test_zone_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = log(tmp, [DONE % 'mod'])
            self.assertEqual(codes(run(path, zone='mod')), [])
            self.assertEqual(codes(run(path, zone='cp_iwz'), 'error'), ['LOG-NOT-COMPLETED'])


class ProblemTest(unittest.TestCase):
    def test_error_and_fatal_one_finding_per_distinct_text_with_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = log(tmp, [
                DONE % 'mod',
                '[ ERROR ][ z::sort ]: Could not sort dpvs surfaces!',
                '[ ERROR ][ z::sort ]: Could not sort dpvs surfaces!',
                '[ FATAL ][ z::techset::init ]: techset "x" not found.',
                '[ ERROR ][ z::bank ]: Could not find sound asset t7\\gun\\fire',
            ])
            report = run(path)
            self.assertEqual(sorted(codes(report, 'error')), ['LOG-ERROR', 'LOG-FATAL', 'LOG-SOUND-MISSING'])
            error = find(report, 'LOG-ERROR')[0]
            self.assertEqual(error['evidence']['count'], 2)
            self.assertEqual(find(report, 'LOG-SOUND-MISSING')[0]['asset'], 't7\\gun\\fire')


class FamilyTest(unittest.TestCase):
    def lines(self):
        return [IMG % 'blank_o', IMG % 'blank_o', IMG % 'zeta', MAT % 'fx/smoke', EMPTY % 'weird mat', DONE % 'mod']

    def test_one_warning_per_family_with_all_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run(log(tmp, self.lines()))
            self.assertEqual(sorted(codes(report, 'warn')), ['LOG-DEFAULT-IMAGE', 'LOG-DEFAULT-MATERIAL', 'LOG-EMPTY-IMAGE'])
            image = find(report, 'LOG-DEFAULT-IMAGE')[0]
            self.assertEqual(image['proof'], 'engine')
            self.assertEqual(image['evidence']['names'], ['blank_o', 'zeta'])
            self.assertEqual(image['evidence']['count'], 2)
            self.assertEqual(image['evidence']['lines'], 3)
            self.assertEqual(find(report, 'LOG-EMPTY-IMAGE')[0]['evidence']['names'], ['weird mat'])
            self.assertEqual(len(report.questions), 3)
            self.assertEqual(codes(report, 'error'), [])
            self.assertIn('LOG-NO-STOCK', codes(report, 'info'))

    def test_message_lists_first_ten_names_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = log(tmp, [IMG % ('n%02d' % i) for i in range(15)] + [DONE % 'mod'])
            image = find(run(path), 'LOG-DEFAULT-IMAGE')[0]
            self.assertIn('n09', image['message'])
            self.assertNotIn('n10,', image['message'])
            self.assertIn('and 5 more', image['message'])
            self.assertEqual(len(image['evidence']['names']), 15)

    def test_stock_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, 'stock/zs/zs.csv', 'image,real\nimage,,flagged\nmaterial,mat/a\nmaterial,,mat/b\n')
            write(tmp, 'stock/zs/images/onfile.iw7Image', 'x')
            stock = common.StockDump([os.path.join(tmp, 'stock')])
            path = log(tmp, [IMG % 'real', IMG % 'flagged', IMG % 'onfile', IMG % 'foreign', MAT % 'mat/b', MAT % 'mat/z',
                             DONE % 'mod'])
            report = run(path, stock=stock)
            image = find(report, 'LOG-DEFAULT-IMAGE')[0]['evidence']
            self.assertEqual((image['in_stock'], image['not_in_stock']), (3, 1))
            material = find(report, 'LOG-DEFAULT-MATERIAL')[0]['evidence']
            self.assertEqual((material['in_stock'], material['not_in_stock']), (1, 1))
            self.assertNotIn('LOG-NO-STOCK', codes(report))

    def test_declared_decision_answers_the_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = log(tmp, [IMG % 'a', DONE % 'mod'])
            intent = common.Intent()
            intent.items['mod'] = {'decisions': {'finding:LOG-DEFAULT-IMAGE': {'keep': True, 'why': 'placeholder wanted'}}}
            report = run(path, intent=intent, zone='mod').answer(intent)
            self.assertEqual(report.counts()['warn'], 0)
            self.assertEqual(find(report, 'LOG-DEFAULT-IMAGE')[0]['answered'], 'placeholder wanted')

    def test_other_warnings_and_facts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = log(tmp, ['[ WARNING ][ z::odd ]: first', '[ WARNING ][ z::odd ]: second', 'stray line',
                             '[ INFO ][ a::b ]: ok', DONE % 'mod'])
            report = run(path)
            other = find(report, 'LOG-OTHER-WARNINGS')
            self.assertEqual(len(other), 1)
            self.assertEqual(other[0]['evidence'], {'count': 2, 'sample': 'first'})
            self.assertEqual(report.facts['levels'], {'INFO': 2, 'WARNING': 2})
            self.assertEqual(report.facts['unparsed'], 1)
            self.assertEqual(report.facts['lines'], 5)


class BaselineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def baseline(self, names):
        doc = {'schema': gate.BASELINE_SCHEMA, 'zone': 'mod', 'why': 'test',
               'entries': sorted([f, n] for f, n in names)}
        return write(self.tmp.name, 'base.json', json.dumps(doc))

    def test_known_new_and_fixed(self):
        base = self.baseline([('image-not-found', 'old'), ('image-not-found', 'gone'), ('material-missing', 'm')])
        path = log(self.tmp.name, [IMG % 'old', IMG % 'fresh', MAT % 'm', DONE % 'mod'])
        report = run(path, baseline=base)
        self.assertEqual(codes(report, 'warn'), [])
        new = find(report, 'LOG-NEW-SUBSTITUTION')
        self.assertEqual([f['asset'] for f in new], ['fresh'])
        self.assertEqual(new[0]['severity'], 'error')
        self.assertEqual(find(report, 'LOG-KNOWN-SUBSTITUTIONS')[0]['evidence'], {'image_not_found': 1, 'material_missing': 1,
                                                                                  'material_empty_image': 0})
        self.assertEqual(find(report, 'LOG-FIXED-SINCE-BASELINE')[0]['evidence']['count'], 1)

    def test_same_log_has_no_errors(self):
        path = log(self.tmp.name, [IMG % 'a', MAT % 'b', DONE % 'mod'])
        base = os.path.join(self.tmp.name, 'out', 'b.json')
        os.makedirs(os.path.dirname(base))
        gate.write_baseline(base, gate.parse_log(path), 'mod', 'accepted')
        report = run(path, baseline=base)
        self.assertEqual(report.counts()['error'], 0)
        self.assertEqual(codes(report), ['LOG-KNOWN-SUBSTITUTIONS'])

    def test_more_than_fifty_new_are_aggregated(self):
        base = self.baseline([])
        path = log(self.tmp.name, [IMG % ('n%03d' % i) for i in range(60)] + [DONE % 'mod'])
        new = find(run(path, baseline=base), 'LOG-NEW-SUBSTITUTION')
        self.assertEqual(len(new), 51)
        self.assertEqual(new[-1]['evidence']['count'], 10)

    def test_bad_baseline_file_is_an_error(self):
        path = log(self.tmp.name, [DONE % 'mod'])
        wrong = write(self.tmp.name, 'wrong.json', '{"schema": "other"}')
        self.assertEqual(codes(run(path, baseline=wrong), 'error'), ['LOG-BASELINE-FILE'])

    def test_write_refuses_overwrite_and_git_work_tree(self):
        path = log(self.tmp.name, [IMG % 'a', DONE % 'mod'])
        parsed = gate.parse_log(path)
        target = os.path.join(self.tmp.name, 'free.json')
        doc = gate.write_baseline(target, parsed, 'mod', 'why')
        self.assertEqual(doc['entries'], [['image-not-found', 'a']])
        with self.assertRaises(ValueError) as caught:
            gate.write_baseline(target, parsed, 'mod', 'why')
        self.assertIn('never overwritten', str(caught.exception))
        write(self.tmp.name, 'repo/.git/HEAD', 'ref')
        with self.assertRaises(ValueError) as caught:
            gate.write_baseline(os.path.join(self.tmp.name, 'repo', 'sub', 'b.json'), parsed, 'mod', 'why')
        self.assertIn('git work tree', str(caught.exception))
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, 'repo', 'sub', 'b.json')))


class CommandLineTest(unittest.TestCase):
    def test_exit_codes_and_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = log(tmp, [DONE % 'mod'], 'good.log')
            warn = log(tmp, [IMG % 'a', DONE % 'mod'], 'warn.log')
            bad = log(tmp, ['[ INFO ][ a::b ]: nothing'], 'bad.log')
            out = os.path.join(tmp, 'out.json')
            stream = io.StringIO()
            old, sys.stdout = sys.stdout, stream
            try:
                self.assertEqual(gate.main([good, '--json', out]), 0)
                self.assertEqual(gate.main([warn]), 0)
                self.assertEqual(gate.main([warn, '--strict']), 2)
                self.assertEqual(gate.main([bad]), 1)
            finally:
                sys.stdout = old
            self.assertEqual(common.load_json(out)['tool'], 'buildlog-gate')

    def test_write_baseline_command_refuses_incomplete_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = log(tmp, [IMG % 'a'], 'bad.log')
            target = os.path.join(tmp, 'b.json')
            old, sys.stdout, err = sys.stdout, io.StringIO(), sys.stderr
            sys.stderr = io.StringIO()
            try:
                code = gate.main([bad, '--write-baseline', target])
            finally:
                sys.stdout, sys.stderr = old, err
            self.assertNotEqual(code, 0)
            self.assertFalse(os.path.exists(target))

    def test_runs_isolated(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = log(tmp, [DONE % 'mod'])
            done = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'zt_buildlog_gate.py'), good],
                                  capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)


if __name__ == '__main__':
    unittest.main()

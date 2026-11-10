"""Synthetic tests for iw7_zone_readback.py (no game data, no ZoneTool, no .ff)."""
import copy
import io
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 't7-weapons'))
import iw7_audit_common as common  # noqa: E402
import iw7_vfx  # noqa: E402
import iw7_zone_readback as zone  # noqa: E402


def write(root, rel, data):
    path = os.path.join(root, *rel.split('/'))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = 'wb' if isinstance(data, bytes) else 'w'
    with open(path, mode, **({} if isinstance(data, bytes) else {'encoding': 'utf-8', 'newline': '\n'})) as handle:
        handle.write(data if isinstance(data, (bytes, str)) else json.dumps(data))
    return path


def xab(frames=30, rate=30.0, name=b'probe'):
    header = bytearray(136)
    struct.pack_into('<f', header, 100, rate)
    struct.pack_into('<f', header, 104, 1.0)
    struct.pack_into('<H', header, 116, frames)
    header[118] = 1
    return b'\x08\x01' + struct.pack('<I', 1) + bytes(header) + b'\x06\x01' + name + b'\0'


class Zone:
    """A source csv, a source tree and a dump folder in a temporary directory."""

    def __init__(self, test):
        self.tmp = tempfile.TemporaryDirectory()
        test.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name
        self.source_csv = os.path.join(self.root, 'zone_source', 'mod.csv')
        self.tree = os.path.join(self.root, 'zonetool', 'mod')
        self.dump = os.path.join(self.root, 'dump', 'mod')
        os.makedirs(self.tree)
        os.makedirs(self.dump)
        self.source_rows, self.dump_rows = [], []

    def asset(self, kind, name, source=None, dumped=None, folder=None, ext='.json', in_source=True, in_dump=True):
        folder = folder or zone.TYPES[kind][0]
        if in_source:
            self.source_rows.append('%s,%s' % (kind, name))
        if in_dump:
            self.dump_rows.append('%s,%s' % (kind, name))
        for base, content in ((self.tree, source), (self.dump, dumped)):
            if content is not None:
                write(base, '%s/%s%s' % (folder, name, ext), content)

    def audit(self, **kw):
        write(self.root, 'zone_source/mod.csv', '\n'.join(['require,cp_zmb'] + self.source_rows) + '\n')
        if self.dump_rows is not None:
            write(self.dump, 'mod.csv', '\n'.join(self.dump_rows) + '\n')
        return zone.audit(self.source_csv, self.tree, self.dump, common.Intent(), **kw)


def codes(report, severity=None):
    return [f['code'] for f in report.findings if severity in (None, f['severity'])]


def find(report, code):
    return [f for f in report.findings if f['code'] == code]


class ListsTest(unittest.TestCase):
    def test_dump_without_csv_is_incomplete(self):
        z = Zone(self)
        z.asset('weapon', 'w', {'a': 1})
        z.dump_rows = None
        self.assertEqual(codes(z.audit(), 'error'), ['ZONE-DUMP-INCOMPLETE'])

    def test_empty_dump_csv_is_incomplete(self):
        z = Zone(self)
        z.asset('weapon', 'w', {'a': 1}, in_dump=False)
        self.assertEqual(codes(z.audit(), 'error'), ['ZONE-DUMP-INCOMPLETE'])

    def test_directive_rows_are_facts_and_flagged_dump_rows_count_as_present(self):
        z = Zone(self)
        z.source_rows.append('ignore,other_zone')
        z.asset('weapon', 'w', {'a': 1}, {'a': 1})
        z.dump_rows.append('image,,flagged')
        z.source_rows.append('image,flagged')
        report = z.audit()
        self.assertEqual(report.facts['directives'], {'require': 1, 'ignore': 1})
        self.assertEqual(codes(report, 'error'), [])

    def test_asked_for_but_not_in_dump_is_an_error_and_extras_are_info(self):
        z = Zone(self)
        z.asset('weapon', 'kept', {'a': 1}, {'a': 1})
        z.asset('weapon', 'lost', {'a': 1}, in_dump=False)
        z.asset('xanim', 'extra', None, None, in_source=False)
        report = z.audit()
        lost = find(report, 'ZONE-ASSET-NOT-LOADED')
        self.assertEqual([f['asset'] for f in lost], ['lost'])
        self.assertEqual(lost[0]['severity'], 'error')
        self.assertEqual(find(report, 'ZONE-ASSET-ADDED')[0]['evidence']['count'], 1)

    def test_a_dump_limited_to_some_kinds_does_not_judge_the_other_kinds(self):
        z = Zone(self)
        z.asset('weapon', 'kept', {'a': 1}, {'a': 1})
        z.asset('weapon', 'lost', {'a': 1}, in_dump=False)
        z.asset('xanim', 'not_dumped', None, None, in_dump=False)
        report = z.audit(types=['Weapon '])
        self.assertEqual([f['asset'] for f in find(report, 'ZONE-ASSET-NOT-LOADED')], ['lost'])
        outside = find(report, 'ZONE-KIND-NOT-DUMPED')
        self.assertEqual(outside[0]['severity'], 'info')
        self.assertEqual(outside[0]['evidence']['counts'], {'xanim': 1})
        self.assertEqual(len(find(z.audit(), 'ZONE-ASSET-NOT-LOADED')), 2)

    def test_more_than_thirty_missing_are_aggregated_per_type(self):
        z = Zone(self)
        z.asset('weapon', 'present', {'a': 1}, {'a': 1})
        for i in range(35):
            z.asset('weapon', 'w%02d' % i, {'a': i}, in_dump=False)
        for i in range(3):
            z.asset('xanim', 'x%d' % i, None, None, in_dump=False)
        missing = find(z.audit(), 'ZONE-ASSET-NOT-LOADED')
        self.assertEqual(len(missing), 30 + 2)
        self.assertEqual(sorted(f['evidence']['count'] for f in missing if 'count' in f['evidence']), [3, 5])


class ValueTest(unittest.TestCase):
    def test_changed_number_is_a_warning_with_both_values(self):
        z = Zone(self)
        z.asset('weapon', 'w', {'weapDef': {'iFireTime': 330, 'name': 'x'}}, {'weapDef': {'iFireTime': 337, 'name': 'x'}})
        report = z.audit()
        diff = find(report, 'ZONE-VALUE-DIFFERS')
        self.assertEqual(len(diff), 1)
        self.assertEqual(diff[0]['severity'], 'warn')
        self.assertEqual(diff[0]['proof'], 'data')
        self.assertEqual(diff[0]['evidence']['differences'], [['weapDef.iFireTime', 330, 337]])
        self.assertIn('iFireTime', diff[0]['message'])

    def test_float_text_round_trip_is_not_a_difference(self):
        z = Zone(self)
        z.asset('weapon', 'w', '{"f": 0.1, "g": 2.5, "b": true, "c": false}',
                '{"f": 0.10000000149011612, "g": 2.5000001, "b": 1, "c": 0}')
        self.assertEqual(codes(z.audit()), [])

    def test_integers_must_match_exactly(self):
        self.assertTrue(zone.equal_values(1, 1.0))
        self.assertFalse(zone.equal_values(16777217, 16777216))
        self.assertTrue(zone.equal_values(16777217.0, 16777216.0))
        self.assertFalse(zone.equal_values(0.1, 0.2))
        self.assertFalse(zone.equal_values('1', 1))
        self.assertTrue(zone.equal_values(True, 1))

    def test_leaf_on_one_side_counts_unless_empty(self):
        z = Zone(self)
        z.asset('weapon', 'w', {'same': 1, 'zero': 0, 'blank': '', 'nothing': None, 'list': [], 'only_source': 5},
                {'same': 1, 'only_dump': 'x'})
        report = z.audit()
        diff = find(report, 'ZONE-VALUE-DIFFERS')[0]
        # a value written in the source and gone from the compiled file is the fault; a value the builder
        # filled in where the source wrote nothing is a fact
        self.assertEqual(sorted(d[0] for d in diff['evidence']['differences']), ['only_source'])
        self.assertEqual(len(find(report, 'ZONE-VALUE-FILLED')), 1)

    def test_values_filled_in_by_the_builder_are_not_a_warning(self):
        z = Zone(self)
        z.asset('soundbank', 'b', {'name': 'b'}, {'name': 'b', 'ADSRSettings': ['sound/b.adsr.csv']})
        z.asset('soundbank', 'c', {'name': 'c'}, {'name': 'c', 'ADSRSettings': ['sound/c.adsr.csv']})
        report = z.audit()
        self.assertEqual(find(report, 'ZONE-VALUE-DIFFERS'), [])
        filled = find(report, 'ZONE-VALUE-FILLED')
        self.assertEqual(len(filled), 1)
        self.assertIn('2 value(s) in 2 asset(s)', filled[0]['message'])

    def bank(self, source_tables, dump_tables, source_lists=None, dump_lists=None):
        z = Zone(self)
        for base, tables in ((z.tree, source_tables), (z.dump, dump_tables)):
            for rel, text in tables.items():
                write(base, rel, text)
        z.asset('soundbank', 'b', {'aliases': source_lists or sorted(source_tables)},
                {'aliases': dump_lists or sorted(dump_tables)})
        return z.audit()

    def test_tables_merged_by_the_builder_are_compared_row_by_row(self):
        head = 'Name,File,Volume\n'
        report = self.bank({'sound/a.csv': head + 'shot,a.wav,0.5\n', 'sound/c.csv': head + 'Reload,r.wav,\n'},
                           {'sound/b.csv': head + 'shot,a.wav,0.500000\nreload,r.wav,0\n'})
        self.assertEqual(codes(report), ['ZONE-TABLES-SAME'])
        self.assertIn('2 named row(s) of 2 source table(s)', find(report, 'ZONE-TABLES-SAME')[0]['message'])

    def test_a_table_row_missing_from_the_compiled_table_is_an_error(self):
        head = 'Name,File,Volume\n'
        report = self.bank({'sound/a.csv': head + 'shot,a.wav,1\nreload,r.wav,1\n'},
                           {'sound/a.csv': head + 'shot,a.wav,1\nextra,e.wav,1\n'})
        lost = find(report, 'ZONE-ROW-NOT-LOADED')[0]
        self.assertEqual((lost['severity'], lost['evidence']['rows']), ('error', ['reload']))
        self.assertEqual(find(report, 'ZONE-ROW-ADDED')[0]['evidence']['count'], 1)
        self.assertEqual(find(report, 'ZONE-TABLES-SAME'), [])

    def test_a_table_value_changed_in_the_compiled_table_is_a_warning(self):
        head = 'Name,File,Volume\n'
        report = self.bank({'sound/a.csv': head + 'shot,a.wav,1\nshot,b.wav,1\nloop,l.wav,1\n'},
                           {'sound/a.csv': head + 'shot,a.wav,0.2\nshot,b.wav,1\n' + 'loop,l.wav,1\n' * 2})
        differs = find(report, 'ZONE-ROW-DIFFERS')[0]
        self.assertEqual(differs['severity'], 'warn')
        self.assertEqual(sorted(d[0] for d in differs['evidence']['differences']),
                         ['loop (number of rows)', 'shot.Volume'])

    def test_a_listed_table_that_cannot_be_read_leaves_the_lists_compared_as_written(self):
        head = 'Name,File\n'
        report = self.bank({'sound/a.csv': head + 'shot,a.wav\n'}, {'sound/a.csv': head + 'shot,a.wav\n'},
                           source_lists=['sound/a.csv', 'sound/gone.csv'], dump_lists=['sound/a.csv'])
        self.assertEqual(codes(report), ['ZONE-VALUE-DIFFERS'])
        report = self.bank({'sound/a.csv': head}, {'sound/a.csv': head}, source_lists=['../outside.csv'])
        self.assertEqual(codes(report), ['ZONE-VALUE-DIFFERS'])

    def test_a_value_the_compiled_format_does_not_carry_is_not_a_warning(self):
        z = Zone(self)
        z.asset('sfxpkg', 'p', {'sounds': {'name': 'p', 'fire': 'a'}}, {'sounds': {'name': '', 'fire': 'a'}})
        report = z.audit()
        self.assertEqual(find(report, 'ZONE-VALUE-DIFFERS'), [])
        self.assertEqual(len(find(report, 'ZONE-VALUE-NOT-CARRIED')), 1)
        # the same path in another kind, or another value lost, stays a warning
        z2 = Zone(self)
        z2.asset('weapon', 'w', {'sounds': {'name': 'p'}}, {'sounds': {'name': ''}})
        z2.asset('sfxpkg', 'q', {'sounds': {'name': 'q', 'fire': 'a'}}, {'sounds': {'name': '', 'fire': ''}})
        self.assertEqual(len(find(z2.audit(), 'ZONE-VALUE-DIFFERS')), 2)

    def test_only_first_eight_differences_are_listed(self):
        z = Zone(self)
        z.asset('weapon', 'w', {'k%d' % i: i for i in range(12)}, {'k%d' % i: i + 100 for i in range(12)})
        diff = find(z.audit(), 'ZONE-VALUE-DIFFERS')[0]
        self.assertEqual(diff['evidence']['count'], 12)
        self.assertEqual(len(diff['evidence']['differences']), 8)

    def test_noise_entries_are_accepted_and_counted(self):
        z = Zone(self)
        z.asset('weapon', 'w', {'a': {'b': 1, 'ptr': 5}}, {'a': {'b': 2, 'ptr': 9}})
        noise = write(z.root, 'noise.json', {
            'schema': zone.NOISE_SCHEMA, 'entries': [
                {'kind': 'weapon', 'path': 'a.ptr', 'why': 'pointer values differ in every build'}]})
        report = z.audit(noise=noise)
        diff = find(report, 'ZONE-VALUE-DIFFERS')[0]
        self.assertEqual(diff['evidence']['count'], 1)
        self.assertEqual(find(report, 'ZONE-NOISE-ACCEPTED')[0]['evidence']['count'], 1)

    def test_noise_all_accepted_leaves_no_warning(self):
        z = Zone(self)
        z.asset('weapon', 'w', {'a': 1}, {'a': 2})
        noise = write(z.root, 'noise.json', {
            'schema': zone.NOISE_SCHEMA, 'entries': [{'kind': 'weapon', 'path': '*', 'why': 'everything is noise here'}]})
        report = z.audit(noise=noise)
        self.assertEqual(codes(report, 'warn'), [])
        self.assertEqual(codes(report), ['ZONE-NOISE-ACCEPTED'])

    def test_noise_entry_without_reason_is_ignored_and_reported(self):
        z = Zone(self)
        z.asset('weapon', 'w', {'a': 1}, {'a': 2})
        noise = write(z.root, 'noise.json', {
            'schema': zone.NOISE_SCHEMA, 'entries': [{'kind': 'weapon', 'path': '*', 'why': '  '},
                                                     {'kind': 'xanim', 'path': '*'}]})
        report = z.audit(noise=noise)
        self.assertEqual(codes(report, 'error'), ['ZONE-NOISE-FILE', 'ZONE-NOISE-FILE'])
        self.assertEqual(len(find(report, 'ZONE-VALUE-DIFFERS')), 1)

    def test_declared_decision_closes_the_warning(self):
        z = Zone(self)
        z.asset('weapon', 'w', {'a': 1}, {'a': 2})
        report = z.audit()
        intent = common.Intent()
        intent.items['w'] = {'decisions': {'finding:ZONE-VALUE-DIFFERS': {'keep': True, 'why': 'loader rounds it'}}}
        report.answer(intent)
        self.assertEqual(report.counts()['warn'], 0)

    def test_unparsable_json_is_a_binary_difference(self):
        z = Zone(self)
        z.asset('weapon', 'w', {'a': 1}, '{ not json')
        self.assertEqual(codes(z.audit(), 'warn'), ['ZONE-BINARY-DIFFERS'])

    def test_identical_json_is_counted_not_reported(self):
        z = Zone(self)
        z.asset('weapon', 'w', {'a': 1}, {'a': 1})
        report = z.audit()
        self.assertEqual(codes(report), [])
        self.assertEqual(report.facts['types']['weapon'], {'source_csv': 1, 'dump_csv': 1, 'compared': 1, 'identical': 1})


class BinaryTest(unittest.TestCase):
    def test_identical_bytes(self):
        z = Zone(self)
        z.asset('xmodel', 'm', b'\x01\x02', b'\x01\x02', ext='.xmb')
        row = find(z.audit(), 'ZONE-BINARY-SUMMARY')[0]['evidence']
        self.assertEqual((row['identical'], row['not_compared']), (1, 0))

    def test_kind_without_decoder_is_not_compared_and_not_a_pass(self):
        z = Zone(self)
        z.asset('xmodel', 'm', b'\x01\x02', b'\x01\x03', ext='.xmb')
        report = z.audit()
        row = find(report, 'ZONE-BINARY-SUMMARY')[0]
        self.assertEqual(row['evidence']['not_compared'], 1)
        self.assertIn('not compared', row['message'])
        self.assertEqual(report.facts['types']['xmodel']['identical'], 0)
        self.assertEqual(codes(report, 'warn'), [])

    def test_xab_same_after_decoding_and_different(self):
        z = Zone(self)
        z.asset('xanim', 'same', xab(30, 30.0, b'one'), xab(30, 30.0, b'other'), ext='.xab')
        z.asset('xanim', 'other', xab(30, 30.0), xab(45, 30.0), ext='.xab')
        report = z.audit()
        row = find(report, 'ZONE-BINARY-SUMMARY')[0]['evidence']
        self.assertEqual((row['same_decoded'], row['differs']), (1, 1))
        diff = find(report, 'ZONE-BINARY-DIFFERS')
        self.assertEqual([f['asset'] for f in diff], ['other'])

    def test_vfx_ignores_pointer_values_but_not_content(self):
        model = iw7_vfx.new_model('a')
        moved = copy.deepcopy(model)
        moved['system']['name@ptr'] = '0x123450'
        renamed = iw7_vfx.new_model('b')
        z = Zone(self)
        z.asset('vfx', 'v/same', iw7_vfx.encode(model), iw7_vfx.encode(moved), folder='particlesystem', ext='.iw7VFX')
        z.asset('vfx', 'v/other', iw7_vfx.encode(model), iw7_vfx.encode(renamed), folder='particlesystem', ext='.iw7VFX')
        z.asset('vfx', 'v/broken', b'junk', iw7_vfx.encode(model), folder='particlesystem', ext='.iw7VFX')
        report = z.audit()
        row = find(report, 'ZONE-BINARY-SUMMARY')[0]['evidence']
        self.assertEqual((row['same_decoded'], row['differs'], row['not_compared']), (1, 1, 1))
        self.assertEqual([f['asset'] for f in find(report, 'ZONE-BINARY-DIFFERS')], ['v/other'])

    def test_image_in_another_format_is_not_compared(self):
        z = Zone(self)
        z.asset('image', 'i', b'DDS data', b'IW7 image', ext='.dds', in_dump=True)
        write(z.dump, 'images/i.iw7Image', b'IW7 image')
        report = z.audit()
        self.assertEqual(find(report, 'ZONE-BINARY-SUMMARY')[0]['evidence']['not_compared'], 1)

    def test_same_file_is_not_a_difference(self):
        z = Zone(self)
        z.tree = z.dump
        z.asset('xmodel', 'm', b'\x01\x02', None, ext='.xmb')
        write(z.dump, 'xmodel/m.xmb', b'\x01\x02')
        self.assertEqual(find(z.audit(), 'ZONE-BINARY-SUMMARY')[0]['evidence']['identical'], 1)


class MissingSourceTest(unittest.TestCase):
    def test_asset_without_source_file_is_info(self):
        z = Zone(self)
        z.asset('material', 'from/stock', None, {'a': 1})
        z.asset('weapon', 'built', {'a': 1}, {'a': 1})
        report = z.audit()
        self.assertEqual(find(report, 'ZONE-SOURCE-MISSING')[0]['evidence']['count'], 1)
        self.assertEqual(report.facts['source_missing'], {'material': 1})
        self.assertEqual(codes(report, 'warn'), [])

    def test_unmapped_types_are_counted_not_compared(self):
        z = Zone(self)
        z.source_rows += ['techset,t1', 'techset,t2', 'rawfile,r']
        z.dump_rows += ['techset,,t1', 'techset,,t2', 'rawfile,r']
        report = z.audit()
        found = find(report, 'ZONE-KIND-NOT-COMPARED')[0]
        self.assertEqual(found['evidence']['counts'], {'rawfile': 1, 'techset': 2})

    def test_dump_without_file_is_info(self):
        z = Zone(self)
        z.asset('weapon', 'w', {'a': 1}, None)
        self.assertEqual(find(z.audit(), 'ZONE-DUMP-NO-FILE')[0]['evidence']['count'], 1)


class LogTest(unittest.TestCase):
    def log(self, z, lines):
        return write(z.root, 'verify.log', '\n'.join(lines) + '\n')

    def test_asset_never_loaded_is_an_error_from_the_log(self):
        z = Zone(self)
        z.asset('weapon', 'ok', {'a': 1}, {'a': 1})
        z.asset('weapon', 'never', {'a': 1}, {'a': 1})
        z.asset('xanim', 'comma', None, None)
        log = self.log(z, [
            '[ INFO ][ zonetool::iw7::dump_asset ]: Loading asset "ok" of type weapon.',
            '[ INFO ][ zonetool::iw7::dump_asset ]: Loading asset ",comma" of type xanim.'])
        errors = find(z.audit(log=log), 'ZONE-ASSET-NOT-LOADED')
        self.assertEqual([f['asset'] for f in errors], ['never'])
        self.assertEqual(errors[0]['source'], 'log')

    def test_not_duplicated_when_the_dump_already_lacks_it(self):
        z = Zone(self)
        z.asset('weapon', 'lost', {'a': 1}, in_dump=False)
        z.asset('weapon', 'ok', {'a': 1}, {'a': 1})
        log = self.log(z, ['[ INFO ][ a::b ]: Loading asset "ok" of type weapon.'])
        self.assertEqual(len(find(z.audit(log=log), 'ZONE-ASSET-NOT-LOADED')), 1)

    def test_loader_errors_one_per_distinct_text(self):
        z = Zone(self)
        z.asset('weapon', 'ok', {'a': 1}, {'a': 1})
        log = self.log(z, ['[ INFO ][ a::b ]: Loading asset "ok" of type weapon.',
                           '[ ERROR ][ a::b ]: broken thing', '[ ERROR ][ a::b ]: broken thing',
                           '[ FATAL ][ a::c ]: crash', '[ WARNING ][ a::c ]: only a warning'])
        found = find(z.audit(log=log), 'ZONE-LOAD-ERROR')
        self.assertEqual(sorted(f['evidence']['count'] for f in found), [1, 2])

    def test_log_without_asset_lines_is_a_note_not_a_flood(self):
        z = Zone(self)
        z.asset('weapon', 'ok', {'a': 1}, {'a': 1})
        log = self.log(z, ['[ INFO ][ a::b ]: nothing useful'])
        report = z.audit(log=log)
        self.assertEqual(codes(report, 'error'), [])
        self.assertIn('ZONE-LOG-NO-ASSETS', codes(report))


class CommandLineTest(unittest.TestCase):
    def test_exit_codes(self):
        good = Zone(self)
        good.asset('weapon', 'w', {'a': 1}, {'a': 1})
        write(good.root, 'zone_source/mod.csv', 'weapon,w\n')
        write(good.dump, 'mod.csv', 'weapon,w\n')
        args = ['--source-csv', good.source_csv, '--source-tree', good.tree, '--dump', good.dump]
        old, sys.stdout = sys.stdout, io.StringIO()
        try:
            self.assertEqual(zone.main(args), 0)
            write(good.dump, 'mod.csv', 'xanim,other\n')
            self.assertEqual(zone.main(args), 1)
        finally:
            sys.stdout = old

    def test_runs_isolated(self):
        z = Zone(self)
        z.asset('weapon', 'w', {'a': 1}, {'a': 1})
        z.audit()
        done = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'iw7_zone_readback.py'), '--source-csv',
                               z.source_csv, '--source-tree', z.tree, '--dump', z.dump], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr + done.stdout)


if __name__ == '__main__':
    unittest.main()

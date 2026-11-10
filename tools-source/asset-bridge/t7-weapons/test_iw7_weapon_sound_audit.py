"""Synthetic tests for iw7_weapon_sound_audit.py (no game data, no ffmpeg)."""
import io
import json
import math
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iw7_audit_common as common  # noqa: E402
import iw7_weapon_sound_audit as audit  # noqa: E402

COLUMNS = ['Name', 'SecondaryAliasName', 'File', 'vol_min', 'vol_max', 'channel', 'type']


def write(root, rel, data):
    path = os.path.join(root, *rel.split('/'))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = 'wb' if isinstance(data, bytes) else 'w'
    with open(path, mode, **({} if isinstance(data, bytes) else {'encoding': 'utf-8', 'newline': '\n'})) as handle:
        handle.write(data if isinstance(data, (bytes, str)) else json.dumps(data))
    return path


def row(name, file=None, secondary='', vol=0.5, channel='weap_plr_fire_overlap_2d', kind='hybrid_pcm'):
    return [name, secondary, file if file is not None else 'w/' + name, str(vol), str(vol), channel, kind]


def csv_text(rows):
    return '\n'.join(','.join(line) for line in [COLUMNS] + rows) + '\n'


def bank(zone, magic=audit.BANK_MAGIC, version=4):
    fields = [magic, version, 0, 0, 0, 0, 0, 0, 0, 0, 0, b'', b'', 0, 0, zone.encode(), b'', b'', 0, 0, b'']
    return struct.pack(audit.BANK_STRUCT, *fields)


def make_tree(root, aliases, sounds=None, profile=None, assets=None, name='w', bank_zone=None):
    """A mod tree with one weapon `name` whose package names `sounds` (slot -> alias)."""
    write(root, 'weapons/%s.json' % name, {'weapDef': {'sfxPackage': name + '_pkg'}})
    pkg = dict(profile or {'szAdsrBaseSetting': 'iw7_long', 'szWeapSndReflectionClass': ''})
    pkg['sounds'] = sounds if sounds is not None else {'fireSoundPlayer': aliases[0][0]}
    write(root, 'sfxpkg/%s_pkg.json' % name, pkg)
    write(root, 'sound/%s.aliases.csv' % name, csv_text(aliases))
    for rel, data in (assets or {}).items():
        write(root, 'sound_assets/' + rel, data)
    if bank_zone is not None:
        write(root, 'soundbank/b.json', {'name': 'b', 'zone': bank_zone, 'aliases': []})
    return root


def make_stock(root, chains=30, sharing=0, kind='hybrid_pcm', vol=0.4):
    """A stock zone with `chains` two-layer player fire chains, `sharing` of them on one channel."""
    zone = os.path.join(root, 'szone')
    rows = []
    for number in range(chains):
        second = 'weap_plr_fire_overlap_2d' if number < sharing else 'weap_plr_fire_2_2d'
        rows.append(row('s%d_plr' % number, 's/a%d' % number, secondary='s%d_mech' % number, vol=vol, kind=kind))
        rows.append(row('s%d_mech' % number, 's/b%d' % number, vol=vol, channel=second, kind=kind))
        write(zone, 'sfxpkg/s%d.json' % number, {'sounds': {'fireSoundPlayer': 's%d_plr' % number,
                                                           'pickupSound': 'stock_only_pickup'},
                                                 'szAdsrBaseSetting': 'iw7_short', 'szWeapSndReflectionClass': 'smg'})
    write(zone, 'sound/szone.all.aliases.csv', csv_text(rows))
    return common.StockDump([zone])


def codes(report, severity=None, code=None):
    return [f for f in report.findings if (severity is None or f['severity'] == severity)
            and (code is None or f['code'] == code)]


def run(tree, stock=None, intent=None, **options):
    options.setdefault('measure', False)
    return audit.audit(tree, stock or common.StockDump([]), intent or common.Intent(), **options)


FLAT = [row('w_fire', vol=0.5, secondary='w_layer'), row('w_layer', vol=0.5, channel='weap_plr_fire_2_2d')]


class BankTest(unittest.TestCase):
    def test_header_reader(self):
        with tempfile.TemporaryDirectory() as temp:
            path = write(temp, 'mod.sabl', bank('mod'))
            self.assertEqual(audit.read_bank_header(path), ('mod', 4))
            with self.assertRaises(ValueError):
                audit.read_bank_header(write(temp, 'x.sabl', bank('mod', magic=1)))
            with self.assertRaises(ValueError):
                audit.read_bank_header(write(temp, 'short.sabl', b'1234'))

    def test_zone_must_equal_loads_as_or_the_stem(self):
        with tempfile.TemporaryDirectory() as temp:
            tree = make_tree(os.path.join(temp, 'tree'), FLAT)
            wrong = write(temp, 'a/mod.sabl', bank('bo3wpn'))
            right = write(temp, 'b/mod.sabs', bank('mod'))
            report = run(tree, banks=[wrong, right], loads_as='mod')
            hits = codes(report, 'error', 'SND-BANK-ZONE')
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]['evidence']['header'], 'bo3wpn')
            self.assertIn('bank header says "bo3wpn" but the game asks for "mod"', hits[0]['message'])
            report = run(tree, banks=[write(temp, 'c/mod.sabl', bank('mod')), write(temp, 'c/other.sabl', bank('mod'))])
            self.assertEqual([f['asset'] for f in codes(report, 'error', 'SND-BANK-ZONE')], ['other.sabl'])

    def test_unreadable_bank(self):
        with tempfile.TemporaryDirectory() as temp:
            tree = make_tree(os.path.join(temp, 'tree'), FLAT)
            report = run(tree, banks=[write(temp, 'mod.sabl', bank('mod', magic=7)), os.path.join(temp, 'absent.sabl')])
            self.assertEqual(len(codes(report, 'error', 'SND-BANK-UNREADABLE')), 2)

    def test_json_zone_only_with_loads_as(self):
        with tempfile.TemporaryDirectory() as temp:
            tree = make_tree(os.path.join(temp, 'tree'), FLAT, bank_zone='bo3wpn')
            self.assertEqual(len(codes(run(tree, loads_as='mod'), 'error', 'SND-BANK-JSON-ZONE')), 1)
            self.assertEqual(codes(run(tree), None, 'SND-BANK-JSON-ZONE'), [])
            tree = make_tree(os.path.join(temp, 'ok'), FLAT, bank_zone='mod')
            self.assertEqual(codes(run(tree, loads_as='mod'), None, 'SND-BANK-JSON-ZONE'), [])


class SampleTest(unittest.TestCase):
    def tree(self, temp, files, rows=FLAT, **kw):
        return make_tree(os.path.join(temp, 'tree'), rows, assets=files, **kw)

    def test_missing_sample_is_an_error_only_when_the_tree_has_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            tree = self.tree(temp, {'w/w_fire.flac': b'x'})
            hits = codes(run(tree), 'error', 'SND-SAMPLE-MISSING')
            self.assertEqual([h['evidence']['alias'] for h in hits], ['w_layer'])
            self.assertEqual(hits[0]['asset'], 'w.aliases.csv')
        with tempfile.TemporaryDirectory() as temp:
            tree = make_tree(os.path.join(temp, 'tree'), FLAT)
            self.assertEqual(codes(run(tree), None, 'SND-SAMPLE-MISSING'), [])

    def test_backslash_files_and_clean_case(self):
        with tempfile.TemporaryDirectory() as temp:
            rows = [row('w_fire', file='bo3\\gun\\w_fire', kind='loaded')]
            tree = self.tree(temp, {'bo3/gun/w_fire.flac': b'x'}, rows=rows)
            self.assertEqual(codes(run(tree), 'error'), [])

    def test_stock_pair_is_not_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            stock = make_stock(temp, chains=2)
            rows = [row('s0_plr', file='s/a0', vol=0.4), row('other', file='s/gone')]
            tree = self.tree(temp, {'w/x.flac': b'x'}, rows=rows, sounds={'fireSoundPlayer': 's0_plr'})
            hits = codes(run(tree, stock), 'error', 'SND-SAMPLE-MISSING')
            self.assertEqual([h['evidence']['alias'] for h in hits], ['other'])

    def test_many_missing_are_one_finding_per_table(self):
        with tempfile.TemporaryDirectory() as temp:
            rows = [row('a%d' % n, kind='loaded') for n in range(12)]
            tree = self.tree(temp, {'w/keep.flac': b'x'}, rows=rows, sounds={})
            hits = codes(run(tree), 'error', 'SND-SAMPLE-MISSING')
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]['evidence']['count'], 12)

    def test_pcmhead(self):
        with tempfile.TemporaryDirectory() as temp:
            files = {'w/w_fire.flac': b'x', 'w/w_layer.flac': b'x', 'w/w_layer.pcmhead': b''}
            hits = codes(run(self.tree(temp, files)), 'error', 'SND-PCMHEAD-MISSING')
            self.assertEqual(sorted(h['evidence']['alias'] for h in hits), ['w_fire', 'w_layer'])
        with tempfile.TemporaryDirectory() as temp:
            files = {'w/w_fire.flac': b'x', 'w/w_layer.flac': b'x', 'w/w_fire.pcmhead': bytes(2048),
                     'w/w_layer.pcmhead': bytes(2048)}
            self.assertEqual(codes(run(self.tree(temp, files)), 'error'), [])
        with tempfile.TemporaryDirectory() as temp:
            rows = [row('w_fire', kind='loaded')]      # only hybrid_pcm needs a header
            self.assertEqual(codes(run(self.tree(temp, {'w/w_fire.flac': b'x'}, rows=rows)), 'error'), [])


class LevelTest(unittest.TestCase):
    def fake(self, table):
        return lambda path: table.get(os.path.basename(path)) or None

    def tree(self, temp, rows, **kw):
        files = {r[2] + '.flac': b'x' for r in rows}
        return make_tree(os.path.join(temp, 'tree'), rows, assets=files, **kw)

    def test_chain_level_power_sum_and_variants_average(self):
        with tempfile.TemporaryDirectory() as temp:
            rows = [row('w_fire', file='f1', secondary='w_layer', vol=1.0, kind='loaded'),
                    row('w_fire', file='f2', secondary='w_layer', vol=0.5, kind='loaded'),
                    row('w_layer', file='f3', vol=1.0, channel='weap_plr_fire_2_2d', kind='loaded')]
            measure = self.fake({'f1.flac': (-20.0, 2), 'f2.flac': (-20.0, 2), 'f3.flac': (-20.0, 1)})
            report = run(self.tree(temp, rows), measure=measure)
            level = report.facts['fire_levels']['w']['w_fire']
            variants = (-20.0 + (-20.0 + 20 * math.log10(0.5))) / 2
            expect = 10 * math.log10(10 ** (variants / 10) + 10 ** (-2.0))
            self.assertAlmostEqual(level, expect, places=1)
            info = codes(report, 'info', 'SND-FIRE-LEVEL')
            self.assertEqual(len(info), 1)
            self.assertIn('w_fire', info[0]['message'])
            self.assertEqual(codes(report, None, 'SND-LEVEL-NOT-MEASURED'), [])

    def test_quiet_against_reference_and_against_loudest(self):
        with tempfile.TemporaryDirectory() as temp:
            rows = [row('w_fire', file='f1', vol=1.0, kind='loaded')]
            tree = self.tree(temp, rows, sounds={'fireSoundPlayer': 'w_fire'})
            report = run(tree, measure=self.fake({'f1.flac': (-30.0, 2)}), fire_reference_db=-20.0)
            quiet = codes(report, 'warn', 'SND-FIRE-QUIET')
            self.assertEqual(len(quiet), 1)
            self.assertEqual(quiet[0]['proof'], 'engine')
            self.assertEqual(quiet[0]['evidence']['below_reference_db'], 10.0)
            self.assertEqual([q['kind'] for q in report.questions], ['hear'])
            report = run(tree, measure=self.fake({'f1.flac': (-30.0, 2)}), fire_reference_db=-25.0)
            self.assertEqual(codes(report, None, 'SND-FIRE-QUIET'), [])       # 5 dB below: inside the 6 dB margin
            self.assertEqual(codes(run(tree, measure=self.fake({'f1.flac': (-30.0, 2)})), None, 'SND-FIRE-QUIET'), [])

    def test_quiet_against_the_loudest_weapon_of_the_tree(self):
        with tempfile.TemporaryDirectory() as temp:
            tree = os.path.join(temp, 'tree')
            make_tree(tree, [row('loud', file='l', vol=1.0, kind='loaded')], name='loud', assets={'l.flac': b'x'})
            make_tree(tree, [row('soft', file='s', vol=1.0, kind='loaded')], name='soft', assets={'s.flac': b'x'})
            measure = self.fake({'l.flac': (-10.0, 2), 's.flac': (-20.0, 2)})
            report = run(tree, measure=measure)
            quiet = codes(report, 'warn', 'SND-FIRE-QUIET')
            self.assertEqual([q['asset'] for q in quiet], ['soft'])
            self.assertAlmostEqual(quiet[0]['evidence']['below_loudest_db'], 10.0, places=1)
            only = run(tree, items=['soft'], measure=measure)
            self.assertEqual(codes(only, None, 'SND-FIRE-QUIET'), [])

    def test_never_estimates(self):
        with tempfile.TemporaryDirectory() as temp:
            rows = [row('w_fire', file='f1', secondary='w_layer', kind='loaded'),
                    row('w_layer', file='f2', channel='weap_plr_fire_2_2d', kind='loaded')]
            tree = self.tree(temp, rows)
            for measure in (False, self.fake({'f1.flac': (-20.0, 2)}), lambda path: None):
                report = run(tree, measure=measure)
                self.assertEqual(report.facts['fire_levels'], {})
                self.assertEqual(codes(report, None, 'SND-FIRE-LEVEL'), [])
                self.assertEqual(len(codes(report, 'info', 'SND-LEVEL-NOT-MEASURED')), 1)

    def test_sample_absent_is_not_measured(self):
        with tempfile.TemporaryDirectory() as temp:
            tree = make_tree(os.path.join(temp, 'tree'), [row('w_fire', file='gone', kind='loaded')],
                             assets={'other.flac': b'x'})
            report = run(tree, measure=self.fake({'gone.flac': (-10.0, 2)}))
            self.assertEqual(len(codes(report, 'info', 'SND-LEVEL-NOT-MEASURED')), 1)

    def test_default_measure_runs_ffmpeg_and_survives_its_absence(self):
        self.assertEqual(audit.channel_count('stereo'), 2)
        self.assertEqual(audit.channel_count('mono'), 1)
        self.assertEqual(audit.channel_count('5.1(side)'), 6)
        self.assertEqual(audit.channel_count('4 channels'), 4)
        self.assertIsNone(audit.channel_count('weird'))
        self.assertIsNone(audit.ffmpeg_measure(os.path.join(tempfile.gettempdir(), 'no-such-sample-xyz.flac')))


class ShapeTest(unittest.TestCase):
    def tree(self, temp, rows):
        return make_tree(os.path.join(temp, 'tree'), rows)

    def test_layers_on_one_channel_warn_when_stock_does_not(self):
        with tempfile.TemporaryDirectory() as temp:
            stock = make_stock(temp, chains=30, sharing=0)
            rows = [row('w_fire', secondary='w_layer', channel='weap_plr_fire_1_2d'),
                    row('w_layer', channel='weap_plr_fire_1_2d')]
            report = run(self.tree(temp, rows), stock)
            hits = codes(report, 'warn', 'SND-LAYERS-ONE-CHANNEL')
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]['proof'], 'engine')
            self.assertEqual(hits[0]['evidence']['stock_chains'], 30)
            self.assertEqual(hits[0]['evidence']['stock_sharing'], 0)
            self.assertEqual([q['kind'] for q in report.questions], ['hear'])

    def test_layers_on_distinct_channels_are_silent(self):
        with tempfile.TemporaryDirectory() as temp:
            report = run(self.tree(temp, FLAT), make_stock(temp))
            self.assertEqual(codes(report, None, 'SND-LAYERS-ONE-CHANNEL'), [])

    def test_sharing_is_only_a_note_when_stock_does_it_too(self):
        with tempfile.TemporaryDirectory() as temp:
            stock = make_stock(temp, chains=20, sharing=10)
            rows = [row('w_fire', secondary='w_layer'), row('w_layer')]       # both on overlap
            report = run(self.tree(temp, rows), stock)
            self.assertEqual(codes(report, 'warn', 'SND-LAYERS-ONE-CHANNEL'), [])
            self.assertEqual(len(codes(report, 'info', 'SND-LAYERS-ONE-CHANNEL')), 1)

    def test_a_declared_decision_closes_the_warning(self):
        with tempfile.TemporaryDirectory() as temp:
            stock = make_stock(temp)
            rows = [row('w_fire', secondary='w_layer', channel='c'), row('w_layer', channel='c')]
            decision = {'schema': common.INTENT_SCHEMA, 'item': 'w', 'kind': 'weapon', 'decisions': {
                'finding:SND-LAYERS-ONE-CHANNEL': {'keep': True, 'why': 'the second layer is meant to replace the first'}}}
            intent = common.Intent.load(write(temp, 'intent.json', decision))
            report = run(self.tree(temp, rows), stock, intent).answer(intent)
            self.assertEqual(codes(report, 'warn', 'SND-LAYERS-ONE-CHANNEL'), [])
            closed = codes(report, 'info', 'SND-LAYERS-ONE-CHANNEL')
            self.assertEqual(closed[0]['answered'], 'the second layer is meant to replace the first')

    def test_rare_root_type(self):
        with tempfile.TemporaryDirectory() as temp:
            stock = make_stock(temp, chains=30)
            rows = [row('w_fire', kind='loaded', secondary='w_layer'), row('w_layer', channel='x', kind='loaded')]
            report = run(self.tree(temp, rows), stock)
            hits = codes(report, 'warn', 'SND-FIRE-TYPE-RARE')
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]['evidence']['type'], 'loaded')
            self.assertEqual(hits[0]['proof'], 'engine')
            self.assertEqual(codes(run(self.tree(temp, FLAT), stock), None, 'SND-FIRE-TYPE-RARE'), [])

    def test_volume_position_is_a_note(self):
        with tempfile.TemporaryDirectory() as temp:
            report = run(self.tree(temp, [row('w_fire', vol=0.9)]), make_stock(temp, vol=0.4))
            hit = codes(report, 'info', 'SND-FIRE-VOLUME-POSITION')[0]
            self.assertEqual(hit['evidence']['position'], 'above-all')
            self.assertEqual(hit['evidence']['stock_median'], 0.4)

    def test_no_stock_skips_comparisons_and_says_so_once(self):
        with tempfile.TemporaryDirectory() as temp:
            rows = [row('w_fire', secondary='w_layer', channel='c', kind='loaded'), row('w_layer', channel='c', kind='loaded')]
            report = run(self.tree(temp, rows))
            self.assertEqual(len(codes(report, 'info', 'SND-NO-STOCK')), 1)
            for code in ('SND-LAYERS-ONE-CHANNEL', 'SND-FIRE-TYPE-RARE', 'SND-FIRE-VOLUME-POSITION'):
                self.assertEqual(codes(report, None, code), [])
            self.assertEqual(codes(report, 'error'), [])


class AliasTest(unittest.TestCase):
    def test_missing_alias_with_stock_is_a_warning_for_the_engine(self):
        with tempfile.TemporaryDirectory() as temp:
            stock = make_stock(temp)
            rows = [row('w_fire', secondary='w_gone')]
            tree = make_tree(os.path.join(temp, 'tree'), rows, sounds={'fireSoundPlayer': 'w_fire', 'fireSound': 'nobody'})
            report = run(tree, stock)
            hits = codes(report, 'warn', 'SND-ALIAS-MISSING')
            self.assertEqual(sorted(h['evidence']['alias'] for h in hits), ['nobody', 'w_gone'])
            self.assertEqual({h['proof'] for h in hits}, {'engine'})
            self.assertEqual(codes(report, 'error'), [])
            self.assertEqual(sorted(q['how']['alias'] if 'how' in q else q.get('alias') for q in report.questions
                                    if q['kind'] == 'hear' and 'heard?' in q['question'] and 'is the sound' in q['question']),
                             ['nobody', 'w_gone'])

    def test_an_alias_stock_packages_use_is_a_note_not_an_error(self):
        with tempfile.TemporaryDirectory() as temp:
            stock = make_stock(temp)
            tree = make_tree(os.path.join(temp, 'tree'), FLAT, sounds={'fireSoundPlayer': 'w_fire',
                                                                       'pickupSound': 'stock_only_pickup'})
            report = run(tree, stock)
            self.assertEqual(codes(report, 'error'), [])
            self.assertEqual(len(codes(report, 'info', 'SND-ALIAS-NOT-IN-DUMP')), 1)

    def test_a_missing_layer_behind_a_stock_alias_is_a_note(self):
        with tempfile.TemporaryDirectory() as temp:
            stock = make_stock(temp)
            zone = os.path.join(temp, 'szone', 'sound', 'szone.all.aliases.csv')
            with open(zone, 'a', encoding='utf-8', newline=chr(10)) as handle:
                handle.write(','.join(row('s_open', secondary='s_beyond')) + chr(10))
            stock = common.StockDump([os.path.join(temp, 'szone')])
            tree = make_tree(os.path.join(temp, 'tree'), FLAT, sounds={'fireSoundPlayer': 'w_fire', 'fireSound': 's_open'})
            report = run(tree, stock)
            self.assertEqual(codes(report, 'error'), [])
            self.assertEqual(len(codes(report, 'info', 'SND-ALIAS-NOT-IN-DUMP')), 1)

    def test_a_stock_row_copied_into_the_tree_is_still_stock(self):
        with tempfile.TemporaryDirectory() as temp:
            stock = make_stock(temp)
            copy = [row('s0_plr', file='s/a0', secondary='s_beyond', vol=0.4)]
            tree = make_tree(os.path.join(temp, 'tree'), copy, sounds={'fireSoundPlayer': 's0_plr'})
            self.assertEqual(codes(run(tree, stock), None, 'SND-ALIAS-MISSING'), [])

    def test_without_stock_it_is_only_a_note(self):
        with tempfile.TemporaryDirectory() as temp:
            tree = make_tree(os.path.join(temp, 'tree'), FLAT, sounds={'fireSoundPlayer': 'w_fire', 'fireSound': 'nobody'})
            report = run(tree)
            self.assertEqual(codes(report, 'error'), [])
            self.assertEqual(len(codes(report, 'info', 'SND-ALIAS-NOT-IN-DUMP')), 1)

    def test_aliases_of_the_dump_are_found(self):
        with tempfile.TemporaryDirectory() as temp:
            stock = make_stock(temp)
            tree = make_tree(os.path.join(temp, 'tree'), FLAT, sounds={'fireSoundPlayer': 'w_fire', 'fireSound': 's3_plr'})
            self.assertEqual(codes(run(tree, stock), 'error'), [])


class ProfileTest(unittest.TestCase):
    def test_profile_equal_to_the_template_warns_and_a_changed_one_does_not(self):
        with tempfile.TemporaryDirectory() as temp:
            stock = make_stock(temp)
            same = {'szAdsrBaseSetting': 'iw7_short', 'szWeapSndReflectionClass': 'smg'}
            tree = make_tree(os.path.join(temp, 'a'), FLAT, profile=same)
            self.assertEqual(len(codes(run(tree, stock), 'warn', 'SND-TEMPLATE-GROUP')), 1)
            tree = make_tree(os.path.join(temp, 'b'), FLAT, profile={'szAdsrBaseSetting': 'iw7_long',
                                                                    'szWeapSndReflectionClass': ''})
            self.assertEqual(codes(run(tree, stock), 'warn', 'SND-TEMPLATE-GROUP'), [])


class CommandLineTest(unittest.TestCase):
    def test_main_writes_the_report_and_the_exit_code(self):
        with tempfile.TemporaryDirectory() as temp:
            tree = make_tree(os.path.join(temp, 'tree'), FLAT)
            target = os.path.join(temp, 'out.json')
            old, sys.stdout = sys.stdout, io.StringIO()
            try:
                code = audit.main([tree, '--no-measure', '--json', target, '--bank',
                                   write(temp, 'mod.sabl', bank('bo3wpn')), '--loads-as', 'mod'])
                printed = sys.stdout.getvalue()
            finally:
                sys.stdout = old
            self.assertEqual(code, 1)
            self.assertIn('SND-BANK-ZONE', printed)
            with open(target, encoding='utf-8') as handle:
                data = json.load(handle)
            self.assertEqual(data['tool'], 'weapon-sound-audit')
            self.assertEqual(data['counts']['error'], 1)


if __name__ == '__main__':
    unittest.main()

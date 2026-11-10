"""Synthetic tests for iw7_audit_common.py (no game data)."""
import argparse
import io
import json
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iw7_audit_common as common  # noqa: E402


def write(root, rel, data):
    path = os.path.join(root, *rel.split('/'))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = 'wb' if isinstance(data, bytes) else 'w'
    with open(path, mode, **({} if isinstance(data, bytes) else {'encoding': 'utf-8', 'newline': '\n'})) as handle:
        handle.write(data if isinstance(data, (bytes, str)) else json.dumps(data))
    return path


def xab(frames=30, rate=30.0):
    """An IW7 animation header as ZoneTool dumps it: one 136-byte record, then the name."""
    header = bytearray(136)
    struct.pack_into('<f', header, 100, rate)
    struct.pack_into('<f', header, 104, 1.0)
    struct.pack_into('<H', header, 116, frames)
    header[118] = 1
    return b'\x08\x01' + struct.pack('<I', 1) + bytes(header) + b'\x06\x01probe\0'


class ReportTest(unittest.TestCase):
    def test_lines_counts_and_exit(self):
        report = common.Report('feel', 'zone')
        report.add('info', 'B', 'gun', 'sits in the middle', source='stock')
        report.add('error', 'A', 'gun', 'declared 5, built 7', notice='it reloads slower than decided',
                   source='intent', field='animpkg:timers.iReloadTime', value=7)
        report.add('warn', 'C', 'gun', 'copy of a stock ribbon', proof='engine')
        report.ask('see', 'gun', 'does the trail read as a short streak?', 'ribbon values are a copy', effect='vfx/x')
        report.ask('see', 'gun', 'does the trail read as a short streak?', 'ribbon values are a copy', effect='vfx/x')
        self.assertEqual(report.counts(), {'error': 1, 'warn': 1, 'info': 1})
        self.assertEqual(len(report.questions), 1)
        self.assertEqual(report.exit_code(), 1)
        out = io.StringIO()
        report.write_text(out)
        text = out.getvalue().splitlines()
        self.assertEqual(text[0], '  ERROR A  gun: declared 5, built 7')
        self.assertEqual(text[1], '        player: it reloads slower than decided')
        self.assertIn('[only the engine can confirm]', text[2])
        self.assertEqual(text[-1], 'feel zone: errors 1, warnings 1, notes 1, engine questions 1')
        data = report.as_dict()
        self.assertEqual(data['schema'], common.SCHEMA)
        self.assertEqual(data['findings'][0]['evidence'], {'field': 'animpkg:timers.iReloadTime', 'value': 7})
        self.assertEqual(data['engine_questions'][0]['how'], {'effect': 'vfx/x'})

    def test_refuses_unknown_words_and_merges(self):
        report = common.Report('all', 'zone')
        with self.assertRaises(ValueError):
            report.add('fatal', 'X', 'a', 'b')
        with self.assertRaises(ValueError):
            report.add('warn', 'X', 'a', 'b', proof='guess')
        with self.assertRaises(ValueError):
            report.ask('smell', 'a', 'q', 'w')
        other = common.Report('sound', 'zone')
        other.add('warn', 'S', 'alias', 'quiet')
        other.ask('hear', 'alias', 'is the shot as loud as stock?', 'level is at the stock floor')
        other.facts['rows'] = 3
        report.merge(other)
        self.assertEqual(report.counts()['warn'], 1)
        self.assertEqual(report.facts, {'sound': {'rows': 3}})
        self.assertEqual(report.exit_code(), 0)

    def test_finish_writes_json(self):
        with tempfile.TemporaryDirectory() as temp:
            target = os.path.join(temp, 'out.json')
            report = common.Report('feel', 'zone')
            code = common.finish(report, argparse.Namespace(json=target), io.StringIO())
            self.assertEqual(code, 0)
            self.assertEqual(common.load_json(target)['counts'], {'error': 0, 'warn': 0, 'info': 0})


class NumbersTest(unittest.TestCase):
    def test_population(self):
        empty = common.Population([])
        self.assertIsNone(empty.median)
        self.assertIsNone(empty.position(3))
        self.assertEqual(empty.describe(), 'no stock values')
        pop = common.Population(list(range(1, 101)) + [True, None, 'x', float('nan')])
        self.assertEqual(pop.n, 100)
        self.assertEqual((pop.min, pop.max, pop.median), (1.0, 100.0, 50.5))
        self.assertEqual(pop.position(0), 'below-all')
        self.assertEqual(pop.position(2), 'low')
        self.assertEqual(pop.position(50), 'central')
        self.assertEqual(pop.position(99), 'high')
        self.assertEqual(pop.position(101), 'above-all')
        self.assertEqual(pop.rank(25), 0.25)
        self.assertIn('stock n=100', pop.describe())

    def test_same_and_fmt(self):
        self.assertTrue(common.same(0.4281, 0.42810001))
        self.assertFalse(common.same(0.4281, 0.946))
        self.assertFalse(common.same(True, 1))
        self.assertTrue(common.same('a', 'a'))
        self.assertEqual(common.fmt(2.5), '2.5')
        self.assertEqual(common.fmt(767.0), '767')
        self.assertEqual(common.number('0.5'), 0.5)
        self.assertIsNone(common.number(''))


class DocumentsTest(unittest.TestCase):
    def test_leaves_and_leaf(self):
        doc = {'a': {'b': 1, 'c': [2, {'d': 3}]}, 'e': 'x'}
        self.assertEqual(common.leaves(doc), {'a.b': 1, 'a.c[0]': 2, 'a.c[1].d': 3, 'e': 'x'})
        self.assertEqual(common.leaf(doc, 'a.c[1].d'), 3)
        self.assertEqual(common.leaf(doc, 'a.zz', 'none'), 'none')

    def test_nearest_stock_names_the_template(self):
        stock = {'pistol': {'szInternalName': 'pistol', 'weapDef': {'iFireTime': 100, 'damage': 30, 'x': 1}},
                 'rifle': {'szInternalName': 'rifle', 'weapDef': {'iFireTime': 80, 'damage': 45, 'x': 2}}}
        mine = {'szInternalName': 'mine', 'weapDef': {'iFireTime': 80, 'damage': 2000, 'x': 2}}
        name, share, compared = common.nearest_stock(mine, stock)
        self.assertEqual((name, compared), ('rifle', 3))
        self.assertAlmostEqual(share, 2 / 3)
        self.assertEqual(common.nearest_stock(stock['pistol'], stock)[:2], ('pistol', 1.0))
        self.assertEqual(common.nearest_stock(mine, {}), (None, 0.0, 0))

    def test_observable_groups(self):
        self.assertEqual(common.observable_group('animpkg:timers.iRaiseTime')[0], 'switching')
        self.assertEqual(common.observable_group('animpkg:timers.iFastReloadEmptyAddTime')[0], 'reloading')
        self.assertEqual(common.observable_group('weapon:weapDef.aimDownSight')[0], 'aiming')
        self.assertEqual(common.observable_group('weapon:weapDef.reticleSide')[0], 'crosshair')
        self.assertEqual(common.observable_group('sfxpkg:szWeapSndReflectionClass')[0], 'sound profile')
        self.assertIsNone(common.observable_group('weapon:weapDef.somethingInternal'))
        keys = [p for _, _, patterns in common.OBSERVABLE for p in patterns]
        self.assertEqual(len(keys), len(set(keys)))


class TreesTest(unittest.TestCase):
    def test_locate_stock_catalog_and_animation(self):
        with tempfile.TemporaryDirectory() as temp:
            write(temp, 'work/zonetool/mod/weapons/gun.json', {'szInternalName': 'gun'})
            write(temp, 'work/zonetool/mod/catalog.txt', 'gun_fire=gun:gun_up:att1\n')
            write(temp, 'work/zonetool/mod/behaviours.txt', 'gun|ns|t|flash=vfx/a|gun_fire\n')
            write(temp, 'work/zonetool/mod/sound/gun.aliases.csv',
                  'Name,File,vol_max,type\ngun_fire,w/gun_fire,0.5,loaded\n,skip,1,loaded\n')
            write(temp, 'work/zonetool/mod/xanim/gun_raise.xab', xab(frames=24))
            write(temp, 'work/zonetool/mod/xanim/broken.xab', b'not an animation')
            zone = common.locate_zone_dir(os.path.join(temp, 'work'))
            self.assertEqual(os.path.basename(zone), 'mod')
            self.assertEqual(common.locate_zone_dir(zone), zone)
            tree = common.preflight.Tree(zone)
            self.assertEqual(common.read_catalog(tree)[0]['fire_alias'], 'gun_fire')
            self.assertEqual(common.read_behaviours(tree)[0]['effects'], {'flash': 'vfx/a'})
            rows = common.alias_rows(zone)
            self.assertEqual([(r['Name'], r['vol_max'], r['_list'], r['_line']) for r in rows],
                             [('gun_fire', '0.5', 'gun.aliases.csv', 2)])
            self.assertEqual(common.xab_info(os.path.join(zone, 'xanim', 'gun_raise.xab')),
                             {'frames': 24, 'rate': 30.0, 'ms': 800})
            with self.assertRaises(ValueError):
                common.xab_info(os.path.join(zone, 'xanim', 'broken.xab'))
            write(temp, 'work/zonetool/other/weapons/b.json', {})
            with self.assertRaises(ValueError):
                common.locate_zone_dir(os.path.join(temp, 'work'))
            with self.assertRaises(ValueError):
                common.locate_zone_dir(os.path.join(temp, 'nothing'))

    def test_stock_dump(self):
        with tempfile.TemporaryDirectory() as temp:
            write(temp, 'dump/a/weapons/one.json', {'v': 1})
            write(temp, 'dump/a/weapons/bad.json', '{broken')
            write(temp, 'dump/b/weapons/one.json', {'v': 2})
            write(temp, 'dump/b/weapons/sub/two.json', {'v': 3})
            write(temp, 'dump/notes.txt', 'x')
            stock = common.StockDump([os.path.join(temp, 'dump')])
            self.assertTrue(stock)
            self.assertEqual(sorted(stock.zones), ['a', 'b'])
            self.assertEqual([(z, n, d['v']) for z, n, d in stock.docs('weapons')],
                             [('a', 'one', 1), ('b', 'sub/two', 3)])
            self.assertTrue(stock.find('weapons', 'sub/two', '.json').endswith('two.json'))
            self.assertIsNone(stock.find('weapons', 'three', '.json'))
            self.assertFalse(common.StockDump([]))
            one = common.StockDump([os.path.join(temp, 'dump', 'b')])
            self.assertEqual(sorted(one.zones), ['b'])


class IntentTest(unittest.TestCase):
    def test_judges_only_what_was_declared(self):
        with tempfile.TemporaryDirectory() as temp:
            write(temp, 'intent/gun.json', {
                'schema': common.INTENT_SCHEMA, 'item': 'gun', 'kind': 'weapon', 'template': 'pistol',
                'decisions': {
                    'weapon:weapDef.aimDownSight': {'value': False, 'why': 'it cannot aim'},
                    'animpkg:timers.iRaiseTime': {'min': 900, 'max': 1100, 'why': 'its raise animation is 1.0 s'},
                    'weapon:weapDef.fHipSpread*': {'keep': True, 'why': 'pistol hip spread is wanted'},
                    'weapon:weapDef.fHipSpreadStandMin': {'value': 2.0, 'why': 'measured in the source game'},
                    'weapon:weapDef.damage': {'value': 5, 'why': '  '}}})
            write(temp, 'intent/readme.json', {'not': 'an intent file'})
            intent = common.Intent.load(os.path.join(temp, 'intent'))
            self.assertEqual(intent.template('gun'), 'pistol')
            self.assertEqual(intent.judge('gun', 'weapon:weapDef.aimDownSight', False), 'match')
            self.assertEqual(intent.judge('gun', 'weapon:weapDef.aimDownSight', True), 'mismatch')
            self.assertEqual(intent.judge('gun', 'animpkg:timers.iRaiseTime', 1000), 'match')
            self.assertEqual(intent.judge('gun', 'animpkg:timers.iRaiseTime', 500), 'mismatch')
            self.assertEqual(intent.judge('gun', 'weapon:weapDef.fHipSpreadDuckedMin', 1.5), 'keep')
            self.assertEqual(intent.judge('gun', 'weapon:weapDef.fHipSpreadStandMin', 2.0), 'match')
            self.assertIsNone(intent.judge('gun', 'weapon:weapDef.damage', 5))        # no reason, no decision
            self.assertIsNone(intent.judge('gun', 'weapon:weapDef.iFireTime', 100))
            self.assertIsNone(intent.judge('other', 'weapon:weapDef.aimDownSight', False))
            self.assertIn('it cannot aim', intent.wanted('gun', 'weapon:weapDef.aimDownSight'))
            report = common.Report('feel', 'zone')
            intent.report_problems(report)
            self.assertEqual([f['code'] for f in report.findings], ['INTENT-FILE'])
            self.assertIn('weapon:weapDef.damage', report.findings[0]['message'])

    def test_missing_and_broken_files(self):
        self.assertEqual(common.Intent.load(None).items, {})
        with tempfile.TemporaryDirectory() as temp:
            bad = write(temp, 'gun.json', '{broken')
            self.assertEqual(len(common.Intent.load(bad).problems), 1)
            wrong = write(temp, 'wrong.json', {'schema': 'other'})
            self.assertEqual(len(common.Intent.load(wrong).problems), 1)


class ChainTest(unittest.TestCase):
    def test_chain_follows_secondary_aliases_and_stops_on_loops_and_unknown_names(self):
        rows = [{'Name': 'fire', 'SecondaryAliasName': 'layer_a', 'channel': 'c1'},
                {'Name': 'fire', 'SecondaryAliasName': 'layer_a', 'channel': 'c1'},
                {'Name': 'layer_a', 'SecondaryAliasName': 'layer_b', 'channel': 'c2'},
                {'Name': 'layer_b', 'SecondaryAliasName': 'fire', 'channel': 'c3'},
                {'Name': 'lonely', 'SecondaryAliasName': 'nowhere', 'channel': 'c4'}]
        index = common.alias_index(rows)
        chain = common.alias_chain(index, 'fire')
        self.assertEqual([(name, len(found)) for name, found in chain], [('fire', 2), ('layer_a', 1), ('layer_b', 1)])
        self.assertEqual(common.alias_chain(index, 'lonely'), [('lonely', [rows[4]]), ('nowhere', [])])
        self.assertEqual(common.alias_chain(index, ''), [])


class GroupJudgeTest(unittest.TestCase):
    WEAPON = {'weapDef': {'aimDownSight': True, 'fHipSpreadStandMin': 2.0, 'hipSpreadStandMax': 3.5, 'damage': 2000,
                          'unrelated': 7}}
    TEMPLATE = {'weapDef': {'aimDownSight': True, 'fHipSpreadStandMin': 2.0, 'hipSpreadStandMax': 3.5, 'damage': 90,
                            'unrelated': 7}}

    def judged(self, decisions=None, only=None):
        intent = common.Intent()
        if decisions is not None:
            intent.items['gun'] = {'schema': common.INTENT_SCHEMA, 'item': 'gun', 'decisions': decisions}
        judge = common.GroupJudge(intent, 'gun')
        judge.feed('weapon', self.WEAPON, self.TEMPLATE, 'stock_gun')
        report = common.Report('probe', 'gun')
        judge.report(report, 'FEEL', only=only)
        return judge, report

    def test_undeclared_template_group_warns_and_a_changed_group_is_silent(self):
        _, report = self.judged()
        codes = {(f['code'], f['evidence']['group']) for f in report.findings}
        self.assertEqual(codes, {('FEEL-TEMPLATE-GROUP', 'aiming'), ('FEEL-TEMPLATE-GROUP', 'spread')})
        self.assertEqual(report.facts['groups']['gun']['damage'],
                         {'values': 1, 'declared': 0, 'changed': 1, 'template': 0})
        self.assertEqual(report.exit_code(), 0)

    def test_a_tool_reports_only_the_groups_it_owns(self):
        _, report = self.judged(only=('spread',))
        self.assertEqual([f['evidence']['group'] for f in report.findings], ['spread'])
        self.assertEqual(list(report.facts['groups']['gun']), ['spread'])

    def test_declared_keep_silences_and_a_broken_decision_is_an_error(self):
        _, report = self.judged({'weapon:weapDef.fHipSpread*': {'keep': True, 'why': 'wanted'},
                                 'weapon:weapDef.aimDownSight': {'value': False, 'why': 'cannot aim'}})
        by_code = {f['code']: f for f in report.findings}
        self.assertEqual(by_code['FEEL-INTENT']['severity'], 'error')
        self.assertEqual(by_code['FEEL-TEMPLATE-PART']['evidence']['keys'], ['weapon:weapDef.hipSpreadStandMax'])
        self.assertNotIn('FEEL-TEMPLATE-GROUP', by_code)
        self.assertEqual(report.exit_code(), 1)

    def test_a_reason_is_required_and_the_skeleton_is_inert(self):
        judge, report = self.judged({'weapon:weapDef.aimDownSight': {'keep': True, 'why': ' '}})
        self.assertIn('FEEL-TEMPLATE-GROUP', {f['code'] for f in report.findings})
        doc = judge.skeleton('stock_gun', 'probe')
        self.assertEqual(doc['template'], 'stock_gun')
        self.assertEqual(doc['decisions']['weapon:weapDef.aimDownSight'], {'value': True, 'why': ''})
        self.assertNotIn('weapon:weapDef.damage', doc['decisions'])
        intent = common.Intent()
        intent.items['gun'] = doc
        self.assertIsNone(intent.judge('gun', 'weapon:weapDef.aimDownSight', True))

    def test_template_of_names_or_finds_the_nearest(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, 'dump/zone_a/weapons/stock_gun.json', self.TEMPLATE)
            write(root, 'dump/zone_a/weapons/other.json', {'weapDef': {'aimDownSight': False, 'damage': 1}})
            stock = common.StockDump([os.path.join(root, 'dump')])
            name, doc, share = common.template_of(self.WEAPON, stock, 'weapons')
            self.assertEqual((name, doc), ('stock_gun', self.TEMPLATE))
            self.assertAlmostEqual(share, 0.8)
            self.assertEqual(common.template_of(self.WEAPON, stock, 'weapons', 'other')[0], 'other')
            self.assertEqual(common.template_of(self.WEAPON, None, 'weapons'), (None, None, 0.0))


class ArgsTest(unittest.TestCase):
    def test_stock_from_environment(self):
        with tempfile.TemporaryDirectory() as temp:
            write(temp, 'dump/a/weapons/one.json', {})
            parser = common.add_common_args(argparse.ArgumentParser())
            old = os.environ.get('IW7_STOCK_DUMP')
            os.environ['IW7_STOCK_DUMP'] = os.path.join(temp, 'dump')
            try:
                self.assertEqual(sorted(common.stock_from_args(parser.parse_args([])).zones), ['a'])
                self.assertFalse(common.stock_from_args(parser.parse_args(['--stock', os.path.join(temp, 'no')])))
            finally:
                if old is None:
                    del os.environ['IW7_STOCK_DUMP']
                else:
                    os.environ['IW7_STOCK_DUMP'] = old


if __name__ == '__main__':
    unittest.main()

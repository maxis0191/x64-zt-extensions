"""Synthetic tests for iw7_weapon_feel_audit.py (no game data, no ffmpeg, no network)."""
import io
import json
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iw7_audit_common as common  # noqa: E402
import iw7_weapon_feel_audit as feel  # noqa: E402


def write(root, rel, data):
    path = os.path.join(root, *rel.split('/'))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = 'wb' if isinstance(data, bytes) else 'w'
    with open(path, mode, **({} if isinstance(data, bytes) else {'encoding': 'utf-8', 'newline': '\n'})) as handle:
        handle.write(data if isinstance(data, (bytes, str)) else json.dumps(data))
    return path


def xab(ms, rate=30.0):
    """An IW7 animation header as ZoneTool dumps it, ms long."""
    frames = int(round(ms * rate / 1000.0))
    header = bytearray(136)
    struct.pack_into('<f', header, 100, rate)
    struct.pack_into('<f', header, 104, 1.0)
    struct.pack_into('<H', header, 116, frames)
    header[118] = 1
    return b'\x08\x01' + struct.pack('<I', 1) + bytes(header) + b'\x06\x01probe\0'


STOCK_COUNT = 25


def weapon_doc(name, package, damage):
    weap = {'szXAnims': package, 'damage': damage, 'iFireTime': 100, 'aimDownSight': True,
            'iAmmoUsedPerShot': 1, 'fHipSpreadStandMin': 2.0, 'bNoPartialReload': False, 'reticleType': 0,
            'moveSpeedScale': 1.0}
    for i in range(30):
        weap['padding%d' % i] = i
    return {'szInternalName': name, 'szDisplayName': name, 'iClipSize': 8, 'weapDef': weap}


def package_doc(raise_ms, raise_anim, total=2000, add=1000, offset='common_off'):
    return {'timers': {'iRaiseTime': raise_ms, 'iReloadTime': total, 'iReloadAddTime': add,
                       'iDropTime': 65535, 'quickDropTime': 0},
            'anims': {'WEAP_ANIM_RAISE': raise_anim, 'WEAP_ANIM_IDLE': 'shared_idle',
                      'WEAP_ANIM_ADDITIVE_SPRINT_OFFSET': offset, 'WEAP_ANIM_DROP': ''},
            'fireAnimTimesMs': [100]}


def build_stock(root, late=0):
    """25 stock weapons; stock package i raises at 0.8 + i * 0.4/24 of its 1000 ms animation. Package 0 owns an
    additive nobody else plays. The last `late` packages bring their ammo after the reload ends."""
    zone = os.path.join(root, 'stockz')
    for i in range(STOCK_COUNT):
        name = 'stock_%d' % i
        write(zone, 'weapons/%s.json' % name, weapon_doc(name, name + '_package', 10 + i))
        ratio = 0.8 + i * 0.4 / 24
        offset = 'owned_by_zero' if i == 0 else 'common_off'
        pkg = package_doc(int(round(ratio * 1000)), 'a_%d' % i, offset=offset)
        if i >= STOCK_COUNT - late:
            pkg['timers']['iReloadAddTime'] = 2500
        if i == STOCK_COUNT - 1:
            pkg['anims']['WEAP_ANIM_ADDITIVE_CRAWL_IN'] = 'elsewhere'
        write(zone, 'animpkg/%s_package.json' % name, pkg)
        write(zone, 'xanim/a_%d.xab' % i, xab(1000))
    for name in ('shared_idle', 'common_off', 'owned_by_zero'):
        write(zone, 'xanim/%s.xab' % name, xab(500))
    return zone


def add_gun(tree, name, raise_ms, anim, anim_ms, damage=10, **timers):
    """A clone of stock weapon 0 and its package, with a new raise animation of its own."""
    write(tree, 'weapons/%s.json' % name, weapon_doc(name, name + '_package', damage))
    pkg = package_doc(raise_ms, anim, offset='owned_by_zero')
    pkg['timers'].update(timers)
    write(tree, 'animpkg/%s_package.json' % name, pkg)
    if anim_ms is not None:
        write(tree, 'xanim/%s.xab' % anim, xab(anim_ms))
    return pkg


def run(tree, stock_zone, items=None, intent=None, **options):
    stock = common.StockDump([stock_zone] if stock_zone else [])
    return feel.audit(tree, stock, intent or common.Intent(), items=items, **options)


def codes(report, item=None):
    return [f['code'] for f in report.findings if item is None or f['asset'] == item]


def finding(report, code, item=None):
    return next((f for f in report.findings if f['code'] == code and (item is None or f['asset'] == item)), None)


class FeelTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = self.temp.name
        self.stock = build_stock(self.root)
        self.tree = os.path.join(self.root, 'mod')

    def tearDown(self):
        self.temp.cleanup()

    # ---------------------------------------------------------------- groups
    def test_groups_leave_out_sound_and_effects(self):
        self.assertNotIn('sound profile', feel.GROUPS)
        self.assertNotIn('effects', feel.GROUPS)
        self.assertIn('switching', feel.GROUPS)
        self.assertEqual(len(feel.GROUPS), len(common.OBSERVABLE) - 2)

    # ---------------------------------------------------------------- F2
    def test_timer_kept_from_template_is_warned_with_question(self):
        add_gun(self.tree, 'gun_a', 800, 'new_anim', 2000)          # template timer kept, animation replaced
        report = run(self.tree, self.stock, ['gun_a'])
        f = finding(report, 'FEEL-TIMER-FROM-TEMPLATE', 'gun_a')
        self.assertIsNotNone(f)
        self.assertEqual((f['severity'], f['proof']), ('warn', 'engine'))
        self.assertEqual(f['evidence']['timer'], 800)
        self.assertEqual(f['evidence']['length_ms'], 2000)
        self.assertAlmostEqual(f['evidence']['ratio'], 0.4)
        self.assertEqual(f['evidence']['n'], STOCK_COUNT)
        self.assertIn('raise lasts 800 ms but its animation new_anim is 2000 ms (plays 40 %)', f['message'])
        self.assertIn('stock middle 100 %', f['message'])
        self.assertTrue(f['notice'])
        self.assertTrue(any(q['kind'] == 'see' and q['asset'] == 'gun_a' for q in report.questions))
        self.assertNotIn('FEEL-TIMER-ANIM-EXTREME', codes(report, 'gun_a'))   # one finding per weapon and pair

    def test_extreme_when_timer_is_not_the_templates(self):
        add_gun(self.tree, 'gun_b', 500, 'new_anim', 2000)
        report = run(self.tree, self.stock, ['gun_b'])
        f = finding(report, 'FEEL-TIMER-ANIM-EXTREME', 'gun_b')
        self.assertEqual((f['severity'], f['proof']), ('warn', 'engine'))
        self.assertNotIn('FEEL-TIMER-FROM-TEMPLATE', codes(report, 'gun_b'))
        self.assertLess(f['evidence']['ratio'], f['evidence']['stock_min'])

    def test_unusual_is_only_a_note(self):
        add_gun(self.tree, 'gun_c', 810, 'new_anim', 1000)           # 81 %: under p5, above the stock minimum
        report = run(self.tree, self.stock, ['gun_c'])
        f = finding(report, 'FEEL-TIMER-ANIM-UNUSUAL', 'gun_c')
        self.assertEqual(f['severity'], 'info')
        self.assertFalse([x for x in report.findings if x['code'].startswith('FEEL-TIMER') and x['severity'] != 'info'])

    def test_timer_inside_the_band_and_unused_slots_are_silent(self):
        add_gun(self.tree, 'gun_ok', 1000, 'new_anim', 1000)         # 100 %: the stock middle
        report = run(self.tree, self.stock, ['gun_ok'])
        self.assertFalse([c for c in codes(report) if c.startswith('FEEL-TIMER')])
        # iDropTime is unset (65535), quickDropTime is 0, the DROP slot is empty: nothing is compared
        self.assertFalse([f for f in report.findings if 'drop' in f['message'] and f['code'].startswith('FEEL-TIMER')])

    def test_declared_decision_closes_the_warning(self):
        add_gun(self.tree, 'gun_a', 800, 'new_anim', 2000)
        intent_dir = os.path.join(self.root, 'intent')
        write(intent_dir, 'gun_a.json', {
            'schema': common.INTENT_SCHEMA, 'item': 'gun_a', 'kind': 'weapon',
            'decisions': {'finding:FEEL-TIMER-FROM-TEMPLATE': {'keep': True, 'why': 'quick raise is wanted'}}})
        intent = common.Intent.load(intent_dir)
        report = run(self.tree, self.stock, ['gun_a'], intent)
        self.assertEqual(finding(report, 'FEEL-TIMER-FROM-TEMPLATE')['severity'], 'warn')
        code = common.finish(report, type('A', (), {'json': None, 'strict': False})(), io.StringIO(), intent=intent)
        self.assertEqual(code, 0)
        closed = finding(report, 'FEEL-TIMER-FROM-TEMPLATE')
        self.assertEqual((closed['severity'], closed['answered']), ('info', 'quick raise is wanted'))

    def test_declared_timer_value_closes_its_own_warning_and_wrong_value_is_an_error(self):
        add_gun(self.tree, 'gun_a', 800, 'new_anim', 2000)
        intent = common.Intent()
        intent.items['gun_a'] = {'schema': common.INTENT_SCHEMA, 'item': 'gun_a', 'decisions': {
            'animpkg:timers.iRaiseTime': {'value': 800, 'why': 'the raise is meant to be quick'}}}
        report = run(self.tree, self.stock, ['gun_a'], intent)
        closed = finding(report, 'FEEL-TIMER-FROM-TEMPLATE')
        self.assertEqual((closed['severity'], closed['answered']), ('info', 'the raise is meant to be quick'))
        intent.items['gun_a']['decisions']['animpkg:timers.iRaiseTime']['value'] = 900
        report = run(self.tree, self.stock, ['gun_a'], intent)
        self.assertIn('FEEL-INTENT', codes(report))
        self.assertEqual(finding(report, 'FEEL-TIMER-FROM-TEMPLATE')['severity'], 'warn')

    def test_missing_animation_is_a_warning_for_the_engine_only_when_no_stock_package_names_it(self):
        pkg = add_gun(self.tree, 'gun_m', 1000, 'new_anim', 1000)
        pkg['anims']['WEAP_ANIM_ADS_UP'] = 'ghost_anim'                  # nobody has it
        pkg['anims']['WEAP_ANIM_ADDITIVE_CRAWL_IN'] = 'elsewhere'        # stock names it, file is not in the dump
        write(self.tree, 'animpkg/gun_m_package.json', pkg)
        report = run(self.tree, self.stock, ['gun_m'])
        self.assertEqual(report.counts()['error'], 0)
        missing = [f for f in report.findings if f['code'] == 'FEEL-ANIM-MISSING']
        self.assertEqual([(f['severity'], f['proof']) for f in missing], [('warn', 'engine')])
        self.assertEqual(missing[0]['evidence']['animation'], 'ghost_anim')
        self.assertTrue([q for q in report.questions if q.get('evidence', {}).get('animation') == 'ghost_anim'
                         or 'ghost_anim' in json.dumps(q)])
        note = finding(report, 'FEEL-ANIM-NOT-IN-DUMP')
        self.assertEqual(note['severity'], 'info')
        self.assertIn('elsewhere', note['message'])

    def test_animation_found_in_the_tree_is_not_missing(self):
        pkg = add_gun(self.tree, 'gun_m', 1000, 'new_anim', 1000)
        pkg['anims']['WEAP_ANIM_ADS_UP'] = 'tree_only'
        write(self.tree, 'animpkg/gun_m_package.json', pkg)
        write(self.tree, 'xanim/tree_only.xab', xab(300))
        report = run(self.tree, self.stock, ['gun_m'])
        self.assertFalse([f for f in report.findings if f['severity'] == 'error'])

    def test_unreadable_animation_header_is_not_compared(self):
        add_gun(self.tree, 'gun_x', 800, 'broken', None)
        write(self.tree, 'xanim/broken.xab', b'not an animation')
        report = run(self.tree, self.stock, ['gun_x'])
        self.assertFalse([c for c in codes(report) if c.startswith('FEEL-TIMER')])
        self.assertFalse([f for f in report.findings if f['severity'] == 'error'])

    # ---------------------------------------------------------------- F3
    def test_ammo_after_the_reload_ends(self):
        add_gun(self.tree, 'gun_l', 1000, 'new_anim', 1000, iReloadAddTime=2500)
        report = run(self.tree, self.stock, ['gun_l'])
        f = finding(report, 'FEEL-RELOAD-ADD-LATE', 'gun_l')
        self.assertEqual(f['severity'], 'warn')
        self.assertEqual((f['evidence']['stock_late'], f['evidence']['stock_n']), (0, STOCK_COUNT))
        self.assertIn('refills after the reload has already ended', f['notice'])

    def test_late_ammo_is_a_note_when_stock_does_it_too(self):
        stock = build_stock(os.path.join(self.root, 'second'), late=3)       # 3 of 25 = 12 %
        add_gun(self.tree, 'gun_l', 1000, 'new_anim', 1000, iReloadAddTime=2500)
        report = run(self.tree, stock, ['gun_l'])
        f = finding(report, 'FEEL-RELOAD-ADD-LATE', 'gun_l')
        self.assertEqual(f['severity'], 'info')
        self.assertEqual(f['evidence']['stock_late'], 3)

    def test_ammo_time_left_from_template(self):
        add_gun(self.tree, 'gun_t', 1000, 'new_anim', 1000, iReloadTime=3000)      # add 1000 as in the template
        report = run(self.tree, self.stock, ['gun_t'])
        f = finding(report, 'FEEL-RELOAD-ADD-TEMPLATE', 'gun_t')
        self.assertEqual((f['severity'], f['proof']), ('warn', 'engine'))
        self.assertIn('not adapted', f['notice'])
        self.assertTrue(any(q['kind'] == 'time' and q['asset'] == 'gun_t' for q in report.questions))

    def test_adapted_ammo_time_is_silent(self):
        add_gun(self.tree, 'gun_t', 1000, 'new_anim', 1000, iReloadTime=3000, iReloadAddTime=1500)
        report = run(self.tree, self.stock, ['gun_t'])
        self.assertFalse([c for c in codes(report) if c.startswith('FEEL-RELOAD')])

    # ---------------------------------------------------------------- F4
    def test_value_outside_stock_is_one_note(self):
        add_gun(self.tree, 'gun_d', 1000, 'new_anim', 1000, damage=5000)
        report = run(self.tree, self.stock, ['gun_d'])
        notes = [f for f in report.findings if f['code'] == 'FEEL-OUTSIDE-STOCK']
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]['severity'], 'info')
        self.assertIn('damage=5000 (stock 10..34)', notes[0]['message'])

    def test_value_inside_stock_is_silent(self):
        add_gun(self.tree, 'gun_d', 1000, 'new_anim', 1000, damage=20)
        report = run(self.tree, self.stock, ['gun_d'])
        self.assertNotIn('FEEL-OUTSIDE-STOCK', codes(report))

    # ---------------------------------------------------------------- F6
    def test_template_animation_owned_by_few_weapons(self):
        add_gun(self.tree, 'gun_a', 1000, 'new_anim', 1000)
        report = run(self.tree, self.stock, ['gun_a'])
        f = finding(report, 'FEEL-TEMPLATE-ANIMS', 'gun_a')
        self.assertEqual((f['severity'], f['proof']), ('warn', 'engine'))
        self.assertIn('ADDITIVE_SPRINT_OFFSET=owned_by_zero (used by 1 of %d stock packages)' % STOCK_COUNT, f['message'])
        self.assertEqual([s['slot'] for s in f['evidence']['slots']], ['ADDITIVE_SPRINT_OFFSET'])   # idle is shared by all
        self.assertTrue(any(q['kind'] == 'see' for q in report.questions))

    def test_replaced_template_animation_is_silent(self):
        pkg = add_gun(self.tree, 'gun_a', 1000, 'new_anim', 1000)
        pkg['anims']['WEAP_ANIM_ADDITIVE_SPRINT_OFFSET'] = 'common_off'
        write(self.tree, 'animpkg/gun_a_package.json', pkg)
        report = run(self.tree, self.stock, ['gun_a'])
        self.assertNotIn('FEEL-TEMPLATE-ANIMS', codes(report))

    # ---------------------------------------------------------------- F1 and stock itself
    def test_template_residue_group_comes_from_the_shared_judge(self):
        add_gun(self.tree, 'gun_a', 1000, 'new_anim', 1000)
        report = run(self.tree, self.stock, ['gun_a'])
        groups = {f['evidence']['group'] for f in report.findings if f['code'].startswith('FEEL-TEMPLATE-')
                  and 'group' in f.get('evidence', {})}
        self.assertTrue(groups)
        self.assertTrue(groups <= set(feel.GROUPS))

    def test_a_stock_package_audited_as_itself_gives_no_error_and_no_template_warning(self):
        report = run(self.stock, self.stock)
        self.assertEqual(report.counts()['error'], 0)
        self.assertFalse([c for c in codes(report) if c in ('FEEL-TIMER-FROM-TEMPLATE', 'FEEL-RELOAD-ADD-TEMPLATE',
                                                            'FEEL-TEMPLATE-ANIMS')])

    # ---------------------------------------------------------------- no stock
    def test_without_stock_only_one_note_and_missing_animations_as_notes(self):
        pkg = add_gun(self.tree, 'gun_a', 800, 'new_anim', 2000)
        pkg['anims']['WEAP_ANIM_ADS_UP'] = 'ghost_anim'
        write(self.tree, 'animpkg/gun_a_package.json', pkg)
        report = run(self.tree, None, ['gun_a'])
        self.assertEqual(report.counts()['error'], 0)
        self.assertEqual(codes(report).count('FEEL-NO-STOCK'), 1)
        self.assertFalse([c for c in codes(report) if c.startswith(('FEEL-TIMER', 'FEEL-RELOAD', 'FEEL-OUTSIDE',
                                                                     'FEEL-TEMPLATE'))])
        self.assertEqual(finding(report, 'FEEL-ANIM-MISSING')['severity'], 'info')

    # ---------------------------------------------------------------- skeleton
    def test_skeleton_is_written_once_and_is_inert(self):
        add_gun(self.tree, 'gun_a', 800, 'new_anim', 2000)
        out = os.path.join(self.root, 'skel')
        report = run(self.tree, self.stock, ['gun_a'], skeleton_dir=out)
        path = os.path.join(out, 'gun_a.intent.json')
        self.assertTrue(os.path.isfile(path))
        doc = common.load_json(path)
        self.assertEqual(doc['schema'], common.INTENT_SCHEMA)
        self.assertEqual(doc['item'], 'gun_a')
        self.assertTrue(doc['decisions'])
        self.assertTrue(all(d['why'] == '' for d in doc['decisions'].values()))
        # only the groups of this audit
        for key in doc['decisions']:
            self.assertIn(common.observable_group(key)[0], feel.GROUPS)
        # a second run refuses to overwrite and says so
        with open(path, 'a', encoding='utf-8') as handle:
            handle.write('\n')
        with open(path, encoding='utf-8') as handle:
            before = handle.read()
        again = run(self.tree, self.stock, ['gun_a'], skeleton_dir=out)
        self.assertIn('FEEL-SKELETON-EXISTS', codes(again))
        with open(path, encoding='utf-8') as handle:
            self.assertEqual(handle.read(), before)
        # empty reasons decide nothing: no verdict for any value, no warning closed
        intent = common.Intent.load(out)
        for key in doc['decisions']:
            self.assertIsNone(intent.judge('gun_a', key, 1))
        loaded = run(self.tree, self.stock, ['gun_a'], intent)
        plain = run(self.tree, self.stock, ['gun_a'])
        self.assertEqual([f['code'] for f in loaded.findings if f['severity'] == 'warn'],
                         [f['code'] for f in plain.findings if f['severity'] == 'warn'])

    def test_filled_skeleton_closes_template_groups(self):
        add_gun(self.tree, 'gun_a', 800, 'new_anim', 2000)
        out = os.path.join(self.root, 'skel')
        run(self.tree, self.stock, ['gun_a'], skeleton_dir=out)
        path = os.path.join(out, 'gun_a.intent.json')
        doc = common.load_json(path)
        for decision in doc['decisions'].values():
            decision['why'] = 'kept on purpose'
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump(doc, handle)
        report = run(self.tree, self.stock, ['gun_a'], common.Intent.load(out))
        self.assertFalse([f for f in report.findings if f['code'] == 'FEEL-TEMPLATE-GROUP'])
        self.assertEqual(finding(report, 'FEEL-TIMER-FROM-TEMPLATE')['severity'], 'info')   # its timer is declared

    # ---------------------------------------------------------------- command line
    def test_main_prints_summary_and_json(self):
        add_gun(self.tree, 'gun_b', 500, 'new_anim', 2000)
        out = os.path.join(self.root, 'r.json')
        old = sys.stdout
        sys.stdout = io.StringIO()
        try:
            code = feel.main([self.tree, '--stock', self.stock, '--item', 'gun_b', '--json', out])
            text = sys.stdout.getvalue()
        finally:
            sys.stdout = old
        self.assertEqual(code, 0)
        self.assertIn('weapon-feel-audit', text.splitlines()[-1])
        self.assertIn('FEEL-TIMER-ANIM-EXTREME', text)
        self.assertEqual(common.load_json(out)['tool'], 'weapon-feel-audit')

    def test_strict_fails_while_a_warning_is_open(self):
        add_gun(self.tree, 'gun_b', 500, 'new_anim', 2000)
        old = sys.stdout
        sys.stdout = io.StringIO()
        try:
            code = feel.main([self.tree, '--stock', self.stock, '--item', 'gun_b', '--strict'])
        finally:
            sys.stdout = old
        self.assertEqual(code, 2)

    def test_unreadable_weapon_file_is_an_error(self):
        write(self.tree, 'weapons/gun_bad.json', '{ not json')
        report = run(self.tree, self.stock, ['gun_bad'])
        self.assertEqual(codes(report), ['FEEL-UNREADABLE'])


if __name__ == '__main__':
    unittest.main()

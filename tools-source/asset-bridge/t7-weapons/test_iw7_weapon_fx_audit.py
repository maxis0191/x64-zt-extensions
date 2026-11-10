"""Synthetic tests for iw7_weapon_fx_audit.py (no game data, no ffmpeg, no network)."""
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iw7_audit_common as common  # noqa: E402
import iw7_vfx as vfx  # noqa: E402
import iw7_weapon_fx_audit as fx  # noqa: E402

GEO = 'PARTICLE_ELEMENT_TYPE_GEO_TRAIL'
SPRITE = 'PARTICLE_ELEMENT_TYPE_BILLBOARD_SPRITE'
TAIL = 'PARTICLE_ELEMENT_TYPE_TAIL'


def write(root, rel, data):
    path = os.path.join(root, *rel.split('/'))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if isinstance(data, bytes):
        with open(path, 'wb') as handle:
            handle.write(data)
    else:
        with open(path, 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(data if isinstance(data, str) else json.dumps(data))
    return path


def link(module_type, **names):
    """A module of that type holding one linked asset."""
    module = vfx.new_module(module_type)
    _, _, _, _, _, ll_path = vfx.MODULE_DEFS[vfx.MT[module_type]]
    data = module[vfx.MODULE_DEFS[vfx.MT[module_type]][0]]
    target = data
    for part in ll_path.split('.'):
        target = target[part]
    target['assetList'] = [vfx.new_linked_asset(module_type, **names)]
    return module


def emitter(etype=SPRITE, material='eq/mat_a', points=None, size=None, color=None, life=None, child=None,
            rate=1.0):
    """One decoded emitter: ribbon geometry (points), size and colour (the 'look'), life, material, child effect."""
    em = vfx.new_emitter()
    em['particleSpawnRate'] = {'min': rate, 'max': rate}
    if life is not None:
        em['particleLife'] = {'min': life, 'max': life}
    state = vfx.new_state(etype)
    init = state['moduleGroupDefs'][0]['moduleDefs']
    if points is not None:
        geo = vfx.new_module('PARTICLE_MODULE_INIT_GEO_TRAIL')
        geo['initGeoTrail']['m_numPointsMax'] = points
        init.append(geo)
    if size is not None or color is not None:
        attr = vfx.new_module('PARTICLE_MODULE_INIT_ATTRIBUTES')
        if size is not None:
            attr['initAttributes']['m_sizeMax'] = [size, size, size, 0.0]
        if color is not None:
            attr['initAttributes']['m_colorMax'] = [color, color, color, 1.0]
        init.append(attr)
    if material:
        init.append(link('PARTICLE_MODULE_INIT_MATERIAL', material=material))
    if child:
        init.append(link('PARTICLE_MODULE_INIT_RUNNER', particleSystem=child))
    em['stateDefs'].append(state)
    return em


def effect_bytes(name, *emitters):
    model = vfx.new_model(name)
    model['system']['emitterDefs'].extend(emitters)
    model['system']['flags'] = vfx.system_flags(model)
    return vfx.encode(model)


def put_effect(zone, name, *emitters):
    return write(zone, 'particlesystem/%s.iw7VFX' % name, effect_bytes(name, *emitters))


def put_weapon(zone, name, trail=None, pkg_effects=None, extra=None):
    weap = {}
    if trail:
        weap['projTrailEffect'] = {'type': 1, 'fx': trail}
    if pkg_effects:
        weap['vfxPackage'] = name + '_vfxpackage'
        write(zone, 'vfxpkg/%s_vfxpackage.json' % name,
              {'name': name + '_vfxpackage', 'vfx': {k: {'type': 1, 'fx': v} for k, v in pkg_effects.items()}})
    doc = {'szInternalName': name, 'weapDef': weap}
    doc.update(extra or {})
    write(zone, 'weapons/%s.json' % name, doc)


def run(zone, stock_roots=(), intent=None, **options):
    stock = common.StockDump(list(stock_roots))
    report = fx.audit(zone, stock, intent or common.Intent(), **options)
    return report


def codes(report, code=None):
    return [f for f in report.findings if code is None or f['code'] == code]


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.zone = os.path.join(self.temp.name, 'zonetool', 'mod')
        self.stock_zone = os.path.join(self.temp.name, 'dump', 'cp_zmb')
        os.makedirs(os.path.join(self.zone, 'weapons'))
        os.makedirs(os.path.join(self.stock_zone, 'particlesystem'))

    def stock(self):
        return [self.stock_zone]


class ReachabilityTest(Base):
    def test_reach_unreferenced_and_children(self):
        put_weapon(self.zone, 'w_a', trail='vfx/test/parent')
        put_effect(self.zone, 'vfx/test/parent', emitter(child='vfx/test/child'))
        put_effect(self.zone, 'vfx/test/child', emitter())
        put_effect(self.zone, 'vfx/test/loose', emitter())
        report = run(self.zone)
        self.assertEqual(report.facts['effects']['w_a'], ['vfx/test/child', 'vfx/test/parent'])
        loose = codes(report, 'FX-UNREFERENCED')
        self.assertEqual(len(loose), 1)
        self.assertEqual(loose[0]['severity'], 'info')
        self.assertEqual(loose[0]['evidence']['first'], ['vfx/test/loose'])
        self.assertEqual(loose[0]['evidence']['count'], 1)
        self.assertEqual(report.counts()['error'], 0)

    def test_package_behaviours_and_followed_weapon(self):
        put_weapon(self.zone, 'w_a', pkg_effects={'viewFlashEffect': 'vfx/test/flash'},
                   extra={'szAltWeaponName': 'w_proj'})
        put_weapon(self.zone, 'w_proj', trail='vfx/test/proj_trail')
        write(self.zone, 'behaviours.txt', 'w_a|ns||beat=vfx/test/script|snd\n')
        for name in ('flash', 'script', 'proj_trail'):
            put_effect(self.zone, 'vfx/test/' + name, emitter())
        report = run(self.zone, items=['w_a'])
        self.assertEqual(report.facts['effects']['w_a'],
                         ['vfx/test/flash', 'vfx/test/proj_trail', 'vfx/test/script'])
        self.assertEqual(codes(report, 'FX-UNREFERENCED'), [])

    def test_no_stock_is_one_note_and_skips_comparisons(self):
        put_weapon(self.zone, 'w_a', trail='vfx/test/trail')
        put_effect(self.zone, 'vfx/test/trail', emitter(GEO, points=10, size=99999.0, life=9999.0))
        report = run(self.zone)
        self.assertEqual(len(codes(report, 'FX-NO-STOCK')), 1)
        for code in ('FX-STOCK-COPY', 'FX-SIZE-EXTREME', 'FX-LIFE-EXTREME', 'FX-SIZE-RANGE'):
            self.assertEqual(codes(report, code), [])

    def test_bad_file_is_an_error(self):
        put_weapon(self.zone, 'w_a', trail='vfx/test/broken')
        write(self.zone, 'particlesystem/vfx/test/broken.iw7VFX', b'not an effect')
        report = run(self.zone)
        self.assertEqual([f['severity'] for f in codes(report, 'FX-BAD-FILE')], ['error'])


class MissingTest(Base):
    def test_missing_error_and_not_in_dump(self):
        put_effect(self.stock_zone, 'vfx/stock/known', emitter())
        write(self.stock_zone, 'weapons/stock_gun.json',
              {'weapDef': {'projTrailEffect': {'type': 1, 'fx': 'vfx/other_zone/used_by_stock'}}})
        put_weapon(self.zone, 'w_a', trail='vfx/test/gone',
                   pkg_effects={'viewFlashEffect': 'vfx/other_zone/used_by_stock',
                                'worldFlashEffect': 'vfx/stock/known'})
        report = run(self.zone, self.stock())
        miss = codes(report, 'FX-MISSING')
        self.assertEqual([(f['severity'], f['proof']) for f in miss], [('warn', 'engine')])
        self.assertEqual(miss[0]['evidence']['effects'], ['vfx/test/gone'])
        dump = codes(report, 'FX-NOT-IN-DUMP')
        self.assertEqual([f['severity'] for f in dump], ['info'])
        self.assertEqual(dump[0]['evidence']['effects'], ['vfx/other_zone/used_by_stock'])

    def test_without_stock_missing_is_only_a_note(self):
        put_weapon(self.zone, 'w_a', trail='vfx/test/gone')
        miss = codes(run(self.zone), 'FX-MISSING')
        self.assertEqual([f['severity'] for f in miss], ['info'])

    def test_present_effects_are_silent(self):
        put_effect(self.stock_zone, 'vfx/stock/known', emitter())
        put_weapon(self.zone, 'w_a', trail='vfx/test/here', pkg_effects={'viewFlashEffect': 'vfx/stock/known'})
        put_effect(self.zone, 'vfx/test/here', emitter(material='eq/m'))
        write(self.zone, 'materials/eq/m.json', {})
        report = run(self.zone, self.stock())
        self.assertEqual(codes(report, 'FX-MISSING') + codes(report, 'FX-NOT-IN-DUMP'), [])


class ReferenceTest(Base):
    def test_reference_rules(self):
        put_effect(self.stock_zone, 'vfx/stock/user', emitter(material='stock/mat_used'))
        put_weapon(self.zone, 'w_a', trail='vfx/test/e')
        put_effect(self.zone, 'vfx/test/e',
                   emitter(material='eq/in_tree'), emitter(material='eq/nowhere'),
                   emitter(material='stock/mat_used'), emitter(material='eq/in_tree', child='vfx/test/no_child'),
                   emitter(material='eq/in_tree', child='vfx/stock/user'))
        write(self.zone, 'materials/eq/in_tree.json', {})
        report = run(self.zone, self.stock())
        errors = codes(report, 'FX-REF-MISSING')
        self.assertEqual(sorted((f['evidence']['kind'], tuple(f['evidence']['names'])) for f in errors),
                         [('effect', ('vfx/test/no_child',)), ('material', ('eq/nowhere',))])
        notes = codes(report, 'FX-REF-NOT-IN-DUMP')
        self.assertEqual([f['evidence']['names'] for f in notes], [['stock/mat_used']])
        self.assertTrue(all((f['severity'], f['proof']) == ('warn', 'engine') for f in errors))
        self.assertEqual(report.counts()['error'], 0)

    def test_missing_child_effect_also_breaks_the_weapon_wiring(self):
        put_weapon(self.zone, 'w_a', trail='vfx/test/e')
        put_effect(self.zone, 'vfx/test/e', emitter(child='vfx/test/no_child'))
        put_effect(self.stock_zone, 'vfx/stock/x', emitter())
        report = run(self.zone, self.stock())
        self.assertEqual([f['severity'] for f in codes(report, 'FX-MISSING')], ['warn'])


class StockCopyTest(Base):
    def _stock_ribbon(self, name='vfx/stock/trail_friendly', **kw):
        put_effect(self.stock_zone, name, emitter(GEO, material='stock/m', points=30, size=100.0, color=0.5,
                                                  life=0.6, **kw))

    def test_ribbon_with_stock_settings_but_new_look_is_flagged(self):
        self._stock_ribbon()
        put_weapon(self.zone, 'w_a', trail='vfx/test/trail')
        put_effect(self.zone, 'vfx/test/trail',
                   emitter(GEO, material='eq/own', points=30, size=7.0, color=0.9, life=0.6))
        write(self.zone, 'materials/eq/own.json', {})
        report = run(self.zone, self.stock())
        hits = codes(report, 'FX-STOCK-COPY')
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]['severity'], 'warn')
        self.assertEqual(hits[0]['proof'], 'engine')
        self.assertEqual(hits[0]['asset'], 'vfx/test/trail')
        self.assertIn('ribbon', hits[0]['message'])
        self.assertIn('trail_friendly', hits[0]['message'])
        self.assertEqual(hits[0]['evidence']['level'], 'settings')
        self.assertEqual([q['kind'] for q in report.questions], ['see'])

    def test_identical_element_is_reported_as_identical(self):
        self._stock_ribbon()
        put_weapon(self.zone, 'w_a', trail='vfx/test/trail')
        put_effect(self.zone, 'vfx/test/trail',
                   emitter(GEO, material='eq/own', points=30, size=100.0, color=0.5, life=0.6),
                   emitter(SPRITE, material='eq/own', size=3.0))
        write(self.zone, 'materials/eq/own.json', {})
        hit = codes(run(self.zone, self.stock()), 'FX-STOCK-COPY')[0]
        self.assertEqual(hit['evidence']['level'], 'identical')

    def test_own_ribbon_settings_are_silent(self):
        self._stock_ribbon()
        put_weapon(self.zone, 'w_a', trail='vfx/test/trail')
        put_effect(self.zone, 'vfx/test/trail',
                   emitter(GEO, material='eq/own', points=100, size=7.0, color=0.9, life=1.0))
        write(self.zone, 'materials/eq/own.json', {})
        self.assertEqual(codes(run(self.zone, self.stock()), 'FX-STOCK-COPY'), [])

    def test_a_declared_decision_closes_the_warning(self):
        self._stock_ribbon()
        put_weapon(self.zone, 'w_a', trail='vfx/test/trail')
        put_effect(self.zone, 'vfx/test/trail',
                   emitter(GEO, material='eq/own', points=30, size=7.0, color=0.9, life=0.6))
        write(self.zone, 'materials/eq/own.json', {})
        intent_file = write(self.temp.name, 'intent/i.json', {
            'schema': common.INTENT_SCHEMA, 'item': 'w_a',
            'decisions': {'finding:FX-STOCK-COPY:vfx/test/*': {'keep': True, 'why': 'the stock trail is wanted'}}})
        intent = common.Intent.load(intent_file)
        report = run(self.zone, self.stock(), intent)
        args = type('A', (), {'json': None, 'strict': True})()
        code = common.finish(report, args, io.StringIO(), intent=intent)
        hit = codes(report, 'FX-STOCK-COPY')[0]
        self.assertEqual(hit['severity'], 'info')
        self.assertEqual(hit['answered'], 'the stock trail is wanted')
        self.assertEqual(code, 0)

    def test_without_a_decision_strict_fails(self):
        self._stock_ribbon()
        put_weapon(self.zone, 'w_a', trail='vfx/test/trail')
        put_effect(self.zone, 'vfx/test/trail',
                   emitter(GEO, material='eq/own', points=30, size=7.0, color=0.9, life=0.6))
        write(self.zone, 'materials/eq/own.json', {})
        report = run(self.zone, self.stock())
        args = type('A', (), {'json': None, 'strict': True})()
        self.assertEqual(common.finish(report, args, io.StringIO(), intent=common.Intent()), 2)

    def test_whole_effect_copy_and_same_bytes_file(self):
        self._stock_ribbon()
        data = effect_bytes('vfx/stock/trail_friendly', emitter(GEO, material='stock/m', points=30, size=100.0,
                                                                 color=0.5, life=0.6))
        write(self.zone, 'particlesystem/vfx/test/renamed.iw7VFX',
              effect_bytes('vfx/test/renamed', emitter(GEO, material='stock/m', points=30, size=100.0, color=0.5,
                                                       life=0.6)))
        write(self.zone, 'particlesystem/vfx/stock/trail_friendly.iw7VFX', data)
        put_weapon(self.zone, 'w_a', trail='vfx/test/renamed',
                   pkg_effects={'viewFlashEffect': 'vfx/stock/trail_friendly'})
        report = run(self.zone, self.stock())
        hits = codes(report, 'FX-STOCK-COPY')
        self.assertEqual([h['asset'] for h in hits], ['vfx/test/renamed'])
        self.assertEqual(hits[0]['evidence']['level'], 'whole effect')
        self.assertEqual(report.facts['own_effects'], ['vfx/test/renamed'])

    def test_other_element_types_only_get_a_note(self):
        put_effect(self.stock_zone, 'vfx/stock/s', emitter(SPRITE, material='stock/m', size=5.0, life=0.3))
        put_weapon(self.zone, 'w_a', trail='vfx/test/s')
        put_effect(self.zone, 'vfx/test/s', emitter(SPRITE, material='eq/own', size=5.0, life=0.3))
        write(self.zone, 'materials/eq/own.json', {})
        report = run(self.zone, self.stock())
        self.assertEqual([f['severity'] for f in codes(report, 'FX-STOCK-COPY')], ['warn'])  # whole effect only
        put_effect(self.zone, 'vfx/test/s', emitter(SPRITE, material='eq/own', size=5.0, life=0.3),
                   emitter(SPRITE, material='eq/own', size=8.0, life=0.9))
        report = run(self.zone, self.stock())
        self.assertEqual(codes(report, 'FX-STOCK-COPY'), [])
        self.assertEqual(codes(report, 'FX-STOCK-COPY-OTHER')[0]['severity'], 'info')

    def test_tail_copy_is_flagged_and_names_a_tail(self):
        put_effect(self.stock_zone, 'vfx/stock/t', emitter(TAIL, material='stock/m', size=5.0, life=0.3))
        put_weapon(self.zone, 'w_a', trail='vfx/test/t')
        put_effect(self.zone, 'vfx/test/t', emitter(TAIL, material='eq/own', size=6.0, life=0.3),
                   emitter(SPRITE, material='eq/own', size=1.0))
        write(self.zone, 'materials/eq/own.json', {})
        hit = codes(run(self.zone, self.stock()), 'FX-STOCK-COPY')[0]
        self.assertIn('the tail (element 0)', hit['message'])

    def test_file_equal_to_any_stock_zone_copy_is_stock(self):
        second = os.path.join(self.temp.name, 'dump', 'patch_cp_zmb')
        os.makedirs(os.path.join(second, 'particlesystem'))
        put_effect(self.stock_zone, 'vfx/stock/p', emitter(GEO, material='stock/m', points=30, size=1.0, life=0.6))
        patched = emitter(GEO, material='stock/m', points=44, size=1.0, life=0.6)
        put_effect(second, 'vfx/stock/p', patched)
        write(self.zone, 'particlesystem/vfx/stock/p.iw7VFX', effect_bytes('vfx/stock/p', patched))
        put_weapon(self.zone, 'w_a', trail='vfx/stock/p')
        report = run(self.zone, [self.stock_zone, second])
        self.assertEqual(report.facts['own_effects'], [])
        self.assertEqual(codes(report, 'FX-STOCK-COPY'), [])

    def test_an_effect_is_not_a_copy_of_its_own_stock_original(self):
        self._stock_ribbon('vfx/test/trail')
        put_weapon(self.zone, 'w_a', trail='vfx/test/trail')
        put_effect(self.zone, 'vfx/test/trail',
                   emitter(GEO, material='stock/m', points=30, size=100.0, color=0.5, life=0.6),
                   emitter(SPRITE, material='stock/m', size=9.0))
        self.assertEqual(codes(run(self.zone, self.stock()), 'FX-STOCK-COPY'), [])


class SizeLifeTest(Base):
    def setUp(self):
        super().setUp()
        for i, (size, life) in enumerate([(10, 0.2), (20, 0.4), (30, 0.6), (40, 0.8), (50, 1.0)]):
            put_effect(self.stock_zone, 'vfx/stock/s%d' % i,
                       emitter(SPRITE, material='stock/m', size=float(size), life=life, rate=float(i + 2)))
        put_weapon(self.zone, 'w_a', trail='vfx/test/e')
        write(self.zone, 'materials/eq/own.json', {})

    def test_above_every_stock_value_warns_for_size_and_life(self):
        put_effect(self.zone, 'vfx/test/e', emitter(SPRITE, material='eq/own', size=5000.0, life=60.0))
        report = run(self.zone, self.stock())
        size, life = codes(report, 'FX-SIZE-EXTREME'), codes(report, 'FX-LIFE-EXTREME')
        self.assertEqual([f['severity'] for f in size + life], ['warn', 'warn'])
        self.assertEqual({f['proof'] for f in size + life}, {'engine'})
        self.assertEqual(size[0]['evidence']['stock_max'], 50.0)
        self.assertEqual(len(report.questions), 2)

    def test_central_value_is_silent(self):
        put_effect(self.zone, 'vfx/test/e', emitter(SPRITE, material='eq/own', size=30.0, life=0.6, rate=7.0))
        report = run(self.zone, self.stock())
        for code in ('FX-SIZE-EXTREME', 'FX-LIFE-EXTREME', 'FX-SIZE-RANGE', 'FX-LIFE-RANGE'):
            self.assertEqual(codes(report, code), [], code)

    def test_outside_the_band_but_inside_stock_is_a_note(self):
        put_effect(self.zone, 'vfx/test/e', emitter(SPRITE, material='eq/own', size=50.0, life=1.0, rate=9.0))
        report = run(self.zone, self.stock())
        self.assertEqual([f['severity'] for f in codes(report, 'FX-SIZE-RANGE')], ['info'])
        self.assertEqual(codes(report, 'FX-SIZE-EXTREME'), [])

    def test_population_is_per_element_type(self):
        put_effect(self.zone, 'vfx/test/e', emitter(GEO, material='eq/own', points=5, size=5000.0, life=0.5))
        report = run(self.zone, self.stock())
        self.assertEqual(codes(report, 'FX-SIZE-EXTREME'), [])      # no stock ribbon to compare with


class ParityTest(Base):
    def _port(self, report_entries, spec=None, behaviour=None):
        folder = os.path.join(self.temp.name, 'port')
        write(folder, 'fx_report.json', report_entries)
        if spec is not None:
            write(folder, 'spec.json', spec)
        if behaviour is not None:
            write(folder, 'behaviour.txt', behaviour)
        return folder

    def test_skipped_elements_count_mismatch_and_missing_counterparts(self):
        put_weapon(self.zone, 'w_a', trail='vfx/test/a')
        put_effect(self.zone, 'vfx/test/a', emitter(), emitter())
        put_effect(self.zone, 'vfx/test/b', emitter())
        port = self._port(
            [{'effect': 'vfx/test/a', 'emitters': 2,
              'skipped': [{'element': 3, 'reason': 'type 12 (klf) has no template'}], 'bytes': 1},
             {'effect': 'vfx/test/b', 'emitters': 4, 'skipped': [], 'bytes': 1},
             {'effect': 'vfx/test/gone', 'emitters': 1, 'skipped': [], 'bytes': 1}],
            spec={'fx': {'trail': {'bo3': 'x/a', 'iw7': 'vfx/test/a'}, 'impact': {'bo3': 'x/n', 'iw7': 'vfx/test/n'}}},
            behaviour='w_a|ns||k=vfx/test/script|snd\n')
        report = run(self.zone, ports=[port])
        skipped = codes(report, 'FX-PARITY-SKIPPED')
        self.assertEqual([(f['asset'], f['severity'], f['proof']) for f in skipped],
                         [('vfx/test/a', 'warn', 'engine')])
        self.assertIn('element 3', skipped[0]['message'])
        count = codes(report, 'FX-PARITY-COUNT')
        self.assertEqual([f['asset'] for f in count], ['vfx/test/b'])
        none = sorted(f['asset'] for f in codes(report, 'FX-PARITY-NO-COUNTERPART'))
        self.assertEqual(none, ['vfx/test/gone', 'vfx/test/n', 'vfx/test/script'])
        self.assertTrue(report.questions)

    def test_clean_port_is_silent_and_unreached_children_are_noted_once(self):
        put_weapon(self.zone, 'w_a', trail='vfx/test/a')
        put_effect(self.zone, 'vfx/test/a', emitter())
        put_effect(self.zone, 'vfx/test/ring', emitter())
        port = self._port([{'effect': 'vfx/test/a', 'emitters': 1, 'skipped': [], 'bytes': 1},
                           {'effect': 'vfx/test/ring', 'emitters': 1, 'skipped': [], 'bytes': 1}],
                          spec={'fx': {'trail': {'iw7': 'vfx/test/a'}}})
        report = run(self.zone, ports=[port])
        for code in ('FX-PARITY-SKIPPED', 'FX-PARITY-COUNT', 'FX-PARITY-NO-COUNTERPART'):
            self.assertEqual(codes(report, code), [])
        self.assertEqual(len(codes(report, 'FX-NO-CHILD-LINKS')), 1)

    def test_no_note_about_child_links_when_a_link_exists(self):
        put_weapon(self.zone, 'w_a', trail='vfx/test/a')
        put_effect(self.zone, 'vfx/test/a', emitter(child='vfx/test/ring'))
        put_effect(self.zone, 'vfx/test/ring', emitter())
        port = self._port([{'effect': 'vfx/test/ring', 'emitters': 1, 'skipped': [], 'bytes': 1}])
        self.assertEqual(codes(run(self.zone, ports=[port]), 'FX-NO-CHILD-LINKS'), [])

    def test_port_folder_without_report_is_an_error(self):
        put_weapon(self.zone, 'w_a')
        empty = os.path.join(self.temp.name, 'empty')
        os.makedirs(empty)
        self.assertEqual([f['severity'] for f in codes(run(self.zone, ports=[empty]), 'FX-PARITY-NO-REPORT')],
                         ['error'])


class CommandLineTest(Base):
    def test_main_writes_json_and_exit_code(self):
        put_weapon(self.zone, 'w_a', trail='vfx/test/gone')
        put_effect(self.stock_zone, 'vfx/stock/known', emitter())
        out = os.path.join(self.temp.name, 'out.json')
        buffer = io.StringIO()
        old = sys.stdout
        sys.stdout = buffer
        try:
            code = fx.main([self.zone, '--stock', self.stock_zone, '--json', out])
        finally:
            sys.stdout = old
        # a missing effect is a warning for the engine: the run passes, the release gate (--strict) does not
        self.assertEqual(code, 0)
        self.assertIn('FX-MISSING', buffer.getvalue())
        sys.stdout = io.StringIO()
        try:
            self.assertEqual(fx.main([self.zone, '--stock', self.stock_zone, '--strict']), 2)
        finally:
            sys.stdout = old
        with open(out, encoding='utf-8') as handle:
            data = json.load(handle)
        self.assertEqual(data['tool'], 'weapon-fx-audit')
        self.assertEqual(data['counts']['error'], 0)
        self.assertGreaterEqual(data['counts']['warn'], 1)
        self.assertTrue([q for q in data['engine_questions'] if q['kind'] == 'see'])

    def test_template_residue_is_reported_for_the_effects_group(self):
        stock_pkg = {'name': 'stock_pkg', 'vfx': {'viewFlashEffect': {'type': 1, 'fx': 'vfx/stock/flash'}}}
        write(self.stock_zone, 'vfxpkg/stock_pkg.json', stock_pkg)
        write(self.stock_zone, 'weapons/stock_gun.json', {'szInternalName': 'stock_gun', 'vfxImpactType': 31,
                                                           'weapDef': {'vfxPackage': 'stock_pkg'}})
        put_effect(self.stock_zone, 'vfx/stock/flash', emitter())
        write(self.zone, 'weapons/w_a.json', {'szInternalName': 'w_a', 'vfxImpactType': 31,
                                              'weapDef': {'vfxPackage': 'stock_pkg'}})
        report = run(self.zone, self.stock())
        residue = [f for f in report.findings if f['code'].startswith('FX-TEMPLATE')]
        self.assertTrue(residue)


if __name__ == '__main__':
    unittest.main()

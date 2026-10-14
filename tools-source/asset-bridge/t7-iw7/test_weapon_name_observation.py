from pathlib import Path
import unittest
import prepare_weapon_name_observation as p


def record(seq, body, tid=17):
    return p.PREFIX + f'seq={seq} tid={tid} ' + body + '\n'


def enabled():
    return record(0, 'kind=enabled scope=historical_f23_startup weapon_presence=unknown')


def enter(seq=1, call=0, kind=23, name=b'authored_fixture_weapon', state='read', tid=17):
    nul = int(state == 'read')
    ref = int(bool(name) and name.startswith(b','))
    return record(seq, f'kind=enter call={call} type={kind} read={state} length={len(name)} '
                  f'nul={nul} reference={ref} name_hex={name.hex() or "-"} '
                  'caller=00000001401DB2C5 header_present=1', tid)


def returned(seq=2, call=0, kind=23, tid=17, present=1):
    return record(seq, f'kind=return call={call} type={kind} result_present={present}', tid)


def finished(seq=3, entered=1, returned_count=1, overflow=0, failed=0):
    return record(seq, f'kind=finished entered={entered} returned={returned_count} '
                  f'overflow={overflow} write_failed={failed}')


class ParserTests(unittest.TestCase):
    def parse(self, text):
        return p.split_observation(text)[1]

    def test_four_types_observed_without_asset_availability_claim(self):
        for kind in range(23, 27):
            with self.subTest(kind=kind):
                result = self.parse(enabled()+enter(kind=kind)+returned(kind=kind)+finished())
                self.assertEqual(result['outcome'], 'NamesObserved')
                self.assertEqual(result['weapon_types_seen'], [kind])
                for flag in ('ready','asset_availability_verified','default_resolution_verified',
                             'weapon_role_bindings_verified','asset_zone_ownership_verified','runtime_compatible'):
                    self.assertFalse(result[flag])

    def test_legacy_text_is_preserved_exactly(self):
        legacy = 'other observer\r\nunchanged F text\n'
        self.assertEqual(p.split_observation(legacy+enabled()+finished(1,0,0))[0], legacy)

    def test_absence_differs_from_finite_no_name_observation(self):
        self.assertEqual(self.parse('legacy\n')['outcome'], 'Absent')
        self.assertEqual(self.parse(enabled()+finished(1,0,0))['outcome'], 'NoNamesObserved')
        self.assertFalse(self.parse(enabled()+finished(1,0,0))['asset_availability_verified'])

    def test_missing_return_or_finish_is_incomplete(self):
        for text in (enabled(), enabled()+enter(), enabled()+enter()+finished(2,1,0),
                     enabled()+enter()+returned()):
            with self.subTest(text=text):
                self.assertEqual(self.parse(text)['outcome'], 'Incomplete')

    def test_refused_or_prefix_names_never_complete(self):
        for state, name in (('getter_exception',b''),('null',b''),('unreadable',b''),
                            ('prefix',b'x'*96),('read',b'')):
            with self.subTest(state=state):
                self.assertEqual(self.parse(enabled()+enter(state=state,name=name)+returned()+finished())['outcome'],
                                 'Incomplete')

    def test_comma_name_remains_reference_not_resolution(self):
        result = self.parse(enabled()+enter(name=b',authored_fixture_weapon')+returned()+finished())
        self.assertEqual(result['records'][1]['reference'],1)
        self.assertEqual(result['records'][1]['name_hex'],b',authored_fixture_weapon'.hex())
        self.assertFalse(result['default_resolution_verified'])

    def test_null_return_does_not_gain_availability(self):
        result = self.parse(enabled()+enter()+returned(present=0)+finished())
        self.assertEqual(result['records'][2]['result_present'],0)
        self.assertFalse(result['asset_availability_verified'])

    def test_eight_calls_overflow_and_total_output_bound(self):
        text=enabled()
        for i in range(8): text += enter(1+i*2,i,23+i%4,b'x'*95)+returned(2+i*2,i,23+i%4)
        text += record(17,'kind=overflow')+finished(18,8,8,1)
        self.assertLess(len(text),p.MAX_BYTES)
        self.assertEqual(len(self.parse(text)['records']),19)
        self.assertEqual(self.parse(text)['outcome'],'Incomplete')

    def test_write_failure_or_missing_whole_line_is_incomplete(self):
        self.assertEqual(self.parse(enabled()+enter()+returned()+finished(failed=1))['outcome'],'Incomplete')
        self.assertEqual(self.parse(enabled()+finished(1,1,0,failed=1))['outcome'],'Incomplete')

    def test_late_entry_or_return_never_proves_scope_complete(self):
        self.assertEqual(self.parse(enabled()+finished(1,0,0)+enter(2)+returned(3))['outcome'],'Incomplete')
        self.assertEqual(self.parse(enabled()+enter()+finished(2,1,0)+returned(3))['outcome'],'Incomplete')
        self.assertEqual(self.parse(enabled()+enter()+finished(2,1,1)+returned(3))['outcome'],'Incomplete')

    def test_orphan_duplicate_and_mismatched_return_refuse(self):
        for body in (returned(),enter()+returned(tid=18),enter()+returned(kind=24),
                     enter()+enter(2),enter()+returned()+returned(3)):
            with self.subTest(body=body), self.assertRaises(ValueError): self.parse(enabled()+body)

    def test_finish_undercount_duplicates_and_overflow_mismatch_refuse(self):
        for text in (enabled()+enter()+finished(2,0,0),enabled()+finished(1,0,1),
                     enabled()+finished(1,0,0)+finished(2,0,0),
                     enabled()+record(1,'kind=overflow')+finished(2,0,0)):
            with self.subTest(text=text), self.assertRaises(ValueError): self.parse(text)

    def test_foreign_types_schema_and_scope_refuse(self):
        good=enabled()+enter()+returned()+finished()
        for a,b in (('type=23','type=22'),('type=23','type=27'),(p.SCHEMA,'wrong/1'),
                    ('weapon_presence=unknown','weapon_presence=verified'),
                    ('historical_f23_startup','mp_freerun_04')):
            with self.subTest(a=a), self.assertRaises(ValueError): self.parse(good.replace(a,b))

    def test_name_width_nul_reference_and_hex_refuse(self):
        good=enabled()+enter()+returned()+finished()
        length=len(b'authored_fixture_weapon')
        for change in ((f'length={length}',f'length={length+1}'),('nul=1','nul=0'),('reference=0','reference=1'),
                       ('name_hex='+b'authored_fixture_weapon'.hex(),'name_hex=00'),
                       ('header_present=1','header_present=2')):
            with self.subTest(change=change), self.assertRaises(ValueError): self.parse(good.replace(*change))
        for name in (b'x'*96,b'x'*97):
            with self.subTest(size=len(name)), self.assertRaises(ValueError): self.parse(enabled()+enter(name=name))

    def test_sequence_thread_line_and_aggregate_bounds_refuse(self):
        for text in (enabled()+enter().replace('seq=1','seq=0'),enabled().replace('tid=17','tid=0'),
                     enabled().replace('tid=17','tid=4294967296'),enabled().replace('seq=0','seq=19'),
                     enabled().rstrip('\n'),enabled()+'[T7_WEAPON_NAMES]'+ 'x'*512+'\n', 'x'*16385):
            with self.subTest(text=text[:100]), self.assertRaises(ValueError): self.parse(text)


class UnusedSourceTests(unittest.TestCase):
    def setUp(self):
        raw=(p.HERE/'native_catalog_add_observation.inc').read_text(encoding='utf-8')
        self.c2='\n'.join('\t'+line if line else '' for line in raw.splitlines())
        self.tu='namespace zonetool::t7\n{\n'+self.c2+'\n}\n'

    def test_exact_existing_module_is_unchanged_and_support_unactivated(self):
        wired=p.wire_unused_module(self.tu)
        self.assertIn(self.c2,wired)
        addition=wired[len(self.tu[:self.tu.index(self.c2)+len(self.c2)]):]
        self.assertNotIn('weapon_names_enable();',addition)
        self.assertNotIn('weapon_names_begin(xasset',addition)
        self.assertNotIn('db_add_xasset_hook.invoke',addition)
        self.assertIn('c2_add_get_name(&asset, &name)',addition)
        self.assertIn('weapon_names_enabled{false}',addition)

    def test_overlay_can_be_removed_to_recover_exact_input(self):
        module=(p.HERE/'native_weapon_name_observation.inc').read_text(encoding='utf-8')
        addition='\n\n'+'\n'.join('\t'+line if line else '' for line in module.splitlines())
        self.assertEqual(p.wire_unused_module(self.tu).replace(addition,''),self.tu)

    def test_changed_missing_duplicate_crlf_and_repeated_input_refuse(self):
        for text in ('namespace zonetool::t7\n{}',self.tu.replace('c2_add_get_name','changed_getter'),
                     self.tu.replace('namespace zonetool::t7','namespace unrelated'),
                     self.tu+'namespace zonetool::t7\n{\n}\n',
                     self.tu+self.c2,self.tu.replace('\n','\r\n'),p.wire_unused_module(self.tu)):
            with self.subTest(text=text[:80]), self.assertRaises((ValueError,RuntimeError)): p.wire_unused_module(text)


if __name__ == '__main__':
    unittest.main()

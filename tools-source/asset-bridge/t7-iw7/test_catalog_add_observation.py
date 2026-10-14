import os
from pathlib import Path
import re
import unittest
import prepare_catalog_add_observation as p
import prepare_message_publication as publication


def record(seq, body, tid=17):
    return p.PREFIX + f'seq={seq} tid={tid} ' + body + '\n'


def context(state='read', name='zm_common', nul=1):
    return f'ff_state={state} ff_nul={nul} ff_name_hex={name.encode().hex()} ff_atomic=0'


def entry(seq=1, call=0, prefix=0, tid=17):
    name = ('2c' if prefix else '') + p.TARGET_HEX
    return record(seq, f'kind=add_enter call={call} type=47 reference_prefix={prefix} name_hex={name} '
                  'caller=00000001401D1234 asset=0000000140123456 ' + context(), tid)


def returned(seq=2, call=0, prefix=0, tid=17):
    return record(seq, f'kind=add_return call={call} reference_prefix={prefix} result=0000000140123456 ' + context(), tid)


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.enabled = record(0, 'kind=enabled')

    def test_exact_comma_and_plain_calls_keep_legacy_bytes(self):
        legacy = 'existing F row\r\n'
        text = legacy + self.enabled + entry() + returned() + entry(3, 1, 1) + returned(4, 1, 1)
        untouched, rows = p.split_observation(text)
        self.assertEqual(untouched, legacy)
        self.assertEqual([r['kind'] for r in rows], ['enabled','add_enter','add_return','add_enter','add_return'])

    def test_entry_without_return_remains_incomplete_evidence(self):
        _, rows = p.split_observation(self.enabled + entry())
        self.assertEqual(len(rows), 2)
        self.assertNotIn('OriginProven', rows[1])
        self.assertNotIn('CataloguePassed', rows[1])

    def test_refused_selection_is_unknown_not_a_target_call(self):
        row = record(1, 'kind=selection_refused type=47 read_state=getter_exception target=unknown')
        _, rows = p.split_observation(self.enabled + row)
        self.assertEqual(rows[1]['kind'], 'selection_refused')
        self.assertNotIn('call', rows[1])
        with self.assertRaises(ValueError): p.split_observation(self.enabled + row + row.replace('seq=1','seq=2'))

    def test_orphan_duplicate_or_mismatched_return_refuses(self):
        for text in (returned(), entry()+returned(tid=18), entry()+returned(prefix=1),
                     entry()+entry(seq=2), entry()+returned()+returned(seq=3)):
            with self.subTest(text=text), self.assertRaises(ValueError): p.split_observation(self.enabled + text)

    def test_exact_selected_name_type_and_schema_refuse_foreign_values(self):
        for change in (('type=47','type=46'), ('reference_prefix=0','reference_prefix=1'),
                       ('name_hex='+p.TARGET_HEX,'name_hex='+'61'*46),
                       (p.SCHEMA,'iw7.t7-zm-observation/1'), ('ff_atomic=0','ff_atomic=1')):
            with self.subTest(change=change), self.assertRaises(ValueError):
                p.split_observation((self.enabled + entry()).replace(*change))

    def test_context_states_are_explicit_and_non_atomic(self):
        for state in ('pointer_unreadable', 'null', 'name_unreadable'):
            text = (self.enabled+entry()).replace(context(),context(state,'',0))
            self.assertEqual(p.split_observation(text)[1][1]['ff_state'],state)
        text = (self.enabled+entry()).replace(context(),context('prefix','x'*64,0))
        self.assertEqual(p.split_observation(text)[1][1]['ff_nul'],0)
        for replacement in (context('read','x'*64,1),context('prefix','short',0),context('null','x',0),context('read','a\0b',1)):
            with self.subTest(replacement=replacement),self.assertRaises(ValueError):
                p.split_observation((self.enabled+entry()).replace(context(),replacement))

    def test_finite_maximum_and_complete_line_bounds(self):
        text=self.enabled+record(1,'kind=selection_refused type=47 read_state=name_unreadable target=unknown')
        for call in range(4): text += entry(2+2*call,call)+returned(3+2*call,call)
        self.assertEqual(len(p.split_observation(text)[1]),10)
        for changed in (text+record(10,'kind=enabled'),self.enabled+entry().rstrip('\n'),
                        self.enabled+entry().replace('seq=1','seq=64'),self.enabled+entry().replace('tid=17','tid=4294967296'),
                        'x'*16385):
            with self.subTest(),self.assertRaises(ValueError):p.split_observation(changed)
        worst=entry(prefix=1,tid=0xffffffff).replace(context(),context('prefix','x'*64,0)).replace('seq=1','seq=63')
        self.assertLessEqual(len(worst.encode())+1,512)  # also admits CRLF


class NativeSourceContractTests(unittest.TestCase):
    def test_module_is_narrow_read_only_and_preserves_error_order(self):
        text=(p.HERE/'native_catalog_add_observation.inc').read_text()
        self.assertEqual(re.search(r'c2_add_target_hex\[\] = "([0-9a-f]+)"',text)[1],p.TARGET_HEX)
        self.assertIn('errno = crt_value; SetLastError(value);',text)
        self.assertIn('asset.type != ASSET_TYPE_RAWFILE',text)
        self.assertIn('current < 4',text)
        self.assertIn('attempt < 8',text)
        for forbidden in ('DB_FindXAssetHeader','DB_LoadXAssets','DB_IsXAssetDefault','strlen(','.create(','std::mutex','std::string'):
            self.assertNotIn(forbidden,text)
        leaf=text.split('static bool c2_add_get_name',1)[1].split('static bool c2_add_exact_name',1)[0]
        self.assertIn('__try { *name = get_asset_name(asset); return true; }',leaf)
        self.assertNotIn('error_guard',leaf)
        self.assertNotIn('db_add_xasset_hook.invoke',leaf)


@unittest.skipUnless(os.environ.get('IW7_T7_SOURCE'),'Pinned owner native source not supplied')
class RealSourceTests(unittest.TestCase):
    def test_existing_call_forwards_once_and_exact_inverse_recovers_base(self):
        outputs,_=publication.render(Path(os.environ['IW7_T7_SOURCE']))
        base=outputs['zonetool.cpp'].decode()
        after=p.wire_cli(base)
        original='db_add_xasset_hook.invoke<XAssetHeader>(type, header)'
        self.assertEqual(base.count(original),1)
        self.assertEqual(after.count(original),1)
        for old,new in reversed(p.edits()):
            self.assertEqual(after.count(new),1)
            after=after.replace(new,old,1)
        module=(p.HERE/'native_catalog_add_observation.inc').read_text()
        block=p.INCLUDES+'\nnamespace zonetool::t7\n{\n'+'\n'.join('\t'+line if line else '' for line in module.splitlines())
        self.assertEqual(after.replace(block,'namespace zonetool::t7\n{',1),base)
        for invalid in (base+'\r',p.wire_cli(base),base.replace(p.edits()[0][0],''),base+p.edits()[1][0]):
            with self.subTest(),self.assertRaises(ValueError):p.wire_cli(invalid)

    def test_getter_signature_is_the_pinned_native_declaration(self):
        root=Path(os.environ['IW7_T7_SOURCE'])
        funcs=(root/'src/zonetool/zonetool/t7/functions.hpp').read_text()
        source=(root/'src/zonetool/zonetool/t7/zonetool.cpp').read_text()
        self.assertIn('get_asset_name(XAsset* asset)',funcs)
        self.assertIn('DB_GetXAssetName{ 0x14019F080 }',funcs)
        self.assertIn('return DB_GetXAssetName(asset);',source)
        self.assertIn('0x1468FD4A8',source)


if __name__=='__main__':unittest.main(verbosity=2)

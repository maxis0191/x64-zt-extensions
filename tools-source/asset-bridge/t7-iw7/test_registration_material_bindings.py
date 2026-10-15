"""Source rendering and authored JSON bounds only; never invokes a compiler/engine."""
import copy
import hashlib
import json
import os
import re
import unittest
import prepare_registration_material_bindings as bindings
import prepare_image_provenance as provenance
import prepare_image_metadata as metadata
import prepare_image_registration_metadata as registration
from test_image_provenance import ProvenanceTransitionTests
from test_image_metadata import MetadataSourceTests
from test_incoming_image_consumer import sample


class MaterialBindingsSourceTests(unittest.TestCase):
    def test_contract_is_closed_and_pending_and_old_inputs_stay_pinned(self):
        c = json.loads((bindings.HERE/bindings.CONTRACT).read_text())
        self.assertEqual((c['source_profile'],c['native_option'],c['report_schema']),
                         (bindings.NAME,bindings.OPTION,bindings.SCHEMA))
        self.assertEqual((c['header_byte_limit'],c['binding_count'],c['snapshot_keys']),
                         (3696,7,json.loads((bindings.HERE/'incoming-image-source-contract.json').read_text())['snapshot_keys']))
        self.assertTrue(c['source_only_pending'])
        for key in ('cpp_qualified','native_observed','ready'): self.assertIs(c[key],False)
        for name, pin in c['files'].items():
            self.assertEqual(bindings.pin((bindings.HERE/name).read_bytes().replace(b'\r\n',b'\n')),pin)
        self.assertEqual(len(c['row_keys']),9)
        source = (bindings.HERE/bindings.MODULE).read_text()
        envelope = source.split('nlohmann::ordered_json result =',1)[1].split('scalar::require(result.dump()',1)[0]
        keys = set(re.findall(r'\{"([a-z0-9_]+)",',envelope)) - set(c['chain_keys'])
        self.assertEqual(keys,set(c['outer_keys']))

    def test_cache_reuses_fault_leaf_and_raw_bool_checks_before_typed_copy(self):
        raw = (bindings.HERE/registration.CAPTURE).read_bytes().replace(b'\r\n',b'\n')
        members = (bindings.HERE/bindings.incoming.MEMBERS).read_bytes().replace(b'\r\n',b'\n')
        derived = bindings.capture_source(raw,members)
        record = derived.split('void record_binding(',1)[1].split('nlohmann::ordered_json incoming_snapshot()',1)[0]
        for token in ('target[offsetof(GfxImage, delayLoadPixels)] <= 1','first == second && first_name == second_name',
                      'recheck();','c >= 0x20'):
            self.assertLess(record.index(token),record.index('GfxImage copied{}'))
        self.assertEqual(derived.count('__declspec(noinline)'),2)
        for token in ('streamedParts[','->pixels','DB_Find','ReadProcessMemory','expected_raw_name'):
            self.assertNotIn(token,record)
        self.assertNotIn('reinterpret_cast<const GfxImage*>',record)
        self.assertIn('copy_fault_ ? nlohmann::ordered_json(nullptr)',derived)

    def test_each_row_finishes_owned_and_global_chain_is_separate(self):
        source = (bindings.HERE/bindings.MODULE).read_text()
        finish = source.split('nlohmann::ordered_json finish(',1)[1]
        for token in ('read.one(', 'read.range(', 'read.name(', 'read.unchanged(', 'query(', 'copy('):
            self.assertNotIn(token,finish)
        self.assertIn('sample.record_binding(binding.image,',source)
        self.assertIn('for (unsigned i = 0; i < binding_count; ++i)',source)
        self.assertNotIn('0xA0AB1041',source)
        entry = (bindings.HERE/bindings.ENTRY).read_text()
        for token in ('db_find','DB_IsXAssetDefault','ASSET_TYPE_IMAGE','lookup','dump_refs'):
            self.assertNotIn(token,entry)
        self.assertLess(entry.index('begin_material_bindings()'),entry.index('resident_export_load_zone('))

    def test_worst_printable_name_authored_json_remains_under_32k(self):
        # C0 controls refuse before publication; quotes/backslashes are the worst remaining escaping.
        name = '\\'*255
        shot = sample(name)
        for key,value in shot['image'].items():
            if type(value) is int and key != 'header_bytes': shot['image'][key] = (1<<32)-1
        chain = dict.fromkeys(('model_header_hex','material_hex','texture_table_hex','image_field_hex'),'f'*16)
        rows = [dict(index=i,binding_hash_u32=(1<<32)-1,usage_u16=65535,image_pointer_present=True,
                     raw_name=name,leading_comma_reference=False,registration_chain=chain,binding_rechecked=True,
                     snapshot=copy.deepcopy(shot)) for i in range(7)]
        self.assertLess(len(json.dumps(rows,separators=(',',':'),ensure_ascii=False).encode())+4096,32768)

    @unittest.skipUnless(os.environ.get('IW7_T7_SOURCE'),'Exact pinned native SOURCE not supplied')
    def test_actual_renderer_and_exact_exclusive_guards(self):
        base = ProvenanceTransitionTests()
        main,cli = base.base()
        main,cli,_ = provenance.overlay(main,cli,base.read)
        main,cli,_ = metadata.overlay(main,cli,base.read)
        main,cli,_ = registration.overlay(main,cli,base.read)
        new_main,new_cli = bindings.overlay(main,cli,base.read)
        c,files,observer,capture,members = bindings.inputs(base.read)
        self.assertEqual((new_main,new_cli),bindings.wire(main,cli,observer,capture,members,files[bindings.MODULE],files[bindings.ENTRY]))
        self.assertLess(len(new_cli.encode()),192*1024)
        bypass = '\t\tif (type == ASSET_TYPE_IMAGE)\n\t\t{\n\t\t\treturn header;\n\t\t}'
        self.assertEqual(new_cli.count(bypass),1)
        self.assertEqual(new_main.count(bindings.FLAG),2)
        derived = bindings.observer_source(observer)
        self.assertLess(derived.index('registration_ = capture('),derived.index('material_bindings_.record('))
        self.assertIn('const auto returned = original(type, incoming);',derived)
        finish = derived.split('finish_material_bindings(bool zone_complete)',1)[1].split('void begin_registration_metadata()',1)[0]
        self.assertNotIn('finish(pointer)',finish)
        for selector,option in (('material_bindings',bindings.OPTION[1:]),('registration_metadata',registration.OPTION[1:]),
                                ('image_metadata',metadata.OPTION[1:]),('provenance',provenance.OPTION[1:])):
            statement = MetadataSourceTests.cli_guard(new_cli,selector)
            expression = compile(MetadataSourceTests.python_predicate(statement),'<bindings guard>','eval')
            self.assertFalse(eval(expression,{'__builtins__':{}},{selector:True,'flags':{option}}))
            other = registration.OPTION[1:] if selector == 'material_bindings' else bindings.OPTION[1:]
            self.assertTrue(eval(expression,{'__builtins__':{}},{selector:True,'flags':{option,other}}))
        with self.assertRaises(ValueError): bindings.overlay(new_main,new_cli,base.read)


if __name__ == '__main__': unittest.main()

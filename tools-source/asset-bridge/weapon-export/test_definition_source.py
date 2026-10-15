"""Finite generator/staging/source preservation checks; never compiles C++."""
import hashlib
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
import generate_definition_readset as generator
import prepare_module as support


class DefinitionSourceTests(unittest.TestCase):
    def corpus(self):
        # Small generated SOURCE fixtures, not replacement native declarations.
        types=re.findall(r'inline bool validate\(Reader& r, const (\w+)\* asset[^;{}]*;',
            support.read_source(support.HERE/'native_definition_fields.inc'))
        self.assertEqual(len(types),41)
        files={name:'// owned declaration fixture '+name+'\n' for name in generator.HEADERS}
        bodies=[]
        for index,native_type in enumerate(types):
            count=1203-40 if index==0 else 1
            macro='ATTACHMENT_DUMP_FIELD' if native_type=='WeaponAttachment' else 'WEAPON_DUMP_FIELD'
            arguments=native_type+'* asset'+(', WeaponCompleteDef* parent' if native_type=='WeaponDef' else '')
            name='dump_complete' if native_type=='WeaponCompleteDef' else 'dump_'+native_type
            if native_type=='WeaponAttachment':name='weapon_attachment::dump'
            else:arguments+=', ordered_json& data'
            bodies.append('void '+name+'('+arguments+') {\n'+''.join(macro+'(field'+str(i)+');\n' for i in range(count))+'}\n')
        filenames=list(generator.SERIALIZERS)
        files[filenames[0]]=''.join(bodies[:-1]);files[filenames[1]]=bodies[-1]
        return files

    def render_fixture(self,files,mutate=None):
        headers={name:hashlib.sha256(files[name].encode()).hexdigest() for name in generator.HEADERS}
        serializers={name:hashlib.sha256(files[name].encode()).hexdigest() for name in generator.SERIALIZERS}
        if mutate:mutate(files)
        with patch.object(generator,'HEADERS',headers),patch.object(generator,'SERIALIZERS',serializers),\
             patch.object(generator,'source',side_effect=lambda path:files[str(path.relative_to(Path('root')/generator.NATIVE)).replace('\\','/')]):
            return generator.render(Path('root'))

    def test_finite_generator_covers_all_functions_macros_and_inline_manual_reads(self):
        text,metadata=self.render_fixture(self.corpus())
        self.assertEqual((metadata['functions'],metadata['macro_fields']),(41,1203))
        for name in ('animOverrides','sfxOverrides','vfxOverrides'):
            self.assertIn('r.inline_objects(&asset->'+name,text)
            self.assertNotIn('r.pointer_array(&asset->'+name,text)
        self.assertIn('original_count < count',text)
        self.assertIn('parent->accuracyGraphKnotCount',text)
        self.assertIn('notetrackSuitEntries',text)

    def test_any_native_source_or_declaration_drift_refuses(self):
        for name in (*generator.HEADERS,*generator.SERIALIZERS):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError,'changed'):
                    self.render_fixture(self.corpus(),lambda files:files.__setitem__(name,files[name]+'// drift\n'))

    def test_unknown_macros_counts_and_pointer_expressions_refuse(self):
        for macro,arguments in (('WEAPON_DUMP_UNKNOWN','a, 4'),('WEAPON_DUMP_FIELD_ARR','a, count'),
                                ('WEAPON_DUMP_FIELD_ALLOC_ARR','a, other->count'),('WEAPON_DUMP_FIELD','a->b'),
                                ('WEAPON_DUMP_STRING_ARR','a, count')):
            with self.subTest(macro=macro):
                with self.assertRaises(ValueError):generator.field_call('WeaponDef',macro,arguments)
        files=self.corpus();name=list(generator.SERIALIZERS)[0]
        files[name]=files[name].replace('WEAPON_DUMP_FIELD(field0);','WEAPON_DUMP_UNKNOWN(field0, 4);',1)
        with self.assertRaisesRegex(ValueError,'Uncovered'):self.render_fixture(files)
        files=self.corpus();files[name]=files[name].replace('WEAPON_DUMP_FIELD(field0);','',1)
        with self.assertRaisesRegex(ValueError,'macro coverage'):self.render_fixture(files)

    def test_array_dispatch_preserves_pinned_inline_camos_and_real_pointer_fields(self):
        for field in ('camoWorldModelMaterialOverride','camoViewModelMaterialOverride'):
            call=generator.field_call('WeaponDef','WEAPON_DUMP_ASSET_ARR',field+', 16')
            self.assertIn('r.inline_objects(&asset->'+field,call)
            self.assertIn('r.asset_field(value,',call)
            with self.assertRaisesRegex(ValueError,'inline asset-array extent'):
                generator.field_call('WeaponDef','WEAPON_DUMP_ASSET_ARR',field+', 15')
        for native,macro,args in (('WeaponDef','WEAPON_DUMP_ASSET_ARR','complexWorldModel, asset->numComplexModels'),
            ('WeaponAttachment','ATTACHMENT_DUMP_ASSET_ARR','worldModelVariations, asset->numModelVariations'),
            ('WeaponAttachment','ATTACHMENT_DUMP_ASSET_ARR','worldModelCamoMaterials, asset->numWorldModelCamoMaterials'),
            ('WeaponDef','WEAPON_DUMP_FIELD_ALLOC_ARR','parallelBounce, 64'),
            ('WeaponAttachment','ATTACHMENT_DUMP_FIELD_ALLOC_ARR','locationDamage, 22')):
            call=generator.field_call(native,macro,args)
            self.assertNotIn('inline_objects',call)
            self.assertTrue(call.startswith(('r.counted_array(', 'r.pointer_array(')))

    def test_script_fixture_uses_dumped_field_and_observes_real_resolver_calls(self):
        fixture=support.read_source(support.HERE/'test_definition_readset.cpp')
        self.assertNotIn('pap.internalName',fixture)
        self.assertIn('pap.attachPoint = 70001',fixture)
        self.assertIn('context.calls == expected_calls',fixture)
        self.assertIn('context.seen == source.pap.attachPoint',fixture)
        functions=generator.functions('''void weapon_attachment::dump(WeaponAttachment* asset) {
// ATTACHMENT_DUMP_SCRIPT_STRING(internalName);
ATTACHMENT_DUMP_SCRIPT_STRING(attachPoint);
}''','owned-fixture.cpp')
        self.assertEqual(generator.MACRO.findall(functions[0][2]),[('ATTACHMENT_DUMP_SCRIPT_STRING','attachPoint')])

    def test_generation_mismatch_refuses_before_staging_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'native'/support.NATIVE_PATH;source.parent.mkdir(parents=True)
            source.write_text('// owned source fixture\n',encoding='utf-8')
            with patch.object(generator,'render',return_value=('partial\n',{})):
                with self.assertRaisesRegex(ValueError,'complete serializer readset differs'):
                    support.stage(root/'native',root/'not-created',player_cli=True)
            self.assertFalse((root/'not-created').exists())

    def test_existing_native_modes_are_byte_preserved_around_new_route(self):
        for name,length,sha,suffix in (
            ('native_player_templates.inc',21266,'8215ff7afda1f1542731a7f12f3287d1e01eccb7846fccbe2d475c880da79575',False),
            ('native_player_cli.hpp',1641,'7514e9de096c2c5e03a9910f56ff82c1f469ee504f56926db73489a2034227aa',False),
            ('native_player_cli.inc',1474,'5e3c86e2e03046742c3899f9ca07954fffb52df897251930651be8b4d152a018',True)):
            text=support.read_source(support.HERE/name)
            preserved=text[-length:] if suffix else text[:length]
            self.assertEqual(hashlib.sha256(preserved.encode()).hexdigest(),sha)

    def test_production_gate_has_no_unguarded_copy_fallback_or_enum_conversion(self):
        reader=support.read_source(support.HERE/'native_definition_readset.hpp')
        self.assertIn('return (copy && copy(&result, address, sizeof(T), context))',reader)
        self.assertNotIn('std::memcpy',reader)
        self.assertIn('if (!load(address, raw, field)) return false;',reader)
        gate=support.read_source(support.HERE/'native_definition_gate.hpp')
        self.assertLess(gate.index('validate(reader, weapon)'),gate.index('serialize(weapon, pap)'))
        self.assertIn('base_type != 1 || pap_type != 0 || pap_flag != 1',gate)
        leaf=support.read_source(support.HERE/'native_definition_access.hpp')
        self.assertIn('code == EXCEPTION_ACCESS_VIOLATION ? EXCEPTION_EXECUTE_HANDLER : EXCEPTION_CONTINUE_SEARCH',leaf)
        self.assertNotIn('EXCEPTION_CONTINUE_EXECUTION',leaf)
        self.assertNotIn('catch',leaf)
        module=support.read_source(support.HERE/'native_player_templates.inc').split('void dump_iw7_player_pair_definitions(',1)[1]
        self.assertEqual(module.count('player_weapon_definitions::registered_asset('),2)
        self.assertNotIn('get_asset_name(',module)
        self.assertNotIn('load_depending',module.replace('// Keep dump=false: no global dispatcher/hook or build load_depending.',''))
        self.assertIn('globals.dump = false',module)
        self.assertIn('weapon_def::dump(',module);self.assertIn('weapon_attachment::dump(',module)


if __name__=='__main__':
    unittest.main()

"""Pure Source/RSP/contract tests; no prepare(), compiler, SDK, PE or native IO."""
import copy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import prepare_build as build
import prepare_registration_bindings_build as recipe
import prepare_image_provenance as provenance
import prepare_image_metadata as metadata
import prepare_image_registration_metadata as registration
from test_image_provenance import ProvenanceTransitionTests as BaseRenderer


class RegistrationBindingsBuildTests(unittest.TestCase):
    def read(self,path,limit,expected=None):
        raw=path.read_bytes().replace(b'\r\n',b'\n')
        self.assertLessEqual(len(raw),limit)
        if expected:self.assertEqual(hashlib.sha256(raw).hexdigest(),expected)
        return raw

    def test_exclusive_typed_selection_refuses_before_preparation_io(self):
        self.assertFalse(recipe.selected(SimpleNamespace(image_registration_metadata_v1=True)))
        self.assertTrue(recipe.selected(SimpleNamespace(image_registration_metadata_v1=True,image_registration_bindings_v1=True)))
        for args in (dict(image_registration_bindings_v1=1),dict(image_registration_bindings_v1=True),
                     dict(image_registration_bindings_v1=True,image_registration_metadata_v1=1),
                     dict(image_registration_bindings_v1=True,image_registration_metadata_v1=True,image_incoming_header_v1=True)):
            with self.assertRaises(ValueError):recipe.selected(SimpleNamespace(**args))
        with patch.object(build,'path_checked',side_effect=AssertionError('Preparation IO reached')) as io:
            with self.assertRaises(ValueError):build.prepare(SimpleNamespace(image_registration_bindings_v1=True))
            io.assert_not_called()

    def test_only_new_explicit_profile_gets_existing_448k_ceiling(self):
        base=dict(provenance_profile=True,metadata_profile=True,registration_profile=True)
        payload={'source':b'x'*(384*1024+1)}
        with self.assertRaises(ValueError):build.require_preparation_bounds(b'{}',payload,**base)
        build.require_preparation_bounds(b'{}',payload,bindings_profile=True,**base)
        for args in (dict(bindings_profile=True),dict(bindings_profile=1,**base),dict(bindings_profile=True,incoming_profile=True,**base)):
            with self.assertRaises(ValueError):build.require_preparation_bounds(b'{}',payload,**args)
        with self.assertRaises(ValueError):build.require_preparation_bounds(b'{}',{'source':b'x'*(448*1024+1)},bindings_profile=True,**base)

    def test_fixtures_are_immutable_inputs_with_separate_39_then_41_counts(self):
        old=self.read(recipe.HERE/registration.FIXTURE,32768)
        new=self.read(recipe.HERE/recipe.producer.FIXTURE,32768)
        baseline=recipe.baseline_source(old);combined=recipe.combined_source(new)
        self.assertIn('#include "selected_image_material_bindings_observer.hpp"',baseline)
        self.assertIn('int original_registration_fixture_main()',baseline)
        self.assertIn('if (checks != 39)',baseline)
        self.assertIn('#include "bindings_registration_baseline_fixture.cpp"',combined)
        self.assertNotIn('void setup(',combined)
        self.assertNotIn('memory_state memory(',combined)
        self.assertNotIn('&memory',combined)
        self.assertLess(combined.index('original_registration_fixture_main() != 0'),combined.index('checks = 0;'))
        self.assertIn('if (checks != 41)',combined)
        for raw,fn in ((old,recipe.baseline_source),(new,recipe.combined_source)):
            with self.assertRaises(ValueError):fn(raw+b'\n')

    def test_contract_and_profile_remain_source_only_and_schema_closed(self):
        c=recipe.source_contract(self.read)
        self.assertEqual((c['legacy_checks'],c['new_checks'],c['total_checks']),(39,41,80))
        profile={'SourceOnlyPending':True};calls=[]
        def pin(path):calls.append(path);return dict(Path=str(path),Bytes=1,SHA256='0'*64)
        recipe.extend_profile(profile,Path('C:/authored output/prepared'),pin)
        self.assertEqual(len(calls),15)
        self.assertEqual(profile['Name'],recipe.producer.NAME)
        self.assertTrue(profile['SourceOnlyPending']);self.assertFalse(profile['BindingsCPPQualified'])
        self.assertEqual(profile['BindingsTotalChecks'],80)
        qualified_base={'SourceOnlyPending':False,'FixtureProof':{'authored':'retained base proof'}}
        recipe.extend_profile(qualified_base,Path('C:/authored output/prepared'),pin)
        self.assertIs(qualified_base['SourceOnlyPending'],False)
        self.assertIn('FixtureProof',qualified_base)
        for bad in (True,40,'39'):
            altered=copy.deepcopy(c);altered['legacy_checks']=bad
            with self.assertRaises(ValueError):recipe.source_contract(lambda *args:json.dumps(altered).encode())
        for role in ('validator','source','generated'):
            altered=copy.deepcopy(c)
            if role=='validator':altered['validator']=None
            elif role=='source':altered['source_pins'][recipe.producer.MODULE]=None
            else:altered['generated']['prepared/'+recipe.producer.CAPTURE_NAME]=None
            with self.assertRaises(ValueError):recipe.source_contract(lambda *args:json.dumps(altered).encode())

    @unittest.skipUnless(os.environ.get('IW7_T7_SOURCE'),'Exact pinned native SOURCE not supplied')
    def test_actual_source_transition_changes_one_rsp_token_and_preserves_parent_api(self):
        base=BaseRenderer();main,cli=base.base()
        base_reads=set()
        def parent_read(path,limit,expected=None):base_reads.add(path);return self.read(path,limit,expected)
        main,cli,_=provenance.overlay(main,cli,parent_read)
        main,cli,_=metadata.overlay(main,cli,parent_read)
        main,cli,_=registration.overlay(main,cli,parent_read)
        observer=registration.observer_source(base.read(recipe.HERE/provenance.HELPER,32768)).encode()
        args=['/nologo','/Iauthored includes',str(recipe.HERE/registration.FIXTURE),'/link'];before=args.copy()
        prepared=Path('C:/authored output/prepared')
        new_reads=set()
        def new_read(path,limit,expected=None):new_reads.add(path);return self.read(path,limit,expected)
        m,c,marker,generated,new_args=recipe.transition(main,cli,observer,args,new_read,prepared)
        added={path.name for path in new_reads-base_reads}
        self.assertEqual(added,{'prepare_registration_bindings_build.py',recipe.CONTRACT,recipe.VALIDATOR,
            'prepare_incoming_image_metadata.py','prepare_registration_material_bindings.py',recipe.producer.CONTRACT,
            recipe.producer.MODULE,recipe.producer.ENTRY,recipe.producer.FIXTURE,recipe.incoming.MEMBERS})
        self.assertEqual((173+len(added)+len(generated),167+len(added)+len(generated)),(187,181))
        self.assertEqual(args,before)
        self.assertEqual(new_args,['/nologo','/Iauthored includes',str(prepared/recipe.COMBINED),'/link'])
        contract=recipe.source_contract(self.read)
        self.assertEqual({name:recipe.producer.pin(raw) for name,raw in generated.items()},contract['generated'])
        self.assertEqual(recipe.producer.pin(m.encode()),contract['producer']['main'])
        self.assertEqual(recipe.producer.pin(c.encode()),contract['producer']['cli'])
        self.assertTrue(marker['SourceOnlyPending'])
        for key in ('CPPQualified','NativeObserved','Ready'):self.assertIs(marker[key],False)
        self.assertEqual(marker['TotalFixtureChecks'],80)
        self.assertEqual(marker['BaseCLISHA256'],recipe.incoming.BASE_PAIR['cli'][1])
        for invalid in ([],[str(recipe.HERE/registration.FIXTURE)]*2,True,[True]):
            with patch.object(Path,'open',side_effect=AssertionError('IO')):
                with self.assertRaises(ValueError):recipe.transition(main,cli,observer,invalid,self.read,prepared)


if __name__=='__main__':unittest.main()

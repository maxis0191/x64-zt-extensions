"""Owned Source fixtures only; no actual Analysis/PREP, opaque input or CPP."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import prepare_definition_cohort as recipe


class RecipeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.base=self.root/'historical-source';self.base.mkdir()
        self.native=self.root/'unopened-native';self.output=self.root/'future-source'
        old_prepared=self.base/'prepared';old_prepared.mkdir();old_run=self.base/'runtime/cpp-WAIT-ROOT'
        self.retained=[dict(Path=str(self.root/'opaque'/(str(i)+'.obj')),Bytes=1,SHA256='a'*64) for i in range(412)]
        self.retained += [dict(Path=str(self.root/'opaque'/(str(i)+'.bin')),Bytes=1,SHA256='b'*64) for i in range(738)]
        self.native_pin=dict(Path=str(self.native/recipe.support.definition_readset.NATIVE/'structs.hpp'),
            Bytes=recipe.NATIVE_HEADER[0],SHA256=recipe.NATIVE_HEADER[1])
        self.retained.append(self.native_pin)
        self.parent=dict(Schema='iw7.player-template-cohort-source/1',NativeSourcePin=recipe.support.SOURCE_PIN,
            PairProfileCLI=True,PrimaryGuardFixture=True,RetainedObjects=412,LinkedObjectCount=413,
            RetainedInputPins=self.retained,ParentBindings=[dict(Path='expected-'+str(i)) for i in range(171)],
            PreparedRoot=str(old_prepared),RunRoot=str(old_run),RunnerBinding=dict(Path=str(self.base/'old-support/Run-PlayerTemplateBuild.ps1')),
            Compiler=str(self.root/'unopened-cl.exe'),SourceBindings=[],OwnDirectIncludeCoverage=[],Providers={},Environment={},
            ExcludedObject=dict(Path='excluded.obj'),ObservedTransitiveSourcePins=[],PreparedBindings=[],Stages=[])
        for name,count in (('name',8),('argv',18),('primary',36)):
            self.parent['Stages'].extend([
                dict(Name=name+'-compile',Stage='Compile',Image=self.parent['Compiler'],Arguments=['@'+str(old_prepared/(name+'.rsp'))],DeadlineSeconds=120,Artifacts=[]),
                dict(Name=name+'-test',Stage='Probe',Image=str(old_run/(name+'-compile')/(name+'.exe')),Arguments=[],ExpectedChecks=count,ExpectedStdout='old\n',DeadlineSeconds=15,Artifacts=[])])
        self.parent['Stages'].extend([
            dict(Name='iw7',Stage='Compile',Image=self.parent['Compiler'],Arguments=['@'+str(old_prepared/'iw7.rsp')],DeadlineSeconds=120,Artifacts=[]),
            dict(Name='link',Stage='Link',Image=str(self.root/'unopened-link.exe'),Arguments=['@'+str(old_prepared/'link.rsp')],DeadlineSeconds=120,Artifacts=[])])
        for name in ('name','argv','primary','iw7','link'):
            raw=(str(self.base)+'/'+name+' Source response\n').encode()
            if name=='link':raw=('\n'.join('"'+p['Path']+'"' for p in self.retained[:412])+'\n"'+str(old_run/'iw7/iw7-player-cli.obj')+'"\n').encode()
            path=old_prepared/(name+'.rsp');path.write_bytes(raw)
            self.parent['PreparedBindings'].append(dict(Path=str(path),Bytes=len(raw),SHA256=hashlib.sha256(raw).hexdigest()))
        self.source_pins=[];self.texts={}
        for name in recipe.SUPPORT_FILES:
            pin,raw=recipe.read_text(recipe.HERE/name);self.source_pins.append(pin);self.texts[name]=raw.decode('utf-8-sig').replace('\r\n','\n').encode()
        self.plan_pin=dict(Path=str(self.base/'cohort-source-plan.json'),Bytes=1,SHA256=recipe.PLAN_SHA,IsText=True)
        self.capsule='# Original H1 capsule source fixture '+str(self.base)+' '+str(Path(self.parent['RunnerBinding']['Path']))+' '+recipe.PLAN_SHA+'\n'

    def arguments(self):
        return (self.root/'composed','f'*40,'c'*64,self.base,self.native,self.output)

    def fake_inputs(self,*_):
        return dict(revisions={'x64-zt-extensions':'f'*40}),copy.deepcopy(self.source_pins),dict(self.texts)

    def fake_reference(self,*_):
        return copy.deepcopy(self.parent),[dict(self.plan_pin)],self.capsule

    def test_default_no_output_no_native_read_no_process_and_null_candidate(self):
        with patch.object(recipe,'source_inputs',side_effect=self.fake_inputs),patch.object(recipe,'historical_reference',side_effect=self.fake_reference),\
             patch.object(recipe.support,'stage') as stage:
            report=recipe.prepare(*self.arguments())
        stage.assert_not_called();self.assertFalse(self.output.exists());self.assertFalse(self.native.exists())
        self.assertEqual((report['Stages'],report['ChecksAuthored']),(10,[8,28,36,100]));self.assertTrue(report['ExpectedNoEffects'])
        for name in ('NativeInputsRead','SDKInputsRead','NativeTypesLoaded','LeaseAcquired','ProcessStarted','CPPExecuted','SourceOutputCreated','RunRootCreated','Ready'):
            self.assertIs(report[name],False)
        self.assertIsNone(report['CandidateBytes']);self.assertIsNone(report['CandidateSHA256'])

    def test_source_prepare_copies_actual100_fixture_and_keeps_expected_objects_only(self):
        def stage(native,prepared,player_cli):
            # Only this Source unit fixture substitutes the external native TU.
            # The production entry always calls the pinned full generator.
            self.assertTrue(player_cli);self.assertEqual(native,self.native)
            target=prepared/recipe.support.NATIVE_PATH;target.parent.mkdir(parents=True)
            target.write_text('// owned small TU Source fixture\n',encoding='utf-8')
            (prepared/'module-source.json').write_text('{}\n',encoding='utf-8')
            return dict(build_extension=dict(definition_fixture_checks_authored=100),compiled=False)
        with patch.object(recipe,'source_inputs',side_effect=self.fake_inputs),patch.object(recipe,'historical_reference',side_effect=self.fake_reference),\
             patch.object(recipe.support,'stage',side_effect=stage):
            report=recipe.prepare(*self.arguments(),execute=True)
        self.assertTrue(report['SourceOutputCreated']);self.assertFalse((self.output/'runtime').exists());self.assertFalse(self.native.exists())
        self.assertFalse(report['ExpectedNoEffects'])
        plan=json.loads((self.output/'cohort-source-plan.json').read_text())
        self.assertEqual(len(plan['Stages']),10);self.assertEqual([p['ExpectedChecks'] for p in plan['Stages'] if p['Stage']=='Probe'],[8,28,36,100])
        self.assertEqual(plan['RetainedInputPins'],self.parent['RetainedInputPins']);self.assertEqual(plan['ParentBindings'],self.parent['ParentBindings'])
        self.assertIsNone(plan['CandidateBytes']);self.assertIsNone(plan['CandidateSHA256']);self.assertFalse(plan['ParentCPPQualificationInherited'])
        fixture=self.output/'prepared/test_definition_readset.cpp'
        self.assertEqual(fixture.read_bytes(),self.texts['test_definition_readset.cpp'])
        self.assertIn('player_definition_readset::with_pair',fixture.read_text())
        response=(self.output/'prepared/definition.rsp').read_text()
        self.assertEqual(response,recipe.definition_response(self.output/'prepared',self.output/'runtime/cpp-WAIT-ROOT'))
        self.assertIn('/FI"',response);self.assertIn('test_definition_readset.cpp',response)
        binding=(self.output/'prepared/native_definition_fixture_binding.hpp').read_text()
        self.assertEqual(binding,recipe.binding_header(self.native_pin['Path']))
        self.assertEqual(len(plan['DefinitionFixture']['Files']),5)
        self.assertEqual(len(plan['PreparedBindings']),20)
        self.assertNotIn('Source.InstanceOriginal',json.dumps(plan))

    def test_binary_suffix_rejected_before_any_filesystem_query(self):
        for name in ('candidate.exe','symbols.pdb','kernel32.lib','assetfile17.pak'):
            with patch.object(Path,'is_symlink') as query,patch.object(Path,'open') as opened:
                with self.assertRaisesRegex(ValueError,'before filesystem IO'):recipe.read_text(self.root/name)
                query.assert_not_called();opened.assert_not_called()

    def test_source_growth_duplicate_json_and_nonfinite_metadata_refused(self):
        for raw in (b'{"x":1,"x":2}',b'{"x":NaN}',b'[]'):
            with self.assertRaises(ValueError):recipe.json_source(raw)
        path=self.root/'too-large.json';path.write_bytes(b' '* (recipe.support.CAP+1))
        with self.assertRaisesRegex(ValueError,'Bounded Source'):recipe.read_text(path)

    def test_composed_source_origin_and_content_are_checked_without_native_inputs(self):
        source=self.root/'owned-composed';directory=source/'tools-source/asset-bridge/weapon-export';directory.mkdir(parents=True)
        files=[]
        for name in recipe.SUPPORT_FILES:
            raw=self.texts[name];path=directory/name;path.write_bytes(raw)
            files.append(dict(path=path.relative_to(source).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),commit='f'*40))
        data=dict(schema='iw7.source-workspace/1',product='x64-zt-extensions',revisions={'x64-zt-extensions':'f'*40},files=files)
        manifest=source/'source-workspace.json';raw=json.dumps(data).encode();manifest.write_bytes(raw)
        with patch.object(recipe,'HERE',directory):
            _,pins,texts=recipe.source_inputs(source,'f'*40,hashlib.sha256(raw).hexdigest())
            self.assertEqual(len(pins),len(recipe.SUPPORT_FILES)+1);self.assertEqual(texts['test_definition_readset.cpp'],self.texts['test_definition_readset.cpp'])
            (directory/'test_definition_readset.cpp').write_bytes(b'// updated metadata cannot legitimize a changed Source package\n')
            with self.assertRaisesRegex(ValueError,'Owned reviewed Source input differs'):
                recipe.source_inputs(source,'f'*40,hashlib.sha256(raw).hexdigest())
        self.assertFalse(self.native.exists());self.assertFalse(self.output.exists())

    def test_wrong_historical_header_or_counts_refused_in_default(self):
        for mutate in (lambda p:p.update(RetainedObjects=411),lambda p:p['RetainedInputPins'][-1].update(SHA256='0'*64)):
            original=copy.deepcopy(self.parent);mutate(self.parent)
            with patch.object(recipe,'source_inputs',side_effect=self.fake_inputs),patch.object(recipe,'historical_reference',side_effect=self.fake_reference):
                if self.parent['RetainedObjects']==411:
                    # derive is only reached by admitted preparation, so check
                    # its pure construction gate without invoking real prepare.
                    with self.assertRaisesRegex(ValueError,'historical declarations'):
                        recipe.derive(self.parent,self.output/'prepared',self.output/'runtime/cpp-WAIT-ROOT','f'*40,{},[],[],self.native_pin,self.plan_pin)
                else:
                    with self.assertRaisesRegex(ValueError,'declared native header'):recipe.prepare(*self.arguments())
            self.parent=original
        self.assertFalse(self.output.exists())


if __name__=='__main__':unittest.main()

import hashlib
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import prepare_build as p
import prepare_message_publication as publication


class SelectionTests(unittest.TestCase):
    def fixture(self):
        return SimpleNamespace(zombies_add_observation_c2=True,catalog_message_publication=True,
            selected_streamed_render_only_v2=True,reuse_plan='plan',reuse_compile_receipt='receipt')

    def test_explicit_c2_is_exclusive_and_preserves_default(self):
        self.assertFalse(p.add_observation_selected(SimpleNamespace()))
        self.assertTrue(p.add_observation_selected(self.fixture()))
        for name,values in (('zombies_add_observation_c2',(1,'true',None)),
                            ('catalog_message_publication',(False,1)),('selected_streamed_render_only_v2',(False,1)),
                            ('selected_streamed_static_v1',(True,)),('zombies_catalogue_observation',(True,)),
                            ('reuse_plan',('',None)),('reuse_compile_receipt',('',None))):
            for value in values:
                args=self.fixture();setattr(args,name,value)
                with self.subTest(name=name,value=value),self.assertRaises(ValueError):p.add_observation_selected(args)

    def test_frozen_c_and_foreign_bases_refuse_before_source_reads(self):
        with patch.object(Path,'read_bytes',side_effect=AssertionError('Read before rejecting foreign base')):
            for raw in (b'foreign',None,'text'):
                with self.subTest(),self.assertRaises(ValueError):p.add_observation_transition(raw)

    def test_approved_module_and_adapter_pins_are_exact(self):
        for name,pin in p.ADD_SOURCE_PINS.items():
            raw=(p.HERE/name).read_bytes()
            self.assertEqual((len(raw),hashlib.sha256(raw).hexdigest()),pin)


@unittest.skipUnless(os.environ.get('IW7_T7_SOURCE'),'Pinned owner native source not supplied')
class RealTransitionTests(unittest.TestCase):
    def test_new_transition_leaves_v2_base_and_frozen_c_unchanged(self):
        outputs,_=publication.render(Path(os.environ['IW7_T7_SOURCE']))
        base=outputs['zonetool.cpp'];original=bytes(base)
        self.assertEqual((len(base),hashlib.sha256(base).hexdigest()),p.ADD_BASE_CLI_PIN)
        after,proof=p.add_observation_transition(base)
        self.assertEqual(base,original)
        self.assertEqual((len(after),hashlib.sha256(after).hexdigest()),p.ADD_CLI_PIN)
        self.assertEqual(set(proof),{'Schema','SourceProfile','BaseCLIBytes','BaseCLISHA256','CLIBytes','CLISHA256'})
        self.assertEqual(proof['SourceProfile'],'t7-zombies-catalogue-observation-c2')
        with self.assertRaises(ValueError):p.zombies_observation_transition(base)
        with self.assertRaises(ValueError):p.add_observation_transition(base+b' ')
        with patch.object(Path,'read_bytes',return_value=b'changed'),self.assertRaises(ValueError):p.add_observation_transition(base)
        with patch.object(p.add_observer,'wire_cli',return_value='foreign'),self.assertRaises(ValueError):p.add_observation_transition(base)


if __name__=='__main__':unittest.main(verbosity=2)

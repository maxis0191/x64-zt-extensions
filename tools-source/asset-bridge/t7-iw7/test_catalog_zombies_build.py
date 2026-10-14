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
        return SimpleNamespace(zombies_catalogue_observation=True, catalog_message_publication=True,
            selected_streamed_static_v1=True, reuse_plan='prior-plan', reuse_compile_receipt='prior-receipt')

    def test_explicit_selector_preserves_default_legacy_choice(self):
        self.assertFalse(p.zombies_observation_selected(SimpleNamespace()))
        args=self.fixture();args.zombies_catalogue_observation=False
        self.assertFalse(p.zombies_observation_selected(args))
        self.assertTrue(p.zombies_observation_selected(self.fixture()))

    def test_selector_requires_both_profiles_and_prior_proofs(self):
        for name, values in (
            ('zombies_catalogue_observation', ('true', 1, None)),
            ('catalog_message_publication', (False, 'true', 1)),
            ('selected_streamed_static_v1', (False, 'true', 1)),
            ('reuse_plan', (None, '')), ('reuse_compile_receipt', (None, ''))):
            for value in values:
                args=self.fixture();setattr(args,name,value)
                with self.subTest(name=name,value=value), self.assertRaises(ValueError):
                    p.zombies_observation_selected(args)

    def test_foreign_cli_fails_before_source_reads_or_rendering(self):
        with patch.object(Path,'read_bytes',side_effect=AssertionError('Source read before CLI rejection')):
            for raw in (b'foreign CLI', 'foreign CLI', None):
                with self.subTest(raw=raw), self.assertRaises(ValueError):
                    p.zombies_observation_transition(raw)

    def test_approved_source25_module_and_adapter_are_exact(self):
        for name,pin in p.ZOMBIES_SOURCE_PINS.items():
            raw=(p.HERE/name).read_bytes()
            self.assertEqual((len(raw),hashlib.sha256(raw).hexdigest()),pin)


@unittest.skipUnless(os.environ.get('IW7_T7_SOURCE'),'Retained pinned owner native source not supplied')
class RealSourceTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        outputs,_=publication.render(Path(os.environ['IW7_T7_SOURCE']))
        cls.base=outputs['zonetool.cpp']

    def test_frozen_c_accepts_only_exact_base_and_refuses_new_factory(self):
        original=bytes(self.base)
        if (len(self.base),hashlib.sha256(self.base).hexdigest()) != p.ZOMBIES_BASE_CLI_PIN:
            # New render-only factory must never silently inherit frozen C.
            with self.assertRaises(ValueError): p.zombies_observation_transition(self.base)
            self.assertEqual(self.base,original)
            return
        after,proof=p.zombies_observation_transition(self.base)
        self.assertEqual(self.base,original)
        self.assertEqual((len(self.base),hashlib.sha256(self.base).hexdigest()),p.ZOMBIES_BASE_CLI_PIN)
        self.assertEqual((len(after),hashlib.sha256(after).hexdigest()),p.ZOMBIES_CLI_PIN)
        self.assertEqual(set(proof),{'Schema','SourceProfile','BaseCLIBytes','BaseCLISHA256','CLIBytes','CLISHA256'})
        self.assertEqual(proof['Schema'],'iw7.t7-zm-observation-build/1')
        self.assertEqual(proof['SourceProfile'],'t7-zombies-catalogue-observation-c')
        self.assertNotIn('NativeExecuted',proof)

    @unittest.skipUnless(os.environ.get('IW7_T7_FROZEN_CLI'), 'Frozen reviewed C base not supplied')
    def test_frozen_c_snapshot_keeps_the_exact_positive_transition(self):
        raw = Path(os.environ['IW7_T7_FROZEN_CLI']).read_bytes()
        self.assertEqual((len(raw), hashlib.sha256(raw).hexdigest()), p.ZOMBIES_BASE_CLI_PIN)
        after, proof = p.zombies_observation_transition(raw)
        self.assertEqual((len(after), hashlib.sha256(after).hexdigest()), p.ZOMBIES_CLI_PIN)
        self.assertEqual(proof['BaseCLISHA256'], p.ZOMBIES_BASE_CLI_PIN[1])

    def test_changed_base_changed_module_or_wrong_generated_cli_refuse(self):
        with self.assertRaises(ValueError):p.zombies_observation_transition(self.base+b' ')
        with patch.object(Path,'read_bytes',return_value=b'changed module'),self.assertRaises(ValueError):
            p.zombies_observation_transition(self.base)
        with patch.object(p.zombies_observer,'wire_cli',return_value='foreign generated CLI'),self.assertRaises(ValueError):
            p.zombies_observation_transition(self.base)


if __name__=='__main__':unittest.main(verbosity=2)

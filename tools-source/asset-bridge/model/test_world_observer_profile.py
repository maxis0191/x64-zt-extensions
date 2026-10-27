"""Source-only checks of the ZoneTool-specific observer signature profile."""
import unittest
from pathlib import Path
import prepare_world_observer_build as profile


class SignatureProfileTests(unittest.TestCase):
    def test_only_one_expected_signature_changes(self):
        source = (Path(__file__).resolve().parent.parent / 'world' / 'world_clipmap_observer.hpp').read_bytes()
        patched = profile.apply_zonetool_signature(source)
        self.assertEqual(patched.count(profile.ZONETOOL_SIGNATURE), 1)
        self.assertNotIn(profile.REFERENCE_SIGNATURE, patched)
        self.assertEqual(patched.replace(profile.ZONETOOL_SIGNATURE, profile.REFERENCE_SIGNATURE), source)

    def test_missing_or_ambiguous_signature_refused(self):
        for source in (b'', profile.REFERENCE_SIGNATURE * 2,
                       profile.REFERENCE_SIGNATURE + profile.ZONETOOL_SIGNATURE):
            with self.subTest(source=source), self.assertRaises(ValueError):
                profile.apply_zonetool_signature(source)


if __name__ == '__main__':
    unittest.main()

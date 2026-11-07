"""Synthetic tests for iw7_mod_reference_audit.py (no game data)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iw7_mod_reference_audit as audit  # noqa: E402


class ReferenceAuditTest(unittest.TestCase):
    def test_map_only_reference_is_reported(self):
        refs = {"shredder_bullet": {"weapons"}, "projectile_tag": {"weapons"}, "vm_raygun_t7_idle": {"animpkg"},
                "techset_common": {"materials"}, "wpn_rgun_fire_plr": {"sfxpkg"}}
        maps = {"cp_zmb": {"shredder_bullet", "projectile_tag"}, "cp_rave": {"projectile_tag"}}
        found = audit.audit(refs, own={"vm_raygun_t7_idle"}, common={"techset_common"}, maps=maps)
        self.assertEqual(found, {"shredder_bullet": {"in": ["cp_zmb"], "missing": ["cp_rave"], "used_by": ["weapons"]}})


if __name__ == "__main__":
    unittest.main()

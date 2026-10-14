"""Original metadata fixtures; none is a retail Ray Gun observation."""
import copy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import source_handoff as handoff

ROOT = Path(__file__).resolve().parent


def plan():
    return handoff.read_metadata(ROOT / 'source-plan.json')


def slots():
    return handoff.read_metadata(ROOT.parents[2] / 'weapon' / 'slot-contract.json')


def complete():
    value = plan()
    value['evidence']['OriginalFixture'] = {
        'source_kind': 'retained-bo3-metadata', 'receipt_sha256': 'a' * 64,
        'observed_field': 'Original fixture declaration; not actual native evidence'}
    for role in value['models']:
        value['models'][role] = {'name': 'Synthetic/' + role,
            'evidence_ref': 'OriginalFixture',
            'bone_names': ['tag_origin', 'tag_flash', 'weapon_core']}
    for role in value['clips']:
        value['clips'][role] = {'name': 'Synthetic/' + role,
            'evidence_ref': 'OriginalFixture', 'channel_names': ['weapon_core']}
    for role in value['tags']:
        value['tags'][role] = {'source_name': 'tag_flash', 'evidence_ref': 'OriginalFixture'}
    return value


class SourceHandoffTests(unittest.TestCase):
    def test_unknown_plan_stays_explicitly_unqualified(self):
        report = handoff.check(plan(), slots())
        self.assertEqual(report['references'], [])
        self.assertIn('models.view.identity', report['unresolved_metadata'])
        self.assertIn('clips.reload.identity', report['unresolved_metadata'])
        self.assertFalse(report['metadata_declarations_complete'])
        self.assertFalse(report['ready'])

    def test_source_candidate_cannot_be_promoted_to_runtime_observation(self):
        value = plan()
        value['weapon_name_candidates'][0]['runtime_observed'] = True
        with self.assertRaisesRegex(ValueError, 'runtime promotion'):
            handoff.check(value, slots())

    def test_unpinned_mod_branch_is_not_a_source_binding(self):
        value = plan()
        value['weapon_name_candidates'][0]['source_url'] = (
            'https://github.com/Original/Fixture/blob/main/weapons.csv')
        with self.assertRaisesRegex(ValueError, 'pinned source'):
            handoff.check(value, slots())

    def test_complete_declarations_never_promote_provenance_or_weapon(self):
        report = handoff.check(complete(), slots())
        self.assertTrue(report['metadata_declarations_complete'])
        for key in ('ready', 'provenance_independently_verified', 'native_payload_verified',
                    'hierarchy_bind_influences_verified', 'clip_semantics_verified',
                    'render_verified', 'playable_weapon_verified', 'pap_verified',
                    'projectile_physics_verified', 'evidence_content_read'):
            self.assertIs(report[key], False)

    def test_channel_absent_from_declared_skeleton_is_refused(self):
        value = complete()
        value['clips']['fire']['channel_names'] = ['not_in_view_or_hands']
        with self.assertRaisesRegex(ValueError, 'channel absent'):
            handoff.check(value, slots())

    def test_case_mismatched_channel_is_not_remapped(self):
        value = complete()
        value['clips']['reload']['channel_names'] = ['Weapon_Core']
        with self.assertRaisesRegex(ValueError, 'channel absent'):
            handoff.check(value, slots())

    def test_partial_clip_does_not_invent_view_hands_binding(self):
        value = complete()
        value['models']['hands'] = None
        report = handoff.check(value, slots())
        self.assertIn('clips.fire.view_hands_binding', report['unresolved_metadata'])
        self.assertFalse(report['metadata_declarations_complete'])

    def test_muzzle_tag_must_exist_in_its_own_world_model(self):
        value = complete()
        value['models']['world']['bone_names'] = ['tag_origin']
        with self.assertRaisesRegex(ValueError, 'Tag world_muzzle'):
            handoff.check(value, slots())

    def test_case_ambiguous_bones_and_asset_identity_are_refused(self):
        value = complete()
        value['models']['view']['bone_names'] += ['TAG_FLASH']
        with self.assertRaisesRegex(ValueError, 'case-ambiguous bone'):
            handoff.check(value, slots())
        value = complete()
        value['models']['world']['name'] = 'synthetic/view'
        with self.assertRaisesRegex(ValueError, 'Case-ambiguous asset'):
            handoff.check(value, slots())

    def test_unbound_evidence_cannot_supply_an_asset(self):
        value = complete()
        value['clips']['idle']['evidence_ref'] = 'Missing'
        with self.assertRaisesRegex(ValueError, 'Unbound evidence'):
            handoff.check(value, slots())

    def test_changed_displaced_slot_identity_is_refused(self):
        contract = copy.deepcopy(slots())
        contract['iw7_slots'][107], contract['iw7_slots'][109] = (
            contract['iw7_slots'][109], contract['iw7_slots'][107])
        with self.assertRaisesRegex(ValueError, 'slot identity mismatch'):
            handoff.check(plan(), contract)

    def test_injected_runtime_claim_and_reference_prefix_are_refused(self):
        value = complete()
        value['models']['view']['ready'] = True
        with self.assertRaisesRegex(ValueError, 'unexpected or missing fields'):
            handoff.check(value, slots())
        value = complete()
        value['models']['view']['name'] = ',unresolved_reference'
        with self.assertRaisesRegex(ValueError, 'Invalid exact'):
            handoff.check(value, slots())

    def test_duplicate_keys_refused_before_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'metadata.json'
            path.write_text('{"name":"first","name":"second"}', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
                handoff.read_metadata(path)

    def test_oversized_growing_input_is_bounded_before_decode(self):
        stream = io.BytesIO(b'\xff' * (handoff.LIMIT + 100))
        with patch.object(Path, 'open', return_value=stream):
            with self.assertRaisesRegex(ValueError, 'exceeds 64 KiB'):
                handoff.read_metadata(Path('never-opened.json'))


if __name__ == '__main__':
    unittest.main()

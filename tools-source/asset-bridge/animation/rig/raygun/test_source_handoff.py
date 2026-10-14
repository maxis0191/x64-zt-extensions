"""Original metadata fixtures; none is a retail Ray Gun observation."""
import copy
from pathlib import Path
import tempfile
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

import source_handoff as handoff

ROOT = Path(__file__).resolve().parent


def plan():
    return handoff.read_metadata(ROOT / 'source-plan.json')


def slots():
    return handoff.read_metadata(ROOT.parents[2] / 'weapon' / 'slot-contract.json',
                                 limit=handoff.SLOT_LIMIT)


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
            with self.assertRaisesRegex(ValueError, 'duplicate JSON field'):
                handoff.read_metadata(path)

    def test_non_json_and_windows_special_paths_refused_before_metadata_or_open(self):
        for path in ('authored.exe', 'report.json:stream', 'C:relative.json',
                     'NUL.json', r'\\.\C:\report.json', r'\\?\C:\report.json'):
            with self.subTest(path=path), patch.object(Path, 'lstat') as meta, \
                    patch.object(Path, 'open') as opened:
                with self.assertRaises(ValueError):
                    handoff.read_metadata(path)
                meta.assert_not_called()
                opened.assert_not_called()

    def test_oversize_empty_nonregular_and_reparse_refused_without_open(self):
        for mode, size, attributes in ((stat.S_IFREG, handoff.LIMIT + 1, 0),
                                      (stat.S_IFREG, 0, 0), (stat.S_IFDIR, 4, 0),
                                      (stat.S_IFREG, 4, 0x400)):
            info = SimpleNamespace(st_mode=mode, st_size=size, st_file_attributes=attributes)
            with self.subTest(mode=mode, size=size, attributes=attributes), \
                    patch.object(Path, 'lstat', return_value=info), \
                    patch.object(Path, 'open') as opened:
                with self.assertRaises(ValueError):
                    handoff.read_metadata('metadata.json')
                opened.assert_not_called()

    def test_normal_json_reuses_io_without_image_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'normal.json'
            path.write_bytes(b'{"ordinary_source":true}')
            self.assertEqual(handoff.read_metadata(path), {'ordinary_source': True})

    def test_opened_handle_identity_and_size_checked_before_read(self):
        declared = SimpleNamespace(st_mode=stat.S_IFREG, st_size=4, st_dev=1,
                                   st_ino=2, st_file_attributes=0)
        for size, inode in ((4, 3), (5, 2)):
            stream = MagicMock()
            stream.__enter__.return_value = stream
            observed = SimpleNamespace(st_mode=stat.S_IFREG, st_size=size, st_dev=1, st_ino=inode)
            with self.subTest(size=size, inode=inode), \
                    patch.object(Path, 'lstat', return_value=declared), \
                    patch.object(Path, 'open', return_value=stream), \
                    patch.object(handoff.metadata_io.os, 'fstat', return_value=observed):
                with self.assertRaisesRegex(ValueError, 'identity/size differs'):
                    handoff.read_metadata('metadata.json')
                stream.read.assert_not_called()

    def test_oversized_growing_input_is_bounded_before_decode(self):
        info = SimpleNamespace(st_mode=stat.S_IFREG, st_size=4, st_dev=1,
                               st_ino=2, st_file_attributes=0)
        stream = MagicMock()
        stream.__enter__.return_value = stream
        stream.read.return_value = b'\xff' * (handoff.LIMIT + 1)
        with patch.object(Path, 'lstat', return_value=info), \
                patch.object(Path, 'open', return_value=stream), \
                patch.object(handoff.metadata_io.os, 'fstat', return_value=info):
            with self.assertRaisesRegex(ValueError, 'changed during bounded read'):
                handoff.read_metadata('metadata.json')
            stream.read.assert_called_once_with(handoff.LIMIT + 1)

    def test_source_contract_is_the_only_explicit_64_kib_input(self):
        path = ROOT.parents[2] / 'weapon' / 'slot-contract.json'
        self.assertGreater(path.stat().st_size, handoff.LIMIT)
        with patch.object(Path, 'open') as opened:
            with self.assertRaisesRegex(ValueError, 'bounded JSON file'):
                handoff.read_metadata(path)
            opened.assert_not_called()
        self.assertEqual(len(handoff.read_metadata(path, limit=handoff.SLOT_LIMIT)['iw7_slots']), 260)

    def test_evidence_and_payload_references_are_never_opened(self):
        value, contract = complete(), slots()
        with patch.object(Path, 'open') as opened:
            report = handoff.check(value, contract)
            self.assertFalse(report['evidence_content_read'])
            opened.assert_not_called()

    def test_nonfinite_json_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'nonfinite.json'
            path.write_bytes(b'{"number":NaN}')
            with self.assertRaisesRegex(ValueError, 'nonfinite JSON'):
                handoff.read_metadata(path)


if __name__ == '__main__':
    unittest.main()

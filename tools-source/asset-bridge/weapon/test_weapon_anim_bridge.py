"""Synthetic structural fixtures only; no retail weapon/clip/native parser."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from weapon_anim_bridge import convert, read_json, validate_package, write_outputs

CONTRACT = json.loads(Path(__file__).with_name('slot-contract.json').read_text())


def fixture():
    donor = {slot['key']:'' for slot in CONTRACT['h1_slots']}
    donor.update({'IDLE':'Synthetic/Idle', 'FIRE':'Synthetic/Fire', 'RELOAD':'Synthetic/Reload',
                  'WEAP_ALT_ANIM_ADJUST':'Synthetic/AltAdjust'})
    template = {'meleeAnimType':3, 'meleeAnimPrimaryCount':2, 'meleeAnimAltCount':1,
                'fireAnimTimesMs':[71,83,97,109],
                'anims':{key:'' for key in CONTRACT['iw7_slots']},
                'timers':{key:(True if kind == 'bool' else 137) for key,kind in CONTRACT['timer_fields'].items()},
                'footsteps':{'footstep':[{'leftCount':2,
                    'step':[{'time':i/4, 'isLeft':i%2 == 0} for i in range(4)],
                    'movement':[{'time':i/8, 'isLeadIn':i%2 == 1} for i in range(4)]} for _ in range(9)]}}
    template['anims']['WEAP_ANIM_INNER_ROOT'] = 'Synthetic/IW7InnerRoot'
    template['anims']['WEAP_ANIM_RAISE'] = 'Synthetic/OldRaise'
    weapon = {'szXAnims':donor, 'szXAnimsRightHanded':None, 'szXAnimsLeftHanded':None,
              'stateTimers':{'fireTime':999}, 'notetrackSoundMap':[{'Key':'fire', 'Value':'synthetic_sound'}]}
    return weapon, {'szXAnims':template}


class WeaponAnimationBridge(unittest.TestCase):
    def test_real_slot_displacements_and_exception(self):
        weapon, templates = fixture()
        result = convert(weapon, templates, 'synthetic_probe', CONTRACT)
        actual = [(x['source_index'],x['target_index'],x['target_key']) for x in result['report']['conversions']]
        self.assertEqual(actual, [(1,107,'WEAP_ANIM_IDLE'), (3,109,'WEAP_ANIM_FIRE'),
                                  (24,171,'WEAP_ANIM_RELOAD'), (132,255,'WEAP_ALT_ANIM_ADJUST')])
        self.assertEqual(sum(x['iw7_index'] is not None for x in CONTRACT['h1_slots']),114)

    def test_native_template_metadata_preserved_and_empty_donor_clears_common_slot(self):
        weapon, templates = fixture()
        before = deepcopy(templates)
        package = convert(weapon, templates, 'synthetic_probe', CONTRACT)['packages']['synthetic_probe_base']
        for key in templates['szXAnims']:
            if key != 'anims':
                self.assertEqual(package[key],templates['szXAnims'][key])
        self.assertEqual(package['anims']['WEAP_ANIM_INNER_ROOT'],'Synthetic/IW7InnerRoot')
        self.assertEqual(package['anims']['WEAP_ANIM_RAISE'],'')
        self.assertEqual(templates,before)

    def test_handedness_keeps_separate_templates_and_links(self):
        weapon, templates = fixture()
        weapon['szXAnimsRightHanded'] = deepcopy(weapon['szXAnims'])
        weapon['szXAnimsRightHanded']['IDLE'] = 'Synthetic/RightIdle'
        templates['szXAnimsRightHanded'] = deepcopy(templates['szXAnims'])
        templates['szXAnimsRightHanded']['fireAnimTimesMs'] = [2,3,5,7]
        result = convert(weapon,templates,'synthetic_probe',CONTRACT)
        self.assertEqual(result['packages']['synthetic_probe_right']['fireAnimTimesMs'],[2,3,5,7])
        self.assertEqual(result['weapondef_links'],{'weapDef':{'szXAnims':'synthetic_probe_base',
             'szXAnimsRightHanded':'synthetic_probe_right','szXAnimsLeftHanded':''}})

    def test_nonempty_unmapped_slot_and_overrides_refused(self):
        weapon,templates = fixture()
        weapon['szXAnims']['SPEED_RELOAD'] = 'Synthetic/SpeedReload'
        with self.assertRaisesRegex(ValueError,'no exact IW7'): convert(weapon,templates,'synthetic_probe',CONTRACT)
        weapon,templates = fixture();weapon['animOverrides'] = [{'attachment':1}]
        with self.assertRaisesRegex(ValueError,'overrides'): convert(weapon,templates,'synthetic_probe',CONTRACT)

    def test_incomplete_unknown_and_numeric_slots_refused(self):
        for bad_key in ('1','idle','WEAP_ANIM_IDLE'):
            weapon,templates = fixture();weapon['szXAnims'][bad_key] = weapon['szXAnims'].pop('IDLE')
            with self.assertRaisesRegex(ValueError,'exact H1'): convert(weapon,templates,'synthetic_probe',CONTRACT)

    def test_missing_template_not_filled_from_other_hand(self):
        weapon,templates = fixture();weapon['szXAnimsLeftHanded'] = deepcopy(weapon['szXAnims'])
        with self.assertRaisesRegex(ValueError,'per active H1'): convert(weapon,templates,'synthetic_probe',CONTRACT)

    def test_case_and_path_ambiguity_refused(self):
        for bad in ('synthetic/idle','../outside','clip\ncommand',',external_reference'):
            weapon,templates = fixture();weapon['szXAnims']['FIRE'] = bad
            with self.assertRaises(ValueError): convert(weapon,templates,'synthetic_probe',CONTRACT)

    def test_timer_range_shape_and_nonfinite_template_refused(self):
        for change in ('uint16','bool','float','missing'):
            weapon,templates = fixture();t = templates['szXAnims']
            if change == 'uint16': t['timers']['iFireDelay'] = 65536
            elif change == 'bool': t['timers']['bHoldFullPrime'] = 1
            elif change == 'float': t['footsteps']['footstep'][0]['step'][0]['time'] = float('inf')
            else: del t['fireAnimTimesMs']
            with self.assertRaises(ValueError): convert(weapon,templates,'synthetic_probe',CONTRACT)

    def test_json_roundtrip_writer_and_no_overwrite(self):
        weapon,templates = fixture();result = convert(weapon,templates,'synthetic_probe',CONTRACT)
        result['report']['input_evidence'] = 'synthetic unit fixture; not a retail dump'
        with tempfile.TemporaryDirectory(prefix='iw7-synthetic-weapon-') as directory:
            root = Path(directory)/'output'
            hashes = write_outputs(result,root)
            package,sha = read_json(root/'animpkg/synthetic_probe_base.json')
            self.assertEqual(package,result['packages']['synthetic_probe_base'])
            self.assertEqual(sha,hashes['animpkg/synthetic_probe_base.json'])
            validate_package(package,CONTRACT)
            with self.assertRaisesRegex(ValueError,'must not exist'): write_outputs(result,root)

    def test_duplicate_json_keys_refused(self):
        with tempfile.TemporaryDirectory(prefix='iw7-synthetic-weapon-') as directory:
            path = Path(directory)/'duplicate.json';path.write_text('{"IDLE":"first","IDLE":"second"}')
            with self.assertRaisesRegex(ValueError,'Duplicate'): read_json(path)

    def test_unconverted_dependencies_and_limits_are_explicit(self):
        weapon,templates = fixture();r = convert(weapon,templates,'synthetic_probe',CONTRACT)['report']
        self.assertEqual(r['unconverted_h1_fields'],['notetrackSoundMap','stateTimers'])
        self.assertIn({'name':'Synthetic/Idle','origins':['h1-unconverted-clip']},r['dependencies'])
        self.assertFalse(r['native_parser_executed'])
        self.assertFalse(r['playable_weapon_verified'])


if __name__ == '__main__': unittest.main()

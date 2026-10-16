"""Authored linkage causals only: no retail input, native tool or game."""
import copy
from dataclasses import FrozenInstanceError
import os
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

BRIDGE = Path(__file__).resolve().parents[2]
for root in (BRIDGE, BRIDGE / 't7-iw7'):
    sys.path.insert(0, str(root))
from animated import fixtures
from animated.preflight import Refusal
from animation.rig import owned_rig_binding as binding


def authored_inputs(prefix='actor_fixture'):
    s = dict(numBones=3, numRootBones=1, numCosmeticBones=0,
             names=[prefix + '_root', prefix + '_hinge', prefix + '_tip'],
             parentList=b'\1\1', tagAngles=struct.pack('<4e', 0, 0, 0, 1) * 2,
             tagPositions=struct.pack('<6f', 1, 0, 0, 1, 0, 0),
             partClassification=bytes(3),
             baseMat=b''.join(struct.pack('<8f', 0, 0, 0, 1, i, 0, 0, 2) for i in range(3)),
             positionLayout='original-declaration-shaped-xyz12')
    positions = struct.pack('<9f', 0, 0, 0, 1, 0, 0, 0, 1, 0)
    attributes = bytes(range(48))
    weights = (fixtures.weight((128, 127), (0, 1)) + fixtures.weight((255,), (2,))
               + fixtures.weight((64, 191), (1, 2)))
    payload = positions + attributes + weights + struct.pack('<3H', 0, 1, 2)
    shared = dict(dataSize=len(payload), flags=0, vertCount=3, indexCount=3,
                  posOffset=0, vertsOffset=36, skinWeightsOffset=84, indicesOffset=120)
    surface = dict(vertCount=3, triCount=1, baseVertOffset=0, baseIndexOffset=0,
                   flags=2, vertListCount=0, partBits=bytes(48))
    clip = fixtures.clip()
    clip['names'] = [s['names'][2], s['names'][0]]
    return s, payload, shared, surface, clip


class OwnedRigBindingTests(unittest.TestCase):
    def refused(self, code, function, *args):
        with self.assertRaises(Refusal) as caught:
            function(*args)
        self.assertEqual(caught.exception.code, code)

    def test_three_bones_partial_shuffled_clip_and_unchanged_skin_ids(self):
        inputs = authored_inputs()
        before = copy.deepcopy(inputs)
        plan = binding.bind_owned_rig(*inputs)
        self.assertEqual(inputs, before)
        self.assertEqual(plan.parent_indices, (None, 0, 1))
        self.assertEqual(plan.clip_channel_to_model_bone, (2, 0))
        self.assertEqual(plan.mapped['new_to_old'], (1, 0, 2))
        self.assertEqual(tuple(row['ids'] for row in plan.mapped['influence_rows']),
                         ((2,), (0, 1), (1, 2)))
        self.assertEqual(plan.mapped['snapshot']['positions'],
                         b''.join(inputs[1][12*i:12*(i+1)] for i in (1, 0, 2)))
        self.assertEqual(plan.mapped['snapshot']['attributes'],
                         b''.join(inputs[1][36+16*i:52+16*i] for i in (1, 0, 2)))
        self.assertEqual(plan.mapped['snapshot']['triangles'], struct.pack('<3H', 1, 0, 2))
        self.assertEqual(plan.inputs['clip']['dataShort'], inputs[4]['dataShort'])
        self.assertEqual(plan.inputs['clip']['randomDataShort'], inputs[4]['randomDataShort'])
        self.assertEqual(plan.inputs['clip']['names'], tuple(inputs[4]['names']))
        self.assertEqual(len(plan.inputs['skeleton']['names']), 3)  # No invented hinge channel.
        binding.require_same_inputs(plan, *inputs)

    def test_actor_and_weapon_use_identical_generic_rules(self):
        actor = binding.bind_owned_rig(*authored_inputs('actor_fixture'))
        weapon = binding.bind_owned_rig(*authored_inputs('weapon_fixture'))
        self.assertEqual(actor.clip_channel_to_model_bone, weapon.clip_channel_to_model_bone)
        self.assertNotEqual(actor.identities['skeleton'], weapon.identities['skeleton'])
        self.assertEqual(actor.mapped['iw7_blend_bytes'], weapon.mapped['iw7_blend_bytes'])

    def test_every_skeleton_field_is_bound_in_identity(self):
        inputs = authored_inputs()
        plan = binding.bind_owned_rig(*inputs)
        for name, value in inputs[0].items():
            changed = copy.deepcopy(inputs)
            if type(value) is bytes:
                changed[0][name] = bytes((value[0] ^ 1,)) + value[1:]
            elif type(value) is list:
                changed[0][name] = list(reversed(value))
            elif type(value) is int:
                changed[0][name] += 1
            else:
                changed[0][name] += '_changed'
            with self.subTest(field=name):
                self.refused('stale_rig_binding', binding.require_same_inputs, plan, *changed)

    def test_full_clip_and_all_three_surface_inputs_are_bound(self):
        inputs = authored_inputs()
        plan = binding.bind_owned_rig(*inputs)
        for group in (2, 3, 4):
            for name, value in inputs[group].items():
                changed = list(copy.deepcopy(inputs))
                if type(value) is bool:
                    changed[group][name] = not value
                elif type(value) is int:
                    changed[group][name] += 1
                elif type(value) is float:
                    changed[group][name] = -value if value else -0.0
                elif type(value) is list:
                    changed[group][name] = list(reversed(value))
                    if changed[group][name] == value:
                        changed[group][name][0] += 1
                else:
                    changed[group][name] = (bytes((value[0] ^ 1,)) + value[1:]) if value else b'\0'
                with self.subTest(group=group, field=name):
                    self.refused('stale_rig_binding', binding.require_same_inputs, plan, *changed)
        changed = list(inputs)
        changed[1] = b'\1' + inputs[1][1:]
        self.refused('stale_rig_binding', binding.require_same_inputs, plan, *changed)

    def test_float_negative_zero_bits_distinct_and_ints_never_coerced(self):
        inputs = authored_inputs()
        positive = binding.bind_owned_rig(*inputs)
        inputs[4]['primedLength'] = -0.0
        negative = binding.bind_owned_rig(*inputs)
        self.assertNotEqual(positive.identities['clip'], negative.identities['clip'])
        self.assertEqual(struct.pack('>d', negative.inputs['clip']['primedLength']), bytes.fromhex('8000000000000000'))
        self.assertEqual(positive.identities['skeleton'], negative.identities['skeleton'])
        for bad in (0, True, float('nan'), float('inf')):
            inputs[4]['primedLength'] = bad
            self.refused('binding_float', binding.bind_owned_rig, *inputs)

    def test_key_insertion_order_does_not_change_typed_identity(self):
        inputs = list(authored_inputs())
        before = binding.bind_owned_rig(*inputs)
        for group in (0, 2, 3, 4):
            inputs[group] = dict(reversed(tuple(inputs[group].items())))
        self.assertEqual(before.identities, binding.bind_owned_rig(*inputs).identities)

    def test_literal_typed_codec_has_type_length_and_binary64_boundaries(self):
        self.assertEqual(binding._encode_value(False), bytes.fromhex('42 00000001 00'))
        self.assertEqual(binding._encode_value(0), bytes.fromhex('55 00000004 00000000'))
        self.assertEqual(binding._encode_value(-0.0), bytes.fromhex('46 00000008 8000000000000000'))
        self.assertEqual(binding._encode_value(b'a'), bytes.fromhex('59 00000001 61'))
        self.assertEqual(binding._encode_value('a'), bytes.fromhex('53 00000001 61'))
        self.assertNotEqual(binding._encode_value(['ab', 'c']), binding._encode_value(['a', 'bc']))

    def test_missing_duplicate_and_wrong_case_names_refuse(self):
        for names, code in ((['missing', 'actor_fixture_root'], 'clip_binding'),
                            (['actor_fixture_root'] * 2, 'bone_names'),
                            (['ACTOR_FIXTURE_TIP', 'actor_fixture_root'], 'clip_binding')):
            inputs = authored_inputs()
            inputs[4]['names'] = names
            self.refused(code, binding.bind_owned_rig, *inputs)

    def test_no_implicit_view_hands_union_or_fake_report_flags(self):
        inputs = authored_inputs()
        inputs[0]['hands'] = dict(inputs[0])
        self.refused('binding_schema', binding.bind_owned_rig, *inputs)
        inputs = authored_inputs()
        inputs[4]['ready'] = True
        self.refused('binding_schema', binding.bind_owned_rig, *inputs)

    def test_parent_and_influence_refusals_still_apply(self):
        for parents in (b'\0\1', b'\1\3'):
            inputs = authored_inputs()
            inputs[0]['parentList'] = parents
            self.refused('parent_distance', binding.bind_owned_rig, *inputs)
        inputs = list(authored_inputs())
        raw = bytearray(inputs[1])
        struct.pack_into('<H', raw, 88, 3)
        inputs[1] = bytes(raw)
        self.refused('weight_bone_ids', binding.bind_owned_rig, *inputs)

    def test_source_profile_restrictions_remain(self):
        for group, field, value, code in (
                (0, 'positionLayout', 'native-xyz12', 'position_stride_unresolved'),
                (0, 'numCosmeticBones', 1, 'cosmetic_bones'),
                (3, 'flags', 3, 'surface_profile'),
                (3, 'partBits', bytes(47) + b'\1', 'part_bits_loss'),
                (4, 'bDelta', True, 'channel_or_delta_loss')):
            inputs = authored_inputs()
            inputs[group][field] = value
            self.refused(code, binding.bind_owned_rig, *inputs)

    def test_all_five_inputs_bounded_before_any_copy_or_codec(self):
        for group, key, value, code in (
                (0, 'names', ['a'] * 256, 'binding_list_bound'),
                (0, 'names', ['x' * 129, 'b'], 'binding_text'),
                (1, None, bytes(256 * 1024 + 1), 'binding_payload'),
                (2, 'dataSize', 2**32, 'binding_integer'),
                (3, 'partBits', bytes(49), 'binding_bytes'),
                (4, 'dataByte', bytes(binding.MAX_BYTES + 1), 'binding_bytes'),
                (4, 'boneCount', [0] * 11, 'binding_list_bound')):
            inputs = list(authored_inputs())
            if key is None:
                inputs[group] = value
            else:
                inputs[group][key] = value
            with self.subTest(group=group, key=key), patch.object(binding, '_value', wraps=binding._value) as checked, patch.object(binding, '_encode') as encode:
                self.refused(code, binding.bind_owned_rig, *inputs)
                self.assertFalse(any(call.kwargs.get('copy') for call in checked.call_args_list))
                encode.assert_not_called()

    def test_clip_aggregate_budget_refuses_before_copy(self):
        inputs = authored_inputs()
        inputs[4]['dataByte'] = bytes(binding.MAX_BYTES)
        with patch.object(binding, '_value', wraps=binding._value) as checked:
            self.refused('binding_byte_budget', binding.bind_owned_rig, *inputs)
            self.assertFalse(any(call.kwargs.get('copy') for call in checked.call_args_list))

    def test_exact_builtin_types_and_bool_int_domains(self):
        class DictSubclass(dict):
            pass
        class ListSubclass(list):
            pass
        for group, field, value, code in (
                (0, 'numBones', True, 'binding_integer'),
                (2, 'flags', False, 'binding_integer'),
                (4, 'bLoop', 1, 'binding_boolean'),
                (0, 'names', ListSubclass(['a', 'b']), 'binding_list'),
                (4, 'dataByte', bytearray(3), 'binding_bytes')):
            inputs = authored_inputs()
            inputs[group][field] = value
            self.refused(code, binding.bind_owned_rig, *inputs)
        inputs = list(authored_inputs())
        inputs[0] = DictSubclass(inputs[0])
        self.refused('binding_schema', binding.bind_owned_rig, *inputs)

    def test_observed_substitution_refuses_before_helpers(self):
        inputs = authored_inputs()
        real = binding._capture
        calls = []
        def capture(*args):
            calls.append(1)
            if len(calls) == 2:
                args[0]['names'][1] += '_changed'
            return real(*args)
        with patch.object(binding, '_capture', side_effect=capture), patch.object(binding, 'preflight_skeleton') as helper:
            self.refused('binding_changed', binding.bind_owned_rig, *inputs)
            helper.assert_not_called()
        self.assertEqual(len(calls), 2)

    def test_equal_python_float_values_with_changed_bits_refuse_between_captures(self):
        inputs = authored_inputs()
        real = binding._capture
        calls = []
        def capture(*args):
            calls.append(1)
            if len(calls) == 2:
                args[4]['primedLength'] = -0.0
            return real(*args)
        with patch.object(binding, '_capture', side_effect=capture), patch.object(binding, 'preflight_skeleton') as helper:
            self.refused('binding_changed', binding.bind_owned_rig, *inputs)
            helper.assert_not_called()

    def test_helpers_receive_retained_snapshot_and_no_caller_alias(self):
        inputs = authored_inputs()
        real = binding.preflight_skeleton
        def validate(owned):
            self.assertIsNot(owned, inputs[0])
            inputs[0]['names'].append('late_mutation')
            return real(owned)
        with patch.object(binding, 'preflight_skeleton', side_effect=validate):
            plan = binding.bind_owned_rig(*inputs)
        self.assertEqual(len(plan.inputs['skeleton']['names']), 3)
        self.assertEqual(plan.clip_channel_to_model_bone, (2, 0))

    def test_deep_freeze_of_inputs_helpers_mapped_and_qualification(self):
        inputs = authored_inputs()
        real = binding.map_owned_source_surface
        originals = []
        def mapped(*args):
            value = real(*args)
            originals.append(value)
            return value
        with patch.object(binding, 'map_owned_source_surface', side_effect=mapped):
            plan = binding.bind_owned_rig(*inputs)
        originals[0]['new_to_old'][0] = 99
        originals[0]['influence_rows'][0]['ids'] = (99,)
        inputs[0]['names'][0] = 'caller_changed'
        self.assertEqual(plan.mapped['new_to_old'], (1, 0, 2))
        self.assertEqual(plan.mapped['influence_rows'][0]['ids'], (2,))
        self.assertEqual(plan.inputs['skeleton']['names'][0], 'actor_fixture_root')
        with self.assertRaises(FrozenInstanceError):
            plan.profile = 'changed'
        def immutable(value):
            self.assertNotIn(type(value), (dict, list))
            if hasattr(value, 'items'):
                with self.assertRaises(TypeError):
                    value['new'] = True
                for item in value.values():
                    immutable(item)
            elif type(value) is tuple:
                for item in value:
                    immutable(item)
        for value in (plan.inputs, plan.mapped, plan.skeleton_checks, plan.clip_checks,
                      plan.identities, plan.qualification):
            immutable(value)
        self.assertTrue(all(value is False for value in plan.qualification.values()))
        for report in (plan.mapped, plan.skeleton_checks, plan.clip_checks):
            for key in ('ready', 'real_t7_provenance', 'engine_verified'):
                self.assertIs(report[key], False)

    def test_ordinary_imports_do_not_change_path_or_use_bare_poison_modules(self):
        code = '''import sys, types
before = list(sys.path)
sys.modules['preflight'] = types.ModuleType('poison_preflight')
sys.modules['reorder_proposal'] = types.ModuleType('poison_reorder')
from animation.rig import owned_rig_binding
from animation.rig.raygun import owned_skin_mapping
from animated import reorder_proposal
assert sys.path == before
assert owned_skin_mapping.regroup_surface is reorder_proposal.regroup_surface
assert owned_rig_binding.preflight_skeleton.__module__ == 'animated.preflight'
assert reorder_proposal.require.__module__ == 'animated.preflight'
'''
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(map(str, (BRIDGE, BRIDGE / 't7-iw7'))))
        result = subprocess.run([sys.executable, '-B', '-S', '-c', code],
                                env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()

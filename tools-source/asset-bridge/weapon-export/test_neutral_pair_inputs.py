"""Owned synthetic report/buffer causals; no captured bodies, files or native work."""
import ast
import copy
import hashlib
import json
import unittest
from unittest.mock import patch

import neutral_pair_inputs as production


WEAPON = 'weapons/sdk_shredder_clone_zm.json'
PAP = 'attachments/sdk_shredder_clone_pap_zm.json'
CSV_PATH = 'zone_source/sdk_shredder_clone_zm.csv'
CSV = b'weapon,sdk_shredder_clone_zm\nattachment,sdk_shredder_clone_pap_zm\n'
FALSE_FLAGS = ('bo3_assets_authenticated', 'external_name_driven_gameplay_verified', 'native_parser_verified',
               'ff_built', 'roundtrip_verified', 'runtime_abi_verified', 'lifetime_verified', 'weapon_granted',
               'projectile_damage_verified', 'physics_qualified', 'retail_pap_transaction_verified', 'gameplay_accepted', 'ready')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return json.dumps(value, separators=(',', ':'), allow_nan=False).encode()


def fixture(weapon=b'{"owned_test":"weapon"}', pap=b'{"owned_test":"attachment"}'):
    # These buffers intentionally are NOT native definitions or captured U1/T2.
    report = dict(schema='iw7.neutral-weapon-clone/1', profile='iw7-shredder-neutral-1-0',
                  weapon='sdk_shredder_clone_zm', pap_attachment='sdk_shredder_clone_pap_zm',
                  source_weapon='iw7_shredder_zm', source_pap_attachment='shredderpap1',
                  pap_attachment_slot='attachments6', upgraded_engine_variant='sdk_shredder_clone_zm+sdk_shredder_clone_pap_zm',
                  observed_base_type=1, observed_pap_type=0, source_enum_map={'base': 'WEAPTYPE_BULLET', 'pap': 'WEAPTYPE_NONE'},
                  source_layout_pin='fab935826c898806855376662a8a03317b3ad8f1', json_mechanics_fields_preserved=True,
                  external_name_driven_gameplay='unverified: private names do not inherit Shredder GSC callbacks',
                  visuals='unchanged IW7 references; dependency bodies not captured',
                  input_sha256={'manifest': sha(b'owned prior manifest'), 'weapon': sha(b'owned prior weapon'), 'pap': sha(b'owned prior pap')},
                  files=[{'path': name, 'bytes': len(raw), 'sha256': sha(raw)}
                         for name, raw in ((WEAPON, weapon), (PAP, pap), (CSV_PATH, CSV))])
    report.update({flag: False for flag in FALSE_FLAGS})
    return report, weapon, pap


class PrivatePairInputTests(unittest.TestCase):
    def validate(self, report):
        raw = encode(report)
        return production.validate_private_pair_report(raw, len(raw), sha(raw))

    def test_positive_closed_report_is_plain_data(self):
        report, _, _ = fixture()
        self.assertEqual(len(report), 30)
        result = self.validate(report)
        self.assertIs(type(result), dict)
        self.assertEqual(result, report)
        self.assertEqual(len(result['files']), 3)
        self.assertTrue(all(result[key] is False for key in FALSE_FLAGS))

    def test_external_raw_pin_precedes_decoder_and_no_self_hash_can_replace_it(self):
        report, _, _ = fixture(); raw = encode(report)
        with patch.object(production.json, 'loads', side_effect=AssertionError('decoder ran before pin')) as decoder:
            for length, digest in ((len(raw) + 1, sha(raw)), (len(raw), '0' * 64), (True, sha(raw)), (len(raw), sha(raw).upper())):
                with self.subTest(length=length, digest=digest):
                    with self.assertRaises(ValueError):
                        production.validate_private_pair_report(raw, length, digest)
            decoder.assert_not_called()
        report['sha256'] = sha(raw)
        with self.assertRaisesRegex(ValueError, 'thirty-key'):
            self.validate(report)

    def test_input_types_and_caps_refuse_before_hash(self):
        report, _, _ = fixture(); raw = encode(report)
        class BytesSubclass(bytes):
            pass
        with patch.object(production.hashlib, 'sha256', side_effect=AssertionError('hash ran before cap/type')) as hashed:
            for value in (bytearray(raw), memoryview(raw), BytesSubclass(raw), raw.decode(), None):
                with self.assertRaises(ValueError):
                    production.validate_private_pair_report(value, len(raw), '0' * 64)
            for length in (0, -1, False, 1.0, '1', 65537):
                with self.assertRaises(ValueError):
                    production.validate_private_pair_report(raw, length, '0' * 64)
            with self.assertRaises(ValueError):
                production.validate_private_pair_report(b'x' * 65537, 65536, '0' * 64)
            hashed.assert_not_called()

    def test_equivalent_report_reserialization_does_not_match_original_raw_pin(self):
        report, _, _ = fixture(); raw = encode(report)
        other = (json.dumps(report, indent=2) + '\n').encode()
        self.assertEqual(json.loads(other), report)
        with self.assertRaisesRegex(ValueError, 'Raw byte length|Raw SHA256'):
            production.validate_private_pair_report(other, len(raw), sha(raw))
        self.assertEqual(production.validate_private_pair_report(other, len(other), sha(other)), report)

    def test_missing_extra_and_nested_keys_are_closed(self):
        report, _, _ = fixture()
        for key in report:
            bad = copy.deepcopy(report); del bad[key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.validate(bad)
        for key in ('source_enum_map', 'input_sha256'):
            for change in ('extra', 'missing'):
                bad = copy.deepcopy(report)
                if change == 'extra': bad[key]['extra'] = '0' * 64
                else: bad[key].pop(next(iter(bad[key])))
                with self.subTest(key=key, change=change), self.assertRaises(ValueError):
                    self.validate(bad)
        bad = copy.deepcopy(report); bad['files'][0]['role'] = 'owned'
        with self.assertRaises(ValueError): self.validate(bad)

    def test_fixed_text_identities_profile_and_source_pin_refuse_drift(self):
        report, _, _ = fixture()
        for key, value in report.items():
            if type(value) is str and key != 'pap_attachment_slot':
                bad = copy.deepcopy(report); bad[key] = value + 'x'
                with self.subTest(key=key), self.assertRaises(ValueError): self.validate(bad)
        for slot in ('attachments', 'attachments2', 'attachments3', 'attachments4', 'attachments5', 'attachments6'):
            good = copy.deepcopy(report); good['pap_attachment_slot'] = slot
            self.assertEqual(self.validate(good)['pap_attachment_slot'], slot)
        for slot in ('attachments7', 'Attachments6', '', None, 6):
            bad = copy.deepcopy(report); bad['pap_attachment_slot'] = slot
            with self.assertRaises(ValueError): self.validate(bad)

    def test_all_flags_and_neutral_integer_types_are_literal(self):
        report, _, _ = fixture()
        for key in FALSE_FLAGS:
            for value in (True, 0, 0.0, None, 'false'):
                bad = copy.deepcopy(report); bad[key] = value
                with self.subTest(key=key, value=value), self.assertRaises(ValueError): self.validate(bad)
        for key in ('observed_base_type', 'observed_pap_type'):
            for value in (True, False, float(report[key]), str(report[key]), 3):
                bad = copy.deepcopy(report); bad[key] = value
                with self.subTest(key=key, value=value), self.assertRaises(ValueError): self.validate(bad)
        for value in (False, 1, 1.0, 'true', None):
            bad = copy.deepcopy(report); bad['json_mechanics_fields_preserved'] = value
            with self.assertRaises(ValueError): self.validate(bad)

    def test_file_set_rejects_duplicates_missing_extras_and_path_aliases(self):
        report, _, _ = fixture()
        for paths in (report['files'][:2], report['files'] + [report['files'][0]], [report['files'][0]] * 3):
            bad = copy.deepcopy(report); bad['files'] = paths
            with self.assertRaises(ValueError): self.validate(bad)
        for path in (WEAPON.upper(), WEAPON.replace('/', '\\'), '../' + WEAPON, 'C:/' + WEAPON,
                     WEAPON + ':stream', WEAPON + '.', WEAPON + ' ', 'weapons/NUL.json', 'neutral-clone.json', None, []):
            bad = copy.deepcopy(report); bad['files'][0]['path'] = path
            with self.subTest(path=path), self.assertRaises(ValueError): self.validate(bad)
        reordered = copy.deepcopy(report); reordered['files'].reverse()
        self.assertEqual(self.validate(reordered), reordered)  # Unique set, no operational CSV ordering claim.

    def test_file_byte_pin_types_and_canonical_hashes(self):
        report, _, _ = fixture()
        for value in (True, 1.0, '1', 0, -1, 2097153):
            bad = copy.deepcopy(report); bad['files'][0]['bytes'] = value
            with self.assertRaises(ValueError): self.validate(bad)
        for value in ('0' * 63, 'a' * 64 + '\n', 'A' * 64, '', None, 1):
            for target in ('file', 'provenance'):
                bad = copy.deepcopy(report)
                if target == 'file': bad['files'][0]['sha256'] = value
                else: bad['input_sha256']['manifest'] = value
                with self.subTest(target=target, value=value), self.assertRaises(ValueError): self.validate(bad)

    def test_csv_pin_is_fixed_even_if_a_new_report_pin_is_supplied(self):
        report, _, _ = fixture()
        for value in (65, 67, True):
            bad = copy.deepcopy(report); bad['files'][2]['bytes'] = value
            with self.assertRaises(ValueError): self.validate(bad)
        bad = copy.deepcopy(report); bad['files'][2]['sha256'] = sha(CSV.replace(b',', b';'))
        with self.assertRaises(ValueError): self.validate(bad)

    def test_strict_json_duplicate_keys_and_wrong_roots(self):
        report, _, _ = fixture(); raw = encode(report)
        duplicate_root = b'{"schema":"iw7.neutral-weapon-clone/1",' + raw[1:]
        duplicate_nested = raw.replace(b'"source_enum_map":{"base":"WEAPTYPE_BULLET",',
            b'"source_enum_map":{"base":"WEAPTYPE_BULLET","base":"WEAPTYPE_BULLET",')
        self.assertNotEqual(duplicate_nested, raw)
        for value in (duplicate_root, duplicate_nested):
            with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
                production.validate_private_pair_report(value, len(value), sha(value))
        for value in (b'null', b'[]', b'1', b'"report"'):
            with self.assertRaises(ValueError): production.validate_private_pair_report(value, len(value), sha(value))

    def test_utf8_trailing_nonfinite_and_surrogate_refusals(self):
        report, _, _ = fixture(); raw = encode(report)
        malformed = [b'\xff', b'\xef\xbb\xbf' + raw, raw + b' null',
                     raw.replace(b'"observed_base_type":1', b'"observed_base_type":NaN'),
                     raw.replace(b'"observed_base_type":1', b'"observed_base_type":Infinity'),
                     raw.replace(b'"observed_base_type":1', b'"observed_base_type":1e999'),
                     raw.replace(b'"profile":"iw7-shredder-neutral-1-0"', b'"profile":"\\ud800"')]
        for value in malformed:
            with self.subTest(value=value[:30]), self.assertRaises(ValueError):
                production.validate_private_pair_report(value, len(value), sha(value))

    def test_real_tree_guards_depth_per_array_and_node_budget(self):
        nested = None
        for _ in range(65): nested = [nested]
        raw = encode(nested)
        with self.assertRaisesRegex(ValueError, 'depth bound'):
            production.validate_private_pair_report(raw, len(raw), sha(raw))
        raw = encode([0] * 8193)
        with self.assertRaisesRegex(ValueError, 'per-array bound'):
            production.validate_private_pair_report(raw, len(raw), sha(raw))
        # Independent production arithmetic: the earlier64KiB raw cap can dominate.
        with self.assertRaisesRegex(ValueError, 'node/depth bound'):
            production._tree_bounds([[0] * 8192 for _ in range(4)])
        production._tree_bounds([[0] * 4097, [0] * 4097])  # Per-array is not a native aggregate proof.

    def test_verifier_revalidates_original_report_and_returns_no_authority(self):
        report, weapon, pap = fixture(); raw = encode(report)
        decoded = production.validate_private_pair_report(raw, len(raw), sha(raw))
        decoded['ready'] = True; decoded['files'][0]['sha256'] = sha(b'other')
        with patch.object(production, 'validate_private_pair_report', wraps=production.validate_private_pair_report) as validate:
            self.assertIsNone(production.verify_private_pair_bytes(raw, len(raw), sha(raw), weapon, pap, CSV))
            validate.assert_called_once_with(raw, len(raw), sha(raw))
        with self.assertRaises(ValueError):
            production.verify_private_pair_bytes(decoded, len(raw), sha(raw), weapon, pap, CSV)

    def test_invalid_report_refuses_before_touching_payload_hashes(self):
        report, _, _ = fixture(); raw = encode(report); original = hashlib.sha256
        with patch.object(production.hashlib, 'sha256', wraps=original) as hashed:
            with self.assertRaisesRegex(ValueError, 'Raw SHA256'):
                production.verify_private_pair_bytes(raw, len(raw), '0' * 64, object(), object(), object())
            self.assertEqual(len(hashed.call_args_list), 1)
            self.assertEqual(hashed.call_args.args, (raw,))

    def test_each_payload_must_be_original_immutable_bytes(self):
        report, weapon, pap = fixture(); raw = encode(report)
        values = [weapon, pap, CSV]
        for index in range(3):
            for replacement in (values[index] + b' ', bytearray(values[index]), memoryview(values[index]), None):
                changed = list(values); changed[index] = replacement
                with self.subTest(index=index), self.assertRaises(ValueError):
                    production.verify_private_pair_bytes(raw, len(raw), sha(raw), *changed)
        changed = list(values); changed[0] = weapon.replace(b'weapon', b'Weapon')
        with self.assertRaisesRegex(ValueError, 'Raw SHA256'):
            production.verify_private_pair_bytes(raw, len(raw), sha(raw), *changed)

    def test_csv_row_order_delimiter_and_newline_mutants_refuse(self):
        report, weapon, pap = fixture(); raw = encode(report)
        for changed in (b'\n'.join(reversed(CSV.rstrip(b'\n').split(b'\n'))) + b'\n',
                        CSV.replace(b',', b';'), CSV.replace(b'\n', b'\r\n'), CSV + b'\0', CSV[:-1]):
            with self.assertRaises(ValueError):
                production.verify_private_pair_bytes(raw, len(raw), sha(raw), weapon, pap, changed)

    def test_raw_binding_does_not_parse_or_qualify_definition_bodies(self):
        report, weapon, pap = fixture(b'\xff\x00synthetic', b'not native JSON')
        raw = encode(report); decoder = production.json.loads
        with patch.object(production.json, 'loads', wraps=decoder) as loads:
            self.assertIsNone(production.verify_private_pair_bytes(raw, len(raw), sha(raw), weapon, pap, CSV))
            self.assertEqual(loads.call_count, 1)
            self.assertEqual(loads.call_args.args[0], raw.decode())

    def test_helpers_do_not_mutate_inputs_or_perform_io(self):
        report, weapon, pap = fixture(); raw = encode(report); original = copy.deepcopy(report)
        with patch('builtins.open', side_effect=AssertionError('pure helper attempted I/O')):
            self.assertEqual(production.validate_private_pair_report(raw, len(raw), sha(raw)), original)
            self.assertIsNone(production.verify_private_pair_bytes(raw, len(raw), sha(raw), weapon, pap, CSV))
        self.assertEqual(report, original)
        self.assertEqual(raw, encode(original))

    def test_module_exports_only_two_helpers_and_imports_no_producer_or_runtime(self):
        self.assertEqual(production.__all__, ('validate_private_pair_report', 'verify_private_pair_bytes'))
        # Source architecture check alongside the behavioral zero-I/O test above.
        import inspect
        tree = ast.parse(inspect.getsource(production))
        imports = {alias.name for node in tree.body if isinstance(node, ast.Import) for alias in node.names}
        self.assertEqual(imports, {'hashlib', 'json', 'math', 're'})
        self.assertFalse(any(isinstance(node, ast.ImportFrom) for node in ast.walk(tree)))


if __name__ == '__main__':
    unittest.main()

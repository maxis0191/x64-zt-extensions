import unittest
import boot_contract as b


class BootContractTests(unittest.TestCase):
    def test_version_two_must_be_explicit_and_cannot_replace_default_v1(self):
        value = b.make_request('fixture_zone', 'fixture/Model_01', 2)
        old = b.command_review(value)
        new = b.command_review(value, version=2)
        self.assertEqual(old['proposed_arguments'][0], '-t7-iw7-model')
        self.assertEqual(new['proposed_arguments'][0], '-t7-iw7-model-v2')
        self.assertEqual(new['private_output_root_key'], old['private_output_root_key'])
        self.assertEqual(b.parse_proposed_arguments(new['proposed_arguments'], version=2), value)
        with self.assertRaises(ValueError): b.parse_proposed_arguments(new['proposed_arguments'])
        with self.assertRaises(ValueError): b.parse_proposed_arguments(old['proposed_arguments'], version=2)
        for version in (True, False, '2', 2.0, 0, 3, None):
            with self.subTest(version=version), self.assertRaises(ValueError):
                b.command_review(value, version=version)

    def test_exact_model_case_path_and_lod_survive(self):
        value = b.make_request('fixture_zone', 'fixture/Model_01', 2)
        review = b.command_review(value)
        self.assertEqual(b.parse_proposed_arguments(review['proposed_arguments']), value)
        self.assertEqual(review['exact_model_names'], ['fixture/Model_01'])
        self.assertEqual(review['xpak_payload_files_allowed'], [])
        self.assertFalse(review['supported_by_unmodified_base_cli'])
        self.assertFalse(review['native_go'])

    def test_generic_existing_commands_cannot_be_mistaken_for_new_target(self):
        for args in (['-dumpzone', 'fixture_zone'], ['dumpzone', 'iw7', 'fixture_zone', 'xmodel'],
                     ['-t7-iw7-model', 'fixture_zone', 'fixture', '0', 'trailing']):
            with self.assertRaises(ValueError): b.parse_proposed_arguments(args)

    def test_path_alias_traversal_and_device_names_refuse(self):
        for name in ('../fixture', '/fixture', 'a//b', 'a/', 'C:/fixture', '\\fixture', ',fixture',
                     'a\n', 'a\0', 'é', 'CON', 'a/lPt9', 'a.', 'a/nul.bin', 'COM1 .x', 'a/CONIN$'):
            with self.assertRaises(ValueError): b.make_request('fixture_zone', name, 0)

    def test_scalar_types_bounds_and_canonical_lod(self):
        for lod in (-1, 6, True, 1.0, '1'):
            with self.assertRaises(ValueError): b.make_request('fixture_zone', 'fixture', lod)
        for text in ('00', '+1', '1 ', '-1', '6'):
            with self.assertRaises(ValueError): b.parse_proposed_arguments([b.PROPOSED_OPTION, 'fixture_zone', 'fixture', text])
        for name in ('x'*256, 'fixture/../other'):
            with self.assertRaises(ValueError): b.make_request('fixture_zone', name, 0)

    def test_legitimate_spelling_and_separators_are_preserved(self):
        for name in ('fixture/Model.v1', r'fixture\Model.v1', 'fixture/model name', 'x'*255):
            self.assertEqual(b.make_request('fixture_zone', name, 0)['model'], name)

    def test_extra_fields_wrong_target_profile_or_nested_zone_refuse(self):
        value = b.make_request('fixture_zone', 'fixture', 0)
        for key, changed in (('target', 't7'), ('profile', 'streamed'), ('zone', 'a/b'), ('extra', True)):
            candidate = {**value, key: changed}
            with self.assertRaises(ValueError): b.validate_request(candidate)

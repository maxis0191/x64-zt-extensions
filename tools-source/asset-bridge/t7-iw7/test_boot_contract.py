import unittest
import boot_contract as b


class BootContractTests(unittest.TestCase):
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
        for name in ('../fixture', '/fixture', 'a//b', 'a/', 'C:/fixture', 'a\\b', ',fixture',
                     'a\n', 'a\0', 'é', 'CON', 'a/lPt9', 'a.' , 'with space'):
            with self.assertRaises(ValueError): b.make_request('fixture_zone', name, 0)

    def test_scalar_types_bounds_and_canonical_lod(self):
        for lod in (-1, 6, True, 1.0, '1'):
            with self.assertRaises(ValueError): b.make_request('fixture_zone', 'fixture', lod)
        for text in ('00', '+1', '1 ', '-1', '6'):
            with self.assertRaises(ValueError): b.parse_proposed_arguments([b.PROPOSED_OPTION, 'fixture_zone', 'fixture', text])
        for name in ('x'*129, 'x'*65, '/'.join(['a']*9)):
            with self.assertRaises(ValueError): b.make_request('fixture_zone', name, 0)

    def test_extra_fields_wrong_target_profile_or_nested_zone_refuse(self):
        value = b.make_request('fixture_zone', 'fixture', 0)
        for key, changed in (('target', 't7'), ('profile', 'streamed'), ('zone', 'a/b'), ('extra', True)):
            candidate = {**value, key: changed}
            with self.assertRaises(ValueError): b.validate_request(candidate)

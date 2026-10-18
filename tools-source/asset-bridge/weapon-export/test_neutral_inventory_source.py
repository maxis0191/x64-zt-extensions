"""Source boundaries and real-renderer checks; no C++/data/package execution."""
import hashlib
import re
import unittest

import prepare_dependency_visitors as production


class NeutralInventorySourceTests(unittest.TestCase):
    def source(self, name):
        return (production.HERE / name).read_text(encoding='utf-8')

    def body(self, text, signature):
        _, opening, end = production.body(text, signature)
        return text[opening:end]

    def test_known_types_are_exactly_the_real_walkers(self):
        common = self.source('native_neutral_dependencies.hpp')
        recognized = set(re.findall(r'case (ASSET_TYPE_\w+):', self.body(common, 'inline bool reference_recognized(')))
        walked = set()
        for name in ('native_weapon_dependencies.inc', 'native_attachment_dependencies.inc'):
            walker = self.source(name)
            self.assertIn('emit_fx(', walker)
            walked.update(re.findall(r'ASSET_TYPE_\w+', walker))
        # Both production walkers call this shared FX discriminant adapter.
        walked.update(re.findall(r'ASSET_TYPE_\w+', self.body(common, 'template<class Sink> bool emit_fx(')))
        self.assertEqual(recognized, walked)
        self.assertEqual(len(recognized), 13)

    def test_strict_policy_and_constructor_cannot_be_widened(self):
        common = self.source('native_neutral_dependencies.hpp')
        policy = self.body(common, 'inline bool reference_supported(')
        self.assertEqual(set(re.findall(r'ASSET_TYPE_\w+', policy)),
                         {'ASSET_TYPE_FX', 'ASSET_TYPE_VFX', 'ASSET_TYPE_RETICLE', 'ASSET_TYPE_RUMBLE'})
        private = common[common.index('    private:'):common.index('    // A distinct descriptive surface')]
        self.assertIn('friend class Inventory;', private)
        self.assertIn('Collector(bool descriptive, Copy copy, void* context)', private)
        self.assertIn('const bool descriptive_;', private)
        self.assertIn(': Collector(false, copy, context)', common)
        self.assertEqual(common.count(': Collector(true, copy, context)'), 1)

    def test_inventory_has_no_rows_or_public_strict_base(self):
        common = self.source('native_neutral_dependencies.hpp')
        inventory = self.body(common, 'class Inventory : private Collector')
        inventory = re.sub(r'//[^\n]*', '', inventory)
        self.assertNotIn('verify_rows', inventory)
        self.assertNotIn('operator ', inventory)
        self.assertIn('!frozen() || blocked_external_count() != 0', inventory)
        self.assertIn('using Collector::references;', inventory)
        self.assertIn('using Collector::edges;', inventory)
        for helper in ('bool read_name(', 'bool read_origin(', 'bool permits('):
            self.assertEqual(common.count(helper), 1)

    def test_contract_and_inventory_are_pure_and_no_activation_was_added(self):
        common = self.source('native_neutral_dependencies.hpp')
        pure = common[:common.index('// Only the legacy adapter')] + common[common.index('inline bool collect_pair'):]
        pure += self.source('native_neutral_pair_contract.hpp')
        pure = re.sub(r'//[^\n]*', '', pure)
        for forbidden in ('zone_base', 'add_asset_of_type', 'load_depending(', 'db_find_', 'dump(',
                          'ignore_assets', 'globals.', 'filesystem::', 'fopen', 'CreateProcess', 'build_zone'):
            self.assertNotIn(forbidden, pure)
        for name in ('prepare_module.py', 'native_player_cli.inc', 'native_player_templates.inc'):
            self.assertNotIn('native_neutral_pair_contract', self.source(name))
            self.assertNotIn('inventory_pair(', self.source(name))

    def test_shared_walkers_remain_the_qualified_bytes(self):
        expected = {'native_weapon_dependencies.inc': 'ee73bd11a29e917c4d633f4379d4356542ef8e4db90dc42cd25b47c6c303694d',
                    'native_attachment_dependencies.inc': 'feb5b198d96a5a0df12ea2fa89acc6376e7bd7953c2dca68be42d167dbad9ce6'}
        for name, pin in expected.items():
            self.assertEqual(hashlib.sha256(self.source(name).encode()).hexdigest(), pin)

    def test_authored_cpp_uses_production_code_and_covers_thirteen_cases(self):
        fixture = self.source('test_neutral_inventory.cpp')
        cases = re.findall(r'\{"([a-z_]+)", ([a-z_]+)\}', fixture)
        self.assertEqual(len(cases), 13)
        self.assertEqual(len(set(cases)), 13)
        for name, function in cases:
            self.assertEqual(name, function)
            self.assertIn('void ' + function + '()', fixture)
        self.assertIn('#include "native_neutral_pair_contract.hpp"', fixture)
        self.assertIn('IW7_NATIVE_STRUCTS_HEADER', fixture)
        self.assertIn('!HasRows<nd::Inventory>::value', fixture)
        self.assertIn('!std::is_convertible_v<nd::Inventory*, nd::Collector*>', fixture)
        self.assertIn('std::swap(claims[0], claims[1])', fixture)
        for forbidden in ('bool visit_weapon(', 'bool visit_attachment(', 'bool check_identities('):
            self.assertNotIn(forbidden, fixture)

    def test_rumble_assessment_and_mixed_claims_are_separate_authored_causals(self):
        fixture = self.source('test_neutral_inventory.cpp')
        assessment = self.body(fixture, 'void rumble_assessment_only()')
        for required in ('nd::inventory_pair(', 'allowed.blocked_external_count() == 0',
                         'blocked.blocked_external_count() == 1',
                         'contract::InventoryState::complete_no_policy_blockers',
                         'contract::InventoryState::complete_policy_blocked'):
            self.assertIn(required, assessment)
        self.assertNotIn('verify_rows', assessment)
        collisions = self.body(fixture, 'void canonical_collisions_both_orders()')
        for required in ('{ASSET_TYPE_RUMBLE, "fixture_rumble", Mode::owned_full}',
                         '{ASSET_TYPE_RUMBLE, ",fixture_rumble", Mode::reference_shell}',
                         'std::swap(rumble[0], rumble[1])'):
            self.assertIn(required, collisions)
        self.assertEqual(collisions.count('contract::check_identities(rumble, 2)'), 2)
        self.assertNotIn('nd::collect_pair(', collisions)
        self.assertIn('inventory.blocked_external_count() == 9', fixture)


if __name__ == '__main__':
    unittest.main()

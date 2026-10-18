"""Finite Source checks only. This module never compiles/imports C++ or a provider."""
import hashlib
import json
from pathlib import Path
import re
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
UNCHANGED = {
    'native_pair_owned_input.hpp': (6833, 'f5c31c73c4e5e5e152bb29bf9efd55008297f81ab7c4b4ec9e562cf2059a44ce'),
    'native_pair_session.hpp': (8349, '65995c3552058107c572c70bd12f2b8134c81550edd87cf584fdbb5176dc7d93'),
    'test_authored_pair_json.cpp': (21305, '55cd60cb30ad753299b44fd05ecbd32854aa4291d124899dc6e6a29e7d1111c7'),
    'native_pair_report.hpp': (12553, '301a8f2a381290abaedd7bd6f87cfe271b0c659af772b41a7873ff37497bd204'),
    'native_pair_bodies.hpp': (33561, '46647a305dca84d8c5bdadbbc6c344387b37000ede41cb07c3c0657da259d52f'),
    'native_pair_body_schema.hpp': (1073140, 'dbedd4632d8bb20686c8c1355d4b0200fc2c6149ba141897007f41252f555b75'),
}
GROUPS = (
    'copy_ingress_guarded_construction', 'adopt_same_objects_no_history',
    'real_preflight_before_components', 'null_and_consumed_ingress_refuse',
    'partial_components_reverse_unwind', 'stable_pair_view_and_builder_lifetime',
    'standard_allocation_frontiers', 'primary_and_cleanup_kept_distinct',
)


class TypedIngressSource(unittest.TestCase):
    def test_existing_owners_preflight_table_and_legacy_are_byte_unchanged(self):
        for name, expected in UNCHANGED.items():
            raw = (HERE / name).read_bytes()
            self.assertEqual((len(raw), hashlib.sha256(raw).hexdigest()), expected, name)

    def test_ingress_and_preflight_transfer_source_order(self):
        text = (HERE / 'native_pair_owned_session.hpp').read_text(encoding='utf-8')
        self.assertLess(text.index('std::unique_ptr<Guards> guards_;'), text.index('std::unique_ptr<Input> raw_;'))
        copy = text.split('OwnedIngress(Copy,', 1)[1].split('OwnedIngress(Adopt,', 1)[0]
        self.assertLess(copy.index('guards_(std::move(guards))'), copy.index('detail::need(bool(guards_))'))
        self.assertLess(copy.index('detail::need(bool(guards_))'), copy.index('std::make_unique<Input>'))
        transfer = text.split('class Transfer final', 1)[1]
        ctor = transfer.split('Transfer(const Transfer&)', 1)[0]
        self.assertIn('ingress_(std::move(ingress))', ctor)
        self.assertIn('validate_owned_pair_bodies(*raw_view_);', ctor)
        for name, owner in (('guards', 'guards_'), ('raw', 'raw_')):
            self.assertRegex(transfer, rf'{name}\(\) noexcept\s*\{{ return std::move\(ingress_->{owner}\); \}}')
        self.assertIn('const Input& input() const && = delete;', text)
        self.assertEqual(text.count('validate_owned_pair_bodies('), 1)
        for forbidden in ('Windows.h', 'filesystem::', 'VirtualAlloc(', 'parse_weapon_json(', 'parse_attachment_json('):
            self.assertNotIn(forbidden, text)

    def test_one_authored_literal_case_has_unchanged_four_raw_roles(self):
        text = (HERE / 'test_pair_owned_session.cpp').read_text(encoding='utf-8')
        raw_block = text.split('original_raw{{\n', 1)[1].split('\n}};', 1)[0]
        raw, parts = [], []
        for match in re.finditer(r'R"IW7AUTH\((.*?)\)IW7AUTH"(\s*,?)', raw_block, re.S):
            parts.append(match[1])
            if match[2].strip() == ',':
                raw.append(''.join(parts).encode('utf-8'))
                parts = []
        self.assertEqual(parts, [])
        self.assertEqual([(len(value), hashlib.sha256(value).hexdigest()) for value in raw], [
            (1764, '7137883b66b4735e5347cb25d7b29c3ec2bc60b66bfcfae33965abd0bcf90807'),
            (22356, '0da006d96531b0d8afc74e6da211911a3c5b71b34c8104101926222bd5f9aa03'),
            (1806, '088c665ca39c03daa3a6c8b84821318389611a5ef5b895223e263a5cdbe5969b'),
            (66, 'f539cb31e182b7648cac4eb4da369e344d0a8da1a877c4fbed1dc23ef105f2c8'),
        ])

    def test_transfer_constructor_is_private_and_only_complete_entry_is_friend(self):
        text = (HERE / 'native_pair_owned_session.hpp').read_text(encoding='utf-8')
        transfer = text.split('class Transfer final', 1)[1].split('template<class Guards, class Components> class TypedOwnedPair final', 1)[0]
        private, public = transfer.split('public:', 1)
        self.assertIn('Transfer(std::unique_ptr<OwnedIngress<Guards>>&&', private)
        self.assertIn('friend auto player_pair_owned_session::make_validated_owned_pair(', private)
        self.assertEqual(private.count('friend '), 1)
        self.assertNotIn('Transfer(std::unique_ptr<OwnedIngress<Guards>>&&', public)
        fixture = (HERE / 'test_pair_owned_session.cpp').read_text(encoding='utf-8')
        self.assertIn('static_assert(!std::is_constructible_v<owned::detail::Transfer<Guard,Components>,', fixture)

    def test_authored_causals_are_present_but_not_execution_evidence(self):
        text = (HERE / 'test_pair_owned_session.cpp').read_text(encoding='utf-8')
        self.assertIn('AUTHORED, NOT COMPILED/LINKED/EXECUTED', text)
        actual = tuple(re.findall(r'\{"([a-z_]+)",\1\}', text))
        self.assertEqual(actual, GROUPS)
        self.assertIn('IW7_TYPED_OWNED_PAIR=8', text)
        for required in ('catch(const player_pair_report::ReportError&', 'catch(const bodies::detail::BodyError&',
                         'report.calls==0', 'std::current_exception()==report.primary',
                         'first_route_size==sizeof(LegacyPair)', 'fail_wrapper_allocation=true',
                         'allocation_fault::live+1==live', 'const unsigned expected[]{5,4,3,2,1,0}'):
            self.assertIn(required, text)
        self.assertNotIn('parse_weapon_json(', text)
        self.assertNotIn('parse_attachment_json(', text)

    def test_declarative_exports_and_honest_documentation(self):
        exports = json.loads((ROOT / 'product.json').read_text(encoding='utf-8'))['exports']
        for name in ('native_pair_owned_session.hpp', 'test_pair_owned_session.cpp', 'test_pair_owned_session_source.py'):
            path = 'tools-source/asset-bridge/weapon-export/' + name
            self.assertEqual(exports.count(path), 1)
        doc = (HERE / 'PAIR-PARSE-SESSION.md').read_text(encoding='utf-8')
        self.assertIn('## Typed guards/raw ingress — inactive Source', doc)
        self.assertIn('copy_with_guards', doc)
        self.assertIn('adopt_owned', doc)
        self.assertIn('AUTHORED, NON-COMPILED', doc)


if __name__ == '__main__':
    unittest.main(verbosity=2)

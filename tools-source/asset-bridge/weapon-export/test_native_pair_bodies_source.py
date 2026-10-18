"""Static integration/finite-dispatch causals only; never compile or execute C++."""
import ast
import hashlib
import json
from pathlib import Path
import re
import unittest

HERE = Path(__file__).resolve().parent
SOURCE_PINS = {
    'native_body_schema.py': (262207, '5e18fe147f2bbc55459f60c4e724dbdd15b86fe4bb23de92562016c2345813db'),
    'neutral_pair_bodies.py': (17221, '820c8580549c3d0e5022e58d5f5bfc120d23db64b9f9f6e4513e05494c178626'),
    'native_pair_owned_input.hpp': (6833, 'f5c31c73c4e5e5e152bb29bf9efd55008297f81ab7c4b4ec9e562cf2059a44ce'),
    'native_pair_report.hpp': (12553, '301a8f2a381290abaedd7bd6f87cfe271b0c659af772b41a7873ff37497bd204'),
    'native_pair_body_schema.hpp': (1073140, 'dbedd4632d8bb20686c8c1355d4b0200fc2c6149ba141897007f41252f555b75'),
}


def source(name):
    return (HERE / name).read_bytes().decode('utf-8').replace('\r\n', '\n')


def schema_literal():
    # Pin every baseline Source before literal decoding. Nothing is imported.
    held_text = {}
    for name, expected in SOURCE_PINS.items():
        raw = (HERE / name).read_bytes()
        if (len(raw), hashlib.sha256(raw).hexdigest()) != expected:
            raise ValueError('Pinned raw baseline Source differs: ' + name)
        held_text[name] = raw.decode('utf-8', errors='strict')
    tree = ast.parse(held_text['native_body_schema.py'])
    assignments = [n for n in tree.body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'SCHEMA' for t in n.targets)]
    if len(assignments) != 1:
        raise ValueError('One SCHEMA literal required')
    return ast.literal_eval(assignments[0].value)


def section(text, first, after):
    return text[text.index(first):text.index(after, text.index(first) + len(first))]


def entry_order(text):
    """Regression check of the real public body, not a runtime verdict."""
    body = text[text.index('inline void validate_owned_pair_bodies('):]
    parts = ('player_pair_report::validate_owned_report(owner);',
             'detail::decode(owner.bytes(player_pair_input::Role::weapon)',
             'detail::decode(owner.bytes(player_pair_input::Role::attachment)',
             'detail::inspect(weapon, attachment, false);',
             'private identity differs', 'neutral BULLET1 required', 'neutral NONE0 required',
             'literal true PAP flag required', 'one private PAP association in declared slot required',
             'detail::inspect(weapon, attachment, true);')
    positions = [body.index(token) for token in parts]
    if positions != sorted(positions) or len(set(positions)) != len(positions):
        raise ValueError('Public report/domain/alignment order differs')
    return body


class NativePairBodiesSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = schema_literal()
        cls.cpp = source('native_pair_bodies.hpp')

    def test_exact_unchanged_baselines_and_two_owned_includes(self):
        self.assertEqual(len(self.schema['types']), 239)
        self.assertEqual(len(self.schema['structures']), 41)
        self.assertEqual(re.findall(r'^#include "([^"]+)"', self.cpp, re.M),
                         ['native_pair_report.hpp', 'native_pair_body_schema.hpp'])
        for forbidden in ('parse_weapon_json(', 'parse_attachment_json(', 'zone_memory',
                          'std::ifstream', 'std::ofstream', 'FILE*', 'LoadLibrary', 'static bool validated'):
            self.assertNotIn(forbidden, self.cpp)
        self.assertEqual(self.cpp.count('inline void validate_owned_pair_bodies('), 1)

    def test_public_report_first_full_frontdoor_before_alignment(self):
        body = entry_order(self.cpp)
        for slot in ('attachments', 'attachments2', 'attachments3', 'attachments4', 'attachments5', 'attachments6'):
            self.assertIn('"' + slot + '"', body)
        self.assertIn("value != ',' + a && value != w && value != ',' + w", body)
        # Causal deletion/order mutants check the actual Source entry, no C++.
        with self.assertRaises(ValueError):
            entry_order(self.cpp.replace('player_pair_report::validate_owned_report(owner);', '', 1))
        with self.assertRaises(ValueError):
            entry_order(self.cpp.replace('detail::inspect(weapon, attachment, false);',
                                        'detail::inspect(weapon, attachment, true);', 1))

    def test_all_table_operations_and_manuals_have_one_finite_dispatch(self):
        operations = {r['op'] for d in self.schema['structures'].values() for r in d['ops']}
        walk = section(self.cpp, 'inline void walk(std::string_view name,', 'inline Trace inspect(')
        named = set(re.findall(r'tag == "([A-Z_]+)"', walk))
        direct = {'FIELD', 'FIELD_RENAME', 'STRING', 'SCRIPT_STRING', 'ASSET', 'FXCOMBINED', 'OPTIONAL', 'MANUAL'}
        self.assertEqual(named, direct)
        self.assertEqual(len(operations), 17)
        self.assertTrue(all('ARR' in name for name in operations - direct))
        arr = section(self.cpp, 'inline void array_rule(', 'inline void manual(')
        for tag in ('ASSET', 'SCRIPT_STRING', 'FXCOMBINED', 'STRING_ARR'):
            self.assertIn('"' + tag + '"', arr)
        manual = section(self.cpp, 'inline void manual(', 'inline void walk(std::string_view name,')
        tags = {r['handler'][0] for d in self.schema['structures'].values()
                for r in d['ops'] if r['op'] == 'MANUAL'}
        self.assertEqual(set(re.findall(r'tag == "([a-z_]+)"', manual)), tags)
        self.assertEqual(len(tags), 8)
        self.assertIn('for (std::size_t i = 0; i < 21; ++i)', manual)
        self.assertIn('for (std::size_t j = 0; j < 3; ++j) walk(', manual)

    def test_same_raw_two_primary_passes_and_no_discard(self):
        decode = section(self.cpp, 'inline Json decode(', 'struct Event {')
        self.assertLess(decode.index('raw.find'), decode.index('Json::sax_parse'))
        self.assertLess(decode.index('Json::sax_parse'), decode.index('Json::parse'))
        self.assertIn('need(Json::sax_parse(raw.begin(), raw.end(), &sax', decode)
        self.assertIn('Json::parse(raw.begin(), raw.end(),', decode)
        self.assertIn('true, false, false', decode)
        self.assertIn('dom.nodes == sax.nodes', decode)
        self.assertIn('dom.max_depth == sax.max_depth', decode)
        self.assertIn('dom.max_array == sax.max_array', decode)
        sax = section(self.cpp, 'struct SaxGuard', 'struct DomGuard')
        self.assertIn("if (c == 'e' || c == 'E') break;", sax)
        self.assertIn('(n != 0 || !nonzero)', sax)
        dom = section(self.cpp, 'struct DomGuard', 'inline Json decode(')
        self.assertNotIn('return false', dom)
        for token in ('depth <= 64', 'nodes < 32768', 'elements < 8192', 'Duplicate decoded key'):
            self.assertIn(token, self.cpp)

    def test_integer_float_and_layout_consumption_remain_distinct(self):
        primitive = section(self.cpp, 'inline void scalar(const Json& value, std::string_view',
                            'inline void scalar(const Json& value, std::uint32_t')
        self.assertLess(primitive.index('std::abs(n) < overflow'), primitive.index('static_cast<float>(n)'))
        self.assertIn('constexpr double overflow = 0x1.ffffffp+127;', primitive)
        self.assertIn('n > maximum ?', primitive)
        self.assertIn('n < -maximum ?', primitive)
        self.assertIn('n == 0 || converted != 0', primitive)
        self.assertIn('name == "WeaponChargeType" && desc.storage_domain_only', primitive)
        self.assertIn('return a.negative ? a.magnitude > b.magnitude', self.cpp)
        asset = section(self.cpp, 'inline void asset(', 'inline void closed(')
        self.assertLess(asset.index('if (!value.is_null())'), asset.index('trace.allocate'))
        walk = section(self.cpp, 'inline void walk(std::string_view name,', 'inline Trace inspect(')
        self.assertIn('tag == "STRING") cstring(value', walk)
        self.assertIn('tag == "SCRIPT_STRING") cstring(value', walk)
        self.assertIn('if (!value.is_null()) { const auto target = element(', walk)
        trace = section(self.cpp, 'struct Trace', 'inline void cstring(')
        for token in ('maximum / unit', 'maximum - total', '8192 - count_value', 'cap - bytes',
                      'script_entries < 65536', 'if (count_value == 0) return;'):
            self.assertIn(token, trace)
        self.assertNotIn('offset = 0', trace)

    def test_exports_once_and_no_existing_consumer_adoption(self):
        manifest = json.loads((HERE.parents[2] / 'product.json').read_text(encoding='utf-8'))
        encoded = json.dumps(manifest)
        for name in ('native_pair_bodies.hpp', 'test_native_pair_bodies.cpp', 'test_native_pair_bodies_source.py'):
            self.assertEqual(encoded.count('tools-source/asset-bridge/weapon-export/' + name), 1)
        for existing in ('native_pair_session.hpp', 'prepare_pair_json_core.py', 'prepare_pair_checked_parse.py'):
            self.assertNotIn('#include "native_pair_bodies.hpp"', source(existing))


if __name__ == '__main__':
    unittest.main()

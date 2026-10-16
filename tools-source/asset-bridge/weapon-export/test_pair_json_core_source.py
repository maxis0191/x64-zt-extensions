"""Owned Source grammar/byte causals only, never a native C++ qualification."""
import ast
import copy
import hashlib
from pathlib import Path
import re
import unittest
from unittest.mock import patch

import authored_pair_json_fixtures as fixtures
import neutral_pair_bodies as bodies
import prepare_pair_json_core as production
from test_neutral_pair_inputs import FALSE_FLAGS, encode, fixture as report_fixture
from test_pair_session_source import corpus as session_corpus, function_body


def digest(text):
    return hashlib.sha256(text.replace('\r\n', '\n').encode()).hexdigest()


def corpus():
    """Minimal owned Source grammar, not vendored native parser data/code."""
    source = session_corpus()
    blocks = {}
    for key, cls, root in [('weapon', 'weapon_def', 'WeaponCompleteDef'), ('attachment', 'weapon_attachment', 'WeaponAttachment')]:
        blocks[key + '_map'] = '\tvoid ' + cls + '::add_script_string(scr_string_t* ptr, const char* str)\n\t{\n\t\tthis->script_strings.emplace_back(ptr, str);\n\t}\n'
        blocks[key + '_macros'] = '#define OWNED_' + key.upper() + ' this->add_script_string(ptr, value)\n'
    names = ['parse', 'parse', 'parse', 'parse', 'parse_weapondef', 'parse_NoteTrackToSoundEntry', 'parse_NoteTrackToSuitSoundEntry', 'parse_extra', 'parse_complete']
    blocks['weapon_helpers'] = ''.join('\tvoid weapon_def::' + name + '(Type' + str(i) + '* asset, ordered_json& data, zone_memory* mem)\n\t{\n' + ('\t\tparse(asset, data, mem);\n' if i < 8 else '') + '\t}\n' for i, name in enumerate(names))
    blocks['weapon_root'] = '\t\tauto asset = mem->allocate<WeaponCompleteDef>();\n\t\tparse_complete(asset, data, mem);\n\t\treturn asset;\n'
    blocks['attachment_helpers'] = '\tvoid parse_att(Type* asset, ordered_json& data, zone_memory* mem)\n\t{\n\t}\n'
    blocks['attachment_dispatch'] = '#define PARSE_ATT(x) parse_att(asset->__att__, data, mem)\n'
    blocks['attachment_root'] = '\t\tauto asset = mem->allocate<WeaponAttachment>();\n\t\tthis->add_script_string(&asset->internalName, asset->szInternalName);\n\t\treturn asset;\n'
    cuts = {}
    for key, cls, root, name in [('weapon', 'weapon_def', 'WeaponCompleteDef', 'weapondef'), ('attachment', 'weapon_attachment', 'WeaponAttachment', 'weaponattachment')]:
        labels = [key + '_map', key + '_macros', key + '_helpers'] + (['attachment_dispatch'] if key == 'attachment' else [])
        text = '#include <std_include.hpp>\n#include "' + name + '.hpp"\nnamespace zonetool::iw7\n{\n' + ''.join(blocks[x] for x in labels)
        text += '\t' + root + '* ' + cls + '::parse(const std::string& name, zone_memory* mem)\n\t{\n\t\t// Owned file-prefix preservation witness\n' + blocks[key + '_root'] + '\t}\n'
        text += '\tvoid ' + cls + '::init(const std::string& name, zone_memory* mem)\n\t{\n\t}\n}\n'
        source[production.NATIVE + 'iw7/assets/' + name + '.cpp'] = text
        for label in labels + [key + '_root']:
            block = blocks[label]; first = text[:text.index(block)].count('\n') + 1
            cuts[label] = (first, first + block.count('\n') - 1, digest(block))
    source[production.STRUCTS] = '// owned opaque-free Source grammar types\n'
    source[production.SESSION_HEADER] = '[[noreturn]] inline void reject_native_activation() { throw 1; }\n'
    return source, blocks, cuts


def render_owned(source, cuts, stage=True):
    pins = {p: digest(v) for p, v in source.items()}
    session_pins = {p: pins[p] for p in production.session.PINS}
    with patch.object(production, 'PINS', pins), patch.object(production, 'CUTS', cuts), patch.object(production.session, 'PINS', session_pins), patch.object(production.session, 'EXPLICIT_HEADER_BYTES', len(source[production.SESSION_HEADER].replace('\r\n', '\n').encode())), patch.object(production.session, 'EXPLICIT_HEADER_SHA256', digest(source[production.SESSION_HEADER])), patch.object(production.memory, 'render', side_effect=lambda v, **_: (v, {})):
        return production.render(source, stage_core=stage)


class PairJsonCoreSourceTests(unittest.TestCase):
    def test_twelve_real_pin_roles_and_checked_memory_pin_remain_explicit(self):
        self.assertEqual(len(production.PINS), 12)
        for path, pin in production.session.PINS.items(): self.assertEqual(production.PINS[path], pin)
        self.assertEqual(production.PINS[production.memory.SOURCE_PATH], production.memory.SOURCE_SHA256)
        self.assertEqual(production.CUTS['weapon_macros'][:2], (30, 190))
        self.assertEqual(production.CUTS['attachment_dispatch'][:2], (664, 673))

    def test_default_is_identity_even_for_original_crlf_without_cut_io_or_staging(self):
        source, _, cuts = corpus(); source = {p: v.replace('\n', '\r\n') for p, v in source.items()}
        with patch.object(production, '_cut', side_effect=AssertionError('DEFAULT extracted core')), patch.object(Path, 'open', side_effect=AssertionError('DEFAULT file IO')):
            out, meta = render_owned(source, cuts, False)
        self.assertEqual(out, source)
        self.assertTrue(all(out[p] is source[p] for p in source))
        self.assertFalse(meta['core_staged']); self.assertFalse(meta['actual_parse'])

    def test_pin_first_refuses_all_drifts_before_cut_or_session(self):
        source, _, _ = corpus(); pins = {p: digest(v) for p, v in source.items()}
        with patch.object(production, 'PINS', pins), patch.object(production, '_cut', side_effect=AssertionError('cut before pins')):
            for path in source:
                bad = dict(source); bad[path] += '// drift\n'
                with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'Pinned core Source drift'): production.render(bad, stage_core=True)

    def test_bounds_and_type_precede_scans_and_hash(self):
        with patch.object(production, 'PINS', {'owned': '0'*64}), patch.object(production, 'sha', side_effect=AssertionError('early hash')):
            for value in (None, b'x', 'x'*2097153, '\0', '\ud800'):
                with self.subTest(value_type=type(value).__name__), self.assertRaises(ValueError): production.render({'owned': value})

    def test_source_roles_and_literal_opt_in_refuse_ambiguity(self):
        source, _, cuts = corpus()
        for bad in ({}, {**source, 'extra': 'x'}):
            with self.assertRaises(ValueError): production.render(bad)
        for flag in (None, 1, 'yes'):
            with self.assertRaises(ValueError): render_owned(source, cuts, flag)

    def test_real_renderer_shares_core_bodies_and_reconstructs_inactive_wrappers(self):
        source, blocks, cuts = corpus(); before = copy.deepcopy(source)
        with patch.object(Path, 'open', side_effect=AssertionError('explicit Source header must avoid IO')):
            out, meta = render_owned(source, cuts)
        self.assertEqual(source, before); self.assertTrue(meta['core_staged'])
        self.assertEqual(meta['staged_rejecting_hooks'], 3)
        for key, name in [('weapon', 'weapondef'), ('attachment', 'weaponattachment')]:
            path = production.NATIVE + 'iw7/assets/' + name + '.cpp'
            restored = out[path].replace('#include "weapon_pair_json_core.hpp"\n', '')
            restored = restored.replace('\t\treturn pair_json::parse_' + key + '_json(data, mem, this->script_strings);\n', blocks[key + '_root'])
            for label in ([key + '_macros', key + '_helpers'] + (['attachment_dispatch'] if key == 'attachment' else [])):
                restored = restored.replace('// Pinned Source moved to pair JSON core: ' + label + '\n', blocks[label])
            session_pins = {p: digest(source[p]) for p in production.session.PINS}
            with patch.object(production.session, 'PINS', session_pins), patch.object(production.session, 'EXPLICIT_HEADER_BYTES', len(source[production.SESSION_HEADER].encode())), patch.object(production.session, 'EXPLICIT_HEADER_SHA256', digest(source[production.SESSION_HEADER])):
                inactive, _ = production.session.render({p: source[p] for p in session_pins}, stage_inactive=True, source_header=source[production.SESSION_HEADER])
            self.assertEqual(restored, inactive[path])
            hook = function_body(out[path], name.replace('weapondef', 'weapon_def').replace('weaponattachment', 'weapon_attachment') + '::parse_checked_inactive(')
            self.assertEqual(re.findall(r'([\w:]+)\(', hook), ['player_pair_session::reject_native_activation'])

    def test_unexpected_cut_and_duplicate_anchor_refuse_without_mutating_input(self):
        source, _, cuts = corpus(); before = copy.deepcopy(source)
        bad = dict(cuts); first, last, _ = bad['weapon_root']; bad['weapon_root'] = (first, last, '0'*64)
        with self.assertRaisesRegex(ValueError, 'Pinned core cut'): render_owned(source, bad)
        self.assertEqual(source, before)
        with self.assertRaisesRegex(ValueError, 'Unique pinned core anchor'): production.once('same same', 'same', 'x')

    def test_maps_context_helpers_and_no_link_surface_are_explicit(self):
        source, _, cuts = corpus(); out, _ = render_owned(source, cuts)
        for path in (production.WEAPON_CORE, production.ATTACHMENT_CORE):
            text = out[path]
            self.assertIn('static void add_script_string(ScriptStrings& strings', text)
            self.assertNotIn('this->', text)
            for forbidden in ('std_include', 'zonetool.hpp', 'asset_interface', 'ZONETOOL_', 'filesystem::', 'DB_', 'SL_'): self.assertNotIn(forbidden, text)
        self.assertIn('ScriptStrings& strings', out[production.WEAPON_CORE])
        self.assertIn('using detail::add_script_string;', out[production.ATTACHMENT_CORE])
        self.assertIn('JSON_DIAGNOSTICS != 1', production.HEADER)
        self.assertIn('#include "../structs.hpp"', production.HEADER)

    def test_renderer_does_not_supply_invocation_or_file_io(self):
        tree = ast.parse(Path(production.__file__).read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                self.assertNotIn(getattr(node.func, 'attr', ''), ('open', 'read_text', 'write_text', 'read_bytes', 'write_bytes', 'run', 'Popen', 'check_output'))
        self.assertNotIn('if __name__', ast.get_source_segment(Path(production.__file__).read_text(encoding='utf-8'), tree) or '')

    def test_explicit_session_header_is_pinned_not_an_activation_escape(self):
        source = session_corpus(); pins = {p: digest(v) for p, v in source.items()}
        fake = '[[noreturn]] inline void reject_native_activation() { /* does not reject */ }'
        with patch.object(production.session, 'PINS', pins), patch.object(Path, 'open', side_effect=AssertionError('explicit header must not read path')):
            with self.assertRaisesRegex(ValueError, 'Pinned explicit authored Source header drift'):
                production.session.render(source, stage_inactive=True, source_header=fake)


class AuthoredPairFixtureSourceTests(unittest.TestCase):
    def test_three_approved_originals_pass_production_validation_and_13_flags_stay_false(self):
        for case in fixtures.cases():
            fixtures.validate_originals(case['raw'], case['pins'])
            report = bodies.validate_private_pair_report(case['raw'][0], *case['pins'][0])
            self.assertTrue(all(report[key] is False for key in FALSE_FLAGS))
            self.assertEqual(case['capacity'], 6208)
            self.assertEqual(case['occurrences'], 4)

    def test_same_length_mutant_old_pin_refuses_new_approved_pin_changes_literal_oracle(self):
        base, renamed, swapped = fixtures.cases()
        self.assertEqual(tuple(map(len, base['raw'])), tuple(map(len, renamed['raw'])))
        with self.assertRaisesRegex(ValueError, 'Source binding'): fixtures.validate_originals(renamed['raw'], base['pins'])
        self.assertNotEqual(base['references'], renamed['references']); self.assertNotEqual(base['references'], swapped['references'])
        self.assertEqual(base['edges'], renamed['edges']); self.assertEqual(base['occurrences'], renamed['occurrences'])

    def test_invalid_utf8_duplicate_and_missing_field_refuse_even_with_new_raw_report_pins(self):
        import json
        base = fixtures.cases()[0]
        bads = [b'\xff', b'{"duplicate":1,"duplicate":2}']
        weapon = json.loads(base['raw'][1]); del weapon['weapDef']; bads.append(encode(weapon))
        for bad in bads:
            report, wr, ar = report_fixture(bad, base['raw'][2]); rr = encode(report)
            raw = (rr, wr, ar, base['raw'][3]); pins = tuple((len(v), hashlib.sha256(v).hexdigest()) for v in raw)
            with self.subTest(bad=bad[:30]), self.assertRaises(ValueError): fixtures.validate_originals(raw, pins)

    def test_header_generation_validates_every_case_before_return_and_is_deterministic(self):
        self.assertEqual(fixtures.render_header(), fixtures.render_header())
        with patch.object(fixtures.validation, 'validate_private_pair_bodies', side_effect=ValueError('refused original')):
            with self.assertRaisesRegex(ValueError, 'refused original'): fixtures.render_header()

    def test_cpp_authors_real_calls_private_rehash_order_and_no_fake_parser_or_os_redirect(self):
        source = (Path(__file__).parent/'test_authored_pair_json.cpp').read_text(encoding='utf-8')
        self.assertIn('pq::parse_weapon_json(', source); self.assertIn('pq::parse_attachment_json(', source)
        self.assertIn('nd::inventory_pair(', source); self.assertIn('OwnedPair<', source)
        self.assertIn('sha256(bytes[i])!=trusted[i].sha256', source)
        private = source.index('// All four PRIVATE copies')
        self.assertLess(private, source.index('ordered_json::parse(bytes[0])'))
        for forbidden in ('#define VirtualAlloc', '#define VirtualFree', 'FakeParser', 'DB_FindXAsset', 'filesystem::', 'LoadLibrary', 'system('): self.assertNotIn(forbidden, source)
        self.assertEqual(len(re.findall(r'\{"[a-z0-9_]+",[a-z0-9_]+\}', source)), 8)
        self.assertIn('IW7_AUTHORED_PAIR_REAL_CORE_FIXTURE=8', source)
        self.assertIn('!oracle(approved_cases[i],golden)', source)
        self.assertIn('stats.decodes==0&&stats.arenas==0', source)
        self.assertIn('std::current_exception();factory.memory->free();std::rethrow_exception(primary)', source)
        # The real field macro skips a missing/null value. A non-null wrong type
        # is required to reach its JSON get<bool>() rather than a later check.
        self.assertIn('attachment["papAttachment"]="authored_negative_type_fault"', source)
        self.assertNotIn('attachment.erase("papAttachment")', source)


if __name__ == '__main__':
    unittest.main()

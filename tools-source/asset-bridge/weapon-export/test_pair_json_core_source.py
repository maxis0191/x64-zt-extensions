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
    def test_unexpected_refusal_diagnostic_and_positive_oracles_remain_byte_identical(self):
        source = (Path(__file__).parent/'test_authored_pair_json.cpp').read_text(encoding='utf-8')
        positive = function_body(source, 'void real_pair_variants()')
        # The extraction is outside this entire positive function. Keep its exact
        # c887 Source bytes, including diagnostics, parser-result checks/oracles.
        self.assertEqual(hashlib.sha256(positive.encode()).hexdigest(),
                         '4d7ef74cfd92a283ec77070c97827a11aee9a2eab61bb744a9cfcea2daa3c993')

    def test_unexpected_refusal_lines_bound_all_fields_and_preserve_same_rethrow(self):
        source = (Path(__file__).parent/'test_authored_pair_json.cpp').read_text(encoding='utf-8')
        positive = function_body(source, 'void real_pair_variants()')
        self.assertLess(positive.index('Report report;Stats stats;'), positive.index('try { actual=execute('))
        catch = function_body(positive, 'catch(const zonetool::checked_memory_error& error)')
        code = re.sub(r'//[^\n]*', '', catch)
        self.assertEqual(re.findall(r'\bthrow[^;]*;', code), ['throw;'])
        self.assertEqual(source.count('std::fprintf(stderr,'), 3)  # Two exclusive branches plus one common size line.
        self.assertLess(code.index('std::fprintf(stderr,'), code.index('throw;'))
        formats = [''.join(ast.literal_eval(p) for p in re.findall(r'"(?:\\.|[^"\\])*"', block))
                   for block in re.findall(r'std::fprintf\(stderr,\s*((?:"(?:\\.|[^"\\])*"\s*)+),', code)]
        self.assertEqual(len(formats), 3)
        widths = {'%.16s': 16, '%.20s': 20, '%d': 11, '%zu': 20, '%u': 10}
        maximum = []
        for fmt in formats:
            self.assertEqual(fmt.count('\n'), 1); self.assertTrue(fmt.endswith('\n'))
            estimated = re.sub(r'%\.16s|%\.20s|%zu|%d|%u', lambda m: 'x'*widths[m[0]], fmt)
            self.assertNotIn('%', estimated); self.assertTrue(estimated.isascii()); maximum.append(len(estimated))
        self.assertLessEqual(max(maximum[:2]) + maximum[2], 1024)
        self.assertIn('if(failure.available)', code)
        self.assertIn('snapshot=0 ordinal=NA unit=NA count=NA bytes=NA', formats[1])
        self.assertIn('char requested[21]="NA";', code)
        self.assertIn('if(failure.requested_bytes_valid) std::snprintf(requested,sizeof(requested),"%zu",failure.requested_bytes);', code)
        self.assertIn('bytes=%.20s', formats[0])
        for fmt in formats[:2]:
            self.assertIn('padding=NA source_pad=0', fmt)
            self.assertIn('align_api=none', fmt)
        for field in ('error.reason()', 'report.primary()', 'report.capacity()', 'report.release_attempts()',
                      'stats.copies', 'stats.hashes', 'stats.decodes', 'stats.arenas', 'stats.weapon_parses',
                      'stats.attachment_parses', 'stats.publications'):
            self.assertIn(field, code)
        for field in ('failure.ordinal', 'failure.element_bytes', 'failure.count', 'failure.requested_type_alignment',
                      'failure.used_before', 'failure.capacity', 'static_cast<unsigned>(stats.phase)',
                      'sizeof(WeaponCompleteDef)', 'alignof(WeaponCompleteDef)', 'sizeof(WeaponDef)', 'alignof(WeaponDef)',
                      'sizeof(WeaponAttachment)', 'alignof(WeaponAttachment)', 'sizeof(WeaponAttachment*)',
                      'sizeof(ReticleDef*)', 'sizeof(const char*)', 'sizeof(char)', 'alignof(FxEffectDef)',
                      'alignof(ReticleDef)', 'sizeof(vec2_t)'):
            self.assertIn(field, code)
        for forbidden in ('GetLastError', 'primary_error', 'original_pool', 'incoming', 'bytes[', '%p', 'report.free'):
            self.assertNotIn(forbidden, code)

    def test_phase_markers_are_entry_intervals_without_changing_cleanup(self):
        source = (Path(__file__).parent/'test_authored_pair_json.cpp').read_text(encoding='utf-8')
        body = function_body(source, 'Result execute(')
        ordered = ['stats.phase=ParsePhase::pair_construction;', 'Pair pair(factory);',
                   'stats.phase=ParsePhase::weapon_parse;', '++stats.weapon_parses;', 'pq::parse_weapon_json(',
                   'stats.phase=ParsePhase::attachment_parse;', '++stats.attachment_parses;', 'pq::parse_attachment_json(',
                   'stats.phase=ParsePhase::post_parse;', 'pair.retain_returned_roots(']
        self.assertEqual(sorted(body.index(value) for value in ordered), [body.index(value) for value in ordered])
        self.assertIn('if(mode!=Mode::bypass_core){stats.phase=ParsePhase::weapon_parse;', body)
        cleanup = function_body(body, 'catch(...)')
        self.assertIn('const auto primary=std::current_exception();factory.memory->free();std::rethrow_exception(primary);', cleanup)
        self.assertNotIn('phase=', cleanup)
        self.assertEqual(body.count('report.allocation_failure()'), 0)
        self.assertEqual(function_body(source, 'void real_pair_variants()').count('report.allocation_failure()'), 1)

    def test_actual_emission_reconstructs_all_twelve_new_source_pins_and_retained_oracles(self):
        import json
        approved = fixtures.cases()
        summary = [{key: case[key] for key in ('label', 'pins', 'capacity', 'weapondef_offset',
                    'attachment_offset', 'references', 'edges', 'occurrences')} for case in approved]
        baseline = json.dumps(summary, sort_keys=True, separators=(',', ':')).encode('utf-8')
        self.assertEqual(hashlib.sha256(baseline).hexdigest(),
                         '5026784b19b7dd1cf7b60bee8841275eaa45572399b5d42a22f8087d55dd94a6')
        expected = [
            ('7137883b66b4735e5347cb25d7b29c3ec2bc60b66bfcfae33965abd0bcf90807',
             '0da006d96531b0d8afc74e6da211911a3c5b71b34c8104101926222bd5f9aa03'),
            ('d2a219fe38146bb3bb47bc6342e663fdb94de986a8a1779a1dc165fd79535772',
             'c71bf500b5cd0a5a60d89eab070edd49c7cdad584b44b1ba1d6eab843f870e7d'),
            ('9f393c3fb117a121917b3ac35ac222fe91263a2d08838283d8f723a3e7819e01',
             '0bd29bac7240039ff432e103243304674fcfb5995740c90e1d8224674b1ddf7d'),
        ]
        for case, (report_hash, weapon_hash) in zip(approved, expected):
            self.assertEqual(case['pins'], ((1764, report_hash), (22356, weapon_hash),
                             (1806, '088c665ca39c03daa3a6c8b84821318389611a5ef5b895223e263a5cdbe5969b'),
                             (66, 'f539cb31e182b7648cac4eb4da369e344d0a8da1a877c4fbed1dc23ef105f2c8')))
            self.assertEqual(json.loads(case['raw'][1])['weapDef']['accuracyGraphName'], [None, None])
        originals, pending = [], bytearray()
        tokens = list(re.finditer(r'(R"IW7AUTH\((.*?)\)IW7AUTH")(,?)', fixtures.render_header(), re.DOTALL))
        self.assertGreater(len(tokens), 12)
        for token in tokens:
            self.assertLessEqual(len(token[1].encode('utf-8')), 4096)
            pending.extend(token[2].encode('utf-8'))
            if token[3]:
                originals.append(bytes(pending)); pending.clear()
        self.assertEqual(pending, b'')
        self.assertEqual(originals, [raw for case in approved for raw in case['raw']])
        self.assertEqual(len(originals), 12)
        self.assertEqual([(len(raw), hashlib.sha256(raw).hexdigest()) for raw in originals],
                         [pin for case in approved for pin in case['pins']])

    def test_literal_tokens_preserve_empty_and_multibyte_boundaries(self):
        for raw in (b'', b'a'*4077, b'a'*4078,
                    ('a'*4076 + 'é🙂' + 'b'*4096).encode('utf-8'), ('🙂'*2049).encode('utf-8')):
            with self.subTest(bytes=len(raw)):
                tokens = fixtures._raw_literals(raw)
                self.assertTrue(tokens)
                decoded = []
                for token in tokens:
                    self.assertLessEqual(len(token.encode('utf-8')), 4096)
                    match = re.fullmatch(r'R"IW7AUTH\((.*?)\)IW7AUTH"', token, re.DOTALL)
                    self.assertIsNotNone(match)
                    decoded.append(match[1].encode('utf-8'))
                self.assertEqual(b''.join(decoded), raw)

    def test_whole_buffer_nul_delimiter_and_utf8_refusals_survive_fragmentation(self):
        for raw in (b'\0', b'a'*4077 + b'\0', b'a'*9000 + b'\0',
                    b')IW7AUTH"', b'a'*4073 + b')IW7AUTH"' + b'b'*4096):
            with self.subTest(bytes=len(raw)), self.assertRaisesRegex(ValueError, 'delimiter or NUL'):
                fixtures._raw_literals(raw)
        with self.assertRaises(UnicodeDecodeError):
            fixtures._raw_literals(b'a'*4077 + b'\xff')

    def test_fixture_source_manifest_closes_real_includes_and_exposes_old_four_file_omission(self):
        here = Path(__file__).parent
        generated = {Path(production.CORE_HEADER).name, 'authored_pair_json_cases.hpp'}

        def missing_includes(supplied):
            return {dependency for name in supplied
                    for dependency in re.findall(r'^\s*#\s*include\s*"([^"]+)"',
                                                 (here/name).read_text(encoding='utf-8'), re.MULTILINE)
                    if dependency not in supplied and dependency not in generated}

        old_four = {'test_authored_pair_json.cpp', 'native_pair_session.hpp',
                    'native_neutral_dependencies.hpp', 'native_definition_access.hpp'}
        self.assertEqual(missing_includes(old_four),
                         {'native_weapon_dependencies.inc', 'native_attachment_dependencies.inc',
                          'native_pair_owned_input.hpp', 'native_pair_bodies.hpp', 'native_pair_native_components.hpp'})
        supplied = set(fixtures.FIXTURE_SOURCE_FILES)
        self.assertEqual(len(supplied), len(fixtures.FIXTURE_SOURCE_FILES))
        self.assertEqual(len(supplied), 12)
        added = {'native_pair_bodies.hpp', 'native_pair_report.hpp', 'native_pair_body_schema.hpp'}
        self.assertEqual(missing_includes(supplied - added), {'native_pair_bodies.hpp'})
        self.assertTrue(old_four <= supplied)
        self.assertEqual(missing_includes(supplied), set())
        for new_header in ('native_pair_owned_session.hpp', 'native_pair_native_components.hpp'):
            self.assertEqual(missing_includes(supplied - {new_header}), {new_header})
        import json
        exports = json.loads((here.parents[2]/'product.json').read_text(encoding='utf-8'))['exports']
        self.assertTrue(all('tools-source/asset-bridge/weapon-export/' + name in exports for name in supplied))

    def test_opt_in_components_use_real_returns_and_owned_role_storage(self):
        here = Path(__file__).parent
        companion = (here/'native_pair_native_components.hpp').read_text(encoding='utf-8')
        typed = (here/'native_pair_owned_session.hpp').read_text(encoding='utf-8')
        for role, function in (('WeaponMap', 'parse_weapon_json'), ('AttachmentMap', 'parse_attachment_json')):
            body = function_body(companion, f'class {role} final')
            self.assertLess(body.index('Json dom_;'), body.index('Strings strings_;'))
            self.assertEqual(body.count('root_ = zonetool::iw7::pair_json::' + function + '(dom_, &arena, strings_);'), 1)
            self.assertIn('need(root_ != nullptr);', body)
            self.assertLess(body.index(f'{role}(const Input& raw, Arena& arena)'), body.index('public:'))
            self.assertIn('new ' + role + '(raw, arena)', companion)
            self.assertNotIn('make_unique<' + role + '>', companion)
        config = function_body(companion, 'NativeComponents(std::size_t capacity,')
        self.assertEqual(config.strip(), '')
        maker = function_body(companion, 'std::unique_ptr<TypedOwnedPair<Guards, NativeComponents>> make_in_memory_owned_pair(')
        self.assertLess(maker.index('make_validated_owned_pair(std::move(ingress), components)'),
                        maker.index('register_component_returns(components.completed_returns(value->input()))'))
        self.assertEqual(maker.count('register_component_returns('), 1)
        self.assertIn('weapon_->raw_ == &raw && attachment_->raw_ == &raw', companion)
        self.assertIn('&weapon_->dom_ != &attachment_->dom_', companion)
        self.assertIn('&weapon_->strings_ != &attachment_->strings_', companion)
        self.assertIn('const Roots& roots() const & { return pair_->roots(); }', typed)
        self.assertIn('const Roots& roots() const && = delete;', typed)
        for banned in ('parse_weapon_json(std::string', 'parse_attachment_json(std::string',
                       'FILE*', 'fopen(', 'DB_Find', 'SL_GetString', 'std::function', 'builder_'):
            self.assertNotIn(banned, companion)

    def test_component_cpp_causals_are_authored_not_native_execution(self):
        code = (Path(__file__).parent/'test_authored_pair_json.cpp').read_text(encoding='utf-8')
        self.assertIn('AUTHORED, NOT COMPILED/LINKED/EXECUTED', code)
        self.assertIn('static_assert(!std::is_constructible_v<Native,size_t,Report&>);', code)
        self.assertIn('!exposes_completion<NativeOwner>::value&&!exposes_rvalue_roots<NativeOwner>::value', code)
        gate = function_body(code, 'native_ingress(const AuthoredCase& source,')
        self.assertLess(gate.index('require_approved_source(source)'), gate.index('std::make_unique<NativeGuards>'))
        self.assertIn('owner.reset();need(destroyed==1);released_once(report);need(oracle(source,result));', code)
        self.assertIn('failure.used_before==source.attachment_offset', code)
        self.assertIn('failure.element_bytes==sizeof(WeaponAttachment)&&failure.count==1', code)
        self.assertIn('need(&error==native_component_fault::primary);', code)
        self.assertIn('native_component_fault::primary=nullptr;refused=true;', code)
        self.assertIn('native_component_fault::failed_bytes==expected_sizes[phase]', code)
        for name in ('native_components_variants', 'native_preflight_refusals',
                     'native_second_role_capacity_failure', 'native_storage_failures_and_order'):
            self.assertEqual(code.count(name + '();'), 1)

    def test_three_approved_originals_pass_production_validation_and_13_flags_stay_false(self):
        for case in fixtures.cases():
            fixtures.validate_originals(case['raw'], case['pins'])
            report = bodies.validate_private_pair_report(case['raw'][0], *case['pins'][0])
            self.assertTrue(all(report[key] is False for key in FALSE_FLAGS))
            self.assertEqual(case['capacity'], 6208)
            self.assertEqual(case['occurrences'], 4)

    def test_old_empty_graph_pair_reconstructs_old_pins_but_refuses_before_emission(self):
        import json
        case = fixtures.cases()[0]
        weapon, attachment = json.loads(case['raw'][1]), json.loads(case['raw'][2])
        weapon['weapDef']['accuracyGraphName'] = ['', '']
        report, wr, ar = report_fixture(encode(weapon), encode(attachment)); rr = encode(report)
        self.assertEqual((len(rr), hashlib.sha256(rr).hexdigest()),
                         (1764, 'd2f2b5189ab6669f2e2a7876694353a4f97e3269904e9620dbcff92e616f4564'))
        self.assertEqual((len(wr), hashlib.sha256(wr).hexdigest()),
                         (22352, '5114899831042a0d9f93988d011a5675799f1706c329cd52316ce289e05fc449'))
        demand = bodies._inspect(weapon, attachment, alignment=False)
        self.assertEqual(demand.offset, 6210)
        self.assertEqual(next(e[2] for e in demand.events if e[0] == 'attachment'), 5594)
        graph_names = [e for e in demand.events if '.accuracyGraphName[' in e[0]]
        self.assertEqual([(e[2], e[3]) for e in graph_names], [(5576, 1), (5577, 1)])
        with self.assertRaisesRegex(ValueError, 'attachment: legacy cursor misalignment for WeaponAttachment'):
            bodies.validate_private_pair_bodies(rr, len(rr), hashlib.sha256(rr).hexdigest(), wr, ar, case['raw'][3])
        with patch.object(fixtures, 'private_pair', return_value=(weapon, attachment)):
            with self.assertRaisesRegex(ValueError, 'legacy cursor misalignment'):
                fixtures.render_header()

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
        header = fixtures.render_header().encode('utf-8')
        self.assertEqual(len(header), 81219)
        self.assertEqual(hashlib.sha256(header).hexdigest(),
                         '61e9a981c4474bd6d2783f5bfd2c77bfebd15bc9cb2a2cfeac6430a0e4c741b5')
        with patch.object(fixtures.validation, 'validate_private_pair_bodies', side_effect=ValueError('refused original')):
            with self.assertRaisesRegex(ValueError, 'refused original'): fixtures.render_header()

    def test_cpp_authors_real_calls_private_rehash_order_and_no_fake_parser_or_os_redirect(self):
        source = (Path(__file__).parent/'test_authored_pair_json.cpp').read_text(encoding='utf-8')
        self.assertIn('pq::parse_weapon_json(', source); self.assertIn('pq::parse_attachment_json(', source)
        self.assertIn('nd::inventory_pair(', source); self.assertIn('OwnedPair<', source)
        buffers = function_body(source, 'Buffers(const Inputs&')
        self.assertIn(': raw(incoming, trusted, stats)', source)
        self.assertIn('input::OwnedInput raw;', source)
        self.assertIn('ordered_json::parse(raw.bytes(input::Role::report))', buffers)
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

    def test_real_body_preflight_keeps_same_raw_owner_before_all_explicit_core_dom_reads(self):
        source = (Path(__file__).parent/'test_authored_pair_json.cpp').read_text(encoding='utf-8')
        buffers = function_body(source, 'Buffers(const Inputs&')
        preflight = 'iw7::neutral::player_pair_bodies::validate_owned_pair_bodies(raw);'
        self.assertIn('#include "native_pair_bodies.hpp"', source)
        self.assertIn('input::OwnedInput raw;', source)
        self.assertIn(': raw(incoming, trusted, stats)', source)
        self.assertEqual(buffers.count(preflight), 1)
        reads = re.findall(r'pq::ordered_json::parse\(raw.bytes\(input::Role::(\w+)\)\)', buffers)
        self.assertEqual(reads, ['report', 'weapon', 'attachment'])
        self.assertLess(buffers.index(preflight), buffers.index('pq::ordered_json::parse('))
        self.assertNotIn('catch(', buffers)
        self.assertIn('std::unique_ptr<Buffers> pending;', source)
        self.assertIn('std::unique_ptr<Buffers> raw(){return std::move(pending);}', source)
        execute = function_body(source, 'Result execute(')
        order = ['require_approved_source(source);', 'Factory factory(',
                 'const auto* const original_raw=&factory.raw_ref->raw;', 'Pair pair(factory);',
                 'need(!factory.pending && &factory.raw_ref->raw == original_raw);']
        self.assertEqual([execute.index(value) for value in order],
                         sorted(execute.index(value) for value in order))
        self.assertIn('preflight performs additional hashing/JSON work outside these counters.', source)

    def test_repinned_buffers_refusals_use_real_preflight_before_core_dom_arena_and_parsers(self):
        source = (Path(__file__).parent/'test_authored_pair_json.cpp').read_text(encoding='utf-8')
        negatives = function_body(source, 'void malformed_inputs_refuse_before_decode()')
        direct = negatives[negatives.index('for(const bool report_mismatch:'):]
        self.assertIn('changed[1]="not-json-before-core-dom";', direct)
        self.assertIn('row["bytes"]=changed[1].size();', direct)
        self.assertIn('report_mismatch?std::string(64,\'0\'):sha256(changed[1])', direct)
        self.assertIn('hashes[i]=sha256(changed[i]);incoming[i]=changed[i];', direct)
        self.assertIn('trusted[i]={changed[i].size(),hashes[i]};', direct)
        self.assertIn('Buffers buffers(incoming,trusted,stats);', direct)
        self.assertIn('catch(const player_pair_report::ReportError& error)', direct)
        self.assertIn('"Report row does not bind SAME owned role"', direct)
        body_raw = (Path(__file__).parent/'native_pair_bodies.hpp').read_bytes()
        self.assertEqual((len(body_raw), hashlib.sha256(body_raw).hexdigest()),
                         (33561, '46647a305dca84d8c5bdadbbc6c344387b37000ede41cb07c3c0657da259d52f'))
        declaration = re.search(r'namespace ([\w:]+)\s*\{\s*namespace (\w+)\s*\{[^{}]*'
                                r'struct BodyError\s*:\s*std::runtime_error', body_raw.decode('utf-8'))
        self.assertIsNotNone(declaration)
        declared_name = declaration[1] + '::' + declaration[2] + '::BodyError'
        caught_name = re.search(r'catch\(const ([\w:]+::BodyError)& error\)', direct)[1]
        self.assertEqual(caught_name, declared_name)
        self.assertNotEqual(declared_name, 'iw7::neutral::player_pair_bodies::BodyError')
        self.assertIn('!report_mismatch&&std::string_view(error.what()).find("weapon:")==0', direct)
        for count in ('copies==4', 'hashes==4', 'decodes==0', 'arenas==0', 'weapon_parses==0',
                      'attachment_parses==0', 'publications==0'):
            self.assertIn('stats.' + count, direct)
        self.assertIn('!report.bound()', direct)
        for forbidden in ('execute(', 'Factory ', 'AuthoredCase ', 'catch(...)', 'parse_weapon_json(',
                          'parse_attachment_json(', 'checked_memory_tag'):
            self.assertNotIn(forbidden, direct)

    def test_owned_input_extraction_retains_actual_sha_and_all_bounds_precede_private_copies(self):
        header = (Path(__file__).parent/'native_pair_owned_input.hpp').read_text(encoding='utf-8')
        sha = re.search(r'    inline std::string sha256\(.*?\n    \}\n', header, re.DOTALL)[0]
        original = sha.replace('inline std::string sha256(', 'std::string sha256(', 1)
        self.assertEqual(hashlib.sha256(original.encode()).hexdigest(),
                         '3325efc215b91d9f41a30bdef4a31645ec2f222d466353ad0a4701098340361d')
        caps = ast.literal_eval('[' + re.search(r'role_caps\{([^}]+)\}', header)[1] + ']')
        self.assertEqual(caps, [65536, 2097152, 2097152, 66])
        self.assertEqual(sum(caps), int(re.search(r'total_cap = (\d+);', header)[1]))
        bounds = function_body(header, 'static void validate_before_copy(')
        for expression in ('incoming[i].size() <= role_caps[i]', 'trusted[i].bytes > 0',
                           'trusted[i].bytes <= role_caps[i]', 'incoming[i].size() == trusted[i].bytes',
                           'detail::checked_total(actual_total, incoming[i].size())',
                           'detail::checked_total(expected_total, trusted[i].bytes)',
                           'trusted[i].sha256.size() == 64'):
            self.assertIn(expression, bounds)
        self.assertNotIn('.assign(', bounds)
        constructor = function_body(header, 'OwnedInput(const Inputs&')
        ordered = ['validate_before_copy(incoming, trusted);', 'pins_[i].sha256.assign(',
                   'bytes_[i].assign(', '++counters.copies;', '++counters.hashes;', 'detail::sha256(bytes_[i])']
        self.assertEqual([constructor.index(value) for value in ordered],
                         sorted(constructor.index(value) for value in ordered))
        addition = function_body(header, 'inline size_t checked_total(')
        self.assertLess(addition.index('used <= total_cap && amount <= total_cap - used'),
                        addition.index('return used + amount;'))

    def test_generic_byte_owner_does_not_widen_finite_fixture_parse_allowlist(self):
        source = (Path(__file__).parent/'test_authored_pair_json.cpp').read_text(encoding='utf-8')
        gate = function_body(source, 'void require_approved_source(')
        self.assertIn('for (const auto& approved : approved_cases) if (&source == &approved) return;', gate)
        self.assertIn('throw PinError();', gate)
        execute = function_body(source, 'Result execute(')
        self.assertLess(execute.index('require_approved_source(source);'), execute.index('Factory factory('))
        fourth = function_body(source, 'void bypass_real_core_refuses(')
        self.assertIn('row["bytes"]=weapon.size();row["sha256"]=weapon_hash;', fourth)
        self.assertIn('fourth.trusted_source_pins[0]={report_raw.size(),report_hash};', fourth)
        self.assertIn('fourth_stats.copies==0&&fourth_stats.hashes==0&&fourth_stats.decodes==0', fourth)
        self.assertEqual(len(fixtures.cases()), 3)
        header = (Path(__file__).parent/'native_pair_owned_input.hpp').read_text(encoding='utf-8')
        code = re.sub(r'//[^\n]*', '', header)
        for forbidden in ('ordered_json', 'parse(', 'zone_memory', 'OwnedPair', 'FILE', 'Windows.h',
                          'LoadLibrary', 'VirtualAlloc', 'std::function', 'operator bool'):
            self.assertNotIn(forbidden, code)
        self.assertIn('const std::string& bytes(Role role) const', code)
        self.assertIn('Pin pin(Role role) const', code)
        for action in ('OwnedInput(const OwnedInput&)', 'OwnedInput(OwnedInput&&)',
                       'operator=(const OwnedInput&)', 'operator=(OwnedInput&&)'):
            self.assertIn(action + ' = delete;', code)

    def test_owned_input_causals_call_production_helper_and_remain_authored_uncompiled(self):
        here = Path(__file__).parent
        code = (here/'test_pair_owned_input.cpp').read_text(encoding='utf-8')
        self.assertIn('#include "native_pair_owned_input.hpp"', code)
        self.assertNotIn('class OwnedInput', code)
        self.assertNotIn('std::string sha256(', code)
        self.assertGreater(code.count('input::OwnedInput owner('), 5)
        for causal in ('input::detail::checked_total(input::total_cap, 1)',
                       '(std::numeric_limits<std::size_t>::max)()', 'counters.copies == 0 && counters.hashes == 0',
                       'mutation.copies == 4 && mutation.hashes == 3', 'std::swap(incoming[0], incoming[1])',
                       'std::swap(pins[0], pins[1])', 'owner->pin(role).sha256',
                       'catch (const allocation_fault::Failure&)', 'allocation_fault::live == before'):
            self.assertIn(causal, code)
        self.assertIn('AUTHORED, NOT COMPILED/EXECUTED', code)
        self.assertIn('IW7_PAIR_OWNED_INPUT=6', code)
        for forbidden in ('ordered_json', 'zone_memory', 'Windows.h', 'VirtualAlloc', 'LoadLibrary'):
            self.assertNotIn(forbidden, code)
        import json
        exports = json.loads((here.parents[2]/'product.json').read_text(encoding='utf-8'))['exports']
        for name in ('native_pair_owned_input.hpp', 'test_pair_owned_input.cpp'):
            self.assertIn('tools-source/asset-bridge/weapon-export/' + name, exports)



class OwnedPairReportSourceTests(unittest.TestCase):
    """Inactive contract/provenance checks; none compiles or executes the C++ fixture."""
    def setUp(self):
        self.here = Path(__file__).parent
        self.header = (self.here/'native_pair_report.hpp').read_text(encoding='utf-8')
        self.fixture = (self.here/'test_pair_report.cpp').read_text(encoding='utf-8')

    def test_closed_literals_match_existing_python_oracle(self):
        import neutral_pair_inputs as oracle
        for key, value in oracle._TEXT.items():
            self.assertIn('{"' + key + '", "' + value + '"}', self.header)
        flags = self.header.split('false_flags{{', 1)[1].split('}};', 1)[0]
        self.assertEqual(tuple(re.findall(r'"([^"\n]+)"', flags)), oracle._FALSE_FLAGS)
        paths = self.header.split('paths{{', 1)[1].split('}};', 1)[0]
        self.assertEqual(tuple(re.findall(r'"([^"\n]+)"', paths)), tuple(oracle._PATH_CAPS))
        self.assertIn(oracle._CSV_HASH, self.header)
        for key in oracle._KEYS:
            self.assertIn('"' + key + '"', self.header.split('closed(report,', 1)[1].split('});', 1)[0])
        self.assertEqual(len(oracle._KEYS), 30)

    def test_primary_include_and_single_const_owner_stay_inactive(self):
        self.assertIn('#if defined(JSON_DIAGNOSTICS) && JSON_DIAGNOSTICS != 1', self.header)
        self.assertLess(self.header.index('#define JSON_DIAGNOSTICS 1'), self.header.index('#include <json.hpp>'))
        self.assertIn('484483acad6d562306efc9b3c6d413404f1b1f8a', self.header)
        self.assertIn('53855e4a20d7bc92d9624bf0d83fba8e22d0d9de83f9480bd4895651602fa8cc', self.header)
        body = function_body(self.header, 'inline void validate_owned_report(')
        self.assertIn('inline void validate_owned_report(const player_pair_input::OwnedInput& owner)', self.header)
        self.assertLess(body.index('raw_pin(owner, Role::report)'), body.index('parse_report(owner.bytes(Role::report), guard)'))
        self.assertEqual(self.header.count('Json::parse('), 1)
        code = re.sub(r'//[^\n]*', '', self.header)
        for forbidden in ('native_pair_session', 'native_neutral_dependencies', 'OwnedPair', 'zone_memory',
                          'Factory', 'FILE', 'Windows.h', 'LoadLibrary', 'VirtualAlloc', 'operator bool', 'const_cast'):
            self.assertNotIn(forbidden, code)
        self.assertNotIn('parse_report(owner.bytes(Role::weapon)', code)
        self.assertNotIn('parse_report(owner.bytes(Role::attachment)', code)

    def test_framing_event_guard_and_literal_integer_checks(self):
        parsing = function_body(self.header, 'inline Json parse_report(')
        self.assertLess(parsing.index('role_caps[0]'), parsing.index('Json::parse('))
        self.assertLess(parsing.index('Report BOM refused'), parsing.index('Json::parse('))
        self.assertLess(parsing.index('Report raw NUL refused'), parsing.index('Json::parse('))
        self.assertIn('raw.begin(), raw.end()', parsing)
        self.assertIn('true, false, false)', parsing)
        self.assertNotIn('c_str()', parsing)
        events = function_body(self.header, 'bool operator()(')
        self.assertIn('frames.back().keys.insert(key).second, "Duplicate report key"', events)
        self.assertEqual(events.count('return true;'), 1)
        self.assertNotIn('return false', events)
        self.assertIn('depth <= 64', self.header)
        self.assertIn('nodes < 32768', self.header)
        self.assertIn('frames.back().elements < 8192', self.header)
        numbers = function_body(self.header, 'inline std::size_t bounded_integer(')
        for variant in ('number_unsigned', 'number_integer'):
            self.assertIn('Json::value_t::' + variant, numbers)
        self.assertLess(numbers.index('value.type()'), numbers.index('value.get<'))
        self.assertLess(numbers.index('number <= cap'), numbers.index('static_cast<std::size_t>(number)'))
        self.assertIn('number >= 0 &&', numbers)

    def test_eight_authored_groups_call_actual_helper_without_body_integration(self):
        self.assertIn('#include "native_pair_report.hpp"', self.fixture)
        self.assertIn('AUTHORED, NOT COMPILED/EXECUTED at Source preparation', self.fixture)
        self.assertIn('IW7_PAIR_REPORT=8', self.fixture)
        groups = self.fixture.split('groups[] = {', 1)[1].split('};', 1)[0]
        self.assertEqual(len(re.findall(r'\{"[^"\n]+", \w+\}', groups)), 8)
        for causal in ('report::validate_owned_report(*owner)', 'Duplicate report key',
                       'Report raw NUL refused', 'Report BOM refused', 'guard.nodes == 48',
                       'mixed.nodes == 7', 'node_limit.value_start(0)', 'catch (const allocation_fault::Failure&)',
                       'refuses_as<Json::parse_error>', 'allocation_fault::live == before',
                       'BEFORE decode', 'std::declval<const input::OwnedInput&>()'):
            self.assertIn(causal, self.fixture)
        for forbidden in ('void validate_owned_report(', 'class OwnedInput', 'std::string sha256(',
                          'native_pair_session.hpp', 'native_neutral_dependencies.hpp', 'zone_memory', 'LoadLibrary'):
            self.assertNotIn(forbidden, self.fixture)

    def test_four_reference_sources_and_address_gate_are_unchanged(self):
        pins = {
            'neutral_pair_inputs.py': 'a722b66b55c2558951dbd481fd742e0f66a74cbefec97d3ddc69168eac29fcd3',
            'native_pair_owned_input.hpp': 'f5c31c73c4e5e5e152bb29bf9efd55008297f81ab7c4b4ec9e562cf2059a44ce',
            'test_neutral_pair_inputs.py': 'aa60cf2de06b88f2ad953f32da949b1c59ce2de8a1db09f19f686954af412565',
            'prepare_pair_json_core.py': 'ce24d250062cf7146738acfdb69e7842f51b05d4803b17df2dae83454c80d9cb',
        }
        for name, pin in pins.items():
            self.assertEqual(digest((self.here/name).read_text(encoding='utf-8')), pin, name)
        # The two authored composition Sources deliberately evolve here; their
        # raw payloads/pins and three-address gate have separate checks above.
        fixture = (self.here/'test_authored_pair_json.cpp').read_text(encoding='utf-8')
        self.assertIn('if (&source == &approved)', fixture)
        self.assertIn('#include "native_pair_bodies.hpp"', fixture)
        self.assertNotIn('native_pair_report.hpp', fixture)

    def test_exact_two_new_declarative_exports(self):
        import json
        exports = json.loads((self.here.parents[2]/'product.json').read_text(encoding='utf-8'))['exports']
        for name in ('native_pair_report.hpp', 'test_pair_report.cpp'):
            self.assertEqual(exports.count('tools-source/asset-bridge/weapon-export/' + name), 1)
        self.assertIn('Success is not provenance', self.header)

if __name__ == '__main__':
    unittest.main()

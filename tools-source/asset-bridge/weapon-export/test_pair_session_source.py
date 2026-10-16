"""Source staging/boundary checks only. Never compiles or runs the C++ fixture."""
import ast
import copy
import hashlib
from pathlib import Path
import re
import unittest
from unittest.mock import patch

import prepare_pair_checked_parse as production


def sha(text):
    return hashlib.sha256(text.replace('\r\n', '\n').encode()).hexdigest()


def corpus():
    """Small authored Source grammar, not native replacement declarations."""
    result = {path: '// owned Source support ' + path + '\n' for path in production.PINS}
    for name, cls, root in [('weapondef', 'weapon_def', 'WeaponCompleteDef'), ('weaponattachment', 'weapon_attachment', 'WeaponAttachment')]:
        hp = production.NATIVE + 'iw7/assets/' + name + '.hpp'
        cp = production.NATIVE + 'iw7/assets/' + name + '.cpp'
        result[hp] = '#pragma once\n#include "../zonetool.hpp"\nnamespace owned {\n\t\t' + root + '* parse(const std::string& name, zone_memory* mem);\n}\n'
        result[cp] = ('#include <std_include.hpp>\n#include "' + name + '.hpp"\nnamespace owned {\n'
                      '\t' + root + '* ' + cls + '::parse(const std::string& name, zone_memory* mem)\n'
                      '\t{\n\t\t// owned legacy byte preservation witness\n\t\treturn nullptr;\n\t}\n'
                      '\tvoid ' + cls + '::init(const std::string& name, zone_memory* mem)\n\t{\n\t}\n}\n')
    result[production.NATIVE + 'utils/io/filesystem.hpp'] = '#pragma once\nnamespace owned {\n\t\tvoid set_fastfile(const std::string& ff);\n}\n'
    result[production.NATIVE + 'utils/io/filesystem.cpp'] = '#include <std_include.hpp>\n#include "filesystem.hpp"\nnamespace owned {\n\t\tvoid set_fastfile(const std::string& ff)\n\t\t{\n\t\t}\n}\n'
    return result


def render_owned(sources, stage=True, *, original_pins=None):
    pins = original_pins or {path: sha(text) for path, text in sources.items()}
    with patch.object(production, 'PINS', pins):
        return production.render(sources, stage_inactive=stage)


def function_body(text, signature):
    start = text.index(signature); opening = text.index('{', start)
    end, depth = opening + 1, 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}'); end += 1
    return text[opening + 1:end - 1]


class PairSessionSourceTests(unittest.TestCase):
    def read(self, name):
        return (production.HERE / name).read_text(encoding='utf-8')

    def test_default_preserves_exact_inputs_and_does_not_read_header(self):
        sources = corpus(); original = copy.deepcopy(sources)
        with patch.object(Path, 'open', side_effect=AssertionError('header read on inactive default')):
            out, metadata = render_owned(sources, False)
        self.assertEqual(out, original); self.assertEqual(sources, original)
        self.assertNotIn(production.HEADER_DESTINATION, out)
        self.assertFalse(metadata['actual_activation'])

    def test_all_ten_pin_drifts_refuse_before_header_or_overlay(self):
        sources = corpus(); pins = {k: sha(v) for k, v in sources.items()}
        self.assertEqual(len(pins), 10)
        for path in pins:
            bad = dict(sources); bad[path] += '// drift\n'
            with self.subTest(path=path), patch.object(Path, 'open', side_effect=AssertionError('read before pins')):
                with self.assertRaisesRegex(ValueError, 'Pinned Source drift'): render_owned(bad, original_pins=pins)
        for bad in ({}, {**sources, 'extra': '// extra'}, {k: v for k, v in sources.items() if k != next(iter(sources))}):
            with self.assertRaises(ValueError): production.render(bad, stage_inactive=True)

    def test_unknown_or_duplicate_anchors_refuse(self):
        for transform in (lambda s: s.replace('::init(', '::other('), lambda s: s + '\tvoid weapon_def::init(const std::string& name, zone_memory* mem)'):
            sources = corpus(); key = production.NATIVE + 'iw7/assets/weapondef.cpp'; sources[key] = transform(sources[key])
            with self.assertRaisesRegex(ValueError, 'Unique pinned'): render_owned(sources)

    def test_stage_has_exact_three_rejecting_hooks_and_legacy_unchanged(self):
        sources = corpus(); original = copy.deepcopy(sources); out, metadata = render_owned(sources)
        self.assertEqual(sources, original)
        changed = {p for p in sources if sources[p] != out[p]}
        self.assertEqual(changed, {production.NATIVE + p for p in ['iw7/assets/weapondef.cpp', 'iw7/assets/weaponattachment.cpp',
                            'iw7/assets/weapondef.hpp', 'iw7/assets/weaponattachment.hpp', 'utils/io/filesystem.cpp', 'utils/io/filesystem.hpp']})
        self.assertEqual(set(out) - set(sources), {production.HEADER_DESTINATION})
        self.assertEqual(metadata['staged_inactive_hooks'], 3)
        for name, cls in [('weapondef', 'weapon_def'), ('weaponattachment', 'weapon_attachment')]:
            path = production.NATIVE + 'iw7/assets/' + name + '.cpp'
            signature = cls + '::parse(const std::string& name, zone_memory* mem)'
            self.assertEqual(function_body(out[path], signature), function_body(sources[path], signature))
            hook = function_body(out[path], cls + '::parse_checked_inactive(')
            calls = re.findall(r'([\w:]+)\(', hook)
            self.assertEqual(calls, ['player_pair_session::reject_native_activation'])
            for forbidden in ('file', 'open(', 'size(', 'read_', 'new ', 'allocate', 'parse(', 'init('):
                self.assertNotIn(forbidden, hook)
        fs = out[production.NATIVE + 'utils/io/filesystem.cpp']
        self.assertTrue(fs.startswith('#include <std_include.hpp>\n#include "filesystem.hpp"'))
        hook = function_body(fs, 'pair_route_seal_inactive::pair_route_seal_inactive()')
        self.assertEqual(hook.strip(), 'player_pair_session::reject_native_activation();')
        self.assertEqual(function_body(fs, 'void set_fastfile('), function_body(sources[production.NATIVE + 'utils/io/filesystem.cpp'], 'void set_fastfile('))

    def test_metadata_or_request_cannot_enable_native_hooks(self):
        out, metadata = render_owned(corpus()); original = dict(out)
        for key, value in metadata.items():
            if type(value) is bool: metadata[key] = True
        self.assertEqual(out, original)
        header = self.read('native_pair_session.hpp')
        reject = function_body(header, 'inline void reject_native_activation()')
        self.assertIn('throw std::logic_error', reject)
        self.assertNotIn('if ', reject)
        self.assertNotIn('passed', reject)

    def test_strict_stage_selection_and_source_types(self):
        sources = corpus()
        for value in (1, None, 'true'):
            with self.assertRaises(ValueError): render_owned(sources, value)
        for value in (b'source', 'source\0suffix'):
            bad = dict(sources); bad[next(iter(bad))] = value
            with self.assertRaises(ValueError): production.render(bad, stage_inactive=True)

    def test_owner_declaration_order_no_copy_move_and_no_native_calls(self):
        header = self.read('native_pair_session.hpp')
        owner = function_body(header, 'class OwnedPair final')
        fields = [owner.index(n) for n in ['guards_;', 'raw_;', 'route_;', 'arena_;', 'weapon_;', 'attachment_;', 'roots_;', 'inventory_;']]
        self.assertEqual(fields, sorted(fields))
        for declaration in ['OwnedPair(const OwnedPair&) = delete', 'operator=(const OwnedPair&) = delete',
                            'OwnedPair(OwnedPair&&) = delete', 'operator=(OwnedPair&&) = delete']:
            self.assertIn(declaration, owner)
        destructor = function_body(owner, '~OwnedPair() noexcept')
        self.assertLess(destructor.index('inventory_.reset()'), destructor.index('roots_.reset()'))
        for forbidden in ('zone_memory', 'Collector', 'zone_base', 'init(', 'prepare(', 'pointer(', 'parse(', 'fopen', 'CreateFile', 'VirtualAlloc', 'current_path'):
            self.assertNotIn(forbidden, re.sub(r'//[^\n]*', '', header))

    def test_route_constructor_unwind_and_restore_failure_are_bounded(self):
        header = self.read('native_pair_session.hpp')
        scope = function_body(header, 'template<class Env> class ScopedRoute final')
        self.assertIn('catch (...) { restore(); throw; }', scope)
        self.assertIn('catch (...) { report_.failed_restore(); }', scope)
        self.assertIn('~ScopedRoute() noexcept { restore(); }', scope)
        for fact in ('std::exit(0)', 'NOT', 'COVERED', 'Fake constructor throws', 'capacity/base'):
            self.assertIn(fact, header)

    def test_cpp_fixture_authored_twelve_cases_without_native_inputs(self):
        fixture = self.read('test_pair_session.cpp')
        cases = re.findall(r'\{"([a-z_]+)", ([a-z_]+)\}', fixture)
        self.assertEqual(len(cases), 12)
        for name, function in cases:
            self.assertEqual(name, function); self.assertIn('static void ' + name + '()', fixture)
        self.assertIn('#include "native_pair_session.hpp"', fixture)
        self.assertNotRegex(fixture, r'\bassert\s*\(')
        code = re.sub(r'//[^\n]*', '', fixture)
        for forbidden in ('windows.h', 'CreateFile(', 'VirtualAlloc(', 'fopen(', 'std::exit(', 'system(', 'zone_memory('):
            self.assertNotIn(forbidden, code)
        self.assertIn('Fake C++ throw', fixture.replace('fake C++ throw', 'Fake C++ throw'))
        self.assertIn('return passed == 12 ? 0 : 2', fixture)

    def test_existing_wiring_is_unchanged_and_no_recipe_cli_or_output_write(self):
        for name in ['prepare_module.py', 'native_player_cli.inc', 'native_player_templates.inc']:
            self.assertNotIn('native_pair_session', self.read(name))
            self.assertNotIn('parse_checked_inactive', self.read(name))
        tree = ast.parse(self.read('prepare_pair_checked_parse.py'))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
        self.assertFalse({getattr(n.func, 'id', '') for n in calls} & {'exec', 'eval', 'compile', 'subprocess', 'system'})
        self.assertFalse({getattr(n.func, 'attr', '') for n in calls} & {'write_bytes', 'write_text', 'mkdir', 'unlink', 'run', 'Popen'})
        self.assertNotIn('__main__', self.read('prepare_pair_checked_parse.py'))


if __name__ == '__main__': unittest.main()

"""Real renderer Source causals; no C++ compilation, SDK query or native arena."""
import ast
import hashlib
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

import prepare_pair_checked_memory as production
import prepare_pair_checked_parse as pair_parse
from test_pair_session_source import function_body

HERE = Path(__file__).resolve().parent


def corpus():
    """Authored grammar for anchors, not a vendored native implementation."""
    lock = '\t\t\tstd::lock_guard<std::recursive_mutex> g(this->mutex_);\n'
    methods = [
        '\t\tzone_memory(const zone_memory& mem)\n\t\t\t: memory_pool_(mem.memory_pool_)\n\t\t{\n\t\t}\n',
        '\t\tzone_memory(const std::size_t& size)\n\t\t{\n\t\t\t// owned legacy constructor witness\n\t\t\tstd::exit(0);\n\t\t}\n',
        '\t\tvoid free()\n\t\t{\n' + lock + '\t\t\t// owned legacy release witness\n\t\t}\n',
        '\t\tvoid clear()\n\t\t{\n\t\t\t// owned legacy clear witness\n\t\t}\n',
        '\t\tvoid print_statistics()\n\t\t{\n\t\t\t// owned legacy statistics witness\n\t\t}\n',
        '\t\t~zone_memory()\n\t\t{\n\t\t\tthis->free();\n\t\t}\n',
        '\t\tchar* duplicate_string(const char* name)\n\t\t{\n' + lock + '\t\t\treturn nullptr;\n\t\t}\n',
        '\t\tchar* duplicate_string(const std::string& name)\n\t\t{\n' + lock + '\t\t\treturn nullptr;\n\t\t}\n',
        '\t\ttemplate<class T>\n\t\tT* manual_allocate(std::size_t size, std::size_t count = 1)\n\t\t{\n' + lock + '\t\t\t// owned legacy capacity witness\n\t\t\tstd::exit(0);\n\t\t}\n',
    ]
    return ('#pragma once\n#include <mutex>\nnamespace zonetool\n{\n\tclass zone_memory\n\t{\n'
            '\t\tstd::recursive_mutex mutex_;\n\tpublic:\n' + ''.join(methods) + '\t};\n}\n')


def render_owned(source=None, *, stage=True):
    source = corpus() if source is None else source
    raw = source.encode('utf-8')
    with patch.object(production, 'SOURCE_BYTES', len(raw)), patch.object(production, 'SOURCE_SHA256', hashlib.sha256(raw).hexdigest()):
        return production.render(source, stage_checked=stage)


class CheckedMemorySourceTests(unittest.TestCase):
    def test_exact_native_source_pin_and_pair_composition_pin_agree(self):
        self.assertEqual(production.SOURCE_BYTES, 3000)
        self.assertEqual(production.SOURCE_PIN, pair_parse.PIN)
        self.assertEqual(pair_parse.PINS[production.SOURCE_PATH], production.SOURCE_SHA256)
        self.assertEqual(production.SOURCE_SHA256, '9025b835313ee45ba3418e3322210dec3b6d334e504a1dd3b59e9f38e2898f35')

    def test_default_preserves_exact_text_without_staging_or_io(self):
        for source in (corpus(), corpus().replace('\n', '\r\n')):
            with patch.object(production, 'replacements', side_effect=AssertionError('DEFAULT staged Source')):
                result, metadata = render_owned(source, stage=False)
            self.assertIs(result, source)
            self.assertFalse(metadata['checked_overlay_staged'])
            self.assertFalse(metadata['layout_changed'])

    def test_pin_drift_refuses_before_any_replacement(self):
        with patch.object(production, 'replacements', side_effect=AssertionError('staging before pin')):
            for source in (corpus(), 'x' * 3000, '\ufeff' + corpus()):
                with self.subTest(source_bytes=len(source.encode())):
                    with self.assertRaisesRegex(ValueError, 'Pinned memory Source drift'):
                        production.render(source, stage_checked=True)

    def test_character_bound_refuses_before_nul_scan_encode_or_hash(self):
        tree = ast.parse((HERE / 'prepare_pair_checked_memory.py').read_text(encoding='utf-8'))
        render = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'render')
        nul_line = render.body[2].lineno
        encode_line = render.body[3].body[0].lineno
        for source in ('x' * 3001, '\0' + 'x' * 3000, '\ud800' + 'x' * 3000):
            visited = set()
            def trace(frame, event, _arg):
                if frame.f_code is production.render.__code__ and event == 'line': visited.add(frame.f_lineno)
                return trace
            previous = sys.gettrace()
            try:
                sys.settrace(trace)
                with patch.object(production.hashlib, 'sha256', side_effect=AssertionError('hash before character bound')):
                    with self.assertRaisesRegex(ValueError, 'Source character bound before scans'):
                        production.render(source, stage_checked=True)
            finally:
                sys.settrace(previous)
            self.assertNotIn(nul_line, visited)
            self.assertNotIn(encode_line, visited)

    def test_input_types_utf8_and_literal_selection_refuse(self):
        for source in (None, b'source', 1, 'source\0tail', '\ud800'):
            with self.assertRaises(ValueError): production.render(source, stage_checked=True)
        for selection in (None, 1, 'true'):
            with self.assertRaisesRegex(ValueError, 'Literal Source-only'):
                render_owned(stage=selection)

    def test_overlay_reverses_exactly_to_legacy_source(self):
        source = corpus(); result, metadata = render_owned(source)
        self.assertEqual(result.count('std::exit(0);'), 2)
        for before, after in reversed(production.replacements()):
            self.assertEqual(result.count(after), 1)
            result = result.replace(after, before, 1)
        self.assertEqual(result.encode(), source.encode())
        self.assertTrue(metadata['layout_changed'])

    def test_missing_or_duplicate_anchors_refuse(self):
        source = corpus()
        for mutated in (source.replace('void clear()', 'void unknown()'), source + 'memory_pool_(mem.memory_pool_)'):
            with self.assertRaisesRegex(ValueError, 'Unique pinned'):
                render_owned(mutated)

    def test_checked_constructor_binds_once_and_captures_null_error_immediately(self):
        source, _ = render_owned()
        body = function_body(source, 'zone_memory(checked_memory_tag,')
        self.assertLess(body.index('if (report.bound_)'), body.index('VirtualAlloc('))
        self.assertLess(body.index('report.owner_ = this'), body.index('VirtualAlloc('))
        self.assertRegex(body, r'if \(!memory_pool_\)\s*\{\s*const DWORD error = GetLastError\(\);\s*checked_fail')
        for forbidden in ('MessageBox', 'std::exit', 'new ', 'std::string'):
            self.assertNotIn(forbidden, body)

    def test_checked_arithmetic_and_live_gate_precede_all_effects(self):
        source, _ = render_owned()
        body = function_body(source, 'T* checked_allocate(')
        self.assertLess(body.index('checked_need_live()'), body.index('count == 0'))
        self.assertLess(body.index('checked_memory_bytes('), body.index('reinterpret_cast<char*>'))
        self.assertLess(body.index('checked_memory_bytes('), body.index('memset('))
        arithmetic = function_body(source, 'inline std::size_t checked_memory_bytes(')
        self.assertLess(arithmetic.index('max)() / size'), arithmetic.index('size * count'))
        self.assertIn('used > capacity || bytes > capacity - used', arithmetic)
        self.assertIn('mem_pos_ += bytes', body)
        self.assertNotRegex(body, r'align|padding|MessageBox|std::exit')
        primary = function_body(source, 'void checked_fail(')
        self.assertIn('primary_ == checked_memory_failure::none', primary)
        self.assertIn('checked_phase::primary_failed', primary)

    def test_one_release_attempt_is_shared_terminal_and_preserves_errors(self):
        source, _ = render_owned()
        body = function_body(source, 'void checked_release_pool() noexcept')
        self.assertEqual(body.count('VirtualFree('), 1)
        self.assertLess(body.index('if (checked_release_attempted_'), body.index('checked_release_attempted_ = true'))
        self.assertLess(body.index('checked_release_attempted_ = true'), body.index('VirtualFree('))
        self.assertLess(body.index('release_attempts_ = 1'), body.index('VirtualFree('))
        self.assertRegex(body, r'VirtualFree\(memory_pool_, 0, MEM_RELEASE\);\s*const DWORD error = result \? 0 : GetLastError\(\);')
        self.assertIn('catch (...)', body)
        for forbidden in ('primary_ =', 'primary_error_ =', 'memory_pool_ =', 'memory_size_ =', 'mem_pos_ =', 'throw ', 'MessageBox', 'std::exit'):
            self.assertNotIn(forbidden, body)
        release = function_body(source, 'void free()')
        self.assertIn('if (checked_report_) { checked_release_pool(); return; }', release)
        self.assertEqual(function_body(source, '~zone_memory()').strip(), 'this->free();')

    def test_terminal_use_and_copy_are_gated_before_pool_adoption(self):
        source, _ = render_owned()
        for signature in ('void clear()', 'void print_statistics()', 'char* duplicate_string(const char*', 'char* duplicate_string(const std::string&'):
            body = function_body(source, signature)
            self.assertIn('checked_need_live()', body)
        self.assertIn('if (checked_report_) return checked_allocate<T>(size, count)', source)
        self.assertIn('memory_pool_((checked_copy_source(mem), mem.memory_pool_))', source)
        copy = function_body(source, 'void checked_copy_source(')
        self.assertIn('if (source.checked_report_)', copy)
        self.assertNotIn('memory_pool_', copy)
        self.assertNotIn('operator=(const zone_memory', source)

    def test_external_report_is_durable_readonly_diagnostics_not_authority(self):
        source, metadata = render_owned()
        report = function_body(source, 'class checked_memory_report final')
        self.assertIn('friend class zone_memory', report)
        self.assertIn('checked_memory_report(const checked_memory_report&) = delete', report)
        self.assertIn('checked_memory_report(checked_memory_report&&) = delete', report)
        for name in ('owner', 'original_pool', 'primary', 'primary_error', 'release', 'release_attempts', 'release_result_available', 'release_error'):
            self.assertIn(name + '() const noexcept', report)
        for forbidden in ('reset(', 'Closed', 'Ready', 'admitted', 'validated'):
            self.assertNotIn(forbidden, report)
        for name in ('actual_activation', 'allocator_closure_qualified', 'legacy_fatal_covered', 'cpp_fixture_executed'):
            self.assertFalse(metadata[name])

    def test_cpp_fixture_authored_twelve_live_checks_with_only_fake_arena_calls(self):
        fixture = (HERE / 'test_pair_checked_memory.cpp').read_text(encoding='utf-8')
        cases = re.findall(r'\{"([a-z0-9_]+)", ([a-z0-9_]+)\}', fixture)
        self.assertEqual(len(cases), 12)
        self.assertEqual(len(set(name for name, _ in cases)), 12)
        for name, function in cases:
            self.assertEqual(name, function)
            self.assertIn('static void ' + name + '()', fixture)
        self.assertLess(fixture.index('#include <Windows.h>'), fixture.index('#define VirtualAlloc fixture::allocate'))
        for redirect in ('#define VirtualAlloc fixture::allocate', '#define VirtualFree fixture::release', '#define MessageBoxA fixture::message', '#include "memory.hpp"'):
            self.assertIn(redirect, fixture)
        self.assertIn('return passed == 12 ? 0 : 2', fixture)
        self.assertIn('IW7_PAIR_CHECKED_MEMORY_FIXTURE=12', fixture)
        self.assertNotRegex(fixture, r'\bassert\s*\(|::VirtualAlloc\(|::VirtualFree\(')
        self.assertIn('AUTHORED ONLY', fixture)
        self.assertIn('Fake VirtualFree throw', fixture)
        self.assertIn('for (bool api_throw : {false, true})', fixture)
        self.assertIn('!report.release_result_available()', fixture)
        self.assertIn('Source-inspected only', fixture)

    def test_renderer_is_pure_source_without_cli_write_or_process(self):
        path = HERE / 'prepare_pair_checked_memory.py'
        text = path.read_text(encoding='utf-8'); tree = ast.parse(text)
        imports = {node.names[0].name for node in tree.body if isinstance(node, ast.Import)}
        self.assertEqual(imports, {'hashlib'})
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        self.assertFalse({getattr(node.func, 'id', '') for node in calls} & {'open', 'exec', 'eval', 'compile'})
        self.assertFalse({getattr(node.func, 'attr', '') for node in calls} & {'read_bytes', 'read_text', 'write_bytes', 'write_text', 'mkdir', 'run', 'Popen'})
        self.assertNotIn('__main__', text)

    def test_existing_hooks_and_consumers_are_not_activated(self):
        for name in ('prepare_module.py', 'native_player_cli.inc', 'native_player_templates.inc', 'prepare_pair_checked_parse.py'):
            text = (HERE / name).read_text(encoding='utf-8')
            self.assertNotIn('prepare_pair_checked_memory', text)
            self.assertNotIn('checked_memory_tag', text)
        reject = function_body((HERE / 'native_pair_session.hpp').read_text(encoding='utf-8'), 'inline void reject_native_activation()')
        self.assertIn('throw std::logic_error', reject)
        self.assertNotIn('if ', reject)


if __name__ == '__main__': unittest.main()

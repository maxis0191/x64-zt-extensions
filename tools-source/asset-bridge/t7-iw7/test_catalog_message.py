"""Source/format checks for the one-callsite message observer, without native work."""
import hashlib
import os
from pathlib import Path
import re
import unittest
import prepare_cli
import prepare_catalog_trace as p
from test_catalog_callers import render_format


def part(start, stop):
    return p.MESSAGE_SUPPORT.split(start, 1)[1].split(stop, 1)[0]


@unittest.skipUnless(os.environ.get('IW7_T7_SOURCE'), 'Retained native source not supplied')
class MessageWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, source = prepare_cli.render(Path(os.environ['IW7_T7_SOURCE']))
        cls.original = source[prepare_cli.PATHS[0]]
        cls.before = p.wire_callers_main(cls.original)
        cls.after = p.wire_message_main(cls.original)

    def test_prior_caller_profile_keeps_qualified_identity(self):
        self.assertEqual(len(self.before.encode()), 28832)
        self.assertEqual(hashlib.sha256(self.before.encode()).hexdigest(),
                         'af47dee318d9390f26c326d2e8ddd734e41bdc6db81b2b240e82c653cf7d2aa4')

    def test_remove_only_message_overlay_recovers_exact_existing_control_flow(self):
        restored = self.after.replace('#include <utils/cryptography.hpp>\n', '').replace(p.MESSAGE_SUPPORT+'\n', '')
        restored = restored.replace('\t\t\tcatalog_message_initialize();\n', '')
        self.assertEqual(restored, self.before)

    def test_installation_is_between_before_marker_and_original_post_unpack(self):
        stub = self.after.split('BOOL set_process_dpi_aware_stub()', 1)[1].split('FARPROC load_binary()', 1)[0]
        self.assertLess(stub.index('"before_post_unpack"'), stub.index('catalog_message_initialize();'))
        self.assertLess(stub.index('catalog_message_initialize();'), stub.index('component_loader::post_unpack();'))
        self.assertLess(stub.index('component_loader::post_unpack();'), stub.index('"after_post_unpack"'))
        self.assertIn('return SetProcessDPIAware();', stub)

    def test_no_original_exit_cleanup_or_cli_changes(self):
        for token in ('void WINAPI exit_hook(', 'void catalog_exit_once('):
            before = self.before.split(token, 1)[1].split('\n\t}', 1)[0]
            after = self.after.split(token, 1)[1].split('\n\t}', 1)[0]
            self.assertEqual(before, after)
        self.assertEqual(self.after.count('catalog_trace_initialize();'), 1)
        self.assertEqual(self.after.count('catalog_message_initialize();'), 1)

    def test_anchor_drift_or_second_overlay_refused(self):
        with self.assertRaises(ValueError): p.wire_message_main(self.after)
        with self.assertRaises(ValueError): p.wire_message_main(self.original.replace('entry_point()', 'other()'))

    def test_digest_comparison_matches_retained_uppercase_provider(self):
        root = Path(os.environ['IW7_T7_SOURCE'])
        provider = (root/'src/common/utils/string.cpp').read_text()
        self.assertIn('va("%02X", data[i] & 0xFF)', provider)
        expected = '6e07cffeb7e5f2dd6466dd4713537edc5c93050cbebc8a07892db032931f038b'
        self.assertIn('"'+expected.upper()+'"', p.MESSAGE_SUPPORT)


class MessageForwardingTests(unittest.TestCase):
    def test_original_four_word_call_is_first_and_not_wrapped_by_a_catch(self):
        body = part('uintptr_t catalog_message_forward(', 'struct catalog_message_install')
        statements = body.split('{', 1)[1]
        statements = re.sub(r'//[^\n]*', '', statements).strip()
        self.assertTrue(statements.startswith('const auto result = reinterpret_cast<uintptr_t(*)(uintptr_t, uintptr_t, uintptr_t, uintptr_t)>(catalog_message_target)('))
        self.assertIn('buffer, capacity, format, arguments);\n\t\tconst DWORD saved_error = GetLastError();', body)
        self.assertLess(body.index('GetLastError()'), body.index('catalog_message_observe('))
        self.assertLess(body.index('catalog_message_observe('), body.index('SetLastError(saved_error);'))
        self.assertLess(body.index('SetLastError(saved_error);'), body.index('return result;'))
        for forbidden in ('__try', '__except', 'catch', 'std::', 'Interlocked', 'GetCurrentThreadId'):
            self.assertNotIn(forbidden, statements)

    def test_forwarding_target_preexists_patch_and_large_observer_cannot_inline(self):
        self.assertIn('constexpr uintptr_t catalog_message_target = 0x140AB6460ULL;', p.MESSAGE_SUPPORT)
        self.assertNotRegex(p.MESSAGE_SUPPORT, r'catalog_message_target\s*=(?! 0x140AB6460ULL)')
        self.assertIn('__declspec(noinline) void catalog_message_observe(', p.MESSAGE_SUPPORT)
        self.assertIn('__declspec(noinline) uintptr_t catalog_message_forward(', p.MESSAGE_SUPPORT)

    def test_activation_follows_published_installation_and_capture_is_single_winner(self):
        init = p.MESSAGE_SUPPORT.split('void catalog_message_initialize()', 1)[1]
        self.assertLess(init.index('std::fprintf'), init.index('std::fflush'))
        self.assertLess(init.index('std::fflush'), init.index('InterlockedExchange(&catalog_message_ready, 1)'))
        self.assertIn('printed >= 0 && flushed == 0 && std::strcmp(out.status, "installed") == 0', init)
        self.assertIn('!catalog_trace_enabled || (InterlockedOr(&catalog_message_install_seen, 1) & 1)', init)
        observe = part('void catalog_message_observe(', 'uintptr_t catalog_message_forward(')
        self.assertIn('InterlockedCompareExchange(&catalog_message_ready, 0, 0) != 1', observe)
        self.assertIn('(InterlockedOr(&catalog_message_seen, 1) & 1)', observe)
        self.assertLess(observe.index('InterlockedOr'), observe.index('catalog_message_read('))
        for forbidden in ('WaitFor', 'Sleep(', 'CriticalSection', 'mutex', 'while ('):
            self.assertNotIn(forbidden, p.MESSAGE_SUPPORT)


class MessageInstallationTests(unittest.TestCase):
    def test_image_rwx_whole_function_and_rel32_are_guarded_before_patch(self):
        prepare = part('void catalog_message_prepare(', 'void catalog_message_rollback(')
        self.assertIn('unsigned char bytes[399];', p.MESSAGE_SUPPORT)
        self.assertIn('region.AllocationBase != module', prepare)
        self.assertIn('region.Protect != PAGE_EXECUTE_READWRITE || region.Type != MEM_IMAGE', prepare)
        self.assertLess(prepare.index('catalog_exit_readable(region, 0x140584F50ULL, sizeof(out.bytes))'), prepare.index('ReadProcessMemory'))
        self.assertIn('out.bytes[72] != 0xE8', prepare)
        self.assertIn('static_cast<int64_t>(catalog_message_site + 5) + displacement != static_cast<int64_t>(catalog_message_target)', prepare)
        self.assertIn('static_cast<int64_t>(relative32) != relative', prepare)
        init = p.MESSAGE_SUPPORT.split('void catalog_message_initialize()', 1)[1]
        self.assertLess(init.index('sha256::compute'), init.index('catalog_message_patch(out)'))
        for forbidden in ('VirtualAlloc', 'VirtualProtect', 'utils::hook::', 'detour', 'LoadLibrary', 'OpenProcess'):
            self.assertNotIn(forbidden, p.MESSAGE_SUPPORT)

    def test_aligned_compare_exchange_preserves_adjacent_three_bytes(self):
        self.assertIn('static_assert(catalog_message_site % 8 == 0)', p.MESSAGE_SUPPORT)
        prepare = part('void catalog_message_prepare(', 'void catalog_message_rollback(')
        self.assertIn('std::memcpy(patch, &out.original, sizeof(patch));', prepare)
        self.assertIn('std::memcpy(patch + 1, &relative32, sizeof(relative32));', prepare)
        patch = part('void catalog_message_patch(', 'void catalog_message_initialize()')
        self.assertIn('out.replacement, out.original)', patch)
        self.assertIn('previous != out.original) { out.attempted = false; out.status = "compare_mismatch";', patch)

    def test_install_and_rollback_each_require_flush_and_exact_readback(self):
        patch = part('void catalog_message_patch(', 'void catalog_message_initialize()')
        rollback = part('void catalog_message_rollback(', 'void catalog_message_patch(')
        for body, expected, success in ((patch, 'replacement', 'installed'), (rollback, 'original', 'rolled_back')):
            self.assertIn('FlushInstructionCache(GetCurrentProcess()', body)
            self.assertIn('ReadProcessMemory(GetCurrentProcess()', body)
            self.assertIn('!flushed || !read || copied != sizeof(observed) || observed != out.'+expected, body)
            self.assertLess(body.index('!flushed || !read'), body.index('out.status = "'+success+'"'))
        self.assertIn('out.original, out.replacement)', rollback)
        self.assertIn('previous != out.replacement && previous != out.original', rollback)
        self.assertIn('out.status = "rollback_failed"', rollback)
        self.assertIn('if (out.attempted) catalog_message_rollback(out);', patch)

    def test_seh_is_separate_from_cpp_digest_and_original_helper(self):
        self.assertEqual(p.MESSAGE_SUPPORT.count('__try'), 4)
        self.assertEqual(p.MESSAGE_SUPPORT.count('__except (EXCEPTION_EXECUTE_HANDLER)'), 4)
        for name in ('read', 'prepare', 'rollback', 'patch'):
            self.assertIn('__declspec(noinline) void catalog_message_'+name+'(', p.MESSAGE_SUPPORT)
        self.assertEqual(p.MESSAGE_SUPPORT.count('catch (...)'), 1)
        self.assertNotIn('exit(', p.MESSAGE_SUPPORT)
        self.assertNotIn('pre_destroy', p.MESSAGE_SUPPORT)


class MessageReadTests(unittest.TestCase):
    def test_stack_capacity_region_and_exact_return_address_before_self_read(self):
        body = part('void catalog_message_read(', 'void catalog_message_observe(')
        for token in ('capacity != 0x1000', 'caller) != catalog_message_site + 5', 'GetCurrentThreadStackLimits',
                      'capacity > high - buffer', 'catalog_exit_readable(region, buffer, 1)'):
            self.assertIn(token, body)
            self.assertLess(body.index(token), body.index('ReadProcessMemory'))
        self.assertIn('remaining < sizeof(out.bytes) ? remaining : sizeof(out.bytes)', body)
        self.assertIn('ReadProcessMemory(GetCurrentProcess()', body)
        self.assertIn('unsigned char bytes[384];', p.MESSAGE_SUPPORT)
        self.assertNotIn('format', body)
        self.assertNotIn('arguments', body)

    def test_post_seh_clamp_and_first_nul_limit_the_serialized_payload(self):
        body = part('void catalog_message_observe(', 'uintptr_t catalog_message_forward(')
        self.assertLess(body.index('out.requested > 384 || out.copied > out.requested'), body.index('SIZE_T length'))
        self.assertIn('out.requested = 0; out.copied = 0; out.status = "read_failed"; out.error = ERROR_INVALID_DATA;', body)
        self.assertIn('if (out.bytes[i] == 0) { length = i; nul = 1; break; }', body)
        self.assertIn('i < length', body)
        self.assertIn('char data[769] = "-";', body)
        self.assertIn('data[2 * length]', body)
        self.assertNotIn('strlen', body)
        self.assertIn('out.status, out.requested, out.copied, length, nul, out.error, data', body)

    def test_only_a_complete_read_can_upgrade_to_ok_or_prefix(self):
        body = part('void catalog_message_observe(', 'uintptr_t catalog_message_forward(')
        self.assertIn('if (std::strcmp(out.status, "complete") == 0) out.status = nul ? "ok" : "prefix";', body)
        self.assertEqual(body.count('out.status = nul ?'), 1)

    def test_actual_formats_fit_fourteen_line_8192_contract(self):
        formats = re.findall(r'std::fprintf\(stderr, "([^"]+)"', p.MESSAGE_SUPPORT)
        self.assertEqual(len(formats), 2)
        buffer = next(f for f in formats if 'kind=buffer' in f)
        install = next(f for f in formats if 'kind=install' in f)
        install_size = len(render_format(install, [4294967295,'S'*32,4294967295]))
        buffer_size = len(render_format(buffer, [4294967295,'S'*32,384,384,384,1,4294967295,'FF'*384]))
        self.assertEqual((install_size,buffer_size),(135,948))
        self.assertEqual(6911+install_size+buffer_size,7994)
        self.assertLessEqual(7994,8192)
        self.assertEqual(p.MESSAGE_SUPPORT.count('std::fprintf(stderr,'),2)
        states = re.findall(r'out.status = "([a-z_]+)"', p.MESSAGE_SUPPORT)
        self.assertTrue(all(len(s)<=32 for s in states))


if __name__ == '__main__': unittest.main()

import hashlib
import os
from pathlib import Path
import re
import unittest
import prepare_cli
import prepare_catalog_trace as p


@unittest.skipUnless(os.environ.get('IW7_T7_SOURCE'), 'Retained native source not supplied')
class ExitContextWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, sources = prepare_cli.render(Path(os.environ['IW7_T7_SOURCE']))
        cls.original = sources[prepare_cli.PATHS[0]]
        # Reconstruct the historically compiled v1 guards, preserving its pins.
        for option in ('t7-iw7-model-v2', 't7-iw7-model-streamed-v1'):
            cls.original = cls.original.replace(' || utils::flags::has_flag("'+option+'")', '')
        cls.trace = p.wire_main(cls.original)
        cls.context = p.wire_exit_main(cls.original)

    def test_removing_extension_restores_exact_v1_including_control_flow(self):
        restored = self.context.replace('\n'+p.EXIT_SUPPORT, '').replace(
            '\t\tcatalog_exit_once(code, _ReturnAddress());',
            '\t\tcatalog_trace_once(32, "exit_hook", code, _ReturnAddress());')
        self.assertEqual(restored, self.trace)
        self.assertEqual(self.context.count(p.SCHEMA), self.trace.count(p.SCHEMA))

    def test_v1_generated_main_keeps_the_previously_built_identity(self):
        self.assertEqual(len(self.trace.encode()), 14426)
        self.assertEqual(hashlib.sha256(self.trace.encode()).hexdigest(),
                         '6d06778290f1d8befb3184cc7ff7de7f82d7acb02ebef9f72e0a91cdf2056bb1')

    def test_return_address_is_captured_at_exit_hook_before_original_cleanup(self):
        hook = self.context.split('void WINAPI exit_hook(', 1)[1].split('\n\t}', 1)[0]
        self.assertIn('catalog_exit_once(code, _ReturnAddress());', hook)
        self.assertLess(hook.index('catalog_exit_once'), hook.index('component_loader::pre_destroy();'))
        self.assertLess(hook.index('component_loader::pre_destroy();'), hook.index('exit(code);'))
        self.assertEqual(self.context.count('catalog_exit_once(code, _ReturnAddress())'), 1)

    def test_single_selection_owns_exit_marker_and_all_context_fields(self):
        body = p.EXIT_SUPPORT.split('void catalog_exit_once(', 1)[1]
        self.assertEqual(self.context.count('catalog_trace_once(32,'), 1)
        self.assertLess(body.index('InterlockedOr(&catalog_trace_seen, 64)'), body.index('catalog_trace_once(32,'))
        self.assertLess(body.index('catalog_trace_once(32,'), body.index('catalog_exit_read_memory'))
        self.assertEqual(body.count('GetCurrentThreadId()'), 1)
        self.assertEqual(body.count('code, tid, caller,'), 3)
        self.assertNotIn('while', body)
        for operation in ('Sleep(', 'WaitFor', 'SuspendThread', 'EnterCriticalSection'):
            self.assertNotIn(operation, p.EXIT_SUPPORT)

    def test_double_overlay_or_anchor_drift_refuses(self):
        with self.assertRaises(ValueError): p.wire_exit_main(self.context)
        with self.assertRaises(ValueError): p.wire_exit_main(self.original.replace('exit_hook(const int code)', 'other_hook(const int code)'))


class ExitContextBoundsTests(unittest.TestCase):
    def test_memory_is_self_only_and_guarded_before_fixed_read(self):
        body = p.EXIT_SUPPORT.split('void catalog_exit_read_memory(', 1)[1].split('void catalog_exit_read_stack(', 1)[0]
        self.assertIn('GetModuleHandleW(L"BlackOps3_UnrankedDedicatedServer.exe")', body)
        self.assertIn('!= 0x140000000ULL', body)
        self.assertIn('out.start = address - 0x40;', body)
        self.assertLess(body.index('out.region.AllocationBase != out.module'), body.index('ReadProcessMemory'))
        self.assertLess(body.index('catalog_exit_readable'), body.index('ReadProcessMemory'))
        self.assertIn('ReadProcessMemory(GetCurrentProcess()', body)
        self.assertIn('unsigned char bytes[256];', p.EXIT_SUPPORT)
        self.assertIn('region.State == MEM_COMMIT', p.EXIT_SUPPORT)
        self.assertIn('(region.Protect & PAGE_GUARD) == 0', p.EXIT_SUPPORT)
        self.assertIn('length <= region.RegionSize - (address - begin)', p.EXIT_SUPPORT)

    def test_three_independent_seh_guards_cannot_replace_exit_or_cleanup(self):
        self.assertEqual(p.EXIT_SUPPORT.count('__try'), 3)
        self.assertEqual(p.EXIT_SUPPORT.count('__except (EXCEPTION_EXECUTE_HANDLER)'), 3)
        self.assertEqual(p.EXIT_SUPPORT.count('out.error = GetExceptionCode()'), 3)
        self.assertNotIn('throw ', p.EXIT_SUPPORT)
        for forbidden in ('exit(', 'quick_exit', 'pre_destroy', 'TerminateProcess', 'CreateFile',
                          'WriteFile', 'LoadLibrary', 'OpenProcess', 'VirtualProtect', 'DB_'):
            self.assertNotIn(forbidden, p.EXIT_SUPPORT)
        self.assertIn('SetLastError(saved_error);', p.EXIT_SUPPORT)

    def test_function_lookup_is_one_record_at_call_instruction_with_no_unwind_read(self):
        self.assertEqual(p.EXIT_SUPPORT.count('RtlLookupFunctionEntry('), 1)
        self.assertIn('RtlLookupFunctionEntry(address - 1, &out.image, nullptr)', p.EXIT_SUPPORT)
        self.assertIn('static_assert(sizeof(RUNTIME_FUNCTION) == 12);', p.EXIT_SUPPORT)
        self.assertIn('ReadProcessMemory(GetCurrentProcess(), out.address, &out.record, sizeof(out.record)', p.EXIT_SUPPORT)
        self.assertIn('out.record.BeginAddress <= rva && rva < out.record.EndAddress', p.EXIT_SUPPORT)
        self.assertEqual(p.EXIT_SUPPORT.count('UnwindData'), 1)  # Only printed as metadata.

    def test_stack_and_serialization_remain_bounded_after_partial_api_failure(self):
        self.assertIn('RtlCaptureStackBackTrace(0, 8, out.frames, nullptr)', p.EXIT_SUPPORT)
        self.assertIn('void* frames[8];', p.EXIT_SUPPORT)
        serialize = p.EXIT_SUPPORT.split('void catalog_exit_once(', 1)[1]
        for bound, serialization in (('if (memory.copied > 256)', 'constexpr char hex[]'),
                                     ('if (stack.count > 8)', 'char frames[137]'),
                                     ('if (function.copied > 12)', 'kind=function')):
            self.assertLess(serialize.index(bound), serialize.index(serialization))
        self.assertIn('char data[513] = "-";', serialize)
        self.assertIn('char frames[137] = "-";', serialize)
        self.assertEqual(serialize.count('std::fprintf(stderr,'), 3)
        self.assertEqual(serialize.count('std::fflush(stderr);'), 3)
        self.assertLess(serialize.index('kind=memory'), serialize.index('catalog_exit_read_stack(stack)'))
        self.assertLess(serialize.index('kind=stack'), serialize.index('catalog_exit_read_function(caller'))

    def test_actual_formats_fit_line_and_total_caps_at_maximum_field_widths(self):
        formats = re.findall(r'std::fprintf\(stderr, "([^"]+)"', p.EXIT_SUPPORT)
        self.assertEqual(len(formats), 3)
        common = [-2147483648, 4294967295, 'F'*16, 'module_mismatch']
        args = [common+['F'*16,256,'F'*16,'F'*16,'F'*16,18446744073709551615,
                        4294967295,4294967295,4294967295,4294967295,'FF'*256],
                common+[8,4294967295,','.join(['F'*16]*8)],
                common+['F'*16,'F'*16,12,0xffffffff,0xffffffff,0xffffffff,4294967295]]
        sizes = []
        for fmt, values, cap in zip(formats, args, (1024,512,512)):
            for before, after in (('%08lX','%08X'),('%llu','%d'),('%zu','%d'),('%lu','%d'),('%u','%d'),('%p','%s')):
                fmt = fmt.replace(before, after)
            line = (fmt % tuple(values)).replace('\\n','\r\n')
            sizes.append(len(line.encode('ascii')))
            self.assertLessEqual(sizes[-1], cap)
        self.assertLessEqual(6*256+sum(sizes),4096)


if __name__ == '__main__': unittest.main()

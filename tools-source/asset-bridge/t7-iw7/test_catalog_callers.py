"""Source-only regressions for the finite E caller capture; no native execution."""
import hashlib
import os
from pathlib import Path
import re
import unittest
import prepare_cli
import prepare_catalog_trace as p


def render_format(fmt, values):
    for before, after in (('%08lX', '%08X'), ('%llu', '%d'), ('%zu', '%d'),
                          ('%lu', '%d'), ('%u', '%d'), ('%p', '%s')):
        fmt = fmt.replace(before, after)
    return (fmt % tuple(values)).replace('\\n', '\r\n').encode('ascii')


@unittest.skipUnless(os.environ.get('IW7_T7_SOURCE'), 'Retained native source not supplied')
class CallerWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, sources = prepare_cli.render(Path(os.environ['IW7_T7_SOURCE']))
        cls.original = sources[prepare_cli.PATHS[0]]
        # Reconstruct the historically compiled v1 guards, preserving its pins.
        for option in ('t7-iw7-model-v2', 't7-iw7-model-streamed-v1'):
            cls.original = cls.original.replace(' || utils::flags::has_flag("'+option+'")', '')
        cls.before = p.wire_exit_main(cls.original)
        cls.after = p.wire_callers_main(cls.original)

    def test_original_exit_context_keeps_exact_built_identity(self):
        self.assertEqual(len(self.before.encode()), 22194)
        self.assertEqual(hashlib.sha256(self.before.encode()).hexdigest(),
                         '5f64c43ca9306cfa0ee561fbe94592a4f0cedcc9382456d11772653695c3fae3')

    def test_removing_callers_recovers_every_original_byte(self):
        restored = self.after.replace('#include <cstring>\n', '').replace(p.CALLERS_SUPPORT+'\n', '').replace(
            '\t\tcatalog_callers_capture(code, tid, caller, stack);\n', '')
        self.assertEqual(restored, self.before)

    def test_same_first_winner_stack_and_context_before_original_cleanup(self):
        body = self.after.split('\tvoid catalog_exit_once(', 1)[1].split('\n}\n', 1)[0]
        self.assertLess(body.index('InterlockedOr(&catalog_trace_seen, 64)'), body.index('catalog_callers_capture'))
        self.assertLess(body.index('kind=function'), body.index('catalog_callers_capture'))
        self.assertLess(body.index('catalog_callers_capture'), body.index('SetLastError(saved_error)'))
        self.assertEqual(body.count('GetCurrentThreadId()'), 1)
        self.assertEqual(self.after.count('RtlCaptureStackBackTrace('), 1)
        self.assertEqual(self.after.count('catalog_callers_capture(code, tid, caller, stack)'), 1)
        before_hook = self.before.split('void WINAPI exit_hook(', 1)[1].split('\n\t}', 1)[0]
        after_hook = self.after.split('void WINAPI exit_hook(', 1)[1].split('\n\t}', 1)[0]
        self.assertEqual(before_hook, after_hook)

    def test_duplicate_or_changed_anchor_refuses(self):
        with self.assertRaises(ValueError): p.wire_callers_main(self.after)
        with self.assertRaises(ValueError): p.wire_callers_main(self.original.replace('entry_point()', 'other()'))


class CallerBoundsTests(unittest.TestCase):
    def test_finite_ordered_targets_only_after_first_matching_current_frame(self):
        body = p.CALLERS_SUPPORT
        self.assertIn('targets[3] = {0x140584FD8ULL, 0x1401DA015ULL, 0x140526D02ULL}', body)
        self.assertIn('index < 3', body)
        self.assertIn('stack.count == 0 || stack.count > 8', body)
        self.assertIn('out.frame = -1;', body)
        self.assertIn('== target) { out.frame = i; break; }', body)
        self.assertLess(body.index('"stack_unavailable"'), body.index('GetModuleHandleW'))
        self.assertLess(body.index('"absent"'), body.index('GetModuleHandleW'))
        self.assertNotIn('RtlCaptureStackBackTrace', body)

    def test_lookup_and_record_are_self_image_guarded_without_unwind_read(self):
        body = p.CALLERS_SUPPORT
        self.assertIn('RtlLookupFunctionEntry(target - 1, &out.image, nullptr)', body)
        self.assertLess(body.index('out.region.AllocationBase != out.module'), body.index('RtlLookupFunctionEntry'))
        self.assertLess(body.index('out.image != reinterpret_cast<uintptr_t>(out.module)'), body.index('record_ok ='))
        self.assertLess(body.index('record_region.AllocationBase != out.module'), body.index('record_ok ='))
        self.assertIn('catalog_exit_readable(record_region, reinterpret_cast<uintptr_t>(out.address), sizeof(out.record))', body)
        self.assertIn('ReadProcessMemory(GetCurrentProcess(), out.address, &out.record, sizeof(out.record)', body)
        self.assertIn('out.record.BeginAddress <= rva && rva < out.record.EndAddress', body)
        self.assertEqual(body.count('UnwindData'), 1)  # Metadata emission only.
        self.assertEqual(body.count('ReadProcessMemory('), 2)

    def test_full_function_or_clipped_window_contains_the_call_instruction(self):
        body = p.CALLERS_SUPPORT
        self.assertIn('unsigned char bytes[512]', body)
        self.assertIn('end - begin > sizeof(out.bytes) || !catalog_exit_readable(out.region, begin, end - begin)', body)
        for expected in ('start = target - 448;', 'stop = target + 64;',
                         'if (start < begin) start = begin;', 'if (start < region_begin) start = region_begin;',
                         'if (stop > end) stop = end;', 'if (stop > region_end) stop = region_end;'):
            self.assertIn(expected, body)
        self.assertIn('start <= target - 1 && target - 1 < stop', body)
        self.assertIn('stop - start > sizeof(out.bytes)', body)
        self.assertIn('out.region.RegionSize > ~uintptr_t(0) - region_begin', body)
        self.assertIn('start == begin && stop == end ? "full" : "window"', body)
        self.assertLess(body.index('!catalog_exit_readable(out.region, start, stop - start)'), body.index('out.start = start;'))

    def test_errors_are_independent_and_serialization_is_rebounded(self):
        body = p.CALLERS_SUPPORT
        self.assertEqual(body.count('__try'), 1)
        self.assertEqual(body.count('__except (EXCEPTION_EXECUTE_HANDLER)'), 1)
        self.assertIn('__except (EXCEPTION_EXECUTE_HANDLER) { out.record = {};', body)
        for forbidden in ('ExitProcess', 'TerminateProcess', 'VirtualProtect', 'LoadLibrary', 'OpenProcess',
                          'exit(', 'quick_exit', 'pre_destroy', 'CreateThread', 'Sleep(', 'WaitFor', 'UnwindData +'):
            self.assertNotIn(forbidden, body)
        serialize = body.split('void catalog_callers_capture(', 1)[1]
        self.assertLess(serialize.index('catalog_caller_context out{};'), serialize.index('catalog_caller_read'))
        self.assertLess(serialize.index('out.record_copied > 12'), serialize.index('std::fprintf'))
        self.assertLess(serialize.index('out.requested > 512 || out.copied > out.requested'), serialize.index('char data[1025]'))
        self.assertEqual(serialize.count('std::fprintf(stderr,'), 1)
        self.assertEqual(serialize.count('std::fflush(stderr);'), 1)

    def test_all_twelve_lines_fit_total_8192_with_maximum_numeric_widths(self):
        fmt = re.findall(r'std::fprintf\(stderr, "([^"]+)"', p.CALLERS_SUPPORT)
        self.assertEqual(len(fmt), 1)
        u32, u64, ptr = 4294967295, 18446744073709551615, 'F'*16
        caller = render_format(fmt[0], [-2147483648,u32,ptr,2,ptr,'record_read_failed',-1,ptr,ptr,ptr,12,
            u32,u32,u32,ptr,512,512,'window',ptr,ptr,u64,u32,u32,u32,u32,'FF'*512])
        self.assertLessEqual(len(caller), 2048)
        context = re.findall(r'std::fprintf\(stderr, "([^"]+)"', p.EXIT_SUPPORT)
        common = [-2147483648,u32,ptr,'module_mismatch']
        contexts = [render_format(context[0],common+[ptr,256,ptr,ptr,ptr,u64,u32,u32,u32,u32,'FF'*256]),
                    render_format(context[1],common+[8,u32,','.join([ptr]*8)]),
                    render_format(context[2],common+[ptr,ptr,12,u32,u32,u32,u32])]
        trace = re.findall(r'std::fprintf\(stderr, "([^"]+)"', p.SUPPORT)
        phase = render_format(trace[0], ['before_entry_point',-2147483648,u32,ptr])
        enabled = render_format(trace[1], [1,1,u32])
        total = len(enabled)+5*len(phase)+sum(map(len,contexts))+3*len(caller)
        self.assertLessEqual(total,8192, f'Actual format upper bound: {total}')
        self.assertEqual(1+5+len(contexts)+3,12)


if __name__ == '__main__': unittest.main()

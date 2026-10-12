"""Portable source-contract checks; these do not compile or execute the C++ probe."""
import ast
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parent
SOURCE = (ROOT / "native_prepatch_probe.inc").read_text(encoding="utf-8")
CODE = re.sub(r"//[^\n]*|/\*.*?\*/", "", SOURCE, flags=re.S)


def selected_sites(text):
    return [(name, int(rva, 0), int(before, 0), int(length, 0)) for name, rva, before, length in
            re.findall(r'\{"([A-Za-z0-9_]+)",\s*(0x[0-9A-Fa-f]+),\s*(0x[0-9A-Fa-f]+|0),\s*(0x[0-9A-Fa-f]+)\}', text)]


def original_static_sites():
    """Read only literal tuples, without importing/launching either inspector."""
    tree = ast.parse((ROOT / "inspect_t7_executable.py").read_text(encoding="utf-8"))
    assignment = next(n for n in tree.body if isinstance(n, ast.Assign) and
                      any(isinstance(t, ast.Name) and t.id == "SITES" for t in n.targets))
    return {v[0]: v[1:4] for e in assignment.value.elts if isinstance(e, ast.Tuple)
            for v in [ast.literal_eval(e)]}


class PrepatchSourceTests(unittest.TestCase):
    def test_probe_is_exact_subset_of_reviewed_static_windows(self):
        actual, original = selected_sites(SOURCE), original_static_sites()
        self.assertEqual(len(actual), 12)
        self.assertEqual(len({s[0] for s in actual}), 12)
        self.assertEqual(sum(s[3] for s in actual), 1536)
        for name, rva, before, length in actual:
            self.assertEqual((rva, before, length), original[name])
            self.assertGreaterEqual(rva, before)
            self.assertLessEqual(length, 256)

    def test_probe_site_contract_detects_address_drift(self):
        mutated = SOURCE.replace('"boot_call", 0x502AA9', '"boot_call", 0x502AAA')
        changed = {n: (r, b, s) for n, r, b, s in selected_sites(mutated)}
        self.assertNotEqual(changed["boot_call"], original_static_sites()["boot_call"])

    def test_memory_is_only_read_from_current_process_without_mapping_or_writes(self):
        self.assertRegex(CODE, r'ReadProcessMemory\(GetCurrentProcess\(\),')
        self.assertIn('GetModuleHandleW(executable_name)', CODE)
        self.assertIn('VirtualQuery(', CODE)
        forbidden = r'\b(?:OpenProcess|LoadLibrary\w*|VirtualProtect\w*|VirtualAlloc\w*|WriteProcessMemory|' \
                    r'CreateProcess\w*|CreateThread|DB_\w+|load_zone|post_unpack|FlushInstructionCache)\s*\('
        self.assertIsNone(re.search(forbidden, CODE))
        self.assertNotIn('utils::hook::', CODE)

    def test_only_exact_flag_and_fresh_filename_are_accepted_in_source(self):
        self.assertIn('argc == 2', CODE)
        self.assertIn('std::wcscmp(argv[1], L"-t7-prepatch-probe") == 0', CODE)
        self.assertIn('L"t7-prepatch-probe.local.json"', CODE)
        self.assertIn('if (!exact || error || exists ||', CODE)
        self.assertIn('captured.test_and_set() || bound_output.empty() || !validate_invocation()', CODE)

    def test_output_is_bound_before_loading_and_cwd_changes_are_refused(self):
        self.assertIn('std::filesystem::absolute(output_name)', CODE)
        self.assertIn('!bound_output.empty() && bound_output != output', CODE)
        self.assertIn('write_enemy_reference_output(bound_output, serialized)', CODE)
        self.assertIn('bound_output.empty() || !validate_invocation()', CODE)

    def test_capture_cannot_throw_back_into_engine_continuation(self):
        self.assertIn('inline int capture() noexcept', CODE)
        self.assertIn('inline bool validate_invocation() noexcept', CODE)
        self.assertRegex(CODE, re.compile(r'catch\s*\(\.\.\.\).*?return 2;', re.S))
        self.assertIn('return complete ? 0 : 2;', CODE)
        self.assertIn('inline bool requested() noexcept', CODE)
        self.assertIn('catch (...) { return true; }', CODE)

    def test_scope_and_cumulative_read_caps_precede_memory_read(self):
        self.assertIn('read_limit = 4 * 1024 * 1024', CODE)
        self.assertIn('pdata_limit = 2 * 1024 * 1024', CODE)
        self.assertIn('length <= image_size - rva', CODE)
        self.assertIn('length <= read_limit - requested_bytes', CODE)
        self.assertIn('info.AllocationBase == reinterpret_cast<void*>(base) && info.Type == MEM_IMAGE', CODE)
        self.assertIn('!(protection & (PAGE_GUARD | PAGE_NOACCESS))', CODE)
        self.assertLess(CODE.index('requested_bytes += length;'), CODE.index('ReadProcessMemory('))
        self.assertIn('ok && received == length', CODE)

    def test_ambiguous_pdata_is_not_used_as_an_anchor(self):
        self.assertIn('fn.BeginAddress >= previous_end', CODE)
        self.assertIn('previous_end = fn.EndAddress;', CODE)
        self.assertIn('{"unwind_format_validated", false}', CODE)

    def test_complete_capture_is_not_compatibility_or_boot_authorization(self):
        for field in ('boot_authorized', 'abi_proven', 'runtime_compatibility_proven'):
            self.assertIn('{"' + field + '", false}', CODE)
            self.assertNotRegex(CODE, r'\["' + field + r'"\]\s*=\s*true')
        self.assertIn('"captured_for_offline_review" : "incomplete_stop"', CODE)
        self.assertIn('"first_dpi_before_component_post_unpack"', CODE)

    def test_publication_reuses_single_existing_create_new_writer(self):
        self.assertIn('report_limit = 256 * 1024', CODE)
        self.assertEqual(CODE.count('zonetool::iw7::write_enemy_reference_output('), 1)
        self.assertLess(CODE.index('serialized.size() <= report_limit'),
                        CODE.index('zonetool::iw7::write_enemy_reference_output('))
        self.assertNotIn('CreateFile', CODE)
        self.assertNotIn('std::ofstream', CODE)


if __name__ == "__main__":
    unittest.main()

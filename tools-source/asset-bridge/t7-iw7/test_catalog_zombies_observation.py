import os
from pathlib import Path
import unittest

import prepare_cli
import prepare_catalog_zombies_observation as p


def marker(body, sequence=0, thread=7, ending='\n'):
    return p.PREFIX + f'seq={sequence} tid={thread} ' + body + ending


class ObservationParserTests(unittest.TestCase):
    def test_legacy_trace_is_preserved_byte_for_byte(self):
        old = '[T7_CATALOG_TRACE] example\r\nordinary diagnostic\n'
        legacy, rows = p.split_observation(old + marker('kind=phase phase=0') + old)
        self.assertEqual(legacy, old + old)
        self.assertEqual(rows, [dict(kind='phase', sequence=0, thread=7, phase=0)])

    def test_raw_enter_does_not_require_a_return_after_fatal_exit(self):
        text = marker('kind=phase phase=0') + marker(
            'kind=raw_enter phase=0 caller=0000000140584FD8 type=47 error=1 wait=-1', 1, 31)
        legacy, rows = p.split_observation(text)
        self.assertEqual(legacy, '')
        self.assertEqual(rows[1]['thread'], 31)
        self.assertEqual(rows[1]['wait'], -1)
        self.assertNotIn('success', rows[1])

    def test_return_pointer_and_load_flags_are_observations_only(self):
        text = marker('kind=raw_return phase=5 result=0000000000000000') + marker(
            'kind=load_enter phase=6 caller=00000001401D9FE0 count=2 sync=0 suppress=-1', 1) + marker(
            'kind=load_return phase=7', 2)
        _, rows = p.split_observation(text)
        self.assertEqual(rows[0]['result'], '0000000000000000')
        self.assertEqual(rows[1]['suppress'], -1)

    def test_zone_header_refusal_and_bounded_names(self):
        for body in ('kind=zone index=0 status=unreadable',
                     'kind=zone index=1 status=unreadable nul=0 name_hex= alloc=65536 free=0 alloc_slot=0 free_slot=0',
                     'kind=zone index=0 status=read nul=1 name_hex=7a6d alloc=65536 free=0 alloc_slot=0 free_slot=0',
                     'kind=zone index=0 status=read nul=0 name_hex=' + 'aa'*64 + ' alloc=0 free=0 alloc_slot=0 free_slot=0'):
            with self.subTest(body=body):
                self.assertEqual(len(p.split_observation(marker(body))[1]), 1)

    def test_invalid_name_termination_is_not_filtered_from_legacy_trace(self):
        base = 'kind=zone index=0 status={status} nul={nul} name_hex={name} alloc=0 free=0 alloc_slot=0 free_slot=0'
        for status, nul, name in (('unreadable', 1, ''), ('unreadable', 0, 'aa'),
                                  ('read', 1, 'a'), ('read', 0, 'aa'), ('read', 1, 'aa'*64)):
            with self.subTest(status=status, nul=nul, name=name):
                with self.assertRaises(ValueError):
                    p.split_observation(marker(base.format(status=status, nul=nul, name=name)))

    def test_exact_schema_kinds_fields_and_pointer_widths(self):
        bad = (
            marker('kind=phase phase=0').replace('/1 ', '/2 '),
            marker('kind=phase phase=14'), marker('kind=phase phase=0 extra=1'),
            marker('kind=unknown phase=0'), marker('kind=raw_return phase=0 result=0'),
            marker('kind=raw_enter phase=0 caller=0000000140584FD8 type=46 error=1 wait=-1'),
            marker('kind=raw_enter phase=0 caller=0000000140584FD8 type=47 error=2 wait=-1'),
            marker('kind=raw_enter phase=0 caller=0000000140584FD8 type=47 error=1 wait=2147483648'),
            marker('kind=load_enter phase=0 caller=00000001401D9FE0 count=4294967296 sync=0 suppress=0'),
            marker('kind=zone index=2 status=unreadable'),
            marker('kind=zone index=0 status=read nul=1 name_hex= alloc=18446744073709551616 free=0 alloc_slot=0 free_slot=0'),
            marker('kind=phase phase=0', 64), marker('kind=phase phase=0', thread=0),
        )
        for text in bad:
            with self.subTest(text=text), self.assertRaises(ValueError):
                p.split_observation(text)

    def test_duplicates_and_event_caps_refuse(self):
        for text in (marker('kind=phase phase=0') * 2,
                     marker('kind=phase phase=0') + marker('kind=phase phase=0', 1),
                     ''.join(marker('kind=raw_return phase=0 result=0000000000000000', i) for i in range(5)),
                     ''.join(marker('kind=zone index=0 status=unreadable', i) for i in range(9))):
            with self.subTest(text=text), self.assertRaises(ValueError):
                p.split_observation(text)

    def test_concurrent_print_order_does_not_imply_origin_or_causality(self):
        _, rows = p.split_observation(marker('kind=phase phase=1', 3, 11) + marker('kind=phase phase=0', 1, 22))
        self.assertEqual([r['sequence'] for r in rows], [3, 1])
        self.assertEqual([r['thread'] for r in rows], [11, 22])

    def test_incomplete_oversized_and_nonascii_observations_refuse(self):
        for text in (marker('kind=phase phase=0', ending=''), 'x' * 16385,
                     marker('kind=phase phase=0') + '\N{EURO SIGN}', marker('x'*512)):
            with self.subTest(text=text), self.assertRaises(ValueError):
                p.split_observation(text)
        self.assertEqual(p.split_observation(''), ('', []))


class NativeObservationSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (p.HERE / 'native_catalog_zombies_observation.inc').read_text(encoding='utf-8')

    def test_four_argument_original_calls_are_single_and_unchanged(self):
        self.assertEqual(self.source.count('zm_observation_find_hook.invoke<XAssetHeader>(type, name, error_if_missing, wait_time)'), 1)
        self.assertEqual(self.source.count('zm_observation_load_hook.invoke<void>(zones, count, sync, suppress_sync)'), 1)
        self.assertIn('return result;', self.source)
        self.assertEqual(self.source.count('errno = entry_errno; SetLastError(entry_error);'), 2)
        self.assertIn('errno = crt_value; SetLastError(value);', self.source)
        self.assertIn('const zm_observation_error_guard restore_result;', self.source)
        self.assertIn('sizeof(XAssetHeader) == 8', self.source)
        self.assertIn('decltype(DB_FindXAssetHeader.get()), zm_find_signature*', self.source)

    def test_one_exact_raw_name_is_guarded_without_a_default_or_payload_probe(self):
        self.assertIn('type == ASSET_TYPE_RAWFILE', self.source)
        self.assertIn('std::memcmp(copy, zm_observation_raw_name, sizeof(copy)) == 0', self.source)
        for forbidden in ('DB_IsXAssetDefault(', 'DB_FindXAssetHeader(', 'DB_LoadXAssets(',
                          'RawFile{', 'rawfile->', 'OpenProcess(', 'CreateFile', 'load_zone(', 'quick_exit(', 'Sleep('):
            self.assertNotIn(forbidden, self.source)

    def test_installation_is_scoped_and_guards_both_sites_before_patching(self):
        install = self.source.split('static void zm_observation_install()', 1)[1]
        self.assertIn('count == 3', install)
        self.assertIn('std::wcscmp(args[2], L"zm_common") == 0', install)
        self.assertLess(install.index('LocalFree(args);'), install.index('if (!selected) return;'))
        self.assertLess(install.index('VirtualQuery('), install.index('zm_observation_find_hook.create('))
        self.assertIn('region.AllocationBase != module', install)
        self.assertIn('zm_observation_find_hook.clear();', install)
        self.assertNotIn('ui/', install)

    def test_guard_reads_and_logging_have_explicit_small_bounds(self):
        self.assertIn('char line[512]', self.source)
        self.assertIn('raw ? 1024 : 7168', self.source)
        self.assertIn('const auto cost = length + 1;', self.source)
        self.assertIn('i < count && i < 2', self.source)
        self.assertIn('unsigned char name[64]', self.source)
        self.assertIn('zm_observation_slot(zm_observation_loads, 4)', self.source)
        self.assertIn('zm_observation_slot(zm_observation_raw_calls, 4)', self.source)
        self.assertIn('attempt < 8 && current < limit', self.source)


@unittest.skipUnless(os.environ.get('IW7_T7_SOURCE'), 'Retained pinned owner native source not supplied')
class RetainedWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, source = prepare_cli.render(Path(os.environ['IW7_T7_SOURCE']))
        cls.before = source[prepare_cli.PATHS[1]]

    def test_removing_only_observations_recovers_exact_input_tu(self):
        after = p.wire_cli(self.before)
        module = (p.HERE / 'native_catalog_zombies_observation.inc').read_text(encoding='utf-8')
        inserted = p.INCLUDES + '\nnamespace zonetool::t7\n{\n' + '\n'.join('\t'+line if line else '' for line in module.splitlines())
        recovered = after.replace(inserted, 'namespace zonetool::t7\n{', 1)
        for old, new in reversed(p.edits()):
            self.assertEqual(recovered.count(new), 1)
            recovered = recovered.replace(new, old, 1)
        self.assertEqual(recovered, self.before)

    def test_drift_and_double_instrumentation_are_refused(self):
        with self.assertRaises(ValueError):
            p.wire_cli(p.wire_cli(self.before))
        for old, _ in p.edits():
            with self.subTest(anchor=old), self.assertRaises(ValueError):
                p.wire_cli(self.before.replace(old, '// missing site', 1))
            with self.subTest(duplicate=old), self.assertRaises(ValueError):
                p.wire_cli(self.before + '\n' + old)


if __name__ == '__main__':
    unittest.main(verbosity=2)

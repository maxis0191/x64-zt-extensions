import os
from pathlib import Path
import unittest
import prepare_cli
import prepare_prepatch as p


@unittest.skipUnless(os.environ.get('IW7_T7_SOURCE'), 'Retained native source not supplied')
class PrepatchWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, sources=prepare_cli.render(Path(os.environ['IW7_T7_SOURCE']))
        cls.before=sources[prepare_cli.PATHS[0]]
        cls.after=p.wire_main(cls.before)

    def test_diagnostic_exit_precedes_post_unpack_and_normal_path_is_preserved(self):
        stub=self.after.split('\t\tBOOL set_process_dpi_aware_stub()',1)[1].split('\t\tFARPROC load_binary()',1)[0]
        self.assertLess(stub.index('exit_hook('+p.API+'::capture())'),stub.index('component_loader::post_unpack();'))
        self.assertIn('return SetProcessDPIAware();',stub)
        self.assertEqual(self.after.count(p.API+'::capture()'),1)
        exit_hook=self.after.split('void WINAPI exit_hook(',1)[1].split('\n\t}',1)[0]
        self.assertLess(exit_hook.index('component_loader::pre_destroy();'),exit_hook.index('exit(code);'))

    def test_invalid_invocation_and_engine_choice_cannot_reach_main_internal(self):
        main=self.after.split('int main()\n',1)[1]
        self.assertLess(main.index(p.API+'::validate_invocation()'),main.index('game::set_mode'))
        self.assertLess(main.index('T7 pre-patch probe requires'),main.index('MessageBoxA'))
        self.assertLess(main.index('T7 pre-patch probe refuses competing'),main.index('return main_internal();'))
        self.assertIn('if (!'+p.API+'::validate_invocation())\n\t\t{\n\t\t\treturn 2;',main)

    def test_loading_exception_refuses_without_modal(self):
        catch=self.after.split('catch (std::exception& e)',1)[1].split('\n\t\t}',1)[0]
        self.assertLess(catch.index('T7 pre-patch probe loading failed'),catch.index('MessageBoxA'))
        self.assertLess(catch.index('return 2;'),catch.index('MessageBoxA'))

    def test_no_rendezvous_is_not_success_and_only_t7_exit_import_is_changed(self):
        t7=self.after.split('\tnamespace t7\n',1)[1].split('\tnamespace iw7\n',1)[0]
        self.assertIn('if ('+p.API+'::requested()) return prepatch_early_exit;',t7)
        self.assertIn('exit_hook(2);',t7)
        other_before=self.before.split('\tnamespace iw7\n',1)[1].split('\tint main_internal()',1)[0]
        other_after=self.after.split('\tnamespace iw7\n',1)[1].split('\tint main_internal()',1)[0]
        self.assertEqual(other_after,other_before)
        self.assertIn('entrypoint returned without capture.',self.after)
        self.assertEqual(self.after.count(p.API+'::requested() ? 2 : 0;'),2)

    def test_exact_anchor_drift_or_second_instrumentation_refuses(self):
        with self.assertRaises(ValueError): p.wire_main(self.after)
        with self.assertRaises(ValueError): p.wire_main(self.before.replace('BOOL set_process_dpi_aware_stub()', 'BOOL changed_stub()'))


if __name__ == '__main__': unittest.main()

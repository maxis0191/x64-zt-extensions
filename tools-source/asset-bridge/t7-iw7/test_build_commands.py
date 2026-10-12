import os
from pathlib import Path, PureWindowsPath
import unittest
import prepare_build as p


class RecipeTests(unittest.TestCase):
    def test_response_paths_reject_quote_or_newline(self):
        for value in ('a"b', 'a\nb', 'a\0b'):
            with self.assertRaises(ValueError): p.quote(value)

    def test_dependency_parser_refuses_ambiguous_records(self):
        with self.assertRaises(ValueError): p.read_records('unowned.hpp\n')
        with self.assertRaises(ValueError): p.read_records('^C:\\a.cpp\na.hpp\n^c:\\A.cpp\nb.hpp\n')


@unittest.skipUnless(os.environ.get('IW7_T7_SOURCE') and os.environ.get('IW7_T7_E7_BUILD'),
                     'Retained T7 source and E7 build paths not supplied')
class ExactCommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e7 = Path(os.environ['IW7_T7_E7_BUILD'])
        cls.cl = p.text_pin(cls.e7/'obj/tlog/CL.command.1.tlog',4*1024**2,p.CL_LOG_SHA)[0].decode('utf-16')
        cls.link = p.text_pin(cls.e7/'obj/tlog/link.command.1.tlog',256*1024,p.LINK_LOG_SHA)[0].decode('utf-16')
        cls.native = os.environ['IW7_T7_SOURCE']

    def commands(self, cl=None, link=None):
        return p.command_payloads(self.cl if cl is None else cl, self.link if link is None else link,
                                  self.native,r'C:\private\prepared',r'C:\private\run')

    def test_three_compile_commands_preserve_abi_and_one_line_macros(self):
        outputs, old = self.commands()
        self.assertEqual(len(old),3)
        for _, obj, _ in p.UNITS:
            command = outputs[obj+'.rsp'].decode()
            for flag in ('/MT ', '/O1 ', '/Zi ', '/W4 ', '/WX ', '/fp:precise ', '/std:c++23preview ', '/Y-'):
                self.assertIn(flag,command)
            for forbidden in ('/Yu','/Fp','/MP','/D\n'):
                self.assertNotIn(forbidden,command)
            self.assertEqual(len(command.splitlines()),1)
            self.assertIn('/D EXPERIMENTAL_IW7',command)
            self.assertIn('C:\\private\\run\\'+obj[:-4]+'\\compile.pdb',command)

    def test_link_preserves_exact_order_of_410_reused_objects(self):
        outputs, replaced = self.commands()
        before = self.link.splitlines()[2:]
        after = outputs['link.rsp'].decode().splitlines()[1:]
        self.assertEqual(len(after),413)
        self.assertEqual(sum(a == b for a,b in zip(before,after)),410)
        self.assertEqual({PureWindowsPath(x).name.casefold() for x in replaced}, {'main.obj','zonetool11.obj','xpak.obj'})
        self.assertIn('/manifest:embed',outputs['link.rsp'].decode())
        self.assertNotIn('/MANIFEST:NO',outputs['link.rsp'].decode())

    def test_changed_compiler_or_link_contract_is_refused(self):
        for before, after in (('/fp:precise','/fp:fast'),('/W4','/W3'),('/MT ','/MD ')):
            with self.assertRaises(ValueError): self.commands(cl=self.cl.replace(before,after))
        with self.assertRaises(ValueError): self.commands(link=self.link.replace('/INCREMENTAL:NO','/INCREMENTAL'))


if __name__ == '__main__': unittest.main()

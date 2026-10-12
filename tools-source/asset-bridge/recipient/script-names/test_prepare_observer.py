import os
from pathlib import Path
import re
import unittest
import prepare_observer as p

class PreparationTests(unittest.TestCase):
    def test_modified_or_oversize_source_refuses(self):
        for value in (b'',b'invented source',b'x'*(p.LIMIT+1)):
            with self.assertRaises(ValueError):p.render(value)

    def test_unique_anchor_required(self):
        for text in ('missing','anchor anchor'):
            with self.assertRaises(ValueError):p.once(text,'anchor','replacement')

    def test_observer_has_no_payload_or_default_creation_access(self):
        source=(p.HERE/'native_observer.inc').read_text()
        self.assertIsNone(re.search(r'->(?:buffer|bytecode)\b',source))
        for forbidden in ('db_find_x_asset_header_safe','dump_asset(', 'write_file(', 'token_name(', 'token_id('):
            self.assertNotIn(forbidden,source)
        self.assertIn('db_find_x_asset_entry(',source)
        self.assertIn('if (enum_error) return;',source)

    def test_metadata_interface_has_no_payload_storage(self):
        source=(p.HERE/'recipient_script_names.hpp').read_text()
        metadata=source.split('struct metadata',1)[1].split('struct row',1)[0]
        self.assertNotIn('*',metadata)
        self.assertNotRegex(metadata,r'\b(?:buffer|bytecode)\b')
        self.assertIn('max_callbacks = 4096',source)
        self.assertIn('max_output = 4096',source)

    def test_cli_rejects_trailing_arguments_and_catches_errors(self):
        source=(p.HERE/'native_cli.inc').read_text()
        self.assertIn('i + 2 != args.size()',source)
        self.assertIn('catch (const std::exception& error)',source)
        self.assertIn('std::quick_exit(EXIT_FAILURE)',source)

@unittest.skipUnless(os.environ.get('IW7_SCRIPT_OBSERVER_SOURCE'),'Optional retained native source not supplied')
class RetainedSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=p.source_snapshot(Path(os.environ['IW7_SCRIPT_OBSERVER_SOURCE'])/p.SOURCE)

    def test_recorded_patch_equals_source_render(self):
        self.assertEqual(p.patch_for(self.data),(p.HERE/'zonetool-fab9358-script-names.patch').read_text())

    def test_old_index_and_dump_logic_remain_exact(self):
        old,new=p.render(self.data)
        start=old.index('\tstatic std::unordered_map<std::string, ScriptFile*> index_enemy_scriptfiles_by_content_name(')
        end=old.index('\tvoid dump_enemy_script_catalog(',start)
        self.assertIn(old[start:end],new)
        start=old.index('\tvoid dump_enemy_scripts(')
        end=old.index('\n\tvoid ',start+6)
        self.assertIn(old[start:end],new)

    def test_only_three_additions_are_present(self):
        old,new=p.render(self.data)
        new=new.replace('\n#include "recipient_script_names.hpp"','',1)
        observer=(p.HERE/'native_observer.inc').read_text()
        block='\n'.join('\t'+line if line else '' for line in observer.splitlines())+'\n\n'
        new=new.replace(block,'',1)
        new=new.replace((p.HERE/'native_cli.inc').read_text()+'\n','',1)
        self.assertEqual(new,old)

if __name__=='__main__':unittest.main()

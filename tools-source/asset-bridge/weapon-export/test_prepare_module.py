import hashlib
import io
import json
from pathlib import Path
import tempfile
import re
import math
import unittest
from unittest.mock import patch

import prepare_module as support


FIXTURE = ('#include "zonetool.hpp"\nnamespace zonetool::iw7\n{\n'
    '\tvoid load_enemy_source_zones(const std::string& donor_zone);\n'
    + support.ANCHOR + '\n\t\tload_zone(donor_zone);\n\t}\n'
    '\tvoid unchanged_cli() { original_command(); }\n}\n')
FIXTURE_SHA = hashlib.sha256(FIXTURE.encode()).hexdigest()


class PreparationTests(unittest.TestCase):
    def primary_source_policy(self, changes=None, lifetimes=None):
        # Source causal over the actual finite C++ helper; not native execution.
        text=support.read_source(support.HERE/'native_primary_guard.hpp')
        body=text.split('Failure first_failure(Reader& source)\n    {',1)[1].split('return {Check::none',1)[0]
        body=re.sub(r'//[^\n]*','',body)
        pattern=re.compile(r'const auto (\w+) = source\.(\w+)\(\);|if \((.*?)\) return (integer|real)\(Check::(\w+), (\w+)\);|if \(!source\.(\w+)\(\)\) return absent\(Check::(\w+)\);')
        self.assertFalse(pattern.sub('',body).strip(),'Uninterpreted Source decision operation')
        data=dict(classification=5,type=3,inventory=0,clip=8,max_ammo=80,ammo_used=1,damage=100,speed=4000,
            gun_model=True,world_model=True,animations=True);data.update(changes or {})
        lifetime=iter(lifetimes or (60.0,60.0));trace=[];values={}
        for operation in pattern.finditer(body):
            variable,getter,condition,maker,key,value,pointer,pointer_key=operation.groups()
            if variable:
                trace.append(getter);values[variable]=next(lifetime) if getter=='lifetime' else data[getter]
            elif condition:
                predicate=condition.replace('!std::isfinite','not math.isfinite')
                if eval(predicate,{'__builtins__':{},'math':math},values):return key,values[value],trace
            else:
                trace.append(pointer)
                if not data[pointer]:return pointer_key,False,trace
        return None,None,trace

    def test_actual_primary_source_first_failure_and_unread_pointer_causals(self):
        complete=['classification','type','inventory','clip','max_ammo','ammo_used','damage','speed',
            'lifetime','lifetime','gun_model','world_model','animations']
        cases=[({'type':1,'inventory':1,'gun_model':False},None,'type',1,2),
            ({'inventory':1},None,'inventory',1,3),({'classification':-1},None,'class_min',-1,3),
            ({'classification':14},None,'class_max',14,3),({'classification':10},None,'class_non_player',10,3),
            ({'classification':11},None,'class_item',11,3),({'clip':0},None,'clip',0,4),
            ({'max_ammo':0},None,'max_ammo',0,5),({'ammo_used':0},None,'ammo_used',0,6),
            ({'damage':0},None,'damage',0,7),({'speed':0},None,'speed',0,8),
            ({},(float('nan'),),'lifetime_finite',float('nan'),9),
            ({},(60.0,0.0),'lifetime_positive',0.0,10),({'gun_model':False},None,'gun_model',False,11),
            ({'world_model':False},None,'world_model',False,12),({'animations':False},None,'animations',False,13)]
        for changes,lifetimes,key,wanted,reads in cases:
            with self.subTest(key=key):
                actual,value,trace=self.primary_source_policy(changes,lifetimes)
                self.assertEqual(actual,key);self.assertEqual(trace,complete[:reads])
                self.assertTrue(math.isnan(value)) if isinstance(wanted,float) and math.isnan(wanted) else self.assertEqual(value,wanted)
        for classification in (0,5,12,13):
            self.assertEqual(self.primary_source_policy({'classification':classification}),(None,None,complete))
        self.assertEqual(self.primary_source_policy(lifetimes=(1.0,-1.0)),('lifetime_positive',-1.0,complete[:10]))

    def test_primary_witness_is_bound_to_actual_offset_and_leaves_later_guards(self):
        source=support.read_source(support.HERE/'native_player_templates.inc')
        self.assertEqual(source.count('report_primary_failure(failure);'),1)
        self.assertLess(source.index('if (!weapon || !weapon->weapDef || !pap)'),source.index('first_failure(reader)'))
        self.assertLess(source.index('first_failure(reader)'),source.index('if (!pap->papAttachment'))
        self.assertIn('PrimaryReader reader{weapon, def}',source);self.assertIn('char line[256]',source)
        self.assertIn('kind=float32_bits value_bits=0x%08X',source)
        self.assertIn('throw std::runtime_error("Reloadable player primary projectile fields not established")',source)
        self.assertNotIn('"%p"',source);self.assertNotIn('source.classification()',source)

    def test_actual_witness_formats_fit_the_declared_buffer_for_all_fixed_keys(self):
        source=support.read_source(support.HERE/'native_player_templates.inc')
        capacity=int(re.search(r'char line\[(\d+)\]',source).group(1))
        formats=re.findall(r'"(IW7_PLAYER_TEMPLATE_PRIMARY_REFUSAL[^"\n]+)"',source)
        keys=re.findall(r'return \{"([^"]+)", "([^"]+)", offsetof\(',source)
        self.assertEqual((capacity,len(formats),len(keys)),(256,2,16))
        for key,container in keys:
            for literal in formats:
                fmt=literal.replace('%zX','%X').replace('\\n','\n')
                arguments=(key,0xffffffff,container,0x1418) if 'value_bits=' in fmt else (key,'presence',-2147483648,container,0x1418)
                self.assertLess(len((fmt%arguments).encode('ascii')),capacity)
    def test_inactive_support_preserves_source_and_entry(self):
        result, module = support.wire_module(FIXTURE, FIXTURE_SHA)
        addition = '\n'.join('\t' + line if line else '' for line in module.splitlines()) + '\n\n'
        without_module = result.replace(addition, '', 1).replace(
            '#include <array>\n#include <cmath>\n#include <fstream>\n#include <sstream>\n', '', 1)
        name_header = support.read_source(support.HERE / 'native_bounded_name.hpp').removeprefix('#pragma once\n')
        without_module = without_module.replace(name_header + '\n', '', 1)
        primary_header = support.read_source(support.HERE / 'native_primary_guard.hpp').removeprefix('#pragma once\n')
        without_module = without_module.replace(primary_header + '\n', '', 1)
        self.assertEqual(without_module, FIXTURE)
        self.assertEqual(result.count('void ' + support.FUNCTION + '('), 1)
        self.assertEqual(result.count(support.FUNCTION), 1)  # no call-site introduced

    def test_source_drift_refused_even_with_same_anchor(self):
        with self.assertRaisesRegex(ValueError, 'Pinned IW7 source changed'):
            support.wire_module(FIXTURE.replace('original_command', 'new_command'), FIXTURE_SHA)

    def test_wrong_namespace_and_missing_or_duplicate_anchor(self):
        for source in (FIXTURE.replace('zonetool::iw7', 'zonetool::t7'),
                       FIXTURE.replace(support.ANCHOR, ''), FIXTURE + support.ANCHOR):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, 'insertion site'):
                support.wire_module(source, hashlib.sha256(source.encode()).hexdigest())

    def test_already_inserted_module_refused(self):
        changed = FIXTURE + '\n// ' + support.FUNCTION
        with self.assertRaisesRegex(ValueError, 'insertion site'):
            support.wire_module(changed, hashlib.sha256(changed.encode()).hexdigest())

    def test_growth_capped_before_decode_or_hash(self):
        class Growth(io.BytesIO):
            def read(self, count=-1):
                self.requested = count
                return super().read(count)
        growth = Growth(b'\xff' * (support.CAP + 1024))
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'small.cpp'
            path.write_bytes(b'tiny')
            with patch.object(Path, 'open', return_value=growth):
                with self.assertRaisesRegex(ValueError, 'Source cap exceeded'):
                    support.read_source(path)
        self.assertEqual(growth.requested, support.CAP + 1)

    def test_bom_crlf_are_normalized(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'source.cpp'
            path.write_bytes(b'\xef\xbb\xbf' + FIXTURE.replace('\n', '\r\n').encode())
            self.assertEqual(support.read_source(path), FIXTURE)

    def test_real_source_outputs_and_overwrite_refusal(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            source = root / 'native' / support.NATIVE_PATH
            source.parent.mkdir(parents=True)
            source.write_text(FIXTURE, encoding='utf-8')
            output = root / 'staged'
            original_wire = support.wire_module
            with patch.object(support, 'wire_module', side_effect=lambda t: original_wire(t, FIXTURE_SHA)):
                report = support.stage(root / 'native', output)
            staged = (output / support.NATIVE_PATH).read_text(encoding='utf-8')
            manifest = json.loads((output / 'module-source.json').read_text())
            self.assertEqual(report, manifest)
            self.assertEqual(manifest['staged_lf_sha256'], hashlib.sha256(staged.encode()).hexdigest())
            self.assertFalse(any(manifest[k] for k in ('cli_wired', 'compiled',
                'native_export_executed', 'full_templates_observed', 'ready')))
            with self.assertRaisesRegex(ValueError, 'Fresh ordinary absolute'):
                support.stage(root / 'native', output)

    def test_relative_and_linked_output_refused_before_source_read(self):
        with self.assertRaisesRegex(ValueError, 'Fresh ordinary absolute'):
            support.stage('not_read', Path('relative'))
        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / 'new'
            with patch.object(Path, 'is_junction', return_value=True):
                with self.assertRaisesRegex(ValueError, 'Fresh ordinary absolute'):
                    support.stage('not_read', output)

    def test_opt_in_cli_is_before_existing_effects_and_preserves_inactive_output(self):
        source = FIXTURE.replace('\tvoid unchanged_cli()',
            '\tvoid handle_params() {\n\t\tauto args = get_command_line_arguments();\n'
            '\t\tfor (const auto& token : args) { original_command(); }\n\t}\n\tvoid unchanged_cli()')
        original = support.wire_module
        with patch.object(support, 'wire_module', side_effect=lambda t: original(t, hashlib.sha256(source.encode()).hexdigest())):
            wired, _ = support.wire_cli(source)
        entry = support.read_source(support.HERE/'native_player_cli.inc')
        block = '\n'.join('\t\t'+line if line else '' for line in entry.splitlines())+'\n'
        header = support.read_source(support.HERE/'native_player_cli.hpp').removeprefix('#pragma once\n')+'\n'
        self.assertLess(wired.index('iw7_player_template_cli::selected(args)'), wired.index('for (const auto& token : args)'))
        self.assertLess(entry.index('::exact(args)'), entry.index('dump_iw7_player_weapon_templates('))
        inactive, _ = original(source, hashlib.sha256(source.encode()).hexdigest())
        self.assertEqual(wired.replace(block, '', 1).replace(header, '', 1), inactive)

    def test_actual_native_argv_predicate_blocks_trailing_operation_before_legacy_loop(self):
        text = support.read_source(support.HERE/'native_player_cli.hpp')
        caps = [int(n) for n in re.search(r'caps\{([^}]+)\}', text).group(1).split(',')]
        count = int(re.search(r'args.size\(\) != (\d+)', text).group(1))
        predicate = re.search(r'return (args\[1\].*);', text).group(1).replace('&&', 'and')
        def exact(args):
            if len(args) != count: return False
            if any(not arg or len(arg.encode()) > cap or any(byte < 0x20 or byte == 0x7f for byte in arg.encode())
                   for arg, cap in zip(args, caps)): return False
            return eval(predicate, {'__builtins__': {}}, {'args': args})
        valid = ['C:/private tool/zonetool.exe','-headless','-iw7-player-weapon-templates','cp_zmb','requested.csv','paris_enemy_cp_zmb_template_player_weapon_source']
        self.assertTrue(exact(valid))
        for args in (valid+['-dumpzone'], valid[1:], [*valid[:3],'cp_rave',*valid[4:]],
                     ['',*valid[1:]], [*valid[:4],'a'*1025,valid[5]], [*valid[:4],'bad\0.csv',valid[5]]):
            self.assertFalse(exact(args))
        trailing = valid+['-dumpzone']
        old_effects = sum(token == '-dumpzone' for token in trailing)
        new_effects = old_effects if exact(trailing) else 0
        self.assertEqual((old_effects, new_effects), (1, 0))

    def test_cli_manifest_declares_fresh_iw7_compile_and_unexecuted_fixtures(self):
        source = FIXTURE.replace('\tvoid unchanged_cli()', '\tvoid handle_params() {\n\t\tauto args = get_command_line_arguments();\n\t}\n\tvoid unchanged_cli()')
        with tempfile.TemporaryDirectory() as root:
            root = Path(root); path = root/'native'/support.NATIVE_PATH
            path.parent.mkdir(parents=True);path.write_text(source, encoding='utf-8')
            original = support.wire_module
            with patch.object(support, 'wire_module', side_effect=lambda t: original(t, hashlib.sha256(source.encode()).hexdigest())):
                report = support.stage(root/'native', root/'output', player_cli=True)
            self.assertTrue(report['cli_wired'])
            self.assertTrue(report['build_extension']['requires_fresh_native_compile'])
            self.assertEqual(report['build_extension']['translation_unit'], support.NATIVE_PATH)
            self.assertEqual(report['build_extension']['argv_count_including_executable'], 6)
            self.assertEqual(report['build_extension']['argv_fixture_checks_authored'], 10)
            self.assertFalse(report['compiled'] or report['native_export_executed'] or report['ready'])
        with self.assertRaisesRegex(ValueError, 'Explicit source CLI boolean'):
            support.stage('not-read', Path('not-created'), player_cli=1)


if __name__ == '__main__':
    unittest.main()

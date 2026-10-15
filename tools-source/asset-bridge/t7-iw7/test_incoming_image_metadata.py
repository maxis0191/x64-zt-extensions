"""Actual source wiring/contracts. Authored native39+48 are NOT executed here."""
import hashlib
import json
import os
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
import prepare_incoming_image_metadata as incoming
import prepare_image_registration_metadata as registration
import prepare_image_metadata as metadata
import prepare_image_provenance as provenance
from test_image_provenance import ProvenanceTransitionTests as BaseRenderer


class IncomingSourceTests(unittest.TestCase):
    def read(self, path, limit, expected=None):
        raw=path.read_bytes().replace(b'\r\n',b'\n')
        self.assertLessEqual(len(raw),limit)
        if expected:self.assertEqual(hashlib.sha256(raw).hexdigest(),expected)
        return raw

    def test_selection_is_explicit_and_not_implied_by_old_profile(self):
        self.assertFalse(incoming.selected(SimpleNamespace(image_registration_metadata_v1=True)))
        self.assertTrue(incoming.selected(SimpleNamespace(image_registration_metadata_v1=True,image_incoming_header_v1=True)))
        for values in ({'image_incoming_header_v1':1},{'image_incoming_header_v1':True},
                       {'image_incoming_header_v1':True,'image_registration_metadata_v1':1}):
            with self.assertRaises(ValueError):incoming.selected(SimpleNamespace(**values))

    def test_actual_early_exact_native_predicate_refuses_all_extra_or_mixed_tokens(self):
        source=(incoming.HERE/incoming.MODULE).read_text()
        body=source.split('inline bool exact_selection(',1)[1].split('    // Calls are serialized',1)[0]
        expression=body.split('scalar::require(',1)[1].split(',\n            "Exclusive exact',1)[0]
        expression=expression.replace('args.size()','len(args)').replace('!args[0].empty()','bool(args[0])')
        expression=expression.replace('args[1] == option','args[1] == '+repr(incoming.OPTION)).replace('&&',' and ')
        predicate=compile('('+expression+')','<actual native early predicate>','eval')
        valid=['tool.exe',incoming.OPTION,'mp_freerun_04','p7_fre_platform_cap_02','0']
        accepted=lambda args:eval(predicate,{'__builtins__':{},'len':len,'bool':bool},{'args':args})
        self.assertTrue(accepted(valid))
        for index,value in ((0,''),(1,'-t7-iw7-image-registration-metadata-v1'),(2,'cp_zmb'),(3,'wrong'),(4,'00')):
            bad=valid.copy();bad[index]=value;self.assertFalse(accepted(bad))
        for flag in ('-t7-iw7-image-registration-metadata-v1','-t7-iw7-image-metadata-v1',incoming.OPTION,'extra'):
            self.assertFalse(accepted(valid+[flag]))
        self.assertFalse(accepted(valid[:-1]))
        arm=source.split('bool arm(',1)[1].split('void begin_map()',1)[0]
        self.assertLess(arm.index('exact_selection(args,requested)'),arm.index('armed_=true'))

    def test_frozen_copy_and_old_api_are_not_rewritten(self):
        base=self.read(incoming.HERE/registration.CAPTURE,32*1024)
        members=self.read(incoming.HERE/incoming.MEMBERS,16*1024)
        derived=incoming.capture_source(base,members)
        # Remove only the newly authored public methods and recover exact source bytes.
        added=''.join('        '+line+'\n' if line else '\n' for line in members.decode().splitlines())
        self.assertEqual(derived.replace(added,'',1).encode(),base)
        self.assertEqual((len(base),hashlib.sha256(base).hexdigest()),incoming.BASE_CAPTURE)
        self.assertNotIn('__try',members.decode())  # Same existing fixed SEH leaves.
        self.assertLess(members.index(b'offsetof(GfxImage, delayLoadPixels)'),members.index(b'GfxImage copied{}'))
        self.assertLess(members.index(b'first == second'),members.index(b'scalar::build('))
        self.assertIn(b'copy_fault_ ? nlohmann::ordered_json(nullptr)',members)

    def test_filter_is_bounded_exact_one_comma_and_does_not_publish_other_names(self):
        source=(incoming.HERE/incoming.MODULE).read_text()
        probe=source.split('std::optional<std::string> probe(',1)[1].split('    public:',1)[0]
        self.assertIn("if (first == ',') { name+=','; offset=1; }",probe)
        self.assertIn('i<target_length',probe)
        self.assertIn('!= 0) return std::nullopt',probe)
        self.assertNotIn('tolower',source)
        self.assertIn('callback_limit = 65536',source)
        self.assertIn('read_limit = 2u*1024u*1024u',source)
        self.assertIn('case_count_limit = 16',source)
        self.assertIn('if (counts_[slot] != 1) return;',source)
        self.assertNotIn('ReadProcessMemory',source)
        self.assertNotIn('db_find_x_asset_header',source)
        self.assertNotIn('original_add_and_observe',source)

    def test_distinct_owned_shape_does_not_invent_admission_or_identity(self):
        source=(incoming.HERE/incoming.MODULE).read_text()
        finish=source.split('nlohmann::ordered_json finish(',1)[1]
        for forbidden in ('copy_leaf(','.range(','.readable(','.name(', 'db_find_', 'pointer->'):
            self.assertNotIn(forbidden,finish)
        for token in ('"not_observed"','"target_matched_sample_refused"','"repeated_target_ambiguous"','"first_complete_sample"',
                      '"partial_or_refused_callback_window"','"not_observed_in_this_bounded_callback_window"'):
            self.assertIn(token,finish)
        for key in ('descriptor_admissible','source_asset_name_association_proven','model_binding_correlated','renderer_binding_proven',
                    'same_pointer_proven','same_object_proven','allocation_retained','atomic_snapshot_proven',
                    'runtime_abi_proven','lifetime_proven','pixels_copied','ready'):
            self.assertIn('{"'+key+'",false}',finish)
        self.assertIn('{"qualified_object_mip_count",nullptr}',finish)
        self.assertNotIn('provenance',finish)

    def test_authored_native_fixture_preserves_actual39_and_declares48_not_passed(self):
        fixture=(incoming.HERE/incoming.FIXTURE).read_text()
        self.assertIn('original_registration_fixture_main()!=0',fixture)
        # Seven bad-argv cases repeat two checks; twelve false claims repeat one.
        self.assertEqual(len(re.findall(r'\bic\(',fixture))-1+12+11,48)
        self.assertIn('incoming_checks!=48',fixture)
        self.assertIn('IW7_T7_INCOMING_IMAGE_CHECKS=48',fixture)
        self.assertIn('reads==0 && !probe.incoming_selected()',fixture)

    @unittest.skipUnless(os.environ.get('IW7_T7_SOURCE'),'Pinned native SOURCE not supplied')
    def test_actual_renderer_arms_before_hook_cominit_and_keeps_image_bypass(self):
        base=BaseRenderer();main,cli=base.base()
        main,cli,_=provenance.overlay(main,cli,base.read)
        main,cli,_=metadata.overlay(main,cli,base.read)
        main,cli,_=registration.overlay(main,cli,base.read)
        original_observer=registration.observer_source(base.read(incoming.HERE/'selected_image_provenance.hpp',32*1024)).encode()
        new_main,new_cli=incoming.wire(main,cli,original_observer,
            self.read(incoming.HERE/registration.CAPTURE,32*1024),self.read(incoming.HERE/incoming.MEMBERS,16*1024),
            self.read(incoming.HERE/incoming.MODULE,32*1024),self.read(incoming.HERE/incoming.ENTRY,16*1024))
        contract=json.loads((incoming.HERE/incoming.CONTRACT).read_text())
        for role,value in (('main',new_main),('cli',new_cli)):
            self.assertEqual((len(value.encode()),hashlib.sha256(value.encode()).hexdigest()),
                             (contract[role]['bytes'],contract[role]['sha256']))
        self.assertEqual(incoming.overlay(main,cli,self.read),(new_main,new_cli))
        early=new_cli.split('void init_zonetool()',1)[1]
        self.assertLess(early.index('configure_incoming(get_command_line_arguments(), true)'),early.index('db_add_xasset_hook.create('))
        self.assertEqual(early.count(incoming.FLAG),1)
        bypass=new_cli.split('if (type == ASSET_TYPE_IMAGE)\n\t\t{',1)[1].split('\n\t\t}',1)[0]
        self.assertIn('before_image_bypass(type, header);\n\t\t\treturn header;',bypass)
        self.assertNotIn('invoke<',bypass)
        self.assertEqual(new_cli.count('db_add_xasset_hook.invoke<XAssetHeader>(original_type, original_header)'),1)
        entry=(incoming.HERE/incoming.ENTRY).read_text()
        self.assertNotIn('configure_incoming',entry)
        self.assertNotIn('db_find_x_asset_header',entry)
        self.assertNotIn('.begin_registration_metadata(',entry)
        self.assertLess(len(new_cli.encode()),192*1024)
        with self.assertRaises(ValueError):incoming.wire(new_main,new_cli,b'',b'',b'',b'',b'')


if __name__=='__main__':unittest.main()

"""Source transition/contract checks only; the causal C++ fixture needs CPP GO."""
import hashlib
import json
import os
from pathlib import Path
import re
import unittest
import prepare_cli
import prepare_catalog_trace as trace
import prepare_message_publication as publication
import prepare_material_parts as parts
import prepare_image_provenance as provenance


class ProvenanceSourceTests(unittest.TestCase):
    def test_native_scope_guard_is_the_actual_fixed_predicate(self):
        text=(provenance.HERE/provenance.ENTRY).read_text()
        predicate=text.split('if (',1)[1].split(')\n',1)[0].replace('||',' or ')
        for zone,model,lod,refused in [
            ("mp_freerun_04","p7_fre_platform_cap_02","0",False),
            ("cp_zmb","p7_fre_platform_cap_02","0",True),
            ("mp_freerun_04","another_model","0",True),
            ("mp_freerun_04","p7_fre_platform_cap_02","1",True),
            ("mp_freerun_04","p7_fre_platform_cap_02","00",True)]:
            self.assertEqual(eval(predicate,{"__builtins__":{}},{
                "zone_arg":zone,"model_arg":model,"lod_arg":lod}),refused)
        self.assertLess(text.index('.begin()'),text.index('resident_export_load_zone('))
        self.assertLess(text.index('db_find_x_asset_header('),text.index('.finish('))
        self.assertIn('DB_IsXAssetDefault(ASSET_TYPE_XMODEL',text)
        self.assertLess(text.index('ZONETOOL_INFO('),text.index('if (!report.at("capture_complete")'))
        for forbidden in ("ASSET_TYPE_IMAGE","GfxImage*","pixels","streamedParts",
                          "get_data_for_xpak_key","read.one","::dump("):
            self.assertNotIn(forbidden,text)

    def test_provenance_never_copies_the_image_body_or_changes_original_add(self):
        text=(provenance.HERE/provenance.HELPER).read_text()
        self.assertIn('image_span = 264',text)
        self.assertIn('value.memory = query_(binding.image);',text)
        self.assertIn('read.unchanged(material.textureTable + binding_index, binding);',text)
        self.assertIn('search_limit = 1024',text)
        self.assertIn('base::reader<Readable> search_;',text)
        for forbidden in ('read.one(binding.image','read.unchanged(binding.image',
                          'ReadProcessMemory(', 'memcpy(', 'streamedParts[','->pixels'):
            self.assertNotIn(forbidden,text)
        body=text.split('XAssetHeader original_add_and_observe(',1)[1].split(
            'nlohmann::ordered_json finish(',1)[0]
        self.assertEqual(body.count('original(type, incoming)'),1)
        self.assertLess(body.index('original(type, incoming)'),body.index('after_model_add('))
        self.assertIn('return returned;',body)
        self.assertNotIn('+ 8',body)
        self.assertIn('std::atomic<bool> active_',text)
        self.assertIn('std::atomic<bool> search_refused_',text)
        for false_flag in ("same_object_proven","lifetime_proven","allocation_retained",
                           "pixels_copied","registration_path_changed","ready"):
            self.assertIn('{"'+false_flag+'", false}',text)
        self.assertIn('nlohmann::ordered_json(nullptr)',text)
        callback=text.split('void after_model_add(',1)[1].split(
            'template <typename OriginalAdd>',1)[0]
        self.assertLess(callback.index('const std::lock_guard lock(mutex_)'),
            callback.index('try\n                {'))
        self.assertIn('IW7_PROVENANCE_BEFORE_REFUSAL(mutex_);',callback)
        self.assertIn('search_refused_ = true; // Publish before the same lock is released.',callback)
        self.assertIn('#ifdef IW7_PROVENANCE_FIXTURE',callback)

    def test_native_fixture_contains_causal_return_and_missing_association_cases(self):
        text=(provenance.HERE/provenance.FIXTURE).read_text()
        for case in ('observation::observe_binding(', 'probe.original_add_and_observe(',
                     'inactive_return.data==&f.model', 'active_return.data==&f.model',
                     'incoming.data = reinterpret_cast<void*>', 'Original");',
                     'different.at("header_changed") == true', 'absent.at("header_changed").is_null()',
                     'twice.at("duplicate_registration")', 'v.rows[0].extent=1', 'v.count=3',
                     'state_change.finish(', 'count_budget.finish(', 'name_budget.finish(',
                     'false_positive=old_gap.finish(', 'held->try_lock()', 'requested.wait()',
                     'corrected_result.at("capture_complete") == false'):
            self.assertIn(case,text)
        self.assertNotIn('sleep_for(',text)
        self.assertNotIn('Sleep(',text)


@unittest.skipUnless(os.environ.get("IW7_T7_SOURCE"),"Pinned native SOURCE not supplied")
class ProvenanceTransitionTests(unittest.TestCase):
    def base(self):
        _,rendered=prepare_cli.render(Path(os.environ["IW7_T7_SOURCE"]))
        main=trace.wire_message_main(rendered[prepare_cli.PATHS[0]])
        return publication.overlay(main,rendered[prepare_cli.PATHS[1]])

    def inputs(self):
        return tuple((provenance.HERE/name).read_bytes().replace(b"\r\n",b"\n")
            for name in ("selected_material_observation.hpp",provenance.HELPER,provenance.ENTRY))

    def read(self,path,limit,expected=None):
        raw=path.read_bytes().replace(b"\r\n",b"\n")
        self.assertLessEqual(len(raw),limit)
        if expected:self.assertEqual(hashlib.sha256(raw).hexdigest(),expected)
        return raw

    def test_actual_render_retains_the_image_bypass_and_exact_return_forwarder(self):
        main,cli=self.base()
        self.assertEqual(parts.pin(main.encode()),parts.BASE_MAIN)
        self.assertEqual(parts.pin(cli.encode()),parts.BASE_CLI)
        out_main,out_cli=provenance.wire(main,cli,*self.inputs())
        self.assertEqual(out_main.count(provenance.FLAG),2)
        self.assertLessEqual(len(out_cli.encode()),128*1024)
        self.assertIn('if (provenance) observe_selected_image_provenance_iw7',out_cli)
        self.assertLess(out_cli.index('*p > 0x7e'),out_cli.index(
            'if (provenance) observe_selected_image_provenance_iw7'))
        original_image='\t\tif (type == ASSET_TYPE_IMAGE)\n\t\t{\n\t\t\treturn header;\n\t\t}'
        self.assertEqual(out_cli.count(original_image),1)
        stub=out_cli.split('XAssetHeader db_add_xasset_stub(',1)[1].split(
            'utils::hook::detour db_finish_load_x_file_hook;',1)[0]
        self.assertLess(stub.index(original_image),stub.index('.original_add_and_observe('))
        self.assertEqual(stub.count('db_add_xasset_hook.invoke<XAssetHeader>'),1)
        self.assertIn('(original_type, original_header)',stub)
        self.assertNotIn('ASSET_TYPE_IMAGE,',stub)
        self.assertEqual(self.base(),(main,cli))
        # The existing G3 renderer still produces its exact frozen pair.
        old_main,old_cli,_=parts.overlay(main,cli,self.read)
        self.assertEqual(parts.pin(old_main.encode()),(43366,
            "031464d8b41c6ae56c94b33f5d65e228b1ab1f4899c40e3688597c4cf7e526d5"))
        self.assertEqual(parts.pin(old_cli.encode()),(124224,
            "0dd4b3bef7c28be797243f8bdc771c65c54d06e28cbf0a300893eaf645cc379d"))

    def test_actual_exclusive_predicate_refuses_mixed_or_malformed_modes(self):
        main,cli=provenance.wire(*self.base(),*self.inputs())
        predicate=cli.split('if (('+provenance.FLAG+' && !provenance)',1)[1].split(
            'throw std::runtime_error("Exclusive exact image-provenance arguments required");',1)[0]
        predicate='(('+provenance.FLAG+' && !provenance)'+predicate
        predicate=predicate.strip()[:-1]
        predicate=re.sub(r'utils::flags::has_flag\("([^"]+)"\)',r'flag("\1")',predicate)
        predicate=predicate.replace('&&',' and ').replace('||',' or ')
        predicate=re.sub(r'!(?!=)',' not ',predicate)
        for exact,flags,refused in [
            (True,{"t7-iw7-image-provenance-v1"},False),
            (False,{"t7-iw7-image-provenance-v1"},True),
            (True,{"t7-iw7-image-provenance-v1","t7-iw7-material-parts-v1"},True),
            (True,{"t7-iw7-image-provenance-v1","t7-prepatch-link-v3"},True),
            (False,{"t7-iw7-catalog"},False)]:
            self.assertEqual(eval(' '.join(predicate.split()),{"__builtins__":{}},
                {"provenance":exact,"flag":lambda name:name in flags}),refused)

    def test_contract_and_wrong_base_epoch_refusals(self):
        main,cli=self.base()
        out_main,out_cli,marker=provenance.overlay(main,cli,self.read)
        self.assertEqual(marker["MainSHA256"],provenance.pin(out_main.encode())[1])
        self.assertEqual(marker["CLISHA256"],provenance.pin(out_cli.encode())[1])
        for changed_main,changed_cli in ((main+" ",cli),(main,cli+" ")):
            with self.assertRaises(ValueError):
                provenance.wire(changed_main,changed_cli,*self.inputs())
        def changed(path,limit,expected=None):
            raw=self.read(path,limit,expected)
            return raw+b" " if path.name==provenance.HELPER else raw
        with self.assertRaises(ValueError):provenance.overlay(main,cli,changed)
        contract=json.loads((provenance.HERE/provenance.CONTRACT).read_text())
        contract["files"][provenance.HELPER]["lf_bytes"]=True
        def mistyped(path,limit,expected=None):
            return json.dumps(contract).encode() if path.name==provenance.CONTRACT else self.read(path,limit,expected)
        with self.assertRaises(ValueError):provenance.overlay(main,cli,mistyped)


if __name__=="__main__":unittest.main()

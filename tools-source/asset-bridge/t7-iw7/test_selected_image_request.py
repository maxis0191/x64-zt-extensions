"""Authored closed metadata only; no game, package, provider or native IO."""
import copy
from dataclasses import replace
import unittest
import tempfile
from unittest.mock import patch
from pathlib import Path

import selected_image_request as s
import resident_image
from test_image_metadata_consumer import report as f2_report


def body_report():
    image = dict(schema="iw7.t7-selected-image-header-metadata/1", source_profile=s.PROFILE,
                 header_bytes=264, image_name="authored_image", image_name_observed=True,
                 width=8,height=8,depth=1,width1=4,height1=4,level_count=7,level_count1=3,
                 map_type=1,format_namespace="DXGI_FORMAT",format_namespace_attestation="source-layout-member",
                 dxgi_format=72,total_size=40,flags=123,streaming=1,streamed_part_count=2,
                 use_fallback=1,fallback_level=3,fallback_size=8,fallback_pointer_present=True,
                 delay_load_pixels=True,source_semantic=2,pixel_payload_bytes_read=0,
                 allocation_retained=False,atomic_snapshot_proven=False,runtime_abi_proven=False,
                 lifetime_proven=False,ready=False,
                 parts=[dict(index=i,active=i<2,width=4 if i==0 else 8,height=4 if i==0 else 8,
                             packed_size_raw=(8 if i==0 else 40)<<4|3,
                             key_hex=f"deadbeef0000000{i+1}") for i in range(4)])
    result = dict.fromkeys(s.FALSES, False)
    result.update(dict.fromkeys(s.TRUES, True))
    result.update(schema=s.SCHEMA,source_profile="t7-image-metadata-v1",native_source_commit=s.PIN,
                  zone="mp_freerun_04",model="p7_fre_platform_cap_02",lod=0,slot=0,binding_index=4,
                  binding_hash_u32=2695565377,image_header_bytes=264,header_copies=2,payload_bytes_read=0,
                  failure_stage="",reason="",image=image,provenance=f2_report())
    return result


def select(value, **kwargs):
    return s.select_image(value, part_index=1, native_exit_code=0, qualified_object_mip_count=1, **kwargs)


class SelectedRequestTests(unittest.TestCase):
    def test_owned_bytes_publication_is_exclusive_and_has_no_material_or_render_claim(self):
        result=select(body_report())
        with tempfile.TemporaryDirectory() as temp:
            output=str(Path(temp)/"authored.dds")
            pixels=bytes(range(32))
            receipt=result.publish_dds(pixels,output)
            self.assertEqual(Path(output).read_bytes()[148:],pixels)
            self.assertFalse(receipt["material_verified"])
            self.assertFalse(receipt["rendered_verified"])
            with self.assertRaises(FileExistsError): result.publish_dds(pixels,output)
            self.assertEqual(Path(output).read_bytes()[148:],pixels)
            missing=str(Path(temp)/"bad.dds")
            with self.assertRaises(ValueError): result.publish_dds(bytes(33),missing)
            self.assertFalse(Path(missing).exists())

    def test_entire_delta_preserves_raw_metadata_and_srgb_without_native_flags_forgery(self):
        report = body_report(); before=copy.deepcopy(report)
        result = select(report)
        self.assertEqual((result.key_hex,result.expected_bytes,result.image.width,result.image.dxgi_format),
                         ("deadbeef00000002",32,8,72))
        self.assertEqual(result.image.level_count, 1)
        self.assertEqual(result.raw_packed_size & 15, 3)  # Not interpreted as a mip count.
        self.assertEqual(report,before)
        self.assertFalse(hasattr(result.image,"streaming"))
        self.assertEqual(resident_image.object_to_dds(result.image,bytes(range(32)))[148:],bytes(range(32)))

    def test_missing_body_old_f2_refused_exit_or_unobserved_source_cannot_select(self):
        for value in (f2_report(),None,dict(body_report(),image=None),dict(body_report(),body_observed=False),
                      dict(body_report(),refused=True),dict(body_report(),model_default=True)):
            with self.subTest(value=type(value)), self.assertRaises(ValueError): select(value)
        for code in (1,-1,True):
            with self.assertRaises(ValueError):
                s.select_image(body_report(),part_index=1,native_exit_code=code,qualified_object_mip_count=1)

    def test_pending_namespace_wrong_layout_and_unknown_owned_name_refuse(self):
        for field,value in (("format_namespace_attestation","pending"),("format_namespace","GfxPixelFormat"),
                            ("source_profile","unknown"),("image_name",None),("image_name_observed",False),
                            ("header_bytes",268),("runtime_abi_proven",True)):
            report=body_report();report["image"][field]=value
            with self.subTest(field=field), self.assertRaises(ValueError): select(report)

    def test_unknown_single_mip_fact_padding_and_multimip_whole_objects_refuse(self):
        for count in (None,False,2):
            with self.assertRaises(ValueError):
                s.select_image(body_report(),part_index=1,native_exit_code=0,qualified_object_mip_count=count)
        for cumulative in (39,41,48,56):
            report=body_report();report["image"]["parts"][1]["packed_size_raw"]=cumulative<<4|3
            with self.subTest(size=cumulative), self.assertRaises(ValueError): select(report)

    def test_part_order_activity_count_size_and_typed_values_are_exact(self):
        for field,value in (("index",True),("index",2),("active",False),("packed_size_raw",128),
                            ("packed_size_raw",True),("key_hex","DEADBEEF00000002"),
                            ("key_hex","0000000000000000"),("width",0)):
            report=body_report();report["image"]["parts"][1][field]=value
            with self.subTest(field=field,value=value), self.assertRaises(ValueError): select(report)
        for field,value in (("streamed_part_count",5),("streaming",0),("depth",2),("map_type",4),("dxgi_format",27)):
            report=body_report();report["image"][field]=value
            with self.subTest(field=field), self.assertRaises(ValueError): select(report)

    def test_provenance_and_native_rechecks_cannot_be_replaced_by_claims(self):
        for field,value in (("association_rechecked",False),("header_rechecked",1),("name_rechecked",False),
                            ("header_copies",1),("binding_index",3),("payload_bytes_read",1),("ready",True),
                            ("failure_stage","header")):
            report=body_report();report[field]=value
            with self.subTest(field=field), self.assertRaises(ValueError): select(report)
        report=body_report();report["provenance"]=None
        with self.assertRaises(ValueError): select(report)

    def test_only_existing_reader_arguments_are_returned_without_io(self):
        result=select(body_report())
        providers=[s.Provider(r"C:\stock\zone\map.xpak","AABBCCDD:0000000000000001",4096)]
        with patch.object(Path,"open",side_effect=AssertionError("IO")):
            args=result.argv(providers,r"D:\private\authored.bin")
        self.assertEqual(args,["--key","deadbeef00000002","--expected-bytes","32","--out",r"D:\private\authored.bin",
                               "--package",r"C:\stock\zone\map.xpak","AABBCCDD:0000000000000001","4096"])
        for output in (r"C:\stock\zone\authored.bin",r"D:\private\a.exe:authored.bin",r"\\?\D:\private\a.bin","relative.bin"):
            with self.subTest(output=output), self.assertRaises(ValueError): result.argv(providers,output)
        for bad in ([],providers*2,[replace(providers[0],identity="aabbccdd:0000000000000001")],
                    [replace(providers[0],bytes=True)],[replace(providers[0],path=r"C:\stock\a.exe")]):
            with self.assertRaises(ValueError): result.argv(bad,r"D:\private\a.bin")


if __name__ == "__main__":
    unittest.main()

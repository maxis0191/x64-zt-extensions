import copy
import unittest
import boot_contract as b
import export_contract as e


def fixture():
    request = b.make_request('fixture_zone', 'fixture/model', 0)
    report = dict.fromkeys(e.FIELDS, False)
    report.update(schema='iw7.t7-iw7-resident-export/1', requested_zone=request['zone'],
                  source_model=request['model'], selected_source_lod=0, output_model_name=request['model'],
                  output_mesh_name='fixture/mesh', output_root_key=b.command_review(request)['private_output_root_key'],
                  target='iw7', profile=b.PROFILE, geometry_profile='t7-iw7-resident-static-v1',
                  material_dependencies=['fixture/material'],
                  model={'relative_path':'xmodel/fixture/model.xmb','bytes':1,'sha256':'a'*64},
                  mesh={'relative_path':'xsurface/fixture/mesh.xsb','bytes':1,'sha256':'b'*64})
    return request, report


class ExportContractTests(unittest.TestCase):
    def test_backslash_identity_uses_generic_relative_path(self):
        request, report = fixture()
        request['model'] = r'fixture\model'
        report.update(source_model=request['model'], output_model_name=request['model'],
                      output_mesh_name=r'fixture\mesh', output_root_key=b.command_review(request)['private_output_root_key'])
        self.assertTrue(e.validate_export(report, request)['receipt_contract_verified'])

    def test_invented_receipt_only_qualifies_contract(self):
        request, report = fixture()
        result = e.validate_export(report, request)
        self.assertTrue(result['receipt_contract_verified'])
        self.assertFalse(result['artifact_bytes_freshly_verified'])
        self.assertFalse(result['asset_zone_ownership_verified'])

    def test_renames_wrong_lod_and_root_refuse(self):
        request, report = fixture()
        for key, value in (('source_model','other'),('output_model_name','other'),
                           ('selected_source_lod',True),('output_root_key','other')):
            with self.assertRaises(ValueError): e.validate_export({**report,key:value}, request)

    def test_default_payload_and_readiness_claims_refuse(self):
        request, report = fixture()
        for key in ('dependency_payloads_verified','zonetool_xpak_helper_reads_allowed','engine_io_verified','asset_zone_ownership_verified',
                    'serialized_parse_verified','runtime_verified','ready'):
            with self.assertRaises(ValueError): e.validate_export({**report,key:True}, request)

    def test_escaped_output_oversize_and_incomplete_digest_refuse(self):
        request, report = fixture()
        for key, value in (('relative_path','../escape.xmb'),('bytes',1024**2+1),('sha256','a'*63)):
            changed = copy.deepcopy(report); changed['model'][key] = value
            with self.assertRaises(ValueError): e.validate_export(changed, request)

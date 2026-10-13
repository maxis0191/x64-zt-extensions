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
                  root_bone_name='fixture_root', selected_counts={'bones':1,'roots':1,'surfaces':1,'vertices':17,'triangles':23},
                  material_dependencies=['fixture/material'],
                  model={'relative_path':'xmodel/fixture/model.xmb','bytes':1,'sha256':'a'*64},
                  mesh={'relative_path':'xsurface/fixture/mesh.xsb','bytes':1,'sha256':'b'*64})
    return request, report


def fixture_v2(counts=((17, 23),) * 5):
    request, report = fixture()
    vertices, triangles = map(sum, zip(*counts))
    report.update(schema=e.SCHEMA_V2, geometry_profile='t7-iw7-resident-static-v2',
                  selected_counts={'bones':1, 'roots':1, 'surfaces':len(counts),
                                   'vertices':vertices, 'triangles':triangles},
                  surface_records=[{'index':i, 'material_slot':i, 'vertices':v, 'triangles':t}
                                   for i, (v, t) in enumerate(counts)],
                  material_dependencies=['fixture/material'] * len(counts),
                  geometry_work_bytes_upper_bound=256 + 368*len(counts) + 60*vertices + 12*triangles)
    return request, report


class ExportContractTests(unittest.TestCase):
    def test_bone_and_counts_are_observed_bounded_values(self):
        request, report = fixture()
        for name in ('root tag', 'root/unchanged'):
            self.assertTrue(e.validate_export({**report,'root_bone_name':name}, request)['receipt_contract_verified'])
        for name in ('', 'x'*256, 'bad\nname', None):
            with self.assertRaises(ValueError): e.validate_export({**report,'root_bone_name':name}, request)
        for key, value in (('bones',2),('roots',True),('surfaces',0),('vertices',2),('triangles',65536)):
            changed = copy.deepcopy(report); changed['selected_counts'][key] = value
            with self.assertRaises(ValueError): e.validate_export(changed, request)

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


class MultisurfaceContractTests(unittest.TestCase):
    def test_one_five_and_maximum_surface_count(self):
        for count in (1, 5, 255):
            with self.subTest(count=count):
                request, report = fixture_v2(((3, 1),) * count)
                self.assertTrue(e.validate_export(report, request)['receipt_contract_verified'])
        for count in (256,):
            request, report = fixture_v2(((3, 1),) * count)
            with self.assertRaises(ValueError): e.validate_export(report, request)

    def test_aggregate_can_exceed_uint16_but_each_surface_cannot(self):
        request, report = fixture_v2(((40000, 40000), (40000, 40000)))
        self.assertTrue(e.validate_export(report, request)['receipt_contract_verified'])
        for pair in ((65536, 1), (3, 65536), (2, 1), (3, 0), (True, 1), (3, True)):
            changed_request, changed = fixture_v2((pair,))
            with self.subTest(pair=pair), self.assertRaises(ValueError):
                e.validate_export(changed, changed_request)

    def test_repeated_material_slots_preserve_order_without_mutation(self):
        request, report = fixture_v2(((3, 1),) * 3)
        report['material_dependencies'] = ['fixture/b', 'fixture/a', 'fixture/b']
        original = copy.deepcopy(report)
        e.validate_export(report, request)
        self.assertEqual(report, original)
        for names in (['fixture/b', 'fixture/a'], ['fixture/b'] * 4, ['fixture/b', None, 'fixture/b']):
            with self.subTest(names=names), self.assertRaises(ValueError):
                e.validate_export({**report, 'material_dependencies':names}, request)

    def test_surface_order_slots_and_exact_records_are_required(self):
        request, report = fixture_v2()
        mutations = [('index', 0), ('index', True), ('material_slot', 0), ('material_slot', True),
                     ('unexpected', 0)]
        for key, value in mutations:
            changed = copy.deepcopy(report)
            changed['surface_records'][1][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                e.validate_export(changed, request)
        for records in ([], report['surface_records'][:-1], tuple(report['surface_records']),
                        list(reversed(report['surface_records'])), [None]*5):
            with self.assertRaises(ValueError):
                e.validate_export({**report, 'surface_records':records}, request)

    def test_totals_are_recomputed_from_all_surfaces(self):
        request, report = fixture_v2()
        for key in ('vertices', 'triangles', 'surfaces'):
            changed = copy.deepcopy(report)
            changed['selected_counts'][key] += 1
            with self.subTest(key=key), self.assertRaises(ValueError): e.validate_export(changed, request)
        changed = copy.deepcopy(report)
        changed['surface_records'][-1]['vertices'] += 1
        with self.assertRaises(ValueError): e.validate_export(changed, request)

    def test_exact_work_boundary_then_one_more_triangle_refused(self):
        # Six legal uint16 surfaces reach exactly 16 MiB of expanded work.
        counts = ((50000, 65535), (50000, 65535), (50000, 16823),
                  (50000, 1), (49997, 1), (3, 1))
        request, report = fixture_v2(counts)
        self.assertEqual(report['geometry_work_bytes_upper_bound'], 16777216)
        self.assertTrue(e.validate_export(report, request)['receipt_contract_verified'])
        request, report = fixture_v2(counts[:-1] + ((3, 2),))
        with self.assertRaisesRegex(ValueError, 'exceeds 16 MiB'): e.validate_export(report, request)

    def test_alias_amplification_refuses_even_when_artifact_sizes_are_tiny(self):
        # Five occurrences may reference the same source/serialized arrays;
        # their expanded work must still be counted five times.
        request, report = fixture_v2(((65535, 65535),) * 5)
        self.assertEqual(report['model']['bytes'], 1)
        self.assertEqual(report['mesh']['bytes'], 1)
        report['geometry_work_bytes_upper_bound'] = 624 + 72*65535
        with self.assertRaisesRegex(ValueError, 'exceeds 16 MiB'): e.validate_export(report, request)

    def test_work_bound_is_exact_integer_not_trusted_metadata(self):
        request, report = fixture_v2()
        work = report['geometry_work_bytes_upper_bound']
        for value in (True, float(work), work-1, work+1, 0, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                e.validate_export({**report, 'geometry_work_bytes_upper_bound':value}, request)

    def test_versions_require_their_own_exact_fields_and_geometry_profile(self):
        for factory in (fixture, lambda: fixture_v2(((17, 23),))):
            request, report = factory()
            other_schema = e.SCHEMA_V2 if report['schema'] == e.SCHEMA_V1 else e.SCHEMA_V1
            other_profile = ('t7-iw7-resident-static-v2' if report['schema'] == e.SCHEMA_V1
                             else 't7-iw7-resident-static-v1')
            for change in ({'schema':other_schema}, {'geometry_profile':other_profile},
                           {'schema':'iw7.t7-iw7-resident-export/3'}, {'schema':None}):
                with self.subTest(change=change), self.assertRaises(ValueError):
                    e.validate_export({**report, **change}, request)
        request, old = fixture()
        with self.assertRaises(ValueError):
            e.validate_export({**old, 'surface_records':[]}, request)

    def test_existing_bounds_and_unqualified_claims_stay_strict_in_v2(self):
        request, report = fixture_v2()
        for change in ({'root_bone_name':'bad\nname'}, {'ready':True}, {'engine_io_verified':True},
                       {'dependency_payloads_verified':True}, {'source_model':'other'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                e.validate_export({**report, **change}, request)
        for role, size in (('model', 1024**2+1), ('mesh', 16*1024**2+1)):
            changed = copy.deepcopy(report); changed[role]['bytes'] = size
            with self.assertRaises(ValueError): e.validate_export(changed, request)

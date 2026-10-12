import copy
from pathlib import Path
import unittest
from catalog_contract import FALSE_FIELDS, validate_catalog


def fixture(count=1):
    rows = [{'name': 'invented_test_'+str(i).zfill(4), 'reference': False, 'resolved_nondefault': True,
             'counts': {'bones': 1, 'roots': 1, 'cosmetic_bones': 0, 'lods': 2}} for i in range(count)]
    return {'schema': 'iw7.t7-iw7-model-catalog/1', 'requested_zone': 'invented_zone',
            'provenance': 'observed_during_requested_zone_load', 'model_count': count,
            'name_bytes': sum(len(r['name'])+1 for r in rows), 'models': rows, **dict.fromkeys(FALSE_FIELDS, False)}


class CatalogTests(unittest.TestCase):
    def test_empty_and_exact_bound(self):
        for n in (0, 1, 1024): validate_catalog(fixture(n), 'invented_zone')

    def test_overflow_is_not_truncated_success(self):
        with self.assertRaises(ValueError): validate_catalog(fixture(1025), 'invented_zone')
        bad = fixture(); bad['truncated'] = True
        with self.assertRaises(ValueError): validate_catalog(bad, 'invented_zone')

    def test_no_provenance_or_geometry_upgrade(self):
        for field in FALSE_FIELDS:
            bad = fixture(); bad[field] = True
            with self.assertRaises(ValueError): validate_catalog(bad, 'invented_zone')

    def test_exact_request_and_name_byte_count(self):
        bad = fixture(); bad['name_bytes'] += 1
        with self.assertRaises(ValueError): validate_catalog(bad, 'invented_zone')
        with self.assertRaises(ValueError): validate_catalog(fixture(), 'different_zone')

    def test_alias_and_unresolved_rows_have_no_counts(self):
        bad = fixture(); bad['models'][0]['resolved_nondefault'] = False
        with self.assertRaises(ValueError): validate_catalog(bad, 'invented_zone')
        bad['models'][0]['counts'] = None
        validate_catalog(bad, 'invented_zone')

    def test_duplicate_or_non_ascii_name_refused(self):
        bad = fixture(2); bad['models'][1] = copy.deepcopy(bad['models'][0])
        with self.assertRaises(ValueError): validate_catalog(bad, 'invented_zone')
        bad = fixture(); bad['models'][0]['name'] = 'not_ascii_é'
        with self.assertRaises(ValueError): validate_catalog(bad, 'invented_zone')

    def test_no_payload_read_and_failure_precedes_publication(self):
        text = (Path(__file__).parent/'native_catalog.inc').read_text()
        for forbidden in ('converter::', '->meshes', '.meshes', '.boneNames', 'dump_zone(', 'dump_csv('):
            self.assertNotIn(forbidden, text)
        self.assertLess(text.index('resident_export_load_zone(zone)'), text.index('db_find_x_asset_header('))
        self.assertLess(text.index('resident_catalog_failed.load()'), text.index('write_enemy_reference_output('))
        self.assertLess(text.index('bytes.size() > 512u * 1024u'), text.index('CreateDirectoryW('))

    def test_capture_is_bounded_and_never_throws_into_engine(self):
        text = (Path(__file__).parent/'native_catalog_capture.inc').read_text()
        self.assertIn('noexcept', text)
        self.assertIn('catch (...)', text)
        self.assertIn('resident_catalog_names.size() >= resident_catalog_max_names', text)
        self.assertIn('std::lock_guard<std::mutex>', text)


if __name__ == '__main__': unittest.main()

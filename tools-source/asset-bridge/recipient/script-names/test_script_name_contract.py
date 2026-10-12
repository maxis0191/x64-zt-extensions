import copy
import json
from pathlib import Path
import tempfile
import unittest
import script_name_contract as c

def empty():
    return {'schema':'iw7.recipient-script-names/1','donor_map':'cp_zmb','asset_type':49,
            'token_alias_inferred':False,'enumeration':{k:0 for k in c.COUNTERS},
            'targets':[{'key':k,'enum_occurrences':0,'enum':None,'direct':None} for k in c.KEYS],
            'payload_bytes_read':0,'script_bytes_verified':False,'closure_complete':False,'ready':False}

def row(key, identity=1):
    return {'identity':identity,'type':49,'content_name':key,'database_name':key,
            'compressed_len':3,'source_len':20,'bytecode_len':5,'is_default':False}

def matched(key=0, occurrences=1):
    value = empty()
    value['enumeration'].update(callbacks=occurrences,named=occurrences,matched=occurrences,
                                decimal_names=occurrences if key == 1 else 0)
    value['targets'][key].update(enum_occurrences=occurrences, enum=row(c.KEYS[key]))
    return value

class ContractTests(unittest.TestCase):
    def test_empty_enum_is_distinct_from_populated_unmatched(self):
        zero = c.validate(empty())
        value = empty(); value['enumeration'].update(callbacks=5,named=3,null_headers=1,null_names=1,unmatched=3,decimal_names=2)
        other = c.validate(value)
        self.assertEqual(zero['requested_match_occurrences'], other['requested_match_occurrences'])
        self.assertEqual(other['enum_callbacks'], 5)

    def test_canonical_only(self):
        result = c.validate(matched())
        self.assertEqual((result['canonical_matches'],result['numeric_matches']), (1,0))

    def test_numeric_only_does_not_become_canonical(self):
        result = c.validate(matched(1))
        self.assertEqual((result['canonical_matches'],result['numeric_matches']), (0,1))
        self.assertFalse(result['token_alias_inferred'])

    def test_two_distinct_identities_remain_distinct(self):
        value = matched()
        value['enumeration'].update(callbacks=2,named=2,matched=2,decimal_names=1)
        value['targets'][1].update(enum_occurrences=1,enum=row(c.KEYS[1],2))
        self.assertEqual(c.validate(value)['observed_identities'], 2)

    def test_duplicate_same_identity_is_counted(self):
        self.assertEqual(c.validate(matched(occurrences=2))['requested_match_occurrences'], 2)

    def test_conflicting_metadata_for_one_identity_refuses(self):
        value = matched(); value['targets'][0]['direct'] = row(c.KEYS[0])
        value['targets'][0]['direct']['bytecode_len'] = 6
        with self.assertRaisesRegex(ValueError, 'conflicting'): c.validate(value)

    def test_cross_key_same_observed_header_is_not_token_inference(self):
        value = matched(1); value['targets'][0]['direct'] = row(c.KEYS[1])
        self.assertEqual(c.validate(value)['observed_identities'], 1)
        self.assertFalse(c.validate(value)['token_alias_inferred'])

    def test_multiple_enum_rows_for_one_key_refuses(self):
        value = matched(); value['targets'][0]['enum'] = [row(c.KEYS[0]),row(c.KEYS[0],2)]
        with self.assertRaises(ValueError): c.validate(value)

    def test_key_changes_reorder_and_extra_targets_refuse(self):
        for mutate in (lambda v:v['targets'].reverse(), lambda v:v['targets'].append(copy.deepcopy(v['targets'][0])),
                       lambda v:v['targets'][0].update(key='scripts/engine/utility.gsc')):
            value=matched(); mutate(value)
            with self.assertRaises(ValueError): c.validate(value)

    def test_alias_payload_and_ready_claims_refuse(self):
        for key in ('token_alias_inferred','script_bytes_verified','closure_complete','ready','payload_bytes_read'):
            value=matched();value[key]=1 if key=='payload_bytes_read' else True
            with self.subTest(key=key),self.assertRaises(ValueError): c.validate(value)

    def test_counter_limits_types_and_partitions_refuse(self):
        for key,bad in (('callbacks',4097),('callbacks',True),('named',2),('matched',0),('decimal_names',2)):
            value=matched();value['enumeration'][key]=bad
            with self.subTest(key=key,bad=bad),self.assertRaises(ValueError):c.validate(value)

    def test_numeric_match_requires_decimal_count(self):
        value=matched(1);value['enumeration']['decimal_names']=0
        with self.assertRaises(ValueError):c.validate(value)

    def test_invalid_lengths_type_or_name_refuse(self):
        for key,bad in (('compressed_len',-1),('source_len',67108865),('bytecode_len',True),('type',48),
                        ('content_name','2626'),('database_name','x'*241),('database_name','bad\0name'),('is_default',1)):
            value=matched();value['targets'][0]['enum'][key]=bad
            with self.subTest(key=key,bad=bad),self.assertRaises(ValueError):c.validate(value)

    def test_default_observation_is_retained_without_qualification(self):
        value=matched();value['targets'][0]['enum']['is_default']=True
        self.assertFalse(c.validate(value)['ready'])

    def test_missing_enum_with_occurrences_refuses(self):
        value=matched();value['targets'][0]['enum']=None
        with self.assertRaises(ValueError):c.validate(value)

    def test_noncontiguous_identity_refuses(self):
        value=matched();value['targets'][0]['enum']['identity']=4
        with self.assertRaises(ValueError):c.validate(value)

    def test_bounded_generated_json_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'generated.json'
            path.write_text(json.dumps(matched(1)),encoding='utf-8')
            self.assertEqual(c.read_observation(path)['numeric_matches'],1)
            path.write_bytes(b' '*4097)
            with self.assertRaises(ValueError):c.read_observation(path)

    def test_duplicate_json_fields_refuse(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            json.loads('{"ready":false,"ready":true}',object_pairs_hook=c.unique_pairs)

if __name__ == '__main__':
    unittest.main()

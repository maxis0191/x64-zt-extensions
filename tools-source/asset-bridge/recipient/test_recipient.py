"""Synthetic bytes and pure contracts only; no retail/native execution."""
import csv
import hashlib
import io
from pathlib import Path
import struct
import tempfile
import unittest

import recipient_contract as c
import recipient_phase as phase


class RecipientTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.work = Path(self.temporary.name)
        self.payload = self.work/c.SCRIPT_PATH
        self.payload.parent.mkdir(parents=True)
        self.data = c.MODULE.encode()+b'\0'+struct.pack('<iii',3,100,2)+b'abcXY'
        self.payload.write_bytes(self.data)

    def tearDown(self):
        self.temporary.cleanup()

    def manifest(self, **updates):
        row = dict(donor_map='cp_zmb',pack_name=c.PACK,module=c.MODULE,status='dumped',
                   path=c.SCRIPT_PATH,size_bytes=str(self.payload.stat().st_size),sha256=c.sha(self.payload))
        row.update(updates)
        out = io.StringIO(); writer = csv.writer(out)
        writer.writerow(row);writer.writerow(row.values())
        return out.getvalue()

    def test_exact_requests_and_extensionless_module(self):
        materials = '\n'.join(','.join(row) for row in c.REFERENCES)+'\n'
        c.validate_requests(materials,c.MODULE+'\r\n')
        for scripts in (c.MODULE+'.gsc\n',c.MODULE,c.MODULE+'\nextra\n'):
            with self.subTest(scripts=scripts),self.assertRaises(ValueError): c.validate_requests(materials,scripts)
        with self.assertRaises(ValueError): c.validate_requests(materials+'image,extra\n',c.MODULE+'\n')

    def test_commands_do_not_concatenate_or_extract(self):
        refs=c.command('references','tool.exe');scripts=c.command('script','tool.exe')
        self.assertEqual(refs[4:],['-enemy-reference-check','cp_zmb','recipient-material.csv',c.REFERENCE_NAME])
        self.assertEqual(scripts[4:],['-enemy-script-dump','cp_zmb','recipient-scripts.txt',c.PACK])
        for flag in ('-dumpasset','-enemy-extract','-enemy-image-dump','-dumpzone'):
            self.assertNotIn(flag,refs+scripts)
        with self.assertRaises(ValueError): c.command('normal','tool.exe')

    def test_reference_results_are_ordered_nondefault_and_not_content(self):
        value='type,name,status\n'+'\n'.join(','.join((*r,'verified')) for r in c.REFERENCES)+'\n'
        self.assertEqual(c.reference_result(value),dict(verified_references=4,serialized_content_observed=False))
        for bad in (value.replace('verified','default_asset',1),value+value.splitlines()[1]+'\n',
                    '\n'.join(value.splitlines()[::-1]),value.replace('type,name,status','name,type,status')):
            with self.subTest(bad=bad),self.assertRaises(ValueError): c.reference_result(bad)

    def test_real_serializer_layout_and_source_len_not_written(self):
        result=c.script_result(self.work,self.manifest())
        self.assertEqual(result['bytes'],40)
        self.assertEqual(result['source_len'],100)
        self.assertEqual(result['sha256'],hashlib.sha256(self.data).hexdigest())
        self.assertFalse(result['decompressed']);self.assertFalse(result['transitive_imports_verified'])
        self.assertEqual(c.MAX_SCRIPT,134217763)

    def test_manifest_wrong_target_hash_status_and_size_rejected(self):
        cases=({'path':'../utility.gscbin'},{'module':c.MODULE+'.gsc'},{'status':'missing_asset'},
               {'sha256':'0'*64},{'size_bytes':'41'},{'donor_map':'cp_rave'})
        for changes in cases:
            with self.subTest(changes=changes),self.assertRaises(ValueError): c.script_result(self.work,self.manifest(**changes))

    def test_duplicate_and_extra_columns_and_rows_rejected(self):
        lines=self.manifest().splitlines()
        cases=(self.manifest()+lines[1]+'\n',lines[0]+',sha256\n'+lines[1]+','+c.sha(self.payload)+'\n',
               lines[0]+'\n'+lines[1]+',extra\n','\n'.join(lines[::-1]))
        for value in cases:
            with self.subTest(value=value),self.assertRaises(ValueError): c.script_result(self.work,value)

    def test_invalid_lengths_and_trailing_bytes_rejected(self):
        for lengths in ((-1,100,2),(3,-1,2),(3,c.MAX_BUFFER+1,2),(3,100,3)):
            self.payload.write_bytes(c.MODULE.encode()+b'\0'+struct.pack('<iii',*lengths)+b'abcXY')
            with self.subTest(lengths=lengths),self.assertRaises(ValueError): c.script_result(self.work,self.manifest())
        self.payload.write_bytes(self.data+b'extra')
        with self.assertRaises(ValueError): c.script_result(self.work,self.manifest())

    def test_wrong_name_and_truncation_rejected(self):
        for data in (self.data.replace(b'utility',b'wronggg'),self.data[:34],b''):
            self.payload.write_bytes(data)
            with self.subTest(data=data),self.assertRaises(ValueError): c.script_result(self.work,self.manifest())

    def test_output_observation_never_claims_complete_package(self):
        target=self.work/'dump'/c.PACK/'scriptfile-manifest.csv'
        target.write_text(self.manifest(),encoding='utf-8')
        observed=c.check_output('script',self.work)
        self.assertFalse(observed['closure_complete']);self.assertFalse(observed['package_ready'])
        self.assertEqual(observed['manifest_sha256'],c.sha(target))

    def test_text_bound_and_missing_output_refuse(self):
        path=self.work/'large.txt';path.write_bytes(b'x'*16385)
        with self.assertRaises(ValueError): c.text(path)
        with self.assertRaises(FileNotFoundError): c.check_output('references',self.work)

    def test_phase_refuses_bad_contract_before_launch(self):
        with self.assertRaises(ValueError): phase.run({'schema':'unknown','phase':'script'},None)
        with self.assertRaises(ValueError): phase.run({'schema':'iw7.recipient-phase/1','phase':'images'},None)
        with self.assertRaises(ValueError): phase.run({'schema':'iw7.recipient-phase/1','phase':'script','timeout':241,'sha256':c.EXE_SHA},None)


if __name__ == '__main__':
    unittest.main(verbosity=2)

"""Finite environment transition checks; authored metadata, no DLL reads."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
import prepare_build as build


class OSResourceTests(unittest.TestCase):
    def proof(self):
        return dict(Schema='iw7.t7-os-resource-qualification/1',Status='ObservationComplete',
            GuardsDisposed=True,LeaseReleased=True,Ready=False,CPPExecuted=False,
            CandidateExecuted=False,StockRead=False,Postflight=dict(Leases=[]),
            Pins=[dict(GuardPassed=True,ExpectedBytes=1,ActualBytes=1,
                ExpectedSHA256='a'*64,ActualSHA256='a'*64) for _ in range(10)],
            OSResource=dict(Path=build.OS_RESOURCE_PATH,HistoricalBytes=12288,
                HistoricalSHA256=build.OS_RESOURCE_BEFORE,ObservedBytes=12288,
                ObservedSHA256=build.OS_RESOURCE_AFTER,ProductVersion='10.0.26100.9711',
                CompanyName='Microsoft Corporation',SignatureStatus='Valid',SignatureType='Catalog',
                SignerSubject='CN=Microsoft Windows, O=Microsoft Corporation, L=Redmond, S=Washington, C=US',
                SignerThumbprint='667BBA1E1F478221AA65DE4F75187A751B03A453',
                ContractAccepted=False,PinAdopted=False))

    def expected(self):
        return {build.key(build.OS_RESOURCE_PATH):dict(Path=build.OS_RESOURCE_PATH,
            Bytes=12288,SHA256=build.OS_RESOURCE_BEFORE),'unrelated':dict(Path='other',Bytes=7,SHA256='b'*64)}

    def apply(self, proof, expected=None):
        raw=json.dumps(proof).encode()
        raw+=b' '*(build.OS_RESOURCE_PROOF[0]-len(raw))
        def read(path,limit,digest):
            self.assertEqual((path,limit,digest),(Path('authored-proof.json'),16*1024,build.OS_RESOURCE_PROOF[1]))
            return raw
        target=self.expected() if expected is None else expected
        marker=build.os_resource_context(Path('authored-proof.json'),read,target)
        return marker,target

    def test_default_and_explicit_paired_selection(self):
        self.assertFalse(build.os_resource_selected(SimpleNamespace()))
        for family in ('material_parts_v1','prepatch_link_v3','prepatch_image_caller_v1'):
            args=SimpleNamespace(os_context_tzres_20261014=True,os_context_proof=Path('proof'))
            setattr(args,family,True)
            self.assertTrue(build.os_resource_selected(args))
        for value in (1,'true',None):
            with self.assertRaises(ValueError):build.os_resource_selected(SimpleNamespace(os_context_tzres_20261014=value))
        for args in (SimpleNamespace(os_context_proof=Path('proof')),
                     SimpleNamespace(os_context_tzres_20261014=True),
                     SimpleNamespace(os_context_tzres_20261014=True,os_context_proof=Path('proof'))):
            with self.assertRaises(ValueError):build.os_resource_selected(args)

    def test_only_one_exact_pin_changes_and_proof_is_bound(self):
        old=self.expected();marker,after=self.apply(self.proof())
        self.assertEqual(after['unrelated'],old['unrelated'])
        self.assertEqual(after[build.key(build.OS_RESOURCE_PATH)],dict(Path=build.OS_RESOURCE_PATH,Bytes=12288,SHA256=build.OS_RESOURCE_AFTER))
        self.assertEqual(marker['Before'],old[build.key(build.OS_RESOURCE_PATH)])
        self.assertEqual(marker['Evidence']['SHA256'],build.OS_RESOURCE_PROOF[1])
        self.assertFalse(marker['KBFileAttributionVerified'])

    def test_wrong_typed_identity_signature_closure_and_suffix_refuse_without_mutation(self):
        for section,key,value in [(None,'LeaseReleased',False),(None,'Ready',True),
                ('OSResource','Path','C:\\other\\tzres.dll'),('OSResource','ObservedBytes',True),
                ('OSResource','ObservedSHA256','c'*64),('OSResource','SignatureStatus','NotSigned'),
                ('OSResource','SignatureType','Authenticode'),('OSResource','ProductVersion','other'),
                ('OSResource','PinAdopted',True),('OSResource','ContractAccepted',True),
                ('OSResource','SignerThumbprint','bad')]:
            proof=self.proof();(proof if section is None else proof[section])[key]=value
            expected=self.expected();before=copy.deepcopy(expected)
            with self.subTest(key=key),self.assertRaises(ValueError):self.apply(proof,expected)
            self.assertEqual(expected,before)
        for kind in ('missing','changed','duplicate-suffix','hash'):
            proof=self.proof();expected=self.expected()
            if kind=='missing':expected.pop(build.key(build.OS_RESOURCE_PATH))
            elif kind=='changed':expected[build.key(build.OS_RESOURCE_PATH)]['SHA256']=build.OS_RESOURCE_AFTER
            elif kind=='duplicate-suffix':proof['Pins'].append(proof['Pins'][0])
            else:proof['Pins'][0]['ActualSHA256']='d'*64
            with self.subTest(kind=kind),self.assertRaises(ValueError):self.apply(proof,expected)


if __name__=='__main__':unittest.main()

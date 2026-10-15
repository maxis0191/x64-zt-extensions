"""Actual neutral PowerShell readers/readback path on small owned Source fixtures.

No native types, compiler, EXE, stock, lease or engine is opened by these tests.
The native C++ fixture remains authored until a separate CPP authorization.
"""
import hashlib
import json
from pathlib import Path
import unittest
import test_export_default as defaults


class DefinitionExportTests(unittest.TestCase):
    setUp = defaults.ExportDefaultTests.setUp
    invoke = defaults.ExportDefaultTests.invoke
    fragment = defaults.ExportDefaultTests.fragment

    def manifest(self):
        data = dict(schema='iw7.registered-player-definition-pair/1', donor='cp_zmb',
            native_source_pin='fab935826c898806855376662a8a03317b3ad8f1', weapon='iw7_shredder_zm', pap_attachment='shredderpap1',
            observed=dict(base_type=1,pap_type=0,pap_flag_raw=1,pap_flag=True,occurrences=1),
            readset=dict(bytes=100000,elements=1000,script_calls=0,copied_text_bytes=100,json_estimate=500000,allocation_estimate=2000000,
                         native_string_matrices=[],flat_empty_string_arrays=2),
            source_layout_only=True,templates_exported=True,full_definitions_observed=True)
        for key in ('projectile_author_eligible','dependency_bodies_captured','runtime_abi_verified','lifetime_verified',
                    'roundtrip_verified','weapon_granted','projectile_damage_verified','physics_qualified',
                    'retail_pap_transaction_verified','gameplay_accepted'):
            data[key]=False
        data['files']=[dict(path=path,bytes=1,sha256='a'*64) for path in
            ('weapons/iw7_shredder_zm.json','attachments/shredderpap1.json')]
        return data

    def definitions(self):
        return dict(szInternalName='iw7_shredder_zm',weapDef=dict(weapType=1,unk0={},
            turretBarrelSpinUpSnd=['']*4,turretBarrelSpinDownSnd=['']*4)), dict(szInternalName='shredderpap1',weaponType=0,papAttachment=True)

    def test_default_selector_is_exact_exclusive_and_has_no_native_effect(self):
        original=json.loads(json.dumps(self.plan))
        self.plan.update(PairDefinitions=True,Pack='paris_enemy_cp_zmb_raygun_pair_definitions_a')
        result=self.invoke();self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse(any(json.loads(result.stdout)[key] for key in
            ('NativeTypesLoaded','OpaqueInputsRead','LeaseAcquired','RuntimeCreated','CandidateExecuted','Ready')))
        good=json.loads(json.dumps(self.plan))
        for value in (False,1,'true',[True],None):
            self.plan=dict(good,PairDefinitions=value);self.assertNotEqual(self.invoke().returncode,0)
        self.plan=dict(good,PairProfile=True);self.assertNotEqual(self.invoke().returncode,0)
        self.plan=dict(original,PairDefinitions=True);self.assertNotEqual(self.invoke().returncode,0)
        self.assertFalse(Path(original['RunRoot']).exists())

    def test_actual_manifest_reader_closed_scalar_budget_and_file_refusals(self):
        valid=self.manifest();cases=[dict(text=json.dumps(valid),refused=False)]
        mutations=[lambda d:d.update(extra=False),lambda d:d.update(schema='iw7.player-pair-profile/1'),
            lambda d:d.update(full_definitions_observed=False),lambda d:d.update(runtime_abi_verified=True),
            lambda d:d.update(projectile_author_eligible=True),lambda d:d.update(physics_qualified=0),
            lambda d:d['observed'].update(base_type=3),lambda d:d['observed'].update(pap_type=3),
            lambda d:d['observed'].update(pap_flag_raw=255),lambda d:d['observed'].update(pap_flag=1),
            lambda d:d['observed'].update(occurrences=2),lambda d:d['readset'].update(bytes=1048577),
            lambda d:d['readset'].update(elements=8193),lambda d:d['readset'].update(script_calls=2049),
            lambda d:d['readset'].update(copied_text_bytes=100001),lambda d:d['readset'].update(json_estimate=2097153),
            lambda d:d['readset'].update(allocation_estimate=16777217),
            lambda d:d['readset'].update(native_string_matrices=['bad']),
            lambda d:d['readset'].update(native_string_matrices=['WeaponDef.turretBarrelSpinUpSnd']*2,flat_empty_string_arrays=0),
            lambda d:d['readset'].update(flat_empty_string_arrays=1),lambda d:d['files'][0].update(path='../weapon.json'),
            lambda d:d['files'][0].update(bytes=0),lambda d:d['files'][0].update(bytes=2097153),
            lambda d:d['files'][0].update(bytes=1.0),lambda d:d['files'][0].update(sha256='A'*64),
            lambda d:d['files'][1].update(path=d['files'][0]['path']),lambda d:d['files'][0].update(extra=0)]
        for mutate in mutations:
            data=json.loads(json.dumps(valid));mutate(data);cases.append(dict(text=json.dumps(data),refused=True))
        cases.append(dict(text=json.dumps(valid).replace('"base_type": 1','"base_type":1,"base_type":1'),refused=True))
        cases.append(dict(text=json.dumps(valid)+' '*16385,refused=True))
        (self.root/'cases.json').write_text(json.dumps(cases),encoding='utf-8')
        result=self.fragment('Convert-PlayerDefinitionJson',"""
$cases=Get-Content (Join-Path $Directory 'cases.json') -Raw|ConvertFrom-Json -Depth 40
foreach($case in $cases){$refused=$false;try{$null=Convert-PlayerDefinitionJson $case.text 'manifest'}catch{$refused=$true}
 if($refused -ne $case.refused){throw 'Actual neutral manifest refusal mismatch'}}
""")
        self.assertEqual(result.returncode,0,result.stderr)

    def test_actual_native_reader_preserves_1_0_and_native_array_shapes(self):
        manifest=self.manifest();weapon,pap=self.definitions();cases=[]
        def case(data,kind,refused,meta=None):
            cases.append(dict(text=json.dumps(data),kind=kind,refused=refused,manifest=meta or manifest))
        case(weapon,'iw7_shredder_zm',False);case(pap,'shredderpap1',False)
        matrix=json.loads(json.dumps(weapon));matrix['weapDef']['turretBarrelSpinUpSnd']=[['']*4 for _ in range(4)]
        matrix_meta=json.loads(json.dumps(manifest));matrix_meta['readset'].update(native_string_matrices=['WeaponDef.turretBarrelSpinUpSnd'],flat_empty_string_arrays=1)
        case(matrix,'iw7_shredder_zm',False,matrix_meta)
        for mutate in (lambda d:d.update(szInternalName=['iw7_shredder_zm']),lambda d:d['weapDef'].update(weapType=3),
                       lambda d:d['weapDef'].update(weapType=1.0),lambda d:d['weapDef'].pop('unk0'),
                       lambda d:d['weapDef'].update(turretBarrelSpinUpSnd=[None]*4),
                       lambda d:d['weapDef'].update(turretBarrelSpinUpSnd=[['']*4]*4)):
            data=json.loads(json.dumps(weapon));mutate(data);case(data,'iw7_shredder_zm',True)
        for mutate in (lambda d:d.update(weaponType=3),lambda d:d.update(weaponType=False),lambda d:d.update(papAttachment=1)):
            data=json.loads(json.dumps(pap));mutate(data);case(data,'shredderpap1',True)
        data=json.loads(json.dumps(matrix));data['weapDef']['turretBarrelSpinUpSnd'][3][2]='different';case(data,'iw7_shredder_zm',True,matrix_meta)
        data=json.loads(json.dumps(matrix));data['weapDef']['turretBarrelSpinUpSnd'][0][0]=None;case(data,'iw7_shredder_zm',True,matrix_meta)
        (self.root/'cases.json').write_text(json.dumps(cases),encoding='utf-8')
        result=self.fragment('Convert-PlayerDefinitionJson',"""
$cases=Get-Content (Join-Path $Directory 'cases.json') -Raw|ConvertFrom-Json -Depth 40
foreach($case in $cases){$refused=$false;try{$null=Convert-PlayerDefinitionJson $case.text $case.kind $case.manifest}catch{$refused=$true}
 if($refused -ne $case.refused){throw 'Actual neutral native JSON refusal mismatch'}}
""")
        self.assertEqual(result.returncode,0,result.stderr)

    def test_actual_readback_path_requires_both_hashes_then_stock_before_completion(self):
        # Execute the actual final statements of the runner's main try body.
        # Source-only stock confirmation is injected; native startup/admission
        # statements before the output-readback boundary are never executed.
        weapon,pap=self.definitions();manifest=self.manifest()
        output=self.root/'work'/'dump'/'paris_enemy_cp_zmb_raygun_pair_definitions_a'
        for name,data in (('weapons/iw7_shredder_zm.json',weapon),('attachments/shredderpap1.json',pap)):
            path=output/name;path.parent.mkdir(parents=True,exist_ok=True);raw=(json.dumps(data)+'\n').encode();path.write_bytes(raw)
            row=next(row for row in manifest['files'] if row['path']==name);row.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        (output/'player-definition-pair-manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
        result=self.fragment(['Read-PlayerOutput','Convert-PlayerDefinitionJson','Confirm-PlayerDefinitionBindings'],r'''
$main=@($a.EndBlock.Statements|Where-Object {$_ -is [Management.Automation.Language.TryStatementAst]})[-1]
$statements=@($main.Body.Statements);$start=-1
for($i=0;$i -lt $statements.Count;$i++){if($statements[$i].Extent.Text.StartsWith('$output=Join-Path $plan.WorkRoot')){$start=$i;break}}
if($start -lt 0){throw 'Actual readback boundary absent'}
$readback=[scriptblock]::Create(($statements[$start..($statements.Count-1)]|ForEach-Object {$_.Extent.Text}) -join "`n")
$plan=@{WorkRoot=(Join-Path $Directory 'work');Pack='paris_enemy_cp_zmb_raygun_pair_definitions_a'}
$pairDefinitions=$true;$pairProfile=$false;$script:stockCalls=0;$script:stockFails=$false
function Confirm-PlayerStock {$script:stockCalls++;if($script:stockFails){throw 'Owned Source stock failure'}}
foreach($scenario in 'valid','bad-hash','missing-pap','stock-fails'){
 $state=[ordered]@{NativeExportComplete=$false;NeutralCaptureComplete=$false;FullDefinitionsObserved=$false;NeutralManifest=$null}
 $script:stockCalls=0;$script:stockFails=$scenario -ceq 'stock-fails'
 $papPath=Join-Path $plan.WorkRoot ('dump/'+$plan.Pack+'/attachments/shredderpap1.json')
 $original=[IO.File]::ReadAllText($papPath)
 if($scenario -ceq 'bad-hash'){[IO.File]::WriteAllText($papPath,$original+' ')}
 if($scenario -ceq 'missing-pap'){[IO.File]::Move($papPath,$papPath+'.held')}
 $refused=$false;try{. $readback}catch{$refused=$true}
 if($scenario -ceq 'valid'){
  if($refused -or !$state.NeutralCaptureComplete -or !$state.FullDefinitionsObserved -or $state.NativeExportComplete -or $script:stockCalls -ne 1){throw 'Actual neutral completion failed'}
 }elseif(!$refused -or $state.NeutralCaptureComplete -or $state.FullDefinitionsObserved -or $state.NativeExportComplete -or
  $script:stockCalls -ne $(if($scenario -ceq 'stock-fails'){1}else{0})){throw 'Actual neutral failure promoted completion'}
 foreach($guard in $guards){$guard.Dispose()};$guards.Clear()
 if($scenario -ceq 'missing-pap'){[IO.File]::Move($papPath+'.held',$papPath)}
 if($scenario -ceq 'bad-hash'){[IO.File]::WriteAllText($papPath,$original)}
}
''')
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__':
    unittest.main()

"""Finite export Source preflight/refusal and bounded-reader/budget causals."""
import hashlib,json,shutil,subprocess,tempfile,unittest
from pathlib import Path
RUNNER=Path(__file__).with_name('Run-PlayerTemplateExport.ps1').resolve()
def pin(path):return dict(Path=str(path),Bytes=path.stat().st_size,SHA256=hashlib.sha256(path.read_bytes()).hexdigest())
class ExportDefaultTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  provider=self.root/'H1Native.Core.ps1';provider.write_bytes(b'# must not import\n')
  csv=self.root/'requested.csv';csv.write_bytes(b'weapon,iw7_shredder_zm\nattachment,shredderpap1\n')
  self.plan=dict(Schema='iw7.player-template-export-source/1',Ready=False,CandidateExecuted=False,StockContentQualified=False,
   RetailAliasCount=70,UniqueRetailSources=39,GroupSeconds=600,ToolSeconds=240,GeneratedLimitBytes=16777216,MetadataReserveBytes=1048576,
   RunnerBinding=pin(RUNNER),SourceBindings=[dict(**pin(provider),Role='Provider')],Request=pin(csv),Pack='paris_enemy_cp_zmb_raygun_template_a_player_weapon_source',
   Providers={k:str(provider) for k in ('Core','Scheduler','Profile','StockCore','BeaconCore','ArenaProcess')},RunRoot=str(self.root/'absent'),StockManifests=[])
  for name,count in (('root',7),('main',31),('zone',32)):
   path=self.root/(name+'.json');path.write_bytes(b'{}\n');self.plan['StockManifests'].append(dict(**pin(path),Name=name,Count=count))
 def invoke(self,run=False):
  path=self.root/'plan.json';raw=(json.dumps(self.plan)+'\n').encode();path.write_bytes(raw)
  args=[shutil.which('pwsh'),'-NoLogo','-NoProfile','-File',str(RUNNER),'-PlanPath',str(path),'-PlanSHA256',hashlib.sha256(raw).hexdigest()]
  return subprocess.run(args+(['-Run'] if run else []),capture_output=True,text=True,timeout=15)
 def test_pure_default(self):
  result=self.invoke();self.assertEqual(result.returncode,0,result.stderr);value=json.loads(result.stdout)
  self.assertFalse(any(value[k] for k in ('NativeTypesLoaded','OpaqueInputsRead','LeaseAcquired','RuntimeCreated','CandidateExecuted','Ready')))
  self.assertFalse(Path(self.plan['RunRoot']).exists())
 def test_ready_refused(self):
  self.plan['Ready']=True;self.assertNotEqual(self.invoke().returncode,0)
 def test_missing_provider_pin_refused(self):
  self.plan['Providers']['StockCore']=str(self.root/'unbound.ps1');r=self.invoke();self.assertNotEqual(r.returncode,0);self.assertIn('provider Source binding',r.stderr)
 def test_single_layout_drift_refused(self):
  self.plan['StockManifests'][2]['Count']=31;r=self.invoke();self.assertNotEqual(r.returncode,0);self.assertIn('pair/layout',r.stderr)
 def test_native_file_entry_refused_before_effects(self):
  r=self.invoke(True);self.assertNotEqual(r.returncode,0);self.assertIn('NoExit/dot',r.stderr);self.assertFalse(Path(self.plan['RunRoot']).exists())
 def test_request_drift_refused(self):
  Path(self.plan['Request']['Path']).write_bytes(b'weapon,other\n');self.assertNotEqual(self.invoke().returncode,0)
 def fragment(self,name,body):
  path=self.root/'fragment.ps1';path.write_text('''param($Runner,$Directory)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$t=$null;$e=$null;$a=[Management.Automation.Language.Parser]::ParseFile($Runner,[ref]$t,[ref]$e)
function Assert-PlayerExportClock {}
function Assert-H1Path($Path){if((Get-Item -LiteralPath $Path).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Redirect'}}
$guards=[Collections.Generic.List[object]]::new()
$script:PlayerTemplateExportOriginalRoot=@{Context=[pscustomobject]@{Guards=$guards}}
'''+''.join(f"$f=$a.Find({{param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq '{n}'}},$true)\n. ([scriptblock]::Create($f.Extent.Text))\n" for n in ([name] if isinstance(name,str) else name))+body,encoding='utf-8')
  return subprocess.run([shutil.which('pwsh'),'-NoLogo','-NoProfile','-File',str(path),str(RUNNER),str(self.root)],capture_output=True,text=True,timeout=15)
 def test_actual_output_reader_caps_before_hash_and_keeps_guard(self):
  r=self.fragment('Read-PlayerOutput','''
$path=Join-Path $Directory 'out.json';[IO.File]::WriteAllText($path,'{}')
$value=Read-PlayerOutput $path 16
$blocked=$false;try{$w=[IO.File]::Open($path,'Open','Write','None');$w.Dispose()}catch{$blocked=$true}
if(!$blocked -or $value.Bytes -ne 2 -or $guards.Count -ne 1){throw 'Bounded output guard failed'}
foreach($guard in $guards){$guard.Dispose()};$guards.Clear()
[IO.File]::WriteAllText($path,'x'*17)
$refused=$false;try{$null=Read-PlayerOutput $path 16}catch{$refused=$true}
if(!$refused){throw 'Oversized output accepted'}
Write-Output 'bounded-output-pass'
''');self.assertEqual(r.returncode,0,r.stderr);self.assertIn('bounded-output-pass',r.stdout)
 def test_actual_budget_counts_small_copies_and_refuses_alias_identity_drift(self):
  r=self.fragment('Test-PlayerGenerated','''
$work=Join-Path $Directory 'work';[IO.Directory]::CreateDirectory($work)|Out-Null
$alias=Join-Path $work 'retail.ff';[IO.File]::WriteAllBytes($alias,[byte[]]::new(1000))
$tool=Join-Path $work 'zonetool-iw7-player.exe';[IO.File]::WriteAllBytes($tool,[byte[]]::new(1000))
[IO.File]::WriteAllBytes((Join-Path $work 'tlsdll.dll'),[byte[]]::new(10))
$plan=[pscustomobject]@{RunRoot=$Directory;WorkRoot=$work;GeneratedLimitBytes=100}
$state=[ordered]@{Inputs=@([pscustomobject]@{Target=$alias;SourceId='same';TargetId='same'});CreatedCopies=@()}
# Ignore the enclosing Source fragment itself by defining only work as run root.
$plan.RunRoot=$work
$script:PlayerTemplateExportOriginalRoot.Plan=$plan;$script:PlayerTemplateExportOriginalRoot.State=$state
Test-PlayerGenerated $state
if($state.GeneratedObservedBytes -ne 10){throw 'Small copy excluded from output accounting'}
$state.Inputs[0].TargetId='different';$refused=$false
try{Test-PlayerGenerated $state}catch{$refused=$true}
if(!$refused){throw 'Unproven alias exemption accepted'}
Write-Output 'budget-causal-pass'
''');self.assertEqual(r.returncode,0,r.stderr);self.assertIn('budget-causal-pass',r.stdout)
 def test_native_manifest_scalar_and_closed_shape_mutants(self):
  manifest=dict(schema='iw7.player-weapon-templates/1',donor='cp_zmb',native_source_pin='fab935826c898806855376662a8a03317b3ad8f1',weapon='iw7_shredder_zm',pap_attachment='shredderpap1',engine_weapon_type='projectile',
   bo3_assets_authenticated=False,weapon_granted=False,projectile_damage_verified=False,retail_pap_transaction_verified=False,gameplay_accepted=False,
   files=[dict(path='weapons/iw7_shredder_zm.json',bytes=2,sha256='a'*64),dict(path='attachments/shredderpap1.json',bytes=2,sha256='b'*64)])
  cases=[('valid',json.dumps(manifest),False)]
  for name in ('schema','donor','weapon','pap_attachment','native_source_pin','engine_weapon_type'):
   changed=json.loads(json.dumps(manifest));changed[name]=[changed[name]];cases.append((name,json.dumps(changed),True))
  changed=json.loads(json.dumps(manifest));changed['files'][0]['bytes']='2';cases.append(('bytes-string',json.dumps(changed),True))
  for value in (None,'hitscan'):
   changed=json.loads(json.dumps(manifest))
   if value is None:del changed['engine_weapon_type']
   else:changed['engine_weapon_type']=value
   cases.append(('weapon-type',json.dumps(changed),True))
  cases.append(('duplicate',json.dumps(manifest).replace('"donor": "cp_zmb"','"donor":"cp_zmb","donor":"cp_zmb"'),True))
  for label,text,refused in cases:
   with self.subTest(label=label):
    path=self.root/'data.json';path.write_text(text,encoding='utf-8')
    r=self.fragment('Convert-PlayerNativeJson',f"$refused=$false;try{{$null=Convert-PlayerNativeJson ([IO.File]::ReadAllText((Join-Path $Directory 'data.json'))) 'manifest'}}catch{{$refused=$true}};if($refused -ne ${str(refused).lower()}){{throw 'Shape causal mismatch'}}")
    self.assertEqual(r.returncode,0,r.stderr)
 def test_weapon_internal_name_array_refused(self):
  path=self.root/'data.json';path.write_text('{"szInternalName":["iw7_shredder_zm"]}',encoding='utf-8')
  r=self.fragment('Convert-PlayerNativeJson',"$refused=$false;try{$null=Convert-PlayerNativeJson ([IO.File]::ReadAllText((Join-Path $Directory 'data.json'))) 'iw7_shredder_zm'}catch{$refused=$true};if(!$refused){throw 'Array name accepted'}")
  self.assertEqual(r.returncode,0,r.stderr)
 def test_source_roles_reject_opaque_ads_and_device_before_any_open(self):
  r=self.fragment('Read-PlayerExportSource','''
foreach($path in @((Join-Path $Directory 'absent.exe'),(Join-Path $Directory 'absent.obj'),(Join-Path $Directory 'absent.tlog'),
 (Join-Path $Directory 'known.json:stream'),'\\\\.\\NUL',(Join-Path $Directory 'NUL.json'))){
 $refused=$false
 try{$null=Read-PlayerExportSource $path ('0'*64) 0 -Role Metadata}catch{
  if($_.Exception.Message -notmatch 'before open'){throw};$refused=$true
 }
 if(!$refused){throw 'Opaque/device path accepted'}
}
Write-Output 'before-open-role-pass'
''');self.assertEqual(r.returncode,0,r.stderr);self.assertIn('before-open-role-pass',r.stdout)
 def test_creation_precision_positive_and_different_microsecond_negative(self):
  r=self.fragment('Test-PlayerHostCreation','''
$kernel=[datetime]::Parse('2026-10-14T23:40:12.2195679Z').ToUniversalTime()
$cim=[datetime]::Parse('2026-10-14T23:40:12.2195670Z').ToUniversalTime()
$different=[datetime]::Parse('2026-10-14T23:40:12.2195680Z').ToUniversalTime()
if(!(Test-PlayerHostCreation $cim $kernel)){throw 'Valid truncated CIM creation refused'}
if(Test-PlayerHostCreation $different $kernel){throw 'Different creation accepted'}
if($kernel.ToString('o') -cne '2026-10-14T23:40:12.2195679Z'){throw 'Kernel identity precision lost'}
Write-Output 'precision-causal-pass'
''');self.assertEqual(r.returncode,0,r.stderr);self.assertIn('precision-causal-pass',r.stdout)
 def test_callbacks_resist_dynamic_context_plan_and_state_shadow(self):
  r=self.fragment(('Assert-PlayerExportClock','Assert-PlayerExportCaller'),'''
$script:T7GroupStarted='original-clock'
function Assert-H1Deadline($Started,$Seconds){if($Started -cne 'original-clock' -or $Seconds -ne 600){throw 'Wrong retained clock'}}
$script:PlayerTemplateExportOriginalRoot=@{Key='iw7.source-causal';Context=[pscustomobject]@{Lease=[pscustomobject]@{Token='source-only'}};Plan=[pscustomobject]@{GroupSeconds=600};State=@{Host=@{PID=$PID}}}
[AppDomain]::CurrentDomain.SetData('iw7.source-causal',$script:PlayerTemplateExportOriginalRoot)
function Invoke-DynamicShadow {
 $Context=@{LeaseToken='stock';Plan=@{TargetRoot='unused'}};$plan=$Context.Plan;$state=@{Host=@{PID=-1}};$root=@{}
 Assert-PlayerExportCaller 'source-only' 'unused'
}
Invoke-DynamicShadow
$refused=$false;try{Assert-PlayerExportCaller 'wrong' 'unused'}catch{$refused=$true}
if(!$refused){throw 'Wrong actual lease token accepted'}
[AppDomain]::CurrentDomain.SetData('iw7.source-causal',@{})
$refused=$false;try{Invoke-DynamicShadow}catch{$refused=$true}
if(!$refused){throw 'Different AppDomain root accepted'}
Write-Output 'scope-causal-pass'
''');self.assertEqual(r.returncode,0,r.stderr);self.assertIn('scope-causal-pass',r.stdout)
 def test_after_apply_uses_original_content_handle_and_refuses_closed_or_wrong_identity(self):
  r=self.fragment('Get-PlayerSourceHandle','''
$path=Join-Path $Directory 'held.json';[IO.File]::WriteAllText($path,'{}')
$content=[IO.FileStream]::new($path,'Open','Read','Read')
$stock=[IO.FileStream]::new($path,'Open','Read','Read');$stockHandle=$stock.SafeFileHandle;$stock.Dispose()
$source=[pscustomobject]@{Path=$path;Before=[pscustomobject]@{Identity='same'};Guard=$stockHandle}
$script:PlayerTemplateExportOriginalRoot.ContentGuards=@{};$script:PlayerTemplateExportOriginalRoot.ContentGuards[$path]=[pscustomobject]@{Identity='same';Stream=$content}
if(![object]::ReferenceEquals((Get-PlayerSourceHandle $source),$content.SafeFileHandle)){throw 'Original content handle changed'}
$source.Before.Identity='different';$refused=$false;try{$null=Get-PlayerSourceHandle $source}catch{$refused=$true}
if(!$refused){throw 'Wrong content identity accepted'}
$source.Before.Identity='same';$content.Dispose();$refused=$false;try{$null=Get-PlayerSourceHandle $source}catch{$refused=$true}
if(!$refused){throw 'Closed content handle accepted'}
Write-Output 'after-apply-guard-pass'
''');self.assertEqual(r.returncode,0,r.stderr);self.assertIn('after-apply-guard-pass',r.stdout)
if __name__=='__main__':unittest.main()

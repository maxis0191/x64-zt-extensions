"""Finite export Source preflight/refusal and bounded-reader/budget causals."""
import ast,hashlib,json,re,shutil,subprocess,tempfile,unittest
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
 def test_pair_profile_default_is_pure_and_selector_is_exact(self):
  original=json.loads(json.dumps(self.plan))
  self.plan.update(PairProfile=True,Pack='paris_enemy_cp_zmb_raygun_pair_profile_a')
  r=self.invoke();self.assertEqual(r.returncode,0,r.stderr)
  self.assertFalse(any(json.loads(r.stdout)[k] for k in ('NativeTypesLoaded','OpaqueInputsRead','LeaseAcquired','RuntimeCreated','CandidateExecuted','Ready')))
  for value in (False,1,'true',[True],None):
   self.plan=dict(original,PairProfile=value,Pack='paris_enemy_cp_zmb_raygun_pair_profile_a')
   self.assertNotEqual(self.invoke().returncode,0)
  self.plan=dict(original,PairProfile=True)
  self.assertNotEqual(self.invoke().returncode,0)
  self.assertFalse(Path(original['RunRoot']).exists())

 def pair_profile(self):
  return dict(schema='iw7.player-pair-profile/1',donor='cp_zmb',native_source_pin='fab935826c898806855376662a8a03317b3ad8f1',
   weapon='iw7_shredder_zm',pap_attachment='shredderpap1',source_offsets=dict(base_type=556,pap_type=28,pap_flag=20),
   observed=dict(base_type=1,pap_type=3,pap_flag_raw=1,pap_flag=True),
   association=dict(status='bounded',counts=[0,1,0,0,0,0],readable=[True]*6,occurrences=1),source_layout_only=True,
   templates_exported=False,projectile_author_eligible=False,runtime_abi_verified=False,weapon_granted=False,
   projectile_damage_verified=False,physics_qualified=False,retail_pap_transaction_verified=False,gameplay_accepted=False)

 def test_actual_pair_profile_reader_closed_typed_positive_and_partial_cases(self):
  valid=self.pair_profile();cases=[('mixed-numbers-preserved',valid,False)]
  partial=json.loads(json.dumps(valid));partial['association'].update(status='refused_bounds_or_readability',counts=[65,0,0,0,0,0],readable=[False,True,True,True,True,True],occurrences=None)
  cases.append(('bounds-partial',partial,False))
  partial=json.loads(json.dumps(valid));partial['observed'].update(pap_flag_raw=255,pap_flag=None);cases.append(('raw-bool-anomaly',partial,False))
  partial=json.loads(json.dumps(valid));partial['association'].update(status='refused_bounds_or_readability',readable=[True,False,True,True,True,True],occurrences=None);cases.append(('unreadable-partial',partial,False))
  changes=[lambda d:d.update(extra=False),lambda d:d.update(schema=['iw7.player-pair-profile/1']),
   lambda d:d.update(projectile_author_eligible=True),lambda d:d.update(physics_qualified=0),
   lambda d:d['observed'].update(base_type='1'),lambda d:d['observed'].update(pap_type=1.0),
   lambda d:d['observed'].update(pap_flag=False),lambda d:d['observed'].update(pap_flag_raw=256),
   lambda d:d['observed'].update(base_type=2147483648),lambda d:d['source_offsets'].update(base_type=557),
   lambda d:d['association'].update(counts=[0]*5),lambda d:d['association'].update(occurrences=2),
   lambda d:d['association'].update(readable=[0]*6),lambda d:d['association'].update(occurrences=None),
   lambda d:d['association'].update(status='refused_bounds_or_readability'),
   lambda d:d['association'].update(readable=[False,True,True,True,True,True]),
   lambda d:d['association'].update(counts=[65,0,0,0,0,0],status='refused_bounds_or_readability',occurrences=None)]
  for i,mutate in enumerate(changes):
   d=json.loads(json.dumps(valid));mutate(d);cases.append((str(i),d,True))
  for label,data,refused in cases:
   with self.subTest(label=label):
    (self.root/'data.json').write_text(json.dumps(data),encoding='utf-8')
    r=self.fragment('Convert-PlayerPairProfileJson',f"$refused=$false;try{{$value=Convert-PlayerPairProfileJson ([IO.File]::ReadAllText((Join-Path $Directory 'data.json')))}}catch{{$refused=$true}};if($refused -ne ${str(refused).lower()}){{throw 'Profile shape causal mismatch'}}")
    self.assertEqual(r.returncode,0,r.stderr)
  raw=json.dumps(valid).replace('"base_type": 1,','"base_type":1,"base_type":1,')
  (self.root/'data.json').write_text(raw,encoding='utf-8')
  r=self.fragment('Convert-PlayerPairProfileJson',"$refused=$false;try{$null=Convert-PlayerPairProfileJson ([IO.File]::ReadAllText((Join-Path $Directory 'data.json')))}catch{$refused=$true};if(!$refused){throw 'Duplicate observed key accepted'}")
  self.assertEqual(r.returncode,0,r.stderr)
 def test_missing_provider_pin_refused(self):
  self.plan['Providers']['StockCore']=str(self.root/'unbound.ps1');r=self.invoke();self.assertNotEqual(r.returncode,0);self.assertIn('provider Source binding',r.stderr)
 def test_single_layout_drift_refused(self):
  self.plan['StockManifests'][2]['Count']=31;r=self.invoke();self.assertNotEqual(r.returncode,0);self.assertIn('pair/layout',r.stderr)
 def test_native_file_entry_refused_before_effects(self):
  r=self.invoke(True);self.assertNotEqual(r.returncode,0);self.assertIn('NoExit/dot',r.stderr);self.assertFalse(Path(self.plan['RunRoot']).exists())
 def test_request_drift_refused(self):
  Path(self.plan['Request']['Path']).write_bytes(b'weapon,other\n');self.assertNotEqual(self.invoke().returncode,0)
 def coverage_plan(self):
  world=RUNNER.parent.parent/'world'/'original-arena'/'AssetfileCoverage.Core.ps1'
  numbers=[int(n) for n in re.search(r'\$numbers=@\(([^)]+)\)',world.read_text(encoding='utf-8-sig')).group(1).split(',')]
  self.plan.update(RetailProfile='fixed33-pak',RetailAliasCount=102,UniqueRetailSources=71,
   WorkRoot=str(Path(self.plan['RunRoot'])/'work'),StockSourceRoot=str(self.root/'unopened-stock'),
   SourceBaselines=[dict(Identity='historical-'+str(i),Links=1) for i in range(71)])
  for pin_row in self.plan['StockManifests']:
   group=pin_row['Name'];names=([f'root{i}.bin' for i in range(7)] if group=='root' else [f'common{i}.ff' for i in range(31)])
   if group=='zone':names += [f'assetfile{n}.pak' for n in numbers]
   target=Path(self.plan['WorkRoot'])/group if group!='root' else Path(self.plan['WorkRoot'])
   value=dict(source=self.plan['StockSourceRoot'],target=str(target),planned_files=len(names),files=[dict(relative=n,bytes=1) for n in names])
   path=Path(pin_row['Path']);path.write_text(json.dumps(value),encoding='utf-8')
   pin_row.update(pin(path),Target=str(target),Count=len(names))
 def mutate_manifest(self,group,change):
  entry=next(p for p in self.plan['StockManifests'] if p['Name']==group);path=Path(entry['Path'])
  value=json.loads(path.read_text());change(value);path.write_text(json.dumps(value),encoding='utf-8');entry.update(pin(path))
 def test_fixed33_world_namespace_default_is_pure_and_explicit(self):
  self.coverage_plan();r=self.invoke();self.assertEqual(r.returncode,0,r.stderr);value=json.loads(r.stdout)
  self.assertEqual((value['RetailAliases'],value['UniqueRetailSources']),(102,71))
  self.assertFalse(any(value[k] for k in ('NativeTypesLoaded','OpaqueInputsRead','LeaseAcquired','RuntimeCreated','CandidateExecuted','Ready')))
  self.assertFalse(Path(self.plan['RunRoot']).exists());self.assertFalse(Path(self.plan['StockSourceRoot']).exists())
  del self.plan['RetailProfile'];self.assertNotEqual(self.invoke().returncode,0)
 def test_fixed33_refuses_profile_count_baseline_and_path_mutants_before_effects(self):
  for key,value in [('RetailProfile',['fixed33-pak']),('RetailProfile','all-paks'),('RetailAliasCount',70),('RetailAliasCount','102'),('UniqueRetailSources',39),('UniqueRetailSources',[71]),('SourceBaselines',[])]:
   with self.subTest(key=key):
    self.coverage_plan();self.plan[key]=value;r=self.invoke();self.assertNotEqual(r.returncode,0);self.assertFalse(Path(self.plan['RunRoot']).exists())
  self.coverage_plan();self.plan['SourceBaselines'][1]['Identity']=self.plan['SourceBaselines'][0]['Identity'];self.assertNotEqual(self.invoke().returncode,0)
  self.coverage_plan();self.plan['StockSourceRoot']=[self.plan['StockSourceRoot']];self.assertNotEqual(self.invoke().returncode,0)
 def test_fixed33_refuses_extra_missing_duplicate_external_and_oversize_manifest_rows(self):
  cases=[lambda m:m['files'][-1].update(relative='assetfile999.pak'),
   lambda m:m['files'][-1].update(relative=m['files'][-2]['relative']),
   lambda m:m['files'][-1].update(relative='../assetfile244.pak'),
   lambda m:m['files'][-1].update(relative=['assetfile244.pak']),
   lambda m:m['files'][-1].update(bytes=1073741825),
   lambda m:m['files'][-1].update(bytes=1.0),
   lambda m:m['files'][0].update(bytes=268435457),
   lambda m:m.update(source=[m['source']]),lambda m:m.update(target=m['target']+'-foreign'),
   lambda m:m.update(planned_files=[64]),lambda m:m['files'].pop()]
  for i,change in enumerate(cases):
   with self.subTest(case=i):
    self.coverage_plan();self.mutate_manifest('zone',change);r=self.invoke();self.assertNotEqual(r.returncode,0);self.assertFalse(Path(self.plan['RunRoot']).exists())
  self.coverage_plan();self.mutate_manifest('main',lambda m:m['files'][-1].update(relative='assetfile244.pak'))
  self.assertNotEqual(self.invoke().returncode,0)
 def modal_plan(self):
  closure={'H1Compiler':'tools-source/asset-bridge/h1-fixture/H1Native.Compiler.ps1','LoadDiagnostic':'tools-source/asset-bridge/world/original-arena/LoadDiagnostic.Core.ps1',
   'Modal':'tools-source/asset-bridge/world/original-arena/modal_window.py','Recipient':'tools-source/asset-bridge/recipient/recipient_dialog.py','Capture':'ops/iw7_capture.py','Debugger':'ops/iw7_debugger.py'}
  for name,relative in closure.items():
   path=self.root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'# Source-only must not import\n')
   self.plan['SourceBindings'].append(dict(**pin(path),Role='Provider'))
   if name in ('H1Compiler','LoadDiagnostic'):self.plan['Providers'][name]=str(path)
  self.plan['ToolSeconds']=120
  self.plan['ModalDiagnostic']=dict(Mode='global-mp-modal-only',HelperSeconds=10,WindowRecordBytes=65536,
   ModalSource=str(self.root/closure['Modal']),RunRoot=str(self.root/'runtime'/'player-template-modal'),
   Python=dict(Path=str(self.root/'absent'/'python.exe'),Bytes=1,SHA256='0'*64))
 def test_modal_default_remains_pure_with_declared_unopened_python(self):
  self.modal_plan();r=self.invoke();self.assertEqual(r.returncode,0,r.stderr);value=json.loads(r.stdout)
  self.assertFalse(any(value[k] for k in ('NativeTypesLoaded','OpaqueInputsRead','LeaseAcquired','RuntimeCreated','CandidateExecuted','Ready')))
  self.assertFalse(Path(self.plan['ModalDiagnostic']['Python']['Path']).exists())
 def test_modal_mixed_modes_limits_and_source_import_layout_refused(self):
  self.modal_plan();original=json.loads(json.dumps(self.plan))
  for key,value in [('Mode',['global-mp-modal-only']),('HelperSeconds','10'),('WindowRecordBytes',65537),('ModalSource',str(self.root/'wrong'/'modal_window.py')),('RunRoot',str(self.root/'external'))]:
   with self.subTest(key=key):
    self.plan=json.loads(json.dumps(original));self.plan['ModalDiagnostic'][key]=value;r=self.invoke();self.assertNotEqual(r.returncode,0);self.assertFalse(Path(self.plan['RunRoot']).exists())
  self.plan=json.loads(json.dumps(original));self.plan['Providers']['H1Compiler']=self.plan['Providers']['Core'];self.assertNotEqual(self.invoke().returncode,0)
  self.plan=json.loads(json.dumps(original));self.plan['SourceBindings']=[p for p in self.plan['SourceBindings'] if not p['Path'].endswith('iw7_capture.py')];self.assertNotEqual(self.invoke().returncode,0)
 def test_modal_owned_runtime_collision_refused_without_effects(self):
  self.modal_plan();owned=Path(self.plan['ModalDiagnostic']['RunRoot']);owned.mkdir(parents=True)
  r=self.invoke();self.assertNotEqual(r.returncode,0);self.assertIn('Fresh package-owned modal runtime',r.stderr)
  self.assertFalse(Path(self.plan['RunRoot']).exists());self.assertEqual(list(owned.iterdir()),[])
 def test_actual_dependency_output_validator_accepts_owned_runtime_and_refuses_external(self):
  debugger=RUNNER.parents[3]/'ops'/'iw7_debugger.py'
  if not debugger.is_file():self.skipTest('Actual dependency function exercised in the composed Source package')
  tree=ast.parse(debugger.read_text(encoding='utf-8-sig'))
  function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='local_output')
  namespace={'Path':Path,'REPO':self.root/'snapshot'}
  exec(compile(ast.Module(body=[function],type_ignores=[]),str(debugger),'exec'),namespace)
  local_output=namespace['local_output'];inside=self.root/'snapshot'/'runtime'/'player-template-modal'/'load-diagnostic'/'modal-window.json'
  self.assertEqual(local_output(inside),inside.absolute());self.assertTrue(inside.parent.is_dir());self.assertFalse(inside.exists())
  outside=self.root/'external'/'modal-window.json'
  with self.assertRaisesRegex(ValueError,'unredirected runtime'):local_output(outside)
  self.assertFalse(outside.parent.exists())
  inside.write_text('{}',encoding='utf-8')
  with self.assertRaisesRegex(ValueError,'overwrite evidence'):local_output(inside)
 def fragment(self,name,body):
  path=self.root/'fragment.ps1';path.write_text('''param($Runner,$Directory)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$t=$null;$e=$null;$a=[Management.Automation.Language.Parser]::ParseFile($Runner,[ref]$t,[ref]$e)
function Assert-PlayerExportClock {}
function Assert-H1Path($Path){if([IO.File]::GetAttributes($Path) -band [IO.FileAttributes]::ReparsePoint){throw 'Redirect'}}
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
 def test_fixed33_large_input_limit_is_only_for_named_main_paks(self):
  r=self.fragment(('Get-PlayerRetailProfile','Get-PlayerRetailByteLimit'),'''
$plan=[pscustomobject]@{RetailProfile='fixed33-pak';StockSourceRoot=$Directory}
if((Get-PlayerRetailByteLimit $plan (Join-Path $Directory 'assetfile21.pak')) -ne 1GB){throw 'Large named retail file refused by legacy cap'}
foreach($path in @((Join-Path $Directory 'assetfile999.pak'),(Join-Path $Directory 'zonetool.exe'),(Join-Path $Directory 'foreign/assetfile21.pak'))){
 if((Get-PlayerRetailByteLimit $plan $path) -ne 256MB){throw 'Unbound input inherited large retail limit'}
}
$legacy=[pscustomobject]@{}
if((Get-PlayerRetailByteLimit $legacy (Join-Path $Directory 'assetfile21.pak')) -ne 256MB){throw 'Legacy cap changed'}
Write-Output 'finite-large-retail-limit-pass'
''');self.assertEqual(r.returncode,0,r.stderr);self.assertIn('finite-large-retail-limit-pass',r.stdout)
 def test_fixed33_rehash_uses_original_stream_and_keeps_its_guard(self):
  r=self.fragment(('Get-PlayerRetailProfile','Get-PlayerRetailByteLimit','Get-PlayerRetailStreamSHA','Confirm-PlayerRetailContent'),'''
$path=Join-Path $Directory 'assetfile21.pak';$raw=[byte[]]@(1,2,3,4);[IO.File]::WriteAllBytes($path,$raw)
$stream=[IO.FileStream]::new($path,'Open','Read','Read');$guards.Add($stream)
$script:PlayerTemplateExportOriginalRoot.Plan=[pscustomobject]@{RetailProfile='fixed33-pak';StockSourceRoot=$Directory}
$script:PlayerTemplateExportOriginalRoot.ContentGuards=@{};$script:PlayerTemplateExportOriginalRoot.ContentGuards[$path]=[pscustomobject]@{Identity='source-only';Stream=$stream}
$pin=[pscustomobject]@{Path=$path;Bytes=4;SHA256=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant()}
Confirm-PlayerRetailContent $pin;Confirm-PlayerRetailContent $pin
if($guards.Count -ne 1 -or $stream.Position -ne 0 -or ![object]::ReferenceEquals($stream,$script:PlayerTemplateExportOriginalRoot.ContentGuards[$path].Stream)){throw 'Original retail stream was replaced or not rewound'}
$blocked=$false;try{$writer=[IO.File]::Open($path,'Open','Write','None');$writer.Dispose()}catch{$blocked=$true};if(!$blocked){throw 'Original retail content guard lost'}
$pin.SHA256='0'*64;$refused=$false;try{Confirm-PlayerRetailContent $pin}catch{$refused=$_.Exception.Message -ceq 'Original retail content hash differs.'};if(!$refused){throw 'Changed expected retail hash accepted'}
$refused=$false;try{$null=Get-PlayerRetailStreamSHA $stream 4 3}catch{$refused=$true};if(!$refused -or $stream.Position -ne 0){throw 'Declared read bound ignored'}
$stream.Dispose();$refused=$false;try{Confirm-PlayerRetailContent $pin}catch{$refused=$true};if(!$refused){throw 'Closed original stream accepted'}
$guards.Clear();Write-Output 'original-retail-stream-pass'
''');self.assertEqual(r.returncode,0,r.stderr);self.assertIn('original-retail-stream-pass',r.stdout)
 def test_fixed33_actual_stock_confirmation_routes_only_retail_to_retained_stream(self):
  r=self.fragment(('Get-PlayerRetailProfile','Get-PlayerRetailByteLimit','Get-PlayerRetailStreamSHA','Confirm-PlayerRetailContent','Pin-PlayerOpaque','Confirm-PlayerStock'),'''
$path=Join-Path $Directory 'assetfile21.pak';$raw=[byte[]]@(1,2,3,4);[IO.File]::WriteAllBytes($path,$raw)
$stream=[IO.FileStream]::new($path,'Open','Read','Read');$guards.Add($stream)
$content=[pscustomobject]@{Path=$path;Bytes=4;SHA256=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant()}
$code=[pscustomobject]@{Role='SourceOnlyCodePin'}
$root=$script:PlayerTemplateExportOriginalRoot;$root.Plan=[pscustomobject]@{RetailProfile='fixed33-pak';StockSourceRoot=$Directory;Candidate=$code;TLS=$code;Sentinel=$code}
$root.StockContexts=@();$root.State=@{ContentPins=@($content);CreatedCopies=@()};$root.ContentGuards=@{}
$root.ContentGuards[$path]=[pscustomobject]@{Identity='source-only';Stream=$stream};$script:codeCalls=0
function Open-T7Pin($Pin,$Context){
 if($Pin.Role -cne 'SourceOnlyCodePin' -or ![object]::ReferenceEquals($Context,$script:PlayerTemplateExportOriginalRoot.Context)){throw 'Retail was sent through the code-input pin API'}
 $script:codeCalls++
}
Confirm-PlayerStock
if($script:codeCalls -ne 3 -or $guards.Count -ne 1 -or $stream.Position -ne 0){throw 'Actual stock confirmation lost its retail/code split'}
$stream.Dispose();$guards.Clear();Write-Output 'actual-retail-confirmation-pass'
''');self.assertEqual(r.returncode,0,r.stderr);self.assertIn('actual-retail-confirmation-pass',r.stdout)
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
 def test_hidden_marker_is_counted_and_limit_still_refuses(self):
  r=self.fragment('Test-PlayerGenerated','''
$work=Join-Path $Directory 'hidden-work';[IO.Directory]::CreateDirectory($work)|Out-Null
$marker=Join-Path $work '__iw7_ship';[IO.File]::WriteAllBytes($marker,[byte[]]::new(4));[IO.File]::SetAttributes($marker,[IO.FileAttributes]34)
$script:PlayerTemplateExportOriginalRoot.Plan=[pscustomobject]@{RunRoot=$work;WorkRoot=$work;GeneratedLimitBytes=4}
$script:PlayerTemplateExportOriginalRoot.State=[ordered]@{Inputs=@()}
Test-PlayerGenerated $null
if($script:PlayerTemplateExportOriginalRoot.State.GeneratedObservedBytes -ne 4){throw 'Hidden marker escaped accounting'}
$refused=$false;try{Test-PlayerGenerated $null 3}catch{$refused=$true}
if(!$refused){throw 'Hidden output exceeds limit without refusal'}
Write-Output 'hidden-budget-pass'
''');self.assertEqual(r.returncode,0,r.stderr);self.assertIn('hidden-budget-pass',r.stdout)
 def test_separate_owned_modal_runtime_is_counted_in_same_finite_budget(self):
  r=self.fragment('Test-PlayerGenerated','''
$work=Join-Path $Directory 'native-run';$modal=Join-Path $Directory 'snapshot-runtime'
[IO.Directory]::CreateDirectory($work)|Out-Null;[IO.Directory]::CreateDirectory($modal)|Out-Null
[IO.File]::WriteAllBytes((Join-Path $work 'generated.bin'),[byte[]]::new(3))
[IO.File]::WriteAllBytes((Join-Path $modal 'modal-window.json'),[byte[]]::new(5))
$script:PlayerTemplateExportOriginalRoot.Plan=[pscustomobject]@{RunRoot=$work;WorkRoot=$work;GeneratedLimitBytes=8;ModalDiagnostic=[pscustomobject]@{RunRoot=$modal}}
$script:PlayerTemplateExportOriginalRoot.State=[ordered]@{Inputs=@()}
Test-PlayerGenerated $null
if($script:PlayerTemplateExportOriginalRoot.State.GeneratedObservedBytes -ne 8){throw 'Separate modal output escaped combined accounting'}
$refused=$false;try{Test-PlayerGenerated $null 7}catch{$refused=$true};if(!$refused){throw 'Combined allowance not enforced'}
$logs=Join-Path $modal 'owned-load-modal';[IO.Directory]::CreateDirectory($logs)|Out-Null
[IO.File]::WriteAllBytes((Join-Path $logs 'stderr.log'),[byte[]]::new(2MB+1))
$refused=$false;try{Test-PlayerGenerated $null 3MB}catch{$refused=$_.Exception.Message -ceq 'Sampled stream threshold exceeded.'}
if(!$refused){throw 'Separate helper stream escaped threshold'}
Write-Output 'combined-modal-budget-pass'
''');self.assertEqual(r.returncode,0,r.stderr);self.assertIn('combined-modal-budget-pass',r.stdout)
 def test_modal_reader_uses_exact_output_cap_and_retained_original_guard(self):
  r=self.fragment(('Read-PlayerOutput','Read-PlayerModalRecord'),'''
$modal=Join-Path $Directory 'owned-modal';$dir=Join-Path $modal 'load-diagnostic';[IO.Directory]::CreateDirectory($dir)|Out-Null
$path=Join-Path $dir 'modal-window.json';[IO.File]::WriteAllText($path,'{}')
$script:PlayerTemplateExportOriginalRoot.ModalOptions=[pscustomobject]@{RunRoot=$modal};$script:PlayerTemplateExportOriginalRoot.State=[ordered]@{}
if((Read-PlayerModalRecord $path) -cne '{}' -or $guards.Count -ne 1 -or $script:PlayerTemplateExportOriginalRoot.State.ModalRecord.Bytes -ne 2){throw 'Actual guarded modal reader not used'}
$blocked=$false;try{$w=[IO.File]::Open($path,'Open','Write','None');$w.Dispose()}catch{$blocked=$true};if(!$blocked){throw 'Modal evidence writable while held'}
$refused=$false;try{Read-PlayerModalRecord (Join-Path $Directory 'outside.json')}catch{$refused=$true};if(!$refused -or $guards.Count -ne 1){throw 'Unbound modal path opened'}
foreach($g in $guards){$g.Dispose()};$guards.Clear();[IO.File]::WriteAllBytes($path,[byte[]]::new(65537))
$refused=$false;try{Read-PlayerModalRecord $path}catch{$refused=$_.Exception.Message -ceq 'Output length exceeds bound.'}
if(!$refused -or $guards.Count -ne 1){throw 'Oversized modal record was not refused before read/hash'}
foreach($g in $guards){$g.Dispose()};$guards.Clear()
Write-Output 'guarded-modal-record-pass'
''');self.assertEqual(r.returncode,0,r.stderr);self.assertIn('guarded-modal-record-pass',r.stdout)
 def test_start_record_survives_failed_output_observation_without_claiming_completion(self):
  r=self.fragment('Record-PlayerCandidateStart','''
$image=Join-Path $Directory 'zonetool-iw7-player.exe';$created=[datetime]::Parse('2026-10-15T01:47:33.1885246Z').ToUniversalTime()
$ctx=[pscustomobject]@{Owner=[pscustomobject]@{PID=42;Image=$image;CreationFileTime=$created.ToFileTimeUtc()}}
$current=[pscustomobject]@{Identity=[ordered]@{PID=42;Image=$image;CreatedUtc=$created.ToString('o')}}
$script:PlayerTemplateExportOriginalRoot=@{Context=$ctx;Plan=@{WorkRoot=$Directory};State=[ordered]@{CandidateStarted=$null;NativeExportComplete=$false;CandidateExecuted=$false}}
$refused=$false;try{Record-PlayerCandidateStart $ctx ([pscustomobject]@{Identity=$null})}catch{$refused=$true}
if(!$refused -or $null -ne $script:PlayerTemplateExportOriginalRoot.State.CandidateStarted){throw 'Unconfirmed startup became a fact'}
Record-PlayerCandidateStart $ctx $current
try{throw 'Output observation failure'}catch{}
$state=$script:PlayerTemplateExportOriginalRoot.State
if(!$state.CandidateStarted -or $state.NativeExportComplete -or $state.CandidateExecuted -or ![object]::ReferenceEquals($state.CandidateIdentity,$current.Identity)){throw 'Started/completed evidence conflated'}
$other=[pscustomobject]@{Owner=$ctx.Owner};$refused=$false;try{Record-PlayerCandidateStart $other $current}catch{$refused=$true}
if(!$refused){throw 'Different original context accepted'}
$current.Identity.CreatedUtc='different';$refused=$false;try{Record-PlayerCandidateStart $ctx $current}catch{$refused=$true}
if(!$refused){throw 'Different child creation accepted'}
Write-Output 'started-failure-pass'
''');self.assertEqual(r.returncode,0,r.stderr);self.assertIn('started-failure-pass',r.stdout)
 def test_unknown_diagnostic_retains_combined_original_jobs_until_both_close(self):
  r=self.fragment('Close-PlayerOriginalJobs','''
class SourceOwner { [bool]$Closed;[bool]$Refuse;[int]$Calls
 [void]StopAndConfirm([int]$Ms){if($Ms -ne 5000){throw 'Wrong closure bound'};$this.Calls++;if($this.Refuse){throw 'Source unknown closure'};$this.Closed=$true}
}
$owner=[SourceOwner]::new();$owner.Closed=$true
$diag=[pscustomobject]@{Owner=$null;Closed=$false;Lease='source-only'}
$ctx=[pscustomobject]@{Owner=$owner;Closed=$true;Lease='source-only';DiagnosticContext=$diag}
$script:PlayerTemplateExportOriginalRoot=@{Context=$ctx;State=[ordered]@{CanExit=$false}}
Close-PlayerOriginalJobs
if($ctx.Closed -or $script:PlayerTemplateExportOriginalRoot.State.OriginalJobsClosed -or $ctx.Lease -cne 'source-only'){throw 'Unknown diagnostic was released by closed main'}
$diag.Owner=[SourceOwner]::new();$diag.Owner.Refuse=$true;Close-PlayerOriginalJobs
if($ctx.Closed -or !$script:PlayerTemplateExportOriginalRoot.State.ClosureError){throw 'Refused diagnostic closure became complete'}
$diag.Owner.Refuse=$false;Close-PlayerOriginalJobs
if(!$ctx.Closed -or !$diag.Closed -or !$diag.Owner.Closed -or !$script:PlayerTemplateExportOriginalRoot.State.OriginalJobsClosed){throw 'Original combined closure missing'}
Write-Output 'combined-source-closure-pass'
''');self.assertEqual(r.returncode,0,r.stderr);self.assertIn('combined-source-closure-pass',r.stdout)
 def test_poll_reuses_actual_world_modal_core_and_stops_after_one_owned_record(self):
  world=RUNNER.parent.parent/'world'/'original-arena'/'LoadDiagnostic.Core.ps1'
  r=self.fragment(('Record-PlayerCandidateStart','Invoke-PlayerOriginalPoll','Read-PlayerOutput','Read-PlayerModalRecord'),f". '{world}'\n"+'''
$image=Join-Path $Directory 'zonetool-iw7-player.exe';$created=[datetime]::Parse('2026-10-15T02:47:39.1438992Z').ToUniversalTime()
$owner=[pscustomobject]@{PID=42;Image=$image;CreationFileTime=$created.ToFileTimeUtc()}
$ctx=[pscustomobject]@{Owner=$owner;Closed=$false;Lease='source-only';Work=$Directory;Guards=$guards}
$current=[pscustomobject]@{Identity=[ordered]@{PID=42;Image=$image;CreatedUtc=$created.ToString('o')}}
$logs=Join-Path $Directory 'source-logs';[IO.Directory]::CreateDirectory($logs)|Out-Null
$line='[ INFO ][ zonetool::iw7::load_zone ]: Loading zone "global_mp"...';[IO.File]::WriteAllText((Join-Path $logs 'stdout.log'),$line+"`n")
$evidence=[ordered]@{Attempted=$false;LastBytes=([IO.FileInfo]::new((Join-Path $logs 'stdout.log'))).Length;LastProgressMs=0L;Outcome='NotTriggered'}
$options=[pscustomobject]@{StartedMs=0;RunRoot=(Join-Path $Directory 'snapshot-runtime');DiagnosticZone='global_mp';ModalTextOnly=$true;ModalSource='Source-only.py';Python='Source-only.exe';PythonSHA256=('0'*64);ToolSHA256=('0'*64);Inputs=@();ModalRecordReader={param($Path) Read-PlayerModalRecord $Path}}
$script:PlayerTemplateExportOriginalRoot=@{Context=$ctx;Plan=@{WorkRoot=$Directory};State=[ordered]@{CandidateStarted=$null};ModalOptions=$options;ModalEvidence=$evidence}
$script:calls=0;$script:budgets=0
function Get-H1Clock {50000}
function Test-PlayerGenerated($Current){$script:budgets++}
function Get-H1OriginalState($Owner){[pscustomobject]@{RootExited=$false;PID=42;Image=$image;CreatedUtc=$created.ToString('o')}}
function Register-H1Original($Lease,$Identity){if($Lease -cne 'source-only' -or $Identity.PID -ne 42){throw 'Wrong original registration'}}
function Invoke-OriginalArenaTool($Diag,$Exe,$SHA,$Arguments,$Work,$Run,$Phase,$Inputs,$Seconds){
 if($Phase -cne 'load-modal' -or $Seconds -ne 10 -or $Diag.Lease -cne $ctx.Lease -or !$ctx.PSObject.Properties['DiagnosticContext'] -or $Run -cne $options.RunRoot -or $Arguments[-1] -cne (Join-Path $Run 'load-diagnostic/modal-window.json')){throw 'Wrong existing original helper dispatch'}
 $script:calls++;$record=@{schema='iw7.world-modal-window/1';identity_verified_after=$true;modal_window_observed=$true;title='Source fixture';controls=@();interaction_performed=$false}
 [IO.File]::WriteAllText((Join-Path $Run 'load-diagnostic/modal-window.json'),($record|ConvertTo-Json))
 $Diag.Closed=$true;[pscustomobject]@{ExitCode=0;JobClosed=$true}
}
$refused=$false;try{Invoke-PlayerOriginalPoll $ctx $current $logs}catch{if($_.Exception.Message -cne 'Load diagnostic captured; material reference not measured.'){throw};$refused=$true}
if(!$refused -or $script:calls -ne 1 -or !$evidence.Attempted -or $evidence.Outcome -cne 'Captured' -or !$ctx.DiagnosticContext.Closed -or !$script:PlayerTemplateExportOriginalRoot.State.CandidateStarted){throw 'One actual modal witness did not fail closed'}
if($guards.Count -ne 1 -or $script:PlayerTemplateExportOriginalRoot.State.ModalRecord.Path -cne (Join-Path $options.RunRoot 'load-diagnostic/modal-window.json')){throw 'World callback bypassed original bounded reader'}
Invoke-PlayerOriginalPoll $ctx $current $logs
if($script:calls -ne 1){throw 'Modal repeated'}
$evidence.Attempted=$false;$options.ModalRecordReader='invalid'
$refused=$false;try{Invoke-PlayerOriginalPoll $ctx $current $logs}catch{$refused=$_.Exception.Message -ceq 'Modal record reader must be an explicit caller callback.'}
if(!$refused -or $script:calls -ne 1 -or $evidence.Outcome -cne 'Failed'){throw 'Present non-script reader did not refuse before helper'}
foreach($g in $guards){$g.Dispose()};$guards.Clear()
Write-Output 'actual-world-core-reuse-pass'
''');self.assertEqual(r.returncode,0,r.stderr);self.assertIn('actual-world-core-reuse-pass',r.stdout)
if __name__=='__main__':unittest.main()

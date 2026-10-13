import copy
import importlib.util
from pathlib import Path
import unittest
import tempfile
import hashlib
import json
import sys
import subprocess
import shutil
import struct
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('model_geometry', ROOT / 'ops/model-lab/geometry.py')
geometry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(geometry)


sys.path.insert(0,str(ROOT/'ops/model-lab'))
try:
    import prepare_writer
    import prepare_ff
    import rigid_export
finally:
    sys.path.pop(0)


class ModelSourceTests(unittest.TestCase):
    def test_ff_admission_rejects_stale_distance_metadata(self):
        script = r'''
param($Repo)
$ErrorActionPreference='Stop'
. "$Repo/ops/model-lab/ModelFF.Core.ps1"
$valid=@{lod0_dist=1000000;has_lods=$true;shadow_cutoff_lod=6;collision_lod=255}
Assert-ModelFFDistanceCandidate ([pscustomobject]$valid)
foreach($field in @('lod0_dist','has_lods','shadow_cutoff_lod','collision_lod')){
    $bad=$valid.Clone();$bad.Remove($field)
    $refused=$false;try{Assert-ModelFFDistanceCandidate ([pscustomobject]$bad)}catch{$refused=$true}
    if(!$refused){throw "Missing $field accepted"}
}
foreach($value in @('1000000',0,999999,$true,[double]::NaN)){
    $bad=$valid.Clone();$bad.lod0_dist=$value
    $refused=$false;try{Assert-ModelFFDistanceCandidate ([pscustomobject]$bad)}catch{$refused=$true}
    if(!$refused){throw 'Invalid distance accepted'}
}
foreach($value in @('true',1,$false)){
    $bad=$valid.Clone();$bad.has_lods=$value
    $refused=$false;try{Assert-ModelFFDistanceCandidate ([pscustomobject]$bad)}catch{$refused=$true}
    if(!$refused){throw 'Invalid hasLods accepted'}
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'runtime') as folder:
            path = Path(folder) / 'admission.ps1'
            path.write_text(script)
            result = subprocess.run(['pwsh', '-NoProfile', '-File', str(path), str(ROOT)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @classmethod
    def setUpClass(cls):
        # Match canonical runtime roots and keep NTFS fixtures on one volume in CI.
        (ROOT / "runtime").mkdir(exist_ok=True)

    def test_model_http_exact_route_and_cache_scope(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime") as folder:
            script=Path(folder)/'runtime-test.ps1'
            script.write_text(r"""param($Repo,$Temp)
$ErrorActionPreference='Stop'
. "$Repo/ops/Base-Client.Core.ps1"
. "$Repo/ops/model-lab/Model-Runtime.Core.ps1"
Add-Type -Path "$Repo/ops/hud-lab/HudHttp.cs"
$bytes=[Text.Encoding]::UTF8.GetBytes('synthetic transport only')
$hash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes))
$http=[IW7HudHttp]::new($bytes,$hash,"$Temp/gets.jsonl",[IW7HudHttp]::ModelRoute)
$client=[Net.Http.HttpClient]::new()
try {
    Assert-IW7ModelHttpContract $http ([pscustomobject]@{HttpRoute=[IW7HudHttp]::ModelRoute;SHA256=$hash})
    foreach($route in @([IW7HudHttp]::Route,([IW7HudHttp]::ModelRoute+'?x=1'),'/mods/other/mod.ff')) {
        $response=$client.GetAsync($http.BaseUrl+$route).GetAwaiter().GetResult()
        if([int]$response.StatusCode -ne 404){throw 'Unexpected route served'}
        $response.Dispose()
    }
    $actual=$client.GetByteArrayAsync($http.BaseUrl+[IW7HudHttp]::ModelRoute).GetAwaiter().GetResult()
    if([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($actual)) -cne $hash){throw 'Changed payload'}
    if($http.CompletedGets -ne 1){throw 'Unexpected GET count'}
} finally {$client.Dispose();$http.Dispose()}
if(!$http.Stopped){throw 'Worker remains'}
$refused=$false
try{[IW7HudHttp]::new($bytes,$hash,"$Temp/invalid.jsonl",'/mods/arbitrary/mod.ff')}catch{$refused=$true}
if(!$refused -or (Test-Path "$Temp/invalid.jsonl")){throw 'Invalid route created journal'}
$null=New-Item -ItemType Directory -Path "$Temp/game/mods/paris_model_probe" -Force
[IO.File]::WriteAllBytes("$Temp/game/mods/paris_model_probe/mod.ff",$bytes)
if((Get-IW7ModelProfilePaths "$Temp/game") -cne 'mods/paris_model_probe'){throw 'Wrong cache scope'}
[IO.File]::WriteAllText("$Temp/game/mods/paris_model_probe/foreign.txt",'preserve')
$refused=$false;try{Get-IW7ModelProfilePaths "$Temp/game"}catch{$refused=$true}
if(!$refused -or !(Test-Path "$Temp/game/mods/paris_model_probe/foreign.txt")){throw 'Foreign cache changed'}
""",encoding='utf-8')
            result=subprocess.run(['pwsh','-NoProfile','-File',str(script),str(ROOT),folder],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_measured_ff_reader_pairs_cannot_be_crossed_or_replaced(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime") as folder:
            script=Path(folder)/'candidate-pairs.ps1'
            script.write_text(r'''param($Repo)
$ErrorActionPreference='Stop'
. "$Repo/ops/model-lab/Model-Runtime.Core.ps1"
$old=Get-IW7ModelCandidate 1036 'BE3A34FF1AB0F95B1850E0BDE0BA60E519706F796F2BF38134C65A42724893CB'
$new=Get-IW7ModelCandidate 1040 '1E677EF4E0649159BFD507D993BA2FC9C12272C6F1C138CCD624D678CDBDBEA6'
$proof=[pscustomobject]@{ReaderSHA256=$new.Reader;Geometry=[pscustomobject]@{shadow_cutoff_lod=6;collision_lod=255}}
Assert-IW7ModelCandidateReader $new $proof
Assert-IW7ModelCandidateReader $old ([pscustomobject]@{ReaderSHA256=$old.Reader})
$lod=Get-IW7ModelCandidate 1040 '0EC7544D0197A2166E0F743A3832E630609109C1380DBFE2DC294D7773685063'
$geometry=[pscustomobject]@{shadow_cutoff_lod=6;collision_lod=255;lod0_dist=1000000;has_lods=$true}
Assert-IW7ModelCandidateReader $lod ([pscustomobject]@{ReaderSHA256=$lod.Reader;Geometry=$geometry})
foreach($bad in @($null,0,999999,'1000000',$true,[double]::NaN)){
    $geometry.lod0_dist=$bad;$refused=$false
    try{Assert-IW7ModelCandidateReader $lod ([pscustomobject]@{ReaderSHA256=$lod.Reader;Geometry=$geometry})}catch{$refused=$true}
    if(!$refused){throw 'LOD candidate accepted invalid distance'}
}
$geometry.lod0_dist=1000000
foreach($bad in @($null,$false,'true',1)){
    $geometry.has_lods=$bad;$refused=$false
    try{Assert-IW7ModelCandidateReader $lod ([pscustomobject]@{ReaderSHA256=$lod.Reader;Geometry=$geometry})}catch{$refused=$true}
    if(!$refused){throw 'LOD candidate accepted changed/undefined hasLods'}
}
foreach($variant in @('size','hash','reader','shadow','collision')) {
    $refused=$false
    try {
        switch($variant) {
            size { Get-IW7ModelCandidate 1036 $new.SHA256 }
            hash { Get-IW7ModelCandidate 1040 ('A'*64) }
            reader { $proof.ReaderSHA256=$old.Reader;Assert-IW7ModelCandidateReader $new $proof }
            shadow { $proof.ReaderSHA256=$new.Reader;$proof.Geometry.shadow_cutoff_lod=255;Assert-IW7ModelCandidateReader $new $proof }
            collision { $proof.Geometry.shadow_cutoff_lod=6;$proof.Geometry.collision_lod=6;Assert-IW7ModelCandidateReader $new $proof }
        }
    } catch {$refused=$true}
    if(!$refused){throw "Candidate pair accepted invalid $variant"}
}
''',encoding='utf-8')
            result=subprocess.run(['pwsh','-NoProfile','-File',str(script),str(ROOT)],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_model_runtime_evidence_does_not_infer_pixels_or_material(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime") as folder:
            script=Path(folder)/'witness.ps1'
            script.write_text(r"""param($Repo,$Temp)
$ErrorActionPreference='Stop'
. "$Repo/ops/Base-Client.Core.ps1"
. "$Repo/ops/model-lab/ModelFF.Core.ps1"
. "$Repo/ops/model-lab/Model-Runtime.Core.ps1"
function Update-IW7BaseClient($Session) {}
function Assert-IW7BaseIdentity($Identity) {if($Identity.PID -notin @(123,456)){throw 'Foreign identity'}}
$null=New-Item -ItemType Directory -Path "$Temp/base-client","$Temp/game/mods/paris_model_probe" -Force
$bytes=[Text.Encoding]::UTF8.GetBytes('synthetic test transport only')
$hash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes))
$build=[pscustomobject]@{Bytes=$bytes;SHA256=$hash;HttpRoute='/mods/paris_model_probe/mod.ff';RunRoot='synthetic'}
$http=[pscustomobject]@{AssetRoute=$build.HttpRoute;SHA256=$hash;Error=$null;CompletedGets=1}
$session=[pscustomobject]@{Identity=[pscustomobject]@{PID=123;Stdout="$Temp/base-client/client.stdout.log";CreatedUtc='synthetic';SHA256=$hash};Server=[pscustomobject]@{PID=456;Stdout="$Temp/server.stdout.log";CreatedUtc='synthetic'};OutputRoot="$Temp/base-client";Plan=[pscustomobject]@{GameRoot="$Temp/game"};Protected=$true;Failed=$false;StartedUtc=[datetime]::UtcNow.AddSeconds(-1)}
[IO.File]::WriteAllBytes("$Temp/game/mods/paris_model_probe/mod.ff",$bytes)
[IO.File]::WriteAllText($session.Identity.Stdout,'synthetic client log')
$text="[Paris model] SCRIPT_MODEL_REQUESTED; model=paris_model_probe; entity=52; pixels_pending=1.`t`r`n[Paris model] READY_MODEL; model=paris_model_probe; game_time_ms=4500; pixels_pending=1.`t`r`n"
[IO.File]::WriteAllText($session.Server.Stdout,$text)
$journal=[ordered]@{utc=[datetime]::UtcNow.ToString('o');method='GET';path=$build.HttpRoute;bytes=$bytes.Length;sha256=$hash}
[IO.File]::WriteAllText("$Temp/model-http.jsonl",($journal|ConvertTo-Json -Compress)+"`n")
Wait-IW7ModelRuntimeEvidence $session $build $http $Temp
$r=Get-Content "$Temp/model-runtime.local.json" -Raw|ConvertFrom-Json
if(!$r.ModelSetRequested -or !$r.FreshCacheVerified -or $r.PixelsVerified -or $r.Ready -or $r.RecipientReferenceResolved -or $r.HttpRequesterPID -cne 'unmeasured'){throw 'False acceptance'}
$build|Add-Member NoteProperty ModelName 'original/mesh.v2'
$text=$text.Replace('model=paris_model_probe;','model=original/mesh.v2;')
[IO.File]::WriteAllText($session.Server.Stdout,$text)
Wait-IW7ModelRuntimeEvidence $session $build $http $Temp
$r=Get-Content "$Temp/model-runtime.local.json" -Raw|ConvertFrom-Json
if($r.ModelName -cne $build.ModelName -or $r.PixelsVerified -or $r.Ready){throw 'Named model invented rendering evidence'}
[IO.File]::WriteAllText($session.Server.Stdout,$text+$text)
$refused=$false;try{Wait-IW7ModelRuntimeEvidence $session $build $http $Temp}catch{$refused=$true}
if(!$refused){throw 'Duplicate request accepted'}
[IO.File]::WriteAllText($session.Server.Stdout,$text)
$session.Server.PID=999
$refused=$false;try{Wait-IW7ModelRuntimeEvidence $session $build $http $Temp}catch{$refused=$true}
if(!$refused){throw 'Foreign server accepted'}
$session.Server.PID=456;$journal.utc=$session.StartedUtc.AddSeconds(-1).ToString('o')
[IO.File]::WriteAllText("$Temp/model-http.jsonl",($journal|ConvertTo-Json -Compress)+"`n")
$refused=$false;try{Wait-IW7ModelRuntimeEvidence $session $build $http $Temp}catch{$refused=$true}
if(!$refused){throw 'Stale GET accepted'}
""",encoding='utf-8')
            result=subprocess.run(['pwsh','-NoProfile','-File',str(script),str(ROOT),folder],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_original_geometry_has_outward_faces_and_one_rigid_root(self):
        data = geometry.validate(geometry.original_cube())
        self.assertFalse(data['iw7_serialized'])
        self.assertFalse(data['ready'])
        self.assertIsNone(data['surfaces'][0]['material_reference'])

    def test_writer_preparation_retains_explicit_source_geometry_and_pin_hashes(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime") as folder:
            source=Path(folder)/'source'
            for name in prepare_writer.INTERFACES:
                file=source/name
                file.parent.mkdir(parents=True,exist_ok=True)
                file.write_bytes(('synthetic interface '+name).encode())
            output=Path(folder)/'prepared'
            # Synthetic interfaces prove staging/hash contract, never compilation.
            manifest=prepare_writer.prepare(output,source,check_pin=False)
            self.assertFalse(manifest['compiled'])
            self.assertFalse(manifest['ready'])
            self.assertFalse(manifest['iw7_normal_encoding_verified'])
            self.assertEqual(manifest['shadow_cutoff_lod'], 6)
            self.assertEqual(manifest['collision_lod'], 255)
            self.assertEqual(manifest['lod0_dist'],1000000)
            self.assertIs(manifest['has_lods'],True)
            self.assertEqual(manifest['candidate_variable'],'lodInfo[0].dist')
            converter=prepare_writer.SHADOW_SENTINEL_SOURCE
            self.assertEqual(manifest['shadow_sentinel_source'],converter)
            self.assertIn(converter,manifest['source_hashes'])
            for name,sha in manifest['source_hashes'].items():
                self.assertEqual(sha,hashlib.sha256((source/name).read_bytes()).hexdigest())
            self.assertEqual(manifest['header_sha256'],hashlib.sha256((output/'probe_geometry.hpp').read_bytes()).hexdigest())
            self.assertIn('probe_vertices[24]',(output/'probe_geometry.hpp').read_text())
            before=(output/'writer.cpp').read_bytes()
            with self.assertRaises(ValueError):
                prepare_writer.prepare(output,source,check_pin=False)
            self.assertEqual((output/'writer.cpp').read_bytes(),before)
            refused=Path(folder)/'wrong-pin'
            with patch.object(prepare_writer.subprocess,'check_output',return_value='a'*40+'\n'):
                with self.assertRaises(ValueError):
                    prepare_writer.prepare(refused,source)
            self.assertFalse(refused.exists())

    def test_writer_preparation_requires_shadow_sentinel_converter_provenance(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime") as folder:
            source=Path(folder)/'source'
            for name in prepare_writer.INTERFACES:
                file=source/name
                file.parent.mkdir(parents=True,exist_ok=True)
                file.write_bytes(('synthetic interface '+name).encode())
            (source/prepare_writer.SHADOW_SENTINEL_SOURCE).unlink()
            output=Path(folder)/'missing-converter'
            with self.assertRaises(FileNotFoundError):
                prepare_writer.prepare(output,source,check_pin=False)
            self.assertFalse(output.exists())

    def test_wrapper_dependency_closure_reaches_memory_refusal_before_any_child(self):
        if not shutil.which('pwsh'):self.skipTest('PowerShell7 required')
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime") as folder:
            script=Path(folder)/'dependencies.ps1'
            script.write_text(r'''
param($Repo)
$ErrorActionPreference='Stop';$ops=Join-Path $Repo 'ops'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $ops 'model-lab/Build-ModelFF.ps1'),[ref]$tokens,[ref]$errors)
if($errors){throw $errors}
# Load actual wrapper dependencies without evaluating its admission/mutation body.
foreach($command in $ast.FindAll({param($node) $node -is [Management.Automation.Language.CommandAst] -and $node.InvocationOperator -eq [Management.Automation.Language.TokenKind]::Dot},$true)){
    if($command.Extent.Text -like '. "$ops/*'){Invoke-Expression $command.Extent.Text}
}
if(!(Get-Command Assert-IW7MemoryHeadroom -ErrorAction SilentlyContinue)){throw 'Wrapper omitted asset-process memory dependency'}
if(!(Get-Command Test-IW7MemoryBudget -ErrorAction SilentlyContinue)){throw 'Runtime memory poll dependency absent'}
function Assert-IW7MemoryHeadroom {throw 'injected-admission-refusal-before-owned-start'}
$cleanup=[pscustomobject]@{Confirmed=$true}
$failure=$null
try{Invoke-IW7LabAssetProcess -Executable 'not-launched.exe' -ToolArguments @('no-launch') -WorkingDirectory $Repo -LogDirectory $Repo -Phase dependency-test -LeaseToken synthetic -CleanupState $cleanup}catch{$failure=$_.Exception.Message}
if($failure -cne 'injected-admission-refusal-before-owned-start' -or !$cleanup.Confirmed){throw 'Dependency closure did not fail at admission before process ownership'}
''',encoding='utf-8')
            result=subprocess.run(['pwsh','-NoProfile','-File',str(script),str(ROOT)],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_real_ntfs_restore_refusals_keep_reservation_and_inventory_is_exact(self):
        if not shutil.which('pwsh'):self.skipTest('PowerShell7 required')
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime") as folder:
            script=Path(folder)/'fixture.ps1'
            script.write_text(r'''
param($Repo,$Fixture)
$ErrorActionPreference='Stop'
. (Join-Path $Repo 'ops/Base-Client.Core.ps1')
. (Join-Path $Repo 'ops/model-lab/ModelFF.Core.ps1')
Add-Type -Path (Join-Path $Repo 'ops/hud-lab/HudFileIdentity.cs')
$script:Released=$false;$script:Occupied=$false
function Exit-IW7ResourceLease {param($Token);$script:Released=$true}
function Assert-ModelFFVacant {param($Work);if($script:Occupied){throw 'injected owned vacancy refusal'}}
foreach($case in @('vacancy','fileid','attributes','pass')){
    $root=Join-Path $Fixture $case;$work=Join-Path $root 'work'
    [IO.Directory]::CreateDirectory($work)|Out-Null
    $source=Join-Path $root 'synthetic.ff';[IO.File]::WriteAllText($source,'synthetic fixture, no game assets')
    $txn=Save-IW7BaseTransaction ([pscustomobject]@{GameRoot=$work;MutableFiles=@('input.ff');ProfileDirectory='unused';ProfileDirectories=@()}) (Join-Path $root 'backup')
    $target=Join-Path $work 'input.ff';New-Item -ItemType HardLink -Path $target -Target $source|Out-Null
    $f=Get-Item -LiteralPath $source
    $input=[pscustomobject]@{Relative='input.ff';Source=$source;Bytes=$f.Length;ModifiedUtc=$f.LastWriteTimeUtc.ToString('o');Attributes=[int]$f.Attributes;SourceId=[IW7HudFileIdentity]::Read($source);TargetId=[IW7HudFileIdentity]::Read($target)}
    $state=[ordered]@{Work=$work;Inputs=@($input);Transaction=$txn;Restored=$false;StockPreserved=$false;RestorationStatus='Pending';CleanupError=$null;RetainedLeaseToken='synthetic-reservation'}
    $script:Released=$false;$script:Occupied=$case -eq 'vacancy'
    if($case -eq 'fileid'){Remove-Item -LiteralPath $target;[IO.File]::WriteAllText($target,'synthetic fixture, no game assets')}
    if($case -eq 'attributes'){[IO.File]::SetAttributes($source,[IO.FileAttributes]::ReadOnly)}
    $failed=$false;try{Complete-ModelFFRestore $state (Join-Path $root 'state.json') 'synthetic-reservation'}catch{$failed=$true}
    if($case -eq 'pass'){
        if($failed -or !$Released -or !$state.Restored -or $state.RetainedLeaseToken -or (Test-Path $target)){throw 'Verified restoration did not release last'}
    }else{
        if(!$failed -or $Released -or $state.Restored -or !$state.RetainedLeaseToken -or !(Test-Path $target) -or $state.RestorationStatus -cne 'Refused'){throw 'Unsafe restore released or removed guarded bytes'}
    }
    [IO.File]::SetAttributes($source,[IO.FileAttributes]::Archive)
}
$log='Loading zone "paris_model_probe"'+"`n"
$rows=@('material,,mopw/character_park_clown_zombie_shoes','xmodelsurfs,paris_model_probe_lod0','xmodel,paris_model_probe','netconststrings,ncs_mdl_paris_model_probe','rawfile,paris_model_probe')
foreach($row in $rows){$parts=$row.Split(',',2);$log+='Loading asset "'+$parts[1]+'" of type '+$parts[0]+'.'+"`n"}
if(@(Get-ModelFFInventory $log).Count -ne 5){throw 'Supported inventory refused'}
foreach($bad in @($log+'Loading asset "foreign" of type rawfile.',$log.Replace(',mopw/character_park_clown_zombie_shoes','wrong'),$log+'Could not find referenced asset')){
    $failed=$false;try{$null=Get-ModelFFInventory $bad}catch{$failed=$true};if(!$failed){throw 'False model inventory accepted'}
}
''',encoding='utf-8')
            result=subprocess.run(['pwsh','-NoProfile','-File',str(script),str(ROOT),folder],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_ff_staging_refuses_unlinked_material_or_changed_payload(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime") as folder:
            run=Path(folder)/'writer';run.mkdir()
            entries=[]
            for name in prepare_ff.ARTIFACTS:
                file=run/'artifacts'/name;file.parent.mkdir(parents=True,exist_ok=True)
                payload=('synthetic transport '+name).encode();file.write_bytes(payload)
                entries.append({'Path':name,'Bytes':len(payload),'SHA256':hashlib.sha256(payload).hexdigest()})
            data={'Schema':'iw7.model-writer-build/1','SourcePin':prepare_writer.PIN,
                  'Source':{'material_reference':None},'Roundtrip':{'geometry_roundtrip_verified':True,
                   'vertices':24,'triangles':12,'bones':1,'surfaces':1,'lods':1,'material_reference':None},
                  'Artifacts':entries,'Ready':False,'FFBuilt':False}
            provenance=run/'writer-provenance.json'
            provenance.write_text(json.dumps(data))
            refused=Path(folder)/'unlinked'
            with self.assertRaises(ValueError):prepare_ff.stage(run,refused)
            self.assertFalse(refused.exists())
            data['Source']['material_reference']=prepare_ff.MATERIAL
            data['Roundtrip']['material_reference']=prepare_ff.MATERIAL
            semantic={'lod0_dist':1000000,'has_lods':True,'shadow_cutoff_lod':6,'collision_lod':255}
            data['Source'].update(semantic,candidate_variable='lodInfo[0].dist')
            data['Roundtrip'].update(semantic)
            for scope in ('Source','Roundtrip'):
                for key,value in (('lod0_dist',None),('lod0_dist',0),('lod0_dist',float('nan')),
                                  ('lod0_dist','1000000'),('lod0_dist',True),('has_lods',False),
                                  ('has_lods','true'),('shadow_cutoff_lod',255),('collision_lod',6)):
                    invalid=copy.deepcopy(data);invalid[scope][key]=value
                    provenance.write_text(json.dumps(invalid))
                    rejected=Path(folder)/'bad-candidate'
                    with self.subTest(scope=scope,key=key,value=value):
                        with self.assertRaises(ValueError):prepare_ff.stage(run,rejected)
                        self.assertFalse(rejected.exists())
            provenance.write_text(json.dumps(data))
            target=Path(folder)/'staged'
            plan=prepare_ff.stage(run,target)
            self.assertFalse(plan['ready']);self.assertFalse(plan['ff_built'])
            self.assertFalse(plan['material_payload_copied'])
            self.assertEqual(len(plan['expected_inventory']),5)
            self.assertEqual(plan['lod0_dist'],1000000)
            self.assertIs(plan['has_lods'],True)
            self.assertEqual(plan['candidate_variable'],'lodInfo[0].dist')
            self.assertIn('ignore,paris_model_probe_recipient',(target/'zone_source/paris_model_probe.csv').read_text())
            with self.assertRaises(ValueError):prepare_ff.stage(run,target)
            (run/'artifacts'/entries[0]['Path']).write_bytes(b'changed')
            changed=Path(folder)/'changed'
            with self.assertRaises(ValueError):prepare_ff.stage(run,changed)
            self.assertFalse(changed.exists())

    def test_geometry_rejects_nan_inverted_faces_bad_indices_and_false_ready(self):
        base = geometry.original_cube()
        for change in (
            lambda d: d['surfaces'][0]['vertices'][0]['position'].__setitem__(0, float('nan')),
            lambda d: d['surfaces'][0]['triangles'][0].reverse(),
            lambda d: d['surfaces'][0]['triangles'][0].__setitem__(0, 24),
            lambda d: d['surfaces'][0]['vertices'][0].__setitem__('weight', .5),
            lambda d: d.__setitem__('ready', True),
            lambda d: d['surfaces'][0].__setitem__('material_reference', 'invented_material'),
        ):
            with self.subTest(change=change):
                data = copy.deepcopy(base)
                change(data)
                with self.assertRaises(ValueError):
                    geometry.validate(data)


class ResidentRigidTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / 'runtime').mkdir(exist_ok=True)
        sys.path.insert(0, str(rigid_export.BRIDGE))
        try:
            spec = importlib.util.spec_from_file_location('_model_lab_synthetic', rigid_export.BRIDGE / 'test_readback.py')
            cls.fixture = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.fixture)
        finally:
            sys.path.pop(0)

    def synthetic(self):
        # Explicit independent irregular pyramid; deliberately not the cube,
        # not donor bytes, and with a mesh name unrelated to the model suffix.
        return self.fixture.Synthetic(names=('original/pilot', 'mesh/unrelated', 'root pivot', 'donor/clay'), lod=0)

    def multi(self, **kwargs):
        return self.fixture.SyntheticMulti(names=('original/pilot', 'mesh/unrelated', 'root pivot', 'donor/clay'), **kwargs)

    def bindings(self, fixture):
        return [dict(slot=i, source=name, target=rigid_export.MATERIAL)
                for i, name in enumerate(fixture.manifest['material_dependencies'])]

    def write_export(self, root, fixture):
        root.mkdir()
        for role in ('model', 'mesh'):
            path = root / fixture.manifest[role]['relative_path']
            path.parent.mkdir(parents=True)
            path.write_bytes(fixture.outputs[role])
        (root / 'request.json').write_bytes(rigid_export.json_bytes(fixture.request))
        (root / 'manifest.json').write_bytes(rigid_export.json_bytes(fixture.manifest))

    def staged(self, base, fixture=None, distance=None):
        fixture = fixture or self.synthetic()
        root, staged = base / 'export', base / 'prepared'
        self.write_export(root, fixture)
        v2 = fixture.manifest['geometry_profile'] == rigid_export.PROFILE_V2
        plan = rigid_export.stage(root, root / 'request.json', root / 'manifest.json', staged,
                                  None if v2 else rigid_export.MATERIAL, distance,
                                  rebinds=self.bindings(fixture) if v2 else None)
        return fixture, root, staged, plan

    def test_material_only_rebind_preserves_every_other_byte_and_manifest(self):
        f = self.synthetic()
        model, mesh = bytes(f.outputs['model']), bytes(f.outputs['mesh'])
        manifest = copy.deepcopy(f.manifest)
        derived, proof = rigid_export.derive(model, mesh, f.manifest, f.request, rigid_export.MATERIAL)
        start, end = f.records['model']['material'] + 2, f.records['model']['lod0'] - 1
        self.assertEqual(derived, model[:start] + rigid_export.MATERIAL.encode() + model[end:])
        self.assertEqual(f.manifest, manifest)
        self.assertEqual(bytes(f.outputs['model']), model)
        self.assertEqual(bytes(f.outputs['mesh']), mesh)
        self.assertEqual(proof['derived_model']['lod_distance'], 317)
        self.assertEqual(proof['source_readback']['mesh']['vertices'], 5)
        self.assertEqual(proof['source_readback']['mesh']['triangle_count'], 6)
        for key in ('native_provenance_verified', 'runtime_verified', 'pixels_verified', 'ready'):
            self.assertIs(proof[key], False)

    def test_explicit_lod_transform_and_source_zero_are_distinct_from_export_validity(self):
        f = self.synthetic().change('model', 'model', 6 + 224, 'f', 0)
        model, mesh = bytes(f.outputs['model']), bytes(f.outputs['mesh'])
        unchanged, _ = rigid_export.derive(model, mesh, f.manifest, f.request, rigid_export.MATERIAL)
        derived, proof = rigid_export.derive(model, mesh, f.manifest, f.request, rigid_export.MATERIAL, 1000000)
        self.assertEqual(derived, unchanged[:230] + struct.pack('<f', 1000000) + unchanged[234:])
        self.assertEqual(proof['transformations'][1]['old'], 0)
        self.assertEqual(proof['transformations'][1]['new'], 1000000)
        self.assertEqual(f.inspect()['model']['lod_distance'], 0)
        for value in (float('nan'), float('inf'), -1, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                rigid_export.derive(model, mesh, f.manifest, f.request, rigid_export.MATERIAL, value)
        with tempfile.TemporaryDirectory(dir=ROOT / 'runtime') as folder:
            _, _, staged, plan = self.staged(Path(folder), f)
            self.assertFalse(plan['scene_lod_distance_sufficient'])
            rigid_export.verify_stage(staged)
            with self.assertRaisesRegex(ValueError, 'export is not invalid'):
                rigid_export.verify_stage(staged, scene=True)

    def test_staging_keeps_native_receipt_and_ncs_actual_name(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'runtime') as folder:
            f, root, staged, plan = self.staged(Path(folder), distance=1000000)
            rigid_export.verify_stage(staged, scene=True)
            self.assertEqual(len(plan['source_files']), 5)
            self.assertEqual((staged / 'evidence/manifest.json').read_bytes(), (root / 'manifest.json').read_bytes())
            self.assertEqual((staged / 'evidence/source.xmb').read_bytes(), bytes(f.outputs['model']))
            self.assertEqual((staged / 'xsurface/mesh/unrelated.xsb').read_bytes(), bytes(f.outputs['mesh']))
            ncs = json.loads((staged / 'netconststrings/ncs_mdl_paris_model_probe.json').read_bytes())
            self.assertEqual(ncs['stringList'], ['original/pilot'])
            self.assertIn('xmodel,original/pilot\n', (staged / 'zone_source/paris_model_probe.csv').read_text())
            self.assertEqual(plan['zone'], 'paris_model_probe')
            with self.assertRaises(ValueError):
                rigid_export.stage(root, root / 'request.json', root / 'manifest.json', root / 'nested', rigid_export.MATERIAL)
            with self.assertRaises(ValueError):
                rigid_export.stage(root, root / 'request.json', root / 'manifest.json', Path(folder) / 'wrong', 'donor/clay')

    def test_third_change_is_rejected_even_when_staged_hash_is_updated(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'runtime') as folder:
            f, _, staged, plan = self.staged(Path(folder), distance=1000000)
            path = staged / 'xmodel/original/pilot.xmb'
            data = bytearray(path.read_bytes())
            # Valid independent mip-radius change: geometry parser alone would
            # accept it, but it is not either declared derivation.
            struct.pack_into('<e', data, f.records['model']['mip_radius'] + 6, 0.5)
            path.write_bytes(data)
            plan['source_files']['xmodel/original/pilot.xmb'] = rigid_export.digest(data)
            (staged / 'model-ff-plan.json').write_bytes(rigid_export.json_bytes(plan))
            with self.assertRaises(ValueError):
                rigid_export.verify_stage(staged)

    def test_cli_rejects_ambiguous_json_and_reports_explicit_scene_gate(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'runtime') as folder:
            base = Path(folder)
            f = self.synthetic().change('model', 'model', 6 + 224, 'f', 0)
            root = base / 'export'
            self.write_export(root, f)
            output = base / 'cli-prepared'
            command = [sys.executable, '-B', '-S', str(ROOT / 'ops/model-lab/prepare_ff.py'),
                       '--export-root', str(root), '--request', str(root / 'request.json'),
                       '--manifest', str(root / 'manifest.json'), '--output', str(output),
                       '--rebind-material', rigid_export.MATERIAL]
            result = subprocess.run(command, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(json.loads(result.stdout)['scene_lod_distance_sufficient'])
            verify = [sys.executable, '-B', '-S', str(ROOT / 'ops/model-lab/rigid_export.py'),
                      'verify-stage', '--source', str(output)]
            result = subprocess.run(verify, capture_output=True, text=True, timeout=15)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('export is not invalid', result.stderr)
            original = (root / 'manifest.json').read_bytes()
            for raw in (b'{"schema":1,"schema":2}', b'{"value":NaN}', b' ' * 4097):
                with self.subTest(raw_length=len(raw)):
                    (root / 'manifest.json').write_bytes(raw)
                    with self.assertRaises(ValueError):
                        rigid_export.stage(root, root / 'request.json', root / 'manifest.json', base / 'refused', rigid_export.MATERIAL)
                    self.assertFalse((base / 'refused').exists())
            (root / 'manifest.json').write_bytes(original)
            for name in ('../escape', 'a/b,rawfile', 'a/CON', 'name;quit'):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    rigid_export.lab_name(name)

    def test_dump_compares_packed_normals_uv_indices_and_semantics(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'runtime') as folder:
            base = Path(folder)
            f, _, staged, _ = self.staged(base, distance=1000000)
            dump = base / 'roundtrip'
            for relative in ('xmodel/original/pilot.xmb', 'xsurface/mesh/unrelated.xsb'):
                target = dump / relative
                target.parent.mkdir(parents=True)
                target.write_bytes((staged / relative).read_bytes())
            ff = base / 'mod.ff'
            ff.write_bytes(b'original synthetic FF stand-in; never engine input')
            proof = rigid_export.verify_dump(staged, dump, ff)
            self.assertTrue(proof['geometry_roundtrip_verified'])
            self.assertFalse(proof['source_geometry_correspondence_verified'])
            self.assertFalse(proof['runtime_verified'])
            # A dump may use different nonzero pointer sentinels.
            model_path = dump / 'xmodel/original/pilot.xmb'
            model = bytearray(model_path.read_bytes())
            struct.pack_into('<Q', model, 6 + 152, 0xabcde000)
            model_path.write_bytes(model)
            rigid_export.verify_dump(staged, dump, ff)
            mesh_path = dump / 'xsurface/mesh/unrelated.xsb'
            original = mesh_path.read_bytes()
            for offset in (12, 16, 20, 24, 28):
                with self.subTest(packed_offset=offset):
                    data = bytearray(original)
                    data[f.records['mesh']['vertices'] + 6 + offset] ^= 1
                    mesh_path.write_bytes(data)
                    with self.assertRaisesRegex(ValueError, 'FF dump differs'):
                        rigid_export.verify_dump(staged, dump, ff)
            mesh_path.write_bytes(original)
            data = bytearray(original)
            offset = f.records['mesh']['triangles'] + 6
            data[offset:offset+6] = struct.pack('<3H', 0, 1, 2)
            mesh_path.write_bytes(data)
            with self.assertRaises(ValueError):
                rigid_export.verify_dump(staged, dump, ff)

    def test_rigid_runtime_requires_reviewed_tuple_and_exact_large_cache(self):
        self.runtime_checks(self.synthetic())

    def test_multisurface_runtime_requires_reviewed_tuple_and_exact_large_cache(self):
        self.runtime_checks(self.multi())

    def runtime_checks(self, fixture):
        with tempfile.TemporaryDirectory(dir=ROOT / 'runtime') as folder:
            base = Path(folder)
            f, _, staged, plan = self.staged(base, fixture, distance=1000000)
            dump = base / 'roundtrip'
            for relative in ('xmodel/original/pilot.xmb', 'xsurface/mesh/unrelated.xsb'):
                target = dump / relative
                target.parent.mkdir(parents=True)
                target.write_bytes((staged / relative).read_bytes())
            ff = base / 'mod.ff'
            ff.write_bytes(b'SYNTHETIC NOT A FASTFILE\n' * 128)
            proof = rigid_export.verify_dump(staged, dump, ff)
            evidence = rigid_export.json_bytes(proof)
            (base / 'geometry-roundtrip.json').write_bytes(evidence)
            (base / 'reader.stdout.log').write_bytes(evidence)
            rows = [('material', ',' + rigid_export.MATERIAL), ('xmodelsurfs', plan['mesh_name']),
                    ('xmodel', plan['model_name']), ('netconststrings', 'ncs_mdl_paris_model_probe'), ('rawfile', 'paris_model_probe')]
            log = 'Loading zone "paris_model_probe"\n' + ''.join(f'Loading asset "{name}" of type {kind}.\n' for kind, name in rows)
            (base / 'inventory.stdout.log').write_text(log)
            state = {'Schema': 'iw7.model-ff-build/1', 'SourcePlan': plan, 'SourcePlanSHA256': proof['source_plan_sha256'],
                     'Restored': True, 'StockPreserved': True, 'RestorationStatus': 'Confirmed', 'RetainedLeaseToken': None,
                     'InventoryVerified': True, 'GeometryRoundtripVerified': True, 'Ready': False,
                     'Build': {'ExitCode': 0}, 'Offline': {'ExitCode': 0, 'Stdout': str(base / 'inventory.stdout.log')},
                     'Dump': {'ExitCode': 0}, 'GeometryReader': {'ExitCode': 0, 'Stdout': str(base / 'reader.stdout.log')},
                     'GeometryEvidenceSHA256': rigid_export.digest(evidence),
                     'FF': {'Path': 'mod.ff', 'Bytes': proof['ff']['bytes'], 'SHA256': proof['ff']['sha256']}}
            (base / 'state.local.json').write_bytes(rigid_export.json_bytes(state))
            script = base / 'runtime.ps1'
            script.write_text(r'''param($Repo,$Root)
$ErrorActionPreference='Stop'
. "$Repo/ops/Base-Client.Core.ps1"
. "$Repo/ops/model-lab/ModelFF.Core.ps1"
. "$Repo/ops/model-lab/Model-Runtime.Core.ps1"
$s=Get-Content "$Root/state.local.json" -Raw|ConvertFrom-Json
$pins=@($s.FF.Bytes,$s.FF.SHA256,$s.GeometryEvidenceSHA256)
$refused=$false;try{Read-IW7ModelBuild $Root 'geometry-roundtrip.json'}catch{$refused=$true}
if(!$refused){throw 'Unreviewed resident build accepted'}
$build=Read-IW7ModelBuild $Root 'geometry-roundtrip.json' @pins
if($build.ModelName -cne 'original/pilot' -or $build.MeshName -cne 'mesh/unrelated' -or
    $build.FsGame -cne 'mods/paris_model_probe' -or $build.Ready -or $build.PixelsVerified){throw 'Rigid route/claims differ'}
$goodProfile=$s.SourcePlan.geometry_profile
$s.SourcePlan.geometry_profile='t7-iw7-resident-static-v3'
$refused=$false;try{Read-IW7RigidModelBuild $Root $s 'geometry-roundtrip.json' @pins}catch{$refused=$true}
if(!$refused){throw 'Unknown geometry profile accepted'}
$s.SourcePlan.geometry_profile=$goodProfile
if($goodProfile -ceq 't7-iw7-resident-static-v2'){
    # Same aggregate totals/work but changed per-surface attribution must fail
    # against the independently pinned reader receipt.
    $s.SourcePlan.surface_records[0].vertices--;$s.SourcePlan.surface_records[1].vertices++
    $refused=$false;try{Read-IW7RigidModelBuild $Root $s 'geometry-roundtrip.json' @pins}catch{$refused=$true}
    if(!$refused){throw 'Crossed per-surface counts accepted'}
    $s.SourcePlan.surface_records[0].vertices++;$s.SourcePlan.surface_records[1].vertices--
}
foreach($i in 0..2){
    $bad=$pins.Clone();$bad[$i]=if($i -eq 0){123}else{'A'*64}
    $refused=$false;try{Read-IW7ModelBuild $Root 'geometry-roundtrip.json' @bad}catch{$refused=$true}
    if(!$refused){throw 'Wrong review tuple accepted'}
}
$log=[IO.File]::ReadAllText("$Root/inventory.stdout.log")
$rows=@(Get-ModelFFInventory $log $build.ModelName $build.MeshName)
if($rows.Count -ne 5){throw 'Incomplete inventory'}
$refused=$false;try{Get-ModelFFInventory $log}catch{$refused=$true}
if(!$refused){throw 'Cube inventory silently widened'}
$game="$Root/game";$null=New-Item -ItemType Directory "$game/mods/paris_model_probe" -Force
[IO.File]::WriteAllBytes("$game/mods/paris_model_probe/mod.ff",$build.Bytes)
$null=Get-IW7ModelProfilePaths $game $build
$knownProfile=$build.GeometryProfile;$build.GeometryProfile='unknown'
$refused=$false;try{Get-IW7ModelProfilePaths $game $build}catch{$refused=$true}
if(!$refused){throw 'Unknown cache profile accepted'}
$build.GeometryProfile=$knownProfile
$refused=$false;try{Get-IW7ModelProfilePaths $game}catch{$refused=$true}
if(!$refused){throw 'Legacy cache limit widened without review'}
$bad=$build.Bytes.Clone();$bad[0]=$bad[0] -bxor 1
[IO.File]::WriteAllBytes("$game/mods/paris_model_probe/mod.ff",$bad)
$refused=$false;try{Get-IW7ModelProfilePaths $game $build}catch{$refused=$true}
if(!$refused -or !(Test-Path "$game/mods/paris_model_probe/mod.ff")){throw 'Foreign larger cache accepted/deleted'}
$refused=$false;try{Get-IW7ModelCandidate $s.FF.Bytes $s.FF.SHA256}catch{$refused=$true}
if(!$refused){throw 'Synthetic FF entered historical whitelist'}
[IO.File]::WriteAllBytes("$Root/roundtrip/xsurface/mesh/unrelated.xsb",[byte[]](1,2,3))
$refused=$false;try{Read-IW7ModelBuild $Root 'geometry-roundtrip.json' @pins}catch{$refused=$true}
if(!$refused){throw 'Changed retained readback accepted'}
''')
            result = subprocess.run(['pwsh', '-NoProfile', '-File', str(script), str(ROOT), folder], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_multisurface_rebind_patches_definitions_once_and_retains_alias_bytes(self):
        shapes = [(self.fixture.PYRAMID, self.fixture.PYRAMID_FACES)] * 4
        for aliases in (True, False):
            f = self.multi(surfaces=shapes, materials=['a/clay', 'b/metal', 'a/clay', 'b/metal'],
                           alias_materials=aliases, alias_geometry=True)
            model, mesh = bytes(f.outputs['model']), bytes(f.outputs['mesh'])
            derived, proof = rigid_export.derive(model, mesh, f.manifest, f.request,
                                                 rebinds=self.bindings(f))
            changes = proof['transformations']
            self.assertEqual(len(changes), 2 if aliases else 4)
            expected = model
            for item in reversed(changes):
                a, b = item['source_string_span']
                self.assertEqual(model[a:b].decode(), item['old'])
                expected = expected[:a] + item['new'].encode() + expected[b:]
            self.assertEqual(derived, expected)
            self.assertEqual(proof['schema'], 'iw7.model-derived-export/2')
            self.assertEqual(proof['derived_model']['materials'], [rigid_export.MATERIAL] * 4)
            self.assertEqual(proof['source_readback']['mesh']['surfaces'], 4)
            self.assertEqual(proof['mesh_sha256'], rigid_export.digest(mesh))
            if aliases:
                self.assertEqual([c['slots'] for c in changes], [[0, 2], [1, 3]])

    def test_multisurface_rebind_requires_exact_explicit_order_and_alias_consistency(self):
        f = self.multi()
        source = bytes(f.outputs['model']), bytes(f.outputs['mesh']), f.manifest, f.request
        for change in (lambda x: x.pop(), lambda x: x.reverse(),
                       lambda x: x[0].update(slot=True), lambda x: x[0].update(source='wrong'),
                       lambda x: x[0].update(target='other/recipient'), lambda x: x[0].update(extra=1)):
            bindings = self.bindings(f);change(bindings)
            with self.assertRaises(ValueError):
                rigid_export.derive(*source, rebinds=bindings)
        with self.assertRaisesRegex(ValueError, 'Aliased material slots'):
            bindings = self.bindings(f);bindings[1]['target'] = 'conflicting/target'
            rigid_export.derive(*source, rebinds=bindings)
        for kwargs in ({}, {'material': rigid_export.MATERIAL},
                       {'material': rigid_export.MATERIAL, 'rebinds': self.bindings(f)}):
            with self.assertRaises(ValueError):
                rigid_export.derive(*source, **kwargs)
        legacy = self.synthetic()
        with self.assertRaises(ValueError):
            rigid_export.derive(bytes(legacy.outputs['model']), bytes(legacy.outputs['mesh']),
                                legacy.manifest, legacy.request, rebinds=self.bindings(legacy))

    def test_multisurface_max_slots_stage_and_metadata_bounds(self):
        f = self.multi(surfaces=[(self.fixture.PYRAMID, self.fixture.PYRAMID_FACES)] * 255,
                       alias_geometry=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'runtime') as folder:
            _, root, staged, plan = self.staged(Path(folder), f, distance=1000000)
            rigid_export.verify_stage(staged, scene=True)
            self.assertEqual(plan['schema'], 'iw7.model-ff-plan/2')
            self.assertEqual(plan['selected_counts']['surfaces'], 255)
            self.assertEqual(len(plan['source_files']), 5)
            self.assertGreater((staged / 'derived-export.json').stat().st_size, 65536)
            self.assertGreater((root / 'manifest.json').stat().st_size, 4096)
            self.assertEqual((staged / 'evidence/manifest.json').read_bytes(), (root / 'manifest.json').read_bytes())
            self.assertEqual((staged / 'zone_source/paris_model_probe_recipient.csv').read_text().count('material,'), 1)
            original = (staged / 'derived-export.json').read_bytes()
            (staged / 'derived-export.json').write_bytes(b' ' * (rigid_export.DOCUMENT_LIMIT + 1))
            with self.assertRaises(ValueError):rigid_export.verify_stage(staged)
            (staged / 'derived-export.json').write_bytes(original)
            plan['surface_records'][254]['vertices'] += 1
            (staged / 'model-ff-plan.json').write_bytes(rigid_export.json_bytes(plan))
            with self.assertRaises(ValueError):rigid_export.verify_stage(staged)

    def test_multisurface_dump_rejects_late_packed_changes_and_undeclared_rebind(self):
        f = self.multi(materials=['first/clay', 'last/metal'])
        with tempfile.TemporaryDirectory(dir=ROOT / 'runtime') as folder:
            base = Path(folder)
            _, _, staged, plan = self.staged(base, f, distance=1000000)
            dump = base / 'roundtrip'
            for role in ('model', 'mesh'):
                relative = f.manifest[role]['relative_path']
                target = dump / relative;target.parent.mkdir(parents=True)
                target.write_bytes((staged / relative).read_bytes())
            ff = base / 'mod.ff';ff.write_bytes(b'SYNTHETIC NOT A FASTFILE')
            proof = rigid_export.verify_dump(staged, dump, ff)
            self.assertEqual(proof['schema'], 'iw7.model-rigid-roundtrip/2')
            self.assertEqual(proof['surface_records'], f.manifest['surface_records'])
            self.assertIs(proof['runtime_verified'], False)
            path = dump / f.manifest['mesh']['relative_path'];original = path.read_bytes()
            for offset in (12, 16, 20, 24, 28):
                data = bytearray(original)
                data[f.records['mesh']['surface_1.vertices'] + 6 + offset] ^= 1
                path.write_bytes(data)
                with self.assertRaisesRegex(ValueError, 'FF dump differs'):
                    rigid_export.verify_dump(staged, dump, ff)
            path.write_bytes(original)
            # A valid but undeclared late material change cannot be hidden by
            # replacing a staged hash and its mutable plan.
            path = staged / f.manifest['model']['relative_path']
            data = path.read_bytes().replace(rigid_export.MATERIAL.encode(), b'other/recipient', 1)
            path.write_bytes(data);plan['source_files'][f.manifest['model']['relative_path']] = rigid_export.digest(data)
            (staged / 'model-ff-plan.json').write_bytes(rigid_export.json_bytes(plan))
            with self.assertRaises(ValueError):rigid_export.verify_stage(staged)

    def test_multisurface_cli_explicit_bindings_and_version_dispatch(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'runtime') as folder:
            base = Path(folder);root = base / 'export';f = self.multi()
            self.write_export(root, f)
            binding_path = base / 'bindings.json';binding_path.write_bytes(rigid_export.json_bytes(self.bindings(f)))
            command = [sys.executable, '-B', '-S', str(ROOT / 'ops/model-lab/prepare_ff.py'),
                       '--export-root', str(root), '--request', str(root / 'request.json'),
                       '--manifest', str(root / 'manifest.json'), '--output', str(base / 'prepared')]
            result = subprocess.run(command + ['--rebind-material', rigid_export.MATERIAL], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0);self.assertFalse((base / 'prepared').exists())
            result = subprocess.run(command + ['--material-rebinds', str(binding_path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['geometry_profile'], rigid_export.PROFILE_V2)

    def test_multisurface_powershell_admission_and_actual_http_dispatch(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'runtime') as folder:
            base = Path(folder);_, _, staged, _ = self.staged(base, self.multi(), distance=1000000)
            script = base / 'v2-gates.ps1'
            script.write_text(r'''param($Repo,$Source)
$ErrorActionPreference='Stop'
. "$Repo/ops/model-lab/ModelFF.Core.ps1"
$raw=[IO.File]::ReadAllText("$Source/model-ff-plan.json")
$valid=$raw|ConvertFrom-Json
Assert-ModelFFRigidPlan $valid
if(@(Get-ModelFFSourceNames $valid).Count -ne 5){throw 'Source inventory changed'}
foreach($case in @('schema','profile','order','totals','work','slots','bool','string','oversize','mixed')){
    $p=$raw|ConvertFrom-Json
    switch($case){
        schema {$p.schema='iw7.model-ff-plan/1'}
        profile {$p.geometry_profile='unrecognized'}
        order {$p.surface_records[1].index=0}
        totals {$p.selected_counts.vertices++}
        work {$p.geometry_work_bytes_upper_bound++}
        slots {$p.material_references=@($p.material_references[0])}
        bool {$p.surface_records[0].material_slot=$false}
        string {$p.surface_records[0].vertices='5'}
        mixed {$p|Add-Member NoteProperty material_reference 'mopw/character_park_clown_zombie_shoes'}
        oversize {
            $p.surface_records=@(0..5|ForEach-Object{[pscustomobject]@{index=$_;material_slot=$_;vertices=65535;triangles=65535}})
            $p.material_references=@($valid.material_references[0])*6
            $p.selected_counts.surfaces=6;$p.selected_counts.vertices=6*65535;$p.selected_counts.triangles=6*65535
            $p.geometry_work_bytes_upper_bound=256+368*6+72*6*65535
        }
    }
    $refused=$false;try{Assert-ModelFFRigidPlan $p}catch{$refused=$true}
    if(!$refused){throw "Invalid v2 $case accepted"}
}
# Aggregate counts are not uint16; each individual surface remains bounded.
$p=$raw|ConvertFrom-Json
foreach($record in $p.surface_records){$record.vertices=40000}
$p.selected_counts.vertices=80000;$p.geometry_work_bytes_upper_bound=256+368*2+60*80000+12*10
Assert-ModelFFRigidPlan $p
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile("$Repo/ops/Agent-Lab.ps1",[ref]$tokens,[ref]$errors)
if($errors){throw $errors}
$assignment=$ast.FindAll({param($n) $n -is [Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -ceq '$modelHttp' -and $n.Right.Extent.Text.StartsWith('if(')},$true)
if(@($assignment).Count -ne 1){throw 'Ambiguous actual HTTP dispatch'}
$condition=$assignment[0].Right.Find({param($n) $n -is [Management.Automation.Language.IfStatementAst]},$true).Clauses[0].Item1.Extent.Text
foreach($profile in @('t7-iw7-resident-static-v1','t7-iw7-resident-static-v2','unknown','T7-IW7-RESIDENT-STATIC-V2','original-cube')){
    $model=[pscustomobject]@{GeometryProfile=$profile}
    $selected=Invoke-Expression $condition
    $expected=$profile -cin @('t7-iw7-resident-static-v1','t7-iw7-resident-static-v2')
    if($selected -ne $expected){throw 'Actual factory dispatch differs'}
}
# Execute the actual pure five-input gate from the build wrapper, without its
# stock, admission or process body. This catches an accidentally v1-only gate.
$ast=[Management.Automation.Language.Parser]::ParseFile("$Repo/ops/model-lab/Build-ModelFF.ps1",[ref]$tokens,[ref]$errors)
if($errors){throw $errors}
$gate=$ast.FindAll({param($n) $n -is [Management.Automation.Language.IfStatementAst] -and $n.Extent.Text.Contains("throw 'Pinned five-input")},$true)
if(@($gate).Count -ne 1){throw 'Ambiguous build source gate'}
$plan=$valid;$planVersion=2;$sourceNames=@(Get-ModelFFSourceNames $plan)
Invoke-Expression $gate[0].Extent.Text
$planVersion=1;$refused=$false;try{Invoke-Expression $gate[0].Extent.Text}catch{$refused=$true}
if(!$refused){throw 'Crossed version accepted by actual build source gate'}
''')
            result = subprocess.run(['pwsh', '-NoProfile', '-File', str(script), str(ROOT), str(staged)],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rigid_http_explicit_bound_does_not_widen_legacy_routes(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'runtime') as folder:
            script = Path(folder) / 'http.ps1'
            script.write_text(r'''param($Repo,$Root)
$ErrorActionPreference='Stop'
Add-Type -Path "$Repo/ops/hud-lab/HudHttp.cs"
$bytes=[Text.Encoding]::UTF8.GetBytes(('SYNTHETIC HTTP ONLY' * 200))
$hash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes))
foreach($route in @([IW7HudHttp]::Route,[IW7HudHttp]::ModelRoute)){
    $refused=$false;try{[IW7HudHttp]::new($bytes,$hash,"$Root/legacy.jsonl",$route)}catch{$refused=$true}
    if(!$refused -or (Test-Path "$Root/legacy.jsonl")){throw 'Legacy route limit widened'}
}
$refused=$false;try{[IW7HudHttp]::CreateRigidModel($bytes,('A'*64),"$Root/wrong.jsonl")}catch{$refused=$true}
if(!$refused -or (Test-Path "$Root/wrong.jsonl")){throw 'Wrong rigid hash created listener/journal'}
# A single zeroed array exercises the actual upper-bound branch. Asset checks
# length before cloning or hashing, so no second large payload is allocated.
$oversize=[byte[]]::new(32MB+1)
$refused=$false;try{[IW7HudHttp]::CreateRigidModel($oversize,$hash,"$Root/oversize.jsonl")}catch{
    $refused=$_.Exception.ToString().Contains('exceeds its route-specific bound')
}
$oversize=$null
if(!$refused -or (Test-Path "$Root/oversize.jsonl")){throw 'Oversized rigid payload reached journal/listener'}
$http=[IW7HudHttp]::CreateRigidModel($bytes,$hash,"$Root/rigid.jsonl")
$client=[Net.Http.HttpClient]::new()
try{
    if($http.AssetRoute -cne [IW7HudHttp]::ModelRoute){throw 'Unexpected rigid route'}
    foreach($route in @([IW7HudHttp]::Route,[IW7HudHttp]::BeaconRoute,[IW7HudHttp]::SoundRoute,([IW7HudHttp]::ModelRoute+'?x=1'))){
        $response=$client.GetAsync($http.BaseUrl+$route).GetAwaiter().GetResult()
        if([int]$response.StatusCode -ne 404){throw 'Rigid HTTP served foreign route'}
        $response.Dispose()
    }
    $actual=$client.GetByteArrayAsync($http.BaseUrl+[IW7HudHttp]::ModelRoute).GetAwaiter().GetResult()
    if([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($actual)) -cne $hash -or $http.CompletedGets -ne 1){throw 'Rigid GET differs'}
}finally{$client.Dispose();$http.Dispose()}
if(!$http.Stopped){throw 'Synthetic HTTP worker remains active'}
''')
            result = subprocess.run(['pwsh', '-NoProfile', '-File', str(script), str(ROOT), folder], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()

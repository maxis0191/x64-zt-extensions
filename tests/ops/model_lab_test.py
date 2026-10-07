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
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('model_geometry', ROOT / 'ops/model-lab/geometry.py')
geometry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(geometry)


sys.path.insert(0,str(ROOT/'ops/model-lab'))
try:
    import prepare_writer
    import prepare_ff
finally:
    sys.path.pop(0)


class ModelSourceTests(unittest.TestCase):
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
            provenance.write_text(json.dumps(data))
            target=Path(folder)/'staged'
            plan=prepare_ff.stage(run,target)
            self.assertFalse(plan['ready']);self.assertFalse(plan['ff_built'])
            self.assertFalse(plan['material_payload_copied'])
            self.assertEqual(len(plan['expected_inventory']),5)
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


if __name__ == '__main__':
    unittest.main()

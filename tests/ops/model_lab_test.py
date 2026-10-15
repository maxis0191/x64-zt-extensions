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


def synthetic_native_run(provenance):
    """Mock of the existing writer receipt, never actual native evidence."""
    stages=[]
    for index,(name,kind,image,duration) in enumerate((('discovery','Fixture','vswhere.exe',15),
            ('compile','Compile','cl.exe',120),('fixture','Fixture','model-writer.exe',30))):
        image_hash=provenance['CompilerSHA256'] if name=='compile' else provenance['WriterSHA256'] if name=='fixture' else '7'*64
        stages.append(dict(Name=name,Stage=kind,ExitCode=0,TreeClosureConfirmed=True,ImageSHA256=image_hash,
            PlanSHA256='8'*64,DeadlineSeconds=duration,Identity=dict(PID=1001+index,Image='C:\\synthetic\\'+image,
            CreatedUtc='2026-10-15T00:00:00.0000000Z')))
    return dict(Schema='iw7.model-writer-native-run/1',Status='NativeRoundtripPassed',
        NativeRootKey=provenance['NativeRootKey'],SourcePin=provenance['SourcePin'],Source=copy.deepcopy(provenance['Source']),
        WriterSHA256=provenance['WriterSHA256'],CompilerSHA256=provenance['CompilerSHA256'],
        ReleasePending=True,LeaseReleased=False,TreeClosureConfirmed=True,Quarantined=False,Ready=False,Stages=stages)


class ModelSourceTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('pwsh'), 'PowerShell stock metadata fixture requires pwsh')
    def test_selected_stock_metadata_compares_exact_utc_instants(self):
        script = r'''
param($Entry,$Root)
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Entry,[ref]$tokens,[ref]$errors)
if($errors){throw 'Entry parse failed'}
$gates=@($ast.FindAll({param($n);$n -is [Management.Automation.Language.IfStatementAst] -and $n.Extent.Text.Contains("throw 'Observed stock metadata/mode changed.'") -and $n.Clauses[0].Item1.Extent.Text.Contains('$f.Length -ne $entry.Bytes')},$true))
if($gates.Count -ne 1){throw 'Unique actual stock metadata gate required'}
$gate=[scriptblock]::Create($gates[0].Extent.Text)
$path=Join-Path $Root 'authored-stock.bin'
[IO.File]::WriteAllText($path,'Authored metadata fixture')
[IO.File]::SetLastWriteTimeUtc($path,[datetime]::Parse('2026-09-29T21:46:19.4827250Z').ToUniversalTime())
$f=Get-Item -LiteralPath $path
$instant=[datetimeoffset]$f.LastWriteTimeUtc
function New-Entry {
    [pscustomobject]@{Bytes=$f.Length;ModifiedUtc=$f.LastWriteTimeUtc.ToString('o');Attributes=[int]$f.Attributes;Mode='HardLink'}
}
foreach($date in @($f.LastWriteTimeUtc.ToString('o'),$f.LastWriteTimeUtc,$instant,$instant.ToOffset([timespan]::FromHours(2)).ToString('o'))){
    $entry=New-Entry;$entry.ModifiedUtc=$date
    . $gate
}
# JSON may return a DateTime on newer PowerShell and a string on older versions.
# Both must preserve the instant, including optional trailing fractional zeros.
foreach($text in @($f.LastWriteTimeUtc.ToString('o'),'2026-09-29T21:46:19.482725Z')){
    $entry=New-Entry;$entry.ModifiedUtc=$text
    $entry=$entry|ConvertTo-Json|ConvertFrom-Json
    . $gate
}
foreach($case in @('tick','bytes','attributes','mode','malformed')){
    $entry=New-Entry
    switch($case){
        tick {$entry.ModifiedUtc=$instant.AddTicks(1).ToString('o')}
        bytes {$entry.Bytes++}
        attributes {$entry.Attributes=$entry.Attributes -bxor [int][IO.FileAttributes]::ReadOnly}
        mode {$entry.Mode='Invalid'}
        malformed {$entry.ModifiedUtc='not-a-date'}
    }
    $refused=$false;try{. $gate}catch{$refused=$true}
    if(!$refused){throw "Changed $case accepted"}
}
'''
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'stock-metadata.ps1'
            path.write_text(script, encoding='utf-8')
            result = subprocess.run(['pwsh', '-NoLogo', '-NoProfile', '-File', str(path),
                                     str(ROOT / 'ops/model-lab/Build-ModelFF.ps1'), folder],
                                    capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which('pwsh'), 'PowerShell stock selector fixture requires pwsh')
    def test_selected_stock_binding_is_explicitly_limited_to_render_only_candidate(self):
        script = r'''
param($Entry,$Root)
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Entry,[ref]$tokens,[ref]$errors)
if($errors){throw 'Entry parse failed'}
$selector=@($ast.FindAll({param($n);$n -is [Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -ceq '$renderOnlyStock'},$true))[0]
$block=@($ast.FindAll({param($n);$n -is [Management.Automation.Language.IfStatementAst] -and $n.Clauses[0].Item1.Extent.Text.Trim() -ceq '$StockBindingPlan'},$true))[0]
$repo=Join-Path $Root 'package';[IO.Directory]::CreateDirectory((Join-Path $repo 'tools-source/asset-bridge/common'))|Out-Null
[IO.File]::WriteAllText((Join-Path $repo 'tools-source/asset-bridge/common/StockBinding.Core.ps1'),'# Authored source import; no asset operations')
$StockBindingPlan=Join-Path $Root 'selected.json'
function Write-Fixture($SentinelMode='Copy'){
    $rows=@([pscustomobject]@{Relative='main/fileSysCheck.cfg';Mode=$SentinelMode})
    for($i=1;$i -lt 72;$i++){$rows+=[pscustomobject]@{Relative=('zone/authored-'+$i+'.ff');Mode='HardLink'}}
    @{stock_binding=@{inputs=$rows};runtime_verified=$false;ready=$false}|ConvertTo-Json -Depth 5|Set-Content $StockBindingPlan
    $script:StockBindingPlanSHA256=(Get-FileHash -LiteralPath $StockBindingPlan).Hash
}
function Invoke-ActualSelector {
    . ([scriptblock]::Create($selector.Extent.Text))
    . ([scriptblock]::Create($block.Extent.Text))
    @($inputs)
}
$arena=$false;$rigid=$true;$CandidateRoot='retained-candidate';$plan=[pscustomobject]@{geometry_profile='t7-iw7-selected-streamed-render-only-v2'}
Write-Fixture
if(@(Invoke-ActualSelector).Count -ne 72 -or $arena){throw 'Explicit render-only path must consume selected mapping without arena marker'}
foreach($profile in @('t7-iw7-resident-static-v1','t7-iw7-resident-static-v2','t7-iw7-selected-streamed-static-v1','unknown')){
    $plan.geometry_profile=$profile;$refused=$false
    try{Invoke-ActualSelector|Out-Null}catch{$refused=$_.Exception.Message -eq 'Explicit bounded original-arena stock binding required.'}
    if(!$refused){throw 'Unselected resident profile gained stock binding'}
}
$plan.geometry_profile='t7-iw7-selected-streamed-render-only-v2';$CandidateRoot='';$refused=$false
try{Invoke-ActualSelector|Out-Null}catch{$refused=$true};if(!$refused){throw 'Candidate selector required'}
$CandidateRoot='retained-candidate';Write-Fixture 'HardLink';$refused=$false
try{Invoke-ActualSelector|Out-Null}catch{$refused=$_.Exception.Message -eq 'Existing 72-input aliases and independent copied sentinel required.'}
if(!$refused){throw 'Independent copied sentinel must remain mandatory'}
Write-Fixture;$StockBindingPlanSHA256='1'*64;$refused=$false
try{Invoke-ActualSelector|Out-Null}catch{$refused=$true};if(!$refused){throw 'Binding digest must remain mandatory'}
Write-Fixture
$changed=Get-Content -LiteralPath $StockBindingPlan -Raw|ConvertFrom-Json
$changed.stock_binding.inputs[1].Mode='Copy'
$changed|ConvertTo-Json -Depth 5|Set-Content $StockBindingPlan
$refused=$false;try{Invoke-ActualSelector|Out-Null}catch{$refused=$true}
if(!$refused){throw 'Changed valid mapping mode must invalidate the pinned binding digest'}
Write-Fixture;$arena=$true;$rigid=$false;$plan.geometry_profile='iw7-original-arena-rigid-v1'
if(@(Invoke-ActualSelector).Count -ne 72){throw 'Original World stock selector changed'}
'''
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'selected-stock.ps1'
            path.write_text(script, encoding='utf-8')
            result = subprocess.run(['pwsh', '-NoLogo', '-NoProfile', '-File', str(path),
                                     str(ROOT / 'ops/model-lab/Build-ModelFF.ps1'), folder],
                                    capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which('pwsh'), 'PowerShell admission fixture requires pwsh')
    def test_resident_candidate_dry_run_defers_opaque_checks_until_lease(self):
        script = r'''
param($Entry,$Root)
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Entry,[ref]$tokens,[ref]$errors)
if($errors){throw 'Entry parse failed'}
$blocks=@($ast.FindAll({param($n);$n -is [Management.Automation.Language.IfStatementAst] -and $n.Clauses[0].Item1.Extent.Text.Trim() -ceq '$CandidateRoot'},$true))
$calls=@($ast.FindAll({param($n);$n -is [Management.Automation.Language.CommandAst] -and $n.GetCommandName() -ceq 'Assert-BeaconCandidate'},$true))
$admission=@($ast.FindAll({param($n);$n -is [Management.Automation.Language.CommandAst] -and $n.GetCommandName() -ceq 'Enter-IW7ResourceLease'},$true))[0]
$dry=@($ast.FindAll({param($n);$n -is [Management.Automation.Language.IfStatementAst] -and $n.Clauses[0].Item1.Extent.Text.Trim() -ceq '$DryRun'},$true))[0]
if($calls.Count -ne 1 -or $calls[0].Extent.StartOffset -le $admission.Extent.EndOffset -or $admission.Extent.StartOffset -le $dry.Extent.EndOffset){throw 'Candidate qualifier must follow DryRun and admission'}
$CandidateRoot=Join-Path $Root 'candidate';$repo=Join-Path $Root 'package'
[IO.Directory]::CreateDirectory((Join-Path $repo 'sdk/modding'))|Out-Null
[IO.Directory]::CreateDirectory((Join-Path $CandidateRoot 'bin'))|Out-Null
[IO.File]::WriteAllText((Join-Path $repo 'sdk/modding/BeaconFF.Core.ps1'),'# Authored import only')
$toolPath=Join-Path $CandidateRoot 'bin/zonetool-community.exe'
[IO.File]::WriteAllText($toolPath,'Authored original fake EXE')
$expected=(Microsoft.PowerShell.Utility\Get-FileHash -LiteralPath $toolPath).Hash.ToLowerInvariant()
$metadata=Join-Path $CandidateRoot 'build-artifact.local.json'
@{schema='iw7.zonetool-community-candidate/1';executable=@{path=$toolPath;sha256=$expected}}|ConvertTo-Json|Set-Content $metadata
$CandidateArtifactSHA256='1'*64;$ToolProvenance='';$NativeJobAssembly='';$arena=$false
$script:Admitted=$false;$script:OpaqueReads=0;$script:QualificationCalls=0
function Resolve-IW7BasePath($Base,$Relative){Join-Path $Base $Relative}
function Read-BeaconJson($Path,$Limit){Get-Content -LiteralPath $Path -Raw|ConvertFrom-Json}
function Assert-BeaconHash($Path,$SHA){if($Path -ine $metadata){throw 'Pre-admission opaque hash'}}
function Get-AppxPackage($Name){[pscustomobject]@{Version='1.2606.22001.0';InstallLocation=(Join-Path $Root 'authored-debugger')}}
function Get-FileHash($LiteralPath){
    if(!$script:Admitted){throw 'Opaque read before lease'}
    $script:OpaqueReads++
    if($LiteralPath -ieq $toolPath){return Microsoft.PowerShell.Utility\Get-FileHash -LiteralPath $LiteralPath}
    if($LiteralPath -like '*cdb.exe'){return [pscustomobject]@{Hash='5F54ABAFCA3AE5638BBF807D402FABB350A64575C1DFA9FBFC7F5732DF5BEE67'}}
    throw 'Unexpected opaque input'
}
function Assert-BeaconCandidate($Base,$SHA){
    if(!$script:Admitted){throw 'Qualifier called before lease'}
    $script:QualificationCalls++
    if((Get-FileHash $toolPath).Hash.ToLowerInvariant() -cne $expected){throw 'Pinned candidate EXE changed'}
    [pscustomobject]@{Path=$toolPath;SHA256=$expected}
}
. ([scriptblock]::Create($blocks[0].Extent.Text))
$preCdb=@($ast.FindAll({param($n);$n -is [Management.Automation.Language.IfStatementAst] -and $n.Clauses[0].Item1.Extent.Text.Trim() -ceq '!$CandidateRoot -or !$arena'},$true))[0]
. ([scriptblock]::Create($preCdb.Extent.Text))
$DryRun=$true;$RunRoot='authored-fresh-run';$inputs=@([pscustomobject]@{Relative='authored-input'});$sourceNames=@('authored-source');$reader=$null
$preview=& ([scriptblock]::Create($dry.Extent.Text))
if(($preview|ConvertFrom-Json).Ready -ne $false -or $script:OpaqueReads -ne 0 -or $script:QualificationCalls -ne 0){throw 'Candidate DryRun read opaque bytes'}
$qualifier=$calls[0];while($qualifier -and $qualifier -isnot [Management.Automation.Language.IfStatementAst]){$qualifier=$qualifier.Parent}
$script:Admitted=$true;$state=@{}
[IO.File]::WriteAllText($toolPath,'Authored changed fake EXE')
$refused=$false;try{. ([scriptblock]::Create($qualifier.Extent.Text))}catch{$refused=$_.Exception.Message -eq 'Pinned candidate EXE changed'}
if(!$refused -or $state.ContainsKey('CandidateQualifiedUnderLease') -or $script:OpaqueReads -ne 1){throw 'Changed candidate must refuse after admission'}
[IO.File]::WriteAllText($toolPath,'Authored original fake EXE')
. ([scriptblock]::Create($qualifier.Extent.Text))
$postCdb=@($ast.FindAll({param($n);$n -is [Management.Automation.Language.IfStatementAst] -and $n.Clauses[0].Item1.Extent.Text.Trim().StartsWith('$CandidateRoot -and !$arena -and')},$true))[0]
if($postCdb.Extent.StartOffset -le $admission.Extent.EndOffset){throw 'Candidate diagnostic hash must follow admission'}
. ([scriptblock]::Create($postCdb.Extent.Text))
if(!$state.CandidateQualifiedUnderLease -or $script:OpaqueReads -ne 3){throw 'Existing candidate and diagnostic checks must each run once'}
'''
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'candidate-admission.ps1'
            path.write_text(script, encoding='utf-8')
            result = subprocess.run(['pwsh', '-NoLogo', '-NoProfile', '-File', str(path),
                                     str(ROOT / 'ops/model-lab/Build-ModelFF.ps1'), folder],
                                    capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

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

    def test_resident_surface96_work_admission_boundaries(self):
        # Metadata-only fixtures exercise the real PowerShell admission gate.
        # Expected totals are independent fixed cases, not a copied calculator.
        def metadata(records, work):
            return {
                'schema': 'iw7.model-ff-plan/2',
                'geometry_profile': 't7-iw7-resident-static-v2',
                'model_name': 'synthetic/model', 'mesh_name': 'synthetic/mesh',
                'zone': 'paris_model_probe', 'recipient': 'cp_zmb',
                'material_payload_copied': False, 'has_lods': True,
                'lod0_dist': 1000000, 'shadow_cutoff_lod': 6, 'collision_lod': 255,
                'selected_counts': {'bones': 1, 'roots': 1, 'surfaces': len(records),
                                    'vertices': sum(v for v, _ in records),
                                    'triangles': sum(t for _, t in records)},
                'surface_records': [{'index': i, 'material_slot': i, 'vertices': v, 'triangles': t}
                                    for i, (v, t) in enumerate(records)],
                'material_references': [rigid_export.MATERIAL] * len(records),
                'geometry_work_bytes_upper_bound': work,
            }

        cases = []
        for label, records, expected in (
            ('minimum-one', [(3, 1)], 832),
            ('minimum-five', [(3, 1)] * 5, 3136),
            ('minimum-255', [(3, 1)] * 255, 147136),
            ('two-surfaces-face', [(5, 2), (3, 1)], 1540),
            ('exact-16MiB', [(44500, 10482)] * 5 + [(44500, 10478)], 16777216),
        ):
            cases.append({'label': label, 'accepted': True, 'metadata': metadata(records, expected)})
            # The old coefficient undercounted every logical surface by 16 B.
            cases.append({'label': label + '-old-claim', 'accepted': False,
                          'metadata': metadata(records, expected - 16 * len(records))})
        old_boundary = [(44500, 10482)] * 5 + [(44500, 10486)]
        cases.extend([
            {'label': 'old-boundary-corrected-over-96', 'accepted': False,
             'metadata': metadata(old_boundary, 16777312)},
            {'label': 'old-boundary-stale-16MiB-claim', 'accepted': False,
             'metadata': metadata(old_boundary, 16777216)},
            {'label': 'one-triangle-over', 'accepted': False,
             'metadata': metadata([(44500, 10482)] * 5 + [(44500, 10479)], 16777228)},
        ])
        legacy = metadata([(3, 1)], 832)
        legacy.update(schema='iw7.model-ff-plan/1', geometry_profile='t7-iw7-resident-static-v1',
                      material_reference=rigid_export.MATERIAL)
        for key in ('surface_records', 'material_references', 'geometry_work_bytes_upper_bound'):
            del legacy[key]
        cases.append({'label': 'v1-unchanged', 'accepted': True, 'metadata': legacy})
        crossed = copy.deepcopy(legacy)
        crossed['geometry_work_bytes_upper_bound'] = 832
        cases.append({'label': 'v1-cannot-claim-v2-work', 'accepted': False, 'metadata': crossed})
        with tempfile.TemporaryDirectory(dir=ROOT / 'runtime') as folder:
            base = Path(folder)
            (base / 'cases.json').write_text(json.dumps(cases), encoding='utf-8')
            script = base / 'surface96-work.ps1'
            script.write_text(r'''param($Repo,$Cases)
$ErrorActionPreference='Stop'
. "$Repo/ops/model-lab/ModelFF.Core.ps1"
foreach($case in (Get-Content -LiteralPath $Cases -Raw | ConvertFrom-Json)){
    $accepted=$true
    try{Assert-ModelFFRigidPlan $case.metadata}catch{$accepted=$false}
    if($accepted -ne $case.accepted){throw "Unexpected admission for $($case.label): $accepted"}
    if($accepted -and @(Get-ModelFFSourceNames $case.metadata).Count -ne 5){throw 'Source inventory changed'}
}
''', encoding='utf-8')
            result = subprocess.run(['pwsh', '-NoProfile', '-File', str(script), str(ROOT), str(base / 'cases.json')],
                                    capture_output=True, text=True, timeout=30)
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
            # New pending writer snapshots require final closure even on legacy route.
            data.update(NativeReleasePending=True,NativeRootKey='IW7.ModelWriter.Root.'+'b'*32,
                        NativeClosureEvidence='writer-closure.json',WriterSHA256='5'*64,CompilerSHA256='6'*64)
            provenance.write_text(json.dumps(data))
            pending=Path(folder)/'pending-no-closure'
            with self.assertRaises((FileNotFoundError,ValueError)):prepare_ff.stage(run,pending)
            self.assertFalse(pending.exists())
            native=json.dumps(synthetic_native_run(data)).encode()
            (run/'writer-native-run.json').write_bytes(native)
            closure=dict(Schema='iw7.model-writer-closure/1',NativeRootKey='IW7.ModelWriter.Root.'+'c'*32,
                JobClosureVerified=True,LeaseReleased=True,InputGuardsClosed=True,PreReleasePublicationsVerified=True,
                WriterProvenanceSHA256=hashlib.sha256(provenance.read_bytes()).hexdigest(),NativeRunSHA256=hashlib.sha256(native).hexdigest(),Ready=False)
            (run/'writer-closure.json').write_text(json.dumps(closure))
            with self.assertRaises(ValueError):prepare_ff.stage(run,pending)
            self.assertFalse(pending.exists())
            closure['NativeRootKey']=data['NativeRootKey']
            (run/'writer-closure.json').write_text(json.dumps(closure))
            closed_plan=prepare_ff.stage(run,Path(folder)/'pending-closed')
            self.assertEqual(len(closed_plan['source_files']),5)
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


class AuthoredRigidSourceTests(unittest.TestCase):
    @staticmethod
    def platform(name='creator_floor', material='creator/floor_material'):
        data = geometry.original_cube()
        data['name'] = name
        surface = data['surfaces'][0]
        surface['material_reference'] = material
        for vertex in surface['vertices']:
            x, y, z = vertex['position']
            vertex['position'] = [16*x, 16*y, z+8]
        data['bounds'] = {'midpoint': [0, 0, 8], 'half_size': [128, 128, 8]}
        return data

    @staticmethod
    def prism():
        data = geometry.original_cube()
        data['name'] = 'second_prism'
        points = [(-24, -16), (24, -16), (0, 24)]
        vertices, triangles = [], []
        for z, order, normal in ((0, (0, 2, 1), [0, 0, -1]), (48, (0, 1, 2), [0, 0, 1])):
            start = len(vertices)
            for index, uv in zip(order, ([0, 0], [1, 0], [.5, 1])):
                vertices.append(dict(position=[*points[index], z], normal=normal, uv=uv, bone=0, weight=1))
            triangles.append([start, start+1, start+2])
        import math
        for i, j in ((0, 1), (1, 2), (2, 0)):
            a, b = points[i], points[j]
            dx, dy = b[0]-a[0], b[1]-a[1]
            length = math.hypot(dx, dy)
            normal = [dy/length, -dx/length, 0]
            start = len(vertices)
            for position, uv in zip(([*a, 0], [*b, 0], [*b, 48], [*a, 48]),
                                    ([0, 0], [1, 0], [1, 1], [0, 1])):
                vertices.append(dict(position=position, normal=normal, uv=uv, bone=0, weight=1))
            triangles.extend(([start, start+1, start+2], [start, start+2, start+3]))
        data['surfaces'] = [dict(material_reference='second_diffuse', vertices=vertices, triangles=triangles)]
        data['bounds'] = {'midpoint': [0, 4, 24], 'half_size': [24, 20, 24]}
        return data

    @staticmethod
    def interfaces(folder):
        source = Path(folder)/'source'
        for name in prepare_writer.INTERFACES:
            path = source/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('Authored text interface fixture: '+name)
        return source

    def test_authored_platform_and_non_cube_prism_derive_bounds_and_half_uvs(self):
        for data, counts, bounds in ((self.platform(), (24, 12), ([0, 0, 8], [128, 128, 8])),
                                     (self.prism(), (18, 8), ([0, 4, 24], [24, 20, 24]))):
            before = copy.deepcopy(data)
            result = geometry.validate_authored(data, model_name=data['name'],
                                                material_reference=data['surfaces'][0]['material_reference'])
            self.assertEqual(data, before)
            surface = result['surfaces'][0]
            self.assertEqual((len(surface['vertices']), len(surface['triangles'])), counts)
            self.assertEqual(result['bounds'], dict(zip(('midpoint', 'half_size'), bounds)))
            self.assertEqual(len(geometry.authored_tangents(result)), counts[0])
            self.assertIs(result['ready'], False)
        self.assertEqual(geometry.packed_uv([.5, .25]), 0x34003800)
        self.assertEqual(geometry.packed_uv([1, 1]), 0x3c003c00)
        self.assertEqual(geometry.packed_uv([2**-24, 0]), 1)
        self.assertEqual(geometry.packed_uv([2**-25, 0]), 0)
        # Off-center fractional positions survive source generation, not one-decimal truncation.
        data = self.platform()
        for vertex in data['surfaces'][0]['vertices']:
            vertex['position'][0] += .125
        data['bounds']['midpoint'][0] = .125
        header = prepare_writer.authored_header(data, mesh_name='different_mesh')
        self.assertIn('128.125f', header)
        self.assertIn('probe_bounds_mid[3] = {0.125f, 0.0f, 8.0f}', header)

    def test_authored_bounds_enclose_serialized_float32_positions(self):
        vertices = [dict(position=[10.000001, -4, 0]), dict(position=[10.000002, 7, 3])]
        bounds = geometry.derived_bounds(vertices)
        for vertex in vertices:
            for axis, value in enumerate(vertex['position']):
                self.assertLessEqual(abs(geometry.float32(value)-bounds['midpoint'][axis]), bounds['half_size'][axis])

    def test_authored_rejects_invalid_data_and_claims_without_relaxing_legacy(self):
        mutations = (
            lambda d: d.__setitem__('name', '../model'),
            lambda d: d.__setitem__('name', 'CON'),
            lambda d: d.__setitem__('lods', True),
            lambda d: d.__setitem__('ready', True),
            lambda d: d.__setitem__('iw7_serialized', True),
            lambda d: d.__setitem__('extra', 'silently ignored input'),
            lambda d: d['bones'][0]['translation'].__setitem__(0, True),
            lambda d: d['bounds']['half_size'].__setitem__(0, 127),
            lambda d: d['surfaces'][0].__setitem__('material_reference', None),
            lambda d: d['surfaces'][0]['vertices'][0].__setitem__('bone', False),
            lambda d: d['surfaces'][0]['vertices'][0].__setitem__('weight', True),
            lambda d: d['surfaces'][0]['vertices'][0]['position'].__setitem__(0, 10**1000),
            lambda d: d['surfaces'][0]['vertices'][0]['position'].__setitem__(0, float('nan')),
            lambda d: d['surfaces'][0]['vertices'][0]['position'].__setitem__(0, 32769),
            lambda d: d['surfaces'][0]['vertices'][0]['normal'].__setitem__(0, .5),
            lambda d: d['surfaces'][0]['vertices'][0]['uv'].__setitem__(0, -.1),
            lambda d: d['surfaces'][0]['triangles'][0].reverse(),
            lambda d: d['surfaces'][0]['triangles'][0].__setitem__(0, True),
            lambda d: d['surfaces'][0]['triangles'][0].__setitem__(0, 24),
            lambda d: d['surfaces'][0]['vertices'].append(copy.deepcopy(d['surfaces'][0]['vertices'][0])),
            lambda d: d['surfaces'][0].__setitem__('vertices', d['surfaces'][0]['vertices']*9),
            lambda d: d['surfaces'][0].__setitem__('triangles', d['surfaces'][0]['triangles']*9),
            lambda d: d['surfaces'][0]['vertices'][1]['uv'].__setitem__(0, 1e-9),
            lambda d: [v['uv'].__setitem__(0, 1-v['uv'][0]) for v in d['surfaces'][0]['vertices']],
        )
        for mutation in mutations:
            data = self.platform()
            mutation(data)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                geometry.validate_authored(data)
        with self.assertRaises(ValueError):
            geometry.validate_authored(self.platform(), model_name='different')
        with self.assertRaises(ValueError):
            geometry.validate_authored(self.platform(), material_reference='different')
        geometry.validate(geometry.original_cube())
        with self.assertRaises(ValueError):
            geometry.validate(self.platform())

    def test_authored_preparation_adapts_existing_serializer_and_reader_for_two_projects(self):
        with tempfile.TemporaryDirectory() as folder:
            source = self.interfaces(folder)
            for number, data in enumerate((self.platform(), self.prism())):
                with self.subTest(model=data['name']):
                    input_path = Path(folder)/f'input{number}.json'
                    input_path.write_text(json.dumps(data))
                    output = Path(folder)/f'prepared{number}'
                    zone, mesh = f'zone_{number}', f'mesh_{number}'
                    material = data['surfaces'][0]['material_reference']
                    manifest = prepare_writer.prepare_authored(output, source, input_path, namespace=f'project_{number}',
                        zone=zone, mesh_name=mesh, material_reference=material, check_pin=False)
                    self.assertEqual(prepare_writer.verify_authored_preparation(output), manifest)
                    checked = subprocess.run([sys.executable, '-B', '-S', str(ROOT/'ops/model-lab/prepare_writer.py'),
                                              '--verify-authored', str(output)], capture_output=True, text=True, timeout=10)
                    self.assertEqual(checked.returncode, 0, checked.stderr)
                    self.assertEqual(json.loads(checked.stdout), manifest)
                    self.assertEqual(manifest['artifact_paths'], ['xmodel/'+data['name']+'.xmb', 'xsurface/'+mesh+'.xsb'])
                    self.assertEqual(manifest['bounds'], data['bounds'])
                    self.assertFalse(manifest['compiled'])
                    self.assertTrue(manifest['material_closure_required'])
                    self.assertFalse(manifest['material_payload_present'])
                    self.assertEqual((output/f'zone_source/{zone}.csv').read_text(),
                                     f'material,{material}\nxmodel,{data["name"]}\nnetconststrings,ncs_mdl_{zone}\n')
                    self.assertEqual(json.loads((output/f'netconststrings/ncs_mdl_{zone}.json').read_bytes())['stringList'], [data['name']])
                    writer = (output/'writer.cpp').read_text()
                    self.assertNotIn('paris_model_probe', writer)
                    self.assertIn('r.open(probe_mesh_path,false)', writer)
                    self.assertIn('d.open(probe_model_path,false)', writer)
                    self.assertIn('s.vertCount==probe_vertex_count && s.triCount==probe_triangle_count', writer)
                    self.assertIn('s.verts0.packedVerts0,probe_vertex_count', writer)
                    self.assertIn('v.texCoord.packed=probe_packed_uvs[i]', writer)
                    self.assertIn('Every position/packed UV/normal/tangent/color differs', writer)
                    with self.assertRaises(ValueError):
                        prepare_writer.prepare_authored(output, source, input_path, namespace='other',
                            zone=zone, mesh_name=mesh, material_reference=material, check_pin=False)

    def test_authored_recipe_refuses_source_tampering_even_with_updated_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            source = self.interfaces(folder)
            path = Path(folder)/'input.json'
            path.write_text(json.dumps(self.prism()))
            output = Path(folder)/'prepared'
            manifest = prepare_writer.prepare_authored(output, source, path, namespace='project', zone='zone',
                mesh_name='mesh', material_reference='second_diffuse', check_pin=False)
            original = (output/'writer.cpp').read_bytes()
            changed = original.replace(b'probe_vertex_count', b'wrong_count', 1)
            (output/'writer.cpp').write_bytes(changed)
            altered = copy.deepcopy(manifest)
            altered['writer_sha256'] = altered['source_files']['writer.cpp'] = hashlib.sha256(changed).hexdigest()
            (output/'writer-source.json').write_text(json.dumps(altered))
            with self.assertRaises(ValueError):
                prepare_writer.verify_authored_preparation(output)
            (output/'writer.cpp').write_bytes(original)
            for field in ('ready', 'compiled', 'material_payload_present', 'physics_serialized', 'geometry_roundtrip_verified'):
                altered = copy.deepcopy(manifest)
                altered[field] = True
                (output/'writer-source.json').write_text(json.dumps(altered))
                with self.subTest(field=field), self.assertRaises(ValueError):
                    prepare_writer.verify_authored_preparation(output)
            (output/'writer-source.json').write_text(json.dumps(manifest))
            self.assertEqual(prepare_writer.verify_authored_preparation(output), manifest)

    def test_authored_refuses_template_drift_and_bad_inputs_before_output(self):
        template = (ROOT/'ops/model-lab/writer.cpp').read_text()
        with self.assertRaises(ValueError):
            prepare_writer.adapt_authored_writer(template.replace('s.vertCount==24', 's.vertCount==25'), {})
        with tempfile.TemporaryDirectory() as folder:
            source = self.interfaces(folder)
            path = Path(folder)/'input.json'
            path.write_text(json.dumps(self.platform()))
            for namespace in ('../escape', 'x'*64, 'COM1', ''):
                output = Path(folder)/'refused'
                with self.subTest(namespace=namespace), self.assertRaises(ValueError):
                    prepare_writer.prepare_authored(output, source, path, namespace=namespace,
                        zone='zone', mesh_name='mesh', material_reference='creator/floor_material', check_pin=False)
                self.assertFalse(output.exists())
            path.write_bytes(b' '* (512*1024+1))
            with self.assertRaises(ValueError):
                prepare_writer.prepare_authored(Path(folder)/'oversized', source, path, namespace='project',
                    zone='zone', mesh_name='mesh', material_reference='creator/floor_material', check_pin=False)

    @unittest.skipUnless(shutil.which('pwsh'), 'PowerShell source-block fixture requires pwsh')
    def test_existing_build_wrapper_keeps_profile_and_native_report_gates(self):
        script = r'''
param($Entry)
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Entry,[ref]$tokens,[ref]$errors)
if($errors){throw 'Build-Writer parse failed'}
$blocks=@($ast.FindAll({param($n);$n -is [Management.Automation.Language.IfStatementAst] -and $n.Clauses[0].Item1.Extent.Text.Trim() -ceq '$authored' -and ($n.Extent.Text.Contains('Authored writer source recipe differs.') -or $n.Extent.Text.Contains('Authored roundtrip $field differs from source.'))},$true))
if($blocks.Count -ne 2){throw 'Expected source recipe and native report gates'}
# Execute the actual native-report gate with authored metadata only. No native invocation.
$gate=[scriptblock]::Create($blocks[1].Extent.Text)
$authored=$true
$manifest=[pscustomobject]@{geometry_profile='iw7-authored-rigid-v1';namespace='second';zone='zone2';model_name='prism';mesh_name='mesh2';material_reference='author/material';vertices=18;triangles=8}
function New-Report {
    $row=@{};foreach($p in $manifest.PSObject.Properties){$row[$p.Name]=$p.Value}
    $row.bones=1;$row.surfaces=1;$row.lods=1;$row.physics_serialized=$false
    $row.geometry_roundtrip_verified=$true;$row.read_existing_supported=$true;$row.iw7_normal_encoding_verified=$false
    [pscustomobject]$row
}
$roundtrip=New-Report;. $gate
foreach($field in @('geometry_profile','namespace','zone','model_name','mesh_name','material_reference','vertices','triangles','physics_serialized','read_existing_supported','iw7_normal_encoding_verified')){
    $roundtrip=New-Report
    switch($field){
        vertices {$roundtrip.$field='18'}
        triangles {$roundtrip.$field=$true}
        physics_serialized {$roundtrip.$field=0}
        read_existing_supported {$roundtrip.$field='true'}
        iw7_normal_encoding_verified {$roundtrip.$field=$true}
        default {$roundtrip.$field='different'}
    }
    $refused=$false;try{. $gate}catch{$refused=$true}
    if(!$refused){throw "Changed authored $field accepted"}
}
$roundtrip=$null;$authored=$false;. $gate
$assignment=@($ast.FindAll({param($n);$n -is [Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -ceq '$artifactNames'},$true))
if($assignment.Count -ne 1){throw 'One artifact path selection required'}
. ([scriptblock]::Create($assignment[0].Extent.Text))
if(($artifactNames -join '|') -cne 'xmodel/paris_model_probe.xmb|xsurface/paris_model_probe_lod0.xsb'){throw 'Legacy paths changed'}
$authored=$true;$manifest|Add-Member NoteProperty artifact_paths @('xmodel/prism.xmb','xsurface/mesh2.xsb')
. ([scriptblock]::Create($assignment[0].Extent.Text))
if(($artifactNames -join '|') -cne 'xmodel/prism.xmb|xsurface/mesh2.xsb'){throw 'Authored paths not propagated'}
'''
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'source-gates.ps1'
            path.write_text(script, encoding='utf-8')
            result = subprocess.run(['pwsh', '-NoLogo', '-NoProfile', '-File', str(path),
                                     str(ROOT/'ops/model-lab/Build-Writer.ps1')],
                                    capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)

    @unittest.skipUnless(shutil.which('pwsh') and (ROOT/'ops/Lab-Paths.ps1').is_file(),
                         'Composed source with ordinary-path helper required')
    def test_writer_tool_source_override_keeps_legacy_pin_and_ordinary_path_gates(self):
        script = r'''
param($Repo,$Fixture,$ManifestPath)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. "$Repo/ops/Lab-Paths.ps1"
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile("$Repo/ops/model-lab/Build-Writer.ps1",[ref]$tokens,[ref]$errors)
if($errors){throw 'Writer entry parse failed'}
$selectors=@($ast.FindAll({param($n);$n -is [Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -ceq '$source'},$true))
if($selectors.Count -ne 1){throw 'One source directory selection required'}
$selector=[scriptblock]::Create($selectors[0].Extent.Text)
$repo=Join-Path $Fixture 'package'
$ToolSource=$null;. $selector
if($source -cne (Join-Path $repo 'tools/x64-zt-enemy')){throw 'Legacy default changed'}
$ToolSource=Join-Path $Fixture 'source';. $selector
if($source -cne [IO.Path]::GetFullPath($ToolSource)){throw 'Explicit source override not selected exactly'}
foreach($bad in @((Join-Path $Fixture 'missing'),$ManifestPath)){
    $ToolSource=$bad;$refused=$false;try{. $selector}catch{$refused=$true}
    if(!$refused){throw 'Missing/file source path accepted'}
}
$ToolSource=Join-Path $Fixture 'source';. $selector
$manifest=Get-Content -LiteralPath $ManifestPath -Raw|ConvertFrom-Json
$pin=@($ast.FindAll({param($n);$n -is [Management.Automation.Language.IfStatementAst] -and $n.Extent.Text.Contains("throw 'Exact pinned tool source required.'")},$true))
$hashes=@($ast.FindAll({param($n);$n -is [Management.Automation.Language.ForEachStatementAst] -and $n.Condition.Extent.Text -ceq '$manifest.source_hashes.PSObject.Properties' -and $n.Extent.Text.Contains('Pinned source interface changed after preparation.')},$true))
if($pin.Count -ne 1 -or $hashes.Count -ne 1){throw 'Actual pin and ten-interface gates required'}
# Exercise the actual production pin gate; no native Git/SDK/compiler probing.
$LASTEXITCODE=0;$head=$manifest.source_pin
. ([scriptblock]::Create($pin[0].Extent.Text))
$head='0'*40;$refused=$false;try{. ([scriptblock]::Create($pin[0].Extent.Text))}catch{$refused=$true}
if(!$refused){throw 'Wrong source pin accepted'}
. ([scriptblock]::Create($hashes[0].Extent.Text))
$first=@($manifest.source_hashes.PSObject.Properties)[0]
[IO.File]::AppendAllText((Join-Path $source $first.Name),' changed')
$refused=$false;try{. ([scriptblock]::Create($hashes[0].Extent.Text))}catch{$refused=$true}
if(!$refused){throw 'Changed source interface accepted'}
'''
        with tempfile.TemporaryDirectory() as folder:
            source = self.interfaces(folder)
            manifest = dict(source_pin=prepare_writer.PIN,
                            source_hashes=prepare_writer.source_hashes(source, check_pin=False))
            path = Path(folder)/'manifest.json'
            path.write_text(json.dumps(manifest))
            entry = Path(folder)/'source-root-gates.ps1'
            entry.write_text(script, encoding='utf-8')
            result = subprocess.run(['pwsh','-NoLogo','-NoProfile','-File',str(entry),str(ROOT),folder,str(path)],
                                    capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)


class WriterExecutionSourceTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('pwsh') and (ROOT/'ops/Lab-Paths.ps1').is_file(),
                         'Composed source ordinary-path helper required')
    def test_actual_writer_dry_run_cannot_probe_sdk_hash_pe_or_admit(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            package=base/'package'
            lab=package/'ops/model-lab'
            lab.mkdir(parents=True)
            for name in ('Build-Writer.ps1','prepare_writer.py','geometry.py','writer.cpp'):
                shutil.copyfile(ROOT/'ops/model-lab'/name,lab/name)
            shutil.copyfile(ROOT/'ops/Lab-Paths.ps1',package/'ops/Lab-Paths.ps1')
            (package/'ops/Resource-Scheduler.Core.ps1').write_text(
                "function Enter-IW7ResourceLease {throw 'TEST: admission forbidden'}\n"
                "function Invoke-IW7ResourceJob {throw 'TEST: nested admission forbidden'}\n")
            source=AuthoredRigidSourceTests.interfaces(base)
            path=base/'mesh.json';path.write_text(json.dumps(AuthoredRigidSourceTests.prism()))
            prepared=package/'runtime/prepared'
            prepare_writer.prepare_authored(prepared,source,path,namespace='project',zone='project',mesh_name='mesh',
                material_reference='second_diffuse',check_pin=False)
            script=base/'dry-run.ps1'
            script.write_text(r'''
param($Package,$Prepared,$Tool,$Fixture)
$ErrorActionPreference='Stop'
function global:git {
    $global:LASTEXITCODE=0
    if($args -contains 'rev-parse'){'fab935826c898806855376662a8a03317b3ad8f1'}
}
function global:Get-ItemProperty {throw 'TEST: SDK probe forbidden'}
function global:Get-FileHash {
    param($LiteralPath,$Algorithm='SHA256')
    if(![IO.Path]::GetFullPath($LiteralPath).StartsWith($Fixture+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'TEST: foreign/opaque hash forbidden'}
    Microsoft.PowerShell.Utility\Get-FileHash -LiteralPath $LiteralPath -Algorithm $Algorithm
}
$rows=@(& "$Package/ops/model-lab/Build-Writer.ps1" -PreparedRoot $Prepared -ToolSource $Tool -Python python -DryRun)
$result=($rows -join [Environment]::NewLine)|ConvertFrom-Json
if($result.Schema -cne 'iw7.model-writer-admission/1' -or !$result.SDKDiscoveryDeferred -or
    $result.LeaseAcquired -or $result.NativeTypesLoaded -or $result.BinaryInputsHashed -or $null -ne $result.Compiler){throw 'Source-only preview contract differs'}
if(Test-Path -LiteralPath (Join-Path $Prepared 'writer-native-run.json')){throw 'Preview created native run state'}
$result|ConvertTo-Json
''',encoding='utf-8')
            result=subprocess.run(['pwsh','-NoLogo','-NoProfile','-File',str(script),str(package),str(prepared),str(source),str(base)],
                                  capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertTrue(json.loads(result.stdout)['SDKDiscoveryDeferred'])

    @unittest.skipUnless(shutil.which('pwsh'), 'PowerShell source AST required')
    def test_single_admission_precedes_discovery_and_h1_owns_all_phases(self):
        script=r'''
param($Entry)
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Entry,[ref]$tokens,[ref]$errors)
if($errors){throw 'Writer parse failed'}
$calls=@($ast.FindAll({param($n);$n -is [Management.Automation.Language.CommandAst]},$true))
$admit=@($calls|Where-Object {$_.GetCommandName() -ceq 'Enter-IW7ResourceLease'})
if($admit.Count -ne 1 -or @($calls|Where-Object {$_.GetCommandName() -ceq 'Invoke-IW7ResourceJob'}).Count){throw 'One admission and no nested wrapper required'}
$entryText=[IO.File]::ReadAllText($Entry)
if($entryText.IndexOf('[AppDomain]::CurrentDomain.SetData($writerRoot.Key,$writerRoot)') -ge $admit[0].Extent.StartOffset){throw 'Actual root must be published before admission'}
$preview=@($ast.FindAll({param($n);$n -is [Management.Automation.Language.IfStatementAst] -and $n.Clauses[0].Item1.Extent.Text.Trim() -ceq '$DryRun'},$true))
if($preview.Count -ne 1 -or $preview[0].Extent.EndOffset -ge $admit[0].Extent.StartOffset){throw 'Preview must return before admission'}
foreach($call in @($calls|Where-Object {$_.GetCommandName() -cin @('Get-ItemProperty','Add-Type','Invoke-ModelWriterPhase')})){
    if($call.Extent.StartOffset -le $admit[0].Extent.EndOffset){throw 'SDK/native phase before admission'}
}
$phases=@($calls|Where-Object {$_.GetCommandName() -ceq 'Invoke-ModelWriterPhase'})
if($phases.Count -ne 3){throw 'Discovery, compiler and writer must use the same H1 path'}
if(@($calls|Where-Object {$_.GetCommandName() -ceq 'Invoke-T7OwnedStage'}).Count -ne 1){throw 'Existing H1 stage dispatcher required'}
$complete=@($calls|Where-Object {$_.GetCommandName() -ceq 'Complete-H1Stage'})
if($complete.Count -ne 1 -or !$complete[0].Extent.Text.Contains('-BeforeReleaseCheck')){throw 'Guard closure must precede the one release'}
'''
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source-order.ps1';path.write_text(script,encoding='utf-8')
            result=subprocess.run(['pwsh','-NoLogo','-NoProfile','-File',str(path),str(ROOT/'ops/model-lab/Build-Writer.ps1')],
                                  capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    @unittest.skipUnless(shutil.which('pwsh'), 'PowerShell source lifecycle fixture required')
    def test_actual_root_survives_publication_refusal_and_group_deadline_prevents_factory(self):
        script=r'''
param($Repo,$Fixture)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. "$Repo/tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1"
$realPublisher=${function:Write-H1Receipt};$realReadback=${function:Assert-H1ReceiptBytes}
function Exit-IW7ResourceLease {throw 'Release must not run after refused publication'}
function Get-H1Clock {$script:clock}
$script:T7H1Deadline=${function:Assert-H1Deadline};$script:T7GroupStarted=0
$text=[IO.File]::ReadAllText("$Repo/ops/model-lab/Build-Writer.ps1")
$start=$text.IndexOf('$writerRoot=');$end=$text.IndexOf('function Add-ModelWriterPin',$start)
$helpers=[scriptblock]::Create($text.Substring($start,$end-$start))
foreach($mode in @('write','readback','expired','late-factory')){
    $prepared=Join-Path $Fixture $mode;[IO.Directory]::CreateDirectory($prepared)|Out-Null
    $writerContext=[pscustomobject]@{Owner=$null;Closed=$true;Lease=[pscustomobject]@{Token=$mode};Guards=[Collections.Generic.List[IDisposable]]::new()}
    $originalContextVariable=Get-Variable writerContext;$bindings=[Collections.Generic.List[object]]::new()
    $state=[ordered]@{LeaseToken=$mode;LeaseReleased=$false;Quarantined=$false;Status='Pending';TreeClosureConfirmed=$true}
    $plan=[pscustomobject]@{RunRoot=$prepared;OutputLimitBytes=128KB;MetadataReserveBytes=64KB;GroupDeadlineSeconds=180}
    $script:clock=0;$script:factories=0;$script:constructed=$null
    function New-H1Owner {$script:factories++;$script:constructed=[pscustomobject]@{Original=$true};if($mode -ceq 'late-factory'){$script:clock=180001};$script:constructed}
    . $helpers
    $root=[AppDomain]::CurrentDomain.GetData($writerRoot.Key)
    if(![object]::ReferenceEquals($root.Context,$writerContext) -or ![object]::ReferenceEquals($root.ContextVariable.Value,$writerContext)){throw 'Root/PSVariable are not the actual original references'}
    $sameLease=$writerContext.Lease;$sameGuards=$writerContext.Guards
    if($mode -cin @('write','readback')){
        ${function:Write-H1Receipt}=$realPublisher;${function:Assert-H1ReceiptBytes}=$realReadback
        if($mode -ceq 'write'){function Write-H1Receipt {throw 'Injected write refusal'}}
        else{function Assert-H1ReceiptBytes {throw 'Injected readback refusal'}}
        Complete-H1Stage $writerContext $state -BeforeReleaseCheck {$null=Publish-ModelWriterReceipt ([ordered]@{Status='ReleasePending'}) 'writer-native-run.json'}
        if($state.LeaseReleased -or ![object]::ReferenceEquals($sameLease,$writerContext.Lease) -or
            ![object]::ReferenceEquals($sameGuards,$root.Guards) -or $root.CanExit -or !$state.Quarantined){throw 'Publication failure lost original root/lease/guards'}
    }else{
        if($mode -ceq 'expired'){$script:clock=180001}
        $refused=$false;try{New-H1Owner|Out-Null}catch{$refused=$true}
        if(!$refused -or $writerRoot.CanExit){throw 'Expired group allowed a new native effect'}
        if($mode -ceq 'expired' -and $script:factories -ne 0){throw 'Expired group called the factory'}
        if($mode -ceq 'late-factory' -and ![object]::ReferenceEquals($writerContext.Owner,$script:constructed)){throw 'Late factory result was not retained before refusing Start'}
    }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'publication-lifecycle.ps1';path.write_text(script,encoding='utf-8')
            result=subprocess.run(['pwsh','-NoLogo','-NoProfile','-File',str(path),str(ROOT),folder],
                                  capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)


class AuthoredFFSourceTests(unittest.TestCase):
    @staticmethod
    def fixture(folder, *, prism=False):
        producer, inspector = prepare_ff.authored_surfaces()
        mesh = AuthoredRigidSourceTests.prism() if prism else AuthoredRigidSourceTests.platform()
        zone = 'second_prism_zone' if prism else 'first_floor_zone'
        model, material_name = mesh['name'], mesh['surfaces'][0]['material_reference']
        source = AuthoredRigidSourceTests.interfaces(folder)
        geometry_path = Path(folder)/'geometry.input.json'
        geometry_path.write_text(json.dumps(mesh))
        writer = Path(folder)/'writer'
        manifest = prepare_writer.prepare_authored(writer, source, geometry_path, namespace=zone, zone=zone,
            mesh_name=model+'_mesh', material_reference=material_name, check_pin=False)
        # Authored source-only fixture receipts, not actual native build evidence.
        entries = []
        for path in manifest['artifact_paths']:
            raw = ('Authored synthetic geometry fixture '+path).encode()
            file = writer/'artifacts'/path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(raw)
            entries.append(dict(Path=path, Bytes=len(raw), SHA256=hashlib.sha256(raw).hexdigest()))
        report = {key: manifest[key] for key in ('geometry_profile','namespace','zone','model_name','mesh_name','material_reference','vertices','triangles')}
        report.update(schema='iw7.model-roundtrip/1', bones=1, surfaces=1, lods=1, shadow_cutoff_lod=6,
            collision_lod=255, lod0_dist=1000000, has_lods=True, geometry_roundtrip_verified=True,
            read_existing_supported=True, iw7_normal_encoding_verified=False, physics_serialized=False,
            ff_built=False, pixels_verified=False, ready=False)
        provenance = dict(Schema='iw7.model-writer-build/1',SourcePin=prepare_writer.PIN,Source=manifest,
            WriterSHA256='5'*64, CompilerSHA256='6'*64, Artifacts=entries, Roundtrip=report, FFBuilt=False, PixelsVerified=False, Ready=False)
        (writer/'writer-provenance.json').write_text(json.dumps(provenance))
        material = {key: 0 for key in inspector.BYTE_FIELDS}
        texture = dict(firstCharacter=0,lastCharacter=0,semantic=14,samplerState=0,typeHash=0,image='old_diffuse')
        normal = dict(texture, semantic=15, image='recipient_normal')
        material.update(surfaceTypeBits=0, stateFlags=0, **{'techniqueSet->name': 'recipient_technique'},
            textureTable=[normal, texture], constantTable=None, subMaterials=None)
        mapping = [dict(loadBits=[0]*6,depthStencilStateBits=[0]*14,blendStateBits=[0]*4,rasterizerState=0)]
        template = dict(material=json.dumps(material).encode(), statebits=bytes(152), statebitsmap=json.dumps(mapping).encode())
        image_name = 'prism_color' if prism else 'floor_color'
        inputs = producer.prepare_material(zone=zone,image_name=image_name,material_name=material_name,
            texture_slot=1,dds=producer.rgba8_dds(3,2,bytes(range(24))),template=template)
        return writer, inputs

    def test_two_projects_join_local_material_closure_and_parametric_inventory(self):
        for prism in (False, True):
            with self.subTest(prism=prism), tempfile.TemporaryDirectory() as folder:
                writer, material = self.fixture(folder, prism=prism)
                output = Path(folder)/'ff-source'
                plan = prepare_ff.stage_authored(writer, output, material_inputs=material)
                self.assertEqual(prepare_ff.verify_authored_stage(output), plan)
                self.assertEqual(plan['schema'], 'iw7.model-ff-plan/3')
                self.assertTrue(plan['material_payload_copied'])
                self.assertFalse(plan['material_closure_verified'])
                self.assertFalse(plan['ff_built'])
                self.assertFalse(plan['ready'])
                rows = (output/f'zone_source/{plan["zone"]}.csv').read_text()
                self.assertIn('material,'+plan['material_reference']+'\n', rows)
                self.assertIn('xmodel,'+plan['model_name']+'\n', rows)
                recipient = (output/f'zone_source/{plan["zone"]}_recipient.csv').read_text()
                self.assertEqual(recipient, 'techset,recipient_technique\nimage,recipient_normal\n')
                self.assertNotIn(plan['material_reference'], recipient)
                self.assertEqual((output/f'images/{plan["image"]["name"]}.dds').read_bytes(),
                                 material['files'][f'images/{plan["image"]["name"]}.dds'])
                self.assertEqual(len(plan['source_files']), 9)
                self.assertEqual(len(plan['dump_files']), 6)
                checked = subprocess.run([sys.executable,'-B','-S',str(ROOT/'ops/model-lab/prepare_ff.py'),
                    '--verify-authored-stage',str(output)],capture_output=True,text=True,timeout=10)
                self.assertEqual(checked.returncode,0,checked.stderr)
                self.assertEqual(json.loads(checked.stdout),plan)

    def test_join_refuses_false_writer_provenance_material_aliases_and_updated_hashes(self):
        with tempfile.TemporaryDirectory() as folder:
            writer, material = self.fixture(folder)
            original = (writer/'writer-provenance.json').read_bytes()
            for field, value in (('geometry_roundtrip_verified',False),('vertices',18),('material_reference','different')):
                report = json.loads(original)
                report['Roundtrip'][field] = value
                (writer/'writer-provenance.json').write_text(json.dumps(report))
                with self.subTest(field=field), self.assertRaises(ValueError):
                    prepare_ff.stage_authored(writer, Path(folder)/'refused',material_inputs=material)
                self.assertFalse((Path(folder)/'refused').exists())
            (writer/'writer-provenance.json').write_bytes(original)
            bad = copy.deepcopy(material)
            bad['recipient_references']['images'].append(bad['image']['name'])
            with self.assertRaises(ValueError):
                prepare_ff.stage_authored(writer,Path(folder)/'refused',material_inputs=bad)
            output = Path(folder)/'ff-source'
            plan = prepare_ff.stage_authored(writer,output,material_inputs=material)
            image_path = f'images/{plan["image"]["name"]}.dds'
            raw = (output/image_path).read_bytes()
            (output/image_path).write_bytes(raw[:-1]+b'\xff')
            plan['source_files'][image_path] = hashlib.sha256((output/image_path).read_bytes()).hexdigest()
            (output/'model-ff-plan.json').write_text(json.dumps(plan))
            with self.assertRaises(ValueError):
                prepare_ff.verify_authored_stage(output)

    def test_new_pre_release_writer_receipts_require_hash_bound_final_closure(self):
        with tempfile.TemporaryDirectory() as folder:
            writer,material=self.fixture(folder)
            path=writer/'writer-provenance.json';provenance=json.loads(path.read_bytes())
            provenance.update(NativeReleasePending=True,NativeRootKey='IW7.ModelWriter.Root.'+'a'*32,
                              NativeClosureEvidence='writer-closure.json')
            path.write_text(json.dumps(provenance))
            with self.assertRaises((FileNotFoundError,ValueError)):
                prepare_ff.stage_authored(writer,Path(folder)/'missing-closure',material_inputs=material)
            native=json.dumps(synthetic_native_run(provenance)).encode()
            (writer/'writer-native-run.json').write_bytes(native)
            closure=dict(Schema='iw7.model-writer-closure/1',NativeRootKey=provenance['NativeRootKey'],
                JobClosureVerified=True,LeaseReleased=True,InputGuardsClosed=True,PreReleasePublicationsVerified=True,
                NativeRunSHA256=hashlib.sha256(native).hexdigest(),WriterProvenanceSHA256=hashlib.sha256(path.read_bytes()).hexdigest(),Ready=False)
            closure_path=writer/'writer-closure.json';closure_path.write_text(json.dumps(closure))
            output=Path(folder)/'ff-source-two-phase'
            plan=prepare_ff.stage_authored(writer,output,material_inputs=material)
            self.assertEqual(prepare_ff.verify_authored_stage(output),plan)
            good_native=json.loads(native)
            changes=(lambda d:d.pop('Schema'),lambda d:d.__setitem__('NativeRootKey','IW7.ModelWriter.Root.'+'f'*32),
                lambda d:d.__setitem__('Status','Failed'),lambda d:d['Source'].__setitem__('name','foreign_model'),
                lambda d:d.__setitem__('WriterSHA256','9'*64),lambda d:d['Stages'].reverse(),
                lambda d:d['Stages'].pop(),lambda d:d['Stages'][0]['Identity'].__setitem__('PID',True))
            invalid_bytes=[b'not JSON',b'{"ReleasePending":true,"LeaseReleased":false}']
            for change in changes:
                invalid=copy.deepcopy(good_native);change(invalid);invalid_bytes.append(json.dumps(invalid).encode())
            for index,raw in enumerate(invalid_bytes):
                (writer/'writer-native-run.json').write_bytes(raw)
                closure['NativeRunSHA256']=hashlib.sha256(raw).hexdigest();closure_path.write_text(json.dumps(closure))
                refused=Path(folder)/f'invalid-native-{index}'
                with self.subTest(index=index),self.assertRaises(ValueError):
                    prepare_ff.stage_authored(writer,refused,material_inputs=material)
                self.assertFalse(refused.exists())
            (writer/'writer-native-run.json').write_bytes(native)
            closure['NativeRunSHA256']=hashlib.sha256(native).hexdigest()
            closure['LeaseReleased']=False;closure_path.write_text(json.dumps(closure))
            with self.assertRaises(ValueError):
                prepare_ff.stage_authored(writer,Path(folder)/'false-closure',material_inputs=material)

    def test_dump_verification_reuses_image_reader_and_rejects_material_or_pixels(self):
        with tempfile.TemporaryDirectory() as folder:
            writer, material = self.fixture(folder)
            output = Path(folder)/'ff-source'
            plan = prepare_ff.stage_authored(writer,output,material_inputs=material)
            dumped = Path(folder)/'dump'
            for name in plan['dump_files']:
                if name.startswith('images/') or name in plan['artifact_paths']:
                    continue
                path = dumped/name
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes((output/name).read_bytes())
            # Reuse the existing surfaces fixture's known IW7 image-record builder.
            spec = importlib.util.spec_from_file_location('_authored_ff_image_fixture',ROOT/'tools-source/asset-bridge/surfaces/test_authored_dds_material.py')
            fixture = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(fixture)
            image = plan['image']
            raw = fixture.iw7_dump(3,2,28,bytes(range(24)),image['name'],image['iw7_semantic'])
            image_path = dumped/f'images/{image["name"]}.iw7Image'
            image_path.parent.mkdir(parents=True)
            image_path.write_bytes(raw)
            ff = Path(folder)/'fixture.ff'
            ff.write_bytes(b'Authored FF fixture only; no engine build')
            result = prepare_ff.verify_authored_dump(output,dumped,ff)
            self.assertTrue(result['image']['serialized_pixel_bytes_verified'])
            self.assertTrue(result['material_fields_verified'])
            self.assertFalse(result['native_cbt_semantics_verified'])
            self.assertFalse(result['pixels_rendered_verified'])
            self.assertFalse(result['ready'])
            image_path.write_bytes(raw[:-1]+b'\xff')
            with self.assertRaises(ValueError):
                prepare_ff.verify_authored_dump(output,dumped,ff)
            image_path.write_bytes(raw)
            path = dumped/f'materials/{plan["material_reference"]}.json'
            data = json.loads(path.read_bytes())
            data['textureTable'][1]['image'] = 'different_image'
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                prepare_ff.verify_authored_dump(output,dumped,ff)

    @unittest.skipUnless(shutil.which('pwsh'), 'PowerShell source fixture requires pwsh')
    def test_existing_ff_plan_inventory_and_admission_dispatch_keep_legacy_strict(self):
        script = r'''
param($Repo,$PlanPath)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. "$Repo/ops/model-lab/ModelFF.Core.ps1"
$plan=Get-Content -LiteralPath $PlanPath -Raw|ConvertFrom-Json
# Actual caller strict mode: the legacy plan has NO geometry_profile property.
$legacyPlan=[pscustomobject]@{schema='iw7.model-ff-plan/1'}
$legacyNames=@(Get-ModelFFSourceNames $legacyPlan)
if($legacyNames.Count -ne 5 -or $legacyNames[0] -cne 'xmodel/paris_model_probe.xmb' -or $legacyNames[4] -cne 'netconststrings/ncs_mdl_paris_model_probe.json'){throw 'Strict legacy source inventory changed'}
$names=@(Get-ModelFFSourceNames $plan)
if($names.Count -ne 9 -or $names[0] -cne $plan.artifact_paths[0]){throw 'Authored exact input closure not selected'}
$lines=@('Loading zone "'+$plan.zone+'"')+@($plan.expected_inventory|ForEach-Object {'Loading asset "'+$_.name+'" of type '+$_.type+'.'})
$log=$lines -join [Environment]::NewLine
if(@(Get-ModelFFInventory $log -AuthoredPlan $plan).Count -ne 8){throw 'Authored inventory not accepted'}
foreach($changed in @($log.Replace('material "','bad "'),$log.Replace('material.','image.'),$log.Replace('Loading zone','Wrong zone'),$log+[Environment]::NewLine+$lines[-1])){
    if($changed -ceq $log){continue}
    $refused=$false;try{Get-ModelFFInventory $changed -AuthoredPlan $plan|Out-Null}catch{$refused=$true}
    if(!$refused){throw 'Changed or duplicate inventory accepted'}
}
$legacy=@('Loading zone "paris_model_probe"','Loading asset ",mopw/character_park_clown_zombie_shoes" of type material.','Loading asset "paris_model_probe_lod0" of type xmodelsurfs.','Loading asset "paris_model_probe" of type xmodel.','Loading asset "ncs_mdl_paris_model_probe" of type netconststrings.','Loading asset "paris_model_probe" of type rawfile.') -join [Environment]::NewLine
if(@(Get-ModelFFInventory $legacy).Count -ne 5){throw 'Legacy inventory changed'}
$bad=$plan|ConvertTo-Json -Depth 15|ConvertFrom-Json;$bad.expected_inventory[3].name=','+$bad.material_reference
$refused=$false;try{Get-ModelFFSourceNames $bad|Out-Null}catch{$refused=$true}
if(!$refused){throw 'Recipient authored material accepted'}
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile("$Repo/ops/model-lab/Build-ModelFF.ps1",[ref]$tokens,[ref]$errors)
if($errors){throw 'Build-ModelFF parse failed'}
# Execute the actual metadata dispatcher on a legal authored document >64 KiB.
# v3 retains the existing 1 MiB plan ceiling; only legacy v1 is limited to64 KiB.
$entryText=[IO.File]::ReadAllText("$Repo/ops/model-lab/Build-ModelFF.ps1")
$start=$entryText.IndexOf('if((Get-Item -LiteralPath $planPath).Length -gt 1MB)')
$stop=$entryText.IndexOf('$modelName=',$start)
$authoredPlanText=[IO.File]::ReadAllText($PlanPath)
$planPath=Join-Path (Split-Path $PlanPath) 'large-authored-plan.json'
[IO.File]::WriteAllText($planPath,($authoredPlanText+(' '*65537)))
. ([scriptblock]::Create($entryText.Substring($start,$stop-$start)))
if($planVersion -ne 3 -or !$authored -or $rigid){throw 'Large authored metadata dispatch differs'}
$admission=@($ast.FindAll({param($n);$n -is [Management.Automation.Language.CommandAst] -and $n.GetCommandName() -ceq 'Enter-IW7ResourceLease'},$true))[0]
$reader=@($ast.FindAll({param($n);$n -is [Management.Automation.Language.IfStatementAst] -and $n.Extent.Text.Contains("throw 'Admitted authored native reader changed.'")},$true))
if($reader.Count -ne 1 -or $reader[0].Extent.StartOffset -le $admission.Extent.EndOffset){throw 'Authored PE verification must remain under lease'}
$receipt=@($ast.FindAll({param($n);$n -is [Management.Automation.Language.IfStatementAst] -and $n.Clauses[0].Item1.Extent.Text.Trim() -ceq '$authored' -and $n.Extent.Text.Contains('Add-Member NoteProperty dumped_artifacts')},$true))
if($receipt.Count -ne 1){throw 'One authored native receipt binding required'}
$authored=$true;$RunRoot=Join-Path (Split-Path $PlanPath) 'receipt-fixture'
function Resolve-IW7BasePath($Base,$Relative){Join-Path $Base $Relative}
$artifactNames=@($plan.artifact_paths)
foreach($name in $artifactNames){
    $path=Join-Path $RunRoot ('roundtrip/'+$name);[IO.Directory]::CreateDirectory((Split-Path $path))|Out-Null
    [IO.File]::WriteAllText($path,'Authored synthetic dumped geometry only')
}
$state=@{SourcePlanSHA256='1'*64;FF=@{Bytes=29;SHA256='2'*64}}
$values=@{schema='iw7.model-roundtrip/1';geometry_roundtrip_verified=$true;physics_serialized=$false;iw7_normal_encoding_verified=$false;vertices=$plan.selected_counts.vertices;triangles=$plan.selected_counts.triangles}
foreach($field in @('geometry_profile','namespace','zone','model_name','mesh_name','material_reference')){$values[$field]=$plan.$field}
$verified=[pscustomobject]$values
. ([scriptblock]::Create($receipt[0].Extent.Text))
if($verified.source_plan_sha256 -cne $state.SourcePlanSHA256 -or $verified.ff.sha256 -cne $state.FF.SHA256 -or
    $verified.dumped_artifacts.Count -ne 2 -or $verified.dumped_artifacts[0].path -cne $artifactNames[0]){throw 'Authored geometry evidence not bound to this FF and source'}
'''
        with tempfile.TemporaryDirectory() as folder:
            writer,material=self.fixture(folder)
            output=Path(folder)/'ff-source'
            prepare_ff.stage_authored(writer,output,material_inputs=material)
            path=Path(folder)/'source-gates.ps1'
            path.write_text(script,encoding='utf-8')
            result=subprocess.run(['pwsh','-NoLogo','-NoProfile','-File',str(path),str(ROOT),str(output/'model-ff-plan.json')],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)


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

    def test_ff_dump_binds_runtime_surface_cache_without_widening_source_stage(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'runtime') as folder:
            base = Path(folder)
            fixture = self.multi()
            _, _, staged, plan = self.staged(base, fixture, distance=1000000)
            dump = base / 'roundtrip'
            for role, name in (('model', plan['model_name']), ('mesh', plan['mesh_name'])):
                relative = ('xmodel/' + name + '.xmb') if role == 'model' else ('xsurface/' + name + '.xsb')
                target = dump / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((staged / relative).read_bytes())
            model = dump / ('xmodel/' + plan['model_name'] + '.xmb')
            mesh = dump / ('xsurface/' + plan['mesh_name'] + '.xsb')
            pointer = 0x998877665544
            model_bytes, mesh_bytes = bytearray(model.read_bytes()), bytearray(mesh.read_bytes())
            struct.pack_into('<Q', model_bytes, 6+272, pointer)
            struct.pack_into('<Q', mesh_bytes, 6+8, pointer)
            model.write_bytes(model_bytes);mesh.write_bytes(mesh_bytes)
            ff = base / 'mod.ff';ff.write_bytes(b'AUTHORED ROUNDTRIP FIXTURE ONLY')
            result = rigid_export.verify_dump(staged, dump, ff)
            self.assertTrue(result['geometry_roundtrip_verified'])
            self.assertFalse(result['runtime_verified'])
            # A correct header cache cannot replace complete strict mesh validation.
            mesh.write_bytes(mesh_bytes[:6+56+2+len(plan['mesh_name'])+1])
            with self.assertRaises(ValueError):
                rigid_export.verify_dump(staged, dump, ff)
            changed_mesh = bytearray(mesh_bytes)
            changed_mesh[fixture.records['mesh']['surface_1.vertices']+6+24] ^= 1
            mesh.write_bytes(changed_mesh)
            with self.assertRaises(ValueError):
                rigid_export.verify_dump(staged, dump, ff)
            mesh.write_bytes(mesh_bytes)
            struct.pack_into('<Q', model_bytes, 6+272, pointer+1)
            model.write_bytes(model_bytes)
            with self.assertRaisesRegex(ValueError, 'surface cache differs'):
                rigid_export.verify_dump(staged, dump, ff)
            # A valid FF cache must still fail the source-stage parser, even if
            # its mutable file hash is updated to match the changed source.
            struct.pack_into('<Q', model_bytes, 6+272, pointer)
            source_model = staged / ('xmodel/' + plan['model_name'] + '.xmb')
            source_model.write_bytes(model_bytes)
            relative = source_model.relative_to(staged).as_posix()
            plan['source_files'][relative] = rigid_export.digest(bytes(model_bytes))
            (staged / 'model-ff-plan.json').write_bytes(rigid_export.json_bytes(plan))
            with self.assertRaises(ValueError):
                rigid_export.verify_stage(staged)

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

    def test_ff_consumer_large_metadata_uses_explicit_serialization_version(self):
        f = self.multi(surfaces=[(self.fixture.PYRAMID, self.fixture.PYRAMID_FACES)] * 255,
                       alias_geometry=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'runtime') as folder:
            base = Path(folder)
            _, _, staged, plan = self.staged(base, f, distance=1000000)
            # Legal whitespace changes size without adding or weakening fields.
            large = (json.dumps(plan, indent=16) + '\n').encode()
            self.assertGreater(len(large), 65536)
            self.assertLessEqual(len(large), 1024**2)
            (staged / 'model-ff-plan.json').write_bytes(large)
            rigid_export.verify_stage(staged, scene=True)
            producer = (ROOT / 'ops/model-lab/Build-ModelFF.ps1').read_text()
            start = producer.index('if((Get-Item -LiteralPath $planPath).Length -gt 1MB)')
            stop = producer.index('$modelName=', start)
            gate = producer[start:stop]
            script = base / 'metadata-bound.ps1'
            script.write_text(r'''param($Repo,$Root,$PlanPath)
$ErrorActionPreference='Stop'
. "$Repo/ops/model-lab/ModelFF.Core.ps1"
function Check-Document($planPath) {
''' + gate + r'''
}
Check-Document $PlanPath
$valid=Get-Content -LiteralPath $PlanPath -Raw|ConvertFrom-Json
$valid.geometry_profile='t7-iw7-selected-streamed-static-v1'
$streamed="$Root/streamed.json"
ConvertTo-Json -InputObject $valid -Depth 20|Set-Content -LiteralPath $streamed
[IO.File]::AppendAllText($streamed,(' '*65537))
Assert-ModelFFRigidPlan $valid
Check-Document $streamed
foreach($profile in @($null,'iw7-original-arena-rigid-v1')) {
    $legacy=[pscustomobject]@{geometry_profile=$profile}
    $legacyPath="$Root/legacy.json"
    ConvertTo-Json -InputObject $legacy|Set-Content -LiteralPath $legacyPath
    [IO.File]::AppendAllText($legacyPath,(' '*65537))
    # Stub only the unrelated source-name check: exercise actual size dispatch.
    function Get-ModelFFSourceNames($Plan){@('unused')}
    if($null -eq $profile){$legacy.PSObject.Properties.Remove('geometry_profile');ConvertTo-Json -InputObject $legacy|Set-Content $legacyPath;[IO.File]::AppendAllText($legacyPath,(' '*65537))}
    $refused=$false;try{Check-Document $legacyPath}catch{$refused=$_.Exception.Message -eq 'Legacy model FF preparation exceeds bound.'}
    if(!$refused){throw 'Legacy/arena metadata limit widened.'}
}
[IO.File]::AppendAllText($streamed,(' '*1MB))
$refused=$false;try{Check-Document $streamed}catch{$refused=$_.Exception.Message -eq 'Bounded model FF preparation required.'}
if(!$refused){throw 'One-MiB document limit widened.'}
''')
            result = subprocess.run(['pwsh', '-NoProfile', '-File', str(script), str(ROOT), folder,
                                     str(staged / 'model-ff-plan.json')], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

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
            $p.geometry_work_bytes_upper_bound=256+384*6+72*6*65535
        }
    }
    $refused=$false;try{Assert-ModelFFRigidPlan $p}catch{$refused=$true}
    if(!$refused){throw "Invalid v2 $case accepted"}
}
# Aggregate counts are not uint16; each individual surface remains bounded.
$p=$raw|ConvertFrom-Json
foreach($record in $p.surface_records){$record.vertices=40000}
$p.selected_counts.vertices=80000;$p.geometry_work_bytes_upper_bound=256+384*2+60*80000+12*10
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
$gate=$ast.FindAll({param($n) $n -is [Management.Automation.Language.IfStatementAst] -and $n.Extent.Text.Contains("throw 'Pinned exact original FF source preparation required.'")},$true)
if(@($gate).Count -ne 1){throw 'Ambiguous build source gate'}
$plan=$valid;$planVersion=2;$authored=$false;$sourceNames=@(Get-ModelFFSourceNames $plan)
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


class AuthoredModelFFLifecycleTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('pwsh') and sys.platform == 'win32', 'Windows Source path/owner fixtures require pwsh')
    def test_actual_authored_entry_metadata_deadlines_and_restore_callback(self):
        result = subprocess.run(['pwsh', '-NoLogo', '-NoProfile', '-File',
                                 str(ROOT / 'tests/ops/Test-AuthoredModelFF.Source.ps1'), '-Repo', str(ROOT)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout.strip())
        self.assertEqual(report['Result'], 'PASS')
        self.assertGreaterEqual(report['Assertions'], 40)
        self.assertFalse(report['NativeProcessStarted'])
        self.assertFalse(report['StockRead'])
        self.assertFalse(report['LeaseAcquired'])


if __name__ == '__main__':
    unittest.main()

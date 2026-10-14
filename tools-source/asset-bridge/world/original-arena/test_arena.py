"""Targeted original geometry/invalid-format/collision-reference checks; no native."""
import copy
import hashlib
import json
import math
import re
from pathlib import Path
import struct
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import arena
import prepare
import readback
import model_lab
import prepare_writer


class ArenaTests(unittest.TestCase):
    def setUp(self):
        self.scene = arena.original_scene()

    def test_original_scene_geometry_has_seven_closed_boxes(self):
        mesh = arena.geometry(self.scene)
        surface = mesh['surfaces'][0]
        self.assertEqual((len(surface['vertices']), len(surface['triangles'])), (168, 84))
        self.assertEqual(mesh['bounds'], {'midpoint': [0, 0, 40], 'half_size': [272, 208, 56]})
        for t in surface['triangles']:
            a,b,c = [surface['vertices'][i] for i in t]
            u = [y-x for x,y in zip(a['position'], b['position'])]
            v = [y-x for x,y in zip(a['position'], c['position'])]
            cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
            self.assertGreater(sum(x*y for x,y in zip(cross,a['normal'])), 0)
        self.assertFalse(mesh['iw7_serialized'])

    def test_invalid_boxes_counts_identifiers_and_claims_refused(self):
        for change in ('nan', 'inverted', 'degenerate', 'oversized', 'duplicate', 'too_many', 'runtime', 'material', 'unknown'):
            with self.subTest(change=change):
                s = copy.deepcopy(self.scene)
                if change == 'nan': s['solids'][0]['minimum'][0] = math.nan
                if change == 'inverted': s['solids'][0]['minimum'][0] = 300
                if change == 'degenerate': s['solids'][0]['maximum'][2] = -16
                if change == 'oversized': s['solids'][0]['maximum'][0] = 5000
                if change == 'duplicate': s['solids'][1]['name'] = s['solids'][0]['name']
                if change == 'too_many': s['solids'] *= 2
                if change == 'runtime': s['runtime_verified'] = True
                if change == 'material': s['material_reference'] = 'invented'
                if change == 'unknown': s['unknown'] = 1
                with self.assertRaises(ValueError): arena.validate(s)

    def test_floor_hit_and_outside_miss(self):
        floor = self.scene['solids'][0]
        hit = arena.swept_box(floor, [0, 0, 32], [0, 0, -32], [0,0,0])
        self.assertTrue(hit['hit']); self.assertEqual(hit['fraction'], .5); self.assertEqual(hit['normal'], [0,0,1])
        self.assertFalse(arena.swept_box(floor, [300,0,32], [300,0,-32], [0,0,0])['hit'])

    def test_actor_falls_to_floor_at_center_height_36(self):
        hit = arena.trace(self.scene, [0,0,80], [0,0,20], self.scene['actor_half_size'])
        self.assertEqual(hit['solid'], 'floor')
        self.assertAlmostEqual(hit['fraction'], 44/60)

    def test_tangent_floor_motion_clear_but_motion_into_floor_blocked(self):
        floor = self.scene['solids'][0]; half = self.scene['actor_half_size']
        self.assertFalse(arena.swept_box(floor, [-128,-96,36], [128,-96,36], half)['hit'])
        self.assertEqual(arena.swept_box(floor, [0,0,36], [0,0,20], half)['fraction'], 0)
        self.assertFalse(arena.swept_box(floor, [0,0,36], [0,0,80], half)['hit'])

    def test_side_wall_and_obstacle_block_actor(self):
        half = self.scene['actor_half_size']
        wall = arena.trace(self.scene, [200,80,36], [300,80,36], half)
        self.assertEqual(wall['solid'], 'east'); self.assertAlmostEqual(wall['fraction'], .41)
        obstacle = arena.trace(self.scene, [-64,0,36], [96,0,36], half)
        self.assertEqual(obstacle['solid'], 'obstacle'); self.assertAlmostEqual(obstacle['fraction'], 65/160)

    def test_start_inside_stationary_and_degenerate_queries(self):
        floor = self.scene['solids'][0]
        self.assertTrue(arena.swept_box(floor, [0,0,-8], [0,0,-8], [0,0,0])['start_solid'])
        self.assertFalse(arena.swept_box(floor, [0,0,32], [0,0,32], [0,0,0])['hit'])
        for half in ([0,-1,0], [True,0,0]):
            with self.assertRaises(ValueError): arena.swept_box(floor,[0,0,32],[0,0,-32],half)

    def test_route_reaches_goal_around_obstacle_and_door_is_clear(self):
        route = arena.route_check(self.scene)
        self.assertTrue(route['clear']); self.assertTrue(route['goal_reached'])
        self.assertFalse(route['native_collision_verified'])
        self.assertFalse(arena.trace(self.scene,[0,-160,36],[0,-224,36],self.scene['actor_half_size'])['hit'])

    def test_goal_reuses_trigger_adapter_without_claiming_solid_collision(self):
        source, converted = arena.goal_trigger(self.scene)
        self.assertEqual(source['trigger']['hulls'][0]['bounds'], {'midPoint': [152,112,40], 'halfSize': [40,32,40]})
        self.assertEqual(converted['trigger']['count'], 1)
        self.assertFalse(converted['runtime_ready'])

    def test_prepared_source_reuses_writer_and_refuses_changed_seam(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/'prepared'
            result = prepare.prepare(output)
            self.assertEqual(result['prepared_files'], 7)
            self.assertFalse(result['native_collision_verified'])
            cpp = (output/'arena_writer.cpp').read_text()
            self.assertIn('probe_vertex_count', cpp)
            self.assertIn('paris_original_arena.xmb', cpp)
            self.assertIn('!rm->physicsAsset', cpp)
            self.assertNotIn('paris_model_probe', cpp)
            with self.assertRaises(ValueError): prepare.prepare(output)
            base = (arena.REPO/'ops/model-lab/writer.cpp').read_text()
            with self.assertRaises(ValueError): prepare.adapt_writer(base.replace('surf.vertCount=24;', 'surf.vertCount=23;'))

    def test_generated_cpp_literals_and_report_are_well_formed(self):
        mesh = arena.geometry(self.scene)
        self.assertIn('probe_radius_squared = 126464.0f;', prepare.header(mesh))
        cpp = prepare.adapt_writer((arena.REPO/'ops/model-lab/writer.cpp').read_text())
        line = next(x for x in cpp.splitlines() if 'std::cout' in x)
        import re
        strings = [json.loads(x) for x in re.findall(r'"(?:[^"\\]|\\.)*"', line)]
        report = json.loads(strings[0]+'168'+strings[1]+'84'+strings[2])
        self.assertEqual(report['schema'], 'iw7.original-arena-roundtrip/1')
        self.assertFalse(report['physics_serialized'])

    def test_halfway_float32_literal_rounds_before_decimal_formatting(self):
        self.assertEqual(prepare.literal(1+2**-24), '1.0f')
        self.assertEqual(prepare.literal(-(1+2**-24)), '-1.0f')


def synthetic_records(mesh, material=None):
    """Tiny authored typed streams for reader fault injection, never retail data."""
    def array(payload, count):
        return b'\x08\x00' if not count else b'\x08\x01'+struct.pack('<I',count)+payload
    def name(text, kind=6):
        return bytes((kind,0)) if text is None else bytes((kind,1))+text.encode()+b'\0'
    surface = mesh['surfaces'][0]
    n, t = len(surface['vertices']), len(surface['triangles'])
    midpoint, half = mesh['bounds']['midpoint'], mesh['bounds']['half_size']
    radius = max(sum(v*v for v in item['position']) for item in surface['vertices'])
    h = bytearray(736);h[20:23]=bytes((1,1,0))
    h[8:15] = bytes((0,1,0,1,255,6,1))
    radius_f32, = struct.unpack('<f',struct.pack('<f',radius))
    struct.pack_into('<HHf',h,24,0,1,1);struct.pack_into('<f',h,40,math.sqrt(radius_f32))
    struct.pack_into('<6f',h,44,*(midpoint+half));struct.pack_into('<fHH',h,224,1000000,1,0)
    struct.pack_into('<I',h,240,0x80000000)
    model = array(h,1)+name(mesh['name'])+name('tag_origin')+array(b'',0)*3+array(bytes(1),1)
    model += array(struct.pack('<8f',0,0,0,1,0,0,0,2),1)+array(b'',0)*3
    model += array(struct.pack('<7f',*(midpoint+half+[radius])),1)+array(bytes(2),1)+array(struct.pack('<Q',bool(material)),1)
    model += name(material,7)+name(mesh['name']+'_lod0',7)+name(None,7)*9+array(b'',0)*3
    g = bytearray(56);struct.pack_into('<H',g,16,1)
    s = bytearray(256);struct.pack_into('<3H2B',s,0,0x82,n,t,1,0)
    struct.pack_into('<I',g,20,0x80000000);struct.pack_into('<I',s,224,0x80000000)
    vertices = b''
    for v in surface['vertices']:
        packed_normal = 0xc0000000
        for i,x in enumerate(v['normal']):packed_normal |= math.floor((x+1)*.5*1023+.5) << (10*i)
        vertices += struct.pack('<3fII2eII',*v['position'],0,0xffffffff,*v['uv'],packed_normal,0)
    faces = b''.join(struct.pack('<3H',*tri) for tri in surface['triangles'])
    raw = array(g,1)+name(mesh['name']+'_lod0')+array(s,1)+array(vertices,n)+array(faces,t)
    raw += array(struct.pack('<4HQ',0,n,0,t,0),1)+b'\x0a\x00'*4
    return model,raw


class IndependentReaderTests(unittest.TestCase):
    def test_all_three_rigid_masks_refuse_lod_group_and_surface_corruption(self):
        source=arena.geometry(arena.original_scene());model,mesh=synthetic_records(source)
        surface_offset=6+56+2+len('paris_original_arena_lod0')+1+6
        for role,offset in (('model',6+240),('group',6+20),('surface',surface_offset+224)):
            for byte in (0,31):
                changed=bytearray(model if role=='model' else mesh);changed[offset+byte]^=1
                with self.subTest(role=role,byte=byte),self.assertRaisesRegex(ValueError,'root part bits'):
                    readback.inspect(bytes(changed) if role=='model' else model,
                                     mesh if role=='model' else bytes(changed),source)
    def test_explicit_material_binding_and_opaque_pointer_relocation(self):
        source=arena.geometry(arena.original_scene())
        unbound,mesh=synthetic_records(source)
        bound,_=synthetic_records(source,readback.MATERIAL)
        self.assertTrue(readback.inspect(bound,mesh,source,expected_material=readback.MATERIAL)['material_bound'])
        with self.assertRaises(ValueError):readback.inspect(bound,mesh,source)
        with self.assertRaises(ValueError):readback.inspect(unbound,mesh,source,expected_material=readback.MATERIAL)
        with self.assertRaises(ValueError):readback.inspect(bound,mesh,source,expected_material='invented')
        for offset in (9,12,13):
            changed=bytearray(bound);changed[6+offset]=0
            with self.assertRaises(ValueError):readback.inspect(bytes(changed),mesh,source,expected_material=readback.MATERIAL)
    def test_valid_original_records_and_native_limits_remain_explicit(self):
        source = arena.geometry(arena.original_scene());model,mesh = synthetic_records(source)
        report=readback.inspect(model,mesh,source)
        self.assertEqual((report['vertices'],report['triangles']),(168,84))
        self.assertFalse(report['physics_serialized']);self.assertFalse(report['runtime_verified'])

    def test_decimal_scene_uses_actual_float32_bounds_positions_and_radius(self):
        for change in ('floor', 'radius'):
            with self.subTest(change=change):
                scene=arena.original_scene()
                if change == 'floor':
                    scene['solids'][0]['minimum'][2] = -16.1
                else:
                    scene['solids'][3]['maximum'][0] = 272.1
                    scene['solids'][3]['maximum'][2] = 96.1
                self.assertTrue(arena.route_check(scene)['clear'])
                source=arena.geometry(scene);model,mesh=synthetic_records(source)
                self.assertTrue(readback.inspect(model,mesh,source)['geometry_roundtrip_verified'])
                # A one-ULP corruption remains refused; the fix is not epsilon.
                broken=bytearray(model)
                bits,=struct.unpack_from('<I',broken,6+44)
                struct.pack_into('<I',broken,6+44,bits+1)
                with self.assertRaisesRegex(ValueError,'model bounds'):
                    readback.inspect(bytes(broken),mesh,source)
                broken=bytearray(model)
                bits,=struct.unpack_from('<I',broken,6+40)
                struct.pack_into('<I',broken,6+40,bits+1)
                with self.assertRaisesRegex(ValueError,'radius'):
                    readback.inspect(bytes(broken),mesh,source)

    def test_truncation_type_count_trailing_and_geometry_corruption(self):
        source = arena.geometry(arena.original_scene());model,mesh = synthetic_records(source)
        variants = [(model[:-1],mesh),(model,mesh[:-1]),(model+b'x',mesh),(model,mesh+b'x')]
        broken=bytearray(model);broken[0]=7;variants.append((bytes(broken),mesh))
        broken=bytearray(model);struct.pack_into('<I',broken,2,2);variants.append((bytes(broken),mesh))
        # First packed vertex follows group/name/surface/vertex record headers.
        p=6+56+2+len('paris_original_arena_lod0')+1+6+256+6
        broken=bytearray(mesh);struct.pack_into('<f',broken,p,500);variants.append((model,bytes(broken)))
        broken=bytearray(mesh);struct.pack_into('<f',broken,p,float('nan'));variants.append((model,bytes(broken)))
        for m,s in variants:
            with self.subTest(model=len(m),mesh=len(s)):
                with self.assertRaises(ValueError):readback.inspect(m,s,source)


class ModelLabTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('pwsh'), 'PowerShell stock date source checks require pwsh')
    def test_stock_metadata_accepts_typed_and_short_dates_but_refuses_changed_ticks(self):
        # Evaluate the actual refusal predicate with authored metadata only.
        # No retail file, native type, reservation or process owner is consulted.
        script=r'''
param($Helper)
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Helper,[ref]$tokens,[ref]$errors)
$node=@($ast.FindAll({param($n);$n -is [Management.Automation.Language.IfStatementAst] -and $n.Extent.Text.Contains("throw 'Retained stock metadata changed.'")},$true))[0]
if(!$node){throw 'Exact stock metadata refusal predicate required'}
$check=[scriptblock]::Create($node.Extent.Text)
$time=[datetimeoffset]'2026-09-29T21:46:16.8069800Z'
$file=[pscustomobject]@{Length=77L;LastWriteTimeUtc=$time.UtcDateTime;Attributes=[IO.FileAttributes]::Archive}
$typed=(' {"ModifiedUtc":"2026-09-29T21:46:16.80698Z"}'|ConvertFrom-Json).ModifiedUtc
foreach($date in @('2026-09-29T21:46:16.8069800Z','2026-09-29T21:46:16.80698Z',$typed)){
    $entry=[pscustomobject]@{Bytes=77L;ModifiedUtc=$date;Attributes=32}
    & $check
}
foreach($kind in 'ticks','bytes','attributes'){
    $entry=[pscustomobject]@{Bytes=77L;ModifiedUtc=$time.AddTicks(1).ToString('o');Attributes=32}
    if($kind -ceq 'bytes'){$entry.ModifiedUtc=$time.ToString('o');$entry.Bytes=78L}
    if($kind -ceq 'attributes'){$entry.ModifiedUtc=$time.ToString('o');$entry.Attributes=33}
    $caught=$false;try{& $check}catch{$caught=$true}
    if(!$caught){throw 'Changed stock metadata was accepted'}
}
'''
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'stock-date.ps1';path.write_text(script,encoding='utf-8')
            result=subprocess.run([shutil.which('pwsh'),'-NoLogo','-NoProfile','-File',str(path),
                str(Path(model_lab.__file__).with_name('Measure-StockReference.ps1'))],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    @unittest.skipUnless(shutil.which('pwsh'), 'PowerShell admission source checks require pwsh')
    def test_world_opaque_qualification_is_deferred_to_existing_admission(self):
        script=r'''
param($Writer,$FF,$Root)
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$writerAst=[Management.Automation.Language.Parser]::ParseFile($Writer,[ref]$tokens,[ref]$errors)
$pin=@($writerAst.FindAll({param($node);$node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq 'Pin'},$true))[0]
. ([scriptblock]::Create($pin.Extent.Text))
$guards=[Collections.Generic.List[IDisposable]]::new();$entries=[Collections.Generic.List[object]]::new();$Run=$true
$fake=Join-Path $Root 'authored.exe';[IO.File]::WriteAllText($fake,'Authored changed binary')
try{$result=Pin $fake ('1'*64);if($result.SHA256 -cne ('1'*64)){throw 'Opaque bytes were hashed before admission'}}finally{foreach($guard in $guards){$guard.Dispose()}}
$commands=@($writerAst.FindAll({param($node);$node -is [Management.Automation.Language.CommandAst]},$true))
$lease=@($commands|Where-Object {$_.GetCommandName() -ceq 'Enter-IW7ResourceLease'})[0]
$hash=@($commands|Where-Object {$_.GetCommandName() -ceq 'Assert-BeaconHash'})[0]
if(!$lease -or !$hash -or $hash.Extent.StartOffset -le $lease.Extent.EndOffset){throw 'Writer opaque validation must follow existing admission'}
$ast=[Management.Automation.Language.Parser]::ParseFile($FF,[ref]$tokens,[ref]$errors)
$block=@($ast.FindAll({param($node);$node -is [Management.Automation.Language.IfStatementAst] -and $node.Clauses[0].Item1.Extent.Text.Trim() -ceq '$CandidateRoot'},$true))[0]
$arena=$true;$ToolProvenance='';$CandidateArtifactSHA256='1'*64;$NativeJobAssembly='absent-owner.dll'
$CandidateRoot=Join-Path $Root 'candidate';$repo=Join-Path $Root 'package'
[IO.Directory]::CreateDirectory((Join-Path $repo 'sdk/modding'))|Out-Null;[IO.Directory]::CreateDirectory($CandidateRoot)|Out-Null
[IO.File]::WriteAllText((Join-Path $repo 'sdk/modding/BeaconFF.Core.ps1'),'# Authored pure import')
$toolPath=Join-Path $CandidateRoot 'bin/zonetool-community.exe';$sha='e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04'
@{schema='iw7.zonetool-community-candidate/1';executable=@{path=$toolPath;sha256=$sha}}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $CandidateRoot 'build-artifact.local.json')
$script:Admitted=$false;$script:QualificationCalls=0
function Resolve-IW7BasePath($Root,$Relative){Join-Path $Root $Relative}
function Assert-BeaconHash($Path,$SHA){if(!(Split-Path $Path -Leaf).Equals('build-artifact.local.json')){throw 'Opaque pre-admission hash'}}
function Read-BeaconJson($Path,$Limit){Get-Content -LiteralPath $Path -Raw|ConvertFrom-Json}
function Assert-BeaconCandidate($Root,$Artifact){if(!$script:Admitted){throw 'Opaque candidate qualified without admission'};$script:QualificationCalls++;[pscustomobject]@{Path=$toolPath;SHA256=$sha}}
. ([scriptblock]::Create($block.Extent.Text))
if($script:QualificationCalls -ne 0 -or $tool -ine $toolPath){throw 'LIGHT metadata must not qualify candidate binary'}
$calls=@($ast.FindAll({param($node);$node -is [Management.Automation.Language.CommandAst] -and $node.GetCommandName() -ceq 'Assert-BeaconCandidate'},$true))
$lease=@($ast.FindAll({param($node);$node -is [Management.Automation.Language.CommandAst] -and $node.GetCommandName() -ceq 'Enter-IW7ResourceLease'},$true))[0]
$admittedCall=@($calls|Where-Object {$_.Extent.StartOffset -gt $lease.Extent.EndOffset})[0]
if(!$admittedCall){throw 'World FF qualifier must follow existing admission'}
$underLease=$admittedCall;while($underLease -and $underLease -isnot [Management.Automation.Language.IfStatementAst]){$underLease=$underLease.Parent}
$script:Admitted=$true;$state=@{}
. ([scriptblock]::Create($underLease.Extent.Text))
if($script:QualificationCalls -ne 1 -or !$state.CandidateQualifiedUnderLease){throw 'Admitted actual candidate validation missing'}
'''
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'admission-source.ps1';path.write_text(script,encoding='utf-8')
            result=subprocess.run([shutil.which('pwsh'),'-NoLogo','-NoProfile','-File',str(path),
                str(Path(model_lab.__file__).with_name('Build-ArenaWriter.ps1')),
                str(arena.REPO/'ops/model-lab/Build-ModelFF.ps1'),temp],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    @unittest.skipUnless(shutil.which('pwsh'), 'PowerShell LIGHT plan checks require pwsh')
    def test_light_measurement_plan_binds_checker_and_local_imports(self):
        helper=Path(model_lab.__file__).with_name('Measure-StockReference.ps1')
        # Authored source/receipt placeholders only; default planning must never
        # inspect the nonexistent native candidate, stock or assembly below.
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);package=root/'package';tool=root/'tool'
            names=set(re.findall(r"'((?:ops|sdk|tools-source)/[^']+\.(?:ps1|py|cs))'",helper.read_text()))
            for name in names:
                path=package/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('Authored source '+name)
            (package/'ops/model-lab/prepare_writer.py').write_text("INTERFACES=['normal-a','normal-b','normal-c']\n")
            for name in ('normal-a','normal-b','normal-c'):
                path=tool/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('Authored normal proof')
            (package/'source-workspace.json').write_text(json.dumps({'revisions':{'iw7-mod-components':'2f9462db806bbd3ab51f9ecb2f3b25ae54ae10f1'}}))
            inputs=[{'Relative':f'main/source-{i}.ff','Source':str(root/f'absent-stock-{i}'),'Mode':'HardLink'} for i in range(71)]
            inputs.append({'Relative':'main/fileSysCheck.cfg','Source':str(root/'absent-sentinel'),'Mode':'Copy'})
            binding=root/'stock.json';binding.write_text(json.dumps({'stock_binding':{'inputs':inputs}}))
            args=[shutil.which('pwsh'),'-NoLogo','-NoProfile','-File',str(helper),'-PackageRoot',str(package),
                  '-RunRoot',str(package/'runtime/reference'),'-StockBindingPlan',str(binding),
                  '-StockBindingPlanSHA256',model_lab.digest(binding.read_bytes()),'-ToolSource',str(tool),
                  '-CandidateRoot',str(root/'absent-candidate'),'-CandidateArtifactSHA256','1'*64,
                  '-NativeJobAssembly',str(root/'absent-owner.dll')]
            def planned():
                result=subprocess.run(args,capture_output=True,text=True,timeout=20)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                value=json.loads(result.stdout)
                self.assertFalse(value['StockBytesRead']);self.assertFalse(value['NativeTypesLoaded']);self.assertFalse(value['LeaseAcquired'])
                return value
            baseline=planned();prior=baseline['PlanSHA256']
            for name in ('tools-source/asset-bridge/world/original-arena/model_lab.py',
                         'tools-source/asset-bridge/world/original-arena/readback.py',
                         'tools-source/asset-bridge/h1-fixture/inspect_fixture.py'):
                path=package/name
                self.assertIn(str(path),[pin['Path'] for pin in baseline['Plan']['SourcePins']])
                path.write_text(path.read_text()+'\nAuthored checker mutation')
                current=planned()['PlanSHA256'];self.assertNotEqual(current,prior);prior=current
            self.assertFalse((package/'runtime/reference').exists())

    @unittest.skipUnless(shutil.which('pwsh'), 'PowerShell source caller checks require pwsh')
    def test_original_job_caller_keeps_unknown_owner_and_accepts_telemetry_only(self):
        # Authored PowerShell mocks only: no native type/job, tool/game process,
        # retail content or resource reservation is used by this source check.
        script = r'''
param($Helper,$Root)
$ErrorActionPreference='Stop'
. $Helper
$script:Mode='pass';$script:Bytes=0L
function Measure-BeaconOutputFiles {return $script:Bytes}
function Get-IW7ResourceSnapshot {return [pscustomobject]@{Committed=99;CommitLimit=100}}
function Invoke-H1OwnedStage($Plan,$State,$Context,$Start,$SHA,$Logs){
    if($Start.WorkingDirectory -cne $Context.Work -or $Start.ArgumentList[0] -cne '-strict-content-sources'){throw 'Literal direct original tool start differs'}
    $Context.Closed=$false
    if($script:Mode -cne 'unknown'){
        $Context.Owner=[pscustomobject]@{Closed=$false;StopCalls=0}
        $Context.Owner|Add-Member ScriptMethod StopAndConfirm {param($Ms);if($Ms -ne 5000){throw 'Wrong original stop deadline'};$this.StopCalls++;$this.Closed=$true}
    }
    if($script:Mode -cne 'pass'){throw 'Authored owner failure'}
    Test-H1Budget $Plan $State
    $State.Identity=[ordered]@{PID=1234;Image=$Start.FileName;CreatedUtc='2026-10-14T00:00:00Z'}
    $State.TreeClosureConfirmed=$true;$State.ExitCode=0;$Context.Closed=$true;$Context.Owner.Closed=$true
}
foreach($mode in 'pass','failed','unknown'){
    $script:Mode=$mode;$work=Join-Path $Root $mode;[IO.Directory]::CreateDirectory($work)|Out-Null
    $context=[pscustomobject]@{Owner=$null;Closed=$true;Lease=[pscustomobject]@{Token='authored'};Work=$work}
    if($mode -ceq 'pass'){
        $result=Invoke-OriginalArenaTool $context (Join-Path $work 'authored.exe') ('1'*64) @('-strict-content-sources') $work $work probe @() 30
        if(!$result.JobClosed -or !$result.RootExited -or $result.ActiveProcesses -ne 0 -or !$context.Closed){throw 'Closed source witness differs'}
    }else{
        $caught=$false;try{$null=Invoke-OriginalArenaTool $context (Join-Path $work 'authored.exe') ('1'*64) @('-strict-content-sources') $work $work probe @() 30}catch{$caught=$true}
        if(!$caught){throw 'Failure was accepted'}
        if($mode -ceq 'failed' -and (!$context.Closed -or $context.Owner.StopCalls -ne 1)){throw 'Original owner cleanup differs'}
        if($mode -ceq 'unknown' -and ($context.Closed -or $context.Owner)){throw 'Unknown factory was treated as closed'}
    }
}
$work=Join-Path $Root 'reused';[IO.Directory]::CreateDirectory($work)|Out-Null
$context=[pscustomobject]@{Owner=$null;Closed=$true;Lease=[pscustomobject]@{Token='authored'};Work=$work}
$script:Mode='pass'
$null=Invoke-OriginalArenaTool $context (Join-Path $work 'authored.exe') ('1'*64) @('-strict-content-sources') $work $work first @() 30
$previous=$context.Owner
$script:Mode='unknown';$caught=$false
try{$null=Invoke-OriginalArenaTool $context (Join-Path $work 'authored.exe') ('1'*64) @('-strict-content-sources') $work $work second @() 30}catch{$caught=$true}
if(!$caught -or $context.Closed -or $context.Owner -or $previous.StopCalls -ne 0){throw 'Previous closed owner falsely qualified a new unknown factory'}
'''
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'source-caller.ps1';path.write_text(script,encoding='utf-8')
            result=subprocess.run([shutil.which('pwsh'),'-NoLogo','-NoProfile','-File',str(path),
                str(Path(model_lab.__file__).with_name('OriginalArena.Process.ps1')),temp],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def reference_fixture(self,root):
        tool,_,_,legacy=self.binding_fixture(root)
        measurement=root/'measurement';measurement.mkdir()
        request={'schema':'iw7.original-arena-reference-request/1','recipient':'cp_zmb',
                 'material':readback.MATERIAL,'input_csv':'requested.csv','output_csv':'world_material'}
        request_raw=model_lab.json_bytes(request)
        (measurement/'reference-request.json').write_bytes(request_raw)
        (measurement/'requested.csv').write_bytes(('material,'+readback.MATERIAL+'\n').encode())
        closure={'Schema':'iw7.original-arena-reference-process/1','ExitCode':0,'RootExited':True,
                 'ActiveProcesses':0,'JobClosed':True,'Restored':True,'StockPreserved':True,
                 'ImageSHA256':model_lab.REFERENCE_TOOL_SHA256,
                 'Identity':{'PID':1234,'Image':str(root/'fixture-tool.exe'),'CreatedUtc':'2026-10-14T00:00:00Z'},
                 'Arguments':['-headless','-unbuffered-io','-strict-content-sources','-enemy-reference-check',
                              'cp_zmb','requested.csv','world_material'],'RequestSHA256':model_lab.digest(request_raw)}
        plan={'Schema':'iw7.original-arena-reference-plan/1','Image':closure['Identity']['Image'],
              'ImageSHA256':model_lab.REFERENCE_TOOL_SHA256,'Arguments':closure['Arguments'],
              'RequestSHA256':closure['RequestSHA256'],'OriginalOwnerAssemblySHA256':model_lab.REFERENCE_OWNER_SHA256}
        plan_raw=model_lab.json_bytes(plan);(measurement/'reference-plan.json').write_bytes(plan_raw)
        closure['PlanSHA256']=model_lab.digest(plan_raw)
        outputs={'csv':('type,name,status\nmaterial,'+readback.MATERIAL+',verified\n').encode(),
                 'stdout':b'ENEMY_REFERENCE_CHECK map=cp_zmb rows=1 verified=1 missing=0 default=0 output=enemy-catalog/world_material.csv\n',
                 'closure':model_lab.json_bytes(closure)}
        snapshots={}
        for key,data in outputs.items():
            name='enemy-catalog/world_material.csv' if key=='csv' else key+('.json' if key=='closure' else '.txt')
            (measurement/name).parent.mkdir(exist_ok=True);(measurement/name).write_bytes(data)
            snapshots[key]={'path':name,'bytes':len(data),'sha256':model_lab.digest(data)}
        evidence={'schema':'iw7.original-arena-recipient-reference/1','source_pin':prepare_writer.PIN,
                  'recipient':'cp_zmb','material':readback.MATERIAL,'snapshot_only':True,
                  'runtime_verified':False,'material_payload_verified':False,
                  'reference_snapshot':snapshots,'normal_encoding_source':legacy['normal_encoding_source']}
        path=root/'reference.json';path.write_bytes(model_lab.json_bytes(evidence))
        return tool,measurement,path,evidence,closure

    def test_current_reference_binding_requires_nondefault_row_closed_job_and_exact_request(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);tool,measurement,path,evidence,closure=self.reference_fixture(root)
            self.assertEqual(model_lab.validate_reference_evidence(tool,path,measurement)[0],readback.MATERIAL)
            for kind in ('default','missing','extra','open','wrong-tool','wrong-request','identity',
                         'plan-digest','root-image','unrestored','stock-changed','marker-path','extra-marker'):
                altered=copy.deepcopy(evidence);changed=copy.deepcopy(closure)
                csv_path=measurement/evidence['reference_snapshot']['csv']['path']
                csv_original=csv_path.read_bytes()
                log_path=measurement/evidence['reference_snapshot']['stdout']['path'];log_original=log_path.read_bytes()
                if kind in ('default','missing','extra'):
                    data=(('type,name,status\nmaterial,'+readback.MATERIAL+','+kind+'\n') if kind!='extra'
                          else csv_original.decode()+'material,other,verified\n').encode()
                    csv_path.write_bytes(data)
                    altered['reference_snapshot']['csv'].update(bytes=len(data),sha256=model_lab.digest(data))
                elif kind in ('marker-path','extra-marker'):
                    data=(log_original.replace(b'world_material.csv',b'other.csv') if kind=='marker-path' else
                          log_original+b'ENEMY_REFERENCE_CHECK map=cp_rave rows=1 verified=1 missing=0 default=0 output=other.csv\n')
                    log_path.write_bytes(data)
                    altered['reference_snapshot']['stdout'].update(bytes=len(data),sha256=model_lab.digest(data))
                else:
                    if kind=='open':changed['ActiveProcesses']=1
                    if kind=='wrong-tool':changed['ImageSHA256']='0'*64
                    if kind=='wrong-request':changed['Arguments'][4]='cp_rave'
                    if kind=='identity':changed['Identity']['PID']=0
                    if kind=='plan-digest':changed['PlanSHA256']='1'*64
                    if kind=='root-image':changed['Identity']['Image']=str(root/'other.exe')
                    if kind=='unrestored':changed['Restored']=False
                    if kind=='stock-changed':changed['StockPreserved']=False
                    data=model_lab.json_bytes(changed);(measurement/'closure.json').write_bytes(data)
                    altered['reference_snapshot']['closure'].update(bytes=len(data),sha256=model_lab.digest(data))
                path.write_bytes(model_lab.json_bytes(altered))
                with self.subTest(kind=kind),self.assertRaises(ValueError):
                    model_lab.validate_reference_evidence(tool,path,measurement)
                csv_path.write_bytes(csv_original)
                log_path.write_bytes(log_original)
                (measurement/'closure.json').write_bytes(model_lab.json_bytes(closure))
            path.write_bytes(model_lab.json_bytes(evidence))
            hashes=prepare_writer.source_hashes(tool,check_pin=False)
            with patch.object(prepare,'source_hashes',return_value=hashes):
                prepare.prepare(root/'new-bound',tool_source=tool,recipient_evidence=path,stock_root=measurement)
            self.assertIn(readback.MATERIAL,(root/'new-bound/probe_geometry.hpp').read_text())

    def binding_fixture(self,root):
        tool,stock=root/'tool',root/'stock'
        for name in prepare_writer.INTERFACES:
            path=tool/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(('Original source fixture '+name).encode())
        snapshots={}
        for name in ('closure','load_log','material_json'):
            raw=('Original evidence fixture '+name).encode();path=stock/(name+'.txt')
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            snapshots[name]={'path':path.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        evidence={'schema':'iw7.model-recipient-evidence/1','source_pin':prepare_writer.PIN,'recipient':'cp_zmb',
                  'material':readback.MATERIAL,'snapshot_only':True,'runtime_verified':False,'material_snapshot':snapshots,
                  'normal_encoding_source':[{'path':name,'sha256':hashlib.sha256((tool/name).read_bytes()).hexdigest()}
                                            for name in prepare_writer.INTERFACES[-3:]]}
        path=root/'recipient.json';path.write_text(json.dumps(evidence))
        return tool,stock,path,evidence

    def prepare_fixture(self,root):
        tool,stock,evidence,_=self.binding_fixture(root)
        prepared=root/'prepared'
        # Test-authored interfaces/evidence; this bypass is scoped to this mock,
        # never a production CLI flag or a claim about live retail snapshots.
        hashes=prepare_writer.source_hashes(tool,check_pin=False)
        with patch.object(prepare,'source_hashes',return_value=hashes):
            prepare.prepare(prepared,tool_source=tool,recipient_evidence=evidence,stock_root=stock)
        geometry=json.loads((prepared/'geometry.source.json').read_bytes())
        artifacts=root/'artifacts'
        for name,raw in zip(model_lab.PAIR,synthetic_records(geometry,readback.MATERIAL)):
            path=artifacts/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        return prepared,artifacts

    def test_material_source_is_separate_from_unchanged_unbound_variant(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);prepared,_=self.prepare_fixture(root)
            manifest=json.loads((prepared/'arena-writer-source.json').read_bytes())
            self.assertEqual(manifest['selected_counts']['vertices'],168)
            self.assertFalse(manifest['compiled']);self.assertFalse(manifest['physics_serialized'])
            self.assertIn('model.lodInfo[0].partBits[0]=surf.partBits[0]',(prepared/'arena_writer.cpp').read_text())
            self.assertIn(json.dumps(readback.MATERIAL),(prepared/'probe_geometry.hpp').read_text())
            unbound=root/'unbound';prepare.prepare(unbound)
            self.assertEqual(len(list(unbound.iterdir())),7)
            self.assertNotIn(readback.MATERIAL,(unbound/'probe_geometry.hpp').read_text())
            for name in ('geometry.source.json','arena.source.json','route.reference.json'):
                self.assertEqual((prepared/name).read_bytes(),(unbound/name).read_bytes())
            with self.assertRaises(ValueError):prepare.prepare(root/'partial',recipient_evidence=root/'recipient.json')

    def test_shared_recipient_validator_refuses_missing_changed_and_escape_proofs(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);tool,stock,path,evidence=self.binding_fixture(root)
            self.assertEqual(prepare_writer.validate_recipient_evidence(tool,path,stock)[0],readback.MATERIAL)
            for kind in ('empty','changed','escape','normal','runtime'):
                altered=copy.deepcopy(evidence)
                if kind=='empty':altered['material_snapshot']={}
                if kind=='changed':altered['material_snapshot']['closure']['sha256']='0'*64
                if kind=='escape':altered['material_snapshot']['closure']['path']='../recipient.json'
                if kind=='normal':altered['normal_encoding_source'].pop()
                if kind=='runtime':altered['runtime_verified']=True
                path.write_text(json.dumps(altered))
                with self.subTest(kind=kind),self.assertRaises(ValueError):
                    prepare_writer.validate_recipient_evidence(tool,path,stock)

    def test_five_payload_stage_uses_existing_zone_and_original_profile(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);prepared,artifacts=self.prepare_fixture(root)
            output=root/'stage';plan=model_lab.stage(artifacts,prepared,output)
            self.assertEqual(plan['geometry_profile'],model_lab.PROFILE)
            self.assertEqual(len(plan['source_files']),5);self.assertEqual(len(plan['validation_files']),8)
            self.assertEqual(model_lab.verify_stage(output)[0],plan)
            self.assertFalse(plan['native_provenance_verified']);self.assertFalse(plan['ready'])
            self.assertEqual((output/'zone_source/paris_model_probe.csv').read_bytes(),
                             model_lab.assets(model_lab.MODEL,model_lab.MESH)['zone_source/paris_model_probe.csv'])
            with self.assertRaises(ValueError):model_lab.stage(artifacts,prepared,output)
            isolated=subprocess.run([sys.executable,'-I','-S','-B',str(Path(model_lab.__file__)),'verify-stage',
                                      '--source',str(output)],capture_output=True,text=True,timeout=20)
            self.assertEqual(isolated.returncode,0,isolated.stderr)
            self.assertEqual(json.loads(isolated.stdout),plan)

    def test_shared_python_process_ignores_foreign_named_module_cache(self):
        with patch.dict(sys.modules,{'readback':object(),'prepare_writer':object(),'rigid_export':object(),'geometry':object()}):
            fresh=model_lab.local_module('_arena_test_foreign_cache',Path(model_lab.__file__))
            self.assertEqual(fresh.readback.MATERIAL,readback.MATERIAL)
            self.assertEqual(fresh.PIN,prepare_writer.PIN)

    def test_changed_prepared_and_every_consulted_staged_input_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);prepared,artifacts=self.prepare_fixture(root)
            output=root/'stage';plan=model_lab.stage(artifacts,prepared,output)
            header=prepared/'probe_geometry.hpp';header.write_bytes(header.read_bytes()+b'changed')
            with self.assertRaises(ValueError):model_lab.stage(artifacts,prepared,root/'bad-stage')
            for name in plan['validation_files']:
                path=output/name;original=path.read_bytes();path.write_bytes(original+b'x')
                try:
                    with self.subTest(name=name),self.assertRaises(ValueError):model_lab.verify_stage(output)
                finally:path.write_bytes(original)

    def test_redump_packed_stream_corruption_refused_and_pointer_relocation_allowed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);prepared,artifacts=self.prepare_fixture(root)
            output=root/'stage';model_lab.stage(artifacts,prepared,output)
            ff=root/'fixture.ff';ff.write_bytes(b'Original test fixture; not a native fastfile')
            proof=model_lab.verify_dump(output,artifacts,ff)
            self.assertEqual(proof['schema'],'iw7.model-original-arena-roundtrip/1')
            self.assertTrue(proof['packed_attributes_byte_identical']);self.assertFalse(proof['runtime_verified'])
            model_path=artifacts/model_lab.PAIR[0];model=model_path.read_bytes()
            changed=bytearray(model);changed[6+240]^=1;model_path.write_bytes(changed)
            with self.assertRaisesRegex(ValueError,'root part bits'):model_lab.verify_dump(output,artifacts,ff)
            model_path.write_bytes(model)
            mesh_path=artifacts/model_lab.PAIR[1];mesh=mesh_path.read_bytes()
            p=6+56+2+len(model_lab.MESH)+1+6+256+6
            for offset in (12,28):
                changed=bytearray(mesh);changed[p+offset]^=1;mesh_path.write_bytes(changed)
                with self.assertRaises(ValueError):model_lab.verify_dump(output,artifacts,ff)
            mesh_path.write_bytes(mesh)
            model_path=artifacts/model_lab.PAIR[0];model=model_path.read_bytes()
            token=b'\x08\x01'+struct.pack('<IQ',1,1)+b'\x07\x01'+readback.MATERIAL.encode()
            replacement=b'\x08\x01'+struct.pack('<IQ',1,1234)+b'\x07\x01'+readback.MATERIAL.encode()
            self.assertEqual(model.count(token),1);model_path.write_bytes(model.replace(token,replacement))
            self.assertTrue(model_lab.verify_dump(output,artifacts,ff)['geometry_roundtrip_verified'])

    @unittest.skipUnless(shutil.which('pwsh'),'PowerShell source dispatch check unavailable')
    def test_modelf_five_asset_dispatch_inventory_and_parser(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);prepared,artifacts=self.prepare_fixture(root)
            output=root/'stage';plan=model_lab.stage(artifacts,prepared,output)
            core=str(arena.REPO/'ops/model-lab/ModelFF.Core.ps1').replace("'","''")
            builder=str(arena.REPO/'ops/model-lab/Build-ModelFF.ps1').replace("'","''")
            source=str(output/'model-ff-plan.json').replace("'","''")
            script=root/'source-test.ps1'
            script.write_text("$ErrorActionPreference='Stop'\n. '"+core+"'\n"+
                "$p=Get-Content -Raw -LiteralPath '"+source+"'|ConvertFrom-Json\n"+
                "$names=@(Get-ModelFFSourceNames $p)\n"+
                "if($names.Count -ne 5 -or $names[0] -cne 'xmodel/paris_original_arena.xmb'){throw 'Arena dispatch'}\n"+
                "if(@(Get-ModelFFSourceNames ([pscustomobject]@{}))[0] -cne 'xmodel/paris_model_probe.xmb'){throw 'Cube dispatch'}\n"+
                "$p.geometry_profile='t7-iw7-resident-static-v1';$null=Get-ModelFFSourceNames $p\n"+
                "$p.geometry_profile='iw7-original-arena-rigid-v1';$p.selected_counts.vertices=$true\n"+
                "$refused=$false;try{$null=Get-ModelFFSourceNames $p}catch{$refused=$true};if(!$refused){throw 'Boolean count accepted'}\n"+
                "$tokens=$null;$errors=$null;$null=[Management.Automation.Language.Parser]::ParseFile('"+builder+"',[ref]$tokens,[ref]$errors)\n"+
                "if($errors.Count){throw ($errors|Out-String)}\n")
            result=subprocess.run([shutil.which('pwsh'),'-NoProfile','-File',str(script)],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__ == '__main__':
    unittest.main()

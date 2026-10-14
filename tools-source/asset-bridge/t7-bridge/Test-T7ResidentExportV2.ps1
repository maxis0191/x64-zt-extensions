# Invented metadata and tiny synthetic artifacts only. No operational plan or native qualification.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
. (Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
. (Join-Path $PSScriptRoot 'T7ResidentExport.Profile.ps1')
$script:checks=0
function Check([bool]$Value,[string]$Why){if(!$Value){throw $Why};$script:checks++}
function Refuses([scriptblock]$Body,[string]$Pattern){
    $caught=$false;try{$null=& $Body}catch{$caught=$true;Check ($_.Exception.Message -match $Pattern) ('Unexpected refusal: '+$_.Exception.Message)}
    Check $caught ('Expected refusal: '+$Pattern)
}
function Copy-Value($Value){$Value|ConvertTo-Json -Depth 20|ConvertFrom-Json}
function New-Geometry([int]$Count=5){
    [pscustomobject]@{
        selected_counts=[pscustomobject]@{bones=1;roots=1;surfaces=$Count;vertices=3*$Count;triangles=$Count}
        surface_records=@(for($i=0;$i -lt $Count;$i++){[pscustomobject]@{index=$i;material_slot=$i;vertices=3;triangles=1}})
        material_dependencies=@(for($i=0;$i -lt $Count;$i++){'same_material'})
        geometry_work_bytes_upper_bound=256+576*$Count
    }
}

$g=New-Geometry
Check ($g.geometry_work_bytes_upper_bound -eq 3136) 'Five-occurrence golden work size differs.'
$before=$g|ConvertTo-Json -Depth 20 -Compress
Assert-T7ResidentExportGeometryV2 $g;$script:checks++
Check (($g|ConvertTo-Json -Depth 20 -Compress) -ceq $before) 'Validation reordered or deduplicated occurrences.'
foreach($pair in @(@(1,832,816),@(255,147136,143056))){
    $value=New-Geometry $pair[0]
    Check ($value.geometry_work_bytes_upper_bound -eq $pair[1]) 'Boundary golden work size differs.'
    Assert-T7ResidentExportGeometryV2 $value;$script:checks++
    $value.geometry_work_bytes_upper_bound=$pair[2]
    Refuses {Assert-T7ResidentExportGeometryV2 $value} 'work bytes'
}

$face=New-Geometry 2
$face.surface_records[1].vertices=5;$face.surface_records[1].triangles=2
$face.selected_counts.vertices=8;$face.selected_counts.triangles=3
$face.geometry_work_bytes_upper_bound=1540
Assert-T7ResidentExportGeometryV2 $face;$script:checks++
$face.geometry_work_bytes_upper_bound=1508
Refuses {Assert-T7ResidentExportGeometryV2 $face} 'work bytes'

# Exact 16 MiB boundary, with every surface below its per-item bound.
$boundary=New-Geometry 6
for($i=0;$i -lt 6;$i++){$boundary.surface_records[$i].vertices=44500;$boundary.surface_records[$i].triangles=10482}
$boundary.surface_records[5].triangles=10478
$boundary.selected_counts.vertices=267000;$boundary.selected_counts.triangles=62888
$boundary.geometry_work_bytes_upper_bound=16777216
Assert-T7ResidentExportGeometryV2 $boundary;$script:checks++
$bad=Copy-Value $boundary;$bad.surface_records[5].triangles++;$bad.selected_counts.triangles++;$bad.geometry_work_bytes_upper_bound+=12
Refuses {Assert-T7ResidentExportGeometryV2 $bad} 'work bytes'
# The former 368*N edge is 96 bytes over the corrected cap at N=6.
$oldEdge=Copy-Value $boundary;$oldEdge.surface_records[5].triangles=10486;$oldEdge.selected_counts.triangles=62896
foreach($declared in @(16777216,16777312)){
    $oldEdge.geometry_work_bytes_upper_bound=$declared
    Refuses {Assert-T7ResidentExportGeometryV2 $oldEdge} 'work bytes'
}

foreach($spec in @(@('bones',0),@('bones',2),@('roots',0),@('roots',2),@('surfaces',0),@('surfaces',256),
    @('vertices',2),@('vertices',16711426),@('triangles',0),@('triangles',16711426))){
    $bad=Copy-Value $g;$bad.selected_counts.($spec[0])=$spec[1]
    Refuses {Assert-T7ResidentExportGeometryV2 $bad} 'geometry count'
}
foreach($field in @('bones','roots','surfaces','vertices','triangles')){
    foreach($value in @($true,'1',1.5,[long]::MaxValue)){
        $bad=Copy-Value $g;$bad.selected_counts.$field=$value
        Refuses {Assert-T7ResidentExportGeometryV2 $bad} 'geometry count'
    }
}
foreach($field in @('vertices','triangles')){
    $bad=Copy-Value $g;$bad.selected_counts.$field++
    Refuses {Assert-T7ResidentExportGeometryV2 $bad} 'Exact v2 vertex and triangle sums'
}
foreach($value in @($null,5,'rows',@())){
    $bad=Copy-Value $g;$bad.surface_records=$value
    Refuses {Assert-T7ResidentExportGeometryV2 $bad} 'surface record'
}
$bad=Copy-Value $g;$bad.surface_records=$bad.surface_records[0..3]
Refuses {Assert-T7ResidentExportGeometryV2 $bad} 'surface record'
$bad=Copy-Value $g;$bad.surface_records+=@($bad.surface_records[4])
Refuses {Assert-T7ResidentExportGeometryV2 $bad} 'surface record'
foreach($field in @('index','material_slot')){
    foreach($value in @(-1,0,2,255,'1',1.0,$true,[long]::MaxValue)){
        $bad=Copy-Value $g;$bad.surface_records[1].$field=$value
        Refuses {Assert-T7ResidentExportGeometryV2 $bad} 'Sequential v2'
    }
}
$bad=Copy-Value $g;$bad.surface_records=@($bad.surface_records[1],$bad.surface_records[0])+$bad.surface_records[2..4]
Refuses {Assert-T7ResidentExportGeometryV2 $bad} 'Sequential v2'
foreach($spec in @(@('vertices',2),@('vertices',65536),@('triangles',0),@('triangles',65536))){
    $bad=Copy-Value $g;$bad.surface_records[0].($spec[0])=$spec[1]
    Refuses {Assert-T7ResidentExportGeometryV2 $bad} 'surface count'
}
foreach($field in @('vertices','triangles')){
    foreach($value in @($true,'3',3.5,[long]::MaxValue)){
        $bad=Copy-Value $g;$bad.surface_records[0].$field=$value
        Refuses {Assert-T7ResidentExportGeometryV2 $bad} 'surface count'
    }
}
foreach($scope in @('selected_counts','surface_records')){
    $bad=Copy-Value $g;$row=if($scope -ceq 'surface_records'){$bad.surface_records[0]}else{$bad.selected_counts}
    $row|Add-Member NoteProperty extra 1
    Refuses {Assert-T7ResidentExportGeometryV2 $bad} 'Exact catalogue fields'
}
foreach($value in @($null,'same_material',@('same_material'))){
    $bad=Copy-Value $g;$bad.material_dependencies=$value
    Refuses {Assert-T7ResidentExportGeometryV2 $bad} 'material occurrence'
}
$bad=Copy-Value $g;$bad.material_dependencies=@('a','b','a','b','a')
Assert-T7ResidentExportGeometryV2 $bad;$script:checks++
Check (($bad.material_dependencies -join '|') -ceq 'a|b|a|b|a') 'Material slots were deduplicated or reordered.'
foreach($value in @('../escape',',reference',('x'*256),$false)){
    $bad=Copy-Value $g;$bad.material_dependencies[4]=$value
    Refuses {Assert-T7ResidentExportGeometryV2 $bad} 'Unsafe export'
}
foreach($value in @(0,3135,3137,832,3056,16777217,'3136',3136.0,$true,[long]::MaxValue)){
    $bad=Copy-Value $g;$bad.geometry_work_bytes_upper_bound=$value
    Refuses {Assert-T7ResidentExportGeometryV2 $bad} 'work bytes'
}
# The same material and geometry occurrence still contributes five full rows.
$bad=Copy-Value $g;$bad.geometry_work_bytes_upper_bound=832
Refuses {Assert-T7ResidentExportGeometryV2 $bad} 'work bytes'
$bad=New-Geometry 255
foreach($row in $bad.surface_records){$row.vertices=65535;$row.triangles=65535}
$bad.selected_counts.vertices=16711425;$bad.selected_counts.triangles=16711425
$bad.geometry_work_bytes_upper_bound=16MB
Refuses {Assert-T7ResidentExportGeometryV2 $bad} 'work bytes'

$request=[pscustomobject]@{schema='iw7.t7-iw7-resident-model-request/1';target='iw7';profile='resident-rigid-one-lod';zone='mp_freerun_04';model='p7_fre_platform_cap_02';lod=0}
$plan=[pscustomobject]@{Operation='ResidentExportV1';ExportRequest=$request;OutputKey=(Get-T7ResidentExportKey $request);
    ResidentMultiSurfaceV2=[pscustomobject]@{Schema='iw7.t7-resident-multi-surface/2'}}
Check ((Get-T7ResidentExportVersion $plan) -eq 2) 'Explicit v2 selection lost.'
Check ((Get-T7ResidentExportReportLimit $plan) -eq 256KB) 'V2 manifest cap differs.'
$v1Plan=Copy-Value $plan;$v1Plan.PSObject.Properties.Remove('ResidentMultiSurfaceV2')
Check ((Get-T7ResidentExportVersion $v1Plan) -eq 1) 'Historical v1 selection changed.'
Check ((Get-T7ResidentExportReportLimit $v1Plan) -eq 4KB) 'V1 manifest cap changed.'
foreach($value in @($null,$false,'v2',@([pscustomobject]@{Schema='iw7.t7-resident-multi-surface/2'}))){
    $bad=Copy-Value $plan;$bad.ResidentMultiSurfaceV2=$value
    Refuses {Get-T7ResidentExportVersion $bad} 'Exact catalogue fields'
}
foreach($schema in @('iw7.t7-resident-multisurface/2','iw7.t7-resident-multi-surface/1',2,$true)){
    $bad=Copy-Value $plan;$bad.ResidentMultiSurfaceV2.Schema=$schema
    Refuses {Get-T7ResidentExportVersion $bad} 'Explicit resident multi-surface'
}
$bad=Copy-Value $plan;$bad|Add-Member NoteProperty ResidentSurfaceCountDiagnostic $null
Refuses {Get-T7ResidentExportVersion $bad} 'cannot be mixed'
Refuses {Get-T7ResidentExportDiagnostic $bad} 'cannot be mixed'
$bad=Copy-Value $plan;$bad.Operation='Catalogue'
Refuses {Get-T7ResidentExportVersion $bad} 'Explicit resident multi-surface'

function New-Manifest([int]$Count=5){
    $geometry=New-Geometry $Count
    [pscustomobject]@{
        schema='iw7.t7-iw7-resident-export/2';requested_zone=$request.zone;source_model=$request.model;selected_source_lod=0
        output_model_name=$request.model;output_mesh_name='synthetic_mesh';output_root_key=$plan.OutputKey;target='iw7';profile=$request.profile
        geometry_profile='t7-iw7-resident-static-v2';root_bone_name='tag_origin';selected_counts=$geometry.selected_counts
        surface_records=$geometry.surface_records;material_dependencies=$geometry.material_dependencies;geometry_work_bytes_upper_bound=$geometry.geometry_work_bytes_upper_bound
        model=[pscustomobject]@{relative_path='xmodel/p7_fre_platform_cap_02.xmb';bytes=1;sha256=('a'*64)}
        mesh=[pscustomobject]@{relative_path='xsurface/synthetic_mesh.xsb';bytes=1;sha256=('b'*64)}
        zonetool_xpak_helper_reads_allowed=$false;engine_io_verified=$false;dependency_payloads_verified=$false
        asset_zone_ownership_verified=$false;serialized_parse_verified=$false;runtime_verified=$false;ready=$false
    }
}
$manifest=New-Manifest
Assert-T7ResidentExportManifest $manifest $plan;$script:checks++
Refuses {Assert-T7ResidentExportManifest $manifest $v1Plan} 'Exact catalogue fields'
foreach($spec in @(@('schema','iw7.t7-iw7-resident-export/1'),@('geometry_profile','t7-iw7-resident-static-v1'))){
    $bad=Copy-Value $manifest;$bad.($spec[0])=$spec[1]
    Refuses {Assert-T7ResidentExportManifest $bad $plan} 'request or profile'
}
foreach($field in @('surface_records','geometry_work_bytes_upper_bound')){
    $bad=Copy-Value $manifest;$bad.PSObject.Properties.Remove($field)
    Refuses {Assert-T7ResidentExportManifest $bad $plan} 'Exact catalogue fields'
}
$v1Manifest=New-Manifest 1;$v1Manifest.schema='iw7.t7-iw7-resident-export/1';$v1Manifest.geometry_profile='t7-iw7-resident-static-v1'
$v1Manifest.PSObject.Properties.Remove('surface_records');$v1Manifest.PSObject.Properties.Remove('geometry_work_bytes_upper_bound')
Assert-T7ResidentExportManifest $v1Manifest $v1Plan;$script:checks++
Refuses {Assert-T7ResidentExportManifest $v1Manifest $plan} 'Exact catalogue fields'
foreach($field in @('zonetool_xpak_helper_reads_allowed','engine_io_verified','dependency_payloads_verified',
    'asset_zone_ownership_verified','serialized_parse_verified','runtime_verified','ready')){
    $bad=Copy-Value $manifest;$bad.$field=$true
    Refuses {Assert-T7ResidentExportManifest $bad $plan} 'overclaims'
}
foreach($spec in @(@('model',(1MB+1)),@('mesh',(16MB+1)))){
    $bad=Copy-Value $manifest;$bad.($spec[0]).bytes=$spec[1]
    Refuses {Assert-T7ResidentExportManifest $bad $plan} 'artifact path'
}
$bad=Copy-Value $manifest;$bad.mesh.relative_path='xsurface/../escape.xsb'
Refuses {Assert-T7ResidentExportManifest $bad $plan} 'artifact path'

# V2 streamed provenance is opt-in; all bytes here are invented metadata.
$v2Request=[pscustomobject]@{schema='iw7.t7-iw7-selected-streamed-request/2';target='iw7';profile='selected-streamed-render-only-rigid-one-lod';
    zone='mp_freerun_04';model='p7_fre_platform_cap_02';lod=0;xpak_key='f58d58f1fc9b6b01';collision_policy='omit-source-rigid-collision-trees';
    packages=@([pscustomobject]@{path='zone/mp_initial.xpak';identity='D088B64A:000C0000001EB2FD';bytes=654311424})}
$streamPlan=Copy-Value $plan;$streamPlan|Add-Member NoteProperty SelectedStreamedRenderOnlyV2 ([pscustomobject]@{Schema='iw7.t7-selected-streamed-render-only-plan/2'})
$streamPlan|Add-Member NoteProperty SelectedXpakProvider ([pscustomobject]@{RelativePath='zone/mp_initial.xpak';FileId='D088B64A:000C0000001EB2FD';
    Metadata=[pscustomobject]@{Bytes=654311424};IndexOffset=653787136;IndexBytes=31152;EntryOffset=653815768;PayloadOffset=146723456;PayloadBytes=7680})
$savedReader=(Get-Item Function:Read-T7SelectedStreamedRequestFile).ScriptBlock
function Read-T7SelectedStreamedRequestFile($Plan){$v2Request}
try{
    $streamManifest=Copy-Value $manifest;$streamManifest.schema='iw7.t7-iw7-selected-streamed-export/2'
    $streamManifest.profile=$v2Request.profile;$streamManifest.geometry_profile='t7-iw7-selected-streamed-render-only-v2'
    $streamManifest.output_root_key=Get-T7ResidentExportOutputKey $streamPlan
    Check ($streamManifest.output_root_key -ceq 't7_iw7_streamed_e02a67b60f90ed8731320c25b72d5f5bc5c444bc1b4f50a86a0daa3745155eca') 'V2 root key differs from the independently reviewed request.'
    $streamManifest|Add-Member NoteProperty selected_mesh_payload ([pscustomobject]@{key_hex='f58d58f1fc9b6b01';source_shared_flags=9;cpu_view_shared_flags=8;
        source_surface_flags=@(32,32,32,32,32);opaque_descriptor_words_hex=@('0000000000000000','0000000000000000','0003ffffffffc000');
        descriptor_field_semantics_verified=$false;package_path='zone/mp_initial.xpak';package_identity='D088B64A:000C0000001EB2FD';file_bytes=654311424;
        hash_table_offset=653787136;hash_entry_offset=653815768;payload_offset=146723456;compressed_bytes=7680;packed_entry_size=7680;indexed_bytes=31152;
        opcodes=@(3);opaque_header_offsets=@(0);payload_bytes=18624;payload_sha256=('a'*64);headers_rechecked=$true;atomic_snapshot_proven=$false;engine_object_writes=$false})
    $streamManifest|Add-Member NoteProperty selected_collision_policy ([pscustomobject]@{policy='omit-source-rigid-collision-trees';scope='render-only';
        source_tree_present=@($true,$true,$true,$true,$true);cpu_tree_present=@($false,$false,$false,$false,$false);collision_dropped=@($true,$true,$true,$true,$true);
        collision_tree_payload_bytes_read=0;collision_conversion_attempted=$false;collision_compatibility_verified=$false;ready=$false})
    Assert-T7ResidentExportManifest $streamManifest $streamPlan;$checks++
    foreach($name in 'policy','scope'){
        $bad=Copy-Value $streamManifest;$bad.selected_collision_policy.$name=@($bad.selected_collision_policy.$name)
        Refuses {Assert-T7ResidentExportManifest $bad $streamPlan} 'Exact render-only collision scope'
    }
    $badRequest=Copy-Value $v2Request;$badRequest.collision_policy=@($badRequest.collision_policy)
    Refuses {Assert-T7SelectedStreamedRequest $badRequest -RenderOnly} 'Exact E5 render-only collision policy'
    $bad=Copy-Value $streamManifest;$bad.PSObject.Properties.Remove('selected_collision_policy')
    Refuses {Assert-T7ResidentExportManifest $bad $streamPlan} 'Exact catalogue fields'
    $bad=Copy-Value $streamManifest;$bad.selected_collision_policy.cpu_tree_present[0]=$true
    Refuses {Assert-T7ResidentExportManifest $bad $streamPlan} 'CPU view'
    Refuses {Assert-T7ResidentExportManifest $streamManifest $plan} 'Exact catalogue fields'
}finally{Set-Item Function:Read-T7SelectedStreamedRequestFile $savedReader}

$root=Join-Path ([IO.Path]::GetTempPath()) ('t7-export-v2-tests-'+[guid]::NewGuid().ToString('N'))
$context=[pscustomobject]@{Closed=$true;Lease=[pscustomobject]@{Token='synthetic-only'};Guards=[Collections.Generic.List[object]]::new()}
function Close-Guards {foreach($guard in $context.Guards){$guard.Dispose()};$context.Guards.Clear()}
function Save-Manifest($Value){[IO.File]::WriteAllText($manifestPath,($Value|ConvertTo-Json -Depth 20),[Text.UTF8Encoding]::new($false))}
try{
    $plan|Add-Member NoteProperty WorkingDirectory (Join-Path $root 'work')
    $v1Plan|Add-Member NoteProperty WorkingDirectory $plan.WorkingDirectory
    $output=Join-Path $plan.WorkingDirectory ('dump/'+$plan.OutputKey)
    foreach($dir in 'xmodel','xsurface'){$null=[IO.Directory]::CreateDirectory((Join-Path $output $dir))}
    $modelPath=Join-Path $output 'xmodel/p7_fre_platform_cap_02.xmb';$meshPath=Join-Path $output 'xsurface/synthetic_mesh.xsb'
    $manifestPath=Join-Path $output 'manifest.json'
    [IO.File]::WriteAllText($modelPath,'synthetic-model');[IO.File]::WriteAllText($meshPath,'synthetic-mesh')
    $manifest=New-Manifest 255
    for($i=0;$i -lt 255;$i++){$manifest.material_dependencies[$i]='m'*255}
    foreach($spec in @(@('model',$modelPath),@('mesh',$meshPath))){
        $manifest.($spec[0]).bytes=(Get-Item -LiteralPath $spec[1]).Length
        $manifest.($spec[0]).sha256=(Get-FileHash -LiteralPath $spec[1]).Hash.ToLowerInvariant()
    }
    Save-Manifest $manifest
    Check ((Get-Item -LiteralPath $manifestPath).Length -gt 4KB) 'Fixture must exercise the larger v2 manifest cap.'
    Refuses {Get-T7ResidentExportFiles $v1Plan} 'byte cap'
    $state=[ordered]@{ExitCode=0;ExportOutcome='NoExport'}
    Check ((Read-T7ResidentExportReport $plan $state $context) -ceq 'ExportFilesObserved') 'V2 report refused.'
    Check ($context.Guards.Count -eq 3 -and $state.SurfaceRecords.Count -eq 255 -and $state.MaterialDependencies.Count -eq 255 -and
        $state.GeometryWorkBytesUpperBound -eq 147136 -and !$state.SerializedParseVerified -and !$state.DependencyPayloadsVerified) 'V2 report lost slots, guards or qualification limits.'
    Close-Guards
    $state.ExitCode=1
    Check ((Read-T7ResidentExportReport $plan $state $context) -ceq 'ValidExportFromFailedProcess') 'Failed native process became accepted.'
    Close-Guards;$state.ExitCode=0
    $bad=Copy-Value $manifest;$bad.geometry_work_bytes_upper_bound=832;Save-Manifest $bad
    Refuses {Read-T7ResidentExportReport $plan $state $context} 'work bytes'
    Check ($context.Guards.Count -eq 1) 'Geometry limits must reject before model or mesh pins are opened.'
    Close-Guards;Save-Manifest $manifest
    $context.Closed=$false;Refuses {Read-T7ResidentExportReport $plan $state $context} 'closed with admission'
    $context.Closed=$true;$context.Lease=$null;Refuses {Read-T7ResidentExportReport $plan $state $context} 'closed with admission'
    $context.Lease=[pscustomobject]@{Token='synthetic-only'}
    $text=[IO.File]::ReadAllText($manifestPath);$padding=256KB-[Text.Encoding]::UTF8.GetByteCount($text)
    Check ($padding -gt 0) 'Synthetic manifest exceeds reviewed cap.'
    [IO.File]::WriteAllText($manifestPath,($text+(' '*$padding)),[Text.UTF8Encoding]::new($false))
    Check ((Read-T7ResidentExportReport $plan $state $context) -ceq 'ExportFilesObserved') 'Exact manifest cap refused.'
    Close-Guards
    [IO.File]::AppendAllText($manifestPath,' ')
    Refuses {Read-T7ResidentExportReport $plan $state $context} 'byte cap'
    Check ($context.Guards.Count -eq 0) 'Oversize manifest was opened or hashed.'
}finally{
    Close-Guards
    $resolved=[IO.Path]::GetFullPath($root);$parent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$resolved.StartsWith($parent,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -cnotmatch '^t7-export-v2-tests-[0-9a-f]{32}$'){throw 'Refuse cleanup outside synthetic root.'}
    if(Test-Path -LiteralPath $resolved){Remove-Item -LiteralPath $resolved -Recurse -Force}
}

[ordered]@{Status='Passed';Checks=$checks;FixtureKind='SyntheticOnly';NativeQualification='NotAssessedByGeometryFixtures';
    OwnerStockRead=$false;NativeProcessStarted=$false;RealLeaseAcquired=$false;OperationalPlanCreated=$false}|ConvertTo-Json

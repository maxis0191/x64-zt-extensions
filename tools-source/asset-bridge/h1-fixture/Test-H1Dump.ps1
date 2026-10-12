# Pure PowerShell/filesystem checks: no Add-Type, lease, compiler or native run.
[CmdletBinding()]param()
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'H1Native.Core.ps1')
$checks=0
function Check($Value,$Message){if(!$Value){throw $Message};$script:checks++}
function Refuses([scriptblock]$Action){$failed=$false;try{& $Action}catch{$failed=$true};Check $failed 'Expected refusal.'}
$legacy=[pscustomobject]@{schema='iw7.h1-parser-converter-observation/1';checks=111;vertices_checked=24;
    bone_name_observed='tag_origin';material_reference='paris_h1_original_material';
    production_parsers_executed=$true;production_converters_executed=$true;declaration_adapter=$true;
    whole_zonetool_application=$false;bone_engine_token_resolved=$false;material_complete=$false;
    lod_named_reference_linked=$false;dump_executed=$false;ff_built=$false;render_verified=$false;retail_h1_compatibility=$false}
Assert-H1Observation $legacy;$checks++
Refuses {Assert-H1Observation $legacy -Dump}
$dump=$legacy|ConvertTo-Json|ConvertFrom-Json
$dump.schema='iw7.h1-parser-converter-dump-observation/1';$dump.dump_executed=$true
$dump|Add-Member fixture_string_adapter $true
$dump|Add-Member string_calls 1
$dump|Add-Member dump_files 2
Assert-H1Observation $dump -Dump;$checks++
Refuses {Assert-H1Observation $dump}
foreach($name in 'bone_engine_token_resolved','material_complete','lod_named_reference_linked','ff_built','render_verified'){
    $changed=$dump|ConvertTo-Json|ConvertFrom-Json;$changed.$name=$true
    Refuses {Assert-H1Observation $changed -Dump}
}
foreach($pair in @(@('string_calls',2),@('dump_files',1),@('fixture_string_adapter',$false),@('dump_executed',$false))){
    $changed=$dump|ConvertTo-Json|ConvertFrom-Json;$changed.($pair[0])=$pair[1]
    Refuses {Assert-H1Observation $changed -Dump}
}
$temp=Join-Path ([IO.Path]::GetTempPath()) ('h1-dump-test-'+[guid]::NewGuid().ToString('N'))
$root=Join-Path $temp 'probe/dump/h1_original'
$folders=@($temp,(Join-Path $temp 'probe'),(Join-Path $temp 'probe/dump'),$root,
           (Join-Path $root 'xmodel'),(Join-Path $root 'xsurface'))
$model=Join-Path $root 'xmodel/paris_h1_original_cube.xmb'
$surface=Join-Path $root 'xsurface/paris_h1_original_cube_lod0.xsb'
$extra=Join-Path $root 'unexpected.bin'
$context=[pscustomobject]@{Guards=[Collections.Generic.List[object]]::new()}
function Close-Guards{foreach($g in $context.Guards){$g.Dispose()};$context.Guards.Clear()}
try{
    foreach($folder in $folders){[IO.Directory]::CreateDirectory($folder)|Out-Null}
    [IO.File]::WriteAllBytes($model,[byte[]](1,2,3));[IO.File]::WriteAllBytes($surface,[byte[]](4,5))
    $plan=[pscustomobject]@{RunRoot=$temp}
    $artifacts=@(Get-H1DumpArtifacts $plan $context)
    Check ($artifacts.Count -eq 2 -and $artifacts[0].Bytes -eq 3 -and $artifacts[1].Bytes -eq 2) 'Artifact identity/length.'
    Check ($artifacts[0].SHA256 -ceq (Get-FileHash -LiteralPath $model).Hash.ToLowerInvariant()) 'Artifact hash.'
    Refuses {[IO.File]::WriteAllBytes($model,[byte[]](9))}
    Close-Guards
    [IO.File]::WriteAllBytes($extra,[byte[]](0));Refuses {Get-H1DumpArtifacts $plan $context};[IO.File]::Delete($extra)
    [IO.File]::WriteAllBytes($model,[byte[]]::new(65537));Refuses {Get-H1DumpArtifacts $plan $context};Close-Guards
    [IO.File]::WriteAllBytes($model,[byte[]]::new(0));Refuses {Get-H1DumpArtifacts $plan $context};Close-Guards
    [IO.File]::Delete($surface);Refuses {Get-H1DumpArtifacts $plan $context}
}finally{
    Close-Guards
    # Only exact test-created files, then empty folders; no recursive delete.
    foreach($path in @($model,$surface,$extra)){if([IO.File]::Exists($path)){[IO.File]::Delete($path)}}
    [array]::Reverse($folders)
    foreach($folder in $folders){if([IO.Directory]::Exists($folder)){[IO.Directory]::Delete($folder,$false)}}
}
Check (!(('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7ResourceMemoryV1' -as [type]))) 'Native types loaded.'
[ordered]@{Schema='iw7.h1-dump-source-tests/1';Assertions=$checks;NativeTypesLoaded=$false;
    NativeExecuted=$false;LeaseAcquired=$false;SyntheticArtifactBytesOnly=$true}|ConvertTo-Json

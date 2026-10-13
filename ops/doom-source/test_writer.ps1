$ErrorActionPreference='Stop'
. "$PSScriptRoot/../Lab-Paths.ps1"
. "$PSScriptRoot/Writer.Core.ps1"
$checks=0
function Expect-Refusal([scriptblock]$Action){$refused=$false;try{& $Action}catch{$refused=$true};if(!$refused){throw 'Expected refusal.'};$script:checks++}
$manifest=[pscustomobject]@{schema='iw7.doom-rigid-writer-source/1';source_pin='fab935826c898806855376662a8a03317b3ad8f1';candidate_name='paris_doom_helmet_a';material_reference='mopw/character_park_clown_zombie_shoes';compiled=$false;ff_built=$false;pixels_verified=$false;ready=$false;
    metrics=[pscustomobject]@{vertices=3;triangles=1;height_engine_units=16;engine_units_per_metre=16;radius_engine=12};interface_hashes=[pscustomobject]@{};prepared_hashes=[pscustomobject]@{}}
$interfaces=@('utils/io/assetmanager.hpp','utils/io/filesystem.hpp','utils/memory.hpp','iw7/structs.hpp','iw7/assets/xmodel.cpp','iw7/assets/xsurface.cpp','iw7/assets/gfximage.cpp','iw7/assets/material.cpp','h1/converter/iw7/assets/xmodel.cpp','h1/converter/iw7/assets/xsurface.cpp','iw7/converter/h1/assets/xsurface.cpp','../game/shared.cpp')
foreach($name in $interfaces){$manifest.interface_hashes | Add-Member $name ('a'*64)}
foreach($name in @('writer.cpp','half_uv.hpp','rigid_geometry.hpp','geometry.source.json')){$manifest.prepared_hashes | Add-Member $name ('b'*64)}
Assert-IW7DoomWriterManifest $manifest;$checks++
foreach($value in @('3',3.1,$true,0,65536)){$manifest.metrics.vertices=$value;Expect-Refusal {Assert-IW7DoomWriterManifest $manifest}}
$manifest.metrics.vertices=3
foreach($value in @([double]::NaN,[double]::PositiveInfinity,'16',0,100001)){$manifest.metrics.engine_units_per_metre=$value;Expect-Refusal {Assert-IW7DoomWriterManifest $manifest}}
$manifest.metrics.engine_units_per_metre=16
$manifest.candidate_name='paris_model_probe';Expect-Refusal {Assert-IW7DoomWriterManifest $manifest};$manifest.candidate_name='paris_doom_helmet_a'
$manifest.prepared_hashes.'writer.cpp'='bad';Expect-Refusal {Assert-IW7DoomWriterManifest $manifest};$manifest.prepared_hashes.'writer.cpp'='b'*64
$manifest.interface_hashes | Add-Member 'other.cpp' ('a'*64);Expect-Refusal {Assert-IW7DoomWriterManifest $manifest};$manifest.interface_hashes.PSObject.Properties.Remove('other.cpp')
$roundtrip=[pscustomobject]@{schema='iw7.doom-rigid-roundtrip/1';vertices=3;triangles=1;bones=1;surfaces=1;lods=1;radius_engine_units=12;engine_units_per_metre=16;shadow_cutoff_lod=6;collision_lod=255;lod0_dist=1000000;has_lods=$true;geometry_roundtrip_verified=$true;iw7_normal_encoding_verified=$false;ff_built=$false;pixels_verified=$false;ready=$false}
Assert-IW7DoomWriterRoundtrip $manifest $roundtrip;$checks++
foreach($value in @('3',3.0,$true)){$roundtrip.vertices=$value;Expect-Refusal {Assert-IW7DoomWriterRoundtrip $manifest $roundtrip}};$roundtrip.vertices=3
foreach($field in @('ready','pixels_verified','iw7_normal_encoding_verified')){$roundtrip.$field=$true;Expect-Refusal {Assert-IW7DoomWriterRoundtrip $manifest $roundtrip};$roundtrip.$field=$false}
$roundtrip.vertices=4;Expect-Refusal {Assert-IW7DoomWriterRoundtrip $manifest $roundtrip};$roundtrip.vertices=3
$roundtrip.collision_lod=6;Expect-Refusal {Assert-IW7DoomWriterRoundtrip $manifest $roundtrip};$roundtrip.collision_lod=255
$roundtrip.engine_units_per_metre=16.1;Expect-Refusal {Assert-IW7DoomWriterRoundtrip $manifest $roundtrip}
$tokens=$null;$errors=$null
[void][System.Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Build-Writer.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Builder parse failed.'};$checks++
$text=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Build-Writer.ps1') -Raw
foreach($needle in @("'/W4','/WX'",'PhysicalBytes 2GB -CommitBytes 3GB','Assert-DoomImmutableInputs','Assert-DoomFreshOutputs','Assert-IW7DoomWriterInputBaseline','Assert-IW7DoomWriterRoundtrip')){if(!$text.Contains($needle)){throw "Builder contract missing: $needle"};$checks++}

# Synthetic input/output phase tests: no compiler, game or retail assets.
$fixture=Join-Path ([IO.Path]::GetTempPath()) ('iw7-doom-provenance-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($fixture)
$files=@('manifest.json','header.hpp','compiler.exe','writer.exe')
foreach($name in $files){[IO.File]::WriteAllText((Join-Path $fixture $name),'original bytes')}
$inputs=@($files[0..2] | ForEach-Object{[pscustomobject]@{Path=(Join-Path $fixture $_);Scope=$fixture;MaximumBytes=64KB}})
$baseline=New-IW7DoomWriterInputBaseline -Files $inputs
Assert-IW7DoomWriterInputBaseline $baseline;$checks++
$writer=New-IW7DoomWriterInputBaseline -Files @([pscustomobject]@{Path=(Join-Path $fixture 'writer.exe');Scope=$fixture;MaximumBytes=64KB})
# Outputs created by compile/run are allowed; immutable checks don't repeat
# fresh-output predicates after compilation.
[IO.File]::WriteAllText((Join-Path $fixture 'compile.log'),'retained synthetic failed/success compile diagnostics')
[void][IO.Directory]::CreateDirectory((Join-Path $fixture 'artifacts'))
Assert-IW7DoomWriterInputBaseline $baseline;Assert-IW7DoomWriterInputBaseline $writer;$checks++
foreach($name in $files){
    $path=Join-Path $fixture $name
    [IO.File]::WriteAllText($path,'modified bytes') # Same byte count, hash must detect.
    $claimPath=Join-Path $fixture 'writer-provenance.json'
    Expect-Refusal {
        Assert-IW7DoomWriterInputBaseline $baseline
        Assert-IW7DoomWriterInputBaseline $writer
        [IO.File]::WriteAllText($claimPath,'must not be claimed')
    }
    if(Test-Path -LiteralPath $claimPath){throw 'Changed input/executable received provenance claims.'};$checks++
    [IO.File]::WriteAllText($path,'original bytes')
}
Expect-Refusal {New-IW7DoomWriterInputBaseline -Files @($inputs[0],$inputs[0])}
[IO.File]::WriteAllText((Join-Path $fixture 'header.hpp'),('x'*70000))
Expect-Refusal {Assert-IW7DoomWriterInputBaseline $baseline}
# Preserve the bounded synthetic fixture and diagnostics for review.
"Provenance fixture retained: $fixture"
"Doom writer pure guards: $checks checks PASS (no compile)."

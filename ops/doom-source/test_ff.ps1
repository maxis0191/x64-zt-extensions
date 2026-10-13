$ErrorActionPreference='Stop'
. "$PSScriptRoot/../Base-Client.Core.ps1"
. "$PSScriptRoot/../model-lab/ModelFF.Core.ps1"
. "$PSScriptRoot/FF.Core.ps1"
$checks=0
function Refuse([scriptblock]$Body){$rejected=$false;try{& $Body}catch{$rejected=$true};if(!$rejected){throw 'Expected FF guard refusal.'};$script:checks++}
$name='paris_doom_helmet_rigid_a';$zone='paris_enemy_doom_helmet_rigid_a'
$plan=[pscustomobject]@{schema='iw7.doom-rigid-ff-plan/1';source_pin='fab935826c898806855376662a8a03317b3ad8f1';asset_name=$name;zone=$zone;recipient='cp_zmb';material_reference='mopw/character_park_clown_zombie_shoes';
    material_payload_copied=$false;normal_encoding_runtime_verified=$false;ff_built=$false;pixels_verified=$false;ready=$false;geometry_roundtrip_verified=$true;
    metrics=[pscustomobject]@{vertices=3;triangles=1};writer_provenance_sha256=('a'*64);reader_sha256=('b'*64);lod0_dist=1000000;has_lods=$true;shadow_cutoff_lod=6;collision_lod=255;
    source_files=[pscustomobject]@{};expected_inventory=@('material,,mopw/character_park_clown_zombie_shoes',"xmodelsurfs,${name}_lod0","xmodel,$name","netconststrings,ncs_mdl_$name","rawfile,$zone")}
$names=@("xmodel/$name.xmb","xsurface/${name}_lod0.xsb","zone_source/$zone.csv","zone_source/${zone}_recipient.csv","netconststrings/ncs_mdl_$name.json")
foreach($file in $names){$plan.source_files | Add-Member $file ('c'*64)}
$actual=@(Assert-IW7DoomFFPlan $plan);if($actual.Count -ne 5){throw 'Five files expected.'};$checks++
$log='Loading zone "'+$zone+'"'+"`n"+(@($plan.expected_inventory | ForEach-Object {$pair=$_ -split ',',2;'Loading asset "'+$pair[1]+'" of type '+$pair[0]+'.'}) -join "`n")
$rows=@(Get-IW7DoomFFInventory $log $plan);if($rows.Count -ne 5){throw 'Five inventory rows expected.'};$checks++
Refuse {Get-IW7DoomFFInventory ($log+"`nLoading asset `"foreign`" of type rawfile.") $plan}
Refuse {Get-IW7DoomFFInventory ($log+"`n[ ERROR ] failed") $plan}
Refuse {Get-IW7DoomFFInventory ($log.Replace($zone,'wrong')) $plan}
Refuse {Get-IW7DoomFFInventory ($log.Replace('Loading asset "','Loading asset ')) $plan}
foreach($value in @($true,'3',3.5,0,65536)){$plan.metrics.vertices=$value;Refuse {Assert-IW7DoomFFPlan $plan}};$plan.metrics.vertices=3
foreach($flag in @('material_payload_copied','normal_encoding_runtime_verified','ff_built','pixels_verified','ready')){$plan.$flag=$true;Refuse {Assert-IW7DoomFFPlan $plan};$plan.$flag=$false}
$plan.zone='paris_model_probe';Refuse {Assert-IW7DoomFFPlan $plan};$plan.zone=$zone
$plan.expected_inventory+=@('rawfile,foreign');Refuse {Assert-IW7DoomFFPlan $plan};$plan.expected_inventory=$plan.expected_inventory[0..4]
$fixture=Join-Path ([IO.Path]::GetTempPath()) ('iw7-doom-ff-guards-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($fixture)
foreach($file in $names){$path=Join-Path $fixture $file;[void][IO.Directory]::CreateDirectory((Split-Path $path));[IO.File]::WriteAllText($path,'synthetic bytes');$plan.source_files.$file=(Get-FileHash -LiteralPath $path).Hash}
Assert-IW7DoomFFSource $plan $fixture;$checks++
[IO.File]::WriteAllText((Join-Path $fixture $names[0]),'modified bytes!');Refuse {Assert-IW7DoomFFSource $plan $fixture}
foreach($file in @('Build-FF.ps1','FF.Core.ps1')){
    $tokens=$null;$errors=$null;[void][System.Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $file),[ref]$tokens,[ref]$errors)
    if($errors.Count){throw 'FF source parse failed.'};$checks++
}
"Doom FF pure guards: $checks checks PASS; fixture retained: $fixture"

Set-StrictMode -Version Latest
function Assert-IW7DoomWriterManifest {
    param([Parameter(Mandatory)]$Manifest)
    $pin='fab935826c898806855376662a8a03317b3ad8f1'
    foreach($flag in @('compiled','ff_built','pixels_verified','ready')) {
        if($Manifest.$flag -isnot [bool] -or $Manifest.$flag){throw 'Uncompiled Doom source-only manifest required.'}
    }
    if($Manifest.schema -cne 'iw7.doom-rigid-writer-source/1' -or $Manifest.source_pin -cne $pin -or
        $Manifest.candidate_name -cnotmatch '^paris_doom_[a-z0-9_]{1,48}$' -or
        $Manifest.material_reference -cne 'mopw/character_park_clown_zombie_shoes'){throw 'Exact Doom candidate scope required.'}
    foreach($pair in @(@('vertices',65535),@('triangles',8192))) {
        $value=$Manifest.metrics.($pair[0])
        if(($value -isnot [long] -and $value -isnot [int]) -or $value -lt 1 -or $value -gt $pair[1]){throw 'Integral bounded Doom mesh counts required.'}
    }
    foreach($pair in @(@('height_engine_units',8,64),@('engine_units_per_metre',0,100000),@('radius_engine',0,444))) {
        $value=$Manifest.metrics.($pair[0])
        if(($value -isnot [long] -and $value -isnot [int] -and $value -isnot [double]) -or
            ![double]::IsFinite([double]$value) -or $value -lt $pair[1] -or $value -gt $pair[2] -or $value -le 0){throw 'Finite bounded engine dimensions required.'}
    }
    $interfaces=@('utils/io/assetmanager.hpp','utils/io/filesystem.hpp','utils/memory.hpp','iw7/structs.hpp','iw7/assets/xmodel.cpp','iw7/assets/xsurface.cpp','iw7/assets/gfximage.cpp','iw7/assets/material.cpp','h1/converter/iw7/assets/xmodel.cpp','h1/converter/iw7/assets/xsurface.cpp','iw7/converter/h1/assets/xsurface.cpp','../game/shared.cpp')
    $prepared=@('writer.cpp','half_uv.hpp','rigid_geometry.hpp','geometry.source.json')
    foreach($pair in @(@('interface_hashes',$interfaces),@('prepared_hashes',$prepared))) {
        $properties=@($Manifest.($pair[0]).PSObject.Properties)
        if($properties.Count -ne $pair[1].Count -or @($pair[1] | Where-Object {$_ -cnotin $properties.Name}).Count){throw 'Exact Doom source provenance set required.'}
        foreach($entry in $properties){if($entry.Value -isnot [string] -or $entry.Value -cnotmatch '^[a-fA-F0-9]{64}$'){throw 'Exact source SHA256 required.'}}
    }
}
function Assert-IW7DoomWriterRoundtrip {
    param([Parameter(Mandatory)]$Manifest,[Parameter(Mandatory)]$Roundtrip)
    foreach($name in @('vertices','triangles','bones','surfaces','lods','shadow_cutoff_lod','collision_lod','lod0_dist')) {
        if($Roundtrip.$name -isnot [long] -and $Roundtrip.$name -isnot [int]){throw 'Integral measured roundtrip metadata required.'}
    }
    foreach($flag in @('geometry_roundtrip_verified','has_lods')) {
        if($Roundtrip.$flag -isnot [bool] -or !$Roundtrip.$flag){throw 'Positive measured roundtrip flags required.'}
    }
    foreach($flag in @('ready','ff_built','pixels_verified','iw7_normal_encoding_verified')) {
        if($Roundtrip.$flag -isnot [bool] -or $Roundtrip.$flag){throw 'Roundtrip cannot claim renderer/encoding acceptance.'}
    }
    if($Roundtrip.schema -cne 'iw7.doom-rigid-roundtrip/1' -or
        $Roundtrip.vertices -ne $Manifest.metrics.vertices -or $Roundtrip.triangles -ne $Manifest.metrics.triangles -or
        $Roundtrip.bones -ne 1 -or $Roundtrip.surfaces -ne 1 -or $Roundtrip.lods -ne 1 -or
        $Roundtrip.shadow_cutoff_lod -ne 6 -or $Roundtrip.collision_lod -ne 255 -or $Roundtrip.lod0_dist -ne 1000000){throw 'Doom measured counts/LOD metadata differ.'}
    foreach($pair in @(@('radius_engine_units','radius_engine'),@('engine_units_per_metre','engine_units_per_metre'))) {
        $value=$Roundtrip.($pair[0]);$expected=[double]$Manifest.metrics.($pair[1])
        if(($value -isnot [double] -and $value -isnot [int] -and $value -isnot [long]) -or
            ![double]::IsFinite([double]$value) -or [math]::Abs([double]$value-$expected) -gt [math]::Max(0.00001,[math]::Abs($expected)*0.000001)){throw 'Roundtrip engine scale/radius differ.'}
    }
}

# These are bounded content snapshots before/after execution, not a claim that
# another process could never transiently write an input between snapshots.
function New-IW7DoomWriterInputBaseline {
    param([Parameter(Mandatory)][object[]]$Files)
    $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $rows=@(foreach($file in $Files){
        $path=Assert-IW7LabPath ([IO.Path]::GetFullPath($file.Path)) $file.Scope
        if(!$seen.Add($path)){throw 'Duplicate writer provenance input.'}
        $item=Get-Item -LiteralPath $path
        if($item.PSIsContainer -or $item.Length -le 0 -or $item.Length -gt $file.MaximumBytes){throw 'Bounded regular writer provenance input required.'}
        [pscustomobject]@{Path=$path;Scope=$file.Scope;MaximumBytes=[long]$file.MaximumBytes;Bytes=[long]$item.Length;SHA256=(Get-FileHash -LiteralPath $path).Hash}
    })
    if(!$rows.Count){throw 'Nonempty writer provenance input set required.'}
    return [pscustomobject]@{Schema='iw7.doom-writer-input-baseline/1';CapturedUtc=[DateTime]::UtcNow.ToString('o');Files=$rows}
}
function Assert-IW7DoomWriterInputBaseline {
    param([Parameter(Mandatory)]$Baseline)
    if($Baseline.Schema -cne 'iw7.doom-writer-input-baseline/1' -or !$Baseline.Files.Count){throw 'Exact writer input baseline required.'}
    $current=New-IW7DoomWriterInputBaseline -Files $Baseline.Files
    for($index=0;$index -lt $Baseline.Files.Count;$index++){
        $expected=$Baseline.Files[$index];$actual=$current.Files[$index]
        if($actual.Path -cne $expected.Path -or $actual.Bytes -ne $expected.Bytes -or $actual.SHA256 -cne $expected.SHA256){throw "Writer provenance input changed: $($expected.Path)"}
    }
}

# Doom rigid FF contracts; importing this file launches or mutates nothing.
function Assert-IW7DoomFFPlan($Plan) {
    if($Plan.schema -cne 'iw7.doom-rigid-ff-plan/1' -or $Plan.source_pin -cne 'fab935826c898806855376662a8a03317b3ad8f1' -or
        $Plan.asset_name -cnotmatch '^paris_doom_[a-z0-9_]{1,48}$' -or
        $Plan.zone -cne ('paris_enemy_'+$Plan.asset_name.Substring(6)) -or
        $Plan.material_reference -cne 'mopw/character_park_clown_zombie_shoes' -or $Plan.recipient -cne 'cp_zmb') {throw 'Exact Doom rigid zone/material scope required.'}
    foreach($flag in @('material_payload_copied','normal_encoding_runtime_verified','ff_built','pixels_verified','ready')) {
        if($Plan.$flag -isnot [bool] -or $Plan.$flag){throw 'Unbuilt source-only FF plan required.'}
    }
    if($Plan.geometry_roundtrip_verified -isnot [bool] -or !$Plan.geometry_roundtrip_verified){throw 'Measured writer roundtrip required.'}
    Assert-ModelFFDistanceCandidate $Plan
    foreach($pair in @(@('vertices',65535),@('triangles',8192))) {
        $value=$Plan.metrics.($pair[0]);if(($value -isnot [int] -and $value -isnot [long]) -or $value -lt 1 -or $value -gt $pair[1]){throw 'Integral bounded FF mesh counts required.'}
    }
    foreach($name in @('writer_provenance_sha256','reader_sha256')){if($Plan.$name -cnotmatch '^[a-fA-F0-9]{64}$'){throw 'Exact writer/reader SHA256 required.'}}
    $expectedFiles=@("xmodel/$($Plan.asset_name).xmb","xsurface/$($Plan.asset_name)_lod0.xsb","zone_source/$($Plan.zone).csv","zone_source/$($Plan.zone)_recipient.csv","netconststrings/ncs_mdl_$($Plan.asset_name).json")
    $properties=@($Plan.source_files.PSObject.Properties)
    if($properties.Count -ne 5 -or @($expectedFiles | Where-Object {$_ -cnotin $properties.Name}).Count){throw 'Exact five-input Doom FF preparation required.'}
    foreach($entry in $properties){if($entry.Value -isnot [string] -or $entry.Value -cnotmatch '^[a-fA-F0-9]{64}$'){throw 'Exact staged input SHA256 required.'}}
    $expected=@('material,,mopw/character_park_clown_zombie_shoes',"xmodelsurfs,$($Plan.asset_name)_lod0","xmodel,$($Plan.asset_name)","netconststrings,ncs_mdl_$($Plan.asset_name)","rawfile,$($Plan.zone)")
    if(@($Plan.expected_inventory).Count -ne 5 -or @($Plan.expected_inventory | Sort-Object -Unique).Count -ne 5 -or @($expected | Where-Object {$_ -cnotin $Plan.expected_inventory}).Count){throw 'Exact typed Doom inventory required.'}
    $expectedFiles
}

function Get-IW7DoomFFInventory([string]$Log,$Plan) {
    $null=Assert-IW7DoomFFPlan $Plan
    if(!$Log.Contains('Loading zone "'+$Plan.zone+'"') -or $Log -match 'could not be found|Could not find referenced|\[ ERROR \]|\[ FATAL \]'){throw 'Doom bootstrap inventory unavailable/recipient reference unresolved.'}
    $rows=@(foreach($line in @($Log -split '\r?\n' | Where-Object {$_ -match 'Loading asset '})){
        if($line -notmatch 'Loading asset "([^"\r\n]+)" of type ([a-z0-9]+)\.$'){throw 'Malformed Doom inventory callback.'}
        $Matches[2]+','+$Matches[1]
    })
    if($rows.Count -ne 5 -or @($rows | Sort-Object -Unique).Count -ne 5 -or @($Plan.expected_inventory | Where-Object {$_ -cnotin $rows}).Count){throw 'Unexpected assets in minimal Doom FF.'}
    $rows
}

function Assert-IW7DoomFFSource($Plan,[string]$Source) {
    foreach($name in @(Assert-IW7DoomFFPlan $Plan)) {
        $path=Resolve-IW7BasePath $Source $name
        $file=Get-Item -LiteralPath $path
        if($file.PSIsContainer -or $file.Length -le 0 -or $file.Length -gt 4MB -or (Get-FileHash -LiteralPath $path).Hash -ine $Plan.source_files.$name){throw 'Doom FF staged source changed.'}
    }
}

# No mutations/launch on import. Model wrapper uses existing transactions and NTFS identity.
function Assert-ModelFFDistanceCandidate($Metadata) {
    if(($Metadata.lod0_dist -isnot [int] -and $Metadata.lod0_dist -isnot [long] -and $Metadata.lod0_dist -isnot [double]) -or
        $Metadata.lod0_dist -ne 1000000 -or $Metadata.has_lods -isnot [bool] -or !$Metadata.has_lods -or
        $Metadata.shadow_cutoff_lod -ne 6 -or $Metadata.collision_lod -ne 255){throw 'Exact single-LOD distance candidate metadata required.'}
}
function Assert-ModelFFAssetName([string]$Name) {
    if($Name -cnotmatch '^[A-Za-z0-9_][A-Za-z0-9_./-]{0,254}$'){throw 'Portable Model Lab asset name required.'}
    foreach($part in $Name.Split('/')){
        if(!$part -or $part -in @('.','..') -or $part.EndsWith('.') -or $part -match '^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\.|$)'){throw 'Unsafe Model Lab asset path.'}
    }
}
function Get-ModelFFRigidVersion($Metadata) {
    switch -CaseSensitive ($Metadata.geometry_profile) {
        't7-iw7-resident-static-v1' {return 1}
        't7-iw7-resident-static-v2' {return 2}
        default {throw 'Unknown resident geometry profile.'}
    }
}
function Get-ModelFFMaterials($Metadata) {
    if($Metadata.geometry_profile -ceq 'iw7-original-arena-rigid-v1'){return $Metadata.material_reference}
    if((Get-ModelFFRigidVersion $Metadata) -eq 2){$Metadata.material_references}else{$Metadata.material_reference}
}
function Assert-ModelFFOriginalArenaGeometry($Metadata) {
    if($Metadata.geometry_profile -cne 'iw7-original-arena-rigid-v1' -or $Metadata.origin -cne 'authored-arena' -or
        $Metadata.model_name -cne 'paris_original_arena' -or $Metadata.mesh_name -cne 'paris_original_arena_lod0' -or
        $Metadata.material_reference -cne 'mopw/character_park_clown_zombie_shoes'){throw 'Explicit original arena identity/material required.'}
    $counts=$Metadata.selected_counts
    if((@($counts.PSObject.Properties.Name | Sort-Object) -join ',') -cne 'bones,roots,surfaces,triangles,vertices'){throw 'Exact original arena count fields required.'}
    foreach($entry in @(@('bones',1,1),@('roots',1,1),@('surfaces',1,1),@('vertices',24,192),@('triangles',12,96))){
        $value=$counts.($entry[0])
        if(($value -isnot [int] -and $value -isnot [long]) -or $value -lt $entry[1] -or $value -gt $entry[2]){throw 'Original arena count outside small rigid profile.'}
    }
    if($counts.vertices % 24 -ne 0 -or $counts.triangles*2 -ne $counts.vertices){throw 'Original box topology counts differ.'}
}
function Assert-ModelFFOriginalArenaPlan($Plan) {
    Assert-ModelFFOriginalArenaGeometry $Plan
    Assert-ModelFFDistanceCandidate $Plan
    if($Plan.schema -cne 'iw7.model-ff-plan/1' -or $Plan.zone -cne 'paris_model_probe' -or $Plan.recipient -cne 'cp_zmb' -or
        $Plan.material_payload_copied -isnot [bool] -or $Plan.material_payload_copied -or
        $Plan.physics_serialized -isnot [bool] -or $Plan.physics_serialized){throw 'Original arena recipient/reference-only profile required.'}
}
function Assert-ModelFFRigidGeometry($Metadata) {
    $version=Get-ModelFFRigidVersion $Metadata
    $counts=$Metadata.selected_counts
    if((@($counts.PSObject.Properties.Name | Sort-Object) -join ',') -cne 'bones,roots,surfaces,triangles,vertices'){throw 'Exact resident count fields required.'}
    $maxSurfaces=if($version -eq 2){255}else{1}
    foreach($entry in @(@('bones',1,1),@('roots',1,1),@('surfaces',1,$maxSurfaces),@('vertices',3,(65535*$maxSurfaces)),@('triangles',1,(65535*$maxSurfaces)))){
        $value=$counts.($entry[0])
        if(($value -isnot [int] -and $value -isnot [long]) -or $value -lt $entry[1] -or $value -gt $entry[2]){throw 'Rigid geometry count outside resident profile.'}
    }
    if($version -eq 1){
        if($Metadata.material_reference -cne 'mopw/character_park_clown_zombie_shoes' -or
            @('surface_records','geometry_work_bytes_upper_bound','material_references' | Where-Object {$_ -cin $Metadata.PSObject.Properties.Name}).Count){throw 'Strict v1 material/surface profile required.'}
        return
    }
    if('material_reference' -cin $Metadata.PSObject.Properties.Name -or $Metadata.material_references -isnot [array] -or
        $Metadata.surface_records -isnot [array] -or $Metadata.material_references.Count -ne $counts.surfaces -or
        $Metadata.surface_records.Count -ne $counts.surfaces){throw 'Ordered v2 material/surface arrays required.'}
    [long]$vertices=0;[long]$triangles=0
    for($i=0;$i -lt $counts.surfaces;$i++){
        $record=$Metadata.surface_records[$i]
        if((@($record.PSObject.Properties.Name | Sort-Object) -join ',') -cne 'index,material_slot,triangles,vertices'){throw 'Exact surface record fields required.'}
        foreach($entry in @(@('index',$i,$i),@('material_slot',$i,$i),@('vertices',3,65535),@('triangles',1,65535))){
            $value=$record.($entry[0])
            if(($value -isnot [int] -and $value -isnot [long]) -or $value -lt $entry[1] -or $value -gt $entry[2]){throw 'Invalid ordered surface record.'}
        }
        if($Metadata.material_references[$i] -cne 'mopw/character_park_clown_zombie_shoes'){throw 'Unreviewed recipient material.'}
        $vertices+=$record.vertices;$triangles+=$record.triangles
    }
    # Includes the 96-byte T7 surface. Aliases count in full per logical slot.
    [long]$work=256+384*$counts.surfaces+60*$vertices+12*$triangles
    if($vertices -ne $counts.vertices -or $triangles -ne $counts.triangles -or $work -gt 16MB -or
        ($Metadata.geometry_work_bytes_upper_bound -isnot [int] -and $Metadata.geometry_work_bytes_upper_bound -isnot [long]) -or
        $Metadata.geometry_work_bytes_upper_bound -ne $work){throw 'Aggregate resident geometry work exceeds bound or differs.'}
}
function Assert-ModelFFRigidPlan($Plan) {
    Assert-ModelFFAssetName $Plan.model_name;Assert-ModelFFAssetName $Plan.mesh_name
    Assert-ModelFFRigidGeometry $Plan
    $version=Get-ModelFFRigidVersion $Plan
    if($Plan.schema -cne "iw7.model-ff-plan/$version" -or $Plan.zone -cne 'paris_model_probe' -or $Plan.recipient -cne 'cp_zmb' -or
        $Plan.material_payload_copied -isnot [bool] -or $Plan.material_payload_copied -or
        $Plan.has_lods -isnot [bool] -or !$Plan.has_lods -or $Plan.shadow_cutoff_lod -ne 6 -or $Plan.collision_lod -ne 255){throw 'Bounded rigid recipient/LOD profile required.'}
    if(($Plan.lod0_dist -isnot [int] -and $Plan.lod0_dist -isnot [long] -and $Plan.lod0_dist -isnot [double]) -or
        [double]::IsNaN($Plan.lod0_dist) -or [double]::IsInfinity($Plan.lod0_dist) -or $Plan.lod0_dist -gt [float]::MaxValue -or $Plan.lod0_dist -lt 256){
        throw 'LOD distance insufficient for this scene; review explicit --lod-distance 1000000. Export validity and visibility are separate.'}
}
function Get-ModelFFSourceNames($Plan) {
    if('geometry_profile' -cin $Plan.PSObject.Properties.Name){
        if($Plan.geometry_profile -ceq 'iw7-original-arena-rigid-v1'){Assert-ModelFFOriginalArenaPlan $Plan}
        else{Assert-ModelFFRigidPlan $Plan}
        "xmodel/$($Plan.model_name).xmb";"xsurface/$($Plan.mesh_name).xsb"
    }else{'xmodel/paris_model_probe.xmb';'xsurface/paris_model_probe_lod0.xsb'}
    'zone_source/paris_model_probe.csv';'zone_source/paris_model_probe_recipient.csv';'netconststrings/ncs_mdl_paris_model_probe.json'
}
function Write-ModelFFState($State,[string]$Path) { $State | ConvertTo-Json -Depth 15 | Set-Content -LiteralPath $Path }
function Assert-ModelFFVacant([string]$Work) {
    foreach($p in @(Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^(iw7|zonetool).*\.exe$'})) {
        if($p.ExecutablePath -and ([IO.Path]::GetFullPath($p.ExecutablePath)).StartsWith($Work+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Model tool work directory remains occupied; retain inputs and reservation.'}
    }
}
function Assert-ModelFFInputs($Inputs,[string]$Work,[switch]$SourceOnly) {
    foreach($entry in $Inputs){
        $null=Resolve-IW7BasePath (Split-Path $entry.Source -Parent) (Split-Path $entry.Source -Leaf)
        $file=Get-Item -LiteralPath $entry.Source
        if($file.Length -ne $entry.Bytes -or $file.LastWriteTimeUtc.Ticks -ne ([datetimeoffset]$entry.ModifiedUtc).UtcDateTime.Ticks -or
            [int]$file.Attributes -ne $entry.Attributes -or [IW7HudFileIdentity]::Read($entry.Source) -cne $entry.SourceId){throw 'Stock source identity/size/time/attributes changed; restoration refused.'}
        if(!$SourceOnly){
            $target=Resolve-IW7BasePath $Work $entry.Relative
            if('TargetId' -cnotin $entry.PSObject.Properties.Name){if(Test-Path -LiteralPath $target){throw 'Unrecorded staged input exists; retain reservation.'};continue}
            if([IW7HudFileIdentity]::Read($target) -cne $entry.TargetId -or ($entry.Mode -eq 'HardLink' -and (Get-Item -LiteralPath $target).Length -ne $entry.Bytes)){throw 'Owned input identity/size changed; restoration refused.'}
        }
    }
}
function Complete-ModelFFRestore($State,[string]$StatePath,[string]$LeaseToken) {
    try {
        Assert-ModelFFVacant $State.Work
        Assert-ModelFFInputs $State.Inputs $State.Work
        Restore-IW7BaseTransaction $State.Transaction
        Assert-ModelFFInputs $State.Inputs $State.Work -SourceOnly
        $State.Restored=$true;$State.StockPreserved=$true;$State.RestorationStatus='Confirmed'
        Write-ModelFFState $State $StatePath
    } catch {
        $State.RestorationStatus='Refused';$State.CleanupError=$_.Exception.Message
        Write-ModelFFState $State $StatePath
        throw
    }
    # Release follows both restore and source-final proof, never from finally.
    Exit-IW7ResourceLease -Token $LeaseToken
    $State.RetainedLeaseToken=$null;Write-ModelFFState $State $StatePath
}
function Get-ModelFFInventory([string]$Log,[string]$ModelName='paris_model_probe',[string]$MeshName='paris_model_probe_lod0',[string[]]$Materials=@('mopw/character_park_clown_zombie_shoes')) {
    Assert-ModelFFAssetName $ModelName;Assert-ModelFFAssetName $MeshName
    if(!$Log.Contains('Loading zone "paris_model_probe"') -or $Log -match 'could not be found|Could not find referenced|\[ ERROR \]|\[ FATAL \]'){throw 'Bootstrap inventory unavailable/recipient reference unresolved.'}
    $rows=@(foreach($line in @($Log -split '\r?\n' | Where-Object {$_ -match 'Loading asset '})){
        if($line -notmatch 'Loading asset "([^"\r\n]+)" of type ([a-z0-9]+)\.$'){throw 'Malformed model inventory callback.'}
        $Matches[2]+','+$Matches[1]
    })
    if(!$Materials.Count -or $Materials.Count -gt 255 -or @($Materials | Where-Object {$_ -cne 'mopw/character_park_clown_zombie_shoes'}).Count){throw 'Explicit reviewed material inventory required.'}
    $expected=@(@($Materials | Select-Object -Unique | ForEach-Object {'material,,'+$_}) + @("xmodelsurfs,$MeshName","xmodel,$ModelName",'netconststrings,ncs_mdl_paris_model_probe','rawfile,paris_model_probe'))
    if($rows.Count -ne $expected.Count -or @($rows | Sort-Object -Unique).Count -ne $expected.Count -or @($expected | Where-Object {$_ -cnotin $rows}).Count){throw 'Expected exact assets including unique recipient references.'}
    $rows
}

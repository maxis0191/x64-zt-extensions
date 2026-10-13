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
function Assert-ModelFFRigidPlan($Plan) {
    Assert-ModelFFAssetName $Plan.model_name;Assert-ModelFFAssetName $Plan.mesh_name
    if($Plan.geometry_profile -cne 't7-iw7-resident-static-v1' -or $Plan.zone -cne 'paris_model_probe' -or
        $Plan.recipient -cne 'cp_zmb' -or $Plan.material_reference -cne 'mopw/character_park_clown_zombie_shoes' -or
        $Plan.material_payload_copied -isnot [bool] -or $Plan.material_payload_copied -or
        $Plan.has_lods -isnot [bool] -or !$Plan.has_lods -or $Plan.shadow_cutoff_lod -ne 6 -or $Plan.collision_lod -ne 255){throw 'Bounded rigid recipient/LOD profile required.'}
    foreach($entry in @(@('bones',1,1),@('roots',1,1),@('surfaces',1,1),@('vertices',3,65535),@('triangles',1,65535))){
        $value=$Plan.selected_counts.($entry[0])
        if(($value -isnot [int] -and $value -isnot [long]) -or $value -lt $entry[1] -or $value -gt $entry[2]){throw 'Rigid geometry count outside resident profile.'}
    }
    if(($Plan.lod0_dist -isnot [int] -and $Plan.lod0_dist -isnot [long] -and $Plan.lod0_dist -isnot [double]) -or
        [double]::IsNaN($Plan.lod0_dist) -or [double]::IsInfinity($Plan.lod0_dist) -or $Plan.lod0_dist -gt [float]::MaxValue -or $Plan.lod0_dist -lt 256){
        throw 'LOD distance insufficient for this scene; review explicit --lod-distance 1000000. Export validity and visibility are separate.'}
}
function Get-ModelFFSourceNames($Plan) {
    if('geometry_profile' -cin $Plan.PSObject.Properties.Name){
        Assert-ModelFFRigidPlan $Plan
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
function Get-ModelFFInventory([string]$Log,[string]$ModelName='paris_model_probe',[string]$MeshName='paris_model_probe_lod0') {
    Assert-ModelFFAssetName $ModelName;Assert-ModelFFAssetName $MeshName
    if(!$Log.Contains('Loading zone "paris_model_probe"') -or $Log -match 'could not be found|Could not find referenced|\[ ERROR \]|\[ FATAL \]'){throw 'Bootstrap inventory unavailable/recipient reference unresolved.'}
    $rows=@(foreach($line in @($Log -split '\r?\n' | Where-Object {$_ -match 'Loading asset '})){
        if($line -notmatch 'Loading asset "([^"\r\n]+)" of type ([a-z0-9]+)\.$'){throw 'Malformed model inventory callback.'}
        $Matches[2]+','+$Matches[1]
    })
    $expected=@('material,,mopw/character_park_clown_zombie_shoes',"xmodelsurfs,$MeshName","xmodel,$ModelName",'netconststrings,ncs_mdl_paris_model_probe','rawfile,paris_model_probe')
    if($rows.Count -ne 5 -or @($rows | Sort-Object -Unique).Count -ne 5 -or @($expected | Where-Object {$_ -cnotin $rows}).Count){throw 'Expected exact five assets including recipient reference.'}
    $rows
}

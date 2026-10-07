# No mutations/launch on import. Model wrapper uses existing transactions and NTFS identity.
function Assert-ModelFFDistanceCandidate($Metadata) {
    if(($Metadata.lod0_dist -isnot [int] -and $Metadata.lod0_dist -isnot [long] -and $Metadata.lod0_dist -isnot [double]) -or
        $Metadata.lod0_dist -ne 1000000 -or $Metadata.has_lods -isnot [bool] -or !$Metadata.has_lods -or
        $Metadata.shadow_cutoff_lod -ne 6 -or $Metadata.collision_lod -ne 255){throw 'Exact single-LOD distance candidate metadata required.'}
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
function Get-ModelFFInventory([string]$Log) {
    if(!$Log.Contains('Loading zone "paris_model_probe"') -or $Log -match 'could not be found|Could not find referenced|\[ ERROR \]|\[ FATAL \]'){throw 'Bootstrap inventory unavailable/recipient reference unresolved.'}
    $rows=@(foreach($line in @($Log -split '\r?\n' | Where-Object {$_ -match 'Loading asset '})){
        if($line -notmatch 'Loading asset "([^"\r\n]+)" of type ([a-z0-9]+)\.$'){throw 'Malformed model inventory callback.'}
        $Matches[2]+','+$Matches[1]
    })
    $expected=@('material,,mopw/character_park_clown_zombie_shoes','xmodelsurfs,paris_model_probe_lod0','xmodel,paris_model_probe','netconststrings,ncs_mdl_paris_model_probe','rawfile,paris_model_probe')
    if($rows.Count -ne 5 -or @($rows | Sort-Object -Unique).Count -ne 5 -or @($expected | Where-Object {$_ -cnotin $rows}).Count){throw 'Expected exact five assets including recipient reference.'}
    $rows
}

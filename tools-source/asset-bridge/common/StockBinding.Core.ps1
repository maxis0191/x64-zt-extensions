# Pure receipt contract for the existing 72-entry FF stock profile. No native
# import, inventory, asset hashing, staging or lease occurs when importing it.
function Get-FFStockCanonicalPath([string]$Path) {
    if(!$Path -or ![IO.Path]::IsPathFullyQualified($Path)){throw 'Canonical absolute stock path required.'}
    $full=[IO.Path]::GetFullPath($Path)
    if($full -ine $Path){throw 'Canonical absolute stock path required.'}
    $full
}
function Get-FFStockBindingInputs($Baseline,$Observation,$Reviewed,[string]$StockRoot,
    [string]$BaselineSHA256,[string]$ReviewedSHA256) {
    # The caller first hashes/reads the two historical receipts and observation.
    # This function validates only their content; it does not repeat inventory.
    if($BaselineSHA256 -ine '4cf67ebe1645c6c0761b9a24cb4e4630edee9c5d737742c704d624fe60cb3850' -or
        $ReviewedSHA256 -ine '9116255ef148a324df15fa914795a7917615f023973111fdc39ae7329a9dcbf4' -or
        $Baseline.Schema -cne 'iw7.model-ff-build/1' -or !$Baseline.Restored -or !$Baseline.StockPreserved -or $Baseline.RetainedLeaseToken -or
        @($Baseline.Inputs).Count -ne 72 -or @($Baseline.Inputs|Where-Object Mode -CEQ HardLink).Count -ne 63 -or
        @($Baseline.Inputs|Where-Object Mode -CEQ Copy).Count -ne 9){throw 'Exact reviewed historical 63-link/9-copy stock profile required.'}
    $root=Get-FFStockCanonicalPath $StockRoot
    if($Observation.Schema -cne 'iw7.ff-stock-observation/1' -or $Observation.BaselineReceiptSHA256 -ine $BaselineSHA256 -or
        $Observation.ReviewedStockManifestSHA256 -ine $ReviewedSHA256 -or $Observation.StockRoot -ine $root -or
        @($Observation.Inputs).Count -ne 72){throw 'Exact hash-bound 72-entry stock observation required.'}
    try{$captured=[datetimeoffset]$Observation.CapturedUtc;if($captured.Year -lt 2000){throw 'date'}}catch{throw 'Stock observation capture time required.'}
    if(@('Restored','StockPreserved','Transaction','RetainedLeaseToken'|Where-Object {$_ -cin $Observation.PSObject.Properties.Name}).Count){throw 'A stock observation cannot claim a restoration transaction.'}
    $base=@{};foreach($entry in $Baseline.Inputs){if($base.ContainsKey($entry.Relative)){throw 'Duplicate historical stock relative.'};$base[$entry.Relative]=$entry}
    $review=@{};foreach($entry in $Reviewed){
        if(!$entry.RelativePath -or $review.ContainsKey($entry.RelativePath) -or $entry.Operation -cne 'NTFSHardLinkImmutableStock' -or
            $entry.SHA256 -cnotmatch '^[a-fA-F0-9]{64}$'){throw 'Reviewed stock content manifest malformed.'}
        $review[$entry.RelativePath]=$entry
    }
    $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($entry in $Observation.Inputs){
        $old=$base[$entry.Relative]
        if(!$old -or !$seen.Add($entry.Relative) -or $entry.Relative -cne $old.Relative -or $entry.Bytes -ne $old.Bytes -or
            $entry.Mode -cne $old.Mode -or $entry.SourceId -cnotmatch '^[A-F0-9]{8}:[A-F0-9]{16}$' -or
            $entry.SHA256 -cnotmatch '^[a-fA-F0-9]{64}$' -or 'TargetId' -cin $entry.PSObject.Properties.Name){throw 'Stock observation relative/mode/bytes/identity differs.'}
        $source=Get-FFStockCanonicalPath $entry.Source
        if($entry.ExternalToolDependency -eq $true){
            if($entry.Relative -cne 'tlsdll.dll' -or $entry.Mode -cne 'Copy' -or $entry.Bytes -ne 113152 -or
                $entry.SHA256 -ine '6E00DBE90E4CCB60283FAD72A769B36542E587019A0DA9FA42CB6A0FCF91207A' -or
                $entry.ReviewedStockRelative -or $source.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)){
                throw 'Only the exact external TLS dependency is permitted.'
            }
        }else{
            $row=$review[$entry.ReviewedStockRelative]
            # The reviewed root names bind main/zone aliases to the same content.
            $reviewRelative=if($entry.Relative -match '^(main|zone)/([^/]+\.ff)$' -or $entry.Relative -ceq 'zone/assetfile1.pak'){[IO.Path]::GetFileName($entry.Relative)}else{$entry.Relative}
            $expected=[IO.Path]::GetFullPath((Join-Path $root $reviewRelative))
            if(!$row -or $entry.ReviewedStockRelative -cne $reviewRelative -or $row.RelativePath -cne $reviewRelative -or
                $row.Length -ne $entry.Bytes -or $row.SHA256 -ine $entry.SHA256 -or $source -ine $expected -or
                !$source.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Observed source does not match reviewed retail content/path.'}
        }
        try{$modified=([datetimeoffset]$entry.ModifiedUtc).UtcDateTime;if($modified.Year -lt 2000){throw 'date'}}catch{throw 'Stock modification time missing.'}
        if(($entry.Attributes -isnot [int] -and $entry.Attributes -isnot [long]) -or $entry.Attributes -lt 0 -or
            ($entry.Attributes -band ([int][IO.FileAttributes]::Directory -bor [int][IO.FileAttributes]::ReparsePoint)) -or
            (($entry.Attributes -band [IO.FileAttributes]::ReadOnly) -and $entry.Relative -cne 'main/fileSysCheck.cfg')){throw 'Only the copied sentinel may be read-only; redirected stock refused.'}
        [pscustomobject]@{Relative=$entry.Relative;Source=$source;Mode=$entry.Mode;Bytes=$entry.Bytes;ModifiedUtc=$modified.ToString('o');
            Attributes=[int]$entry.Attributes;ExpectedSourceId=$entry.SourceId;ExpectedSHA256=$entry.SHA256}
    }
}
function Assert-FFStockIdentity($Entry,[string]$ActualIdentity) {
    if('ExpectedSourceId' -cin $Entry.PSObject.Properties.Name -and $Entry.ExpectedSourceId -cne $ActualIdentity){throw 'Observed stock NTFS identity changed; no staging permitted.'}
}
function Assert-FFStockContent($Inputs) {
    # Call only under the complete admission, with every source guarded and its
    # real SourceId already captured/checked. Cache solely by that verified ID.
    $hashes=@{}
    foreach($entry in $Inputs|Where-Object {'ExpectedSHA256' -cin $_.PSObject.Properties.Name}){
        if(!$entry.SourceId -or $entry.SourceId -cne $entry.ExpectedSourceId){throw 'Guarded observed source identity required before content hashing.'}
        if(!$hashes.ContainsKey($entry.SourceId)){$hashes[$entry.SourceId]=(Get-FileHash -LiteralPath $entry.Source -Algorithm SHA256).Hash}
        if($hashes[$entry.SourceId] -ine $entry.ExpectedSHA256){throw 'Observed stock content changed; no staging permitted.'}
    }
}

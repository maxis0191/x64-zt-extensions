# Pure supplemental receipt contract. No inventory, hashing, native import or
# staging on import/plan. The historical 72-entry FF binding stays unchanged.
function Get-RecipientSupplementalStockInputs($Observation,$Reviewed,[string]$StockRoot,[string]$ReviewedSHA256) {
    $root=Get-FFStockCanonicalPath $StockRoot
    $names=@('assetfile17.pak','assetfile19.pak','assetfile37.pak','assetfile53.pak')
    if($ReviewedSHA256 -ine '9116255ef148a324df15fa914795a7917615f023973111fdc39ae7329a9dcbf4' -or
       $Observation.Schema -cne 'iw7.recipient-stock-observation/1' -or
       $Observation.Profile -cne 'observed-cp-paks-17-19-37-53' -or
       $Observation.ToolSource -cne 'fab935826c898806855376662a8a03317b3ad8f1' -or
       $Observation.ReviewedStockManifestSHA256 -ine $ReviewedSHA256 -or
       $Observation.StockRoot -ine $root -or @($Observation.Inputs).Count -ne 4 -or
       $Observation.ContentVerification -cne 'DeferredUntilAdmittedRun'){
        throw 'Exact separate Recipient PAK observation required.'
    }
    try{$captured=[datetimeoffset]$Observation.CapturedUtc;if($captured.Year -lt 2000){throw 'date'}}catch{throw 'Recipient observation capture time required.'}
    if(@('Restored','StockPreserved','Transaction','RetainedLeaseToken','Ready'|Where-Object {$_ -cin $Observation.PSObject.Properties.Name}).Count){
        throw 'A metadata observation cannot claim a restoration or accepted package.'
    }
    $inputs=@(for($index=0;$index -lt $names.Count;$index++){
        $name=$names[$index];$entry=$Observation.Inputs[$index]
        $rows=@($Reviewed|Where-Object RelativePath -CEQ $name)
        if($rows.Count -ne 1){throw 'One reviewed content row required for each supplemental PAK.'}
        $row=$rows[0]
        $source=Get-FFStockCanonicalPath $entry.Source
        if($entry.Relative -cne ('zone/'+$name) -or $entry.Mode -cne 'HardLink' -or
           $entry.ReviewedStockRelative -cne $name -or $row.Operation -cne 'NTFSHardLinkImmutableStock' -or
           $row.SHA256 -cnotmatch '^[a-fA-F0-9]{64}$' -or $entry.SHA256 -ine $row.SHA256 -or
           ($entry.Bytes -isnot [int] -and $entry.Bytes -isnot [long]) -or $entry.Bytes -le 0 -or $entry.Bytes -ne $row.Length -or
           $source -ine [IO.Path]::GetFullPath((Join-Path $root $name)) -or
           !$source.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase) -or
           $entry.SourceId -cnotmatch '^[A-F0-9]{8}:[A-F0-9]{16}$' -or
           'TargetId' -cin $entry.PSObject.Properties.Name){throw 'Recipient PAK path/order/mode/content/identity differs.'}
        try{$modified=([datetimeoffset]$entry.ModifiedUtc).UtcDateTime;if($modified.Year -lt 2000){throw 'date'}}catch{throw 'Recipient PAK modification time required.'}
        if(($entry.Attributes -isnot [int] -and $entry.Attributes -isnot [long]) -or $entry.Attributes -lt 0 -or
           ($entry.Attributes -band ([int][IO.FileAttributes]::Directory -bor [int][IO.FileAttributes]::ReparsePoint -bor [int][IO.FileAttributes]::ReadOnly))){
            throw 'Supplemental PAK must be an ordinary writable-attribute file guarded against writes during execution.'
        }
        [pscustomobject]@{Relative=$entry.Relative;Source=$source;Mode='HardLink';Bytes=$entry.Bytes;
            ModifiedUtc=$modified.ToString('o');Attributes=[int]$entry.Attributes;
            ExpectedSourceId=$entry.SourceId;ExpectedSHA256=$entry.SHA256;StockProfile='RecipientSupplemental'}
    })
    $bytes=[long]($inputs|Measure-Object Bytes -Sum).Sum
    if($bytes -ne 580092048 -or $bytes -gt 600MB){throw 'Recipient supplemental logical/hash-read budget differs.'}
    $inputs
}
function Get-RecipientStockBudget($Baseline,$Supplemental) {
    $all=@($Baseline)+@($Supplemental)
    $unique=@{}
    $relatives=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($entry in $all){
        if(!$relatives.Add($entry.Relative)){throw 'Duplicate Recipient staged stock path.'}
        if($unique.ContainsKey($entry.ExpectedSourceId)){
            $previous=$unique[$entry.ExpectedSourceId]
            if($previous.Bytes -ne $entry.Bytes -or $previous.ExpectedSHA256 -ine $entry.ExpectedSHA256){throw 'Aliased stock metadata/content differs.'}
        }else{$unique[$entry.ExpectedSourceId]=$entry}
    }
    [ordered]@{BaselineEntries=@($Baseline).Count;SupplementalEntries=@($Supplemental).Count;
        SupplementalLogicalBytes=[long]($Supplemental|Measure-Object Bytes -Sum).Sum;SupplementalLimitBytes=600MB;
        SupplementalCopiedBytes=0L;UniqueHashReadBytes=[long]($unique.Values|Measure-Object Bytes -Sum).Sum;
        UniqueHashReadFiles=$unique.Count;StockHardLinks=@($all|Where-Object Mode -CEQ HardLink).Count;
        StockCopiedBytes=[long]($all|Where-Object Mode -CEQ Copy|Measure-Object Bytes -Sum).Sum;
        ContentVerified=$false;AdditionalResidentBytesMeasured=$false}
}

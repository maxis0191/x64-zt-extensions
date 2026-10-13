# Pure supplemental receipt contract. No inventory, hashing, native import or
# staging on import/plan. The historical 72-entry FF binding stays unchanged.
function Get-RecipientSupplementalProfile([string]$Name) {
    # Explicit immutable scopes. Never infer/expand a profile from files.
    switch -CaseSensitive ($Name) {
        'observed-cp-paks-17-19-37-53' {
            [pscustomobject]@{Name=$Name;Schema='iw7.recipient-stock-observation/1';
                Names=@('assetfile17.pak','assetfile19.pak','assetfile37.pak','assetfile53.pak');
                Bytes=580092048L;LimitBytes=600MB;AdditionalBytes=0L;EvidenceSHA256=$null}
        }
        'observed-cp-paks-17-19-37-53-69' {
            [pscustomobject]@{Name=$Name;Schema='iw7.recipient-stock-observation/2';
                Names=@('assetfile17.pak','assetfile19.pak','assetfile37.pak','assetfile53.pak','assetfile69.pak');
                Bytes=966557876L;LimitBytes=966557876L;AdditionalBytes=386465828L;
                EvidenceSHA256='867E858ECD4BFFDE50A04E62488E42B73F528177E0E01B51A081BC030DBBB280'}
        }
        'doom-reviewed-all-asset-paks-20261012' {
            [pscustomobject]@{Name=$Name;Schema='iw7.recipient-stock-observation/3';
                Names=@('assetfile17.pak','assetfile19.pak','assetfile21.pak','assetfile25.pak','assetfile26.pak',
                    'assetfile36.pak','assetfile37.pak','assetfile52.pak','assetfile53.pak','assetfile68.pak',
                    'assetfile69.pak','assetfile84.pak','assetfile85.pak','assetfile100.pak','assetfile101.pak',
                    'assetfile116.pak','assetfile117.pak','assetfile132.pak','assetfile133.pak','assetfile148.pak',
                    'assetfile149.pak','assetfile164.pak','assetfile165.pak','assetfile180.pak','assetfile181.pak',
                    'assetfile196.pak','assetfile197.pak','assetfile212.pak','assetfile213.pak','assetfile228.pak',
                    'assetfile229.pak','assetfile244.pak');
                Bytes=4695508096L;LimitBytes=4695508096L;AdditionalBytes=4115416048L;
                EvidenceSHA256='67995123AB95D54DE3DDB9FFB0F52015DAA0978F3C782C977A7C9A3A3C9F58F3';
                InventoryEvidenceSHA256='683C8A39B6BD289A2ACC0A27129A038361D5A217D6EF129D07DA739FEB6F76BF'}
        }
        default {throw 'Unreviewed Recipient supplemental profile.'}
    }
}
function Get-RecipientCompleteInventoryAssets($Inventory,[string]$StockRoot,[string]$ReviewedSHA256) {
    $profile=Get-RecipientSupplementalProfile 'doom-reviewed-all-asset-paks-20261012'
    if(!$Inventory -or $Inventory.Schema -cne 'iw7.recipient-pak-inventory-proposal/1' -or
       $Inventory.StockRoot -ine $StockRoot -or $Inventory.ReviewedManifestSHA256 -ine $ReviewedSHA256 -or
       $Inventory.RetailPayloadBytesRead -ne 0 -or @($Inventory.Files).Count -ne 82){throw 'Exact complete metadata inventory required.'}
    $assets=@($Inventory.Files|Where-Object Family -CEQ assetfile)
    $expected=@('assetfile1.pak')+@($profile.Names)
    if($assets.Count -ne 33 -or @($Inventory.Files|Where-Object Family -CEQ imagefile).Count -ne 49 -or
       (($assets.Name|Sort-Object -CaseSensitive) -join ',') -cne (($expected|Sort-Object -CaseSensitive) -join ',') -or
       @($assets.SourceId|Sort-Object -Unique).Count -ne 33 -or
       [long]($assets|Measure-Object Bytes -Sum).Sum -ne 4705977508L){throw 'Complete asset inventory scope/identity/budget differs.'}
    foreach($entry in $assets){
        if($entry.SourceId -cnotmatch '^[A-F0-9]{8}:[A-F0-9]{16}$' -or
           ($entry.Bytes -isnot [int] -and $entry.Bytes -isnot [long]) -or $entry.Bytes -le 0 -or
           $entry.ContentVerified -ne $false){throw 'Complete inventory is descriptive metadata only.'}
    }
    $assets
}
function Assert-RecipientInventoryMatch($Entry,$InventoryEntry,[string]$Identity,[string]$Hash) {
    if($Identity -cne $InventoryEntry.SourceId -or $Hash -ine $InventoryEntry.ReviewedSHA256 -or
       $Entry.Bytes -ne $InventoryEntry.Bytes -or $Entry.Attributes -ne $InventoryEntry.Attributes -or
       ([datetimeoffset]$Entry.ModifiedUtc).UtcTicks -ne ([datetimeoffset]$InventoryEntry.ModifiedUtc).UtcTicks){
        throw 'Complete-profile entry differs from pinned inventory metadata.'
    }
}
function Assert-RecipientCompleteBaseline($Baseline,$Inventory,[string]$StockRoot,[string]$ReviewedSHA256) {
    $assets=@(Get-RecipientCompleteInventoryAssets $Inventory $StockRoot $ReviewedSHA256)
    $pak1=@($Baseline|Where-Object Relative -CEQ 'zone/assetfile1.pak')
    if($pak1.Count -ne 1){throw 'Complete asset profile requires exactly one baseline pak1.'}
    Assert-RecipientInventoryMatch $pak1[0] ($assets|Where-Object Name -CEQ 'assetfile1.pak') $pak1[0].ExpectedSourceId $pak1[0].ExpectedSHA256
}
function Get-RecipientSupplementalStockInputs($Observation,$Reviewed,[string]$StockRoot,[string]$ReviewedSHA256,$CompleteInventory=$null) {
    $root=Get-FFStockCanonicalPath $StockRoot
    $profile=Get-RecipientSupplementalProfile $Observation.Profile;$names=$profile.Names
    if($ReviewedSHA256 -ine '9116255ef148a324df15fa914795a7917615f023973111fdc39ae7329a9dcbf4' -or
       $Observation.Schema -cne $profile.Schema -or
       $Observation.ToolSource -cne 'fab935826c898806855376662a8a03317b3ad8f1' -or
       $Observation.ReviewedStockManifestSHA256 -ine $ReviewedSHA256 -or
       $Observation.StockRoot -ine $root -or @($Observation.Inputs).Count -ne $names.Count -or
       ($profile.EvidenceSHA256 -and $Observation.AdditionalDependencyEvidenceSHA256 -ine $profile.EvidenceSHA256) -or
       $Observation.ContentVerification -cne 'DeferredUntilAdmittedRun'){
        throw 'Exact separate Recipient PAK observation required.'
    }
    $inventoryAssets=@()
    if($profile.InventoryEvidenceSHA256){
        if($Observation.CompleteInventoryEvidenceSHA256 -ine $profile.InventoryEvidenceSHA256){throw 'Pinned complete inventory evidence required.'}
        $inventoryAssets=@(Get-RecipientCompleteInventoryAssets $CompleteInventory $root $ReviewedSHA256)
    }elseif($CompleteInventory -or 'CompleteInventoryEvidenceSHA256' -cin $Observation.PSObject.Properties.Name){
        throw 'Complete inventory cannot be mixed into an earlier profile.'
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
        if($profile.InventoryEvidenceSHA256){
            Assert-RecipientInventoryMatch $entry ($inventoryAssets|Where-Object Name -CEQ $name) $entry.SourceId $entry.SHA256
        }
        [pscustomobject]@{Relative=$entry.Relative;Source=$source;Mode='HardLink';Bytes=$entry.Bytes;
            ModifiedUtc=$modified.ToString('o');Attributes=[int]$entry.Attributes;
            ExpectedSourceId=$entry.SourceId;ExpectedSHA256=$entry.SHA256;StockProfile='RecipientSupplemental';StockProfileId=$profile.Name}
    })
    $bytes=[long]($inputs|Measure-Object Bytes -Sum).Sum
    if($bytes -ne $profile.Bytes -or $bytes -gt $profile.LimitBytes){throw 'Recipient supplemental logical/hash-read budget differs.'}
    $inputs
}
function Get-RecipientStockBudget($Baseline,$Supplemental) {
    $profileNames=@($Supplemental|ForEach-Object StockProfileId|Sort-Object -Unique)
    if($profileNames.Count -ne 1){throw 'One explicit supplemental profile required for byte accounting.'}
    $profile=Get-RecipientSupplementalProfile $profileNames[0]
    $supplementalBytes=[long]($Supplemental|Measure-Object Bytes -Sum).Sum
    if(@($Supplemental).Count -ne $profile.Names.Count -or $supplementalBytes -ne $profile.Bytes){throw 'Supplemental count/bytes differ from the named profile.'}
    if((@($Supplemental|ForEach-Object Relative) -join ',') -cne (@($profile.Names|ForEach-Object {'zone/'+$_}) -join ',')){
        throw 'Supplemental budget requires the exact ordered named scope.'
    }
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
    [ordered]@{BaselineEntries=@($Baseline).Count;SupplementalEntries=@($Supplemental).Count;SupplementalProfile=$profile.Name;
        SupplementalLogicalBytes=$supplementalBytes;SupplementalLimitBytes=$profile.LimitBytes;AdditionalBytesBeyondFourPAKs=$profile.AdditionalBytes;
        SupplementalCopiedBytes=0L;UniqueHashReadBytes=[long]($unique.Values|Measure-Object Bytes -Sum).Sum;
        UniqueHashReadFiles=$unique.Count;StockHardLinks=@($all|Where-Object Mode -CEQ HardLink).Count;
        StockCopiedBytes=[long]($all|Where-Object Mode -CEQ Copy|Measure-Object Bytes -Sum).Sum;
        ContentVerified=$false;AdditionalResidentBytesMeasured=$false}
}

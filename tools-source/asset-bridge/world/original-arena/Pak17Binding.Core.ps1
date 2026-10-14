# Pure, opt-in supplement to the immutable 72-entry World baseline.
# No file/identity/payload lookup, staging, native type or lease occurs here.
function Get-ArenaRequiredPak17Input($Baseline,$Binding,$BaselineSHA256) {
    $paks=@($Baseline|Where-Object Relative -CEQ 'zone/assetfile1.pak')
    if(@($Baseline).Count -ne 72 -or $paks.Count -ne 1 -or $paks[0].Relative -isnot [string] -or
       $paks[0].Mode -isnot [string] -or $paks[0].Source -isnot [string] -or
       $paks[0].ExpectedSourceId -isnot [string] -or $paks[0].Mode -cne 'HardLink'){
        throw 'Exact 72-input baseline and its one pack1 provider required.'
    }
    if($Binding -is [array] -or $BaselineSHA256 -isnot [string]){throw 'Scalar pack17 receipt and baseline digest required.'}
    foreach($name in 'Schema','BaselineBindingSHA256','ReviewedManifestSHA256'){
        if($Binding.$name -isnot [string]){throw 'Pack17 contract fields must be scalar strings.'}
    }
    if($Binding.Schema -cne 'iw7.world-required-pak17/1' -or $Binding.BaselineBindingSHA256 -cne $BaselineSHA256 -or
       $Binding.ReviewedManifestSHA256 -cne '9116255ef148a324df15fa914795a7917615f023973111fdc39ae7329a9dcbf4'){
        throw 'Hash-bound original baseline and reviewed pack metadata required.'
    }
    $entry=$Binding.Input
    if(!$entry -or $entry -is [array]){throw 'One scalar pack17 input object required.'}
    foreach($name in 'Relative','Mode','Source','ExpectedSHA256','ExpectedSourceId'){
        if($entry.$name -isnot [string]){throw 'Pack17 input fields must be scalar strings.'}
    }
    if(($entry.Bytes -isnot [int] -and $entry.Bytes -isnot [long]) -or
       ($entry.ModifiedUtc -isnot [string] -and $entry.ModifiedUtc -isnot [datetime] -and $entry.ModifiedUtc -isnot [datetimeoffset])){
        throw 'Scalar integer size and supported scalar UTC time required.'
    }
    $expected=[IO.Path]::GetFullPath((Join-Path (Split-Path $paks[0].Source) 'assetfile17.pak'))
    if(!$entry -or $entry.Relative -cne 'zone/assetfile17.pak' -or $entry.Mode -cne 'HardLink' -or
       ![IO.Path]::IsPathFullyQualified($entry.Source) -or [IO.Path]::GetFullPath($entry.Source) -ine $expected -or
       $entry.Bytes -ne 104595492 -or $entry.ExpectedSHA256 -ine '6f5c0d1937b5a707d4e1fb3009f68a827714d9e4a72ff2d6570b57dbf6b0f058' -or
       $entry.ExpectedSourceId -cnotmatch '^[A-F0-9]{8}:[A-F0-9]{16}$' -or
       $paks[0].ExpectedSourceId -cnotmatch '^[A-F0-9]{8}:[A-F0-9]{16}$' -or
       $entry.ExpectedSourceId.Split(':')[0] -cne $paks[0].ExpectedSourceId.Split(':')[0] -or
       ($entry.Attributes -isnot [int] -and $entry.Attributes -isnot [long]) -or $entry.Attributes -ne 32){
        throw 'Only the required pack17 from the existing pack1 provider is allowed.'
    }
    try{$modified=([datetimeoffset]$entry.ModifiedUtc).UtcDateTime;if($modified.Year -lt 2000){throw 'date'}}catch{throw 'Exact pack17 modification time required.'}
    [pscustomobject]@{Relative='zone/assetfile17.pak';Source=$expected;Mode='HardLink';Bytes=104595492L;
        ModifiedUtc=$modified.ToString('o');Attributes=32;ExpectedSourceId=$entry.ExpectedSourceId;
        ExpectedSHA256=$entry.ExpectedSHA256;Supplement='world-required-pak17'}
}

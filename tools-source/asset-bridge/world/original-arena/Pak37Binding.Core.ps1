# Pure, opt-in pack37 addition after the unchanged baseline and pack17 qualifier.
# No stock lookup, staging, native type or admission occurs here.
function Get-ArenaRequiredPak37Input($Existing,$Binding,$BaselineSHA256,$Pak17BindingSHA256) {
    if(@($Existing).Count -ne 73 -or @($Existing|Where-Object {$_.Relative -isnot [string]}).Count){throw 'Exact scalar 73-input World profile required.'}
    $paks=@($Existing|Where-Object {$_.Relative -match '(?i)\.pak$'})
    $one=@($paks|Where-Object Relative -CEQ 'zone/assetfile1.pak')
    $seventeen=@($paks|Where-Object Relative -CEQ 'zone/assetfile17.pak')
    if($paks.Count -ne 2 -or $one.Count -ne 1 -or $seventeen.Count -ne 1){throw 'Only original pack1 and qualified pack17 may precede pack37.'}
    foreach($pack in @($one[0],$seventeen[0])){
        foreach($name in 'Mode','Source','ExpectedSourceId'){if($pack.$name -isnot [string]){throw 'Scalar existing pack provider fields required.'}}
        if($pack.Mode -cne 'HardLink' -or $pack.ExpectedSourceId -cnotmatch '^[A-F0-9]{8}:[A-F0-9]{16}$'){throw 'Guarded existing hardlink pack providers required.'}
    }
    $provider=Split-Path $one[0].Source
    if([IO.Path]::GetFullPath($seventeen[0].Source) -ine [IO.Path]::GetFullPath((Join-Path $provider 'assetfile17.pak')) -or
       $seventeen[0].ExpectedSourceId.Split(':')[0] -cne $one[0].ExpectedSourceId.Split(':')[0]){throw 'Pack17 and pack1 must retain the same provider.'}
    if($Binding -is [array] -or $BaselineSHA256 -isnot [string] -or $Pak17BindingSHA256 -isnot [string]){throw 'Scalar pack37 receipt and preceding digests required.'}
    foreach($name in 'Schema','BaselineBindingSHA256','RequiredPak17BindingSHA256','ReviewedManifestSHA256','CauseModalRecordSHA256'){
        if($Binding.$name -isnot [string]){throw 'Pack37 contract fields must be scalar strings.'}
    }
    if($Binding.Schema -cne 'iw7.world-required-pak37/1' -or $Binding.BaselineBindingSHA256 -cne $BaselineSHA256 -or
       $Binding.RequiredPak17BindingSHA256 -cne $Pak17BindingSHA256 -or
       $Binding.ReviewedManifestSHA256 -cne '9116255ef148a324df15fa914795a7917615f023973111fdc39ae7329a9dcbf4' -or
       $Binding.CauseModalRecordSHA256 -cne 'fb2ec614bc6ed8bce15dd8067aea4eed69b7da288e0c96fac3d8a8835350a9c6'){
        throw 'Original baseline, qualified pack17 and actual M5 filename evidence required.'
    }
    $entry=$Binding.Input
    if(!$entry -or $entry -is [array]){throw 'One scalar pack37 input object required.'}
    foreach($name in 'Relative','Mode','Source','ExpectedSHA256','ExpectedSourceId'){
        if($entry.$name -isnot [string]){throw 'Pack37 input fields must be scalar strings.'}
    }
    if(($entry.Bytes -isnot [int] -and $entry.Bytes -isnot [long]) -or
       ($entry.Attributes -isnot [int] -and $entry.Attributes -isnot [long]) -or
       ($entry.ModifiedUtc -isnot [string] -and $entry.ModifiedUtc -isnot [datetime] -and $entry.ModifiedUtc -isnot [datetimeoffset])){
        throw 'Scalar integer metadata and supported scalar UTC time required.'
    }
    $expected=[IO.Path]::GetFullPath((Join-Path $provider 'assetfile37.pak'))
    if($entry.Relative -cne 'zone/assetfile37.pak' -or $entry.Mode -cne 'HardLink' -or
       ![IO.Path]::IsPathFullyQualified($entry.Source) -or [IO.Path]::GetFullPath($entry.Source) -ine $expected -or
       $entry.Bytes -ne 53477412 -or $entry.Attributes -ne 32 -or
       $entry.ExpectedSHA256 -ine '839c1da30e43b9c5c78cc457d3fa3ef61bd85ae818c81a2d2d0b30ff187fb349' -or
       $entry.ExpectedSourceId -cnotmatch '^[A-F0-9]{8}:[A-F0-9]{16}$' -or
       $entry.ExpectedSourceId.Split(':')[0] -cne $one[0].ExpectedSourceId.Split(':')[0]){
        throw 'Only the M5-required pack37 from the existing pack1 provider is allowed.'
    }
    try{$modified=([datetimeoffset]$entry.ModifiedUtc).UtcDateTime;if($modified.Year -lt 2000){throw 'date'}}catch{throw 'Exact pack37 modification time required.'}
    [pscustomobject]@{Relative='zone/assetfile37.pak';Source=$expected;Mode='HardLink';Bytes=53477412L;
        ModifiedUtc=$modified.ToString('o');Attributes=32;ExpectedSourceId=$entry.ExpectedSourceId;
        ExpectedSHA256=$entry.ExpectedSHA256;Supplement='world-required-pak37'}
}

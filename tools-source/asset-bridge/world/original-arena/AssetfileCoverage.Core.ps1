# Pure fixed namespace coverage, not a claim of minimal CP dependencies.
# The caller verifies the small manifest/receipt hashes; stock stays unread here.
function Get-ArenaAssetfileCoverageInputs($Existing,$Binding,$Reviewed,$BaselineSHA,$Pak17SHA,$Pak37SHA) {
    $numbers=@(1,17,19,21,25,26,36,37,52,53,68,69,84,85,100,101,116,117,132,133,148,149,164,165,180,181,196,197,212,213,228,229,244)
    $names=@($numbers|ForEach-Object {'assetfile'+$_+'.pak'})
    if(@($Existing).Count -ne 74 -or @($Existing|Where-Object {$_.Relative -isnot [string]}).Count){throw 'Exact preceding 74-input World profile required.'}
    $paks=@($Existing|Where-Object {$_.Relative -match '(?i)\.pak$'})
    if($paks.Count -ne 3 -or @($paks|Where-Object {$_.Relative -cnotin @('zone/assetfile1.pak','zone/assetfile17.pak','zone/assetfile37.pak')}).Count){throw 'Only qualified pack1/17/37 may precede coverage.'}
    $pack1=@($paks|Where-Object Relative -CEQ 'zone/assetfile1.pak')
    if($pack1.Count -ne 1 -or $pack1[0].Source -isnot [string] -or $pack1[0].ExpectedSourceId -isnot [string] -or
       $pack1[0].ExpectedSourceId -cnotmatch '^[A-F0-9]{8}:[A-F0-9]{16}$'){throw 'Scalar existing pack1 provider required.'}
    if($Binding -is [array] -or $BaselineSHA -isnot [string] -or $Pak17SHA -isnot [string] -or $Pak37SHA -isnot [string]){throw 'Scalar coverage receipt and preceding digests required.'}
    foreach($field in 'Schema','BaselineBindingSHA256','RequiredPak17BindingSHA256','RequiredPak37BindingSHA256','ReviewedManifestSHA256'){
        if($Binding.$field -isnot [string]){throw 'Coverage contract fields must be scalar strings.'}
    }
    if($Binding.Schema -cne 'iw7.world-assetfile-coverage/1' -or $Binding.BaselineBindingSHA256 -cne $BaselineSHA -or
       $Binding.RequiredPak17BindingSHA256 -cne $Pak17SHA -or $Binding.RequiredPak37BindingSHA256 -cne $Pak37SHA -or
       $Binding.ReviewedManifestSHA256 -cne '9116255ef148a324df15fa914795a7917615f023973111fdc39ae7329a9dcbf4'){
        throw 'Hash-bound original baseline, typed supplements and reviewed manifest required.'
    }
    foreach($field in 'NamespaceCoverageOnly','MetadataOnly','MinimalDependencySet','CurrentPayloadHashed','AliasesCreated'){
        if($Binding.$field -isnot [bool]){throw 'Scalar truthful coverage flags required.'}
    }
    if(!$Binding.NamespaceCoverageOnly -or !$Binding.MetadataOnly -or $Binding.MinimalDependencySet -or $Binding.CurrentPayloadHashed -or $Binding.AliasesCreated){throw 'Unrun namespace coverage receipt required.'}
    if($Binding.Inputs -isnot [array] -or $Binding.Inputs.Count -ne 33){throw 'Exactly 33 fixed assetfile entries required.'}
    $provider=Split-Path $pack1[0].Source
    $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $additional=[Collections.Generic.List[object]]::new()
    foreach($entry in $Binding.Inputs){
        if(!$entry -or $entry -is [array]){throw 'Scalar coverage entry required.'}
        foreach($field in 'Relative','Source','Mode','ExpectedSourceId','ExpectedSHA256'){
            if($entry.$field -isnot [string]){throw 'Coverage input fields must be scalar strings.'}
        }
        $name=[IO.Path]::GetFileName($entry.Relative)
        if($name -cnotin $names -or $entry.Relative -cne ('zone/'+$name) -or !$seen.Add($name)){throw 'Only the exact fixed assetfile namespace is allowed.'}
        $row=@($Reviewed|Where-Object RelativePath -CEQ $name)
        if($row.Count -ne 1 -or $row[0].Operation -isnot [string] -or $row[0].Operation -cne 'NTFSHardLinkImmutableStock' -or
           $row[0].SHA256 -isnot [string] -or $row[0].SHA256 -cnotmatch '^[A-Fa-f0-9]{64}$' -or
           ($row[0].Length -isnot [int] -and $row[0].Length -isnot [long])){throw 'Exact historical reviewed row required.'}
        if(($entry.Bytes -isnot [int] -and $entry.Bytes -isnot [long]) -or
           ($entry.Attributes -isnot [int] -and $entry.Attributes -isnot [long]) -or
           ($entry.ModifiedUtc -isnot [string] -and $entry.ModifiedUtc -isnot [datetime] -and $entry.ModifiedUtc -isnot [datetimeoffset])){throw 'Scalar coverage size/attributes/UTC metadata required.'}
        $expected=[IO.Path]::GetFullPath((Join-Path $provider $name))
        if($entry.Mode -cne 'HardLink' -or ![IO.Path]::IsPathFullyQualified($entry.Source) -or
           [IO.Path]::GetFullPath($entry.Source) -ine $expected -or $entry.Bytes -ne $row[0].Length -or $entry.Attributes -ne 32 -or
           $entry.ExpectedSHA256 -ine $row[0].SHA256 -or $entry.ExpectedSourceId -cnotmatch '^[A-F0-9]{8}:[A-F0-9]{16}$' -or
           $entry.ExpectedSourceId.Split(':')[0] -cne $pack1[0].ExpectedSourceId.Split(':')[0]){throw 'Fixed immutable source/provider/volume/content metadata required.'}
        try{$modified=([datetimeoffset]$entry.ModifiedUtc).UtcDateTime;if($modified.Year -lt 2000){throw 'date'}}catch{throw 'Exact coverage modification time required.'}
        $prior=@($paks|Where-Object Relative -CEQ $entry.Relative)
        if($prior.Count){
            if($prior.Count -ne 1 -or $prior[0].Source -ine $expected -or $prior[0].Mode -cne 'HardLink' -or
               $prior[0].Bytes -ne $entry.Bytes -or $prior[0].ExpectedSourceId -cne $entry.ExpectedSourceId -or
               $prior[0].ExpectedSHA256 -ine $entry.ExpectedSHA256 -or $prior[0].Attributes -ne $entry.Attributes -or
               ([datetimeoffset]$prior[0].ModifiedUtc).UtcDateTime.Ticks -ne $modified.Ticks){throw 'Existing typed pack1/17/37 binding changed.'}
        }else{
            $additional.Add([pscustomobject]@{Relative=$entry.Relative;Source=$expected;Mode='HardLink';Bytes=[long]$entry.Bytes;
                ModifiedUtc=$modified.ToString('o');Attributes=32;ExpectedSourceId=$entry.ExpectedSourceId;
                ExpectedSHA256=$entry.ExpectedSHA256;Supplement='world-assetfile-coverage'})
        }
    }
    if($seen.Count -ne 33 -or $additional.Count -ne 30){throw 'Exact fixed 30 additions required.'}
    $additional.ToArray()
}

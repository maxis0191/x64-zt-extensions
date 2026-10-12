# FLAC-17 adapter only. No provider import, process, type or admission on load.
function Assert-FlacBuildExtension($Plan,$Seal) {
    $expected=@{
        'sound_bank.cpp'=@(113219,'8142eead0fe7cbdb6a0b17cc106efa4d02f0652e9955657f220ce1b82d66c95e')
        'sound_flac_metadata.hpp'=@(6337,'2226b5a9fa8afc241f843a5a1dc8da38574eb0c931a43f4d66a1b5eae0a19eca')
        'flac_dump_probe.cpp'=@(2226,'3f0015a2e7958ccb4d7194e876212767ea19b0f3467ab52f96d3993f39064e86')
        'flac_dump_cases.hpp'=@(10402,'fbf0e8c03c850af01b45c46a03bf183b8ce5355c294b2618493ca72a75673cb3')
    }
    if(!$Plan.flac -or $Plan.flac.Count -ne 4 -or @($Plan.flac.sources).Count -ne 4){throw 'Closed four-source FLAC extension required.'}
    foreach($field in 'overlay','sources','review','original_sound_bank'){if(!$Plan.flac.Contains($field)){throw 'Unknown FLAC extension shape.'}}
    Assert-ChecksumBuildPath $Plan.flac.overlay
    if((Split-Path $Plan.flac.overlay -Parent) -ine (Join-Path $Plan.shared_repo 'runtime/content-surfaces') -or
        (Split-Path $Plan.flac.overlay -Leaf) -cnotmatch '^original-sound-flac-dump-source-[a-z0-9-]+$'){throw 'Private FLAC overlay required.'}
    $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($pin in $Plan.source_pins){if(!$seen.Add([IO.Path]::GetFullPath($pin.path))){throw 'Duplicate bootstrap source.'}}
    $seen.Clear()
    foreach($pin in $Plan.flac.sources){
        $name=[IO.Path]::GetFileName($pin.path)
        if($pin.Count -ne 3 -or !$expected.ContainsKey($name) -or !$seen.Add($pin.path) -or
            $pin.path -ine (Join-Path $Plan.flac.overlay $name) -or
            ($pin.bytes -isnot [int] -and $pin.bytes -isnot [long]) -or $pin.bytes -ne $expected[$name][0] -or
            $pin.sha256 -cne $expected[$name][1]){throw 'Exact FLAC source identity required.'}
        $sources=@($Plan.source_pins|Where-Object path -IEQ $pin.path)
        if($sources.Count -ne 1 -or $sources[0].bytes -ne $pin.bytes -or $sources[0].sha256 -cne $pin.sha256 -or
            @($Seal.Inputs|Where-Object Path -IEQ $pin.path).Count){throw 'New FLAC source requires own retained guard, not Seal C.'}
    }
    $review=$Plan.flac.review
    $bound=@($Plan.source_pins|Where-Object path -IEQ $review.path)
    if($review.Count -ne 3 -or $review.sha256 -cne '75ad217b9841856a7401785fef53b8281e3b80e26bf5525e37e8250ee2826ce9' -or
        ($review.bytes -isnot [int] -and $review.bytes -isnot [long]) -or $review.bytes -le 0 -or $review.bytes -gt 128KB -or
        $bound.Count -ne 1 -or $bound[0].bytes -ne $review.bytes -or $bound[0].sha256 -cne $review.sha256){throw 'Exact original response review guard required.'}
    $original=@($Seal.Inputs|Where-Object Path -IEQ $Plan.flac.original_sound_bank)
    if($original.Count -ne 1 -or $original[0].SHA256 -cne '46bc9e333cc9985ad3358e68a44adbc9b8469feabdbfe946aeb4eff8c1a068b5'){
        throw 'Original sound source must remain in Seal C.'
    }
    foreach($command in $Plan.commands){
        if($command.working_directory -ine $Plan.candidate){throw 'Private command directory required.'}
        if($command.phase -ceq 'probe-flac-run'){
            if($command.kind -cne 'probe_run' -or @($command.arguments).Count -ne 1 -or $command.arguments[0] -cne '--verify-headers' -or
                $command.executable -ine (Join-Path $Plan.candidate 'probe/flac-header.exe')){throw 'Closed FLAC probe command required.'}
        }elseif($command.kind -cne 'probe_run'){
            if(@($command.arguments).Count -ne 1 -or $command.arguments[0] -cne ('@'+$command.response_path)){
                throw 'Literal response command required.'
            }
        }
    }
}

function Open-FlacBuildSdkInputs($Context) {
    # Called only after complete admission. These historical binary pins are not
    # opened/hashed by FLAC-17 Plan mode or during its bootstrap.
    foreach($pin in $Context.Plan.sdk_tools){
        Assert-ChecksumBuildPath $pin.path
        $stream=[IO.File]::Open($pin.path,'Open','Read','Read')
        $Context.InputGuards.Add($stream);$Context.Record.InputGuardsOpened++
        $item=Get-Item -LiteralPath $pin.path -Force
        $entry=@{Path=$pin.path;Bytes=$pin.bytes;SHA256=$pin.sha256;Attributes=[int]$item.Attributes;ModifiedUtcTicks=$item.LastWriteTimeUtc.Ticks}
        $Context.GuardedInputs.Add([pscustomobject]@{Entry=$entry;Stream=$stream})
        Assert-ChecksumBuildMetadata $entry
        if((Get-ChecksumBuildHash $stream $Context) -cne $pin.sha256){throw 'Guarded SDK tool differs before FLAC build.'}
        Assert-ChecksumBuildMetadata $entry
    }
}

function Assert-FlacHeaderProbe($Probe) {
    if($Probe.Count -ne 7 -or $Probe.schema -cne 'iw7.flac-dump-header-probe/1' -or
        ($Probe.cases -isnot [int] -and $Probe.cases -isnot [long]) -or $Probe.cases -ne 103){throw 'Actual 103-case C++ FLAC probe required.'}
    foreach($name in 'input_unchanged','extent_checks'){
        if($Probe[$name] -isnot [bool] -or !$Probe[$name]){throw 'FLAC native header invariants failed.'}
    }
    foreach($name in 'native_dump_tested','full_conformance','ready'){
        if($Probe[$name] -isnot [bool] -or $Probe[$name]){throw 'Header probe cannot promote dump, codec or runtime.'}
    }
}

function Assert-FlacIncludeBytes($File,$Paths,[scriptblock]$CheckClock) {
    # The unchanged completion reader already holds a deny-write/delete guard.
    # Re-read its bounded text without consuming another retained-file slot.
    & $CheckClock
    $raw=[IO.File]::ReadAllBytes($File.Image)
    if($raw.Length -ne $File.Bytes -or $raw.Length -gt 2MB){throw 'Bounded guarded include trace required.'}
    $text=[Text.UTF8Encoding]::new($false,$true).GetString($raw)
    $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($line in $text.Split("`n")){
        $line=$line.Trim()
        if($line.StartsWith('Note: including file:')){
            $path=$line.Substring('Note: including file:'.Length).Trim()
            if(![IO.Path]::IsPathFullyQualified($path)){throw 'Absolute include trace path required.'}
            [void]$seen.Add([IO.Path]::GetFullPath($path).ToLowerInvariant())
        }
    }
    # Match Python's character ordering, independent of the host culture.
    $ordered=[string[]]@($seen)
    [Array]::Sort($ordered,[StringComparer]::Ordinal)
    Assert-AuditSameJson @($ordered) @($Paths) 'actual FLAC-profile compiler include paths'
    & $CheckClock
}

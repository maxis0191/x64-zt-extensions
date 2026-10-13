# Original tiny fixtures only. The existing file-ID helper reads their NTFS metadata.
# No stock, engine, source build, resource admission, or opaque content read/hash.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
. (Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
Add-Type -Path (Join-Path $repo 'ops/hud-lab/HudFileIdentity.cs')
$script:checks=0;$script:fixtureNumber=0
$temporary=Join-Path ([IO.Path]::GetTempPath()) ('t7-opaque-manifest-tests-'+[guid]::NewGuid().ToString('N'))
$contexts=[Collections.Generic.List[object]]::new();$junctions=[Collections.Generic.List[string]]::new()
function Check([bool]$Value,[string]$Reason){if(!$Value){throw $Reason};$script:checks++}
function Refuses([scriptblock]$Body,[string]$Pattern){
    $caught=$false
    try{& $Body}catch{$caught=$true;Check ($_.Exception.Message -match $Pattern) ('Unexpected refusal: '+$_.Exception.Message)}
    Check $caught ('Expected refusal: '+$Pattern)
}
function Fixture([string]$Profile='ObservedStartupManifestA',[bool]$Initialize=$true){
    $script:fixtureNumber++
    $root=Join-Path $temporary ('case-'+$script:fixtureNumber)
    $work=Join-Path $root 'work';$lpc=Join-Path $work 'identities\dedicatedpc\LPC'
    [IO.Directory]::CreateDirectory($lpc)|Out-Null
    $plan=[pscustomobject]@{RunRoot=$root;WorkingDirectory=$work;EngineOutputProfile=$Profile;OutputKey='synthetic_catalog'}
    $context=[pscustomobject]@{Closed=$true;Lease=[pscustomobject]@{Token=('f'*32)};Guards=[Collections.Generic.List[object]]::new()}
    $contexts.Add($context)
    if($Initialize){Initialize-T7CatalogueOpaqueManifestObservation $plan}
    [pscustomobject]@{Root=$root;Work=$work;Lpc=$lpc;Path=(Join-Path $lpc '.manifest');Plan=$plan;Context=$context}
}
function Write-FixtureBytes([string]$Path,[int]$Count){
    $bytes=[byte[]]::new($Count)
    for($i=0;$i -lt $Count;$i++){$bytes[$i]=[byte](241-$i)}
    [IO.File]::WriteAllBytes($Path,$bytes)
}
function Release-Fixture($Fixture){foreach($guard in $Fixture.Context.Guards){$guard.Dispose()};$Fixture.Context.Guards.Clear()}
try {
    # Both allowed profiles pass the unchanged scalar/budget gate, then encounter
    # the deliberately noncanonical synthetic RunRoot. Unknown profiles fail earlier.
    foreach($name in @('ObservedStartupA','ObservedStartupManifestA','unknown')){
        $plan=[pscustomobject]@{Schema='iw7.t7-catalogue-plan/1';EngineOutputProfile=$name;Runner='synthetic';
            CandidateBytes=21740032;CandidateSHA256='94dd29a9cb538504ddeb3545483e43a5dfea195aaca155db5bf147f1c6334c15';
            RunRoot='not-an-absolute-path';PhysicalBytes=6GB;CommitBytes=8GB;GroupDeadlineSeconds=200;DeadlineSeconds=120;
            MutableOutputLimitBytes=64MB;MetadataReserveBytes=64KB;CleanupSeconds=5;ReportLimitBytes=512KB;LogLimitBytes=1MB;
            OutputLimitBytes=127799192;RetryAuthorized=$false}
        $pattern=if($name -ceq 'unknown'){'Fixed catalogue plan'}else{'Canonical absolute path'}
        Refuses {Assert-T7CataloguePlan $plan $temporary 'synthetic'} $pattern
    }
    $f=Fixture 'ObservedStartupA'
    Assert-T7CatalogueEngineOutputs $f.Plan;$script:checks++
    Write-FixtureBytes $f.Path 8
    Refuses {Assert-T7CatalogueEngineOutputs $f.Plan} 'Unexpected identity entry'
    Refuses {Assert-T7CatalogueEngineOutputs $f.Plan -Closed -Context $f.Context} 'Unexpected identity entry'
    Check ($f.Context.Guards.Count -eq 0) 'Legacy profile retained a new guard.'

    $f=Fixture 'ObservedStartupManifestA' $false
    Refuses {Assert-T7CatalogueEngineOutputs $f.Plan} 'initialized runtime attempt'
    # Exercise the actual runtime initialization hook once; no budget/provider is invoked.
    Enable-T7CatalogueRuntimeProfile $f.Plan
    Assert-T7CatalogueEngineOutputs $f.Plan;$script:checks++
    Assert-T7CatalogueEngineOutputs $f.Plan -Closed -Context $f.Context;$script:checks++
    Check ($f.Context.Guards.Count -eq 0) 'Absent optional output created a guard.'
    Refuses {Assert-T7CatalogueEngineOutputs $f.Plan -Closed -Context $f.Context} 'already consumed'
    Write-FixtureBytes $f.Path 8
    Refuses {Assert-T7CatalogueEngineOutputs $f.Plan} 'finalized absence changed'

    $f=Fixture
    $baselineBytes=Measure-H1Output $f.Root
    $baselineEntries=@(Get-ChildItem -LiteralPath $f.Root -Recurse -Force).Count
    foreach($length in 0..8){
        Write-FixtureBytes $f.Path $length
        Assert-T7CatalogueEngineOutputs $f.Plan;$script:checks++
        Check ($f.Context.Guards.Count -eq 0) 'Progress observation retained a writer-blocking guard.'
    }
    Check ((Measure-H1Output $f.Root)-$baselineBytes -eq 8) 'Opaque bytes escaped logical output accounting.'
    Check (@(Get-ChildItem -LiteralPath $f.Root -Recurse -Force).Count-$baselineEntries -eq 1) 'Opaque entry escaped tree accounting.'
    Assert-T7CatalogueEngineOutputs $f.Plan -Closed -Context $f.Context;$script:checks++
    Check ($f.Context.Guards.Count -eq 1 -and $f.Context.Guards[0].Length -eq 8 -and $f.Context.Guards[0].Position -eq 0) 'Expected unread, exact-size guard missing.'
    Refuses {[IO.File]::WriteAllText($f.Path,'replacement')} '.'
    Refuses {[IO.File]::Delete($f.Path)} '.'
    Refuses {[IO.File]::Move($f.Path,(Join-Path $f.Root 'moved.bin'))} '.'
    Assert-T7CatalogueEngineOutputs $f.Plan;$script:checks++
    $retained=$f.Context.Guards[0]
    Release-Fixture $f
    Check $retained.SafeFileHandle.IsClosed 'Cleanup did not close the retained manifest handle.'
    $exclusive=[IO.File]::Open($f.Path,'Open','ReadWrite','None');$exclusive.Dispose();$script:checks++

    foreach($length in 0..7){
        $f=Fixture;Write-FixtureBytes $f.Path $length
        Assert-T7CatalogueEngineOutputs $f.Plan;$script:checks++
        Refuses {Assert-T7CatalogueEngineOutputs $f.Plan -Closed -Context $f.Context} 'final size or identity'
        Check ($f.Context.Guards.Count -eq 0) 'Rejected final size leaked a retained guard.'
        $exclusive=[IO.File]::Open($f.Path,'Open','ReadWrite','None');$exclusive.Dispose();$script:checks++
    }
    $f=Fixture;Write-FixtureBytes $f.Path 9
    Refuses {Assert-T7CatalogueEngineOutputs $f.Plan} 'at most eight'
    Refuses {Assert-T7CatalogueEngineOutputs $f.Plan -Closed -Context $f.Context} 'at most eight'
    $f=Fixture;[IO.Directory]::CreateDirectory($f.Path)|Out-Null
    Refuses {Assert-T7CatalogueEngineOutputs $f.Plan} 'ordinary file'

    foreach($relative in @('dedicatedpc\.manifest','dedicatedpc\dumps\.manifest','dedicatedpc\LPC\.Manifest',
        'dedicatedpc\LPC\.manifest.tmp','dedicatedpc\LPC\other')){
        $f=Fixture;$path=Join-Path (Join-Path $f.Work 'identities') $relative
        [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($path))|Out-Null
        Write-FixtureBytes $path 8
        # Exclusive content lock: rejecting the name must not need any byte read.
        $private=[IO.File]::Open($path,'Open','ReadWrite','None')
        try{Refuses {Assert-T7CatalogueEngineOutputs $f.Plan} 'Unexpected identity entry'}finally{$private.Dispose()}
    }
    $f=Fixture;[IO.Directory]::CreateDirectory((Join-Path $f.Lpc 'other'))|Out-Null
    Refuses {Assert-T7CatalogueEngineOutputs $f.Plan} 'Unexpected identity entry'

    # A real junction in the synthetic tree exercises no-reparse ancestry without
    # requiring symlink privileges. Its target is another tiny synthetic directory.
    $f=Fixture;$target=Join-Path $f.Root 'redirect-target'
    [IO.Directory]::CreateDirectory($target)|Out-Null
    Write-FixtureBytes (Join-Path $target '.manifest') 8
    [IO.Directory]::Delete($f.Lpc)
    New-Item -ItemType Junction -Path $f.Lpc -Target $target|Out-Null;$junctions.Add($f.Lpc)
    Refuses {Assert-T7CatalogueEngineOutputs $f.Plan} 'Reparse'
    Refuses {Assert-T7CatalogueEngineOutputs $f.Plan -Closed -Context $f.Context} 'Reparse'
    $f=Fixture;$target=Join-Path $f.Root 'redirect-leaf-target'
    [IO.Directory]::CreateDirectory($target)|Out-Null
    New-Item -ItemType Junction -Path $f.Path -Target $target|Out-Null;$junctions.Add($f.Path)
    Refuses {Assert-T7CatalogueEngineOutputs $f.Plan} 'Reparse'

    $f=Fixture;Write-FixtureBytes $f.Path 8;Assert-T7CatalogueEngineOutputs $f.Plan
    $firstId=Get-T7CatalogueFileId $f.Path
    [IO.File]::Move($f.Path,(Join-Path $f.Root 'retained-first.bin'));Write-FixtureBytes $f.Path 8
    Check ((Get-T7CatalogueFileId $f.Path) -cne $firstId) 'Fixture did not replace the native file identity.'
    Refuses {Assert-T7CatalogueEngineOutputs $f.Plan} 'identity'
    Refuses {Assert-T7CatalogueEngineOutputs $f.Plan -Closed -Context $f.Context} 'identity'
    $f=Fixture;Write-FixtureBytes $f.Path 8;Assert-T7CatalogueEngineOutputs $f.Plan
    [IO.File]::Move($f.Path,(Join-Path $f.Root 'retained-disappeared.bin'))
    Refuses {Assert-T7CatalogueEngineOutputs $f.Plan} 'disappeared'

    foreach($fault in @('no-lease','bad-token','not-closed','no-guards')){
        $f=Fixture;Write-FixtureBytes $f.Path 8
        switch($fault){'no-lease'{$f.Context.Lease=$null};'bad-token'{$f.Context.Lease.Token='invalid'};
            'not-closed'{$f.Context.Closed=$false};'no-guards'{$f.Context.Guards=$null}}
        Refuses {Assert-T7CatalogueEngineOutputs $f.Plan -Closed -Context $f.Context} 'retained admission/guards'
    }
    $f=Fixture
    Refuses {Assert-T7CatalogueEngineOutputs $f.Plan -Closed} 'retained admission/guards'
    $oldPlan=$f.Plan;$other=Fixture
    Refuses {Assert-T7CatalogueEngineOutputs $oldPlan} 'initialized runtime attempt'

    # Replace the path between its preliminary identity sample and final open.
    # Real IDs still come from the helper; only the race timing is injected.
    $f=Fixture;Write-FixtureBytes $f.Path 8
    $script:realIdentity=${function:Get-T7CatalogueFileId};$script:replacePath=$f.Path
    $script:retainedPath=Join-Path $f.Root 'retained-race.bin';$script:replaceOnce=$true
    function Get-T7CatalogueFileId([string]$Path){
        $id=& $script:realIdentity $Path
        if($script:replaceOnce -and $Path -ceq $script:replacePath){
            $script:replaceOnce=$false
            [IO.File]::Move($Path,$script:retainedPath);Write-FixtureBytes $Path 8
        }
        $id
    }
    try{Refuses {Assert-T7CatalogueEngineOutputs $f.Plan -Closed -Context $f.Context} 'final size or identity'}
    finally{${function:Get-T7CatalogueFileId}=$script:realIdentity}
    Check ($f.Context.Guards.Count -eq 0) 'Identity-race rejection retained a guard.'
    $exclusive=[IO.File]::Open($f.Path,'Open','ReadWrite','None');$exclusive.Dispose();$script:checks++

    $f=Fixture;Write-FixtureBytes $f.Path 8
    $f.Context.Guards=[Collections.ArrayList]::ReadOnly([Collections.ArrayList]::new())
    Refuses {Assert-T7CatalogueEngineOutputs $f.Plan -Closed -Context $f.Context} 'read-only|fixed size'
    Check ($f.Context.Guards.Count -eq 0) 'Failed guard registration retained a handle.'
    $exclusive=[IO.File]::Open($f.Path,'Open','ReadWrite','None');$exclusive.Dispose();$script:checks++

    # The existing 64-entry counter remains authoritative, including the manifest.
    $f=Fixture;Write-FixtureBytes $f.Path 8
    $count=@(Get-ChildItem -LiteralPath $f.Root -Recurse -Force).Count
    for($i=$count;$i -lt 64;$i++){[IO.File]::WriteAllBytes((Join-Path $f.Root ('synthetic-'+$i)),[byte[]]::new(0))}
    Check ((Measure-H1Output $f.Root) -eq 8) 'Exactly 64 entries should remain measurable.'
    [IO.File]::WriteAllBytes((Join-Path $f.Root 'synthetic-over-limit'),[byte[]]::new(0))
    Refuses {Measure-H1Output $f.Root} 'entry count exceeded 64'
    [ordered]@{Status='Passed';Checks=$script:checks;SyntheticFixtures=$script:fixtureNumber;
        NativeFileIdentityHelperUsed=$true;NativeEngineLoaded=$false;RealAdmission=$false;OwnerStockRead=$false;
        OpaqueContentReadOrHashed=$false}|ConvertTo-Json
}finally{
    foreach($context in $contexts){if($null -ne $context.Guards){foreach($guard in $context.Guards){$guard.Dispose()}}}
    $resolved=[IO.Path]::GetFullPath($temporary)
    $parent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$resolved.StartsWith($parent,[StringComparison]::OrdinalIgnoreCase) -or
       [IO.Path]::GetFileName($resolved) -cnotmatch '^t7-opaque-manifest-tests-[0-9a-f]{32}$'){throw 'Refuse cleanup outside exact synthetic root.'}
    foreach($junction in $junctions){
        if(![IO.Path]::GetFullPath($junction).StartsWith($resolved+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Refuse junction cleanup outside synthetic root.'}
        [IO.Directory]::Delete($junction)
    }
    if(Test-Path -LiteralPath $resolved){Remove-Item -LiteralPath $resolved -Recurse -Force}
}

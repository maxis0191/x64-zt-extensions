# Fixed catalogue adapter. Ownership, pin readers and closure stay in H1Native.Core.
function Get-T7CatalogueCandidateProfile($Plan) {
    if(!$Plan.PSObject.Properties['CandidateProfile']){return 'ordinary-d2'}
    if($Plan.CandidateProfile -cnotin @('ordinary-d2','t7-catalog-trace','t7-catalog-exit-context')){throw 'Unknown catalogue candidate profile.'}
    $Plan.CandidateProfile
}
function Get-T7CatalogueMainBaseline($Plan) {
    if(!$Plan.PSObject.Properties['MainBaseline']){return 'Running'}
    if($Plan.MainBaseline -cnotin @('Running','Stopped')){throw 'Unknown Main baseline.'}
    $Plan.MainBaseline
}
function Assert-T7CatalogueMain($Plan) {
    $baseline=Get-T7CatalogueMainBaseline $Plan
    if($baseline -ceq 'Running') {
        # Preserve the existing generation/UDP-owner check without changing its helper.
        return (Assert-T7PrepatchMain $Plan.PreservedMain)
    }
    $expected=$Plan.PreservedMain
    if(!(Test-T7CatalogueInteger $expected.PID ([int]::MaxValue)) -or $expected.PID -le 0 -or
       !$expected.CreatedUtc -or !$expected.Image){throw 'Original Main identity required for stopped baseline.'}
    $null=[datetimeoffset]::Parse($expected.CreatedUtc)
    Assert-H1Path $expected.Image
    $name=[IO.Path]::GetFileName($expected.Image)
    $processes=@(Get-IW7ResourceProcesses)
    # PID reuse, inaccessible same-name images and the expected image at any PID
    # are conservative refusals. Absence does not explain why Main stopped.
    $matches=@($processes|Where-Object {
        $_.PID -eq $expected.PID -or
        ($_.Image -and $_.Image -ieq $expected.Image) -or
        (!$_.Image -and $_.Name -ieq $name)
    })
    $udp=@(Get-NetUDPEndpoint -ErrorAction Stop|Where-Object LocalPort -EQ 27016)
    if($matches.Count -or $udp.Count){throw 'Stopped Main baseline differs or is ambiguous.'}
    [ordered]@{CapturedUtc=[DateTime]::UtcNow.ToString('o');Baseline='Stopped';
        OriginalPID=$expected.PID;OriginalCreatedUtc=$expected.CreatedUtc;ExpectedImage=$expected.Image;
        OriginalPIDAbsent=$true;ExpectedImageAbsent=$true;UDP27016Absent=$true;Cause='Unknown'}
}
function Assert-T7CatalogueMetadata($Expected) {
    Assert-H1Path $Expected.Path
    $item=Get-Item -LiteralPath $Expected.Path
    if($item.PSIsContainer -or $item.Length -ne $Expected.Bytes -or
       [string]$item.Attributes -cne $Expected.Attributes -or
       $item.LastWriteTimeUtc.Ticks -ne ([datetimeoffset]$Expected.LastWriteUtc).UtcDateTime.Ticks){throw 'Reviewed input metadata changed.'}
}
function Assert-T7CataloguePlan($Plan,[string]$Repo,[string]$Runner) {
    $candidateProfile=Get-T7CatalogueCandidateProfile $Plan
    $null=Get-T7CatalogueMainBaseline $Plan
    if($Plan.Schema -cne 'iw7.t7-catalogue-plan/1' -or $Plan.Runner -cne $Runner -or
       $Plan.EngineOutputProfile -cne 'ObservedStartupA' -or
       $Plan.PhysicalBytes -ne 6GB -or $Plan.CommitBytes -ne 8GB -or
       $Plan.GroupDeadlineSeconds -ne 200 -or $Plan.DeadlineSeconds -ne 120 -or
       $Plan.MutableOutputLimitBytes -ne 64MB -or $Plan.MetadataReserveBytes -ne 64KB -or
       $Plan.CleanupSeconds -ne 5 -or $Plan.ReportLimitBytes -ne 512KB -or
       $Plan.LogLimitBytes -ne 1MB -or $Plan.OutputLimitBytes -ne (106059160L+$Plan.CandidateBytes) -or
       $Plan.RetryAuthorized -isnot [bool] -or $Plan.RetryAuthorized){throw 'Fixed catalogue plan differs.'}
    if(!(Test-T7CatalogueInteger $Plan.CandidateBytes 64MB) -or $Plan.CandidateBytes -le 0 -or
       $Plan.CandidateSHA256 -cnotmatch '\A[0-9a-f]{64}\z'){throw 'Exact bounded candidate identity required.'}
    if($candidateProfile -ceq 'ordinary-d2' -and ($Plan.CandidateBytes -ne 21740032 -or
       $Plan.CandidateSHA256 -cne '94dd29a9cb538504ddeb3545483e43a5dfea195aaca155db5bf147f1c6334c15')){throw 'Ordinary D2 candidate differs.'}
    if($candidateProfile -cne 'ordinary-d2') {
        $limit=if($candidateProfile -ceq 't7-catalog-trace'){1536}else{4096}
        if(!(Test-T7CatalogueInteger $Plan.TraceStderrLimitBytes $limit) -or $Plan.TraceStderrLimitBytes -ne $limit){throw 'Exact trace stderr bound required.'}
    }
    Assert-H1Path $Plan.RunRoot
    if([IO.Path]::GetDirectoryName($Plan.RunRoot) -cne (Join-Path $Repo 'runtime') -or
       [IO.Path]::GetFileName($Plan.RunRoot) -cnotmatch '^t7-catalog-[a-z][a-z0-9-]*$' -or
       $Plan.WorkingDirectory -cne (Join-Path $Plan.RunRoot 'work') -or
       $Plan.StageRoot -cne (Join-Path $Plan.RunRoot 'evidence') -or
       $Plan.Image -cne (Join-Path $Plan.WorkingDirectory 't7-zonetool-candidate.exe') -or
       @($Plan.Arguments).Count -ne 2 -or $Plan.Arguments[0] -cne '-t7-iw7-catalog' -or
       $Plan.Arguments[1] -cne 'mp_freerun_04' -or
       $Plan.OutputKey -cne 't7_iw7_catalog_1d7749fdf2454720fad852816e9ddde027a157a4cc486aa18b3eb8fd4a25c2ce'){throw 'Exact catalogue command/root required.'}
    foreach($dir in @($Plan.RunRoot,$Plan.WorkingDirectory,$Plan.StageRoot,(Join-Path $Plan.RunRoot 'temp'))) {
        Assert-H1Path $dir
        if(![IO.Directory]::Exists($dir)){throw 'Prepared empty ordinary directories required.'}
    }
    $rootNames=@([IO.Directory]::EnumerateFileSystemEntries($Plan.RunRoot)|ForEach-Object {[IO.Path]::GetFileName($_)}|Sort-Object)
    if(($rootNames -join '|') -cne 'evidence|temp|work'){throw 'Fresh attempt root required; no retry or parent zone.'}
    foreach($dir in @($Plan.WorkingDirectory,$Plan.StageRoot,(Join-Path $Plan.RunRoot 'temp'))) {
        if(@([IO.Directory]::EnumerateFileSystemEntries($dir)).Count){throw 'Prepared work/evidence/temp must be empty.'}
    }
    if(@($Plan.Bindings).Count -gt 32 -or @($Plan.Bindings.Path|Sort-Object -Unique).Count -ne @($Plan.Bindings).Count){throw 'Bounded unique bindings required.'}
    foreach($pin in $Plan.Bindings) {
        Assert-H1Path $pin.Path
        $item=Get-Item -LiteralPath $pin.Path
        if($item.PSIsContainer -or $pin.IsText -isnot [bool] -or $pin.Bytes -le 0 -or $pin.Bytes -gt 64MB -or
           ($pin.IsText -and $pin.Bytes -gt 1MB) -or $pin.SHA256 -cnotmatch '^[0-9a-f]{64}$' -or $item.Length -ne $pin.Bytes){throw 'Bound pin metadata differs.'}
    }
    $expected=@(
        @($Plan.CandidateSource,$Plan.CandidateBytes,$Plan.CandidateSHA256),
        @($Plan.EngineSource,21737352,'3df511d71e3690b14517379783bbfb713f6fe2ed2f2e73b445b4878216686156'),
        @($Plan.SteamSource,235600,'71af8666392acad2080a816b9f1196fe9ccb950e1db8a549f8312c4d231f55a8'))
    foreach($row in $expected) {
        $pin=@($Plan.Bindings|Where-Object Path -CEQ $row[0])
        if($pin.Count -ne 1 -or $pin[0].IsText -or $pin[0].Bytes -ne $row[1] -or $pin[0].SHA256 -cne $row[2]){throw 'Exact qualified D2/engine/Steam binding required.'}
    }
    if(@($Plan.InputMetadata).Count -ne 4 -or @($Plan.InputMetadata.Path|Sort-Object -Unique).Count -ne 4){throw 'Four exact input metadata records required.'}
    $paths=@($Plan.CandidateSource,$Plan.EngineSource,$Plan.SteamSource,$Plan.Zone.Path)
    foreach($item in $Plan.InputMetadata){if($item.Path -cnotin $paths){throw 'Unexpected input metadata.'};Assert-T7CatalogueMetadata $item}
    if($Plan.Zone.Bytes -ne 16977344 -or $Plan.Zone.SHA256 -ne $null -or
       $Plan.Zone.RelativePath -cne 'zone/mp_freerun_04.ff' -or
       $Plan.Zone.HashProvenance -cne 'ObserveUnderLease' -or
       [IO.Path]::GetFileName($Plan.Zone.Path) -cne 'mp_freerun_04.ff' -or
       @($Plan.Bindings|Where-Object Path -CEQ $Plan.Zone.Path).Count){throw 'Only the explicit unsealed owner FF is allowed.'}
    Assert-T7CatalogueMetadata $Plan.Zone
}
function Assert-T7CatalogueBuild($Plan,$Receipt) {
    $candidateProfile=Get-T7CatalogueCandidateProfile $Plan
    foreach($field in 'InputsReverified','TreeClosureConfirmed','LeaseReleased','Quarantined','CandidateExecuted') {
        if($Receipt.$field -isnot [bool]){throw 'Build lifecycle booleans required.'}
    }
    if($Receipt.Schema -cne 'iw7.t7-minimal-build/1' -or $Receipt.PlanSHA256 -cne $Plan.ExpectedBuildPlanSHA256 -or
       $Receipt.Status -cne 'Passed' -or !$Receipt.InputsReverified -or !$Receipt.TreeClosureConfirmed -or
       !$Receipt.LeaseReleased -or $Receipt.Quarantined -or $Receipt.CandidateExecuted){throw 'Closed successful unexecuted catalogue build required.'}
    if($candidateProfile -ceq 'ordinary-d2') {
        if($Receipt.PlanSHA256 -cne 'daa7097f872b83a5762b2cb56bf6dd5a235ed2beee8e0ff077276c61622d53fa' -or
           $Receipt.PSObject.Properties['BuildProfile']){throw 'Exact closed ordinary D2 build required.'}
    }else{Assert-T7CatalogueTraceBuild $Plan $Receipt}
    $artifacts=@($Receipt.Stages|ForEach-Object {$_.Artifacts}|Where-Object Path -CEQ $Plan.CandidateSource)
    if($artifacts.Count -ne 1 -or $artifacts[0].Bytes -ne $Plan.CandidateBytes -or $artifacts[0].SHA256 -cne $Plan.CandidateSHA256){throw 'Candidate differs from build artifact.'}
}
function Assert-T7CatalogueTextPin($Pin,$Bindings) {
    Assert-T7CatalogueFields $Pin @('Path','Bytes','SHA256')
    Assert-H1Path $Pin.Path
    if(!(Test-T7CatalogueInteger $Pin.Bytes 1MB) -or $Pin.Bytes -eq 0 -or $Pin.SHA256 -cnotmatch '\A[0-9a-f]{64}\z'){throw 'Bounded exact trace text pin required.'}
    $match=@($Bindings|Where-Object {$_.Path -ceq $Pin.Path -and $_.IsText -is [bool] -and $_.IsText -and $_.Bytes -eq $Pin.Bytes -and $_.SHA256 -ceq $Pin.SHA256})
    if($match.Count -ne 1){throw 'Trace text pin is not guarded.'}
}
function Assert-T7CatalogueTraceBuild($Plan,$Receipt) {
    $candidateProfile=Get-T7CatalogueCandidateProfile $Plan
    $buildPin=@($Plan.Bindings|Where-Object {$_.Path -ceq $Plan.BuildPlan -and $_.IsText})
    if($buildPin.Count -ne 1 -or $buildPin[0].SHA256 -cne $Plan.ExpectedBuildPlanSHA256 -or
       $buildPin[0].Bytes -gt 1MB -or $Plan.ExpectedBuildPlanSHA256 -ceq 'daa7097f872b83a5762b2cb56bf6dd5a235ed2beee8e0ff077276c61622d53fa'){throw 'Trace requires its own guarded build plan.'}
    $build=Read-H1SmallJson $Plan.BuildPlan 1MB
    if($build.Schema -cne 'iw7.t7-minimal-build-plan/1' -or
       $build.SourceCommit -cne 'fab935826c898806855376662a8a03317b3ad8f1'){throw 'Trace build source/schema differs.'}
    $profile=$build.BuildProfile
    $fields=@('Name','Option','ArgumentCount','TraceSchema','Wiring','PreparedMain','BaseBuildPlan','BaseBuildReceipt')
    if($candidateProfile -ceq 't7-catalog-exit-context'){$fields+=@('ContextSchema')}
    foreach($p in @($profile,$Receipt.BuildProfile)) {
        Assert-T7CatalogueFields $p $fields
        if($p.Name -cne $candidateProfile -or $p.Option -cne '-t7-iw7-catalog' -or
           ($p.ArgumentCount -isnot [long] -and $p.ArgumentCount -isnot [int]) -or $p.ArgumentCount -ne 3 -or
           $p.TraceSchema -cne 'iw7.t7-catalog-trace/1'){throw 'Exact catalogue trace profile required.'}
        if($candidateProfile -ceq 't7-catalog-exit-context' -and $p.ContextSchema -cne 'iw7.t7-catalog-exit-context/1'){throw 'Exact exit context schema required.'}
    }
    foreach($name in 'Wiring','PreparedMain','BaseBuildPlan','BaseBuildReceipt') {
        $pin=$profile.$name;$other=$Receipt.BuildProfile.$name
        Assert-T7CatalogueTextPin $pin $Plan.Bindings
        Assert-T7CatalogueTextPin $pin $build.Bindings
        Assert-T7CatalogueFields $other @('Path','Bytes','SHA256')
        if($other.Path -cne $pin.Path -or $other.Bytes -ne $pin.Bytes -or $other.SHA256 -cne $pin.SHA256){throw 'Receipt trace profile differs from build plan.'}
    }
    if($profile.PreparedMain.Path -cne (Join-Path $build.PreparedRoot 'main.cpp') -or
       $profile.Wiring.Path -cne (Join-Path ([IO.Path]::GetDirectoryName($build.Runner)) 'prepare_catalog_trace.py') -or
       $profile.BaseBuildPlan.SHA256 -cne 'daa7097f872b83a5762b2cb56bf6dd5a235ed2beee8e0ff077276c61622d53fa' -or
       $profile.BaseBuildReceipt.SHA256 -cne 'c609bc56523654d8bca4b855024a463393185aab8e19ed4eae94c1ff8f6a09c2'){throw 'Trace source/base provenance differs.'}
    $base=Read-H1SmallJson $profile.BaseBuildPlan.Path 1MB
    $reuse=$build.ReuseCompile;$old=$base.ReuseCompile
    if($base.Schema -cne 'iw7.t7-minimal-build-plan/1' -or $reuse.RecompiledMain -isnot [bool] -or !$reuse.RecompiledMain -or
       $reuse.OriginalStatus -cne 'Failed' -or $reuse.Checks -ne 51){throw 'Trace must recompile main and retain qualified failed-group objects.'}
    foreach($name in 'SourcePlan','SourcePlanSHA256','Receipt','ReceiptSHA256') {
        if($reuse.$name -cne $old.$name){throw 'Trace reuse chain differs from ordinary D2.'}
        if($name -cin @('SourcePlan','Receipt')) {
            $pin=@($base.Bindings|Where-Object {$_.Path -ceq $old.$name -and $_.IsText})
            if($pin.Count -ne 1){throw 'D2 reuse source pin missing.'}
            Assert-T7CatalogueTextPin ([pscustomobject]@{Path=$pin[0].Path;Bytes=$pin[0].Bytes;SHA256=$pin[0].SHA256}) $build.Bindings
        }
    }
    $retained=@($old.StageRoots|Where-Object {[IO.Path]::GetFileName($_) -cne 'main'})
    if(@($reuse.StageRoots).Count -ne 2 -or (@($retained|ForEach-Object {[IO.Path]::GetFileName($_)}) -join '|') -cne 'zonetool11|xpak' -or
       (@($reuse.StageRoots) -join '|') -cne ($retained -join '|')){throw 'Exact retained zonetool11/xpak roots required.'}
    foreach($stages in @(@{Rows=@($build.Stages)},@{Rows=@($Receipt.Stages)})) {
        if($stages.Rows.Count -ne 2 -or ($stages.Rows.Name -join '|') -cne 'main|link' -or
           ($stages.Rows.Stage -join '|') -cne 'Compile|Link'){throw 'Trace requires actual main Compile then link Link.'}
    }
    for($i=0;$i -lt 2;$i++) {
        $stage=$Receipt.Stages[$i]
        if($stage.PlanSHA256 -cne $Plan.ExpectedBuildPlanSHA256 -or $stage.ExitCode -ne 0 -or
           $stage.TreeClosureConfirmed -isnot [bool] -or !$stage.TreeClosureConfirmed){throw 'Trace compile/link stage not successful and closed.'}
    }
    $mainRoot=Join-Path $build.RunRoot 'main';$linkRoot=Join-Path $build.RunRoot 'link'
    $mainObject=Join-Path $mainRoot 'main.obj';$dependencyPath=Join-Path $mainRoot 'dependencies.json'
    foreach($path in @($mainObject,$dependencyPath)) {
        $pin=@($Receipt.Stages[0].Artifacts|Where-Object Path -CEQ $path)
        if($pin.Count -ne 1 -or $pin[0].Bytes -le 0 -or $pin[0].SHA256 -cnotmatch '\A[0-9a-f]{64}\z'){throw 'Trace main artifact missing.'}
        if($path -ceq $dependencyPath){Assert-T7CatalogueTextPin $pin[0] $Plan.Bindings}
    }
    $deps=Read-H1SmallJson $dependencyPath 1MB
    if([IO.Path]::GetFullPath($deps.Data.Source) -ine $profile.PreparedMain.Path){throw 'Compiler dependencies do not identify prepared trace main.'}
    $link=$build.Stages[1]
    $rsp=Join-Path ([IO.Path]::GetDirectoryName($build.PreparedRoot)) 'link.rsp'
    if(@($link.Arguments).Count -ne 1 -or $link.Arguments[0] -cne ('@'+$rsp) -or
       $Plan.CandidateSource -cne (Join-Path $linkRoot 'zonetool-t7.exe')){throw 'Trace link command/artifact differs.'}
    $rspPin=@($build.Bindings|Where-Object {$_.Path -ceq $rsp -and $_.IsText})
    if($rspPin.Count -ne 1){throw 'Trace link response pin missing.'}
    Assert-T7CatalogueTextPin ([pscustomobject]@{Path=$rsp;Bytes=$rspPin[0].Bytes;SHA256=$rspPin[0].SHA256}) $Plan.Bindings
    if(@([IO.File]::ReadAllLines($rsp)|Where-Object {$_ -ceq ('"'+$mainObject+'"')}).Count -ne 1){throw 'Trace Link must consume the newly compiled main object exactly once.'}
    if(@($Receipt.Stages[1].Artifacts|Where-Object Path -CEQ $Plan.CandidateSource).Count -ne 1){throw 'Trace candidate absent from Link artifacts.'}
}
function Get-T7CatalogueFileId([string]$Path) { [IW7HudFileIdentity]::Read($Path) }
function Open-T7CatalogueZone($Zone,$Context) {
    Assert-T7CatalogueMetadata $Zone
    # The only unsealed payload. Hold this exact source open before observing its hash.
    $guard=[IO.FileStream]::new($Zone.Path,'Open','Read','Read')
    try {
        Assert-T7CatalogueMetadata $Zone
        if($guard.Length -ne 16977344){throw 'Observed FF length differs.'}
        $fileId=Get-T7CatalogueFileId $Zone.Path
        $hash=[Security.Cryptography.SHA256]::Create()
        try{$sha=[Convert]::ToHexString($hash.ComputeHash($guard)).ToLowerInvariant()}finally{$hash.Dispose()}
        Assert-T7CatalogueMetadata $Zone
        if($guard.Length -ne $Zone.Bytes -or (Get-T7CatalogueFileId $Zone.Path) -cne $fileId){throw 'Observed FF identity changed.'}
        $guard.Position=0;$Context.Guards.Add($guard)
        [pscustomobject]@{Path=$Zone.Path;Bytes=$Zone.Bytes;SHA256=$sha;IsText=$false;FileId=$fileId;HashProvenance='ObservedUnderLeaseNotDepotVerified'}
    }catch{$guard.Dispose();throw}
}
function New-T7CatalogueAlias($Pin,[string]$Destination,$Context) {
    Assert-H1Path $Destination
    if(Test-Path -LiteralPath $Destination){throw 'Alias destination already exists.'}
    $sourceId=Get-T7CatalogueFileId $Pin.Path
    New-Item -ItemType HardLink -Path $Destination -Target $Pin.Path -ErrorAction Stop|Out-Null
    $guard=Open-H1Pin ([pscustomobject]@{Path=$Destination;Bytes=$Pin.Bytes;SHA256=$Pin.SHA256})
    $Context.Guards.Add($guard)
    $aliasId=Get-T7CatalogueFileId $Destination
    if($sourceId -cne $aliasId){throw 'Source/alias file IDs differ.'}
    [pscustomobject]@{Path=$Destination;Source=$Pin.Path;Bytes=$Pin.Bytes;SHA256=$Pin.SHA256;FileId=$aliasId}
}
function New-T7CatalogueStart($Plan) {
    $start=New-T7PrepatchStart $Plan # Environment setup only; diagnostic is not invoked.
    $start.ArgumentList.Clear();$start.ArgumentList.Add('-t7-iw7-catalog');$start.ArgumentList.Add('mp_freerun_04')
    $start
}
function Assert-T7CatalogueFields($Value,[string[]]$Fields) {
    if($null -eq $Value -or $Value -isnot [pscustomobject] -or
       (@($Value.PSObject.Properties.Name|Sort-Object) -join '|') -cne (@($Fields|Sort-Object) -join '|')){throw 'Exact catalogue fields required.'}
}
function Test-T7CatalogueInteger($Value,[long]$Maximum) {
    ($Value -is [int] -or $Value -is [long]) -and $Value -ge 0 -and $Value -le $Maximum
}
function Get-T7CatalogueOutcome($Report,[Nullable[int]]$ExitCode) {
    if($null -eq $Report){return 'NoCatalogue'}
    $falseFields=@('truncated','asset_zone_ownership_verified','zonetool_xpak_helper_reads_allowed','engine_io_verified','geometry_verified','runtime_verified','ready')
    Assert-T7CatalogueFields $Report (@('schema','requested_zone','provenance','model_count','name_bytes','models')+$falseFields)
    if($Report.schema -cne 'iw7.t7-iw7-model-catalog/1' -or $Report.requested_zone -cne 'mp_freerun_04' -or
       $Report.provenance -cne 'observed_during_requested_zone_load'){throw 'Catalogue request/provenance differs.'}
    foreach($field in $falseFields){if($Report.$field -isnot [bool] -or $Report.$field){throw 'Catalogue overclaims its scope.'}}
    if($Report.models -isnot [array] -or !(Test-T7CatalogueInteger $Report.model_count 1024) -or
       $Report.model_count -ne $Report.models.Count -or !(Test-T7CatalogueInteger $Report.name_bytes 256KB)){throw 'Catalogue count exceeds bound or differs.'}
    $previous=$null;$nameBytes=0
    foreach($row in $Report.models) {
        Assert-T7CatalogueFields $row @('name','reference','resolved_nondefault','counts')
        if($row.name -isnot [string] -or $row.name -cnotmatch '\A[\x20-\x7e]{1,255}\z' -or
           ($null -ne $previous -and [string]::CompareOrdinal($previous,$row.name) -ge 0)){throw 'Names must be bounded ASCII, sorted and unique.'}
        if($row.reference -isnot [bool] -or $row.reference -ne $row.name.StartsWith(',') -or
           $row.resolved_nondefault -isnot [bool]){throw 'Reference/resolution flags differ.'}
        if($row.resolved_nondefault) {
            if($row.reference){throw 'Reference alias cannot claim resolved counts.'}
            Assert-T7CatalogueFields $row.counts @('bones','roots','cosmetic_bones','lods')
            foreach($name in 'bones','roots','cosmetic_bones','lods') {
                $max=if($name -ceq 'cosmetic_bones'){65535}else{255}
                if(!(Test-T7CatalogueInteger $row.counts.$name $max)){throw 'Header count width differs.'}
            }
        }elseif($null -ne $row.counts){throw 'Unresolved row cannot claim counts.'}
        $nameBytes+=$row.name.Length+1;$previous=$row.name
    }
    if($nameBytes -ne $Report.name_bytes){throw 'Name byte count differs.'}
    if($ExitCode -ne 0){return 'ValidCatalogueFromFailedProcess'}
    if($Report.model_count -eq 0){return 'EmptyCatalogue'}
    'CatalogueWithNames'
}
function Read-T7CatalogueReport($Plan,$State,$Context) {
    $path=Join-Path (Join-Path $Plan.WorkingDirectory $Plan.OutputKey) 'catalog.json'
    if(!(Test-Path -LiteralPath $path)){return 'NoCatalogue'}
    $State.CatalogueOutcome='CataloguePresentUnqualified'
    Assert-H1Path $path
    $size=(Get-Item -LiteralPath $path).Length
    if($size -le 0 -or $size -gt 512KB){throw 'Catalogue JSON size refused.'}
    $pin=[pscustomobject]@{Path=$path;Bytes=$size;SHA256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
    $Context.Guards.Add((Open-H1Pin $pin));$State.Report=$pin
    $report=Read-H1SmallJson $path 512KB
    $outcome=Get-T7CatalogueOutcome $report $State.ExitCode
    $State.ModelCount=$report.model_count
    $outcome
}
function ConvertFrom-T7CatalogueTrace([string]$Text) {
    if($Text.Length -eq 0){return [pscustomobject]@{Outcome='NoTrace';Events=@()}}
    if([Text.Encoding]::UTF8.GetByteCount($Text) -ge 1536 -or !$Text.EndsWith("`n")){throw 'Trace stderr oversized or incomplete.'}
    $lines=$Text.Substring(0,$Text.Length-1).Split("`n")
    if($lines.Count -gt 6){throw 'Trace exceeds six one-shot events.'}
    $events=[Collections.Generic.List[object]]::new();$seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $prefix='\A\[T7_CATALOG_TRACE\] schema=iw7\.t7-catalog-trace/1 phase='
    $tid='(0|[1-9][0-9]{0,9})'
    foreach($raw in $lines) {
        if($raw.Length+1 -ge 256){throw 'Trace line reaches 256 bytes.'}
        $line=$raw -creplace '\r$',''
        $enabled=[regex]::Match($line,($prefix+'enabled stdout_unbuffered=([01]) stderr_unbuffered=([01]) tid='+$tid+'\z'))
        if($enabled.Success) {
            $row=[pscustomobject]@{Phase='enabled';StdoutUnbuffered=($enabled.Groups[1].Value -ceq '1');StderrUnbuffered=($enabled.Groups[2].Value -ceq '1');ThreadId=[ulong]$enabled.Groups[3].Value}
        }else {
            $match=[regex]::Match($line,($prefix+'(before_post_unpack|after_post_unpack|before_entry_point|entry_point_return|exit_hook) code=(0|-?[1-9][0-9]{0,9}) tid='+$tid+' return_address=([0-9A-Fa-f]{16})\z'))
            if(!$match.Success){throw 'Unknown trace event or stderr format.'}
            $code=[long]$match.Groups[2].Value
            if($code -lt [int]::MinValue -or $code -gt [int]::MaxValue){throw 'Trace code exceeds signed int32.'}
            $row=[pscustomobject]@{Phase=$match.Groups[1].Value;Code=$code;ThreadId=[ulong]$match.Groups[3].Value;ReturnAddress=$match.Groups[4].Value}
            if($row.Phase -cin @('before_post_unpack','after_post_unpack','before_entry_point') -and $code -ne 0){throw 'Nonzero boundary trace code.'}
            if($row.Phase -cne 'exit_hook' -and $row.ReturnAddress -cne '0000000000000000'){throw 'Unexpected non-exit trace return address.'}
        }
        if($row.ThreadId -gt [uint]::MaxValue -or !$seen.Add($row.Phase)){throw 'Trace thread ID or duplicate event differs.'}
        $events.Add($row)
    }
    [pscustomobject]@{Outcome=$(if($seen.Contains('enabled')){'TraceObserved'}else{'TracePartial'});Events=@($events.ToArray())}
}
function Read-T7CatalogueTrace($Plan,$State,$Context) {
    $profile=Get-T7CatalogueCandidateProfile $Plan
    if($profile -ceq 'ordinary-d2'){return}
    $State.TraceOutcome='NoTrace'
    if($profile -ceq 't7-catalog-exit-context'){$State.ExitContextOutcome='Absent';$State.ExitContext=[ordered]@{Captures=@();IncompleteTrailingLine=$false}}
    $path=Join-Path $Plan.StageRoot 'stderr.log'
    if(!(Test-Path -LiteralPath $path)){return}
    $State.TraceOutcome='TracePresentUnqualified'
    Assert-H1Path $path
    $size=(Get-Item -LiteralPath $path).Length
    if($profile -ceq 't7-catalog-exit-context' -and $size -gt 0){$State.ExitContextOutcome='PresentUnqualified'}
    Assert-T7CatalogueTraceSize $profile $size
    $pin=[pscustomobject]@{Path=$path;Bytes=$size;SHA256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
    $Context.Guards.Add((Open-H1Pin $pin));$State.TraceReport=$pin
    $text=[Text.UTF8Encoding]::new($false,$true).GetString([IO.File]::ReadAllBytes($path))
    $result=if($profile -ceq 't7-catalog-exit-context'){ConvertFrom-T7CatalogueExitContext $text}else{ConvertFrom-T7CatalogueTrace $text}
    $State.TraceOutcome=$result.Outcome;$State.TraceEvents=$result.Events
    if($profile -ceq 't7-catalog-exit-context'){$State.ExitContextOutcome=$result.ContextOutcome;$State.ExitContext=$result.Context}
}
function Assert-T7CatalogueTraceSize([string]$Profile,[long]$Bytes) {
    if(($Profile -ceq 't7-catalog-trace' -and $Bytes -ge 1536) -or
       ($Profile -ceq 't7-catalog-exit-context' -and $Bytes -gt 4096)){throw 'Trace stderr cap exceeded.'}
}
function Get-T7CatalogueContextNumber($Match,[string]$Name,[ulong]$Maximum=[uint]::MaxValue) {
    $value=[ulong]::Parse($Match.Groups[$Name].Value,[Globalization.CultureInfo]::InvariantCulture)
    if($value -gt $Maximum){throw 'Exit context integer exceeds field width.'}
    $value
}
function ConvertFrom-T7CatalogueExitLine([string]$Line) {
    $dec='(0|[1-9][0-9]{0,19})';$ptr='[0-9A-Fa-f]{16}'
    $prefix='\A\[T7_CATALOG_EXIT\] schema=iw7\.t7-catalog-exit-context/1 kind='
    $head=$prefix+'(?<kind>memory|stack|function) code=(?<code>0|-?[1-9][0-9]{0,9}) tid=(?<tid>'+ $dec +') ra=(?<ra>'+ $ptr +') '
    $prefixMatch=[regex]::Match($Line,$head)
    if(!$prefixMatch.Success){throw 'Unknown exit context prefix or correlation fields.'}
    $kind=$prefixMatch.Groups['kind'].Value
    $tail=switch($kind) {
        memory {'status=(?<status>ok|module_missing|module_mismatch|address_invalid|query_failed|region_invalid|read_failed|partial|exception) start=(?<start>'+$ptr+') requested=256 read=(?<read>'+$dec+') module=(?<module>'+$ptr+') allocation=(?<allocation>'+$ptr+') region=(?<region>'+$ptr+') region_size=(?<region_size>'+$dec+') state=(?<state>'+$dec+') protect=(?<protect>'+$dec+') type=(?<type>'+$dec+') error=(?<error>'+$dec+') data=(?<data>-|[0-9A-F]+)\z'}
        stack {'status=(?<status>ok|empty|invalid_count|exception) count=(?<count>'+$dec+') error=(?<error>'+$dec+') addresses=(?<addresses>-|[0-9A-F]{16}(,[0-9A-F]{16}){0,7})\z'}
        function {'status=(?<status>ok|not_found|module_mismatch|query_failed|region_invalid|read_failed|partial|record_invalid|exception) image=(?<image>'+$ptr+') record=(?<record>'+$ptr+') read=(?<read>'+$dec+') begin=(?<begin>[0-9A-F]{8}) end=(?<end>[0-9A-F]{8}) unwind=(?<unwind>[0-9A-F]{8}) error=(?<error>'+$dec+')\z'}
    }
    $m=[regex]::Match($Line,$head+$tail)
    if(!$m.Success){throw 'Unknown exit context status or field format.'}
    $code=[long]$m.Groups['code'].Value
    if($code -lt [int]::MinValue -or $code -gt [int]::MaxValue){throw 'Exit context code exceeds int32.'}
    $ra=$m.Groups['ra'].Value;$raValue=[Convert]::ToUInt64($ra,16)
    $row=[ordered]@{Kind=$kind;Code=$code;ThreadId=(Get-T7CatalogueContextNumber $m 'tid');ReturnAddress=$ra;
        Status=$m.Groups['status'].Value;Error=(Get-T7CatalogueContextNumber $m 'error')}
    switch($kind) {
        memory {
            foreach($field in 'start','module','allocation','region'){$row[$field]=$m.Groups[$field].Value}
            $row.Requested=256;$row.ReadBytes=Get-T7CatalogueContextNumber $m 'read' 256
            $row.RegionSize=Get-T7CatalogueContextNumber $m 'region_size' ([ulong]::MaxValue)
            foreach($field in 'state','protect','type'){$row[$field]=Get-T7CatalogueContextNumber $m $field}
            $row.DataHex=$m.Groups['data'].Value
            if(($row.ReadBytes -eq 0 -and $row.DataHex -cne '-') -or
               ($row.ReadBytes -gt 0 -and ($row.DataHex -ceq '-' -or $row.DataHex.Length -ne 2*$row.ReadBytes))){throw 'Exit memory data/read mismatch.'}
            if(($row.Status -ceq 'partial' -and ($row.ReadBytes -eq 0 -or $row.ReadBytes -eq 256)) -or
               ($row.Status -ceq 'read_failed' -and $row.ReadBytes -notin @(0,256)) -or
               ($row.Status -cnotin @('ok','partial','read_failed','exception') -and $row.ReadBytes -ne 0)){throw 'Exit memory status/read mismatch.'}
            if($row.Status -ceq 'ok') {
                $start=[Convert]::ToUInt64($row.start,16);$region=[Convert]::ToUInt64($row.region,16)
                if($row.ReadBytes -ne 256 -or $row.Error -ne 0 -or $raValue -lt 64 -or $start -ne $raValue-64 -or
                   [Convert]::ToUInt64($row.module,16) -ne 0x140000000L -or [Convert]::ToUInt64($row.allocation,16) -ne 0x140000000L -or
                   $row.state -ne 0x1000 -or ($row.protect -band 0x100) -ne 0 -or
                   ($row.protect -band 0xFF) -eq 1 -or ($row.protect -band 0xFF) -eq 0 -or $start -lt $region -or
                   $row.RegionSize -lt 256 -or ([decimal]$start-[decimal]$region) -gt ([decimal]$row.RegionSize-256)){throw 'Successful exit memory capture has inconsistent bounds.'}
            }
        }
        stack {
            $row.Count=Get-T7CatalogueContextNumber $m 'count' 8
            $value=$m.Groups['addresses'].Value
            $row.Addresses=@(if($value -cne '-'){$value.Split(',')})
            if($row.Addresses.Count -ne $row.Count -or ($row.Count -eq 0 -and $value -cne '-')){throw 'Exit stack address/count mismatch.'}
            if($row.Status -ceq 'ok' -and ($row.Count -eq 0 -or $row.Error -ne 0)){throw 'Successful exit stack capture is empty or failed.'}
            if($row.Status -cne 'ok' -and $row.Count -ne 0){throw 'Failed exit stack capture exposes addresses.'}
        }
        function {
            $row.Image=$m.Groups['image'].Value;$row.Record=$m.Groups['record'].Value
            $row.ReadBytes=Get-T7CatalogueContextNumber $m 'read' 12
            foreach($field in 'begin','end','unwind'){$row[$field]=[Convert]::ToUInt32($m.Groups[$field].Value,16)}
            if($row.ReadBytes -ne 12 -and ($row.begin -ne 0 -or $row.end -ne 0 -or $row.unwind -ne 0)){throw 'Incomplete runtime function copy exposes RVAs.'}
            if(($row.Status -ceq 'partial' -and ($row.ReadBytes -eq 0 -or $row.ReadBytes -eq 12)) -or
               ($row.Status -cin @('read_failed','record_invalid') -and $row.ReadBytes -notin @(0,12)) -or
               ($row.Status -cnotin @('ok','partial','read_failed','record_invalid','exception') -and $row.ReadBytes -ne 0)){throw 'Runtime function status/read mismatch.'}
            if($row.Status -cnotin @('ok','record_invalid') -and ($row.begin -ne 0 -or $row.end -ne 0 -or $row.unwind -ne 0)){throw 'Failed runtime function copy exposes RVAs.'}
            if($row.Status -ceq 'ok') {
                $base=[Convert]::ToUInt64($row.Image,16)
                if($row.ReadBytes -ne 12 -or $row.Error -ne 0 -or $base -ne 0x140000000L -or
                   [Convert]::ToUInt64($row.Record,16) -eq 0 -or $raValue -eq 0 -or $row.begin -ge $row.end -or
                   ([decimal]$raValue-1) -lt ([decimal]$base+$row.begin) -or ([decimal]$raValue-1) -ge ([decimal]$base+$row.end)){throw 'Successful runtime function capture does not contain RA-1.'}
            }
        }
    }
    [pscustomobject]$row
}
function ConvertFrom-T7CatalogueExitContext([string]$Text) {
    Assert-T7CatalogueTraceSize 't7-catalog-exit-context' ([Text.Encoding]::UTF8.GetByteCount($Text))
    if($Text -cmatch '[^\x20-\x7e\r\n]'){throw 'Exit context stderr must be ASCII without BOM.'}
    if(!$Text.Length){return [pscustomobject]@{Outcome='NoTrace';Events=@();ContextOutcome='Absent';Context=[ordered]@{Captures=@();IncompleteTrailingLine=$false}}}
    $complete=$Text.EndsWith("`n")
    $lines=if($complete){@($Text.Substring(0,$Text.Length-1).Split("`n"))}else{@($Text.Split("`n"))}
    if($lines.Count -gt 9){throw 'Exit context stderr exceeds nine lines.'}
    $markers=[Collections.Generic.List[string]]::new();$captures=[Collections.Generic.List[object]]::new()
    $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $prefix='[T7_CATALOG_EXIT] schema=iw7.t7-catalog-exit-context/1 kind='
    $exitSeen=$false;$incomplete=$false;$lastKind=-1
    for($i=0;$i -lt $lines.Count;$i++) {
        $raw=$lines[$i];$line=$raw -creplace '\r$',''
        if(!$complete -and $i -eq $lines.Count-1) {
            if(!$exitSeen -or $captures.Count -ge 3 -or (!$prefix.StartsWith($line,[StringComparison]::Ordinal) -and !$line.StartsWith($prefix,[StringComparison]::Ordinal))){throw 'Unrecognized incomplete exit context line.'}
            $incomplete=$true
            if($line.StartsWith($prefix,[StringComparison]::Ordinal)) {
                $kind=($line.Substring($prefix.Length) -split ' ',2)[0]
                $possible=@('memory','stack','function'|Where-Object {$_.StartsWith($kind,[StringComparison]::Ordinal)})
                if(!$possible.Count){throw 'Unknown incomplete exit context kind.'}
                if($kind -cin @('memory','stack','function')) {
                    $index=[array]::IndexOf(@('memory','stack','function'),$kind)
                    $cap=if($kind -ceq 'memory'){1024}else{512}
                    if($seen.Contains($kind) -or $index -le $lastKind -or $raw.Length -gt $cap){throw 'Duplicate, reordered or oversized incomplete exit context.'}
                }
            }
            continue
        }
        if($line.StartsWith('[T7_CATALOG_TRACE] ',[StringComparison]::Ordinal)) {
            $markers.Add($raw+"`n")
            if($line -cmatch ' phase=exit_hook '){$exitSeen=$true}
            continue
        }
        $row=ConvertFrom-T7CatalogueExitLine $line
        $cap=if($row.Kind -ceq 'memory'){1024}else{512}
        $index=[array]::IndexOf(@('memory','stack','function'),$row.Kind)
        if(!$exitSeen -or !$seen.Add($row.Kind) -or $index -le $lastKind -or $raw.Length+1 -gt $cap){throw 'Exit context order, duplicate or line bound differs.'}
        $lastKind=$index;$captures.Add($row)
    }
    $trace=ConvertFrom-T7CatalogueTrace ($markers -join '')
    if($captures.Count -or $incomplete) {
        $exit=@($trace.Events|Where-Object Phase -CEQ 'exit_hook')
        if($exit.Count -ne 1){throw 'Exit context has no matching exit_hook.'}
        foreach($row in $captures){if($row.Code -ne $exit[0].Code -or $row.ThreadId -ne $exit[0].ThreadId -or $row.ReturnAddress -ine $exit[0].ReturnAddress){throw 'Exit context correlation differs from exit_hook.'}}
    }
    $outcome=if(!$captures.Count -and !$incomplete){'Absent'}elseif($captures.Count -eq 3 -and !$incomplete -and !@($captures|Where-Object Status -CNE 'ok').Count){'Observed'}else{'Partial'}
    [pscustomobject]@{Outcome=$trace.Outcome;Events=$trace.Events;ContextOutcome=$outcome;
        Context=[ordered]@{Captures=@($captures.ToArray());IncompleteTrailingLine=$incomplete}}
}
function Assert-T7CatalogueEngineOutputs($Plan,[switch]$Closed,$Context) {
    Assert-H1Path $Plan.WorkingDirectory
    $allowedFiles=@('BlackOps3_UnrankedDedicatedServer.exe','steam_api64.dll','t7-zonetool-candidate.exe')
    foreach($entry in [IO.Directory]::EnumerateFileSystemEntries($Plan.WorkingDirectory)) {
        Assert-H1Path $entry
        $name=[IO.Path]::GetFileName($entry)
        if($name -cin $allowedFiles){if([IO.Directory]::Exists($entry)){throw 'Binary alias became a directory.'};continue}
        if($name -ceq 'steam_appid.txt') {
            if([IO.Directory]::Exists($entry) -or (Get-Item -LiteralPath $entry).Length -gt 6){throw 'Observed Steam app-id output type/size differs.'}
            if($Closed) {
                # Partial writes are tolerated during observation, never at acceptance.
                $sha=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::ASCII.GetBytes('311210'))).ToLowerInvariant()
                $Context.Guards.Add((Open-H1Pin ([pscustomobject]@{Path=$entry;Bytes=6;SHA256=$sha})))
            }
            continue
        }
        if($name -ceq 'identities') {
            if(![IO.Directory]::Exists($entry)){throw 'Observed identities path must be a directory.'}
            # Only the four empty directory shapes observed in A. Never read keys.
            $allowed=@('dedicatedpc','dedicatedpc\dumps','dedicatedpc\LPC')
            $pending=[Collections.Generic.Stack[string]]::new();$pending.Push($entry)
            while($pending.Count) {
                foreach($child in [IO.Directory]::EnumerateFileSystemEntries($pending.Pop())) {
                    Assert-H1Path $child
                    $relative=$child.Substring($entry.Length+1)
                    if($relative -cnotin $allowed -or ![IO.Directory]::Exists($child)){throw 'Unexpected identity entry; retain privately without reading payload.'}
                    $pending.Push($child)
                }
            }
            continue
        }
        if($name -cnotin @('zone',$Plan.OutputKey) -or ![IO.Directory]::Exists($entry)){throw 'Unexpected engine output; preserve and stop.'}
        $allowed=if($name -ceq 'zone'){'mp_freerun_04.ff'}else{'catalog.json'}
        foreach($child in [IO.Directory]::EnumerateFileSystemEntries($entry)) {
            Assert-H1Path $child
            if([IO.Path]::GetFileName($child) -cne $allowed -or [IO.Directory]::Exists($child)){throw 'Unexpected zone/catalogue output; preserve and stop.'}
            if($allowed -ceq 'catalog.json' -and (Get-Item -LiteralPath $child).Length -gt 512KB){throw 'Catalogue report cap exceeded.'}
        }
    }
    if(Test-Path -LiteralPath (Join-Path $Plan.RunRoot 'zone')){throw 'Unexpected parent zone.'}
}
function Enable-T7CatalogueRuntimeProfile($Plan) {
    $script:T7CatalogueGroupStarted=Get-H1Clock
    $script:T7CatalogueBaseDeadline=${function:Assert-H1Deadline};$script:T7CatalogueBaseBudget=${function:Test-H1Budget}
    function script:Assert-H1Deadline($Started,[int]$Seconds) {
        & $script:T7CatalogueBaseDeadline $script:T7CatalogueGroupStarted 200
        & $script:T7CatalogueBaseDeadline $Started $Seconds
    }
    function script:Test-H1Budget($Plan,$State) {
        Assert-H1Deadline $script:T7CatalogueGroupStarted 200
        & $script:T7CatalogueBaseBudget $Plan $State
        foreach($name in 'stdout.log','stderr.log') {
            $path=Join-Path $Plan.StageRoot $name
            if((Test-Path -LiteralPath $path) -and (Get-Item -LiteralPath $path).Length -gt 1MB){throw 'Catalogue log cap exceeded.'}
            if($name -ceq 'stderr.log' -and (Test-Path -LiteralPath $path)){
                Assert-T7CatalogueTraceSize (Get-T7CatalogueCandidateProfile $Plan) (Get-Item -LiteralPath $path).Length
            }
        }
        Assert-T7CatalogueEngineOutputs $Plan
        Assert-H1Deadline $script:T7CatalogueGroupStarted 200
    }
}

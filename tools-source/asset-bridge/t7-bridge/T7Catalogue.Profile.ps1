# Fixed catalogue adapter. Ownership, pin readers and closure stay in H1Native.Core.
function Get-T7CatalogueCandidateProfile($Plan) {
    if(!$Plan.PSObject.Properties['CandidateProfile']){return 'ordinary-d2'}
    if($Plan.CandidateProfile -cnotin @('ordinary-d2','t7-catalog-trace','t7-catalog-exit-context','t7-catalog-callers','t7-catalog-message')){throw 'Unknown catalogue candidate profile.'}
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
        $limit=switch($candidateProfile){'t7-catalog-trace'{1536};'t7-catalog-exit-context'{4096};'t7-catalog-callers'{8192};'t7-catalog-message'{8192}}
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
    if($candidateProfile -cin @('t7-catalog-exit-context','t7-catalog-callers','t7-catalog-message')){$fields+=@('ContextSchema')}
    if($candidateProfile -cin @('t7-catalog-callers','t7-catalog-message')){$fields+=@('CallerSchema')}
    if($candidateProfile -ceq 't7-catalog-message'){$fields+=@('MessageSchema')}
    foreach($p in @($profile,$Receipt.BuildProfile)) {
        Assert-T7CatalogueFields $p $fields
        if($p.Name -cne $candidateProfile -or $p.Option -cne '-t7-iw7-catalog' -or
           ($p.ArgumentCount -isnot [long] -and $p.ArgumentCount -isnot [int]) -or $p.ArgumentCount -ne 3 -or
           $p.TraceSchema -cne 'iw7.t7-catalog-trace/1'){throw 'Exact catalogue trace profile required.'}
        if($candidateProfile -cin @('t7-catalog-exit-context','t7-catalog-callers','t7-catalog-message') -and $p.ContextSchema -cne 'iw7.t7-catalog-exit-context/1'){throw 'Exact exit context schema required.'}
        if($candidateProfile -cin @('t7-catalog-callers','t7-catalog-message') -and $p.CallerSchema -cne 'iw7.t7-catalog-callers/1'){throw 'Exact caller schema required.'}
        if($candidateProfile -ceq 't7-catalog-message' -and $p.MessageSchema -cne 'iw7.t7-catalog-message/1'){throw 'Exact message schema required.'}
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
    $hasContext=$profile -cin @('t7-catalog-exit-context','t7-catalog-callers','t7-catalog-message')
    $hasCallers=$profile -cin @('t7-catalog-callers','t7-catalog-message')
    if($hasContext){$State.ExitContextOutcome='Absent';$State.ExitContext=[ordered]@{Captures=@();IncompleteTrailingLine=$false}}
    if($hasCallers){$State.CallersOutcome='Absent';$State.Callers=[ordered]@{Captures=@();IncompleteTrailingLine=$false}}
    if($profile -ceq 't7-catalog-message'){$State.MessageOutcome='Absent';$State.Message=[ordered]@{Captures=@();IncompleteTrailingLine=$false;ExitCorrelated=$false}}
    $path=Join-Path $Plan.StageRoot 'stderr.log'
    if(!(Test-Path -LiteralPath $path)){return}
    $State.TraceOutcome='TracePresentUnqualified'
    Assert-H1Path $path
    $size=(Get-Item -LiteralPath $path).Length
    if($hasContext -and $size -gt 0){$State.ExitContextOutcome='PresentUnqualified'}
    if($hasCallers -and $size -gt 0){$State.CallersOutcome='PresentUnqualified'}
    if($profile -ceq 't7-catalog-message' -and $size -gt 0){$State.MessageOutcome='PresentUnqualified'}
    Assert-T7CatalogueTraceSize $profile $size
    $pin=[pscustomobject]@{Path=$path;Bytes=$size;SHA256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
    $Context.Guards.Add((Open-H1Pin $pin));$State.TraceReport=$pin
    $text=[Text.UTF8Encoding]::new($false,$true).GetString([IO.File]::ReadAllBytes($path))
    $result=switch($profile){
        't7-catalog-message'{ConvertFrom-T7CatalogueMessage $text}
        't7-catalog-callers'{ConvertFrom-T7CatalogueCallers $text}
        't7-catalog-exit-context'{ConvertFrom-T7CatalogueExitContext $text}
        default{ConvertFrom-T7CatalogueTrace $text}
    }
    $State.TraceOutcome=$result.Outcome;$State.TraceEvents=$result.Events
    if($hasContext){$State.ExitContextOutcome=$result.ContextOutcome;$State.ExitContext=$result.Context}
    if($hasCallers){$State.CallersOutcome=$result.CallersOutcome;$State.Callers=$result.Callers}
    if($profile -ceq 't7-catalog-message'){$State.MessageOutcome=$result.MessageOutcome;$State.Message=$result.Message}
}
function Assert-T7CatalogueTraceSize([string]$Profile,[long]$Bytes) {
    if(($Profile -ceq 't7-catalog-trace' -and $Bytes -ge 1536) -or
       ($Profile -ceq 't7-catalog-exit-context' -and $Bytes -gt 4096) -or
       ($Profile -cin @('t7-catalog-callers','t7-catalog-message') -and $Bytes -gt 8192)){throw 'Trace stderr cap exceeded.'}
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
function Assert-T7CatalogueCallerWindow($Row) {
    $base=0x140000000L;$ra=[Convert]::ToUInt64($Row.ReturnAddress,16)
    $start=[Convert]::ToUInt64($Row.Start,16);$region=[Convert]::ToUInt64($Row.Region,16)
    $begin=[decimal]$base+$Row.Begin;$end=[decimal]$base+$Row.End
    $regionEnd=[decimal]$region+$Row.RegionSize
    if($Row.RecordReadBytes -ne 12 -or [Convert]::ToUInt64($Row.Record,16) -eq 0 -or
       [Convert]::ToUInt64($Row.Module,16) -ne $base -or [Convert]::ToUInt64($Row.Image,16) -ne $base -or
       [Convert]::ToUInt64($Row.Allocation,16) -ne $base -or $Row.Begin -ge $Row.End -or
       ([decimal]$ra-1) -lt $begin -or ([decimal]$ra-1) -ge $end -or
       $Row.State -ne 0x1000 -or ($Row.Protect -band 0x100) -ne 0 -or
       ($Row.Protect -band 0xFF) -in @(0,1) -or $regionEnd -gt [decimal][ulong]::MaxValue -or
       ([decimal]$ra-1) -lt $region -or ([decimal]$ra-1) -ge $regionEnd){throw 'Caller code window lacks a qualified function or readable region.'}
    if($end-$begin -le 512 -and $begin -ge $region -and $end -le $regionEnd) {
        $expectedStart=$begin;$expectedEnd=$end;$scope='full'
    }else {
        $expectedStart=[Math]::Max([Math]::Max(([decimal]$ra-448),$begin),[decimal]$region)
        $expectedEnd=[Math]::Min([Math]::Min(([decimal]$ra+64),$end),$regionEnd);$scope='window'
    }
    if($expectedStart -gt ([decimal]$ra-1) -or $expectedEnd -le ([decimal]$ra-1) -or
       $expectedEnd-$expectedStart -gt 512 -or $start -ne $expectedStart -or
       $Row.Requested -ne $expectedEnd-$expectedStart -or $Row.Scope -cne $scope){throw 'Caller code window differs from the exact bounded intersection.'}
}
function ConvertFrom-T7CatalogueCallerLine([string]$Line) {
    $dec='(0|[1-9][0-9]{0,19})';$ptr='[0-9A-F]{16}'
    $pattern='\A\[T7_CATALOG_CALLER\] schema=iw7\.t7-catalog-callers/1 code=(?<code>0|-?[1-9][0-9]{0,9}) tid=(?<tid>'+$dec+') exit_ra=(?<exit_ra>'+$ptr+') index=(?<index>[0-2]) ra=(?<ra>'+$ptr+') '+
        'status=(?<status>ok|absent|stack_unavailable|module_missing|module_mismatch|query_failed|region_invalid|not_found|record_partial|record_read_failed|record_invalid|partial|read_failed|exception) frame=(?<frame>-1|[0-7]) '+
        'module=(?<module>'+$ptr+') image=(?<image>'+$ptr+') record=(?<record>'+$ptr+') record_read=(?<record_read>'+$dec+') '+
        'begin=(?<begin>[0-9A-F]{8}) end=(?<end>[0-9A-F]{8}) unwind=(?<unwind>[0-9A-F]{8}) start=(?<start>'+$ptr+') requested=(?<requested>'+$dec+') read=(?<read>'+$dec+') '+
        'scope=(?<scope>none|full|window) allocation=(?<allocation>'+$ptr+') region=(?<region>'+$ptr+') region_size=(?<region_size>'+$dec+') '+
        'state=(?<state>'+$dec+') protect=(?<protect>'+$dec+') type=(?<type>'+$dec+') error=(?<error>'+$dec+') data=(?<data>-|[0-9A-F]+)\z'
    $m=[regex]::Match($Line,$pattern)
    if(!$m.Success){throw 'Unknown caller record or field format.'}
    $code=[long]$m.Groups['code'].Value
    if($code -lt [int]::MinValue -or $code -gt [int]::MaxValue){throw 'Caller code exceeds int32.'}
    $row=[ordered]@{Code=$code;ThreadId=(Get-T7CatalogueContextNumber $m 'tid');ExitReturnAddress=$m.Groups['exit_ra'].Value;
        Index=[int]$m.Groups['index'].Value;ReturnAddress=$m.Groups['ra'].Value;Status=$m.Groups['status'].Value;
        Frame=[int]$m.Groups['frame'].Value;RecordReadBytes=(Get-T7CatalogueContextNumber $m 'record_read' 12);
        Requested=(Get-T7CatalogueContextNumber $m 'requested' 512);ReadBytes=(Get-T7CatalogueContextNumber $m 'read' 512);
        Scope=$m.Groups['scope'].Value;RegionSize=(Get-T7CatalogueContextNumber $m 'region_size' ([ulong]::MaxValue));DataHex=$m.Groups['data'].Value}
    foreach($field in 'module','image','record','start','allocation','region'){$row[$field]=$m.Groups[$field].Value}
    foreach($field in 'begin','end','unwind'){$row[$field]=[Convert]::ToUInt32($m.Groups[$field].Value,16)}
    foreach($field in 'state','protect','type','error'){$row[$field]=Get-T7CatalogueContextNumber $m $field}
    if($row.ReturnAddress -cne @('0000000140584FD8','00000001401DA015','0000000140526D02')[$row.Index]){throw 'Caller index/target differs.'}
    if($row.ReadBytes -gt $row.Requested -or ($row.ReadBytes -eq 0 -and $row.DataHex -cne '-') -or
       ($row.ReadBytes -gt 0 -and ($row.DataHex -ceq '-' -or $row.DataHex.Length -ne 2*$row.ReadBytes))){throw 'Caller data/read bounds differ.'}
    $hasRvas=$row.begin -ne 0 -or $row.end -ne 0 -or $row.unwind -ne 0
    if(($row.RecordReadBytes -ne 12 -and $hasRvas) -or
       ($row.Status -cnotin @('ok','partial','read_failed','record_invalid','region_invalid') -and $hasRvas)){throw 'Failed or incomplete caller function copy exposes RVAs.'}
    if(($row.Status -ceq 'record_partial' -and $row.RecordReadBytes -notin (1..11)) -or
       ($row.Status -cin @('record_read_failed','record_invalid','region_invalid') -and $row.RecordReadBytes -notin @(0,12)) -or
       ($row.Status -cin @('absent','stack_unavailable','module_missing','module_mismatch','query_failed','not_found') -and $row.RecordReadBytes -ne 0)){throw 'Caller function status/read differs.'}
    if($row.Requested -eq 0) {
        if($row.start -cne '0000000000000000' -or $row.Scope -cne 'none' -or $row.ReadBytes -ne 0){throw 'Caller without a code request has a window.'}
    }elseif($row.start -ceq '0000000000000000' -or $row.Scope -ceq 'none' -or
        $row.Status -cnotin @('ok','partial','read_failed','exception')){throw 'Caller pre-read refusal exposes a code request.'}
    if(($row.Status -ceq 'ok' -and ($row.Requested -eq 0 -or $row.ReadBytes -ne $row.Requested -or $row.error -ne 0)) -or
       ($row.Status -ceq 'partial' -and ($row.ReadBytes -eq 0 -or $row.ReadBytes -ge $row.Requested)) -or
       ($row.Status -ceq 'read_failed' -and $row.ReadBytes -notin @(0,$row.Requested)) -or
       ($row.Status -ceq 'read_failed' -and $row.Requested -eq 0 -and $row.error -ne 13)){throw 'Caller code status/read differs.'}
    if($row.Status -cin @('absent','stack_unavailable')) {
        if($row.Frame -ne -1 -or $row.RecordReadBytes -ne 0 -or $row.Requested -ne 0 -or $row.error -ne 0 -or
           $row.RegionSize -ne 0 -or $row.state -ne 0 -or $row.protect -ne 0 -or $row.type -ne 0){throw 'Uncaptured caller exposes lookup/read metadata.'}
        foreach($field in 'module','image','record','allocation','region'){if($row[$field] -cne '0000000000000000'){throw 'Uncaptured caller exposes an address.'}}
    }
    # Exceptions preserve bounded diagnostic metadata but zero the record RVAs.
    # A serializer clamp is explicit read_failed/error 13, never Observed.
    if($row.Requested -gt 0 -and $row.Status -cne 'exception'){Assert-T7CatalogueCallerWindow ([pscustomobject]$row)}
    [pscustomobject]$row
}
function ConvertFrom-T7CatalogueCallers([string]$Text) {
    Assert-T7CatalogueTraceSize 't7-catalog-callers' ([Text.Encoding]::UTF8.GetByteCount($Text))
    if($Text -cmatch '[^\x20-\x7e\r\n]'){throw 'Caller stderr must be ASCII without BOM.'}
    $complete=$Text.EndsWith("`n")
    $lines=@(if($Text.Length){if($complete){$Text.Substring(0,$Text.Length-1).Split("`n")}else{$Text.Split("`n")}})
    if($lines.Count -gt 12){throw 'Caller stderr exceeds twelve lines.'}
    $prefix='[T7_CATALOG_CALLER] schema=iw7.t7-catalog-callers/1 '
    $legacy=[Text.StringBuilder]::new();$captures=[Collections.Generic.List[object]]::new()
    $started=$false;$incomplete=$false
    for($i=0;$i -lt $lines.Count;$i++) {
        $raw=$lines[$i];$line=$raw -creplace '\r$','';$lastIncomplete=!$complete -and $i -eq $lines.Count-1
        $isCaller=$line.StartsWith('[T7_CATALOG_CALLER]',[StringComparison]::Ordinal)
        # Recognizable truncated caller prefix is preserved only after three EXIT records.
        $isPartial=$lastIncomplete -and $line.Length -gt 0 -and
            ($prefix.StartsWith($line,[StringComparison]::Ordinal) -or $line.StartsWith($prefix,[StringComparison]::Ordinal))
        if(!$started -and ($isCaller -or $isPartial)) {
            $context=ConvertFrom-T7CatalogueExitContext $legacy.ToString()
            if($context.Context.Captures.Count -eq 3 -and !$context.Context.IncompleteTrailingLine){$started=$true}
            elseif($isCaller){throw 'Caller records require all three preceding EXIT records.'}
            # A shorter ambiguous prefix may still be a truncated legacy EXIT.
            # Let the unchanged legacy reader qualify it at its current stage.
        }
        if(!$started){[void]$legacy.Append($raw);if(!$lastIncomplete){[void]$legacy.Append("`n")};continue}
        if($captures.Count -ge 3 -or $raw.Length+$(if($lastIncomplete){0}else{1}) -gt 2048){throw 'Caller count or line cap exceeded.'}
        if($lastIncomplete) {
            if(!$isPartial){throw 'Unrecognized incomplete caller line.'}
            # Do not accept a visibly duplicated/reordered target even when cut off.
            $index=[regex]::Match($line,' index=([0-9]+)(?: |$)')
            if($index.Success -and $index.Groups[1].Value -cne [string]$captures.Count){throw 'Incomplete caller index is duplicated or reordered.'}
            $incomplete=$true;continue
        }
        if(!$isCaller){throw 'Non-caller record follows caller diagnostics.'}
        $row=ConvertFrom-T7CatalogueCallerLine $line
        if($row.Index -ne $captures.Count){throw 'Caller records are duplicated or reordered.'}
        $captures.Add($row)
    }
    if(!$started){$context=ConvertFrom-T7CatalogueExitContext $legacy.ToString()}
    if($started) {
        $exit=@($context.Events|Where-Object Phase -CEQ 'exit_hook')[0]
        $stack=@($context.Context.Captures|Where-Object Kind -CEQ 'stack')[0]
        foreach($row in $captures) {
            if($row.Code -ne $exit.Code -or $row.ThreadId -ne $exit.ThreadId -or $row.ExitReturnAddress -ine $exit.ReturnAddress){throw 'Caller correlation differs from exit_hook.'}
            $frame=if($stack.Status -ceq 'ok'){[array]::IndexOf($stack.Addresses,$row.ReturnAddress)}else{-1}
            if($row.Frame -ne $frame){throw 'Caller frame is not the first matching stack occurrence.'}
            if(($stack.Status -cne 'ok' -and $row.Status -cne 'stack_unavailable') -or
               ($stack.Status -ceq 'ok' -and $frame -lt 0 -and $row.Status -cne 'absent') -or
               ($frame -ge 0 -and $row.Status -cin @('absent','stack_unavailable'))){throw 'Caller presence/status differs from the captured stack.'}
        }
    }
    $outcome=if(!$captures.Count -and !$incomplete){'Absent'}elseif($captures.Count -eq 3 -and !$incomplete -and !@($captures|Where-Object Status -CNE 'ok').Count){'Observed'}else{'Partial'}
    [pscustomobject]@{Outcome=$context.Outcome;Events=$context.Events;ContextOutcome=$context.ContextOutcome;Context=$context.Context;
        CallersOutcome=$outcome;Callers=[ordered]@{Captures=@($captures.ToArray());IncompleteTrailingLine=$incomplete}}
}
function ConvertFrom-T7CatalogueMessageLine([string]$Line) {
    $dec='(0|[1-9][0-9]{0,9})';$count='(0|[1-9][0-9]{0,2})'
    $head='\A\[T7_CATALOG_MSG\] schema=iw7\.t7-catalog-message/1 kind=(?<kind>install|buffer) tid=(?<tid>'+$dec+') status='
    $install='(?<status>installed|module_missing|module_mismatch|query_failed|region_invalid|read_failed|signature_mismatch|call_mismatch|wrapper_far|compare_mismatch|rolled_back|rollback_failed|exception) error=(?<error>'+$dec+')\z'
    $buffer='(?<status>ok|prefix|partial|argument_invalid|stack_invalid|query_failed|region_invalid|read_failed|exception) '+
        'requested=(?<requested>'+$count+') read=(?<read>'+$count+') length=(?<length>'+$count+') nul=(?<nul>[01]) error=(?<error>'+$dec+') data=(?<data>-|[0-9A-F]+)\z'
    $m=[regex]::Match($Line,$head+$install)
    if(!$m.Success -or $m.Groups['kind'].Value -cne 'install') {
        $m=[regex]::Match($Line,$head+$buffer)
        if(!$m.Success -or $m.Groups['kind'].Value -cne 'buffer'){throw 'Unknown message record or field format.'}
    }
    $row=[ordered]@{Kind=$m.Groups['kind'].Value;ThreadId=(Get-T7CatalogueContextNumber $m 'tid');
        Status=$m.Groups['status'].Value;Error=(Get-T7CatalogueContextNumber $m 'error')}
    if($row.Kind -ceq 'install') {
        if($row.Status -ceq 'installed' -and $row.Error -ne 0){throw 'Successful message installation has an error.'}
        return [pscustomobject]$row
    }
    $row.Requested=Get-T7CatalogueContextNumber $m 'requested' 384
    $row.ReadBytes=Get-T7CatalogueContextNumber $m 'read' 384
    $row.Length=Get-T7CatalogueContextNumber $m 'length' 384
    $row.NulTerminated=$m.Groups['nul'].Value -ceq '1';$row.DataHex=$m.Groups['data'].Value
    if($row.ReadBytes -gt $row.Requested -or $row.Length -gt $row.ReadBytes -or
       ($row.NulTerminated -and $row.Length -ge $row.ReadBytes) -or
       (!$row.NulTerminated -and $row.Length -ne $row.ReadBytes) -or
       ($row.Length -eq 0 -and $row.DataHex -cne '-') -or
       ($row.Length -gt 0 -and ($row.DataHex -ceq '-' -or $row.DataHex.Length -ne 2*$row.Length))){throw 'Message counts, NUL or payload length differ.'}
    # The terminator is excluded by the producer. Keep bytes private and opaque;
    # checking aligned zero bytes does not assume a text encoding.
    if($row.Length -gt 0){for($i=0;$i -lt $row.DataHex.Length;$i+=2){if($row.DataHex.Substring($i,2) -ceq '00'){throw 'Message payload includes a NUL or bytes after it.'}}}
    switch($row.Status) {
        ok {if($row.Requested -eq 0 -or $row.ReadBytes -ne $row.Requested -or !$row.NulTerminated -or $row.Error -ne 0){throw 'Complete message capture has inconsistent status.'}}
        prefix {if($row.Requested -eq 0 -or $row.ReadBytes -ne $row.Requested -or $row.NulTerminated -or $row.Error -ne 0){throw 'Message prefix has inconsistent status.'}}
        partial {if($row.ReadBytes -eq 0 -or $row.ReadBytes -ge $row.Requested){throw 'Partial message capture has inconsistent counts.'}}
        read_failed {
            if($row.ReadBytes -notin @(0,$row.Requested) -or ($row.Requested -eq 0 -and $row.Error -ne 13)){throw 'Failed message copy differs from the bounded RPM/clamp contract.'}
        }
        exception {} # Bounded counts already checked; a NUL never upgrades SEH.
        default {if($row.Requested -ne 0 -or $row.ReadBytes -ne 0 -or $row.Length -ne 0 -or $row.NulTerminated){throw 'Message pre-read refusal exposes a copy.'}}
    }
    [pscustomobject]$row
}
function ConvertFrom-T7CatalogueMessage([string]$Text) {
    Assert-T7CatalogueTraceSize 't7-catalog-message' ([Text.Encoding]::UTF8.GetByteCount($Text))
    if($Text -cmatch '[^\x20-\x7e\r\n]'){throw 'Message stderr must be ASCII without BOM.'}
    $complete=$Text.EndsWith("`n")
    $lines=@(if($Text.Length){if($complete){$Text.Substring(0,$Text.Length-1).Split("`n")}else{$Text.Split("`n")}})
    if($lines.Count -gt 14){throw 'Message stderr exceeds fourteen lines.'}
    $prefix='[T7_CATALOG_MSG] schema=iw7.t7-catalog-message/1 kind='
    $legacy=[Text.StringBuilder]::new();$captures=[Collections.Generic.List[object]]::new()
    $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $positions=@{};$tracePositions=@{};$incomplete=$false
    for($i=0;$i -lt $lines.Count;$i++) {
        $raw=$lines[$i];$line=$raw -creplace '\r$','';$lastIncomplete=!$complete -and $i -eq $lines.Count-1
        $isMessage=$line.StartsWith('[T7_CATALOG_MSG]',[StringComparison]::Ordinal)
        $couldBeMessage=$lastIncomplete -and $line.Length -gt 0 -and
            ($prefix.StartsWith($line,[StringComparison]::Ordinal) -or $line.StartsWith($prefix,[StringComparison]::Ordinal))
        if($couldBeMessage -and !$isMessage) {
            # An ambiguous short prefix can still belong to EXIT/CALLER /1.
            $legacyAccepts=$false
            try{$null=ConvertFrom-T7CatalogueCallers ($legacy.ToString()+$raw);$legacyAccepts=$true}catch{}
            if($legacyAccepts){$couldBeMessage=$false}
        }
        if($lastIncomplete -and ($isMessage -or $couldBeMessage)) {
            if(!$couldBeMessage -or $captures.Count -ge 2 -or $raw.Length -gt 1024){throw 'Unrecognized or excess incomplete message record.'}
            if($line.StartsWith($prefix,[StringComparison]::Ordinal)) {
                $kind=($line.Substring($prefix.Length) -split ' ',2)[0]
                $possible=@('install','buffer'|Where-Object {$_.StartsWith($kind,[StringComparison]::Ordinal)})
                if(!$possible.Count){throw 'Unknown incomplete message kind.'}
                if($kind -cin @('install','buffer')) {
                    $cap=if($kind -ceq 'install'){256}else{1024}
                    if($seen.Contains($kind) -or $raw.Length -gt $cap){throw 'Duplicate or oversized incomplete message record.'}
                    if($kind -ceq 'buffer' -and (!$seen.Contains('install') -or $captures[0].Status -cne 'installed')){throw 'Incomplete message buffer requires a preceding successful installation.'}
                }
            }
            $incomplete=$true;continue
        }
        if($isMessage) {
            $row=ConvertFrom-T7CatalogueMessageLine $line
            $cap=if($row.Kind -ceq 'install'){256}else{1024}
            if(!$seen.Add($row.Kind) -or $raw.Length+1 -gt $cap){throw 'Message one-shot or line cap differs.'}
            $positions[$row.Kind]=$i;$captures.Add($row);continue
        }
        [void]$legacy.Append($raw);if(!$lastIncomplete){[void]$legacy.Append("`n")}
        $phase=[regex]::Match($line,'\A\[T7_CATALOG_TRACE\] .* phase=(before_post_unpack|after_post_unpack|exit_hook) ')
        if($phase.Success){$tracePositions[$phase.Groups[1].Value]=$i}
    }
    $previous=ConvertFrom-T7CatalogueCallers $legacy.ToString()
    $installation=@($captures|Where-Object Kind -CEQ 'install');$buffer=@($captures|Where-Object Kind -CEQ 'buffer')
    $installBoundaryObserved=$false;$correlated=$false;$correlation='NoBuffer'
    if($installation.Count) {
        if(!$tracePositions.ContainsKey('before_post_unpack')){throw 'Message installation lacks before_post_unpack.'}
        if($positions.install -le $tracePositions.before_post_unpack){throw 'Message installation precedes before_post_unpack.'}
        $installBoundaryObserved=$true
        if($tracePositions.ContainsKey('after_post_unpack') -and $positions.install -ge $tracePositions.after_post_unpack){throw 'Message installation follows after_post_unpack.'}
    }
    if($buffer.Count) {
        if($installation.Count -ne 1 -or $installation[0].Status -cne 'installed' -or $positions.buffer -le $positions.install){throw 'Message buffer requires a preceding successful installation.'}
        $exit=@($previous.Events|Where-Object Phase -CEQ 'exit_hook')
        if(!$exit.Count){$correlation='NoExitHook'}
        elseif($buffer[0].ThreadId -ne $exit[0].ThreadId){$correlation='DifferentThread'}
        elseif($positions.buffer -ge $tracePositions.exit_hook){throw 'Message buffer follows exit_hook on its own thread.'}
        else{$correlated=$true;$correlation='SameThreadBeforeExit'}
    }
    $outcome=if(!$captures.Count -and !$incomplete){'Absent'}elseif($incomplete -or !$buffer.Count -or !$correlated -or !$installBoundaryObserved){'Partial'}
        elseif($buffer[0].Status -ceq 'ok'){'Observed'}elseif($buffer[0].Status -ceq 'prefix'){'Prefix'}else{'Partial'}
    [pscustomobject]@{Outcome=$previous.Outcome;Events=$previous.Events;ContextOutcome=$previous.ContextOutcome;Context=$previous.Context;
        CallersOutcome=$previous.CallersOutcome;Callers=$previous.Callers;MessageOutcome=$outcome;
        Message=[ordered]@{Captures=@($captures.ToArray());IncompleteTrailingLine=$incomplete;InstallBoundaryObserved=$installBoundaryObserved;
            ExitCorrelated=$correlated;Correlation=$correlation}}
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

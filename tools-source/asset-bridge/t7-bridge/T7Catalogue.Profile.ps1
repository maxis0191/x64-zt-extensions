# Fixed catalogue adapter. Ownership, pin readers and closure stay in H1Native.Core.
function Get-T7CatalogueCandidateProfile($Plan) {
    if(!$Plan.PSObject.Properties['CandidateProfile']){return 'ordinary-d2'}
    if($Plan.CandidateProfile -cnotin @('ordinary-d2','t7-catalog-trace')){throw 'Unknown catalogue candidate profile.'}
    $Plan.CandidateProfile
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
    if($candidateProfile -ceq 't7-catalog-trace' -and $Plan.TraceStderrLimitBytes -ne 1536){throw 'Exact trace stderr bound required.'}
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
    $buildPin=@($Plan.Bindings|Where-Object {$_.Path -ceq $Plan.BuildPlan -and $_.IsText})
    if($buildPin.Count -ne 1 -or $buildPin[0].SHA256 -cne $Plan.ExpectedBuildPlanSHA256 -or
       $buildPin[0].Bytes -gt 1MB -or $Plan.ExpectedBuildPlanSHA256 -ceq 'daa7097f872b83a5762b2cb56bf6dd5a235ed2beee8e0ff077276c61622d53fa'){throw 'Trace requires its own guarded build plan.'}
    $build=Read-H1SmallJson $Plan.BuildPlan 1MB
    if($build.Schema -cne 'iw7.t7-minimal-build-plan/1' -or
       $build.SourceCommit -cne 'fab935826c898806855376662a8a03317b3ad8f1'){throw 'Trace build source/schema differs.'}
    $profile=$build.BuildProfile
    $fields=@('Name','Option','ArgumentCount','TraceSchema','Wiring','PreparedMain','BaseBuildPlan','BaseBuildReceipt')
    foreach($p in @($profile,$Receipt.BuildProfile)) {
        Assert-T7CatalogueFields $p $fields
        if($p.Name -cne 't7-catalog-trace' -or $p.Option -cne '-t7-iw7-catalog' -or
           ($p.ArgumentCount -isnot [long] -and $p.ArgumentCount -isnot [int]) -or $p.ArgumentCount -ne 3 -or
           $p.TraceSchema -cne 'iw7.t7-catalog-trace/1'){throw 'Exact catalogue trace profile required.'}
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
    if((Get-T7CatalogueCandidateProfile $Plan) -ceq 'ordinary-d2'){return}
    $State.TraceOutcome='NoTrace'
    $path=Join-Path $Plan.StageRoot 'stderr.log'
    if(!(Test-Path -LiteralPath $path)){return}
    $State.TraceOutcome='TracePresentUnqualified'
    Assert-H1Path $path
    $size=(Get-Item -LiteralPath $path).Length
    if($size -ge 1536){throw 'Trace stderr cap exceeded.'}
    $pin=[pscustomobject]@{Path=$path;Bytes=$size;SHA256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
    $Context.Guards.Add((Open-H1Pin $pin));$State.TraceReport=$pin
    $result=ConvertFrom-T7CatalogueTrace ([Text.UTF8Encoding]::new($false,$true).GetString([IO.File]::ReadAllBytes($path)))
    $State.TraceOutcome=$result.Outcome;$State.TraceEvents=$result.Events
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
            if($name -ceq 'stderr.log' -and (Get-T7CatalogueCandidateProfile $Plan) -ceq 't7-catalog-trace' -and
               (Test-Path -LiteralPath $path) -and (Get-Item -LiteralPath $path).Length -ge 1536){throw 'Trace stderr cap exceeded.'}
        }
        Assert-T7CatalogueEngineOutputs $Plan
        Assert-H1Deadline $script:T7CatalogueGroupStarted 200
    }
}

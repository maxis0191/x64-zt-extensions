# Functions only. Importing this file does not load native types or touch leases.
Set-StrictMode -Version Latest
function Assert-H1Path([string]$Path) {
    if(![IO.Path]::IsPathFullyQualified($Path) -or [IO.Path]::GetFullPath($Path) -cne $Path -or $Path -match '["\r\n]') {throw 'Canonical absolute path required.'}
    for($part=$Path;$part;$part=[IO.Path]::GetDirectoryName($part)) {
        if(Test-Path -LiteralPath $part) {
            if(([IO.File]::GetAttributes($part) -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Reparse ancestry refused.'}
        }
    }
}
function Open-H1Pin($Pin) {
    Assert-H1Path $Pin.Path
    if($Pin.SHA256 -cnotmatch '^[0-9a-f]{64}$' -or $Pin.Bytes -lt 0 -or $Pin.Bytes -gt 64MB){throw 'Invalid bounded binding.'}
    $guard=[IO.FileStream]::new($Pin.Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    try {
        if($guard.Length -ne $Pin.Bytes){throw 'Bound input length differs.'}
        $hash=[Security.Cryptography.SHA256]::Create()
        try {$actual=[Convert]::ToHexString($hash.ComputeHash($guard)).ToLowerInvariant()} finally {$hash.Dispose()}
        if($actual -cne $Pin.SHA256 -or $guard.Length -ne $Pin.Bytes){throw 'Bound input hash/length differs.'}
        Assert-H1Path $Pin.Path
        $guard.Position=0
        return $guard
    }catch{$guard.Dispose();throw}
}
function Read-H1SmallJson([string]$Path,[int]$Limit=128KB) {
    Assert-H1Path $Path
    $stream=[IO.FileStream]::new($Path,'Open','Read','Read')
    try {
        if($stream.Length -gt $Limit){throw 'JSON input exceeds bound.'}
        $bytes=[byte[]]::new($Limit+1);$used=0
        do {$read=$stream.Read($bytes,$used,$bytes.Length-$used);$used+=$read} while($read -gt 0 -and $used -lt $bytes.Length)
        if($used -gt $Limit){throw 'JSON input grew above bound.'}
        [Text.Encoding]::UTF8.GetString($bytes,0,$used)|ConvertFrom-Json -Depth 20
    }finally{$stream.Dispose()}
}
function Measure-H1Output([string]$Root) {
    Assert-H1Path $Root
    $pending=[Collections.Generic.Stack[string]]::new();$pending.Push($Root)
    $total=0L;$count=0
    while($pending.Count) {
        foreach($entry in [IO.Directory]::EnumerateFileSystemEntries($pending.Pop())) {
            if(++$count -gt 64){throw 'Output entry count exceeded 64.'}
            $attributes=[IO.File]::GetAttributes($entry)
            if($attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Output reparse entry refused before descent.'}
            if($attributes -band [IO.FileAttributes]::Directory){$pending.Push($entry)}
            else {$total+=([IO.FileInfo]$entry).Length}
        }
    }
    $total
}
function Get-H1Clock { [Diagnostics.Stopwatch]::GetTimestamp()/([double][Diagnostics.Stopwatch]::Frequency)*1000 }
function Assert-H1Deadline($Started,[int]$Seconds) {
    if((Get-H1Clock)-$Started -ge $Seconds*1000){throw 'Stage deadline exceeded.'}
}
function Test-H1Budget($Plan,$State) {
    $bytes=Measure-H1Output $Plan.RunRoot
    $State.MaxObservedOutputBytes=[math]::Max($State.MaxObservedOutputBytes,$bytes)
    if($bytes -gt $Plan.OutputLimitBytes-$Plan.MetadataReserveBytes){throw 'Output budget exceeded; preserve diagnostics.'}
    $snapshot=Get-IW7ResourceSnapshot
    if($snapshot.CommitLimit -le 0 -or $snapshot.Committed -gt $snapshot.CommitLimit*0.85){throw 'Commit high water exceeded.'}
}
function Register-H1Original($Lease,$Identity) {
    # Register only the original handle tuple, never adopt a PID's new occupant.
    Invoke-IW7ResourceLock {
        $registry=Read-IW7ResourceState
        $rows=@($registry.Leases|Where-Object Token -CEQ $Lease.Token)
        if($rows.Count -ne 1 -or $rows[0].Kind -cne $Lease.Kind -or $rows[0].Scope -ine $Lease.Scope){throw 'Exact stage lease missing.'}
        $matches=@(Get-IW7ResourceProcesses|Where-Object PID -EQ $Identity.PID)
        if($matches.Count -ne 1 -or !(Test-IW7ResourceIdentity $Identity $matches[0])){throw 'Original process differs from scheduler observation.'}
        $rows[0].Processes=@($matches[0]);$rows[0].Phase='Running'
        Save-IW7ResourceState $registry
    }
}
function New-H1Owner { [IW7.AnimationProbe.NativeJob]::new() }
function Invoke-H1OwnedStage($Plan,$State,$Context,$Start,[string]$ImageSHA256,[string]$StageRoot) {
    $started=Get-H1Clock;$State.StartedUtc=[datetime]::UtcNow.ToString('o')
    $Context.Closed=$false
    $Context.Owner=New-H1Owner # Keep the owner before Start can partially fail.
    $Context.Owner.Start($Start,$ImageSHA256,(Join-Path $StageRoot 'stdout.log'),(Join-Path $StageRoot 'stderr.log'))
    Assert-H1Deadline $started $State.DeadlineSeconds
    $State.Identity=[ordered]@{PID=$Context.Owner.PID;Image=$Context.Owner.Image;
        CreatedUtc=[datetime]::FromFileTimeUtc($Context.Owner.CreationFileTime).ToString('o')}
    if($State.Identity.Image -ine $Start.FileName){throw 'Original child image differs.'}
    try {Register-H1Original $Context.Lease $State.Identity;$State.Registration='Registered'}
    catch {
        $State.RegistrationError=$_.Exception.Message
        if(!$Context.Owner.TreeExited()){throw}
        $State.Registration='Original job already empty before CIM registration'
    }
    Assert-H1Deadline $started $State.DeadlineSeconds
    while($true) {
        Test-H1Budget $Plan $State
        Assert-H1Deadline $started $State.DeadlineSeconds
        $empty=$Context.Owner.TreeExited()
        Assert-H1Deadline $started $State.DeadlineSeconds
        if($empty) {
            $Context.Owner.CloseConfirmed();$Context.Closed=$Context.Owner.Closed
            $State.TreeClosureConfirmed=$Context.Closed;$State.ExitCode=$Context.Owner.ExitCode
            Assert-H1Deadline $started $State.DeadlineSeconds
            $State.ElapsedMs=(Get-H1Clock)-$started
            if(!$Context.Closed -or $State.ExitCode -ne 0){throw 'Original stage process failed.'}
            return
        }
        if(Test-Path -LiteralPath (Join-Path $Plan.RunRoot 'stop.request')){throw 'Coordinator stop requested.'}
        Start-Sleep -Milliseconds 100
        Assert-H1Deadline $started $State.DeadlineSeconds
    }
}
function Complete-H1Stage($Context,$State) {
    if(!$Context.Closed) {
        try {
            if(!$Context.Owner){throw 'Owner unavailable after creation attempt; closure unknown.'}
            $State.TerminationRequested=$true
            $Context.Owner.StopAndConfirm(5000)
            $Context.Closed=$Context.Owner.Closed
            if(!$Context.Closed){throw 'Original job closure unconfirmed.'}
        }catch{$State.CleanupError=$_.Exception.Message}
    }
    $State.TreeClosureConfirmed=$Context.Closed
    if($Context.Owner -and $Context.Closed){$State.ExitCode=$Context.Owner.ExitCode}
    if($Context.Closed -and $Context.Lease) {
        try {Exit-IW7ResourceLease -Token $Context.Lease.Token;$Context.Lease=$null;$State.LeaseReleased=$true}
        catch {$State.CleanupError=$_.Exception.Message}
    }
    if(!$Context.Closed -or $Context.Lease) {
        $State.Status='Quarantined';$State.Quarantined=$true
        [AppDomain]::CurrentDomain.SetData(('IW7.H1.Quarantine.'+$State.LeaseToken),$Context)
    }
}
function Write-H1Receipt($Plan,$State,[string]$StageRoot) {
    $total=Measure-H1Output $Plan.RunRoot
    $State.OutputBytesBeforeReceipt=$total
    $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($State|ConvertTo-Json -Depth 16)+"`n")
    if($bytes.Length -gt $Plan.MetadataReserveBytes -or $total+$bytes.Length -gt $Plan.OutputLimitBytes){throw 'Final receipt exceeds reserved output budget.'}
    $pending=Join-Path $StageRoot 'receipt.pending.json';$final=Join-Path $StageRoot 'receipt.json'
    $stream=[IO.FileStream]::new($pending,'CreateNew','Write','Read')
    try {$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
    if((Measure-H1Output $Plan.RunRoot) -gt $Plan.OutputLimitBytes){throw 'Output changed before receipt publication.'}
    [IO.File]::Move($pending,$final) # No replacement; success is never published early.
}
function Assert-H1Observation($Report) {
    if($Report.schema -cne 'iw7.h1-parser-converter-observation/1' -or $Report.checks -lt 1 -or
       $Report.vertices_checked -ne 24 -or $Report.bone_name_observed -cne 'tag_origin' -or
       $Report.material_reference -cne 'paris_h1_original_material'){throw 'Native observation identity differs.'}
    foreach($name in 'production_parsers_executed','production_converters_executed','declaration_adapter') {
        if($Report.$name -isnot [bool] -or !$Report.$name){throw 'Native method observation missing.'}
    }
    foreach($name in 'whole_zonetool_application','bone_engine_token_resolved','material_complete','lod_named_reference_linked',
        'dump_executed','ff_built','render_verified','retail_h1_compatibility') {
        if($Report.$name -isnot [bool] -or $Report.$name){throw 'Native observation overclaims its scope.'}
    }
}

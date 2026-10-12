# Read-only observation helpers. Importing does not inspect or launch a process.
function Assert-RecipientLightIdentity($Plan,$Phase,$Locator,$Parent,$Child,$ExpectedNative) {
    if(!$Parent -or !$Child -or $Plan.Phases.Count -ne 1 -or $Plan.Phases[0] -cne 'references' -or
       $Phase.Phase -cne 'references' -or $Locator.phase -cne 'references' -or
       $Locator.executable_sha256 -cne $Plan.Candidate.SHA256 -or
       $Plan.Candidate.SHA256 -cne 'e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04'){
        throw 'Exact references-only parent/child observation required.'
    }
    $image=Join-Path $Plan.Work 'zonetool.exe'
    foreach($pair in @(@($Phase.Image,$Plan.PythonExe),@($Parent.Image,$Plan.PythonExe),@($Locator.image,$image),@($Child.Image,$image))){
        if(!$pair[0] -or ![IO.Path]::IsPathFullyQualified($pair[0]) -or
           [IO.Path]::GetFullPath($pair[0]) -ine [IO.Path]::GetFullPath($pair[1])){throw 'Observed process image differs.'}
    }
    if($Phase.PID -lt 1 -or $Locator.pid -lt 1 -or $Parent.PID -ne $Phase.PID -or
       $Locator.parent_pid -ne $Phase.PID -or $Child.ParentPID -ne $Phase.PID -or $Child.PID -ne $Locator.pid){throw 'Original parent/child relationship differs.'}
    foreach($stamp in @($Phase.CreatedUtc,$Parent.CreatedUtc,$Child.CreatedUtc,$Locator.spawn_observed_utc)){
        if(!$stamp){throw 'Real creation and locator times required.'}
    }
    # CIM is microsecond-resolution; original handles can retain 100ns ticks.
    if([math]::Abs((([datetimeoffset]$Phase.CreatedUtc)-([datetimeoffset]$Parent.CreatedUtc)).Ticks) -gt 10 -or
       ([datetimeoffset]$Child.CreatedUtc) -lt ([datetimeoffset]$Parent.CreatedUtc) -or
       ([datetimeoffset]$Child.CreatedUtc) -gt ([datetimeoffset]$Locator.spawn_observed_utc)){
        throw 'Observed process creation differs from original relationship.'
    }
    if($ExpectedNative -and ($ExpectedNative.PID -ne $Child.PID -or $ExpectedNative.Image -ine $Child.Image -or
       ([datetimeoffset]$ExpectedNative.CreatedUtc).Ticks -ne ([datetimeoffset]$Child.CreatedUtc).Ticks)){
        throw 'Previously bound native identity changed; no replacement adoption.'
    }
}
function Read-RecipientLightProcess([int]$ProcessId) {
    $item=Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -OperationTimeoutSec 2 -ErrorAction Stop
    if(!$item -or !$item.CreationDate -or !$item.ExecutablePath){throw 'Process identity unavailable.'}
    [pscustomobject]@{PID=[int]$item.ProcessId;ParentPID=[int]$item.ParentProcessId;Image=$item.ExecutablePath;
        CreatedUtc=$item.CreationDate.ToUniversalTime().ToString('o');
        ReadOperations=$item.ReadOperationCount;WriteOperations=$item.WriteOperationCount;
        ReadBytes=$item.ReadTransferCount;WriteBytes=$item.WriteTransferCount}
}
function Get-RecipientLightObservation($Plan,$Phase,$Locator,$ExpectedNative) {
    $parent=Read-RecipientLightProcess $Phase.PID
    $child=Read-RecipientLightProcess $Locator.pid
    Assert-RecipientLightIdentity $Plan $Phase $Locator $parent $child $ExpectedNative
    if((Get-FileHash -LiteralPath $child.Image -Algorithm SHA256).Hash -ine $Plan.Candidate.SHA256){throw 'Observed E7 image hash differs.'}
    $process=Get-Process -Id $child.PID -ErrorAction Stop
    try {
        # Hold this process's handle throughout sampling; do not adopt a new PID.
        $null=$process.Handle
        if($process.HasExited -or [math]::Abs(($process.StartTime.ToUniversalTime()-([datetimeoffset]$child.CreatedUtc).UtcDateTime).Ticks) -gt 10){throw 'Native identity changed before observation.'}
        $threads=@($process.Threads)
        $rows=@(foreach($thread in @($threads|Select-Object -First 256)){
            try {
                $state=$thread.ThreadState
                [ordered]@{Id=$thread.Id;State=$state.ToString();WaitReason=$(if($state -eq [Diagnostics.ThreadState]::Wait){$thread.WaitReason.ToString()}else{$null});
                    CpuSeconds=$thread.TotalProcessorTime.TotalSeconds;Unavailable=$null}
            }catch{[ordered]@{Id=$null;State=$null;WaitReason=$null;CpuSeconds=$null;Unavailable=$_.Exception.GetType().FullName}}
        })
        $window=@{Handle=$null;Title=$null;Unavailable=$null;AllWindowsEnumerated=$false}
        try{$window.Handle=$process.MainWindowHandle.ToInt64();$window.Title=$process.MainWindowTitle.Substring(0,[math]::Min(256,$process.MainWindowTitle.Length))}
        catch{$window.Unavailable=$_.Exception.GetType().FullName}
        $result=[ordered]@{Schema='iw7.recipient-light-observation/1';Utc=[datetime]::UtcNow.ToString('o');Identity=$child;
            NativeAgeSeconds=([datetime]::UtcNow-([datetimeoffset]$child.CreatedUtc).UtcDateTime).TotalSeconds;
            CpuSeconds=$process.TotalProcessorTime.TotalSeconds;WorkingSet=$process.WorkingSet64;PrivateBytes=$process.PrivateMemorySize64;
            Threads=$rows;ThreadCount=$threads.Count;ThreadsTruncated=($threads.Count -gt 256);MainWindow=$window;
            OriginalParent=$parent;DirectJobMembershipQueried=$false;SnapshotTaken=$false;DebuggerAttached=$false}
        $afterParent=Read-RecipientLightProcess $Phase.PID
        $afterChild=Read-RecipientLightProcess $Locator.pid
        Assert-RecipientLightIdentity $Plan $Phase $Locator $afterParent $afterChild $child
        if($process.HasExited){throw 'Native exited during observation; sample unavailable.'}
        $result
    }finally{$process.Dispose()}
}

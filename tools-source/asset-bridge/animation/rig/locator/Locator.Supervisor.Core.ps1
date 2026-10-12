# Locator-only lifecycle. Import performs no native load, lease or process action.
function Get-LocatorClock {[Environment]::TickCount64}
function Assert-LocatorDeadline([long]$Started,[long]$Limit=60000) {
    if((Get-LocatorClock)-$Started -ge $Limit){throw 'Locator original-process deadline exceeded.'}
}
function Assert-LocatorPath([string]$Path) {
    if(![IO.Path]::IsPathFullyQualified($Path) -or $Path -match '["\r\n]' -or [IO.Path]::GetFullPath($Path) -cne $Path){throw 'Canonical absolute locator path required.'}
    $current=$Path
    while($current){
        if(Test-Path -LiteralPath $current){
            if((Get-Item -LiteralPath $current -Force).Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)){throw 'Locator reparse path refused.'}
        }
        $parent=Split-Path $current -Parent;if($parent -eq $current){break};$current=$parent
    }
}
function Get-LocatorProviders([string]$Root) {
    $pins=[ordered]@{
        'ops/Resource-Scheduler.Core.ps1'='0d0ebef0f434c4e1ecc2614a4061f7e0685988adefcae596ff5a7891b1f3e25b'
        'ops/Resource-Memory.ps1'='6a708d2e7fa9803628bfbf5c670068d63d22a2d2cfc157994afa82d56ac9c241'
        'ops/native/ResourceMemory.cs'='b159804d12ca504cd592f4cdee191a9b68353e9e0117f9045a28a522b25692e9'
        'ops/Resource-RecorderOwnedProcess.Core.ps1'='23d6f589a6f973f6d9c56a2ff3dcb66c4df6a0aa9fe0a7125048dd9061f93c54'
        'ops/hud-lab/HudFileIdentity.cs'='61255ad8bbb6b4e2437291d3083811a56c1217ab68484bb1f22a4d5148616dbd'
    }
    foreach($key in $pins.Keys){[pscustomobject]@{Path=Join-Path $Root $key;SHA256=$pins[$key]}}
}
function Assert-LocatorPin($Pin,[switch]$MetadataOnly) {
    Assert-LocatorPath $Pin.Path;$file=Get-Item -LiteralPath $Pin.Path
    if($file.PSIsContainer -or $file.Length -le 0 -or $file.Length -gt 32MB -or $Pin.SHA256 -cnotmatch '^[a-f0-9]{64}$'){throw 'Bounded locator pin required.'}
    if($Pin.PSObject.Properties['Bytes'] -and $file.Length -ne $Pin.Bytes){throw 'Locator pinned byte count differs.'}
    if(!$MetadataOnly -and (Get-FileHash -LiteralPath $Pin.Path).Hash -ine $Pin.SHA256){throw 'Locator source pin differs.'}
}
function Add-LocatorGuard($Pin,$Context) {
    Assert-LocatorPath $Pin.Path
    $stream=[IO.File]::Open($Pin.Path,'Open','Read','Read');$Context.Guards.Add($stream)
    Assert-LocatorPin $Pin
    $file=Get-Item -LiteralPath $Pin.Path
    $Context.Baselines.Add([pscustomobject]@{Path=$Pin.Path;SHA256=$Pin.SHA256;Bytes=$file.Length;
        ModifiedUtc=$file.LastWriteTimeUtc.ToString('o');Attributes=[int]$file.Attributes;FileId=$null})
}
function Set-LocatorGuardIds($Context) {
    foreach($item in $Context.Baselines){
        $id=[IW7HudFileIdentity]::Read($item.Path)
        if($item.FileId -and $item.FileId -cne $id){throw 'Locator guarded file identity changed.'}
        $item.FileId=$id
    }
}
function Assert-LocatorGuards($Context) {
    foreach($item in $Context.Baselines){
        Assert-LocatorPath $item.Path;$file=Get-Item -LiteralPath $item.Path
        if(!$item.FileId -or [IW7HudFileIdentity]::Read($item.Path) -cne $item.FileId -or $file.Length -ne $item.Bytes -or
           $file.LastWriteTimeUtc.ToString('o') -cne $item.ModifiedUtc -or [int]$file.Attributes -ne $item.Attributes -or
           (Get-FileHash -LiteralPath $item.Path).Hash -ine $item.SHA256){throw 'Locator final guarded source proof failed.'}
    }
}
function Get-LocatorArguments($Plan) {
    $arguments=@('-I','-B','-X',('pycache_prefix='+(Join-Path $Plan.RunRoot 'unused-pycache')),$Plan.Script,
        '--text',$Plan.References.text.Path,'--rdata',$Plan.References.rdata.Path,'--pdata',$Plan.References.pdata.Path,
        '--output',(Join-Path $Plan.RunRoot 'report.local.json'),'--max-output-bytes','3145728')
    if($Plan.Schema -ceq 'iw7.rig-locator-supervisor-plan/2'){
        Assert-LocatorTargetedPlan $Plan;$arguments+=@('--entry',$Plan.Entry)
    }
    foreach($argument in $arguments){if($argument -match '["\r\n]' -or $argument.EndsWith('\')){throw 'Unsafe locator argument.'}}
    ($arguments|ForEach-Object {'"'+$_+'"'}) -join ' '
}
function Get-LocatorTargetedLimits {
    [ordered]@{root_entries=1;fragments=8;fragment_bytes=16384;decoded_bytes=32768;instructions=8192;
        control_edges=512;seconds=10;text_scans=0;external_callees_followed=0}
}
function Assert-LocatorTargetedPlan($Plan) {
    $limits=Get-LocatorTargetedLimits
    if($Plan.Phase -cne 'targeted-continuations' -or $Plan.Entry -cnotin '0x140a17970','0x140a17e70','0x140dd1f90' -or
       @($Plan.TargetedLimits.PSObject.Properties).Count -ne $limits.Count){throw 'Exact targeted seed and limits required.'}
    foreach($key in $limits.Keys){
        $value=$Plan.TargetedLimits.$key
        if(($value -isnot [int] -and $value -isnot [long]) -or $value -ne $limits[$key]){throw 'Exact targeted seed and limits required.'}
    }
}
function Get-LocatorRuntimePaths([string]$Python) {
    $root=Split-Path $Python -Parent
    $capstone=Join-Path $root 'Lib/site-packages/capstone'
    $paths=@(foreach($name in 'python3.dll','python312.dll','vcruntime140.dll','vcruntime140_1.dll'){Join-Path $root $name})
    $paths+=@(Get-ChildItem -LiteralPath $capstone -Recurse -File -Force|Where-Object {$_.Extension -cin '.py','.dll','.pyd'}|ForEach-Object FullName)
    @($paths|Sort-Object)
}
function New-LocatorJob([string]$Python,[string]$Arguments,[string]$Work) {
    [IW7.CommunityBuild.BuildJob]::Prepare($Python,$Arguments,$Work)
}
function Get-LocatorJobSnapshot($Owner) {
    $exited=$Owner.Exited;$active=$Owner.Active
    [pscustomobject]@{RootExited=$exited;Active=$active;ExitCode=$(if($exited){$Owner.ExitCode}else{$null})}
}
function Register-LocatorOriginalProcess($Lease,$Identity) {
    # Same current scheduler lock/schema, but compare the CIM tuple against the
    # original handles before persisting it. Never adopt a reused PID.
    Invoke-IW7ResourceLock {
        $registry=Read-IW7ResourceState
        $rows=@($registry.Leases|Where-Object Token -CEQ $Lease.Token)
        if($rows.Count -ne 1 -or $rows[0].Kind -cne 'Analysis' -or $rows[0].Scope -ine $Lease.Scope){throw 'Exact locator Analysis lease missing.'}
        $matches=@(Get-IW7ResourceProcesses|Where-Object PID -EQ $Identity.PID)
        if($matches.Count -ne 1 -or !(Test-IW7ResourceIdentity $Identity $matches[0])){throw 'CIM identity absent or differs from original locator handles.'}
        $rows[0].Processes=@($matches[0]);$rows[0].Phase='Running'
        Save-IW7ResourceState $registry
    }
}
function Measure-LocatorOutput([string]$Root) {
    $total=0L
    foreach($file in Get-ChildItem -LiteralPath $Root -Recurse -Force){
        if($file.Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)){throw 'Locator output reparse entry refused.'}
        if(!$file.PSIsContainer){$total+=$file.Length}
    }
    if($total -gt 4MB){throw 'Locator combined output exceeded 4 MiB.'}
    $total
}
function Save-LocatorState($State,[string]$Root) {
    $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($State|ConvertTo-Json -Depth 12)+"`n")
    if($bytes.Length -gt 128KB){throw 'Locator state exceeded 128 KiB.'}
    [IO.File]::WriteAllBytes((Join-Path $Root 'state.local.json'),$bytes)
}
function Test-LocatorRunningBudget($Plan,$State) {
    $bytes=Measure-LocatorOutput $Plan.RunRoot;$State.MaxObservedBytes=[math]::Max($State.MaxObservedBytes,$bytes)
    $memory=Get-IW7ResourceSnapshot
    if($memory.CommitLimit -le 0 -or $memory.Committed -gt $memory.CommitLimit*0.85){throw 'Locator commit pressure exceeded 85 percent.'}
}
function Assert-LocatorReport($Report,[bool]$Targeted=$false,[string]$ExpectedEntry='0x140a17970') {
    $schema=if($Targeted){'iw7.rig-targeted-static/2'}else{'iw7.rig-first-write-static/1'}
    if($Report.schema -cne $schema -or $Report.status -cne 'candidate-route-requires-review' -or $Report.report_limit_bytes -ne 3MB -or
       $Report.file_read_bytes -ne 25162848 -or $Report.reference_hashes_verified -isnot [bool] -or !$Report.reference_hashes_verified){throw 'Bounded locator data report required.'}
    foreach($key in 'actual_first_writer_established','live_breakpoint_established','reference_live_provenance','process_attached','game_or_zonetool_launched','acceptance_changed'){
        if($Report.$key -isnot [bool] -or $Report.$key){throw 'Locator report cannot establish runtime or acceptance.'}
    }
    $counters=@(@('decoded_instructions',128000),@('text_scans',17),@('linear_opcode_search_bytes',359301120))
    if($Targeted){
        $counters=@(@('decoded_instructions',8192),@('text_scans',0),@('linear_opcode_search_bytes',0),
            @('fragment_count',8),@('decoded_bytes',32768),@('control_edge_count',512),@('external_callees_followed',0),
            @('root_entries',1),@('visited_instructions',8192),@('refused_frontier_count',0))
        foreach($key in 'complete_logical_function_established','continuation_same_function_established','unvisited_is_unreachable'){
            if($Report.$key -isnot [bool] -or $Report.$key){throw 'Targeted fragments cannot establish a complete logical function.'}
        }
        foreach($key in 'frontier_queue_exhausted','all_declared_frontiers_traversed'){
            if($Report.$key -isnot [bool] -or !$Report.$key){throw 'Refused or pending frontiers cannot establish a completed route.'}
        }
        if($Report.entry -cne $ExpectedEntry -or @($Report.refused_frontiers).Count -ne 0 -or
           @($Report.pending_frontiers).Count -ne 0 -or $null -ne $Report.current_frontier){throw 'Exact entry and no refused/pending frontier required.'}
        Assert-LocatorTargetedPlan ([pscustomobject]@{Phase='targeted-continuations';Entry=$Report.entry;TargetedLimits=$Report.limits})
        if($Report.root_entries -ne 1 -or $Report.fragment_count -lt 1 -or $Report.decoded_instructions -lt 1 -or $Report.decoded_bytes -lt 1 -or
           $Report.visited_instructions -lt 1 -or $Report.visited_instructions -gt $Report.decoded_instructions -or
           @($Report.fragments).Count -ne $Report.fragment_count -or @($Report.control_edges).Count -ne $Report.control_edge_count -or
           $Report.elapsed_seconds -isnot [ValueType] -or $Report.elapsed_seconds -is [bool] -or
           ![double]::IsFinite([double]$Report.elapsed_seconds) -or $Report.elapsed_seconds -lt 0 -or $Report.elapsed_seconds -gt 10){throw 'Targeted report bounds differ.'}
        $bytes=0L;$instructions=0L
        foreach($fragment in $Report.fragments){
            if($fragment.decode_complete -isnot [bool] -or !$fragment.decode_complete){throw 'Incomplete fragment cannot establish a completed route.'}
            if(($fragment.bytes -isnot [int] -and $fragment.bytes -isnot [long]) -or $fragment.bytes -lt 1 -or $fragment.bytes -gt 16384){throw 'Targeted fragment byte bound differs.'}
            $bytes+=$fragment.bytes;$instructions+=@($fragment.instructions).Count
        }
        if($bytes -ne $Report.decoded_bytes -or $instructions -ne $Report.decoded_instructions){throw 'Targeted aggregate counters differ.'}
    }
    foreach($limit in $counters){
        $value=$Report.($limit[0])
        if(($value -isnot [int] -and $value -isnot [long]) -or $value -lt 0 -or $value -gt $limit[1]){throw 'Locator report counter exceeds fixed budget.'}
    }
}
function Stop-LocatorOriginalJob($Context,$State) {
    $State.StopRequested=$true;$Context.Closed=$false
    if(!$Context.Owner){$State.CleanupError='Original job factory returned no owner; closure unknown.';return}
    try {
        $started=Get-LocatorClock;$Context.Owner.Stop()
        while($true){
            $sample=Get-LocatorJobSnapshot $Context.Owner
            Assert-LocatorDeadline $started 15000
            $State.Closure=$sample
            if($sample.RootExited -and $sample.Active -eq 0){$Context.Closed=$true;return}
            Start-Sleep -Milliseconds 100
        }
    }catch{$State.CleanupError=$_.Exception.Message}
}
function Invoke-LocatorOwnedProcess($Plan,$State,$Context) {
    $arguments=Get-LocatorArguments $Plan
    $started=Get-LocatorClock;$State.StartedMonotonicMs=$started
    $Context.Closed=$false # A throwing factory is not evidence of no process.
    $Context.Owner=New-LocatorJob $Plan.Python.Path $arguments $Plan.RunRoot
    $Context.Owner.Resume() # Never put slow CIM registration before Resume.
    Assert-LocatorDeadline $started
    $State.Identity=[ordered]@{PID=$Context.Owner.PID;Image=$Context.Owner.Image;CreatedUtc=$Context.Owner.CreatedUtc;Priority=$Context.Owner.Priority}
    Assert-LocatorDeadline $started
    if($State.Identity.Image -ine $Plan.Python.Path -or !$State.Identity.CreatedUtc -or $State.Identity.Priority -ne 0x4000){throw 'Locator original handle identity or priority differs.'}
    try {
        Register-LocatorOriginalProcess $Context.Lease $State.Identity
        $State.Registration='Registered'
    }catch{
        $State.RegistrationError=$_.Exception.Message
        $sample=Get-LocatorJobSnapshot $Context.Owner
        Assert-LocatorDeadline $started
        if(!$sample.RootExited -or $sample.Active -ne 0){throw}
        $State.Registration='Original job already closed before CIM registration'
    }
    Assert-LocatorDeadline $started
    while($true){
        Test-LocatorRunningBudget $Plan $State
        Assert-LocatorDeadline $started # Fresh clock after telemetry/filesystem calls.
        $sample=Get-LocatorJobSnapshot $Context.Owner
        Assert-LocatorDeadline $started
        $State.Closure=$sample;$State.ElapsedMs=(Get-LocatorClock)-$started
        Save-LocatorState $State $Plan.RunRoot
        Assert-LocatorDeadline $started
        if($sample.RootExited -and $sample.Active -eq 0){
            $Context.Closed=$true
            if($sample.ExitCode -ne 0){throw "Locator original root exited $($sample.ExitCode)."}
            return
        }
        if(Test-Path -LiteralPath (Join-Path $Plan.RunRoot 'stop.request')){throw 'Coordinator requested locator stop.'}
        Assert-LocatorDeadline $started
        Start-Sleep -Milliseconds 100
        Assert-LocatorDeadline $started
    }
}
function Complete-LocatorOwnership($State,$Context) {
    if(!$Context.Closed){Stop-LocatorOriginalJob $Context $State}
    if($Context.Lease){
        try{Assert-LocatorGuards $Context;$State.SourcesUnchanged=$true}catch{$State.CleanupError=$_.Exception.Message}
        if($Context.Closed -and $State.SourcesUnchanged){
            try{Exit-IW7ResourceLease -Token $Context.Lease.Token;$Context.Lease=$null;$State.RetainedLeaseToken=$null}
            catch{$State.CleanupError=$_.Exception.Message}
        }
    }
    if($Context.Closed -and !$Context.Lease){
        if($Context.Owner){$Context.Owner.Dispose();$Context.Owner=$null}
        foreach($guard in $Context.Guards){$guard.Dispose()};$Context.Guards.Clear()
        $State.Closed=$true;$State.Quarantined=$false
    }else{
        $State.Status='Quarantined';$State.Quarantined=$true;$State.Closed=$Context.Closed
        [AppDomain]::CurrentDomain.SetData(('IW7.Locator.Quarantine.'+$State.RetainedLeaseToken),$Context)
    }
}
function Save-LocatorFinalCounters($State,[string]$Root) {
    for($i=0;$i -lt 5;$i++){
        Save-LocatorState $State $Root
        $previous=$State.FinalObservedBytes;$maximum=$State.MaxObservedBytes
        $State.FinalObservedBytes=Measure-LocatorOutput $Root
        $State.MaxObservedBytes=[math]::Max($State.MaxObservedBytes,$State.FinalObservedBytes)
        if($State.FinalObservedBytes -eq $previous -and $State.MaxObservedBytes -eq $maximum){return}
    }
    throw 'Locator final byte counters did not converge.'
}

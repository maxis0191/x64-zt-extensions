# Fixed diagnostic profile only. H1 retains pin readers, ownership, stop and receipt code.
function Assert-T7PrepatchPlan($Plan,[string]$Repo,[string]$Runner) {
    if($Plan.Schema -cne 'iw7.t7-prepatch-plan/1' -or $Plan.Runner -cne $Runner -or
       $Plan.PhysicalBytes -ne 6GB -or $Plan.CommitBytes -ne 8GB -or
       $Plan.GroupDeadlineSeconds -ne 200 -or $Plan.DeadlineSeconds -ne 120 -or
       $Plan.MutableOutputLimitBytes -ne 64MB -or $Plan.MetadataReserveBytes -ne 64KB -or
       $Plan.CleanupSeconds -ne 5 -or $Plan.ReportLimitBytes -ne 256KB -or
       $Plan.LogLimitBytes -ne 1MB -or $Plan.RetryAuthorized -isnot [bool] -or $Plan.RetryAuthorized){throw 'Fixed diagnostic plan differs.'}
    Assert-H1Path $Plan.RunRoot
    if([IO.Path]::GetDirectoryName($Plan.RunRoot) -cne (Join-Path $Repo 'runtime') -or
       [IO.Path]::GetFileName($Plan.RunRoot) -cnotmatch '^t7-prepatch-[a-z][a-z0-9-]*$' -or
       $Plan.WorkingDirectory -cne (Join-Path $Plan.RunRoot 'work') -or
       $Plan.StageRoot -cne (Join-Path $Plan.RunRoot 'evidence') -or
       $Plan.Image -cne (Join-Path $Plan.WorkingDirectory 't7-zonetool-prepatch-probe.exe') -or
       @($Plan.Arguments).Count -ne 1 -or $Plan.Arguments[0] -cne '-t7-prepatch-probe'){throw 'Exact private command required.'}
    foreach($dir in @($Plan.WorkingDirectory,$Plan.StageRoot,(Join-Path $Plan.RunRoot 'temp'))) {
        Assert-H1Path $dir
        if(![IO.Directory]::Exists($dir)){throw 'Prepared private directories required.'}
    }
    foreach($path in @($Plan.Image,(Join-Path $Plan.RunRoot 'attempt.json'),(Join-Path $Plan.RunRoot 'stop.request'),
        (Join-Path $Plan.WorkingDirectory 't7-prepatch-probe.local.json'),(Join-Path $Plan.RunRoot 'zone'))) {
        if(Test-Path -LiteralPath $path){throw 'Attempt, output, stop marker or candidate already exists; no retry.'}
    }
    $names=@([IO.Directory]::EnumerateFileSystemEntries($Plan.WorkingDirectory)|ForEach-Object {[IO.Path]::GetFileName($_)}|Sort-Object)
    if(($names -join '|') -cne 'BlackOps3_UnrankedDedicatedServer.exe|steam_api64.dll' -or
       @([IO.Directory]::EnumerateFileSystemEntries($Plan.StageRoot)).Count -or
       @([IO.Directory]::EnumerateFileSystemEntries((Join-Path $Plan.RunRoot 'temp'))).Count){throw 'Only the two prepared aliases and empty evidence/temp are allowed.'}
    if(@($Plan.Bindings).Count -gt 32 -or @($Plan.Bindings.Path|Sort-Object -Unique).Count -ne @($Plan.Bindings).Count){throw 'Bounded unique bindings required.'}
    foreach($pin in $Plan.Bindings) {
        Assert-H1Path $pin.Path
        if($pin.IsText -isnot [bool] -or $pin.Bytes -le 0 -or $pin.Bytes -gt 64MB -or
           ($pin.IsText -and $pin.Bytes -gt 1MB) -or $pin.SHA256 -cnotmatch '^[0-9a-f]{64}$' -or
           (Get-Item -LiteralPath $pin.Path).Length -ne $pin.Bytes){throw 'Pin metadata/type differs.'}
    }
    foreach($pair in @(@('BlackOps3_UnrankedDedicatedServer.exe',21737352,'3df511d71e3690b14517379783bbfb713f6fe2ed2f2e73b445b4878216686156',$Plan.EngineSource),
                       @('steam_api64.dll',235600,'71af8666392acad2080a816b9f1196fe9ccb950e1db8a549f8312c4d231f55a8',$Plan.SteamSource))) {
        foreach($path in @($pair[3],(Join-Path $Plan.WorkingDirectory $pair[0]))) {
            $pin=@($Plan.Bindings|Where-Object Path -CEQ $path)
            if($pin.Count -ne 1 -or $pin[0].Bytes -ne $pair[1] -or $pin[0].SHA256 -cne $pair[2] -or $pin[0].IsText){throw 'Exact existing engine/Steam source and alias pins required.'}
        }
    }
    if($Plan.OutputLimitBytes -ne (64MB+21737352+235600+$Plan.CandidateBytes)){throw 'Output budget must include immutable binary aliases.'}
}
function Assert-T7PrepatchBuild($Plan,$Receipt) {
    foreach($field in 'InputsReverified','TreeClosureConfirmed','LeaseReleased','Quarantined','CandidateExecuted') {
        if($Receipt.$field -isnot [bool]){throw 'Build lifecycle booleans required.'}
    }
    if($Receipt.PlanSHA256 -cne $Plan.ExpectedBuildPlanSHA256 -or $Receipt.Status -cne 'Passed' -or !$Receipt.InputsReverified -or !$Receipt.TreeClosureConfirmed -or
       !$Receipt.LeaseReleased -or $Receipt.Quarantined -or $Receipt.CandidateExecuted){throw 'Closed successful unexecuted build required.'}
    $profile=$Receipt.BuildProfile
    if(!$profile -or $profile.Name -cne 't7-prepatch-probe' -or $profile.Option -cne '-t7-prepatch-probe' -or
       $profile.ArgumentCount -ne 2 -or $profile.Report -cne 't7-prepatch-probe.local.json'){throw 'Instrumented build profile required; ordinary D2 is refused.'}
    foreach($name in 'Helper','Wiring','PreparedMain') {
        $expected=$profile.$name
        $pin=@($Plan.Bindings|Where-Object {$_.Path -ceq $expected.Path -and $_.IsText -and $_.Bytes -eq $expected.Bytes -and $_.SHA256 -ceq $expected.SHA256})
        if($pin.Count -ne 1){throw 'Instrumented helper/wiring/main pin missing.'}
    }
    $artifacts=@($Receipt.Stages|ForEach-Object {$_.Artifacts}|Where-Object {$_.Path -ceq $Plan.CandidateSource})
    if($artifacts.Count -ne 1 -or $artifacts[0].Bytes -ne $Plan.CandidateBytes -or $artifacts[0].SHA256 -cne $Plan.CandidateSHA256){throw 'Candidate differs from actual build artifact.'}
}
function New-T7PrepatchStart($Plan) {
    $start=[Diagnostics.ProcessStartInfo]::new($Plan.Image)
    $start.WorkingDirectory=$Plan.WorkingDirectory;$start.UseShellExecute=$false;$start.CreateNoWindow=$true;$start.WindowStyle='Hidden'
    $start.Environment.Clear()
    $windows=[Environment]::GetEnvironmentVariable('SystemRoot')
    $start.Environment['SystemRoot']=$windows;$start.Environment['WINDIR']=$windows
    $start.Environment['PATH']=Join-Path $windows 'System32';$start.Environment['COMSPEC']=Join-Path $windows 'System32/cmd.exe'
    $temp=Join-Path $Plan.RunRoot 'temp'
    $start.Environment['TEMP']=$temp;$start.Environment['TMP']=$temp
    $start.Environment['USERPROFILE']=Join-Path $temp 'profile'
    $start.Environment['APPDATA']=Join-Path $temp 'profile/roaming';$start.Environment['LOCALAPPDATA']=Join-Path $temp 'profile/local'
    $start.ArgumentList.Add('-t7-prepatch-probe')
    $start
}
function Assert-T7PrepatchMain($Expected) {
    $rows=@(Get-IW7ResourceProcesses|Where-Object PID -EQ $Expected.PID)
    $udp=@(Get-NetUDPEndpoint -LocalPort 27016 -ErrorAction Stop)
    if($rows.Count -ne 1 -or !(Test-IW7ResourceIdentity $Expected $rows[0]) -or !$udp.Count -or
       @($udp|Where-Object OwningProcess -NE $Expected.PID).Count){throw 'Preserved Main generation/UDP ownership differs.'}
    [ordered]@{CapturedUtc=[DateTime]::UtcNow.ToString('o');GenerationAndUDP27016OwnerUnchanged=$true}
}
function Get-T7PrepatchOutcome($Report,$Identity,[Nullable[int]]$ExitCode,[string]$ExpectedModule) {
    if($null -eq $Report){return 'NoCapture'}
    if($Report.schema -cne 'iw7.t7-prepatch-memory-observation/1' -or
       $Report.phase -cne 'first_dpi_before_component_post_unpack' -or $Report.pid -ne $Identity.PID -or
       $Report.read_limit -ne 4MB -or $Report.report_limit -ne 256KB -or
       $Report.capture_complete -isnot [bool] -or $Report.window_count -ne 12 -or
       $Report.window_observations -ne @($Report.windows).Count -or @($Report.windows).Count -gt 12 -or
       $Report.source_base -cne '0x140000000' -or $Report.requested_bytes -lt 0 -or
       $Report.requested_bytes -gt 4MB -or $Report.returned_bytes -lt 0 -or
       $Report.returned_bytes -gt $Report.requested_bytes){throw 'Diagnostic report identity/schema differs.'}
    foreach($field in 'boot_authorized','abi_proven','runtime_compatibility_proven') {
        if($Report.$field -isnot [bool] -or $Report.$field){throw 'Diagnostic report overclaims compatibility.'}
    }
    if($Report.PSObject.Properties['creation_filetime'] -and
       [DateTime]::FromFileTimeUtc([long]$Report.creation_filetime).ToString('o') -cne $Identity.CreatedUtc){throw 'Diagnostic process generation differs.'}
    if(!$Report.capture_complete) {
        if($Report.status -cne 'incomplete_stop' -or $ExitCode -ne 2){throw 'Partial report/exit disagree.'}
        return 'CapturePartial'
    }
    if($ExitCode -ne 0 -or $Report.status -cne 'captured_for_offline_review' -or
       !$Report.PSObject.Properties['creation_filetime'] -or
       $Report.requested_bytes -le 0 -or $Report.returned_bytes -ne $Report.requested_bytes -or
       @($Report.windows).Count -ne 12 -or ![IO.Path]::IsPathFullyQualified($Report.module_path) -or
       [IO.Path]::GetFullPath($Report.module_path) -ine $ExpectedModule -or
       $Report.base_matches_source -isnot [bool] -or $Report.PSObject.Properties['capture_error'] -or
       $Report.PSObject.Properties['metadata_error']){throw 'Complete capture contract differs.'}
    $sites=@('DB_FindXAssetHeader','DB_LoadXAssets','SL_ConvertToString','boot_call','server_thread_ret',
        'copy_info_branch_1','copy_info_branch_2','image_loader_call','integrity_intact_1','integrity_intact_2','integrity_intact_3','integrity_split')
    $lengths=@(256,256,128,96,128,96,96,96,96,96,96,96)
    $rvas=@(0x1D5FB0,0x1D8740,0x1632C0,0x502AA9,0x537840,0x1A18DF,0x1A1B5B,0x1B1E5D,0x064DC4,0x909BD4,0x10654C1,0x0621A8)
    for($i=0;$i -lt 12;$i++) {
        $row=$Report.windows[$i]
        $before=if($i -in 0,1,2,4){0}else{32}
        if($row.site -cne $sites[$i] -or $row.window_bytes -ne $lengths[$i] -or $row.rva -ne $rvas[$i] -or $row.window_rva -ne ($rvas[$i]-$before) -or
           $row.bytes_hex -cnotmatch ('^[0-9a-f]{'+(2*$lengths[$i])+'}$') -or
           $row.PSObject.Properties['error']){throw 'Complete capture window differs.'}
    }
    'CaptureComplete'
}
function Read-T7PrepatchReport($Plan,$State,$Context) {
    $path=Join-Path $Plan.WorkingDirectory 't7-prepatch-probe.local.json'
    if(!(Test-Path -LiteralPath $path)){return 'NoCapture'}
    $State.CaptureOutcome='CapturePresentUnqualified'
    Assert-H1Path $path
    $size=(Get-Item -LiteralPath $path).Length
    if($size -le 0 -or $size -gt 256KB){throw 'Diagnostic JSON size refused.'}
    $pin=[pscustomobject]@{Path=$path;Bytes=$size;SHA256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
    $Context.Guards.Add((Open-H1Pin $pin))
    $report=Read-H1SmallJson $path 256KB
    $State.Report=$pin
    Get-T7PrepatchOutcome $report $State.Identity $State.ExitCode (Join-Path $Plan.WorkingDirectory 'BlackOps3_UnrankedDedicatedServer.exe')
}
function Enable-T7PrepatchRuntimeProfile($Plan,$Context) {
    $script:T7PrepatchGroupStarted=Get-H1Clock
    $script:T7PrepatchBaseDeadline=${function:Assert-H1Deadline}
    $script:T7PrepatchBaseBudget=${function:Test-H1Budget}
    function script:Assert-H1Deadline($Started,[int]$Seconds) {
        & $script:T7PrepatchBaseDeadline $script:T7PrepatchGroupStarted 200
        & $script:T7PrepatchBaseDeadline $Started $Seconds
    }
    function script:Test-H1Budget($Plan,$State) {
        Assert-H1Deadline $script:T7PrepatchGroupStarted 200
        & $script:T7PrepatchBaseBudget $Plan $State
        foreach($name in 'stdout.log','stderr.log') {
            $p=Join-Path $Plan.StageRoot $name
            if((Test-Path -LiteralPath $p) -and (Get-Item -LiteralPath $p).Length -gt $Plan.LogLimitBytes){throw 'Diagnostic log cap exceeded.'}
        }
        $p=Join-Path $Plan.WorkingDirectory 't7-prepatch-probe.local.json'
        if((Test-Path -LiteralPath $p) -and (Get-Item -LiteralPath $p).Length -gt 256KB){throw 'Diagnostic report cap exceeded.'}
        $allowed=@('BlackOps3_UnrankedDedicatedServer.exe','steam_api64.dll','t7-zonetool-prepatch-probe.exe','t7-prepatch-probe.local.json')
        foreach($entry in [IO.Directory]::EnumerateFileSystemEntries($Plan.WorkingDirectory)) {
            if([IO.Path]::GetFileName($entry) -cnotin $allowed -or [IO.Directory]::Exists($entry)){throw 'Unexpected engine working-directory output; preserve and stop.'}
        }
        Assert-H1Deadline $script:T7PrepatchGroupStarted 200
    }
}

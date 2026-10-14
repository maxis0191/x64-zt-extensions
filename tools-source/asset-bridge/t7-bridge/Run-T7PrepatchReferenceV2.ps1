# Default: source/pin metadata check only. -Run consumes one reviewed attempt.
[CmdletBinding()]
param([Parameter(Mandatory)][string]$PlanPath,[Parameter(Mandatory)][string]$PlanSHA256,[switch]$Run)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
if(!$IsWindows -or [IntPtr]::Size -ne 8 -or $PSVersionTable.PSVersion.Major -lt 7){throw 'Windows x64 PowerShell 7 required.'}
if($PlanSHA256 -cnotmatch '^[0-9a-f]{64}$'){throw 'V2 exact reviewed plan SHA256 required.'}
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$core=Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1'
. $core # Trusted repository functions only; no type, process or lease is loaded.
$guards=[Collections.Generic.List[object]]::new()
$context=[pscustomobject]@{Owner=$null;Closed=$true;Lease=$null;Guards=$guards}
$state=$null;$failure=$null;$attempted=$false;$plan=$null
$taskHostState=$null
try {
    $size=(Get-Item -LiteralPath $PlanPath).Length
    if($size -gt 128KB){throw 'Diagnostic plan exceeds 128 KiB.'}
    $guards.Add((Open-H1Pin ([pscustomobject]@{Path=$PlanPath;Bytes=$size;SHA256=$PlanSHA256})))
    $plan=Read-H1SmallJson $PlanPath
    $profile=Join-Path $PSScriptRoot 'T7PrepatchReferenceV2.Profile.ps1'
    $scheduler=Join-Path $repo 'ops/Resource-Scheduler.Core.ps1'
    $required=@($PSCommandPath,$profile,$core,$scheduler,(Join-Path $repo 'ops/Resource-Memory.ps1'),
        (Join-Path $repo 'ops/Resource-RecorderOwnedProcess.Core.ps1'),(Join-Path $repo 'ops/native/ResourceMemory.cs'))
    foreach($path in $required) {
        $pin=@($plan.Bindings|Where-Object {$_.Path -is [string] -and $_.Path -ceq $path -and $_.IsText -is [bool] -and $_.IsText})
        if($pin.Count -ne 1 -or ($pin[0].Bytes -isnot [int] -and $pin[0].Bytes -isnot [long]) -or $pin[0].Bytes -le 0 -or $pin[0].Bytes -gt 1MB -or
           $pin[0].SHA256 -isnot [string] -or $pin[0].SHA256 -cnotmatch '^[0-9a-f]{64}$'){throw 'V2 scalar bounded exact source binding missing.'}
        $guards.Add((Open-H1Pin $pin[0]))
    }
    . $profile
    $plan=Read-T7RefV2Json $PlanPath
    Assert-T7RefV2Plan $plan $repo $PSCommandPath
    foreach($pin in $plan.Bindings|Where-Object IsText){if($pin.Path -cnotin $required){$guards.Add((Open-H1Pin $pin))}}
    $job=@($plan.Bindings|Where-Object {$_.Path -ceq $plan.JobAssembly -and !$_.IsText})
    if($job.Count -ne 1 -or $job[0].SHA256 -cne '5f613ebb83019dbf4bfa4f6a93c5329098343729b70acc2cfa70aa8b64f195f8'){throw 'Existing witnessed NativeJob pin required.'}
    $shell=[Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
    if($plan.HostImage -cne $shell -or @($plan.Bindings|Where-Object {$_.Path -ceq $shell -and !$_.IsText}).Count -ne 1){throw 'Exact current PowerShell host pin required.'}
    Assert-T7RefV2Build $plan (Read-T7RefV2Json $plan.BuildPlan 1MB)
    Assert-T7RefV2ClosedBuildPins $plan (Read-T7RefV2Json $plan.BuildClosedPins)
    $candidateReady=$null -ne $plan.CandidateSource
    if($candidateReady) {
        Assert-T7RefV2String $plan.CandidateSource 'CandidateSource';Assert-T7RefV2String $plan.CandidateSHA256 'CandidateSHA256'
        Assert-T7RefV2String $plan.BuildReceipt 'BuildReceipt';Assert-T7RefV2String $plan.ExpectedBuildReceiptSHA256 'ExpectedBuildReceiptSHA256'
        if($plan.CandidateBytes -ne 21777408 -or $plan.CandidateSHA256 -cne 'f11c683b5379e08cca4e881a7a412a2a8a45b5f872acb690ac62218fce6717f5' -or $plan.ExpectedBuildReceiptSHA256 -cne '77e7fecfbf47217cee2fb5f4e371e76350961b759007130d1d4980488168b9f8'){throw 'Exact original V2 candidate/receipt cohort required.'}
        $candidate=@($plan.Bindings|Where-Object {$_.Path -ceq $plan.CandidateSource -and !$_.IsText})
        if($candidate.Count -ne 1 -or $candidate[0].SHA256 -cne $plan.CandidateSHA256 -or $candidate[0].Bytes -ne $plan.CandidateBytes){throw 'Candidate pin differs.'}
        $build=@($plan.Bindings|Where-Object {$_.Path -ceq $plan.BuildReceipt -and $_.IsText})
        if($build.Count -ne 1 -or $build[0].Bytes -ne 16885 -or $build[0].SHA256 -cne $plan.ExpectedBuildReceiptSHA256){throw 'Actual instrumented build receipt binding missing.'}
        Assert-T7RefV2Build $plan (Read-T7RefV2Json $plan.BuildPlan 1MB) (Read-T7RefV2Json $plan.BuildReceipt 1MB)
    }elseif($plan.CandidateBytes -ne 0 -or $null -ne $plan.CandidateSHA256 -or $null -ne $plan.BuildReceipt -or $null -ne $plan.ExpectedBuildReceiptSHA256){throw 'Incomplete candidate placeholder differs.'}
    if(!$Run) {
        [ordered]@{Status=$(if($candidateReady){'PlanCheckedPendingGO'}else{'PlanCheckedPendingInstrumentedCandidate'});
            CandidateBound=$candidateReady;NativeTypesLoaded=$false;BinaryInputsHashed=$false;LeaseAcquired=$false;FilesCreated=$false;Ready=$false}|ConvertTo-Json
        return
    }
    if(!$candidateReady){throw 'Instrumented candidate required before Run.'}
    Assert-T7RefV2HostArguments $plan $PlanPath $PlanSHA256 ([Environment]::GetCommandLineArgs())
    if([AppDomain]::CurrentDomain.GetData('IW7.T7PrepatchReferenceV2')){throw 'Original V2 host already consumed; no re-entry.'}
    if(('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7ResourceMemoryV1' -as [type])){throw 'Fresh PowerShell host required.'}
    . $scheduler
    $before=Assert-T7RefV2Main $plan
    $state=[ordered]@{Schema='iw7.t7-prepatch-reference-run/2';Status='Running';PlanSHA256=$PlanSHA256;
        Stage='Prepatch';DeadlineSeconds=120;MaxObservedOutputBytes=0L;Identity=$null;ExitCode=$null;
        TreeClosureConfirmed=$true;LeaseReleased=$false;Quarantined=$false;TerminationRequested=$false;
        CaptureOutcome='NoCapture';CompatibilityProven=$false;Ready=$false;MainBefore=$before;InputsReverified=$false;InputMetadata=@()}
    $context.Lease=Enter-IW7ResourceLease -Scope $plan.RunRoot -Kind Extract -PhysicalBytes 6GB -CommitBytes 8GB -Owner 'T7 reference V2 diagnostic only'
    $state.LeaseToken=$context.Lease.Token
    # Last create-only check precedes publication of our own host-start marker.
    Assert-T7RefV2Plan $plan $repo $PSCommandPath
    $taskProcess=[Diagnostics.Process]::GetCurrentProcess()
    $taskHostState=[pscustomobject]@{Host=[pscustomobject]@{PID=$PID;CreatedUtc=$taskProcess.StartTime.ToUniversalTime().ToString('o');Image=$shell};Plan=$plan;PlanSHA256=$PlanSHA256;Context=$context;State=$state;Phase='Running';CanExit=$false}
    [AppDomain]::CurrentDomain.SetData('IW7.T7PrepatchReferenceV2',$taskHostState)
    $taskStartPath=$plan.RunRoot+'.host-start.json'
    $taskStartBytes=[Text.UTF8Encoding]::new($false).GetBytes(($taskHostState.Host|ConvertTo-Json)+"`n")
    $taskStartStream=[IO.FileStream]::new($taskStartPath,'CreateNew','Write','Read');try{$taskStartStream.Write($taskStartBytes,0,$taskStartBytes.Length)}finally{$taskStartStream.Dispose()}
    Enable-T7RefV2RuntimeProfile $plan $context
    $marker=[IO.FileStream]::new((Join-Path $plan.RunRoot 'attempt.json'),'CreateNew','Write','Read')
    try{$bytes=[Text.Encoding]::UTF8.GetBytes((([ordered]@{Schema='iw7.t7-prepatch-reference-attempt/2';PlanSHA256=$PlanSHA256;StartedUtc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json -Compress)+"`n"));$marker.Write($bytes,0,$bytes.Length);$attempted=$true}finally{$marker.Dispose()}
    foreach($pin in $plan.Bindings|Where-Object {!$_.IsText}){$guards.Add((Open-H1Pin $pin));Assert-H1Deadline $script:T7RefV2Started 200}
    $state.InputMetadata=@($plan.Bindings|Where-Object {!$_.IsText}|ForEach-Object {
        $item=Get-Item -LiteralPath $_.Path;[pscustomobject]@{Path=$_.Path;Bytes=$item.Length;Attributes=[string]$item.Attributes;LastWriteUtc=$item.LastWriteTimeUtc.ToString('o')}
    })
    New-Item -ItemType HardLink -Path $plan.Image -Target $plan.CandidateSource -ErrorAction Stop|Out-Null
    $guards.Add((Open-H1Pin ([pscustomobject]@{Path=$plan.Image;Bytes=$plan.CandidateBytes;SHA256=$plan.CandidateSHA256})))
    foreach($name in 'profile','profile/roaming','profile/local'){[IO.Directory]::CreateDirectory((Join-Path (Join-Path $plan.RunRoot 'temp') $name))|Out-Null}
    $null=[Reflection.Assembly]::LoadFrom($plan.JobAssembly)
    Assert-H1Deadline $script:T7RefV2Started 200
    Test-H1Budget $plan $state
    Invoke-H1OwnedStage $plan $state $context (New-T7RefV2Start $plan) $plan.CandidateSHA256 $plan.StageRoot
}catch{
    $failure=$_
    if($state){$state.Error=$_.Exception.Message;$state.Status='Failed'}
}finally{
    # On ordinary root0/root2 closure, inspect/reverify while admission and guards
    # still exist. Never rehash binary inputs after Complete-H1Stage releases it.
    if($state -and $attempted -and $context.Closed -and $context.Lease) {
        try {
            $state.CaptureOutcome=Read-T7RefV2Report $plan $state $context
            foreach($pin in $plan.Bindings){$guard=Open-H1Pin $pin;try{}finally{$guard.Dispose()};Assert-H1Deadline $script:T7RefV2Started 200}
            foreach($before in $state.InputMetadata) {
                $now=Get-Item -LiteralPath $before.Path
                if($now.Length -ne $before.Bytes -or [string]$now.Attributes -cne $before.Attributes -or $now.LastWriteTimeUtc.ToString('o') -cne $before.LastWriteUtc){throw 'Original input metadata changed; restoration unconfirmed.'}
            }
            $state.InputsReverified=$true;$state.OriginalInputMetadataUnchanged=$true;$state.AliasesRetained=$true
            $state.MainAfter=Assert-T7RefV2Main $plan
            Test-H1Budget $plan $state
            Assert-H1Deadline $script:T7RefV2Started 200
            if(!$failure -and $state.CaptureOutcome -cne 'CaptureComplete'){throw 'Diagnostic did not produce a complete capture.'}
        }catch{if(!$failure){$failure=$_};$state.ValidationError=$_.Exception.Message;$state.Status='Failed'}
    }
    if($state){Complete-H1Stage $context $state}
    if($state -and $attempted -and $context.Closed -and !$context.Lease -and !$state.InputsReverified -and $state.TerminationRequested) {
        # Only the bounded diagnostic JSON is read after forced closure. No
        # binary rehash or success qualification occurs outside the reservation.
        try{$state.CaptureOutcome=Read-T7RefV2Report $plan $state $context}
        catch{$state.ReportError=$_.Exception.Message}
    }
    if($state -and !$context.Closed){$state.CaptureOutcome='NotInspectedWhileJobUnclosed'}
    if($state -and $attempted) {
        if($context.Owner -and $context.Closed){$state.ClosureEvidence='Pinned NativeJob CloseConfirmed rechecks original RootExited and ActiveProcesses==0; original ExitCode retained.'}
        $state.FinishedUtc=[DateTime]::UtcNow.ToString('o')
        try {
            if(!$state.Quarantined){Assert-H1Deadline $script:T7RefV2Started 200}
            if(!$failure -and $context.Closed -and !$context.Lease -and $state.LeaseReleased -and
               !$state.TerminationRequested -and $state.CaptureOutcome -ceq 'CaptureComplete' -and $state.InputsReverified){$state.Status='CaptureCompletePendingReview'}
        }catch{if(!$failure){$failure=$_};$state.Status='Failed';$state.FinalizationError=$_.Exception.Message}
        try {
            Write-H1Receipt $plan $state $plan.StageRoot
            if($context.Closed -and !$context.Lease){foreach($guard in $guards){$guard.Dispose()};$guards.Clear()}
            if($state.Status -ceq 'CaptureCompletePendingReview') {
                try{Assert-H1Deadline $script:T7RefV2Started 200}
                catch {
                    $failure=$_;$state.Status='Failed';$state.FinalizationError=$_.Exception.Message
                    [IO.File]::Move((Join-Path $plan.StageRoot 'receipt.json'),(Join-Path $plan.StageRoot 'receipt.deadline-exceeded.json'))
                    Write-H1Receipt $plan $state $plan.StageRoot
                }
            }
        }catch{if(!$failure){$failure=$_};Write-Warning ('Receipt publication failed: '+$_.Exception.Message)}
    }
    if($context.Closed -and !$context.Lease){foreach($guard in $guards){$guard.Dispose()};$guards.Clear()}
}
if($taskHostState){$taskHostState.Phase='Returned'}
if($state -and $state.Quarantined) {
    Write-Warning 'Original owner/lease/guards retained in IW7.H1.Quarantine; keep this host for recovery. No retry.'
    while($true){Start-Sleep -Seconds 1}
}
if($taskHostState){Complete-T7RefV2Host}
if($state){[ordered]@{Status=$state.Status;CaptureOutcome=$state.CaptureOutcome;Receipt=(Join-Path $plan.StageRoot 'receipt.json');CompatibilityProven=$false;Ready=$false}|ConvertTo-Json}
if($failure){throw $failure}

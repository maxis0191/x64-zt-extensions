# MaterialV2 compiler-closure policy adapted to a DIRECT original cl.exe root.
# Existing pinned NativeJob owns every native handle and every stop primitive.
function Get-H1PrivateMethod($Owner,[string]$Name,[switch]$Static) {
    if($Owner.GetType().FullName -cne 'IW7.AnimationProbe.NativeJob'){throw 'Exact pinned NativeJob type required.'}
    $flags=[Reflection.BindingFlags]::NonPublic -bor [Reflection.BindingFlags]::DeclaredOnly
    $flags=$flags -bor $(if($Static){[Reflection.BindingFlags]::Static}else{[Reflection.BindingFlags]::Instance})
    $method=$Owner.GetType().GetMethod($Name,$flags)
    if(!$method){throw ('Pinned NativeJob method unavailable: '+$Name)}
    $method
}
function Get-H1OriginalHandle($Owner,[ValidateSet('job','process')][string]$Name) {
    if($Owner.GetType().FullName -cne 'IW7.AnimationProbe.NativeJob'){throw 'Exact pinned NativeJob type required.'}
    $field=$Owner.GetType().GetField($Name,([Reflection.BindingFlags]::NonPublic -bor [Reflection.BindingFlags]::Instance -bor [Reflection.BindingFlags]::DeclaredOnly))
    if(!$field -or $field.FieldType -ne [Microsoft.Win32.SafeHandles.SafeFileHandle]){throw 'Pinned original handle layout changed.'}
    $handle=$field.GetValue($Owner)
    if(!$handle -or $handle.IsClosed -or $handle.IsInvalid){throw 'Live original handle required.'}
    $handle
}
function Get-H1OriginalState($Owner) {
    $job=Get-H1OriginalHandle $Owner job;$process=Get-H1OriginalHandle $Owner process
    $jobHeld=$false;$processHeld=$false
    try {
        $job.DangerousAddRef([ref]$jobHeld);$process.DangerousAddRef([ref]$processHeld)
        $exited=(Get-H1PrivateMethod $Owner RootExited).Invoke($Owner,@())
        $active=(Get-H1PrivateMethod $Owner ActiveProcesses).Invoke($Owner,@())
        $exitCode=$null
        if($exited) {
            $arguments=[object[]]@($process,[uint32]0)
            if(!(Get-H1PrivateMethod $Owner GetExitCodeProcess -Static).Invoke($null,$arguments)){throw 'Original compiler exit unavailable.'}
            $exitCode=$arguments[1]
        }
        [pscustomobject]@{RootExited=$exited;RootExitCode=$exitCode;ActiveProcesses=$active;PID=$Owner.PID;Image=$Owner.Image;
            CreatedUtc=[datetime]::FromFileTimeUtc($Owner.CreationFileTime).ToString('o');CapturedUtc=[datetime]::UtcNow.ToString('o')}
    }finally{
        if($processHeld){$process.DangerousRelease()};if($jobHeld){$job.DangerousRelease()}
        [GC]::KeepAlive($Owner)
    }
}
function Stop-H1OriginalJob($Owner) {
    $job=Get-H1OriginalHandle $Owner job;$held=$false
    try {
        $job.DangerousAddRef([ref]$held)
        # The exact existing provider's stop primitive, on its own retained job.
        # Do not call StopAndConfirm here: it disposes handles before a fresh poll.
        $arguments=[object[]]@($job,[uint32]3758096385)
        if(!(Get-H1PrivateMethod $Owner TerminateJobObject -Static).Invoke($null,$arguments)){throw 'Original job termination request failed.'}
    }finally{if($held){$job.DangerousRelease()};[GC]::KeepAlive($Owner)}
}
function Get-H1OriginalMembers($Owner) {[IW7.H1Diagnostics.JobMembers]::Capture($Owner)}
function Assert-H1CompilerRoot($Snapshot,$Identity,$Policy) {
    if($Snapshot.RootExited -isnot [bool] -or !$Snapshot.RootExited -or
       ($Snapshot.RootExitCode -isnot [uint32] -and $Snapshot.RootExitCode -isnot [int] -and $Snapshot.RootExitCode -isnot [long]) -or
       $Snapshot.RootExitCode -ne 0 -or $Snapshot.Image -ine $Policy.Compiler -or
       $Snapshot.PID -ne $Identity.PID -or $Snapshot.Image -ine $Identity.Image -or
       $Snapshot.CreatedUtc -cne $Identity.CreatedUtc){throw 'Successful original compiler handle identity required.'}
    $null=Get-MaterialV2MemberTime $Snapshot.CreatedUtc
}
function Assert-H1TelemetryCapture($Capture,$Snapshot,$Identity,$Policy) {
    Assert-H1CompilerRoot $Snapshot $Identity $Policy
    if($Snapshot.ActiveProcesses -ne 1 -or $Capture.AssignedCount -ne 1 -or $Capture.ListedCount -ne 1 -or
       @($Capture.Members).Count -ne 1){throw 'Exactly one complete original-job member required.'}
    $member=@($Capture.Members)[0]
    Assert-MaterialV2MemberIdentity $member
    if($member.Image -ine $Policy.Telemetry -or $member.PID -eq $Identity.PID -or $member.ParentPID -ne $Identity.PID -or
       (Get-MaterialV2MemberTime $member.CreatedUtc) -lt (Get-MaterialV2MemberTime $Identity.CreatedUtc) -or
       (Get-MaterialV2MemberTime $member.CreatedUtc) -gt (Get-MaterialV2MemberTime $Capture.CapturedUtc)){
        throw 'Residual is not the pinned original compiler telemetry child.'
    }
    $member
}
function Get-H1CompilerArtifacts($Plan,$Context) {
    foreach($name in 'native_probe.exe','native_probe.obj','native_probe.pdb') {
        $path=Join-Path $Plan.RunRoot ('compile/'+$name);Assert-H1Path $path
        $item=Get-Item -LiteralPath $path
        if($item.Length -le 0 -or $item.Length -gt 30MB){throw 'Compiler artifact size refused.'}
        $pin=[pscustomobject]@{Path=$path;Bytes=$item.Length;SHA256=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()}
        $Context.Guards.Add((Open-H1Pin $pin))
        $pin
    }
}
function Confirm-H1BoundInputs($Plan) {
    foreach($pin in $Plan.Bindings){$guard=Open-H1Pin $pin;try{}finally{$guard.Dispose()}}
}
function Assert-H1CompilerToolPins($Plan,$Policy) {
    foreach($expected in @(@($Policy.Compiler,$Policy.CompilerSHA256),@($Policy.Telemetry,$Policy.TelemetrySHA256))) {
        $pin=@($Plan.Bindings|Where-Object Path -IEQ $expected[0])
        if($pin.Count -ne 1 -or $pin[0].SHA256 -ine $expected[1]){throw 'Reviewed compiler/telemetry binding missing.'}
        $guard=Open-H1Pin $pin[0];try{}finally{$guard.Dispose()}
    }
}
function Complete-H1CompilerTelemetry($Plan,$State,$Context,$Snapshot,$Started) {
    $evidence=$State.CompilerTelemetry
    if(!$Snapshot.RootExited -or $Snapshot.ActiveProcesses -eq 0 -or $evidence.Completed){return $false}
    $policy=Get-MaterialV2CompilerPolicy $Plan.Compiler
    Assert-H1CompilerRoot $Snapshot $State.Identity $policy
    Assert-H1Deadline $Started $State.DeadlineSeconds
    Confirm-H1BoundInputs $Plan
    Assert-H1CompilerToolPins $Plan $policy
    $evidence.Artifacts=@(Get-H1CompilerArtifacts $Plan $Context)
    $evidence.CompilerResult=[ordered]@{PlanSHA256=$State.PlanSHA256;Identity=$State.Identity;ExitCode=$Snapshot.RootExitCode;
        CompilerSHA256=$policy.CompilerSHA256;BoundInputsVerified=@($Plan.Bindings).Count}
    Assert-H1Deadline $Started $State.DeadlineSeconds
    $first=Get-H1OriginalMembers $Context.Owner
    $evidence.BeforeStopFirst=$first
    $firstMember=Assert-H1TelemetryCapture $first $Snapshot $State.Identity $policy
    Assert-H1Deadline $Started $State.DeadlineSeconds
    Start-Sleep -Milliseconds 50
    $second=Get-H1OriginalMembers $Context.Owner
    $evidence.BeforeStopSecond=$second
    $current=Get-H1OriginalState $Context.Owner
    $evidence.BeforeStopOriginalState=$current
    $secondMember=Assert-H1TelemetryCapture $second $current $State.Identity $policy
    if($firstMember.PID -ne $secondMember.PID -or $firstMember.CreatedUtc -cne $secondMember.CreatedUtc -or
       $firstMember.ParentPID -ne $secondMember.ParentPID -or $firstMember.Image -ine $secondMember.Image -or
       (Get-MaterialV2MemberTime $second.CapturedUtc) -lt (Get-MaterialV2MemberTime $first.CapturedUtc)){
        throw 'Original-job telemetry generation changed between captures.'
    }
    Test-H1Budget $Plan $State
    Assert-H1Deadline $Started $State.DeadlineSeconds
    $evidence.Action='StopOriginalJobAfterVerifiedCompilerAndTelemetry'
    $stopStarted=Get-H1Clock
    Stop-H1OriginalJob $Context.Owner
    while($true) {
        $after=Get-H1OriginalState $Context.Owner
        Assert-H1Deadline $Started $State.DeadlineSeconds
        Assert-H1Deadline $stopStarted 5
        Assert-H1CompilerRoot $after $State.Identity $policy
        if($after.ActiveProcesses -eq 0){
            $members=Get-H1OriginalMembers $Context.Owner
            Assert-H1Deadline $Started $State.DeadlineSeconds
            Assert-H1Deadline $stopStarted 5
            if($members.AssignedCount -ne 0 -or $members.ListedCount -ne 0 -or @($members.Members).Count -ne 0){throw 'Fresh original-job capture is not empty.'}
            $evidence.AfterStop=$after;$evidence.AfterStopMembers=$members;$evidence.Completed=$true
            return $true # Caller MUST obtain another ordinary snapshot before closing.
        }
        Start-Sleep -Milliseconds 20
    }
}

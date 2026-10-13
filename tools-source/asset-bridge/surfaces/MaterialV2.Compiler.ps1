# Local, explicit post-compile telemetry closure. No environment mutation and no
# PID termination; the caller still needs the ordinary zero-active phase gate.
function Get-MaterialV2CompilerPolicy([string]$Compiler) {
    if([IO.Path]::GetFileName($Compiler) -ine 'cl.exe'){throw 'Exact MSVC compiler path required.'}
    [pscustomobject]@{Mode='StopOriginalJobAfterVerifiedCompilerAndTelemetry';
        Compiler=$Compiler;CompilerSHA256='FE251EF50A1545B1B0835EE17B1E785459712B38D79E45B5C1D3D28970A36619';
        Telemetry=(Join-Path (Split-Path $Compiler -Parent) 'vctip.exe');
        TelemetrySHA256='D591358C6AEE4B673562CA3B3A15C250E612708394FE3B44A7A7EDA2470570A5'}
}
function Get-MaterialV2MemberTime([string]$Value) {
    $time=[datetimeoffset]::MinValue
    if(![datetimeoffset]::TryParseExact($Value,'o',[Globalization.CultureInfo]::InvariantCulture,
        [Globalization.DateTimeStyles]::None,[ref]$time) -or $time.Offset -ne [timespan]::Zero -or $time.Year -lt 2000){
        throw 'Exact native member creation timestamp required.'
    }
    $time
}
function Assert-MaterialV2MemberIdentity($Member) {
    if(($Member.PID -isnot [uint32] -and $Member.PID -isnot [int] -and $Member.PID -isnot [long]) -or
       $Member.PID -lt 1 -or $Member.PID -gt [uint32]::MaxValue -or
       $Member.InOriginalJob -isnot [bool] -or !$Member.InOriginalJob -or $Member.Error -or $Member.ParentError -or
       ($Member.ParentPID -isnot [uint32] -and $Member.ParentPID -isnot [int] -and $Member.ParentPID -isnot [long]) -or
       $Member.ParentPID -lt 1 -or !$Member.Image -or ![IO.Path]::IsPathFullyQualified($Member.Image)){
        throw 'Complete original-job member identity required.'
    }
    $null=Get-MaterialV2MemberTime $Member.CreatedUtc
}
function Update-MaterialV2CompilerWitness($Evidence,$Observation,[long]$RootPID,$Policy) {
    $Evidence.LastObservation=$Observation
    $compilers=@($Observation.Members|Where-Object Image -IEQ $Policy.Compiler)
    if($compilers.Count -gt 1){throw 'Multiple compiler identities are not an accepted telemetry closure.'}
    if($compilers.Count -eq 1){
        $compiler=$compilers[0];Assert-MaterialV2MemberIdentity $compiler
        if($compiler.ParentPID -ne $RootPID){throw 'Compiler must be a witnessed direct child of the original root.'}
        if($Evidence.CompilerIdentity -and ($Evidence.CompilerIdentity.PID -ne $compiler.PID -or
           $Evidence.CompilerIdentity.CreatedUtc -cne $compiler.CreatedUtc)){throw 'Compiler generation changed.'}
        $Evidence.CompilerIdentity=$compiler
    }
}
function Complete-MaterialV2CompilerTelemetry($Owner,$Snapshot,$Observation,$Receipt,$Evidence,$Policy) {
    if(!$Snapshot.RootExited -or $Snapshot.ActiveProcesses -eq 0 -or $Evidence.Completed){return $false}
    if($Snapshot.RootExited -isnot [bool] -or
       ($Snapshot.RootExitCode -isnot [uint32] -and $Snapshot.RootExitCode -isnot [int] -and $Snapshot.RootExitCode -isnot [long]) -or
       $Snapshot.RootExitCode -ne 0){throw 'Successful original root required before compiler telemetry closure.'}
    # A valid receipt is necessary, never sufficient to accept a phase.
    if($Receipt.schema -cne 'iw7.material-v2-phase-result/1' -or $Receipt.phase -cne 'compile' -or $Receipt.failure -or
       ($Receipt.exit_code -isnot [int] -and $Receipt.exit_code -isnot [long]) -or $Receipt.exit_code -ne 0 -or
       $Receipt.executable_sha256 -ine $Policy.CompilerSHA256 -or
       ($Receipt.pid -isnot [int] -and $Receipt.pid -isnot [long]) -or !$Evidence.CompilerIdentity -or
       $Receipt.pid -ne $Evidence.CompilerIdentity.PID){throw 'Successful receipt for the independently witnessed compiler required.'}
    if($Snapshot.ActiveProcesses -ne 1 -or $Observation.AssignedCount -ne 1 -or
       $Observation.ListedCount -ne 1 -or @($Observation.Members).Count -ne 1){throw 'Exactly one verified telemetry member must remain.'}
    $member=@($Observation.Members)[0];Assert-MaterialV2MemberIdentity $member
    if($member.Image -ine $Policy.Telemetry -or $member.ParentPID -ne $Evidence.CompilerIdentity.PID -or
       (Get-MaterialV2MemberTime $member.CreatedUtc) -lt (Get-MaterialV2MemberTime $Evidence.CompilerIdentity.CreatedUtc) -or
       (Get-MaterialV2MemberTime $member.CreatedUtc) -gt (Get-MaterialV2MemberTime $Observation.CapturedUtc)){
        throw 'Residual identity is not the exact witnessed compiler telemetry child.'
    }
    Assert-BeaconHash $Policy.Compiler $Policy.CompilerSHA256
    Assert-BeaconHash $Policy.Telemetry $Policy.TelemetrySHA256
    $Evidence.BeforeStop=$Observation;$Evidence.NativeReceipt=$Receipt;$Evidence.Cleanup=[ordered]@{}
    $Evidence.Action='StopOriginalJobAfterVerifiedCompilerAndTelemetry'
    if(!(Stop-MaterialV2OwnedPhase $Owner $Evidence.Cleanup)){throw 'Compiler telemetry original-job closure remains unconfirmed.'}
    $Evidence.Completed=$true
    # The caller resumes normal supervision and records a FRESH exit0/Active0
    # snapshot, then validates the native receipt again before accepting output.
    return $true
}

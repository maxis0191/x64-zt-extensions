# Pure world adapter gates. Importing this file starts nothing.
function Get-WorldObserverBudgets {
    [ordered]@{PhysicalBytes=4GB;CommitBytes=6GB;OutputBytes=64MB;LiveOutputBytes=63MB;
        StreamBytes=2MB;CompileMs=90000L;FixtureMs=10000L;GroupMs=120000L;SupervisorSeconds=240}
}
function Assert-WorldObserverTime([long]$ElapsedMs,[string]$Phase,[long]$PhaseElapsedMs) {
    $b=Get-WorldObserverBudgets
    if($ElapsedMs -lt 0 -or $PhaseElapsedMs -lt 0 -or $ElapsedMs -ge $b.GroupMs){throw 'World group deadline reached (120 seconds).'}
    $limit=switch -CaseSensitive ($Phase){'compile'{$b.CompileMs};'fixture'{$b.FixtureMs};default{throw 'Unknown world phase.'}}
    if($PhaseElapsedMs -ge $limit){throw "World $Phase deadline reached."}
}
function Assert-WorldObserverPollTime($State,[long]$StartedMs,[long]$NowMs,[long]$GroupStartedMs=$StartedMs) {
    $phase=if($null -eq $State.FixtureStartedMs){'compile'}else{'fixture'}
    $phaseStart=if($null -eq $State.FixtureStartedMs){$StartedMs}else{$State.FixtureStartedMs}
    Assert-WorldObserverTime ($NowMs-$GroupStartedMs) $phase ($NowMs-$phaseStart)
}
function Resolve-WorldObserverPath([string]$Path) {
    if($Path -notmatch '^[A-Za-z]:[\\/]' -or $Path.Substring(2) -match '[:"<>|?*\x00-\x1f]' -or
       $Path -match '(^|[\\/])(?:\.\.?|[^\\/]*[. ])([\\/]|$)'){throw 'Unambiguous absolute local path required.'}
    foreach($part in $Path.Substring(3) -split '[\\/]'){
        if($part -match '^(?i:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\.|$)'){throw 'Reserved Windows device path refused.'}
    }
    $full=[IO.Path]::GetFullPath($Path).TrimEnd('\','/')
    Resolve-IW7BasePath (Split-Path $full -Parent) (Split-Path $full -Leaf)
}
function Assert-WorldObserverPins($Entries) {
    foreach($entry in $Entries){
        $null=Resolve-WorldObserverPath $entry.Path
        Assert-BeaconHash $entry.Path $entry.SHA256
    }
}
function Measure-WorldObserverOutput([string]$Root,[switch]$Final) {
    $count=0;$bytes=0L
    foreach($file in Get-ChildItem -LiteralPath $Root -Recurse -Force){
        if(++$count -gt 4096 -or ($file.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'World output inventory bound or redirect.'}
        if(!$file.PSIsContainer){$bytes+=$file.Length}
    }
    Assert-WorldObserverOutput $bytes -Final:$Final
    $bytes
}
function Assert-WorldObserverOutput([long]$Bytes,[switch]$Final) {
    $b=Get-WorldObserverBudgets;$limit=if($Final){$b.OutputBytes}else{$b.LiveOutputBytes}
    if($Bytes -lt 0 -or $Bytes -gt $limit){throw 'World output budget exceeded.'}
}
function Write-WorldObserverJson([string]$Path,$Value) {
    # Publish complete small protocol files only. Never overwrite a prior receipt.
    $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($Value|ConvertTo-Json -Depth 20))
    if($bytes.Length -gt 512KB){throw 'World JSON receipt bound.'}
    $temporary=$Path+'.pending'
    $stream=[IO.File]::Open($temporary,'CreateNew','Write','None')
    try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
    [IO.File]::Move($temporary,$Path)
}
function Write-WorldObserverFinalReceipt([string]$Root,$State) {
    $before=Measure-WorldObserverOutput $Root
    $State.FinalBytes=$before
    $stable=$false
    for($pass=0;$pass -lt 4;$pass++){
        $serialized=[Text.UTF8Encoding]::new($false).GetBytes(($State|ConvertTo-Json -Depth 20))
        $next=$before+$serialized.Length
        if($next -eq $State.FinalBytes){$stable=$true;break}
        $State.FinalBytes=$next
    }
    if(!$stable){throw 'Final world byte accounting did not converge.'}
    Assert-WorldObserverOutput $State.FinalBytes -Final
    Write-WorldObserverJson (Join-Path $Root 'run.json') $State
    if((Measure-WorldObserverOutput $Root -Final) -ne $State.FinalBytes){throw 'Final world receipt byte accounting differs.'}
}
function Complete-WorldObserverReservation([string]$Root,$State,$Lease,$Guards,[scriptblock]$BeforeReleaseCheck) {
    # The immutable file is an explicitly BEFORE-release snapshot. The returned
    # state alone reports the subsequent scheduler outcome; no file write after
    # release is required to qualify the already published/accounted evidence.
    if($State.LeaseReleased -or $State.LeaseReleaseState -in 'Confirmed','Unconfirmed'){throw 'Never retry a confirmed or ambiguous lease release.'}
    $State.LeaseReleased=$false;$State.RetainedLeaseToken=$Lease.Token
    $State.LeaseReleaseState='NotAttempted';$State.ReceiptStage='BeforeLeaseRelease'
    $State.FinalReceiptVerified=$false;$State.FinalizationFailure=$null
    $attempted=$false
    try {
        if($State.JobClosureVerified -isnot [bool] -or !$State.JobClosureVerified -or
           $State.SourceHashesUnchanged -isnot [bool] -or !$State.SourceHashesUnchanged){throw 'Closure and source integrity required before finalization/release.'}
        if($State.Status -ceq 'SyntheticHarnessPassed'){$State.Status='SyntheticHarnessValidatedLeaseHeld'}
        Write-WorldObserverFinalReceipt $Root $State
        $path=Join-Path $Root 'run.json'
        $guard=[IO.File]::Open($path,'Open','Read','Read');$Guards.Add($guard)
        $expected=[Text.UTF8Encoding]::new($false).GetBytes(($State|ConvertTo-Json -Depth 20))
        $expectedHash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($expected))
        $actualHash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($guard))
        if($guard.Length -ne $expected.Length -or $actualHash -cne $expectedHash -or
           (Measure-WorldObserverOutput $Root -Final) -ne $State.FinalBytes){throw 'Published final receipt/accounting verification failed.'}
        $State.FinalReceiptVerified=$true;$State.FinalReceiptSHA256=$actualHash
        if($BeforeReleaseCheck){& $BeforeReleaseCheck}
        $attempted=$true;$State.LeaseReleaseState='Unconfirmed'
        Exit-IW7ResourceLease -Token $Lease.Token
        $State.LeaseReleased=$true;$State.RetainedLeaseToken=$null;$State.LeaseReleaseState='Confirmed'
        if($State.Status -ceq 'SyntheticHarnessValidatedLeaseHeld'){$State.Status='SyntheticHarnessPassed'}
    } catch {
        $State.Status='Failed';$State.FinalizationFailure=$_.Exception.Message
        # A throwing release may have changed the registry: preserve the token
        # for reconciliation and say unconfirmed, never assert it stayed held.
        $State.LeaseReleaseState=if($attempted){'Unconfirmed'}else{'NotAttempted'}
        throw
    }
}
function Assert-WorldObserverCompileReceipt($Receipt,$Witness,$Policy) {
    if($Receipt.schema -cne 'iw7.material-v2-phase-result/1' -or $Receipt.phase -cne 'compile' -or
       $Receipt.failure -or ($Receipt.exit_code -isnot [long] -and $Receipt.exit_code -isnot [int]) -or
       $Receipt.exit_code -ne 0 -or $Receipt.executable_sha256 -ine $Policy.CompilerSHA256 -or
       !$Witness.CompilerIdentity -or ($Receipt.pid -isnot [long] -and $Receipt.pid -isnot [int]) -or
       $Receipt.pid -ne $Witness.CompilerIdentity.PID){throw 'Successful independently witnessed world compiler receipt required.'}
}
function Get-WorldObserverConsolePolicy {
    # Reviewed Windows 10.0.26100.1 catalog-signed image; updates fail closed.
    [pscustomobject]@{Image=(Join-Path ([Environment]::SystemDirectory) 'conhost.exe');
        SHA256='E449BCE01F275CD08F3D4E64BB73B3B43AE845A0DBDB3E6131426E66537705E5';
        SignerSubject='CN=Microsoft Windows, O=Microsoft Corporation, L=Redmond, S=Washington, C=US';
        SignerThumbprint='BAC13DF18B37E808208A39D3A54CCE975FAC8C1D'}
}
function Assert-WorldObserverConsoleSignature($Signature,$Policy) {
    if($Signature.Path -ine $Policy.Image -or $Signature.Status.ToString() -cne 'Valid' -or
       !$Signature.SignerCertificate -or $Signature.SignerCertificate.Subject -cne $Policy.SignerSubject -or
       $Signature.SignerCertificate.Thumbprint -ine $Policy.SignerThumbprint){throw 'Pinned Microsoft Windows console-host signature required.'}
}
function Assert-WorldObserverConsoleMember($Member,$Root,$Observation,$Policy) {
    Assert-MaterialV2MemberIdentity $Member
    if($Member.Image -ine $Policy.Image -or $Member.ParentPID -ne $Root.PID -or $Member.PID -eq $Root.PID -or
       (Get-MaterialV2MemberTime $Member.CreatedUtc) -lt (Get-MaterialV2MemberTime $Root.CreatedUtc) -or
       (Get-MaterialV2MemberTime $Member.CreatedUtc) -gt (Get-MaterialV2MemberTime $Observation.CapturedUtc)){
        throw 'Exact same-job direct-root console-host identity required.'
    }
}
function Update-WorldObserverConsoleWitness($Evidence,$Observation,$Root,$Policy) {
    $members=@($Observation.Members|Where-Object Image -IEQ $Policy.Image)
    if($members.Count -gt 1){throw 'At most one console-host generation is permitted.'}
    if($members.Count -eq 0){return}
    $member=$members[0];Assert-WorldObserverConsoleMember $member $Root $Observation $Policy
    if($Evidence.Identity -and ($Evidence.Identity.PID -ne $member.PID -or
       $Evidence.Identity.CreatedUtc -cne $member.CreatedUtc -or $Evidence.Identity.Image -ine $member.Image)){
        throw 'Console-host generation changed.'
    }
    if(!$Evidence.Identity){
        $Evidence.Identity=[pscustomobject]@{PID=$member.PID;Image=$member.Image;CreatedUtc=$member.CreatedUtc;
            ParentPID=$member.ParentPID;InOriginalJob=$true;Error=$null;ParentError=$null}
    }
}
function Assert-WorldObserverMembers($Observation,$Root,$Witness,$Policy,$ConsoleWitness,$ConsolePolicy,[switch]$RootExited) {
    $members=@($Observation.Members)
    $maximum=if($RootExited){2}else{3}
    if($members.Count -lt 1 -or $members.Count -gt $maximum -or $Observation.AssignedCount -ne $members.Count -or
       $Observation.ListedCount -ne $members.Count){throw 'Complete root/console/telemetry membership required.'}
    $roots=@($members|Where-Object PID -EQ $Root.PID)
    if($roots.Count -ne $(if($RootExited){0}else{1})){throw 'Original root presence differs from world gate.'}
    $seen=[Collections.Generic.HashSet[long]]::new();$consoles=0;$telemetry=0
    foreach($member in $members){
        Assert-MaterialV2MemberIdentity $member
        if(!$seen.Add($member.PID)){throw 'Duplicate original-job member identity.'}
        if($member.PID -eq $Root.PID){
            if($member.Image -ine $Root.Image -or $member.CreatedUtc -cne $Root.CreatedUtc){throw 'Original root generation changed.'}
        }elseif($member.Image -ieq $ConsolePolicy.Image){
            Assert-WorldObserverConsoleMember $member $Root $Observation $ConsolePolicy
            if(++$consoles -gt 1 -or !$ConsoleWitness.Identity -or $ConsoleWitness.Identity.PID -ne $member.PID -or
               $ConsoleWitness.Identity.CreatedUtc -cne $member.CreatedUtc -or $ConsoleWitness.Identity.Image -ine $member.Image){
                throw 'Previously witnessed single console-host generation required.'
            }
        }elseif($member.Image -ieq $Policy.Telemetry){
            if(++$telemetry -gt 1 -or $member.ParentPID -ne $Witness.CompilerIdentity.PID -or
               (Get-MaterialV2MemberTime $member.CreatedUtc) -lt (Get-MaterialV2MemberTime $Witness.CompilerIdentity.CreatedUtc) -or
               (Get-MaterialV2MemberTime $member.CreatedUtc) -gt (Get-MaterialV2MemberTime $Observation.CapturedUtc)){
                throw 'Exact single compiler telemetry child required.'
            }
        }else{
            throw 'Unrecognized world job member.'
        }
    }
}
function Assert-WorldObserverAdvance($Observation,$Root,$Witness,$Receipt,$Policy,$ConsoleWitness,$ConsolePolicy) {
    Assert-WorldObserverCompileReceipt $Receipt $Witness $Policy
    Assert-WorldObserverMembers $Observation $Root $Witness $Policy $ConsoleWitness $ConsolePolicy
}
function Complete-WorldObserverResiduals($Owner,$Snapshot,$Observation,$Receipt,$Witness,$Policy,$Root,$ConsoleWitness,$ConsolePolicy) {
    if(!$Snapshot.RootExited -or $Snapshot.ActiveProcesses -eq 0 -or $ConsoleWitness.Completed){return $false}
    if($Snapshot.RootExited -isnot [bool] -or
       ($Snapshot.RootExitCode -isnot [uint32] -and $Snapshot.RootExitCode -isnot [int] -and $Snapshot.RootExitCode -isnot [long]) -or
       $Snapshot.RootExitCode -ne 0 -or $Snapshot.ActiveProcesses -ne @($Observation.Members).Count){
        throw 'Successful original root and complete residual membership required.'
    }
    Assert-WorldObserverCompileReceipt $Receipt $Witness $Policy
    Assert-WorldObserverMembers $Observation $Root $Witness $Policy $ConsoleWitness $ConsolePolicy -RootExited
    if(@($Observation.Members|Where-Object Image -IEQ $ConsolePolicy.Image).Count -eq 0){
        # Reuse the existing telemetry closer with the COMPLETE observation.
        return (Complete-MaterialV2CompilerTelemetry $Owner $Snapshot $Observation $Receipt $Witness $Policy)
    }
    Assert-BeaconHash $Policy.Compiler $Policy.CompilerSHA256
    Assert-BeaconHash $Policy.Telemetry $Policy.TelemetrySHA256
    Assert-BeaconHash $ConsolePolicy.Image $ConsolePolicy.SHA256
    $ConsoleWitness.BeforeStop=$Observation;$ConsoleWitness.Cleanup=[ordered]@{}
    $ConsoleWitness.Action='StopOriginalJobAfterVerifiedRootAndConsoleMembers'
    if(!(Stop-MaterialV2OwnedPhase $Owner $ConsoleWitness.Cleanup)){throw 'World residual original-job closure remains unconfirmed.'}
    $ConsoleWitness.Completed=$true
    # Reused supervisor must subsequently observe fresh original root0/Active0.
    return $true
}
function Assert-WorldObserverClosed($Identity) {
    if($Identity.JobRootExitedAtClose -isnot [bool] -or !$Identity.JobRootExitedAtClose -or
       ($Identity.JobActiveAtClose -isnot [uint32] -and $Identity.JobActiveAtClose -isnot [int] -and $Identity.JobActiveAtClose -isnot [long]) -or
       $Identity.JobActiveAtClose -ne 0 -or
       ($Identity.ExitCode -isnot [uint32] -and $Identity.ExitCode -isnot [int] -and $Identity.ExitCode -isnot [long]) -or
       $Identity.ExitCode -ne 0){throw 'Fresh original root0/Active0 required.'}
}
function Get-WorldObserverCompilerArguments([string]$VC,[string]$SDK,[string]$Version,[string]$World,[string]$RunRoot) {
    if($Version -cnotmatch '^10\.0\.\d+\.0$'){throw 'Exact Windows SDK version required.'}
    $includes=@((Join-Path $VC 'include'))+@('ucrt','shared','um'|ForEach-Object{Join-Path $SDK "Include/$Version/$_"})
    foreach($path in $includes){$null=Resolve-WorldObserverPath $path;if(!(Test-Path -LiteralPath $path -PathType Container)){throw 'Installed compiler include directory missing.'}}
    @('/nologo','/std:c++20','/EHsc','/MD','/O1','/W4','/D_CRT_SECURE_NO_WARNINGS')+
        @($includes|ForEach-Object{'/I'+$_})+
        @((Join-Path $World 'test_world_clipmap_observer.cpp'),('/Fo'+(Join-Path $RunRoot 'observer.obj')),
          ('/Fe'+(Join-Path $RunRoot 'observer.exe')),('/Fd'+(Join-Path $RunRoot 'observer.pdb')),'/link','/INCREMENTAL:NO',
          ('/LIBPATH:'+(Join-Path $VC 'lib/x64')),('/LIBPATH:'+(Join-Path $SDK "Lib/$Version/ucrt/x64")),
          ('/LIBPATH:'+(Join-Path $SDK "Lib/$Version/um/x64")),'bcrypt.lib')
}

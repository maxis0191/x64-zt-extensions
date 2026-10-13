# World profile only. Dot-source after the pinned H1 core/compiler and T7 profile.
# The original native owner, direct-tool telemetry policy and stage loop stay there.
$script:WorldH1Deadline=$script:T7H1Deadline
$script:WorldH1Budget=$script:T7H1Budget
function Assert-H1Deadline($Started,[int]$Seconds) {
    & $script:WorldH1Deadline $script:WorldGroupStarted 120
    & $script:WorldH1Deadline $Started $Seconds
}
function Get-WorldStageContract {
    [pscustomobject]@{Schema='iw7.world-observer-output-contract/2';Enforcement='Sampled';StrictWriteCap=$false;
        StreamThresholdBytes=2MB;LiveTotalThresholdBytes=63MB;FinalAcceptanceBytes=64MB;
        NominalPollSleepMs=100;MaximumDetectionLatencyMs=$null;MaximumOvershootBytes=$null;
        CompileAndLinkSeconds=90;FixtureSeconds=10;CheckSeconds=5;GroupSeconds=120;CleanupSeconds=5;
        FixtureRecords=24;FixtureRecordBytes=4096;FixtureStdoutExpectedMaximumBytes=98508;
        FixtureSuccessStderr='Original synthetic observer fixture PASS; not engine evidence';
        AcceptedTranscriptBytes=128KB;NativeMeasurementAvailable=$false}
}
function Test-WorldStageStreams($Plan,$State) {
    # Direct files: a sampled threshold, never a claim that writes are capped.
    foreach($stage in $Plan.Stages) {
        foreach($name in 'stdout.log','stderr.log') {
            $path=Join-Path (Join-Path $Plan.RunRoot $stage.Name) $name
            if(!(Test-Path -LiteralPath $path)){continue}
            Assert-H1Path $path
            $bytes=(Get-Item -LiteralPath $path).Length
            $State.MaxObservedStreamBytes=[math]::Max($State.MaxObservedStreamBytes,$bytes)
            if($bytes -gt $Plan.OutputContract.StreamThresholdBytes) {
                $State.StreamThresholdExceeded=[ordered]@{Stage=$stage.Name;Stream=$name;ObservedBytes=$bytes}
                throw 'World sampled stream threshold exceeded; stop the original owned job.'
            }
        }
    }
}
function Test-H1Budget($Plan,$State) {
    Assert-H1Deadline $script:WorldGroupStarted 120
    & $script:WorldH1Budget $Plan $State
    Test-WorldStageStreams $Plan $State
    if(Test-Path -LiteralPath (Join-Path $Plan.RunRoot 'stop.request')){throw 'Coordinator requested World stop.'}
    Assert-H1Deadline $script:WorldGroupStarted 120
}
function Get-H1CompilerArtifacts($Plan,$Context) {
    foreach($name in $script:WorldCurrentStage.Artifacts) {
        $path=Join-Path (Join-Path $Plan.RunRoot $script:WorldCurrentStage.Name) $name
        Assert-H1Path $path
        $file=Get-Item -LiteralPath $path
        if($file.Length -le 0 -or $file.Length -gt 8MB){throw 'Bounded World stage artifact required.'}
        $pin=[pscustomobject]@{Path=$path;Bytes=$file.Length;SHA256=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()}
        $Context.Guards.Add((Open-H1Pin $pin))
        Assert-H1Deadline $script:WorldGroupStarted 120
        $pin
    }
}
function Stop-WorldStageOnFailure($Context,$State) {
    # No lease release here: World publishes its immutable final receipt first.
    if($Context.Closed){return}
    $State.TerminationRequested=$true
    try {
        if(!$Context.Owner){throw 'Original World stage owner unavailable; retain quarantine.'}
        $Context.Owner.StopAndConfirm(5000)
        $Context.Closed=$Context.Owner.Closed
        if(!$Context.Closed){throw 'World stage closure remains unconfirmed.'}
        $State.TreeClosureConfirmed=$true;$State.ExitCode=$Context.Owner.ExitCode
    }catch{$State.CleanupError=$_.Exception.Message}
}
function Invoke-WorldStage($Plan,$State,$Context,$Start,[string]$ImageSHA256,[string]$StageRoot,[double]$Started) {
    if(!$Context.Closed){throw 'Previous World original job remains open.'}
    try {
        Test-H1Budget $Plan $State
        Assert-H1Deadline $Started $State.DeadlineSeconds
        # A throwing factory must not leave the previous closed owner as false
        # evidence about a new creation attempt. The previous stage is closed.
        $Context.Owner=$null
        # Reuse the qualified direct Compile and scoped Link adapter verbatim.
        Invoke-T7OwnedStage $Plan $State $Context $Start $ImageSHA256 $StageRoot $Started
        # A short-lived tool can exceed a threshold between the last poll and
        # exit. Check again before advancing, even though its job is now closed.
        Test-H1Budget $Plan $State
        Assert-H1Deadline $Started $State.DeadlineSeconds
    }catch{
        $State.Failure=$_.Exception.Message
        Stop-WorldStageOnFailure $Context $State
        throw
    }
}
function Get-WorldStages([string]$Compiler,[string]$Python,[string[]]$LegacyArguments,[string]$World,[string]$RunRoot) {
    $split=[array]::IndexOf($LegacyArguments,'/link')
    if($split -lt 1){throw 'Explicit legacy compiler/link boundary required.'}
    $compileRoot=Join-Path $RunRoot 'compile';$linkRoot=Join-Path $RunRoot 'link'
    $obj=Join-Path $compileRoot 'observer.obj';$exe=Join-Path $linkRoot 'observer.exe'
    # Preserve existing flags/includes and the original TU; /c prevents an
    # implicit linker and each tool gets its own direct original-job identity.
    $compile=@($LegacyArguments[0..($split-1)]|Where-Object{$_ -notmatch '^/(Fo|Fe|Fd)'})+
        @('/c',('/Fo'+$obj))
    $link=@('/NOLOGO',('/OUT:'+$exe),$obj)+$LegacyArguments[($split+1)..($LegacyArguments.Count-1)]
    @(
        [pscustomobject]@{Name='compile';Stage='Compile';Image=$Compiler;Arguments=$compile;DeadlineSeconds=90;Artifacts=@('observer.obj')},
        [pscustomobject]@{Name='link';Stage='Link';Image=(Join-Path (Split-Path $Compiler -Parent) 'link.exe');Arguments=$link;DeadlineSeconds=90;Artifacts=@('observer.exe')},
        [pscustomobject]@{Name='fixture';Stage='Fixture';Image=$exe;Arguments=@();DeadlineSeconds=10;Artifacts=@()},
        [pscustomobject]@{Name='check';Stage='Check';Image=$Python;Arguments=@('-I','-S','-B',(Join-Path $World 'check_observer_harness.py'),(Join-Path $RunRoot 'fixture/stdout.log'));DeadlineSeconds=5;Artifacts=@()}
    )
}
function Assert-WorldFixtureOutput($Plan,$Context) {
    $root=Join-Path $Plan.RunRoot 'fixture'
    $stdout=Join-Path $root 'stdout.log';$stderr=Join-Path $root 'stderr.log'
    $output=Get-Item -LiteralPath $stdout
    if($output.Length -le 0 -or $output.Length -gt $Plan.OutputContract.FixtureStdoutExpectedMaximumBytes){throw 'World fixture output exceeds source-derived expected maximum.'}
    if((Get-Item -LiteralPath $stderr).Length -gt 128){throw 'World fixture stderr differs.'}
    $message=[IO.File]::ReadAllText($stderr)
    $expected=$Plan.OutputContract.FixtureSuccessStderr
    if($message -cne ($expected+"`n") -and $message -cne ($expected+"`r`n")){throw 'World fixture success marker required.'}
    $pin=[pscustomobject]@{Path=$stdout;Bytes=$output.Length;SHA256=(Get-FileHash -LiteralPath $stdout).Hash.ToLowerInvariant()}
    $Context.Guards.Add((Open-H1Pin $pin))
    $pin
}

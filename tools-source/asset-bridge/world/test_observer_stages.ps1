param([Parameter(Mandatory)][string]$StageProviderRoot,[Parameter(Mandatory)][string]$LinkProfilePath)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. "$StageProviderRoot/tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1"
. "$StageProviderRoot/tools-source/asset-bridge/surfaces/MaterialV2.Compiler.ps1"
. "$StageProviderRoot/tools-source/asset-bridge/h1-fixture/H1Native.Compiler.ps1"
. $LinkProfilePath
. "$PSScriptRoot/ObserverStages.Profile.ps1"
$script:tick=0.0;$script:WorldGroupStarted=0.0;$script:checks=0;$script:starts=0;$script:stops=0;$script:case=''
function Check($Value,$Message){if(!$Value){throw $Message};$script:checks++}
function Refuse([scriptblock]$Body,[string]$Match){$caught=$null;try{& $Body}catch{$caught=$_};Check ($caught -and $caught.Exception.Message -match $Match) ('Expected refusal: '+$Match+'; got '+$caught)}
function Get-H1Clock {$script:tick}
function Start-Sleep([int]$Milliseconds){$script:tick+=$Milliseconds}
function Get-IW7ResourceSnapshot {[pscustomobject]@{CommitLimit=100;Committed=$(if($script:case -ceq 'memory'){86}else{1})}}
function Register-H1Original($Lease,$Identity) {}
function Exit-IW7ResourceLease {throw 'A stage must never release the lease.'}
function Stop-Process {throw 'Never stop by PID/name.'}
function Get-H1OriginalState($Owner){[pscustomobject]@{RootExited=$Owner.Exited;RootExitCode=$Owner.ExitCode;ActiveProcesses=$(if($Owner.Exited){0}else{1})}}
function Resize-TestFile($Path,[long]$Bytes){$f=[IO.File]::Open($Path,'OpenOrCreate','Write','Read');try{$f.SetLength($Bytes)}finally{$f.Dispose()}}
function New-H1Owner {
    if($script:case -ceq 'factory-failure'){throw 'Synthetic factory failure'}
    $owner=[pscustomobject]@{PID=101;Image='';CreationFileTime=([datetime]'2026-10-12T12:00:00Z').ToFileTimeUtc();Closed=$false;Exited=$true;ExitCode=0;Output=''}
    $owner|Add-Member ScriptMethod Start {
        param($Start,$Hash,$Out,$Err)
        $script:starts++;$this.Image=$Start.FileName;$this.Output=$Out
        [IO.File]::WriteAllBytes($Out,[byte[]]@());[IO.File]::WriteAllBytes($Err,[byte[]]@())
        if($script:case -in 'stream','unclosed'){Resize-TestFile $Out (2MB+1);$this.Exited=$false}
        if($script:case -ceq 'total'){Resize-TestFile $Out 1025;$this.Exited=$false}
        if($script:case -ceq 'timeout'){$this.Exited=$false}
        if($script:case -ceq 'group-after-start'){$script:tick=120000;$this.Exited=$false}
        if($script:case -ceq 'nonzero'){$this.ExitCode=7}
        if($script:case -ceq 'stop-request'){[IO.File]::WriteAllText((Join-Path (Split-Path (Split-Path $Out -Parent) -Parent) 'stop.request'),'stop');$this.Exited=$false}
    }
    $owner|Add-Member ScriptMethod TreeExited {
        if($script:case -ceq 'exit-overflow'){Resize-TestFile $this.Output (2MB+1)}
        $this.Exited
    }
    $owner|Add-Member ScriptMethod CloseConfirmed {$this.Closed=$true}
    $owner|Add-Member ScriptMethod StopAndConfirm {
        param($Ms)
        Check ($Ms -eq 5000) 'Cleanup bound changed'
        $script:stops++
        if($script:case -ceq 'unclosed'){throw 'Synthetic unconfirmed closure'}
        $this.Exited=$true;$this.Closed=$true;$this.ExitCode=122
    }
    $owner
}
$root=Join-Path $PSScriptRoot ('.world-stages-test-'+[guid]::NewGuid().ToString('N'))
try {
    [IO.Directory]::CreateDirectory($root)|Out-Null
    $contract=Get-WorldStageContract
    Check (!$contract.StrictWriteCap -and $null -eq $contract.MaximumOvershootBytes -and $null -eq $contract.MaximumDetectionLatencyMs) 'Sampled contract overclaims a cap'
    foreach($script:case in 'success','link-success','stream','unclosed','factory-failure','total','exit-overflow','timeout','group-after-start','nonzero','stop-request','memory') {
        $caseRoot=Join-Path $root $script:case;[IO.Directory]::CreateDirectory($caseRoot)|Out-Null
        $stageRoot=Join-Path $caseRoot 'stage';[IO.Directory]::CreateDirectory($stageRoot)|Out-Null
        $script:tick=0.0;$script:starts=0;$script:stops=0
        $kind=if($script:case -ceq 'link-success'){'Link'}elseif($script:case -ceq 'timeout'){'Fixture'}else{'Compile'}
        $image=if($kind -ceq 'Link'){'C:\Pinned\link.exe'}else{'C:\Pinned\cl.exe'}
        $hash='a364af801a8539e4324d9489313dbf001d959128451fc99a27b24676bbac058f'
        $plan=[pscustomobject]@{RunRoot=$caseRoot;Compiler='C:\Pinned\cl.exe';OutputContract=$contract;OutputLimitBytes=64MB;
            MetadataReserveBytes=1MB;Stages=@([pscustomobject]@{Name='stage'});Bindings=@([pscustomobject]@{Path='C:\Pinned\link.exe';SHA256=$hash})}
        if($script:case -ceq 'total'){$plan.OutputLimitBytes=2048;$plan.MetadataReserveBytes=1024}
        $state=[ordered]@{Stage=$kind;Name='stage';DeadlineSeconds=$(if($kind -ceq 'Fixture'){10}else{90});MaxObservedOutputBytes=0L;
            MaxObservedStreamBytes=0L;TerminationRequested=$false;CompilerTelemetry=[ordered]@{Completed=$false;Action=$null}}
        $context=[pscustomobject]@{Closed=$true;Owner=$null;Lease='retained-test-lease'}
        if($script:case -ceq 'factory-failure'){$context.Owner=[pscustomobject]@{Closed=$true;ExitCode=0}}
        $invoke={Invoke-WorldStage $plan $state $context ([pscustomobject]@{FileName=$image}) $hash $stageRoot 0.0}
        switch($script:case) {
            {$_ -in 'success','link-success'} {& $invoke;Check ($context.Closed -and $state.ExitCode -eq 0 -and $script:starts -eq 1 -and $script:stops -eq 0) 'Qualified stage not reused'}
            'memory' {Refuse $invoke 'Commit high water';Check ($script:starts -eq 0) 'Admission-side threshold launched a child'}
            'unclosed' {Refuse $invoke 'sampled stream';Check (!$context.Closed -and $context.Owner -and $state.CleanupError -and $script:stops -eq 1) 'Unconfirmed owner discarded'}
            'factory-failure' {Refuse $invoke 'factory failure';Check (!$context.Closed -and $null -eq $context.Owner -and $state.CleanupError -and $script:stops -eq 0) 'Previous closed owner incorrectly certified a failed factory'}
            'exit-overflow' {Refuse $invoke 'sampled stream';Check ($context.Closed -and $script:stops -eq 0 -and $state.Failure) 'Final stream sample missed short-lived flood'}
            'nonzero' {Refuse $invoke 'root0';Check ($context.Closed -and $state.ExitCode -eq 7) 'Failed exit accepted'}
            default {Refuse $invoke 'threshold|budget|deadline|World stop';Check ($context.Closed -and $script:stops -eq 1 -and $state.ExitCode -eq 122) 'Threshold/deadline did not close the original job'}
        }
        Check ($context.Lease -ceq 'retained-test-lease') 'Stage modified its lease'
    }
    # Both compilation and direct link are charged against the same 90 s start.
    $script:case='build-deadline';$script:tick=90000.0;$script:starts=0
    $state.Stage='Link';$state.DeadlineSeconds=90;$context.Closed=$true
    Refuse {Invoke-WorldStage $plan $state $context ([pscustomobject]@{FileName='C:\Pinned\link.exe'}) $hash $stageRoot 0.0} 'deadline'
    Check ($script:starts -eq 0) 'Link received a fresh 90 second budget'
    $script:tick=0.0;$context.Closed=$false
    Refuse {Invoke-WorldStage $plan $state $context ([pscustomobject]@{FileName='C:\Pinned\link.exe'}) $hash $stageRoot 0.0} 'Previous'
    Check ($script:starts -eq 0) 'Unclosed prior job overwritten'
    $script:case='boundary';$plan.OutputLimitBytes=64MB;$plan.MetadataReserveBytes=1MB
    foreach($name in 'stdout.log','stderr.log') {
        Resize-TestFile (Join-Path $stageRoot $name) 2MB
        Test-WorldStageStreams $plan $state
        Resize-TestFile (Join-Path $stageRoot $name) (2MB+1)
        Refuse {Test-WorldStageStreams $plan $state} 'sampled stream'
        Check ($state.StreamThresholdExceeded.Stream -ceq $name) 'Wrong stream threshold evidence'
        Resize-TestFile (Join-Path $stageRoot $name) 0
    }
    $fixtureRoot=Join-Path $plan.RunRoot 'fixture';[IO.Directory]::CreateDirectory($fixtureRoot)|Out-Null
    Resize-TestFile (Join-Path $fixtureRoot 'stdout.log') $contract.FixtureStdoutExpectedMaximumBytes
    $capture=[pscustomobject]@{Guards=[Collections.Generic.List[IDisposable]]::new()}
    foreach($ending in "`n","`r`n") {
        [IO.File]::WriteAllText((Join-Path $fixtureRoot 'stderr.log'),$contract.FixtureSuccessStderr+$ending)
        $pin=Assert-WorldFixtureOutput $plan $capture
        Check ($pin.Bytes -eq 98508) 'Expected fixture envelope changed'
        Refuse {$f=[IO.File]::Open($pin.Path,'Open','Write','ReadWrite');$f.Dispose()} 'another process|access'
        foreach($guard in $capture.Guards){$guard.Dispose()};$capture.Guards.Clear()
    }
    Resize-TestFile (Join-Path $fixtureRoot 'stdout.log') 98509
    Refuse {Assert-WorldFixtureOutput $plan $capture} 'expected maximum'
    Resize-TestFile (Join-Path $fixtureRoot 'stdout.log') 1
    [IO.File]::WriteAllText((Join-Path $fixtureRoot 'stderr.log'),'')
    Refuse {Assert-WorldFixtureOutput $plan $capture} 'success marker'
    [ordered]@{Checks=$script:checks;Passed=$true;NativeTypesLoaded=$false;NativeChildrenStarted=0;LeaseAcquired=$false}|ConvertTo-Json
}finally {
    $full=[IO.Path]::GetFullPath($root);$base=[IO.Path]::GetFullPath($PSScriptRoot)+[IO.Path]::DirectorySeparatorChar
    if(!$full.StartsWith($base,[StringComparison]::OrdinalIgnoreCase)){throw 'Test cleanup escaped World directory.'}
    if(Test-Path -LiteralPath $full){Remove-Item -LiteralPath $full -Recurse -Force}
}

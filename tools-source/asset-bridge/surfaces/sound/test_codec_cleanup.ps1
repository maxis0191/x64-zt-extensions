$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Invoke-SoundCodec.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Codec syntax failed.'}
$outer=@($ast.EndBlock.Statements|Where-Object {$_ -is [Management.Automation.Language.TryStatementAst]})
if($outer.Count -ne 1){throw 'Expected one top-level lifecycle try/finally.'}
$text=$outer[0].Finally.Extent.Text
$cleanup=[scriptblock]::Create($text.Substring(1,$text.Length-2))

function Test-CodecCleanup([string]$Case) {
    # Run the actual finally body with plain mock objects. No Add-Type, scheduler,
    # BuildJob, reservation, child process or real file handle is created.
    $events=[Collections.Generic.List[string]]::new()
    $owner=[pscustomobject]@{Events=$events;Case=$Case;Exited=$true;ExitCode=0}
    $owner|Add-Member ScriptMethod Stop {$this.Events.Add('Stop')}
    $owner|Add-Member ScriptProperty Active {
        if($this.Case -eq 'UnknownClosure'){throw 'Mock original job query failed'}
        return 0
    }
    $owner|Add-Member ScriptMethod Dispose {
        $this.Events.Add('JobDispose')
        if($this.Case -eq 'DisposeFailure'){throw 'Mock job dispose failed'}
    }
    $guard=[pscustomobject]@{Events=$events}
    $guard|Add-Member ScriptMethod Dispose {$this.Events.Add('GuardDispose')}
    $guards=@($guard);$lease=[pscustomobject]@{Token='mock-retained-token'}
    $closed=($Case -ne 'UnknownClosure');$intact=$true;$created=$true
    $PlanPath='mock-plan';$PlanSHA256='mock-hash'
    $plan=[pscustomobject]@{HashInputs=@([pscustomobject]@{Path='mock-input'})}
    $state=[ordered]@{Status='ThirdPartyPCMVerified';Failure=$null;Cleanup=$null;
        RetainedLeaseToken=$lease.Token;JobClosed=$false;JobDisposeCompleted=$false;
        InputHashesMatch=$false;InputsUnchanged=$false;ReadGuardsReleased=$false;
        Quarantined=$false;ExternalDecoderVerified=$false}
    function Assert-CodecHash($Entry){if($Case -eq 'InputMismatch'){throw 'Mock input drift'}}
    function Get-FileHash {param($LiteralPath);[pscustomobject]@{Hash='mock-hash'}}
    function Save-CodecState {}
    function Measure-CodecOutputs {}
    function Exit-IW7ResourceLease {param($Token)
        $events.Add('LeaseRelease')
        if($Case -eq 'LeaseFailure'){throw 'Mock lease release failure'}
    }
    $thrown=$null
    try{& $cleanup}catch{$thrown=$_.Exception.Message}
    if(($null -ne $thrown) -ne ($Case -eq 'LeaseFailure')){throw "Unexpected cleanup exception in $Case : $thrown"}
    if($events.IndexOf('JobDispose') -lt 0 -or $events.IndexOf('GuardDispose') -le $events.IndexOf('JobDispose')){
        throw "Input guard released before job disposal attempt: $Case"
    }
    if(!$state.ReadGuardsReleased){throw "Released guards unreported: $Case"}
    if($Case -eq 'Success'){
        if(!$state.ExternalDecoderVerified -or !$state.InputsUnchanged -or $state.Quarantined -or $state.RetainedLeaseToken){throw 'Valid closure was not accepted.'}
    }else{
        if($state.ExternalDecoderVerified -or !$state.Quarantined -or $state.Status -ne 'Failed' -or !$state.RetainedLeaseToken){throw "Failed cleanup escaped quarantine: $Case"}
        if($Case -ne 'LeaseFailure' -and $state.InputsUnchanged){throw "Unknown integrity was qualified: $Case"}
        if($Case -ne 'LeaseFailure' -and $events.Contains('LeaseRelease')){throw "Unproven cleanup released lease: $Case"}
    }
    if($Case -eq 'UnknownClosure' -and ($state.JobClosed -or !$state.InputHashesMatch -or !$events.Contains('Stop'))){
        throw 'Unknown closure must distinguish matching hashes from qualified integrity.'
    }
    if($Case -eq 'DisposeFailure' -and $state.JobDisposeCompleted){throw 'Failed disposal was accepted.'}
}

foreach($case in 'Success','UnknownClosure','DisposeFailure','InputMismatch','LeaseFailure'){Test-CodecCleanup $case}
if(('IW7.CommunityBuild.BuildJob' -as [type]) -or ('IW7ResourceMemoryV1' -as [type])){throw 'Native classes unexpectedly loaded.'}
'5 actual-finally cleanup cases passed with mocks; no native classes, reservation or codec launched.'

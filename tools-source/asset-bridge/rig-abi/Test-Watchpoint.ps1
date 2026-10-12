$ErrorActionPreference='Stop'
. "$PSScriptRoot/Watchpoint.Core.ps1"
$script:cases=0
function Check($Condition,[string]$Message){if(!$Condition){throw $Message}}
function Fixture {
    $script:tick=0L;$script:calls=[Collections.Generic.List[string]]::new();$script:poll=0
    $script:slowExit=0L;$script:stopFails=$false
    $script:job=[pscustomobject]@{Done=$false;Count=1;Code=122;ResumeCount=0;StopCount=0;Disposed=$false}
    $script:job|Add-Member ScriptProperty Exited {$this.Done}
    $script:job|Add-Member ScriptProperty Active {$this.Count}
    $script:job|Add-Member ScriptProperty ExitCode {$script:tick+=$script:slowExit;return $this.Code}
    $script:job|Add-Member ScriptMethod Resume {$this.ResumeCount++;$script:calls.Add('Resume')}
    $script:job|Add-Member ScriptMethod Stop {
        $this.StopCount++;$script:calls.Add('Stop')
        if($script:stopFails){throw 'synthetic original Stop failure'}
        $this.Done=$true;$this.Count=0
    }
    $script:job|Add-Member ScriptMethod Dispose {$this.Disposed=$true;$script:calls.Add('Dispose')}
    $script:watch=[pscustomobject]@{Due=240000L;StopAttempted=$false;Closed=$false}
    $script:watch|Add-Member ScriptMethod Tighten {param($due) $this.Due=$due;$script:calls.Add('Tighten')}
    $script:watch|Add-Member ScriptMethod RequestStop {$this.StopAttempted=$true;$script:job.Stop()}
    $script:watch|Add-Member ScriptMethod CloseAfterJobClosed {$this.Closed=$true;$script:calls.Add('Disarm')}
    $script:hooks=[ordered]@{
        Now={return $script:tick}
        Acquire={param($state,$physical,$commit) Check ($physical -eq 10GB -and $commit -eq 14GB) 'Incomplete budget';$script:calls.Add('Acquire');[pscustomobject]@{Token='synthetic-lease'}}
        Stage={param($state) $script:calls.Add('Stage')}
        Prepare={param($state) $script:calls.Add('Prepare');return $script:job}
        Identity={param($state) [pscustomobject]@{OriginalHandles=$true;PID=100;CreationUtc='synthetic'}}
        Deadline={param($owner,$due) $script:watch.Due=$due;$script:calls.Add('Deadline');return $script:watch}
        Register={param($state) $script:calls.Add('Register')}
        Poll={param($state) $script:poll++;[pscustomobject]@{Nonce=$state.Nonce;Healthy=$true;Bytes=42;Status=$(if($script:poll -eq 1){'ArmedStopped'}else{'CaptureStopped'});IdentityChecked=$true;BreakpointChecked=$true}}
        Continue={param($state) $script:calls.Add('Continue')}
        Seal={param($state) [pscustomobject]@{Nonce=$state.Nonce;SHA256=('a'*64);Bytes=42;WitnessParsed=$true;FixtureOnly=$true}}
        Budget={param($state)}
        Save={param($state)}
        VerifySources={param($state) $script:calls.Add('VerifySources')}
        Restore={param($state) $script:calls.Add('Restore');return $true}
        Release={param($state) $script:calls.Add('Release');return $true}
        Quarantine={param($state) $script:calls.Add('Quarantine')}
        Delay={$script:tick+=100L}
    }
}
function RunCase([string]$Name,[scriptblock]$Edit,[scriptblock]$Verify){
    Fixture;& $Edit
    $state=Invoke-RigWatchTransaction $script:hooks (New-RigWatchState ('b'*32))
    & $Verify $state
    $script:cases++;Write-Output "PASS $Name"
}
RunCase 'capture stop restores; forced root exit stays 122' {} {
    param($s)
    Check ($s.DiagnosticCaptured -and $s.Closed -and $s.Restored -and $s.LeaseReleased) 'Capture closure failed'
    Check (!$s.RuntimeReady -and !$s.FFVerified -and !$s.SemanticAccepted) 'Diagnostic became acceptance'
    Check ($s.Snapshot.RootExitCode -eq 122 -and $script:job.StopCount -eq 1) 'Original forced exit lost'
    Check ($script:calls.IndexOf('Deadline') -lt $script:calls.IndexOf('Resume')) 'Deadline armed late'
    Check ($script:calls.IndexOf('Tighten') -lt $script:calls.IndexOf('Continue')) 'Armed deadline set late'
    Check ($script:calls.IndexOf('Dispose') -lt $script:calls.IndexOf('Restore')) 'Restored before close'
}
RunCase 'slow acquisition cannot reset clock at Resume' {$script:hooks.Acquire={param($s,$p,$c) $script:tick=240000L;[pscustomobject]@{Token='synthetic-lease'}}} {
    param($s) Check (!$s.DiagnosticCaptured -and $script:job.ResumeCount -eq 0 -and $s.LeaseReleased) 'Late admission escaped deadline'
}
RunCase 'factory failure quarantines unknown ownership' {$script:hooks.Prepare={throw 'factory failed'}} {
    param($s) Check ($s.Quarantined -and !$s.Closed -and !$s.Restored -and !$s.LeaseReleased) 'Unknown factory inferred closed'
}
RunCase 'identity failure recovers suspended original job' {$script:hooks.Identity={throw 'identity failed'}} {
    param($s) Check (!$s.DiagnosticCaptured -and $s.Closed -and $script:job.ResumeCount -eq 0 -and $s.Restored) 'Suspended recovery failed'
}
RunCase 'slow identity cannot resume' {$script:hooks.Identity={$script:tick=240001L;[pscustomobject]@{OriginalHandles=$true}}} {
    param($s) Check (!$s.DiagnosticCaptured -and $script:job.ResumeCount -eq 0) 'Late identity resumed root'
}
RunCase 'missing real breakpoint refuses continuation' {$script:hooks.Poll={param($s) [pscustomobject]@{Nonce=$s.Nonce;Healthy=$true;Bytes=1;Status='ArmedStopped';IdentityChecked=$true;BreakpointChecked=$false}}} {
    param($s) Check (!$s.DiagnosticCaptured -and !$s.Continued -and $s.Closed) 'Unconfirmed breakpoint resumed'
}
RunCase 'capture before continuation refused' {$script:hooks.Poll={param($s) [pscustomobject]@{Nonce=$s.Nonce;Healthy=$true;Bytes=1;Status='CaptureStopped'}}} {
    param($s) Check (!$s.DiagnosticCaptured -and !$s.Capture) 'Unsolicited capture accepted'
}
RunCase 'foreign transport nonce refused' {$script:hooks.Poll={[pscustomobject]@{Nonce=('c'*32);Healthy=$true;Bytes=1;Status='Loading'}}} {
    param($s) Check (!$s.DiagnosticCaptured -and $s.Failure -like '*Unhealthy*') 'Foreign event accepted'
}
RunCase 'EOF never passes as silence' {$script:hooks.Poll={param($s) [pscustomobject]@{Nonce=$s.Nonce;Healthy=$true;Bytes=1;Status='EOF'}}} {
    param($s) Check (!$s.DiagnosticCaptured -and $s.Closed -and $s.Restored) 'EOF became capture'
}
RunCase 'drain failure is fatal' {$script:hooks.Poll={param($s) [pscustomobject]@{Nonce=$s.Nonce;Healthy=$false;Bytes=1;Status='Loading'}}} {
    param($s) Check (!$s.DiagnosticCaptured -and $s.Closed) 'Drain failure accepted'
}
RunCase 'slow seal misses armed deadline' {$script:hooks.Seal={param($s) $script:tick+=10001L;[pscustomobject]@{Nonce=$s.Nonce;SHA256=('a'*64);Bytes=1;WitnessParsed=$true}}} {
    param($s) Check (!$s.DiagnosticCaptured -and $s.Failure -like '*deadline*') 'Slow seal accepted'
}
RunCase 'slow exit getter misses cleanup deadline despite Active0' {$script:slowExit=30001L} {
    param($s) Check ($s.Quarantined -and !$s.Restored -and !$s.LeaseReleased -and !$s.DiagnosticCaptured) 'Late Active0 accepted'
}
RunCase 'slow cleanup save misses deadline before acceptance' {$script:hooks.Save={param($s) if($null -ne $s.CleanupDueMs){$script:tick+=30001L}}} {
    param($s) Check ($s.Quarantined -and !$s.Restored -and !$s.LeaseReleased) 'Slow save escaped closure deadline'
}
RunCase 'original Stop error retains ownership' {$script:stopFails=$true} {
    param($s) Check ($s.Quarantined -and !$s.Closed -and !$s.LeaseReleased) 'Stop failure released lease'
}
RunCase 'source drift prevents restoration' {$script:hooks.VerifySources={throw 'source drift'}} {
    param($s) Check ($s.Closed -and $s.Quarantined -and !$s.Restored -and !$s.LeaseReleased) 'Source drift restored/released'
}
RunCase 'restoration exception retains lease' {$script:hooks.Restore={throw 'restore failed'}} {
    param($s) Check ($s.Closed -and $s.Quarantined -and !$s.LeaseReleased) 'Failed restoration released lease'
}
RunCase 'release exception remains unknown' {$script:hooks.Release={throw 'release failed'}} {
    param($s) Check ($s.Quarantined -and $s.ReleaseAttempted -and !$s.LeaseReleased) 'Release error hidden'
}
RunCase 'late release records actual release without acceptance' {$script:hooks.Release={$script:tick+=30001L;return $true}} {
    param($s) Check ($s.Quarantined -and $s.LeaseReleased -and !$s.DiagnosticCaptured) 'Late released state misreported'
}
RunCase 'persistent stopped debugger reaches global timeout' {$script:hooks.Poll={param($s) [pscustomobject]@{Nonce=$s.Nonce;Healthy=$true;Bytes=1;Status='Loading'}};$script:hooks.Delay={$script:tick+=60000L}} {
    param($s) Check (!$s.DiagnosticCaptured -and $s.Closed -and $s.Restored -and $script:job.StopCount -eq 1) 'Persistent debugger was not recovered'
}
Write-Output "Source-only transaction cases: $script:cases passed; no native types, debugger, fixture or process launched."

# Functions only. No type loading, process creation or resource observation on import.
function New-RigWatchFixtureState([string]$Nonce) {
    if($Nonce -cnotmatch '^[a-f0-9]{32}$'){throw 'Exact session nonce required.'}
    [ordered]@{Schema='iw7.rig-watch-fixture-transaction/1';Mode='fixture';ResourceProfile='iw7.rig-watch-python-cdb-fixture/1';
        PhysicalBytes=4GB;CommitBytes=6GB;MeasuredResourcePeaks=$false;
        Nonce=$Nonce;Status='Preparing';Failure=$null;CleanupFailure=$null;
        StartedMs=$null;LastMs=$null;DueMs=$null;CleanupDueMs=$null;Lease=$null;AcquireAttempted=$false;
        StageStarted=$false;FactoryStarted=$false;Owner=$null;Deadline=$null;Context=[ordered]@{};
        Identity=$null;Snapshot=$null;Capture=$null;Continued=$false;Closed=$false;Restored=$false;
        LeaseReleased=$false;ReleaseAttempted=$false;Quarantined=$false;DiagnosticCaptured=$false;
        RuntimeReady=$false;FFVerified=$false;SemanticAccepted=$false;History=@()}
}
function Get-RigWatchNow($State,$Hooks) {
    $now=& $Hooks.Now
    if(($now -isnot [long] -and $now -isnot [int]) -or $now -lt 0 -or
       ($null -ne $State.LastMs -and $now -lt $State.LastMs)){throw 'Monotonic millisecond clock required.'}
    $State.LastMs=[long]$now
    return [long]$now
}
function Assert-RigWatchTime($State,$Hooks,[switch]$Cleanup) {
    $now=Get-RigWatchNow $State $Hooks
    $due=if($Cleanup){$State.CleanupDueMs}else{$State.DueMs}
    if($now -ge $due){throw $(if($Cleanup){'Watch cleanup deadline exceeded.'}else{'Watch observation deadline exceeded.'})}
    if(!$Cleanup -and $State.Deadline -and $State.Deadline.StopAttempted){throw 'Original-job deadline requested stop.'}
}
function Save-RigWatchCheckpoint($State,$Hooks,[switch]$Cleanup) {
    & $Hooks.Save $State | Out-Null
    Assert-RigWatchTime $State $Hooks -Cleanup:$Cleanup
}
function Get-RigWatchSnapshot($Owner) {
    $exited=$Owner.Exited;$active=$Owner.Active
    if($exited -isnot [bool] -or ($active -isnot [uint32] -and $active -isnot [int] -and $active -isnot [long]) -or $active -lt 0){throw 'Invalid original-handle snapshot.'}
    $code=if($exited){$Owner.ExitCode}else{$null}
    if($exited -and $code -isnot [uint32] -and $code -isnot [int] -and $code -isnot [long]){throw 'Original exit code unavailable.'}
    [pscustomobject]@{RootExited=$exited;Active=$active;RootExitCode=$code}
}
function Assert-RigWatchWorkers($Workers) {
    foreach($name in @('stdout','stderr','stdin')){
        if(!$Workers -or !$Workers.$name -or $Workers.$name.Terminated -isnot [bool] -or
           $Workers.$name.Terminated -or $Workers.$name.Outcome -cne 'running'){
            throw 'Transport worker termination or missing liveness evidence.'
        }
    }
}
function Assert-RigWatchFixtureTransportEvent($Event,$State) {
    if($Event.schema -cne 'iw7.rig-watch-transport/1' -or $Event.FixtureOnly -isnot [bool] -or !$Event.FixtureOnly -or
       $Event.RootPID -ne $State.Identity.PID -or $Event.Nonce -cne $State.Nonce){throw 'Transport identity differs.'}
    if($Event.Status -ceq 'Failed'){
        $State.Context.TransportFailure=$Event
        throw ('Fixture transport failed: '+[string]$Event.Error)
    }
}
function Invoke-RigWatchFixtureTransaction($Hooks,$State) {
    # Fixed fixture-only envelope; no generic/retail budget parameter or fallback.
    if($State.Schema -cne 'iw7.rig-watch-fixture-transaction/1' -or $State.Mode -cne 'fixture' -or
       $State.ResourceProfile -cne 'iw7.rig-watch-python-cdb-fixture/1' -or
       $State.PhysicalBytes -ne 4GB -or $State.CommitBytes -ne 6GB){throw 'Exact fixed fixture resource profile required.'}
    foreach($name in @('Now','Acquire','Stage','Prepare','Identity','Deadline','Register','Poll','Continue','Seal',
        'Budget','Save','VerifySources','Restore','Release','Quarantine','Delay')){
        if(!$Hooks.Contains($name) -or $Hooks[$name] -isnot [scriptblock]){throw "Missing concrete provider: $name"}
    }
    $State.StartedMs=Get-RigWatchNow $State $Hooks
    $State.DueMs=$State.StartedMs+240000L
    try {
        $State.AcquireAttempted=$true
        $State.Lease=& $Hooks.Acquire $State 4GB 6GB
        if(!$State.Lease -or !$State.Lease.Token){throw 'Admission did not return a bound lease.'}
        Assert-RigWatchTime $State $Hooks
        $State.StageStarted=$true
        & $Hooks.Stage $State | Out-Null
        Save-RigWatchCheckpoint $State $Hooks
        $State.FactoryStarted=$true
        $State.Owner=& $Hooks.Prepare $State
        if(!$State.Owner){throw 'Original job factory returned no owner.'}
        # Arm the independently running deadline before identity, save, registration
        # or Resume can block. A late factory still returns a suspended root.
        $State.Deadline=& $Hooks.Deadline $State.Owner $State.DueMs
        if(!$State.Deadline){throw 'Original-job deadline was not armed.'}
        Assert-RigWatchTime $State $Hooks
        $State.Identity=& $Hooks.Identity $State
        Assert-RigWatchTime $State $Hooks
        if(!$State.Identity -or $State.Identity.OriginalHandles -isnot [bool] -or !$State.Identity.OriginalHandles){throw 'Bound original-handle identity required.'}
        Save-RigWatchCheckpoint $State $Hooks
        $State.Owner.Resume()
        Assert-RigWatchTime $State $Hooks
        & $Hooks.Register $State | Out-Null
        Save-RigWatchCheckpoint $State $Hooks
        $State.Status='Loading'
        while($true){
            & $Hooks.Budget $State | Out-Null
            Assert-RigWatchTime $State $Hooks
            $event=& $Hooks.Poll $State
            Assert-RigWatchTime $State $Hooks
            if(!$event -or $event.Nonce -cne $State.Nonce -or $event.Healthy -isnot [bool] -or !$event.Healthy -or
               ($event.Bytes -isnot [int] -and $event.Bytes -isnot [long]) -or $event.Bytes -lt 0 -or $event.Bytes -gt 1MB){throw 'Unhealthy/unbound transport or output cap.'}
            if($event.Status -cnotin @('Loading','ArmedStopped','Running','CaptureStopped')){throw 'Transport refused, ended or returned an unknown status.'}
            if($event.Status -ceq 'ArmedStopped' -and !$State.Continued){
                if($event.IdentityChecked -isnot [bool] -or !$event.IdentityChecked -or
                   $event.BreakpointChecked -isnot [bool] -or !$event.BreakpointChecked){throw 'Stopped identity and actual breakpoint confirmation required.'}
                $State.DueMs=[math]::Min($State.DueMs,(Get-RigWatchNow $State $Hooks)+10000L)
                $State.Deadline.Tighten($State.DueMs)
                Save-RigWatchCheckpoint $State $Hooks
                & $Hooks.Continue $State | Out-Null
                $State.Continued=$true;$State.Status='Running'
                Assert-RigWatchTime $State $Hooks
            }elseif($event.Status -ceq 'CaptureStopped'){
                if(!$State.Continued){throw 'Capture appeared before authorized continuation.'}
                $State.Capture=& $Hooks.Seal $State
                Assert-RigWatchTime $State $Hooks
                if(!$State.Capture -or $State.Capture.Nonce -cne $State.Nonce -or
                   $State.Capture.SHA256 -cnotmatch '^[a-f0-9]{64}$' -or $State.Capture.WitnessParsed -isnot [bool] -or
                   !$State.Capture.WitnessParsed -or $State.Capture.Bytes -lt 1 -or $State.Capture.Bytes -gt 256KB){throw 'Bound sealed parsed witness required.'}
                Save-RigWatchCheckpoint $State $Hooks
                $State.Status='CapturedStopped'
                break
            }elseif(($State.Continued -and $event.Status -ceq 'Loading') -or (!$State.Continued -and $event.Status -ceq 'Running')){
                throw 'Transport state regressed or continued without authorization.'
            }
            $State.Snapshot=Get-RigWatchSnapshot $State.Owner
            Save-RigWatchCheckpoint $State $Hooks
            if($State.Snapshot.RootExited){throw 'Original transport root ended before a sealed capture.'}
            & $Hooks.Delay | Out-Null
            Assert-RigWatchTime $State $Hooks
        }
    }catch{$State.Failure=$_.Exception.Message;$State.Status='Failed'}
    # Cleanup has its own finite allowance, also capped at start+270 s. It does
    # not reset the observation deadline or convert a forced exit into exit0.
    try {
        $State.CleanupDueMs=[math]::Min((Get-RigWatchNow $State $Hooks)+30000L,$State.StartedMs+270000L)
        if($State.Owner){
            if($State.Deadline){$State.Deadline.RequestStop()}else{$State.Owner.Stop()}
            while($true){
                $State.Snapshot=Get-RigWatchSnapshot $State.Owner
                Save-RigWatchCheckpoint $State $Hooks -Cleanup
                if($State.Snapshot.RootExited -and $State.Snapshot.Active -eq 0){
                    $State.Closed=$true
                    if($State.Deadline){$State.Deadline.CloseAfterJobClosed()}
                    Assert-RigWatchTime $State $Hooks -Cleanup
                    $State.Owner.Dispose();$State.Owner=$null
                    Assert-RigWatchTime $State $Hooks -Cleanup
                    break
                }
                & $Hooks.Delay | Out-Null
                Assert-RigWatchTime $State $Hooks -Cleanup
            }
        }elseif($State.FactoryStarted){throw 'Factory outcome unknown; original closure cannot be proved.'}
        else{$State.Closed=$true}
        & $Hooks.VerifySources $State | Out-Null
        Assert-RigWatchTime $State $Hooks -Cleanup
        if($State.StageStarted){
            $restored=& $Hooks.Restore $State
            if($restored -isnot [bool] -or !$restored){throw 'Exact restoration not confirmed.'}
            $State.Restored=$true
        }else{$State.Restored=$true}
        Save-RigWatchCheckpoint $State $Hooks -Cleanup
        if($State.Lease){
            $State.ReleaseAttempted=$true
            $released=& $Hooks.Release $State
            if($released -isnot [bool] -or !$released){throw 'Admission release outcome unknown.'}
            $State.LeaseReleased=$true
            Assert-RigWatchTime $State $Hooks -Cleanup
        }elseif($State.AcquireAttempted){throw 'Admission result unknown; inspect registry before claiming release.'}
        $State.DiagnosticCaptured=(!$State.Failure -and $null -ne $State.Capture)
        $State.Status=if($State.DiagnosticCaptured){'CaptureClosedRestored'}else{'FailedClosedRestored'}
        Save-RigWatchCheckpoint $State $Hooks -Cleanup
    }catch{
        $State.DiagnosticCaptured=$false;$State.CleanupFailure=$_.Exception.Message;$State.Status='Quarantined'
        $State.Quarantined=$true
        & $Hooks.Quarantine $State | Out-Null
    }
    return $State
}

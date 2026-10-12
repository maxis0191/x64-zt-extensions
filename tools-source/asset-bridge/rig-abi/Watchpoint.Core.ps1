# Functions only. No type loading, process creation or resource observation on import.
function New-RigWatchFixtureState([string]$Nonce) {
    if($Nonce -cnotmatch '^[a-f0-9]{32}$'){throw 'Exact session nonce required.'}
    [ordered]@{Schema='iw7.rig-watch-fixture-transaction/1';Mode='fixture';ResourceProfile='iw7.rig-watch-python-cdb-fixture/1';
        PhysicalBytes=4GB;CommitBytes=6GB;MeasuredResourcePeaks=$false;
        Nonce=$Nonce;Status='Preparing';Failure=$null;CleanupFailure=$null;
        StartedMs=$null;LastMs=$null;DueMs=$null;CleanupDueMs=$null;Lease=$null;AcquireAttempted=$false;
        StageStarted=$false;FactoryStarted=$false;Owner=$null;Deadline=$null;Context=[ordered]@{};
        Identity=$null;Snapshot=$null;Capture=$null;AttachmentAuthorized=$false;StartupContinued=$false;
        DescendantClosureUnproven=$false;OriginalJobClosed=$false;Continued=$false;Closed=$false;Restored=$false;
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
        if($Event.InitialFailure.Type -ceq 'IsProcessInJobNonmember'){$State.DescendantClosureUnproven=$true}
        throw ('Fixture transport failed: '+[string]$Event.Error)
    }
}
function Confirm-RigWatchFixtureMembers($State,$Event,$Observation,[string]$Python,[string]$Cdb) {
    # Pure validation of a snapshot from the pinned, read-only original-job observer.
    # Save the failed observation too; absence must never become an ownership claim.
    $State.Context.LastMembership=$Observation
    $State.Context.MembershipPhase=$Event.Status
    $State.DescendantClosureUnproven=$true
    if(($Event.Target.pid -isnot [int] -and $Event.Target.pid -isnot [long] -and $Event.Target.pid -isnot [uint32]) -or
       $Event.Target.pid -le 0 -or $Event.Target.pid -gt [uint32]::MaxValue -or
       ($Event.Target.created_filetime -isnot [long] -and $Event.Target.created_filetime -isnot [int]) -or
       $Event.Target.created_filetime -le 0){throw 'Numeric original target identity required.'}
    $count=if($Event.Status -ceq 'TargetCreatedStopped'){2}else{3}
    $members=@($Observation.Members)
    if($Observation.AssignedCount -ne $count -or $Observation.ListedCount -ne $count -or $members.Count -ne $count){
        throw 'Exact original root/fixture or root/fixture/CDB membership required.'
    }
    foreach($member in $members){
        if($member.Error -or $member.InOriginalJob -isnot [bool] -or !$member.InOriginalJob -or
           [datetime]$member.CreatedUtc -lt [datetime]$State.Identity.CreatedUtc){throw 'Original-job member identity differs.'}
    }
    $root=@($members|Where-Object PID -EQ $State.Identity.PID)
    $target=@($members|Where-Object PID -EQ $Event.Target.pid)
    if($root.Count -ne 1 -or $root[0].Image -ine $Python -or
       ([datetime]$root[0].CreatedUtc).ToFileTimeUtc() -ne ([datetime]$State.Identity.CreatedUtc).ToFileTimeUtc() -or
       $target.Count -ne 1 -or $target[0].Image -ine $Python -or $target[0].PID -eq $State.Identity.PID -or
       ([datetime]$target[0].CreatedUtc).ToFileTimeUtc() -ne $Event.Target.created_filetime){throw 'New target is not bound to original creation identity.'}
    if($Event.Status -cin @('TargetCreatedStopped','AttachedStopped')){
        if($Event.Target.OriginalHandles -isnot [bool] -or !$Event.Target.OriginalHandles -or
           $Event.Target.CreatedSuspended -isnot [bool] -or !$Event.Target.CreatedSuspended -or
           $Event.Target.PrimaryResumed -isnot [bool] -or $Event.Target.PrimaryResumed -or
           $Event.Target.CreationFlags -ne 0x08004004 -or $Event.Target.InheritedHandles -isnot [bool] -or
           $Event.Target.InheritedHandles){throw 'Retained suspended creation handles required.'}
    }
    if($State.Context.TargetCreation -and
       ($Event.Target.pid -ne $State.Context.TargetCreation.pid -or $Event.Target.created_filetime -ne $State.Context.TargetCreation.created_filetime)){
        throw 'Fixture changed after owned creation.'
    }
    if($count -eq 2){
        if($Event.DebuggerPID){throw 'Debugger appeared before attachment authorization.'}
        $State.Context.TargetCreation=$Event.Target
        $State.Context.CreationMembership=$Observation
    }else{
        $debugger=@($members|Where-Object PID -EQ $Event.DebuggerPID)
        if(!$State.Context.TargetCreation -or $debugger.Count -ne 1 -or $debugger[0].Image -ine $Cdb -or
           $debugger[0].PID -in @($State.Identity.PID,$target[0].PID) -or
           [datetime]$debugger[0].CreatedUtc -lt [datetime]$target[0].CreatedUtc){throw 'Stopped CDB is not bound to the original job.'}
        if($State.Context.DebuggerIdentity -and
           ($debugger[0].PID -ne $State.Context.DebuggerIdentity.PID -or $debugger[0].CreatedUtc -cne $State.Context.DebuggerIdentity.CreatedUtc)){
            throw 'Debugger creation identity changed.'
        }
        $State.Context.DebuggerIdentity=$debugger[0]
        if($Event.Status -ceq 'AttachedStopped'){$State.Context.AttachedMembership=$Observation}
    }
    $State.DescendantClosureUnproven=$false
    $Event|Add-Member -NotePropertyName OriginalJobChecked -NotePropertyValue $true -Force
}
function Invoke-RigWatchFixtureTransaction($Hooks,$State) {
    # Fixed fixture-only envelope; no generic/retail budget parameter or fallback.
    if($State.Schema -cne 'iw7.rig-watch-fixture-transaction/1' -or $State.Mode -cne 'fixture' -or
       $State.ResourceProfile -cne 'iw7.rig-watch-python-cdb-fixture/1' -or
       $State.PhysicalBytes -ne 4GB -or $State.CommitBytes -ne 6GB){throw 'Exact fixed fixture resource profile required.'}
    foreach($name in @('Now','Acquire','Stage','Prepare','Identity','Deadline','Register','Poll','Attach','Startup','Continue','Seal',
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
        $State.DescendantClosureUnproven=$true
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
            if($event.Status -cnotin @('Loading','TargetCreatedStopped','AttachedStopped','ArmedStopped','Running','CaptureStopped')){throw 'Transport refused, ended or returned an unknown status.'}
            if($event.Status -ceq 'TargetCreatedStopped'){
                if($State.StartupContinued){throw 'Transport regressed to fixture creation.'}
                if(!$State.AttachmentAuthorized){
                    if($event.OriginalJobChecked -isnot [bool] -or !$event.OriginalJobChecked){throw 'Original-job fixture membership required before attachment.'}
                    $State.DescendantClosureUnproven=$true # A new debugger may exist after this authorization.
                    Save-RigWatchCheckpoint $State $Hooks
                    & $Hooks.Attach $State | Out-Null
                    $State.AttachmentAuthorized=$true
                    Assert-RigWatchTime $State $Hooks
                }
            }elseif($event.Status -ceq 'AttachedStopped'){
                if(!$State.AttachmentAuthorized -or $State.Continued){throw 'Unsolicited attached debugger state.'}
                if(!$State.StartupContinued){
                    if($event.OriginalJobChecked -isnot [bool] -or !$event.OriginalJobChecked){throw 'Original three-process membership required before startup.'}
                    $State.DescendantClosureUnproven=$false
                    Save-RigWatchCheckpoint $State $Hooks
                    & $Hooks.Startup $State | Out-Null
                    $State.StartupContinued=$true
                    Assert-RigWatchTime $State $Hooks
                }
            }elseif($event.Status -ceq 'ArmedStopped' -and !$State.Continued){
                if(!$State.StartupContinued){throw 'Fixture armed before authorized startup.'}
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
                    $State.OriginalJobClosed=$true
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
        else{$State.OriginalJobClosed=$true}
        if($State.DescendantClosureUnproven){throw 'Original job closed; descendant closure remains unproven. Admission retained.'}
        $State.Closed=$true
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

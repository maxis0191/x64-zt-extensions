param([switch]$InteropOnly)
$ErrorActionPreference='Stop'
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
function Check([bool]$Value,[string]$Message){if(!$Value){throw $Message}}
if($InteropOnly){
    # Managed compilation/layout inspection only: no job or process is created,
    # and no kernel query is called. This does not measure real Windows memory.
    Check ([IntPtr]::Size -eq 8) 'The reviewed interop layout is x64.'
    Add-Type -LiteralPath (Join-Path $repo 'tools-source/asset-bridge/model/BuildJob.cs')
    Add-Type -LiteralPath (Join-Path $PSScriptRoot 'SoundBuildJob.cs')
    $ownerType=[IW7.SoundFFTelemetryV1.BuildJob]
    Check ($ownerType -ne [IW7.CommunityBuild.BuildJob]) 'Sound job must have its own versioned type.'
    Check ($null -eq [IW7.CommunityBuild.BuildJob].GetProperty('PeakJobCommitBytes')) 'Shared job was modified.'
    foreach($pair in @(@('BasicLimits',64),@('IoCounters',48),@('ExtendedLimits',144))){
        $type=$ownerType.GetNestedType($pair[0],[Reflection.BindingFlags]::NonPublic)
        Check ([Runtime.InteropServices.Marshal]::SizeOf([Activator]::CreateInstance($type)) -eq $pair[1]) ('Layout differs: '+$pair[0])
    }
    $extended=$ownerType.GetNestedType('ExtendedLimits',[Reflection.BindingFlags]::NonPublic)
    Check ([Runtime.InteropServices.Marshal]::OffsetOf($extended,'peakJob').ToInt64() -eq 136) 'PeakJobMemoryUsed offset differs.'
    $empty=[Activator]::CreateInstance($ownerType,$true)
    $rejected=$false
    try{$null=$ownerType.GetProperty('PeakJobCommitBytes').GetValue($empty)}catch{
        $rejected=$_.Exception.ToString().Contains('ObjectDisposedException')
    }
    Check $rejected 'Zero handle must refuse before QueryInformationJobObject can select the caller job.'
    $empty.Dispose()
    '7 managed layout/zero-handle/type-isolation checks passed; no kernel call, native process or real peak measurement.'
    return
}
. "$PSScriptRoot/SoundFF.Core.ps1"
. "$repo/sdk/modding/BeaconFF.Core.ps1"
. "$PSScriptRoot/../MaterialV2.Core.ps1"
# Real source gate, text only. No historical Plan is rewritten or rebound.
$sourcePin=Get-SoundFFPin (Join-Path $PSScriptRoot 'SoundBuildJob.cs')
foreach($sourceCase in 'Valid','Missing','Duplicate','ChangedHash'){
    $pins=@($sourcePin.PSObject.Copy())
    if($sourceCase -ceq 'Missing'){$pins=@()}
    if($sourceCase -ceq 'Duplicate'){$pins+=,$sourcePin.PSObject.Copy()}
    if($sourceCase -ceq 'ChangedHash'){$pins[0].SHA256='0'*64}
    $rejected=$false;try{Assert-SoundFFJobSource $pins $PSScriptRoot}catch{$rejected=$true}
    Check ($rejected -eq ($sourceCase -cne 'Valid')) ('Sound-local job source gate differs: '+$sourceCase)
}
$temp=Join-Path ([IO.Path]::GetTempPath()) ('iw7-sound-job-memory-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($temp)|Out-Null
try {
    $cases=@('Success','Zero','QueryFailure','InvalidValue','WaitFailure','WaitAndQueryFailure','UnknownClosure','StopThrows','FactoryFailure','IdentityFailure','DisposeFailure','Maximum')
    foreach($case in $cases){
        $events=[Collections.Generic.List[string]]::new()
        $run=Join-Path $temp $case;[IO.Directory]::CreateDirectory($run)|Out-Null
        $planFile=Join-Path $run 'plan.json';[IO.File]::WriteAllText($planFile,'{}')
        $phaseFile=Join-Path $run 'phase.json';[IO.File]::WriteAllText($phaseFile,'{}')
        $plan=[pscustomobject]@{RunRoot=$run;Work=$run;Python='mock-python.txt';SharedRepo=$repo;HashInputs=@();Review=@{phase_adapter='mock-adapter.py'}}
        $state=[ordered]@{Phases=@();Status='Testing';Failure=$null;CleanupError=$null;Inputs=@();Artifacts=@();RestorationStatus='Pending'}
        $c=[pscustomobject]@{Plan=$plan;PlanPath=$planFile;PlanSHA256=(Get-FileHash -LiteralPath $planFile).Hash;State=$state;
            StatePath=(Join-Path $run 'state.json');Owner=$null;Closed=$true;Saved=$false;InputsGuarded=$false;
            Lease=@{Token='mock'};Guards=[Collections.Generic.List[IDisposable]]::new()}
        function Get-MaterialV2MonotonicMs {0L}
        function New-SoundFFJob {
            if($case -eq 'FactoryFailure'){throw 'Original factory failure'}
            $owner=[pscustomobject]@{Case=$case;Events=$events;Disposed=$false;Value=$peak}
            $owner|Add-Member ScriptProperty PeakJobCommitBytes {
                $this.Events.Add('Query')
                if($this.Disposed){throw 'Queried after disposal'}
                if($this.Case -in 'QueryFailure','WaitAndQueryFailure'){throw [ComponentModel.Win32Exception]::new(5)}
                if($this.Case -eq 'InvalidValue'){return 'not a counter'}
                return [uint64]$this.Value
            }
            $owner|Add-Member ScriptMethod Dispose {
                $this.Events.Add('Dispose')
                if($this.Case -eq 'DisposeFailure'){throw 'Original dispose failure'}
                $this.Disposed=$true
            }
            return $owner
        }
        function Get-BeaconJobIdentity {param($Owner,$Expected,$Phase)
            if($case -eq 'IdentityFailure'){throw 'Original identity failure'}
            [ordered]@{Phase=$Phase}
        }
        function Start-MaterialV2OwnedPhase {param($Owner,$Token)
            [pscustomobject]@{StartedMonotonicMs=0;StartedUtc='synthetic';SchedulerAttached=$false}
        }
        function Wait-MaterialV2OwnedPhase {param($Owner,$Identity,$Start,$Timeout,$Callback)
            if($case -in 'WaitFailure','WaitAndQueryFailure','UnknownClosure','StopThrows'){throw 'Original phase failure'}
            $Identity.ExitCode=0;$Identity.JobRootExitedAtClose=$true;$Identity.JobActiveAtClose=0
        }
        function Stop-MaterialV2OwnedPhase {param($Owner,$Evidence)
            $events.Add('Stop')
            if($case -eq 'StopThrows'){throw 'Original stop failure'}
            return $case -ne 'UnknownClosure'
        }
        function Assert-MaterialV2PhaseResult {}
        function Read-BeaconJson {param($Path,$Limit)
            if((Split-Path $Path -Leaf) -eq 'phase.json'){return @{}}
            [pscustomobject]@{schema='iw7.original-sound-ff-phase/1';phase=$phase;verified=$true;
                explicit_normal_pipe_returns=$true;drain_exception_types=@();existing_runner_receipt_sha256=(Get-FileHash -LiteralPath $phaseFile).Hash}
        }
        function Save-SoundFFFinalState {param($Context,[switch]$Diagnostic);Save-SoundFFState $Context}
        function Exit-IW7ResourceLease {param($Token);$events.Add('Release')}
        $values=if($case -eq 'Maximum'){@([uint64]9007199254740993,[uint64]9007199254740995,[uint64]9007199254740994,[uint64]1)}elseif($case -eq 'Zero'){@([uint64]0)}else{@([uint64]123456789)}
        $phaseNames=@('build','verify','dump','read')
        $failed=$false
        for($i=0;$i -lt $values.Count;$i++){
            $peak=$values[$i];$phase=$phaseNames[$i]
            $spec=[pscustomobject]@{phase=$phase;timeout=240;logs=$run;sha256=('a'*64)}
            try{Invoke-SoundFFPhase $c $spec}catch{
                $failed=$true;$state.Status='Failed';$state.Failure=$_.Exception.Message;break
            }
        }
        Complete-SoundFFTransaction $c
        foreach($guard in $c.Guards){$guard.Dispose()}
        $saved=Get-Content -LiteralPath $c.StatePath -Raw|ConvertFrom-Json
        $memory=$saved.JobMemory;$row=$memory.Phases[-1]
        Check (!$memory.SupervisorIncluded -and $null -eq $memory.SupervisorPeakCommitBytes -and !$memory.TransactionPeakCovered) ('Scope overclaimed: '+$case)
        $expectedFailure=$case -in 'WaitFailure','WaitAndQueryFailure','UnknownClosure','StopThrows','FactoryFailure','IdentityFailure','DisposeFailure'
        Check ($failed -eq $expectedFailure) ('Original phase result changed: '+$case)
        $unavailable=$case -in 'QueryFailure','WaitAndQueryFailure','InvalidValue'
        if($case -eq 'FactoryFailure'){
            Check ($row.Status -ceq 'NotQueried' -and $null -eq $row.PeakJobCommitBytes -and $null -eq $memory.MaxObservedPhaseJobCommitBytes -and !$events.Contains('Query')) 'Unreturned owner acquired a fake measurement.'
        }elseif($unavailable){
            Check ($row.Status -ceq 'Unavailable' -and $row.Error -and $null -eq $row.PeakJobCommitBytes -and $null -eq $memory.MaxObservedPhaseJobCommitBytes) ('Query failure became zero: '+$case)
        }else{
            Check ($row.Status -ceq 'Captured' -and $row.PeakJobCommitBytes -eq $peak) ('Peak missing: '+$case)
            $expectedMax=if($case -eq 'Maximum'){[uint64]9007199254740995}else{$peak}
            Check ($memory.MaxObservedPhaseJobCommitBytes -eq $expectedMax) ('Maximum was summed/rounded/lost: '+$case)
            Check ($row.JobClosedAtQuery -eq ($case -notin 'UnknownClosure','StopThrows')) ('Finality overclaimed: '+$case)
        }
        if($events.Contains('Dispose')){Check ($events.IndexOf('Query') -ge 0 -and $events.IndexOf('Query') -lt $events.IndexOf('Dispose')) ('Disposal preceded query: '+$case)}
        Check (@($events|Where-Object {$_ -ceq 'Query'}).Count -eq $(if($case -eq 'FactoryFailure'){0}else{$values.Count})) ('Query unexpectedly retried: '+$case)
        if($case -in 'UnknownClosure','StopThrows','FactoryFailure','DisposeFailure'){
            Check ($saved.Quarantined -and !$events.Contains('Release')) ('Unknown ownership released: '+$case)
        }
        if($case -eq 'WaitAndQueryFailure'){Check ($saved.Failure -ceq 'Original phase failure') 'Telemetry hid original failure.'}
        if($case -eq 'StopThrows'){Check (!$events.Contains('Dispose') -and $saved.CleanupError -ceq 'Original stop failure') 'Telemetry changed failed-stop ownership.'}
    }
    Check (!('IW7.SoundFFTelemetryV1.BuildJob' -as [type]) -and !('IW7.CommunityBuild.BuildJob' -as [type]) -and !('IW7ResourceMemoryV1' -as [type])) 'Mock suite loaded native helpers.'
    '4 real source-pin gates and 12 sound phase/cleanup-flow cases passed using synthetic counters and mock ownership; no admission, kernel query or measured peak.'
}finally{
    $resolved=[IO.Path]::GetFullPath($temp)
    if(!$resolved.StartsWith([IO.Path]::GetFullPath([IO.Path]::GetTempPath()),[StringComparison]::OrdinalIgnoreCase) -or
        (Split-Path $resolved -Leaf) -notlike 'iw7-sound-job-memory-*'){throw 'Unsafe test cleanup target'}
    foreach($entry in @(Get-ChildItem -LiteralPath $resolved -Recurse -Force)){
        if($entry.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Unexpected redirect in test root'}
        if(!$entry.PSIsContainer){Remove-Item -LiteralPath $entry.FullName}
    }
    foreach($directory in @(Get-ChildItem -LiteralPath $resolved -Directory -Recurse|Sort-Object {$_.FullName.Length} -Descending)){Remove-Item -LiteralPath $directory.FullName}
    Remove-Item -LiteralPath $resolved
}

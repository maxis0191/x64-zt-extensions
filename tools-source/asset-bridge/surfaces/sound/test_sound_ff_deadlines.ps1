$ErrorActionPreference='Stop'
. "$PSScriptRoot/SoundFF.Core.ps1"
. "$PSScriptRoot/../MaterialV2.Core.ps1"
$script:mockMs=0
function Get-MaterialV2MonotonicMs {$script:mockMs}
function Get-MaterialV2UtcNow {[datetime]'2026-10-12T00:00:00Z'}
function Start-Sleep {param($Milliseconds);$script:mockMs+=$Milliseconds}

function Test-FreshWait([string]$Case) {
    $script:mockMs=0
    $owner=[pscustomobject]@{Exited=$true;Active=0;Case=$Case}
    $owner|Add-Member ScriptProperty ExitCode {
        if($this.Case -eq 'SlowExitCode'){$script:mockMs=245001}
        return 0
    }
    $identity=[ordered]@{}
    $failed=$false
    try{
        Wait-MaterialV2OwnedPhase $owner $identity 0 240 {
            param($snapshot,$changed)
            if($Case -eq 'SlowSave'){$script:mockMs=245001}
            if($Case -eq 'SlowDrainSave'){$script:mockMs=2001}
        }
    }catch{$failed=$true}
    if($failed -ne ($Case -ne 'Prompt')){throw "Wrong deadline decision: $Case"}
    if($Case -ne 'Prompt' -and $identity.Supervision.Outcome -ne 'Failed'){throw 'Late Active0 accepted.'}
}
foreach($case in 'Prompt','SlowExitCode','SlowSave','SlowDrainSave'){Test-FreshWait $case}
foreach($case in 'PromptCleanup','SlowStopCall','SlowCleanupExit'){
    $script:mockMs=0
    $owner=[pscustomobject]@{Exited=$true;Active=0;Case=$case}
    $owner|Add-Member ScriptMethod Stop {if($this.Case -eq 'SlowStopCall'){$script:mockMs=15001}}
    $owner|Add-Member ScriptProperty ExitCode {if($this.Case -eq 'SlowCleanupExit'){$script:mockMs=15001};return 0}
    $evidence=[ordered]@{};$closed=Stop-MaterialV2OwnedPhase $owner $evidence
    if($closed -ne ($case -eq 'PromptCleanup')){throw "Wrong cleanup deadline decision: $case"}
}

$temp=[IO.Path]::GetFullPath((Join-Path ([IO.Path]::GetTempPath()) ('iw7-sound-deadline-'+[guid]::NewGuid().ToString('N'))))
[IO.Directory]::CreateDirectory($temp)|Out-Null
try {
    foreach($case in 'PromptReceipt','SlowReceipt','SlowFinalSave','SlowDispose'){
        $script:mockMs=0
        $run=Join-Path $temp $case;[IO.Directory]::CreateDirectory($run)|Out-Null
        $c=[pscustomobject]@{Plan=[pscustomobject]@{RunRoot=$run;Work=$run;Python='C:\mock\python.exe';SharedRepo=$run;Review=@{phase_adapter='C:\mock\phase.py'}};
            State=[ordered]@{Phases=@()};Lease=@{Token='mock'};Owner=$null;Closed=$true;Guards=[Collections.Generic.List[IDisposable]]::new()}
        $spec=[pscustomobject]@{phase='read';timeout=30;logs=$run;sha256=('a'*64)}
        function New-SoundFFJob {
            $item=[pscustomobject]@{Case=$case};$item|Add-Member ScriptMethod Dispose {if($this.Case -eq 'SlowDispose'){$script:mockMs=35001}};return $item
        }
        function Get-BeaconJobIdentity {param($Owner,$Expected,$Phase);[ordered]@{Phase=$Phase}}
        function Start-MaterialV2OwnedPhase {param($Owner,$Token);[pscustomobject]@{StartedMonotonicMs=0;StartedUtc='mock';SchedulerAttached=$false}}
        function Wait-MaterialV2OwnedPhase {param($Owner,$Identity,$Start,$Timeout,$Callback);$Identity.ExitCode=0}
        function Assert-MaterialV2PhaseResult {}
        function Read-BeaconJson {param($Path,$Limit)
            if($case -eq 'SlowReceipt'){$script:mockMs=35001}
            if((Split-Path $Path -Leaf) -eq 'phase.json'){return @{}}
            [pscustomobject]@{schema='iw7.original-sound-ff-phase/1';phase='read';verified=$true;explicit_normal_pipe_returns=$true;
                drain_exception_types=@();existing_runner_receipt_sha256=('b'*64)}
        }
        function Get-FileHash {param($LiteralPath);[pscustomobject]@{Hash=('b'*64)}}
        function Save-SoundFFState {param($Context)
            if($case -eq 'SlowFinalSave' -and $Context.State.Phases.Count -and $Context.State.Phases[0].Contains('SoundReceipt')){$script:mockMs=35001}
        }
        $failed=$false
        try{Invoke-SoundFFPhase $c $spec}catch{$failed=$true}
        finally{foreach($guard in $c.Guards){$guard.Dispose()}}
        if($failed -ne ($case -ne 'PromptReceipt')){throw "Wrong post-receipt deadline decision: $case"}
        if($case -ne 'PromptReceipt' -and $c.State.Phases[0].PostReceiptDecisionElapsedMs -lt 35000){throw 'Missing fresh post-save time.'}
    }
    if(('IW7.CommunityBuild.BuildJob' -as [type]) -or ('IW7ResourceMemoryV1' -as [type])){throw 'Native class unexpectedly loaded.'}
    '11 monotonic deadline cases passed with mocks, including slow ExitCode, stop, dispose, save, drain callback and receipt; no native process.'
}finally{
    $resolved=[IO.Path]::GetFullPath($temp)
    if(!$resolved.StartsWith([IO.Path]::GetFullPath([IO.Path]::GetTempPath()),[StringComparison]::OrdinalIgnoreCase) -or
        (Split-Path $resolved -Leaf) -notlike 'iw7-sound-deadline-*'){throw 'Unsafe cleanup root'}
    foreach($entry in @(Get-ChildItem -LiteralPath $resolved -Recurse -Force)){
        if($entry.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Unexpected redirected test entry'}
        if(!$entry.PSIsContainer){Remove-Item -LiteralPath $entry.FullName}
    }
    foreach($directory in @(Get-ChildItem -LiteralPath $resolved -Directory -Recurse|Sort-Object {$_.FullName.Length} -Descending)){Remove-Item -LiteralPath $directory.FullName}
    Remove-Item -LiteralPath $resolved
}

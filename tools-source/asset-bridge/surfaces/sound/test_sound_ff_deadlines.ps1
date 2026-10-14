$ErrorActionPreference='Stop'
. "$PSScriptRoot/SoundFF.Core.ps1"
. "$PSScriptRoot/../MaterialV2.Core.ps1"
# Import only the pure policy function from the composed dependency. No native
# type, scheduler registry, lease or process is created by this source test.
$scheduler=Join-Path $PSScriptRoot '../../../../ops/Resource-Scheduler.Core.ps1'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($scheduler,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Scheduler source parse failed.'}
$budget=@($ast.FindAll({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq 'Test-IW7ResourceBudget'},$true))
if($budget.Count -ne 1){throw 'One shared telemetry policy function required.'}
. ([scriptblock]::Create($budget[0].Extent.Text))
foreach($estimates in @(@(1,1),@(512MB,1GB),@(12GB,16GB))){Assert-SoundFFEstimates $estimates[0] $estimates[1]}
foreach($field in 'PhysicalBytes','CommitBytes'){
    foreach($invalid in @($null,0,-1,$true,1.0,'1',[bigint]::Parse('9223372036854775808'))){
        $values=@{PhysicalBytes=1;CommitBytes=1};$values[$field]=$invalid
        $refused=$false;try{Assert-SoundFFEstimates @values}catch{$refused=$true}
        if(!$refused){throw "Invalid typed estimate accepted: $field"}
    }
}
$mismatch=[pscustomobject]@{PhysicalBytes=1;CommitBytes=1;Review=@{physical_bytes=1;commit_bytes=2}}
$refused=$false;try{Assert-SoundFFExecutionPlan $mismatch $PSScriptRoot}catch{
    if($_.Exception.Message -cne 'Reviewed scenario estimates differ.'){throw};$refused=$true
}
if(!$refused){throw 'Changed reviewed estimates accepted.'}
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
    foreach($case in 'PromptReceipt','HighCommitReceipt','InvalidTelemetryReceipt','SlowReceipt','SlowFinalSave','SlowDispose'){
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
        function Wait-MaterialV2OwnedPhase {param($Owner,$Identity,$Start,$Timeout,$Callback)
            if($case -in 'HighCommitReceipt','InvalidTelemetryReceipt'){& $Callback $null $false}
            $Identity.ExitCode=0
        }
        function Measure-SoundFFOutputs {}
        function Get-IW7ResourceSnapshot {
            @{PhysicalTotal=1GB;PhysicalAvailable=0;CommitLimit=1GB;Committed=$(if($case -eq 'InvalidTelemetryReceipt'){2GB}else{1GB})}
        }
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
        if($failed -ne ($case -notin 'PromptReceipt','HighCommitReceipt')){throw "Wrong phase decision: $case"}
        if($case -in 'SlowReceipt','SlowFinalSave','SlowDispose' -and $c.State.Phases[0].PostReceiptDecisionElapsedMs -lt 35000){throw 'Missing fresh post-save time.'}
    }
    if(('IW7.CommunityBuild.BuildJob' -as [type]) -or ('IW7ResourceMemoryV1' -as [type])){throw 'Native class unexpectedly loaded.'}
    '13 phase/deadline cases and typed-estimate guards passed with mocks; high commit accepted, impossible telemetry refused; no native process.'
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

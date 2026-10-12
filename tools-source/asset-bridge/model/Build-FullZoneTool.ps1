param([Parameter(Mandatory)][string]$CandidateRoot,
    [Parameter(Mandatory)][string]$MSBuild,
    [int]$CorrectionWindowSeconds=1200)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..' ))
. "$repo/ops/Resource-Scheduler.Core.ps1"
$root=[IO.Path]::GetFullPath($CandidateRoot)
if(Test-Path -LiteralPath (Join-Path $root 'result.local.json')){throw 'Preserve prior evidence before an explicitly authorized new admission.'}
$prep=Get-Content -LiteralPath (Join-Path $root 'preparation.local.json') -Raw|ConvertFrom-Json
if($prep.output -ine $root -or $prep.compile_units -ne 413 -or $prep.dependency_libraries -ne 18 -or
   $prep.feature_macro -cne 'EXPERIMENTAL_IW7' -or !(Test-Path -LiteralPath $MSBuild -PathType Leaf)) {throw 'Prepared candidate identity differs.'}
$project=Join-Path $root 'zonetool-community.vcxproj'
if((Get-FileHash -LiteralPath $project).Hash.ToLowerInvariant() -cne $prep.project_sha256){throw 'Prepared project hash differs.'}
$head=& git -C $prep.source rev-parse HEAD
if($LASTEXITCODE -ne 0 -or $head -cne $prep.source_pin){throw 'Retained source pin changed before admission.'}
$dirty=& git -C $prep.source status --porcelain --untracked-files=no
if($LASTEXITCODE -ne 0 -or $dirty){throw 'Retained tracked source changed before admission.'}
foreach($entry in $prep.readonly_inputs){
    if((Get-Item -LiteralPath $entry.path).Length -ne $entry.bytes -or
       (Get-FileHash -LiteralPath $entry.path).Hash.ToLowerInvariant() -cne $entry.sha256){throw "Retained input differs: $($entry.path)"}
}
function Get-CandidateBytes {
    $size=0L
    foreach($path in [IO.Directory]::EnumerateFiles($root,'*',[IO.SearchOption]::AllDirectories)){$size+=([IO.FileInfo]$path).Length}
    $size
}
$lease=$null;$owner=$null;$records=[Collections.Generic.List[object]]::new();$maxBytes=0L;$failure=$null
$started=[datetime]::UtcNow
try {
    $lease=Enter-IW7ResourceLease -Scope $root -Kind Build -PhysicalBytes 4GB -CommitBytes 6GB -Owner 'H1 strict-source full ZoneTool candidate'
    $lease|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $root 'lease.local.json')
    Add-Type -LiteralPath (Join-Path $PSScriptRoot 'BuildJob.cs')
    # Exercise inherited child containment/termination before starting the compiler.
    $owner=[IW7.CommunityBuild.BuildJob]::Prepare((Join-Path $env:SystemRoot 'System32/cmd.exe'),'/d /c ping.exe -n 30 127.0.0.1 > nul',$root)
    $owner.Resume();$until=[datetime]::UtcNow.AddSeconds(5)
    while($owner.Active -lt 2 -and [datetime]::UtcNow -lt $until){Start-Sleep -Milliseconds 50}
    $testActive=$owner.Active
    if($testActive -lt 2){throw 'Owned child containment fixture did not create two job members.'}
    $owner.Stop();$until=[datetime]::UtcNow.AddSeconds(5)
    while(($owner.Active -ne 0 -or !$owner.Exited) -and [datetime]::UtcNow -lt $until){Start-Sleep -Milliseconds 50}
    if($owner.Active -ne 0 -or !$owner.Exited){throw 'Owned job containment fixture did not close.'}
    @{ActiveBeforeStop=$testActive;ActiveAfterStop=$owner.Active;ExitCode=$owner.ExitCode;Priority=$owner.Priority}|
        ConvertTo-Json|Set-Content -LiteralPath (Join-Path $root 'job-fixture.local.json')
    $owner.Dispose();$owner=$null
    $previousAttempts=@(Get-ChildItem -LiteralPath $root -Filter 'build-*.log' | ForEach-Object {
        if($_.Name -match '^build-(\d+)\.log$'){[int]$Matches[1]}
    })
    [int]$firstAttempt=if($previousAttempts.Count){1+($previousAttempts|Measure-Object -Maximum).Maximum}else{1}
    for($attempt=$firstAttempt;$attempt -lt $firstAttempt+8;$attempt++) {
        $log=Join-Path $root "build-$attempt.log"
        $argsText='"{0}" /m:1 /nr:false /nologo /noconsolelogger /p:Configuration=Release /p:Platform=x64 /p:PreferredToolArchitecture=x64 /p:MultiProcessorCompilation=false /p:BuildProjectReferences=false "/flp:LogFile={1};Verbosity=normal"' -f $project,$log
        $owner=[IW7.CommunityBuild.BuildJob]::Prepare($MSBuild,$argsText,$root)
        if($owner.Image -ine [IO.Path]::GetFullPath($MSBuild)){throw 'Original handle image differs.'}
        $record=[ordered]@{Attempt=$attempt;PID=$owner.PID;Image=$owner.Image;CreatedUtc=$owner.CreatedUtc;
            StartedUtc=[datetime]::UtcNow.ToString('o');Priority=$owner.Priority;Arguments=$argsText;
            SchedulerAttached=$false;ExitCode=$null;JobActiveAtClose=$null}
        $records.Add($record)
        $owner.Resume()
        # WMI cannot reliably query the image of a never-resumed process. The
        # original handle and assigned job already own the complete process tree.
        $registrationUntil=[datetime]::UtcNow.AddSeconds(5)
        while(!$owner.Exited -and !$record.SchedulerAttached){
            try {Add-IW7ResourceProcess -Token $lease.Token -ProcessId $owner.PID;$record.SchedulerAttached=$true}
            catch {
                if($_.Exception.Message -notlike 'Child identity unavailable*' -or [datetime]::UtcNow -gt $registrationUntil){throw}
                Start-Sleep -Milliseconds 100
            }
        }
        while(!$owner.Exited) {
            $bytes=Get-CandidateBytes;$maxBytes=[math]::Max($maxBytes,$bytes)
            if($bytes -ge 1600MB){throw 'Artifact stop threshold 1600 MiB reached; preserving margin below 2 GiB.'}
            $memory=Get-IW7ResourceSnapshot
            if($memory.Committed -gt $memory.CommitLimit*0.85){throw 'Commit pressure exceeded 85 percent.'}
            if([datetime]::UtcNow -gt $started.AddMinutes(45)){throw 'Bounded build timeout.'}
            if(Test-Path -LiteralPath (Join-Path $root 'stop.request')){throw 'Coordinator requested owned job stop.'}
            Start-Sleep -Milliseconds 250
        }
        $record.ExitCode=$owner.ExitCode
        # The root compiler driver has exited. Some native tool helpers can
        # outlive it; terminate only descendants in our original kernel job.
        $record.JobActiveAfterRootExit=$owner.Active
        if($owner.Active -ne 0){$owner.Stop()}
        $until=[datetime]::UtcNow.AddSeconds(15)
        while(($owner.Active -ne 0 -or !$owner.Exited) -and [datetime]::UtcNow -lt $until){Start-Sleep -Milliseconds 100}
        if($owner.Active -ne 0 -or !$owner.Exited){throw 'Original build tree closure unavailable.'}
        $record.ExitCode=$owner.ExitCode;$record.JobActiveAtClose=$owner.Active;$record.EndedUtc=[datetime]::UtcNow.ToString('o')
        $owner.Dispose();$owner=$null
        $records|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $root 'attempts.local.json')
        if($record.ExitCode -eq 0){break}
        Write-Output "Attempt $attempt failed ($($record.ExitCode)); preserving lease for source correction."
        $request=Join-Path $root "attempt-$($attempt+1).go"
        $until=[datetime]::UtcNow.AddSeconds($CorrectionWindowSeconds)
        while(!(Test-Path -LiteralPath $request)){
            if((Test-Path -LiteralPath (Join-Path $root 'stop.request')) -or [datetime]::UtcNow -gt $until){throw 'Correction window stopped/expired.'}
            Start-Sleep -Seconds 1
        }
        if((Get-Content -LiteralPath $request -Raw).Trim() -cne 'retry'){throw 'Invalid retry request.'}
    }
    if($records[-1].ExitCode -ne 0){throw 'Attempt bound reached.'}
} catch {$failure=$_.Exception.Message;Write-Output $failure}
finally {
    $closed=$true
    if($null -ne $owner){
        try{
            $owner.Stop();$until=[datetime]::UtcNow.AddSeconds(15)
            while(($owner.Active -ne 0 -or !$owner.Exited) -and [datetime]::UtcNow -lt $until){Start-Sleep -Milliseconds 100}
            $closed=($owner.Active -eq 0 -and $owner.Exited)
            if($closed -and $records.Count){$records[-1].ExitCode=$owner.ExitCode;$records[-1].JobActiveAtClose=$owner.Active}
        }catch{$closed=$false}
        $owner.Dispose()
    }
    $unchanged=$true;$auditErrors=[Collections.Generic.List[string]]::new()
    foreach($entry in $prep.readonly_inputs){
        try {if((Get-FileHash -LiteralPath $entry.path).Hash.ToLowerInvariant() -cne $entry.sha256){$unchanged=$false;$auditErrors.Add("Input digest changed: $($entry.path)")}}
        catch {$unchanged=$false;$auditErrors.Add($_.Exception.Message)}
    }
    $released=$false;$releaseError=$null
    if($lease -and $closed){
        try {Exit-IW7ResourceLease -Token $lease.Token;$released=$true}
        catch {$releaseError=$_.Exception.Message}
    }
    $finalBytes=$null;$snapshot=$null
    try {$finalBytes=Get-CandidateBytes;$maxBytes=[math]::Max($maxBytes,$finalBytes)}catch{$auditErrors.Add($_.Exception.Message)}
    try {$snapshot=Get-IW7ResourceSnapshot}catch{$auditErrors.Add($_.Exception.Message)}
    if(!$failure -and (!$unchanged -or $auditErrors.Count -or !$released -or !$closed)){$failure='Post-build audit or release incomplete.'}
    if(!$failure -and ($null -eq $finalBytes -or $finalBytes -ge 1600MB)){$failure='Final artifacts reached the conservative stop threshold.'}
    [ordered]@{Schema='iw7.zonetool-full-build/1';StartedUtc=$started.ToString('o');EndedUtc=[datetime]::UtcNow.ToString('o');
        Failure=$failure;Attempts=@($records.ToArray());MaxObservedBytes=$maxBytes;FinalBytes=$finalBytes;
        HardCeiling=2GB;StopThreshold=1600MB;ReadOnlyInputsUnchanged=$unchanged;JobClosureVerified=$closed;
        LeaseReleased=$released;LeaseToken=$(if($lease){$lease.Token});AfterSnapshot=$snapshot;
        AuditErrors=@($auditErrors.ToArray());ReleaseError=$releaseError}|
        ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $root 'result.local.json')
}
if($failure){throw $failure}

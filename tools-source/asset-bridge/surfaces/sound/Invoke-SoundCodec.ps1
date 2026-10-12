param(
    [Parameter(Mandatory)][string]$PlanPath,
    [Parameter(Mandatory)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$PlanSHA256,
    [switch]$Run
)
$ErrorActionPreference='Stop'
function Assert-CodecPlainPath([string]$Path) {
    if(![IO.Path]::IsPathFullyQualified($Path)){throw 'Absolute path required.'}
    for($p=[IO.Path]::GetFullPath($Path);$p;$p=Split-Path $p -Parent){
        if((Test-Path -LiteralPath $p) -and ((Get-Item -LiteralPath $p -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Reparse path refused.'}
    }
}
function Assert-CodecHash($Entry) {
    Assert-CodecPlainPath $Entry.Path
    $f=Get-Item -LiteralPath $Entry.Path
    if($f.Length -ne $Entry.Bytes -or [int]$f.Attributes -ne $Entry.Attributes -or
       $f.LastWriteTimeUtc.Ticks -ne ([datetimeoffset]$Entry.ModifiedUtc).UtcDateTime.Ticks -or
       (Get-FileHash -LiteralPath $Entry.Path -Algorithm SHA256).Hash -ine $Entry.SHA256){throw ('Pinned input changed: '+$Entry.Path)}
}
Assert-CodecPlainPath $PlanPath
if((Get-Item -LiteralPath $PlanPath).Length -gt 65536 -or (Get-FileHash -LiteralPath $PlanPath).Hash -ine $PlanSHA256){throw 'Reviewed plan changed.'}
$plan=Get-Content -LiteralPath $PlanPath -Raw|ConvertFrom-Json
if($plan.Schema -cne 'iw7.original-sound-codec-execution/1' -or $plan.PhysicalBytes -ne 512MB -or $plan.CommitBytes -ne 1GB -or
   $plan.DeadlineMs -ne 10000 -or $plan.CleanupMs -ne 5000){throw 'Exact one-second codec plan/budgets required.'}
$repo=[IO.Path]::GetFullPath($plan.SharedRepo)
$worker=Join-Path $PSScriptRoot 'codec_worker.py'
$scheduler=Join-Path $repo 'ops/Resource-Scheduler.Core.ps1'
$jobSource=Join-Path $repo 'tools-source/asset-bridge/model/BuildJob.cs'
$required=@($PSCommandPath,$worker,$plan.Codec,$plan.Python,$plan.InputFLAC,$plan.OriginalWAV,$plan.SourceManifest,
    $scheduler,$jobSource,(Join-Path $repo 'ops/Resource-Memory.ps1'),(Join-Path $repo 'ops/native/ResourceMemory.cs'),
    (Join-Path $repo 'ops/Resource-RecorderOwnedProcess.Core.ps1'),(Join-Path $repo 'sdk/modding/beacon_tool_phase.py'))
foreach($path in $required){if(@($plan.HashInputs|Where-Object Path -IEQ $path).Count -ne 1){throw ('Required pin missing/duplicated: '+$path)}}
foreach($entry in $plan.HashInputs){Assert-CodecHash $entry}
if(($plan.HashInputs|Where-Object Path -IEQ $jobSource).SHA256 -ine 'f6be2a4cafddb78b5e07a6802354575ada418cb7643d96a3abd0a4c063bc6387' -or
   ($plan.HashInputs|Where-Object Path -IEQ $plan.Codec).SHA256 -ine 'ad8f211bc894755e0061c55ab280ae00e8d3d4f15a8cc4372b24cfa247b5942e') {throw 'Known shared owner/codec pin required.'}
Assert-CodecPlainPath $plan.RunRoot
if(Test-Path -LiteralPath $plan.RunRoot){throw 'Fresh codec RunRoot required; no retry/overwrite.'}
$output=Join-Path $plan.RunRoot 'decoded.wav'
$expected=@('-nostdin','-n','-loglevel','info','-xerror','-err_detect','explode','-threads','1','-f','flac','-protocol_whitelist','file','-i',$plan.InputFLAC,
    '-map','0:a:0','-vn','-sn','-dn','-map_metadata','-1','-c:a','pcm_s16le','-threads','1','-fflags','+bitexact','-flags:a','+bitexact','-f','wav','-fs','131072',$output)
if(($plan.CodecArguments|ConvertTo-Json -Compress) -cne ($expected|ConvertTo-Json -Compress)){throw 'Literal codec arguments differ.'}
if(!$Run){$plan|ConvertTo-Json -Depth 12;return}
if(('IW7.CommunityBuild.BuildJob' -as [type]) -or ('IW7ResourceMemoryV1' -as [type])){throw 'Fresh execution host required.'}
$guards=[Collections.Generic.List[IO.FileStream]]::new();$lease=$null;$owner=$null;$closed=$true;$intact=$true;$created=$false
$state=[ordered]@{Schema='iw7.original-sound-codec-result/1';Status='Preparing';PlanSHA256=$PlanSHA256;RetainedLeaseToken=$null;
    Reservation=$null;Root=$null;Worker=$null;Cleanup=$null;InputsUnchanged=$false;JobClosed=$false;Failure=$null;
    ExternalDecoderVerified=$false;Ready=$false;PlaybackVerified=$false}
function Save-CodecState {if($created){[IO.File]::WriteAllText((Join-Path $plan.RunRoot 'state.local.json'),($state|ConvertTo-Json -Depth 15))}}
function Measure-CodecOutputs {
    $items=@(Get-ChildItem -LiteralPath $plan.RunRoot -Recurse -Force)
    if(@($items|Where-Object {$_.Attributes -band [IO.FileAttributes]::ReparsePoint}).Count){throw 'Output reparse entry refused.'}
    $files=@($items|Where-Object {!$_.PSIsContainer})
    if(($files|Measure-Object Length -Sum).Sum -gt 1MB){throw 'Temporary output exceeds 1 MiB.'}
    foreach($f in $files){
        if($f.Name -in 'stdout.log','stderr.log' -and $f.Length -gt 32768){throw 'Codec log bound exceeded.'}
        if($f.Name -eq 'decoded.wav' -and $f.Length -gt 262144){throw 'WAV watchdog bound exceeded.'}
        if($f.Name -eq 'worker-receipt.json' -and $f.Length -gt 16384){throw 'Worker receipt bound exceeded.'}
    }
}
try {
    $guards.Add([IO.File]::Open($PlanPath,'Open','Read','Read'))
    if((Get-FileHash -LiteralPath $PlanPath).Hash -ine $PlanSHA256){throw 'Plan changed before read guard.'}
    foreach($entry in $plan.HashInputs){$guards.Add([IO.File]::Open($entry.Path,'Open','Read','Read'));Assert-CodecHash $entry}
    . $scheduler
    $lease=Enter-IW7ResourceLease -Scope $plan.RunRoot -Kind Analysis -PhysicalBytes 512MB -CommitBytes 1GB -Owner 'Original sound one-second FFmpeg decode only'
    $state.RetainedLeaseToken=$lease.Token
    $state.Reservation=[ordered]@{Kind=$lease.Kind;CreatedUtc=$lease.CreatedUtc;PhysicalBytes=$lease.PhysicalBytes;CommitBytes=$lease.CommitBytes}
    [IO.Directory]::CreateDirectory($plan.RunRoot)|Out-Null;$created=$true;Save-CodecState
    Add-Type -LiteralPath $jobSource
    $arguments=@('-B',$worker,'--plan',$PlanPath,'--plan-sha256',$PlanSHA256)
    $literal=(@(foreach($a in $arguments){if(!$a -or $a -match '["\x00-\x1f]' -or $a.EndsWith('\')){throw 'Unsupported literal worker argument.'};'"'+$a+'"'}) -join ' ')
    $owner=[IW7.CommunityBuild.BuildJob]::Prepare($plan.Python,$literal,$plan.RunRoot);$closed=$false
    $state.Root=[ordered]@{PID=$owner.PID;Image=$owner.Image;CreatedUtc=$owner.CreatedUtc;Priority=$owner.Priority;SchedulerAttached=$false;LastSample=$null}
    if($state.Root.Image -ine $plan.Python -or $state.Root.Priority -ne 16384){throw 'Original root identity/priority mismatch.'}
    $owner.Resume();$clock=[Diagnostics.Stopwatch]::StartNew()
    if(!$owner.Exited){
        try{Add-IW7ResourceProcess -Token $lease.Token -ProcessId $owner.PID;$state.Root.SchedulerAttached=$true}
        catch{if($_.Exception.Message -notlike 'Child identity unavailable*' -or !$owner.Exited){throw}}
    }
    $state.Status='Decoding';Save-CodecState
    while($true){
        $exited=$owner.Exited;$active=$owner.Active;$code=if($exited){$owner.ExitCode}else{$null}
        $state.Root.LastSample=[ordered]@{ElapsedMs=$clock.ElapsedMilliseconds;RootExited=$exited;Active=$active;ExitCode=$code}
        Measure-CodecOutputs
        $memory=Get-IW7ResourceSnapshot
        if($memory.Committed -gt $memory.CommitLimit*0.85){throw 'Committed-memory pressure stop.'}
        if($clock.ElapsedMilliseconds -ge 10000){throw 'Codec original-job deadline expired.'}
        if($exited -and $code -ne 0){throw 'Worker root exited nonzero.'}
        if($exited -and $active -eq 0){$closed=$true;break}
        Start-Sleep -Milliseconds 100
    }
    $receiptPath=Join-Path $plan.RunRoot 'worker-receipt.json'
    $r=Get-Content -LiteralPath $receiptPath -Raw|ConvertFrom-Json
    if($r.schema -cne 'iw7.original-sound-codec-worker/1' -or $r.failure -or ($r.native_exit_code -isnot [long] -and $r.native_exit_code -isnot [int]) -or
       $r.native_exit_code -ne 0 -or $r.pipes_eof -isnot [bool] -or !$r.pipes_eof -or $r.pcm_verified -isnot [bool] -or !$r.pcm_verified -or
       $r.pcm_bytes -ne 96000 -or $r.samples -ne 48000 -or $r.channels -ne 1 -or $r.bits_per_sample -ne 16 -or $r.sample_rate -ne 48000 -or
       $r.pcm_sha256 -cne '72cb02b5178ce424fd3df3dbfb28b0b9613f69a4da3af71a022b8b542a46ddd9' -or
       $r.codec_sha256 -cne 'ad8f211bc894755e0061c55ab280ae00e8d3d4f15a8cc4372b24cfa247b5942e'){throw 'Independent codec receipt did not pass.'}
    $guards.Add([IO.File]::Open($output,'Open','Read','Read'))
    if((Get-Item -LiteralPath $output).Length -gt 131072 -or (Get-Item -LiteralPath $output).Length -ne $r.wav_bytes -or
       (Get-FileHash -LiteralPath $output).Hash -ine $r.wav_sha256){throw 'Decoded output changed after worker readback.'}
    $state.Worker=$r;$state.Status='ThirdPartyPCMVerified'
} catch {$state.Failure=$_.Exception.Message;$state.Status='Failed';throw}
finally {
    if($owner -and !$closed){
        $state.Cleanup=[ordered]@{StopRequested=$true;Closed=$false;LastSample=$null;Error=$null}
        try{
            $cleanupClock=[Diagnostics.Stopwatch]::StartNew();$owner.Stop()
            while($true){
                $exited=$owner.Exited;$active=$owner.Active;$code=if($exited){$owner.ExitCode}else{$null}
                $state.Cleanup.LastSample=[ordered]@{ElapsedMs=$cleanupClock.ElapsedMilliseconds;RootExited=$exited;Active=$active;ExitCode=$code}
                if($cleanupClock.ElapsedMilliseconds -gt 5000){throw 'Original job cleanup deadline expired.'}
                if($exited -and $active -eq 0){$closed=$true;$state.Cleanup.Closed=$true;break}
                Start-Sleep -Milliseconds 100
            }
        }catch{$state.Cleanup.Error=$_.Exception.Message}
    }
    if($owner){$owner.Dispose()}
    foreach($entry in $plan.HashInputs){try{Assert-CodecHash $entry}catch{$intact=$false;$state.Failure=$_.Exception.Message}}
    try{if((Get-FileHash -LiteralPath $PlanPath).Hash -ine $PlanSHA256){$intact=$false}}
    catch{$intact=$false;$state.Failure=$_.Exception.Message}
    $state.InputsUnchanged=$intact;$state.JobClosed=$closed
    if(!$intact -or !$closed){$state.Status='Failed'}
    Save-CodecState
    try{
        if($created){Measure-CodecOutputs}
        if($lease -and $closed -and $intact){Exit-IW7ResourceLease -Token $lease.Token;$state.RetainedLeaseToken=$null}
    }catch{$state.Status='Failed';$state.Failure=$_.Exception.Message;throw}
    finally{
        foreach($guard in $guards){$guard.Dispose()}
        $state.ExternalDecoderVerified=($state.Status -ceq 'ThirdPartyPCMVerified' -and $closed -and $intact -and !$state.RetainedLeaseToken)
        Save-CodecState
    }
    Save-CodecState
    if($created){Measure-CodecOutputs}
}
if(!$state.JobClosed -or !$state.InputsUnchanged -or $state.RetainedLeaseToken){throw 'Codec closure/integrity incomplete; retain evidence and reservation.'}
$state|ConvertTo-Json -Depth 15

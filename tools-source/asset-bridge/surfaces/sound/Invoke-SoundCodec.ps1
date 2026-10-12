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
    Assert-CodecMetadata $Entry
    if((Get-FileHash -LiteralPath $Entry.Path -Algorithm SHA256).Hash -ine $Entry.SHA256){throw ('Pinned input changed: '+$Entry.Path)}
}
function Assert-CodecMetadata($Entry) {
    Assert-CodecPlainPath $Entry.Path
    if(($Entry.Bytes -isnot [int] -and $Entry.Bytes -isnot [long]) -or $Entry.Bytes -le 0 -or
       $Entry.SHA256 -isnot [string] -or $Entry.SHA256 -notmatch '^[a-fA-F0-9]{64}$'){throw 'Exact input size/hash declaration required.'}
    $f=Get-Item -LiteralPath $Entry.Path
    if($f.PSIsContainer -or $f.Length -ne $Entry.Bytes -or [int]$f.Attributes -ne $Entry.Attributes -or
       $f.LastWriteTimeUtc.Ticks -ne ([datetimeoffset]$Entry.ModifiedUtc).UtcDateTime.Ticks){throw ('Input metadata changed: '+$Entry.Path)}
}
function Open-CodecReadGuard([string]$Path) {
    Assert-CodecPlainPath $Path
    [IO.File]::Open($Path,'Open','Read','Read')
}
function Assert-CodecKnownPin($Plan,[string]$Path,[long]$Bytes,[string]$SHA256) {
    $pins=@($Plan.HashInputs|Where-Object Path -IEQ $Path)
    if($pins.Count -ne 1 -or $pins[0].Bytes -ne $Bytes -or $pins[0].SHA256 -ine $SHA256){throw 'Closed profile input pin differs.'}
}
function Get-CodecProfile($Plan) {
    if($Plan.InputProfile -isnot [string] -or $Plan.InputProfile -cnotin @('OriginalSource','NativeDumpF','NativeDumpOnlyC')){throw 'Explicit closed codec profile required.'}
    $source=Join-Path $Plan.SharedRepo 'runtime/content-surfaces/original-sound-source-b'
    if($Plan.OriginalWAV -ine (Join-Path $source 'original/source.wav') -or
       $Plan.SourceManifest -ine (Join-Path $source 'sound-source.json')){throw 'Original fixture binding differs.'}
    Assert-CodecKnownPin $Plan $Plan.Codec 242496512 'ad8f211bc894755e0061c55ab280ae00e8d3d4f15a8cc4372b24cfa247b5942e'
    Assert-CodecKnownPin $Plan $Plan.Python 104952 '4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a'
    Assert-CodecKnownPin $Plan $Plan.OriginalWAV 96044 '299727b757b46804ca52144133b7e72405f13ddcdaf8aea30a497afc62ca9cb4'
    Assert-CodecKnownPin $Plan $Plan.SourceManifest 3158 '06a2bf8650ba235e176746efe29b00f383e26144cd24ff5dd1774c28f9d71a01'
    if($Plan.InputProfile -ceq 'OriginalSource'){
        $inputPath=Join-Path $source 'sound_assets/community/original_chime_v1.flac'
        $hash='9f807b3f4dfee213dfd44e3f60b9109075327b233f321bdf38f594c3a0c47bbb'
        if($Plan.NativeDumpState){throw 'Original profile cannot adopt a dump state.'}
        $status='ThirdPartyPCMVerified'
    }elseif($Plan.InputProfile -ceq 'NativeDumpF'){
        $dumpRoot=Join-Path $Plan.SharedRepo 'runtime/content-surfaces/original-sound-sab-ff-b'
        $inputPath=Join-Path $dumpRoot 'work/dump/sdk_original_sound_v1/sound_assets/community/original_chime_v1.flac'
        $hash='a4e9276568dfeaf42d39deefe243b1efc2b9095b2f558bcb3512b98c417154d9'
        if($Plan.NativeDumpState -ine (Join-Path $dumpRoot 'state.local.json')){throw 'Exact completed F state required.'}
        Assert-CodecKnownPin $Plan $Plan.NativeDumpState 65117 'd0a57123f7940eee29ef42da7440dd353e63eeffbfc025d37b162f4feda9e1a9'
        $status='DumpDecodedByFFmpeg'
    }else{
        # Observed successful DumpOnly A receipt; no payload hashing in Plan mode.
        $hash='1f20e4e3d2ea9160c833ba2f188950908573c9bf677e63e10edf639efd40c725';$dumpStateSHA='761ef1246010482d9451e1feae1b7e0f2e75bcd0ea678a1ce70f294184d669df';$dumpStateBytes=62517
        $dumpRoot=Join-Path $Plan.SharedRepo 'runtime/content-surfaces/original-sound-dump-only-a'
        $inputPath=Join-Path $dumpRoot 'work/dump/sdk_original_sound_v1/sound_assets/community/original_chime_v1.flac'
        if($Plan.NativeDumpState -ine (Join-Path $dumpRoot 'state.local.json')){throw 'Exact qualified DumpOnly state required.'}
        Assert-CodecKnownPin $Plan $Plan.NativeDumpState $dumpStateBytes $dumpStateSHA
        $status='DumpDecodedByFFmpeg'
    }
    if($Plan.InputFLAC -ine $inputPath){throw 'Profile FLAC path differs.'}
    Assert-CodecKnownPin $Plan $inputPath 96394 $hash
    [pscustomobject]@{Name=$Plan.InputProfile;InputSHA256=$hash;SuccessStatus=$status}
}
function Assert-CodecDumpOnlyEvidence($Plan) {
    # Existing caller owns admission, retained guards and exact state/input hashes.
    $e=Get-Content -LiteralPath $Plan.NativeDumpState -Raw|ConvertFrom-Json
    if($e.Schema -cne 'iw7.original-sound-ff-result/1' -or $e.Profile -cne 'DumpOnly' -or $e.Status -cne 'SoundDumpOnlyBytesVerified' -or
        $e.Work -ine (Join-Path (Split-Path $Plan.NativeDumpState) 'work') -or $e.RetainedLeaseToken -or $e.Failure -or $e.CleanupError -or
        $e.RestorationStatus -cne 'Confirmed' -or $e.OutputAccountingStatus -cne 'Converged' -or $e.OutputBudgetError -or $e.OutputAccountingError){throw 'Qualified DumpOnly lifecycle required.'}
    foreach($flag in 'Restored','StockPreserved','JobClosureVerified','JobDisposeCompleted','SourceHashesUnchanged','ReadGuardsReleased'){
        if($e.$flag -isnot [bool] -or !$e.$flag){throw 'DumpOnly closure proof missing.'}
    }
    foreach($flag in 'Quarantined','Ready','PlaybackVerified'){
        if($e.$flag -isnot [bool] -or $e.$flag){throw 'DumpOnly exclusion differs.'}
    }
    if(($e.Phases.Phase -join ',') -cne 'dump,read' -or
        $e.Phases[0].NativeExecutableSHA256 -cne 'cef411cf9b4de69be02cb4017aabd964e9143e340e211188daa6b6bab366493a' -or
        $e.Phases[1].NativeExecutableSHA256 -ine '4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a'){throw 'Qualified C dump/read phases required.'}
    foreach($phase in $e.Phases){
        if(($phase.ExitCode -isnot [int] -and $phase.ExitCode -isnot [long]) -or $phase.ExitCode -ne 0 -or $phase.JobActiveAtClose -ne 0 -or
            $phase.JobRootExitedAtClose -isnot [bool] -or !$phase.JobRootExitedAtClose -or $phase.SoundReceipt.verified -isnot [bool] -or !$phase.SoundReceipt.verified -or
            $phase.SoundReceipt.explicit_normal_pipe_returns -isnot [bool] -or !$phase.SoundReceipt.explicit_normal_pipe_returns -or @($phase.SoundReceipt.drain_exception_types).Count){throw 'Dump/read did not close normally.'}
    }
    if($e.Reader.dump_profile -cne 'DumpOnlyC' -or $e.Reader.dump_streaminfo_block_size -ne 4096 -or
        $e.Reader.inventory_provenance -cne 'PreservedBuildF' -or
        $e.ImmutableFF.PlanSHA256 -ine '3d90a5746a8ee698fb08715e270f2855f261b318393257f91a9e7f59e3ad39d5' -or
        $e.ImmutableFF.StateSHA256 -ine 'd0a57123f7940eee29ef42da7440dd353e63eeffbfc025d37b162f4feda9e1a9'){throw 'Exact preserved F/4096 reader scope required.'}
    foreach($flag in 'dump_seek_frame_bytes_verified','dump_streaminfo_rewritten','dump_alias_values_verified','inventory_verified'){
        if($e.Reader.$flag -isnot [bool] -or !$e.Reader.$flag){throw 'DumpOnly byte reader incomplete.'}
    }
    foreach($flag in 'dump_standalone_flac_validated','native_alias_index_verified','checksum_checksum_verified','playback_verified','ready'){
        if($e.Reader.$flag -isnot [bool] -or $e.Reader.$flag){throw 'DumpOnly reader overclaims.'}
    }
    $pin=@($Plan.HashInputs|Where-Object Path -IEQ $Plan.InputFLAC)
    if($pin.Count -ne 1 -or $e.DumpFlac.Path -ine $Plan.InputFLAC -or $e.DumpFlac.Bytes -ne 96394 -or
        $e.DumpFlac.SHA256 -ine $pin[0].SHA256 -or $e.DumpFlac.Bytes -ne $pin[0].Bytes -or
        $e.DumpFlac.Attributes -ne $pin[0].Attributes -or
        ([datetimeoffset]$e.DumpFlac.ModifiedUtc).UtcTicks -ne ([datetimeoffset]$pin[0].ModifiedUtc).UtcTicks){throw 'Observed guarded dump identity differs.'}
}
function Assert-CodecDumpEvidence($Plan) {
    if($Plan.InputProfile -ceq 'NativeDumpOnlyC'){Assert-CodecDumpOnlyEvidence $Plan;return}
    if($Plan.InputProfile -cne 'NativeDumpF'){return}
    # Called only after admission, retained guards and the exact state hash.
    $e=Get-Content -LiteralPath $Plan.NativeDumpState -Raw|ConvertFrom-Json
    if($e.Schema -cne 'iw7.original-sound-ff-result/1' -or $e.Status -cne 'SoundSABAndFFBytesVerified' -or
       $e.Work -ine (Join-Path (Split-Path $Plan.NativeDumpState) 'work') -or $e.RetainedLeaseToken -or $e.Failure -or $e.CleanupError){throw 'Completed F evidence differs.'}
    foreach($flag in 'Restored','StockPreserved','JobClosureVerified','JobDisposeCompleted','SourceHashesUnchanged','ReadGuardsReleased'){
        if($e.$flag -isnot [bool] -or !$e.$flag){throw 'Completed F closure proof missing.'}
    }
    foreach($flag in 'Quarantined','Ready','PlaybackVerified'){
        if($e.$flag -isnot [bool] -or $e.$flag){throw 'Completed F exclusion differs.'}
    }
    foreach($flag in 'dump_seek_frame_bytes_verified','dump_streaminfo_rewritten'){
        if($e.Reader.$flag -isnot [bool] -or !$e.Reader.$flag){throw 'Completed F reader scope differs.'}
    }
    foreach($flag in 'dump_standalone_flac_validated','native_alias_index_verified','checksum_checksum_verified'){
        if($e.Reader.$flag -isnot [bool] -or $e.Reader.$flag){throw 'Completed F reader scope differs.'}
    }
}
Assert-CodecPlainPath $PlanPath
if((Get-Item -LiteralPath $PlanPath).Length -gt 65536 -or (Get-FileHash -LiteralPath $PlanPath).Hash -ine $PlanSHA256){throw 'Reviewed plan changed.'}
$plan=Get-Content -LiteralPath $PlanPath -Raw|ConvertFrom-Json
if($plan.Schema -cne 'iw7.original-sound-codec-execution/2'){throw 'Explicit profile execution schema 2 required.'}
foreach($bound in @(@('PhysicalBytes',512MB),@('CommitBytes',1GB),@('DeadlineMs',10000),@('CleanupMs',5000),
    @('LogLimitEachBytes',32768),@('WavSuccessMaxBytes',131072),@('WavWatchdogStopBytes',131072),@('TotalTempStopBytes',1MB))){
    $v=$plan.($bound[0]);if(($v -isnot [int] -and $v -isnot [long]) -or $v -ne $bound[1]){throw 'Exact typed codec plan/budgets required.'}
}
$profile=Get-CodecProfile $plan
$repo=[IO.Path]::GetFullPath($plan.SharedRepo)
$worker=Join-Path $PSScriptRoot 'codec_worker.py'
$scheduler=Join-Path $repo 'ops/Resource-Scheduler.Core.ps1'
$jobSource=Join-Path $repo 'tools-source/asset-bridge/model/BuildJob.cs'
$required=@($PSCommandPath,$worker,$plan.Codec,$plan.Python,$plan.InputFLAC,$plan.OriginalWAV,$plan.SourceManifest,
    $scheduler,$jobSource,(Join-Path $repo 'ops/Resource-Memory.ps1'),(Join-Path $repo 'ops/native/ResourceMemory.cs'),
    (Join-Path $repo 'ops/Resource-RecorderOwnedProcess.Core.ps1'),(Join-Path $repo 'sdk/modding/beacon_tool_phase.py'))
if($plan.InputProfile -cin @('NativeDumpF','NativeDumpOnlyC')){$required+=,$plan.NativeDumpState}
$readme=Join-Path (Split-Path (Split-Path $plan.Codec)) 'README.txt'
$allowed=@($required)+@($readme)
if(@($plan.HashInputs).Count -gt $allowed.Count -or @($plan.HashInputs|Group-Object {$_.Path.ToLowerInvariant()}|Where-Object Count -NE 1).Count){throw 'Duplicate or extra codec pins refused.'}
foreach($path in $required){if(@($plan.HashInputs|Where-Object Path -IEQ $path).Count -ne 1){throw ('Required pin missing/duplicated: '+$path)}}
foreach($entry in $plan.HashInputs){
    if($entry.Path -notin $allowed){throw 'Unrecognized codec input.'}
    Assert-CodecMetadata $entry
    if($entry.Path -ine $plan.Codec -and $entry.Bytes -gt 1MB){throw 'Non-codec input exceeds bound.'}
}
if(($plan.HashInputs|Where-Object Path -IEQ $jobSource).SHA256 -ine 'f6be2a4cafddb78b5e07a6802354575ada418cb7643d96a3abd0a4c063bc6387' -or
   ($plan.HashInputs|Where-Object Path -IEQ $plan.Codec).SHA256 -ine 'ad8f211bc894755e0061c55ab280ae00e8d3d4f15a8cc4372b24cfa247b5942e') {throw 'Known shared owner/codec pin required.'}
Assert-CodecPlainPath $plan.RunRoot
if(Test-Path -LiteralPath $plan.RunRoot){throw 'Fresh codec RunRoot required; no retry/overwrite.'}
foreach($entry in $plan.HashInputs){if($entry.Path.StartsWith($plan.RunRoot.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Output contains a protected input.'}}
$output=Join-Path $plan.RunRoot 'decoded.wav'
$expected=@('-nostdin','-n','-loglevel','info','-xerror','-err_detect','explode','-threads','1','-f','flac','-protocol_whitelist','file','-i',$plan.InputFLAC,
    '-map','0:a:0','-vn','-sn','-dn','-map_metadata','-1','-c:a','pcm_s16le','-threads','1','-fflags','+bitexact','-flags:a','+bitexact','-f','wav','-fs','131072',$output)
if(($plan.CodecArguments|ConvertTo-Json -Compress) -cne ($expected|ConvertTo-Json -Compress)){throw 'Literal codec arguments differ.'}
if(!$Run){$plan|ConvertTo-Json -Depth 12;return}
if(('IW7.CommunityBuild.BuildJob' -as [type]) -or ('IW7ResourceMemoryV1' -as [type])){throw 'Fresh execution host required.'}
$guards=[Collections.Generic.List[IO.FileStream]]::new();$lease=$null;$owner=$null;$closed=$true;$intact=$true;$created=$false
$heldInputs=[Collections.Generic.List[object]]::new();$allInputsVerified=$false
$bootstrap=@($PSCommandPath,$scheduler,(Join-Path $repo 'ops/Resource-Memory.ps1'),
    (Join-Path $repo 'ops/native/ResourceMemory.cs'),(Join-Path $repo 'ops/Resource-RecorderOwnedProcess.Core.ps1'))
$state=[ordered]@{Schema='iw7.original-sound-codec-result/2';Status='Preparing';InputProfile=$profile.Name;InputSHA256=$profile.InputSHA256;PlanSHA256=$PlanSHA256;RetainedLeaseToken=$null;
    Reservation=$null;Root=$null;Worker=$null;Cleanup=$null;InputHashesMatch=$false;InputsUnchanged=$false;JobClosed=$false;Failure=$null;
    JobDisposeCompleted=$false;ReadGuardsReleased=$false;Quarantined=$false;
    ExternalDecoderVerified=$false;DumpDecodedByFFmpeg=$false;StandaloneFLACConformanceVerified=$false;Ready=$false;PlaybackVerified=$false}
function Save-CodecState {if($created){[IO.File]::WriteAllText((Join-Path $plan.RunRoot 'state.local.json'),($state|ConvertTo-Json -Depth 15))}}
function Measure-CodecOutputs {
    $items=@(Get-ChildItem -LiteralPath $plan.RunRoot -Recurse -Force)
    if(@($items|Where-Object {$_.Attributes -band [IO.FileAttributes]::ReparsePoint}).Count){throw 'Output reparse entry refused.'}
    $files=@($items|Where-Object {!$_.PSIsContainer})
    if(($files|Measure-Object Length -Sum).Sum -gt 1MB){throw 'Temporary output exceeds 1 MiB.'}
    foreach($f in $files){
        if($f.Name -in 'stdout.log','stderr.log' -and $f.Length -gt 32768){throw 'Codec log bound exceeded.'}
        if($f.Name -eq 'decoded.wav' -and $f.Length -gt 131072){throw 'WAV watchdog bound exceeded.'}
        if($f.Name -eq 'worker-receipt.json' -and $f.Length -gt 16384){throw 'Worker receipt bound exceeded.'}
    }
}
try {
    $guards.Add((Open-CodecReadGuard $PlanPath))
    if((Get-FileHash -LiteralPath $PlanPath).Hash -ine $PlanSHA256){throw 'Plan changed before read guard.'}
    # Only the five exact source files needed to trust this entry/admission may
    # be hashed before admission. No executable, audio or dump receipt is read.
    foreach($entry in $plan.HashInputs|Where-Object {$_.Path -in $bootstrap}){
        $guards.Add((Open-CodecReadGuard $entry.Path));$heldInputs.Add($entry);Assert-CodecHash $entry
    }
    . $scheduler
    $lease=Enter-IW7ResourceLease -Scope $plan.RunRoot -Kind Analysis -PhysicalBytes 512MB -CommitBytes 1GB -Owner 'Pinned original sound codec profile only'
    $state.RetainedLeaseToken=$lease.Token
    $state.Reservation=[ordered]@{Kind=$lease.Kind;CreatedUtc=$lease.CreatedUtc;PhysicalBytes=$lease.PhysicalBytes;CommitBytes=$lease.CommitBytes}
    foreach($entry in $plan.HashInputs|Where-Object {$_.Path -notin $bootstrap}){
        $guards.Add((Open-CodecReadGuard $entry.Path));$heldInputs.Add($entry);Assert-CodecHash $entry
    }
    $allInputsVerified=$true
    Assert-CodecDumpEvidence $plan
    [IO.Directory]::CreateDirectory($plan.RunRoot)|Out-Null;$created=$true;Save-CodecState
    Add-Type -LiteralPath $jobSource
    $arguments=@('-B',$worker,'--plan',$PlanPath,'--plan-sha256',$PlanSHA256)
    $literal=(@(foreach($a in $arguments){if(!$a -or $a -match '["\x00-\x1f]' -or $a.EndsWith('\')){throw 'Unsupported literal worker argument.'};'"'+$a+'"'}) -join ' ')
    $closed=$false
    $owner=[IW7.CommunityBuild.BuildJob]::Prepare($plan.Python,$literal,$plan.RunRoot)
    $state.Root=[ordered]@{PID=$owner.PID;Image=$owner.Image;CreatedUtc=$owner.CreatedUtc;Priority=$owner.Priority;SchedulerAttached=$false;LastSample=$null}
    if($state.Root.Image -ine $plan.Python -or $state.Root.Priority -ne 16384){throw 'Original root identity/priority mismatch.'}
    $clock=[Diagnostics.Stopwatch]::StartNew();$owner.Resume()
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
    if((Get-Item -LiteralPath $receiptPath).Length -gt 16384){throw 'Worker receipt bound exceeded before read.'}
    $r=Get-Content -LiteralPath $receiptPath -Raw|ConvertFrom-Json
    if($r.schema -cne 'iw7.original-sound-codec-worker/2' -or $r.input_profile -cne $profile.Name -or $r.input_flac_sha256 -cne $profile.InputSHA256 -or
       $r.status -cne $profile.SuccessStatus -or $r.standalone_flac_conformance_verified -ne $false -or $r.playback_verified -ne $false -or $r.ready -ne $false -or
       $r.failure -or ($r.native_exit_code -isnot [long] -and $r.native_exit_code -isnot [int]) -or
       $r.native_exit_code -ne 0 -or $r.pipes_eof -isnot [bool] -or !$r.pipes_eof -or $r.pcm_verified -isnot [bool] -or !$r.pcm_verified -or
       $r.pcm_bytes -ne 96000 -or $r.samples -ne 48000 -or $r.channels -ne 1 -or $r.bits_per_sample -ne 16 -or $r.sample_rate -ne 48000 -or
       $r.pcm_sha256 -cne '72cb02b5178ce424fd3df3dbfb28b0b9613f69a4da3af71a022b8b542a46ddd9' -or
       $r.codec_sha256 -cne 'ad8f211bc894755e0061c55ab280ae00e8d3d4f15a8cc4372b24cfa247b5942e'){throw 'Independent codec receipt did not pass.'}
    foreach($name in 'standalone_flac_conformance_verified','playback_verified','ready'){
        if($r.$name -isnot [bool] -or $r.$name){throw 'Explicit codec exclusion missing.'}
    }
    foreach($name in 'stdout','stderr'){
        $drain=$r.drains.$name
        if($drain.normal_return -isnot [bool] -or !$drain.normal_return -or $null -ne $drain.exception_type){throw 'Explicit normal pipe completion missing.'}
    }
    $guards.Add([IO.File]::Open($output,'Open','Read','Read'))
    if((Get-Item -LiteralPath $output).Length -gt 131072 -or (Get-Item -LiteralPath $output).Length -ne $r.wav_bytes -or
       (Get-FileHash -LiteralPath $output).Hash -ine $r.wav_sha256){throw 'Decoded output changed after worker readback.'}
    if($clock.ElapsedMilliseconds -ge 10000){throw 'Codec receipt acceptance deadline expired.'}
    $state.Worker=$r;$state.Status=$profile.SuccessStatus
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
    # Kill-on-close is requested before releasing input guards. Dispose is not
    # evidence that every descendant exited; keep the original closure verdict.
    try{if($owner){$owner.Dispose()};$state.JobDisposeCompleted=$true}
    catch{$state.Status='Failed';$state.Failure='Original job dispose failed: '+$_.Exception.GetType().Name}
    # A refusal before admission rechecks only already guarded bootstrap source;
    # it cannot fall through to hashes of audio/executables in finally.
    foreach($entry in $heldInputs){try{Assert-CodecHash $entry}catch{$intact=$false;$state.Failure=$_.Exception.Message}}
    try{if((Get-FileHash -LiteralPath $PlanPath).Hash -ine $PlanSHA256){$intact=$false}}
    catch{$intact=$false;$state.Failure=$_.Exception.Message}
    $state.InputHashesMatch=($allInputsVerified -and $intact);$state.JobClosed=$closed
    $state.InputsUnchanged=($allInputsVerified -and $intact -and $closed -and $state.JobDisposeCompleted)
    $state.Quarantined=([bool]$lease -and !$state.InputsUnchanged)
    if($state.Quarantined){$state.Status='Failed'}
    Save-CodecState
    try{
        if($created){Measure-CodecOutputs}
        if($lease -and $state.InputsUnchanged){Exit-IW7ResourceLease -Token $lease.Token;$state.RetainedLeaseToken=$null}
    }catch{$state.Status='Failed';$state.Failure=$_.Exception.Message;$state.Quarantined=$true;throw}
    finally{
        foreach($guard in $guards){$guard.Dispose()}
        # These handles cannot survive supervisor exit. Unknown closure retains
        # a quarantine/lease, never a promise of continuing input protection.
        $state.ReadGuardsReleased=$true
        $qualified=($state.Status -ceq $profile.SuccessStatus -and $state.InputsUnchanged -and !$state.Quarantined -and !$state.RetainedLeaseToken)
        $state.ExternalDecoderVerified=($qualified -and $profile.Name -ceq 'OriginalSource')
        $state.DumpDecodedByFFmpeg=($qualified -and $profile.Name -cin @('NativeDumpF','NativeDumpOnlyC'))
        Save-CodecState
    }
    Save-CodecState
    if($created){Measure-CodecOutputs}
}
if(!$state.JobClosed -or !$state.InputsUnchanged -or $state.RetainedLeaseToken){throw 'Codec closure/integrity incomplete; retain evidence and reservation.'}
$state|ConvertTo-Json -Depth 15

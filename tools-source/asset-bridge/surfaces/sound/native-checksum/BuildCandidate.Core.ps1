# Pure definitions. Admission and existing native type loading occur only in Build.
function Get-ChecksumBuildClock { [Environment]::TickCount64 }
function Read-ChecksumBuildChunk($Stream,[byte[]]$Buffer) { $Stream.Read($Buffer,0,$Buffer.Length) }
function Assert-ChecksumBuildPath([string]$Path) {
    if(![IO.Path]::IsPathFullyQualified($Path) -or $Path.Contains('"') -or $Path -match '[\x00-\x1f]'){throw 'Absolute literal build path required.'}
    for($p=[IO.Path]::GetFullPath($Path);$p;$p=Split-Path $p -Parent){
        if((Test-Path -LiteralPath $p) -and (Get-Item -LiteralPath $p -Force).Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)){throw 'Redirected build path refused.'}
    }
}
function Assert-ChecksumBuildPlan($Plan,$Seal,$SealState) {
    if($Plan.schema -cne 'iw7.sound-checksum-build-plan/1' -or $Plan.sealed -isnot [bool] -or !$Plan.sealed -or
        $Plan.physical_bytes -ne 4GB -or $Plan.commit_bytes -ne 6GB -or $Plan.stop_bytes -ne 512MB -or $Plan.planning_ceiling_bytes -ne 768MB -or
        $Plan.source_pin -cne 'fab935826c898806855376662a8a03317b3ad8f1' -or
        $Plan.gsc_provider_revision -cne 'eabe74ab65d8ce2a943b54d24b15a60749a0cf2a' -or
        $Plan.sab_ff_authorized -isnot [bool] -or $Plan.sab_ff_authorized -or $Plan.ready -isnot [bool] -or $Plan.ready){throw 'Exact sound build-only contract required.'}
    if($Seal.Schema -cne 'iw7.sound-checksum-sealed-inputs/1' -or $SealState.Status -cne 'Sealed' -or
        $SealState.LeaseReleased -isnot [bool] -or !$SealState.LeaseReleased -or $null -ne $SealState.RetainedLeaseToken -or
        $SealState.InputHashesVerifiedTwice -isnot [bool] -or !$SealState.InputHashesVerifiedTwice -or
        $SealState.ManifestSHA256 -cne $Plan.seal_sha256 -or $Seal.FileCount -ne @($Seal.Inputs).Count -or
        $Seal.FileCount -lt 1 -or $Seal.FileCount -gt 4096){throw 'Complete independently sealed inputs required.'}
    $pins=@{supervision='b6125dfaa4c6b16e4ebc6f54f160369788cfe5290f4c734edb925101af4f3471';
        completion='9710dd10beaa1db17d0bca51916679145f5d76460bc3c43463f888bc9aff3ad0';
        diagnostics='971284b7643182a351a0294c8df52e74794ecc57a7fb870749ccd141f5222379';
        residual_policy='86c2d8f3f6c79e5dd644f11741521f74b3ccd6960f45189ba41da38f17ef3888';
        members='5a02254764277b62f752792f1ec4f5b93b85237b171a3381a78d58f6af190e91';
        job='f6be2a4cafddb78b5e07a6802354575ada418cb7643d96a3abd0a4c063bc6387'}
    foreach($role in $pins.Keys){$p=@($Plan.providers|Where-Object role -CEQ $role);if($p.Count -ne 1 -or $p[0].sha256 -cne $pins[$role]){throw 'Qualified provider identity differs.'}}
    foreach($field in 'candidate','output','shared_repo','python','worker','compiler','scheduler','seal','seal_result'){Assert-ChecksumBuildPath $Plan[$field]}
    if([IO.Path]::GetFullPath($Plan.output) -ine [IO.Path]::GetFullPath($Plan.candidate)){throw 'Single private output required.'}
    foreach($name in 'CL','_CL_','LINK','_LINK_','LIBPATH','PYTHONPATH','PYTHONHOME'){
        if(!$Plan.environment.Contains($name) -or $Plan.environment[$name] -cne ''){throw 'Implicit tool options not neutralized.'}
    }
    if($Plan.environment.VSLANG -cne '1033' -or $Plan.environment.NUMBER_OF_PROCESSORS -cne '1' -or
        $Plan.environment.TEMP -ine (Join-Path $Plan.candidate 'tmp') -or $Plan.environment.TMP -cne $Plan.environment.TEMP){throw 'Fixed private native environment required.'}
    $order=@('probe-original-compile','probe-original-link','probe-original-run','probe-patched-compile','probe-patched-link','probe-patched-run',
        'compile-loadedsound','compile-loadedsound1','compile-loadedsound2','compile-loadedsound3','compile-sound_bank','compile-common-bit-buffer','archive-common','link-candidate')
    if(@($Plan.commands).Count -ne 14){throw 'Fourteen exact native phases required.'}
    for($i=0;$i -lt 14;$i++){if($Plan.commands[$i].phase -cne $order[$i]){throw 'Native phase order differs.'}}
    $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase);$bytes=0L
    foreach($entry in $Seal.Inputs){
        if(![IO.Path]::IsPathFullyQualified($entry.Path) -or !$seen.Add([IO.Path]::GetFullPath($entry.Path)) -or
            ($entry.Bytes -isnot [long] -and $entry.Bytes -isnot [int]) -or $entry.Bytes -lt 0 -or $entry.Bytes -gt 512MB -or
            $entry.SHA256 -cnotmatch '^[a-f0-9]{64}$' -or $entry.ModifiedUtcTicks -isnot [long]){throw 'Unique bounded sealed input required.'}
        $bytes+=$entry.Bytes
    }
    if($bytes -ne $Seal.TotalBytes -or $bytes -gt 2GB){throw 'Sealed byte accounting differs.'}
}
function Measure-ChecksumBuildOutput([string]$Root) {
    $bytes=0L
    if(Test-Path -LiteralPath $Root){foreach($item in Get-ChildItem -LiteralPath $Root -Force -Recurse){
        if($item.Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)){throw 'Redirected candidate output refused.'}
        if(!$item.PSIsContainer){$bytes+=$item.Length}
    }}
    $bytes
}
function Assert-ChecksumBuildBudget($Context) {
    $now=Get-ChecksumBuildClock
    $Context.Record.ElapsedMs=$now-$Context.Started
    if($Context.Record.ElapsedMs -ge 3600000){throw 'Sound build observed global deadline reached.'}
    $size=Measure-ChecksumBuildOutput $Context.Plan.candidate
    $Context.Record.PeakObservedOutputBytes=[math]::Max($Context.Record.PeakObservedOutputBytes,$size)
    if($size -ge 512MB){throw 'Sound build observed output stop threshold reached.'}
    if($now-$Context.LastPressurePoll -ge 1000){
        if(Test-Path -LiteralPath (Join-Path $Context.Plan.candidate 'stop.request')){throw 'Sound build stop requested.'}
        $memory=Get-IW7ResourceSnapshot
        if($memory.CommitLimit -le 0 -or $memory.Committed -gt .85*$memory.CommitLimit){throw 'Sound build commit pressure stop.'}
        $Context.LastPressurePoll=Get-ChecksumBuildClock
        if($Context.LastPressurePoll-$Context.Started -ge 3600000){throw 'Late pressure callback exceeded observed deadline.'}
    }
    $size
}
function Get-ChecksumBuildHash($Stream,$Context) {
    $Stream.Position=0;$buffer=[byte[]]::new(262144)
    $hash=[Security.Cryptography.IncrementalHash]::CreateHash([Security.Cryptography.HashAlgorithmName]::SHA256)
    try {
        while($true){
            $null=Assert-ChecksumBuildBudget $Context
            $read=Read-ChecksumBuildChunk $Stream $buffer;$Context.Record.ProofBytesRead+=$read
            $null=Assert-ChecksumBuildBudget $Context
            if(!$read){break};$hash.AppendData($buffer,0,$read)
        }
        [Convert]::ToHexString($hash.GetHashAndReset()).ToLowerInvariant()
    }finally{$hash.Dispose()}
}
function Assert-ChecksumBuildMetadata($Entry) {
    $f=Get-Item -LiteralPath $Entry.Path -Force
    if($f.PSIsContainer -or $f.Length -ne $Entry.Bytes -or [int]$f.Attributes -ne $Entry.Attributes -or $f.LastWriteTimeUtc.Ticks -ne $Entry.ModifiedUtcTicks){throw 'Sealed input metadata changed.'}
}
function Open-ChecksumBuildInputs($Context,$Seal) {
    foreach($entry in $Seal.Inputs){
        Assert-ChecksumBuildPath $entry.Path;Assert-ChecksumBuildMetadata $entry
        $stream=[IO.File]::Open($entry.Path,'Open','Read','Read');$Context.InputGuards.Add($stream)
        $Context.Record.InputGuardsOpened++
        $Context.GuardedInputs.Add([pscustomobject]@{Entry=$entry;Stream=$stream})
        if((Get-ChecksumBuildHash $stream $Context) -cne $entry.SHA256){throw 'Sealed input content changed before build.'}
        Assert-ChecksumBuildMetadata $entry
    }
    $Context.Record.InputsVerifiedBefore=$true
}
function Confirm-ChecksumBuildInputs($Context) {
    foreach($item in $Context.GuardedInputs){
        Assert-ChecksumBuildMetadata $item.Entry
        if((Get-ChecksumBuildHash $item.Stream $Context) -cne $item.Entry.SHA256){throw 'Guarded sealed input changed after build.'}
        Assert-ChecksumBuildMetadata $item.Entry
    }
    $Context.Record.InputsVerifiedAfter=$true
}
function Write-ChecksumBuildState($Context) {
    $path=Join-Path $Context.Plan.candidate 'supervisor-state.json'
    for($pass=0;$pass -lt 4;$pass++){
        $raw=[Text.UTF8Encoding]::new($false).GetBytes(($Context.Record|ConvertTo-Json -Depth 30)+"`n")
        if($raw.Length -gt 2MB){throw 'Bounded sound supervisor state required.'}
        [IO.File]::WriteAllBytes($path,$raw)
        $actual=Measure-ChecksumBuildOutput $Context.Plan.candidate
        $Context.Record.PeakObservedOutputBytes=[math]::Max($Context.Record.PeakObservedOutputBytes,$actual)
        $now=(Get-ChecksumBuildClock)-$Context.Started
        if(($actual -ge 512MB -or $now -ge 3600000) -and $Context.Record.Success){
            $Context.Record.Success=$false;$Context.Record.Failure='Final state write exceeded observed time/output limit.'
            $Context.Record.ElapsedMs=$now;$Context.Record.OutputBytes=$actual;continue
        }
        if($actual -eq $Context.Record.OutputBytes){return}
        $Context.Record.OutputBytes=$actual
    }
    throw 'Sound state output accounting did not converge.'
}
function New-ChecksumBuildOwner($Plan,[string]$Arguments){[IW7.CommunityBuild.BuildJob]::Prepare($Plan.python,$Arguments,$Plan.candidate)}
function Initialize-ChecksumBuildTypes($Plan) {
    if(('IW7.CommunityBuild.BuildJob' -as [type]) -or ('IW7.AnimationRig.JobMembers' -as [type])){throw 'Fresh host without preloaded job types required.'}
    $job=@($Plan.providers|Where-Object role -CEQ 'job')[0];$members=@($Plan.providers|Where-Object role -CEQ 'members')[0]
    Add-Type -Path $job.path
    Add-Type -Path $members.path
}
function Invoke-ChecksumBuild($Plan,$Seal,[string]$PlanPath,[string]$PlanSHA256,$Bootstrap) {
    $record=[ordered]@{Schema='iw7.sound-checksum-supervisor/1';Success=$false;PlanSHA256=$PlanSHA256;SealSHA256=$Plan.seal_sha256;
        RunID=[guid]::NewGuid().ToString('N');StartedUtc=[datetime]::UtcNow.ToString('o');ElapsedMs=0L;Failure=$null;
        RootExitObservedMs=$null;PeakObservedOutputBytes=0L;OutputBytes=0L;ProofBytesRead=0L;InputsVerifiedBefore=$false;InputsVerifiedAfter=$false;
        InputGuardsOpened=0;InputGuardsDisposed=0;
        TreeClosed=$true;LeaseReleased=$false;RetainedLeaseToken=$null;Ready=$false;SABFFVerified=$false}
    $c=@{Plan=$Plan;Record=$record;Started=(Get-ChecksumBuildClock);LastPressurePoll=0L;
        InputGuards=[Collections.Generic.List[IDisposable]]::new();GuardedInputs=[Collections.Generic.List[object]]::new()}
    $lease=$null;$owner=$null;$closed=$true;$startedNative=$false;$postProofRequired=$false;$sourceProofFailed=$false
    $measure={Measure-ChecksumBuildOutput $Plan.candidate};$boundedMeasure={Assert-ChecksumBuildBudget $c}
    try {
        if(Test-Path -LiteralPath $Plan.candidate){throw 'Candidate already exists; no retry.'}
        $lease=Enter-IW7ResourceLease -Scope $Plan.candidate -Kind Build -PhysicalBytes 4GB -CommitBytes 6GB -Owner 'Sound checksum incremental native build'
        $record.RetainedLeaseToken=$lease.Token
        [IO.Directory]::CreateDirectory($Plan.candidate)|Out-Null
        Open-ChecksumBuildInputs $c $Seal
        Initialize-ChecksumBuildTypes $Plan
        $context=@{PlanSHA256=$PlanSHA256;RunID=$record.RunID;LeaseToken=$lease.Token;LeaseOwnerPID=$PID;OriginalIdentity=$null;
            AcceptedReceipt=$null;SealedPaths=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase);SealedByPath=@{}}
        foreach($entry in $Seal.Inputs){$path=[IO.Path]::GetFullPath($entry.Path);[void]$context.SealedPaths.Add($path);$context.SealedByPath[$path]=$entry}
        $saved=[Environment]::GetEnvironmentVariables('Process')
        try {
            foreach($name in @($saved.Keys)){[Environment]::SetEnvironmentVariable($name,$null,'Process')}
            foreach($name in $Plan.environment.Keys){[Environment]::SetEnvironmentVariable($name,$Plan.environment[$name],'Process')}
            [Environment]::SetEnvironmentVariable('IW7_SOUND_BUILD_PLAN',$PlanSHA256,'Process')
            [Environment]::SetEnvironmentVariable('IW7_SOUND_BUILD_RUN_ID',$record.RunID,'Process')
            [Environment]::SetEnvironmentVariable('IW7_SOUND_BUILD_LEASE',$lease.Token,'Process')
            [Environment]::SetEnvironmentVariable('IW7_SOUND_BUILD_OWNER',[string]$PID,'Process')
            $arguments='-I -B "'+$Plan.worker+'" --plan "'+$PlanPath+'" --plan-sha256 '+$PlanSHA256+' --execute'
            $closed=$false # A failed factory has unknown closure, never implicit success.
            $owner=New-ChecksumBuildOwner $Plan $arguments
            $record.OriginalIdentity=Get-AuditOriginalIdentity $owner $Plan.python;$context.OriginalIdentity=$record.OriginalIdentity
            $owner.Resume();$startedNative=$true;$postProofRequired=$true
        }finally{
            foreach($name in @([Environment]::GetEnvironmentVariables('Process').Keys)){[Environment]::SetEnvironmentVariable($name,$null,'Process')}
            foreach($name in $saved.Keys){[Environment]::SetEnvironmentVariable($name,$saved[$name],'Process')}
        }
        Register-AuditOwnedBuild $owner $lease.Token $record $c.Started $boundedMeasure
        $qualify={Complete-ChecksumBuildEvidence $owner $record $c.Started $Plan $context $boundedMeasure $true}
        Wait-AuditOwnedBuild $owner $record $c.Started $boundedMeasure $null $qualify
        $closed=$true
        if($record.RootExitCode -ne 0){throw 'Original sound build root failed; no retry.'}
        if(!$record.QualifiedClosure -or !$record.QualifiedClosure.AcceptanceGranted){
            Complete-ChecksumBuildEvidence $owner $record $c.Started $Plan $context $boundedMeasure $false
        }
        # Heavy source/artifact proof is outside the unchanged two-second drain.
        foreach($role in $context.AcceptedReceipt.artifacts.Keys){
            $a=$context.AcceptedReceipt.artifacts[$role];$path=Join-Path $Plan.candidate $a.relative
            Assert-ChecksumBuildPath $path
            $s=[IO.File]::Open($path,'Open','Read','Read');$c.InputGuards.Add($s)
            $record.InputGuardsOpened++
            if($s.Length -ne $a.bytes -or (Get-ChecksumBuildHash $s $c) -cne $a.sha256){throw 'Closed-job final artifact proof differs.'}
        }
        $record.FinalArtifactsVerified=$true;$record.Artifacts=$context.AcceptedReceipt.artifacts
        $record.Success=$true
    }catch{$record.Failure=$_.Exception.Message;$record.Success=$false}
    finally {
        if($owner -and !$closed){try{Stop-AuditOwnedBuild $owner $record $measure;$closed=$true}catch{$record.ClosureError=$_.Exception.Message}}
        if($closed -and $postProofRequired){
            try{Confirm-ChecksumBuildInputs $c}catch{$sourceProofFailed=$true;$record.Success=$false;$record.SourceProofError=$_.Exception.Message}
        }
        if($lease){
            $release={
                foreach($guard in $c.InputGuards){$guard.Dispose();$record.InputGuardsDisposed++}
                if($record.InputGuardsDisposed -ne $record.InputGuardsOpened){throw 'Input/artifact guard disposal incomplete.'}
                Exit-IW7ResourceLease -Token $lease.Token
                $record.RetainedLeaseToken=$null
            }
            if($sourceProofFailed){$record.TreeClosed=$closed;$record.LeaseRetainedReason='Post-run input proof unresolved';$Bootstrap.Retain=$true;$c.Owner=$owner;$script:ChecksumRetainedContext=$c}
            else{
                Complete-AuditOwnedCleanup $owner $record $closed $measure $release
                if(!$record.LeaseReleased){$Bootstrap.Retain=$true;$c.Owner=$owner;$script:ChecksumRetainedContext=$c}
            }
        }
        $record.NativeRootResumed=$startedNative;$record.ElapsedMs=(Get-ChecksumBuildClock)-$c.Started
        if($record.ElapsedMs -ge 3600000){$record.Success=$false;$record.Failure='Observed deadline exceeded during final lifecycle.'}
        if(Test-Path -LiteralPath $Plan.candidate){
            try{Write-ChecksumBuildState $c}catch{$record.Success=$false;$record.FinalStateError=$_.Exception.Message;throw}
            if((Get-ChecksumBuildClock)-$c.Started -ge 3600000 -and $record.Success){
                $record.Success=$false;$record.Failure='Final state write returned after observed deadline.';Write-ChecksumBuildState $c
            }
        }
    }
    if(!$record.Success -or !$record.LeaseReleased){throw ('Sound build failed; preserve output and lease evidence. '+$record.Failure)}
    $record
}
